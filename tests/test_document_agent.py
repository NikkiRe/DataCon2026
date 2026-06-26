"""Tests for document extraction chunking."""

from chemx_extract.extraction.document_agent import _split_into_chunks


def test_split_into_chunks_adds_overlap():
    pages = [f"## Page {i}\n\n{'x' * 5000}" for i in range(1, 8)]
    content = "\n\n".join(pages)
    chunks = _split_into_chunks(content, max_chars=12000)
    assert len(chunks) > 1
    assert "do not re-extract" in chunks[1].lower()


def test_split_into_chunks_single_short_doc():
    content = "## Page 1\n\nShort text."
    assert _split_into_chunks(content) == [content]
