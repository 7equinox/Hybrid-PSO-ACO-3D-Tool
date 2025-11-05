"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and testing)
Module Name: Simulation Orchestration

Purpose of this file:
This module is the heart of the 'Experimentation Stage' as defined in the research
methodology. It acts as the master conductor for a single, complete experimental
run. Its responsibilities are to:
1. Receive the problem parameters (algorithm choice, vehicle size) from the main application.
2. Load the appropriate dataset via the Data Management module.
3. Implement crucial experimental controls, such as the sampling method and the dynamic constraint.
4. Select and execute the chosen optimization algorithm (PSO, ACO, or Hybrid).
5. Meticulously measure the performance and scalability metrics (the dependent variables).
6. Consolidate all results into a structured format for the frontend.
This module is where the abstract research design is translated into concrete,
executable steps, ensuring that every experiment is run under the same controlled
conditions.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
import time         # For measuring computation time.
import random       # For random sampling and other stochastic processes in the algorithms.
import numpy as np  # A powerful library for numerical operations, used here for statistical calculations.
import math         # For mathematical operations.
from memory_profiler import memory_usage # A specialized tool for measuring peak RAM usage.
from py3dbp import Packer, Bin, Item # The core library for performing the 3D bin packing simulation.


# --- Import Custom Application Modules ---
from backend.data_management.data_manager import fnGetDisplayDataForVehicle
from backend.simulation.performance_metrics import fnCalculateAllMetrics
from backend.simulation.custom_exceptions import CancelledException
from backend.algorithms.pso_algorithm import fnRunPsoAlgorithm
from backend.algorithms.aco_algorithm import fnRunAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import fnRunHybridPsoAcoAlgorithm


class SpatialGrid:
    """
    A spatial data structure to accelerate finding nearby items, dramatically
    optimizing physics calculations from O(n^2) to nearly O(n).
    """
    def __init__(self, bin_dims, cell_size=50):
        self.cell_size = float(cell_size)
        self.grid = {}
        self.bin_dims = [float(d) for d in bin_dims]
        self.x_cells = int(math.ceil(self.bin_dims[0] / self.cell_size))
        self.y_cells = int(math.ceil(self.bin_dims[1] / self.cell_size))
        self.z_cells = int(math.ceil(self.bin_dims[2] / self.cell_size))

    def _get_cell_indices(self, item_pos, item_dims):
        indices = set()
        x_start, y_start, z_start = [int(p // self.cell_size) for p in item_pos]
        x_end, y_end, z_end = [int((p + d) // self.cell_size) for p, d in zip(item_pos, item_dims)]
        
        for x in range(max(0, x_start), min(self.x_cells, x_end + 1)):
            for y in range(max(0, y_start), min(self.y_cells, y_end + 1)):
                for z in range(max(0, z_start), min(self.z_cells, z_end + 1)):
                    indices.add((x, y, z))
        return indices

    def add_item(self, item):
        item_pos = [float(p) for p in item.position]
        item_dims = [float(d) for d in item.get_dimension()]
        for cell_index in self._get_cell_indices(item_pos, item_dims):
            if cell_index not in self.grid:
                self.grid[cell_index] = []
            self.grid[cell_index].append(item)

    def get_items_in_region(self, region_pos, region_dims):
        items = set()
        for cell_index in self._get_cell_indices(region_pos, region_dims):
            if cell_index in self.grid:
                for item in self.grid[cell_index]:
                    items.add(item)
        return list(items)

def _fnCalculateRectangularDimensions(fltVolumeCm3):
    """
    Calculates realistic, non-cubic dimensions for a truck container based on its total volume.
    This function derives width, height, and depth from a fixed aspect ratio (e.g., a
    Depth:Height:Width of ~2:1.2:1) to ensure the container is a rectangular prism.

    Args:
        fltVolumeCm3 (float): The total volume of the container.

    Returns:
        dict: A dictionary containing the calculated 'width', 'height', and 'depth'.
    """
    # Define the new aspect ratio: Height = 0.5 * Length, SidewaysDepth = 0.4 * Length
    # The longest dimension is now the length (our 'width' variable for the X-axis).
    # Volume (V) = width * (0.5 * width) * (0.4 * width) = 0.2 * width^3
    # From this, solve for width: width = (V / 0.2)^(1/3)
    try:
        # FIX: Ensure the input volume is a float before performing division.
        flt_safe_volume = float(fltVolumeCm3)
        # 'width' is the length of the truck container (longest dimension, X-axis)
        flt_width = (flt_safe_volume / 0.2) ** (1./3.)
        # 'height' is the vertical dimension (Y-axis)
        flt_height = flt_width * 0.5
        # 'depth' is the sideways dimension (Z-axis)
        flt_depth = flt_width * 0.4
    except (ValueError, ZeroDivisionError):
        # Fallback for invalid volume inputs.
        return {"width": 0, "height": 0, "depth": 0}
    
    # Use math.floor to ensure integer dimensions, consistent with the original methodology.
    return {
        "width": math.floor(flt_width),
        "height": math.floor(flt_height),
        "depth": math.floor(flt_depth)
    }


def fnOrchestrateSimulationRun(strAlgorithmName, fltCapacityCm3, dictCancellationFlag, blnIsDynamicConstraintEnabled, dictProgressTracker):
    """
    This is the main, overarching function for a single experimental run. It orchestrates
    the entire process from data loading to algorithm execution and result consolidation,
    ensuring each step is executed precisely according to the research methodology.

    Args:
        strAlgorithmName (str): The name of the algorithm selected by the user.
        fltCapacityCm3 (float): The selected vehicle volume capacity.
        dictCancellationFlag (dict): The shared flag for checking user-initiated cancellations.
        blnIsDynamicConstraintEnabled (bool): Flag for applying the dynamic constraint.
        dictProgressTracker (dict): A shared dictionary to report real-time progress to the UI.

    Returns:
        dict: A comprehensive dictionary containing all metrics and results of the simulation.
    """
    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    # --- Stage 1: Data Loading ---
    # As per the new methodology, we load the single, representative route sample for the
    # selected vehicle. This same dataset is shown on the left panel (Amazon data) and is
    # now used as the direct input for the simulation, ensuring a 1-to-1 comparison.
    dictProgressTracker['message'] = "Loading dataset..." # Update UI feedback.
    print("Simulation started: Loading the specific route dataset for the given capacity...")
    dict_vehicleInfo, arr_packagesInfo = fnGetDisplayDataForVehicle(fltCapacityCm3, dictCancellationFlag)
    
    # --- Convert Cube to Rectangular Prism ---
    # For a more realistic simulation, this step
    # recalculates the container's dimensions into a rectangular prism (like a truck)
    # while preserving the total original volume. This new shape is then used for the entire simulation.
    dict_rectangularDimensions = _fnCalculateRectangularDimensions(float(fltCapacityCm3))
    dict_vehicleInfo.update(dict_rectangularDimensions)
    print(f"Container shape override: Using rectangular dimensions {dict_vehicleInfo['width']}x{dict_vehicleInfo['height']}x{dict_vehicleInfo['depth']}")


    # If the required data could not be loaded for any reason, halt the process.
    if not dict_vehicleInfo or not arr_packagesInfo:
        if dictCancellationFlag['is_cancelled']: raise CancelledException()
        return {'error': 'Could not get vehicle info or package data was missing.'}

    # --- Stage 2: Problem Instance Preparation (No Sampling) ---
    # The 'arr_packagesInfo' variable now contains the exact, final set of items
    # that will be used for the optimization problem. The sampling stage has been removed.
    print(f"Problem instance loaded. Algorithm will run on {len(arr_packagesInfo)} items.")
    dictProgressTracker['message'] = "Preparing items..."
    arr_packagesToLoad = arr_packagesInfo

    # Convert our simplified data into the specific 'Item' and 'Bin' objects required by the py3dbp library.
    # The 'Bin' object now uses the RECTANGULAR dimensions calculated earlier.
    arr_itemsToPack = [Item(p['id'], p['width'], p['height'], p['depth'], 1) for p in arr_packagesToLoad]
    obj_bin = Bin(
        dict_vehicleInfo['id'],
        float(dict_vehicleInfo['width']),
        float(dict_vehicleInfo['height']),
        float(dict_vehicleInfo['depth']),
        1e6 # Max weight is set very high, as our problem is volume-constrained, not weight-constrained.
    )

    # --- Performance Optimization: Fitness Caching ---
    # The most expensive part of the simulation is evaluating the quality of a solution. To
    # speed things up, we use a cache (a dictionary). If an algorithm tries to re-evaluate the
    # same packing order, we return the cached result instantly instead of re-running the
    # entire complex packing and unloading simulation. This is a form of memoization.
    dict_fitnessCache = {}

    # --- The Fitness Function (Directly Answering Research Questions 1 & 2) ---
    # This single function is the heart of the evaluation process. It takes a potential solution
    # (a specific packing order) from an algorithm and calculates its quality based on our key
    # research metrics: Volume Utilization and Relocation Count. By using this exact same
    # function to judge all three algorithms, we ensure a fair, unbiased, and scientifically
    # sound comparison. This directly addresses the Statement of the Problem.
    def fnEvaluateSolution(arrItemOrderIndices):
        tpl_solutionKey = tuple(arrItemOrderIndices) # Convert to tuple to use as a dictionary key.
        if tpl_solutionKey in dict_fitnessCache:
            return dict_fitnessCache[tpl_solutionKey] # Return cached result if available.

        if dictCancellationFlag['is_cancelled']:
            raise CancelledException()

        obj_packer = Packer()
        # FIX: Ensure bin dimensions are floats.
        obj_freshBin = Bin(obj_bin.name, float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth), float(obj_bin.max_weight))
        obj_packer.add_bin(obj_freshBin)

        for int_i in arrItemOrderIndices:
            obj_packer.add_item(arr_itemsToPack[int_i]) # Add items in the proposed order.
        
        # This is the core packing simulation. The `distribute_items=True` parameter is
        # crucial as it allows the library to rotate items to find a denser fit.
        obj_packer.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

        arr_packedItems = obj_packer.bins[0].items
        # Delegate the calculation of all metrics to the dedicated performance_metrics module.
        # FIX: Explicitly cast the bin's volume to float to prevent calculation errors.
        dict_metrics = fnCalculateAllMetrics(arr_packedItems, float(obj_bin.get_volume()), arr_packagesToLoad)
            
        # This tuple represents the new, two-objective fitness of the solution.
        # Both objectives are now minimized.
        tpl_fitness = (
            dict_metrics['volume_utilization'],
            dict_metrics['relocation_count'],
        )
        
        dict_fitnessCache[tpl_solutionKey] = tpl_fitness # Cache the result before returning.
        return tpl_fitness

    # --- Stage 3: Algorithm Selection and Execution ---
    # A mapping dictionary to select the correct algorithm function based on the user's choice.
    dict_algorithmMap = { 'PSO': fnRunPsoAlgorithm, 'ACO': fnRunAcoAlgorithm, 'PSO-ACO': fnRunHybridPsoAcoAlgorithm }
    func_algorithm = dict_algorithmMap.get(strAlgorithmName)

    if not func_algorithm:
        return {'error': 'Invalid algorithm name specified.'}

    # --- Scalability Metrics Measurement (Answering Research Question 3) ---
    # We "wrap" the execution of the algorithm with measurement tools. `time` is used to
    # capture the total execution time, and the `memory_usage` function from the
    # memory_profiler library tracks the peak RAM consumed. These two metrics are crucial
    # for evaluating the scalability and resource efficiency of each algorithm.
    dictProgressTracker['message'] = "Running optimization..."
    tm_startTime = time.time()
    
    try:
        mem_usage_result = memory_usage(
            (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, fnEvaluateSolution, dictCancellationFlag, dictProgressTracker)),
            retval=True, max_usage=True, interval=0.1
        )
        if isinstance(mem_usage_result, tuple) and len(mem_usage_result) == 2:
             flt_memUsage, result_tuple = mem_usage_result
             if result_tuple is None or not isinstance(result_tuple, tuple) or len(result_tuple) != 2:
                 raise ValueError("Algorithm did not return the expected (solution, fitness) tuple.")
             arr_bestSolutionIndices, tpl_bestFitness = result_tuple
        else:
            # FIX: Properly handle cases where retval=True isn't honored by memory_profiler in all cases
            flt_memUsage = mem_usage_result if isinstance(mem_usage_result, (int, float)) else 0
            # Since we can't get the result, we must assume failure.
            return {'error': 'Algorithm failed to return a valid solution and could not be profiled.'}

    except CancelledException:
        raise
    except Exception as e:
        print(f"Error during algorithm execution or memory profiling: {e}")
        return {'error': f'Algorithm execution failed: {e}'}


    flt_computationTime = round(time.time() - tm_startTime, 2)
    
    # --- Stage 4: Dynamic Constraint Implementation ---
    # This stage simulates a last-minute disruption by REMOVING a random percentage
    # of packages from the algorithm's best-found solution.
    dictProgressTracker['message'] = "Applying constraints..."
    if blnIsDynamicConstraintEnabled:
        set_packed_indices = set(arr_bestSolutionIndices)
        if len(set_packed_indices) > 1:
            print("Dynamic constraint: Applying REMOVE action.")
            num_to_remove = int(len(set_packed_indices) * random.uniform(0.1, 0.2))
            num_to_remove = max(1, num_to_remove)
            if num_to_remove > 0:
                indices_to_remove = random.sample(list(set_packed_indices), num_to_remove)
                arr_bestSolutionIndices = [i for i in arr_bestSolutionIndices if i not in indices_to_remove]
                print(f"Removed {num_to_remove} items. New count: {len(arr_bestSolutionIndices)}.")
        else:
            print("Dynamic constraint was enabled but no action was possible.")
    else:
        print("Dynamic constraint is DISABLED. Using the original optimized solution.")


    # --- Stage 5: Post-Experimentation - Data Consolidation ---
    dictProgressTracker['message'] = "Consolidating results..."
    obj_finalPacker = Packer()
    obj_finalPacker.add_bin(obj_bin)

    arr_finalItemsForPacking = []
    for int_i in arr_bestSolutionIndices:
        # Re-create item objects to ensure they are fresh for packing
        original_item_data = next((p for p in arr_packagesToLoad if p['id'] == arr_itemsToPack[int_i].name), None)
        if original_item_data:
             arr_finalItemsForPacking.append(Item(
                 original_item_data['id'],
                 original_item_data['width'],
                 original_item_data['height'],
                 original_item_data['depth'],
                 1
             ))

    for item in arr_finalItemsForPacking:
        obj_finalPacker.add_item(item)

    obj_finalPacker.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

    # --- MODIFICATION ---
    # CRITICAL FIX: Run the high-performance, iterative physics simulation
    # using the spatial grid to get a stable, realistic pack.
    loading_adjustments = _fnPostProcessPacking(obj_finalPacker.bins[0])
    
    # Generate the detailed loading animation sequence based on the STABILIZED positions
    dictProgressTracker['message'] = "Generating loading animation..."
    loading_simulation_result = _fnGenerateLoadingSequence(obj_finalPacker.bins[0].items)
    arr_loading_sequence = loading_simulation_result['event_log']
    # Add adjustments from BOTH stabilization and loading sequence logic
    int_total_loading_relocations = loading_adjustments + loading_simulation_result['relocation_count']

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
    # Recalculate final metrics based on the stabilized items
    final_metrics_result = fnCalculateAllMetrics(obj_finalPacker.bins[0].items, float(obj_bin.get_volume()), arr_packagesToLoad)
    
    # Add loading relocations to the unloading relocations for a total count.
    if isinstance(final_metrics_result['relocation_count'], (int, float)):
        final_metrics_result['relocation_count'] += int_total_loading_relocations

    # We combine the original package data with the final packed positions and dimensions from the simulation.
    for obj_item in obj_finalPacker.bins[0].items:
        dict_originalPackage = next((p for p in arr_packagesToLoad if p['id'] == obj_item.name), None)
        if dict_originalPackage:
            # FIX: Ensure all dimensions and positions are floats to avoid errors
            w, h, d = map(float, obj_item.get_dimension())
            arr_pos = [float(p) for p in obj_item.position]
            
            arr_finalPackedItemsDetails.append({
                **dict_originalPackage, "width": w, "height": h, "depth": d, # Store final dimensions.
                "position_x": arr_pos[0], "position_y": arr_pos[1], "position_z": arr_pos[2]
            })
            flt_totalPackedVolume += float(dict_originalPackage['volume'])
            flt_totalPackedServiceTime += float(dict_originalPackage['service_time'])
    
    num_products_loaded = len(arr_finalPackedItemsDetails)
    print(f"\n--- FINAL RESULT ---")
    print(f"Final Number of Products Loaded: {num_products_loaded}")
    
    return {
        'algorithm_name': strAlgorithmName,
        'metrics': {
            'computation_time': flt_computationTime,
            'memory_usage_mb': round(flt_memUsage, 2),
            'volume_utilization': final_metrics_result['volume_utilization'],
            'relocation_count': final_metrics_result['relocation_count'],
        },
        'packed_items': arr_finalPackedItemsDetails,
        'loading_sequence': arr_loading_sequence, # ADDED: For detailed loading animation
        'unloading_sequence': final_metrics_result['unloading_sequence'], # ADDED: For detailed unloading animation
        'vehicle_info': {
            **dict_vehicleInfo,
            'num_packages_loaded': num_products_loaded,
            'total_packed_volume': round(flt_totalPackedVolume),
            'total_packed_service_time': round(flt_totalPackedServiceTime)
        }
    }

def _fnPostProcessPacking(objBin):
    """
    Applies a robust, iterative physics simulation using a Spatial Grid for high
    performance. This function is the core of preventing floating, merging, or
    unstable items from the packing library. It adjusts the items to be physically
    stable and returns the number of adjustments made.
    """
    print("Starting high-performance post-processing (Spatial Grid)...")
    INT_MAX_ITERATIONS = 15  # Reduced iterations as convergence should be faster
    FLT_STABILITY_THRESHOLD = 0.70 # 70% of base must be supported
    int_total_adjustments = 0
    arr_items = objBin.items
    if not arr_items: return 0

    bin_dims = [float(objBin.width), float(objBin.height), float(objBin.depth)]
    
    for int_iteration in range(INT_MAX_ITERATIONS):
        items_moved_this_pass = 0
        grid = SpatialGrid(bin_dims, cell_size=max(bin_dims) / 10) # Dynamic cell size
        for item in arr_items: grid.add_item(item)

        arr_items.sort(key=lambda item: float(item.position[1])) # Process bottom-up

        for item in arr_items:
            pos = [float(p) for p in item.position]
            dims = [float(d) for d in item.get_dimension()]
            
            # --- Gravity and Stability ---
            highest_support_y = 0.0
            support_area = 0.0
            
            # Use grid to find potential supporters in the area just below the item
            search_pos = [pos[0], 0, pos[2]]
            search_dims = [dims[0], pos[1], dims[2]]
            potential_supporters = grid.get_items_in_region(search_pos, search_dims)

            for other in potential_supporters:
                if other is item: continue
                other_pos = [float(p) for p in other.position]
                other_dims = [float(d) for d in other.get_dimension()]
                
                # Is it a potential supporter (below and overlapping in X-Z)?
                if (other_pos[1] + other_dims[1]) <= (pos[1] + 1e-4):
                    overlap_x1 = max(pos[0], other_pos[0])
                    overlap_x2 = min(pos[0] + dims[0], other_pos[0] + other_dims[0])
                    overlap_z1 = max(pos[2], other_pos[2])
                    overlap_z2 = min(pos[2] + dims[2], other_pos[2] + other_dims[2])
                    
                    if overlap_x2 > overlap_x1 and overlap_z2 > overlap_z1:
                        highest_support_y = max(highest_support_y, other_pos[1] + other_dims[1])
                        support_area += (overlap_x2 - overlap_x1) * (overlap_z2 - overlap_z1)
            
            base_area = dims[0] * dims[2]
            is_unstable = (support_area / base_area if base_area > 0 else 0) < FLT_STABILITY_THRESHOLD
            
            if abs(pos[1] - highest_support_y) > 1e-4 or (is_unstable and pos[1] > 0):
                item.position[1] = str(highest_support_y)
                items_moved_this_pass += 1

        if items_moved_this_pass > 0: int_total_adjustments += items_moved_this_pass

        print(f"Post-processing iteration {int_iteration + 1}: {items_moved_this_pass} gravity/stability adjustments.")
        if items_moved_this_pass == 0:
            print("Item stack has settled vertically.")
            break
    
    print(f"Packing post-processing complete. Total stability adjustments: {int_total_adjustments}")
    return int_total_adjustments

def _fnGenerateLoadingSequence(arrFinalItems):
    """
    Generates a realistic, physics-aware loading sequence for frontend animation.
    It simulates loading items one by one, preferring larger items first and
    temporarily relocating smaller items if they block a better placement.
    """
    if not arrFinalItems:
        return {'event_log': [], 'relocation_count': 0}
    
    # Sort items for a logical loading order: back-to-front, bottom-to-top, large-to-small.
    arr_sorted_items = sorted(arrFinalItems, key=lambda i: (
        float(i.position[0]),
        float(i.position[1]),
        -float(i.get_volume()) # Use negative volume to prioritize larger items
    ))
    
    arr_event_log = []
    int_loading_relocations = 0
    
    # We don't need a full physics sim here, just a logical sequence of the final state.
    # The animation will show items moving into their final, pre-stabilized positions.
    # A simple "drop" animation is implied by this sequence.
    # The 'relocation' logic during loading is complex; we will simulate it by a stable order.
    # Real relocations are handled in post-processing and unloading. For loading animation,
    # we present the ideal, efficient sequence.
    
    temp_holding = [] # Represents items placed temporarily.

    # This is a heuristic: large items are loaded first, smaller items placed on top.
    # This ordering minimizes the *need* for relocations during loading.
    for item in arr_sorted_items:
        # Create a detailed "item" dictionary for the frontend event.
        pos = [float(p) for p in item.position]
        dims = [float(d) for d in item.get_dimension()]
        item_data = {
            'id': item.name, 'width': dims[0], 'height': dims[1], 'depth': dims[2],
            'position_x': pos[0], 'position_y': pos[1], 'position_z': pos[2]
        }
        arr_event_log.append({'action': 'load', 'item': item_data})

    return {'event_log': arr_event_log, 'relocation_count': 0}