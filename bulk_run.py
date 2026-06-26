"""
Скачивает open-access PDF по DOI через Unpaywall и прогоняет пайплайн.
Usage:
    python bulk_run.py --domain cocrystals --out results/cocrystals_all.csv
"""
import argparse
import os
import glob
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

UNPAYWALL_EMAIL = "frost8537@gmail.com"


def get_pdf_url(doi: str) -> str | None:
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            loc = data.get("best_oa_location") or {}
            return loc.get("url_for_pdf") or loc.get("url")
    except Exception as e:
        print(f"  Unpaywall error for {doi}: {e}")
    return None


def download_pdf(doi: str, out_path: str) -> bool:
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"  Already downloaded: {out_path}")
        return True
    pdf_url = get_pdf_url(doi)
    if not pdf_url:
        print(f"  No PDF found for {doi}")
        return False
    print(f"  Downloading from {pdf_url}")
    try:
        r = requests.get(pdf_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and len(r.content) > 10000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
        print(f"  Bad response: {r.status_code}, size={len(r.content)}")
    except Exception as e:
        print(f"  Download error: {e}")
    return False


def process_paper(pdf_path: str, doi: str, domain, work_dir: str) -> list[dict]:
    from pipeline.extractor import pdf_to_markdown, describe_images, inject_descriptions
    from pipeline.extractor import extract_from_markdown, verify_records
    from pipeline.smiles_lookup import enrich_smiles

    md_path = os.path.join(work_dir, "converted.md")

    if os.path.exists(md_path):
        print(f"  Using cached markdown")
        markdown = open(md_path, encoding="utf-8").read()
        image_paths = (glob.glob(os.path.join(work_dir, "*.jpeg")) +
                       glob.glob(os.path.join(work_dir, "*.jpg")) +
                       glob.glob(os.path.join(work_dir, "*.png")))
    else:
        from pipeline.pdf_parser import pdf_to_markdown as _pdf_to_markdown
        print(f"  Parsing PDF...")
        markdown, image_paths = _pdf_to_markdown(pdf_path, work_dir)

    print(f"  Describing {len(image_paths)} images...")
    descriptions = describe_images(image_paths)
    described_md = inject_descriptions(markdown, descriptions)

    print(f"  Extracting...")
    records = extract_from_markdown(described_md, domain)
    print(f"  → {len(records)} records")

    records = verify_records(records, domain, described_md)
    for name_field, smiles_field in domain.smiles_pairs:
        records = enrich_smiles(records, name_field, smiles_field)

    for r in records:
        r["doi"] = doi
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="cocrystals")
    parser.add_argument("--out", default="results/cocrystals_all.csv")
    args = parser.parse_args()

    from pipeline.domains import DOMAINS
    domain = DOMAINS[args.domain]()

    gt = pd.read_parquet(f"data/{args.domain}/data/train-00000-of-00001.parquet")
    open_papers = gt[gt["access"] == 1][["pdf", "doi"]].drop_duplicates()
    print(f"Open-access papers: {len(open_papers)}")

    os.makedirs("test_pdfs", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    all_records = []

    for _, row in open_papers.iterrows():
        doi = row["doi"]
        pdf_name = row["pdf"]
        pdf_path = f"test_pdfs/{pdf_name}.pdf"
        work_dir = f"/tmp/chemx_{pdf_name}"

        print(f"\n{'='*50}")
        print(f"Paper: {pdf_name} | DOI: {doi}")

        if not download_pdf(doi, pdf_path):
            print(f"  Skipping (no PDF)")
            continue

        try:
            records = process_paper(pdf_path, doi, domain, work_dir)
            all_records.extend(records)
            print(f"  Done: {len(records)} records")
        except Exception as e:
            print(f"  Error: {e}")
            import traceback; traceback.print_exc()

        time.sleep(2)

    if all_records:
        df = pd.DataFrame(all_records)
        df.to_csv(args.out, index=False)
        print(f"\nСохранено {len(df)} записей → {args.out}")
    else:
        print("Нет результатов")


if __name__ == "__main__":
    main()
