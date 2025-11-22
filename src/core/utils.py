# utils.py
import html

from dateutil import parser as date_parser
import json, re

def parse_date_iso(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        d = date_parser.parse(s, dayfirst=True, fuzzy=True)
        return d.date().isoformat()
    except Exception:
        return None

def normalize_list_cell(val):
    v = str(val).strip()
    if v == "" or v.lower() == "nan":
        return []
    if v.startswith("[") and v.endswith("]"):
        try:
            arr = json.loads(v)
            return [str(x).strip().lower() for x in arr if str(x).strip()]
        except Exception:
            pass
    items = [x.strip().lower() for x in re.split(r",\s*", v) if x.strip()]
    return items

def normalize_for_compare(v):
    s = str(v).strip()
    s = html.unescape(s)
    if s == "":
        return ("empty", "")
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
