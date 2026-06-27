import pandas as pd

from chemx_extract.eval.metrics import calc_metrics, compute_metrics, macro_f1


def test_calc_metrics_perfect_match():
    cols = ["compound_id", "smiles"]
    df_true = pd.DataFrame(
        [
            {"compound_id": "A", "smiles": "CCO"},
            {"compound_id": "B", "smiles": "CCC"},
        ]
    )
    df_pred = df_true.copy()
    metrics = calc_metrics(df_true[cols], df_pred[cols])
    assert metrics.loc["compound_id", "f1"] == 1.0
    assert metrics.loc["smiles", "f1"] == 1.0


def test_calc_metrics_partial_match():
    cols = ["compound_id", "smiles"]
    df_true = pd.DataFrame([{"compound_id": "A", "smiles": "CCO"}])
    df_pred = pd.DataFrame([{"compound_id": "B", "smiles": "CCO"}])
    metrics = calc_metrics(df_true[cols], df_pred[cols])
    assert metrics.loc["compound_id", "tp"] == 0.0
    assert metrics.loc["compound_id", "fp"] == 1.0
    assert metrics.loc["compound_id", "fn"] == 1.0
    assert metrics.loc["smiles", "f1"] == 1.0


def test_calc_metrics_multiset_counts():
    cols = ["compound_id"]
    df_true = pd.DataFrame([{"compound_id": "A"}, {"compound_id": "A"}])
    df_pred = pd.DataFrame([{"compound_id": "A"}])
    metrics = calc_metrics(df_true[cols], df_pred[cols])
    assert metrics.loc["compound_id", "tp"] == 1.0
    assert metrics.loc["compound_id", "fn"] == 1.0


def test_macro_f1():
    metrics_df = pd.DataFrame({"f1": [1.0, 0.5, 0.0]})
    assert macro_f1(metrics_df) == 0.5


def test_compute_metrics_averages_per_article():
    cols = ["compound_id", "smiles"]
    df_true = pd.DataFrame(
        [
            {"compound_id": "A", "smiles": "CCO", "pdf": "a.pdf"},
            {"compound_id": "B", "smiles": "CCC", "pdf": "b.pdf"},
        ]
    )
    df_pred = pd.DataFrame(
        [
            {"compound_id": "A", "smiles": "CCO", "pdf": "a.pdf"},
            {"compound_id": "X", "smiles": "CCC", "pdf": "b.pdf"},
        ]
    )
    metrics = compute_metrics(df_true, df_pred, "oxazolidinone")
    assert metrics.loc["compound_id", "f1"] == 0.5
    assert metrics.loc["smiles", "f1"] == 1.0
