"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Ant Colony Optimization (ACO) Algorithm

Purpose of this file:
To implement the standalone Ant Colony Optimization algorithm as
depicted in the ACO System Architecture flowchart.

Author/ s:
ALFARO, ABRAM  S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import random
import numpy as np
from py3dbp import Packer, Bin, Item

class ACO:
    """
    Implements the standalone Ant Colony Optimization algorithm for 3D bin packing.
    """
    def __init__(self, dict_vehicle, arr_packages, int_iterations, int_population_size):
        self.obj_bin = Bin(
            dict_vehicle['name'],
            dict_vehicle['width'],
            dict_vehicle['height'],
            dict_vehicle['depth'],
            99999
        )
        self.arr_items = [
            Item(p['name'], p['width'], p['height'], p['depth'], p['weight']) for p in arr_packages
        ]
        self.int_iterations = int_iterations
        self.int_ant_count = int_population_size
        self.int_num_items = len(self.arr_items)
        
        # Map items to indices for the pheromone matrix
        self.dict_item_to_idx = {item.name: i for i, item in enumerate(self.arr_items)}
        self.dict_idx_to_item = {i: item for i, item in enumerate(self.arr_items)}
        
        # ACO parameters
        self.flt_alpha = 1.0  # Pheromone influence
        self.flt_beta = 2.0   # Heuristic influence (e.g., item volume)
        self.flt_evaporation_rate = 0.5
        self.flt_pheromone_deposit = 100.0

        # Pheromone matrix: Represents desirability of placing item j after item i
        self.mtx_pheromones = np.ones((self.int_num_items, self.int_num_items))
        
        self.arr_best_solution_so_far = []
        self.flt_best_fitness_so_far = -1

    def _fitness_function(self, arr_item_sequence):
        obj_packer = Packer()
        obj_packer.add_bin(self.obj_bin)
        for obj_item in arr_item_sequence:
            obj_packer.add_item(obj_item)
        
        obj_packer.pack()
        return sum(item.get_volume() for item in obj_packer.bins[0].items)

    def run(self):
        """
        Executes the ACO algorithm according to the system architecture.
        """
        if not self.arr_items:
            return [], [] # Return empty lists if there are no items to pack

        for _ in range(self.int_iterations):
            arr_all_ant_solutions = []
            
            # 1. Distribute ants
            for _ in range(self.int_ant_count):
                arr_current_solution = self._construct_solution_for_ant()
                arr_all_ant_solutions.append(arr_current_solution)

            # 2. Evaporate pheromones
            self.mtx_pheromones *= (1 - self.flt_evaporation_rate)
            
            # 3. Deposit pheromones
            for arr_solution in arr_all_ant_solutions:
                flt_fitness = self._fitness_function(arr_solution)
                if flt_fitness > self.flt_best_fitness_so_far:
                    self.flt_best_fitness_so_far = flt_fitness
                    self.arr_best_solution_so_far = arr_solution
                    
                # Deposit pheromones on the path of this solution
                for i in range(len(arr_solution) - 1):
                    int_from_idx = self.dict_item_to_idx[arr_solution[i].name]
                    int_to_idx = self.dict_item_to_idx[arr_solution[i+1].name]
                    self.mtx_pheromones[int_from_idx, int_to_idx] += self.flt_pheromone_deposit / (self.flt_best_fitness_so_far + 1)

        # Use the best found sequence for final packing
        obj_final_packer = Packer()
        obj_final_packer.add_bin(self.obj_bin)
        for obj_item in self.arr_best_solution_so_far:
            obj_final_packer.add_item(obj_item)
            
        obj_final_packer.pack()
        return obj_final_packer.bins[0].items, obj_final_packer.bins[0].unfitted_items

    def _construct_solution_for_ant(self):
        """ An ant builds a solution (a permutation of items) """
        arr_solution = []
        arr_unvisited_items = list(range(self.int_num_items))
        
        int_current_item_idx = random.choice(arr_unvisited_items)
        arr_unvisited_items.remove(int_current_item_idx)
        arr_solution.append(self.dict_idx_to_item[int_current_item_idx])
        
        while arr_unvisited_items:
            arr_probabilities = []
            for int_next_item_idx in arr_unvisited_items:
                flt_pheromone = self.mtx_pheromones[int_current_item_idx, int_next_item_idx] ** self.flt_alpha
                # Heuristic: prefer larger items first
                flt_heuristic = (self.dict_idx_to_item[int_next_item_idx].get_volume() ** self.flt_beta)
                arr_probabilities.append(flt_pheromone * flt_heuristic)
            
            flt_sum_probs = sum(arr_probabilities)
            if flt_sum_probs == 0: # Avoid division by zero
                arr_probabilities = np.ones(len(arr_unvisited_items)) / len(arr_unvisited_items)
            else:
                arr_probabilities = np.array(arr_probabilities) / flt_sum_probs
            
            int_next_item_idx = np.random.choice(arr_unvisited_items, p=arr_probabilities)
            
            arr_unvisited_items.remove(int_next_item_idx)
            arr_solution.append(self.dict_idx_to_item[int_next_item_idx])
            int_current_item_idx = int_next_item_idx
            
        return arr_solution