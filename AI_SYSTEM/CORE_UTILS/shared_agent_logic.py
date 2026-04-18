# -*- coding: utf-8 -*-
# ============================================================
# 🤖 RoboRana AI — Shared Agent Logic (v3.1: Hybrid Intelligence + GPT Reasoner + Reflex-Ready Framework)
# Author: Sandeep Rana
# Purpose: Unified multi-agent logic + Human-First reasoning + GPT-assisted comprehension
# ============================================================

import pandas as pd
from datetime import datetime, timedelta
from AI_SYSTEM.CORE_UTILS.column_schema import COLUMN_MAP, DATE_FORMATS
from AI_SYSTEM.CORE_UTILS.data_column_mapper import validate_dataframe
from AI_SYSTEM.CORE_UTILS.style_logic import add_style_column, summarize_by_style
import traceback
import re
import os
import json
import random
import inspect

# ✅ NEW IMPORTS
from AI_SYSTEM.CORE_UTILS.chat_brain_and_intent_engine import attach_chatbrain, attach_intent_engine
from AI_SYSTEM.CORE_UTILS.emotion_reactor import attach_emotion_reactor
from AI_SYSTEM.CORE_UTILS.gpt_reasoner import gpt_reason_interpretation   # 🔥 GPT Hybrid Reasoner


# ------------------------------------------------------------
# 🩺 Safe Print
# ------------------------------------------------------------
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        print(msg.encode("ascii", errors="ignore").decode("ascii"), **kwargs)


# ------------------------------------------------------------
# 🧠 Period Parser (Detect “last 7 days”, “month”, etc.)
# ------------------------------------------------------------
def parse_period(query: str):
    query = query.lower()
    today = datetime.today()
    if "last 7" in query or "week" in query:
        return today - timedelta(days=7), today
    elif "15 days" in query:
        return today - timedelta(days=15), today
    elif "30 days" in query or "month" in query:
        return today - timedelta(days=30), today
    elif "90 days" in query or "quarter" in query:
        return today - timedelta(days=90), today
    elif "year" in query:
        return today - timedelta(days=365), today
    return None, None


# ------------------------------------------------------------
# 🔢 Utility: Force numeric
# ------------------------------------------------------------
def to_num(s):
    return pd.to_numeric(
        s.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce"
    ).fillna(0.0)


# ------------------------------------------------------------
# 🚀 Shared Data Query Handler
# ------------------------------------------------------------
def handle_generic_query(agent_type: str, df: pd.DataFrame, query: str):
    q = query.lower()
    safe_print(f"🧠 Shared handler active for {agent_type} | Query: {query}")

    start, end = parse_period(q)
    date_col = None

    if start and end:
        schema = COLUMN_MAP.get(agent_type, {})
        date_col = schema.get("date")
        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", infer_datetime_format=True)
            df = df[(df[date_col] >= start) & (df[date_col] <= end)]
            safe_print(f"📅 Date filtered → {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")

    schema = COLUMN_MAP.get(agent_type, {})
    mapped = validate_dataframe(df, schema)
    sku_col = mapped.get("sku")
    date_col = mapped.get("date") or date_col
    qty_col = mapped.get("quantity") or "__qty__"
    value_col = mapped.get("value")

    if not sku_col:
        raise ValueError(f"⚠️ Missing SKU column for {agent_type}")

    df["__qty__"] = 1
    if value_col:
        df[value_col] = to_num(df[value_col])
    else:
        df["__val__"] = 0
        value_col = "__val__"

    if "style" in q:
        safe_print("🎨 Style-level query detected.")
        df = add_style_column(df, sku_col)
        summary = summarize_by_style(df, value_col=value_col)
        safe_print(f"✅ Generated style-level summary ({len(summary)} rows).")
        return summary

    grouped = df.groupby(sku_col).agg(
        total_qty=(qty_col, "sum"),
        total_value=(value_col, "sum")
    ).reset_index()

    safe_print(f"✅ SKU-level aggregation completed ({len(grouped)} rows).")
    return grouped.sort_values("total_value", ascending=False).head(10)


# ------------------------------------------------------------
# 💡 Recommendation Engine
# ------------------------------------------------------------
def suggest_next_steps(query: str):
    q = query.lower()
    if "top" in q and "sku" in q:
        return "💡 Tip: Try 'top selling styles last 30 days' for a broader category view."
    if "style" in q:
        return "🧩 You can also ask: 'which style has highest return rate?' for deeper insight."
    if "return" in q:
        return "📦 Maybe check: 'returns by portal last month' to locate the source issue."
    if "inventory" in q:
        return "📊 Try: 'slow moving inventory this quarter' to improve stock rotation."
    if "finance" in q:
        return "💰 Consider: 'most profitable SKUs this month' or 'ROI by style'."
    return "🤖 Ask RoboRana anything — sales, returns, inventory, or profitability!"


# ------------------------------------------------------------
# 🧩 Integration Helper — Hybrid Intelligence + EmotionReactor + FAILSAFE
# ------------------------------------------------------------
def integrate_shared_logic(agent_instance):
    # Attach shared core logic
    agent_instance.handle_generic_query = handle_generic_query
    agent_instance.parse_period = parse_period
    agent_instance.to_num = to_num
    agent_instance.suggest_next_steps = suggest_next_steps

    # ✅ Attach Conversational Intelligence
    try:
        attach_chatbrain(agent_instance)
        attach_intent_engine(agent_instance)
        attach_emotion_reactor(agent_instance)
        safe_print("🧩 Central Intelligence Modules attached → ChatBrain + IntentEngine + EmotionReactor ✅")
    except Exception as e:
        safe_print(f"⚠️ Failed to attach conversational modules: {e}")

    # =========================================================
    # 💬 Operation FAILSAFE — Polite Fallback System
    # =========================================================
    def polite_fallback(query: str, reason: str = None):
        prefix = random.choice(["🤔", "🙂", "💬", "⚠️", "📩"])
        polite_templates = [
            f"{prefix} I’m not fully sure what you meant by that — could you rephrase?",
            f"{prefix} I didn’t find enough data for this request. Maybe try adjusting the range or portal?",
            f"{prefix} I couldn’t map this query to a known metric. Did you mean sales, returns, or profitability?",
            f"{prefix} It looks like there’s no result for that search. Maybe check if data exists for this period?",
            f"{prefix} Let’s double-check — are you referring to Ajio, Myntra, or Inventory?"
        ]
        message = random.choice(polite_templates)
        if reason:
            message += f"\n\n🧠 Debug note: ({reason})"
        return message

    setattr(agent_instance, "polite_fallback", polite_fallback)
    safe_print("✅ Polite fallback system (Operation FAILSAFE) attached to agent.")

    # =========================================================
    # 🧠 Hybrid Reasoning (Local NLU + GPT Reasoner)
    # =========================================================
    def hybrid_reason(query: str, context: dict = None):
        """
        Uses local NLU first; invokes GPT Reasoner if confidence < 0.6.
        Returns structured interpretation with confidence.
        """
        context_snapshot = context or getattr(agent_instance, "chat_snapshot", lambda: {})()
        interpretation = {"action": "unknown", "confidence": 0.0}
        conf = 0.0

        # 🧩 Local reasoning
        local_nlu = getattr(agent_instance, "nlu", None)
        if local_nlu and hasattr(local_nlu, "interpret"):
            try:
                interpretation = local_nlu.interpret(query, context_snapshot)
                conf = interpretation.get("confidence", 0)
                safe_print(f"🧠 Local NLU Interpretation → {interpretation}")
            except Exception as e:
                safe_print(f"⚠️ Local NLU error: {e}")

        # 🤖 GPT Reasoner fallback
        if conf < 0.6:
            safe_print(f"🧩 Low confidence ({conf:.2f}) → Invoking GPT Reasoner...")
            try:
                gpt_result = gpt_reason_interpretation(query, context_snapshot)
                if gpt_result and isinstance(gpt_result, dict):
                    interpretation = gpt_result
                    safe_print(f"🤖 GPT Reasoner Refined → {interpretation}")
            except Exception as e:
                safe_print(f"⚠️ GPT Reasoner fallback failed: {e}")

        # Attach Reflex metadata for multi-agent routing (future-ready)
        interpretation["source_agent"] = getattr(agent_instance, "name", "Unknown Agent")
        interpretation["timestamp"] = datetime.utcnow().isoformat()

        return interpretation

    setattr(agent_instance, "hybrid_reason", hybrid_reason)
    safe_print("🧠 Hybrid Reasoning (Local + GPT) attached to agent ✅")

    # =========================================================
    # 🧠 Human Reasoning + Knowledge Recall (Unchanged)
    # =========================================================
    def human_reason(query: str, context: str = ""):
        try:
            if hasattr(agent_instance, "cognitive_reason"):
                result = agent_instance.cognitive_reason(query, context)
                if result and any(tag in result for tag in ["🤔", "✅", "📊", "redirect", "formula"]):
                    return result

            normalized = query
            if hasattr(agent_instance, "process_user_input"):
                try:
                    normalized = agent_instance.process_user_input(query)
                except Exception:
                    normalized = query

            from AI_SYSTEM.CORE_UTILS.logic_memory import recall_knowledge, recall_formula
            term = query.strip().split()[-1]
            meaning = recall_knowledge(term)
            if meaning:
                return f"🤓 Sure — **{term}** means: {meaning}"
            formula = recall_formula(term)
            if formula:
                return f"📊 I know this formula:\n**{term} = {formula}**"

            return None
        except Exception as e:
            return f"⚠️ Human reasoning error: {e}\n{traceback.format_exc()}"

    setattr(agent_instance, "human_reason", human_reason)
    safe_print("🧠 Human reasoning system attached to agent ✅")

    # ---------------------------------------------------------
    # 🚀 GPT Reasoner Attachment (Global Function)
    # ---------------------------------------------------------
    def run_gpt_reasoner(query, conf=None):
        safe_print(f"🧩 GPT Reasoner Triggered ({conf or '?.??'})")
        try:
            result = gpt_reason_interpretation(query)
            if result and result.get("action") != "unknown":
                safe_print(f"🤖 GPT Reasoner Output → {result}")
            else:
                safe_print(f"⚠️ GPT Reasoner returned 'unknown' for query: {query}")
            return result
        except Exception as e:
            safe_print(f"⚠️ GPT Reasoner error: {e}")
            return None

    setattr(agent_instance, "run_gpt_reasoner", run_gpt_reasoner)
    safe_print("✅ GPT Reasoner attached successfully to agent.")
