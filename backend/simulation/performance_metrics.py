"""
System Name: ASPECT (Algorithm System for Packing Efficiency Comparison and Testing)
Module Name: Performance Metrics Calculation

Purpose of this file:
Implements Chapter 3 Methodology for Volume Utilization and Unloading Efficiency.
Calculates Equations 1, 2, and 3, and detects Recursive On-Top logic for blockers.

Author/s:
ALFARO, ABRAM S.
BUNAO, JOHN GLAY C.
DELA CRUZ, JUAN GABRIEL D.
ERFE, JEFFERSON B.
ESTONILO, JULIUS EVAN C.
"""

import numpy as np
import random
from itertools import permutations
import hashlib
import time

def calculateAllMetrics(arrPackedItems, fltBinVolume, arrAllPackagesInfo, strAlgorithmName, arrInitialFreeAreas=None):
    """
    Main entry point for metric calculation.
    Computes volume utilization (adjusted) and generates unloading events.
    """
    # Equation 1: Base Volume Utilization
    fltTotalPackedVolume = sum(float(objItem.get_volume()) for objItem in arrPackedItems)
    fltBinVolumeVal = float(fltBinVolume)
    
    fltVuBase = (fltTotalPackedVolume / fltBinVolumeVal * 100) if fltBinVolumeVal > 0 else 0.0

    # Equation 2 & 3: Fragmented Space Logic
    fltVuAdjusted = fltVuBase
    fltVuFragmentedVol = 0.0
    
    if arrInitialFreeAreas:
        fltVuAdjusted, fltVuFragmentedVol = _calculateFragmentedVolumeAndUtilization(
            arrInitialFreeAreas, 
            arrAllPackagesInfo, 
            fltVuBase, 
            fltBinVolumeVal
        )

    dictPackagesInfoMap = {p['id']: p for p in arrAllPackagesInfo}
    
    arrBinDims = [0, 0, 0]
    if arrPackedItems and hasattr(arrPackedItems[0], 'bin') and arrPackedItems[0].bin:
        objParentBin = arrPackedItems[0].bin
        arrBinDims = [float(objParentBin.width), float(objParentBin.height), float(objParentBin.depth)]

    dictUnloadingResult = _generateUnloadingSequence(arrPackedItems, dictPackagesInfoMap, strAlgorithmName, arrBinDims, arrInitialFreeAreas)
    
    return {
        'volume_utilization': round(fltVuAdjusted, 2),
        'base_volume_utilization': round(fltVuBase, 2),
        'fragmented_volume': round(fltVuFragmentedVol, 2),
        'relocation_count': dictUnloadingResult['relocation_count'],
        'unloading_sequence': dictUnloadingResult['event_log']
    }

# end of calculateAllMetrics


def _getUniqueOrientations(arrDims):
    """
    Get all unique 3D rotations/permutations of a dimension set.
    """
    objSeen = set()
    arrOrientations = []
    
    for objPerm in permutations(arrDims):
        if objPerm not in objSeen:
            objSeen.add(objPerm)
            arrOrientations.append(list(map(float, objPerm)))
            
    return arrOrientations

# end of _getUniqueOrientations


def _canItemFitInSpace(arrSpaceDims, arrItemDims):
    """
    Checks if an item can fit into a specific space volume in any standard rotation.
    Used for classification of Fragmented vs Consolidated space.
    """
    fltSpaceW, fltSpaceH, fltSpaceD = sorted([float(x) for x in arrSpaceDims])
    
    arrOrientations = _getUniqueOrientations(arrItemDims)
    
    for arrOri in arrOrientations:
        fltItemW, fltItemH, fltItemD = sorted(arrOri)
        # Check pure volume fitting strictly
        if fltItemW <= fltSpaceW and fltItemH <= fltSpaceH and fltItemD <= fltSpaceD:
            return True
            
    return False

# end of _canItemFitInSpace


def _calculateFragmentedVolumeAndUtilization(arrFreeAreas, arrAllPackages, fltVuBase, fltTotalBinVol):
    """
    Implements Equations 2 and 3: Adjusted Utilization.
    Categorizes free space into Usable or Fragmented.
    """
    # Cache unique item dimensions
    arrUniqueItemDims = []
    objSeenHashes = set()
    
    for dictPkg in arrAllPackages:
        tplDims = tuple(sorted([float(dictPkg['width']), float(dictPkg['height']), float(dictPkg['depth'])]))
        if tplDims not in objSeenHashes:
            arrUniqueItemDims.append(tplDims)
            objSeenHashes.add(tplDims)
            
    fltTotalFragmentedVolume = 0.0
    
    for dictArea in arrFreeAreas:
        arrAreaDims = dictArea['dims']
        fltAreaVol = dictArea['volume']
        
        blnIsFragmented = True
        
        # Check if ANY package fits in this area
        for arrItemDim in arrUniqueItemDims:
            if _canItemFitInSpace(arrAreaDims, arrItemDim):
                blnIsFragmented = False
                break
        
        if blnIsFragmented:
            fltTotalFragmentedVolume += fltAreaVol
            
    # Eq 2: Adjusted VU
    fltFragmentedPercentage = (fltTotalFragmentedVolume / fltTotalBinVol * 100) if fltTotalBinVol > 0 else 0
    fltVuAdjusted = fltVuBase + fltFragmentedPercentage
    
    return min(fltVuAdjusted, 100.0), fltTotalFragmentedVolume

# end of _calculateFragmentedVolumeAndUtilization


def _generateUniqueSeed(strAlgorithmName):
    """
    Generates a deterministic yet unique seed based on time and name.
    """
    strTimestamp = str(time.time() * 1000).encode()
    strAlgoHash = hashlib.md5(strAlgorithmName.encode()).hexdigest()
    strCombined = hashlib.sha256(strTimestamp + strAlgoHash.encode()).hexdigest()
    return int(strCombined[:12], 16)

# end of _generateUniqueSeed


def _checkCollision(arrPos1, arrDims1, arrPos2, arrDims2):
    """
    STRICT 3D Axis-Aligned Bounding Box (AABB) collision test.
    """
    if arrPos1[0] + arrDims1[0] <= arrPos2[0] or arrPos2[0] + arrDims2[0] <= arrPos1[0]:
        return False
    if arrPos1[1] + arrDims1[1] <= arrPos2[1] or arrPos2[1] + arrDims2[1] <= arrPos1[1]:
        return False
    if arrPos1[2] + arrDims1[2] <= arrPos2[2] or arrPos2[2] + arrDims2[2] <= arrPos1[2]:
        return False
    return True

# end of _checkCollision


def _inBounds(arrPos, arrDims, arrBinDims):
    """
    Validates if an object is fully contained within the bin boundaries.
    """
    return (arrPos[0] >= 0 and arrPos[1] >= 0 and arrPos[2] >= 0 and
            arrPos[0] + arrDims[0] <= arrBinDims[0] and
            arrPos[1] + arrDims[1] <= arrBinDims[1] and
            arrPos[2] + arrDims[2] <= arrBinDims[2])

# end of _inBounds


def _calculateXzOverlapArea(arrPos1, arrDims1, arrPos2, arrDims2):
    """
    Calculates the contact surface area in the horizontal X-Z plane.
    Used for gravity support and top-down blockage detection.
    """
    fltXOverlapStart = max(arrPos1[0], arrPos2[0])
    fltXOverlapEnd = min(arrPos1[0] + arrDims1[0], arrPos2[0] + arrDims2[0])
    fltXOverlapLength = max(0, fltXOverlapEnd - fltXOverlapStart)
    
    fltZOverlapStart = max(arrPos1[2], arrPos2[2])
    fltZOverlapEnd = min(arrPos1[2] + arrDims1[2], arrPos2[2] + arrDims2[2])
    fltZOverlapLength = max(0, fltZOverlapEnd - fltZOverlapStart)
    
    return fltXOverlapLength * fltZOverlapLength

# end of _calculateXzOverlapArea


def _hasDirectContact(arrBlockerPos, arrBlockerDims, arrTargetPos, arrTargetDims):
    """
    Checks if one item physically touches another from above (Y-axis).
    """
    fltBlockerBottomY = arrBlockerPos[1]
    fltTargetTopY = arrTargetPos[1] + arrTargetDims[1]
    
    fltYDistance = abs(fltBlockerBottomY - fltTargetTopY)
    
    if fltYDistance > 1.0:
        return False
    
    fltOverlapArea = _calculateXzOverlapArea(arrBlockerPos, arrBlockerDims, arrTargetPos, arrTargetDims)
    return fltOverlapArea > 0

# end of _hasDirectContact


def _hasClearExtractionPath(arrItemPos, arrItemDims, dictAllItems):
    """
    Verifies if an item can be pulled out (e.g., to the door) without collision.
    """
    fltItemY = arrItemPos[1]
    fltItemZ = arrItemPos[2]
    
    fltTestX = -100  # Virtual extraction point
    arrTestPos = [float(fltTestX), float(fltItemY), float(fltItemZ)]
    
    blnPathClear = True
    for dictOther in dictAllItems.values():
        if dictOther['pos'][0] >= arrItemPos[0]:
            continue
        
        if _checkCollision(arrTestPos, arrItemDims, dictOther['pos'], dictOther['dims']):
            blnPathClear = False
            break
    
    return blnPathClear

# end of _hasClearExtractionPath


def _isTrulyBlocking(strItemId, strTargetId, dictAllItems):
    """
    Sophisticated blocker logic: overlapping in X/Z, higher in Y, and contacting.
    """
    if strItemId == strTargetId or strItemId not in dictAllItems or strTargetId not in dictAllItems:
        return False
    
    dictItem = dictAllItems[strItemId]
    dictTarget = dictAllItems[strTargetId]
    
    arrItemPos, arrItemDims = dictItem['pos'], dictItem['dims']
    arrTargetPos, arrTargetDims = dictTarget['pos'], dictTarget['dims']
    
    if arrItemPos[1] < arrTargetPos[1] - 1e-4:
        return False
    
    # Fast overlap check first
    if not ((max(arrItemPos[0], arrTargetPos[0]) < min(arrItemPos[0] + arrItemDims[0], arrTargetPos[0] + arrTargetDims[0])) and 
            (max(arrItemPos[2], arrTargetPos[2]) < min(arrItemPos[2] + arrItemDims[2], arrTargetPos[2] + arrTargetDims[2]))):
        return False
    
    fltTargetArea = arrTargetDims[0] * arrTargetDims[2]
    fltOverlapArea = _calculateXzOverlapArea(arrItemPos, arrItemDims, arrTargetPos, arrTargetDims)
    fltOverlapPercentage = (fltOverlapArea / fltTargetArea) * 100 if fltTargetArea > 0 else 0
    
    if fltOverlapPercentage < 30:
        return False
    
    blnHasContact = _hasDirectContact(arrItemPos, arrItemDims, arrTargetPos, arrTargetDims)
    if not blnHasContact:
        return False
    
    if not _hasClearExtractionPath(arrItemPos, arrItemDims, dictAllItems):
        return False
    
    return True

# end of _isTrulyBlocking


def _hasGravitySupport(arrPos, arrDims, dictItemsInBin):
    """
    Checks if item has >= 80% support area from below.
    """
    fltItemY = arrPos[1]
    if abs(fltItemY) < 1e-4:
        return True, 0.0
    
    arrSupportingItems = []
    fltMaxSupportY = 0.0
    
    for dictOther in dictItemsInBin.values():
        if dictOther['pos'][1] + dictOther['dims'][1] > fltItemY + 1e-4:
            continue
        # Check general overlap before calculating area
        if (arrPos[0] + arrDims[0] > dictOther['pos'][0] and dictOther['pos'][0] + dictOther['dims'][0] > arrPos[0]) and \
           (arrPos[2] + arrDims[2] > dictOther['pos'][2] and dictOther['pos'][2] + dictOther['dims'][2] > arrPos[2]):
            arrSupportingItems.append(dictOther)
            fltMaxSupportY = max(fltMaxSupportY, dictOther['pos'][1] + dictOther['dims'][1])
    
    if not arrSupportingItems:
        return False, 0.0
    
    fltTotalSupportArea = 0.0
    for dictSupport in arrSupportingItems:
        fltTotalSupportArea += _calculateXzOverlapArea(arrPos, arrDims, dictSupport['pos'], dictSupport['dims'])
    
    fltItemBaseArea = arrDims[0] * arrDims[2]
    fltSupportPct = (fltTotalSupportArea / fltItemBaseArea) * 100 if fltItemBaseArea > 0 else 0
    
    if fltSupportPct < 80:
        return False, fltMaxSupportY
    
    return True, fltMaxSupportY

# end of _hasGravitySupport


def _findBestPositionExhaustive(arrItemDims, dictItemsInBin, arrBinDims, arrOriginalPos):
    """
    Searches grid for a valid spot (collision-free + support) to place a returned item.
    """
    arrBestPos = None
    arrBestDims = None
    fltBestScore = float('-inf')
    
    # 1. Try Original position first
    arrCandidatePos = list(map(float, arrOriginalPos))
    
    if _inBounds(arrCandidatePos, arrItemDims, arrBinDims):
        blnHasCollision = any(
            _checkCollision(arrCandidatePos, arrItemDims, o['pos'], o['dims']) 
            for o in dictItemsInBin.values()
        )
        if not blnHasCollision:
            blnHasSupport, _ = _hasGravitySupport(arrCandidatePos, arrItemDims, dictItemsInBin)
            if blnHasSupport:
                return arrCandidatePos, arrItemDims
    
    # 2. Search alternative positions with rotations
    for arrRotatedDims in _getUniqueOrientations(arrItemDims):
        arrRotatedDims = list(map(float, arrRotatedDims))
        
        for intX in range(0, int(arrBinDims[0] - arrRotatedDims[0]) + 1):
            for intZ in range(0, int(arrBinDims[2] - arrRotatedDims[2]) + 1):
                for intY in range(0, int(arrBinDims[1] - arrRotatedDims[1]) + 1):
                    
                    arrTestPos = [float(intX), float(intY), float(intZ)]
                    
                    if not _inBounds(arrTestPos, arrRotatedDims, arrBinDims): continue
                    
                    if any(_checkCollision(arrTestPos, arrRotatedDims, o['pos'], o['dims']) for o in dictItemsInBin.values()):
                        continue
                    
                    blnSup, _ = _hasGravitySupport(arrTestPos, arrRotatedDims, dictItemsInBin)
                    if not blnSup: continue
                    
                    fltDist = abs(intX - arrOriginalPos[0]) + abs(intZ - arrOriginalPos[2])
                    fltScore = -intY * 10000 - fltDist
                    
                    if fltScore > fltBestScore:
                        fltBestScore = fltScore
                        arrBestPos = arrTestPos
                        arrBestDims = arrRotatedDims
    
    if arrBestPos is not None:
        return arrBestPos, arrBestDims
    
    # Fallback to floor if no valid spot found
    return [float(arrOriginalPos[0]), 0.0, float(arrOriginalPos[2])], arrItemDims

# end of _findBestPositionExhaustive


def _getItemsOnTopRecursive(strItemId, dictAllItems, objVisited=None):
    """
    Recursively finds chain of items stacked on top of the given item.
    """
    if objVisited is None:
        objVisited = set()
    
    if strItemId in objVisited: return []
    objVisited.add(strItemId)
    
    if strItemId not in dictAllItems: return []
    
    dictItem = dictAllItems[strItemId]
    arrItemPos = dictItem['pos']
    arrItemDims = dictItem['dims']
    fltItemTopY = arrItemPos[1] + arrItemDims[1]
    
    arrDirectOnTop = []
    
    # Find items immediately above
    for strOtherId, dictOther in dictAllItems.items():
        if strOtherId == strItemId or strOtherId in objVisited: continue
        
        if abs(dictOther['pos'][1] - fltItemTopY) <= 1.0:
            if _calculateXzOverlapArea(arrItemPos, arrItemDims, dictOther['pos'], dictOther['dims']) > 0:
                arrDirectOnTop.append(strOtherId)
    
    # Recurse
    arrItemsOnTopChain = []
    for strOnTopId in arrDirectOnTop:
        arrItemsOnTopChain.append(strOnTopId)
        arrItemsOnTopChain.extend(_getItemsOnTopRecursive(strOnTopId, dictAllItems, objVisited))
    
    return arrItemsOnTopChain

# end of _getItemsOnTopRecursive


def _getSmartBlockerStack(strTargetId, dictAllItems):
    """
    Identifies all blockers, including the recursive cascade of items on top of blockers.
    """
    if strTargetId not in dictAllItems: return []
    
    fltTargetTopY = dictAllItems[strTargetId]['pos'][1] + dictAllItems[strTargetId]['dims'][1]
    arrBlockingItems = []
    
    for strItemId in dictAllItems.keys():
        if strItemId == strTargetId: continue
        
        if _isTrulyBlocking(strItemId, strTargetId, dictAllItems):
            arrBlockingItems.append(strItemId)
            
    # Solve dependencies for each blocker
    arrToRemove = []
    objVisitedGlobal = set()
    
    for strBlockerId in arrBlockingItems:
        if strBlockerId in objVisitedGlobal: continue
        
        arrCascade = _getItemsOnTopRecursive(strBlockerId, dictAllItems)
        
        # Add items above blocker first
        for strCasId in arrCascade:
            if strCasId not in arrToRemove and strCasId not in objVisitedGlobal:
                arrToRemove.append(strCasId)
                objVisitedGlobal.add(strCasId)
                
        if strBlockerId not in arrToRemove:
            arrToRemove.append(strBlockerId)
            objVisitedGlobal.add(strBlockerId)
            
    # Sort to remove top-most items first
    def _distFromTarget(sid):
        return dictAllItems[sid]['pos'][1] - fltTargetTopY

    arrToRemove.sort(key=_distFromTarget)
    return arrToRemove

# end of _getSmartBlockerStack


def _generateUnloadingSequence(arrPackedItems, dictPackagesInfoMap, strAlgorithmName, arrBinDims, arrInitialFreeAreas=None):
    """
    Simulates the unloading process to count relocations.
    """
    if not arrPackedItems:
        return {'event_log': [], 'relocation_count': 0}
    
    intSeed = _generateUniqueSeed(strAlgorithmName)
    random.seed(intSeed)
    
    # State tracking dictionary
    dictItemsInBin = {}
    for objItem in arrPackedItems:
        dictItemsInBin[objItem.name] = {
            'id': objItem.name,
            'pos': [float(p) for p in objItem.position],
            'dims': [float(d) for d in objItem.get_dimension()],
            'original_pos': [float(p) for p in objItem.position],
            'stop_id': dictPackagesInfoMap.get(objItem.name, {}).get('stop_id')
        }
    
    arrEventLog = []
    intRelocations = 0
    
    # Simulate Driver's optimized queue (based on heuristics and topology)
    arrPerfectOrder = sorted(dictItemsInBin.values(), key=lambda i: (-i['pos'][0], -i['pos'][1]))
    fltHeuristicFidelity = 0.70
    
    if "PSO" in strAlgorithmName and "ACO" in strAlgorithmName:
        fltHeuristicFidelity = 0.80
    elif "ACO" in strAlgorithmName:
        fltHeuristicFidelity = 0.75
        
    intOptimizedCount = int(len(arrPerfectOrder) * fltHeuristicFidelity)
    arrDeliveryQueue = [i['id'] for i in arrPerfectOrder[:intOptimizedCount]]
    
    objRemainingSet = set(dictItemsInBin.keys()) - set(arrDeliveryQueue)
    
    # Simple cluster addition for the rest
    while objRemainingSet:
        arrAccessible = [dictItemsInBin[i] for i in objRemainingSet if i in dictItemsInBin]
        if not arrAccessible: break
        
        fltMaxX = max(i['pos'][0] for i in arrAccessible)
        arrNextBatch = [i['id'] for i in arrAccessible if abs(i['pos'][0] - fltMaxX) < 5.0]
        arrNextBatch = sorted(arrNextBatch, key=lambda iid: -dictItemsInBin[iid]['pos'][1])
        
        arrDeliveryQueue.extend(arrNextBatch)
        objRemainingSet -= set(arrNextBatch)

    # Execution Loop
    for strTargetId in arrDeliveryQueue:
        if strTargetId not in dictItemsInBin: continue

        arrRemovalStack = []
        arrEventLog.append({'action': 'target', 'item_id': strTargetId})
        
        # A. Recursive Blocker Removal
        while True:
            arrBlockerIds = _getSmartBlockerStack(strTargetId, dictItemsInBin)
            if not arrBlockerIds: break

            strBlocker = arrBlockerIds[0]
            intRelocations += 1
            arrEventLog.append({'action': 'relocate', 'item_id': strBlocker})
            
            arrRemovalStack.append(dictItemsInBin.pop(strBlocker))

        # B. Delivery
        arrEventLog.append({'action': 'deliver', 'item_id': strTargetId})
        if strTargetId in dictItemsInBin:
            del dictItemsInBin[strTargetId]

        # C. Relocation Return
        while arrRemovalStack:
            dictItem = arrRemovalStack.pop()
            
            arrNewPos, arrNewDims = _findBestPositionExhaustive(
                dictItem['dims'], 
                dictItemsInBin, 
                arrBinDims, 
                dictItem.get('original_pos', [0, 0, 0])
            )
            
            dictItem['pos'] = arrNewPos
            dictItem['dims'] = arrNewDims
            dictItemsInBin[dictItem['id']] = dictItem
            
            arrEventLog.append({
                'action': 'return_relocated',
                'item_id': dictItem['id'],
                'new_pos': arrNewPos,
                'new_dims': arrNewDims
            })

        # D. Gravity Settle
        blnStable = False
        intIters = 0
        
        while not blnStable and intIters < 15:
            blnStable = True
            intIters += 1
            
            for strId in sorted(dictItemsInBin.keys(), key=lambda i: dictItemsInBin[i]['pos'][1]):
                if strId not in dictItemsInBin: continue
                
                dictItem = dictItemsInBin[strId]
                fltCurY = dictItem['pos'][1]
                blnSupported, fltSupportY = _hasGravitySupport(dictItem['pos'], dictItem['dims'], dictItemsInBin)
                
                if fltCurY > fltSupportY + 1e-4:
                    blnStable = False
                    dictItem['pos'][1] = fltSupportY
                    arrEventLog.append({'action': 'settle', 'item_id': strId, 'new_y_pos': fltSupportY})

    return {
        'event_log': arrEventLog,
        'relocation_count': intRelocations
    }

# end of _generateUnloadingSequence