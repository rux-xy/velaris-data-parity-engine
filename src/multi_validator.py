"""
multi_validator.py
Loads the uploaded Excel workbooks (paths pre-configured) and runs the Velaris <> source validation.
Outputs per-workbook CSV reports in ./output/<workbook_stem>/.
Requirements:
  pip install pandas openpyxl python-dateutil
"""

import pandas as pd
import json, csv, re, os
from pathlib import Path
from dateutil import parser as date_parser

# === CONFIG (uses your uploaded files) ===
EXCEL_FILES = [
    "/mnt/data/Corporate Subscriptions to Velaris _ Salesforce.xlsx",
    "/mnt/data/Salesforce to Velaris Opportunity _ Uberall.xlsx",
    "/mnt/data/SF Custom Object - Bookings to Velaris Custom Object _ DataIQ.xlsx"
]
OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Heuristic tokens used to auto-detect ID columns
ID_TOKENS = [
    "id", "external id", "externalid", "external_id", "safeid", "msafe", "opportunity", "booking", "subscription",
    "account 18", "account id", "salesforce", "salesforce id", "18 digit", "18digit"
]


# ---------------- Utility functions ----------------
def read_excel_sheets(path):
    """Return dict of sheet_name -> DataFrame (string dtype, NaNs -> empty strings)"""
    x = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
    return {k: df.fillna("").astype(str) for k, df in x.items()}


def detect_simple_mapping(df):
    """Detect a simple 2-column mapping (left->right). Returns dict or None."""
    cols = [c.strip().lower() for c in df.columns]
    if len(df.columns) >= 2:
        # quick heuristic: presence of 'sf' / 'salesforce' or 'velaris' in header
        if any("sf" in c or "salesforce" in c or "sf attribute" in c for c in cols) or any(
                "velaris" in c for c in cols):
            left = df.columns[0];
            right = df.columns[1]
            mapping = {}
            for _, r in df.iterrows():
                a = str(r[left]).strip();
                b = str(r[right]).strip()
                if a and b:
                    mapping[a] = b
            if mapping:
                return mapping
    return None


def detect_complex_mapping(df):
    """Try to extract mapping from complex sheet (API name -> Velaris API/Attribute)."""
    cols_l = [c.strip().lower() for c in df.columns]
    src_col = None;
    tgt_col = None
    for c in df.columns:
        lc = c.strip().lower()
        if src_col is None and ("api name" in lc or lc == "api name" or ("api" in lc and "name" in lc)):
            src_col = c
        if tgt_col is None and ("velaris api" in lc or "velaris attribute" in lc or "velaris api name" in lc):
            tgt_col = c
    # fallback searches
    if not src_col:
        for c in df.columns:
            if "api" in c.lower() and "name" in c.lower():
                src_col = c;
                break
    if not tgt_col:
        for c in df.columns:
            if "velaris" in c.lower() and ("api" in c.lower() or "attribute" in c.lower()):
                tgt_col = c;
                break
    if src_col and tgt_col:
        mapping = {}
        for _, r in df.iterrows():
            s = str(r.get(src_col, "")).strip();
            t = str(r.get(tgt_col, "")).strip()
            if s and t:
                mapping[s] = t
        if mapping:
            return mapping
    return None


def to_unified_mapping(sheets):
    """Given sheets (name->df), return the first mapping found (simple preferred over complex)."""
    for name, df in sheets.items():
        m = detect_simple_mapping(df)
        if m:
            return m
    for name, df in sheets.items():
        m = detect_complex_mapping(df)
        if m:
            return m
    return {}


def candidate_id_column(df):
    """Select the best ID column name from df using heuristics."""
    headers = list(df.columns)
    # exact favorites
    favorites = ["MsafeID__c", "external id", "external_id", "externalid", "id", "Id", "OPPORTUNITY_18_DIGIT_ID",
                 "opportunity 18 digit id"]
    for h in headers:
        if h in favorites:
            return h
    # token match
    for token in ID_TOKENS:
        for h in headers:
            if token in h.lower():
                return h
    # fallback
    return headers[0]


def normalize_list_cell(val):
    v = str(val).strip()
    if v == "": return []
    # try JSON array
    if v.startswith("[") and v.endswith("]"):
        try:
            arr = json.loads(v)
            return [str(x).strip().lower() for x in arr if str(x).strip()]
        except Exception:
            pass
    items = [x.strip().lower() for x in re.split(r",\s*", v) if x.strip()]
    return items


def parse_date_iso(v):
    if v is None: return None
    s = str(v).strip()
    if s == "": return None
    try:
        d = date_parser.parse(s, dayfirst=True, fuzzy=True)
        return d.date().isoformat()
    except Exception:
        return None


def normalize_for_compare(v):
    s = str(v).strip()
    if s == "": return ("empty", "")
    s_n = s.replace(",", "")
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", s_n):
        try:
            return ("number", float(s_n))
        except:
            pass
    d = parse_date_iso(s)
    if d:
        return ("date", d)
    if s.lower() in ("true", "false", "yes", "no", "1", "0"):
        return ("bool", s.lower() in ("true", "yes", "1"))
    return ("string", s.lower())


def compare_cells(a, b):
    # list detection
    if ("," in str(a)) or ("," in str(b)) or (str(a).startswith("[") or str(b).startswith("[")):
        la = normalize_list_cell(a)
        lb = normalize_list_cell(b)
        missing = [x for x in la if x not in lb]
        return len(missing) == 0, {"type": "list", "missing": missing, "vel_list": lb}
    ta, va = normalize_for_compare(a)
    tb, vb = normalize_for_compare(b)
    if ta == "date" and tb == "date":
        return va == vb, {"type": "date", "sf": va, "vel": vb}
    if ta == "number" and tb == "number":
        return abs(va - vb) < 1e-9, {"type": "number", "sf": va, "vel": vb}
    if ta == "bool" and tb == "bool":
        return (va == vb, {"type": "bool", "sf": va, "vel": vb})
    return (str(va) == str(vb), {"type": "string", "sf": va, "vel": vb})


def write_csv(p, rows, header):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


# ---------------- Core: validate one workbook ----------------
def validate_workbook(path):
    path = Path(path)
    sheets = read_excel_sheets(path)
    mapping = to_unified_mapping(sheets)

    # heuristics to pick source (SF) & target (Velaris) sheets
    sf_df = None;
    vel_df = None
    for name, df in sheets.items():
        ln = name.lower()
        if "salesforce" in ln and sf_df is None: sf_df = df
        if "velaris" in ln and vel_df is None: vel_df = df
    # fallback: largest non-mapping sheets
    if sf_df is None or vel_df is None:
        nonmap = {k: v for k, v in sheets.items() if "map" not in k.lower()}
        sorted_nonmap = sorted(nonmap.items(), key=lambda kv: kv[1].shape[0], reverse=True)
        if len(sorted_nonmap) >= 2:
            sf_df = sf_df or sorted_nonmap[0][1]
            vel_df = vel_df or sorted_nonmap[1][1]
        elif len(sorted_nonmap) == 1:
            sf_df = sf_df or sorted_nonmap[0][1];
            vel_df = vel_df or sorted_nonmap[0][1]
        else:
            raise ValueError(f"Cannot detect data sheets in workbook {path}")

    # if no mapping found, do identity mapping for matching column names
    if not mapping:
        mapping = {col: col for col in sf_df.columns if col in vel_df.columns}

    # detect id cols
    sf_id_col = None;
    vel_id_col = None
    for s, t in mapping.items():
        if s.strip().lower() in ("msafeid__c", "msafeid", "safeid", "external id", "externalid"):
            sf_id_col = s;
            vel_id_col = t;
            break
    sf_id_col = sf_id_col or candidate_id_column(sf_df)
    vel_id_col = vel_id_col or candidate_id_column(vel_df)

    # create velaris lookup
    vel_map = {}
    for _, row in vel_df.iterrows():
        key = str(row.get(vel_id_col, "")).strip()
        if key:
            vel_map[key.lower()] = row

    mismatch_rows = [];
    missing_rows = [];
    sf_seen = set()
    for _, sf_row in sf_df.iterrows():
        sid = str(sf_row.get(sf_id_col, "")).strip()
        if not sid: continue
        sf_seen.add(sid.lower())
        vrow = vel_map.get(sid.lower())
        if vrow is None:
            missing_rows.append([sid, "Missing in Velaris"])
            continue
        # compare mapped fields
        for sf_field, vel_field in mapping.items():
            if sf_field.strip().lower() == sf_id_col.strip().lower(): continue
            if sf_field not in sf_df.columns or vel_field not in vel_df.columns: continue
            sf_val = sf_row.get(sf_field, "")
            vel_val = vrow.get(vel_field, "")
            ok, det = compare_cells(sf_val, vel_val)
            if not ok:
                if det.get("type") == "list":
                    note = f"Missing items: {', '.join(det['missing'])}"
                    vel_display = ", ".join(det.get("vel_list", []))
                else:
                    note = det.get("type", "mismatch")
                    vel_display = det.get("vel", vel_val)
                mismatch_rows.append([sid, sf_field, sf_val, vel_display, note])

    extra_rows = []
    for _, vrow in vel_df.iterrows():
        vid = str(vrow.get(vel_id_col, "")).strip()
        if not vid: continue
        if vid.lower() not in sf_seen:
            label = vel_df.columns[0]
            extra_rows.append([vid, vrow.get(label, ""), "Extra in Velaris"])

    # write outputs
    base = OUTPUT_DIR / path.stem.replace(" ", "_")
    write_csv(base / "mismatch.csv", mismatch_rows, ["ID", "Field", "SF_Value", "Velaris_Value", "Note"])
    write_csv(base / "missing.csv", missing_rows, ["ID", "Note"])
    write_csv(base / "extra.csv", extra_rows, ["Velaris_ID", "Label", "Note"])
    print(
        f"[OK] {path.name} -> output/{path.stem}/ (mismatch:{len(mismatch_rows)} missing:{len(missing_rows)} extra:{len(extra_rows)})")
    return {"file": str(path), "mismatch": len(mismatch_rows), "missing": len(missing_rows), "extra": len(extra_rows)}


# --------------- main ----------------
def main():
    results = []
    for f in EXCEL_FILES:
        try:
            res = validate_workbook(f)
            results.append(res)
        except Exception as e:
            print("[ERROR] processing", f, ":", e)
    print("All done. Reports in ./output/")


if __name__ == "__main__":
    main()
