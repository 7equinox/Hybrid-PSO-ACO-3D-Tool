"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Performance Metrics Calculation

Purpose of this file:
This module contains the precise mathematical implementations for calculating the
dependent variables as defined in the research methodology for Research
Questions 1 and 2. It evaluates a given packing solution against two competing
dimensions:
1.  **Traditional Space Optimization:** How densely are items packed (Volume Utilization)?
2.  **Novel Operational Efficiency:** How easy and efficient is the unloading
    process (Relocation Count, Feasibility, Sequence Length)?
By centralizing these calculations, we ensure that every algorithm is judged by
the exact same, consistent, and unbiased criteria. This module is therefore
fundamental to addressing the study's central Statement of the Problem, which
focuses on the critical gap in evaluating unloading feasibility in packing research.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
import numpy as np # Used for its robust numerical operations.


def fnCalculateAllMetrics(arrPackedItems, fltBinVolume, arrAllPackagesInfo):
    """
    Serves as the main function to compute all defined performance metrics for a
    single, completed packing solution. It acts as a single point of evaluation,
    guaranteeing that PSO, ACO, and the Hybrid algorithm are all measured against
    the exact same standards, which is essential for a fair and direct comparison.

    Args:
        arrPackedItems (list): The list of 'Item' objects that were successfully packed.
        fltBinVolume (float): The total available volume of the vehicle's container.
        arrAllPackagesInfo (list): The list of dictionaries containing metadata for all packages.

    Returns:
        dict: A dictionary containing all the calculated performance metrics for the given solution.
    """
    # --- METRIC 1: VOLUME UTILIZATION ---
    # This metric directly implements 'Equation 3' from the methodology. It answers the
    # classic packing question: "How much of the available space did we use?" While it is a
    # traditional metric, it serves as a crucial baseline. It allows us to verify that any
    # improvements in unloading efficiency do not come at an unacceptable cost to packing density.
    flt_totalPackedVolume = sum(item.get_volume() for item in arrPackedItems)
    flt_volumeUtilization = float((flt_totalPackedVolume / fltBinVolume) * 100) if fltBinVolume > 0 else 0.0

    # To evaluate unloading, we must first establish the required unloading order.
    # We create a delivery sequence based on the `stop_id` for each package, simulating
    # a driver's fixed route.
    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    set_packedStops = {dict_packagesInfoMap.get(item.name, {}).get('stop_id') for item in arrPackedItems}
    arr_deliverySequence = sorted(list(filter(None, set_packedStops)))

    # --- METRICS 2, 3, & 4: THE UNLOADING SIMULATION ---
    # The following metrics are the novel contribution of this research. They are derived from
    # a detailed, step-by-step simulation of the physical unloading process. This simulation
    # is the core mechanism that allows us to quantitatively answer the research questions
    # about operational efficiency—the very factor that standard packing algorithms typically ignore.
    tpl_unloadingResults = _fnSimulateUnloading(arrPackedItems, arr_deliverySequence, dict_packagesInfoMap)
    # The original sequence length from the simulation is discarded in favor of the explicit formula.
    int_relocationCount, _, bln_isFeasible = tpl_unloadingResults

    # As per the methodology, the Unloading Sequence Length is the total number of actions required.
    # This is the sum of correctly retrieving every loaded package plus every extra relocation move.
    num_products_loaded = len(arrPackedItems)
    int_unloadingSequenceLength = num_products_loaded + int_relocationCount


    # Consolidate all metrics into a single, structured results object.
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': int_relocationCount,
        # This boolean directly informs the 'Feasibility Rate' calculation in the methodology.
        'unloading_feasibility': "Feasible" if bln_isFeasible else "Infeasible",
        'unloading_sequence_length': int_unloadingSequenceLength
    }


def _fnSimulateUnloading(arrPackedItems, arrDeliverySequence, dictPackagesInfoMap):
    """
    Simulates the physical, step-by-step process of a delivery driver unloading items
    from the vehicle. This function is the primary tool for evaluating the operational
    viability and efficiency of a packing arrangement. It determines whether all items can be
    retrieved in their correct delivery order and precisely quantifies the extra work
    (relocations) and total effort (sequence length) required.

    Physical Assumption: The delivery vehicle is unloaded from a single opening at the front
    (defined as the position with the largest X-coordinate).

    Returns:
        tuple: A tuple containing (relocation_count, sequence_length, is_feasible).
    """
    # An empty vehicle is trivially easy to unload. It is perfectly feasible with zero work.
    if not arrPackedItems:
        return 0, 0, True

    # Create a mutable copy of the items to simulate their physical removal from the vehicle.
    dict_itemsInBin = {item.name: item for item in arrPackedItems}

    int_relocations = 0      # Counts only the unnecessary moves.
    int_sequenceLength = 0   # Counts ALL moves (retrievals + relocations).

    # Process each stop in the pre-defined delivery sequence, mimicking a driver's route.
    for str_targetStopId in arrDeliverySequence:
        # First, identify all items currently inside the vehicle that are destined for this stop.
        arr_itemsForThisStopIds = [
            item.name for item in dict_itemsInBin.values()
            if dictPackagesInfoMap.get(item.name, {}).get('stop_id') == str_targetStopId
        ]

        # A driver must unload items from front-to-back. We sort the target items for this stop
        # by their X-position to simulate this physical constraint.
        arr_itemsForThisStopIds.sort(
            key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
            reverse=True # `reverse=True` because larger X means closer to the front.
        )

        # Now, attempt to retrieve each target item one by one.
        for str_targetItemId in arr_itemsForThisStopIds:
            # Check if the item is still in the bin. It might have already been
            # moved out as a blocker for a previous item.
            if str_targetItemId not in dict_itemsInBin:
                continue

            obj_targetItem = dict_itemsInBin[str_targetItemId]

            # --- Blocker Identification ---
            # This is the critical logic that directly addresses the Statement of the Problem.
            # We must identify which OTHER items are physically blocking access to our target item.
            # An item is considered a "blocker" if it is positioned IN FRONT of the target
            # (has a larger x-coordinate) AND overlaps with it in the vertical (Y) and
            # horizontal (Z) planes. A high number of blockers signifies a poorly designed
            # packing arrangement that creates significant extra work for the driver.
            arr_blockingItemsIds = []
            flt_tx, flt_ty, flt_tz = map(float, obj_targetItem.position)
            flt_tdx, flt_tdy, flt_tdz = map(float, obj_targetItem.get_dimension())

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId: continue # An item cannot block itself.

                flt_ox, flt_oy, flt_oz = map(float, obj_otherItem.position)
                flt_odx, flt_ody, flt_odz = map(float, obj_otherItem.get_dimension())

                bln_isInFront = flt_ox > flt_tx # Is it closer to the door?
                bln_yOverlap = (flt_ty < flt_oy + flt_ody) and (flt_oy < flt_ty + flt_tdy) # Does it overlap vertically?
                bln_zOverlap = (flt_tz < flt_oz + flt_odz) and (flt_oz < flt_tz + flt_odz) # Does it overlap sideways?

                if bln_isInFront and bln_yOverlap and bln_zOverlap:
                    arr_blockingItemsIds.append(str_otherId)

            # If any blockers were found, they must be "relocated" (removed from the bin first).
            if arr_blockingItemsIds:
                # Relocate blockers from front-to-back to be efficient.
                arr_blockingItemsIds.sort(
                    key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
                    reverse=True
                )
                for str_blockerId in arr_blockingItemsIds:
                    if str_blockerId in dict_itemsInBin:
                        int_relocations += 1      # This is an extra, wasted move.
                        int_sequenceLength += 1   # Every move (good or bad) adds to the total effort.
                        del dict_itemsInBin[str_blockerId] # Simulate removing the blocker.

            # After all blockers are cleared, the target item can be retrieved.
            if str_targetItemId in dict_itemsInBin:
                int_sequenceLength += 1   # A successful retrieval is one operational move.
                del dict_itemsInBin[str_targetItemId] # Simulate removing the target item.

    # --- Final Feasibility Check ---
    # The unloading process is considered "feasible" if, and only if, the vehicle is
    # completely empty at the end. If any items remain, it signifies a "deadlock" scenario
    # where some items were permanently trapped behind others. This represents a catastrophic
    # operational failure for the packing solution.
    bln_isFeasible = not dict_itemsInBin # If the dictionary is empty, it's feasible.

    return int_relocations, int_sequenceLength, bln_isFeasible
