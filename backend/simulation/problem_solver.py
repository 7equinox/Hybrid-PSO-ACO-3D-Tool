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
import numpy as np # <-- IMPORT NUMPY
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# Import dependent modules
from backend.data_management.data_loader import getSimulationDataForVehicle
from backend.simulation.metrics_calculator import calculateAllMetrics

# CORRECTED: Import the exception from its new, neutral location.
from backend.simulation.exceptions import CancelledException 

from backend.algorithms.pso_algorithm import runPsoAlgorithm
from backend.algorithms.aco_algorithm import runAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import runHybridPsoAcoAlgorithm

def solveLoadingProblem(str_algorithmName, flt_capacityCm3, cancellation_flag):
    """
    The main orchestrator function for a single simulation run. It fetches the
    full simulation dataset, sets up the 3D bin packing problem, invokes the
    correct algorithm, and structures the final results. It now accepts a cancellation flag
    which it will check periodically and pass down to the algorithm.
    """
    # --- IMMEDIATE PRE-EMPTIVE CHECK ---
    if cancellation_flag['is_cancelled']:
        raise CancelledException()

    print("Simulation started: Now loading required dataset...")

    dict_vehicleInfo, arr_packagesInfo = getSimulationDataForVehicle(flt_capacityCm3, cancellation_flag)

    if (not dict_vehicleInfo or not arr_packagesInfo):
        if cancellation_flag['is_cancelled']: raise CancelledException()
        return {'error': 'Could not get vehicle info or package data was missing.'}

    # ==============================================================================
    # === NEW: VOLUME-CONSTRAINED STRATIFIED SAMPLING ==============================
    # To prevent memory errors on large datasets (e.g., >70k items) and to
    # significantly speed up computation, we sample the data down to a manageable size.
    # This directly implements the "Sampling Method" from Chapter 3.
    # ==============================================================================
    MAX_SAMPLE_SIZE = 1000 # Set a hard limit to prevent memory issues.
    if len(arr_packagesInfo) > MAX_SAMPLE_SIZE:
        print(f"Original dataset has {len(arr_packagesInfo)} items. Applying sampling to reduce to {MAX_SAMPLE_SIZE}.")

        # 1. Stratification based on volume
        volumes = [p['volume'] for p in arr_packagesInfo]
        p33, p66 = np.percentile(volumes, [33.3, 66.7])
        
        small_items = [p for p in arr_packagesInfo if p['volume'] <= p33]
        medium_items = [p for p in arr_packagesInfo if p33 < p['volume'] <= p66]
        large_items = [p for p in arr_packagesInfo if p['volume'] > p66]

        random.shuffle(small_items)
        random.shuffle(medium_items)
        random.shuffle(large_items)

        # 2. Proportional Allocation & 3. Constrained Random Selection
        sampled_packages = []
        current_volume = 0.0
        
        # Interleave selections to maintain proportions
        iter_small = iter(small_items)
        iter_medium = iter(medium_items)
        iter_large = iter(large_items)
        
        while len(sampled_packages) < MAX_SAMPLE_SIZE:
            added_in_cycle = False
            
            # Try to add a small item
            try:
                item = next(iter_small)
                if current_volume + item['volume'] <= flt_capacityCm3:
                    sampled_packages.append(item)
                    current_volume += item['volume']
                    added_in_cycle = True
            except StopIteration: pass
            if len(sampled_packages) >= MAX_SAMPLE_SIZE: break

            # Try to add a medium item
            try:
                item = next(iter_medium)
                if current_volume + item['volume'] <= flt_capacityCm3:
                    sampled_packages.append(item)
                    current_volume += item['volume']
                    added_in_cycle = True
            except StopIteration: pass
            if len(sampled_packages) >= MAX_SAMPLE_SIZE: break

            # Try to add a large item
            try:
                item = next(iter_large)
                if current_volume + item['volume'] <= flt_capacityCm3:
                    sampled_packages.append(item)
                    current_volume += item['volume']
                    added_in_cycle = True
            except StopIteration: pass
            
            # If we've exhausted all item lists or can't fit any more, stop.
            if not added_in_cycle:
                break
        
        # Replace the original package list with our new, smaller, feasible sample
        arr_packagesInfo = sampled_packages
        print(f"Sampling complete. New problem size: {len(arr_packagesInfo)} items.")
    # ==============================================================================
    # === END OF SAMPLING IMPLEMENTATION ===========================================
    # ==============================================================================


    # --- DYNAMIC CONSTRAINT IMPLEMENTATION ---
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
    def evaluateSolution(arr_itemOrderIndices):
        if cancellation_flag['is_cancelled']:
            raise CancelledException()

        obj_packer = Packer()
        obj_freshBin = Bin(obj_bin.name, obj_bin.width, obj_bin.height, obj_bin.depth, obj_bin.max_weight)
        obj_packer.add_bin(obj_freshBin)

        for int_i in arr_itemOrderIndices:
            obj_packer.add_item(arr_itemsToPack[int_i])
        
        obj_packer.pack(bigger_first=False) 
        
        arr_packedItems = obj_packer.bins[0].items
        if not arr_packedItems:
            return 0, float('inf'), float('inf')
        
        set_packedItemIds = {item.name for item in arr_packedItems}
        arr_finalPackagesInfo = [p for p in arr_packagesToLoad if p['id'] in set_packedItemIds]

        dict_metrics = calculateAllMetrics(
            arr_packedItems,
            obj_bin.get_volume(),
            arr_finalPackagesInfo
        )
        
        if dict_metrics['unloading_feasibility'] == 'Infeasible':
             return 0, float('inf'), float('inf')

        return (
            dict_metrics['volume_utilization'],
            dict_metrics['relocation_count'],
            dict_metrics['unloading_sequence_length']
        )

    # --- ALGORITHM SELECTION AND EXECUTION ---
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
    flt_memUsage, (arr_bestSolutionIndices, tpl_bestFitness) = memory_usage(
        (func_algorithm, (arr_itemsToPack, arr_packagesToLoad, evaluateSolution, cancellation_flag)),
        retval=True, max_usage=True, interval=0.1
    )
    flt_computationTime = round(time.time() - tm_startTime, 2)
    
    if not arr_bestSolutionIndices:
        print("Algorithm returned no solution, likely due to cancellation.")
        return {
            'algorithm_name': str_algorithmName,
            'metrics': {
                'computation_time': flt_computationTime, 'memory_usage_mb': round(flt_memUsage, 2),
                'volume_utilization': 0, 'relocation_count': 'N/A',
                'unloading_feasibility': 'Cancelled',
                'unloading_sequence_length': 'N/A'
            },
            'packed_items': [],
            'vehicle_info': {
                **dict_vehicleInfo, 'num_packages_loaded': 0,
                'total_packed_volume': 0, 'total_packed_service_time': 0
            }
        }

    # --- POST-EXPERIMENTATION: DATA CONSOLIDATION ---
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