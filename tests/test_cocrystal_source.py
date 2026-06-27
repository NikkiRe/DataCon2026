"""Tests for cocrystal source-text refinement."""

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.cocrystal_source import (
    canonical_drug_name,
    format_ratio_cocrystal,
    infer_photostability,
    refine_cocrystal_rows_from_source,
)

TERAOKA_SNIPPET = (
    "The photostability of three types of furosemide (FUR) cocrystal. "
    "bility of FUR-CAF was approximately 6-fold higher than that of FUR. "
    "FUR-UREA is more photosensitive than the photostability of those crystal forms. "
    "FUR-NIC was improved more than that of FUR-CAF."
)


def test_canonical_drug_name():
    assert canonical_drug_name("furosemide") == "Furosemide"
    assert canonical_drug_name("carvedilol") == "carvedilol"


def test_infer_photostability_fur_caf():
    assert infer_photostability("FUR-CAF", TERAOKA_SNIPPET) == "increases"
    assert infer_photostability("FUR-UREA", TERAOKA_SNIPPET) == "decreases"
    assert infer_photostability("FUR-NIC", TERAOKA_SNIPPET) == "increases"


def test_format_ratio_cocrystal():
    assert format_ratio_cocrystal("1:1") == "1 : 1"
    assert format_ratio_cocrystal("1 : 1") == "1 : 1"
    assert format_ratio_cocrystal("2:0.5") == "2:0.5"


def test_no_comparative_photostability_clears_field():
    solubility_only = (
        "Solubility enhancement of carvedilol using drug-drug cocrystallization. "
        "Samples stored in a photostability chamber for 30 days."
    )
    rows = [
        {
            "name_cocrystal": "CAR-HCT",
            "ratio_cocrystal": "2:0.5",
            "name_drug": "carvedilol",
            "SMILES_drug": NOT_DETECTED,
            "name_coformer": "hydrochlorothiazide",
            "SMILES_coformer": NOT_DETECTED,
            "photostability_change": "increases",
        }
    ]
    refined, notes = refine_cocrystal_rows_from_source(rows, solubility_only)
    assert refined[0]["photostability_change"] == NOT_DETECTED
    assert any("NOT_DETECTED" in n for n in notes)


def test_refine_overrides_wrong_photostability():
    rows = [
        {
            "name_cocrystal": "FUR-CAF",
            "ratio_cocrystal": "1:1",
            "name_drug": "furosemide",
            "SMILES_drug": NOT_DETECTED,
            "name_coformer": "caffeine",
            "SMILES_coformer": NOT_DETECTED,
            "photostability_change": "does not change",
        }
    ]
    refined, notes = refine_cocrystal_rows_from_source(rows, TERAOKA_SNIPPET)
    assert refined[0]["photostability_change"] == "increases"
    assert refined[0]["name_drug"] == "Furosemide"
    assert any("photostability" in n for n in notes)
