# -*- coding: utf-8 -*-
# ================================================
# 🤖 Sales Agent — Hive Mind Integrated (v4.5 Reflex-Integrated + GPT Reasoner Fallback)
# ================================================
import json
import os
import sys
import time
import threading
import pandas as pd
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from AI_SYSTEM.CORE_UTILS.style_logic import add_style_column, summarize_by_style
from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.SALES_AGENT.tools.sales_data_tools import interpret_query
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    record_insight,
    record_pattern,
    summarize_collective_intelligence,
)

# ✅ NEW IMPORTS
from AI_SYSTEM.CORE_UTILS.column_schema import COLUMN_MAP, DATE_FORMATS
from AI_SYSTEM.CORE_UTILS.data_column_mapper import validate_dataframe
from AI_SYSTEM.CORE_UTILS.gpt_reasoner import gpt_reason_interpretation  # 🧠 GPT Fallback Layer

# ------------------------------------------------
# 🩺 Safe Print Helper
# ------------------------------------------------
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        print(msg.encode("ascii", errors="ignore").decode("ascii"), **kwargs)

# ------------------------------------------------
# ⏳ Spinner
# ------------------------------------------------
class Spinner:
    def __init__(self, message="Processing"):
        self.running = False
        self.message = message
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def _spin(self):
        while self.running:
            for c in "|/-\\":
                sys.stdout.write(f"\r{self.message}... {c}")
                sys.stdout.flush()
                time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 5) + "\r")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# ------------------------------------------------
# 🧠 Semantic Intent Detector
# ------------------------------------------------
class IntentDetector:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.intent_map = {
            "top_seller": [
                "top seller", "best seller", "fast moving", "high sales",
                "popular product", "highest selling", "most sold",
                "best performing", "fast mover"
            ],
            "bottom_seller": [
                "bottom seller", "low sales", "least selling", "worst performing",
                "slow moving", "poor seller", "underperforming", "not selling"
            ],
            "per_channel": [
                "by channel", "per channel", "each marketplace", "platform wise",
                "portal wise", "compare marketplaces"
            ],
            "across_all": [
                "across all", "overall", "combined", "total", "aggregate",
                "all marketplaces", "all platforms", "overall sales"
            ],
        }

    def detect(self, text):
        text_emb = self.model.encode(text, convert_to_tensor=True)
        best_intent, best_score = None, -1

        for intent, examples in self.intent_map.items():
            ex_emb = self.model.encode(examples, convert_to_tensor=True)
            score = util.cos_sim(text_emb, ex_emb).mean().item()
            if score > best_score:
                best_intent, best_score = intent, score

        return best_intent, best_score

# ------------------------------------------------
# 📁 Log Config
# ------------------------------------------------
LOG_DIR = "AI_SYSTEM/MEMORY/agent_logs"
LOG_FILE = os.path.join(LOG_DIR, "sales_agent_log.json")
QUERY_HISTORY_FILE = "AI_SYSTEM/MEMORY/query_history.json"
os.makedirs(LOG_DIR, exist_ok=True)

def append_json(file_path, new_entry):
    try:
        data = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        data.append(new_entry)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Error writing to {file_path}: {e}")

# ------------------------------------------------
# 🤖 Sales Agent
# ------------------------------------------------
class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Sales Agent",
            role_prompt=(
                "You are RoboRana’s Sales Intelligence Agent — you analyze SKU-level sales, "
                "understand natural human questions, and respond like a professional analyst."
            ),
        )

        self.intent_detector = IntentDetector()

        safe_print("🔧 Initializing Unified RAG Brain...")
        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Unified RAG Brain connected.")
        except Exception as e:
            safe_print(f"❌ Failed to initialize RAG: {e}")
            self.rag = None

        self.hive_summary = summarize_collective_intelligence()
        safe_print("🤖 Sales Agent (Hive Mode) initialized.\n")

    def _locate_sales_csv(self):
        for root, _, files in os.walk(os.getcwd()):
            for f in files:
                if f.lower() == "sales_master.csv":
                    return os.path.join(root, f)
        return None

    def _to_num(self, s):
        return pd.to_numeric(
            s.astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce"
        ).fillna(0.0)

    # ✅ ONLY UPDATED FUNCTION BELOW ✅
    def _handle_data_query(self, query: str):
        q = query.lower()

        intent, conf = self.intent_detector.detect(q)
        safe_print(f"🧭 Detected intent: {intent} (conf={conf:.2f})")

        gpt_intent = None

        if conf < 0.45:
            safe_print(f"🧩 Low confidence ({conf:.2f}) → invoking GPT Reasoner...")
            try:
                gpt_intent = gpt_reason_interpretation(query)
                safe_print(f"🤖 GPT Reasoner Output → {gpt_intent}")
            except Exception as e:
                safe_print(f"⚠️ GPT Reasoner error: {e}")

        # ---------- TIME SCOPE ----------
        scope = "all_time"

        if "today" in q or "today's" in q:
            scope = "today"
        elif "yesterday" in q:
            scope = "yesterday"
        elif "7 days" in q or "last 7" in q:
            scope = "7_days"
        elif "month" in q:
            scope = "month"

        if gpt_intent and scope == "all_time" and "scope" in gpt_intent:
            scope = gpt_intent["scope"]

        safe_print(f"🔒 Time Scope Locked → {scope}")

        csv_path = self._locate_sales_csv()
        if not csv_path:
            return self.polite_fallback(query, "Sales data file not found")

        safe_print(f"📂 Using sales data file → {csv_path}")

        df = pd.read_csv(csv_path, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]

        schema = COLUMN_MAP.get("sales", {})
        mapped = validate_dataframe(df, schema)

        sku_col = mapped.get("sku") or "item sku code"
        date_col = mapped.get("date")
        value_col = mapped.get("value")

        if not sku_col or not date_col:
            return self.polite_fallback(query, "Required sales columns missing")

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["__qty__"] = 1

        if not value_col:
            value_col = next((c for c in df.columns if "selling" in c or "amount" in c), None)

        if value_col:
            df[value_col] = self._to_num(df[value_col])
        else:
            df["__val__"] = 0
            value_col = "__val__"

        today = datetime.now().date()

        # ✅ SMART FALLBACK ENGINE
        if scope == "today":
            todays_data = df[df[date_col].dt.date == today]

            if todays_data.empty:
                latest_date = df[date_col].dt.date.max()
                safe_print(f"⚠️ No data for today → Using latest available date: {latest_date}")
                df = df[df[date_col].dt.date == latest_date]
                scope = f"latest_available ({latest_date})"
            else:
                df = todays_data

        elif scope == "yesterday":
            df = df[df[date_col].dt.date == today - pd.Timedelta(days=1)]

        elif scope == "7_days":
            df = df[df[date_col] >= (pd.Timestamp.today() - pd.Timedelta(days=7))]

        elif scope == "month":
            df = df[df[date_col].dt.month == today.month]

        if df.empty:
            return self.polite_fallback(query, f"No data found for {scope}")

        # ---------- SUMMARY MODE ----------
        if "summary" in q or "scan" in q or "total" in q:
            total_orders = len(df)
            total_sales = df[value_col].sum()

            safe_print(f"\n📊 SALES SUMMARY ({scope.upper()})")
            safe_print(f"🛒 Orders       : {total_orders}")
            safe_print(f"💰 Revenue      : ₹{total_sales:,.2f}")
            safe_print(f"📦 Avg Order    : ₹{(total_sales/total_orders if total_orders else 0):,.2f}\n")

            return {
                "scope": scope,
                "orders": total_orders,
                "revenue": total_sales
            }

        # ---------- TOP / BOTTOM SKU MODE ----------
        is_top = intent == "top_seller"
        is_bottom = intent == "bottom_seller"

        grouped = df.groupby(sku_col).agg(
            total_qty=("__qty__", "sum"),
            total_value=(value_col, "sum")
        )

        out = grouped.sort_values("total_value", ascending=is_bottom).head(10)

        safe_print(f"\n📊 Showing {'Top' if is_top else 'Bottom'} 10 SKUs ({scope})\n")
        safe_print(out.to_string())

        leader = out.index[0]
        lead_val = out.iloc[0]["total_value"]

        remark = (
            f"🟢 '{leader}' leads with ₹{lead_val:,.0f}"
            if is_top else
            f"🔻 '{leader}' is lowest with ₹{lead_val:,.0f}"
        )

        safe_print(f"\n{remark} ({scope})\n")

        return out.reset_index().to_dict(orient="records")

    # ------------------------------------------------
    # 🎯 Handle Query
    # ------------------------------------------------
    def handle_query(self, query):
        query = self.process_user_input(query)

        spinner = Spinner("📊 Running Sales Analysis")
        spinner.start()

        try:
            safe_print(f"\n🧠 New Query → {query}\n")
            result = self._handle_data_query(query)

            spinner.stop()

            if isinstance(result, dict):
                return result

            if isinstance(result, list):
                safe_print("\n✅ Structured query handled.\n")
                return result

            if isinstance(result, str):
                safe_print(result)
                return result

            return self.polite_fallback(query, "Unhandled result type")

        except Exception as e:
            spinner.stop()
            safe_print(f"⚠️ Execution error: {e}")
            return self.polite_fallback(query, str(e))

# ------------------------------------------------
# 🚀 Entry
# ------------------------------------------------
if __name__ == "__main__":
    safe_print("🚀 Sales Agent (Hive Mind) started")
    agent = SalesAgent()

    while True:
        q = input("🧠 Enter a query (or 'exit'): ").strip()
        if q.lower() == "exit":
            safe_print("👋 Exiting Sales Agent")
            break
        if q:
            agent.handle_query(q)
