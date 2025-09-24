# HYBRID-PSO-ACO-D-TOOL/backend/algorithms/aco.py

import random
import numpy as np

def run_aco(items, packages_info, evaluate_solution, num_ants=20, max_generations=50, alpha=1.0, beta=2.0, evaporation_rate=0.5):
    """
    Executes the standalone Ant Colony Optimization algorithm.
    """
    num_items = len(items)
    
    service_times = np.array([p.get('service_time', 1) for p in packages_info])
    service_times[service_times == 0] = 1e-6 
    heuristic_info = 1.0 / service_times

    pheromones = np.ones((num_items, num_items))

    best_solution_ever = []
    best_fitness_ever = (0, float('inf'), float('inf'))

    for gen in range(max_generations):
        all_ant_solutions = []
        for _ in range(num_ants):
            solution = construct_solution(pheromones, heuristic_info, num_items, alpha, beta)
            if not solution: continue
            
            fitness = evaluate_solution(solution)
            all_ant_solutions.append((solution, fitness))

            # --- LOGIC IMPROVEMENT ---
            # This now performs a proper multi-objective check (dominance check)
            # instead of just comparing the first objective.
            # A new solution is better if it's better or equal on all objectives
            # and strictly better on at least one.
            # (Note: For minimization objectives, a smaller value is better)
            if (fitness[0] >= best_fitness_ever[0] and
                fitness[1] <= best_fitness_ever[1] and
                fitness[2] <= best_fitness_ever[2] and
                (fitness[0] > best_fitness_ever[0] or
                 fitness[1] < best_fitness_ever[1] or
                 fitness[2] < best_fitness_ever[2])):
                best_solution_ever = solution
                best_fitness_ever = fitness

        pheromones *= (1 - evaporation_rate)
        
        for solution, fitness in all_ant_solutions:
            pheromone_deposit = fitness[0]
            if pheromone_deposit > 0:
                for i in range(num_items - 1):
                    pheromones[solution[i]][solution[i+1]] += pheromone_deposit

    return best_solution_ever, best_fitness_ever

def construct_solution(pheromones, heuristic_info, num_items, alpha, beta):
    """
    Builds a single solution path influenced by both pheromones and the 
    service time heuristic.
    """
    solution = []
    available_items = list(range(num_items))
    
    if not available_items: return []
    current_item = random.choice(available_items)
    solution.append(current_item)
    available_items.remove(current_item)

    while available_items:
        probabilities = []
        for next_item in available_items:
            pheromone_level = pheromones[current_item][next_item] ** alpha
            heuristic_value = heuristic_info[next_item] ** beta
            probabilities.append(pheromone_level * heuristic_value)

        prob_sum = sum(probabilities)
        if prob_sum == 0:
            next_item = random.choice(available_items)
        else:
            probabilities = [p / prob_sum for p in probabilities]
            next_item = random.choices(available_items, weights=probabilities, k=1)[0]
        
        solution.append(next_item)
        available_items.remove(next_item)
        current_item = next_item

    return solution