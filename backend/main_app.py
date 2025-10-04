"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Main Application

Purpose of this file:
Serves as the main entry point and web server for the application. It handles
HTTP requests from the user interface, manages asynchronous simulation and
data-loading tasks using background threads, and returns the final
experimental results to the frontend for visualization. This asynchronous
architecture is critical to solving the computational problem of long-running
optimization algorithms which would otherwise time out in a standard web request.

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

# Add the project root to the Python path to ensure all modules can be found.
g_str_projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if g_str_projectRoot not in sys.path:
    sys.path.insert(0, g_str_projectRoot)

# Import the core logic modules of the application.
from backend.data_management.data_manager import fn_getAllVehicleCapacities, fn_getDisplayDataForVehicle
from backend.simulation.simulation_orchestrator import fn_orchestrateSimulationRun
from backend.simulation.custom_exceptions import CancelledException

# Initialize the Flask web application instance.
g_obj_flaskApp = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- THREAD MANAGEMENT FOR ASYNCHRONOUS OPERATIONS ---
# Global dictionaries are used to track the state of long-running background jobs.
# This allows the main web server to remain responsive while heavy computation occurs elsewhere.
# A Lock is used for each dictionary to ensure thread-safe access, preventing race conditions.
g_dict_runningSimulations = {}
g_obj_simulationLock = Lock()

g_dict_runningDataLoads = {}
g_obj_dataLoadLock = Lock()


def _executeSimulationInThread(strSimulationId, strAlgorithmName, fltCapacityCm3, blnIsDynamicConstraintEnabled):
    """
    This function is the target for a background thread that executes a simulation.
    Running the optimization algorithm here prevents the user's web browser from
    freezing or timing out, which is essential for conducting experiments that
    can take several minutes.
    """
    global g_dict_runningSimulations

    try:
        # Retrieve the shared cancellation flag. The algorithm inside the thread will
        # periodically check this flag to see if the user has requested to stop the process.
        dict_cancellationFlag = g_dict_runningSimulations[strSimulationId]['cancellation_flag']

        # Delegate the complex logic of the simulation to the orchestrator module.
        dict_results = fn_orchestrateSimulationRun(
            strAlgorithmName, 
            fltCapacityCm3, 
            dict_cancellationFlag, 
            blnIsDynamicConstraintEnabled
        )

        # Use a lock to safely update the shared global dictionary with the results.
        with g_obj_simulationLock:
            # Re-check the flag. It's possible the user cancelled *just* as
            # the simulation finished, before this lock was acquired.
            if g_dict_runningSimulations[strSimulationId]['status'] == "cancelling":
                g_dict_runningSimulations[strSimulationId]['status'] = 'cancelled'
                g_dict_runningSimulations[strSimulationId]['result'] = None
            else:
                g_dict_runningSimulations[strSimulationId]['status'] = 'completed'
                g_dict_runningSimulations[strSimulationId]['result'] = dict_results

    except CancelledException:
        # If the algorithm gracefully exits due to cancellation, update its status.
        with g_obj_simulationLock:
            g_dict_runningSimulations[strSimulationId]['status'] = 'cancelled'
            print(f"Simulation {strSimulationId} cancelled successfully.")

    except Exception as obj_err:
        # If any other error occurs, capture it and report it back to the user.
        print(f"Error in simulation thread {strSimulationId}: {obj_err}")
        with g_obj_simulationLock:
            g_dict_runningSimulations[strSimulationId]['status'] = 'error'
            g_dict_runningSimulations[strSimulationId]['result'] = {'error': str(obj_err)}


def _executeDataLoadingInThread(strLoadId, fltCapacityCm3):
    """
    Runs the data loading and preprocessing in a background thread. This is necessary
    because parsing the large JSON dataset can be an I/O-intensive operation that
    could otherwise make the UI unresponsive.
    """
    global g_dict_runningDataLoads
    try:
        dict_cancellationFlag = g_dict_runningDataLoads[strLoadId]['cancellation_flag']

        # Delegate the data loading task to the data manager module.
        dict_vehicleInfo, arr_packagesInfo = fn_getDisplayDataForVehicle(fltCapacityCm3, dict_cancellationFlag)

        # Safely update the shared state with the loaded data.
        with g_obj_dataLoadLock:
            if g_dict_runningDataLoads[strLoadId]['status'] == "cancelling":
                g_dict_runningDataLoads[strLoadId]['status'] = 'cancelled'
            elif not dict_vehicleInfo:
                 g_dict_runningDataLoads[strLoadId]['status'] = 'error'
                 g_dict_runningDataLoads[strLoadId]['result'] = {'error': 'Could not find a valid sample route for the specified capacity.'}
            else:
                g_dict_runningDataLoads[strLoadId]['status'] = 'completed'
                g_dict_runningDataLoads[strLoadId]['result'] = {
                    'vehicle': dict_vehicleInfo,
                    'packages': arr_packagesInfo
                }

    except CancelledException:
         with g_obj_dataLoadLock:
            g_dict_runningDataLoads[strLoadId]['status'] = 'cancelled'
            print(f"Data loading job {strLoadId} cancelled successfully.")

    except Exception as obj_err:
        with g_obj_dataLoadLock:
            g_dict_runningDataLoads[strLoadId]['status'] = 'error'
            g_dict_runningDataLoads[strLoadId]['result'] = {'error': str(obj_err)}


@g_obj_flaskApp.route('/')
def handleIndexPage():
    """
    Renders the main HTML page of the application. The page is initially rendered
    with an empty list for vehicle capacities to ensure a very fast initial load time.
    The capacities are then fetched by the frontend JavaScript after the page loads.
    """
    return render_template('index.html', capacities=[])


@g_obj_flaskApp.route('/get_all_capacities', methods=['GET'])
def handleGetAllCapacitiesRequest():
    """
    Provides a dedicated API endpoint for the slow task of reading the dataset
    to find all unique vehicle capacities. Isolating this slow operation prevents
    it from blocking the rendering of the main application page.
    """
    try:
        arr_capacities = fn_getAllVehicleCapacities()
        return jsonify({'capacities': arr_capacities})
    except Exception as obj_err:
        print(f"Error in /get_all_capacities: {obj_err}")
        return jsonify({'error': str(obj_err)}), 500


@g_obj_flaskApp.route('/start_data_loading', methods=['POST'])
def handleStartDataLoadingRequest():
    """
    API endpoint to initiate an asynchronous data loading job. It creates a unique
    ID for the job, starts a new thread to perform the work, and immediately
    returns the ID to the client so it can start polling for the result.
    """
    global g_dict_runningDataLoads

    obj_data = request.get_json()
    flt_capacityCm3 = float(obj_data.get('capacity'))
    str_loadId = str(uuid.uuid4())

    # Create the mutable dictionary that will act as a cancellation signal.
    dict_cancellationFlag = {'is_cancelled': False}
    obj_thread = Thread(target=_executeDataLoadingInThread, args=(str_loadId, flt_capacityCm3))

    # Add the job to the tracking dictionary.
    with g_obj_dataLoadLock:
        g_dict_runningDataLoads[str_loadId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dict_cancellationFlag
        }

    obj_thread.start() # Start the background thread.
    return jsonify({'status': 'started', 'load_id': str_loadId})


@g_obj_flaskApp.route('/data_loading_status/<string:strLoadId>')
def handleDataLoadingStatusRequest(strLoadId):
    """
    API endpoint that allows the client to periodically poll for the status of a
    running data loading job using its unique ID.
    """
    with g_obj_dataLoadLock:
        dict_job = g_dict_runningDataLoads.get(strLoadId)
        if not dict_job:
            return jsonify({'status': 'not_found'}), 404
        # Return the current status and the result if it's completed or has errored.
        return jsonify({'status': dict_job['status'], 'result': dict_job['result']})


@g_obj_flaskApp.route('/cancel_data_loading/<string:strLoadId>', methods=['POST'])
def handleCancelDataLoadingRequest(strLoadId):
    """
    API endpoint to request the cancellation of a running data loading job.
    It works by setting a flag that the background thread checks periodically.
    """
    with g_obj_dataLoadLock:
        dict_job = g_dict_runningDataLoads.get(strLoadId)
        if dict_job and dict_job['status'] == 'running':
            print(f"Received cancel request for data loading job: {strLoadId}")
            # Set the flag to True, signaling the thread to stop.
            dict_job['cancellation_flag']['is_cancelled'] = True
            dict_job['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        else:
            return jsonify({'status': 'not_found_or_already_complete'}), 404


@g_obj_flaskApp.route('/start_simulation', methods=['POST'])
def handleStartSimulationRequest():
    """
    API endpoint to initiate an asynchronous simulation. It creates a unique job ID,
    starts a new background thread for the simulation, and immediately returns
    the ID to the client for status polling.
    """
    global g_dict_runningSimulations

    obj_data = request.get_json()
    str_algorithmName = obj_data.get('algorithm')
    flt_capacityCm3 = float(obj_data.get('capacity'))
    bln_isDynamicConstraintEnabled = obj_data.get('dynamic_constraint_enabled', True) # Default to True if not provided
    str_simulationId = str(uuid.uuid4())

    dict_cancellationFlag = {'is_cancelled': False}
    obj_thread = Thread(
        target=_executeSimulationInThread,
        args=(str_simulationId, str_algorithmName, flt_capacityCm3, bln_isDynamicConstraintEnabled)
    )

    with g_obj_simulationLock:
        g_dict_runningSimulations[str_simulationId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dict_cancellationFlag
        }

    obj_thread.start()
    print(f"Started simulation with ID: {str_simulationId}")
    return jsonify({'status': 'started', 'simulation_id': str_simulationId})


@g_obj_flaskApp.route('/simulation_status/<string:strSimulationId>')
def handleSimulationStatusRequest(strSimulationId):
    """
    API endpoint that allows the client to poll for the status of a running simulation.
    """
    with g_obj_simulationLock:
        dict_sim = g_dict_runningSimulations.get(strSimulationId)
        if not dict_sim:
            return jsonify({'status': 'not_found'}), 404
        # The job entry is not deleted on completion to prevent a race condition
        # where the client polls just as the job finishes but before it can get the result.
        return jsonify({'status': dict_sim['status'], 'result': dict_sim['result']})


@g_obj_flaskApp.route('/cancel_simulation/<string:strSimulationId>', methods=['POST'])
def handleCancelSimulationRequest(strSimulationId):
    """
    API endpoint to request the cancellation of a running simulation by setting
    the shared cancellation flag to True.
    """

    with g_obj_simulationLock:
        dict_sim = g_dict_runningSimulations.get(strSimulationId)
        if dict_sim and dict_sim['status'] == 'running':
            print(f"Received cancel request for simulation ID: {strSimulationId}")
            dict_sim['cancellation_flag']['is_cancelled'] = True
            dict_sim['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        elif dict_sim:
            # The job has already finished or been cancelled.
            return jsonify({'status': 'already_complete'}), 404
        else:
            return jsonify({'status': 'not_found'}), 404


# This block executes only when the script is run directly.
if __name__ == '__main__':
    # Starts the Flask development server. `threaded=True` is essential to handle
    # concurrent requests from the UI while background jobs are running.
    g_obj_flaskApp.run(host='0.0.0.0', port=5000, debug=True, threaded=True)