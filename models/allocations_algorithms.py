import pandas as pd
from pyscipopt import Model, quicksum, Eventhdlr, SCIP_EVENTTYPE
import time

from models_and_KPIS import Slab, Plate, Order, Allocation
from models_and_KPIS import  is_compatible, calculate_required_length


def greedy_heuristic_allocate(slabs, orders):
    """
    Perform greedy best-fit allocation of slabs to plates.

    Initial feasibility is checked before allocation. Plates
    with no compatible or sufficiently long slab are excluded
    from the allocation process.

    The algorithm processes orders sequentially. All plates
    belonging to an order must be allocated successfully before
    the temporary allocations are committed.

    Returns
    -------
    allocations : list
        Feasible slab-to-plate Allocation objects.

    unallocated_orders : dict
        Orders that could not be fully allocated, together with
        their failure reasons and affected plates.
    """

    allocations = []

    # =========================================================
    # Prepare plate list
    # =========================================================

    plates = [
        plate
        for order in orders
        for plate in order.plates
    ]

    # =========================================================
    # Initial feasibility screening
    # =========================================================
    #
    # This identifies:
    #
    #   1. Plates with no compatible slab
    #   2. Plates for which compatible slabs exist but none
    #      has sufficient original length
    #
    # It also creates:
    #
    #   feasible_pairs
    #   required_lengths
    #
    # which are reused by the Greedy algorithm.
    # =========================================================

    (
        initially_unallocatable,
        feasible_pairs,
        required_lengths
    ) = identify_initial_infeasibility(
        slabs,
        orders,
        plates
    )

    # =========================================================
    # Store slabs by ID for fast lookup
    # =========================================================

    slab_by_id = {
        slab.slab_id: slab
        for slab in slabs
    }

    # =========================================================
    # Store unallocated orders
    # =========================================================

    unallocated_orders = {}

    # =========================================================
    # Process orders sequentially
    # =========================================================

    for order in orders:

        # -----------------------------------------------------
        # Check whether the order contains a plate that failed
        # the initial feasibility screening.
        #
        # Because the current problem assumes full order
        # fulfilment, the complete order must be rejected.
        # -----------------------------------------------------

        initially_failed_plates = [
            plate.plate_id
            for plate in order.plates
            if plate.plate_id in initially_unallocatable
        ]

        if initially_failed_plates:

            unallocated_orders[
                order.order_id
            ] = {
                "reason": "Initial feasibility failure",

                "affected_plates": {
                    plate_id:
                        initially_unallocatable[plate_id]
                    for plate_id in initially_failed_plates
                }
            }

            continue

        # -----------------------------------------------------
        # Pseudo allocations for the current order.
        #
        # These allocations are committed only if every plate
        # in the order can be allocated.
        # -----------------------------------------------------

        allocations_temp = []

        order_failed = False
        failed_plates = []

        # =====================================================
        # Process plates within the order
        # =====================================================

        for plate in order.plates:

            plate_id = plate.plate_id

            feasible_candidates = []

            # -------------------------------------------------
            # Only examine slabs that passed the initial
            # feasibility screening for this plate.
            # -------------------------------------------------

            for slab_id in feasible_pairs[plate_id]:

                slab = slab_by_id[slab_id]

                required_length = required_lengths[
                    plate_id,
                    slab_id
                ]

                # -------------------------------------------------
                # Material already committed to this slab by
                # previously completed orders.
                # -------------------------------------------------

                committed_usage = sum(
                    allocation.required_length
                    for allocation in allocations
                    if allocation.slab.slab_id == slab_id
                )

                # -------------------------------------------------
                # Material temporarily assigned to this slab
                # within the current order.
                # -------------------------------------------------

                temporary_usage = sum(
                    allocation.required_length
                    for allocation in allocations_temp  
                    if allocation.slab.slab_id == slab_id
                )

                used_length = (
                    committed_usage
                    + temporary_usage
                )

                # -------------------------------------------------
                # Remaining slab capacity
                # -------------------------------------------------

                remaining_capacity = (
                    slab.length
                    - used_length
                )

                # -------------------------------------------------
                # Check whether the plate still fits on the
                # remaining slab capacity.
                # -------------------------------------------------

                if required_length <= remaining_capacity:

                    remaining_after_allocation = (
                        remaining_capacity
                        - required_length
                    )

                    feasible_candidates.append(
                        (
                            remaining_after_allocation,
                            slab
                        )
                    )

            # =================================================
            # No slab with sufficient remaining capacity
            # =================================================

            if not feasible_candidates:

                order_failed = True

                failed_plates.append(
                    plate_id
                )

                # Since full order fulfilment is required,
                # stop processing this order.
                break

            # =================================================
            # Best-fit Greedy selection
            # =================================================
            #
            # Select the slab that leaves the smallest amount
            # of unused capacity after allocating this plate.
            # =================================================

            feasible_candidates.sort(
                key=lambda candidate: candidate[0]
            )

            _, selected_slab = (
                feasible_candidates[0]
            )

            allocations_temp.append(
                Allocation(
                    selected_slab,
                    plate,
                    order
                )
            )

        # =====================================================
        # Order could not be fully allocated
        # =====================================================

        if order_failed:

            unallocated_orders[
                order.order_id
            ] = {
                "reason": (
                    "Insufficient available "
                    "slab length"
                ),

                "affected_plates": failed_plates
            }

            # -------------------------------------------------
            # Discard all pseudo allocations belonging to
            # this incomplete order.
            # -------------------------------------------------

            allocations_temp = []

            continue

        # =====================================================
        # Commit complete order
        # =====================================================

        allocations.extend(
            allocations_temp
        )

    # =========================================================
    # Return final result
    # =========================================================

    return (
        allocations,
        unallocated_orders
    )



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
    #opti_model.setIntParam('display/verblevel', 4)
    
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

    (
        initially_unallocatable,
        feasible_pairs,
        required_lengths
    ) = identify_initial_infeasibility(
        slabs,
        orders,
        plates
    )

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

    for plate_id, slab_id in x:

        opti_model.addCons(
            x[plate_id, slab_id] <= y[slab_id],
            name=f"Link_{plate_id}_{slab_id}"
            )


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
        -yield_loss_weight * yield_loss_ratio
    )

    opti_model.setObjective(
        objective,
        #total_yield_loss,
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

    #scip_allocated_plate_ids = {
    #    allocation.plate.plate_id
    #    for allocation in scip_allocations
    #}

    scip_unallocated_orders = identify_post_allocation_infeasibility(
        orders,
        initially_unallocatable,
        scip_allocations
    )


    return scip_allocations, scip_unallocated_orders



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



def identify_initial_infeasibility(
    slabs,
    orders,
    plates
):
    """
    Identify plates that have no feasible slab before
    running the allocation algorithm.
    """

    initially_unallocatable = {}
    feasible_pairs = {}
    required_lengths = {}

    plate_to_order = {
        plate.plate_id: order
        for order in orders
        for plate in order.plates
    }

    for plate in plates:

        plate_id = plate.plate_id
        order = plate_to_order[plate_id]

        feasible_pairs[plate_id] = []

        has_compatible_slab = False

        for slab in slabs:

            compatible, _ = is_compatible(
                slab,
                plate,
                order
            )

            if not compatible:
                continue

            has_compatible_slab = True

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
            ].append(
                slab.slab_id
            )

        if not has_compatible_slab:

            initially_unallocatable[plate_id] = (
                "No compatible slab"
            )

        elif not feasible_pairs[plate_id]:

            initially_unallocatable[plate_id] = (
                "Insufficient slab length"
            )

    return (
        initially_unallocatable,
        feasible_pairs,
        required_lengths
    )

def identify_post_allocation_infeasibility(
    orders,
    initially_unallocatable,
    allocations
):
    """
    Identify orders that could not be fully fulfilled after
    the allocation algorithm.

    Initial feasibility failures are retained with their
    plate-level reasons.

    Plates that were initially feasible but remained
    unallocated after the algorithm are classified as having
    insufficient available slab length.

    Because full order fulfilment is required, an order is
    considered unallocated if one or more of its plates
    remain unallocated.

    Returns
    -------
    unallocated_orders : dict

        Example:

        {
            "O004": {
                "reason": "No compatible slab",
                "affected_plates": ["P013"]
            },

            "O005": {
                "reason": "Insufficient available slab length",
                "affected_plates": ["P017"]
            }
        }
    """

    # =========================================================
    # Identify successfully allocated plates
    # =========================================================

    allocated_plate_ids = {
        allocation.plate.plate_id
        for allocation in allocations
    }

    # =========================================================
    # Identify all plates that remain unallocated
    # =========================================================

    unallocated_plate_reasons = dict(
        initially_unallocatable
    )

    for order in orders:

        for plate in order.plates:

            plate_id = plate.plate_id

            # Already allocated -> nothing to report
            if plate_id in allocated_plate_ids:
                continue

            # Already identified during initial feasibility
            if plate_id in initially_unallocatable:
                continue

            # Initially feasible, but not allocated
            unallocated_plate_reasons[plate_id] = (
                "Insufficient available slab length"
            )

    # =========================================================
    # Convert plate-level information to order-level output
    # =========================================================

    unallocated_orders = {}

    for order in orders:

        affected_plates = []

        plate_reasons = []

        for plate in order.plates:

            plate_id = plate.plate_id

            if plate_id in unallocated_plate_reasons:

                affected_plates.append(
                    plate_id
                )

                plate_reasons.append(
                    unallocated_plate_reasons[plate_id]
                )

        # -----------------------------------------------------
        # If at least one plate is unallocated, the whole
        # order is considered unallocated.
        # -----------------------------------------------------

        if affected_plates:

            unique_reasons = set(
                plate_reasons
            )

            if len(unique_reasons) == 1:

                reason = next(
                    iter(unique_reasons)
                )

            else:

                reason = (
                    "Multiple feasibility issues"
                )

            unallocated_orders[
                order.order_id
            ] = {
                "reason": reason,
                "affected_plates": affected_plates
            }

    return unallocated_orders