import streamlit as st
import pandas as pd
import tempfile
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from pipeline.domains import DOMAINS
from pipeline.extractor import run_pipeline

st.set_page_config(page_title="ChemX Extractor", layout="wide")
st.title("ChemX — Chemical Data Extractor")
st.caption("Upload a scientific PDF and extract structured chemical data automatically.")

domain_name = st.selectbox("Domain", list(DOMAINS.keys()))
uploaded = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded and st.button("Extract", type="primary"):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    work_dir = tempfile.mkdtemp(prefix="chemx_")

    with st.spinner("Running pipeline (this takes 1-2 min)..."):
        try:
            domain = DOMAINS[domain_name]()
            records = run_pipeline(tmp_path, domain, work_dir=work_dir)

            if records:
                df = pd.DataFrame(records)
                st.success(f"Extracted {len(df)} record(s)")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode()
                st.download_button("Download CSV", csv, "extracted.csv", "text/csv")
            else:
                st.warning("No records extracted. Check the PDF or domain.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            os.unlink(tmp_path)
