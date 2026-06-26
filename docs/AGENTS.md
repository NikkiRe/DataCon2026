# Agent handbook — DataCon2026

Instructions for AI agents (and humans) working on this repo.

## Roles

### Orchestrator
- Owns `docs/ORCHESTRATOR.md`, task specs, integration, conflict resolution.
- Does **not** implement feature code unless fixing integration gaps.
- Updates task status table after each subagent run.

### Developer
- Implements **only** files listed in assigned `docs/tasks/TASK-XX-*.md`.
- Follows ChemX column names exactly (see `chemx_extract/schemas.py`).
- Uses `NOT_DETECTED` for missing fields.
- No scope creep; minimal dependencies.

### Reviewer
- Read task spec + diff; check schema match, error handling, no secrets in code.
- Output: `docs/reviews/TASK-XX-review.md` with PASS/FAIL and bullet fixes.

### Tester
- Run tests in task spec; add tests if missing.
- Output: `docs/reviews/TASK-XX-test.md` with commands run and PASS/FAIL.

### Integration tester
- Run full pipeline smoke test per `docs/SUBMISSION.md`.
- Output: `docs/reviews/INTEGRATION-test.md`.

## Coding conventions

- Python 3.10+, type hints where natural.
- `chemx_extract/` = library; `app/` = Streamlit; `scripts/` = CLI.
- Log with `logging`, not print (except CLI scripts).
- OpenAI: use `openai` SDK v1+, model default `gpt-4.1-mini-2025-04-14` in config (upgrade via env).
- Never commit `.env` or API keys.

## ChemX eval rules (critical)

From ChemX `metric_calc.py`:
- Compare **per PDF article**, multiset match per column (order irrelevant).
- Ground truth: HuggingFace train split, `access == 1` only.
- Numeric: comma → dot before compare.
- SMILES: RDKit canonicalize both sides.
- `oxazolidinone` / `benzimidazole`: `target_relation` normalize `'='` → `=`.
- `magnetic` / `seltox`: restricted article lists (see schemas).

## File you must read before coding

1. Assigned task in `docs/tasks/`
2. `chemx_extract/schemas.py` (column lists)
3. ChemX baseline: https://github.com/ai-chem/ChemX/tree/main/LLM

## PR / commit policy

Human team decides commits. Agents produce working tree; orchestrator integrates.
