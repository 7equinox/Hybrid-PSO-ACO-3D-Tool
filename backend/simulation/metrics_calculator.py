"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
This module provides functions to calculate all dependent variables (performance
metrics) defined in the research methodology for Research Questions 1 and 2.
It evaluates a given packing solution against loading and unloading criteria.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import numpy as np

def calculateAllMetrics(arr_packedItems, flt_binVolume, arr_allPackagesInfo):
    """
    The master function to compute all performance metrics for a given solution.
    This function centralizes the evaluation process, ensuring that each
    algorithm is judged by the same criteria.
    """
    # --- METRIC 1: VOLUME UTILIZATION ---
    # This directly implements 'Equation 3' from the methodology to measure how
    # efficiently the algorithm uses the available 3D space. A higher percentage
    # indicates a better packing density.
    flt_totalPackedVolume = sum(item.get_volume() for item in arr_packedItems)
    flt_volumeUtilization = float((flt_totalPackedVolume / flt_binVolume) * 100) if flt_binVolume > 0 else 0.0

    # A lookup map is created for quick access to package metadata (e.g., stop_id),
    # which is required for simulating the delivery sequence.
    dict_packagesInfoMap = {p['id']: p for p in arr_allPackagesInfo}

    # Generate the delivery sequence based on the items that were successfully packed.
    # A realistic route plan would involve visiting stops in a sorted order.
    set_packedStops = {dict_packagesInfoMap.get(item.name, {}).get('stop_id') for item in arr_packedItems}
    arr_deliverySequence = sorted(list(filter(None, set_packedStops)))

    # --- METRICS 2, 3, 4: UNLOADING SIMULATION ---
    # These metrics are derived from a detailed simulation of the unloading process.
    # This simulation is crucial for answering research questions about operational
    # efficiency, which standard packing algorithms often ignore.
    tpl_unloadingResults = _simulateUnloading(arr_packedItems, arr_deliverySequence, dict_packagesInfoMap)
    int_relocationCount, int_unloadingSequenceLength, bln_isFeasible = tpl_unloadingResults

    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': int_relocationCount,
        'unloading_feasibility': "Feasible" if bln_isFeasible else "Infeasible", # Implements 'Equation 2'
        'unloading_sequence_length': int_unloadingSequenceLength
    }

def _simulateUnloading(arr_packedItems, arr_deliverySequence, dict_packagesInfoMap):
    """
    A private helper function that simulates the physical process of unloading items
    from the vehicle to calculate feasibility, relocation count, and sequence length.
    It assumes items are unloaded from the front of the cargo space (largest X-coordinate).
    """
    if not arr_packedItems:
        # An empty vehicle is trivially feasible with zero relocations.
        return 0, 0, True

    # Create a copy of the items to simulate their removal from the bin.
    dict_itemsInBin = {item.name: item for item in arr_packedItems}

    int_relocations = 0
    int_sequenceLength = 0

    # Process each stop in the pre-defined delivery sequence.
    for str_targetStopId in arr_deliverySequence:
        # Identify all items in the bin destined for the current stop.
        arr_itemsForThisStopIds = [
            item.name for item in dict_itemsInBin.values()
            if dict_packagesInfoMap.get(item.name, {}).get('stop_id') == str_targetStopId
        ]

        # Items at a single stop must be unloaded from most to least accessible.
        # Accessibility is defined by the x-coordinate (position[0]), descending.
        arr_itemsForThisStopIds.sort(
            key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
            reverse=True
        )

        for str_targetItemId in arr_itemsForThisStopIds:
            if str_targetItemId not in dict_itemsInBin:
                continue # Item was already removed as part of a relocation.

            obj_targetItem = dict_itemsInBin[str_targetItemId]
            arr_blockingItemsIds = []

            # Determine which other items physically block access to the target item.
            # A "blocker" is defined as any item positioned in front of the target
            # (larger x-coordinate) and overlapping in the Y-Z plane.
            flt_tx, flt_ty, flt_tz = map(float, obj_targetItem.position)
            flt_tdx, flt_tdy, flt_tdz = map(float, obj_targetItem.get_dimension())

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId:
                    continue

                flt_ox, flt_oy, flt_oz = map(float, obj_otherItem.position)
                flt_odx, flt_ody, flt_odz = map(float, obj_otherItem.get_dimension())

                bln_isInFront = flt_ox > flt_tx
                bln_yOverlap = (flt_ty < flt_oy + flt_ody) and (flt_oy < flt_ty + flt_tdy)
                bln_zOverlap = (flt_tz < flt_oz + flt_odz) and (flt_oz < flt_tz + flt_odz)

                if bln_isInFront and bln_yOverlap and bln_zOverlap:
                    arr_blockingItemsIds.append(str_otherId)

            # If there are blockers, they must be "relocated" (removed).
            # These are also removed from most- to least-accessible to simulate
            # a realistic unloading process.
            arr_blockingItemsIds.sort(
                key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
                reverse=True
            )

            for str_blockerId in arr_blockingItemsIds:
                if str_blockerId in dict_itemsInBin:
                    int_relocations += 1
                    int_sequenceLength += 1 # A relocation is one move.
                    del dict_itemsInBin[str_blockerId]

            # After clearing blockers, remove the target item.
            if str_targetItemId in dict_itemsInBin:
                int_sequenceLength += 1 # A successful retrieval is one move.
                del dict_itemsInBin[str_targetItemId]

    # Unloading is considered "feasible" if and only if the bin is empty at the end.
    # If any items remain, it means a deadlock occurred.
    bln_isFeasible = not dict_itemsInBin

    return int_relocations, int_sequenceLength, bln_isFeasible