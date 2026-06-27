# TASK-02 — Preprocessing

**Owner files:** `chemx_extract/preprocessing/__init__.py`, `chemx_extract/preprocessing/pdf_parser.py`, `chemx_extract/preprocessing/tables.py`, `chemx_extract/preprocessing/merge_suppl.py`

**Depends on:** TASK-01

## Goal

Convert PDF to structured text + tables for downstream agents.

## API

```python
@dataclass
class ParsedDocument:
    pdf_name: str
    markdown: str
    tables: list[str]  # markdown or CSV-like table strings
    image_paths: list[Path]

def parse_pdf(pdf_path: Path, work_dir: Path) -> ParsedDocument: ...
def merge_supplementary(main_pdf: Path, suppl_pdf: Path | None, out_path: Path) -> Path: ...
def extract_tables_pdfplumber(pdf_path: Path) -> list[str]: ...
```

## Implementation notes

1. **Primary path:** Try `marker-pdf` if installed; else fallback `pdfplumber` text extraction per page.
2. **Tables:** Always run `pdfplumber` table extraction; append as `## Table N` blocks.
3. **Images:** If marker extracts images to `work_dir/images/`, collect paths; else render pages with `pdf2image` (optional, guarded import) at 150 DPI max 50 pages.
4. **merge_supplementary:** Concatenate PDFs with pypdf if available, else copy main only.

## Acceptance tests

```bash
pytest tests/test_preprocessing.py -v
```

Create `tests/test_preprocessing.py`:
- Mock or skip-if-no-pdf test for `extract_tables_pdfplumber` on empty/minimal input
- Test `ParsedDocument` dataclass fields exist

## Out of scope

LLM calls, SMILES.
