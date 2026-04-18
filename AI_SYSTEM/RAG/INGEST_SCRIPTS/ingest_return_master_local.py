# =========================================================
# ingest_return_master_local.py — SmartSync Auto-Detect v2.2
# ---------------------------------------------------------
# - Uses local SentenceTransformer for embeddings
# - Auto-detects Return_Master.csv or Return_Master_Updated.csv
# - Embeds in batches (128)
# - Uploads to ChromaDB in batches (5000)
# - Automatically skips already ingested records
# - Designed for daily incremental Return_Master updates
# =========================================================

import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from pathlib import Path
import time
import os

# === PATH CONFIG ===
BASE_PATH = Path(os.getenv("ROBORANA_BASE_PATH", Path.cwd()))
RETURNS_DIR = BASE_PATH / "DATA" / "RETURNS" / "Master"
VECTOR_PATH = BASE_PATH / "AI_SYSTEM" / "RAG" / "VECTOR_DB"
COLLECTION_NAME = "returns"

# === AUTO-DETECT MASTER FILE ===
CSV_MAIN = RETURNS_DIR / "Return_Master.csv"
CSV_UPDATED = RETURNS_DIR / "Return_Master_Updated.csv"

if CSV_UPDATED.exists():
    CSV_PATH = CSV_UPDATED
    print(f"📂 Using updated master file:\n   {CSV_PATH}")
elif CSV_MAIN.exists():
    CSV_PATH = CSV_MAIN
    print(f"📂 Using main master file:\n   {CSV_PATH}")
else:
    raise FileNotFoundError("❌ No Return_Master file found (neither main nor updated).")

# === CONNECT TO CHROMA ===
client = chromadb.PersistentClient(path=str(VECTOR_PATH))
try:
    collection = client.get_collection(name=COLLECTION_NAME)
except Exception:
    print(f"ℹ️ Collection '{COLLECTION_NAME}' missing. Creating explicitly for ingestion.")
    collection = client.create_collection(name=COLLECTION_NAME)

# === LOAD LOCAL EMBEDDING MODEL ===
print("\n🔧 Loading local embedding model (this may take ~30s the first time)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# === READ CSV ===
print(f"\n📥 Loading: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, on_bad_lines='skip', engine='python')
print(f"✅ Loaded {len(df)} rows.\n")

# === DETERMINE UNIQUE IDENTIFIER ===
unique_col = None
for col in df.columns:
    if "return order code" in col.lower() or "return id" in col.lower() or "rto" in col.lower():
        unique_col = col
        break

if unique_col is None:
    print("⚠️ 'Return Order Code' not found — using row index as unique ID.")
    df["__unique_id__"] = df.index.astype(str)
    unique_col = "__unique_id__"
else:
    print(f"🔑 Using '{unique_col}' as unique identifier.\n")

# === PREPARE TEXT CHUNKS ===
records = []
for i, row in tqdm(df.iterrows(), total=len(df), desc="Preparing data"):
    text = ", ".join([f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])])
    uid = str(row[unique_col])
    records.append((f"return_{uid}", text))

# === FETCH EXISTING IDS FROM CHROMA ===
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
    print(f"✅ Found {len(existing_ids)} existing records in Chroma.\n")
except Exception as e:
    print(f"⚠️ Could not fetch existing records: {e}\n")

# === FILTER NEW RECORDS ===
new_records = [(rid, txt) for rid, txt in records if rid not in existing_ids]
print(f"🧮 {len(new_records)} new records to embed & upload (skipped {len(records) - len(new_records)} existing).\n")

if not new_records:
    print("✅ Nothing new to process. All return records already exist in Chroma.")
    exit()

# === CREATE EMBEDDINGS ===
print("🧠 Creating embeddings locally in batches of 128...")
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

print(f"\n🎯 Done! {total_records} new return records stored in collection '{COLLECTION_NAME}'.")
