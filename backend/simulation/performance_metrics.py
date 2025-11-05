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
    # The simulation now generates an event log and a relocation count simultaneously.
    dict_unloadingSimulationResult = fnGenerateUnloadingSequence(arrPackedItems, arr_deliverySequence, dict_packagesInfoMap)
    int_relocationCount = dict_unloadingSimulationResult['relocation_count']
    arr_unloadingSequence = dict_unloadingSimulationResult['event_log']

    # Consolidate all metrics into a single, structured results object.
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': int_relocationCount,
        'unloading_sequence': arr_unloadingSequence # Pass the detailed log for visualization.
    }


def fnGenerateUnloadingSequence(arrPackedItems, arrDeliverySequence, dictPackagesInfoMap):
    """
    Simulates the unloading process step-by-step to generate a detailed event log
    for frontend animation and to count relocations accurately. This revised
    function implements a more realistic "vertical batch" unloading from the front
    and simulates gravity to settle items after removals.

    Physical Assumption: The vehicle is unloaded from the front (largest X-coordinate).
    Unloading proceeds from Top-to-Bottom for items in the current front-most "slice".

    Returns:
        dict: A dictionary containing the 'event_log' (a list of actions) and the
              'relocation_count'. Returns an infinite count on failure.
    """
    if not arrPackedItems:
        return {'event_log': [], 'relocation_count': 0}

    # Use a dictionary of dictionaries for mutable, detailed item data.
    dict_itemsInBin = {
        item.name: {
            'id': item.name,
            'pos': [float(p) for p in item.position],
            'dims': [float(d) for d in item.get_dimension()],
            'stop_id': dictPackagesInfoMap.get(item.name, {}).get('stop_id'),
            'item_obj': item 
        } for item in arrPackedItems
    }
    
    arr_eventLog = []
    int_relocations = 0

    for str_targetStopId in arrDeliverySequence:
        while True: # Loop until all items for this stop are delivered or found unreachable.
            arr_itemsForThisStopIds = [
                item['id'] for item in dict_itemsInBin.values() if item['stop_id'] == str_targetStopId
            ]
            if not arr_itemsForThisStopIds: break # No more items for this stop, move to the next.

            # Identify the single most accessible item for the current stop.
            # "Most accessible" means: largest X (closest to door), then largest Y (highest up).
            str_targetItemId = max(
                arr_itemsForThisStopIds, 
                key=lambda item_id: (dict_itemsInBin[item_id]['pos'][0], dict_itemsInBin[item_id]['pos'][1])
            )
            
            obj_targetItem = dict_itemsInBin[str_targetItemId]
            arr_eventLog.append({'action': 'target', 'item_id': str_targetItemId})

            # --- Blocker Identification ---
            arr_blockingItemsIds = []
            flt_tx, flt_ty, flt_tz = obj_targetItem['pos']
            flt_tdx, flt_tdy, flt_tdz = obj_targetItem['dims']

            for str_otherId, obj_otherItem in dict_itemsInBin.items():
                if str_otherId == str_targetItemId: continue

                flt_ox, flt_oy, flt_oz = obj_otherItem['pos']
                flt_odx, flt_ody, flt_odz = obj_otherItem['dims']

                bln_isInFront = flt_ox > flt_tx
                bln_yOverlap = (flt_ty < flt_oy + flt_ody) and (flt_oy < flt_ty + flt_tdy)
                bln_zOverlap = (flt_tz < flt_oz + flt_odz) and (flt_oz < flt_tz + flt_odz)

                if bln_isInFront and bln_yOverlap and bln_zOverlap:
                    arr_blockingItemsIds.append(str_otherId)

            # If blockers are found, they must be relocated.
            if arr_blockingItemsIds:
                arr_blockingItemsIds.sort(
                    key=lambda item_id: dict_itemsInBin[item_id]['pos'][0], reverse=True
                )
                for str_blockerId in arr_blockingItemsIds:
                    if str_blockerId in dict_itemsInBin:
                        int_relocations += 1
                        arr_eventLog.append({'action': 'relocate', 'item_id': str_blockerId})
                        del dict_itemsInBin[str_blockerId]
            
            # After clearing blockers, deliver the target item.
            if str_targetItemId in dict_itemsInBin:
                arr_eventLog.append({'action': 'deliver', 'item_id': str_targetItemId})
                del dict_itemsInBin[str_targetItemId]
            
            # --- MODIFICATION: Apply Gravity Simulation After Every Removal ---
            # After removing an item (or items), check for any items that are now unsupported and settle them.
            bln_items_settled = True
            while bln_items_settled: # Loop until no more items can settle in a pass.
                bln_items_settled = False
                arr_sorted_items = sorted(dict_itemsInBin.values(), key=lambda i: i['pos'][1])

                for item_to_check in arr_sorted_items:
                    flt_ix, flt_iy, flt_iz = item_to_check['pos']
                    flt_iw, flt_ih, flt_id = item_to_check['dims']
                    
                    flt_highest_support_y = 0.0
                    for other_item in dict_itemsInBin.values():
                        if other_item['id'] == item_to_check['id']: continue
                        
                        flt_ox, flt_oy, flt_oz = other_item['pos']
                        flt_ow, flt_oh, flt_od = other_item['dims']

                        # Check if 'other_item' is below 'item_to_check' and overlaps in X-Z plane
                        if (flt_oy + flt_oh) <= flt_iy + 1e-4:
                            overlap_x = (flt_ix < flt_ox + flt_ow) and (flt_ox < flt_ix + flt_iw)
                            overlap_z = (flt_iz < flt_oz + flt_od) and (flt_oz < flt_iz + flt_id)
                            if overlap_x and overlap_z:
                                flt_highest_support_y = max(flt_highest_support_y, flt_oy + flt_oh)
                    
                    if flt_iy > flt_highest_support_y + 1e-4: # If item is floating
                        item_to_check['pos'][1] = flt_highest_support_y
                        bln_items_settled = True
                        arr_eventLog.append({
                            'action': 'settle',
                            'item_id': item_to_check['id'],
                            'new_y_pos': flt_highest_support_y
                        })
    
    # Final feasibility check
    if dict_itemsInBin:
        return {'event_log': arr_eventLog, 'relocation_count': float('inf')}

    return {'event_log': arr_eventLog, 'relocation_count': int_relocations}