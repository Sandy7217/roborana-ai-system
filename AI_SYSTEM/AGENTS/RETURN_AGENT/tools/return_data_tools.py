"""
AI_SYSTEM/AGENTS/RETURN_AGENT/tools/return_data_tools.py
------------------------------------------------------------
Advanced Return Data Tool — v2.0 (Style + Dynamic Path Integrated)
"""

import os
import pandas as pd
from datetime import datetime, timedelta

from AI_SYSTEM.CORE_UTILS.style_logic import add_style_column


# -------------------------------------------------------------
# 📁 Dynamic Returns Folder Finder
# -------------------------------------------------------------
def find_returns_base() -> str:
    """
    Dynamically locate DATA/RETURNS folder by walking upward.
    """
    anchors = [os.path.dirname(__file__), os.getcwd()]

    for anchor in anchors:
        p = anchor
        for _ in range(6):
            candidate = os.path.join(p, "DATA", "RETURNS")
            if os.path.isdir(candidate):
                print(f"📁 Found returns base folder: {candidate}")
                return candidate
            p = os.path.dirname(p)

    raise FileNotFoundError("❌ Could not locate DATA/RETURNS folder.")


def get_return_file() -> str:
    """
    Priority:
    1️⃣ Use Return_Master_Updated.csv if exists  
    2️⃣ Otherwise fallback to latest CSV in RETURNS folder
    """
    base = find_returns_base()

    master_path = os.path.join(base, "Master", "Return_Master_Updated.csv")

    if os.path.exists(master_path):
        print(f"📁 Using Return Master File: {os.path.basename(master_path)}")
        return master_path

    # Fallback to latest file
    all_files = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.lower().endswith(".csv"):
                all_files.append(os.path.join(root, f))

    if not all_files:
        raise FileNotFoundError("❌ No return files found in DATA/RETURNS.")

    latest = max(all_files, key=os.path.getmtime)
    print(f"📁 Using latest fallback return file: {os.path.basename(latest)}")
    return latest


# -------------------------------------------------------------
# 🧹 Load & Clean Returns Data
# -------------------------------------------------------------
def load_return_data():
    """Load and sanitize Return data with Style-Level Logic."""

    file_path = get_return_file()

    df = pd.read_csv(
        file_path,
        low_memory=False,
        on_bad_lines="skip",
        quoting=1,
        encoding="utf-8"
    )

    # ✅ Normalize headers
    df.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    # ✅ Keep only customer returns
    if "return_type" in df.columns:
        before = len(df)
        df = df[df["return_type"].astype(str).str.lower().str.contains("customer", na=False)]
        after = len(df)
        if before - after > 0:
            print(f"🚫 Filtered out {before - after} non-customer returns")

    # ✅ Detect date column
    date_col = next((c for c in df.columns if "date" in c), None)
    if not date_col:
        raise ValueError("❌ No date column found in Return CSV.")

    df["return_date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["return_date"])

    # ✅ Numeric fields cleaning
    numeric_cols = [c for c in df.columns if any(x in c for x in ["total", "value", "amount", "qty", "price"])]
    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r"[^\d.]", "", regex=True),
            errors="coerce"
        ).fillna(0)

    # ✅ Standardize total value column
    total_col = next((c for c in df.columns if "total" in c or "amount" in c or "value" in c), None)
    if total_col:
        df.rename(columns={total_col: "total_value"}, inplace=True)
    else:
        df["total_value"] = 0

    # ✅ Standardize qty
    if "qty" not in df.columns:
        df["qty"] = 1

    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(1)

    # ✅ Detect and standardize SKU
    sku_col = next((c for c in df.columns if "sku" in c or "product" in c), None)
    if not sku_col:
        raise ValueError("❌ No SKU/Product column found in Return data.")

    df.rename(columns={sku_col: "sku"}, inplace=True)

    # ✅ Add Style Code
    df = add_style_column(df, sku_col="sku")

    print(f"✅ Loaded {len(df)} valid customer return rows")
    print(f"🕒 Date range: {df['return_date'].min()} → {df['return_date'].max()}")
    print(f"🎨 Unique styles: {df['Style Code'].nunique()}")

    return df


# -------------------------------------------------------------
# 📊 Main Query Interpreter
# -------------------------------------------------------------
def interpret_return_query(query: str):
    """Return numeric summary (totals, channels, SKUs, styles)."""

    try:
        df = load_return_data()
    except Exception as e:
        return {"info": f"❌ Error loading return data: {type(e).__name__} — {e}"}

    now = datetime.now()
    q = query.lower().strip()

    # 🕒 Detect timeframe
    if "7" in q and "day" in q:
        start_dt = now - timedelta(days=7)
        period = "last 7 days"
    elif "30" in q and "day" in q:
        start_dt = now - timedelta(days=30)
        period = "last 30 days"
    elif "yesterday" in q:
        start_dt = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
        period = "yesterday"
    elif "today" in q:
        start_dt = now.replace(hour=0, minute=0, second=0)
        period = "today"
    else:
        start_dt = df["return_date"].min()
        period = f"since {start_dt.strftime('%Y-%m-%d')}"

    df = df[(df["return_date"] >= start_dt) & (df["return_date"] <= now)]

    # 🔍 Channel filter
    if "channel_entry" in df.columns:
        for ch in ["ajio", "myntra", "flipkart", "amazon", "nykaa"]:
            if ch in q:
                df = df[df["channel_entry"].astype(str).str.lower().str.contains(ch)]

    if df.empty:
        return {"info": f"No returns found for {period}."}

    # 📊 Core metrics
    total_value = df["total_value"].sum()
    total_qty = df["qty"].sum()
    total_orders = len(df)
    avg_value = round(total_value / total_orders, 2) if total_orders else 0

    # 💰 Channel Summary
    channel_summary = {}
    if "channel_entry" in df.columns:
        channel_summary = df.groupby("channel_entry")["total_value"].sum().sort_values(ascending=False).to_dict()

    # 🏷️ Top SKUs
    top_skus = (
        df.groupby("sku")
        .agg(total_value=("total_value", "sum"), qty=("qty", "sum"))
        .sort_values("total_value", ascending=False)
        .head(10)
        .reset_index()
        .to_dict(orient="records")
    )

    # 🎨 Top Styles
    top_styles = (
        df.groupby("Style Code")
        .agg(total_value=("total_value", "sum"), qty=("qty", "sum"))
        .sort_values("total_value", ascending=False)
        .head(10)
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "period": period,
        "total_orders": int(total_orders),
        "total_qty": int(total_qty),
        "total_value": round(total_value, 2),
        "avg_value": avg_value,
        "unique_styles": int(df["Style Code"].nunique()),
        "channel_summary": channel_summary,
        "top_skus": top_skus,
        "top_styles": top_styles,
    }


# -------------------------------------------------------------
# 🧪 Style-Level Summary Helper
# -------------------------------------------------------------
def get_style_level_return_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate return performance by Style Code."""
    return df.groupby("Style Code").agg(
        total_return_qty=("qty", "sum"),
        total_return_value=("total_value", "sum"),
        total_orders=("sku", "count")
    ).sort_values("total_return_value", ascending=False).reset_index()


# -------------------------------------------------------------
# 🧪 Local Test
# -------------------------------------------------------------
if __name__ == "__main__":
    result = interpret_return_query("myntra returns last 7 days")
    print("\n📊 Return Summary:")
    for k, v in result.items():
        print(f"{k}: {v}")
