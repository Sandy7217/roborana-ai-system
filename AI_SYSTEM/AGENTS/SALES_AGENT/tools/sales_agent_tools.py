import os
from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal
from AI_SYSTEM.AGENTS.SALES_AGENT.tools.sales_data_tools import interpret_query  # 🆕 CSV logic

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
            if csv_summary and "total_sales" in csv_summary:
                local_block = (
                    f"💰 Local CSV Summary:\n"
                    f"- Period: Last {csv_summary['days']} days\n"
                    f"- Total Sales: ₹{csv_summary['total_sales']:,}\n"
                    f"- Orders: {csv_summary['total_orders']:,}\n"
                    f"- Avg Order Value: ₹{csv_summary['avg_order_value']:,}\n"
                )
                combined_context.append(local_block)
            elif "info" in csv_summary:
                combined_context.append(f"ℹ️ {csv_summary['info']}")
        except Exception as e:
            combined_context.append(f"⚠️ CSV summary error: {e}")

        # 2️⃣ RAG CONTEXT
        try:
            results = rag_client.unified_query(user_query, n_results=5)
            for source, docs in results.items():
                if docs and any(docs):
                    docs_preview = "\n".join(docs[:3])  # top 3 snippets per source
                    combined_context.append(f"\n📘 RAG Source: {source}\n{docs_preview}")
        except Exception as e:
            combined_context.append(f"⚠️ RAG query error: {e}")

        # Combine all sources
        context = "\n".join(combined_context) if combined_context else "No data found from CSV or RAG."
        return context

    except Exception as e:
        print(f"⚠️ Context retrieval error: {e}")
        return "Context unavailable due to an error."


# Optional: direct test mode
if __name__ == "__main__":
    print("🧠 Testing Sales Agent Combined Context Fetcher...\n")
    rag = UnifiedQueryRAGLocal()
    test_query = "total sales in last 7 days"
    context = get_sales_context(rag, test_query)
    print("\n✅ Retrieved Context:\n", context)
