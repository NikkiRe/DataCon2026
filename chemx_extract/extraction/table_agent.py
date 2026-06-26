from __future__ import annotations

import logging

from chemx_extract.extraction.base import call_llm_json, normalize_row
from chemx_extract.extraction.prompts import build_system_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)


def extract_from_tables(
    tables: list[str],
    domain: str,
    ctx: ExtractionContext,
    *,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> list[dict]:
    """Structured extraction from raw tables."""
    if not tables:
        return []

    route = ctx.route
    prov = provider or route.extract_provider
    mod = model or route.extract_model
    tokens = max_tokens or route.extract_max_tokens

    system = build_system_prompt(domain)
    combined = "\n\n---\n\n".join(
        f"Table {index + 1}:\n{table.strip()}"
        for index, table in enumerate(tables)
        if table and table.strip()
    )
    if not combined:
        return []

    user = (
        "Extract ALL data rows from the following tables. "
        "One table row = one JSON object. Do NOT collapse or summarize rows. "
        "Return ONLY a JSON array with the schema columns.\n\n"
        f"{combined[:100_000]}"
    )

    client = ctx.client_for(prov)  # type: ignore[arg-type]
    raw_rows = call_llm_json(prov, client, system, user, mod, tokens)  # type: ignore[arg-type]
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Extracted %d rows from %d tables via %s/%s", len(rows), len(tables), prov, mod)
    return rows
