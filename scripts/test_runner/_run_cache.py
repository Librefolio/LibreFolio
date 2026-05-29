"""
Test Run Cache - resume interrupted test suites.

Persists pass/fail state for test suites so that --resume can skip
already-passed tests and restart from the last failure point.

Cache file: scripts/test_runner/.run_cache.json (gitignored)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_CACHE_FILE = Path(__file__).parent / ".run_cache.json"


def _load_all() -> dict:
    """Load the entire cache file."""
    if not _CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict) -> None:
    """Write the entire cache file."""
    _CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_cache(suite_key: str) -> dict:
    """Load cache entry for a specific suite."""
    all_data = _load_all()
    return all_data.get(suite_key, {"passed": [], "failed": None, "timestamp": None})


def mark_passed(suite_key: str, test_name: str) -> None:
    """Mark a test as passed within a suite."""
    all_data = _load_all()
    entry = all_data.setdefault(suite_key, {"passed": [], "failed": None, "timestamp": None})
    if test_name not in entry["passed"]:
        entry["passed"].append(test_name)
    if entry["failed"] == test_name:
        entry["failed"] = None
    entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
    _save_all(all_data)


def mark_failed(suite_key: str, test_name: str) -> None:
    """Mark a test as failed (stopping point for resume)."""
    all_data = _load_all()
    entry = all_data.setdefault(suite_key, {"passed": [], "failed": None, "timestamp": None})
    entry["failed"] = test_name
    entry["timestamp"] = datetime.now().isoformat(timespec="seconds")
    _save_all(all_data)


def is_passed(suite_key: str, test_name: str) -> bool:
    """Check if a test was already passed in the current run."""
    entry = load_cache(suite_key)
    return test_name in entry["passed"]


def clear_suite(suite_key: str) -> None:
    """Clear cache for a specific suite (full pass completed)."""
    all_data = _load_all()
    if suite_key in all_data:
        del all_data[suite_key]
        _save_all(all_data)


def clear_all() -> None:
    """Clear all cached run state (fresh start)."""
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()


def show_status() -> str:
    """Return a formatted status string of the current cache."""
    all_data = _load_all()
    if not all_data:
        return "No active test run cache. All suites start fresh."

    lines = []
    for suite_key, entry in all_data.items():
        passed = entry.get("passed", [])
        failed = entry.get("failed")
        ts = entry.get("timestamp", "?")
        lines.append(f"")
        lines.append(f"  \U0001f4cb {suite_key} (last update: {ts})")
        lines.append(f"     \u2705 Passed: {len(passed)} test(s)")
        if passed:
            for t in passed:
                lines.append(f"        \u2022 {t}")
        if failed:
            lines.append(f"     \u274c Stopped at: {failed}")
        else:
            lines.append(f"     \u23f3 Next: resume will continue from test #{len(passed) + 1}")

    return "\n".join(lines)
