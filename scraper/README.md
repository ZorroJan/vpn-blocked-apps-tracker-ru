# Scraper documentation

## Архитектура

```
scraper/
├── main.py              # точка входа, оркестрирует пайплайн
├── sources.yaml         # список источников
├── aliases.yaml         # словарь синонимов: канонические имена ↔ варианты
├── normalize.py         # нормализация (сырое имя → AppDefinition)
├── aggregate.py         # слияние с историей в data/apps.json
├── render_readme.py     # генерация корневого README.md
└── sources/             # парсеры
    ├── __init__.py      # общие утилиты для парсеров
    ├── hitech_mail.py
    ├── rozetked.py
    ├── kod_durova.py
    └── meduza.py
```

## Пайплайн

1. **Fetch** — `main.py` обходит источники из `sources.yaml`, грузит HTML.
2. **Parse** — каждый источник имеет свой модуль в `sources/`, экспортирует
   функцию `parse(html: str) -> list[str]`, возвращающую сырые строки.
3. **Normalize** — `normalize.py` сопоставляет сырые строки с
   каноническими именами по `aliases.yaml`. Неизвестное отбрасывается.
4. **Aggregate** — `aggregate.py` мержит результаты с `data/apps.json`,
   обновляя `first_seen`, `last_confirmed`, `sources`, `confidence`, `status`.
5. **Render** — `render_readme.py` генерирует корневой `README.md`.
6. **Snapshot** — сырой результат запуска кладётся в `data/snapshots/<date>.json`
   для отладки.

## Запуск локально

```bash
# В корне репозитория
python -m venv .venv
source .venv/bin/activate          # на Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest tests/ -v
python -m scraper.main
```

## Добавить новый источник

1. Добавьте запись в `sources.yaml`:
   ```yaml
   - id: new_source
     name: "Имя источника"
     url: "https://..."
     parser: new_source
     enabled: true
   ```
2. Создайте `sources/new_source.py`:
   ```python
   from . import extract_list_items, clean_app_name

   def parse(html: str) -> list[str]:
       items = extract_list_items(html)
       return [clean_app_name(item) for item in items if item]
   ```
3. Если вёрстка нестандартная (не `<li>`), напишите парсер под конкретные
   селекторы. Утилиты `extract_article_text()` и `BeautifulSoup` доступны.

## Добавить новое приложение

Откройте `aliases.yaml` и добавьте блок:

```yaml
Имя Приложения:
  category: marketplace  # см. список категорий в render_readme.py
  aliases:
    - "имя приложения"
    - "alternate name"
    - "ещё вариант написания"
```

Категории, известные `render_readme.py`:
`marketplace`, `streaming`, `payments`, `yandex_services`, `social`, `mail`,
`delivery`, `retail`, `travel`, `maps`, `jobs`, `government`, `other`.

Чтобы добавить новую категорию, отредактируйте `CATEGORY_TITLES` в
`render_readme.py`.

## Поведение при сбоях

- **Источник не отвечает** — пропускается, остальные обрабатываются.
- **Парсер вернул 0 совпадений** — источник пропускается (защита от поломки
  вёрстки, см. `MIN_EXPECTED_AFTER_HEALTHY` в `main.py`).
- **Все источники упали** — скрипт завершается с кодом 1, данные не трогает.
- **Приложение не упоминается > 30 дней** — переезжает в архив, но не удаляется.

## Обновление логики уверенности

Сейчас:
- `confirmed` — 2+ источника подтвердили в последнем запуске.
- `reported` — 1 источник.

Чтобы изменить порог, правьте `merge_run()` в `aggregate.py`.

## Если что-то ломается

Снапшоты в `data/snapshots/<date>.json` показывают, что именно вернул
каждый парсер в конкретный день. Если у источника изменилась вёрстка,
сравните последний снапшот с предыдущим, обновите соответствующий парсер
в `sources/`.
