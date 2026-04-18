# -*- coding: utf-8 -*-
# ================================================
# 📢 Ads / Performance Agent — Hive Mind Integrated v4.0 (Human + Conversational)
# ================================================
import json, os, sys, time, threading
from datetime import datetime

from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.ADS_AGENT.tools.ads_agent_tools import get_ads_context
from AI_SYSTEM.AGENTS.ADS_AGENT.tools.ads_data_tools import interpret_ads_query
from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    summarize_collective_intelligence,
    record_insight,
    record_pattern,
)


# ------------------------------------------------
# 🩺 Safe Print Helper (UTF-8 Safe)
# ------------------------------------------------
def safe_print(*args, **kwargs):
    """UTF-8 safe print for console and Streamlit logs."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        print(msg.encode("ascii", errors="ignore").decode("ascii"), **kwargs)


# ------------------------------------------------
# ⏳ Progress Spinner
# ------------------------------------------------
class Spinner:
    def __init__(self, message="Processing"):
        self.running = False
        self.message = message
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def _spin(self):
        symbols = "|/-\\"
        i = 0
        while self.running:
            sys.stdout.write(f"\r{self.message}... {symbols[i % len(symbols)]}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.12)
        sys.stdout.write("\r" + " " * (len(self.message) + 8) + "\r")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


# ------------------------------------------------
# 📁 Log Configuration
# ------------------------------------------------
LOG_DIR = "AI_SYSTEM/MEMORY/agent_logs"
LOG_FILE = os.path.join(LOG_DIR, "ads_agent_log.json")
QUERY_HISTORY_FILE = "AI_SYSTEM/MEMORY/query_history.json"
os.makedirs(LOG_DIR, exist_ok=True)


def append_json(path, row):
    try:
        data = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        data.append(row)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Log write error: {e}")


# ------------------------------------------------
# 🤖 Ads Agent (Hive Mind Aware + Human Understanding)
# ------------------------------------------------
class AdsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Ads Agent",
            role_prompt=(
                "You are RoboRana’s **Ads & Performance Intelligence Agent**, part of the Hive Mind Collective. "
                "You analyze PLA, visibility, CTR, CPC, ROAS, and revenue attribution. "
                "You understand natural human questions (even Hindi or casual phrases) "
                "and reply like a performance marketing strategist — clear, confident, and conversational. "
                "Correlate ad performance with sales, returns, and inventory patterns using shared Hive intelligence."
            ),
        )

        integrate_shared_logic(self)

        # ✅ Shared Logic Integration
        self.handle_generic_query = getattr(self, "handle_generic_query", None)

        safe_print("🔧 Initializing Unified RAG Brain...")
        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Unified RAG Brain connected.")
        except Exception as e:
            safe_print(f"❌ Failed to initialize RAG: {e}")
            self.rag = None

        # 🧠 Load Hive Mind collective intelligence
        self.hive_summary = summarize_collective_intelligence()
        safe_print("🤝 Connected to Hive Mind Collective.")
        safe_print("🤖 Ads Agent (Hive Mode) initialized and ready.\n")

    # ------------------------------------------------
    # 🧠 Handle Query
    # ------------------------------------------------
    def handle_query(self, query):
        # 🧩 Step 1 — Normalize user input (Hindi/Hinglish → English, fix typos)
        query = self.process_user_input(query)

        spinner = Spinner("📊 Analyzing Ads & Performance Data")
        spinner.start()
        response = ""
        data = {}
        totals = {}
        rag_ctx = ""
        has_ads_data = False
        has_rag_context = False

        try:
            safe_print(f"\n🧠 New Query → {query}\n")

            # Step 2️⃣ — Interpret Ad Performance Data
            try:
                data = interpret_ads_query(query)
                if not isinstance(data, dict):
                    data = {}
                    totals = {}
                else:
                    totals = data.get("totals", {}) or {}
                has_ads_data = bool(totals)
                if has_ads_data:
                    safe_print(f"🧾 Period: {data.get('period_start')} → {data.get('period_end')}")
                    safe_print(
                        f"💰 Spend ₹{totals.get('spend', 0):,} | 🖱️ Clicks {totals.get('clicks', 0)} | 👀 Impr {totals.get('impressions', 0)}"
                    )
                    safe_print(
                        f"🛍️ Orders {totals.get('orders', 0)} | 💵 Rev ₹{totals.get('revenue', 0):,} | 📈 ROAS {totals.get('roas', 0)}\n"
                    )
                else:
                    safe_print("⚠️ No numeric data found in Ads dataset.\n")
            except Exception as e:
                data = {}
                totals = {}
                has_ads_data = False
                safe_print(f"⚠️ Error generating numeric summary: {e}")

            # Step 3️⃣ — Context Gathering
            safe_print("🔍 Fetching RAG + Hive context...\n")
            try:
                rag_ctx = get_ads_context(self.rag, query)
                if rag_ctx is None:
                    rag_ctx = ""
                elif not isinstance(rag_ctx, str):
                    rag_ctx = str(rag_ctx)
                rag_ctx_stripped = rag_ctx.strip()
                has_rag_context = bool(
                    rag_ctx_stripped
                    and not rag_ctx_stripped.startswith("⚠️")
                    and not rag_ctx_stripped.startswith("No context")
                    and not rag_ctx_stripped.startswith("No documents")
                )
            except Exception as e:
                rag_ctx = f"⚠️ Context error: {e}"
                has_rag_context = False

            hive_context = self.hive_summary

            if not has_ads_data and not has_rag_context:
                response = "I could not find enough grounded ads data for this query right now. Please check whether the ads source files and RAG collections are available and up to date."
            else:
                # Step 4️⃣ — Unified Reasoning Prompt
                prompt = f"""
### 🧠 Hive Mind Context
{hive_context}

### 📊 Ads Data Summary
{json.dumps(data, indent=2, default=str)}

### 🧾 RAG Context
{rag_ctx}

### ❓User Query
{query}

Now generate a **clear, conversational performance summary** including:
1️⃣ Key Ad Insights (ROAS, CTR, CPC)
2️⃣ Cross-Agent Correlations (Sales uplift, Return trends, Inventory effects)
3️⃣ Root Causes of Performance Changes
4️⃣ Smart Optimization Recommendations
5️⃣ Actionable Patterns to teach Hive Mind
Use a professional but friendly tone.
"""

                try:
                    response = self.think(prompt)
                except Exception as e:
                    response = f"⚠️ Reasoning error: {e}"

            # Step 5️⃣ — Conversational Postprocessing
            response = self.process_agent_output(query, response)

            # Step 6️⃣ — Logging
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agent": "Ads Agent",
                "query": query,
                "response": response[:4000],
                "period_start": str(data.get("period_start")),
                "period_end": str(data.get("period_end")),
            }
            append_json(LOG_FILE, entry)
            append_json(QUERY_HISTORY_FILE, {"timestamp": entry["timestamp"], "query": query})

            # Step 7️⃣ — Record in Hive Mind
            try:
                record_insight("Ads Agent", response, {"query": query})
                if "roas" in response.lower() and "drop" in response.lower():
                    record_pattern("ROAS decline trend detected", "Ads Agent")
                elif "ctr" in response.lower() and "low" in response.lower():
                    record_pattern("CTR degradation pattern found", "Ads Agent")
                elif "conversion" in response.lower() and "improved" in response.lower():
                    record_pattern("Ad conversion improvement detected", "Ads Agent")
            except Exception as e:
                safe_print(f"⚠️ Hive update error: {e}")

        finally:
            spinner.stop()

        # Step 8️⃣ — Output
        safe_print("📝 Log saved successfully.\n")
        safe_print("💬 ===== Ads Agent (Hive-Enhanced Conversational Response) =====\n")
        safe_print(response)
        safe_print("\n" + "=" * 90 + "\n")
        return response


# ------------------------------------------------
# 🚀 CLI Interface (Auto-Mode for Manager)
# ------------------------------------------------
if __name__ == "__main__":
    safe_print("🚀 Ads Agent (Hive Mind) started")
    agent = AdsAgent()

    auto_mode = any(x in sys.argv for x in ["--auto", "--summary", "--manager"])
    if auto_mode:
        safe_print("🤖 Manager-triggered auto summary mode.\n")
        agent.handle_query("ads performance summary for manager")
        sys.exit(0)

    while True:
        try:
            q = input("🧠 Enter query (or 'exit'): ").strip()
            if q.lower() == "exit":
                safe_print("👋 Exiting Ads Agent...")
                break
            if q:
                agent.handle_query(q)
        except KeyboardInterrupt:
            safe_print("\n👋 Exiting Ads Agent...")
            break
        except Exception as e:
            safe_print(f"⚠️ Error: {e}")
