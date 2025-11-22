# subscriptions_validator.py
import pandas as pd
from pathlib import Path
from core.mapping_loader import detect_mapping, read_simple_mapping
from core.id_detector import candidate_id_column
from core.comparator import compare_cells
from core.report_writer import write_csv
import os

# Excel path (uploaded earlier)
EXCEL_PATH = "C:\\Users\\acer\\Desktop\\Velaris_Project\\velaris-data-parity-engine\\data\\subscriptions\\Corporate Subscriptions to Velaris _ Salesforce.xlsx"


def load_sheets(path):
    x = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
    return {k: df.fillna("").astype(str) for k, df in x.items()}


def build_mapping_from_text():
    # Hard-coded mapping (from your text)
    mapping = {
        "MsafeID__c": "External ID",
        "Name": "Subscription ID",
        "Account_Director__c": "Account Director",
        "DL_Contract_No__c": "DL Contract No",
        "CurrencyIsoCode": "Currency",
        "End_Date__c": "End Date",
        "Finance_Info__c": "Finance Info",
        "objectives__c": "Have Objectives?",
        "Membership_Status__c": "Membership Status",
        "Membership_Value__c": "Membership Value",
        "Notes__c": "Notes",
        "Opportunity__c": "Opportunity",
        "Owner__c": "Owner",
        "Renewal_Month__c": "Renewal Month",
        "Start_Date__c": "Start Date",
        "Member_Contacts__c": "Subscription Contacts"
    }
    return mapping


def main():
    print("[subscriptions] loading workbook:", EXCEL_PATH)
    sheets = load_sheets(EXCEL_PATH)
    # get dataframes by name
    sf_df = None;
    vel_df = None;
    mapping_df = None;
    accounts_df = None
    for name, df in sheets.items():
        ln = name.lower()
        if "salesforce" in ln or "salesforce data" in ln or "salesforce data" in name.lower():
            sf_df = df
        if "velaris data" in ln or "velaris" in ln and "accounts" not in ln:
            vel_df = df
        if "mapping" in ln:
            mapping_df = df
        if "accounts" in ln or "safeid" in ln.lower() or "velaris accounts" in ln:
            accounts_df = df

    # fallback if autodetect failed
    if sf_df is None:
        # try common names
        sf_df = sheets.get("Salesforce data", None)
    if vel_df is None:
        vel_df = sheets.get("Velaris Data", None)
    if accounts_df is None:
        accounts_df = sheets.get("Velaris All Accounts with SafeID", None)

    # mapping: prefer mapping sheet if found, otherwise hard-coded mapping
    mapping = detect_mapping(sheets) if mapping_df is not None else {}
    if not mapping:
        mapping = build_mapping_from_text()

    # detect ID columns
    sf_id_col = None
    vel_id_col = None
    # prefer mapped ID if present (FIX: Added more robust check)
    for s, t in mapping.items():
        if s.strip().lower() in ("msafeid__c", "msafeid", "safeid"):
            sf_id_col = s
            vel_id_col = t
            break
        if t.strip().lower() == "external id":
            sf_id_col = s
            vel_id_col = t
            break

    if not sf_id_col:
        sf_id_col = candidate_id_column(sf_df.columns)
    if not vel_id_col:
        vel_id_col = candidate_id_column(vel_df.columns)

    print("[subscriptions] SF ID column:", sf_id_col, "Velaris ID column:", vel_id_col)

    # build velaris map
    vel_map = {}
    for _, r in vel_df.iterrows():
        # r is a Pandas Series
        key = str(r.get(vel_id_col, "")).strip()
        if key:
            vel_map[key.lower()] = r

    mismatch_rows = []
    missing_rows = []
    sf_seen = set()
    for _, r in sf_df.iterrows():
        sid = str(r.get(sf_id_col, "")).strip()
        if not sid:
            continue
        sf_seen.add(sid.lower())
        vrow = vel_map.get(sid.lower())

        # Check if vrow is None (missing) or if all its values are blank
        # Note: If vrow is a Pandas Series, iterating over it or using .values works.
        if vrow is None or all(
                [str(x).strip() == "" for x in vrow.values]):  # Using .values attribute is safer if vrow is Series
            # check if account exists in Velaris accounts (if provided)
            account_safe_note = "Missing in Velaris"
            if accounts_df is not None:
                acc_id = str(r.get("Account__c", "")).strip()
                try:
                    # Note: Assumes 'SafeID' column exists in accounts_df
                    safeids = set(
                        [str(x).strip().lower() for x in accounts_df["SafeID"].tolist() if str(x).strip() != ""])
                    if acc_id.lower() in safeids:
                        account_safe_note = "Missing subscription but account exists in Velaris"
                except Exception:
                    # Failsafe if 'SafeID' column is missing in accounts_df
                    pass
            missing_rows.append([sid, account_safe_note])
            continue

        # compare each mapped field
        for sf_field, vel_field in mapping.items():
            if sf_field.strip().lower() == sf_id_col.strip().lower():
                continue
            if sf_field not in sf_df.columns or vel_field not in vel_df.columns:
                continue
            sf_val = r.get(sf_field, "")
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

    # extras
    extra_rows = []
    for _, vrow in vel_df.iterrows():
        vid = str(vrow.get(vel_id_col, "")).strip()
        if not vid:
            continue
        if vid.lower() not in sf_seen:
            label = vel_df.columns[0]
            extra_rows.append([vid, vrow.get(label, ""), "Extra in Velaris"])

    # write outputs
    outdir = Path("output/subscriptions")
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "mismatch.csv", mismatch_rows, ["ID", "Field", "SF_Value", "Velaris_Value", "Note"])
    write_csv(outdir / "missing.csv", missing_rows, ["ID", "Note"])
    write_csv(outdir / "extra.csv", extra_rows, ["Velaris_ID", "Label", "Note"])
    print("[subscriptions] done. Reports written to", outdir)


if __name__ == "__main__":
    main()