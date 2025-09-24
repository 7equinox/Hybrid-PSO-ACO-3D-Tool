# HYBRID-PSO-ACO-3D-TOOL/backend/algorithms/pso.py

import random
from deap import base, tools
# Import the custom DEAP creator object from our base configuration.
from .base import creator

# --- Particle Swarm Optimization (PSO) ---
# This implementation follows the system architecture for PSO described in Chapter 3.
# It uses DEAP for the evolutionary computation framework.

def run_pso(items, evaluate_solution, num_particles=30, max_generations=50):
    """
    Executes the standalone Particle Swarm Optimization algorithm.
    """
    num_items = len(items)

    # Initialize DEAP toolbox for setting up the PSO components.
    toolbox = base.Toolbox()

    # Step 1: Initialization (from PSO System Architecture)
    # A particle's position is a permutation of item indices.
    toolbox.register("permutation", random.sample, range(num_items), num_items)
    # Register the 'Particle' creator for generating individuals.
    toolbox.register("particle", tools.initIterate, creator.Particle, toolbox.permutation)
    # Create the 'swarm' (population) of particles.
    toolbox.register("population", tools.initRepeat, list, toolbox.particle)

    # Register the fitness function (evaluation) and particle update rule.
    toolbox.register("evaluate", evaluate_solution)
    toolbox.register("update", update_particle, phi1=2.0, phi2=2.0)
    
    # Create the initial swarm.
    swarm = toolbox.population(n=num_particles)
    
    # Initialize the Global Best (gBest) holder.
    gbest = None

    # Main optimization loop, iterating for a set number of generations.
    for gen in range(max_generations):
        # Step 2: Fitness Evaluation
        for part in swarm:
            # Calculate fitness for new particles.
            if not part.fitness.valid:
                part.fitness.values = toolbox.evaluate(part)

            # Step 3: pBest and gBest Update
            # Update the particle's Personal Best (pBest) if the current position is better.
            if not part.pbest or part.pbest.fitness < part.fitness:
                part.pbest = creator.Particle(part)
                part.pbest.fitness.values = part.fitness.values

            # Update the Global Best (gBest) for the entire swarm.
            if not gbest or gbest.fitness < part.fitness:
                gbest = creator.Particle(part)
                gbest.fitness.values = part.fitness.values
        
        # Step 4: Velocity and Position Update
        # Apply the update rule to move each particle in the search space.
        for part in swarm:
            toolbox.update(part, gbest)
            
    # The process terminates when max generations are reached.
    return gbest, gbest.fitness.values

def update_particle(part, gbest, phi1, phi2, w=0.5):
    """
    Updates a particle's position for permutation-based PSO.
    Instead of a continuous velocity vector, this uses a series of swap operations
    to move from one permutation to another. The swaps are guided by the
    difference between the current position and the pBest/gBest positions.
    """
    num_items = len(part)

    # Cognitive component: moves inspired by the particle's own best position.
    pbest_swaps = []
    # Find indices where current particle differs from its personal best.
    pbest_diff = [i for i in range(num_items) if i < len(part.pbest) and part[i] != part.pbest[i]]
    if len(pbest_diff) >= 2:
        # Generate a number of swaps proportional to the cognitive parameter phi1.
        num_swaps = int(phi1 * random.random() * len(pbest_diff) / 2)
        for _ in range(num_swaps):
             pbest_swaps.append(tuple(random.sample(pbest_diff, 2)))
    
    # Social component: moves inspired by the swarm's global best position.
    gbest_swaps = []
    gbest_diff = [i for i in range(num_items) if i < len(gbest) and part[i] != gbest[i]]
    if len(gbest_diff) >= 2:
        # Generate swaps proportional to the social parameter phi2.
        num_swaps = int(phi2 * random.random() * len(gbest_diff) / 2)
        for _ in range(num_swaps):
            gbest_swaps.append(tuple(random.sample(gbest_diff, 2)))

    # Apply the calculated swaps to update the particle's position.
    for i, j in (pbest_swaps + gbest_swaps):
        part[i], part[j] = part[j], part[i]