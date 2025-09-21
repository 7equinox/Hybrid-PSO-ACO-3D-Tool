import random
import numpy as np
from utils.structures import Bin
from utils.metrics_calculator import simulate_unloading

# --- Algorithm Parameters ---
# These values can be tuned to adjust the algorithm's performance
NUM_PARTICLES = 30 # The size of the swarm
MAX_ITERATIONS = 50 # Number of optimization loops
INERTIA_WEIGHT = 0.7 # w: Controls the influence of the previous velocity
COGNITIVE_COEFFICIENT = 1.5 # c1: How much a particle trusts its own best findings
SOCIAL_COEFFICIENT = 1.5 # c2: How much a particle trusts the swarm's best findings


def _calculate_fitness(item_sequence, container):
    """
    Evaluates how 'good' a given packing sequence is.
    This function is the core of the optimization, guiding the search.
    A higher fitness score is better.
    """
    temp_bin = Bin(container['width'], container['height'], container['depth'], container['capacity'])
    temp_bin.pack_items(item_sequence)
    
    # Calculate Volume Utilization
    packed_volume = sum(item['volume'] for item in temp_bin.items)
    utilization_score = (packed_volume / container['capacity'])
    
    # Calculate Unloading Efficiency (inversely related to relocation count)
    unloading_order = [item['id'] for item in item_sequence]
    unloading_results = simulate_unloading(temp_bin.items, unloading_order)
    
    # A high relocation count is bad, so we create a penalty.
    # Add 1 to avoid division by zero. Max possible relocations is ~N^2.
    # We normalize it to a 0-1 scale where 1 is best (0 relocations).
    relocation_penalty = unloading_results['relocations']
    efficiency_score = 1 - (relocation_penalty / (len(item_sequence)**2 + 1))
    
    # The fitness is a weighted sum of the two objectives.
    # The weights determine the priority. Here, we value them equally.
    fitness = (0.6 * utilization_score) + (0.4 * efficiency_score)
    
    # Return 0 if packing is infeasible
    return fitness if unloading_results['feasibility'] != "Feasible" else fitness


class Particle:
    """Represents a single potential solution (a particle) in the swarm."""
    def __init__(self, items):
        # The particle's position is a specific sequence (permutation) of items to be packed.
        self.position = random.sample(items, len(items))
        # Velocity represents a set of swaps needed to transform one position to another.
        self.velocity = []
        # Personal best is the best position this specific particle has found so far.
        self.pBest_pos = self.position
        self.pBest_fit = -1


def solve(items, container):
    """
    Main function to run the PSO algorithm.
    """
    swarm = [Particle(items) for _ in range(NUM_PARTICLES)]
    
    # Initialize global bests
    gBest_pos = None
    gBest_fit = -1

    # Announce the start of the specific algorithm
    print("[PSO] Starting PSO optimization...")

    # Main PSO loop
    for _ in range(MAX_ITERATIONS):
        for particle in swarm:
            # 1. Evaluate current position
            current_fitness = _calculate_fitness(particle.position, container)

            # 2. Update Personal Best (pBest)
            if current_fitness > particle.pBest_fit:
                particle.pBest_fit = current_fitness
                particle.pBest_pos = particle.position

            # 3. Update Global Best (gBest)
            if particle.pBest_fit > gBest_fit:
                gBest_fit = particle.pBest_fit
                gBest_pos = particle.pBest_pos
        
        # Print progress. `\r` moves the cursor to the line's start, `end=""` prevents a new line.
        print(f"\r[PSO] Iteration {_ + 1}/{MAX_ITERATIONS} | Best Fitness: {gBest_fit:.4f}", end="")

        # 4. Update particle velocities and positions
        for particle in swarm:
            # a. Calculate new velocity
            # Velocity is calculated as a series of "swap operators"
            inertia_component = particle.velocity # Swaps from last iteration
            
            # Cognitive component: swaps to move from current position to pBest
            cognitive_component = []
            if random.random() < COGNITIVE_COEFFICIENT:
                 cognitive_component = _get_swaps(particle.position, particle.pBest_pos)

            # Social component: swaps to move from current position to gBest
            social_component = []
            if random.random() < SOCIAL_COEFFICIENT:
                social_component = _get_swaps(particle.position, gBest_pos)

            # Combine the components to get the new velocity
            particle.velocity = (inertia_component[:int(len(inertia_component) * INERTIA_WEIGHT)] +
                                 cognitive_component + social_component)

            # b. Update position by applying the swaps
            new_position = particle.position[:]
            for i, j in particle.velocity:
                new_position[i], new_position[j] = new_position[j], new_position[i]
            particle.position = new_position

    # Add a final "complete" message with a newline to properly finish the progress line.
    print("\n[PSO] Optimization complete.")
    return gBest_pos

def _get_swaps(pos1, pos2):
    """Helper function to find the swaps needed to transform pos1 into pos2."""
    swaps = []
    # Create a mapping from item ID to its index in pos1
    mapping = {item['id']: i for i, item in enumerate(pos1)}
    temp_pos = pos1[:] # Make a mutable copy
    
    for i in range(len(temp_pos)):
        if temp_pos[i]['id'] != pos2[i]['id']:
            # Find where the correct item is currently located
            correct_item_current_idx = mapping[pos2[i]['id']]
            # Get the item that is in the wrong place
            item_to_swap = temp_pos[i]

            # Perform the swap
            temp_pos[i], temp_pos[correct_item_current_idx] = temp_pos[correct_item_current_idx], temp_pos[i]

            # Record the swap
            swaps.append((i, correct_item_current_idx))

            # Update the mapping to reflect the swap
            mapping[item_to_swap['id']] = correct_item_current_idx
            mapping[pos2[i]['id']] = i
    
    return swaps