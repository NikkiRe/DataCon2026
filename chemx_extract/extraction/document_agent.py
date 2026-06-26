"""Single-pass extraction from full article content."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from chemx_extract.extraction.base import (
    call_anthropic_pdf_json,
    call_llm_json,
    normalize_row,
)
from chemx_extract.extraction.prompts import (
    build_chunk_user_prompt,
    build_document_user_prompt,
    build_system_prompt,
)
from chemx_extract.config import OPENAI_EXTRACT_MODEL
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 120_000
_MAX_CHUNK_CHARS = 28_000
_CHUNK_OVERLAP_CHARS = 1200
# Anthropic PDF API: large base64 payloads often yield prose instead of JSON.
MAX_PDF_DIRECT_BYTES = 1_500_000  # ~1.5 MB


def extract_from_document(
    content: str,
    domain: str,
    ctx: ExtractionContext,
    *,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    user_prompt: str | None = None,
) -> list[dict]:
    """One LLM call on full markdown + tables + figure descriptions."""
    if not content or not content.strip():
        return []

    route = ctx.route
    system = build_system_prompt(domain)
    trimmed = content.strip()
    if len(trimmed) > _MAX_CONTENT_CHARS:
        trimmed = trimmed[:_MAX_CONTENT_CHARS] + "\n\n[... truncated ...]"
    user = user_prompt or build_document_user_prompt(domain, trimmed)

    prov = provider or route.extract_provider
    mod = model or route.extract_model
    tokens = max_tokens or route.extract_max_tokens

    client = ctx.client_for(prov)  # type: ignore[arg-type]
    raw_rows = call_llm_json(prov, client, system, user, mod, tokens)  # type: ignore[arg-type]

    # Fallback: Anthropic rate-limited or bad JSON → try OpenAI in hybrid setups.
    if not raw_rows and prov == "anthropic" and ctx.openai_client is not None:
        logger.info("Anthropic extract failed; trying OpenAI")
        raw_rows = call_llm_json(
            "openai",
            ctx.openai_client,
            system,
            user,
            OPENAI_EXTRACT_MODEL,
            16000,
        )
        prov, mod = "openai", OPENAI_EXTRACT_MODEL

    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Document extract: %d rows via %s/%s", len(rows), prov, mod)
    return rows


def extract_from_pdf_direct(
    pdf_path: Path,
    domain: str,
    ctx: ExtractionContext,
) -> list[dict]:
    """Ultra-fast: single Anthropic PDF document call (task1 pattern)."""
    pdf_path = Path(pdf_path)
    route = ctx.route
    if route.extract_provider != "anthropic" or ctx.anthropic_client is None:
        logger.warning("PDF-direct mode requires Anthropic; skipping")
        return []

    size = pdf_path.stat().st_size
    if size > MAX_PDF_DIRECT_BYTES:
        logger.info(
            "PDF too large for pdf-direct (%.1f MB > %.1f MB): %s",
            size / 1e6,
            MAX_PDF_DIRECT_BYTES / 1e6,
            pdf_path.name,
        )
        return []

    system = build_system_prompt(domain)
    user = (
        f"Extract every experimental record from this article for domain '{domain}'. "
        "Return ONLY a JSON array of objects with the schema columns. "
        "No markdown, no explanation — raw JSON array only. "
        "Include all table rows; do not summarize."
    )
    raw_rows = call_anthropic_pdf_json(
        ctx.anthropic_client,
        system,
        user,
        pdf_path,
        route.extract_model,
        route.extract_max_tokens,
    )
    rows = [normalize_row(row, domain) for row in raw_rows]
    logger.info("PDF-direct extract: %d rows", len(rows))
    return rows


def _split_into_chunks(content: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split by page headers or size for multi-call extraction."""
    if len(content) <= max_chars:
        return [content]

    if "## Page" in content:
        parts = re.split(r"(?=^## Page \d+)", content, flags=re.MULTILINE)
        chunks: list[str] = []
        buffer = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(buffer) + len(part) + 2 <= max_chars:
                buffer = f"{buffer}\n\n{part}".strip() if buffer else part
            else:
                if buffer:
                    chunks.append(buffer)
                buffer = part if len(part) <= max_chars else part[:max_chars]
        if buffer:
            chunks.append(buffer)
        result = chunks if chunks else [content[:max_chars]]
    else:
        result = [content[i : i + max_chars] for i in range(0, len(content), max_chars)]

    if len(result) <= 1:
        return result

    overlapped: list[str] = [result[0]]
    for i in range(1, len(result)):
        tail = result[i - 1][-_CHUNK_OVERLAP_CHARS:].strip()
        prefix = f"[context from previous section — do not re-extract same rows]\n{tail}\n\n"
        overlapped.append(prefix + result[i])
    return overlapped


def extract_from_document_chunked(
    content: str,
    domain: str,
    ctx: ExtractionContext,
    *,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    verbose: bool = True,
) -> list[dict]:
    """Extract from long articles via multiple OpenAI calls (better row recall)."""
    from chemx_extract.pipeline_log import log_chunks, log_rows, stage

    chunks = _split_into_chunks(content.strip())
    if not chunks:
        return []

    if verbose and len(chunks) > 1:
        log_chunks(chunks)

    all_rows: list[dict] = []
    chunk_total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        if verbose and chunk_total > 1:
            stage(f"chunk {index}/{chunk_total} extract ({len(chunk):,} chars)...")
        user = (
            build_chunk_user_prompt(domain, chunk, chunk_index=index, chunk_total=chunk_total)
            if chunk_total > 1
            else None
        )
        rows = extract_from_document(
            chunk,
            domain,
            ctx,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            user_prompt=user,
        )
        if verbose and chunk_total > 1:
            log_rows(f"chunk {index}/{chunk_total} result", rows, domain, max_rows=3)
        all_rows.extend(rows)

    before_dedup = len(all_rows)
    seen: set[str] = set()
    unique: list[dict] = []
    for row in all_rows:
        key = str(sorted(row.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    if verbose and before_dedup != len(unique):
        stage(f"chunk dedup: {before_dedup} → {len(unique)} row(s) (-{before_dedup - len(unique)} duplicates)")

    return unique
