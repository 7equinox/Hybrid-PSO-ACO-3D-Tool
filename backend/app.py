"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Main Application

Purpose of this file:
Serves as the main entry point and web server for the application. It handles
HTTP requests from the user interface, orchestrates calls to the data loading
and simulation modules, and returns the results to the frontend.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
from flask import Flask, render_template, request, jsonify
import os
import sys

# Add the project root to the Python path for correct module resolution.
g_str_projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if g_str_projectRoot not in sys.path:
    sys.path.insert(0, g_str_projectRoot)

# Import the refactored modules.
from backend.data_management.data_loader import getAllVehicleCapacities, getDisplayDataForVehicle
from backend.simulation.problem_solver import solveLoadingProblem

# Initialize the Flask application
obj_app = Flask(__name__, template_folder='../templates', static_folder='../static')

@obj_app.route('/')
def index():
    """
    Renders the main user interface.
    This function populates the vehicle selection dropdown by fetching all
    unique vehicle capacities from the dataset, preparing the user for
    the 'Pre-Experimentation Stage' outlined in the methodology.
    """
    arr_capacities = getAllVehicleCapacities()
    return render_template('index.html', capacities=arr_capacities)

@obj_app.route('/get_vehicle_data', methods=['POST'])
def getVehicleData():
    """
    MODIFIED: Handles AJAX requests to fetch package data for ONE sample route.
    This data is ONLY for display on the left-hand panel of the UI. It provides
    a concrete example of a real-world problem instance.
    """
    try:
        obj_data = request.get_json()
        flt_capacityCm3 = float(obj_data.get('capacity'))

        # MODIFICATION: Call the new display-specific function. Pagination is no longer needed.
        dict_vehicleInfo, arr_packagesInfo = getDisplayDataForVehicle(flt_capacityCm3)

        if not dict_vehicleInfo:
            return jsonify({'error': 'Could not find a valid sample route for the specified capacity.'}), 404

        # The structure of the returned JSON is simplified as pagination is removed.
        return jsonify({
            'vehicle': dict_vehicleInfo,
            'packages': arr_packagesInfo
        })
    except Exception as e:
        print(f"Error in /get_vehicle_data: {e}")
        return jsonify({'error': str(e)}), 500

@obj_app.route('/simulate', methods=['POST'])
def simulate():
    """
    MODIFIED: Initiates the core 'Experimentation Stage' by running the algorithm.
    It now only receives the capacity and algorithm name, and the solver fetches
    the full aggregated dataset itself.
    """
    try:
        obj_data = request.get_json()
        str_algorithmName = obj_data.get('algorithm')
        flt_capacityCm3 = float(obj_data.get('capacity'))
        
        # MODIFICATION: The 'packages' array is no longer passed from the frontend.
        print(f"Starting simulation for {str_algorithmName} with capacity {flt_capacityCm3}...")

        # The solver now fetches the full aggregated data internally.
        dict_results = solveLoadingProblem(
            str_algorithmName,
            flt_capacityCm3
        )

        print("Simulation finished. Sending results to frontend.")
        return jsonify(dict_results)
    except Exception as e:
        print(f"Error during simulation: {e}")
        return jsonify({'error': f'An internal error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    # Use single-threaded mode for predictable behavior and easier debugging.
    obj_app.run(host='0.0.0.0', port=5000, debug=True, threaded=False)