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


def extract_from_tables(tables: list[str], domain: str, client: OpenAI) -> list[dict]:
    """Extract schema-aligned rows from markdown or text table representations."""
    if not tables:
        return []

    system = build_system_prompt(domain)
    combined = "\n\n---\n\n".join(
        f"Table {index + 1}:\n{table.strip()}"
        for index, table in enumerate(tables)
        if table and table.strip()
    )
    if not combined:
        return []

    user = (
        "Extract all data rows from the following tables. "
        "Return one JSON object per table row with the schema columns.\n\n"
        f"{combined}"
    )

    raw_rows = call_llm_json(client, system, user, OPENAI_MODEL)
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Extracted %d rows from %d tables for domain %s", len(rows), len(tables), domain)
    return rows
