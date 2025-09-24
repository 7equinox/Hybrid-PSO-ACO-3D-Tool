# HYBRID-PSO-ACO-3D-TOOL/backend/app.py

# Import necessary libraries
from flask import Flask, render_template, request, jsonify
import os
import sys

# Add the project root to the Python path to allow for absolute imports
# This makes the code more modular and easier to maintain
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import custom modules for data handling and problem-solving
from backend.utils.data_loader import load_data, get_all_vehicle_capacities
from backend.utils.problem_solver import solve_loading_problem

# Initialize the Flask application
# 'template_folder' and 'static_folder' point to the frontend directories
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Route for the main page of the web application
@app.route('/')
def index():
    """
    Renders the main HTML page of the tool.
    This serves as the user interface for the simulation.
    """
    # Dynamically fetch vehicle capacities to populate the dropdown on page load.
    capacities = get_all_vehicle_capacities()
    return render_template('index.html', capacities=capacities)

# API endpoint to fetch data related to a specific vehicle capacity
@app.route('/get_vehicle_data', methods=['POST'])
def get_vehicle_data():
    """
    This endpoint is called by the frontend to fetch the list of packages 
    associated with a selected vehicle capacity.
    This allows the left panel of the UI to be populated with the initial dataset.
    """
    try:
        data = request.get_json()
        capacity_cm3 = float(data.get('capacity'))
        
        # Load vehicle and package data using the data_loader utility
        vehicle_info, packages_info = load_data(capacity_cm3)
        
        # If no data is found for the given capacity, return an error
        if not vehicle_info:
            return jsonify({'error': 'Vehicle with specified capacity not found.'}), 404
        
        # Return the loaded data in JSON format to the frontend
        return jsonify({
            'vehicle': vehicle_info,
            'packages': packages_info
        })
    except Exception as e:
        print(f"Error in /get_vehicle_data: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoint to run the simulation
@app.route('/simulate', methods=['POST'])
def simulate():
    """
    This is the core endpoint that triggers the optimization process.
    It receives the selected algorithm and vehicle capacity from the frontend,
    runs the simulation, and returns the calculated performance metrics.
    """
    try:
        data = request.get_json()
        algorithm_name = data.get('algorithm')
        capacity_cm3 = float(data.get('capacity'))
        
        print(f"Starting simulation for {algorithm_name} with capacity {capacity_cm3} cm³...")
        
        # Call the main solver function which handles the entire optimization process
        results = solve_loading_problem(algorithm_name, capacity_cm3)

        print("Simulation finished. Sending results to frontend.")
        
        # Return the comprehensive results to the frontend
        return jsonify(results)
    except Exception as e:
        print(f"Error during simulation: {e}")
        # In case of an error, send a structured error message to the frontend
        return jsonify({'error': f'An internal error occurred: {str(e)}'}), 500

# Main entry point for running the Flask application
if __name__ == '__main__':
    # 'debug=True' allows for automatic reloading on code changes
    # and provides detailed error pages.
    # 'host=0.0.0.0' makes the server accessible from any device on the network.
    app.run(host='0.0.0.0', port=5000, debug=True)