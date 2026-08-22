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


'''
import os
import json
import random
import pandas as pd


# =========================================================
# Configuration
# =========================================================

random.seed(42)

num_orders = 15
num_plates = 50
num_slabs = 20

# Constant effective slab cross-sectional area.
# This is a prototype assumption used by the
# volume-based required-length calculation.
SLAB_CROSS_SECTION = 0.04  # m²

grades = ["G1", "G2"]
qualities = ["Q1", "Q2"]
surface_classes = ["S1", "S2"]
suppliers = ["SUP1", "SUP2", "SUP3"]

dataset_suffix = f"s{num_slabs}_p{num_plates}"


# =========================================================
# 1. Generate slab inventory
# =========================================================

slabs = []

for i in range(num_slabs):

    slab = {
        "slab_id": f"S{i + 1:03d}",
        "length": random.choice(
            [8, 9, 10, 11, 12, 13, 14, 15, 16]
        ),
        "grade": random.choice(grades),
        "quality": random.choice(qualities),
        "supplier": random.choice(suppliers),
        "surface_class": random.choice(surface_classes),
        "status": "Available",
        "available_from": "2026-08-22"
    }

    slabs.append(slab)


# ---------------------------------------------------------
# Add inventory restrictions
# ---------------------------------------------------------

# Two reserved slabs
for slab in slabs[16:18]:
    slab["status"] = "Reserved"


# Two incoming slabs
for slab in slabs[18:20]:
    slab["status"] = "Incoming"
    slab["available_from"] = "2026-08-25"


# =========================================================
# 2. Generate orders
# =========================================================

orders = []


# ---------------------------------------------------------
# Distribute 50 plates across 15 orders
# Each order starts with 3 plates.
# Remaining plates are distributed so that no order
# contains more than 5 plates.
# ---------------------------------------------------------

plate_counts = [3] * num_orders

remaining = num_plates - sum(plate_counts)

while remaining > 0:

    index = random.randrange(num_orders)

    if plate_counts[index] < 5:
        plate_counts[index] += 1
        remaining -= 1


plate_counter = 1


# =========================================================
# Generate individual orders
# =========================================================

for order_number in range(1, num_orders + 1):

    order_id = f"O{order_number:03d}"

    customer = (
        f"Customer_"
        f"{chr(64 + ((order_number - 1) % 5) + 1)}"
    )

    # Some customers have supplier restrictions
    if order_number % 4 == 0:

        allowed_suppliers = [
            random.choice(suppliers)
        ]

    else:

        allowed_suppliers = None


    # Some customers have surface requirements
    if order_number % 5 == 0:

        required_surface_class = random.choice(
            surface_classes
        )

    else:

        required_surface_class = None


    # Keep material grade consistent within an order
    order_grade = random.choice(grades)

    order_quality = random.choice(qualities)

    plates = []


    # -----------------------------------------------------
    # Generate plates belonging to this order
    # -----------------------------------------------------

    for _ in range(
        plate_counts[order_number - 1]
    ):

        plate = {

            "plate_id": f"P{plate_counter:03d}",

            # Plate length
            "length": round(
                random.uniform(2.0, 7.0),
                1
            ),

            # Plate width
            "width": random.choice(
                [1.8, 2.0, 2.2, 2.5]
            ),

            # Plate thickness
            "thickness": random.choice(
                [0.020, 0.025, 0.030]
            ),

            "grade": order_grade,

            "quality": order_quality
        }

        plates.append(plate)

        plate_counter += 1


    # -----------------------------------------------------
    # Create order
    # -----------------------------------------------------

    orders.append(
        {
            "order_id": order_id,
            "customer": customer,
            "allowed_suppliers": allowed_suppliers,
            "required_surface_class":
                required_surface_class,

            # For our prototype we assume complete
            # order fulfilment is required.
            "require_full_fulfilment": True,

            "plates": plates
        }
    )


# =========================================================
# 3. Save slab inventory to Excel
# =========================================================

slab_df = pd.DataFrame(slabs)

slab_excel_path = os.path.join(
    data_dir,
    f"slab_inventory_input_{dataset_suffix}.xlsx"
)

slab_df.to_excel(
    slab_excel_path,
    sheet_name="Slab_Inventory",
    index=False
)


# =========================================================
# 4. Save orders to Excel
# =========================================================

order_rows = []

for order in orders:

    for plate in order["plates"]:

        order_rows.append(
            {
                "order_id": order["order_id"],
                "customer": order["customer"],
                "plate_id": plate["plate_id"],
                "length": plate["length"],
                "width": plate["width"],
                "thickness": plate["thickness"],
                "grade": plate["grade"],
                "quality": plate["quality"],

                "allowed_suppliers": (
                    ",".join(
                        order["allowed_suppliers"]
                    )
                    if order["allowed_suppliers"]
                    else None
                ),

                "required_surface_class":
                    order["required_surface_class"],

                "require_full_fulfilment":
                    order["require_full_fulfilment"]
            }
        )


orders_df = pd.DataFrame(order_rows)

orders_excel_path = os.path.join(
    data_dir,
    f"orders_input_{dataset_suffix}.xlsx"
)

orders_df.to_excel(
    orders_excel_path,
    sheet_name="Orders",
    index=False
)


# =========================================================
# 5. Save slabs to JSON
# =========================================================

slabs_json_path = os.path.join(
    data_dir,
    f"slabs_{dataset_suffix}.json"
)

with open(slabs_json_path, "w") as f:

    json.dump(
        slabs,
        f,
        indent=4
    )


# =========================================================
# 6. Save orders to JSON
# =========================================================

orders_json_path = os.path.join(
    data_dir,
    f"orders_{dataset_suffix}.json"
)

with open(orders_json_path, "w") as f:

    json.dump(
        orders,
        f,
        indent=4
    )


# =========================================================
# 7. Summary
# =========================================================

print("Synthetic dataset generated successfully.\n")

print(f"Slabs generated  : {len(slabs)}")
print(f"Orders generated : {len(orders)}")
print(
    f"Plates generated : "
    f"{sum(len(order['plates']) for order in orders)}"
)

print("\nSlab inventory status:")
print(
    slab_df["status"].value_counts()
)

print("\nPlates per order:")
print(
    orders_df.groupby("order_id").size()
)

print("\nFiles created:")

print(
    os.path.basename(slabs_json_path)
)

print(
    os.path.basename(orders_json_path)
)

print(
    os.path.basename(slab_excel_path)
)

print(
    os.path.basename(orders_excel_path)
)
'''