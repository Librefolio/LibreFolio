"""
Small coverage tests for scheduler job log helpers.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.services.scheduler import joblog


@pytest.fixture
def isolated_joblog_dir(monkeypatch):
    """Use repo-local sandbox for scheduler log file."""
    root = DEFAULT_TEST_DATA_DIR / f"joblog_misc_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(joblog, "get_data_dir", lambda: root)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


def test_read_entries_returns_newest_first_and_applies_since_filter(isolated_joblog_dir):
    """read_entries returns reverse chronological subset."""
    log_path = isolated_joblog_dir / "logs" / "scheduler_jobs.jsonl"
    entries = [
        {"ts": datetime(2026, 1, 10, 8, 0, tzinfo=UTC).isoformat(), "job": "job-1"},
        {"ts": datetime(2026, 1, 11, 8, 0, tzinfo=UTC).isoformat(), "job": "job-2"},
        {"ts": datetime(2026, 1, 12, 8, 0, tzinfo=UTC).isoformat(), "job": "job-3"},
    ]
    _write_jsonl(log_path, entries)

    result = joblog.read_entries(since=entries[1]["ts"])

    assert [entry["job"] for entry in result] == ["job-3", "job-2"]


def test_rotate_if_needed_keeps_only_last_max_entries(isolated_joblog_dir):
    """Rotation trims oldest lines beyond MAX_ENTRIES."""
    log_path = isolated_joblog_dir / "logs" / "scheduler_jobs.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as handle:
        for index in range(joblog.MAX_ENTRIES + 3):
            handle.write(json.dumps({"idx": index}) + "\n")

    joblog._rotate_if_needed(log_path)

    with open(log_path, encoding="utf-8") as handle:
        kept_entries = [json.loads(line) for line in handle if line.strip()]

    assert len(kept_entries) == joblog.MAX_ENTRIES
    assert kept_entries[0]["idx"] == 3
    assert kept_entries[-1]["idx"] == joblog.MAX_ENTRIES + 2
