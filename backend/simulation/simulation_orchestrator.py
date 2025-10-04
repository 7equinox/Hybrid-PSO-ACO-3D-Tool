"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
This module acts as the orchestrator for the 'Experimentation Stage' as
defined in the research methodology. It is the core of the experimental
process, responsible for setting up a defined problem (algorithm, items,
container), applying the crucial sampling and dynamic constraints, executing
the selected optimization algorithm, and capturing all performance and
scalability metrics required for analysis to answer the research questions.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import time
import random
import numpy as np
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# Import dependent modules from within the application.
from backend.data_management.data_manager import fn_getSimulationDataForVehicle
from backend.simulation.performance_metrics import fn_calculateAllMetrics
from backend.simulation.custom_exceptions import CancelledException
from backend.algorithms.pso_algorithm import fn_runPsoAlgorithm
from backend.algorithms.aco_algorithm import fn_runAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import fn_runHybridPsoAcoAlgorithm

def fn_orchestrateSimulationRun(strAlgorithmName, fltCapacityCm3, dictCancellationFlag):
    """
    This is the main function for a single experimental run. It orchestrates
    the entire process from data loading to algorithm execution and result
    consolidation, ensuring each step aligns with the research methodology.
    """
    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    print("Simulation started: Loading full dataset for the given capacity...")
    # Fetch the complete dataset associated with the selected vehicle capacity.
    dict_vehicleInfo, arr_packagesInfo = fn_getSimulationDataForVehicle(fltCapacityCm3, dictCancellationFlag)

    # Halt if the required data could not be loaded.
    if not dict_vehicleInfo or not arr_packagesInfo:
        if dictCancellationFlag['is_cancelled']: raise CancelledException()
        return {'error': 'Could not get vehicle info or package data was missing.'}

    # --- SAMPLING METHOD IMPLEMENTATION (from Chapter 3 Methodology) ---
    # The full dataset for larger vehicles can contain over 82,155 items, which
    # is computationally infeasible to process on standard hardware (e.g., causing
    # massive memory allocation failures). To overcome this, we implement the
    # 'Volume-Constrained Stratified Random Sampling' method. This creates smaller,
    # yet representative and solvable, problem instances, enabling a fair benchmark
    # across all algorithms without compromising the integrity of the data.
    MAX_SAMPLE_SIZE =1000 # A hard limit to prevent out-of-memory errors.
    if len(arr_packagesInfo) > MAX_SAMPLE_SIZE:
        print(f"Original dataset has {len(arr_packagesInfo)} items. Applying sampling to reduce to {MAX_SAMPLE_SIZE}.")

        # Step 1: Stratification. Items are categorized into Small, Medium, and Large based on volume percentiles.
        # This ensures the sample maintains the same general distribution of item sizes as the original dataset.
        arr_volumes = [p['volume'] for p in arr_packagesInfo]
        flt_p33, flt_p66 = np.percentile(arr_volumes, [33.3, 66.7])
        arr_smallItems = [p for p in arr_packagesInfo if p['volume'] <= flt_p33]
        arr_mediumItems = [p for p in arr_packagesInfo if flt_p33 < p['volume'] <= flt_p66]
        arr_largeItems = [p for p in arr_packagesInfo if p['volume'] > flt_p66]

        # Shuffle each stratum to ensure random selection.
        random.shuffle(arr_smallItems)
        random.shuffle(arr_mediumItems)
        random.shuffle(arr_largeItems)

        # Steps 2 & 3: Proportional Allocation & Constrained Random Selection.
        # We iteratively build a new sample by adding items from each stratum. The process
        # is constrained by both the max sample size and the total vehicle volume,
        # guaranteeing a feasible and standardized problem instance for the experiment.
        arr_sampledPackages = []
        flt_currentVolume = 0.0
        iter_small = iter(arr_smallItems)
        iter_medium = iter(arr_mediumItems)
        iter_large = iter(arr_largeItems)

        while len(arr_sampledPackages) < MAX_SAMPLE_SIZE:
            bln_addedInCycle = False
            # Attempt to add items proportionally by iterating through the strata.
            for iterator in [iter_small, iter_medium, iter_large]:
                try:
                    obj_item = next(iterator)
                    # The crucial volume constraint check.
                    if flt_currentVolume + obj_item['volume'] <= fltCapacityCm3:
                        arr_sampledPackages.append(obj_item)
                        flt_currentVolume += obj_item['volume']
                        bln_addedInCycle = True
                except StopIteration:
                    pass # This stratum is exhausted.
                if len(arr_sampledPackages) >= MAX_SAMPLE_SIZE: break
            
            # If a full pass through all strata adds no new items, stop.
            if not bln_addedInCycle: break
        
        # The original large package list is now replaced by our smaller, feasible sample.
        arr_packagesInfo = arr_sampledPackages
        print(f"Sampling complete. New problem size: {len(arr_packagesInfo)} items.")


    # --- DYNAMIC CONSTRAINT IMPLEMENTATION (from Chapter 3 Methodology) ---
    # To test the algorithms' adaptability to real-world disruptions (like last-minute
    # order changes), a random subset (10-20%) of items is removed from the problem
    # instance just before optimization begins.
    # if len(arr_packagesInfo) > 1:
    #     int_numToRemove = int(len(arr_packagesInfo) * random.uniform(0.1, 0.2))
    #     arr_packagesToLoad = random.sample(arr_packagesInfo, len(arr_packagesInfo) - int_numToRemove)
    # else:
    arr_packagesToLoad = arr_packagesInfo

    # Convert the problem data into the format required by the `py3dbp` library.
    arr_itemsToPack = [Item(p['id'], p['width'], p['height'], p['depth'], 1) for p in arr_packagesToLoad]
    
    obj_bin = Bin(
        dict_vehicleInfo['id'],
        dict_vehicleInfo['width'],
        dict_vehicleInfo['height'],
        dict_vehicleInfo['depth'],
        1e6 # Max weight is set high as our problem is volume-constrained, not weight-constrained.
    )

    # --- FITNESS FUNCTION (Answering RQ1 & RQ2) ---
    # This function is the heart of the evaluation. It takes a potential solution (an item packing order)
    # from an algorithm and calculates its quality based on the key research metrics: Volume Utilization,
    # Relocation Count, and Unloading Sequence Length. This single function ensures all three
    # algorithms are judged by the exact same, unbiased criteria.
    def fn_evaluateSolution(arrItemOrderIndices):
        # Allow the process to be cancelled gracefully mid-evaluation.
        if dictCancellationFlag['is_cancelled']:
            raise CancelledException()

        # A fresh packer and bin are created for each evaluation to ensure independence.
        obj_packer = Packer()
        obj_freshBin = Bin(obj_bin.name, obj_bin.width, obj_bin.height, obj_bin.depth, obj_bin.max_weight)
        obj_packer.add_bin(obj_freshBin)

        # Add items to the packer in the specific order dictated by the algorithm's solution.
        for int_i in arrItemOrderIndices:
            obj_packer.add_item(arr_itemsToPack[int_i])
        
        # Run the underlying packing heuristic.
        obj_packer.pack(bigger_first=False) 
        
        arr_packedItems = obj_packer.bins[0].items
        if not arr_packedItems:
            # If the packing order results in no items being packed, return the worst-case fitness.
            return 0, float('inf'), float('inf')
        
        # Delegate the calculation of all metrics to the dedicated performance_metrics module.
        dict_metrics = fn_calculateAllMetrics(
            arr_packedItems,
            obj_bin.get_volume(),
            arr_packagesToLoad
        )
        
        # An 'Infeasible' solution is heavily penalized. This guides the search
        # away from packing arrangements that result in deadlocks during unloading.
        if dict_metrics['unloading_feasibility'] == 'Infeasible':
             return 0, float('inf'), float('inf')

        # Return the multi-objective fitness values.
        return (
            dict_metrics['volume_utilization'],
            dict_metrics['relocation_count'],
            dict_metrics['unloading_sequence_length']
        )

    # --- ALGORITHM SELECTION AND EXECUTION ---
    # Select and run the appropriate algorithm based on the user's choice.
    dict_algorithmMap = {
        'PSO': fn_runPsoAlgorithm,
        'ACO': fn_runAcoAlgorithm,
        'PSO-ACO': fn_runHybridPsoAcoAlgorithm
    }
    func_algorithm = dict_algorithmMap.get(strAlgorithmName)

    if not func_algorithm:
        return {'error': 'Invalid algorithm name specified.'}
    
    # --- SCALABILITY METRICS MEASUREMENT (Answering RQ3) ---
    # The `memory_profiler` library is used to measure the peak RAM usage, and `time`
    # is used to measure the total execution time. These two metrics are crucial for
    # evaluating the scalability of each algorithm.
    tm_startTime = time.time()
    # The memory_usage function wraps the algorithm call to monitor its resource consumption.
    flt_memUsage, (arr_bestSolutionIndices, tpl_bestFitness) = memory_usage(
        (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, fn_evaluateSolution, dictCancellationFlag)),
        retval=True, max_usage=True, interval=0.1
    )
    flt_computationTime = round(time.time() - tm_startTime, 2)
    
    # --- POST-EXPERIMENTATION: DATA CONSOLIDATION ---
    # After the algorithm finishes, this section takes the best solution it found
    # and prepares a comprehensive result object to be sent back to the frontend for display.
    obj_finalPacker = Packer()
    obj_finalPacker.add_bin(obj_bin)
    for int_i in arr_bestSolutionIndices:
        obj_finalPacker.add_item(arr_itemsToPack[int_i])
    obj_finalPacker.pack(bigger_first=False)

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
    # Augment the original package data with the final packed positions.
    for obj_item in obj_finalPacker.bins[0].items:
        dict_originalPackage = next((p for p in arr_packagesToLoad if p['id'] == obj_item.name), None)
        if dict_originalPackage:
            arr_pos = [float(p) for p in obj_item.position]
            arr_finalPackedItemsDetails.append({
                **dict_originalPackage,
                "position_x": arr_pos[0], "position_y": arr_pos[1], "position_z": arr_pos[2]
            })
            flt_totalPackedVolume += dict_originalPackage['volume']
            flt_totalPackedServiceTime += dict_originalPackage['service_time']
    
    # Structure the final, comprehensive results dictionary.
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