"""End-to-end PDF extraction pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from chemx_extract.config import OUTPUT_DIR
from chemx_extract.extraction.compress_agent import compress_text
from chemx_extract.extraction.draft_vision_agent import draft_describe_figure
from chemx_extract.llm.routing import ExtractionContext, build_extraction_context
from chemx_extract.merge.postprocess import merge_rows, postprocess_dataframe
from chemx_extract.schemas import get_columns
from chemx_extract.smiles.resolver import resolve_smiles_fields

logger = logging.getLogger(__name__)

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

    def parse_pdf(pdf_path: Path, work_dir: Path) -> ParsedDocument:
        return ParsedDocument(
            pdf_name=pdf_path.stem,
            markdown="",
            tables=[],
            image_paths=[],
        )

try:
    from chemx_extract.extraction.figure_agent import extract_from_figure
    from chemx_extract.extraction.table_agent import extract_from_tables
    from chemx_extract.extraction.text_agent import extract_from_text
except ImportError:
    logger.warning("extraction module unavailable; using extraction stubs")

    def extract_from_tables(tables, domain, ctx):  # type: ignore[no-untyped-def]
        return []

    def extract_from_text(text, domain, ctx, **kwargs):  # type: ignore[no-untyped-def]
        return []

    def extract_from_figure(image_path, domain, ctx, **kwargs):  # type: ignore[no-untyped-def]
        return []


def extract_from_pdf(
    pdf_path: Path,
    domain: str,
    work_dir: Path | None = None,
    ctx: ExtractionContext | None = None,
) -> pd.DataFrame:
    """
    Staged extraction pipeline:
      1.  Haiku / GPT-4o-mini — compress article text
      1b. GPT-4o-mini — draft figure descriptions
      2.  Opus / GPT-4.1 — structured JSON from tables + compressed text
      2b. GPT-4o — structured JSON from figures
    """
    pdf_path = Path(pdf_path)
    columns = get_columns(domain)

    if work_dir is None:
        work_dir = OUTPUT_DIR / pdf_path.stem
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if ctx is None:
        ctx = build_extraction_context()

    parsed = parse_pdf(pdf_path, work_dir)
    rows: list[dict] = []

    # Stage 1: compress prose (tables stay raw)
    compressed = compress_text(parsed.markdown, domain, ctx)

    # Stage 1b + 2b: figures — draft then final vision extraction
    figure_draft_notes: list[str] = []
    for image_path in parsed.image_paths[:10]:
        image_path = Path(image_path)
        draft = draft_describe_figure(image_path, domain, ctx)
        if draft.strip():
            figure_draft_notes.append(f"### {image_path.name}\n{draft}")
        rows.extend(extract_from_figure(image_path, domain, ctx, draft_note=draft))

    figure_notes = "\n\n".join(figure_draft_notes)

    # Stage 2: structured extraction from tables + compressed text
    rows.extend(extract_from_tables(parsed.tables, domain, ctx))
    rows.extend(extract_from_text(compressed, domain, ctx, figure_notes=figure_notes))

    merged = merge_rows(rows, domain)
    resolved = [resolve_smiles_fields(row, domain) for row in merged]
    df = pd.DataFrame(resolved, columns=columns) if resolved else pd.DataFrame(columns=columns)
    df = postprocess_dataframe(df, domain)
    df["pdf"] = pdf_path.stem
    return df
