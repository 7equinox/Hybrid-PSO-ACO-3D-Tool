# HYBRID-PSO-ACO-3D-TOOL/backend/utils/metrics_calculator.py

import numpy as np

def calculate_all_metrics(packed_items, bin_volume, delivery_sequence, packages_info_map):
    """
    A master function that calculates all performance metrics for a given packing solution.
    'packed_items' is a list of py3dbp.Item objects.
    'packages_info_map' is a dictionary mapping item.name (ID) to its full info (like stop_id).
    """
    
    # --- Metric 1: Volume Utilization ---
    total_packed_volume = sum(item.get_volume() for item in packed_items)
    
    # The result of the division using py3dbp's Decimal values is a Decimal.
    # We must explicitly cast the final result to float() before rounding.
    volume_utilization = float((total_packed_volume / bin_volume) * 100) if bin_volume > 0 else 0.0
    
    # --- Metrics 2, 3, 4: Unloading Simulation ---
    relocation_count, unloading_sequence_length, is_feasible = simulate_unloading(packed_items, delivery_sequence, packages_info_map)

    return {
        'volume_utilization': round(volume_utilization, 2),
        'relocation_count': relocation_count,
        'unloading_feasibility': "Feasible" if is_feasible else "Infeasible",
        'unloading_sequence_length': unloading_sequence_length
    }

def simulate_unloading(packed_items, delivery_sequence, packages_info_map):
    """
    Simulates the unloading process. This function now works directly with py3dbp.Item objects
    by using the packages_info_map to retrieve metadata like 'stop_id'.
    """
    
    if not packed_items:
        return 0, 0, True

    items_in_bin = {item.name: item for item in packed_items}

    relocations = 0
    sequence_length = 0
    
    for target_stop_id in delivery_sequence:
        items_for_this_stop = [
            item_id for item_id in items_in_bin 
            if packages_info_map.get(item_id, {}).get('stop_id') == target_stop_id
        ]
        
        items_for_this_stop.sort(key=lambda item_id: float(items_in_bin[item_id].position[0]), reverse=True)

        for target_item_id in items_for_this_stop:
            if target_item_id not in items_in_bin:
                continue 
            
            target_item = items_in_bin[target_item_id]
            
            blocking_items = []
            
            # --- FIX ---
            # Cast all position and dimension values to float() immediately upon retrieval.
            # This ensures all subsequent arithmetic operations (+, >) are performed
            # on compatible number types (float with float).
            tx, ty, tz = map(float, target_item.position)
            tdx, tdy, tdz = map(float, target_item.get_dimension()) 

            for other_id, other_item in items_in_bin.items():
                if other_id == target_item_id:
                    continue

                ox, oy, oz = map(float, other_item.position)
                odx, ody, odz = map(float, other_item.get_dimension())

                # Now, the comparison `ox + odx > tx + tdx` is valid.
                if ox + odx > tx + tdx : 
                    y_overlap = (ty < oy + ody) and (oy < ty + tdy)
                    z_overlap = (tz < oz + odz) and (oz < tz + tdz)
                    if y_overlap and z_overlap:
                        blocking_items.append(other_id)

            blocking_items.sort(key=lambda item_id: float(items_in_bin[item_id].position[0]), reverse=True)

            for blocker_id in blocking_items:
                if blocker_id in items_in_bin:
                    relocations += 1
                    sequence_length += 1 
                    del items_in_bin[blocker_id] 

            sequence_length += 1
            del items_in_bin[target_item_id]

    is_feasible = len(items_in_bin) == 0
    
    return relocations, sequence_length, is_feasible