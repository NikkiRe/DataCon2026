# TASK-03 — Extraction agents

**Owner files:** `chemx_extract/extraction/__init__.py`, `chemx_extract/extraction/base.py`, `chemx_extract/extraction/table_agent.py`, `chemx_extract/extraction/text_agent.py`, `chemx_extract/extraction/figure_agent.py`, `chemx_extract/extraction/prompts.py`

**Depends on:** TASK-01

## Goal

Domain-aware LLM agents that return `list[dict]` rows (keys = schema columns).

## API

```python
def extract_from_tables(tables: list[str], domain: str, client: OpenAI) -> list[dict]: ...
def extract_from_text(markdown: str, domain: str, client: OpenAI) -> list[dict]: ...
def extract_from_figure(image_path: Path, domain: str, client: OpenAI) -> list[dict]: ...
```

## prompts.py

- `PROMPT_DESCRIPTION` — domain chemical assistant (from ChemX)
- `build_system_prompt(domain)` — column list + types + `NOT_DETECTED` rule + JSON array output
- Per-domain hints:
  - **cocrystals:** coformer/drug names, ratios, photostability
  - **oxazolidinone:** compound_id, MIC, bacteria, pMIC
  - **cytotoxicity:** cell lines, viability, concentration

## base.py

- `call_llm_json(client, system, user, model)` → parse JSON array; on failure return `[]`
- `normalize_row(row: dict, domain: str) -> dict` — ensure all columns present, default `NOT_DETECTED`

## figure_agent.py

- Encode image base64, call vision model
- Prompt: describe tables/structures in figure AND extract schema rows if visible

## Acceptance tests

```bash
pytest tests/test_extraction.py -v
```

Mock OpenAI client; test `normalize_row` fills missing columns.

## Out of scope

SMILES from structures (TASK-04), merge (TASK-04).
