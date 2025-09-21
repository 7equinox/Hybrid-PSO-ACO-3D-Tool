document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    // A centralized place to hold references to all interactive or updatable UI elements.
    const ui = {
        // Modal elements
        modal: document.getElementById('myModal'),
        openModalBtn: document.getElementById('openModalBtn'),
        closeModalBtn: document.getElementById('closeModalBtn'),
        algorithmButtons: document.querySelectorAll('.modal-options button'),
        capacitySelect: document.getElementById('capacity-select'),
        runSimBtn: document.getElementById('runSimBtn'),
        clearSimBtn: document.getElementById('clearSimBtn'),
        // Initial data panel (left)
        initial: {
            capacity: document.querySelector('[data-id="initial-vehicle-capacity"]'),
            totalVolume: document.querySelector('[data-id="initial-total-volume"]'),
            productCount: document.querySelector('[data-id="initial-product-count"]'),
            serviceTime: document.querySelector('[data-id="initial-service-time"]'),
            itemTable: document.querySelector('[data-id="initial-item-table"]'),
            noItemMsg: document.querySelector('[data-id="initial-no-item-msg"]'),
        },
        // Results panel (right)
        results: {
            algorithmName: document.querySelector('[data-id="algorithm-name"]'),
            capacity: document.querySelector('[data-id="result-vehicle-capacity"]'),
            totalVolume: document.querySelector('[data-id="result-total-volume"]'),
            productCount: document.querySelector('[data-id="result-product-count"]'),
            serviceTime: document.querySelector('[data-id="result-service-time"]'),
            itemTable: document.querySelector('[data-id="result-item-table"]'),
            noItemMsg: document.querySelector('[data-id="result-no-item-msg"]'),
        },
        // Metrics display
        metrics: {
            execTime: document.querySelector('[data-id="metric-exec-time"]'),
            memUsage: document.querySelector('[data-id="metric-mem-usage"]'),
            volUtil: document.querySelector('[data-id="metric-vol-util"]'),
            relocCount: document.querySelector('[data-id="metric-reloc-count"]'),
            feasibility: document.querySelector('[data-id="metric-feasibility"]'),
            seqLength: document.querySelector('[data-id="metric-seq-length"]'),
        },
    };

    // --- Application State ---
    // A simple object to store the current user selections.
    let simulationState = {
        selectedAlgorithm: 'PSO',
        selectedCapacity: null,
    };

    // --- Helper Functions ---
    /**
     * Updates a table body with a list of item data.
     * @param {HTMLElement} tableBody - The <tbody> element to update.
     * @param {Array<Object>} items - An array of item objects.
     * @param {HTMLElement} noItemMsgEl - The "no items" message element.
     */
    const updateItemTable = (tableBody, items, noItemMsgEl) => {
        tableBody.innerHTML = ''; // Clear previous content
        if (items && items.length > 0) {
            noItemMsgEl.style.display = 'none';
            items.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.id}</td>
                    <td>${item.volume}</td>
                    <td>${item.service_time}</td>
                    <td>${item.height}</td>
                    <td>${item.length}</td>
                    <td>${item.width}</td>
                `;
                tableBody.appendChild(row);
            });
        } else {
            noItemMsgEl.style.display = 'block';
        }
    };
    
    /**
     * Clears all displayed data from both initial and results panels.
     */
    const clearAllDisplays = () => {
        // Clear initial panel
        ui.initial.capacity.textContent = '0';
        ui.initial.totalVolume.textContent = '0';
        ui.initial.productCount.textContent = '0';
        ui.initial.serviceTime.textContent = '0';
        updateItemTable(ui.initial.itemTable, [], ui.initial.noItemMsg);
        ui.initial.noItemMsg.textContent = 'SELECT A VEHICLE TO VIEW ITEMS';


        // Clear results panel
        ui.results.algorithmName.textContent = 'N/A';
        ui.results.capacity.textContent = '0';
        ui.results.totalVolume.textContent = '0';
        ui.results.productCount.textContent = '0';
        ui.results.serviceTime.textContent = '0';
        updateItemTable(ui.results.itemTable, [], ui.results.noItemMsg);

        // Clear metrics
        ui.metrics.execTime.textContent = '0';
        ui.metrics.memUsage.textContent = '0';
        ui.metrics.volUtil.textContent = '0';
        ui.metrics.relocCount.textContent = '0';
        ui.metrics.feasibility.textContent = 'N/A';
        ui.metrics.seqLength.textContent = '0';
    };


    // --- API Communication Functions ---
    /**
     * Fetches the list of unique vehicle capacities from the backend and populates the dropdown.
     */
    const fetchAndPopulateCapacities = async () => {
        try {
            const response = await fetch('/api/capacities');
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const capacities = await response.json();
            
            ui.capacitySelect.innerHTML = '<option value="" selected disabled>Select Vehicle Capacity...</option>'; // Reset
            capacities.forEach(cap => {
                const option = document.createElement('option');
                option.value = cap;
                option.textContent = cap;
                ui.capacitySelect.appendChild(option);
            });
        } catch (error) {
            console.error("Failed to fetch vehicle capacities:", error);
            alert("Error: Could not load vehicle capacities from the server.");
        }
    };

    /**
     * Fetches the initial package and route data for the selected capacity.
     */
    const fetchInitialData = async () => {
        if (!simulationState.selectedCapacity) return;

        try {
            const response = await fetch('/api/initial-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: simulationState.selectedCapacity }),
            });

            if (!response.ok) throw new Error('Failed to fetch initial data.');
            const data = await response.json();
            
            // Update the UI with the fetched data
            ui.initial.capacity.textContent = data.vehicle_capacity || 0;
            ui.initial.totalVolume.textContent = data.total_product_volume || 0;
            ui.initial.productCount.textContent = data.number_of_products || 0;
            ui.initial.serviceTime.textContent = data.total_service_time || 0;
            updateItemTable(ui.initial.itemTable, data.items, ui.initial.noItemMsg);

        } catch (error) {
            console.error("Error fetching initial data:", error);
        }
    };
    
    /**
     * Sends the simulation request to the backend and updates the UI with the results.
     */
    const runSimulation = async () => {
        if (!simulationState.selectedAlgorithm || !simulationState.selectedCapacity) {
            alert("Please select both an algorithm and a vehicle capacity.");
            return;
        }

        // --- Visual Feedback for User ---
        ui.modal.style.display = 'none'; // Close modal
        document.body.style.cursor = 'wait'; // Show loading cursor
        ui.runSimBtn.disabled = true;
        ui.runSimBtn.textContent = 'Simulating...';


        try {
            // This is the object with the CORRECT keys that the backend expects.
            const requestBody = {
                algorithm: simulationState.selectedAlgorithm,
                capacity: simulationState.selectedCapacity
            };

            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // OLD LINE: body: JSON.stringify(simulationState),
                // NEW, CORRECTED LINE:
                body: JSON.stringify(requestBody), 
            });
            const results = await response.json();

            if (!response.ok || results.error) {
                throw new Error(results.error || `Simulation failed with status: ${response.status}`);
            }

            // --- Update UI with simulation results ---
            // Summary banner
            ui.results.algorithmName.textContent = simulationState.selectedAlgorithm;
            ui.results.capacity.textContent = results.solution_summary.vehicle_capacity || 0;
            ui.results.totalVolume.textContent = results.solution_summary.total_product_volume || 0;
            ui.results.productCount.textContent = results.solution_summary.number_of_products_loaded || 0;
            ui.results.serviceTime.textContent = results.solution_summary.total_service_time || 0;
            
            // Metrics
            ui.metrics.execTime.textContent = results.metrics.execution_time;
            ui.metrics.memUsage.textContent = results.metrics.memory_usage;
            ui.metrics.volUtil.textContent = results.metrics.volume_utilization;
            ui.metrics.relocCount.textContent = results.metrics.relocation_count;
            ui.metrics.feasibility.textContent = results.metrics.unloading_feasibility;
            ui.metrics.seqLength.textContent = results.metrics.unloading_sequence_length;

            // Loaded items table
            updateItemTable(ui.results.itemTable, results.loaded_items, ui.results.noItemMsg);
            
        } catch (error) {
            console.error("Simulation error:", error);
            alert(`An error occurred during the simulation: ${error.message}`);
        } finally {
            // --- Restore UI after simulation ---
            document.body.style.cursor = 'default';
            ui.runSimBtn.disabled = false;
            ui.runSimBtn.textContent = 'Simulate';
        }
    };


    // --- Event Listeners Setup ---
    // Modal controls
    ui.openModalBtn.onclick = () => ui.modal.style.display = 'flex';
    ui.closeModalBtn.onclick = () => ui.modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target === ui.modal) ui.modal.style.display = 'none';
    };

    // Algorithm selection
    ui.algorithmButtons.forEach(button => {
        button.addEventListener('click', () => {
            ui.algorithmButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            simulationState.selectedAlgorithm = button.getAttribute('data-algo');
        });
    });

    // Capacity selection
    ui.capacitySelect.addEventListener('change', (event) => {
        simulationState.selectedCapacity = parseFloat(event.target.value);
        fetchInitialData(); // Load initial data for the left panel upon selection
    });
    
    // Simulation execution
    ui.runSimBtn.addEventListener('click', runSimulation);
    ui.clearSimBtn.addEventListener('click', () => {
        clearAllDisplays();
        ui.capacitySelect.selectedIndex = 0; // Reset dropdown
        simulationState.selectedCapacity = null;
        ui.modal.style.display = 'none'; // Close modal after clearing
    });

    // --- Initial Application Load ---
    fetchAndPopulateCapacities();
});