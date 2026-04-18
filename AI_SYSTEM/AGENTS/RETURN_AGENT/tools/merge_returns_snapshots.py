# =========================================================
# merge_returns_snapshots.py — RoboRana Returns Merger v3.9
# ---------------------------------------------------------
# - Auto-creates Return_Master.csv if missing
# - Aligns and merges all old return CSVs from OLD_RETURNS
# - Maps columns by header name similarity
# - Filters out "Courier Return" rows in Return Type
# - Skips malformed lines safely
# - Saves to Return_Master_Updated.csv (non-destructive)
# =========================================================

import os
import pandas as pd

# === PATH CONFIG ===
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
RETURNS_DIR = os.path.join(BASE_PATH, "DATA", "RETURNS")
SOURCE_DIR = os.path.join(RETURNS_DIR, "OLD_RETURNS")
MASTER_FILE = os.path.join(RETURNS_DIR, "Master", "Return_Master.csv")
OUTPUT_FILE = os.path.join(RETURNS_DIR, "Master", "Return_Master_Updated.csv")

# === SETTINGS ===
OVERWRITE_MASTER = False  # set True after verifying output

# === UTILITIES ===
def _canonical(s: str) -> str:
    """Normalize column header for matching."""
    return " ".join(str(s).replace("\u00A0", " ").replace("\ufeff", "").strip().split()).lower()

def safe_read_csv(path: str) -> pd.DataFrame:
    """Safely read CSV with flexible fallback."""
    try:
        return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="skip", quoting=1)
    except Exception:
        return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip", quoting=1)

def main():
    print(f"📂 Checking master schema at: {MASTER_FILE}\n")

    # === STEP 1 — Check Master File ===
    if os.path.exists(MASTER_FILE):
        master_df = safe_read_csv(MASTER_FILE)
        master_cols = list(master_df.columns)
        print(f"✅ Master found with {len(master_df)} rows and {len(master_cols)} columns.\n")
    else:
        print("⚠️ Master file not found. A new one will be created from OLD_RETURNS.\n")
        master_df = pd.DataFrame()
        master_cols = None

    # === STEP 2 — Verify Source Directory ===
    if not os.path.isdir(SOURCE_DIR):
        print(f"❌ Source folder not found: {SOURCE_DIR}")
        return

    files = [os.path.join(SOURCE_DIR, f) for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".csv")]
    if not files:
        print("⚠️ No CSV files found in OLD_RETURNS folder.")
        return

    print(f"🧩 Found {len(files)} CSV files in: {SOURCE_DIR}\n")

    aligned_frames = []
    total_rows_added = 0
    total_courier_removed = 0

    # === STEP 3 — If master missing, use first CSV as schema base ===
    if master_cols is None:
        for sample_path in files:
            try:
                sample_df = safe_read_csv(sample_path)
                sample_df.columns = [" ".join(str(c).replace("\u00A0", " ").replace("\ufeff", "").strip().split()) for c in sample_df.columns]
                master_cols = list(sample_df.columns)
                print(f"🧱 Master schema initialized from {os.path.basename(sample_path)} with {len(master_cols)} columns.\n")
                break
            except Exception:
                continue
        if master_cols is None:
            print("❌ Could not determine schema from any CSV. Check your OLD_RETURNS files.")
            return

    master_key_map = {_canonical(c): c for c in master_cols}

    # === STEP 4 — Process All Files ===
    for file in sorted(files):
        try:
            df = safe_read_csv(file)
            df.columns = [" ".join(str(c).replace("\u00A0", " ").replace("\ufeff", "").strip().split()) for c in df.columns]

            src_to_master = {
                src: master_key_map[_canonical(src)]
                for src in df.columns if _canonical(src) in master_key_map
            }

            aligned = pd.DataFrame(columns=master_cols)
            for mcol in master_cols:
                match = next((s for s, m in src_to_master.items() if m == mcol), None)
                aligned[mcol] = df[match] if match else ""

            # 🧹 Remove "Courier Return"
            return_type_cols = [c for c in aligned.columns if "return type" in c.lower()]
            if return_type_cols:
                rt_col = return_type_cols[0]
                before = len(aligned)
                aligned = aligned[~aligned[rt_col].astype(str).str.lower().str.contains("courier return", na=False)]
                removed = before - len(aligned)
                total_courier_removed += removed
                print(f"🚫 Removed {removed} 'Courier Return' rows from {os.path.basename(file)}")

            aligned_frames.append(aligned)
            total_rows_added += len(aligned)
            print(f"📄 {os.path.basename(file)} → {len(aligned)} rows aligned to master schema.\n")

        except Exception as e:
            print(f"⚠️ Failed to process {os.path.basename(file)}: {e}")

    if not aligned_frames:
        print("❌ No valid data loaded from OLD_RETURNS.")
        return

    # === STEP 5 — Merge and Save ===
    merged_df = pd.concat([master_df] + aligned_frames, ignore_index=True)
    out_path = MASTER_FILE if OVERWRITE_MASTER else OUTPUT_FILE

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    merged_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n✅ Merge Complete!")
    print(f"   • Added rows (after filtering): {total_rows_added}")
    print(f"   • 'Courier Return' rows removed: {total_courier_removed}")
    print(f"   • Final total rows: {len(merged_df)}")
    print(f"   • Saved to: {out_path}")
    if not OVERWRITE_MASTER:
        print("   • (Set OVERWRITE_MASTER=True to overwrite Return_Master.csv)")

if __name__ == "__main__":
    main()
