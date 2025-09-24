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


    // --- DOM ELEMENT REFERENCES ---
    // Caching references to DOM elements improves performance and code readability.
    const obj_modal = document.getElementById("myModal");
    const obj_openModalBtn = document.getElementById("openModalBtn");
    const obj_closeModalBtn = document.getElementById("closeModalBtn");
    const obj_runSimBtn = document.getElementById("run-sim-btn");
    const obj_loader = document.getElementById("loader");
    const obj_clearSimBtn = document.getElementById("clear-sim-btn");
    const obj_cancelLoadBtn = document.getElementById('cancel-load-btn');
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
            g_bln_isLoadCancelled = false; // Reset cancellation flag on new selection.
            _startIncrementalLoad(g_str_selectedCapacity);
        }
    });

    /**
    * Sets the cancellation flag when the "Cancel" button in the loader is clicked.
    */
    obj_cancelLoadBtn.addEventListener('click', () => {
        g_bln_isLoadCancelled = true;
    });

    /**
    * Initiates the simulation process when the "Simulate" button is clicked.
    */
    obj_runSimBtn.addEventListener("click", () => {
        _runSimulation();
    });

    /**
    * Clears all data and reloads the page to start a new experiment.
    */
    obj_clearSimBtn.addEventListener("click", () => {
        location.reload();
    });


    // --- CORE LOGIC FUNCTIONS ---

    /**
    * Manages the entire incremental data loading process. It fetches package data
    * from the backend page by page until all data is loaded or the user cancels.
    * This corresponds to the 'Dataset Preparation' stage of the methodology.
    * @param {string} str_capacity - The selected vehicle capacity in cm³.
    */
    async function _startIncrementalLoad(str_capacity) {
        _showLoader("Preparing data load...");
        _resetInitialUI();

        let int_currentPage = 1;
        let int_totalPages = 1;
        let flt_runningVolume = 0;
        let flt_runningServiceTime = 0;

        // Loop until all pages are fetched OR the cancellation flag is set.
        while (int_currentPage <= int_totalPages && !g_bln_isLoadCancelled) {
            try {
                const obj_response = await fetch('/get_vehicle_data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ capacity: str_capacity, page: int_currentPage })
                });

                if (!obj_response.ok) {
                    throw new Error(`Server error: ${obj_response.statusText}`);
                }

                const obj_data = await obj_response.json();

                if (int_currentPage === 1 && obj_data.vehicle.pagination_meta) {
                    int_totalPages = obj_data.vehicle.pagination_meta.total_pages;
                    document.getElementById('initial-vehicle-volume').textContent = _formatNumber(obj_data.vehicle.capacity_cm3);
                }

                if (obj_data.packages && obj_data.packages.length > 0) {
                    _appendPackagesToTable(obj_data.packages);
                    g_arr_allLoadedPackages.push(...obj_data.packages);

                    obj_data.packages.forEach(obj_pkg => {
                        flt_runningVolume += obj_pkg.volume;
                        flt_runningServiceTime += obj_pkg.service_time;
                    });

                    _updateInitialSummary(flt_runningVolume, g_arr_allLoadedPackages.length, flt_runningServiceTime);
                }

                const int_totalItems = obj_data.vehicle.pagination_meta.total_items;
                _showLoader(`Loading packages... ${g_arr_allLoadedPackages.length} of ${int_totalItems}`);

                int_currentPage++;

            } catch (obj_error) {
                console.error("Failed during incremental load:", obj_error);
                alert("An error occurred while loading data. Please try again.");
                break; // Exit the loop on error.
            }
        } // End of while loop

        if (g_bln_isLoadCancelled) {
            console.log(`Loading cancelled by user. Loaded ${g_arr_allLoadedPackages.length} packages.`);
        } else {
            console.log("Finished loading all packages.");
        }

        _hideLoader();
    }

    /**
    * Triggers the backend simulation. It gathers all required data (algorithm,
    * capacity, packages), sends it to the server, and awaits the results.
    * This function executes the 'Experimentation Stage' of the methodology.
    */
    async function _runSimulation() {
        if (!g_str_selectedCapacity) {
            alert("Please select a vehicle capacity first.");
            return;
        }
        if (g_arr_allLoadedPackages.length === 0) {
            alert("Please select a vehicle and wait for data to load.");
            return;
        }

        obj_modal.style.display = "none";
        _showLoader("Running simulation... This may take a moment.");
        obj_cancelLoadBtn.style.display = 'none'; // Hide cancel during simulation

        try {
            const obj_response = await fetch('/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    algorithm: g_str_selectedAlgorithm,
                    capacity: g_str_selectedCapacity,
                    packages: g_arr_allLoadedPackages
                }),
            });
            const obj_results = await obj_response.json();

            if (obj_results.error) {
                alert(`Simulation Error: ${obj_results.error}`);
            } else {
                _updateResultsUI(obj_results);
            }
        } catch (obj_error) {
            console.error("Simulation failed:", obj_error);
            alert("A critical error occurred during the simulation.");
        } finally {
            _hideLoader();
            obj_cancelLoadBtn.style.display = 'block'; // Re-show cancel button
        }
    }


    // --- UI HELPER FUNCTIONS ---
    // These functions manipulate the DOM to display data and feedback to the user.

    /**
    * Displays the loading spinner with a custom message.
    * @param {string} [str_message="Processing..."] - The text to display below the spinner.
    */
    function _showLoader(str_message = "Processing...") {
        obj_loader.querySelector('p').textContent = str_message;
        obj_cancelLoadBtn.style.display = 'block';
        obj_loader.style.display = 'flex';
    }

    /**
    * Hides the loading spinner.
    */
    function _hideLoader() {
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