# ASPECT: Algorithm System for Packing Efficiency Comparison and Testing

### **OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM**

## Project Overview

ASPECT is the bespoke computational instrument developed to empirically validate our thesis on logistics optimization. This software addresses a critical deficiency in existing delivery systems: the disconnection between how vehicles are packed (loading) and how they must be efficiently emptied (unloading).

While traditional algorithms optimize strictly for space density—often creating "brick walls" of cargo that trap early-delivery items—ASPECT operationalizes our proposed **Hybrid PSO-ACO** algorithm. This novel approach synthesizes the global search velocity of **Particle Swarm Optimization (PSO)** with the localized, constructive memory of **Ant Colony Optimization (ACO)**.

The software simulates complex, dynamic 3D bin packing scenarios using real-world data to determine if our hybrid model outperforms standalone heuristics in three key dimensions: **Optimization Quality** (Volume Utilization), **Operational Efficiency** (Relocation Count), and **Computational Scalability**.

---

## 1. Research Implementation & System Logic

This application does not merely run a simulation; it acts as a direct translator of the research methodology defined in **Chapter 3** into executable Python code.

### A. Algorithmic Core (The Independent Variables)
The system executes a comparative analysis of three distinct algorithmic behaviors:
1.  **Standalone PSO:** Implemented in `backend/algorithms/pso_algorithm.py`, this models solution generation as "particles" flying through hyperspace, influenced by a heuristic based on service times.
2.  **Standalone ACO:** Implemented in `backend/algorithms/aco_algorithm.py`, this mimics the foraging behavior of ants using a pheromone matrix to reinforce effective loading sequences.
3.  **Hybrid PSO-ACO:** Implemented in `backend/algorithms/hybrid_pso_aco_algorithm.py`, this is the study’s primary contribution. It embeds an **Elitist Pheromone-Guided Velocity Update** within the standard PSO loop (see *Methodology Fig 8*). The swarm learns from the best structural layouts found by ACO, allowing it to navigate out of local optima and find solutions that are both dense and easy to unload.

### B. Mathematical Modeling of Efficiency (The Dependent Variables)
The backend orchestration logic (`backend/simulation/simulation_orchestrator.py`) and metrics engine (`performance_metrics.py`) strictly adhere to the study's quantitative definitions:

*   **Adjusted Volume Utilization ($VU_j$):** The software goes beyond simple bounding boxes. It detects "Fragmented Space"—irregular 3D gaps where no item can fit due to geometry (Methodology Eq 2 & 3). This penalty ensures that we measure *usable* space, not just theoretical volume.
*   **Relocation Count:** The metric engine runs a full unloading simulation (`fnGenerateUnloadingSequence`). It employs a **Recursive Cascade Detection** logic to identify every instance where a non-target item blocks a target package. This quantifies the exact physical effort required for delivery.
*   **Scalability Metrics:** Using the `memory_profiler` library, the system tracks peak RAM usage and execution time (in seconds) to test algorithm stability as vehicle sizes increase.

### C. Data Handling Strategy
The system utilizes the **2021 Amazon Last Mile Routing Research Challenge Dataset**. To handle the massive computational overhead of this dataset within a web environment, `backend/data_management/data_manager.py` implements an intelligent caching strategy. It extracts valid sample routes for specific vehicle capacities and serializes them into local JSON caches, ensuring simulations are consistent and reproducible.

---

## 2. Technical Architecture

The software is engineered for stability and user responsiveness during computationally intensive "NP-Hard" simulations.

*   **Asynchronous Backend:** The Flask server (`main_app.py`) utilizes background threading (`threading.Thread`). This decoupling allows the algorithm to perform heavy mathematical operations (like 3D collision detection) without freezing the web interface.
*   **Graceful Interruptions:** A custom exception handler (`backend/simulation/custom_exceptions.py`) allows the user to abort deeply nested algorithmic loops instantly. This flow control is critical for long-running scalability trials.
*   **3D Visualization:** The frontend (`index.html`) leverages **Three.js** to render the final packed solution. This transforms abstract metric data into a rotatable, interactive 3D model, allowing researchers to visually verify item sequencing and support validity (gravity checks).

---

## 3. Pre-requisites

Ensure the following environments are established before deployment:
*   **Language:** Python 3.8 or higher.
*   **Package Manager:** `pip` (standard Python installer).
*   **Dataset:** 2021 Amazon Last Mile Routing Research Challenge (`eval_route_data.json` and `eval_package_data.json`).

---

## 4. Installation Guide

1.  **Environment Setup:**
    Clone the repository and navigate to the project root. Create and activate a virtual environment for isolation:
    ```bash
    python -m venv venv
    # Windows: venv\Scripts\activate
    # Mac/Linux: source venv/bin/activate
    ```

2.  **Dependency Installation:**
    Install the necessary scientific libraries (`numpy`, `pandas`, `deap`, etc.):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Data Placement:**
    Place the Amazon dataset JSON files into the mandated directory structure:
    `backend/almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/`

4.  **System Initialization:**
    Launch the server orchestration module:
    ```bash
    python backend/main_app.py
    ```
    Access the interface at `http://127.0.0.1:5000` via your preferred web browser.

---

## 5. Experimental Procedure

To replicate the study's experimental design using ASPECT, follow this structured workflow:

1.  **Parameter Configuration:** Click the **Modify Simulation** button. Select an algorithm (PSO, ACO, or PSO-ACO) and a specific Vehicle Volume Capacity.
    *   *Note: First-time loading for a capacity triggers the dataset caching sequence.*
2.  **Constraint Testing (Optional):** Enable the **Dynamic Constraint** toggle to mimic real-time logistics disruptions. This feature randomly extracts 10-20% of the manifest post-optimization to test algorithm adaptability.
3.  **Execution:** Initiate the simulation. The loader will display real-time generational progress.
4.  **Analysis:** Upon completion, examine the generated metrics (Time, Memory, Relocations). Use the **Visualize Result** dropdown to render the container layout or animate the loading/unloading sequence, confirming the physical feasibility of the solution.

---

*This software serves as the technological proof-of-concept for the thesis presented to the faculty. All source code is version-controlled for academic integrity.*