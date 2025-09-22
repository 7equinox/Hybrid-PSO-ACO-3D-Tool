// HYBRID-PSO-ACO-3D-TOOL/static/script.js
document.addEventListener("DOMContentLoaded", () => {
    // Get modal elements
    const modal = document.getElementById("myModal");
    const openBtn = document.getElementById("openModalBtn");
    const closeBtn = document.getElementById("closeModalBtn");
    const runSimBtn = document.getElementById("run-sim-btn");
    const loader = document.getElementById("loader");
    const clearSimBtn = document.getElementById("clear-sim-btn");

    // Get algorithm and capacity selection elements
    const algoButtons = document.querySelectorAll(".modal-options button");
    const capacitySelect = document.getElementById("vehicle-capacity-select");

    let selectedAlgorithm = "PSO"; // Default selected algorithm
    let selectedCapacity = null;

    // --- Modal Interactivity ---
    openBtn.onclick = () => { modal.style.display = "flex"; };
    closeBtn.onclick = () => { modal.style.display = "none"; };
    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    };

    // --- Algorithm Selection Logic ---
    algoButtons.forEach(button => {
        button.addEventListener("click", () => {
            algoButtons.forEach(btn => btn.classList.remove("active"));
            button.classList.add("active");
            selectedAlgorithm = button.getAttribute("data-algo");
        });
    });

    // --- Capacity Selection and Initial Data Loading ---
    capacitySelect.addEventListener("change", async (event) => {
        selectedCapacity = event.target.value;
        if (!selectedCapacity) return;

        showLoader("Loading vehicle data...");
        try {
            const response = await fetch('/get_vehicle_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capacity: selectedCapacity })
            });
            const data = await response.json();

            if (data.error) {
                alert(`Error: ${data.error}`);
            } else {
                updateInitialDataUI(data);
            }
        } catch (error) {
            console.error("Failed to fetch vehicle data:", error);
            alert("An error occurred while loading vehicle data.");
        } finally {
            hideLoader();
        }
    });

    // --- Simulation Execution ---
    runSimBtn.addEventListener("click", async () => {
        if (!selectedCapacity) {
            alert("Please select a vehicle capacity first.");
            return;
        }

        modal.style.display = "none";
        showLoader("Running simulation... This may take a moment.");

        try {
            const response = await fetch('/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    algorithm: selectedAlgorithm,
                    capacity: selectedCapacity
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
        }
    });
    
    // --- Clear Simulation Logic ---
    clearSimBtn.addEventListener("click", () => {
       location.reload(); 
    });


    // --- Helper Functions to Update the UI ---

    function showLoader(message = "Processing...") {
        loader.querySelector('p').textContent = message;
        loader.style.display = 'flex';
    }

    function hideLoader() {
        loader.style.display = 'none';
    }

    function updateInitialDataUI(data) {
        document.getElementById('initial-vehicle-volume').textContent = formatNumber(data.vehicle.capacity_cm3);
        document.getElementById('initial-product-volume').textContent = formatNumber(Math.round(data.vehicle.total_package_volume));
        document.getElementById('initial-product-count').textContent = data.vehicle.num_packages;
        document.getElementById('initial-service-time').textContent = formatNumber(Math.round(data.vehicle.total_service_time));

        const tableBody = document.getElementById('initial-item-table-body');
        const noItemText = document.getElementById('initial-no-item');
        tableBody.innerHTML = ''; // Clear previous data

        if (data.packages && data.packages.length > 0) {
            noItemText.style.display = 'none';
            data.packages.forEach(pkg => {
                tableBody.innerHTML += createTableRow(pkg);
            });
        } else {
            noItemText.style.display = 'block';
        }
    }

    function updateResultsUI(results) {
        // Update result banners
        document.getElementById('result-algorithm-name').textContent = results.algorithm_name;
        document.getElementById('result-vehicle-volume').textContent = formatNumber(results.vehicle_info.capacity_cm3);
        document.getElementById('result-product-volume').textContent = formatNumber(results.vehicle_info.total_packed_volume);
        document.getElementById('result-product-count').textContent = results.vehicle_info.num_packages_loaded;
        document.getElementById('result-service-time').textContent = formatNumber(results.vehicle_info.total_packed_service_time);

        // Update metrics
        const metrics = results.metrics;
        document.getElementById('metric-exec-time').textContent = metrics.computation_time;
        document.getElementById('metric-mem-usage').textContent = metrics.memory_usage_mb;
        document.getElementById('metric-vol-util').textContent = metrics.volume_utilization;
        document.getElementById('metric-reloc-count').textContent = metrics.relocation_count;
        document.getElementById('metric-feasibility').textContent = metrics.unloading_feasibility;
        document.getElementById('metric-seq-len').textContent = metrics.unloading_sequence_length;

        // Update packed items table
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
    
    function createTableRow(pkg) {
         return `
            <tr>
                <td>${pkg.id}</td>
                <td>${formatNumber(Math.round(pkg.volume))}</td>
                <td>${pkg.service_time}</td>
                <td>${pkg.height}</td>
                <td>${pkg.depth}</td> <!-- Note: Length in UI might correspond to depth in data -->
                <td>${pkg.width}</td>
            </tr>
        `;
    }

    function formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
});