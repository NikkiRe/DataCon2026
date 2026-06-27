from __future__ import annotations

import logging

from chemx_extract.extraction.base import call_llm_json, normalize_row
from chemx_extract.extraction.prompts import build_system_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)


def extract_from_text(
    text: str,
    domain: str,
    ctx: ExtractionContext,
    *,
    figure_notes: str = "",
) -> list[dict]:
    """Stage 2: structured extraction from compressed text + optional figure drafts."""
    if not text or not text.strip():
        if not figure_notes.strip():
            return []

    route = ctx.route
    system = build_system_prompt(domain)
    parts = []
    if text and text.strip():
        parts.append("## Compressed article facts\n" + text.strip())
    if figure_notes.strip():
        parts.append("## Figure draft notes\n" + figure_notes.strip())

    user = (
        "Extract all relevant data rows from the content below. "
        "Return ONLY a JSON array — one object per distinct experimental record.\n\n"
        + "\n\n".join(parts)
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
        "Extracted %d rows from text via %s/%s",
        len(rows),
        route.extract_provider,
        route.extract_model,
    )
    return rows
