# TASK-06 — CLI & Streamlit UI

**Owner files:** `scripts/run_extract.py`, `scripts/run_eval.py`, `app/streamlit_app.py`

**Depends on:** TASK-04, TASK-05

## Goal

User-facing entry points for hackathon demo and submission.

## scripts/run_extract.py

```
python scripts/run_extract.py --pdf PATH --domain cocrystals [-o out.csv] [--work-dir tmp/]
```

- argparse, load dotenv
- call `extract_from_pdf`, save CSV
- print row count

## scripts/run_eval.py

```
python scripts/run_eval.py --domain cocrystals --predictions pred.csv
```

- print per-field metrics table + Macro-F1
- optional `--save-metrics metrics.csv`

## app/streamlit_app.py

- Sidebar: domain select (all DATASETS)
- File uploader: PDF
- Button "Extract" → progress spinner → dataframe display
- Download CSV button
- Show Macro-F1 note: "Run eval script on test set for official score"
- Handle errors gracefully (missing API key message)

## Acceptance tests

Manual smoke:
```bash
streamlit run app/streamlit_app.py  # starts without error
python scripts/run_extract.py --help
python scripts/run_eval.py --help
```

## Out of scope

Auth, deployment.
