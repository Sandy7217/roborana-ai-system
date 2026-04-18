# =========================================================
# creative_agent.py — RoboRana Creative Agent (v4.0 Human + Conversational)
# ---------------------------------------------------------
# - AI-powered designer agent for PPT/PDF/CSV generation
# - Understands Hindi, Hinglish, and casual language
# - Conversational tone, human-friendly responses
# - Integrated with Hive Mind + Unified RAG Brain
# =========================================================

import os, sys, json, re
from datetime import datetime, timedelta
import pandas as pd

from AI_SYSTEM.RAG.rag_brain import UnifiedRAGBrain
from AI_SYSTEM.AGENTS.base_agent import BaseAgent
from AI_SYSTEM.HIVE_MIND.hivemind_core import (
    summarize_collective_intelligence,
    record_insight,
    record_pattern
)
from AI_SYSTEM.AGENTS.CREATIVE_AGENT.tools.creative_tools import (
    load_profile, choose_theme,
    load_sales_master, load_returns_master,
    summarize_sales, summarize_returns,
    export_csv
)
from AI_SYSTEM.AGENTS.CREATIVE_AGENT.tools.creative_visual_tools import (
    build_sales_ppt_v3, build_returns_ppt_v3
)
from AI_SYSTEM.CORE_UTILS.shared_agent_logic import integrate_shared_logic

# ---------------------------------------------------------
# 🌐 Configuration
# ---------------------------------------------------------
BASE_PATH = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
LOG_FILE = os.path.join(BASE_PATH, "AI_SYSTEM", "MEMORY", "agent_logs", "creative_agent_log.json")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ---------------------------------------------------------
# 🩺 Safe Print
# ---------------------------------------------------------
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        msg = " ".join(str(a) for a in args)
        print(msg.encode("ascii", errors="ignore").decode("ascii"), **kwargs)


# ---------------------------------------------------------
# 📜 Logging
# ---------------------------------------------------------
def append_log(entry: dict):
    try:
        data = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append(entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        safe_print(f"⚠️ Log write error: {e}")


# ---------------------------------------------------------
# 🧩 Command Parser
# ---------------------------------------------------------
def parse_command(q: str) -> dict:
    ql = q.lower()
    artifact = "ppt" if any(k in ql for k in ["ppt", "presentation", "slide"]) else (
        "pdf" if "pdf" in ql else ("csv" if "csv" in ql or "export" in ql else "ppt")
    )
    source = "returns" if "return" in ql else "sales"

    m = re.search(r"last\s+(\d+)\s+days", ql)
    days = int(m.group(1)) if m else (7 if "week" in ql else 30 if "month" in ql else 7)

    theme = None
    for k in ["floral", "modern", "midnight", "sunset", "corporate"]:
        if k in ql:
            theme = k
            break

    dual_mode = ("pdf" in ql and "ppt" in ql) or "report" in ql
    return {"artifact": artifact, "source": source, "days": days, "theme": theme, "dual": dual_mode}


# ---------------------------------------------------------
# 🎨 Creative Agent (Human-Aware + Hive Mind)
# ---------------------------------------------------------
class CreativeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Creative Agent",
            role_prompt=(
                "You are RoboRana’s **Creative Architect**, part of the Hive Mind Collective. "
                "You understand natural and Hindi/Hinglish commands to create visual reports. "
                "You reply like a creative designer — friendly, confident, and helpful. "
                "You build insightful PPTs, PDFs, and CSVs enriched with Hive and RAG intelligence."
            ),
        )
        if not getattr(self, "_shared_logic_injected", False):
            try:
                integrate_shared_logic(self)
                setattr(self, "_shared_logic_injected", True)
            except Exception as e:
                safe_print(f"⚠️ Failed to integrate shared logic: {e}")

        # ✅ Shared Logic Integration
        self.handle_generic_query = getattr(self, "handle_generic_query", None)

        safe_print("🔧 Initializing Unified RAG Brain...")
        try:
            self.rag = UnifiedRAGBrain()
            safe_print("✅ Connected to Unified RAG Brain.")
        except Exception as e:
            safe_print(f"⚠️ RAG connection failed: {e}")
            self.rag = None

        self.hive_summary = summarize_collective_intelligence()
        safe_print("🧠 Hive Mind awareness enabled.")
        safe_print("🎨 Creative Agent (Human-Aware Mode) ready.\n")

    # -----------------------------------------------------
    # 🤝 Collaboration Hooks
    # -----------------------------------------------------
    def talk_to_agent(self, agent_name: str, task: str):
        return f"🤝 Sent creative request '{task}' to {agent_name} (simulation mode)."

    # -----------------------------------------------------
    # 📊 Handlers for outputs
    # -----------------------------------------------------
    def handle_ppt(self, source: str, days: int, theme: str | None):
        safe_print(f"🎨 Building {source} PPT ({theme or 'modern'} theme)...")

        try:
            context = self.rag.query_all(source, f"{source} summary last {days} days")
        except Exception:
            context = "⚠️ RAG context unavailable."

        design_notes = f"""
        ### Hive Collective Summary:
        {self.hive_summary}

        ### Contextual Data:
        {context}

        Use this intelligence to enrich visual storytelling.
        """

        if source == "sales":
            out = build_sales_ppt_v3(days=days, theme_key=theme or "modern", additional_context=design_notes)
        else:
            out = build_returns_ppt_v3(days=days, theme_key=theme or "modern", additional_context=design_notes)

        msg = f"✅ PPT ready: {out}"
        record_insight("Creative Agent", f"Generated {source} PPT for {days} days", {"path": out})
        return msg

    def handle_pdf(self, source: str, days: int, theme: str | None):
        safe_print(f"📄 Generating {source} PDF...")
        ppt_msg = self.handle_ppt(source, days, theme)

        try:
            import comtypes.client
            ppt_path = ppt_msg.split(": ")[-1]
            pdf_path = ppt_path.replace(".pptx", ".pdf")
            safe_print("🧩 Exporting PPT to PDF...")
            powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
            presentation = powerpoint.Presentations.Open(ppt_path)
            presentation.SaveAs(pdf_path, 32)
            presentation.Close()
            powerpoint.Quit()
            record_insight("Creative Agent", f"Exported {source} PDF for {days} days", {"path": pdf_path})
            msg = f"✅ PDF exported: {pdf_path}"
        except Exception as e:
            msg = f"⚠️ PDF export failed: {e}"
        return msg

    def handle_csv(self, source: str, days: int):
        safe_print(f"💾 Exporting {source} CSV for last {days} days...")
        if source == "sales":
            df = load_sales_master()
            col = [c for c in df.columns if "date" in c.lower()][0]
        else:
            df = load_returns_master()
            col = [c for c in df.columns if "date" in c.lower()][0]

        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df[df[col] >= (datetime.now() - timedelta(days=days))]

        out = export_csv(df, f"{source.title()}_Export_last_{days}_days")
        record_insight("Creative Agent", f"Exported {source} CSV for {days} days", {"path": out})
        return f"✅ CSV exported: {out}"

    # -----------------------------------------------------
    # 🚀 Execute Commands
    # -----------------------------------------------------
    def execute(self, q: str):
        # 🧠 Step 1: Normalize human/Hindi command
        q = self.process_user_input(q)
        safe_print(f"\n🎯 Processed Command → {q}\n")

        # Step 2: Parse for action
        job = parse_command(q)
        artifact, src, days, theme, dual = (
            job["artifact"], job["source"], job["days"], job["theme"], job["dual"]
        )

        # Step 3: Generate creative output
        result = None
        if dual:
            safe_print("🧠 Dual mode detected — generating both PPT and PDF...")
            ppt_msg = self.handle_ppt(src, days, theme)
            pdf_msg = self.handle_pdf(src, days, theme)
            result = f"{ppt_msg}\n{pdf_msg}"
        elif artifact == "ppt":
            result = self.handle_ppt(src, days, theme)
        elif artifact == "pdf":
            result = self.handle_pdf(src, days, theme)
        else:
            result = self.handle_csv(src, days)

        # Step 4: Log results
        append_log({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": q,
            "artifact": artifact,
            "source": src,
            "days": days,
            "theme": theme,
            "result": result
        })

        # Step 5: Add Hive pattern
        if "sales" in src and "ppt" in artifact:
            record_pattern("Sales report visualization generated", "Creative Agent")
        elif "returns" in src:
            record_pattern("Return trends visualization generated", "Creative Agent")

        # Step 6: Human-friendly reply
        response = result
        try:
            response = self.process_agent_output(q, result)
        except Exception as e:
            safe_print(f"⚠️ process_agent_output failed, using raw result: {e}")
            response = result

        if response is None or not str(response).strip():
            response = str(result) if result is not None else "Creative output generated, but no response text was returned."
        safe_print("\n🎨 ===== Creative Agent Response =====\n")
        safe_print(response)
        return response


# ---------------------------------------------------------
# 🧩 Entry Point
# ---------------------------------------------------------
def main():
    safe_print("🎨 Creative Agent (Hive + Conversational) ready.")
    safe_print("Examples:")
    safe_print("  - bhai 7 din ki sales ppt bana do modern theme mein")
    safe_print("  - returns report pdf+ppt dono chahiye")
    safe_print("  - export sales csv last 30 days\n")

    agent = CreativeAgent()

    if any(a in sys.argv for a in ["--auto", "--manager"]):
        safe_print("🤖 Manager Mode Active — Generating weekly Sales Report...\n")
        agent.execute("create weekly sales report pdf+ppt last 7 days (modern)")
        safe_print("🤖 Manager Mode — Ready for next command.\n")

    while True:
        try:
            q = input("🎯 Creative Command (or 'exit'): ").strip()
            if q.lower() == "exit":
                safe_print("👋 Bye!")
                break
            if q:
                agent.execute(q)
        except KeyboardInterrupt:
            safe_print("\n👋 Bye!")
            break
        except Exception as e:
            safe_print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    main()
