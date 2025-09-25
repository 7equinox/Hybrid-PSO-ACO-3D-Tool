"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
This file contains the implementation of the proposed Hybrid PSO-ACO algorithm.
The code is a direct translation of the Hybrid System Architecture (Figure 6)
from Chapter 3, integrating ACO's pheromone mechanism into the PSO loop to
balance global exploration with reinforced, local search, specifically to
enhance unloading feasibility.

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
from .base_algorithm import creator
from backend.simulation.exceptions import CancelledException

def runHybridPsoAcoAlgorithm(arr_items, arr_packagesInfo, func_evaluateSolution, cancellation_flag,
                           int_numParticles=30, int_maxGenerations=50, flt_evaporationRate=0.2):
    """
    Executes the proposed Pheromone-Augmented Particle Swarm Optimization (PACO) algorithm.
    """
    int_numItems = len(arr_items)
    
    # Heuristic Information (as used in standalone versions)
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arr_packagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1
    
    # --- INITIALIZATION (PSO + ACO Elements) ---
    # As per the hybrid flowchart, this phase initializes both the PSO swarm
    # and the ACO pheromone matrix.
    obj_toolbox = base.Toolbox()
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)
    obj_toolbox.register("evaluate", func_evaluateSolution)

    list_swarm = obj_toolbox.population(n=int_numParticles)
    # The pheromone matrix stores the collective knowledge of good item sequences.
    mtr_pheromoneMatrix = np.ones((int_numItems, int_numItems))
    obj_gbest = None

    # Register the unique HYBRID update function.
    obj_toolbox.register("update", _updateParticleHybrid, pheromone_matrix=mtr_pheromoneMatrix,
                         service_times=arr_serviceTimes, phi1=1.5, phi2=1.5, phi3=2.0, phi4=1.5)

    # --- HYBRID OPTIMIZATION LOOP ---
    try:
        for gen in range(int_maxGenerations):
            # NEW: Check for a cancellation request at the start of each generation.
            if cancellation_flag['is_cancelled']:
                raise CancelledException()

            print(f"Hybrid PSO-ACO Generation: {gen + 1}/{int_maxGenerations}")

            # 1. Evaluate fitness and update pBest/gBest (Standard PSO Step)
            # FASTER CANCELLATION: Add check
            for i, obj_particle in enumerate(list_swarm):
                if cancellation_flag['is_cancelled']: raise CancelledException()

                if not obj_particle.fitness.valid:
                    obj_particle.fitness.values = obj_toolbox.evaluate(obj_particle)

                if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                    obj_particle.pbest = creator.Particle(obj_particle)
                    obj_particle.pbest.fitness.values = obj_particle.fitness.values

                if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                    obj_gbest = creator.Particle(obj_particle)
                    obj_gbest.fitness.values = obj_particle.fitness.values
            
            # --- WEIGHTED PHEROMONE UPDATE (ACO Integration) ---
            # This is the core feedback mechanism shown in the yellow box of the hybrid flowchart.
            
            # 2. Evaporate pheromones
            mtr_pheromoneMatrix *= (1 - flt_evaporationRate)
            
            # 3. Rank particles and deposit pheromones based on elite performance.
            list_sortedSwarm = sorted(list_swarm, key=lambda p: p.fitness.values[0], reverse=True)
            int_numElites = max(1, int(0.2 * len(list_swarm))) # Top 20% are elites.

            # Only the best-performing particles are allowed to reinforce the pheromone trail.
            for obj_eliteParticle in list_sortedSwarm[:int_numElites]:
                flt_depositAmount = obj_eliteParticle.fitness.values[0] # Deposit based on quality.
                if (flt_depositAmount > 0 and len(obj_eliteParticle) > 1):
                    for i in range(int_numItems - 1):
                        mtr_pheromoneMatrix[obj_eliteParticle[i]][obj_eliteParticle[i+1]] += flt_depositAmount

            # 4. Update Particle Velocity with Pheromone Influence
            # FASTER CANCELLATION: Add check
            for i, obj_particle in enumerate(list_swarm):
                 if i % 5 == 0 and cancellation_flag['is_cancelled']: raise CancelledException()
                 obj_toolbox.update(obj_particle, obj_gbest)

    except CancelledException:
        print("Hybrid PSO-ACO algorithm was cancelled.")
        # FIX for NoneType: Ensure a valid iterable is always returned.
        solution = obj_gbest if obj_gbest else []
        fitness = obj_gbest.fitness.values if obj_gbest else (0, float('inf'), float('inf'))
        return solution, fitness

    return obj_gbest, obj_gbest.fitness.values

def _updateParticleHybrid(obj_particle, obj_gbest, pheromone_matrix, service_times,
                          phi1, phi2, phi3, phi4, w=0.5):
    """
    The augmented hybrid update function. It computes a particle's velocity by
    combining the standard PSO components with a new pheromone-guided component.
    """
    int_numItems = len(obj_particle)

    # --- Cognitive & Social Components (from PSO) ---
    # Standard influence from personal and global best positions.
    arr_pbestSwaps = []
    arr_pbestDiff = [i for i in range(int_numItems) if i < len(obj_particle.pbest) and obj_particle[i] != obj_particle.pbest[i]]
    if len(arr_pbestDiff) >= 2:
        int_numSwaps = int(phi1 * random.random() * len(arr_pbestDiff) / 2)
        for _ in range(int_numSwaps):
            arr_pbestSwaps.append(tuple(random.sample(arr_pbestDiff, 2)))
    
    arr_gbestSwaps = []
    arr_gbestDiff = [i for i in range(int_numItems) if i < len(obj_gbest) and obj_particle[i] != obj_gbest[i]]
    if len(arr_gbestDiff) >= 2:
        int_numSwaps = int(phi2 * random.random() * len(arr_gbestDiff) / 2)
        for _ in range(int_numSwaps):
            arr_gbestSwaps.append(tuple(random.sample(arr_gbestDiff, 2)))
    
    # --- PHEROMONE-GUIDED COMPONENT (from ACO) ---
    # This is the key hybridization. It introduces swaps that move items into
    # positions that are strongly favored by the pheromone trails, pulling the
    # solution towards historically successful patterns.
    arr_pheromoneSwaps = []
    int_numPhSwaps = int(phi3 * random.random())
    for _ in range(int_numPhSwaps):
        if int_numItems <= 1: continue
        # Choose a random position to try and improve.
        int_posToImprove = random.randrange(int_numItems - 1)
        int_currentItemAtPos = obj_particle[int_posToImprove]
        
        # Find the best item to place *after* the current item, based on pheromones.
        arr_pheromoneProbs = pheromone_matrix[int_currentItemAtPos].copy()
        for i in range(int_posToImprove + 1):
            if obj_particle[i] < len(arr_pheromoneProbs): arr_pheromoneProbs[obj_particle[i]] = 0 # Mask used items

        if np.sum(arr_pheromoneProbs) > 0:
            int_bestNextItem = np.argmax(arr_pheromoneProbs)
            # If the best next item isn't already there, create a swap to move it there.
            if obj_particle[int_posToImprove + 1] != int_bestNextItem and int_bestNextItem in obj_particle:
                int_originalPosOfBestItem = obj_particle.index(int_bestNextItem)
                arr_pheromoneSwaps.append(tuple(sorted((int_posToImprove + 1, int_originalPosOfBestItem))))

    # --- HEURISTIC COMPONENT (Domain Knowledge) ---
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
            
    # Apply all swaps from all components to generate the final particle movement.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_pheromoneSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        if i < len(obj_particle) and j < len(obj_particle):
            obj_particle[i], obj_particle[j] = obj_particle[j], obj_particle[i]