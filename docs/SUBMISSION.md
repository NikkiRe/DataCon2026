# Submission & scoring guide — DataCon2026

For the hackathon team and future agents.

## What judges score (100 points)

| Criterion | Points | What to deliver |
|-----------|--------|-----------------|
| Extraction quality | 40 | Macro-F1 on ChemX **test/open-access** articles vs single-agent baseline |
| Web UI | 20 | Working upload → table → download |
| Code & README | 20 | This repo: install, run, reproduce metrics |
| Presentation | 20 | Slides + live demo + Q&A |

### Bonus points

| Bonus | Points |
|-------|--------|
| Each extra domain beaten (max 8) | +5 each |
| Both directions (small molecules + nanomaterials) | +10 |

## Baseline to beat (single-agent Macro-F1)

| Domain key | Direction | Baseline |
|------------|-----------|----------|
| cocrystals | small molecules | 0.296 |
| oxazolidinone | small molecules | 0.491 |
| benzimidazole | small molecules | 0.217 |
| complexes | small molecules | 0.290 |
| nanozymes | nanomaterials | 0.164 |
| cytotoxicity | nanomaterials | 0.182 |
| synergy | nanomaterials | 0.080 |
| magnetic | nanomaterials | 0.034 |
| seltox | nanomaterials | 0.045 |

Reference per-field metrics: `metrics/metrics_*_from_single_agent.csv` in repo root.

## How to compute YOUR score locally

### 1. Setup

```bash
cd DataCon2026
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set OPENAI_API_KEY
```

### 2. Get open-access PDFs

ChemX eval uses articles marked `access == 1` in HuggingFace datasets.

Option A — ChemX repo workflow:
```bash
git clone https://github.com/ai-chem/ChemX.git
# Place PDFs in ChemX/LLM/data/pdfs/pdf_<dataset>/
```

Option B — Download from DOI links in dataset (see HF dataset cards).

Domain → folder name mapping:
- cocrystals → `pdf_cocrystals`
- oxazolidinone → `pdf_oxazolidinone`
- cytotoxicity → `pdf_cytotoxicity`
- etc.

### 3. Run extraction on all open-access PDFs for a domain

```bash
# Single file
python scripts/run_extract.py --pdf path/to/article.pdf --domain cocrystals -o out/cocrystals_pred.csv

# Batch (example shell loop)
for f in ChemX/LLM/data/pdfs/pdf_cocrystals/*.pdf; do
  python scripts/run_extract.py --pdf "$f" --domain cocrystals -o "out/$(basename $f .pdf).csv"
done
# Then concatenate CSVs (ensure pdf column present)
```

### 4. Run evaluation

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_all_pred.csv --save-metrics out/metrics_cocrystals.csv
```

Output includes **Macro-F1**. Compare to baseline in table above.

Official eval logic matches ChemX: `chemx_extract/eval/metrics.py` (ported from `ChemX/LLM/src/metric_calc.py`).

### 5. Document results in README

Add section:

```markdown
## Results

| Domain | Macro-F1 (ours) | Baseline | Δ |
|--------|-----------------|----------|---|
| cocrystals | 0.XX | 0.296 | +0.XX |
```

## What to submit to organizers

Confirm exact upload channel with DataCon organizers (GitHub link / form / LMS). Typically:

1. **Git repository URL** (public or invited reviewers)
2. **README.md** with install + run + results table
3. **requirements.txt** pinned versions recommended
4. **Final metrics CSV** per domain attempted
5. **Demo URL or video** if UI not hosted (Streamlit Cloud / local recording)

### Repository checklist

- [ ] `README.md` — quickstart, architecture diagram, results
- [ ] `requirements.txt`
- [ ] `.env.example` (no secrets)
- [ ] `scripts/run_extract.py`, `scripts/run_eval.py`
- [ ] `app/streamlit_app.py`
- [ ] `metrics/` baseline files (already present)
- [ ] Your `out/metrics_*.csv` or documented commands to reproduce

### Streamlit demo

Local:
```bash
streamlit run app/streamlit_app.py
```

Free deploy (optional):
- [Streamlit Community Cloud](https://streamlit.io/cloud) — connect GitHub, set `OPENAI_API_KEY` in secrets

## Recommended submission strategy

1. **Minimum viable:** Beat baseline on **cocrystals** (smallest, fastest).
2. **Strong:** cocrystals + **oxazolidinone** (small molecules depth).
3. **Bonus max:** Add **cytotoxicity** or **nanozymes** (+10 cross-direction bonus).

## Cost estimate

- ~1–3 API calls per PDF page block + images
- cocrystals: ~13 articles → low cost
- Full oxazolidinone: larger; budget ~$20–50 with gpt-4.1-mini

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Macro-F1 very low | Check `pdf` column matches HF `pdf` field (lowercase, with/without .pdf) |
| SMILES always 0 | Enable PubChem resolver; check RDKit canonicalization |
| HF download fails | `huggingface-cli login` or cache offline |
| marker-pdf install fails | Use pdfplumber fallback (default in preprocessing) |

## Links

- ChemX: https://github.com/ai-chem/ChemX
- Datasets: https://huggingface.co/collections/ai-chem/chemx-6820df9ecf568b1ff0ea2431
- Paper: NeurIPS 2025 ChemX track
