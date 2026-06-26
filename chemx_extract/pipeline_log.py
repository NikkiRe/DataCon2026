"""Structured stage logging for pipeline debugging and tuning."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from chemx_extract.config import NOT_DETECTED
from chemx_extract.schemas import get_columns

_PREVIEW_LEN = 72


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def stage(msg: str) -> None:
    print(f"  [{_ts()}] {msg}", flush=True)


def stage_header(name: str, **meta: Any) -> None:
    parts = " | ".join(f"{k}={v}" for k, v in meta.items())
    stage(f"── {name} ── {parts}" if parts else f"── {name} ──")


def _preview(value: object) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) > _PREVIEW_LEN:
        return text[: _PREVIEW_LEN - 3] + "..."
    return text


def field_fill_stats(rows: list[dict], domain: str) -> dict[str, str]:
    """Per-column fill rate (non-NOT_DETECTED)."""
    cols = get_columns(domain)
    if not rows:
        return {c: "0/0" for c in cols}
    stats: dict[str, str] = {}
    n = len(rows)
    for col in cols:
        filled = sum(
            1
            for r in rows
            if col in r and r[col] not in (None, "", NOT_DETECTED)
        )
        stats[col] = f"{filled}/{n}"
    return stats


def log_rows(label: str, rows: list[dict], domain: str, *, max_rows: int = 5) -> None:
    """Log row count, field fill rates, and sample rows."""
    cols = get_columns(domain)
    stage(f"{label}: {len(rows)} row(s)")
    if not rows:
        stage(f"  (empty — no records at this stage)")
        return

    stats = field_fill_stats(rows, domain)
    low = [c for c, s in stats.items() if s.startswith("0/")]
    ok = [c for c, s in stats.items() if not s.startswith("0/")]
    if ok:
        stage(f"  filled fields: {', '.join(f'{c}={stats[c]}' for c in ok)}")
    if low:
        stage(f"  empty fields:  {', '.join(low)}")

    for i, row in enumerate(rows[:max_rows]):
        parts = [f"{c}={_preview(row.get(c, NOT_DETECTED))}" for c in cols[:4]]
        extra = len(cols) - 4
        suffix = f" (+{extra} cols)" if extra > 0 else ""
        stage(f"  row[{i}]: {' | '.join(parts)}{suffix}")
    if len(rows) > max_rows:
        stage(f"  ... +{len(rows) - max_rows} more row(s)")


def log_row_delta(before: list[dict], after: list[dict], domain: str, label: str) -> None:
    """Compare row counts and highlight verify/merge changes."""
    stage(
        f"{label}: {len(before)} → {len(after)} row(s) "
        f"({'+' if len(after) >= len(before) else ''}{len(after) - len(before)})"
    )
    if len(before) == len(after):
        return
    if len(after) < len(before):
        stage(f"  ⚠ lost {len(before) - len(after)} row(s) — check verify/dedup")
    else:
        stage(f"  + gained {len(after) - len(before)} row(s)")


def log_parse_summary(
    *,
    chars: int,
    images: int,
    tables: int,
    table_chars: int,
    cached: bool,
    pdf_mb: float,
) -> None:
    stage_header("PARSE", pdf=f"{pdf_mb:.1f}MB", cache="hit" if cached else "miss")
    stage(f"text={chars:,} chars | images={images} | pdfplumber_tables={tables} ({table_chars:,} chars)")
    if tables == 0 and chars > 10_000:
        stage("  ⚠ pdfplumber found 0 tables — data may be in prose only")
    if images == 0 and chars > 10_000:
        stage("  ⚠ no figure images extracted — vision stage skipped")


def log_chunks(chunks: list[str]) -> None:
    stage(f"split into {len(chunks)} chunk(s):")
    for i, ch in enumerate(chunks):
        stage(f"  chunk[{i}]: {len(ch):,} chars | start: {_preview(ch[:120])}")


def log_postprocess(before: list[dict], df_rows: int, domain: str) -> None:
    stage_header("POSTPROCESS", rows_in=len(before), rows_out=df_rows)
    if df_rows < len(before):
        stage(f"  dedup/merge removed {len(before) - df_rows} row(s)")
