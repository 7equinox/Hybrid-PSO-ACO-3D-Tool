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
    
    # FIX: Explicitly cast item volume to float to prevent Decimal/float conflicts.
    flt_totalPackedVolume = sum(float(item.get_volume()) for item in arrPackedItems)
    # FIX: Ensure fltBinVolume is treated as a float.
    flt_volumeUtilization = float((flt_totalPackedVolume / float(fltBinVolume)) * 100) if float(fltBinVolume) > 0 else 0.0

    # To evaluate unloading, we must first establish the required unloading order.
    # We create a delivery sequence based on the `stop_id` for each package, simulating
    # a driver's fixed route.
    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    set_packedStops = {dict_packagesInfoMap.get(item.name, {}).get('stop_id') for item in arrPackedItems}
    arr_deliverySequence = sorted(list(filter(None, set_packedStops)))

    # --- METRIC 2: THE UNLOADING SIMULATION ---
    # This metric is derived from a detailed, step-by-step simulation of the physical
    # unloading process. This simulation is the core mechanism that allows us to quantitatively
    # answer the research questions about operational efficiency.
    int_relocationCount = _fnSimulateUnloading(arrPackedItems, arr_deliverySequence, dict_packagesInfoMap)


    # Consolidate all metrics into a single, structured results object.
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': int_relocationCount,
    }


def _fnSimulateUnloading(arrPackedItems, arrDeliverySequence, dictPackagesInfoMap):
    """
    Simulates the physical, step-by-step process of a delivery driver unloading items
    from the vehicle. This function is the primary tool for evaluating the operational
    efficiency of a packing arrangement. It quantifies the extra work (relocations) required.
    If an unloading deadlock occurs (items are trapped), it returns an infinite penalty.

    Physical Assumption: The delivery vehicle is unloaded from a single opening at the front
    (defined as the position with the largest X-coordinate).

    Returns:
        int: The total number of relocations. Returns float('inf') if unloading is not feasible.
    """
    # An empty vehicle is perfectly feasible with zero work.
    if not arrPackedItems:
        return 0

    # Create a mutable copy of the items to simulate their physical removal from the vehicle.
    dict_itemsInBin = {item.name: item for item in arrPackedItems}

    int_relocations = 0      # Counts only the unnecessary moves.

    # Process each stop in the pre-defined delivery sequence, mimicking a driver's route.
    for str_targetStopId in arrDeliverySequence:
        # First, identify all items currently inside the vehicle that are destined for this stop.
        arr_itemsForThisStopIds = [
            item.name for item in dict_itemsInBin.values()
            if dictPackagesInfoMap.get(item.name, {}).get('stop_id') == str_targetStopId
        ]

        # A driver must unload items from front-to-back AND top-to-bottom. This sort order
        # correctly prioritizes items with the largest X coordinate (closest to door) first,
        # then the largest Y coordinate (highest up). This creates a vertical, batch-like unload.
        # FIX: Ensure all position components used for sorting are cast to float.
        arr_itemsForThisStopIds.sort(
            key=lambda item_id: (
                float(dict_itemsInBin[item_id].position[0]), # Primary sort: X-axis (front)
                float(dict_itemsInBin[item_id].position[1])  # Secondary sort: Y-axis (top)
            ),
            reverse=True # `reverse=True` because larger X is front, larger Y is top.
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
            # FIX: Ensure all dimensions and positions are cast to float before calculations.
            flt_tx, flt_ty, flt_tz = map(float, obj_targetItem.position)
            flt_tdx, flt_tdy, flt_tdz = map(float, obj_targetItem.get_dimension())

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId: continue # An item cannot block itself.

                # FIX: Ensure all dimensions and positions are cast to float before calculations.
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
                # FIX: Ensure position used for sorting is cast to float.
                arr_blockingItemsIds.sort(
                    key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
                    reverse=True
                )
                for str_blockerId in arr_blockingItemsIds:
                    if str_blockerId in dict_itemsInBin:
                        int_relocations += 1      # This is an extra, wasted move.
                        del dict_itemsInBin[str_blockerId] # Simulate removing the blocker.

            # After all blockers are cleared, the target item can be retrieved.
            if str_targetItemId in dict_itemsInBin:
                del dict_itemsInBin[str_targetItemId] # Simulate removing the target item.

    # --- Final Feasibility Check ---
    # If any items remain, it signifies a "deadlock" scenario where some items
    # were permanently trapped. This is a catastrophic operational failure and is
    # heavily penalized by returning an infinite relocation count.
    if dict_itemsInBin: # If the dictionary is NOT empty, it's infeasible.
        return float('inf')

    return int_relocations


def fnGenerateUnloadingSequence(arrPackedItems, arrAllPackagesInfo):
    """
    Performs the same unloading simulation as _fnSimulateUnloading, but instead
    of returning a simple count, it generates a detailed, step-by-step event log
    for creating an animation on the frontend.
    
    Returns:
        list: A list of event dictionaries (e.g., {'action': 'relocate', 'item_id': 'xyz'}).
    """
    if not arrPackedItems:
        return []

    dict_itemsInBin = {item.name: item for item in arrPackedItems}
    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    set_packedStops = {dict_packagesInfoMap.get(item.name, {}).get('stop_id') for item in arrPackedItems}
    arr_deliverySequence = sorted(list(filter(None, set_packedStops)))
    
    arr_eventLog = []

    for str_targetStopId in arr_deliverySequence:
        arr_itemsForThisStopIds = [
            item.name for item in dict_itemsInBin.values()
            if dict_packagesInfoMap.get(item.name, {}).get('stop_id') == str_targetStopId
        ]
        # Match the updated sorting logic: Front-to-back (X), then Top-to-bottom (Y)
        # FIX: Ensure all position components used for sorting are cast to float.
        arr_itemsForThisStopIds.sort(
            key=lambda item_id: (
                float(dict_itemsInBin[item_id].position[0]),
                float(dict_itemsInBin[item_id].position[1])
            ),
            reverse=True
        )

        for str_targetItemId in arr_itemsForThisStopIds:
            if str_targetItemId not in dict_itemsInBin:
                continue

            obj_targetItem = dict_itemsInBin[str_targetItemId]
            arr_eventLog.append({'action': 'target', 'item_id': str_targetItemId})
            
            arr_blockingItemsIds = []
            # FIX: Ensure all dimensions and positions are cast to float before calculations.
            flt_tx, flt_ty, flt_tz = map(float, obj_targetItem.position)
            flt_tdx, flt_tdy, flt_tdz = map(float, obj_targetItem.get_dimension())

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId: continue
                # FIX: Ensure all dimensions and positions are cast to float before calculations.
                flt_ox, flt_oy, flt_oz = map(float, obj_otherItem.position)
                flt_odx, flt_ody, flt_odz = map(float, obj_otherItem.get_dimension())
                bln_isInFront = flt_ox > flt_tx
                bln_yOverlap = (flt_ty < flt_oy + flt_ody) and (flt_oy < flt_ty + flt_tdy)
                bln_zOverlap = (flt_tz < flt_oz + flt_odz) and (flt_oz < flt_tz + flt_odz)

                if bln_isInFront and bln_yOverlap and bln_zOverlap:
                    arr_blockingItemsIds.append(str_otherId)
            
            if arr_blockingItemsIds:
                # FIX: Ensure position used for sorting is cast to float.
                arr_blockingItemsIds.sort(
                    key=lambda item_id: float(dict_itemsInBin[item_id].position[0]),
                    reverse=True
                )
                for str_blockerId in arr_blockingItemsIds:
                    if str_blockerId in dict_itemsInBin:
                        arr_eventLog.append({'action': 'relocate', 'item_id': str_blockerId})
                        del dict_itemsInBin[str_blockerId]

            if str_targetItemId in dict_itemsInBin:
                arr_eventLog.append({'action': 'deliver', 'item_id': str_targetItemId})
                del dict_itemsInBin[str_targetItemId]

    return arr_eventLog