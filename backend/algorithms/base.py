# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/base.py

from deap import base, creator

# This central file defines the evolutionary computation components using DEAP,
# as specified in the Chapter 3 Methodology section.

# 1. Define Multi-Objective Fitness
# The problem aims to MAXIMIZE volume utilization and MINIMIZE relocation count
# and unloading sequence length. The weights reflect this:
# (1.0 for maximization, -1.0 for minimization).
# This definition directly addresses Research Questions 1 and 2.
try:
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0, -1.0))
except Exception:
    pass # Prevents errors on hot-reloading in debug mode.

# 2. Define the Particle Structure
# Each "Particle" represents a candidate solution (a permutation of items).
# It holds the solution itself (a list), its fitness, its movement speed
# (a sequence of swaps), and its personal best (pbest) position.
try:
    creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None)
except Exception:
    pass # Prevents errors on hot-reloading.