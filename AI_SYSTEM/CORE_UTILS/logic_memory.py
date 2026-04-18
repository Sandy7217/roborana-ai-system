# -*- coding: utf-8 -*-
# ============================================================
# 🧠 RoboRana Logic Memory Engine
# Author: Sandeep Rana
# Purpose: Store, recall, and persist learned knowledge & formulas
# ============================================================

import os
import json
from datetime import datetime

# Paths
MEMORY_DIR = os.path.join("AI_SYSTEM", "MEMORY")
os.makedirs(MEMORY_DIR, exist_ok=True)

KNOWLEDGE_FILE = os.path.join(MEMORY_DIR, "learned_knowledge.json")
FORMULA_FILE = os.path.join(MEMORY_DIR, "learned_formulas.json")

# Helpers
def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to save memory file: {e}")

# ============================================================
# 📘 Knowledge Memory — definitions, meanings
# ============================================================
def learn_knowledge(term: str, meaning: str):
    """Save a new definition."""
    data = _load_json(KNOWLEDGE_FILE)
    data[term.lower()] = {
        "meaning": meaning.strip(),
        "learned_on": datetime.now().isoformat()
    }
    _save_json(KNOWLEDGE_FILE, data)

def recall_knowledge(term: str):
    """Recall a definition."""
    data = _load_json(KNOWLEDGE_FILE)
    term = term.lower().strip()
    if term in data:
        return data[term]["meaning"]
    return None

# ============================================================
# 🧮 Formula Memory — equations, KPIs, expressions
# ============================================================
def learn_formula(term: str, formula: str):
    """Save a new formula."""
    data = _load_json(FORMULA_FILE)
    data[term.lower()] = {
        "formula": formula.strip(),
        "learned_on": datetime.now().isoformat()
    }
    _save_json(FORMULA_FILE, data)

def recall_formula(term: str):
    """Recall a formula."""
    data = _load_json(FORMULA_FILE)
    term = term.lower().strip()
    if term in data:
        return data[term]["formula"]
    return None

# ============================================================
# 🧾 Optional: List all learned items
# ============================================================
def list_memory():
    knowledge = _load_json(KNOWLEDGE_FILE)
    formulas = _load_json(FORMULA_FILE)
    return {
        "knowledge": knowledge,
        "formulas": formulas
    }

if __name__ == "__main__":
    print("🧠 Current RoboRana Memory Snapshot:")
    print(json.dumps(list_memory(), indent=4, ensure_ascii=False))
