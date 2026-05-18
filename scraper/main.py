"""Main entry point for the scraper.

Pipeline:
1. Load sources from sources.yaml
2. Fetch HTML from each source (with safety: failures don't kill the run)
3. Run each source's parser to extract raw app names
4. Normalize raw names to canonical app records via aliases.yaml
5. Merge with existing data/apps.json (history-aware)
6. Save data/apps.json and regenerate README.md
7. Save a snapshot of this run for audit/debugging
"""

from __future__ import annotations

import importlib
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

from scraper.normalize import Normalizer
from scraper.aggregate import merge_run, load_existing, save as save_dataset
from scraper.render_readme import generate as generate_readme, save as save_readme


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_DIR = REPO_ROOT / "scraper"
DATA_DIR = REPO_ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

USER_AGENT = (
    "Mozilla/5.0 (compatible; vpn-blocked-apps-tracker/1.0; "
    "+https://github.com/YOUR_USERNAME/vpn-blocked-apps-tracker)"
)
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 3  # seconds between source fetches, to be polite

# Safety: if a source's parser previously returned >= MIN_EXPECTED apps
# but now returns 0, treat as a parser failure and skip rather than wipe data.
MIN_EXPECTED_AFTER_HEALTHY = 1


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("scraper")


def fetch(url: str) -> str | None:
    """Fetch a URL with reasonable defaults. Returns HTML or None on failure."""
    try:
        log.info(f"Fetching {url}")
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.9"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


def run_source(source: dict, normalizer: Normalizer) -> list[dict] | None:
    """Run a single source's parser. Returns list of {name, category} dicts or None on failure."""
    parser_name = source["parser"]
    try:
        module = importlib.import_module(f"scraper.sources.{parser_name}")
    except ImportError as e:
        log.error(f"Cannot import parser '{parser_name}': {e}")
        return None

    html = fetch(source["url"])
    if html is None:
        return None

    try:
        raw_items = module.parse(html)
    except Exception as e:
        log.exception(f"Parser '{parser_name}' raised: {e}")
        return None

    log.info(f"Source '{source['id']}' parser returned {len(raw_items)} raw items")

    matched = normalizer.normalize_list(raw_items)
    log.info(f"Source '{source['id']}' matched {len(matched)} known apps")

    if len(matched) < MIN_EXPECTED_AFTER_HEALTHY:
        log.warning(
            f"Source '{source['id']}' returned suspiciously few matches "
            f"({len(matched)}). Skipping to avoid corrupting data."
        )
        return None

    return [{"name": app.canonical, "category": app.category} for app in matched]


def main() -> int:
    log.info("=" * 60)
    log.info("Starting VPN-blocked apps tracker update")
    log.info("=" * 60)

    # Load configs
    with open(SCRAPER_DIR / "sources.yaml", "r", encoding="utf-8") as f:
        sources_config = yaml.safe_load(f)["sources"]

    normalizer = Normalizer(SCRAPER_DIR / "aliases.yaml")
    log.info(f"Loaded {len(normalizer.apps)} known apps from aliases.yaml")

    # Run each source
    run_results: dict[str, list[dict]] = {}
    for source in sources_config:
        if not source.get("enabled", True):
            log.info(f"Skipping disabled source '{source['id']}'")
            continue

        result = run_source(source, normalizer)
        if result is not None:
            run_results[source["id"]] = result

        time.sleep(REQUEST_DELAY)

    if not run_results:
        log.error("All sources failed. Aborting to preserve existing data.")
        return 1

    log.info(f"Successfully scraped {len(run_results)}/{len(sources_config)} sources")

    # Merge with existing data
    data_path = DATA_DIR / "apps.json"
    existing = load_existing(data_path)
    log.info(f"Existing dataset has {len(existing.get('apps', []))} apps")

    updated = merge_run(existing, run_results)
    log.info(f"Updated dataset has {len(updated['apps'])} apps")

    save_dataset(data_path, updated)
    log.info(f"Saved {data_path}")

    # Snapshot
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    snapshot_path = SNAPSHOTS_DIR / f"{today}.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": today, "run_results": run_results},
            f, ensure_ascii=False, indent=2
        )
    log.info(f"Saved snapshot {snapshot_path}")

    # README
    readme_content = generate_readme(updated, sources_config)
    save_readme(REPO_ROOT / "README.md", readme_content)
    log.info("Regenerated README.md")

    log.info("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
