// HYBRID-PSO-ACO-3D-TOOL/static/script.js
document.addEventListener("DOMContentLoaded", () => {
    // --- Elements ---
    const modal = document.getElementById("myModal");
    const openBtn = document.getElementById("openModalBtn");
    const closeBtn = document.getElementById("closeModalBtn");
    const runSimBtn = document.getElementById("run-sim-btn");
    const loader = document.getElementById("loader");
    const clearSimBtn = document.getElementById("clear-sim-btn");
    const algoButtons = document.querySelectorAll(".modal-options button");
    const capacitySelect = document.getElementById("vehicle-capacity-select");
    const initialTableBody = document.getElementById('initial-item-table-body');
    const tableContainer = document.querySelector('.table.white-bg');
    
    // NEW -> Get a reference to the cancel button
    const cancelLoadBtn = document.getElementById('cancel-load-btn');

    // --- State Management ---
    let selectedAlgorithm = "PSO";
    let selectedCapacity = null;
    let allLoadedPackages = []; // Stores all packages for the simulation
    let isCancelled = false; // NEW -> Cancellation flag

    // --- Modal & Algorithm Logic (Unchanged) ---
    openBtn.onclick = () => { modal.style.display = "flex"; };
    closeBtn.onclick = () => { modal.style.display = "none"; };
    window.onclick = (event) => { if (event.target === modal) modal.style.display = "none"; };
    algoButtons.forEach(button => {
        button.addEventListener("click", () => {
            algoButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");
            selectedAlgorithm = button.getAttribute("data-algo");
        });
    });

    // --- Data Loading Logic ---
    capacitySelect.addEventListener("change", (event) => {
        selectedCapacity = event.target.value;
        if (selectedCapacity) {
            isCancelled = false; // <-- NEW: Reset the flag on a new selection
            startIncrementalLoad(selectedCapacity);
        }
    });

    // --- NEW -> Event Listener for the Cancel Button ---
    cancelLoadBtn.addEventListener('click', () => {
        isCancelled = true; // Set the flag to true to stop the loading loop
    });

    // Main function to handle the entire incremental loading process
    async function startIncrementalLoad(capacity) {
        showLoader("Preparing data load...");
        resetInitialUI();
        
        let currentPage = 1;
        let totalPages = 1; 
        
        let runningVolume = 0;
        let runningServiceTime = 0;
        
        // Loop until all pages are fetched OR the user cancels
        while (currentPage <= totalPages && !isCancelled) {
            try {
                const response = await fetch('/get_vehicle_data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ capacity, page: currentPage })
                });
                
                if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
                
                const data = await response.json();
                
                if (currentPage === 1) {
                    totalPages = data.vehicle.pagination_meta.total_pages;
                    document.getElementById('initial-vehicle-volume').textContent = formatNumber(data.vehicle.capacity_cm3);
                }
                
                if (data.packages && data.packages.length > 0) {
                    appendPackagesToTable(data.packages);
                    allLoadedPackages.push(...data.packages);

                    data.packages.forEach(pkg => {
                        runningVolume += pkg.volume;
                        runningServiceTime += pkg.service_time;
                    });
                    
                    updateDynamicSummary(runningVolume, allLoadedPackages.length, runningServiceTime);
                }
                
                const totalItems = data.vehicle.pagination_meta.total_items;
                showLoader(`Loading packages... ${allLoadedPackages.length} of ${totalItems}`);

                currentPage++;
            
            } catch (error) {
                console.error("Failed during incremental load:", error);
                alert("An error occurred while loading data. Please try again.");
                break;
            }
        }
        
        // If the loop finished because it was cancelled, update the totals one last time
        if (isCancelled) {
            console.log(`Loading cancelled by user. Loaded ${allLoadedPackages.length} packages.`);
        } else {
            console.log("Finished loading all packages.");
        }

        hideLoader();
    }

    // --- Simulation Button (added a check for isCancelled) ---
    runSimBtn.addEventListener("click", async () => {
        if (!selectedCapacity) {
            alert("Please select a vehicle capacity first.");
            return;
        }
        if (allLoadedPackages.length === 0) {
            alert("Please select a vehicle and wait for data to load.");
            return;
        }

        modal.style.display = "none";
        showLoader("Running simulation... This may take a moment.");
        // Hide the cancel button during simulation
        cancelLoadBtn.style.display = 'none'; 

        try {
            const response = await fetch('/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    algorithm: selectedAlgorithm,
                    capacity: selectedCapacity,
                    packages: allLoadedPackages
                }),
            });
            const results = await response.json();

            if (results.error) {
                alert(`Simulation Error: ${results.error}`);
            } else {
                updateResultsUI(results);
            }
        } catch (error) {
            console.error("Simulation failed:", error);
            alert("A critical error occurred during the simulation.");
        } finally {
            hideLoader();
            // Important to re-show it in case user opens loader again
            cancelLoadBtn.style.display = 'block'; 
        }
    });

    clearSimBtn.addEventListener("click", () => location.reload());

    // --- UI Helper Functions (with one change to showLoader) ---

    function showLoader(message = "Processing...") {
        loader.querySelector('p').textContent = message;
        // Make sure the cancel button is visible when the loader shows
        cancelLoadBtn.style.display = 'block'; 
        loader.style.display = 'flex';
    }

    function hideLoader() {
        loader.style.display = 'none';
    }

    function resetInitialUI() {
        initialTableBody.innerHTML = '';
        allLoadedPackages = [];
        document.getElementById('initial-vehicle-volume').textContent = '0';
        document.getElementById('initial-product-volume').textContent = '0';
        document.getElementById('initial-product-count').textContent = '0';
        document.getElementById('initial-service-time').textContent = '0';
        document.getElementById('initial-no-item').style.display = 'block';
    }

    function updateDynamicSummary(volume, count, serviceTime) {
        document.getElementById('initial-product-volume').textContent = formatNumber(Math.round(volume));
        document.getElementById('initial-product-count').textContent = formatNumber(count);
        document.getElementById('initial-service-time').textContent = formatNumber(Math.round(serviceTime));
    }
    
    function appendPackagesToTable(packages) {
        const noItemText = document.getElementById('initial-no-item');
        if (packages && packages.length > 0) {
            noItemText.style.display = 'none';
            let rowsHtml = '';
            packages.forEach(pkg => {
                rowsHtml += createTableRow(pkg);
            });
            initialTableBody.innerHTML += rowsHtml;
        }
    }

    function createTableRow(pkg) {
         return `
            <tr>
                <td>${pkg.id}</td>
                <td>${formatNumber(Math.round(pkg.volume))}</td>
                <td>${pkg.service_time}</td>
                <td>${pkg.height}</td>
                <td>${pkg.depth}</td>
                <td>${pkg.width}</td>
            </tr>
        `;
    }

    function formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    function updateResultsUI(results) {
        document.getElementById('result-algorithm-name').textContent = results.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = formatNumber(results.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = formatNumber(results.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = results.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = formatNumber(results.vehicle_info.total_packed_service_time);
        const metrics = results.metrics;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;
        document.getElementById('metric-feasibility').textContent = metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = metrics.unloading_sequence_length;
        const tableBody = document.getElementById('result-item-table-body');
        const noItemText = document.getElementById('result-no-item');
        tableBody.innerHTML = '';
        if (results.packed_items && results.packed_items.length > 0) {
            noItemText.style.display = 'none';
            results.packed_items.forEach(pkg => {
                tableBody.innerHTML += createTableRow(pkg);
            });
        } else {
             noItemText.style.display = 'block';
        }
    }
});