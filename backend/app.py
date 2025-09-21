import os
from flask import Flask, jsonify, render_template, request
from utils.data_loader import load_data, get_routes_and_capacities, get_route_data_by_capacity
from utils.problem_solver import solve_packing_problem

# Initialize the Flask application
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Define the absolute paths for the dataset files to ensure they are found correctly
# This is robust and avoids issues with the script's execution directory
base_dir = os.path.dirname(os.path.abspath(__file__))
PACKAGE_FILE = os.path.join(base_dir, 'almrrc2021', 'almrrc2021-data-evaluation', 'model_apply_inputs', 'eval_package_data.json')
ROUTE_FILE = os.path.join(base_dir, 'almrrc2021', 'almrrc2021-data-evaluation', 'model_apply_inputs', 'eval_route_data.json')

# Load package and route data into memory when the application starts
# This avoids re-reading large files on every request, improving performance
package_data, route_data = load_data(PACKAGE_FILE, ROUTE_FILE)
# Pre-process the route data to get a list of unique vehicle capacities for the frontend
routes_and_capacities = get_routes_and_capacities(route_data)

@app.route('/')
def index():
    """
    Serves the main HTML page of the application.
    This is the user-facing interface.
    """
    return render_template('index.html')

@app.route('/api/capacities', methods=['GET'])
def get_capacities():
    """
    API endpoint to provide the list of unique vehicle capacities to the frontend.
    This populates the dropdown in the simulation settings modal.
    """
    # Sorting ensures a consistent order in the UI
    unique_capacities = sorted(list(routes_and_capacities.keys()))
    return jsonify(unique_capacities)

@app.route('/api/initial-data', methods=['POST'])
def get_initial_data():
    """
    API endpoint to fetch the initial data for a selected vehicle capacity.
    When a user selects a capacity, this provides the corresponding route and package info
    to display in the left panel of the UI before the simulation runs.
    """
    data = request.get_json()
    capacity = float(data.get('capacity', 0))

    if not capacity:
        return jsonify({"error": "Capacity not provided"}), 400

    # Retrieve pre-filtered route information based on the selected capacity
    initial_data = get_route_data_by_capacity(capacity, route_data, package_data)

    if not initial_data:
        return jsonify({"error": "No data found for the selected capacity"}), 404

    return jsonify(initial_data)

@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    The main API endpoint that triggers the optimization process.
    It receives the algorithm and vehicle capacity from the user,
    runs the simulation, and returns the calculated metrics.
    """
    try:
        data = request.get_json()
        algorithm_name = data.get('algorithm')
        capacity = float(data.get('capacity', 0))

        # Log the incoming request
        print(f"\n[INFO] Received simulation request: Algorithm='{algorithm_name}', Capacity={capacity}")

        if not all([algorithm_name, capacity]):
            return jsonify({"error": "Missing parameters. Required: algorithm, capacity"}), 400

        # Delegate the complex task of running the simulation to the problem_solver module
        # This keeps the main app file clean and focused on web-related tasks
        results = solve_packing_problem(algorithm_name, capacity, route_data, package_data)

        if "error" in results:
             return jsonify(results), 500

        return jsonify(results)

    except Exception as e:
        # Gracefully handle any unexpected errors during simulation
        # This prevents the server from crashing and provides a helpful error message to the user
        app.logger.error(f"An error occurred during simulation: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == '__main__':
    # Runs the Flask application in debug mode for development
    # In a production environment, a proper WSGI server like Gunicorn or Waitress should be used
    app.run(debug=True)