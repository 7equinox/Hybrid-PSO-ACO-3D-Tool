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

# NEW: Added a separate dictionary and lock for data loading jobs.
g_dict_dataloads = {}
g_obj_dataload_lock = Lock()

def _run_simulation_thread(str_simulationId, str_algorithmName, flt_capacityCm3):
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

# NEW: Thread target for loading initial display data asynchronously.
def _run_data_loading_thread(str_loadId, flt_capacityCm3):
    """
    Runs the data loading and processing in a background thread so the UI
    doesn't freeze. It can now be cancelled.
    """
    global g_dict_dataloads
    try:
        cancellation_flag = g_dict_dataloads[str_loadId]['cancellation_flag']

        # The data loader function now accepts a cancellation_flag.
        dict_vehicleInfo, arr_packagesInfo = getDisplayDataForVehicle(flt_capacityCm3, cancellation_flag)

        with g_obj_dataload_lock:
            if g_dict_dataloads[str_loadId]['status'] == "cancelling":
                g_dict_dataloads[str_loadId]['status'] = 'cancelled'
            elif not dict_vehicleInfo:
                 g_dict_dataloads[str_loadId]['status'] = 'error'
                 g_dict_dataloads[str_loadId]['result'] = {'error': 'Could not find a valid sample route for the specified capacity.'}
            else:
                g_dict_dataloads[str_loadId]['status'] = 'completed'
                g_dict_dataloads[str_loadId]['result'] = {
                    'vehicle': dict_vehicleInfo,
                    'packages': arr_packagesInfo
                }
    
    except CancelledException:
         with g_obj_dataload_lock:
            g_dict_dataloads[str_loadId]['status'] = 'cancelled'
            print(f"Data loading job {str_loadId} cancelled successfully.")
    
    except Exception as e:
        print(f"Error in data loading thread {str_loadId}: {e}")
        with g_obj_dataload_lock:
            g_dict_dataloads[str_loadId]['status'] = 'error'
            g_dict_dataloads[str_loadId]['result'] = {'error': str(e)}

@obj_app.route('/')
def index():
    """
    MODIFIED: This function is now instantaneous.
    It no longer loads all vehicle capacities. It simply renders the
    HTML template with an empty list. The actual capacities will be
    fetched by JavaScript after the page loads.
    """
    # Pass an empty list to prevent the Jinja template from erroring out.
    return render_template('index.html', capacities=[])


@obj_app.route('/get_all_capacities', methods=['GET'])
def get_all_capacities():
    """
    NEW ENDPOINT: This is dedicated to the slow task.
    The frontend JavaScript will call this endpoint to populate the vehicle dropdown.
    This isolates the slow operation from the initial page load.
    """
    try:
        # The slow operation happens here, in its own request.
        arr_capacities = getAllVehicleCapacities()
        return jsonify({'capacities': arr_capacities})
    except Exception as e:
        print(f"Error in /get_all_capacities: {e}")
        return jsonify({'error': str(e)}), 500

# --- NEW ASYNC DATA LOADING ENDPOINTS ---
@obj_app.route('/start_data_loading', methods=['POST'])
def start_data_loading():
    """ Starts the initial data loading in a background thread. """
    global g_dict_dataloads
    
    obj_data = request.get_json()
    flt_capacityCm3 = float(obj_data.get('capacity'))
    str_loadId = str(uuid.uuid4())
    
    cancellation_flag = {'is_cancelled': False}
    obj_thread = Thread(target=_run_data_loading_thread, args=(str_loadId, flt_capacityCm3))
    
    with g_obj_dataload_lock:
        g_dict_dataloads[str_loadId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': cancellation_flag
        }
    
    obj_thread.start()
    return jsonify({'status': 'started', 'load_id': str_loadId})

@obj_app.route('/data_loading_status/<string:str_loadId>')
def data_loading_status(str_loadId):
    """ Allows the client to poll for the status of a data loading job. """
    with g_obj_dataload_lock:
        dict_job = g_dict_dataloads.get(str_loadId)
        if not dict_job:
            return jsonify({'status': 'not_found'}), 404
            
        # FIX: Do not delete the record. Just return the final status.
        # This prevents race conditions with cancel requests.
        return jsonify({'status': dict_job['status'], 'result': dict_job['result']})

@obj_app.route('/cancel_data_loading/<string:str_loadId>', methods=['POST'])
def cancel_data_loading(str_loadId):
    """ Sets the cancellation flag for a running data loading thread. """
    with g_obj_dataload_lock:
        dict_job = g_dict_dataloads.get(str_loadId)
        if dict_job and dict_job['status'] == 'running':
            print(f"Received cancel request for data loading job: {str_loadId}")
            dict_job['cancellation_flag']['is_cancelled'] = True
            dict_job['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        else:
            return jsonify({'status': 'not_found_or_already_complete'}), 404

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
        args=(str_simulationId, str_algorithmName, flt_capacityCm3) # REMOVED cancellation_flag from here
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
        if not dict_sim:
            return jsonify({'status': 'not_found'}), 404
        
        # FIX: The primary fix for the 404 race condition.
        # DO NOT delete the simulation entry from the dictionary upon completion.
        # Just return its final state. The client will stop polling.
        return jsonify({'status': dict_sim['status'], 'result': dict_sim['result']})


@obj_app.route('/cancel_simulation/<string:str_simulationId>', methods=['POST'])
def cancel_simulation(str_simulationId):
    """
    This endpoint now works reliably because the simulation status is not deleted.
    It can correctly identify a running job and set its cancellation flag.
    """
    with g_obj_lock:
        dict_sim = g_dict_simulations.get(str_simulationId)
        # Check if the job exists AND is currently in a runnable state.
        if dict_sim and dict_sim['status'] == 'running':
            print(f"Received cancel request for simulation ID: {str_simulationId}")
            dict_sim['cancellation_flag']['is_cancelled'] = True
            dict_sim['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        elif dict_sim:
            # The job exists but is already completed, cancelled, or has errored.
            return jsonify({'status': 'already_complete'}), 404
        else:
            # The job ID does not exist at all.
            return jsonify({'status': 'not_found'}), 404

if __name__ == '__main__':
    # Use single-threaded mode for predictable behavior and easier debugging.
    obj_app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)