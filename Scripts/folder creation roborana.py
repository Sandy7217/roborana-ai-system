import os
from datetime import date

# Get desktop path (Windows)
desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

# Main project folder
base_path = os.path.join(desktop, "RoboRana_AI_Data")

# Define folder structure
folders = [
    "DATA/SALES/RAW",
    "DATA/SALES/DAILY",
    "DATA/SALES/FINAL",
    
    "DATA/RETURNS/RAW",
    "DATA/RETURNS/DAILY",
    "DATA/RETURNS/FINAL",
    
    "DATA/INVENTORY/RAW",
    "DATA/INVENTORY/DAILY",
    "DATA/INVENTORY/FINAL",
    
    "DATA/ADS/PLA",
    "DATA/ADS/VISIBILITY",
    
    "REFERENCE/MAPPING",
    "REFERENCE/CHANNEL_ITEM_TYPE",
    "REFERENCE/COSTING",
    
    "BACKUP/DAILY_BACKUPS",
    "BACKUP/WEEKLY_BACKUPS",
    
    "LOGS/N8N",
    "LOGS/AI_AGENTS",
    
    "ARCHIVE/OLD_DATA",
]

# Create all folders
for folder in folders:
    path = os.path.join(base_path, folder)
    os.makedirs(path, exist_ok=True)

print(f"✅ RoboRana folder structure created successfully at:\n{base_path}")

# Optionally, create today's dated folders for daily data
today = date.today().strftime("%Y-%m-%d")
for module in ["SALES", "RETURNS", "INVENTORY"]:
    daily_path = os.path.join(base_path, f"DATA/{module}/DAILY/{today}")
    os.makedirs(daily_path, exist_ok=True)
    print(f"📁 Created daily snapshot folder for {module}: {today}")
