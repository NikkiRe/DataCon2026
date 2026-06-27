from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chemx_extract.exceptions import NoLLMProviderError
from chemx_extract.pipeline import extract_from_pdf


@patch("chemx_extract.pipeline.build_extraction_context")
@patch("chemx_extract.pipeline.compress_text", return_value="compressed facts")
@patch("chemx_extract.pipeline.draft_describe_figure", return_value="figure draft")
@patch("chemx_extract.pipeline.parse_pdf")
@patch("chemx_extract.pipeline.extract_from_tables")
@patch("chemx_extract.pipeline.extract_from_text")
@patch("chemx_extract.pipeline.extract_from_figure")
@patch("chemx_extract.pipeline.verify_records", side_effect=lambda rows, *a, **k: rows)
def test_extract_from_pdf_staged_pipeline(
    mock_verify,
    mock_figure,
    mock_text,
    mock_tables,
    mock_parse,
    mock_draft,
    mock_compress,
    mock_build_ctx,
    tmp_path,
):
    pdf_path = tmp_path / "article.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parsed = MagicMock()
    parsed.tables = ["| a | b |"]
    parsed.markdown = "# Title"
    parsed.image_paths = [tmp_path / "fig1.png"]
    mock_parse.return_value = parsed
    mock_build_ctx.return_value = MagicMock()

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

    df = extract_from_pdf(
        pdf_path,
        "oxazolidinone",
        work_dir=tmp_path / "work",
        mode="staged",
    )

    assert len(df) == 1
    assert df.loc[0, "target_value"] == "1.0"
    mock_compress.assert_called_once()
    mock_tables.assert_called_once()


@patch("chemx_extract.pipeline.build_extraction_context")
@patch("chemx_extract.pipeline.batch_describe_figures", return_value={})
@patch("chemx_extract.pipeline.parse_pdf")
@patch("chemx_extract.pipeline.extract_from_document")
@patch("chemx_extract.pipeline.verify_records", side_effect=lambda rows, *a, **k: rows)
def test_extract_from_pdf_fast_pipeline(
    mock_verify,
    mock_document,
    mock_parse,
    mock_batch_vision,
    mock_build_ctx,
    tmp_path,
):
    pdf_path = tmp_path / "article.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parsed = MagicMock()
    parsed.markdown = (
        "# Title\n\nThe photostability of CBZ-SAC was improved compared with that of pure drug."
    )
    parsed.image_paths = []
    parsed.tables = []
    parsed.image_source = "none"
    mock_parse.return_value = parsed
    mock_build_ctx.return_value = MagicMock()

    mock_document.return_value = [
        {
            "name_cocrystal": "CBZ-SAC",
            "ratio_cocrystal": "1:1",
            "name_drug": "Carbamazepine",
            "SMILES_drug": "NOT_DETECTED",
            "name_coformer": "Saccharin",
            "SMILES_coformer": "NOT_DETECTED",
            "photostability_change": "increases",
        }
    ]

    df = extract_from_pdf(pdf_path, "cocrystals", work_dir=tmp_path / "work", mode="fast")

    assert len(df) == 1
    assert df.loc[0, "photostability_change"] == "increases"
    assert df.loc[0, "ratio_cocrystal"] == "1 : 1"
    mock_document.assert_called_once()
    mock_batch_vision.assert_not_called()


@patch("chemx_extract.pipeline.build_extraction_context", side_effect=NoLLMProviderError("no keys"))
def test_extract_from_pdf_raises_without_providers(mock_ctx, tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with pytest.raises(NoLLMProviderError):
        extract_from_pdf(pdf_path, "oxazolidinone", work_dir=tmp_path / "work")
