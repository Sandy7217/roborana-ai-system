# =========================================================
# ROBORANA — Assistant (v3.4 Stable)
# Chat-first UI + Memory + Correct Agent Handling
# =========================================================

import os, sys, json, subprocess, re
from pathlib import Path
from datetime import datetime

import streamlit as st
# Force UTF-8 output on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"

# ---------- Config ----------

BASE_PATH = Path(
    os.getenv(
        "ROBORANA_HOME",
        r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
    )
)

OUTPUTS_DIR = BASE_PATH / "OUTPUTS"
UPLOADS_DIR = BASE_PATH / "AI_SYSTEM" / "INTERFACE" / "UPLOADS"
LOGS_DIR = BASE_PATH / "AI_SYSTEM" / "MEMORY" / "agent_logs"
CHAT_MEMORY = BASE_PATH / "AI_SYSTEM" / "MEMORY" / "chat_history.json"

VENV_PY = BASE_PATH / ".venv312" / "Scripts" / "python.exe"


AGENTS = {
    "Manager":   "AI_SYSTEM.AGENTS.MANAGER_AGENT.manager_agent",
    "Sales":     "AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent",
    "Returns":   "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
    "Inventory": "AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent",
    "Ads":       "AI_SYSTEM.AGENTS.ADS_AGENT.ads_agent",
    "Creative":  "AI_SYSTEM.AGENTS.CREATIVE_AGENT.creative_agent",
}


# ---------- Ensure folders ----------

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CHAT_MEMORY.parent.mkdir(parents=True, exist_ok=True)


# ---------- Helpers ----------

def path_exists(p):
    try:
        return Path(p).exists()
    except:
        return False


def _python_bin() -> str:
    return str(VENV_PY) if path_exists(VENV_PY) else sys.executable


def save_chat_memory(messages):
    """Persist chat for learning"""

    try:
        data = {
            "updated_at": datetime.now().isoformat(),
            "messages": messages
        }

        with open(CHAT_MEMORY, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    except:
        pass


def load_chat_memory():

    if CHAT_MEMORY.exists():

        try:
            with open(CHAT_MEMORY, "r", encoding="utf-8") as f:
                return json.load(f).get("messages", [])

        except:
            return []

    return []


def _clean_agent_output(text: str) -> str:

    if not text:
        return ""

    # Prefer explicit "Response" sections when available.
    block = re.search(
        r"={5,}.*?Response.*?={5,}\s*(.*?)(?:\n={5,}.*?$|\Z)",
        text,
        re.S | re.I | re.M
    )

    if block:
        text = block.group(1).strip()

    drop_patterns = [
        r"^🔧.*$", r"^✅.*$", r"^🚀.*$", r"^🔍.*$", r"^📁.*$",
        r"^🤖.*$", r"^🧠.*$", r"^📝.*$", r"^📦.*$", r"^🧩.*$",
        r"^Spinner.*$", r"^Thread.*$", r"^Using vector DB.*$",
        r"Unified RAG.*", r"Hive Mind.*", r"RAG (Brain|search).*",
        r"^={5,}.*$", r"^-{5,}.*$"
    ]

    lines = []

    for line in text.splitlines():

        stripped = line.strip()

        if any(re.search(p, stripped) for p in drop_patterns):
            continue

        if "Enter a query" in line or "Exiting" in line:
            continue

        lines.append(line)

    cleaned = "\n".join(lines).strip()

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


def _looks_like_fatal_error(text: str) -> bool:
    if not text:
        return False

    checks = [
        "Traceback",
        "ModuleNotFoundError",
        "ImportError",
        "SyntaxError",
        "FileNotFoundError",
        "SystemExit",
    ]

    return any(c in text for c in checks)


def _has_response_block(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"={5,}.*?Response.*?={5,}", text, re.I))


def run_agent(agent_name, user_query, timeout=180):

    result = {
        "ok": False,
        "text": "",
        "raw_output": "",
        "error": "",
        "return_code": None,
    }

    module = AGENTS.get(agent_name)

    if not module:
        result["error"] = "agent_not_configured"
        result["text"] = "❌ Agent not configured."
        return result["text"]

    py = _python_bin()

    cmd = [py, "-m", module]

    env = os.environ.copy()
    env["CLEAN_OUTPUT_MODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    
    try:

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_PATH),
            text=True,
            encoding="utf-8",
            errors="ignore",   # <<< FIX
            env=env
        )

        stdin_payload = f"{user_query}\nexit\n"

        out, _ = p.communicate(stdin_payload, timeout=timeout)
        result["raw_output"] = out or ""
        result["return_code"] = p.returncode

        raw_output = result["raw_output"]
        cleaned_output = _clean_agent_output(raw_output)
        has_response_block = _has_response_block(raw_output)
        fatal_error = _looks_like_fatal_error(raw_output)

        if not raw_output.strip():
            result["error"] = "empty_output"
            result["text"] = "❌ Agent returned no output. Check logs."
        elif not cleaned_output.strip():
            result["error"] = "uncleanable_output"
            result["text"] = "⚠️ Agent produced output, but no clean answer could be extracted."
        elif fatal_error and not has_response_block:
            result["error"] = "startup_or_fatal_error"
            result["text"] = "❌ Agent failed to start correctly. Please check module paths or environment setup."
        elif result["return_code"] not in (0, None) and not cleaned_output.strip():
            result["error"] = "non_zero_no_answer"
            result["text"] = "⚠️ Agent encountered an error before finishing. Check logs for details."
        else:
            # Keep useful answers, even with non-zero return codes.
            result["ok"] = True
            result["text"] = cleaned_output

        if (
            not result["ok"]
            and result["return_code"] not in (0, None)
            and result["error"] not in {"startup_or_fatal_error", "uncleanable_output", "empty_output"}
        ):
            result["error"] = result["error"] or "non_zero_exit"
            result["text"] = result["text"] or "⚠️ Agent encountered an error before finishing. Check logs for details."

        return result["text"]


    except subprocess.TimeoutExpired:

        result["error"] = "timeout"
        result["text"] = "⏱️ The agent took too long. Try a smaller query."
        return result["text"]


    except Exception as e:

        result["error"] = "system_error"
        result["text"] = f"❌ System Error: {e}"
        return result["text"]


def save_uploads(files):

    saved = []

    for f in files or []:

        dest = UPLOADS_DIR / f.name

        with open(dest, "wb") as w:
            w.write(f.read())

        saved.append(str(dest))

    return saved


def list_output_files():

    if not OUTPUTS_DIR.exists():
        return []

    return sorted(
        [p for p in OUTPUTS_DIR.rglob("*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )


# ---------- UI ----------

st.set_page_config(
    page_title="ROBORANA",
    page_icon="🤖",
    layout="wide"
)


MIN_CSS = """
<style>

.stApp {background: #0b0f18;}

h1,h2,h3 { color: #e5e7eb; }

section[data-testid="stSidebar"] {background: #0b0f18;}

div[data-testid="stChatMessage"] {
    max-width: 900px;
    margin-left: 0;
    margin-right: auto;
}

div[data-testid="stChatMessage"] + div[data-testid="stChatMessage"] {
    margin-top: .35rem;
}

</style>
"""

st.markdown(MIN_CSS, unsafe_allow_html=True)


# ---------- Header ----------

colL, colR = st.columns([4, 2])

with colL:
    st.markdown("# 🤖 ROBORANA")

with colR:

    with st.expander("⬇️ Downloads (OUTPUTS)", expanded=False):

        files = list_output_files()

        if not files:
            st.caption("No generated reports yet.")

        for f in files[:30]:

            ts = datetime.fromtimestamp(
                f.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M")

            with open(f, "rb") as fh:

                st.download_button(
                    label=f"Download — {f.name} • {ts}",
                    data=fh,
                    file_name=f.name,
                    use_container_width=True,
                )


# ---------- Controls ----------

st.divider()

top = st.container()

with top:

    c1, c2, c3 = st.columns([2, 4, 2])

    with c1:

        agent = st.selectbox(
            "Agent",
            list(AGENTS.keys()),
            index=0
        )

    with c2:

        uploads = st.file_uploader(
            "Attach files (CSV/XLSX/PDF/Images)",
            type=["csv","xlsx","xls","pdf","png","jpg","jpeg","webp"],
            accept_multiple_files=True
        )

    with c3:

        st.markdown("### 🟢 System")
        st.caption("All agents ready")


# ---------- Chat State ----------

if "messages" not in st.session_state:

    st.session_state.messages = load_chat_memory()


# ---------- Render Chat ----------

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])


# ---------- Input ----------

prompt = st.chat_input("Type your message…")


if prompt and prompt.strip():

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)


    saved_paths = save_uploads(uploads)

    meta = (
        f"\n\n[uploaded_files]: {saved_paths}\n"
        if saved_paths else ""
    )


    final_query = (
        f"{prompt.strip()}{meta}\n"
        "Reply concisely with data-driven results. Avoid logs."
    )


    with st.chat_message("assistant"):

        with st.spinner("Thinking…"):

            reply = run_agent(agent, final_query)

        st.markdown(reply if reply else "_(no content)_")


    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })


    save_chat_memory(st.session_state.messages)


# ---------- Footer ----------

st.markdown(
    "<br><span style='color:#94a3b8;font-size:12px'>"
    "RoboRana Assistant v3.4 — stable, correct agent handling, production-ready."
    "</span>",
    unsafe_allow_html=True
)
