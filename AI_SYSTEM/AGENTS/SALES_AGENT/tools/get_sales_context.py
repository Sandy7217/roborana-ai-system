# ==========================================================
# 🧠 get_sales_context.py — v2.7 Stable (RoboRana AI)
# Combines CSV + RAG insight layers for Sales Agent
# ==========================================================
import os
from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal
from AI_SYSTEM.AGENTS.SALES_AGENT.tools.sales_data_tools import interpret_query  # Local CSV logic


def get_sales_context(rag_client, user_query: str):
    """
    Fetch contextual information for Sales Agent queries.
    Combines:
    1. Local sales data insights (from Sales_Master.csv)
    2. RAG-based context from vector database
    """
    try:
        print(f"\n🔍 Fetching combined context for Sales Agent — Query: {user_query}\n")
        combined_context = []

        # 1️⃣ LOCAL SALES DATA CONTEXT
        try:
            csv_summary = interpret_query(user_query)
            if csv_summary and isinstance(csv_summary, dict):
                if "total_sales" in csv_summary:
                    local_block = (
                        f"💰 Local CSV Summary:\n"
                        f"- Period: Last {csv_summary.get('days', '?')} days\n"
                        f"- Total Sales: ₹{csv_summary.get('total_sales', 0):,}\n"
                        f"- Orders: {csv_summary.get('total_orders', 0):,}\n"
                        f"- Avg Order Value: ₹{csv_summary.get('avg_order_value', 0):,}\n"
                    )
                    combined_context.append(local_block)
                elif "info" in csv_summary:
                    combined_context.append(f"ℹ️ {csv_summary['info']}")
                else:
                    combined_context.append(f"⚠️ Unexpected CSV summary structure: {csv_summary}")
            else:
                combined_context.append("⚠️ No valid CSV summary returned.")
        except FileNotFoundError as e:
            combined_context.append(f"❌ CSV file missing: {e}")
        except Exception as e:
            combined_context.append(f"⚠️ CSV summary error: {type(e).__name__} — {e}")

        # 2️⃣ RAG CONTEXT
        try:
            results = rag_client.unified_query(user_query, n_results=5)
            if results:
                for source, docs in results.items():
                    if docs and any(docs):
                        docs_preview = "\n".join(docs[:3])  # top 3 snippets per source
                        combined_context.append(f"\n📘 RAG Source: {source}\n{docs_preview}")
            else:
                combined_context.append("⚠️ No relevant documents found in RAG sources.")
        except Exception as e:
            combined_context.append(f"⚠️ RAG query error: {type(e).__name__} — {e}")

        # Combine all sources
        context = "\n".join(combined_context).strip() if combined_context else "No data found from CSV or RAG."
        return context or "Context unavailable."

    except Exception as e:
        print(f"⚠️ Context retrieval error: {type(e).__name__} — {e}")
        return "Context unavailable due to an error."


# ----------------------------------------------------------
# 🔬 Test Mode
# ----------------------------------------------------------
if __name__ == "__main__":
    print("🧠 Testing Sales Agent Combined Context Fetcher...\n")
    rag = UnifiedQueryRAGLocal()
    test_query = "total sales in last 7 days"
    context = get_sales_context(rag, test_query)
    print("\n✅ Retrieved Context:\n", context)
