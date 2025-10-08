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
    let g_obj_lastResults = null;              // Caches the full result object for visualization.

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
    const obj_visualizeBtn = document.getElementById('visualize-btn'); 
    
    // --- DOM elements for the Guides Modal ---
    const obj_guidesModal = document.getElementById("guidesModal");
    const obj_openGuidesBtn = document.getElementById("openGuidesBtn");
    const obj_closeGuidesBtn = document.getElementById("closeGuidesBtn");
    const obj_gotItBtn = document.getElementById("gotItBtn");


    // --- INITIALIZATION ---
    // This function is called once the page is fully loaded to populate the initial UI elements.
    _fnLoadInitialCapacities();
    // The Guides modal is already set to be visible via inline CSS on page load.

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
    obj_openGuidesBtn.onclick = () => { obj_guidesModal.style.display = "flex"; };
    obj_closeGuidesBtn.onclick = () => { obj_guidesModal.style.display = "none"; };
    obj_gotItBtn.onclick = () => { obj_guidesModal.style.display = "none"; };
    obj_visualizeBtn.addEventListener('click', () => { _fnOpenVisualizationWindow(); });

    window.onclick = (e) => { 
        if (e.target === obj_modal) { obj_modal.style.display = "none"; }
        if (e.target === obj_guidesModal) { obj_guidesModal.style.display = "none"; }
    };

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

    async function _fnStartLoadingDisplayData(strCapacity) {
        g_bln_loadCancellationRequested = false; 
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
                obj_cancelLoadBtn.disabled = false;
                g_obj_loadPollingInterval = setInterval(_fnCheckLoadStatus, 1500);
            } else {
                throw new Error("Failed to start data loading on the server.");
            }
        } catch (error) {
            console.error("Error starting data load:", error);
            alert(`Could not start data load: ${error.message}`);
            _fnHideLoader();
        }
    }

    async function _fnCheckLoadStatus() {
        if (g_bln_loadCancellationRequested || !g_str_currentLoadId) {
            clearInterval(g_obj_loadPollingInterval);
            return;
        }

        _fnShowLoader(`Loading sample route data...`, { showLoadCancel: true });
        
        try {
            const response = await fetch(`/data_loading_status/${g_str_currentLoadId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();
            
            if (data.status === 'completed') {
                clearInterval(g_obj_loadPollingInterval); 
                const result = data.result;
                document.getElementById('initial-vehicle-volume').textContent = _fnFormatNumber(result.vehicle.capacity_cm3);
                if (result.packages && result.packages.length > 0) {
                    _fnAppendPackagesToTable(result.packages);
                    g_arr_allLoadedPackages = result.packages;
                    _fnUpdateInitialSummary(result.vehicle.total_package_volume, result.packages.length, result.vehicle.total_service_time);
                }
                obj_runSimBtn.disabled = false;
                _fnHideLoader();
            } else if (data.status === 'error') {
                clearInterval(g_obj_loadPollingInterval);
                alert(`Data Loading Error: ${data.result.error}`);
                _fnResetInitialUI();
                _fnHideLoader();
            } else if (data.status === 'cancelled') {
                 clearInterval(g_obj_loadPollingInterval);
                 _fnResetInitialUI();
                 obj_runSimBtn.disabled = true;
                 _fnHideLoader();
            }
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_loadPollingInterval);
             alert("Lost connection with the server during data load.");
             obj_runSimBtn.disabled = true;
             _fnHideLoader();
        }
    }

    async function _fnCancelDataLoading() {
        if (!g_str_currentLoadId) return;
        g_bln_loadCancellationRequested = true;
        obj_cancelLoadBtn.disabled = true;
        _fnShowLoader('Cancellation requested. Terminating process… Please wait.', { showLoadCancel: false });
        
        try {
            fetch(`/cancel_data_loading/${g_str_currentLoadId}`, { method: 'POST' });
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

    async function _fnStartSimulation() {
        g_bln_simCancellationRequested = false;
        if (!g_str_selectedCapacity || g_arr_allLoadedPackages.length === 0) {
            alert("Please select a vehicle capacity and wait for its data to load first.");
            return;
        }
        
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
                    dynamic_constraint_enabled: bln_isDynamicConstraintEnabled
                }),
            });
            const data = await response.json();
            if (data.status === 'started') {
                g_str_currentSimulationId = data.simulation_id;
                obj_cancelSimBtn.disabled = false;
                g_obj_simPollingInterval = setInterval(_fnCheckSimulationStatus, 2000);
            } else { throw new Error("Failed to start simulation on the server."); }
        } catch (error) {
            console.error("Error starting simulation:", error);
            alert(`Could not start simulation: ${error.message}`);
            _fnHideLoader();
        }
    }

    /**
     * Periodically polls the backend to check the status and progress of the simulation job.
     */
    async function _fnCheckSimulationStatus() {
        if (g_bln_simCancellationRequested || !g_str_currentSimulationId) {
            clearInterval(g_obj_simPollingInterval);
            return;
        }

        try {
            const response = await fetch(`/simulation_status/${g_str_currentSimulationId}`);
            if (!response.ok) throw new Error(`Server status check failed: ${response.statusText}`);
            const data = await response.json();

            if (data.status === 'running' && data.progress) {
                const progress = data.progress;
                if (progress.total > 0) {
                    _fnShowLoader(
                        `Optimizing... (Generation ${progress.current} / ${progress.total})`, 
                        { showSimCancel: false }
                    );
                } else {
                     _fnShowLoader(
                        progress.message || 'Simulation in progress...', 
                        { showSimCancel: true }
                     );
                }
            }
            
            if (data.status === 'completed') {
                clearInterval(g_obj_simPollingInterval);
                _fnUpdateResultsUI(data.result);
                _fnHideLoader();
            } else if (data.status === 'error') {
                clearInterval(g_obj_simPollingInterval);
                alert(`Simulation Error: ${data.result.error}`);
                _fnHideLoader();
            } else if (data.status === 'cancelled') {
                 clearInterval(g_obj_simPollingInterval);
                 _fnHideLoader();
            }
        } catch (error) {
             console.error("Polling error:", error);
             clearInterval(g_obj_simPollingInterval);
             alert("Lost connection with the server.");
             _fnHideLoader();
        }
    }
    
    async function _fnCancelSimulation() {
        if (!g_str_currentSimulationId) return;
        g_bln_simCancellationRequested = true;
        obj_cancelSimBtn.disabled = true;
        _fnShowLoader('Cancellation requested. Terminating process… Please wait.', { showSimCancel: false });
        try {
            fetch(`/cancel_simulation/${g_str_currentSimulationId}`, { method: 'POST' });
            
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
    
    function _fnShowLoader(strMessage = "Processing...", options = {}) {
        obj_loader.querySelector('p').textContent = strMessage;
        obj_cancelLoadBtn.style.display = options.showLoadCancel ? 'block' : 'none';
        obj_cancelSimBtn.style.display = options.showSimCancel ? 'block' : 'none';
        if (options.showSimCancel) { obj_cancelSimBtn.disabled = !!options.simCancelDisabled; }
        if (options.showLoadCancel) { obj_cancelLoadBtn.disabled = !!options.loadCancelDisabled; }
        obj_loader.style.display = 'flex';
    }

    function _fnHideLoader() {
        obj_cancelLoadBtn.style.display = 'none';
        obj_cancelSimBtn.style.display = 'none';
        obj_loader.style.display = 'none';
    }

    function _fnResetInitialUI() {
        obj_initialTableBody.innerHTML = '';
        g_arr_allLoadedPackages = [];
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        document.getElementById('initial-no-item').style.display = 'block';
    }

    function _fnUpdateInitialSummary(fltVolume, intCount, fltServiceTime) {
        document.getElementById('initial-product-volume').textContent = _fnFormatNumber(Math.round(fltVolume));
        document.getElementById('initial-product-count').textContent = _fnFormatNumber(intCount);
        document.getElementById('initial-service-time').textContent = _fnFormatNumber(Math.round(fltServiceTime));
    }

    function _fnAppendPackagesToTable(arrPackages) {
        if (arrPackages && arrPackages.length > 0) {
            document.getElementById('initial-no-item').style.display = 'none';
            obj_initialTableBody.innerHTML = arrPackages.map(_fnCreateTableRow).join('');
        }
    }

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

    function _fnFormatNumber(numValue) {
        return numValue ? numValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : '0';
    }

    function _fnUpdateResultsUI(objResults) {
        g_obj_lastResults = objResults;
        obj_visualizeBtn.style.display = 'none'; 

        document.getElementById('result-algorithm-name').textContent = objResults.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = _fnFormatNumber(objResults.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = _fnFormatNumber(objResults.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = objResults.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = _fnFormatNumber(objResults.vehicle_info.total_packed_service_time);

        const { metrics } = objResults;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;
        document.getElementById('metric-feasibility').textContent = metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = metrics.unloading_sequence_length;

        const tableBody = document.getElementById('result-item-table-body');
        const noItemText = document.getElementById('result-no-item');
        tableBody.innerHTML = ''; 
        if (objResults.packed_items && objResults.packed_items.length > 0) {
            noItemText.style.display = 'none';
            tableBody.innerHTML = objResults.packed_items.map(_fnCreateTableRow).join('');
            obj_visualizeBtn.style.display = 'inline-flex';
        } else {
            noItemText.style.display = 'block';
        }
    }

    /**
     * MODIFIED: Implemented the ultimate failsafe to prevent rendering invalid items.
     */
    function _fnOpenVisualizationWindow() {
        if (!g_obj_lastResults) {
            alert("No simulation data available to visualize.");
            return;
        }

        const { vehicle_info, packed_items } = g_obj_lastResults;
        
        const htmlContent = `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>3D Packing Visualization</title>
                <style>
                    body { margin: 0; overflow: hidden; font-family: sans-serif; }
                    canvas { display: block; }
                    .info-panel {
                        position: absolute;
                        top: 10px;
                        padding: 10px;
                        background: rgba(0, 0, 0, 0.7);
                        color: white;
                        border-radius: 5px;
                        font-size: 14px;
                        line-height: 1.5;
                        pointer-events: none;
                    }
                    #item-info-panel {
                        left: 10px;
                        display: none; 
                    }
                    #item-info-panel strong { color: #e08128; }
                    #controls-panel {
                        right: 10px;
                        text-align: right;
                    }
                    #controls-panel button {
                        margin-top: 5px;
                        padding: 8px 12px;
                        background: #333;
                        color: white;
                        border: 1px solid #555;
                        border-radius: 5px;
                        cursor: pointer;
                        pointer-events: auto;
                    }
                    #controls-panel button:hover { background: #555; }
                </style>
            </head>
            <body>
                <div id="item-info-panel" class="info-panel"></div>
                <div id="controls-panel" class="info-panel">
                    <b>Controls:</b> Left-Click to Rotate, Right-Click to Pan, Scroll to Zoom.
                    <br/><button id="reset-view-btn">Reset View</button>
                </div>

                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"><\/script>
                
                <script>
                    const scene = new THREE.Scene();
                    scene.background = new THREE.Color(0x282c34);
                    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 20000);
                    const renderer = new THREE.WebGLRenderer({ antialias: true });
                    renderer.setSize(window.innerWidth, window.innerHeight);
                    document.body.appendChild(renderer.domElement);

                    const controls = new THREE.OrbitControls(camera, renderer.domElement);
                    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
                    scene.add(ambientLight);
                    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
                    directionalLight.position.set(200, 500, 300);
                    scene.add(directionalLight);

                    const vehicleW = ${vehicle_info.width};
                    const vehicleH = ${vehicle_info.height};
                    const vehicleD = ${vehicle_info.depth};

                    const containerGeom = new THREE.BoxGeometry(vehicleW, vehicleH, vehicleD);
                    const containerEdges = new THREE.EdgesGeometry(containerGeom);
                    const containerLines = new THREE.LineSegments(containerEdges, new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 }));
                    const containerCenter = new THREE.Vector3(vehicleW / 2, vehicleH / 2, vehicleD / 2);
                    containerLines.position.copy(containerCenter);
                    scene.add(containerLines);
                    
                    const colorCache = {};
                    function getDeterministicColor(id) {
                        if (!colorCache[id]) {
                            let hash = 0;
                            for (let i = 0; i < id.length; i++) {
                                hash = id.charCodeAt(i) + ((hash << 5) - hash);
                                hash = hash & hash;
                            }
                            const hue = Math.abs(hash % 360);
                            colorCache[id] = new THREE.Color(\`hsl(\${hue}, 80%, 60%)\`);
                        }
                        return colorCache[id];
                    }

                    const packageMeshes = [];
                    const packedItems = ${JSON.stringify(packed_items)};
                    packedItems.forEach(item => {
                        // MODIFIED: This is the final client-side failsafe.
                        // It explicitly checks that an item has valid 3D dimensions before
                        // attempting to render it. This guarantees that even if corrupt data
                        // were to reach the frontend, it would simply be ignored rather than
                        // causing a visual artifact.
                        if (item.width > 0 && item.height > 0 && item.depth > 0) {
                            const visualScale = 0.999;
                            const itemGeom = new THREE.BoxGeometry(
                                item.width * visualScale, 
                                item.height * visualScale, 
                                item.depth * visualScale
                            );
                            
                            const itemMaterial = new THREE.MeshLambertMaterial({ color: getDeterministicColor(item.id) });
                            const itemMesh = new THREE.Mesh(itemGeom, itemMaterial);
                            itemMesh.position.set(
                                item.position_x + item.width / 2,
                                item.position_y + item.height / 2,
                                item.position_z + item.depth / 2
                            );
                            itemMesh.userData = item;
                            scene.add(itemMesh);
                            packageMeshes.push(itemMesh);
                        }
                    });
                    
                    const maxDim = Math.max(vehicleW, vehicleH, vehicleD);
                    camera.position.x = -maxDim; 
                    camera.position.y = containerCenter.y;
                    camera.position.z = containerCenter.z;
                    controls.target.copy(containerCenter);
                    
                    controls.saveState();

                    const raycaster = new THREE.Raycaster();
                    const mouse = new THREE.Vector2();
                    let selectedObject = null;
                    const highlightMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFF00, transparent: true, opacity: 0.8 });
                    const infoDiv = document.getElementById('item-info-panel');
                    
                    function createTextSprite(message, position, fontSize = 14) {
                        const canvas = document.createElement('canvas');
                        const context = canvas.getContext('2d');
                        context.font = \`Bold \${fontSize}px Arial\`;
                        const textWidth = context.measureText(message).width;
                        canvas.width = textWidth + 20;
                        canvas.height = fontSize + 20;
                        
                        context.font = \`Bold \${fontSize}px Arial\`;
                        context.fillStyle = 'white';
                        context.textAlign = 'center';
                        context.textBaseline = 'middle';
                        context.fillText(message, canvas.width / 2, canvas.height / 2);
                        
                        const texture = new THREE.CanvasTexture(canvas);
                        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
                        const sprite = new THREE.Sprite(spriteMaterial);
                        sprite.scale.set(canvas.width, canvas.height, 1.0);
                        sprite.position.copy(position);
                        scene.add(sprite);
                    }

                    const labelOffset = 30;
                    createTextSprite('Back', new THREE.Vector3(vehicleW + labelOffset, containerCenter.y, containerCenter.z));
                    createTextSprite('Front', new THREE.Vector3(-labelOffset, containerCenter.y, containerCenter.z));
                    createTextSprite('Top', new THREE.Vector3(containerCenter.x, vehicleH + labelOffset, containerCenter.z));
                    createTextSprite('Bottom', new THREE.Vector3(containerCenter.x, -labelOffset, containerCenter.z));
                    createTextSprite('Right Side', new THREE.Vector3(containerCenter.x, containerCenter.y, vehicleD + labelOffset));
                    createTextSprite('Left Side', new THREE.Vector3(containerCenter.x, containerCenter.y, -labelOffset));
                    
                    document.getElementById('reset-view-btn').addEventListener('click', () => {
                        controls.reset();
                    });

                    window.addEventListener('click', (event) => {
                        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
                        mouse.y = - (event.clientY / window.innerHeight) * 2 + 1;
                        raycaster.setFromCamera(mouse, camera);
                        const intersects = raycaster.intersectObjects(packageMeshes);

                        if (selectedObject) {
                            selectedObject.material = selectedObject.userData.originalMaterial;
                            selectedObject = null;
                        }
                        infoDiv.style.display = 'none';

                        if (intersects.length > 0) {
                            const intersected = intersects[0].object;
                            selectedObject = intersected;
                            selectedObject.userData.originalMaterial = selectedObject.material;
                            selectedObject.material = highlightMaterial;
                            
                            const data = intersected.userData;
                            infoDiv.style.display = 'block';
                            infoDiv.innerHTML = \`
                                <strong>Product ID:</strong> \${data.id}<br>
                                <strong>Volume:</strong> \${Math.round(data.volume).toLocaleString()} cm³<br>
                                <strong>Service Time:</strong> \${data.service_time} s<br>
                                <strong>Dimensions (W×H×D):</strong> \${data.width}×\${data.height}×\${data.depth} cm
                            \`;
                        }
                    });

                    function animate() {
                        requestAnimationFrame(animate);
                        controls.update();
                        renderer.render(scene, camera);
                    }
                    animate();
                    
                    window.addEventListener('resize', () => {
                        camera.aspect = window.innerWidth / window.innerHeight;
                        camera.updateProjectionMatrix();
                        renderer.setSize(window.innerWidth, window.innerHeight);
                    }, false);
                <\/script>
            </body>
            </html>
        `;
        
        const vizWindow = window.open("", "3D Visualization", "width=900,height=700");
        vizWindow.document.open();
        vizWindow.document.write(htmlContent);
        vizWindow.document.close();

        obj_visualizeBtn.disabled = true;
        const checkWindowClosed = setInterval(() => {
            if (vizWindow.closed) {
                clearInterval(checkWindowClosed);
                obj_visualizeBtn.disabled = false;
                console.log("Visualization window closed, button re-enabled.");
            }
        }, 500);
    }
});