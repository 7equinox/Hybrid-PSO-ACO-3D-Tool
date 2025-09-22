# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/pso.py
import random
import numpy as np
from deap import base, tools
# --- FIX ---
# ONLY import the 'creator' object from our base setup file.
from .base import creator

def run_pso(items, bin_dimensions, evaluate_solution, num_particles=30, max_generations=50, progress_callback=None):
    num_items = len(items)

    toolbox = base.Toolbox()
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    # --- FIX ---
    # Reference the Particle class THROUGH the creator object.
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)

    toolbox.register("evaluate", evaluate_solution)
    toolbox.register("update", update_particle_velocity, phi1=2.0, phi2=2.0)

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

        for part in swarm:
            toolbox.update(part, gbest)

        if progress_callback and gbest:
            progress_callback({
                'generation': gen + 1,
                'max_generations': max_generations,
                'best_fitness': gbest.fitness.values
            })

    return gbest, gbest.fitness.values

def update_particle_velocity(part, gbest, phi1, phi2, w=0.5):
    num_items = len(part)

    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        v_pbest = [tuple(random.sample(pbest_diff, 2)) for _ in range(int(phi1 * random.random() * len(pbest_diff)))]
    else:
        v_pbest = []

    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        v_gbest = [tuple(random.sample(gbest_diff, 2)) for _ in range(int(phi2 * random.random() * len(gbest_diff)))]
    else:
        v_gbest = []

    for swap in v_pbest + v_gbest:
        if len(swap) == 2:
            i, j = swap
            part[i], part[j] = part[j], part[i]