# Project Report 
we are working on phase 1 (Problem Modeling & Formulation) and 2 (Complexity Analysis) more specifically in Subphase 1.2: Mathematical Formulation 1 - Arc-Based MILP where we must propose a mathematical  formulation The first formulation should follow a classical optimization approach (e.g., MILP-based assignment or scheduling model) and studying the complexity of the probeml 

The problem is **Multi-Depot Vehicle Routing Problem with Energy Constraints (MDVRP-EC)** with combination of :
- Vehicle Routing Problem (VRP)
- Capacitated VRP (CVRP)
- Electric VRP (EVRP)
- Team Orienteering Problem (TOP) (will be explained shortly)

## Problem understanding 
- There is a **depot** (or multiple depots) where drones start, load packages, and return for recharging or reloading.
- **Customers** (delivery points) each have a demand (package weight/volume, q_i) and a location.
- A **fleet of identical** (K drones) performs deliveries. Each drone can make multiple trips if it returns to the depot.
- The objective is Maximize total profit collected, while total energy used by each drone ≤ Battery limit. due to the chosing the approach of TOP with drone resources (batteries, fleet) are scarce, so prioritize high-value or urgent deliveries. Secondary objective is Minimize energy used

### Modeling the problem as TOP 
Since the Algerian market doesn not currently use widespread drone-based delivery for commercial goods or last-mile consumer packages due to many factors, and Although not yet operational, the country is actively building infrastructure for future technological applications, including a dedicated, government-supported, drone-focused we restrict our focus in this project to encourage and facilitate the adaptation of drone-based delivery to considering a small number of drones and not enough battery power.

This considerations makes the Team oriented Problem the best template for the project because instead of trying to serve everyone (which is impossible), you should choose the most important customers first.
By most important we take into consideration 
- **Prioritize high-value deliveries** Some customers are more important than others. For example:
	- Customer A orders medicine → very high value
	- Customer B orders a book → low value
	- Customer C orders food (urgent) → high urgency

So we give priority to customers with **high urgency/high importance**.
we introduce p_i factor to represent the urgency of the delivery i 

## Problem constraints
1. As a result to TOP template, we change the constraint of Each customer must be served exactly once to Each customer is visited at most once (not exactly once) if we still consider the larger set of customers or keep it  Each customer must be served exactly once of the subset with higher urgency.
2. Capacity constraints:
	- Payload: Cumulative load on a route ≤ Q.
	- Energy/Battery: Remaining battery after each leg ≥ 0; track consumption e_ij (which may depend on current payload).
3. Route stricture: Routes starts and ends at depots
4. Battery/Payload : each drone performs one route per battery charge. no charging in the middle of the route. Each drone must return to depot with non negative attery => must be battery aware (tracking remaining capacity)
Solutions must ensure every route is feasible (battery and payload never exceeded) and the overall plan covers demands efficiently.

## Problem assumptions 
1. homogenous drones
2. deterministic demands (demands of customer x is set to Y kg), distance (distance between point i and j is deterministic ie we dont take into consideration wind, obstacles, traffic), and energy models(energy conmused from i to j under the same conditions is the same).
3. instant loading/unloading
4. drones can make multiple trips 
5. further discussion Euclidean distance or Real GIS data 
6. No simultaneous drone operations conflicting in airspace.


The first formulation should follow a classical optimization approach (e.g., MILP-based
assignment or scheduling model).



## Key Modeling choices and justifications
TOP influence: To transform the problem from “serve a subset of customers” into “serve all customers in a selected subset”, we perform the following pre-processing step before formulating the mathematical model . 
#### Pre-processing Procedure
1. Let S={1,2,…,s}  be the full set of all potential customers.
2. For each customer i∈S, assign a **profit/urgency score** pi≥0 .
    - Higher values of pi  are given to high-urgency or high-value deliveries (medicine).
    - Lower values are assigned to standard or low-priority deliveries (books).
3. Sort all customers in **decreasing order** of their profit/urgency score pi.
4. Define a threshold Kmax​ = maximum number of customers that can be reasonably served given the limited fleet size and battery capacity (this threshold can be determined based on preliminary experiments).
5. Select the top Kmax​ customers with the highest pi values. Let N⊆S  be this selected subset of high-priority customers, where ∣N∣=Kmax⁡.

After this pre-processing step, the optimization problem is solved only on the reduced set N.

This reflects real Algerian market priorities where resources are scarce.

**Primary Objective**: Maximize total profit collected.

**Secondary Objective**: Minimize total energy consumption among high-profit solutions. We use a **weighted single objective**: **Maximize** ∑ p_i * served_i − λ * TotalEnergy where λ > 0 is a small weighting factor (tuned during experiments, e.g., 0.01–0.1) to prioritize profit while penalizing excessive energy use.
 
**Battery modeling**: Each route starts and ends at a depot with full battery. No recharging during a route. Remaining battery is tracked to ensure feasibility.

## Sets and Parameters
- K = {1, 2, ..., m} : Set of identical drones 
- N₀ = N ∪ {0} : Nodes including the depot (0).
- N = {1, 2, ..., n} : Set of customers
- d_{ij} : Distance from i to j 
- e_{ij} : Energy consumed when flying from i to j 
- q_i : Demand (payload weight) of customer i
- p_i : Profit/urgency score of customer i
- B : Battery capacity (energy units)
- Q : Payload capacity per drone (weight units)

## Decision variables
- x_{ijk} ∈ {0,1} : 1 if drone k travels directly from node i to node j, 0 otherwise
- u_{ik} ≥ 0 : Cumulative payload (load) on drone k after visiting node i (for capacity tracking)
- b_{ik} ≥ 0 : Remaining battery of drone k upon arrival at node i (for energy tracking)
- zk∈{0,1} : 1 if drone k has started its operations (used only for initial battery)



## **Exact method implementation**
#### Branch and Bound Design
1. Branching strategy:
	- We split the problem by deciding one by one whether a drone should fly directly from one point to another (x_ijk). This creates two branches (two sub-problems yes or no). 
	- we solve the LP relaxation where these variables are allowed to take fractional values (like 0.3, 0.7, 0.45, etc.)
	- We choose the most uncertain decision first (the one closest to 0.5 in the relaxed solution). This helps reducing the feasible region (possible route structures) much faster than random branching. It quickly forces the solver to make clear decisions about which drone goes where, which helps eliminate invalid partial routes early and not the ones we are certain about.
	
2. Bounding strategy:
	- In each branch, we solve a relaxed version (LP relaxation) to get a Lower Bound (best possible energy if we continue this way).
	- Use a heuristic (Nearest Neighbor) to get an Upper Bound (a good feasible energy we already know). The heuristic builds feasible routes while respecting battery and payload constraints. Every time a new integer feasible solution is found, the upper bound is updated.
	
3. Prune :
	- If the Lower Bound is already worse than the best solution we have → throw away this entire branch (no need to explore further).
	- If the LP relaxation at a node is infeasible (violates battery, payload, or flow constraints), the node is pruned.
	
4. Node Selection:
	- Best-First: Always explore the most promising branch first (recommended).
	
5. Repeat: Keep branching on the most promising parts until all branches are explored or pruned.


#### Implementation Details
**Solver Integration**

- We use an existing **LP/MILP solver** (Gurobi, CPLEX, or SCIP) to solve the LP relaxation at each node of the Branch & Bound tree.
- The solver is called repeatedly to solve the relaxed problem with some variables fixed according to the branching decisions.

**Custom Branch & Bound Tree Management** 
Instead of using the solver’s built-in B&B (black-box), we implement a **custom Branch & Bound framework** in Python to have full control over:

- Branching decisions
- Node selection
- Upper and lower bound management

**Preprocessing and Enhancements**

1. **Preprocessing Techniques**:
    - Variable fixing: Fix xi0k=0  or x0jk=0  when clearly impossible based on energy or distance.
    - Reduced cost fixing (if dual information is available).
    - Logical implications (if battery is too low to reach certain customers).
    
2. **Constraint Tightening**:
    - Add valid inequalities to strengthen the LP relaxation (subtour elimination cuts, capacity cuts, battery-based cuts).
    - Use MTZ-based constraints more efficiently.
    
3. **Initial Upper Bound**:
    - Run the Nearest Neighbor heuristic multiple times with different starting points and random perturbations to obtain a good initial feasible solution.

**Implementation Tools**

- **Programming Language**: Python 3.10+
- **Solver**: PuLP (preferred due to its simplicity and sufficientfor the scope of the project) or SCIP (open-source alternative)
- **Libraries**: gurobipy or pyscipopt for solver interaction, numpy for matrix operations.