import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from nanozx import dataset, metric
from nanozx.schema import FIELDS

PREDS = Path(__file__).resolve().parents[1] / "data" / "cache" / "preds.csv"


def main() -> None:
    gt = dataset.ground_truth()
    preds = pd.read_csv(PREDS, dtype=str).fillna("nan")
    preds["pdf"] = preds["pdf"].str.lower()

    covered = sorted(set(gt["pdf"]) & set(preds["pdf"]))
    print(f"GT articles: {gt['pdf'].nunique()} | predicted: {preds['pdf'].nunique()} | covered: {len(covered)}")

    full = metric.score(gt, preds)
    print(f"\nfull-set macro-F1 (39 articles, missing scored 0): {metric.macro_f1(full):.4f}")

    gt_cov = gt[gt["pdf"].isin(covered)]
    cov = metric.score(gt_cov, preds)
    print(f"covered-only macro-F1 ({len(covered)} articles): {metric.macro_f1(cov):.4f}")

    print("\nper-field f1 (covered-only):")
    for field in FIELDS:
        print(f"  {field:14} {cov.loc[field, 'f1']:.3f}")


if __name__ == "__main__":
    main()
