"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
Implements the standalone Ant Colony Optimization (ACO) algorithm. This code
directly corresponds to the ACO System Architecture flowchart (Figure 5)
in Chapter 3. It serves as another baseline for comparison against the
proposed hybrid algorithm.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import random
import numpy as np

def runAcoAlgorithm(arr_items, arr_packagesInfo, func_evaluateSolution,
                    int_numAnts=20, int_maxGenerations=50,
                    flt_alpha=1.0, flt_beta=2.0, flt_evaporationRate=0.5):
    """
    Executes the complete standalone ACO algorithm.
    """
    int_numItems = len(arr_items)

    # Heuristic Information: Similar to PSO, we use service time to provide
    # a local guidance heuristic for the ants' decisions.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arr_packagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1e-6 # Avoid division by zero
    arr_heuristicInfo = 1.0 / arr_serviceTimes

    # --- INITIALIZATION ---
    # The pheromone matrix is initialized uniformly, ensuring no initial bias in path selection.
    mtr_pheromones = np.ones((int_numItems, int_numItems))

    arr_bestSolutionEver = []
    tpl_bestFitnessEver = (0, float('inf'), float('inf'))

    # --- ITERATIVE OPTIMIZATION LOOP ---
    # Represents the core cycle of the ACO algorithm.
    for _ in range(int_maxGenerations):
        arr_allAntSolutions = []
        # 1. Distribute Ants & Traverse Paths
        for _ in range(int_numAnts):
            # Each ant constructs a solution (item permutation) probabilistically.
            arr_solution = _constructSolution(mtr_pheromones, arr_heuristicInfo, int_numItems, flt_alpha, flt_beta)
            if not arr_solution: continue

            # Evaluate the fitness of the constructed solution.
            tpl_fitness = func_evaluateSolution(arr_solution)
            arr_allAntSolutions.append((arr_solution, tpl_fitness))

            # Update the best solution found across all generations.
            # A proper multi-objective check is used here.
            is_better = (tpl_fitness[0] >= tpl_bestFitnessEver[0] and
                         tpl_fitness[1] <= tpl_bestFitnessEver[1] and
                         tpl_fitness[2] <= tpl_bestFitnessEver[2] and
                         (tpl_fitness[0] > tpl_bestFitnessEver[0] or
                          tpl_fitness[1] < tpl_bestFitnessEver[1] or
                          tpl_fitness[2] < tpl_bestFitnessEver[2]))
            if is_better:
                arr_bestSolutionEver = arr_solution
                tpl_bestFitnessEver = tpl_fitness

        # --- UPDATE PHEROMONE TRAIL ---
        # 2. Evaporate Pheromones: Reduces the influence of old trails.
        mtr_pheromones *= (1 - flt_evaporationRate)

        # 3. Deposit Pheromones: Reinforces paths that led to good solutions.
        for arr_solution, tpl_fitness in arr_allAntSolutions:
            flt_pheromoneDeposit = tpl_fitness[0] # Deposit is proportional to volume utilization.
            if flt_pheromoneDeposit > 0:
                for i in range(int_numItems - 1):
                    mtr_pheromones[arr_solution[i]][arr_solution[i+1]] += flt_pheromoneDeposit

    return arr_bestSolutionEver, tpl_bestFitnessEver

def _constructSolution(mtr_pheromones, arr_heuristicInfo, int_numItems, flt_alpha, flt_beta):
    """
    Builds a single ant's solution (a path). The decision for the next item
    is a probabilistic choice influenced by both the pheromone trail (global
    knowledge) and the heuristic information (local knowledge).
    """
    arr_solution = []
    list_availableItems = list(range(int_numItems))

    if not list_availableItems: return []
    int_currentItem = random.choice(list_availableItems)
    arr_solution.append(int_currentItem)
    list_availableItems.remove(int_currentItem)

    while list_availableItems:
        arr_probabilities = []
        # Calculate the probability of moving to each of the remaining items.
        for int_nextItem in list_availableItems:
            flt_pheromoneLevel = mtr_pheromones[int_currentItem][int_nextItem] ** flt_alpha
            flt_heuristicValue = arr_heuristicInfo[int_nextItem] ** flt_beta
            arr_probabilities.append(flt_pheromoneLevel * flt_heuristicValue)

        flt_probSum = sum(arr_probabilities)
        if flt_probSum == 0:
            # If no path has any preference, choose randomly.
            int_nextItem = random.choice(list_availableItems)
        else:
            # Otherwise, choose based on the weighted probabilities (roulette wheel selection).
            arr_probabilities = [p / flt_probSum for p in arr_probabilities]
            int_nextItem = random.choices(list_availableItems, weights=arr_probabilities, k=1)[0]

        arr_solution.append(int_nextItem)
        list_availableItems.remove(int_nextItem)
        int_currentItem = int_nextItem

    return arr_solution