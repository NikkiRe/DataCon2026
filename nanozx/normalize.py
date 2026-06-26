from .schema import ACTIVITY_VOCAB, FIELDS, SYNGONY_VOCAB
from .serialize import is_missing, serialize_value

_VOCAB = {"activity": ACTIVITY_VOCAB, "syngony": SYNGONY_VOCAB}


def _snap(value: str, vocab: set[str]) -> str:
    low = value.strip().lower()
    for canonical in vocab:
        if low == canonical:
            return canonical
    for canonical in vocab:
        if canonical in low:
            return canonical
    return value


def normalize_record(record: dict) -> dict:
    out = {}
    for field in FIELDS:
        value = record.get(field)
        if field in _VOCAB and not is_missing(value):
            value = _snap(str(value), _VOCAB[field])
        out[field] = serialize_value(field, value)
    return out
