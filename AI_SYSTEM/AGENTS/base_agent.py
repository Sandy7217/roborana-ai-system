# -*- coding: utf-8 -*-
# ===========================================================
# 🤖 Base Agent — Core Brain of RoboRana AI (Human-Aware Version)
#    + Cognitive Dual Brain (Knowledge + Formula) — Modular (Option 2)
# ===========================================================
import os
import json
import ast
from datetime import datetime
from difflib import get_close_matches
from dotenv import load_dotenv
from openai import OpenAI
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ===========================================================
# 🌍 Environment & OpenAI Client Initialization
# ===========================================================
load_dotenv(dotenv_path="AI_SYSTEM/.env")

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"⚠️ Failed to initialize OpenAI client: {e}")
    client = None


# ===========================================================
# 🧠 Memory Paths (Dual Memory + Conversation)
# ===========================================================
BASE_MEM_DIR = "AI_SYSTEM/MEMORY"
os.makedirs(BASE_MEM_DIR, exist_ok=True)

KNOWLEDGE_PATH = os.path.join(BASE_MEM_DIR, "knowledge_memory.json")
FORMULA_PATH = os.path.join(BASE_MEM_DIR, "formula_memory.json")
CONV_PATH = os.path.join(BASE_MEM_DIR, "conversation_memory.json")

# Ensure files exist (start with empty dict/list)
for p, default in [(KNOWLEDGE_PATH, {}), (FORMULA_PATH, {}), (CONV_PATH, [])]:
    if not os.path.exists(p):
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Could not create memory file {p}: {e}")


# ===========================================================
# 🔐 Safe Formula Evaluator (AST-based, no exec)
# ===========================================================
ALLOWED_AST_NODES = {
    'Expression', 'BinOp', 'UnaryOp', 'Num', 'Name', 'Load',
    'Add', 'Sub', 'Mult', 'Div', 'FloorDiv', 'Mod', 'Pow',
    'UAdd', 'USub', 'Call', 'Tuple', 'List', 'Dict',
    'Compare', 'Eq', 'NotEq', 'Lt', 'LtE', 'Gt', 'GtE',
    'BoolOp', 'And', 'Or', 'IfExp'
}

ALLOWED_NAMES = {
    # common math constants could be added if needed
}

class SafeEvalVisitor(ast.NodeVisitor):
    def generic_visit(self, node):
        nodename = node.__class__.__name__
        if nodename not in ALLOWED_AST_NODES:
            raise ValueError(f"Disallowed AST node: {nodename}")
        return super().generic_visit(node)

def safe_eval(expr: str, variables: dict):
    """
    Evaluate a numeric expression safely using AST parsing.
    Supports arithmetic, parentheses, and variable names provided in `variables`.
    """
    try:
        parsed = ast.parse(expr, mode='eval')
        SafeEvalVisitor().visit(parsed)
        compiled = compile(parsed, filename="<ast>", mode="eval")
        # Evaluate with restricted globals and provided locals
        return eval(compiled, {"__builtins__": {}}, dict(variables))
    except Exception as e:
        raise ValueError(f"Safe eval error: {e}")


# ===========================================================
# 🧠 BaseAgent Class Definition
# ===========================================================
class BaseAgent:
    def __init__(self, name, role_prompt):
        self.name = name
        self.role_prompt = role_prompt

        # small in-memory caches to reduce file I/O per process
        self._knowledge_cache = None
        self._formula_cache = None

        # -------------------------------------------------------
    # 🧠 Core Reasoning Function (Hybrid GPT + Reasoner v1.4)
    # -------------------------------------------------------
    def think(self, query):
        """
        Unified reasoning layer — primary GPT model with intelligent fallback
        to GPT Reasoner v1.4 for structured interpretation.
        """
        try:
            from AI_SYSTEM.CORE_UTILS.gpt_reasoner import gpt_reason_interpretation
        except Exception as e:
            print(f"⚠️ GPT Reasoner import failed: {e}")
            gpt_reason_interpretation = None

        if not client:
            print(f"⚠️ OpenAI client not initialized for {self.name}.")
            return f"⚠️ Reasoning unavailable — client not initialized."

        try:
            print("🧠 [Think Path] Using GPT-4o-mini …")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.role_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7
            )
            if response is None:
                return None
            try:
                if not response or not getattr(response, "choices", None):
                    reply = None
                else:
                    first_choice = response.choices[0] if len(response.choices) > 0 else None
                    message = first_choice.message if first_choice and getattr(first_choice, "message", None) else None
                    content = message.content if message and getattr(message, "content", None) else None
                    reply = content.strip() if isinstance(content, str) else None                    
                
            except Exception:
                    reply = None 

            if reply:
                return reply

            if gpt_reason_interpretation:
                print("🔁 [Think Path] Falling back to GPT Reasoner v1.4 …")
                reason_output = gpt_reason_interpretation(query)
                if reason_output and isinstance(reason_output, dict):
                    readable = (
                        f"Action: {reason_output.get('action', 'unknown')}, "
                        f"Scope: {reason_output.get('scope', 'all_time')}, "
                        f"Channel: {reason_output.get('channel', 'overall')}, "
                        f"Confidence: {reason_output.get('confidence', 0):.2f}"
                    )
                    return readable

            return None

        except Exception as e:
            print(f"⚠️ think() reasoning error: {e}")
            try:
                if gpt_reason_interpretation:
                    print("🔁 [Think Path] Recovering via GPT Reasoner v1.4 …")
                    reason_output = gpt_reason_interpretation(query)
                    if reason_output and isinstance(reason_output, dict):
                        readable = (
                            f"Action: {reason_output.get('action', 'unknown')}, "
                            f"Scope: {reason_output.get('scope', 'all_time')}, "
                            f"Channel: {reason_output.get('channel', 'overall')}, "
                            f"Confidence: {reason_output.get('confidence', 0):.2f}"
                        )
                        return readable
            except Exception as e2:
                print(f"⚠️ GPT Reasoner fallback failed: {e2}")
            return None

    # ===========================================================
    # 🧩 HUMAN UNDERSTANDING + CONVERSATIONAL LAYER (EXISTING HOOKS)
    # ===========================================================
    def process_user_input(self, query: str):
        """
        Handles Natural Language Understanding (NLU).
        Keeps modular behavior: first tries CORE_UTILS's NLU, then applies learned knowledge and autocorrect.
        """
        try:
            from AI_SYSTEM.CORE_UTILS.conversational_brain import preprocess_agent_query
            processed = preprocess_agent_query(self, query, safe_print=print)
        except Exception as e:
            print(f"⚠️ NLU processing failed: {e}")
            processed = query

        # Apply knowledge memory replacements
        try:
            processed = self.apply_knowledge_memory(processed)
        except Exception as e:
            print(f"⚠️ apply_knowledge_memory failed: {e}")

        # Autocorrect query words using known knowledge keys
        try:
            processed = self.autocorrect_query_words(processed)
        except Exception as e:
            # non-fatal
            pass

        return processed

    def process_agent_output(self, query: str, response: str):
        if not isinstance(response, str):
            response = ""
        """
        Adds conversational tone and human-like phrasing to responses.
        Uses CORE_UTILS postprocessing when available, then runs human_reason to:
         - detect redirection needs
         - handle formula requests and calculation
         - add 'should I do this?' prompts
         - ask for clarification when confused
        """
        if not isinstance(response, str):
            response = ""
           
        try:
            from AI_SYSTEM.CORE_UTILS.conversational_brain import postprocess_agent_response
            processed = postprocess_agent_response(self, query, response)
        except Exception as e:
            print(f"⚠️ Conversational formatting failed: {e}")
            processed = response

        # Enrich with reasoning and conversational features
        try:
            processed = self.human_reason(query, processed)
        except Exception as e:
            print(f"⚠️ human_reason failed: {e}")

        return processed

    # ===========================================================
    # 🔁 Memory Load/Save Utilities (Knowledge & Formula)
    # ===========================================================
    def load_knowledge_memory(self):
        if self._knowledge_cache is not None:
            return self._knowledge_cache
        try:
            with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                self._knowledge_cache = json.load(f) or {}
        except Exception:
            self._knowledge_cache = {}
        return self._knowledge_cache

    def save_knowledge_memory(self, data: dict):
        try:
            with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._knowledge_cache = data
            return True
        except Exception as e:
            print(f"⚠️ Could not save knowledge memory: {e}")
            return False

    def load_formula_memory(self):
        if self._formula_cache is not None:
            return self._formula_cache
        try:
            with open(FORMULA_PATH, "r", encoding="utf-8") as f:
                self._formula_cache = json.load(f) or {}
        except Exception:
            self._formula_cache = {}
        return self._formula_cache

    def save_formula_memory(self, data: dict):
        try:
            with open(FORMULA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._formula_cache = data
            return True
        except Exception as e:
            print(f"⚠️ Could not save formula memory: {e}")
            return False

    # Conversation memory (append, keep last N)
    def remember_conversation(self, query: str, response: str, keep=15):
        try:
            data = []
            if os.path.exists(CONV_PATH):
                with open(CONV_PATH, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = []
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "agent": self.name,
                "query": query,
                "response": response
            }
            data.append(entry)
            data = data[-keep:]
            with open(CONV_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ remember_conversation failed: {e}")

    # ===========================================================
    # 🧩 Knowledge Memory Operations (Words, Slang, Abbrev)
    # ===========================================================
    def detect_learning_type(self, user_text: str) -> str:
        """
        Heuristic to decide whether an input is teaching a formula or a word/meaning.
        If the user-provided meaning contains arithmetic operators or parentheses, treat as formula.
        """
        sample = user_text.strip().lower()
        # If arithmetic operators present or common formula words like '=', treat as formula
        if any(op in sample for op in ["+", "-", "*", "/", "%", "(", ")", "**", "^", "="]):
            return "formula"
        return "word"

    def learn_new_term(self, term: str, meaning: str):
        """Store term -> meaning in knowledge memory."""
        try:
            data = self.load_knowledge_memory()
            data[term.lower()] = meaning
            saved = self.save_knowledge_memory(data)
            return saved
        except Exception as e:
            print(f"⚠️ learn_new_term failed: {e}")
            return False

    # ===========================================================
    # 🧮 Formula Memory Operations
    # ===========================================================
    def learn_formula(self, name: str, formula_str: str, description: str = None):
        """
        Save the formula string (as an expression) for later safe evaluation.
        Expect the formula_str to be something like: "(revenue - cost_of_sales) / revenue * 100"
        """
        try:
            data = self.load_formula_memory()
            data[name.lower()] = {
                "formula": formula_str,
                "description": description or f"User-defined formula for {name}"
            }
            saved = self.save_formula_memory(data)
            return saved
        except Exception as e:
            print(f"⚠️ learn_formula failed: {e}")
            return False

    def calculate_from_formula(self, name: str, context_vars: dict):
        """
        Compute a saved formula using context_vars dictionary.
        Returns (result, True) on success, (error_message, False) on failure or missing formula.
        """
        try:
            data = self.load_formula_memory()
            key = name.lower()
            if key not in data:
                return None, False
            formula = data[key].get("formula")
            if not formula:
                return None, False
            # safe eval
            try:
                result = safe_eval(formula, context_vars)
                return result, True
            except Exception as e:
                return f"⚠️ Calculation error: {e}", False
        except Exception as e:
            return f"⚠️ calculate_from_formula failed: {e}", False

    # ===========================================================
    # 🔁 Apply Knowledge Memory (replace known terms in user queries)
    # ===========================================================
    def apply_knowledge_memory(self, query: str):
        """
        Replace occurrences of known terms with their canonical abbreviation/meaning, if helpful.
        Example: if 'stock keeping unit' -> 'sku' exists, replace long form with 'sku' or vice-versa.
        We'll replace longer phrases first to avoid partial matches.
        """
        try:
            data = self.load_knowledge_memory()
            if not data:
                return query
            # Sort keys by length descending to replace long phrases first
            keys = sorted(data.keys(), key=lambda x: -len(x))
            q_lower = query
            for k in keys:
                if k.lower() in q_lower.lower():
                    # replace case-insensitively while preserving original case where possible
                    # simple approach: replace all lowercase occurrences
                    q_lower = q_lower.replace(k, data[k])
            return q_lower
        except Exception as e:
            print(f"⚠️ apply_knowledge_memory error: {e}")
            return query

    # ===========================================================
    # ✏️ Autocorrect / Fuzzy Matching for Query Words
    # ===========================================================
    def autocorrect_query_words(self, query: str, cutoff=0.8):
        """
        Use knowledge keys as known words and attempt to autocorrect typos.
        This is a light-weight fuzzy correction: splits the query and corrects tokens that closely match known keys.
        """
        try:
            known = list(self.load_knowledge_memory().keys())
            if not known:
                return query
            tokens = query.split()
            corrected = []
            for tok in tokens:
                # if exact known, keep
                if tok.lower() in known:
                    corrected.append(tok)
                    continue
                # find close match
                m = get_close_matches(tok.lower(), known, n=1, cutoff=cutoff)
                if m:
                    corrected.append(m[0])
                else:
                    corrected.append(tok)
            return " ".join(corrected)
        except Exception as e:
            print(f"⚠️ autocorrect_query_words error: {e}")
            return query

    # ===========================================================
    # 🧭 Intent Detection & Routing (lightweight)
    # ===========================================================
    INTENT_KEYWORDS = {
        "sales": ["sale", "sales", "revenue", "orders", "top seller", "sku", "aov"],
        "returns": ["return", "rto", "refund", "exchange"],
        "inventory": ["stock", "inventory", "quantity", "reorder", "stockout", "stock keeping unit", "sku"],
        "ads": ["ads", "advert", "advertising", "campaign", "roas", "impression", "ctr", "cpc"],
        "manager": ["summary", "overview", "performance", "report", "manager"],
        "creative": ["ppt", "presentation", "pdf", "slide", "visual", "export"]
    }

    def detect_agent_context(self, query: str):
        q = query.lower()
        for agent, keys in self.INTENT_KEYWORDS.items():
            if any(k in q for k in keys):
                return agent
        return "unknown"

    # ===========================================================
    # 🧠 Human Tone & Conversation Wrapping
    # ===========================================================
    def human_talk(self, query: str, response: str) -> str:
        """
        Wrap the response in a human-friendly opener/closer and small tone adjustments.
        This keeps it consistent across agents.
        """
        try:
            q = query.lower()
            emoji = "🤓"
            if any(x in q for x in ["issue", "error", "problem", "fail", "failed"]):
                emoji = "🧠"
            elif any(x in q for x in ["good", "great", "nice", "thanks", "thank"]):
                emoji = "😄"
            elif any(x in q for x in ["urgent", "now", "immediately"]):
                emoji = "⚡"

            openers = [
                f"{emoji} Sure — here you go!",
                f"{emoji} Got it, checking that now.",
                f"{emoji} Okay, here’s what I found:",
                f"{emoji} Alright — quick summary below."
            ]
            import random
            opener = random.choice(openers)
            closer = "\n\nAnything else you want me to check or do? (I can run the report / save / visualize.)"
            # Compose final
            final = f"{opener}\n\n{response}\n\n{closer}"
            return final
        except Exception as e:
            print(f"⚠️ human_talk error: {e}")
            return response

    # ===========================================================
    # 🤖 Human Reasoner: redirection, formula handling, clarification prompts
    # ===========================================================
    def human_reason(self, query: str, response: str) -> str:
        """
        The central human-like decision layer:
        - Detects if query belongs to another agent and suggests redirecting
        - Detects requests to calculate metrics and computes them if formula is known
        - If unknown formula, asks the user to teach
        - Adds human_talk wrapper and stores conversation memory
        """
        try:
            q = query.lower().strip()

            # 1) Detect intent -> if belongs to other agent, suggest redirect
            intent_agent = self.detect_agent_context(q)
            current_agent_key = self.name.lower().replace(" agent", "")
            if intent_agent != "unknown" and intent_agent != current_agent_key:
                # Suggest redirect
                suggestion = (f"Hey, this looks like a question for the **{intent_agent.title()} Agent**. "
                              f"Would you like me to forward this to them for a detailed answer? (reply 'yes' to redirect)")
                # Wrap and remember
                self.remember_conversation(query, suggestion)
                return self.human_talk(query, suggestion)

            # 2) If asks to calculate something — try to compute using formula memory
            if any(tok in q for tok in ["calculate", "what is", "compute", "show me", "how much is", "give me the"]):
                # Attempt to extract metric name (simple heuristic)
                metric = None
                tokens = q.replace("?", "").split()
                # pick first short alpha token that matches a known formula key
                formula_keys = list(self.load_formula_memory().keys())
                for t in tokens:
                    if t.lower() in formula_keys:
                        metric = t.lower()
                        break
                # fallback: look for exact phrase like 'ros' or 'roas' in the query
                if not metric:
                    for fk in formula_keys:
                        if fk in q:
                            metric = fk
                            break

                if metric:
                    # gather a context_vars dictionary - try to extract numeric words or fallback to placeholders
                    context_vars = self.extract_context_variables_from_query(q)
                    result, ok = self.calculate_from_formula(metric, context_vars)
                    if ok:
                        text = f"📊 {metric.upper()} = {result}"
                        self.remember_conversation(query, text)
                        return self.human_talk(query, text)
                    else:
                        # ask for formula if not known or calc error
                        if result is None:
                            ask = self.ask_for_formula(metric)
                            self.remember_conversation(query, ask)
                            return self.human_talk(query, ask)
                        else:
                            # calculation error
                            self.remember_conversation(query, result)
                            return self.human_talk(query, result)

            # 3) If the response seems to indicate unknown or confusion, ask for clarification
            if any(token in response.lower() for token in ["i'm not sure", "i do not know", "unknown", "can't find", "couldn't find"]):
                clarification = self.handle_confusion(query)
                self.remember_conversation(query, clarification)
                return self.human_talk(query, clarification)

            # 4) Default: humanize and remember
            self.remember_conversation(query, response)
            return self.human_talk(query, response)

        except Exception as e:
            print(f"⚠️ human_reason encountered error: {e}")
            # fallback: basic human talk
            try:
                self.remember_conversation(query, response)
            except:
                pass
            return self.human_talk(query, response)

    # ===========================================================
    # 🔎 Helper: extract numeric/context variables from query (very basic)
    #    In future you can hook this to actual data fetchers (Sales/Ads) for real values.
    # ===========================================================
    def extract_context_variables_from_query(self, query: str) -> dict:
        """
        Lightweight heuristic to create a context dict to use in formulas.
        This should be replaced by real data lookup in production:
        - If a timeframe is asked (last 7 days), pull sums from Sales/Ads.
        - For now, attempt to find numbers in the query or return placeholders (0).
        """
        vars = {}
        # try to find integers/floats in the query
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", query)
        # map common names if present
        if "revenue" in query:
            vars["revenue"] = float(nums[0]) if nums else 0.0
        if "cost" in query or "cost_of_sales" in query:
            vars["cost_of_sales"] = float(nums[1]) if len(nums) > 1 else 0.0
        if "ad_spend" in query or "ads" in query:
            vars["ad_spend"] = float(nums[0]) if nums else 0.0
        # default placeholders (so safe_eval doesn't crash if variable missing)
        # Real integration: replace with sum over date range from Sales/Ads DB
        for k in ["revenue", "cost_of_sales", "ad_spend", "returns", "gross_profit", "average_inventory_cost"]:
            if k not in vars:
                vars[k] = 0.0
        return vars

    # ===========================================================
    # 🗣️ Clarification, Ask-for-Formula and Confusion Handlers
    # ===========================================================
    def ask_for_formula(self, metric_name: str) -> str:
        return (f"🤔 I don't yet know how to calculate **{metric_name.upper()}**. "
                "Can you please tell me the formula (for example: ROS = (revenue - cost_of_sales) / revenue * 100)? "
                "I'll learn it and use it next time.")

    def handle_confusion(self, query: str) -> str:
        return (f"🤔 Sorry, I didn't fully understand: '{query}'. "
                "Could you rephrase or give an example? If it's a specific term, you can teach me (e.g. 'SKU means Stock Keeping Unit').")

    # ===========================================================
    # 🔁 Learn-from-user orchestrator: figures out whether user taught a word or a formula
    # ===========================================================
    def learn_from_user(self, term: str, explanation: str, description: str = None) -> str:
        """
        Decide whether explanation is a formula or a word meaning, and save accordingly.
        Returns success message or error.
        """
        try:
            ltype = self.detect_learning_type(explanation)
            if ltype == "formula":
                ok = self.learn_formula(term, explanation, description)
                if ok:
                    return f"✅ Learned formula for '{term}': {explanation}"
                else:
                    return "⚠️ Failed to save formula."
            else:
                ok = self.learn_new_term(term, explanation)
                if ok:
                    return f"✅ Learned meaning for '{term}': {explanation}"
                else:
                    return "⚠️ Failed to save meaning."
        except Exception as e:
            return f"⚠️ learn_from_user failed: {e}"

    # ===========================================================
    # 🔁 Redirect helper (uses agent_router if present)
    # ===========================================================
    def redirect_to_agent(self, agent_name: str, query: str) -> str:
        """
        Try to call the target agent module and return its stdout.
        This is a best-effort helper; if agent_router exists in CORE_UTILS, use that.
        """
        try:
            # Prefer centralized router if exists
            try:
                from AI_SYSTEM.CORE_UTILS.agent_router import redirect_to_agent as router_call
                return router_call(agent_name, query)
            except Exception:
                # fallback: attempt to call module directly via subprocess
                import subprocess, sys
                module_path = f"AI_SYSTEM.AGENTS.{agent_name.upper()}_AGENT.{agent_name.lower()}_agent"
                proc = subprocess.run([sys.executable, "-m", module_path, query], capture_output=True, text=True, timeout=300)
                return proc.stdout or proc.stderr
        except Exception as e:
            return f"⚠️ Redirect failed: {e}"

# ===========================================================
# 🧠 RoboRana Unified Intelligence Hook (Auto Injection)
# ===========================================================
try:
    from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic

    # ✅ Patch BaseAgent.__init__ to inject shared logic into all future agent instances
    _original_init = BaseAgent.__init__

    def _init_with_shared_logic(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        try:
            integrate_shared_logic(self)
        except Exception as e:
            print(f"⚠️ Failed to inject shared logic into {getattr(self, 'name', 'Unknown Agent')}: {e}")

    BaseAgent.__init__ = _init_with_shared_logic

    print("\n=====================================================")
    print("✅ Shared logic auto-injection enabled for all agents.")
    print("🧩 Central Intelligence Module: ACTIVE")
    print("=====================================================\n")

except Exception as e:
    print(f"⚠️ Shared logic setup failed: {e}")
