from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

try:
    from chemx_extract.config import NOT_DETECTED
except ImportError:
    NOT_DETECTED = "NOT_DETECTED"

try:
    from chemx_extract.schemas import EXTRACTED_COLUMNS, get_columns
except ImportError:
    EXTRACTED_COLUMNS = {
        "cocrystals": [
            "name_cocrystal",
            "ratio_cocrystal",
            "name_drug",
            "SMILES_drug",
            "name_coformer",
            "SMILES_coformer",
            "photostability_change",
        ],
        "oxazolidinone": [
            "compound_id",
            "smiles",
            "target_type",
            "target_relation",
            "target_value",
            "target_units",
            "bacteria",
        ],
        "cytotoxicity": [
            "material",
            "shape",
            "coat_functional_group",
            "synthesis_method",
            "surface_charge",
            "core_nm",
            "size_in_medium_nm",
            "hydrodynamic_nm",
            "potential_mv",
            "zeta_in_medium_mv",
            "no_of_cells_cells_well",
            "human_animal",
            "cell_source",
            "cell_tissue",
            "cell_morphology",
            "cell_age",
            "time_hr",
            "concentration",
            "test",
            "test_indicator",
            "viability_%",
        ],
    }

    def get_columns(domain: str) -> list[str]:
        return EXTRACTED_COLUMNS.get(domain, [])


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _unwrap_json_array(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("rows", "data", "results", "extractions", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def parse_llm_json_content(content: str | None) -> list[dict]:
    if not content:
        return []
    try:
        data = json.loads(_strip_json_fences(content))
        return _unwrap_json_array(data)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON content")
        return []


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _encode_image(path: Path) -> tuple[str, str]:
    return base64.b64encode(path.read_bytes()).decode("utf-8"), _media_type(path)


def call_anthropic_text(
    client: Any,
    system: str,
    user: str,
    model: str,
    max_tokens: int,
) -> str:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "".join(parts).strip()
    except Exception:
        logger.exception("Anthropic text call failed")
        return ""


def call_openai_text(client: Any, system: str, user: str, model: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return (content or "").strip()
    except Exception:
        logger.exception("OpenAI text call failed")
        return ""


def call_llm_text(
    provider: Literal["anthropic", "openai"],
    client: Any,
    system: str,
    user: str,
    model: str,
    max_tokens: int = 8192,
) -> str:
    if provider == "anthropic":
        return call_anthropic_text(client, system, user, model, max_tokens)
    return call_openai_text(client, system, user, model)


def call_anthropic_json(
    client: Any,
    system: str,
    user: str,
    model: str,
    max_tokens: int,
) -> list[dict]:
    text = call_anthropic_text(client, system, user, model, max_tokens)
    return parse_llm_json_content(text)


def call_openai_json(client: Any, system: str, user: str, model: str) -> list[dict]:
    text = call_openai_text(client, system, user, model)
    return parse_llm_json_content(text)


def call_llm_json(
    provider: Literal["anthropic", "openai"],
    client: Any,
    system: str,
    user: str,
    model: str,
    max_tokens: int = 16000,
) -> list[dict]:
    if provider == "anthropic":
        return call_anthropic_json(client, system, user, model, max_tokens)
    return call_openai_json(client, system, user, model)


def call_openai_vision_text(
    client: Any,
    system: str,
    user_text: str,
    image_path: Path,
    model: str,
) -> str:
    try:
        if not image_path.is_file() or image_path.suffix.lower() not in _IMAGE_SUFFIXES:
            return ""
        encoded, media = _encode_image(image_path)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media};base64,{encoded}"},
                        },
                    ],
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("OpenAI vision call failed")
        return ""


def call_anthropic_vision_text(
    client: Any,
    system: str,
    user_text: str,
    image_path: Path,
    model: str,
    max_tokens: int,
) -> str:
    try:
        if not image_path.is_file() or image_path.suffix.lower() not in _IMAGE_SUFFIXES:
            return ""
        encoded, media = _encode_image(image_path)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media,
                                "data": encoded,
                            },
                        },
                    ],
                }
            ],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "".join(parts).strip()
    except Exception:
        logger.exception("Anthropic vision call failed")
        return ""


def call_vision_text(
    provider: Literal["anthropic", "openai"],
    client: Any,
    system: str,
    user_text: str,
    image_path: Path,
    model: str,
    max_tokens: int = 8192,
) -> str:
    if provider == "anthropic":
        return call_anthropic_vision_text(client, system, user_text, image_path, model, max_tokens)
    return call_openai_vision_text(client, system, user_text, image_path, model)


def normalize_row(row: dict, domain: str) -> dict:
    columns = get_columns(domain)
    normalized: dict[str, str] = {}
    for column in columns:
        value = row.get(column, NOT_DETECTED)
        if value is None or (isinstance(value, str) and not value.strip()):
            normalized[column] = NOT_DETECTED
        else:
            normalized[column] = str(value)
    return normalized
