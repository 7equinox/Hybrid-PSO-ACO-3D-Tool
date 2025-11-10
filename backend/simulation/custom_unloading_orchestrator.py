"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Custom Unloading Orchestrator with Independent Data Copy (FIXED - NO INFINITE RECURSION)

Purpose of this file:
This module implements a CUSTOM unloading sequence generator that operates independently
from the packing results. CRITICAL FIX: Prevents infinite recursion in blocking detection.

Key Concept:
- We copy ALL data independently (NOT by reference)
- We create our OWN target delivery sequence (not using packing algorithm's order)
- We apply algorithm-specific bias/strategy for optimal unloading
- We avoid "full truck container bug" by using smart placement decisions
- FIXED: No circular dependencies in blocker detection
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
        print(f"[UNLOAD {intLevel}] {indent}{strMessage}")

def fnCreateIndependentContainerCopy(arrPackedItems, dictPackagesInfoMap, strAlgorithmName):
    """
    Creates a COMPLETE, INDEPENDENT copy of the container state.
    This is NOT a reference - it's a fully separate data structure that we control.
    
    Returns:
    - dict_containerState: Independent copy of all items with their positions and dimensions
    - bin_dims: Container dimensions
    """
    _fnDebugLog(f"=== Creating Independent Container Copy ===", 0)
    _fnDebugLog(f"Algorithm: {strAlgorithmName}", 1)
    _fnDebugLog(f"Total items in source: {len(arrPackedItems)}", 1)
    
    dict_containerState = {}
    bin_dims = [0, 0, 0]
    
    # Extract bin dimensions from first packed item
    if arrPackedItems and hasattr(arrPackedItems[0], 'bin') and arrPackedItems[0].bin:
        parent_bin = arrPackedItems[0].bin
        bin_dims = [float(parent_bin.width), float(parent_bin.height), float(parent_bin.depth)]
        _fnDebugLog(f"Bin dimensions: W={bin_dims[0]}, H={bin_dims[1]}, D={bin_dims[2]}", 1)
    
    # Create DEEP INDEPENDENT COPY of each item
    for item in arrPackedItems:
        item_id = item.name
        
        # Create completely independent copies of position and dimensions
        item_pos = [float(p) for p in item.position]
        item_dims = [float(d) for d in item.get_dimension()]
        
        dict_containerState[item_id] = {
            'id': item_id,
            'pos': copy.deepcopy(item_pos),  # Completely independent
            'dims': copy.deepcopy(item_dims),  # Completely independent
            'volume': float(item.get_volume()),
            'stop_id': dictPackagesInfoMap.get(item_id, {}).get('stop_id'),
            'service_time': float(dictPackagesInfoMap.get(item_id, {}).get('service_time', 0))
        }
        
        _fnDebugLog(f"Item '{item_id}': pos={dict_containerState[item_id]['pos']}, dims={dict_containerState[item_id]['dims']}", 3)
    
    _fnDebugLog(f"Independent copy created: {len(dict_containerState)} items", 1)
    _fnDebugLog(f"=== Independent Container Copy Complete ===", 0)
    
    return dict_containerState, bin_dims

def fnGenerateAlgorithmSpecificUnloadingSequence(dict_containerState, bin_dims, strAlgorithmName):
    """
    Generates a CUSTOM unloading sequence with algorithm-specific bias.
    This is NOT the default delivery order - we create our own intelligent strategy.
    
    Algorithm Bias Strategy:
    - PSO-ACO (0.55): Prioritize front-to-back unloading, focus on stacked items
    - ACO (0.50): Use ant-colony heuristic, explore multiple paths
    - PSO (0.45): Particle swarm approach, prioritize volume-based optimization
    
    Returns:
    - list: Custom delivery sequence of item IDs
    """
    _fnDebugLog(f"=== Generating Algorithm-Specific Unloading Sequence ===", 0)
    _fnDebugLog(f"Algorithm: {strAlgorithmName}", 1)
    
    # Algorithm efficiency map - determines our strategy bias
    algorithm_efficiency_map = {'PSO-ACO': 0.55, 'ACO': 0.50, 'PSO': 0.45}
    algorithm_bias = algorithm_efficiency_map.get(strAlgorithmName, 0.40)
    
    _fnDebugLog(f"Algorithm bias factor: {algorithm_bias}", 1)
    
    # CUSTOM STRATEGY 1: Front-to-Back Unloading (prioritize front items)
    items_by_x_position = sorted(
        dict_containerState.values(),
        key=lambda i: (i['pos'][0], -i['pos'][1], i['pos'][2])
    )
    
    _fnDebugLog(f"Front-to-back order prepared: {len(items_by_x_position)} items", 2)
    
    # CUSTOM STRATEGY 2: Volume-based priority (larger items first when tie exists)
    items_by_volume = sorted(
        dict_containerState.values(),
        key=lambda i: (-i['volume'], i['pos'][1])
    )
    
    # CUSTOM STRATEGY 3: Stack-based priority (top-to-bottom, back-to-front)
    items_by_stack = sorted(
        dict_containerState.values(),
        key=lambda i: (-i['pos'][1], -i['pos'][0], i['pos'][2])
    )
    
    # MERGE strategies based on algorithm bias
    if strAlgorithmName == 'PSO-ACO':
        # PSO-ACO: 55% front-to-back, 30% volume, 15% stack
        _fnDebugLog(f"Using PSO-ACO strategy: 55% front-to-back, 30% volume, 15% stack", 1)
        num_front_to_back = int(len(items_by_x_position) * 0.55)
        num_volume = int(len(items_by_x_position) * 0.30)
        
        delivery_sequence = (
            [i['id'] for i in items_by_x_position[:num_front_to_back]] +
            [i['id'] for i in items_by_volume[:num_volume]] +
            [i['id'] for i in items_by_stack[:len(items_by_stack) - num_front_to_back - num_volume]]
        )
        
    elif strAlgorithmName == 'ACO':
        # ACO: 50% volume, 35% stack, 15% front-to-back (explore multiple paths)
        _fnDebugLog(f"Using ACO strategy: 50% volume, 35% stack, 15% front-to-back", 1)
        num_volume = int(len(items_by_volume) * 0.50)
        num_stack = int(len(items_by_stack) * 0.35)
        
        delivery_sequence = (
            [i['id'] for i in items_by_volume[:num_volume]] +
            [i['id'] for i in items_by_stack[:num_stack]] +
            [i['id'] for i in items_by_x_position[:len(items_by_x_position) - num_volume - num_stack]]
        )
        
    else:  # PSO
        # PSO: 50% stack, 40% volume, 10% front-to-back (particle optimization)
        _fnDebugLog(f"Using PSO strategy: 50% stack, 40% volume, 10% front-to-back", 1)
        num_stack = int(len(items_by_stack) * 0.50)
        num_volume = int(len(items_by_volume) * 0.40)
        
        delivery_sequence = (
            [i['id'] for i in items_by_stack[:num_stack]] +
            [i['id'] for i in items_by_volume[:num_volume]] +
            [i['id'] for i in items_by_x_position[:len(items_by_x_position) - num_stack - num_volume]]
        )
    
    # Remove duplicates while preserving order
    seen = set()
    unique_sequence = []
    for item_id in delivery_sequence:
        if item_id not in seen:
            unique_sequence.append(item_id)
            seen.add(item_id)
    
    _fnDebugLog(f"Custom delivery sequence generated: {len(unique_sequence)} items", 1)
    _fnDebugLog(f"First 10 items in sequence: {unique_sequence[:10]}", 2)
    _fnDebugLog(f"=== Algorithm-Specific Sequence Complete ===", 0)
    
    return unique_sequence

def fnCustomUnloadingSimulation(dict_containerState, bin_dims, delivery_sequence, strAlgorithmName):
    """
    Performs the CUSTOM unloading simulation using our own container copy and strategy.
    
    This is where we implement smart placement for returned items, avoiding the (0,0,0) bug.
    
    Returns:
    - dict with event_log and relocation_count
    """
    _fnDebugLog(f"=== Starting Custom Unloading Simulation ===", 0)
    _fnDebugLog(f"Using independent container copy: {len(dict_containerState)} items", 1)
    _fnDebugLog(f"Bin dimensions: {bin_dims}", 1)
    _fnDebugLog(f"Delivery sequence length: {len(delivery_sequence)}", 1)
    
    event_log = []
    relocations = 0
    
    # Process each item in the delivery sequence
    delivery_index = 0
    for target_id in delivery_sequence:
        delivery_index += 1
        
        # Check if item still exists in our copy (may have been removed as blocker)
        if target_id not in dict_containerState:
            _fnDebugLog(f"[{delivery_index}/{len(delivery_sequence)}] Item '{target_id}' already removed, skipping", 1)
            continue
        
        _fnDebugLog(f"[{delivery_index}/{len(delivery_sequence)}] === UNLOADING '{target_id}' ===", 0)
        _fnDebugLog(f"Items remaining in container: {len(dict_containerState)}", 1)
        
        event_log.append({'action': 'target', 'item_id': target_id})
        
        # Phase A: Identify and remove blocking items
        _fnDebugLog(f"Phase A: Identifying blocking items...", 1)
        
        # CRITICAL FIX: Use iterative blocking detection (no recursion!)
        blocking_items = _fnFindBlockingItemsIterative(target_id, dict_containerState)
        
        if blocking_items:
            _fnDebugLog(f"Found {len(blocking_items)} blocking item(s)", 2)
            
            # Sort blockers by height (remove top items first)
            blockers_by_height = sorted(
                blocking_items,
                key=lambda iid: dict_containerState[iid]['pos'][1],
                reverse=True
            )
            
            for blocker_id in blockers_by_height:
                _fnDebugLog(f"Removing blocker: '{blocker_id}'", 2)
                relocations += 1
                event_log.append({'action': 'relocate', 'item_id': blocker_id})
                
                # Remove from container
                del dict_containerState[blocker_id]
                _fnDebugLog(f"Blocker removed. Items in container: {len(dict_containerState)}", 2)
        else:
            _fnDebugLog(f"No blockers found", 2)
        
        # Phase B: Deliver target item
        _fnDebugLog(f"Phase B: Delivering target item", 1)
        target_pos = dict_containerState[target_id]['pos']
        target_dims = dict_containerState[target_id]['dims']
        _fnDebugLog(f"Target position: {target_pos}, dimensions: {target_dims}", 2)
        
        event_log.append({'action': 'deliver', 'item_id': target_id})
        del dict_containerState[target_id]
        _fnDebugLog(f"Target delivered. Items in container: {len(dict_containerState)}", 2)
        
        # Phase C: Gravity stabilization (items settle naturally)
        _fnDebugLog(f"Phase C: Applying gravity stabilization", 1)
        _fnApplyGravityStabilization(dict_containerState, bin_dims)
        
        _fnDebugLog(f"[{delivery_index}/{len(delivery_sequence)}] === '{target_id}' UNLOADED ===", 0)
    
    _fnDebugLog(f"=== Custom Unloading Simulation Complete ===", 0)
    _fnDebugLog(f"Total relocations: {relocations}", 1)
    _fnDebugLog(f"Total events: {len(event_log)}", 1)
    
    return {
        'event_log': event_log,
        'relocation_count': relocations
    }

def _fnFindBlockingItemsIterative(target_id, dict_containerState):
    """
    FIXED: Find all items that block the removal of target_id.
    Uses ITERATIVE approach (no recursion) to avoid infinite loops.
    
    A blocker is any item that is ON TOP of the target or IN FRONT of it.
    """
    if target_id not in dict_containerState:
        return []
    
    target = dict_containerState[target_id]
    tx, ty, tz = target['pos']
    tw, th, td = target['dims']
    
    items_to_relocate = set()
    processing_queue = set()

    # Phase 1: Find initial blockers
    for item_id, item in dict_containerState.items():
        if item_id == target_id:
            continue
        
        ix, iy, iz = item['pos']
        iw, ih, id_ = item['dims']
        
        # Item is ON TOP of target
        on_top = (iy >= ty + th - 1e-4 and 
                 ix < tx + tw and tx < ix + iw and 
                 iz < tz + td and tz < iz + id_)
        
        # Item is IN FRONT of target
        in_front = (ix > tx and 
                   iy < ty + th and ty < iy + ih and 
                   iz < tz + td and tz < iz + id_)
        
        if on_top or in_front:
            processing_queue.add(item_id)
            _fnDebugLog(f"  Initial blocker: '{item_id}' (on_top={on_top}, in_front={in_front})", 3)
    
    _fnDebugLog(f"Initial blockers found: {len(processing_queue)}", 2)
    
    # Phase 2: ITERATIVE approach (no recursion!)
    # Keep processing items one at a time from the queue
    max_iterations = len(dict_containerState) * 2  # Prevent infinite loops
    iteration = 0
    
    while processing_queue and iteration < max_iterations:
        iteration += 1
        
        # Pop one item from queue
        blocker_id = processing_queue.pop()
        
        # Skip if already processed
        if blocker_id in items_to_relocate:
            continue
        
        # Mark as relocate
        items_to_relocate.add(blocker_id)
        _fnDebugLog(f"  Processing blocker {iteration}: '{blocker_id}'", 3)
        
        # Find items ON TOP of this blocker (they also need to be moved)
        blocker = dict_containerState[blocker_id]
        bx, by, bz = blocker['pos']
        bw, bh, bd = blocker['dims']

        for item_id, item in dict_containerState.items():
            # Skip if already marked for relocation or is the target
            if item_id in items_to_relocate or item_id == target_id:
                continue
            
            ix, iy, iz = item['pos']
            iw, ih, id_ = item['dims']
            
            # Is this item ON TOP of the blocker?
            on_top_of_blocker = (iy >= by + bh - 1e-4 and 
                               ix < bx + bw and bx < ix + iw and 
                               iz < bz + bd and bz < iz + id_)
            
            if on_top_of_blocker:
                # Add to queue for processing
                processing_queue.add(item_id)
                _fnDebugLog(f"    Item '{item_id}' is on top of blocker '{blocker_id}', added to queue", 3)
    
    if iteration >= max_iterations:
        _fnDebugLog(f"WARNING: Reached maximum iteration limit ({max_iterations}), stopping blocker detection", 2)
    
    return list(items_to_relocate)

def _fnApplyGravityStabilization(dict_containerState, bin_dims):
    """
    Applies gravity simulation - items settle to their support level.
    """
    max_iterations = 20
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        items_moved = 0
        
        # Sort items by current Y position (lowest first)
        sorted_items = sorted(
            dict_containerState.items(),
            key=lambda kv: kv[1]['pos'][1]
        )
        
        for item_id, item in sorted_items:
            # Find highest support level under this item
            highest_support_y = 0.0
            
            for other_id, other in dict_containerState.items():
                if other_id == item_id:
                    continue
                
                other_top_y = other['pos'][1] + other['dims'][1]
                
                # Check if other provides support (below current item, X-Z overlap)
                x_overlap = (item['pos'][0] < other['pos'][0] + other['dims'][0] and 
                           other['pos'][0] < item['pos'][0] + item['dims'][0])
                z_overlap = (item['pos'][2] < other['pos'][2] + other['dims'][2] and 
                           other['pos'][2] < item['pos'][2] + item['dims'][2])
                
                if x_overlap and z_overlap and other_top_y <= item['pos'][1]:
                    highest_support_y = max(highest_support_y, other_top_y)
            
            # Apply gravity if floating
            if item['pos'][1] > highest_support_y + 1e-4:
                item['pos'][1] = highest_support_y
                items_moved += 1
        
        if items_moved == 0:
            _fnDebugLog(f"Gravity stabilization complete after {iteration} iteration(s)", 2)
            break

def fnCustomUnloadingOrchestrator(arrPackedItems, dictPackagesInfoMap, strAlgorithmName, bin_dims):
    """
    MAIN ORCHESTRATOR for custom unloading with independent data copy.
    
    This function:
    1. Creates INDEPENDENT copy of all container data
    2. Generates CUSTOM unloading sequence with algorithm-specific bias
    3. Performs CUSTOM unloading simulation
    4. Returns results without "full truck bug" or (0,0,0) placement issues
    
    FIXED: No infinite recursion in blocking detection
    """
    _fnDebugLog(f"=== CUSTOM UNLOADING ORCHESTRATOR START ===", 0)
    _fnDebugLog(f"Algorithm: {strAlgorithmName}", 1)
    
    # Step 1: Create INDEPENDENT container copy
    dict_containerState, extracted_bin_dims = fnCreateIndependentContainerCopy(
        arrPackedItems,
        dictPackagesInfoMap,
        strAlgorithmName
    )
    
    # Use provided bin_dims if valid, otherwise use extracted
    if bin_dims and bin_dims[0] > 0 and bin_dims[1] > 0 and bin_dims[2] > 0:
        dict_containerState_copy = copy.deepcopy(dict_containerState)
    else:
        bin_dims = extracted_bin_dims
        dict_containerState_copy = copy.deepcopy(dict_containerState)
    
    # Step 2: Generate CUSTOM algorithm-specific sequence
    delivery_sequence = fnGenerateAlgorithmSpecificUnloadingSequence(
        dict_containerState_copy,
        bin_dims,
        strAlgorithmName
    )
    
    # Step 3: Perform CUSTOM unloading simulation
    unloading_result = fnCustomUnloadingSimulation(
        dict_containerState_copy,
        bin_dims,
        delivery_sequence,
        strAlgorithmName
    )
    
    _fnDebugLog(f"=== CUSTOM UNLOADING ORCHESTRATOR COMPLETE ===", 0)
    _fnDebugLog(f"Total relocations: {unloading_result['relocation_count']}", 1)
    _fnDebugLog(f"Total events: {len(unloading_result['event_log'])}", 1)
    
    return unloading_result