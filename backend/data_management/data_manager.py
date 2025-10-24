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

    # This is a critical memory management step. After we have the information we need,
    # we explicitly delete the large object and ask the garbage collector to reclaim the memory.
    del obj_dfRouteData
    gc.collect()

    print("Memory released after fetching capacities.")
    # Return a sorted list of the capacities.
    return sorted([float(c) for c in arr_capacities])


def _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    This function is the core of the 'Dataset Preparation' stage. It now finds the FIRST
    valid, loadable route for a given capacity and caches ONLY that route's data.
    This ensures that the data used for display is the exact same data used for the simulation,
    fulfilling the core requirement of the revised methodology.

    Args:
        fltVehicleCapacityCm3 (float): The vehicle capacity to get data for.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        dict: A dictionary containing the processed metadata and package list for a single route.
    """
    # Check for cancellation at the start.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    # Define the name of the cache file based on the capacity.
    str_cacheFilename = f"route_{fltVehicleCapacityCm3}.json" # Use a new naming scheme to avoid old cache conflicts.
    str_cacheFilepath = os.path.join(g_str_DATA_CACHE_DIR, str_cacheFilename)

    # --- THE FAST PATH ---
    # If a pre-processed cache file already exists, we load it and return the data immediately.
    if os.path.exists(str_cacheFilepath):
        print(f"Loading from existing single-route cache file: {str_cacheFilename}")
        with open(str_cacheFilepath, 'r') as f:
            return json.load(f)

    # --- THE SLOW PATH (only runs once per capacity) ---
    if dictCancellationFlag['is_cancelled']: raise CancelledException()
    print(f"Cache not found. Searching for a single valid route for capacity: {fltVehicleCapacityCm3}")
    obj_dfRouteDataCache, dict_packageDataCache = _fnLoadSourceDataset(dictCancellationFlag)

    # Filter the massive route dataframe to find all possible routes that match the selected capacity.
    obj_dfMatchingRoutes = obj_dfRouteDataCache[
        obj_dfRouteDataCache['executor_capacity_cm3'] == fltVehicleCapacityCm3
    ]

    # If no routes are found for this capacity, we stop and release memory.
    if obj_dfMatchingRoutes.empty:
        del obj_dfRouteDataCache, dict_packageDataCache
        gc.collect()
        return None
    
    arr_routeIds = obj_dfMatchingRoutes.index.tolist()
    
    # Iterate through every possible route ID for this capacity until we find one that is valid.
    for i, str_routeId in enumerate(arr_routeIds):
        if i % 50 == 0 and dictCancellationFlag['is_cancelled']:
             raise CancelledException()

        # Gather all the package information for this specific route.
        dict_routePackages = dict_packageDataCache.get(str_routeId, {})
        arr_packagesForThisRoute = []
        for str_stopId, dict_packagesAtStop in dict_routePackages.items():
            for str_packageId, dict_details in dict_packagesAtStop.items():
                dict_dims = dict_details.get('dimensions', {})
                try:
                    flt_h = float(dict_dims.get('height_cm', 0))
                    flt_w = float(dict_dims.get('width_cm', 0))
                    flt_d = float(dict_dims.get('depth_cm', 0))
                    if (flt_h > 0 and flt_w > 0 and flt_d > 0):
                        flt_volume = flt_h * flt_w * flt_d
                        arr_packagesForThisRoute.append({
                            'id': str_packageId, 'route_id': str_routeId, 'stop_id': str_stopId,
                            'height': flt_h, 'width': flt_w, 'depth': flt_d, 'volume': flt_volume,
                            'service_time': float(dict_details.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    continue

        flt_totalVolume = sum(p['volume'] for p in arr_packagesForThisRoute)
        
        # --- THE VALIDATION CRITERION ---
        # A route is considered a valid sample if its total package volume is less than the vehicle capacity.
        if flt_totalVolume < fltVehicleCapacityCm3:
            print(f"Found and caching valid display route: {str_routeId}")

            # Construct the metadata object specifically for THIS SINGLE ROUTE.
            flt_dimension = (fltVehicleCapacityCm3 ** (1./3.))
            dict_metadata = {
                'id': str_routeId, 'capacity_cm3': fltVehicleCapacityCm3,
                'width': math.floor(flt_dimension), 'height': math.floor(flt_dimension), 'depth': math.floor(flt_dimension),
                'total_package_volume': flt_totalVolume,
                'total_service_time': sum(p['service_time'] for p in arr_packagesForThisRoute),
                'num_packages': len(arr_packagesForThisRoute),
            }

            # Combine the metadata and this route's packages into a single object for caching.
            dict_dataToCache = { 'metadata': dict_metadata, 'packages': arr_packagesForThisRoute }
            
            # Write this single-route data to a JSON file in the cache directory.
            with open(str_cacheFilepath, 'w') as f:
                json.dump(dict_dataToCache, f)
            print(f"Successfully created single-route cache: {str_cacheFilename}")
            
            # Clean up the large source dataframes from memory.
            del obj_dfRouteDataCache, dict_packageDataCache
            gc.collect()

            # IMPORTANT: Return the data immediately after finding the first valid route.
            return dict_dataToCache
            
    # If the loop finishes and no single, loadable route was found, return None.
    # Clean up memory before returning.
    del obj_dfRouteDataCache, dict_packageDataCache
    gc.collect()
    return None


def fnGetDisplayDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Retrieves the single, representative sample route for a given capacity from the cache.
    This function is used to populate the information panels on the user interface before a
    simulation is run.

    Args:
        fltVehicleCapacityCm3 (float): The target vehicle capacity.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        tuple: A dictionary with the single vehicle's info, and a list of its packages.
    """
    print(f"Loading display data for capacity: {fltVehicleCapacityCm3}")
    dict_cachedData = _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)
    
    if not dict_cachedData:
        return None, []
    
    return dict_cachedData['metadata'], dict_cachedData['packages']


def fnGetSimulationDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Retrieves the single, representative sample route for a given capacity from the cache.
    This provides the EXACT same problem instance as fnGetDisplayDataForVehicle, ensuring
    that the simulation runs on the same data the user sees.

    Args:
        fltVehicleCapacityCm3 (float): The target vehicle capacity.
        dictCancellationFlag (dict): The shared cancellation flag.

    Returns:
        tuple: The vehicle metadata and the list of packages for the single cached route.
    """
    print(f"Loading simulation data for capacity: {fltVehicleCapacityCm3}")
    # This function now behaves identically to fnGetDisplayDataForVehicle.
    dict_cachedData = _fnGetOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)

    if not dict_cachedData: 
        return None, []
    
    return dict_cachedData['metadata'], dict_cachedData['packages']