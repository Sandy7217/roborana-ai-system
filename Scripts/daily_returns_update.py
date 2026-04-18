import pandas as pd
import os
import re
from datetime import datetime

# ================= PATHS =================
RETURNS_FOLDER = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\RETURNS\FINAL"
MASTER_FILE = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\RETURNS\Master\Return_Master_Updated.csv"

# ================= FIND LATEST RETURNS FILE =================
snapshot_files = [
    file for file in os.listdir(RETURNS_FOLDER)
    if file.startswith("returns_") and file.endswith(".csv")
]

if not snapshot_files:
    print("❌ No return snapshots found")
    exit()

# Extract date like: "26 Nov 2025"
def extract_date(filename):
    match = re.search(r'(\d{1,2}\s[A-Za-z]{3}\s\d{4})', filename)
    if match:
        return datetime.strptime(match.group(1), "%d %b %Y")
    return None

dated_files = [(extract_date(f), f) for f in snapshot_files if extract_date(f)]

if not dated_files:
    print("❌ Could not extract date from filenames")
    exit()

latest_file = max(dated_files, key=lambda x: x[0])[1]
latest_file_path = os.path.join(RETURNS_FOLDER, latest_file)

print("📄 Latest return snapshot selected:", latest_file)

# ================= LOAD MASTER =================
master_df = pd.read_csv(MASTER_FILE, low_memory=False)
before_rows = len(master_df)

# ================= COLUMN ALIGN FUNCTION =================
def align_columns(df, master_cols):
    df.columns = df.columns.str.strip()
    for col in master_cols:
        if col not in df.columns:
            df[col] = ""
    return df[master_cols]

# ================= LOAD DAILY RETURNS =================
daily_df = pd.read_csv(latest_file_path, low_memory=False)
daily_rows = len(daily_df)

daily_df = align_columns(daily_df, master_df.columns)

print("✅ Daily snapshot aligned")
print("📊 Master rows before:", before_rows)
print("📊 Snapshot rows:", daily_rows)

# ================= CREATE COMPOSITE UNIQUE KEY =================
daily_df["__unique_key__"] = (
    daily_df["Sale Order Number"].astype(str).str.strip() + "_" +
    daily_df["Product SKU Code"].astype(str).str.strip()
)

master_df["__unique_key__"] = (
    master_df["Sale Order Number"].astype(str).str.strip() + "_" +
    master_df["Product SKU Code"].astype(str).str.strip()
)

# ================= FIND NEW VS UPDATED =================
old_keys = set(master_df["__unique_key__"])
incoming_keys = set(daily_df["__unique_key__"])

new_keys = incoming_keys - old_keys
common_keys = incoming_keys & old_keys

print("🆕 New unique return rows:", len(new_keys))
print("🔄 Updated existing rows:", len(common_keys))

# ================= MERGE =================
combined = pd.concat([master_df, daily_df], ignore_index=True)

combined.drop_duplicates(
    subset="__unique_key__",
    keep="last",   # Latest wins
    inplace=True
)

combined.drop(columns=["__unique_key__"], inplace=True)

after_rows = len(combined)

# ================= SAVE UPDATED MASTER =================
combined.to_csv(MASTER_FILE, index=False)

# ================= FINAL REPORT =================
print("\n✅ RETURNS MASTER UPDATED SUCCESSFULLY ✅")
print("📦 Snapshot used:", latest_file)
print("📊 Rows before:", before_rows)
print("📊 Rows in snapshot:", daily_rows)
print("➕ New rows added:", len(new_keys))
print("🔄 Rows updated:", len(common_keys))
print("📊 Rows after:", after_rows)
print("📁 Master file:", MASTER_FILE)
