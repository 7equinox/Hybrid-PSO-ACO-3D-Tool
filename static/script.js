/***
 * System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
 * Module Name: Frontend Logic
 *
 * Purpose of this file:
 * Manages all client-side interactivity for the user interface. This includes
 * handling user inputs (algorithm/vehicle selection), fetching data from the
 * backend, incrementally loading and displaying problem instances, triggering
 * simulations, and populating the UI with the final results and metrics.
 *
 * Author/s:
 * ALFARO, ABRAM S.
 * BUNAO, JOHN GLAY C.
 * DELA CRUZ, JUAN GABRIEL D.
 * ERFE, JEFFERSON B.
 * ESTONILO, JULIUS EVAN C.
 *
 */
document.addEventListener("DOMContentLoaded", () => {

    // --- GLOBAL STATE VARIABLES ---
    // These variables maintain the state of the user's selections and loaded data.
    let g_str_selectedAlgorithm = "PSO";
    let g_str_selectedCapacity = null;
    let g_arr_allLoadedPackages = [];
    let g_bln_isLoadCancelled = false;

    // NEW: Variables for tracking the async simulation task.
    let g_str_currentSimulationId = null;
    let g_obj_pollingInterval = null;

    // --- DOM ELEMENT REFERENCES ---
    // Caching references to DOM elements improves performance and code readability.
    const obj_modal = document.getElementById("myModal");
    const obj_openModalBtn = document.getElementById("openModalBtn");
    const obj_closeModalBtn = document.getElementById("closeModalBtn");
    const obj_runSimBtn = document.getElementById("run-sim-btn");
    const obj_loader = document.getElementById("loader");
    const obj_clearSimBtn = document.getElementById("clear-sim-btn");

     // NEW: Get references to BOTH cancel buttons.
    const obj_cancelLoadBtn = document.getElementById('cancel-load-btn');
    const obj_cancelSimBtn = document.getElementById('cancel-sim-btn');

    const arr_algoButtons = document.querySelectorAll(".modal-options button");
    const obj_capacitySelect = document.getElementById("vehicle-capacity-select");
    const obj_initialTableBody = document.getElementById('initial-item-table-body');


    // --- EVENT LISTENERS INITIALIZATION ---
    // Binds user actions (clicks, changes) to their corresponding functions.

    /**
    * Opens the simulation settings modal when the gear icon is clicked.
    */
    obj_openModalBtn.onclick = () => {
        obj_modal.style.display = "flex";
    };

    /**
    * Closes the simulation settings modal.
    */
    obj_closeModalBtn.onclick = () => {
        obj_modal.style.display = "none";
    };

    /**
    * Allows closing the modal by clicking outside of its content area.
    */
    window.onclick = (obj_event) => {
        if (obj_event.target === obj_modal) {
            obj_modal.style.display = "none";
        }
    };

    /**
    * Attaches a click handler to each algorithm button (PSO, ACO, PSO-ACO)
    * to update the selected algorithm state.
    */
    arr_algoButtons.forEach(obj_button => {
        obj_button.addEventListener("click", () => {
            arr_algoButtons.forEach(btn => btn.classList.remove("active"));
            obj_button.classList.add("active");
            g_str_selectedAlgorithm = obj_button.getAttribute("data-algo");
        });
    });

    /**
    * Triggers the data loading process when the user selects a new vehicle capacity.
    */
    obj_capacitySelect.addEventListener("change", (obj_event) => {
        g_str_selectedCapacity = obj_event.target.value;
        if (g_str_selectedCapacity) {
            // It now calls the correct function for loading display data.
            _loadDisplayData(g_str_selectedCapacity);
        }
    });
    /**
    * Sets the cancellation flag when the "Cancel" button in the loader is clicked.
    */
    obj_cancelLoadBtn.addEventListener('click', () => { g_bln_isLoadCancelled = true; });

    // NEW: Cancel SIMULATION
    obj_cancelSimBtn.addEventListener('click', () => { _cancelSimulation(); });

    /**
    * Initiates the simulation process when the "Simulate" button is clicked.
    */
    obj_runSimBtn.addEventListener("click", () => { _startSimulation(); });

    /**
    * Clears all data and reloads the page to start a new experiment.
    */
    obj_clearSimBtn.addEventListener("click", () => {
        location.reload();
    });


    // --- CORE LOGIC FUNCTIONS ---

    /**
    * NEW & CORRECTED: Fetches and displays data for a single, valid sample route.
    * @param {string} str_capacity - The selected vehicle capacity in cm³.
    */
    async function _loadDisplayData(str_capacity) {
        _showLoader("Loading sample route data...", { showLoadCancel: true });
        _resetInitialUI();
        g_bln_isLoadCancelled = false; // Reset the cancel flag

        try {
            const obj_response = await fetch('/get_vehicle_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: str_capacity }) // No page number needed
            });

            if (!obj_response.ok) {
                const err_data = await obj_response.json();
                throw new Error(err_data.error || `Server error: ${obj_response.statusText}`);
            }

            const obj_data = await obj_response.json();
            
            document.getElementById('initial-vehicle-volume').textContent = _formatNumber(obj_data.vehicle.capacity_cm3);
            
            if (obj_data.packages && obj_data.packages.length > 0) {
                _appendPackagesToTable(obj_data.packages);
                g_arr_allLoadedPackages = obj_data.packages; // Store the packages
                
                _updateInitialSummary(
                    obj_data.vehicle.total_package_volume,
                    obj_data.packages.length,
                    obj_data.vehicle.total_service_time
                );
            }
        } catch (obj_error) {
            console.error("Failed to load display data:", obj_error);
            alert(`Could not load sample route: ${obj_error.message}`);
            _resetInitialUI();
        } finally {
            _hideLoader();
        }
    }

    /**
    * STARTS the simulation by calling the backend to create a background thread.
    */
    async function _startSimulation() {
        if (!g_str_selectedCapacity) {
            alert("Please select a vehicle capacity first.");
            return;
        }
        if (g_arr_allLoadedPackages.length === 0) {
            alert("Please wait for the sample data to load before simulating.");
            return;
        }

        obj_modal.style.display = "none";
        // Show the simulation cancel button.
        _showLoader("Starting simulation...", { showSimCancel: true, simCancelDisabled: true });

        try {
            const obj_response = await fetch('/start_simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    algorithm: g_str_selectedAlgorithm,
                    capacity: g_str_selectedCapacity
                }),
            });

            const obj_data = await obj_response.json();
            if (obj_data.status === 'started') {
                g_str_currentSimulationId = obj_data.simulation_id;
                // FIX: NOW that we have an ID, ENABLE the cancel button.
                obj_cancelSimBtn.disabled = false;
                // Start polling every 2 seconds
                g_obj_pollingInterval = setInterval(_checkSimulationStatus, 2000);
            } else {
                throw new Error("Failed to start simulation on the server.");
            }
        } catch (obj_error) {
            console.error("Error starting simulation:", obj_error);
            alert(`Could not start simulation: ${obj_error.message}`);
            _hideLoader();
        }
    }

    /**
    * Periodically checks the status of the running simulation.
    */
    async function _checkSimulationStatus() {
        if (!g_str_currentSimulationId) return;
        
        _showLoader(`Running simulation... (ID: ${g_str_currentSimulationId})`, { showSimCancel: true });

        try {
            const obj_response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
            if (!obj_response.ok) { // Handles cases where the server restarts mid-simulation
                throw new Error(`Server status check failed: ${obj_response.statusText}`);
            }
            const obj_data = await obj_response.json();
            if (obj_data.status === 'completed') {
                clearInterval(g_obj_pollingInterval);
                _updateResultsUI(obj_data.result);
                _hideLoader();
                g_str_currentSimulationId = null;
            } else if (obj_data.status === 'error') {
                clearInterval(g_obj_pollingInterval);
                alert(`Simulation Error: ${obj_data.result.error}`);
                _hideLoader();
                g_str_currentSimulationId = null;
            } else if (obj_data.status === 'cancelled') {
                 clearInterval(g_obj_pollingInterval);
                 alert("Simulation has been cancelled.");
                 _hideLoader();
                 g_str_currentSimulationId = null;
            }
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_pollingInterval);
             alert("Lost connection with the server.");
             _hideLoader();
             g_str_currentSimulationId = null;
        }
    }
    
    /**
     * Sends a cancel request to the backend for the current simulation.
     */
    async function _cancelSimulation() {
        if (!g_str_currentSimulationId) return;

        console.log(`Sending cancel request for ${g_str_currentSimulationId}`);
        // FIX: Disable the button immediately to prevent multiple clicks.
        obj_cancelSimBtn.disabled = true;
        _showLoader('Cancelling simulation...', { showSimCancel: false }); // Hide button after click

        try {
            await fetch(`/cancel_simulation/${g_str_currentSimulationId}`, { method: 'POST' });
        } catch (obj_error) {
            console.error("Failed to send cancel request:", obj_error);
            // The polling will eventually handle the UI cleanup even if this fails.
        }
    }

    // --- UI HELPER FUNCTIONS ---
    // These functions manipulate the DOM to display data and feedback to the user.

    /**
    * MODIFIED: Shows the loader and conditionally displays cancel buttons.
    */
    function _showLoader(str_message = "Processing...", options = {}) {
        obj_loader.querySelector('p').textContent = str_message;
        obj_cancelLoadBtn.style.display = options.showLoadCancel ? 'block' : 'none';
        
        // Handle simulation cancel button visibility and state
        obj_cancelSimBtn.style.display = options.showSimCancel ? 'block' : 'none';
        if (options.showSimCancel) {
            obj_cancelSimBtn.disabled = !!options.simCancelDisabled;
        }

        obj_loader.style.display = 'flex';
    }

    /**
    * Hides the loading spinner.
    */
    function _hideLoader() {
        // Ensure both buttons are hidden when the loader is hidden.
        obj_cancelLoadBtn.style.display = 'none';
        obj_cancelSimBtn.style.display = 'none';
        obj_loader.style.display = 'none';
    }

    /**
    * Clears the initial data display section on the left.
    */
    function _resetInitialUI() {
        obj_initialTableBody.innerHTML = '';
        g_arr_allLoadedPackages = [];
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        document.getElementById('initial-no-item').style.display = 'block';
    }

    /**
    * Updates the summary cards in the initial data section.
    * @param {number} flt_volume - The total volume of loaded packages.
    * @param {number} int_count - The total number of loaded packages.
    * @param {number} flt_serviceTime - The total service time of loaded packages.
    */
    function _updateInitialSummary(flt_volume, int_count, flt_serviceTime) {
        document.getElementById('initial-product-volume').textContent = _formatNumber(Math.round(flt_volume));
        document.getElementById('initial-product-count').textContent = _formatNumber(int_count);
        document.getElementById('initial-service-time').textContent = _formatNumber(Math.round(flt_serviceTime));
    }

    /**
    * Adds new rows of package data to the initial items table.
    * @param {Array<Object>} arr_packages - An array of package objects to add.
    */
    function _appendPackagesToTable(arr_packages) {
        const obj_noItemText = document.getElementById('initial-no-item');
        if (arr_packages && arr_packages.length > 0) {
            obj_noItemText.style.display = 'none';
            let str_rowsHtml = '';
            arr_packages.forEach(obj_pkg => {
                str_rowsHtml += _createTableRow(obj_pkg);
            });
            obj_initialTableBody.innerHTML += str_rowsHtml;
        }
    }

    /**
    * Creates the HTML string for a single table row.
    * @param {Object} obj_pkg - The package object containing item details.
    * @returns {string} The HTML string for the `<tr>` element.
    */
    function _createTableRow(obj_pkg) {
        return `
            <tr>
                <td>${obj_pkg.id}</td>
                <td>${_formatNumber(Math.round(obj_pkg.volume))}</td>
                <td>${obj_pkg.service_time}</td>
                <td>${obj_pkg.height}</td>
                <td>${obj_pkg.depth}</td>
                <td>${obj_pkg.width}</td>
            </tr>
        `;
    }

    /**
    * Formats a number with commas as thousands separators.
    * @param {number} num_value - The number to format.
    * @returns {string} The formatted number as a string.
    */
    function _formatNumber(num_value) {
        if (num_value === null || num_value === undefined) {
            return '0';
        }
        return num_value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
    * Populates the entire right-hand section of the UI with the final simulation results.
    * This corresponds to the 'Post-Experimentation' stage where data is presented.
    * @param {Object} obj_results - The results object from the backend.
    */
    function _updateResultsUI(obj_results) {
        // Update result summary cards
        document.getElementById('result-algorithm-name').textContent = obj_results.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = _formatNumber(obj_results.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = _formatNumber(obj_results.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = obj_results.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = _formatNumber(obj_results.vehicle_info.total_packed_service_time);

        // Update all metrics
        const obj_metrics = obj_results.metrics;
        document.getElementById('metric-exec-time').textContent = obj_metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = obj_metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = obj_metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = obj_metrics.relocation_count;
        document.getElementById('metric-feasibility').textContent = obj_metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = obj_metrics.unloading_sequence_length;

        // Update the packed items table
        const obj_tableBody = document.getElementById('result-item-table-body');
        const obj_noItemText = document.getElementById('result-no-item');
        obj_tableBody.innerHTML = ''; // Clear previous results
        if (obj_results.packed_items && obj_results.packed_items.length > 0) {
            obj_noItemText.style.display = 'none';
            obj_results.packed_items.forEach(obj_pkg => {
                obj_tableBody.innerHTML += _createTableRow(obj_pkg);
            });
        } else {
            obj_noItemText.style.display = 'block';
        }
    }

}); // End of DOMContentLoaded