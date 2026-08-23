

class Slab:

    def __init__(
        self,
        slab_id,
        length,
        grade,
        quality,
        supplier,
        surface_class,
        status="Available",
        available_from=None
    ):
        self.slab_id = slab_id
        self.length = length
        self.grade = grade
        self.quality = quality
        self.supplier = supplier
        self.surface_class = surface_class
        self.status = status
        available_from = available_from


class Plate:

    def __init__(
        self,
        plate_id,
        order_id,
        length,
        width,
        thickness,
        grade,
        quality
    ):
        self.plate_id = plate_id
        self.order_id = order_id
        self.length = length
        self.width = width
        self.thickness = thickness
        self.grade = grade
        self.quality = quality

class Order:

    def __init__(
        self,
        order_id,
        customer,
        plates,
        allowed_suppliers=None,
        required_surface_class=None,
        require_full_fulfilment=True
    ):
        self.order_id = order_id
        self.customer = customer
        self.plates = plates
        self.allowed_suppliers = allowed_suppliers
        self.required_surface_class = required_surface_class
        self.require_full_fulfilment = require_full_fulfilment


def is_compatible(slab, plate, order):

    # A slab-plate combination is feasible only when:
    #   1. Steel grade is compatible.
    #   2. Quality specification is compatible.
    #   3. Customer-specific supplier restrictions are met.
    #   4. Customer-specific surface requirements are met.
    #   5. The slab is currently available.


    # Steel grade
    if slab.grade != plate.grade:
        return False, "Steel grade mismatch"

    # Quality specification
    if slab.quality != plate.quality:
        return False, "Quality specification mismatch"

    # Customer-specific supplier restriction
    if order.allowed_suppliers is not None:
        if slab.supplier not in order.allowed_suppliers:
            return False, "Supplier not permitted for customer"

    # Customer-specific surface restriction
    if order.required_surface_class is not None:
        if slab.surface_class != order.required_surface_class:
            return False, "Surface class does not meet customer requirement"

    # Inventory status
    if slab.status != "Available":
        return False, f"Slab is {slab.status}"

    return True, "Compatible"


SLAB_CROSS_SECTION_CONSTANT = 0.04  

def calculate_required_length(slab, plate):

    if slab.grade != plate.grade:
        raise ValueError("Incompatible slab grade")

    if slab.grade == "G1":
        yield_factor = 0.94

    elif slab.grade == "G2":
        yield_factor = 0.88

    else:
        raise ValueError(
            f"Unsupported slab grade: {slab.grade}"
        )

    plate_volume = (
        plate.length *
        plate.width *
        plate.thickness
    )

    required_length = (
        plate_volume /
        (SLAB_CROSS_SECTION_CONSTANT * yield_factor)
    )

    return required_length


class Allocation:

    def __init__(self, slab, plate, order):

        compatible, reason = is_compatible(
            slab,
            plate,
            order
        )

        if not compatible:
            raise ValueError(
                f"Slab {slab.slab_id} is not compatible "
                f"with Plate {plate.plate_id}: {reason}"
            )

        self.slab = slab
        self.plate = plate
        self.order = order

        self.required_length = calculate_required_length(
            slab,
            plate
        )


def calculate_material_consumption(allocations):
    """
    Calculate total slab length consumed by the allocations.
    """
    return sum(
        allocation.required_length
        for allocation in allocations
    )



def calculate_yield_loss(allocations):
    """
    Calculate total unused length on slabs that are actually used.
    """

    consumption_by_slab = {}

    for allocation in allocations:

        slab_id = allocation.slab.slab_id

        consumption_by_slab[slab_id] = (
            consumption_by_slab.get(slab_id, 0)
            + allocation.required_length
        )

    total_yield_loss = 0.0

    for slab_id, used_length in consumption_by_slab.items():

        slab = next(
            allocation.slab
            for allocation in allocations
            if allocation.slab.slab_id == slab_id
        )

        if used_length > slab.length:
            raise ValueError(
                f"Capacity exceeded for slab {slab_id}: "
                f"required {used_length:.2f} m, "
                f"available {slab.length:.2f} m"
            )

        total_yield_loss += (
            slab.length - used_length
        )

    return total_yield_loss


def calculate_slab_utilisation(slabs, allocations):
    """
    Calculate utilisation of slabs that are used in the allocation.

    Returns utilisation as a percentage.
    """

    consumption_by_slab = {}

    for allocation in allocations:

        slab_id = allocation.slab.slab_id

        consumption_by_slab[slab_id] = (
            consumption_by_slab.get(slab_id, 0.0)
            + allocation.required_length
        )

    total_capacity = 0.0
    total_consumption = 0.0

    for slab in slabs:

        if slab.slab_id in consumption_by_slab:

            total_capacity += slab.length
            total_consumption += (
                consumption_by_slab[slab.slab_id]
            )

    if total_capacity == 0:
        return 0.0

    return (
        total_consumption /
        total_capacity
    ) * 100


def get_slab_consumption(allocations):
    """
    Return total allocated length for each slab.
    """

    consumption = {}

    for allocation in allocations:

        slab_id = allocation.slab.slab_id

        consumption[slab_id] = (
            consumption.get(slab_id, 0.0)
            + allocation.required_length
        )

    return consumption


def calculate_kpis(
    slabs,
    orders,
    allocations,
    unallocated_orders
):

    material_consumption = calculate_material_consumption(
        allocations
    )

    yield_loss = calculate_yield_loss(
        allocations
    )

    utilisation = calculate_slab_utilisation(
        slabs,
        allocations
    )


    return {
        "material_consumption": material_consumption,
        "yield_loss": yield_loss,
        "slab_utilisation": utilisation,
        "order_fulfilment": (len(orders) - len(unallocated_orders)) / len(orders) if len(orders) > 0 else 0.0
    }


