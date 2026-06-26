import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from nanozx import extract, predict

st.set_page_config(page_title="Nanozyme extractor", layout="wide")
st.title("Nanozyme data extraction")
st.caption("Upload a nanozyme article (PDF). The extractor returns ChemX-schema records.")

uploaded = st.file_uploader("Article PDF", type="pdf")

if uploaded is not None:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded.read())
        pdf_path = tmp.name

    with st.spinner("Extracting with Claude Opus 4.8..."):
        records = extract.extract_records(pdf_path)
        frame = predict.records_to_frame(records, uploaded.name.rsplit(".", 1)[0])

    st.success(f"Extracted {len(frame)} records.")
    st.dataframe(frame, use_container_width=True)
    st.download_button(
        "Download CSV",
        frame.to_csv(index=False).encode(),
        file_name=f"{uploaded.name.rsplit('.', 1)[0]}_extracted.csv",
        mime="text/csv",
    )
