"""ChemX-compatible evaluation metrics (ported from ChemX LLM/src/metric_calc.py)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
from datasets import load_dataset
from rdkit import Chem
from rdkit import RDLogger

from chemx_extract.config import NOT_DETECTED
from chemx_extract.schemas import (
    DATASETS_IDS,
    EXTRACTED_COLUMNS,
    MAGNETIC_ARTICLES,
    NUMERIC_COLUMNS,
    SELTOX_ARTICLES,
    SMILES_COLS,
)

RDLogger.DisableLog("rdApp.*")


def convert_comma(value: object) -> str:
    try:
        return str(value).replace(",", ".")
    except Exception:  # noqa: BLE001
        return str(value)


def select_open_access(df_dataset: pd.DataFrame) -> pd.DataFrame:
    return df_dataset.loc[df_dataset["access"] == 1]


def _canonicalize_smiles_value(value: object) -> object:
    text = str(value)
    mol = Chem.MolFromSmiles(text)
    if mol is None:
        return value
    return Chem.MolToSmiles(mol)


def prepare_dataset(domain: str, df_dataset: pd.DataFrame | None = None) -> pd.DataFrame:
    """Prepare ground-truth rows: numeric cleanup, SMILES canonicalization, open access."""
    n_cols = NUMERIC_COLUMNS[domain]
    s_cols = SMILES_COLS[domain]

    if df_dataset is None:
        dataset_hf = load_dataset(DATASETS_IDS[domain])
        df_dataset = dataset_hf["train"].to_pandas()

    df = df_dataset.copy()

    for col in n_cols:
        df[col] = df[col].apply(convert_comma)

    if domain in ("oxazolidinone", "benzimidazole"):
        df["target_relation"] = df["target_relation"].apply(
            lambda x: "=" if x == "'='" else x
        )

    df = df.fillna(NOT_DETECTED)

    if domain in ("oxazolidinone", "benzimidazole", "cocrystals", "complexes"):
        for col in s_cols:
            df[col] = df[col].apply(_canonicalize_smiles_value)

    return select_open_access(df)


def prepare_predictions(df_pred: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Normalize prediction rows to ChemX comparison format."""
    cols = EXTRACTED_COLUMNS[domain]
    s_cols = SMILES_COLS[domain]
    n_cols = NUMERIC_COLUMNS[domain]

    df = df_pred.copy()
    for col in cols:
        if col not in df.columns:
            df[col] = NOT_DETECTED

    for col in n_cols:
        df[col] = df[col].apply(convert_comma)

    if domain in ("oxazolidinone", "benzimidazole"):
        df["target_relation"] = df["target_relation"].apply(
            lambda x: "=" if x == "'='" else x
        )

    if domain in ("oxazolidinone", "benzimidazole", "cocrystals", "complexes"):
        for col in s_cols:
            df[col] = df[col].apply(_canonicalize_smiles_value)

    if domain in ("cytotoxicity", "seltox", "synergy", "magnetic"):
        df["pdf"] = df["pdf"].apply(
            lambda x: x if str(x).endswith(".pdf") else f"{x}.pdf"
        )

    df = df.fillna(NOT_DETECTED)
    df["pdf"] = df["pdf"].apply(lambda x: str(x).lower())
    return df[cols + ["pdf"]].drop_duplicates()


def empty_metrics(cols: list[str]) -> pd.DataFrame:
    metrics: dict[str, dict[str, float]] = {}
    for col in cols:
        metrics[col] = {
            "tp": 0.0,
            "fp": 0.0,
            "fn": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }
    return pd.DataFrame(metrics).T


def calc_metrics(df_true: pd.DataFrame, df_pred: pd.DataFrame) -> pd.DataFrame:
    """Multiset TP/FP/FN metrics per column (ChemX logic)."""
    metrics: dict[str, dict[str, float]] = {}

    for col in df_true.columns:
        true_values = list(df_true[col].astype(str).values)
        pred_values = list(df_pred[col].astype(str).values)

        tv = deepcopy(true_values)
        pv = deepcopy(pred_values)
        tp = 0
        for val in tv:
            if val in pv:
                pv.pop(pv.index(val))
                tp += 1

        tv = deepcopy(true_values)
        pv = deepcopy(pred_values)
        fp = 0
        for val in pv:
            if val in tv:
                tv.pop(tv.index(val))
            else:
                fp += 1

        tv = deepcopy(true_values)
        pv = deepcopy(pred_values)
        fn = 0
        for val in tv:
            if val in pv:
                pv.pop(pv.index(val))
            else:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        metrics[col] = {
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return pd.DataFrame(metrics).T


def _article_list(domain: str, df_true: pd.DataFrame) -> list[str]:
    if domain == "magnetic":
        return [article.lower() for article in MAGNETIC_ARTICLES]
    if domain == "seltox":
        return [article.lower() for article in SELTOX_ARTICLES]
    return [str(pdf).lower() for pdf in df_true["pdf"].unique()]


def load_ground_truth(domain: str) -> pd.DataFrame:
    """Load and preprocess HuggingFace ground truth for a domain."""
    return prepare_dataset(domain)


def compute_metrics(
    df_true: pd.DataFrame,
    df_pred: pd.DataFrame,
    domain: str,
) -> pd.DataFrame:
    """Average per-article multiset metrics across all evaluation articles."""
    cols = EXTRACTED_COLUMNS[domain]
    df_true_prep = df_true.copy()
    for col in cols:
        if col not in df_true_prep.columns:
            df_true_prep[col] = NOT_DETECTED
    df_true_prep = df_true_prep.fillna(NOT_DETECTED)
    df_true_prep["pdf"] = df_true_prep["pdf"].apply(lambda x: str(x).lower())
    df_pred_prep = prepare_predictions(df_pred, domain)

    access_articles = _article_list(domain, df_true_prep)
    df_metrics = empty_metrics(cols)

    for article in access_articles:
        df_true_article = df_true_prep.loc[df_true_prep["pdf"] == article, cols]
        df_pred_article = df_pred_prep.loc[df_pred_prep["pdf"] == article, cols]
        df_metrics_article = calc_metrics(df_true_article, df_pred_article)
        df_metrics += df_metrics_article

    return df_metrics / len(access_articles)


def macro_f1(metrics_df: pd.DataFrame) -> float:
    """Macro-F1: mean F1 across all extracted columns."""
    return float(metrics_df["f1"].mean())


def evaluate_predictions(
    domain: str,
    predictions_path: Path,
) -> tuple[pd.DataFrame, float]:
    """Load ground truth and predictions, return metrics DataFrame and Macro-F1."""
    df_true = load_ground_truth(domain)
    df_pred = pd.read_csv(predictions_path)
    metrics_df = compute_metrics(df_true, df_pred, domain)
    return metrics_df, macro_f1(metrics_df)
