"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Hybrid PSO-ACO Algorithm

Purpose of this file:
To implement the hybrid Particle Swarm - Ant Colony Optimization algorithm as
depicted in the Hybrid PSO-ACO System Architecture flowchart. This integrates
the ACO pheromone mechanism into the PSO loop.

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

class HybridPSO_ACO:
    """
    Implements a Pheromone-Augmented Particle Swarm Optimization (PACO) framework.
    """
    def __init__(self, dict_vehicle, arr_packages, int_iterations, int_population_size):
        self.obj_bin = Bin(
            dict_vehicle['name'], dict_vehicle['width'], dict_vehicle['height'], dict_vehicle['depth'], 99999
        )
        self.arr_items = [
            Item(p['name'], p['width'], p['height'], p['depth'], p['weight']) for p in arr_packages
        ]
        self.int_iterations = int_iterations
        self.int_particle_count = int_population_size
        self.int_num_items = len(self.arr_items)
        
        # Map items to indices for the pheromone matrix
        self.dict_item_to_idx = {item.name: i for i, item in enumerate(self.arr_items)}

        # --- Initialize PSO Components ---
        self.flt_w = 0.5; self.flt_c1 = 1.0; self.flt_c2 = 2.0
        
        # --- Initialize ACO Components ---
        self.flt_evaporation_rate = 0.3
        self.flt_pheromone_deposit = 1.0
        # Pheromone matrix initialized uniformly
        self.mtx_pheromones = np.ones((self.int_num_items, self.int_num_items))

    def _fitness_function(self, arr_item_sequence):
        """ Evaluates the fitness based on packed volume. Higher is better. """
        obj_packer = Packer(); obj_packer.add_bin(self.obj_bin)
        for obj_item in arr_item_sequence:
            obj_packer.add_item(obj_item)
        obj_packer.pack()
        return sum(item.get_volume() for item in obj_packer.bins[0].items)

    def _update_pheromones(self, arr_ranked_particles, arr_ranked_scores):
        """
        Performs a weighted pheromone update based on elite particles (best solutions).
        """
        # Evaporate pheromones
        self.mtx_pheromones *= (1 - self.flt_evaporation_rate)
        
        # Elitist update: only the best particles deposit pheromones
        int_num_elites = max(1, self.int_particle_count // 4) # Top 25%
        for i in range(int_num_elites):
            arr_solution = arr_ranked_particles[i]
            flt_fitness_score = arr_ranked_scores[i]
            
            for j in range(len(arr_solution) - 1):
                int_from_idx = self.dict_item_to_idx[arr_solution[j].name]
                int_to_idx = self.dict_item_to_idx[arr_solution[j+1].name]
                # Deposit is scaled by solution quality
                self.mtx_pheromones[int_from_idx, int_to_idx] += self.flt_pheromone_deposit * flt_fitness_score
                
    def _update_particle_position(self, arr_current_pos, arr_pbest_pos, arr_gbest_pos):
        """
        Updates particle position using PSO logic plus a pheromone-guided component.
        This is the core of the hybridization.
        """
        # Cognitive pull towards pBest
        if random.random() < self.flt_c1:
            int_idx1 = random.randrange(self.int_num_items); obj_item_to_find = arr_pbest_pos[int_idx1]
            try:
                int_idx2 = arr_current_pos.index(obj_item_to_find)
                arr_current_pos[int_idx1], arr_current_pos[int_idx2] = arr_current_pos[int_idx2], arr_current_pos[int_idx1]
            except ValueError: pass
            
        # Social pull towards gBest
        if random.random() < self.flt_c2:
            int_idx1 = random.randrange(self.int_num_items); obj_item_to_find = arr_gbest_pos[int_idx1]
            try:
                int_idx2 = arr_current_pos.index(obj_item_to_find)
                arr_current_pos[int_idx1], arr_current_pos[int_idx2] = arr_current_pos[int_idx2], arr_current_pos[int_idx1]
            except ValueError: pass
        
        # --- Pheromone-Guided Component ---
        # Introduce a small mutation guided by the pheromone trails
        int_idx1 = random.randrange(self.int_num_items - 1)
        int_current_item_idx = self.dict_item_to_idx[arr_current_pos[int_idx1].name]
        
        # Find the most desirable next item based on pheromones
        int_best_next_item_idx = np.argmax(self.mtx_pheromones[int_current_item_idx])
        obj_best_next_item = next(item for item in self.arr_items if self.dict_item_to_idx[item.name] == int_best_next_item_idx)
        
        try:
            int_idx_to_swap = arr_current_pos.index(obj_best_next_item)
            # Swap with the item that is currently after idx1
            arr_current_pos[int_idx1 + 1], arr_current_pos[int_idx_to_swap] = arr_current_pos[int_idx_to_swap], arr_current_pos[int_idx1 + 1]
        except ValueError: pass

        return arr_current_pos

    def run(self):
        """ Executes the Hybrid PSO-ACO algorithm. """
        if not self.arr_items:
            return [], [] # Return empty lists if there are no items to pack

        # 1. Initialization
        arr_swarm = [random.sample(self.arr_items, len(self.arr_items)) for _ in range(self.int_particle_count)]
        arr_pbest_positions = list(arr_swarm)
        arr_pbest_scores = [self._fitness_function(p) for p in arr_pbest_positions]
        
        int_gbest_index = arr_pbest_scores.index(max(arr_pbest_scores))
        arr_gbest_position = arr_pbest_positions[int_gbest_index]
        flt_gbest_score = arr_pbest_scores[int_gbest_index]
        
        # 2. Main Loop
        for _ in range(self.int_iterations):
            for i in range(self.int_particle_count):
                # 3. Update particle position (velocity is implicitly handled in this permutation approach)
                arr_swarm[i] = self._update_particle_position(arr_swarm[i], arr_pbest_positions[i], arr_gbest_position)
                
                # 4. Evaluate Fitness & Update pBest
                flt_current_score = self._fitness_function(arr_swarm[i])
                if flt_current_score > arr_pbest_scores[i]:
                    arr_pbest_scores[i] = flt_current_score
                    arr_pbest_positions[i] = arr_swarm[i]

            # 5. Update gBest
            int_current_best_idx = arr_pbest_scores.index(max(arr_pbest_scores))
            if arr_pbest_scores[int_current_best_idx] > flt_gbest_score:
                flt_gbest_score = arr_pbest_scores[int_current_best_idx]
                arr_gbest_position = arr_pbest_positions[int_current_best_idx]

            # 6. Weighted Pheromone Update
            # Rank particles based on their personal best fitness
            arr_ranked_indices = np.argsort(arr_pbest_scores)[::-1]
            arr_ranked_pbest_pos = [arr_pbest_positions[i] for i in arr_ranked_indices]
            arr_ranked_pbest_scores = [arr_pbest_scores[i] for i in arr_ranked_indices]
            self._update_pheromones(arr_ranked_pbest_pos, arr_ranked_pbest_scores)

        # Final packing with the global best solution
        obj_final_packer = Packer(); obj_final_packer.add_bin(self.obj_bin)
        for obj_item in arr_gbest_position:
            obj_final_packer.add_item(obj_item)
        obj_final_packer.pack()
        return obj_final_packer.bins[0].items, obj_final_packer.bins[0].unfitted_items