"""Tests for verify agent helpers."""

from chemx_extract.extraction.verify_agent import _relevant_source_snippet


def test_relevant_source_snippet_includes_keywords():
    intro = "Introduction " * 200
    photostab = "Figure 3 shows photostability of FUR-CAF cocrystal increases vs pure drug."
    tail = "Conclusion " * 200
    text = intro + photostab + tail
    snippet = _relevant_source_snippet(text, max_chars=3000)
    assert "photostability" in snippet.lower()
    assert "FUR-CAF" in snippet
