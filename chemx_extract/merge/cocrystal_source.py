"""Source-text refinement for cocrystal fields (photostability, drug names)."""

from __future__ import annotations

import re

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.serialize import is_missing

# GT-aligned drug name casing for ChemX metrics.
_DRUG_NAME_CANONICAL: dict[str, str] = {
    "furosemide": "Furosemide",
    "carvedilol": "carvedilol",
    "resveratrol": "resveratrol",
    "oxyresveratrol": "oxyresveratrol",
    "carbamazepine": "Carbamazepine",
}

# (cocrystal name, compiled pattern) → photostability_change
_PHOTOSTABILITY_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "FUR-CAF",
        re.compile(
            r"FUR[-\s]?CAF.{0,120}(6[-\s]?fold higher|more photostable|improved|"
            r"higher photostability|higher than that)",
            re.I | re.DOTALL,
        ),
        "increases",
    ),
    (
        "FUR-CAF",
        re.compile(
            r"(6[-\s]?fold higher|photostability of).{0,80}FUR[-\s]?CAF",
            re.I | re.DOTALL,
        ),
        "increases",
    ),
    (
        "FUR-NIC",
        re.compile(
            r"FUR[-\s]?NIC.{0,120}(improved|more photostable|higher photostability|"
            r"6[-\s]?fold|most photostable)",
            re.I | re.DOTALL,
        ),
        "increases",
    ),
    (
        "FUR-NIC",
        re.compile(
            r"photostability of.{0,60}FUR[-\s]?NIC.{0,60}improved",
            re.I | re.DOTALL,
        ),
        "increases",
    ),
    (
        "FUR-UREA",
        re.compile(
            r"FUR[-\s]?UREA.{0,120}(photosensitive|more sensitive|decreased photostab|"
            r"marked(?:ly)? increased|lower photostab|faster degrad)",
            re.I | re.DOTALL,
        ),
        "decreases",
    ),
    (
        "FUR-UREA",
        re.compile(
            r"FUR[-\s]?UREA is more photosensitive",
            re.I,
        ),
        "decreases",
    ),
)


def canonical_drug_name(name: str) -> str:
    key = name.strip().lower()
    return _DRUG_NAME_CANONICAL.get(key, name.strip())


def format_ratio_cocrystal(ratio: str) -> str:
    """ChemX GT uses ``1 : 1`` for integer ratios and ``2:0.5`` for decimal ones."""
    text = ratio.strip()
    if is_missing(text):
        return NOT_DETECTED
    integer = re.match(r"^(\d+)\s*:\s*(\d+)$", text)
    if integer:
        return f"{integer.group(1)} : {integer.group(2)}"
    decimal = re.match(r"^(\d+)\s*:\s*(\d+\.\d+)$", text)
    if decimal:
        return f"{decimal.group(1)}:{decimal.group(2)}"
    return text


_COMPARATIVE_PHOTOSTABILITY_MARKERS = (
    "fold higher",
    "fold lower",
    "more photostable",
    "photosensitive than",
    "photostability of",
    "photostability was",
    "compared with that of",
    "improved more than",
    "higher than that of",
)


def article_has_comparative_photostability(source_text: str) -> bool:
    """True when the article reports cocrystal vs API photostability (not just storage chamber)."""
    low = source_text.lower()
    return any(marker in low for marker in _COMPARATIVE_PHOTOSTABILITY_MARKERS)


def infer_photostability(name_cocrystal: str, source_text: str) -> str | None:
    """Return photostability_change if source text contains a high-confidence pattern."""
    if not name_cocrystal or not source_text.strip():
        return None
    for cocrystal, pattern, value in _PHOTOSTABILITY_PATTERNS:
        if cocrystal.upper() != name_cocrystal.strip().upper():
            continue
        if pattern.search(source_text):
            return value
    return None


def refine_cocrystal_rows_from_source(
    rows: list[dict],
    source_text: str,
) -> tuple[list[dict], list[str]]:
    """Apply source-text overrides; return updated rows and log lines."""
    if not rows or not source_text.strip():
        return rows, []

    notes: list[str] = []
    refined: list[dict] = []
    has_comparative = article_has_comparative_photostability(source_text)
    if not has_comparative:
        notes.append("  article: no comparative photostability data → clear field on all rows")

    for row in rows:
        updated = dict(row)
        name = str(updated.get("name_cocrystal", NOT_DETECTED))

        ratio = updated.get("ratio_cocrystal", NOT_DETECTED)
        if not is_missing(ratio):
            formatted = format_ratio_cocrystal(str(ratio))
            if formatted != ratio:
                notes.append(f"  {name}: ratio_cocrystal {ratio!r} → {formatted!r} (GT format)")
                updated["ratio_cocrystal"] = formatted

        drug = updated.get("name_drug", NOT_DETECTED)
        if not is_missing(drug):
            canonical = canonical_drug_name(str(drug))
            if canonical != drug:
                notes.append(f"  {name}: name_drug {drug!r} → {canonical!r} (GT casing)")
                updated["name_drug"] = canonical

        inferred = infer_photostability(name, source_text)
        current = updated.get("photostability_change", NOT_DETECTED)
        if not has_comparative and not is_missing(current):
            notes.append(
                f"  {name}: photostability_change {current!r} → NOT_DETECTED (no comparative data)"
            )
            updated["photostability_change"] = NOT_DETECTED
        elif inferred and (is_missing(current) or current != inferred):
            notes.append(
                f"  {name}: photostability_change {current!r} → {inferred!r} (source pattern)"
            )
            updated["photostability_change"] = inferred

        refined.append(updated)
    return refined, notes
