"""The scheduler's third job, ``profile_read``: the weekly read of the enrichers (project 68, lot B6).

Under test, as the contract of B6 states it:

1. **Which assets** (``jobs.run_profile_read(state, settings)``): the ACTIVE assets whose enricher ``config`` is not
   empty. An inactive asset is skipped (the manual «Aggiorna» still reads it: ``test_enricher_refresh.py``); an asset
   without bindings, or with an empty ``config``, too.
2. **A regular round** (``state.profile_read.retry_at`` not come): ``round_started_at`` = now, and
   ``refresh_assets(session, ids, hold_deferred=True)``. The ``JobState``: ``last_items_ok`` the assets read with no
   error and nothing deferred, ``last_items_deferred`` the assets with a ``RATE_LIMITED`` read, ``last_items_err`` the
   rest; ``last_status`` by ``_classify_job_status``; ``retry_at`` now + the shortest ``retry_after`` of the deferred
   reads, or now + 15 minutes when none of them carries one (lot B6c, below); ``round_started_at`` kept.
3. **A retry round** (the job runs because ``retry_at`` came): ``refresh_assets(session, ids, read_since=<round
   start>, hold_deferred=False)``. The bindings already read in this round (state ``read_at`` ≥ the round's start, ok
   or not_found) are not read again — their plugin is not called — and their values still join the merge, from the
   read cache. Only ONE retry: a retry round never sets ``retry_at`` again, even when a read is refused again; it keeps
   ``round_started_at``. A regular round after it reads everything again and starts a new round.
4. **The log**: one entry per run (``joblog.build_profile_read_entry``): ``job`` "profile_read", ``summary {ok, err,
   deferred}``, ``retry_at``, ``items [{asset_id, name, status: ok|error|deferred, voices_written, error}]``; it validates
   as a ``SchedulerLogEntry``.
5. **Holding a voice for the second round** (``refresh_assets(…, hold_deferred=True)``, consultant 16/11): when an
   enricher's read of an asset is ``RATE_LIMITED``, the voices it declares for the asset's type
   (``plugin.voices[asset_type]``) whose merged winner comes AFTER it in the asset's order are not written in that round;
   the others are. With ``hold_deferred=False`` the usual «source down → the next one» applies.
6. **The default wait** (lot B6c, consultant and coordinator): the real enrichers refuse without a wait, so a round
   whose deferred reads carry no ``retry_after`` sets ``retry_at`` = now + **15 minutes**, in the state and in the
   entry. A plugin-given wait still wins: the shortest KNOWN wait decides, even when it is longer than 15 minutes and
   even beside a refusal without one. Nothing deferred (errors included) → no retry. The cap stays: a retry round
   refused again, without a wait too, sets no third round, and the held voices are written from the next source. The
   default lives in the profile-read job only: the shared ``jobs._retry_at`` still answers None without a wait, so the
   price jobs are unchanged (job-level pin: ``test_scheduler_jobs.py::
   test_current_price_refresh_with_no_pause_known_leaves_no_retry_at``).

The plan's case «un rifiuto rimanda e il secondo giro salta chi è già letto» is
``test_a_refusal_defers_and_the_second_round_skips_what_was_read``; the consultant's two are
``test_round_one_holds_the_voice_and_round_two_writes_it_from_the_first`` and
``test_the_first_refusing_again_in_round_two_writes_the_voice_from_the_second``.

The read cache is process-wide and an ``ok`` read stays there 30 minutes: it would hide a binding read again. So a
case that counts the plugin's calls across rounds clears it between them; the consultant's second case keeps it, since
the contract takes the skipped binding's value from it. Round two is fed the very ``JobState`` round one wrote, only its
``retry_at`` moved into the past (the time has come): a wrong ``round_started_at`` written by the job shows.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all``, opened as production opens
its own; the job reaches it through ``jobs.get_async_engine`` (and ``refresh.get_async_engine``), replaced for the
test; a barrier checks that the entry names exactly the assets of that file. The job log is redirected under
``tmp_path`` (``joblog.get_data_dir``). The enrichers are synthetic classes registered under ``lab_profread_*`` codes
and removed at teardown, as ``test_enricher_refresh.py`` does. The job's own clock is the wall clock: its times are
bracketed by readings taken before and after the call. Nothing sleeps; every call is bounded by ``DEADLINE``.

Not pinned: the default of ``hold_deferred``; the ``ok`` count of an asset a retry round fully skips (only that ok +
err + deferred is the number of assets); ``error`` on a deferred item; ``voices_written`` beyond the cases that pin it.

Red until B6: ``jobs.run_profile_read``, ``refresh_assets(hold_deferred=…)``, ``JobState.round_started_at`` and
``SchedulerState.profile_read`` do not exist; each case fails at its first call, never at collection.

Red until B6c: the cases of section 6 where no deferred read carries a wait (``retry_at`` is None today). The known-wait,
nothing-deferred and shared-function cases are green by design: barriers against a default used as a cap, mixed into
the minimum, applied without a refusal, or moved into ``_retry_at``. The name of the module constant is not pinned.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import threading
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.enrichers import bindings, refresh
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherReadStatus, EnricherRecognition, EnricherTerms
from backend.app.services.enrichers.refresh import AssetRefreshResult, refresh_assets
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.platform.scheduler import joblog, jobs
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import SchedulerState
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.app.utils.runtime.cache import clear_cache
from backend.test_scripts.test_utils import print_section, print_success

SETTINGS_FAMILY = "enricher"
LAB_PREFIX = "lab_profread_"
LAB_CLASS_PREFIX = "LabProfReadEnricher_"
CACHE_NAME = "enricher_read"
#: The bound on every job run, refresh and read: against a hang, never a wait.
DEADLINE = 15.0
LAB_DATE = date(2026, 11, 13)
NOW = datetime(2026, 11, 14, 2, 0, tzinfo=UTC)
#: Every voice a lab may yield by default, declared for ETF.
LAB_VOICES = frozenset({"ter", "fund_size", "description"})
FUND_SIZE = {"amount": "1000", "currency": "EUR"}

#: The outcomes a lab's table can give instead of values.
NOT_FOUND = "not_found"
ERROR = "error"
RATE = "rate_limited"
LAB_ERROR_CODE = "LAB_ERROR"
RETRY_AFTER = 30.0

Script = Callable[[list[EnricherBinding], frozenset[str] | None], Iterator[EnricherReadItem]]


# =============================================================================
# SYNTHETIC ENRICHERS
# =============================================================================


def _ident(tag: str) -> str:
    """An identifier no other test (and no other run within the cache's TTL) uses."""
    return f"LPR{tag}{uuid.uuid4().hex[:10].upper()}"


def _binding(identifier: str) -> EnricherBinding:
    return EnricherBinding(identifier_type="ISIN", identifier=identifier, params={})


def _config_entry(binding: EnricherBinding) -> dict[str, Any]:
    return {"identifier_type": binding.identifier_type, "identifier": binding.identifier, **dict(binding.params)}


def _rate(seconds: float | None = RETRY_AFTER) -> tuple[str, float | None]:
    """A table entry: refused for too many requests, ``retry_after`` ``seconds`` (None: the refusal gives no wait)."""
    return (RATE, seconds)


@dataclass
class Lab:
    """A registered synthetic enricher: its code, its answers (identifier → values or outcome), every ``read`` call."""

    code: str
    table: dict[str, Any]
    calls: list[tuple[tuple[EnricherBinding, ...], frozenset[str] | None]] = field(default_factory=list)

    def identifiers_read(self) -> list[str]:
        return [binding.identifier for bindings_read, _ in self.calls for binding in bindings_read]

    def reads_of(self, identifier: str) -> int:
        return self.identifiers_read().count(identifier)


def _table_script(table: Mapping[str, Any]) -> Script:
    """Answer each binding from ``table`` by its identifier, read at the call (a test may change it between rounds)."""

    def script(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:
        for index, binding in enumerate(bindings_read):
            spec = table[binding.identifier]
            if spec == NOT_FOUND:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
            elif spec == ERROR:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=LAB_ERROR_CODE, error_message="the lab fails on purpose")
            elif isinstance(spec, tuple) and spec[0] == RATE:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=spec[1])
            else:
                values = dict(spec) if keys is None else {key: value for key, value in spec.items() if key in keys}
                yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_date=LAB_DATE)

    return script


class _LabMethods(EnricherPlugin):
    """The abstract methods but ``read``."""

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        return EnricherRecognition(found=True, name=f"Lab {binding.identifier}")

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://lab.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []


@pytest.fixture(autouse=True)
def _fresh_read_cache() -> Iterator[None]:
    """The read cache is process-wide: empty before and after each test."""
    clear_cache(CACHE_NAME)
    yield
    clear_cache(CACHE_NAME)


@pytest.fixture(autouse=True)
def _no_timezone_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The store's today follows ``scheduler_timezone``; a deployment variable must not move it under the test."""
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)


@pytest.fixture
def lab() -> Iterator[Callable[..., Lab]]:
    """``lab(name, table=…, voices=…)`` registers a synthetic enricher and gives back its ``Lab``. ``voices`` maps asset
    types to the voices it declares (default: ``LAB_VOICES`` for ETF); it covers those types (degree 10). Removed from the
    registry, with its claims, at teardown."""
    labs: list[Lab] = []

    def register(name: str, *, table: dict[str, Any] | None = None, voices: Mapping[AssetType, frozenset[str]] | None = None) -> Lab:
        code = f"{LAB_PREFIX}{name}"
        handle = Lab(code=code, table={} if table is None else table)
        lock = threading.Lock()
        answer = _table_script(handle.table)
        declared = dict(voices) if voices is not None else {AssetType.ETF: LAB_VOICES}

        def read(self, bindings_read, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the contract's signature
            received = None if keys is None else frozenset(keys)
            with lock:
                handle.calls.append((tuple(bindings_read), received))
            yield from answer(list(bindings_read), received)

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"Lab profile read {name} (testing)",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": ("ISIN",),
            "default_priority": {asset_type: (10 if asset_type in declared else None) for asset_type in AssetType},
            "voices": declared,
            "read": read,
        }
        labs.append(handle)
        EnricherRegistry.register(type(f"{LAB_CLASS_PREFIX}{name}", (_LabMethods,), attributes))
        assert isinstance(EnricherRegistry.get_plugin_instance(code), EnricherPlugin), f"barrier: {code} is not served after its registration"
        return handle

    yield register
    storage = EnricherRegistry._get_storage()
    for handle in labs:
        stored = storage.get(handle.code)
        if stored is not None and getattr(stored, "__name__", "").startswith(LAB_CLASS_PREFIX):
            storage.pop(handle.code, None)
        release_env_variables(SETTINGS_FAMILY, handle.code)


# =============================================================================
# THE PRIVATE DATABASE AND THE JOB'S SURROUNDINGS
# =============================================================================


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profile_read.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def job_env(engine: AsyncEngine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncEngine:
    """The job's engine is the private file's, its log is under tmp_path: nothing of the lane is read or written."""
    monkeypatch.setattr(jobs, "get_async_engine", lambda: engine)
    monkeypatch.setattr(refresh, "get_async_engine", lambda: engine)
    log_root = tmp_path / "joblog"
    log_root.mkdir()
    monkeypatch.setattr(joblog, "get_data_dir", lambda: log_root)
    return engine


async def _asset(engine: AsyncEngine, tag: str, *, active: bool = True, asset_type: AssetType = AssetType.ETF) -> tuple[int, str]:
    """A new asset of the private file: its id and display name."""
    name = f"Lab profile read {tag} {uuid.uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=asset_type, active=active)
        session.add(asset)
        await session.commit()
    return int(asset.id), name


async def _bind(engine: AsyncEngine, asset_id: int, config: Mapping[str, EnricherBinding]) -> None:
    async with AsyncSession(engine) as session:
        await bindings.save_config(session, asset_id, {code: _config_entry(binding) for code, binding in config.items()})
        await session.commit()


async def _rows(engine: AsyncEngine, asset_id: int, key: str | None = None) -> list[AssetProfileUpdate]:
    """The asset's profile rows (of ``key`` when given), read from a session of their own, in the store's order."""
    async with AsyncSession(engine) as session:
        statement = select(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == asset_id)
        if key is not None:
            statement = statement.where(AssetProfileUpdate.key == key)
        return list((await session.execute(statement.order_by(AssetProfileUpdate.read_on, AssetProfileUpdate.id))).scalars().all())


def _value_and_source(rows: Sequence[AssetProfileUpdate]) -> list[tuple[Any, str]]:
    """Each row as (its value in the stored form of its voice, its source), as ``test_enricher_refresh.py`` reads them."""
    return [(None if row.value is None else normalize(row.key, json.loads(row.value)), row.source) for row in rows]


async def _state(engine: AsyncEngine, asset_id: int) -> dict[str, dict[str, Any]]:
    async with AsyncSession(engine) as session:
        row = (await bindings.load_enrichers(session, [asset_id])).get(asset_id)
    return {} if row is None else row.state


def _settings() -> SchedulerSettings:
    """Every field given: the job reads none of them beyond its own."""
    return SchedulerSettings(
        scheduler_enabled=True,
        current_price_frequency_minutes=10,
        history_sync_times=[time(6, 0), time(23, 0)],
        history_sync_days=["mon", "tue", "wed", "thu", "fri"],
        history_sync_horizon_days=14,
        scheduler_timezone="UTC",
        profile_read_days=["sat"],
        profile_read_times=[time(3, 0)],
    )


async def _run_round(state: SchedulerState) -> tuple[datetime, datetime]:
    """One run of the job on ``state``, bounded; the wall clock before and after it."""
    before = datetime.now(UTC)
    await asyncio.wait_for(jobs.run_profile_read(state, _settings()), DEADLINE)
    return before, datetime.now(UTC)


def _retry_has_come(state: SchedulerState) -> None:
    """The time of the retry has come: ``retry_at`` moved into the past, every other field as round one wrote it."""
    assert state.profile_read.retry_at is not None, f"barrier: round one set a retry: {state.profile_read}"
    state.profile_read = dataclasses.replace(state.profile_read, retry_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat())


def _utc(value: Any, what: str) -> datetime:
    assert isinstance(value, str), f"{what} is an ISO text: {value!r}"
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None, f"{what} carries its offset: {value}"
    return parsed.astimezone(UTC)


def _entries() -> list[dict[str, Any]]:
    """The profile-read entries of the test's own log, newest first."""
    return [entry for entry in joblog.read_entries() if entry.get("job") == "profile_read"]


def _item(entry: Mapping[str, Any], asset_id: int) -> dict[str, Any]:
    found = [item for item in entry.get("items", []) if item.get("asset_id") == asset_id]
    assert len(found) == 1, f"one item for asset {asset_id}: {entry.get('items')}"
    return found[0]


def _counts(state: SchedulerState) -> tuple[int, int, int]:
    job = state.profile_read
    return job.last_items_ok, job.last_items_err, job.last_items_deferred


# =============================================================================
# 1. WHICH ASSETS
# =============================================================================


@pytest.mark.asyncio
async def test_only_the_active_assets_with_enrichers_are_read(job_env: AsyncEngine, lab) -> None:
    """An active asset with a binding is read; an inactive one with a binding, an active one without a row and one with an
    empty ``config`` are not. The entry names the one read, and nothing of the lane (private-file barrier)."""
    print_section("profile_read: which assets")
    i_active, i_inactive = _ident("AC"), _ident("IN")
    a = lab("which", table={i_active: {"ter": "0.0022", "description": "read"}, i_inactive: {"ter": "0.0040"}})
    active, active_name = await _asset(job_env, "active")
    inactive, _ = await _asset(job_env, "inactive", active=False)
    unbound, _ = await _asset(job_env, "unbound")
    emptied, _ = await _asset(job_env, "emptied")
    await _bind(job_env, active, {a.code: _binding(i_active)})
    await _bind(job_env, inactive, {a.code: _binding(i_inactive)})
    await _bind(job_env, emptied, {})
    state = SchedulerState()

    before, after = await _run_round(state)

    assert a.identifiers_read() == [i_active], f"only the active asset's binding is read: {a.calls}"
    job = state.profile_read
    assert (job.last_status, *_counts(state), job.retry_at) == ("ok", 1, 0, 0, None), job
    assert before <= _utc(job.last_run_at, "last_run_at") <= after
    assert before <= _utc(job.round_started_at, "round_started_at") <= after, "a regular round starts a round"
    (entry,) = _entries()
    assert {item["asset_id"] for item in entry["items"]} == {active}, f"the entry names exactly the asset read, of the private file: {entry['items']}"
    item = _item(entry, active)
    assert (item["name"], item["status"], item["voices_written"], item.get("error")) == (active_name, "ok", 2, None), item
    assert [row.key for row in await _rows(job_env, inactive)] == [] and await _state(job_env, inactive) == {}, "the inactive asset is not touched"
    assert {unbound, emptied}.isdisjoint({item["asset_id"] for item in entry["items"]})
    print_success("the active asset with enrichers only")


@pytest.mark.asyncio
async def test_with_nothing_to_read_the_run_still_records_itself(job_env: AsyncEngine) -> None:
    """No asset with enrichers: the run is ``ok`` with nothing counted, and still writes its entry — summary zeros, no
    item, no retry."""
    print_section("profile_read: nothing to read")
    await _asset(job_env, "alone")
    state = SchedulerState()

    await _run_round(state)

    assert (state.profile_read.last_status, *_counts(state), state.profile_read.retry_at) == ("ok", 0, 0, 0, None), state.profile_read
    (entry,) = _entries()
    assert (entry["summary"], entry["items"], entry.get("retry_at")) == ({"ok": 0, "err": 0, "deferred": 0}, [], None), entry
    print_success("recorded")


# =============================================================================
# 2. A REGULAR ROUND
# =============================================================================


@pytest.mark.asyncio
async def test_a_regular_round_counts_assets_and_retries_at_the_shortest_pause(job_env: AsyncEngine, lab) -> None:
    """Five assets: one ok; one refused for 90 s; one refused for 30 s by one enricher and in error at another (deferred:
    a refused read makes the asset deferred); one in error; one ok at one enricher and in error at another (an error).
    ``last_items_ok`` 1, ``last_items_err`` 2, ``last_items_deferred`` 2, "partial"; ``retry_at`` now + 30 s;
    ``round_started_at`` the round's start, at or before every ``read_at`` of the round. The entry says the same, item by
    item, and validates as a ``SchedulerLogEntry``."""
    print_section("profile_read: a regular round")
    ids = {tag: _ident(tag) for tag in ("OK", "R90", "R30", "E30", "ERR", "MOK", "MER")}
    a = lab("round_a", table={ids["OK"]: {"ter": "0.0022", "description": "fine"}, ids["R90"]: _rate(90.0), ids["R30"]: _rate(30.0), ids["ERR"]: ERROR, ids["MOK"]: {"ter": "0.0011"}})
    b = lab("round_b", table={ids["E30"]: ERROR, ids["MER"]: ERROR})
    ok, ok_name = await _asset(job_env, "ok")
    slow, _ = await _asset(job_env, "r90")
    mixed_rate, _ = await _asset(job_env, "r30")
    broken, broken_name = await _asset(job_env, "err")
    half, _ = await _asset(job_env, "half")
    await _bind(job_env, ok, {a.code: _binding(ids["OK"])})
    await _bind(job_env, slow, {a.code: _binding(ids["R90"])})
    await _bind(job_env, mixed_rate, {a.code: _binding(ids["R30"]), b.code: _binding(ids["E30"])})
    await _bind(job_env, broken, {a.code: _binding(ids["ERR"])})
    await _bind(job_env, half, {a.code: _binding(ids["MOK"]), b.code: _binding(ids["MER"])})
    state = SchedulerState()

    before, after = await _run_round(state)

    job = state.profile_read
    assert (job.last_status, *_counts(state)) == ("partial", 1, 2, 2), job
    assert (job.consecutive_failures, job.next_attempt_at, job.last_error) == (0, None, None), job
    retry_at = _utc(job.retry_at, "retry_at")
    assert before + timedelta(seconds=30) <= retry_at <= after + timedelta(seconds=30), f"now + the shortest pause (30 s): {job.retry_at}"
    round_start = _utc(job.round_started_at, "round_started_at")
    assert before <= round_start <= after, job.round_started_at
    read_ats = [_utc(entry["read_at"], "read_at") for asset_id in (ok, slow, mixed_rate, broken, half) for entry in (await _state(job_env, asset_id)).values()]
    assert read_ats and all(read_at >= round_start for read_at in read_ats), f"the round starts before its reads: {round_start} vs {read_ats}"

    (entry,) = _entries()
    assert (entry["status"], entry["summary"], _utc(entry.get("retry_at"), "the entry's retry_at")) == ("partial", {"ok": 1, "err": 2, "deferred": 2}, retry_at), entry
    assert {item["asset_id"]: item["status"] for item in entry["items"]} == {ok: "ok", slow: "deferred", mixed_rate: "deferred", broken: "error", half: "error"}
    assert (_item(entry, ok)["name"], _item(entry, ok)["voices_written"], _item(entry, ok).get("error")) == (ok_name, 2, None)
    broken_item = _item(entry, broken)
    assert broken_item["name"] == broken_name and broken_item["voices_written"] == 0 and isinstance(broken_item.get("error"), str) and broken_item["error"], broken_item
    from pydantic import TypeAdapter  # noqa: PLC0415 — test-local

    from backend.app.schemas.settings import SchedulerLogEntry  # noqa: PLC0415 — read at call: the union of B6

    parsed = TypeAdapter(SchedulerLogEntry).validate_python(json.loads(json.dumps(entry, default=str)))
    assert type(parsed).__name__ == "SchedulerLogProfileReadEntry", type(parsed).__name__
    print_success("counted by asset; retry at the shortest pause")


# =============================================================================
# 3. THE RETRY ROUND
# =============================================================================


@pytest.mark.asyncio
async def test_a_refusal_defers_and_the_second_round_skips_what_was_read(job_env: AsyncEngine, lab) -> None:
    """«Un rifiuto rimanda e il secondo giro salta chi è già letto». Asset P: A (ok, ``description``) then B (refused,
    ``ter``); asset Q: A ok. Round one: P deferred, Q ok, a retry. The retry round (cache cleared, so a call shows):
    A is called for neither asset, B once for P, now ok: its ``ter`` written; no ``retry_at``, the round's start kept,
    nothing deferred, the two assets counted."""
    print_section("profile_read: the retry round skips what was read")
    ip_a, ip_b, iq_a = _ident("PA"), _ident("PB"), _ident("QA")
    a = lab("skip_a", table={ip_a: {"description": "from a"}, iq_a: {"description": "q from a"}}, voices={AssetType.ETF: frozenset({"description"})})
    b = lab("skip_b", table={ip_b: _rate()}, voices={AssetType.ETF: frozenset({"ter"})})
    p, _ = await _asset(job_env, "p")
    q, _ = await _asset(job_env, "q")
    await _bind(job_env, p, {a.code: _binding(ip_a), b.code: _binding(ip_b)})
    await _bind(job_env, q, {a.code: _binding(iq_a)})
    state = SchedulerState()
    await _run_round(state)
    assert (state.profile_read.last_status, *_counts(state)) == ("partial", 1, 0, 1), f"barrier: round one deferred P: {state.profile_read}"
    round_one = state.profile_read
    calls = {a.code: len(a.identifiers_read()), b.code: len(b.identifiers_read())}
    clear_cache(CACHE_NAME)
    b.table[ip_b] = {"ter": "0.0031"}
    _retry_has_come(state)

    await _run_round(state)

    assert {a.code: len(a.identifiers_read()) - calls[a.code], b.code: len(b.identifiers_read()) - calls[b.code]} == {a.code: 0, b.code: 1}, f"the retry round reads only what was refused: {a.calls} / {b.calls}"
    assert b.identifiers_read()[-1] == ip_b
    job = state.profile_read
    assert job.retry_at is None, f"one retry only: {job}"
    assert job.round_started_at == round_one.round_started_at, "a retry continues the round it retries"
    assert job.last_items_deferred == 0 and job.last_items_ok + job.last_items_err + job.last_items_deferred == 2, job
    assert _value_and_source(await _rows(job_env, p, "ter")) == [(normalize("ter", "0.0031"), b.code)], "the refused voice is written in round two"
    entries = _entries()
    assert len(entries) == 2, f"one entry per run: {entries}"
    assert _item(entries[0], p)["status"] == "ok" and entries[0].get("retry_at") is None, entries[0]
    print_success("only the refused binding read again")


@pytest.mark.asyncio
async def test_a_retry_round_refused_again_sets_no_retry(job_env: AsyncEngine, lab) -> None:
    """The refused binding is refused again in the retry round: it is read (once), the asset is deferred again, but no
    ``retry_at`` is set: the next read is the next regular round."""
    print_section("profile_read: refused again, no second retry")
    identifier = _ident("RA")
    b = lab("again", table={identifier: _rate(45.0)})
    asset_id, _ = await _asset(job_env, "again")
    await _bind(job_env, asset_id, {b.code: _binding(identifier)})
    state = SchedulerState()
    await _run_round(state)
    round_one = state.profile_read
    _retry_has_come(state)

    await _run_round(state)

    assert b.reads_of(identifier) == 2, f"read in both rounds: {b.calls}"
    job = state.profile_read
    assert (job.retry_at, job.last_items_deferred, job.round_started_at) == (None, 1, round_one.round_started_at), job
    assert _item(_entries()[0], asset_id)["status"] == "deferred" and _entries()[0].get("retry_at") is None
    print_success("one retry only")


@pytest.mark.asyncio
async def test_a_regular_round_after_the_retry_reads_everything_and_starts_a_new_round(job_env: AsyncEngine, lab) -> None:
    """Negative control: after the retry round, a regular round (no ``retry_at``, cache cleared) reads every binding
    again — the ones read in the old round too — and starts a new round."""
    print_section("profile_read: the next regular round reads everything")
    i_a, i_b = _ident("NA"), _ident("NB")
    a = lab("next_a", table={i_a: {"description": "a"}}, voices={AssetType.ETF: frozenset({"description"})})
    b = lab("next_b", table={i_b: _rate()}, voices={AssetType.ETF: frozenset({"ter"})})
    asset_id, _ = await _asset(job_env, "next")
    await _bind(job_env, asset_id, {a.code: _binding(i_a), b.code: _binding(i_b)})
    state = SchedulerState()
    await _run_round(state)
    _retry_has_come(state)
    b.table[i_b] = {"ter": "0.0031"}
    await _run_round(state)
    old_round = _utc(state.profile_read.round_started_at, "round_started_at")
    assert state.profile_read.retry_at is None, f"barrier: the retry round set no retry: {state.profile_read}"
    calls = (a.reads_of(i_a), b.reads_of(i_b))
    clear_cache(CACHE_NAME)

    before, after = await _run_round(state)

    assert (a.reads_of(i_a) - calls[0], b.reads_of(i_b) - calls[1]) == (1, 1), f"a regular round reads every binding: {a.calls} / {b.calls}"
    new_round = _utc(state.profile_read.round_started_at, "round_started_at")
    assert before <= new_round <= after and new_round > old_round, f"a new round: {old_round} → {new_round}"
    print_success("a new round")


# =============================================================================
# 4. THE CONSULTANT'S TWO CASES (16/11)
# =============================================================================


async def _held_setup(job_env: AsyncEngine, lab, tag: str) -> tuple[Lab, Lab, int, str, str]:
    """An asset bound to A then B. A declares ``ter`` and ``description`` and is refused; B gives ``ter`` 0.0031 (A will
    give 0.0022) and ``fund_size``, which A does not declare."""
    i_a, i_b = _ident(f"{tag}A"), _ident(f"{tag}B")
    a = lab(f"{tag.lower()}_first", table={i_a: _rate()}, voices={AssetType.ETF: frozenset({"ter", "description"})})
    b = lab(f"{tag.lower()}_second", table={i_b: {"ter": "0.0031", "fund_size": FUND_SIZE}}, voices={AssetType.ETF: frozenset({"ter", "fund_size"})})
    asset_id, _ = await _asset(job_env, tag)
    await _bind(job_env, asset_id, {a.code: _binding(i_a), b.code: _binding(i_b)})
    return a, b, asset_id, i_a, i_b


@pytest.mark.asyncio
async def test_round_one_holds_the_voice_and_round_two_writes_it_from_the_first(job_env: AsyncEngine, lab) -> None:
    """Consultant, case one: round one does not write ``ter`` (A, first, was refused: B's different value waits),
    writes ``fund_size`` (A does not declare it); round two, A answers 0.0022: ``ter`` is written from A — one row, A's."""
    print_section("profile_read: held in round one, written from the first in round two")
    a, b, asset_id, i_a, _ = await _held_setup(job_env, lab, "HA")
    state = SchedulerState()

    await _run_round(state)

    assert await _rows(job_env, asset_id, "ter") == [], "round one holds the voice the refused enricher comes first for"
    assert _value_and_source(await _rows(job_env, asset_id, "fund_size")) == [(normalize("fund_size", FUND_SIZE), b.code)], "a voice the refused enricher does not declare is written"
    a.table[i_a] = {"ter": "0.0022", "description": "from a"}
    _retry_has_come(state)

    await _run_round(state)

    assert _value_and_source(await _rows(job_env, asset_id, "ter")) == [(normalize("ter", "0.0022"), a.code)], "one row, the first enricher's value"
    print_success("held, then written from the first")


@pytest.mark.asyncio
async def test_the_first_refusing_again_in_round_two_writes_the_voice_from_the_second(job_env: AsyncEngine, lab) -> None:
    """Consultant, case two: A refuses in round two too: ``ter`` is written from B (its round-one read, from the cache:
    B is not called again) — one row, B's; and no retry is set."""
    print_section("profile_read: refused again, written from the second")
    a, b, asset_id, _, i_b = await _held_setup(job_env, lab, "HB")
    state = SchedulerState()
    await _run_round(state)
    assert await _rows(job_env, asset_id, "ter") == [], "barrier: round one held the voice"
    b_calls = b.reads_of(i_b)
    _retry_has_come(state)

    await _run_round(state)

    assert b.reads_of(i_b) == b_calls, f"B was read in this round already: not called again: {b.calls}"
    assert _value_and_source(await _rows(job_env, asset_id, "ter")) == [(normalize("ter", "0.0031"), b.code)], "source down → the next one, in the second round"
    assert state.profile_read.retry_at is None
    print_success("written from the second")


# =============================================================================
# 5. refresh_assets(hold_deferred=…)
# =============================================================================


def normalize(key: str, raw: Any) -> Any:
    """``raw`` in the stored form of ``key``."""
    return normalize_value(key, raw)


async def _refresh(engine: AsyncEngine, asset_ids: Sequence[int], **kwargs: Any) -> list[AssetRefreshResult]:
    async def run() -> list[AssetRefreshResult]:
        async with AsyncSession(engine) as session:
            return await refresh_assets(session, asset_ids, **kwargs)

    return await asyncio.wait_for(run(), DEADLINE)


def _result(results: Sequence[AssetRefreshResult], asset_id: int) -> AssetRefreshResult:
    found = [result for result in results if result.asset_id == asset_id]
    assert len(found) == 1, f"one result for asset {asset_id}: {results}"
    return found[0]


async def _three_voices(engine: AsyncEngine, lab, tag: str) -> tuple[Lab, Lab, Lab, int]:
    """Order C, A, B on one ETF. A is refused and declares ``description`` and ``ter``. C (before A) gives
    ``description``; B (after A) gives ``ter`` and ``fund_size``."""
    i_c, i_a, i_b = _ident(f"{tag}C"), _ident(f"{tag}A"), _ident(f"{tag}B")
    c = lab(f"{tag.lower()}_c", table={i_c: {"description": "from c"}}, voices={AssetType.ETF: frozenset({"description"})})
    a = lab(f"{tag.lower()}_a", table={i_a: _rate()}, voices={AssetType.ETF: frozenset({"description", "ter"})})
    b = lab(f"{tag.lower()}_b", table={i_b: {"ter": "0.0031", "fund_size": FUND_SIZE}}, voices={AssetType.ETF: frozenset({"ter", "fund_size"})})
    asset_id, _ = await _asset(engine, tag)
    await _bind(engine, asset_id, {c.code: _binding(i_c), a.code: _binding(i_a), b.code: _binding(i_b)})
    return c, a, b, asset_id


@pytest.mark.asyncio
async def test_hold_deferred_holds_only_the_declared_voices_whose_winner_comes_after(engine: AsyncEngine, lab) -> None:
    """``hold_deferred=True``: of the three voices, ``ter`` (declared by A, winner B after A) is held; ``description``
    (declared, winner C before A) and ``fund_size`` (not declared by A) are written. A is listed in ``deferred``."""
    print_section("refresh_assets: hold_deferred=True")
    c, a, b, asset_id = await _three_voices(engine, lab, "HD")

    result = _result(await _refresh(engine, [asset_id], now=NOW, hold_deferred=True), asset_id)

    assert sorted(result.written) == ["description", "fund_size"], result
    assert [(outcome.code, outcome.error_code) for outcome in result.deferred] == [(a.code, RATE_LIMITED)], result.deferred
    assert await _rows(engine, asset_id, "ter") == []
    assert _value_and_source(await _rows(engine, asset_id, "description")) == [("from c", c.code)]
    assert _value_and_source(await _rows(engine, asset_id, "fund_size")) == [(normalize("fund_size", FUND_SIZE), b.code)]
    assert (await _state(engine, asset_id)).get(a.code, {}).get("error_code") == RATE_LIMITED, "the refusal is in the state"
    print_success("only the voice that waits for A")


@pytest.mark.asyncio
async def test_hold_deferred_false_writes_from_the_next_source(engine: AsyncEngine, lab) -> None:
    """``hold_deferred=False``: the same reads write all three voices, ``ter`` from B («source down → the next one»)."""
    print_section("refresh_assets: hold_deferred=False")
    _, _, b, asset_id = await _three_voices(engine, lab, "HN")

    result = _result(await _refresh(engine, [asset_id], now=NOW, hold_deferred=False), asset_id)

    assert sorted(result.written) == ["description", "fund_size", "ter"], result
    assert _value_and_source(await _rows(engine, asset_id, "ter")) == [(normalize("ter", "0.0031"), b.code)]
    print_success("the next source wins")


@pytest.mark.asyncio
async def test_hold_deferred_reads_the_voices_declared_for_the_asset_type(engine: AsyncEngine, lab) -> None:
    """A refused enricher declares ``ter`` for STOCK only, ``description`` for ETF: on an ETF, B's ``ter`` is written
    (A does not declare it for that type), B's ``description`` is held."""
    print_section("refresh_assets: hold_deferred reads plugin.voices[asset_type]")
    i_a, i_b = _ident("TA"), _ident("TB")
    a = lab("type_a", table={i_a: _rate()}, voices={AssetType.ETF: frozenset({"description"}), AssetType.STOCK: frozenset({"ter"})})
    b = lab("type_b", table={i_b: {"ter": "0.0031", "description": "from b"}}, voices={AssetType.ETF: frozenset({"ter", "description"})})
    asset_id, _ = await _asset(engine, "type")
    await _bind(engine, asset_id, {a.code: _binding(i_a), b.code: _binding(i_b)})

    result = _result(await _refresh(engine, [asset_id], now=NOW, hold_deferred=True), asset_id)

    assert result.written == ["ter"], result
    assert _value_and_source(await _rows(engine, asset_id, "ter")) == [(normalize("ter", "0.0031"), b.code)]
    assert await _rows(engine, asset_id, "description") == []
    print_success("the asset's type decides")


@pytest.mark.asyncio
async def test_hold_deferred_with_nothing_refused_writes_everything(engine: AsyncEngine, lab) -> None:
    """``hold_deferred=True`` and no refusal: the merge is written whole, as without it."""
    print_section("refresh_assets: hold_deferred=True, nothing refused")
    i_a, i_b = _ident("FA"), _ident("FB")
    a = lab("free_a", table={i_a: {"description": "from a"}}, voices={AssetType.ETF: frozenset({"description", "ter"})})
    b = lab("free_b", table={i_b: {"ter": "0.0031"}}, voices={AssetType.ETF: frozenset({"ter"})})
    asset_id, _ = await _asset(engine, "free")
    await _bind(engine, asset_id, {a.code: _binding(i_a), b.code: _binding(i_b)})

    result = _result(await _refresh(engine, [asset_id], now=NOW, hold_deferred=True), asset_id)

    assert sorted(result.written) == ["description", "ter"] and result.deferred == [], result
    print_success("nothing held")


@pytest.mark.asyncio
async def test_read_since_takes_the_skipped_bindings_values_from_the_cache(engine: AsyncEngine, lab) -> None:
    """Round one (``hold_deferred=True``): B first is refused, A after it gives ``ter``: held. Round two
    (``read_since`` the round's start, ``hold_deferred=False``), B refused again: A is skipped (not called) and its
    cached ``ter`` is written — one row, A's."""
    print_section("refresh_assets: read_since with the skipped binding's value from the cache")
    i_b, i_a = _ident("CB"), _ident("CA")
    b = lab("cache_b", table={i_b: _rate()}, voices={AssetType.ETF: frozenset({"ter"})})
    a = lab("cache_a", table={i_a: {"ter": "0.0022"}}, voices={AssetType.ETF: frozenset({"ter"})})
    asset_id, _ = await _asset(engine, "cache")
    await _bind(engine, asset_id, {b.code: _binding(i_b), a.code: _binding(i_a)})
    round_start = datetime.now(UTC)
    first = _result(await _refresh(engine, [asset_id], hold_deferred=True), asset_id)
    assert first.written == [] and await _rows(engine, asset_id, "ter") == [], f"barrier: round one held ter: {first}"
    a_calls = a.reads_of(i_a)

    second = _result(await _refresh(engine, [asset_id], read_since=round_start, hold_deferred=False), asset_id)

    assert a.reads_of(i_a) == a_calls and b.reads_of(i_b) == 2, f"A skipped, B read again: {a.calls} / {b.calls}"
    assert second.written == ["ter"], second
    assert _value_and_source(await _rows(engine, asset_id, "ter")) == [(normalize("ter", "0.0022"), a.code)]
    print_success("the cached value joins the merge")


# =============================================================================
# 6. THE DEFAULT WAIT (lot B6c)
# =============================================================================

#: The wait of a round whose refusals give none: the contract's number, not the module constant's name.
DEFAULT_WAIT = timedelta(minutes=15)


def _assert_retry_in(value: Any, before: datetime, after: datetime, pause: timedelta, what: str) -> None:
    """``value`` is an aware instant within [before, after] + ``pause``: bracketed by the clock around the run."""
    moment = _utc(value, what)
    assert before + pause <= moment <= after + pause, f"{what}: now + {pause} expected, got {moment.isoformat()} (run between {before.isoformat()} and {after.isoformat()})"


async def _refused_round(job_env: AsyncEngine, lab, tag: str, waits: Sequence[float | None]) -> tuple[SchedulerState, datetime, datetime]:
    """One regular round on one asset per wait, each refused by one enricher with that ``retry_after`` (None: no wait).
    Barrier: every refusal reached the job as such — the asset's state says ``RATE_LIMITED`` with that very wait, and
    the round counts each asset deferred."""
    identifiers = [_ident(f"{tag}{index}") for index in range(len(waits))]
    refuser = lab(f"default_{tag.lower()}", table={identifier: _rate(wait) for identifier, wait in zip(identifiers, waits, strict=True)})
    assets = []
    for identifier in identifiers:
        asset_id, _ = await _asset(job_env, f"default {tag}")
        await _bind(job_env, asset_id, {refuser.code: _binding(identifier)})
        assets.append(asset_id)
    state = SchedulerState()

    before, after = await _run_round(state)

    for asset_id, wait in zip(assets, waits, strict=True):
        read = (await _state(job_env, asset_id)).get(refuser.code, {})
        assert (read.get("error_code"), read.get("retry_after")) == (RATE_LIMITED, wait), f"barrier: the refusal of asset {asset_id} reached the job with retry_after {wait}: {read}"
    assert (state.profile_read.last_status, *_counts(state)) == ("partial", 0, 0, len(waits)), f"barrier: every asset deferred: {state.profile_read}"
    return state, before, after


@pytest.mark.asyncio
@pytest.mark.parametrize("waits", [pytest.param((None,), id="one-refusal-without-a-wait"), pytest.param((None, None), id="two-refusals-without-a-wait")])
async def test_a_refusal_without_a_wait_retries_after_the_default_15_minutes(job_env: AsyncEngine, lab, waits: tuple[None, ...]) -> None:
    """B6c: no deferred read carries a ``retry_after`` (the real enrichers refuse so): ``retry_at`` is now + 15 minutes,
    in the state and in the entry — not None, which would leave the held voices waiting a week."""
    print_section("profile_read: a refusal without a wait → the default 15 minutes")
    state, before, after = await _refused_round(job_env, lab, f"DW{len(waits)}", waits)

    _assert_retry_in(state.profile_read.retry_at, before, after, DEFAULT_WAIT, "state.profile_read.retry_at")
    (entry,) = _entries()
    _assert_retry_in(entry.get("retry_at"), before, after, DEFAULT_WAIT, "the entry's retry_at")
    print_success("retry in 15 minutes")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("waits", "pause"),
    [
        pytest.param((3600.0,), timedelta(seconds=3600), id="a-known-wait-longer-than-the-default"),
        pytest.param((3600.0, None), timedelta(seconds=3600), id="mixed-the-known-wait-longer-than-the-default"),
        pytest.param((240.0, None), timedelta(seconds=240), id="mixed-the-known-wait-shorter-than-the-default"),
    ],
)
async def test_a_plugin_given_wait_still_wins_over_the_default(job_env: AsyncEngine, lab, waits: tuple[float | None, ...], pause: timedelta) -> None:
    """B6c, green by design: a plugin-given ``retry_after`` wins. Alone at 3600 s it gives 3600 s (the default is not a
    cap); beside a refusal without a wait, the shortest KNOWN wait decides, 3600 s or 240 s (the default joins no
    minimum and does not replace a known wait)."""
    print_section("profile_read: a known wait wins over the default")
    state, before, after = await _refused_round(job_env, lab, f"KW{len(waits)}{int(pause.total_seconds())}", waits)

    _assert_retry_in(state.profile_read.retry_at, before, after, pause, "state.profile_read.retry_at")
    (entry,) = _entries()
    _assert_retry_in(entry.get("retry_at"), before, after, pause, "the entry's retry_at")
    print_success("the known wait")


@pytest.mark.asyncio
async def test_errors_without_a_refusal_set_no_retry(job_env: AsyncEngine, lab) -> None:
    """B6c, green by design: an error that is not a refusal defers nothing, so no default wait — ``retry_at`` stays None.
    (Nothing read wrong at all: ``test_only_the_active_assets_with_enrichers_are_read``.)"""
    print_section("profile_read: errors alone set no retry")
    i_ok, i_err = _ident("EOK"), _ident("EER")
    a = lab("errors_only", table={i_ok: {"ter": "0.0022"}, i_err: ERROR})
    ok, _ = await _asset(job_env, "errors ok")
    broken, _ = await _asset(job_env, "errors err")
    await _bind(job_env, ok, {a.code: _binding(i_ok)})
    await _bind(job_env, broken, {a.code: _binding(i_err)})
    state = SchedulerState()

    await _run_round(state)

    assert (state.profile_read.last_status, *_counts(state)) == ("partial", 1, 1, 0), f"barrier: one ok, one error, nothing deferred: {state.profile_read}"
    assert state.profile_read.retry_at is None and _entries()[0].get("retry_at") is None, state.profile_read
    print_success("no retry without a refusal")


@pytest.mark.asyncio
async def test_round_two_refused_again_without_a_wait_sets_no_third_round_and_writes_from_the_second(job_env: AsyncEngine, lab) -> None:
    """B6c with B6's cap: A, first, refuses without a wait in both rounds. Round one holds ``ter`` and retries in 15
    minutes; round two (A refused again, no wait) sets no third round — ``retry_at`` None in the state and the entry,
    no default — keeps the round's start, and writes ``ter`` from B, from its round-one read (B not called again)."""
    print_section("profile_read: refused again without a wait → no third round")
    i_a, i_b = _ident("NWA"), _ident("NWB")
    a = lab("nowait_first", table={i_a: _rate(None)}, voices={AssetType.ETF: frozenset({"ter", "description"})})
    b = lab("nowait_second", table={i_b: {"ter": "0.0031", "fund_size": FUND_SIZE}}, voices={AssetType.ETF: frozenset({"ter", "fund_size"})})
    asset_id, _ = await _asset(job_env, "nowait")
    await _bind(job_env, asset_id, {a.code: _binding(i_a), b.code: _binding(i_b)})
    state = SchedulerState()

    before, after = await _run_round(state)

    assert (await _state(job_env, asset_id)).get(a.code, {}).get("retry_after", "<missing>") is None, "barrier: A refused without a wait"
    assert await _rows(job_env, asset_id, "ter") == [], "barrier: round one held the voice"
    _assert_retry_in(state.profile_read.retry_at, before, after, DEFAULT_WAIT, "round one's retry_at")
    round_one = state.profile_read
    b_calls, a_calls = b.reads_of(i_b), a.reads_of(i_a)
    _retry_has_come(state)

    await _run_round(state)

    assert a.reads_of(i_a) == a_calls + 1 and b.reads_of(i_b) == b_calls, f"round two reads A again, not B: {a.calls} / {b.calls}"
    job = state.profile_read
    assert (job.retry_at, job.last_items_deferred, job.round_started_at) == (None, 1, round_one.round_started_at), f"one retry only, the round kept: {job}"
    assert _entries()[0].get("retry_at") is None, _entries()[0]
    assert _value_and_source(await _rows(job_env, asset_id, "ter")) == [(normalize("ter", "0.0031"), b.code)], "source down → the next one, in the second round"
    print_success("no third round; written from the second")


def test_the_shared_retry_at_gives_no_default() -> None:
    """B6c, green by design — barrier on the shared function: ``jobs._retry_at`` still answers None for deferred items
    without a wait (and for none), so the price jobs keep no retry without a pause; the default lives in
    ``run_profile_read`` only. Job-level pin: ``test_scheduler_jobs.py::
    test_current_price_refresh_with_no_pause_known_leaves_no_retry_at``."""
    from types import SimpleNamespace  # noqa: PLC0415 — test-local

    print_section("jobs._retry_at: no default")
    refused = SimpleNamespace(error_code=RATE_LIMITED, retry_after=None)
    assert jobs._retry_at([], NOW) is None
    assert jobs._retry_at([refused, refused], NOW) is None
    print_success("the price jobs unchanged")
