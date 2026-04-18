# create_ai_system_folders.py
import os
from pathlib import Path

# base RoboRana data folder (edit if your path differs)
BASE = Path(r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data")

# define AI system subfolders
folders = [
    BASE / "AI_SYSTEM",
    BASE / "AI_SYSTEM" / "RAG",
    BASE / "AI_SYSTEM" / "RAG" / "VECTOR_DB",
    BASE / "AI_SYSTEM" / "RAG" / "KNOWLEDGE",
    BASE / "AI_SYSTEM" / "RAG" / "INGEST_SCRIPTS",
    BASE / "AI_SYSTEM" / "AGENTS",
    BASE / "AI_SYSTEM" / "AGENTS" / "SALES_AGENT",
    BASE / "AI_SYSTEM" / "AGENTS" / "INVENTORY_AGENT",
    BASE / "AI_SYSTEM" / "AGENTS" / "FINANCE_AGENT",
    BASE / "AI_SYSTEM" / "AGENTS" / "MANAGER_AGENT",
    BASE / "AI_SYSTEM" / "AGENTS" / "PERFORMANCE_AGENT",
    BASE / "AI_SYSTEM" / "AGENTS" / "CREATIVE_AGENT",
    BASE / "AI_SYSTEM" / "MEMORY",
    BASE / "AI_SYSTEM" / "LOGS",
]

def create_folders():
    for f in folders:
        f.mkdir(parents=True, exist_ok=True)
        print("✅", f)

if __name__ == "__main__":
    print("Creating RoboRana AI System folders...\n")
    create_folders()
    print("\n🎯 All AI_SYSTEM folders are ready.")
