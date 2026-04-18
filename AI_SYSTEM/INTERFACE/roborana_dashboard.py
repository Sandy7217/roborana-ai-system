# =========================================================
# RoboRana AI — Streamlit Command Center v2.0 (Local Edition)
# - Dashboard (KPIs + Plotly charts)
# - Chat with Agents (Manager, Sales, Returns, Inventory, Ads, Creative)
# - One-click Reports (PPT / PDF / CSV via Creative Agent)
# - Files browser (OUTPUTS/)
# - Logs viewer (agent logs)
# - Settings (paths + theme persisted)
# =========================================================

import os, sys, json, subprocess, time
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# Default PATHS
# -----------------------------
BASE_PATH = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data")
DEFAULT_SETTINGS = {
    "BASE_PATH": str(BASE_PATH),
    "SALES_MASTER": str(BASE_PATH / "DATA" / "SALES" / "Master" / "Sales_Master.csv"),
    "RETURNS_MASTER": str(BASE_PATH / "DATA" / "RETURNS" / "Master" / "Return_Master_Updated.csv"),
    "INVENTORY_FILE": str(BASE_PATH / "DATA" / "INVENTORY" / "current_inventory.csv"),
    "OUTPUTS_DIR": str(BASE_PATH / "OUTPUTS"),
    "LOGS_DIR": str(BASE_PATH / "AI_SYSTEM" / "MEMORY" / "agent_logs"),
    "VENV_PY": str(BASE_PATH / ".venv312" / "Scripts" / "python.exe"),
    "AGENTS": {
        "Manager": "AI_SYSTEM.AGENTS.MANAGER_AGENT.manager_agent",
        "Sales": "AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent",
        "Returns": "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
        "Inventory": "AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent",
        "Ads": "AI_SYSTEM.AGENTS.ADS_AGENT.ads_agent",
        "Creative": "AI_SYSTEM.AGENTS.CREATIVE_AGENT.creative_agent",
    },
    "THEME": "dark",
}

SETTINGS_FILE = BASE_PATH / "AI_SYSTEM" / "INTERFACE" / "settings_ui.json"
SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Utilities
# -----------------------------
def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(cfg: dict):
    SETTINGS_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

CFG = load_settings()

def path_exists(p): 
    try: return Path(p).exists()
    except Exception: return False

def nice_num(x, prefix="₹"):
    try:
        return f"{prefix}{float(x):,.2f}"
    except Exception:
        return f"{x}"

def read_csv_safe(path, dayfirst=False):
    if not path_exists(path): return pd.DataFrame()
    try:
        return pd.read_csv(path, on_bad_lines="skip", low_memory=False, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path, on_bad_lines="skip", low_memory=False, encoding="utf-8-sig", engine="python")

def find_col(df, keys):
    cols = {c.lower(): c for c in df.columns}
    for key in keys:
        for lc, orig in cols.items():
            if key in lc:
                return orig
    return None

def filter_last_days(df, date_keys, days, dayfirst=False):
    if df.empty: return df
    dt_col = find_col(df, date_keys)
    if not dt_col: return df
    s = pd.to_datetime(df[dt_col], errors="coerce", dayfirst=dayfirst)
    cutoff = datetime.now() - timedelta(days=days)
    return df[s >= cutoff]

def kpi_card(label, value, help_text=None, cols=None, idx=0):
    if cols is None:
        st.metric(label, value, help=help_text)
    else:
        with cols[idx]:
            st.metric(label, value, help=help_text)

# -----------------------------
# Agent Communication (Final Robust Version)
# -----------------------------
def run_agent(agent_name: str, query: str, timeout=120):
    """
    Run local RoboRana AI agent safely.
    1️⃣ Tries to run as a module (-m AI_SYSTEM.AGENTS.XYZ)
    2️⃣ If import fails, falls back to direct .py file execution
    """
    try:
        py = CFG["VENV_PY"] if path_exists(CFG["VENV_PY"]) else sys.executable
        module = CFG["AGENTS"].get(agent_name)
        if not module:
            return f"❌ Agent '{agent_name}' not configured."

        ai_system_path = str(BASE_PATH / "AI_SYSTEM")
        project_root = str(BASE_PATH)
        env = os.environ.copy()

        # Ensure Python sees AI_SYSTEM package
        env["PYTHONPATH"] = f"{project_root};{ai_system_path};{env.get('PYTHONPATH', '')}"

        cmd = [py, "-m", module]
        stdin_payload = f"{query}\nexit\n"

        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_root,
            text=True,
            encoding="utf-8",
            env=env,
        )
        out, err = p.communicate(stdin_payload, timeout=timeout)

        # If module import fails → fallback to .py path
        if "ModuleNotFoundError" in (err or ""):
            agent_path = (BASE_PATH / "AI_SYSTEM" / "AGENTS" / f"{agent_name.upper()}_AGENT" / f"{agent_name.lower()}_agent.py")
            if agent_path.exists():
                cmd = [py, str(agent_path)]
                p = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(BASE_PATH),
                    text=True,
                    encoding="utf-8",
                    env=env,
                )
                out, err = p.communicate(stdin_payload, timeout=timeout)

        if p.returncode != 0:
            return f"⚠️ Agent exited with error:\n{err or out}"
        if not out.strip():
            return "🤖 Agent did not return any output."
        return out.strip()

    except subprocess.TimeoutExpired:
        return "⏱️ Agent took too long and was stopped."
    except FileNotFoundError:
        return f"❌ Python executable not found: {CFG['VENV_PY']}"
    except Exception as e:
        return f"❌ Unexpected error running agent: {e}"

def call_creative_agent(command: str):
    return run_agent("Creative", command, timeout=300)

# -----------------------------
# Page Styling
# -----------------------------
st.set_page_config(page_title="RoboRana AI — Command Center", page_icon="🤖", layout="wide")

DARK_CSS = """
<style>
section[data-testid="stSidebar"] {background: #111827;}
.stApp {background: #0b0f18; color: #E5E7EB;}
h1, h2, h3 { color: #E5E7EB; }
div.stMetric [data-testid="stMetricValue"] { color:#E5E7EB; }
.kpi-card {padding:16px; border-radius:16px; background:#111827; border:1px solid #1f2937;}
.chat-bubble-user {background:#1f3a8a; color:#fff; padding:12px 14px; border-radius:14px; margin:6px 0; align-self:flex-end; max-width:70%;}
.chat-bubble-agent {background:#1f2937; color:#e5e7eb; padding:12px 14px; border-radius:14px; margin:6px 0; align-self:flex-start; max-width:70%;}
.chat-wrap {display:flex; flex-direction:column; gap:6px;}
textarea {font-size:15px !important;}
.stButton>button {border-radius:10px; height:42px;}
.file-row {padding:10px 12px; border-bottom:1px solid #1f2937;}
</style>
"""

LIGHT_CSS = """
<style>
.kpi-card {padding:16px; border-radius:16px; background:#ffffff; border:1px solid #e5e7eb;}
.chat-bubble-user {background:#2563eb; color:#fff; padding:12px 14px; border-radius:14px; margin:6px 0; align-self:flex-end; max-width:70%;}
.chat-bubble-agent {background:#f3f4f6; color:#111827; padding:12px 14px; border-radius:14px; margin:6px 0; align-self:flex-start; max-width:70%;}
.chat-wrap {display:flex; flex-direction:column; gap:6px;}
</style>
"""
st.markdown(DARK_CSS if CFG["THEME"] == "dark" else LIGHT_CSS, unsafe_allow_html=True)

# -----------------------------
# Sidebar Navigation
# -----------------------------
st.sidebar.title("🧠 RoboRana AI")
page = st.sidebar.radio(
    "Select Section",
    ["📊 Dashboard", "💬 Agent Chat", "📑 Reports", "📂 Files", "📜 Logs", "⚙️ Settings"],
    index=0,
)

# =========================================================
# PAGE: Dashboard
# =========================================================
if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    sales_df = read_csv_safe(CFG["SALES_MASTER"])
    ret_df = read_csv_safe(CFG["RETURNS_MASTER"])
    inv_df = read_csv_safe(CFG["INVENTORY_FILE"])

    days = st.slider("Window (days)", 7, 60, 14, 1)

    s_win = filter_last_days(sales_df, ["order date", "created", "placed"], days)
    price_col = find_col(s_win, ["selling price", "total price", "final amount"])
    order_col = find_col(s_win, ["order code", "display order code", "seller order id"])
    total_sales = pd.to_numeric(s_win[price_col], errors="coerce").fillna(0).sum() if price_col else 0
    orders = s_win[order_col].nunique() if order_col else len(s_win)
    aov = (total_sales / orders) if orders else 0

    r_win = filter_last_days(ret_df, ["date", "created", "updated"], days, dayfirst=True)
    ret_val_col = find_col(r_win, ["total", "amount", "value", "selling price"])
    ret_value = pd.to_numeric(r_win[ret_val_col], errors="coerce").fillna(0).sum() if ret_val_col else 0

    kc1, kc2, kc3, kc4 = st.columns(4)
    kpi_card("Revenue", nice_num(total_sales), cols=[kc1, kc2, kc3, kc4], idx=0)
    kpi_card("Orders", f"{orders:,}", cols=[kc1, kc2, kc3, kc4], idx=1)
    kpi_card("AOV", nice_num(aov), cols=[kc1, kc2, kc3, kc4], idx=2)
    kpi_card("Return Value", nice_num(ret_value), cols=[kc1, kc2, kc3, kc4], idx=3)

# =========================================================
# PAGE: Agent Chat
# =========================================================
elif page == "💬 Agent Chat":
    st.title("💬 Chat with Agents")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    agent = st.selectbox("Choose Agent:", list(CFG["AGENTS"].keys()), index=0)
    prompt = st.text_area("Enter your query:", height=140, placeholder="Ask RoboRana anything...")

    if st.button("🚀 Send Command", use_container_width=True):
        st.session_state.chat_history.append(("user", f"[{agent}] {prompt}"))
        with st.spinner("Agent is processing..."):
            response = run_agent(agent, prompt)
        formatted = f"<pre style='white-space:pre-wrap;'>{response}</pre>"
        st.session_state.chat_history.append(("agent", formatted))
        st.rerun()

    st.markdown("---")
    st.markdown("#### Conversation")
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for role, msg in st.session_state.chat_history:
        css = "chat-bubble-user" if role == "user" else "chat-bubble-agent"
        st.markdown(f'<div class="{css}">{msg}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# PAGE: Reports / Files / Logs / Settings
# =========================================================
# (Keep your existing sections)
