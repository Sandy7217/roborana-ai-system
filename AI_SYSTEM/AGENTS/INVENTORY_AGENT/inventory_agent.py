# -*- coding: utf-8 -*-
# ============================================================
# 🤖 Inventory Agent — Hive Mind Integrated v5.6
# (Human Conversational + NLU + Hybrid Logic + GPT Summary Layer
#  + Style/SKU Awareness + Rate of Sale Metrics + Forecasting)
# ============================================================
import json
import os
import sys
import time
import threading
import re
from datetime import datetime
import pandas as pd

from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.INVENTORY_AGENT.tools.inventory_data_tools import interpret_inventory_query
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    record_insight,
    record_pattern,
    summarize_collective_intelligence,
)
from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic

# --------------------------
# === CONFIGURED MASTER PATHS
# --------------------------
SALES_MASTER_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES\Master\Sales_Master.csv"
RETURNS_MASTER_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\RETURNS\Master\Return_Master_Updated.csv"

# ------------------------------------------------
# 🩺 Safe Print Helper
# ------------------------------------------------
def safe_print(*args, **kwargs):
    """UTF-8 safe print for console, Streamlit, and n8n logs"""
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
            time.sleep(0.10)
        sys.stdout.write("\r" + " " * (len(self.message) + 8) + "\r")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# ------------------------------------------------
# 📁 Log Config
# ------------------------------------------------
LOG_DIR = "AI_SYSTEM/MEMORY/agent_logs"
LOG_FILE = os.path.join(LOG_DIR, "inventory_agent_log.json")
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
# ⚙️ Utility — Health Rating System
# ------------------------------------------------
def evaluate_health(low_stock, total):
    try:
        pct = (low_stock / total) * 100 if total > 0 else 0
        if pct < 10:
            return ("🟢 Good", f"Only {pct:.1f}% SKUs are low — healthy inventory levels.")
        elif pct < 25:
            return ("🟡 Moderate", f"{pct:.1f}% SKUs are low — monitor restocking soon.")
        else:
            return ("🔴 Critical", f"{pct:.1f}% SKUs are low — immediate replenishment needed.")
    except Exception:
        return ("⚪ Unknown", "Could not determine health level from data.")

# ------------------------------------------------
# 🔮 Style & SKU Level Analyzer
# ------------------------------------------------
def analyze_style_sku_level(latest_file_path, sales_df=None, returns_df=None):
    df = pd.read_csv(latest_file_path)

    inv_col = next((c for c in df.columns if "inventory" in c.lower()), None)
    style_col = next((c for c in df.columns if "style" in c.lower()), None)
    sku_col = next((c for c in df.columns if "sku" in c.lower()), None)

    if not inv_col:
        raise ValueError("No inventory column found in inventory file.")
    df[inv_col] = pd.to_numeric(df[inv_col], errors="coerce").fillna(0)

    merge_key = None
    sales_map = pd.DataFrame()
    returns_map = pd.DataFrame()

    # sales merge
    if sales_df is not None:
        sales_sku = next((c for c in sales_df.columns if "sku" in c.lower()), None)
        sales_style = next((c for c in sales_df.columns if "style" in c.lower()), None)
        sales_qty_col = next((c for c in sales_df.columns if "qty" in c.lower() or "quantity" in c.lower() or "sold" in c.lower()), None)
        if sales_qty_col:
            if sku_col and sales_sku:
                merge_key = "sku"
                sales_map = sales_df[[sales_sku, sales_qty_col]].groupby(sales_sku).sum().reset_index()
                sales_map.columns = [sku_col, "sales_30d"]
            elif style_col and sales_style:
                merge_key = "style"
                sales_map = sales_df[[sales_style, sales_qty_col]].groupby(sales_style).sum().reset_index()
                sales_map.columns = [style_col, "sales_30d"]

    # returns merge
    if returns_df is not None:
        returns_sku = next((c for c in returns_df.columns if "sku" in c.lower()), None)
        returns_style = next((c for c in returns_df.columns if "style" in c.lower()), None)
        returns_qty_col = next((c for c in returns_df.columns if "qty" in c.lower() or "quantity" in c.lower() or "returned" in c.lower()), None)
        if returns_qty_col:
            if merge_key == "sku" and returns_sku:
                returns_map = returns_df[[returns_sku, returns_qty_col]].groupby(returns_sku).sum().reset_index()
                returns_map.columns = [sku_col, "returns_30d"]
            elif merge_key == "style" and returns_style:
                returns_map = returns_df[[returns_style, returns_qty_col]].groupby(returns_style).sum().reset_index()
                returns_map.columns = [style_col, "returns_30d"]

    working = df.copy()
    if merge_key == "sku" and sku_col:
        if not sales_map.empty:
            working = working.merge(sales_map, on=sku_col, how="left")
        else:
            working["sales_30d"] = 0
        if not returns_map.empty:
            working = working.merge(returns_map, on=sku_col, how="left")
        else:
            working["returns_30d"] = 0
    elif merge_key == "style" and style_col:
        if not sales_map.empty:
            working = working.merge(sales_map, on=style_col, how="left")
        else:
            working["sales_30d"] = 0
        if not returns_map.empty:
            working = working.merge(returns_map, on=style_col, how="left")
        else:
            working["returns_30d"] = 0
    else:
        working["sales_30d"] = 0
        working["returns_30d"] = 0

    for col in ["sales_30d", "returns_30d"]:
        working[col] = pd.to_numeric(working[col], errors="coerce").fillna(0)

    if sku_col:
        sku_summary = working[[sku_col, inv_col, "sales_30d", "returns_30d"]].copy()
        sku_summary.rename(columns={sku_col: "SKU", inv_col: "Inventory"}, inplace=True)
        sku_summary["Net_Sales_30D"] = sku_summary["sales_30d"] - sku_summary["returns_30d"]
        sku_summary["ROS_per_day"] = sku_summary["Net_Sales_30D"] / 30.0
        sku_summary["Coverage_Days"] = sku_summary.apply(lambda r: (r["Inventory"] / r["ROS_per_day"]) if r["ROS_per_day"] > 0 else float("inf"), axis=1)
    else:
        sku_summary = pd.DataFrame()

    if style_col:
        style_summary = (
            working.groupby(style_col)
            .agg(total_inventory=(inv_col, "sum"),
                 total_sales_30d=("sales_30d", "sum"),
                 total_returns_30d=("returns_30d", "sum"))
            .reset_index()
        )
        style_summary["net_sales_30d"] = style_summary["total_sales_30d"] - style_summary["total_returns_30d"]
        style_summary["avg_daily_sales"] = style_summary["net_sales_30d"] / 30.0
        style_summary["coverage_days"] = style_summary.apply(lambda x: (x["total_inventory"] / x["avg_daily_sales"]) if x["avg_daily_sales"] > 0 else float("inf"), axis=1)
    else:
        style_summary = pd.DataFrame()

    return style_summary, sku_summary

# ------------------------------------------------
# 🔎 Forecast utilities
# ------------------------------------------------
def parse_forecast_days_from_query(query, default=90):
    q = query.lower()
    m = re.search(r"(\d+)\s*days", q)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)\s*month", q)
    if m2:
        return int(m2.group(1)) * 30
    if "quarter" in q:
        return 90
    return default

def compute_reorder_recommendations(sku_df, days):
    if sku_df is None or sku_df.empty:
        return pd.DataFrame()
    df = sku_df.copy()
    if "ROS_per_day" not in df.columns:
        df["ROS_per_day"] = 0.0
    df["Predicted_Demand"] = df["ROS_per_day"] * days
    df["Reorder_Qty"] = df.apply(lambda r: max(0, int(round(r["Predicted_Demand"] - r["Inventory"]))), axis=1)
    df["Need_Reorder"] = df["Reorder_Qty"] > 0
    df = df.sort_values(by="Reorder_Qty", ascending=False).reset_index(drop=True)
    return df
# ------------------------------------------------
# 🧠 Inventory Intent Router (SAFE ADDITION)
# ------------------------------------------------
def detect_inventory_mode(query: str):
    q = query.lower()

    if any(k in q for k in ["style level", "style-wise", "style wise", "by style"]):
        return "style"

    if any(k in q for k in ["sku level", "sku wise", "by sku"]):
        return "sku"

    if any(k in q for k in ["reorder", "forecast", "planning"]):
        return "forecast"

    return "summary"

# ------------------------------------------------
# 🤖 Inventory Agent
# ------------------------------------------------
class InventoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Inventory Agent",
            role_prompt=(
                "You are RoboRana’s **Inventory Intelligence Agent**, part of the Hive Mind collective. "
                "You understand human queries about stock health, replenishment, and over/under-stock. "
                "You are aware of SKU-level and style-level details and can compute rate-of-sale (ROS), "
                "stock coverage days, and forecast future requirements."
            ),
        )

        if not getattr(self, "_shared_logic_injected", False):
            try:
                integrate_shared_logic(self)
                setattr(self, "_shared_logic_injected", True)
            except Exception as e:
                safe_print(f"⚠️ Failed to integrate shared logic: {e}")

        self.handle_generic_query = getattr(self, "handle_generic_query", None)
        safe_print("🔧 Initializing Unified RAG Brain...")

        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Unified RAG Brain connected.")
        except Exception as e:
            safe_print(f"❌ Failed to initialize RAG: {e}")
            self.rag = None

        # preload sales & returns
        self.sales_df = None
        self.returns_df = None
        try:
            if os.path.exists(SALES_MASTER_PATH):
                self.sales_df = pd.read_csv(SALES_MASTER_PATH)
                safe_print(f"✅ Loaded Sales Master ({len(self.sales_df)} rows).")
            else:
                safe_print("⚠️ Sales Master not found at configured path.")
        except Exception as e:
            safe_print(f"⚠️ Failed to load Sales Master: {e}")

        try:
            if os.path.exists(RETURNS_MASTER_PATH):
                self.returns_df = pd.read_csv(RETURNS_MASTER_PATH)
                safe_print(f"✅ Loaded Returns Master ({len(self.returns_df)} rows).")
            else:
                safe_print("⚠️ Returns Master not found at configured path.")
        except Exception as e:
            safe_print(f"⚠️ Failed to load Returns Master: {e}")

        self.hive_summary = summarize_collective_intelligence()
        safe_print("🧠 Hive Mind awareness enabled.")
        safe_print("🤖 Inventory Agent (Human-Aware Mode) ready.\n")

    def handle_query(self, query):
        query = self.process_user_input(query)
        spinner = Spinner("📦 Analyzing Inventory Health")
        spinner.start()
        response = ""
        try:
            safe_print(f"\n🧠 New Query → {query}\n")
            summary = interpret_inventory_query(query)
            mode = detect_inventory_mode(query)
            summary_data = summary.copy() if isinstance(summary, dict) else summary
            summary_text = json.dumps(summary, indent=2, ensure_ascii=False) if isinstance(summary, dict) else str(summary)
            safe_print("📊 Local inventory metrics computed successfully.\n")

            forecast_days = parse_forecast_days_from_query(query, default=90)

            try:
                latest_file = summary.get("latest_file", None) if isinstance(summary, dict) else None
                if latest_file and os.path.exists(latest_file):
                    style_summary, sku_summary = analyze_style_sku_level(latest_file, self.sales_df, self.returns_df)
                    safe_print(f"📦 Style/SKU-level data processed ({len(style_summary)} styles, {len(sku_summary)} SKU rows).")

                    sku_with_forecast = compute_reorder_recommendations(sku_summary, forecast_days)
                    summary["style_summary"] = style_summary.head(15).to_dict(orient="records") if not style_summary.empty else []
                    summary["sku_summary"] = sku_with_forecast.head(20).to_dict(orient="records") if not sku_with_forecast.empty else []
                    summary["forecast_days"] = forecast_days
                else:
                    safe_print("ℹ️ Using latest inventory snapshot for analysis.")
            except Exception as e:
                safe_print(f"⚠️ Style-level analysis failed: {e}")

            try:
                gpt_summary = self.think(f"Summarize this inventory report conversationally: {summary_text}")
                if gpt_summary:
                    summary_text = f"{summary_text}\n\n🤖 GPT View: {gpt_summary}"
            except Exception as e:
                safe_print(f"⚠️ GPT Summary generation failed: {e}")
                gpt_summary = None

            rag_context = ""
            try:
                if self.rag:
                    rag_context = self.rag.query_all("inventory", query)
            except Exception as e:
                safe_print(f"⚠️ RAG query failed: {e}")


# -------------------------------
# 🧠 Inventory Prompt Routing (FIX)
# -------------------------------
            if mode == "style":
                prompt = f"""
### 🧠 Hive Mind Context
{self.hive_summary}

### 🔍 Style Level Inventory
{summary.get('style_summary', [])}

### 🧾 RAG Insights
{rag_context}

### ❓User Query
{query}

Generate a STYLE-LEVEL inventory report including:
2️⃣ ROS & coverage days
3️⃣ At-risk styles
4️⃣ Style-level reorder suggestions
5️⃣ Clear business conclusion
1️⃣ Style-wise total inventory (aggregate SKUs)
2️⃣ Coverage days per style
3️⃣ At-risk styles
4️⃣ Style-level reorder suggestions

IMPORTANT:
- Merge all SKUs under one style.
- Do not show size-wise or SKU-wise rows.


"""
            elif mode == "sku":
                    prompt = f"""
### 🧠 Hive Mind Context
{self.hive_summary}

### 🔍 SKU Level Inventory
{summary.get('sku_summary', [])}

### 🧾 RAG Insights
{rag_context}

### ❓User Query
{query}

Generate a SKU-LEVEL inventory report including:
1️⃣ SKU-wise inventory
2️⃣ Dead / zero movement SKUs
3️⃣ Immediate reorder SKUs
4️⃣ Actionable reorder quantities.
"""
            else:
                    prompt = f"""
### 🧠 Hive Mind Context
{self.hive_summary}

### 📦 Inventory Summary
{summary_text}

### 🧾 RAG Insights
{rag_context}

### ❓User Query
{query}

Generate a SUMMARY inventory report including:
1️⃣ Stock health (low %, overstock %)
2️⃣ Key inventory risks
3️⃣ High-level action plan
4️⃣ Friendly closing remark.
"""                    
                                
            response = self.think(prompt)

            if not response or len(str(response).strip()) < 40:
                safe_print("⚠️ Using fallback: merging metrics + forecast.")
                def get_val(obj, key): return obj.get(key, 0) if isinstance(obj, dict) else getattr(obj, key, 0)
                total_skus = get_val(summary_data, "total_skus")
                total_qty = get_val(summary_data, "total_quantity")
                low_stock = get_val(summary_data, "low_stock_items")
                overstock = get_val(summary_data, "overstocked_items")
                rating, note = evaluate_health(low_stock, total_skus)
                top_reorders_txt = ""
                if isinstance(summary, dict) and summary.get("sku_summary"):
                    reorders = summary.get("sku_summary")[:8]
                    lines = [f"• {r.get('SKU','?')} — Inventory: {r.get('Inventory',0)}, Reorder: {r.get('Reorder_Qty',0)}, Coverage: {r.get('Coverage_Days','∞')}" for r in reorders]
                    top_reorders_txt = "\n\n🔧 Top SKU reorder suggestions:\n" + "\n".join(lines)
                response = f"""
📦 **Inventory Summary Report**
─────────────────────────────
• Total SKUs: {total_skus}
• Total Quantity: {total_qty}
• Low Stock Items: {low_stock}
• Overstocked Items: {overstock}

🧩 **Health Rating:** {rating}
💬 {note}

Forecast horizon: {forecast_days} days.
{gpt_summary if gpt_summary else ""}
{top_reorders_txt}
"""

            entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "agent": "Inventory Agent", "query": query, "response": str(response)[:4000]}
            append_json(LOG_FILE, entry)
            append_json(QUERY_HISTORY_FILE, {"timestamp": entry["timestamp"], "query": query})
            try: record_insight("Inventory Agent", response, {"query": query})
            except Exception as e: safe_print(f"⚠️ Hive update failed: {e}")

        finally:
            spinner.stop()
            safe_print("\n📝 Log saved successfully.\n")
            safe_print("💬 ===== Inventory Agent (Human Conversational) Response =====\n")
            safe_print(response)
            safe_print("\n" + "=" * 90 + "\n")
            return response


# ------------------------------------------------
# 🚀 CLI Interface
# ------------------------------------------------
if __name__ == "__main__":
    safe_print("🚀 Inventory Agent (Hive Mind) started")
    agent = InventoryAgent()
    auto_mode = any(flag in sys.argv for flag in ["--auto", "--summary", "--manager"])
    if auto_mode:
        safe_print("🤖 Manager-triggered auto summary mode.\n")
        agent.handle_query("inventory health summary for manager")
        sys.exit(0)

    while True:
        try:
            q = input("🧠 Enter a query (or 'exit'): ").strip()
            if q.lower() == "exit":
                safe_print("👋 Exiting Inventory Agent...")
                break
            if q:
                agent.handle_query(q)
        except KeyboardInterrupt:
            safe_print("\n👋 Exiting Inventory Agent...")
            break
        except Exception as e:
            safe_print(f"⚠️ Error: {e}")
