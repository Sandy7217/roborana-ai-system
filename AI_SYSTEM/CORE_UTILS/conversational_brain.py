# -*- coding: utf-8 -*-
# ===========================================================
# 🗣️ RoboRana Conversational Brain (Human-like Response Layer)
# ===========================================================
from AI_SYSTEM.CORE_UTILS.nlu_tools import normalize_human_text, smart_summarize_context
import random

CONVERSATION_TONES = {
    "friendly": [
        "Got it, boss! Here's what I found 👇",
        "Sure thing — let's break it down 💡",
        "Okay, here's the story so far 📊",
    ],
    "formal": [
        "Here’s the summary of the requested analysis:",
        "Following is the executive insight report:",
        "The requested performance overview is presented below:",
    ],
    "encouraging": [
        "Nice move asking that — this insight can help optimize things further 🚀",
        "Smart question — here’s what the data says:",
    ],
}

def choose_tone(query: str) -> str:
    """Selects a conversational tone based on query context."""
    q = query.lower()
    if any(k in q for k in ["report", "summary", "overview", "data", "metric"]):
        return "formal"
    elif any(k in q for k in ["show", "batao", "karo", "what", "how", "why"]):
        return "friendly"
    else:
        return "encouraging"

def humanize_response(query: str, response: str) -> str:
    """Adds a conversational intro and a softer human tone."""
    tone = choose_tone(query)
    opener = random.choice(CONVERSATION_TONES[tone])
    final_response = f"{opener}\n\n{response.strip()}"
    return final_response

def preprocess_agent_query(agent, query: str, safe_print=print):
    """Unified pre-processing pipeline for all agents."""
    query = normalize_human_text(query, safe_print=safe_print)
    return query

def postprocess_agent_response(agent, query: str, response: str):
    """Unified post-processing to humanize output."""
    return humanize_response(query, response)
