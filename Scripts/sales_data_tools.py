# Scripts/diagnostic_sales_test.py
# ---------------------------------------------------
# 🤖 FULL SALES MASTER VALIDATION DIAGNOSTIC
# Purpose: Validate Sales_Master.csv for AI agent readiness
# ---------------------------------------------------

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# ✅ Path to your Sales Master CSV
file_path = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES\Master\Sales_Master.csv"

print("🔍 Step 1: Loading CSV...")
if not os.path.exists(file_path):
    raise FileNotFoundError(f"❌ File not found at: {file_path}")

df = pd.read_csv(file_path, low_memory=False)
print("✅ CSV loaded successfully.")
print("📄 Columns found:", list(df.columns))

# --- Normalize column names ---
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
print("✅ Normalized columns:", list(df.columns))

# --- Detect order date column ---
order_date_col = next((c for c in df.columns if "order" in c and "date" in c), None)
if not order_date_col:
    raise ValueError("❌ No 'order date' column found!")

print(f"🕓 Detected order date column: {order_date_col}")

# --- Parse dates ---
df[order_date_col] = pd.to_datetime(df[order_date_col], errors="coerce", dayfirst=True)
invalid_dates = df[order_date_col].isna().sum()
if invalid_dates > 0:
    print(f"⚠️ Dropped {invalid_dates} invalid date rows")
    df = df.dropna(subset=[order_date_col])

print(f"✅ Parsed order dates successfully ({len(df)} valid rows)")

# --- Detect price column ---
price_col = next((c for c in df.columns if "sell" in c and "price" in c), None)
if not price_col:
    raise ValueError("❌ Selling price column not found!")

df[price_col] = pd.to_numeric(df[price_col], errors="coerce").fillna(0)
print(f"✅ Selling price column detected: {price_col}")

# --- Quick test summary for last 7 days ---
now = datetime.now()
start_dt = now - timedelta(days=7)
mask = (df[order_date_col] >= start_dt) & (df[order_date_col] <= now)
df_filtered = df.loc[mask]

total_sales = df_filtered[price_col].sum()
total_orders = len(df_filtered)
avg_order_value = total_sales / total_orders if total_orders else 0

print(f"\n🧾 Sales summary for last 7 days:")
print(f"   Total Sales: ₹{total_sales:,.2f}")
print(f"   Total Orders: {total_orders}")
print(f"   Avg Order Value: ₹{avg_order_value:,.2f}")
print("\n✅ Full diagnostic completed successfully.")
