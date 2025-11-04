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
            dict_metrics['relocation_count']
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
            flt_memUsage = mem_usage_result if isinstance(mem_usage_result, (int, float)) else 0
            return {'error': 'Algorithm failed to return a valid solution.'}
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
            num_to_remove = max(1, num_to_remove) if num_to_remove > 0 else 0
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

    for int_i in arr_bestSolutionIndices:
        obj_finalPacker.add_item(arr_itemsToPack[int_i])

    obj_finalPacker.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

    # --- MODIFICATION ---
    # CRITICAL FIX: The post-processing function has been rewritten to be a robust, iterative physics simulation
    # that prevents the item merging bug and produces a stable, realistic pack.
    int_loading_relocations = _fnPostProcessPacking(obj_finalPacker.bins[0])

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
    # Recalculate the final metrics based on the contents of the bin AFTER the potential disruption AND physics simulation.
    final_metrics = fnCalculateAllMetrics(obj_finalPacker.bins[0].items, float(obj_bin.get_volume()), arr_packagesToLoad)
    
    # Add the relocations from the physics stabilization to the total relocation count.
    if isinstance(final_metrics['relocation_count'], (int, float)):
        final_metrics['relocation_count'] += int_loading_relocations

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
    print("This number reflects the count of items the packing library successfully placed in the bin.")
    print("It can differ from the initial or disrupted count if some items could not be fit due to their geometry.\n")
    
    return {
        'algorithm_name': strAlgorithmName,
        'metrics': {
            'computation_time': flt_computationTime,
            'memory_usage_mb': round(flt_memUsage, 2),
            'volume_utilization': final_metrics['volume_utilization'],
            'relocation_count': final_metrics['relocation_count'],
        },
        'packed_items': arr_finalPackedItemsDetails,
        'vehicle_info': {
            **dict_vehicleInfo,
            'num_packages_loaded': num_products_loaded,
            'total_packed_volume': round(flt_totalPackedVolume),
            'total_packed_service_time': round(flt_totalPackedServiceTime)
        }
    }


def _fnPostProcessPacking(objBin):
    """
    Applies a robust, iterative physics simulation to correct the packing solution
    from the library into a physically realistic and stable arrangement. This function
    is the core of preventing floating, merging, or unstable items.

    The process works as follows:
    1.  **Iterative Settling:** The function loops until a full pass over all items
        results in no movements, ensuring the stack is stable.
    2.  **Gravity Application (Bottom-Up):** In each pass, items are sorted by height.
        For each item, it calculates the highest solid surface directly beneath it
        formed by other items or the container floor.
    3.  **Stability Check (70% Rule):** It calculates the total X-Z overlap area
        with all supporters below. If this area is less than 70% of the item's own
        base, the item is considered unstable.
    4.  **Corrective Drop:** If an item is floating (not touching its support) or is
        unstable, it is moved down to rest on its highest support surface. This is
        counted as a "loading relocation".
    5.  **Collision Resolution:** After the gravity pass, a separate check finds any
        items that are now overlapping (colliding). It resolves this by pushing
        the items apart by the minimum amount needed. This also counts as a
        "loading relocation".
    6.  **Boundary Enforcement:** A final check ensures no item protrudes outside
        the container walls.

    Args:
        objBin (Bin): The bin object containing the final packed items.
    
    Returns:
        int: The total number of adjustments (loading relocations) made.
    """
    print("Starting robust iterative post-processing to fix stability and collisions...")
    
    INT_MAX_ITERATIONS = 30 # Allow more passes for complex arrangements to settle
    FLT_COMPARISON_TOLERANCE = 1e-4
    FLT_STABILITY_THRESHOLD = 0.70 # The "70% rule"
    INT_PRECISION_DIGITS = 3
    
    arr_items = objBin.items
    if not arr_items: return 0

    arr_bin_dims = [float(objBin.width), float(objBin.height), float(objBin.depth)]
    int_total_adjustments = 0

    for int_iteration in range(INT_MAX_ITERATIONS):
        int_items_moved_this_pass = 0
        
        # Sort items bottom-up to ensure a stable foundation is built first.
        arr_items.sort(key=lambda item: float(item.position[1]))

        # --- PASS 1: Gravity, Stability, and Vertical Correction ---
        for obj_current_item in arr_items:
            flt_ix, flt_iy, flt_iz = map(float, obj_current_item.position)
            flt_iw, flt_ih, flt_id = map(float, obj_current_item.get_dimension())
            flt_i_base_area = flt_iw * flt_id
            
            flt_highest_support_y = 0.0
            flt_total_support_area = 0.0
            
            for obj_other_item in arr_items:
                if obj_other_item is obj_current_item: continue
                flt_ox, flt_oy, flt_oz = map(float, obj_other_item.position)
                flt_ow, flt_oh, flt_od = map(float, obj_other_item.get_dimension())
                
                # Is the other item a potential supporter (below and overlapping in X-Z)?
                if (flt_oy + flt_oh) <= (flt_iy + FLT_COMPARISON_TOLERANCE):
                    overlap_x1 = max(flt_ix, flt_ox)
                    overlap_x2 = min(flt_ix + flt_iw, flt_ox + flt_ow)
                    overlap_z1 = max(flt_iz, flt_oz)
                    overlap_z2 = min(flt_iz + flt_id, flt_oz + flt_od)
                    
                    if overlap_x2 > overlap_x1 and overlap_z2 > overlap_z1:
                        flt_highest_support_y = max(flt_highest_support_y, flt_oy + flt_oh)
                        flt_total_support_area += (overlap_x2 - overlap_x1) * (overlap_z2 - overlap_z1)

            is_floating = abs(flt_iy - flt_highest_support_y) > FLT_COMPARISON_TOLERANCE
            is_unstable = (flt_total_support_area / flt_i_base_area) < FLT_STABILITY_THRESHOLD if flt_i_base_area > 0 else True
            
            if is_floating or (is_unstable and flt_iy > 0):
                obj_current_item.position[1] = str(flt_highest_support_y)
                int_items_moved_this_pass += 1
                int_total_adjustments += 1
                
        # --- PASS 2: Lateral Collision Resolution ---
        for i in range(len(arr_items)):
            for j in range(i + 1, len(arr_items)):
                item1 = arr_items[i]
                item2 = arr_items[j]
                
                pos1 = [float(p) for p in item1.position]
                dims1 = [float(d) for d in item1.get_dimension()]
                pos2 = [float(p) for p in item2.position]
                dims2 = [float(d) for d in item2.get_dimension()]
                
                # Check for 3D AABB overlap
                if (pos1[0] < pos2[0] + dims2[0] and pos1[0] + dims1[0] > pos2[0] and
                    pos1[1] < pos2[1] + dims2[1] and pos1[1] + dims1[1] > pos2[1] and
                    pos1[2] < pos2[2] + dims2[2] and pos1[2] + dims1[2] > pos2[2]):
                    
                    # Collision detected, push them apart along the axis of smallest overlap
                    dx = min((pos1[0] + dims1[0]) - pos2[0], (pos2[0] + dims2[0]) - pos1[0])
                    dy = min((pos1[1] + dims1[1]) - pos2[1], (pos2[1] + dims2[1]) - pos1[1])
                    dz = min((pos1[2] + dims1[2]) - pos2[2], (pos2[2] + dims2[2]) - pos1[2])

                    # Arbitrarily move item2
                    if dx < dy and dx < dz: # Resolve along X
                        if (pos1[0] + dims1[0]/2) < (pos2[0] + dims2[0]/2): item2.position[0] = str(float(item2.position[0]) + dx)
                        else: item2.position[0] = str(float(item2.position[0]) - dx)
                    elif dy < dz: # Resolve along Y (pushing up)
                        if (pos1[1] + dims1[1]/2) < (pos2[1] + dims2[1]/2): item2.position[1] = str(float(item2.position[1]) + dy)
                        else: item2.position[1] = str(float(item2.position[1]) - dy)
                    else: # Resolve along Z
                        if (pos1[2] + dims1[2]/2) < (pos2[2] + dims2[2]/2): item2.position[2] = str(float(item2.position[2]) + dz)
                        else: item2.position[2] = str(float(item2.position[2]) - dz)
                        
                    int_items_moved_this_pass += 1
                    int_total_adjustments += 1
        
        print(f"Post-processing iteration {int_iteration + 1}: {int_items_moved_this_pass} corrective adjustments made.")
        if int_items_moved_this_pass == 0:
            print("Item stack has settled into a stable, collision-free configuration.")
            break
    else:
        print("Warning: Post-processing reached max iterations. The configuration may not be fully settled.")

    # --- Final Pass: Boundary Enforcement ---
    for item in arr_items:
        pos = [float(p) for p in item.position]
        dims = [float(d) for d in item.get_dimension()]
        for axis in range(3):
            pos[axis] = max(0, min(pos[axis], arr_bin_dims[axis] - dims[axis]))
        item.position = [str(round(p, INT_PRECISION_DIGITS)) for p in pos]
    
    print(f"Packing post-processing complete. Total loading adjustments counted: {int_total_adjustments}")
    return int_total_adjustments