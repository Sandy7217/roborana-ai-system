# query_sales_local.py
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

# === CONFIG ===
VECTOR_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\AI_SYSTEM\RAG\VECTOR_DB")
COLLECTION_NAME = "sales"

# === CONNECT TO CHROMA ===
client = chromadb.PersistentClient(path=str(VECTOR_PATH))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# === LOAD LOCAL EMBEDDING MODEL ===
print("🔧 Loading local model for query embeddings...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# === INPUT QUERY ===
query = input("\n🔍 Enter your search query (e.g., 'top orders from Ajio in July'): ").strip()
if not query:
    print("⚠️ No query entered. Exiting.")
    exit()

# === CREATE EMBEDDING FOR QUERY ===
query_embedding = model.encode([query])

# === SEARCH IN CHROMA ===
print("\n📊 Searching in Chroma...")
results = collection.query(
    query_embeddings=query_embedding,
    n_results=5  # top 5 most relevant records
)

# === SHOW RESULTS ===
print("\n🎯 Top Matches:")
for i, doc in enumerate(results["documents"][0]):
    print(f"\n[{i+1}] {doc[:300]}...")
