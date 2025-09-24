# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/hybrid_pso_aco.py

import random
import numpy as np
from deap import base, tools
# Import the custom DEAP creator object from our base configuration.
from .base import creator

# --- Hybrid PSO-ACO Algorithm ---
# This implementation reflects the Pheromone-Augmented Particle Swarm Optimization (PACO)
# framework detailed in the Hybrid PSO-ACO System Architecture section of Chapter 3.
# It integrates ACO's pheromone mechanism directly into the PSO loop.

def run_hybrid_pso_aco(items, evaluate_solution, num_particles=30, max_generations=50, evaporation_rate=0.2):
    """
    Executes the proposed hybrid PSO-ACO algorithm.
    """
    num_items = len(items)
    
    # Initialize DEAP toolbox, similar to the standalone PSO.
    toolbox = base.Toolbox()
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)
    toolbox.register("evaluate", evaluate_solution)

    # --- Initialization Phase (from Hybrid System Architecture) ---
    # 1. Generate a swarm of particles (candidate solutions).
    swarm = toolbox.population(n=num_particles)
    # 2. Initialize the pheromone matrix uniformly to avoid early bias.
    pheromone_matrix = np.ones((num_items, num_items))
    # 3. Register the HYBRID update rule, passing the pheromone matrix to it.
    toolbox.register("update", update_particle_hybrid, pheromone_matrix=pheromone_matrix, phi1=1.5, phi2=1.5, phi3=2.0)
    gbest = None

    # --- Main Optimization Loop ---
    for gen in range(max_generations):
        # 1. Evaluate particle solutions using the multi-objective fitness function.
        for part in swarm:
            if not part.fitness.valid:
                part.fitness.values = toolbox.evaluate(part)

            # 2. Update pBest and gBest based on standard PSO rules.
            if not part.pbest or part.pbest.fitness < part.fitness:
                part.pbest = creator.Particle(part)
                part.pbest.fitness.values = part.fitness.values
            if not gbest or gbest.fitness < part.fitness:
                gbest = creator.Particle(part)
                gbest.fitness.values = part.fitness.values
        
        # --- Pheromone Update Mechanism (Integration of ACO) ---
        # a) Pheromone Evaporation.
        pheromone_matrix *= (1 - evaporation_rate)
        
        # b) Weighted Pheromone Update using Elite Particles.
        # This reflects the rank-based update rules inspired by Abitz et al. (2020).
        # We sort the swarm to identify the best-performing ("elite") particles.
        sorted_swarm = sorted(swarm, key=lambda p: p.fitness.values[0], reverse=True)
        num_elites = max(1, int(0.2 * len(swarm))) # Top 20% are elites.

        for elite_particle in sorted_swarm[:num_elites]:
            # The deposit amount is scaled by the elite particle's performance.
            deposit_amount = elite_particle.fitness.values[0]
            if deposit_amount > 0:
                for i in range(num_items - 1):
                    pheromone_matrix[elite_particle[i]][elite_particle[i+1]] += deposit_amount

        # 3. Update Particle Velocities and Positions using the augmented equation.
        for part in swarm:
            toolbox.update(part, gbest)

    # Termination: After max generations, return the best solution found.
    return gbest, gbest.fitness.values


def update_particle_hybrid(part, gbest, pheromone_matrix, phi1, phi2, phi3, w=0.5):
    """
    This is the augmented PSO update equation that incorporates a pheromone component,
    creating the hybrid behavior as seen in studies by Song et al. (2023).
    The particle's movement is now influenced by three forces:
    1. Cognitive (pBest): Its own past success.
    2. Social (gBest): The swarm's collective success.
    3. Pheromone Guidance: The historically successful paths discovered by the colony.
    """
    num_items = len(part)
    
    # --- Cognitive Component (from pBest) ---
    pbest_swaps = []
    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        num_swaps = int(phi1 * random.random() * len(pbest_diff) / 2)
        for _ in range(num_swaps):
            pbest_swaps.append(tuple(random.sample(pbest_diff, 2)))

    # --- Social Component (from gBest) ---
    gbest_swaps = []
    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        num_swaps = int(phi2 * random.random() * len(gbest_diff) / 2)
        for _ in range(num_swaps):
            gbest_swaps.append(tuple(random.sample(gbest_diff, 2)))
    
    # --- Pheromone-Guided Component ---
    pheromone_swaps = []
    num_ph_swaps = int(phi3 * random.random())
    for _ in range(num_ph_swaps):
        if num_items <= 1: continue
        # Choose a random position in the solution to try to improve.
        pos_to_improve = random.randrange(num_items - 1)
        current_item_at_pos = part[pos_to_improve]
        
        # Use the pheromone matrix to find the most desirable NEXT item.
        pheromone_probs = pheromone_matrix[current_item_at_pos]
        # Avoid choosing an item already placed before this position.
        for i in range(pos_to_improve + 1):
            if part[i] < len(pheromone_probs):
                pheromone_probs[part[i]] = 0

        if np.sum(pheromone_probs) > 0:
            best_next_item = np.argmax(pheromone_probs)
            # If the best next item according to pheromones is not what we have,
            # create a swap to fix it.
            if part[pos_to_improve + 1] != best_next_item and best_next_item in part:
                original_pos_of_best_item = part.index(best_next_item)
                pheromone_swaps.append(tuple(sorted((pos_to_improve + 1, original_pos_of_best_item))))

    # Apply all swaps to update the particle's position.
    all_swaps = list(set(pbest_swaps + gbest_swaps + pheromone_swaps))
    for i, j in all_swaps:
        if i < len(part) and j < len(part):
            part[i], part[j] = part[j], part[i]