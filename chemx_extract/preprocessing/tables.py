"""PDF table extraction via pdfplumber."""

from __future__ import annotations

from pathlib import Path


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
        lines.append("| " + " | ".join(padded[:len(header)]) + " |")
    return "\n".join(lines)


def extract_tables_pdfplumber(pdf_path: Path) -> list[str]:
    """Extract tables from a PDF as markdown blocks prefixed with ``## Table N``."""
    import pdfplumber

    tables: list[str] = []
    table_num = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for raw_table in page.extract_tables() or []:
                markdown = _table_to_markdown(raw_table)
                if not markdown.strip():
                    continue
                table_num += 1
                tables.append(f"## Table {table_num}\n\n{markdown}")

    return tables
