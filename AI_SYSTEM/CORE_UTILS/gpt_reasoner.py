# -*- coding: utf-8 -*-
# ===============================================================
# 🤖 RoboRana GPT Reasoner (Hybrid Cognitive Layer v1.4 — Reflex+Cache Mode)
# Author: Sandeep Rana
# Purpose:
#   - Neural reasoning fallback for low-confidence NLU.
#   - Interprets natural/human/Hinglish queries → structured intent.
#   - Secure GPT integration with local cache + auto fallback.
# ===============================================================

import os
import json
import traceback
import re
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# ===============================================================
# 🔐 Environment Setup
# ===============================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ GPT Reasoner: OpenAI client initialized.")
except Exception as e:
    client = None
    print(f"⚠️ GPT Reasoner: OpenAI client not available — {e}")

# ===============================================================
# 🧠 Local Query Cache (Avoid redundant GPT calls)
# ===============================================================
CACHE_FILE = os.path.join("AI_SYSTEM", "MEMORY", "gpt_reason_cache.json")


def _load_cache():
    """Safely load the GPT reasoning cache."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    """Safely save the GPT reasoning cache."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to save GPT Reasoner cache: {e}")


# ===============================================================
# ⚙️ GPT Reasoning Core
# ===============================================================
def gpt_reason_interpretation(query: str, context: dict = None, model: str = "gpt-4o-mini") -> dict:
    """
    Uses GPT to interpret user queries and return structured meaning.
    Returns: dict(action, scope, channel, granularity, confidence)
    """
    try:
        if not query or not isinstance(query, str):
            return {"error": "invalid_query", "confidence": 0.0}

        original_query = query.strip()
        q_low = original_query.lower().replace(" pls ", "please ").replace(" bro ", " ")
        q_low = re.sub(r"[^a-zA-Z0-9\s]", " ", q_low)

        # --- Cache check ---
        cache = _load_cache()
        query_hash = hashlib.md5(q_low.encode()).hexdigest()
        if query_hash in cache:
            cached = cache[query_hash]
            print(f"🧩 [CACHE HIT] GPT Reasoner → {cached}")
            return cached

        # --- GPT unavailable fallback ---
        if not client:
            print("⚠️ GPT Reasoner inactive (client not initialized).")
            return {
                "action": "unknown",
                "scope": "all_time",
                "channel": "overall",
                "granularity": "sku",
                "confidence": 0.0,
                "source": "local_fail"
            }

        # --- Context handling ---
        context_text = ""
        if isinstance(context, dict) and context:
            try:
                context_text = json.dumps(context, indent=2, ensure_ascii=False)
            except Exception:
                context_text = str(context)

        # ===============================================================
        # 🧩 GPT Instruction Prompt
        # ===============================================================
        prompt = f"""
You are the cognitive reasoning brain of RoboRana AI — an e-commerce analytics system.

Your task:
- Understand natural, human, or Hinglish queries (e.g., "ajio sale last week", "which style sold most last month").
- Interpret the user's intent precisely and output structured JSON only.
- Infer missing info logically (no extra text).

Output Format:
{{
  "action": "summarize_sales" | "compare_channels" | "style_analysis" |
             "returns_summary" | "inventory_health" | "profitability" | "unknown",
  "scope": "7_days" | "30_days" | "90_days" | "365_days" | "all_time",
  "channel": "myntra" | "ajio" | "flipkart" | "amazon" | "overall",
  "granularity": "sku" | "style" | "portal",
  "confidence": 0.xx
}}

Rules:
- "last week" → "7_days", "last month" → "30_days", "quarter" → "90_days".
- Detect portal names (ajio, myntra, flipkart, amazon).
- Boost confidence for specific queries.
- Return *only* JSON (no markdown or comments).

Example:
"show ajio sale last 7 days" →
{{"action": "summarize_sales", "scope": "7_days", "channel": "ajio", "granularity": "sku", "confidence": 0.95}}

"which style sold most last month" →
{{"action": "style_analysis", "scope": "30_days", "channel": "overall", "granularity": "style", "confidence": 0.93}}

User Query:
{original_query}

Context:
{context_text}
"""

        # ===============================================================
        # 🧩 GPT API Call
        # ===============================================================
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are RoboRana's logical reasoning module."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            max_tokens=350,
        )

        choices = getattr(resp, "choices", None)
        if not isinstance(choices, list) or len(choices) == 0:
            print("⚠️ GPT returned empty or invalid response.")
            return {
                "action": "unknown",
                "scope": "all_time",
                "channel": "overall",
                "granularity": "sku",
                "confidence": 0.0,
                "error": "empty_response",
                "source": "gpt_reasoner",
                "timestamp": datetime.now().isoformat()
        }
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", None) if message else None
        raw_reply = content.strip() if isinstance(content, str) else ""
        print(f"🧠 Raw GPT Reply: {raw_reply[:200]}{'...' if len(raw_reply) > 200 else ''}")

        # ===============================================================
        # 🧩 JSON Extraction + Cleaning
        # ===============================================================
        structured = {}
        try:
            structured = json.loads(raw_reply)
        except Exception:
            match = re.search(r"\{.*\}", raw_reply, re.DOTALL)
            if match:
                try:
                    structured = json.loads(match.group(0))
                except Exception:
                    structured = {}
        if not isinstance(structured, dict):
            structured = {}

        # --- Fill defaults ---
        defaults = {
            "action": "unknown",
            "scope": "all_time",
            "channel": "overall",
            "granularity": "sku",
            "confidence": 0.5,
        }
        for k, v in defaults.items():
            structured.setdefault(k, v)

        # Safe confidence handling
        confidence = structured.get("confidence", 0)
        if confidence < 0.6 and len(original_query.split()) > 6:
            structured["confidence"] = confidence + 0.15
        # --- Final metadata ---
        structured["source"] = "gpt_reasoner"
        structured["timestamp"] = datetime.now().isoformat()

        # --- Log and Cache ---
        print(f"🧩 GPT Reasoner Final Output: {structured}")
        cache[query_hash] = structured
        _save_cache(cache)

        return structured

    except Exception as e:
        print(f"⚠️ GPT Reasoner Error: {e}\n{traceback.format_exc()}")
        return {
            "action": "unknown",
            "scope": "all_time",
            "channel": "overall",
            "granularity": "sku",
            "confidence": 0.0,
            "error": str(e),
        }


# ---------------------------------------------------------
# ✅ Diagnostic Mode — Run Reasoner Directly
# ---------------------------------------------------------
if __name__ == "__main__":
    from pprint import pprint

    print("🧠 GPT Reasoner Diagnostic Mode (Hybrid Reflex+Cache Active)")
    print("Type your query below (or 'exit' to quit):\n")

    while True:
        q = input("🔍 Query: ").strip()
        if q.lower() in ["exit", "quit"]:
            print("👋 Exiting GPT Reasoner Diagnostic.")
            break
        if q:
            try:
                result = gpt_reason_interpretation(q)
                print("\n🧩 Reasoning Output:")
                pprint(result)
                print("\n" + "=" * 70 + "\n")
            except Exception as e:
                print(f"⚠️ Error: {e}")
