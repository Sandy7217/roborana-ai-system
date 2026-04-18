# -*- coding: utf-8 -*-
# ================================================
# 🧠 Manager Agent — RoboRana v3.7
# (Hive Smart Router + Inventory Forecast Integration)
# ================================================
import os, json, sys, threading, time, itertools, subprocess
from datetime import datetime

from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.MANAGER_AGENT.tools.manager_agent_tools import get_manager_context
from AI_SYSTEM.AGENTS.MANAGER_AGENT.tools.manager_diagnostics import diagnose_agents
from AI_SYSTEM.AGENTS.MANAGER_AGENT.tools.manager_subprocess_runner import run_agent_live
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    summarize_collective_intelligence,
    record_insight,
    record_pattern,
)
from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic
from AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent import InventoryAgent  # 🔗 NEW

# ------------------------------------------------
# 🧩 Language Understanding Layer
# ------------------------------------------------
from langdetect import detect
from deep_translator import GoogleTranslator
from spellchecker import SpellChecker

spell = SpellChecker(distance=1)

COMMON_SHORTCUTS = {
    "sku": "product",
    "rev": "revenue",
    "qty": "quantity",
    "sel": "sale",
    "wek": "week",
    "bro": "",
    "batao": "show",
    "karo": "do",
    "dekh": "show",
}

# ------------------------------------------------
# 🌍 Force UTF-8 mode for Windows
# ------------------------------------------------
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# ------------------------------------------------
# 🩺 Safe Print Helper
# ------------------------------------------------
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        except Exception:
            pass

# ------------------------------------------------
# ⚙️ Configuration
# ------------------------------------------------
LOG_DIR = "AI_SYSTEM/MEMORY/agent_logs"
LOG_FILE = os.path.join(LOG_DIR, "manager_agent_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

AGENT_KEYS = ["sales", "returns", "inventory", "ads"]

# ------------------------------------------------
# 🧩 JSON Append Utility
# ------------------------------------------------
def append_json(path, data):
    try:
        buf = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    buf = json.load(f)
                except Exception:
                    buf = []
        buf.append(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(buf, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Log write error: {e}")

# ------------------------------------------------
# 🔄 Progress Spinner
# ------------------------------------------------
def progress_spinner(stop_event, active_agents, progress):
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    total = len(active_agents)
    while not stop_event.is_set():
        completed = progress["done"]
        percent = int((completed / total) * 100)
        running = ", ".join(active_agents[:total - completed])
        safe_print(
            f"\r⏳ Running agents: {running or 'None'} | Progress: {percent}% {next(spinner)}",
            end="",
            flush=True,
        )
        time.sleep(0.15)
    safe_print("\r✅ All agents completed successfully.                             ")

# ------------------------------------------------
# 🧩 Language Normalizer
# ------------------------------------------------
def normalize_human_text(text: str) -> str:
    original = text
    try:
        lang = detect(text)
        if lang != "en":
            text = GoogleTranslator(source=lang, target="en").translate(text)
    except Exception:
        pass

    words = []
    for w in text.split():
        w_low = w.lower()
        if w_low in COMMON_SHORTCUTS:
            repl = COMMON_SHORTCUTS[w_low]
            if repl:
                words.append(repl)
        else:
            corrected = spell.correction(w_low)
            words.append(corrected or w_low)

    normalized = " ".join(words)
    normalized = (
        normalized.replace(" pls ", " please ")
        .replace(" bro ", " ")
        .replace(" bata ", " tell ")
    )
    safe_print(f"🧩 NLU normalized: {original!r} → {normalized!r}")
    return normalized

# ------------------------------------------------
# 🧠 Smart Summarizer
# ------------------------------------------------
def smart_summarize_context(agent, text: str, label="RAG Context", max_chars=7000):
    if not isinstance(text, str):
        return text
    if len(text) <= max_chars:
        return text

    safe_print(f"🧩 Smart Summarizer → {label} too long ({len(text)} chars), compressing...")
    sample = text[:16000]
    summarize_prompt = f"""
    Summarize the following {label} into clear, concise points.
    Focus on:
    - Key insights, metrics, and patterns
    - Performance highlights or risks
    - Actionable business takeaways
    Output under 2000 words, formatted cleanly in markdown.
    --- BEGIN {label} ---
    {sample}
    --- END {label} ---
    """

    try:
        compressed = agent.think(summarize_prompt)
        safe_print(f"✅ {label} summarized successfully ({len(compressed)} chars).")
        return compressed
    except Exception as e:
        safe_print(f"⚠️ Smart summarizer failed ({label}): {e}")
        return text[:max_chars] + "\n\n[...truncated due to summarization error...]"

# ------------------------------------------------
# 🤖 Manager Agent
# ------------------------------------------------
class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Manager Agent",
            role_prompt=(
                "You are RoboRana’s **Manager Agent (CommandCore)** — "
                "the central intelligence that leads Sales, Returns, Inventory, and Ads agents. "
                "You analyze, coordinate, and synthesize data using the Hive Mind collective memory, "
                "RAG intelligence, and diagnostic insights. You act like a COO — executive, strategic, and data-driven."
            ),
        )

        if not getattr(self, "_shared_logic_injected", False):
            try:
                integrate_shared_logic(self)
                setattr(self, "_shared_logic_injected", True)
            except Exception as e:
                safe_print(f"⚠️ Failed to integrate shared logic: {e}")

        # 🧩 Connect Inventory Agent
        self.inventory_agent = InventoryAgent()
        safe_print("🧩 Manager connected to Inventory Agent successfully.")

        safe_print("🔧 Initializing Unified RAG Brain...")
        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Unified RAG Brain connected.")
        except Exception as e:
            safe_print(f"❌ Failed to initialize RAG: {e}")
            self.rag = None

        self.hive_summary = summarize_collective_intelligence()
        safe_print("🤖 Manager Agent (Hive Mode) ready.\n")

    # ------------------------------------------------
    def _detect_live_triggers(self, query: str):
        q = query.lower()
        wants_live = any(k in q for k in ["refresh", "recalculate", "rerun", "update", "latest", "live", "run "])
        targets = [k for k in AGENT_KEYS if k in q]
        if "all" in q or "overall" in q:
            targets = AGENT_KEYS.copy()
        return wants_live, list(dict.fromkeys(targets))

    def _maybe_run_agents(self, query: str):
        wants_live, targets = self._detect_live_triggers(query)
        if not wants_live or not targets:
            return []
        safe_print(f"⚡ Live mode triggered → Running agents: {targets}")
        outputs, threads = {}, []
        stop_event = threading.Event()
        progress = {"done": 0}

        def _runner(agent_key):
            outputs[agent_key] = run_agent_live(agent_key, query)
            progress["done"] += 1

        for key in targets:
            t = threading.Thread(target=_runner, args=(key,))
            t.start()
            threads.append(t)

        spinner_thread = threading.Thread(target=progress_spinner, args=(stop_event, targets, progress), daemon=True)
        spinner_thread.start()

        for t in threads:
            t.join()
        stop_event.set()
        spinner_thread.join()
        safe_print("")
        for key, result in outputs.items():
            status = "✅ OK" if result.get("ok") else "❌ FAIL"
            safe_print(f"   • {key.upper()}: {status} (code={result.get('code')})")
        return list(outputs.items())

    # ------------------------------------------------
    def handle_query(self, query: str):
        safe_print(f"\n🧠 New Manager Query → {query}\n")
        query = normalize_human_text(query)
        q = query.lower().strip()

        # 🔮 Inventory forecast logic
        if any(k in q for k in ["inventory", "forecast", "replenish", "stock plan", "reorder"]):
            safe_print("📦 Manager delegating inventory forecast task...")
            forecast_response = self.inventory_agent.handle_query(query)
            combined = f"""
🧭 **Manager’s Consolidated Insight**
──────────────────────────────
{forecast_response}

🧩 **Manager’s Note:** Based on these projections, align procurement and marketing with stock availability.
I can also compare sales and returns to refine next quarter’s buy plan if needed.
"""
            safe_print("\n💬 ===== Manager (Forecast Integration) Response =====\n")
            safe_print(combined)
            safe_print("\n" + "=" * 90 + "\n")
            return combined

        # 🔍 Standard multi-agent logic continues
        live_runs = self._maybe_run_agents(query)
        diag = diagnose_agents()
        safe_print("\n📦 Aggregating multi-agent context from Hive + RAG...\n")

        try:
            ctx = get_manager_context(self.rag, query)
        except Exception as e:
            ctx = f"⚠️ Context fetch error: {e}"

        ctx = smart_summarize_context(self, ctx, "RAG Context", 7000)
        self.hive_summary = smart_summarize_context(self, self.hive_summary, "Hive Summary", 7000)

        prompt = (
            f"### 🧠 Collective Hive Intelligence\n{self.hive_summary}\n\n"
            f"### 📚 RAG Context\n{ctx}\n\n"
            f"### 🧩 Diagnostics Snapshot\n{json.dumps(diag, indent=2)}\n\n"
            f"### ❓User Query\n{query}\n\n"
            "Now generate a **unified executive summary** including:\n"
            "1️⃣ Collective Snapshot (Sales / Returns / Inventory / Ads)\n"
            "2️⃣ Detected Cross-Agent Patterns\n"
            "3️⃣ Key Wins & Business Risks\n"
            "4️⃣ 48-Hour Action Plan\n"
            "5️⃣ Managerial Recommendations.\n"
        )

        try:
            response = self.think(prompt)
        except Exception as e:
            response = f"⚠️ Reasoning error: {e}"

        entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "agent": "Manager Agent", "query": query, "response": response[:4000]}
        append_json(LOG_FILE, entry)

        try:
            record_insight("Manager Agent", response, {"query": query})
        except Exception as e:
            safe_print(f"⚠️ Hive Mind update failed: {e}")

        safe_print("\n📝 Log saved → manager_agent_log.json\n")
        safe_print("\n💬 ===== Manager Agent (Hive-Integrated) Executive Brief =====\n")
        safe_print(response)
        safe_print("\n" + "=" * 90 + "\n")
        return response

# ------------------------------------------------
def main():
    safe_print("🚀 Manager Agent (Hive-Integrated) started")
    agent = ManagerAgent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = agent.handle_query(query)
        safe_print(result)
        return

    if not sys.stdin.isatty():
        query = sys.stdin.read().strip()
        if query:
            result = agent.handle_query(query)
            safe_print(result)
        return

    while True:
        try:
            q = input("🧠 Enter a query (or 'exit'): ").strip()
            if q.lower() == "exit":
                safe_print("👋 Exiting Manager Agent...")
                break
            if q:
                agent.handle_query(q)
        except KeyboardInterrupt:
            safe_print("\n👋 Exiting Manager Agent...")
            break
        except Exception as e:
            safe_print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    main()
