# HYBRID-PSO-ACO-3D-TOOL/backend/utils/problem_solver.py

import time
import random
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# Import custom modules
from backend.utils.data_loader import load_data
from backend.utils.metrics_calculator import calculate_all_metrics

# Import the algorithm functions
from backend.algorithms.pso import run_pso
from backend.algorithms.aco import run_aco
from backend.algorithms.hybrid_pso_aco import run_hybrid_pso_aco


def solve_loading_problem(algorithm_name, capacity_cm3):
    """
    The main orchestrator function for solving the loading problem.
    It loads data, runs the selected algorithm, and returns the results.
    """
    
    # Load vehicle and package data
    vehicle_info, packages_info = load_data(capacity_cm3)
    if not vehicle_info or not packages_info:
        return {'error': 'Could not load data for the selected capacity.'}
        
    # --- Dynamic Constraint Simulation ---
    # As per the methodology, simulate a last-minute change.
    # We remove 10-20% of the items to see how the algorithm adapts.
    num_to_remove = int(len(packages_info) * random.uniform(0.1, 0.2))
    packages_to_load = random.sample(packages_info, len(packages_info) - num_to_remove)

    # Prepare data for the 3D bin packing library
    items_to_pack = [
        Item(
            name=p['id'],
            width=p['width'],
            height=p['height'],
            depth=p['depth'],
            weight=1 # Weight is not used in this problem but is required by the library
        ) for p in packages_to_load
    ]
    
    the_bin = Bin(
        name=vehicle_info['id'],
        width=vehicle_info['width'],
        height=vehicle_info['height'],
        depth=vehicle_info['depth'],
        max_weight=100000 
    )

    # This is the fitness function that all algorithms will use to evaluate a solution.
    # A "solution" is a permutation of item indices.
    def evaluate_solution(item_order_indices):
        packer = Packer()
        packer.add_bin(the_bin)

        # Pack items according to the permutation provided by the algorithm
        for i in item_order_indices:
            packer.add_item(items_to_pack[i])
        
        packer.pack(bigger_first=False) # We control the order, so packer's heuristic is off
        
        packed_items_list = packer.bins[0].items
        if not packed_items_list:
            # If no items could be packed, this is the worst possible solution
            return 0, float('inf'), float('inf')
        
        # Build a list of full package info for only the items that were successfully packed.
        packed_items_full_info = [
            p for p in packages_to_load 
            if p['id'] in {item.name for item in packed_items_list}
        ]
        
        # Create a mapping from package ID to its details for quick lookups
        packages_info_map = {p['id']: p for p in packed_items_full_info}
        
        delivery_sequence = sorted(list(set(p['stop_id'] for p in packed_items_full_info)))
        
        # --- FIX ---
        # The function call is now corrected:
        # 1. The keyword is 'packed_items', matching the function definition.
        # 2. We pass the actual list of py3dbp.Item objects.
        # 3. A lookup map is passed to provide extra details (like stop_id) to the metric calculator.
        metrics = calculate_all_metrics(
            packed_items=packed_items_list,
            bin_volume=the_bin.get_volume(),
            delivery_sequence=delivery_sequence,
            packages_info_map=packages_info_map 
        )
        
        # If the solution is infeasible, apply a heavy penalty to its fitness
        if metrics['unloading_feasibility'] == 'Infeasible':
             return 0, float('inf'), float('inf')

        # The fitness value returned to the DEAP framework
        return (
            metrics['volume_utilization'], 
            metrics['relocation_count'], 
            metrics['unloading_sequence_length']
        )
    
    # --- Select and Run Algorithm ---
    # This block measures computation time and memory usage.
    algo_func = None
    if algorithm_name == 'PSO':
        algo_func = run_pso
    elif algorithm_name == 'ACO':
        algo_func = run_aco
    elif algorithm_name == 'PSO-ACO':
        algo_func = run_hybrid_pso_aco

    if not algo_func:
        return {'error': 'Invalid algorithm name specified.'}

    start_time = time.time()
    
    bin_dimensions = (the_bin.width, the_bin.height, the_bin.depth)
    
    # The `memory_usage` function executes the target function and records its peak memory consumption.
    mem_usage, (best_solution_indices, best_fitness) = memory_usage(
        (algo_func, (items_to_pack, bin_dimensions, evaluate_solution)),
        retval=True,
        max_usage=True
    )
    
    end_time = time.time()
    computation_time = round(end_time - start_time, 2)
    
    # --- Process Final Solution ---
    # Repack the best solution found by the algorithm to get the final state
    final_packer = Packer()
    final_packer.add_bin(the_bin)
    for i in best_solution_indices:
        final_packer.add_item(items_to_pack[i])
    final_packer.pack(bigger_first=False)

    final_packed_items = []
    total_packed_volume = 0
    total_packed_service_time = 0

    for item in final_packer.bins[0].items:
        original_package = next((p for p in packages_to_load if p['id'] == item.name), None)
        if original_package:
            final_packed_items.append({
                **original_package,
                "position_x": item.position[0],
                "position_y": item.position[1],
                "position_z": item.position[2]
            })
            total_packed_volume += original_package['volume']
            total_packed_service_time += original_package['service_time']

    final_metrics = {
        'volume_utilization': best_fitness[0],
        'relocation_count': best_fitness[1],
        'unloading_feasibility': "Feasible" if best_fitness[1] != float('inf') else "Infeasible",
        'unloading_sequence_length': best_fitness[2]
    }

    # Structure the final output to be sent to the frontend
    return {
        'algorithm_name': algorithm_name,
        'metrics': {
            'computation_time': computation_time,
            'memory_usage_mb': round(mem_usage, 2),
            **final_metrics
        },
        'packed_items': final_packed_items,
        'vehicle_info': {
            'capacity_cm3': capacity_cm3,
            'num_packages_loaded': len(final_packed_items),
            'total_packed_volume': round(total_packed_volume),
            'total_packed_service_time': round(total_packed_service_time)
        }
    }