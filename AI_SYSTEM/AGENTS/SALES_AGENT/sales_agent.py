# -*- coding: utf-8 -*-
# ================================================
# 🤖 Sales Agent — Hive Mind Integrated (v4.9 Month Parsing + Channel Logic + Date Fix)
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
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    record_insight,
    record_pattern,
    summarize_collective_intelligence,
)

from AI_SYSTEM.CORE_UTILS.column_schema import COLUMN_MAP
from AI_SYSTEM.CORE_UTILS.data_column_mapper import validate_dataframe
from AI_SYSTEM.CORE_UTILS.gpt_reasoner import gpt_reason_interpretation
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
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def _spin(self):
        while self.running:
            for c in "|/-\\":
                sys.stdout.write(f"\r{self.message}... {c}")
                sys.stdout.flush()
                time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# ------------------------------------------------
# 🧠 Intent Detector
# ------------------------------------------------
class IntentDetector:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.intent_map = {
            "top_seller": [
                "top seller", "best seller", "fast moving",
                "highest selling", "best performing", "most sold"
            ],
            "bottom_seller": [
                "bottom seller", "worst seller",
                "least selling", "low sales", "slow moving"
            ]
        }

    def detect(self, text):
        text_emb = self.model.encode(text, convert_to_tensor=True)
        best_intent, best_score = None, -1

        for intent, examples in self.intent_map.items():
            ex_emb = self.model.encode(examples, convert_to_tensor=True)
            score = util.cos_sim(text_emb, ex_emb).mean().item()
            if score > best_score:
                best_intent = intent
                best_score = score

        return best_intent, best_score

# ------------------------------------------------
# 🎨 Strip Size From SKU
# ------------------------------------------------
def strip_size_from_sku(sku: str):
    if not isinstance(sku, str):
        return sku

    size_tokens = [
        "-XS", "-S", "-M", "-L", "-XL", "-XXL",
        "-XXXL", "-3XL", "-4XL", "-5XL"
    ]

    for token in size_tokens:
        if sku.endswith(token):
            return sku[:-len(token)]

    parts = sku.split("-")
    if len(parts) >= 2 and len(parts[-1]) <= 3:
        return "-".join(parts[:-1])

    return sku

# ------------------------------------------------
# 🏬 Channel Normalization
# ------------------------------------------------
def normalize_channel_name(raw):
    raw = str(raw).upper()
    if "MYNTRA" in raw:
        return "MYNTRA"
    if "AJIO" in raw:
        return "AJIO"
    if "AMAZON" in raw:
        return "AMAZON"
    if "FLIPKART" in raw:
        return "FLIPKART"
    if "NYKAA" in raw:
        return "NYKAA"
    if "TATA" in raw:
        return "TATACLIQ"
    return raw

def get_channel_request(query):
    q = query.lower()

    exact_map = {
        "myntrappmp": "MYNTRAPPMP",
        "myntrasjit": "MYNTRASJIT",
        "ajio_dropship": "AJIO_DROPSHIP",
        "amazon_in_api": "AMAZON_IN_API",
        "flipkart": "FLIPKART",
        "nykaa": "NYKAA_FASHION"
    }

    merged_map = {
        "myntra": "MYNTRA",
        "ajio": "AJIO",
        "amazon": "AMAZON",
        "flipkart": "FLIPKART",
        "nykaa": "NYKAA",
        "tatacliq": "TATACLIQ"
    }

    for key, value in exact_map.items():
        if key in q:
            return value, "exact"

    for key, value in merged_map.items():
        if key in q:
            return value, "merged"

    return None, None

# ------------------------------------------------
# ✅ Month Parsing
# ------------------------------------------------
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

def parse_month_from_query(query: str):
    q = query.lower()
    year = datetime.now().year
    month = None

    for key in MONTH_MAP.keys():
        if key in q:
            month = MONTH_MAP[key]

    for word in q.split():
        if word.isdigit() and len(word) == 4:
            year = int(word)

    return month, year

# ------------------------------------------------
# 🤖 Sales Agent
# ------------------------------------------------
class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Sales Agent",
            role_prompt=(
                "You are RoboRana’s Sales Intelligence Agent — you analyze SKU-level sales, "
                "channel-wise trends, and style-level performance like a pro analyst."
            ),
        )
        if not getattr(self, "_shared_logic_injected", False):
            try:
                integrate_shared_logic(self)
                setattr(self, "_shared_logic_injected", True)
            except Exception as e:
                safe_print(f"⚠️ Failed to integrate shared logic: {e}")

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

    def _handle_data_query(self, query: str):
        q = query.lower()
        intent, conf = self.intent_detector.detect(q)

        safe_print(f"🧭 Intent: {intent} ({conf:.2f})")

        path = self._locate_sales_csv()
        df = pd.read_csv(path, low_memory=False)

        df.columns = [c.strip().lower() for c in df.columns]

        schema = COLUMN_MAP.get("sales", {})
        mapped = validate_dataframe(df, schema)

        sku_col = mapped.get("sku")
        date_col = mapped.get("date")
        value_col = mapped.get("value")
        channel_col = "channel name" if "channel name" in df.columns else mapped.get("channel")

        # ✅ FIXED DATE PARSING
        try:
            df[date_col] = pd.to_datetime(
                df[date_col],
                format="%d/%m/%Y %H:%M:%S",
                errors="raise"
            )
        except:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        df["date_only"] = df[date_col].dt.date
        df["__qty__"] = 1
        df[value_col] = self._to_num(df[value_col])

        df["normalized_channel"] = df[channel_col].apply(normalize_channel_name)

        # ✅ Channel logic
        requested_channel, mode = get_channel_request(query)
        if requested_channel:
            if mode == "exact":
                df = df[df[channel_col].astype(str).str.upper().str.contains(requested_channel)]
                safe_print(f"✅ Exact Channel Mode: {requested_channel}")
            else:
                df = df[df["normalized_channel"] == requested_channel]
                safe_print(f"✅ Merged Channel Mode: {requested_channel}")

        # ✅ Month filtering
        month, year = parse_month_from_query(query)
        today = datetime.now()

        if month:
            df = df[(df[date_col].dt.month == month) & (df[date_col].dt.year == year)]
            scope = f"{month}-{year}"

        elif "7 days" in q:
            df = df[df["date_only"] >= (today.date() - pd.Timedelta(days=7))]
            scope = "LAST 7 DAYS"

        elif "month" in q:
            df = df[(df[date_col].dt.month == today.month) & (df[date_col].dt.year == today.year)]
            scope = "THIS MONTH"

        else:
            latest = df["date_only"].max()
            df = df[df["date_only"] == latest]
            scope = f"LATEST ({latest})"

        if df.empty:
            return self.polite_fallback(query, f"No data found for {scope}")

        # ✅ STYLE LEVEL
        if "style" in q:
            df["style_code"] = df[sku_col].apply(strip_size_from_sku)

            summary = df.groupby("style_code").agg(
                total_qty=("__qty__", "sum"),
                total_value=(value_col, "sum")
            ).sort_values("total_value", ascending=False)

            safe_print(f"\n🎨 STYLE PERFORMANCE [{scope}]\n")
            safe_print(summary.head(10))
            return summary.head(10)

        # ✅ CHANNEL LEVEL
        if "channel" in q or "marketplace" in q or "portal" in q:
            channel_summary = df.groupby("normalized_channel").agg(
                orders=("__qty__", "sum"),
                revenue=(value_col, "sum")
            ).sort_values("revenue", ascending=False)

            safe_print(f"\n🏬 CHANNEL PERFORMANCE [{scope}]\n")
            safe_print(channel_summary)
            return channel_summary

        # ✅ SKU LEVEL
        sku_summary = df.groupby(sku_col).agg(
            total_qty=("__qty__", "sum"),
            total_value=(value_col, "sum")
        ).sort_values("total_value", ascending=False)

        safe_print(f"\n📦 SKU PERFORMANCE [{scope}]\n")
        safe_print(sku_summary.head(10))
        return sku_summary.head(10)

    def handle_query(self, query):
        spinner = Spinner("Analyzing Sales")
        spinner.start()

        try:
            result = self._handle_data_query(query)
            spinner.stop()
            return self._normalize_output(result)
        except Exception as e:
            spinner.stop()
            safe_print("⚠️ Error:", e)
            return self.polite_fallback(query, str(e))

    def _normalize_output(self, result):
        """
        Convert structured pandas outputs to deterministic text for UI/process safety.
        """
        try:
            if isinstance(result, pd.DataFrame):
                if result.empty:
                    return "No rows matched this sales query."
                safe_df = result.reset_index()
                return safe_df.to_string(index=False, max_rows=25)
            if isinstance(result, pd.Series):
                return result.to_string()
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False, indent=2)
            if result is None:
                return "No response generated."
            return str(result)
        except Exception as e:
            safe_print(f"⚠️ Output normalization failed: {e}")
            return str(result)

if __name__ == "__main__":
    safe_print("🚀 Sales Agent (v4.9 FULL Power) started")

    agent = SalesAgent()
    while True:
        q = input("🧠 Enter query (or 'exit'): ").strip()
        if q.lower() == "exit":
            break
        if q:
            agent.handle_query(q)
