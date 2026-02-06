/**
* System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
* Module Name: Frontend Logic
*
* Purpose of this file: Manages client-side interaction, API requests for loading data/simulation, and UI state updates using Hungarian notation and consistent style.
*
* Author/s:
* ALFARO, ABRAM S.
* BUNAO, JOHN GLAY C.
* DELA CRUZ, JUAN GABRIEL D.
* ERFE, JEFFERSON B.
* ESTONILO, JULIUS EVAN C.
*/

document.addEventListener("DOMContentLoaded", () => 
{
    // --- GLOBAL VARIABLES ---
    let g_strSelectedAlgorithm = "PSO";
    let g_strSelectedCapacity = null;
    let g_arrAllLoadedPackages = [];
    let g_strCurrentLoadId = null;
    let g_objLoadPollingInterval = null;
    let g_strCurrentSimulationId = null;
    let g_objSimPollingInterval = null;
    let g_blnLoadCancellationRequested = false;
    let g_blnSimCancellationRequested = false;
    let g_objLastResults = null;

    // --- DOM REFERENCES ---
    const g_objConfigModal = document.getElementById("myModal");
    const g_objOpenModalBtn = document.getElementById("openModalBtn");
    const g_objCloseModalBtn = document.getElementById("closeModalBtn");
    const g_objRunSimBtn = document.getElementById("run-sim-btn");
    const g_objClearSimBtn = document.getElementById("clear-sim-btn");
    
    const g_objLoaderModal = document.getElementById("loader");
    const g_objCancelLoadBtn = document.getElementById('cancel-load-btn');
    const g_objCancelSimBtn = document.getElementById('cancel-sim-btn');
    
    const g_arrAlgoButtons = document.querySelectorAll(".modal-options button");
    const g_objCapacitySelect = document.getElementById("vehicle-capacity-select");
    const g_objDynamicConstraintToggle = document.getElementById('dynamic-constraint-toggle');
    
    const g_objInitialTableBody = document.getElementById('initial-item-table-body');
    
    const g_objVisualizeMenu = document.getElementById('visualize-menu');
    const g_objVisualizeMenuBtn = document.getElementById('visualize-menu-btn');
    const g_objVisualizeDropdown = document.getElementById('visualize-dropdown-content');
    const g_objVizStaticBtn = document.getElementById('viz-static-btn');
    const g_objVizLoadAnimBtn = document.getElementById('viz-load-anim-btn');
    const g_objVizUnloadAnimBtn = document.getElementById('viz-unload-anim-btn');
    
    const g_objGuidesModal = document.getElementById("guidesModal");
    const g_objOpenGuidesBtn = document.getElementById("openGuidesBtn");
    const g_objCloseGuidesBtn = document.getElementById("closeGuidesBtn");
    const g_objGotItBtn = document.getElementById("gotItBtn");


    // --- INITIALIZATION ---
    // Start by loading the vehicle choices for the dropdown
    loadInitialCapacities();
    

    /**
     * Async load of capacity list for dropdown.
     * Fetches the available vehicle types from the backend to populate the UI select element.
     */
    async function loadInitialCapacities()
    {
        console.log("Requesting vehicle capacity list from server...");
        g_objCapacitySelect.disabled = true;
        
        // Add a temporary loading state option
        const objLoadingOption = new Option("Loading vehicles...", "", true, true);
        objLoadingOption.disabled = true;
        g_objCapacitySelect.add(objLoadingOption);

        try 
        {
            // Execute GET request
            const objResponse = await fetch('/get_all_capacities');
            
            // Check for network or server errors
            if (!objResponse.ok) 
            {
                throw new Error(`Server error: ${objResponse.statusText}`);
            }

            // Parse response and populate select options
            const objData = await objResponse.json();
            g_objCapacitySelect.innerHTML = '<option value="" disabled selected>Select Vehicle Capacity</option>';
            
            // Iterate through received capacities and create options
            objData.capacities.forEach(strCapacity => 
            {
                const objOption = document.createElement('option');
                objOption.value = strCapacity;
                objOption.textContent = Number(strCapacity).toLocaleString();
                g_objCapacitySelect.appendChild(objOption);
            }); //end of forEach

            console.log("Successfully loaded vehicle capacities.");
        }
        catch (objError) 
        {
            // Handle connection failure
            console.error("Failed to load vehicle capacities:", objError);
            g_objCapacitySelect.innerHTML = '<option value="" disabled selected>Error loading vehicles</option>';
        }
        finally 
        {
            // Ensure select box is re-enabled regardless of outcome
            g_objCapacitySelect.disabled = false;
        }
    } //end of loadInitialCapacities


    // --- EVENT LISTENERS ---

    // Modal Visibility Controls
    g_objOpenModalBtn.onclick = () => 
    { 
        g_objConfigModal.style.display = "flex"; 
    };

    g_objCloseModalBtn.onclick = () => 
    { 
        g_objConfigModal.style.display = "none"; 
    };

    g_objOpenGuidesBtn.onclick = () => 
    { 
        g_objGuidesModal.style.display = "flex"; 
    };

    g_objCloseGuidesBtn.onclick = () => 
    { 
        g_objGuidesModal.style.display = "none"; 
    };

    g_objGotItBtn.onclick = () => 
    { 
        g_objGuidesModal.style.display = "none"; 
    };
    
    // Visualization Menu Controls
    g_objVisualizeMenuBtn.addEventListener('click', () => 
    {
        g_objVisualizeDropdown.classList.toggle('show-dropdown');
    });

    g_objVizStaticBtn.addEventListener('click', (e) => 
    {
        e.preventDefault();
        openVisualizationWindow('static');
        g_objVisualizeDropdown.classList.remove('show-dropdown');
    });

    g_objVizLoadAnimBtn.addEventListener('click', (e) => 
    {
        e.preventDefault();
        openVisualizationWindow('load');
        g_objVisualizeDropdown.classList.remove('show-dropdown');
    });

    g_objVizUnloadAnimBtn.addEventListener('click', (e) => 
    {
        e.preventDefault();
        openVisualizationWindow('unload');
        g_objVisualizeDropdown.classList.remove('show-dropdown');
    });

    // Window Click Handlers (Close modals on outside click)
    window.onclick = (objEvent) => 
    { 
        if (objEvent.target === g_objConfigModal) 
        { 
            g_objConfigModal.style.display = "none"; 
        }
        if (objEvent.target === g_objGuidesModal) 
        { 
            g_objGuidesModal.style.display = "none"; 
        }
        if (!objEvent.target.matches('.visualize-btn, .visualize-btn *')) 
        {
            if (g_objVisualizeDropdown.classList.contains('show-dropdown')) 
            {
                g_objVisualizeDropdown.classList.remove('show-dropdown');
            }
        }
    }; //end of window.onclick
    
    // Simulation Control Buttons
    g_objClearSimBtn.addEventListener("click", () => 
    { 
        location.reload(); 
    });
    
    g_objCancelLoadBtn.addEventListener('click', () => 
    { 
        cancelDataLoading(); 
    });
    
    g_objCancelSimBtn.addEventListener('click', () => 
    { 
        cancelSimulation(); 
    });
    
    g_objRunSimBtn.addEventListener("click", () => 
    { 
        startSimulation(); 
    });
    
    // Algorithm Selection Handling
    g_arrAlgoButtons.forEach(objButton => 
    {
        objButton.addEventListener("click", () => 
        {
            // Reset active state for all buttons and highlight the selected one
            g_arrAlgoButtons.forEach(btn => btn.classList.remove("active"));
            objButton.classList.add("active");
            g_strSelectedAlgorithm = objButton.getAttribute("data-algo");
        });
    }); //end of g_arrAlgoButtons.forEach

    // Vehicle Capacity Change Handling
    g_objCapacitySelect.addEventListener("change", (objEvent) => 
    {
        g_strSelectedCapacity = objEvent.target.value;
        if (g_strSelectedCapacity) 
        {
            // Initiate data loading when a valid capacity is selected
            startLoadingDisplayData(g_strSelectedCapacity);
        }
    }); //end of g_objCapacitySelect listener


    // --- DATA FUNCTIONS ---

    /**
     * Start backend data prep.
     * Initiates the asynchronous data loading process on the server for the selected capacity.
     */
    async function startLoadingDisplayData(strCapacity) 
    {
        // Reset state variables
        g_blnLoadCancellationRequested = false; 
        g_objRunSimBtn.disabled = true;
        resetInitialUI();

        showLoader("Starting data load...", { showLoadCancel: true, loadCancelDisabled: false });

        try 
        {
            // Send request to initialize data
            const objResponse = await fetch('/start_data_loading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: strCapacity })
            });

            const objData = await objResponse.json();
            
            // Validate response and start polling
            if (objData.status === 'started') 
            {
                g_strCurrentLoadId = objData.load_id;
                g_objCancelLoadBtn.disabled = false;
                g_objLoadPollingInterval = setInterval(checkLoadStatus, 1500);
            } 
            else 
            {
                throw new Error("Failed to start data loading on the server.");
            }
        } 
        catch (objError) 
        {
            console.error("Error starting data load:", objError);
            alert(`Could not start data load: ${objError.message}`);
            hideLoader();
        }
    } //end of startLoadingDisplayData

    /**
     * Check loading status via poll.
     * Periodically queries the server to update the loading progress or final results.
     */
    async function checkLoadStatus() 
    {
        // Guard clause for cancellation or invalid ID
        if (g_blnLoadCancellationRequested || !g_strCurrentLoadId) 
        {
            clearInterval(g_objLoadPollingInterval);
            return;
        }
        
        showLoader(`Loading sample route data...`, { showLoadCancel: true });
        
        try 
        {
            const objResponse = await fetch(`/data_loading_status/${g_strCurrentLoadId}`);
            if (!objResponse.ok) 
            {
                throw new Error(`Server status check failed: ${objResponse.statusText}`);
            }
            
            const objData = await objResponse.json();
            
            // Handle different status states (completed, error, cancelled)
            if (objData.status === 'completed') 
            {
                clearInterval(g_objLoadPollingInterval);
                
                const objResult = objData.result;
                
                // Update UI with vehicle and package details
                document.getElementById('initial-vehicle-volume').textContent = formatNumber(objResult.vehicle.capacity_cm3);
                
                if (objResult.packages && objResult.packages.length > 0) 
                {
                    appendPackagesToTable(g_objInitialTableBody, objResult.packages);
                    g_arrAllLoadedPackages = objResult.packages;
                    updateInitialSummary(objResult.vehicle.total_package_volume, objResult.packages.length, objResult.vehicle.total_service_time);
                }

                g_objRunSimBtn.disabled = false;
                hideLoader();
            }
            else if (objData.status === 'error')
            {
                clearInterval(g_objLoadPollingInterval);
                alert(`Data Loading Error: ${objData.result.error}`);
                resetInitialUI();
                hideLoader();
            } 
            else if (objData.status === 'cancelled') 
            {
                 clearInterval(g_objLoadPollingInterval);
                 resetInitialUI();
                 g_objRunSimBtn.disabled = true;
                 hideLoader();
            }
        } 
        catch (objError) 
        {
             // Handle network interruption during polling
             console.error("Polling error:", objError);
             clearInterval(g_objLoadPollingInterval);
             alert("Lost connection with the server during data load.");
             g_objRunSimBtn.disabled = true;
             hideLoader();
        }
    } //end of checkLoadStatus
    
    /**
     * Cancel ongoing loading job.
     * Sends a request to the server to halt the data preparation process.
     */
    async function cancelDataLoading() 
    {
        if (!g_strCurrentLoadId) return;

        // Update UI state immediately
        g_blnLoadCancellationRequested = true;
        g_objCancelLoadBtn.disabled = true;
        showLoader('Cancellation requested... Please wait.', { showLoadCancel: false });
        
        try 
        {
            // Request cancellation
            fetch(`/cancel_data_loading/${g_strCurrentLoadId}`, { method: 'POST' });
            
            clearInterval(g_objLoadPollingInterval);
            
            // Start separate interval to verify cancellation success
            const objCleanupInterval = setInterval(async () => 
            {
                const objResponse = await fetch(`/data_loading_status/${g_strCurrentLoadId}`);
                const objData = await objResponse.json();
                
                if (['cancelled', 'error', 'not_found'].includes(objData.status)) 
                {
                    clearInterval(objCleanupInterval);
                    alert("Data loading has been cancelled.");
                    resetInitialUI();
                    hideLoader();
                }
            }, 2000); //end of objCleanupInterval
        }
        catch (objError) 
        {
            console.error("Failed to send data load cancel request:", objError);
            hideLoader();
        }
    } //end of cancelDataLoading


    // --- SIMULATION FUNCTIONS ---

    /**
     * Initiates the packing simulation.
     * Validates input, updates UI, and triggers the algorithm on the server.
     */
    async function startSimulation() 
    {
        g_blnSimCancellationRequested = false;

        // Validate pre-conditions
        if (!g_strSelectedCapacity || g_arrAllLoadedPackages.length === 0) 
        {
            alert("Please select a vehicle capacity and wait for its data to load first.");
            return;
        }
        
        const blnIsDynamicConstraintEnabled = g_objDynamicConstraintToggle.checked;
        
        g_objConfigModal.style.display = "none";
        showLoader("Starting simulation...", { showSimCancel: true, simCancelDisabled: false });
        
        try 
        {
            // Construct and send payload
            const objResponse = await fetch('/start_simulation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    algorithm: g_strSelectedAlgorithm, 
                    capacity: g_strSelectedCapacity,
                    dynamic_constraint_enabled: blnIsDynamicConstraintEnabled
                }),
            });
            const objData = await objResponse.json();
            
            if (objData.status === 'started') 
            {
                g_strCurrentSimulationId = objData.simulation_id;
                g_objCancelSimBtn.disabled = false;
                // Start polling for simulation progress
                g_objSimPollingInterval = setInterval(checkSimulationStatus, 2000);
            } 
            else 
            {
                throw new Error("Failed to start simulation on the server.");
            }
        } 
        catch (objError) 
        {
            console.error("Error starting simulation:", objError);
            alert(`Could not start simulation: ${objError.message}`);
            hideLoader();
        }
    } //end of startSimulation


    /**
     * Polls the server for simulation progress or completion.
     */
    async function checkSimulationStatus() 
    {
        // Stop if cancelled or invalid
        if (g_blnSimCancellationRequested || !g_strCurrentSimulationId) 
        {
            clearInterval(g_objSimPollingInterval);
            return;
        }

        try 
        {
            const objResponse = await fetch(`/simulation_status/${g_strCurrentSimulationId}`);
            if (!objResponse.ok) 
            {
                throw new Error(`Server status check failed: ${objResponse.statusText}`);
            }

            const objData = await objResponse.json();

            // Update loader with progress (generations/steps)
            if (objData.status === 'running' && objData.progress) 
            {
                const objProgress = objData.progress;
                if (objProgress.total > 0) 
                {
                    showLoader(
                        `Optimizing... (Generation ${objProgress.current} / ${objProgress.total})`, 
                        { showSimCancel: false }
                    );
                } 
                else 
                {
                     showLoader(
                        objProgress.message || 'Simulation in progress...', 
                        { showSimCancel: true }
                     );
                }
            }
            
            // Handle completion or failure
            if (objData.status === 'completed') 
            {
                clearInterval(g_objSimPollingInterval);
                updateResultsUI(objData.result);
                hideLoader();
            } 
            else if (objData.status === 'error')
            {
                clearInterval(g_objSimPollingInterval);
                alert(`Simulation Error: ${objData.result.error}`);
                hideLoader();
            } 
            else if (objData.status === 'cancelled') 
            {
                 clearInterval(g_objSimPollingInterval);
                 hideLoader();
            }
        } 
        catch (objError) 
        {
             console.error("Polling error:", objError);
             clearInterval(g_objSimPollingInterval);
             alert("Lost connection with the server.");
             hideLoader();
        }
    } //end of checkSimulationStatus
    

    /**
     * Aborts the running simulation.
     */
    async function cancelSimulation() 
    {
        if (!g_strCurrentSimulationId) return;
        
        g_blnSimCancellationRequested = true;
        g_objCancelSimBtn.disabled = true;
        showLoader('Cancellation requested... Please wait.', { showSimCancel: false });
        
        try 
        {
            fetch(`/cancel_simulation/${g_strCurrentSimulationId}`, { method: 'POST' });
            
            clearInterval(g_objSimPollingInterval);
            
            // Poll for cancellation confirmation
            const objCleanupInterval = setInterval(async () => 
            {
                 const objResponse = await fetch(`/simulation_status/${g_strCurrentSimulationId}`);
                 const objData = await objResponse.json();
                 if (['cancelled', 'error', 'not_found'].includes(objData.status)) 
                 {
                     clearInterval(objCleanupInterval);
                     alert("Simulation has been cancelled.");
                     hideLoader();
                 }
            }, 1500);
        }
        catch (objError) 
        {
            console.error("Failed to send simulation cancel request:", objError);
            hideLoader();
        }
    } //end of cancelSimulation
    

    // --- HELPER FUNCTIONS ---

    /**
     * Controls the visibility and content of the loading modal.
     */
    function showLoader(strMessage = "Processing...", objOptions = {})
    {
        g_objLoaderModal.querySelector('p').textContent = strMessage;
        
        g_objCancelLoadBtn.style.display = objOptions.showLoadCancel ? 'block' : 'none';
        g_objCancelSimBtn.style.display = objOptions.showSimCancel ? 'block' : 'none';
        
        if (objOptions.showSimCancel) 
        { 
            g_objCancelSimBtn.disabled = !!objOptions.simCancelDisabled; 
        }
        if (objOptions.showLoadCancel) 
        { 
            g_objCancelLoadBtn.disabled = !!objOptions.loadCancelDisabled; 
        }
        
        g_objLoaderModal.style.display = 'flex';
    }


    /**
     * Hides the loading modal and resets button visibility.
     */
    function hideLoader() 
    {
        g_objCancelLoadBtn.style.display = 'none';
        g_objCancelSimBtn.style.display = 'none';
        g_objLoaderModal.style.display = 'none';
    }


    /**
     * Clears the input table and resets counters.
     */
    function resetInitialUI()
    {
        g_objInitialTableBody.innerHTML = '';
        g_arrAllLoadedPackages = [];
        
        // Reset display values
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        
        document.getElementById('initial-no-item').style.display = 'block';
    }


    /**
     * Populates summary statistics in the initialization screen.
     */
    function updateInitialSummary(fltVolume, intCount, fltServiceTime)
    {
        document.getElementById('initial-product-volume').textContent = formatNumber(Math.round(fltVolume));
        document.getElementById('initial-product-count').textContent = formatNumber(intCount);
        document.getElementById('initial-service-time').textContent = formatNumber(Math.round(fltServiceTime));
    }


    /**
     * Generates HTML rows for the package data table.
     */
    function appendPackagesToTable(objTableBody, arrPackages)
    {
        if (arrPackages && arrPackages.length > 0) 
        {
            // Hide the "empty state" message if it exists
            const objNoItemText = objTableBody.nextElementSibling;
            if (objNoItemText && objNoItemText.classList.contains('no-item')) 
            {
                objNoItemText.style.display = 'none';
            }
            
            // Sort packages ID alphabetically
            arrPackages.sort((a, b) => a.id.localeCompare(b.id));

            // Generate row HTML using map
            objTableBody.innerHTML = arrPackages.map(createTableRowHTML).join('');
        }
    }


    /**
     * Helper to create a single table row string.
     */
    function createTableRowHTML(objPkg) 
    {
        return `
            <tr>
                <td>${objPkg.id}</td>
                <td>${formatNumber(Math.round(objPkg.volume))}</td>
                <td>${objPkg.service_time}</td>
                <td>${objPkg.height}</td>
                <td>${objPkg.depth}</td>
                <td>${objPkg.width}</td>
            </tr>`;
    }


    /**
     * Formats numbers with commas (thousands separator).
     */
    function formatNumber(fltValue)
    {
        return fltValue ? fltValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : '0';
    }


    /**
     * Populates the Results Dashboard with simulation metrics.
     */
    function updateResultsUI(objResults) 
    {
        g_objLastResults = objResults;
        g_objVisualizeMenu.style.display = 'none';

        // Update Overview Strings
        document.getElementById('result-algorithm-name').textContent = objResults.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = formatNumber(objResults.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = formatNumber(objResults.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = objResults.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = formatNumber(objResults.vehicle_info.total_packed_service_time);

        // Update Performance Metrics
        const { metrics } = objResults;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;

        // Populate packed item list
        const objResultTableBody = document.getElementById('result-item-table-body');
        const objNoItemText = document.getElementById('result-no-item');
        
        objResultTableBody.innerHTML = ''; 
        if (objResults.packed_items && objResults.packed_items.length > 0)
        {
            objNoItemText.style.display = 'none';
            appendPackagesToTable(objResultTableBody, objResults.packed_items);
            
            // Enable visualization features
            g_objVisualizeMenu.style.display = 'inline-flex';
        } 
        else
        {
            objNoItemText.style.display = 'block';
        }
    } //end of updateResultsUI


    /**
     * Opens a new popup window to render the 3D Packing Solution.
     * Contains the complete HTML/JS source for the visualization using Three.js.
     */
    function openVisualizationWindow(strMode = 'static')
    {
        if (!g_objLastResults) 
        {
            alert("No simulation data available to visualize.");
            return;
        }

        const { vehicle_info, packed_items, metrics, loading_sequence, unloading_sequence } = g_objLastResults;
        
        // Embed the 3D Viewer Logic within a dynamic HTML string
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
                        display: ${strMode === 'static' ? 'none' : 'block'};
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

                <!-- Three.js Libraries -->
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"><\/script>
                
                <script>
                    // --- Visualization Initialization ---
                    const strMode = '${strMode}';
                    const objVehicleInfo = ${JSON.stringify(vehicle_info)};
                    let arrPackedItemsData = ${JSON.stringify(packed_items)};
                    const arrLoadingSequence = ${JSON.stringify(loading_sequence || [])};
                    const arrUnloadingSequence = ${JSON.stringify(unloading_sequence || [])};

                    // Setup Scene, Camera, and Renderer
                    const objScene = new THREE.Scene();
                    objScene.background = new THREE.Color(0x282c34);
                    const objCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 20000);
                    const objRenderer = new THREE.WebGLRenderer({ antialias: true });
                    objRenderer.setSize(window.innerWidth, window.innerHeight);
                    document.body.appendChild(objRenderer.domElement);

                    // Add Orbit Controls and Lights
                    const objControls = new THREE.OrbitControls(objCamera, objRenderer.domElement);
                    const objAmbientLight = new THREE.AmbientLight(0xffffff, 0.6);
                    objScene.add(objAmbientLight);
                    const objDirectionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                    objDirectionalLight.position.set(200, 500, 300);
                    objScene.add(objDirectionalLight);

                    // --- Container Construction ---
                    const fltVehicleW = objVehicleInfo.width;
                    const fltVehicleH = objVehicleInfo.height;
                    const fltVehicleD = objVehicleInfo.depth;
                    
                    // Draw Wireframe of the container
                    const objContainerGeom = new THREE.BoxGeometry(fltVehicleW, fltVehicleH, fltVehicleD);
                    const objContainerEdges = new THREE.EdgesGeometry(objContainerGeom);
                    const objContainerLines = new THREE.LineSegments(objContainerEdges, new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 }));
                    
                    // Center the container
                    const objContainerCenter = new THREE.Vector3(fltVehicleW / 2, fltVehicleH / 2, fltVehicleD / 2);
                    objContainerLines.position.copy(objContainerCenter);
                    objScene.add(objContainerLines);
                    
                    // --- Helper: Item Coloring ---
                    const objColorCache = {};
                    // Generate a deterministic color hash based on ID
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

                    const objPackageMeshes = {};

                    // --- Create Individual Item Meshes ---
                    function createPackageMesh(objItem) {
                        if (objItem.width <= 0 || objItem.height <= 0 || objItem.depth <= 0) return null;
                        
                        // Slightly scale down for visual separation between boxes
                        const FLT_VISUAL_SCALE = 0.999;
                        const objItemGeom = new THREE.BoxGeometry(objItem.width * FLT_VISUAL_SCALE, objItem.height * FLT_VISUAL_SCALE, objItem.depth * FLT_VISUAL_SCALE);
                        const objItemMaterial = new THREE.MeshLambertMaterial({ color: getDeterministicColor(objItem.id), transparent: true });
                        const objItemMesh = new THREE.Mesh(objItemGeom, objItemMaterial);
                        
                        // Calculate actual position centered
                        const objCenteredPos = {
                            x: objItem.position_x + objItem.width / 2,
                            y: objItem.position_y + objItem.height / 2,
                            z: objItem.position_z + objItem.depth / 2,
                        };
                        objItemMesh.position.set(objCenteredPos.x, objCenteredPos.y, objCenteredPos.z);
                        // Store metadata for raycasting and interaction
                        objItemMesh.userData = { ...objItem, originalMaterial: objItemMaterial, final_position: objCenteredPos };
                        return objItemMesh;
                    }

                    // Create meshes for all items in payload
                    arrPackedItemsData.forEach(item => {
                        const objMesh = createPackageMesh(item);
                        if (objMesh) objPackageMeshes[item.id] = objMesh;
                    });

                    // Position Camera to see whole container
                    objCamera.position.set(objContainerCenter.x, objContainerCenter.y + fltVehicleH, objContainerCenter.z + fltVehicleD * 1.5);
                    objControls.target.copy(objContainerCenter);
                    objControls.saveState();
                    
                    // --- Label Rendering ---
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
                    
                    // --- Animation Logic ---
                    let blnIsPlaying = false;
                    let objAnimationTimeout = null;
                    const objPlayPauseBtn = document.getElementById('play-pause-btn');
                    const objSpeedSlider = document.getElementById('speed-slider');
                    const objProgressBar = document.getElementById('progress-bar');
                    const objAnimStatus = document.getElementById('animation-status');
                    
                    // Speed Control
                    function getAnimationDelay() { return 1100 - (objSpeedSlider.value * 100); }

                    // Linear Interpolation helper
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

                    let arrAnimationQueue = [];
                    let intCurrentStepIndex = 0;
                    let intVisualStepIndex = 0;

                    // Filter helper for events relevant to viewing
                    function isVisualEvent(objStep) {
                        const arrVisualActions = ['load', 'target', 'relocate', 'deliver', 'settle', 'return_relocated'];
                        return arrVisualActions.includes(objStep.action);
                    }

                    // Main Animation Loop
                    function processAnimationQueue() {
                        // Check completion
                        if (!blnIsPlaying || intCurrentStepIndex >= arrAnimationQueue.length) {
                            objAnimStatus.textContent = 'Animation Complete.';
                            objPlayPauseBtn.textContent = 'Replay';
                            blnIsPlaying = false;
                            return;
                        }

                        // Skip non-visual internal steps
                        while (intCurrentStepIndex < arrAnimationQueue.length && !isVisualEvent(arrAnimationQueue[intCurrentStepIndex])) {
                            intCurrentStepIndex++;
                        }

                        if (intCurrentStepIndex >= arrAnimationQueue.length) {
                            objAnimStatus.textContent = 'Animation Complete.';
                            objPlayPauseBtn.textContent = 'Replay';
                            blnIsPlaying = false;
                            return;
                        }

                        const objStep = arrAnimationQueue[intCurrentStepIndex];
                        const objMesh = objPackageMeshes[objStep.item_id || objStep.item?.id];
                        
                        if (!objMesh) {
                            // Skip invalid items
                            intCurrentStepIndex++;
                            intVisualStepIndex++;
                            objProgressBar.style.width = \`\${(intCurrentStepIndex / arrAnimationQueue.length) * 100}%\`;
                            if(blnIsPlaying) objAnimationTimeout = setTimeout(processAnimationQueue, 50);
                            return;
                        }
                        
                        let duration = getAnimationDelay() * 0.5;
                        // On tween completion, move to next step
                        let onComplete = () => {
                            intCurrentStepIndex++;
                            intVisualStepIndex++;
                            objProgressBar.style.width = \`\${(intCurrentStepIndex / arrAnimationQueue.length) * 100}%\`;
                            if(blnIsPlaying) objAnimationTimeout = setTimeout(processAnimationQueue, getAnimationDelay());
                        };

                        // Execute visualization based on action type
                        switch(objStep.action) {
                            case 'load':
                                objAnimStatus.textContent = \`Loading item\`;
                                // Start above container and drop down
                                objMesh.position.y = fltVehicleH + objMesh.userData.height;
                                objScene.add(objMesh);
                                tween(objMesh.position, objMesh.userData.final_position, duration, onComplete);
                                break;
                                
                            case 'target':
                                objAnimStatus.textContent = \`Targeting item...\`;
                                objMesh.material = new THREE.MeshBasicMaterial({ color: 0xFFFF00, wireframe: true });
                                setTimeout(onComplete, 50);
                                break;
                                
                            case 'relocate':
                                objAnimStatus.textContent = \`Relocating item (blocked)...\`;
                                // Move item OUT of vehicle to temp storage
                                const relocatePos = { x: fltVehicleW + 50, y: fltVehicleH / 2, z: objMesh.position.z };
                                tween(objMesh.position, relocatePos, duration, () => {
                                    objScene.remove(objMesh);
                                    onComplete();
                                });
                                break;
                                
                            case 'deliver':
                                objAnimStatus.textContent = \`Delivering item!\`;
                                objMesh.material = objMesh.userData.originalMaterial;
                                // Move item OUT to destination
                                const deliverPos = { x: fltVehicleW + 50, y: objMesh.position.y, z: objMesh.position.z };
                                tween(objMesh.position, deliverPos, duration, () => {
                                    objScene.remove(objMesh);
                                    onComplete();
                                });
                                break;
                                
                            case 'settle':
                                objAnimStatus.textContent = 'Items settling due to gravity...';
                                // Physics adjustment visual
                                const new_centered_y = objStep.new_y_pos + objMesh.userData.height / 2;
                                tween(objMesh.position, { y: new_centered_y }, duration * 0.8, () => {
                                    objMesh.userData.final_position.y = new_centered_y;
                                    onComplete();
                                });
                                break;
                                
                            case 'return_relocated':
                                objAnimStatus.textContent = \`Returning item to container...\`;
                                const new_pos = objStep.new_pos;
                                const new_centered_pos = {
                                    x: new_pos[0] + objMesh.userData.width / 2,
                                    y: new_pos[1] + objMesh.userData.height / 2,
                                    z: new_pos[2] + objMesh.userData.depth / 2,
                                };
                                const returnStartPos = { x: fltVehicleW + 50, y: new_centered_pos.y, z: new_centered_pos.z };
                                objMesh.position.set(returnStartPos.x, returnStartPos.y, returnStartPos.z);
                                objMesh.material = objMesh.userData.originalMaterial;
                                objScene.add(objMesh);
                                tween(objMesh.position, new_centered_pos, duration, () => {
                                    objMesh.userData.final_position = new_centered_pos;
                                    onComplete();
                                });
                                break;
                                
                            default:
                                intCurrentStepIndex++;
                                intVisualStepIndex++;
                                objProgressBar.style.width = \`\${(intCurrentStepIndex / arrAnimationQueue.length) * 100}%\`;
                                if(blnIsPlaying) objAnimationTimeout = setTimeout(processAnimationQueue, 50);
                                break;
                        }
                    }
                    
                    // --- Player Controls ---
                    function setupAndPlay() {
                        blnIsPlaying = !blnIsPlaying;
                        objPlayPauseBtn.textContent = blnIsPlaying ? 'Pause' : 'Play';
                        if (blnIsPlaying) {
                            processAnimationQueue();
                        } else {
                            clearTimeout(objAnimationTimeout);
                        }
                    }

                    objPlayPauseBtn.addEventListener('click', () => {
                        // Reset functionality for Replay
                        if (objPlayPauseBtn.textContent === 'Replay') {
                            Object.values(objPackageMeshes).forEach(m => objScene.remove(m));
                            arrPackedItemsData.forEach(item => {
                                const objMesh = objPackageMeshes[item.id];
                                if(objMesh) {
                                    const objOrigCentered = {
                                        x: item.position_x + item.width / 2,
                                        y: item.position_y + item.height / 2,
                                        z: item.position_z + item.depth / 2,
                                    };
                                    objMesh.position.copy(objOrigCentered);
                                    objMesh.userData.final_position = objOrigCentered;
                                    objMesh.material = objMesh.userData.originalMaterial;
                                }
                            });
                            // Repopulate for non-load modes
                            if(strMode === 'unload' || strMode === 'static') {
                                Object.values(objPackageMeshes).forEach(m => objScene.add(m));
                            }
                            intCurrentStepIndex = 0;
                            intVisualStepIndex = 0;
                            objProgressBar.style.width = '0%';
                            blnIsPlaying = false;
                        }
                        setupAndPlay();
                    });

                    // Initial State Setup based on mode
                    if (strMode === 'static') {
                        Object.values(objPackageMeshes).forEach(mesh => objScene.add(mesh));
                    } else if (strMode === 'load') {
                        arrAnimationQueue = arrLoadingSequence;
                    } else if (strMode === 'unload') {
                        arrAnimationQueue = arrUnloadingSequence;
                        Object.values(objPackageMeshes).forEach(mesh => objScene.add(mesh));
                    }

                    // --- User Interaction (Clicking Items) ---
                    const objRaycaster = new THREE.Raycaster();
                    const objMouse = new THREE.Vector2();
                    let objSelectedObject = null;
                    const objHighlightMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFF00, transparent: true, opacity: 0.8 });
                    const objInfoDiv = document.getElementById('item-info-panel');
                    
                    window.addEventListener('click', (event) => {
                        // Convert mouse coords
                        objMouse.x = (event.clientX / window.innerWidth) * 2 - 1;
                        objMouse.y = - (event.clientY / window.innerHeight) * 2 + 1;
                        objRaycaster.setFromCamera(objMouse, objCamera);
                        
                        // Check intersection with boxes
                        const arrMeshesForIntersect = Object.values(objPackageMeshes).filter(m => m.parent === objScene);
                        const arrIntersects = objRaycaster.intersectObjects(arrMeshesForIntersect);
                        
                        // Reset previous selection
                        if (objSelectedObject) {
                            if (objSelectedObject.userData.originalMaterial && !objSelectedObject.material.wireframe) {
                                objSelectedObject.material = objSelectedObject.userData.originalMaterial;
                            }
                            objSelectedObject = null;
                        }
                        objInfoDiv.style.display = 'none';
                        
                        // Highlight new selection and show info
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

                    // Start Rendering Loop
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
        
        // Open the generated HTML in a popup
        const objVizWindow = window.open("", "3D Visualization", "width=1200,height=800");
        if (objVizWindow) 
        {
            objVizWindow.document.open();
            objVizWindow.document.write(strHtmlContent);
            objVizWindow.document.close();
            
            // Monitor popup state
            g_objVisualizeMenuBtn.disabled = true;
            const objCheckWindowClosedInterval = setInterval(() => 
            {
                if (objVizWindow.closed) 
                {
                    clearInterval(objCheckWindowClosedInterval);
                    g_objVisualizeMenuBtn.disabled = false;
                }
            }, 500);
        } 
        else 
        {
            alert("Please allow pop-ups for this site to view the visualization.");
        }
    } //end of openVisualizationWindow
}); //end of DOMContentLoaded listener