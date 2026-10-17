"""
MF-A (workstream MF, lot A) — the Dashboard's Performance table values each position with the engine.

``PortfolioService.get_positions_contribution`` gives one row per (broker, asset) with its ``start_value``,
``end_value`` and ``period_unrealized_delta`` (the change of market value − historical cost over the period) and its
``period_pnl``. Since MF-A those boundary figures are the engine's own position valuations at the end of ``date_from``
and at ``date_to`` (movements dated ≤ ``date_from`` are in the start), and an internal TRANSFER that departs and
arrives inside the period splits its result between the two brokers (developer's decision P22: «each broker answers
for its own tract; total unchanged»).

Before MF-A (HEAD 45ae068cc + lots B and H, uncommitted) each row valued itself: ``_get_price_at_date`` (market
quotes only, raw price, no split adjustment), converted by ``_convert_to_base`` at ``date_from``'s rate at the start
and at **the quote's own date**'s rate at the end; with no quote, or no rate, the value was None and its side of the
delta dropped (counted as 0). No trade mark, no at-cost estimate (J-17). An internal TRANSFER inside the period gave
the sender −UG_start and the receiver +UG_end.

Every scenario: one user owning 100 % of its brokers (A, and B for the transfers), one asset X (W for the holding at
cost), the Dashboard read in EUR from ``date_from`` to ``date_to``, through both paths that build the table: the
report the Dashboard posts (``get_report``, one engine run shared by the summary and the table) and the standalone
calls (``get_summary`` + ``get_positions_contribution``). Every expected value computed by hand; each scenario is
first proven to be the one intended through the engine's own period figures in the summary (the precondition, green
on HEAD and after): market value and unrealized G/L at both boundaries, their change, the period P&L.

Red on HEAD, green after (expected / HEAD):

- TestTradeMarkAtStart::one-buy — BUY 10 X for 1000 on 07-01, no quote before the period, close 110 on ``date_to``
  (07-31), period from 07-10. The engine values the start at the BUY's price: start 1000, end 1100, delta 100,
  P&L 100, P&L % 0.1. HEAD: start None (no quote on or before 07-10), delta 100 by luck (the BUY's mark equals its
  cost), P&L % None;
- TestTradeMarkAtStart::two-buys — BUY 10 for 800 on 07-01 and 10 for 1000 on 07-03 (cost 1800), same quotes: the
  start is 20 × 100 = 2000 (unrealized 200), the end 2200 (400): delta 200, P&L 200, P&L % 0.1. HEAD: start None,
  delta 400 − 0 = 400, P&L 400;
- TestOldForeignQuoteAtEnd — X in USD, EUR/USD 1.25 from 2047-03-01 (1 USD = 0.8 EUR), 1.6 from 2047-03-15
  (0.625): DEPOSIT and BUY 10 X for 1000 USD on 03-01 (cost 800 EUR), close 100 USD on ``date_from`` (03-05), last
  close 120 USD on 03-10, ``date_to`` 03-20. End 1200 USD at 03-20's rate: 750; delta −50, P&L −50. HEAD: at
  03-10's rate, 960; delta 160. The rates sit in 2047, where no other test writes EUR/USD;
- TestSplitAfterLastQuote — close 100 on 04-01, BUY 10 for 1000 on 04-02, SPLIT 2:1 (event + linked ADJUSTMENT +10)
  on 04-22, no later observation; period 04-10 → 04-30. End 20 × 50 = 1000 (the BUY's 100 restated through the
  split), delta 0, P&L 0. HEAD: 20 × 100 = 2000 (the 04-01 quote, never split-adjusted), delta 1000. NOTE: the engine
  restates a *trade-derived* mark through a split, never a market quote (``_market_value_for``: «real asset-system
  quotes already sit on the current-unit axis»), so the BUY after the quote is what makes the last observation a
  pre-split price; with the quote as the last observation the engine also gives 2000 (see the report);
- TestHeldAtCost — ADJUSTMENT +5 W at a cost of 40 a unit on 06-02, no price ever; period 06-10 → 06-30. Valued at
  cost (ESTIMATED_AT_COST): start 200, end 200, delta 0, P&L 0. HEAD: None, None, None, None;
- TestTransferMidPeriod (P22) — A: BUY 10 X for 800 on 10-01; closes 100 on ``date_from`` (10-10), 120 on 10-15,
  130 on 10-20, 150 on ``date_to`` (10-31); a linked TRANSFER of the 10 from A to B (the arrival carrying the cost,
  80 a unit, as the auto cost writes it) departing on 10-15 and arriving inside the period. C = 800 moves, V = the
  value on arrival: A = 0 − 200 + (V − 800), B = (1500 − 800) − 0 − (V − 800). ``same-day`` (arrival 10-15,
  V = 1200): A 200, B 300; ``in-transit-inside`` (arrival 10-20, V = 1300): A 300, B 200. Total 500 either way.
  HEAD: A −200, B 700.

Green on HEAD and after:

- TestTransferInTransitAtStart — departure 10-08 (before the period), arrival 10-15: today's attribution, B delta 700
  (1500 − 800), no figure for A;
- TestTransferInTransitAtEnd — departure 10-15, arrival 11-05 (after the period): A delta −200 (0 − 200), no row for B;
- TestOrdinaryEur — BUY 10 for 1000 on 08-01, closes 110 on ``date_from`` (08-11) and 130 on ``date_to`` (08-29),
  SELL 5 for 600 on 08-20: start 1100, end 650, delta 50 (150 − 100), realized 100, P&L 150;
- TestMissingFx — X in USD with no EUR/USD rate (every one removed inside the test's transaction), bought for 1000
  EUR (cost known), closes 100 and 110 USD on the boundaries: start, end, delta and P&L None.

TestInvariant — the rows add up to the engine: Σ rows' ``period_unrealized_delta`` == the summary's
``period_unrealized_gain_loss_delta`` (the engine's ``ugl_delta``), and Σ rows' ``period_pnl`` + Σ ``other_effects``
== the summary's ``period_pnl`` (to ``CONVERSION_DUST`` per hidden row). Red on HEAD for ``two-buys`` (400 against
200), ``old-foreign-quote`` (160 against −50) and ``split-after-last-quote`` (1000 against 0); green on HEAD for every
other scenario (the transfers move result between rows, not out of them). Not on ``missing-fx``: the engine counts a
holding it cannot value at zero against its cost, the rows leave it out, and both sums are 0 by coincidence.

MF-P4b — TestComponentPercents: each component of a row's period P&L also as a fraction of the row's |start_value|
(``period_unrealized_delta_percent``, ``period_realized_gain_loss_percent``, ``period_income_percent``,
``period_fees_taxes_percent``), to 4 decimals like ``period_pnl_percent``, the costs positive like
``period_fees_taxes``; None without a start value or without the component. One ledger (period 05-09 → 05-30, every
amount EUR): DEPOSIT 1000, BUY 10 X for 1000, close 100 on ``date_from``; inside the period SELL 5 for 550 (realized
550 − 5 × 100 = 50), a DIVIDEND of 12.34 and a FEE of 2.57 both on X, close 107.458 on ``date_to`` (end 5 × 107.458 =
537.29 against a cost of 500: unrealized 37.29). Red on HEAD (the four fields do not exist: AttributeError), green
after:

- held at the start (BUY on 05-02, start 1000): 37.29 / 1000 = 0.03729 → 0.0373, 50 / 1000 → 0.0500,
  12.34 / 1000 = 0.01234 → 0.0123, 2.57 / 1000 = 0.00257 → 0.0026 (positive); the row's return, 97.06 / 1000 →
  0.0971, is unchanged;
- opened inside the period (the same ledger with the BUY on 05-12, start 0): every component present, every fraction
  None (no base), like ``period_pnl_percent``;
- income only (a DIVIDEND of 12.34 and a FEE of 2.57 on an asset Z the broker never traded: a row with start 0 and no
  position): every fraction None.

MF-A5 — TestClosedPositionBase: a position fully sold in the period annualizes its P&L on the cost of every unit that
left it — sold, or moved by a counted P22 tract to a broker of the scope (``contributions.closed_position_base``) — over
its flight time; when a unit left another way, the general rule (P&L on |start value| over the period). One ledger
(period 01-15 → 04-30, every amount EUR): A: DEPOSIT 1000, BUY 10 X for 1000 on 01-06; closes 110 on ``date_from``,
115 on 03-17, 120 on 03-19, 130 on ``date_to``; SELL 5 for 625 on 02-17 (realized 125); on 03-17 the last 5 leave A
for B (a linked TRANSFER, arriving 03-19, worth 600 there: tract 100). The flight time is 01-15 → 03-17, 61 days; the
period 105. Expected / HEAD (203197f5a):

- in the scope (J's example): A's P&L 125 (ΔUGL −100 + tract 100, realized 125) on 500 + 500: 0.1250 → 1.023376;
  HEAD on the 500 sold: 0.2500 → 2.800768. Red on HEAD;
- the scope is A alone (B outside it: the departure is in-kind capital, no tract), or the arrival on 05-12, after the
  period (in transit at its end): A's P&L 25 (ΔUGL −100, realized 125); two exits, one sale counted, no base — the
  general rule, 25 / 1100 → 0.0227 → 0.081152 over 105 days; HEAD: 25 / 500 → 0.339024 over 61. Red on HEAD;
- the last 5 sold for 650 instead (no transfer, the guard): P&L 175 on the 1000 sold → 1.624696, as on HEAD;
- nothing sold, all 10 moved (worth 1200 on arrival): A's P&L 100 (ΔUGL −100 + tract 200) on the 1000 moved, 0.1000 →
  0.768795 over 61 days; HEAD had no cost sold, so no closed return: the general rule, 100 / 1100 → 0.0909 → 0.353155
  over 105. Red on HEAD (a change the decision brings: a transfer-only exit now has the closed return).

Each proven first through the engine's period figures in the summary and A's row (start, end, ΔUGL, P&L, realized,
fully sold), all green on HEAD. A scenario may read a subset of the user's brokers (``_Scenario.scope``): the report's
``broker_ids`` and the standalone calls'.

Isolation: every test owns its user, brokers and assets (unique names) and writes only through a session that is
rolled back: nothing is committed. EUR amounts are read in EUR (``target_currency_override`` / the report's
``target_currency``); the EUR/USD rates of TestOldForeignQuoteAtEnd are flushed with the rest and rolled back, and the
removal of every EUR/USD rate and route in TestMissingFx is rolled back too (the FX service backward-fills without
limit, so only an absence owned by the test is an absence). The report, WAC and engine blob caches are emptied around
each test. Rows are found by the test's own broker and asset ids; the user owns only the test's brokers.

Reference: backend/app/services/portfolio_service.py (get_positions_contribution, get_report),
backend/app/services/financial_math/portfolio/daily_state.py (_build_position_state, _value_held_position,
_market_value_for, _internal_pair_value), backend/app/services/financial_math/portfolio/period.py (period_pnl),
backend/app/services/financial_math/portfolio/contributions.py (closed_position_base, transfer_costs_moved_out).
"""

import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    PriceHistory,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import AssetPeriodContribution, PortfolioReportQuery, PortfolioSummary, PositionsContribution
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.financial_math.returns import cumulative_to_annualized
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services._range_bounds import lift_range_bound
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"
ZERO = Decimal("0")

# trade-mark-at-start
TM_OPEN = date(2025, 7, 1)
TM_SECOND_BUY = date(2025, 7, 3)
TM_FROM = date(2025, 7, 10)
TM_TO = date(2025, 7, 31)

# old-foreign-quote-at-end: a year no other test writes EUR/USD in
FX_OPEN = date(2047, 3, 1)
FX_FROM = date(2047, 3, 5)
FX_LAST_QUOTE = date(2047, 3, 10)
FX_RATE_MOVE = date(2047, 3, 15)
FX_TO = date(2047, 3, 20)

# split-after-last-quote
SP_QUOTE = date(2025, 4, 1)
SP_BUY = date(2025, 4, 2)
SP_FROM = date(2025, 4, 10)
SP_SPLIT = date(2025, 4, 22)
SP_TO = date(2025, 4, 30)

# held-at-cost
HC_OPEN = date(2025, 6, 2)
HC_FROM = date(2025, 6, 10)
HC_TO = date(2025, 6, 30)

# transfers
TR_OPEN = date(2025, 10, 1)
TR_EARLY_DEPARTURE = date(2025, 10, 8)  # before the period
TR_FROM = date(2025, 10, 10)
TR_MID = date(2025, 10, 15)
TR_LATER = date(2025, 10, 20)
TR_TO = date(2025, 10, 31)
TR_LATE_ARRIVAL = date(2025, 11, 5)  # after the period

# ordinary-eur
OR_OPEN = date(2025, 8, 1)
OR_FROM = date(2025, 8, 11)
OR_SELL = date(2025, 8, 20)
OR_TO = date(2025, 8, 29)

# missing-fx
MF_OPEN = date(2025, 9, 1)
MF_FROM = date(2025, 9, 10)
MF_TO = date(2025, 9, 30)

# component-percents (MF-P4b)
CP_OPEN = date(2025, 5, 2)
CP_FROM = date(2025, 5, 9)
CP_LATE_BUY = date(2025, 5, 12)  # inside the period: the position opened in it
CP_SELL = date(2025, 5, 16)
CP_DIVIDEND = date(2025, 5, 20)
CP_FEE = date(2025, 5, 21)
CP_TO = date(2025, 5, 30)

# closed-position base (MF-A5): the window FROM → DEPARTURE is 61 days, FROM → TO 105, both annualizable (≥ 30)
CB_OPEN = date(2025, 1, 6)
CB_FROM = date(2025, 1, 15)
CB_SELL = date(2025, 2, 17)
CB_DEPARTURE = date(2025, 3, 17)  # the day the last units leave A
CB_ARRIVAL = date(2025, 3, 19)
CB_TO = date(2025, 4, 30)
CB_LATE_ARRIVAL = date(2025, 5, 12)  # after the period

# The annualized return's rounding of the period return before annualizing (financial_math.portfolio.contributions).
RETURN_STEP = Decimal("0.0001")


# =============================================================================
# HELPERS
# =============================================================================


@dataclass
class _Book:
    """One user owning 100 % of the test's brokers, and the test's assets, each by a label."""

    user: User
    brokers: dict[str, Broker]
    assets: dict[str, Asset]


@dataclass(frozen=True)
class _EngineFigures:
    """The engine's period figures, as the summary exposes them, computed by hand (all EUR)."""

    market_value_start: str
    market_value_end: str
    ugl_start: str
    ugl_end: str
    pnl: str


@dataclass
class _Scenario:
    book: _Book
    date_from: date
    date_to: date
    engine: _EngineFigures | None  # None: the engine's period figures are not this scenario's subject
    scope: tuple[str, ...] | None = None  # the brokers read, by label; None: every broker the user owns


def _broker_ids(scenario: _Scenario) -> list[int] | None:
    """The scenario's scope as the services take it: None for every broker of the user."""
    return None if scenario.scope is None else [scenario.book.brokers[label].id for label in scenario.scope]


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


async def _book(session: AsyncSession, keep_alive: list[object], label: str, brokers: tuple[str, ...], assets: dict[str, str]) -> _Book:
    """A fresh user owning 100 % of ``brokers``; ``assets`` maps each label to its currency."""
    tag = uuid4().hex[:12]
    user = User(username=f"mfa_{label}_{tag}", email=f"mfa_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker_rows = {name: Broker(name=f"MfA {label} {name} {tag}") for name in brokers}
    asset_rows = {name: Asset(display_name=f"MfA {label} {name} {tag}", currency=currency, asset_type=AssetType.STOCK) for name, currency in assets.items()}
    await _persist(session, keep_alive, user, *broker_rows.values(), *asset_rows.values())
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in broker_rows.values()))
    return _Book(user=user, brokers=broker_rows, assets=asset_rows)


def _cash(book: _Book, broker: str, kind: TransactionType, day: date, amount: str, currency: str = EUR) -> Transaction:
    return Transaction(broker_id=book.brokers[broker].id, asset_id=None, type=kind, date=day, quantity=ZERO, amount=Decimal(amount), currency=currency)


def _trade(book: _Book, broker: str, asset: str, kind: TransactionType, day: date, quantity: str, amount: str, currency: str = EUR) -> Transaction:
    return Transaction(broker_id=book.brokers[broker].id, asset_id=book.assets[asset].id, type=kind, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency)


def _close(book: _Book, asset: str, day: date, close: str, currency: str = EUR) -> PriceHistory:
    price = Decimal(close)
    return PriceHistory(asset_id=book.assets[asset].id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=currency, source_plugin_key="mf_a_test")


async def _link(session: AsyncSession, departure: Transaction, arrival: Transaction) -> None:
    """A linked pair references itself both ways: the ids exist only after the first flush."""
    departure.related_transaction_id = arrival.id
    arrival.related_transaction_id = departure.id
    await session.flush()


async def _own_missing_rate(session: AsyncSession, currency: str, target: str) -> None:
    """Guarantee that ``currency`` has no rate and no route to ``target`` while this test runs.

    ``fx_rates`` and ``fx_conversion_routes`` are global and store a pair alphabetically: both are emptied for it inside
    this test's transaction, which the ``session`` fixture rolls back, so a neighbour's rows come back intact. Even a
    years-old rate would matter: the FX service backward-fills without limit. (Same contract as
    ``test_lots_analysis_service._own_missing_rate``.)
    """
    base, quote = sorted((currency, target))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))


# =============================================================================
# SCENARIOS
# =============================================================================


async def _trade_mark_one_buy(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "tm1", ("A",), {"X": EUR})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, TM_OPEN, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, TM_OPEN, "10", "-1000"),
        # No quote on or before TM_FROM: the start is valued by the BUY's price.
        _close(book, "X", TM_TO, "110"),
    )
    return _Scenario(book=book, date_from=TM_FROM, date_to=TM_TO, engine=_EngineFigures("1000", "1100", "0", "100", "100"))


async def _trade_mark_two_buys(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "tm2", ("A",), {"X": EUR})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, TM_OPEN, "1800"),
        _trade(book, "A", "X", TransactionType.BUY, TM_OPEN, "10", "-800"),
        _trade(book, "A", "X", TransactionType.BUY, TM_SECOND_BUY, "10", "-1000"),
        _close(book, "X", TM_TO, "110"),
    )
    # Start: 20 × 100 (the last BUY's price) = 2000 against a cost of 1800; end 2200 against 1800.
    return _Scenario(book=book, date_from=TM_FROM, date_to=TM_TO, engine=_EngineFigures("2000", "2200", "200", "400", "200"))


async def _old_foreign_quote(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "fx", ("A",), {"X": USD})
    await _persist(
        session,
        keep_alive,
        # Stored alphabetically, 1 EUR = rate USD: 1 USD = 1 / 1.25 = 0.8 EUR, then 1 / 1.6 = 0.625 EUR.
        FxRate(date=FX_OPEN, base=EUR, quote=USD, rate=Decimal("1.25"), source="TEST"),
        FxRate(date=FX_RATE_MOVE, base=EUR, quote=USD, rate=Decimal("1.6"), source="TEST"),
        _cash(book, "A", TransactionType.DEPOSIT, FX_OPEN, "1000", currency=USD),
        _trade(book, "A", "X", TransactionType.BUY, FX_OPEN, "10", "-1000", currency=USD),
        _close(book, "X", FX_FROM, "100", currency=USD),
        _close(book, "X", FX_LAST_QUOTE, "120", currency=USD),
    )
    # Start 1000 USD × 0.8 = 800 against a cost of 800; end 1200 USD × 0.625 = 750 against 800.
    return _Scenario(book=book, date_from=FX_FROM, date_to=FX_TO, engine=_EngineFigures("800", "750", "0", "-50", "-50"))


async def _split_after_last_quote(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "split", ("A",), {"X": EUR})
    event = AssetEvent(asset_id=book.assets["X"].id, date=SP_SPLIT, type=AssetEventType.SPLIT, value=Decimal("2"), currency=EUR)
    await _persist(session, keep_alive, event)
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, SP_QUOTE, "1000"),
        _close(book, "X", SP_QUOTE, "100"),
        # The day after the quote: the BUY is the last observation before the split.
        _trade(book, "A", "X", TransactionType.BUY, SP_BUY, "10", "-1000"),
        Transaction(broker_id=book.brokers["A"].id, asset_id=book.assets["X"].id, asset_event_id=event.id, type=TransactionType.ADJUSTMENT, date=SP_SPLIT, quantity=Decimal("10"), amount=ZERO),
    )
    # Start 10 × 100; end 20 × (100 / 2); the split keeps the cost, 1000.
    return _Scenario(book=book, date_from=SP_FROM, date_to=SP_TO, engine=_EngineFigures("1000", "1000", "0", "0", "0"))


async def _held_at_cost(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "atcost", ("A",), {"W": EUR})
    await _persist(
        session,
        keep_alive,
        # In kind, no cash, no quote, no BUY or SELL: W has no price at all.
        Transaction(broker_id=book.brokers["A"].id, asset_id=book.assets["W"].id, type=TransactionType.ADJUSTMENT, date=HC_OPEN, quantity=Decimal("5"), amount=ZERO, cost_basis_override=Decimal("40"), cost_basis_currency=EUR),
    )
    return _Scenario(book=book, date_from=HC_FROM, date_to=HC_TO, engine=_EngineFigures("200", "200", "0", "0", "0"))


async def _transfer_ledger(session: AsyncSession, keep_alive: list[object], label: str, departure_day: date, arrival_day: date) -> _Book:
    """A: DEPOSIT 800 and BUY 10 X for 800 on TR_OPEN; the 10 X leave A on ``departure_day`` and reach B on
    ``arrival_day`` (a linked TRANSFER pair, the arrival carrying the cost, 80 a unit, as the auto cost writes it);
    X closes 100 on TR_FROM, 120 on TR_MID, 130 on TR_LATER, 150 on TR_TO."""
    book = await _book(session, keep_alive, label, ("A", "B"), {"X": EUR})
    departure = Transaction(broker_id=book.brokers["A"].id, asset_id=book.assets["X"].id, type=TransactionType.TRANSFER, date=departure_day, quantity=Decimal("-10"), amount=ZERO)
    arrival = Transaction(
        broker_id=book.brokers["B"].id,
        asset_id=book.assets["X"].id,
        type=TransactionType.TRANSFER,
        date=arrival_day,
        quantity=Decimal("10"),
        amount=ZERO,
        cost_basis_override=Decimal("80"),
        cost_basis_currency=EUR,
    )
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, TR_OPEN, "800"),
        _trade(book, "A", "X", TransactionType.BUY, TR_OPEN, "10", "-800"),
        departure,
        arrival,
        _close(book, "X", TR_FROM, "100"),
        _close(book, "X", TR_MID, "120"),
        _close(book, "X", TR_LATER, "130"),
        _close(book, "X", TR_TO, "150"),
    )
    await _link(session, departure, arrival)
    return book


async def _transfer_same_day(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _transfer_ledger(session, keep_alive, "trsame", TR_MID, TR_MID)
    # Start: A holds 10 × 100 against 800; end: B holds 10 × 150 against 800. NAV 1000 → 1500, no flow.
    return _Scenario(book=book, date_from=TR_FROM, date_to=TR_TO, engine=_EngineFigures("1000", "1500", "200", "700", "500"))


async def _transfer_in_transit_inside(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _transfer_ledger(session, keep_alive, "trinside", TR_MID, TR_LATER)
    return _Scenario(book=book, date_from=TR_FROM, date_to=TR_TO, engine=_EngineFigures("1000", "1500", "200", "700", "500"))


async def _transfer_in_transit_at_start(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _transfer_ledger(session, keep_alive, "trstart", TR_EARLY_DEPARTURE, TR_MID)
    # On TR_FROM the 10 X are in flight: no held position (in transit is outside market value and open cost), NAV 1000
    # through the value in transit; end: B holds 1500 against 800.
    return _Scenario(book=book, date_from=TR_FROM, date_to=TR_TO, engine=_EngineFigures("0", "1500", "0", "700", "500"))


async def _transfer_in_transit_at_end(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _transfer_ledger(session, keep_alive, "trend", TR_MID, TR_LATE_ARRIVAL)
    # Start: A holds 1000 against 800; on TR_TO the 10 X are in flight (worth 1500, outside market value).
    return _Scenario(book=book, date_from=TR_FROM, date_to=TR_TO, engine=_EngineFigures("1000", "0", "200", "0", "500"))


async def _ordinary_eur(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "ordinary", ("A",), {"X": EUR})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, OR_OPEN, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, OR_OPEN, "10", "-1000"),
        _close(book, "X", OR_FROM, "110"),
        _trade(book, "A", "X", TransactionType.SELL, OR_SELL, "-5", "600"),
        _close(book, "X", OR_TO, "130"),
    )
    # Start 1100 against 1000; end 5 × 130 = 650 against 500; NAV 1100 → 650 + cash 600.
    return _Scenario(book=book, date_from=OR_FROM, date_to=OR_TO, engine=_EngineFigures("1100", "650", "100", "150", "150"))


async def _missing_fx(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    await _own_missing_rate(session, USD, EUR)
    book = await _book(session, keep_alive, "nofx", ("A",), {"X": USD})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, MF_OPEN, "1000"),
        # Paid in EUR: the cost is known, only the valuation lacks a rate.
        _trade(book, "A", "X", TransactionType.BUY, MF_OPEN, "10", "-1000"),
        _close(book, "X", MF_FROM, "100", currency=USD),
        _close(book, "X", MF_TO, "110", currency=USD),
    )
    return _Scenario(book=book, date_from=MF_FROM, date_to=MF_TO, engine=None)


async def _components_ledger(session: AsyncSession, keep_alive: list[object], label: str, buy_day: date) -> _Book:
    """DEPOSIT 1000 on CP_OPEN, BUY 10 X for 1000 on ``buy_day``; inside the period SELL 5 for 550, a DIVIDEND of 12.34
    and a FEE of 2.57 both attributed to X; X closes 100 on CP_FROM and 107.458 on CP_TO."""
    book = await _book(session, keep_alive, label, ("A",), {"X": EUR})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, CP_OPEN, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, buy_day, "10", "-1000"),
        _close(book, "X", CP_FROM, "100"),
        # Average cost 100 a unit: realized 550 − 500 = 50.
        _trade(book, "A", "X", TransactionType.SELL, CP_SELL, "-5", "550"),
        _trade(book, "A", "X", TransactionType.DIVIDEND, CP_DIVIDEND, "0", "12.34"),
        _trade(book, "A", "X", TransactionType.FEE, CP_FEE, "0", "-2.57"),
        _close(book, "X", CP_TO, "107.458"),
    )
    return book


async def _components_held_at_start(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _components_ledger(session, keep_alive, "p4held", CP_OPEN)
    # Start 10 × 100 = 1000 against 1000; end 5 × 107.458 = 537.29 against 500; NAV 1000 → 537.29 + cash
    # (550 + 12.34 − 2.57 = 559.77) = 1097.06, no external flow: P&L 97.06 = 37.29 + 50 + 12.34 − 2.57.
    return _Scenario(book=book, date_from=CP_FROM, date_to=CP_TO, engine=_EngineFigures("1000", "537.29", "0", "37.29", "97.06"))


async def _components_opened_in_period(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _components_ledger(session, keep_alive, "p4opened", CP_LATE_BUY)
    # Start: cash 1000, nothing held; end as above: NAV 1000 → 1097.06, no external flow inside the period.
    return _Scenario(book=book, date_from=CP_FROM, date_to=CP_TO, engine=_EngineFigures("0", "537.29", "0", "37.29", "97.06"))


async def _components_income_only(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "p4income", ("A",), {"Z": EUR})
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, CP_OPEN, "1000"),
        # On Z, never bought, sold, adjusted or transferred: the row has no position.
        _trade(book, "A", "Z", TransactionType.DIVIDEND, CP_DIVIDEND, "0", "12.34"),
        _trade(book, "A", "Z", TransactionType.FEE, CP_FEE, "0", "-2.57"),
    )
    # Nothing held at either boundary; NAV 1000 → 1009.77.
    return _Scenario(book=book, date_from=CP_FROM, date_to=CP_TO, engine=_EngineFigures("0", "0", "0", "0", "9.77"))


async def _closed_base_ledger(session: AsyncSession, keep_alive: list[object], label: str, *, sold: str, moved: str, arrival_day: date) -> _Book:
    """MF-A5. A: DEPOSIT 1000 and BUY 10 X for 1000 on CB_OPEN (100 a unit). Inside the period: SELL 5 for ``sold`` on
    CB_SELL when ``sold`` is not empty; on CB_DEPARTURE the ``moved`` units left leave A for B, reaching it on
    ``arrival_day`` (a linked TRANSFER pair, the arrival carrying the cost, 100 a unit, as the auto cost writes it) —
    or, when ``moved`` is empty, the last 5 are sold for 650 instead. X closes 110 on CB_FROM, 115 on CB_DEPARTURE, 120
    on CB_ARRIVAL, 130 on CB_TO: every boundary and every day a value is read on has its own quote."""
    book = await _book(session, keep_alive, label, ("A", "B"), {"X": EUR})
    rows: list[object] = [
        _cash(book, "A", TransactionType.DEPOSIT, CB_OPEN, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, CB_OPEN, "10", "-1000"),
        _close(book, "X", CB_FROM, "110"),
        _close(book, "X", CB_DEPARTURE, "115"),
        _close(book, "X", CB_ARRIVAL, "120"),
        _close(book, "X", CB_TO, "130"),
    ]
    if sold:
        rows.append(_trade(book, "A", "X", TransactionType.SELL, CB_SELL, "-5", sold))
    if not moved:
        rows.append(_trade(book, "A", "X", TransactionType.SELL, CB_DEPARTURE, "-5", "650"))
        await _persist(session, keep_alive, *rows)
        return book
    departure = Transaction(broker_id=book.brokers["A"].id, asset_id=book.assets["X"].id, type=TransactionType.TRANSFER, date=CB_DEPARTURE, quantity=-Decimal(moved), amount=ZERO)
    arrival = Transaction(
        broker_id=book.brokers["B"].id,
        asset_id=book.assets["X"].id,
        type=TransactionType.TRANSFER,
        date=arrival_day,
        quantity=Decimal(moved),
        amount=ZERO,
        cost_basis_override=Decimal("100"),
        cost_basis_currency=EUR,
    )
    await _persist(session, keep_alive, *rows, departure, arrival)
    await _link(session, departure, arrival)
    return book


async def _sold_and_moved_in_scope(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    """J's example: 5 sold for 625, 5 moved to B and worth 600 there on arrival, both brokers read."""
    book = await _closed_base_ledger(session, keep_alive, "a5scope", sold="625", moved="5", arrival_day=CB_ARRIVAL)
    # Start: A holds 10 × 110 against 1000; end: B holds 5 × 130 against 500. NAV 1100 → 650 + cash 625, no flow.
    return _Scenario(book=book, date_from=CB_FROM, date_to=CB_TO, engine=_EngineFigures("1100", "650", "100", "150", "175"))


async def _sold_and_moved_out_of_scope(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    """The same ledger with A alone read: the TRANSFER is no internal pair, B is outside the scope."""
    book = await _closed_base_ledger(session, keep_alive, "a5out", sold="625", moved="5", arrival_day=CB_ARRIVAL)
    # NAV 1100 → cash 625; the 5 X leave the scope as in-kind capital at their value on CB_DEPARTURE, 5 × 115 = 575:
    # P&L 625 − 1100 + 575 = 100.
    return _Scenario(book=book, date_from=CB_FROM, date_to=CB_TO, engine=_EngineFigures("1100", "0", "100", "0", "100"), scope=("A",))


async def _sold_and_moved_in_transit_at_end(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    """The 5 moved reach B after the period: still in transit on CB_TO."""
    book = await _closed_base_ledger(session, keep_alive, "a5transit", sold="625", moved="5", arrival_day=CB_LATE_ARRIVAL)
    # End: nothing held, the 5 X in flight worth 5 × 130 = 650 (outside market value): NAV 1100 → 625 + 650.
    return _Scenario(book=book, date_from=CB_FROM, date_to=CB_TO, engine=_EngineFigures("1100", "0", "100", "0", "175"))


async def _sold_twice(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    """No transfer: 5 sold for 625, the last 5 for 650."""
    book = await _closed_base_ledger(session, keep_alive, "a5sold", sold="625", moved="", arrival_day=CB_ARRIVAL)
    # NAV 1100 → cash 1275.
    return _Scenario(book=book, date_from=CB_FROM, date_to=CB_TO, engine=_EngineFigures("1100", "0", "100", "0", "175"))


async def _moved_whole(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    """Nothing sold: all 10 moved to B, worth 1200 there on arrival, both brokers read."""
    book = await _closed_base_ledger(session, keep_alive, "a5moved", sold="", moved="10", arrival_day=CB_ARRIVAL)
    # End: B holds 10 × 130 against 1000. NAV 1100 → 1300, no flow.
    return _Scenario(book=book, date_from=CB_FROM, date_to=CB_TO, engine=_EngineFigures("1100", "1300", "100", "300", "200"))


ScenarioBuilder = Callable[[AsyncSession, list[object]], Awaitable[_Scenario]]

# Every scenario whose rows the engine can value: the invariant is meaningful on each.
INVARIANT_SCENARIOS: dict[str, ScenarioBuilder] = {
    "trade-mark-one-buy": _trade_mark_one_buy,
    # Red on HEAD: 400 against 200.
    "trade-mark-two-buys": _trade_mark_two_buys,
    # Red on HEAD: 160 against −50.
    "old-foreign-quote": _old_foreign_quote,
    # Red on HEAD: 1000 against 0.
    "split-after-last-quote": _split_after_last_quote,
    "held-at-cost": _held_at_cost,
    "transfer-same-day": _transfer_same_day,
    "transfer-in-transit-inside": _transfer_in_transit_inside,
    "transfer-in-transit-at-start": _transfer_in_transit_at_start,
    "transfer-in-transit-at-end": _transfer_in_transit_at_end,
    "ordinary-eur": _ordinary_eur,
}


# =============================================================================
# READING AND CHECKING
# =============================================================================


def _report_query(scenario: _Scenario) -> PortfolioReportQuery:
    """The Dashboard's report: the summary and the Performance table from one engine run."""
    return PortfolioReportQuery(
        broker_ids=_broker_ids(scenario),
        date_range=OpenDateRangeModel(start=scenario.date_from, end=scenario.date_to),
        target_currency=EUR,
        include_summary=True,
        include_history=False,
        include_allocation_history=False,
        include_breakdown=False,
        include_positions_contribution=True,
    )


def _amount(value) -> Decimal | None:
    return value.amount if value is not None else None


def _engine_problems(summary: PortfolioSummary, figures: _EngineFigures) -> list[str]:
    """The engine's period figures in the summary against the scenario's, computed by hand."""
    shown = {
        "period_market_value_start": _amount(summary.period_market_value_start),
        "market_value": _amount(summary.market_value),
        "period_unrealized_gain_loss_start": _amount(summary.period_unrealized_gain_loss_start),
        "period_unrealized_gain_loss_end": _amount(summary.period_unrealized_gain_loss_end),
        "period_unrealized_gain_loss_delta": _amount(summary.period_unrealized_gain_loss_delta),
        "period_pnl": _amount(summary.period_pnl),
    }
    expected = {
        "period_market_value_start": Decimal(figures.market_value_start),
        "market_value": Decimal(figures.market_value_end),
        "period_unrealized_gain_loss_start": Decimal(figures.ugl_start),
        "period_unrealized_gain_loss_end": Decimal(figures.ugl_end),
        "period_unrealized_gain_loss_delta": Decimal(figures.ugl_end) - Decimal(figures.ugl_start),
        "period_pnl": Decimal(figures.pnl),
    }
    return [f"summary {name} {shown[name]}, expected {expected[name]}" for name in expected if shown[name] != expected[name]]


async def _read(session: AsyncSession, scenario: _Scenario, path: str) -> tuple[PositionsContribution, PortfolioSummary]:
    """The scenario's Performance table and summary through ``path``, once proven to be the scenario intended."""
    service = PortfolioService(session)
    user_id = scenario.book.user.id
    if path == "report":
        report = await service.get_report(user_id, _report_query(scenario))
        contribution, summary = report.positions_contribution, report.summary
        assert contribution is not None and summary is not None, "the report includes what it was asked for"
    else:
        # The summary first, as a Dashboard would: its engine run is in the blob cache when the table asks for its own,
        # so a cached run cannot answer for a different period start (see test_period_start_snapshot.py).
        broker_ids = _broker_ids(scenario)
        summary = await service.get_summary(user_id=user_id, broker_ids=broker_ids, target_currency_override=EUR, date_from=scenario.date_from, date_to=scenario.date_to)
        contribution = await service.get_positions_contribution(user_id=user_id, broker_ids=broker_ids, date_from=scenario.date_from, date_to=scenario.date_to, target_currency_override=EUR)
    if scenario.engine is not None:
        problems = _engine_problems(summary, scenario.engine)
        assert not problems, "precondition — not the scenario intended:\n" + "\n".join(problems)
    return contribution, summary


def _rows(contribution: PositionsContribution, book: _Book) -> dict[tuple[str, str], AssetPeriodContribution]:
    """The table's rows by (broker label, asset label): the user owns only the book's brokers, so every row is the book's."""
    broker_labels = {broker.id: label for label, broker in book.brokers.items()}
    asset_labels = {asset.id: label for label, asset in book.assets.items()}
    rows: dict[tuple[str, str], AssetPeriodContribution] = {}
    for row in contribution.positions:
        key = (broker_labels.get(row.broker_id, str(row.broker_id)), asset_labels.get(row.asset_id, str(row.asset_id)))
        assert key[0] in book.brokers and key[1] in book.assets, f"row {key} is not the test's"
        assert key not in rows, f"two rows for {key}"
        rows[key] = row
    return rows


def _row(contribution: PositionsContribution, book: _Book, broker: str, asset: str) -> AssetPeriodContribution:
    rows = _rows(contribution, book)
    assert (broker, asset) in rows, f"no row for ({broker}, {asset}); rows {sorted(rows)}"
    return rows[(broker, asset)]


def _view(row: AssetPeriodContribution) -> dict[str, Decimal | None]:
    return {"start_value": row.start_value, "end_value": row.end_value, "period_unrealized_delta": row.period_unrealized_delta, "period_pnl": row.period_pnl}


def _expected(start: str | None, end: str | None, delta: str | None, pnl: str | None) -> dict[str, Decimal | None]:
    """The four boundary figures of a row, every amount in EUR; None where the row cannot know it."""
    return {
        "start_value": None if start is None else Decimal(start),
        "end_value": None if end is None else Decimal(end),
        "period_unrealized_delta": None if delta is None else Decimal(delta),
        "period_pnl": None if pnl is None else Decimal(pnl),
    }


def _no_figure(contribution: PositionsContribution, book: _Book, broker: str, asset: str) -> None:
    """``broker`` holds nothing at either boundary and has no period activity: no row, or a row with no result."""
    row = _rows(contribution, book).get((broker, asset))
    if row is not None:
        assert (row.period_unrealized_delta or ZERO, row.period_pnl or ZERO) == (ZERO, ZERO), f"row ({broker}, {asset}): {_view(row)}"


def _components(row: AssetPeriodContribution) -> dict[str, Decimal | None]:
    """A row's start value and the four components of its period P&L (MF-P4b's precondition)."""
    return {
        "start_value": row.start_value,
        "period_unrealized_delta": row.period_unrealized_delta,
        "period_realized_gain_loss": row.period_realized_gain_loss,
        "period_income": row.period_income,
        "period_fees_taxes": row.period_fees_taxes,
    }


def _component_percents(row: AssetPeriodContribution) -> dict[str, Decimal | None]:
    """The four components as fractions of |start_value| (MF-P4b); plain attribute reads, so HEAD fails naming the field."""
    return {
        "period_unrealized_delta_percent": row.period_unrealized_delta_percent,
        "period_realized_gain_loss_percent": row.period_realized_gain_loss_percent,
        "period_income_percent": row.period_income_percent,
        "period_fees_taxes_percent": row.period_fees_taxes_percent,
    }


_NO_COMPONENT_PERCENTS: dict[str, Decimal | None] = {
    "period_unrealized_delta_percent": None,
    "period_realized_gain_loss_percent": None,
    "period_income_percent": None,
    "period_fees_taxes_percent": None,
}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the old-foreign-quote scenario lives in 2047, after tomorrow, so the range bound is lifted for the
    whole module, before any fixture builds data (see ``lift_range_bound``)."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        lift_range_bound(monkeypatch)
        yield


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.fixture
def keep_alive() -> list[object]:
    """Strong references to every row the test flushes (see _persist)."""
    return []


@pytest.fixture(autouse=True)
def clean_portfolio_caches(request):
    """No cached report, WAC or engine blob crosses into or out of a test."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(params=["report", "standalone"])
def path(request) -> str:
    """Both ways the Performance table is built: the Dashboard's report (one engine run shared with the summary) and the
    standalone calls."""
    return request.param


# =============================================================================
# Red on HEAD, green after: each row valued by the engine
# =============================================================================


class TestTradeMarkAtStart:
    """No market quote on or before ``date_from``: the engine values the start at the last BUY's price (a trade mark,
    LAST_TRADE_PRICE); HEAD read market quotes only and left the start None."""

    @pytest.mark.asyncio
    async def test_one_buy_the_start_is_the_buy_price(self, session, keep_alive, path):
        """BUY 10 for 1000, close 110 at the end: start 10 × 100 = 1000, end 1100, delta 100, P&L 100, 10 %.
        HEAD: start None, P&L % None (the delta is 100 both ways: the BUY's mark equals its cost)."""
        print_section(f"MF-A trade mark at start, one BUY ({path})")
        scenario = await _trade_mark_one_buy(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        assert _view(row) == _expected("1000", "1100", "100", "100")
        assert row.period_pnl_percent == Decimal("0.1"), "100 / 1000"
        print_success("start 1000 at the BUY's price")

    @pytest.mark.asyncio
    async def test_two_buys_the_start_is_the_last_buy_price(self, session, keep_alive, path):
        """BUY 10 for 800 then 10 for 1000 (cost 1800), close 110 at the end: start 20 × 100 = 2000 (unrealized 200),
        end 2200 (400): delta 200, P&L 200, 10 %. HEAD: start None, delta 400 − 0 = 400, P&L 400, P&L % None."""
        print_section(f"MF-A trade mark at start, two BUYs ({path})")
        scenario = await _trade_mark_two_buys(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        assert _view(row) == _expected("2000", "2200", "200", "200")
        assert row.period_pnl_percent == Decimal("0.1"), "200 / 2000"
        print_success("start 2000, delta 200")


class TestOldForeignQuoteAtEnd:
    """A USD quote older than ``date_to``: the engine converts the carried mark at ``date_to``'s rate; HEAD at the
    quote's own date."""

    @pytest.mark.asyncio
    async def test_the_end_is_converted_at_the_period_end_rate(self, session, keep_alive, path):
        """Last close 120 USD on 03-10, EUR/USD from 1.25 to 1.6 on 03-15, ``date_to`` 03-20: end 1200 / 1.6 = 750,
        start 1000 / 1.25 = 800 (= its cost), delta −50, P&L −50. HEAD: end 1200 / 1.25 = 960, delta 160."""
        print_section(f"MF-A old foreign quote at end ({path})")
        scenario = await _old_foreign_quote(session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        holding = next(h for h in summary.holdings if h.asset_id == scenario.book.assets["X"].id)
        assert (holding.current_value, holding.valuation_reference_date) == (Decimal("750"), FX_LAST_QUOTE), "precondition: the engine carries the 03-10 quote to 03-20 at 03-20's rate"
        assert _view(row) == _expected("800", "750", "-50", "-50")
        print_success("end 750 at the period end's rate")


class TestSplitAfterLastQuote:
    """The last observation is a pre-split price: the engine restates it through the split; HEAD's market quote was
    never split-adjusted, so the doubled quantity met the old price."""

    @pytest.mark.asyncio
    async def test_the_end_is_split_adjusted(self, session, keep_alive, path):
        """Close 100 on 04-01, BUY 10 for 1000 on 04-02, SPLIT 2:1 on 04-22, nothing after: end 20 × 50 = 1000, start
        1000, cost 1000 throughout: delta 0, P&L 0. HEAD: end 20 × 100 = 2000 (the 04-01 quote), delta 1000."""
        print_section(f"MF-A split after the last observation ({path})")
        scenario = await _split_after_last_quote(session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        holding = next(h for h in summary.holdings if h.asset_id == scenario.book.assets["X"].id)
        assert (holding.quantity, holding.current_value, holding.valuation_split_adjusted) == (Decimal("20"), Decimal("1000"), True), "precondition: the engine restates the BUY's 100 to 50"
        assert _view(row) == _expected("1000", "1000", "0", "0")
        print_success("end 1000, not doubled")


class TestHeldAtCost:
    """No price at all: the engine counts the holding at its book cost (ESTIMATED_AT_COST, J-17); HEAD had no price to
    read and left every figure None."""

    @pytest.mark.asyncio
    async def test_a_holding_with_no_price_is_valued_at_cost(self, session, keep_alive, path):
        """ADJUSTMENT +5 W at 40 a unit: start 200, end 200, delta 0, P&L 0. HEAD: None, None, None, None."""
        print_section(f"MF-A held at cost ({path})")
        scenario = await _held_at_cost(session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "W")

        holding = next(h for h in summary.holdings if h.asset_id == scenario.book.assets["W"].id)
        assert (holding.valuation_source, holding.current_value) == ("ESTIMATED_AT_COST", Decimal("200")), "precondition: the engine values W at its cost"
        assert _view(row) == _expected("200", "200", "0", "0")
        print_success("W at cost, 200 → 200")


class TestTransferMidPeriod:
    """P22 — a TRANSFER from A to B that departs and arrives inside the period: A answers for its tract up to the arrival
    (it closes at V, the value on arrival), B from the arrival (it opens at V). C = 800, the cost moved. HEAD gave A
    −UG_start = −200 and B UG_end = 700."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("builder", "sender", "receiver"),
        [
            # V = 10 × 120 = 1200: A = 0 − 200 + (1200 − 800); B = (1500 − 800) − 0 − (1200 − 800).
            pytest.param(_transfer_same_day, "200", "300", id="same-day"),
            # V = 10 × 130 = 1300 (the value on arrival, 10-20): A = −200 + 500; B = 700 − 500.
            pytest.param(_transfer_in_transit_inside, "300", "200", id="in-transit-inside"),
        ],
    )
    async def test_each_broker_answers_for_its_own_tract(self, session, keep_alive, path, builder, sender, receiver):
        """A and B split the 500 at the value on arrival; HEAD: A −200, B 700."""
        print_section(f"MF-A P22 transfer inside the period ({path})")
        scenario = await builder(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row_a = _row(contribution, scenario.book, "A", "X")
        row_b = _row(contribution, scenario.book, "B", "X")

        assert (row_a.start_value, row_b.end_value) == (Decimal("1000"), Decimal("1500")), "the boundaries: A held 10 × 100 at the start, B 10 × 150 at the end"
        assert {"A": (row_a.period_unrealized_delta, row_a.period_pnl), "B": (row_b.period_unrealized_delta, row_b.period_pnl)} == {
            "A": (Decimal(sender), Decimal(sender)),
            "B": (Decimal(receiver), Decimal(receiver)),
        }
        assert row_a.period_unrealized_delta + row_b.period_unrealized_delta == Decimal("500"), "the total is unchanged"
        print_success(f"A {sender}, B {receiver}")


# =============================================================================
# Green on HEAD and after: the attribution and the values that do not change
# =============================================================================


class TestTransferInTransitAtStart:
    """Already in flight at ``date_from``: today's attribution — the receiver takes its unrealized at the end."""

    @pytest.mark.asyncio
    async def test_the_receiver_takes_its_end_unrealized(self, session, keep_alive, path):
        """Departure 10-08, arrival 10-15: B start 0, end 1500, delta 700 (1500 − 800), P&L 700; A holds nothing at
        either boundary and has no period result."""
        print_section(f"MF-A transfer in transit at the start ({path})")
        scenario = await _transfer_in_transit_at_start(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)

        assert _view(_row(contribution, scenario.book, "B", "X")) == _expected("0", "1500", "700", "700")
        _no_figure(contribution, scenario.book, "A", "X")
        print_success("B 700, A nothing")


class TestTransferInTransitAtEnd:
    """Not yet arrived at ``date_to``: today's attribution — the sender gives up its start unrealized."""

    @pytest.mark.asyncio
    async def test_the_sender_gives_up_its_start_unrealized(self, session, keep_alive, path):
        """Departure 10-15, arrival 11-05: A start 1000, end 0, delta −200 (0 − 200), P&L −200; B has no row in the
        period (its arrival is after it)."""
        print_section(f"MF-A transfer in transit at the end ({path})")
        scenario = await _transfer_in_transit_at_end(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)

        assert _view(_row(contribution, scenario.book, "A", "X")) == _expected("1000", "0", "-200", "-200")
        _no_figure(contribution, scenario.book, "B", "X")
        print_success("A −200, B nothing")


class TestOrdinaryEur:
    """Quotes on both boundaries, a sale in between: the same figures both ways."""

    @pytest.mark.asyncio
    async def test_quotes_on_both_boundaries(self, session, keep_alive, path):
        """Start 10 × 110 = 1100 (cost 1000), end 5 × 130 = 650 (cost 500): delta 150 − 100 = 50; realized 600 − 500 =
        100; P&L 150."""
        print_section(f"MF-A ordinary EUR position ({path})")
        scenario = await _ordinary_eur(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        assert _view(row) == _expected("1100", "650", "50", "150")
        assert row.period_realized_gain_loss == Decimal("100")
        print_success("1100 → 650, P&L 150")


class TestMissingFx:
    """A USD quote with no EUR/USD rate at all: the value cannot be known, both ways."""

    @pytest.mark.asyncio
    async def test_a_missing_rate_leaves_the_value_unknown(self, session, keep_alive, path):
        """Closes 100 and 110 USD on the boundaries, no rate: start, end, delta and P&L None."""
        print_section(f"MF-A missing FX ({path})")
        scenario = await _missing_fx(session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        holding = next(h for h in summary.holdings if h.asset_id == scenario.book.assets["X"].id)
        assert (holding.current_value, holding.missing_fx_pair) == (None, "USD/EUR"), "precondition: the engine has no rate for the USD quote"
        assert _view(row) == _expected(None, None, None, None)
        print_success("no rate, no value")


# =============================================================================
# The rows add up to the engine
# =============================================================================


class TestInvariant:
    """Σ rows' unrealized delta == the engine's period ``ugl_delta``; Σ rows' P&L + Σ other effects == the period P&L.

    Red on HEAD for trade-mark-two-buys, old-foreign-quote and split-after-last-quote; green on HEAD elsewhere."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(INVARIANT_SCENARIOS))
    async def test_the_rows_add_up_to_the_engine_unrealized_delta(self, session, keep_alive, path, name):
        """Σ ``period_unrealized_delta`` (a row without one counts 0) == ``period_unrealized_gain_loss_delta``, exactly."""
        print_section(f"MF-A invariant, unrealized delta: {name} ({path})")
        scenario = await INVARIANT_SCENARIOS[name](session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        rows_delta = sum((row.period_unrealized_delta or ZERO for row in _rows(contribution, scenario.book).values()), ZERO)

        assert summary.period_unrealized_gain_loss_delta is not None
        assert rows_delta == summary.period_unrealized_gain_loss_delta.amount, f"rows {rows_delta}, engine {summary.period_unrealized_gain_loss_delta.amount}"
        print_success(f"Σ rows = {rows_delta}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(INVARIANT_SCENARIOS))
    async def test_rows_and_other_effects_add_up_to_the_period_pnl(self, session, keep_alive, path, name):
        """Σ rows' ``period_pnl`` + Σ ``other_effects`` == the summary's ``period_pnl``: «Other» holds only what is not a
        position's valuation. Up to ``CONVERSION_DUST`` for each row the table hides below it (an FX-on-cash row per
        broker and the residual)."""
        print_section(f"MF-A invariant, period P&L: {name} ({path})")
        scenario = await INVARIANT_SCENARIOS[name](session, keep_alive)

        contribution, summary = await _read(session, scenario, path)
        rows_pnl = sum((row.period_pnl or ZERO for row in _rows(contribution, scenario.book).values()), ZERO)
        other = sum((effect.period_pnl for effect in contribution.other_effects), ZERO)
        hidden_rows = len(scenario.book.brokers) + 1

        assert summary.period_pnl is not None
        gap = rows_pnl + other - summary.period_pnl.amount
        assert abs(gap) <= CONVERSION_DUST * hidden_rows, f"rows {rows_pnl} + other {other} = {rows_pnl + other}, period P&L {summary.period_pnl.amount}"
        print_success(f"rows {rows_pnl} + other {other} = {summary.period_pnl.amount}")


# =============================================================================
# MF-P4b — each component of the period P&L on the row's start value (red on HEAD: the fields do not exist)
# =============================================================================


class TestComponentPercents:
    """The Performance tooltip's percentages: each component / |start_value|, to 4 decimals like ``period_pnl_percent``,
    the costs positive; None without a start value or without the component."""

    @pytest.mark.asyncio
    async def test_each_component_is_a_fraction_of_the_start_value(self, session, keep_alive, path):
        """Start 1000: unrealized 37.29 → 0.03729 → 0.0373 (up), realized 50 → 0.0500, income 12.34 → 0.01234 → 0.0123
        (down), fees 2.57 → 0.00257 → 0.0026 (up, positive). Each rounded on its own: they add up to 0.0970 against the
        row's 97.06 / 1000 → 0.0971."""
        print_section(f"MF-P4b component percents, held at the start ({path})")
        scenario = await _components_held_at_start(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        assert _components(row) == {
            "start_value": Decimal("1000"),
            "period_unrealized_delta": Decimal("37.29"),
            "period_realized_gain_loss": Decimal("50"),
            "period_income": Decimal("12.34"),
            "period_fees_taxes": Decimal("2.57"),
        }, "precondition: every component present on a start of 1000"
        assert (row.period_pnl, row.period_pnl_percent) == (Decimal("97.06"), Decimal("0.0971")), "precondition: the row's own return"
        assert _component_percents(row) == {
            "period_unrealized_delta_percent": Decimal("0.0373"),
            "period_realized_gain_loss_percent": Decimal("0.0500"),
            "period_income_percent": Decimal("0.0123"),
            "period_fees_taxes_percent": Decimal("0.0026"),
        }
        print_success("0.0373 + 0.0500 + 0.0123 − 0.0026 on a start of 1000")

    @pytest.mark.asyncio
    async def test_a_position_opened_in_the_period_has_no_fraction(self, session, keep_alive, path):
        """The same ledger with the BUY inside the period: start 0, every component present, every fraction None (no
        base), like ``period_pnl_percent``."""
        print_section(f"MF-P4b component percents, opened in the period ({path})")
        scenario = await _components_opened_in_period(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "X")

        assert _components(row) == {
            "start_value": ZERO,
            "period_unrealized_delta": Decimal("37.29"),
            "period_realized_gain_loss": Decimal("50"),
            "period_income": Decimal("12.34"),
            "period_fees_taxes": Decimal("2.57"),
        }, "precondition: every component present, nothing held at the start"
        assert row.period_pnl_percent is None, "precondition: no return on a start of 0"
        assert _component_percents(row) == _NO_COMPONENT_PERCENTS
        print_success("start 0, no fraction")

    @pytest.mark.asyncio
    async def test_an_income_only_row_has_no_fraction(self, session, keep_alive, path):
        """A DIVIDEND of 12.34 and a FEE of 2.57 on an asset never traded: a row with start 0 and no position, every
        fraction None."""
        print_section(f"MF-P4b component percents, income-only row ({path})")
        scenario = await _components_income_only(session, keep_alive)

        contribution, _summary = await _read(session, scenario, path)
        row = _row(contribution, scenario.book, "A", "Z")

        assert _components(row) == {
            "start_value": ZERO,
            "period_unrealized_delta": None,
            "period_realized_gain_loss": None,
            "period_income": Decimal("12.34"),
            "period_fees_taxes": Decimal("2.57"),
        }, "precondition: the income-only row"
        assert (row.end_value, row.period_pnl, row.is_fully_sold) == (ZERO, Decimal("9.77"), True), "precondition: no position"
        assert _component_percents(row) == _NO_COMPONENT_PERCENTS
        print_success("income only, no fraction")


# =============================================================================
# MF-A5 — a closed position's annualized return: on the cost of every unit that left it, or the general rule
# =============================================================================


def _annualized(pnl: str, base: str, start: date, end: date) -> Decimal | None:
    """``pnl`` over ``base``, rounded as the service rounds it, annualized over ``start`` → ``end``."""
    return cumulative_to_annualized((Decimal(pnl) / Decimal(base)).quantize(RETURN_STEP), (end - start).days)


def _closed_row(contribution: PositionsContribution, book: _Book, *, delta: str, pnl: str, realized: str | None) -> AssetPeriodContribution:
    """A's row, once proven to be the position intended: 10 × 110 held at the start, nothing at the end, its result."""
    row = _row(contribution, book, "A", "X")
    assert _view(row) == _expected("1100", "0", delta, pnl), "precondition: A's boundaries and result"
    assert (row.period_realized_gain_loss, row.is_fully_sold) == (None if realized is None else Decimal(realized), True), "precondition: fully sold, with its realized"
    return row


class TestClosedPositionBase:
    """A position fully sold in the period annualizes its P&L on a base over its flight time, CB_FROM → CB_DEPARTURE
    (61 days), when its exits are all covered; otherwise the general rule: the P&L on |start value| over CB_FROM →
    CB_TO (105 days). Since MF-A5 the base is the cost of the units sold **and** of those a counted tract moved to a
    broker of the scope; until then (HEAD 203197f5a) the cost sold alone."""

    @pytest.mark.asyncio
    async def test_sold_and_moved_in_scope_the_base_is_both_costs(self, session, keep_alive, path):
        """J's example. A: ΔUGL 0 − 100 + the tract (600 − 500) = 0, realized 625 − 500 = 125: P&L 125 on 500 sold +
        500 moved = 1000, 0.1250 → 1.023376 over 61 days. HEAD: on the 500 sold, 0.2500 → 2.800768. Red on HEAD."""
        print_section(f"MF-A5 closed position, sold and moved in the scope ({path})")
        scenario = await _sold_and_moved_in_scope(session, keep_alive)
        expected, head = _annualized("125", "1000", CB_FROM, CB_DEPARTURE), _annualized("125", "500", CB_FROM, CB_DEPARTURE)
        assert expected is not None and head is not None and expected != head, "precondition: two annualizable returns"

        contribution, _summary = await _read(session, scenario, path)
        row = _closed_row(contribution, scenario.book, delta="0", pnl="125", realized="125")

        assert row.annualized_return == expected, f"expected {expected} (125 / 1000); HEAD gave {head} (125 / 500)"
        print_success(f"125 / 1000 over 61 days: {row.annualized_return}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "builder",
        [
            # broker_ids = [A]: the departure is in-kind capital leaving the scope, no tract.
            pytest.param(_sold_and_moved_out_of_scope, id="moved-out-of-the-scope"),
            # Arrival after CB_TO: the tract is not counted in this period.
            pytest.param(_sold_and_moved_in_transit_at_end, id="still-in-transit-at-the-end"),
        ],
    )
    async def test_a_unit_that_left_another_way_leaves_the_general_rule(self, session, keep_alive, path, builder):
        """Two exits, one sale counted: no base. A: ΔUGL 0 − 100, realized 125, P&L 25 on the start value 1100,
        0.0227 → 0.081152 over 105 days. HEAD: on the 500 sold over the flight time, 0.0500 → 0.339024. Red on HEAD."""
        print_section(f"MF-A5 closed position, a unit left another way: {builder.__name__} ({path})")
        scenario = await builder(session, keep_alive)
        expected, head = _annualized("25", "1100", CB_FROM, CB_TO), _annualized("25", "500", CB_FROM, CB_DEPARTURE)
        assert expected is not None and head is not None and expected != head, "precondition: two annualizable returns"

        contribution, _summary = await _read(session, scenario, path)
        row = _closed_row(contribution, scenario.book, delta="-100", pnl="25", realized="125")

        assert row.annualized_return == expected, f"expected {expected} (25 / 1100 over 105 days); HEAD gave {head} (25 / 500 over 61)"
        print_success(f"the general rule, 25 / 1100 over 105 days: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_sold_only_is_unchanged(self, session, keep_alive, path):
        """Guard. No transfer, two sales: realized 125 + 150 = 275, ΔUGL −100, P&L 175 on the 1000 sold, 0.1750 →
        1.624696 over 61 days. The same on HEAD."""
        print_section(f"MF-A5 closed position, sold only ({path})")
        scenario = await _sold_twice(session, keep_alive)
        expected = _annualized("175", "1000", CB_FROM, CB_DEPARTURE)
        assert expected is not None

        contribution, _summary = await _read(session, scenario, path)
        row = _closed_row(contribution, scenario.book, delta="-100", pnl="175", realized="275")

        assert row.annualized_return == expected
        print_success(f"175 / 1000 over 61 days: {row.annualized_return}")

    @pytest.mark.asyncio
    async def test_moved_only_the_base_is_the_cost_moved(self, session, keep_alive, path):
        """Every unit moved to B, nothing sold. A: ΔUGL 0 − 100 + the tract (1200 − 1000) = 100, no realized: P&L 100
        on the 1000 moved, 0.1000 → 0.768795 over 61 days. HEAD: no cost sold, no closed return — the general rule,
        100 / 1100 → 0.0909 → 0.353155 over 105 days. Red on HEAD."""
        print_section(f"MF-A5 closed position, moved only ({path})")
        scenario = await _moved_whole(session, keep_alive)
        expected, head = _annualized("100", "1000", CB_FROM, CB_DEPARTURE), _annualized("100", "1100", CB_FROM, CB_TO)
        assert expected is not None and head is not None and expected != head, "precondition: two annualizable returns"

        contribution, _summary = await _read(session, scenario, path)
        row = _closed_row(contribution, scenario.book, delta="100", pnl="100", realized=None)

        assert row.annualized_return == expected, f"expected {expected} (100 / 1000 over 61 days); HEAD gave {head} (100 / 1100 over 105)"
        print_success(f"100 / 1000 over 61 days: {row.annualized_return}")
