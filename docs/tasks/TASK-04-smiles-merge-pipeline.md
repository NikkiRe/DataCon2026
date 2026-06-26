# TASK-04 — SMILES, merge & pipeline

**Owner files:** `chemx_extract/smiles/__init__.py`, `chemx_extract/smiles/resolver.py`, `chemx_extract/merge/__init__.py`, `chemx_extract/merge/postprocess.py`, `chemx_extract/pipeline.py`

**Depends on:** TASK-01, TASK-02, TASK-03

## Goal

End-to-end `extract_from_pdf(pdf_path, domain) -> pd.DataFrame`.

## smiles/resolver.py

```python
def canonicalize_smiles(s: str) -> str: ...  # RDKit; return original if invalid
def name_to_smiles(name: str) -> str | None: ...  # PubChem PUG REST
def resolve_smiles_fields(row: dict, domain: str) -> dict: ...  # fill SMILES cols from names
```

Optional guarded import for DECIMER — if not installed, skip image→SMILES.

## merge/postprocess.py

```python
def merge_rows(rows: list[dict], domain: str) -> list[dict]: ...  # dedupe by key fields
def postprocess_dataframe(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    # canonical SMILES, numeric comma fix, target_relation fix, NOT_DETECTED
```

Dedup key: first non-NOT_DETECTED among `compound_id`, `name_cocrystal`, `material`, `NP`, `formula`.

## pipeline.py

```python
def extract_from_pdf(pdf_path: Path, domain: str, work_dir: Path | None = None) -> pd.DataFrame:
    # 1. parse_pdf
    # 2. extract_from_tables + extract_from_text
    # 3. extract_from_figure for each image (limit 10)
    # 4. merge_rows + resolve_smiles + postprocess
    # 5. add column pdf = stem of filename
```

## Acceptance tests

```bash
pytest tests/test_merge.py tests/test_pipeline.py -v
```

## Out of scope

Eval (TASK-05), UI (TASK-06).
