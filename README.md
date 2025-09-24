# HYBRID PSO-ACO 3D LOADING OPTIMIZATION TOOL

This project provides an interactive, experimental software tool developed for the research titled: **"OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM"**.

It allows for the direct simulation and comparison of three metaheuristic algorithms—Particle Swarm Optimization (PSO), Ant Colony Optimization (ACO), and a proposed hybrid PSO-ACO—in solving complex 3D vehicle loading problems.

---

## 1. Addressing the Research Problem

The core purpose of this tool is to provide a platform to answer the study's central **Statement of the Problem**. Existing algorithms often focus solely on packing density (volume utilization) while neglecting the practical challenges of unloading items in a specific sequence. This leads to inefficient operations, unnecessary item relocations, and sometimes even inaccessible (infeasible) loads.

This software directly addresses these gaps by:

*   **Measuring Operational Viability:** It goes beyond simple packing and simulates the unloading process to calculate critical metrics like **Relocation Count**, **Unloading Feasibility**, and **Unloading Sequence Length**.
*   **Enabling Direct Comparison:** The tool allows users to run standalone PSO, standalone ACO, and the proposed Hybrid PSO-ACO on the exact same problem instance, generating the data needed to answer **Research Questions 1 & 2** regarding loading and unloading optimality.
*   **Testing Scalability:** By allowing simulations across various real-world vehicle capacities from the Amazon dataset, the tool measures **Computation Time** and **Memory Usage**, directly addressing **Research Question 3** on algorithm scalability.
*   **Simulating Dynamic Conditions:** It incorporates a "dynamic constraint" where 10-20% of items are randomly altered post-selection, mimicking real-world disruptions like last-minute order changes and testing the algorithms' robustness.

---

## 2. Alignment with System Architecture (Chapter 3)

The software's architecture is a direct implementation of the designs outlined in Chapter 3 of the research methodology.

### Particle Swarm Optimization (PSO) - (Figure 4)
*   **Implemented in:** `backend/algorithms/pso_algorithm.py`
*   **Logic:** The `runPsoAlgorithm` function follows the PSO flowchart precisely. It initializes a "swarm" of "particles," where each particle is a potential packing sequence. In each iteration, it evaluates each particle's fitness, updates its Personal Best (`pbest`), and updates the Global Best (`gbest`). The `updateParticle` function then calculates a new "velocity" (a series of swaps) to move the particle towards promising solutions.

### Ant Colony Optimization (ACO) - (Figure 5)
*   **Implemented in:** `backend/algorithms/aco_algorithm.py`
*   **Logic:** The `runAcoAlgorithm` function mimics the behavior of ants. It initializes an "ant population" that traverses paths to construct solutions. After each iteration, "pheromones" are evaporated and then deposited on the paths of the best solutions, reinforcing better sequences. The `construct_solution` function uses these pheromone trails to guide subsequent ants.

### Hybrid PSO-ACO Algorithm - (Figure 6)
*   **Implemented in:** `backend/algorithms/hybrid_pso_aco_algorithm.py`
*   **Logic:** This implementation embodies the Pheromone-Augmented Particle Swarm Optimization (PACO) framework. It follows the PSO structure but integrates a key ACO mechanism:
    *   **Pheromone Influence on Velocity:** The `update_particle_hybrid` function contains an augmented velocity equation. A particle's movement is now influenced not just by its `pbest` and the `gbest`, but also by the pheromone matrix, guiding it towards historically successful item orderings.
    *   **Weighted Pheromone Update:** As shown in the yellow box of the hybrid flowchart, after each generation, the top-performing particles (the "elites") are ranked. Their success is used to deposit pheromones, reinforcing the trails that lead to high-quality, unload-feasible solutions. This creates a feedback loop where PSO's global search informs ACO's local memory, and vice versa.

---

## 3. Pre-requisites

*   Python 3.8 or newer
*   `pip` (Python package installer)
*   Git (for cloning the repository)

---

## 4. Installation and Setup

1.  **Clone the Repository:**
    ```bash
    git clone [Your Repository URL]
    cd HYBRID-PSO-ACO-3D-TOOL
    ```

2.  **Install Dependencies:**
    It is highly recommended to use a virtual environment.
    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv/Scripts/activate`

    # Install the required Python libraries
    pip install -r requirements.txt
    ```

3.  **Dataset:**
    *   The project is pre-configured to use small **sample data** located in `backend/sample_data/`. This allows the tool to run immediately for demonstration purposes.
    *   To use the full **2021 Amazon Last Mile Routing Research Challenge Dataset**, you must download it and place the contents into the `backend/almrrc2021/` directory. Then, you will need to comment out the sample data paths and uncomment the real data paths in `backend/data_management/data_loader.py`.

---

## 5. Running the Application

Once the setup is complete, you can start the web server from the project's root directory:

```bash
python backend/app.py
```

Open a web browser and navigate to `http://127.0.0.1:5000` to access the tool.

### How to Use:

1.  Click the **"Modify Simulation"** button.
2.  Select an **Optimization Algorithm** (PSO, ACO, or PSO-ACO).
3.  Choose a **Vehicle Volume Capacity** from the dropdown. The application will begin loading all associated package data. You can cancel this loading process at any time.
4.  Once loading is complete (or canceled), click the **"Simulate"** button to run the experiment.
5.  The results, including all scalability and loading/unloading metrics, will be displayed on the right-hand side.

---

## 6. Directory Structure

-   `backend/`: Contains all server-side Python logic.
    -   `algorithms/`: Implementation of the three core optimization algorithms (PSO, ACO, Hybrid).
    -   `data_management/`: Handles loading, preprocessing, and caching of the dataset.
    -   `simulation/`: Orchestrates the simulation runs and calculates performance metrics.
    -   `sample_data/`: A small subset of the data for quick testing.
-   `static/`: Contains the CSS and JavaScript files for the frontend.
-   `templates/`: Contains the `index.html` file for the user interface.
-   `requirements.txt`: A list of all Python dependencies.