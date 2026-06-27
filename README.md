# ChemX Extract

Извлечение структурированных химических данных из научных PDF-статей для бенчмарка
[ChemX](https://github.com/ai-chem/ChemX) (задача DataCon'26). Фреймворк покрывает все 9 доменов
бенчмарка: на вход подаётся PDF и ключ домена, на выходе CSV в схеме ChemX.

Полная постановка задачи: [docs/TASK.md](docs/TASK.md).
Пошаговая инструкция запуска и проверки: [RUN.md](RUN.md).

## Что делает

1. Парсит PDF в текст и таблицы (pymupdf или marker-pdf, фолбэк pdfplumber) и рендерит страницы с рисунками в изображения.
2. Описывает рисунки vision-моделью и вшивает описания в текст статьи.
3. Извлекает структурированные записи из таблиц и текста сильной моделью; длинный текст предварительно сжимает дешёвой моделью.
4. Вторым проходом верифицирует записи (отключается флагом `--no-verify`) и при необходимости резолвит SMILES (RDKit, PubChem по названию).
5. Объединяет, нормализует и постобрабатывает результат в одну таблицу схемы домена.
6. Считает Macro-F1 по метрике ChemX для самопроверки.

Режимы извлечения (флаг `--mode`): `fast` (по умолчанию: текст, таблицы и vision), `pdf` (отправка PDF в модель одним вызовом), `staged` (старый поэтапный режим).

## Требования

- Python 3.11 или новее.
- Ключ хотя бы одного провайдера: `ANTHROPIC_API_KEY` или `OPENAI_API_KEY`.
  При наличии обоих включается полный гибридный режим.

## Структура репозитория

```
chemx_extract/            ядро
  config.py               чтение .env: ключи, модели, пути
  schemas.py              9 доменов: колонки, числовые поля, SMILES-поля, id датасетов
  pipeline.py             extract_from_pdf: режимы fast / pdf / staged
  pipeline_log.py         структурированный лог этапов
  preprocessing/          парсинг PDF (pymupdf или marker-pdf, фолбэк pdfplumber), таблицы, рендер страниц
  extraction/             агенты: document, table, vision (batch), сжатие текста, верификация, промпты
  llm/                    клиенты Anthropic/OpenAI и роутинг моделей
  merge/                  нормализация, объединение и постобработка строк, guard верификации
  smiles/                 резолвер SMILES (RDKit + PubChem по названию)
  eval/metrics.py         метрика ChemX (Macro-F1), порт LLM/src/metric_calc.py

scripts/
  run_extract.py          извлечь одну статью (флаги --mode, --no-verify)
  batch_extract.py        извлечь все PDF из папки в один CSV
  run_eval.py             посчитать Macro-F1 против ground truth ChemX
  download_pdfs.py        скачать open-access PDF по DOI

app/streamlit_app.py      веб-демо: выбор домена, загрузка PDF, таблица, выгрузка CSV
tests/                    pytest, маркер integration для тестов с ключом/PDF
metrics/                  опубликованные метрики single-agent бейзлайна по всем доменам
docs/                     постановка задачи и проектные заметки
.env.example              шаблон переменных окружения
requirements.txt
```

## Роутинг моделей

Режим выбирается автоматически по наличию ключей (chemx_extract/llm/routing.py):

| Ключи в .env | Сжатие | Извлечение | Рисунки |
|---|---|---|---|
| Anthropic и OpenAI | Haiku | Opus 4.8 | gpt-4o-mini, затем gpt-4o |
| только Anthropic | Haiku | Opus 4.8 | Opus 4.8 (vision) |
| только OpenAI | gpt-4o-mini | gpt-4.1 | gpt-4o |
| ни одного | ошибка NoLLMProviderError | | |

Колонка "Рисунки" - это модель, которая описывает изображения страниц. Страницы с рисунками
рендерятся по умолчанию через pymupdf; pdf2image (нужен poppler) и marker-pdf - опциональные
альтернативы с более чистым результатом.

Модели и лимиты токенов переопределяются переменными в `.env` (см. `.env.example`).

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# впишите ANTHROPIC_API_KEY и/или OPENAI_API_KEY в .env
```

Извлечь одну статью:

```bash
python scripts/run_extract.py --pdf path/to/article.pdf --domain cocrystals -o out/test.csv
```

Дополнительные флаги: `--mode {fast,pdf,staged}` (по умолчанию fast) и `--no-verify` (без второго прохода).

Извлечь все PDF из папки:

```bash
python scripts/batch_extract.py --pdf-dir path/to/pdfs --domain cocrystals -o out/cocrystals_pred.csv
```

Посчитать метрику против ground truth ChemX (грузится с Hugging Face):

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv
```

Запустить демо:

```bash
streamlit run app/streamlit_app.py
```

Подробно, по шагам, с ожидаемым выводом и разбором ошибок: [RUN.md](RUN.md).

## Тестирование

Юнит-тесты без сети и ключей:

```bash
pytest -m "not integration"
```

Все тесты, включая требующие ключ или PDF:

```bash
pytest
```

## Оценка качества

`scripts/run_eval.py` использует метрику ChemX (`chemx_extract/eval/metrics.py`): по-колоночное
сравнение мультимножеств значений на каждую статью, усреднение по статьям, Macro-F1 как среднее F1
по полям домена. Считаются только open-access статьи (`access == 1`).

Планки single-agent бейзлайна, которые нужно превзойти, приведены в `docs/SUBMISSION.md` и в файлах
`metrics/metrics_<domain>_from_single_agent.csv`.

Замеренного скора в репозитории пока нет: его нужно воспроизвести через `run_eval` на своих
предсказаниях. Как убедиться, что скор честный (а не завышен лёгкой метрикой), описано в
[RUN.md](RUN.md), раздел про проверку метрики.

## Ограничения

- Нужны open-access PDF. Часть числовых полей (кинетика, концентрации) у многих статей находится в
  Supporting Information, поэтому без подмешивания ESI эти поля остаются пустыми.
- Качество зависит от парсинга PDF. Текст и таблицы извлекает `pdfplumber`, страницы с рисунками
  рендерит `pymupdf` (входит в зависимости). Опционально: `marker-pdf` даёт более чистый markdown,
  `pdf2image` плюс `poppler` - более качественный рендер страниц.
- Прогон через API стоит денег и упирается в лимиты тарифа ключа.
