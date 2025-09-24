"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Algorithms

Purpose of this file:
This file establishes the fundamental building blocks for the evolutionary
algorithms using the DEAP library, as specified in the methodology. It defines
the multi-objective fitness criteria and the structure of an individual
solution ("Particle") to ensure all algorithms operate on a consistent foundation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""
from deap import base, creator

# --- 1. DEFINE MULTI-OBJECTIVE FITNESS ---
# This creator function sets up the fitness evaluation framework. Our goal is to
# solve a multi-objective problem:
#   - MAXIMIZE Volume Utilization (weight: 1.0)
#   - MINIMIZE Relocation Count (weight: -1.0)
#   - MINIMIZE Unloading Sequence Length (weight: -1.0)
# This definition is central to addressing Research Questions 1 and 2.
try:
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0, -1.0))
except Exception:
    pass # Prevents errors on hot-reloading during development.

# --- 2. DEFINE THE PARTICLE/SOLUTION STRUCTURE ---
# Each "Particle" represents a single candidate solution, which is a specific
# permutation (ordering) of items to be packed. The structure holds:
#   - The solution itself (a list of item indices).
#   - Its associated multi-objective fitness.
#   - Its "speed" or velocity (used in PSO to guide its movement).
#   - Its personal best known position (`pbest`), a memory component for PSO.
try:
    creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None)
except Exception:
    pass # Prevents errors on hot-reloading.