# HYBRID PSO-ACO 3D LOADING OPTIMIZATION TOOL

This project is an interactive, experimental software tool developed for the research titled: **"OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM"**.

It provides a platform for the direct simulation and comparison of three metaheuristic algorithms—Particle Swarm Optimization (PSO), Ant Colony Optimization (ACO), and the proposed hybrid PSO-ACO—on complex, dynamic 3D vehicle loading problems derived from a real-world dataset.

---

## 1. Addressing the Research Problem (Chapter 1)

The primary purpose of this software is to serve as the research instrument to answer the study's central **Statement of the Problem**. Traditional optimization heuristics often excel at maximizing packing density but critically neglect the operational feasibility of unloading items according to a specific delivery sequence. This oversight leads to inefficient last-mile operations, increased item handling (relocations), and in worst-case scenarios, completely blocked or inaccessible packages (infeasible loads).

This software directly addresses these research gaps by:

*   **Measuring Operational Viability:** Going beyond simple volume metrics, the tool simulates the entire unloading process for each solution to calculate the critical dependent variables for this study: **Relocation Count**, **Unloading Feasibility**, and **Unloading Sequence Length**. This directly confronts the issue that existing algorithms often fail to measure unloading efficiency.

*   **Enabling Direct, Fair Comparison:** The tool allows a user to run standalone PSO, standalone ACO, and the proposed Hybrid PSO-ACO on identical problem instances. This experimental design generates the data needed to answer **Research Question 1 (Loading)** and **Research Question 2 (Unloading)** regarding the performance differences among the algorithms.

*   **Testing Scalability:** By allowing simulations across the various real-world vehicle capacities from the Amazon dataset, the tool precisely measures **Computation Time** and **Memory Usage**. This directly addresses **Research Question 3** on algorithm scalability and provides empirical data on which algorithm is most efficient as problem complexity increases.

*   **Simulating Dynamic Conditions:** The software implements the "Dynamic Constraint" specified in the methodology, where 10-20% of items are randomly removed before optimization. This mimics real-world disruptions (e.g., last-minute order cancellations) and tests the robustness and adaptability of each algorithm, a key challenge in dynamic logistics.

---

## 2. Alignment with System Architecture (Chapter 3)

The software's architecture is a direct and faithful implementation of the designs outlined in Chapter 3 of the research methodology.

### Particle Swarm Optimization (PSO) - (Figure 4)
*   **Implementation:** `backend/algorithms/pso_algorithm.py`
*   **How it Aligns:** The `fn_runPsoAlgorithm` function follows the PSO flowchart precisely. It begins by initializing a "swarm" of "particles," where each particle is a candidate packing sequence. In each iteration, it evaluates the multi-objective fitness of each particle, updates its Personal Best (`pbest`), and updates the swarm's Global Best (`gbest`). The `_updateParticle` function then calculates a new "velocity" (a series of item swaps) to guide the particle's search based on its own experience, the swarm's experience, and heuristic information.

### Ant Colony Optimization (ACO) - (Figure 5)
*   **Implementation:** `backend/algorithms/aco_algorithm.py`
*   **How it Aligns:** The `fn_runAcoAlgorithm` function models the behavior of an ant colony. It initializes an "ant population" where each ant constructs a solution path. After each generation, "pheromones" are evaporated globally and then deposited on the paths of the best-performing solutions, reinforcing successful subsequences. The `_constructSolution` function shows how ants probabilistically choose their next step based on a combination of these pheromone trails (collective memory) and local heuristic information.

### Hybrid PSO-ACO Algorithm - (Figure 6)
*   **Implementation:** `backend/algorithms/hybrid_pso_aco_algorithm.py`
*   **How it Aligns:** This file embodies the proposed Pheromone-Augmented Particle Swarm Optimization (PACO) framework. It merges the two architectures:
    *   **Pheromone Influence on Velocity:** The `_updateParticleHybrid` function contains the augmented velocity equation, the core of the hybridization. A particle's movement is now influenced not just by its `pbest` and the `gbest` (PSO), but also by a **new pheromone-guided component**. This component introduces swaps that move items toward positions that are strongly favored by the pheromone matrix, guiding PSO's global search with ACO's learned local-structure knowledge.
    *   **Weighted Pheromone Update:** As shown in the hybrid flowchart, after each generation, the top-performing "elite" particles are used to deposit pheromones. This creates a powerful feedback loop where PSO's global exploration finds good solutions, and the characteristics of those good solutions are encoded into the ACO pheromone matrix to guide future explorations more effectively toward unload-feasible configurations.

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
    *   By default, the project is configured to use the **2021 Amazon Last Mile Routing Research Challenge Dataset**.
    *   Ensure you have downloaded and placed the `eval_route_data.json` and `eval_package_data.json` files in the `backend/almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/` directory.

---

## 5. Running the Application

Once the setup is complete, start the Flask web server from the project's root directory:

```bash
python backend/main_app.py```

Open a web browser and navigate to `http://127.0.0.1:5000` to access the tool.

### How to Use the Tool:

1.  Click the **"Modify Simulation"** gear icon.
2.  Choose an **Optimization Algorithm** to test (PSO, ACO, or the proposed PSO-ACO).
3.  Select a **Vehicle Volume Capacity** from the dropdown. The application will asynchronously load a valid sample route for that capacity. You can cancel this data-loading process.
4.  Once the initial data is loaded, click the **"Simulate"** button to run the experiment.
5.  A loader will appear indicating the algorithm is running. You can cancel the simulation at any point.
6.  Upon completion, the results, including all scalability (Time, Memory) and loading/unloading (Volume Util, Relocations, Feasibility, Sequence Length) metrics, will be displayed on the right-hand side.