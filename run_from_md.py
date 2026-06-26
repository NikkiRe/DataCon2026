"""
Запуск пайплайна от уже распарсенного markdown (пропускает OCR).
Usage:
    python run_from_md.py --md /tmp/chemx_Yutani2019/converted.md --work_dir /tmp/chemx_Yutani2019 --doi "10.3390/cryst9110553" --out results/Yutani2019.csv
"""
import argparse
import os
import glob
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", required=True)
    parser.add_argument("--work_dir", required=True)
    parser.add_argument("--doi", default="")
    parser.add_argument("--out", default="results/output.csv")
    parser.add_argument("--domain", default="cocrystals")
    args = parser.parse_args()

    from pipeline.domains import DOMAINS
    from pipeline.extractor import describe_images, inject_descriptions, extract_from_markdown, verify_records, enrich_smiles

    domain = DOMAINS[args.domain]()
    markdown = open(args.md, encoding="utf-8").read()

    image_paths = glob.glob(os.path.join(args.work_dir, "*.jpeg")) + \
                  glob.glob(os.path.join(args.work_dir, "*.png")) + \
                  glob.glob(os.path.join(args.work_dir, "*.jpg"))

    print(f"[2/5] Describing {len(image_paths)} images...")
    descriptions = describe_images(image_paths)

    print("[3/5] Injecting image descriptions...")
    described_md = inject_descriptions(markdown, descriptions)

    print("[4/5] Extracting structured data...")
    records = extract_from_markdown(described_md, domain)
    print(f"  → Extracted {len(records)} records")

    print("[5/5] Verifying and enriching SMILES...")
    records = verify_records(records, domain, described_md)
    for name_field, smiles_field in domain.smiles_pairs:
        from pipeline.smiles_lookup import enrich_smiles
        records = enrich_smiles(records, name_field, smiles_field)

    if args.doi:
        for r in records:
            r["doi"] = args.doi

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(args.out, index=False)
    print(f"\nСохранено {len(df)} записей → {args.out}")
    print(df.to_string())

if __name__ == "__main__":
    main()
