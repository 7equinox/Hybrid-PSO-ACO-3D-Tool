# HYBRID-PSO-ACO-3D-TOOL/backend/utils/data_loader.py

import json
import os
import pandas as pd
import math
import gc # Import the garbage collector module

# --- Setup Paths and Cache Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Real datasets
# ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
# PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# --- Sample Data (Using smaller files for demonstration) ---
ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_route_data.json')
PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_package_data.json')

# Define and create the cache directory
DATA_CACHE_DIR = os.path.join(BASE_DIR, '..', 'data')
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# --- MODIFICATION ---
# REMOVED the global cache variables (_route_data_cache, _package_data_cache).
# We will no longer hold the entire 190MB+ dataset in memory for the application's lifetime.

def _load_and_release_json_data():
    """
    MODIFIED: This function now loads the large JSON files, returns them,
    and is intended for temporary use. The goal is to load, process, and then
    release this data from memory as quickly as possible.
    """
    print("Loading large JSON files into memory for processing...")
    with open(ROUTE_DATA_PATH, 'r') as f:
        route_data_df = pd.DataFrame.from_dict(json.load(f), orient='index')
    with open(PACKAGE_DATA_PATH, 'r') as f:
        package_data = json.load(f)
    print("Finished loading large JSON files.")
    return route_data_df, package_data

def get_all_vehicle_capacities():
    """
    MODIFIED: Loads route data just to get capacities and then releases it.
    This prevents holding data in memory.
    """
    route_data, _ = _load_and_release_json_data()
    capacities = route_data['executor_capacity_cm3'].dropna().unique()
    # Explicitly clear the dataframe from memory and run garbage collection
    del route_data
    gc.collect()
    print("Memory released after fetching capacities.")
    return sorted([float(c) for c in capacities])

def _get_or_create_capacity_cache(vehicle_capacity_cm3):
    """
    MODIFIED SIGNIFICANTLY FOR SPEED:
    - This function now creates a single, more intelligent cache file.
    - The cache file is a JSON object with two keys: 'metadata' and 'packages'.
    - 'metadata' stores pre-calculated vehicle info and package totals.
    - This completely AVOIDS reloading the huge route file on subsequent page loads, making pagination instantaneous.
    """
    cache_filename = f"{vehicle_capacity_cm3}.json"
    cache_filepath = os.path.join(DATA_CACHE_DIR, cache_filename)

    # Clear old cache files
    for filename in os.listdir(DATA_CACHE_DIR):
        if filename.endswith('.json') and filename != cache_filename:
            os.remove(os.path.join(DATA_CACHE_DIR, filename))
            print(f"Removed old cache file: {filename}")

    # If the smart cache file exists, just load and return it. This is the FAST path.
    if os.path.exists(cache_filepath):
        print(f"Loading from existing smart cache file: {cache_filename}")
        with open(cache_filepath, 'r') as f:
            return json.load(f)

    # --- SLOW PATH (happens only ONCE per vehicle capacity) ---
    print(f"Cache not found. Creating new smart cache for capacity: {vehicle_capacity_cm3}")
    route_data_cache, package_data_cache = _load_and_release_json_data()
    
    matching_routes_df = route_data_cache[
        route_data_cache['executor_capacity_cm3'] == vehicle_capacity_cm3
    ]

    if matching_routes_df.empty:
        del route_data_cache, package_data_cache
        gc.collect()
        return None

    # Step 1: Process all packages for this capacity
    all_packages_info = []
    route_ids = matching_routes_df.index.tolist()
    for route_id in route_ids:
        route_packages = package_data_cache.get(route_id, {})
        for stop_id, packages_at_stop in route_packages.items():
            for package_id, details in packages_at_stop.items():
                dims = details.get('dimensions', {})
                try:
                    volume = float(dims.get('height_cm', 0)) * float(dims.get('width_cm', 0)) * float(dims.get('depth_cm', 0))
                    if volume > 0:
                        all_packages_info.append({
                            'id': package_id, 'route_id': route_id, 'stop_id': stop_id,
                            'height': float(dims.get('height_cm')), 'width': float(dims.get('width_cm')),
                            'depth': float(dims.get('depth_cm')), 'volume': volume,
                            'service_time': float(details.get('planned_service_time_seconds', 0))
                        })
                except (ValueError, TypeError):
                    continue
    
    # Step 2: Pre-calculate all metadata. This is only done ONCE.
    dimension = (vehicle_capacity_cm3 ** (1./3.))
    metadata = {
        'id': ', '.join(route_ids),
        'capacity_cm3': vehicle_capacity_cm3,
        'width': math.floor(dimension), 'height': math.floor(dimension), 'depth': math.floor(dimension),
        'total_package_volume': sum(p['volume'] for p in all_packages_info),
        'total_service_time': sum(p['service_time'] for p in all_packages_info),
        'num_packages': len(all_packages_info),
        'num_vehicles_found': len(route_ids)
    }

    # Step 3: Combine metadata and packages into a single object for caching
    data_to_cache = {
        'metadata': metadata,
        'packages': all_packages_info
    }

    # Step 4: Save the new smart cache file
    with open(cache_filepath, 'w') as f:
        json.dump(data_to_cache, f)
    print(f"Successfully created smart cache: {cache_filename}")

    # Step 5: CRITICAL - Release memory now that the cache is saved
    del route_data_cache, package_data_cache, all_packages_info
    gc.collect()
    print("Memory from large JSON files has been successfully released.")

    return data_to_cache


def load_data(vehicle_capacity_cm3, page=1, page_size=100):
    """
    MODIFIED FOR SPEED: This function is now much simpler and faster.
    It gets the complete data from the smart cache and simply paginates the results.
    NO MORE REPEATED FILE LOADING.
    """
    cached_data = _get_or_create_capacity_cache(vehicle_capacity_cm3)
    
    if not cached_data:
        return None, []

    metadata = cached_data['metadata']
    all_packages_info = cached_data['packages']
    
    # Paginate the results from the full list
    total_packages = metadata['num_packages']
    total_pages = math.ceil(total_packages / page_size) if page_size > 0 else 1
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_packages = all_packages_info[start_index:end_index]
    
    # Construct the final vehicle info, adding pagination details to the pre-calculated metadata
    aggregate_vehicle_info = {
        **metadata,  # Unpack all the pre-calculated totals
        'pagination_meta': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_items': total_packages
        }
    }
    
    return aggregate_vehicle_info, paginated_packages


def get_vehicle_info_only(vehicle_capacity_cm3):
    """
    MODIFIED FOR SPEED: This now uses the smart cache. It's fast because it
    will either trigger cache creation once or just read the small cache file.
    """
    cached_data = _get_or_create_capacity_cache(vehicle_capacity_cm3)
    if not cached_data:
        return None
    
    # Just return the metadata part of the cache
    return cached_data['metadata']