import pandas as pd
import io
from datetime import datetime

# === Get Input Data from Merge Node ===
# Input 1 → Uniware + Ajio sale data
# Input 2 → Myntra SJIT sale data (Google Sheet)
final_sales = pd.DataFrame($json["final_sales"])        # From Extract from File
myntra_sjit = pd.DataFrame($json["Myntra SJIT sale"])   # From Google Sheet node

# === Clean column names ===
final_sales.columns = final_sales.columns.str.strip()
myntra_sjit.columns = myntra_sjit.columns.str.strip().str.lower()

# === Rename Myntra SJIT columns to match Final Sales file ===
rename_map = {
    'seller order id': 'Display Order Code',
    'sku': 'Item SKU Code',
    'final amount': 'Selling Price',
    'channel': 'Channel Name'
}
myntra_sjit.rename(columns=rename_map, inplace=True)

# === Keep only required columns ===
keep_cols = [col for col in rename_map.values() if col in myntra_sjit.columns]
myntra_sjit = myntra_sjit[keep_cols]

# === Match common columns between both datasets ===
common_cols = [col for col in final_sales.columns if col in myntra_sjit.columns]

# === Append Myntra SJIT data under Final Sales ===
merged_df = pd.concat([final_sales[common_cols], myntra_sjit[common_cols]], ignore_index=True)

# === Save merged data as Excel (Binary Output for n8n) ===
excel_buffer = io.BytesIO()
today_str = datetime.now().strftime("%Y-%m-%d")
file_name = f"Final_Sales_Merged_{today_str}.xlsx"

merged_df.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)

# === Return Binary Output for n8n ===
return {
    "binary": {
        "data": {
            "data": excel_buffer.getvalue(),
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "fileName": file_name
        }
    }
}
