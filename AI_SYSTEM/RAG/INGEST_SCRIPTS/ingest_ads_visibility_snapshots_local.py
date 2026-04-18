import os
import glob
import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb

# ========== CONFIGURATION ==========
DATA_FOLDER = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\ADS\VISIBILITY"
CHROMA_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\AI_SYSTEM\RAG\VECTOR_DB"
COLLECTION_NAME = "ads_visibility"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 5000
# ==================================

print("🔧 Loading local embedding model (this may take ~30s the first time)...")
model = SentenceTransformer(MODEL_NAME)

# ---------- Load and Combine Snapshots ----------
csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
if not csv_files:
    raise FileNotFoundError("❌ No CSV files found in Visibility folder.")

print(f"\n📂 Found {len(csv_files)} visibility reports. Reading and combining...\n")

dfs = []
for file in tqdm(csv_files):
    try:
        df = pd.read_csv(file)
        filename = os.path.basename(file)
        snapshot_info = filename.replace("Visibility_Data_", "").replace(".csv", "")
        df["snapshot_datetime"] = snapshot_info
        dfs.append(df)
    except Exception as e:
        print(f"⚠️ Skipped file {file}: {e}")

merged_df = pd.concat(dfs, ignore_index=True)
print(f"✅ Combined total rows: {len(merged_df)}\n")

# ---------- Prepare Texts & Metadata ----------
texts = []
metadata = []
ids = []

for i, row in merged_df.iterrows():
    text = " | ".join([f"{col}: {str(row[col])}" for col in merged_df.columns if col != "snapshot_datetime"])
    texts.append(text)
    metadata.append({"snapshot_datetime": str(row["snapshot_datetime"])})
    ids.append(f"ads_visibility_{i}")

# ---------- Create Embeddings ----------
print("🧠 Creating embeddings locally...")
embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)

# ---------- Connect to Chroma ----------
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# ---------- Upload to Chroma in Safe Batches ----------
print("\n🚀 Uploading to Chroma in chunks...\n")
total_batches = (len(texts) - 1) // BATCH_SIZE + 1

for i in range(0, len(texts), BATCH_SIZE):
    batch_texts = texts[i:i + BATCH_SIZE]
    batch_embeddings = embeddings[i:i + BATCH_SIZE]
    batch_metadata = metadata[i:i + BATCH_SIZE]
    batch_ids = ids[i:i + BATCH_SIZE]

    collection.add(
        embeddings=batch_embeddings,
        documents=batch_texts,
        metadatas=batch_metadata,
        ids=batch_ids
    )
    print(f"✅ Uploaded batch {i // BATCH_SIZE + 1} / {total_batches}")

print(f"\n🎯 Done! {len(texts)} records stored in collection '{COLLECTION_NAME}'.")
