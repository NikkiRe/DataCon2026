"""Row merge/dedup and dataframe post-processing."""

from __future__ import annotations

import pandas as pd

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.normalize import normalize_record
from chemx_extract.schemas import get_columns
from chemx_extract.smiles.resolver import canonicalize_smiles, resolve_smiles_fields

# Only deduplicate when a stable row key exists; cytotoxicity rows share materials.
_DEDUP_KEY_BY_DOMAIN: dict[str, list[str]] = {
    "oxazolidinone": ["compound_id"],
    "benzimidazole": ["compound_id"],
    "cocrystals": ["name_cocrystal", "ratio_cocrystal"],
    "complexes": ["compound_id"],
    "nanozymes": ["formula", "reaction_type"],
    "magnetic": ["name"],
    "seltox": ["np", "bacteria"],
    "synergy": ["NP", "bacteria", "drug"],
    "cytotoxicity": [],
}


def _dedup_key(row: dict, domain: str) -> str | None:
    fields = _DEDUP_KEY_BY_DOMAIN.get(domain, [])
    if not fields:
        return None
    parts: list[str] = []
    for field in fields:
        value = row.get(field)
        if value in (None, "", NOT_DETECTED):
            if domain == "cocrystals" and field == "ratio_cocrystal":
                continue
            return None
        parts.append(f"{field}:{value}")
    return "|".join(parts) if parts else None


def _merge_row_values(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value not in (None, "", NOT_DETECTED):
            merged[key] = value
        elif key not in merged:
            merged[key] = NOT_DETECTED
    return merged


def merge_rows(rows: list[dict], domain: str) -> list[dict]:
    """Merge duplicate rows when domain defines a stable key."""
    columns = get_columns(domain)
    merged_by_key: dict[str, dict] = {}
    unkeyed: list[dict] = []

    for row in rows:
        normalized = {col: row.get(col, NOT_DETECTED) for col in columns}
        key = _dedup_key(normalized, domain)
        if key is None:
            unkeyed.append(normalized)
            continue
        if key in merged_by_key:
            merged_by_key[key] = _merge_row_values(merged_by_key[key], normalized)
        else:
            merged_by_key[key] = normalized

    return list(merged_by_key.values()) + unkeyed


def postprocess_dataframe(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Normalize values to ChemX format, canonicalize SMILES, fill missing."""
    if df.empty:
        return pd.DataFrame(columns=get_columns(domain))

    columns = get_columns(domain)
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = NOT_DETECTED
    out = out[columns]

    records = []
    for row in out.to_dict(orient="records"):
        row = normalize_record(row, domain)
        row = resolve_smiles_fields(row, domain)
        for col in columns:
            if col in row and row[col] not in (None, "", NOT_DETECTED):
                # Re-canonicalize SMILES after serialize
                from chemx_extract.schemas import SMILES_COLS

                if col in SMILES_COLS.get(domain, []):
                    row[col] = canonicalize_smiles(str(row[col]))
        records.append(row)

    result = pd.DataFrame(records, columns=columns)
    result = result.fillna(NOT_DETECTED)
    result = result.replace("", NOT_DETECTED)
    return result.drop_duplicates().reset_index(drop=True)
