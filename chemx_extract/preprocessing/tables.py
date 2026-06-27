"""PDF table extraction via pdfplumber."""

from __future__ import annotations

from pathlib import Path

_TABLE_SETTINGS: tuple[dict | None, ...] = (
    None,
    {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_tolerance": 5,
    },
    {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_tolerance": 5,
    },
)


def _table_to_markdown(table: list[list[str | None]]) -> str:
    if not table:
        return ""

    rows: list[list[str]] = []
    for row in table:
        cells = [str(cell).strip() if cell is not None else "" for cell in row]
        rows.append(cells)

    if not rows:
        return ""

    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def _dedupe_tables(tables: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for table in tables:
        key = table.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(table)
    return unique


def extract_tables_pdfplumber(pdf_path: Path) -> list[str]:
    """Extract tables from a PDF as markdown blocks prefixed with ``## Table N``."""
    import pdfplumber

    raw_tables: list[str] = []
    table_num = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for settings in _TABLE_SETTINGS:
                kwargs = {} if settings is None else {"table_settings": settings}
                try:
                    page_tables = page.extract_tables(**kwargs) or []
                except Exception:
                    continue
                for raw_table in page_tables:
                    markdown = _table_to_markdown(raw_table)
                    if not markdown.strip():
                        continue
                    table_num += 1
                    raw_tables.append(f"## Table {table_num}\n\n{markdown}")
                if page_tables:
                    break

    return _dedupe_tables(raw_tables)
