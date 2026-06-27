"""Merge main and supplementary PDF files."""

from __future__ import annotations

import shutil
from pathlib import Path


def merge_supplementary(
    main_pdf: Path,
    suppl_pdf: Path | None,
    out_path: Path,
) -> Path:
    """Concatenate main and supplementary PDFs, or copy main only when merge is unavailable."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if suppl_pdf is None:
        shutil.copy2(main_pdf, out_path)
        return out_path

    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for pdf in (main_pdf, suppl_pdf):
            reader = PdfReader(str(pdf))
            for page in reader.pages:
                writer.add_page(page)
        with out_path.open("wb") as f:
            writer.write(f)
        return out_path
    except ImportError:
        shutil.copy2(main_pdf, out_path)
        return out_path
