import pandas as pd
import os
import re
from datetime import datetime

# ================= PATHS =================
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES"
MASTER_FILE = os.path.join(BASE_PATH, "Master", "Sales_Master.csv")

# ================= FIND LATEST SNAPSHOT =================
daily_files = []

for file in os.listdir(BASE_PATH):
    if file.startswith("Master_sale_data") and file.endswith(".csv"):
        daily_files.append(file)

if not daily_files:
    print("❌ No daily snapshots found")
    exit()

# Extract date like: "25 Nov 2025"
def extract_date(filename):
    match = re.search(r'(\d{1,2}\s[A-Za-z]{3}\s\d{4})', filename)
    if match:
        return datetime.strptime(match.group(1), "%d %b %Y")
    return None

dated_files = []

for file in daily_files:
    file_date = extract_date(file)
    if file_date:
        dated_files.append((file_date, file))

if not dated_files:
    print("❌ Could not extract dates from filenames")
    exit()

# Pick the most recent snapshot
latest_file = max(dated_files, key=lambda x: x[0])[1]
daily_file_path = os.path.join(BASE_PATH, latest_file)

print("📄 Latest daily snapshot selected:", latest_file)

# ================= LOAD MASTER =================
print("📄 Loading master file...")
master_df = pd.read_csv(MASTER_FILE, low_memory=False)
master_columns = list(master_df.columns)

# ================= ALIGN FUNCTION =================
def align_columns(df, master_cols):
    df.columns = df.columns.str.strip()

    # Add missing columns
    for col in master_cols:
        if col not in df.columns:
            df[col] = ""

    # Keep only master columns
    df = df[master_cols]
    return df

# ================= LOAD DAILY SNAPSHOT =================
print("📄 Loading daily snapshot...")
daily_df = pd.read_csv(daily_file_path, low_memory=False)

daily_df = align_columns(daily_df, master_columns)

# ================= MERGE INTO MASTER =================
print("🔁 Merging daily data into master...")
updated_master = pd.concat([master_df, daily_df], ignore_index=True)

print("📊 Rows before deduplication:", len(updated_master))

# ================= REMOVE DUPLICATES =================
updated_master.drop_duplicates(
    subset=["Display Order Code"],
    keep="last",    # Latest record wins ✅
    inplace=True
)

print("🧹 Rows after deduplication:", len(updated_master))

# ================= SAVE MASTER =================
updated_master.to_csv(MASTER_FILE, index=False)

print("\n✅ DAILY SALES MASTER UPDATED SUCCESSFULLY ✅")
print("📁 Updated file:", MASTER_FILE)
print("📦 Snapshot used:", latest_file)
