"""Streamlit UI for ChemX PDF extraction: upload a PDF, extract, view and download the table."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.config import ANTHROPIC_API_KEY, OPENAI_API_KEY  # noqa: E402
from chemx_extract.exceptions import NoLLMProviderError  # noqa: E402
from chemx_extract.pipeline import extract_from_pdf  # noqa: E402
from chemx_extract.schemas import DATASETS, get_columns  # noqa: E402

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
_EMPTY_TOKENS = {"", "nan", "none", "not_detected"}


def fill_summary(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    cols = [c for c in get_columns(domain) if c in df.columns]
    n = len(df)
    rows = []
    for col in cols:
        values = df[col].astype(str).str.strip().str.lower()
        filled = int((~values.isin(_EMPTY_TOKENS)).sum())
        rows.append({"field": col, "filled": f"{filled}/{n}"})
    return pd.DataFrame(rows)


def discover_examples() -> list[tuple[Path, str | None]]:
    if not EXAMPLES_DIR.is_dir():
        return []
    found = []
    for csv in sorted(EXAMPLES_DIR.glob("*.csv")):
        domain = csv.stem.split("__")[0] if "__" in csv.stem else None
        found.append((csv, domain if domain in DATASETS else None))
    return found


def run_extraction(
    pdf_bytes: bytes,
    name: str,
    domain: str,
    mode: str,
    verify: bool,
    holder: dict,
) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="chemx_") as tmp:
            pdf_path = Path(tmp) / name
            pdf_path.write_bytes(pdf_bytes)
            holder["df"] = extract_from_pdf(
                pdf_path,
                domain,
                work_dir=Path(tmp) / "work",
                mode=mode,
                verify=verify,
            )
    except Exception as exc:  # noqa: BLE001
        holder["error"] = exc


def show_result(df: pd.DataFrame, domain: str | None, source_name: str) -> None:
    st.success(f"{len(df)} row(s) extracted.")
    st.dataframe(df, use_container_width=True)
    if domain:
        with st.expander("Field fill summary"):
            st.dataframe(fill_summary(df, domain), use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"{source_name}.csv",
        mime="text/csv",
    )


st.set_page_config(page_title="ChemX Extract", layout="wide")
st.title("ChemX PDF Extraction")
st.caption("Upload a chemistry article PDF, pick a domain, extract structured data, download CSV.")

if "cache" not in st.session_state:
    st.session_state.cache = {}

with st.sidebar:
    domain = st.selectbox("Domain", DATASETS, index=DATASETS.index("cocrystals"))
    mode = st.selectbox(
        "Mode",
        ["fast", "pdf", "staged"],
        index=0,
        help="fast: text + tables + vision. pdf: one call with the PDF. staged: legacy.",
    )
    verify = st.checkbox(
        "Second-pass verification",
        value=True,
        help="Higher quality, slower. Uncheck for a faster demo.",
    )
    st.divider()
    if not ANTHROPIC_API_KEY and not OPENAI_API_KEY:
        st.error("No API key. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env or app secrets.")
    elif ANTHROPIC_API_KEY and OPENAI_API_KEY:
        st.success("Hybrid route: Anthropic + OpenAI.")
    elif ANTHROPIC_API_KEY:
        st.info("Anthropic-only route.")
    else:
        st.info("OpenAI-only route.")
    st.caption("Official Macro-F1: run scripts/run_eval.py on the test set.")

examples = discover_examples()
if examples:
    st.subheader("Examples (precomputed, instant)")
    columns = st.columns(min(len(examples), 3))
    for i, (csv, _) in enumerate(examples):
        if columns[i % len(columns)].button(csv.stem, key=f"ex_{csv.stem}"):
            st.session_state.example = csv.name
    chosen = st.session_state.get("example")
    if chosen:
        csv = EXAMPLES_DIR / chosen
        ex_domain = next((d for c, d in examples if c.name == chosen), None)
        st.markdown(f"**Example: {csv.stem}**")
        show_result(pd.read_csv(csv, dtype=str).fillna(""), ex_domain, csv.stem)

st.subheader("Extract from your PDF")
uploaded = st.file_uploader("PDF file", type=["pdf"])

if uploaded is not None:
    pdf_bytes = uploaded.getvalue()
    cache_key = (hashlib.sha256(pdf_bytes).hexdigest(), domain, mode, verify)
    st.write(f"Selected: {uploaded.name}  |  domain={domain}  |  mode={mode}  |  verify={verify}")

    if st.button("Extract", type="primary"):
        stem = Path(uploaded.name).stem
        if cache_key in st.session_state.cache:
            st.info("Loaded from cache.")
            show_result(st.session_state.cache[cache_key], domain, stem)
        elif not ANTHROPIC_API_KEY and not OPENAI_API_KEY:
            st.error("No API key configured. Set one in .env or app secrets.")
        else:
            holder: dict = {}
            worker = threading.Thread(
                target=run_extraction,
                args=(pdf_bytes, uploaded.name, domain, mode, verify, holder),
                daemon=True,
            )
            worker.start()
            with st.status(f"Extracting ({domain}, mode={mode})...", expanded=True) as status:
                ticker = st.empty()
                started = time.time()
                while worker.is_alive():
                    ticker.write(f"working... {int(time.time() - started)}s elapsed")
                    time.sleep(0.5)
                worker.join()
                elapsed = int(time.time() - started)
                if "error" in holder:
                    error = holder["error"]
                    if isinstance(error, NoLLMProviderError):
                        status.update(label="No API key", state="error")
                        st.error(str(error))
                    else:
                        status.update(label=f"Failed after {elapsed}s", state="error")
                        message = str(error)
                        if "rate_limit" in message or "429" in message:
                            st.error("Rate limit hit. Wait and retry, or use a higher-tier key.")
                        else:
                            st.error(f"Extraction failed: {message}")
                else:
                    status.update(label=f"Done in {elapsed}s", state="complete")

            if "df" in holder:
                st.session_state.cache[cache_key] = holder["df"]
                show_result(holder["df"], domain, stem)
