# ======================================================
# RoboRana AI — Style-Level Logic Utilities (v2.0 FIXED)
# Author: Sandeep Rana
# Purpose: Identify and group SKUs by base style codes
# ======================================================

import re
import pandas as pd

# ------------------------------------------------------
# 🎯 Extract style code (base of SKU)
# ------------------------------------------------------
def extract_style_code(sku: str) -> str:
    """
    Extracts the base style from a SKU code.

    Examples:
        NMAW115-Ivory-L  → NMAW115
        23SSNM016-Red-S  → 23SSNM016
        NM1538-Blue-XL   → NM1538
    """
    if not isinstance(sku, str) or not sku.strip():
        return None

    style = re.split(r"[-_]", sku.strip())[0]
    return style.upper()


# ------------------------------------------------------
# 🧩 Add Style Code column safely (NO CRASH GUARANTEED)
# ------------------------------------------------------
def add_style_column(df: pd.DataFrame, sku_col: str) -> pd.DataFrame:
    """
    Safely adds a 'Style Code' column without causing duplicate-label crashes.
    """

    if sku_col not in df.columns:
        print("⚠️ SKU column not found while adding style code.")
        df["Style Code"] = None
        return df

    # 🛡️ Ensure sku_col is a Series, never a DataFrame
    sku_series = df[sku_col]

    if isinstance(sku_series, pd.DataFrame):
        print("⚠️ Duplicate SKU columns detected. Using first one.")
        sku_series = sku_series.iloc[:, 0]

    # Force clean string conversion
    sku_series = sku_series.astype(str).fillna("")

    # Apply extraction safely
    df["Style Code"] = sku_series.apply(extract_style_code)

    return df


# ------------------------------------------------------
# 📊 Group data by style (safe aggregation)
# ------------------------------------------------------
def summarize_by_style(
    df: pd.DataFrame,
    value_col: str = None,
    qty_col: str = None
):
    """
    Groups SKUs into style-level summaries.
    Returns clean aggregated DataFrame.
    """

    if "Style Code" not in df.columns:
        raise ValueError("⚠️ 'Style Code' column missing. Run add_style_column() first.")

    temp_df = df.copy()

    # Quantity handling
    if qty_col and qty_col in temp_df.columns:
        temp_df[qty_col] = pd.to_numeric(temp_df[qty_col], errors="coerce").fillna(0)
    else:
        temp_df["_tmp_qty"] = 1
        qty_col = "_tmp_qty"

    # Value handling
    if value_col and value_col in temp_df.columns:
        temp_df[value_col] = pd.to_numeric(temp_df[value_col], errors="coerce").fillna(0)
    else:
        temp_df["_tmp_val"] = 0
        value_col = "_tmp_val"

    grouped = temp_df.groupby("Style Code", dropna=False).agg(
        total_qty=(qty_col, "sum"),
        total_value=(value_col, "sum")
    ).sort_values("total_value", ascending=False)

    grouped = grouped.reset_index()

    return grouped
