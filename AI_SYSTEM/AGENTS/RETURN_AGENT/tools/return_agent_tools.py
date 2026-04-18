"""
AI_SYSTEM/AGENTS/RETURN_AGENT/tools/return_agent_tools.py
---------------------------------------------------------
Combines Return CSV analysis (updated v2 logic) with RAG context
for advanced query reasoning inside RoboRana Return Agent.
"""

import os
from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal
# ✅ Use the upgraded code now located directly in return_data_tools.py
from AI_SYSTEM.AGENTS.RETURN_AGENT.tools.return_data_tools import interpret_return_query

def get_return_context(rag_client, user_query: str):
    """
    Fetch contextual information for Return Agent queries.
    Combines:
    1️⃣ Local return data insights (from Return_Master.csv)
    2️⃣ RAG-based contextual knowledge from vector DB
    """
    try:
        print(f"\n🔍 Fetching combined context for Return Agent — Query: {user_query}\n")
        combined_context = []

        # -----------------------------------------------------
        # 1️⃣ LOCAL RETURN DATA CONTEXT (Numeric Summary)
        # -----------------------------------------------------
        try:
            csv_summary = interpret_return_query(user_query)
            if csv_summary and "total_orders" in csv_summary:
                local_block = (
                    f"📦 Local Return Summary:\n"
                    f"- Period: {csv_summary['period_start']} → {csv_summary['period_end']}\n"
                    f"- Total Returns: {csv_summary['total_orders']:,}\n"
                    f"- Total Quantity: {csv_summary['total_qty']:,}\n"
                    f"- Total Value: ₹{csv_summary['total_value']:,}\n"
                    f"- Avg Return Value: ₹{csv_summary['avg_value']:,}\n"
                )

                # Channel breakdown
                if csv_summary.get("channel_summary"):
                    local_block += "\n🌐 Channel Breakdown:\n"
                    for ch, val in csv_summary["channel_summary"].items():
                        local_block += f"   • {ch}: ₹{val:,.0f}\n"

                # Top SKUs
                if csv_summary.get("top_skus"):
                    local_block += "\n🏷️ Top 5 Returned SKUs:\n"
                    for item in csv_summary["top_skus"][:5]:
                        sku = item.get("product_sku_code", "N/A")
                        qty = item.get("qty", 0)
                        total = item.get("total", 0)
                        local_block += f"   • {sku} → Qty: {qty} | ₹{total:,.0f}\n"

                combined_context.append(local_block)

            elif "info" in csv_summary:
                combined_context.append(f"ℹ️ {csv_summary['info']}")

        except Exception as e:
            combined_context.append(f"⚠️ CSV summary error: {e}")

        # -----------------------------------------------------
        # 2️⃣ RAG CONTEXT
        # -----------------------------------------------------
        try:
            results = rag_client.unified_query(user_query, n_results=5)
            for source, docs in results.items():
                if docs and any(docs):
                    docs_preview = "\n".join(docs[:3])  # show top 3 snippets per source
                    combined_context.append(f"\n📘 RAG Source: {source}\n{docs_preview}")
        except Exception as e:
            combined_context.append(f"⚠️ RAG query error: {e}")

        # -----------------------------------------------------
        # Combine All Context
        # -----------------------------------------------------
        context = "\n".join(combined_context) if combined_context else "No context found from CSV or RAG."
        return context

    except Exception as e:
        print(f"⚠️ Context retrieval error: {e}")
        return "Context unavailable due to an error."


# -----------------------------------------------------
# 🧪 Local Test
# -----------------------------------------------------
if __name__ == "__main__":
    print("🧠 Testing Return Agent Context Fetcher...\n")
    rag = UnifiedQueryRAGLocal()
    test_query = "returns in last 7 days"
    context = get_return_context(rag, test_query)
    print("\n✅ Retrieved Context:\n", context)
