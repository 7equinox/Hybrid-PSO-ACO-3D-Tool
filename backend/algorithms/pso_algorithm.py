"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Standalone Particle Swarm Optimization (PSO) Algorithm

Purpose of this file:
This module contains the complete implementation of the standalone Particle
Swarm Optimization (PSO) algorithm. This code is a direct and faithful
translation of the PSO System Architecture flowchart (Figure 5) presented in
Chapter 3 of the methodology. PSO works by simulating a "swarm" of particles,
where each particle represents a potential solution to the packing problem.
These particles "fly" through the solution space, influenced by their own best-found
positions and the best position found by the entire swarm.

The performance of this algorithm on our defined metrics (Volume Utilization,
Relocation Count, etc.) serves as a critical baseline. By comparing the results of
this well-established algorithm to our proposed hybrid model, we can scientifically
evaluate whether our hybrid approach offers any significant advantages.

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
from .base_algorithm import creator # Imports the custom Fitness and Particle structures we defined.
from backend.simulation.custom_exceptions import CancelledException # For graceful cancellation.


def fnRunPsoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                       intNumParticles=10, intMaxGenerations=10):
    """
    Executes the complete standalone Particle Swarm Optimization algorithm, from
    initialization to the final result, strictly following the procedural flowchart
    (Figure 5) from the methodology.

    Args:
        arrItems (list): The list of item objects to be packed.
        arrPackagesInfo (list): Metadata for the packages (e.g., service time).
        funcEvaluateSolution (function): The shared fitness evaluation function from the orchestrator.
        dictCancellationFlag (dict): The shared flag to check for user-initiated cancellation.
        dictProgressTracker (dict): A shared dictionary to report real-time progress to the UI.
        intNumParticles (int): The number of particles in the swarm (i.e., the population size).
        intMaxGenerations (int): The number of iterations the algorithm will run (the stopping condition).

    Returns:
        tuple: The best solution found (a list of item indices) and its multi-objective fitness values.
    """
    int_numItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations # Inform the UI about the total number of generations.

    # --- Heuristic Information ---
    # To improve the search, we incorporate domain-specific knowledge. A good general
    # heuristic in logistics is that items delivered earlier are often smaller or have shorter
    # service times. We use service time to create a "desirability" score, guiding the
    # algorithm towards potentially better solutions faster than a purely random search.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1 # Avoid division-by-zero errors.

    # --- INITIALIZATION (Corresponds to "Initialize ant population" in the flowchart) ---
    # A "swarm" of particles is created. Each "particle" is a complete candidate solution,
    # which, for our problem, is a specific permutation (a packing order) of the items.
    obj_toolbox = base.Toolbox()
    # "permutation" will generate a random ordering of item indices.
    obj_toolbox.register("permutation", random.sample, range(int_numItems), int_numItems)
    # "particle" will create a single individual using our custom Particle structure, filled with a permutation.
    obj_toolbox.register("particle", tools.initIterate, creator.Particle, obj_toolbox.permutation)
    # "population" will create a list of particles, giving us our full swarm.
    obj_toolbox.register("population", tools.initRepeat, list, obj_toolbox.particle)

    # Register the core evolutionary functions with DEAP's toolbox for easy calling.
    obj_toolbox.register("evaluate", funcEvaluateSolution)
    obj_toolbox.register("update", _fnUpdateParticle, phi1=2.0, phi2=2.0, phi3=1.5,
                         service_times=arr_serviceTimes)

    list_swarm = obj_toolbox.population(n=intNumParticles)
    obj_gbest = None # This will track the Global Best solution ever found by the entire swarm.

    # --- ITERATIVE OPTIMIZATION LOOP (The main cycle of the PSO Flowchart) ---
    try:
        # The loop runs for a fixed number of generations, which is our stopping condition.
        for gen in range(intMaxGenerations):
            dictProgressTracker['current'] = gen + 1 # Update the UI with the current generation.
            # Check for the cancellation signal at the beginning of each generation.
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"PSO Generation: {gen + 1}/{intMaxGenerations}")

            for obj_particle in list_swarm:
                # --- EVALUATE FITNESS & UPDATE PERSONAL BEST (pBest) ---
                # Each particle's fitness (its quality) is calculated using the shared evaluation
                # function if it hasn't been evaluated already.
                if not obj_particle.fitness.valid:
                    obj_particle.fitness.values = funcEvaluateSolution(obj_particle)

                # Each particle has a "memory" of the best position it has personally visited.
                # If its current position is better than its memory, it updates its memory.
                # This corresponds to the "Evaluate Personal Best (pBest)" step in the flowchart.
                if not obj_particle.pbest or obj_particle.pbest.fitness < obj_particle.fitness:
                    obj_particle.pbest = creator.Particle(obj_particle)
                    obj_particle.pbest.fitness.values = obj_particle.fitness.values

                # --- UPDATE GLOBAL BEST (gBest) ---
                # The Global Best for the entire swarm is updated if the current particle's
                # fitness is better than any fitness seen so far across ALL particles. This
                # represents the collective knowledge of the swarm. This corresponds to the
                # "Assign pBest to Global Best (gBest)" step in the flowchart.
                if not obj_gbest or obj_gbest.fitness < obj_particle.fitness:
                    obj_gbest = creator.Particle(obj_particle)
                    obj_gbest.fitness.values = obj_particle.fitness.values

            # --- COMPUTE VELOCITY AND UPDATE PARTICLE POSITION ---
            # After every particle in the swarm has been evaluated, they are all updated.
            # Each particle's new position is determined by its velocity, which is influenced
            # by its own experience (pBest) and the swarm's collective experience (gBest).
            # This is the "Compute Velocity" and "Update particle position" step.
            for obj_particle in list_swarm:
                obj_toolbox.update(obj_particle, obj_gbest)
            # The loop then repeats for the next generation.

    except CancelledException:
        # This block ensures a graceful exit if the user cancels the simulation.
        print("PSO algorithm was cancelled.")
        solution = obj_gbest if obj_gbest else []
        fitness = obj_gbest.fitness.values if obj_gbest else (0, float('inf'), float('inf'))
        return solution, fitness

    # After the loop terminates, the best solution found throughout the entire run is returned.
    return obj_gbest, obj_gbest.fitness.values


def _fnUpdateParticle(objParticle, objGbest, phi1, phi2, phi3, service_times):
    """
    Updates a single particle's position (its item permutation). In a standard PSO,
    velocity is a vector added to the position. For our permutation-based problem,
    the "velocity" is better understood as a series of intelligent swaps designed to
    transform the current permutation into a new one that is closer to the best-known solutions.

    Args:
        objParticle (Particle): The particle to update.
        objGbest (Particle): The global best particle of the swarm.
        phi1, phi2, phi3 (float): Weighting factors for the different velocity components.
        service_times (np.array): The heuristic information.
    """
    int_numItems = len(objParticle)

    # The velocity is composed of three parts:

    # --- 1. Cognitive Component (Influence of Personal Best) ---
    # This component generates swaps that nudge the particle's current solution
    # to be more like its own personal best-found solution. It represents the particle's
    # individual "memory" or "experience."
    arr_pbestSwaps = []
    if hasattr(objParticle, 'pbest') and objParticle.pbest:
        # Find the positions where the current solution differs from its personal best.
        arr_pbestDiff = [i for i in range(int_numItems) if i < len(objParticle.pbest) and objParticle[i] != objParticle.pbest[i]]
        if len(arr_pbestDiff) >= 2:
            int_numSwaps = int(phi1 * random.random() * len(arr_pbestDiff) / 2)
            arr_pbestSwaps.extend(tuple(random.sample(arr_pbestDiff, 2)) for _ in range(int_numSwaps))

    # --- 2. Social Component (Influence of Global Best) ---
    # This component generates swaps that pull the particle towards the swarm's
    # global best-found solution. This represents the "social learning" or
    # "collective intelligence" aspect of PSO, where successful discoveries are
    # shared and adopted by the whole group.
    arr_gbestSwaps = []
    if objGbest:
        # Find the positions where the current solution differs from the global best.
        arr_gbestDiff = [i for i in range(int_numItems) if i < len(objGbest) and objParticle[i] != objGbest[i]]
        if len(arr_gbestDiff) >= 2:
            int_numSwaps = int(phi2 * random.random() * len(arr_gbestDiff) / 2)
            arr_gbestSwaps.extend(tuple(random.sample(arr_gbestDiff, 2)) for _ in range(int_numSwaps))

    # --- 3. Heuristic Component (Influence of Domain Knowledge) ---
    # This is an additional component that biases the search using our external,
    # problem-specific knowledge (the service time heuristic). It suggests swaps
    # that move items with shorter service times earlier in the packing sequence.
    arr_heuristicSwaps = []
    int_numHeuristicSwaps = int(phi3 * random.random())
    for _ in range(int_numHeuristicSwaps):
        if int_numItems < 2: continue
        idx1, idx2 = random.sample(range(int_numItems), 2)
        # Create a swap if the item at the earlier position has a longer service time.
        if service_times[objParticle[idx1]] > service_times[objParticle[idx2]]:
            arr_heuristicSwaps.append(tuple(sorted((idx1, idx2))))

    # Combine all suggested swaps and apply them to the particle's current permutation
    # to create its new position for the next generation. Using a `set` automatically
    # removes any duplicate swaps that may have been generated by different components.
    arr_allSwaps = list(set(arr_pbestSwaps + arr_gbestSwaps + arr_heuristicSwaps))
    for i, j in arr_allSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]
