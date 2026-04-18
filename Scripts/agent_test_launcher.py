# ============================================================
# File: SCRIPTS/agent_test_launcher.py
# Purpose: One-click health and functionality diagnostic for RoboRana AI Agents
# Author: Sandeep Rana 🧠
# ============================================================

# ============================================================
# File: SCRIPTS/agent_test_launcher.py
# Purpose: One-click health and functionality diagnostic for RoboRana AI Agents
# ============================================================

import os
import sys
import json
from datetime import datetime

# --- Ensure project root is in sys.path ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# === Agents Import ===
from AI_SYSTEM.AGENTS.SALES_AGENT.sales_agent import SalesAgent
from AI_SYSTEM.AGENTS.INVENTORY_AGENT.inventory_agent import InventoryAgent
# (you can later add FinanceAgent, AdsAgent, ReturnsAgent etc.)

# === Diagnostic Log Path ===
LOG_DIR = "AI_SYSTEM/MEMORY/diagnostics"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"diagnostic_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json")

# === Utility ===
def log_result(agent_name, query, result, success=True):
    """Append each agent’s test result to diagnostic log file."""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent_name,
        "query": query,
        "status": "✅ PASS" if success else "❌ FAIL",
        "summary": result[:500]
    }

    data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []

    data.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# === Main Diagnostic Routine ===
def run_agent_diagnostics():
    print("\n🚀 Starting RoboRana AI System Diagnostic...\n")

    results_summary = []

    # ===== Sales Agent =====
    try:
        print("🧮 Testing Sales Agent...")
        sales_agent = SalesAgent()
        response = sales_agent.handle_query("show me sales summary of last 7 days")
        results_summary.append(("Sales Agent", "✅ PASS"))
        log_result("Sales Agent", "show me sales summary of last 7 days", response, success=True)
    except Exception as e:
        print(f"❌ Sales Agent error: {e}")
        results_summary.append(("Sales Agent", "❌ FAIL"))
        log_result("Sales Agent", "show me sales summary of last 7 days", str(e), success=False)

    # ===== Inventory Agent =====
    try:
        print("\n📦 Testing Inventory Agent...")
        inventory_agent = InventoryAgent()
        response = inventory_agent.handle_query("show me inventory summary")
        results_summary.append(("Inventory Agent", "✅ PASS"))
        log_result("Inventory Agent", "show me inventory summary", response, success=True)
    except Exception as e:
        print(f"❌ Inventory Agent error: {e}")
        results_summary.append(("Inventory Agent", "❌ FAIL"))
        log_result("Inventory Agent", "show me inventory summary", str(e), success=False)

    # === Summary Report ===
    print("\n🧠 ===== Diagnostic Summary =====\n")
    for agent, status in results_summary:
        print(f"{agent:<25} {status}")

    print(f"\n📝 Detailed diagnostic log saved to: {LOG_FILE}")
    print("\n✅ Diagnostic complete. RoboRana AI is ready!\n")


# === Entry Point ===
if __name__ == "__main__":
    run_agent_diagnostics()
