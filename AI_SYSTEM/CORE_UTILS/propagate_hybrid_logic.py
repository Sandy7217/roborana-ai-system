# -*- coding: utf-8 -*-
# ======================================================
# 🤖 RoboRana Auto Logic Propagation Script
# Author: Sandeep Rana
# Purpose: Auto-inject Hybrid Shared Logic v3.0 into all agents
# ======================================================

import os

AGENT_PATHS = [
    "AI_SYSTEM/AGENTS/INVENTORY_AGENT/inventory_agent.py",
    "AI_SYSTEM/AGENTS/FINANCE_AGENT/finance_agent.py",
    "AI_SYSTEM/AGENTS/ADS_AGENT/ads_agent.py",
    "AI_SYSTEM/AGENTS/MANAGER_AGENT/manager_agent.py"
]

injection_code = "\nfrom AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic\nintegrate_shared_logic(self)\n"

for path in AGENT_PATHS:
    if not os.path.exists(path):
        print(f"⚠️ Missing file: {path}")
        continue

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "integrate_shared_logic(self)" in content:
        print(f"✅ Already integrated: {path}")
        continue

    # Inject right after super().__init__()
    updated = content.replace(
        "super().__init__(", 
        "super().__init__(" + injection_code
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"🧩 Hybrid Shared Logic v3.0 integrated into: {path}")

print("\n✅ All available agents have been upgraded with Hybrid Shared Logic v3.0.")
