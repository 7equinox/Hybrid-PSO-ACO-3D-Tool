"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Data Management

Purpose of this file:
Implements the 'Sources of Data' and 'Dataset Preparation' sections of the
methodology. It is responsible for loading the 2021 Amazon Last Mile
Routing Research Challenge Dataset, performing the necessary preprocessing to
structure the data, and implementing a caching strategy to efficiently
provide problem instances for the simulation experiments. This module is the
foundation for the entire experimental process.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import json
import os
import pandas as pd
import math
import gc
# Import the custom exception for handling user-initiated cancellations during long operations.
from backend.simulation.custom_exceptions import CancelledException

# --- Global Constants for File Paths and Cache Directory ---
# These constants define the location of the raw dataset files as specified in the 'Sources of Data'.
g_str_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
g_str_ROUTE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
g_str_PACKAGE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# Use smaller sample data for development and demonstration.
# g_str_ROUTE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../sample_data/test_route_data.json')
# g_str_PACKAGE_DATA_PATH = os.path.join(g_str_BASE_DIR, '../sample_data/test_package_data.json')

# The cache directory stores pre-processed data. This is a critical optimization
# to avoid re-reading and re-processing the massive source JSON files on every run.
g_str_DATA_CACHE_DIR = os.path.join(g_str_BASE_DIR, '../', 'data_cache')
os.makedirs(g_str_DATA_CACHE_DIR, exist_ok=True)

# A default cancellation flag object is provided for functions that might be called without one.
DEFAULT_CANCEL_FLAG = {'is_cancelled': False}


def _loadSourceDataset(dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Loads the large raw JSON files from the Amazon dataset into memory using pandas.
    Because this is an I/O-intensive and time-consuming operation, it includes
    pre-emptive checks for the cancellation flag, allowing the user to interrupt the process.
    """
    # Check for cancellation before attempting to read the first large file.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()
    print("Loading large route JSON file into memory...")
    with open(g_str_ROUTE_DATA_PATH, 'r') as f:
        obj_dfRouteData = pd.DataFrame.from_dict(json.load(f), orient='index')

    # Check for cancellation again before the second large file read.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()
    print("Loading large package JSON file into memory...")
    with open(g_str_PACKAGE_DATA_PATH, 'r') as f:
        dict_packageData = json.load(f)

    print("Finished loading large JSON files.")
    return obj_dfRouteData, dict_packageData


def fn_getAllVehicleCapacities():
    """
    Efficiently extracts all unique vehicle capacities from the dataset.
    This function is designed for speed and memory conservation; it loads the
    large route data, extracts only the required capacity values, and then
    immediately releases the data from memory to keep the application's footprint low.
    """
    obj_dfRouteData, _ = _loadSourceDataset()
    arr_capacities = obj_dfRouteData['executor_capacity_cm3'].dropna().unique()

    # Explicitly clear the large dataframe and trigger Python's garbage collector.
    # This is essential for managing the memory impact of the large dataset.
    del obj_dfRouteData
    gc.collect()

    print("Memory released after fetching capacities.")
    return sorted([float(c) for c in arr_capacities])


def _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Manages the creation and retrieval of a cache file for a specific vehicle capacity.
    This function is the core of the 'Dataset Preparation' stage. It avoids the
    need to re-process the entire multi-gigabyte dataset on every request,
    significantly improving performance after the first run for any given capacity.
    """
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    str_cacheFilename = f"{fltVehicleCapacityCm3}.json"
    str_cacheFilepath = os.path.join(g_str_DATA_CACHE_DIR, str_cacheFilename)

    # If a pre-processed cache file already exists, load and return it directly. This is the fast path.
    if os.path.exists(str_cacheFilepath):
        if dictCancellationFlag['is_cancelled']: raise CancelledException()
        print(f"Loading from existing smart cache file: {str_cacheFilename}")
        with open(str_cacheFilepath, 'r') as f:
            return json.load(f)

    # If the cache does not exist, the slow path is taken: load the source data and process it.
    if dictCancellationFlag['is_cancelled']: raise CancelledException()
    print(f"Cache not found. Creating new smart cache for capacity: {fltVehicleCapacityCm3}")
    obj_dfRouteDataCache, dict_packageDataCache = _loadSourceDataset(dictCancellationFlag)

    # Filter the routes to find all those that match the selected capacity.
    obj_dfMatchingRoutes = obj_dfRouteDataCache[
        obj_dfRouteDataCache['executor_capacity_cm3'] == fltVehicleCapacityCm3
    ]

    if obj_dfMatchingRoutes.empty:
        # Release memory and return if no routes are found.
        del obj_dfRouteDataCache, dict_packageDataCache
        gc.collect()
        return None

    # This loop performs the main data aggregation. It iterates through all matching
    # routes and their packages, restructuring the data into a clean, flat list of package
    # objects that can be easily used by the simulation module.
    arr_allPackagesInfo = []
    arr_routeIds = obj_dfMatchingRoutes.index.tolist()
    # A cancellation check is placed inside the most expensive loop for responsiveness.
    for i, str_routeId in enumerate(arr_routeIds):
        if i % 50 == 0 and dictCancellationFlag['is_cancelled']:
             raise CancelledException()
        dict_routePackages = dict_packageDataCache.get(str_routeId, {})
        for str_stopId, dict_packagesAtStop in dict_routePackages.items():
            for str_packageId, dict_details in dict_packagesAtStop.items():
                dict_dims = dict_details.get('dimensions', {})
                try:
                    # Calculate volume and ensure dimensions are valid.
                    flt_volume = float(dict_dims.get('height_cm', 0)) * \
                                 float(dict_dims.get('width_cm', 0)) * \
                                 float(dict_dims.get('depth_cm', 0))
                    if (flt_volume > 0): # Only include items with valid, non-zero volume.
                        arr_allPackagesInfo.append({
                            'id': str_packageId, 'route_id': str_routeId, 'stop_id': str_stopId,
                            'height': float(dict_dims.get('height_cm')),
                            'width': float(dict_dims.get('width_cm')),
                            'depth': float(dict_dims.get('depth_cm')),
                            'volume': flt_volume,
                            'service_time': float(dict_details.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    # Ignore packages with malformed data.
                    continue

    # Create metadata about the aggregated dataset for the selected capacity.
    flt_dimension = (fltVehicleCapacityCm3 ** (1./3.))
    dict_metadata = {
        'id': ', '.join(arr_routeIds),
        'capacity_cm3': fltVehicleCapacityCm3,
        'width': math.floor(flt_dimension), 'height': math.floor(flt_dimension), 'depth': math.floor(flt_dimension),
        'total_package_volume': sum(p['volume'] for p in arr_allPackagesInfo),
        'total_service_time': sum(p['service_time'] for p in arr_allPackagesInfo),
        'num_packages': len(arr_allPackagesInfo),
        'num_vehicles_found': len(arr_routeIds)
    }

    # Combine the metadata and the package list into a single object to be cached.
    dict_dataToCache = { 'metadata': dict_metadata, 'packages': arr_allPackagesInfo }

    # Write the processed data to a JSON file in the cache directory.
    with open(str_cacheFilepath, 'w') as f:
        json.dump(dict_dataToCache, f)
    print(f"Successfully created smart cache: {str_cacheFilename}")

    # After caching is complete, it is critical to release the memory consumed
    # by the large dataframes to keep the application lean.
    del obj_dfRouteDataCache, dict_packageDataCache, arr_allPackagesInfo
    gc.collect()
    print("Memory from large JSON files has been successfully released.")

    return dict_dataToCache


def fn_getDisplayDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Finds a single, valid sample route for a given capacity to display in the UI.
    A route is considered "valid" if the total volume of its assigned packages does
    not exceed the vehicle's capacity. This provides the user with a realistic,
    loadable problem instance to view before running a simulation.
    """
    print(f"Searching for a single valid display route for capacity: {fltVehicleCapacityCm3}")
    # This function leverages the cache to avoid re-processing the entire dataset.
    dict_fullData = _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)
    if not dict_fullData:
        return None, []

    arr_allPackages = dict_fullData.get('packages', [])
    set_processedRoutes = set()

    for i, obj_pkg in enumerate(arr_allPackages):
        if i % 100 == 0 and dictCancellationFlag['is_cancelled']:
            raise CancelledException()

        str_routeId = obj_pkg['route_id']
        if str_routeId in set_processedRoutes: continue

        # Filter to get all packages for this specific route and check the volume constraint.
        arr_packagesForThisRoute = [p for p in arr_allPackages if p['route_id'] == str_routeId]
        flt_totalVolume = sum(p['volume'] for p in arr_packagesForThisRoute)

        if flt_totalVolume < fltVehicleCapacityCm3:
            print(f"Found valid display route: {str_routeId}")
            # Construct a specific metadata object for just this single route.
            flt_dimension = (fltVehicleCapacityCm3 ** (1./3.))
            dict_vehicleInfo = {
                'id': str_routeId, # Use only this route's ID.
                'capacity_cm3': fltVehicleCapacityCm3,
                'width': math.floor(flt_dimension),
                'height': math.floor(flt_dimension),
                'depth': math.floor(flt_dimension),
                'total_package_volume': flt_totalVolume,
                'total_service_time': sum(p['service_time'] for p in arr_packagesForThisRoute),
                'num_packages': len(arr_packagesForThisRoute),
            }
            return dict_vehicleInfo, arr_packagesForThisRoute

        set_processedRoutes.add(str_routeId)

    # If no single loadable route is found (unlikely), return an empty result.
    return None, []


def fn_getSimulationDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    """
    Retrieves the full, aggregated dataset for a given vehicle capacity from the cache.
    This provides all packages from all routes associated with that capacity. This is
    the complete dataset that will be passed to the simulation orchestrator, which
    will then apply the 'Sampling Method' from the methodology.
    """
    print(f"Loading full aggregate dataset for capacity: {fltVehicleCapacityCm3}")
    dict_cachedData = _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)

    if not dict_cachedData: return None, []
    # Return both the vehicle metadata and the complete list of packages.
    return dict_cachedData['metadata'], dict_cachedData['packages']