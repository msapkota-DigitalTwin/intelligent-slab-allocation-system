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

\[
L_{p,s} =
\text{calculate\_required\_length}(s,p)
\]

A plate can only be allocated when:

- the slab is compatible with the plate/order;
- sufficient slab length is available;
- inventory restrictions are satisfied.

The optimisation decision variable is:

\[
x_{p,s} \in \{0,1\}
\]

where \(x_{p,s}=1\) indicates that plate \(p\) is allocated to slab \(s\).

The slab capacity constraint is:

\[
\sum_p L_{p,s}x_{p,s} \leq L_s
\]

For orders requiring full fulfilment, all plates in the order must be allocated.

The optimisation objective balances order fulfilment and yield-loss minimisation:

\[
\max(w_fF-w_yY)
\]

where:

- \(F\) = order fulfilment ratio;
- \(Y\) = normalised yield loss;
- \(w_f\) = fulfilment weight;
- \(w_y\) = yield-loss weight.

The default weights are:

```python
fulfilment_weight = 0.4
yield_loss_weight = 0.6
```
For orders requiring full fulfilment, all plates belonging to the order must be allocated for the order to be considered fulfilled.

The optimisation objective balances:

- order fulfilment;
- slab yield loss.

The two objective components are normalised and combined using user-defined weights.

---

## 3. Data Modelling

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

Example:

```text
S001
Length: 9 m
Grade: G1
Quality: Q1
Supplier: SUP1
Surface class: S1
Status: Available
```


