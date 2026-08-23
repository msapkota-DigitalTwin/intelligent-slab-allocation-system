import pandas as pd
from pyscipopt import Model, quicksum, Eventhdlr, SCIP_EVENTTYPE
import time

from models_and_KPIS import Slab, Plate, Order, Allocation
from models_and_KPIS import  is_compatible, calculate_required_length


def greedy_heuristic_allocate(slabs, orders):
    """
    Perform greedy allocation of slabs to plates in orders.

    Returns
    -------
    allocations : list
        Feasible slab-to-plate Allocation objects.

    unallocated_orders : dict
        Orders that could not be fully allocated, together with the
        reason for failure.
    """

    allocations = []
    unallocated_orders = {}

    # Process orders sequentially
    for order in orders:

        # Temporary allocations for the current order.
        # These are committed only if the complete order can be fulfilled.
        temporary_allocations = []

        # Process plates within the current order
        for plate in order.plates:

            feasible_candidates = []

            # Examine all slabs as potential candidates
            for slab in slabs:

                # Check grade, quality, customer restrictions,
                # and inventory status.
                compatible, _ = is_compatible(
                    slab,
                    plate,
                    order
                )

                if not compatible:
                    continue

                # Calculate material required from this slab
                required_length = calculate_required_length(
                    slab,
                    plate
                )

                # Material already committed to this slab
                committed_usage = sum(
                    allocation.required_length
                    for allocation in allocations
                    if allocation.slab.slab_id == slab.slab_id
                )

                # Material temporarily assigned to this slab
                # within the current order
                temporary_usage = sum(
                    allocation.required_length
                    for allocation in temporary_allocations
                    if allocation.slab.slab_id == slab.slab_id
                )

                used_length = (
                    committed_usage +
                    temporary_usage
                )

                # Remaining slab capacity
                remaining_capacity = (
                    slab.length - used_length
                )

                # Check slab capacity constraint
                if required_length <= remaining_capacity:

                    remaining_after_allocation = (
                        remaining_capacity - required_length
                    )

                    feasible_candidates.append(
                        (
                            remaining_after_allocation,
                            slab
                        )
                    )

            # -------------------------------------------------
            # No feasible slab for this plate
            # -------------------------------------------------

            if not feasible_candidates:

                unallocated_orders[order.order_id] = (
                    f"Could not allocate plate "
                    f"{plate.plate_id}: "
                    f"no compatible slab with sufficient "
                    f"remaining capacity"
                )

                # Entire order must be rejected
                temporary_allocations = []
                break

            # -------------------------------------------------
            # Best-fit greedy selection
            # -------------------------------------------------

            feasible_candidates.sort(
                key=lambda candidate: candidate[0]
            )

            _, selected_slab = feasible_candidates[0]

            temporary_allocations.append(
                Allocation(
                    selected_slab,
                    plate,
                    order
                )
            )

        # -----------------------------------------------------
        # Commit the order only if every plate was allocated
        # -----------------------------------------------------

        if len(temporary_allocations) == len(order.plates):

            allocations.extend(
                temporary_allocations
            )

    return allocations, unallocated_orders




def solve_allocation_with_scip(slabs,
        orders,
        fulfilment_weight=0.8,
        yield_loss_weight=0.2,
        time_limit=30
    ):

    if fulfilment_weight < 0 or yield_loss_weight < 0:
        raise ValueError("Objective weights must be non-negative.")

    if not abs(
        fulfilment_weight + yield_loss_weight - 1.0
    ) < 1e-9:
        raise ValueError(
            "Objective weights must sum to 1."
        )

    """
    Perform allocation of slabs to plates in orders using SCIP.

    Returns
    -------
    allocations : list
        Feasible slab-to-plate Allocation objects.

    unallocated_orders : dict
        Orders that could not be fully allocated, together with the
        reason for failure.
    """

    # Create a new SCIP model
    opti_model = Model("slab_allocation")

    # Include the custom event handler
    log_handler = LogEventHandler()
    opti_model.includeEventhdlr(log_handler, "LogEventHandler", "Handler for capturing log data")
    
    
    # Set verbosity level (e.g., 4 for detailed information)
    opti_model.setIntParam('display/verblevel', 4)
    
    # You can also set other parameters to customize the logging output
    opti_model.setIntParam('display/freq', 1)  # Display output at every node
    

    print("SCIP model created")

    # =========================================================
    # Flatten orders into individual plates
    # =========================================================
    #
    # The optimisation operates at plate-to-slab level.
    # Therefore, we create a single list containing all plates
    # while retaining the parent order of each plate.
  
    # =========================================================
    plates = []
    plate_to_order = {}

    for order in orders:

        for plate in order.plates:

            plates.append(plate)

            plate_to_order[plate.plate_id] = order


    # =========================================================
    # Precompute feasible plate-slab combinations
    # =========================================================
    # slab-plate combination constraint matching, before the optimisation is run, 
    # to reduce the search space.
    #
    # Required lengths are calculated once here rather than
    # repeatedly during optimisation.
    # =========================================================

    required_lengths = {}
    feasible_pairs = {}

    for plate in plates:

        plate_id = plate.plate_id
        order = plate_to_order[plate_id]

        feasible_pairs[plate_id] = []

        for slab in slabs:

            compatible, _ = is_compatible(
                slab,
                plate,
                order
            )

            if not compatible:
                continue

            required_length = calculate_required_length(
                slab,
                plate
            )

            if required_length > slab.length:
                continue

            required_lengths[
                plate_id,
                slab.slab_id
            ] = required_length

            feasible_pairs[
                plate_id
            ].append(slab.slab_id)


    # =========================================================
    # Check for plates with no feasible slab
    # =========================================================
    #
    # A plate with no feasible slab cannot currently be
    # produced from the available inventory.
    #
    # We check this before constructing the optimisation model
    # so that inventory/compatibility issues can be identified
    # explicitly.
    # =========================================================

    plates_without_candidates = [
        plate_id
        for plate_id, candidates
        in feasible_pairs.items()
        if len(candidates) == 0
    ]

    print(
        "Plates with no feasible slab:",
        plates_without_candidates
    )


    # =========================================================
    # Create plate-to-slab decision variables
    # =========================================================
    #
    # x[p,s] = 1:
    #     Plate p is allocated to slab s.
    #
    # x[p,s] = 0:
    #     Plate p is not allocated to slab s.
    #
    # Variables are created only for feasible plate-slab pairs.
    # =========================================================

    x = {}

    for plate_id, slab_ids in feasible_pairs.items():

        for slab_id in slab_ids:

            x[
                plate_id,
                slab_id
            ] = opti_model.addVar(
                vtype="B",
                name=f"x_{plate_id}_{slab_id}"
            )

    print("Allocation variables:", len(x))


    # =========================================================
    # Step 6: Create order fulfilment variables
    # =========================================================
    #
    # z[o] = 1:
    #     The complete order is fulfilled.
    #
    # z[o] = 0:
    #     The order is not fulfilled.
    #
    # This allows the model to represent inventory shortages
    # while preventing partial fulfilment of an order.
    # =========================================================

    z = {}

    for order in orders:

        z[order.order_id] = opti_model.addVar(
            vtype="B",
            name=f"z_{order.order_id}_fulfilled"
        )

    print("Order variables:", len(z))


    # =========================================================
    # Enforce complete order fulfilment
    # =========================================================
    #
    # For every plate belonging to an order:
    #
    #     sum(x[p,s]) = z[o]
    #
    # If z[o] = 1:
    #     every plate in the order must be allocated exactly once.
    #
    # If z[o] = 0:
    #     none of the plates in the order can be allocated.
    #
    # Therefore, an order cannot be partially fulfilled.
    # =========================================================

    for order in orders:

        order_id = order.order_id

        for plate in order.plates:

            plate_id = plate.plate_id

            opti_model.addCons(
                quicksum(
                    x[plate_id, slab_id]
                    for slab_id in feasible_pairs[plate_id]
                )
                == z[order_id],

                name=f"Order_{order_id}_Plate_{plate_id}"
            )


    # =========================================================
    # Step 8: Enforce slab capacity constraints
    # =========================================================
    #
    # The total material required by all plates assigned to a
    # slab cannot exceed the physical length of that slab.
    #
    #     sum(required_length[p,s] * x[p,s]) <= slab.length
    #
    # This prevents multiple plates from collectively consuming
    # more material than the selected slab can provide.
    # =========================================================

    for slab in slabs:

        slab_id = slab.slab_id

        opti_model.addCons(
            quicksum(
                required_lengths[plate_id, slab_id]
                * x[plate_id, slab_id]

                for plate_id, sid in x
                if sid == slab_id
            )
            <= slab.length,

            name=f"Slab_{slab_id}_Capacity"
        )

    # =========================================================
    # Step Create slab usage variables
    # =========================================================
    #
    # y[s] = 1:
    #     Slab s is used by at least one allocation.
    #
    # y[s] = 0:
    #     Slab s is not used.
    #
    # These variables are required to calculate yield loss,
    # because unused length is counted only for slabs that are
    # actually selected for production.
    # =========================================================

    y = {}

    for slab in slabs:

        y[slab.slab_id] = opti_model.addVar(
            vtype="B",
            name=f"y_{slab.slab_id}_used"
        )

    ## =========================================================
    # Step: Calculate total slab length used
    # =========================================================
    #
    # y[s] = 1 indicates that slab s is used.
    #
    # Therefore, the total length of slabs used is:
    #
    #       sum(length[s] * y[s])
    # =========================================================

    total_slab_length_used = quicksum(
        slab.length * y[slab.slab_id]
        for slab in slabs
    )

    print("Total slab length expression created.")

    # =========================================================
    # Step 11: Calculate total material consumption
    # =========================================================
    #
    # required_lengths[p,s] contains the slab length required
    # when plate p is produced from slab s.
    #
    # The expression below calculates the total slab material
    # consumed by the selected allocations.
    # =========================================================

    total_material_consumption = quicksum(
        required_lengths[plate_id, slab_id]
        * x[plate_id, slab_id]

        for plate_id, slab_id in x
    )

    print("Material consumption expression created.")


    # =========================================================
    # Step 13: Define total yield loss
    # =========================================================
    #
    # Yield loss represents the unused length of slabs that
    # are opened/used for production.
    #
    #       yield loss =
    #       slab length used - material consumed
    # =========================================================

    total_yield_loss = (
        total_slab_length_used
        - total_material_consumption
    )

    print("Yield loss expression created.")


    # =========================================================
    # Step: Define order fulfilment reward
    # =========================================================
    #
    # z[o] = 1 means the complete order is fulfilled.
    #
    # We first want to maximise the number of fulfilled orders.
    # A sufficiently large value M is therefore assigned to
    # each fulfilled order.
    # =========================================================


    total_orders_fulfilled = quicksum(
        z[order.order_id]
        for order in orders
    )

    print("Order fulfilment expression created.")


    # =========================================================
    # Normalised objective components
    # =========================================================

    # Fraction of orders completely fulfilled
    fulfilment_ratio = (
        total_orders_fulfilled
        / len(orders)
    )

    # Total available slab inventory
    total_available_slab_length = sum(
        slab.length
        for slab in slabs
    )

    # Fraction of available slab length lost as yield loss
    yield_loss_ratio = (
        total_yield_loss
        / total_available_slab_length
    )

    # =========================================================
    # Step: Define weighted objective
    # =========================================================
    #
    # The user controls the trade-off between:
    #
    #   - complete order fulfilment
    #   - material efficiency
    #
    # The weights should sum to 1.
    # =========================================================

    objective = (
        fulfilment_weight * fulfilment_ratio
        - yield_loss_weight * yield_loss_ratio
    )

    opti_model.setObjective(
        objective,
        "maximize"
    )

    print("Weighted objective defined.")


    # =========================================================
    # Step 16: Inspect optimisation model
    # =========================================================

    print(
        "Number of allocation variables (x):",
        len(x)
    )

    print(
        "Number of order fulfilment variables (z):",
        len(z)
    )

    print(
        "Number of slab usage variables (y):",
        len(y)
    )

    print(
        "Number of constraints:",
        opti_model.getNConss()
    )

    # =========================================================
    # Step 17: Solve the slab allocation model
    # =========================================================
  

    time_limit = time_limit  # seconds

    opti_model.setRealParam(
        "limits/time",
        time_limit
    )
    start_time = time.time()
    opti_model.optimize()
    end_time = time.time()
    print(
        "SCIP status:",
        opti_model.getStatus()
    )
    print(
        "Optimization time:",
        end_time - start_time
    )


    # Objective value of the best solution found
    if opti_model.getNSols() > 0:

        print(
            "Objective value:",
            opti_model.getObjVal()
        )

    else:

        print("No feasible solution found.")


    # =========================================================
    # Step 18: Extract SCIP allocation solution
    # =========================================================
    #
    # Convert the selected binary x[p,s] variables back into
    # the same Allocation objects used by the greedy heuristic.
    #
    # This allows both approaches to use exactly the same
    # KPI calculation functions.
    # =========================================================

    scip_allocations = []

    if opti_model.getNSols() > 0:

        best_solution = opti_model.getBestSol()

        for plate_id, slab_id in x:

            value = opti_model.getSolVal(
                best_solution,
                x[plate_id, slab_id]
            )

            # Binary variable selected by SCIP
            if value > 0.5:

                plate = next(
                    plate
                    for plate in plates
                    if plate.plate_id == plate_id
                )

                slab = next(
                    slab
                    for slab in slabs
                    if slab.slab_id == slab_id
                )

                order = plate_to_order[plate_id]

                scip_allocations.append(
                    Allocation(
                        slab,
                        plate,
                        order
                    )
                )


    print(
        "SCIP allocations:",
        len(scip_allocations)
    )


    # =========================================================
    # Step: Identify unfulfilled orders
    # =========================================================

    scip_allocated_plate_ids = {
        allocation.plate.plate_id
        for allocation in scip_allocations
    }

    scip_unallocated_orders = {}

    for order in orders:

        missing_plates = [
            plate.plate_id
            for plate in order.plates
            if plate.plate_id not in scip_allocated_plate_ids
        ]

        if missing_plates:

            scip_unallocated_orders[order.order_id] = (
                f"Could not allocate plates: {missing_plates}"
            )


    print(
        "Unallocated SCIP orders:",
        scip_unallocated_orders
    )


    return scip_allocations, scip_unallocated_orders, log_handler.progress_data



class LogEventHandler(Eventhdlr):
    def __init__(self):
        self.progress_data = []

    def eventinit(self):
        self.model.catchEvent(SCIP_EVENTTYPE.NODESOLVED, self)

    def eventexit(self):
        self.model.dropEvent(SCIP_EVENTTYPE.NODESOLVED, self)

    def eventexec(self, event):
        node = event.getNode()
        if node:
            node_id = node.getNumber()
            obj_val = round(self.model.getObjVal(),3)
            time_elapsed = self.model.getSolvingTime()
            
            '''
            if self.model.getNSols() > 0:
                best_sol = round(self.model.getBestSol())
                self.progress_data.append((node_id, obj_val, time_elapsed, best_sol))
                 # Print progress information
                print(f"Node {node_id}, Objective Value {obj_val}, Time Elapsed {time_elapsed}, Best sol: {best_sol}")
            else:
            '''
            self.progress_data.append((node_id, obj_val, time_elapsed))
             # Print progress information
            print(f"Node {node_id}, Objective Value {obj_val}, Time Elapsed {time_elapsed}")
                