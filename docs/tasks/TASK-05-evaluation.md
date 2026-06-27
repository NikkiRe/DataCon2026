# TASK-05 — Evaluation

**Owner files:** `chemx_extract/eval/__init__.py`, `chemx_extract/eval/metrics.py`

**Depends on:** TASK-01

## Goal

ChemX-compatible Macro-F1 computation (port of `LLM/src/metric_calc.py`).

## API

```python
def load_ground_truth(domain: str) -> pd.DataFrame: ...
def compute_metrics(df_true: pd.DataFrame, df_pred: pd.DataFrame, domain: str) -> pd.DataFrame: ...
def macro_f1(metrics_df: pd.DataFrame) -> float: ...
def evaluate_predictions(domain: str, predictions_path: Path) -> tuple[pd.DataFrame, float]: ...
```

## Rules (must match ChemX)

- Per-article multiset TP/FP/FN per column
- Average metrics across articles
- `prepare_dataset` preprocessing on GT
- Predictions need `pdf` column (+ schema columns)
- magnetic/seltox: filter articles to `MAGNETIC_ARTICLES` / `SELTOX_ARTICLES`

## Acceptance tests

```bash
pytest tests/test_eval.py -v
```

Unit test `calc_metrics` with toy true/pred DataFrames.

## Out of scope

CLI wrapper (TASK-06).
