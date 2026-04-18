# -*- coding: utf-8 -*-
# ======================================================
# 🧩 RoboRana Logic Injection Fixer
# Author: Sandeep Rana
# Purpose: Auto-correct misplaced integrate_shared_logic injection
# ======================================================

import os
import re

AGENTS = [
    "AI_SYSTEM/AGENTS/INVENTORY_AGENT/inventory_agent.py",
    "AI_SYSTEM/AGENTS/ADS_AGENT/ads_agent.py",
    "AI_SYSTEM/AGENTS/MANAGER_AGENT/manager_agent.py"
]

injection = "\nfrom AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic\nintegrate_shared_logic(self)\n"

for path in AGENTS:
    if not os.path.exists(path):
        print(f"⚠️ Missing file: {path}")
        continue

    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # Remove wrong injected lines (if inside parentheses)
    code = re.sub(r"super\.__init__\([^)]*integrate_shared_logic\(self\)[^)]*\)", "super().__init__()", code)

    # Add proper injection right after the super().__init__() call
    if "integrate_shared_logic(self)" not in code:
        code = code.replace("super().__init__()", "super().__init__()" + injection)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"✅ Fixed injection in: {path}")

print("\n✅ All logic injections corrected successfully.")
