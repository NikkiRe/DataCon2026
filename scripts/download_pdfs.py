import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import requests

from nanozx import dataset

EMAIL = os.environ.get("UNPAYWALL_EMAIL", "ne@agmo.cat")
PDF_DIR = Path(__file__).resolve().parents[1] / "data" / "pdfs"
MANIFEST = PDF_DIR / "manifest.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/pdf,*/*",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def unpaywall_urls(doi: str) -> list[str]:
    api = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
    try:
        data = SESSION.get(api, timeout=30).json()
    except Exception:
        return []
    locations = []
    if data.get("best_oa_location"):
        locations.append(data["best_oa_location"])
    locations.extend(data.get("oa_locations") or [])
    urls = []
    for loc in locations:
        for key in ("url_for_pdf", "url"):
            if loc.get(key):
                urls.append(loc[key])
    return urls


def _pmc_render(url: str) -> str | None:
    match = re.search(r"PMC(\d+)|articles/(\d{6,})", url)
    if not match:
        return None
    pmc = match.group(1) or match.group(2)
    return f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmc}&blobtype=pdf"


def _meta_pdf_url(html: str, base: str) -> str | None:
    match = re.search(r'name=["\']citation_pdf_url["\']\s+content=["\']([^"\']+)', html)
    if not match:
        match = re.search(r'content=["\']([^"\']+)["\']\s+name=["\']citation_pdf_url["\']', html)
    if not match:
        return None
    return requests.compat.urljoin(base, match.group(1))


def _get(url: str):
    try:
        return SESSION.get(url, timeout=60, allow_redirects=True)
    except Exception:
        return None


def fetch_pdf(url: str, dest: Path) -> bool:
    pmc = _pmc_render(url)
    if pmc:
        response = _get(pmc)
        if response and response.content.startswith(b"%PDF"):
            dest.write_bytes(response.content)
            return True

    response = _get(url)
    if response is None or response.status_code != 200:
        return False
    if response.content.startswith(b"%PDF"):
        dest.write_bytes(response.content)
        return True

    if "html" in response.headers.get("Content-Type", ""):
        pdf_url = _meta_pdf_url(response.text, response.url)
        if pdf_url and pdf_url != url:
            inner = _get(pdf_url)
            if inner and inner.content.startswith(b"%PDF"):
                dest.write_bytes(inner.content)
                return True
    return False


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    df = dataset.load_raw()
    articles = df[df["access"] == 1][["pdf", "doi"]].drop_duplicates("pdf")

    records = []
    for _, row in articles.iterrows():
        stem, doi = row["pdf"], row["doi"]
        dest = PDF_DIR / f"{stem}.pdf"
        if dest.exists():
            records.append((stem, doi, "cached", ""))
            print(f"[cached] {stem}")
            continue

        candidates = unpaywall_urls(doi) + [f"https://doi.org/{doi}"]
        status, source = "download_failed", ""
        for url in candidates:
            if fetch_pdf(url, dest):
                status, source = "ok", url
                break
        records.append((stem, doi, status, source))
        print(f"[{status}] {stem}  {source[:80]}")
        time.sleep(0.5)

    manifest = pd.DataFrame(records, columns=["pdf", "doi", "status", "url"])
    manifest.to_csv(MANIFEST, index=False)
    counts = manifest["status"].value_counts().to_dict()
    print(f"\ncoverage: {counts}")
    print(f"downloaded/cached: {sum(manifest['status'].isin(['ok', 'cached']))}/{len(manifest)}")


if __name__ == "__main__":
    main()
