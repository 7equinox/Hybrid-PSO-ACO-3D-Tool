"""
*System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
*Module Name: Standalone Ant Colony Optimization (ACO) Algorithm
*
*Purpose of this file:
*Implements standalone ACO logic per Chapter 3 Figure 7.
*Constructive search using pheromone trails and evaporation.
*
*Author/s:
*ALFARO, ABRAM S.
*BUNAO, JOHN GLAY C.
*DELA CRUZ, JUAN GABRIEL D.
*ERFE, JEFFERSON B.
*ESTONILO, JULIUS EVAN C.
"""

import random
import numpy as np
from backend.simulation.custom_exceptions import CancelledException


# Executes standard ACO with constructive ants and pheromone updates.
# manages the pheromone evaporation and global pheromone updates based on fitness.
def runAcoAlgorithm(arrItems, arrPackagesInfo, funcEvaluateSolution, dictCancellationFlag, dictProgressTracker,
                       intNumAnts=10, intMaxGenerations=10,
                       fltAlpha=1.0, fltBeta=2.0, fltEvaporationRate=0.5):
    
    intNumItems = len(arrItems)
    dictProgressTracker['total'] = intMaxGenerations
    
    # Heuristics Initialization
    # inverse of service time is used for heuristic desirability
    arrServiceTimes = np.array([p.get('service_time', 1) for p in arrPackagesInfo])
    arrServiceTimes[arrServiceTimes == 0] = 1e-6
    arrHeuristicInfo = 1.0 / arrServiceTimes

    arrPheromones = np.ones((intNumItems, intNumItems))

    arrBestSolution = []
    tplBestFitness = (float('inf'), float('inf'))

    # Main Evolutionary Loop
    try:
        for intGen in range(intMaxGenerations):
            dictProgressTracker['current'] = intGen + 1
            if dictCancellationFlag['is_cancelled']: raise CancelledException()
            print(f"ACO Generation: {intGen + 1}/{intMaxGenerations}")

            arrAntSolutions = []
            
            # Ant Solution Construction Phase
            for _ in range(intNumAnts):
                arrSol = _constructSolution(arrPheromones, arrHeuristicInfo, intNumItems, fltAlpha, fltBeta, dictCancellationFlag)
                if not arrSol: continue

                tplFit = funcEvaluateSolution(arrSol)
                arrAntSolutions.append((arrSol, tplFit))

                # Pareto Update Logic
                # Check if new solution dominates the best found so far
                if (tplFit[0] < tplBestFitness[0] and tplFit[1] < tplBestFitness[1]) or \
                   (tplFit[0] <= tplBestFitness[0] and tplFit[1] < tplBestFitness[1]) or \
                   (tplFit[0] < tplBestFitness[0] and tplFit[1] <= tplBestFitness[1]):
                    arrBestSolution = arrSol
                    tplBestFitness = tplFit

            # Pheromone Update Phase
            # Evaporation followed by depositing pheromones on trails of valid solutions
            arrPheromones *= (1 - fltEvaporationRate)

            for arrSol, tplFit in arrAntSolutions:
                fltCombinedFitness = float(tplFit[0]) + float(tplFit[1])
                fltDeposit = 1.0 / (1.0 + fltCombinedFitness)

                if fltDeposit > 0:
                    for i in range(intNumItems - 1):
                        arrPheromones[arrSol[i]][arrSol[i+1]] += fltDeposit

    except CancelledException:
        print("ACO algorithm was cancelled.")
        return arrBestSolution, tplBestFitness

    return arrBestSolution, tplBestFitness

# end of runAcoAlgorithm


# Step-by-step path construction by a single ant.
# Uses probability calculation based on pheromone levels and heuristic info.
def _constructSolution(arrPheromones, arrHeuristicInfo, intNumItems, fltAlpha, fltBeta, dictCancellationFlag):
    
    if dictCancellationFlag['is_cancelled']: raise CancelledException()

    arrSolution = []
    arrAvailable = list(range(intNumItems))

    if not arrAvailable: return []
    intCurrent = random.choice(arrAvailable)
    arrSolution.append(intCurrent)
    arrAvailable.remove(intCurrent)

    # Path Construction Loop
    while arrAvailable:
        arrProbs = []
        
        # Calculate transition probabilities
        for intNext in arrAvailable:
            fltPh = arrPheromones[intCurrent][intNext] ** fltAlpha
            fltHeu = arrHeuristicInfo[intNext] ** fltBeta
            arrProbs.append(fltPh * fltHeu)

        fltSum = sum(arrProbs)
        
        if fltSum == 0:
            intNext = random.choice(arrAvailable)
        else:
            arrProbs = [p / fltSum for p in arrProbs]
            intNext = random.choices(arrAvailable, weights=arrProbs, k=1)[0]

        arrSolution.append(intNext)
        arrAvailable.remove(intNext)
        intCurrent = intNext

    return arrSolution

# end of _constructSolution