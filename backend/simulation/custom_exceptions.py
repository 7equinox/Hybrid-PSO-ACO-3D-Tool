"""
System Name: Hybrid PSO-ACO 3D Loading Optimization Tool
Module Name: Simulation

Purpose of this file:
Defines custom exceptions used across the simulation and algorithm modules
to handle specific flow control situations. The primary purpose of having a
dedicated `CancelledException` is to enable a graceful and immediate exit
from the deep computational loops found in the metaheuristic algorithms when a
task is cancelled by the user via the web interface. This is a key component
of the application's asynchronous architecture, ensuring the research tool
remains responsive and usable during long-running experiments.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

class CancelledException(Exception):
    """
    A custom exception that is raised when a simulation or data-loading task
    is cancelled by the user.

    Purpose in Methodology:
    The metaheuristic algorithms in Chapter 3 operate within nested loops that
    can run for many thousands of iterations. Simply checking a boolean flag
    in every loop can be cumbersome and may not allow for immediate termination.

    By raising this exception when the cancellation flag is detected, the program
    can immediately unwind the call stack and jump out of the deepest parts of
    the algorithm's execution. This provides a clean, efficient, and immediate
    way to terminate long-running processes, which is essential for the
    usability of the interactive research instrument.
    """
    pass