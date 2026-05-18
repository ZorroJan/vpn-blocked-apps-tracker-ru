# Project: vpn-blocked-apps-tracker

Автоматизированный трекер российских приложений, блокирующих доступ при включённом VPN. GitHub Actions запускает Python-скрипт раз в сутки, скрипт парсит несколько СМИ, нормализует названия по словарю синонимов, мержит с историей и обновляет `README.md` + `data/apps.json`.

## Stack

- Python 3.11, `requests` + `beautifulsoup4` + `pyyaml`, `pytest`
- GitHub Actions для расписания
- Никаких внешних сервисов, БД, API-ключей

## Layout

```
scraper/           # пайплайн: main.py → sources/ → normalize → aggregate → render_readme
  sources/         # один файл = один источник, экспортирует parse(html) -> list[str]
  aliases.yaml     # канонические имена приложений ↔ варианты написания
  sources.yaml     # список источников (URL + имя парсера)
data/
  apps.json        # машиночитаемый список (генерируется)
  snapshots/       # сырые результаты каждого запуска, для отладки
tests/             # pytest, без сетевых запросов
.github/workflows/ # daily update
```

Полное описание архитектуры: @scraper/README.md
Roadmap и текущие задачи: @docs/ROADMAP.md

## Commands

```bash
pip install -r requirements.txt
pytest tests/ -v              # все тесты офлайновые
python -m scraper.main         # полный прогон (ходит в сеть)
```

## Hard rules

- **Не редактировать корневой `README.md` и `data/apps.json` руками** — оба регенерируются `scraper/main.py`. Правки уйдут на следующем запуске.
- **Каждое новое приложение → правка `scraper/aliases.yaml`**, не правка кода. Категории, синонимы — всё там.
- **Каждый новый источник → правка `scraper/sources.yaml` + новый файл в `scraper/sources/`** по тому же шаблону, что и существующие парсеры. Не трогать `main.py` для добавления источников.
- **Не удалять `data/snapshots/`** — это история запусков для дебага парсеров.
- **Тесты не должны ходить в сеть.** Парсеры тестируются на фиксированных HTML-фикстурах (см. @.claude/rules/testing.md).
- **Перед коммитом изменений в `scraper/` — `pytest tests/ -v` должен быть зелёным.**

## Conventions

- Парсер источника обязан экспортировать `parse(html: str) -> list[str]`. Возвращает сырые строки, нормализация — отдельный этап.
- Категории приложений в `aliases.yaml` должны совпадать с ключами `CATEGORY_TITLES` в `scraper/render_readme.py`. Новая категория → правка обоих файлов.
- ё/е считаются одной буквой при матчинге (см. `Normalizer._normalize_text`).
- Изменения, которые ломают формат `apps.json`, требуют миграции — см. @.claude/rules/data-format.md.

## Detailed rules (загружаются при работе с релевантными файлами)

- @.claude/rules/parsers.md — как писать/чинить парсеры в `scraper/sources/`
- @.claude/rules/testing.md — правила для `tests/`
- @.claude/rules/data-format.md — схема `apps.json` и правила её эволюции
- @.claude/rules/workflow.md — GitHub Actions и деплой
