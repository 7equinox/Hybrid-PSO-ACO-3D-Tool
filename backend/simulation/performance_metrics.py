"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
This module provides the functions to calculate all dependent variables
(performance metrics) as defined in the research methodology for Research
Questions 1 and 2. It evaluates a given packing solution against both
traditional space optimization (Volume Utilization) and the novel operational
unloading criteria (Relocation Count, Feasibility, Sequence Length). This
module is therefore central to addressing the study's Statement of the
Problem, which focuses on the gap in evaluating unloading efficiency.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import numpy as np

def fn_calculateAllMetrics(arrPackedItems, fltBinVolume, arrAllPackagesInfo):
    """
    Serves as the central function to compute all performance metrics for a
    given packed solution. This single point of evaluation ensures that each
    algorithm (PSO, ACO, Hybrid) is judged by the same consistent and
    unbiased criteria, enabling a fair and direct comparison.

    Args:
        arrPackedItems (list): The list of 'Item' objects successfully packed by an algorithm.
        fltBinVolume (float): The total volume of the container (vehicle).
        arrAllPackagesInfo (list): A list of dictionaries containing metadata for all packages.

    Returns:
        dict: A dictionary containing all calculated performance metrics.
    """
    # --- METRIC 1: VOLUME UTILIZATION ---
    # This directly implements 'Equation 3' from the methodology. It measures how
    # efficiently the algorithm utilizes the available 3D space. While a traditional
    # packing goal, it serves as an important baseline to ensure that improvements in
    # unloading feasibility do not come at a significant cost to packing density.
    flt_totalPackedVolume = sum(item.get_volume() for item in arrPackedItems)
    flt_volumeUtilization = float((flt_totalPackedVolume / fltBinVolume) * 100) if fltBinVolume > 0 else 0.0

    # To simulate a realistic delivery, we must first establish the required unloading order.
    # A lookup map is created for quick access to package metadata (like the stop_id),
    # and from this, a sorted delivery sequence is generated.
    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    set_packedStops = {dict_packagesInfoMap.get(item.name, {}).get('stop_id') for item in arrPackedItems}
    arr_deliverySequence = sorted(list(filter(None, set_packedStops)))

    # --- METRICS 2, 3, 4: UNLOADING SIMULATION ---
    # The following metrics are derived from a detailed simulation of the unloading process.
    # This simulation is the core mechanism that allows us to answer the research questions
    # about operational efficiency—the very factor that standard packing algorithms often ignore.
    tpl_unloadingResults = _simulateUnloading(arrPackedItems, arr_deliverySequence, dict_packagesInfoMap)
    int_relocationCount, int_unloadingSequenceLength, bln_isFeasible = tpl_unloadingResults

    # Consolidate all metrics into a single results object.
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': int_relocationCount,
        # This directly represents the Feasibility Rate calculation from the methodology.
        'unloading_feasibility': "Feasible" if bln_isFeasible else "Infeasible",
        'unloading_sequence_length': int_unloadingSequenceLength
    }

def _simulateUnloading(arrPackedItems, arrDeliverySequence, dictPackagesInfoMap):
    """
    Simulates the physical, step-by-step process of unloading items from the vehicle.
    This function is the primary tool for evaluating the operational viability of a
    packing solution. It determines if items can be retrieved in the correct order
    and quantifies the effort required (relocations and total moves).

    Assumption: The delivery vehicle is unloaded from the front opening (largest X-coordinate).

    Returns:
        tuple: (relocation_count, sequence_length, is_feasible)
    """
    # A trivial case: an empty vehicle is perfectly feasible with zero effort.
    if not arrPackedItems:
        return 0, 0, True

    # Create a mutable copy of the items to simulate their removal from the bin.
    dict_itemsInBin = {item.name: item for item in arrPackedItems}

    int_relocations = 0
    int_sequenceLength = 0

    # Process each stop in the pre-defined delivery sequence, mimicking a driver's route.
    for str_targetStopId in arrDeliverySequence:
        # Identify all items currently in the bin that are destined for this stop.
        arr_itemsForThisStopIds = [
            item.name for item in dict_itemsInBin.values()
            if dictPackagesInfoMap.get(item.name, {}).get('stop_id') == str_targetStopId
        ]
        
        # At any given stop, items must be unloaded from most to least accessible
        # (i.e., from front to back of the vehicle).
        arr_itemsForThisStopIds.sort(
            key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
            reverse=True
        )

        for str_targetItemId in arr_itemsForThisStopIds:
            if str_targetItemId not in dict_itemsInBin:
                # This can happen if the item was already removed as part of a relocation.
                continue

            obj_targetItem = dict_itemsInBin[str_targetItemId]
            
            # --- Blocker Identification ---
            # This is the critical logic that addresses the Statement of the Problem.
            # We identify which other items physically block access to the target item.
            # A "blocker" is an item positioned in front of the target (larger x-coordinate)
            # and overlapping with it in the Y-Z plane. A high number of blockers indicates
            # an inefficient packing arrangement that will require extra work during unloading.
            arr_blockingItemsIds = []
            flt_tx, flt_ty, flt_tz = map(float, obj_targetItem.position)
            flt_tdx, flt_tdy, flt_tdz = map(float, obj_targetItem.get_dimension())

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId: continue
                flt_ox, flt_oy, flt_oz = map(float, obj_otherItem.position)
                flt_odx, flt_ody, flt_odz = map(float, obj_otherItem.get_dimension())

                bln_isInFront = flt_ox > flt_tx
                bln_yOverlap = (flt_ty < flt_oy + flt_ody) and (flt_oy < flt_ty + flt_tdy)
                bln_zOverlap = (flt_tz < flt_oz + flt_odz) and (flt_oz < flt_tz + flt_odz)

                if bln_isInFront and bln_yOverlap and bln_zOverlap:
                    arr_blockingItemsIds.append(str_otherId)

            # If blockers exist, they must be "relocated" (removed from the bin first).
            # Each relocation adds to the relocation_count (a measure of inefficiency)
            # and the sequence_length (a measure of total effort).
            if arr_blockingItemsIds:
                arr_blockingItemsIds.sort(
                    key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
                    reverse=True
                )
                for str_blockerId in arr_blockingItemsIds:
                    if str_blockerId in dict_itemsInBin:
                        int_relocations += 1
                        int_sequenceLength += 1 # A relocation is one operational move.
                        del dict_itemsInBin[str_blockerId]

            # After all blockers are cleared, the target item can be retrieved.
            if str_targetItemId in dict_itemsInBin:
                int_sequenceLength += 1 # A successful retrieval is also one operational move.
                del dict_itemsInBin[str_targetItemId]

    # --- Feasibility Check ---
    # Unloading is considered "feasible" if and only if the bin is empty at the end.
    # If any items remain, it signifies a deadlock where some items were impossible
    # to access, representing a critical operational failure of the packing solution.
    bln_isFeasible = not dict_itemsInBin

    return int_relocations, int_sequenceLength, bln_isFeasible