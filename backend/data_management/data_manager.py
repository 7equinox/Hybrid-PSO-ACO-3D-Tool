"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Data Management

Purpose of this file:
This module is the direct implementation of the 'Sources of Data' and 'Dataset
Preparation' stages outlined in the research methodology. It is singularly
responsible for all interactions with the raw 2021 Amazon Last Mile Routing
Research Challenge Dataset. Its primary functions are to:
1. Load the massive, complex JSON source files.
2. Preprocess and sanitize the data to create clean, usable problem instances.
3. Implement an intelligent caching strategy to dramatically speed up subsequent
   data loads, which is critical for making the research tool practical for
   repeated experiments.
This module provides the foundational, reliable data upon which all experiments
and simulations are built.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
import json     # For reading and writing JSON files (the format of our dataset).
import os       # For interacting with the file system (e.g., finding paths, creating directories).
import pandas as pd # A powerful library for handling large, structured datasets efficiently.
import math     # For mathematical operations, like calculating cube roots for dimensions.
import gc       # Python's "Garbage Collector" interface, used here to manually free up memory.
from backend.simulation.custom_exceptions import CancelledException # Our custom exception for graceful cancellation.


# --- GLOBAL CONSTANTS ---
# Define the file paths for the dataset. Using global constants makes the code
# cleaner and easier to update if the file locations ever change.
g_str_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# These paths point to the large, official dataset files as specified in the 'Sources of Data'.
g_str_ROUTE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
g_str_PACKAGE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# The cache is a "smart storage" folder. We will store pre-processed data here
# to avoid re-reading the massive source files every time the application is used.
# This is a critical performance optimization.
g_str_DATA_CACHE_DIR = os.path.join(g_str_BASE_DIR, '../', 'data_cache')
os.makedirs(g_str_DATA_CACHE_DIR, exist_ok=True) # Create the directory if it doesn't exist.

# A default object for the cancellation flag. This allows functions to be called
# in different contexts without always needing to pass a flag.
DEFAULT_CANCEL_FLAG = {'is_cancelled': False}


def _fnLoadSourceDataset(dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Loads the large raw JSON files from the Amazon dataset into memory using the pandas library.
    Because this is a very time-consuming operation (it can take several seconds), it
    is designed to be interruptible. The function checks the cancellation flag before
    and between reading the large files, allowing the user to abort the process.

    Args:
        dictCancellationFlag (dict): The shared flag that signals when to stop.

    Returns:
        tuple: A pandas DataFrame with route data and a dictionary with package data.
    """
    # Check for a cancellation signal before starting the slow file-reading process.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    print("Loading large route JSON file into memory...")
    # Open and parse the route data file.
    with open(g_str_ROUTE_DATA_PATH, 'r') as f:
        # Using pandas is much more memory-efficient than loading the whole JSON object at once.
        obj_dfRouteData = pd.DataFrame.from_dict(json.load(f), orient='index')

    # Check for cancellation again before reading the second large file.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    print("Loading large package JSON file into memory...")
    # Open and parse the package data file.
    with open(g_str_PACKAGE_DATA_PATH, 'r') as f:
        dict_packageData = json.load(f)

    print("Finished loading large JSON files.")
    return obj_dfRouteData, dict_packageData


def fnGetAllVehicleCapacities():
    """
    Efficiently extracts all unique vehicle capacity values from the entire dataset.
    This function is optimized for speed and memory conservation. It loads the large
    route data, pulls out ONLY the 'executor_capacity_cm3' column, finds the unique
    values, and then immediately releases the massive dataframe from memory to keep
    the application's memory footprint as small as possible. This populates the
    dropdown menu in the user interface.
    """
    # Load the source dataset.
    obj_dfRouteData, _ = _fnLoadSourceDataset()
    # Extract the unique, non-null capacity values.
    arr_capacities = obj_dfRouteData['executor_capacity_cm3'].dropna().unique()

    # --- PERFORMANCE OPTIMIZATION ---
    # The following memory management lines have been commented out.
    # This keeps the large dataframe in memory longer, avoiding the overhead of
    # garbage collection, which is part of the strategy to trade memory for speed.
    #
    # del obj_dfRouteData
    # gc.collect()

    print("Memory NOT explicitly released after fetching capacities.")
    # Return a sorted list of the capacities.
    return sorted([float(c) for c in arr_capacities])


def _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    This function is the core of the 'Dataset Preparation' stage. It manages a cache
    of pre-processed data for each specific vehicle capacity. The first time a user
    selects a vehicle, this function will perform the slow task of filtering and
    structuring all relevant data from the source files and save the result to a
    new, smaller JSON file in the 'data_cache' directory. On all subsequent requests
    for the same capacity, it will simply read that small, clean cache file directly,
    making the process nearly instantaneous.

    Args:
        fltVehicleCapacityCm3 (float): The vehicle capacity to get data for.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        dict: A dictionary containing the processed metadata and package list for the capacity.
    """
    # Check for cancellation at the start.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    # Define the name of the cache file based on the capacity.
    str_cacheFilename = f"{fltVehicleCapacityCm3}.json"
    str_cacheFilepath = os.path.join(g_str_DATA_CACHE_DIR, str_cacheFilename)

    # --- THE FAST PATH ---
    # If a pre-processed cache file already exists, we load it and return the data immediately.
    if os.path.exists(str_cacheFilepath):
        print(f"Loading from existing smart cache file: {str_cacheFilename}")
        with open(str_cacheFilepath, 'r') as f:
            return json.load(f)

    # --- THE SLOW PATH (only runs once per capacity) ---
    if dictCancellationFlag['is_cancelled']: raise CancelledException()
    print(f"Cache not found. Creating new smart cache for capacity: {fltVehicleCapacityCm3}")
    obj_dfRouteDataCache, dict_packageDataCache = _fnLoadSourceDataset(dictCancellationFlag)

    # Filter the massive route dataframe to find only the routes that match the selected capacity.
    obj_dfMatchingRoutes = obj_dfRouteDataCache[
        obj_dfRouteDataCache['executor_capacity_cm3'] == fltVehicleCapacityCm3
    ]

    # If no routes are found for this capacity, we stop and release memory.
    if obj_dfMatchingRoutes.empty:
        del obj_dfRouteDataCache, dict_packageDataCache
        gc.collect()
        return None

    # This loop is the main data aggregation step. It iterates through every package
    # on every matching route, cleaning and restructuring the data into a simple, flat
    # list of package objects that is easy for our simulation module to work with.
    arr_allPackagesInfo = []
    arr_routeIds = obj_dfMatchingRoutes.index.tolist()

    # A cancellation check is placed inside this expensive loop to ensure the process remains responsive.
    for i, str_routeId in enumerate(arr_routeIds):
        if i % 50 == 0 and dictCancellationFlag['is_cancelled']:
             raise CancelledException() # Check every 50 routes.

        dict_routePackages = dict_packageDataCache.get(str_routeId, {})
        for str_stopId, dict_packagesAtStop in dict_routePackages.items():
            for str_packageId, dict_details in dict_packagesAtStop.items():
                dict_dims = dict_details.get('dimensions', {})
                try:
                    flt_h = float(dict_dims.get('height_cm', 0))
                    flt_w = float(dict_dims.get('width_cm', 0))
                    flt_d = float(dict_dims.get('depth_cm', 0))

                    # --- CRITICAL DATA SANITIZATION ---
                    # This is a key step for ensuring the integrity of our experiment. The raw
                    # dataset may contain invalid entries (e.g., items with zero height).
                    # We explicitly filter these out to prevent them from causing errors or
                    # producing nonsensical results in the simulation. We only accept items
                    # that have valid, three-dimensional volume.
                    if (flt_h > 0 and flt_w > 0 and flt_d > 0):
                        flt_volume = flt_h * flt_w * flt_d
                        arr_allPackagesInfo.append({
                            'id': str_packageId, 'route_id': str_routeId, 'stop_id': str_stopId,
                            'height': flt_h, 'width': flt_w, 'depth': flt_d, 'volume': flt_volume,
                            'service_time': float(dict_details.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    # If any data is malformed (e.g., not a number), we simply ignore that package.
                    continue

    # Create a metadata summary about the aggregated dataset.
    flt_dimension = (fltVehicleCapacityCm3 ** (1./3.))
    dict_metadata = {
        'id': ', '.join(arr_routeIds), 'capacity_cm3': fltVehicleCapacityCm3,
        'width': math.floor(flt_dimension), 'height': math.floor(flt_dimension), 'depth': math.floor(flt_dimension),
        'total_package_volume': sum(p['volume'] for p in arr_allPackagesInfo),
        'total_service_time': sum(p['service_time'] for p in arr_allPackagesInfo),
        'num_packages': len(arr_allPackagesInfo),
        'num_vehicles_found': len(arr_routeIds)
    }

    # Combine the metadata and the package list into a single object for caching.
    dict_dataToCache = { 'metadata': dict_metadata, 'packages': arr_allPackagesInfo }

    # Write the newly processed, clean data to a JSON file in the cache directory.
    with open(str_cacheFilepath, 'w') as f:
        json.dump(dict_dataToCache, f)
    print(f"Successfully created smart cache: {str_cacheFilename}")

    # --- PERFORMANCE OPTIMIZATION ---
    # The following memory management lines have been commented out to keep the
    # large source dataframes in memory. This uses more RAM but avoids the
    # performance cost of deleting large objects and running the garbage collector.
    #
    # del obj_dfRouteDataCache, dict_packageDataCache, arr_allPackagesInfo
    # gc.collect()
    print("Memory from large JSON files has NOT been successfully released.")

    return dict_dataToCache


def fnGetDisplayDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Finds a single, representative sample route for a given capacity. This sample
    is used to populate the information panels on the user interface before a
    simulation is run. To be considered a valid sample, the total volume of its
    assigned packages must not exceed the vehicle's capacity. This provides the
    user with a realistic, loadable problem instance to view.

    Args:
        fltVehicleCapacityCm3 (float): The target vehicle capacity.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        tuple: A dictionary with the single vehicle's info, and a list of its packages.
    """
    print(f"Searching for a single valid display route for capacity: {fltVehicleCapacityCm3}")
    # This function cleverly leverages the cache to avoid re-processing the entire dataset.
    dict_fullData = _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)
    if not dict_fullData:
        return None, []

    arr_allPackages = dict_fullData.get('packages', [])
    set_processedRoutes = set()

    # Iterate through all packages, grouped by their route ID.
    for i, obj_pkg in enumerate(arr_allPackages):
        if i % 100 == 0 and dictCancellationFlag['is_cancelled']:
            raise CancelledException()

        str_routeId = obj_pkg['route_id']
        # Skip this route if we've already checked it.
        if str_routeId in set_processedRoutes: continue

        # Filter the full package list to get all packages for this one specific route.
        arr_packagesForThisRoute = [p for p in arr_allPackages if p['route_id'] == str_routeId]
        flt_totalVolume = sum(p['volume'] for p in arr_packagesForThisRoute)

        # Check if the total volume of packages fits within the vehicle's capacity.
        if flt_totalVolume < fltVehicleCapacityCm3:
            print(f"Found valid display route: {str_routeId}")
            # If it fits, we've found our sample. Construct the metadata object for this single route.
            flt_dimension = (fltVehicleCapacityCm3 ** (1./3.))
            dict_vehicleInfo = {
                'id': str_routeId, 'capacity_cm3': fltVehicleCapacityCm3,
                'width': math.floor(flt_dimension), 'height': math.floor(flt_dimension), 'depth': math.floor(flt_dimension),
                'total_package_volume': flt_totalVolume,
                'total_service_time': sum(p['service_time'] for p in arr_packagesForThisRoute),
                'num_packages': len(arr_packagesForThisRoute),
            }
            # Return the vehicle info and just the packages for this one route.
            return dict_vehicleInfo, arr_packagesForThisRoute

        set_processedRoutes.add(str_routeId)

    # If no single, loadable route is found (which is very unlikely), return an empty result.
    return None, []


def fnGetSimulationDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Retrieves the complete, aggregated dataset for a given vehicle capacity from the cache.
    This provides ALL packages from ALL routes associated with that capacity. This is the
    full dataset that will be passed to the simulation orchestrator. The orchestrator will
    then apply a sampling method to this large dataset to create a manageable problem
    instance for the actual experiment.

    Args:
        fltVehicleCapacityCm3 (float): The target vehicle capacity.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        tuple: The vehicle metadata and the complete, aggregated list of all packages.
    """
    print(f"Loading full aggregate dataset for capacity: {fltVehicleCapacityCm3}")
    dict_cachedData = _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)

    if not dict_cachedData: return None, []
    
    # Return both the vehicle metadata and the full list of packages.
    return dict_cachedData['metadata'], dict_cachedData['packages']