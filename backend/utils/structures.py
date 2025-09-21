# This file contains shared data structures to avoid circular imports.

class Bin:
    """
    A simulation of a 3D container (e.g., a delivery vehicle) to hold packed items.
    This class is a placeholder for the core functionality of a real 3D packing library
    like Py3dbp, focusing on the data structure aspects needed for the algorithms.
    """
    def __init__(self, width, height, depth, capacity):
        self.width = width
        self.height = height
        self.depth = depth
        self.capacity = capacity
        # 'items' will store the packed item dictionaries along with their calculated positions.
        self.items = []

    def pack_items(self, items_to_pack):
        """
        Simulates packing a list of items into the bin based on a simple volume-first heuristic.
        The packing order is critical and is determined by the algorithm's solution sequence.
        
        In a real implementation, this method would contain complex geometric calculations
        to determine the optimal (x, y, z) coordinates for each item without overlap.
        For this research tool, we simplify this by just checking against total volume,
        as the core of the study is the optimization of the *sequence*, not the packing geometry itself.
        """
        current_volume = 0
        self.items = [] # Reset the bin before each new packing attempt

        for item in items_to_pack:
            # Check if adding the next item would exceed the vehicle's capacity.
            if current_volume + item.get('volume', 0) <= self.capacity:
                # Assign a placeholder position. In a real 3D packer, this would be
                # the output of a complex placement algorithm (e.g., finding the best corner).
                item_copy = item.copy() # Use a copy to avoid modifying original item lists
                item_copy['position'] = (0, 0, current_volume / (self.width * self.depth if self.width * self.depth > 0 else 1))
                self.items.append(item_copy)
                current_volume += item_copy['volume']
            else:
                # If the item doesn't fit, the packing for this sequence stops here.
                # This naturally penalizes solutions that try to pack more than the container can hold.
                break