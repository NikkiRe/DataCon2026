from __future__ import annotations

import logging
from pathlib import Path

from chemx_extract.extraction.base import call_vision_text, normalize_row, parse_llm_json_content
from chemx_extract.extraction.prompts import build_system_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)


def extract_from_figure(
    image_path: Path,
    domain: str,
    ctx: ExtractionContext,
    *,
    draft_note: str = "",
) -> list[dict]:
    """Stage 2b: final structured extraction from figure (GPT-4o / Opus vision)."""
    route = ctx.route
    if route.final_vision_provider is None or route.final_vision_model is None:
        return []

    image_path = Path(image_path)
    system = build_system_prompt(domain)
    draft_block = f"\n\nDraft description from prior pass:\n{draft_note}" if draft_note.strip() else ""
    user = (
        "Extract structured data rows visible in this figure that match the schema. "
        f"Return ONLY a JSON array of row objects.{draft_block}"
    )

    client = ctx.client_for(route.final_vision_provider)
    vision_text = call_vision_text(
        route.final_vision_provider,
        client,
        system,
        user,
        image_path,
        route.final_vision_model,
        route.extract_max_tokens,
    )
    raw_rows = parse_llm_json_content(vision_text)
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info(
        "Extracted %d rows from figure %s via %s/%s",
        len(rows),
        image_path.name,
        route.final_vision_provider,
        route.final_vision_model,
    )
    return rows
