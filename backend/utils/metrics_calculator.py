import copy

def calculate_volume_utilization(packed_items, container_capacity):
    """
    Calculates the percentage of container space occupied by packed items.
    Addresses metric 1a in the Statement of the Problem.
    """
    total_items_volume = sum(item['volume'] for item in packed_items)
    utilization = (total_items_volume / container_capacity) * 100
    return f"{round(utilization, 2)}%"


def _is_accessible(item_to_check, all_items_in_bin):
    """
    A simplified check to see if an item can be removed.
    In a real 3D system, this would involve checking for items positioned
    directly above the target item along the exit axis (e.g., the z-axis).
    """
    # This is a placeholder for complex geometric calculations.
    # For this simulation, we'll assume an item is accessible if it's
    # one of the last few items packed, which is a common LIFO-like scenario.
    # This simplification allows us to demonstrate the logic for relocation and feasibility.
    item_index = -1
    for i, item in enumerate(all_items_in_bin):
        if item['id'] == item_to_check['id']:
            item_index = i
            break
            
    # For simulation, let's assume the last 20% of packed items are "on top" and thus accessible.
    return item_index >= (len(all_items_in_bin) * 0.8)


def simulate_unloading(packed_items, unloading_order):
    """
    Simulates the unloading process to calculate feasibility, relocation count, and sequence length.
    This is the core logic for answering metrics 1b, 1c, 1d, 2a, 2b, and 2c.
    """
    # Create a deep copy of the packed items to simulate removals without affecting the original data
    current_bin_state = copy.deepcopy(packed_items)
    
    relocation_count = 0
    unloading_sequence_length = 0
    
    # Iterate through the required unloading sequence
    for target_item_id in unloading_order:
        # Find the target item in the current state of the bin
        target_item = next((item for item in current_bin_state if item['id'] == target_item_id), None)
        
        # If the item to be unloaded isn't in the bin, something went wrong with the packing.
        if not target_item:
            return {"feasibility": "Infeasible (Item Missing)", "relocations": -1, "sequence_length": -1}
        
        # Check if the target item is accessible
        while not _is_accessible(target_item, current_bin_state):
            # If not accessible, we need to relocate a blocking item.
            # In this simulation, we identify the "last" packed item as the blocker.
            if not current_bin_state: # Should not happen if target_item exists
                return {"feasibility": "Infeasible (Deadlock)", "relocations": relocation_count, "sequence_length": unloading_sequence_length}

            blocking_item = current_bin_state.pop() # Remove the "top-most" item
            relocation_count += 1
            unloading_sequence_length += 1 # A relocation is an action
            
            # This logic simulates trying to put the blocking item back, which we'll omit for simplicity.
            # In a real scenario, you'd find a new temp location. Here, we just count the removal.

        # The item is now accessible, so we can unload it.
        # Find its index and remove it.
        item_index_to_remove = -1
        for i, item in enumerate(current_bin_state):
             if item['id'] == target_item_id:
                item_index_to_remove = i
                break
        
        if item_index_to_remove != -1:
            current_bin_state.pop(item_index_to_remove)
            unloading_sequence_length += 1 # The actual unloading is one action
        else:
             return {"feasibility": "Infeasible (Item Vanished)", "relocations": -1, "sequence_length": -1}

    # If the loop completes, it means all items were successfully unloaded in order.
    return {
        "feasibility": "Feasible",
        "relocations": relocation_count,
        "sequence_length": unloading_sequence_length
    }


def calculate_all_metrics(solution_bin, container, unloading_order):
    """
    Top-level function to compute and return all performance metrics.
    """
    packed_items = solution_bin.items
    container_capacity = container['capacity']

    # Calculate volume utilization
    volume_utilization = calculate_volume_utilization(packed_items, container_capacity)

    # Simulate unloading to get the other metrics
    unloading_results = simulate_unloading(packed_items, unloading_order)

    return {
        "volume_utilization": volume_utilization,
        "relocation_count": unloading_results['relocations'],
        "unloading_feasibility": unloading_results['feasibility'],
        "unloading_sequence_length": unloading_results['sequence_length']
    }