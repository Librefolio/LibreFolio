"""Scheduler job log — JSONL file with per-item detail and rotation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.config import get_data_dir

MAX_ENTRIES = 500


def _log_path() -> Path:
    return Path(get_data_dir()) / "logs" / "scheduler_jobs.jsonl"


def append_entry(entry: dict[str, Any]) -> None:
    """Append a single JSON line to the job log, rotating if needed."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, default=str)

    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    _rotate_if_needed(path)


def _rotate_if_needed(path: Path) -> None:
    """Keep only the last MAX_ENTRIES lines."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_ENTRIES:
            keep = lines[-MAX_ENTRIES:]
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.writelines(keep)
            os.replace(str(tmp), str(path))
    except OSError:
        pass


def read_entries(since: str | None = None) -> list[dict[str, Any]]:
    """Read log entries in reverse chronological order (newest first).

    Args:
        since: ISO-8601 timestamp string. Only entries with ts >= since
               are returned. If None, all entries are returned.

    Returns:
        List of parsed log entry dicts.
    """
    path = _log_path()
    if not path.exists():
        return []

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    # Parse and optionally filter by timestamp
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except (ValueError, TypeError):
            pass

    entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if since_dt:
            try:
                entry_dt = datetime.fromisoformat(entry["ts"])
                if entry_dt < since_dt:
                    continue
            except (KeyError, ValueError, TypeError):
                continue

        entries.append(entry)

    return entries


def build_current_price_entry(
    results: list,
    asset_names: dict[int, str],
    duration_s: float,
    status: str,
    asset_icons: dict[int, str | None] | None = None,
) -> dict[str, Any]:
    """Build a JSONL entry for a current-price refresh run."""
    icons = asset_icons or {}
    items = []
    for r in results:
        item: dict[str, Any] = {
            "asset_id": r.asset_id,
            "name": asset_names.get(r.asset_id, "?"),
            "ok": r.value is not None,
        }
        if icons.get(r.asset_id):
            item["icon_url"] = icons[r.asset_id]
        if r.error:
            item["error"] = r.error
        items.append(item)

    ok_count = sum(1 for i in items if i["ok"])
    return {
        "ts": datetime.now().astimezone().isoformat(),
        "job": "current_price",
        "duration_s": duration_s,
        "status": status,
        "summary": {"ok": ok_count, "err": len(items) - ok_count},
        "items": items,
    }


def build_history_sync_entry(
    asset_results: list,
    fx_results: list,
    asset_names: dict[int, str],
    duration_s: float,
    status: str,
    asset_icons: dict[int, str | None] | None = None,
) -> dict[str, Any]:
    """Build a JSONL entry for a history-sync run."""
    icons = asset_icons or {}
    assets = []
    for r in asset_results:
        item: dict[str, Any] = {
            "asset_id": r.asset_id,
            "name": asset_names.get(r.asset_id, "?"),
            "status": str(r.status),
        }
        if icons.get(r.asset_id):
            item["icon_url"] = icons[r.asset_id]
        if r.errors:
            item["errors"] = r.errors
        if r.provider_used:
            item["provider"] = r.provider_used
        item["prices_changed"] = r.points_changed
        item["events_changed"] = getattr(r, "events_changed", 0)
        assets.append(item)

    fx = []
    for r in fx_results:
        pair_parts = r.pair.split("-") if hasattr(r, "pair") else []
        item: dict[str, Any] = {
            "pair": r.pair,
            "status": str(r.status),
        }
        if len(pair_parts) == 2:
            item["base"] = pair_parts[0]
            item["quote"] = pair_parts[1]
        if r.errors:
            item["errors"] = r.errors
        if r.provider_used:
            item["provider"] = r.provider_used
        item["points_changed"] = r.points_changed
        fx.append(item)

    asset_ok = sum(1 for a in assets if a["status"] == "ok")
    fx_ok = sum(1 for f in fx if f["status"] == "ok")

    return {
        "ts": datetime.now().astimezone().isoformat(),
        "job": "history_sync",
        "duration_s": duration_s,
        "status": status,
        "summary": {
            "assets_ok": asset_ok,
            "assets_err": len(assets) - asset_ok,
            "fx_ok": fx_ok,
            "fx_err": len(fx) - fx_ok,
        },
        "assets": assets,
        "fx": fx,
    }
