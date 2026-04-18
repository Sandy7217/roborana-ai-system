import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

# ========== CONFIG ==========
CHROMA_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\AI_SYSTEM\RAG\VECTOR_DB"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# ============================

print("🔧 Initializing local RAG Query System...")

# Load model
model = SentenceTransformer(MODEL_NAME)

# Connect to Chroma
client = chromadb.PersistentClient(path=CHROMA_PATH)
collections = {c.name: c for c in client.list_collections()}

print(f"✅ Connected to Chroma. Collections available: {list(collections.keys())}\n")

# Query function
def query_collection(collection_name, user_query, top_k=5):
    if collection_name not in collections:
        print(f"❌ Collection '{collection_name}' not found.")
        return []

    collection = collections[collection_name]
    query_embedding = model.encode([user_query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    print(f"\n🔍 Query: {user_query}")
    print(f"📚 Results from collection: {collection_name}")
    print("="*60)

    for i, doc in enumerate(results['documents'][0]):
        print(f"#{i+1} — {doc[:500]}")  # limit long rows
        print("-"*60)

    return results


# ---------- Example ----------
if __name__ == "__main__":
    user_query = input("🧠 Enter your query: ")
    collection_name = input("📁 Collection (sales / returns / inventory): ").strip()
    query_collection(collection_name, user_query)
