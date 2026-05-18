"""Aggregate findings across sources and merge with the existing dataset.

The data file (apps.json) keeps a per-app record:
- first_seen: ISO date when first detected by any source
- last_confirmed: ISO date of the most recent run that detected it
- sources: list of source ids that have ever reported it
- last_sources: list of source ids that reported it on the most recent run
- confidence: derived field, "confirmed" if 2+ sources agree on last run, else "reported"
- status: "active" if last_confirmed within ACTIVE_DAYS, else "archived"

This design is robust to source outages: a single parser breaking won't
wipe everything, because we only update last_confirmed for apps we actually
saw this run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ACTIVE_DAYS = 30


@dataclass
class AppRecord:
    name: str
    category: str
    first_seen: str
    last_confirmed: str
    sources: list[str]
    last_sources: list[str]
    confidence: str  # "confirmed" or "reported"
    status: str  # "active" or "archived"


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_existing(data_path: Path) -> dict:
    if not data_path.exists():
        return {"updated_at": None, "apps": []}
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_run(
    existing: dict,
    run_results: dict[str, list[dict]],  # source_id -> list of {name, category}
    today: str | None = None,
) -> dict:
    """Merge a fresh run's findings into the existing dataset.

    run_results maps source_id to a list of {name, category} dicts. Returns
    the updated dataset (new dict, doesn't mutate input).
    """
    today = today or _today_iso()

    # Build: app_name -> set of source_ids that saw it this run
    seen_this_run: dict[str, set[str]] = {}
    categories: dict[str, str] = {}
    for source_id, apps in run_results.items():
        for app in apps:
            name = app["name"]
            seen_this_run.setdefault(name, set()).add(source_id)
            categories[name] = app["category"]

    # Index existing apps by name
    existing_by_name: dict[str, dict] = {a["name"]: a for a in existing.get("apps", [])}

    updated_apps: list[dict] = []
    all_names = set(existing_by_name.keys()) | set(seen_this_run.keys())

    for name in all_names:
        prev = existing_by_name.get(name)
        current_sources = seen_this_run.get(name, set())

        if prev is None:
            # New app
            record = AppRecord(
                name=name,
                category=categories.get(name, "other"),
                first_seen=today,
                last_confirmed=today,
                sources=sorted(current_sources),
                last_sources=sorted(current_sources),
                confidence="confirmed" if len(current_sources) >= 2 else "reported",
                status="active",
            )
            updated_apps.append(asdict(record))
        else:
            # Existing app — update if seen this run, else age it
            if current_sources:
                merged_sources = sorted(set(prev.get("sources", [])) | current_sources)
                record = {
                    **prev,
                    "category": categories.get(name, prev.get("category", "other")),
                    "last_confirmed": today,
                    "sources": merged_sources,
                    "last_sources": sorted(current_sources),
                    "confidence": "confirmed" if len(current_sources) >= 2 else "reported",
                    "status": "active",
                }
            else:
                # Not seen this run — check if it should be archived
                last_confirmed = datetime.fromisoformat(prev["last_confirmed"])
                today_dt = datetime.fromisoformat(today)
                age_days = (today_dt - last_confirmed).days
                status = "archived" if age_days > ACTIVE_DAYS else "active"
                record = {**prev, "status": status, "last_sources": []}
            updated_apps.append(record)

    # Sort: active confirmed first, then active reported, then archived
    def sort_key(a: dict) -> tuple:
        status_rank = 0 if a["status"] == "active" else 1
        conf_rank = 0 if a["confidence"] == "confirmed" else 1
        return (status_rank, conf_rank, a["name"])

    updated_apps.sort(key=sort_key)

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "apps": updated_apps,
    }


def save(data_path: Path, dataset: dict) -> None:
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
