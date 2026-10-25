# Nanozymes: прототип извлечения данных из статей (DataCon'26)

Ветка с личным прототипом Никиты Евстигнеева, сделанным в рамках командного проекта DataCon'26.
Командный проект занял 3-е место. Итоговое решение команды — пакет `chemx_extract` в ветке
[`main`](https://github.com/NikkiRe/DataCon2026/tree/main); эта ветка не является его предком.
Постановка задачи и файлы `metrics/` взяты из исходного командного репозитория
[Sleptsov99/DataCon2026](https://github.com/Sleptsov99/DataCon2026).

Задача: по PDF научной статьи о нанозимах заполнить 20 полей схемы бенчмарка
[ChemX](https://github.com/ai-chem/ChemX) (датасет `ai-chem/Nanozymes`) и сравнить качество с
бейзлайном ChemX single-agent: Macro-F1 = 0.164 (среднее F1 по полям в
`metrics/metrics_nanozymes_from_single_agent.csv`). Постановка задачи: [`docs/TASK.md`](docs/TASK.md).

## Что внутри

```
nanozx/
  schema.py        20 полей домена, числовые и строковые поля, токены пропусков (NOT_DETECTED / nan)
  dataset.py       загрузка ai-chem/Nanozymes (parquet с Hugging Face), фильтр access == 1, кэш в data/cache/
  metric.py        метрика ChemX: мультимножество значений по колонке на статью,
                   усреднение по статьям, Macro-F1 = среднее F1 по полям
  serialize.py     приведение значений к формату эталона (пропуски, float -> "25.0", length/width/depth без ".0")
  normalize.py     привязка activity и syngony к фиксированному словарю + сериализация
  prompts.py       системный промпт и JSON Schema ответа
  extract.py       вызов Claude (claude-opus-4-8) со structured output: PDF целиком или текст статьи
  predict.py       записи -> DataFrame предсказаний
scripts/
  download_pdfs.py        open-access PDF по DOI (Unpaywall, Europe PMC, citation_pdf_url) + manifest.csv
  run_extract.py          извлечение: --source api | text | manual  ->  data/cache/preds.csv
  score_preds.py          Macro-F1 предсказаний против эталона
  prove_serialization.py  метрика на предсказаниях бейзлайна ChemX: как есть и после serialize.py
  mine_vocab.py           частотные словари значений полей -> data/cache/vocab.json (справочно, кодом не используется)
app/streamlit_app.py      веб-демо: PDF -> таблица -> CSV
data/manual/              12 JSON-файлов с записями для 12 open-access статей ({"samples": [...]});
                          режим --source manual использует их как предсказания
```

Каталоги `data/cache/` и `data/pdfs/` создаются при запуске и в репозиторий не входят.

## Установка

Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # версии не закреплены

export ANTHROPIC_API_KEY=...             # для --source api/text и для веб-демо
export UNPAYWALL_EMAIL=you@example.com   # контактный адрес для Unpaywall (download_pdfs.py)
```

Код не читает `.env`, поэтому переменные нужно задать в окружении.
Эталон `ai-chem/Nanozymes` скачивается с Hugging Face при первом запуске и кэшируется в `data/cache/`.

## Запуск

```bash
python scripts/download_pdfs.py                # PDF в data/pdfs/ + data/pdfs/manifest.csv

python scripts/run_extract.py --source api     # PDF целиком в модель
python scripts/run_extract.py --source text    # первые 16 000 символов текста (PyMuPDF), дешевле
python scripts/run_extract.py --source manual  # записи из data/manual/
# --limit N — первые N статей; --sleep — пауза между вызовами API (по умолчанию 70 с)

python scripts/score_preds.py                  # метрика по data/cache/preds.csv
python scripts/prove_serialization.py          # проверка реализации метрики на бейзлайне ChemX

streamlit run app/streamlit_app.py             # веб-демо (нужен ANTHROPIC_API_KEY)
```

Режимы `api` и `text` перебирают статьи, PDF которых лежат в `data/pdfs/`, поэтому сначала нужен
`download_pdfs.py`; без PDF скрипт завершается с сообщением об этом. Режим `manual` перебирает JSON-файлы
в `data/manual/` и работает без PDF и без API-ключа. `download_pdfs.py` без `UNPAYWALL_EMAIL`
завершается с ошибкой.

`score_preds.py` печатает два числа. Full-set Macro-F1 считается по всем open-access статьям, статьи
без предсказаний дают 0; именно это число сравнимо с бейзлайном. Covered-only Macro-F1 считается только
по статьям с предсказаниями: это диагностика, с бейзлайном она несравнима.

## Метрика и что из неё следует

Метрика ChemX сравнивает не строки, а мультимножества значений в каждой колонке для каждой статьи, по
точному строковому совпадению. Пропуски в эталоне записаны как `NOT_DETECTED` для строк и `nan` для чисел,
и совпадение пропуска засчитывается. Поэтому важны и число строк на статью, и корректная запись пропусков.
Числа хранятся как float, приведённый к строке (`25.0`). Оценка идёт только по open-access статьям
(`access == 1`): для Nanozymes это 111 строк в 39 статьях.

Качество зависит не только от содержания, но и от формата. `prove_serialization.py` скачивает
опубликованные предсказания бейзлайна ChemX и считает на них метрику дважды:

```
baseline published target macro-F1: 0.164
reproduced as-is macro-F1:           0.1640
format-only macro-F1:                0.2379
```

Вторая строка показывает, что реализация метрики даёт опубликованное значение бейзлайна. Третья — что
заметная часть ошибок бейзлайна связана с форматом значений. Все предсказания прототипа проходят через
`serialize.py`.

## Результаты

Результат автоматического прогона экстрактора (`--source api` / `text`) по всем статьям в репозитории
не сохранён. Файлы в `data/manual/` (12 из 39 open-access статей) ни один скрипт репозитория не создаёт:
`run_extract.py --source manual` только читает их. Оценка по ним не является воспроизводимой оценкой
экстрактора, поэтому здесь не приводится.

## Ограничения

- Отдельной отложенной выборки нет. Правила сериализации и промпт ориентированы на конвенции разметки
  тех же open-access записей ChemX, на которых считается метрика; `mine_vocab.py` строит словари по ним же.
  Поэтому любые оценки на этих данных оптимистичны и не являются оценкой на независимых данных.
- `download_pdfs.py` скачивает не все open-access PDF: часть издателей блокирует автоматические запросы,
  такие статьи отмечаются в `manifest.csv` как `download_failed`.
- Supporting Information не используется: значения, которые есть только в ESI, извлечь нельзя.
- Прогон через API платный и упирается в rate limit ключа; для этого есть текстовый режим и `--sleep`.
- Версии зависимостей в `requirements.txt` не закреплены.
