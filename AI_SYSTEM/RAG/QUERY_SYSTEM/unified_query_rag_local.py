# =========================================================
# File: AI_SYSTEM/RAG/QUERY_SYSTEM/unified_query_rag_local.py
# Purpose: Unified local query interface for all RAG operations (Persistent ChromaDB client)
# =========================================================

import os
import chromadb


class UnifiedQueryRAGLocal:
    """
    Unified Query Interface for local ChromaDB (PersistentClient version).
    Compatible with UnifiedRAGBrain, Sales Agent, Inventory Agent, and all RAG-based modules.
    """

    def __init__(self):
        # -------------------------------------------------
        # 🔍 Determine Vector DB Path
        # -------------------------------------------------
        base_path = self._resolve_vector_db_path()
        print(f"🔍 Using vector DB path: {base_path}")

        # -------------------------------------------------
        # 🧠 Initialize Persistent Client (Chroma v0.5+)
        # -------------------------------------------------
        try:
            self.client = chromadb.PersistentClient(path=base_path)
        except Exception as e:
            print(f"❌ Failed to initialize Chroma PersistentClient: {e}")
            raise

        # Predefined expected collections (for reference)
        self.known_collections = [
            "sales", "returns", "inventory",
            "ads", "ads_pla", "ads_visibility", "finance"
        ]

        # Fetch actual collections from DB
        try:
            available = self.client.list_collections()
            self.collections = [c.name for c in available]
            print(f"✅ Connected to {len(self.collections)} collections: {self.collections}")
        except Exception as e:
            print(f"⚠️ Failed to list collections: {e}")
            self.collections = self.known_collections

        print("✅ UnifiedQueryRAGLocal initialized successfully.\n")

    def _resolve_vector_db_path(self) -> str:
        """
        Resolve vector DB path in a deterministic way.
        """
        candidates = [
            os.path.abspath(os.path.join(os.getcwd(), "AI_SYSTEM", "RAG", "VECTOR_DB")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "VECTOR_DB")),
        ]
        for p in candidates:
            if os.path.isdir(p):
                return p
        return candidates[0]

    # =========================================================
    # 🧩 Helper — List all available collections
    # =========================================================
    def get_collections(self):
        """Return a list of all available Chroma collections."""
        try:
            collections = self.client.list_collections()
            names = [c.name for c in collections]
            print(f"✅ Available collections: {names}")
            return names
        except Exception as e:
            print(f"❌ Error fetching collections: {e}")
            return []

    # =========================================================
    # 🔹 Query a single collection
    # =========================================================
    def query_single_source(self, collection_name: str, query_text: str, n_results: int = 5):
        """
        Query one collection and return the most relevant documents.
        Returns a dictionary with documents and metadata.
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            results = collection.query(query_texts=[query_text], n_results=n_results)

            docs = results.get("documents", [[]])[0] if results else []
            if docs:
                print(f"📄 Retrieved {len(docs)} documents from '{collection_name}'")
            else:
                print(f"⚠️ No relevant documents found in '{collection_name}'")

            return {"collection": collection_name, "documents": docs}

        except Exception as e:
            print(f"❌ Query failed for '{collection_name}': {e}")
            return {"collection": collection_name, "error": str(e), "documents": []}

    # =========================================================
    # 🔹 Unified Multi-Collection Query
    # =========================================================
    def query_all_sources(self, query_text: str, n_results: int = 5):
        """
        Perform a unified query across all available RAG collections.
        Used by UnifiedRAGBrain and all AI agents.
        """
        print(f"\n🧠 Running unified RAG search for: '{query_text}'\n")
        combined_results = {}
        searched = self.collections if self.collections else self.known_collections

        for name in searched:
            print(f"🔍 Searching in collection: {name}")
            result = self.query_single_source(name, query_text, n_results)
            docs = result.get("documents", [])
            if docs:
                combined_results[name] = docs

        if not combined_results:
            print("⚠️ No relevant documents found in any collection.\n")
            return {"message": "No relevant documents found."}

        print("✅ Unified RAG search completed successfully.\n")
        return combined_results

    # =========================================================
    # 🔹 Backward Compatibility Alias
    # =========================================================
    def unified_query(self, query_text: str, n_results: int = 5):
        """Alias for backward compatibility (same as query_all_sources)."""
        return self.query_all_sources(query_text, n_results)


# =========================================================
# 🧪 Standalone Test Mode
# =========================================================
if __name__ == "__main__":
    rag = UnifiedQueryRAGLocal()
    rag.get_collections()
    result = rag.query_all_sources("top performing SKUs in October 2025")
    print("\n🧩 Query Output Preview:")
    print(result)
