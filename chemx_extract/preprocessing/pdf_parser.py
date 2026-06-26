"""PDF parsing: marker-pdf with pdfplumber fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from chemx_extract.preprocessing.tables import extract_tables_pdfplumber

logger = logging.getLogger(__name__)

_MAX_IMAGE_PAGES = 50
_IMAGE_DPI = 150
_MAX_VISION_PAGES = 8


@dataclass
class ParsedDocument:
    pdf_name: str
    markdown: str
    tables: list[str]
    image_paths: list[Path]


def _extract_text_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                parts.append(f"## Page {i}\n\n{text.strip()}")
    return "\n\n".join(parts)


def _try_marker(pdf_path: Path, work_dir: Path) -> tuple[str, list[Path]] | None:
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
    except ImportError:
        return None

    try:
        converter = PdfConverter(artifact_dict=create_model_dict())
        rendered = converter(str(pdf_path))
    except Exception as exc:
        logger.warning("marker-pdf conversion failed for %s: %s", pdf_path, exc)
        return None

    markdown = getattr(rendered, "markdown", "") or ""
    image_paths: list[Path] = []

    images_dir = work_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    raw_images = getattr(rendered, "images", None)
    if raw_images:
        for name, image in raw_images.items():
            dest = images_dir / Path(str(name)).name
            try:
                if hasattr(image, "save"):
                    image.save(dest)
                elif isinstance(image, bytes):
                    dest.write_bytes(image)
                else:
                    continue
                image_paths.append(dest)
            except Exception as exc:
                logger.warning("Failed to save marker image %s: %s", name, exc)

    if image_paths:
        return markdown, image_paths

    if images_dir.is_dir():
        for path in sorted(images_dir.iterdir()):
            if path.is_file():
                image_paths.append(path)

    return markdown, image_paths


def _render_pages_pdf2image(pdf_path: Path, work_dir: Path, *, max_pages: int = _MAX_VISION_PAGES) -> list[Path]:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return []

    images_dir = work_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        pages = convert_from_path(
            str(pdf_path),
            dpi=_IMAGE_DPI,
            first_page=1,
            last_page=min(max_pages, _MAX_IMAGE_PAGES),
        )
    except Exception as exc:
        logger.warning("pdf2image conversion failed for %s: %s", pdf_path, exc)
        return []

    paths: list[Path] = []
    for i, page_image in enumerate(pages, start=1):
        dest = images_dir / f"page_{i:03d}.png"
        page_image.save(dest, format="PNG")
        paths.append(dest)
    return paths


def _append_tables_to_markdown(markdown: str, tables: list[str]) -> str:
    if not tables:
        return markdown
    blocks = "\n\n".join(tables)
    if markdown.strip():
        return f"{markdown.strip()}\n\n{blocks}"
    return blocks


def parse_pdf(pdf_path: Path, work_dir: Path, *, use_cache: bool = True) -> ParsedDocument:
    """Parse a PDF into markdown, tables, and optional page images."""
    work_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.name
    cache_md = work_dir / "converted.md"

    if use_cache and cache_md.is_file() and cache_md.stat().st_size > 100:
        markdown = cache_md.read_text(encoding="utf-8")
        images_dir = work_dir / "images"
        image_paths = (
            sorted(p for p in images_dir.iterdir() if p.is_file())
            if images_dir.is_dir()
            else []
        )
        if not image_paths:
            image_paths = _render_pages_pdf2image(pdf_path, work_dir)
        tables = extract_tables_pdfplumber(pdf_path)
        return ParsedDocument(
            pdf_name=pdf_name,
            markdown=markdown,
            tables=tables,
            image_paths=image_paths,
        )

    marker_result = _try_marker(pdf_path, work_dir)
    if marker_result is not None:
        markdown, image_paths = marker_result
        if not markdown.strip():
            markdown = _extract_text_pdfplumber(pdf_path)
    else:
        markdown = _extract_text_pdfplumber(pdf_path)
        image_paths = []

    tables = extract_tables_pdfplumber(pdf_path)
    markdown = _append_tables_to_markdown(markdown, tables)

    if not image_paths:
        image_paths = _render_pages_pdf2image(pdf_path, work_dir)

    cache_md.write_text(markdown, encoding="utf-8")

    return ParsedDocument(
        pdf_name=pdf_name,
        markdown=markdown,
        tables=tables,
        image_paths=image_paths,
    )
