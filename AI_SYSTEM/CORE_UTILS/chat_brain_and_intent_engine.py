# -*- coding: utf-8 -*-
"""
AI_SYSTEM/CORE_UTILS/chat_brain_and_intent_engine.py

ChatBrain + IntentEmotionEngine (Enhanced for RoboRana)

Upgrades:
- Loop / repeat detection
- Hard scope locking (today / yesterday etc.)
- Better ecommerce intent detection
- Reduced wrong fallback triggers
"""

import os
import json
import re
from datetime import datetime
from collections import deque, Counter
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

# -----------------------------
# Config
# -----------------------------
MEMORY_DIR = os.path.join("AI_SYSTEM", "MEMORY")
CHAT_BRAIN_FILE = os.path.join(MEMORY_DIR, "chat_brain.json")
DEFAULT_MAX_MESSAGES = 40

# -----------------------------
# ChatBrain
# -----------------------------
class ChatBrain:
    """Short-term conversation manager"""

    def __init__(self, max_messages: int = DEFAULT_MAX_MESSAGES, persist: bool = True):
        self.max_messages = max_messages
        self.messages = deque(maxlen=max_messages)
        self.persist = persist

        if persist:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            try:
                self._load()
            except Exception:
                pass

    def push_message(self, role: str, text: str, meta: Optional[dict] = None):
        item = {
            "role": role,
            "text": text.strip(),
            "ts": datetime.utcnow().isoformat(),
            "meta": meta or {}
        }
        self.messages.append(item)
        if self.persist:
            self._save()

    def last(self, n: int = 1) -> List[dict]:
        return list(self.messages)[-n:]

    def clear(self):
        self.messages.clear()
        if self.persist:
            self._save()

    def get_snapshot(self, lookback: int = 10) -> dict:
        recent = list(self.messages)[-lookback:]
        texts = [m["text"] for m in recent]
        tone = self._estimate_tone(texts)
        topic = self._extract_topic_hint(texts)

        return {
            "recent_messages": recent,
            "dominant_tone": tone,
            "topic_hint": topic
        }

    # -------------------------
    # Detection helpers
    # -------------------------

    def is_repeating(self, new_text: str, threshold: float = 0.85) -> bool:
        """Detect if assistant is repeating itself"""
        if len(self.messages) < 2:
            return False

        last_agent = None
        for msg in reversed(self.messages):
            if msg["role"] == "agent":
                last_agent = msg["text"]
                break

        if not last_agent:
            return False

        similarity = SequenceMatcher(None, new_text, last_agent).ratio()
        return similarity > threshold

    def _estimate_tone(self, texts):
        joined = " ".join(t.lower() for t in texts)

        if any(x in joined for x in ["wtf", "frustrat", "angry"]):
            return "frustrated"
        if any(x in joined for x in ["please", "kindly", "could you"]):
            return "formal"
        if any(x in joined for x in ["bro", "bhai", "lol", "hmm"]):
            return "casual"
        return "neutral"

    def _extract_topic_hint(self, texts):
        joined = " ".join(texts).lower()
        keywords = [
            "sku", "style", "returns", "inventory",
            "ads", "myntra", "ajio", "sales", "roas", "profit"
        ]

        for kw in keywords:
            if re.search(r"\b" + kw + r"\b", joined):
                return kw

        words = re.findall(r"\b[a-z]{3,15}\b", joined)
        stop = {"the", "and", "for", "with", "that", "this", "you"}
        counts = Counter(w for w in words if w not in stop)
        return counts.most_common(1)[0][0] if counts else None

    # -------------------------
    # Persistence
    # -------------------------

    def _save(self):
        try:
            with open(CHAT_BRAIN_FILE, "w", encoding="utf-8") as f:
                json.dump({"messages": list(self.messages)}, f, indent=2)
        except Exception as e:
            print(f"⚠️ ChatBrain save failed: {e}")

    def _load(self):
        if os.path.exists(CHAT_BRAIN_FILE):
            with open(CHAT_BRAIN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.messages = deque(data.get("messages", []), maxlen=self.max_messages)

# -----------------------------
# IntentEmotionEngine
# -----------------------------
class IntentEmotionEngine:
    """
    Improved for RoboRana with ecommerce logic + scope locking
    """

    def __init__(self):

        self.intent_keywords = {
            "sales_summary": [r"sales", r"summary", r"total sales", r"scan"],
            "bottom_seller": [r"lowest", r"bottom", r"poor", r"worst"],
            "top_seller": [r"top", r"best", r"highest"],
            "returns": [r"return", r"refund"],
            "inventory": [r"stock", r"inventory"],
            "command": [r"run", r"export", r"schedule"]
        }

        self.positive = {"good", "great", "perfect"}
        self.negative = {"bad", "error", "problem", "issue"}
        self.confused = {"what", "how", "confused"}
        self.angry = {"wtf", "frustrate", "annoy"}

    # -------------------------
    # Core Detect Function
    # -------------------------

    def detect(self, text: str) -> Dict:
        text = text.lower().strip()

        intent_scores = {}
        for intent, patterns in self.intent_keywords.items():
            score = sum(1 for p in patterns if re.search(p, text))
            if score:
                intent_scores[intent] = score

        if intent_scores:
            intent = max(intent_scores, key=intent_scores.get)
            base_conf = 0.50 + (intent_scores[intent] * 0.15)
        else:
            intent = "casual"
            base_conf = 0.3

        # ------------------------
        # Scope Detection
        # ------------------------
        scope = "unspecified"

        if "today" in text:
            scope = "today"
        elif "yesterday" in text:
            scope = "yesterday"
        elif "7 days" in text or "last 7" in text:
            scope = "7_days"
        elif "month" in text:
            scope = "month"

        # ------------------------
        # Emotion Detection
        # ------------------------
        words = set(re.findall(r"\b[a-z']{2,}\b", text))
        emotion = "neutral"
        emo_score = 0

        if words & self.positive:
            emotion, emo_score = "positive", 0.2
        if words & self.negative:
            emotion, emo_score = "negative", 0.3
        if words & self.confused:
            emotion, emo_score = "confused", 0.3
        if words & self.angry:
            emotion, emo_score = "angry", 0.5

        confidence = min(0.99, base_conf + emo_score)

        return {
            "intent": intent,
            "scope": scope,
            "emotion": emotion,
            "confidence": round(confidence, 2)
        }

# -----------------------------
# Integration Helpers
# -----------------------------

def attach_chatbrain(agent, chatbrain: Optional[ChatBrain] = None):

    if chatbrain is None:
        chatbrain = ChatBrain()

    setattr(agent, "chatbrain", chatbrain)

    def push(role, text, meta=None):
        return chatbrain.push_message(role, text, meta)

    def snapshot(lookback=10):
        return chatbrain.get_snapshot(lookback)

    setattr(agent, "push_chat", push)
    setattr(agent, "chat_snapshot", snapshot)

    return chatbrain


def attach_intent_engine(agent, engine: Optional[IntentEmotionEngine] = None):

    if engine is None:
        engine = IntentEmotionEngine()

    setattr(agent, "intent_engine", engine)

    def detect_intent(text):
        return engine.detect(text)

    setattr(agent, "detect_intent", detect_intent)

    return engine


# -----------------------------
# Self Test
# -----------------------------
if __name__ == "__main__":
    cb = ChatBrain()
    ie = IntentEmotionEngine()

    cb.push_message("user", "scan today sales")
    print("Intent:", ie.detect("scan today sales"))
    print("Snapshot:", cb.get_snapshot())

