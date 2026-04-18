# -*- coding: utf-8 -*-
"""
AI_SYSTEM/CORE_UTILS/conversational_fusion_loop.py

Conversational Fusion Loop
- Orchestrates ChatBrain, IntentEmotionEngine, ContextualVoiceRouter, EmotionReactor
- Loads agents on demand and routes queries to the appropriate specialist agent
- Local, fault-tolerant, and log-friendly

Author: Generated for Sandeep Rana / RoboRana
Version: 1.0 (Operation R.O.B.O.T.A.L.K Phase 1.4)
"""

import importlib
import inspect
import os
import json
import traceback
from typing import Dict, Any, Optional, Tuple

from AI_SYSTEM.CORE_UTILS.chat_brain_and_intent_engine import ChatBrain, IntentEmotionEngine
from AI_SYSTEM.CORE_UTILS.contextual_voice_router import ContextualVoiceRouter, attach_contextual_router
from AI_SYSTEM.CORE_UTILS.emotion_reactor import EmotionReactor, attach_emotion_reactor
from AI_SYSTEM.CORE_UTILS.chat_brain_and_intent_engine import attach_chatbrain, attach_intent_engine

# Config
ROUTES_LOG = os.path.join("AI_SYSTEM", "MEMORY", "fusion_routes.json")
AGENT_LOAD_ORDER = {
    "sales": "AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent",
    "returns": "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
    "inventory": "AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent",
    "finance": "AI_SYSTEM.AGENTS.FINANCE_AGENT.finance_agent",
    "ads": "AI_SYSTEM.AGENTS.ADS_AGENT.ads_agent",
    "manager": "AI_SYSTEM.AGENTS.MANAGER_AGENT.manager_agent",
}

# Common handler method name candidates (tries these in order)
HANDLER_CANDIDATES = [
    "handle_query",
    "handle_message",
    "run_query",
    "generate_response",
    "handle"
]

def _should_emotionally_process(text: str) -> bool:
    if not isinstance(text, str):
        return False
    t = text.strip()
    if not t:
        return False

    structured_markers = [
        "###", "```", "|", "•", "-", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
        "Spend:", "Revenue:", "ROAS", "CTR", "CPC",
        "Ads spend was", "ROAS was", "Please tell me exactly",
        "This looks like", "This seems related", "I could not find enough grounded"
    ]
    if any(marker in t for marker in structured_markers):
        return False

    if "\n" in t and any(line.strip().startswith(("-", "•", "#")) for line in t.splitlines()):
        return False

    return True


# -----------------------------
# Helper: Agent Loader
# -----------------------------
def _instantiate_agent_from_module(module_path: str):
    """
    Try to import a module and instantiate the first class with 'Agent' in its name,
    or any class that looks like an agent. Returns an instance or None.
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        print(f"⚠️ Could not import module '{module_path}': {e}")
        return None

    # find agent-like classes
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        # skip imported classes not defined in module
        if obj.__module__ != mod.__name__:
            continue
        if "Agent" in name or name.lower().endswith("agent"):
            try:
                instance = obj()
                return instance
            except Exception as e:
                # try instantiate without args via other means
                try:
                    instance = obj
                    return instance
                except Exception:
                    print(f"⚠️ Failed to instantiate class '{name}' in {module_path}: {e}")
                    continue

    # fallback: look for a callable named 'main' or 'start' that returns an agent-like object
    for candidate in ("main", "start"):
        fn = getattr(mod, candidate, None)
        if callable(fn):
            try:
                candidate_obj = fn()
                return candidate_obj
            except Exception:
                continue

    return None


# -----------------------------
# Fallback Dummy Agent
# -----------------------------
class DummyAgent:
    def __init__(self, name="dummy"):
        self.name = name
        self._loaded = True

    def handle_query(self, q: str):
        return f"⚠️ (Fallback) I couldn't load a specialist agent for this request. Please try the manager or check logs."

    def __repr__(self):
        return f"<DummyAgent {self.name}>"


# -----------------------------
# Conversational Fusion Loop
# -----------------------------
class ConversationalFusionLoop:
    def __init__(self, load_agents: bool = True, log_routes: bool = True):
        # Core modules
        self.chatbrain = ChatBrain()
        self.intent_engine = IntentEmotionEngine()
        self.voice_router = ContextualVoiceRouter(log_routes=log_routes)
        self.emotion_reactor = EmotionReactor()

        # Cache for agent instances
        self._agents: Dict[str, Any] = {}
        self.log_routes = log_routes

        # Optionally preload common agents
        if load_agents:
            for k, v in AGENT_LOAD_ORDER.items():
                try:
                    self._agents[k] = self._load_agent(k)
                except Exception:
                    self._agents[k] = None

    # -----------------------------
    # Agent loading + attaching shared tools
    # -----------------------------
    def _load_agent(self, agent_key: str):
        """Load or instantiate agent by key using AGENT_LOAD_ORDER mapping."""
        if agent_key in self._agents and self._agents[agent_key] is not None:
            return self._agents[agent_key]

        module_path = AGENT_LOAD_ORDER.get(agent_key)
        if not module_path:
            print(f"⚠️ No module mapping for agent key: {agent_key}")
            inst = DummyAgent(agent_key)
            self._agents[agent_key] = inst
            return inst

        inst = _instantiate_agent_from_module(module_path)
        if inst is None:
            inst = DummyAgent(agent_key)
            self._agents[agent_key] = inst
            return inst

        # ensure agent has name attribute
        if not hasattr(inst, "name"):
            try:
                inst.name = agent_key
            except Exception:
                pass

        # Attach shared modules if not already present
        try:
            attach_chatbrain(inst)
        except Exception:
            pass
        try:
            attach_intent_engine(inst)
        except Exception:
            pass
        try:
            attach_emotion_reactor(inst)
        except Exception:
            pass
        try:
            attach_contextual_router(inst)
        except Exception:
            pass

        self._agents[agent_key] = inst
        return inst

    # -----------------------------
    # Core: Handle user input
    # -----------------------------
    def handle_user_input(self, user_text: str) -> Dict[str, Any]:
        """
        Full orchestrator:
          - push to chatbrain
          - detect intent/emotion
          - route to agent
          - invoke agent handler
          - react emotionally
          - persist & return metadata + text
        """
        result = {
            "ok": False,
            "user_text": user_text,
            "routed_agent": None,
            "routing_confidence": 0.0,
            "raw_response": None,
            "final_response": None,
            "error": None
        }

        try:
            # 1) persist user message
            self.chatbrain.push_message("user", user_text)

            # 2) analyze intent & emotion (use local engine)
            intent_data = self.intent_engine.detect(user_text)
            if not isinstance(intent_data, dict):
                intent_data = {}

            intent = intent_data.get("intent", "unknown")
            emotion = intent_data.get("emotion", "neutral")
            conf = intent_data.get("confidence", 0.0)
            result["detected_intent"] = intent
            result["detected_emotion"] = emotion
            result["intent_confidence"] = conf

            # 3) snapshot for topic hint
            snapshot = self.chatbrain.get_snapshot(lookback=10)
            topic_hint = snapshot.get("topic_hint")

            # 4) route to agent
            agent_key, routing_conf, meta = self.voice_router.route_message(user_text, intent, emotion, topic_hint)
            result["routed_agent"] = agent_key
            result["routing_confidence"] = routing_conf
            result["route_meta"] = meta

            # 5) load agent
            agent_inst = self._load_agent(agent_key) or DummyAgent(agent_key)

            # 6) choose best handler on agent
            raw_response = None
            for h in HANDLER_CANDIDATES:
                handler = getattr(agent_inst, h, None)
                if callable(handler):
                    try:
                        # prefer passing raw text only; some handlers accept (text, ...) signature
                        sig = inspect.signature(handler)
                        if len(sig.parameters) == 1:
                            raw_response = handler(user_text)
                        else:
                            # try common signatures: (text, agent_context) or (text, user_text)
                            try:
                                raw_response = handler(user_text, {"intent": intent, "emotion": emotion, "topic": topic_hint})
                            except Exception:
                                raw_response = handler(user_text)
                        break
                    except Exception as e:
                        # try next handler
                        continue

            # If no handler found, try a generic attribute 'handle' or fallback to DummyAgent
            if raw_response is None:
                if hasattr(agent_inst, "handle"):
                    try:
                        raw_response = agent_inst.handle(user_text)
                    except Exception:
                        raw_response = f"⚠️ Agent {agent_key} could not process the request."
                else:
                    raw_response = f"⚠️ Agent {agent_key} has no callable handler. Fallback in place."

            result["raw_response"] = raw_response

            # 7) Emotionally modulate (prefer agent's own reactor if exists)
            final_response = None
            raw_response_text = str(raw_response) if raw_response is not None else ""
            try:
                should_apply_emotion = _should_emotionally_process(raw_response_text)
                should_apply_emotion = bool(raw_response_text.strip())
                if should_apply_emotion:
                    if hasattr(agent_inst, "react_response") and callable(getattr(agent_inst, "react_response")):
                        final_response = agent_inst.react_response(raw_response_text, emotion=emotion, tone=snapshot.get("dominant_tone", "neutral"), agent_type=agent_key)
                    else:
                        final_response = self.emotion_reactor.react(raw_response_text, emotion=emotion, tone=snapshot.get("dominant_tone", "neutral"), agent_type=agent_key)
                else:
                    final_response = raw_response_text
            except Exception as e:
                final_response = raw_response_text

            if not final_response:
                final_response = str(raw_response) if raw_response is not None else "⚠️ No response generated."
            except Exception as e:
                final_response = raw_response_text

            if not isinstance(final_response, str) or not final_response.strip():
                final_response = raw_response_text if raw_response_text.strip() else "⚠️ I could not generate a stable response. Please retry."

            result["final_response"] = final_response

            # 8) push agent reply to chatbrain
            self.chatbrain.push_message("agent", final_response)

            result["ok"] = True

            # 9) log fused route (separate log file)
            if self.log_routes:
                try:
                    os.makedirs(os.path.dirname(ROUTES_LOG), exist_ok=True)
                    log_entry = {
                        "ts": self.chatbrain.last(1)[0]["ts"] if self.chatbrain.last(1) else None,
                        "user_text": user_text,
                        "intent": intent,
                        "emotion": emotion,
                        "agent": agent_key,
                        "routing_confidence": routing_conf,
                        "final_response_preview": (final_response[:300] if final_response else "")
                    }
                    if os.path.exists(ROUTES_LOG):
                        with open(ROUTES_LOG, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    else:
                        data = []
                    data.append(log_entry)
                    if len(data) > 2000:
                        data = data[-1000:]
                    with open(ROUTES_LOG, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

        except Exception as e:
            traceback_str = traceback.format_exc()
            result["error"] = f"{e}\n{traceback_str}"
            result["ok"] = False

        return result


# -----------------------------
# CLI Quick Test
# -----------------------------
if __name__ == "__main__":
    print("\n=== RoboRana Conversational Fusion Loop — CLI Test ===\n")
    fusion = ConversationalFusionLoop(load_agents=False, log_routes=True)
    print("Type a message (type 'exit' to quit).")
    while True:
        try:
            txt = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break
        if not txt:
            continue
        if txt.lower() in ("exit", "quit"):
            print("Exiting.")
            break

        out = fusion.handle_user_input(txt)
        if out.get("ok"):
            print("\n🧭 Routed to:", out.get("routed_agent"), f"(conf={out.get('routing_confidence')})")
            print("🤖 RoboRana:", out.get("final_response"), "\n")
        else:
            print("⚠️ Error handling message:", out.get("error"))
