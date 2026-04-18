# ======================================================
# RoboRana AI — Master Column Schema (Permanent Mapping)
# Author: Sandeep Rana
# Purpose: Single Source of Truth for all data columns
# ======================================================

COLUMN_MAP = {
    "sales": {
        "sku": "Item SKU Code",
        "date": "Order Date as dd/mm/yyyy hh:MM:ss",
        "quantity": None,        # 1 row = 1 quantity
        "value": "Selling Price" # ✅ Use Selling Price only for value calculations
    },
    "returns": {
        "sku": "Product SKU Code",
        "date": "Date",
        "quantity": "Qty",
        "value": "Total"         # ✅ Return ₹ value column
    },
    "inventory": {
        "sku": "Item SKU Code",
        "quantity": "Qty"
    }
}

DATE_FORMATS = {
    "sales": "%d/%m/%Y %H:%M:%S",
    "returns": "%d-%m-%Y"
}
