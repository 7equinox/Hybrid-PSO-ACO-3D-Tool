"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
Implements the standalone Particle Swarm Optimization (PSO) algorithm. This
code directly corresponds to the PSO System Architecture flowchart (Figure 4)
in Chapter 3. Its performance serves as a baseline to evaluate the
proposed hybrid algorithm against.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import random
import numpy as np
from deap import base, tools
from .base_algorithm import creator # Import the base creator definitions

def runPsoAlgorithm(arr_items, arr_packagesInfo, func_evaluateSolution,
                    int_numParticles=30, int_maxGenerations=50):
    """
    Executes the complete standalone PSO algorithm.
    """
    int_numItems = len(arr_items)

    # Heuristic Information: Prioritize items with lower service times.
    # This adds domain-specific knowledge to guide the search.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arr_packagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1

    # --- INITIALIZATION ---
    # As shown in the flowchart, we first initialize a population (swarm)
    # of particles, each with a random permutation of items.
    obj_toolbox = base.Toolbox()
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)
    obj_toolbox.register("evaluate", func_evaluateSolution)
    obj_toolbox.register("update", _updateParticle, phi1=2.0, phi2=2.0, phi3=1.5,
                         service_times=arr_serviceTimes)

    list_swarm = obj_toolbox.population(n=int_numParticles)
    obj_gbest = None # The Global Best solution found so far.

    # --- ITERATIVE OPTIMIZATION LOOP ---
    # This loop represents the core cycle of the PSO algorithm.
    for _ in range(int_maxGenerations):
        # 1. Evaluate Fitness & Update Personal Best (pBest) for each particle.
        for obj_particle in list_swarm:
            # The fitness is evaluated only if it hasn't been calculated before.
            if not obj_particle.fitness.valid:
                obj_particle.fitness.values = obj_toolbox.evaluate(obj_particle)

            # If the particle's current position is better than its personal best, update it.
            if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                obj_particle.pbest = creator.Particle(obj_particle)
                obj_particle.pbest.fitness.values = obj_particle.fitness.values

            # 2. Update Global Best (gBest) for the entire swarm.
            if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                obj_gbest = creator.Particle(obj_particle)
                obj_gbest.fitness.values = obj_particle.fitness.values

        # 3. Compute Velocity and Update Particle Position.
        for obj_particle in list_swarm:
            obj_toolbox.update(obj_particle, obj_gbest)

    return obj_gbest, obj_gbest.fitness.values

def _updateParticle(obj_particle, obj_gbest, phi1, phi2, phi3, service_times, w=0.5):
    """
    Updates a particle's position (item permutation) based on PSO movement rules.
    This function applies velocity to the particle, guiding it through the search space.
    """
    int_numItems = len(obj_particle)

    # --- Cognitive Component (Influence of pBest) ---
    # This part of the velocity pulls the particle towards its own best-known position.
    arr_pbestSwaps = []
    arr_pbestDiff = [i for i in range(int_numItems) if i < len(obj_particle.pbest) and obj_particle[i] != obj_particle.pbest[i]]
    if len(arr_pbestDiff) >= 2:
        int_numSwaps = int(phi1 * random.random() * len(arr_pbestDiff) / 2)
        for _ in range(int_numSwaps):
            arr_pbestSwaps.append(tuple(random.sample(arr_pbestDiff, 2)))

    # --- Social Component (Influence of gBest) ---
    # This part of the velocity pulls the particle towards the swarm's best-known position.
    arr_gbestSwaps = []
    arr_gbestDiff = [i for i in range(int_numItems) if i < len(obj_gbest) and obj_particle[i] != obj_gbest[i]]
    if len(arr_gbestDiff) >= 2:
        int_numSwaps = int(phi2 * random.random() * len(arr_gbestDiff) / 2)
        for _ in range(int_numSwaps):
            arr_gbestSwaps.append(tuple(random.sample(arr_gbestDiff, 2)))

    # --- Heuristic Component (Domain Knowledge) ---
    # An additional component that biases the search towards solutions where items
    # with shorter service times are packed earlier.
    arr_heuristicSwaps = []
    int_numHeuristicSwaps = int(phi3 * random.random())
    for _ in range(int_numHeuristicSwaps):
        if int_numItems < 2: continue
        idx1, idx2 = random.sample(range(int_numItems), 2)
        if idx1 > idx2: idx1, idx2 = idx2, idx1 # Ensure consistent order for swap tuple

        int_item1Index = obj_particle[idx1]
        int_item2Index = obj_particle[idx2]

        if service_times[int_item1Index] > service_times[int_item2Index]:
            arr_heuristicSwaps.append((idx1, idx2))

    # Apply all computed swaps to update the particle's position.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        obj_particle[i], obj_particle[j] = obj_particle[j], obj_particle[i]