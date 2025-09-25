"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
Defines custom exceptions used across the simulation and algorithm modules
to handle specific flow control situations, like graceful cancellation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

class CancelledException(Exception):
    """
    A custom exception that is raised when a simulation task is cancelled
    by the user. This allows for a clean and immediate exit from deep loops
    within the algorithms.
    """
    pass