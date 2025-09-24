# HYBRID-PSO-ACO-3D-TOOL/backend/utils/data_loader.py

import json
import os
import pandas as pd
import math

# --- Setup Paths and Cache Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
# PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# -- Sample Data --
ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_route_data.json')
PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_package_data.json')

# Define and create the cache directory
DATA_CACHE_DIR = os.path.join(BASE_DIR, '..', 'data')
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# Cache data read from files in memory
_route_data_cache = None
_package_data_cache = None

def _load_json_data():
    """Loads large JSON files into memory once."""
    global _route_data_cache, _package_data_cache
    if _route_data_cache is None:
        with open(ROUTE_DATA_PATH, 'r') as f:
            _route_data_cache = pd.DataFrame.from_dict(json.load(f), orient='index')
    if _package_data_cache is None:
        with open(PACKAGE_DATA_PATH, 'r') as f:
            _package_data_cache = json.load(f)

def get_all_vehicle_capacities():
    """Gets all unique capacities from the route data."""
    _load_json_data()
    capacities = _route_data_cache['executor_capacity_cm3'].dropna().unique()
    return sorted([float(c) for c in capacities])

def _get_or_create_capacity_cache(vehicle_capacity_cm3):
    """
    MODIFIED: First, it clears any old cache files. Then, it checks for a
    pre-filtered cache file for the current capacity. If it doesn't exist, it creates one.
    Returns the complete list of packages for the given capacity.
    """
    cache_filename = f"{vehicle_capacity_cm3}.json"
    cache_filepath = os.path.join(DATA_CACHE_DIR, cache_filename)

    # --- NEW: Clear all OTHER cache files ---
    for filename in os.listdir(DATA_CACHE_DIR):
        if filename.endswith('.json') and filename != cache_filename:
            try:
                os.remove(os.path.join(DATA_CACHE_DIR, filename))
                print(f"Removed old cache file: {filename}")
            except Exception as e:
                print(f"Error removing old cache file {filename}: {e}")
    # --- END of new code ---

    # Check if the correct cache file already exists
    if os.path.exists(cache_filepath):
        print(f"Loading from existing cache file: {cache_filename}")
        with open(cache_filepath, 'r') as f:
            return json.load(f)

    # If not found, create it
    print(f"Cache not found. Creating new cache file for capacity: {vehicle_capacity_cm3}")
    _load_json_data()
    
    matching_routes_df = _route_data_cache[
        _route_data_cache['executor_capacity_cm3'] == vehicle_capacity_cm3
    ]

    if matching_routes_df.empty:
        return []

    all_packages_info = []
    for route_id, _ in matching_routes_df.iterrows():
        route_packages = _package_data_cache.get(route_id, {})
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
    
    # Save the filtered data to the new cache file
    with open(cache_filepath, 'w') as f:
        json.dump(all_packages_info, f)

    return all_packages_info

def load_data(vehicle_capacity_cm3, page=1, page_size=100):
    """
    Primary UI function. Uses the cache to get all packages,
    then calculates totals and returns a single page of items.
    """
    all_packages_info = _get_or_create_capacity_cache(vehicle_capacity_cm3)
    
    if not all_packages_info:
        return None, []

    # Calculate totals from the full (cached) list
    total_package_volume = sum(p['volume'] for p in all_packages_info)
    total_service_time = sum(p['service_time'] for p in all_packages_info)
    total_packages = len(all_packages_info)

    # Paginate the results
    total_pages = math.ceil(total_packages / page_size) if page_size > 0 else 1
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_packages = all_packages_info[start_index:end_index]
    
    # Create the summary object for the frontend
    _load_json_data() # Ensure _route_data_cache is available
    matching_routes_df = _route_data_cache[_route_data_cache['executor_capacity_cm3'] == vehicle_capacity_cm3]
    route_ids = matching_routes_df.index.tolist()
    dimension = (vehicle_capacity_cm3 ** (1./3.))
    
    aggregate_vehicle_info = {
        'id': ', '.join(route_ids),
        'capacity_cm3': vehicle_capacity_cm3,
        'width': math.floor(dimension), 'height': math.floor(dimension), 'depth': math.floor(dimension),
        'total_package_volume': total_package_volume,
        'total_service_time': total_service_time,
        'num_packages': total_packages,
        'num_vehicles_found': len(route_ids),
        'pagination_meta': {
            'current_page': page, 'page_size': page_size,
            'total_pages': total_pages, 'total_items': total_packages
        }
    }
    
    return aggregate_vehicle_info, paginated_packages

def get_vehicle_info_only(vehicle_capacity_cm3):
    """
    SUPER FAST: Gets only the vehicle dimension info for a given capacity
    without processing any packages or interacting with cache files.
    """
    _load_json_data()
    matching_routes_df = _route_data_cache[_route_data_cache['executor_capacity_cm3'] == vehicle_capacity_cm3]
    if matching_routes_df.empty: return None
        
    route_ids = matching_routes_df.index.tolist()
    dimension = (vehicle_capacity_cm3 ** (1./3.))
    vehicle_info = {
        'id': ', '.join(route_ids), 'capacity_cm3': vehicle_capacity_cm3,
        'width': math.floor(dimension), 'height': math.floor(dimension), 'depth': math.floor(dimension)
    }
    return vehicle_info