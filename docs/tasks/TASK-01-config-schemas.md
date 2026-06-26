# TASK-01 — Config & schemas

**Owner files:** `chemx_extract/__init__.py`, `chemx_extract/config.py`, `chemx_extract/schemas.py`, `requirements.txt`, `.env.example`, `.gitignore`

## Goal

Central configuration and ChemX-aligned domain schemas. Foundation for all other tasks.

## Requirements

### `chemx_extract/schemas.py`
Mirror ChemX `LLM/src/constants.py`:
- `DATASETS`, `DATASETS_IDS`, `EXTRACTED_COLUMNS`, `NUMERIC_COLUMNS`, `SMILES_COLS`
- `MAGNETIC_ARTICLES`, `SELTOX_ARTICLES` lists
- Helper: `get_columns(domain: str) -> list[str]`

### `chemx_extract/config.py`
- Load from env: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4.1-mini-2025-04-14`), `OPENAI_VISION_MODEL` (default `gpt-4o-2024-11-20`)
- `NOT_DETECTED = "NOT_DETECTED"`
- Paths: `DATA_DIR`, `OUTPUT_DIR`

### `requirements.txt`
Include at minimum:
```
openai>=1.0
pandas>=2.0
datasets>=2.14
rdkit
python-dotenv
streamlit
pdfplumber
Pillow
requests
pytest
```
Comment optional: `marker-pdf`, `decimer`

### `.env.example`
```
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini-2025-04-14
OPENAI_VISION_MODEL=gpt-4o-2024-11-20
PUBCHEM_USER_AGENT=DataCon2026/1.0
```

### `.gitignore`
`.env`, `__pycache__`, `.venv`, `out/`, `data/cache/`, `*.pyc`

## Acceptance tests

```bash
python -c "from chemx_extract.schemas import EXTRACTED_COLUMNS; assert 'cocrystals' in EXTRACTED_COLUMNS"
python -c "from chemx_extract.config import NOT_DETECTED; assert NOT_DETECTED == 'NOT_DETECTED'"
```

## Out of scope

No extraction logic.
