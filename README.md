# Intelligent Slab Allocation System

## 1. Overview

This project implements an intelligent slab-to-plate allocation system for a steel plate mill.

The system recommends slab-to-plate allocations while satisfying material and operational constraints and minimising material waste.

Two allocation approaches are implemented:

- **Greedy Best-Fit Heuristic**
- **SCIP Mixed-Integer Programming (MIP)**

Both approaches use the same data model, feasibility checks and KPI calculations, allowing their solutions to be compared consistently.

---

## 2. Problem Formulation

A customer order may contain one or more plates. Each plate must be allocated to a compatible slab.

For a plate \(p\) and slab \(s\), the required slab length is calculated as:

```math
L_{p,s} =
\text{calculate\_required\_length}(s,p)

```
A plate can only be allocated when:

- the slab is compatible with the plate/order;
- sufficient slab length is available;
- inventory restrictions are satisfied.

The optimisation decision variable is:

```math
x_{p,s} \in \{0,1\}
```

where \(x_{p,s}=1\) indicates that plate \(p\) is allocated to slab \(s\).

The slab capacity constraint is:
```math
\sum_p L_{p,s}x_{p,s} \leq L_s
```

For orders requiring full fulfilment, all plates in the order must be allocated.

The optimisation objective balances order fulfilment and yield-loss minimisation:

```math
\max(w_f * F - w_y* Y)
```

where:

- \(F\) = order fulfilment ratio;
- \(Y\) = normalised yield loss;
- \(w_f\) = order fulfilment weight;
- \(w_y\) = yield-loss minimisation weight.

The default weights are:

```python
order_fulfilment_weight = 0.4
yield_loss_minimisation_weight = 0.6
```

For orders requiring full fulfilment, all plates belonging to the order must be allocated for the order to be considered fulfilled.

The optimisation objective balances:

- order fulfilment;
- slab yield loss.

The two objective components are normalised and combined using user-defined weights.

---

## 3. Assumptions

The following assumptions apply where the problem statement does not specify implementation details:

- A slab can be allocated to multiple plates, provided that the total required length does not exceed its available length.
- Unused length from an opened slab is counted as yield loss.
- Reserved slabs are unavailable for the current allocation.
- Incoming slabs are unavailable until their specified availability date.
- Steel grade, quality, supplier, and surface-class restrictions are treated as hard compatibility constraints.
- Orders requiring full fulfilment are considered fulfilled only when all associated plates are allocated.
- A plate can be allocated to at most one slab.
- Required slab-length calculations are deterministic.
- The Greedy method is a heuristic and does not guarantee global optimality.
- SCIP optimises the formulated objective subject to the defined constraints.

---

## 4. Data Modelling

The system uses four main data objects.

### Slab

A slab contains:

- `slab_id`
- `length`
- `grade`
- `quality`
- `supplier`
- `surface_class`
- `status`
- `available_from`

### Plate

A plate contains:

- `plate_id`
- `order_id`
- `length`
- `width`
- `thickness`
- `grade`
- `quality`

### Order

An order contains:

- `order_id`
- `customer`
- `plates`
- `allowed_suppliers`
- `required_surface_class`
- `require_full_fulfilment`

### `Allocation`

Represents the selected relationship:

```text
Order → Plate → Slab
```

Each allocation also records the required slab length.

### Input Formats

Input data is supported in:

- Excel
- JSON

---

## 5. Allocation Logic

### Initial Feasibility Analysis

Before allocation, each plate is checked against available slabs. The system identifies:

- Compatible slabs
- Slabs with sufficient individual length
- Initially infeasible plates

This prevents infeasible plate/slab combinations from entering the optimisation model.

Typical initial infeasibility reasons include:

- `No compatible slab`
- `Insufficient slab length`

### Greedy Best-Fit

The Greedy algorithm processes orders sequentially.

For each plate, it:

1. Identifies feasible slabs with sufficient remaining capacity.
2. Selects the slab that leaves the smallest remaining capacity.
3. Commits temporary allocations only if all plates in an order can be fulfilled.

This approach provides a fast, practical allocation method and a baseline for comparison against mathematical optimisation.

### SCIP MIP Optimisation

SCIP uses binary plate-to-slab allocation variables for feasible combinations.

The optimisation model enforces:

- Plate allocation constraints
- Slab capacity constraints
- Order-fulfilment requirements
- Slab usage and yield-loss calculation

A slab-use variable is linked to allocation variables so that the full length of every opened slab is included when calculating yield loss.

### Post-Allocation Feasibility

After either allocation algorithm completes, the system identifies plates that were initially feasible but could not ultimately be allocated.

These are reported using reasons such as:

- `Insufficient available slab length`

Unallocated results are returned at order level along with affected plates.

#### Example

```json
{
  "O005": {
    "reason": "Insufficient available slab length",
    "affected_plates": ["P017"]
  }
}
```

---

## 6. KPIs

The same key performance indicators (KPIs) are calculated for both allocation algorithms:

- Material consumption
- Yield loss
- Slab utilisation
- Order fulfilment
- Runtime

### Yield-Loss Calculation

\[
\text{Yield Loss} = \text{Total Slab Length Used} - \text{Material Consumption}
\]

This provides a consistent basis for comparing the Greedy and SCIP approaches.

---

## 7. Project Structure

```text
intelligent-slab-allocation-system/
│
├── models/
│   ├── data_loader.py
│   ├── models_and_kpis.py
│   ├── allocations_algorithms.py
│   └── main.py
│
├── data/
│
├── output/
│
├── notebooks/
│   └── experiments.ipynb
│
├── requirements.txt
└── README.md
```

### Main Modules

#### `data_loader.py`

Loads Excel and JSON input data and converts records into the system data objects.

#### `models_and_kpis.py`

Contains the core data models and common KPI calculations.

#### `allocations_algorithms.py`

Contains:

- Compatibility checks
- Feasibility analysis
- Greedy allocation
- SCIP optimisation
- Post-allocation diagnosis

#### `main.py`

Provides the application entry point, including:

- Algorithm selection
- Objective-weight configuration
- KPI reporting
- JSON output generation

---

## 8. Running the Project

### Configuration

Example configuration in `main.py`:

```python
order_file_dir = "data/orders_input_s30_p50.xlsx"
slab_file_dir = "data/slab_inventory_input_s30_p50.xlsx"

allocation_algorithm_type = "SCIP"

fulfilment_weight = 0.4
yield_loss_weight = 0.6
```

### Run the Application

```bash
python models/main.py
```

The system prints allocation results and KPIs, then generates a JSON output file containing:

- Selected allocations
- Unallocated-order information
- KPI results

Output filenames reflect the problem size and allocation algorithm. For example:

```text
allocation_s30_p50_SCIP.json
allocation_s30_p50_greedy.json
```


----


## 9. Example API / Service Interface

The allocation logic is separated from the application entry point, allowing it to be integrated into another planning system or exposed as a service.

### Core Conceptual Python Interface

```python
result = solve_slab_allocation(
    slabs=slabs,
    orders=orders,
    algorithm="SCIP",
    fulfilment_weight=0.4,
    yield_loss_weight=0.6
)
```
The current system accepts slab and order data through Excel or JSON files. Algorithm selection and optimisation weights are supplied separately through the application configuration.

For future integration as an API/service, these inputs could be combined into a single request:

### Example API Request

```json
{
  "slabs": [],
  "orders": [],
  "algorithm": "SCIP",
  "objective_weights": {
    "fulfilment_weight": 0.4,
    "yield_loss_weight": 0.6
  }
}
```

#### Output

```json
{
  "allocations": [],
  "unallocated_orders": {},
  "kpis": {},
  "runtime_seconds": 0.0
}
```


## 9. Deployment and Monitoring Overview

The allocation engine can be deployed as a Python service between an order/inventory system and the production-planning system.

```text
Order / Inventory System
          ↓
    Allocation Service
          ↓
   Feasibility Analysis
          ↓
    Greedy / SCIP
          ↓
     KPI Calculation
          ↓
 Recommended Allocation
```

For production deployment, package the Python environment and SCIP configuration reproducibly.

### Configurable Parameters

The following operational parameters should remain configurable:

- Allocation algorithm
- Objective weights
- Solver time limit
- Input locations
- Output locations

### Monitoring

Recommended production metrics include:

- Allocation runtime
- Number of fulfilled orders
- Number of unallocated orders
- Order-fulfilment ratio
- Yield loss
- Slab utilisation
- Solver status and timeouts
- Reasons for infeasibility

Infeasibility analysis can identify recurring inventory or compatibility problems, including:

- `No compatible slab`
- `Insufficient slab length`
- `Insufficient available slab length`

---
