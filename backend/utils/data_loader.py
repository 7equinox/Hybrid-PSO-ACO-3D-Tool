# HYBRID-PSO-ACO-3D-TOOL/backend/utils/data_loader.py

import json
import os
import pandas as pd
import math

# Define paths to the dataset files.
# Using os.path.join ensures compatibility across different operating systems.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# UPDATED to use the large dataset files
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

def load_data(vehicle_capacity_cm3, page=1, page_size=100):
    """
    MODIFIED for PAGINATION: Aggregates data from ALL vehicles matching the specified capacity,
    but now returns only a 'page' of packages at a time to avoid crashing the browser.
    The aggregate info is calculated once and returned with every page.
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
    # This is still memory intensive on the server, but necessary to get total counts for pagination
    for target_route_id, _ in matching_routes_df.iterrows():
        route_ids.append(target_route_id)
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
                            'id': package_id, 'route_id': target_route_id, 'stop_id': stop_id,
                            'height': height, 'width': width, 'depth': depth,
                            'volume': volume, 'service_time': service_time
                        })
                        total_package_volume += volume
                        total_service_time += service_time
                except (ValueError, TypeError):
                    print(f"Skipping package {package_id} in route {target_route_id} due to invalid data.")
                    continue

    # --- PAGINATION LOGIC ---
    total_packages = len(all_packages_info)
    total_pages = math.ceil(total_packages / page_size) if page_size > 0 else 1
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_packages = all_packages_info[start_index:end_index]
    # --- END PAGINATION LOGIC ---

    dimension = (vehicle_capacity_cm3 ** (1./3.))
    
    # This object now contains the grand totals and pagination metadata
    aggregate_vehicle_info = {
        'id': ', '.join(route_ids),
        'capacity_cm3': vehicle_capacity_cm3,
        'width': math.floor(dimension),
        'height': math.floor(dimension),
        'depth': math.floor(dimension),
        'total_package_volume': total_package_volume,
        'total_service_time': total_service_time,
        'num_packages': total_packages,
        'num_vehicles_found': len(route_ids),
        'pagination_meta': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_items': total_packages
        }
    }

    return aggregate_vehicle_info, paginated_packages