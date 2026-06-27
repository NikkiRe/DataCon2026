# Инструкция по запуску (по шагам)

Документ для запуска проекта с нуля. Делай строго по порядку, шаги не пропускай.
Каждую команду копируй целиком. После команд указано, что должно появиться в выводе.

Все команды выполняются из корня проекта (папка с этим файлом).

## Шаг 0. Проверь, что есть на компьютере

```bash
python3 --version
```

Ожидаемо: `Python 3.11.x` или выше. Если версия ниже 3.11, поставь новее, иначе часть кода не запустится.

Что ещё понадобится:
- API-ключ OpenAI и/или Anthropic.
- Несколько PDF научных статей (open-access) по домену, который будешь тестировать.

## Шаг 1. Создай виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
```

На Windows вместо второй команды: `.venv\Scripts\activate`.

Проверка:

```bash
which python
```

Ожидаемо: путь заканчивается на `.venv/bin/python`. Если нет, окружение не активировалось, повтори шаг.

## Шаг 2. Установи зависимости

```bash
pip install -r requirements.txt
```

Ожидаемо: в конце `Successfully installed ...`.

`marker-pdf` в requirements не входит и не обязателен. Парсинг работает на `pdfplumber` (текст и
таблицы) плюс `pymupdf` (рендер страниц с рисунками), поэтому vision-этап работает из коробки.

Опционально, для более качественного рендера страниц, можно поставить `pdf2image` и системный `poppler`:

```bash
pip install pdf2image
```

Системный poppler: на macOS `brew install poppler`, на Ubuntu или Debian `sudo apt-get install poppler-utils`.

## Шаг 3. Пропиши ключи

```bash
cp .env.example .env
```

Открой файл `.env` в редакторе и впиши значения:
- `ANTHROPIC_API_KEY=...` и/или
- `OPENAI_API_KEY=...`

Достаточно одного ключа. Если впишешь оба, включится полный гибридный режим.
Файл `.env` в репозиторий не попадает (он в .gitignore). Ключ никуда не коммить.

## Шаг 4. Проверь, что код в принципе работает (без ключей и сети)

```bash
pytest -m "not integration"
```

Ожидаемо: строка вида `N passed`. Это юнит-тесты метрики, merge, роутинга и препроцессинга.
Если тут красное, дальше идти нет смысла: сначала чини окружение.

## Шаг 5. Подготовь PDF

Метрика ChemX считается только по open-access статьям (поле `access == 1` в датасете на Hugging Face).
Сложи такие PDF в одну папку по домену, например:

```
pdfs/
  cocrystals/
    article1.pdf
    article2.pdf
```

Где взять PDF:
- по DOI из карточки датасета на Hugging Face (ссылки в `docs/SUBMISSION.md`);
- через рабочий процесс репозитория ChemX (папки `LLM/data/pdfs/pdf_<domain>`).

Имя файла должно соответствовать полю `pdf` в датасете (регистр и наличие `.pdf` метрика приводит
к единому виду сама).

## Шаг 6. Извлеки одну статью (быстрая проверка пайплайна)

```bash
python scripts/run_extract.py --pdf pdfs/cocrystals/article1.pdf --domain cocrystals -o out/test.csv
```

Список допустимых доменов: oxazolidinone, benzimidazole, cocrystals, complexes, nanozymes,
magnetic, cytotoxicity, seltox, synergy.

Необязательные флаги: `--mode {fast,pdf,staged}` (по умолчанию fast) и `--no-verify` (без второго
прохода верификации: быстрее и дешевле, но качество ниже).

Ожидаемо: `Wrote N row(s) to .../out/test.csv`.
Открой `out/test.csv` и убедись, что там есть строки и колонки домена.

Если упало с `NoLLMProviderError`: ключ не задан или `.env` не подхватился. Вернись к шагу 3.

## Шаг 7. Извлеки все статьи домена (батч)

```bash
python scripts/batch_extract.py --pdf-dir pdfs/cocrystals --domain cocrystals -o out/cocrystals_pred.csv
```

Ожидаемо: построчно `Extracting <файл>... -> N row(s)`, в конце
`Wrote N total row(s) to .../out/cocrystals_pred.csv`.

Это может занять время и потратить деньги на API: примерно несколько вызовов модели на статью.

## Шаг 8. Посчитай метрику (честную, как в ChemX)

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv
```

Нужен интернет: ground truth грузится с Hugging Face.

Ожидаемо: таблица по полям (precision, recall, f1) и строка `Macro-F1: 0.xxxx`.
Сравни с планкой бейзлайна для домена (cocrystals 0.296; полный список в `docs/SUBMISSION.md`).

Сохранить метрику в файл:

```bash
python scripts/run_eval.py --domain cocrystals --predictions out/cocrystals_pred.csv --save-metrics out/cocrystals_metrics.csv
```

## Шаг 9. Запусти веб-демо

```bash
streamlit run app/streamlit_app.py
```

Откроется браузер на `http://localhost:8501`. Выбери домен в боковой панели, загрузи PDF, нажми
`Extract`. Внизу появится таблица и кнопка выгрузки CSV.

## Как убедиться, что скор честный

Высокий Macro-F1 на этой задаче подозрителен (single-agent бейзлайн от 0.034 до 0.491). Прежде чем
верить числу, проверь саму метрику двумя быстрыми тестами.

Идеальные предсказания должны давать примерно 1.0. Возьми ground truth как предсказания:

```bash
python - <<'PY'
from chemx_extract.eval.metrics import load_ground_truth, compute_metrics, macro_f1
gt = load_ground_truth("cocrystals")
m = compute_metrics(gt, gt, "cocrystals")
print("perfect:", round(macro_f1(m), 4))
PY
```

Ожидаемо: близко к 1.0. Если меньше, метрика занижает.

Пустые предсказания должны давать близко к 0:

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

Ожидаемо: близко к 0. Если пустые предсказания дают высокий скор, в метрике утечка
(например, пустые поля засчитываются как совпадение), и числу верить нельзя.

Признаки нечестного скора, которых быть не должно:
- оценка только по статьям, для которых есть предсказания, без полного open-access набора;
- пустые значения выбрасываются до подсчёта, из-за чего отсутствующие поля дают бесплатные совпадения.

## Частые ошибки и что делать

| Симптом | Причина и решение |
|---|---|
| NoLLMProviderError | Ключ не задан. Заполни `.env` (шаг 3) или активируй окружение заново. |
| 429 / rate limit | Лимит тарифа ключа. Подожди, уменьши объём, гоняй по одной статье. |
| Установка marker-pdf падает | Необязательный пакет. Игнорируй, используется pdfplumber. |
| Hugging Face download fails | Нет интернета или не залогинен. Проверь сеть, при необходимости `huggingface-cli login`. |
| Macro-F1 неожиданно низкий | Проверь, что в предсказаниях есть колонка `pdf` и имена совпадают со статьями датасета. |
| SMILES всегда 0 | Проверь установку RDKit; при наличии включи PubChem-резолвер. |
| ModuleNotFoundError chemx_extract | Запускаешь не из корня проекта или не активировано окружение. Вернись в корень, активируй .venv. |

## Стоимость прогона

Ориентир: несколько вызовов модели на одну страницу PDF плюс обработка рисунков. Небольшой домен
(например cocrystals, порядка десятка статей) обходится дёшево. Крупные домены дороже:
закладывай бюджет и гоняй частями.
