"""
AI_SYSTEM/AGENTS/ADS_AGENT/tools/ads_data_tools.py
--------------------------------------------------
Loads latest Myntra PLA & Visibility snapshots, merges by SKU, and computes:
CTR, CPC, ROAS, Orders/Units, Revenue, plus Top SKUs by Spend & ROAS.
"""

import os, re, glob
import pandas as pd
from datetime import datetime, timedelta

# -------------------------------------------------------------
# Paths (root-agnostic, but default to your Windows absolute)
# -------------------------------------------------------------
DEFAULT_BASE = r"C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"
PLA_DIR_DEFAULT = os.path.join(DEFAULT_BASE, "DATA", "ADS", "PLA")
VIS_DIR_DEFAULT = os.path.join(DEFAULT_BASE, "DATA", "ADS", "VISIBILITY")

def _resolve_dir(prefer_path):
    if os.path.isdir(prefer_path):
        return prefer_path
    here = os.path.dirname(__file__)
    for up in range(7):
        root = here
        for _ in range(up):
            root = os.path.dirname(root)
        cand = os.path.join(root, "DATA", "ADS", os.path.basename(prefer_path))
        if os.path.isdir(cand):
            return cand
    return prefer_path  # last resort

PLA_DIR = _resolve_dir(PLA_DIR_DEFAULT)
VIS_DIR = _resolve_dir(VIS_DIR_DEFAULT)

# -------------------------------------------------------------
# Snapshot discovery (mirrors your inventory pattern)
# -------------------------------------------------------------
def _latest_csv(directory: str, pattern_prefix: str):
    """Find the latest snapshot CSV in `directory` that starts with prefix."""
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"❌ Directory not found: {directory}")
    files = [f for f in os.listdir(directory) if f.lower().endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"❌ No CSV files found in: {directory}")

    pref = [f for f in files if f.lower().startswith(pattern_prefix.lower())]
    candidates = pref if pref else files

    scored = []
    for f in candidates:
        fp = os.path.join(directory, f)
        dt = None
        for rx in [
            r"(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})",
            r"(\d{1,2})\s*([A-Za-z]{3,9})\s*(\d{4})",
            r"([A-Za-z]{3,9})[_\-\s]*(\d{1,2})[_\-\s]*(\d{4})",
        ]:
            m = re.search(rx, f)
            if m:
                try:
                    if m.group(1).isalpha():
                        month = datetime.strptime(m.group(1)[:3], "%b").month
                        day = int(m.group(2))
                        year = int(m.group(3))
                    elif m.group(2).isalpha():
                        day = int(m.group(1))
                        month = datetime.strptime(m.group(2)[:3], "%b").month
                        year = int(m.group(3))
                    else:
                        year, month, day = map(int, m.groups())
                    dt = datetime(year, month, day)
                    break
                except Exception:
                    pass
        score = (dt or datetime.fromtimestamp(os.path.getmtime(fp)), fp)
        scored.append(score)

    scored.sort(key=lambda x: x[0])
    latest = scored[-1][1]
    print(f"📁 Using latest snapshot from {os.path.basename(directory)} → {os.path.basename(latest)}")
    return latest

# -------------------------------------------------------------
# Header helpers
# -------------------------------------------------------------
def _find_header(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    low = [c.lower() for c in cols]
    for c in candidates:
        lc = c.lower()
        for i, v in enumerate(low):
            if lc == v or lc in v or v in lc:
                return cols[i]
    return None

def _norm_cols(df):
    df.columns = [c.strip() for c in df.columns]
    return df

# -------------------------------------------------------------
# Loaders
# -------------------------------------------------------------
def _load_latest_pla():
    path = _latest_csv(PLA_DIR, "pla")
    df = pd.read_csv(path, low_memory=False, on_bad_lines="skip")
    df = _norm_cols(df)
    return df, path

def _load_latest_visibility():
    path = _latest_csv(VIS_DIR, "visibility")
    df = pd.read_csv(path, low_memory=False, on_bad_lines="skip")
    df = _norm_cols(df)
    return df, path

# -------------------------------------------------------------
# Main numeric engine
# -------------------------------------------------------------
def interpret_ads_query(user_query: str):
    """Compute Spend, CTR, CPC, ROAS, and Top SKUs from PLA + Visibility."""
    now = datetime.now()
    pla_df, pla_path = _load_latest_pla()
    vis_df, vis_path = _load_latest_visibility()

    # -----------------------------
    # PLA column mapping
    # -----------------------------
    cols_pla = list(pla_df.columns)
    sku_p = _find_header(cols_pla, ["SKU", "sku", "Product SKU", "Product SKU Code"])
    spend_p = _find_header(cols_pla, ["budget_spend", "Spend", "spend", "Ad Spend"])
    clicks_p = _find_header(cols_pla, ["clicks", "Clicks"])
    impr_p = _find_header(cols_pla, ["impressions", "Impressions"])
    ctr_p = _find_header(cols_pla, ["ctr", "CTR"])
    orders_p = _find_header(cols_pla, ["orders", "Orders", "units_sold_total", "Units Sold Total"])
    revenue_p = _find_header(cols_pla, ["total_revenue", "Revenue", "Sales", "sales_value"])
    campaign_p = _find_header(cols_pla, ["campaign_name", "Campaign Name", "Ad Group", "ad_group"])

    for col in [spend_p, clicks_p, impr_p, orders_p, revenue_p, ctr_p]:
        if col and col in pla_df.columns:
            pla_df[col] = pd.to_numeric(pla_df[col], errors="coerce")

    total_spend = float(pla_df[spend_p].sum()) if spend_p else 0.0
    total_clicks = int(pla_df[clicks_p].sum()) if clicks_p else 0
    total_impr = int(pla_df[impr_p].sum()) if impr_p else 0
    total_orders = int(pla_df[orders_p].sum()) if orders_p else 0
    total_revenue = float(pla_df[revenue_p].sum()) if revenue_p else 0.0

    ctr_calc = (total_clicks / total_impr * 100) if total_impr else (float(pla_df[ctr_p].mean()) if ctr_p else 0.0)
    cpc = (total_spend / total_clicks) if total_clicks else 0.0
    roas = (total_revenue / total_spend) if total_spend else 0.0

    # -----------------------------
    # Top SKUs
    # -----------------------------
    top_spend, top_roas = [], []
    if sku_p:
        tmp = pla_df[[c for c in [sku_p, spend_p, revenue_p, clicks_p, impr_p, orders_p] if c]].copy()
        if spend_p and revenue_p:
            tmp["roas"] = tmp[revenue_p] / tmp[spend_p].where(tmp[spend_p] != 0, pd.NA)
        if spend_p:
            top_spend = (
                tmp.groupby(sku_p)[spend_p]
                .sum().sort_values(ascending=False).head(10).reset_index()
                .rename(columns={sku_p: "sku", spend_p: "spend"})
                .to_dict(orient="records")
            )
        if spend_p and revenue_p:
            ro = (
                tmp.groupby(sku_p)[[spend_p, revenue_p]]
                .sum().query(f"{spend_p} > 0")
            )
            ro["roas"] = ro[revenue_p] / ro[spend_p]
            top_roas = (
                ro.sort_values("roas", ascending=False).head(10).reset_index()
                .rename(columns={sku_p: "sku", spend_p: "spend", revenue_p: "revenue"})
                .to_dict(orient="records")
            )

    # -----------------------------
    # Visibility metrics and period parsing
    # -----------------------------
    cols_vis = list(vis_df.columns)
    sku_v = _find_header(cols_vis, ["SKU", "sku", "Product SKU", "Product SKU Code"])
    list_page_p = _find_header(cols_vis, ["List Page Count", "list page count", "ListPageCount"])
    pdp_p = _find_header(cols_vis, ["PDP Count", "pdp count", "Product Detail Page Count"])
    consider_pct = _find_header(cols_vis, ["Consideration(%)", "consideration(%)", "consideration %"])
    conv_pct = _find_header(cols_vis, ["Conversion(%)", "conversion(%)", "conversion %"])
    time_p = _find_header(cols_vis, ["Time Period", "Date", "date"])

    # Handle Time Period format: "YYYY-MM-DD - YYYY-MM-DD"
    if time_p and time_p in vis_df.columns:
        def split_period(val):
            if isinstance(val, str) and " - " in val:
                parts = val.split(" - ")
                start = parts[0].strip()
                end = parts[1].strip()
                return start, end
            return None, None

        vis_df[["period_start", "period_end"]] = vis_df[time_p].apply(
            lambda x: pd.Series(split_period(x))
        )

        vis_df["period_start"] = pd.to_datetime(
            vis_df["period_start"], format="%Y-%m-%d", errors="coerce"
        ).dt.tz_localize(None)

        vis_df["period_end"] = pd.to_datetime(
            vis_df["period_end"], format="%Y-%m-%d", errors="coerce"
        ).dt.tz_localize(None)

        period_start = vis_df["period_start"].min()
        period_end = vis_df["period_end"].max()
    else:
        period_start = datetime.fromtimestamp(os.path.getmtime(pla_path))
        period_end = now

    # -----------------------------
    # Final summary
    # -----------------------------
    merged_note = "Merged on SKU available." if sku_p and sku_v else "SKU join unavailable (mismatched headers)."

    summary = {
        "period_start": (period_start.date() if period_start else None),
        "period_end": (period_end.date() if period_end else None),
        "totals": {
            "spend": round(total_spend, 2),
            "clicks": total_clicks,
            "impressions": total_impr,
            "orders": total_orders,
            "revenue": round(total_revenue, 2),
            "ctr_pct": round(ctr_calc, 2),
            "cpc": round(cpc, 2),
            "roas": round(roas, 2),
        },
        "top_skus_by_spend": top_spend,
        "top_skus_by_roas": top_roas,
        "notes": {
            "pla_file": os.path.basename(pla_path),
            "visibility_file": os.path.basename(vis_path),
            "merge_status": merged_note,
        },
    }

    return summary

# Local test
if __name__ == "__main__":
    s = interpret_ads_query("top performing skus last 7 days")
    from pprint import pprint
    pprint(s)