/**
 * System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
 * Module Name: Frontend User Interface Logic
 *
 * Purpose of this file:
 * This script is the "brain" of the user interface. It manages all client-side
 * interactivity and communication with the backend server. Its primary duties include:
 *   1. Handling user inputs, like algorithm and vehicle selections.
 *   2. Asynchronously requesting data from the server without freezing the page.
 *   3. Initiating simulation jobs on the backend.
 *   4. Periodically checking the status of those jobs for progress updates.
 *   5. Displaying the final, detailed results of the experiment to the user.
 *
 * Author/s:
 * ALFARO, ABRAM S.
 * BUNAO, JOHN GLAY C.
 * DELA CRUZ, JUAN GABRIEL D.
 * ERFE, JEFFERSON B.
 * ESTONILO, JULIUS EVAN C.
 */

// This special command ensures that our code only runs after the entire HTML page has been fully loaded and is ready.
document.addEventListener("DOMContentLoaded", () => 
{
    // --- GLOBAL STATE VARIABLES ---
    // These variables act as the application's memory on the user's browser. They keep track of
    // important information like user selections and the status of ongoing processes. The 'g_'
    // prefix signifies that they are global, accessible from anywhere within this script.

    // Remembers which algorithm the user has selected (e.g., "PSO"). Starts with "PSO" by default.
    let g_strSelectedAlgorithm = "PSO";
    // Stores the vehicle capacity (size) the user chooses from the dropdown menu.
    let g_strSelectedCapacity = null;
    // Holds the complete list of packages for the selected vehicle, once loaded from the server.
    let g_arrAllLoadedPackages = [];
    // Stores the unique ID for the current data-loading process, used to track its status.
    let g_strCurrentLoadId = null;
    // A timer that repeatedly asks the server for the status of the data loading job.
    let g_objLoadPollingInterval = null;
    // Stores the unique ID for the current simulation run, used for status tracking.
    let g_strCurrentSimulationId = null;
    // A timer that repeatedly asks the server for the simulation's progress.
    let g_objSimPollingInterval = null;
    // A flag to know if the user has requested to cancel the data loading process.
    let g_blnLoadCancellationRequested = false;
    // A flag to know if the user has requested to cancel the simulation process.
    let g_blnSimCancellationRequested = false;
    // Caches the most recent simulation results to be used for the 3D visualization.
    let g_objLastResults = null;


    // --- DOM ELEMENT REFERENCES ---
    // To work with HTML elements (like buttons and text fields), we need to get a reference to them.
    // We store these references in constants (variables that don't change) for easy and efficient access.

    // References to the main simulation configuration modal (pop-up window) and its buttons.
    const g_objConfigModal = document.getElementById("myModal");
    const g_objOpenModalBtn = document.getElementById("openModalBtn");
    const g_objCloseModalBtn = document.getElementById("closeModalBtn");
    const g_objRunSimBtn = document.getElementById("run-sim-btn");
    const g_objClearSimBtn = document.getElementById("clear-sim-btn");
    
    // References to the loading spinner modal and its cancel buttons.
    const g_objLoaderModal = document.getElementById("loader");
    const g_objCancelLoadBtn = document.getElementById('cancel-load-btn');
    const g_objCancelSimBtn = document.getElementById('cancel-sim-btn');
    
    // References to other interactive elements in the simulation modal.
    const g_arrAlgoButtons = document.querySelectorAll(".modal-options button");
    const g_objCapacitySelect = document.getElementById("vehicle-capacity-select");
    const g_objDynamicConstraintToggle = document.getElementById('dynamic-constraint-toggle');
    
    // Reference to the table body where initial package data is displayed.
    const g_objInitialTableBody = document.getElementById('initial-item-table-body');
    
    // --- MODIFICATION ---
    // References for the new visualization dropdown menu
    const g_objVisualizeMenu = document.getElementById('visualize-menu');
    const g_objVisualizeMenuBtn = document.getElementById('visualize-menu-btn');
    const g_objVisualizeDropdown = document.getElementById('visualize-dropdown-content');
    const g_objVizStaticBtn = document.getElementById('viz-static-btn');
    const g_objVizLoadAnimBtn = document.getElementById('viz-load-anim-btn');
    // const g_objVizUnloadAnimBtn = document.getElementById('viz-unload-anim-btn');
    
    // References to the user guide modal and its buttons.
    const g_objGuidesModal = document.getElementById("guidesModal");
    const g_objOpenGuidesBtn = document.getElementById("openGuidesBtn");
    const g_objCloseGuidesBtn = document.getElementById("closeGuidesBtn");
    const g_objGotItBtn = document.getElementById("gotItBtn");


    // --- INITIALIZATION ---
    // This is the first function that runs when the script starts. Its job is to prepare the page.
    _loadInitialCapacities();
    

    /**
     * This function asks the backend server for the list of all available vehicle capacities (sizes).
     * It runs automatically when the page loads, filling the dropdown menu for the user.
     * The `async` keyword means this function can perform network requests without freezing the webpage.
     */
    async function _loadInitialCapacities()
    {
        // Log a message to the browser's console for debugging purposes.
        console.log("Requesting vehicle capacity list from server...");
        
        // Temporarily disable the dropdown menu to prevent clicks while it's loading.
        g_objCapacitySelect.disabled = true;
        
        // Show a "Loading..." message in the dropdown.
        const loadingOption = new Option("Loading vehicles...", "", true, true);
        loadingOption.disabled = true;
        g_objCapacitySelect.add(loadingOption);

        // A try...catch block is used to gracefully handle any network errors that might occur.
        try 
        {
            // The 'fetch' command sends an HTTP GET request to our server's '/get_all_capacities' endpoint.
            const response = await fetch('/get_all_capacities');
            
            // If the server response is not "OK" (e.g., an error occurred on the server), we raise an error.
            if (!response.ok) 
            {
                throw new Error(`Server error: ${response.statusText}`);
            }

            // We parse the JSON data returned by the server, which contains the list of capacities.
            const data = await response.json();

            // Clear the "Loading..." message from the dropdown.
            g_objCapacitySelect.innerHTML = '<option value="" disabled selected>Select Vehicle Capacity</option>';
            
            // Loop through each capacity received from the server and add it as a new option to the dropdown.
            data.capacities.forEach(capacity => 
            {
                const option = document.createElement('option');
                option.value = capacity;
                // We format the number with commas (e.g., 4,672,279.5) to make it easier to read.
                option.textContent = Number(capacity).toLocaleString();
                g_objCapacitySelect.appendChild(option);
            });
            console.log("Successfully loaded vehicle capacities.");
        }
        catch (error) 
        {
            // If an error occurred during the fetch, we log it and show an error message in the dropdown.
            console.error("Failed to load vehicle capacities:", error);
            g_objCapacitySelect.innerHTML = '<option value="" disabled selected>Error loading vehicles</option>';
        }
        finally 
        {
            // This 'finally' block ensures that the dropdown is re-enabled, regardless of whether the fetch succeeded or failed.
            g_objCapacitySelect.disabled = false;
        }
    }


    // --- EVENT LISTENERS ---
    // These blocks of code "listen" for user actions (like clicks) and then trigger specific functions in response.

    // When the "Modify Simulation" button is clicked, display the configuration modal.
    g_objOpenModalBtn.onclick = () => { g_objConfigModal.style.display = "flex"; };

    // When the 'X' button inside the modal is clicked, hide the modal.
    g_objCloseModalBtn.onclick = () => { g_objConfigModal.style.display = "none"; };
    
    // When the "User Guide" button is clicked, display the guides modal.
    g_objOpenGuidesBtn.onclick = () => { g_objGuidesModal.style.display = "flex"; };
    
    // When the 'X' button inside the guides modal is clicked, hide it.
    g_objCloseGuidesBtn.onclick = () => { g_objGuidesModal.style.display = "none"; };
    
    // When the "Got It!" button inside the guides modal is clicked, hide it.
    g_objGotItBtn.onclick = () => { g_objGuidesModal.style.display = "none"; };
    
    // --- MODIFICATION: Event listeners for the new visualization dropdown ---
    g_objVisualizeMenuBtn.addEventListener('click', () => {
        g_objVisualizeDropdown.classList.toggle('show-dropdown');
    });

    g_objVizStaticBtn.addEventListener('click', (e) => {
        e.preventDefault();
        _openVisualizationWindow('static');
        g_objVisualizeDropdown.classList.remove('show-dropdown');
    });

    g_objVizLoadAnimBtn.addEventListener('click', (e) => {
        e.preventDefault();
        _openVisualizationWindow('load');
        g_objVisualizeDropdown.classList.remove('show-dropdown');
    });

    // g_objVizUnloadAnimBtn.addEventListener('click', (e) => {
    //     e.preventDefault();
    //     _openVisualizationWindow('unload');
    //     g_objVisualizeDropdown.classList.remove('show-dropdown');
    // });

    // This allows the user to close a modal by clicking on the dark background area outside of it.
    window.onclick = (event) => 
    { 
        if (event.target === g_objConfigModal) { g_objConfigModal.style.display = "none"; }
        if (event.target === g_objGuidesModal) { g_objGuidesModal.style.display = "none"; }
        // Close dropdown if clicked outside
        if (!event.target.matches('.visualize-btn, .visualize-btn *')) {
            if (g_objVisualizeDropdown.classList.contains('show-dropdown')) {
                g_objVisualizeDropdown.classList.remove('show-dropdown');
            }
        }
    };
    
    // When the "Clear Simulation" button is clicked, simply reload the entire page to reset everything.
    g_objClearSimBtn.addEventListener("click", () => { location.reload(); });
    
    // Listen for clicks on the cancel buttons within the loader.
    g_objCancelLoadBtn.addEventListener('click', () => { _cancelDataLoading(); });
    g_objCancelSimBtn.addEventListener('click', () => { _cancelSimulation(); });

    // When the "Simulate" button is clicked, start the simulation process.
    g_objRunSimBtn.addEventListener("click", () => { _startSimulation(); });
    
    // This loop sets up the click behavior for the three algorithm selection buttons.
    g_arrAlgoButtons.forEach(button => 
    {
        button.addEventListener("click", () => 
        {
            // First, remove the "active" style from all algorithm buttons.
            g_arrAlgoButtons.forEach(btn => btn.classList.remove("active"));
            
            // Then, add the "active" style to the specific button that was clicked.
            button.classList.add("active");
            
            // Finally, update the global state variable to remember which algorithm is now selected.
            g_strSelectedAlgorithm = button.getAttribute("data-algo");
        });
    });

    // When the user chooses a new vehicle from the dropdown...
    g_objCapacitySelect.addEventListener("change", (event) => 
    {
        // Get the value of the selected option and store it.
        g_strSelectedCapacity = event.target.value;

        // If a valid capacity was selected (not the placeholder)...
        if (g_strSelectedCapacity) 
        {
            // Start the process of loading the corresponding package data from the server.
            _startLoadingDisplayData(g_strSelectedCapacity);
        }
    });


    // --- ASYNCHRONOUS DATA AND SIMULATION FUNCTIONS ---

    /**
     * Initiates the data loading process on the server for a specific vehicle capacity.
     * It does not wait for the data; instead, it gets a job ID and starts polling.
     */
    async function _startLoadingDisplayData(strCapacity) 
    {
        g_blnLoadCancellationRequested = false; 
        g_objRunSimBtn.disabled = true; // Disable the "Simulate" button while data is loading.
        _resetInitialUI(); // Clear any old data from the left panel.
        _showLoader("Starting data load...", { showLoadCancel: true, loadCancelDisabled: false }); // Show the loader.

        try 
        {
            // Send a POST request to the server to kick off the background data loading job.
            const response = await fetch('/start_data_loading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: strCapacity })
            });

            // Parse the server's immediate response.
            const data = await response.json();
            
            // If the server confirms the job has started...
            if (data.status === 'started') 
            {
                g_strCurrentLoadId = data.load_id; // Store the unique job ID.
                g_objCancelLoadBtn.disabled = false; // The cancel button can now be used.
                // Start a timer to call '_checkLoadStatus' every 1.5 seconds to get updates.
                g_objLoadPollingInterval = setInterval(_checkLoadStatus, 1500);
            } 
            else 
            {
                // If the job couldn't start, throw an error.
                throw new Error("Failed to start data loading on the server.");
            }
        } 
        catch (error) 
        {
            // Handle any errors that occurred while trying to start the job.
            console.error("Error starting data load:", error);
            alert(`Could not start data load: ${error.message}`);
            _hideLoader(); // Hide the loader if something went wrong.
        }
    }

    /**
     * This function is called repeatedly by a timer to ask the server for the status
     * of the ongoing data loading job.
     */
    async function _checkLoadStatus() 
    {
        // If the user requested to cancel or if there's no active job, stop checking.
        if (g_blnLoadCancellationRequested || !g_strCurrentLoadId) 
        {
            clearInterval(g_objLoadPollingInterval);
            return;
        }
        
        // Update the loader message.
        _showLoader(`Loading sample route data...`, { showLoadCancel: true });
        
        try 
        {
            // Fetch the status from the server using the current job ID.
            const response = await fetch(`/data_loading_status/${g_strCurrentLoadId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();
            
            // --- Check the status received from the server ---
            if (data.status === 'completed') 
            {
                clearInterval(g_objLoadPollingInterval); // Stop the timer.
                const result = data.result; // Get the loaded data.
                // Update the UI on the left panel with the new data.
                document.getElementById('initial-vehicle-volume').textContent = _formatNumber(result.vehicle.capacity_cm3);
                if (result.packages && result.packages.length > 0) 
                {
                    _appendPackagesToTable(g_objInitialTableBody, result.packages);
                    g_arrAllLoadedPackages = result.packages; // Store the packages globally.
                    _updateInitialSummary(result.vehicle.total_package_volume, result.packages.length, result.vehicle.total_service_time);
                }
                g_objRunSimBtn.disabled = false; // Re-enable the "Simulate" button.
                _hideLoader(); // Hide the loader.
            }
            else if (data.status === 'error')
            {
                clearInterval(g_objLoadPollingInterval); // Stop the timer.
                alert(`Data Loading Error: ${data.result.error}`); // Show the error message.
                _resetInitialUI(); // Clear the UI.
                _hideLoader(); // Hide the loader.
            } 
            else if (data.status === 'cancelled') 
            {
                 clearInterval(g_objLoadPollingInterval);
                 _resetInitialUI();
                 g_objRunSimBtn.disabled = true; // Keep the simulate button disabled.
                 _hideLoader();
            }
            // If the status is still 'running', this function will simply run again on the next interval.
        } 
        catch (error) 
        {
             console.error("Polling error:", error);
             clearInterval(g_objLoadPollingInterval);
             alert("Lost connection with the server during data load.");
             g_objRunSimBtn.disabled = true;
             _hideLoader();
        }
    }
    
    /**
     * This function sends a request to the server to cancel the currently active data loading job.
     */
    async function _cancelDataLoading() 
    {
        if (!g_strCurrentLoadId) return; // Do nothing if there's no job to cancel.
        g_blnLoadCancellationRequested = true; // Set the flag to stop polling immediately.
        g_objCancelLoadBtn.disabled = true; // Disable the cancel button to prevent multiple clicks.
        _showLoader('Cancellation requested... Please wait.', { showLoadCancel: false });
        
        try 
        {
            // Send the cancellation request to the server. We don't need to wait for a response here.
            fetch(`/cancel_data_loading/${g_strCurrentLoadId}`, { method: 'POST' });
            
            // Stop the main polling timer.
            clearInterval(g_objLoadPollingInterval);
            
            // Start a new, temporary timer to confirm when the server process has fully stopped.
            const cleanupInterval = setInterval(async () => {
                const response = await fetch(`/data_loading_status/${g_strCurrentLoadId}`);
                const data = await response.json();
                
                // Once the server confirms the job is 'cancelled', 'error', or 'not_found', we can stop checking.
                if (['cancelled', 'error', 'not_found'].includes(data.status)) 
                {
                    clearInterval(cleanupInterval);
                    alert("Data loading has been cancelled.");
                    _resetInitialUI(); // Reset the left panel.
                    _hideLoader(); // Hide the loader.
                }
            }, 2000);
        }
        catch (error) 
        {
            console.error("Failed to send data load cancel request:", error);
            _hideLoader();
        }
    }


    /**
     * Gathers all user selections and sends a request to the server to start the main simulation.
     */
    async function _startSimulation() 
    {
        g_blnSimCancellationRequested = false; // Reset the simulation cancellation flag.

        // First, check if the necessary data is ready.
        if (!g_strSelectedCapacity || g_arrAllLoadedPackages.length === 0) 
        {
            alert("Please select a vehicle capacity and wait for its data to load first.");
            return;
        }
        
        // Check the state of the "Enable Dynamic Constraint" toggle switch.
        const blnIsDynamicConstraintEnabled = g_objDynamicConstraintToggle.checked;
        
        // Hide the configuration modal and show the loader.
        g_objConfigModal.style.display = "none";
        _showLoader("Starting simulation...", { showSimCancel: true, simCancelDisabled: false });
        
        try 
        {
            // Send a POST request to the server with all the simulation parameters.
            const response = await fetch('/start_simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    algorithm: g_strSelectedAlgorithm, 
                    capacity: g_strSelectedCapacity,
                    dynamic_constraint_enabled: blnIsDynamicConstraintEnabled
                }),
            });
            const data = await response.json();
            
            // If the server confirms the simulation job has started...
            if (data.status === 'started') 
            {
                g_strCurrentSimulationId = data.simulation_id; // Store the new job ID.
                g_objCancelSimBtn.disabled = false; // Enable the simulation cancel button.
                // Start polling for simulation status every 2 seconds.
                g_objSimPollingInterval = setInterval(_checkSimulationStatus, 2000);
            } 
            else 
            {
                throw new Error("Failed to start simulation on the server.");
            }
        } 
        catch (error) 
        {
            console.error("Error starting simulation:", error);
            alert(`Could not start simulation: ${error.message}`);
            _hideLoader();
        }
    }


    /**
     * Periodically polls the backend to check the status and progress of the simulation job.
     */
    async function _checkSimulationStatus() 
    {
        // Stop checking if the user requested cancellation or if there is no active job ID.
        if (g_blnSimCancellationRequested || !g_strCurrentSimulationId) 
        {
            clearInterval(g_objSimPollingInterval);
            return;
        }

        try 
        {
            // Ask the server for the current status of the simulation.
            const response = await fetch(`/simulation_status/${g_strCurrentSimulationId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();

            // If the simulation is still running, update the loader with progress information.
            if (data.status === 'running' && data.progress) 
            {
                const progress = data.progress;
                // If we have generation numbers, show them.
                if (progress.total > 0) 
                {
                    _showLoader(
                        `Optimizing... (Generation ${progress.current} / ${progress.total})`, 
                        { showSimCancel: false }
                    );
                } 
                else 
                {
                    // Otherwise, show the general message from the server (e.g., "Sampling data...").
                     _showLoader(
                        progress.message || 'Simulation in progress...', 
                        { showSimCancel: true }
                     );
                }
            }
            
            // If the server reports that the simulation is complete...
            if (data.status === 'completed') 
            {
                clearInterval(g_objSimPollingInterval); // Stop polling.
                _updateResultsUI(data.result); // Update the right-hand panel with the results.
                _hideLoader(); // Hide the loader.
            } 
            else if (data.status === 'error')
            {
                clearInterval(g_objSimPollingInterval);
                alert(`Simulation Error: ${data.result.error}`);
                _hideLoader();
            } 
            else if (data.status === 'cancelled') 
            {
                 clearInterval(g_objSimPollingInterval);
                 _hideLoader();
            }
        } 
        catch (error) 
        {
             console.error("Polling error:", error);
             clearInterval(g_objSimPollingInterval);
             alert("Lost connection with the server.");
             _hideLoader();
        }
    }
    

    /**
     * This function sends a request to the server to cancel the currently active simulation job.
     */
    async function _cancelSimulation() 
    {
        if (!g_strCurrentSimulationId) return;
        g_blnSimCancellationRequested = true;
        g_objCancelSimBtn.disabled = true; // Prevent multiple clicks.
        _showLoader('Cancellation requested... Please wait.', { showSimCancel: false });
        try 
        {
            // Send the request to cancel.
            fetch(`/cancel_simulation/${g_strCurrentSimulationId}`, { method: 'POST' });
            
            // Stop the main polling timer.
            clearInterval(g_objSimPollingInterval);
            
            // Start a temporary timer to confirm when the server has finished cancelling.
            const cleanupInterval = setInterval(async () => {
                 const response = await fetch(`/simulation_status/${g_strCurrentSimulationId}`);
                 const data = await response.json();
                 if (['cancelled', 'error', 'not_found'].includes(data.status)) {
                     clearInterval(cleanupInterval);
                     alert("Simulation has been cancelled.");
                     _hideLoader();
                 }
            }, 1500);
        }
        catch (error) 
        {
            console.error("Failed to send simulation cancel request:", error);
            _hideLoader();
        }
    }
    

    // --- UI HELPER FUNCTIONS ---
    // These smaller functions are responsible for managing specific parts of the user interface.
    
    /**
     * Shows the loading spinner modal with a custom message and configured buttons.
     */
    function _showLoader(strMessage = "Processing...", objOptions = {})
    {
        g_objLoaderModal.querySelector('p').textContent = strMessage;
        g_objCancelLoadBtn.style.display = objOptions.showLoadCancel ? 'block' : 'none';
        g_objCancelSimBtn.style.display = objOptions.showSimCancel ? 'block' : 'none';
        if (objOptions.showSimCancel) { g_objCancelSimBtn.disabled = !!objOptions.simCancelDisabled; }
        if (objOptions.showLoadCancel) { g_objCancelLoadBtn.disabled = !!objOptions.loadCancelDisabled; }
        g_objLoaderModal.style.display = 'flex';
    }


    /**
     * Hides the loading spinner modal.
     */
    function _hideLoader() 
    {
        g_objCancelLoadBtn.style.display = 'none';
        g_objCancelSimBtn.style.display = 'none';
        g_objLoaderModal.style.display = 'none';
    }


    /**
     * Clears all the data displayed on the left-hand (initial data) panel.
     */
    function _resetInitialUI()
    {
        g_objInitialTableBody.innerHTML = '';
        g_arrAllLoadedPackages = [];
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        document.getElementById('initial-no-item').style.display = 'block';
    }


    /**
     * Updates the summary cards on the left panel with calculated totals.
     */
    function _updateInitialSummary(fltVolume, intCount, fltServiceTime)
    {
        document.getElementById('initial-product-volume').textContent = _formatNumber(Math.round(fltVolume));
        document.getElementById('initial-product-count').textContent = _formatNumber(intCount);
        document.getElementById('initial-service-time').textContent = _formatNumber(Math.round(fltServiceTime));
    }


    /**
     * Fills a given table with rows of package data, sorting them by ID for consistency.
     */
    function _appendPackagesToTable(tableBodyElement, arrPackages)
    {
        if (arrPackages && arrPackages.length > 0) 
        {
            const noItemElement = tableBodyElement.nextElementSibling;
            if (noItemElement && noItemElement.classList.contains('no-item')) {
                noItemElement.style.display = 'none';
            }
            
            // --- MODIFICATION ---
            // Sort packages by ID before rendering to ensure consistent table order.
            arrPackages.sort((a, b) => a.id.localeCompare(b.id));

            // The `map` function transforms each package object into an HTML table row string,
            // and `join` combines them all into one large string to update the table body.
            tableBodyElement.innerHTML = arrPackages.map(_createTableRowHTML).join('');
        }
    }


    /**
     * A helper function that creates the HTML string for a single table row.
     */
    function _createTableRowHTML(objPkg) 
    {
        return `
            <tr>
                <td>${objPkg.id}</td>
                <td>${_formatNumber(Math.round(objPkg.volume))}</td>
                <td>${objPkg.service_time}</td>
                <td>${objPkg.height}</td>
                <td>${objPkg.depth}</td>
                <td>${objPkg.width}</td>
            </tr>`;
    }

    /**
     * Takes a number and formats it with commas for better readability.
     */
    function _formatNumber(numValue)
    {
        return numValue ? numValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : '0';
    }

    /**
     * Populates the entire right-hand panel with the final results from a simulation.
     */
    function _updateResultsUI(objResults) 
    {
        g_objLastResults = objResults; // Cache the full results object.
        g_objVisualizeMenu.style.display = 'none'; // Hide the visualize menu initially.

        // Update the summary cards on the right panel.
        document.getElementById('result-algorithm-name').textContent = objResults.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = _formatNumber(objResults.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = _formatNumber(objResults.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = objResults.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = _formatNumber(objResults.vehicle_info.total_packed_service_time);

        // Update the detailed performance metrics.
        const { metrics } = objResults;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;

        // Populate the "Packed Items" table.
        const objResultTableBody = document.getElementById('result-item-table-body');
        const objNoItemText = document.getElementById('result-no-item');
        objResultTableBody.innerHTML = ''; 
        if (objResults.packed_items && objResults.packed_items.length > 0)
        {
            objNoItemText.style.display = 'none';
            // Use the consistent table appending function
            _appendPackagesToTable(objResultTableBody, objResults.packed_items);
            
            // --- MODIFICATION ---
            // Only show the "Visualize Result" dropdown if there are items to show.
            g_objVisualizeMenu.style.display = 'inline-flex';
        } 
        else
        {
            objNoItemText.style.display = 'block';
        }
    }


/**
 * This function is responsible for creating and opening the interactive 3D visualization.
 * It dynamically generates a complete HTML file as a string, injects the necessary
 * simulation data into it, and then opens this generated content in a new browser window.
 * This has been refactored to handle static, loading, and unloading modes.
 */
function _openVisualizationWindow(mode = 'static')
{
    if (!g_objLastResults) 
    {
        alert("No simulation data available to visualize.");
        return;
    }

    const { vehicle_info, packed_items, metrics, loading_sequence, unloading_sequence } = g_objLastResults;
    
    const strHtmlContent = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>3D Packing Visualization</title>
            <style>
                body { margin: 0; overflow: hidden; font-family: sans-serif; background-color: #282c34; color: white; }
                canvas { display: block; }
                .info-panel {
                    position: absolute; padding: 10px; background: rgba(0, 0, 0, 0.7);
                    border-radius: 5px; font-size: 14px; line-height: 1.5;
                    border: 1px solid #555;
                }
                #item-info-panel { left: 10px; top: 10px; display: none; }
                #item-info-panel strong { color: #e08128; }
                #controls-panel { right: 10px; top: 10px; text-align: right; }
                #animation-panel { 
                    display: ${mode === 'static' ? 'none' : 'block'};
                    left: 10px; bottom: 10px; width: calc(100% - 20px);
                }
                .anim-controls { display: flex; align-items: center; gap: 15px; margin-top: 5px; }
                .anim-controls button, .controls-btn {
                    padding: 8px 12px; background: #333; color: white; border: 1px solid #555;
                    border-radius: 5px; cursor: pointer; 
                }
                .anim-controls button:hover, .controls-btn:hover { background: #555; }
                .anim-controls button:disabled { background: #222; color: #777; cursor: not-allowed; }
                #progress-bar-container { flex-grow: 1; height: 10px; background: #555; border-radius: 5px; overflow: hidden; }
                #progress-bar { width: 0%; height: 100%; background: #e08128; transition: width 0.1s linear; }
            </style>
        </head>
        <body>
            <div id="item-info-panel" class="info-panel"></div>
            <div id="controls-panel" class="info-panel">
                <b>Controls:</b> Left-Click to Rotate, Right-Click to Pan, Scroll to Zoom.
                <br/><button id="reset-view-btn" class="controls-btn">Reset View</button>
            </div>
            <div id="animation-panel" class="info-panel">
                <div id="animation-status">Status: Paused</div>
                 <div class="anim-controls">
                    <button id="play-pause-btn">Play</button>
                    <div id="progress-bar-container"><div id="progress-bar"></div></div>
                    <label for="speed-slider">Speed:</label>
                    <input type="range" id="speed-slider" min="1" max="10" value="5" step="1">
                </div>
            </div>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"><\/script>
            
            <script>
                const mode = '${mode}';
                const vehicle_info = ${JSON.stringify(vehicle_info)};
                let packed_items_data = ${JSON.stringify(packed_items)};
                const loading_sequence = ${JSON.stringify(loading_sequence || [])};
                const unloading_sequence = ${JSON.stringify(unloading_sequence || [])};

                const objScene = new THREE.Scene();
                objScene.background = new THREE.Color(0x282c34);
                const objCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 20000);
                const objRenderer = new THREE.WebGLRenderer({ antialias: true });
                objRenderer.setSize(window.innerWidth, window.innerHeight);
                document.body.appendChild(objRenderer.domElement);

                const objControls = new THREE.OrbitControls(objCamera, objRenderer.domElement);
                const objAmbientLight = new THREE.AmbientLight(0xffffff, 0.6);
                objScene.add(objAmbientLight);
                const objDirectionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                objDirectionalLight.position.set(200, 500, 300);
                objScene.add(objDirectionalLight);

                const fltVehicleW = vehicle_info.width;
                const fltVehicleH = vehicle_info.height;
                const fltVehicleD = vehicle_info.depth;
                const objContainerGeom = new THREE.BoxGeometry(fltVehicleW, fltVehicleH, fltVehicleD);
                const objContainerEdges = new THREE.EdgesGeometry(objContainerGeom);
                const objContainerLines = new THREE.LineSegments(objContainerEdges, new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 }));
                const objContainerCenter = new THREE.Vector3(fltVehicleW / 2, fltVehicleH / 2, fltVehicleD / 2);
                objContainerLines.position.copy(objContainerCenter);
                objScene.add(objContainerLines);
                
                const objColorCache = {};
                function getDeterministicColor(strId) {
                    if (!objColorCache[strId]) {
                        let intHash = 0;
                        for (let i = 0; i < strId.length; i++) {
                            intHash = strId.charCodeAt(i) + ((intHash << 5) - intHash);
                            intHash = intHash & intHash;
                        }
                        const intHue = Math.abs(intHash % 360);
                        objColorCache[strId] = new THREE.Color(\`hsl(\${intHue}, 80%, 60%)\`);
                    }
                    return objColorCache[strId];
                }

                const packageMeshes = {}; // Map of all item meshes, loaded or not.

                function createPackageMesh(objItem) {
                    if (objItem.width <= 0 || objItem.height <= 0 || objItem.depth <= 0) return null;
                    const FLT_VISUAL_SCALE = 0.999;
                    const objItemGeom = new THREE.BoxGeometry(objItem.width * FLT_VISUAL_SCALE, objItem.height * FLT_VISUAL_SCALE, objItem.depth * FLT_VISUAL_SCALE);
                    const objItemMaterial = new THREE.MeshLambertMaterial({ color: getDeterministicColor(objItem.id), transparent: true });
                    const objItemMesh = new THREE.Mesh(objItemGeom, objItemMaterial);
                    
                    const centered_pos = {
                        x: objItem.position_x + objItem.width / 2,
                        y: objItem.position_y + objItem.height / 2,
                        z: objItem.position_z + objItem.depth / 2,
                    };
                    objItemMesh.position.set(centered_pos.x, centered_pos.y, centered_pos.z);
                    objItemMesh.userData = { ...objItem, originalMaterial: objItemMaterial, final_position: centered_pos };
                    return objItemMesh;
                }

                packed_items_data.forEach(item => {
                    const mesh = createPackageMesh(item);
                    if (mesh) packageMeshes[item.id] = mesh;
                });

                objCamera.position.set(objContainerCenter.x, objContainerCenter.y + fltVehicleH, objContainerCenter.z + fltVehicleD * 1.5);
                objControls.target.copy(objContainerCenter);
                objControls.saveState();
                
                function createTextSprite(strMessage, objPosition) {
                    const objCanvas = document.createElement('canvas');
                    const objContext = objCanvas.getContext('2d');
                    objContext.font = \`Bold 16px Arial\`;
                    const fltTextWidth = objContext.measureText(strMessage).width;
                    objCanvas.width = fltTextWidth + 20;
                    objCanvas.height = 40;
                    objContext.font = \`Bold 16px Arial\`;
                    objContext.fillStyle = 'rgba(255, 255, 255, 0.8)';
                    objContext.textAlign = 'center';
                    objContext.textBaseline = 'middle';
                    objContext.fillText(strMessage, objCanvas.width / 2, objCanvas.height / 2);
                    const objTexture = new THREE.CanvasTexture(objCanvas);
                    const objSpriteMaterial = new THREE.SpriteMaterial({ map: objTexture });
                    const objSprite = new THREE.Sprite(objSpriteMaterial);
                    objSprite.scale.set(objCanvas.width / 2, objCanvas.height / 2, 1.0);
                    objSprite.position.copy(objPosition);
                    objScene.add(objSprite);
                }

                const INT_LABEL_OFFSET = 40;
                createTextSprite('Front (Door)', new THREE.Vector3(fltVehicleW + INT_LABEL_OFFSET, objContainerCenter.y, objContainerCenter.z));
                createTextSprite('Back', new THREE.Vector3(-INT_LABEL_OFFSET, objContainerCenter.y, objContainerCenter.z));
                
                document.getElementById('reset-view-btn').addEventListener('click', () => { objControls.reset(); });
                
                let isPlaying = false;
                let animationTimeout = null;
                const playPauseBtn = document.getElementById('play-pause-btn');
                const speedSlider = document.getElementById('speed-slider');
                const progressBar = document.getElementById('progress-bar');
                const animStatus = document.getElementById('animation-status');
                
                function getAnimationDelay() { return 1100 - (speedSlider.value * 100); }

                function tween(obj, to, duration, onComplete) {
                     const from = {};
                     for (const key in to) from[key] = obj[key];
                     const start = performance.now();
                     function animateFrame() {
                         const now = performance.now();
                         let t = (now - start) / duration;
                         if (t > 1) t = 1;
                         for (const key in to) obj[key] = from[key] + (to[key] - from[key]) * t;
                         if (t < 1) requestAnimationFrame(animateFrame);
                         else if (onComplete) onComplete();
                     }
                     requestAnimationFrame(animateFrame);
                }

                let animationQueue = [];
                let currentStepIndex = 0;

                function processAnimationQueue() {
                    if (!isPlaying || currentStepIndex >= animationQueue.length) {
                        animStatus.textContent = 'Animation Complete.';
                        playPauseBtn.textContent = 'Replay';
                        isPlaying = false;
                        return;
                    }

                    const step = animationQueue[currentStepIndex];
                    const mesh = packageMeshes[step.item_id || step.item?.id];
                    if (!mesh) {
                        currentStepIndex++;
                        if(isPlaying) animationTimeout = setTimeout(processAnimationQueue, 50);
                        return;
                    }
                    
                    let duration = getAnimationDelay() * 0.5;
                    let onComplete = () => {
                        currentStepIndex++;
                        progressBar.style.width = \`\${(currentStepIndex / animationQueue.length) * 100}%\`;
                        if(isPlaying) animationTimeout = setTimeout(processAnimationQueue, getAnimationDelay());
                    };

                    switch(step.action) {
                        case 'load':
                            animStatus.textContent = \`Loading item \${step.item.id}\`;
                            mesh.position.y = fltVehicleH + mesh.userData.height;
                            objScene.add(mesh);
                            tween(mesh.position, mesh.userData.final_position, duration, onComplete);
                            break;
                        case 'target':
                            animStatus.textContent = \`Targeting \${step.item_id}\`;
                            mesh.material = new THREE.MeshBasicMaterial({ color: 0xFFFF00, wireframe: true });
                            setTimeout(onComplete, 50); // Small delay for visibility
                            break;
                        case 'relocate':
                            animStatus.textContent = \`Relocating \${step.item_id}...\`;
                             const relocatePos = { x: fltVehicleW + 50, y: fltVehicleH / 2, z: mesh.position.z };
                             tween(mesh.position, relocatePos, duration, () => {
                                 objScene.remove(mesh);
                                 onComplete();
                             });
                            break;
                        case 'deliver':
                            animStatus.textContent = \`Delivering \${step.item_id}!\`;
                            mesh.material = mesh.userData.originalMaterial;
                            const deliverPos = { x: fltVehicleW + 50, y: mesh.position.y, z: mesh.position.z };
                            tween(mesh.position, deliverPos, duration, () => {
                                 objScene.remove(mesh);
                                 onComplete();
                             });
                            break;
                        case 'settle':
                             animStatus.textContent = 'Items settling due to gravity...';
                             const new_centered_y = step.new_y_pos + mesh.userData.height / 2;
                             tween(mesh.position, { y: new_centered_y }, duration * 0.8, () => {
                                mesh.userData.final_position.y = new_centered_y;
                                onComplete();
                             });
                             break;
                        case 'return_relocated':
                             animStatus.textContent = \`Returning \${step.item_id}\`;
                             const new_pos = step.new_pos;
                             const new_centered_pos = {
                                 x: new_pos[0] + mesh.userData.width / 2,
                                 y: new_pos[1] + mesh.userData.height / 2,
                                 z: new_pos[2] + mesh.userData.depth / 2,
                             };
                             const returnStartPos = { x: fltVehicleW + 50, y: new_centered_pos.y, z: new_centered_pos.z };
                             mesh.position.set(returnStartPos.x, returnStartPos.y, returnStartPos.z);
                             mesh.material = mesh.userData.originalMaterial;
                             objScene.add(mesh);
                             tween(mesh.position, new_centered_pos, duration, () => {
                                // Update its final position since it moved.
                                mesh.userData.final_position = new_centered_pos;
                                onComplete();
                             });
                             break;
                    }
                }
                
                function setupAndPlay() {
                    isPlaying = !isPlaying;
                    playPauseBtn.textContent = isPlaying ? 'Pause' : 'Play';
                    if (isPlaying) {
                        processAnimationQueue();
                    } else {
                        clearTimeout(animationTimeout);
                    }
                }

                playPauseBtn.addEventListener('click', () => {
                    if (playPauseBtn.textContent === 'Replay') {
                        Object.values(packageMeshes).forEach(m => objScene.remove(m));
                        packed_items_data.forEach(item => {
                             const mesh = packageMeshes[item.id];
                             if(mesh) {
                                const original_centered = {
                                    x: item.position_x + item.width / 2,
                                    y: item.position_y + item.height / 2,
                                    z: item.position_z + item.depth / 2,
                                };
                                mesh.position.copy(original_centered);
                                mesh.userData.final_position = original_centered;
                                mesh.material = mesh.userData.originalMaterial;
                             }
                        });
                        if(mode === 'unload' || mode === 'static') {
                             Object.values(packageMeshes).forEach(m => objScene.add(m));
                        }
                        currentStepIndex = 0;
                        progressBar.style.width = '0%';
                        isPlaying = false;
                    }
                    setupAndPlay();
                });

                if (mode === 'static') {
                    Object.values(packageMeshes).forEach(mesh => objScene.add(mesh));
                } else if (mode === 'load') {
                    animationQueue = loading_sequence;
                } else if (mode === 'unload') {
                    animationQueue = unloading_sequence;
                    Object.values(packageMeshes).forEach(mesh => objScene.add(mesh));
                }

                // ... Raycasting and other boilerplate code is the same ...
                
                 // Raycasting for item selection
                const objRaycaster = new THREE.Raycaster();
                const objMouse = new THREE.Vector2();
                let objSelectedObject = null;
                const objHighlightMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFF00, transparent: true, opacity: 0.8 });
                const objInfoDiv = document.getElementById('item-info-panel');
                
                window.addEventListener('click', (event) => {
                    objMouse.x = (event.clientX / window.innerWidth) * 2 - 1;
                    objMouse.y = - (event.clientY / window.innerHeight) * 2 + 1;
                    objRaycaster.setFromCamera(objMouse, objCamera);
                    
                    const meshesForIntersect = Object.values(packageMeshes).filter(m => m.parent === objScene);
                    const arrIntersects = objRaycaster.intersectObjects(meshesForIntersect);
                    
                    if (objSelectedObject) {
                        if (objSelectedObject.userData.originalMaterial && !objSelectedObject.material.wireframe) {
                            objSelectedObject.material = objSelectedObject.userData.originalMaterial;
                        }
                        objSelectedObject = null;
                    }
                    objInfoDiv.style.display = 'none';
                    
                    if (arrIntersects.length > 0) {
                        objSelectedObject = arrIntersects[0].object;
                        if (!objSelectedObject.material.wireframe) { 
                            objSelectedObject.material = objHighlightMaterial;
                        }
                        const objData = objSelectedObject.userData;
                        objInfoDiv.style.display = 'block';
                        objInfoDiv.innerHTML = \`
                            <strong>Product ID:</strong> \${objData.id}<br>
                            <strong>Volume:</strong> \${Math.round(objData.volume).toLocaleString()} cm³<br>
                            <strong>Dimensions:</strong> \${objData.width}×\${objData.height}×\${objData.depth} cm
                        \`;
                    }
                });

                function animate() {
                    requestAnimationFrame(animate);
                    objControls.update();
                    objRenderer.render(objScene, objCamera);
                }
                animate();
                
                window.addEventListener('resize', () => {
                    objCamera.aspect = window.innerWidth / window.innerHeight;
                    objCamera.updateProjectionMatrix();
                    objRenderer.setSize(window.innerWidth, window.innerHeight);
                }, false);

            <\/script>
        </body>
        </html>
    `;
    
    const objVizWindow = window.open("", "3D Visualization", "width=1200,height=800");
    if (objVizWindow) {
        objVizWindow.document.open();
        objVizWindow.document.write(strHtmlContent);
        objVizWindow.document.close();
        g_objVisualizeMenuBtn.disabled = true;
        const intCheckWindowClosedInterval = setInterval(() => {
            if (objVizWindow.closed) {
                clearInterval(intCheckWindowClosedInterval);
                g_objVisualizeMenuBtn.disabled = false;
            }
        }, 500);
    } else {
        alert("Please allow pop-ups for this site to view the visualization.");
    }
}
});