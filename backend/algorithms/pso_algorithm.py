"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Standalone Particle Swarm Optimization (PSO) Algorithm

Purpose of this file:
Implements standalone PSO logic per Chapter 3 Figure 5.
Swarm optimization using pBest, gBest, and heuristic velocities.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

import random
import numpy as np
from deap import base, tools
from .base_algorithm import creator
from backend.simulation.custom_exceptions import CancelledException


def runPsoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                       intNumParticles=10, intMaxGenerations=10):
    """
    Execute standard PSO.
    """
    intNumItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations
    
    # Heuristic: Service times
    arrServiceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arrServiceTimes[arrServiceTimes == 0] = 1

    # Initialization
    objToolbox = base.Toolbox()
    objToolbox.register("permutation", random.sample, range(intNumItems), intNumItems)
    objToolbox.register("particle", tools.initIterate, creator.Particle, objToolbox.permutation)
    objToolbox.register("population", tools.initRepeat, list, objToolbox.particle)

    objToolbox.register("evaluate", funcEvaluateSolution)
    objToolbox.register("update", _updateParticle, fltPhi1=2.0, fltPhi2=2.0, fltPhi3=1.5,
                         arrServiceTimes=arrServiceTimes)

    arrSwarm = objToolbox.population(n=intNumParticles)
    objGbest = None

    # Loop
    try:
        for intGen in range(intMaxGenerations):
            dictProgressTracker['current'] = intGen + 1
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"PSO Generation: {intGen + 1}/{intMaxGenerations}")

            for objParticle in arrSwarm:
                if not objParticle.fitness.valid:
                    objParticle.fitness.values = funcEvaluateSolution(objParticle)

                if not objParticle.pbest or objParticle.pbest.fitness < objParticle.fitness:
                    objParticle.pbest = creator.Particle(objParticle)
                    objParticle.pbest.fitness.values = objParticle.fitness.values

                if not objGbest or objGbest.fitness < objParticle.fitness:
                    objGbest = creator.Particle(objParticle)
                    objGbest.fitness.values = objParticle.fitness.values

            # Velocity Update
            for objParticle in arrSwarm:
                objToolbox.update(objParticle, objGbest)

    except CancelledException:
        print("PSO algorithm was cancelled.")
        arrSolution = objGbest if objGbest else []
        tplFitness = objGbest.fitness.values if objGbest else (float('inf'), float('inf'))
        return arrSolution, tplFitness

    return objGbest, objGbest.fitness.values

# end of runPsoAlgorithm


def _updateParticle(objParticle, objGbest, fltPhi1, fltPhi2, fltPhi3, arrServiceTimes):
    """
    Moves particle by applying swaps (velocity) derived from cognitive, social, and heuristic inputs.
    """
    intNumItems = len(objParticle)
    arrPbestSwaps = []

    # Cognitive
    if hasattr(objParticle, 'pbest') and objParticle.pbest:
        arrPbestDiff = [i for i in range(intNumItems) if i < len(objParticle.pbest) and objParticle[i] != objParticle.pbest[i]]
        if len(arrPbestDiff) >= 2:
            intSwaps = int(fltPhi1 * random.random() * len(arrPbestDiff) / 2)
            arrPbestSwaps.extend(tuple(random.sample(arrPbestDiff, 2)) for _ in range(intSwaps))

    # Social
    arrGbestSwaps = []
    if objGbest:
        arrGbestDiff = [i for i in range(intNumItems) if i < len(objGbest) and objParticle[i] != objGbest[i]]
        if len(arrGbestDiff) >= 2:
            intSwaps = int(fltPhi2 * random.random() * len(arrGbestDiff) / 2)
            arrGbestSwaps.extend(tuple(random.sample(arrGbestDiff, 2)) for _ in range(intSwaps))

    # Heuristic
    arrHeuristicSwaps = []
    intHeuristicSwaps = int(fltPhi3 * random.random())
    
    for _ in range(intHeuristicSwaps):
        if intNumItems < 2: continue
        intIdx1, intIdx2 = random.sample(range(intNumItems), 2)
        if arrServiceTimes[objParticle[intIdx1]] > arrServiceTimes[objParticle[intIdx2]]:
            arrHeuristicSwaps.append(tuple(sorted((intIdx1, intIdx2))))

    # Apply Swaps
    arrAllSwaps = list(set(arrPbestSwaps + arrGbestSwaps + arrHeuristicSwaps))
    for i, j in arrAllSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]

# end of _updateParticle