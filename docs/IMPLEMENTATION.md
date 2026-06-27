# Реализация — ChemX Staged Extraction Pipeline

> Решение для финала DataCon'26. Конкурентное описание задачи — в [README.md](../README.md).

## Архитектура

```
PDF → preprocessing (marker/pdfplumber + tables)
    → extraction agents (table / text / figure + LLM)
    → merge + SMILES (PubChem + RDKit)
    → postprocess → CSV
```

Подробности для агентов: [docs/AGENTS.md](AGENTS.md), [docs/ORCHESTRATOR.md](ORCHESTRATOR.md).

## Модели (staged pipeline + fallback)

| Стадия | Primary | Fallback (OpenAI only) |
|--------|---------|----------------------|
| 1. Сжатие текста | Haiku 4.5 | GPT-4o-mini |
| 1b. Draft vision | GPT-4o-mini | Haiku vision |
| 2. Structured extract | Opus 4.8 | GPT-4.1 |
| 2b. Final vision | GPT-4o | Opus vision |

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
# Both keys → full hybrid pipeline
```

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# В .env укажите OPENAI_API_KEY
```

### Один PDF

```bash
python scripts/run_extract.py --pdf path/to/article.pdf --domain cocrystals -o out/pred.csv
```

### Пакетная экстракция (для eval)

```bash
python scripts/batch_extract.py --pdf-dir /path/to/pdf_cocrystals --domain cocrystals -o out/cocrystals_pred.csv
```

### Оценка Macro-F1

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv --save-metrics out/metrics_cocrystals.csv
```

Сравните Macro-F1 с бейзлайном в `metrics/metrics_*_from_single_agent.csv`.

### Веб-интерфейс

```bash
streamlit run app/streamlit_app.py
```

## Структура репозитория

```
chemx_extract/          # библиотека пайплайна
  preprocessing/        # PDF → markdown, tables, images
  extraction/           # LLM agents
  smiles/               # PubChem, RDKit
  merge/                # dedup, postprocess
  eval/                 # ChemX metrics
  pipeline.py           # extract_from_pdf()
app/streamlit_app.py    # демо UI
scripts/                # CLI
docs/                   # ТЗ для агентов, submission guide
tests/                  # 33 unit tests
metrics/                # бейзлайн single-agent (организаторы)
```

## Целевые домены

| Домен | Baseline Macro-F1 | Приоритет |
|-------|------------------:|-----------|
| cocrystals | 0.296 | P0 — старт здесь |
| oxazolidinone | 0.491 | P1 |
| cytotoxicity | 0.182 | P2 — бонус «оба направления» |

## Результаты

| Domain | Macro-F1 (ours) | Baseline | Δ |
|--------|----------------:|---------:|---|
| cocrystals | _TBD_ | 0.296 | — |
| oxazolidinone | _TBD_ | 0.491 | — |
| cytotoxicity | _TBD_ | 0.182 | — |

_Заполните после batch extraction + eval (нужен OPENAI_API_KEY и PDF статей)._

## Как сдать и получить score

Полная инструкция: **[docs/SUBMISSION.md](SUBMISSION.md)**

Кратко:
1. **40 баллов** — Macro-F1 на тестовых open-access статьях ChemX > single-agent baseline
2. **20 баллов** — Streamlit UI (upload → таблица → CSV)
3. **20 баллов** — код, README, воспроизводимость
4. **20 баллов** — презентация
5. **Бонусы:** +5 за каждый доп. домен (max 8), +10 за оба направления (молекулы + нано)

## Тесты

```bash
pytest -m "not integration" -v
```

## Опциональные улучшения

```bash
pip install marker-pdf pdf2image decimer
```

- `marker-pdf` — лучший PDF→markdown
- `decimer` — SMILES с рисунков структур

## Документация для субагентов

| Документ | Назначение |
|----------|------------|
| [docs/ORCHESTRATOR.md](ORCHESTRATOR.md) | План, статусы задач |
| [docs/AGENTS.md](AGENTS.md) | Роли: orchestrator / dev / reviewer / tester |
| [docs/SUBMISSION.md](SUBMISSION.md) | Score, PDF, метрики, checklist |
| [docs/tasks/](tasks/) | ТЗ TASK-01 … TASK-07 |
| [docs/reviews/](reviews/) | Отчёты review & test |
