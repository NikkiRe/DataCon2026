# Orchestrator — DataCon2026 ChemX Extraction

## Mission

Build a **staged extraction pipeline** that beats ChemX single-agent baseline (Macro-F1) on at least one domain, with Streamlit UI and reproducible eval.

## Target domains (priority)

| Priority | Domain key | HF dataset | Baseline Macro-F1 |
|----------|------------|------------|-------------------|
| P0 | `cocrystals` | ai-chem/Co-crystals | 0.296 |
| P1 | `oxazolidinone` | ai-chem/Oxazolidinones | 0.491 |
| P2 | `cytotoxicity` | ai-chem/Cytotox | 0.182 |

## Architecture

```
PDF → preprocessing → block routing → [table|text|figure|smiles agents] → merge → postprocess → CSV
```

## Repository layout (ownership)

| Path | Owner task | Description |
|------|------------|-------------|
| `chemx_extract/config.py`, `schemas.py` | TASK-01 | Domain schemas, env, constants |
| `chemx_extract/preprocessing/` | TASK-02 | PDF→markdown, tables, suppl merge |
| `chemx_extract/extraction/` | TASK-03 | LLM agents (table, text, figure) |
| `chemx_extract/smiles/`, `merge/`, `pipeline.py` | TASK-04 | SMILES tools, merge, orchestration |
| `chemx_extract/eval/` | TASK-05 | ChemX-compatible metrics |
| `app/`, `scripts/` | TASK-06 | Streamlit + CLI |
| `tests/` | TASK-07 | Unit + integration tests |
| `docs/` | Orchestrator | Specs, submission guide |

## Workflow

```
Orchestrator → Developer (task) → Reviewer (same task) → Tester (same task)
                                                      ↘
                                            Integration Tester (TASK-INT)
```

## Acceptance criteria (global)

1. `pip install -r requirements.txt` works (core deps; optional marker/decimer documented).
2. `python scripts/run_extract.py --pdf path.pdf --domain cocrystals` produces CSV with schema columns.
3. `python scripts/run_eval.py --domain cocrystals --predictions path.csv` prints Macro-F1.
4. `streamlit run app/streamlit_app.py` — upload PDF, see table, download CSV.
5. All domain keys match ChemX `LLM/src/constants.py`.
6. Missing values → `NOT_DETECTED` (eval convention).
7. SMILES canonicalized via RDKit when valid.

## Environment variables

See `.env.example`. Required: `OPENAI_API_KEY`. Optional: `PUBCHEM_USER_AGENT`.

## Commands (integration)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill OPENAI_API_KEY

# Single PDF
python scripts/run_extract.py --pdf data/sample.pdf --domain cocrystals -o out/pred.csv

# Eval (needs HF datasets + predictions with pdf column)
python scripts/run_eval.py --domain cocrystals --predictions out/pred.csv

# UI
streamlit run app/streamlit_app.py
```

## Subagent assignment log

| Task | Developer | Reviewer | Tester | Status |
|------|-----------|----------|--------|--------|
| TASK-01 | [dev](9bd18883-7c99-487d-8479-9eb8af258a17) | TASK-01-03-review | pytest | **done** |
| TASK-02 | [dev](6160fa38-fc73-4a29-8bda-f12043ad3f9e) | TASK-01-03-review | pytest | **done** |
| TASK-03 | [dev](2196c98f-e8a4-4efa-9851-9734dd3049f0) | TASK-01-03-review | pytest | **done** |
| TASK-04 | [dev](6ac494d0-46d1-48f0-b787-2fd345185642) | TASK-04-06-review | pytest | **done** |
| TASK-05 | [dev](6ac494d0-46d1-48f0-b787-2fd345185642) | TASK-04-06-review | pytest | **done** |
| TASK-06 | [dev](821d0ecb-2d9b-46fd-8ac4-6bb04625f26a) | TASK-04-06-review | --help | **done** |
| TASK-07 | all devs | — | TASK-07-test | **done** |
| TASK-INT | — | — | [INTEGRATION-test](06cf8dc5-654c-4c81-88dc-7ea08a6d2a89) | **PASS** |
