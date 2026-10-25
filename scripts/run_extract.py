import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from nanozx import predict
from nanozx.schema import FIELDS

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "pdfs"
MANUAL_DIR = ROOT / "data" / "manual"
OUT = ROOT / "data" / "cache" / "preds.csv"


def stems() -> list[str]:
    return sorted(p.stem for p in PDF_DIR.glob("*.pdf"))


def manual_stems() -> list[str]:
    return sorted(p.stem for p in MANUAL_DIR.glob("*.json"))


def records_api(stem: str) -> list[dict]:
    from nanozx import extract

    return extract.extract_records(PDF_DIR / f"{stem}.pdf")


def records_manual(stem: str) -> list[dict]:
    path = MANUAL_DIR / f"{stem}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("samples", [])


def records_text(stem: str) -> list[dict]:
    import fitz

    from nanozx import extract

    doc = fitz.open(PDF_DIR / f"{stem}.pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return extract.extract_records_from_text(text[:16000])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["api", "text", "manual"], default="manual")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=70.0)
    args = parser.parse_args()

    getter = {"api": records_api, "text": records_text, "manual": records_manual}[args.source]
    throttle = args.source in ("api", "text")

    if args.source == "manual":
        targets = manual_stems()
        if not targets:
            sys.exit(f"no JSON files in {MANUAL_DIR}")
    else:
        targets = stems()
        if not targets:
            sys.exit(f"no PDFs in {PDF_DIR}: run scripts/download_pdfs.py first")
    if args.limit:
        targets = targets[: args.limit]

    frames = []
    for index, stem in enumerate(targets):
        try:
            records = getter(stem)
        except Exception as error:
            print(f"[err]  {stem}: {type(error).__name__}: {str(error)[:120]}")
            records = []
        if records:
            frames.append(predict.records_to_frame(records, stem))
            print(f"[ok]   {stem}: {len(records)} records", flush=True)
        else:
            print(f"[skip] {stem}: no records", flush=True)
        if throttle and index < len(targets) - 1:
            time.sleep(args.sleep)

    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FIELDS + ["pdf"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    print(f"\nwrote {len(result)} prediction rows for {result['pdf'].nunique()} articles -> {OUT}")


if __name__ == "__main__":
    main()
