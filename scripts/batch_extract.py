#!/usr/bin/env python3
"""Batch-extract all PDFs in a directory and concatenate predictions into one CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.pipeline import extract_from_pdf  # noqa: E402
from chemx_extract.schemas import DATASETS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch PDF extraction for ChemX eval.")
    parser.add_argument("--pdf-dir", type=Path, required=True, help="Directory with PDF files.")
    parser.add_argument("--domain", type=str, choices=DATASETS, required=True)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=PROJECT_ROOT / "out" / "predictions.csv",
        help="Combined predictions CSV.",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=PROJECT_ROOT / "out" / "work",
        help="Root directory for per-PDF work dirs.",
    )
    args = parser.parse_args()

    pdf_dir = args.pdf_dir.expanduser().resolve()
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    frames: list[pd.DataFrame] = []
    for pdf in pdfs:
        print(f"Extracting {pdf.name}...")
        work_dir = args.work_root / pdf.stem
        df = extract_from_pdf(pdf, args.domain, work_dir=work_dir)
        frames.append(df)
        print(f"  -> {len(df)} row(s)")

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output, index=False)
    print(f"Wrote {len(combined)} total row(s) to {args.output}")


if __name__ == "__main__":
    main()
