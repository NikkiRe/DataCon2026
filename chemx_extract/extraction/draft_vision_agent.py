"""Stage 1b: cheap vision draft descriptions."""

from __future__ import annotations

import logging
from pathlib import Path

from chemx_extract.extraction.base import call_vision_text
from chemx_extract.extraction.prompts import PROMPT_DESCRIPTION
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)

_DRAFT_SYSTEM = (
    f"{PROMPT_DESCRIPTION}\n\n"
    "Describe this figure for chemical data extraction. Include:\n"
    "- Visible table cells with exact values and headers\n"
    "- Chart axis labels, units, and readable data points\n"
    "- Chemical structure labels and compound names\n"
    "- Figure/table caption text if visible\n"
    "Be factual and concise. Do not invent values."
)


def draft_describe_figure(
    image_path: Path,
    domain: str,
    ctx: ExtractionContext,
) -> str:
    """Draft figure description via GPT-4o-mini (or Haiku vision fallback)."""
    route = ctx.route
    if route.draft_vision_provider is None or route.draft_vision_model is None:
        return ""

    image_path = Path(image_path)
    user = f"Domain: {domain}. Describe all extractable chemical data visible in this figure."

    client = ctx.client_for(route.draft_vision_provider)
    description = call_vision_text(
        route.draft_vision_provider,
        client,
        _DRAFT_SYSTEM,
        user,
        image_path,
        route.draft_vision_model,
        route.compress_max_tokens,
    )
    logger.info("Draft vision for %s: %d chars", image_path.name, len(description))
    return description
