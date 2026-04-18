# Scripts/diagnostic_sales_test_basic.py
# ---------------------------------------------------
# 🔍 BASIC SALES MASTER DIAGNOSTIC
# Purpose: Verify Sales_Master.csv structure, date parsing,
# and grouping works before running agent scripts.
# ---------------------------------------------------

import pandas as pd
import traceback

# 🔧 Path to your Sales Master file
file_path = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES\Master\Sales_Master.csv"

print("🔍 Step 1: Loading CSV...")
df = pd.read_csv(file_path, low_memory=False)
print("✅ CSV loaded successfully.")
print("📄 Columns found:", list(df.columns))

# --- Step 2: Normalize the column names ---
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
print("✅ Normalized columns:", list(df.columns))

# --- Step 3: Detect the order date column ---
order_date_col = None
for col in df.columns:
    if "order_date" in col or "date" in col:
        order_date_col = col
        break

if not order_date_col:
    print("❌ No order date column found!")
    exit()

print(f"🕓 Detected order date column: {order_date_col}")

# --- Step 4: Try parsing the order date ---
try:
    df[order_date_col] = pd.to_datetime(df[order_date_col], errors='coerce', dayfirst=True)
    print("✅ Parsed order dates successfully.")
except Exception as e:
    print("❌ Error parsing order dates:", str(e))
    traceback.print_exc()

# --- Step 5: Drop invalid dates ---
invalid_count = df[order_date_col].isna().sum()
if invalid_count > 0:
    print(f"⚠️ Dropped {invalid_count} invalid date rows")
    df = df.dropna(subset=[order_date_col])

print(f"🧩 Debug — order date type: {type(df[order_date_col])}, dtype={df[order_date_col].dtype}")
print("🧩 Sample values:", df[order_date_col].head(5).tolist())

# --- Step 6: Simple grouping test ---
try:
    grouped = df.groupby(df[order_date_col].dt.date).size()
    print("✅ Grouping successful. Sample result:")
    print(grouped.head())
except Exception as e:
    print("❌ Grouping failed:")
    traceback.print_exc()

print("\n✅ Basic diagnostic completed successfully.")
