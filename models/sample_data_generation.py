import os
import json
import pandas as pd


# =========================================================
# Output directory
# =========================================================

OUTPUT_DIR = r"D:\Projects\slab-allocation-system\intelligent-slab-allocation-system\data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# 1. Slab inventory
# =========================================================

slabs = [
    {
        "slab_id": "S001",
        "length": 10.0,
        "grade": "G1",
        "quality": "Q1",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S002",
        "length": 12.0,
        "grade": "G1",
        "quality": "Q1",
        "supplier": "SUP2",
        "surface_class": "S2",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S003",
        "length": 9.0,
        "grade": "G1",
        "quality": "Q2",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S004",
        "length": 14.0,
        "grade": "G1",
        "quality": "Q1",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Reserved",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S005",
        "length": 11.0,
        "grade": "G2",
        "quality": "Q1",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S006",
        "length": 13.0,
        "grade": "G2",
        "quality": "Q1",
        "supplier": "SUP2",
        "surface_class": "S2",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S007",
        "length": 9.0,
        "grade": "G2",
        "quality": "Q2",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Available",
        "available_from": "2026-08-22"
    },
    {
        "slab_id": "S008",
        "length": 15.0,
        "grade": "G2",
        "quality": "Q1",
        "supplier": "SUP1",
        "surface_class": "S1",
        "status": "Incoming",
        "available_from": "2026-08-25"
    }
]


# =========================================================
# 2. Orders and plates
# =========================================================

orders = [
    {
        "order_id": "O001",
        "customer": "Customer_A",
        "allowed_suppliers": None,
        "required_surface_class": None,
        "require_full_fulfilment": True,
        "plates": [
            {
                "plate_id": "P001",
                "length": 4.0,
                "width": 2.0,
                "thickness": 0.020,
                "grade": "G1",
                "quality": "Q1"
            },
            {
                "plate_id": "P002",
                "length": 3.5,
                "width": 2.0,
                "thickness": 0.020,
                "grade": "G1",
                "quality": "Q1"
            }
        ]
    },

    {
        "order_id": "O002",
        "customer": "Customer_B",
        "allowed_suppliers": ["SUP1"],
        "required_surface_class": None,
        "require_full_fulfilment": True,
        "plates": [
            {
                "plate_id": "P003",
                "length": 5.0,
                "width": 2.2,
                "thickness": 0.025,
                "grade": "G1",
                "quality": "Q1"
            },
            {
                "plate_id": "P004",
                "length": 3.0,
                "width": 2.2,
                "thickness": 0.025,
                "grade": "G1",
                "quality": "Q1"
            }
        ]
    },

    {
        "order_id": "O003",
        "customer": "Customer_C",
        "allowed_suppliers": None,
        "required_surface_class": "S1",
        "require_full_fulfilment": True,
        "plates": [
            {
                "plate_id": "P005",
                "length": 6.0,
                "width": 2.5,
                "thickness": 0.030,
                "grade": "G2",
                "quality": "Q1"
            },
            {
                "plate_id": "P006",
                "length": 4.0,
                "width": 2.5,
                "thickness": 0.030,
                "grade": "G2",
                "quality": "Q1"
            }
        ]
    },

    {
        "order_id": "O004",
        "customer": "Customer_A",
        "allowed_suppliers": None,
        "required_surface_class": None,
        "require_full_fulfilment": False,
        "plates": [
            {
                "plate_id": "P007",
                "length": 5.5,
                "width": 2.0,
                "thickness": 0.020,
                "grade": "G1",
                "quality": "Q2"
            },
            {
                "plate_id": "P008",
                "length": 3.5,
                "width": 2.0,
                "thickness": 0.020,
                "grade": "G1",
                "quality": "Q2"
            }
        ]
    }
]


# =========================================================
# 3. Generate Excel: Slab inventory
# =========================================================

slabs_df = pd.DataFrame(slabs)

slab_excel_path = os.path.join(
    OUTPUT_DIR,
    "slab_inventory_input.xlsx"
)

slabs_df.to_excel(
    slab_excel_path,
    sheet_name="Slab_Inventory",
    index=False
)


# =========================================================
# 4. Generate Excel: Orders
# =========================================================

order_rows = []

for order in orders:

    for plate in order["plates"]:

        order_rows.append({
            "order_id": order["order_id"],
            "customer": order["customer"],
            "plate_id": plate["plate_id"],
            "length": plate["length"],
            "width": plate["width"],
            "thickness": plate["thickness"],
            "grade": plate["grade"],
            "quality": plate["quality"],
            "allowed_suppliers": (
                ",".join(order["allowed_suppliers"])
                if order["allowed_suppliers"]
                else None
            ),
            "required_surface_class":
                order["required_surface_class"],
            "require_full_fulfilment":
                order["require_full_fulfilment"]
        })


orders_df = pd.DataFrame(order_rows)

orders_excel_path = os.path.join(
    OUTPUT_DIR,
    "orders_input.xlsx"
)

orders_df.to_excel(
    orders_excel_path,
    sheet_name="Orders",
    index=False
)


# =========================================================
# 5. Generate JSON: Slabs
# =========================================================

slabs_json_path = os.path.join(
    OUTPUT_DIR,
    "slabs.json"
)

with open(slabs_json_path, "w") as f:
    json.dump(
        slabs,
        f,
        indent=4
    )


# =========================================================
# 6. Generate JSON: Orders
# =========================================================

orders_json_path = os.path.join(
    OUTPUT_DIR,
    "orders.json"
)

with open(orders_json_path, "w") as f:
    json.dump(
        orders,
        f,
        indent=4
    )


# =========================================================
# 7. Confirmation
# =========================================================

print("Synthetic input data generated successfully.\n")

print(f"Slab inventory Excel : {slab_excel_path}")
print(f"Orders Excel         : {orders_excel_path}")
print(f"Slabs JSON           : {slabs_json_path}")
print(f"Orders JSON          : {orders_json_path}")