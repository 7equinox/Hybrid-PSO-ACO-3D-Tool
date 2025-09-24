# HYBRID-PSO-ACO-3D-TOOL/backend/utils/metrics_calculator.py

import numpy as np

def calculate_all_metrics(packed_items, bin_volume, all_packages_info):
    """
    Master function to compute all performance metrics defined in Chapter 3.
    This centralizes evaluation for any given packing solution.
    'packed_items' is the list of successfully placed py3dbp.Item objects.
    'all_packages_info' is the list of dictionaries for all packages loaded for this run.
    """
    
    # --- Metric 1: Volume Utilization ---
    # As per methodology, this measures the percentage of container space occupied.
    total_packed_volume = sum(item.get_volume() for item in packed_items)
    volume_utilization = float((total_packed_volume / bin_volume) * 100) if bin_volume > 0 else 0.0
    
    # Create a lookup map for quick access to package metadata (like stop_id).
    packages_info_map = {p['id']: p for p in all_packages_info}

    # Generate the delivery sequence from the items that were actually packed.
    packed_stops = {packages_info_map.get(item.name, {}).get('stop_id') for item in packed_items}
    # A realistic delivery sequence is sorted, representing an optimized route plan.
    delivery_sequence = sorted(list(filter(None, packed_stops)))
    
    # --- Metrics 2, 3, 4: Unloading Simulation ---
    # These metrics are derived from simulating the physical unloading process.
    relocation_count, unloading_sequence_length, is_feasible = simulate_unloading(packed_items, delivery_sequence, packages_info_map)

    return {
        'volume_utilization': round(volume_utilization, 2),
        'relocation_count': relocation_count,
        # A binary metric indicating if the entire load could be unloaded.
        'unloading_feasibility': "Feasible" if is_feasible else "Infeasible",
        # Total number of moves (removals + relocations) to empty the vehicle.
        'unloading_sequence_length': unloading_sequence_length
    }

def simulate_unloading(packed_items, delivery_sequence, packages_info_map):
    """
    Simulates the unloading process to measure operational efficiency.
    It assesses whether items can be accessed in delivery order without deadlocks.
    Unloading is assumed to occur from the front of the cargo space (largest X-coordinate).
    """
    
    if not packed_items:
        return 0, 0, True # An empty truck is trivially feasible.

    # Create a copy of the items in the bin to simulate their removal.
    items_in_bin = {item.name: item for item in packed_items}

    relocations = 0
    sequence_length = 0
    
    # Process stops one by one according to the delivery plan.
    for target_stop_id in delivery_sequence:
        # Get all items destined for the current stop.
        items_for_this_stop_ids = [
            item.name for item in items_in_bin.values() 
            if packages_info_map.get(item.name, {}).get('stop_id') == target_stop_id
        ]
        
        # Unload items at a stop starting from the most accessible (closest to door).
        # We sort by the front-face x-coordinate (position[0]), descending.
        items_for_this_stop_ids.sort(
            key=lambda item_id: float(items_in_bin[item_id].position[0]), reverse=True
        )

        for target_item_id in items_for_this_stop_ids:
            if target_item_id not in items_in_bin:
                continue  # Item was already relocated and removed.
            
            target_item = items_in_bin[target_item_id]
            blocking_items_ids = []
            
            # CRITICAL FIX: Correctly identify items blocking the target.
            # An item is a "blocker" if it is physically located between the
            # target item and the vehicle's door (assumed at x_max).
            
            tx, ty, tz = map(float, target_item.position)
            # Use get_dimension() to account for item rotation during packing.
            tdx, tdy, tdz = map(float, target_item.get_dimension())

            for other_id, other_item in items_in_bin.items():
                if other_id == target_item_id:
                    continue

                ox, oy, oz = map(float, other_item.position)
                odx, ody, odz = map(float, other_item.get_dimension())

                # A blocker must be "in front of" the target (larger x-coordinate)
                # AND must overlap in the Y-Z plane.
                is_in_front = ox > tx
                y_overlap = (ty < oy + ody) and (oy < ty + tdy)
                z_overlap = (tz < oz + odz) and (oz < tz + tdz)
                
                if is_in_front and y_overlap and z_overlap:
                    blocking_items_ids.append(other_id)

            # Relocate blocking items. They must also be removed from most- to least-accessible.
            blocking_items_ids.sort(
                key=lambda item_id: float(items_in_bin[item_id].position[0]), reverse=True
            )

            for blocker_id in blocking_items_ids:
                if blocker_id in items_in_bin:
                    relocations += 1
                    sequence_length += 1 # Each relocation is one move.
                    del items_in_bin[blocker_id] 
            
            # After clearing blockers, remove the target item itself.
            if target_item_id in items_in_bin:
                sequence_length += 1 # Each successful retrieval is one move.
                del items_in_bin[target_item_id]

    # Unloading is feasible only if every packed item could be successfully removed.
    is_feasible = not items_in_bin
    
    return relocations, sequence_length, is_feasible