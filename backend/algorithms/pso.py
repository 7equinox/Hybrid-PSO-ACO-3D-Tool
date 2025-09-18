"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Particle Swarm Optimization (PSO) Algorithm

Purpose of this file:
To implement the standalone Particle Swarm Optimization algorithm as
depicted in the PSO System Architecture flowchart.

Author/ s:
ALFARO, ABRAM  S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import random
from py3dbp import Packer, Bin, Item

class PSO:
    """
    Implements the standalone Particle Swarm Optimization algorithm for 3D bin packing.
    """
    def __init__(self, dict_vehicle, arr_packages, int_iterations, int_population_size):
        self.obj_bin = Bin(
            dict_vehicle['name'],
            dict_vehicle['width'],
            dict_vehicle['height'],
            dict_vehicle['depth'],
            99999 # Max weight
        )
        self.arr_items = [
            Item(p['name'], p['width'], p['height'], p['depth'], p['weight']) for p in arr_packages
        ]
        self.int_iterations = int_iterations
        self.int_particle_count = int_population_size

        # PSO parameters
        self.flt_w = 0.5  # Inertia
        self.flt_c1 = 1.5 # Cognitive parameter
        self.flt_c2 = 1.5 # Social parameter
        
    def _fitness_function(self, arr_item_sequence):
        """
        Evaluates the fitness of a solution (a sequence of items).
        Fitness is determined by the packed volume. Higher is better.
        """
        obj_packer = Packer()
        obj_packer.add_bin(self.obj_bin)
        for obj_item in arr_item_sequence:
            obj_packer.add_item(obj_item)
        
        obj_packer.pack()
        
        flt_packed_volume = sum(item.get_volume() for item in obj_packer.bins[0].items)
        return flt_packed_volume
        
    def run(self):
        """
        Executes the PSO algorithm according to the system architecture.
        """
        if not self.arr_items:
                    return [], [] # Return empty lists if there are no items to pack

        # 1. Initialize particle population (each particle is a permutation of items)
        arr_swarm = [random.sample(self.arr_items, len(self.arr_items)) for _ in range(self.int_particle_count)]
        arr_velocities = [[(0, 0) for _ in self.arr_items] for _ in range(self.int_particle_count)] # Simplified velocity
        
        arr_pbest_positions = list(arr_swarm)
        arr_pbest_scores = [self._fitness_function(p) for p in arr_pbest_positions]
        
        int_gbest_index = arr_pbest_scores.index(max(arr_pbest_scores))
        arr_gbest_position = arr_pbest_positions[int_gbest_index]
        flt_gbest_score = arr_pbest_scores[int_gbest_index]

        # 2. Iteration loop
        for _ in range(self.int_iterations):
            for i in range(self.int_particle_count):
                # 3. Update particle position (simplified for permutation-based problems)
                # Swap items based on pBest and gBest influences
                arr_current_pos = arr_swarm[i]
                
                # Cognitive component
                if random.random() < self.flt_c1:
                    # Move towards pBest by swapping one element
                    int_swap_idx1 = random.randrange(len(arr_current_pos))
                    obj_item_to_find = arr_pbest_positions[i][int_swap_idx1]
                    try:
                        int_swap_idx2 = arr_current_pos.index(obj_item_to_find)
                        arr_current_pos[int_swap_idx1], arr_current_pos[int_swap_idx2] = arr_current_pos[int_swap_idx2], arr_current_pos[int_swap_idx1]
                    except ValueError:
                        pass # Item might not be in the current list
                
                # Social component
                if random.random() < self.flt_c2:
                    # Move towards gBest by swapping one element
                    int_swap_idx1 = random.randrange(len(arr_current_pos))
                    obj_item_to_find = arr_gbest_position[int_swap_idx1]
                    try:
                        int_swap_idx2 = arr_current_pos.index(obj_item_to_find)
                        arr_current_pos[int_swap_idx1], arr_current_pos[int_swap_idx2] = arr_current_pos[int_swap_idx2], arr_current_pos[int_swap_idx1]
                    except ValueError:
                        pass
                
                arr_swarm[i] = arr_current_pos
                flt_current_score = self._fitness_function(arr_swarm[i])
                
                # 4. Evaluate and update pBest
                if flt_current_score > arr_pbest_scores[i]:
                    arr_pbest_scores[i] = flt_current_score
                    arr_pbest_positions[i] = arr_swarm[i]
                    
            # 5. Update gBest
            int_current_best_idx = arr_pbest_scores.index(max(arr_pbest_scores))
            if arr_pbest_scores[int_current_best_idx] > flt_gbest_score:
                flt_gbest_score = arr_pbest_scores[int_current_best_idx]
                arr_gbest_position = arr_pbest_positions[int_current_best_idx]
                
        # Use the best found sequence to do the final packing
        obj_final_packer = Packer()
        obj_final_packer.add_bin(self.obj_bin)
        for obj_item in arr_gbest_position:
            obj_final_packer.add_item(obj_item)
            
        obj_final_packer.pack()
        
        return obj_final_packer.bins[0].items, obj_final_packer.bins[0].unfitted_items