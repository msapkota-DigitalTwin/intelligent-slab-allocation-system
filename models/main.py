import os
import time

from data_loader import load_input_data
from allocations_algorithms import greedy_heuristic_allocate, solve_allocation_with_scip
from models_and_KPIS import calculate_kpis


if __name__ == "__main__":

    # =========================================================
    # Load input data

    # Excel is used here as the input format. The data loader
    # can also support JSON without changing the allocation
    # algorithms.
    # ===================
    
    data_dir =  r"D:\Projects\slab-allocation-system\intelligent-slab-allocation-system\data"

    #slab_file = os.path.join(data_dir, "slab_inventory_input.xlsx")
    slab_file = os.path.join(data_dir, "slab_inventory_input_s30_p50.xlsx")
    #order_file = os.path.join(data_dir, "orders_input.xlsx")
    order_file = os.path.join(data_dir, "orders_input_s30_p50.xlsx")

    # Load input data
    slabs, orders = load_input_data(
            slab_path=slab_file,
            order_path=order_file,
            file_format="excel"
        )

    print("=" * 60)
    print("SLAB ALLOCATION")
    print("=" * 60)

    print(
        f"Slabs loaded : {len(slabs)}"
    )

    print(
        f"Orders loaded: {len(orders)}"
    )

    print(
        f"Plates loaded: "
        f"{sum(len(order.plates) for order in orders)}"
    )


# =========================================================
# 3. Run Greedy allocation
# =========================================================

print("\n" + "=" * 60)
print("GREEDY ALLOCATION")
print("=" * 60)

start_time = time.perf_counter()

greedy_allocations, greedy_unallocated_orders = (
    greedy_heuristic_allocate(
        slabs,
        orders
    )
)

greedy_runtime = (
    time.perf_counter() - start_time
)

print(
    f"Runtime: {greedy_runtime:.4f} seconds"
)

print(
    f"Allocations: {len(greedy_allocations)}"
)

print(
    f"Unallocated orders: "
    f"{len(greedy_unallocated_orders)}"
)

# =========================================================
# Calculate Greedy KPIs
# =========================================================

greedy_kpis = calculate_kpis(
    slabs,
    orders,
    greedy_allocations,
    greedy_unallocated_orders
)

print("\nGreedy KPIs:")

for key, value in greedy_kpis.items():

    print(
        f"  {key}: {value}"
    )


# =========================================================
# 5. Run SCIP optimisation
# =========================================================

print("\n" + "=" * 60)
print("Running SCIP OPTIMISATION")
print("=" * 60)

start_time = time.perf_counter()

scip_allocations, scip_unallocated_orders, _ = solve_allocation_with_scip(
    slabs,
    orders,

    # Objective weights
    fulfilment_weight=0.8,
    yield_loss_weight=0.2,

    # Maximum solver runtime
    time_limit=30
)

scip_runtime = (
    time.perf_counter() - start_time
)

print(
    f"Runtime: {scip_runtime:.4f} seconds"
)


print(
    f"Allocations: {len(scip_allocations)}"
)

print(
    f"Unallocated orders: "
    f"{len(scip_unallocated_orders)}"
)


# =========================================================
# 7. Calculate SCIP KPIs
# =========================================================

scip_kpis = calculate_kpis(
    slabs,
    orders,
    scip_allocations,
    scip_unallocated_orders
)

print("\nSCIP KPIs:")

for key, value in scip_kpis.items():

    print(
        f"  {key}: {value}"
    )