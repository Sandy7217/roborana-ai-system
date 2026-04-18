# =========================================================
# ingest_sales_master_local.py — SmartSync + Logging v3.0
# ---------------------------------------------------------
# - Uses local SentenceTransformer for embeddings
# - Embeds in batches (128)
# - Uploads to ChromaDB in batches (5000)
# - Automatically skips already ingested records
# - Logs each ingestion run with details
# =========================================================

import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from pathlib import Path
import time
import json
from datetime import datetime

# === PATH CONFIG ===
BASE_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data")
CSV_PATH = BASE_PATH / "DATA" / "SALES" / "Master" / "Sales_Master.csv"
VECTOR_PATH = BASE_PATH / "AI_SYSTEM" / "RAG" / "VECTOR_DB"
LOG_PATH = BASE_PATH / "AI_SYSTEM" / "MEMORY" / "ingest_logs"
LOG_FILE = LOG_PATH / "sales_ingest_log.json"
COLLECTION_NAME = "sales"

# === CONNECT TO CHROMA ===
client = chromadb.PersistentClient(path=str(VECTOR_PATH))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# === LOAD LOCAL EMBEDDING MODEL ===
print("🔧 Loading local embedding model (this may take ~30s the first time)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# === READ CSV ===
print(f"\n📂 Loading: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, on_bad_lines='skip', engine='python')
print(f"✅ Loaded {len(df)} rows.")

# === DETERMINE UNIQUE IDENTIFIER ===
unique_col = None
for col in df.columns:
    if "sale order code" in col.lower():
        unique_col = col
        break

if unique_col is None:
    print("⚠️ 'Sale Order Code' not found — using row index as unique ID.")
    df["__unique_id__"] = df.index.astype(str)
    unique_col = "__unique_id__"

# === PREPARE TEXT CHUNKS ===
records = []
for i, row in tqdm(df.iterrows(), total=len(df), desc="Preparing data"):
    text = ", ".join([f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])])
    uid = str(row[unique_col])
    records.append((f"sales_{uid}", text))

# === FETCH EXISTING IDS FROM CHROMA (for resume/incremental) ===
print("\n🔍 Checking existing records in Chroma...")
existing_ids = set()
try:
    offset = 0
    limit = 5000
    while True:
        result = collection.get(include=["ids"], limit=limit, offset=offset)
        if not result["ids"]:
            break
        existing_ids.update(result["ids"])
        offset += limit
    print(f"✅ Found {len(existing_ids)} existing records.")
except Exception as e:
    print(f"⚠️ Could not fetch existing records: {e}")

# === FILTER NEW RECORDS ===
new_records = [(rid, txt) for rid, txt in records if rid not in existing_ids]
print(f"🧮 {len(new_records)} new records to embed & upload (skipped {len(records) - len(new_records)} existing).")

if not new_records:
    print("✅ Nothing new to process. All records already exist in Chroma.")
    exit()

# === CREATE EMBEDDINGS ===
start_time = time.time()
print("\n🧠 Creating embeddings locally in batches of 128...")
texts = [r[1] for r in new_records]
embeddings = model.encode(texts, batch_size=128, show_progress_bar=True)

# === SAVE TO CHROMA IN SAFE BATCHES ===
BATCH_SIZE = 5000
total_records = len(new_records)
num_batches = (total_records + BATCH_SIZE - 1) // BATCH_SIZE

print(f"\n🚀 Uploading to Chroma in {num_batches} batches of {BATCH_SIZE} each...\n")

for i in range(0, total_records, BATCH_SIZE):
    start = i
    end = min(i + BATCH_SIZE, total_records)
    batch_ids = [r[0] for r in new_records[start:end]]
    batch_texts = [r[1] for r in new_records[start:end]]
    batch_embeds = embeddings[start:end].tolist()

    try:
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=batch_embeds
        )
        print(f"✅ Uploaded batch {i//BATCH_SIZE + 1}/{num_batches} ({len(batch_ids)} records)")
    except Exception as e:
        print(f"⚠️ Error uploading batch {i//BATCH_SIZE + 1}: {e}")

    time.sleep(0.3)  # prevent overload

elapsed = round((time.time() - start_time) / 60, 2)

# === FINAL STATUS ===
final_count = len(existing_ids) + total_records
print(f"\n🎯 Done! {total_records} new records stored in collection '{COLLECTION_NAME}'.")
print(f"🕒 Total time taken: {elapsed} minutes.")
print(f"📊 Collection total (approx): {final_count} records.\n")

# === LOG RESULTS ===
LOG_PATH.mkdir(parents=True, exist_ok=True)

log_entry = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "csv_file": str(CSV_PATH),
    "records_added": total_records,
    "records_skipped": len(records) - len(new_records),
    "total_in_collection": final_count,
    "time_taken_min": elapsed
}

if LOG_FILE.exists():
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)
else:
    logs = []

logs.append(log_entry)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    json.dump(logs, f, indent=4, ensure_ascii=False)

print(f"🧾 Log saved → {LOG_FILE}")
