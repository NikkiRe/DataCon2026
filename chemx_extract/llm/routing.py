"""Model routing with Anthropic/OpenAI fallback tiers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from chemx_extract.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_CHEAP_MAX_TOKENS,
    ANTHROPIC_CHEAP_MODEL,
    ANTHROPIC_EXTRACT_MODEL,
    ANTHROPIC_MAX_TOKENS,
    OPENAI_API_KEY,
    OPENAI_CHEAP_MODEL,
    OPENAI_DRAFT_VISION_MODEL,
    OPENAI_EXTRACT_MODEL,
    OPENAI_VISION_MODEL,
)
from chemx_extract.exceptions import NoLLMProviderError
from chemx_extract.llm.clients import get_anthropic_client, get_openai_client

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai"]


@dataclass(frozen=True)
class ModelRoute:
    """Resolved model assignments for one extraction run."""

    mode: Literal["hybrid", "anthropic_only", "openai_only"]
    compress_provider: Provider
    compress_model: str
    compress_max_tokens: int
    extract_provider: Provider
    extract_model: str
    extract_max_tokens: int
    draft_vision_provider: Provider | None
    draft_vision_model: str | None
    final_vision_provider: Provider | None
    final_vision_model: str | None


@dataclass
class ExtractionContext:
    """Active clients + resolved route for the pipeline."""

    route: ModelRoute
    anthropic_client: Any | None
    openai_client: Any | None

    def client_for(self, provider: Provider) -> Any:
        client = self.anthropic_client if provider == "anthropic" else self.openai_client
        if client is None:
            raise RuntimeError(f"{provider} client is not available")
        return client


def resolve_route() -> ModelRoute:
    """Pick models: hybrid when both keys present, else single-provider fallback."""
    has_anthropic = bool(ANTHROPIC_API_KEY)
    has_openai = bool(OPENAI_API_KEY)

    if not has_anthropic and not has_openai:
        raise NoLLMProviderError(
            "Configure at least one of ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
        )

    if has_anthropic and has_openai:
        logger.info("LLM route: hybrid (Haiku → GPT-4o-mini → Opus → GPT-4o)")
        return ModelRoute(
            mode="hybrid",
            compress_provider="anthropic",
            compress_model=ANTHROPIC_CHEAP_MODEL,
            compress_max_tokens=ANTHROPIC_CHEAP_MAX_TOKENS,
            extract_provider="anthropic",
            extract_model=ANTHROPIC_EXTRACT_MODEL,
            extract_max_tokens=ANTHROPIC_MAX_TOKENS,
            draft_vision_provider="openai",
            draft_vision_model=OPENAI_DRAFT_VISION_MODEL,
            final_vision_provider="openai",
            final_vision_model=OPENAI_VISION_MODEL,
        )

    if has_anthropic:
        logger.info("LLM route: anthropic_only (Haiku → Opus, vision via Opus)")
        return ModelRoute(
            mode="anthropic_only",
            compress_provider="anthropic",
            compress_model=ANTHROPIC_CHEAP_MODEL,
            compress_max_tokens=ANTHROPIC_CHEAP_MAX_TOKENS,
            extract_provider="anthropic",
            extract_model=ANTHROPIC_EXTRACT_MODEL,
            extract_max_tokens=ANTHROPIC_MAX_TOKENS,
            draft_vision_provider="anthropic",
            draft_vision_model=ANTHROPIC_CHEAP_MODEL,
            final_vision_provider="anthropic",
            final_vision_model=ANTHROPIC_EXTRACT_MODEL,
        )

    logger.info("LLM route: openai_only (GPT-4o-mini → GPT-4.1 → GPT-4o)")
    return ModelRoute(
        mode="openai_only",
        compress_provider="openai",
        compress_model=OPENAI_CHEAP_MODEL,
        compress_max_tokens=8192,
        extract_provider="openai",
        extract_model=OPENAI_EXTRACT_MODEL,
        extract_max_tokens=16000,
        draft_vision_provider="openai",
        draft_vision_model=OPENAI_DRAFT_VISION_MODEL,
        final_vision_provider="openai",
        final_vision_model=OPENAI_VISION_MODEL,
    )


def build_extraction_context() -> ExtractionContext:
    """Build clients and route; raises NoLLMProviderError if no API keys."""
    route = resolve_route()
    anthropic_client = get_anthropic_client()
    openai_client = get_openai_client()

    if route.compress_provider == "anthropic" and anthropic_client is None:
        raise NoLLMProviderError("ANTHROPIC_API_KEY set but anthropic package/client failed")
    if route.compress_provider == "openai" and openai_client is None:
        raise NoLLMProviderError("OPENAI_API_KEY set but openai package/client failed")

    return ExtractionContext(
        route=route,
        anthropic_client=anthropic_client,
        openai_client=openai_client,
    )
