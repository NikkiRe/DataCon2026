#!/usr/bin/env python3
"""Download open-access PDFs for a ChemX domain.

Sources (in priority order):
- mdpi-res.com direct deploy URLs for MDPI articles (10.3390/*)
- Unpaywall API (all OA locations, not only best)
- OpenAlex OA locations
- Semantic Scholar openAccessPdf
- Publisher-specific fallbacks + HTML link scraping
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from datasets import load_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chemx_extract.schemas import DATASETS, DATASETS_IDS  # noqa: E402

HF_CACHE = PROJECT_ROOT / "data" / "hf_cache"


def _unpaywall_email() -> str:
    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if email and "example.com" not in email:
        return email
    try:
        out = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            cwd=PROJECT_ROOT,
        )
        email = (out.stdout or "").strip()
        if email and "example.com" not in email:
            return email
    except Exception:
        pass
    return "research@openalex.org"


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


def _is_pdf(content: bytes) -> bool:
    return len(content) > 5000 and content[:4] == b"%PDF"


def _try_fetch(
    session: requests.Session,
    url: str,
    seen: set[str],
    *,
    referer: str | None = None,
) -> bytes | None:
    if url in seen:
        return None
    seen.add(url)
    try:
        headers = {"Referer": referer} if referer else {}
        resp = session.get(url, timeout=90, allow_redirects=True, headers=headers)
        if _is_pdf(resp.content):
            return resp.content
        if "html" in resp.headers.get("content-type", "").lower():
            for link in _find_pdf_links(resp.text, resp.url):
                data = _try_fetch(session, link, seen, referer=resp.url)
                if data:
                    return data
    except Exception:
        return None
    return None


def _mdpi_res_urls(session: requests.Session, doi: str) -> list[str]:
    """Build mdpi-res.com article_deploy URLs from DOI landing page path."""
    if not doi.startswith("10.3390/"):
        return []
    try:
        landing = session.get(f"https://doi.org/{doi}", timeout=30, allow_redirects=True).url
    except Exception:
        return []
    if "mdpi.com" not in landing:
        return []

    parts = landing.rstrip("/").split("/")
    if len(parts) < 3 or not parts[-1].isdigit():
        return []

    vol, art = parts[-3], parts[-1]
    slug = doi.split("/", 1)[1]
    journal_match = re.match(r"([a-z]+)", slug)
    if not journal_match:
        return []
    journal = journal_match.group(1)
    art_padded = str(int(art)).zfill(5)
    stem = f"{journal}-{vol}-{art_padded}"

    urls: list[str] = []
    for ver in ("-v2", "", "-v1"):
        urls.append(
            f"https://mdpi-res.com/{journal}/{stem}/article_deploy/{stem}{ver}.pdf"
        )
    return urls


def _unpaywall_urls(session: requests.Session, doi: str, email: str) -> list[str]:
    urls: list[str] = []
    try:
        resp = session.get(
            f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={email}",
            timeout=30,
        )
        if not resp.ok:
            return urls
        data = resp.json()
        for loc in data.get("oa_locations") or []:
            if loc.get("url_for_pdf"):
                urls.append(loc["url_for_pdf"])
            elif loc.get("url", "").lower().endswith(".pdf"):
                urls.append(loc["url"])
        best = data.get("best_oa_location") or {}
        if best.get("url_for_pdf"):
            urls.insert(0, best["url_for_pdf"])
    except Exception:
        pass
    return urls


def _openalex_urls(session: requests.Session, doi: str) -> list[str]:
    urls: list[str] = []
    try:
        resp = session.get(
            f"https://api.openalex.org/works/https://doi.org/{doi}",
            timeout=30,
        )
        if not resp.ok:
            return urls
        work = resp.json()
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
    return urls


def _semantic_scholar_pdf(session: requests.Session, doi: str) -> str | None:
    try:
        resp = session.get(
            "https://api.semanticscholar.org/graph/v1/paper/"
            f"DOI:{quote(doi, safe='')}?fields=openAccessPdf",
            timeout=30,
        )
        if resp.ok:
            pdf = (resp.json().get("openAccessPdf") or {}).get("url")
            if pdf:
                return pdf
    except Exception:
        pass
    return None


def _candidate_urls(doi: str) -> list[str]:
    urls: list[str] = []
    if doi.startswith("10.1186/"):
        urls.append(f"https://link.springer.com/content/pdf/{doi}.pdf")
    if doi.startswith("10.1021/"):
        urls.append(f"https://pubs.acs.org/doi/pdf/{doi}")
    urls.append(f"https://doi.org/{doi}")
    return urls


def download_pdf(session: requests.Session, name: str, doi: str, dest: Path, email: str) -> bool:
    if dest.exists() and dest.stat().st_size > 5000:
        return True

    urls: list[str] = []
    seen_urls: set[str] = set()

    def add(*candidates: str | None) -> None:
        for url in candidates:
            if url and url not in seen_urls:
                seen_urls.add(url)
                urls.append(url)

    # MDPI: mdpi-res works even when www.mdpi.com blocks bots.
    add(*_mdpi_res_urls(session, doi))
    add(*_unpaywall_urls(session, doi, email))
    add(*_openalex_urls(session, doi))
    add(_semantic_scholar_pdf(session, doi))
    add(*_candidate_urls(doi))

    fetch_seen: set[str] = set()
    for url in urls:
        data = _try_fetch(session, url, fetch_seen)
        if data:
            dest.write_bytes(data)
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=DATASETS, required=True)
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip PDFs that already exist in the output directory.",
    )
    args = parser.parse_args()

    email = _unpaywall_email()
    dataset_id = DATASETS_IDS[args.domain]
    out_dir = PROJECT_ROOT / "data" / "pdfs" / f"pdf_{args.domain}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset(dataset_id, split="train", cache_dir=str(HF_CACHE))
    df = ds.to_pandas()
    articles = df[df["access"] == 1][["pdf", "doi"]].drop_duplicates("pdf")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; DataCon2026/1.0; "
                f"mailto:{email})"
            ),
            "Accept": "application/pdf,*/*",
        }
    )

    ok, fail = 0, 0
    for _, row in articles.iterrows():
        name, doi = row["pdf"], row["doi"]
        dest = out_dir / f"{name}.pdf"
        if args.only_missing and dest.exists() and dest.stat().st_size > 5000:
            ok += 1
            print(f"SKIP {name} (exists)")
            continue
        if download_pdf(session, name, doi, dest, email):
            ok += 1
            print(f"OK  {name}")
        else:
            fail += 1
            print(f"FAIL {name} ({doi})")
        time.sleep(0.8)

    print(f"\nDownloaded {ok}/{len(articles)} PDFs to {out_dir}")
    print(f"Unpaywall email: {email}")


if __name__ == "__main__":
    main()
