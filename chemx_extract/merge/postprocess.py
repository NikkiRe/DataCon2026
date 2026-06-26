"""Row merge/dedup and dataframe post-processing."""

from __future__ import annotations

import pandas as pd

from chemx_extract.config import NOT_DETECTED
from chemx_extract.schemas import NUMERIC_COLUMNS, SMILES_COLS, get_columns
from chemx_extract.smiles.resolver import canonicalize_smiles, resolve_smiles_fields

DEDUP_KEY_FIELDS = ["compound_id", "name_cocrystal", "material", "NP", "formula"]


def convert_comma(value: object) -> str:
    """Convert decimal commas to dots for numeric comparison."""
    if value in (None, "", NOT_DETECTED):
        return NOT_DETECTED
    try:
        return str(value).replace(",", ".")
    except Exception:  # noqa: BLE001
        return str(value)


def _dedup_key(row: dict) -> str | None:
    for field in DEDUP_KEY_FIELDS:
        if field not in row:
            continue
        value = row.get(field)
        if value not in (None, "", NOT_DETECTED):
            return f"{field}:{value}"
    return None


def _merge_row_values(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value not in (None, "", NOT_DETECTED):
            merged[key] = value
        elif key not in merged:
            merged[key] = NOT_DETECTED
    return merged


def merge_rows(rows: list[dict], domain: str) -> list[dict]:
    """Merge duplicate rows, deduplicating by the first available key field."""
    columns = get_columns(domain)
    merged_by_key: dict[str, dict] = {}
    unkeyed: list[dict] = []

    for row in rows:
        normalized = {col: row.get(col, NOT_DETECTED) for col in columns}
        key = _dedup_key(normalized)
        if key is None:
            unkeyed.append(normalized)
            continue
        if key in merged_by_key:
            merged_by_key[key] = _merge_row_values(merged_by_key[key], normalized)
        else:
            merged_by_key[key] = normalized

    return list(merged_by_key.values()) + unkeyed


def postprocess_dataframe(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Canonicalize SMILES, fix numeric commas, normalize target_relation, fill NOT_DETECTED."""
    if df.empty:
        return pd.DataFrame(columns=get_columns(domain))

    out = df.copy()
    columns = get_columns(domain)

    for col in columns:
        if col not in out.columns:
            out[col] = NOT_DETECTED

    out = out[columns]

    for col in NUMERIC_COLUMNS.get(domain, []):
        if col in out.columns:
            out[col] = out[col].apply(convert_comma)

    if domain in ("oxazolidinone", "benzimidazole") and "target_relation" in out.columns:
        out["target_relation"] = out["target_relation"].apply(
            lambda x: "=" if x == "'='" else x
        )

    for col in SMILES_COLS.get(domain, []):
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: canonicalize_smiles(str(x)) if x not in (None, "", NOT_DETECTED) else NOT_DETECTED
            )

    records = [resolve_smiles_fields(row, domain) for row in out.to_dict(orient="records")]
    out = pd.DataFrame(records, columns=columns)
    out = out.fillna(NOT_DETECTED)
    out = out.replace("", NOT_DETECTED)
    return out
