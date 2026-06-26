# Integration test report — DataCon2026

**Date:** 2026-06-26  
**Environment:** macOS, Python 3.14.4, `.venv` at repo root  
**Tester:** Integration Tester subagent

## Command results

| # | Command | Result | Notes |
|---|---------|--------|-------|
| 1 | `.venv/bin/pytest -m "not integration" -v` | **PASS** | 33/33 passed in ~1.6s |
| 2 | `.venv/bin/python scripts/run_extract.py --help` | **PASS** | Exit 0; `--pdf`, `--domain`, `-o`, `--work-dir` documented |
| 3 | `.venv/bin/python scripts/run_eval.py --help` | **PASS** | Exit 0; `--domain`, `--predictions`, `--save-metrics` documented |
| 4 | `from chemx_extract.pipeline import extract_from_pdf; from chemx_extract.eval.metrics import evaluate_predictions` | **PASS** | Prints `IMPORT OK` |
| 5 | Docs existence check | **PASS** | All required files present (see below) |

### Docs checklist

| Path | Status |
|------|--------|
| `docs/ORCHESTRATOR.md` | Present |
| `docs/AGENTS.md` | Present |
| `docs/SUBMISSION.md` | Present |
| `docs/tasks/TASK-01-config-schemas.md` | Present |
| `docs/tasks/TASK-02-preprocessing.md` | Present |
| `docs/tasks/TASK-03-extraction-agents.md` | Present |
| `docs/tasks/TASK-04-smiles-merge-pipeline.md` | Present |
| `docs/tasks/TASK-05-evaluation.md` | Present |
| `docs/tasks/TASK-06-cli-ui.md` | Present |
| `docs/tasks/TASK-07-tests.md` | Present |

## Overall

**PASS** — All requested integration checks succeeded. Unit test suite is green; CLI entry points and core imports work; documentation scaffold is complete.

## Gaps for production / hackathon submission

These items were **not** part of the pass/fail checklist above but block a complete judge-ready submission per `docs/SUBMISSION.md` and `docs/ORCHESTRATOR.md`:

### Scoring blockers (40–60 pts at risk)

| Gap | Impact |
|-----|--------|
| **No Macro-F1 results** — no `out/metrics_*.csv` or README results table vs baselines | Extraction quality (40 pts) cannot be demonstrated |
| **No end-to-end extract smoke test** on a real PDF with `OPENAI_API_KEY` | Pipeline correctness on live LLM calls unverified |
| **No eval smoke test** against HuggingFace ground truth (`run_eval.py` with real predictions) | Official Macro-F1 reproduction unverified |

### Submission checklist gaps (`docs/SUBMISSION.md`)

| Gap | Status |
|-----|--------|
| `README.md` install + run quickstart (English) | Missing — root README is competition brief (Russian), no `pip install`, CLI, or Streamlit commands |
| Results table (Macro-F1 ours vs baseline) | Missing |
| `requirements.txt` pinned versions | Not pinned (ranges only) |
| `app/streamlit_app.py` runnable | **Streamlit not installed in `.venv`** (`pip show streamlit` → not found); `requirements.txt` lists it but env is incomplete |
| Final metrics CSV per domain | Not produced |
| Demo URL or video | Not documented |
| Git history / public repo | Entire implementation appears untracked (no commits at test time) |

### Engineering / test coverage gaps

| Gap | Notes |
|-----|-------|
| **No `@pytest.mark.integration` tests** | Marker defined in `pytest.ini`; zero tests use it — E2E PDF/API path untested in CI |
| **`streamlit run app/streamlit_app.py`** | Not smoke-tested (blocked by missing `streamlit` package) |
| **Orchestrator task table** | All tasks still `pending` in `docs/ORCHESTRATOR.md` |
| **EyeDrops domain** | Listed in competition README (10 ChemX datasets) but not in CLI `--domain` choices (9 domains) — acceptable if out of scope, but limits bonus domains |
| **`__pycache__/` artifacts** | Present in working tree; ensure `.gitignore` excludes before first commit |

### Recommended next steps (priority order)

1. `pip install -r requirements.txt` (verify `streamlit` installs) and smoke-test `streamlit run app/streamlit_app.py`.
2. Set `OPENAI_API_KEY` in `.env`; run `run_extract.py` on one open-access cocrystals PDF.
3. Batch-extract + `run_eval.py --save-metrics`; add results table to README.
4. Add at least one integration test (real PDF or mocked API) marked `@pytest.mark.integration`.
5. Pin dependencies; commit repo; document demo URL or record a short video.

## Test failures

None — all requested commands passed.
