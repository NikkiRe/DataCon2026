"""Tests for ChemX value serialization and normalization."""

import pandas as pd

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.normalize import normalize_field, normalize_record
from chemx_extract.merge.postprocess import merge_rows, postprocess_dataframe
from chemx_extract.merge.serialize import is_missing, serialize_value


def test_is_missing_tokens():
    assert is_missing(None)
    assert is_missing("")
    assert is_missing("NOT_DETECTED")
    assert is_missing("'NOT_DETECTED'")
    assert not is_missing("Carbamazepine")


def test_serialize_cocrystals_string():
    assert serialize_value("name_drug", "  Carbamazepine  ", "cocrystals") == "Carbamazepine"
    assert serialize_value("name_drug", NOT_DETECTED, "cocrystals") == NOT_DETECTED


def test_serialize_cytotoxicity_numeric():
    assert serialize_value("time_hr", "24", "cytotoxicity") == "24.0"
    assert serialize_value("time_hr", "1,5", "cytotoxicity") == "1.5"
    assert serialize_value("time_hr", NOT_DETECTED, "cytotoxicity") == NOT_DETECTED


def test_serialize_nanozymes_numeric_missing():
    assert serialize_value("km_value", NOT_DETECTED, "nanozymes") == "nan"
    assert serialize_value("km_value", "0.217", "nanozymes") == "0.217"


def test_normalize_photostability():
    assert normalize_field("photostability_change", "UV protection increased", "cocrystals") == "increases"
    assert normalize_field("photostability_change", "degraded faster", "cocrystals") == "decreases"
    assert normalize_field("photostability_change", "unchanged", "cocrystals") == "does not change"
    assert normalize_field("photostability_change", "photostability enhanced", "cocrystals") == "increases"


def test_normalize_nanosponge_cocrystal():
    row = normalize_record(
        {
            "name_cocrystal": "Resveratrol-loaded nanosponge",
            "ratio_cocrystal": "1:6 w/w",
            "name_drug": "Resveratrol",
            "SMILES_drug": "NOT_DETECTED",
            "name_coformer": "Cyclodextrin-based nanosponge",
            "SMILES_coformer": "NOT_DETECTED",
            "photostability_change": "increases",
        },
        "cocrystals",
    )
    assert row["name_cocrystal"] == "RES-NS"
    assert row["ratio_cocrystal"] == NOT_DETECTED
    assert row["name_coformer"] == "nanosponge"
    assert row["name_drug"] == "resveratrol"


def test_merge_cocrystals_keeps_distinct_ratios():
    rows = [
        normalize_record(
            {
                "name_cocrystal": "FUR-CAF",
                "ratio_cocrystal": "1:1",
                "name_drug": "Furosemide",
                "SMILES_drug": NOT_DETECTED,
                "name_coformer": "Caffeine",
                "SMILES_coformer": NOT_DETECTED,
                "photostability_change": "increases",
            },
            "cocrystals",
        ),
        normalize_record(
            {
                "name_cocrystal": "FUR-NIC",
                "ratio_cocrystal": "1:1",
                "name_drug": "Furosemide",
                "SMILES_drug": NOT_DETECTED,
                "name_coformer": "Nicotinamide",
                "SMILES_coformer": NOT_DETECTED,
                "photostability_change": "increases",
            },
            "cocrystals",
        ),
    ]
    merged = merge_rows(rows, "cocrystals")
    assert len(merged) == 2


def test_merge_cocrystals_collapses_nanosponge_variants():
    rows = [
        normalize_record(
            {
                "name_cocrystal": "Resveratrol-loaded nanosponge",
                "ratio_cocrystal": "1:2 w/w",
                "name_drug": "Resveratrol",
                "SMILES_drug": NOT_DETECTED,
                "name_coformer": "nanosponge",
                "SMILES_coformer": NOT_DETECTED,
                "photostability_change": "increases",
            },
            "cocrystals",
        ),
        normalize_record(
            {
                "name_cocrystal": "RES-NS",
                "ratio_cocrystal": "1:6 w/w",
                "name_drug": "resveratrol",
                "SMILES_drug": NOT_DETECTED,
                "name_coformer": "nanosponge",
                "SMILES_coformer": NOT_DETECTED,
                "photostability_change": "increases",
            },
            "cocrystals",
        ),
    ]
    merged = merge_rows(rows, "cocrystals")
    assert len(merged) == 1
    assert merged[0]["name_cocrystal"] == "RES-NS"


def test_normalize_human_animal():
    assert normalize_field("human_animal", "Human", "cytotoxicity") == "H"
    assert normalize_field("human_animal", "animal", "cytotoxicity") == "A"


def test_postprocess_photostability_enum():
    df = pd.DataFrame(
        [
            {
                "name_cocrystal": "X",
                "ratio_cocrystal": NOT_DETECTED,
                "name_drug": "Drug",
                "SMILES_drug": NOT_DETECTED,
                "name_coformer": "Coformer",
                "SMILES_coformer": NOT_DETECTED,
                "photostability_change": "2-fold protection against UV",
            }
        ]
    )
    out = postprocess_dataframe(df, "cocrystals")
    assert out.loc[0, "photostability_change"] == "increases"


def test_normalize_record_all_columns():
    row = normalize_record({"name_drug": "A"}, "cocrystals")
    assert set(row.keys()) == {
        "name_cocrystal",
        "ratio_cocrystal",
        "name_drug",
        "SMILES_drug",
        "name_coformer",
        "SMILES_coformer",
        "photostability_change",
    }
