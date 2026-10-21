"""P3 of MF's fast formulas (workstream MF, release 1.3) — the portfolio engine and the native cash read X's unit-rate
steps instead of asking ``convert_bulk`` for every day: the same rates, digit and exponent, on the same days, at a cost
that no longer grows with the range. Pinned on a real database.

The developer's rule: «è imperativo non sbagliare i calcoli, veloci sì, ma precisi».

Today (HEAD ``2f4ab1962``):
- ``PortfolioCalculationEngine._preload_fx_rates`` collects ``(currency, day)`` needs — transaction amounts at their date,
  priced outgoing ADJUSTMENTs at their date (dropped from the oracle by N78-1: such a row has no value), external cash flows, price and asset currencies on every day of
  ``[date_from, date_to]``, TRANSFER legs before the range, in-transit cash on every day of the transit from
  ``max(start, EARLIEST_RANGE_START)``, in-transit cost at the arrival — asks ``convert_bulk`` one unit of each, and
  returns ``fx_rate_map[(currency, target, day)]`` holding the answered needs. ``DailyStateBuilder`` reads it with
  ``.get`` at the exact day.
- ``compute_native_cash`` asks ``convert_bulk`` for every foreign movement at its date plus one unit of each foreign
  currency on every day (``_unit_requests``), and builds ``NativeCash(unit_rates={(currency, day): rate})``.

The cure (MF, written after these reds): the engine builds windows per currency (the range as one window, single days as
``(d, d)``, the transit from ``max(start, floor)``), makes ONE ``unit_rate_steps`` call and NO ``convert_bulk`` call, and
returns ``AskedDayRates(steps, windows)`` (``{}`` when nothing is needed). The native cash keeps ``convert_bulk`` for the
movements only, asks the same days as windows in one ``unit_rate_steps`` call, and its ``unit_rates`` is the view
(``fixed_destination`` = the report currency).

The contract chosen for the engine (asked of the test author): NO ``convert_bulk`` call at all. A single day is a
``(d, d)`` window and costs one step, the same as one ``convert_bulk`` item; one reader means one source for every
``(currency, day)`` — two readers would need a rule for a day both answer — and X's oracle already proves the steps are
``convert_bulk``'s answers. The native cash is different: a movement's amount must keep ``convert_bulk``'s own
arithmetic (``amount / rate`` is not ``amount × (1 / rate)`` to the last digit), so its amounts stay there.

The book of the direct calls (``_preload_fx_rates`` and ``compute_native_cash`` on a private SQLite file), report EUR:
- EUR/USD, stored inverted for USD→EUR: an anchor five weeks before the range (2024-01-26), a legacy 0 on the would-be
  anchor (2024-03-01), the same rate on 03-05 and 03-06, then a gap 03-07..03-24 holding three legacy rows (1E-19 on
  03-10, 1E+19 on 03-15, inf on 03-20: outside ``usable_fx_rate_bounds()``), rows again from 03-25, one after the range;
- CHF/EUR, stored direct: rows on 02-01, 03-15, 04-10, a legacy inf on 04-01;
- EUR/GBP, stored inverted: first row 03-20, after GBP's first need (03-08, 03-10); JPY has no row at all;
- every rate has a long inverse (1 / 1.0837 = 0.9227646027498385161945187783): another arithmetic shows in ``as_tuple()``.
The native cash's book sits around ``EARLIEST_RANGE_START`` (1900-01-01): movements before it (single-day windows), a
stored rate strictly between two of its windows, GBP's first rate after its first movement, legacy rows.

The report's book (``PortfolioService.get_report`` on a private file, 8a's way): two brokers, a USD and a CHF stock,
deposits in USD, CHF, EUR, GBP (one before GBP's first rate), a cash transfer in transit across the USD gap, trades,
a dividend, fees on legacy-row days, over 2024-03-04..04-30, on the same rates.

What is tested:

1. ``TestTheEngineMapIsConvertBulks`` — the map ``_preload_fx_rates`` returns (called directly, and recorded during a
   report as 8a's ``_Recorders`` do) equals, key for key and digit for digit, what ``convert_bulk`` answers for one unit
   on every need of today (``_fx_needs_today``, HEAD's collection copied verbatim); ``.get`` and ``in`` agree with it on
   every day from 2024-01-20 to 2024-05-15 of every currency (off the asked days: nothing). A cash transfer in transit
   entirely before the floor asks no window there and raises nothing (a window ``(floor, end)`` with ``end < floor``
   would make ``unit_rate_steps`` raise ``ValueError``).
2. ``TestTheNativeCashIsConvertBulks`` — the ``NativeCash`` of ``compute_native_cash`` (called directly, and recorded
   during the report) against a ``NativeCash`` built from the dense ``convert_bulk`` dict of today's asked days
   (``_unit_requests_today``, HEAD's copied verbatim): same ``converted``, same walk of ``unit_rates``, same ``value_at``
   on every day, same ``rate_change_days`` and ``exchange_results`` — with ``rates_until`` after the last movement, before
   a currency's first movement (no window for it: ``unit_rate_steps`` raises on a window that ends before it starts), and
   None.
3. ``TestTheReportIsBitIdentical`` — the whole report (summary with breakdown, history, positions contribution, broker
   P&L history, P&L candles, income, cost, deposit histories, acquisition funding) computed by the product and computed
   with HEAD's dense readers (``_preload_fx_rates_today``, ``_compute_native_cash_today``, verbatim) patched in: every
   field equal, every Decimal by ``as_tuple()``.
4. ``TestTheCost`` — ``_preload_fx_rates`` hands ``convert_bulk`` nothing and calls ``unit_rate_steps`` once, with
   windows covering exactly today's needs; its work (``convert_bulk`` items + steps returned) does not grow when the range
   grows from 30 to 3000 days; ``compute_native_cash`` hands ``convert_bulk`` the foreign movements only, calls
   ``unit_rate_steps`` once with windows covering exactly today's asked days, and its work (items + steps + the days of
   ``NativeCash._rate_days``) does not grow when ``rates_until`` moves from 30 to 3000 days after the last movement.
   Nothing to convert: no call at all (guards).

RED on HEAD 2f4ab1962 — the cost only: ``TestTheCost``'s five cost tests (``convert_bulk`` is handed one unit per day,
``unit_rate_steps`` is never called, the work grows ~100× with the range). GREEN on HEAD, guards the cure must keep green:
``TestTheEngineMapIsConvertBulks``, ``TestTheNativeCashIsConvertBulks``, ``TestTheReportIsBitIdentical`` (today's readers
ARE the oracle), the «nothing to convert» guard (engine and native cash) and the oracles' own guard
(``test_the_oracles_are_copies_of_head``).

Mutants, measured before the hand-over on a scratch reference cure (a temporary ``AskedDayRates`` and engine/native-cash
change written only to check these tests, never the product): green 15/15 on it; each mutant below turns red the tests
named, and only on this file's own evidence:
- the view not limited to the windows: the three engine-map tests (``.get`` off the asked days). The report's own output
  does not move on this book: the recorded map is what catches it;
- windows not merged: both engine maps and the bit-identical report;
- a range window starting a day late / ending a day early: both engine maps and the windows test (the early end also
  the report);
- a transit window started before the floor: the pre-floor transit test (the other books have no row before the floor);
- single days of transactions not asked: both engine maps, the windows test, the pre-floor transit, the report (the GBP
  fee of 2024-04-12 is asked by the transaction source alone);
- the native calendar missing a currency's first step: both native-cash tests;
- ``step_series`` dropping the anchor step: both native-cash tests and the report;
- the native cash's early single days not asked: the floor book and the native windows test.

Re-measured on MF's cure (2026-10-20, a scratch copy of HEAD 2f4ab1962 + the cure): green 15/15, and every mutant above
turns red the same tests. Two more, of the callers' guards: the engine asking a transit window that ends before it
starts (a transit wholly before the floor) — the pre-floor transit test, as ``unit_rate_steps`` raises; the native cash
asking one for a currency whose first movement comes after ``rates_until`` — the floor book with ``rates_until``
1900-01-04. A fill limit in either door of the FX service alone (``convert_bulk`` or ``unit_rate_steps``) turns 8 tests
red: the oracle and the product no longer read one rule.

Isolation: PURE with respect to the lane — every database is a private SQLite file under ``tmp_path`` (the app schema,
``SQLModel.metadata.create_all``, NullPool, disposed at teardown); no lane database, no server, no network. Legacy rates
are planted with raw SQL past the model and read back. The report, WAC and engine blob caches are emptied around each
test; every patch goes through ``monkeypatch``. No sleep, no wall-clock assertion, no translated text.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory); alone:
``./dev.py test services roi-fifo-utils test_fx_steps_service_parity``.

Reference: backend/app/services/fx/conversion.py (convert_bulk, unit_rate_steps), backend/app/services/financial_math/
portfolio/engine.py (_preload_fx_rates), backend/app/services/financial_math/native_cash.py (compute_native_cash,
_unit_requests, NativeCash), backend/test_scripts/test_services/test_financial/test_fx_gap_single_reading.py (8a's book
and recorders), backend/test_scripts/test_services/test_financial_math/test_asked_day_rates.py (the view, pure).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.native_cash as native_cash_module
import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all; and the session module's PRAGMA listener
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.precision import usable_fx_rate_bounds
from backend.app.schemas.common import Currency, OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.native_cash import CashMovement, NativeCash
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, InTransitInterval
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.portfolio_service import PortfolioService
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START
from backend.test_scripts.test_utils import print_section, print_success

Pair = tuple[str, str]
Window = tuple[date, date]

EUR, USD, CHF, GBP, JPY = "EUR", "USD", "CHF", "GBP", "JPY"
FLOOR = EARLIEST_RANGE_START

#: The real functions, taken before any patch: the recorders delegate to them, the oracles call them.
REAL_CONVERT_BULK = fx_conversion.convert_bulk
REAL_UNIT_RATE_STEPS = fx_conversion.unit_rate_steps
REAL_PRELOAD = PortfolioCalculationEngine._preload_fx_rates
REAL_COMPUTE_NATIVE_CASH = native_cash_module.compute_native_cash

START = date(2024, 3, 4)
END = date(2024, 4, 30)
PROBE_FIRST, PROBE_LAST = date(2024, 1, 20), date(2024, 5, 15)

#: Usable rows, as ``fx_rates`` keeps them (base < quote): (base, quote, day, rate).
MAIN_ROWS: tuple[tuple[str, str, date, str], ...] = (
    (EUR, USD, date(2024, 1, 26), "1.0837"),  # the anchor, five weeks before the range
    (EUR, USD, date(2024, 3, 5), "1.0912345678"),
    (EUR, USD, date(2024, 3, 6), "1.0912345678"),  # the same rate, the next day
    (EUR, USD, date(2024, 3, 25), "1.0612345678"),
    (EUR, USD, date(2024, 3, 28), "1.1"),
    (EUR, USD, date(2024, 4, 2), "1.0837"),
    (EUR, USD, date(2024, 4, 9), "1.0723456789"),
    (EUR, USD, date(2024, 4, 16), "1.1"),
    (EUR, USD, date(2024, 4, 23), "1.0899999999"),
    (EUR, USD, date(2024, 4, 29), "1.0837"),
    (EUR, USD, date(2024, 5, 6), "1.3"),  # after the range
    (CHF, EUR, date(2024, 2, 1), "1.0234567891"),
    (CHF, EUR, date(2024, 3, 15), "1.05"),
    (CHF, EUR, date(2024, 4, 10), "0.9876543210"),
    (EUR, GBP, date(2024, 3, 20), "0.8571234567"),
    (EUR, GBP, date(2024, 4, 18), "0.86"),
)
#: Legacy rows an older release could leave, outside ``usable_fx_rate_bounds()``: planted with raw SQL.
MAIN_LEGACY: tuple[tuple[str, str, date, float], ...] = (
    (EUR, USD, date(2024, 3, 1), 0.0),  # on the would-be anchor of the range
    (EUR, USD, date(2024, 3, 10), 1e-19),
    (EUR, USD, date(2024, 3, 15), 1e19),
    (EUR, USD, date(2024, 3, 20), float("inf")),
    (CHF, EUR, date(2024, 4, 1), float("inf")),
)

#: The native cash's book: around the floor.
NATIVE_ROWS: tuple[tuple[str, str, date, str], ...] = (
    (EUR, USD, date(1899, 10, 15), "1.25"),
    (EUR, USD, date(1899, 12, 20), "1.0837"),  # strictly between the two early windows (11-20 and 12-25)
    (EUR, USD, date(1900, 1, 10), "1.3333333333"),
    (EUR, USD, date(1900, 2, 1), "1.0912345678"),
    (EUR, USD, date(1900, 2, 2), "1.0912345678"),
    (EUR, USD, date(1900, 3, 15), "1.1"),
    (CHF, EUR, date(1899, 6, 1), "1.0234567891"),
    (CHF, EUR, date(1900, 1, 25), "1.05"),
    (CHF, EUR, date(1900, 3, 22), "1.01"),
    (EUR, GBP, date(1900, 1, 12), "0.8571234567"),
    (EUR, GBP, date(1900, 2, 20), "0.86"),
)
NATIVE_LEGACY: tuple[tuple[str, str, date, float], ...] = (
    (EUR, USD, date(1899, 12, 24), 1e19),
    (EUR, USD, date(1900, 1, 20), 0.0),
    (CHF, EUR, date(1900, 3, 20), float("inf")),
)
NATIVE_RATES_UNTIL = date(1900, 3, 31)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _show(lines: list[str], shown: int = 12) -> str:
    more = f"\n  … and {len(lines) - shown} more" if len(lines) > shown else ""
    return "\n  " + "\n  ".join(lines[:shown]) + more


def _bits(value: object) -> object:
    """None, or a Decimal's sign, digits and exponent: ``==`` alone takes 1.0837 for 1.0837000000."""
    if value is None:
        return None
    if type(value) is Decimal:
        return value.as_tuple()
    return (type(value).__name__, repr(value))


def _deep_bits(value: object) -> object:
    """Any nested value with every Decimal as ``as_tuple()``: what the bit-identical report compares."""
    if isinstance(value, BaseModel):
        return _deep_bits(value.model_dump())
    if isinstance(value, Decimal):
        return ("Decimal", value.as_tuple())
    if isinstance(value, dict):
        return {key: _deep_bits(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_bits(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_deep_bits(item) for item in value), key=repr)
    return value


def _differences(left: object, right: object, path: str = "report") -> list[str]:
    """The paths where two ``_deep_bits`` trees differ."""
    if type(left) is not type(right):
        return [f"{path}: {left!r} vs {right!r}"]
    if isinstance(left, dict):
        found = [f"{path}.{key}: only on one side" for key in sorted(set(left) ^ set(right), key=repr)]
        for key in sorted(set(left) & set(right), key=repr):
            found += _differences(left[key], right[key], f"{path}.{key}")
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{path}: {len(left)} items vs {len(right)}"]
        found = []
        for index, (item_left, item_right) in enumerate(zip(left, right, strict=True)):
            found += _differences(item_left, item_right, f"{path}[{index}]")
        return found
    return [] if left == right else [f"{path}: {left!r} vs {right!r}"]


# =============================================================================
# THE ORACLES OF TODAY — HEAD 2f4ab1962, VERBATIM
# =============================================================================


def _fx_needs_today(  # noqa: C901 — HEAD's collection loops, copied as they are
    classified_txs: list[ClassifiedTransaction],
    in_transit_intervals: list[InTransitInterval],
    external_cash_flows: list[tuple[date, int, Decimal, str]],
    price_map: dict[int, list[tuple[date, Decimal, str]]],
    asset_currencies: dict[int, str],
    target_currency: str,
    date_from: date,
    date_to: date,
) -> set[tuple[str, date]]:
    """Every ``(currency, day)`` HEAD's ``_preload_fx_rates`` asks ``convert_bulk`` for: its collection, verbatim."""
    fx_needs: set[tuple[str, date]] = set()
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.amount and tx.amount != 0 and tx.currency and tx.currency != target_currency:
            fx_needs.add((tx.currency, tx.date))
    # N78-1 (the developer's decision, 21/10/2026): an outgoing ADJUSTMENT has no value, so the value it may store is never
    # converted and is no need. HEAD 2f4ab1962 asked (cost currency, row date) for each one (J-24); that loop is gone from
    # this oracle, which follows the rule and no longer HEAD alone (RED until the cure on the book's two such rows).
    for dt, _, _, ccy in external_cash_flows:
        if ccy != target_currency:
            fx_needs.add((ccy, dt))
    price_currencies: set[str] = set()
    for prices in price_map.values():
        for _, _, ccy in prices:
            if ccy != target_currency:
                price_currencies.add(ccy)
    asset_ccys_non_target: set[str] = set()
    for ccy in asset_currencies.values():
        if ccy != target_currency:
            asset_ccys_non_target.add(ccy)
    all_non_target_ccys = price_currencies | asset_ccys_non_target
    if all_non_target_ccys:
        current = date_from
        while current <= date_to:
            for ccy in all_non_target_ccys:
                fx_needs.add((ccy, current))
            current += timedelta(days=1)
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.type != TransactionType.TRANSFER or tx.asset_id is None or not tx.quantity or tx.date >= date_from:
            continue
        leg_ccys = {ccy for _, _, ccy in price_map.get(tx.asset_id, [])}
        asset_ccy = asset_currencies.get(tx.asset_id)
        if asset_ccy:
            leg_ccys.add(asset_ccy)
        for ccy in leg_ccys:
            if ccy != target_currency:
                fx_needs.add((ccy, tx.date))
    for interval in in_transit_intervals:
        dep = interval.departure_leg
        if interval.tx_type == "cash" and dep.currency and dep.currency != target_currency:
            current = max(interval.start_date, EARLIEST_RANGE_START)
            while current <= interval.end_date:
                fx_needs.add((dep.currency, current))
                current += timedelta(days=1)
        if interval.cost_basis_currency and interval.cost_basis_currency != target_currency:
            fx_needs.add((interval.cost_basis_currency, interval.arrival_leg.date))
    return fx_needs


def _unit_requests_today(foreign: Sequence[CashMovement], rates_until: date | None) -> list[tuple[str, date]]:
    """HEAD's ``native_cash._unit_requests``, verbatim."""
    first: dict[str, date] = {}
    last: dict[str, date] = {}
    early: dict[str, set[date]] = {}
    for movement in foreign:
        currency = movement.currency
        if currency not in first or movement.date < first[currency]:
            first[currency] = movement.date
        if currency not in last or movement.date > last[currency]:
            last[currency] = movement.date
        if movement.date < EARLIEST_RANGE_START:
            early.setdefault(currency, set()).add(movement.date)
    requests: list[tuple[str, date]] = []
    for currency in sorted(first):
        requests.extend((currency, day) for day in sorted(early.get(currency, ())))
        day = max(first[currency], EARLIEST_RANGE_START)
        end = last[currency] if rates_until is None else rates_until
        while day <= end:
            requests.append((currency, day))
            day += timedelta(days=1)
    return requests


async def _units_by_convert_bulk(session: AsyncSession, needs: Iterable[tuple[str, date]], target: str) -> dict[tuple[str, str, date], Decimal]:
    """One unit of each ``(currency, day)`` in ``target`` by the real ``convert_bulk``: the answered ones."""
    needs = sorted(needs)
    results, _errors = await REAL_CONVERT_BULK(session, [(Currency(code=currency, amount=Decimal("1")), target, day) for currency, day in needs], raise_on_error=False)
    assert len(results) == len(needs), f"the oracle itself is wrong: {len(results)} answers for {len(needs)} needs"
    return {(currency, target, day): result[0].amount for (currency, day), result in zip(needs, results, strict=True) if result is not None}


async def _preload_fx_rates_today(self, classified_txs, in_transit_intervals, external_cash_flows, price_map, asset_currencies, target_currency, date_from, date_to):
    """HEAD's ``_preload_fx_rates``: its needs, one ``convert_bulk``, the answered ones in a dict."""
    fx_needs = _fx_needs_today(classified_txs, in_transit_intervals, external_cash_flows, price_map, asset_currencies, target_currency, date_from, date_to)
    if not fx_needs:
        return {}
    return await _units_by_convert_bulk(self.db, fx_needs, target_currency)


async def _compute_native_cash_today(session: Any, movements: Sequence[CashMovement], *, report_currency: str, rates_until: date | None = None) -> NativeCash:
    """HEAD's ``compute_native_cash``, verbatim but for the names: one ``convert_bulk`` for the amounts and the unit days,
    a plain dict of unit rates."""
    movements = tuple(movements)
    amount_indexes = [index for index, movement in enumerate(movements) if movement.currency != report_currency and movement.amount != 0]
    if not amount_indexes:
        return NativeCash(report_currency=report_currency, movements=movements, converted=tuple(movement.amount for movement in movements), unit_rates={})
    unit_requests = _unit_requests_today([movements[index] for index in amount_indexes], rates_until)
    requests = [(Currency(code=movements[index].currency, amount=movements[index].amount), report_currency, movements[index].date) for index in amount_indexes]
    requests += [(Currency(code=currency, amount=Decimal("1")), report_currency, day) for currency, day in unit_requests]
    results, _errors = await REAL_CONVERT_BULK(session, requests, raise_on_error=False)

    def _result(position: int) -> Decimal | None:
        result = results[position] if position < len(results) else None
        return None if result is None else result[0].amount

    converted: list[Decimal | None] = [movement.amount for movement in movements]
    for position, index in enumerate(amount_indexes):
        converted[index] = _result(position)
    unit_rates: dict[tuple[str, date], Decimal] = {}
    offset = len(amount_indexes)
    for position, key in enumerate(unit_requests):
        rate = _result(offset + position)
        if rate is not None:
            unit_rates[key] = rate
    return NativeCash(report_currency=report_currency, movements=movements, converted=tuple(converted), unit_rates=unit_rates)


# =============================================================================
# PRIVATE DATABASES
# =============================================================================


async def _plant_rates(engine: AsyncEngine, rows: Iterable[tuple[str, str, date, str]], legacy: Iterable[tuple[str, str, date, float]]) -> None:
    """The usable rows through the model, as the app stores a rate; the legacy rows with raw SQL past it, read back."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([FxRate(date=day, base=base, quote=quote, rate=Decimal(rate), source="P3-STEPS") for base, quote, day, rate in rows])
        await session.commit()
    legacy = list(legacy)
    smallest, first_refused = usable_fx_rate_bounds()
    async with engine.begin() as connection:
        for base, quote, day, rate in legacy:
            assert not (smallest <= Decimal(str(rate)) < first_refused), f"the fixture itself is wrong: the legacy rate {rate} is usable"
            await connection.execute(
                text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"),
                {"day": day.isoformat(), "base": base, "quote": quote, "rate": rate, "source": "P3-LEGACY"},
            )
        stored = sorted((row[0], row[1], row[2], float(row[3])) for row in (await connection.execute(text("SELECT base, quote, date, rate FROM fx_rates WHERE source = 'P3-LEGACY'"))).all())
        planted = sorted((base, quote, day.isoformat(), rate) for base, quote, day, rate in legacy)
        assert stored == planted, f"the fixture itself is wrong: raw SQL reads back {stored}, not the legacy rows planted {planted}"


@asynccontextmanager
async def _private_engine(directory: Path, name: str) -> AsyncIterator[AsyncEngine]:
    """The app schema on a private SQLite file under ``directory``; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / f'p3_{name}.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@asynccontextmanager
async def _rated_session(directory: Path, rows, legacy, name: str) -> AsyncIterator[AsyncSession]:
    async with _private_engine(directory, name) as engine:
        await _plant_rates(engine, rows, legacy)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request):
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# WHAT THE FX SERVICE WAS ASKED
# =============================================================================


@dataclass
class _FxCalls:
    """Every ``convert_bulk`` and ``unit_rate_steps`` call while recording: items, windows and the steps answered."""

    bulk: list[list[tuple[str, Decimal, str, date]]] = field(default_factory=list)
    steps_requests: list[dict[Pair, list[Window]]] = field(default_factory=list)
    steps_answers: list[Mapping[Pair, Any]] = field(default_factory=list)

    @property
    def bulk_items(self) -> list[tuple[str, Decimal, str, date]]:
        return [item for call in self.bulk for item in call]

    @property
    def step_days(self) -> int:
        return sum(len(steps.days) for answer in self.steps_answers for steps in answer.values())

    def asked_days(self) -> dict[Pair, set[date]]:
        """The days of every window of every ``unit_rate_steps`` call, by pair."""
        days: dict[Pair, set[date]] = {}
        for request in self.steps_requests:
            for pair, windows in request.items():
                for first, last in windows:
                    days.setdefault(pair, set()).update(_days(first, last))
        return days


def _record_fx(monkeypatch: pytest.MonkeyPatch, module: Any) -> _FxCalls:
    """Recorders on ``convert_bulk`` and ``unit_rate_steps``, on ``module`` (which may not import them yet: added) and on
    the FX service, each delegating to the real function. Windows are read once, as lists, before the delegation."""
    calls = _FxCalls()

    async def bulk(session, conversions, raise_on_error=True):
        conversions = list(conversions)
        calls.bulk.append([(amount.code, amount.amount, to_currency, day) for amount, to_currency, day in conversions])
        return await REAL_CONVERT_BULK(session, conversions, raise_on_error=raise_on_error)

    async def steps(session, requests):
        materialized = {pair: list(windows) for pair, windows in requests.items()}
        calls.steps_requests.append(materialized)
        answer = await REAL_UNIT_RATE_STEPS(session, materialized)
        calls.steps_answers.append(answer)
        return answer

    monkeypatch.setattr(module, "convert_bulk", bulk, raising=False)
    monkeypatch.setattr(module, "unit_rate_steps", steps, raising=False)
    monkeypatch.setattr(fx_conversion, "convert_bulk", bulk)
    monkeypatch.setattr(fx_conversion, "unit_rate_steps", steps)
    return calls


# =============================================================================
# THE ENGINE'S INPUTS, BUILT BY HAND
# =============================================================================


def _tx(tx_id: int, tx_type: TransactionType, day: date, *, amount: str | None = None, currency: str | None = None, asset_id: int | None = None, quantity: str = "0", broker_id: int = 1, cbo: str | None = None, cbo_ccy: str | None = None) -> Transaction:
    """A transaction row as the engine reads it (never persisted)."""
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = broker_id
    tx.asset_id = asset_id
    tx.type = tx_type
    tx.date = day
    tx.quantity = Decimal(quantity)
    tx.amount = None if amount is None else Decimal(amount)
    tx.currency = currency
    tx.cost_basis_override = None if cbo is None else Decimal(cbo)
    tx.cost_basis_currency = cbo_ccy
    tx.related_transaction_id = None
    tx.updated_at = day
    return tx


def _classified(*txs: Transaction) -> list[ClassifiedTransaction]:
    return [ClassifiedTransaction(tx=tx, classification="normal") for tx in txs]


def _interval(tx_type: str, departure: Transaction, arrival: Transaction, *, cost_currency: str | None = None) -> InTransitInterval:
    return InTransitInterval(
        start_date=departure.date,
        end_date=arrival.date - timedelta(days=1),
        tx_type=tx_type,
        departure_leg=departure,
        arrival_leg=arrival,
        share=Decimal("1"),
        asset_id=departure.asset_id,
        cost_basis_amount=None if cost_currency is None else Decimal("80"),
        cost_basis_currency=cost_currency,
    )


def _main_inputs(date_from: date = START, date_to: date = END) -> dict[str, Any]:
    """Every source of need of ``_preload_fx_rates``: amounts on legacy-row and gap days, outgoing ADJUSTMENTs storing a
    value (the asset's currency, then GBP before its first rate: no need since N78-1, they have no value), a TRANSFER leg before the range, external flows, price currencies
    (USD, CHF, GBP for an EUR asset), a cash transit across the USD gap, one past ``date_to``, an in-transit cost in CHF
    arriving after the range, a JPY fee (no rate at all), an EUR deposit (nothing to ask)."""
    txs = _classified(
        _tx(1, TransactionType.DEPOSIT, date(2024, 2, 20), amount="10000", currency=USD),
        _tx(2, TransactionType.BUY, date(2024, 3, 12), amount="-1000", currency=USD, asset_id=1, quantity="10"),
        _tx(3, TransactionType.DEPOSIT, date(2024, 3, 10), amount="500", currency=GBP),
        _tx(4, TransactionType.BUY, date(2024, 3, 5), amount="-300", currency=CHF, asset_id=2, quantity="3"),
        _tx(5, TransactionType.ADJUSTMENT, date(2024, 2, 25), asset_id=1, quantity="-2", cbo="50"),
        _tx(6, TransactionType.ADJUSTMENT, date(2024, 3, 8), asset_id=1, quantity="-1", cbo="60", cbo_ccy=GBP),
        _tx(7, TransactionType.TRANSFER, date(2024, 2, 28), asset_id=1, quantity="-1"),
        _tx(8, TransactionType.DIVIDEND, date(2024, 4, 15), amount="20", currency=CHF, asset_id=2),
        _tx(9, TransactionType.FEE, date(2024, 3, 1), amount="-5", currency=USD),
        _tx(10, TransactionType.FEE, date(2024, 4, 3), amount="-100", currency=JPY),
        _tx(11, TransactionType.DEPOSIT, date(2024, 3, 4), amount="1000", currency=EUR),
    )
    intervals = [
        _interval("cash", _tx(20, TransactionType.CASH_TRANSFER, date(2024, 3, 8), amount="-400", currency=USD), _tx(21, TransactionType.CASH_TRANSFER, date(2024, 3, 28), amount="400", currency=USD, broker_id=2)),
        _interval("cash", _tx(22, TransactionType.CASH_TRANSFER, date(2024, 4, 25), amount="-300", currency=USD), _tx(23, TransactionType.CASH_TRANSFER, date(2024, 5, 10), amount="300", currency=USD, broker_id=2)),
        _interval("asset", _tx(24, TransactionType.TRANSFER, date(2024, 4, 20), asset_id=2, quantity="-1"), _tx(25, TransactionType.TRANSFER, date(2024, 5, 2), asset_id=2, quantity="1", broker_id=2), cost_currency=CHF),
    ]
    return {
        "classified_txs": txs,
        "in_transit_intervals": intervals,
        "external_cash_flows": [(date(2024, 3, 18), 1, Decimal("200"), USD), (date(2024, 4, 2), 1, Decimal("50"), GBP)],
        "price_map": {
            1: [(date(2024, 2, 20), Decimal("100"), USD), (date(2024, 3, 5), Decimal("101"), USD)],
            2: [(date(2024, 2, 22), Decimal("50"), CHF)],
            3: [(date(2024, 3, 4), Decimal("7"), GBP)],
        },
        "asset_currencies": {1: USD, 2: CHF, 3: EUR},
        "target_currency": EUR,
        "date_from": date_from,
        "date_to": date_to,
    }


def _probe_keys(currencies: Iterable[str], target: str, first: date = PROBE_FIRST, last: date = PROBE_LAST) -> list[tuple[str, str, date]]:
    return [(currency, target, day) for currency in sorted(currencies) for day in _days(first, last)]


def _map_problems(fx_map: Mapping, expected: Mapping, probes: Iterable) -> list[str]:
    """The engine's map against ``convert_bulk``'s answers on today's needs: its walk, and ``.get``/``in`` on every
    probe (absent where today has no entry)."""
    problems: list[str] = []
    walked = {key: _bits(value) for key, value in fx_map.items()}
    wanted = {key: _bits(value) for key, value in expected.items()}
    if walked != wanted:
        missing, extra = sorted(set(wanted) - set(walked)), sorted(set(walked) - set(wanted))
        differing = sorted(key for key in set(wanted) & set(walked) if wanted[key] != walked[key])
        problems.append(f"the map's walk is not convert_bulk's answers on today's needs: {len(missing)} missing {missing[:4]}, {len(extra)} extra {extra[:4]}, {len(differing)} differing {[(key, walked[key], wanted[key]) for key in differing[:2]]}")
    for key in sorted(set(probes) | set(expected)):
        got, want = fx_map.get(key), expected.get(key)
        if _bits(got) != _bits(want):
            problems.append(f".get({key}) is {got!r}, convert_bulk on today's needs gives {want!r}")
        elif (key in fx_map) != (key in expected):
            problems.append(f"{key} in the map is {key in fx_map}, today {key in expected}")
    return problems


# =============================================================================
# THE NATIVE CASH'S BOOK
# =============================================================================


def _move(day: date, currency: str, amount: str, broker_id: int = 1, *, kind: str = "DEPOSIT", share: str = "1", asset_id: int | None = None) -> CashMovement:
    return CashMovement(movement_id=None, transaction_type=kind, date=day, broker_id=broker_id, asset_id=asset_id, currency=currency, amount=Decimal(amount), share=Decimal(share))


def _native_movements() -> list[CashMovement]:
    """USD before the floor (1899-11-20, 1899-12-25: single-day windows, the 1899-12-20 row between them) and after it;
    GBP before its first rate (1900-01-03, not converted) and after (1900-02-10); CHF; a zero USD fee; an EUR deposit."""
    return [
        _move(date(1899, 11, 1), USD, "0.00", kind="FEE"),
        _move(date(1899, 11, 20), USD, "1000.00"),
        _move(date(1899, 12, 25), USD, "-200", kind="WITHDRAWAL"),
        _move(date(1900, 1, 3), GBP, "700"),
        _move(date(1900, 1, 5), CHF, "500", broker_id=2),
        _move(date(1900, 1, 15), EUR, "50.0", broker_id=3),
        _move(date(1900, 1, 20), USD, "300", broker_id=2, share="0.5"),
        _move(date(1900, 2, 10), GBP, "100", kind="DIVIDEND", asset_id=7),
        _move(date(1900, 3, 1), USD, "-100", kind="FEE"),
    ]


async def _dense_native_cash(session: AsyncSession, movements: Sequence[CashMovement], report_currency: str, rates_until: date | None) -> tuple[NativeCash, dict[tuple[str, date], Decimal]]:
    """The oracle: today's ``compute_native_cash`` on the same session — the dense dict of today's asked days."""
    built = await _compute_native_cash_today(session, movements, report_currency=report_currency, rates_until=rates_until)
    return built, dict(built.unit_rates)


def _outcome(call) -> object:
    try:
        answer = call()
    except ValueError as error:
        return ("raises", type(error).__name__)
    if isinstance(answer, dict):
        return {key: _bits(value) for key, value in answer.items()}
    return answer


def _native_problems(cash: NativeCash, dense_cash: NativeCash, frame: list[date], label: str) -> list[str]:
    """``cash`` (the product's) against ``dense_cash`` (today's, from the dense dict): converted, the walk of
    ``unit_rates``, ``value_at`` on every day, ``rate_change_days`` and ``exchange_results`` on windows."""
    problems: list[str] = []
    if [_bits(value) for value in cash.converted] != [_bits(value) for value in dense_cash.converted]:
        problems.append(f"{label} converted: {cash.converted} vs today's {dense_cash.converted}")
    walked, dense = {key: _bits(value) for key, value in cash.unit_rates.items()}, {key: _bits(value) for key, value in dense_cash.unit_rates.items()}
    if walked != dense:
        problems.append(f"{label} the walk of unit_rates is not today's dict: missing {sorted(set(dense) - set(walked))[:4]}, extra {sorted(set(walked) - set(dense))[:4]}, differing {sorted(key for key in set(dense) & set(walked) if dense[key] != walked[key])[:4]}")
    problems += [f"{label} value_at({day}): {mine} vs today's {today}" for day in frame if (mine := _outcome(lambda day=day: cash.value_at(day))) != (today := _outcome(lambda day=day: dense_cash.value_at(day)))]
    windows = [(None, frame[-1]), (frame[0], frame[-1])] + [(frame[index], frame[min(index + 23, len(frame) - 1)]) for index in range(0, len(frame) - 1, 11)]
    for date_from, date_to in windows:
        if cash.rate_change_days(date_from, date_to) != dense_cash.rate_change_days(date_from, date_to):
            problems.append(f"{label} rate_change_days({date_from}, {date_to}): {list(cash.rate_change_days(date_from, date_to))} vs today's {list(dense_cash.rate_change_days(date_from, date_to))}")
        if date_from is not None and date_from < date_to and _outcome(lambda a=date_from, b=date_to: cash.exchange_results(a, b)) != _outcome(lambda a=date_from, b=date_to: dense_cash.exchange_results(a, b)):
            problems.append(f"{label} exchange_results({date_from}, {date_to}) differ")
    return problems


# =============================================================================
# THE REPORT'S BOOK
# =============================================================================


@dataclass(frozen=True)
class _ReportBook:
    engine: AsyncEngine
    user_id: int
    broker_ids: tuple[int, int]


async def _seed_report_book(engine: AsyncEngine) -> _ReportBook:
    """User U owns brokers A and B; X a USD stock priced every day, Y a CHF stock priced every third day; the rows below;
    the main rates. Every amount and quantity follows the sign rules of ``TransactionType``."""
    tag = uuid4().hex[:12]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"p3_{tag}", email=f"p3_{tag}@test.com", hashed_password="fakehash", is_active=True)
        broker_a, broker_b = Broker(name=f"P3 steps A {tag}"), Broker(name=f"P3 steps B {tag}")
        stock_x = Asset(display_name=f"P3 steps X {tag}", currency=USD, asset_type=AssetType.STOCK)
        stock_y = Asset(display_name=f"P3 steps Y {tag}", currency=CHF, asset_type=AssetType.STOCK)
        session.add_all([user, broker_a, broker_b, stock_x, stock_y])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in (broker_a, broker_b)])
        for index, day in enumerate(_days(date(2024, 2, 20), END)):
            close = Decimal("100") + Decimal(index) / 4
            session.add(PriceHistory(asset_id=stock_x.id, date=day, open=close, high=close + 1, low=close - 1, close=close, volume=Decimal("1"), currency=USD, source_plugin_key="p3_steps"))
            if index % 3 == 0:
                close_y = Decimal("50") + Decimal(index) / 10
                session.add(PriceHistory(asset_id=stock_y.id, date=day, open=close_y, high=close_y, low=close_y, close=close_y, volume=Decimal("1"), currency=CHF, source_plugin_key="p3_steps"))

        def row(broker: Broker, tx_type: TransactionType, day: date, amount: str, currency: str, asset: Asset | None = None, quantity: str = "0") -> Transaction:
            return Transaction(broker_id=broker.id, asset_id=asset.id if asset else None, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency)

        session.add_all(
            [
                row(broker_a, TransactionType.DEPOSIT, date(2024, 2, 20), "10000", USD),
                row(broker_a, TransactionType.DEPOSIT, date(2024, 2, 22), "5000", CHF),
                row(broker_a, TransactionType.DEPOSIT, START, "1000", EUR),
                row(broker_a, TransactionType.BUY, date(2024, 3, 5), "-1000", USD, stock_x, "10"),
                row(broker_a, TransactionType.DEPOSIT, date(2024, 3, 10), "300", GBP),
                row(broker_a, TransactionType.BUY, date(2024, 3, 12), "-250", CHF, stock_y, "5"),
                row(broker_a, TransactionType.FEE, date(2024, 3, 15), "-5", USD),
                row(broker_a, TransactionType.DEPOSIT, date(2024, 4, 5), "200", GBP),
                # a GBP amount that is no external flow: its day is asked by the transaction source alone
                row(broker_a, TransactionType.FEE, date(2024, 4, 12), "-3", GBP),
                row(broker_a, TransactionType.DIVIDEND, date(2024, 4, 15), "20", CHF, stock_y),
                row(broker_b, TransactionType.FEE, date(2024, 4, 20), "-5", USD),
                row(broker_a, TransactionType.SELL, date(2024, 4, 22), "460", USD, stock_x, "-4"),
            ]
        )
        sent, received = row(broker_a, TransactionType.CASH_TRANSFER, date(2024, 3, 8), "-400", USD), row(broker_b, TransactionType.CASH_TRANSFER, date(2024, 3, 28), "400", USD)
        session.add_all([sent, received])
        await session.flush()
        sent.related_transaction_id, received.related_transaction_id = received.id, sent.id
        await session.commit()
        book = _ReportBook(engine=engine, user_id=user.id, broker_ids=(broker_a.id, broker_b.id))
    await _plant_rates(engine, MAIN_ROWS, MAIN_LEGACY)
    return book


def _report_query() -> PortfolioReportQuery:
    return PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=START, end=END),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=False,
        include_breakdown=True,
        include_positions_contribution=True,
        include_broker_pnl_history=True,
        include_pnl_candles=True,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
    )


@dataclass
class _Recorded:
    """What a report handed the FX readers: each preload's arguments and map, each native cash's arguments and value."""

    preloads: list[tuple[dict[str, Any], Mapping]] = field(default_factory=list)
    native_cashes: list[tuple[dict[str, Any], NativeCash]] = field(default_factory=list)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> _Recorded:
        preload_signature, native_signature = inspect.signature(REAL_PRELOAD), inspect.signature(REAL_COMPUTE_NATIVE_CASH)
        current_preload = PortfolioCalculationEngine._preload_fx_rates
        current_engine_native, current_service_native = portfolio_engine_module.compute_native_cash, portfolio_service_module.compute_native_cash

        async def preload(engine_self, *args, **kwargs):
            fx_map = await current_preload(engine_self, *args, **kwargs)
            arguments = dict(preload_signature.bind(engine_self, *args, **kwargs).arguments)
            arguments.pop("self")
            self.preloads.append((arguments, fx_map))
            return fx_map

        def native_recorder(current):
            async def native_cash(*args, **kwargs):
                built = await current(*args, **kwargs)
                self.native_cashes.append((dict(native_signature.bind(*args, **kwargs).arguments), built))
                return built

            return native_cash

        monkeypatch.setattr(PortfolioCalculationEngine, "_preload_fx_rates", preload)
        monkeypatch.setattr(portfolio_engine_module, "compute_native_cash", native_recorder(current_engine_native))
        monkeypatch.setattr(portfolio_service_module, "compute_native_cash", native_recorder(current_service_native))
        return self


async def _report(book: _ReportBook):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, _report_query())


# =============================================================================
# 1 — THE ENGINE'S MAP IS convert_bulk'S, ON TODAY'S NEEDS ONLY
# =============================================================================


class TestTheEngineMapIsConvertBulks:
    @pytest.mark.asyncio
    async def test_the_preload_map_on_every_source_of_need(self, tmp_path):
        """``_preload_fx_rates`` called directly on every source of need: its map is ``convert_bulk``'s answers on
        today's needs, digit and exponent, and nothing on any other day of 2024-01-20..05-15 for USD, CHF, GBP, JPY."""
        print_section("P3: the engine's map, every source of need, against convert_bulk")
        inputs = _main_inputs()
        async with _rated_session(tmp_path, MAIN_ROWS, MAIN_LEGACY, "preload") as session:
            fx_map = await PortfolioCalculationEngine(session)._preload_fx_rates(**inputs)
            expected = await _units_by_convert_bulk(session, _fx_needs_today(**inputs), EUR)
        assert {key[0] for key in expected} == {USD, CHF, GBP}, f"precondition: today's answered needs cover USD, CHF and GBP, they cover {sorted({key[0] for key in expected})}"
        problems = _map_problems(fx_map, expected, _probe_keys((USD, CHF, GBP, JPY), EUR))
        assert not problems, f"the engine's map is not convert_bulk's answers on today's needs ({len(problems)} problem(s)):{_show(problems)}"
        print_success(f"✓ {len(expected)} rates, the same as convert_bulk's to the digit; nothing on an unasked day")

    @pytest.mark.asyncio
    async def test_a_transit_before_the_floor_asks_nothing_there(self, tmp_path, monkeypatch):
        """GUARD. A deposits 1000 USD on 1890-01-01; 400 USD leave A on 1890-01-02 and reach B on 1899-06-02: the transit
        ends before the floor, so today asks only the movements' own days. The cure must not ask a window ``(floor,
        1899-06-01)`` (``unit_rate_steps`` raises on a window that ends before it starts) nor any day before the floor but
        those three; its map is ``convert_bulk``'s."""
        print_section("P3: a cash transit entirely before the floor")
        old_rows = ((EUR, USD, date(1889, 12, 1), "1.2"), (EUR, USD, date(1899, 1, 1), "1.25"))
        txs = [
            _tx(1, TransactionType.DEPOSIT, date(1890, 1, 1), amount="1000", currency=USD),
            _tx(2, TransactionType.CASH_TRANSFER, date(1890, 1, 2), amount="-400", currency=USD),
            _tx(3, TransactionType.CASH_TRANSFER, date(1899, 6, 2), amount="400", currency=USD, broker_id=2),
        ]
        txs[1].related_transaction_id, txs[2].related_transaction_id = 3, 2
        classification = ScopeAwareTransactionClassifier({1, 2}, txs, {1: Decimal("1"), 2: Decimal("1")}).classify()
        assert [(interval.tx_type, interval.end_date) for interval in classification.in_transit_intervals] == [("cash", date(1899, 6, 1))], "precondition: one cash transit ending on 1899-06-01"
        inputs = {
            "classified_txs": classification.classified,
            "in_transit_intervals": classification.in_transit_intervals,
            "external_cash_flows": classification.external_cash_flows,
            "price_map": {},
            "asset_currencies": {},
            "target_currency": EUR,
            "date_from": FLOOR,
            "date_to": FLOOR + timedelta(days=9),
        }
        async with _rated_session(tmp_path, old_rows, (), "transit_floor") as session:
            calls = _record_fx(monkeypatch, portfolio_engine_module)
            fx_map = await PortfolioCalculationEngine(session)._preload_fx_rates(**inputs)
            monkeypatch.undo()
            expected = await _units_by_convert_bulk(session, _fx_needs_today(**inputs), EUR)
        before_floor = sorted(day for days in calls.asked_days().values() for day in days if day < FLOOR)
        assert before_floor in ([], [date(1890, 1, 1), date(1890, 1, 2), date(1899, 6, 2)]), f"days asked before the floor through unit_rate_steps: {before_floor}; only the movements' own days may be"
        problems = _map_problems(fx_map, expected, _probe_keys((USD,), EUR, date(1889, 12, 25), date(1890, 1, 10)) + _probe_keys((USD,), EUR, date(1899, 5, 25), FLOOR + timedelta(days=12)))
        assert not problems, f"the map of a pre-floor transit is not convert_bulk's on today's needs:{_show(problems)}"
        print_success(f"✓ {sorted(day for _currency, _target, day in expected)} only")

    @pytest.mark.asyncio
    async def test_the_map_the_engine_uses_in_a_report(self, tmp_path, monkeypatch):
        """8a's way: the map ``_preload_fx_rates`` returns during ``get_report`` (recorded), against ``convert_bulk`` on
        the needs of today computed from the very arguments it was given."""
        print_section("P3: the engine's map during a report, against convert_bulk")
        recorded = _Recorded().install(monkeypatch)
        async with _private_engine(tmp_path, "report_map") as engine:
            book = await _seed_report_book(engine)
            await _report(book)
            assert recorded.preloads, "the report never preloaded the FX rates: the recorder does not describe it"
            problems: list[str] = []
            async with AsyncSession(engine, expire_on_commit=False) as session:
                for arguments, fx_map in recorded.preloads:
                    expected = await _units_by_convert_bulk(session, _fx_needs_today(**arguments), arguments["target_currency"])
                    problems += _map_problems(fx_map, expected, _probe_keys((USD, CHF, GBP), arguments["target_currency"]))
        assert not problems, f"the map of the report's engine is not convert_bulk's on today's needs:{_show(problems)}"
        print_success(f"✓ {len(recorded.preloads)} preload(s), each convert_bulk's to the digit")


# =============================================================================
# 2 — THE NATIVE CASH IS THE NATIVE CASH OF THE DENSE convert_bulk DICT
# =============================================================================


class TestTheNativeCashIsConvertBulks:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("rates_until", "currencies"),
        [
            pytest.param(NATIVE_RATES_UNTIL, {USD, CHF, GBP}, id="rates-until-after-the-last-movement"),
            # CHF's first movement (1900-01-05) is after rates_until: today asks it no day; a window (01-05, 01-04) would
            # make unit_rate_steps raise ValueError. GBP's window (01-03, 01-04) holds no rate yet
            pytest.param(date(1900, 1, 4), {USD}, id="rates-until-before-a-currency-starts"),
            pytest.param(None, {USD, CHF, GBP}, id="rates-until-none-each-currency-to-its-last-movement"),
        ],
    )
    async def test_compute_native_cash_around_the_floor(self, tmp_path, rates_until, currencies):
        """``compute_native_cash`` on the native book (movements before the floor, a rate between two windows, GBP's first
        rate after its first movement, legacy rows) against today's dense ``NativeCash``: every reading equal — with
        ``rates_until`` after the last movement, before a currency's first movement, and None."""
        print_section(f"P3: compute_native_cash around the floor, rates until {rates_until}, against the dense convert_bulk dict")
        movements = _native_movements()
        async with _rated_session(tmp_path, NATIVE_ROWS, NATIVE_LEGACY, "native") as session:
            cash = await REAL_COMPUTE_NATIVE_CASH(session, movements, report_currency=EUR, rates_until=rates_until)
            dense_cash, dense = await _dense_native_cash(session, movements, EUR, rates_until)
        assert {currency for currency, _day in dense} == currencies and dense_cash.converted[3] is None, f"precondition: rates of {sorted(currencies)}, got {sorted({currency for currency, _day in dense})}; GBP's first movement not converted"
        problems = _native_problems(cash, dense_cash, _days(date(1899, 10, 25), date(1900, 4, 20)), "native book")
        assert not problems, f"compute_native_cash is not today's dense native cash ({len(problems)} problem(s)):{_show(problems)}"
        print_success(f"✓ {len(dense)} dense rates; value_at, change days and exchange results equal")

    @pytest.mark.asyncio
    async def test_the_native_cash_the_engine_uses_in_a_report(self, tmp_path, monkeypatch):
        """8a's way: every ``NativeCash`` built during ``get_report`` (recorded, with its arguments) against today's
        dense one on the same movements and ``rates_until``."""
        print_section("P3: the native cash during a report, against the dense convert_bulk dict")
        recorded = _Recorded().install(monkeypatch)
        async with _private_engine(tmp_path, "report_native") as engine:
            book = await _seed_report_book(engine)
            await _report(book)
            assert recorded.native_cashes, "the report built no native cash: the recorder does not describe it"
            problems: list[str] = []
            async with AsyncSession(engine, expire_on_commit=False) as session:
                for arguments, cash in recorded.native_cashes:
                    dense_cash, _dense = await _dense_native_cash(session, arguments["movements"], arguments["report_currency"], arguments.get("rates_until"))
                    problems += _native_problems(cash, dense_cash, _days(date(2024, 2, 15), END + timedelta(days=5)), f"native cash (rates_until {arguments.get('rates_until')})")
        assert not problems, f"a native cash of the report is not today's dense one ({len(problems)} problem(s)):{_show(problems)}"
        print_success(f"✓ {len(recorded.native_cashes)} native cash(es), every reading equal")


# =============================================================================
# 3 — THE WHOLE REPORT, BIT FOR BIT
# =============================================================================


class TestTheReportIsBitIdentical:
    @pytest.mark.asyncio
    async def test_the_report_with_the_product_readers_and_with_todays(self, tmp_path, monkeypatch):
        """The same report twice on the same book: with the product's readers, then with HEAD's dense readers patched in
        (``_preload_fx_rates_today``, ``_compute_native_cash_today``). Every field equal, every Decimal by
        ``as_tuple()``."""
        print_section("P3: the whole report, the product's readers against today's dense ones")
        async with _private_engine(tmp_path, "report_bits") as engine:
            book = await _seed_report_book(engine)
            product = _deep_bits(await _report(book))
            _clear_portfolio_caches()
            with monkeypatch.context() as patch:
                patch.setattr(PortfolioCalculationEngine, "_preload_fx_rates", _preload_fx_rates_today)
                patch.setattr(portfolio_engine_module, "compute_native_cash", _compute_native_cash_today)
                patch.setattr(portfolio_service_module, "compute_native_cash", _compute_native_cash_today)
                today = _deep_bits(await _report(book))
        assert product["history"] and product["summary"], "precondition: the report has a history and a summary"
        differences = _differences(product, today)
        assert not differences, f"the report differs from today's ({len(differences)} path(s)):{_show(differences)}"
        print_success(f"✓ {len(product['history'])} history points and every section equal, bit for bit")


# =============================================================================
# 4 — THE COST
# =============================================================================


def _needs_by_pair(needs: Iterable[tuple[str, date]], target: str) -> dict[Pair, set[date]]:
    by_pair: dict[Pair, set[date]] = {}
    for currency, day in needs:
        by_pair.setdefault((currency, target), set()).add(day)
    return by_pair


def _days_problems(asked: Mapping[Pair, set[date]], wanted: Mapping[Pair, set[date]]) -> list[str]:
    return [
        f"{pair}: windows ask {len(asked.get(pair, set()))} days, today {len(wanted.get(pair, set()))}; missing {sorted(wanted.get(pair, set()) - asked.get(pair, set()))[:4]}, extra {sorted(asked.get(pair, set()) - wanted.get(pair, set()))[:4]}"
        for pair in sorted(set(asked) | set(wanted))
        if asked.get(pair, set()) != wanted.get(pair, set())
    ]


def _cost_inputs(date_from: date, date_to: date) -> dict[str, Any]:
    """A range after every stored row: whatever its length, each currency has one step (its anchor) in it."""
    return {
        "classified_txs": _classified(_tx(1, TransactionType.DEPOSIT, date(2024, 2, 20), amount="10000", currency=USD), _tx(2, TransactionType.BUY, date(2024, 3, 5), amount="-300", currency=CHF, asset_id=2, quantity="3")),
        "in_transit_intervals": [],
        "external_cash_flows": [],
        "price_map": {1: [(date(2024, 2, 20), Decimal("100"), USD)], 2: [(date(2024, 2, 22), Decimal("50"), CHF)]},
        "asset_currencies": {1: USD, 2: CHF},
        "target_currency": EUR,
        "date_from": date_from,
        "date_to": date_to,
    }


class TestTheCost:
    @pytest.mark.asyncio
    async def test_the_preload_asks_convert_bulk_nothing_and_unit_rate_steps_once(self, tmp_path, monkeypatch):
        """RED today (cost): ``_preload_fx_rates`` hands ``convert_bulk`` one unit per need — every day of the range per
        currency — and never calls ``unit_rate_steps``. After the cure: no ``convert_bulk`` item, one ``unit_rate_steps``
        call."""
        print_section("P3 cost: the engine's preload asks convert_bulk nothing, unit_rate_steps once")
        async with _rated_session(tmp_path, MAIN_ROWS, MAIN_LEGACY, "cost_calls") as session:
            calls = _record_fx(monkeypatch, portfolio_engine_module)
            await PortfolioCalculationEngine(session)._preload_fx_rates(**_main_inputs())
        assert (len(calls.bulk_items), len(calls.steps_requests)) == (0, 1), f"_preload_fx_rates handed convert_bulk {len(calls.bulk_items)} items in {len(calls.bulk)} call(s) and called unit_rate_steps {len(calls.steps_requests)} time(s): expected 0 items and 1 call"
        print_success("✓ 0 convert_bulk items, 1 unit_rate_steps call")

    @pytest.mark.asyncio
    async def test_the_preload_windows_ask_the_needs_of_today(self, tmp_path, monkeypatch):
        """RED today (no ``unit_rate_steps`` call): the windows of the cure's one call cover, pair by pair, exactly the
        days today's needs hold — no day of the range lost or added at either end, every single day of a transaction,
        the transit from its first day and past ``date_to``."""
        print_section("P3 cost: the engine's windows are the needs of today")
        inputs = _main_inputs()
        async with _rated_session(tmp_path, MAIN_ROWS, MAIN_LEGACY, "cost_windows") as session:
            calls = _record_fx(monkeypatch, portfolio_engine_module)
            await PortfolioCalculationEngine(session)._preload_fx_rates(**inputs)
        assert calls.steps_requests, "_preload_fx_rates never called unit_rate_steps"
        problems = _days_problems(calls.asked_days(), _needs_by_pair(_fx_needs_today(**inputs), EUR))
        assert not problems, f"the engine's windows do not ask the days of today:{_show(problems)}"
        print_success("✓ the windows ask today's days, pair by pair")

    @pytest.mark.asyncio
    async def test_the_preload_work_does_not_grow_with_the_range(self, tmp_path, monkeypatch):
        """RED today (cost): over a range after every stored row, 30 days then 3000 days. The work — ``convert_bulk``
        items plus the days of the steps returned — must not grow: today it is one item per day and currency."""
        print_section("P3 cost: the engine's preload, 30 days against 3000")
        work: dict[int, tuple[int, int]] = {}
        async with _rated_session(tmp_path, MAIN_ROWS, MAIN_LEGACY, "cost_range") as session:
            for length in (30, 3000):
                calls = _record_fx(monkeypatch, portfolio_engine_module)
                first = date(2024, 6, 1)
                await PortfolioCalculationEngine(session)._preload_fx_rates(**_cost_inputs(first, first + timedelta(days=length - 1)))
                monkeypatch.undo()
                work[length] = (len(calls.bulk_items), calls.step_days)
        assert sum(work[3000]) <= sum(work[30]), f"(convert_bulk items, step days) over 30 days {work[30]}, over 3000 days {work[3000]}: the work grows with the range"
        print_success(f"✓ work over 30 days {work[30]}, over 3000 days {work[3000]}")

    @pytest.mark.asyncio
    async def test_compute_native_cash_hands_convert_bulk_the_movements_only(self, tmp_path, monkeypatch):
        """RED today (cost): ``compute_native_cash`` hands ``convert_bulk`` every foreign movement AND one unit per asked
        day. After the cure: the foreign non-zero movements only, in their order, and one ``unit_rate_steps`` call whose
        windows cover exactly today's asked days (single days before the floor, every day from ``max(first, floor)`` to
        ``rates_until``)."""
        print_section("P3 cost: the native cash hands convert_bulk the movements only")
        movements = _native_movements()
        foreign = [movement for movement in movements if movement.currency != EUR and movement.amount != 0]
        async with _rated_session(tmp_path, NATIVE_ROWS, NATIVE_LEGACY, "cost_native") as session:
            calls = _record_fx(monkeypatch, native_cash_module)
            await native_cash_module.compute_native_cash(session, movements, report_currency=EUR, rates_until=NATIVE_RATES_UNTIL)
        units = [item for item in calls.bulk_items if item not in {(movement.currency, movement.amount, EUR, movement.date) for movement in foreign}]
        assert calls.bulk_items == [
            (movement.currency, movement.amount, EUR, movement.date) for movement in foreign
        ], f"compute_native_cash handed convert_bulk {len(calls.bulk_items)} items for {len(foreign)} foreign movements: {len(units)} are no movement (one unit per asked day, e.g. {units[:3]})"
        assert len(calls.steps_requests) == 1, f"compute_native_cash called unit_rate_steps {len(calls.steps_requests)} time(s): expected 1"
        problems = _days_problems(calls.asked_days(), _needs_by_pair(_unit_requests_today(foreign, NATIVE_RATES_UNTIL), EUR))
        assert not problems, f"the native cash's windows do not ask the days of today:{_show(problems)}"
        print_success(f"✓ {len(foreign)} movements to convert_bulk, the asked days through one unit_rate_steps call")

    @pytest.mark.asyncio
    async def test_compute_native_cash_work_does_not_grow_with_rates_until(self, tmp_path, monkeypatch):
        """RED today (cost): ``rates_until`` 30 days, then 3000 days, after the last movement. The work — ``convert_bulk``
        items, the days of the steps, and the days ``NativeCash._rate_days`` keeps — must not grow: today every asked day
        is one item and one rate day."""
        print_section("P3 cost: the native cash, rates until 30 days against 3000 days")
        movements = _native_movements()
        last = max(movement.date for movement in movements)
        work: dict[int, tuple[int, int, int]] = {}
        async with _rated_session(tmp_path, NATIVE_ROWS, NATIVE_LEGACY, "cost_native_range") as session:
            for length in (30, 3000):
                calls = _record_fx(monkeypatch, native_cash_module)
                cash = await native_cash_module.compute_native_cash(session, movements, report_currency=EUR, rates_until=last + timedelta(days=length))
                monkeypatch.undo()
                work[length] = (len(calls.bulk_items), calls.step_days, sum(len(days) for days in cash._rate_days.values()))
        assert sum(work[3000]) <= sum(work[30]), f"(convert_bulk items, step days, rate days kept) with rates_until +30 days {work[30]}, +3000 days {work[3000]}: the work grows with rates_until"
        print_success(f"✓ work +30 days {work[30]}, +3000 days {work[3000]}")

    @pytest.mark.asyncio
    async def test_nothing_needed_asks_nothing(self, monkeypatch):
        """GUARD (green today): an EUR-only scope gives ``{}`` with no call at all; an EUR-only native cash makes none and
        never touches its session (None here)."""
        print_section("P3 cost: nothing to convert, nothing asked")
        calls = _record_fx(monkeypatch, portfolio_engine_module)
        inputs = _cost_inputs(START, END) | {"classified_txs": _classified(_tx(1, TransactionType.DEPOSIT, START, amount="100", currency=EUR)), "price_map": {}, "asset_currencies": {1: EUR}}
        assert await PortfolioCalculationEngine(None)._preload_fx_rates(**inputs) == {}
        native_calls = _record_fx(monkeypatch, native_cash_module)
        cash = await native_cash_module.compute_native_cash(None, [_move(START, EUR, "100"), _move(START, USD, "0")], report_currency=EUR, rates_until=END)
        assert dict(cash.unit_rates) == {}
        assert (calls.bulk, calls.steps_requests, native_calls.bulk, native_calls.steps_requests) == ([], [], [], []), "something was asked with nothing to convert"
        print_success("✓ no call")


def test_the_oracles_are_copies_of_head():
    """GUARD of the oracles: ``_fx_needs_today`` and ``_unit_requests_today`` answer, on the books of this file, what the
    product's own functions answered when the file was written (HEAD 2f4ab1962) — counted here so that a later edit of
    an oracle shows. The native book asks 2 days before the floor and 90 from it for USD (1900 is not a leap year), 86 for CHF (from
    1900-01-05), 88 for GBP (from 1900-01-03)."""
    print_section("P3: the oracles of today")
    foreign = [movement for movement in _native_movements() if movement.currency != EUR and movement.amount != 0]
    asked = _needs_by_pair(_unit_requests_today(foreign, NATIVE_RATES_UNTIL), EUR)
    assert {pair[0]: len(days) for pair, days in asked.items()} == {USD: 92, CHF: 86, GBP: 88}, {pair[0]: len(days) for pair, days in asked.items()}
    needs = _needs_by_pair(_fx_needs_today(**_main_inputs()), EUR)
    assert {pair[0] for pair in needs} == {USD, CHF, GBP, JPY}
    assert min(needs[(USD, EUR)]) == date(2024, 2, 20) and max(needs[(USD, EUR)]) == date(2024, 5, 9), (min(needs[(USD, EUR)]), max(needs[(USD, EUR)]))
    print_success("✓ the oracles answer as HEAD did")
