"""MF-J1-8a (workstream MF, J-1 item 8) — an FX gap is read one way: by the engine's securities and by the native cash.

What it guards. A guard, no product change (green on HEAD 5d87dec28, and on the P3 cure). Two readers value a portfolio
day in the report currency, and both get their rates from ONE rule of the FX service
(``backend/app/services/fx/conversion.py``): the latest usable rate on or before the day, with no limit on how far back,
a row the bounds ``usable_fx_rate_bounds()`` (X-R38) reject (a stored 0, ``inf``, anything at or above
``usable_fx_rate_bounds()[1]``) being a missing rate, filled over like a day without a row. Since P3 («formule veloci»)
the rule has two doors that share it: ``convert_bulk``, an amount on a day, and ``unit_rate_steps``, one unit on windows
of days kept as steps (the days a stored rate changes) — the same rows and filter (``_usable_rates``, from each window's
backward-fill anchor) and the same arithmetic (``_converted``), so on every asked day a step is ``convert_bulk``'s answer
to the digit (pinned by ``test_services/test_fx_rate_steps.py``).

- The engine (``financial_math/portfolio/engine.py::_preload_fx_rates``) gathers, for each foreign currency, the windows
  of days it reads — every day of ``[actual_from, actual_to]`` for the price / asset currencies, each transaction date,
  every day a cash transfer is in transit — makes one ``unit_rate_steps`` call and returns ``AskedDayRates(steps,
  windows)`` (``financial_math/fx_rates.py``) as ``fx_rate_map``: ``fx_rate_map[(currency, report currency, day)]`` is
  the step on or before the day, on an asked day only (any other day is absent, as in the dict it replaces).
  ``DailyStateBuilder._convert`` / ``_market_value_for`` read it at the exact day. The securities are valued with it.
  Before P3 it asked ``convert_bulk`` for one unit on every one of those days.
- The native cash (``financial_math/native_cash.py::compute_native_cash``, called with ``rates_until=actual_to``)
  converts each foreign movement at its date with ``convert_bulk``, and asks one unit of each foreign currency on every
  day from its first movement through ``rates_until`` as windows (``_unit_windows``) in one ``unit_rate_steps`` call.
  ``NativeCash.unit_rates`` is ``AskedDayRates(steps, windows, fixed_destination=report currency)``: its walk gives
  ``(currency, day)`` for every asked day with a rate, as the dict did. ``_rate_at`` bisects the steps themselves
  (``step_series()``: only the days a rate starts) for the last rate on or before the day, and ``_foreign_value`` raises on
  a counted balance without one. The cash is valued with it, and the daily states take their cash from it
  (``_revalue_foreign_cash``). Before P3 the unit rates were ``convert_bulk`` answers on every day (``_unit_requests``),
  and ``_rate_at`` bisected all of them.

The backlog (CP-6) had feared that a gap «beyond ``convert_bulk``'s fill window» would leave the cash valued and the
securities not: there is no such window, both readings come from the same unlimited fill. This file keeps it that way.

The book, on a private SQLite file under ``tmp_path`` (the app schema, ``SQLModel.metadata.create_all``, an engine of its
own, ``sqlite+aiosqlite``, NullPool, disposed at teardown): user U owns broker A at 100 %, report currency EUR; X is a
USD stock with a close on every calendar day D1..END (2024-03-01..03-29, ``100 + i/2`` USD).

- D1 03-01: DEPOSIT 10000 USD (before the report window, START = 03-02);  D2 03-02: BUY 10 X for 1000 USD;
- GAP_BUY_DAY 03-11 (inside the gap): BUY 4 X for 400 USD.
- Rates stored on D1, D2, D3 (03-01..03-03), then NONE from 03-04 to 03-17 (the gap, 14 days), then on every day from
  RESUME (03-18) to END. 1 USD is worth 0.8, 0.78125, 0.625 EUR on D1..D3; every value has a terminating inverse, so the
  stored EUR/USD rate (``fx/storage.py::normalize_rate_for_storage``: the pair in alphabetical order, the rate
  inverted — 1.25, 1.28, 1.6) and its conversion back are exact, and every comparison below is ``==``.
- Inside the gap, two legacy rows an older release could store, written with raw SQL past the model (the table has no
  CHECK on ``rate``; a barrier reads them back): EUR/USD 0 on 03-08 and 1e19 on 03-13. Both are outside
  ``usable_fx_rate_bounds()``: every gap day must read D3's 0.625, never them.

The tests (every day of the gap is asserted, the deviations listed all at once):

- ``TestOneReadingOfTheGap`` — ``PortfolioService.get_report`` over START..END, with recorders on
  ``PortfolioCalculationEngine._preload_fx_rates`` (the ``fx_rate_map`` it returns) and on the engine module's
  ``compute_native_cash`` (the ``NativeCash`` it returns, the very one the engine result carries): both maps cover every
  day D1..END and hold the same rate on each; every gap day carries D3's rate, every stored day its own; on every gap day
  the daily state values the securities (``qty × close × 0.625``, no missing price or FX, NAV complete) and the cash
  (``USD balance × 0.625``, the native cash's ``value_at``), and the report's history point says the same.
- ``TestTheNativeCashFillsOnItsOwn`` — the native cash's second layer: rebuilt from a plain dict of the unit rates of the
  stored days only (as if nothing had been asked in the gap; ``_rate_series`` reads a dict as before P3), it values
  every day D1..END as the real one does. Since P3 the real one reads its steps only (D1..D3, then RESUME on), so this
  carrying forward is read end to end too.
- ``TestBeforeTheFirstRate`` — the same book with a DEPOSIT of 500 USD on EARLY_DAY (02-27), before the first stored
  rate: neither reader has a rate on 02-27..02-29; the native cash does not count the deposit (no conversion, reported
  missing) and neither does the engine (its ``missing_fx`` names the day; the cash on D1 is 10000 × 0.8, not 10500 × 0.8).

Teeth — product mutations that turn it red. First applied at runtime in a private harness on HEAD 5d87dec28; re-measured
on the P3 cure (HEAD 2f4ab1962 + the cure) on a scratch copy, which is what follows:

- (a) a fill limit in the engine's reading only (re-expressed for P3: a step of ``_preload_fx_rates``'s map whose stored
  row is more than 5 days older than the day reads no rate; before P3, a ``convert_bulk`` answer that old was dropped):
  the engine's map loses 03-09..03-17, the native cash keeps them; the securities read 0 with USD/EUR missing and the
  engine's cash misses the BUY of 03-11 — the three ``TestOneReadingOfTheGap`` tests red, as before P3;
- (b) ``NativeCash._rate_at`` reading the exact day only: no longer masked end to end. Before P3 every day had a unit
  rate, so only ``TestTheNativeCashFillsOnItsOwn`` saw it; now the native cash keeps its steps only, and its
  ``value_at`` raises ``ValueError`` from the first gap day — ``TestOneReadingOfTheGap``'s third test and
  ``TestTheNativeCashFillsOnItsOwn`` red;
- (c) the usable bounds (X-R38) dropped from ``_usable_rates``, both doors at once: the 0 row of 03-08 becomes a step and
  ``unit_rate_steps`` divides by it — ``decimal.DivisionByZero`` from the report (``convert_bulk`` caught it per item and
  answered no rate; the steps have no such catch: the bounds are their only guard) — all five tests red;
- (d) a fill limit in ``convert_bulk`` alone (the backlog's «fill window» made real), since P3 only the movements' door:
  both maps keep 03-09..03-17 (they read ``unit_rate_steps``); the native cash no longer converts the BUY of 03-11 (left
  out, reported missing) while the engine still counts it — ``TestOneReadingOfTheGap``'s third test,
  ``TestTheNativeCashFillsOnItsOwn`` and ``TestBeforeTheFirstRate`` red (before P3, all five);
- (d') the same limit in ``unit_rate_steps`` alone, the second door (a step older than 5 days expires): both maps lose
  03-09..03-17, and the native cash raises ``ValueError: no USD/EUR rate on or before 2024-03-09`` for its counted
  balance — all five tests red. A fill window for every reader now needs both doors; ``test_fx_rate_steps.py`` (X)
  holds them to one rule, and ``test_fx_steps_service_parity.py`` catches either alone (8 reds each);
- (e) ``NativeCash._rate_at`` reading forward (``bisect_left``, the rate on or after the day): no longer masked, like
  (b): the gap reads RESUME's 0.64 in the real native cash too — ``TestOneReadingOfTheGap``'s third test and
  ``TestTheNativeCashFillsOnItsOwn`` red.

No assertion of this file changed for P3: the two walks (``fx_rate_map.items()``, ``native_cash.unit_rates.items()``)
still give every asked day, and every re-expressed mutant turns red the tests named above.

Isolation: PURE with respect to the lane — no session on the lane's database, no server, no network. The L2, WAC and
engine blob caches (process-global) are emptied before and after each test; every patch goes through ``monkeypatch``.
No sleep, no wall-clock assertion, no translated text.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_fx_gap_single_reading``.

Reference: backend/app/services/fx/conversion.py (convert_bulk, unit_rate_steps, _usable_rates),
backend/app/services/financial_math/fx_rates.py (AskedDayRates), backend/app/services/financial_math/portfolio/engine.py
(_preload_fx_rates, compute_native_cash's call), backend/app/services/financial_math/portfolio/daily_state.py (_convert,
_market_value_for, _revalue_foreign_cash), backend/app/services/financial_math/native_cash.py (_unit_windows, _rate_at,
_step_rate_series, _foreign_value), backend/test_scripts/test_services/test_financial/test_fx_steps_service_parity.py
(P3: both readers against convert_bulk, bit for bit),
LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md
(«J-1 — riconciliazione», item 8, proposal 8a).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.precision import usable_fx_rate_bounds
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery, PortfolioReportResponse
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.native_cash import MissingCashConversion, NativeCash
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.fx.storage import normalize_rate_for_storage
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"
PAIR = f"{USD}/{EUR}"

EARLY_DAY = date(2024, 2, 27)
D1 = date(2024, 3, 1)
D2 = date(2024, 3, 2)
D3 = date(2024, 3, 3)
GAP_FIRST = date(2024, 3, 4)
ZERO_DAY = date(2024, 3, 8)
GAP_BUY_DAY = date(2024, 3, 11)
HUGE_DAY = date(2024, 3, 13)
GAP_LAST = date(2024, 3, 17)
RESUME = date(2024, 3, 18)
END = date(2024, 3, 29)
START = D2  # the report window: the DEPOSIT of D1 is before it

LEGACY_SOURCE = "MF-J1-8a legacy"


def _days(first: date, last: date) -> tuple[date, ...]:
    """Every calendar day from ``first`` to ``last``, both included."""
    return tuple(first + timedelta(days=offset) for offset in range((last - first).days + 1))


GAP_DAYS = _days(GAP_FIRST, GAP_LAST)
FRAME_DAYS = _days(D1, END)

# 1 USD in EUR on each day with a stored row. Every value has a terminating inverse: the stored EUR/USD rate (1 / value)
# and the conversion back (1 / rate) are exact, so the readers' rates and the values built on them compare with ==.
_RESUMED_CYCLE = ("0.64", "0.8", "0.78125", "0.5", "0.9765625", "0.4")
USD_IN_EUR: dict[date, Decimal] = {
    D1: Decimal("0.8"),
    D2: Decimal("0.78125"),
    D3: Decimal("0.625"),
    **{day: Decimal(_RESUMED_CYCLE[index % len(_RESUMED_CYCLE)]) for index, day in enumerate(_days(RESUME, END))},
}
# Legacy EUR/USD rows inside the gap, as an older release could store them: below and above usable_fx_rate_bounds().
LEGACY_EUR_USD: dict[date, Decimal] = {ZERO_DAY: Decimal("0"), HUGE_DAY: Decimal("1e19")}

CLOSES: dict[date, Decimal] = {day: Decimal("100") + Decimal(index) / 2 for index, day in enumerate(FRAME_DAYS)}

# (label, asset, type, day, quantity, amount) — every amount in USD, at broker A
_ROWS = (
    ("deposit", None, TransactionType.DEPOSIT, D1, "0", "10000"),
    ("buy_1", "X", TransactionType.BUY, D2, "10", "-1000"),
    ("buy_2", "X", TransactionType.BUY, GAP_BUY_DAY, "4", "-400"),
)
_EARLY_ROW = ("early_deposit", None, TransactionType.DEPOSIT, EARLY_DAY, "0", "500")


def _held_quantity(day: date) -> Decimal:
    """X held at the end of ``day`` (from the book's rows)."""
    return sum((Decimal(quantity) for _label, asset, _type, row_day, quantity, _amount in _ROWS if asset == "X" and row_day <= day), Decimal("0"))


def _usd_cash(day: date) -> Decimal:
    """The USD balance at the end of ``day``, from D1 (the book's rows; the early deposit is never counted)."""
    return sum((Decimal(amount) for _label, _asset, _type, row_day, _quantity, amount in _ROWS if row_day <= day), Decimal("0"))


def _last_usable_rate(day: date) -> Decimal:
    """1 USD in EUR as the rule reads it: the latest stored (usable) day on or before ``day``."""
    return USD_IN_EUR[max(stored for stored in USD_IN_EUR if stored <= day)]


def _show_days(days: Iterable[date]) -> str:
    """Days as runs: ``2024-03-09..2024-03-17, 2024-03-20``."""
    ordered = sorted(set(days))
    runs: list[tuple[date, date]] = []
    for day in ordered:
        if runs and day == runs[-1][1] + timedelta(days=1):
            runs[-1] = (runs[-1][0], day)
        else:
            runs.append((day, day))
    return ", ".join(first.isoformat() if first == last else f"{first.isoformat()}..{last.isoformat()}" for first, last in runs) or "none"


def _show_lines(lines: list[str], shown: int = 20) -> str:
    more = f"\n  … and {len(lines) - shown} more" if len(lines) > shown else ""
    return "\n  " + "\n  ".join(lines[:shown]) + more


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_id: int
    asset_id: int


async def _seed(engine: AsyncEngine, *, early_deposit: bool) -> _Book:
    """The book, owned by a new user, committed to the private file; then the legacy rows, past the model."""
    tag = uuid4().hex[:12]
    rows = (*_ROWS, _EARLY_ROW) if early_deposit else _ROWS
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"mfj1_8a_{tag}", email=f"mfj1_8a_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker = Broker(name=f"MF-J1-8a fx gap A {tag}")
        asset = Asset(display_name=f"MF-J1-8a fx gap X {tag}", currency=USD, asset_type=AssetType.STOCK)
        session.add_all([user, broker, asset])
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add_all([PriceHistory(asset_id=asset.id, date=day, open=close, high=close, low=close, close=close, volume=Decimal("1"), currency=USD, source_plugin_key="mfj1_8a_test") for day, close in CLOSES.items()])
        for day, usd_in_eur in USD_IN_EUR.items():
            # As the app stores a rate: the pair in alphabetical order, the rate inverted when it is not (1 EUR = rate USD)
            base, quote, rate = normalize_rate_for_storage(USD, EUR, usd_in_eur)
            session.add(FxRate(date=day, base=base, quote=quote, rate=rate, source="MF-J1-8a"))
        session.add_all([Transaction(broker_id=broker.id, asset_id=asset.id if asset_label else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=USD) for _label, asset_label, tx_type, day, quantity, amount in rows])
        await session.commit()
        book = _Book(engine=engine, user_id=user.id, broker_id=broker.id, asset_id=asset.id)

    smallest, first_refused = usable_fx_rate_bounds()
    async with engine.begin() as connection:
        for day, planted in LEGACY_EUR_USD.items():
            assert not (smallest <= planted < first_refused), f"the fixture itself is wrong: a legacy rate {planted} is inside usable_fx_rate_bounds() {smallest}..{first_refused}"
            await connection.execute(
                text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"),
                {"day": day.isoformat(), "base": EUR, "quote": USD, "rate": float(planted), "source": LEGACY_SOURCE},
            )
        stored = {date.fromisoformat(day): Decimal(str(rate)) for day, rate in (await connection.execute(text("SELECT date, rate FROM fx_rates WHERE source = :source"), {"source": LEGACY_SOURCE})).all()}
        assert stored == LEGACY_EUR_USD, f"the fixture itself is wrong: raw SQL reads back {stored}, not the legacy rates planted, {LEGACY_EUR_USD}"
        oriented = (await connection.execute(text("SELECT DISTINCT base, quote FROM fx_rates"))).all()
        assert [tuple(pair) for pair in oriented] == [(EUR, USD)], f"the fixture itself is wrong: fx_rates holds the pairs {oriented}, not EUR/USD alone as the app stores USD/EUR"
    return book


@asynccontextmanager
async def _private_book(directory: Path, *, early_deposit: bool) -> AsyncIterator[_Book]:
    """The app schema and the book on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mfj1_8a_fx_gap.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine, early_deposit=early_deposit)
    finally:
        await engine.dispose()


# =============================================================================
# THE READING — the report, with what each reader was handed
# =============================================================================


@dataclass
class _Recorders:
    """What the engine's two readers were handed during a report: ``fx_rate_map`` and ``NativeCash``, and the result."""

    fx_rate_maps: list[dict[tuple[str, str, date], Decimal]] = field(default_factory=list)
    native_cashes: list[NativeCash] = field(default_factory=list)
    results: list[PortfolioCalculationResult] = field(default_factory=list)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> _Recorders:
        """Wrap the methods that build and return each value: each delegates to what it wraps and keeps its answer."""
        real_preload = PortfolioCalculationEngine._preload_fx_rates
        real_native_cash = portfolio_engine_module.compute_native_cash
        real_calculate = PortfolioCalculationEngine.calculate

        async def preload(engine_self, *args, **kwargs):
            fx_rate_map = await real_preload(engine_self, *args, **kwargs)
            self.fx_rate_maps.append(fx_rate_map)
            return fx_rate_map

        async def native_cash(*args, **kwargs):
            built = await real_native_cash(*args, **kwargs)
            self.native_cashes.append(built)
            return built

        async def calculate(engine_self, *args, **kwargs):
            result = await real_calculate(engine_self, *args, **kwargs)
            self.results.append(result)
            return result

        monkeypatch.setattr(PortfolioCalculationEngine, "_preload_fx_rates", preload)
        monkeypatch.setattr(portfolio_engine_module, "compute_native_cash", native_cash)
        monkeypatch.setattr(PortfolioCalculationEngine, "calculate", calculate)
        return self


@dataclass(frozen=True)
class _Reading:
    book: _Book
    fx_rate_map: dict[tuple[str, str, date], Decimal]
    native_cash: NativeCash
    result: PortfolioCalculationResult
    report: PortfolioReportResponse

    def engine_rates(self) -> dict[date, Decimal]:
        """1 USD in EUR by day, as the engine's ``fx_rate_map`` holds it."""
        return {day: rate for (currency, target, day), rate in self.fx_rate_map.items() if currency == USD and target == EUR}

    def native_rates(self) -> dict[date, Decimal]:
        """1 USD in EUR by day, as the native cash's ``unit_rates`` holds it."""
        return {day: rate for (currency, day), rate in self.native_cash.unit_rates.items() if currency == USD}

    def states(self) -> dict[date, DailyPortfolioState]:
        return {state.date: state for state in self.result.daily_states}


async def _read_the_book(directory: Path, monkeypatch: pytest.MonkeyPatch, *, early_deposit: bool = False) -> _Reading:
    """One report over START..END in EUR, on a session of the book's own file; what the two readers were handed."""
    recorders = _Recorders().install(monkeypatch)
    async with _private_book(directory, early_deposit=early_deposit) as book:
        query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=START, end=END), target_currency=EUR, include_summary=True, include_history=True, include_allocation_history=False)
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            report = await PortfolioService(session).get_report(book.user_id, query)
    # The caches are empty and one report asks for one build: anything else and the recorders do not describe it
    built = (len(recorders.results), len(recorders.fx_rate_maps), len(recorders.native_cashes))
    assert built == (1, 1, 1), f"one report on emptied caches made (engine results, fx_rate_maps, native cashes) = {built}: expected one build of each"
    result = recorders.results[0]
    assert result.native_cash is recorders.native_cashes[0], "the engine result does not carry the NativeCash compute_native_cash returned: the daily states were valued with another one"
    return _Reading(book=book, fx_rate_map=recorders.fx_rate_maps[0], native_cash=recorders.native_cashes[0], result=result, report=report)


def _value_at(native_cash: NativeCash, day: date, broker_id: int) -> Decimal | str | None:
    """The native cash's value of the broker on ``day``, or the error it raised, as text."""
    try:
        return native_cash.value_at(day).get(broker_id)
    except ValueError as error:
        return f"raised ValueError({error})"


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# 1 — THE GUARD: ONE READING OF THE GAP
# =============================================================================


class TestOneReadingOfTheGap:
    @pytest.mark.asyncio
    async def test_the_two_readers_hold_the_same_rate_on_every_day(self, tmp_path, monkeypatch):
        """Both maps cover every day D1..END, and on each the engine's rate == the native cash's (Decimal ==)."""
        print_section("MF-J1-8a: fx_rate_map and NativeCash.unit_rates hold the same USD/EUR rate on every day")
        reading = await _read_the_book(tmp_path, monkeypatch)
        engine_rates, native_rates = reading.engine_rates(), reading.native_rates()

        engine_missing = [day for day in FRAME_DAYS if day not in engine_rates]
        native_missing = [day for day in FRAME_DAYS if day not in native_rates]
        assert not engine_missing and not native_missing, f"a reader has no {PAIR} rate on a day of the frame {D1}..{END} (the gap is {GAP_FIRST}..{GAP_LAST}):\n  engine fx_rate_map missing: {_show_days(engine_missing)}\n  native cash unit_rates missing: {_show_days(native_missing)}"
        differ = [f"{day}: engine {engine_rates[day]}, native cash {native_rates[day]}" for day in sorted(engine_rates.keys() & native_rates.keys()) if engine_rates[day] != native_rates[day]]
        assert not differ, f"the engine and the native cash read {PAIR} differently on {len(differ)} day(s):{_show_lines(differ)}"
        print_success(f"✓ {len(FRAME_DAYS)} days, one {PAIR} rate per day for both readers")

    @pytest.mark.asyncio
    async def test_every_gap_day_carries_the_last_usable_rate_before_it(self, tmp_path, monkeypatch):
        """Every gap day reads D3's 0.625 in both maps — never a legacy row (0 on 03-08, 1e19 on 03-13) — and every
        stored day reads its own rate (the fill stops at RESUME)."""
        print_section("MF-J1-8a: every gap day carries D3's rate in both readers, not the legacy rows")
        reading = await _read_the_book(tmp_path, monkeypatch)
        engine_rates, native_rates = reading.engine_rates(), reading.native_rates()

        wrong: list[str] = []
        for day in FRAME_DAYS:
            expected = _last_usable_rate(day)
            for reader, rates in (("engine", engine_rates), ("native cash", native_rates)):
                got = rates.get(day)
                if got != expected:
                    where = "gap day" if day in GAP_DAYS else "stored day"
                    wrong.append(f"{day} ({where}), {reader}: {got if got is not None else 'no rate'}, expected {expected}")
        legacy = ", ".join(f"EUR/USD {rate} on {day}" for day, rate in LEGACY_EUR_USD.items())
        assert not wrong, f"a reader does not read {PAIR} as the latest usable rate on or before the day ({len(wrong)} deviation(s); D3 {D3} = {USD_IN_EUR[D3]}; the legacy rows, never to be read: {legacy}):{_show_lines(wrong)}"
        print_success(f"✓ the {len(GAP_DAYS)} gap days read {USD_IN_EUR[D3]} (D3) in both readers; the legacy rows are skipped")

    @pytest.mark.asyncio
    async def test_every_gap_day_values_the_securities_and_the_cash_at_that_rate(self, tmp_path, monkeypatch):
        """On every gap day the daily state has the securities valued (qty × close × 0.625, nothing missing) and the cash
        valued (USD balance × 0.625, the native cash's value), and the report's history point says the same."""
        print_section("MF-J1-8a: every gap day values the securities and the cash, at the same rate")
        reading = await _read_the_book(tmp_path, monkeypatch)
        states = reading.states()
        points = {point.date: point for point in reading.report.history or []}
        broker_id = reading.book.broker_id

        wrong: list[str] = []
        for day in GAP_DAYS:
            rate = _last_usable_rate(day)
            state = states.get(day)
            if state is None:
                wrong.append(f"{day}: no daily state")
                continue
            securities = _held_quantity(day) * CLOSES[day] * rate
            cash = _usd_cash(day) * rate
            if state.missing_fx_pairs or state.missing_price_asset_ids or not state.nav_complete:
                wrong.append(f"{day}: missing FX {sorted(state.missing_fx_pairs)}, missing price {sorted(state.missing_price_asset_ids)}, nav_complete {state.nav_complete}")
            if state.market_value != securities:
                wrong.append(f"{day}: securities {state.market_value}, expected {_held_quantity(day)} × {CLOSES[day]} × {rate} = {securities}")
            native_value = _value_at(reading.native_cash, day, broker_id)
            if native_value != cash:
                wrong.append(f"{day}: native cash value {native_value}, expected {_usd_cash(day)} USD × {rate} = {cash}")
            if state.cash_value != cash:
                wrong.append(f"{day}: state cash {state.cash_value}, expected {cash}")
            point = points.get(day)
            if point is None:
                wrong.append(f"{day}: no history point in the report")
            elif (point.market_value.amount, point.cash_value.amount) != (state.market_value, state.cash_value):
                wrong.append(f"{day}: history point (securities, cash) = ({point.market_value.amount}, {point.cash_value.amount}), the state's ({state.market_value}, {state.cash_value})")
        assert not wrong, f"a gap day does not value both the securities and the cash at D3's {PAIR} rate ({len(wrong)} deviation(s)):{_show_lines(wrong)}"
        print_success(f"✓ {len(GAP_DAYS)} gap days: securities and cash valued at {USD_IN_EUR[D3]}, the report's history agrees")


# =============================================================================
# 2 — THE NATIVE CASH'S SECOND LAYER: ITS OWN READING FILLS THE SAME WAY
# =============================================================================


class TestTheNativeCashFillsOnItsOwn:
    @pytest.mark.asyncio
    async def test_a_day_convert_bulk_did_not_answer_reads_the_last_rate_before_it(self, tmp_path, monkeypatch):
        """The engine's NativeCash rebuilt with the unit rates of the stored days only values every day D1..END as the
        real one does: ``_rate_at`` reads the last rate on or before the day, as ``convert_bulk`` does. Before P3 this
        layer was masked end to end (``compute_native_cash`` asked every day and ``convert_bulk`` filled each); since P3
        the real one reads its steps only, so it is read end to end too; here it stands alone, on a plain dict."""
        print_section("MF-J1-8a: NativeCash with the stored days' rates only reads the gap as convert_bulk does")
        reading = await _read_the_book(tmp_path, monkeypatch)
        native_cash = reading.native_cash
        broker_id = reading.book.broker_id
        sparse_rates = {key: rate for key, rate in native_cash.unit_rates.items() if key[1] in USD_IN_EUR}
        assert {day for currency, day in sparse_rates if currency == USD} == set(USD_IN_EUR), f"precondition: the engine's NativeCash has unit rates on the stored days {_show_days(USD_IN_EUR)}, it has them on {_show_days(day for _currency, day in sparse_rates)}"
        sparse = NativeCash(report_currency=native_cash.report_currency, movements=native_cash.movements, converted=native_cash.converted, unit_rates=sparse_rates)

        wrong: list[str] = []
        for day in FRAME_DAYS:
            expected = _usd_cash(day) * _last_usable_rate(day)
            real, rebuilt = _value_at(native_cash, day, broker_id), _value_at(sparse, day, broker_id)
            if (real, rebuilt) != (expected, expected):
                wrong.append(f"{day}{' (gap)' if day in GAP_DAYS else ''}: rebuilt {rebuilt}, real {real}, expected {_usd_cash(day)} USD × {_last_usable_rate(day)} = {expected}")
        assert not wrong, f"the native cash's own reading does not fill a day without a unit rate from the last rate before it ({len(wrong)} deviation(s)):{_show_lines(wrong)}"
        print_success(f"✓ {len(FRAME_DAYS)} days valued alike with {len(sparse_rates)} unit rates and with {len(native_cash.unit_rates)}")


# =============================================================================
# 3 — BEFORE THE FIRST RATE: NEITHER READER HAS ONE
# =============================================================================


class TestBeforeTheFirstRate:
    @pytest.mark.asyncio
    async def test_neither_reader_has_a_rate_before_the_first_stored_one(self, tmp_path, monkeypatch):
        """A USD DEPOSIT on EARLY_DAY, before the first stored rate (D1): no rate on 02-27..02-29 in either map; the
        native cash leaves the deposit out (not converted, reported missing) and the engine too (``missing_fx`` names
        the day, the cash on D1 is the D1 deposit alone)."""
        print_section("MF-J1-8a: before the first stored rate neither reader has one, and neither counts the movement")
        reading = await _read_the_book(tmp_path, monkeypatch, early_deposit=True)
        engine_rates, native_rates = reading.engine_rates(), reading.native_rates()
        native_cash = reading.native_cash
        before = _days(EARLY_DAY, D1 - timedelta(days=1))

        wrong: list[str] = []
        for reader, rates in (("engine", engine_rates), ("native cash", native_rates)):
            early = [day for day in before if day in rates]
            if early:
                wrong.append(f"{reader} has a {PAIR} rate before the first stored one on {_show_days(early)}")
            if rates.get(D1) != USD_IN_EUR[D1]:
                wrong.append(f"{reader} reads {rates.get(D1)} on D1 {D1}, the first stored rate is {USD_IN_EUR[D1]}")
        early_movements = [(movement, converted) for movement, converted in zip(native_cash.movements, native_cash.converted, strict=True) if movement.date == EARLY_DAY and movement.broker_id == reading.book.broker_id]
        if [(movement.transaction_type, movement.amount, converted) for movement, converted in early_movements] != [("DEPOSIT", Decimal("500"), None)]:
            wrong.append(f"native cash: the early deposit is {early_movements}, expected one DEPOSIT of 500 USD with no conversion")
        missing = native_cash.missing_conversions()
        if missing != [MissingCashConversion(pair=PAIR, dates=(EARLY_DAY,))]:
            wrong.append(f"native cash: missing conversions {missing}, expected {PAIR} on {EARLY_DAY} alone")
        if EARLY_DAY not in reading.result.missing_fx.get(PAIR, set()):
            wrong.append(f"engine: missing_fx {reading.result.missing_fx} does not name {PAIR} on {EARLY_DAY}")
        cash_on_d1 = _usd_cash(D1) * USD_IN_EUR[D1]
        native_on_d1 = _value_at(native_cash, D1, reading.book.broker_id)
        state_on_d1 = reading.states().get(D1)
        if native_on_d1 != cash_on_d1 or state_on_d1 is None or state_on_d1.cash_value != cash_on_d1:
            wrong.append(f"cash on D1 {D1}: native cash {native_on_d1}, state {state_on_d1.cash_value if state_on_d1 else 'none'}, expected {_usd_cash(D1)} USD × {USD_IN_EUR[D1]} = {cash_on_d1} (the early 500 not counted)")
        assert not wrong, f"before the first stored {PAIR} rate the two readers do not agree on «no rate» ({len(wrong)} deviation(s)):{_show_lines(wrong)}"
        print_success(f"✓ no rate in either reader on {_show_days(before)}; the early deposit counted by neither")
