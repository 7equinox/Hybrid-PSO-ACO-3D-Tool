"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
This file establishes the fundamental building blocks for all metaheuristic
algorithms (PSO, ACO, and Hybrid) using the DEAP library, as specified in
the 'Research Instrument' section of the methodology. It serves two critical
functions: defining the multi-objective fitness criteria that directly
reflect our research questions, and defining the structure of an individual
solution (a "Particle"). This ensures that all algorithms operate on a
consistent, comparable, and methodologically sound foundation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
from deap import base, creator

# --- 1. DEFINE MULTI-OBJECTIVE FITNESS ---
# This `creator` function is the formal implementation of the evaluation
# framework that directly addresses the research's Statement of the Problem.
# It defines a multi-objective fitness function that simultaneously evaluates
# a solution against competing goals: balancing traditional packing density with
# the novel, critical measures of operational unloading efficiency.

# The `weights` tuple specifies the optimization direction for each objective:
#   - Volume Utilization: To be MAXIMIZED (weight: 1.0)
#   - Relocation Count: To be MINIMIZED (weight: -1.0)
#   - Unloading Sequence Length: To be MINIMIZED (weight: -1.0)

# This setup is what allows the algorithms to learn and distinguish between a
# densely packed but operationally terrible solution and a slightly less dense
# but highly efficient and feasible solution.
try:
    # We define a new fitness type called "FitnessMulti".
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0, -1.0))
except Exception:
    # This try-except block prevents errors when the code is hot-reloaded during
    # development, as DEAP does not allow re-creating an existing type.
    pass

# --- 2. DEFINE THE INDIVIDUAL SOLUTION STRUCTURE ---
# This `creator` function defines the data structure for a single candidate solution,
# which we name "Particle" for consistency with PSO terminology, though it applies
# to all algorithms. Each Particle represents a specific permutation (an ordered
# list) of items to be packed into the vehicle.

# The structure is defined as a Python list (`list`) and is augmented with
# several attributes essential for the evolutionary process:
#   - fitness: An instance of our newly defined "FitnessMulti" to store its
#     multi-objective evaluation scores.
#   - speed: A list used by the PSO algorithm to store its velocity vector,
#     guiding its movement through the search space.
#   - pbest: Short for "personal best," this attribute is used by PSO to store a
#     particle's best-known position (solution) found so far, acting as a memory component.
try:
    # We define a new individual type called "Particle".
    creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None)
except Exception:
    pass