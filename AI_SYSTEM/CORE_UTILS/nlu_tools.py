# -*- coding: utf-8 -*-
# ================================================
# 🧩 RoboRana NLU + Context Tools (HLC-v2)
# - upgrades: adds NLUEngine (embedding-backed, context-aware)
# - preserves: normalize_human_text, smart_summarize_context
# ================================================
from typing import Optional, Dict, Any, List
import re
import math

# keep your existing imports & helpers
try:
    from langdetect import detect
except Exception:
    detect = None  # optional

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None  # optional

try:
    from spellchecker import SpellChecker
except Exception:
    SpellChecker = None

# optional embedding NLU (graceful fallback)
try:
    from sentence_transformers import SentenceTransformer, util
except Exception:
    SentenceTransformer = None
    util = None

# initialize spell if available
spell = SpellChecker(distance=1) if SpellChecker else None

COMMON_SHORTCUTS = {
    "sku": "product",
    "rev": "revenue",
    "qty": "quantity",
    "sel": "sale",
    "wek": "week",
    "bro": "",
    "batao": "show",
    "karo": "do",
    "dekh": "show",
    "pls": "please",
    "bata": "tell",
}

def normalize_human_text(text: str, safe_print=print) -> str:
    """Translates Hindi/Hinglish → English, fixes typos & slang.
    Keeps original semantics; safe fallback if langdetect/translator missing.
    """
    original = text
    try:
        if detect:
            lang = detect(text)
        else:
            lang = "en"
        if lang != "en" and GoogleTranslator:
            try:
                text = GoogleTranslator(source=lang, target="en").translate(text)
            except Exception:
                # translator failed — keep original
                pass
    except Exception:
        # language detection failed — continue with original text
        pass

    words: List[str] = []
    for w in text.split():
        w_low = w.lower()
        if w_low in COMMON_SHORTCUTS:
            repl = COMMON_SHORTCUTS[w_low]
            if repl:
                words.append(repl)
            # if repl is empty string -> skip filler
        else:
            if spell:
                try:
                    corrected = spell.correction(w_low)
                except Exception:
                    corrected = w_low
            else:
                corrected = w_low
            words.append(corrected or w_low)

    normalized = " ".join(words)
    normalized = (
        normalized.replace(" pls ", " please ")
        .replace(" bro ", " ")
        .replace(" bata ", " tell ")
    )
    if safe_print:
        safe_print(f"🧩 NLU normalized: {original!r} → {normalized!r}")
    return normalized


def smart_summarize_context(agent, text: str, label="RAG Context", max_chars=7000):
    """Summarizes long RAG context using the agent’s reasoning model."""
    if not isinstance(text, str):
        return text
    if len(text) <= max_chars:
        return text

    if agent:
        try:
            prompt = f"""
            Summarize the following {label} into concise bullet points:
            Focus on insights, metrics, patterns, and actionables.
            --- BEGIN ---
            {text[:16000]}
            --- END ---
            """
            summary = agent.think(prompt)
            safe_print = getattr(agent, "safe_print", print)
            safe_print(f"✅ {label} summarized successfully.")
            return summary
        except Exception as e:
            print(f"⚠️ Summarization failed: {e}")
    return text[:max_chars] + "\n[...truncated...]"


# ----------------------------
# NLU Engine - local, context-aware
# ----------------------------
class NLUEngine:
    """
    Lightweight NLU engine that returns structured interpretation:
    {
      action: str,
      scope: str,
      channel: str,
      granularity: str,
      confidence: float,
      raw: {...}
    }

    Uses sentence-transformers if available; otherwise uses template matching.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", verbose: bool = True):
        self.verbose = verbose
        self.model = None
        self.embeddings_enabled = False

        if SentenceTransformer and util:
            try:
                self.model = SentenceTransformer(model_name)
                self.embeddings_enabled = True
                if self.verbose:
                    print(f"🧠 NLUEngine loaded embedding model: {model_name}")
            except Exception as e:
                self.model = None
                self.embeddings_enabled = False
                if self.verbose:
                    print(f"⚠️ NLUEngine: embedding model load failed: {e}")

        # domain templates (examples) — extend as needed
        self.templates = {
            "summarize_sales": [
                "show me sales summary", "sales report", "7 day sales", "sales overview", "sales data",
                "show sales", "weekly sales", "last 7 days sales", "7 day sales summary", "sales summary"
            ],
            "compare_channels": [
                "sales by portal", "sales by channel", "compare marketplaces", "each platform sales",
                "portal wise sales", "myntra vs ajio sales", "channel comparison"
            ],
            "style_analysis": [
                "sales by style", "top styles", "style-wise sales", "design performance",
                "which style sold best", "style summary"
            ],
            "profitability": [
                "profit", "margin", "roi", "profitability report", "profit by sku", "profit by style"
            ],
            "returns_summary": [
                "returns", "return rate", "which skus returned", "returns by portal", "return reason"
            ],
            "inventory_health": [
                "slow moving", "fast moving", "days of stock", "stock cover", "inventory aging"
            ]
        }

        # precompute template embeddings if model available
        self._template_embeddings = {}
        if self.embeddings_enabled:
            try:
                for action, examples in self.templates.items():
                    self._template_embeddings[action] = self.model.encode(examples, convert_to_tensor=True)
            except Exception:
                self._template_embeddings = {}

    # -------------------------
    # helpers
    # -------------------------
    @staticmethod
    def _extract_scope_from_text(text: str) -> str:
        """Return scopes like '7_days', '30_days', '365_days', 'week', 'month', 'all_time'."""
        t = text.lower()
        # match "last 7 days" or "7 day" "7days"
        m = re.search(r"last\s*(\d+)\s*day", t) or re.search(r"(\d+)\s*day", t)
        if m:
            n = int(m.group(1))
            return f"{n}_days"
        if re.search(r"\blast\s*week\b", t) or re.search(r"\bthis week\b", t):
            return "7_days"
        if re.search(r"\blast\s*month\b", t) or re.search(r"\bthis month\b", t):
            return "30_days"
        if re.search(r"\byear\b", t):
            return "365_days"
        return "all_time"

    @staticmethod
    def _infer_channel_from_text_and_context(text: str, context_topic: Optional[str]) -> str:
        """Try to extract a channel (myntra, ajio, flipkart, amazon) or fallback to context/topic or 'all'."""
        t = text.lower()
        for ch in ["myntra", "ajio", "flipkart", "amazon", "amazon.in", "ajio.in"]:
            if ch in t:
                return ch
        if context_topic:
            return context_topic
        # search for common portal words
        if "portal" in t or "channel" in t or "marketplace" in t:
            return "all"
        return "all"

    @staticmethod
    def _extract_granularity(text: str) -> str:
        t = text.lower()
        if "style" in t or "design" in t:
            return "style"
        if "sku" in t or "product" in t or "item" in t:
            return "sku"
        if "portal" in t or "channel" in t:
            return "portal"
        return "sku"

    # -------------------------
    # main interpret function
    # -------------------------
    def interpret(self, raw_text: str, context_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Interpret user text into structured action.
        context_snapshot: output of ChatBrain.get_snapshot() (may include topic_hint)
        """
        if not isinstance(raw_text, str):
            raw_text = str(raw_text or "")

        # 1) normalize (translate / spell / shortcuts)
        text = normalize_human_text(raw_text, safe_print=(print if self.verbose else None)).strip()
        if self.verbose:
            print(f"🧩 NLU interpret input → {text!r}")

        # 2) quick pattern checks (fast)
        if re.search(r"\b(top|best|highest|most sold|fast moving)\b", text):
            quick_action = "summarize_sales"
            quick_conf = 0.55
        elif re.search(r"\b(bottom|least|slow moving|worst)\b", text):
            quick_action = "inventory_health"
            quick_conf = 0.52
        else:
            quick_action = None
            quick_conf = 0.0

        # 3) embedding-based similarity (preferred) OR template matching fallback
        best_action = None
        best_score = -1.0

        if self.embeddings_enabled and self._template_embeddings:
            try:
                text_emb = self.model.encode(text, convert_to_tensor=True)
                for action, emb in self._template_embeddings.items():
                    # cosine similarities (mean over examples)
                    score = util.cos_sim(text_emb, emb).mean().item()
                    if score > best_score:
                        best_score = score
                        best_action = action
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ NLU embedding interpret error: {e}")
                best_action = None
                best_score = -1.0
        else:
            # fallback: naive example substring matching
            for action, examples in self.templates.items():
                for ex in examples:
                    if ex in text:
                        best_action = action
                        best_score = max(best_score, 0.45)
            # last fallback: quick_action
            if not best_action and quick_action:
                best_action = quick_action
                best_score = quick_conf

        # 4) If embedding confidence low but we detect explicit time ranges or summary words — boost
        scope = self._extract_scope_from_text(text)
        if best_score < 0.4:
            if any(k in text for k in ["sales", "summary", "report", "overview", "7 day", "30 day", "weekly"]):
                if self.verbose:
                    print("🧠 NLU: low embedding score but found 'sales' keywords — boosting to 'summarize_sales'")
                best_action = best_action or "summarize_sales"
                best_score = max(best_score, 0.45)

        # Force fallback to quick_action if still nothing
        if not best_action and quick_action:
            best_action = quick_action
            best_score = max(best_score, quick_conf)

        # 5) build final structured output
        context_topic = None
        if isinstance(context_snapshot, dict):
            context_topic = context_snapshot.get("topic_hint")

        channel = self._infer_channel_from_text_and_context(text, context_topic)
        granularity = self._extract_granularity(text)

        # compute final confidence in [0,1]
        conf = round(float(best_score if best_score >= 0 else 0.0), 2)
        conf = max(conf, 0.1)  # never zero

        result = {
            "action": best_action or "unknown",
            "scope": scope or "all_time",
            "channel": channel or "all",
            "granularity": granularity,
            "confidence": conf,
            "raw": {
                "original": raw_text,
                "normalized": text,
                "template_score": best_score,
                "context_topic": context_topic
            }
        }

        if self.verbose:
            print(f"🧠 NLU interpreted → {result}")

        return result


# If used as a script for quick local tests
if __name__ == "__main__":
    nlu = NLUEngine(verbose=True)
    tests = [
        "show me 7 day sales summary",
        "how many sold last week on myntra",
        "top styles this month",
        "show slow moving items",
        "profit by sku last quarter",
        "myntrappmp sale",  # typo example
    ]
    for t in tests:
        out = nlu.interpret(t, context_snapshot={"topic_hint": None})
        print("---")
        print(t, "=>", out)
