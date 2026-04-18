"""
AI_SYSTEM/AGENTS/MANAGER_AGENT/tools/manager_diagnostics.py
------------------------------------------------------------
Health & error diagnostics for all agents based on their logs.
Writes a central diagnostics.json and returns a status summary.
Enhanced for CommandCore v2.1 — includes detailed error recognition
and fix recommendations.
"""

import os, json, re
from datetime import datetime
from typing import Dict, List

# -------------------------------------------------------------
# Paths & Constants
# -------------------------------------------------------------
LOG_DIR = os.path.join("AI_SYSTEM", "MEMORY", "agent_logs")
DIAG_FILE = os.path.join("AI_SYSTEM", "MEMORY", "diagnostics.json")

AGENT_LOGS = {
    "sales":     "sales_agent_log.json",
    "returns":   "return_agent_log.json",
    "inventory": "inventory_agent_log.json",
    "ads":       "ads_agent_log.json",
    # "finance": "finance_agent_log.json",  # future expansion
}

ERROR_PATTERNS = [
    r"❌", r"⚠️", r"Traceback", r"Error:", r"Exception",
    r"ModuleNotFoundError", r"FileNotFoundError",
    r"tokenizing data", r"Failed to initialize RAG", r"csv", r"on_bad_lines",
    r"Timeout", r"runpy", r"ImportError"
]

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _read_json_list(path: str) -> List[dict]:
    """Read JSON array safely."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _find_last_error(entries: List[dict]) -> Dict:
    """Scan log entries backward and return last error snippet."""
    for row in reversed(entries):
        text = (row.get("response") or "") + " " + " ".join(
            [str(v) for v in row.values() if isinstance(v, str)]
        )
        for pat in ERROR_PATTERNS:
            if re.search(pat, text, re.I):
                return {
                    "timestamp": row.get("timestamp"),
                    "pattern": pat,
                    "snippet": text[:800]
                }
    return None


# -------------------------------------------------------------
# 🔍 Diagnose All Agents
# -------------------------------------------------------------
def diagnose_agents() -> Dict:
    """Scan all agent logs and return a summarized health report."""
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agents": {}
    }

    for agent, logname in AGENT_LOGS.items():
        path = os.path.join(LOG_DIR, logname)
        entries = _read_json_list(path)
        last_update = entries[-1]["timestamp"] if entries else None
        last_error = _find_last_error(entries)

        if entries and not last_error:
            status = "healthy"
        elif entries and last_error:
            status = "attention"
        else:
            status = "no_logs"

        # Suggest fix if any error exists
        fix_hint = explain_issue(agent, last_error) if last_error else "No issues detected."

        report["agents"][agent] = {
            "status": status,
            "last_update": last_update,
            "last_error": last_error,
            "suggested_fix": fix_hint
        }

    # Persist diagnostics snapshot
    os.makedirs(os.path.dirname(DIAG_FILE), exist_ok=True)
    try:
        with open(DIAG_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Could not write diagnostics.json: {e}")

    return report


# -------------------------------------------------------------
# 💡 Error Interpretation Layer
# -------------------------------------------------------------
def explain_issue(agent_key: str, last_error: Dict) -> str:
    """Return human-readable cause + recommended fix."""
    if not last_error:
        return "No recent errors detected."

    s = (last_error.get("snippet") or "").lower()

    # --- CSV and data issues ---
    if "tokenizing data" in s or "c error" in s or "csv" in s:
        return (
            "CSV structure or delimiter issue detected — extra commas or bad quoting.\n"
            "🩺 Fix: Ensure CSV rows are properly quoted, or modify loader with `on_bad_lines='skip'` "
            "and `quoting=1` for pandas. Check if the report export matches expected format."
        )

    # --- RAG database / initialization ---
    if "failed to initialize rag" in s:
        return (
            "RAG initialization failed — likely vector DB unavailable or misconfigured.\n"
            "🩺 Fix: Check `AI_SYSTEM/RAG/VECTOR_DB/` path, confirm collection names exist, "
            "and that Chroma/Pinecone connection is active. Then re-run the agent."
        )

    # --- Missing imports or module resolution ---
    if "modulenotfounderror" in s or "importerror" in s:
        return (
            "Python failed to import an AI_SYSTEM module — environment or path issue.\n"
            "🩺 Fix: Ensure you run from the RoboRana root directory, or set `PYTHONPATH` "
            "to include project base. Verify the missing module path physically exists."
        )

    # --- Working directory / subprocess path issue ---
    if "frozen runpy" in s or "run_module_as_main" in s or "cwd" in s:
        return (
            "Module launch failed due to wrong working directory or subprocess context.\n"
            "🩺 Fix: Confirm the live runner launches from the RoboRana root path "
            "and that `AI_SYSTEM` is in the module namespace."
        )

    # --- File not found ---
    if "filenotfounderror" in s or "no such file" in s:
        return (
            "Required file or daily snapshot missing.\n"
            "🩺 Fix: Verify the expected CSV/report file exists under the correct path. "
            "Ensure daily snapshots for PLA, Visibility, Sales, and Returns are generated."
        )

    # --- Timeout / hung process ---
    if "timeout" in s or "timed out" in s:
        return (
            "Agent execution timed out.\n"
            "🩺 Fix: Increase timeout in manager_live_runner or optimize agent logic for lighter queries."
        )

    # --- Permission / encoding ---
    if "permission" in s or "denied" in s:
        return (
            "File or folder permission issue detected.\n"
            "🩺 Fix: Run Python with elevated permissions or adjust OS-level folder access rights."
        )

    # --- Generic fallback ---
    return (
        "Error detected — unknown category.\n"
        "🩺 Fix: Review the stderr or log snippet for more detail, "
        "check CSV integrity, module imports, and RAG connectivity."
    )
