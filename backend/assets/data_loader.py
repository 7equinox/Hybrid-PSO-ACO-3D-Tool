"""
System Name: OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
Module Name: Data Loader

Purpose of this file:
To handle loading, parsing, and preprocessing of the 2021 Amazon Last Mile
Routing Research Challenge Dataset from its JSON file format.

Author/ s:
ALFARO, ABRAM  S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
import pandas as pd

class DataLoader:
    """
    Manages loading and preparing data for the simulation.
    """
    def __init__(self, str_route_file_path, str_package_file_path):
        """
        Initializes the DataLoader with paths to the dataset files.
        """
        self.str_route_file = str_route_file_path
        self.str_package_file = str_package_file_path

    def load_data(self):
        """
        Loads the route and package JSON data into pandas DataFrames.
        
        Returns:
            A tuple containing two dictionaries: (routes_data, package_data).
        """
        try:
            # Load route data
            df_routes = pd.read_json(self.str_route_file, orient='index')
            dict_routes = df_routes.to_dict(orient='index')
            
            # Load package data
            df_packages = pd.read_json(self.str_package_file, orient='index')
            dict_packages = df_packages.to_dict(orient='index')
            
            return dict_routes, dict_packages
        except FileNotFoundError as err:
            raise FileNotFoundError(f"Dataset file not found: {err}. Ensure the dataset path is correct.")

    def _route_has_packages(self, dict_route_info):
            """ 
            Helper function to check if a route has any associated packages in its stops. 
            """
            if 'stops' in dict_route_info and isinstance(dict_route_info['stops'], dict):
                for stop_data in dict_route_info['stops'].values():
                    if 'package_ids' in stop_data and isinstance(stop_data['package_ids'], list) and stop_data['package_ids']:
                        return True # Found a stop with a non-empty list of package_ids
            return False

    def get_route_by_capacity(self, dict_routes, flt_capacity):
        """
        Finds the first route ID that matches the given vehicle capacity.
        
        Args:
            dict_routes (dict): The dictionary of all route data.
            flt_capacity (float): The vehicle capacity to search for.
            
        Returns:
            The route ID (str) if a match is found, otherwise None.
        """
        for str_route_id, dict_route_info in dict_routes.items():
            if float(dict_route_info['executor_capacity_cm3']) == flt_capacity:
                if self._route_has_packages(dict_route_info):
                    return str_route_id
        return None

    def prepare_simulation_data(self, str_route_id, dict_routes, dict_packages):
        """
        Prepares the vehicle and package lists for a specific route.
        
        Args:
            str_route_id (str): The ID of the selected route.
            dict_routes (dict): The dictionary of all routes.
            dict_packages (dict): The dictionary of all packages.
            
        Returns:
            A tuple: (vehicle_data_dict, package_data_list).
        """
        # Get the vehicle info from the selected route
        dict_route_info = dict_routes[str_route_id]
        
        # Dimensions are assumed based on standard container sizes, as they
        # are not provided in the dataset. These are example values.
        # This is a controlled variable as per Chapter 3.
        dict_vehicle_data = {
            'name': 'Delivery-Vehicle',
            'width': 180, # cm
            'height': 160, # cm
            'depth': 220, # cm
            'capacity_cm3': dict_route_info['executor_capacity_cm3']
        }
        
        # Get the list of package IDs by iterating through all stops in the route.
        # The original code incorrectly looked for a 'route_sequence' key.
        arr_package_ids = []
        if 'stops' in dict_route_info and isinstance(dict_route_info['stops'], dict):
            for stop_id, stop_data in dict_route_info['stops'].items():
                if 'package_ids' in stop_data and isinstance(stop_data['package_ids'], list):
                    arr_package_ids.extend(stop_data['package_ids'])

        # Filter the main package dictionary to get only the packages for this route
        arr_packages_for_route = []
        for str_package_id in arr_package_ids:
            if str_package_id in dict_packages:
                dict_package = dict_packages[str_package_id]
                # Reformat the dictionary to match the expected structure
                # The py3dbp library expects dimensions in a different order.
                arr_packages_for_route.append({
                    'name': str_package_id,
                    'width': dict_package['dimensions']['width_cm'],
                    'height': dict_package['dimensions']['height_cm'],
                    'depth': dict_package['dimensions']['depth_cm'],
                    'weight': 1 # Weight is not used but required by library
                })

        return dict_vehicle_data, arr_packages_for_route