# HYBRID-PSO-ACO-3D-TOOL/backend/app.py

from flask import Flask, render_template, request, jsonify
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Correctly import from respective modules
# NO CHANGES here, as the function signatures from the outside remain the same.
from backend.utils.data_loader import get_all_vehicle_capacities, load_data
from backend.utils.problem_solver import solve_loading_problem

# Initialize the Flask application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    """
    COMMENT: This route now calls `get_all_vehicle_capacities` which is designed
    to load, use, and then immediately release the large dataset,
    preventing long-term memory usage.
    """
    capacities = get_all_vehicle_capacities()
    return render_template('index.html', capacities=capacities)

@app.route('/get_vehicle_data', methods=['POST'])
def get_vehicle_data():
    """
    COMMENT: The logic here is perfectly fine. It calls our modified `load_data` function.
    The memory-intensive part (cache creation) happens inside `load_data` only once
    per session and the memory is released right after.
    """
    try:
        data = request.get_json()
        capacity_cm3 = float(data.get('capacity'))
        page = data.get('page', 1)
        # Setting a small page size is good for incremental loading display on the frontend.
        page_size = 1

        # The data_loader now handles caching and memory management efficiently.
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

@app.route('/simulate', methods=['POST'])
def simulate():
    """
    COMMENT: No changes needed. This function correctly receives the package list
    from the frontend. Whether the user cancelled loading or it completed,
    this endpoint simply gets the final list, which is very memory efficient.
    The `solve_loading_problem` also doesn't load data anymore, so this is clean.
    """
    try:
        data = request.get_json()
        algorithm_name = data.get('algorithm')
        capacity_cm3 = float(data.get('capacity'))
        all_packages = data.get('packages') # Receives the list (complete or partial) from the frontend

        if not all_packages:
            return jsonify({'error': 'Package data is required for simulation.'}), 400

        print(f"Starting simulation for {algorithm_name} with {len(all_packages)} packages...")
        
        # Passes all necessary arguments to the solver.
        results = solve_loading_problem(algorithm_name, capacity_cm3, all_packages)

        print("Simulation finished. Sending results to frontend.")
        return jsonify(results)
    except Exception as e:
        print(f"Error during simulation: {e}")
        return jsonify({'error': f'An internal error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    # Using threaded=False is often better for debugging and predictable behavior without a multi-threaded design.
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=False)