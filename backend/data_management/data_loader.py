"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Data Management

Purpose of this file:
Implements the 'Sources of Data' and 'Dataset Preparation' sections of the
methodology. It is responsible for loading the 2021 Amazon Last Mile
Routing Research Challenge Dataset, preprocessing it, and caching it
efficiently to provide problem instances for the simulation experiments.

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

# --- Global Constants for File Paths and Cache Directory ---
g_str_baseDir = os.path.dirname(os.path.abspath(__file__))
g_str_routeDataPath = os.path.join(g_str_baseDir, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
g_str_packageDataPath = os.path.join(g_str_baseDir, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# Use smaller sample data for development and demonstration.
# g_str_routeDataPath = os.path.join(g_str_baseDir, '../sample_data/test_route_data.json')
# g_str_packageDataPath = os.path.join(g_str_baseDir, '../sample_data/test_package_data.json')

# Cache directory to store pre-processed data, improving performance on subsequent runs.
g_str_dataCacheDir = os.path.join(g_str_baseDir, '..', 'data_cache')
os.makedirs(g_str_dataCacheDir, exist_ok=True)

def _loadAndReleaseJsonData():
    """
    A private utility function to load large JSON files into memory for
    temporary processing. It ensures data is explicitly released to manage
    memory usage effectively, which is critical for the 'Scalability Trials'.
    """
    print("Loading large JSON files into memory for processing...")
    with open(g_str_routeDataPath, 'r') as f:
        df_routeData = pd.DataFrame.from_dict(json.load(f), orient='index')
    with open(g_str_packageDataPath, 'r') as f:
        dict_packageData = json.load(f)
    print("Finished loading large JSON files.")
    return df_routeData, dict_packageData

def getAllVehicleCapacities():
    """
    Loads route data just long enough to extract all unique vehicle capacities
    and then releases the memory. This populates the UI's selection dropdown.
    """
    df_routeData, _ = _loadAndReleaseJsonData()
    arr_capacities = df_routeData['executor_capacity_cm3'].dropna().unique()

    # Explicitly clear the dataframe from memory and run garbage collection.
    del df_routeData
    gc.collect()

    print("Memory released after fetching capacities.")
    return sorted([float(c) for c in arr_capacities])

def _getOrCreateCapacityCache(flt_vehicleCapacityCm3):
    """
    Manages the creation and retrieval of a 'smart' cache file.
    This avoids re-processing the entire large dataset for every request,
    significantly speeding up the 'Dataset Preparation' stage after the
    first run for a given vehicle capacity.
    """
    str_cacheFilename = f"{flt_vehicleCapacityCm3}.json"
    str_cacheFilepath = os.path.join(g_str_dataCacheDir, str_cacheFilename)

    # Clear old cache files to prevent disk usage bloat.
    for str_filename in os.listdir(g_str_dataCacheDir):
        if (str_filename.endswith('.json') and str_filename != str_cacheFilename):
            os.remove(os.path.join(g_str_dataCacheDir, str_filename))
            print(f"Removed old cache file: {str_filename}")

    # If cache exists, load and return it (fast path).
    if os.path.exists(str_cacheFilepath):
        print(f"Loading from existing smart cache file: {str_cacheFilename}")
        with open(str_cacheFilepath, 'r') as f:
            return json.load(f)

    # If cache does not exist, create it (slow path, runs only once per capacity).
    print(f"Cache not found. Creating new smart cache for capacity: {flt_vehicleCapacityCm3}")
    df_routeDataCache, dict_packageDataCache = _loadAndReleaseJsonData()

    df_matchingRoutes = df_routeDataCache[
        df_routeDataCache['executor_capacity_cm3'] == flt_vehicleCapacityCm3
    ]

    if df_matchingRoutes.empty:
        del df_routeDataCache, dict_packageDataCache
        gc.collect()
        return None

    # Step 1: Process and aggregate all packages for the given capacity.
    arr_allPackagesInfo = []
    arr_routeIds = df_matchingRoutes.index.tolist()
    for str_routeId in arr_routeIds:
        dict_routePackages = dict_packageDataCache.get(str_routeId, {})
        for str_stopId, dict_packagesAtStop in dict_routePackages.items():
            for str_packageId, dict_details in dict_packagesAtStop.items():
                dict_dims = dict_details.get('dimensions', {})
                try:
                    flt_volume = float(dict_dims.get('height_cm', 0)) * \
                                 float(dict_dims.get('width_cm', 0)) * \
                                 float(dict_dims.get('depth_cm', 0))
                    if (flt_volume > 0):
                        arr_allPackagesInfo.append({
                            'id': str_packageId, 'route_id': str_routeId, 'stop_id': str_stopId,
                            'height': float(dict_dims.get('height_cm')),
                            'width': float(dict_dims.get('width_cm')),
                            'depth': float(dict_dims.get('depth_cm')),
                            'volume': flt_volume,
                            'service_time': float(dict_details.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    continue

    # Step 2: Pre-calculate metadata to avoid re-computation.
    flt_dimension = (flt_vehicleCapacityCm3 ** (1./3.))
    dict_metadata = {
        'id': ', '.join(arr_routeIds),
        'capacity_cm3': flt_vehicleCapacityCm3,
        'width': math.floor(flt_dimension), 'height': math.floor(flt_dimension), 'depth': math.floor(flt_dimension),
        'total_package_volume': sum(p['volume'] for p in arr_allPackagesInfo),
        'total_service_time': sum(p['service_time'] for p in arr_allPackagesInfo),
        'num_packages': len(arr_allPackagesInfo),
        'num_vehicles_found': len(arr_routeIds)
    }

    # Step 3: Combine metadata and packages into a single object.
    dict_dataToCache = { 'metadata': dict_metadata, 'packages': arr_allPackagesInfo }

    # Step 4: Save the object to the smart cache file.
    with open(str_cacheFilepath, 'w') as f:
        json.dump(dict_dataToCache, f)
    print(f"Successfully created smart cache: {str_cacheFilename}")

    # Step 5: Critically, release memory after caching is complete.
    del df_routeDataCache, dict_packageDataCache, arr_allPackagesInfo
    gc.collect()
    print("Memory from large JSON files has been successfully released.")

    return dict_dataToCache

def loadDataForVehicle(flt_vehicleCapacityCm3, int_page=1, int_pageSize=100):
    """
    The main public function to load paginated data for a given vehicle capacity.
    It relies on the caching mechanism to ensure fast and memory-efficient data retrieval.
    """
    dict_cachedData = _getOrCreateCapacityCache(flt_vehicleCapacityCm3)

    if not dict_cachedData:
        return None, []

    dict_metadata = dict_cachedData['metadata']
    arr_allPackagesInfo = dict_cachedData['packages']

    # Paginate the results from the full cached list.
    int_totalPackages = dict_metadata['num_packages']
    int_totalPages = math.ceil(int_totalPackages / int_pageSize) if int_pageSize > 0 else 1
    int_startIndex = (int_page - 1) * int_pageSize
    int_endIndex = int_startIndex + int_pageSize
    arr_paginatedPackages = arr_allPackagesInfo[int_startIndex:int_endIndex]

    # Construct the final vehicle info dictionary, adding pagination details.
    dict_aggregateVehicleInfo = {
        **dict_metadata,
        'pagination_meta': {
            'current_page': int_page,
            'page_size': int_pageSize,
            'total_pages': int_totalPages,
            'total_items': int_totalPackages
        }
    }

    return dict_aggregateVehicleInfo, arr_paginatedPackages

def getVehicleInfoOnly(flt_vehicleCapacityCm3):
    """
    A utility to quickly fetch only the metadata for a vehicle,
    leveraging the smart cache.
    """
    dict_cachedData = _getOrCreateCapacityCache(flt_vehicleCapacityCm3)
    if not dict_cachedData:
        return None

    # Return only the 'metadata' portion of the cache.
    return dict_cachedData['metadata']