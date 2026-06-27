"""Second-pass verification of extracted records (task2 pattern)."""

from __future__ import annotations

import json
import logging

from chemx_extract.extraction.base import call_llm_json, normalize_row
from chemx_extract.extraction.prompts import build_verify_prompt
from chemx_extract.llm.routing import ExtractionContext

logger = logging.getLogger(__name__)

_VERIFY_SNIPPET = 12_000
_KEYWORD_MARKERS = (
    "photostab",
    "figure",
    "table",
    "cocrystal",
    "co-crystal",
    "coformer",
    "degrad",
    "uv",
    "nanosponge",
)


def _relevant_source_snippet(source_text: str, max_chars: int = _VERIFY_SNIPPET) -> str:
    """Build a verify excerpt: keyword lines first, then head + tail."""
    text = source_text.strip()
    if len(text) <= max_chars:
        return text

    keyword_blocks: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        low = line.lower()
        if not any(marker in low for marker in _KEYWORD_MARKERS):
            continue
        block = line.strip()
        if len(block) < 20 or len(block) > 800 or block in seen:
            continue
        seen.add(block)
        keyword_blocks.append(block)

    low_text = text.lower()
    for marker in _KEYWORD_MARKERS:
        start = 0
        while True:
            idx = low_text.find(marker, start)
            if idx == -1:
                break
            window = text[max(0, idx - 120) : min(len(text), idx + 280)].strip()
            if len(window) >= 20 and window not in seen:
                seen.add(window)
                keyword_blocks.append(window)
            start = idx + len(marker)

    if keyword_blocks:
        strong = ("photostab", "cocrystal", "co-crystal", "coformer", "degrad", "nanosponge")
        priority = [b for b in keyword_blocks if any(s in b.lower() for s in strong)]
        ordered = priority + [b for b in keyword_blocks if b not in priority]
        kw_text = "\n".join(ordered)[: max_chars // 2]
        remaining = max_chars - len(kw_text) - 2
        head_size = max(0, remaining // 2)
        tail_size = max(0, remaining - head_size)
        return f"{text[:head_size]}\n{kw_text}\n{text[-tail_size:]}"

    head_size = max_chars // 2
    tail_size = max_chars - head_size
    return f"{text[:head_size]}\n{text[-tail_size:]}"


def verify_records(
    records: list[dict],
    domain: str,
    source_text: str,
    ctx: ExtractionContext,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """Ask extract model to fix errors and remove duplicates."""
    if not records:
        return records

    route = ctx.route
    prov = provider or route.extract_provider
    mod = model or route.extract_model

    system = build_verify_prompt(domain)
    snippet = _relevant_source_snippet(source_text)
    user = f"""You extracted these records:

{json.dumps(records, indent=2, ensure_ascii=False)}

Check each record against the article excerpt below. Fix errors, remove duplicate rows,
add missing table rows. Return ONLY a corrected JSON array.

--- ARTICLE EXCERPT ---
{snippet}
--- END ---"""

    client = ctx.client_for(prov)  # type: ignore[arg-type]
    raw_rows = call_llm_json(prov, client, system, user, mod, route.extract_max_tokens)  # type: ignore[arg-type]
    if not raw_rows:
        return records

    verified = [normalize_row(row, domain) for row in raw_rows]
    logger.info("Verify pass: %d -> %d rows via %s/%s", len(records), len(verified), prov, mod)
    return verified
