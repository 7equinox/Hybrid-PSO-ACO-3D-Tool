# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/pso.py

import random
import numpy as np
from deap import base, tools
from .base import creator

def run_pso(items, packages_info, evaluate_solution, num_particles=30, max_generations=50):
    """
    Executes the standalone Particle Swarm Optimization algorithm.
    """
    num_items = len(items)

    service_times = np.array([p.get('service_time', 1) for p in packages_info])
    service_times[service_times == 0] = 1 

    toolbox = base.Toolbox()
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)
    toolbox.register("evaluate", evaluate_solution)
    toolbox.register("update", update_particle, phi1=2.0, phi2=2.0, phi3=1.5, service_times=service_times)
    
    swarm = toolbox.population(n=num_particles)
    gbest = None

    for gen in range(max_generations):
        for part in swarm:
            if not part.fitness.valid:
                part.fitness.values = toolbox.evaluate(part)

            if not part.pbest or part.pbest.fitness < part.fitness:
                part.pbest = creator.Particle(part)
                part.pbest.fitness.values = part.fitness.values

            # --- BUG FIX ---
            # The error was here. It now correctly copies the fitness from the better `part`.
            if not gbest or gbest.fitness < part.fitness:
                gbest = creator.Particle(part)
                gbest.fitness.values = part.fitness.values # Corrected line
        
        for part in swarm:
            toolbox.update(part, gbest)
            
    return gbest, gbest.fitness.values

def update_particle(part, gbest, phi1, phi2, phi3, service_times, w=0.5):
    """
    Updates a particle's position with an added heuristic component
    that prioritizes items with lower service times.
    """
    num_items = len(part)

    # Cognitive component (pBest)
    pbest_swaps = []
    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        num_swaps = int(phi1 * random.random() * len(pbest_diff) / 2)
        for _ in range(num_swaps):
             pbest_swaps.append(tuple(random.sample(pbest_diff, 2)))
    
    # Social component (gBest)
    gbest_swaps = []
    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        num_swaps = int(phi2 * random.random() * len(gbest_diff) / 2)
        for _ in range(num_swaps):
            gbest_swaps.append(tuple(random.sample(gbest_diff, 2)))
            
    # Heuristic component (Service Time Priority)
    heuristic_swaps = []
    num_heuristic_swaps = int(phi3 * random.random()) 
    for _ in range(num_heuristic_swaps):
        if num_items < 2: continue
        idx1, idx2 = random.sample(range(num_items), 2)
        if idx1 > idx2: idx1, idx2 = idx2, idx1
        
        item1_idx = part[idx1]
        item2_idx = part[idx2]

        if service_times[item1_idx] > service_times[item2_idx]:
            heuristic_swaps.append((idx1, idx2))

    # Apply all swaps
    all_swaps = list(set(pbest_swaps + gbest_swaps + heuristic_swaps))
    for i, j in all_swaps:
        part[i], part[j] = part[j], part[i]