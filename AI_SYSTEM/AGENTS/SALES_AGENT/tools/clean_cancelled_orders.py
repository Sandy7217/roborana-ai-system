# =========================================================
# AI_SYSTEM/AGENTS/SALES_AGENT/tools/append_csvs_to_sales_master.py
# =========================================================
# RoboRana AI — Sales Master Merger v2.0 (Stable)
# ---------------------------------------------------------
# • Reads ALL CSVs in the OLD_SALES folder
# • Aligns them to Sales_Master.csv schema (auto column match)
# • Appends data safely, preserves column order
# • No filters, no cancel logic, no dedup — pure merge
# ---------------------------------------------------------
# Author: RoboRana AI System (Sandeep Rana)
# =========================================================

import os
import pandas as pd

# ---------- PATHS ----------
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
SALES_DIR = os.path.join(BASE_PATH, "DATA", "SALES")
SOURCE_DIR = os.path.join(SALES_DIR, "OLD_SALES")        # <- place old CSVs here
MASTER_FILE = os.path.join(SALES_DIR, "Master", "Sales_Master.csv")
OUTPUT_FILE = os.path.join(SALES_DIR, "Master", "Sales_Master_Updated.csv")

# Overwrite master directly if True
OVERWRITE_MASTER = False
# -----------------------------

def _canonical(s: str) -> str:
    """Normalize header names for case-insensitive matching."""
    return " ".join(str(s).replace("\u00A0", " ").replace("\ufeff", "").strip().split()).lower()

def main():
    # 1️⃣ Load Master Schema
    print(f"📂 Loading master schema from: {MASTER_FILE}")
    master_df = pd.read_csv(MASTER_FILE, encoding="utf-8-sig", low_memory=False)
    master_cols = list(master_df.columns)
    print(f"✅ Master has {len(master_df)} rows and {len(master_cols)} columns.\n")

    # 2️⃣ Find CSVs in Source Folder
    if not os.path.isdir(SOURCE_DIR):
        raise FileNotFoundError(f"❌ Source folder not found: {SOURCE_DIR}")

    files = [os.path.join(SOURCE_DIR, f) for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".csv")]
    if not files:
        print("⚠️ No CSV files found in source folder.")
        return

    print(f"🧩 Found {len(files)} CSV files to append from:\n   {SOURCE_DIR}\n")

    # 3️⃣ Canonical Header Map
    master_key_map = {_canonical(c): c for c in master_cols}

    aligned_frames = []
    total_rows_loaded = 0

    # 4️⃣ Process Each CSV
    for path in sorted(files):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False, on_bad_lines="skip", quoting=1)
            df.columns = [" ".join(str(c).replace("\u00A0", " ").replace("\ufeff", "").strip().split()) for c in df.columns]
            src_cols = list(df.columns)

            # Build mapping to master schema
            src_to_master = {}
            for src in src_cols:
                key = _canonical(src)
                if key in master_key_map:
                    src_to_master[src] = master_key_map[key]

            # Create aligned DataFrame
            aligned = pd.DataFrame(columns=master_cols)
            for mcol in master_cols:
                found_src = next((src for src, mapped in src_to_master.items() if mapped == mcol), None)
                aligned[mcol] = df[found_src] if found_src else ""

            aligned_frames.append(aligned)
            total_rows_loaded += len(aligned)
            print(f"📄 {os.path.basename(path)} → {len(aligned)} rows aligned to master schema.")

        except Exception as e:
            print(f"⚠️ Failed to process {os.path.basename(path)} → {e}")

    if not aligned_frames:
        print("❌ No valid CSVs loaded.")
        return

    # 5️⃣ Append to Master
    to_append = pd.concat(aligned_frames, ignore_index=True)
    final_df = pd.concat([master_df, to_append], ignore_index=True)

    # 6️⃣ Save Output
    out_path = MASTER_FILE if OVERWRITE_MASTER else OUTPUT_FILE
    final_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n✅ Merge Complete.")
    print(f"   • Appended rows: {total_rows_loaded}")
    print(f"   • Final total rows: {len(final_df)}")
    print(f"   • Saved to: {out_path}")
    if not OVERWRITE_MASTER:
        print("   • (Set OVERWRITE_MASTER=True to overwrite Sales_Master.csv)")

if __name__ == "__main__":
    main()
