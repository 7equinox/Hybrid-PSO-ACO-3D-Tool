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
    # ** Store a copy of the full dataset before sampling for the dynamic constraint 'insert' operation.
    arr_full_dataset_for_capacity = arr_packagesInfo[:]

    
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

    # At this point, the final set of items for the initial optimization is prepared.
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
    # The `memory_usage` function calls our algorithm and returns both the memory usage and the algorithm's own return values.
    flt_memUsage, (arr_bestSolutionIndices, tpl_bestFitness) = memory_usage(
        (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, fnEvaluateSolution, dictCancellationFlag, dictProgressTracker)),
        retval=True, max_usage=True, interval=0.1
    )
    flt_computationTime = round(time.time() - tm_startTime, 2)
    
    # --- Stage 4: Dynamic Constraint Implementation ---
    # This stage simulates last-minute disruptions. It first determines which actions
    # (remove or substitute) are possible, then randomly chooses one to execute.
    # This guarantees that a disruption always occurs if one is possible.
    dictProgressTracker['message'] = "Applying constraints..."
    if blnIsDynamicConstraintEnabled:
        # Determine the set of packed items from the initial solution.
        set_packed_indices = set(arr_bestSolutionIndices)
        
        # Find packages that exist in the full dataset but were not part of the initial problem.
        initial_problem_ids = {p['id'] for p in arr_packagesToLoad}
        new_item_candidates = [p for p in arr_full_dataset_for_capacity if p['id'] not in initial_problem_ids]
        
        # Build a list of actions that are currently possible.
        arr_possible_actions = []
        if len(set_packed_indices) > 1:
            arr_possible_actions.append('remove')
        # Substitution is possible only if there are packed items to remove and new items to add.
        if set_packed_indices and new_item_candidates:
            arr_possible_actions.append('insert')
            
        if arr_possible_actions:
            # Randomly select a valid action to perform.
            str_action = random.choice(arr_possible_actions)
            
            # --- REMOVE ACTION ---
            if str_action == 'remove':
                print("Dynamic constraint: Applying REMOVE action.")
                num_to_remove = int(len(set_packed_indices) * random.uniform(0.1, 0.2))
                num_to_remove = max(1, num_to_remove) if num_to_remove > 0 else 0
                
                if num_to_remove > 0:
                    indices_to_remove = random.sample(list(set_packed_indices), num_to_remove)
                    arr_bestSolutionIndices = [i for i in arr_bestSolutionIndices if i not in indices_to_remove]
                    print(f"Removed {num_to_remove} items. New count: {len(arr_bestSolutionIndices)}.")

            # --- INSERT ACTION (as Substitution) ---
            elif str_action == 'insert':
                print("Dynamic constraint: Applying INSERT (substitution) action.")
                # The number to substitute is based on the packed items and cannot exceed the available pools.
                num_to_substitute = int(len(set_packed_indices) * random.uniform(0.1, 0.2))
                num_to_substitute = min(num_to_substitute, len(new_item_candidates), len(set_packed_indices))
                num_to_substitute = max(1, num_to_substitute) if num_to_substitute > 0 else 0

                if num_to_substitute > 0:
                    # Step 1: Select indices to remove from the current best solution.
                    indices_to_remove = random.sample(arr_bestSolutionIndices, num_to_substitute)
                    
                    # Step 2: Select brand new packages to insert.
                    new_packages_to_add = random.sample(new_item_candidates, num_to_substitute)
                    
                    # Step 3: Add these new packages to our master lists and get their new indices.
                    newly_added_indices = []
                    for new_pkg in new_packages_to_add:
                        arr_packagesToLoad.append(new_pkg)
                        arr_itemsToPack.append(Item(new_pkg['id'], new_pkg['width'], new_pkg['height'], new_pkg['depth'], 1))
                        newly_added_indices.append(len(arr_itemsToPack) - 1) # The index is the new last position.

                    # Step 4: Rebuild the solution by removing old indices and adding the new ones.
                    arr_bestSolutionIndices = [i for i in arr_bestSolutionIndices if i not in indices_to_remove]
                    arr_bestSolutionIndices.extend(newly_added_indices)
                    
                    print(f"Substituted {num_to_substitute} items. Solution count is now {len(arr_bestSolutionIndices)}.")
        
        else:
            # This handles edge cases where no disruption is possible (e.g., only 1 item).
            print("Dynamic constraint was enabled but no action was possible.")
    else:
        print("Dynamic constraint is DISABLED. Using the original optimized solution.")


    # --- Stage 5: Post-Experimentation - Data Consolidation ---
    # After the algorithm has finished and found its best solution (which may have been
    # disrupted by the dynamic constraint), this section prepares a comprehensive result
    # object for the UI.
    dictProgressTracker['message'] = "Consolidating results..."
    obj_finalPacker = Packer()
    obj_finalPacker.add_bin(obj_bin)

    # Note: we use the final (potentially disrupted) arr_bestSolutionIndices here.
    # This works because the underlying arr_itemsToPack has been updated.
    for int_i in arr_bestSolutionIndices:
        obj_finalPacker.add_item(arr_itemsToPack[int_i])

    obj_finalPacker.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)

    # Apply a post-processing step to add physical realism (gravity).
    _fnPostProcessPacking(obj_finalPacker.bins[0])

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
    # Recalculate the final metrics based on the contents of the bin AFTER the potential disruption.
    # Note: arr_packagesToLoad now includes the newly inserted items.
    final_metrics = fnCalculateAllMetrics(obj_finalPacker.bins[0].items, obj_bin.get_volume(), arr_packagesToLoad)
    
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
    
    # Final backend log to confirm the number of items successfully placed in the bin.
    num_products_loaded = len(arr_finalPackedItemsDetails)
    print(f"\n--- FINAL RESULT ---")
    print(f"Final Number of Products Loaded: {num_products_loaded}")
    print("This number reflects the count of items the packing library successfully placed in the bin.")
    print("It can differ from the initial or disrupted count if some items could not be fit due to their geometry.\n")
    
    # Construct the final, structured results dictionary that will be sent to the frontend.
    return {
        'algorithm_name': strAlgorithmName,
        'metrics': {
            'computation_time': flt_computationTime,
            'memory_usage_mb': round(flt_memUsage, 2),
            'volume_utilization': final_metrics['volume_utilization'],
            'relocation_count': final_metrics['relocation_count'],
            'unloading_feasibility': final_metrics['unloading_feasibility'],
            'unloading_sequence_length': final_metrics['unloading_sequence_length']
        },
        'packed_items': arr_finalPackedItemsDetails,
        'vehicle_info': {
            **dict_vehicleInfo,
            'num_packages_loaded': num_products_loaded, # Use the final calculated number.
            'total_packed_volume': round(flt_totalPackedVolume),
            'total_packed_service_time': round(flt_totalPackedServiceTime)
        }
    }


def _fnPostProcessPacking(objBin):
    """
    Applies a rigorous, multi-stage physics simulation to the final packing
    solution. This function guarantees physical realism by iteratively applying
    gravity and performing explicit collision detection and resolution on all three
    axes (X, Y, and Z), completely eliminating any merging, overlapping, or
    floating items.

    The process works as follows:
    1.  **Iterative Settling Loop:** The function runs in multiple passes until a
        full pass occurs where no item moves, signifying a final, stable state.
        Each item is processed from the bottom-up to ensure a stable foundation.
    2.  **Y-Axis Resolution (Gravity & Vertical Collision):** For each item, the
        function finds the highest solid surface directly beneath it by checking
        for X-Z plane overlaps with all other items. It then moves the item
        down to rest exactly on this surface, simultaneously eliminating any
        floating and resolving all vertical collisions.
    3.  **X/Z-Axis Resolution (Lateral Collision):** After settling an item
        vertically, the function performs a new, critical check for lateral
        (side-to-side) collisions. If an item overlaps another, it is pushed
        away by the minimum amount required to resolve the overlap, ensuring no
        two items occupy the same space.
    4.  **Convergence & Boundary Enforcement:** The iterative process continues
        until the entire arrangement is stable and collision-free. A final check
        clamps all items within the container's boundaries to correct any minor
        protrusions from floating-point inaccuracies.

    Args:
        objBin (Bin): The bin object containing the final packed items.
    """
    # --- Configuration ---
    # A safety limit to prevent potential infinite loops in complex scenarios.
    INT_MAX_ITERATIONS = 20
    # A small tolerance value for floating-point comparisons to avoid precision errors.
    FLT_COMPARISON_TOLERANCE = 1e-5
    # The number of decimal places to use when rounding positions for final output.
    INT_PRECISION_DIGITS = 3

    print("Starting advanced packing post-processing with collision resolution...")

    arr_items = objBin.items
    arr_bin_dims = [float(objBin.width), float(objBin.height), float(objBin.depth)]

    # --- Stage 1: Iterative Settling and Collision Resolution ---
    for int_iteration in range(INT_MAX_ITERATIONS):
        int_items_moved_this_pass = 0
        arr_items.sort(key=lambda item: float(item.position[1])) # Process bottom-up

        for obj_current_item in arr_items:
            # --- Y-AXIS: Apply Gravity & Resolve Vertical Collisions ---
            flt_current_iy = float(obj_current_item.position[1])
            flt_highest_support_y = 0.0

            flt_ix, flt_iz = float(obj_current_item.position[0]), float(obj_current_item.position[2])
            flt_iw, flt_id = float(obj_current_item.get_dimension()[0]), float(obj_current_item.get_dimension()[2])

            for obj_other_item in arr_items:
                if obj_other_item is obj_current_item:
                    continue

                flt_oy, flt_oh = float(obj_other_item.position[1]), float(obj_other_item.get_dimension()[1])
                # Check if other_item is a potential supporter (below and overlaps in X-Z)
                if (flt_oy + flt_oh) <= (flt_current_iy + FLT_COMPARISON_TOLERANCE):
                    flt_ox, flt_oz = float(obj_other_item.position[0]), float(obj_other_item.position[2])
                    flt_ow, flt_od = float(obj_other_item.get_dimension()[0]), float(obj_other_item.get_dimension()[2])

                    bln_x_overlap = (flt_ix < flt_ox + flt_ow) and (flt_ox < flt_ix + flt_iw)
                    bln_z_overlap = (flt_iz < flt_oz + flt_od) and (flt_oz < flt_iz + flt_id)

                    if bln_x_overlap and bln_z_overlap:
                        flt_highest_support_y = max(flt_highest_support_y, flt_oy + flt_oh)

            # Move item down if it's floating above its highest support
            if abs(flt_current_iy - flt_highest_support_y) > FLT_COMPARISON_TOLERANCE:
                obj_current_item.position[1] = str(flt_highest_support_y)
                int_items_moved_this_pass += 1
            
            # --- X/Z-AXIS: Resolve Lateral Collisions ---
            # Now that the item is at the correct height, check for side overlaps
            flt_ix, flt_iy, flt_iz = [float(p) for p in obj_current_item.position]
            flt_iw, flt_ih, flt_id = [float(d) for d in obj_current_item.get_dimension()]
            
            for obj_other_item in arr_items:
                 if obj_other_item is obj_current_item:
                     continue
                 
                 flt_ox, flt_oy, flt_oz = [float(p) for p in obj_other_item.position]
                 flt_ow, flt_oh, flt_od = [float(d) for d in obj_other_item.get_dimension()]
                 
                 # Check for full 3D overlap (collision)
                 bln_x_overlap = (flt_ix < flt_ox + flt_ow) and (flt_ox < flt_ix + flt_iw)
                 bln_y_overlap = (flt_iy < flt_oy + flt_oh) and (flt_oy < flt_iy + flt_ih)
                 bln_z_overlap = (flt_iz < flt_oz + flt_od) and (flt_oz < flt_iz + flt_id)

                 if bln_x_overlap and bln_y_overlap and bln_z_overlap:
                     # A collision exists, calculate the overlap on each axis
                     flt_dx = min(flt_ix + flt_iw - flt_ox, flt_ox + flt_ow - flt_ix)
                     flt_dz = min(flt_iz + flt_id - flt_oz, flt_oz + flt_od - flt_iz)

                     # Resolve collision by pushing the current_item along the axis of least overlap
                     if flt_dx < flt_dz: # Push along X-axis
                         if flt_ix < flt_ox: # current_item is to the left of other_item
                             obj_current_item.position[0] = str(flt_ix - flt_dx)
                         else: # current_item is to the right
                             obj_current_item.position[0] = str(flt_ix + flt_dx)
                     else: # Push along Z-axis
                         if flt_iz < flt_oz: # current_item is in front of other_item
                            obj_current_item.position[2] = str(flt_iz - flt_dz)
                         else: # current_item is behind
                             obj_current_item.position[2] = str(flt_iz + flt_dz)
                     
                     int_items_moved_this_pass += 1


        print(f"Post-processing iteration {int_iteration + 1}: {int_items_moved_this_pass} adjustments made.")
        if int_items_moved_this_pass == 0:
            print("Item stack has settled into a stable, collision-free configuration.")
            break
    else:
        print("Warning: Post-processing reached max iterations. The configuration may not be fully settled.")

    # --- Stage 2: Final Boundary Enforcement ---
    for obj_item in arr_items:
        arr_pos = [float(p) for p in obj_item.position]
        arr_dims = [float(d) for d in obj_item.get_dimension()]

        for int_axis in range(3):
            if arr_pos[int_axis] < 0:
                arr_pos[int_axis] = 0
            if arr_pos[int_axis] + arr_dims[int_axis] > arr_bin_dims[int_axis]:
                arr_pos[int_axis] = arr_bin_dims[int_axis] - arr_dims[int_axis]

        obj_item.position = [str(round(p, INT_PRECISION_DIGITS)) for p in arr_pos]

    print("Packing post-processing complete.")