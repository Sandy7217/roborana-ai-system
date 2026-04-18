# File: AI_SYSTEM/RAG/rag_brain.py
# Purpose: Unified interface for all RAG-related operations in RoboRana AI

import os
from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal


class UnifiedRAGBrain:
    """
    The UnifiedRAGBrain serves as a single access point to all RAG collections.
    It wraps around the UnifiedQueryRAGLocal system to perform multi-collection searches
    and provides standardized query interfaces for all AI agents.

    ✅ Supports:
       - query(): unified search across all collections
       - query_all(): domain-specific RAG context for agents
       - unified_query(): backward compatibility for older agents
    """

    def __init__(self):
        print("🔧 Initializing Unified RAG Brain...")

        # Initialize unified local query engine
        self.query_engine = UnifiedQueryRAGLocal()

        # Define available RAG data collections
        self.collections = {
            "sales": None,
            "returns": None,
            "inventory": None,
            "ads": None,
            "ads_pla": None,
            "ads_visibility": None,
            "finance": None
        }

        print(f"✅ Connected to {len(self.collections)} collections: {list(self.collections.keys())}")

    # ==========================================================
    # 🧠 Unified Multi-Collection Query
    # ==========================================================
    def query(self, question: str):
        """Perform a unified RAG query across all sources (multi-collection)."""
        try:
            result = self.query_engine.query_all_sources(question)
            return self._format_result(result)
        except Exception as e:
            print(f"❌ RAG unified query error: {e}")
            return f"⚠️ Unified RAG query failed: {e}"

    # ==========================================================
    # 🧠 Compatibility Method (Old Agents)
    # ==========================================================
    def unified_query(self, question: str, n_results: int = 5):
        """Alias for older agents using unified_query() syntax."""
        try:
            result = self.query_engine.unified_query(question, n_results=n_results)
            return self._format_result(result)
        except Exception as e:
            print(f"⚠️ Context retrieval error: {e}")
            return f"⚠️ Unified query failed: {e}"

    # ==========================================================
    # 🧩 Collection-Specific Query (New Helper)
    # ==========================================================
    def query_all(self, collection_name: str, query_text: str, n_results: int = 5):
        """
        Query a specific RAG collection and return formatted context text.

        Example:
            rag.query_all("inventory", "show me low stock items")
        """
        try:
            if not collection_name:
                return "⚠️ No collection name provided."

            valid_names = list(self.collections.keys())
            if collection_name not in valid_names:
                return f"⚠️ Invalid collection '{collection_name}'. Available: {valid_names}"

            results = self.query_engine.query_single_source(
                collection_name, query_text, n_results=n_results
            )

            return self._format_result(results, domain=collection_name)

        except Exception as e:
            return f"⚠️ query_all error for '{collection_name}': {e}"

    # ==========================================================
    # 🧰 Internal Helper — Format Results
    # ==========================================================
    def _format_result(self, result, domain=None):
        """
        Safely formats various RAG result types into human-readable text.
        Works for dict, list, string, or None responses.
        """
        if result is None:
            return f"No context found{f' in {domain}' if domain else ''}."

        # If it's a dictionary with "documents" or "text" fields
        if isinstance(result, dict):
            if "documents" in result:
                docs = result.get("documents", [])
                if not docs:
                    return f"No documents found in {domain or 'RAG'} context."
                return "\n".join([f"- {d}" for d in docs])
            elif "text" in result:
                return result["text"]

            # Generic key-value flatten
            return "\n".join([f"{k}: {v}" for k, v in result.items()])

        # If it's a list, join entries as bullet points
        if isinstance(result, list):
            if not result:
                return f"No entries found in {domain or 'RAG'}."
            return "\n".join([f"- {r}" for r in result])

        # If it's already a string, return it as-is
        if isinstance(result, str):
            return result.strip()

        # Fallback for unknown result types
        return f"[Unrecognized RAG result type: {type(result)}]"
