
# =========================================================
# main.py
# =========================================================

# The user need to provide:
#   - order input file
#   - slab inventory input file
#   - allocation algorithm
#   - objective weightages
#
# The system then:
#   1. Loads the input data
#   2. Runs the selected allocation algorithm
#   3. Calculate KPIs
#   4. Prints the KPIs
#   5. Saves the allocation result as JSON
#
# Supported algorithms:
#   - greedy
#   - SCIP/MIP
# =========================================================


import os
import time
import json

from data_loader import load_input_data
from allocations_algorithms import greedy_heuristic_allocate, solve_allocation_with_scip
from models_and_KPIS import calculate_kpis


if __name__ == "__main__":

    # =========================================================
    # User configuration
    # =========================================================

    data_dir =  r"D:\Projects\slab-allocation-system\intelligent-slab-allocation-system\data"

    #slab_file = os.path.join(data_dir, "slab_inventory_input.xlsx")
    slab_file_dir = os.path.join(data_dir, "slab_inventory_input_s30_p50.json")
    #slab_file_dir = os.path.join(data_dir, "slab_inventory_input_s40_p80.json")
    #order_file = os.path.join(data_dir, "orders_input.xlsx")
    order_file_dir = os.path.join(data_dir, "orders_input_s30_p50.json")
    #order_file_dir = os.path.join(data_dir, "orders_input_s40_p80.json")

    # can be "greedy" (or "heuristic") or "SCIP" (or "MIP")
    allocation_algorithm_type = "SCIP"
    #allocation_algorithm_type = "greedy"

    #weightages for the two objectives in the optimisation problem
    #fullfilment_weight is related to number of orders fulfilled/total orders, 
    # while yield_loss_weight is related to the total yield loss ratio in the allocation which we want to minimize. 
    # The two weights should sum to 1.
    
    order_fulfilment_weight = 0.4    # can be between 0 and 1, with yield_loss_weight = 1 - fulfilment_weight
    yield_loss_minimisation_weight = 0.6   # can be between 0 and 1, with fulfilment_weight = 1 - yield_loss_weight

    time_limit = 30


    # =========================================================
    # Output directory
    # =========================================================

    output_dir = "output"

    os.makedirs(
        output_dir,
        exist_ok=True
    )


    # =========================================================
    # Determine input format
    # =========================================================

    order_extension = os.path.splitext(
        order_file_dir
    )[-1].lower()

    slab_extension = os.path.splitext(
        slab_file_dir
    )[-1].lower()


    if order_extension != slab_extension:

        raise ValueError(
            "Order and slab files must use the same "
            "file format."
        )


    if order_extension == ".xlsx":

        file_format = "excel"

    elif order_extension == ".json":

        file_format = "json"

    else:

        raise ValueError(
            "Unsupported input format. "
            "Use .xlsx or .json."
        )


    # =========================================================
    # Load input data
    # =========================================================

    print("=" * 60)
    print("SLAB ALLOCATION SYSTEM \n")
    print("=" * 60)

    print(
        f"Order file : {order_file_dir}"
        )

    print(
        f"Slab file  : {slab_file_dir}"
        )

    print(
        f"Algorithm  : {allocation_algorithm_type}"

        )

    print(
        f"Objective weights: "
        f"Fulfilment={order_fulfilment_weight}, "
        f"Yield loss={yield_loss_minimisation_weight}"
    )


    slabs, orders = load_input_data(
            slab_file_dir,
            order_file_dir,
            file_format=file_format
        )


    number_of_orders = len(orders)

    number_of_plates = sum(
        len(order.plates)
        for order in orders
        )

    number_of_slabs = len(slabs)


    print("\nInput summary:")
    print(
        f"  Orders : {number_of_orders}"
    )

    print(
        f"  Plates : {number_of_plates}"
    )

    print(
        f"  Slabs  : {number_of_slabs}"
    )

    # =========================================================
    # Run selected allocation algorithm
    # =========================================================

    algorithm = (
        allocation_algorithm_type
        .strip()
        .lower()
    )


    start_time = time.perf_counter()


    if  "greedy" in algorithm or 'heuristic' in algorithm:

        print("\nRunning Greedy allocation...")

        allocations, unallocated_orders = (
            greedy_heuristic_allocate(
                slabs,
                orders
            )
        )


    elif "scip" in algorithm or "mip" in algorithm:

        print("\nRunning SCIP/MIP optimisation...")

        allocations, unallocated_orders = solve_allocation_with_scip(
            slabs,
            orders,
            fulfilment_weight=order_fulfilment_weight,
            yield_loss_weight=yield_loss_minimisation_weight,
            time_limit=time_limit
        )


    else:

        raise ValueError(
            f"Unknown allocation algorithm: "
            f"{allocation_algorithm_type}. "
            f"Use 'greedy', 'SCIP', or 'MIP'."
        )


    runtime_seconds = (
        time.perf_counter() - start_time
    )


    # =========================================================
    # Calculate KPIs
    # =========================================================

    kpis = calculate_kpis(
        slabs,
        orders,
        allocations,
        unallocated_orders
    )


    # Add runtime to KPI output

    kpis["runtime_seconds"] = (
        runtime_seconds
    )


    # =========================================================
    # Print KPIs
    # =========================================================

    print("\n" + "=" * 60)
    print("ALLOCATION RESULTS")
    print("=" * 60)

    print(
        f"Algorithm: "
        f"{allocation_algorithm_type}"
    )

    print(
        f"Runtime: "
        f"{runtime_seconds:.4f} seconds"
    )

    print(
        f"Allocations Total: {len(allocations)}")
    print(f"Allocated Plates-Slabs Combinations: {[(allocation.plate.plate_id, allocation.slab.slab_id) for allocation in allocations]}")
    
   
    print(
        f"\nUnallocated orders: {unallocated_orders}"
    )

    print("\nKPIs:")

    for key, value in kpis.items():

        print(
            f"  {key}: {value}"
        )


    # =========================================================
    # Determining problem size for output filename
    # =========================================================
    #
    # The problem size is derived from the number of orders,
    # plates and slabs rather than relying on a hard-coded
    # value in the code.
    # =========================================================

    problem_size = (
        f"orders_{number_of_orders}"
        f"_plates_{number_of_plates}"
        f"_slabs_{number_of_slabs}"
    )


    algorithm_name = algorithm.upper()


    output_filename = (
        f"allocation_"
        f"{problem_size}_"
        f"{algorithm_name}.json"
    )


    output_path = os.path.join(
        output_dir,
        output_filename
    )


    # =========================================================
    # Convert allocations to JSON-compatible records
    # =========================================================

    allocation_records = []

    for allocation in allocations:

        allocation_records.append(
            {
                "order_id": allocation.order.order_id,
                "plate_id": allocation.plate.plate_id,
                "slab_id": allocation.slab.slab_id,
                "required_length": (
                    allocation.required_length
                )
            }
        )


    # =========================================================
    # Prepare output
    # =========================================================

    output_data = {

        "algorithm": (
            allocation_algorithm_type
        ),

        "input": {
            "order_file": order_file_dir,
            "slab_file": slab_file_dir,
            "number_of_orders": number_of_orders,
            "number_of_plates": number_of_plates,
            "number_of_slabs": number_of_slabs
        },

        "objective_weights": {
            "fulfilment": order_fulfilment_weight,
            "yield_loss": yield_loss_minimisation_weight
        },

        "kpis": kpis,

        "allocations": allocation_records,

        "unallocated_orders": unallocated_orders
        
    }


    # =========================================================
    # Save output JSON
    # =========================================================

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output_data,
            file,
            indent=4
        )


    print(
        f"\nOutput saved to:"
        f"\n  {output_path}"
    )

    print("=" * 60)