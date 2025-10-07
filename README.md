# HYBRID PSO-ACO 3D LOADING OPTIMIZATION TOOL

This project presents an interactive software instrument developed to empirically validate the research titled: **"OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM"**.

The application serves as a high-fidelity simulation environment for the rigorous comparison of three metaheuristic algorithms: Particle Swarm Optimization (PSO), Ant Colony Optimization (ACO), and our proposed hybrid PSO-ACO. These algorithms are applied to solve complex 3D vehicle loading problems using a real-world dataset, providing a robust platform for experimental analysis.

---

## 1. Addressing the Research Problem (Chapter 1)

The central purpose of this software is to provide definitive answers to the study's **Statement of the Problem**. The core challenge addressed is that conventional packing algorithms are designed to maximize one objective—how much can be fit into a space—while failing to consider a crucial operational reality: the efficiency of unloading packages according to a pre-defined delivery route. This gap leads to operational bottlenecks, excessive package handling, and potentially infeasible unloading scenarios where packages are physically blocked.

This software is engineered to bridge this critical gap by providing the means to test our research hypotheses:

*   **Quantifying Unloading Efficiency:** The tool moves beyond simple density metrics. For every potential solution, it simulates the entire unloading sequence to compute the study's key dependent variables: **Relocation Count**, **Unloading Feasibility**, and **Unloading Sequence Length**. This directly confronts the primary deficiency in existing models and provides the data to answer **Research Question 1 (Loading)** and **Research Question 2 (Unloading)** by comparing how effectively each algorithm minimizes wasted operational effort.

*   **Evaluating Scalability and Resourcefulness:** The software meticulously tracks **Computation Time** and **Memory Usage** for every simulation run. This provides the empirical data required to address **Research Question 3**, which investigates how each algorithm scales in performance and resource consumption as the problem size increases.

*   **Simulating Real-World Disruptions:** A key feature is the ability to toggle a **Dynamic Constraint**. When activated, this feature mimics real-world uncertainty by removing 10-20% of packages just before optimization begins, testing the adaptability and robustness of each algorithm against unforeseen changes—a common challenge in logistics.

*   **NEW — Intuitive Result Visualization:** To make the complex, three-dimensional output of the algorithms understandable, the tool now includes an **interactive 3D visualization** of the final packed vehicle. This feature allows users to intuitively grasp why a certain packing arrangement resulted in a high or low relocation count, transforming abstract metrics into a tangible and explorable model.

---

## 2. System Architecture and Performance Strategy (Chapter 3)

The software's architecture is a direct translation of the designs specified in Chapter 3 of the methodology. Further, it incorporates a deliberate performance strategy to ensure the tool is practical for real-time analysis and demonstration on standard hardware.

### Algorithm Implementation
*   **Particle Swarm Optimization (PSO) - (Figure 4):** Implemented in `backend/algorithms/pso_algorithm.py`, this module simulates a swarm of particles (candidate solutions) navigating a search space. Each particle adjusts its trajectory based on its own best-found solution and the global best-found solution of the swarm.

*   **Ant Colony Optimization (ACO) - (Figure 5):** Implemented in `backend/algorithms/aco_algorithm.py`, this module models the foraging behavior of ants. It uses a probabilistic construction approach where artificial ants build solutions based on "pheromone trails," a collective memory of which solution components have historically led to high-quality results.

*   **Hybrid PSO-ACO Algorithm - (Figure 6):** The core of our research, implemented in `backend/algorithms/hybrid_pso_aco_algorithm.py`. This novel architecture integrates ACO's pheromone mechanism directly into PSO's velocity update equation. This allows the global-search strength of PSO to be intelligently guided by the local, constructive learning of ACO, creating a feedback loop designed to rapidly converge on solutions that are both space-efficient and operationally sound.

### Strategy for Performance Optimization

To ensure a fluid and practical user experience during live demonstrations, particularly on hardware with limited physical memory, a multi-faceted performance strategy was implemented:

1.  **Strategic Down-Sampling (`MAX_SAMPLE_SIZE = 400`):** Instead of processing the entire dataset of over 80,000 items, which is computationally infeasible, the system employs volume-constrained stratified sampling to create a smaller, representative problem instance. This reduces memory pressure and algorithm complexity while preserving the statistical properties of the original dataset.

2.  **Parameter Tuning:** The operational parameters for each algorithm (e.g., `intNumParticles`, `intNumAnts`, `intMaxGenerations`) have been tuned to balance search thoroughness with execution speed. The current values (`10` agents, `10` generations) are set to achieve demonstration runtimes of approximately 3-10 minutes per simulation for PSO and Hybrid PSO-ACO. On the other hand, ACO has a running time of approximately 40-50 minutes.

3.  **Computational Memoization (Fitness Caching):** The most computationally intensive task is evaluating the fitness of a given packing solution. A cache has been implemented within the `simulation_orchestrator`. If an algorithm attempts to evaluate a solution that has been seen before, the cached result is returned instantly, avoiding redundant calculations and significantly accelerating the optimization process.

---

## 3. Pre-requisites

*   Python 3.8+
*   `pip` (Python package installer)
*   Git (for cloning the repository)

---

## 4. Installation and Setup

1.  **Clone the Repository:**
    ```bash
    git clone [Your Repository URL]
    cd [repository-folder-name]
    ```

2.  **Set Up a Virtual Environment (Highly Recommended):**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate the environment
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Dataset Configuration:**
    *   This project is configured to use the **2021 Amazon Last Mile Routing Research Challenge Dataset**.
    *   Ensure the `eval_route_data.json` and `eval_package_data.json` files are placed within the `backend/almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/` directory.

---

## 5. Running the Application

Once the setup is complete, launch the Flask web server from the project's root directory:

```bash
python backend/main_app.py
```

Open a web browser and navigate to `http://127.0.0.1:5000`.

### How to Use the Tool:

The application interface is divided into a left panel (Initial Dataset) and a right panel (Simulation Results). The following steps guide a typical experimental workflow:

1.  **Open Simulation Settings:**
    *   Begin by clicking the **"Modify Simulation"** gear icon at the top right of the screen. This will open the main configuration modal.

2.  **Select an Algorithm:**
    *   Choose one of the three optimization algorithms to test: **PSO**, **ACO**, or the hybrid **PSO-ACO**.

3.  **Choose a Vehicle:**
    *   Select a **Vehicle Volume Capacity** from the dropdown menu. The application will immediately contact the server to load a valid, sample set of packages corresponding to that vehicle size.
    *   Once loaded, the left panel will populate with the initial vehicle and package data.

4.  **Configure the Dynamic Constraint:**
    *   Use the toggle switch to **enable or disable** the dynamic constraint. When enabled, the simulation mimics a real-world disruption by randomly removing 10-20% of packages before optimization, forcing the algorithm to adapt.

5.  **Run the Simulation:**
    *   Press the **"Simulate"** button to begin the experiment. A loading indicator will appear.
    *   **NEW:** The loader will now display real-time feedback from the backend, showing the current **generation number** of the running algorithm (e.g., "Generation 5 / 10"). This provides a clear indication of progress during longer simulations.
    *   You may cancel the process at any time using the "Cancel Simulation" button.

6.  **Analyze the Results:**
    *   Upon completion, the right-hand panel will display the comprehensive outcome. This includes the final loaded vehicle statistics and a full breakdown of key performance metrics (Execution Time, Memory Usage, Volume Utilization, Relocation Count, etc.).

7.  **NEW — Visualize the Solution:**
    *   If the simulation produces a valid packing solution, a **"Visualize Packing"** button will appear next to the "Loading/Unloading Metrics" title.
    *   Clicking this button will launch a new window containing a fully interactive 3D model of the packed vehicle. You can **rotate, pan, and zoom** to inspect the layout.
    *   **Click on any package** within the 3D model to highlight it and display its detailed information (Product ID, Volume, Service Time, and Dimensions) in a convenient info panel.