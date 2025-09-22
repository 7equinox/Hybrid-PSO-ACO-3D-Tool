# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/aco.py
import random
import numpy as np

# ACO doesn't use DEAP, so it only needs the callback logic.
def run_aco(items, bin_dimensions, evaluate_solution, num_ants=10, max_generations=50, alpha=1.0, beta=2.0, evaporation_rate=0.5, progress_callback=None):
    num_items = len(items)
    
    pheromones = np.ones((num_items, num_items)) / num_items

    best_solution = None
    best_fitness = (-1, float('inf'), float('inf'))

    for gen in range(max_generations):
        all_ant_solutions = []
        for _ in range(num_ants):
            solution = construct_solution(pheromones, num_items, alpha, beta)
            fitness = evaluate_solution(solution)
            all_ant_solutions.append((solution, fitness))

            current_best_val = best_fitness[0]
            new_val = fitness[0]
            if new_val > current_best_val:
                best_solution = solution
                best_fitness = fitness

        pheromones *= (1 - evaporation_rate)
        
        for solution, fitness in all_ant_solutions:
            pheromone_deposit = fitness[0] 
            for i in range(num_items - 1):
                pheromones[solution[i]][solution[i+1]] += pheromone_deposit
        
        # After each generation, call the callback function if it exists.
        if progress_callback:
            progress_callback({
                'generation': gen + 1,
                'max_generations': max_generations,
                'best_fitness': best_fitness
            })

    return best_solution, best_fitness

def construct_solution(pheromones, num_items, alpha, beta):
    solution = []
    remaining_items = list(range(num_items))
    
    if not remaining_items:
        return []
    
    current_item = random.choice(remaining_items)
    solution.append(current_item)
    remaining_items.remove(current_item)

    while remaining_items:
        probabilities = []
        for next_item in remaining_items:
            pheromone_level = pheromones[current_item][next_item] ** alpha
            heuristic_value = (1.0) ** beta 
            probabilities.append(pheromone_level * heuristic_value)

        probabilities_sum = sum(probabilities)
        if probabilities_sum == 0:
            next_item = random.choice(remaining_items)
        else:
            probabilities = [p / probabilities_sum for p in probabilities]
            next_item = random.choices(remaining_items, weights=probabilities, k=1)[0]
        
        solution.append(next_item)
        remaining_items.remove(next_item)
        current_item = next_item

    return solution