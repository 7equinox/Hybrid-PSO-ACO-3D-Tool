"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Simulation Support

Purpose of a this file:
This file defines a custom exception class, `CancelledException`, which is a specialized
tool for handling a specific flow-control situation in our application. The primary purpose
is to enable a clean, immediate, and graceful exit from the deeply nested computational
loops found within the metaheuristic algorithms when a task is cancelled by the user from
the web interface. This is a key technical component of the application's asynchronous
architecture, ensuring the research tool remains responsive and robust during long-running
experiments.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

class CancelledException(Exception):
    """
    A custom exception that is "raised" (or triggered) whenever an algorithm or
    data-loading process detects that its cancellation flag has been set to True.

    Purpose in the Research Methodology:
    The metaheuristic algorithms defined in Chapter 3 (PSO, ACO, Hybrid) operate
    within multiple layers of loops (e.g., loops for generations, loops for particles,
    loops for constructing solutions). Simply checking a boolean flag in the outermost
    loop might not terminate the process immediately if it's busy in a deep inner loop.

    By "raising" this special exception when the cancellation flag is detected, the program
    can immediately interrupt its current task, unwind the entire call stack (jump out of
    all the nested loops at once), and be caught by a dedicated "except" block at the highest
    level. This provides a clean, efficient, and immediate way to terminate long-running
    processes, which is essential for the usability of this interactive research instrument.
    """
    pass
