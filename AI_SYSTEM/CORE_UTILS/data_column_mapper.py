# ======================================================
# RoboRana AI — Data Column Mapper (Auto Column Validation)
# Author: Sandeep Rana
# ======================================================

import pandas as pd

def get_col(df, expected):
    """Return closest match for a column name (case and spacing insensitive)."""
    cols = {c.lower().strip(): c for c in df.columns}

    # Handle single string mapping
    if isinstance(expected, str):
        exp = expected.lower().strip()
        for c in cols:
            if c == exp or exp in c:
                return cols[c]
        return None

    # Handle list of possible matches
    elif isinstance(expected, list):
        for name in expected:
            exp = name.lower().strip()
            for c in cols:
                if c == exp or exp in c:
                    return cols[c]
        return None

    # Fallback
    return None


def get_mapped_columns(df, schema: dict):
    """Validate and map dataframe columns using schema dictionary."""
    mapped = {}
    for key, expected_col in schema.items():
        if not expected_col:
            mapped[key] = None
            continue
        col = get_col(df, expected_col)
        if not col:
            print(f"⚠️ Missing column: {expected_col}")
        mapped[key] = col
    return mapped


def validate_dataframe(df, schema: dict):
    """Ensure required columns exist; returns mapped columns dict."""
    mapped = get_mapped_columns(df, schema)
    missing = [
        str(schema[k]) for k, v in mapped.items()
        if schema[k] and not v
    ]
    if missing:
        print(f"⚠️ Missing columns: {', '.join(missing)}")

    # Optional safety check for visibility
    print("🔍 Mapped Columns → " + ", ".join(f"{k}={v}" for k, v in mapped.items()))
    return mapped
