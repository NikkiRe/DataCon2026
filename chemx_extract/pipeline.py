"""End-to-end PDF extraction pipeline."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from chemx_extract.config import OPENAI_CHEAP_MODEL, OPENAI_EXTRACT_MODEL, OUTPUT_DIR
from chemx_extract.extraction.base import call_llm_text
from chemx_extract.extraction.prompts import build_compress_prompt
from chemx_extract.extraction.batch_vision import batch_describe_figures, inject_figure_descriptions
from chemx_extract.extraction.document_agent import (
    MAX_PDF_DIRECT_BYTES,
    extract_from_document,
    extract_from_document_chunked,
    extract_from_pdf_direct,
)
from chemx_extract.extraction.openai_route import openai_extract_model, use_openai
from chemx_extract.extraction.verify_agent import verify_records
from chemx_extract.llm.routing import ExtractionContext, build_extraction_context
from chemx_extract.merge.postprocess import merge_rows, postprocess_dataframe
from chemx_extract.merge.normalize import normalize_record
from chemx_extract.pipeline_log import (
    log_parse_summary,
    log_postprocess,
    log_row_delta,
    log_rows,
    stage,
    stage_header,
)
from chemx_extract.schemas import get_columns
from chemx_extract.smiles.resolver import resolve_smiles_fields

logger = logging.getLogger(__name__)

PipelineMode = Literal["fast", "pdf", "staged"]

try:
    from chemx_extract.preprocessing.pdf_parser import ParsedDocument, parse_pdf
except ImportError:
    logger.warning("preprocessing module unavailable; using PDF parser stub")

    @dataclass
    class ParsedDocument:
        pdf_name: str
        markdown: str
        tables: list[str]
        image_paths: list[Path]

    def parse_pdf(pdf_path: Path, work_dir: Path, *, use_cache: bool = True) -> ParsedDocument:
        return ParsedDocument(
            pdf_name=pdf_path.stem,
            markdown="",
            tables=[],
            image_paths=[],
        )

try:
    from chemx_extract.extraction.compress_agent import compress_text
    from chemx_extract.extraction.draft_vision_agent import draft_describe_figure
    from chemx_extract.extraction.figure_agent import extract_from_figure
    from chemx_extract.extraction.table_agent import extract_from_tables
    from chemx_extract.extraction.text_agent import extract_from_text
except ImportError:
    compress_text = None  # type: ignore[assignment]
    draft_describe_figure = None  # type: ignore[assignment]
    extract_from_figure = None  # type: ignore[assignment]
    extract_from_tables = None  # type: ignore[assignment]
    extract_from_text = None  # type: ignore[assignment]


def _rows_to_dataframe(
    rows: list[dict],
    domain: str,
    pdf_stem: str,
) -> pd.DataFrame:
    before = len(rows)
    columns = get_columns(domain)
    normalized = [normalize_record(row, domain) for row in rows]
    merged = merge_rows(normalized, domain)
    if len(merged) != before:
        stage(f"merge_rows: {before} → {len(merged)} row(s)")
        log_rows("after merge", merged, domain)

    resolved = [resolve_smiles_fields(row, domain) for row in merged]
    df = pd.DataFrame(resolved, columns=columns) if resolved else pd.DataFrame(columns=columns)
    df = postprocess_dataframe(df, domain)
    log_postprocess(merged, len(df), domain)
    df["pdf"] = pdf_stem

    if not df.empty:
        log_rows("FINAL output", df.to_dict(orient="records"), domain)
    return df


_COMPRESS_THRESHOLD = 120_000
_CHUNK_THRESHOLD = 30_000


def _openai_compress(content: str, domain: str, ctx: ExtractionContext) -> str:
    if not ctx.openai_client:
        return content
    system = build_compress_prompt(domain)
    user = (
        "Compress into a fact sheet. Copy EVERY table row verbatim. "
        "Keep all numbers, ratios, compound names, and experimental conditions.\n\n"
        f"{content[:100_000]}"
    )
    return call_llm_text(
        "openai",
        ctx.openai_client,
        system,
        user,
        OPENAI_CHEAP_MODEL,
        8192,
    )


def _openai_kwargs(ctx: ExtractionContext) -> dict:
    return {
        "provider": "openai",
        "model": openai_extract_model(ctx),
        "max_tokens": 16000,
    }


def _extract_fast(
    pdf_path: Path,
    domain: str,
    work_dir: Path,
    ctx: ExtractionContext,
    *,
    verify: bool = True,
) -> pd.DataFrame:
    pdf_mb = pdf_path.stat().st_size / 1e6
    stage_header("START", pdf=pdf_path.name, domain=domain, mode="fast", verify=verify)
    if oai := use_openai(ctx):
        stage(f"LLM route: OpenAI ({OPENAI_EXTRACT_MODEL})")
    else:
        stage(f"LLM route: Anthropic ({ctx.route.extract_model})")

    cache_hit = (work_dir / "converted.md").is_file()
    t0 = time.monotonic()
    parsed = parse_pdf(pdf_path, work_dir, use_cache=True)
    table_chars = sum(len(t) for t in parsed.tables)
    log_parse_summary(
        chars=len(parsed.markdown),
        images=len(parsed.image_paths),
        tables=len(parsed.tables),
        table_chars=table_chars,
        cached=cache_hit,
        pdf_mb=pdf_mb,
    )
    stage(f"parse time: {time.monotonic() - t0:.1f}s")

    content = parsed.markdown
    if parsed.image_paths:
        t1 = time.monotonic()
        stage_header("VISION", images=len(parsed.image_paths))
        descriptions = batch_describe_figures(parsed.image_paths, domain, ctx)
        content = inject_figure_descriptions(content, descriptions)
        stage(f"descriptions: {len(descriptions)} | time: {time.monotonic() - t1:.1f}s")
    else:
        stage("VISION skipped (no images)")

    oai_kw = _openai_kwargs(ctx) if oai else {}
    rows: list[dict] = []

    if parsed.tables and extract_from_tables:
        t1 = time.monotonic()
        stage_header("TABLE EXTRACT", tables=len(parsed.tables))
        for i, tbl in enumerate(parsed.tables[:3]):
            stage(f"  table[{i}] preview: {tbl[:120].replace(chr(10), ' ')}...")
        table_rows = extract_from_tables(parsed.tables, domain, ctx, **(oai_kw if oai else {}))
        log_rows("TABLE EXTRACT result", table_rows, domain)
        rows.extend(table_rows)
        stage(f"table extract time: {time.monotonic() - t1:.1f}s")
    elif not parsed.tables:
        stage("TABLE EXTRACT skipped (pdfplumber: 0 tables)")

    prose_len = len(content) - table_chars
    skip_compress = bool(parsed.tables) or prose_len <= _COMPRESS_THRESHOLD
    if oai and len(content) > _COMPRESS_THRESHOLD and not skip_compress:
        t1 = time.monotonic()
        stage_header("COMPRESS", in_chars=len(content), prose=prose_len)
        compressed = _openai_compress(content, domain, ctx)
        if compressed.strip():
            content = compressed
        stage(f"out_chars={len(content):,} | time: {time.monotonic() - t1:.1f}s")
    elif parsed.tables and len(content) > _COMPRESS_THRESHOLD:
        stage(f"COMPRESS skipped (tables={len(parsed.tables)}, prose={prose_len:,} chars)")

    t2 = time.monotonic()
    stage_header("TEXT EXTRACT", chars=len(content), chunked=len(content) > _CHUNK_THRESHOLD)
    if oai:
        if len(content) > _CHUNK_THRESHOLD:
            doc_rows = extract_from_document_chunked(content, domain, ctx, **oai_kw, verbose=True)
        else:
            doc_rows = extract_from_document(content, domain, ctx, **oai_kw)
            log_rows("TEXT EXTRACT result", doc_rows, domain)
    else:
        doc_rows = extract_from_document(content, domain, ctx)
        log_rows("TEXT EXTRACT result", doc_rows, domain)

    pre_merge = len(rows)
    rows.extend(doc_rows)
    if pre_merge and doc_rows:
        stage(f"combined table+text: {pre_merge} + {len(doc_rows)} = {len(rows)} row(s) before verify")
    stage(f"text extract time: {time.monotonic() - t2:.1f}s")

    if verify and rows:
        t3 = time.monotonic()
        stage_header("VERIFY", rows_in=len(rows))
        before_verify = list(rows)
        rows = verify_records(
            rows,
            domain,
            parsed.markdown,
            ctx,
            **({"provider": "openai", "model": oai_kw["model"]} if oai else {}),
        )
        log_row_delta(before_verify, rows, domain, "VERIFY")
        log_rows("VERIFY result", rows, domain)
        stage(f"verify time: {time.monotonic() - t3:.1f}s")
    elif not rows:
        stage("VERIFY skipped (no rows to verify)")
    elif not verify:
        stage("VERIFY skipped (--no-verify)")

    stage_header("POSTPROCESS")
    return _rows_to_dataframe(rows, domain, pdf_path.stem)


def _extract_pdf_direct(
    pdf_path: Path,
    domain: str,
    work_dir: Path,
    ctx: ExtractionContext,
) -> pd.DataFrame:
    size_mb = pdf_path.stat().st_size / 1e6
    if pdf_path.stat().st_size > MAX_PDF_DIRECT_BYTES:
        stage(
            f"PDF-direct skipped — {size_mb:.1f} MB > {MAX_PDF_DIRECT_BYTES / 1e6:.1f} MB → fast mode"
        )
        return _extract_fast(pdf_path, domain, work_dir, ctx, verify=False)

    stage_header("PDF-DIRECT", size_mb=f"{size_mb:.1f}")
    t0 = time.monotonic()
    rows = extract_from_pdf_direct(pdf_path, domain, ctx)
    log_rows("PDF-DIRECT result", rows, domain)
    stage(f"pdf-direct time: {time.monotonic() - t0:.1f}s")
    if not rows:
        stage("PDF-direct empty → falling back to fast mode")
        return _extract_fast(pdf_path, domain, work_dir, ctx, verify=False)
    return _rows_to_dataframe(rows, domain, pdf_path.stem)


def _extract_staged(
    pdf_path: Path,
    domain: str,
    work_dir: Path,
    ctx: ExtractionContext,
) -> pd.DataFrame:
    if compress_text is None:
        return _extract_fast(pdf_path, domain, work_dir, ctx)

    stage_header("STAGED", pdf=pdf_path.name)
    parsed = parse_pdf(pdf_path, work_dir)
    rows: list[dict] = []
    compressed = compress_text(parsed.markdown, domain, ctx)

    figure_draft_notes: list[str] = []
    if draft_describe_figure and extract_from_figure:
        for image_path in parsed.image_paths[:10]:
            image_path = Path(image_path)
            draft = draft_describe_figure(image_path, domain, ctx)
            if draft.strip():
                figure_draft_notes.append(f"### {image_path.name}\n{draft}")
            fig_rows = extract_from_figure(image_path, domain, ctx, draft_note=draft)
            rows.extend(fig_rows)

    figure_notes = "\n\n".join(figure_draft_notes)

    if extract_from_tables:
        rows.extend(extract_from_tables(parsed.tables, domain, ctx))
    if extract_from_text:
        rows.extend(extract_from_text(compressed, domain, ctx, figure_notes=figure_notes))

    if rows:
        before = list(rows)
        rows = verify_records(rows, domain, parsed.markdown, ctx)
        log_row_delta(before, rows, domain, "STAGED verify")

    return _rows_to_dataframe(rows, domain, pdf_path.stem)


def extract_from_pdf(
    pdf_path: Path,
    domain: str,
    work_dir: Path | None = None,
    ctx: ExtractionContext | None = None,
    *,
    mode: PipelineMode = "fast",
    verify: bool = True,
) -> pd.DataFrame:
    pdf_path = Path(pdf_path)

    if work_dir is None:
        work_dir = OUTPUT_DIR / pdf_path.stem
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if ctx is None:
        ctx = build_extraction_context()

    logger.info("Pipeline mode=%s domain=%s pdf=%s", mode, domain, pdf_path.name)

    if mode == "pdf":
        return _extract_pdf_direct(pdf_path, domain, work_dir, ctx)
    if mode == "staged":
        return _extract_staged(pdf_path, domain, work_dir, ctx)
    return _extract_fast(pdf_path, domain, work_dir, ctx, verify=verify)
