from __future__ import annotations

import logging

from chemx_extract.extraction.base import call_llm_json, normalize_row
from chemx_extract.extraction.prompts import build_system_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)


def extract_from_tables(tables: list[str], domain: str, ctx: ExtractionContext) -> list[dict]:
    """Stage 2: structured extraction from raw tables (Opus / GPT-4.1)."""
    if not tables:
        return []

    route = ctx.route
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
        "Return ONLY a JSON array — one object per table row with the schema columns.\n\n"
        f"{combined}"
    )

    client = ctx.client_for(route.extract_provider)
    raw_rows = call_llm_json(
        route.extract_provider,
        client,
        system,
        user,
        route.extract_model,
        route.extract_max_tokens,
    )
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info(
        "Extracted %d rows from %d tables via %s/%s",
        len(rows),
        len(tables),
        route.extract_provider,
        route.extract_model,
    )
    return rows
