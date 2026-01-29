"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Simulation Support

Purpose of this file:
Defines CancelledException to control flow interruptions during async threads.
Enables instant loop exit on user cancellation.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

class CancelledException(Exception):
    """
    Raised when the shared cancellation flag detects a user interrupt signal.
    """
    pass

# end of CancelledException