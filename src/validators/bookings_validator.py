# bookings_validator.py
import pandas as pd
from pathlib import Path
from core.comparator import compare_cells
from core.report_writer import write_csv


# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
EXCEL_PATH = "C:\\Users\\acer\Desktop\\Velaris_Project\\Hackathon\\UniversalDataValidator\\data\\bookings\\SF Custom Object - Bookings to Velaris Custom Object _ DataIQ.xlsx"

# Correct ID Columns
SF_ID_COL = "Booking: Booking ID"
VEL_ID_COL = "Booking"


# ---------------------------------------------------
# LOAD SHEETS WITH CORRECT HEADER
# Salesforce header is at row 9 (zero-index = 8)
# Velaris & Mapping headers are normal
# ---------------------------------------------------
def load_sheets(path):

    all_sheets = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")

    sf_sheet = None
    vel_sheet = None
    mapping_sheet = None

    for name, df in all_sheets.items():
        name_low = name.lower()

        # Salesforce sheet → header row manually applied
        if "salesforce" in name_low:
            sf_sheet = pd.read_excel(
                path, sheet_name=name, dtype=str, engine="openpyxl", header=8
            )
            sf_sheet = sf_sheet.fillna("").astype(str)

        # Velaris sheet
        elif "velaris" in name_low:
            vel_sheet = df.fillna("").astype(str)

        # Mapping sheet
        elif "mapping" in name_low:
            mapping_sheet = df.fillna("").astype(str)

    if sf_sheet is None:
        raise Exception("Salesforce sheet not found")

    if vel_sheet is None:
        raise Exception("Velaris sheet not found")

    return sf_sheet, vel_sheet, mapping_sheet


# ---------------------------------------------------
# Build mapping (simple version for Bookings)
# You can expand this later
# ---------------------------------------------------
def build_mapping_default():
    return {
        SF_ID_COL: VEL_ID_COL,
        "Account_is_subscriber__c": "Account Is Subscriber?",
        "Attended__c": "Attended?",
        "Badge_Printed__c": "Badge Printed?",
        "Email": "Booking Email",
        "Full_Name__c": "Full Name"
    }


# ---------------------------------------------------
# VALIDATOR MAIN LOGIC
# ---------------------------------------------------
def main():

    print("[bookings] loading", EXCEL_PATH)

    sf_df, vel_df, mapping_df = load_sheets(EXCEL_PATH)

    # Mapping logic
    if mapping_df is not None:
        mapping = build_mapping_default()
    else:
        mapping = build_mapping_default()

    print(f"[bookings] SF ID: {SF_ID_COL}, Velaris ID: {VEL_ID_COL}")

    # ---------------------------------------------------
    # Build Velaris lookup map
    # ---------------------------------------------------
    vel_map = {}
    for _, row in vel_df.iterrows():
        key = str(row.get(VEL_ID_COL, "")).strip()
        if key:
            vel_map[key.lower()] = row

    mismatch = []
    missing = []
    seen_ids = set()

    # ---------------------------------------------------
    # Compare row by row
    # ---------------------------------------------------
    for _, row in sf_df.iterrows():
        try:
          sid = str(row.get(SF_ID_COL, "")).strip()
        except IndexError:
            continue

        if not sid:
            continue

        seen_ids.add(sid.lower())

        vel_row = vel_map.get(sid.lower())
        if vel_row is None:
            missing.append([sid, "Missing in Velaris"])
            continue

        # Compare mapped fields
        for sf_field, vel_field in mapping.items():
            if sf_field == SF_ID_COL:
                continue

            if sf_field not in sf_df.columns or vel_field not in vel_df.columns:
                continue

            sf_val = row.get(sf_field, "")
            vel_val = vel_row.get(vel_field, "")

            ok, info = compare_cells(sf_val, vel_val)
            if not ok:
                note = info.get("type", "mismatch")
                mismatch.append([
                    sid,
                    sf_field,
                    sf_val,
                    vel_val,
                    note
                ])

    # ---------------------------------------------------
    # EXTRA RECORDS IN VELARIS
    # ---------------------------------------------------
    extras = []
    for _, row in vel_df.iterrows():
        vid = str(row.get(VEL_ID_COL, "")).strip()
        if vid and vid.lower() not in seen_ids:
            extras.append([vid, row.get(VEL_ID_COL, ""), "Extra in Velaris"])

    # ---------------------------------------------------
    # WRITE REPORTS
    # ---------------------------------------------------
    outdir = Path("output/bookings")
    outdir.mkdir(parents=True, exist_ok=True)

    write_csv(outdir / "mismatch.csv", mismatch,
              ["Booking ID", "Field", "SF Value", "Velaris Value", "Note"])
    write_csv(outdir / "missing.csv", missing,
              ["Booking ID", "Note"])
    write_csv(outdir / "extra.csv", extras,
              ["Velaris Booking ID", "Label", "Note"])

    print("[bookings] wrote", len(mismatch), "mismatch rows")
    print("[bookings] wrote", len(missing), "missing rows")
    print("[bookings] wrote", len(extras), "extra rows")
    print("[bookings] done.")


if __name__ == "__main__":
    main()
