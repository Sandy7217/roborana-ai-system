"""
AI_SYSTEM/AGENTS/ADS_AGENT/tools/ads_agent_tools.py
---------------------------------------------------
Combines numeric Ads summary with RAG context (ads_pla + ads_visibility).
"""

from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal
from AI_SYSTEM.AGENTS.ADS_AGENT.tools.ads_data_tools import interpret_ads_query

def get_ads_context(rag_client, user_query: str):
    blocks = []
    # 1) Numeric summary
    try:
        s = interpret_ads_query(user_query)
        t = s["totals"]
        block = (
            f"📣 Ads Numeric Summary\n"
            f"- Period: {s['period_start']} → {s['period_end']}\n"
            f"- Spend: ₹{t['spend']:,} | Clicks: {t['clicks']:,} | Impr: {t['impressions']:,}\n"
            f"- Orders: {t['orders']:,} | Revenue: ₹{t['revenue']:,}\n"
            f"- CTR: {t['ctr_pct']}% | CPC: ₹{t['cpc']} | ROAS: {t['roas']}\n"
        )
        if s["top_skus_by_spend"]:
            block += "\n🏷️ Top 5 SKUs by Spend:\n"
            for row in s["top_skus_by_spend"][:5]:
                block += f"   • {row['sku']}: ₹{row['spend']:,}\n"
        if s["top_skus_by_roas"]:
            block += "\n💹 Top 5 SKUs by ROAS:\n"
            for row in s["top_skus_by_roas"][:5]:
                r = row.get("roas")
                block += f"   • {row['sku']}: ROAS {round(r,2) if r==r else 'NA'} (Rev ₹{row.get('revenue',0):,} / Spend ₹{row.get('spend',0):,})\n"
        blocks.append(block)
    except Exception as e:
        blocks.append(f"⚠️ CSV summary error: {e}")

    # 2) RAG context (searches all collections; ads sets will surface)
    try:
        results = rag_client.unified_query(user_query, n_results=5)
        for source, docs in results.items():
            if docs and any(docs):
                snippet = "\n".join(docs[:3])
                blocks.append(f"\n📘 RAG Source: {source}\n{snippet}")
    except Exception as e:
        blocks.append(f"⚠️ RAG query error: {e}")

    return "\n".join(blocks) if blocks else "No context available."

if __name__ == "__main__":
    rag = UnifiedQueryRAGLocal()
    print(get_ads_context(rag, "top performing skus this month"))
