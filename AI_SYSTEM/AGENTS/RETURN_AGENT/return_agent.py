# -*- coding: utf-8 -*-
# ================================================
# 🤖 Return Agent — Hive Mind Integrated v5.3.2 (Precision + Correct Column Mapping)
# ================================================
import json, os, sys, time, threading, re
import pandas as pd
from datetime import datetime, timedelta

from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.RETURN_AGENT.tools.return_agent_tools import get_return_context
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    record_insight,
    record_pattern,
    summarize_collective_intelligence,
)

# ✅ Unified Schema Imports
from AI_SYSTEM.CORE_UTILS.column_schema import COLUMN_MAP, DATE_FORMATS
from AI_SYSTEM.CORE_UTILS.data_column_mapper import validate_dataframe
from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic


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
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def _spin(self):
        symbols = "|/-\\"
        i = 0
        while self.running:
            sys.stdout.write(f"\r{self.message}... {symbols[i % len(symbols)]}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 8) + "\r")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


# ------------------------------------------------
# 📁 Log Configuration
# ------------------------------------------------
LOG_DIR = "AI_SYSTEM/MEMORY/agent_logs"
LOG_FILE = os.path.join(LOG_DIR, "return_agent_log.json")
QUERY_HISTORY_FILE = "AI_SYSTEM/MEMORY/query_history.json"
os.makedirs(LOG_DIR, exist_ok=True)


def append_json(path, row):
    try:
        buf = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    buf = json.load(f)
                except:
                    buf = []
        buf.append(row)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(buf, f, indent=4, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Log write error: {e}")


# ------------------------------------------------
# 🤖 Return Agent — Unified Column Mapping (Final)
# ------------------------------------------------
class ReturnAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Return Agent",
            role_prompt=(
                "You are RoboRana’s Return Intelligence Agent. "
                "Be precise, data-driven, and human in tone. "
                "If the user asks 'why' or 'reason', use reasoning; "
                "otherwise, reply factually and politely."
            ),
        )

        if not getattr(self, "_shared_logic_injected", False):
            try:
                integrate_shared_logic(self)
                setattr(self, "_shared_logic_injected", True)
            except Exception as e:
                safe_print(f"⚠️ Failed to integrate shared logic: {e}")

        # ✅ Shared Logic Integration
        self.handle_generic_query = getattr(self, "handle_generic_query", None)

        safe_print("🔧 Initializing Unified RAG Brain...")
        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Unified RAG Brain connected.")
        except Exception as e:
            safe_print(f"❌ Failed to initialize RAG: {e}")
            self.rag = None

        base = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
        self.return_master_path = os.path.join(base, "DATA", "RETURNS", "Master", "Return_Master_Updated.csv")
        self.sales_master_path = os.path.join(base, "DATA", "SALES", "Master", "Sales_Master.csv")

        safe_print(f"📁 Using Return File: {self.return_master_path}")
        safe_print(f"📁 Using Sales File: {self.sales_master_path}")

        self.hive_summary = summarize_collective_intelligence()
        safe_print("🤖 Return Agent (Precision Mode) ready.\n")

    # ------------------------------------------------
    # 🧩 Helpers
    # ------------------------------------------------
    def _parse_period(self, query):
        query = query.lower()
        m = re.search(r"last\s+(\d+)\s+days", query)
        if m:
            days = int(m.group(1))
        elif "week" in query or "hafta" in query or "7 din" in query:
            days = 7
        elif "month" in query or "mahina" in query:
            days = 30
        else:
            days = 7
        end = datetime.now()
        start = end - timedelta(days=days)
        return start, end, days

    def _detect_intent(self, query):
        q = query.lower()
        if any(k in q for k in ["why", "reason", "issue", "problem", "root cause"]):
            return "reason"
        if any(k in q for k in ["%", "percent", "ratio", "return rate"]):
            return "percent"
        if any(k in q for k in ["sku", "item", "top", "highest", "max"]):
            return "sku"
        if any(k in q for k in ["portal", "channel", "marketplace"]):
            return "portal"
        return "summary"

    # ------------------------------------------------
    # 📦 Load CSVs (Real Column Names Applied)
    # ------------------------------------------------
    def _load_csvs(self, start, end):
        returns = pd.read_csv(self.return_master_path, low_memory=False)
        sales = pd.read_csv(self.sales_master_path, low_memory=False)

        # 🧩 Real column mapping based on file structure
        sku_r = "Product SKU Code"
        date_r = "Date"
        qty_r = "Qty"
        val_r = "Total"
        channel_r = "Channel entry"

        # ✅ Use Centralized Schema for Sales
        sal_schema = COLUMN_MAP["sales"]
        sal_cols = validate_dataframe(sales, sal_schema)
        sku_s, date_s, qty_s, val_s = sal_cols["sku"], sal_cols["date"], sal_cols["quantity"], sal_cols["value"]

        # Parse Dates
        returns[date_r] = pd.to_datetime(returns[date_r], errors="coerce", dayfirst=True)
        sales[date_s] = pd.to_datetime(sales[date_s], errors="coerce", format=DATE_FORMATS["sales"], dayfirst=True)

        # Filter by Period
        returns = returns[(returns[date_r] >= start) & (returns[date_r] <= end)]
        sales = sales[(sales[date_s] >= start) & (sales[date_s] <= end)]

        # Clean numeric columns
        for col in [val_r, val_s]:
            if col and (col in returns.columns or col in sales.columns):
                df = returns if col in returns.columns else sales
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        safe_print(f"🔍 Mapped Columns → Return: SKU={sku_r}, Date={date_r}, Value={val_r} | Sales: SKU={sku_s}, Date={date_s}, Value={val_s}")
        safe_print(f"✅ Loaded {len(returns)} returns and {len(sales)} sales rows for {start.date()} → {end.date()}")
        return returns, sales, sku_r, sku_s, val_r, val_s

    # ------------------------------------------------
    # 🧠 Handle Query
    # ------------------------------------------------
    def handle_query(self, query):
        query = self.process_user_input(query)
        spinner = Spinner("📦 Processing Return Query")
        spinner.start()
        response = ""

        try:
            safe_print(f"\n🧠 New Query → {query}\n")
            intent = self._detect_intent(query)
            start, end, days = self._parse_period(query)
            safe_print(f"📅 Period Detected: {start.date()} → {end.date()} ({days} days)")

            returns, sales, sku_r, sku_s, val_r, val_s = self._load_csvs(start, end)

            # ===== Intent Handling =====
            if intent == "percent":
                total_sales = sales[val_s].sum() if val_s else 0
                total_returns = returns[val_r].sum() if val_r else 0
                return_pct = (total_returns / total_sales * 100) if total_sales else 0
                response = f"📊 Return % in last {days} days: **{return_pct:.2f}%** (₹{total_returns:,.0f} of ₹{total_sales:,.0f})"

            elif intent == "portal":
                if "Channel entry" not in returns.columns:
                    response = "⚠️ No channel/portal data found in return file."
                else:
                    df = returns.groupby("Channel entry")[val_r].sum().sort_values(ascending=False).head(10)
                    response = "📦 Top Return Portals (₹ Value):\n" + "\n".join([f"- {i}: ₹{v:,.0f}" for i, v in df.items()])

            elif intent == "sku":
                df = returns.groupby(sku_r)[val_r].sum().sort_values(ascending=False).head(10)
                response = "📦 Top Returned SKUs (₹ Value):\n" + "\n".join([f"- {i}: ₹{v:,.0f}" for i, v in df.items()])

            elif intent == "reason":
                rag_context = get_return_context(self.rag, query)
                response = self.think(f"Hive Context: {self.hive_summary}\nRAG Data: {rag_context}\nUser asked: {query}\nExplain briefly.")

            else:
                total_returns = returns[val_r].sum() if val_r else 0
                total_qty = len(returns)
                response = f"📊 Total Returns (last {days} days): {total_qty:,} orders worth ₹{total_returns:,.0f}"

            # ===== Logging =====
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agent": "Return Agent",
                "query": query,
                "response": response,
            }
            append_json(LOG_FILE, entry)
            append_json(QUERY_HISTORY_FILE, {"timestamp": entry["timestamp"], "query": query})

        finally:
            spinner.stop()

        # ===== Output =====
        safe_print("\n📝 Log saved successfully.\n")
        safe_print("💬 ===== Return Agent (Precision Mode) Response =====\n")
        safe_print(response)
        safe_print("\n" + "=" * 90 + "\n")
        return response


# ------------------------------------------------
# 🚀 CLI Interface
# ------------------------------------------------
if __name__ == "__main__":
    safe_print("🚀 Return Agent (Hive Mind) started")
    agent = ReturnAgent()

    auto_mode = any(x in sys.argv for x in ["--auto", "--summary", "--manager"])
    if auto_mode:
        safe_print("🤖 Manager-triggered auto summary mode.\n")
        agent.handle_query("return summary for manager")
        sys.exit(0)

    while True:
        try:
            q = input("🧠 Enter a query (or 'exit'): ").strip()
            if q.lower() == "exit":
                safe_print("👋 Exiting Return Agent...")
                break
            if q:
                agent.handle_query(q)
        except KeyboardInterrupt:
            safe_print("\n👋 Exiting Return Agent...")
            break
        except Exception as e:
            safe_print(f"⚠️ Error: {e}")
