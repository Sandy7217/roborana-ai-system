import os, sys, subprocess
import importlib.util

# ------------------------------------------------
# 🧩 Agent Module Map
# ------------------------------------------------
AGENT_MODULES = {
    "sales":     "AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent",
    "returns":   "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
    "return":    "AI_SYSTEM.AGENTS.RETURN_AGENT.return_agent",
    "inventory": "AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent",
    "ads":       "AI_SYSTEM.AGENTS.ADS_AGENT.ads_agent",
    # "finance": "AI_SYSTEM.AGENTS.FINANCE_AGENT.finance_agent",
}

# ------------------------------------------------
# 📍 Project Root Resolver
# ------------------------------------------------
def _find_project_root():
    """
    Walks upward from this file to find the RoboRana project root 
    (the folder containing 'AI_SYSTEM'). Ensures correct CWD for subprocesses.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    cur = here
    for _ in range(10):  # safeguard depth limit
        if os.path.isdir(os.path.join(cur, "AI_SYSTEM")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return os.getcwd()  # fallback

PROJECT_ROOT = _find_project_root()

def _validate_module_path(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return importlib.util.find_spec(module) is not None

# ------------------------------------------------
# 🚀 Agent Runner — Cross-Platform & Input-Safe
# ------------------------------------------------
def run_agent_live(agent_key: str, query: str, python_exec: str = sys.executable, timeout: int = 240) -> dict:
    """
    Runs a given agent module (by key) in a subprocess and streams its output safely.
    Sends the query as input followed by 'exit' to close agent CLI.
    Returns structured result with stdout, stderr, and success flag.
    """
    module = AGENT_MODULES.get(agent_key.lower())
    if not module:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Unknown agent '{agent_key}'",
            "module": None,
            "code": None,
        }
    if not _validate_module_path(module):
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Invalid module path for agent '{agent_key}': {module}",
            "module": module,
            "code": None,
        }

    cmd = [python_exec, "-m", module]
    payload = (query.strip() + "\nexit\n").encode("utf-8", errors="ignore")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,  # ensures -m works correctly
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

        out, err = proc.communicate(input=payload, timeout=timeout)
        stdout = out.decode("utf-8", errors="replace")
        stderr = err.decode("utf-8", errors="replace")

        # consider successful if returncode=0 or recognizable completion token present
        ok = (proc.returncode == 0) or ("=====" in stdout)

        return {
            "ok": ok,
            "stdout": stdout[-6000:],  # trim large logs
            "stderr": stderr[-4000:],
            "module": module,
            "code": proc.returncode,
        }

    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s for {module}",
            "module": module,
            "code": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "module": module,
            "code": None,
        }
