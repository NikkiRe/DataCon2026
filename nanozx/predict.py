import pandas as pd

from .normalize import normalize_record
from .schema import FIELDS


def records_to_frame(records: list[dict], pdf: str) -> pd.DataFrame:
    rows = []
    for record in records:
        row = normalize_record(record)
        row["pdf"] = pdf.lower()
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=FIELDS + ["pdf"])
    return pd.DataFrame(rows)[FIELDS + ["pdf"]].drop_duplicates()
