"""Factory helpers for hybrid Anthropic + OpenAI clients."""

from __future__ import annotations

import logging

from chemx_extract.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def get_anthropic_client():
    """Return Anthropic client for text/table extraction, or None if unavailable."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic

        return Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic package not installed")
        return None


def get_openai_client():
    """Return OpenAI client for vision extraction, or None if unavailable."""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.warning("openai package not installed")
        return None
