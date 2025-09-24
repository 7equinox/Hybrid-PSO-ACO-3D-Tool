# HYBRID-PSO-ACO-3D-TOOL/backend/app.py

from flask import Flask, render_template, request, jsonify
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Correctly import from respective modules
from backend.utils.data_loader import get_all_vehicle_capacities, load_data
from backend.utils.problem_solver import solve_loading_problem

# Initialize the Flask application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    capacities = get_all_vehicle_capacities()
    return render_template('index.html', capacities=capacities)

# MODIFIED API to fetch paginated data
@app.route('/get_vehicle_data', methods=['POST'])
def get_vehicle_data():
    try:
        data = request.get_json()
        capacity_cm3 = float(data.get('capacity'))
        # Get page and page_size from the request, with default values
        page = data.get('page', 1)
        page_size = 1 # A reasonable chunk size

        # The data_loader now handles pagination
        vehicle_info, packages_info = load_data(capacity_cm3, page=page, page_size=page_size)
        
        if not vehicle_info:
            return jsonify({'error': 'Vehicle with specified capacity not found.'}), 404
        
        return jsonify({
            'vehicle': vehicle_info,
            'packages': packages_info
        })
    except Exception as e:
        print(f"Error in /get_vehicle_data: {e}")
        return jsonify({'error': str(e)}), 500

# MODIFIED Simulation endpoint to now accept the full list of packages from the frontend
@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json()
        algorithm_name = data.get('algorithm')
        capacity_cm3 = float(data.get('capacity'))
        # IMPORTANT: It receives the package list from the frontend again
        all_packages = data.get('packages')

        if not all_packages:
            return jsonify({'error': 'Package data is required for simulation.'}), 400

        print(f"Starting simulation for {algorithm_name} with {len(all_packages)} packages...")
        
        # It passes all 3 arguments to the solver
        results = solve_loading_problem(algorithm_name, capacity_cm3, all_packages)

        print("Simulation finished. Sending results to frontend.")
        return jsonify(results)
    except Exception as e:
        print(f"Error during simulation: {e}")
        return jsonify({'error': f'An internal error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)