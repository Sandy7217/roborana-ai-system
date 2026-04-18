"""
AI_SYSTEM/AGENTS/SALES_AGENT/tools/sales_data_tools.py
------------------------------------------------------
RoboRana AI — Sales Data Tool v2.17 (SKU + STYLE CRASH FIXED)
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from AI_SYSTEM.CORE_UTILS.style_logic import add_style_column


# =========================================================
# 🛡️ Debug Guardian
# =========================================================
def debug_report(df, tag=""):
    print(f"\n🔍 RoboRana Debug Report [{tag}]")
    print("➡ Shape:", df.shape)
    print("➡ Duplicate columns:", df.columns[df.columns.duplicated()].tolist())
    print("➡ Duplicate index:", df.index.duplicated().sum())

    nulls = df.isna().sum().sort_values(ascending=False).head(8)
    print("➡ Top Null Columns:\n", nulls)

    return df


# =========================================================
# 📍 Locate Sales Folder
# =========================================================
def find_sales_folder():
    anchors = [os.path.dirname(__file__), os.getcwd()]

    for anchor in anchors:
        p = anchor
        for _ in range(6):
            for sub in ["FINAL", "Final", "Master", "master"]:
                candidate = os.path.join(p, "DATA", "SALES", sub)
                if os.path.isdir(candidate):
                    print(f"📁 Found sales folder: {candidate}")
                    return candidate
            p = os.path.dirname(p)

    raise FileNotFoundError("❌ SALES folder not found")


# =========================================================
# 🔍 Latest Sales File
# =========================================================
def get_latest_sales_file():
    folder = find_sales_folder()

    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".csv")]

    if not files:
        raise FileNotFoundError("❌ No Sales CSV found")

    latest = max(files, key=os.path.getmtime)
    print(f"📦 Using latest sales file: {os.path.basename(latest)}")
    return latest


# =========================================================
# 🧩 Safe Date Parser
# =========================================================
def _parse_dates_series(series: pd.Series):
    s = series.astype(str).str.strip().str.replace(r"[\[\]']", "", regex=True)
    parsed = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return pd.to_datetime(parsed, errors="coerce")


# =========================================================
# 🧹 Load & Clean Sales Data
# =========================================================
def load_sales_data():

    file_path = get_latest_sales_file()

    df = pd.read_csv(
        file_path,
        encoding="utf-8",
        low_memory=False,
        on_bad_lines="skip",
        quoting=1
    )

    df = debug_report(df, "RAW LOAD")

    # ✅ Kill duplicate columns
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Normalize names
    df.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in df.columns]

    # Detect columns
    date_col = next((c for c in df.columns if "order" in c and "date" in c), None)
    price_col = next((c for c in df.columns if "selling" in c and "price" in c), None)
    total_col = next((c for c in df.columns if "total" in c and "price" in c), None)
    sku_col = next((c for c in df.columns if "sku" in c), None)

    if not date_col or not (price_col or total_col) or not sku_col:
        raise ValueError("❌ Required columns missing")

    df.rename(columns={
        date_col: "order_date",
        sku_col: "sku",
        price_col or total_col: "selling_price"
    }, inplace=True)

    # ✅ If duplicate sku columns still exist → FIX
    if isinstance(df["sku"], pd.DataFrame):
        df["sku"] = df["sku"].iloc[:, 0]

    # ✅ Dates
    df["order_date"] = _parse_dates_series(df["order_date"])

    before = len(df)
    df = df.dropna(subset=["order_date"])
    print(f"⚠ Dropped {before - len(df)} invalid dates")

    df = df.reset_index(drop=True)

    # ✅ Price cleaning
    df["selling_price"] = (
        df["selling_price"]
        .astype(str)
        .str.replace(r"[^\d.]", "", regex=True)
        .replace("", np.nan)
    )
    df["selling_price"] = pd.to_numeric(df["selling_price"], errors="coerce").fillna(0)

    # ✅ Quantity safety
    if "qty" not in df.columns:
        df["qty"] = 1
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(1)

    # 🎨 Style Safe Injection
    try:
        df = add_style_column(df.copy(), sku_col="sku")
    except Exception as e:
        print(f"⚠️ Style logic crashed: {e}")

        # 🔥 SAFE FALLBACK: now sku is guaranteed to be a Series
        df["Style Code"] = df["sku"].astype(str).str.split("-").str[0]

    # ✅ Remove any duplicate sku created by style logic
    df = df.loc[:, ~df.columns.duplicated()].copy()

    df = debug_report(df, "AFTER CLEANING")

    print(f"✅ Final rows: {len(df)}")
    print(f"🕒 Date range: {df['order_date'].min()} → {df['order_date'].max()}")
    print(f"🎨 Unique styles: {df['Style Code'].nunique()}")

    return df


# =========================================================
# 📊 Query Engine
# =========================================================
def interpret_query(user_query: str):

    try:
        df = load_sales_data()

        now = datetime.now()
        q = user_query.lower()

        if "7" in q:
            start_dt, days = now - timedelta(days=7), 7
        elif "30" in q:
            start_dt, days = now - timedelta(days=30), 30
        else:
            start_dt = df["order_date"].min()
            days = (now - start_dt).days

        end_dt = now

        # ✅ Safe numpy filtering
        dates = df["order_date"].values.astype("datetime64[ns]")
        idx = np.where((dates >= np.datetime64(start_dt)) & (dates <= np.datetime64(end_dt)))[0]

        df_filtered = df.iloc[idx].reset_index(drop=True)

        print(f"🕵️ Filtered {len(df_filtered)} rows")

        total_sales = float((df_filtered["selling_price"] * df_filtered["qty"]).sum())
        total_orders = len(df_filtered)

        return {
            "period": f"Last {days} days",
            "total_sales": round(total_sales, 2),
            "total_orders": int(total_orders),
            "avg_order_value": round(total_sales / total_orders, 2) if total_orders else 0,
            "unique_styles": int(df_filtered["Style Code"].nunique())
        }

    except Exception as e:
        return {
            "status": "CRASH",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }


# =========================================================
# 🧪 Local Test
# =========================================================
if __name__ == "__main__":
    response = interpret_query("sales in last 7 days")
    print("\n🧾 RoboRana Summary:", response)
