import json
import pandas as pd

def load_data(package_path, route_path):
    """
    Loads the package and route data from their respective JSON files.
    This function is called once at server startup to load data into memory.
    """
    try:
        with open(package_path, 'r') as f:
            package_data = json.load(f)
        with open(route_path, 'r') as f:
            route_data = json.load(f)
        return package_data, route_data
    except FileNotFoundError as e:
        # Handle cases where the dataset files are not found, preventing the app from crashing
        print(f"Error loading data files: {e}")
        return None, None
    except json.JSONDecodeError as e:
        # Handle cases where the JSON files are malformed
        print(f"Error decoding JSON: {e}")
        return None, None


def get_routes_and_capacities(route_data):
    """
    Parses the route data to create a mapping from each unique vehicle capacity
    to a list of route IDs that use that capacity.
    This pre-computation makes lookups by capacity much faster.
    """
    capacities = {}
    if not route_data:
        return capacities
        
    for route_id, data in route_data.items():
        capacity = data.get("executor_capacity_cm3")
        if capacity:
            if capacity not in capacities:
                capacities[capacity] = []
            capacities[capacity].append(route_id)
    return capacities

def get_route_data_by_capacity(capacity, all_route_data, all_package_data):
    """
    Retrieves a single representative route and its associated packages for a given capacity.
    This provides the "initial data" displayed in the UI's left panel.
    """
    # Find a route that matches the selected capacity. We only need one for display purposes.
    route_id_for_capacity = next((rid for rid, rdata in all_route_data.items() if rdata.get("executor_capacity_cm3") == capacity), None)

    if not route_id_for_capacity:
        return None
    
    route_info = all_route_data[route_id_for_capacity]
    packages_for_route = all_package_data.get(route_id_for_capacity, {})
    
    # Process the package data into a structured list of dictionaries
    # This format is easy for the frontend to render in a table
    item_list = []
    total_volume = 0
    total_service_time = 0

    # The dataset nests packages under stop IDs (e.g., 'AH', 'AJ')
    for stop_id, stop_packages in packages_for_route.items():
        for package_id, details in stop_packages.items():
            dims = details.get('dimensions', {})
            # Ensure all required dimensions are present before calculation
            if all(k in dims for k in ['height_cm', 'width_cm', 'depth_cm']):
                h = dims['height_cm']
                w = dims['width_cm']
                d = dims['depth_cm']
                volume = h * w * d
                total_volume += volume
                service_time = details.get('planned_service_time_seconds', 0)
                total_service_time += service_time
                item_list.append({
                    'id': package_id,
                    'volume': round(volume, 2),
                    'service_time': service_time,
                    'height': h,
                    'length': d, # Mapping 'depth_cm' to 'length' for consistency
                    'width': w,
                })

    return {
        "vehicle_capacity": capacity,
        "total_product_volume": round(total_volume, 2),
        "number_of_products": len(item_list),
        "total_service_time": round(total_service_time, 2),
        "items": item_list,
        "route_id": route_id_for_capacity # Return the RouteID for context
    }