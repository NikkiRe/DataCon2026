"""Tests for extraction agents with mocked LLM clients."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chemx_extract.extraction.base import (
    EXTRACTED_COLUMNS,
    call_anthropic_json,
    call_llm_json,
    call_openai_json,
    normalize_row,
    parse_llm_json_content,
)
from chemx_extract.extraction.compress_agent import compress_text
from chemx_extract.extraction.figure_agent import extract_from_figure
from chemx_extract.extraction.prompts import (
    PROMPT_DESCRIPTION,
    build_compress_prompt,
    build_system_prompt,
)
from chemx_extract.extraction.table_agent import extract_from_tables
from chemx_extract.extraction.text_agent import extract_from_text
from chemx_extract.llm.routing import ExtractionContext, ModelRoute


def _hybrid_route() -> ModelRoute:
    return ModelRoute(
        mode="hybrid",
        compress_provider="anthropic",
        compress_model="claude-haiku-4-5",
        compress_max_tokens=8192,
        extract_provider="anthropic",
        extract_model="claude-opus-4-8",
        extract_max_tokens=16000,
        draft_vision_provider="openai",
        draft_vision_model="gpt-4o-mini",
        final_vision_provider="openai",
        final_vision_model="gpt-4o",
    )


def _ctx(anthropic=None, openai=None) -> ExtractionContext:
    return ExtractionContext(
        route=_hybrid_route(),
        anthropic_client=anthropic,
        openai_client=openai,
    )


def _mock_openai_completion(content: str | None) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_openai_client(content: str | None) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_openai_completion(content)
    return client


def _mock_anthropic_client(content: str | None) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = content or ""
    response = MagicMock()
    response.content = [block]
    client = MagicMock()
    client.messages.create.return_value = response
    return client


@pytest.mark.parametrize(
    "domain",
    ["cocrystals", "oxazolidinone", "cytotoxicity"],
)
def test_normalize_row_fills_missing_columns(domain: str) -> None:
    row = {"compound_id": "OX-1"} if domain == "oxazolidinone" else {}
    normalized = normalize_row(row, domain)
    expected_columns = EXTRACTED_COLUMNS[domain]

    assert list(normalized.keys()) == expected_columns
    if domain == "oxazolidinone":
        assert normalized["compound_id"] == "OX-1"
    for key, value in normalized.items():
        if key not in row:
            assert value == "NOT_DETECTED"


def test_build_compress_prompt_includes_columns() -> None:
    prompt = build_compress_prompt("cocrystals")
    assert "fact sheet" in prompt.lower()
    assert "name_cocrystal" in prompt


def test_build_system_prompt_includes_domain_hints() -> None:
    prompt = build_system_prompt("cocrystals")
    assert PROMPT_DESCRIPTION in prompt
    assert "NOT_DETECTED" in prompt


def test_parse_llm_json_strips_markdown_fences() -> None:
    payload = json.dumps([{"compound_id": "1"}])
    rows = parse_llm_json_content(f"```json\n{payload}\n```")
    assert len(rows) == 1


def test_call_anthropic_json_parses_array() -> None:
    payload = [{"compound_id": "A1"}]
    client = _mock_anthropic_client(json.dumps(payload))
    rows = call_anthropic_json(client, "system", "user", "claude-opus-4-8", 16000)
    assert rows == payload


def test_call_llm_json_openai_alias() -> None:
    payload = [{"compound_id": "A1"}]
    client = _mock_openai_client(json.dumps(payload))
    rows = call_llm_json("openai", client, "system", "user", "gpt-4.1", 16000)
    assert rows == payload


def test_compress_text_uses_cheap_tier() -> None:
    client = _mock_anthropic_client("compound X MIC 0.5 ug/ml")
    ctx = _ctx(anthropic=client)
    out = compress_text("Long article about cocrystals...", "cocrystals", ctx)
    assert "MIC" in out
    client.messages.create.assert_called_once()


def test_extract_from_tables_uses_extract_tier() -> None:
    payload = [{"compound_id": "OX-2", "target_value": "0.5"}]
    client = _mock_anthropic_client(json.dumps(payload))
    ctx = _ctx(anthropic=client)
    tables = ["| compound_id | target_value |\n| OX-2 | 0.5 |"]

    rows = extract_from_tables(tables, "oxazolidinone", ctx)

    assert len(rows) == 1
    assert rows[0]["compound_id"] == "OX-2"


def test_extract_from_text_includes_figure_notes() -> None:
    payload = [{"material": "Fe3O4", "viability_%": "85"}]
    client = _mock_anthropic_client(json.dumps(payload))
    ctx = _ctx(anthropic=client)

    rows = extract_from_text(
        "compressed facts",
        "cytotoxicity",
        ctx,
        figure_notes="Figure 1: viability 85%",
    )

    assert len(rows) == 1
    call_args = client.messages.create.call_args.kwargs
    assert "Figure 1" in call_args["messages"][0]["content"]


def test_extract_from_figure_uses_openai_vision(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    payload = [{"name_drug": "Aspirin"}]
    client = _mock_openai_client(json.dumps(payload))
    ctx = _ctx(openai=client)

    rows = extract_from_figure(image_path, "cocrystals", ctx, draft_note="draft note")

    assert len(rows) == 1
    call_kwargs = client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in user_content)


def test_extract_from_tables_empty_input() -> None:
    ctx = _ctx(anthropic=_mock_anthropic_client("[]"))
    assert extract_from_tables([], "cocrystals", ctx) == []
