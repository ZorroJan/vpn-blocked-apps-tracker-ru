---
paths:
  - "tests/**/*.py"
---

# Тестирование

## Правила

- **Никаких сетевых запросов.** Тесты должны быть детерминированными и быстрыми. Если нужен HTML — клади в `tests/fixtures/`.
- **Каждый парсер должен иметь хотя бы один тест** на фиксированной HTML-фикстуре. Это страховка от изменения вёрстки источника.
- **`pytest tests/ -v` должен быть зелёным перед каждым коммитом.**
- **Покрытие важных модулей**: `normalize.py`, `aggregate.py` — тесты обязательны для каждой логической ветки. `render_readme.py` — достаточно одного smoke-теста.

## Структура

```
tests/
  test_normalize.py         # уже есть, расширяй при изменениях в normalize.py
  test_aggregate.py         # уже есть, расширяй при изменениях в aggregate.py
  test_sources.py           # тесты парсеров (когда понадобятся)
  fixtures/
    hitech_mail_2026-05.html
    rozetked_2026-05.html
    ...
```

## Шаблон теста парсера

```python
from pathlib import Path
from scraper.sources import hitech_mail

FIXTURES = Path(__file__).parent / "fixtures"

def test_hitech_mail_extracts_ozon() -> None:
    html = (FIXTURES / "hitech_mail_2026-05.html").read_text(encoding="utf-8")
    result = hitech_mail.parse(html)
    # Проверяй наличие, не точный список — список может меняться от снапшота к снапшоту
    assert any("Ozon" in item or "ozon" in item.lower() for item in result)
    assert len(result) > 5  # sanity check, что парсер не вернул пустоту
```

**Почему не точное равенство:** статьи обновляются, новые приложения добавляются в списки. Тест должен ловить «парсер сломан» (вернул 0 или мусор), а не «список приложений изменился».

## Что НЕ тестировать

- Содержимое `aliases.yaml` — это data, не код.
- Точный markdown из `render_readme.py` — он будет меняться при правках оформления. Достаточно проверить, что он непустой и содержит имена приложений.
- Работу `requests` — это библиотека, она протестирована своими разработчиками.

## Моки

Если нужно протестировать `main.py` целиком — мокай `fetch()` через `monkeypatch`:

```python
def test_main_handles_source_failure(monkeypatch):
    from scraper import main
    monkeypatch.setattr(main, "fetch", lambda url: None)
    # ...
```

## Запуск отдельных тестов

```bash
pytest tests/test_normalize.py -v
pytest tests/test_normalize.py::test_longest_match_wins -v
pytest tests/ -k "yandex" -v        # все тесты с "yandex" в имени
```
