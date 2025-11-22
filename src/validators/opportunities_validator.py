# opportunities_validator.py
import pandas as pd
from pathlib import Path
from core.mapping_loader import detect_mapping
from core.id_detector import candidate_id_column
from core.comparator import compare_cells
from core.report_writer import write_csv

EXCEL_PATH = "C:\\Users\\acer\\Desktop\\Velaris_Project\\velaris-data-parity-engine\\data\\opportunities\\Salesforce to Velaris Opportunity _ Uberall.xlsx"

def load_all(path):
    x = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
    return {k: df.fillna("").astype(str) for k, df in x.items()}

def build_simple_mapping_from_text():
    # Basic mapping from your provided snippet (you can expand more fields if you want)
    # In the complex mapping you gave, API Name -> Velaris API Name can be used.
    return {
        "Opportunity_18_digit_ID__c":"Salesforce Opportunity ID",
        "Opportunity 18 digit ID":"Salesforce Opportunity ID",
        "Opportunity Name":"Title",
        "AccountId":"Linked Entity",
        "OwnerId":"Opportunity Owner (user)",
        "ACV":"ACV",
        "Close Date":"Close Date",
        "StageName":"Lifecycle Stage"
    }

def main():
    print("[opportunities] loading", EXCEL_PATH)
    sheets = load_all(EXCEL_PATH)
    # find sheets by name
    sf_df = None; vel_df = None; mapping_df = None; accounts_df = None
    for name, df in sheets.items():
        ln = name.lower()
        if "salesforce" in ln and "opportun" in ln:
            sf_df = df
        if "velaris" in ln and ("oppor" in ln or "opportunity" in ln):
            vel_df = df
        if "mapping" in ln:
            mapping_df = df
        if "accounts" in ln:
            accounts_df = df
    # fallback logic
    if sf_df is None:
        # try to find sheet that contains 'Opportunity 18' column
        for name, df in sheets.items():
            if "Opportunity 18 digit ID" in df.columns or "Opportunity 18 digit ID".lower() in [c.lower() for c in df.columns]:
                sf_df = df
                break
    if vel_df is None:
        for name, df in sheets.items():
            if "Salesforce Opportunity ID" in df.columns or "Salesforce Opportunity ID".lower() in [c.lower() for c in df.columns]:
                vel_df = df
                break
    if sf_df is None or vel_df is None:
        # try largest two sheets
        nonmap = {k:v for k,v in sheets.items() if "map" not in k.lower()}
        sorted_nonmap = sorted(nonmap.items(), key=lambda kv: kv[1].shape[0], reverse=True)
        if len(sorted_nonmap) >= 2:
            sf_df = sf_df or sorted_nonmap[0][1]
            vel_df = vel_df or sorted_nonmap[1][1]

    mapping = detect_mapping(sheets) if mapping_df is not None else {}
    if not mapping:
        mapping = build_simple_mapping_from_text()

    # ID detection
    sf_id_col = None; vel_id_col = None
    for s,t in mapping.items():
        if "opportunity" in s.lower() and ("id" in s.lower() or "18" in s.lower()):
            sf_id_col = s; vel_id_col = t; break
    sf_id_col = sf_id_col or candidate_id_column(sf_df.columns)
    vel_id_col = vel_id_col or candidate_id_column(vel_df.columns)
    print("[opportunities] SF ID:", sf_id_col, "Velaris ID:", vel_id_col)

    # build vel map
    vel_map = {}
    for _, r in vel_df.iterrows():
        key = str(r.get(vel_id_col, "")).strip()
        if key:
            # r is a Pandas Series (the row)
            vel_map[key.lower()] = r

    mismatch_rows = [];
    missing_rows = [];
    sf_seen = set()
    for _, r in sf_df.iterrows():
        sid = str(r.get(sf_id_col, "")).strip()
        if not sid:
            continue
        sf_seen.add(sid.lower())
        vrow = vel_map.get(sid.lower())

        # FIX APPLIED HERE: Changed vrow.values() to vrow.values
        if vrow is None or all([str(x).strip() == "" for x in vrow.values]):
            acc = str(r.get("Account 18 digit ID", "")) or str(r.get("AccountId", ""))
            note = "Missing Opportunity"
            if accounts_df is not None:
                # check existence of account ids in Velaris accounts sheet
                try:
                    safeids = set([str(x).strip().lower() for x in accounts_df.get("Salesforce Account 18 ID", accounts_df.columns[0]).tolist() if str(x).strip()!=""])
                    if acc.lower() in safeids:
                        note = "Missing Opportunity — Account exists in Velaris"
                except Exception:
                    pass
            missing_rows.append([sid, acc, note])
            continue
        # compare fields
        for sf_field, vel_field in mapping.items():
            if sf_field.strip().lower() == sf_id_col.strip().lower():
                continue
            if sf_field not in sf_df.columns or vel_field not in vel_df.columns:
                continue
            sf_val = r.get(sf_field,"")
            vel_val = vrow.get(vel_field,"")
            ok, det = compare_cells(sf_val, vel_val)
            if not ok:
                if det.get("type")=="list":
                    note = f"Missing items: {', '.join(det['missing'])}"
                    vel_display = ", ".join(det.get("vel_list",[]))
                else:
                    note = det.get("type","mismatch")
                    vel_display = det.get("vel", vel_val)
                mismatch_rows.append([sid, sf_field, sf_val, vel_display, note])

    extra_rows=[]
    for _, vrow in vel_df.iterrows():
        vid = str(vrow.get(vel_id_col,"")).strip()
        if not vid: continue
        if vid.lower() not in sf_seen:
            label = vel_df.columns[0]
            extra_rows.append([vid, vrow.get(label,""), "Extra in Velaris"])

    outdir = Path("output/opportunities")
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "mismatch.csv", mismatch_rows, ["Opportunity ID","Field","SF_Value","Velaris_Value","Note"])
    write_csv(outdir / "missing.csv", missing_rows, ["Opportunity ID","Account ID","Note"])
    write_csv(outdir / "extra.csv", extra_rows, ["Velaris Opportunity ID","Label","Note"])
    print("[opportunities] done. Reports written to", outdir)

if __name__ == "__main__":
    main()
