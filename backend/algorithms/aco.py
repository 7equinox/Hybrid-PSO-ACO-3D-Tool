import random
import numpy as np
from utils.structures import Bin
from utils.metrics_calculator import simulate_unloading

# --- Algorithm Parameters ---
# These values can be tuned to adjust the algorithm's performance
NUM_ANTS = 25 # The number of ants in the colony
MAX_ITERATIONS = 50 # Number of cycles for the ants to build solutions
EVAPORATION_RATE = 0.5 # rho: How fast pheromone trails fade
PHEROMONE_INTENSITY = 1.0 # Q: A constant affecting the amount of deposited pheromone
ALPHA = 1.0 # Controls the influence of the pheromone trail
BETA = 2.0 # Controls the influence of heuristic information (e.g., item volume)

def _calculate_fitness(item_sequence, container):
    """
    Evaluates the quality of a sequence, identical to the fitness function in PSO.
    This ensures that both standalone algorithms are optimizing for the same objectives,
    allowing for a fair comparison.
    """
    temp_bin = Bin(container['width'], container['height'], container['depth'], container['capacity'])
    temp_bin.pack_items(item_sequence)
    
    packed_volume = sum(item['volume'] for item in temp_bin.items)
    utilization_score = (packed_volume / container['capacity'])
    
    unloading_order = [item['id'] for item in item_sequence]
    unloading_results = simulate_unloading(temp_bin.items, unloading_order)
    
    if unloading_results['feasibility'] != "Feasible":
        return 0 # A sequence that is not fully unloadable gets the worst possible score

    relocation_penalty = unloading_results['relocations']
    efficiency_score = 1 - (relocation_penalty / (len(item_sequence)**2 + 1))
    
    fitness = (0.6 * utilization_score) + (0.4 * efficiency_score)
    return fitness


class Ant:
    """Represents a single ant, which builds a candidate solution."""
    def __init__(self, num_items):
        self.tour = [] # The sequence of items (nodes) visited
        self.visited = [False] * num_items

    def add_to_tour(self, item_index):
        """Adds an item to the ant's tour and marks it as visited."""
        self.tour.append(item_index)
        self.visited[item_index] = True


def solve(items, container):
    """
    Main function to run the Ant Colony Optimization algorithm.
    """
    num_items = len(items)
    
    # 1. Initialize pheromone matrix and heuristic information
    # The pheromone matrix stores the learned desirability of transitions between items.
    pheromone_matrix = np.ones((num_items, num_items))
    
    # Heuristic info: We prefer to pack larger items first as this is a common packing heuristic.
    # The heuristic value for choosing item j is proportional to its volume.
    heuristic_info = np.array([item['volume'] for item in items])
    heuristic_info[heuristic_info == 0] = 1e-10 # Avoid division by zero for items with no volume
    
    best_solution = None
    best_fitness = -1

    # Announce start
    print("[ACO] Starting ACO optimization...")

    # 2. Main ACO loop
    for _ in range(MAX_ITERATIONS):
        colony = [Ant(num_items) for _ in range(NUM_ANTS)]
        ant_solutions = []

        # a. Each ant constructs a solution
        for ant in colony:
            # Start each ant at a random item
            start_node = random.randint(0, num_items - 1)
            ant.add_to_tour(start_node)

            while len(ant.tour) < num_items:
                current_node = ant.tour[-1]
                
                # Calculate selection probabilities for the next item
                probabilities = []
                for next_node in range(num_items):
                    if not ant.visited[next_node]:
                        pheromone_level = pheromone_matrix[current_node][next_node] ** ALPHA
                        heuristic_value = heuristic_info[next_node] ** BETA
                        probabilities.append((next_node, pheromone_level * heuristic_value))
                
                # Normalize probabilities
                total_prob = sum(p for _, p in probabilities)
                if total_prob == 0: # If all remaining nodes have 0 probability, pick randomly
                     next_node = random.choice([p[0] for p in probabilities])
                else:
                    nodes, probs = zip(*probabilities)
                    probs = np.array(probs) / total_prob
                    next_node = np.random.choice(nodes, p=probs)
                
                ant.add_to_tour(next_node)
            
            # Ant has completed its tour, convert indices back to item objects
            item_sequence = [items[i] for i in ant.tour]
            fitness = _calculate_fitness(item_sequence, container)
            ant_solutions.append((item_sequence, fitness))

        # b. Update the global best solution if a better one was found
        current_best_ant_solution, current_best_ant_fitness = max(ant_solutions, key=lambda x: x[1])
        if current_best_ant_fitness > best_fitness:
            best_fitness = current_best_ant_fitness
            best_solution = current_best_ant_solution

        # Print progress for the current iteration
        print(f"\r[ACO] Iteration {_ + 1}/{MAX_ITERATIONS} | Best Fitness: {best_fitness:.4f}", end="")

        # c. Update pheromone matrix
        # Pheromone Evaporation
        pheromone_matrix *= (1 - EVAPORATION_RATE)

        # Pheromone Deposition
        for solution, fitness in ant_solutions:
            if fitness > 0: # Only good solutions should deposit pheromones
                # Create a map from item ID to index for quick lookups
                id_to_index_map = {item['id']: i for i, item in enumerate(items)}
                
                for i in range(num_items - 1):
                    from_node_idx = id_to_index_map[solution[i]['id']]
                    to_node_idx = id_to_index_map[solution[i+1]['id']]
                    # Deposit pheromone proportional to the solution's quality
                    pheromone_matrix[from_node_idx][to_node_idx] += (PHEROMONE_INTENSITY * fitness)

    # Add final completion message
    print("\n[ACO] Optimization complete.")
    return best_solution