from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from chemx_extract.config import NOT_DETECTED
from chemx_extract.pipeline import extract_from_pdf


@patch("chemx_extract.pipeline._get_openai_client")
@patch("chemx_extract.pipeline.parse_pdf")
@patch("chemx_extract.pipeline.extract_from_tables")
@patch("chemx_extract.pipeline.extract_from_text")
@patch("chemx_extract.pipeline.extract_from_figure")
def test_extract_from_pdf_wires_pipeline(
    mock_figure,
    mock_text,
    mock_tables,
    mock_parse,
    mock_client,
    tmp_path,
):
    pdf_path = tmp_path / "article.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parsed = MagicMock()
    parsed.tables = ["| a | b |"]
    parsed.markdown = "# Title"
    parsed.image_paths = [tmp_path / "fig1.png"]
    mock_parse.return_value = parsed
    mock_client.return_value = MagicMock()

    row = {
        "compound_id": "CMP1",
        "smiles": "CCO",
        "target_type": "MIC",
        "target_relation": "=",
        "target_value": "1,0",
        "target_units": "uM",
        "bacteria": "E. coli",
    }
    mock_tables.return_value = [row]
    mock_text.return_value = []
    mock_figure.return_value = []

    df = extract_from_pdf(pdf_path, "oxazolidinone", work_dir=tmp_path / "work")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.loc[0, "pdf"] == "article"
    assert df.loc[0, "compound_id"] == "CMP1"
    assert df.loc[0, "target_value"] == "1.0"
    mock_parse.assert_called_once()
    mock_tables.assert_called_once()
    mock_text.assert_called_once()


@patch("chemx_extract.pipeline._get_openai_client", return_value=None)
@patch("chemx_extract.pipeline.parse_pdf")
def test_extract_from_pdf_without_client_returns_empty_schema(mock_parse, mock_client, tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parsed = MagicMock()
    parsed.tables = []
    parsed.markdown = ""
    parsed.image_paths = []
    mock_parse.return_value = parsed

    df = extract_from_pdf(pdf_path, "oxazolidinone", work_dir=tmp_path / "work")

    assert list(df.columns) == [
        "compound_id",
        "smiles",
        "target_type",
        "target_relation",
        "target_value",
        "target_units",
        "bacteria",
        "pdf",
    ]
    assert len(df) == 0
