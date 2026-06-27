"""ChemX-exact value serialization (ported from task1/nanozx/serialize.py)."""

from __future__ import annotations

import math
import re

from chemx_extract.config import NOT_DETECTED
from chemx_extract.schemas import NUMERIC_COLUMNS

_MISSING_TOKENS = frozenset(
    {"", "NOT_DETECTED", "NAN", "NONE", "N/A", "NA", "ND", "-", "--", "NULL"}
)

# Nanozymes GT uses literal "nan" for missing numerics; other domains use NOT_DETECTED.
_NAN_NUMERIC_DOMAINS = frozenset({"nanozymes"})

# Stored as strings in GT but represent numbers (nanozymes length/width/depth).
_RAW_NUMERIC_FIELDS: dict[str, frozenset[str]] = {
    "nanozymes": frozenset({"length", "width", "depth"}),
}


def is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        cleaned = value.strip().strip("'\"")
        if cleaned.upper() in _MISSING_TOKENS:
            return True
    return False


def numeric_missing_token(domain: str) -> str:
    return "nan" if domain in _NAN_NUMERIC_DOMAINS else NOT_DETECTED


def _as_number(value: object) -> float:
    if isinstance(value, str):
        value = value.strip().strip("'\"").replace(",", ".")
    return float(value)


def serialize_value(field: str, value: object, domain: str) -> str:
    """Serialize one field value to the exact string form expected by ChemX metrics."""
    numeric_cols = set(NUMERIC_COLUMNS.get(domain, []))
    raw_numeric = _RAW_NUMERIC_FIELDS.get(domain, frozenset())
    numeric = field in numeric_cols or field in raw_numeric

    if is_missing(value):
        return numeric_missing_token(domain) if numeric else NOT_DETECTED

    if field in numeric_cols:
        try:
            number = _as_number(value)
            # Match pandas float64 → str convention used in ChemX GT.
            return str(number)
        except (ValueError, TypeError):
            return numeric_missing_token(domain)

    if field in raw_numeric:
        try:
            number = _as_number(value)
            return str(int(number)) if number.is_integer() else str(number)
        except (ValueError, TypeError):
            return str(value).strip().strip("'\"")

    text = str(value).strip().strip("'\"")
    text = re.sub(r"[–—−]", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text
