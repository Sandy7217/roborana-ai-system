# -*- coding: utf-8 -*-
"""
AI_SYSTEM/CORE_UTILS/contextual_voice_router.py

Purpose:
- Direct user queries to the correct AI agent (Sales, Returns, Inventory, Finance, Ads, or Manager)
  based on detected topic, intent, and tone.
- Acts as the “voice switchboard” for RoboRana’s multi-agent conversational system.

Author: Generated for Sandeep Rana / RoboRana
Version: 1.0 (Operation R.O.B.O.T.A.L.K Phase 1.3)
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Tuple


# -------------------------------------------------------------------
# ROUTER CLASS
# -------------------------------------------------------------------
class ContextualVoiceRouter:
    """
    Determines which agent should handle a given user message.
    Inputs: intent, emotion, topic_hint (from ChatBrain + IntentEmotionEngine)
    Output: agent_type, confidence, route_log
    """

    def __init__(self, log_routes: bool = True):
        self.log_routes = log_routes
        self.log_path = os.path.join("AI_SYSTEM", "MEMORY", "chat_routes.json")

        # Keyword maps (rule-based detection)
        self.topic_keywords = {
            "sales": ["sale", "order", "revenue", "growth", "myntra", "ajio", "top sku", "ros", "gmv"],
            "returns": ["return", "refund", "rto", "replacement", "defect"],
            "inventory": ["inventory", "stock", "quantity", "slow", "fast moving", "out of stock"],
            "finance": ["profit", "margin", "roi", "cost", "loss", "expense", "net", "gmv"],
            "ads": ["ad", "advertisement", "campaign", "myntra ads", "visibility", "pla", "impression", "ctr"],
            "manager": ["status", "report", "summary", "dashboard", "overall", "update"]
        }

    # ---------------------------------------------------------------
    # 🔍 Core Router
    # ---------------------------------------------------------------
    def route_message(
        self,
        user_text: str,
        intent: str,
        emotion: str,
        topic_hint: Optional[str] = None
    ) -> Tuple[str, float, Dict]:
        """
        Returns (agent_type, confidence, metadata)
        """

        text = user_text.lower().strip()
        matched_agent = None
        confidence = 0.0

        # 1️⃣ — Use topic hint first (from ChatBrain)
        if topic_hint:
            for agent, kws in self.topic_keywords.items():
                if topic_hint.lower() in kws:
                    matched_agent = agent
                    confidence = 0.85
                    break

        # 2️⃣ — Scan message keywords
        if not matched_agent:
            for agent, kws in self.topic_keywords.items():
                for kw in kws:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text):
                        matched_agent = agent
                        confidence = max(confidence, 0.7)
                        break
                if matched_agent:
                    break

        # 3️⃣ — Use intent fallback if no keyword match
        if not matched_agent:
            if intent in ["analyze", "query"]:
                matched_agent = "sales"
                confidence = 0.5
            elif intent in ["teach", "definition", "explain"]:
                matched_agent = "manager"
                confidence = 0.5
            else:
                matched_agent = "manager"
                confidence = 0.4

        # 4️⃣ — Adjust routing based on emotion or tone
        if emotion in ["angry", "negative", "frustrated"] and matched_agent != "manager":
            confidence -= 0.05  # slight uncertainty
        elif emotion in ["positive", "curious"]:
            confidence += 0.05

        confidence = round(min(max(confidence, 0.3), 0.95), 2)

        # 5️⃣ — Log routing for debugging
        metadata = {
            "agent": matched_agent,
            "intent": intent,
            "emotion": emotion,
            "topic_hint": topic_hint,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "query": user_text
        }

        if self.log_routes:
            self._log_route(metadata)

        return matched_agent, confidence, metadata

    # ---------------------------------------------------------------
    # 🧾 Route Logger
    # ---------------------------------------------------------------
    def _log_route(self, metadata: Dict):
        """Save routing decision to a log file for debugging and traceability."""
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            if os.path.exists(self.log_path):
                with open(self.log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []

            data.append(metadata)
            if len(data) > 2000:
                data = data[-1000:]  # keep recent history only

            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ Route log failed: {e}")


# -------------------------------------------------------------------
# 🔗 Integration Helper
# -------------------------------------------------------------------
def attach_contextual_router(agent, router: Optional[ContextualVoiceRouter] = None):
    """Attach ContextualVoiceRouter to an agent dynamically."""
    if router is None:
        router = ContextualVoiceRouter()
    setattr(agent, "voice_router", router)

    def route_message(user_text, intent, emotion, topic_hint=None):
        return router.route_message(user_text, intent, emotion, topic_hint)

    setattr(agent, "route_message", route_message)
    return router


# -------------------------------------------------------------------
# 🧪 Self-test
# -------------------------------------------------------------------
if __name__ == "__main__":
    router = ContextualVoiceRouter()
    tests = [
        "show me ajio sales last week",
        "check returns by portal",
        "profit margin trend last month",
        "slow moving inventory this quarter",
        "ads performance myntra",
        "overall report summary"
    ]
    for t in tests:
        intent = "analyze"
        emotion = "neutral"
        agent, conf, meta = router.route_message(t, intent, emotion)
        print(f"🧭 '{t}' → {agent.upper()} (conf: {conf})")
