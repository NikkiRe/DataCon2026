"""Protect table-extract fields from verify regressions."""

from __future__ import annotations

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.normalize import normalize_record
from chemx_extract.merge.postprocess import merge_rows
from chemx_extract.merge.serialize import is_missing

_GUARDED_FIELDS = ("photostability_change", "ratio_cocrystal", "name_drug", "name_coformer", "name_cocrystal")


def _cocrystal_key(row: dict) -> str | None:
    name = row.get("name_cocrystal")
    if is_missing(name):
        return None
    return str(name).strip().upper()


def should_skip_verify(
    table_rows: list[dict],
    combined_rows: list[dict],
    domain: str,
) -> bool:
    """Skip verify LLM when table extract already agrees with deduped text rows."""
    if domain != "cocrystals" or not table_rows or not combined_rows:
        return False

    table_norm = [normalize_record(r, domain) for r in table_rows]
    combined_norm = [normalize_record(r, domain) for r in combined_rows]
    merged = merge_rows(combined_norm, domain)

    table_by_key = {_cocrystal_key(r): r for r in table_norm if _cocrystal_key(r)}
    if not table_by_key:
        return False

    merged_by_key = {_cocrystal_key(r): r for r in merged if _cocrystal_key(r)}

    if set(table_by_key) != set(merged_by_key):
        return False

    for key, trow in table_by_key.items():
        mrow = merged_by_key[key]
        for field in _GUARDED_FIELDS:
            tv, cv = trow.get(field), mrow.get(field)
            if not is_missing(tv) and not is_missing(cv) and tv != cv:
                return False
    return True


def guard_verify_output(
    verified: list[dict],
    table_rows: list[dict],
    before_verify: list[dict],
    domain: str,
) -> tuple[list[dict], list[str]]:
    """Restore table-anchored fields when verify changed them incorrectly."""
    if domain != "cocrystals" or not verified:
        return verified, []

    table_norm = [normalize_record(r, domain) for r in table_rows]
    table_by_key = {_cocrystal_key(r): r for r in table_norm if _cocrystal_key(r)}

    before_by_key = {_cocrystal_key(r): r for r in before_verify if _cocrystal_key(r)}

    notes: list[str] = []
    guarded: list[dict] = []

    for row in verified:
        updated = dict(row)
        key = _cocrystal_key(updated)
        if not key:
            guarded.append(updated)
            continue

        anchor = table_by_key.get(key) or before_by_key.get(key)
        if not anchor:
            guarded.append(updated)
            continue

        for field in _GUARDED_FIELDS:
            anchor_val = anchor.get(field)
            current = updated.get(field)
            if is_missing(anchor_val) or anchor_val == current:
                continue
            notes.append(
                f"  {updated.get('name_cocrystal')}: verify changed {field} "
                f"{current!r} → restore {anchor_val!r} (table/text anchor)"
            )
            updated[field] = anchor_val
        guarded.append(updated)

    return guarded, notes
