"""Tests for extraction agents with mocked OpenAI client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chemx_extract.extraction.base import EXTRACTED_COLUMNS, call_llm_json, normalize_row
from chemx_extract.extraction.figure_agent import extract_from_figure
from chemx_extract.extraction.prompts import (
    PROMPT_DESCRIPTION,
    build_system_prompt,
)
from chemx_extract.extraction.table_agent import extract_from_tables
from chemx_extract.extraction.text_agent import extract_from_text


def _mock_completion(content: str | None) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_client(content: str | None) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_completion(content)
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


def test_normalize_row_preserves_existing_values() -> None:
    row = {
        "name_drug": "Ibuprofen",
        "name_coformer": "Nicotinamide",
    }
    normalized = normalize_row(row, "cocrystals")

    assert normalized["name_drug"] == "Ibuprofen"
    assert normalized["name_coformer"] == "Nicotinamide"
    assert normalized["ratio_cocrystal"] == "NOT_DETECTED"


def test_build_system_prompt_includes_domain_hints() -> None:
    prompt = build_system_prompt("cocrystals")

    assert PROMPT_DESCRIPTION in prompt
    assert "name_cocrystal" in prompt
    assert "NOT_DETECTED" in prompt
    assert "photostability" in prompt.lower()

    ox_prompt = build_system_prompt("oxazolidinone")
    assert "compound_id" in ox_prompt
    assert "MIC" in ox_prompt or "pMIC" in ox_prompt

    cyto_prompt = build_system_prompt("cytotoxicity")
    assert "viability" in cyto_prompt.lower()
    assert "cell" in cyto_prompt.lower()


def test_call_llm_json_strips_markdown_fences() -> None:
    payload = json.dumps([{"compound_id": "1"}])
    client = _mock_client(f"```json\n{payload}\n```")
    rows = call_llm_json(client, "sys", "user", "gpt-test")
    assert len(rows) == 1
    assert rows[0]["compound_id"] == "1"


def test_call_llm_json_parses_array() -> None:
    payload = [{"compound_id": "A1", "bacteria": "S. aureus"}]
    client = _mock_client(json.dumps(payload))

    rows = call_llm_json(client, "system", "user", "test-model")

    assert rows == payload
    client.chat.completions.create.assert_called_once()


def test_call_llm_json_parses_wrapped_object() -> None:
    payload = {"rows": [{"name_drug": "Drug A"}]}
    client = _mock_client(json.dumps(payload))

    rows = call_llm_json(client, "system", "user", "test-model")

    assert rows == [{"name_drug": "Drug A"}]


def test_call_llm_json_returns_empty_on_invalid_json() -> None:
    client = _mock_client("not json")

    rows = call_llm_json(client, "system", "user", "test-model")

    assert rows == []


def test_call_llm_json_returns_empty_on_api_error() -> None:
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("api down")

    rows = call_llm_json(client, "system", "user", "test-model")

    assert rows == []


def test_extract_from_tables_normalizes_rows() -> None:
    payload = [{"compound_id": "OX-2", "target_value": "0.5"}]
    client = _mock_client(json.dumps(payload))
    tables = ["| compound_id | target_value |\n| OX-2 | 0.5 |"]

    rows = extract_from_tables(tables, "oxazolidinone", client)

    assert len(rows) == 1
    assert rows[0]["compound_id"] == "OX-2"
    assert rows[0]["target_value"] == "0.5"
    assert rows[0]["bacteria"] == "NOT_DETECTED"


def test_extract_from_tables_empty_input() -> None:
    client = _mock_client("[]")

    assert extract_from_tables([], "cocrystals", client) == []
    client.chat.completions.create.assert_not_called()


def test_extract_from_text_normalizes_rows() -> None:
    payload = [{"material": "Fe3O4", "viability_%": "85"}]
    client = _mock_client(json.dumps(payload))

    rows = extract_from_text("Nanoparticle cytotoxicity study.", "cytotoxicity", client)

    assert len(rows) == 1
    assert rows[0]["material"] == "Fe3O4"
    assert rows[0]["viability_%"] == "85"
    assert rows[0]["shape"] == "NOT_DETECTED"


def test_extract_from_text_empty_input() -> None:
    client = _mock_client("[]")

    assert extract_from_text("", "cocrystals", client) == []
    client.chat.completions.create.assert_not_called()


def test_extract_from_figure_uses_vision_and_normalizes(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    payload = [{"name_drug": "Aspirin", "name_coformer": "Caffeine"}]
    client = _mock_client(json.dumps(payload))

    rows = extract_from_figure(image_path, "cocrystals", client)

    assert len(rows) == 1
    assert rows[0]["name_drug"] == "Aspirin"
    assert rows[0]["SMILES_drug"] == "NOT_DETECTED"

    call_kwargs = client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in user_content)


def test_extract_from_figure_missing_file() -> None:
    client = _mock_client("[]")
    missing = Path("/tmp/nonexistent_chemx_figure.png")

    rows = extract_from_figure(missing, "cocrystals", client)

    assert rows == []
    client.chat.completions.create.assert_not_called()
