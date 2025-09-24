# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/aco.py

import random
import numpy as np

# --- Ant Colony Optimization (ACO) ---
# This implementation follows the system architecture for ACO described in Chapter 3.
# It uses NumPy for efficient pheromone matrix operations, as per the methodology.

def run_aco(items, evaluate_solution, num_ants=20, max_generations=50, alpha=1.0, beta=1.0, evaporation_rate=0.5):
    """
    Executes the standalone Ant Colony Optimization algorithm.
    """
    num_items = len(items)
    
    # Step 1: Pheromone Initialization (from ACO System Architecture)
    # Pheromone matrix stores the desirability of placing item 'j' after item 'i'.
    pheromones = np.ones((num_items, num_items))

    best_solution_ever = None
    # Initialize best fitness with worst possible values.
    best_fitness_ever = (0, float('inf'), float('inf'))

    # Main optimization loop.
    for gen in range(max_generations):
        all_ant_solutions = []
        # Step 2: Ant Solution Construction
        for _ in range(num_ants):
            # Each ant builds a potential solution (a packing permutation).
            solution = construct_solution(pheromones, num_items, alpha, beta)
            # Evaluate the quality of the ant's constructed solution.
            fitness = evaluate_solution(solution)
            all_ant_solutions.append((solution, fitness))

            # Update the overall best solution found so far across all ants.
            if fitness[0] > best_fitness_ever[0]:
                best_solution_ever = solution
                best_fitness_ever = fitness

        # Step 3: Pheromone Update
        # a) Pheromone Evaporation: Reduces influence of old trails.
        pheromones *= (1 - evaporation_rate)
        
        # b) Pheromone Deposition: Reinforces paths of good solutions.
        for solution, fitness in all_ant_solutions:
            # The amount of pheromone deposited is proportional to solution quality.
            # Here, we use volume utilization as the primary quality metric.
            pheromone_deposit = fitness[0]
            if pheromone_deposit > 0:
                 # Increase pheromone levels for adjacent pairs in the solution path.
                for i in range(num_items - 1):
                    pheromones[solution[i]][solution[i+1]] += pheromone_deposit

    # The loop terminates and the best solution found is returned.
    return best_solution_ever, best_fitness_ever

def construct_solution(pheromones, num_items, alpha, beta):
    """
    Builds a single solution path based on pheromone levels.
    An ant starts at a random item and iteratively chooses the next item to add
    to the sequence based on a probabilistic decision rule.
    """
    solution = []
    available_items = list(range(num_items))
    
    # Start with a random first item.
    if not available_items: return []
    current_item = random.choice(available_items)
    solution.append(current_item)
    available_items.remove(current_item)

    while available_items:
        probabilities = []
        # Calculate probability of moving to each remaining item.
        for next_item in available_items:
            # Pheromone level (desirability). Alpha controls its influence.
            pheromone_level = pheromones[current_item][next_item] ** alpha
            # Heuristic value (not used here, beta=0). In other problems, this
            # could be based on item size, urgency, etc.
            heuristic_value = 1.0 ** beta 
            probabilities.append(pheromone_level * heuristic_value)

        # Normalize probabilities to make a random choice.
        prob_sum = sum(probabilities)
        if prob_sum == 0:
            # If all paths have zero probability, choose randomly to avoid getting stuck.
            next_item = random.choice(available_items)
        else:
            probabilities = [p / prob_sum for p in probabilities]
            next_item = random.choices(available_items, weights=probabilities, k=1)[0]
        
        solution.append(next_item)
        available_items.remove(next_item)
        current_item = next_item

    return solution