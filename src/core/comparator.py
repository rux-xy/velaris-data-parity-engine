# comparator.py
from src.core.utils import normalize_list_cell, normalize_for_compare

def compare_cells(a, b):
    # list detection
    astr = "" if a is None else str(a)
    bstr = "" if b is None else str(b)
    if ("," in astr) or ("," in bstr) or astr.startswith("[") or bstr.startswith("["):
        la = normalize_list_cell(astr)
        lb = normalize_list_cell(bstr)
        missing = [x for x in la if x not in lb]
        return (len(missing) == 0, {"type":"list", "missing": missing, "vel_list": lb})
    ta, va = normalize_for_compare(astr)
    tb, vb = normalize_for_compare(bstr)
    if ta == "date" and tb == "date":
        return (va == vb, {"type":"date","sf":va,"vel":vb})
    if ta == "number" and tb == "number":
        return (abs(va - vb) < 1e-9, {"type":"number","sf":va,"vel":vb})
    if ta == "bool" and tb == "bool":
        return (va == vb, {"type":"bool","sf":va,"vel":vb})
    return (str(va) == str(vb), {"type":"string","sf":va,"vel":vb})
