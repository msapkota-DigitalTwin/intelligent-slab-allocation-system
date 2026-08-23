#data_loader

import pandas as pd
import json

from models_and_KPIS import Slab, Plate, Order

def slabs_from_records_dict(records):
    #print(type(records))
    #print(records[:2])
    return [
        Slab(
            slab_id=record["slab_id"],
            length=record["length"],
            grade=record["grade"],
            quality=record["quality"],
            supplier=record["supplier"],
            surface_class=record["surface_class"],
            status=record["status"],
            available_from=record["available_from"]
        )
        for record in records
    ]


def orders_from_records_dict(records):

    orders = []

    # Group records by order_id
    orders_by_id = {}

    for record in records:

        order_id = record["order_id"]

        if order_id not in orders_by_id:
            orders_by_id[order_id] = []

        orders_by_id[order_id].append(record)


    # Convert each group into an Order object
    for order_id, order_records in orders_by_id.items():

        first_record = order_records[0]

        # -------------------------------------------------
        # Create Plate objects
        # -------------------------------------------------

        plates = []

        for record in order_records:

            plate = Plate(
                plate_id=record["plate_id"],
                order_id=record["order_id"],
                length=record["length"],
                width=record["width"],
                thickness=record["thickness"],
                grade=record["grade"],
                quality=record["quality"]
            )

            plates.append(plate)


        # -------------------------------------------------
        # Convert supplier restriction
        # -------------------------------------------------

        allowed_suppliers = (
            first_record["allowed_suppliers"]
        )

        if (
            allowed_suppliers is not None
            and not pd.isna(allowed_suppliers)
        ):

            allowed_suppliers = [
                supplier.strip()
                for supplier
                in str(allowed_suppliers).split(",")
            ]

        else:

            allowed_suppliers = None


        # -------------------------------------------------
        # Convert surface requirement
        # -------------------------------------------------

        required_surface_class = (
            first_record["required_surface_class"]
        )

        if pd.isna(required_surface_class):
            required_surface_class = None


        # -------------------------------------------------
        # Create Order object
        # -------------------------------------------------

        order = Order(
            order_id=order_id,
            customer=first_record["customer"],
            plates=plates,
            allowed_suppliers=allowed_suppliers,
            required_surface_class=required_surface_class,
            require_full_fulfilment=bool(
                first_record[
                    "require_full_fulfilment"
                ]
            )
        )

        orders.append(order)

    return orders


def load_input_data(
    slab_path,
    order_path,
    file_format="excel"
):
    if file_format == "excel":
        df_slab = pd.read_excel(slab_path)
        records_slab = df_slab.to_dict(orient="records")
        slabs = slabs_from_records_dict(records_slab)

        df_order = pd.read_excel(order_path)
        records_order = df_order.to_dict(orient="records")
        orders = orders_from_records_dict(records_order)


    elif file_format == "json":
        with open(slab_path, "r") as slab_file:
            records_slab = json.load(slab_file)
            slabs = slabs_from_records_dict(records_slab["slabs"])

        with open(order_path, "r") as order_file:
            records_order = json.load(order_file)
            orders = orders_from_records_dict(records_order["orders"])

    else:
        raise ValueError(
            "file_format must be 'excel' or 'json'"
        )

    return slabs, orders