"""Builds every panel (in parallel) into one JSON payload. Shared by the API and the CLI."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from launchpad.panels import PANELS

log = logging.getLogger(__name__)


def build_panel(panel) -> dict:
    """A failing data source only breaks its own panel, not the page."""
    try:
        return panel.build()
    except Exception as exc:
        log.exception("panel %s failed", panel.id)
        return {"id": panel.id, "title": panel.title, "type": "error", "error": str(exc)}


def build_panels() -> dict:
    with ThreadPoolExecutor(max_workers=len(PANELS)) as pool:
        panels = list(pool.map(build_panel, PANELS))
    return {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "panels": panels,
    }
