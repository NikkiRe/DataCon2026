"""Stage 1: cheap-model text compression / routing."""

from __future__ import annotations

import logging
import time

from chemx_extract.extraction.base import call_llm_text
from chemx_extract.extraction.prompts import build_compress_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)

# ~6–8k tokens per chunk to stay under typical 10k TPM limits
_CHUNK_CHARS = 18_000
_INTER_CHUNK_SLEEP = 65


def _chunk_text(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            break_at = text.rfind("\n\n", start, end)
            if break_at > start + size // 2:
                end = break_at
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def compress_text(markdown: str, domain: str, ctx: ExtractionContext) -> str:
    """Reduce article markdown to a fact sheet using the cheap tier (Haiku / GPT-4o-mini)."""
    if not markdown or not markdown.strip():
        return ""

    route = ctx.route
    system = build_compress_prompt(domain)
    client = ctx.client_for(route.compress_provider)

    chunks = _chunk_text(markdown.strip(), _CHUNK_CHARS)
    parts: list[str] = []

    for index, chunk in enumerate(chunks):
        if index > 0 and route.compress_provider == "anthropic":
            time.sleep(_INTER_CHUNK_SLEEP)
        user = (
            f"Compress part {index + 1}/{len(chunks)} of the article into a structured fact sheet. "
            "Keep all numeric values and chemical names exact.\n\n"
            f"{chunk}"
        )
        compressed = call_llm_text(
            route.compress_provider,
            client,
            system,
            user,
            route.compress_model,
            route.compress_max_tokens,
        )
        if compressed:
            parts.append(compressed)

    result = "\n\n".join(parts)
    logger.info(
        "Compressed text for %s via %s/%s (%d chars → %d chars, %d chunks)",
        domain,
        route.compress_provider,
        route.compress_model,
        len(markdown),
        len(result),
        len(chunks),
    )
    return result
