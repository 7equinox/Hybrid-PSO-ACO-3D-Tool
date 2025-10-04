"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
Implements the standalone Particle Swarm Optimization (PSO) algorithm. This
code is a direct translation of the PSO System Architecture flowchart (Figure 4)
from Chapter 3. Its performance on the defined metrics (Volume Utilization,
Relocation Count, etc.) serves as a crucial baseline to evaluate the
effectiveness and novelty of the proposed hybrid PSO-ACO algorithm.

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
from .base_algorithm import creator  # Imports the base Fitness and Particle definitions.
from backend.simulation.custom_exceptions import CancelledException

def fn_runPsoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag,
                       intNumParticles=10, intMaxGenerations=10):
    """
    Executes the complete standalone Particle Swarm Optimization algorithm,
    following the procedural flowchart (Figure 4) from the methodology.

    Args:
        arrItems (list): The list of item objects to be packed.
        arrPackagesInfo (list): Metadata for the packages.
        funcEvaluateSolution (function): The fitness evaluation function.
        dictCancellationFlag (dict): A shared flag to check for user-initiated cancellation.
        intNumParticles (int): The size of the swarm (number of candidate solutions).
        intMaxGenerations (int): The number of iterations for the optimization loop.

    Returns:
        tuple: The best solution found (a list of indices) and its fitness values.
    """
    int_numItems = len(arrItems)

    # Heuristic Information: Incorporates domain-specific knowledge to guide the
    # search more effectively than a purely random process. In this case, we
    # use service time to create a bias, as items with lower service times are
    # often desirable to deliver earlier.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1 # Avoid issues with zero service time.

    # --- INITIALIZATION (Step 1 of the PSO Flowchart) ---
    # A population (or "swarm") of particles is created. Each "particle" represents a
    # unique candidate solution, which in this problem is a random permutation (packing order) of items.
    obj_toolbox = base.Toolbox()
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)

    # Register the core functions of the PSO loop with the DEAP toolbox.
    obj_toolbox.register("evaluate", funcEvaluateSolution)
    obj_toolbox.register("update", _updateParticle, phi1=2.0, phi2=2.0, phi3=1.5,
                         service_times=arr_serviceTimes)

    list_swarm = obj_toolbox.population(n=intNumParticles)
    obj_gbest = None # This will track the Global Best solution found by the entire swarm.

    # --- ITERATIVE OPTIMIZATION LOOP (The core cycle of the PSO Flowchart) ---
    try:
        # The loop continues until a stopping condition is met (max generations reached).
        for gen in range(intMaxGenerations):
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"PSO Generation: {gen + 1}/{intMaxGenerations}")

            for obj_particle in list_swarm:
                # --- Step 2: Evaluate Fitness & Update Personal Best (pBest) ---
                # Each particle's fitness is calculated using the shared evaluation function
                # if it hasn't been evaluated already in this generation.
                if not obj_particle.fitness.valid:
                    obj_particle.fitness.values = funcEvaluateSolution(obj_particle)

                # The particle updates its "memory" (pBest) if its current position
                # yields a better fitness than its previously recorded personal best.
                if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                    obj_particle.pbest = creator.Particle(obj_particle)
                    obj_particle.pbest.fitness.values = obj_particle.fitness.values

                # --- Step 3: Update Global Best (gBest) ---
                # The Global Best for the entire swarm is updated if the current particle's
                # fitness is better than the best fitness found so far across all particles.
                if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                    obj_gbest = creator.Particle(obj_particle)
                    obj_gbest.fitness.values = obj_particle.fitness.values

            # --- Step 4: Compute Velocity and Update Particle Position ---
            # Each particle's velocity and position are updated based on its own
            # experience (pBest) and the collective experience of the swarm (gBest).
            for obj_particle in list_swarm:
                obj_toolbox.update(obj_particle, obj_gbest)

    except CancelledException:
        # Handles graceful exit if the user cancels the simulation.
        print("PSO algorithm was cancelled.")
        solution = obj_gbest if obj_gbest else []
        fitness = obj_gbest.fitness.values if obj_gbest else (0, float('inf'), float('inf'))
        return solution, fitness

    # After the loop terminates, return the best solution found.
    return obj_gbest, obj_gbest.fitness.values


def _updateParticle(objParticle, objGbest, phi1, phi2, phi3, service_times):
    """
    Updates a particle's position (its item permutation) by applying a calculated
    "velocity". For this permutation-based problem, the velocity is not a vector
    but rather a series of swaps designed to move the particle towards more
    promising areas of the solution space.
    """
    int_numItems = len(objParticle)

    # --- Cognitive Component (Influence of pBest) ---
    # This component generates swaps that pull the particle towards its own
    # personal best-known position. It represents the particle's individual "memory" or "experience".
    arr_pbestSwaps = []
    # Find the indices where the current position differs from the personal best.
    arr_pbestDiff = [i for i in range(int_numItems) if i < len(objParticle.pbest) and objParticle[i] != objParticle.pbest[i]]
    if len(arr_pbestDiff) >= 2:
        # The number of swaps is proportional to the difference.
        int_numSwaps = int(phi1 * random.random() * len(arr_pbestDiff) / 2)
        arr_pbestSwaps.extend(tuple(random.sample(arr_pbestDiff, 2)) for _ in range(int_numSwaps))

    # --- Social Component (Influence of gBest) ---
    # This component generates swaps that pull the particle towards the swarm's
    # global best-known position. This represents the "social" or "collective intelligence" aspect of PSO.
    arr_gbestSwaps = []
    # Find the indices where the current position differs from the global best.
    arr_gbestDiff = [i for i in range(int_numItems) if i < len(objGbest) and objParticle[i] != objGbest[i]]
    if len(arr_gbestDiff) >= 2:
        int_numSwaps = int(phi2 * random.random() * len(arr_gbestDiff) / 2)
        arr_gbestSwaps.extend(tuple(random.sample(arr_gbestDiff, 2)) for _ in range(int_numSwaps))

    # --- Heuristic Component (Domain Knowledge) ---
    # An additional velocity component based on domain-specific knowledge. This
    # can accelerate the search by biasing it towards solutions that are likely
    # to be good based on external information (e.g., shorter service times).
    arr_heuristicSwaps = []
    int_numHeuristicSwaps = int(phi3 * random.random())
    for _ in range(int_numHeuristicSwaps):
        if int_numItems < 2: continue
        idx1, idx2 = random.sample(range(int_numItems), 2)
        # Create a swap if the item at the earlier position has a longer service time.
        # This move pushes items with shorter service times earlier in the packing sequence.
        if service_times[objParticle[idx1]] > service_times[objParticle[idx2]]:
            arr_heuristicSwaps.append(tuple(sorted((idx1, idx2))))

    # Combine all swaps and apply them to update the particle's position (its permutation).
    # Using a set() removes any duplicate swaps that may have been generated by different components.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]