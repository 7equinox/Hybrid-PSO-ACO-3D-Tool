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

    // NEW: Separate tracking variables for data loading and simulation.
    let g_str_currentLoadId = null;
    let g_obj_loadPollingInterval = null;
    let g_str_currentSimulationId = null;
    let g_obj_simPollingInterval = null;

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

    // NEW: State flags to prevent the polling function from overwriting our "cancelling" message.
    let g_bln_load_cancellation_requested = false;
    let g_bln_sim_cancellation_requested = false;

    // --- INITIALIZATION ---
    // This is the new entry point for all page logic.
    _loadInitialCapacities();

    /**
     * NEW: Fetches the vehicle capacity list from the new dedicated endpoint
     * and populates the dropdown select menu.
     */
    async function _loadInitialCapacities() {
        console.log("Requesting vehicle capacity list from server...");
        // You can add a visual indicator here, e.g., disabling the select box
        obj_capacitySelect.disabled = true;
        // Add a temporary "Loading..." option
        const loadingOption = new Option("Loading vehicles...", "", true, true);
        loadingOption.disabled = true;
        obj_capacitySelect.add(loadingOption);

        try {
            const response = await fetch('/get_all_capacities');
            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }
            const data = await response.json();
            
            // Clear the "Loading..." message
            obj_capacitySelect.innerHTML = '<option value="" disabled selected>Select Vehicle Capacity</option>';

            // Populate the dropdown with the fetched capacities
            data.capacities.forEach(capacity => {
                const option = document.createElement('option');
                option.value = capacity;
                // Simple formatting for the display text
                option.textContent = Number(capacity).toLocaleString();
                obj_capacitySelect.appendChild(option);
            });
            console.log("Successfully loaded vehicle capacities.");

        } catch (error) {
            console.error("Failed to load vehicle capacities:", error);
            // Show an error state in the dropdown
            obj_capacitySelect.innerHTML = '<option value="" disabled selected>Error loading vehicles</option>';
        } finally {
            // Re-enable the select box regardless of success or failure
            obj_capacitySelect.disabled = false;
        }
    }

    // --- EVENT LISTENERS ---
    obj_openModalBtn.onclick = () => { obj_modal.style.display = "flex"; };
    obj_closeModalBtn.onclick = () => { obj_modal.style.display = "none"; };
    window.onclick = (e) => { if (e.target === obj_modal) { obj_modal.style.display = "none"; }};
    obj_clearSimBtn.addEventListener("click", () => { location.reload(); });
    
    arr_algoButtons.forEach(button => {
        button.addEventListener("click", () => {
            arr_algoButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");
            g_str_selectedAlgorithm = button.getAttribute("data-algo");
        });
    });

    obj_capacitySelect.addEventListener("change", (e) => {
        g_str_selectedCapacity = e.target.value;
        if (g_str_selectedCapacity) {
            _startLoadingDisplayData(g_str_selectedCapacity);
        }
    });
    
    // MODIFIED: Attach listeners to the correct async cancellation functions.
    obj_cancelLoadBtn.addEventListener('click', () => { _cancelDataLoading(); });
    obj_cancelSimBtn.addEventListener('click', () => { _cancelSimulation(); });
    obj_runSimBtn.addEventListener("click", () => { _startSimulation(); });

    /**
    * Clears all data and reloads the page to start a new experiment.
    */
    obj_clearSimBtn.addEventListener("click", () => {
        location.reload();
    });


    // --- CORE LOGIC FUNCTIONS ---

    /**
    * NEW: Starts the ASYNCHRONOUS data loading process.
    */
    async function _startLoadingDisplayData(str_capacity) {
        // Reset the cancellation flag at the start of a new job.
        g_bln_load_cancellation_requested = false;
        
        obj_runSimBtn.disabled = true;
        _resetInitialUI();
        _showLoader("Starting data load...", { showLoadCancel: true, loadCancelDisabled: true });

        try {
            const response = await fetch('/start_data_loading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: str_capacity })
            });
            const data = await response.json();
            if (data.status === 'started') {
                g_str_currentLoadId = data.load_id;
                obj_cancelLoadBtn.disabled = false; // Enable cancel button now that we have an ID
                g_obj_loadPollingInterval = setInterval(_checkLoadStatus, 2000);
            } else {
                throw new Error("Failed to start data loading on the server.");
            }
        } catch (error) {
            console.error("Error starting data load:", error);
            alert(`Could not start data load: ${error.message}`);
            _hideLoader();
        }
    }

    /**
     * NEW: Periodically checks the status of the running data load job.
     */
    async function _checkLoadStatus() {
        // If a cancellation has already been sent from the UI, STOP POLLING.
        // This prevents the "Loading..." message from reappearing.
        if (g_bln_load_cancellation_requested) {
            // We can even add logic here to forcefully stop the interval
            // after a timeout if the backend doesn't respond.
            // For now, simply stopping the UI updates is enough.
            clearInterval(g_obj_loadPollingInterval);
            return;
        }

        if (!g_str_currentLoadId) return;

        _showLoader(`Loading sample route data...`, { showLoadCancel: true });
        
        try {
            const response = await fetch(`/data_loading_status/${g_str_currentLoadId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            
            const data = await response.json();
            
            if (data.status === 'completed') {
                clearInterval(g_obj_loadPollingInterval);
                const result = data.result;
                document.getElementById('initial-vehicle-volume').textContent = _formatNumber(result.vehicle.capacity_cm3);
                if (result.packages && result.packages.length > 0) {
                    _appendPackagesToTable(result.packages);
                    g_arr_allLoadedPackages = result.packages;
                    _updateInitialSummary(result.vehicle.total_package_volume, result.packages.length, result.vehicle.total_service_time);
                }
                // IMPROVEMENT: Only enable the simulate button on SUCCESS.
                obj_runSimBtn.disabled = false;
                _hideLoader();
            } else if (data.status === 'error') {
                clearInterval(g_obj_loadPollingInterval);
                alert(`Data Loading Error: ${data.result.error}`);
                _resetInitialUI();
                _hideLoader();
            } else if (data.status === 'cancelled') {
                 clearInterval(g_obj_loadPollingInterval);
                 alert("Data loading has been cancelled.");
                 _resetInitialUI();
                 // Keep the simulate button disabled
                 obj_runSimBtn.disabled = true;
                 _hideLoader();
            }
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_loadPollingInterval);
             alert("Lost connection with the server during data load.");
             obj_runSimBtn.disabled = true; // Also disable on connection error
             _hideLoader();
        }
    }

    async function _cancelDataLoading() {
        if (!g_str_currentLoadId) return;

        // 1. SET THE FLAG FIRST. This is the most critical step.
        g_bln_load_cancellation_requested = true;
        
        obj_cancelLoadBtn.disabled = true;

        // 2. Give INSTANT UI feedback. This message will now "stick".
        _showLoader('Cancellation signal sent. Process will terminate shortly...', { showLoadCancel: false });
        
        try {
            // 3. Send the request. We don't even need to wait for it.
            //    The backend will eventually catch up.
            fetch(`/cancel_data_loading/${g_str_currentLoadId}`, { method: 'POST' });

            // 4. Restart a slower, "cleanup" poller. This poller will wait for the final
            //    "cancelled" state from the backend to hide the loader and show the alert.
            //    This is more robust than letting the fast poller continue.
            clearInterval(g_obj_loadPollingInterval); // Stop the old poller
            const cleanupInterval = setInterval(async () => {
                const response = await fetch(`/data_loading_status/${g_str_currentLoadId}`);
                const data = await response.json();
                if (data.status === 'cancelled' || data.status === 'error') {
                    clearInterval(cleanupInterval);
                    alert("Data loading has been cancelled.");
                    _resetInitialUI();
                    _hideLoader();
                }
            }, 2000); // Check every 2 seconds

        } catch (error) {
            console.error("Failed to send data load cancel request:", error);
            _hideLoader();
        }
    }

   /**
    * STARTS the simulation by calling the backend to create a background thread.
    */
    async function _startSimulation() {
        // Reset the cancellation flag at the start of a new job.
        g_bln_sim_cancellation_requested = false;

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
                // #FIX: Use the correct variable name `g_obj_simPollingInterval`.
                g_obj_simPollingInterval = setInterval(_checkSimulationStatus, 2000);
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
        // If a cancellation has already been sent, STOP POLLING.
        // This prevents the "Running simulation..." message from reappearing.
        if (g_bln_sim_cancellation_requested) {
            clearInterval(g_obj_simPollingInterval);
            return;
        }

        if (!g_str_currentSimulationId) return;
        
        _showLoader(`Running simulation... (ID: ${g_str_currentSimulationId.substring(0,8)})`, { showSimCancel: true });

        try {
            obj_cancelSimBtn.style.display = 'none';

            const obj_response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
            if (!obj_response.ok) { // Handles cases where the server restarts mid-simulation
                throw new Error(`Server status check failed: ${obj_response.statusText}`);
            }
            const obj_data = await obj_response.json();
            
            if (obj_data.status === 'completed') {
                // #FIX: Use the correct variable name `g_obj_simPollingInterval`.
                clearInterval(g_obj_simPollingInterval);
                _updateResultsUI(obj_data.result);
                _hideLoader();
                g_str_currentSimulationId = null;
            } else if (obj_data.status === 'error') {
                // #FIX: Use the correct variable name `g_obj_simPollingInterval`.
                clearInterval(g_obj_simPollingInterval);
                alert(`Simulation Error: ${obj_data.result.error}`);
                _hideLoader();
                g_str_currentSimulationId = null;
            }
        } catch (error) {
             console.error("Polling error:", error);
             // #FIX: Use the correct variable name `g_obj_simPollingInterval`.
             clearInterval(g_obj_simPollingInterval);
             alert("Lost connection with the server.");
             _hideLoader();
             g_str_currentSimulationId = null;
        }
    }
    
    async function _cancelSimulation() {
        if (!g_str_currentSimulationId) return;

        // 1. SET THE FLAG.
        g_bln_sim_cancellation_requested = true;

        obj_cancelSimBtn.disabled = true;

        // 2. Give INSTANT UI feedback.
        _showLoader('Cancellation signal sent. Simulation will terminate shortly...', { showSimCancel: false });

        try {
            // 3. Send the request.
            fetch(`/cancel_simulation/${g_str_currentSimulationId}`, { method: 'POST' });

            // 4. Start the cleanup poller.
            clearInterval(g_obj_simPollingInterval);
            const cleanupInterval = setInterval(async () => {
                 const response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
                 const data = await response.json();
                 if (data.status === 'cancelled' || data.status === 'error') {
                     clearInterval(cleanupInterval);
                     alert("Simulation has been cancelled.");
                     _hideLoader();
                 }
            }, 1500); // Check every 1.5 seconds

        } catch (error) {
            console.error("Failed to send simulation cancel request:", error);
            _hideLoader();
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