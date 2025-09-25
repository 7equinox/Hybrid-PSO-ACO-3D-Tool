"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
This module acts as the orchestrator for the 'Experimentation Stage'.
It takes a problem definition (algorithm, items, container) and executes
the selected optimization algorithm, capturing and returning all performance
and scalability metrics for analysis.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import time
import random
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# Import dependent modules
from backend.data_management.data_loader import getSimulationDataForVehicle
from backend.simulation.metrics_calculator import calculateAllMetrics
from backend.algorithms.pso_algorithm import runPsoAlgorithm
from backend.algorithms.aco_algorithm import runAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import runHybridPsoAcoAlgorithm

def solveLoadingProblem(str_algorithmName, flt_capacityCm3):
    """
    The main orchestrator function for a single simulation run. It fetches the
    full simulation dataset, sets up the 3D bin packing problem, invokes the
    correct algorithm, and structures the final results.
    """
    dict_vehicleInfo, arr_packagesInfo = getSimulationDataForVehicle(flt_capacityCm3)

    if (not dict_vehicleInfo or not arr_packagesInfo):
        return {'error': 'Could not get vehicle info or package data was missing.'}

    # --- DYNAMIC CONSTRAINT IMPLEMENTATION ---
    # As per the methodology, this section simulates last-minute changes by
    # randomly removing 10-20% of items before optimization. This tests the
    # algorithm's adaptability.
    if (len(arr_packagesInfo) > 1):
        int_numToRemove = int(len(arr_packagesInfo) * random.uniform(0.1, 0.2))
        arr_packagesToLoad = random.sample(arr_packagesInfo, len(arr_packagesInfo) - int_numToRemove)
    else:
        arr_packagesToLoad = arr_packagesInfo
    
    # Convert package data into py3dbp Item objects for the packing library.
    arr_itemsToPack = [
        Item(p['id'], p['width'], p['height'], p['depth'], 1) for p in arr_packagesToLoad
    ]
    
    # Define the container (Bin) using vehicle dimensions.
    obj_bin = Bin(
        dict_vehicleInfo['id'],
        dict_vehicleInfo['width'],
        dict_vehicleInfo['height'],
        dict_vehicleInfo['depth'],
        1e6 # A very large max weight, as our problem is volume-constrained.
    )

    # --- FITNESS FUNCTION ---
    # This is the core evaluation function passed to each algorithm. It takes a
    # potential solution (an ordering of items), simulates packing, and returns
    # the multi-objective fitness values (volume, relocations, sequence length).
    def evaluateSolution(arr_itemOrderIndices):
        obj_packer = Packer()
        # Create a fresh bin for each evaluation to ensure independent trials.
        obj_freshBin = Bin(obj_bin.name, obj_bin.width, obj_bin.height, obj_bin.depth, obj_bin.max_weight)
        obj_packer.add_bin(obj_freshBin)

        for int_i in arr_itemOrderIndices:
            obj_packer.add_item(arr_itemsToPack[int_i])
        
        obj_packer.pack(bigger_first=False) # Use the library's packing heuristic.
        
        arr_packedItems = obj_packer.bins[0].items
        if not arr_packedItems:
            # Return a very poor fitness for solutions that pack nothing.
            return 0, float('inf'), float('inf')
        
        # Get the original package data for only the items that were successfully packed.
        set_packedItemIds = {item.name for item in arr_packedItems}
        arr_finalPackagesInfo = [p for p in arr_packagesToLoad if p['id'] in set_packedItemIds]

        # Calculate all metrics as defined in the methodology.
        dict_metrics = calculateAllMetrics(
            arr_packedItems,
            obj_bin.get_volume(),
            arr_finalPackagesInfo
        )
        
        # Penalize infeasible solutions heavily in the fitness score.
        if dict_metrics['unloading_feasibility'] == 'Infeasible':
             return 0, float('inf'), float('inf')

        return (
            dict_metrics['volume_utilization'],
            dict_metrics['relocation_count'],
            dict_metrics['unloading_sequence_length']
        )

    # --- ALGORITHM SELECTION AND EXECUTION ---
    # Maps the algorithm name from the UI to the corresponding function.
    dict_algorithmMap = {
        'PSO': runPsoAlgorithm,
        'ACO': runAcoAlgorithm,
        'PSO-ACO': runHybridPsoAcoAlgorithm
    }
    func_algorithm = dict_algorithmMap.get(str_algorithmName)

    if not func_algorithm:
        return {'error': 'Invalid algorithm name specified.'}
    
    tm_startTime = time.time()
    
    # --- SCALABILITY METRICS MEASUREMENT ---
    # The 'memory_profiler' library is used here to capture peak memory usage,
    # and the 'time' module captures computation time, directly addressing
    # the scalability metrics for Research Question 3.
    flt_memUsage, (arr_bestSolutionIndices, tpl_bestFitness) = memory_usage(
        (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, evaluateSolution)),
        retval=True, max_usage=True, interval=0.1
    )
    flt_computationTime = round(time.time() - tm_startTime, 2)
    
    # --- POST-EXPERIMENTATION: DATA CONSOLIDATION ---
    # After finding the best solution, re-pack it to get the final state
    # and format all data for display and interpretation.
    obj_finalPacker = Packer()
    obj_finalPacker.add_bin(obj_bin)
    for int_i in arr_bestSolutionIndices:
        obj_finalPacker.add_item(arr_itemsToPack[int_i])
    obj_finalPacker.pack(bigger_first=False)

    arr_finalPackedItemsDetails = []
    flt_totalPackedVolume = 0
    flt_totalPackedServiceTime = 0
    
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
    
    # Structure the final results dictionary to be sent to the frontend.
    return {
        'algorithm_name': str_algorithmName,
        'metrics': {
            'computation_time': flt_computationTime, 'memory_usage_mb': round(flt_memUsage, 2),
            'volume_utilization': tpl_bestFitness[0], 'relocation_count': tpl_bestFitness[1],
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