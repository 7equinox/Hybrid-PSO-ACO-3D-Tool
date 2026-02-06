"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Data Management

Purpose of this file:
This module handles all interactions with the raw 2021 Amazon Last Mile Routing
Research Challenge Dataset. It implements loading, preprocessing, and caching of
large JSON files to create valid problem instances for simulation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

# --- Import necessary libraries ---
import json
import os
import pandas as pd
import math
import gc
from backend.simulation.custom_exceptions import CancelledException


# --- GLOBAL CONSTANTS ---
G_STR_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Constants describing path locations to strict dataset inputs
G_STR_ROUTE_DATA_PATH = os.path.join(G_STR_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
G_STR_PACKAGE_DATA_PATH = os.path.join(G_STR_BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')
G_STR_DATA_CACHE_DIR = os.path.join(G_STR_BASE_DIR, '../', 'data_cache')

# Ensure cache directory exists at runtime
os.makedirs(G_STR_DATA_CACHE_DIR, exist_ok=True)

# Default flag for optional arguments to allow safe interruptions
DEFAULT_CANCEL_FLAG = {'is_cancelled': False}


# Loads raw JSON files into memory. 
# Checks cancellation flag between heavy I/O operations to prevent hanging.
# Returns: tuple (objRouteDataFrame, dictPackageData)
def _loadSourceDataset(dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    
    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    print("Loading large route JSON file into memory...")
    
    with open(G_STR_ROUTE_DATA_PATH, 'r') as fileObject:
        objRouteDataFrame = pd.DataFrame.from_dict(json.load(fileObject), orient='index')

    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    print("Loading large package JSON file into memory...")
    
    with open(G_STR_PACKAGE_DATA_PATH, 'r') as fileObject:
        dictPackageData = json.load(fileObject)

    print("Finished loading large JSON files.")
    return objRouteDataFrame, dictPackageData

# end of _loadSourceDataset


# Extracts all unique vehicle capacity values from the dataset to populate UI.
# This function is Optimized for memory management by manually invoking garbage collection.
def getAllVehicleCapacities():
    
    objRouteDataFrame, _ = _loadSourceDataset()
    
    # Extract unique values and drop nulls from dataframe column.
    arrCapacities = objRouteDataFrame['executor_capacity_cm3'].dropna().unique()

    # Manual memory cleanup.
    del objRouteDataFrame
    gc.collect()

    print("Memory released after fetching capacities.")
    
    # Return sorted float list.
    return sorted([float(c) for c in arrCapacities])

# end of getAllVehicleCapacities


# Finds or creates a cached route file for the specific capacity.
# Searches for the first valid route if no cache exists in the 'data_cache' folder.
def _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    
    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    strCacheFilename = f"route_{fltVehicleCapacityCm3}.json"
    strCacheFilepath = os.path.join(G_STR_DATA_CACHE_DIR, strCacheFilename)

    # --- THE FAST PATH: Load existing cache ---
    if os.path.exists(strCacheFilepath):
        print(f"Loading from existing single-route cache file: {strCacheFilename}")
        with open(strCacheFilepath, 'r') as fileObject:
            return json.load(fileObject)

    # --- THE SLOW PATH: Generate cache ---
    # This block executes only if cache is missing.
    if dictCancellationFlag['is_cancelled']:
        raise CancelledException()

    print(f"Cache not found. Searching for a single valid route for capacity: {fltVehicleCapacityCm3}")
    
    objRouteDataFrameCache, dictPackageDataCache = _loadSourceDataset(dictCancellationFlag)

    # Filter routes matching the target capacity.
    objMatchingRoutes = objRouteDataFrameCache[
        objRouteDataFrameCache['executor_capacity_cm3'] == fltVehicleCapacityCm3
    ]

    # Handle case where no routes match.
    if objMatchingRoutes.empty:
        del objRouteDataFrameCache, dictPackageDataCache
        gc.collect()
        return None
    
    arrRouteIds = objMatchingRoutes.index.tolist()
    
    # Iterate through potential routes to find one with valid packages.
    for intIndex, strRouteId in enumerate(arrRouteIds):
        # Check cancellation periodically.
        if intIndex % 50 == 0 and dictCancellationFlag['is_cancelled']:
             raise CancelledException()

        dictRoutePackages = dictPackageDataCache.get(strRouteId, {})
        arrPackagesForThisRoute = []
        
        # Flatten structure and validate dimensions.
        for strStopId, dictPackagesAtStop in dictRoutePackages.items():
            for strPackageId, dictDetails in dictPackagesAtStop.items():
                dictDims = dictDetails.get('dimensions', {})
                try:
                    fltHeight = float(dictDims.get('height_cm', 0)) or 1.0
                    fltWidth = float(dictDims.get('width_cm', 0)) or 1.0
                    fltDepth = float(dictDims.get('depth_cm', 0)) or 1.0
                    
                    if (fltHeight > 0 and fltWidth > 0 and fltDepth > 0):
                        fltVolume = fltHeight * fltWidth * fltDepth
                        arrPackagesForThisRoute.append({
                            'id': strPackageId, 
                            'route_id': strRouteId, 
                            'stop_id': strStopId,
                            'height': fltHeight, 
                            'width': fltWidth, 
                            'depth': fltDepth, 
                            'volume': fltVolume,
                            'service_time': float(dictDetails.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    continue

        fltTotalVolume = sum(p['volume'] for p in arrPackagesForThisRoute)
        
        # Validation Criterion: Must have packages and fit in truck (Valid Constraints).
        if 0 < fltTotalVolume < fltVehicleCapacityCm3:
            print(f"Found and caching valid display route: {strRouteId}")

            fltDimension = (fltVehicleCapacityCm3 ** (1. / 3.))
            dictMetadata = {
                'id': strRouteId, 
                'capacity_cm3': fltVehicleCapacityCm3,
                'width': math.floor(fltDimension), 
                'height': math.floor(fltDimension), 
                'depth': math.floor(fltDimension),
                'total_package_volume': fltTotalVolume,
                'total_service_time': sum(p['service_time'] for p in arrPackagesForThisRoute),
                'num_packages': len(arrPackagesForThisRoute),
            }

            dictDataToCache = {
                'metadata': dictMetadata, 
                'packages': arrPackagesForThisRoute 
            }
            
            with open(strCacheFilepath, 'w') as fileObject:
                json.dump(dictDataToCache, fileObject)
                
            print(f"Successfully created single-route cache: {strCacheFilename}")
            
            del objRouteDataFrameCache, dictPackageDataCache
            gc.collect()
            return dictDataToCache
            
    # Cleanup if no route found.
    del objRouteDataFrameCache, dictPackageDataCache
    gc.collect()
    return None

# end of _getOrCreateCapacityCache


# Public interface to retrieve cached data for display in the UI.
def getDisplayDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    
    print(f"Loading display data for capacity: {fltVehicleCapacityCm3}")
    
    dictCachedData = _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)
    
    if not dictCachedData:
        return None, []
    
    return dictCachedData['metadata'], dictCachedData['packages']

# end of getDisplayDataForVehicle


# Public interface to retrieve cached data for the simulation engine.
# Ensures data consistency between UI and Simulation.
def getSimulationDataForVehicle(fltVehicleCapacityCm3, dictCancellationFlag=DEFAULT_CANCEL_FLAG):
    
    print(f"Loading simulation data for capacity: {fltVehicleCapacityCm3}")
    
    dictCachedData = _getOrCreateCapacityCache(fltVehicleCapacityCm3, dictCancellationFlag)

    if not dictCachedData: 
        return None, []
    
    return dictCachedData['metadata'], dictCachedData['packages']

# end of getSimulationDataForVehicle