# OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES
# Main Project Documentation

## 1. System Overview

This project provides the backend implementation for a research tool designed to solve dynamic 3D loading problems for delivery vehicles. It implements and compares three metaheuristic algorithms: standalone Particle Swarm Optimization (PSO), standalone Ant Colony Optimization (ACO), and a novel Hybrid PSO-ACO algorithm.

The system is designed to directly address the research objectives outlined in the project's "Statement of the Problem" by providing a platform for experimental evaluation based on metrics like volume utilization, unloading feasibility, and scalability.

The backend is built with Python using the Flask framework and communicates with the provided HTML/CSS/JS frontend.

## 2. Prerequisites

Before running the tool, ensure you have the following installed:
*   **Python** (version 3.8 or newer)
*   **pip** (Python package installer)
*   The **2021 Amazon Last Mile Routing Research Challenge Dataset**. The entire `almrrc2021` folder must be placed inside the `backend` directory.

## 3. How to Set Up and Run the Tool

Follow these steps to get the application running:

**Step 1: Set up the Backend**
1.  Navigate to the `backend` directory in your terminal:
    ```bash
    cd path/to/optimizing_delivery_vehicles/backend
    ```
2.  (Recommended) Create and activate a Python virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  Install the required Python libraries using the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
4.  Start the Flask server:
    ```bash
    python app.py
    ```
    The backend server will now be running at `http://127.0.0.1:5000`.

**Step 2: Run the Frontend**
1.  Navigate to the `frontend` directory.
2.  Open the `index.html` file in a modern web browser (like Chrome or Firefox).

The frontend will automatically connect to the backend server, and you can now run simulations.

## 4. Alignment with Chapter 3 Methodology

This implementation strictly follows the methodology and system architectures defined in Chapter 3.

### System Architecture Implementation

*   **Particle Swarm Optimization (PSO)**: Implemented in `backend/algorithms/pso.py`. It follows the specified flowchart:
    1.  `__init__`: Initializes a population of particles, where each particle's "position" is a unique permutation of the items to be loaded.
    2.  `run` loop: Iteratively updates particle positions by influencing them towards their personal best (`pBest`) and the global best (`gBest`) solutions found so far.
    3.  `_fitness_function`: Evaluates each particle's solution by using a 3D packing library (`py3dbp`) to calculate the total volume of packed items.

*   **Ant Colony Optimization (ACO)**: Implemented in `backend/algorithms/aco.py`. It mirrors the ACO flowchart:
    1.  `__init__`: Initializes a pheromone matrix where `T(i, j)` represents the desirability of placing item `j` immediately after item `i`.
    2.  `run` loop:
        *   Ants construct solutions probabilistically based on pheromone levels and a heuristic (item volume).
        *   `Evaporation`: Pheromone trails are globally reduced.
        *   `Deposition`: Ants deposit pheromones on the paths of the solutions they created, with better solutions depositing more pheromones.
    3.  The process converges towards solutions with highly-trafficked (high pheromone) paths.

*   **Hybrid PSO-ACO Algorithm**: Implemented in `backend/algorithms/hybrid_pso_aco.py`, this follows the "Pheromone-Augmented Particle Swarm Optimization" architecture:
    1.  `__init__`: Initializes both PSO particles and an ACO pheromone matrix.
    2.  The main loop is driven by PSO, evaluating `pBest` and `gBest`.
    3.  **Key Hybridization Step 1 - Weighted Pheromone Update**: After each PSO iteration, the best-performing particles (elites) are ranked. They then deposit pheromones on the matrix, reinforcing the item sequences that led to good solutions (`_update_pheromones` function). This directly integrates ACO's memory mechanism into PSO.
    4.  **Key Hybridization Step 2 - Pheromone-Guided Velocity**: During the particle position update (`_update_particle_position`), a new component is added. In addition to moving towards `pBest` and `gBest`, a particle's item sequence is slightly perturbed based on the strongest pheromone trails, nudging the swarm towards patterns found to be effective by the entire colony.

## 5. Answering the Statement of the Problem

The developed tool directly facilitates answering the three core research questions:

*   **RQ1 (Optimal Item Loading)** & **RQ2 (Optimal Item Unloading)**:
    By selecting any of the three algorithms and running a simulation, the user is presented with metrics for **Volume Utilization**, **Relocation Count**, **Unloading Feasibility**, and **Unloading Sequence Length**. These outputs can be recorded over multiple runs (as described in the methodology) to statistically compare the performance of the Hybrid PSO-ACO against the standalone algorithms.

*   **RQ3 (Scalability)**:
    The frontend allows the user to select from different **Vehicle Volume Capacities**. Each capacity corresponds to a different problem instance from the dataset with a varying number of items. By running simulations for each capacity and recording the metrics (especially `Solution Quality Degradation`, `Feasibility Rate`, and `Convergence Stability` which can be derived from execution time), the user can directly compare how each algorithm's performance scales as the problem complexity increases.

This tool provides the complete experimental framework required to generate the data necessary for your research analysis.

Perfect 👍 since you have **large storage available for the dataset**, you should make that crystal clear in your `README.md`.

That way, anyone using your project knows **where to get the data, how to store it, and how it connects to your system**.

Here’s what I suggest adding:

#### **6. Dataset Access**

This project uses the **2021 Amazon Last Mile Routing Research Challenge (ALM-RRC) Dataset**, which is required for running simulations.

Due to GitHub’s file size limitations, the dataset is **not included in this repository**. Instead, you can download it from the provided storage:

* **Download Link:** \[[Registry of Open Data on AWS](https://registry.opendata.aws/amazon-last-mile-challenges/)]
* **Size:** \~3 GB total
* **Contents:** Training and evaluation JSON files (`route_data.json`, `package_data.json`, `travel_times.json`, etc.)

Once downloaded, place the dataset inside the `backend` folder:

```plaintext
Hybrid-PSO-ACO-3D-Tool/
├── backend/
│   ├── almrrc2021/
│   │   ├── almrrc2021-data-training/
│   │   └── almrrc2021-data-evaluation/
│   ├── assets/
│   ├── algorithms/
│   └── app.py
├── frontend/
└── README.md
```

#### **7. Notes on Large Dataset Handling**

* The dataset is **too large to be stored in GitHub**; it is excluded via `.gitignore`.
* Ensure that the dataset folder structure matches exactly as shown above.