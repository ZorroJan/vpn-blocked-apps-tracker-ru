---
paths:
  - "scraper/sources/**/*.py"
  - "scraper/sources.yaml"
---

# Парсеры источников

## Контракт

Каждый файл в `scraper/sources/` экспортирует **только** одну функцию:

```python
def parse(html: str) -> list[str]:
    ...
```

Возвращает список сырых строк — потенциальных названий приложений. **Не нормализует** (этим занимается `scraper/normalize.py`). **Не категоризирует.** **Не дедуплицирует.** Просто извлекает текст из HTML.

## Шаблон по умолчанию

Большинство источников структурируют списки приложений как `<li>` внутри статьи. Если так, парсер тривиален:

```python
from . import extract_list_items, clean_app_name

def parse(html: str) -> list[str]:
    items = extract_list_items(html)
    return [clean_app_name(item) for item in items if item]
```

Утилиты в `scraper/sources/__init__.py`:
- `extract_list_items(html)` — все `<li>` короче 200 символов
- `extract_article_text(html)` — текст статьи без скриптов/навигации
- `clean_app_name(raw)` — снимает буллеты, нумерацию, хвостовую пунктуацию

## Когда дефолт не работает

Если источник не использует `<li>` или вёрстка сложнее, пиши кастомную логику. Конкретные селекторы — через `BeautifulSoup`:

```python
from bs4 import BeautifulSoup
from . import clean_app_name

def parse(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article") or soup.find("div", class_="article-body")
    if not article:
        return []
    items = [p.get_text(strip=True) for p in article.find_all("p")]
    return [clean_app_name(item) for item in items if item and len(item) < 200]
```

**Не используй XPath или регулярки по HTML** — только BeautifulSoup.

## Как чинить сломанный парсер

1. Открой последний снапшот в `data/snapshots/<date>.json` — там видно, что парсер вернул в день, когда всё ещё работало.
2. Сравни с тем, что возвращает сейчас:
   ```python
   import requests
   from scraper.sources import <parser_name>
   html = requests.get("URL_ИСТОЧНИКА").text
   print(<parser_name>.parse(html))
   ```
3. Скопируй текущий HTML источника в `tests/fixtures/<source>_<date>.html` (создай папку при необходимости).
4. Допиши тест в `tests/test_sources.py`, проверяющий, что парсер вытаскивает нужное из этой фикстуры.
5. Правь парсер, пока тест не зелёный.

## Анти-паттерны

- ❌ Импортировать `Normalizer` или `aliases.yaml` внутри парсера — это вне его ответственности.
- ❌ Возвращать словари с категорией — категория проставляется на этапе нормализации.
- ❌ Глобальные `requests.get()` на уровне модуля — HTTP-запрос делает `main.py`, парсер получает HTML.
- ❌ Молча проглатывать исключения внутри `parse()` — пусть упадёт, `main.py` это поймает и пропустит источник.

## Когда добавлять источник

1. Запись в `scraper/sources.yaml`:
   ```yaml
   - id: имя_без_пробелов
     name: "Отображаемое имя"
     url: "https://..."
     parser: имя_файла_без_py
     enabled: true
   ```
2. Файл `scraper/sources/<parser>.py` по шаблону выше.
3. Запусти `python -m scraper.main` локально, проверь, что источник возвращает разумное число матчей. Если 0 — либо парсер не работает, либо в `aliases.yaml` нет имён, которые встречаются на странице.
