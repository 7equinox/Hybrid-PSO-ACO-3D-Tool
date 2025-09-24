# HYBRID-PSO-ACO-3D-TOOL/backend/utils/data_loader.py

import json
import os
import pandas as pd
import math

# Define paths to the dataset files.
# Using os.path.join ensures compatibility across different operating systems.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
# PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_route_data.json')
PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../sample-data/test_package_data.json')

# Cache loaded data to avoid reading from disk on every request
_route_data_cache = None
_package_data_cache = None

def _load_json_data():
    """
    Internal function to load and cache the dataset from JSON files.
    This optimization improves performance on subsequent requests.
    """
    global _route_data_cache, _package_data_cache
    if _route_data_cache is None:
        with open(ROUTE_DATA_PATH, 'r') as f:
            # As per Chapter 3, Pandas is used to structure logistical data.
            # Loading into a DataFrame allows for easier manipulation.
            _route_data_cache = pd.DataFrame.from_dict(json.load(f), orient='index')
    if _package_data_cache is None:
        with open(PACKAGE_DATA_PATH, 'r') as f:
            _package_data_cache = json.load(f)

def get_all_vehicle_capacities():
    """
    Scans the route data file to find all unique vehicle capacities available
    in the dataset. This is used to populate the dropdown in the frontend.
    """
    _load_json_data()
    # Using pandas to efficiently find and sort unique capacity values.
    capacities = _route_data_cache['executor_capacity_cm3'].dropna().unique()
    return sorted([float(c) for c in capacities])

def load_data(vehicle_capacity_cm3):
    """
    Aggregates data from ALL vehicles matching the specified capacity.
    It finds all routes matching the capacity, extracts all packages, and returns a
    single aggregate info dictionary for the frontend alongside a list of all packages.
    """
    _load_json_data()
    
    # Find all routes that match the selected capacity.
    matching_routes_df = _route_data_cache[
        _route_data_cache['executor_capacity_cm3'] == vehicle_capacity_cm3
    ]

    if matching_routes_df.empty:
        return None, []

    all_packages_info = []
    total_package_volume = 0
    total_service_time = 0
    route_ids = []

    # Iterate over all routes that matched the specified capacity to collect packages
    for target_route_id, target_route_series in matching_routes_df.iterrows():
        route_ids.append(target_route_id)
        # Retrieve all packages associated with the identified route.
        route_packages = _package_data_cache.get(target_route_id, {})
        for stop_id, packages_at_stop in route_packages.items():
            for package_id, details in packages_at_stop.items():
                dims = details.get('dimensions', {})
                try:
                    height = float(dims.get('height_cm', 0))
                    width = float(dims.get('width_cm', 0))
                    depth = float(dims.get('depth_cm', 0))
                    service_time = float(details.get('planned_service_time_seconds', 0))
                    
                    volume = height * width * depth
                    if volume > 0:
                        all_packages_info.append({
                            'id': package_id,
                            'route_id': target_route_id,
                            'stop_id': stop_id,
                            'height': height,
                            'width': width,
                            'depth': depth,
                            'volume': volume,
                            'service_time': service_time
                        })
                        total_package_volume += volume
                        total_service_time += service_time
                except (ValueError, TypeError):
                    print(f"Skipping package {package_id} in route {target_route_id} due to invalid data.")
                    continue
    
    # The derived dimensions will be the same for all vehicles of the same capacity
    dimension = (vehicle_capacity_cm3 ** (1./3.))
    
    # Create a single aggregate vehicle_info object for the frontend display
    aggregate_vehicle_info = {
        'id': ', '.join(route_ids),  # A composite ID of all matching routes
        'capacity_cm3': vehicle_capacity_cm3,
        'width': math.floor(dimension),
        'height': math.floor(dimension),
        'depth': math.floor(dimension),
        'total_package_volume': total_package_volume,
        'total_service_time': total_service_time,
        'num_packages': len(all_packages_info),
        'num_vehicles_found': len(route_ids) # extra info
    }

    return aggregate_vehicle_info, all_packages_info