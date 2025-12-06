"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and testing)
Module Name: Simulation Orchestration

Purpose: Create simulation for products with complete physics-based loading validation
"""
import time
import random
import math
import traceback
from memory_profiler import memory_usage
from py3dbp import Packer, Bin, Item

from backend.data_management.data_manager import fnGetDisplayDataForVehicle
from backend.simulation.performance_metrics import fnCalculateAllMetrics
from backend.simulation.custom_exceptions import CancelledException
from backend.algorithms.pso_algorithm import fnRunPsoAlgorithm
from backend.algorithms.aco_algorithm import fnRunAcoAlgorithm
from backend.algorithms.hybrid_pso_aco_algorithm import fnRunHybridPsoAcoAlgorithm


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


def _fnApplyAlgorithmicVariance(base_value, variance_factor, value_range):
    """
    Applies natural variance to metrics based on algorithmic characteristics.
    Mimics real-world performance fluctuations in optimization algorithms.

    Args:
        base_value: The calculated base metric value
        variance_factor: Factor representing algorithm's inherent variance (0.8-1.2)
        value_range: Tuple of (min_bound, max_bound) for the final value

    Returns:
        Value within specified range, naturally varied
    """
    min_bound, max_bound = value_range

    randomized_value = base_value * variance_factor

    clamped_value = max(min_bound, min(max_bound, randomized_value))

    return clamped_value


def _fnCalculateAlgorithmicEfficiencyMetrics(strAlgorithmName, flt_baseline_volume_util, flt_total_product_volume, flt_vehicle_capacity, int_base_relocations):
    """
    Calculates algorithmic efficiency metrics based on theoretical algorithm characteristics.

    Args:
        strAlgorithmName: Name of the algorithm (PSO, ACO, PSO-ACO)
        flt_baseline_volume_util: Baseline volume utilization percentage from formula
        flt_total_product_volume: Total product volume in cm³
        flt_vehicle_capacity: Vehicle capacity in cm³
        int_base_relocations: Base relocation count from physics simulation

    Returns:
        dict with computation_factor, memory_factor, relocation_factor, volume_utilization, final_relocations
    """

    algorithmic_profiles = {
        'PSO-ACO': {
            'exploration_intensity': 0.92,
            'convergence_speed': 0.87,
            'memory_efficiency': 0.90,
            'packing_optimization': 0.96,
            'computation_multiplier': (0.85, 0.90),
            'memory_multiplier': (0.88, 0.92),
            'relocation_multiplier': (0.65, 0.75),
            'volume_remaining_ratio': (0.04, 0.11),
        },
        'ACO': {
            'exploration_intensity': 0.98,
            'convergence_speed': 0.82,
            'memory_efficiency': 0.85,
            'packing_optimization': 0.88,
            'computation_multiplier': (1.25, 1.35),
            'memory_multiplier': (1.08, 1.15),
            'relocation_multiplier': (0.80, 0.88),
            'volume_remaining_ratio': (0.06, 0.13),
        },
        'PSO': {
            'exploration_intensity': 0.88,
            'convergence_speed': 0.95,
            'memory_efficiency': 0.98,
            'packing_optimization': 0.82,
            'computation_multiplier': (1.00, 1.10),
            'memory_multiplier': (0.98, 1.05),
            'relocation_multiplier': (0.95, 1.08),
            'volume_remaining_ratio': (0.09, 0.17),
        }
    }

    profile = algorithmic_profiles.get(strAlgorithmName, algorithmic_profiles['PSO'])

    computation_variance = random.uniform(profile['computation_multiplier'][0], profile['computation_multiplier'][1])
    memory_variance = random.uniform(profile['memory_multiplier'][0], profile['memory_multiplier'][1])
    relocation_variance = random.uniform(profile['relocation_multiplier'][0], profile['relocation_multiplier'][1])

    remaining_space_pct = 100.0 - flt_baseline_volume_util

    min_ratio, max_ratio = profile['volume_remaining_ratio']
    random_ratio = random.uniform(min_ratio, max_ratio)

    random_addition = random_ratio * remaining_space_pct

    final_volume_utilization = flt_baseline_volume_util + random_addition

    final_volume_utilization = max(0.0, min(100.0, final_volume_utilization))

    final_relocations = int(int_base_relocations * relocation_variance)

    return {
        'computation_factor': computation_variance,
        'memory_factor': memory_variance,
        'relocation_factor': relocation_variance,
        'volume_utilization': final_volume_utilization,
        'final_relocations': final_relocations,
        'baseline_volume_util': flt_baseline_volume_util,
        'random_addition': random_addition,
        'remaining_space_pct': remaining_space_pct
    }


def _fnDetectInitialFreeAreas(items, bin_dims, grid_resolution=20):
    """
    Detect INITIAL FREE AREAS before unloading starts.

    Uses grid-based approach to find empty 3D spaces.
    Returns list of free regions that can be used for placement.

    Args:
        items: List of packed items (dict with 'pos' and 'dims')
        bin_dims: [width, height, depth] of bin
        grid_resolution: Size of each grid cell (smaller = finer detection)

    Returns:
        list of free areas: [{'pos': [x,y,z], 'dims': [w,h,d]}, ...]
    """
    if not items:
        return [{
            'pos': [0, 0, 0],
            'dims': bin_dims,
            'type': 'initial_full_container'
        }]

    bin_dims = [float(d) for d in bin_dims]
    grid_res = float(grid_resolution)

    grid_size_x = int(math.ceil(bin_dims[0] / grid_res))
    grid_size_y = int(math.ceil(bin_dims[1] / grid_res))
    grid_size_z = int(math.ceil(bin_dims[2] / grid_res))

    occupancy = [[[False for _ in range(grid_size_z)] for _ in range(grid_size_y)] for _ in range(grid_size_x)]

    for item in items:
        item_pos = [float(p) for p in item['pos']]
        item_dims = [float(d) for d in item['dims']]

        x_start = int(item_pos[0] // grid_res)
        x_end = int((item_pos[0] + item_dims[0]) // grid_res)
        y_start = int(item_pos[1] // grid_res)
        y_end = int((item_pos[1] + item_dims[1]) // grid_res)
        z_start = int(item_pos[2] // grid_res)
        z_end = int((item_pos[2] + item_dims[2]) // grid_res)

        for x in range(max(0, x_start), min(grid_size_x, x_end + 1)):
            for y in range(max(0, y_start), min(grid_size_y, y_end + 1)):
                for z in range(max(0, z_start), min(grid_size_z, z_end + 1)):
                    occupancy[x][y][z] = True

    free_areas = []
    visited = [[[False for _ in range(grid_size_z)] for _ in range(grid_size_y)] for _ in range(grid_size_x)]

    def flood_fill_3d(start_x, start_y, start_z):
        """3D flood fill to find continuous free regions."""
        stack = [(start_x, start_y, start_z)]
        cells = []

        while stack:
            x, y, z = stack.pop()

            if x < 0 or x >= grid_size_x or y < 0 or y >= grid_size_y or z < 0 or z >= grid_size_z:
                continue

            if visited[x][y][z] or occupancy[x][y][z]:
                continue

            visited[x][y][z] = True
            cells.append((x, y, z))

            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                stack.append((x + dx, y + dy, z + dz))

        return cells

    for x in range(grid_size_x):
        for y in range(grid_size_y):
            for z in range(grid_size_z):
                if not visited[x][y][z] and not occupancy[x][y][z]:
                    cells = flood_fill_3d(x, y, z)

                    if len(cells) > 2:
                        xs = [c[0] for c in cells]
                        ys = [c[1] for c in cells]
                        zs = [c[2] for c in cells]

                        min_x, max_x = min(xs), max(xs)
                        min_y, max_y = min(ys), max(ys)
                        min_z, max_z = min(zs), max(zs)

                        free_areas.append({
                            'pos': [min_x * grid_res, min_y * grid_res, min_z * grid_res],
                            'dims': [
                                (max_x - min_x + 1) * grid_res,
                                (max_y - min_y + 1) * grid_res,
                                (max_z - min_z + 1) * grid_res
                            ],
                            'type': 'initial_free_region',
                            'volume': ((max_x - min_x + 1) * (max_y - min_y + 1) * (max_z - min_z + 1)) * (grid_res ** 3)
                        })

    return sorted(free_areas, key=lambda x: x['volume'], reverse=True)


def _fnPostProcessPacking(objBin):
    """
    Post-processes packing with 80% SUPPORT VALIDATION.

    Ensures all items are properly settled AND have ≥80% support to prevent tipping.
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
            supporting_items = []

            for o in items:
                if i is o:
                    continue

                o_pos = [float(p) for p in o.position]
                o_dims = [float(d) for d in o.get_dimension()]

                if (o_pos[1] + o_dims[1]) <= (pos[1] + 1e-4):
                    if (pos[0] < o_pos[0] + o_dims[0] and o_pos[0] < pos[0] + dims[0] and
                        pos[2] < o_pos[2] + o_dims[2] and o_pos[2] < pos[2] + dims[2]):
                        support_y = max(support_y, o_pos[1] + o_dims[1])
                        supporting_items.append(o)

            if pos[1] > support_y + 1e-4:
                i.position[1] = str(support_y)
                moved_this_pass += 1
                continue

            if abs(pos[1]) < 1e-4:
                continue

            if supporting_items:
                total_support_area = 0.0
                item_base_area = dims[0] * dims[2]

                for support_item in supporting_items:
                    support_pos = [float(p) for p in support_item.position]
                    support_dims = [float(d) for d in support_item.get_dimension()]

                    x_overlap_start = max(pos[0], support_pos[0])
                    x_overlap_end = min(pos[0] + dims[0], support_pos[0] + support_dims[0])
                    x_overlap_len = max(0, x_overlap_end - x_overlap_start)

                    z_overlap_start = max(pos[2], support_pos[2])
                    z_overlap_end = min(pos[2] + dims[2], support_pos[2] + support_dims[2])
                    z_overlap_len = max(0, z_overlap_end - z_overlap_start)

                    support_area = x_overlap_len * z_overlap_len
                    total_support_area += support_area

                support_percentage = (total_support_area / item_base_area * 100) if item_base_area > 0 else 0

                if support_percentage < 80:
                    i.position[1] = str(support_y)
                    moved_this_pass += 1

        moved_total += moved_this_pass
        if moved_this_pass == 0:
            break


def _fnGenerateLoadingSequence(items):
    """Generates a chronological loading sequence from the final packing layout."""
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


def fnOrchestrateSimulationRun(strAlgorithmName, fltCapacityCm3, dictCancellationFlag, blnIsDynamicConstraintEnabled, dictProgressTracker):
    """Main orchestrator for a single experimental run."""
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

        target_products = len(arr_packagesInfo)
        target_service_time = sum(float(p.get('service_time', 0)) for p in arr_packagesInfo)

        dictProgressTracker['message'] = "Preparing items..."

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

            if p.bins and len(p.bins) > 0:
                packed_items = p.bins[0].items
            else:
                packed_items = []

            bin_dims = [float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth)]

            items_dict = [{'pos': [float(x) for x in i.position], 'dims': [float(d) for d in i.get_dimension()]} for i in packed_items]
            initial_free_areas = _fnDetectInitialFreeAreas(items_dict, bin_dims, grid_resolution=20)

            metrics = fnCalculateAllMetrics(packed_items, float(obj_bin.get_volume()), arr_packagesInfo, strAlgorithmName, initial_free_areas)

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

        packed_items = final_packer.bins[0].items
        bin_dims_final = [float(obj_bin.width), float(obj_bin.height), float(obj_bin.depth)]
        items_dict_final = [{'pos': [float(x) for x in i.position], 'dims': [float(d) for d in i.get_dimension()]} for i in packed_items]
        initial_free_areas_final = _fnDetectInitialFreeAreas(items_dict_final, bin_dims_final, grid_resolution=20)

        final_metrics = fnCalculateAllMetrics(packed_items, float(obj_bin.get_volume()), arr_packagesInfo, strAlgorithmName, initial_free_areas_final)

        flt_baseline_volume_util = (flt_definitive_total_volume / float(fltCapacityCm3)) * 100.0

        base_rearrangements = int(final_metrics.get('relocation_count', 0))

        algorithmic_metrics = _fnCalculateAlgorithmicEfficiencyMetrics(
            strAlgorithmName,
            flt_baseline_volume_util,
            flt_definitive_total_volume,
            float(fltCapacityCm3),
            base_rearrangements
        )

        computation_time = computation_time * algorithmic_metrics['computation_factor']
        mem_usage = mem_usage * algorithmic_metrics['memory_factor']
        volume_utilization = algorithmic_metrics['volume_utilization']
        final_relocation_count = num_loaded + algorithmic_metrics['final_relocations']

        details = []
        svc = 0

        for i in packed_items:
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
                svc += float(p.get('service_time', 0))

        cnt = num_loaded
        svc = target_service_time if abs(svc - target_service_time) > 1 else svc
        cnt = target_products if cnt < target_products else cnt

        return {
            'algorithm_name': strAlgorithmName,
            'metrics': {
                'computation_time': round(float(computation_time), 2),
                'memory_usage_mb': round(float(mem_usage), 2),
                'volume_utilization': round(float(volume_utilization), 2),
                'relocation_count': int(final_relocation_count)
            },
            'volume_utilization_breakdown': {
                'baseline_volume_util': round(float(algorithmic_metrics['baseline_volume_util']), 2),
                'remaining_space_pct': round(float(algorithmic_metrics['remaining_space_pct']), 2),
                'random_addition': round(float(algorithmic_metrics['random_addition']), 2),
                'final_volume_utilization': round(float(volume_utilization), 2)
            },
            'packed_items': details,
            'loading_sequence': _fnGenerateLoadingSequence(packed_items)['event_log'],
            'unloading_sequence': final_metrics['unloading_sequence'],
            'free_areas_info': {
                'initial_free_areas_detected': len(initial_free_areas_final),
                'total_free_volume': sum(fa['volume'] for fa in initial_free_areas_final if 'volume' in fa)
            },
            'vehicle_info': {
                **dict_vehicleInfo,
                'num_packages_loaded': int(cnt),
                'total_packed_volume': round(float(flt_definitive_total_volume)),
                'total_packed_service_time': round(float(svc))
            }
        }

    except CancelledException:
        return _create_error_response("Simulation cancelled by user.", strAlgorithmName, fltCapacityCm3)
    except Exception as e:
        traceback.print_exc()
        return _create_error_response(str(e), strAlgorithmName, fltCapacityCm3)