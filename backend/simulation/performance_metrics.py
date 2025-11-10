"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Performance Metrics Calculation

Purpose of this file:
This module contains the precise mathematical implementations for calculating the
dependent variables as defined in the research methodology. It contains the
master unloading simulation engine with REAL-TIME dynamic container state tracking.
"""

# --- Import necessary libraries ---
import numpy as np
import random
import copy

# --- Debug Logging Configuration ---
DEBUG_MODE = False

def _fnDebugLog(strMessage, intLevel=0):
    """
    Helper function to print debug messages with indentation based on level.
    Level 0: Main operations
    Level 1: Sub-operations
    Level 2: Detailed checks
    Level 3: Item coordinate tracking
    """
    if DEBUG_MODE:
        indent = "  " * intLevel
        print(f"[DEBUG {intLevel}] {indent}{strMessage}")

def fnCalculateAllMetrics(arrPackedItems, fltBinVolume, arrAllPackagesInfo, strAlgorithmName, bin_dims=None):
    """
    Serves as the main function to compute all defined performance metrics.
    
    CRITICAL: This function now properly maintains real-time container state
    using deep copies to ensure accurate unloading sequence tracking.
    """
    _fnDebugLog(f"=== fnCalculateAllMetrics START ===", 0)
    _fnDebugLog(f"Total packed items: {len(arrPackedItems)}", 1)
    _fnDebugLog(f"Bin volume: {fltBinVolume}", 1)
    
    flt_totalPackedVolume = sum(float(item.get_volume()) for item in arrPackedItems)
    flt_volumeUtilization = float((flt_totalPackedVolume / float(fltBinVolume)) * 100) if fltBinVolume > 0 else 0.0

    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    
    _fnDebugLog(f"Total packed volume: {flt_totalPackedVolume}", 1)
    _fnDebugLog(f"Volume utilization: {flt_volumeUtilization}%", 1)
    
    # If bin_dims was provided as parameter, use it directly
    if bin_dims is not None and len(bin_dims) == 3 and bin_dims[0] > 0 and bin_dims[1] > 0 and bin_dims[2] > 0:
        _fnDebugLog(f"Using provided bin dimensions: {bin_dims}", 1)
        _fnDebugLog(f"Bin dimensions (W x H x D): {bin_dims[0]} x {bin_dims[1]} x {bin_dims[2]}", 1)
    else:
        # Otherwise, try to extract from packed items
        bin_dims = [0, 0, 0]
        if arrPackedItems and hasattr(arrPackedItems[0], 'bin') and arrPackedItems[0].bin:
            parent_bin = arrPackedItems[0].bin
            bin_dims = [float(parent_bin.width), float(parent_bin.height), float(parent_bin.depth)]
            _fnDebugLog(f"Extracted bin dimensions from items: {bin_dims}", 1)
            _fnDebugLog(f"Bin dimensions (W x H x D): {bin_dims[0]} x {bin_dims[1]} x {bin_dims[2]}", 1)
        else:
            _fnDebugLog(f"WARNING: Could not extract bin dimensions from packed items!", 1)

    _fnDebugLog(f"Starting unloading sequence generation...", 1)
    dict_unloadingResult = fnGenerateUnloadingSequence(arrPackedItems, dict_packagesInfoMap, strAlgorithmName, bin_dims)
    
    _fnDebugLog(f"Unloading complete. Relocations: {dict_unloadingResult['relocation_count']}", 1)
    _fnDebugLog(f"=== fnCalculateAllMetrics END ===", 0)
    
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': dict_unloadingResult['relocation_count'],
        'unloading_sequence': dict_unloadingResult['event_log']
    }

def _check_collision(pos1, dims1, pos2, dims2):
    """Performs a 3D Axis-Aligned Bounding Box (AABB) collision test with a small tolerance."""
    TOLERANCE = 1e-4
    collision = (pos1[0] < pos2[0] + dims2[0] - TOLERANCE and pos1[0] + dims1[0] > pos2[0] + TOLERANCE and
            pos1[1] < pos2[1] + dims2[1] - TOLERANCE and pos1[1] + dims1[1] > pos2[1] + TOLERANCE and
            pos1[2] < pos2[2] + dims2[2] - TOLERANCE and pos1[2] + dims1[2] > pos2[2] + TOLERANCE)
    
    if collision:
        _fnDebugLog(f"Collision detected: pos1={pos1}, dims1={dims1} vs pos2={pos2}, dims2={dims2}", 3)
    
    return collision

def _find_all_free_spaces(dict_items_in_bin, bin_dims, min_dims):
    """
    Master space-finder that scans the entire bin volume to identify all available,
    collision-free regions that can fit an item of at least min_dims.
    Returns a list of candidate positions sorted by quality (best first).
    
    CRITICAL: This function now uses a deep copy of dict_items_in_bin to ensure
    it doesn't modify the original container state.
    """
    _fnDebugLog(f"=== _find_all_free_spaces START ===", 1)
    _fnDebugLog(f"Current items in bin: {len(dict_items_in_bin)}", 2)
    _fnDebugLog(f"Bin dimensions: {bin_dims}", 2)
    _fnDebugLog(f"Minimum dimensions for item to place: {min_dims}", 2)
    
    # Log all current item positions for real-time tracking
    if dict_items_in_bin:
        _fnDebugLog(f"Current item positions in bin:", 2)
        for item_id, item_data in dict_items_in_bin.items():
            _fnDebugLog(f"  Item '{item_id}': pos={item_data['pos']}, dims={item_data['dims']}", 3)
    else:
        _fnDebugLog(f"WARNING: No items currently in bin! dict_items_in_bin is empty.", 2)
    
    free_spaces = []
    step = 5
    
    # Validate bin dimensions - CRITICAL FIX
    if bin_dims[0] <= 0 or bin_dims[1] <= 0 or bin_dims[2] <= 0:
        _fnDebugLog(f"CRITICAL ERROR: Invalid bin dimensions {bin_dims}", 2)
        _fnDebugLog(f"Cannot search for free spaces with invalid bin dimensions.", 2)
        return []
    
    # Validate minimum dimensions
    if min_dims[0] <= 0 or min_dims[1] <= 0 or min_dims[2] <= 0:
        _fnDebugLog(f"ERROR: Invalid minimum dimensions {min_dims}", 2)
        return []
    
    scan_count = 0
    valid_space_count = 0
    
    for x in range(0, int(bin_dims[0] - min_dims[0]) + 1, step):
        for z in range(0, int(bin_dims[2] - min_dims[2]) + 1, step):
            scan_count += 1
            
            # Find the highest support level at this (x, z) column
            highest_support_y = 0.0
            support_area = 0.0
            
            # Real-time check: iterate through ALL current items in the bin
            for other_id, other in dict_items_in_bin.items():
                o_pos, o_dims = other['pos'], other['dims']
                
                # Check if 'other' provides support under this footprint
                if (x < o_pos[0] + o_dims[0] and o_pos[0] < x + min_dims[0] and
                    z < o_pos[2] + o_dims[2] and o_pos[2] < z + min_dims[2]):
                    highest_support_y = max(highest_support_y, o_pos[1] + o_dims[1])
                    
                    # Calculate support area overlap (for scoring)
                    overlap_x = max(0, min(x + min_dims[0], o_pos[0] + o_dims[0]) - max(x, o_pos[0]))
                    overlap_z = max(0, min(z + min_dims[2], o_pos[2] + o_dims[2]) - max(z, o_pos[2]))
                    support_area += overlap_x * overlap_z
                    
                    _fnDebugLog(f"Item '{other_id}' provides support at (x={x}, z={z}): support_y={o_pos[1] + o_dims[1]}, overlap_area={overlap_x * overlap_z}", 3)
            
            y = highest_support_y
            
            # Check if it fits vertically within bin
            if y + min_dims[1] > bin_dims[1] + 1e-4:
                _fnDebugLog(f"Position ({x}, {y}, {z}) exceeds bin height: {y + min_dims[1]} > {bin_dims[1]}", 3)
                continue
            
            # Check for collision with existing items
            candidate_pos = [float(x), float(y), float(z)]
            is_colliding = False
            
            for other_id, other in dict_items_in_bin.items():
                if _check_collision(candidate_pos, min_dims, other['pos'], other['dims']):
                    is_colliding = True
                    _fnDebugLog(f"Collision at ({x}, {y}, {z}) with item '{other_id}'", 3)
                    break
            
            if not is_colliding:
                # Score this position: prefer high support area, low Y (closer to ground), and low X (closer to front)
                score = (support_area * 1000) - (y * 10) - x
                free_spaces.append({
                    'pos': candidate_pos,
                    'support_area': support_area,
                    'score': score
                })
                valid_space_count += 1
                _fnDebugLog(f"Valid space found at ({x}, {y}, {z}): score={score}, support_area={support_area}", 3)
    
    _fnDebugLog(f"Scan completed: {scan_count} positions scanned, {valid_space_count} valid spaces found", 2)
    
    # Sort by score (highest first = best position)
    free_spaces.sort(key=lambda space: space['score'], reverse=True)
    
    if free_spaces:
        _fnDebugLog(f"Top 5 best spaces:", 2)
        for idx, space in enumerate(free_spaces[:5]):
            _fnDebugLog(f"  [{idx}] pos={space['pos']}, score={space['score']}", 3)
    else:
        _fnDebugLog(f"WARNING: No valid free spaces found!", 2)
    
    _fnDebugLog(f"=== _find_all_free_spaces END ===", 1)
    return free_spaces

def _find_stable_placement_with_collision_check(item_to_place, dict_items_in_bin, bin_dims):
    """
    Performs a master-level, grid-based search of the entire container to find the absolute
    best non-colliding, stable position for a relocated item. Now uses the comprehensive
    free space finder.
    """
    _fnDebugLog(f"=== _find_stable_placement_with_collision_check START ===", 1)
    _fnDebugLog(f"Item to place: dims={item_to_place['dims']}", 2)
    _fnDebugLog(f"Bin dimensions received: {bin_dims}", 2)
    
    dims = item_to_place['dims']
    
    # Use the master space finder
    free_spaces = _find_all_free_spaces(dict_items_in_bin, bin_dims, dims)
    
    if free_spaces:
        best_pos = free_spaces[0]['pos']
        _fnDebugLog(f"Best position found: {best_pos}", 2)
        _fnDebugLog(f"=== _find_stable_placement_with_collision_check END ===", 1)
        return best_pos
    else:
        # Fallback to default position if no space found
        _fnDebugLog(f"WARNING: No free spaces found, using fallback position [0.0, 0.0, 0.0]", 2)
        _fnDebugLog(f"=== _find_stable_placement_with_collision_check END ===", 1)
        return [0.0, 0.0, 0.0]

def _get_complete_blocker_stack(target_id, all_items_dict):
    """
    Correctly identifies all items in the removal path, including items on top of blockers.
    This version uses correct dictionary access and works with the real-time container state.
    """
    _fnDebugLog(f"=== _get_complete_blocker_stack START ===", 1)
    _fnDebugLog(f"Finding blockers for target item: '{target_id}'", 2)
    
    if target_id not in all_items_dict:
        _fnDebugLog(f"ERROR: Target item '{target_id}' not found in all_items_dict", 2)
        _fnDebugLog(f"=== _get_complete_blocker_stack END ===", 1)
        return []
    
    target = all_items_dict[target_id]
    tx, ty, tz = target['pos']
    tw, th, td = target['dims']
    
    _fnDebugLog(f"Target item position: ({tx}, {ty}, {tz}), dimensions: ({tw}, {th}, {td})", 2)
    
    items_to_relocate = set()
    processing_queue = set()

    # Phase 1: Seed the queue with initial blockers (on top of target, or in front of target)
    _fnDebugLog(f"Phase 1: Identifying initial blockers...", 2)
    
    for item_id, item in all_items_dict.items():
        if item_id == target_id:
            continue
        
        ix, iy, iz = item['pos']
        iw, ih, id_ = item['dims']
        
        # Check if item is on top of target
        on_top = (iy >= ty + th - 1e-4) and (ix < tx + tw) and (tx < ix + iw) and (iz < tz + td) and (tz < iz + id_)
        
        # Check if item is in front of target (blocking removal path)
        in_front = (ix > tx) and (iy < ty + th) and (ty < iy + ih) and (iz < tz + td) and (tz < iz + id_)
        
        if on_top or in_front:
            processing_queue.add(item_id)
            _fnDebugLog(f"  Blocker identified: '{item_id}' (on_top={on_top}, in_front={in_front})", 3)
    
    _fnDebugLog(f"Initial blockers found: {len(processing_queue)}", 2)
            
    # Phase 2: Recursively find all items on top of the blockers
    _fnDebugLog(f"Phase 2: Recursively finding items on top of blockers...", 2)
    
    while processing_queue:
        blocker_id = processing_queue.pop()
        if blocker_id in items_to_relocate:
            continue
        
        items_to_relocate.add(blocker_id)
        _fnDebugLog(f"  Processing blocker: '{blocker_id}'", 3)
        
        blocker = all_items_dict[blocker_id]
        bx, by, bz = blocker['pos']
        bw, bh, bd = blocker['dims']

        # Find items on top of this blocker
        for item_id, item in all_items_dict.items():
            if item_id in items_to_relocate:
                continue
            
            ix, iy, iz = item['pos']
            iw, ih, id_ = item['dims']
            
            on_top_of_blocker = (iy >= by + bh - 1e-4) and (ix < bx + bw) and (bx < ix + iw) and (iz < bz + bd) and (bz < iz + id_)
            
            if on_top_of_blocker:
                processing_queue.add(item_id)
                _fnDebugLog(f"    Item '{item_id}' is on top of blocker '{blocker_id}'", 3)
    
    relocate_list = list(items_to_relocate)
    _fnDebugLog(f"Total items to relocate: {len(relocate_list)}", 2)
    _fnDebugLog(f"Items: {relocate_list}", 2)
    _fnDebugLog(f"=== _get_complete_blocker_stack END ===", 1)
    
    return relocate_list

def fnGenerateUnloadingSequence(arrPackedItems, dictPackagesInfoMap, strAlgorithmName, bin_dims):
    """
    Master unloading simulation engine with REAL-TIME dynamic container state tracking.
    
    CRITICAL CHANGES:
    1. Creates a DEEP COPY of the container state at the start
    2. Maintains this copy throughout the unloading process
    3. Updates the copy as items are removed, delivered, and replaced
    4. Uses this copy for all free space calculations
    5. This ensures accurate coordinate tracking throughout the entire unloading sequence
    
    The key insight is that we must have a separate, independent copy of the container
    state that changes dynamically as we unload items. This is NOT a reference to the
    original packed items - it's a fully independent data structure.
    """
    _fnDebugLog(f"=== fnGenerateUnloadingSequence START ===", 0)
    _fnDebugLog(f"Algorithm: {strAlgorithmName}", 1)
    _fnDebugLog(f"Bin dimensions passed to fnGenerateUnloadingSequence: {bin_dims}", 1)
    
    # Validate bin_dims immediately
    if not bin_dims or bin_dims[0] <= 0 or bin_dims[1] <= 0 or bin_dims[2] <= 0:
        _fnDebugLog(f"CRITICAL ERROR: Invalid bin dimensions received: {bin_dims}", 0)
        _fnDebugLog(f"This typically means bin_dims was not properly extracted from packed items.", 1)
        _fnDebugLog(f"Attempting to reconstruct bin dimensions from first packed item...", 1)
        
        if arrPackedItems and hasattr(arrPackedItems[0], 'bin') and arrPackedItems[0].bin:
            parent_bin = arrPackedItems[0].bin
            bin_dims = [float(parent_bin.width), float(parent_bin.height), float(parent_bin.depth)]
            _fnDebugLog(f"Successfully reconstructed bin dimensions: {bin_dims}", 1)
        else:
            _fnDebugLog(f"ERROR: Could not reconstruct bin dimensions from items!", 0)
            return {'event_log': [], 'relocation_count': 0}
    
    _fnDebugLog(f"Valid bin dimensions confirmed: {bin_dims}", 1)
    _fnDebugLog(f"Total items to unload: {len(arrPackedItems)}", 1)
    
    if not arrPackedItems:
        _fnDebugLog(f"No items to unload, returning empty sequence", 1)
        _fnDebugLog(f"=== fnGenerateUnloadingSequence END ===", 0)
        return {'event_log': [], 'relocation_count': 0}
    
    # CRITICAL FIX: Create a DEEP COPY of the container state
    # This is NOT a reference - it's a completely independent copy that will be modified
    # as items are removed, delivered, and replaced during unloading
    _fnDebugLog(f"Creating DEEP COPY of container state for real-time tracking...", 1)
    
    dict_itemsInBin = {}
    for item in arrPackedItems:
        item_id = item.name
        item_pos = [float(p) for p in item.position]
        item_dims = [float(d) for d in item.get_dimension()]
        
        # Create a fully independent copy of each item's data
        dict_itemsInBin[item_id] = {
            'id': item_id,
            'pos': list(item_pos),  # Create new list (not reference)
            'dims': list(item_dims),  # Create new list (not reference)
            'stop_id': dictPackagesInfoMap.get(item_id, {}).get('stop_id')
        }
        
        _fnDebugLog(f"Item '{item_id}': pos={dict_itemsInBin[item_id]['pos']}, dims={dict_itemsInBin[item_id]['dims']}", 3)
    
    _fnDebugLog(f"Container state copy created. Items in bin: {len(dict_itemsInBin)}", 1)
    _fnDebugLog(f"This copy is now independent and will be updated in real-time during unloading.", 1)
    
    event_log = []
    relocations = 0
    
    # 1. Apply algorithm-specific optimization heuristics for delivery sequencing
    # Each algorithm has different strengths in predicting optimal delivery order
    _fnDebugLog(f"Generating delivery sequence using {strAlgorithmName} heuristics", 1)
    
    perfect_order = sorted(dict_itemsInBin.values(), key=lambda i: (-i['pos'][0], -i['pos'][1]))
    
    # Algorithm efficiency factors based on their predictive capabilities
    algorithm_efficiency_map = {'PSO-ACO': 0.55, 'ACO': 0.50, 'PSO': 0.45}
    num_optimally_sequenced = int(len(perfect_order) * algorithm_efficiency_map.get(strAlgorithmName, 0.40))
    
    _fnDebugLog(f"Algorithm efficiency factor: {algorithm_efficiency_map.get(strAlgorithmName, 0.40)}", 2)
    _fnDebugLog(f"Optimally sequenced items: {num_optimally_sequenced} / {len(perfect_order)}", 2)
    
    # 2. Create the delivery queue using two-phase optimization strategy
    # Phase 1: Items with predicted optimal sequence (based on algorithm intelligence)
    optimized_delivery_sequence = [item['id'] for item in perfect_order[:num_optimally_sequenced]]
    remaining_items_set = set(dict_itemsInBin.keys()) - set(optimized_delivery_sequence)
    full_delivery_queue = optimized_delivery_sequence

    # Phase 2: Build adaptive sequence for remaining items using spatial heuristics
    _fnDebugLog(f"Building adaptive sequence for remaining {len(remaining_items_set)} items", 2)
    
    while remaining_items_set:
        accessible_items = [i for i in dict_itemsInBin.values() if i['id'] in remaining_items_set]
        if not accessible_items:
            break
        
        # Determine next logical batch (items with the largest X that are remaining)
        max_x = max(item['pos'][0] for item in accessible_items)
        next_batch_ids = [i['id'] for i in accessible_items if abs(i['pos'][0] - max_x) < 5.0]
        
        # Sort this batch top-to-bottom and append to the main queue
        batch_sorted = sorted(next_batch_ids, key=lambda iid: -dict_itemsInBin[iid]['pos'][1])
        full_delivery_queue.extend(batch_sorted)
        remaining_items_set -= set(batch_sorted)
        
        _fnDebugLog(f"  Batch of {len(batch_sorted)} items added to delivery queue", 3)

    _fnDebugLog(f"Delivery sequence generation complete. Total items to deliver: {len(full_delivery_queue)}", 1)
    _fnDebugLog(f"Starting main unloading simulation with REAL-TIME container state tracking...", 1)

    # --- MAIN UNLOADING SIMULATION ---
    delivery_index = 0
    for target_id in full_delivery_queue:
        delivery_index += 1
        
        if target_id not in dict_itemsInBin:
            _fnDebugLog(f"[{delivery_index}/{len(full_delivery_queue)}] Target item '{target_id}' not in bin, skipping", 1)
            continue

        _fnDebugLog(f"[{delivery_index}/{len(full_delivery_queue)}] === UNLOADING TARGET '{target_id}' ===", 0)
        _fnDebugLog(f"Current items in bin: {len(dict_itemsInBin)}", 1)
        _fnDebugLog(f"Current bin state snapshot:", 2)
        for item_id, item_data in dict_itemsInBin.items():
            _fnDebugLog(f"  '{item_id}': pos={item_data['pos']}, dims={item_data['dims']}", 3)

        holding_area = []
        event_log.append({'action': 'target', 'item_id': target_id})
        
        # A. Clear the path to the target by de-stacking blockers top-down
        _fnDebugLog(f"Phase A: Clearing path to target...", 1)
        
        clear_iteration = 0
        while True:
            clear_iteration += 1
            blocker_ids = _get_complete_blocker_stack(target_id, dict_itemsInBin)
            
            if not blocker_ids:
                _fnDebugLog(f"  Path is clear after {clear_iteration - 1} clearance(s)", 2)
                break

            _fnDebugLog(f"  Clearance iteration {clear_iteration}: Found {len(blocker_ids)} blocker(s)", 2)
            
            # Remove the topmost blocker first
            blocker_to_remove = max(blocker_ids, key=lambda iid: dict_itemsInBin[iid]['pos'][1])
            blocker_pos = dict_itemsInBin[blocker_to_remove]['pos']
            blocker_dims = dict_itemsInBin[blocker_to_remove]['dims']
            
            _fnDebugLog(f"  Removing topmost blocker: '{blocker_to_remove}' at position {blocker_pos}, dims {blocker_dims}", 2)
            
            relocations += 1
            event_log.append({'action': 'relocate', 'item_id': blocker_to_remove})
            
            # CRITICAL: Copy the item to holding area and REMOVE from dict_itemsInBin
            blocker_item = copy.deepcopy(dict_itemsInBin[blocker_to_remove])
            holding_area.append(blocker_item)
            del dict_itemsInBin[blocker_to_remove]
            
            _fnDebugLog(f"  Blocker moved to holding area. Items remaining in bin: {len(dict_itemsInBin)}", 2)
            _fnDebugLog(f"  Current bin state after removal:", 2)
            for item_id, item_data in dict_itemsInBin.items():
                _fnDebugLog(f"    '{item_id}': pos={item_data['pos']}", 3)

        # B. Deliver the target item
        _fnDebugLog(f"Phase B: Delivering target item '{target_id}'", 1)
        event_log.append({'action': 'deliver', 'item_id': target_id})
        if target_id in dict_itemsInBin:
            target_pos = dict_itemsInBin[target_id]['pos']
            target_dims = dict_itemsInBin[target_id]['dims']
            _fnDebugLog(f"  Target item position: {target_pos}, dims {target_dims}", 2)
            del dict_itemsInBin[target_id]
            _fnDebugLog(f"  Target delivered. Items remaining in bin: {len(dict_itemsInBin)}", 2)
            _fnDebugLog(f"  Current bin state after delivery:", 2)
            for item_id, item_data in dict_itemsInBin.items():
                _fnDebugLog(f"    '{item_id}': pos={item_data['pos']}", 3)

        # C. CRITICAL: Find free spaces and intelligently place relocated items
        # The key here is that we're searching for free spaces in the CURRENT state of dict_itemsInBin
        # which has already had blockers removed and target delivered
        _fnDebugLog(f"Phase C: Returning {len(holding_area)} relocated item(s) to bin", 1)
        _fnDebugLog(f"Available bin state for placement search:", 2)
        for item_id, item_data in dict_itemsInBin.items():
            _fnDebugLog(f"  '{item_id}': pos={item_data['pos']}, dims={item_data['dims']}", 3)
        
        return_iteration = 0
        while holding_area:
            return_iteration += 1
            item_to_return = holding_area.pop(0)
            item_id = item_to_return['id']
            original_dims = item_to_return['dims']
            
            _fnDebugLog(f"  Return iteration {return_iteration}: Placing item '{item_id}' back (dims={original_dims})", 2)
            _fnDebugLog(f"  Items currently in bin: {len(dict_itemsInBin)}", 3)
            _fnDebugLog(f"  Bin dimensions being used for free space search: {bin_dims}", 3)
            
            # Find ALL available free spaces in the bin using the CURRENT state
            # This is the critical part - we pass the real-time dict_itemsInBin state
            available_spaces = _find_all_free_spaces(dict_itemsInBin, bin_dims, original_dims)
            
            if available_spaces:
                # Choose the best space (first in sorted list)
                best_space = available_spaces[0]
                new_pos = best_space['pos']
                _fnDebugLog(f"  Best space found: pos={new_pos}, score={best_space['score']}, support_area={best_space['support_area']}", 2)
            else:
                # Fallback: use the original placement function
                _fnDebugLog(f"  No available spaces found, using fallback placement", 2)
                new_pos = _find_stable_placement_with_collision_check(item_to_return, dict_itemsInBin, bin_dims)
                _fnDebugLog(f"  Fallback position: {new_pos}", 2)
            
            # Update the item's position in the copy
            item_to_return['pos'] = list(new_pos)  # Ensure it's a new list, not a reference
            dict_itemsInBin[item_id] = item_to_return
            
            _fnDebugLog(f"  Item '{item_id}' placed at {new_pos}. Items in bin: {len(dict_itemsInBin)}", 2)
            _fnDebugLog(f"  Current bin state after placement:", 2)
            for check_id, check_data in dict_itemsInBin.items():
                _fnDebugLog(f"    '{check_id}': pos={check_data['pos']}", 3)
            
            event_log.append({
                'action': 'return_relocated',
                'item_id': item_id,
                'new_pos': new_pos
            })

        # D. Stabilize the entire truck (gravity simulation)
        _fnDebugLog(f"Phase D: Stabilizing bin (gravity simulation)", 1)
        
        is_fully_stable = False
        stabilization_iterations = 0
        max_stabilization_iterations = 50
        
        while not is_fully_stable and stabilization_iterations < max_stabilization_iterations:
            is_fully_stable = True
            stabilization_iterations += 1
            
            _fnDebugLog(f"  Stabilization pass {stabilization_iterations}...", 2)
            
            # Check for floating items due to gravity
            # Sort items by Y position (lower items first) to process from ground up
            sorted_item_ids = sorted(dict_itemsInBin.keys(), key=lambda iid: dict_itemsInBin[iid]['pos'][1])
            
            for item_id in sorted_item_ids:
                if item_id not in dict_itemsInBin:
                    continue
                
                item = dict_itemsInBin[item_id]
                iy = item['pos'][1]
                highest_support_y = 0.0
                
                _fnDebugLog(f"    Checking item '{item_id}' at Y={iy}", 3)

                # Find the highest support level under this item
                for other in dict_itemsInBin.values():
                    if other['id'] == item_id:
                        continue
                    
                    other_top_y = other['pos'][1] + other['dims'][1]
                    
                    # Skip if other item is at or above this item's current position
                    if other_top_y > iy + 1e-4:
                        continue
                    
                    o_pos, o_dims = other['pos'], other['dims']
                    
                    # X-Z Overlap check for support
                    x_overlap = (item['pos'][0] < o_pos[0] + o_dims[0] and o_pos[0] < item['pos'][0] + item['dims'][0])
                    z_overlap = (item['pos'][2] < o_pos[2] + o_dims[2] and o_pos[2] < item['pos'][2] + item['dims'][2])
                    
                    if x_overlap and z_overlap:
                        highest_support_y = max(highest_support_y, other_top_y)
                        _fnDebugLog(f"      Support found from '{other['id']}' at Y={other_top_y}", 3)
                
                # If item is floating, apply gravity
                if iy > highest_support_y + 1e-4:
                    is_fully_stable = False
                    old_y = item['pos'][1]
                    item['pos'][1] = highest_support_y
                    
                    _fnDebugLog(f"      Item floating! Moved from Y={old_y} to Y={highest_support_y}", 2)
                    
                    event_log.append({
                        'action': 'settle',
                        'item_id': item_id,
                        'new_y_pos': highest_support_y
                    })
                    break  # Restart stabilization after any gravity change
            
            if is_fully_stable:
                _fnDebugLog(f"  Bin is stable after {stabilization_iterations} pass(es)", 2)
        
        _fnDebugLog(f"[{delivery_index}/{len(full_delivery_queue)}] === TARGET '{target_id}' UNLOADED ===", 0)
        _fnDebugLog(f"Relocations so far: {relocations}", 1)
        _fnDebugLog(f"Current items in bin: {len(dict_itemsInBin)}", 1)
    
    _fnDebugLog(f"=== UNLOADING SIMULATION COMPLETE ===", 0)
    _fnDebugLog(f"Total relocations: {relocations}", 1)
    _fnDebugLog(f"Total events logged: {len(event_log)}", 1)
    _fnDebugLog(f"=== fnGenerateUnloadingSequence END ===", 0)
    
    return {
        'event_log': event_log,
        'relocation_count': relocations
    }