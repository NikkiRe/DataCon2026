"""Tests for selective vision page selection."""

from unittest.mock import MagicMock, patch

from chemx_extract.preprocessing.pdf_parser import _vision_page_numbers


def test_vision_page_numbers_prefers_photostability_pages(tmp_path):
    filler = MagicMock()
    filler.extract_text.return_value = ""
    page1 = MagicMock()
    page1.extract_text.return_value = "Introduction only."
    page3 = MagicMock()
    page3.extract_text.return_value = "Figure 3. Photostability of FUR-CAF cocrystal vs FUR."
    page9 = MagicMock()
    page9.extract_text.return_value = "Figure 9. UV degradation results."

    mock_pdf = MagicMock()
    mock_pdf.pages = [page1, filler, page3, filler, filler, filler, filler, filler, page9]
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_pdf
    mock_ctx.__exit__.return_value = False

    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("pdfplumber.open", return_value=mock_ctx):
        pages = _vision_page_numbers(pdf_path)

    assert 1 not in pages
    assert 3 in pages
    assert 9 in pages
    assert len(pages) <= 4
