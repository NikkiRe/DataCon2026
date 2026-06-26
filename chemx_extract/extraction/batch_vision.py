"""Batch figure description in a single vision call (task2 pattern)."""

from __future__ import annotations

import logging
from pathlib import Path

from chemx_extract.extraction.base import call_anthropic_vision_batch, call_vision_text
from chemx_extract.extraction.prompts import PROMPT_DESCRIPTION
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)

_MAX_BATCH_IMAGES = 12

_BATCH_SYSTEM = (
    f"{PROMPT_DESCRIPTION}\n\n"
    "Describe chemical data visible in each figure for extraction."
)

_BATCH_USER_SUFFIX = (
    "For each image above, describe all chemical structures, tables, and data visible. "
    "Include molecule names, SMILES if shown, numerical values, units, and labels. "
    "Format:\nImage 1: <description>\nImage 2: <description>\netc."
)


def batch_describe_figures(
    image_paths: list[Path],
    domain: str,
    ctx: ExtractionContext,
) -> dict[str, str]:
    """Describe up to N figures in one cheap vision call; fallback to per-image."""
    route = ctx.route
    if route.draft_vision_provider is None or route.draft_vision_model is None:
        return {}

    paths = [Path(p) for p in image_paths[:_MAX_BATCH_IMAGES]]
    if not paths:
        return {}

    if route.draft_vision_provider == "anthropic" and len(paths) > 1:
        client = ctx.client_for("anthropic")
        descriptions = call_anthropic_vision_batch(
            client,
            _BATCH_SYSTEM,
            paths,
            _BATCH_USER_SUFFIX,
            route.draft_vision_model,
            route.compress_max_tokens,
        )
        if descriptions:
            logger.info("Batch vision described %d images", len(descriptions))
            return descriptions

    # Fallback: one call per image
    result: dict[str, str] = {}
    user = f"Domain: {domain}. Describe all extractable chemical data visible in this figure."
    client = ctx.client_for(route.draft_vision_provider)
    for path in paths:
        text = call_vision_text(
            route.draft_vision_provider,
            client,
            _BATCH_SYSTEM,
            user,
            path,
            route.draft_vision_model,
            route.compress_max_tokens,
        )
        result[str(path)] = text
    return result


def inject_figure_descriptions(markdown: str, descriptions: dict[str, str]) -> str:
    """Insert figure descriptions into markdown (ChemX described.md style)."""
    result = markdown
    for path, desc in descriptions.items():
        if not desc.strip():
            continue
        filename = Path(path).name
        tag = f"<DESCRIPTION_FROM_IMAGE>\n{desc.strip()}\n</DESCRIPTION_FROM_IMAGE>"
        for pattern in (f"![]({filename})", f"![](./{filename})", f"![image]({filename})"):
            if pattern in result:
                result = result.replace(pattern, tag)
                break
        else:
            result += f"\n\n### Figure {filename}\n{tag}\n"
    return result
