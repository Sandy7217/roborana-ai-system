# ================================================================
# 🧩 inventory_data_tools.py — RoboRana Inventory Intelligence v2.8.1-Stable+
# Fully compatible with 'Inventory' column + hybrid filename auto-locator
# ================================================================

import os
import re
import pandas as pd
from datetime import datetime


# ------------------------------------------------------------
# 📍 Locate Inventory Directory Automatically
# ------------------------------------------------------------
def find_inventory_dir():
    """Locate the DATA/INVENTORY/FINAL directory robustly."""
    anchors = [os.path.dirname(__file__), os.getcwd()]
    max_up = 6
    candidates = []

    for anchor in anchors:
        p = anchor
        for _ in range(max_up + 1):
            candidate = os.path.join(p, "DATA", "INVENTORY", "FINAL")
            candidates.append(candidate)
            p = os.path.dirname(p)

    extra = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../DATA/INVENTORY/FINAL")),
        os.path.abspath(os.path.join(os.getcwd(), "DATA", "INVENTORY", "FINAL")),
    ]
    candidates.extend(extra)

    seen, final = set(), []
    for c in candidates:
        c_abs = os.path.abspath(c)
        if c_abs not in seen:
            seen.add(c_abs)
            final.append(c_abs)

    for c in final:
        if os.path.isdir(c):
            print(f"🔎 Resolved INVENTORY_DIR: {c}")
            return c

    print("⚠️ Could not find DATA/INVENTORY/FINAL. Tried these paths:")
    for c in final:
        print("  -", c)
    return None


INVENTORY_DIR = find_inventory_dir()
print(f"🔍 inventory_data_tools resolved INVENTORY_DIR = {INVENTORY_DIR}")


# ------------------------------------------------------------
# 🗓️ Date Extraction from Query
# ------------------------------------------------------------
def _extract_date_from_query(query: str):
    """Extract date (e.g. '30 oct', '31/10/2025', etc.) from user query."""
    if not query:
        return None
    query = query.lower()
    patterns = [
        r"(\d{1,2})[\/\-\s]?([a-z]{3,9})[\/\-\s]?(\d{2,4})?",
        r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            try:
                day = int(match.group(1))
                month_part = match.group(2)
                year = match.group(3) if len(match.groups()) > 2 else None
                if month_part.isalpha():
                    month = datetime.strptime(month_part[:3], "%b").month
                else:
                    month = int(month_part)
                year = int(year) if year else datetime.now().year
                return datetime(year, month, day)
            except Exception:
                continue
    return None


# ------------------------------------------------------------
# 🗂️ Snapshot File Discovery
# ------------------------------------------------------------
def _get_snapshot_files():
    """Return list of valid inventory CSV snapshots with extracted dates."""
    if not INVENTORY_DIR or not os.path.isdir(INVENTORY_DIR):
        print(f"⚠️ INVENTORY_DIR not found or invalid: {INVENTORY_DIR}")
        return []

    files = [f for f in os.listdir(INVENTORY_DIR) if f.lower().endswith(".csv")]
    if not files:
        print(f"⚠️ No CSV files found in {INVENTORY_DIR}")
        return []

    file_info = []
    for f in files:
        full_path = os.path.join(INVENTORY_DIR, f)
        parsed = None

        patterns = [
            r"(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})",
            r"(\d{1,2})\s*([A-Za-z]{3,9})\s*(\d{4})",
            r"(\d{1,2})[_\-\s]*([A-Za-z]{3,9})[_\-\s]*(\d{4})",
            r"([A-Za-z]{3,9})[_\-\s]*(\d{1,2})[_\-\s]*(\d{4})",
        ]

        for p in patterns:
            m = re.search(p, f)
            if m:
                try:
                    if m.group(1).isalpha():
                        mth = datetime.strptime(m.group(1)[:3], "%b").month
                        day = int(m.group(2))
                        year = int(m.group(3))
                    elif m.group(2).isalpha():
                        day = int(m.group(1))
                        mth = datetime.strptime(m.group(2)[:3], "%b").month
                        year = int(m.group(3))
                    else:
                        y, mth, day = map(int, m.groups())
                        year = y
                    parsed = datetime(year, mth, day)
                    break
                except Exception:
                    continue

        if parsed:
            mtime = os.path.getmtime(full_path)
            file_info.append((parsed.date(), f, mtime))
        else:
            print(f"⚠️ Could not parse date from filename: {f}")

    if not file_info:
        print(f"⚠️ No valid snapshots parsed from directory {INVENTORY_DIR}.")
        print(f"   Directory contains: {files}")
        return []

    latest_by_date = {}
    for date_, fname, mtime in file_info:
        if date_ not in latest_by_date or mtime > latest_by_date[date_][1]:
            latest_by_date[date_] = (fname, mtime)

    sorted_files = sorted(
        [(datetime.combine(d, datetime.min.time()), v[0]) for d, v in latest_by_date.items()],
        key=lambda x: x[0],
    )

    print(f"📁 Found {len(sorted_files)} valid inventory snapshots:")
    for dt, name in sorted_files:
        print(f"   - {name} ({dt.date()})")

    return sorted_files


# ------------------------------------------------------------
# 📦 Load Inventory File (By Date or Latest)
# ------------------------------------------------------------
def get_inventory_file_for_query(query: str):
    """Return appropriate inventory CSV path based on query date (or latest available)."""
    snapshot_files = _get_snapshot_files()
    if not snapshot_files:
        raise FileNotFoundError(
            f"❌ No inventory snapshots found in FINAL directory. Directory contains: {os.listdir(INVENTORY_DIR)}"
        )

    query_date = _extract_date_from_query(query)
    if query_date:
        candidates = [s for s in snapshot_files if s[0] <= query_date]
        if candidates:
            chosen = max(candidates, key=lambda x: x[0])
            print(f"📁 Using snapshot closest to {query_date.date()}: {chosen[1]}")
            return os.path.join(INVENTORY_DIR, chosen[1])
        else:
            print(f"⚠️ No snapshot older than {query_date.date()} found — using oldest available: {snapshot_files[0][1]}")
            return os.path.join(INVENTORY_DIR, snapshot_files[0][1])
    else:
        chosen = snapshot_files[-1][1]
        print(f"📁 Using latest inventory snapshot: {chosen}")
        return os.path.join(INVENTORY_DIR, chosen)


# ------------------------------------------------------------
# 📊 Load & Normalize Inventory Data
# ------------------------------------------------------------
def load_inventory_data(user_query: str = ""):
    """Load appropriate inventory CSV (latest or by date in query)."""
    file_path = get_inventory_file_for_query(user_query)
    df = pd.read_csv(file_path, low_memory=False, on_bad_lines="skip", quoting=1)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Broadened detection (includes 'inventory' column)
    qty_keywords = ["inventory", "qty", "quantity", "stock", "avail", "closing", "balance"]
    qty_cols = [c for c in df.columns if any(k in c for k in qty_keywords)]

    for col in qty_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "inventory" in df.columns:
        df["total_quantity"] = df["inventory"]
        print("📊 Using 'inventory' column for total quantity.")
    elif qty_cols:
        valid_qty_cols = [c for c in qty_cols if not any(x in c for x in ["transfer", "adjust", "return"])]
        if not valid_qty_cols:
            valid_qty_cols = qty_cols
        df["total_quantity"] = df[valid_qty_cols].sum(axis=1)
        print(f"📊 Quantity columns detected: {valid_qty_cols}")
    else:
        print("⚠️ No quantity-related columns found.")
        df["total_quantity"] = 0

    print(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns from {os.path.basename(file_path)}")
    return df


# ------------------------------------------------------------
# 🧠 Interpret Inventory Query — for Agent Integration
# ------------------------------------------------------------
def interpret_inventory_query(query: str, inventory_df=None):
    """Interpret user queries related to inventory (low stock, overstock, etc.)."""
    try:
        if inventory_df is None:
            inventory_df = load_inventory_data(query)

        total_skus = inventory_df["sku"].nunique() if "sku" in inventory_df.columns else len(inventory_df)
        total_qty = inventory_df["total_quantity"].sum()

        low_stock = inventory_df[inventory_df["total_quantity"] <= 5]
        over_stock = inventory_df[inventory_df["total_quantity"] >= 100]

        summary = {
            "total_skus": int(total_skus),
            "total_qty": int(total_qty),
            "low_stock_count": len(low_stock),
            "over_stock_count": len(over_stock),
            "status": "ok",
        }

        print("\n📊 Inventory Summary:")
        print(f"   • Total SKUs: {summary['total_skus']}")
        print(f"   • Total Quantity: {summary['total_qty']}")
        print(f"   • Low Stock Items: {summary['low_stock_count']}")
        print(f"   • Overstocked Items: {summary['over_stock_count']}")
        print("✅ interpret_inventory_query executed successfully.\n")

        return summary

    except Exception as e:
        print(f"⚠️ interpret_inventory_query() error: {e}")
        return {"error": str(e), "status": "failed"}
