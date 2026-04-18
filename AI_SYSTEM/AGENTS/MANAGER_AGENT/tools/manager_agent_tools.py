"""
AI_SYSTEM/AGENTS/MANAGER_AGENT/tools/manager_agent_tools.py
-----------------------------------------------------------
Build unified context from latest agent logs; enrich with RAG.
Also wires in diagnostics to summarize agent health.
"""

import os, json, re
from typing import List, Dict
from AI_SYSTEM.RAG.QUERY_SYSTEM.unified_query_rag_local import UnifiedQueryRAGLocal
from AI_SYSTEM.AGENTS.MANAGER_AGENT.tools.manager_diagnostics import diagnose_agents

LOG_DIR = os.path.join("AI_SYSTEM", "MEMORY", "agent_logs")

AGENT_LOG_FILES = {
    "sales":     "sales_agent_log.json",
    "returns":   "return_agent_log.json",
    "inventory": "inventory_agent_log.json",
    "ads":       "ads_agent_log.json",
}

def _read_json(path: str) -> List[dict]:
    if not os.path.exists(path): return []
    try:
        with open(path, "r", encoding="utf-8") as f: data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _latest(entries: List[dict], n: int = 2) -> List[dict]:
    return entries[-n:] if entries else []

def _short(s: str, n: int = 1000) -> str:
    return s if len(s) <= n else s[:n] + " …"

def get_manager_context(rag_client, user_query: str, max_entries_per_agent: int = 2) -> str:
    blocks = []

    # Add diagnostics block
    diag = diagnose_agents()
    blocks.append("🩺 Agent Health Snapshot")
    for agent, meta in diag["agents"].items():
        line = f"- {agent}: {meta['status']}"
        if meta.get("last_update"):
            line += f" (updated {meta['last_update']})"
        if meta.get("last_error"):
            line += " — has recent error"
        blocks.append(line)

    # Add latest responses from agents (for context)
    for agent_key, logname in AGENT_LOG_FILES.items():
        entries = _read_json(os.path.join(LOG_DIR, logname))
        latest = _latest(entries, max_entries_per_agent)
        if not latest: continue
        blocks.append(f"\n📘 {agent_key.upper()} — Latest {len(latest)} entr{'y' if len(latest)==1 else 'ies'}")
        for row in latest:
            ts = row.get("timestamp", "unknown")
            txt = _short(row.get("response", "") or "", 900)
            blocks.append(f"- [{ts}] {txt}")

    # RAG enrichment
    try:
        results = rag_client.unified_query(user_query, n_results=5)
        for source, docs in results.items():
            if docs and any(docs):
                preview = "\n".join(docs[:3])
                blocks.append(f"\n📚 RAG Source: {source}\n{preview}")
    except Exception as e:
        blocks.append(f"⚠️ RAG query error: {e}")

    return "\n".join(blocks) if blocks else "No context available."
