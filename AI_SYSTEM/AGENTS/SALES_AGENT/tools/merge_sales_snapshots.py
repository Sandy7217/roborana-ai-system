# =========================================================
# AI_SYSTEM/AGENTS/SALES_AGENT/tools/merge_sales_snapshots.py
# =========================================================
# RoboRana AI — Sales Snapshot Merger v4.1 (Final Dual Output + Warn-Only + Auto Log)
# ---------------------------------------------------------
# Combines Uniware + SJIT daily snapshots into one master file.
# ✅ Keeps SJIT data intact
# ✅ Detects duplicates but DOES NOT remove them
# ✅ Saves Duplicate_Report.csv with details
# ✅ Adds Source Type column
# ✅ Adds Snapshot Origin for debug (Sales_Master_Debug.csv)
# ✅ Main Sales_Master.csv remains clean for RAG ingestion
# ✅ Creates daily run log in /LOGS/sales_merge_log.txt
# =========================================================

import os
import pandas as pd
from datetime import datetime

# 🧭 PATH CONFIGURATION
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
SALES_DIR = os.path.join(BASE_PATH, "DATA", "SALES")
MASTER_FILE = os.path.join(SALES_DIR, "Master", "Sales_Master.csv")
DEBUG_FILE = os.path.join(SALES_DIR, "Master", "Sales_Master_Debug.csv")
DUPLICATE_REPORT = os.path.join(SALES_DIR, "Master", "Duplicate_Report.csv")
LOG_FILE = os.path.join(BASE_PATH, "LOGS", "sales_merge_log.txt")


def merge_sales_snapshots():
    print(f"📂 Reading sales snapshots from: {SALES_DIR}")

    all_files = [
        os.path.join(SALES_DIR, f)
        for f in os.listdir(SALES_DIR)
        if f.lower().startswith("master_sale_data_") and f.lower().endswith(".csv")
    ]
    if not all_files:
        print("⚠️ No daily snapshot CSVs found in SALES folder.")
        return

    print(f"🧩 Found {len(all_files)} snapshot files to merge.")
    dfs = []

    # Read and clean all snapshots
    for file in sorted(all_files):
        try:
            df = pd.read_csv(file, encoding="utf-8-sig", low_memory=False, on_bad_lines="skip", quoting=1)
            df.columns = [c.strip().replace("\u00A0", " ").replace("\ufeff", "").strip() for c in df.columns]

            # Extract snapshot origin (from filename)
            snap_name = os.path.basename(file).replace("Master_sale_data_", "").replace(".csv", "")
            df["Snapshot Origin"] = snap_name

            dfs.append(df)
            print(f"✅ Loaded {len(df)} rows from {os.path.basename(file)}")
        except Exception as e:
            print(f"⚠️ Failed to read {file}: {e}")

    if not dfs:
        print("❌ No valid dataframes loaded.")
        return

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged.loc[:, ~merged.columns.duplicated()]
    merged.dropna(how="all", inplace=True)

    # 🕒 Sort by order date if present
    date_cols = [c for c in merged.columns if "date" in c.lower()]
    if date_cols:
        main_date_col = date_cols[0]
        merged[main_date_col] = pd.to_datetime(merged[main_date_col], errors="coerce", dayfirst=False)
        merged = merged.sort_values(by=main_date_col, ascending=True)
        print(f"🕒 Sorted by date column: {main_date_col}")

    # 🧭 Identify channel and SJIT rows
    if "Channel Name" not in merged.columns:
        print("⚠️ 'Channel Name' column not found; assuming all Uniware.")
        merged["Channel Name"] = "Unknown"

    merged["Channel Name"] = merged["Channel Name"].astype(str).str.strip().str.lower()

    # Detect SJIT rows
    sjit_mask = merged["Channel Name"].isin(["myntrasjit", "myntra sjit", "myntra_sjit"])
    sjit_df = merged[sjit_mask].copy()
    uniware_df = merged[~sjit_mask].copy()

    print(f"🔹 MyntraSJIT rows: {len(sjit_df)}")
    print(f"🔹 Uniware rows: {len(uniware_df)}")

    # 🏷️ Add Source Type
    sjit_df["Source Type"] = "MyntraSJIT"
    uniware_df["Source Type"] = "Uniware"

    # 🧠 Duplicate detection (Warn Only — DO NOT REMOVE)
    duplicate_count = 0
    if len(uniware_df) > 0:
        possible_cols = [
            "sale order item code", "item sku code", "display order code",
            "order date", "channel name", "selling price", "order status", "invoice number"
        ]
        dup_cols = [c for c in uniware_df.columns if any(key in c.lower() for key in possible_cols)]

        if len(dup_cols) > 3:
            duplicate_mask = uniware_df.duplicated(subset=dup_cols, keep=False)
            duplicate_df = uniware_df[duplicate_mask]
            if not duplicate_df.empty:
                duplicate_count = len(duplicate_df)
                print(f"⚠️ WARNING: {duplicate_count} potential duplicate Uniware rows detected (not removed).")
                print(f"🔍 Duplicate check based on: {dup_cols[:6]}")
                print(f"📄 Saving duplicate list → {DUPLICATE_REPORT}")

                os.makedirs(os.path.dirname(DUPLICATE_REPORT), exist_ok=True)
                duplicate_df.to_csv(DUPLICATE_REPORT, index=False, encoding="utf-8-sig")

                print("🔎 Sample duplicates:")
                print(duplicate_df.head(3).to_string(index=False))
            else:
                print("✅ No duplicate Uniware rows detected.")
        else:
            print("⚠️ Not enough columns found for duplicate detection.")
    else:
        print("ℹ️ No Uniware data found for duplicate checking.")

    # 🔄 Merge Uniware + SJIT back together
    merged_final = pd.concat([uniware_df, sjit_df], ignore_index=True)

    # 💾 Save RAG-compatible clean master
    os.makedirs(os.path.dirname(MASTER_FILE), exist_ok=True)
    merged_final.drop(columns=["Snapshot Origin"], errors="ignore").to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ Final master saved → {MASTER_FILE}")

    # 💾 Save Debug version (with snapshot info)
    merged_final.to_csv(DEBUG_FILE, index=False, encoding="utf-8-sig")
    print(f"🧾 Debug file (with snapshot origins) saved → {DEBUG_FILE}")

    print(f"📊 Total rows in master: {len(merged_final)} (from {len(merged)})")

    # 🪵 Log summary for Task Scheduler verification
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Sales snapshots merged: {len(all_files)} files | "
            f"Rows: {len(merged_final)} | Duplicates: {duplicate_count}\n"
        )


if __name__ == "__main__":
    merge_sales_snapshots()