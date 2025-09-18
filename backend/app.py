"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Main Application Server

Purpose of this file:
To provide a web server endpoint that receives simulation requests from the
frontend, orchestrates the execution of optimization algorithms, and
returns the calculated performance metrics.

Author/ s:
ALFARO, ABRAM  S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import time
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from assets.data_loader import DataLoader
from assets.problem_solver import ProblemSolver

# Initialize Flask app
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing to allow communication with the frontend
CORS(app)

# Global variables to hold data to avoid reloading on every request
obj_data_loader = None
dict_routes = None
dict_packages = None

def initialize_data():
    """
    Initializes the data loader and loads dataset into memory.
    This function is called once when the server starts.
    """
    global obj_data_loader, dict_routes, dict_packages
    
    # Path to the dataset within the backend directory
    str_route_data_path = 'almrrc2021/almrrc2021-data-training/model_build_inputs/route_data.json'
    str_package_data_path = 'almrrc2021/almrrc2021-data-training/model_build_inputs/package_data.json'
    
    try:
        obj_data_loader = DataLoader(str_route_data_path, str_package_data_path)
        dict_routes, dict_packages = obj_data_loader.load_data()
        print("--- Dataset loaded successfully ---")
    except FileNotFoundError as e:
        print(f"Error loading dataset: {e}. Please ensure the 'almrrc2021' folder is in the 'backend' directory.")
        obj_data_loader = None


@app.route('/simulate', methods=['POST'])
def simulate():
    """
    Handles the simulation request from the frontend.
    It expects a JSON payload with 'algorithm' and 'vehicle_capacity'.
    """
    if obj_data_loader is None:
        return jsonify({"error": "Dataset not loaded. Check server logs."}), 500

    # Get data from the frontend request
    json_data = request.get_json()
    str_selected_algorithm = json_data.get('algorithm')
    flt_selected_capacity = float(json_data.get('vehicle_capacity'))
    
    print(f"Received simulation request: Algorithm={str_selected_algorithm}, Capacity={flt_selected_capacity}")

    # Prepare the simulation environment
    try:
        # Find the route ID matching the selected vehicle capacity
        str_route_id = obj_data_loader.get_route_by_capacity(dict_routes, flt_selected_capacity)
        if not str_route_id:
            return jsonify({"error": "No route found for the selected vehicle capacity."}), 400
        
        # Get vehicle and package data for the simulation
        dict_vehicle_data, arr_package_data = obj_data_loader.prepare_simulation_data(
            str_route_id, dict_routes, dict_packages
        )

        # Initialize the problem solver with the selected data and algorithm
        obj_solver = ProblemSolver(str_selected_algorithm, dict_vehicle_data, arr_package_data)
        
        # Start timer for execution time metric
        flt_start_time = time.time()
        
        # --- EXECUTE THE OPTIMIZATION ALGORITHM ---
        dict_solution = obj_solver.run()

        flt_end_time = time.time()
        flt_execution_time = flt_end_time - flt_start_time

        # --- PREPARE THE RESPONSE ---
        # Append runtime metrics to the solution dictionary
        dict_solution['metrics']['execution_time'] = round(flt_execution_time, 4)
        # Note: memory_profiler is complex to integrate into a live web request.
        # This value is a placeholder; real memory profiling should be done offline.
        dict_solution['metrics']['memory_usage'] = "N/A"

        print("--- Simulation complete. Sending results to frontend. ---")
        return jsonify(dict_solution)

    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Initialize data once on server startup
    initialize_data()
    # Run the Flask server
    app.run(debug=True, port=5000)