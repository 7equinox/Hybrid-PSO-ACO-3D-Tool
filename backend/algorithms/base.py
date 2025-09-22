# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/base.py

from deap import base, creator

# Define the fitness and particle classes once in this central location.
# These will be attached to the 'creator' object.
# The DEAP warnings on reload are normal in development and can be ignored.
creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0, -1.0))
creator.create("Particle", list, fitness=creator.FitnessMulti, speed=list, pbest=None, best=None)