"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Proposed Hybrid PSO-ACO Algorithm

Purpose of this file:
This module contains the implementation of the novel Hybrid Particle Swarm and
Ant Colony Optimization (PSO-ACO) algorithm. This code is a direct translation
of the proposed Hybrid System Architecture flowchart (Figure 7) from Chapter 3.
The central innovation of this algorithm is the deep integration of ACO's
pheromone-based memory mechanism directly into the PSO search loop.

The hypothesis is that this hybridization will achieve superior performance by
synergizing the strengths of both parent algorithms:
-   **PSO's Strength (Global Exploration):** Its ability to rapidly explore a
    vast solution space and identify promising regions.
-   **ACO's Strength (Local Refinement & Memory):** Its ability to reinforce
    and exploit good solution components (i.e., specific pairs or short
    sequences of items that lead to good results).
By having the PSO swarm's search results continuously update the ACO pheromone
matrix, and then using that matrix to intelligently guide the PSO particles'
movement, we create a powerful feedback loop. This loop is specifically
designed to discover packing sequences that are not only spatially dense but also
highly feasible and efficient to unload, thereby directly addressing the core
research gap identified in the Statement of the Problem.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
import random
import numpy as np
from deap import base, tools
from .base_algorithm import creator # Imports the shared Fitness and Particle structures.
from backend.simulation.custom_exceptions import CancelledException # For graceful cancellation.


def fnRunHybridPsoAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                                intNumParticles=10, intMaxGenerations=10, fltEvaporationRate=0.2):
    """
    Executes the proposed Pheromone-Augmented Particle Swarm Optimization (PACO) algorithm,
    strictly following the procedural flowchart (Figure 7) from the methodology.
    
    Args:
        arrItems (list): The list of item objects to be packed.
        arrPackagesInfo (list): Metadata for the packages.
        funcEvaluateSolution (function): The shared fitness evaluation function.
        dictCancellationFlag (dict): Shared flag for user-initiated cancellation.
        dictProgressTracker (dict): Shared dictionary for reporting real-time progress.
        intNumParticles (int): The size of the particle swarm.
        intMaxGenerations (int): The number of optimization iterations.
        fltEvaporationRate (float): The rate at which pheromone trails decay.

    Returns:
        tuple: The best solution found and its multi-objective fitness values.
    """
    int_numItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations # Inform the UI about the total number of generations.
    
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1

    # --- INITIALIZATION (Combines elements from both PSO and ACO, as per Figure 7) ---
    # The hybrid algorithm begins by setting up the necessary components from both of its parent methodologies.
    
    # 1. Initialize the PSO components: A swarm of particles.
    obj_toolbox = base.Toolbox()
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)
    obj_toolbox.register("evaluate", funcEvaluateSolution)
    list_swarm = obj_toolbox.population(n=intNumParticles)
    
    # 2. Initialize the ACO component: A pheromone matrix for collective memory.
    mtr_pheromoneMatrix = np.ones((int_numItems, int_numItems))
    obj_gbest = None

    # 3. Register the unique HYBRID update function with the DEAP toolbox. This function
    #    contains the core logic of our proposed hybridization.
    obj_toolbox.register("update", _fnUpdateParticleHybrid, pheromone_matrix=mtr_pheromoneMatrix,
                         service_times=arr_serviceTimes, phi1=1.5, phi2=1.5, phi3=2.0, phi4=1.5)

    # --- HYBRID OPTIMIZATION LOOP (The core cycle of the Hybrid Flowchart, Figure 7) ---
    try:
        for gen in range(intMaxGenerations):
            dictProgressTracker['current'] = gen + 1 # Update UI progress.
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"Hybrid PSO-ACO Generation: {gen + 1}/{intMaxGenerations}")

            # --- Step 1: Evaluate Fitness and Update pBest/gBest (A standard PSO step) ---
            # This step drives the global exploration aspect of the algorithm. Each particle
            # evaluates its current solution and updates its personal and the global best memories.
            # This is identical to the process in the standalone PSO.
            for obj_particle in list_swarm:
                if not obj_particle.fitness.valid:
                    obj_particle.fitness.values = obj_toolbox.evaluate(obj_particle)
                if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                    obj_particle.pbest = creator.Particle(obj_particle)
                    obj_particle.pbest.fitness.values = obj_particle.fitness.values
                if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                    obj_gbest = creator.Particle(obj_particle)
                    obj_gbest.fitness.values = obj_particle.fitness.values
            
            # --- Step 2: WEIGHTED PHEROMONE UPDATE (The core ACO integration step) ---
            # This is the crucial feedback mechanism from the hybrid flowchart. Information
            # discovered by the PSO search is now used to update the ACO's collective memory.

            # Step 2a. Pheromone Evaporation (from ACO): Reduces the influence of old trails to encourage exploration.
            mtr_pheromoneMatrix *= (1 - fltEvaporationRate)
            
            # Step 2b. Elite-Based Pheromone Deposition (from ACO, modified):
            # This is the 'Weighted Pheromone Update' block in the flowchart. Instead of all
            # particles/ants depositing pheromones, we use an 'elitist' or 'rank-based'
            # strategy. Only the best-performing particles (the "elites") in the current
            # generation are allowed to deposit pheromones. This is a critical refinement that
            # ensures only high-quality solution components (good item sub-sequences) are
            # reinforced, preventing mediocre solutions from polluting the collective memory.
            list_sortedSwarm = sorted(list_swarm, key=lambda p: p.fitness.values[0]) # Sort by smallest VU
            int_numElites = max(1, int(0.2 * len(list_swarm))) # The top 20% of particles are elites.

            for obj_eliteParticle in list_sortedSwarm[:int_numElites]:
                # The amount of pheromone deposited is now inversely proportional to the elite solution's
                # primary fitness value (volume utilization), since a lower value is better.
                # FIX: Explicitly cast the fitness value to float before the division operation.
                flt_depositAmount = 1.0 / (1.0 + float(obj_eliteParticle.fitness.values[0]))
                if flt_depositAmount > 0 and len(obj_eliteParticle) > 1:
                    for i in range(int_numItems - 1):
                        mtr_pheromoneMatrix[obj_eliteParticle[i]][obj_eliteParticle[i+1]] += flt_depositAmount

            # --- Step 3: Update Particle Velocity with Augmented, Pheromone-Guided Equation ---
            # Each particle's velocity and position are now updated using the special hybrid function,
            # which incorporates the newly updated pheromone information as a guiding force.
            # This step, labeled "Compute velocity with pheromone influence" in the flowchart,
            # closes the powerful feedback loop between PSO and ACO.
            for obj_particle in list_swarm:
                 obj_toolbox.update(obj_particle, obj_gbest)

    except CancelledException:
        print("Hybrid PSO-ACO algorithm was cancelled.")
        solution = obj_gbest if obj_gbest else []
        fitness = obj_gbest.fitness.values if obj_gbest else (float('inf'), float('inf'))
        return solution, fitness

    # After all generations, return the best solution found.
    return obj_gbest, obj_gbest.fitness.values


def _fnUpdateParticleHybrid(objParticle, objGbest, pheromone_matrix, service_times, phi1, phi2, phi3, phi4):
    """
    This is the augmented hybrid update function, the core of the proposed algorithm.
    It calculates a particle's "velocity" (a series of swaps) by combining the three
    standard PSO influences (cognitive, social, heuristic) with a new and powerful
    **pheromone-guided component** derived from the ACO memory matrix.

    Args:
        objParticle (Particle): The particle to update.
        objGbest (Particle): The global best particle.
        pheromone_matrix (np.array): The shared ACO pheromone matrix.
        service_times (np.array): Heuristic information.
        phi1, phi2, phi3, phi4 (float): Weighting factors for the components.
    """
    int_numItems = len(objParticle)
    if int_numItems <= 1: return

    # --- Standard PSO Components (Cognitive & Social) ---
    # These function exactly as they do in the standalone PSO, pulling the particle
    # towards its personal best memory and the swarm's collective global best. These
    # components are responsible for the broad, explorative search behavior.
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
    # This is the key novelty of the hybrid algorithm. This component introduces new swaps
    # that are not random but are intelligently biased by the collective memory stored
    # in the pheromone matrix. It effectively asks: "Based on all past successful
    # solutions, what is the best item to place AFTER the one at my current position?"
    # It then suggests a swap to make that happen. This powerfully refines the global
    # search of PSO with proven, locally-optimal structures learned by the ACO mechanism.
    arr_pheromoneSwaps = []
    int_numPhSwaps = int(phi3 * random.random())
    for _ in range(int_numPhSwaps):
        if int_numItems <= 1: continue
        # Choose a random position in the current solution to try and improve.
        int_posToImprove = random.randrange(int_numItems - 1)
        int_currentItemAtPos = objParticle[int_posToImprove]
        
        # Look up the pheromone trail to find the most "desirable" item to place next.
        arr_pheromoneProbs = pheromone_matrix[int_currentItemAtPos].copy()
        # Ensure we don't try to place an item that's already in the sequence up to this point.
        for i in range(int_posToImprove + 1):
             if objParticle[i] < len(arr_pheromoneProbs): arr_pheromoneProbs[objParticle[i]] = 0

        if np.sum(arr_pheromoneProbs) > 0:
            int_bestNextItem = np.argmax(arr_pheromoneProbs)
            # If the most desirable next item isn't already there, create a swap to move it into place.
            if objParticle[int_posToImprove + 1] != int_bestNextItem and int_bestNextItem in objParticle:
                int_originalPosOfBestItem = objParticle.index(int_bestNextItem)
                arr_pheromoneSwaps.append(tuple(sorted((int_posToImprove + 1, int_originalPosOfBestItem))))

    # --- Standard Heuristic Component ---
    # As with the standalone versions, this component adds a simple bias based on service time.
    arr_heuristicSwaps = []
    int_numHeuristicSwaps = int(phi4 * random.random())
    for _ in range(int_numHeuristicSwaps):
        if int_numItems < 2: continue
        idx1, idx2 = random.sample(range(int_numItems), 2)
        if service_times[objParticle[idx1]] > service_times[objParticle[idx2]]:
             arr_heuristicSwaps.append(tuple(sorted((idx1, idx2))))
            
    # Combine and apply all swaps from all four driving forces to generate the particle's
    # final movement for this generation.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_pheromoneSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]