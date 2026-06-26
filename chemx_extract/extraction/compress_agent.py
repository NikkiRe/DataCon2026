"""Stage 1: cheap-model text compression / routing."""

from __future__ import annotations

import logging

from chemx_extract.extraction.base import call_llm_text
from chemx_extract.extraction.prompts import build_compress_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)


def compress_text(markdown: str, domain: str, ctx: ExtractionContext) -> str:
    """Reduce article markdown to a fact sheet using the cheap tier (Haiku / GPT-4o-mini)."""
    if not markdown or not markdown.strip():
        return ""

    route = ctx.route
    system = build_compress_prompt(domain)
    user = (
        "Compress the following article text into a structured fact sheet. "
        "Keep all numeric values and chemical names exact.\n\n"
        f"{markdown.strip()}"
    )

    client = ctx.client_for(route.compress_provider)
    compressed = call_llm_text(
        route.compress_provider,
        client,
        system,
        user,
        route.compress_model,
        route.compress_max_tokens,
    )
    logger.info(
        "Compressed text for %s via %s/%s (%d → %d chars)",
        domain,
        route.compress_provider,
        route.compress_model,
        len(markdown),
        len(compressed),
    )
    return compressed
