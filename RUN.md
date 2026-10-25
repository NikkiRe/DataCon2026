# Инструкция по запуску (по шагам)

Пошаговый запуск с нуля. Команды выполняются из корня репозитория; после каждой
указан ожидаемый вывод.

## Шаг 0. Проверка окружения

```bash
python3 --version
```

Ожидаемо: `Python 3.11.x` или выше. На более старых версиях часть кода не запустится.

Также понадобятся:
- API-ключ OpenAI и/или Anthropic;
- несколько open-access PDF научных статей по выбранному домену.

## Шаг 1. Виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
```

На Windows вместо второй команды: `.venv\Scripts\activate`.

Проверка:

```bash
which python
```

Ожидаемо: путь заканчивается на `.venv/bin/python`. Иначе окружение не активировано.

## Шаг 2. Зависимости

```bash
pip install -r requirements.txt
```

Ожидаемо: в конце `Successfully installed ...`.

`marker-pdf` в requirements не входит и не обязателен. Без него текст и таблицы извлекает
`pdfplumber`, а страницы с рисунками рендерит `pymupdf`, поэтому vision-этап работает без
дополнительных пакетов.

Для более качественного рендера страниц можно поставить `pdf2image` и системный `poppler`:

```bash
pip install pdf2image
```

Системный poppler: на macOS `brew install poppler`, на Ubuntu или Debian `sudo apt-get install poppler-utils`.

## Шаг 3. Ключи API

```bash
cp .env.example .env
```

В `.env` указываются:
- `ANTHROPIC_API_KEY=...` и/или
- `OPENAI_API_KEY=...`

Достаточно одного ключа; при наличии обоих включается полный гибридный режим.
Файл `.env` указан в `.gitignore`.

## Шаг 4. Юнит-тесты (без ключей и сети)

```bash
pytest -m "not integration"
```

Ожидаемо: строка вида `N passed`. Это юнит-тесты метрики, merge, роутинга и препроцессинга.
Если тесты падают, сначала нужно исправить окружение.

## Шаг 5. PDF

Метрика ChemX считается только по open-access статьям (поле `access == 1` в датасете на Hugging Face).
PDF складываются в одну папку по домену, например:

```
pdfs/
  cocrystals/
    article1.pdf
    article2.pdf
```

Источники PDF:
- DOI из карточки датасета на Hugging Face (ссылки в `docs/SUBMISSION.md`);
- рабочий процесс репозитория ChemX (папки `LLM/data/pdfs/pdf_<domain>`).

Имя файла должно соответствовать полю `pdf` в датасете (регистр и наличие `.pdf` метрика приводит
к единому виду сама).

## Шаг 6. Одна статья

```bash
python scripts/run_extract.py --pdf pdfs/cocrystals/article1.pdf --domain cocrystals -o out/test.csv
```

Допустимые домены: oxazolidinone, benzimidazole, cocrystals, complexes, nanozymes,
magnetic, cytotoxicity, seltox, synergy.

Необязательные флаги: `--mode {fast,pdf,staged}` (по умолчанию fast) и `--no-verify` (без второго
прохода верификации: быстрее и дешевле, но качество ниже).

Ожидаемо: `Wrote N row(s) to .../out/test.csv`. В `out/test.csv` должны быть строки и колонки домена.

`NoLLMProviderError` означает, что ключ не задан или `.env` не прочитан (см. шаг 3).

## Шаг 7. Пакетный прогон

```bash
python scripts/batch_extract.py --pdf-dir pdfs/cocrystals --domain cocrystals -o out/cocrystals_pred.csv
```

Ожидаемо: в начале `Batch start: N PDF(s), mode=fast, domain=cocrystals`, для каждого файла
`done in … → N row(s)`, в конце `Batch complete in …`.

Прогон занимает время и расходует API: несколько вызовов модели на статью.

## Шаг 8. Метрика

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv
```

Нужен интернет: ground truth загружается с Hugging Face.

Ожидаемо: таблица по полям (precision, recall, f1) и строка `Macro-F1: 0.xxxx`.
Планка бейзлайна для cocrystals — 0.296; полный список в `docs/SUBMISSION.md`.

Сохранение метрики в файл:

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv --save-metrics out/cocrystals_metrics.csv
```

## Шаг 9. Веб-демо

```bash
streamlit run app/streamlit_app.py
```

Приложение открывается на `http://localhost:8501`. В боковой панели выбирается домен, затем
загружается PDF и нажимается `Extract`. Ниже появляются таблица и кнопка выгрузки CSV.

## Проверка метрики (sanity check)

Высокий Macro-F1 на этой задаче требует проверки (single-agent бейзлайн от 0.034 до 0.491).
Два быстрых теста самой метрики.

Идеальные предсказания (ground truth как предсказания) должны давать 1.0:

```bash
python - <<'PY'
from chemx_extract.eval.metrics import load_ground_truth, compute_metrics, macro_f1
gt = load_ground_truth("cocrystals")
m = compute_metrics(gt, gt, "cocrystals")
print("perfect:", round(macro_f1(m), 4))
PY
```

Ожидаемо: `perfect: 1.0`. Меньшее значение означает, что метрика занижает.

Пустые предсказания должны давать 0:

```bash
python - <<'PY'
import pandas as pd
from chemx_extract.eval.metrics import load_ground_truth, compute_metrics, macro_f1
gt = load_ground_truth("cocrystals")
empty = pd.DataFrame(columns=list(gt.columns))
m = compute_metrics(gt, empty, "cocrystals")
print("empty:", round(macro_f1(m), 4))
PY
```

Ожидаемо: `empty: 0.0`. Высокий скор на пустых предсказаниях означает утечку в метрике
(например, пустые поля засчитываются как совпадение).

Типичные ошибки оценки: подсчёт только по статьям с предсказаниями; удаление пустых значений до
подсчёта.

## Частые ошибки

| Симптом | Причина и решение |
|---|---|
| NoLLMProviderError | Ключ не задан. Заполнить `.env` (шаг 3) или заново активировать окружение. |
| 429 / rate limit | Лимит тарифа ключа. Подождать, уменьшить объём, запускать по одной статье. |
| Установка marker-pdf падает | Пакет необязательный; используется pdfplumber. |
| Hugging Face download fails | Нет сети или нужна авторизация: проверить сеть, при необходимости `huggingface-cli login`. |
| Macro-F1 неожиданно низкий | Проверить, что в предсказаниях есть колонка `pdf` и имена совпадают со статьями датасета. |
| SMILES всегда 0 | Проверить установку RDKit; при наличии включить PubChem-резолвер. |
| ModuleNotFoundError chemx_extract | Скрипт запущен не из корня проекта или не активировано окружение. |

## Стоимость прогона

Ориентир: несколько вызовов модели на одну страницу PDF плюс обработка рисунков. Небольшой домен
(например cocrystals, порядка десятка статей) обходится дёшево. Крупные домены дороже, их лучше
прогонять частями.
