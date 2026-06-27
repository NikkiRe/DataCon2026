# Examples for the demo

Files here power the "Examples (precomputed, instant)" section of the Streamlit app.
They let you demo the result table immediately, without waiting for a live API run.

## How to add an example

1. Run an extraction once and save the CSV:

   ```bash
   python scripts/run_extract.py --pdf path/to/article.pdf --domain cocrystals -o app/examples/cocrystals__article1.csv
   ```

2. Name the file `<domain>__<name>.csv`. The part before `__` must be a valid domain
   (oxazolidinone, benzimidazole, cocrystals, complexes, nanozymes, magnetic, cytotoxicity,
   seltox, synergy). It drives the per-field fill summary shown under the table.

3. Restart the app. A button labelled `<domain>__<name>` appears; clicking it shows the table instantly.

If this folder has no CSV files, the examples section is simply hidden.
