import time
import json
import numpy as np
from memory_profiler import memory_usage
from utils.data_loader import get_route_data_by_capacity
from utils.metrics_calculator import calculate_all_metrics
from utils.structures import Bin
from algorithms import pso, aco, hybrid_pso_aco

# This helper class is a placeholder for the 3D Bin from a library like Py3dbp.
# For this self-contained example, we simulate its behavior to focus on the algorithm integration.
class Bin:
    """A simulation of a 3D container to hold packed items."""
    def __init__(self, width, height, depth, capacity):
        self.width = width
        self.height = height
        self.depth = depth
        self.capacity = capacity
        self.items = [] # This will store the packed items with their positions.

    # In a real implementation, this would involve complex geometric calculations.
    # Here, we just add items assuming they fit until the volume limit is reached.
    def pack_items(self, items_to_pack):
        """
        Packs a list of items into the bin based on a simple volume-first heuristic.
        This simulates the core function of a 3D packing library.
        The packing order is determined by the algorithm's solution sequence.
        """
        current_volume = 0
        
        # This is where a real 3D packer (like Py3dbp) would perform its placement logic.
        # It would determine the x, y, z coordinates for each item.
        # To keep this example runnable without a complex dependency, we simulate a simple packing process.
        
        for item in items_to_pack:
            if current_volume + item['volume'] <= self.capacity:
                # Assign a dummy position. In reality, this would be the output of the packing algorithm.
                item['position'] = (0, 0, current_volume / (self.width * self.depth)) # Placeholder Z position
                self.items.append(item)
                current_volume += item['volume']
            else:
                # The item doesn't fit, so we stop packing this sequence here.
                break

def _get_container_dimensions(capacity):
    """
    Derives cuboid dimensions from a single volume value.
    This is a necessary step as the dataset provides volume but 3D packing requires dimensions.
    The chosen dimensions are based on typical delivery vehicle aspect ratios.
    """
    # Assuming a standard delivery van height and a reasonable width-to-depth ratio
    height = 180 # cm (approx 5' 11")
    # Using the formula: capacity = height * width * depth. Let depth = 1.5 * width
    # capacity = 180 * width * (1.5 * width) => capacity = 270 * width^2
    width = np.sqrt(capacity / 270)
    depth = 1.5 * width
    return round(width, 2), round(height, 2), round(depth, 2)


def solve_packing_problem(algorithm, capacity, route_data, package_data):
    """
    Orchestrates the entire solving process for a given problem instance.
    """
    # 1. Prepare the problem instance
    # Fetch the list of items (packages) for the given vehicle capacity.
    instance_data = get_route_data_by_capacity(capacity, route_data, package_data)
    if not instance_data or not instance_data.get("items"):
        return {"error": "Could not prepare data for the given capacity."}
    
    items = instance_data["items"]
    # Define the unloading order as the sequence of items provided in the dataset.
    # The goal is to pack items such that this unloading sequence is efficient.
    unloading_order = [item['id'] for item in items]
    
    # Get the 3D dimensions of the delivery vehicle.
    w, h, d = _get_container_dimensions(capacity)
    container = {"width": w, "height": h, "depth": d, "capacity": capacity}

    # Announce data preparation is complete
    print(f"[INFO] Prepared data for {len(items)} items.")

    # 2. Select and run the appropriate algorithm
    # Announce algorithm start
    print(f"[INFO] Starting '{algorithm}' algorithm...")
    # The `mem_usage` and timing logic directly addresses RQ3 (Scalability).
    start_time = time.time()
    
    # `memory_usage` runs the target function and records its peak memory consumption.
    mem_usage, solution = memory_usage(
        (run_algorithm, (algorithm, items, container)),
        retval=True,
        interval=0.1
    )
    
    end_time = time.time()
    computation_time = round(end_time - start_time, 4)
    # The peak memory usage is the max value recorded. Convert from MiB to a more readable format.
    peak_memory = round(max(mem_usage), 2)
    
    # Announce algorithm completion with key stats
    print(f"\n[INFO] Algorithm finished in {computation_time} seconds. Peak memory: {peak_memory} MiB.")

    if not solution or not solution.items:
        return {"error": "Algorithm failed to produce a valid solution."}

    # 3. Calculate metrics for the obtained solution
    # Announce metrics calculation start
    print("[INFO] Calculating performance metrics...")
    # The metrics calculation directly addresses RQ1 (Loading) and RQ2 (Unloading).
    metrics = calculate_all_metrics(solution, container, unloading_order)

    # 4. Format and return the final results
    # Announce completion
    print("[INFO] Process complete. Sending results to frontend.")
    # The structure of this dictionary matches the fields in the frontend's right panel.
    return {
        "metrics": {
            "execution_time": computation_time,
            "memory_usage": f"{peak_memory} MiB",
            **metrics
        },
        "solution_summary": {
            "vehicle_capacity": capacity,
            "total_product_volume": sum(item['volume'] for item in solution.items),
            "number_of_products_loaded": len(solution.items),
            "total_service_time": sum(item['service_time'] for item in solution.items),
        },
        "loaded_items": sorted(solution.items, key=lambda x: x['id']) # Sort for consistent display
    }

def run_algorithm(algorithm_name, items, container):
    """
    A wrapper function that calls the selected optimization algorithm.
    """
    solution_bin = Bin(
        width=container['width'], 
        height=container['height'], 
        depth=container['depth'],
        capacity=container['capacity']
    )
    
    # In this dictionary, we map the string name from the frontend
    # to the actual callable Python function for the algorithm.
    solver_map = {
        'PSO': pso.solve,
        'ACO': aco.solve,
        'PSO-ACO': hybrid_pso_aco.solve
    }

    if algorithm_name not in solver_map:
        raise ValueError(f"Unknown algorithm specified: {algorithm_name}")

    # Call the selected algorithm's main `solve` function
    solve_function = solver_map[algorithm_name]
    
    # The algorithm returns the best sequence of items found.
    # The fitness function used internally by each algorithm will simulate the packing
    # to guide the search, but here we do the final packing with the best sequence.
    best_item_sequence = solve_function(items, container)
    
    # Simulate the packing process with the best item sequence found by the algorithm.
    solution_bin.pack_items(best_item_sequence)

    return solution_bin