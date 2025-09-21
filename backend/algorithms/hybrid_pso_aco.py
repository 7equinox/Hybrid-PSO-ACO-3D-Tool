import random
import numpy as np
from utils.structures import Bin
from algorithms.pso import Particle, _get_swaps, _calculate_fitness as _pso_fitness
from algorithms.aco import PHEROMONE_INTENSITY, EVAPORATION_RATE

# --- Hybrid Algorithm Parameters ---
# Inherits some parameters from PSO and ACO
NUM_PARTICLES = 30
MAX_ITERATIONS = 50
INERTIA_WEIGHT = 0.5
COGNITIVE_COEFFICIENT = 1.4
# The social coefficient is now augmented by the pheromone influence
SOCIAL_COEFFICIENT = 0.8 
PHEROMONE_INFLUENCE_FACTOR = 0.6 # How much pheromones guide the social pull

def solve(items, container):
    """
    Main function to run the Hybrid PSO-ACO algorithm.
    This follows the Pheromone-Augmented Particle Swarm Optimization (PACO) architecture.
    """
    num_items = len(items)
    
    # --- Initialization ---
    # 1. Initialize PSO swarm (same as standard PSO)
    swarm = [Particle(items) for _ in range(NUM_PARTICLES)]
    
    # 2. Initialize pheromone matrix (as in ACO, uniform at the start)
    pheromone_matrix = np.ones((num_items, num_items))
    
    # Global best trackers
    gBest_pos = None
    gBest_fit = -1

    # Announce start
    print("[Hybrid] Starting Hybrid PSO-ACO optimization...")

    # Map item IDs to indices for efficient pheromone matrix updates
    id_to_index_map = {item['id']: i for i, item in enumerate(items)}

    # --- Main Hybrid Loop ---
    for iteration in range(MAX_ITERATIONS):
        # --- Standard PSO Evaluation Phase ---
        particle_fitnesses = []
        for particle in swarm:
            current_fitness = _pso_fitness(particle.position, container)
            particle_fitnesses.append(current_fitness)
            
            if current_fitness > particle.pBest_fit:
                particle.pBest_fit = current_fitness
                particle.pBest_pos = particle.position

            if particle.pBest_fit > gBest_fit:
                gBest_fit = particle.pBest_fit
                gBest_pos = particle.pBest_pos
        
        # Print progress after evaluating all particles in the iteration
        print(f"\r[Hybrid] Iteration {iteration + 1}/{MAX_ITERATIONS} | Best Fitness: {gBest_fit:.4f}", end="")

        # --- Weighted Pheromone Update (ACO integration) ---
        # 1. Pheromone Evaporation (applies to the entire matrix)
        pheromone_matrix *= (1 - EVAPORATION_RATE)

        # 2. Pheromone Deposition by Elite Particles
        # Rank particles based on their current fitness
        sorted_indices = np.argsort(particle_fitnesses)[::-1] # Descending order of fitness
        num_elites = max(1, int(0.2 * NUM_PARTICLES)) # Top 20% of particles are elites

        for i in range(num_elites):
            elite_particle_index = sorted_indices[i]
            elite_particle = swarm[elite_particle_index]
            fitness = particle_fitnesses[elite_particle_index]

            # The pheromone contribution is weighted by the particle's performance
            # (Elitist, Rank-Based Update)
            if fitness > 0:
                solution_path = elite_particle.position
                for j in range(num_items - 1):
                    from_node_idx = id_to_index_map[solution_path[j]['id']]
                    to_node_idx = id_to_index_map[solution_path[j+1]['id']]
                    pheromone_matrix[from_node_idx][to_node_idx] += (PHEROMONE_INTENSITY * fitness)

        # --- Pheromone-Augmented Velocity and Position Update ---
        for particle in swarm:
            # Generate a "pheromone-guided" solution to influence the social component.
            # This solution is built stochastically using the updated pheromone matrix,
            # much like a single ant builds a tour.
            pheromone_guided_pos = _construct_solution_with_pheromones(items, pheromone_matrix, id_to_index_map)

            # --- Update Velocity (Augmented PSO Equation) ---
            # Inertia and Cognitive components remain the same as standard PSO
            inertia_component = particle.velocity
            cognitive_component = []
            if random.random() < COGNITIVE_COEFFICIENT:
                cognitive_component = _get_swaps(particle.position, particle.pBest_pos)

            # Social component is now a blend of gBest and the pheromone-guided solution
            social_swaps_gBest = _get_swaps(particle.position, gBest_pos)
            social_swaps_pheromone = _get_swaps(particle.position, pheromone_guided_pos)
            
            # The particle is pulled towards the global best AND the collective wisdom in the pheromones
            social_component = (social_swaps_gBest[:int(len(social_swaps_gBest) * SOCIAL_COEFFICIENT)] +
                                social_swaps_pheromone[:int(len(social_swaps_pheromone) * PHEROMONE_INFLUENCE_FACTOR)])

            # Combine to get the final velocity
            particle.velocity = (inertia_component[:int(len(inertia_component) * INERTIA_WEIGHT)] +
                                 cognitive_component + social_component)

            # --- Update Position (Standard PSO) ---
            new_position = particle.position[:]
            for i, j in particle.velocity:
                 # Ensure indices are valid before swapping
                if 0 <= i < len(new_position) and 0 <= j < len(new_position):
                    new_position[i], new_position[j] = new_position[j], new_position[i]
            particle.position = new_position

    # Add final completion message
    print("\n[Hybrid] Optimization complete.")
    return gBest_pos

def _construct_solution_with_pheromones(items, pheromone_matrix, id_to_index_map):
    """
    Builds a single solution probabilistically using only the pheromone matrix.
    This simulates how an ant from ACO would build a tour.
    """
    num_items = len(items)
    tour_indices = []
    visited = [False] * num_items

    # Start at a random node
    start_node = random.randint(0, num_items - 1)
    tour_indices.append(start_node)
    visited[start_node] = True
    
    while len(tour_indices) < num_items:
        current_node = tour_indices[-1]
        probabilities = []
        for next_node in range(num_items):
            if not visited[next_node]:
                # Probability is based solely on pheromone level here
                prob = pheromone_matrix[current_node][next_node]
                probabilities.append((next_node, prob))
        
        # Normalize and select next node
        total_prob = sum(p for _, p in probabilities)
        if total_prob == 0:
            next_node = random.choice([p[0] for p in probabilities if p[0] is not None])
        else:
            nodes, probs = zip(*probabilities)
            probs = np.array(probs) / total_prob
            next_node = np.random.choice(nodes, p=probs)
        
        tour_indices.append(next_node)
        visited[next_node] = True

    # Convert the tour of indices back to a list of item objects
    return [items[i] for i in tour_indices]