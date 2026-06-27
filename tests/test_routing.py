"""Tests for LLM provider routing and fallbacks."""

from __future__ import annotations

import pytest

from chemx_extract.exceptions import NoLLMProviderError
from chemx_extract.llm import routing


def test_resolve_route_hybrid(monkeypatch):
    monkeypatch.setattr(routing, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(routing, "OPENAI_API_KEY", "sk-test")

    route = routing.resolve_route()
    assert route.mode == "hybrid"
    assert route.compress_provider == "anthropic"
    assert route.compress_model == routing.ANTHROPIC_CHEAP_MODEL
    assert route.extract_provider == "anthropic"
    assert route.extract_model == routing.ANTHROPIC_EXTRACT_MODEL
    assert route.draft_vision_provider == "openai"
    assert route.draft_vision_model == routing.OPENAI_DRAFT_VISION_MODEL
    assert route.final_vision_provider == "openai"
    assert route.final_vision_model == routing.OPENAI_VISION_MODEL


def test_resolve_route_anthropic_only(monkeypatch):
    monkeypatch.setattr(routing, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(routing, "OPENAI_API_KEY", "")

    route = routing.resolve_route()
    assert route.mode == "anthropic_only"
    assert route.compress_provider == "anthropic"
    assert route.extract_provider == "anthropic"
    assert route.draft_vision_provider == "anthropic"
    assert route.final_vision_provider == "anthropic"


def test_resolve_route_openai_only(monkeypatch):
    monkeypatch.setattr(routing, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(routing, "OPENAI_API_KEY", "sk-test")

    route = routing.resolve_route()
    assert route.mode == "openai_only"
    assert route.compress_provider == "openai"
    assert route.extract_provider == "openai"
    assert route.draft_vision_provider == "openai"
    assert route.final_vision_provider == "openai"


def test_resolve_route_no_keys(monkeypatch):
    monkeypatch.setattr(routing, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(routing, "OPENAI_API_KEY", "")

    with pytest.raises(NoLLMProviderError):
        routing.resolve_route()
