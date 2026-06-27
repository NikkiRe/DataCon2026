"""PDF parsing: marker-pdf with pdfplumber fallback."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from chemx_extract.preprocessing.tables import extract_tables_pdfplumber

logger = logging.getLogger(__name__)

_MAX_IMAGE_PAGES = 50
_IMAGE_DPI = 150
_MAX_VISION_PAGES = 4


@dataclass
class ParsedDocument:
    pdf_name: str
    markdown: str
    tables: list[str]
    image_paths: list[Path]
    image_source: str = "none"


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


def _vision_page_numbers(pdf_path: Path, *, max_pages: int = _MAX_VISION_PAGES) -> list[int]:
    """Select pages with figure/chart captions; prefer photostability/results figures."""
    import pdfplumber

    candidates: list[tuple[int, int]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not re.search(r"figure\s*\d|fig\.\s*\d|chart\s*\d", text, re.I):
                    continue
                low = text.lower()
                priority = 0
                if "photostab" in low or "degrad" in low or "uv" in low:
                    priority += 20
                fig_nums = [
                    int(m.group(1))
                    for m in re.finditer(r"(?:figure|fig\.|chart)\s*(\d+)", text, re.I)
                ]
                if fig_nums:
                    priority += max(fig_nums)
                candidates.append((priority, i))
    except Exception as exc:
        logger.warning("vision page scan failed for %s: %s", pdf_path, exc)
        return [1]

    if not candidates:
        return [1]

    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = sorted({page for _, page in candidates[:max_pages]})
    return selected


def _render_pages_pdf2image(
    pdf_path: Path,
    work_dir: Path,
    *,
    page_numbers: list[int] | None = None,
) -> list[Path]:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return []

    images_dir = work_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    pages = page_numbers or list(range(1, _MAX_VISION_PAGES + 1))

    paths: list[Path] = []
    for page_num in pages[:_MAX_VISION_PAGES]:
        try:
            rendered = convert_from_path(
                str(pdf_path),
                dpi=_IMAGE_DPI,
                first_page=page_num,
                last_page=page_num,
            )
        except Exception as exc:
            logger.warning("pdf2image page %d failed for %s: %s", page_num, pdf_path, exc)
            continue
        if not rendered:
            continue
        dest = images_dir / f"page_{page_num:03d}.png"
        rendered[0].save(dest, format="PNG")
        paths.append(dest)
    return paths


def _render_pages_pymupdf(
    pdf_path: Path,
    work_dir: Path,
    *,
    page_numbers: list[int] | None = None,
) -> list[Path]:
    try:
        import fitz  # pymupdf
    except ImportError:
        return []

    images_dir = work_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    pages = page_numbers or _vision_page_numbers(pdf_path)

    paths: list[Path] = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in pages[:_MAX_VISION_PAGES]:
            if page_num < 1 or page_num > doc.page_count:
                continue
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=_IMAGE_DPI)
            dest = images_dir / f"page_{page_num:03d}.png"
            pix.save(dest)
            paths.append(dest)
        doc.close()
    except Exception as exc:
        logger.warning("pymupdf render failed for %s: %s", pdf_path, exc)
        return []
    return paths


def _render_page_images(pdf_path: Path, work_dir: Path) -> tuple[list[Path], str]:
    """Render PDF pages to PNG; return paths and method used."""
    page_nums = _vision_page_numbers(pdf_path)
    paths = _render_pages_pdf2image(pdf_path, work_dir, page_numbers=page_nums)
    if paths:
        return paths, f"pdf2image({len(paths)} pages)"

    paths = _render_pages_pymupdf(pdf_path, work_dir, page_numbers=page_nums)
    if paths:
        return paths, f"pymupdf({len(paths)} pages)"

    return [], "none"


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
    image_source = "none"

    if use_cache and cache_md.is_file() and cache_md.stat().st_size > 100:
        markdown = cache_md.read_text(encoding="utf-8")
        images_dir = work_dir / "images"
        image_paths = (
            sorted(p for p in images_dir.iterdir() if p.is_file())
            if images_dir.is_dir()
            else []
        )
        if image_paths:
            image_source = "cache"
        elif not image_paths:
            image_paths, image_source = _render_page_images(pdf_path, work_dir)
        tables = extract_tables_pdfplumber(pdf_path)
        return ParsedDocument(
            pdf_name=pdf_name,
            markdown=markdown,
            tables=tables,
            image_paths=image_paths,
            image_source=image_source,
        )

    marker_result = _try_marker(pdf_path, work_dir)
    if marker_result is not None:
        markdown, image_paths = marker_result
        image_source = "marker" if image_paths else "none"
        if not markdown.strip():
            markdown = _extract_text_pdfplumber(pdf_path)
    else:
        markdown = _extract_text_pdfplumber(pdf_path)
        image_paths = []

    tables = extract_tables_pdfplumber(pdf_path)
    markdown = _append_tables_to_markdown(markdown, tables)

    if not image_paths:
        image_paths, image_source = _render_page_images(pdf_path, work_dir)

    cache_md.write_text(markdown, encoding="utf-8")

    return ParsedDocument(
        pdf_name=pdf_name,
        markdown=markdown,
        tables=tables,
        image_paths=image_paths,
        image_source=image_source,
    )
