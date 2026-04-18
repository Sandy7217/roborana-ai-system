# -*- coding: utf-8 -*-
# =========================================================
# 🤖 Hive Mind Core — RoboRana Collective Intelligence System
# Version: 1.1 | Author: Sandeep Rana | Operation: Unified Cortex
# =========================================================

import os, json, time
from datetime import datetime
from threading import Lock

# ---------------------------------------------------------
# 🧠 Configuration
# ---------------------------------------------------------
HIVE_MEMORY_PATH = "AI_SYSTEM/MEMORY/hive_memory.json"
os.makedirs(os.path.dirname(HIVE_MEMORY_PATH), exist_ok=True)
_lock = Lock()  # for safe concurrent access


# ---------------------------------------------------------
# ⚙️ Utility Functions
# ---------------------------------------------------------
def _read_json(path):
    if not os.path.exists(path):
        return {"insights": [], "patterns": [], "corrections": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"insights": [], "patterns": [], "corrections": []}


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _safe_strip(value):
    """Ensures .strip() never fails even if input is None or non-string."""
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return ""
    return value.strip()


# ---------------------------------------------------------
# 🧩 Record Insight
# ---------------------------------------------------------
def record_insight(agent_name: str, insight_text, context: dict = None):
    """
    Record a new analytical insight from any agent.
    Each insight entry includes timestamp, agent, content, and optional context.
    """
    context = context or {}
    with _lock:
        mem = _read_json(HIVE_MEMORY_PATH)
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": _safe_strip(agent_name),
            "insight": _safe_strip(insight_text),
            "context": context,
        }
        mem["insights"].append(entry)
        _write_json(HIVE_MEMORY_PATH, mem)
    prune_hive()
    return True


# ---------------------------------------------------------
# 🧩 Record Pattern or Trend
# ---------------------------------------------------------
def record_pattern(pattern_desc, source_agent: str = None):
    """
    Record recurring patterns or trends identified across agents.
    E.g., "Myntra RTO rate rising since last week"
    """
    with _lock:
        mem = _read_json(HIVE_MEMORY_PATH)
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pattern": _safe_strip(pattern_desc),
            "source": _safe_strip(source_agent),
        }
        mem["patterns"].append(entry)
        _write_json(HIVE_MEMORY_PATH, mem)
    prune_hive()
    return True


# ---------------------------------------------------------
# 🧩 Record Correction (Learning Feedback)
# ---------------------------------------------------------
def record_correction(agent_name: str, correction_text):
    """
    Store manual corrections or feedback to teach RoboRana.
    Example:
      record_correction("Sales Agent", "AOV formula should exclude cancelled orders.")
    """
    with _lock:
        mem = _read_json(HIVE_MEMORY_PATH)
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent": _safe_strip(agent_name),
            "correction": _safe_strip(correction_text),
        }
        mem["corrections"].append(entry)
        _write_json(HIVE_MEMORY_PATH, mem)
    prune_hive()
    return True


# ---------------------------------------------------------
# 🧩 Summarize Collective Insights
# ---------------------------------------------------------
def summarize_collective_intelligence(limit=20) -> str:
    """
    Return a formatted markdown summary of the most recent insights and patterns.
    Used by Manager and all agents to gain context of team intelligence.
    """
    mem = _read_json(HIVE_MEMORY_PATH)
    insights = mem.get("insights", [])[-limit:]
    patterns = mem.get("patterns", [])[-5:]

    text = "### 🧠 Hive Mind Intelligence Summary\n"
    if not insights and not patterns:
        return text + "_No insights recorded yet._"

    if insights:
        text += "\n**Recent Analytical Insights:**\n"
        for i in insights:
            timestamp = i.get("timestamp", "unknown")
            agent = _safe_strip(i.get("agent", "Unknown Agent"))
            insight = _safe_strip(i.get("insight", ""))
            if insight:
                text += f"- ({timestamp}) **{agent}** → {insight}\n"

    if patterns:
        text += "\n**Detected Patterns & Trends:**\n"
        for p in patterns:
            timestamp = p.get("timestamp", "unknown")
            pattern = _safe_strip(p.get("pattern", ""))
            src = _safe_strip(p.get("source", ""))
            src_text = f" (from {src})" if src else ""
            if pattern:
                text += f"- ({timestamp}) {pattern}{src_text}\n"

    return text


# ---------------------------------------------------------
# 🧩 Memory Maintenance
# ---------------------------------------------------------
def prune_hive(max_entries=500):
    """
    Prevents Hive memory from growing indefinitely.
    Keeps the most recent entries only.
    """
    with _lock:
        mem = _read_json(HIVE_MEMORY_PATH)
        mem["insights"] = mem.get("insights", [])[-max_entries:]
        mem["patterns"] = mem.get("patterns", [])[-max_entries // 5:]
        mem["corrections"] = mem.get("corrections", [])[-max_entries // 10:]
        _write_json(HIVE_MEMORY_PATH, mem)


# ---------------------------------------------------------
# ✅ Example Use
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🧠 Hive Mind Core initialized.")
    record_insight("Sales Agent", "Top SKU sales increased by 12% on Myntra last week.")
    record_pattern("RTO rate increasing for festive kurtas", "Returns Agent")
    print(summarize_collective_intelligence())
