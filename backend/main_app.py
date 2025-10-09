"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Main Application and Web Server

Purpose of this file:
This file serves as the main entry point and the central nervous system for the
entire application. It initializes a Flask web server that listens for and responds
to requests from the user's web browser. Its most critical function is managing
the execution of long-running, computationally intensive optimization algorithms.
To prevent the user's browser from timing out or becoming unresponsive during these
simulations, this module employs a background threading architecture. This design is
the fundamental solution to the core computing problem of running complex scientific
simulations within an interactive web environment.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
from flask import Flask, render_template, request, jsonify  # Core components for the web server.
import os        # Used for interacting with the operating system, like finding file paths.
import sys       # Allows manipulation of Python's runtime environment, like modifying the path.
import uuid      # Used to generate unique identifiers for each simulation and data-loading job.
from threading import Thread, Lock # The fundamental tools for running tasks in the background.
import multiprocessing # --- ADDED: For leveraging multiple CPU cores to accelerate simulations ---


# --- System Path Configuration ---
# Add the project's root directory to the Python path.
# This is a crucial step to ensure that when we try to import our other custom
# modules (like the data manager or the algorithms), Python knows where to find them.
g_str_projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if g_str_projectRoot not in sys.path:
    sys.path.insert(0, g_str_projectRoot)


# --- Import Custom Application Modules ---
# These imports bring in the core logic that our web server will orchestrate.
# The orchestrator is the "conductor" of the experiment, while the data manager
# handles the "Sources of Data" part of the research.
from backend.data_management.data_manager import fnGetAllVehicleCapacities, fnGetDisplayDataForVehicle
from backend.simulation.simulation_orchestrator import fnOrchestrateSimulationRun
from backend.simulation.custom_exceptions import CancelledException


# --- Flask Application Initialization ---
# This line creates the actual web application instance using the Flask framework.
# We tell it where to find our HTML templates and static files (CSS, JavaScript).
g_obj_flaskApp = Flask(__name__, template_folder='../templates', static_folder='../static')


# --- GLOBAL STATE MANAGEMENT FOR ASYNCHRONOUS OPERATIONS ---
# To manage tasks running in the background, we need a way for the main server
# thread to track their status. These global dictionaries act as a "job board."
# Each dictionary is protected by a "Lock" to prevent a serious issue called a
# "race condition," where two threads might try to write to the same spot in memory
# at the exact same time, leading to corrupted data. The Lock ensures that only
# one thread can access the dictionary at any given moment.

# This dictionary holds the status and results of every simulation run.
g_dict_runningSimulations = {}
g_obj_simulationLock = Lock() # A digital "talking stick" to ensure orderly access to the dictionary.

# This dictionary tracks the status of dataset loading and preprocessing jobs.
g_dict_runningDataLoads = {}
g_obj_dataLoadLock = Lock()


def _fnExecuteSimulationInThread(strSimulationId, strAlgorithmName, fltCapacityCm3, blnIsDynamicConstraintEnabled):
    """
    This is the function that a background thread will execute when a simulation is started.
    By placing the heavy computational work of the optimization algorithm here, we free up
    the main web server to continue responding to the user. This is what allows the loading
    spinner on the screen to animate smoothly and for the "Cancel" button to work, even
    while the server is deep in complex calculations.

    Args:
        strSimulationId (str): The unique ID for this specific simulation run.
        strAlgorithmName (str): The name of the algorithm to run (e.g., 'PSO').
        fltCapacityCm3 (float): The vehicle capacity selected by the user.
        blnIsDynamicConstraintEnabled (bool): A flag indicating if the dynamic constraint should be applied.
    """
    global g_dict_runningSimulations

    try:
        # Retrieve the shared "control panel" dictionaries for this specific job.
        # These were created in the main thread and are shared with this background thread.
        # This is how the main thread can "signal" this thread to cancel.
        dict_cancellationFlag = g_dict_runningSimulations[strSimulationId]['cancellation_flag']
        dict_progressTracker = g_dict_runningSimulations[strSimulationId]['progress'] # For real-time UI updates.

        # --- MODIFIED: Parallel Processing Setup ---
        # To significantly speed up the simulation, we create a pool of worker processes.
        # This allows fitness evaluations to be spread across multiple CPU cores.
        # We leave one core free to ensure the main server and OS remain responsive.
        int_num_cores = max(1, multiprocessing.cpu_count() - 1)
        print(f"--- Simulation {strSimulationId} starting: Utilizing {int_num_cores} CPU cores for parallel processing. ---")
        
        with multiprocessing.Pool(processes=int_num_cores) as pool:
            # Delegate the entire complex logic of the experiment to the simulation orchestrator module.
            # We now pass the 'pool' object to be used by the underlying algorithms.
            dict_results = fnOrchestrateSimulationRun(
                strAlgorithmName,
                fltCapacityCm3,
                dict_cancellationFlag,
                blnIsDynamicConstraintEnabled,
                dict_progressTracker, # Pass the progress tracker down into the core simulation logic.
                pool=pool # --- ADDED: Pass the worker pool to the orchestrator.
            )
        # --- END OF MODIFICATION ---

        # Once the simulation is complete, we must safely update the global job board.
        # We acquire the lock to ensure no other thread interferes while we write the result.
        with g_obj_simulationLock:
            # A final check: Did the user click "Cancel" right as the simulation finished?
            # This handles that edge case to ensure the final status is 'cancelled'.
            if g_dict_runningSimulations[strSimulationId]['status'] == "cancelling":
                g_dict_runningSimulations[strSimulationId]['status'] = 'cancelled'
                g_dict_runningSimulations[strSimulationId]['result'] = None
            else:
                # If not cancelled, we mark it as completed and store the valuable results.
                g_dict_runningSimulations[strSimulationId]['status'] = 'completed'
                g_dict_runningSimulations[strSimulationId]['result'] = dict_results

    except CancelledException:
        # This block catches the special exception raised when the algorithm
        # detects that the cancellation flag has been set. It's a clean way to exit gracefully.
        with g_obj_simulationLock:
            g_dict_runningSimulations[strSimulationId]['status'] = 'cancelled'
            print(f"Simulation {strSimulationId} cancelled successfully.")

    except Exception as obj_err:
        # A catch-all for any other unexpected errors during the simulation.
        # This ensures the application doesn't crash and can report the error to the user.
        print(f"Error in simulation thread {strSimulationId}: {obj_err}")
        with g_obj_simulationLock:
            g_dict_runningSimulations[strSimulationId]['status'] = 'error'
            g_dict_runningSimulations[strSimulationId]['result'] = {'error': str(obj_err)}


def _fnExecuteDataLoadingInThread(strLoadId, fltCapacityCm3):
    """
    Runs the data loading and preprocessing in a separate background thread.
    While not as long as a simulation, parsing the very large Amazon dataset can still
    be slow enough to make the user interface feel sluggish. This function prevents that.

    Args:
        strLoadId (str): The unique ID for this data loading job.
        fltCapacityCm3 (float): The capacity to filter the dataset by.
    """
    global g_dict_runningDataLoads
    try:
        # Get the cancellation flag for this job.
        dict_cancellationFlag = g_dict_runningDataLoads[strLoadId]['cancellation_flag']

        # Delegate the task of reading and preparing the data to the data manager module.
        dict_vehicleInfo, arr_packagesInfo = fnGetDisplayDataForVehicle(fltCapacityCm3, dict_cancellationFlag)

        # Safely update the shared job board with the loaded data.
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
         # Handle a graceful cancellation.
         with g_obj_dataLoadLock:
            g_dict_runningDataLoads[strLoadId]['status'] = 'cancelled'
            print(f"Data loading job {strLoadId} cancelled successfully.")

    except Exception as obj_err:
        # Handle any unexpected errors.
        with g_obj_dataLoadLock:
            g_dict_runningDataLoads[strLoadId]['status'] = 'error'
            g_dict_runningDataLoads[strLoadId]['result'] = {'error': str(obj_err)}


# --- WEB SERVER ROUTE DEFINITIONS ---
# These blocks of code define the different "pages" or API "endpoints" of our web application.
# The `@g_obj_flaskApp.route(...)` is a special instruction (a "decorator") that tells Flask:
# "When a web browser asks for THIS specific URL, run the function right below me."

@g_obj_flaskApp.route('/')
def fnHandleIndexPageRequest():
    """
    This function handles requests for the main page of the application (the root URL).
    It renders the primary HTML file, `index.html`, which serves as the user interface.
    The initial page is rendered quickly with an empty list of vehicle capacities, which
    are then fetched separately by the frontend JavaScript. This improves perceived load time.
    """
    return render_template('index.html', capacities=[])


@g_obj_flaskApp.route('/get_all_capacities', methods=['GET'])
def fnHandleGetAllCapacitiesRequest():
    """
    Provides a dedicated API endpoint for the slow task of reading the dataset to find
    all unique vehicle capacities. By isolating this operation, we prevent it from
    blocking the rendering of the main application page, making the UI appear much faster.
    """
    try:
        arr_capacities = fnGetAllVehicleCapacities()
        # jsonify is a Flask helper that correctly formats our Python list into JSON for the web browser.
        return jsonify({'capacities': arr_capacities})
    except Exception as obj_err:
        print(f"Error in /get_all_capacities: {obj_err}")
        return jsonify({'error': str(obj_err)}), 500 # Return an error code.


@g_obj_flaskApp.route('/start_data_loading', methods=['POST'])
def fnHandleStartDataLoadingRequest():
    """
    This endpoint is called by the frontend JavaScript when the user selects a vehicle.
    Its job is to kick off the background data-loading process. It does NOT wait for the
    process to finish. Instead, it immediately returns a unique job ID. The frontend can then
    use this ID to ask for status updates separately. This is a core part of the asynchronous design.
    """
    global g_dict_runningDataLoads

    obj_data = request.get_json()  # Get the data sent from the browser (the selected capacity).
    flt_capacityCm3 = float(obj_data.get('capacity'))
    str_loadId = str(uuid.uuid4()) # Generate a new, unique ID for this job.

    # This is the "control flag." It's a dictionary so it can be passed by reference,
    # meaning if the main thread changes `is_cancelled` to True, the background thread sees that change instantly.
    dict_cancellationFlag = {'is_cancelled': False}
    # Create a new Thread object, telling it which function to run and what arguments to give it.
    obj_thread = Thread(target=_fnExecuteDataLoadingInThread, args=(str_loadId, flt_capacityCm3))

    # Add this new job to our global "job board" dictionary.
    with g_obj_dataLoadLock:
        g_dict_runningDataLoads[str_loadId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dict_cancellationFlag
        }

    obj_thread.start() # Start the background job.
    return jsonify({'status': 'started', 'load_id': str_loadId}) # Immediately reply to the browser.


@g_obj_flaskApp.route('/data_loading_status/<string:strLoadId>')
def fnHandleDataLoadingStatusRequest(strLoadId):
    """
    An API endpoint that allows the client to periodically "poll" (ask for updates)
    about a running data loading job using its unique ID.
    """
    with g_obj_dataLoadLock:
        dict_job = g_dict_runningDataLoads.get(strLoadId)
        if not dict_job:
            return jsonify({'status': 'not_found'}), 404
        # Return the current status and the result if it's completed or has an error.
        return jsonify({'status': dict_job['status'], 'result': dict_job['result']})


@g_obj_flaskApp.route('/cancel_data_loading/<string:strLoadId>', methods=['POST'])
def fnHandleCancelDataLoadingRequest(strLoadId):
    """
    An endpoint to request the cancellation of a running data loading job.
    It works by simply setting the shared `is_cancelled` flag to True. The background
    thread is designed to check this flag periodically and exit gracefully if it sees the change.
    """
    with g_obj_dataLoadLock:
        dict_job = g_dict_runningDataLoads.get(strLoadId)
        if dict_job and dict_job['status'] == 'running':
            print(f"Received cancel request for data loading job: {strLoadId}")
            # This is the signal. Setting this to True tells the thread to stop.
            dict_job['cancellation_flag']['is_cancelled'] = True
            dict_job['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        else:
            return jsonify({'status': 'not_found_or_already_complete'}), 404


@g_obj_flaskApp.route('/start_simulation', methods=['POST'])
def fnHandleStartSimulationRequest():
    """
    The endpoint called by the "Simulate" button. Much like the data loading endpoint,
    this kicks off the heavy simulation work in a background thread and immediately
    returns a unique simulation ID to the frontend for status polling.
    """
    global g_dict_runningSimulations

    # Get simulation parameters from the user's request.
    obj_data = request.get_json()
    str_algorithmName = obj_data.get('algorithm')
    flt_capacityCm3 = float(obj_data.get('capacity'))
    bln_isDynamicConstraintEnabled = obj_data.get('dynamic_constraint_enabled', True)
    str_simulationId = str(uuid.uuid4())

    # Create the mutable dictionaries that will be shared between the main and background threads.
    # The progress tracker will be updated by the algorithm with its current generation number.
    dict_progressTracker = {'current': 0, 'total': 0, 'message': 'Initializing...'}
    dict_cancellationFlag = {'is_cancelled': False}

    # Set up the new thread for the simulation.
    obj_thread = Thread(
        target=_fnExecuteSimulationInThread,
        args=(str_simulationId, str_algorithmName, flt_capacityCm3, bln_isDynamicConstraintEnabled)
    )

    # Add the job to the "job board."
    with g_obj_simulationLock:
        g_dict_runningSimulations[str_simulationId] = {
            'thread': obj_thread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dict_cancellationFlag,
            'progress': dict_progressTracker # Add the progress tracker to the job's entry.
        }

    obj_thread.start() # Start the simulation.
    print(f"Started simulation with ID: {str_simulationId}")
    return jsonify({'status': 'started', 'simulation_id': str_simulationId})


@g_obj_flaskApp.route('/simulation_status/<string:strSimulationId>')
def fnHandleSimulationStatusRequest(strSimulationId):
    """
    An API endpoint that allows the client to poll for the status and progress of a
    running simulation, which is used to update the loading spinner's text.
    """
    with g_obj_simulationLock:
        dict_sim = g_dict_runningSimulations.get(strSimulationId)
        if not dict_sim:
            return jsonify({'status': 'not_found'}), 404
        
        # We don't delete the job entry after completion. This prevents a race condition where the client
        # might poll for the final result at the exact moment the job finishes, and miss it.
        # The frontend is responsible for fetching the final result one last time after seeing the 'completed' status.
        return jsonify({
            'status': dict_sim['status'],
            'result': dict_sim['result'],
            'progress': dict_sim.get('progress', {}) # The 'progress' dictionary is included in the response.
        })


@g_obj_flaskApp.route('/cancel_simulation/<string:strSimulationId>', methods=['POST'])
def fnHandleCancelSimulationRequest(strSimulationId):
    """
    An API endpoint to request the cancellation of a running simulation by setting
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


# --- Application Entry Point ---
# This special block of code checks if the script is being run directly.
# If it is, it starts the Flask development server.
if __name__ == '__main__':
    # --- ADDED: Set the start method for multiprocessing ---
    # This is important for compatibility, especially on macOS and Windows.
    # 'fork' is generally faster but can be less safe; 'spawn' is more robust.
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        # This will raise a RuntimeError if the start method has already been set.
        # It's safe to ignore in that case.
        pass
    # --- END OF ADDITION ---
    
    # Starts the web server. `threaded=True` is absolutely essential. It allows Flask
    # to handle multiple requests simultaneously, such as a user clicking "Cancel"
    # while a background thread is running and the frontend is polling for status.
    g_obj_flaskApp.run(host='0.0.0.0', port=5000, debug=True, threaded=True)