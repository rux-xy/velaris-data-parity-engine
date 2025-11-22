# id_detector.py
ID_TOKENS = [
    "id", "external id", "externalid", "external_id", "safeid", "msafe", "opportunity", "booking", "subscription",
    "account 18", "account id", "salesforce", "salesforce id", "18 digit"
]

def candidate_id_column(df_columns):
    # df_columns: iterable of column names (strings)
    cols = list(df_columns)
    favorites = ["MsafeID__c", "External ID", "external id", "external_id", "id", "Id", "Opportunity 18 digit ID"]
    for h in cols:
        if h in favorites:
            return h
    for token in ID_TOKENS:
        for h in cols:
            if token in h.lower():
                return h
    return cols[0] if cols else None
