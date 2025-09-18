"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Problem Solver

Purpose of this file:
To act as a controller that initializes the appropriate optimization
algorithm, executes the simulation, and formats the solution for the frontend.

Author/ s:
ALFARO, ABRAM  S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
from algorithms.pso import PSO
from algorithms.aco import ACO
from algorithms.hybrid_pso_aco import HybridPSO_ACO
from assets.metrics_calculator import MetricsCalculator

class ProblemSolver:
    """
    Orchestrates the running of a selected optimization algorithm and calculates results.
    """
    def __init__(self, str_algorithm, dict_vehicle_data, arr_package_data):
        """
        Initializes the solver.
        """
        self.str_algorithm_name = str_algorithm
        self.dict_vehicle = dict_vehicle_data
        self.arr_packages = arr_package_data
        self.obj_algorithm = None

    def _initialize_algorithm(self):
        """
        Initializes the algorithm object based on the name.
        This function aligns with the choice made by the user in the frontend.
        """
        # --- HYPERPARAMETERS for the algorithms ---
        # These can be tuned for better performance
        int_iterations = 50
        int_population_size = 20 # Represents number of particles or ants

        if self.str_algorithm_name == "Particle Swarm Optimization":
            self.obj_algorithm = PSO(
                self.dict_vehicle, 
                self.arr_packages,
                int_iterations, 
                int_population_size
            )
        elif self.str_algorithm_name == "Ant Colony Optimization":
            self.obj_algorithm = ACO(
                self.dict_vehicle,
                self.arr_packages,
                int_iterations,
                int_population_size
            )
        elif self.str_algorithm_name == "PSO-ACO Algorithm":
            self.obj_algorithm = HybridPSO_ACO(
                self.dict_vehicle,
                self.arr_packages,
                int_iterations,
                int_population_size
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.str_algorithm_name}")

    def run(self):
        """
        Initializes and runs the optimization process, then calculates metrics.
        
        Returns:
            A dictionary containing the simulation results.
        """
        print(f"Initializing algorithm: {self.str_algorithm_name}...")
        self._initialize_algorithm()

        print("Running optimization...")
        # The 'run' method in each algorithm returns the packed items
        arr_packed_items, arr_unpacked_items = self.obj_algorithm.run()

        print("Calculating final metrics...")
        # Calculate performance metrics based on the packing result
        obj_metrics_calculator = MetricsCalculator(
            self.dict_vehicle, self.arr_packages, arr_packed_items
        )

        dict_metrics = {
            'volume_utilization': obj_metrics_calculator.calculate_volume_utilization(),
            'relocation_count': obj_metrics_calculator.calculate_relocation_count(),
            'unloading_feasibility': obj_metrics_calculator.get_unloading_feasibility(),
            'unloading_sequence_length': obj_metrics_calculator.get_unloading_sequence_length()
        }

        # Format the loaded items data for display in the frontend table
        arr_formatted_packed_items = [
            {
                "id": item.name,
                "volume": round(item.get_volume()),
                "service_time": "N/A", # Service time is not in the dataset
                "height": item.height,
                "length": item.depth,
                "width": item.width
            }
            for item in arr_packed_items
        ]

        flt_total_product_volume = sum(item.get_volume() for item in arr_packed_items)

        dict_final_solution = {
            'algorithm_name': self.str_algorithm_name,
            'metrics': dict_metrics,
            'vehicle_stats': {
                'capacity': self.dict_vehicle['capacity_cm3'],
                'total_item_volume': round(flt_total_product_volume),
                'num_items_loaded': len(arr_packed_items),
                'total_service_time': 'N/A'
            },
            'loaded_items': arr_formatted_packed_items
        }
        
        return dict_final_solution