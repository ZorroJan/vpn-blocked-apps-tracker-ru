---
paths:
  - "data/**/*.json"
  - "scraper/aggregate.py"
  - "scraper/render_readme.py"
---

# Формат данных

## Схема `data/apps.json` (актуальная, v1)

```json
{
  "updated_at": "2026-05-18T06:00:00.000Z",
  "apps": [
    {
      "name": "Ozon",
      "category": "marketplace",
      "first_seen": "2026-04-14",
      "last_confirmed": "2026-05-18",
      "sources": ["hitech_mail", "meduza", "rozetked"],
      "last_sources": ["hitech_mail", "rozetked"],
      "confidence": "confirmed",
      "status": "active"
    }
  ]
}
```

### Семантика полей

| Поле | Тип | Значения | Кто пишет |
|---|---|---|---|
| `name` | string | каноническое имя из `aliases.yaml` | aggregate |
| `category` | string | из `CATEGORY_TITLES` в `render_readme.py` | aliases → aggregate |
| `first_seen` | string | ISO date | aggregate, ставится один раз |
| `last_confirmed` | string | ISO date | aggregate, обновляется при каждом упоминании |
| `sources` | array | union всех источников, когда-либо упомянувших | aggregate, append-only |
| `last_sources` | array | источники, упомянувшие на последнем прогоне | aggregate, перезаписывается |
| `confidence` | enum | `"confirmed"` (≥2 источника на последнем прогоне), `"reported"` (1 источник) | aggregate, derived |
| `status` | enum | `"active"` (last_confirmed в пределах `ACTIVE_DAYS` дней), `"archived"` | aggregate, derived |

`ACTIVE_DAYS` — константа в `scraper/aggregate.py`, сейчас 30.

## Правила эволюции схемы

**Backwards compatibility важен** — есть пользователи, которые могут потреблять `apps.json` через GitHub (raw.githubusercontent.com).

### Что можно менять без миграции

- Добавить новое поле в `app` — старые потребители его проигнорируют.
- Добавить новое значение в `confidence` или `status` — старые потребители увидят неизвестное значение, но не упадут (если они разумно написаны).

### Что требует миграции

- Переименование или удаление существующего поля.
- Изменение типа поля.
- Изменение семантики (например, `last_confirmed` начинает означать что-то другое).

### Процедура миграции

1. Подними версию схемы: добавь поле `"schema_version": 2` в корень `apps.json`.
2. Напиши миграцию в `scraper/aggregate.py`:
   ```python
   def _migrate_v1_to_v2(data: dict) -> dict:
       data["schema_version"] = 2
       # ...
       return data
   ```
3. Вызови миграцию в `load_existing()` если `schema_version` отсутствует или меньше актуальной.
4. Обнови этот файл и `docs/SCHEMA.md` (создай при необходимости).
5. Добавь тест в `tests/test_aggregate.py`, проверяющий миграцию на старом снапшоте.

## Категории

Список синхронизирован между двумя файлами:

- `scraper/aliases.yaml` — поле `category` у каждого приложения и `default_category`
- `scraper/render_readme.py` — ключи в `CATEGORY_TITLES`

**Добавление новой категории:**
1. Ключ в `CATEGORY_TITLES` (с эмодзи и русским названием).
2. Использование в `aliases.yaml`.
3. Опционально: добавь в `docs/CATEGORIES.md` (создай при необходимости).

Несинхронизированная категория не сломает скрипт — приложение просто попадёт в раздел без заголовка. Это бажно, но не критично.

## Снапшоты

`data/snapshots/<YYYY-MM-DD>.json` — сырой результат конкретного запуска:

```json
{
  "date": "2026-05-18",
  "run_results": {
    "hitech_mail": [{"name": "Ozon", "category": "marketplace"}, ...],
    "rozetked": [...]
  }
}
```

Снапшоты — это **результат после нормализации**, но **до мержа с историей**. Они нужны для:
- Дебага парсеров (что вернул источник в день X?).
- Восстановления `apps.json` при ошибке (можно перезаписать, прогнав `aggregate` поверх архива снапшотов).
- Анализа динамики (когда какое приложение появилось/пропало в каком источнике).

**Не удаляй снапшоты.** Они компактны, их можно хранить бесконечно.
