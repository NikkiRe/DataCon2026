#!/usr/bin/env python3
"""CLI entry point: evaluate predictions against ChemX ground truth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.eval.metrics import evaluate_predictions  # noqa: E402
from chemx_extract.schemas import DATASETS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate extraction predictions against ChemX ground truth.",
    )
    parser.add_argument(
        "--domain",
        choices=DATASETS,
        required=True,
        help="ChemX domain key (e.g. cocrystals).",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="Path to predictions CSV (must include pdf column).",
    )
    parser.add_argument(
        "--save-metrics",
        type=Path,
        default=None,
        help="Optional path to save per-field metrics as CSV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    predictions_path = args.predictions.resolve()

    if not predictions_path.is_file():
        print(f"Error: predictions file not found: {predictions_path}", file=sys.stderr)
        return 1

    metrics_df, macro = evaluate_predictions(args.domain, predictions_path)

    print(f"Per-field metrics ({args.domain}):")
    print(metrics_df.to_string())
    print(f"\nMacro-F1: {macro:.4f}")

    if args.save_metrics:
        save_path = args.save_metrics.resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_df.to_csv(save_path)
        print(f"\nSaved metrics to {save_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
