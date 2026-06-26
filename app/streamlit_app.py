"""Streamlit demo UI for ChemX PDF extraction."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from chemx_extract.config import OPENAI_API_KEY  # noqa: E402
from chemx_extract.pipeline import extract_from_pdf  # noqa: E402
from chemx_extract.schemas import DATASETS  # noqa: E402

st.set_page_config(page_title="ChemX Extract", page_icon="🧪", layout="wide")
st.title("ChemX PDF Extraction")
st.caption("Upload a chemistry article PDF and extract structured data by domain.")

domain = st.sidebar.selectbox("Domain", DATASETS, index=DATASETS.index("cocrystals"))

uploaded = st.file_uploader("PDF file", type=["pdf"])

if not OPENAI_API_KEY:
    st.warning(
        "OPENAI_API_KEY is not set. Add it to `.env` or Streamlit secrets. "
        "Extraction will run without LLM calls and may return empty results."
    )

if uploaded is not None:
    st.info(f"Selected: **{uploaded.name}** ({domain})")

    if st.button("Extract", type="primary"):
        with st.spinner("Extracting data from PDF…"):
            try:
                with tempfile.TemporaryDirectory(prefix="chemx_") as tmp:
                    pdf_path = Path(tmp) / uploaded.name
                    pdf_path.write_bytes(uploaded.getvalue())
                    work_dir = Path(tmp) / "work"
                    df = extract_from_pdf(pdf_path, domain, work_dir=work_dir)

                st.success(f"Extracted {len(df)} row(s).")
                st.dataframe(df, use_container_width=True)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv_bytes,
                    file_name=f"{Path(uploaded.name).stem}.csv",
                    mime="text/csv",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Extraction failed: {exc}")

st.sidebar.divider()
st.sidebar.info(
    "Run `python scripts/run_eval.py` on the test set for the official Macro-F1 score."
)
