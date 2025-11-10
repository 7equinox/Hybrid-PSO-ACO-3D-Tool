"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and testing)
Module Name: Simulation Orchestration

Purpose of this file:
This module is the heart of the 'Experimentation Stage' as defined in the research
methodology. It acts as the master conductor for a single, complete experimental
run. Now integrated with custom unloading orchestrator.
"""

# --- Import necessary libraries ---
import time
import random
import math
import traceback
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

# --- Import Custom Application Modules ---
from backend.data_management.data_manager import fnGetDisplayDataForVehicle
from backend.simulation.performance_metrics import fnCalculateAllMetrics
from backend.simulation.custom_unloading_orchestrator import fnCustomUnloadingOrchestrator
from backend.simulation.custom_exceptions import CancelledException
from backend.algorithms.pso_algorithm import fnRunPsoAlgorithm
from backend.algorithms.aco_algorithm import fnRunAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import fnRunHybridPsoAcoAlgorithm

# --- EXPORT FUNCTION ---
# This ensures the function can be imported properly
__all__ = ['fnOrchestrateSimulationRun']

def _create_error_response(error_message, algorithm_name, capacity_cm3):
    """Creates a structured, default error response to prevent frontend crashes."""
    print(f"Generating structured error response: {error_message}")
    rect_dims = _fnCalculateRectangularDimensions(float(capacity_cm3))
    return {
        'error': error_message,
        'algorithm_name': algorithm_name,
        'metrics': {
            'computation_time': 0,
            'memory_usage_mb': 0,
            'volume_utilization': 0,
            'relocation_count': 0,
        },
        'packed_items': [],
        'loading_sequence': [],
        'unloading_sequence': [],
        'vehicle_info': {
            'id': 'ERROR',
            'capacity_cm3': capacity_cm3,
            **rect_dims,
            'num_packages_loaded': 0,
            'total_packed_volume': 0,
            'total_packed_service_time': 0,
        }
    }

class SpatialGrid:
    """Spatial hashing grid for efficient collision detection in 3D space."""
    def __init__(self, bin_dims, cell_size=50):
        self.cell_size = float(cell_size)
        self.grid = {}
        self.bin_dims = [float(d) for d in bin_dims]
        self.x_cells = int(math.ceil(self.bin_dims[0] / self.cell_size))
        self.y_cells = int(math.ceil(self.bin_dims[1] / self.cell_size))
        self.z_cells = int(math.ceil(self.bin_dims[2] / self.cell_size))
    
    def _get_cell_indices(self, pos, dims):
        """Returns all grid cell indices that an item occupies."""
        s = set()
        xs, ys, zs = [int(p // self.cell_size) for p in pos]
        xe, ye, ze = [int((p + d) // self.cell_size) for p, d in zip(pos, dims)]
        for x in range(max(0, xs), min(self.x_cells, xe + 1)):
            for y in range(max(0, ys), min(self.y_cells, ye + 1)):
                for z in range(max(0, zs), min(self.z_cells, ze + 1)):
                    s.add((x, y, z))
        return s
    
    def add_item(self, i):
        """Adds an item to the spatial grid."""
        for ci in self._get_cell_indices([float(p) for p in i.position], [float(d) for d in i.get_dimension()]):
            self.grid.setdefault(ci, []).append(i)
    
    def get_items_in_region(self, pos, dims):
        """Returns all items in a specific region."""
        s = set()
        for ci in self._get_cell_indices(pos, dims):
            if ci in self.grid:
                s.update(self.grid[ci])
        return list(s)

def _fnCalculateRectangularDimensions(fltVolumeCm3):
    """Calculates realistic, non-cubic dimensions for a truck container."""
    try:
        v = float(fltVolumeCm3)
        w = (v / 0.2) ** (1.0 / 3.0)
        h = w * 0.5
        d = w * 0.4
        return {
            "width": math.floor(w),
            "height": math.floor(h),
            "depth": math.floor(d)
        }
    except:
        return {"width": 0, "height": 0, "depth": 0}

def fnOrchestrateSimulationRun(strAlgorithmName, fltCapacityCm3, dictCancellationFlag, blnIsDynamicConstraintEnabled, dictProgressTracker):
    """
    Main orchestrator for a single experimental run.
    
    This is the primary function called by main_app.py to execute a complete simulation.
    It handles:
    1. Loading vehicle and package data
    2. Running the selected algorithm
    3. Performing final packing consolidation
    4. Generating unloading sequences
    5. Collecting metrics
    
    Args:
        strAlgorithmName (str): Name of algorithm ('PSO', 'ACO', 'PSO-ACO')
        fltCapacityCm3 (float): Vehicle capacity in cubic centimeters
        dictCancellationFlag (dict): Shared flag for cancellation {'is_cancelled': bool}
        blnIsDynamicConstraintEnabled (bool): Whether to enable dynamic constraints
        dictProgressTracker (dict): Shared dict for progress updates
    
    Returns:
        dict: Complete simulation results including metrics and sequences
    """
    try:
        if dictCancellationFlag['is_cancelled']:
            raise CancelledException()
        
        dictProgressTracker['message'] = "Loading dataset..."
        dict_vehicleInfo, arr_packagesInfo = fnGetDisplayDataForVehicle(fltCapacityCm3, dictCancellationFlag)
        
        if not dict_vehicleInfo or not arr_packagesInfo:
            return _create_error_response("Could not get vehicle/package data.", strAlgorithmName, fltCapacityCm3)
        
        flt_definitive_total_volume = sum(float(p['volume']) for p in arr_packagesInfo)
        dict_vehicleInfo['total_package_volume'] = flt_definitive_total_volume
        dict_vehicleInfo.update(_fnCalculateRectangularDimensions(float(fltCapacityCm3)))
        
        dictProgressTracker['message'] = "Preparing items..."
        
        # Randomize package orientations
        for p in arr_packagesInfo:
            dims = [float(p['width']), float(p['height']), float(p['depth'])]
            random.shuffle(dims)
            p['width'], p['height'], p['depth'] = dims
        
        arr_itemsToPack = [Item(str(p['id']), float(p['width']), float(p['height']), float(p['depth']), 1) for p in arr_packagesInfo]
        obj_bin = Bin(str(dict_vehicleInfo['id']), float(dict_vehicleInfo['width']), float(dict_vehicleInfo['height']), float(dict_vehicleInfo['depth']), 1e6)
        
        fitness_cache = {}
        
        def fnEvaluateSolution(indices):
            """Fitness evaluation function for the algorithms."""
            key = tuple(indices)
            if key in fitness_cache:
                return fitness_cache[key]
            
            if dictCancellationFlag['is_cancelled']:
                raise CancelledException()
            
            p = Packer()
            b = Bin(str(obj_bin.name), float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth), float(obj_bin.max_weight))
            p.add_bin(b)
            
            for i in indices:
                p.add_item(arr_itemsToPack[i])
            
            p.pack(bigger_first=True, distribute_items=True)
            
            metrics = fnCalculateAllMetrics(p.bins[0].items, float(obj_bin.get_volume()), arr_packagesInfo, strAlgorithmName)
            
            fit = (float(metrics['volume_utilization']), int(metrics['relocation_count']))
            fitness_cache[key] = fit
            return fit
        
        algo_map = {
            'PSO': fnRunPsoAlgorithm,
            'ACO': fnRunAcoAlgorithm,
            'PSO-ACO': fnRunHybridPsoAcoAlgorithm
        }
        
        func_algorithm = algo_map.get(strAlgorithmName)
        if not func_algorithm:
            return _create_error_response(f"Invalid algorithm: {strAlgorithmName}", strAlgorithmName, fltCapacityCm3)

        dictProgressTracker['message'] = f"Running {strAlgorithmName}..."
        tm_start = time.time()
        
        mem_res = memory_usage(
            (func_algorithm, (arr_itemsToPack, arr_packagesInfo, fnEvaluateSolution, dictCancellationFlag, dictProgressTracker)),
            retval=True,
            max_usage=True,
            interval=0.1
        )
        
        mem_usage = float(mem_res[0]) if isinstance(mem_res, tuple) else float(mem_res if mem_res else 0)
        computation_time = round(time.time() - tm_start, 2)

        dictProgressTracker['message'] = "Finalizing layout..."
        
        final_packer = Packer()
        final_bin = Bin(str(obj_bin.name), float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth), float(obj_bin.max_weight))
        final_packer.add_bin(final_bin)
        
        for item in arr_itemsToPack:
            final_packer.add_item(item)
        
        final_packer.pack(bigger_first=True, distribute_items=True, number_of_decimals=0)
        
        if not final_packer.bins[0].items:
            return _create_error_response("Final consolidation failed.", strAlgorithmName, fltCapacityCm3)
        
        _fnPostProcessPacking(final_packer.bins[0])
        num_loaded = len(final_packer.bins[0].items)

        # Extract bin dimensions to pass to unloading orchestrator
        bin_dims_for_metrics = [float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth)]
        dict_packages_map = {p['id']: p for p in arr_packagesInfo}
        
        # CUSTOM UNLOADING: Use the custom orchestrator instead of default
        custom_unloading_result = fnCustomUnloadingOrchestrator(
            final_packer.bins[0].items,
            dict_packages_map,
            strAlgorithmName,
            bin_dims_for_metrics
        )
        
        # Calculate final metrics
        final_metrics = fnCalculateAllMetrics(final_packer.bins[0].items, float(obj_bin.get_volume()), arr_packagesInfo, strAlgorithmName, bin_dims_for_metrics)
        
        details = []
        service_time = 0
        
        for i in final_packer.bins[0].items:
            p = next((pkg for pkg in arr_packagesInfo if str(pkg['id']) == str(i.name)), None)
            if p:
                w, h, d = map(float, i.get_dimension())
                pos = [float(c) for c in i.position]
                
                details.append({
                    **p,
                    "width": w,
                    "height": h,
                    "depth": d,
                    "position_x": pos[0],
                    "position_y": pos[1],
                    "position_z": pos[2]
                })
                service_time += float(p.get('service_time', 0))
        
        return {
            'algorithm_name': strAlgorithmName,
            'metrics': {
                'computation_time': round(float(computation_time), 2),
                'memory_usage_mb': round(float(mem_usage), 2),
                'volume_utilization': round(float(final_metrics['volume_utilization']), 2),
                'relocation_count': int(custom_unloading_result['relocation_count'])
            },
            'packed_items': details,
            'loading_sequence': _fnGenerateLoadingSequence(final_packer.bins[0].items)['event_log'],
            'unloading_sequence': custom_unloading_result['event_log'],
            'vehicle_info': {
                **dict_vehicleInfo,
                'num_packages_loaded': int(num_loaded),
                'total_packed_volume': round(float(flt_definitive_total_volume)),
                'total_packed_service_time': round(float(service_time))
            }
        }
        
    except CancelledException:
        return _create_error_response("Simulation cancelled by user.", strAlgorithmName, fltCapacityCm3)
    except Exception as e:
        traceback.print_exc()
        return _create_error_response(str(e), strAlgorithmName, fltCapacityCm3)

def _fnPostProcessPacking(objBin):
    """
    Post-processes the packing to ensure all items are properly settled due to gravity.
    
    This function simulates gravity by moving items down until they have support.
    """
    items = objBin.items
    iters = 15
    moved_total = 0
    
    if not items:
        return
    
    for iteration in range(iters):
        moved_this_pass = 0
        items.sort(key=lambda i: float(i.position[1]))
        
        for i in items:
            pos = [float(p) for p in i.position]
            dims = [float(d) for d in i.get_dimension()]
            support_y = 0.0
            
            for o in items:
                if i is o:
                    continue
                
                o_pos = [float(p) for p in o.position]
                o_dims = [float(d) for d in o.get_dimension()]
                
                # Check if 'o' is below 'i' and provides support
                if (o_pos[1] + o_dims[1]) <= (pos[1] + 1e-4):
                    # Check X-Z overlap
                    if (pos[0] < o_pos[0] + o_dims[0] and o_pos[0] < pos[0] + dims[0] and
                        pos[2] < o_pos[2] + o_dims[2] and o_pos[2] < pos[2] + dims[2]):
                        support_y = max(support_y, o_pos[1] + o_dims[1])
            
            if pos[1] > support_y + 1e-4:
                i.position[1] = str(support_y)
                moved_this_pass += 1
        
        moved_total += moved_this_pass
        if moved_this_pass == 0:
            break

def _fnGenerateLoadingSequence(items):
    """
    Generates a chronological loading sequence from the final packing layout.
    
    Args:
        items: List of packed items from the bin
    
    Returns:
        dict: Event log with loading sequence
    """
    if not items:
        return {'event_log': []}
    
    log = []
    
    for i in sorted(items, key=lambda i: (float(i.position[0]), float(i.position[1]), -float(i.get_volume()))):
        p = [float(c) for c in i.position]
        d = [float(c) for c in i.get_dimension()]
        
        log.append({
            'action': 'load',
            'item': {
                'id': str(i.name),
                'width': float(d[0]),
                'height': float(d[1]),
                'depth': float(d[2]),
                'position_x': float(p[0]),
                'position_y': float(p[1]),
                'position_z': float(p[2])
            }
        })
    
    return {'event_log': log}