# HYBRID-PSO-ACO-3D-TOOL/backend/utils/problem_solver.py

import time
import random
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# Import custom utilities and algorithm implementations
from backend.utils.data_loader import load_data
from backend.utils.metrics_calculator import calculate_all_metrics
from backend.algorithms.pso import run_pso
from backend.algorithms.aco import run_aco
from backend.algorithms.hybrid_pso_aco import run_hybrid_pso_aco

def solve_loading_problem(algorithm_name, capacity_cm3):
    """
    Main orchestrator function that manages the entire simulation process.
    It loads data, applies dynamic constraints, runs the selected algorithm,
    evaluates the result, and formats the output for the frontend.
    """
    
    # Stage 1: Load initial vehicle and package data for the scenario.
    vehicle_info, packages_info = load_data(capacity_cm3)
    if not vehicle_info or not packages_info:
        return {'error': 'Could not load data for the selected capacity.'}
        
    # Stage 2: Apply the Dynamic Constraint as specified in Chapter 3.
    # This simulates real-world disruptions like last-minute order cancellations
    # by randomly removing 10-20% of items before optimization begins.
    if len(packages_info) > 1:
        num_to_remove = int(len(packages_info) * random.uniform(0.1, 0.2))
        packages_to_load = random.sample(packages_info, len(packages_info) - num_to_remove)
    else:
        packages_to_load = packages_info

    # Prepare data for the py3dbp library. Each package becomes an 'Item'.
    items_to_pack = [
        Item(p['id'], p['width'], p['height'], p['depth'], 1) for p in packages_to_load
    ]
    
    the_bin = Bin(
        vehicle_info['id'], 
        vehicle_info['width'], 
        vehicle_info['height'], 
        vehicle_info['depth'], 
        1e6 # Max weight is not a constraint in this study.
    )

    # The Fitness Function: This function is the core of the evaluation.
    # It takes a potential solution (an item packing order) and returns a
    # multi-objective fitness value based on the metrics from Chapter 3.
    def evaluate_solution(item_order_indices):
        packer = Packer()
        packer.add_bin(the_bin)

        # A solution is a permutation of item indices, dictating packing order.
        for i in item_order_indices:
            packer.add_item(items_to_pack[i])
        
        # We control the order, so the packer's internal heuristics are disabled.
        packer.pack(bigger_first=False) 
        
        packed_items_list = packer.bins[0].items
        if not packed_items_list:
            # If nothing fits, it's the worst possible solution.
            # Fitness: (Volume, Relocations, Sequence Length)
            return 0, float('inf'), float('inf')
        
        # The metrics need the full info of only the successfully packed items.
        packed_item_ids = {item.name for item in packed_items_list}
        final_packages_info = [p for p in packages_to_load if p['id'] in packed_item_ids]

        metrics = calculate_all_metrics(
            packed_items_list,
            the_bin.get_volume(),
            final_packages_info
        )
        
        # Penalize infeasible solutions heavily to guide the search away from them.
        if metrics['unloading_feasibility'] == 'Infeasible':
             return 0, float('inf'), float('inf')

        # Return the three objectives for DEAP's multi-objective fitness evaluation.
        return (
            metrics['volume_utilization'], 
            metrics['relocation_count'], 
            metrics['unloading_sequence_length']
        )
    
    # Stage 3: Select and execute the chosen optimization algorithm.
    # This block measures scalability metrics (Computation Time and Memory Usage).
    algorithm_map = {'PSO': run_pso, 'ACO': run_aco, 'PSO-ACO': run_hybrid_pso_aco}
    algo_func = algorithm_map.get(algorithm_name)

    if not algo_func:
        return {'error': 'Invalid algorithm name specified.'}

    start_time = time.time()
    
    # The memory_profiler library directly measures peak RAM usage during execution,
    # satisfying a key requirement of the methodology for scalability analysis.
    # `retval=True` ensures the function's return value is passed through.
    mem_usage, (best_solution_indices, best_fitness) = memory_usage(
        (algo_func, (items_to_pack, evaluate_solution)),
        retval=True,
        max_usage=True,
        interval=0.1
    )
    
    computation_time = round(time.time() - start_time, 2)
    
    # Stage 4: Process and return the final, optimized solution.
    # Re-pack the single best solution found to get the final item positions.
    final_packer = Packer()
    final_packer.add_bin(the_bin)
    for i in best_solution_indices:
        final_packer.add_item(items_to_pack[i])
    final_packer.pack(bigger_first=False)

    final_packed_items_details = []
    total_packed_volume = 0
    total_packed_service_time = 0
    
    # Enrich the output data with positioning info for visualization.
    for item in final_packer.bins[0].items:
        original_package = next((p for p in packages_to_load if p['id'] == item.name), None)
        if original_package:
            # Cast positions to float for JSON compatibility
            pos = [float(p) for p in item.position]
            final_packed_items_details.append({
                **original_package,
                "position_x": pos[0],
                "position_y": pos[1],
                "position_z": pos[2]
            })
            total_packed_volume += original_package['volume']
            total_packed_service_time += original_package['service_time']
    
    # Compile the final report for the frontend.
    return {
        'algorithm_name': algorithm_name,
        'metrics': {
            'computation_time': computation_time,
            'memory_usage_mb': round(mem_usage, 2),
            'volume_utilization': best_fitness[0],
            'relocation_count': best_fitness[1],
            'unloading_feasibility': "Feasible" if best_fitness[1] != float('inf') else "Infeasible",
            'unloading_sequence_length': best_fitness[2]
        },
        'packed_items': final_packed_items_details,
        'vehicle_info': {
            'capacity_cm3': capacity_cm3,
            'num_packages_loaded': len(final_packed_items_details),
            'total_packed_volume': round(total_packed_volume),
            'total_packed_service_time': round(total_packed_service_time)
        }
    }