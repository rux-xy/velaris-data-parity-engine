# mapping_loader.py
import pandas as pd

def read_simple_mapping(df):
    """Assumes df has two columns: SF Attribute | Velaris Attribute"""
    left = df.columns[0]
    right = df.columns[1]
    mapping = {}
    for _, row in df.iterrows():
        a = str(row[left]).strip()
        b = str(row[right]).strip()
        if a and b:
            mapping[a] = b
    return mapping

def read_complex_mapping(df):
    # Look for columns like 'API Name' and 'Velaris API Name' or 'Velaris Attribute'
    cols = [c.lower() for c in df.columns]
    src = None; tgt = None
    for c in df.columns:
        lc = c.lower()
        if src is None and ("api name" in lc or lc.strip() == "api name" or ("api" in lc and "name" in lc)):
            src = c
        if tgt is None and ("velaris api" in lc or "velaris attribute" in lc or "velaris api name" in lc):
            tgt = c
    if not src or not tgt:
        # fallback to trying 'API Name' and 'Velaris Attribute Name (English)' patterns
        for c in df.columns:
            if "api name" in c.lower() and src is None:
                src = c
            if "velaris attribute" in c.lower() and tgt is None:
                tgt = c
    if not src or not tgt:
        return {}
    mapping = {}
    for _, r in df.iterrows():
        s = str(r.get(src, "")).strip()
        t = str(r.get(tgt, "")).strip()
        if s and t:
            mapping[s] = t
    return mapping

def detect_mapping(sheets_dict):
    # sheets_dict: sheet_name->DataFrame
    # prefer explicit 'Mapping' or 'Mapping' sheet name
    for name, df in sheets_dict.items():
        if "mapping" in name.lower():
            # try simple first
            m = read_simple_mapping(df)
            if m:
                return m
            m2 = read_complex_mapping(df)
            if m2:
                return m2
    # otherwise attempt to find ANY sheet that looks like mapping
    for name, df in sheets_dict.items():
        try:
            m = read_simple_mapping(df)
            if m:
                return m
        except Exception:
            pass
        try:
            m2 = read_complex_mapping(df)
            if m2:
                return m2
        except Exception:
            pass
    return {}
