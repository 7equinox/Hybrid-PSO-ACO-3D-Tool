"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
Contains the implementation of the proposed Hybrid PSO-ACO algorithm. This
code is a direct translation of the Hybrid System Architecture (Figure 6)
from Chapter 3. The core novelty lies in integrating ACO's pheromone-based
memory mechanism directly into the PSO search loop. This hybridization aims
to balance PSO's strong global exploration capabilities with ACO's strength in
reinforcing good solution components (local search), specifically to discover
packing sequences that are not only dense but also highly feasible and
efficient to unload, addressing the central gap identified in the Statement of the Problem.

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
from .base_algorithm import creator # Imports the shared Fitness and Particle structures.
from backend.simulation.custom_exceptions import CancelledException

# NEW: The main function now accepts a progress tracker dictionary.
def fn_runHybridPsoAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                                intNumParticles=10, intMaxGenerations=10, fltEvaporationRate=0.2):
    """
    Executes the proposed Pheromone-Augmented Particle Swarm Optimization (PACO) algorithm,
    following the procedural flowchart (Figure 6) from the methodology.
    """
    int_numItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations # NEW: Set the total number of generations for the UI.
    
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1

    # --- INITIALIZATION (Combines PSO and ACO elements as per Figure 6) ---
    # The hybrid approach starts by initializing components from both parent algorithms.
    # A swarm of particles is created for PSO's global search.
    obj_toolbox = base.Toolbox()
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)
    obj_toolbox.register("evaluate", funcEvaluateSolution)

    list_swarm = obj_toolbox.population(n=intNumParticles)
    
    # Simultaneously, a pheromone matrix is created for ACO's memory mechanism.
    mtr_pheromoneMatrix = np.ones((int_numItems, int_numItems))
    obj_gbest = None

    # The DEAP toolbox is registered with the unique HYBRID update function.
    obj_toolbox.register("update", _updateParticleHybrid, pheromone_matrix=mtr_pheromoneMatrix,
                         service_times=arr_serviceTimes, phi1=1.5, phi2=1.5, phi3=2.0, phi4=1.5)

    # --- HYBRID OPTIMIZATION LOOP (The core cycle of Figure 6) ---
    try:
        for gen in range(intMaxGenerations):
            dictProgressTracker['current'] = gen + 1 # NEW: Update the current generation number.
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"Hybrid PSO-ACO Generation: {gen + 1}/{intMaxGenerations}")

            # --- Step 1: Evaluate Fitness and Update pBest/gBest (Standard PSO Step) ---
            # Each particle's fitness is evaluated, and both personal and global bests are updated.
            # This step drives the global exploration aspect of the algorithm.
            for obj_particle in list_swarm:
                if not obj_particle.fitness.valid:
                    obj_particle.fitness.values = obj_toolbox.evaluate(obj_particle)
                if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                    obj_particle.pbest = creator.Particle(obj_particle)
                    obj_particle.pbest.fitness.values = obj_particle.fitness.values
                if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                    obj_gbest = creator.Particle(obj_particle)
                    obj_gbest.fitness.values = obj_particle.fitness.values
            
            # --- Step 2: WEIGHTED PHEROMONE UPDATE (Core ACO Integration Step) ---
            # This is the crucial feedback mechanism from the hybrid flowchart where information
            # from PSO's search is used to update ACO's memory.

            # 2a. Pheromone Evaporation: Reduces the influence of old trails.
            mtr_pheromoneMatrix *= (1 - fltEvaporationRate)
            
            # 2b. Elite-Based Pheromone Deposition: Only the best-performing particles ("elites")
            # in the current generation are allowed to deposit pheromones. This 'elitist' or 'rank-based'
            # strategy ensures that only high-quality solution components (item subsequences)
            # are reinforced, preventing mediocre solutions from polluting the collective memory.
            list_sortedSwarm = sorted(list_swarm, key=lambda p: p.fitness.values[0], reverse=True)
            int_numElites = max(1, int(0.2 * len(list_swarm))) # Top 20% are considered elites.

            for obj_eliteParticle in list_sortedSwarm[:int_numElites]:
                # The deposit amount is proportional to the solution's quality.
                flt_depositAmount = obj_eliteParticle.fitness.values[0]
                if flt_depositAmount > 0 and len(obj_eliteParticle) > 1:
                    for i in range(int_numItems - 1):
                        mtr_pheromoneMatrix[obj_eliteParticle[i]][obj_eliteParticle[i+1]] += flt_depositAmount

            # --- Step 3: Update Particle Velocity with Augmented, Pheromone-Guided Equation ---
            # Each particle's velocity is now calculated using the hybrid function, which incorporates
            # the newly updated pheromone information. This closes the feedback loop.
            for obj_particle in list_swarm:
                 obj_toolbox.update(obj_particle, obj_gbest)

    except CancelledException:
        print("Hybrid PSO-ACO algorithm was cancelled.")
        solution = obj_gbest if obj_gbest else []
        fitness = obj_gbest.fitness.values if obj_gbest else (0, float('inf'), float('inf'))
        return solution, fitness

    return obj_gbest, obj_gbest.fitness.values


def _updateParticleHybrid(objParticle, objGbest, pheromone_matrix, service_times, phi1, phi2, phi3, phi4):
    """
    The augmented hybrid update function. It computes a particle's "velocity"
    (a series of swaps) by combining the standard PSO influences (cognitive and social)
    with a new, powerful pheromone-guided component derived from ACO.
    """
    int_numItems = len(objParticle)
    if int_numItems <= 1: return

    # --- Standard PSO Components (Cognitive & Social) ---
    # These components function exactly as in the standalone PSO, pulling the
    # particle towards its personal best and the global best positions.
    arr_pbestSwaps = []
    if hasattr(objParticle, 'pbest') and objParticle.pbest:
        arr_pbestDiff = [i for i in range(int_numItems) if i < len(objParticle.pbest) and objParticle[i] != objParticle.pbest[i]]
        if len(arr_pbestDiff) >= 2:
            int_numSwaps = int(phi1 * random.random() * len(arr_pbestDiff) / 2)
            arr_pbestSwaps.extend(tuple(random.sample(arr_pbestDiff, 2)) for _ in range(int_numSwaps))

    arr_gbestSwaps = []
    if objGbest:
        arr_gbestDiff = [i for i in range(int_numItems) if i < len(objGbest) and objParticle[i] != objGbest[i]]
        if len(arr_gbestDiff) >= 2:
            int_numSwaps = int(phi2 * random.random() * len(arr_gbestDiff) / 2)
            arr_gbestSwaps.extend(tuple(random.sample(arr_gbestDiff, 2)) for _ in range(int_numSwaps))

    # --- PHEROMONE-GUIDED COMPONENT (The Core Hybridization Mechanism) ---
    # This is the key novelty of the hybrid algorithm. This component introduces
    # swaps that are not random but are intelligently guided by the collective
    # memory stored in the pheromone matrix. It biases the particle's movement
    # towards incorporating subsequences that have been part of historically
    # successful (i.e., high-volume, low-relocation) solutions. This helps to
    # refine the global search of PSO with proven, locally-optimal structures from ACO.
    arr_pheromoneSwaps = []
    int_numPhSwaps = int(phi3 * random.random())
    for _ in range(int_numPhSwaps):
        # Choose a random position in the sequence to try and improve.
        if int_numItems <= 1: continue
        int_posToImprove = random.randrange(int_numItems - 1)
        int_currentItemAtPos = objParticle[int_posToImprove]
        
        # Look up the pheromone trail to find the best item to place *after* the current one.
        arr_pheromoneProbs = pheromone_matrix[int_currentItemAtPos].copy()
        # Mask out items that have already been placed to avoid invalid sequences.
        for i in range(int_posToImprove + 1):
             if objParticle[i] < len(arr_pheromoneProbs): arr_pheromoneProbs[objParticle[i]] = 0

        if np.sum(arr_pheromoneProbs) > 0:
            int_bestNextItem = np.argmax(arr_pheromoneProbs)
            # If the best next item isn't already there, create a swap to move it into place.
            if objParticle[int_posToImprove + 1] != int_bestNextItem and int_bestNextItem in objParticle:
                int_originalPosOfBestItem = objParticle.index(int_bestNextItem)
                arr_pheromoneSwaps.append(tuple(sorted((int_posToImprove + 1, int_originalPosOfBestItem))))

    # --- HEURISTIC COMPONENT (Domain Knowledge) ---
    # As with the standalone versions, this component adds a bias based on service time.
    arr_heuristicSwaps = []
    int_numHeuristicSwaps = int(phi4 * random.random())
    for _ in range(int_numHeuristicSwaps):
        if int_numItems < 2: continue
        idx1, idx2 = random.sample(range(int_numItems), 2)
        if service_times[objParticle[idx1]] > service_times[objParticle[idx2]]:
             arr_heuristicSwaps.append(tuple(sorted((idx1, idx2))))
            
    # Combine and apply all swaps from all four components to generate the final particle movement.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_pheromoneSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]