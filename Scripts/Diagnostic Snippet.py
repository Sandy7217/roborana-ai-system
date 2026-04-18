import pandas as pd
import numpy as np

path = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data\DATA\SALES\Master\Sales_Master.csv"
df = pd.read_csv(path, low_memory=False)
print("\n🧩 Columns:", df.columns.tolist())

# detect order date column
cols = [c for c in df.columns if 'order' in c.lower() and 'date' in c.lower()]
if not cols:
    print("❌ No 'order date' column found")
else:
    col = cols[0]
    s = df[col]
    print(f"\n📦 Detected order date column: {col}")
    print("📊 Raw dtype:", s.dtype, "type:", type(s))
    print("🔹 Sample raw values:", s.astype(str).head(5).tolist())

    parsed = pd.to_datetime(
        s.astype(str).str.replace(r"[\[\]']", "", regex=True),
        errors="coerce",
        dayfirst=True
    )
    print("\n📅 Parsed dtype:", parsed.dtype)
    print("⚠️ NaT count:", parsed.isna().sum())
    print("✅ Parsed sample:", parsed.head(5).tolist())
