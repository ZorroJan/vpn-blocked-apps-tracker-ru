"""Tests for the aggregator (merge logic with history)."""

from scraper.aggregate import merge_run


def test_new_apps_added() -> None:
    existing = {"updated_at": None, "apps": []}
    run = {
        "src1": [{"name": "Ozon", "category": "marketplace"}],
        "src2": [{"name": "Ozon", "category": "marketplace"}],
    }
    result = merge_run(existing, run, today="2026-05-18")
    assert len(result["apps"]) == 1
    app = result["apps"][0]
    assert app["name"] == "Ozon"
    assert app["confidence"] == "confirmed"
    assert app["status"] == "active"
    assert app["first_seen"] == "2026-05-18"
    assert sorted(app["sources"]) == ["src1", "src2"]


def test_single_source_is_reported_only() -> None:
    existing = {"updated_at": None, "apps": []}
    run = {"src1": [{"name": "Ozon", "category": "marketplace"}]}
    result = merge_run(existing, run, today="2026-05-18")
    assert result["apps"][0]["confidence"] == "reported"


def test_re_run_updates_last_confirmed() -> None:
    existing = {
        "updated_at": None,
        "apps": [
            {
                "name": "Ozon",
                "category": "marketplace",
                "first_seen": "2026-04-14",
                "last_confirmed": "2026-04-14",
                "sources": ["src1"],
                "last_sources": ["src1"],
                "confidence": "reported",
                "status": "active",
            }
        ],
    }
    run = {"src1": [{"name": "Ozon", "category": "marketplace"}]}
    result = merge_run(existing, run, today="2026-05-18")
    app = result["apps"][0]
    assert app["first_seen"] == "2026-04-14"  # preserved
    assert app["last_confirmed"] == "2026-05-18"  # updated


def test_missing_app_within_30_days_stays_active() -> None:
    existing = {
        "updated_at": None,
        "apps": [
            {
                "name": "Ozon",
                "category": "marketplace",
                "first_seen": "2026-04-14",
                "last_confirmed": "2026-05-10",
                "sources": ["src1"],
                "last_sources": ["src1"],
                "confidence": "reported",
                "status": "active",
            }
        ],
    }
    result = merge_run(existing, run_results={}, today="2026-05-18")
    app = result["apps"][0]
    assert app["status"] == "active"  # only 8 days old
    assert app["last_sources"] == []


def test_missing_app_past_30_days_archived() -> None:
    existing = {
        "updated_at": None,
        "apps": [
            {
                "name": "Ozon",
                "category": "marketplace",
                "first_seen": "2026-03-01",
                "last_confirmed": "2026-04-01",
                "sources": ["src1"],
                "last_sources": ["src1"],
                "confidence": "reported",
                "status": "active",
            }
        ],
    }
    result = merge_run(existing, run_results={}, today="2026-05-18")
    assert result["apps"][0]["status"] == "archived"


def test_archived_can_become_active_again() -> None:
    existing = {
        "updated_at": None,
        "apps": [
            {
                "name": "Ozon",
                "category": "marketplace",
                "first_seen": "2026-03-01",
                "last_confirmed": "2026-04-01",
                "sources": ["src1"],
                "last_sources": [],
                "confidence": "reported",
                "status": "archived",
            }
        ],
    }
    run = {"src1": [{"name": "Ozon", "category": "marketplace"}]}
    result = merge_run(existing, run, today="2026-05-18")
    assert result["apps"][0]["status"] == "active"
