#!/usr/bin/env python3
"""CLI entry point: extract structured data from a PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.config import OUTPUT_DIR  # noqa: E402
from chemx_extract.pipeline import extract_from_pdf  # noqa: E402
from chemx_extract.schemas import DATASETS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured chemistry data from a PDF.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        required=True,
        help="Path to the input PDF file.",
    )
    parser.add_argument(
        "--domain",
        choices=DATASETS,
        required=True,
        help="ChemX domain key (e.g. cocrystals).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: out/<pdf_stem>.csv).",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Working directory for preprocessing artifacts (default: out/<pdf_stem>/).",
    )
    parser.add_argument(
        "--mode",
        choices=("fast", "pdf", "staged"),
        default="fast",
        help="Pipeline mode: fast (default), pdf (1-call), staged (legacy).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip second-pass verification (faster, lower quality).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path = args.pdf.resolve()

    if not pdf_path.is_file():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    output_path = args.output
    if output_path is None:
        output_path = OUTPUT_DIR / f"{pdf_path.stem}.csv"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir = args.work_dir.resolve() if args.work_dir else None

    df = extract_from_pdf(
        pdf_path,
        args.domain,
        work_dir=work_dir,
        mode=args.mode,
        verify=not args.no_verify,
    )
    df.to_csv(output_path, index=False)

    print(f"Wrote {len(df)} row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
