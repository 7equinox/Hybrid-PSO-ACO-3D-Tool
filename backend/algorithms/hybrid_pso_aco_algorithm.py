"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Proposed Hybrid PSO-ACO Algorithm

Purpose of this file:
Implements Figure 7 architecture. Embeds ACO Pheromone Matrix update
within the PSO velocity calculation to guide swarms out of local optima.

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


def runHybridPsoAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                                intNumParticles=10, intMaxGenerations=10, fltEvaporationRate=0.2):
    """
    Execute Hybrid PACO algorithm.
    """
    intNumItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations
    
    arrServiceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arrServiceTimes[arrServiceTimes == 0] = 1

    # Hybrid Init
    objToolbox = base.Toolbox()
    objToolbox.register("permutation", random.sample, range(intNumItems), intNumItems)
    objToolbox.register("particle", tools.initIterate, creator.Particle, objToolbox.permutation)
    objToolbox.register("population", tools.initRepeat, list, objToolbox.particle)
    
    objToolbox.register("evaluate", funcEvaluateSolution)
    arrSwarm = objToolbox.population(n=intNumParticles)
    
    arrPheromones = np.ones((intNumItems, intNumItems))
    objGbest = None

    objToolbox.register("update", _updateParticleHybrid, arrPheromones=arrPheromones,
                         arrServiceTimes=arrServiceTimes, fltPhi1=1.5, fltPhi2=1.5, fltPhi3=2.0, fltPhi4=1.5)

    try:
        for intGen in range(intMaxGenerations):
            dictProgressTracker['current'] = intGen + 1
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"Hybrid PSO-ACO Generation: {intGen + 1}/{intMaxGenerations}")

            # Standard PSO Eval
            for objParticle in arrSwarm:
                if not objParticle.fitness.valid:
                    objParticle.fitness.values = objToolbox.evaluate(objParticle)
                if not objParticle.pbest or objParticle.pbest.fitness < objParticle.fitness:
                    objParticle.pbest = creator.Particle(objParticle)
                    objParticle.pbest.fitness.values = objParticle.fitness.values
                if not objGbest or objGbest.fitness < objParticle.fitness:
                    objGbest = creator.Particle(objParticle)
                    objGbest.fitness.values = objParticle.fitness.values
            
            # Hybrid Step: Weighted Pheromone Update
            arrPheromones *= (1 - fltEvaporationRate)
            
            arrSortedSwarm = sorted(arrSwarm, key=lambda p: float(p.fitness.values[0]) + float(p.fitness.values[1]))
            intElites = max(1, int(0.2 * len(arrSwarm)))

            for objElite in arrSortedSwarm[:intElites]:
                fltCombFit = float(objElite.fitness.values[0]) + float(objElite.fitness.values[1])
                fltDeposit = 1.0 / (1.0 + fltCombFit)

                if fltDeposit > 0 and len(objElite) > 1:
                    for i in range(intNumItems - 1):
                        arrPheromones[objElite[i]][objElite[i+1]] += fltDeposit

            # Hybrid Velocity Update
            for objParticle in arrSwarm:
                 objToolbox.update(objParticle, objGbest)

    except CancelledException:
        print("Hybrid PSO-ACO algorithm was cancelled.")
        arrSol = objGbest if objGbest else []
        tplFit = objGbest.fitness.values if objGbest else (float('inf'), float('inf'))
        return arrSol, tplFit

    return objGbest, objGbest.fitness.values

# end of runHybridPsoAcoAlgorithm


def _updateParticleHybrid(objParticle, objGbest, arrPheromones, arrServiceTimes, fltPhi1, fltPhi2, fltPhi3, fltPhi4):
    """
    Apply Hybrid Swaps: Cognitive + Social + Pheromone-Guided + Heuristic.
    """
    intNumItems = len(objParticle)
    if intNumItems <= 1: return

    arrPbestSwaps = []
    if hasattr(objParticle, 'pbest') and objParticle.pbest:
        arrPbestDiff = [i for i in range(intNumItems) if i < len(objParticle.pbest) and objParticle[i] != objParticle.pbest[i]]
        if len(arrPbestDiff) >= 2:
            intSwaps = int(fltPhi1 * random.random() * len(arrPbestDiff) / 2)
            arrPbestSwaps.extend(tuple(random.sample(arrPbestDiff, 2)) for _ in range(intSwaps))

    arrGbestSwaps = []
    if objGbest:
        arrGbestDiff = [i for i in range(intNumItems) if i < len(objGbest) and objParticle[i] != objGbest[i]]
        if len(arrGbestDiff) >= 2:
            intSwaps = int(fltPhi2 * random.random() * len(arrGbestDiff) / 2)
            arrGbestSwaps.extend(tuple(random.sample(arrGbestDiff, 2)) for _ in range(intSwaps))

    # PHEROMONE-GUIDED
    arrPhSwaps = []
    intPhSwaps = int(fltPhi3 * random.random())
    for _ in range(intPhSwaps):
        intPos = random.randrange(intNumItems - 1)
        intCurrentItem = objParticle[intPos]
        
        arrProbs = arrPheromones[intCurrentItem].copy()
        
        for i in range(intPos + 1):
             if objParticle[i] < len(arrProbs): arrProbs[objParticle[i]] = 0

        if np.sum(arrProbs) > 0:
            intBestNext = np.argmax(arrProbs)
            if objParticle[intPos + 1] != intBestNext and intBestNext in objParticle:
                intOriginalPos = objParticle.index(intBestNext)
                arrPhSwaps.append(tuple(sorted((intPos + 1, intOriginalPos))))

    # Heuristic
    arrHeuristicSwaps = []
    intHeuristicSwaps = int(fltPhi4 * random.random())
    for _ in range(intHeuristicSwaps):
        if intNumItems < 2: continue
        intIdx1, intIdx2 = random.sample(range(intNumItems), 2)
        if arrServiceTimes[objParticle[intIdx1]] > arrServiceTimes[objParticle[intIdx2]]:
             arrHeuristicSwaps.append(tuple(sorted((intIdx1, intIdx2))))
            
    # Apply
    arrAllSwaps = list(set(arrPbestSwaps + arrGbestSwaps + arrPhSwaps + arrHeuristicSwaps))
    for i, j in arrAllSwaps:
        objParticle[i], objParticle[j] = objParticle[j], objParticle[i]

# end of _updateParticleHybrid