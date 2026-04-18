import pandas as pd
import os

# ================== PATHS ==================
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES"

OLD_SALES_FOLDER = os.path.join(BASE_PATH, "OLD_SALES")
DAILY_SNAPSHOT_FOLDER = BASE_PATH
MASTER_PATH = os.path.join(BASE_PATH, "Master", "Sales_Master.csv")

# ================== LOAD MASTER TEMPLATE ==================
print("📄 Loading master template...")
master_df = pd.read_csv(MASTER_PATH, low_memory=False)
master_columns = list(master_df.columns)

print("✅ Master template loaded")
print("Columns:", len(master_columns))

# ================== COLUMN ALIGN FUNCTION ==================
def align_columns(df, master_cols):
    df.columns = df.columns.str.strip()

    # Add missing columns
    for col in master_cols:
        if col not in df.columns:
            df[col] = ""

    # Remove extra unwanted columns
    df = df[master_cols]

    return df

# ================== LOAD ALL OLD SALES FILES ==================
all_data = []

print("\n📂 Loading OLD SALES files...")

for file in os.listdir(OLD_SALES_FOLDER):
    if file.endswith(".csv"):
        file_path = os.path.join(OLD_SALES_FOLDER, file)
        print("→ Reading:", file)

        try:
            df = pd.read_csv(file_path, low_memory=False)
            aligned_df = align_columns(df, master_columns)
            all_data.append(aligned_df)
        except Exception as e:
            print("⚠ Error:", file, "->", e)

print("✅ Old sales files loaded:", len(all_data))

# ================== LOAD DAILY SNAPSHOTS ==================
print("\n📂 Loading Daily Snapshot files...")

for file in os.listdir(DAILY_SNAPSHOT_FOLDER):
    if file.startswith("Master_sale_data") and file.endswith(".csv"):
        file_path = os.path.join(DAILY_SNAPSHOT_FOLDER, file)
        print("→ Reading:", file)

        try:
            df = pd.read_csv(file_path, low_memory=False)
            aligned_df = align_columns(df, master_columns)
            all_data.append(aligned_df)
        except Exception as e:
            print("⚠ Error:", file, "->", e)

print("✅ Daily snapshots added")

# ================== INCLUDE CURRENT MASTER ==================
print("\n📂 Adding existing master file data...")
all_data.append(master_df)

# ================== MERGE EVERYTHING ==================
final_df = pd.concat(all_data, ignore_index=True)

print("\n📊 Total rows before cleaning:", len(final_df))

# ================== REMOVE DUPLICATES (KEEP LATEST) ==================
final_df.drop_duplicates(
    subset=["Display Order Code"],
    keep="last",   # 👈 This is your request (latest entry wins)
    inplace=True
)

print("🧹 Rows after deduplication:", len(final_df))

# ================== SAVE THE REBUILT MASTER ==================
final_df.to_csv(MASTER_PATH, index=False)

print("\n🔥 SALES MASTER REBUILT & ALIGNED SUCCESSFULLY 🔥")
print("📁 Path:", MASTER_PATH)
print("✅ Total Orders:", len(final_df))
