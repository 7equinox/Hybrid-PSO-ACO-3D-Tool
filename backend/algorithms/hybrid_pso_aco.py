# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/hybrid_pso_aco.py

import random
import numpy as np
from deap import base, tools
from .base import creator

def run_hybrid_pso_aco(items, packages_info, evaluate_solution, num_particles=30, max_generations=50, evaporation_rate=0.2):
    """
    Executes the proposed hybrid PSO-ACO algorithm.
    """
    num_items = len(items)

    service_times = np.array([p.get('service_time', 1) for p in packages_info])
    service_times[service_times == 0] = 1
    
    toolbox = base.Toolbox()
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)
    toolbox.register("evaluate", evaluate_solution)

    swarm = toolbox.population(n=num_particles)
    pheromone_matrix = np.ones((num_items, num_items))

    toolbox.register("update", update_particle_hybrid, pheromone_matrix=pheromone_matrix, 
                     service_times=service_times, phi1=1.5, phi2=1.5, phi3=2.0, phi4=1.5)
    gbest = None

    for gen in range(max_generations):
        for part in swarm:
            if not part.fitness.valid:
                part.fitness.values = toolbox.evaluate(part)

            if not part.pbest or part.pbest.fitness < part.fitness:
                part.pbest = creator.Particle(part)
                part.pbest.fitness.values = part.fitness.values
            
            # --- BUG FIX ---
            # The same error was here. Corrected to copy from `part`.
            if not gbest or gbest.fitness < part.fitness:
                gbest = creator.Particle(part)
                gbest.fitness.values = part.fitness.values # Corrected line
        
        pheromone_matrix *= (1 - evaporation_rate)
        
        sorted_swarm = sorted(swarm, key=lambda p: p.fitness.values[0], reverse=True)
        num_elites = max(1, int(0.2 * len(swarm)))

        for elite_particle in sorted_swarm[:num_elites]:
            deposit_amount = elite_particle.fitness.values[0]
            if deposit_amount > 0 and len(elite_particle) > 1:
                for i in range(num_items - 1):
                    pheromone_matrix[elite_particle[i]][elite_particle[i+1]] += deposit_amount

        for part in swarm:
            toolbox.update(part, gbest)

    return gbest, gbest.fitness.values

def update_particle_hybrid(part, gbest, pheromone_matrix, service_times, phi1, phi2, phi3, phi4, w=0.5):
    """
    The augmented hybrid update equation, with heuristic guidance.
    """
    num_items = len(part)
    
    # Cognitive Component
    pbest_swaps = []
    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        num_swaps = int(phi1 * random.random() * len(pbest_diff) / 2)
        for _ in range(num_swaps): pbest_swaps.append(tuple(random.sample(pbest_diff, 2)))

    # Social Component
    gbest_swaps = []
    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        num_swaps = int(phi2 * random.random() * len(gbest_diff) / 2)
        for _ in range(num_swaps): gbest_swaps.append(tuple(random.sample(gbest_diff, 2)))
    
    # Pheromone-Guided Component
    pheromone_swaps = []
    num_ph_swaps = int(phi3 * random.random())
    for _ in range(num_ph_swaps):
        if num_items <= 1: continue
        pos_to_improve = random.randrange(num_items - 1)
        current_item_at_pos = part[pos_to_improve]
        
        pheromone_probs = pheromone_matrix[current_item_at_pos].copy()
        for i in range(pos_to_improve + 1):
            if part[i] < len(pheromone_probs): pheromone_probs[part[i]] = 0

        if np.sum(pheromone_probs) > 0:
            best_next_item = np.argmax(pheromone_probs)
            if part[pos_to_improve + 1] != best_next_item and best_next_item in part:
                original_pos_of_best_item = part.index(best_next_item)
                pheromone_swaps.append(tuple(sorted((pos_to_improve + 1, original_pos_of_best_item))))

    # Heuristic component
    heuristic_swaps = []
    num_heuristic_swaps = int(phi4 * random.random())
    for _ in range(num_heuristic_swaps):
        if num_items < 2: continue
        idx1, idx2 = random.sample(range(num_items), 2)
        if idx1 > idx2: idx1, idx2 = idx2, idx1
        
        item1_idx = part[idx1]
        item2_idx = part[idx2]

        if service_times[item1_idx] > service_times[item2_idx]:
            heuristic_swaps.append((idx1, idx2))
            
    # Apply all swaps
    all_swaps = list(set(pbest_swaps + gbest_swaps + pheromone_swaps + heuristic_swaps))
    for i, j in all_swaps:
        if i < len(part) and j < len(part):
            part[i], part[j] = part[j], part[i]