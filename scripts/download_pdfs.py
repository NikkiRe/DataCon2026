#!/usr/bin/env python3
"""Download open-access PDFs for a ChemX domain via OpenAlex + HTML link scraping."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from datasets import load_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chemx_extract.schemas import DATASETS, DATASETS_IDS  # noqa: E402

HF_CACHE = PROJECT_ROOT / "data" / "hf_cache"


def _find_pdf_links(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").lower()
        if ".pdf" in href.lower() or "pdf" in text or "download" in text:
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = urljoin(base_url, href)
            if href.startswith("http"):
                yield href


def download_pdf(session: requests.Session, name: str, doi: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 5000:
        return True

    urls: list[str] = []
    try:
        r = session.get(f"https://api.openalex.org/works/https://doi.org/{doi}", timeout=30)
        if r.ok:
            work = r.json()
            oa = work.get("open_access") or {}
            if oa.get("oa_url"):
                urls.append(oa["oa_url"])
            for loc in work.get("locations") or []:
                if loc.get("pdf_url"):
                    urls.append(loc["pdf_url"])
                elif loc.get("landing_page_url"):
                    urls.append(loc["landing_page_url"])
    except Exception:
        pass

    if doi.startswith("10.3390/"):
        urls.insert(0, f"https://www.mdpi.com/{doi.split('/', 1)[1]}/pdf")
    urls.append(f"https://doi.org/{doi}")

    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = session.get(url, timeout=90, allow_redirects=True)
            if resp.content[:4] == b"%PDF" and len(resp.content) > 5000:
                dest.write_bytes(resp.content)
                return True
            ctype = resp.headers.get("content-type", "")
            if "html" in ctype.lower():
                for link in _find_pdf_links(resp.text, resp.url):
                    if link in seen:
                        continue
                    seen.add(link)
                    r2 = session.get(link, timeout=90, allow_redirects=True, headers={"Referer": resp.url})
                    if r2.content[:4] == b"%PDF" and len(r2.content) > 5000:
                        dest.write_bytes(r2.content)
                        return True
                if "mdpi.com" in resp.url:
                    pdf_url = resp.url.split("?")[0].rstrip("/") + "/pdf"
                    r3 = session.get(pdf_url, timeout=90, allow_redirects=True, headers={"Referer": resp.url})
                    if r3.content[:4] == b"%PDF" and len(r3.content) > 5000:
                        dest.write_bytes(r3.content)
                        return True
        except Exception:
            continue
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=DATASETS, required=True)
    args = parser.parse_args()

    dataset_id = DATASETS_IDS[args.domain]
    out_dir = PROJECT_ROOT / "data" / "pdfs" / f"pdf_{args.domain}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset(dataset_id, split="train", cache_dir=str(HF_CACHE))
    df = ds.to_pandas()
    articles = df[df["access"] == 1][["pdf", "doi"]].drop_duplicates("pdf")

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (compatible; DataCon2026/1.0; mailto:datacon2026@example.com)"}
    )

    ok, fail = 0, 0
    for _, row in articles.iterrows():
        name, doi = row["pdf"], row["doi"]
        dest = out_dir / f"{name}.pdf"
        if download_pdf(session, name, doi, dest):
            ok += 1
            print(f"OK  {name}")
        else:
            fail += 1
            print(f"FAIL {name} ({doi})")
        time.sleep(0.8)

    print(f"\nDownloaded {ok}/{len(articles)} PDFs to {out_dir}")


if __name__ == "__main__":
    main()
