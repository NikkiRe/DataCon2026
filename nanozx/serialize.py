import math

from .schema import FLOAT_FIELDS, NUMERIC_MISSING, RAW_NUMERIC_FIELDS, STRING_MISSING

_MISSING_TOKENS = {"", "NOT_DETECTED", "NAN", "NONE", "N/A", "NA", "ND", "-", "--"}


def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().strip("'\"").upper() in _MISSING_TOKENS:
        return True
    return False


def _as_number(value) -> float:
    if isinstance(value, str):
        value = value.strip().strip("'\"").replace(",", ".")
    return float(value)


def serialize_value(field: str, value) -> str:
    numeric = field in FLOAT_FIELDS or field in RAW_NUMERIC_FIELDS
    if is_missing(value):
        return NUMERIC_MISSING if numeric else STRING_MISSING

    if field in FLOAT_FIELDS:
        try:
            return str(_as_number(value))
        except (ValueError, TypeError):
            return NUMERIC_MISSING

    if field in RAW_NUMERIC_FIELDS:
        try:
            number = _as_number(value)
        except (ValueError, TypeError):
            return str(value).strip().strip("'\"")
        return str(int(number)) if number.is_integer() else str(number)

    return str(value).strip().strip("'\"")
