"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
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
from backend.data_management.data_manager import fnGetSimulationDataForVehicle
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
        # 'width' is the length of the truck container (longest dimension, X-axis)
        flt_width = (fltVolumeCm3 / 0.2) ** (1./3.)
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
    dictProgressTracker['message'] = "Loading dataset..." # Update UI feedback.
    print("Simulation started: Loading full dataset for the given capacity...")
    # Fetch the complete, aggregated dataset for the selected vehicle capacity from the data manager.
    dict_vehicleInfo, arr_packagesInfo = fnGetSimulationDataForVehicle(fltCapacityCm3, dictCancellationFlag)
    
    # --- Convert Cube to Rectangular Prism ---
    # For a more realistic simulation, this step
    # recalculates the container's dimensions into a rectangular prism (like a truck)
    # while preserving the total original volume. This new shape is then used for the entire simulation.
    dict_rectangularDimensions = _fnCalculateRectangularDimensions(fltCapacityCm3)
    dict_vehicleInfo.update(dict_rectangularDimensions)
    print(f"Container shape override: Using rectangular dimensions {dict_vehicleInfo['width']}x{dict_vehicleInfo['height']}x{dict_vehicleInfo['depth']}")


    # If the required data could not be loaded for any reason, halt the process.
    if not dict_vehicleInfo or not arr_packagesInfo:
        if dictCancellationFlag['is_cancelled']: raise CancelledException()
        return {'error': 'Could not get vehicle info or package data was missing.'}

    # --- Stage 2: Sampling Method Implementation ---
    # This is a critical engineering step to solve a major computational problem.
    # The full dataset for larger vehicles can contain tens of thousands of items, which would
    # require enormous amounts of memory and weeks of computation time. To make the experiment
    # feasible on standard hardware, we implement a 'Volume-Constrained Stratified Random
    # Sampling' method. This technique intelligently creates a smaller, yet statistically
    # representative, problem instance. This allows us to fairly benchmark the algorithms
    # under controlled, solvable conditions.
    dictProgressTracker['message'] = "Sampling data..."
    INT_MAX_SAMPLE_SIZE = 400 # A hard limit to prevent out-of-memory errors during the experiment.
    if len(arr_packagesInfo) > INT_MAX_SAMPLE_SIZE:
        print(f"Original dataset has {len(arr_packagesInfo)} items. Applying sampling to reduce to {INT_MAX_SAMPLE_SIZE}.")

        # Step 2a: Stratification. We categorize items into Small, Medium, and Large based on volume.
        # This ensures that our smaller sample maintains the same general distribution of item sizes
        # as the much larger original dataset, preserving its real-world characteristics.
        arr_volumes = [p['volume'] for p in arr_packagesInfo]
        flt_p33, flt_p66 = np.percentile(arr_volumes, [33.3, 66.7])
        arr_smallItems = [p for p in arr_packagesInfo if p['volume'] <= flt_p33]
        arr_mediumItems = [p for p in arr_packagesInfo if flt_p33 < p['volume'] <= flt_p66]
        arr_largeItems = [p for p in arr_packagesInfo if p['volume'] > flt_p66]

        random.shuffle(arr_smallItems)
        random.shuffle(arr_mediumItems)
        random.shuffle(arr_largeItems)

        # Step 2b: Proportional and Constrained Selection.
        # We build the new sample by iteratively adding items from each size category. The process
        # stops when we either reach the max sample size OR the total volume of sampled items
        # exceeds the vehicle's capacity. This guarantees a feasible and standardized problem.
        arr_sampledPackages = []
        flt_currentVolume = 0.0
        iter_small = iter(arr_smallItems)
        iter_medium = iter(arr_mediumItems)
        iter_large = iter(arr_largeItems)

        while len(arr_sampledPackages) < INT_MAX_SAMPLE_SIZE:
            bln_addedInCycle = False
            for iterator in [iter_small, iter_medium, iter_large]:
                try:
                    obj_item = next(iterator)
                    if flt_currentVolume + obj_item['volume'] <= fltCapacityCm3: # The volume constraint.
                        arr_sampledPackages.append(obj_item)
                        flt_currentVolume += obj_item['volume']
                        bln_addedInCycle = True
                except StopIteration:
                    pass
                if len(arr_sampledPackages) >= INT_MAX_SAMPLE_SIZE: break
            if not bln_addedInCycle: break

        arr_packagesInfo = arr_sampledPackages # The smaller sample now becomes our official problem instance.
        print(f"Sampling complete. New problem size: {len(arr_packagesInfo)} items.")

    # --- Stage 3: Dynamic Constraint Implementation ---
    # As per the methodology, this step simulates real-world disruptions. If enabled by the user,
    # it randomly removes 10-20% of the items from the problem right before optimization begins.
    # This directly tests the algorithms' adaptability to sudden changes, a key research goal.
    dictProgressTracker['message'] = "Applying constraints..."
    if blnIsDynamicConstraintEnabled:
        print("Dynamic constraint is ENABLED. Removing 10-20% of items from the problem.")
        if len(arr_packagesInfo) > 1:
            int_numToRemove = int(len(arr_packagesInfo) * random.uniform(0.1, 0.2))
            arr_packagesToLoad = random.sample(arr_packagesInfo, len(arr_packagesInfo) - int_numToRemove)
        else:
            arr_packagesToLoad = arr_packagesInfo
    else:
        print("Dynamic constraint is DISABLED. Using the full set of sampled items.")
        arr_packagesToLoad = arr_packagesInfo

    # Convert our simplified data into the specific 'Item' and 'Bin' objects required by the py3dbp library.
    # The 'Bin' object now uses the RECTANGULAR dimensions calculated earlier.
    arr_itemsToPack = [Item(p['id'], p['width'], p['height'], p['depth'], 1) for p in arr_packagesToLoad]
    obj_bin = Bin(
        dict_vehicleInfo['id'],
        dict_vehicleInfo['width'],
        dict_vehicleInfo['height'],
        dict_vehicleInfo['depth'],
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
    # research metrics: Volume Utilization, Relocation Count, Unloading Feasibility, and Sequence Length.
    # By using this exact same function to judge all three algorithms, we ensure a fair,
    # unbiased, and scientifically sound comparison. This directly addresses the Statement of the Problem.
    def fnEvaluateSolution(arrItemOrderIndices):
        tpl_solutionKey = tuple(arrItemOrderIndices) # Convert to tuple to use as a dictionary key.
        if tpl_solutionKey in dict_fitnessCache:
            return dict_fitnessCache[tpl_solutionKey] # Return cached result if available.

        if dictCancellationFlag['is_cancelled']:
            raise CancelledException()

        obj_packer = Packer()
        obj_freshBin = Bin(obj_bin.name, obj_bin.width, obj_bin.height, obj_bin.depth, obj_bin.max_weight)
        obj_packer.add_bin(obj_freshBin)

        for int_i in arrItemOrderIndices:
            obj_packer.add_item(arr_itemsToPack[int_i]) # Add items in the proposed order.
        
        # This is the core packing simulation. The `distribute_items=True` parameter is
        # crucial as it allows the library to rotate items to find a denser fit.
        obj_packer.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

        arr_packedItems = obj_packer.bins[0].items
        if not arr_packedItems:
            # If a solution results in no items being packed, it's given the worst possible fitness score.
            tpl_fitness = (0, float('inf'), float('inf'))
        else:
            # Delegate the calculation of all metrics to the dedicated performance_metrics module.
            dict_metrics = fnCalculateAllMetrics(arr_packedItems, obj_bin.get_volume(), arr_packagesToLoad)
            
            # An 'Infeasible' solution (one with unloading deadlocks) is heavily penalized.
            # This guides the algorithms away from such operationally disastrous arrangements.
            if dict_metrics['unloading_feasibility'] == 'Infeasible':
                tpl_fitness = (0, float('inf'), float('inf'))
            else:
                # This tuple represents the multi-objective fitness of the solution.
                tpl_fitness = (
                    dict_metrics['volume_utilization'],
                    dict_metrics['relocation_count'],
                    dict_metrics['unloading_sequence_length']
                )
        
        dict_fitnessCache[tpl_solutionKey] = tpl_fitness # Cache the result before returning.
        return tpl_fitness

    # --- Stage 4: Algorithm Selection and Execution ---
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
    # The `memory_usage` function calls our algorithm and returns both the memory usage and the algorithm's own return values.
    flt_memUsage, (arr_bestSolutionIndices, tpl_bestFitness) = memory_usage(
        (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, fnEvaluateSolution, dictCancellationFlag, dictProgressTracker)),
        retval=True, max_usage=True, interval=0.1
    )
    flt_computationTime = round(time.time() - tm_startTime, 2)

    # --- Stage 5: Post-Experimentation - Data Consolidation ---
    # After the algorithm has finished and found its best solution, this section prepares a
    # comprehensive, detailed result object to be sent back to the user interface for display.
    dictProgressTracker['message'] = "Consolidating results..."
    obj_finalPacker = Packer()
    obj_finalPacker.add_bin(obj_bin)

    for int_i in arr_bestSolutionIndices:
        obj_finalPacker.add_item(arr_itemsToPack[int_i])

    obj_finalPacker.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

    # Apply a post-processing step to add physical realism (gravity).
    _fnPostProcessPacking(obj_finalPacker.bins[0])

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
    # We combine the original package data with the final packed positions and dimensions from the simulation.
    for obj_item in obj_finalPacker.bins[0].items:
        dict_originalPackage = next((p for p in arr_packagesToLoad if p['id'] == obj_item.name), None)
        if dict_originalPackage:
            w, h, d = obj_item.get_dimension() # Get the final, possibly rotated, dimensions.
            arr_pos = [float(p) for p in obj_item.position] # Convert string positions to numbers.
            
            arr_finalPackedItemsDetails.append({
                **dict_originalPackage, "width": w, "height": h, "depth": d, # Store final dimensions.
                "position_x": arr_pos[0], "position_y": arr_pos[1], "position_z": arr_pos[2]
            })
            flt_totalPackedVolume += dict_originalPackage['volume']
            flt_totalPackedServiceTime += dict_originalPackage['service_time']
    
    # Construct the final, structured results dictionary that will be sent to the frontend.
    return {
        'algorithm_name': strAlgorithmName,
        'metrics': {
            'computation_time': flt_computationTime,
            'memory_usage_mb': round(flt_memUsage, 2),
            'volume_utilization': tpl_bestFitness[0],
            'relocation_count': tpl_bestFitness[1],
            'unloading_feasibility': "Feasible" if tpl_bestFitness[1] != float('inf') else "Infeasible",
            'unloading_sequence_length': tpl_bestFitness[2]
        },
        'packed_items': arr_finalPackedItemsDetails,
        'vehicle_info': {
            **dict_vehicleInfo,
            'num_packages_loaded': len(arr_finalPackedItemsDetails),
            'total_packed_volume': round(flt_totalPackedVolume),
            'total_packed_service_time': round(flt_totalPackedServiceTime)
        }
    }


def _fnPostProcessPacking(objBin):
    """
    Applies simple "gravity" and boundary enforcement to the final packing solution.
    The `py3dbp` library sometimes leaves small gaps or places items slightly outside
    the container boundaries. This function corrects those issues to create a more
    physically realistic visualization for the user.

    Args:
        objBin (Bin): The bin object containing the final packed items.
    """
    print("Starting packing post-processing for physical realism...")
    
    list_items = objBin.items
    # This correctly reads the (potentially rectangular) dimensions from the Bin object.
    bin_dims = [np.floor(float(objBin.width)), np.floor(float(objBin.height)), np.floor(float(objBin.depth))]
    
    # --- Stage 1: Iterative Gravity Simulation ---
    # We loop multiple times to allow items to "settle" on top of each other correctly.
    # An item placed on top of two smaller items might need a second pass to settle further.
    for _ in range(3): # Three passes are usually sufficient for most configurations.
        items_moved = 0
        list_items.sort(key=lambda item: float(item.position[1])) # Sort by height (Y-axis).
        
        for i, obj_item in enumerate(list_items):
            flt_ix, flt_iy, flt_iz = [float(p) for p in obj_item.position]
            flt_iw, flt_ih, flt_id = [float(d) for d in obj_item.get_dimension()]
            
            flt_supportHeight = 0.0 # Start by assuming it rests on the floor (y=0).
            
            # Find the highest point of support from all OTHER items below it.
            for j, obj_otherItem in enumerate(list_items):
                if i == j: continue
                flt_ox, flt_oy, flt_oz = [float(p) for p in obj_otherItem.position]
                flt_ow, flt_oh, flt_od = [float(d) for d in obj_otherItem.get_dimension()]
                
                bln_x_overlap = (flt_ix < flt_ox + flt_ow) and (flt_ox < flt_ix + flt_iw)
                bln_z_overlap = (flt_iz < flt_oz + flt_od) and (flt_oz < flt_iz + flt_id)

                # If another item is below this one and overlaps in the X-Z plane, it provides support.
                if bln_x_overlap and bln_z_overlap and (flt_oy + flt_oh <= flt_iy + 0.1):
                    flt_supportHeight = max(flt_supportHeight, flt_oy + flt_oh)

            # If the item is "floating," move it down to its support height.
            if flt_iy > flt_supportHeight:
                obj_item.position[1] = str(flt_supportHeight)
                items_moved += 1
        
        if items_moved == 0:
            print("Item stack has settled.")
            break # If a full pass moves no items, gravity has been fully applied.

    # --- Stage 2: Enforce Container Boundaries ---
    # This step ensures no part of any item is visually outside the container wireframe.
    for obj_item in list_items:
        pos = [float(p) for p in obj_item.position]
        dims = [float(d) for d in obj_item.get_dimension()]
        
        for axis in range(3): # Check X, Y, and Z axes.
            if pos[axis] < 0: pos[axis] = 0 # Clamp to the floor/walls.
            if pos[axis] + dims[axis] > bin_dims[axis]:
                pos[axis] = bin_dims[axis] - dims[axis] # Clamp to the ceiling/far walls.
        
        obj_item.position = [str(p) for p in pos]
        
    print("Packing post-processing complete.")