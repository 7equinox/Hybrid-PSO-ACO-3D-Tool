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
import uuid
from threading import Thread, Lock

# Add the project root to the Python path for correct module resolution.
g_str_projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if g_str_projectRoot not in sys.path:
    sys.path.insert(0, g_str_projectRoot)

# Import the refactored modules.
from backend.data_management.data_loader import getAllVehicleCapacities, getDisplayDataForVehicle
from backend.simulation.problem_solver import solveLoadingProblem
from backend.simulation.exceptions import CancelledException

# Initialize the Flask application
obj_app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- THREAD MANAGEMENT FOR CANCELLATION ---
# This global dictionary will store the state of all running simulations.
# A Lock is used to make sure that concurrent requests don't corrupt this dictionary.
g_dict_simulations = {}
g_obj_lock = Lock()

def _run_simulation_thread(str_simulationId, str_algorithmName, flt_capacityCm3, cancellation_flag):
    """
    This function is the target for our background thread. It runs the heavy
    computation and updates the shared global state with the result.
    """
    global g_dict_simulations
    
    try:
        # The cancellation flag object is passed into the solver.
        cancellation_flag = g_dict_simulations[str_simulationId]['cancellation_flag']
        
        dict_results = solveLoadingProblem(str_algorithmName, flt_capacityCm3, cancellation_flag)
        
        with g_obj_lock:
            # Re-check the flag. It's possible the user cancelled *just* as
            # the simulation finished, before this lock was acquired.
            if g_dict_simulations[str_simulationId]['status'] == "cancelling":
                g_dict_simulations[str_simulationId]['status'] = 'cancelled'
                g_dict_simulations[str_simulationId]['result'] = None
                print(f"Simulation {str_simulationId} was cancelled just before completion.")
            else:
                g_dict_simulations[str_simulationId]['status'] = 'completed'
                g_dict_simulations[str_simulationId]['result'] = dict_results

    except CancelledException:
        with g_obj_lock:
            g_dict_simulations[str_simulationId]['status'] = 'cancelled'
            print(f"Simulation {str_simulationId} cancelled successfully.")

    except Exception as e:
        print(f"Error in simulation thread {str_simulationId}: {e}")
        with g_obj_lock:
            g_dict_simulations[str_simulationId]['status'] = 'error'
            g_dict_simulations[str_simulationId]['result'] = {'error': str(e)}

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

@obj_app.route('/start_simulation', methods=['POST'])
def start_simulation():
    """
    NEW ENDPOINT: Instantly starts the simulation in a background thread.
    It returns a unique ID for the client to track the job's progress.
    """
    global g_dict_simulations
    
    obj_data = request.get_json()
    str_algorithmName = obj_data.get('algorithm')
    flt_capacityCm3 = float(obj_data.get('capacity'))
    str_simulationId = str(uuid.uuid4())

    # This mutable dictionary acts as our signal to the running thread.
    cancellation_flag = {'is_cancelled': False}
    
    obj_thread = Thread(
        target=_run_simulation_thread,
        args=(str_simulationId, str_algorithmName, flt_capacityCm3, cancellation_flag)
    )

    with g_obj_lock:
        g_dict_simulations[str_simulationId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': cancellation_flag
        }
    
    obj_thread.start()
    print(f"Started simulation with ID: {str_simulationId}")
    
    return jsonify({'status': 'started', 'simulation_id': str_simulationId})


@obj_app.route('/simulation_status/<string:str_simulationId>')
def simulation_status(str_simulationId):
    """
    NEW ENDPOINT: Allows the client to poll for the status of a simulation.
    """
    with g_obj_lock:
        dict_sim = g_dict_simulations.get(str_simulationId)
        if dict_sim:
            if dict_sim['status'] in ['completed', 'error', 'cancelled']:
                # Once the job is done, we can remove it from memory.
                result_to_send = {'status': dict_sim['status'], 'result': dict_sim['result']}
                del g_dict_simulations[str_simulationId]
                return jsonify(result_to_send)
            else:
                # Still running
                return jsonify({'status': dict_sim['status']})
        else:
            return jsonify({'status': 'not_found'}), 404


@obj_app.route('/cancel_simulation/<string:str_simulationId>', methods=['POST'])
def cancel_simulation(str_simulationId):
    """
    NEW ENDPOINT: Sets the cancellation flag for a running simulation thread.
    """
    with g_obj_lock:
        dict_sim = g_dict_simulations.get(str_simulationId)
        if dict_sim and dict_sim['status'] == 'running':
            print(f"Received cancel request for simulation ID: {str_simulationId}")
            dict_sim['cancellation_flag']['is_cancelled'] = True
            dict_sim['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        else:
            return jsonify({'status': 'not_found_or_already_complete'}), 404

if __name__ == '__main__':
    # Use single-threaded mode for predictable behavior and easier debugging.
    obj_app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)