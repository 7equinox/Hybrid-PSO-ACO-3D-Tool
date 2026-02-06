"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Main Application and Web Server

Purpose of this file:
This file serves as the main entry point and the central nervous system for the
entire application. It initializes a Flask web server that listens for and responds
to requests from the user's web browser. Its most critical function is managing
the execution of long-running, computationally intensive optimization algorithms
using a background threading architecture.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

# --- Import necessary libraries ---
from flask import Flask, render_template, request, jsonify # Core components for the web server
import os # Used for interacting with the operating system
import sys # Allows manipulation of Python's runtime environment
import uuid # Used to generate unique identifiers
from threading import Thread, Lock # Tools for background tasks


# --- System Path Configuration ---
# Add the project's root directory to the Python path to enable module imports.
# This ensures that backend packages can be resolved correctly.
g_strProjectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if g_strProjectRoot not in sys.path:
    sys.path.insert(0, g_strProjectRoot)

# --- Import Custom Application Modules ---
# Import logic for data management and simulation orchestration.
from backend.data_management.data_manager import getAllVehicleCapacities, getDisplayDataForVehicle
from backend.simulation.simulation_orchestrator import orchestrateSimulationRun
from backend.simulation.custom_exceptions import CancelledException


# --- Flask Application Initialization ---
# Initialize the Flask app with specific folders for templates and static assets.
g_objFlaskApp = Flask(__name__, template_folder='../templates', static_folder='../static')


# --- GLOBAL STATE MANAGEMENT ---
# Dictionaries acting as "job boards" for async tasks, protected by Locks to prevent race conditions.
# g_ denotes global scope as per naming convention.
g_dictRunningSimulations = {}
g_objSimulationLock = Lock()

g_dictRunningDataLoads = {}
g_objDataLoadLock = Lock()


# Executes the optimization algorithm in a background thread.
# This prevents blocking the main web server loop during heavy processing.
# Arguments:
#   strSimulationId: Unique UUID for the specific job.
#   strAlgorithmName: Name of algorithm to run (PSO, ACO, etc).
#   fltCapacityCm3: Volume constraint for the container.
#   blnIsDynamicConstraintEnabled: Boolean flag for extra constraints.
def _executeSimulationInThread(strSimulationId, strAlgorithmName, fltCapacityCm3, blnIsDynamicConstraintEnabled):
    
    global g_dictRunningSimulations

    try:
        # Retrieve control objects (cancellation flag, progress tracker) shared with the main thread.
        dictCancellationFlag = g_dictRunningSimulations[strSimulationId]['cancellation_flag']
        dictProgressTracker = g_dictRunningSimulations[strSimulationId]['progress']

        # Delegate execution to the orchestration module.
        dictResults = orchestrateSimulationRun(
            strAlgorithmName,
            fltCapacityCm3,
            dictCancellationFlag,
            blnIsDynamicConstraintEnabled,
            dictProgressTracker
        )

        # Securely update the global state with results.
        # Lock usage ensures thread safety during write operations.
        with g_objSimulationLock:
            # Check for edge-case cancellation during completion.
            if g_dictRunningSimulations[strSimulationId]['status'] == "cancelling":
                g_dictRunningSimulations[strSimulationId]['status'] = 'cancelled'
                g_dictRunningSimulations[strSimulationId]['result'] = None
            else:
                g_dictRunningSimulations[strSimulationId]['status'] = 'completed'
                g_dictRunningSimulations[strSimulationId]['result'] = dictResults

    except CancelledException:
        # Handle graceful cancellation request explicitly.
        with g_objSimulationLock:
            g_dictRunningSimulations[strSimulationId]['status'] = 'cancelled'
            print(f"Simulation {strSimulationId} cancelled successfully.")

    except Exception as objErr:
        # Catch-all for unexpected failures (General Error Handling).
        print(f"Error in simulation thread {strSimulationId}: {objErr}")
        with g_objSimulationLock:
            g_dictRunningSimulations[strSimulationId]['status'] = 'error'
            g_dictRunningSimulations[strSimulationId]['result'] = {'error': str(objErr)}

# end of _executeSimulationInThread


# Runs the dataset parsing and caching in a separate thread.
# This prevents UI freezes during large file I/O operations on JSON files.
def _executeDataLoadingInThread(strLoadId, fltCapacityCm3):
    
    global g_dictRunningDataLoads

    try:
        dictCancellationFlag = g_dictRunningDataLoads[strLoadId]['cancellation_flag']

        # Call data manager to prepare the route.
        dictVehicleInfo, arrPackagesInfo = getDisplayDataForVehicle(fltCapacityCm3, dictCancellationFlag)

        # Securely update the status.
        with g_objDataLoadLock:
            if g_dictRunningDataLoads[strLoadId]['status'] == "cancelling":
                g_dictRunningDataLoads[strLoadId]['status'] = 'cancelled'
            elif not dictVehicleInfo:
                # Set error status if data parsing failed.
                g_dictRunningDataLoads[strLoadId]['status'] = 'error'
                g_dictRunningDataLoads[strLoadId]['result'] = {'error': 'Could not find a valid sample route for the specified capacity.'}
            else:
                # Populate results on success.
                g_dictRunningDataLoads[strLoadId]['status'] = 'completed'
                g_dictRunningDataLoads[strLoadId]['result'] = {
                    'vehicle': dictVehicleInfo,
                    'packages': arrPackagesInfo
                }

    except CancelledException:
        # Handle cancellation request gracefully.
        with g_objDataLoadLock:
            g_dictRunningDataLoads[strLoadId]['status'] = 'cancelled'
            print(f"Data loading job {strLoadId} cancelled successfully.")

    except Exception as objErr:
        # Handle general exceptions.
        with g_objDataLoadLock:
            g_dictRunningDataLoads[strLoadId]['status'] = 'error'
            g_dictRunningDataLoads[strLoadId]['result'] = {'error': str(objErr)}

# end of _executeDataLoadingInThread


# --- WEB SERVER ROUTE DEFINITIONS ---

@g_objFlaskApp.route('/')
# Serves the main HTML interface.
def handleIndexPageRequest():
    
    return render_template('index.html', capacities=[])

# end of handleIndexPageRequest


@g_objFlaskApp.route('/get_all_capacities', methods=['GET'])
# API endpoint to fetch distinct vehicle capacities from the dataset.
def handleGetAllCapacitiesRequest():
    
    try:
        arrCapacities = getAllVehicleCapacities()
        return jsonify({'capacities': arrCapacities})
    except Exception as objErr:
        # Log and return error for debugging.
        print(f"Error in /get_all_capacities: {objErr}")
        return jsonify({'error': str(objErr)}), 500

# end of handleGetAllCapacitiesRequest


@g_objFlaskApp.route('/start_data_loading', methods=['POST'])
# Starts an async job to load dataset info for a selected capacity.
def handleStartDataLoadingRequest():
    
    global g_dictRunningDataLoads

    # Extract parameters from request.
    objData = request.get_json()
    fltCapacityCm3 = float(objData.get('capacity'))
    strLoadId = str(uuid.uuid4())

    dictCancellationFlag = {'is_cancelled': False}
    objThread = Thread(target=_executeDataLoadingInThread, args=(strLoadId, fltCapacityCm3))

    # Register the thread in global state dictionary.
    with g_objDataLoadLock:
        g_dictRunningDataLoads[strLoadId] = {
            'thread': objThread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dictCancellationFlag
        }

    objThread.start()
    return jsonify({'status': 'started', 'load_id': strLoadId})

# end of handleStartDataLoadingRequest


@g_objFlaskApp.route('/data_loading_status/<string:strLoadId>')
# Polls the status of a specific data loading job.
def handleDataLoadingStatusRequest(strLoadId):
    
    with g_objDataLoadLock:
        dictJob = g_dictRunningDataLoads.get(strLoadId)
        if not dictJob:
            return jsonify({'status': 'not_found'}), 404
        
        return jsonify({'status': dictJob['status'], 'result': dictJob['result']})

# end of handleDataLoadingStatusRequest


@g_objFlaskApp.route('/cancel_data_loading/<string:strLoadId>', methods=['POST'])
# Signals a running data load job to terminate via shared flag.
def handleCancelDataLoadingRequest(strLoadId):
    
    with g_objDataLoadLock:
        dictJob = g_dictRunningDataLoads.get(strLoadId)
        
        # Determine if cancellation is valid.
        if dictJob and dictJob['status'] == 'running':
            print(f"Received cancel request for data loading job: {strLoadId}")
            dictJob['cancellation_flag']['is_cancelled'] = True
            dictJob['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        else:
            return jsonify({'status': 'not_found_or_already_complete'}), 404

# end of handleCancelDataLoadingRequest


@g_objFlaskApp.route('/start_simulation', methods=['POST'])
# Initiates a simulation run with specified parameters.
def handleStartSimulationRequest():
    
    global g_dictRunningSimulations

    # Retrieve input parameters.
    objData = request.get_json()
    strAlgorithmName = objData.get('algorithm')
    fltCapacityCm3 = float(objData.get('capacity'))
    blnIsDynamicConstraintEnabled = objData.get('dynamic_constraint_enabled', True)
    strSimulationId = str(uuid.uuid4())

    # Shared mutable state objects for the thread (Inter-thread communication).
    dictProgressTracker = {'current': 0, 'total': 0, 'message': 'Initializing...'}
    dictCancellationFlag = {'is_cancelled': False}

    objThread = Thread(
        target=_executeSimulationInThread,
        args=(strSimulationId, strAlgorithmName, fltCapacityCm3, blnIsDynamicConstraintEnabled)
    )

    # Register job.
    with g_objSimulationLock:
        g_dictRunningSimulations[strSimulationId] = {
            'thread': objThread,
            'status': 'running',
            'result': None,
            'cancellation_flag': dictCancellationFlag,
            'progress': dictProgressTracker
        }

    objThread.start()
    print(f"Started simulation with ID: {strSimulationId}")
    return jsonify({'status': 'started', 'simulation_id': strSimulationId})

# end of handleStartSimulationRequest


@g_objFlaskApp.route('/simulation_status/<string:strSimulationId>')
# Polls for real-time progress of a simulation.
def handleSimulationStatusRequest(strSimulationId):
    
    with g_objSimulationLock:
        dictSim = g_dictRunningSimulations.get(strSimulationId)
        if not dictSim:
            return jsonify({'status': 'not_found'}), 404
        
        return jsonify({
            'status': dictSim['status'],
            'result': dictSim['result'],
            'progress': dictSim.get('progress', {})
        })

# end of handleSimulationStatusRequest


@g_objFlaskApp.route('/cancel_simulation/<string:strSimulationId>', methods=['POST'])
# Signals a simulation thread to stop execution via the shared flag.
def handleCancelSimulationRequest(strSimulationId):
    
    with g_objSimulationLock:
        dictSim = g_dictRunningSimulations.get(strSimulationId)
        
        # Attempt to set the cancel flag.
        if dictSim and dictSim['status'] == 'running':
            print(f"Received cancel request for simulation ID: {strSimulationId}")
            dictSim['cancellation_flag']['is_cancelled'] = True
            dictSim['status'] = 'cancelling'
            return jsonify({'status': 'cancellation_requested'})
        elif dictSim:
            return jsonify({'status': 'already_complete'}), 404
        else:
            return jsonify({'status': 'not_found'}), 404

# end of handleCancelSimulationRequest


# --- Application Entry Point ---
if __name__ == '__main__':
    # Threading is enabled to allow concurrent request handling (polling while processing).
    g_objFlaskApp.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

# end of main block