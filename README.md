# HYBRID-PSO-ACO-3D-TOOL

This repository contains the source code for the research project titled: "OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM".

The tool provides a web-based interface to simulate and compare the performance of three optimization algorithms—Particle Swarm Optimization (PSO), Ant Colony Optimization (ACO), and a hybrid PSO-ACO—on a 3D vehicle loading problem using the 2021 Amazon Last Mile Routing Research Challenge Dataset.

## Prerequisites

Before running the application, ensure you have the following installed:

1.  **Python 3.8+**: The backend is built using Python.
2.  **Pip**: Python's package installer is required to install dependencies.
3.  **Virtual Environment (Recommended)**: To maintain a clean project environment, it's highly recommended to use a virtual environment.

## Installation and Setup

1.  **Clone the repository or download the source code.**

2.  **Navigate to the project directory:**
    ```bash
    cd HYBRID-PSO-ACO-3D-TOOL
    ```

3.  **Create and activate a virtual environment:**
    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

4.  **Install the required dependencies from `requirements.txt`:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Tool

1.  **Ensure you are in the root directory (`HYBRID-PSO-ACO-3D-TOOL/`) and your virtual environment is activated.**

2.  **Run the Flask application:**
    ```bash
    python backend/app.py
    ```

3.  **Open your web browser and navigate to the following address:**
    [http://127.0.0.1:5000](http://127.0.0.1:5000)

4.  **Using the Interface:**
    *   Click on the "Modify Simulation" gear icon to open the simulation settings modal.
    *   Choose the desired **Optimization Algorithm** and **Vehicle Volume Capacity**.
    *   Click the "Simulate" button to run the optimization process. The backend will execute the selected algorithm, and the results (metrics and packed item list) will be displayed on the right-hand side of the screen. The initial dataset for the selected vehicle will appear on the left.

## Alignment with Research Methodology (Chapter 3)

This tool is a direct implementation of the methodology described in Chapter 3 of the research paper.

*   **System Architecture:**
    *   `backend/algorithms/pso.py`: Implements the standalone Particle Swarm Optimization algorithm as visualized in Figure 5.
    *   `backend/algorithms/aco.py`: Implements the standalone Ant Colony Optimization algorithm as visualized in Figure 6.
    *   `backend/algorithms/hybrid_pso_aco.py`: Implements the proposed hybrid Pheromone-Augmented Particle Swarm Optimization (PACO) as detailed in Figure 7. It integrates the pheromone update mechanism from ACO directly into the PSO velocity update loop.

*   **Dataset and Data Preparation:**
    *   `backend/utils/data_loader.py`: Handles the "Dataset Preparation" phase by loading and parsing the specified `eval_route_data.json` and `eval_package_data.json` files from the Amazon dataset. It filters packages based on the selected vehicle capacity.

*   **Experimentation Stage:**
    *   The `/simulate` endpoint in `backend/app.py` orchestrates the "Experimentation Stage." Although the frontend triggers a single run for visualization, the underlying structure is built to be extendable for the 30 independent runs required for statistical analysis.
    *   The "Dynamic Constraint" (last-minute item insertion/removal) is handled within the `problem_solver.py` module, which re-optimizes the solution after the change.

*   **Performance Metrics:**
    *   `backend/utils/metrics_calculator.py`: This module is dedicated to calculating all the dependent variables outlined in the methodology:
        *   **Loading/Unloading Metrics (RQ1 & RQ2):** Volume Utilization, Relocation Count, Unloading Feasibility, and Unloading Sequence Length.
        *   **Scalability Metrics (RQ3):** Computation time and Memory Usage are measured using Python's `time` and `memory_profiler` modules.

## Answering the Statement of the Problem

This tool was designed specifically to address the core research questions and test the stated hypotheses.

1.  **Addresses the Core Problem:** The tool tackles the challenge of optimizing 3D loading while considering the often-neglected **unloading feasibility**. The unloading simulation within `metrics_calculator.py` explicitly calculates relocations and sequence length, providing a quantitative measure of how easily items can be retrieved.

2.  **Enables Comparison:** By allowing the user to seamlessly switch between standalone PSO, ACO, and the hybrid algorithm, the tool provides the direct comparison needed to answer RQ1, RQ2, and RQ3. The displayed metrics allow for a direct performance assessment.

3.  **Provides Data for Hypothesis Testing:** The quantitative output from each simulation run (computation time, memory usage, volume utilization, etc.) is the raw data required for the statistical analyses described in the methodology (ANOVA, Tukey's HSD, Chi-Square). By running simulations across different vehicle capacities, a researcher can gather the necessary data to accept or reject the null hypotheses H₀₁, H₀₂, and H₀₃, thereby determining if the proposed hybrid algorithm offers a statistically significant improvement.

4.  **Demonstrates Superiority of the Hybrid Algorithm:** The `hybrid_pso_aco.py` implementation is designed to outperform the standalone versions by leveraging PSO's global search capabilities while using ACO's pheromone trails to guide particles toward historically successful regions of the search space. This prevents premature convergence on suboptimal solutions and results in packing configurations that are not only dense but also optimized for efficient unloading.