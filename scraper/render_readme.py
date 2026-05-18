"""Generate README.md from apps.json.

The README is the human-facing entry point. It groups apps by category,
shows confidence, source count, and dates. Archived apps live in a
separate collapsed section.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

CATEGORY_TITLES = {
    "marketplace": "🛒 Маркетплейсы",
    "streaming": "🎬 Стриминг и кинотеатры",
    "payments": "💳 Платежи",
    "yandex_services": "🟡 Сервисы Яндекса",
    "social": "💬 Соцсети",
    "mail": "📧 Почта",
    "delivery": "📦 Доставка",
    "retail": "🏪 Розничные сети",
    "travel": "✈️ Путешествия и транспорт",
    "maps": "🗺️ Карты",
    "jobs": "💼 Работа",
    "government": "🏛️ Госуслуги",
    "other": "❓ Прочее",
}

CONFIDENCE_BADGE = {
    "confirmed": "✅ подтверждено",
    "reported": "⚠️ упомянуто",
}


def _format_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return iso


def generate(dataset: dict, sources_config: list[dict]) -> str:
    """Render the dataset as a markdown README."""
    updated_at = dataset.get("updated_at", "")
    apps = dataset.get("apps", [])

    active = [a for a in apps if a["status"] == "active"]
    archived = [a for a in apps if a["status"] == "archived"]

    # Group active apps by category
    by_category: dict[str, list[dict]] = {}
    for app in active:
        by_category.setdefault(app["category"], []).append(app)

    lines: list[str] = []
    lines.append("# 🇷🇺 Российские приложения, которые не работают с VPN")
    lines.append("")
    lines.append(
        "Автоматически обновляемый список российских сайтов и приложений, "
        "которые блокируют доступ при включённом VPN. Данные собираются из "
        "открытых источников раз в сутки."
    )
    lines.append("")
    lines.append(f"**Последнее обновление:** {_format_date(updated_at[:10]) if updated_at else '—'}  ")
    lines.append(f"**Всего активных записей:** {len(active)}  ")
    lines.append(f"**В архиве:** {len(archived)}")
    lines.append("")
    lines.append("> ⚠️ Список собирается из сообщений СМИ и пользователей. "
                 "Блокировки могут применяться неравномерно: у одних пользователей "
                 "приложение не открывается с VPN, у других работает. "
                 "Многое зависит от конкретного VPN-протокола.")
    lines.append("")

    # Legend
    lines.append("## Обозначения")
    lines.append("")
    lines.append("- ✅ **подтверждено** — упоминается двумя и более источниками в последнем обновлении")
    lines.append("- ⚠️ **упомянуто** — упоминается одним источником в последнем обновлении")
    lines.append(f"- В архив попадают записи, не подтверждённые более 30 дней")
    lines.append("")

    # Sources
    lines.append("## Источники данных")
    lines.append("")
    for src in sources_config:
        if src.get("enabled", True):
            lines.append(f"- [{src['name']}]({src['url']})")
    lines.append("")

    # Active apps by category
    lines.append("## Активный список")
    lines.append("")
    if not active:
        lines.append("_Пока нет данных. Запустите сбор данных (см. ниже)._")
        lines.append("")
    else:
        for category in CATEGORY_TITLES:
            if category not in by_category:
                continue
            apps_in_cat = by_category[category]
            lines.append(f"### {CATEGORY_TITLES[category]}")
            lines.append("")
            lines.append("| Приложение | Статус | Источников | Впервые замечено | Последнее подтверждение |")
            lines.append("|---|---|---|---|---|")
            for app in apps_in_cat:
                badge = CONFIDENCE_BADGE.get(app["confidence"], app["confidence"])
                lines.append(
                    f"| **{app['name']}** | {badge} | {len(app['last_sources'])} | "
                    f"{_format_date(app['first_seen'])} | {_format_date(app['last_confirmed'])} |"
                )
            lines.append("")

    # Archived
    if archived:
        lines.append("## Архив")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Приложения, не подтверждённые более 30 дней (нажмите, чтобы развернуть)</summary>")
        lines.append("")
        lines.append("| Приложение | Категория | Последнее подтверждение |")
        lines.append("|---|---|---|")
        for app in archived:
            lines.append(
                f"| {app['name']} | {app.get('category', 'other')} | "
                f"{_format_date(app['last_confirmed'])} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("## Машиночитаемые данные")
    lines.append("")
    lines.append("Полный список доступен в виде JSON: [`data/apps.json`](data/apps.json)")
    lines.append("")
    lines.append("## Как это работает")
    lines.append("")
    lines.append("Скрипт парсит указанные источники раз в сутки через GitHub Actions, "
                 "нормализует названия приложений по словарю синонимов и обновляет "
                 "`data/apps.json` и этот README. Подробнее — в [`scraper/README.md`](scraper/README.md).")
    lines.append("")
    lines.append("## Лицензия и атрибуция")
    lines.append("")
    lines.append("Код — MIT. Данные собраны из публичных источников, "
                 "приведённых выше; права на оригинальные публикации принадлежат их авторам.")

    return "\n".join(lines)


def save(readme_path: Path, content: str) -> None:
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
