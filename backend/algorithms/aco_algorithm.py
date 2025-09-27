"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
Implements the standalone Ant Colony Optimization (ACO) algorithm. This code
directly corresponds to the ACO System Architecture flowchart (Figure 5) in
Chapter 3. ACO provides a memory-based, constructive search approach, which
serves as a second critical baseline for comparison against both the standalone
PSO and the proposed hybrid algorithm. This allows the study to assess how
different metaheuristic strategies perform on the dynamic loading problem.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import random
import numpy as np
from backend.simulation.custom_exceptions import CancelledException

def fn_runAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag,
                       intNumAnts=20, intMaxGenerations=50,
                       fltAlpha=1.0, fltBeta=2.0, fltEvaporationRate=0.5):
    """
    Executes the complete standalone Ant Colony Optimization algorithm,
    following the procedural flowchart (Figure 5) from the methodology.

    Args:
        arrItems (list): The list of item objects to be packed.
        arrPackagesInfo (list): Metadata for the packages, used for heuristics.
        funcEvaluateSolution (function): The shared fitness evaluation function.
        dictCancellationFlag (dict): A shared flag to check for user-initiated cancellation.
        intNumAnts (int): The number of ants in the colony for each generation.
        intMaxGenerations (int): The number of iterations for the optimization loop.
        fltAlpha (float): The influence factor for the pheromone trail.
        fltBeta (float): The influence factor for the heuristic information.
        fltEvaporationRate (float): The rate at which pheromones evaporate.

    Returns:
        tuple: The best solution found (a list of indices) and its fitness values.
    """
    int_numItems = len(arrItems)

    # Heuristic Information: Provides a local "desirability" measure for ants
    # when choosing their next step. As with PSO, we use service time as a heuristic
    # to encourage ants to construct paths that prioritize items with shorter service times.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1e-6 # Avoid division by zero.
    arr_heuristicInfo = 1.0 / arr_serviceTimes

    # --- INITIALIZATION (Step 1 of the ACO Flowchart) ---
    # The pheromone matrix represents the collective, long-term memory of the ant colony.
    # mtr_pheromones[i][j] stores the learned desirability of placing item j immediately after item i.
    # It is initialized uniformly to ensure no initial bias in path selection.
    mtr_pheromones = np.ones((int_numItems, int_numItems))

    # Variables to track the best solution found across all generations.
    arr_bestSolutionEver = []
    tpl_bestFitnessEver = (0, float('inf'), float('inf')) # (Volume, Relocations, SeqLength)

    # --- ITERATIVE OPTIMIZATION LOOP (The core cycle of the ACO Flowchart) ---
    try:
        for gen in range(intMaxGenerations):
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"ACO Generation: {gen + 1}/{intMaxGenerations}")

            arr_allAntSolutions = []
            # --- Step 2: Ants Construct Solutions ---
            # In each generation, a new population of "ants" independently constructs solutions.
            # Each ant builds a permutation of items step-by-step.
            for _ in range(intNumAnts):
                # An ant constructs a full solution (a path).
                arr_solution = _constructSolution(mtr_pheromones, arr_heuristicInfo, int_numItems, fltAlpha, fltBeta, dictCancellationFlag)
                if not arr_solution: continue

                # --- Step 3: Evaluate Solution Quality ---
                # The constructed solution is evaluated using the universal fitness function.
                tpl_fitness = funcEvaluateSolution(arr_solution)
                arr_allAntSolutions.append((arr_solution, tpl_fitness))

                # Update the best-so-far solution found across the entire run.
                # A proper multi-objective check is used: prioritize better volume,
                # then fewer relocations for ties.
                is_better = (tpl_fitness[0] > tpl_bestFitnessEver[0]) or \
                            (tpl_fitness[0] == tpl_bestFitnessEver[0] and tpl_fitness[1] < tpl_bestFitnessEver[1])
                if is_better:
                    arr_bestSolutionEver = arr_solution
                    tpl_bestFitnessEver = tpl_fitness

            # --- Step 4: UPDATE PHEROMONE TRAIL ---
            # This is the learning mechanism of ACO.

            # 4a. Pheromone Evaporation: Globally reduces the intensity of all pheromone trails.
            # This prevents premature convergence to suboptimal solutions by allowing the
            # colony to "forget" old, potentially poor paths and explore new ones.
            mtr_pheromones *= (1 - fltEvaporationRate)

            # 4b. Pheromone Deposition: Reinforces the paths (item subsequences) that were
            # part of high-quality solutions found in the current generation. Ants deposit
            # pheromones, making these successful paths more attractive for future ants.
            for arr_solution, tpl_fitness in arr_allAntSolutions:
                # The amount of pheromone deposited is proportional to the solution's quality (Volume Utilization).
                flt_pheromoneDeposit = tpl_fitness[0]
                if flt_pheromoneDeposit > 0:
                    # Reinforce the edges/transitions used in this good solution.
                    for i in range(int_numItems - 1):
                        mtr_pheromones[arr_solution[i]][arr_solution[i+1]] += flt_pheromoneDeposit

    except CancelledException:
        print("ACO algorithm was cancelled.")
        return arr_bestSolutionEver, tpl_bestFitnessEver

    return arr_bestSolutionEver, tpl_bestFitnessEver


def _constructSolution(mtrPheromones, arrHeuristicInfo, intNumItems, fltAlpha, fltBeta, dictCancellationFlag):
    """
    Builds a single ant's solution (a complete item permutation) step-by-step.
    The decision for the next item is a probabilistic choice influenced by both
    the pheromone trail (global, learned knowledge) and the heuristic information
    (local, problem-specific knowledge).
    """
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    arr_solution = []
    list_availableItems = list(range(intNumItems))

    # Start the ant at a random item.
    if not list_availableItems: return []
    int_currentItem = random.choice(list_availableItems)
    arr_solution.append(int_currentItem)
    list_availableItems.remove(int_currentItem)

    # Continue until the permutation is complete.
    while list_availableItems:
        arr_probabilities = []
        # Calculate the probability of moving from the current item to each available next item.
        for int_nextItem in list_availableItems:
            # The choice is a weighted product of pheromone level and heuristic value.
            flt_pheromoneLevel = mtrPheromones[int_currentItem][int_nextItem] ** fltAlpha
            flt_heuristicValue = arrHeuristicInfo[int_nextItem] ** fltBeta
            arr_probabilities.append(flt_pheromoneLevel * flt_heuristicValue)

        flt_probSum = sum(arr_probabilities)
        if flt_probSum == 0:
            # If no path has any preference (e.g., at the start), choose randomly.
            int_nextItem = random.choice(list_availableItems)
        else:
            # Otherwise, choose the next item using roulette wheel selection, where
            # paths with higher probability have a greater chance of being selected.
            arr_probabilities = [p / flt_probSum for p in arr_probabilities]
            int_nextItem = random.choices(list_availableItems, weights=arr_probabilities, k=1)[0]

        # Add the chosen item to the solution and move the ant to it.
        arr_solution.append(int_nextItem)
        list_availableItems.remove(int_nextItem)
        int_currentItem = int_nextItem

    return arr_solution