from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from openai import OpenAI

from chemx_extract.extraction.base import normalize_row

try:
    from chemx_extract.config import OPENAI_VISION_MODEL
except ImportError:
    OPENAI_VISION_MODEL = "gpt-4o-2024-11-20"

from chemx_extract.extraction.prompts import build_system_prompt

logger = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _unwrap_json_array(data: object) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("rows", "data", "results", "extractions", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _call_vision_json(
    client: OpenAI,
    system: str,
    user_text: str,
    image_path: Path,
    model: str,
) -> list[dict]:
    try:
        if not image_path.is_file():
            logger.warning("Figure not found: %s", image_path)
            return []
        if image_path.suffix.lower() not in _IMAGE_SUFFIXES:
            logger.warning("Unsupported figure format: %s", image_path)

        encoded = _encode_image(image_path)
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
                            "image_url": {
                                "url": f"data:{_media_type(image_path)};base64,{encoded}",
                            },
                        },
                    ],
                },
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return []
        data = json.loads(content)
        return _unwrap_json_array(data)
    except Exception:
        logger.exception("Failed to parse vision LLM JSON response")
        return []


def extract_from_figure(image_path: Path, domain: str, client: OpenAI) -> list[dict]:
    """Extract schema-aligned rows from a figure using a vision model."""
    system = build_system_prompt(domain)
    user = (
        "Describe any tables, charts, or chemical structures visible in this figure. "
        "Then extract structured data rows that match the schema when values are visible. "
        "Return a JSON array of row objects."
    )

    raw_rows = _call_vision_json(client, system, user, image_path, OPENAI_VISION_MODEL)
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Extracted %d rows from figure %s for domain %s", len(rows), image_path, domain)
    return rows
