#!/usr/bin/env python3
"""Batch-extract all PDFs in a directory and concatenate predictions into one CSV."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.pipeline import extract_from_pdf  # noqa: E402
from chemx_extract.schemas import DATASETS  # noqa: E402


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.1f}m"


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
    parser.add_argument(
        "--delay",
        type=int,
        default=0,
        help="Seconds to wait between PDFs (rate-limit safety).",
    )
    parser.add_argument(
        "--mode",
        choices=("fast", "pdf", "staged"),
        default="fast",
        help="Pipeline mode (default: fast).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification pass.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip PDFs already present in output CSV.",
    )
    args = parser.parse_args()

    pdf_dir = args.pdf_dir.expanduser().resolve()
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}", file=sys.stderr)
        sys.exit(1)

    existing_pdfs: set[str] = set()
    if args.resume and args.output.is_file():
        prev = pd.read_csv(args.output)
        if "pdf" in prev.columns:
            existing_pdfs = set(prev["pdf"].astype(str))

    frames: list[pd.DataFrame] = []
    if args.resume and args.output.is_file() and existing_pdfs:
        frames.append(pd.read_csv(args.output))

    to_run: list[Path] = []
    for pdf in pdfs:
        stem = pdf.stem.removesuffix(".pdf")
        if args.resume and stem in existing_pdfs:
            continue
        to_run.append(pdf)

    total = len(to_run)
    batch_start = time.monotonic()
    print(f"[{_ts()}] Batch start: {total} PDF(s), mode={args.mode}, domain={args.domain}")
    if total == 0:
        print(f"[{_ts()}] Nothing to do (all PDFs already in output).")
        if args.output.is_file():
            print(f"Existing output: {args.output}")
        return

    for done, pdf in enumerate(to_run, start=1):
        stem = pdf.stem.removesuffix(".pdf")
        if args.delay > 0 and done > 1:
            print(f"[{_ts()}] Waiting {args.delay}s (rate-limit)...")
            time.sleep(args.delay)

        elapsed = time.monotonic() - batch_start
        avg = elapsed / (done - 1) if done > 1 else None
        eta = _fmt_duration(avg * (total - done + 1)) if avg else "?"
        print(
            f"[{_ts()}] [{done}/{total}] {pdf.name}  "
            f"(elapsed {_fmt_duration(elapsed)}, ETA ~{eta})",
            flush=True,
        )

        t0 = time.monotonic()
        work_dir = args.work_root / stem
        df = extract_from_pdf(
            pdf,
            args.domain,
            work_dir=work_dir,
            mode=args.mode,
            verify=not args.no_verify,
        )
        dt = time.monotonic() - t0
        frames.append(df)
        print(f"[{_ts()}]   done in {_fmt_duration(dt)} → {len(df)} row(s)", flush=True)

        combined = pd.concat(frames, ignore_index=True).drop_duplicates()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(args.output, index=False)
        print(f"[{_ts()}]   saved {len(combined)} total rows → {args.output.name}", flush=True)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    total_time = time.monotonic() - batch_start
    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output, index=False)
    print(
        f"[{_ts()}] Batch complete in {_fmt_duration(total_time)}: "
        f"{len(combined)} row(s) → {args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
