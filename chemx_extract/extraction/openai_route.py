"""OpenAI-first LLM routing for quality extraction."""

from __future__ import annotations

from chemx_extract.config import OPENAI_EXTRACT_MODEL
from chemx_extract.llm.routing import ExtractionContext


def use_openai(ctx: ExtractionContext) -> bool:
    return ctx.openai_client is not None and ctx.route.mode in ("hybrid", "openai_only")


def openai_extract_model(_ctx: ExtractionContext) -> str:
    return OPENAI_EXTRACT_MODEL
