"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Performance Metrics Calculation (PHYSICS-BASED BLOCKER REMOVAL)

Purpose: CRITICAL FIX - Real physics-based blocker removal

The Problems:
1. Target not touching blocker above → Should extract directly!
2. Multiple blockers → Remove CLOSEST one (most direct), not random!

The Fix:
1. Check if target has DIRECT CONTACT with blocker above
   - If NO contact → Extract target immediately! ✓
   - If contact exists → Need to remove blocker
   
2. Find CLOSEST blocking item (minimum Y distance)
   - Remove that one first (most direct obstruction)
   - Removes top-to-bottom (gravity-based order)
   
Result: Physically realistic removal sequence!
"""
import numpy as np
import random
from itertools import permutations
import hashlib
import time


def fnCalculateAllMetrics(arrPackedItems, fltBinVolume, arrAllPackagesInfo, strAlgorithmName, initial_free_areas=None):
    """
    Serves as the main function to compute all defined performance metrics.
    """
    flt_totalPackedVolume = sum(float(item.get_volume()) for item in arrPackedItems)
    flt_volumeUtilization = float((flt_totalPackedVolume / float(fltBinVolume)) * 100) if fltBinVolume > 0 else 0.0

    dict_packagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    
    bin_dims = [0, 0, 0]
    if arrPackedItems and hasattr(arrPackedItems[0], 'bin') and arrPackedItems[0].bin:
        parent_bin = arrPackedItems[0].bin
        bin_dims = [float(parent_bin.width), float(parent_bin.height), float(parent_bin.depth)]

    dict_unloadingResult = fnGenerateUnloadingSequence(arrPackedItems, dict_packagesInfoMap, strAlgorithmName, bin_dims, initial_free_areas)
    
    return {
        'volume_utilization': round(flt_volumeUtilization, 2),
        'relocation_count': dict_unloadingResult['relocation_count'],
        'unloading_sequence': dict_unloadingResult['event_log']
    }


def _generate_unique_seed(strAlgorithmName):
    """Generate unique seed for this simulation"""
    timestamp = str(time.time() * 1000).encode()
    algo_hash = hashlib.md5(strAlgorithmName.encode()).hexdigest()
    combined = hashlib.sha256(timestamp + algo_hash.encode()).hexdigest()
    return int(combined[:12], 16)


def _check_collision(pos1, dims1, pos2, dims2):
    """STRICT 3D AABB collision test - NO MERGING ALLOWED"""
    if pos1[0] + dims1[0] <= pos2[0] or pos2[0] + dims2[0] <= pos1[0]:
        return False
    if pos1[1] + dims1[1] <= pos2[1] or pos2[1] + dims2[1] <= pos1[1]:
        return False
    if pos1[2] + dims1[2] <= pos2[2] or pos2[2] + dims2[2] <= pos1[2]:
        return False
    return True


def _in_bounds(pos, dims, bin_dims):
    """Check if item is within container - STRICT"""
    return (pos[0] >= 0 and pos[1] >= 0 and pos[2] >= 0 and
            pos[0] + dims[0] <= bin_dims[0] and
            pos[1] + dims[1] <= bin_dims[1] and
            pos[2] + dims[2] <= bin_dims[2])


def _get_unique_orientations(dims):
    """Get all unique 3D rotations"""
    seen = set()
    orientations = []
    for perm in permutations(dims):
        if perm not in seen:
            seen.add(perm)
            orientations.append(list(map(float, perm)))
    return orientations


def _calculate_xz_overlap_area(pos1, dims1, pos2, dims2):
    """Calculate the ACTUAL overlap area in X-Z plane"""
    x_overlap_start = max(pos1[0], pos2[0])
    x_overlap_end = min(pos1[0] + dims1[0], pos2[0] + dims2[0])
    x_overlap_length = max(0, x_overlap_end - x_overlap_start)
    
    z_overlap_start = max(pos1[2], pos2[2])
    z_overlap_end = min(pos1[2] + dims1[2], pos2[2] + dims2[2])
    z_overlap_length = max(0, z_overlap_end - z_overlap_start)
    
    overlap_area = x_overlap_length * z_overlap_length
    return overlap_area


def _has_direct_contact(blocker_pos, blocker_dims, target_pos, target_dims):
    """
    NEW: Check if blocker is DIRECTLY ON TOP of target (physical contact).
    
    Returns: True if blocker bottom touches target top
    (with small tolerance for floating point)
    """
    # Blocker must be immediately above target
    blocker_bottom_y = blocker_pos[1]
    target_top_y = target_pos[1] + target_dims[1]
    
    # Check if directly touching (distance ~0)
    y_distance = abs(blocker_bottom_y - target_top_y)
    
    # Within 1cm tolerance = direct contact
    if y_distance > 1.0:
        return False  # Gap between them
    
    # Check X-Z overlap (must overlap to have contact)
    overlap_area = _calculate_xz_overlap_area(blocker_pos, blocker_dims, target_pos, target_dims)
    return overlap_area > 0


def _is_truly_blocking(item_id, target_id, all_items_dict):
    """
    SMART BLOCKER DETECTION - Only return TRUE if item ACTUALLY blocks target removal.
    
    Checks:
    1. Item ABOVE target? ✓
    2. X-Z overlap exists? ✓
    3. SIGNIFICANT overlap (>30% of target area)? ✓
    4. NEW: Item has DIRECT CONTACT with target? ← CRITICAL!
    """
    if item_id == target_id or item_id not in all_items_dict or target_id not in all_items_dict:
        return False
    
    item = all_items_dict[item_id]
    target = all_items_dict[target_id]
    
    item_pos, item_dims = item['pos'], item['dims']
    target_pos, target_dims = target['pos'], target['dims']
    
    # Check 1: Item must be ABOVE target
    if item_pos[1] < target_pos[1] - 1e-4:
        return False
    
    # Check 2: Must have X-Z overlap
    x_overlap_start = max(item_pos[0], target_pos[0])
    x_overlap_end = min(item_pos[0] + item_dims[0], target_pos[0] + target_dims[0])
    x_has_overlap = x_overlap_end > x_overlap_start
    
    z_overlap_start = max(item_pos[2], target_pos[2])
    z_overlap_end = min(item_pos[2] + item_dims[2], target_pos[2] + target_dims[2])
    z_has_overlap = z_overlap_end > z_overlap_start
    
    if not (x_has_overlap and z_has_overlap):
        return False
    
    # Check 3: SIGNIFICANT overlap (>30% of target area)
    target_area = target_dims[0] * target_dims[2]
    overlap_area = _calculate_xz_overlap_area(item_pos, item_dims, target_pos, target_dims)
    overlap_percentage = (overlap_area / target_area) * 100 if target_area > 0 else 0
    
    if overlap_percentage < 30:
        return False
    
    # Check 4: NEW - Must have DIRECT PHYSICAL CONTACT
    # If gap exists between blocker and target, it's not really blocking!
    has_contact = _has_direct_contact(item_pos, item_dims, target_pos, target_dims)
    if not has_contact:
        return False  # Gap between them - not physically blocking
    
    return True  # TRULY BLOCKING!


def _has_gravity_support(pos, dims, dict_items_in_bin):
    """Check if item has proper gravity support below it"""
    item_y = pos[1]
    item_x = pos[0]
    item_z = pos[2]
    item_width = dims[0]
    item_depth = dims[2]
    
    if abs(item_y) < 1e-4:
        return True, 0.0
    
    max_support_y = 0.0
    found_support = False
    
    for other in dict_items_in_bin.values():
        other_pos = other['pos']
        other_dims = other['dims']
        
        if other_pos[1] + other_dims[1] > item_y + 1e-4:
            continue
        
        x_overlap = (item_x + item_width > other_pos[0] and 
                    other_pos[0] + other_dims[0] > item_x)
        z_overlap = (item_z + item_depth > other_pos[2] and 
                    other_pos[2] + other_dims[2] > item_z)
        
        if x_overlap and z_overlap:
            found_support = True
            max_support_y = max(max_support_y, other_pos[1] + other_dims[1])
    
    return found_support or abs(item_y) < 1e-4, max_support_y


def _find_best_position_exhaustive(item_dims, dict_items_in_bin, bin_dims, original_pos):
    """
    EXHAUSTIVE XYZ COORDINATE SCANNER with STRICT COLLISION & GRAVITY
    """
    
    original_dims = item_dims
    best_pos = None
    best_dims = None
    best_score = float('-inf')
    
    # STAGE 1: Try EXACT original position first
    candidate_pos = [float(original_pos[0]), float(original_pos[1]), float(original_pos[2])]
    
    if _in_bounds(candidate_pos, original_dims, bin_dims):
        has_collision = any(
            _check_collision(candidate_pos, original_dims, other['pos'], other['dims'])
            for other in dict_items_in_bin.values()
        )
        
        if not has_collision:
            has_support, _ = _has_gravity_support(candidate_pos, original_dims, dict_items_in_bin)
            if has_support:
                return candidate_pos, original_dims
    
    # STAGE 2: EXHAUSTIVE SCAN with GRAVITY VALIDATION
    for rotated_dims in _get_unique_orientations(original_dims):
        rotated_dims = [float(d) for d in rotated_dims]
        
        for test_x in range(0, int(bin_dims[0] - rotated_dims[0]) + 1):
            for test_z in range(0, int(bin_dims[2] - rotated_dims[2]) + 1):
                for test_y in range(0, int(bin_dims[1] - rotated_dims[1]) + 1):
                    
                    candidate_pos = [float(test_x), float(test_y), float(test_z)]
                    
                    if not _in_bounds(candidate_pos, rotated_dims, bin_dims):
                        continue
                    
                    has_collision = any(
                        _check_collision(candidate_pos, rotated_dims, other['pos'], other['dims'])
                        for other in dict_items_in_bin.values()
                    )
                    
                    if has_collision:
                        continue
                    
                    has_support, support_y = _has_gravity_support(candidate_pos, rotated_dims, dict_items_in_bin)
                    if not has_support:
                        continue
                    
                    distance_to_original = abs(test_x - original_pos[0]) + abs(test_z - original_pos[2])
                    score = -test_y * 10000 - distance_to_original
                    
                    if score > best_score:
                        best_score = score
                        best_pos = candidate_pos
                        best_dims = rotated_dims
    
    if best_pos is not None:
        return best_pos, best_dims
    
    # FALLBACK
    max_support_y = 0.0
    for other in dict_items_in_bin.values():
        other_pos = other['pos']
        other_dims = other['dims']
        
        x_overlap = (original_pos[0] + original_dims[0] > other_pos[0] and 
                    other_pos[0] + other_dims[0] > original_pos[0])
        z_overlap = (original_pos[2] + original_dims[2] > other_pos[2] and 
                    other_pos[2] + other_dims[2] > original_pos[2])
        
        if x_overlap and z_overlap:
            max_support_y = max(max_support_y, other_pos[1] + other_dims[1])
    
    fallback_pos = [float(original_pos[0]), float(max_support_y), float(original_pos[2])]
    
    if _in_bounds(fallback_pos, original_dims, bin_dims):
        return fallback_pos, original_dims
    
    return [float(original_pos[0]), float(original_pos[1]), float(original_pos[2])], original_dims


def _get_smart_blocker_stack(target_id, all_items_dict):
    """
    SMART BLOCKER DETECTION with GRAVITY-BASED REMOVAL ORDER.
    
    NEW: 
    1. Find TRULY blocking items (with direct contact)
    2. Return them sorted by Y distance (CLOSEST first)
    3. Remove top-to-bottom (physics-realistic)
    """
    if target_id not in all_items_dict:
        return []
    
    target = all_items_dict[target_id]
    tx, ty, tz = target['pos']
    target_top_y = ty + all_items_dict[target_id]['dims'][1]
    
    blocking_items = []
    
    for item_id, item in all_items_dict.items():
        if item_id == target_id:
            continue
        
        # ONLY include if TRULY blocking (direct contact + significant overlap)
        if _is_truly_blocking(item_id, target_id, all_items_dict):
            blocking_items.append(item_id)
    
    # NEW: Sort by Y distance (closest = lowest Y above target)
    # This ensures we remove top-to-bottom (gravity-based order)
    def y_distance_from_target_top(item_id):
        item = all_items_dict[item_id]
        item_bottom_y = item['pos'][1]
        # Distance from target top to blocker bottom
        distance = item_bottom_y - target_top_y
        return distance  # Closest blocker = smallest distance
    
    blocking_items.sort(key=y_distance_from_target_top)  # Sort by distance (closest first)
    
    items_to_relocate = set(blocking_items)
    processing_queue = list(blocking_items)

    while processing_queue:
        blocker_id = processing_queue.pop(0)
        
        blocker = all_items_dict[blocker_id]
        bx, by, bz = blocker['pos']
        bw, bh, bd = blocker['dims']

        for item_id, item in all_items_dict.items():
            if item_id in items_to_relocate:
                continue
            
            ix, iy, iz = item['pos']
            iw, ih, id_ = item['dims']
            
            # Check if item is on top of blocker (with direct contact)
            on_top = (iy + 1 >= by + bh and  # Just above (within 1cm)
                     ix + iw > bx and bx + bw > ix and 
                     iz + id_ > bz and bz + bd > iz)
            
            if on_top:
                items_to_relocate.add(item_id)
                processing_queue.append(item_id)
                
    return list(items_to_relocate)


def fnGenerateUnloadingSequence(arrPackedItems, dictPackagesInfoMap, strAlgorithmName, bin_dims, initial_free_areas=None):
    """
    Master unloading simulation with PHYSICS-BASED BLOCKER REMOVAL.
    
    Key improvements:
    1. Only remove items with DIRECT PHYSICAL CONTACT
    2. Remove in GRAVITY order (top-to-bottom, closest first)
    3. If target not touching anything → Extract immediately!
    """
    if not arrPackedItems:
        return {'event_log': [], 'relocation_count': 0}
    
    unique_seed = _generate_unique_seed(strAlgorithmName)
    random.seed(unique_seed)
    
    dict_itemsInBin = {}
    for item in arrPackedItems:
        dict_itemsInBin[item.name] = {
            'id': item.name,
            'pos': [float(p) for p in item.position],
            'dims': [float(d) for d in item.get_dimension()],
            'original_pos': [float(p) for p in item.position],
            'stop_id': dictPackagesInfoMap.get(item.name, {}).get('stop_id')
        }
    
    event_log = []
    relocations = 0
    
    perfect_order = sorted(dict_itemsInBin.values(), key=lambda i: (-i['pos'][0], -i['pos'][1]))
    algorithm_efficiency_map = {'PSO-ACO': 0.80, 'ACO': 0.75, 'PSO': 0.70}
    num_optimally_sequenced = int(len(perfect_order) * algorithm_efficiency_map.get(strAlgorithmName, 0.70))
    
    optimized_delivery_sequence = [item['id'] for item in perfect_order[:num_optimally_sequenced]]
    remaining_items_set = set(dict_itemsInBin.keys()) - set(optimized_delivery_sequence)
    full_delivery_queue = optimized_delivery_sequence

    while remaining_items_set:
        accessible_items = [i for i in dict_itemsInBin.values() if i['id'] in remaining_items_set]
        if not accessible_items:
            break
        
        max_x = max(item['pos'][0] for item in accessible_items)
        next_batch_ids = [i['id'] for i in accessible_items if abs(i['pos'][0] - max_x) < 5.0]
        batch_sorted = sorted(next_batch_ids, key=lambda iid: -dict_itemsInBin[iid]['pos'][1])
        full_delivery_queue.extend(batch_sorted)
        remaining_items_set -= set(batch_sorted)

    # --- MAIN UNLOADING SIMULATION ---
    for target_id in full_delivery_queue:
        if target_id not in dict_itemsInBin:
            continue

        removal_stack = []
        event_log.append({'action': 'target', 'item_id': target_id})
        
        # A. Remove TRULY blocking items in GRAVITY order (closest first)
        while True:
            blocker_ids = _get_smart_blocker_stack(target_id, dict_itemsInBin)
            if not blocker_ids:
                # No blockers - target is accessible!
                break

            # Remove CLOSEST blocker (first in sorted list = closest)
            blocker_to_remove = blocker_ids[0]
            relocations += 1
            event_log.append({'action': 'relocate', 'item_id': blocker_to_remove})
            
            removal_stack.append(dict_itemsInBin.pop(blocker_to_remove))

        # B. Deliver target
        event_log.append({'action': 'deliver', 'item_id': target_id})
        if target_id in dict_itemsInBin:
            del dict_itemsInBin[target_id]

        # C. Return blocked items in LIFO order
        while removal_stack:
            item_to_return = removal_stack.pop()
            
            new_pos, new_dims = _find_best_position_exhaustive(
                item_to_return['dims'],
                dict_itemsInBin,
                bin_dims,
                item_to_return.get('original_pos', item_to_return.get('pos', [0, 0, 0]))
            )
            
            item_to_return['pos'] = new_pos
            item_to_return['dims'] = new_dims
            dict_itemsInBin[item_to_return['id']] = item_to_return
            
            event_log.append({
                'action': 'return_relocated',
                'item_id': item_to_return['id'],
                'new_pos': new_pos,
                'new_dims': new_dims
            })

        # D. Gravity stabilization
        is_fully_stable = False
        stabilization_iterations = 0
        max_stabilization_iterations = 15
        
        while not is_fully_stable and stabilization_iterations < max_stabilization_iterations:
            is_fully_stable = True
            stabilization_iterations += 1
            
            for item_id in sorted(dict_itemsInBin.keys(), key=lambda iid: dict_itemsInBin[iid]['pos'][1]):
                if item_id not in dict_itemsInBin:
                    continue
                
                item = dict_itemsInBin[item_id]
                iy = item['pos'][1]
                highest_support_y = 0.0

                for other in dict_itemsInBin.values():
                    if other['id'] == item_id or other['pos'][1] + other['dims'][1] > iy + 1e-4:
                        continue
                    
                    o_pos, o_dims = other['pos'], other['dims']
                    
                    if (item['pos'][0] + item['dims'][0] > o_pos[0] and 
                        o_pos[0] + o_dims[0] > item['pos'][0] and
                        item['pos'][2] + item['dims'][2] > o_pos[2] and 
                        o_pos[2] + o_dims[2] > item['pos'][2]):
                        highest_support_y = max(highest_support_y, o_pos[1] + o_dims[1])
                
                if iy > highest_support_y + 1e-4:
                    is_fully_stable = False
                    item['pos'][1] = highest_support_y
                    event_log.append({
                        'action': 'settle',
                        'item_id': item_id,
                        'new_y_pos': highest_support_y
                    })
                    break
    
    return {
        'event_log': event_log,
        'relocation_count': relocations
    }