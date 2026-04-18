# ingest_sales_master.py
import os
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

# === CONFIG ===
CSV_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES\Master\Sales_Master.csv"
VECTOR_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\AI_SYSTEM\RAG\VECTOR_DB"
COLLECTION_NAME = "sales"

# === CONNECT TO CHROMA ===
client = chromadb.PersistentClient(path=VECTOR_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# === EMBEDDING SETUP ===
embedding_func = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

# === READ DATA ===
print(f"📂 Loading sales data from:\n{CSV_PATH}\n")
df = pd.read_csv(CSV_PATH)
print(f"✅ Loaded {len(df)} rows.\n")

# === CREATE TEXT CHUNKS FOR EMBEDDING ===
# you can customize this based on your CSV structure
records = []
for i, row in tqdm(df.iterrows(), total=len(df), desc="Preparing data"):
    text = ", ".join([f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])])
    records.append({
        "id": f"sales_{i}",
        "text": text
    })

# === ADD TO CHROMA ===
print("\n🚀 Uploading embeddings to Chroma...")
collection.add(
    ids=[r["id"] for r in records],
    documents=[r["text"] for r in records],
    embeddings=None  # handled internally by Chroma using embedding_func
)

print(f"\n🎯 Ingestion complete! {len(records)} records added to collection '{COLLECTION_NAME}'.")
