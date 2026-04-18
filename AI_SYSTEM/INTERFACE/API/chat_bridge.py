# =========================================================
# 🤖 RoboRana Chat Bridge v1.0
# - Unified interface between Streamlit chat and local agents
# - Handles text, files, and contextual memory
# - Returns structured output to frontend
# =========================================================

import os, sys, json, tempfile, subprocess, shutil
from datetime import datetime
from pathlib import Path
import pandas as pd

# =========================================================
# Configuration
# =========================================================
BASE_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data")
CHAT_MEMORY_DIR = BASE_PATH / "AI_SYSTEM" / "MEMORY" / "chat_sessions"
CHAT_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = BASE_PATH / "AI_SYSTEM" / "INTERFACE" / "settings_ui.json"
CFG = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")) if SETTINGS_FILE.exists() else {}

# Default Python environment
PYTHON_PATH = CFG.get("VENV_PY", str(BASE_PATH / ".venv312" / "Scripts" / "python.exe"))
AGENTS = CFG.get("AGENTS", {})

# =========================================================
# Utility Functions
# =========================================================
def safe_print(*args):
    try:
        print(*args)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        print(msg.encode("ascii", errors="ignore").decode("ascii"))

def ensure_dir(p):
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_uploaded_file(uploaded_file, agent_name="General"):
    """Save uploaded file to temp path for agent access."""
    if not uploaded_file:
        return None
    folder = ensure_dir(BASE_PATH / "TEMP_UPLOADS" / agent_name)
    save_path = folder / uploaded_file.name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(save_path)

def save_chat_history(agent_name, user_msg, agent_reply):
    """Append to persistent chat memory JSON file."""
    folder = ensure_dir(CHAT_MEMORY_DIR / agent_name)
    file_path = folder / f"{datetime.now().strftime('%Y%m%d')}.json"
    history = []
    if file_path.exists():
        try:
            history = json.loads(file_path.read_text(encoding="utf-8"))
        except:
            history = []
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_msg,
        "agent": agent_reply,
    })
    file_path.write_text(json.dumps(history, indent=4, ensure_ascii=False), encoding="utf-8")

def run_local_agent(agent_name, query_text, file_path=None, timeout=200):
    """Run a local agent module in subprocess and return clean stdout."""
    if agent_name not in AGENTS:
        return {"text": f"❌ Unknown agent: {agent_name}"}
    module = AGENTS[agent_name]
    py_exec = PYTHON_PATH if Path(PYTHON_PATH).exists() else sys.executable
    cmd = [py_exec, "-m", module]
    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_PATH),
            text=True,
            encoding="utf-8",
        )
        payload = f"{query_text}\nexit\n"
        out, _ = p.communicate(payload, timeout=timeout)

        # Clean logs — strip emojis, progress, spinner frames
        clean = []
        for line in out.splitlines():
            if not line.strip():
                continue
            if any(x in line for x in ["🔧", "✅", "📁", "⚠️", "📦", "📝", "🚀"]):
                continue
            clean.append(line)
        text_output = "\n".join(clean[-100:]).strip()
        return {"text": text_output}
    except subprocess.TimeoutExpired:
        return {"text": "⏱️ Agent took too long to respond."}
    except Exception as e:
        return {"text": f"❌ Execution error: {e}"}

# =========================================================
# Main Chat Bridge Entry Point
# =========================================================
def query_agent(agent_name: str, context: dict):
    """
    context = {
        "text": "user query",
        "file_path": "optional path",
        "chat_history": [...],
    }
    """
    query_text = context.get("text", "").strip()
    file_path = context.get("file_path")
    chat_history = context.get("chat_history", [])

    if not query_text:
        return {"text": "⚠️ Please enter a valid message."}

    # Pre-Process: Add file mention if exists
    if file_path:
        query_text += f"\nAttached file for analysis: {os.path.basename(file_path)}"

    # Pass to agent
    resp = run_local_agent(agent_name, query_text)

    # Save chat
    save_chat_history(agent_name, query_text, resp.get("text", ""))

    # Return structured
    return {
        "text": resp.get("text", ""),
        "meta": {
            "agent": agent_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file": file_path,
        },
    }

# =========================================================
# Quick CLI Test Mode
# =========================================================
if __name__ == "__main__":
    print("🤖 ChatBridge quick test")
    ctx = {"text": "test run from CLI", "chat_history": []}
    print(query_agent("Returns", ctx))
