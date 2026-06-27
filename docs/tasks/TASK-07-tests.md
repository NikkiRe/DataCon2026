# TASK-07 — Tests

**Owner files:** `tests/conftest.py`, `tests/test_preprocessing.py`, `tests/test_extraction.py`, `tests/test_merge.py`, `tests/test_pipeline.py`, `tests/test_eval.py`, `pytest.ini`

**Depends on:** TASK-01–05 (implement tests even if modules stubbed)

## Goal

Automated test suite; no network/API in default run.

## conftest.py

- Fixtures: sample row dicts per domain
- `mock_openai_client` monkeypatch pattern

## Coverage targets

| File | Min tests |
|------|-----------|
| schemas/config | import + column count |
| normalize_row | missing cols filled |
| postprocess | SMILES canonical, target_relation |
| metrics | toy TP/FP/FN |
| merge_rows | dedup |

## pytest.ini

```ini
[pytest]
testpaths = tests
markers =
    integration: needs API key or PDF
```

## Acceptance

```bash
pytest -m "not integration" -v
```

All pass without OPENAI_API_KEY.

## Out of scope

E2E with real PDF (integration tester).
