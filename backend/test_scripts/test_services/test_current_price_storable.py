"""X-R40 + W-B62 (workstream X, the lot of 17/10): the current (live) price and the price refresh serve, cache and announce
only what the database can keep.

W-B62 (17/10, the follow-up of W-B58): the current price serves only what the database can keep. Measured before the
cure (``price_query.get_current_prices_bulk``): the provider's quote is stored in the current-value cache before anything
checks it, and served as it comes — a finite but huge Decimal such as ``1E+50000000`` passes pydantic, and
``SafeDecimal`` writes it in full (``format(v, "f")``, about 50 MB a response), from the cache for 2 minutes; W-B58 kept
it out of the database only. A history refresh announces in ``changed_points`` every incoming date, the one W-B58 skips
included. The database fallback reads the latest row whatever its close, and a close that reads ``None`` (a REAL inf)
makes ``Decimal(str(None))`` raise: the whole bulk call fails. The cure's contract:

* a quote no price column keeps (``storable_price`` is None: ``1E+50000000``, ``1E+60``, ``1E-13``, which truncates to
  0) is never served and never cached: the item falls back to the database as after a provider failure — the stored
  close of the latest row, ``source`` ``db:last_known``, or ``error`` set and no value when nothing is stored — and a
  second call asks the provider again. «Not cached» is recorded (every value the cache is given), never timed;
* a valid quote is served as the database keeps it (12 decimals, then 15 significant digits, ``ROUND_DOWN``):
  65432.1234567890999 is served 65432.123456789, the close of the persisted row, on the first call and from the cache;
* a refresh leaves out of ``changed_points`` a date whose value no column keeps (a close of 1E+60, a volume of 1E+25);
  the other dates are there;
* the database fallback answers the most recent row whose close reads a number (a latest close of +inf is passed
  over), or ``error`` set and no value when there is none; nothing raises;
* guards: a quote of 101.5 is served and cached as before; a normal latest row is the fallback as before.

The current-price and refresh tests drive ``_QuoteDouble``, which counts its calls; the database-fallback tests run with
no provider and with one that fails (``_falling_back``), their rows seeded by the ORM, the unreadable close then written
by raw SQL (``9e999``, a REAL +inf).

X-R40 (17/10, merged with W-B62 into this lot): the refusal is logged once, and the refresh caches only what the database
keeps. Measured before the cure: the current-price persist (W-B58) warns about a quote it skips at every call, so a
provider stuck on an unstorable value repeats the same warning at every poll — and, the first quote cached raw, the later
polls of the next 2 minutes never ask the provider for another. The refresh (``refresh._fetch_refresh_item``), when its
range reaches today, fetches the current value, stores it raw in the same current-value cache and appends it as today's
point: W-B58 skips that point at the upsert, ``changed_points`` announces it all the same, and the current price serves
the raw value from the cache for 2 minutes without asking the provider. The cure's contract:

* a refused quote is logged once per process for each (asset, provider, value), never at every poll: three polls
  answered 1E+60, 1E+60 and 1E+61 log two warnings, each naming the asset, and ask the provider three times. Counted on
  the warnings, and worse, that name the test's provider code, whichever module logs them and whatever their text, in a
  capture a barrier event of ``price_query``'s logger proves live;
* the refresh's own write to the current-value cache follows the same rules: an unstorable current value (1E+60) is
  neither cached, nor added as today's point, nor announced in ``changed_points``, and the current price then asks the
  provider again and falls back to the stored close; a valid one (65432.1234567890999) is cached as the database keeps
  it, 65432.123456789, which the current price then serves from the cache without asking the provider;
* guard: a quote that already fits is served in its own form (101.5 stays 101.5, 100 stays 100, not padded to the 12
  decimals ``storable_price`` gives them): only a quote the truncation changes is served truncated.

X-R51 (17/10, the follow-up of X-R40): a refresh whose current value is refused names the refusal. Measured on the
X-R40 + W-B62 checkpoint: the value ``storable_price`` refuses no longer reaches the upsert, whose «rejected 1 date(s)
with a value no price column can keep» made the result PARTIAL with that message; it is only logged, once. A refresh
with history answers OK with no message, one of the current value alone FAILED with «No price data available from
provider». The cure's contract: the result names the refused value (1E+60) and the limit it breaks (12 digits before
the decimal point) — PARTIAL with the history, its message the first of its errors; FAILED without, in its one
error — and the rest stays as X-R40 left it (the history stored, today absent from ``changed_points``).

The doubles and fixtures are W-B58's and W-B62's, copied from ``test_asset_digit_limits.py`` (workstream W): the two
assets of the unit (``owned``), ``_QuoteDouble`` and the ``assigned`` fixture, ``_current_price``, ``_falling_back``,
``_seed_closes`` and ``_record_current_cache``. W-B62's tests are W's, unchanged; the X-R40 tests follow them.

Each red says what the user or the operator faces; a GUARD passes before and after the cure.

Isolation: WRITE-SCOPED, the services default (as ``asset-digit-limits``). Every row is this unit's own: two EUR CRYPTO
assets created under a unique name, and only their prices, events and provider assignment are written, read and wiped,
by asset id. The provider codes are unique per test, so the current-value cache entries (keyed by the provider code) and
the log-once keys (asset, provider, value) are the test's own; ``_record_current_cache`` patches ``set`` on the shared
cache object for the test only (``monkeypatch``), every value still stored. Nothing here counts or reads a row it did
not write.
"""

import asyncio
import contextlib
import re
import sys
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint, FAUpsert
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel, SyncStatus
from backend.app.services.assets import core, price_query
from backend.app.services.assets.base import AssetSourceProvider
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.test_scripts.test_utils import unique_id

# A window far from the mock dataset and from the other price/event units (1992, 1994-1995). Rows are
# scoped by asset anyway: the dates only keep the failure output readable.
BASE_DATE = date(1991, 4, 8)


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """The two EUR CRYPTO assets of this unit: PEPE, the one the stories are about, and another one saved in the same call."""

    asset_id: int
    other_asset_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.asset_id, self.other_asset_id]


async def _wipe(owned: _Owned) -> None:
    """Drop every price and event of this unit's assets."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The two assets, under a name no concurrent worker can repeat, dropped with their rows in teardown."""
    marker = f"{unique_id('XR40')}_{uuid.uuid4().hex[:8]}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            pepe = Asset(display_name=f"XR40 PEPE {marker}", currency="EUR", asset_type=AssetType.CRYPTO, active=True)
            other = Asset(display_name=f"XR40 Other {marker}", currency="EUR", asset_type=AssetType.CRYPTO, active=True)
            session.add_all([pepe, other])
            await session.commit()
            return _Owned(pepe.id, other.id)

    async def _drop(owned: _Owned) -> None:
        await _wipe(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
            await session.commit()

    owned = asyncio.run(_create())
    yield owned
    asyncio.run(_drop(owned))


@pytest_asyncio.fixture
async def owned(owned_module: _Owned):
    """The module's assets, with no price and no event before and after the test."""
    await _wipe(owned_module)
    yield owned_module
    await _wipe(owned_module)


# --------------------------------------------------------------------------- #
# Prices: requests, read-back
# --------------------------------------------------------------------------- #


def _point(offset: int, close: str, **ohlcv: str) -> FAPricePoint:
    """One price point as the Data Editor sends it: no currency (the asset's), only the fields given."""
    return FAPricePoint(date=_day(offset), close=Decimal(close), **{field: Decimal(value) for field, value in ohlcv.items()})


async def _manual_upsert(data: list[FAUpsert]) -> dict:
    """``POST /assets/prices`` minus HTTP: the router calls the service without ``source_plugin_key`` (``"MANUAL"``)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await AssetSourceManager.bulk_upsert_prices(data, session)


async def _stored(owned: _Owned) -> dict[tuple[int, date], PriceHistory]:
    """Every price row of this unit's assets by (asset_id, date), read back through the model's column types."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))).scalars().all()
    return {(row.asset_id, row.date): row for row in rows}


# --------------------------------------------------------------------------- #
# W-B58 and W-B62: the provider double of the current-price and refresh tests
# --------------------------------------------------------------------------- #


@dataclass
class _Assigned:
    """The PEPE asset assigned, for one test, to a provider double of the test's own: its code, the assignment's id, the
    current value the double answers (a ``float`` is built without validation, as a plugin that skips the schema; an
    exception is raised, as a provider that fails), the history it serves (None: it is never asked for one), and how many
    times it was asked for each."""

    code: str
    assignment_id: int
    quote: object = Decimal("1")
    history: list[FAPricePoint] | None = None
    current_calls: int = 0
    history_calls: int = 0


class _QuoteDouble(AssetSourceProvider):
    """The provider of the current-price and refresh tests: never on the network, it answers ``assigned.quote`` in EUR, as
    of today, and ``assigned.history`` when it is set, counting every call."""

    test_only = True

    def __init__(self, assigned: _Assigned):
        self.assigned = assigned

    @property
    def provider_code(self) -> str:
        return self.assigned.code

    @property
    def provider_name(self) -> str:
        return "R13-SEC2 current-price double"

    @property
    def test_cases(self) -> list[dict]:
        return []

    @property
    def test_search_query(self) -> str | None:
        return None

    def validate_params(self, params: dict | None) -> None:
        """Any params will do."""

    async def get_current_value(self, identifier, identifier_type, provider_params=None) -> FACurrentValue:
        self.assigned.current_calls += 1
        quote = self.assigned.quote
        if isinstance(quote, Exception):
            raise quote
        if isinstance(quote, float):
            return FACurrentValue.model_construct(value=quote, currency="EUR", as_of_date=date.today(), source=self.provider_code)
        return FACurrentValue(value=quote, currency="EUR", as_of_date=date.today(), source=self.provider_code)

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        if self.assigned.history is None:
            raise AssertionError("the R13-SEC2 current-price double is never asked for a history")
        self.assigned.history_calls += 1
        return FAHistoricalData(prices=list(self.assigned.history), currency="EUR", source=self.provider_code)


async def _assign_double(owned: _Owned, monkeypatch: pytest.MonkeyPatch) -> _Assigned:
    """The PEPE asset assigned to a ``_QuoteDouble`` behind a code of the test's own, which the registry hands out from now
    on (``monkeypatch``: until the test's teardown). ``_drop_double`` undoes the assignment."""
    code = f"xr40_{uuid.uuid4().hex[:12]}"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assignment = AssetProviderAssignment(asset_id=owned.asset_id, provider_code=code, identifier=f"R13-{uuid.uuid4().hex[:8]}", identifier_type=ProviderInputType.TICKER)
        session.add(assignment)
        await session.commit()
        state = _Assigned(code=code, assignment_id=assignment.id)
    original = AssetProviderRegistry.get_provider_instance

    def get_provider_instance(_cls, provider_code, **kwargs):
        return _QuoteDouble(state) if provider_code == code else original(provider_code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(get_provider_instance))
    return state


async def _drop_double(owned: _Owned, state: _Assigned) -> None:
    """The prices and events written meanwhile, and the assignment of ``_assign_double``, dropped."""
    await _wipe(owned)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.id == state.assignment_id))
        await session.commit()


@pytest_asyncio.fixture
async def assigned(owned: _Owned, monkeypatch: pytest.MonkeyPatch):
    """The PEPE asset assigned to a ``_QuoteDouble`` behind a code of the test's own, which the registry hands out; the
    assignment, and the prices and events written meanwhile, dropped at teardown."""
    state = await _assign_double(owned, monkeypatch)
    yield state
    await _drop_double(owned, state)


async def _current_price(asset_id: int, story: str):
    """The current-price path (``get_current_prices_bulk``) for one asset: its item; an exception fails the test naming it."""
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            (item,) = await AssetSourceManager.get_current_prices_bulk([asset_id], session)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story}: get_current_prices_bulk raised {exc!r}: GET /assets/prices/current answers 500 (R13-SEC2)")
    return item


# --------------------------------------------------------------------------- #
# W-B62: the current price serves, and caches, only what the database can keep
# --------------------------------------------------------------------------- #

#: Quotes no price column can keep (``storable_price``): written in full by ``SafeDecimal`` the first is about 50 MB of
#: digits; the second has 61 integer digits; the third truncates to 0 at 12 decimal places, and a close is never 0.
_UNSTORABLE_QUOTES = [
    pytest.param(Decimal("1E+50000000"), id="1E+50000000"),
    pytest.param(Decimal("1E+60"), id="1E+60"),
    pytest.param(Decimal("1E-13"), id="1E-13-truncates-to-0"),
]


def _record_current_cache(monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, object]]:
    """From now on, every ``(key, value)`` stored in the current-value cache (``core._asset_current_cache``), in order; each
    value is still stored. A record, not a timing: the cache's 2 minutes never decide a result."""
    written: list[tuple[object, object]] = []
    cache = core._asset_current_cache
    store = cache.set

    def recording_set(key, value, *, ttl=None):
        written.append((key, value))
        store(key, value, ttl=ttl)

    monkeypatch.setattr(cache, "set", recording_set)
    return written


def _cached_quotes(written: list[tuple[object, object]]) -> list[object]:
    """The values of the current quotes the cache was given, in order."""
    return [getattr(value, "value", value) for _key, value in written]


@contextlib.asynccontextmanager
async def _falling_back(owned: _Owned, monkeypatch: pytest.MonkeyPatch, how: str) -> AsyncIterator[_Assigned | None]:
    """The PEPE asset with its current price falling back to the database: with no provider (``no-provider``), or assigned
    to a ``_QuoteDouble`` that fails (``failing-provider``), dropped on the way out."""
    if how == "no-provider":
        yield None
        return
    state = await _assign_double(owned, monkeypatch)
    state.quote = RuntimeError("provoked: the provider failed")
    try:
        yield state
    finally:
        await _drop_double(owned, state)


async def _seed_closes(owned: _Owned, closes: dict[int, str]) -> None:
    """Price rows of the PEPE asset, one per day offset, each close an SQLite literal written with raw SQL over a row the
    ORM wrote (``9e999`` is a REAL +inf, which reads ``None`` since W-B58): as an older version or another tool leaves
    them. Each close is checked as the file holds it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        for offset, literal in closes.items():
            row = PriceHistory(asset_id=owned.asset_id, date=_day(offset), close=Decimal("1"), currency="EUR", source_plugin_key="MANUAL")
            session.add(row)
            await session.flush()
            await session.execute(text(f"UPDATE price_history SET close = {literal} WHERE id = :id"), {"id": row.id})
            storage, held = (await session.execute(text("SELECT typeof(close), close FROM price_history WHERE id = :id"), {"id": row.id})).one()
            assert storage in ("integer", "real") and float(held) == float(literal), f"scaffold: the close of {_day(offset)} is held as {storage} {held!r}, not {literal}"
        await session.commit()


FALLBACKS = [pytest.param("no-provider", id="no-provider"), pytest.param("failing-provider", id="failing-provider")]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [pytest.param(True, id="a-stored-close"), pytest.param(False, id="no-stored-close")])
@pytest.mark.parametrize("quote", _UNSTORABLE_QUOTES)
async def test_an_unstorable_current_quote_is_never_served_and_the_item_falls_back_to_the_database(owned, assigned, quote, stored):
    """Red today: the quote is served as it comes, ``source`` the provider's: ``SafeDecimal`` writes 1E+50000000 in full
    (``format(v, "f")``, about 50 MB a response), 1E+60 and 1E-13 are values no price column keeps. W-B58 keeps them out
    of the database only.

    Contract (W-B62): never served — the item falls back to the database as after a provider failure: the stored close of
    the latest day, ``source`` ``db:last_known``, when a row exists (a close of 10 on day 0); otherwise ``error`` set and
    no value.
    """
    if stored:
        await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "10")])])
    assigned.quote = quote

    item = await _current_price(owned.asset_id, f"a current quote of {quote} EUR")

    assert assigned.current_calls == 1, f"barrier: the provider double was asked {assigned.current_calls} times for the current value, not once"
    served = {"source": item.source, "value": item.value, "as_of_date": item.as_of_date, "error": item.error}
    if stored:
        expected = {"source": "db:last_known", "value": Decimal("10"), "as_of_date": _day(0), "error": None}
        assert served == expected, f"W-B62: a current quote of {quote} EUR, which no price column keeps, was served as {served}: expected the stored close, {expected}"
    else:
        assert not (item.source or "").startswith("provider:") and item.value is None and item.error, f"W-B62: a current quote of {quote} EUR, which no price column keeps, was served as {served}: expected no value and an error, as when the provider fails and nothing is stored"


@pytest.mark.asyncio
@pytest.mark.parametrize("quote", [*_UNSTORABLE_QUOTES, pytest.param(float("inf"), id="derived-float-inf")])
async def test_an_unstorable_current_quote_is_never_cached(owned, assigned, monkeypatch, quote):
    """Red today: the quote is stored in the current-value cache (``core._asset_current_cache.set``) before anything checks
    it, and served from there for 2 minutes. The float inf of a plugin that skips the schema is cached too, before the item
    refuses it — and a cache hit builds the item outside the provider's ``try``, so the next call raises: derived from
    "never cached" (a non-finite quote is unstorable).

    Contract (W-B62): the cache is never given the quote — no value stored during the call is it — and a second call asks
    the provider again. Recorded, not timed.
    """
    written = _record_current_cache(monkeypatch)
    assigned.quote = quote

    await _current_price(owned.asset_id, f"a current quote of {quote}")

    assert assigned.current_calls == 1, f"barrier: the provider double was asked {assigned.current_calls} times for the current value, not once"
    cached = [value for value in _cached_quotes(written) if value is quote or value == quote]
    assert cached == [], f"W-B62: a current quote of {quote}, which no price column keeps, was stored in the current-value cache ({len(cached)} time(s)): it is served from there for 2 minutes"

    await _current_price(owned.asset_id, f"a second call after a current quote of {quote}")

    assert assigned.current_calls == 2, f"W-B62: a second call did not ask the provider again ({assigned.current_calls} call(s) in all): something held the quote of {quote} between the calls"


@pytest.mark.asyncio
async def test_a_valid_current_quote_is_served_as_the_database_keeps_it(owned, assigned):
    """Red today: served as it comes, 65432.1234567890999, while the row persisted for today holds 65432.123456789.

    Contract (W-B62): served as the database keeps it, 12 decimals then 15 significant digits, ``ROUND_DOWN``:
    65432.123456789, equal to the persisted row's close — on the first call, and on the second, served from the cache.
    Compared by value: a trailing zero is no digit.
    """
    assigned.quote = Decimal("65432.1234567890999")
    expected = Decimal("65432.123456789")

    first = await _current_price(owned.asset_id, "a current quote of 65432.1234567890999 EUR")
    second = await _current_price(owned.asset_id, "a second call after a current quote of 65432.1234567890999 EUR")

    assert (first.source, second.source) == (f"provider:{assigned.code}",) * 2, f"barrier: the quote was not served from the provider path ({first!r}, {second!r})"
    row = (await _stored(owned)).get((owned.asset_id, date.today()))
    assert row is not None and row.close == expected, f"barrier: the row persisted for today closes at {row.close if row else None}, not {expected}: the persist of W-B58 changed"
    served = (first.value, second.value)
    assert served == (row.close, row.close), f"W-B62: a current quote of 65432.1234567890999 EUR is served as {served} (first call, second call): expected {row.close}, the close the database keeps"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "delivered"),
    [
        pytest.param("close", "1E+60", id="close-1E+60"),
        pytest.param("volume", "1E+25", id="volume-1E+25"),
    ],
)
async def test_a_refresh_delta_leaves_out_a_date_no_column_can_keep(owned, assigned, field, delivered):
    """Red today: ``changed_points`` is taken from the incoming points (``_count_actual_price_changes`` compares the close
    alone), so the date W-B58 skips — a close of 1E+60, a volume of 1E+25 — is announced as changed, and the chart draws a
    point the database never got.

    Contract (W-B62): a history refresh delivering day 0 (1.5), day 1 (the unstorable value) and day 2 (2.5): day 1 is
    absent from ``FARefreshResult.changed_points``, days 0 and 2 are present. The range ends long before today, so the
    current value is not asked.
    """
    bad = _point(1, delivered) if field == "close" else _point(1, "1.5", **{field: delivered})
    assigned.history = [_point(0, "1.5"), bad, _point(2, "2.5")]
    request = FARefreshItem(asset_id=owned.asset_id, date_range=SyncDateRangeModel(start=_day(0), end=_day(2)))

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            response = await AssetSourceManager.bulk_refresh_prices([request], session)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"a refresh delivering a {field} of {delivered} EUR on {_day(1)} raised {exc!r}")

    (result,) = response.results
    assert (assigned.history_calls, result.provider_used) == (1, assigned.code), f"barrier: the refresh did not fetch the double's history once ({assigned.history_calls} calls): {result!r}"
    stored = sorted(day for (_asset_id, day) in await _stored(owned))
    assert stored == [_day(0), _day(2)], f"barrier: the refresh stored the days {stored}, not days 0 and 2 alone: the skip of W-B58 changed"
    delta = sorted(point.date for point in result.changed_points or [])
    assert _day(1) not in delta, f"W-B62: a refresh delivering a {field} of {delivered} EUR on {_day(1)}, which no column keeps, announces it in changed_points: {delta}"
    assert {_day(0), _day(2)} <= set(delta), f"W-B62: days 0 and 2 were stored, yet changed_points holds {delta}"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", FALLBACKS)
async def test_the_database_fallback_answers_the_latest_close_that_reads_a_number(owned, monkeypatch, how):
    """Red today: the fallback takes the latest row, day 1, whose close the file holds as +inf (``9e999``), which reads
    ``None`` since W-B58; ``Decimal(str(None))`` raises ``InvalidOperation``, and the whole bulk call fails.

    Contract (W-B62): no exception; the item answers the most recent row whose close reads a number, day 0's 10, with
    ``source`` ``db:last_known``. With no provider, or a provider that fails.
    """
    async with _falling_back(owned, monkeypatch, how):
        await _seed_closes(owned, {0: "10", 1: "9e999"})

        item = await _current_price(owned.asset_id, f"the database fallback ({how}) over a latest close of +inf")

    served = {"source": item.source, "value": item.value, "as_of_date": item.as_of_date, "error": item.error}
    expected = {"source": "db:last_known", "value": Decimal("10"), "as_of_date": _day(0), "error": None}
    assert served == expected, f"W-B62: the database fallback ({how}) over a latest close that reads None answered {served}: expected day 0's close, {expected}"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", FALLBACKS)
async def test_the_database_fallback_with_no_close_that_reads_a_number_answers_an_error(owned, monkeypatch, how):
    """Red today: the only row, day 1, closes at +inf, read ``None``; ``Decimal(str(None))`` raises ``InvalidOperation``.

    Contract (W-B62): no exception; the item has ``error`` set and no value. With no provider, or a provider that fails.
    """
    async with _falling_back(owned, monkeypatch, how):
        await _seed_closes(owned, {1: "9e999"})

        item = await _current_price(owned.asset_id, f"the database fallback ({how}) over a single close of +inf")

    assert item.value is None and item.error, f"W-B62: the database fallback ({how}) with no close that reads a number answered {item!r}: expected no value and an error"


@pytest.mark.asyncio
async def test_guard_a_normal_current_quote_is_served_and_cached_as_before(owned, assigned, monkeypatch):
    """Guard: green today and after. A quote of 101.5 EUR is served from the provider (compared by value), stored once in
    the current-value cache, which answers it right after, and a second call serves it again."""
    written = _record_current_cache(monkeypatch)
    assigned.quote = Decimal("101.5")

    first = await _current_price(owned.asset_id, "a current quote of 101.5 EUR")

    assert (first.source, first.value) == (f"provider:{assigned.code}", Decimal("101.5")), f"a current quote of 101.5 EUR was served as {first!r}"
    cached = _cached_quotes(written)
    assert cached == [Decimal("101.5")], f"a current quote of 101.5 EUR was cached as {cached}: expected once"
    held, held_ok = core._asset_current_cache.get(written[0][0])
    assert held_ok and getattr(held, "value", held) == Decimal("101.5"), f"the current-value cache does not answer the quote of 101.5 EUR right after the call: {held!r}"
    second = await _current_price(owned.asset_id, "a second call after a current quote of 101.5 EUR")
    assert (second.source, second.value) == (f"provider:{assigned.code}", Decimal("101.5")), f"a second call served {second!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", FALLBACKS)
async def test_guard_a_normal_latest_row_is_the_database_fallback_as_before(owned, monkeypatch, how):
    """Guard: green today and after. Closes of 10 on day 0 and 12.5 on day 1: the fallback answers day 1's 12.5, with
    ``source`` ``db:last_known``. With no provider, or a provider that fails."""
    async with _falling_back(owned, monkeypatch, how):
        await _seed_closes(owned, {0: "10", 1: "12.5"})

        item = await _current_price(owned.asset_id, f"the database fallback ({how}) over closes of 10 and 12.5")

    served = {"source": item.source, "value": item.value, "as_of_date": item.as_of_date, "error": item.error}
    expected = {"source": "db:last_known", "value": Decimal("12.5"), "as_of_date": _day(1), "error": None}
    assert served == expected, f"the database fallback ({how}) answered {served}: expected day 1's close, {expected}"


# --------------------------------------------------------------------------- #
# X-R40: a refusal logged once; the refresh caches, stores and announces only what the database keeps
# --------------------------------------------------------------------------- #

#: An event sent through price_query.py's own logger inside every capture of this block, then looked for.
_XR40_BARRIER = "X-R40 capture barrier"


def _xr40_warnings(events: list[dict], code: str) -> list[dict]:
    """The warnings, and worse, among ``events`` that name the provider ``code``, whichever module logs them and whatever
    their text; the barrier left out."""
    return [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != _XR40_BARRIER and code in str(event)]


def _xr40_names_the_asset(event: dict, asset_id: int) -> bool:
    """Whether a log event names asset ``asset_id``: its id as a whole number anywhere in the event, a field's value or the
    text. The digits of a provider code, a date or an exponent (``1E+60``) are no name."""
    return re.search(rf"(?<![\w.+-]){asset_id}(?![\w.+-])", str(event)) is not None


def _xr40_assert_the_capture_saw(events: list[dict]) -> None:
    """Barrier: an event sent through price_query.py's own logger inside the capture is there, so a missing warning is a
    warning not logged, never a blind capture."""
    assert any(event.get("event") == _XR40_BARRIER for event in events), f"barrier: the log capture saw no event of price_query.py's logger: {events}"


async def _xr40_refresh_up_to_today(owned: _Owned, assigned: _Assigned, story: str):
    """``bulk_refresh_prices`` of the PEPE asset from day 0 to today, a range that reaches today, so the refresh asks the
    current value too: its one result. An exception fails the test, naming it. Barrier: one result, from the double,
    which was asked once for the history and once for the current value."""
    request = FARefreshItem(asset_id=owned.asset_id, date_range=SyncDateRangeModel(start=_day(0), end=date.today()))
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            response = await AssetSourceManager.bulk_refresh_prices([request], session)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story}: bulk_refresh_prices raised {exc!r}")
    results = response.results
    fetched = (len(results), results[0].provider_used if results else None, assigned.history_calls, assigned.current_calls)
    assert fetched == (1, assigned.code, 1, 1), f"barrier: {story} answered (results, provider, history calls, current-value calls) = {fetched}, not (1, {assigned.code}, 1, 1): {results!r}"
    return results[0]


@pytest.mark.asyncio
async def test_an_unstorable_quote_is_logged_once_per_value_not_at_every_poll(owned, assigned):
    """Red today: the first quote of 1E+60 is cached raw and served from the cache, and the persist warns that no price
    column keeps it at every call: three polls log three warnings about 1E+60 — the operator's log repeats one refusal at
    every poll, the scheduler's and every open page's — the third poll never sees the provider's 1E+61, and the provider
    is asked once.

    Contract (X-R40): a refusal is logged once per process for each (asset, provider, value), never at every poll. The
    provider answering 1E+60, 1E+60, then 1E+61: exactly two warnings (or worse) name the test's provider, one per refused
    value, each naming the asset; and the provider is asked at each of the three polls, nothing having cached a refused
    quote. Counted whichever module logs them and whatever their text; the capture is proved live by a barrier event of
    ``price_query``'s logger.
    """
    story = f"three polls of the current price of asset {owned.asset_id}, its provider answering 1E+60, 1E+60 then 1E+61 EUR"
    assigned.quote = Decimal("1E+60")

    with capture_logs() as events:
        price_query.logger.warning(_XR40_BARRIER)
        await _current_price(owned.asset_id, "a first poll of the current price, its provider answering 1E+60 EUR")
        first_calls = assigned.current_calls
        await _current_price(owned.asset_id, "a second poll of the current price, its provider answering 1E+60 EUR")
        assigned.quote = Decimal("1E+61")
        await _current_price(owned.asset_id, "a third poll of the current price, its provider answering 1E+61 EUR")
    _xr40_assert_the_capture_saw(events)

    assert first_calls == 1, f"barrier: the provider double was asked {first_calls} times for the current value on the first poll, not once"
    warnings = _xr40_warnings(events, assigned.code)
    assert len(warnings) == 2, f"X-R40: {story} logged {len(warnings)} warning(s) naming the provider {assigned.code}: expected 2, one per refused value — the same refusal repeated at every poll fills the operator's log: {warnings}"
    unnamed = [event for event in warnings if not _xr40_names_the_asset(event, owned.asset_id)]
    assert not unnamed, f"X-R40: {story}: a warning about a refused quote does not name asset {owned.asset_id}, so the operator cannot tell which asset it is about: {unnamed}"
    assert assigned.current_calls == 3, f"X-R40: {story} asked the provider {assigned.current_calls} time(s): expected 3, one per poll — something held a refused quote between the polls"


@pytest.mark.asyncio
async def test_a_refresh_never_caches_nor_stores_nor_announces_an_unstorable_current_value(owned, assigned, monkeypatch):
    """Red today: a refresh up to today asks the provider for the current value and stores its 1E+60 raw in the
    current-value cache, then appends it as today's point: W-B58 skips that point at the upsert, ``changed_points``
    announces it all the same — the chart draws a point the database never got — and for 2 minutes the current price
    serves 1E+60 from the cache without asking the provider.

    Contract (X-R40): the refresh's own write to the current-value cache follows the rules of W-B62. A history of 1.5, 2
    and 2.5 on days 0 to 2, and a current value of 1E+60: the cache is never given 1E+60; days 0, 1 and 2 are stored,
    today is not; ``changed_points`` holds days 0 to 2, not today; the current price then asks the provider again and, the
    quote refused, answers day 2's stored close, 2.5, ``source`` ``db:last_known``.
    """
    written = _record_current_cache(monkeypatch)
    assigned.history = [_point(0, "1.5"), _point(1, "2"), _point(2, "2.5")]
    assigned.quote = Decimal("1E+60")
    story = "a refresh up to today whose provider answers a current value of 1E+60 EUR"

    result = await _xr40_refresh_up_to_today(owned, assigned, story)

    cached = [value for value in _cached_quotes(written) if value is assigned.quote or value == assigned.quote]
    assert cached == [], f"X-R40: {story}, which no price column keeps, stored it in the current-value cache ({len(cached)} time(s)): the current price serves it from there for 2 minutes, without asking the provider"
    stored = sorted(day for (_asset_id, day) in await _stored(owned))
    assert stored == [_day(0), _day(1), _day(2)], f"X-R40: {story} stored the days {stored}: expected days 0, 1 and 2, and not today, whose value no column keeps"
    delta = sorted(point.date for point in result.changed_points or [])
    assert date.today() not in delta, f"X-R40: {story} announces today in changed_points, a value no column keeps — the chart draws a point the database never got: {delta}"
    assert {_day(0), _day(1), _day(2)} <= set(delta), f"X-R40: days 0, 1 and 2 were stored, yet changed_points holds {delta}"

    item = await _current_price(owned.asset_id, f"the current price after {story}")

    assert assigned.current_calls == 2, f"X-R40: after {story}, the current price did not ask the provider ({assigned.current_calls} call(s) in all): it was answered by what the refresh left in the cache"
    served = {"source": item.source, "value": item.value, "as_of_date": item.as_of_date, "error": item.error}
    expected = {"source": "db:last_known", "value": Decimal("2.5"), "as_of_date": _day(2), "error": None}
    assert served == expected, f"X-R40: after {story}, the current price answered {served}: expected day 2's stored close, {expected}"


@pytest.mark.asyncio
async def test_a_refresh_caches_a_valid_current_value_as_the_database_keeps_it(owned, assigned, monkeypatch):
    """Red today: the refresh stores the provider's current value raw in the current-value cache, 65432.1234567890999,
    while the row it writes for today closes at 65432.123456789; the current price then serves 65432.1234567890999 from
    the cache — a price the database does not hold.

    Contract (X-R40): cached as the database keeps it (12 decimals then 15 significant digits, ``ROUND_DOWN``): every value
    the cache is given is 65432.123456789, by value; the current price then serves 65432.123456789 from the cache,
    ``source`` the provider's, without asking the provider again.
    """
    written = _record_current_cache(monkeypatch)
    assigned.history = [_point(0, "1.5"), _point(1, "2"), _point(2, "2.5")]
    assigned.quote = Decimal("65432.1234567890999")
    expected = Decimal("65432.123456789")
    story = "a refresh up to today whose provider answers a current value of 65432.1234567890999 EUR"

    await _xr40_refresh_up_to_today(owned, assigned, story)

    row = (await _stored(owned)).get((owned.asset_id, date.today()))
    assert row is not None and row.close == expected, f"barrier: the row {story} stored for today closes at {row.close if row else None}, not {expected}: the persist of W-B58 changed"
    cached = _cached_quotes(written)
    assert cached and all(value == expected for value in cached), f"X-R40: {story} gave the current-value cache {cached}: expected {expected}, the close the database keeps (by value)"

    item = await _current_price(owned.asset_id, f"the current price after {story}")

    served = (item.source, item.value)
    assert served == (f"provider:{assigned.code}", expected), f"X-R40: after {story}, the current price served {served}: expected {expected} from the cache, the close the database keeps"
    assert assigned.current_calls == 1, f"X-R40: after {story}, the current price asked the provider again ({assigned.current_calls} calls in all): the value the refresh cached was not served"


# --------------------------------------------------------------------------- #
# X-R51: a refresh whose current value is refused names the refusal
# --------------------------------------------------------------------------- #


def _xr51_whole_numbers(text: str, asset_id: int, *quoted: str) -> set[str]:
    """The whole numbers ``text`` states, its ``quoted`` values, its ISO dates and its naming of the asset (``asset 12``,
    ``asset_id=12``) taken out first: none of them can stand in for a limit, nor can the digits of a provider code, an
    identifier, a decimal or an exponent (a number touching a letter, ``_``, ``.``, ``+`` or ``-`` before it, or a letter,
    ``_`` or decimals after it)."""
    for value in quoted:
        text = text.replace(value, " ")
    text = re.sub(r"\d{4}-\d{2}-\d{2}", " ", text)
    text = re.sub(rf"(?i)\basset\w*\W{{0,4}}{asset_id}(?!\w|\.\d)", " ", text)
    return set(re.findall(r"(?<![\w.+-])\d+(?!\w|\.\d)", text))


def _xr51_assert_names_the_refusal(text: str | None, refused: str, asset_id: int, story: str) -> None:
    """X-R51: ``text`` names the refused current value, ``refused`` as written, and the limit it breaks, 12 digits before
    the decimal point: the whole number 12 (``_xr51_whole_numbers``)."""
    named = text is not None and refused in text and "12" in _xr51_whole_numbers(text, asset_id, refused)
    assert named, f"X-R51: {story} reports {text!r}: expected it to name the refused value, {refused}, and the limit it breaks, 12 digits before the decimal point — the user is not told why today's price is missing"


async def _xr51_refresh(owned: _Owned, assigned: _Assigned, start: date, story: str):
    """``bulk_refresh_prices`` of the PEPE asset from ``start`` to today, a range that reaches today, so the refresh asks the
    current value: its one result. An exception fails the test, naming it. Barrier: one result, from the double, which was
    asked once for the current value, and once for the history when the range starts before today, never when it starts
    today."""
    request = FARefreshItem(asset_id=owned.asset_id, date_range=SyncDateRangeModel(start=start, end=date.today()))
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            response = await AssetSourceManager.bulk_refresh_prices([request], session)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story}: bulk_refresh_prices raised {exc!r}")
    results = response.results
    expected = (1, assigned.code, 1 if start < date.today() else 0, 1)
    fetched = (len(results), results[0].provider_used if results else None, assigned.history_calls, assigned.current_calls)
    assert fetched == expected, f"barrier: {story} answered (results, provider, history calls, current-value calls) = {fetched}, not {expected}: {results!r}"
    return results[0]


@pytest.mark.asyncio
async def test_a_refresh_with_history_names_a_refused_current_value(owned, assigned):
    """Red today: a refresh up to today stores the history of days 0 to 2 and answers OK, with no message: the current
    value of 1E+60 is refused before it becomes today's point and only logged, once (X-R40), so the user who asked for
    today sees a refresh that went well and no price for today. Before X-R40 the refused point reached the upsert, whose
    «rejected 1 date(s) with a value no price column can keep» made the result PARTIAL with that message.

    Contract (X-R51): the result names the refusal — PARTIAL, its message the first of its errors, naming the refused
    value, 1E+60, and the limit it breaks, 12 digits before the decimal point (a whole number: the dates and the value
    taken out first) — and the rest stays as X-R40 left it: days 0, 1 and 2 stored, today absent from ``changed_points``.
    """
    assigned.history = [_point(0, "1.5"), _point(1, "2"), _point(2, "2.5")]
    assigned.quote = Decimal("1E+60")
    story = "a refresh up to today whose provider answers a history of days 0 to 2 and a current value of 1E+60 EUR"

    result = await _xr51_refresh(owned, assigned, _day(0), story)

    answered = {"status": result.status, "message": result.message, "errors": result.errors}
    assert result.status == SyncStatus.PARTIAL and result.errors and result.message == result.errors[0], f"X-R51: {story} answered {answered}: expected PARTIAL, its message the first of its errors, naming the refused current value — the user sees a refresh that went well, and no price for today"
    _xr51_assert_names_the_refusal(result.message, "1E+60", owned.asset_id, story)
    stored = sorted(day for (_asset_id, day) in await _stored(owned))
    assert stored == [_day(0), _day(1), _day(2)], f"X-R51: {story} stored the days {stored}: expected days 0, 1 and 2, and not today, whose value no column keeps"
    delta = sorted(point.date for point in result.changed_points or [])
    assert date.today() not in delta and {_day(0), _day(1), _day(2)} <= set(delta), f"X-R51: {story} announces {delta} in changed_points: expected days 0, 1 and 2, and not today, whose value no column keeps"


@pytest.mark.asyncio
async def test_a_refresh_of_the_current_value_alone_names_a_refused_one(owned, assigned):
    """Red today: a refresh of today alone asks the provider for the current value only; its 1E+60 is refused and only
    logged, once (X-R40), and the result is FAILED with the generic «No price data available from provider»: the user is
    told the provider had nothing, when it answered a value no price column keeps.

    Contract (X-R51): FAILED, with one error naming the refused value, 1E+60, and the limit it breaks, 12 digits before
    the decimal point — not «No price data available from provider». No history is asked, the range starting today: the
    double would serve an empty one and count the call, which the barrier would see (a history left None is no barrier:
    the double raises before it counts, and the refresh swallows the raise).
    """
    assigned.history = []
    assigned.quote = Decimal("1E+60")
    story = "a refresh of today alone whose provider answers a current value of 1E+60 EUR"

    result = await _xr51_refresh(owned, assigned, date.today(), story)

    answered = {"status": result.status, "message": result.message, "errors": result.errors}
    assert result.status == SyncStatus.FAILED and len(result.errors) == 1, f"X-R51: {story} answered {answered}: expected FAILED, with one error naming the refused current value"
    _xr51_assert_names_the_refusal(result.errors[0], "1E+60", owned.asset_id, f"{story} (not «No price data available from provider»)")


@pytest.mark.asyncio
@pytest.mark.parametrize("quote", [pytest.param(Decimal("101.5"), id="101.5"), pytest.param(Decimal("100"), id="100")])
async def test_guard_a_quote_that_fits_is_served_in_its_own_form(owned, assigned, quote):
    """Guard: green today and after. A quote that already fits is served in its own form, on the first call and from the
    cache: 101.5 stays 101.5 and 100 stays 100 (``as_tuple``), not the 101.500000000000 and 100.000000000000
    ``storable_price`` gives them. Only a quote the truncation changes is served truncated."""
    assigned.quote = quote

    first = await _current_price(owned.asset_id, f"a current quote of {quote} EUR")
    second = await _current_price(owned.asset_id, f"a second call after a current quote of {quote} EUR")

    assert assigned.current_calls == 1, f"barrier: the provider double was asked {assigned.current_calls} times for the current value in two calls, not once: the second call was not served from the cache"
    served = [(item.source, item.value.as_tuple() if item.value is not None else None) for item in (first, second)]
    expected = [(f"provider:{assigned.code}", quote.as_tuple())] * 2
    assert served == expected, f"a current quote of {quote} EUR, which fits, was served as {first.value!r} then {second.value!r} from the cache ({first.source}, {second.source}): expected {quote!r} in its own form both times"
