# =========================================================
# ROBORANA — Assistant (v3.2 Minimal)
# Chat-first UI + Downloads panel
# =========================================================

import os, sys, json, subprocess, re
from pathlib import Path
from datetime import datetime

import streamlit as st

# ---------- Config ----------
BASE_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data")
OUTPUTS_DIR = BASE_PATH / "OUTPUTS"
UPLOADS_DIR = BASE_PATH / "AI_SYSTEM" / "INTERFACE" / "UPLOADS"
LOGS_DIR = BASE_PATH / "AI_SYSTEM" / "MEMORY" / "agent_logs"
VENV_PY = BASE_PATH / ".venv312" / "Scripts" / "python.exe"

AGENTS = {
    "Manager":  "AI_SYSTEM.AGENTS.MANAGER_AGENT.manager_agent",
    "Sales":    "AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent",
    "Returns":  "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
    "Inventory":"AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent",
    "Ads":      "AI_SYSTEM.AGENTS.ADS_AGENT.ads_agent",
    "Creative": "AI_SYSTEM.AGENTS.CREATIVE_AGENT.creative_agent",
}

# Make sure folders exist
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def path_exists(p): 
    try: return Path(p).exists()
    except: return False

def _python_bin() -> str:
    return str(VENV_PY) if path_exists(VENV_PY) else sys.executable

def _clean_agent_output(text: str) -> str:
    """Remove spinner/log lines & keep the 'business' answer clean."""
    if not text:
        return ""

    # Try to keep content inside any "===== ... Response =====" section if present
    block = re.search(r"=====.*?Response.*?=====\s*(.*)", text, re.S | re.I)
    if block:
        text = block.group(1)

    # Drop common log/status lines
    drop_patterns = [
        r"^🔧.*$", r"^✅.*$", r"^🚀.*$", r"^🔍.*$", r"^📁.*$",
        r"^🤖.*$", r"^🧠.*$", r"^📝.*$", r"^📦.*$", r"^🧩.*$",
        r"^Spinner.*$", r"^Thread.*$", r"^Using vector DB.*$",
        r"Unified RAG.*", r"Hive Mind.*", r"RAG (Brain|search).*",
        r"^={5,}.*$", r"^-{5,}.*$"
    ]
    lines = []
    for line in text.splitlines():
        if any(re.search(p, line.strip()) for p in drop_patterns):
            continue
        # strip left-over prompts like "Enter a query..."
        if "Enter a query" in line or "Exiting" in line:
            continue
        lines.append(line)

    cleaned = "\n".join(lines).strip()

    # Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # If agent printed a giant console dump in a code block, keep it as is but trimmed
    return cleaned

def run_agent(agent_name: str, user_query: str, extra_env: dict | None = None, timeout: int = 180) -> str:
    """Run the chosen agent as a module; pipe the query via stdin; return cleaned text."""
    module = AGENTS.get(agent_name)
    if not module:
        return "❌ Agent not configured."

    py = _python_bin()
    cmd = [py, "-m", module]

    # Pass a 'CLEAN_OUTPUT_MODE' signal into agents (those that read env will comply)
    env = os.environ.copy()
    env["CLEAN_OUTPUT_MODE"] = "1"
    if extra_env:
        env.update(extra_env)

    try:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_PATH),
            text=True,
            encoding="utf-8",
            env=env,
        )
        stdin_payload = f"{user_query}\nexit\n"
        out, _ = p.communicate(stdin_payload, timeout=timeout)
        return _clean_agent_output(out)
    except subprocess.TimeoutExpired:
        return "⏱️ The agent took too long. Try refining the query."
    except Exception as e:
        return f"❌ Error running agent: {e}"

def save_uploads(files) -> list[str]:
    """Save uploaded files and return absolute paths."""
    saved = []
    for f in files or []:
        dest = UPLOADS_DIR / f.name
        with open(dest, "wb") as w:
            w.write(f.read())
        saved.append(str(dest))
    return saved

def list_output_files() -> list[Path]:
    if not OUTPUTS_DIR.exists():
        return []
    return sorted([p for p in OUTPUTS_DIR.rglob("*") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)

# ---------- UI ----------
st.set_page_config(page_title="ROBORANA", page_icon="🤖", layout="wide")

MIN_CSS = """
<style>
/* Minimal dark polish */
.stApp {background: #0b0f18;}
h1,h2,h3 { color: #e5e7eb; }
.sidebar .sidebar-content { background: #0b0f18 !important; }
section[data-testid="stSidebar"] {background: #0b0f18;}
/* Chat look */
div[data-testid="stChatMessage"] { max-width: 900px; margin-left: 0; margin-right: auto; }
div[data-testid="stChatMessage"] + div[data-testid="stChatMessage"] { margin-top: .35rem; }
</style>
"""
st.markdown(MIN_CSS, unsafe_allow_html=True)

# Header
colL, colR = st.columns([4,2])
with colL:
    st.markdown("# 🤖 ROBORANA")
with colR:
    # Quick downloads shortcut
    with st.expander("⬇️ Downloads (OUTPUTS)", expanded=False):
        files = list_output_files()
        if not files:
            st.caption("No generated reports yet.")
        for f in files[:30]:
            ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            with open(f, "rb") as fh:
                st.download_button(
                    label=f"Download — {f.name}  •  {ts}",
                    data=fh,
                    file_name=f.name,
                    use_container_width=True,
                )

# Agent selector (top-right feel)
st.divider()
top = st.container()
with top:
    c1, c2 = st.columns([2, 4])
    with c1:
        agent = st.selectbox("Agent", list(AGENTS.keys()), index=0, help="Choose which brain should answer.")
    with c2:
        uploads = st.file_uploader(
            "Attach files (CSV/XLSX/PDF/images) — optional",
            type=["csv","xlsx","xls","pdf","png","jpg","jpeg","webp"],
            accept_multiple_files=True
        )

# Initialize chat state
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of dicts: {role:"user/assistant", "content": str}

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Bottom input (sticks to bottom)
prompt = st.chat_input("Type your message…")

if prompt is not None and prompt.strip() != "":
    # Show user's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Save uploads (if any) & pass their paths to the agent as meta
    saved_paths = save_uploads(uploads)
    meta = f"\n\n[uploaded_files]: {saved_paths}\n" if saved_paths else ""

    # Build final query for the agent (the agent can choose to read any provided files)
    final_query = (
        f"{prompt.strip()}{meta}\n"
        "Note: Reply concisely with factual, data-driven results. Avoid internal logs."
    )

    # Call agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply = run_agent(agent, final_query)
        st.markdown(reply if reply else "_(no content)_")

    # Save bot message
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Footer note (tiny)
st.markdown(
    "<br><span style='color:#94a3b8;font-size:12px'>RoboRana Assistant v3.2 — chat-first, minimal. "
    "Outputs are saved to OUTPUTS/ automatically by agents.</span>",
    unsafe_allow_html=True
)
