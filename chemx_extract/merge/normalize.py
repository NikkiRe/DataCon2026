"""Domain-specific canonicalization before serialization."""

from __future__ import annotations

import re

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.cocrystal_source import canonical_drug_name, format_ratio_cocrystal
from chemx_extract.merge.serialize import is_missing, serialize_value
from chemx_extract.schemas import get_columns

_PHOTOSTABILITY_VALUES = ("increases", "decreases", "decrease", "does not change")

# Nanosponge cocrystal naming (Dhakar2019 GT pattern).
_NANOSPONGE_NAME_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"resveratrol.*nanosponge|res[-\s]?loaded\s*ns|res[-\s]?ns\b", re.I), "RES-NS"),
    (re.compile(r"oxyresveratrol.*nanosponge|oxy[-\s]?loaded\s*ns|oxy[-\s]?ns\b", re.I), "OXY-NS"),
)
_NANOSPONGE_NAMES = frozenset({"RES-NS", "OXY-NS"})

_ACTIVITY_VOCAB = frozenset({"peroxidase", "oxidase", "catalase", "laccase"})
_SYNGONY_VOCAB = frozenset(
    {
        "cubic",
        "hexagonal",
        "tetragonal",
        "monoclinic",
        "orthorhombic",
        "trigonal",
        "amorphous",
        "triclinic",
    }
)


def _snap_vocab(value: str, vocab: frozenset[str]) -> str:
    low = value.strip().lower()
    for canonical in vocab:
        if low == canonical:
            return canonical
    for canonical in vocab:
        if canonical in low:
            return canonical
    return value


def _normalize_photostability(value: str) -> str:
    low = value.strip().lower()
    if "does not change" in low or "unchanged" in low or "no change" in low:
        return "does not change"
    if any(
        token in low
        for token in (
            "protection",
            "enhanced",
            "enhance",
            "improved",
            "improve",
            "higher stability",
            "more stable",
            "slower degrad",
        )
    ) or ("increase" in low and "decrease" not in low):
        return "increases"
    if any(
        token in low
        for token in ("decrease", "degrad", "reduc", "worse", "lower stability", "faster degrad")
    ):
        return "decreases"
    return value.strip()


def _normalize_cocrystal_name(value: str) -> str:
    text = value.strip()
    for pattern, canonical in _NANOSPONGE_NAME_RULES:
        if pattern.search(text):
            return canonical
    return text


def _is_nanosponge_cocrystal(name_cocrystal: str, name_coformer: str) -> bool:
    if name_cocrystal in _NANOSPONGE_NAMES:
        return True
    combined = f"{name_cocrystal} {name_coformer}".lower()
    return "nanosponge" in combined or re.search(r"\bres[-\s]?ns\b|\boxy[-\s]?ns\b", combined, re.I)


def _normalize_coformer(value: str, name_cocrystal: str) -> str:
    text = value.strip()
    if _is_nanosponge_cocrystal(name_cocrystal, text):
        return "nanosponge"
    low = text.lower()
    if "nanosponge" in low or "cyclodextrin" in low and "sponge" in low:
        return "nanosponge"
    # ChemX GT uses lowercase coformer names (caffeine, urea, hydrochlorothiazide).
    return text.lower()


def _normalize_cocrystal_ratio(ratio: str, name_cocrystal: str, name_coformer: str) -> str:
    if _is_nanosponge_cocrystal(name_cocrystal, name_coformer):
        return NOT_DETECTED
    return format_ratio_cocrystal(ratio)


def _normalize_human_animal(value: str) -> str:
    low = value.strip().lower()
    if low in {"h", "human"}:
        return "H"
    if low in {"a", "animal"}:
        return "A"
    return value.strip()


def normalize_field(field: str, value: object, domain: str) -> str:
    if is_missing(value):
        return serialize_value(field, value, domain)

    text = str(value).strip()

    if domain == "cocrystals":
        if field == "name_cocrystal":
            text = _normalize_cocrystal_name(text)
        elif field == "photostability_change":
            text = _normalize_photostability(text)
        elif field == "name_drug":
            text = canonical_drug_name(text)
    elif domain == "cytotoxicity" and field == "human_animal":
        text = _normalize_human_animal(text)
    elif domain == "nanozymes":
        if field == "activity":
            text = _snap_vocab(text, _ACTIVITY_VOCAB)
        elif field == "syngony":
            text = _snap_vocab(text, _SYNGONY_VOCAB)

    if domain in ("oxazolidinone", "benzimidazole") and field == "target_relation":
        text = "=" if text == "'='" else text

    return serialize_value(field, text, domain)


def normalize_record(record: dict, domain: str) -> dict:
    columns = get_columns(domain)
    if domain != "cocrystals":
        return {col: normalize_field(col, record.get(col), domain) for col in columns}

    # Cocrystals: normalize name first, then coformer/ratio depend on it.
    name_raw = record.get("name_cocrystal", NOT_DETECTED)
    name = NOT_DETECTED if is_missing(name_raw) else _normalize_cocrystal_name(str(name_raw).strip())

    coformer_raw = record.get("name_coformer", NOT_DETECTED)
    coformer = _normalize_coformer(str(coformer_raw).strip(), name) if not is_missing(coformer_raw) else NOT_DETECTED

    ratio_raw = record.get("ratio_cocrystal", NOT_DETECTED)
    ratio = (
        _normalize_cocrystal_ratio(str(ratio_raw).strip(), name, coformer)
        if not is_missing(ratio_raw)
        else NOT_DETECTED
    )

    out: dict[str, str] = {}
    for col in columns:
        if col == "name_cocrystal":
            out[col] = serialize_value(col, name, domain)
        elif col == "name_coformer":
            out[col] = serialize_value(col, coformer, domain)
        elif col == "ratio_cocrystal":
            out[col] = serialize_value(col, ratio, domain)
        else:
            out[col] = normalize_field(col, record.get(col), domain)

    if name == "RES-NS":
        drug = record.get("name_drug", NOT_DETECTED)
        if is_missing(drug) or "resveratrol" in str(drug).lower():
            out["name_drug"] = serialize_value("name_drug", "resveratrol", domain)
    elif name == "OXY-NS":
        drug = record.get("name_drug", NOT_DETECTED)
        if is_missing(drug) or "oxyresveratrol" in str(drug).lower():
            out["name_drug"] = serialize_value("name_drug", "oxyresveratrol", domain)
    elif not is_missing(out.get("name_drug")):
        out["name_drug"] = serialize_value(
            "name_drug", canonical_drug_name(str(out["name_drug"])), domain
        )

    return out
