/***
 * System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
 * Module Name: Frontend Logic
 *
 * Purpose of this file:
 * Manages all client-side interactivity. This includes handling user input
 * (algorithm/vehicle selection), asynchronously fetching data from the
 * backend, triggering simulations, polling for status updates, and
 * populating the UI with the final experimental results and metrics.
 *
 * Author/s:
 * ALFARO, ABRAM S.
 * BUNAO, JOHN GLAY C.
 * DELA CRUZ, JUAN GABRIEL D.
 * ERFE, JEFFERSON B.
 * ESTONILO, JULIUS EVAN C.
 */
document.addEventListener("DOMContentLoaded", () => {

    // --- GLOBAL STATE VARIABLES ---
    // These variables maintain the state of the user's selections and the application's current operations.
    let g_str_selectedAlgorithm = "PSO";       // Stores the currently selected algorithm (e.g., "PSO", "ACO").
    let g_str_selectedCapacity = null;       // Stores the currently selected vehicle capacity in cm³.
    let g_arr_allLoadedPackages = [];          // Caches the package data for the selected capacity.
    let g_str_currentLoadId = null;            // Tracks the unique ID of the active data-loading job.
    let g_obj_loadPollingInterval = null;      // Holds the interval timer for checking data-load status.
    let g_str_currentSimulationId = null;      // Tracks the unique ID of the active simulation job.
    let g_obj_simPollingInterval = null;       // Holds the interval timer for checking simulation status.
    let g_bln_loadCancellationRequested = false; // A flag for immediate UI feedback when data loading is cancelled.
    let g_bln_simCancellationRequested = false;  // A flag for immediate UI feedback when simulation is cancelled.

    // --- DOM ELEMENT REFERENCES ---
    // Caching references to frequently accessed DOM elements improves performance and code readability.
    const obj_modal = document.getElementById("myModal");
    const obj_openModalBtn = document.getElementById("openModalBtn");
    const obj_closeModalBtn = document.getElementById("closeModalBtn");
    const obj_runSimBtn = document.getElementById("run-sim-btn");
    const obj_loader = document.getElementById("loader");
    const obj_clearSimBtn = document.getElementById("clear-sim-btn");
    const obj_cancelLoadBtn = document.getElementById('cancel-load-btn');
    const obj_cancelSimBtn = document.getElementById('cancel-sim-btn');
    const arr_algoButtons = document.querySelectorAll(".modal-options button");
    const obj_capacitySelect = document.getElementById("vehicle-capacity-select");
    const obj_initialTableBody = document.getElementById('initial-item-table-body');
    const obj_dynamicConstraintToggle = document.getElementById('dynamic-constraint-toggle');

    // --- INITIALIZATION ---
    // This function is called once the page is fully loaded to populate the initial UI elements.
    _fnLoadInitialCapacities();

    /**
     * Asynchronously fetches the list of all available vehicle capacities from the backend.
     * This is done after the page loads to avoid blocking the initial render, improving perceived performance.
     */
    async function _fnLoadInitialCapacities() {
        console.log("Requesting vehicle capacity list from server...");
        obj_capacitySelect.disabled = true; // Disable dropdown while loading.
        const loadingOption = new Option("Loading vehicles...", "", true, true);
        loadingOption.disabled = true;
        obj_capacitySelect.add(loadingOption);
        try {
            const response = await fetch('/get_all_capacities');
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();

            // Clear the "Loading..." message and populate with real data.
            obj_capacitySelect.innerHTML = '<option value="" disabled selected>Select Vehicle Capacity</option>';
            data.capacities.forEach(capacity => {
                const option = document.createElement('option');
                option.value = capacity;
                option.textContent = Number(capacity).toLocaleString(); // Format for readability.
                obj_capacitySelect.appendChild(option);
            });
            console.log("Successfully loaded vehicle capacities.");
        } catch (error) {
            console.error("Failed to load vehicle capacities:", error);
            obj_capacitySelect.innerHTML = '<option value="" disabled selected>Error loading vehicles</option>';
        } finally {
            obj_capacitySelect.disabled = false; // Re-enable dropdown regardless of outcome.
        }
    }

    // --- EVENT LISTENERS ---
    // Binds user actions (clicks, selections) to their corresponding handler functions.
    obj_openModalBtn.onclick = () => { obj_modal.style.display = "flex"; };
    obj_closeModalBtn.onclick = () => { obj_modal.style.display = "none"; };
    window.onclick = (e) => { if (e.target === obj_modal) { obj_modal.style.display = "none"; }};
    obj_clearSimBtn.addEventListener("click", () => { location.reload(); }); // Resets the application.
    obj_cancelLoadBtn.addEventListener('click', () => { _fnCancelDataLoading(); });
    obj_cancelSimBtn.addEventListener('click', () => { _fnCancelSimulation(); });
    obj_runSimBtn.addEventListener("click", () => { _fnStartSimulation(); });
    
    // Handles algorithm selection in the modal.
    arr_algoButtons.forEach(button => {
        button.addEventListener("click", () => {
            arr_algoButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");
            g_str_selectedAlgorithm = button.getAttribute("data-algo");
        });
    });

    // Triggers the data loading process when a new vehicle capacity is selected.
    obj_capacitySelect.addEventListener("change", (e) => {
        g_str_selectedCapacity = e.target.value;
        if (g_str_selectedCapacity) {
            _fnStartLoadingDisplayData(g_str_selectedCapacity);
        }
    });

    // --- ASYNCHRONOUS LOGIC FUNCTIONS ---

    /**
     * Initiates the data loading process on the backend for a selected vehicle capacity.
     * This function does NOT wait for completion; it starts the job and begins polling for status.
     * @param {string} strCapacity The selected vehicle capacity.
     */
    async function _fnStartLoadingDisplayData(strCapacity) {
        g_bln_loadCancellationRequested = false; // Reset cancellation flag for the new job.
        obj_runSimBtn.disabled = true;
        _fnResetInitialUI();
        _fnShowLoader("Starting data load...", { showLoadCancel: true, loadCancelDisabled: true });
        try {
            const response = await fetch('/start_data_loading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: strCapacity })
            });
            const data = await response.json();
            if (data.status === 'started') {
                g_str_currentLoadId = data.load_id;
                obj_cancelLoadBtn.disabled = false; // Enable cancel button now that we have an ID.
                g_obj_loadPollingInterval = setInterval(_fnCheckLoadStatus, 1500); // Start polling.
            } else {
                throw new Error("Failed to start data loading on the server.");
            }
        } catch (error) {
            console.error("Error starting data load:", error);
            alert(`Could not start data load: ${error.message}`);
            _fnHideLoader();
        }
    }

    /**
     * Periodically polls the backend to check the status of the ongoing data loading job.
     * It handles 'completed', 'error', and 'cancelled' states.
     */
    async function _fnCheckLoadStatus() {
        // If user clicked "Cancel", immediately stop sending polling requests.
        if (g_bln_loadCancellationRequested) {
            clearInterval(g_obj_loadPollingInterval);
            return;
        }
        if (!g_str_currentLoadId) return;

        _fnShowLoader(`Loading sample route data...`, { showLoadCancel: true });
        
        try {
            const response = await fetch(`/data_loading_status/${g_str_currentLoadId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();
            
            // Handle the final "completed" state.
            if (data.status === 'completed') {
                clearInterval(g_obj_loadPollingInterval); // Stop polling.
                const result = data.result;
                // Populate the UI with the loaded data.
                document.getElementById('initial-vehicle-volume').textContent = _fnFormatNumber(result.vehicle.capacity_cm3);
                if (result.packages && result.packages.length > 0) {
                    _fnAppendPackagesToTable(result.packages);
                    g_arr_allLoadedPackages = result.packages; // Cache the data.
                    _fnUpdateInitialSummary(result.vehicle.total_package_volume, result.packages.length, result.vehicle.total_service_time);
                }
                obj_runSimBtn.disabled = false; // Enable the simulate button.
                _fnHideLoader();
            } else if (data.status === 'error') {
                clearInterval(g_obj_loadPollingInterval);
                alert(`Data Loading Error: ${data.result.error}`);
                _fnResetInitialUI();
                _fnHideLoader();
            } else if (data.status === 'cancelled') {
                 // The backend confirmed the cancellation.
                 clearInterval(g_obj_loadPollingInterval);
                 _fnResetInitialUI();
                 obj_runSimBtn.disabled = true;
                 _fnHideLoader();
            }
            // If status is 'running', this function will simply exit and be called again on the next interval.
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_loadPollingInterval);
             alert("Lost connection with the server during data load.");
             obj_runSimBtn.disabled = true;
             _fnHideLoader();
        }
    }

    /**
     * Sends a cancellation request to the backend for the current data loading job.
     */
    async function _fnCancelDataLoading() {
        if (!g_str_currentLoadId) return;
        
        // 1. Set the local flag for immediate UI feedback.
        g_bln_loadCancellationRequested = true;
        obj_cancelLoadBtn.disabled = true;
        _fnShowLoader('Cancellation requested. Terminating process… Please wait.', { showLoadCancel: false });
        
        try {
            // 2. Send the non-blocking cancellation request to the backend.
            fetch(`/cancel_data_loading/${g_str_currentLoadId}`, { method: 'POST' });
            
            // 3. Stop the main poller and start a "cleanup" poller to wait for the final status.
            clearInterval(g_obj_loadPollingInterval);
            const cleanupInterval = setInterval(async () => {
                const response = await fetch(`/data_loading_status/${g_str_currentLoadId}`);
                const data = await response.json();
                if (['cancelled', 'error', 'not_found'].includes(data.status)) {
                    clearInterval(cleanupInterval);
                    alert("Data loading has been cancelled.");
                    _fnResetInitialUI();
                    _fnHideLoader();
                }
            }, 2000);
        } catch (error) {
            console.error("Failed to send data load cancel request:", error);
            _fnHideLoader();
        }
    }

    /**
     * Initiates the simulation process on the backend.
     */
    async function _fnStartSimulation() {
        g_bln_simCancellationRequested = false;
        if (!g_str_selectedCapacity || g_arr_allLoadedPackages.length === 0) {
            alert("Please select a vehicle capacity and wait for its data to load first.");
            return;
        }
        
        // Read the state of the new toggle switch.
        const bln_isDynamicConstraintEnabled = obj_dynamicConstraintToggle.checked;
        
        obj_modal.style.display = "none";
        _fnShowLoader("Starting simulation...", { showSimCancel: true, simCancelDisabled: true });
        
        try {
            const response = await fetch('/start_simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    algorithm: g_str_selectedAlgorithm, 
                    capacity: g_str_selectedCapacity,
                    dynamic_constraint_enabled: bln_isDynamicConstraintEnabled // Send toggle state to backend
                }),
            });
            const data = await response.json();
            if (data.status === 'started') {
                g_str_currentSimulationId = data.simulation_id;
                obj_cancelSimBtn.disabled = false;
                g_obj_simPollingInterval = setInterval(_fnCheckSimulationStatus, 2000); // Start polling.
            } else { throw new Error("Failed to start simulation on the server."); }
        } catch (error) {
            console.error("Error starting simulation:", error);
            alert(`Could not start simulation: ${error.message}`);
            _fnHideLoader();
        }
    }

    /**
     * Periodically polls the backend to check the status of the ongoing simulation job.
     */
    async function _fnCheckSimulationStatus() {
        if (g_bln_simCancellationRequested) {
            clearInterval(g_obj_simPollingInterval);
            return;
        }
        if (!g_str_currentSimulationId) return;

        _fnShowLoader(`Simulation in progress… Please wait.`, { showSimCancel: false });
        try {
            const response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();
            
            // Handle final states.
            if (data.status === 'completed') {
                clearInterval(g_obj_simPollingInterval);
                _fnUpdateResultsUI(data.result); // Populate the results panel.
                _fnHideLoader();
            } else if (data.status === 'error') {
                clearInterval(g_obj_simPollingInterval);
                alert(`Simulation Error: ${data.result.error}`);
                _fnHideLoader();
            }
             // If status is 'running', do nothing and wait for the next interval.
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_simPollingInterval);
             alert("Lost connection with the server.");
             _fnHideLoader();
        }
    }
    
    /**
     * Sends a cancellation request to the backend for the current simulation job.
     */
    async function _fnCancelSimulation() {
        if (!g_str_currentSimulationId) return;
        g_bln_simCancellationRequested = true;
        obj_cancelSimBtn.disabled = true;
        _fnShowLoader('Cancellation requested. Terminating process… Please wait.', { showSimCancel: false });
        try {
            fetch(`/cancel_simulation/${g_str_currentSimulationId}`, { method: 'POST' });
            
            // Start cleanup poller.
            clearInterval(g_obj_simPollingInterval);
            const cleanupInterval = setInterval(async () => {
                 const response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
                 const data = await response.json();
                 if (['cancelled', 'error', 'not_found'].includes(data.status)) {
                     clearInterval(cleanupInterval);
                     alert("Simulation has been cancelled.");
                     _fnHideLoader();
                 }
            }, 1500);
        } catch (error) {
            console.error("Failed to send simulation cancel request:", error);
            _fnHideLoader();
        }
    }
    
    // --- UI HELPER FUNCTIONS ---
    
    /**
     * Displays the loading spinner modal with a custom message and button configuration.
     * @param {string} strMessage - The message to display.
     * @param {object} options - Configuration for displaying cancel buttons.
     */
    function _fnShowLoader(strMessage = "Processing...", options = {}) {
        obj_loader.querySelector('p').textContent = strMessage;
        obj_cancelLoadBtn.style.display = options.showLoadCancel ? 'block' : 'none';
        obj_cancelSimBtn.style.display = options.showSimCancel ? 'block' : 'none';
        if (options.showSimCancel) { obj_cancelSimBtn.disabled = !!options.simCancelDisabled; }
        if (options.showLoadCancel) { obj_cancelLoadBtn.disabled = !!options.loadCancelDisabled; }
        obj_loader.style.display = 'flex';
    }

    /** Hides the loading spinner modal. */
    function _fnHideLoader() {
        obj_cancelLoadBtn.style.display = 'none';
        obj_cancelSimBtn.style.display = 'none';
        obj_loader.style.display = 'none';
    }

    /** Clears all displayed data from the initial data panel (left side). */
    function _fnResetInitialUI() {
        obj_initialTableBody.innerHTML = '';
        g_arr_allLoadedPackages = [];
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        document.getElementById('initial-no-item').style.display = 'block';
    }

    /**
     * Updates the summary cards in the initial data panel.
     * @param {number} fltVolume - Total package volume.
     * @param {number} intCount - Total number of packages.
     * @param {number} fltServiceTime - Total service time.
     */
    function _fnUpdateInitialSummary(fltVolume, intCount, fltServiceTime) {
        document.getElementById('initial-product-volume').textContent = _fnFormatNumber(Math.round(fltVolume));
        document.getElementById('initial-product-count').textContent = _fnFormatNumber(intCount);
        document.getElementById('initial-service-time').textContent = _fnFormatNumber(Math.round(fltServiceTime));
    }

    /**
     * Populates the initial items table with package data.
     * @param {Array<object>} arrPackages - An array of package objects.
     */
    function _fnAppendPackagesToTable(arrPackages) {
        if (arrPackages && arrPackages.length > 0) {
            document.getElementById('initial-no-item').style.display = 'none';
            obj_initialTableBody.innerHTML = arrPackages.map(_fnCreateTableRow).join('');
        }
    }

    /**
     * Creates the HTML string for a single table row.
     * @param {object} objPkg - A single package object.
     * @returns {string} The HTML `<tr>` string.
     */
    function _fnCreateTableRow(objPkg) {
        return `
            <tr>
                <td>${objPkg.id}</td>
                <td>${_fnFormatNumber(Math.round(objPkg.volume))}</td>
                <td>${objPkg.service_time}</td>
                <td>${objPkg.height}</td>
                <td>${objPkg.depth}</td>
                <td>${objPkg.width}</td>
            </tr>`;
    }

    /**
     * Formats a number with commas for thousands separation.
     * @param {number} numValue - The number to format.
     * @returns {string} The formatted number string.
     */
    function _fnFormatNumber(numValue) {
        return numValue ? numValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : '0';
    }

    /**
     * Populates the entire results panel (right side) with the data from a completed simulation.
     * @param {object} objResults - The full results object from the backend.
     */
    function _fnUpdateResultsUI(objResults) {
        // Update result summary cards
        document.getElementById('result-algorithm-name').textContent = objResults.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = _fnFormatNumber(objResults.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = _fnFormatNumber(objResults.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = objResults.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = _fnFormatNumber(objResults.vehicle_info.total_packed_service_time);

        // Update all performance metrics from the results
        const { metrics } = objResults;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;
        document.getElementById('metric-feasibility').textContent = metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = metrics.unloading_sequence_length;

        // Update the packed items table
        const tableBody = document.getElementById('result-item-table-body');
        const noItemText = document.getElementById('result-no-item');
        tableBody.innerHTML = ''; // Clear previous results
        if (objResults.packed_items && objResults.packed_items.length > 0) {
            noItemText.style.display = 'none';
            tableBody.innerHTML = objResults.packed_items.map(_fnCreateTableRow).join('');
        } else {
            noItemText.style.display = 'block';
        }
    }
});