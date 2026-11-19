"""Reading the profile from the enrichers, and merging it (project 68, lot B5a): ``services/enrichers/refresh.py``.

Under test, as its module docstring and dataclasses state the contract:

1. **Read** (``read_bindings``). The requests are grouped by enricher: one ``read`` call per enricher, with its bindings
   in the order of the requests, the binding's free keys as ``params``. The enrichers run at once (two held on
   ``threading.Event``, released B then A: B's outcome comes out first); an enricher's outcomes come out as it yields
   them. A binding the plugin never answers (fewer items, an index out of the list, an index given twice, a raise
   mid-way) comes out exactly once, as ``error``. A ``RATE_LIMITED`` item comes out with its ``error_code`` and
   ``retry_after``.
2. **Filter.** ``ok`` values come out in their stored form (``catalogue.normalize_value``); a voice the catalogue
   refuses (``ter: "-1"``), an unknown voice and a ``None`` are dropped and logged, the plugin's other voices kept.
3. **Cache** (``enricher_read``, ``READ_CACHE_TTL`` 1800 s). The key is the enricher and the whole binding, parameters
   included: a second read within the TTL does not call the plugin (``from_cache``), other parameters do. ``ok`` and
   ``not_found`` are kept, ``error`` and ``RATE_LIMITED`` never. An entry read for some voices never answers a request
   for more (all, or a wider set); one read for all answers any subset. ``use_cache=False`` always calls.
4. **Merge** (``merge_voices``). Voice by voice the first enricher of ``order`` whose ``ok`` outcome gave it wins, with
   its ``source_date``; an enricher down (``error``, ``not_found``) leaves everything to the next one; ``others`` holds
   the other enrichers' values; an enricher not in ``order`` is ignored; the order of the outcomes does not matter.
5. **Ask** (``ask_profile``). Reads the bindings (from the cache when it can), merges them in the order of ``config``;
   ``keys`` restricts the voices. It takes no session: it cannot write.
6. **Refresh** (``refresh_assets``). For each asset, its bindings from ``asset_enrichers.config``: the merged voices
   through the store (``source`` the winning enricher, its ``source_date``, ``user_id`` NULL, ``read_on`` the store's
   today), «different from now» (a second refresh with the same values writes no row), and the ``state`` of every
   enricher read (``read_at`` UTC, ``status``, ``error_code``, ``retry_after``, ``voices``). An asset whose plugin fails
   does not stop the others; an asset that does not exist answers ``error``; a code not installed is skipped; a
   ``RATE_LIMITED`` outcome is listed in ``deferred``; ``read_since`` skips the bindings read ``ok``/``not_found`` at
   or after it; the ``config`` is read again when writing (a binding removed in flight writes nothing, a new order
   decides the merge); an inactive asset is read too. Rows and state are read back from another session: proof that
   each asset was committed.
7. **A3 rule (16/11).** A plugin giving one voice in a wrong format: its other voices are written, that one is logged.
8. **Per-voice dates (correction C1b-1).** ``EnricherReadItem`` gains ``source_dates`` (voice → date, empty by default):
   the date of a voice that has one of its own; a voice not in it takes the item's ``source_date``. ``ReadOutcome``
   keeps it (also from the cache); ``merge_voices`` gives each ``MergedVoice`` the date of its own voice from the
   winning enricher (``source_dates.get(key, source_date)``), so ``ask_profile``'s voices and the rows of
   ``refresh_assets`` carry it. The store's rule is unchanged: a second read with the same value and only another
   per-voice date writes no row. Items with ``source_dates`` are built in the test body, never inside a lab's ``read``:
   before C1b the constructor refuses the field there, with its name, instead of in a worker thread where the core
   would turn it into ``NO_ANSWER``.

The synthetic enrichers are classes registered on ``EnricherRegistry`` under ``lab_refresh_*`` codes (removed with their
claims at teardown). The core resolves them by code and builds a new instance each time, so what a lab answers and the
calls it records live in closures, under a lock (the calls come from worker threads). A lab answers from a table,
identifier → values (filtered to the ``keys`` it is given) or an outcome; a script replaces the table where the test
needs a malformed answer. Every identifier is unique to its test and the ``enricher_read`` cache is cleared before and
after each test: the cache is process-wide.

Every call is bounded by ``DEADLINE``, against a hang, never a wait. Held plugins wait on their own event with a bound,
and every event is set in ``finally`` and at teardown.

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``).

Not pinned: whether ``read_bindings`` trims an outcome's values to ``keys`` (only ``ask`` is pinned to restrict them);
which of two items with the same index wins (the test yields identical ones); two requests with the same enricher and
binding in one read; whether ``state.voices`` counts the voices given or written (asserted only where both agree, one
enricher on a first refresh); whether ``read_at`` equals ``now`` (only that it is UTC); whether ``refresh`` reads from
the cache (the cache is cleared between two refreshes that count calls); the ``state`` of a binding removed in flight;
whether an asset without bindings answers ``error``; the TTL running out (no clock tests).

Not pinned (C1b-1): ``source_value`` still answering the item-level date (the task does not name it); whether the core
drops a per-voice date of a voice the catalogue refused or the plugin did not give.

Red until B5a: every function of ``refresh.py`` raises ``NotImplementedError``; each test fails at its first call, never
at collection. Two guards are green already: ``READ_CACHE_TTL`` and the signature of ``ask_profile`` (no session).
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import inspect
import json
import re
import threading
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType
from backend.app.logging_config import get_logger
from backend.app.services.assets.profile import freshness, store
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.enrichers import bindings, refresh
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherReadStatus, EnricherRecognition, EnricherTerms
from backend.app.services.enrichers.refresh import AskResult, AssetRefreshResult, MergedVoice, ReadOutcome, ReadRequest, ask_profile, merge_voices, read_bindings, refresh_assets
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.app.utils.runtime.cache import clear_cache
from backend.test_scripts.test_utils import print_section, print_success

SETTINGS_FAMILY = "enricher"
LAB_PREFIX = "lab_refresh_"
LAB_CLASS_PREFIX = "LabRefreshEnricher_"
CACHE_NAME = "enricher_read"
#: The bound on every read, refresh and hold: against a hang, never a wait.
DEADLINE = 15.0
LAB_DATE = date(2026, 10, 31)
OTHER_DATE = date(2026, 9, 30)
NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
LOG_CANARY = "lab_refresh_log_canary"

#: Every voice a lab may legitimately yield, declared for ETF (registration refuses a voice outside the catalogue).
LAB_VOICES = frozenset({"ter", "fund_size", "description", "geography", "distribution_policy", "replication"})
RAW_GEOGRAPHY = {"USA": "0.6", "JPN": "0.4"}
FUND_SIZE = {"amount": "1000", "currency": "EUR"}

#: The outcomes a lab's table can give instead of values.
NOT_FOUND = "not_found"
ERROR = "error"
RATE = "rate_limited"
RAISE = "raise"
LAB_ERROR_CODE = "LAB_ERROR"
RETRY_AFTER = 30.0

Script = Callable[[list[EnricherBinding], frozenset[str] | None], Iterator[EnricherReadItem]]


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


def _ident(tag: str) -> str:
    """An identifier no other test (and no other run within the cache's TTL) uses."""
    return f"LRF{tag}{uuid.uuid4().hex[:10].upper()}"


def _binding(identifier: str, identifier_type: str = "ISIN", **params: Any) -> EnricherBinding:
    return EnricherBinding(identifier_type=identifier_type, identifier=identifier, params=params)


def _config_entry(binding: EnricherBinding) -> dict[str, Any]:
    """A binding as ``asset_enrichers.config`` stores it: the two fields and the plugin's free keys."""
    return {"identifier_type": binding.identifier_type, "identifier": binding.identifier, **dict(binding.params)}


def _same_binding(left: EnricherBinding, right: EnricherBinding) -> bool:
    return (left.identifier_type, left.identifier, dict(left.params)) == (right.identifier_type, right.identifier, dict(right.params))


@dataclass
class Lab:
    """A registered synthetic enricher: its code, its answers, and every ``read`` call as (bindings, keys)."""

    code: str
    table: dict[str, Any]
    calls: list[tuple[tuple[EnricherBinding, ...], frozenset[str] | None]] = field(default_factory=list)
    started: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)

    def identifiers_read(self) -> list[str]:
        return [binding.identifier for bindings_read, _ in self.calls for binding in bindings_read]


def _table_script(table: Mapping[str, Any], source_date: date | None) -> Script:
    """Answer each binding from ``table`` by its identifier: values (filtered to ``keys``) or one of the outcomes."""

    def script(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:
        for index, binding in enumerate(bindings_read):
            spec = table[binding.identifier]
            if spec == RAISE:
                raise RuntimeError(f"lab source down at {binding.identifier}")
            if spec == NOT_FOUND:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
            elif spec == ERROR:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=LAB_ERROR_CODE, error_message="the lab fails on purpose")
            elif spec == RATE:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=RETRY_AFTER)
            else:
                values = dict(spec) if keys is None else {key: value for key, value in spec.items() if key in keys}
                yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_date=source_date)

    return script


class _LabMethods(EnricherPlugin):
    """The abstract methods but ``read``: a synthetic enricher differs by its declarations and its answers."""

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        return EnricherRecognition(found=True, name=f"Lab {binding.identifier}")

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://lab.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []


@pytest.fixture(autouse=True)
def _fresh_read_cache() -> Iterator[None]:
    """The read cache is process-wide: empty before and after each test (its return value is not asserted, the cache
    may not exist yet)."""
    clear_cache(CACHE_NAME)
    yield
    clear_cache(CACHE_NAME)


@pytest.fixture
def lab() -> Iterator[Callable[..., Lab]]:
    """``lab(name, table=…, script=…, hold=…, source_date=…)`` registers a synthetic enricher covering ETF (degree 10)
    and gives back its ``Lab``. ``hold``: every ``read`` waits on the lab's ``release`` event (bounded) after setting
    ``started``. Removed from the registry, with its claims, at teardown; every event is set first."""
    labs: list[Lab] = []

    def register(name: str, *, table: dict[str, Any] | None = None, script: Script | None = None, hold: bool = False, source_date: date | None = LAB_DATE) -> Lab:
        code = f"{LAB_PREFIX}{name}"
        handle = Lab(code=code, table={} if table is None else table)
        lock = threading.Lock()
        answer = script if script is not None else _table_script(handle.table, source_date)

        def read(self, bindings_read, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the contract's signature
            received = None if keys is None else frozenset(keys)
            with lock:
                handle.calls.append((tuple(bindings_read), received))
            handle.started.set()
            if hold and not handle.release.wait(DEADLINE):
                raise TimeoutError(f"lab {code} was never released")
            yield from answer(list(bindings_read), received)

        attributes: dict[str, Any] = {
            "code": code,
            "name": f"Lab refresh {name} (testing)",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": ("ISIN", "LEI", "TICKER"),
            "default_priority": {asset_type: (10 if asset_type == AssetType.ETF else None) for asset_type in AssetType},
            "voices": {AssetType.ETF: LAB_VOICES},
            "read": read,
        }
        labs.append(handle)
        EnricherRegistry.register(type(f"{LAB_CLASS_PREFIX}{name}", (_LabMethods,), attributes))
        assert isinstance(EnricherRegistry.get_plugin_instance(code), EnricherPlugin), f"barrier: {code} is not served after its registration"
        return handle

    yield register
    for handle in labs:
        handle.started.set()
        handle.release.set()
    storage = EnricherRegistry._get_storage()
    for handle in labs:
        stored = storage.get(handle.code)
        if stored is not None and getattr(stored, "__name__", "").startswith(LAB_CLASS_PREFIX):
            storage.pop(handle.code, None)
        release_env_variables(SETTINGS_FAMILY, handle.code)


async def _read(requests: Sequence[ReadRequest], keys: Any = None, *, use_cache: bool = True) -> list[ReadOutcome]:
    """Every outcome of ``read_bindings``, consumed to its end under ``DEADLINE``."""

    async def consume() -> list[ReadOutcome]:
        return [outcome async for outcome in read_bindings(requests, keys, use_cache=use_cache)]

    outcomes = await asyncio.wait_for(consume(), DEADLINE)
    assert all(isinstance(outcome, ReadOutcome) for outcome in outcomes), f"only ReadOutcome: {outcomes}"
    return outcomes


def _of(outcomes: Sequence[ReadOutcome], code: str, identifier: str) -> list[ReadOutcome]:
    return [outcome for outcome in outcomes if outcome.code == code and outcome.binding.identifier == identifier]


def _one(outcomes: Sequence[ReadOutcome], code: str, identifier: str) -> ReadOutcome:
    found = _of(outcomes, code, identifier)
    assert len(found) == 1, f"exactly one outcome for {code} / {identifier}: {outcomes}"
    return found[0]


@contextlib.contextmanager
def _captured_refresh_log() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged under the refresh module's logger name must
    be among them."""
    with capture_logs() as events:
        get_logger(refresh.__name__).debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the refresh module's log does not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _logged_together(events: list[dict[str, Any]], *parts: str) -> list[dict[str, Any]]:
    """The captured events (the canary left out) whose text names every one of ``parts`` as a whole word (``ter`` is not
    found inside ``filter``)."""
    patterns = [re.compile(rf"(?<![A-Za-z0-9_]){re.escape(part)}(?![A-Za-z0-9_])") for part in parts]
    return [event for event in events if event.get("event") != LOG_CANARY and all(pattern.search(str(event)) for pattern in patterns)]


# --- the private database -----------------------------------------------------


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'enricher_refresh.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def _no_timezone_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The store's today follows ``scheduler_timezone``; a deployment variable must not move it under the test."""
    monkeypatch.delenv("LIBREFOLIO_DEFAULT_TIMEZONE", raising=False)


async def _asset(engine: AsyncEngine, tag: str, *, active: bool = True) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=f"Lab refresh {tag} {uuid.uuid4().hex[:8]}", currency="EUR", asset_type=AssetType.ETF, active=active)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _bind(engine: AsyncEngine, asset_id: int, config: Mapping[str, EnricherBinding]) -> None:
    async with AsyncSession(engine) as session:
        await bindings.save_config(session, asset_id, {code: _config_entry(binding) for code, binding in config.items()})
        await session.commit()


async def _refresh(engine: AsyncEngine, asset_ids: Sequence[int], **kwargs: Any) -> list[AssetRefreshResult]:
    async def run() -> list[AssetRefreshResult]:
        async with AsyncSession(engine) as session:
            return await refresh_assets(session, asset_ids, **kwargs)

    results = await asyncio.wait_for(run(), DEADLINE)
    assert all(isinstance(result, AssetRefreshResult) for result in results), f"only AssetRefreshResult: {results}"
    return results


def _result(results: Sequence[AssetRefreshResult], asset_id: int) -> AssetRefreshResult:
    found = [result for result in results if result.asset_id == asset_id]
    assert len(found) == 1, f"one result for asset {asset_id}: {results}"
    return found[0]


async def _rows(engine: AsyncEngine, asset_id: int) -> list[AssetProfileUpdate]:
    """The asset's profile rows, read from a session of their own (what was committed), in the store's order."""
    async with AsyncSession(engine) as session:
        statement = select(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == asset_id).order_by(AssetProfileUpdate.read_on, AssetProfileUpdate.id)
        return list((await session.execute(statement)).scalars().all())


def _row_summary(rows: Sequence[AssetProfileUpdate]) -> dict[str, tuple[Any, str, int | None, date | None]]:
    """The last row of each voice as (stored value, source, user_id, source_date)."""
    summary: dict[str, tuple[Any, str, int | None, date | None]] = {}
    for row in rows:
        stored = None if row.value is None else normalize_value(row.key, json.loads(row.value))
        summary[row.key] = (stored, row.source, row.user_id, row.source_date)
    return summary


async def _state(engine: AsyncEngine, asset_id: int) -> dict[str, dict[str, Any]]:
    async with AsyncSession(engine) as session:
        row = (await bindings.load_enrichers(session, [asset_id])).get(asset_id)
    return {} if row is None else row.state


async def _today(engine: AsyncEngine) -> date:
    async with AsyncSession(engine) as session:
        return await store.profile_today(session, NOW)


def _read_at(entry: Mapping[str, Any]) -> datetime:
    """The ``read_at`` of a state entry, which must be a UTC ISO date-time."""
    value = entry.get("read_at")
    assert isinstance(value, str), f"read_at is an ISO text: {entry}"
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0), f"read_at is in UTC: {value}"
    return parsed


# =============================================================================
# 1. read_bindings: grouping, order of arrival, unanswered bindings
# =============================================================================


@pytest.mark.asyncio
async def test_one_read_call_per_enricher_with_its_bindings_in_request_order(lab) -> None:
    print_section("read_bindings: grouped by enricher")
    b1, b2, b3, c1 = _ident("G1"), _ident("G2"), _ident("G3"), _ident("GC")
    a = lab("group_a", table={b1: {"ter": "0.001"}, b2: {"ter": "0.002"}, b3: {"ter": "0.003"}})
    c = lab("group_c", table={c1: {"description": "lab c"}})
    requests = [
        ReadRequest(owner=1, code=a.code, binding=_binding(b1)),
        ReadRequest(owner=2, code=c.code, binding=_binding(c1)),
        ReadRequest(owner=2, code=a.code, binding=_binding(b2)),
        ReadRequest(owner="draft", code=a.code, binding=_binding(b3)),
    ]

    outcomes = await _read(requests)

    assert [[binding.identifier for binding in call] for call, _ in a.calls] == [[b1, b2, b3]], f"one call for A with its three bindings in order: {a.calls}"
    assert [[binding.identifier for binding in call] for call, _ in c.calls] == [[c1]], f"one call for C: {c.calls}"
    assert len(outcomes) == len(requests), f"one outcome per request: {outcomes}"
    for request in requests:
        outcome = _one(outcomes, request.code, request.binding.identifier)
        assert outcome.owner == request.owner and _same_binding(outcome.binding, request.binding), f"the outcome carries its request's owner and binding: {outcome}"
        assert outcome.status == EnricherReadStatus.OK and outcome.from_cache is False and outcome.source_date == LAB_DATE, f"read now, ok: {outcome}"
    print_success("one call per enricher; one outcome per request")


@pytest.mark.asyncio
async def test_an_enrichers_outcomes_come_out_as_it_yields_them(lab) -> None:
    identifiers = [_ident("Y0"), _ident("Y1"), _ident("Y2")]

    def backwards(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the script's signature
        for index in (2, 0, 1):
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values={"description": f"item {index}"}, source_date=LAB_DATE)

    a = lab("yield_order", script=backwards)

    outcomes = await _read([ReadRequest(owner=index, code=a.code, binding=_binding(identifier)) for index, identifier in enumerate(identifiers)])

    assert [outcome.binding.identifier for outcome in outcomes] == [identifiers[2], identifiers[0], identifiers[1]], f"as yielded: 2, 0, 1: {outcomes}"
    assert [outcome.values for outcome in outcomes] == [{"description": "item 2"}, {"description": "item 0"}, {"description": "item 1"}], f"each item to its binding: {outcomes}"


@pytest.mark.asyncio
async def test_enrichers_run_at_once_and_outcomes_come_out_as_they_complete(lab) -> None:
    """A and B, each held inside ``read`` on its own event; A requested first. Both are called at once; B is released
    first and its outcome comes out first, then A's."""
    print_section("read_bindings: order of arrival")
    ia, ib = _ident("ARA"), _ident("ARB")
    a = lab("arrival_a", table={ia: {"description": "lab a"}}, hold=True)
    b = lab("arrival_b", table={ib: {"description": "lab b"}}, hold=True)
    stream = read_bindings([ReadRequest(owner=1, code=a.code, binding=_binding(ia)), ReadRequest(owner=1, code=b.code, binding=_binding(ib))])
    first = asyncio.ensure_future(anext(stream))
    both = asyncio.ensure_future(asyncio.to_thread(lambda: a.started.wait(DEADLINE) and b.started.wait(DEADLINE)))
    try:
        await asyncio.wait({first, both}, timeout=DEADLINE, return_when=asyncio.FIRST_COMPLETED)
        if first.done():
            raise AssertionError(f"an outcome came out before any enricher was released: {first.result()}")  # .result() raises the read's own failure
        assert await asyncio.wait_for(both, DEADLINE), f"A and B must be called at once, each in its own worker thread: A {a.started.is_set()}, B {b.started.is_set()}"

        b.release.set()
        early = await asyncio.wait_for(first, DEADLINE)
        assert isinstance(early, ReadOutcome) and early.code == b.code and early.status == EnricherReadStatus.OK, f"B, released first, comes out first: {early}"

        a.release.set()
        late = await asyncio.wait_for(anext(stream), DEADLINE)
        assert isinstance(late, ReadOutcome) and late.code == a.code and late.status == EnricherReadStatus.OK, f"then A: {late}"
        rest = await asyncio.wait_for(_drain(stream), DEADLINE)
        assert rest == [], f"no other outcome: {rest}"
    finally:
        for event in (a.started, b.started, a.release, b.release):
            event.set()
        for task in (first, both):
            if not task.done():
                task.cancel()
        await asyncio.gather(first, both, return_exceptions=True)
        await stream.aclose()
    print_success("B came out first")


async def _drain(stream: Any) -> list[ReadOutcome]:
    return [outcome async for outcome in stream]


@pytest.mark.asyncio
async def test_bindings_a_plugin_never_answers_come_out_once_as_errors(lab) -> None:
    """The plugin answers only the first of three bindings: the two others come out once each, as errors."""
    identifiers = [_ident("F0"), _ident("F1"), _ident("F2")]

    def first_only(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the script's signature
        yield EnricherReadItem(index=0, status=EnricherReadStatus.OK, values={"description": "only the first"}, source_date=LAB_DATE)

    a = lab("fewer", script=first_only)

    outcomes = await _read([ReadRequest(owner=index, code=a.code, binding=_binding(identifier)) for index, identifier in enumerate(identifiers)])

    assert len(outcomes) == 3, f"one outcome per binding, nothing pending: {outcomes}"
    assert _one(outcomes, a.code, identifiers[0]).status == EnricherReadStatus.OK, outcomes
    assert [_one(outcomes, a.code, identifier).status for identifier in identifiers[1:]] == [EnricherReadStatus.ERROR, EnricherReadStatus.ERROR], f"the unanswered ones are errors: {outcomes}"


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", ["out_of_range", "twice"])
async def test_an_index_out_of_the_list_or_given_twice_answers_no_binding(lab, malformed) -> None:
    """Two bindings; the plugin answers index 0 and, instead of index 1, an index out of the list or index 0 again (an
    identical item). Each binding comes out exactly once: the first ok, the second an error."""
    identifiers = [_ident("M0"), _ident("M1")]
    item = EnricherReadItem(index=0, status=EnricherReadStatus.OK, values={"description": "index 0"}, source_date=LAB_DATE)

    def script(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the script's signature
        if malformed == "out_of_range":
            yield EnricherReadItem(index=7, status=EnricherReadStatus.OK, values={"description": "nobody's"}, source_date=LAB_DATE)
        yield item
        if malformed == "twice":
            yield item

    a = lab(f"malformed_{malformed}", script=script)

    outcomes = await _read([ReadRequest(owner=index, code=a.code, binding=_binding(identifier)) for index, identifier in enumerate(identifiers)])

    assert len(outcomes) == 2, f"exactly one outcome per binding: {outcomes}"
    assert _one(outcomes, a.code, identifiers[0]).status == EnricherReadStatus.OK, outcomes
    assert _one(outcomes, a.code, identifiers[1]).status == EnricherReadStatus.ERROR, f"the binding never answered is an error: {outcomes}"


@pytest.mark.asyncio
async def test_a_plugin_that_raises_mid_way_leaves_errors_and_the_others_still_answer(lab) -> None:
    ok_first, broken_at, never = _ident("R0"), _ident("R1"), _ident("R2")
    healthy_identifier = _ident("RH")
    a = lab("raises", table={ok_first: {"description": "before the raise"}, broken_at: RAISE, never: {"description": "never reached"}})
    healthy = lab("raises_healthy", table={healthy_identifier: {"description": "healthy"}})

    outcomes = await _read([ReadRequest(owner=index, code=a.code, binding=_binding(identifier)) for index, identifier in enumerate((ok_first, broken_at, never))] + [ReadRequest(owner=9, code=healthy.code, binding=_binding(healthy_identifier))])

    assert len(outcomes) == 4, f"one outcome per request: {outcomes}"
    assert _one(outcomes, a.code, ok_first).status == EnricherReadStatus.OK, f"what came before the raise stays: {outcomes}"
    assert [_one(outcomes, a.code, identifier).status for identifier in (broken_at, never)] == [EnricherReadStatus.ERROR, EnricherReadStatus.ERROR], f"the rest are errors: {outcomes}"
    assert _one(outcomes, healthy.code, healthy_identifier).status == EnricherReadStatus.OK, f"the other enricher still answers: {outcomes}"


@pytest.mark.asyncio
async def test_a_rate_limited_item_comes_out_with_its_code_and_retry_after(lab) -> None:
    identifier = _ident("RL")
    a = lab("rate", table={identifier: RATE})

    outcomes = await _read([ReadRequest(owner=1, code=a.code, binding=_binding(identifier))])

    outcome = _one(outcomes, a.code, identifier)
    assert outcome.status == EnricherReadStatus.ERROR and outcome.error_code == RATE_LIMITED and outcome.retry_after == RETRY_AFTER, f"a refusal for too many requests: {outcome}"


# =============================================================================
# 2. The catalogue filter
# =============================================================================


@pytest.mark.asyncio
async def test_values_come_out_in_stored_form_and_refused_unknown_or_none_voices_are_dropped_and_logged(lab) -> None:
    print_section("read_bindings: the catalogue filter")
    identifier = _ident("CF")
    a = lab("filter", table={identifier: {"geography": RAW_GEOGRAPHY, "ter": "-1", "not_a_voice": "x", "description": None, "distribution_policy": "accumulating"}})

    with _captured_refresh_log() as events:
        outcomes = await _read([ReadRequest(owner=1, code=a.code, binding=_binding(identifier))])

    outcome = _one(outcomes, a.code, identifier)
    assert outcome.status == EnricherReadStatus.OK, f"the plugin's other voices go on: {outcome}"
    assert dict(outcome.values) == {"geography": normalize_value("geography", RAW_GEOGRAPHY), "distribution_policy": "accumulating"}, f"stored form, the refused, the unknown and the None dropped: {outcome.values}"
    for dropped in ("ter", "not_a_voice", "description"):
        assert _logged_together(events, dropped, a.code), f"the dropped voice {dropped} is logged with the enricher's code: {events}"
    print_success("stored form; three voices dropped and logged")


# =============================================================================
# 3. The cache
# =============================================================================


def test_the_read_cache_lives_thirty_minutes() -> None:
    assert refresh.READ_CACHE_TTL == 1800


def test_ask_takes_no_session() -> None:
    """``ask`` writes nothing: it is not even given a session."""
    assert list(inspect.signature(ask_profile).parameters) == ["asset_type", "config", "keys"]


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", [pytest.param({"ter": "0.0022"}, id="ok"), pytest.param(NOT_FOUND, id="not_found")])
async def test_an_ok_or_not_found_read_is_answered_from_the_cache_the_second_time(lab, spec) -> None:
    identifier = _ident("CK")
    a = lab(f"cache_{'ok' if isinstance(spec, dict) else 'nf'}", table={identifier: spec})
    request = ReadRequest(owner=1, code=a.code, binding=_binding(identifier))

    first = _one(await _read([request]), a.code, identifier)
    second = _one(await _read([request]), a.code, identifier)

    assert len(a.calls) == 1, f"the second read within the TTL does not call the plugin: {a.calls}"
    assert first.from_cache is False and second.from_cache is True, f"from_cache: {first} / {second}"
    assert (second.status, dict(second.values), second.source_date) == (first.status, dict(first.values), first.source_date), f"the same outcome: {first} / {second}"


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", [ERROR, RATE])
async def test_an_error_or_a_refusal_is_never_cached(lab, spec) -> None:
    identifier = _ident("CE")
    a = lab(f"cache_{spec}", table={identifier: spec})
    request = ReadRequest(owner=1, code=a.code, binding=_binding(identifier))

    first = _one(await _read([request]), a.code, identifier)
    second = _one(await _read([request]), a.code, identifier)

    assert first.status == EnricherReadStatus.ERROR, f"barrier: the lab fails: {first}"
    assert len(a.calls) == 2 and second.from_cache is False, f"an {spec} is read again: {a.calls} / {second}"


@pytest.mark.asyncio
async def test_other_parameters_are_another_cache_key_and_reach_the_plugin(lab) -> None:
    identifier = _ident("CP")
    a = lab("cache_params", table={identifier: {"description": "same identifier"}})

    await _read([ReadRequest(owner=1, code=a.code, binding=_binding(identifier, mic="MTA"))])
    second = _one(await _read([ReadRequest(owner=1, code=a.code, binding=_binding(identifier, mic="ETFPLUS"))]), a.code, identifier)

    assert [dict(call[0].params) for call, _ in a.calls] == [{"mic": "MTA"}, {"mic": "ETFPLUS"}], f"called again for other parameters, which reach the plugin: {a.calls}"
    assert second.from_cache is False, second


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_keys", "second_keys", "calls"),
    [
        pytest.param({"ter"}, None, 2, id="ter-then-all"),
        pytest.param({"ter"}, {"ter", "fund_size"}, 2, id="ter-then-wider"),
        pytest.param(None, {"ter"}, 1, id="all-then-ter"),
    ],
)
async def test_a_partial_read_never_answers_a_request_for_more(lab, first_keys, second_keys, calls) -> None:
    identifier = _ident("CV")
    a = lab(f"cache_keys_{len(first_keys or ())}_{len(second_keys or ())}", table={identifier: {"ter": "0.0022", "fund_size": FUND_SIZE, "description": "all"}})
    request = ReadRequest(owner=1, code=a.code, binding=_binding(identifier))

    await _read([request], first_keys)
    second = _one(await _read([request], second_keys), a.code, identifier)

    assert len(a.calls) == calls, f"keys {first_keys} then {second_keys}: {calls} plugin call(s): {a.calls}"
    assert a.calls[0][1] == (None if first_keys is None else frozenset(first_keys)), f"the plugin is asked the voices asked: {a.calls}"
    if calls == 1:
        assert second.from_cache is True and "ter" in second.values, f"a read of every voice answers a subset: {second}"
    else:
        assert second.from_cache is False and a.calls[1][1] == (None if second_keys is None else frozenset(second_keys)), f"read again for more voices: {a.calls}"


@pytest.mark.asyncio
async def test_use_cache_false_always_calls_the_plugin(lab) -> None:
    identifier = _ident("CN")
    a = lab("cache_off", table={identifier: {"description": "fresh"}})
    request = ReadRequest(owner=1, code=a.code, binding=_binding(identifier))

    await _read([request])
    assert len(a.calls) == 1, "barrier: the first read calls the plugin"
    second = _one(await _read([request], use_cache=False), a.code, identifier)

    assert len(a.calls) == 2 and second.from_cache is False, f"use_cache=False calls the plugin: {a.calls} / {second}"


@pytest.mark.asyncio
async def test_only_the_bindings_not_cached_reach_the_plugin(lab) -> None:
    cached, fresh = _ident("CC"), _ident("CF")
    a = lab("cache_mixed", table={cached: {"description": "cached"}, fresh: {"description": "fresh"}})
    await _read([ReadRequest(owner=1, code=a.code, binding=_binding(cached))])

    outcomes = await _read([ReadRequest(owner=1, code=a.code, binding=_binding(cached)), ReadRequest(owner=2, code=a.code, binding=_binding(fresh))])

    assert [[binding.identifier for binding in call] for call, _ in a.calls] == [[cached], [fresh]], f"the second call holds only the binding not cached: {a.calls}"
    assert _one(outcomes, a.code, cached).from_cache is True and _one(outcomes, a.code, fresh).from_cache is False, outcomes


# =============================================================================
# 4. merge_voices
# =============================================================================


def _outcome(code: str, status: EnricherReadStatus = EnricherReadStatus.OK, values: Mapping[str, Any] | None = None, source_date: date | None = LAB_DATE) -> ReadOutcome:
    return ReadOutcome(owner=1, code=code, binding=_binding(f"MERGE{code.upper()}"), status=status, values=dict(values or {}), source_date=source_date)


def test_merge_takes_each_voice_from_the_first_enricher_of_the_order_that_gave_it() -> None:
    """``first`` gives ter and description, ``second`` ter and fund_size (another day): ter and description are the
    first's, fund_size the second's with its own day; ``others`` holds the second's ter. The outcomes are given in the
    opposite order: only ``order`` counts."""
    print_section("merge_voices")
    first = _outcome("first", values={"ter": "0.0022", "description": "first"}, source_date=LAB_DATE)
    second = _outcome("second", values={"ter": "0.0031", "fund_size": FUND_SIZE}, source_date=OTHER_DATE)

    merged = merge_voices(["first", "second"], [second, first])

    assert set(merged) == {"ter", "description", "fund_size"}, merged
    assert all(isinstance(voice, MergedVoice) for voice in merged.values()), merged
    assert (merged["ter"].value, merged["ter"].source, merged["ter"].source_date) == ("0.0022", "first", LAB_DATE), merged["ter"]
    assert dict(merged["ter"].others) == {"second": "0.0031"}, f"the other enricher's ter: {merged['ter']}"
    assert (merged["fund_size"].value, merged["fund_size"].source, merged["fund_size"].source_date) == (FUND_SIZE, "second", OTHER_DATE), f"a voice the first does not give comes from the second, with its day: {merged['fund_size']}"
    assert dict(merged["description"].others) == {} and dict(merged["fund_size"].others) == {}, "a voice one enricher gives has no others"
    print_success("first of the order per voice; others kept")


@pytest.mark.parametrize("status", [EnricherReadStatus.ERROR, EnricherReadStatus.NOT_FOUND])
def test_merge_an_enricher_down_leaves_every_voice_to_the_next(status) -> None:
    down = _outcome("down", status=status, values={}, source_date=None)
    second = _outcome("second", values={"ter": "0.0031", "description": "second"}, source_date=OTHER_DATE)

    merged = merge_voices(["down", "second"], [down, second])

    assert {key: (voice.value, voice.source, voice.source_date) for key, voice in merged.items()} == {"ter": ("0.0031", "second", OTHER_DATE), "description": ("second", "second", OTHER_DATE)}, merged
    assert all("down" not in voice.others for voice in merged.values()), merged


def test_merge_ignores_an_enricher_not_in_the_order() -> None:
    first = _outcome("first", values={"ter": "0.0022"})
    stranger = _outcome("stranger", values={"ter": "0.0099", "description": "only the stranger"})

    merged = merge_voices(["first"], [stranger, first])

    assert set(merged) == {"ter"}, f"a voice only an enricher outside the order gives is not merged: {merged}"
    assert merged["ter"].source == "first" and "stranger" not in merged["ter"].others, f"nor kept among the others: {merged['ter']}"


# =============================================================================
# 5. ask_profile
# =============================================================================


@pytest.mark.asyncio
async def test_ask_reads_the_config_and_merges_it_in_its_order_reusing_the_cache(lab) -> None:
    print_section("ask_profile")
    ia, ib = _ident("AA"), _ident("AB")
    a = lab("ask_a", table={ia: {"ter": "0.0022", "description": "lab a"}}, source_date=LAB_DATE)
    b = lab("ask_b", table={ib: {"ter": "0.0031", "fund_size": FUND_SIZE}}, source_date=OTHER_DATE)
    config = {a.code: _config_entry(_binding(ia, mic="MTA")), b.code: _config_entry(_binding(ib))}

    result = await asyncio.wait_for(ask_profile(AssetType.ETF, config), DEADLINE)

    assert isinstance(result, AskResult), result
    assert (result.voices["ter"].value, result.voices["ter"].source, result.voices["ter"].source_date) == ("0.0022", a.code, LAB_DATE), result.voices
    assert dict(result.voices["ter"].others) == {b.code: "0.0031"}, result.voices["ter"]
    assert result.voices["fund_size"].source == b.code and result.voices["description"].source == a.code, result.voices
    assert sorted((outcome.code, outcome.status) for outcome in result.outcomes) == sorted([(a.code, EnricherReadStatus.OK), (b.code, EnricherReadStatus.OK)]), result.outcomes
    assert dict(a.calls[0][0][0].params) == {"mic": "MTA"}, f"the binding's free keys reach the plugin as params: {a.calls}"

    swapped = await asyncio.wait_for(ask_profile(AssetType.ETF, {b.code: config[b.code], a.code: config[a.code]}), DEADLINE)

    assert swapped.voices["ter"].source == b.code and dict(swapped.voices["ter"].others) == {a.code: "0.0022"}, f"the order of config decides: {swapped.voices}"
    assert len(a.calls) == 1 and len(b.calls) == 1 and all(outcome.from_cache for outcome in swapped.outcomes), f"the second ask is answered from the cache: {a.calls} {b.calls} {swapped.outcomes}"
    print_success("config order merged; the second ask from the cache")


@pytest.mark.asyncio
async def test_ask_with_keys_restricts_the_voices(lab) -> None:
    identifier = _ident("AK")
    a = lab("ask_keys", table={identifier: {"ter": "0.0022", "description": "lab", "fund_size": FUND_SIZE}})

    result = await asyncio.wait_for(ask_profile(AssetType.ETF, {a.code: _config_entry(_binding(identifier))}, {"ter"}), DEADLINE)

    assert set(result.voices) == {"ter"} and result.voices["ter"].value == "0.0022", f"only the voices asked: {result.voices}"
    assert a.calls[0][1] == frozenset({"ter"}), f"the plugin is asked the voices asked: {a.calls}"


# =============================================================================
# 6. refresh_assets
# =============================================================================


@pytest.mark.asyncio
async def test_refresh_writes_the_merged_voices_and_the_state(engine: AsyncEngine, lab) -> None:
    """One enricher, one asset: its voices written as source rows (the enricher, its day, no user, the store's today),
    the state of the read, and the binding's free keys given to the plugin."""
    print_section("refresh_assets: write")
    identifier = _ident("W1")
    a = lab("write", table={identifier: {"ter": "0.0022", "geography": RAW_GEOGRAPHY}})
    asset_id = await _asset(engine, "write")
    await _bind(engine, asset_id, {a.code: _binding(identifier, mic="MTA")})

    results = await _refresh(engine, [asset_id], now=NOW)

    result = _result(results, asset_id)
    assert result.error is None and sorted(result.written) == ["geography", "ter"], f"both voices written: {result}"
    assert [(outcome.code, outcome.status) for outcome in result.outcomes] == [(a.code, EnricherReadStatus.OK)] and result.deferred == [], result
    assert dict(a.calls[0][0][0].params) == {"mic": "MTA"}, f"the config's free keys reach the plugin: {a.calls}"
    rows = await _rows(engine, asset_id)
    assert _row_summary(rows) == {"ter": ("0.0022", a.code, None, LAB_DATE), "geography": (normalize_value("geography", RAW_GEOGRAPHY), a.code, None, LAB_DATE)}, f"source rows, committed: {_row_summary(rows)}"
    assert {row.read_on for row in rows} == {await _today(engine)}, f"read_on is the store's today: {[row.read_on for row in rows]}"
    entry = (await _state(engine, asset_id)).get(a.code)
    assert entry is not None, f"the state of the enricher read: {await _state(engine, asset_id)}"
    assert {"read_at", "status", "error_code", "retry_after", "voices"} <= set(entry), f"the state's fields: {entry}"
    _read_at(entry)
    assert (entry["status"], entry["error_code"], entry["retry_after"], entry["voices"]) == ("ok", None, None, 2), f"ok, two voices: {entry}"
    print_success("rows and state written")


@pytest.mark.asyncio
async def test_refresh_merges_in_the_config_order(engine: AsyncEngine, lab) -> None:
    ia, ib = _ident("WA"), _ident("WB")
    a = lab("merge_a", table={ia: {"ter": "0.0022", "description": "lab a"}}, source_date=LAB_DATE)
    b = lab("merge_b", table={ib: {"ter": "0.0031", "fund_size": FUND_SIZE}}, source_date=OTHER_DATE)
    asset_id = await _asset(engine, "merge")
    await _bind(engine, asset_id, {b.code: _binding(ib), a.code: _binding(ia)})

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert sorted(result.written) == ["description", "fund_size", "ter"], result
    assert _row_summary(await _rows(engine, asset_id)) == {
        "ter": ("0.0031", b.code, None, OTHER_DATE),
        "fund_size": (FUND_SIZE, b.code, None, OTHER_DATE),
        "description": ("lab a", a.code, None, LAB_DATE),
    }, "B first in config: its ter wins; A gives what B does not"
    state = await _state(engine, asset_id)
    assert {code: state.get(code, {}).get("status") for code in (a.code, b.code)} == {a.code: "ok", b.code: "ok"}, state


@pytest.mark.asyncio
async def test_a_second_refresh_with_the_same_values_writes_nothing(engine: AsyncEngine, lab) -> None:
    identifier = _ident("W2")
    a = lab("twice", table={identifier: {"ter": "0.0022", "description": "same"}})
    asset_id = await _asset(engine, "twice")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    first = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)
    assert sorted(first.written) == ["description", "ter"], f"barrier: the first refresh writes: {first}"
    before = [row.id for row in await _rows(engine, asset_id)]
    clear_cache(CACHE_NAME)

    second = _result(await _refresh(engine, [asset_id], now=NOW + timedelta(hours=1)), asset_id)

    assert second.written == [], f"«different from now»: nothing changed, nothing written: {second}"
    assert [row.id for row in await _rows(engine, asset_id)] == before, "no new row"
    assert (await _state(engine, asset_id)).get(a.code, {}).get("status") == "ok", "the state is written again"


@pytest.mark.asyncio
async def test_an_asset_whose_plugin_fails_does_not_stop_the_others(engine: AsyncEngine, lab) -> None:
    broken_identifier, good_identifier = _ident("XB"), _ident("XG")
    broken = lab("fail_broken", table={broken_identifier: RAISE})
    good = lab("fail_good", table={good_identifier: {"ter": "0.0022"}})
    failing = await _asset(engine, "failing")
    healthy = await _asset(engine, "healthy")
    await _bind(engine, failing, {broken.code: _binding(broken_identifier)})
    await _bind(engine, healthy, {good.code: _binding(good_identifier)})

    results = await _refresh(engine, [failing, healthy], now=NOW)

    assert _result(results, failing).written == [] and await _rows(engine, failing) == [], "the failing asset writes no value"
    assert (await _state(engine, failing)).get(broken.code, {}).get("status") == "error", f"its state says error: {await _state(engine, failing)}"
    assert _result(results, healthy).written == ["ter"], f"the other asset is written: {results}"
    assert _row_summary(await _rows(engine, healthy)) == {"ter": ("0.0022", good.code, None, LAB_DATE)}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("spec", "status", "error_code", "retry_after"),
    [
        pytest.param(NOT_FOUND, "not_found", None, None, id="not_found"),
        pytest.param(ERROR, "error", LAB_ERROR_CODE, None, id="error"),
        pytest.param(RATE, "error", RATE_LIMITED, RETRY_AFTER, id="rate_limited"),
    ],
)
async def test_the_state_records_each_outcome_and_a_refusal_is_deferred(engine: AsyncEngine, lab, spec, status, error_code, retry_after) -> None:
    identifier = _ident("ST")
    a = lab(f"state_{spec}", table={identifier: spec})
    asset_id = await _asset(engine, f"state {spec}")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert result.written == [] and await _rows(engine, asset_id) == [], f"nothing to write: {result}"
    entry = (await _state(engine, asset_id)).get(a.code)
    assert entry is not None, "the state of the enricher read"
    _read_at(entry)
    assert (entry["status"], entry["error_code"], entry["retry_after"]) == (status, error_code, retry_after), entry
    deferred = [(outcome.code, outcome.error_code) for outcome in result.deferred]
    assert deferred == ([(a.code, RATE_LIMITED)] if spec == RATE else []), f"only a refusal for too many requests is deferred: {result.deferred}"


@pytest.mark.asyncio
async def test_an_asset_that_does_not_exist_answers_an_error_and_the_others_go_on(engine: AsyncEngine, lab) -> None:
    identifier = _ident("NE")
    a = lab("missing_other", table={identifier: {"ter": "0.0022"}})
    asset_id = await _asset(engine, "beside missing")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    missing = asset_id + 100_000

    results = await _refresh(engine, [missing, asset_id], now=NOW)

    gone = _result(results, missing)
    assert gone.error and gone.written == [] and gone.outcomes == [], f"an asset that does not exist answers error: {gone}"
    assert await _rows(engine, missing) == [] and await _state(engine, missing) == {}, "nothing written for it"
    assert _result(results, asset_id).written == ["ter"], f"the other asset is written: {results}"


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [pytest.param(None, id="no-row"), pytest.param({}, id="empty-config")])
async def test_an_asset_without_bindings_reads_and_writes_nothing(engine: AsyncEngine, config) -> None:
    asset_id = await _asset(engine, "unbound")
    if config is not None:
        await _bind(engine, asset_id, config)

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert result.written == [] and result.outcomes == [] and result.deferred == [], f"nothing read: {result}"
    assert await _rows(engine, asset_id) == [] and await _state(engine, asset_id) == {}, "nothing written"


@pytest.mark.asyncio
async def test_a_binding_whose_enricher_is_not_installed_is_skipped(engine: AsyncEngine, lab) -> None:
    identifier = _ident("NI")
    a = lab("installed", table={identifier: {"ter": "0.0022"}})
    absent = f"{LAB_PREFIX}not_installed"
    assert EnricherRegistry.get_plugin(absent) is None, f"barrier: {absent} is not installed"
    asset_id = await _asset(engine, "not installed")
    await _bind(engine, asset_id, {absent: _binding(_ident("NX")), a.code: _binding(identifier)})

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert [outcome.code for outcome in result.outcomes] == [a.code] and result.written == ["ter"], f"only the installed enricher is read: {result}"
    assert set(await _state(engine, asset_id)) == {a.code}, f"no state for the enricher not installed: {await _state(engine, asset_id)}"


@pytest.mark.asyncio
async def test_read_since_skips_the_bindings_read_ok_or_not_found_since_then(engine: AsyncEngine, lab) -> None:
    """Three enrichers on one asset: ok, not_found, error. A second refresh with ``read_since`` at their read reads only
    the one in error; with ``read_since`` after it, all three."""
    print_section("refresh_assets: read_since")
    i_ok, i_nf, i_err = _ident("SO"), _ident("SN"), _ident("SE")
    ok = lab("since_ok", table={i_ok: {"ter": "0.0022"}})
    nf = lab("since_nf", table={i_nf: NOT_FOUND})
    err = lab("since_err", table={i_err: ERROR})
    asset_id = await _asset(engine, "since")
    await _bind(engine, asset_id, {ok.code: _binding(i_ok), nf.code: _binding(i_nf), err.code: _binding(i_err)})
    await _refresh(engine, [asset_id], now=NOW)
    state = await _state(engine, asset_id)
    assert {code: state.get(code, {}).get("status") for code in (ok.code, nf.code, err.code)} == {ok.code: "ok", nf.code: "not_found", err.code: "error"}, f"barrier: the first refresh wrote the three states: {state}"
    read_ats = [_read_at(state[code]) for code in (ok.code, nf.code, err.code)]
    calls = {lab_.code: len(lab_.calls) for lab_ in (ok, nf, err)}
    clear_cache(CACHE_NAME)

    await _refresh(engine, [asset_id], now=NOW, read_since=min(read_ats))

    assert {lab_.code: len(lab_.calls) - calls[lab_.code] for lab_ in (ok, nf, err)} == {ok.code: 0, nf.code: 0, err.code: 1}, f"ok and not_found read since then are skipped, the error is read again: {[lab_.calls for lab_ in (ok, nf, err)]}"
    calls = {lab_.code: len(lab_.calls) for lab_ in (ok, nf, err)}
    clear_cache(CACHE_NAME)

    await _refresh(engine, [asset_id], now=NOW, read_since=max(read_ats) + timedelta(seconds=1))

    assert {lab_.code: len(lab_.calls) - calls[lab_.code] for lab_ in (ok, nf, err)} == {ok.code: 1, nf.code: 1, err.code: 1}, f"read before read_since: all read again: {[lab_.calls for lab_ in (ok, nf, err)]}"
    print_success("read_since skips what was read since")


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["removed", "reordered"])
async def test_the_config_is_read_again_when_writing(engine: AsyncEngine, lab, change) -> None:
    """A (first in config) is held inside ``read``; meanwhile another session saves a config without A, or with B
    first, and commits. Released, the refresh writes nothing from A when it was removed, and follows the new order when
    it was reordered: ter is B's either way."""
    print_section(f"refresh_assets: config {change} in flight")
    ia, ib = _ident("HA"), _ident("HB")
    a = lab(f"flight_a_{change}", table={ia: {"ter": "0.0022", "description": "lab a"}}, hold=True)
    b = lab(f"flight_b_{change}", table={ib: {"ter": "0.0031"}})
    asset_id = await _asset(engine, f"flight {change}")
    await _bind(engine, asset_id, {a.code: _binding(ia), b.code: _binding(ib)})
    task = asyncio.ensure_future(_refresh(engine, [asset_id], now=NOW))
    started = asyncio.ensure_future(asyncio.to_thread(a.started.wait, DEADLINE))
    try:
        await asyncio.wait({task, started}, timeout=DEADLINE, return_when=asyncio.FIRST_COMPLETED)
        if task.done():
            raise AssertionError(f"the refresh ended before A was released: {task.result()}")  # .result() raises the refresh's own failure
        assert await asyncio.wait_for(started, DEADLINE), "barrier: A is being read"
        new_config = {b.code: _binding(ib)} if change == "removed" else {b.code: _binding(ib), a.code: _binding(ia)}
        await asyncio.wait_for(_bind(engine, asset_id, new_config), DEADLINE)  # a write lock held during the read fails here, never hangs
        a.release.set()
        results = await asyncio.wait_for(task, DEADLINE)
    finally:
        a.started.set()
        a.release.set()
        for pending in (task, started):
            if not pending.done():
                pending.cancel()
        await asyncio.gather(task, started, return_exceptions=True)

    summary = _row_summary(await _rows(engine, asset_id))
    assert summary.get("ter") == ("0.0031", b.code, None, LAB_DATE), f"ter follows the config of now: {summary}"
    if change == "removed":
        assert all(row.source != a.code for row in await _rows(engine, asset_id)), f"a binding removed in flight writes nothing: {summary}"
        assert "description" not in summary, summary
    else:
        assert summary.get("description") == ("lab a", a.code, None, LAB_DATE), f"A, still bound, gives what B does not: {summary}"
    assert isinstance(_result(results, asset_id), AssetRefreshResult)


@pytest.mark.asyncio
async def test_an_inactive_asset_is_refreshed_too(engine: AsyncEngine, lab) -> None:
    identifier = _ident("IN")
    a = lab("inactive", table={identifier: {"ter": "0.0022"}})
    asset_id = await _asset(engine, "inactive", active=False)
    await _bind(engine, asset_id, {a.code: _binding(identifier)})

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert result.written == ["ter"] and _row_summary(await _rows(engine, asset_id)) == {"ter": ("0.0022", a.code, None, LAB_DATE)}, f"a manual refresh reads an inactive asset: {result}"


# =============================================================================
# 7. A3 rule (16/11): one voice in a wrong format
# =============================================================================


@pytest.mark.asyncio
async def test_one_voice_in_a_wrong_format_is_logged_and_the_others_are_written(engine: AsyncEngine, lab) -> None:
    print_section("refresh_assets: one wrong voice (A3 rule)")
    identifier = _ident("A3")
    a = lab("wrong_voice", table={identifier: {"ter": "-1", "description": "kept", "distribution_policy": "accumulating"}})
    asset_id = await _asset(engine, "wrong voice")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})

    with _captured_refresh_log() as events:
        result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert sorted(result.written) == ["description", "distribution_policy"], f"the other voices are written: {result}"
    assert _row_summary(await _rows(engine, asset_id)) == {"description": ("kept", a.code, None, LAB_DATE), "distribution_policy": ("accumulating", a.code, None, LAB_DATE)}, "no ter row"
    assert _logged_together(events, "ter", a.code), f"the refused voice is logged with the enricher's code: {events}"
    print_success("wrong voice logged, the others written")


# =============================================================================
# 8. Per-voice dates (correction C1b-1)
# =============================================================================

#: A voice's own date, and a second one for the same voice on a later read.
VOICE_DATE = date(2026, 9, 1)
LATER_VOICE_DATE = date(2026, 10, 15)


def _dated_item(values: Mapping[str, Any], *, source_dates: Mapping[str, date], source_date: date | None = None) -> EnricherReadItem:
    """An ``ok`` item with per-voice dates (its ``index`` is set when yielded). Called in the test body: before C1b
    ``EnricherReadItem`` has no ``source_dates`` and the test fails here, naming it."""
    return EnricherReadItem(index=0, status=EnricherReadStatus.OK, values=dict(values), source_date=source_date, source_dates=dict(source_dates))


def _items_script(items: Mapping[str, EnricherReadItem]) -> Script:
    """Answer each binding with the prebuilt item of its identifier, at its index (``items`` is read at call time: a
    test may swap an item between two reads)."""

    def script(bindings_read: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:  # noqa: ARG001 — the script's signature
        for index, binding in enumerate(bindings_read):
            yield dataclasses.replace(items[binding.identifier], index=index)

    return script


def _dated_outcome(code: str, values: Mapping[str, Any], *, source_dates: Mapping[str, date], source_date: date | None = None) -> ReadOutcome:
    return ReadOutcome(owner=1, code=code, binding=_binding(f"MERGE{code.upper()}"), status=EnricherReadStatus.OK, values=dict(values), source_date=source_date, source_dates=dict(source_dates))


def test_source_dates_is_empty_by_default() -> None:
    print_section("per-voice dates (C1b-1)")
    item = EnricherReadItem(index=0, status=EnricherReadStatus.OK)
    assert dict(getattr(item, "source_dates", {"<no field>": None})) == {}, "EnricherReadItem.source_dates: empty by default"
    outcome = ReadOutcome(owner=1, code="x", binding=_binding("DEFAULTS"), status=EnricherReadStatus.OK)
    assert dict(getattr(outcome, "source_dates", {"<no field>": None})) == {}, "ReadOutcome.source_dates: empty by default"


@pytest.mark.parametrize("item_date", [None, LAB_DATE], ids=["no-item-date", "item-date"])
def test_merge_gives_each_voice_its_own_date_else_the_items(item_date) -> None:
    """``ter`` dated on its own: it carries that date; ``description`` and ``fund_size`` carry the item's date (None or
    E)."""
    outcome = _dated_outcome("first", {"ter": "0.0022", "description": "first", "fund_size": FUND_SIZE}, source_dates={"ter": VOICE_DATE}, source_date=item_date)

    merged = merge_voices(["first"], [outcome])

    assert {key: voice.source_date for key, voice in merged.items()} == {"ter": VOICE_DATE, "description": item_date, "fund_size": item_date}, merged


def test_merge_takes_the_date_of_the_winning_enrichers_voice() -> None:
    """``first`` wins ter with no per-voice date (its item date); ``second`` loses ter (its ter date is not used) and
    wins fund_size with fund_size's own date."""
    first = _dated_outcome("first", {"ter": "0.0022"}, source_dates={}, source_date=LAB_DATE)
    second = _dated_outcome("second", {"ter": "0.0031", "fund_size": FUND_SIZE}, source_dates={"ter": VOICE_DATE, "fund_size": LATER_VOICE_DATE}, source_date=OTHER_DATE)

    merged = merge_voices(["first", "second"], [second, first])

    assert (merged["ter"].source, merged["ter"].source_date) == ("first", LAB_DATE), f"the winner's date, never the loser's per-voice one: {merged['ter']}"
    assert (merged["fund_size"].source, merged["fund_size"].source_date) == ("second", LATER_VOICE_DATE), merged["fund_size"]


@pytest.mark.asyncio
async def test_read_carries_the_per_voice_dates_and_the_cache_keeps_them(lab) -> None:
    identifier = _ident("PD")
    item = _dated_item({"ter": "0.0022", "description": "dated"}, source_dates={"ter": VOICE_DATE}, source_date=LAB_DATE)
    a = lab("per_voice_read", script=_items_script({identifier: item}))
    request = ReadRequest(owner=1, code=a.code, binding=_binding(identifier))

    first = _one(await _read([request]), a.code, identifier)
    second = _one(await _read([request]), a.code, identifier)

    assert first.status == EnricherReadStatus.OK and first.from_cache is False, f"barrier: read now, ok: {first}"
    assert dict(getattr(first, "source_dates", {})) == {"ter": VOICE_DATE} and first.source_date == LAB_DATE, f"the outcome keeps the per-voice dates: {first}"
    assert second.from_cache is True and len(a.calls) == 1, f"barrier: the second read is the cache's: {second}"
    assert dict(getattr(second, "source_dates", {})) == {"ter": VOICE_DATE}, f"the cache keeps them: {second}"


@pytest.mark.asyncio
async def test_ask_answers_each_voice_with_its_own_date(lab) -> None:
    identifier = _ident("PA")
    item = _dated_item({"ter": "0.0022", "description": "dated"}, source_dates={"ter": VOICE_DATE})
    a = lab("per_voice_ask", script=_items_script({identifier: item}))

    result = await asyncio.wait_for(ask_profile(AssetType.ETF, {a.code: _config_entry(_binding(identifier))}), DEADLINE)

    assert {key: voice.source_date for key, voice in result.voices.items()} == {"ter": VOICE_DATE, "description": None}, result.voices


@pytest.mark.asyncio
async def test_refresh_writes_each_row_with_its_voices_date(engine: AsyncEngine, lab) -> None:
    identifier = _ident("PW")
    item = _dated_item({"ter": "0.0022", "description": "dated"}, source_dates={"ter": VOICE_DATE}, source_date=LAB_DATE)
    a = lab("per_voice_write", script=_items_script({identifier: item}))
    asset_id = await _asset(engine, "per voice write")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})

    result = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert sorted(result.written) == ["description", "ter"], result
    assert _row_summary(await _rows(engine, asset_id)) == {"ter": ("0.0022", a.code, None, VOICE_DATE), "description": ("dated", a.code, None, LAB_DATE)}


@pytest.mark.asyncio
async def test_a_new_per_voice_date_alone_writes_no_row(engine: AsyncEngine, lab) -> None:
    """The store's rule kept: a second refresh with the same values, ``ter`` now dated another day, writes nothing; the
    row keeps its first date."""
    identifier = _ident("PS")
    items = {identifier: _dated_item({"ter": "0.0022", "description": "same"}, source_dates={"ter": VOICE_DATE})}
    a = lab("per_voice_same", script=_items_script(items))
    asset_id = await _asset(engine, "per voice same")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    first = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)
    assert sorted(first.written) == ["description", "ter"], f"barrier: the first refresh writes: {first}"
    before = [row.id for row in await _rows(engine, asset_id)]
    dates = {key: summary[3] for key, summary in _row_summary(await _rows(engine, asset_id)).items()}
    assert dates == {"ter": VOICE_DATE, "description": None}, f"barrier: ter written with its own date, description with the item's (None): {dates}"
    items[identifier] = _dated_item({"ter": "0.0022", "description": "same"}, source_dates={"ter": LATER_VOICE_DATE})
    clear_cache(CACHE_NAME)

    second = _result(await _refresh(engine, [asset_id], now=NOW + timedelta(hours=1)), asset_id)

    assert len(a.calls) == 2, f"barrier: the second refresh read the plugin again: {a.calls}"
    assert second.written == [], f"only the per-voice date changed: no row: {second}"
    assert [row.id for row in await _rows(engine, asset_id)] == before, "no new row"
    assert _row_summary(await _rows(engine, asset_id))["ter"][3] == VOICE_DATE, "the row keeps its first date"
    print_success("per-voice dates merged, cached, written; no row for a date alone")


# =============================================================================
# 9. Confirmations (lot D1d): when each source last gave each voice
# =============================================================================


@pytest.mark.asyncio
async def test_an_ok_read_confirms_each_voice_it_gave_at_its_read(engine: AsyncEngine, lab) -> None:
    """``state[code]["confirmed"]``: voice → the moment of the read that gave it; ``voices`` stays the count."""
    identifier = _ident("C1")
    a = lab("confirm", table={identifier: {"ter": "0.0022", "fund_size": FUND_SIZE}})
    asset_id = await _asset(engine, "confirm")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})

    await _refresh(engine, [asset_id], now=NOW)

    entry = (await _state(engine, asset_id))[a.code]
    assert entry["voices"] == 2, f"voices stays the count: {entry}"
    assert {key: datetime.fromisoformat(moment) for key, moment in entry.get("confirmed", {}).items()} == {"ter": NOW, "fund_size": NOW}, f"each voice given, at the read: {entry}"


@pytest.mark.asyncio
async def test_the_same_answer_every_week_writes_no_row_and_stays_fresh(engine: AsyncEngine, lab) -> None:
    """Forty days ago and now the source gives the same fund size: one row, opened forty days ago, confirmed now."""
    identifier = _ident("C2")
    a = lab("confirm_weekly", table={identifier: {"fund_size": FUND_SIZE}})
    asset_id = await _asset(engine, "confirm weekly")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    first = _result(await _refresh(engine, [asset_id], now=NOW - timedelta(days=40)), asset_id)
    assert first.written == ["fund_size"], f"barrier: the first read writes: {first}"
    clear_cache(CACHE_NAME)

    second = _result(await _refresh(engine, [asset_id], now=NOW), asset_id)

    assert second.written == [] and len(await _rows(engine, asset_id)) == 1, f"the same value writes no row: {second}"
    async with AsyncSession(engine) as session:
        today = await store.profile_today(session, NOW)
        opened = await store.profile_today(session, NOW - timedelta(days=40))
        result = (await freshness.voice_freshness(session, [asset_id], today=today)).get(asset_id, {})
    assert result.get("fund_size") == freshness.VoiceFreshness(confirmed_on=today, stale=False, opened_on=opened), f"opened forty days ago, confirmed now, not stale: {result}"


@pytest.mark.asyncio
async def test_a_failed_read_keeps_the_last_confirmation(engine: AsyncEngine, lab) -> None:
    """Read ok ten days ago, then an error: the state says the error, the confirmation of ten days ago stays."""
    identifier = _ident("C3")
    a = lab("confirm_then_error", table={identifier: {"fund_size": FUND_SIZE}})
    asset_id = await _asset(engine, "confirm then error")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    await _refresh(engine, [asset_id], now=NOW - timedelta(days=10))
    a.table[identifier] = ERROR
    clear_cache(CACHE_NAME)

    await _refresh(engine, [asset_id], now=NOW)

    entry = (await _state(engine, asset_id))[a.code]
    assert entry["status"] == "error", f"barrier: the second read failed: {entry}"
    assert datetime.fromisoformat(entry.get("confirmed", {}).get("fund_size", "1970-01-01T00:00:00+00:00")) == NOW - timedelta(days=10), f"the last confirmation stays: {entry}"


@pytest.mark.asyncio
async def test_a_read_of_some_voices_keeps_the_others_confirmation(engine: AsyncEngine, lab) -> None:
    identifier = _ident("C4")
    a = lab("confirm_partial", table={identifier: {"ter": "0.0022", "fund_size": FUND_SIZE}})
    asset_id = await _asset(engine, "confirm partial")
    await _bind(engine, asset_id, {a.code: _binding(identifier)})
    await _refresh(engine, [asset_id], now=NOW - timedelta(days=10))
    clear_cache(CACHE_NAME)

    await _refresh(engine, [asset_id], now=NOW, keys={"ter"})

    confirmed = {key: datetime.fromisoformat(moment) for key, moment in (await _state(engine, asset_id))[a.code].get("confirmed", {}).items()}
    assert confirmed == {"ter": NOW, "fund_size": NOW - timedelta(days=10)}, f"ter confirmed now, fund_size kept: {confirmed}"
