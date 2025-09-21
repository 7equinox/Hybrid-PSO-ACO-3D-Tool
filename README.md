# Hybrid PSO-ACO 3D Loading Optimization Tool

This project is a full-stack web application designed to implement and evaluate a hybrid Particle Swarm Optimization and Ant Colony Optimization (PSO-ACO) algorithm for solving dynamic 3D loading and unloading problems for delivery vehicles. This tool directly supports the research outlined in the thesis: "OPTIMIZING DYNAMIC 3D LOADING AND UNLOADING FOR DELIVERY VEHICLES USING HYBRID PARTICLE SWARM AND ANT COLONY ALGORITHM".

## Alignment with Research

This implementation directly addresses the core research objectives by:

1.  **Implementing the System Architectures:** The backend provides separate, modular implementations for standalone PSO, standalone ACO, and the proposed hybrid PSO-ACO algorithm, matching the flowcharts and descriptions in Chapter 3.
2.  **Solving the Statement of the Problem:** The tool is designed to answer the key research questions by running simulations and calculating the specific performance metrics defined in the problem statement (volume utilization, relocation count, feasibility, sequence length, computation time, and memory usage).
3.  **Utilizing the Specified Dataset:** The application is built to consume the `eval_package_data.json` and `eval_route_data.json` files from the 2021 Amazon Last Mile Routing Research Challenge Dataset.
4.  **Providing a User Interface for Experimentation:** The web-based frontend allows for easy selection of algorithms and vehicle capacities, enabling the controlled experiments described in the methodology.

## Features

-   Interactive web interface to configure and run simulations.
-   Backend server built with Flask (Python).
-   Modular implementation of PSO, ACO, and Hybrid PSO-ACO algorithms.
-   Dynamic calculation and display of all key performance metrics outlined in the research.
-   Data loading and preprocessing of the Amazon dataset.
-   Scalability analysis through automated measurement of execution time and memory usage.

## Technical Stack

-   **Backend:** Python 3, Flask, NumPy, Pandas, memory-profiler
-   **Frontend:** HTML5, CSS3, JavaScript (no external frameworks)
-   **Dataset:** JSON

## Prerequisites

Before you begin, ensure you have the following installed on your system:

-   **Python 3.8 or newer:** [Download Python](https://www.python.org/downloads/)
-   **pip** (Python's package installer, usually comes with Python)
-   A modern web browser (e.g., Chrome, Firefox, Edge)

## Installation and Setup

Follow these steps to get the application running on your local machine.

### 1. Clone the Repository

Clone this project to your local machine using Git, or download the ZIP file and extract it.

```bash
git clone <your-repository-url>
cd HYBRID-PSO-ACO-3D-TOOL
```

### 2. Set Up a Virtual Environment (Recommended)

Using a virtual environment is best practice to keep project dependencies isolated.

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows (Git Bash or CMD):
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Ensure Dataset is in Place

Verify that the Amazon dataset files are correctly placed in the following directory:
`HYBRID-PSO-ACO-3D-TOOL/backend/almrrc2021/almrrc2021-data-evaluation/model_apply_inputs/`

The two required files are:
- `eval_package_data.json`
- `eval_route_data.json`

## How to Run the Tool

Once the setup is complete, you can start the application with a single command from the project's root directory (`HYBRID-PSO-ACO-3D-TOOL/`).

```bash
# This command runs the main Flask application file.
python backend/app.py
```

After running the command, you will see output in your terminal similar to this:
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

**Open your web browser and navigate to the URL shown: [http://127.0.0.1:5000](http://127.0.0.1:5000)**

## Using the Application

1.  **Modify Simulation:** Click the "Modify Simulation" button to open the settings modal.
2.  **Select Algorithm:** Choose one of the three algorithms to test. The default is Particle Swarm Optimization.
3.  **Select Vehicle Capacity:** From the dropdown menu, select one of the available vehicle volume capacities from the dataset. The application will automatically load the corresponding item data on the left panel.
4.  **Run Simulation:** Click the "Simulate" button. The application will send the configuration to the backend, run the optimization, and display the results and calculated metrics in the right panel. Please be patient, as the simulations can take some time to complete.
5.  **Clear Simulation:** To reset the interface, click the "Clear Simulation" button in the modal.