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
    except Exception:
        try:
            msg = " ".join(str(a) for a in args)
            print(msg)
        except Exception:
            pass


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
MAX_LOG_ENTRIES = 1000
os.makedirs(LOG_DIR, exist_ok=True)


def append_json(path, row):
    try:
        data = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        data.append(row)
        data = data[-MAX_LOG_ENTRIES:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Log write error: {e}")


def _should_use_spinner():
    return sys.stdout is not None and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def normalize_ads_response(response):
    if response is None:
        return {
            "status": "error",
            "data": {},
            "message": "Ads agent returned None"
        }

    if isinstance(response, dict):
        return {
            "status": response.get("status", "success"),
            "data": response.get("data", response),
            "message": response.get("message", "")
        }

    return {
        "status": "success",
        "data": {"raw_output": str(response)},
        "message": ""
    }


def build_ads_fallback_summary(query, data):
    safe_data = data if isinstance(data, dict) else {}
    totals = safe_data.get("totals", {}) or {}
    if isinstance(totals, dict) and totals:
        spend = totals.get("spend", 0)
        clicks = totals.get("clicks", 0)
        impressions = totals.get("impressions", 0)
        orders = totals.get("orders", 0)
        revenue = totals.get("revenue", 0)
        roas = totals.get("roas", 0)
        return (
            f"For the selected ads period, spend was ₹{spend:,}, clicks were {clicks}, "
            f"impressions were {impressions}, orders were {orders}, revenue was ₹{revenue:,}, "
            f"and ROAS was {roas}."
        )
    return "I could not find enough grounded ads data for this query right now. Please check whether the ads source files and RAG collections are available and up to date."


def detect_ads_domain_scope(query: str):
    q = (query or "").lower().strip()

    ads_keywords = [
        "ads", "ad", "campaign", "campaigns", "pla", "visibility",
        "roas", "ctr", "cpc", "clicks", "impressions", "spend",
        "ad spend", "ads spend", "marketing spend", "ad revenue"
    ]

    sales_keywords = [
        "sales", "revenue", "orders", "sold", "gmv", "aov"
    ]

    inventory_keywords = [
        "inventory", "stock", "replenish", "reorder", "stockout", "stock out"
    ]

    returns_keywords = [
        "return", "returns", "rto", "refund", "exchange"
    ]

    finance_keywords = [
        "profit", "margin", "payout", "settlement", "finance"
    ]

    if any(k in q for k in ads_keywords):
        return "ads"
    if any(k in q for k in inventory_keywords):
        return "inventory"
    if any(k in q for k in returns_keywords):
        return "returns"
    if any(k in q for k in finance_keywords):
        return "finance"
    if any(k in q for k in sales_keywords):
        return "sales"

    return "unknown"


def build_ads_redirect_response(scope: str) -> str:
    if scope == "sales":
        return "This looks like a Sales question, not an Ads question. Please ask the Sales Agent for an accurate answer."
    if scope == "inventory":
        return "This looks like an Inventory question. Please ask the Inventory Agent for the right analysis."
    if scope == "returns":
        return "This seems related to Returns. Please ask the Returns Agent for a precise answer."
    if scope == "finance":
        return "This looks like a Finance question. Please ask the Finance Agent if available, or use the Manager Agent."
    return "This does not look clearly ads-related. Please ask an ads-specific question, or use the Manager Agent for cross-functional help."


def classify_ads_query(query: str):
    q = (query or "").lower().strip()

    if not q:
        return {"mode": "unclear", "target": None}

    broad_keywords = [
        "summary", "full summary", "analyze", "analysis", "insights",
        "recommendation", "recommendations", "deep dive", "performance",
        "root cause", "overall", "all metrics", "full report"
    ]

    comparison_keywords = [
        "compare", "vs", "versus", "difference", "better than"
    ]

    top_keywords = [
        "top", "best", "highest", "lowest", "worst"
    ]

    metric_keywords = {
        "spend": ["spend", "ad spend", "ads spend", "marketing spend", "cost"],
        "revenue": ["revenue", "ad revenue", "sales from ads"],
        "roas": ["roas", "return on ad spend"],
        "ctr": ["ctr", "click through rate", "click-through rate"],
        "cpc": ["cpc", "cost per click"],
        "clicks": ["clicks", "total clicks"],
        "impressions": ["impressions", "views"],
        "orders": ["orders", "ad orders", "conversions"]
    }

    if any(k in q for k in broad_keywords):
        return {"mode": "broad_summary", "target": None}

    if any(k in q for k in comparison_keywords):
        matched = []
        for metric, keywords in metric_keywords.items():
            if any(k in q for k in keywords):
                matched.append(metric)
        return {"mode": "comparison", "target": matched}

    if any(k in q for k in top_keywords):
        return {"mode": "top_item", "target": None}

    matched = []
    for metric, keywords in metric_keywords.items():
        if any(k in q for k in keywords):
            matched.append(metric)

    if len(matched) == 1:
        return {"mode": "single_metric", "target": matched[0]}

    if len(matched) > 1:
        return {"mode": "comparison", "target": matched}

    vague_patterns = [
        "ads",
        "how are ads",
        "what about ads",
        "tell me about ads",
        "show ads"
    ]
    if q in vague_patterns or len(q.split()) <= 2:
        return {"mode": "unclear", "target": None}

    return {"mode": "broad_summary", "target": None}


def build_single_metric_response(metric: str, data: dict) -> str:
    safe_data = data if isinstance(data, dict) else {}
    totals = safe_data.get("totals", {}) or {}
    period_start = safe_data.get("period_start")
    period_end = safe_data.get("period_end")

    def period_text():
        if period_start or period_end:
            return f" for {period_start} to {period_end}"
        return ""

    if metric == "spend":
        return f"Ads spend was ₹{totals.get('spend', 0):,}{period_text()}."
    if metric == "revenue":
        return f"Ad revenue was ₹{totals.get('revenue', 0):,}{period_text()}."
    if metric == "roas":
        return f"ROAS was {totals.get('roas', 0)}{period_text()}."
    if metric == "ctr":
        return f"CTR was {totals.get('ctr', 0)}{period_text()}."
    if metric == "cpc":
        return f"CPC was ₹{totals.get('cpc', 0):,}{period_text()}."
    if metric == "clicks":
        return f"Total clicks were {totals.get('clicks', 0)}{period_text()}."
    if metric == "impressions":
        return f"Total impressions were {totals.get('impressions', 0)}{period_text()}."
    if metric == "orders":
        return f"Orders attributed to ads were {totals.get('orders', 0)}{period_text()}."

    return build_ads_fallback_summary("", data)


def build_metric_comparison_response(metrics, data: dict) -> str:
    if not metrics:
        return "Please tell me exactly which ads metrics you want compared, for example spend vs revenue, ROAS vs CTR, or clicks vs impressions."

    safe_data = data if isinstance(data, dict) else {}
    totals = safe_data.get("totals", {}) or {}
    period_start = safe_data.get("period_start")
    period_end = safe_data.get("period_end")

    label_map = {
        "spend": f"Spend: ₹{totals.get('spend', 0):,}",
        "revenue": f"Revenue: ₹{totals.get('revenue', 0):,}",
        "roas": f"ROAS: {totals.get('roas', 0)}",
        "ctr": f"CTR: {totals.get('ctr', 0)}",
        "cpc": f"CPC: ₹{totals.get('cpc', 0):,}",
        "clicks": f"Clicks: {totals.get('clicks', 0)}",
        "impressions": f"Impressions: {totals.get('impressions', 0)}",
        "orders": f"Orders: {totals.get('orders', 0)}",
    }

    parts = [label_map[m] for m in metrics if m in label_map]

    period_text = ""
    if period_start or period_end:
        period_text = f" for {period_start} to {period_end}"

    if parts:
        return f"{' | '.join(parts)}{period_text}."
    return "I could not identify the exact ads metrics you want compared. Please rephrase your question."


def build_ads_clarification_response() -> str:
    return (
        "Please tell me exactly what you want from ads data. "
        "For example: ads spend, ROAS, CTR, revenue, clicks, impressions, orders, comparison, or full performance summary."
    )


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

        # ✅ Shared logic hook reserved for future generic fallback paths.
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
        spinner = Spinner("📊 Analyzing Ads & Performance Data")
        use_spinner = _should_use_spinner()
        if use_spinner:
            spinner.start()
        response = ""
        final_response = ""
        data = {}
        totals = {}
        rag_ctx = ""
        has_ads_data = False
        has_rag_context = False
        query_info = {"mode": "broad_summary", "target": None}
        domain_scope = "unknown"
        response_source = "unknown"

        try:
            # 🧩 Step 1 — Normalize user input (Hindi/Hinglish → English, fix typos)
            original_query = query
            process_user_input_fn = getattr(self, "process_user_input", None)
            if callable(process_user_input_fn):
                try:
                    query = process_user_input_fn(query)
                except (TypeError, AttributeError) as e:
                    # Safety fallback for downstream intent parsing failures in shared logic
                    if "NoneType" in str(e) and "subscriptable" in str(e):
                        safe_print("⚠️ Intent parsing failed; falling back to raw query.")
                        query = original_query
                    else:
                        query = original_query
            else:
                query = original_query

            if query is None:
                query = original_query
            if not isinstance(query, str):
                query = str(query)

            safe_print(f"\n🧠 New Query → {query}\n")
            domain_scope = detect_ads_domain_scope(query)
            safe_print(f"🎯 Domain scope detected: {domain_scope}")

            if domain_scope not in ("ads", "unknown"):
                response = build_ads_redirect_response(domain_scope)
                response_source = "deterministic"
            else:
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

                query_info = classify_ads_query(query)

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
                    response_source = "deterministic"
                elif query_info.get("mode") == "unclear":
                    response = build_ads_clarification_response()
                    response_source = "deterministic"
                elif query_info.get("mode") == "single_metric" and has_ads_data:
                    response = build_single_metric_response(query_info.get("target"), data)
                    response_source = "deterministic"
                elif query_info.get("mode") == "comparison" and has_ads_data:
                    response = build_metric_comparison_response(query_info.get("target"), data)
                    response_source = "deterministic"
                elif query_info.get("mode") == "top_item":
                    response = "Please specify what you want ranked in ads, for example top spend SKU, top ROAS SKU, highest clicks, or lowest CTR."
                    response_source = "deterministic"
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
                        response_source = "llm"
                        safe_print(f"DEBUG think() type={type(response)} value={repr(response)[:500]}")
                    except Exception as e:
                        response = f"⚠️ Reasoning error: {e}"
                        response_source = "deterministic"

                    if response is None:
                        safe_print("⚠️ think() returned None; using deterministic ads fallback summary.")
                        response = build_ads_fallback_summary(query, data)
                        response_source = "deterministic"
                    elif isinstance(response, str) and not response.strip():
                        safe_print("⚠️ think() returned blank text; using deterministic ads fallback summary.")
                        response = build_ads_fallback_summary(query, data)
                        response_source = "deterministic"

            # Step 5️⃣ — Conversational Postprocessing
            raw_reasoning_response = response
            process_agent_output_fn = getattr(self, "process_agent_output", None)

            if callable(process_agent_output_fn) and response_source == "llm":
                try:
                    processed_response = process_agent_output_fn(query, response)
                    safe_print(f"DEBUG process_agent_output() type={type(processed_response)} value={repr(processed_response)[:500]}")

                    if processed_response is None:
                        safe_print("⚠️ process_agent_output returned None; using raw reasoning response.")
                        response = raw_reasoning_response

                    elif isinstance(processed_response, str) and not processed_response.strip():
                        safe_print("⚠️ process_agent_output returned blank text; using raw reasoning response.")
                        response = raw_reasoning_response

                    elif isinstance(processed_response, str) and any(
                        failure_text in processed_response.lower()
                        for failure_text in [
                            "i could not generate",
                            "unable to generate",
                            "sorry, i couldn't",
                            "could not process",
                            "something went wrong",
                        ]
                    ):
                        safe_print("⚠️ process_agent_output returned generic failure text; using raw reasoning response.")
                        response = raw_reasoning_response

                    else:
                        response = processed_response

                except (TypeError, AttributeError) as e:
                    if "NoneType" in str(e) and "subscriptable" in str(e):
                        safe_print("⚠️ Output postprocessing fallback triggered.")
                        response = raw_reasoning_response if isinstance(raw_reasoning_response, str) else str(raw_reasoning_response)
                    else:
                        safe_print(f"⚠️ Output postprocessing skipped: {e}")
            final_response = response

            # Step 6️⃣ — Logging
            safe_data = data if isinstance(data, dict) else {}
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agent": "Ads Agent",
                "query": query,
                "response": final_response[:4000],
                "period_start": str(safe_data.get("period_start")),
                "period_end": str(safe_data.get("period_end")),
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

        except Exception as e:
            safe_print(f"⚠️ Unexpected Ads Agent error: {e}")
            response = f"I hit an unexpected error while analyzing ads data: {e}"
            final_response = response
        finally:
            if use_spinner:
                spinner.stop()

        if not final_response:
            final_response = response if isinstance(response, str) and response else "I hit an unexpected ads-agent state with no final response."

        # Step 8️⃣ — Output
        safe_print("📝 Log saved successfully.\n")
        safe_print("💬 ===== Ads Agent (Hive-Enhanced Conversational Response) =====\n")
        safe_print(final_response)
        safe_print("\n" + "=" * 90 + "\n")
        return final_response

    def handle_query_normalized(self, query):
        raw = self.handle_query(query)
        return normalize_ads_response(raw)


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
