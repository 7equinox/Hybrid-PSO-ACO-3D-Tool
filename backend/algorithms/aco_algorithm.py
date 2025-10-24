"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Standalone Ant Colony Optimization (ACO) Algorithm

Purpose of this file:
This module contains the complete implementation of the standalone Ant Colony
Optimization (ACO) algorithm. This code is a direct and faithful translation of
the ACO System Architecture flowchart (Figure 6) presented in Chapter 3. ACO is
inspired by the foraging behavior of real ants. It uses a collective, memory-based
search strategy where artificial "ants" build solutions piece by piece. Their choices
are influenced by "pheromone trails"—a shared memory that records which paths
have historically led to high-quality solutions.

ACO offers a fundamentally different search strategy (constructive) compared to PSO
(trajectory-based). Including it as a second baseline allows our study to perform a
more robust comparison, assessing how different metaheuristic philosophies perform on
the unique challenges of the dynamic 3D loading problem.

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
from backend.simulation.custom_exceptions import CancelledException # For graceful cancellation.


def fnRunAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                       intNumAnts=10, intMaxGenerations=10,
                       fltAlpha=1.0, fltBeta=2.0, fltEvaporationRate=0.5):
    """
    Executes the complete standalone Ant Colony Optimization algorithm, from
    initialization to the final result, strictly following the procedural flowchart
    (Figure 6) from the methodology.

    Args:
        arrItems (list): The list of item objects to be packed.
        arrPackagesInfo (list): Metadata for the packages, used for heuristic guidance.
        funcEvaluateSolution (function): The shared fitness evaluation function from the orchestrator.
        dictCancellationFlag (dict): The shared flag for checking user-initiated cancellation.
        dictProgressTracker (dict): A shared dictionary to report real-time progress to the UI.
        intNumAnts (int): The number of ants in the colony for each generation.
        intMaxGenerations (int): The number of iterations for the optimization loop.
        fltAlpha (float): The weighting factor for the influence of the pheromone trail.
        fltBeta (float): The weighting factor for the influence of the heuristic information.
        fltEvaporationRate (float): The rate at which pheromones decay over time.

    Returns:
        tuple: The best solution found (a list of indices) and its multi-objective fitness values.
    """
    int_numItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations # Inform the UI about the total number of generations.

    # --- Heuristic Information ---
    # In ACO, this provides a measure of the local "desirability" of choosing a particular
    # next step. Similar to PSO, we use service time as our heuristic. An ant will be
    # more attracted to picking an item with a shorter service time as its next step in the sequence.
    arr_serviceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arr_serviceTimes[arr_serviceTimes == 0] = 1e-6 # Avoid division by zero errors.
    arr_heuristicInfo = 1.0 / arr_serviceTimes

    # --- INITIALIZATION (Corresponds to "Initialize ant population" and Pheromone Matrix setup) ---
    # The pheromone matrix is the heart of ACO. It acts as the collective, long-term memory
    # of the entire ant colony. The value at `mtr_pheromones[i][j]` represents the learned
    # desirability of placing item `j` immediately after item `i` in the packing sequence.
    # It is initialized uniformly (all 1s) to ensure no initial bias in path selection.
    mtr_pheromones = np.ones((int_numItems, int_numItems))

    # Variables to track the best solution found across the entire history of the run.
    arr_bestSolutionEver = []
    tpl_bestFitnessEver = (float('inf'), float('inf'))

    # --- ITERATIVE OPTIMIZATION LOOP (The main cycle of the ACO Flowchart) ---
    try:
        # The loop runs for a fixed number of generations, our stopping condition.
        for gen in range(intMaxGenerations):
            dictProgressTracker['current'] = gen + 1 # Update the UI with the current generation.
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"ACO Generation: {gen + 1}/{intMaxGenerations}")

            arr_allAntSolutions = []
            # --- ANTS CONSTRUCT SOLUTIONS (Corresponds to "Ants traverse random paths") ---
            # In each generation, a new population of "ants" independently constructs solutions.
            # Unlike PSO where solutions are modified, here they are built from scratch, step-by-step.
            for _ in range(intNumAnts):
                # An ant constructs a full solution (a path/permutation).
                arr_solution = _fnConstructSolution(mtr_pheromones, arr_heuristicInfo, int_numItems, fltAlpha, fltBeta, dictCancellationFlag)
                if not arr_solution: continue # Skip if solution construction was cancelled.

                # The constructed solution's quality is then evaluated using the universal fitness function.
                tpl_fitness = funcEvaluateSolution(arr_solution)
                arr_allAntSolutions.append((arr_solution, tpl_fitness))

                # Update the overall best-so-far solution found across the entire run.
                # We now use Pareto dominance logic for a multi-objective problem where lower is better for both.
                if (tpl_fitness[0] < tpl_bestFitnessEver[0] and tpl_fitness[1] < tpl_bestFitnessEver[1]) or \
                   (tpl_fitness[0] <= tpl_bestFitnessEver[0] and tpl_fitness[1] < tpl_bestFitnessEver[1]) or \
                   (tpl_fitness[0] < tpl_bestFitnessEver[0] and tpl_fitness[1] <= tpl_bestFitnessEver[1]):
                    arr_bestSolutionEver = arr_solution
                    tpl_bestFitnessEver = tpl_fitness


            # --- UPDATE PHEROMONE TRAIL (The "learning" step of ACO) ---
            # This is where the collective memory of the swarm is updated based on the
            # experiences of the ants in the current generation. It consists of two stages:

            # Stage A: Pheromone Evaporation (Corresponds to "Evaporate pheromones")
            # All pheromone trails are slightly reduced. This is a crucial step that prevents
            # the colony from getting stuck on a single, suboptimal path too early. It allows the
            # system to "forget" older, potentially less promising paths, encouraging exploration.
            mtr_pheromones *= (1 - fltEvaporationRate)

            # Stage B: Pheromone Deposition (Corresponds to "Deposit pheromones")
            # The paths that were part of the high-quality solutions found in this generation
            # are reinforced. Ants "deposit" more pheromones on these successful trails, making them
            # more attractive and more likely to be chosen by ants in future generations.
            for arr_solution, tpl_fitness in arr_allAntSolutions:
                # The amount of pheromone deposited is inversely proportional to the solution's
                # primary fitness value (volume utilization), since lower is now better.
                # FIX: Explicitly cast tpl_fitness[0] to float to prevent the TypeError.
                flt_pheromoneDeposit = 1.0 / (1.0 + float(tpl_fitness[0]))
                if flt_pheromoneDeposit > 0:
                    # For each step in the successful path, reinforce the connection.
                    for i in range(int_numItems - 1):
                        mtr_pheromones[arr_solution[i]][arr_solution[i+1]] += flt_pheromoneDeposit
            # The loop then repeats for the next generation.

    except CancelledException:
        print("ACO algorithm was cancelled.")
        return arr_bestSolutionEver, tpl_bestFitnessEver

    # After all generations are complete, return the best solution found.
    return arr_bestSolutionEver, tpl_bestFitnessEver


def _fnConstructSolution(mtrPheromones, arrHeuristicInfo, intNumItems, fltAlpha, fltBeta, dictCancellationFlag):
    """
    Builds a single ant's solution (a complete item permutation) in a step-by-step,
    constructive manner. At each step, the ant must choose the next item to add to
    its sequence from the set of not-yet-placed items. This decision is not random; it is
    a probabilistic choice heavily influenced by both the pheromone trail (global, learned
    knowledge) and the heuristic information (local, problem-specific knowledge).

    Args:
        mtrPheromones (np.array): The current pheromone matrix.
        arrHeuristicInfo (np.array): The pre-computed heuristic values.
        intNumItems (int): The total number of items to place.
        fltAlpha (float): The pheromone influence factor.
        fltBeta (float): The heuristic influence factor.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        list: A single, complete permutation of item indices.
    """
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    arr_solution = []
    list_availableItems = list(range(intNumItems))

    # Start the ant at a random item to introduce diversity.
    if not list_availableItems: return []
    int_currentItem = random.choice(list_availableItems)
    arr_solution.append(int_currentItem)
    list_availableItems.remove(int_currentItem)

    # Continue adding items one by one until the permutation is complete.
    while list_availableItems:
        arr_probabilities = []
        # Calculate the "attractiveness" of moving from the current item to each available next item.
        for int_nextItem in list_availableItems:
            # The attractiveness is a weighted combination of pheromone level and heuristic value.
            # Higher pheromone means this path has been successful in the past.
            # Higher heuristic means this next item is locally desirable (e.g., short service time).
            flt_pheromoneLevel = mtrPheromones[int_currentItem][int_nextItem] ** fltAlpha
            flt_heuristicValue = arrHeuristicInfo[int_nextItem] ** fltBeta
            arr_probabilities.append(flt_pheromoneLevel * flt_heuristicValue)

        flt_probSum = sum(arr_probabilities)
        if flt_probSum == 0:
            # If all available paths have zero preference (e.g., at the very start), choose randomly.
            int_nextItem = random.choice(list_availableItems)
        else:
            # Otherwise, use the calculated probabilities to make a weighted random choice.
            # This is like a "roulette wheel," where paths with higher attractiveness get a
            # larger slice and are more likely to be chosen, but less attractive paths
            # still have a small chance, allowing for exploration.
            arr_probabilities = [p / flt_probSum for p in arr_probabilities]
            int_nextItem = random.choices(list_availableItems, weights=arr_probabilities, k=1)[0]

        # Add the chosen item to the ant's solution and "move" the ant to this new item.
        arr_solution.append(int_nextItem)
        list_availableItems.remove(int_nextItem)
        int_currentItem = int_nextItem

    return arr_solution