from copy import deepcopy

import pandas as pd

from .schema import FIELDS


def field_counts(true_values: list[str], pred_values: list[str]) -> tuple[int, int, int]:
    pv = deepcopy(pred_values)
    tp = 0
    for value in true_values:
        if value in pv:
            pv.pop(pv.index(value))
            tp += 1

    tv = deepcopy(true_values)
    fp = 0
    for value in pred_values:
        if value in tv:
            tv.pop(tv.index(value))
        else:
            fp += 1

    pv = deepcopy(pred_values)
    fn = 0
    for value in true_values:
        if value in pv:
            pv.pop(pv.index(value))
        else:
            fn += 1

    return tp, fp, fn


def _prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def score(df_true: pd.DataFrame, df_pred: pd.DataFrame) -> pd.DataFrame:
    articles = df_true["pdf"].unique()
    agg = {col: dict(tp=0.0, fp=0.0, fn=0.0, precision=0.0, recall=0.0, f1=0.0) for col in FIELDS}

    for article in articles:
        true_rows = df_true[df_true["pdf"] == article]
        pred_rows = df_pred[df_pred["pdf"] == article]
        for col in FIELDS:
            tp, fp, fn = field_counts(
                list(true_rows[col].astype(str)), list(pred_rows[col].astype(str))
            )
            precision, recall, f1 = _prf(tp, fp, fn)
            cell = agg[col]
            cell["tp"] += tp
            cell["fp"] += fp
            cell["fn"] += fn
            cell["precision"] += precision
            cell["recall"] += recall
            cell["f1"] += f1

    n = len(articles)
    for col in FIELDS:
        for key in agg[col]:
            agg[col][key] /= n
    return pd.DataFrame(agg).T


def macro_f1(metrics: pd.DataFrame) -> float:
    return float(metrics["f1"].mean())
