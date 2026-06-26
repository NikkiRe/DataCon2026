# Review: TASK-04, TASK-05, TASK-06

**Date:** 2026-06-26  
**Reviewer:** subagent (Composer 2.5)  
**Verdict:** All **PASS**

| Task | Verdict |
|------|---------|
| TASK-04 SMILES / merge / pipeline | PASS |
| TASK-05 Evaluation | PASS |
| TASK-06 CLI & UI | PASS |

## ChemX metric compatibility

Port matches upstream `LLM/src/metric_calc.py` multiset logic. Pipeline `pdf` column uses filename stem (correct for small-molecule domains).

## Known gaps (non-blocking)

- DECIMER imported but not wired into figure pipeline (optional enhancement)
- Duplicate SMILES resolution in pipeline + postprocess (harmless)
- Run real Macro-F1 after batch extraction (human step with API key)

## Added by orchestrator

- `scripts/batch_extract.py` for multi-PDF eval workflow
