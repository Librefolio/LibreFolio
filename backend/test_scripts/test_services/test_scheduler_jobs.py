"""Scheduler job bodies — run_current_price_refresh / run_history_sync + the joblog
entries they produce.

Why doubles instead of the real service calls
---------------------------------------------
``AssetSourceManager.get_current_prices_bulk``, ``AssetSourceManager.bulk_refresh_prices``
and ``sync_pairs_bulk`` rewrite prices for **every** active asset and **every** FX route.
``Asset``, ``PriceHistory`` and ``FxRate`` carry no ``user_id``, so running those calls
for real would make this unit WRITE_GLOBAL and would rewrite data underneath every
concurrent unit — besides reaching third-party providers over the network.

Replacing the three entry points with doubles keeps the whole orchestration running for
real (select -> count -> classify -> state -> build entry -> append) while the global
write never happens. This unit is therefore READ.

Isolation
---------
* **joblog**: sandboxed through ``joblog.get_data_dir`` (fixture ``isolated_joblog_dir``),
  the same pattern as ``test_scheduler_joblog_misc.py`` with a distinct suffix. Every
  assertion on the log therefore reads a file this test owns entirely, which is why
  ``len(entries) == N`` is legitimate here.
* **scheduler state**: ``jobs.py`` mutates the ``SchedulerState`` object it is handed and
  never calls ``save_state()`` — only ``scheduler.py`` persists. A throwaway
  ``SchedulerState()`` per test is therefore complete isolation, no sandboxing needed.
* **database**: only SELECTs survive, and only in the "live schema" tests at the bottom of
  this file: the job's two, and the two lookups of the last saved dates (lot Z-5), read
  inside one explicit read transaction. Everywhere else ``jobs.AsyncSession`` is replaced,
  because the zero-active-assets path cannot be produced on a database other units are
  writing to, and so are the two lookups (``_install_fake_session``).

Lot Z7b: items the provider refused for too many requests
---------------------------------------------------------
An item whose ``error_code`` is ``"RATE_LIMITED"`` is **deferred**, whatever its status or
value: neither ok nor failed. The cases of the section "RATE_LIMITED items" pin how the
two jobs count them, the ``retry_at`` they write (now + the shortest ``retry_after`` of the
deferred items), the reset of the failure backoff by a run that ends, and the job log
(``deferred``/``retry_after`` per item, the deferred counters, ``retry_at``). The cases
written before Z7b pin a run without such items, which must not change; they compare the
summary without the deferred counters (``_counts``), which a run with nothing deferred
gains at 0 — pinned exactly by the Z7b cases.

Lot Z-5: the history sync reaches back to the last saved date
-------------------------------------------------------------
Each asset's window starts the day after its last saved price; the FX call, one for every
pair, starts the day after the last saved rate of the pair furthest behind. Never later
than the horizon's start (``today - horizon_days``), never earlier than
``HISTORY_CATCH_UP_MAX_DAYS`` (365) days ago; every window ends today. A run that reaches
back past the horizon says so in one event, "Scheduler: history sync reaches back", and
nowhere else: its state and its job log entry gain nothing. The section "Lot Z-5" pins
``_history_sync_start`` on a fixed day, then the job with the dates the two fake lookups of
``_install_fake_session`` give, the event behind a canary barrier, and the state and entry
of a run that reaches back; the two lookups meet the live database at the bottom. Those
lookups answer ``{}`` by default, so the cases written before Z-5 sync the horizon, as they
did. The job cases count from ``date.today()`` as the job does: the same-day assumption of
the cases above.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.db.models import FxConversionRoute, FxRate, PriceHistory
from backend.app.db.session import get_async_engine
from backend.app.schemas.prices import FACurrentPriceItem
from backend.app.schemas.refresh import (
    FABulkRefreshResponse,
    FARefreshResult,
    FXSyncBulkResponse,
    FXSyncPairResult,
    SyncDateRangeModel,
    SyncStatus,
)
from backend.app.services.platform.scheduler import joblog, jobs
from backend.app.services.platform.scheduler.state import JobState, SchedulerState

# ============================================================================
# Fixtures and doubles
# ============================================================================


@pytest.fixture
def isolated_joblog_dir(monkeypatch):
    """Use a repo-local sandbox for the scheduler log file.

    ``append_entry`` resolves ``get_data_dir()`` from the ``joblog`` module globals at
    call time, so patching it there also redirects the calls made through
    ``jobs.append_entry``. The uuid suffix keeps the eight parallel workers apart.
    """
    root = DEFAULT_TEST_DATA_DIR / f"scheduler_jobs_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(joblog, "get_data_dir", lambda: root)
    yield root
    shutil.rmtree(root, ignore_errors=True)


class _FakeScalars:
    """``.scalars()`` half of a SQLAlchemy result."""

    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeResult:
    """Result double answering both access shapes used by ``jobs.py``.

    ``run_current_price_refresh`` and the asset half of ``run_history_sync`` call
    ``.all()`` on a tuple select; the FX half calls ``.scalars().all()`` on an ORM
    select. Carrying both payloads on one result object lets a single fake session
    serve every ``execute()`` in a job without having to inspect the statement.
    """

    def __init__(self, asset_rows, routes):
        self._asset_rows = asset_rows
        self._routes = routes

    def all(self):
        return list(self._asset_rows)

    def scalars(self):
        return _FakeScalars(self._routes)


class _FakeSession:
    """Stand-in for ``AsyncSession(engine)`` — async context manager, no database.

    The job still builds its real SQLAlchemy statements (so a column that no longer
    exists still explodes at construction time); only the execution is replaced.
    """

    def __init__(self, asset_rows, routes, executed):
        self._asset_rows = asset_rows
        self._routes = routes
        self._executed = executed

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def execute(self, statement):
        self._executed.append(statement)
        return _FakeResult(self._asset_rows, self._routes)


def _install_fake_session(
    monkeypatch,
    *,
    asset_rows=(),
    routes=(),
    last_price_dates: dict[int, date] | None = None,
    last_fx_dates: dict[str, date] | None = None,
    lookups: dict | None = None,
):
    """Replace ``jobs.AsyncSession``; return the list of executed statements.

    Lot Z-5: the two lookups of the last saved dates, ``jobs._last_price_dates`` and
    ``jobs._last_fx_dates``, are replaced too. Like the real ones they answer, for what they
    are asked, the ids and slugs that have a date — from ``last_price_dates`` and
    ``last_fx_dates`` —, nothing by default: a case written before Z-5 syncs the horizon, as
    it did. ``raising=False``: until the code of Z-5 exists, ``jobs`` has no such attribute.
    ``lookups``, when given, records what each lookup was asked (``"asset_ids"``, ``"pairs"``).
    """
    executed: list = []

    def _factory(_engine):
        return _FakeSession(asset_rows, routes, executed)

    monkeypatch.setattr(jobs, "AsyncSession", _factory)

    saved_prices = dict(last_price_dates or {})
    saved_rates = dict(last_fx_dates or {})

    async def _fake_last_price_dates(session, asset_ids):
        assert isinstance(session, _FakeSession), f"_last_price_dates takes a session the job opened, not {session!r}"
        asked = list(asset_ids)
        if lookups is not None:
            lookups.setdefault("asset_ids", []).append(asked)
        return {asset_id: saved_prices[asset_id] for asset_id in asked if asset_id in saved_prices}

    async def _fake_last_fx_dates(session, pairs):
        assert isinstance(session, _FakeSession), f"_last_fx_dates takes a session the job opened, not {session!r}"
        asked = list(pairs)
        if lookups is not None:
            lookups.setdefault("pairs", []).append(asked)
        return {pair: saved_rates[pair] for pair in asked if pair in saved_rates}

    monkeypatch.setattr(jobs, "_last_price_dates", _fake_last_price_dates, raising=False)
    monkeypatch.setattr(jobs, "_last_fx_dates", _fake_last_fx_dates, raising=False)
    return executed


def _asset_row(asset_id: int, name: str, icon: str | None = None) -> tuple:
    """One row of ``select(Asset.id, Asset.display_name, Asset.icon_url)``."""
    return (asset_id, name, icon)


def _route(base: str, quote: str, provider: str = "ECB") -> FxConversionRoute:
    """A real (unsaved, never added to a session) route row."""
    return FxConversionRoute(
        base=base,
        quote=quote,
        chain_steps=json.dumps([{"from": base, "to": quote, "provider": provider}]),
    )


def _install_current_price_double(monkeypatch, *, failing: set[int] | None = None, recorder: dict | None = None):
    """Replace the bulk current-price fetch with a double built from the ids it gets."""
    failing = failing or set()

    async def _fake(asset_ids, session, concurrency=5):
        if recorder is not None:
            recorder["asset_ids"] = list(asset_ids)
            recorder["concurrency"] = concurrency
        items = []
        for asset_id in asset_ids:
            if asset_id in failing:
                items.append(FACurrentPriceItem(asset_id=asset_id, error=f"provider timeout for {asset_id}"))
            else:
                items.append(
                    FACurrentPriceItem(
                        asset_id=asset_id,
                        value=Decimal("12.34"),
                        currency="EUR",
                        as_of_date=date(2026, 1, 15),
                        source="provider:double",
                    )
                )
        return items

    monkeypatch.setattr(jobs.AssetSourceManager, "get_current_prices_bulk", staticmethod(_fake))


def _install_refresh_double(monkeypatch, *, failing: set[int] | None = None, recorder: dict | None = None, empty: bool = False):
    """Replace the bulk history refresh with a double built from the requests it gets.

    ``recorder`` gets the ids requested, in order (``"asset_ids"``), and each one's window
    ``(start, end)`` by id (``"date_ranges"``, lot Z-5).
    """
    failing = failing or set()

    async def _fake(requests, session, concurrency=5, semaphore_timeout=60):
        if recorder is not None:
            recorder["asset_ids"] = [item.asset_id for item in requests]
            recorder["date_ranges"] = {item.asset_id: (item.date_range.start, item.date_range.end) for item in requests}
        results = []
        if not empty:
            for item in requests:
                failed = item.asset_id in failing
                results.append(
                    FARefreshResult(
                        asset_id=item.asset_id,
                        status=SyncStatus.FAILED if failed else SyncStatus.OK,
                        provider_used=None if failed else "mockprov",
                        points_fetched=0 if failed else 5,
                        points_changed=0 if failed else 3,
                        events_changed=0 if failed else 1,
                        errors=[f"boom {item.asset_id}"] if failed else [],
                    )
                )
        success = sum(1 for r in results if r.status == SyncStatus.OK)
        return FABulkRefreshResponse(
            results=results,
            success_count=success,
            date_range=None,
            total_points_changed=sum(r.points_changed for r in results),
        )

    monkeypatch.setattr(jobs.AssetSourceManager, "bulk_refresh_prices", staticmethod(_fake))


def _install_fx_double(monkeypatch, *, failing: set[str] | None = None, recorder: dict | None = None, empty: bool = False):
    """Replace ``sync_pairs_bulk`` with a double built from the pairs it gets."""
    failing = failing or set()

    async def _fake(session, pairs, date_range):
        start_date, end_date = date_range
        if recorder is not None:
            recorder["pairs"] = list(pairs)
            recorder["date_range"] = (start_date, end_date)
        results = []
        if not empty:
            for pair in pairs:
                failed = pair in failing
                results.append(
                    FXSyncPairResult(
                        pair=pair,
                        status=SyncStatus.FAILED if failed else SyncStatus.OK,
                        provider_used=None if failed else "MOCKFX",
                        points_changed=0 if failed else 4,
                        errors=[f"no data for {pair}"] if failed else [],
                    )
                )
        success = sum(1 for r in results if r.status == SyncStatus.OK)
        return FXSyncBulkResponse(
            results=results,
            success_count=success,
            date_range=SyncDateRangeModel(start=start_date, end=end_date),
            total_points_changed=sum(r.points_changed for r in results),
        )

    monkeypatch.setattr(jobs, "sync_pairs_bulk", _fake)


def _sole_entry(job: str) -> dict:
    """The single log entry written by the job under test.

    The log lives in this test's own sandbox directory, so asserting on its exact
    cardinality is asserting on a collection the test created.
    """
    entries = joblog.read_entries()
    assert len(entries) == 1, f"expected exactly one log entry, got {len(entries)}"
    entry = entries[0]
    assert entry["job"] == job
    return entry


def _item_for(items: list[dict], key: str, value) -> dict:
    """Pick the item identified by ``key == value`` — never by position."""
    matches = [item for item in items if item.get(key) == value]
    assert len(matches) == 1, f"expected one item with {key}={value!r}, got {len(matches)}"
    return matches[0]


#: The summary counters of the items deferred, which lot Z7b adds to an entry.
DEFERRED_COUNTERS = frozenset({"deferred", "assets_deferred", "fx_deferred"})


def _counts(summary: dict) -> dict:
    """``summary`` without the deferred counters of lot Z7b.

    The cases written before Z7b pin what a run without RATE_LIMITED items counts, which
    must not change; such a run gains the deferred counters at 0, pinned exactly by the
    Z7b cases (``test_*_with_nothing_deferred_*``).
    """
    return {key: value for key, value in summary.items() if key not in DEFERRED_COUNTERS}


# ============================================================================
# _classify_job_status
# ============================================================================


@pytest.mark.parametrize(
    ("ok_count", "total_count", "expected"),
    [
        (0, 0, "ok"),  # nothing to do is not a failure
        (1, 1, "ok"),  # smallest all-ok run
        (5, 5, "ok"),
        (0, 1, "error"),  # smallest all-failed run
        (0, 5, "error"),
        (1, 5, "partial"),  # lower boundary of "partial"
        (4, 5, "partial"),  # upper boundary of "partial"
    ],
)
def test_classify_job_status(ok_count, total_count, expected):
    """The three outcomes plus their boundary values."""
    assert jobs._classify_job_status(ok_count, total_count) == expected


# ============================================================================
# run_current_price_refresh
# ============================================================================


@pytest.mark.asyncio
async def test_current_price_refresh_all_ok(monkeypatch, isolated_joblog_dir):
    """Nominal run: every asset priced -> status ok, state and log agree."""
    rows = [_asset_row(101, "Alpha ETF", "https://example.invalid/alpha.png"), _asset_row(102, "Beta Fund")]
    _install_fake_session(monkeypatch, asset_rows=rows)
    recorder: dict = {}
    _install_current_price_double(monkeypatch, recorder=recorder)

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    # The job passes the ids it selected, with the concurrency it declares.
    assert recorder["asset_ids"] == [101, 102]
    assert recorder["concurrency"] == 3

    assert state.current_price.last_status == "ok"
    assert state.current_price.last_items_ok == 2
    assert state.current_price.last_items_err == 0
    assert state.current_price.last_error is None
    assert state.current_price.last_run_at is not None
    assert state.current_price.last_duration_s is not None
    # The other job must not be touched by this one.
    assert state.history_sync == JobState()

    entry = _sole_entry("current_price")
    assert entry["status"] == "ok"
    assert _counts(entry["summary"]) == {"ok": 2, "err": 0}
    alpha = _item_for(entry["items"], "asset_id", 101)
    beta = _item_for(entry["items"], "asset_id", 102)
    assert alpha["name"] == "Alpha ETF"
    assert alpha["ok"] is True
    assert alpha["icon_url"] == "https://example.invalid/alpha.png"
    assert "error" not in alpha
    assert beta["ok"] is True
    assert "icon_url" not in beta  # no icon on the row -> key omitted


@pytest.mark.asyncio
async def test_current_price_refresh_partial(monkeypatch, isolated_joblog_dir):
    """One asset in error out of three -> partial, and the error reaches the log."""
    rows = [_asset_row(201, "Gamma"), _asset_row(202, "Delta"), _asset_row(203, "Epsilon")]
    _install_fake_session(monkeypatch, asset_rows=rows)
    _install_current_price_double(monkeypatch, failing={202})

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    assert state.current_price.last_status == "partial"
    assert state.current_price.last_items_ok == 2
    assert state.current_price.last_items_err == 1

    entry = _sole_entry("current_price")
    assert entry["status"] == "partial"
    assert _counts(entry["summary"]) == {"ok": 2, "err": 1}
    failed = _item_for(entry["items"], "asset_id", 202)
    assert failed["ok"] is False
    assert failed["error"] == "provider timeout for 202"


@pytest.mark.asyncio
async def test_current_price_refresh_all_failed(monkeypatch, isolated_joblog_dir):
    """Every asset in error -> status error, not partial."""
    rows = [_asset_row(301, "Zeta"), _asset_row(302, "Eta")]
    _install_fake_session(monkeypatch, asset_rows=rows)
    _install_current_price_double(monkeypatch, failing={301, 302})

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    assert state.current_price.last_status == "error"
    assert state.current_price.last_items_ok == 0
    assert state.current_price.last_items_err == 2

    entry = _sole_entry("current_price")
    assert entry["status"] == "error"
    assert _counts(entry["summary"]) == {"ok": 0, "err": 2}
    assert all(item["ok"] is False for item in entry["items"])


@pytest.mark.asyncio
async def test_current_price_refresh_no_active_assets_still_records_the_run(monkeypatch, isolated_joblog_dir):
    """Zero active assets -> the run is still recorded, with nothing in it.

    It used to return early and write neither the state nor a log entry, so the
    scheduler panel kept showing the outcome of the *previous* run: "it ran and found
    nothing to do" looked exactly like "it stopped running". run_history_sync has
    always written its entry in the same situation, and the two now agree.

    The provider call is still skipped — recording the run is not the same as doing
    pointless work.
    """
    _install_fake_session(monkeypatch, asset_rows=[])

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("get_current_prices_bulk must not run when there are no active assets")

    monkeypatch.setattr(jobs.AssetSourceManager, "get_current_prices_bulk", staticmethod(_must_not_be_called))

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    assert state.current_price.last_run_at is not None, "an empty run must still stamp the time it happened"
    assert state.current_price.last_status == "ok"
    assert state.current_price.last_items_ok == 0
    assert state.current_price.last_items_err == 0
    assert state.current_price.last_error is None
    assert state.history_sync == JobState(), "the other job must be untouched"

    entries = joblog.read_entries()
    assert len(entries) == 1, "an empty run is still a run, and the panel needs to see it"
    assert entries[0]["job"] == "current_price"
    assert entries[0]["status"] == "ok"
    assert _counts(entries[0]["summary"]) == {"ok": 0, "err": 0}
    assert entries[0]["items"] == []


# ============================================================================
# run_history_sync
# ============================================================================


@pytest.mark.asyncio
async def test_history_sync_all_ok(monkeypatch, isolated_joblog_dir):
    """Nominal run: assets and FX pairs all ok -> status ok, both halves in the log."""
    rows = [_asset_row(401, "Alpha ETF", "https://example.invalid/alpha.png"), _asset_row(402, "Beta Fund")]
    routes = [_route("EUR", "USD"), _route("CHF", "EUR")]
    _install_fake_session(monkeypatch, asset_rows=rows, routes=routes)
    asset_recorder: dict = {}
    fx_recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=asset_recorder)
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    state = SchedulerState()
    await jobs.run_history_sync(state, horizon_days=7)

    assert asset_recorder["asset_ids"] == [401, 402]
    # Pairs are de-duplicated and sorted before the FX call.
    assert fx_recorder["pairs"] == ["CHF-EUR", "EUR-USD"]
    # horizon_days is honoured: the window is exactly seven days wide, ending today.
    start, end = fx_recorder["date_range"]
    assert (end - start).days == 7
    assert end == date.today()

    assert state.history_sync.last_status == "ok"
    assert state.history_sync.last_items_ok == 4  # 2 assets + 2 pairs
    assert state.history_sync.last_items_err == 0
    assert state.current_price == JobState()  # the other job is untouched

    entry = _sole_entry("history_sync")
    assert entry["status"] == "ok"
    assert _counts(entry["summary"]) == {"assets_ok": 2, "assets_err": 0, "fx_ok": 2, "fx_err": 0}
    alpha = _item_for(entry["assets"], "asset_id", 401)
    assert alpha["name"] == "Alpha ETF"
    assert alpha["status"] == "ok"
    assert alpha["provider"] == "mockprov"
    assert alpha["prices_changed"] == 3
    assert alpha["events_changed"] == 1
    assert alpha["icon_url"] == "https://example.invalid/alpha.png"
    assert "icon_url" not in _item_for(entry["assets"], "asset_id", 402)
    eur_usd = _item_for(entry["fx"], "pair", "EUR-USD")
    assert eur_usd["base"] == "EUR"
    assert eur_usd["quote"] == "USD"
    assert eur_usd["status"] == "ok"
    assert eur_usd["provider"] == "MOCKFX"
    assert eur_usd["points_changed"] == 4


@pytest.mark.asyncio
async def test_history_sync_partial_on_both_halves(monkeypatch, isolated_joblog_dir):
    """A failed asset and a failed pair -> partial, with per-item errors in the log."""
    rows = [_asset_row(501, "Gamma"), _asset_row(502, "Delta")]
    routes = [_route("EUR", "USD"), _route("GBP", "USD")]
    _install_fake_session(monkeypatch, asset_rows=rows, routes=routes)
    _install_refresh_double(monkeypatch, failing={502})
    _install_fx_double(monkeypatch, failing={"GBP-USD"})

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert state.history_sync.last_status == "partial"
    assert state.history_sync.last_items_ok == 2  # one asset + one pair
    assert state.history_sync.last_items_err == 2

    entry = _sole_entry("history_sync")
    assert entry["status"] == "partial"
    assert _counts(entry["summary"]) == {"assets_ok": 1, "assets_err": 1, "fx_ok": 1, "fx_err": 1}
    failed_asset = _item_for(entry["assets"], "asset_id", 502)
    assert failed_asset["status"] == "failed"
    assert failed_asset["errors"] == ["boom 502"]
    assert "provider" not in failed_asset  # provider_used is None -> key omitted
    failed_pair = _item_for(entry["fx"], "pair", "GBP-USD")
    assert failed_pair["status"] == "failed"
    assert failed_pair["errors"] == ["no data for GBP-USD"]
    assert "provider" not in failed_pair


@pytest.mark.asyncio
async def test_history_sync_fx_failure_alone_degrades_status(monkeypatch, isolated_joblog_dir):
    """FX is not cosmetic: assets all ok but every pair failing still yields partial."""
    rows = [_asset_row(601, "Theta")]
    routes = [_route("EUR", "USD"), _route("CHF", "EUR")]
    _install_fake_session(monkeypatch, asset_rows=rows, routes=routes)
    _install_refresh_double(monkeypatch)
    _install_fx_double(monkeypatch, failing={"EUR-USD", "CHF-EUR"})

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert state.history_sync.last_status == "partial"
    assert state.history_sync.last_items_ok == 1  # the single asset
    assert state.history_sync.last_items_err == 2  # both pairs

    entry = _sole_entry("history_sync")
    assert _counts(entry["summary"]) == {"assets_ok": 1, "assets_err": 0, "fx_ok": 0, "fx_err": 2}


@pytest.mark.asyncio
async def test_history_sync_skips_manual_routes(monkeypatch, isolated_joblog_dir):
    """MANUAL routes are user-managed and must never be handed to the FX sync."""
    routes = [
        _route("EUR", "USD"),
        _route("NOK", "SEK", provider="MANUAL"),
        _route("DKK", "EUR", provider="manual"),  # case-insensitive by design
    ]
    _install_fake_session(monkeypatch, asset_rows=[], routes=routes)
    fx_recorder: dict = {}
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert fx_recorder["pairs"] == ["EUR-USD"]
    assert {item["pair"] for item in _sole_entry("history_sync")["fx"]} == {"EUR-USD"}


@pytest.mark.asyncio
async def test_history_sync_keeps_routes_with_unreadable_chain_steps(monkeypatch, isolated_joblog_dir):
    """A corrupt chain_steps column must not silently drop the pair from the sync.

    Both failure shapes the product guards against are reachable in practice: a NULL
    column (TypeError) and a truncated write (JSONDecodeError). Either way the route
    cannot be proven MANUAL, and the job syncs it rather than skipping it.
    """
    broken_json = FxConversionRoute(base="AUD", quote="USD", chain_steps="[{not json")
    null_steps = FxConversionRoute(base="CAD", quote="USD", chain_steps=None)
    _install_fake_session(monkeypatch, asset_rows=[], routes=[broken_json, null_steps])
    fx_recorder: dict = {}
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert fx_recorder["pairs"] == ["AUD-USD", "CAD-USD"]


@pytest.mark.asyncio
async def test_history_sync_with_nothing_to_do_still_reports(monkeypatch, isolated_joblog_dir):
    """No assets and no routes -> status ok, and unlike current-price it still reports.

    The contrast with ``run_current_price_refresh`` is deliberate and is the reason the
    early-return question above is worth asking: same "nothing to do" situation, two
    different observability outcomes.
    """
    _install_fake_session(monkeypatch, asset_rows=[], routes=[])

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("no assets and no routes: neither bulk call should run")

    monkeypatch.setattr(jobs.AssetSourceManager, "bulk_refresh_prices", staticmethod(_must_not_be_called))
    monkeypatch.setattr(jobs, "sync_pairs_bulk", _must_not_be_called)

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert state.history_sync.last_status == "ok"
    assert state.history_sync.last_items_ok == 0
    assert state.history_sync.last_items_err == 0
    assert state.history_sync.last_run_at is not None

    entry = _sole_entry("history_sync")
    assert entry["assets"] == []
    assert entry["fx"] == []
    assert _counts(entry["summary"]) == {"assets_ok": 0, "assets_err": 0, "fx_ok": 0, "fx_err": 0}


@pytest.mark.asyncio
async def test_history_sync_with_no_assets_still_syncs_fx(monkeypatch, isolated_joblog_dir):
    """No active assets must not cancel the FX half of the job."""
    _install_fake_session(monkeypatch, asset_rows=[], routes=[_route("EUR", "USD")])

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("bulk_refresh_prices must not run without assets")

    monkeypatch.setattr(jobs.AssetSourceManager, "bulk_refresh_prices", staticmethod(_must_not_be_called))
    _install_fx_double(monkeypatch)

    state = SchedulerState()
    await jobs.run_history_sync(state)

    assert state.history_sync.last_status == "ok"
    assert state.history_sync.last_items_ok == 1
    entry = _sole_entry("history_sync")
    assert entry["assets"] == []
    assert _item_for(entry["fx"], "pair", "EUR-USD")["status"] == "ok"


# ============================================================================
# RATE_LIMITED items: deferred, not failed (lot Z7b)
# ============================================================================

RATE_LIMITED = "RATE_LIMITED"
#: A current price that failed for a reason other than a pause: no value.
PRICE_FAILED = {"value": None, "currency": None, "as_of_date": None, "source": None, "error": "provider timeout"}
#: An asset history, and an FX pair, that failed for a reason other than a pause.
ASSET_FAILED = {"status": SyncStatus.FAILED, "provider_used": None, "points_fetched": 0, "points_changed": 0, "events_changed": 0, "errors": ["boom"]}
PAIR_FAILED = {"status": SyncStatus.FAILED, "provider_used": None, "points_changed": 0, "errors": ["no data"]}
#: The keys of an entry, exactly: those of before lot Z7b, and ``retry_at``.
CURRENT_PRICE_ENTRY_KEYS = {"ts", "job", "duration_s", "status", "summary", "items", "retry_at"}
HISTORY_ENTRY_KEYS = {"ts", "job", "duration_s", "status", "summary", "assets", "fx", "retry_at"}


def _price_refused(retry_after: float | None, *, last_value: bool = False) -> dict:
    """A current price the provider refused for too many requests: with its last stored value when ``last_value``, with none otherwise."""
    fields: dict = {"error": "too many requests", "error_code": RATE_LIMITED, "retry_after": retry_after}
    if last_value:
        fields["source"] = "db:last_known"
    else:
        fields.update(value=None, currency=None, as_of_date=None, source=None)
    return fields


def _asset_refused(retry_after: float | None, status: SyncStatus = SyncStatus.FAILED) -> dict:
    """An asset history the provider refused for too many requests: FAILED, or OK/PARTIAL with part of the data saved."""
    fields: dict = {"status": status, "errors": ["too many requests"], "error_code": RATE_LIMITED, "retry_after": retry_after}
    if status == SyncStatus.FAILED:
        fields.update(provider_used=None, points_fetched=0, points_changed=0, events_changed=0)
    return fields


def _pair_refused(retry_after: float | None) -> dict:
    """An FX pair that failed because its providers refused for too many requests."""
    return {"status": SyncStatus.FAILED, "provider_used": None, "points_changed": 0, "errors": ["too many requests"], "error_code": RATE_LIMITED, "retry_after": retry_after}


def _install_current_price_answers(monkeypatch, answers: dict[int, dict]) -> None:
    """Replace the bulk current-price fetch: every asset priced, unless ``answers`` gives it other fields."""

    async def _fake(asset_ids, session, concurrency=5):
        priced = {"value": Decimal("12.34"), "currency": "EUR", "as_of_date": date(2026, 1, 15), "source": "provider:double"}
        return [FACurrentPriceItem(asset_id=asset_id, **{**priced, **answers.get(asset_id, {})}) for asset_id in asset_ids]

    monkeypatch.setattr(jobs.AssetSourceManager, "get_current_prices_bulk", staticmethod(_fake))


def _install_refresh_answers(monkeypatch, answers: dict[int, dict]) -> None:
    """Replace the bulk history refresh: every asset synced, unless ``answers`` gives it other fields."""

    async def _fake(requests, session, concurrency=5, semaphore_timeout=60):
        synced = {"status": SyncStatus.OK, "provider_used": "mockprov", "points_fetched": 5, "points_changed": 3, "events_changed": 1}
        results = [FARefreshResult(asset_id=item.asset_id, **{**synced, **answers.get(item.asset_id, {})}) for item in requests]
        return FABulkRefreshResponse(results=results, success_count=sum(1 for r in results if r.status == SyncStatus.OK), date_range=None, total_points_changed=sum(r.points_changed for r in results))

    monkeypatch.setattr(jobs.AssetSourceManager, "bulk_refresh_prices", staticmethod(_fake))


def _install_fx_answers(monkeypatch, answers: dict[str, dict]) -> None:
    """Replace ``sync_pairs_bulk``: every pair synced, unless ``answers`` gives it other fields."""

    async def _fake(session, pairs, date_range):
        start_date, end_date = date_range
        synced = {"status": SyncStatus.OK, "provider_used": "MOCKFX", "points_changed": 4}
        results = [FXSyncPairResult(pair=pair, **{**synced, **answers.get(pair, {})}) for pair in pairs]
        return FXSyncBulkResponse(results=results, success_count=sum(1 for r in results if r.status == SyncStatus.OK), date_range=SyncDateRangeModel(start=start_date, end=end_date), total_points_changed=sum(r.points_changed for r in results))

    monkeypatch.setattr(jobs, "sync_pairs_bulk", _fake)


def _assert_retry_at(value, before: datetime, after: datetime, pause: float, what: str) -> None:
    """``value`` is an aware ISO-8601 instant within [before, after] + ``pause``: bounded by readings of the clock taken around the job, never an exact duration."""
    assert isinstance(value, str), f"{what}: an ISO-8601 timestamp expected, got {value!r}"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        pytest.fail(f"{what}: {value!r} is not ISO-8601")
    assert moment.utcoffset() is not None, f"{what}: {value!r} is not aware"
    low, high = before + timedelta(seconds=pause), after + timedelta(seconds=pause)
    assert low <= moment <= high, f"{what}: {moment.isoformat()} is not within [{low.isoformat()}, {high.isoformat()}]"


def _deferred(items: list[dict], key: str) -> dict:
    """``{<key>: retry_after}`` of the items an entry marks ``"deferred": true``, ``retry_after`` None where it is not given."""
    return {item[key]: item.get("retry_after") for item in items if item.get("deferred") is True}


def _unmarked(items: list[dict]) -> bool:
    """No item carries ``deferred`` or ``retry_after``: the shape items had before lot Z7b."""
    return all(not {"deferred", "retry_after"} & set(item) for item in items)


@pytest.mark.parametrize(
    ("ok_count", "total_count", "expected"),
    [(0, 0, "ok"), (1, 1, "ok"), (5, 5, "ok"), (0, 1, "error"), (0, 5, "error"), (1, 5, "partial"), (4, 5, "partial")],
)
def test_classify_job_status_with_nothing_deferred_is_unchanged(ok_count, total_count, expected):
    """Z7b: ``deferred_count=0``, given explicitly, classifies as before."""
    assert jobs._classify_job_status(ok_count, total_count, deferred_count=0) == expected


@pytest.mark.parametrize(
    ("ok_count", "total_count", "deferred_count"),
    [
        (0, 1, 1),  # the smallest run with every item deferred
        (0, 4, 4),  # every item deferred
        (3, 4, 1),  # every other item ok: one deferred is enough to leave "ok"
        (0, 4, 1),  # nothing ok, three failed, one deferred: not "error"
        (1, 4, 1),  # ok, failed and deferred together
    ],
)
def test_classify_job_status_with_an_item_deferred_is_partial(ok_count, total_count, deferred_count):
    """Z7b: "ok" only when every item succeeded, "error" only when nothing succeeded and nothing was deferred: with an item deferred it is "partial", every item deferred included."""
    assert jobs._classify_job_status(ok_count, total_count, deferred_count=deferred_count) == "partial"


@pytest.mark.asyncio
async def test_current_price_refresh_defers_rate_limited_items_and_retries_at_the_shortest_pause(monkeypatch, isolated_joblog_dir):
    """Z7b: an item RATE_LIMITED is deferred whatever its value — one that kept its last stored price is not ok —, neither ok nor failed. ``retry_at`` is now + the shortest ``retry_after`` of the deferred items (30 s): one without it does not count, nor does the pause of an item that is not RATE_LIMITED. The log marks each deferred item, with its ``retry_after`` when known, counts them apart, and gives ``retry_at``."""
    rows = [_asset_row(701, "Priced"), _asset_row(702, "Paused, Last Price Kept"), _asset_row(703, "Paused 30 s"), _asset_row(704, "Paused, No Retry-After"), _asset_row(705, "Timed Out"), _asset_row(706, "Unknown Symbol")]
    _install_fake_session(monkeypatch, asset_rows=rows)
    _install_current_price_answers(
        monkeypatch,
        {
            702: _price_refused(120.0, last_value=True),
            703: _price_refused(30.0),
            704: _price_refused(None),
            705: PRICE_FAILED,
            706: {**PRICE_FAILED, "error": "unknown symbol", "error_code": "NOT_FOUND", "retry_after": 5.0},
        },
    )

    state = SchedulerState()
    before = datetime.now(UTC)
    await jobs.run_current_price_refresh(state)
    after = datetime.now(UTC)

    job = state.current_price
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred) == ("partial", 1, 2, 3)
    assert (job.consecutive_failures, job.next_attempt_at, job.last_error) == (0, None, None)
    _assert_retry_at(job.retry_at, before, after, 30.0, "state.current_price.retry_at")
    assert state.history_sync == JobState()

    entry = _sole_entry("current_price")
    assert entry["status"] == "partial"
    assert entry["summary"] == {"ok": 1, "err": 2, "deferred": 3}
    _assert_retry_at(entry["retry_at"], before, after, 30.0, "the entry's retry_at")
    assert _deferred(entry["items"], "asset_id") == {702: 120.0, 703: 30.0, 704: None}
    assert {asset_id: _item_for(entry["items"], "asset_id", asset_id)["ok"] for asset_id in (701, 702, 705, 706)} == {701: True, 702: False, 705: False, 706: False}


@pytest.mark.asyncio
async def test_current_price_refresh_with_every_item_deferred_is_partial_not_error(monkeypatch, isolated_joblog_dir):
    """Z7b: every price paused, one with its last stored value: "partial", nothing ok, nothing failed, both deferred; ``retry_at`` now + 60 s, the shorter pause."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(711, "Paused 5 min"), _asset_row(712, "Paused 1 min, Last Price Kept")])
    _install_current_price_answers(monkeypatch, {711: _price_refused(300.0), 712: _price_refused(60.0, last_value=True)})

    state = SchedulerState()
    before = datetime.now(UTC)
    await jobs.run_current_price_refresh(state)
    after = datetime.now(UTC)

    job = state.current_price
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred) == ("partial", 0, 0, 2)
    _assert_retry_at(job.retry_at, before, after, 60.0, "state.current_price.retry_at")
    entry = _sole_entry("current_price")
    assert (entry["status"], entry["summary"]) == ("partial", {"ok": 0, "err": 0, "deferred": 2})
    _assert_retry_at(entry["retry_at"], before, after, 60.0, "the entry's retry_at")


@pytest.mark.asyncio
async def test_current_price_refresh_with_no_pause_known_leaves_no_retry_at(monkeypatch, isolated_joblog_dir):
    """Z7b: the one deferred item gives no ``retry_after``: it is still deferred, and ``retry_at`` is None, in the state and, as null, in the entry."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(721, "Priced"), _asset_row(722, "Paused, No Retry-After")])
    _install_current_price_answers(monkeypatch, {722: _price_refused(None)})

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    job = state.current_price
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred, job.retry_at) == ("partial", 1, 0, 1, None)
    entry = _sole_entry("current_price")
    assert entry["summary"] == {"ok": 1, "err": 0, "deferred": 1}
    assert entry.get("retry_at", "<missing>") is None
    assert _deferred(entry["items"], "asset_id") == {722: None}


@pytest.mark.asyncio
async def test_current_price_refresh_with_nothing_deferred_keeps_its_entry_shape_with_zero_deferred(monkeypatch, isolated_joblog_dir):
    """Z7b: one price ok, one failed, none paused: the state has nothing deferred, no ``retry_at``, no failure held; the entry keeps the shape it had, plus ``summary.deferred`` 0 and ``retry_at`` null, its items unmarked."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(731, "Priced"), _asset_row(732, "Timed Out")])
    _install_current_price_answers(monkeypatch, {732: PRICE_FAILED})

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    job = state.current_price
    assert (job.last_status, job.last_items_deferred, job.retry_at, job.consecutive_failures, job.next_attempt_at) == ("partial", 0, None, 0, None)
    entry = _sole_entry("current_price")
    assert set(entry) == CURRENT_PRICE_ENTRY_KEYS
    assert entry["summary"] == {"ok": 1, "err": 1, "deferred": 0}
    assert entry["retry_at"] is None
    assert _unmarked(entry["items"]), entry["items"]


@pytest.mark.asyncio
async def test_current_price_refresh_that_ends_resets_the_failure_backoff(monkeypatch, isolated_joblog_dir):
    """Z7b: the job had failed three times, held until 10:08, with items deferred before: a run that ends writes a fresh ``JobState`` — no failure, no next attempt, nothing deferred, no ``retry_at``, "ok", no error."""
    previous = JobState(
        last_run_at="2026-06-08T09:00:00+00:00",
        last_status="error",
        last_error="ProviderExploded",
        last_items_deferred=2,
        retry_at="2026-06-08T09:05:00+00:00",
        consecutive_failures=3,
        next_attempt_at="2026-06-08T10:08:00+00:00",
    )
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(741, "Priced")])
    _install_current_price_answers(monkeypatch, {})

    state = SchedulerState(current_price=previous)
    await jobs.run_current_price_refresh(state)

    job = state.current_price
    assert (job.consecutive_failures, job.next_attempt_at, job.last_items_deferred, job.retry_at, job.last_status, job.last_error) == (0, None, 0, None, "ok", None)


@pytest.mark.asyncio
async def test_history_sync_defers_rate_limited_items_whatever_their_status(monkeypatch, isolated_joblog_dir):
    """Z7b: assets and pairs RATE_LIMITED are deferred whatever their status — FAILED, PARTIAL or OK with part of the data saved —; ok is OK and not deferred, failed the rest (a PARTIAL included). Totals over both halves; ``retry_at`` now + the shortest ``retry_after`` of both (45 s, a pair's). The log marks each deferred item, counts them apart per half, and gives ``retry_at``."""
    rows = [_asset_row(801, "Synced"), _asset_row(802, "Refused 5 min"), _asset_row(803, "Partly Saved, Refused 90 s"), _asset_row(804, "Failed"), _asset_row(805, "Saved, Refused, No Retry-After"), _asset_row(806, "Partial")]
    routes = [_route("EUR", "USD"), _route("GBP", "USD"), _route("CHF", "EUR")]
    _install_fake_session(monkeypatch, asset_rows=rows, routes=routes)
    _install_refresh_answers(monkeypatch, {802: _asset_refused(300.0), 803: _asset_refused(90.0, SyncStatus.PARTIAL), 804: ASSET_FAILED, 805: _asset_refused(None, SyncStatus.OK), 806: {"status": SyncStatus.PARTIAL}})
    _install_fx_answers(monkeypatch, {"GBP-USD": _pair_refused(45.0), "CHF-EUR": PAIR_FAILED})

    state = SchedulerState()
    before = datetime.now(UTC)
    await jobs.run_history_sync(state)
    after = datetime.now(UTC)

    job = state.history_sync
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred) == ("partial", 2, 3, 4)
    assert (job.consecutive_failures, job.next_attempt_at, job.last_error) == (0, None, None)
    _assert_retry_at(job.retry_at, before, after, 45.0, "state.history_sync.retry_at")
    assert state.current_price == JobState()

    entry = _sole_entry("history_sync")
    assert entry["status"] == "partial"
    assert entry["summary"] == {"assets_ok": 1, "assets_err": 2, "assets_deferred": 3, "fx_ok": 1, "fx_err": 1, "fx_deferred": 1}
    _assert_retry_at(entry["retry_at"], before, after, 45.0, "the entry's retry_at")
    assert _deferred(entry["assets"], "asset_id") == {802: 300.0, 803: 90.0, 805: None}
    assert _deferred(entry["fx"], "pair") == {"GBP-USD": 45.0}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset_pause", "pair_pause", "shortest"),
    [pytest.param(300.0, 45.0, 45.0, id="the-pair-pause-shorter"), pytest.param(20.0, 600.0, 20.0, id="the-asset-pause-shorter")],
)
async def test_history_sync_retries_at_the_shortest_pause_of_both_halves(monkeypatch, isolated_joblog_dir, asset_pause, pair_pause, shortest):
    """Z7b: one asset and one pair paused: ``retry_at`` is now + the shorter pause, whichever half it comes from, in the state and in the entry."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(811, "Synced"), _asset_row(812, "Refused")], routes=[_route("EUR", "USD"), _route("GBP", "USD")])
    _install_refresh_answers(monkeypatch, {812: _asset_refused(asset_pause)})
    _install_fx_answers(monkeypatch, {"GBP-USD": _pair_refused(pair_pause)})

    state = SchedulerState()
    before = datetime.now(UTC)
    await jobs.run_history_sync(state)
    after = datetime.now(UTC)

    job = state.history_sync
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred) == ("partial", 2, 0, 2)
    _assert_retry_at(job.retry_at, before, after, shortest, "state.history_sync.retry_at")
    _assert_retry_at(_sole_entry("history_sync")["retry_at"], before, after, shortest, "the entry's retry_at")


@pytest.mark.asyncio
async def test_history_sync_with_every_item_deferred_is_partial_not_error(monkeypatch, isolated_joblog_dir):
    """Z7b: the one asset and the one pair paused: "partial", nothing ok, nothing failed, two deferred; ``retry_at`` now + 120 s, the pair's pause being unknown."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(821, "Refused")], routes=[_route("EUR", "USD")])
    _install_refresh_answers(monkeypatch, {821: _asset_refused(120.0)})
    _install_fx_answers(monkeypatch, {"EUR-USD": _pair_refused(None)})

    state = SchedulerState()
    before = datetime.now(UTC)
    await jobs.run_history_sync(state)
    after = datetime.now(UTC)

    job = state.history_sync
    assert (job.last_status, job.last_items_ok, job.last_items_err, job.last_items_deferred) == ("partial", 0, 0, 2)
    _assert_retry_at(job.retry_at, before, after, 120.0, "state.history_sync.retry_at")
    entry = _sole_entry("history_sync")
    assert (entry["status"], entry["summary"]) == ("partial", {"assets_ok": 0, "assets_err": 0, "assets_deferred": 1, "fx_ok": 0, "fx_err": 0, "fx_deferred": 1})


@pytest.mark.asyncio
async def test_history_sync_with_nothing_deferred_keeps_its_entry_shape_with_zero_deferred(monkeypatch, isolated_joblog_dir):
    """Z7b: an asset and a pair ok, an asset and a pair failed, none paused: nothing deferred, no ``retry_at``, no failure held; the entry keeps the shape it had, plus ``assets_deferred`` and ``fx_deferred`` 0 and ``retry_at`` null, its items unmarked."""
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(831, "Synced"), _asset_row(832, "Failed")], routes=[_route("EUR", "USD"), _route("GBP", "USD")])
    _install_refresh_answers(monkeypatch, {832: ASSET_FAILED})
    _install_fx_answers(monkeypatch, {"GBP-USD": PAIR_FAILED})

    state = SchedulerState()
    await jobs.run_history_sync(state)

    job = state.history_sync
    assert (job.last_status, job.last_items_deferred, job.retry_at, job.consecutive_failures, job.next_attempt_at) == ("partial", 0, None, 0, None)
    entry = _sole_entry("history_sync")
    assert set(entry) == HISTORY_ENTRY_KEYS
    assert entry["summary"] == {"assets_ok": 1, "assets_err": 1, "assets_deferred": 0, "fx_ok": 1, "fx_err": 1, "fx_deferred": 0}
    assert entry["retry_at"] is None
    assert _unmarked(entry["assets"]) and _unmarked(entry["fx"]), entry


@pytest.mark.asyncio
async def test_history_sync_that_ends_resets_the_failure_backoff(monkeypatch, isolated_joblog_dir):
    """Z7b: the sync had failed five times, held until 11:00, with an item deferred before: a run that ends writes a fresh ``JobState`` — no failure, no next attempt, nothing deferred, no ``retry_at``, "ok", no error."""
    previous = JobState(
        last_run_at="2026-06-08T06:00:30+00:00",
        last_status="error",
        last_error="ProviderExploded",
        last_items_deferred=1,
        retry_at="2026-06-08T06:05:00+00:00",
        consecutive_failures=5,
        next_attempt_at="2026-06-08T11:00:00+00:00",
    )
    _install_fake_session(monkeypatch, asset_rows=[_asset_row(841, "Synced")], routes=[])
    _install_refresh_answers(monkeypatch, {})

    state = SchedulerState(history_sync=previous)
    await jobs.run_history_sync(state)

    job = state.history_sync
    assert (job.consecutive_failures, job.next_attempt_at, job.last_items_deferred, job.retry_at, job.last_status, job.last_error) == (0, None, 0, None, "ok", None)


# ============================================================================
# Lot Z-5: the history sync reaches back to the last saved date
# ============================================================================

#: The day the cases of ``_history_sync_start`` count from: a fixed one, so they never read the clock.
FIXED_TODAY = date(2026, 10, 16)
#: The event of a run whose window reaches back past the horizon, and the event every run ends with.
REACHES_BACK = "Scheduler: history sync reaches back"
HISTORY_SYNC_EVENT = "Scheduler: history sync"
JOBS_CANARY = "scheduler jobs test: canary through the jobs' logger"


def _day(offset: int) -> date:
    """``FIXED_TODAY`` moved by ``offset`` days: negative in the past, positive in the future."""
    return FIXED_TODAY + timedelta(days=offset)


def _assert_asked(lookups: dict, *, asset_ids: Iterable[int] = (), pairs: Iterable[str] = ()) -> None:
    """Barrier: the job asked for the last saved date of every asset and pair given.

    A window at the horizon then is the saved dates' answer, not a job that never looked.
    """
    asked_ids = {asset_id for call in lookups.get("asset_ids", []) for asset_id in call}
    asked_pairs = {pair for call in lookups.get("pairs", []) for pair in call}
    assert set(asset_ids) <= asked_ids, f"the job never asked for the last saved price of {sorted(set(asset_ids) - asked_ids)}"
    assert set(pairs) <= asked_pairs, f"the job never asked for the last saved rate of {sorted(set(pairs) - asked_pairs)}"


@contextmanager
def _captured_job_log() -> Iterator[list[dict]]:
    """What the jobs log inside the block, behind a barrier: a canary logged through ``jobs.logger``, at the level of the
    event under test, must arrive first — else an event missing from the capture would prove nothing."""
    with capture_logs() as events:
        jobs.logger.info(JOBS_CANARY)
        assert JOBS_CANARY in {event.get("event") for event in events}, f"barrier: jobs.logger does not reach capture_logs: {events}"
        yield events


def _logged(events: list[dict], name: str) -> list[dict]:
    """Every captured event named ``name``, in order."""
    return [event for event in events if event.get("event") == name]


def _timeless(record: dict, *keys: str) -> dict:
    """``record`` without ``keys``: the time a run carries, which two runs never share."""
    return {key: value for key, value in record.items() if key not in keys}


def _timeless_state(job: JobState) -> JobState:
    """``job`` without the time of its run."""
    return dataclasses.replace(job, last_run_at=None, last_duration_s=None)


@pytest.mark.parametrize(
    ("horizon_days", "last_saved", "expected"),
    [
        pytest.param(14, None, _day(-14), id="never-saved"),
        pytest.param(14, _day(-1), _day(-14), id="saved-yesterday"),
        pytest.param(14, FIXED_TODAY, _day(-14), id="saved-today"),
        pytest.param(14, _day(-14), _day(-14), id="resuming-the-day-after-the-horizon-start"),
        pytest.param(14, _day(-15), _day(-14), id="resuming-on-the-horizon-start"),
        pytest.param(14, _day(-16), _day(-15), id="resuming-the-day-before-the-horizon-start"),
        pytest.param(14, _day(-45), _day(-44), id="a-month-behind"),
        pytest.param(14, _day(-365), _day(-364), id="resuming-the-day-after-the-floor"),
        pytest.param(14, _day(-366), _day(-365), id="resuming-on-the-floor"),
        pytest.param(14, _day(-367), _day(-365), id="resuming-the-day-before-the-floor"),
        pytest.param(14, _day(-800), _day(-365), id="older-than-the-cap"),
        pytest.param(14, _day(4), _day(-14), id="saved-in-the-future"),
        pytest.param(60, _day(-30), _day(-60), id="inside-a-60-day-horizon"),
        pytest.param(60, _day(-62), _day(-61), id="behind-a-60-day-horizon"),
        pytest.param(365, None, _day(-365), id="never-saved-with-a-365-day-horizon"),
        pytest.param(365, _day(-900), _day(-365), id="far-behind-a-365-day-horizon"),
    ],
)
def test_history_sync_start_on_a_fixed_day(horizon_days, last_saved, expected):
    """Z-5: where a window starts, ``today`` fixed. At the horizon's start (``today - horizon_days``) when nothing is saved
    or when the day after the last saved date is not before it — a date in the future included —; else the day after the
    last saved date, but never earlier than 365 days ago. Each boundary from both sides."""
    assert jobs._history_sync_start(FIXED_TODAY, horizon_days, last_saved) == expected


def test_history_catch_up_reaches_back_365_days_at_most():
    """Z-5: how far back the sync reaches at most, whatever the last saved date: a year."""
    assert jobs.HISTORY_CATCH_UP_MAX_DAYS == 365


@pytest.mark.asyncio
async def test_history_sync_starts_each_asset_the_day_after_its_last_saved_price(monkeypatch, isolated_joblog_dir):
    """Z-5: each asset has its own window. 401, last saved 30 days ago, starts 29 days ago; 402, saved yesterday, and 403,
    never saved, start at the 14-day horizon. Every window ends today."""
    today = date.today()
    rows = [_asset_row(401, "A Month Behind"), _asset_row(402, "Saved Yesterday"), _asset_row(403, "Never Saved")]
    _install_fake_session(monkeypatch, asset_rows=rows, last_price_dates={401: today - timedelta(days=30), 402: today - timedelta(days=1)})
    recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=recorder)

    await jobs.run_history_sync(SchedulerState(), horizon_days=14)

    horizon_start = today - timedelta(days=14)
    assert recorder["date_ranges"] == {
        401: (today - timedelta(days=29), today),
        402: (horizon_start, today),
        403: (horizon_start, today),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("days_since_saved", "furthest_behind"),
    [
        pytest.param({"EUR-USD": 40, "CHF-EUR": 1}, "EUR-USD", id="eur-usd-40-days-behind"),
        pytest.param({"EUR-USD": 20, "CHF-EUR": 40}, "CHF-EUR", id="both-behind-chf-eur-further"),
        pytest.param({"EUR-USD": 1, "CHF-EUR": 0}, None, id="every-pair-up-to-date"),
        pytest.param({}, None, id="no-rate-ever-saved"),
    ],
)
async def test_history_sync_fx_window_starts_at_the_pair_furthest_behind(monkeypatch, isolated_joblog_dir, days_since_saved, furthest_behind):
    """Z-5: one FX call, so one window for every pair. It starts the day after the last saved rate of the pair furthest
    behind — EUR-USD saved 40 days ago: 39 days ago —, at the 14-day horizon when no pair is behind, and ends today. The
    horizon there is the saved dates' answer: the job asked for them."""
    today = date.today()
    saved = {pair: today - timedelta(days=days) for pair, days in days_since_saved.items()}
    lookups: dict = {}
    _install_fake_session(monkeypatch, routes=[_route("EUR", "USD"), _route("CHF", "EUR")], last_fx_dates=saved, lookups=lookups)
    fx_recorder: dict = {}
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    await jobs.run_history_sync(SchedulerState(), horizon_days=14)

    _assert_asked(lookups, pairs={"CHF-EUR", "EUR-USD"})
    start = saved[furthest_behind] + timedelta(days=1) if furthest_behind else today - timedelta(days=14)
    assert fx_recorder["date_range"] == (start, today)


@pytest.mark.asyncio
async def test_history_sync_reaches_back_no_further_than_365_days(monkeypatch, isolated_joblog_dir):
    """Z-5: an asset and a pair last saved 800 days ago both start 365 days ago, not 799: the catch-up has a cap."""
    today = date.today()
    long_ago = today - timedelta(days=800)
    _install_fake_session(
        monkeypatch,
        asset_rows=[_asset_row(461, "Dormant Fund")],
        routes=[_route("EUR", "USD")],
        last_price_dates={461: long_ago},
        last_fx_dates={"EUR-USD": long_ago},
    )
    asset_recorder: dict = {}
    fx_recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=asset_recorder)
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    await jobs.run_history_sync(SchedulerState(), horizon_days=14)

    a_year_ago = today - timedelta(days=365)
    assert asset_recorder["date_ranges"] == {461: (a_year_ago, today)}
    assert fx_recorder["date_range"] == (a_year_ago, today)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("price_days", "fx_days", "behind", "earliest_days"),
    [
        pytest.param({921: 40, 922: 1}, {"EUR-USD": 25, "CHF-EUR": 1}, (1, 1), 39, id="an-asset-furthest-behind"),
        pytest.param({921: 25, 922: 1}, {"EUR-USD": 50, "CHF-EUR": 1}, (1, 1), 49, id="a-pair-furthest-behind"),
        pytest.param({921: 40, 922: 20}, {"EUR-USD": 30, "CHF-EUR": 60}, (2, 2), 59, id="two-of-each-behind"),
    ],
)
async def test_history_sync_logs_how_far_it_reaches_back(monkeypatch, isolated_joblog_dir, price_days, fx_days, behind, earliest_days):
    """Z-5: a run whose window reaches back past the 14-day horizon logs one INFO event: how many assets and how many pairs
    are behind — an item saved yesterday, or never, is not —, and the earliest start of all, an asset's or the FX call's."""
    today = date.today()
    _install_fake_session(
        monkeypatch,
        asset_rows=[_asset_row(921, "First"), _asset_row(922, "Second"), _asset_row(923, "Never Saved")],
        routes=[_route("EUR", "USD"), _route("CHF", "EUR"), _route("GBP", "USD")],
        last_price_dates={asset_id: today - timedelta(days=days) for asset_id, days in price_days.items()},
        last_fx_dates={pair: today - timedelta(days=days) for pair, days in fx_days.items()},
    )
    _install_refresh_double(monkeypatch)
    _install_fx_double(monkeypatch)

    with _captured_job_log() as events:
        await jobs.run_history_sync(SchedulerState(), horizon_days=14)

    reached = _logged(events, REACHES_BACK)
    assert len(reached) == 1, f"one {REACHES_BACK!r} event for a run that reaches back, got {reached}"
    (event,) = reached
    assert event["log_level"] == "info"
    expected = {"assets_behind": behind[0], "fx_pairs_behind": behind[1], "earliest_start": (today - timedelta(days=earliest_days)).isoformat()}
    assert {key: event.get(key) for key in expected} == expected


@pytest.mark.asyncio
async def test_history_sync_with_nothing_behind_logs_no_reaching_back(monkeypatch, isolated_joblog_dir):
    """Z-5: assets saved yesterday, today, in the future, never, or 15 days ago — resuming on the horizon's start, which is
    not before it —, pairs saved yesterday, never, or 15 days ago: every window is the 14-day horizon's, and no
    "reaches back" event. The silence means something because the job did ask for the saved dates and did log its run."""
    today = date.today()
    lookups: dict = {}
    _install_fake_session(
        monkeypatch,
        asset_rows=[_asset_row(931, "Yesterday"), _asset_row(932, "Today"), _asset_row(933, "Ahead"), _asset_row(934, "Never"), _asset_row(935, "15 Days")],
        routes=[_route("EUR", "USD"), _route("CHF", "EUR"), _route("GBP", "USD")],
        last_price_dates={931: today - timedelta(days=1), 932: today, 933: today + timedelta(days=4), 935: today - timedelta(days=15)},
        last_fx_dates={"EUR-USD": today - timedelta(days=1), "GBP-USD": today - timedelta(days=15)},
        lookups=lookups,
    )
    asset_recorder: dict = {}
    fx_recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=asset_recorder)
    _install_fx_double(monkeypatch, recorder=fx_recorder)

    with _captured_job_log() as events:
        await jobs.run_history_sync(SchedulerState(), horizon_days=14)

    _assert_asked(lookups, asset_ids={931, 932, 933, 934, 935}, pairs={"CHF-EUR", "EUR-USD", "GBP-USD"})
    assert len(_logged(events, HISTORY_SYNC_EVENT)) == 1, f"the run's own event is missing from the capture: {events}"
    horizon = (today - timedelta(days=14), today)
    assert asset_recorder["date_ranges"] == dict.fromkeys((931, 932, 933, 934, 935), horizon)
    assert fx_recorder["date_range"] == horizon
    assert _logged(events, REACHES_BACK) == []


async def _run_logged(monkeypatch, log_dir: Path, last_price_dates: dict[int, date], last_fx_dates: dict[str, date]) -> dict:
    """One ``run_history_sync`` of assets 941 and 942 and pairs EUR-USD and CHF-EUR, every item synced, its job log in
    ``log_dir``: the state it wrote, its entry, its "Scheduler: history sync" events and the windows it asked for."""
    log_dir.mkdir()
    monkeypatch.setattr(joblog, "get_data_dir", lambda: log_dir)
    _install_fake_session(
        monkeypatch,
        asset_rows=[_asset_row(941, "Behind Or Not"), _asset_row(942, "Saved Yesterday")],
        routes=[_route("EUR", "USD"), _route("CHF", "EUR")],
        last_price_dates=last_price_dates,
        last_fx_dates=last_fx_dates,
    )
    asset_recorder: dict = {}
    fx_recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=asset_recorder)
    _install_fx_double(monkeypatch, recorder=fx_recorder)
    state = SchedulerState()
    with _captured_job_log() as events:
        await jobs.run_history_sync(state, horizon_days=14)
    return {
        "state": state.history_sync,
        "entry": _sole_entry("history_sync"),
        "events": _logged(events, HISTORY_SYNC_EVENT),
        "asset_start": asset_recorder["date_ranges"][941][0],
        "fx_start": fx_recorder["date_range"][0],
    }


@pytest.mark.asyncio
async def test_history_sync_reaching_back_changes_neither_the_state_nor_the_entry(monkeypatch, isolated_joblog_dir):
    """Z-5: the same assets and pairs, the same provider answers, synced once caught up and once from 90 days behind. The
    ``JobState``, the job log entry and the "Scheduler: history sync" event are the same but for the time they carry:
    reaching back adds no field and changes no value there. It is told by its own event only."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    long_ago = today - timedelta(days=90)
    up_to_date = {"EUR-USD": yesterday, "CHF-EUR": yesterday}
    caught_up = await _run_logged(monkeypatch, isolated_joblog_dir / "caught-up", {941: yesterday, 942: yesterday}, up_to_date)
    behind = await _run_logged(monkeypatch, isolated_joblog_dir / "behind", {941: long_ago, 942: yesterday}, {**up_to_date, "EUR-USD": long_ago})

    # Barrier: the second run did reach back and the first did not, or comparing them would prove nothing.
    horizon_start = today - timedelta(days=14)
    resumed = long_ago + timedelta(days=1)
    assert (caught_up["asset_start"], caught_up["fx_start"]) == (horizon_start, horizon_start)
    assert (behind["asset_start"], behind["fx_start"]) == (resumed, resumed), "the run 90 days behind did not reach back"
    assert len(caught_up["events"]) == 1, f"the run's own event is missing from the capture: {caught_up['events']}"

    assert _timeless_state(behind["state"]) == _timeless_state(caught_up["state"])
    assert _timeless(behind["entry"], "ts", "duration_s") == _timeless(caught_up["entry"], "ts", "duration_s")
    assert [_timeless(event, "duration_s") for event in behind["events"]] == [_timeless(event, "duration_s") for event in caught_up["events"]]


# ============================================================================
# Live-schema guard — the only tests here that reach the shared database
# ============================================================================


@pytest.mark.asyncio
async def test_current_price_select_stays_valid_against_live_schema(monkeypatch, isolated_joblog_dir):
    """Run the real SELECT against the real database, with the provider call doubled.

    The tests above replace the session, so a rename of ``Asset.icon_url`` or of
    ``AssetProviderAssignment.asset_id`` would go unnoticed. This one executes the
    statement for real. It asserts no count it did not create: the number of active
    assets is shared state, so the assertion is the *relation* between what the job
    selected and what it logged, which holds for zero assets as well.
    """
    recorder: dict = {}
    _install_current_price_double(monkeypatch, recorder=recorder)

    state = SchedulerState()
    await jobs.run_current_price_refresh(state)

    observed = recorder.get("asset_ids", [])
    entries = joblog.read_entries()
    # Exactly one entry per run, empty runs included — the panel needs to see that the
    # job happened even when it had nothing to do.
    assert len(entries) == 1
    logged_ids = {item["asset_id"] for entry in entries for item in entry["items"]}
    assert logged_ids == set(observed)


@pytest.mark.asyncio
async def test_history_sync_selects_stay_valid_against_live_schema(monkeypatch, isolated_joblog_dir):
    """Same guard for the asset SELECT *and* the FxConversionRoute SELECT.

    Both doubles return empty result sets: the subject is the two statements, not the
    contents of a database this test does not own.
    """
    asset_recorder: dict = {}
    fx_recorder: dict = {}
    _install_refresh_double(monkeypatch, recorder=asset_recorder, empty=True)
    _install_fx_double(monkeypatch, recorder=fx_recorder, empty=True)

    state = SchedulerState()
    await jobs.run_history_sync(state)

    # Unlike current-price, history-sync always reports.
    entry = _sole_entry("history_sync")
    assert entry["assets"] == []
    assert entry["fx"] == []
    assert state.history_sync.last_run_at is not None
    # Every pair the job derived from the live routes is a well-formed slug.
    for pair in fx_recorder.get("pairs", []):
        assert len(pair.split("-")) == 2, f"malformed pair slug built from a live route: {pair!r}"


#: Lot Z-5, live: an asset id no price can carry, asset ids being autoincremented from 1.
IMPOSSIBLE_ASSET_ID = -1
#: A pair no rate is stored for: codes shaped like ISO 4217, unassigned, written by no test. Not "AAA-ZZZ", the pair one
#: thinks of first: ``test_db/test_numeric_truncation.py`` commits rates for it.
NEVER_STORED_PAIR = "XQB-XQC"
#: How many stored assets, and how many stored pairs, a live case asks about.
LIVE_SAMPLE = 3


async def _begin_read_snapshot(session: AsyncSession) -> None:
    """Open an explicit read transaction: every SELECT of ``session`` from here on sees one snapshot of the database.

    Under pysqlite's legacy transaction control each bare SELECT runs in an implicit transaction of its own, so two
    SELECTs may see two states of a database other units are writing to, and comparing what they read would fail for a
    neighbour's commit. In WAL mode a deferred read transaction blocks no writer; closing the session rolls it back.
    Nothing is written.
    """
    await session.execute(text("BEGIN"))


def _calendar_day(value: object) -> bool:
    """A ``date`` and not a ``datetime``, which is one too but cannot be compared with a date."""
    return isinstance(value, date) and not isinstance(value, datetime)


def _reversed_pair(slug: str) -> str:
    base, quote = slug.split("-")
    return f"{quote}-{base}"


@pytest.mark.asyncio
async def test_last_price_dates_stays_valid_against_live_schema():
    """Z-5: ``_last_price_dates`` on a real session against the real database, read only.

    It asserts no count it did not create. Within one snapshot, asked about a few assets that have prices and an id none
    can have, it answers for each of the first the latest date of its prices — what the test reads itself, row by row —
    and nothing for the id. With no price stored, only the id is asked about, and it holds too.
    """
    async with AsyncSession(get_async_engine()) as session:
        await _begin_read_snapshot(session)
        sample = select(PriceHistory.asset_id).distinct().order_by(PriceHistory.asset_id).limit(LIVE_SAMPLE)
        asked = [*(await session.execute(sample)).scalars().all(), IMPOSSIBLE_ASSET_ID]
        stored = (await session.execute(select(PriceHistory.asset_id, PriceHistory.date).where(PriceHistory.asset_id.in_(asked)))).all()
        last = await jobs._last_price_dates(session, asked)

    latest: dict[int, date] = {}
    for asset_id, day in stored:
        latest[asset_id] = max(day, latest.get(asset_id, day))
    assert IMPOSSIBLE_ASSET_ID not in last, f"an id no price can carry got a date: {last}"
    assert set(last) <= set(asked), f"answered about ids it was not asked about: {set(last) - set(asked)}"
    assert all(_calendar_day(day) for day in last.values()), f"a last saved date is not a date: {last}"
    assert last == latest, f"not the latest stored date of each asset asked about, within one snapshot: expected {latest}, got {last}"


@pytest.mark.asyncio
async def test_last_fx_dates_stays_valid_against_live_schema():
    """Z-5: ``_last_fx_dates`` on a real session against the real database, read only.

    A rate is stored with base and quote in alphabetical order; a pair is asked about as a slug, in either order. Within
    one snapshot, both orders of a few stored pairs answer the latest date of the pair's rates — what the test reads
    itself, row by row —, each under the slug it was asked as; a pair with no rate, in either order, answers nothing.
    With no rate stored, only that pair is asked about, and it holds too.
    """
    async with AsyncSession(get_async_engine()) as session:
        await _begin_read_snapshot(session)
        sample = select(FxRate.base, FxRate.quote).distinct().order_by(FxRate.base, FxRate.quote).limit(LIVE_SAMPLE)
        stored_pairs = (await session.execute(sample)).all()
        latest: dict[str, date] = {}
        for base, quote in stored_pairs:
            days = (await session.execute(select(FxRate.date).where(FxRate.base == base, FxRate.quote == quote))).scalars().all()
            latest[f"{base}-{quote}"] = latest[f"{quote}-{base}"] = max(days)
        never = [NEVER_STORED_PAIR, _reversed_pair(NEVER_STORED_PAIR)]
        asked = [*latest, *never]
        last = await jobs._last_fx_dates(session, asked)

    assert not set(never) & set(last), f"a pair with no rate got a date: {last}"
    assert set(last) <= set(asked), f"answered about slugs it was not asked about: {set(last) - set(asked)}"
    assert all(_calendar_day(day) for day in last.values()), f"a last saved date is not a date: {last}"
    for base, quote in stored_pairs:
        assert last.get(f"{base}-{quote}") == last.get(f"{quote}-{base}"), f"{base}-{quote} and {quote}-{base} are one stored pair: {last}"
    assert last == latest, f"not the latest stored date of each pair asked about, within one snapshot: expected {latest}, got {last}"
