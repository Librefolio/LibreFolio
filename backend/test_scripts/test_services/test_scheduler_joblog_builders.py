"""Scheduler job log — the entry builders and the append/rotate/read round trip.

Companion to ``test_scheduler_jobs.py``: that file drives the two job bodies end to
end, this one pins the *shape* of what they write and the log file's own lifecycle.

Everything here is pure: no database, no server. The only side effect is the JSONL
file, redirected into a per-test sandbox directory through ``joblog.get_data_dir``
(same pattern as ``test_scheduler_joblog_misc.py``, distinct suffix), so the eight
parallel workers never share a log. Because that file is owned entirely by the test
that wrote it, asserting on its exact number of lines is asserting on the test's own
data.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.schemas.prices import FACurrentPriceItem
from backend.app.schemas.refresh import FARefreshResult, FXSyncPairResult, SyncStatus
from backend.app.services.scheduler import joblog


@pytest.fixture
def isolated_joblog_dir(monkeypatch):
    """Use a repo-local sandbox for the scheduler log file."""
    root = DEFAULT_TEST_DATA_DIR / f"joblog_builders_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(joblog, "get_data_dir", lambda: root)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _log_file(root):
    return root / "logs" / "scheduler_jobs.jsonl"


def _pick(items: list[dict], key: str, value) -> dict:
    """Pick the one item identified by ``key == value`` — never by position."""
    matches = [item for item in items if item.get(key) == value]
    assert len(matches) == 1, f"expected one item with {key}={value!r}, got {len(matches)}"
    return matches[0]


# ============================================================================
# append_entry / read_entries round trip
# ============================================================================


def test_append_entry_creates_the_log_and_reads_back_newest_first(isolated_joblog_dir):
    """append_entry creates logs/ on demand; read_entries returns newest first."""
    assert not _log_file(isolated_joblog_dir).exists()

    joblog.append_entry({"ts": datetime(2026, 3, 1, 9, 0, tzinfo=UTC).isoformat(), "job": "first"})
    joblog.append_entry({"ts": datetime(2026, 3, 1, 10, 0, tzinfo=UTC).isoformat(), "job": "second"})

    assert _log_file(isolated_joblog_dir).exists()
    entries = joblog.read_entries()
    # This log holds only what this test appended, so the ordering is the subject.
    assert [entry["job"] for entry in entries] == ["second", "first"]


def test_append_entry_serialises_values_json_cannot_encode(isolated_joblog_dir):
    """default=str keeps a Decimal or a date from killing the scheduler run.

    Job entries are built from provider results, and those carry Decimals and dates.
    Without the fallback encoder append_entry would raise inside the job body and the
    run would be lost, not just its log line.
    """
    joblog.append_entry(
        {
            "ts": datetime(2026, 3, 2, 9, 0, tzinfo=UTC).isoformat(),
            "job": "encodable",
            "value": Decimal("12.34"),
            "when": datetime(2026, 3, 2, 9, 0, tzinfo=UTC).date(),
        }
    )

    entries = joblog.read_entries()
    assert len(entries) == 1
    written = _pick(entries, "job", "encodable")
    assert written["value"] == "12.34"
    assert written["when"] == "2026-03-02"


def test_append_entry_rotates_the_log_and_leaves_no_temp_file(isolated_joblog_dir):
    """Appending past MAX_ENTRIES drops the oldest lines through the public path."""
    path = _log_file(isolated_joblog_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for index in range(joblog.MAX_ENTRIES):
            handle.write(json.dumps({"ts": datetime(2026, 3, 3, tzinfo=UTC).isoformat(), "job": f"seed-{index}"}) + "\n")

    joblog.append_entry({"ts": datetime(2026, 3, 4, tzinfo=UTC).isoformat(), "job": "appended"})

    entries = joblog.read_entries()
    assert len(entries) == joblog.MAX_ENTRIES
    jobs_seen = {entry["job"] for entry in entries}
    assert "appended" in jobs_seen
    assert "seed-0" not in jobs_seen, "the oldest line should have been rotated out"
    assert "seed-1" in jobs_seen, "rotation must drop exactly the overflow"
    # os.replace must not leave the intermediate file behind.
    assert not path.with_suffix(".tmp").exists()


def test_append_entry_below_the_cap_does_not_rotate(isolated_joblog_dir):
    """A short log is left alone — the rotation check has a "nothing to do" side."""
    joblog.append_entry({"ts": datetime(2026, 3, 5, tzinfo=UTC).isoformat(), "job": "short"})

    with open(_log_file(isolated_joblog_dir), encoding="utf-8") as handle:
        assert len([line for line in handle if line.strip()]) == 1


def test_read_entries_returns_empty_list_when_the_log_was_never_written(isolated_joblog_dir):
    """No file yet is a normal state (fresh install), not an error."""
    assert joblog.read_entries() == []


def test_read_entries_skips_blank_and_truncated_lines(isolated_joblog_dir):
    """A half-written line after a crash must cost one entry, not the whole log."""
    path = _log_file(isolated_joblog_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": datetime(2026, 3, 6, 8, 0, tzinfo=UTC).isoformat(), "job": "good-1"}) + "\n")
        handle.write("\n")
        handle.write('{"ts": "2026-03-06T09:00:00+00:00", "job": "trun\n')
        handle.write(json.dumps({"ts": datetime(2026, 3, 6, 10, 0, tzinfo=UTC).isoformat(), "job": "good-2"}) + "\n")

    entries = joblog.read_entries()

    assert [entry["job"] for entry in entries] == ["good-2", "good-1"]


def test_read_entries_ignores_an_unparseable_since_value(isolated_joblog_dir):
    """A malformed `since` degrades to "no filter", it does not empty the response.

    `since` arrives from the API query string, so it is user input.
    """
    joblog.append_entry({"ts": datetime(2026, 3, 7, 8, 0, tzinfo=UTC).isoformat(), "job": "kept"})

    entries = joblog.read_entries(since="yesterday-ish")

    assert [entry["job"] for entry in entries] == ["kept"]


def test_read_entries_drops_entries_without_a_usable_ts_when_filtering(isolated_joblog_dir):
    """With `since` active, an entry whose ts is missing or invalid cannot qualify."""
    path = _log_file(isolated_joblog_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"job": "no-ts"}) + "\n")
        handle.write(json.dumps({"ts": "not-a-timestamp", "job": "bad-ts"}) + "\n")
        handle.write(json.dumps({"ts": datetime(2026, 3, 8, 12, 0, tzinfo=UTC).isoformat(), "job": "good"}) + "\n")

    entries = joblog.read_entries(since=datetime(2026, 3, 8, 0, 0, tzinfo=UTC).isoformat())

    assert [entry["job"] for entry in entries] == ["good"]
    # Without the filter the same three lines all come back.
    assert len(joblog.read_entries()) == 3


# ============================================================================
# build_current_price_entry
# ============================================================================


def test_build_current_price_entry_shape():
    """Per-item flags, optional keys and the summary derived from them."""
    results = [
        FACurrentPriceItem(asset_id=11, value=Decimal("10.5"), currency="EUR", source="provider:double"),
        FACurrentPriceItem(asset_id=12, value=Decimal("7.25"), currency="EUR", source="provider:double"),
        FACurrentPriceItem(asset_id=13, error="provider timeout"),
    ]
    names = {11: "With Icon", 12: "Without Icon"}  # 13 deliberately absent
    icons = {11: "https://example.invalid/11.png", 12: None}  # 13 deliberately absent

    entry = joblog.build_current_price_entry(results, names, 1.25, "partial", asset_icons=icons)

    assert entry["job"] == "current_price"
    assert entry["status"] == "partial"
    assert entry["duration_s"] == 1.25
    assert entry["summary"] == {"ok": 2, "err": 1}
    assert datetime.fromisoformat(entry["ts"]).tzinfo is not None

    with_icon = _pick(entry["items"], "asset_id", 11)
    assert with_icon == {"asset_id": 11, "name": "With Icon", "ok": True, "icon_url": "https://example.invalid/11.png"}

    without_icon = _pick(entry["items"], "asset_id", 12)
    assert without_icon == {"asset_id": 12, "name": "Without Icon", "ok": True}

    failed = _pick(entry["items"], "asset_id", 13)
    # Unknown asset id falls back to "?" rather than raising inside the job.
    assert failed == {"asset_id": 13, "name": "?", "ok": False, "error": "provider timeout"}


def test_build_current_price_entry_without_icons_or_results():
    """The icons argument is optional and an empty run is still a well-formed entry."""
    entry = joblog.build_current_price_entry([], {}, 0.0, "ok")

    assert entry["items"] == []
    assert entry["summary"] == {"ok": 0, "err": 0}

    single = joblog.build_current_price_entry([FACurrentPriceItem(asset_id=21, value=Decimal("1"))], {21: "Solo"}, 0.1, "ok")
    assert _pick(single["items"], "asset_id", 21) == {"asset_id": 21, "name": "Solo", "ok": True}


# ============================================================================
# build_history_sync_entry
# ============================================================================


def _asset_result(asset_id: int, *, ok: bool, provider: str | None, errors: list[str]) -> FARefreshResult:
    return FARefreshResult(
        asset_id=asset_id,
        status=SyncStatus.OK if ok else SyncStatus.FAILED,
        provider_used=provider,
        points_changed=3 if ok else 0,
        events_changed=1 if ok else 0,
        errors=errors,
    )


def _fx_result(pair: str, *, ok: bool, provider: str | None, errors: list[str]) -> FXSyncPairResult:
    return FXSyncPairResult(
        pair=pair,
        status=SyncStatus.OK if ok else SyncStatus.FAILED,
        provider_used=provider,
        points_changed=4 if ok else 0,
        errors=errors,
    )


def test_build_history_sync_entry_shape():
    """Assets and FX halves, their optional keys, and the four summary counters."""
    assets = [
        _asset_result(31, ok=True, provider="mockprov", errors=[]),
        _asset_result(32, ok=False, provider=None, errors=["boom"]),
    ]
    fx = [
        _fx_result("EUR-USD", ok=True, provider="MOCKFX", errors=[]),
        _fx_result("GBP-USD", ok=False, provider=None, errors=["no data"]),
    ]
    names = {31: "Alpha"}  # 32 deliberately absent
    icons = {31: "https://example.invalid/31.png", 32: None}

    entry = joblog.build_history_sync_entry(assets, fx, names, 4.5, "partial", asset_icons=icons)

    assert entry["job"] == "history_sync"
    assert entry["status"] == "partial"
    assert entry["duration_s"] == 4.5
    assert entry["summary"] == {"assets_ok": 1, "assets_err": 1, "fx_ok": 1, "fx_err": 1}
    assert datetime.fromisoformat(entry["ts"]).tzinfo is not None

    ok_asset = _pick(entry["assets"], "asset_id", 31)
    assert ok_asset == {
        "asset_id": 31,
        "name": "Alpha",
        "status": "ok",
        "icon_url": "https://example.invalid/31.png",
        "provider": "mockprov",
        "prices_changed": 3,
        "events_changed": 1,
    }

    failed_asset = _pick(entry["assets"], "asset_id", 32)
    # No icon, no provider: both keys are omitted rather than emitted as null.
    assert failed_asset == {
        "asset_id": 32,
        "name": "?",
        "status": "failed",
        "errors": ["boom"],
        "prices_changed": 0,
        "events_changed": 0,
    }

    ok_pair = _pick(entry["fx"], "pair", "EUR-USD")
    assert ok_pair == {"pair": "EUR-USD", "status": "ok", "base": "EUR", "quote": "USD", "provider": "MOCKFX", "points_changed": 4}

    failed_pair = _pick(entry["fx"], "pair", "GBP-USD")
    assert failed_pair == {"pair": "GBP-USD", "status": "failed", "base": "GBP", "quote": "USD", "errors": ["no data"], "points_changed": 0}


def test_build_history_sync_entry_without_icons_or_results():
    """The icons argument is optional and an empty run is still a well-formed entry."""
    entry = joblog.build_history_sync_entry([], [], {}, 0.0, "ok")

    assert entry["assets"] == []
    assert entry["fx"] == []
    assert entry["summary"] == {"assets_ok": 0, "assets_err": 0, "fx_ok": 0, "fx_err": 0}

    no_icons = joblog.build_history_sync_entry([_asset_result(41, ok=True, provider=None, errors=[])], [], {41: "Solo"}, 0.1, "ok")
    solo = _pick(no_icons["assets"], "asset_id", 41)
    assert "icon_url" not in solo
    assert "provider" not in solo


def test_build_history_sync_entry_counts_partial_and_skipped_as_not_ok():
    """Only SyncStatus.OK feeds the *_ok counters; partial and skipped do not."""
    assets = [
        FARefreshResult(asset_id=51, status=SyncStatus.PARTIAL),
        FARefreshResult(asset_id=52, status=SyncStatus.SKIPPED),
        FARefreshResult(asset_id=53, status=SyncStatus.OK),
    ]
    fx = [
        FXSyncPairResult(pair="EUR-CHF", status=SyncStatus.PARTIAL),
        FXSyncPairResult(pair="EUR-SEK", status=SyncStatus.SKIPPED),
    ]

    entry = joblog.build_history_sync_entry(assets, fx, {}, 0.5, "partial")

    assert entry["summary"] == {"assets_ok": 1, "assets_err": 2, "fx_ok": 0, "fx_err": 2}
    assert _pick(entry["assets"], "asset_id", 51)["status"] == "partial"
    assert _pick(entry["fx"], "pair", "EUR-SEK")["status"] == "skipped"


def test_sync_status_must_stay_a_strenum_or_every_summary_counter_silently_zeroes():
    """Non-regression guard on `str(r.status) == "ok"` in build_history_sync_entry.

    The builder serialises each result's status with `str(...)` and then counts the
    literal string "ok". That works only because `SyncStatus` is a `StrEnum`
    (backend/app/schemas/refresh.py). If it were ever moved back to `(str, Enum)`,
    `str(SyncStatus.OK)` would become "SyncStatus.OK": the comparison would never
    match, `assets_ok`/`fx_ok` would report 0 for a perfectly successful run, and the
    per-item `status` written into the JSONL would change shape for every frontend
    reader — all without a single exception being raised. This test exists to turn
    that silent regression into a red line.
    """
    assert str(SyncStatus.OK) == "ok"
    assert str(SyncStatus.FAILED) == "failed"
    assert str(SyncStatus.PARTIAL) == "partial"
    assert str(SyncStatus.SKIPPED) == "skipped"

    # And the consequence, asserted through the builder itself rather than inferred.
    entry = joblog.build_history_sync_entry(
        [FARefreshResult(asset_id=61, status=SyncStatus.OK)],
        [FXSyncPairResult(pair="EUR-USD", status=SyncStatus.OK)],
        {61: "Alpha"},
        0.2,
        "ok",
    )
    assert entry["summary"]["assets_ok"] == 1
    assert entry["summary"]["fx_ok"] == 1
    assert _pick(entry["assets"], "asset_id", 61)["status"] == "ok"
    assert _pick(entry["fx"], "pair", "EUR-USD")["status"] == "ok"
