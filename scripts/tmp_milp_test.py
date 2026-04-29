import numpy as np
from pulp import (
    LpProblem,
    LpMinimize,
    LpMaximize,
    LpVariable,
    lpSum,
    PULP_CBC_CMD,
    LpStatus,
    value,
)


np.random.seed(42)


class ProblemConfig:
    def __init__(self):
        self.num_drones = 2
        self.battery_capacity = 100.0
        self.payload_capacity = 10.0
        self.alpha = 0.5
        self.beta = 2.0
        self.drone_mass = 3.0
        self.battery_mass = 1.0
        self.bnb_gap_tolerance = 0.05
        self.lambda_weight = 0.05

    def energy_consumption(self, distance: float, payload_mass: float) -> float:
        total_mass = self.drone_mass + self.battery_mass + payload_mass
        return (self.alpha * total_mass + self.beta) * distance


class InstanceGenerator:
    def __init__(self, config: ProblemConfig):
        self.config = config

    def generate_instance(self, num_customers: int, area_size=(30.0, 30.0)):
        depot_x, depot_y = area_size[0] / 2, area_size[1] / 2
        customers = []
        for _ in range(num_customers):
            while True:
                x = float(np.random.uniform(0, area_size[0]))
                y = float(np.random.uniform(0, area_size[1]))
                if ((x - depot_x) ** 2 + (y - depot_y) ** 2) ** 0.5 > 2.0:
                    customers.append((x, y))
                    break

        demands = np.random.gamma(shape=2.0, scale=1.5, size=num_customers)
        demands = np.clip(demands, 0.5, 8.0)

        all_x = [depot_x] + [c[0] for c in customers]
        all_y = [depot_y] + [c[1] for c in customers]

        n = num_customers
        dist = np.zeros((n + 1, n + 1))
        for i in range(n + 1):
            for j in range(n + 1):
                if i != j:
                    dist[i, j] = ((all_x[i] - all_x[j]) ** 2 + (all_y[i] - all_y[j]) ** 2) ** 0.5

        avg_payload = float(np.mean(demands))
        energy = np.zeros((n + 1, n + 1))
        for i in range(n + 1):
            for j in range(n + 1):
                if i != j:
                    energy[i, j] = self.config.energy_consumption(dist[i, j], avg_payload / 2.0)

        return {
            "num_customers": n,
            "demands": demands.tolist(),
            "distance_matrix": dist,
            "energy_matrix": energy,
        }


class DroneDeliveryMILP:
    def __init__(self, instance, config: ProblemConfig):
        self.instance = instance
        self.config = config
        self.n = instance["num_customers"]
        self.m = config.num_drones
        self.model = None
        self.variables = {}

    def build_model(self):
        self.model = LpProblem("Drone_Delivery_TOP", LpMaximize)

        N = list(range(1, self.n + 1))
        N0 = [0] + N
        K = list(range(1, self.m + 1))

        e = self.instance["energy_matrix"]
        q = [0.0] + self.instance["demands"]
        # Use urgency as profit for TOP selection
        p = [0.0] + [1.0] * self.n
        B = self.config.battery_capacity
        Q = self.config.payload_capacity
        M = 10000.0
        lam = self.config.lambda_weight

        x = LpVariable.dicts("x", ((i, j, k) for i in N0 for j in N0 if i != j for k in K), cat="Binary")
        y = LpVariable.dicts("y", (i for i in N), cat="Binary")
        u = LpVariable.dicts("u", ((i, k) for i in N0 for k in K), lowBound=0, upBound=Q)
        b = LpVariable.dicts("b", ((i, k) for i in N0 for k in K), lowBound=0, upBound=B)
        self.variables = {"x": x, "y": y, "u": u, "b": b}

        total_energy = lpSum(e[i][j] * x[(i, j, k)] for i in N0 for j in N0 if i != j for k in K)
        total_profit = lpSum(p[i] * y[i] for i in N)
        self.model += total_profit - lam * (total_energy / B)

        # Customer selection linking: if y[i]=1 then visit exactly once; else not visited
        for i in N:
            self.model += lpSum(x[(j, i, k)] for j in N0 if j != i for k in K) == y[i]
            self.model += lpSum(x[(i, j, k)] for j in N0 if j != i for k in K) == y[i]

        self.model += lpSum(y[i] for i in N) >= 1

        # Flow conservation per drone (including depot)
        for j in N0:
            for k in K:
                self.model += lpSum(x[(i, j, k)] for i in N0 if i != j) == lpSum(x[(j, i, k)] for i in N0 if i != j)

        # Battery
        for k in K:
            self.model += b[(0, k)] == B

        for i in N0:
            for j in N0:
                if i == j:
                    continue
                for k in K:
                    if j != 0:
                        self.model += b[(j, k)] <= b[(i, k)] - e[i][j] + M * (1 - x[(i, j, k)])
                    else:
                        self.model += b[(i, k)] - e[i][j] >= -M * (1 - x[(i, j, k)])

        # Payload remaining
        for k in K:
            self.model += u[(0, k)] == Q

        for i in N0:
            for j in N:
                if i == j:
                    continue
                for k in K:
                    self.model += u[(j, k)] <= u[(i, k)] - q[j] + M * (1 - x[(i, j, k)])
                    self.model += u[(i, k)] >= q[j] * x[(i, j, k)]

    def solve(self, time_limit=30):
        solver = PULP_CBC_CMD(timeLimit=time_limit, msg=0, gapRel=self.config.bnb_gap_tolerance)
        self.model.solve(solver)
        return LpStatus[self.model.status], value(self.model.objective)


if __name__ == "__main__":
    config = ProblemConfig()
    inst = InstanceGenerator(config).generate_instance(5)
    print("total demand", round(sum(inst["demands"]), 3))
    e = inst["energy_matrix"]
    B = config.battery_capacity
    # Basic reachability diagnostics
    infeasible_from_depot = [j for j in range(1, 6) if e[0][j] > B]
    infeasible_return_to_depot = [i for i in range(1, 6) if e[i][0] > B]
    print("customers with e[0][j] > B:", infeasible_from_depot)
    print("customers with e[i][0] > B:", infeasible_return_to_depot)
    # For each customer, check if it has any feasible incoming arc from any node (including depot)
    no_feasible_incoming = []
    for j in range(1, 6):
        feasible = any(i != j and e[i][j] <= B for i in range(0, 6))
        if not feasible:
            no_feasible_incoming.append(j)
    print("customers with NO feasible incoming arc (<=B):", no_feasible_incoming)

    milp = DroneDeliveryMILP(inst, config)
    milp.build_model()
    status, obj = milp.solve()
    print("status", status)
    print("obj", obj)
