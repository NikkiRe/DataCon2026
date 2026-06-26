from __future__ import annotations

import logging

from openai import OpenAI

from chemx_extract.extraction.base import call_llm_json, normalize_row

try:
    from chemx_extract.config import OPENAI_MODEL
except ImportError:
    OPENAI_MODEL = "gpt-4.1-mini-2025-04-14"

from chemx_extract.extraction.prompts import build_system_prompt

logger = logging.getLogger(__name__)


def extract_from_text(markdown: str, domain: str, client: OpenAI) -> list[dict]:
    """Extract schema-aligned rows from article markdown text."""
    if not markdown or not markdown.strip():
        return []

    system = build_system_prompt(domain)
    user = (
        "Extract all relevant data rows from the following article text. "
        "Return one JSON object per distinct experimental record.\n\n"
        f"{markdown.strip()}"
    )

    raw_rows = call_llm_json(client, system, user, OPENAI_MODEL)
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Extracted %d rows from text for domain %s", len(rows), domain)
    return rows
