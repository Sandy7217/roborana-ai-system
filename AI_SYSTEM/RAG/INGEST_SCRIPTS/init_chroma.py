# init_chroma.py
import chromadb
from pathlib import Path

# Set the local Chroma vector database path
VECTOR_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\AI_SYSTEM\RAG\VECTOR_DB")

# Initialize Chroma persistent client
client = chromadb.PersistentClient(path=str(VECTOR_PATH))

# Optional: create starter collections (you can add more later)
collections = [
    "sales",
    "returns",
    "inventory",
    "ads",
    "finance"
]

print("🔧 Initializing local Chroma database at:")
print(VECTOR_PATH, "\n")

for name in collections:
    collection = client.get_or_create_collection(name=name)
    print(f"✅ Collection created: {collection.name}")

print("\n🎯 Chroma RAG base initialized successfully!")
