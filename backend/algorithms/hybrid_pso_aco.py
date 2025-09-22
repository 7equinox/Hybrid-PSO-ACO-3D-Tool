# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/hybrid_pso_aco.py
import random
import numpy as np
from deap import base, tools
# --- FIX ---
# ONLY import the 'creator' object from our base setup file.
from .base import creator

def run_hybrid_pso_aco(items, bin_dimensions, evaluate_solution, num_particles=30, max_generations=50, progress_callback=None):
    num_items = len(items)

    pheromone_matrix = np.ones((num_items, num_items))
    evaporation_rate = 0.1

    toolbox = base.Toolbox()
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    # --- FIX ---
    # Reference the Particle class THROUGH the creator object.
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)
    toolbox.register("evaluate", evaluate_solution)
    toolbox.register("update", update_particle_hybrid, pheromone_matrix=pheromone_matrix, phi1=1.5, phi2=1.5, phi3=1.0)

    swarm = toolbox.population(n=num_particles)
    gbest = None

    for gen in range(max_generations):
        for part in swarm:
            if not part.fitness.valid:
                part.fitness.values = toolbox.evaluate(part)
                
            # --- FIX ---
            # Use creator.Particle when creating new instances.
            if not part.pbest or part.pbest.fitness < part.fitness:
                part.pbest = creator.Particle(part)
                part.pbest.fitness.values = part.fitness.values
            if not gbest or gbest.fitness < part.fitness:
                gbest = creator.Particle(part)
                gbest.fitness.values = part.fitness.values

        pheromone_matrix *= (1 - evaporation_rate)

        sorted_swarm = sorted(swarm, key=lambda p: p.fitness.values[0], reverse=True)
        num_elites = max(1, int(0.1 * len(swarm)))

        for i in range(num_elites):
            elite_particle = sorted_swarm[i]
            deposit_amount = (1.0 / (i + 1)) * elite_particle.fitness.values[0]
            for pos_idx, item_idx in enumerate(elite_particle):
                pheromone_matrix[pos_idx][item_idx] += deposit_amount

        for part in swarm:
            toolbox.update(part, gbest)

        if progress_callback and gbest:
            progress_callback({
                'generation': gen + 1,
                'max_generations': max_generations,
                'best_fitness': gbest.fitness.values
            })

    return gbest, gbest.fitness.values

def update_particle_hybrid(part, gbest, pheromone_matrix, phi1, phi2, phi3, w=0.5):
    num_items = len(part)
    v_pbest, v_gbest, v_pheromone = [], [], []

    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        v_pbest = [tuple(random.sample(pbest_diff, 2)) for _ in range(int(phi1 * random.random() * len(pbest_diff)))]

    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        v_gbest = [tuple(random.sample(gbest_diff, 2)) for _ in range(int(phi2 * random.random() * len(gbest_diff)))]

    pheromone_influence_strength = int(phi3 * random.random() * num_items / 2)
    for _ in range(pheromone_influence_strength):
        if num_items <= 0: continue
        pos_to_improve = random.randrange(num_items)
        pheromone_probs = pheromone_matrix[pos_to_improve]
        best_item_for_pos = np.argmax(pheromone_probs)

        if best_item_for_pos != part[pos_to_improve] and best_item_for_pos in part:
            original_pos_of_best_item = part.index(best_item_for_pos)
            v_pheromone.append(tuple(sorted((pos_to_improve, original_pos_of_best_item))))

    all_swaps = list(set(v_pbest + v_gbest + v_pheromone))
    for swap in all_swaps:
        if len(swap) == 2:
            i, j = swap
            part[i], part[j] = part[j], part[i]