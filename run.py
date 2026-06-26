"""
CLI entry point.
Usage:
    python run.py --pdf paper.pdf --domain cocrystals --out results/output.csv
"""

import argparse
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="ChemX extraction pipeline")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--domain", default="cocrystals", choices=["cocrystals"])
    parser.add_argument("--out", default="results/output.csv")
    parser.add_argument("--doi", default="", help="DOI of the paper (for evaluation)")
    args = parser.parse_args()

    from pipeline.domains import DOMAINS
    from pipeline.extractor import run_pipeline

    domain_cls = DOMAINS[args.domain]
    domain = domain_cls()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    work_dir = f"/tmp/chemx_{os.path.basename(args.pdf).replace('.pdf', '')}"

    records = run_pipeline(args.pdf, domain, work_dir=work_dir)

    if args.doi:
        for r in records:
            r["doi"] = args.doi

    df = pd.DataFrame(records, columns=domain.output_columns + (["doi"] if args.doi else []))
    df.to_csv(args.out, index=False)
    print(f"\nSaved {len(df)} records → {args.out}")
    print(df.to_string())


if __name__ == "__main__":
    main()
