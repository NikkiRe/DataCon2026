import pandas as pd

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.postprocess import merge_rows, postprocess_dataframe
from chemx_extract.smiles.resolver import canonicalize_smiles


def test_merge_rows_deduplicates_by_compound_id():
    rows = [
        {
            "compound_id": "CMP1",
            "smiles": "CCO",
            "target_type": NOT_DETECTED,
            "target_relation": NOT_DETECTED,
            "target_value": "1,0",
            "target_units": "uM",
            "bacteria": "E. coli",
        },
        {
            "compound_id": "CMP1",
            "smiles": NOT_DETECTED,
            "target_type": "MIC",
            "target_relation": "=",
            "target_value": "2.0",
            "target_units": "uM",
            "bacteria": NOT_DETECTED,
        },
    ]
    merged = merge_rows(rows, "oxazolidinone")
    assert len(merged) == 1
    assert merged[0]["smiles"] == "CCO"
    assert merged[0]["target_type"] == "MIC"
    assert merged[0]["target_value"] == "2.0"


def test_merge_rows_keeps_unkeyed_rows():
    rows = [
        {
            "compound_id": NOT_DETECTED,
            "smiles": "CCO",
            "target_type": NOT_DETECTED,
            "target_relation": NOT_DETECTED,
            "target_value": NOT_DETECTED,
            "target_units": NOT_DETECTED,
            "bacteria": NOT_DETECTED,
        },
        {
            "compound_id": NOT_DETECTED,
            "smiles": "CCC",
            "target_type": NOT_DETECTED,
            "target_relation": NOT_DETECTED,
            "target_value": NOT_DETECTED,
            "target_units": NOT_DETECTED,
            "bacteria": NOT_DETECTED,
        },
    ]
    merged = merge_rows(rows, "oxazolidinone")
    assert len(merged) == 2


def test_postprocess_canonicalizes_smiles_and_fixes_numeric_commas():
    df = pd.DataFrame(
        [
            {
                "compound_id": "A",
                "smiles": "C(C)O",
                "target_type": NOT_DETECTED,
                "target_relation": NOT_DETECTED,
                "target_value": "1,5",
                "target_units": NOT_DETECTED,
                "bacteria": NOT_DETECTED,
            }
        ]
    )
    out = postprocess_dataframe(df, "oxazolidinone")
    assert out.loc[0, "smiles"] == canonicalize_smiles("C(C)O")
    assert out.loc[0, "target_value"] == "1.5"


def test_postprocess_fixes_target_relation():
    df = pd.DataFrame(
        [
            {
                "compound_id": "A",
                "smiles": NOT_DETECTED,
                "target_type": NOT_DETECTED,
                "target_relation": "'='",
                "target_value": NOT_DETECTED,
                "target_units": NOT_DETECTED,
                "bacteria": NOT_DETECTED,
            }
        ]
    )
    out = postprocess_dataframe(df, "oxazolidinone")
    assert out.loc[0, "target_relation"] == "="


def test_postprocess_fills_not_detected():
    df = pd.DataFrame(
        [
            {
                "compound_id": "A",
                "smiles": "",
                "target_type": None,
                "target_relation": NOT_DETECTED,
                "target_value": NOT_DETECTED,
                "target_units": NOT_DETECTED,
                "bacteria": NOT_DETECTED,
            }
        ]
    )
    out = postprocess_dataframe(df, "oxazolidinone")
    assert out.loc[0, "smiles"] == NOT_DETECTED
    assert out.loc[0, "target_type"] == NOT_DETECTED
