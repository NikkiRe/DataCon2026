"""Tests for PDF preprocessing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chemx_extract.preprocessing import (
    ParsedDocument,
    extract_tables_pdfplumber,
    merge_supplementary,
    parse_pdf,
)


def test_parsed_document_fields() -> None:
    doc = ParsedDocument(
        pdf_name="article.pdf",
        markdown="# Title\n\nBody text.",
        tables=["## Table 1\n\n| a | b |\n| --- | --- |\n| 1 | 2 |"],
        image_paths=[Path("/tmp/page_001.png")],
    )

    assert doc.pdf_name == "article.pdf"
    assert "Title" in doc.markdown
    assert len(doc.tables) == 1
    assert doc.tables[0].startswith("## Table 1")
    assert doc.image_paths[0].name == "page_001.png"


def test_extract_tables_pdfplumber_no_tables() -> None:
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = []
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_pdf
    mock_ctx.__exit__.return_value = False

    with patch("pdfplumber.open", return_value=mock_ctx) as mock_open:
        result = extract_tables_pdfplumber(Path("dummy.pdf"))

    assert result == []
    mock_open.assert_called_once_with(Path("dummy.pdf"))


def test_extract_tables_pdfplumber_formats_markdown() -> None:
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = [
        [["Compound", "Value"], ["A", "1"]],
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_pdf
    mock_ctx.__exit__.return_value = False

    with patch("pdfplumber.open", return_value=mock_ctx):
        result = extract_tables_pdfplumber(Path("dummy.pdf"))

    assert len(result) == 1
    assert result[0].startswith("## Table 1")
    assert "| Compound | Value |" in result[0]
    assert "| A | 1 |" in result[0]


def test_extract_tables_pdfplumber_on_blank_pdf(tmp_path: Path) -> None:
    try:
        from pypdf import PdfWriter
    except ImportError:
        pytest.skip("pypdf not installed")

    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as f:
        writer.write(f)

    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        pytest.skip("pdfplumber not installed")

    tables = extract_tables_pdfplumber(pdf_path)
    assert isinstance(tables, list)
    assert tables == []


def test_merge_supplementary_copies_main_when_no_suppl(tmp_path: Path) -> None:
    main = tmp_path / "main.pdf"
    main.write_bytes(b"%PDF-1.4 minimal")
    out = tmp_path / "merged.pdf"

    result = merge_supplementary(main, None, out)

    assert result == out
    assert out.read_bytes() == main.read_bytes()


def test_parse_pdf_pdfplumber_fallback(tmp_path: Path) -> None:
    try:
        from pypdf import PdfWriter
    except ImportError:
        pytest.skip("pypdf not installed")

    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as f:
        writer.write(f)

    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        pytest.skip("pdfplumber not installed")

    work_dir = tmp_path / "work"
    with patch(
        "chemx_extract.preprocessing.pdf_parser._try_marker",
        return_value=None,
    ):
        doc = parse_pdf(pdf_path, work_dir)

    assert doc.pdf_name == "sample.pdf"
    assert isinstance(doc.markdown, str)
    assert isinstance(doc.tables, list)
    assert isinstance(doc.image_paths, list)
