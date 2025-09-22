# HYBRID-PSO-ACO-3D-TOOL/backend/utils/data_loader.py
import json
import os
import pandas as pd

# Define paths to the dataset files.
# Using os.path.join ensures compatibility across different operating systems.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_route_data.json')
PACKAGE_DATA_PATH = os.path.join(BASE_DIR, '../almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/eval_package_data.json')

# Cache loaded data to avoid reading from disk on every request
_route_data_cache = None
_package_data_cache = None

def _load_json_data():
    """
    Internal function to load and cache the dataset from JSON files.
    Caching is a performance optimization to speed up subsequent requests.
    """
    global _route_data_cache, _package_data_cache
    if _route_data_cache is None:
        with open(ROUTE_DATA_PATH, 'r') as f:
            _route_data_cache = json.load(f)
    if _package_data_cache is None:
        with open(PACKAGE_DATA_PATH, 'r') as f:
            _package_data_cache = json.load(f)

def get_all_vehicle_capacities():
    """
    Scans the route data file to find all unique vehicle capacities available
    in the dataset. This is used to populate the dropdown in the frontend.
    """
    _load_json_data()
    capacities = set()
    for route_id, route_details in _route_data_cache.items():
        if 'executor_capacity_cm3' in route_details:
            capacities.add(float(route_details['executor_capacity_cm3']))
    return sorted(list(capacities))


def load_data(vehicle_capacity_cm3):
    """
    Loads vehicle and package data for a given vehicle capacity.
    It finds a route matching the capacity and extracts all associated packages.
    """
    _load_json_data()
    
    target_route_id = None
    vehicle_info = {}
    
    # Find the first RouteID that matches the selected capacity
    for route_id, route_details in _route_data_cache.items():
        if route_details.get('executor_capacity_cm3') == vehicle_capacity_cm3:
            target_route_id = route_id
            vehicle_info = {
                'id': route_id,
                'capacity_cm3': route_details['executor_capacity_cm3'],
                # For 3D bin packing, we need vehicle dimensions. The dataset only gives volume.
                # We derive cube-like dimensions as a reasonable assumption for the simulation.
                'width': round((vehicle_capacity_cm3 ** (1./3.))),
                'height': round((vehicle_capacity_cm3 ** (1./3.))),
                'depth': round((vehicle_capacity_cm3 ** (1./3.))),
            }
            break

    if not target_route_id:
        return None, None
        
    packages_info = []
    total_package_volume = 0
    total_service_time = 0

    # Retrieve all packages for the identified route
    route_packages = _package_data_cache.get(target_route_id, {})
    for stop, packages_at_stop in route_packages.items():
        for package_id, details in packages_at_stop.items():
            dims = details.get('dimensions', {})
            # Ensure package dimensions are valid numbers
            try:
                height = float(dims.get('height_cm', 0))
                width = float(dims.get('width_cm', 0))
                depth = float(dims.get('depth_cm', 0))
                service_time = float(details.get('planned_service_time_seconds', 0))
                
                volume = height * width * depth
                if volume > 0:
                    packages_info.append({
                        'id': package_id,
                        'stop_id': stop,
                        'height': height,
                        'width': width,
                        'depth': depth,
                        'volume': volume,
                        'service_time': service_time
                    })
                    total_package_volume += volume
                    total_service_time += service_time
            except (ValueError, TypeError):
                # Skip packages with invalid or missing data
                continue
    
    # Add summary information to the vehicle data dictionary
    vehicle_info['total_package_volume'] = total_package_volume
    vehicle_info['total_service_time'] = total_service_time
    vehicle_info['num_packages'] = len(packages_info)

    return vehicle_info, packages_info