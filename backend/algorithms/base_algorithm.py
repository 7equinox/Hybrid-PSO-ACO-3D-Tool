"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Base Algorithm Configuration

Purpose of this file:
Establishes DEAP foundations for evolutionary algorithms.
Defines 'FitnessMulti' for multi-objective optimization (Vol vs. Relocations)
and 'Particle' structure for candidates.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

from deap import base, creator


# --- MULTI-OBJECTIVE FITNESS DEFINITION ---
# Weights: (-1.0, -1.0) means minimize both objectives.
try:
    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))
except Exception:
    pass

# --- INDIVIDUAL (PARTICLE) DEFINITION ---
# Defines properties for evolutionary agents.
try:
    creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None)
except Exception:
    pass