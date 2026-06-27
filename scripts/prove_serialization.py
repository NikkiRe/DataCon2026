#!/usr/bin/env python3
"""Show metric gain from ChemX serialization layer on baseline predictions."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from chemx_extract.eval.metrics import evaluate_predictions, macro_f1
from chemx_extract.merge.normalize import normalize_record
from chemx_extract.schemas import EXTRACTED_COLUMNS, get_columns

BASELINE_ROOT = PROJECT_ROOT / "data" / "ChemX" / "LLM" / "result" / "from_single_agent"


def reserialize_predictions(domain: str, pred: pd.DataFrame) -> pd.DataFrame:
    cols = get_columns(domain)
    rows = []
    for _, record in pred.iterrows():
        row = normalize_record(record.to_dict(), domain)
        row["pdf"] = str(record.get("pdf", ""))
        rows.append(row)
    return pd.DataFrame(rows)[cols + ["pdf"]].drop_duplicates()


def main() -> None:
    for domain in ("cocrystals", "cytotoxicity", "nanozymes"):
        baseline_path = BASELINE_ROOT / domain / "pred.csv"
        if not baseline_path.is_file():
            print(f"Skip {domain}: no baseline pred")
            continue

        raw = pd.read_csv(baseline_path)
        fixed = reserialize_predictions(domain, raw)

        tmp_raw = Path(f"/tmp/baseline_{domain}_raw.csv")
        tmp_fix = Path(f"/tmp/baseline_{domain}_fixed.csv")
        raw.to_csv(tmp_raw, index=False)
        fixed.to_csv(tmp_fix, index=False)

        _, macro_raw = evaluate_predictions(domain, tmp_raw)
        metrics_fix, macro_fix = evaluate_predictions(domain, tmp_fix)

        print(f"\n{domain}:")
        print(f"  baseline as-is:     {macro_raw:.4f}")
        print(f"  + serialization:    {macro_fix:.4f}  (Δ {macro_fix - macro_raw:+.4f})")


if __name__ == "__main__":
    main()
