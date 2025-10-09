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
    
    // Reference to the button that opens the 3D visualization window.
    const g_objVisualizeBtn = document.getElementById('visualize-btn'); 
    
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
    
    // Listen for a click on the "Visualize Packing" button and call the function to open the 3D view.
    g_objVisualizeBtn.addEventListener('click', () => { _openVisualizationWindow(); });

    // This allows the user to close a modal by clicking on the dark background area outside of it.
    window.onclick = (event) => 
    { 
        if (event.target === g_objConfigModal) { g_objConfigModal.style.display = "none"; }
        if (event.target === g_objGuidesModal) { g_objGuidesModal.style.display = "none"; }
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
        _showLoader("Starting data load...", { showLoadCancel: false, loadCancelDisabled: false }); // Show the loader.

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
                    _appendPackagesToTable(result.packages);
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
        _showLoader("Starting simulation...", { showSimCancel: true, simCancelDisabled: true });
        
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
                        { showSimCancel: false } // Keep cancel button injvisible and disabled.
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
     * Fills the "Selected Items" table with rows of package data.
     */
    function _appendPackagesToTable(arrPackages)
    {
        if (arrPackages && arrPackages.length > 0) 
        {
            document.getElementById('initial-no-item').style.display = 'none';
            // The `map` function transforms each package object into an HTML table row string,
            // and `join` combines them all into one large string to update the table body.
            g_objInitialTableBody.innerHTML = arrPackages.map(_createTableRowHTML).join('');
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
        g_objVisualizeBtn.style.display = 'none'; // Hide the visualize button initially.

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
        document.getElementById('metric-feasibility').textContent = metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = metrics.unloading_sequence_length;

        // Populate the "Packed Items" table.
        const objResultTableBody = document.getElementById('result-item-table-body');
        const objNoItemText = document.getElementById('result-no-item');
        objResultTableBody.innerHTML = ''; 
        if (objResults.packed_items && objResults.packed_items.length > 0)
        {
            objNoItemText.style.display = 'none';
            objResultTableBody.innerHTML = objResults.packed_items.map(_createTableRowHTML).join('');
            // Only show the "Visualize Packing" button if there are items to show.
            g_objVisualizeBtn.style.display = 'inline-flex';
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
     * This approach keeps the visualization code entirely self-contained.
     */
    function _openVisualizationWindow() 
    {
        // First, we perform a critical safety check. If there are no results stored from the
        // last simulation, we inform the user and stop the function immediately.
        if (!g_objLastResults) 
        {
            alert("No simulation data available to visualize.");
            return;
        }

        // We extract the vehicle information and the list of packed items from the stored results.
        // This is the specific data needed to build our 3D scene.
        const { vehicle_info, packed_items } = g_objLastResults;
        
        // This is the core of the function. We define a very long string that contains the entire
        // source code for the new pop-up window. Using backticks (`) allows us to create a
        // multi-line string and easily embed our simulation variables directly into it using ${...}.
        const strHtmlContent = `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>3D Packing Visualization</title>
                <!-- This section defines the style and appearance of the elements in our 3D view window. -->
                <style>
                    body { margin: 0; overflow: hidden; font-family: sans-serif; }
                    canvas { display: block; }
                    .info-panel {
                        position: absolute; top: 10px; padding: 10px; background: rgba(0, 0, 0, 0.7);
                        color: white; border-radius: 5px; font-size: 14px; line-height: 1.5; pointer-events: none;
                    }
                    #item-info-panel { left: 10px; display: none; }
                    #item-info-panel strong { color: #e08128; }
                    #controls-panel { right: 10px; text-align: right; }
                    #controls-panel button {
                        margin-top: 5px; padding: 8px 12px; background: #333; color: white; border: 1px solid #555;
                        border-radius: 5px; cursor: pointer; pointer-events: auto;
                    }
                    #controls-panel button:hover { background: #555; }
                </style>
            </head>
            <body>
                <!-- These are the HTML panels that will display information on top of our 3D canvas. -->
                <div id="item-info-panel" class="info-panel"></div>
                <div id="controls-panel" class="info-panel">
                    <b>Controls:</b> Left-Click to Rotate, Right-Click to Pan, Scroll to Zoom.
                    <br/><button id="reset-view-btn">Reset View</button>
                </div>

                <!-- We include the required Three.js library files from a trusted online source (CDN). -->
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"><\/script>
                
                <!-- This is the main script that will run inside the new window to create the 3D scene. -->
                <script>
                    // === SCENE SETUP ===
                    // A "scene" is the top-level container in Three.js; it holds all our objects, lights, and cameras.
                    const objScene = new THREE.Scene();
                    // We set a dark background color for our scene.
                    objScene.background = new THREE.Color(0x282c34);
                    // The "camera" is our eye in the 3D world. A PerspectiveCamera mimics how the human eye sees.
                    const objCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 20000);
                    // The "renderer" is what takes the scene and camera and draws the result onto the screen (an HTML canvas).
                    const objRenderer = new THREE.WebGLRenderer({ antialias: true }); // 'antialias' makes edges smoother.
                    // We set the renderer's size to match the full browser window.
                    objRenderer.setSize(window.innerWidth, window.innerHeight);
                    // We add the renderer's canvas element to our HTML body.
                    document.body.appendChild(objRenderer.domElement);

                    // === CONTROLS AND LIGHTING ===
                    // "OrbitControls" allow the user to interact with the scene using the mouse (rotate, zoom, pan).
                    const objControls = new THREE.OrbitControls(objCamera, objRenderer.domElement);
                    // "AmbientLight" provides a soft, general light that illuminates everything in the scene equally.
                    const objAmbientLight = new THREE.AmbientLight(0xffffff, 0.6);
                    objScene.add(objAmbientLight);
                    // "DirectionalLight" acts like the sun, providing light from a specific direction, which creates shadows and highlights.
                    const objDirectionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                    objDirectionalLight.position.set(200, 500, 300); // We position the light high up.
                    objScene.add(objDirectionalLight);

                    // === VEHICLE CONTAINER CREATION ===
                    // We get the vehicle's dimensions from our injected data.
                    const fltVehicleW = ${vehicle_info.width};
                    const fltVehicleH = ${vehicle_info.height};
                    const fltVehicleD = ${vehicle_info.depth};
                    // We create a "geometry" which defines the shape (a box) of our container.
                    const objContainerGeom = new THREE.BoxGeometry(fltVehicleW, fltVehicleH, fltVehicleD);
                    // "EdgesGeometry" creates a wireframe from the box geometry.
                    const objContainerEdges = new THREE.EdgesGeometry(objContainerGeom);
                    // We create a "material" (what the wireframe looks like) and combine it with the edges to create a visible object.
                    const objContainerLines = new THREE.LineSegments(objContainerEdges, new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 }));
                    // We calculate the center point of our vehicle.
                    const objContainerCenter = new THREE.Vector3(fltVehicleW / 2, fltVehicleH / 2, fltVehicleD / 2);
                    // We position the container's wireframe to be centered in our scene.
                    objContainerLines.position.copy(objContainerCenter);
                    objScene.add(objContainerLines);
                    
                    // === PACKAGE COLORING LOGIC ===
                    // This function generates a unique, consistent color for each package based on its ID.
                    const objColorCache = {}; // We store colors here to avoid recalculating them.
                    function getDeterministicColor(strId) {
                        if (!objColorCache[strId]) {
                            let intHash = 0;
                            for (let i = 0; i < strId.length; i++) {
                                intHash = strId.charCodeAt(i) + ((intHash << 5) - intHash);
                                intHash = intHash & intHash; // This is a bitwise operation to keep the number manageable.
                            }
                            const intHue = Math.abs(intHash % 360); // We use the hash to pick a color hue (0-359).
                            objColorCache[strId] = new THREE.Color(\`hsl(\${intHue}, 80%, 60%)\`);
                        }
                        return objColorCache[strId];
                    }

                    // === PACKAGE MESH CREATION ===
                    // This section creates the 3D box for each individual package.
                    const arrPackageMeshes = []; // An array to hold all the package objects for later reference (like for clicking).
                    const arrPackedItems = ${JSON.stringify(packed_items)};
                    arrPackedItems.forEach(objItem => {
                        // CRITICAL: A final safety check to ensure we only render items with valid, positive dimensions.
                        if (objItem.width > 0 && objItem.height > 0 && objItem.depth > 0) {
                            // We make the visual box slightly smaller than its real size to create small gaps, making individual boxes easier to see.
                            const FLT_VISUAL_SCALE = 0.999;
                            // Define the shape (geometry) of the package box.
                            const objItemGeom = new THREE.BoxGeometry(
                                objItem.width * FLT_VISUAL_SCALE, objItem.height * FLT_VISUAL_SCALE, objItem.depth * FLT_VISUAL_SCALE
                            );
                            // Define the appearance (material) of the box, using our color function.
                            const objItemMaterial = new THREE.MeshLambertMaterial({ color: getDeterministicColor(objItem.id) });
                            // A "mesh" is the final object, combining a shape (geometry) with an appearance (material).
                            const objItemMesh = new THREE.Mesh(objItemGeom, objItemMaterial);
                            // We set the position of the box inside the container based on the simulation results.
                            objItemMesh.position.set(
                                objItem.position_x + objItem.width / 2,
                                objItem.position_y + objItem.height / 2,
                                objItem.position_z + objItem.depth / 2
                            );
                            objItemMesh.userData = objItem; // We attach the original package data to the 3D object itself for easy access later.
                            objScene.add(objItemMesh);
                            arrPackageMeshes.push(objItemMesh);
                        }
                    });
                    
                    // === INITIAL CAMERA POSITION ===
                    // We calculate the largest dimension of the vehicle to set an appropriate initial camera distance.
                    const fltMaxDim = Math.max(fltVehicleW, fltVehicleH, fltVehicleD);
                    // Position the camera to provide a good overview of the packed container from the side.
                    objCamera.position.x = -fltMaxDim; 
                    objCamera.position.y = objContainerCenter.y;
                    objCamera.position.z = objContainerCenter.z;
                    // We tell the camera controls to look at the center of the container.
                    objControls.target.copy(objContainerCenter);
                    // Save this initial view so the "Reset View" button knows where to return to.
                    objControls.saveState();

                    // === INTERACTIVITY AND LABELS ===
                    // "Raycaster" is a tool in Three.js used to detect which object the mouse is pointing at.
                    const objRaycaster = new THREE.Raycaster();
                    const objMouse = new THREE.Vector2(); // A variable to store the mouse's current X/Y coordinates.
                    let objSelectedObject = null; // A variable to remember which object is currently selected.
                    // A special material to make the selected package glow yellow.
                    const objHighlightMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFF00, transparent: true, opacity: 0.8 });
                    const objInfoDiv = document.getElementById('item-info-panel'); // Reference to our HTML info panel.
                    
                    // A helper function to create text labels that float in the 3D space.
                    function createTextSprite(strMessage, objPosition, intFontSize = 14) {
                        const objCanvas = document.createElement('canvas');
                        const objContext = objCanvas.getContext('2d');
                        objContext.font = \`Bold \${intFontSize}px Arial\`;
                        const fltTextWidth = objContext.measureText(strMessage).width;
                        objCanvas.width = fltTextWidth + 20;
                        objCanvas.height = intFontSize + 20;
                        
                        objContext.font = \`Bold \${intFontSize}px Arial\`;
                        objContext.fillStyle = 'white';
                        objContext.textAlign = 'center';
                        objContext.textBaseline = 'middle';
                        objContext.fillText(strMessage, objCanvas.width / 2, objCanvas.height / 2);
                        
                        const objTexture = new THREE.CanvasTexture(objCanvas);
                        const objSpriteMaterial = new THREE.SpriteMaterial({ map: objTexture });
                        const objSprite = new THREE.Sprite(objSpriteMaterial);
                        objSprite.scale.set(objCanvas.width, objCanvas.height, 1.0);
                        objSprite.position.copy(objPosition);
                        objScene.add(objSprite);
                    }

                    // Create and place all the orientation labels around the container.
                    const INT_LABEL_OFFSET = 30; // How far from the container the labels should be.
                    createTextSprite('Back', new THREE.Vector3(fltVehicleW + INT_LABEL_OFFSET, objContainerCenter.y, objContainerCenter.z));
                    createTextSprite('Front', new THREE.Vector3(-INT_LABEL_OFFSET, objContainerCenter.y, objContainerCenter.z));
                    createTextSprite('Top', new THREE.Vector3(objContainerCenter.x, fltVehicleH + INT_LABEL_OFFSET, objContainerCenter.z));
                    createTextSprite('Bottom', new THREE.Vector3(objContainerCenter.x, -INT_LABEL_OFFSET, objContainerCenter.z));
                    createTextSprite('Right Side', new THREE.Vector3(objContainerCenter.x, objContainerCenter.y, fltVehicleD + INT_LABEL_OFFSET));
                    createTextSprite('Left Side', new THREE.Vector3(objContainerCenter.x, objContainerCenter.y, -INT_LABEL_OFFSET));
                    
                    // Setup the click listener for the reset button.
                    document.getElementById('reset-view-btn').addEventListener('click', () => { objControls.reset(); });
                    
                    // Add an event listener that fires whenever the user clicks in the window.
                    window.addEventListener('click', (event) => {
                        // We convert the mouse's screen coordinates (in pixels) to Three.js's normalized coordinates (-1 to +1).
                        objMouse.x = (event.clientX / window.innerWidth) * 2 - 1;
                        objMouse.y = - (event.clientY / window.innerHeight) * 2 + 1;
                        // We tell the raycaster to shoot a "ray" from the camera through the mouse's position into the scene.
                        objRaycaster.setFromCamera(objMouse, objCamera);
                        // We check if this ray intersects with any of our package meshes.
                        const arrIntersects = objRaycaster.intersectObjects(arrPackageMeshes);
                        
                        // First, if an object was previously selected, we restore its original color.
                        if (objSelectedObject) {
                            objSelectedObject.material = objSelectedObject.userData.originalMaterial;
                            objSelectedObject = null;
                        }
                        // We hide the info panel.
                        objInfoDiv.style.display = 'none';
                        
                        // If our ray hit one or more objects...
                        if (arrIntersects.length > 0) {
                            const objIntersected = arrIntersects[0].object; // We take the closest object that was hit.
                            objSelectedObject = objIntersected; // We mark it as the currently selected object.
                            objSelectedObject.userData.originalMaterial = objSelectedObject.material; // We save its original material.
                            objSelectedObject.material = objHighlightMaterial; // We apply the yellow highlight material.
                            
                            const objData = objIntersected.userData; // Get the package data we stored earlier.
                            // We make the info panel visible and populate it with the item's details.
                            objInfoDiv.style.display = 'block';
                            objInfoDiv.innerHTML = \`
                                <strong>Product ID:</strong> \${objData.id}<br>
                                <strong>Volume:</strong> \${Math.round(objData.volume).toLocaleString()} cm³<br>
                                <strong>Service Time:</strong> \${objData.service_time} s<br>
                                <strong>Dimensions (W×H×D):</strong> \${objData.width}×\${objData.height}×\${objData.depth} cm
                            \`;
                        }
                    });

                    // === RENDER LOOP ===
                    // This is the main animation loop. 'requestAnimationFrame' creates a loop that calls the 'animate'
                    // function roughly 60 times per second, creating a smooth visual experience.
                    function animate() {
                        requestAnimationFrame(animate); // Tell the browser we want to run this function again on the next frame.
                        objControls.update(); // Update the controls (this is necessary if auto-rotation or damping is enabled).
                        objRenderer.render(objScene, objCamera); // Re-draw the scene from the camera's current perspective.
                    }
                    animate(); // Start the loop.
                    
                    // This ensures that if the user resizes the browser window, our 3D scene will resize to match.
                    window.addEventListener('resize', () => {
                        objCamera.aspect = window.innerWidth / window.innerHeight;
                        objCamera.updateProjectionMatrix(); // We must update the camera's projection matrix after changing its aspect ratio.
                        objRenderer.setSize(window.innerWidth, window.innerHeight);
                    }, false);
                <\/script>
            </body>
            </html>
        `;
        
        // This command opens a new browser window or tab.
        const objVizWindow = window.open("", "3D Visualization", "width=900,height=700");
        
        // This series of commands writes our dynamically generated HTML content directly into the new window.
        objVizWindow.document.open();
        objVizWindow.document.write(strHtmlContent);
        objVizWindow.document.close();

        // To prevent users from opening many visualization windows, we temporarily disable the button after one is opened.
        g_objVisualizeBtn.disabled = true;

        // We set up a simple timer that checks every half-second to see if the user has closed the visualization window.
        const intCheckWindowClosedInterval = setInterval(() => {
            if (objVizWindow.closed) {
                clearInterval(intCheckWindowClosedInterval); // Once closed, we stop the timer.
                g_objVisualizeBtn.disabled = false; // We re-enable the "Visualize Packing" button.
                console.log("Visualization window closed, button re-enabled.");
            }
        }, 500);
    }
});