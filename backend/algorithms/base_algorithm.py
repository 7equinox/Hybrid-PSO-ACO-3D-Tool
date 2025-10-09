"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Base Algorithm Configuration

Purpose of this file:
This file establishes the foundational building blocks for all metaheuristic
algorithms (PSO, ACO, and Hybrid) used in this study. It leverages the DEAP
library, as specified in the 'Research Instrument' section of the methodology,
to accomplish two critical tasks:
1.  **Define the Multi-Objective Fitness:** It formally defines the criteria by
    which every potential solution will be judged. This definition is a direct
    translation of our research goals, balancing the competing objectives of
    packing density against operational unloading efficiency.
2.  **Define the Individual Structure:** It specifies the data structure for a
    single candidate solution (e.g., a "Particle" in PSO).
By defining these core components in one central location, we ensure that all
three algorithms operate on a consistent, comparable, and methodologically sound foundation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
# --- Import necessary libraries ---
from deap import base, creator # Core components from the DEAP library for creating custom evolutionary algorithms.


# --- 1. DEFINE THE MULTI-OBJECTIVE FITNESS CRITERIA ---
# This `creator` function from DEAP is where we formally implement the evaluation
# framework that directly addresses the research's Statement of the Problem. We are
# creating a custom "fitness" type that can judge a solution not on a single score,
# but on multiple, often conflicting, objectives.

# The `weights` tuple is the key. It tells the algorithm whether to MAXIMIZE or MINIMIZE each objective score:
#   - Objective 1 (Weight: 1.0): Volume Utilization. We want this to be as high as possible (MAXIMIZE).
#   - Objective 2 (Weight: -1.0): Relocation Count. We want this to be as low as possible (MINIMIZE).
#   - Objective 3 (Weight: -1.0): Unloading Sequence Length. We also want this to be as low as possible (MINIMIZE).

# This multi-objective setup is what enables our algorithms to learn the subtle trade-offs
# and distinguish between a densely packed but operationally disastrous solution and a
# slightly less dense but highly efficient and feasible one. This is central to our research hypothesis.
try:
    # We define a new fitness type called "FitnessMulti".
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0, -1.0))
except Exception:
    # This try-except block is a technical requirement. It prevents an error if the code
    # is reloaded during development, as DEAP does not allow re-creating an existing type.
    pass


# --- 2. DEFINE THE STRUCTURE OF AN INDIVIDUAL SOLUTION ---
# This `creator` function defines the data structure for a single candidate solution. In the
# context of this research, a "solution" is a specific permutation (an ordered list) of
# items to be packed into the vehicle. We name it "Particle" to align with PSO terminology,
# but this same structure is used by the ants in ACO and the individuals in the hybrid model.

# The base structure is a Python `list`. We then augment this list with several special
# attributes that are essential for the algorithms to function:
#   - `fitness`: Holds an instance of our `FitnessMulti` object to store its evaluation scores.
#   - `speed`: Used by PSO to store its velocity, which guides its movement in the search space.
#   - `pbest`: Stands for "personal best." Used by PSO as a memory component to store the
#              best solution this particular particle has ever found.
try:
    # We define a new individual type called "Particle".
    creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None)
except Exception:
    # Same as above, this handles potential errors on code reload.
    pass
