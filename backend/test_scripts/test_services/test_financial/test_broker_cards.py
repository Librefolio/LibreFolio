"""
MF-B (workstream MF, lot B) — the Dashboard's broker cards read the engine's per-broker slice of the headline.

``PortfolioService.get_summary(include_breakdown=True)`` gives one ``BrokerBreakdown`` card per broker of the user.
Since MF-B a card's ``net_worth`` is ``last_state.broker_contributions[broker].nav_contribution`` and its
``gain_loss`` is ``.pnl_contribution``: the engine's own slices of the headline ``net_worth`` (``nav_value``) and
``total_gain_loss`` (``total_pnl``) on the valuation date, which add up to them by construction. ``cash_total`` is
unchanged: the broker's native cash valued at the valuation date's rates.

Before MF-B (HEAD 45ae068cc) the card summed it itself: the ``current_value`` of the broker's holdings — the end
positions above ``QUANTITY_DUST_THRESHOLD`` (0.00001) only — plus its cash (``native_cash.value_at``) plus its value
in transit (``in_transit_contribution``), and ``gain_loss`` = that − the broker's capital. Same numbers, but for one
case: a dust position (0 < quantity ≤ 0.00001) that the headline counts and the card did not.

Three checks per scenario:

1. the cards add up to the headline: Σ ``net_worth`` == ``net_worth`` and Σ ``gain_loss`` == ``total_gain_loss``,
   exactly;
2. each card is its holdings, its cash and what it has in flight: ``net_worth`` == Σ its holdings' ``current_value``
   + its ``cash_total`` + its value in transit (on the sender's card) + the value of a dust position (never a
   holding row), each in-transit and dust value computed by hand;
3. each card shows the figures computed by hand.

Before any check, the scenario is proven to be the one intended (``_summary``): the headline, the holdings (one row
per expected position, its valuation source and value), each card's ``cash_total`` and the value in transit — every
figure the change does not touch.

Scenarios (report currency EUR, every asset quoted in EUR):

- ``two-eur-brokers`` — A: DEPOSIT 10000, BUY 10 X for 1000 and 5 Y for 1000, closes 113 and 177 → 2015 + cash 8000
  = 10015, gain 15; B: DEPOSIT 3000, BUY 20 Z for 1000, close 61 → 1220 + 2000 = 3220, gain 220. Headline 13235 / 235;
- ``no-event-on-the-valuation-day`` — the same ledger valued on Sunday 2025-02-02: the last quote is Friday's, no row
  on the day, the engine reuses Friday's state. Same figures;
- ``foreign-cash-revalued`` — U: DEPOSIT 1000 USD (EUR/USD 1.25: 800 EUR) and 2000 EUR, BUY 10 X for 1000 EUR; after
  the last transaction EUR/USD moves to 1.6 (1 USD = 0.625 EUR); X closes at 110. Card: 1100 + cash 1000 + 625 = 2725,
  capital 2800, gain −75. E: DEPOSIT 500. Headline 3225 / −75. The rates sit in 2046, where no other test writes
  EUR/USD;
- ``held-at-cost`` — A: DEPOSIT 1000, BUY 10 X for 1000 (close 113: 1130), ADJUSTMENT +5 W at a cost of 40 a unit with
  no price at all → ``ESTIMATED_AT_COST`` 200 (J-17), capital 1000 + 200; card 1330, gain 130. B: DEPOSIT 700.
  Headline 2030 / 130;
- ``security-in-transit`` — S: DEPOSIT 5000, BUY 10 X for 1000, TRANSFER −10 on 03-04 that reaches R on 03-10; X
  closes 120 on 03-05; valued on 03-06: S holds cash 4000 and the 10 X in flight, 1200: 5200, gain 200. R: DEPOSIT 300.
  Headline 5500 / 200;
- ``cash-in-transit`` — S: DEPOSIT 5000, BUY 10 X for 1000 (close 120), CASH_TRANSFER −1000 on 03-04 reaching R on
  03-10; valued on 03-06: S 1200 + cash 3000 + 1000 in flight = 5200, gain 200. R: DEPOSIT 300. Headline 5500 / 200;
- ``dust-residual`` — A: DEPOSIT 5000, BUY 1 X for 1000, SELL 0.999998 for 999.998; X closes 1000: 0.000002 held,
  worth 0.002, no holding row (at or below the dust threshold). A: cash 4999.998 + 0.002 = 5000, gain 0. B: DEPOSIT
  3000, BUY 20 Z for 1000, close 61: 3220, gain 220. Headline 8220 / 220.

Green on HEAD and after: every scenario but ``dust-residual``, for all three checks (parity pins).

Red on HEAD, green after: ``dust-residual``, for all three checks — HEAD's card A was 4999.998 with a gain of −0.002:
the cards added up to 8219.998 / 219.998 against a headline of 8220 / 220.

Isolation: every test owns its user, brokers and assets (unique names) and writes only through a session that is
rolled back: nothing is committed. Amounts are in EUR and read in EUR (``target_currency_override``) but for the USD
cash of ``foreign-cash-revalued``, whose two EUR/USD rates are flushed with the rest and rolled back. The report, WAC
and engine blob caches are emptied around each test. Cards and holdings are found by the test's own broker and asset
ids; the user owns only the test's brokers, so its cards are all of them.

Reference: backend/app/services/portfolio_service.py (get_summary, the by_broker loop),
backend/app/services/financial_math/portfolio/daily_state.py (BrokerDailyContribution).
"""

import sys
from collections.abc import Awaitable, Callable, Mapping
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

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import BrokerBreakdown, PortfolioSummary
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services._range_bounds import lift_range_bound
from backend.test_scripts.test_utils import print_section, print_success

EUR = "EUR"
USD = "USD"
ZERO = Decimal("0")

# two-eur-brokers, no-event-on-the-valuation-day, held-at-cost, dust-residual
OPEN_DAY = date(2025, 1, 2)
SELL_DAY = date(2025, 1, 15)
FRIDAY = date(2025, 1, 31)  # every close
SUNDAY = date(2025, 2, 2)  # no row of any kind

# security-in-transit, cash-in-transit
TRANSIT_OPEN = date(2025, 3, 3)
DEPARTURE = date(2025, 3, 4)
TRANSIT_CLOSE = date(2025, 3, 5)
IN_FLIGHT = date(2025, 3, 6)  # the valuation date
ARRIVAL = date(2025, 3, 10)

# foreign-cash-revalued: a year no other test writes EUR/USD in
FX_DEPOSIT = date(2046, 3, 1)
FX_BUY = date(2046, 3, 2)
FX_RATE_MOVE = date(2046, 3, 5)  # after the last transaction
FX_CLOSE = date(2046, 3, 8)
FX_VALUATION = date(2046, 3, 10)


# =============================================================================
# HELPERS
# =============================================================================


@dataclass
class _Book:
    """One user owning 100 % of the test's brokers, and the test's EUR assets, each by a label."""

    user: User
    brokers: dict[str, Broker]
    assets: dict[str, Asset]


@dataclass(frozen=True)
class _Card:
    """A card as computed by hand. ``in_transit`` and ``dust`` are the parts of ``net_worth`` that are neither a
    holding row nor cash: the value this broker has in flight, and the value of its positions at or below the dust
    threshold."""

    net_worth: str
    gain_loss: str
    cash_total: str
    in_transit: str = "0"
    dust: str = "0"


@dataclass(frozen=True)
class _Holding:
    """A holding row the scenario must show: how it is valued and what it is worth."""

    source: str
    value: str
    quoted_on: date | None = None


@dataclass(frozen=True)
class _Scenario:
    book: _Book
    valuation_date: date
    net_worth: str
    total_gain_loss: str
    cards: dict[str, _Card]
    holdings: dict[tuple[str, str], _Holding]
    in_transit_market_value: str | None = None


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


async def _book(session: AsyncSession, keep_alive: list[object], label: str, brokers: tuple[str, ...], assets: tuple[str, ...]) -> _Book:
    tag = uuid4().hex[:12]
    user = User(username=f"mfb_{label}_{tag}", email=f"mfb_{label}_{tag}@test.com", hashed_password="fakehash", is_active=True)
    broker_rows = {name: Broker(name=f"MfB {label} {name} {tag}") for name in brokers}
    asset_rows = {name: Asset(display_name=f"MfB {label} {name} {tag}", currency=EUR, asset_type=AssetType.STOCK) for name in assets}
    await _persist(session, keep_alive, user, *broker_rows.values(), *asset_rows.values())
    await _persist(session, keep_alive, *(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in broker_rows.values()))
    return _Book(user=user, brokers=broker_rows, assets=asset_rows)


def _cash(book: _Book, broker: str, kind: TransactionType, day: date, amount: str, currency: str = EUR) -> Transaction:
    return Transaction(broker_id=book.brokers[broker].id, asset_id=None, type=kind, date=day, quantity=ZERO, amount=Decimal(amount), currency=currency)


def _trade(book: _Book, broker: str, asset: str, kind: TransactionType, day: date, quantity: str, amount: str) -> Transaction:
    return Transaction(broker_id=book.brokers[broker].id, asset_id=book.assets[asset].id, type=kind, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=EUR)


def _close(book: _Book, asset: str, day: date, close: str) -> PriceHistory:
    price = Decimal(close)
    return PriceHistory(asset_id=book.assets[asset].id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf_b_test")


async def _link(session: AsyncSession, departure: Transaction, arrival: Transaction) -> None:
    """A linked pair references itself both ways: the ids exist only after the first flush."""
    departure.related_transaction_id = arrival.id
    arrival.related_transaction_id = departure.id
    await session.flush()


# =============================================================================
# SCENARIOS
# =============================================================================


async def _two_eur_brokers_ledger(session: AsyncSession, keep_alive: list[object], label: str) -> _Book:
    book = await _book(session, keep_alive, label, ("A", "B"), ("X", "Y", "Z"))
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, OPEN_DAY, "10000"),
        _trade(book, "A", "X", TransactionType.BUY, OPEN_DAY, "10", "-1000"),
        _trade(book, "A", "Y", TransactionType.BUY, OPEN_DAY, "5", "-1000"),
        _cash(book, "B", TransactionType.DEPOSIT, OPEN_DAY, "3000"),
        _trade(book, "B", "Z", TransactionType.BUY, OPEN_DAY, "20", "-1000"),
        _close(book, "X", FRIDAY, "113"),
        _close(book, "Y", FRIDAY, "177"),
        _close(book, "Z", FRIDAY, "61"),
    )
    return book


_TWO_EUR_CARDS = {"A": _Card("10015", "15", "8000"), "B": _Card("3220", "220", "2000")}


async def _two_eur_brokers(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _two_eur_brokers_ledger(session, keep_alive, "two")
    holdings = {("A", "X"): _Holding("MARKET_PRICE", "1130", FRIDAY), ("A", "Y"): _Holding("MARKET_PRICE", "885", FRIDAY), ("B", "Z"): _Holding("MARKET_PRICE", "1220", FRIDAY)}
    return _Scenario(book=book, valuation_date=FRIDAY, net_worth="13235", total_gain_loss="235", cards=_TWO_EUR_CARDS, holdings=holdings)


async def _no_event_on_the_valuation_day(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    assert (FRIDAY.weekday(), SUNDAY.weekday()) == (4, 6), "precondition: the last quote on a Friday, the valuation on the Sunday after"
    book = await _two_eur_brokers_ledger(session, keep_alive, "sunday")
    # Every price is Friday's, carried to Sunday.
    holdings = {("A", "X"): _Holding("MARKET_PRICE", "1130", FRIDAY), ("A", "Y"): _Holding("MARKET_PRICE", "885", FRIDAY), ("B", "Z"): _Holding("MARKET_PRICE", "1220", FRIDAY)}
    return _Scenario(book=book, valuation_date=SUNDAY, net_worth="13235", total_gain_loss="235", cards=_TWO_EUR_CARDS, holdings=holdings)


async def _foreign_cash_revalued(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "usd", ("U", "E"), ("X",))
    await _persist(
        session,
        keep_alive,
        # Stored alphabetically, 1 EUR = rate USD: 1 USD = 1 / 1.25 = 0.8 EUR, then 1 / 1.6 = 0.625 EUR.
        FxRate(date=FX_DEPOSIT, base=EUR, quote=USD, rate=Decimal("1.25"), source="TEST"),
        FxRate(date=FX_RATE_MOVE, base=EUR, quote=USD, rate=Decimal("1.6"), source="TEST"),
        _cash(book, "U", TransactionType.DEPOSIT, FX_DEPOSIT, "1000", currency=USD),
        _cash(book, "U", TransactionType.DEPOSIT, FX_DEPOSIT, "2000"),
        _trade(book, "U", "X", TransactionType.BUY, FX_BUY, "10", "-1000"),
        _cash(book, "E", TransactionType.DEPOSIT, FX_DEPOSIT, "500"),
        _close(book, "X", FX_CLOSE, "110"),
    )
    # U: 1100 + cash (1000 EUR + 1000 USD × 0.625) = 2725 on a capital of 800 + 2000.
    cards = {"U": _Card("2725", "-75", "1625"), "E": _Card("500", "0", "500")}
    return _Scenario(book=book, valuation_date=FX_VALUATION, net_worth="3225", total_gain_loss="-75", cards=cards, holdings={("U", "X"): _Holding("MARKET_PRICE", "1100", FX_CLOSE)})


async def _held_at_cost(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "atcost", ("A", "B"), ("X", "W"))
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, OPEN_DAY, "1000"),
        _trade(book, "A", "X", TransactionType.BUY, OPEN_DAY, "10", "-1000"),
        # In kind, no cash, no quote, no BUY or SELL: W has no price at all.
        Transaction(broker_id=book.brokers["A"].id, asset_id=book.assets["W"].id, type=TransactionType.ADJUSTMENT, date=OPEN_DAY, quantity=Decimal("5"), amount=ZERO, cost_basis_override=Decimal("40"), cost_basis_currency=EUR),
        _cash(book, "B", TransactionType.DEPOSIT, OPEN_DAY, "700"),
        _close(book, "X", FRIDAY, "113"),
    )
    # A: 1130 + 200 + cash 0, on a capital of 1000 deposited + 200 in kind.
    cards = {"A": _Card("1330", "130", "0"), "B": _Card("700", "0", "700")}
    holdings = {("A", "X"): _Holding("MARKET_PRICE", "1130", FRIDAY), ("A", "W"): _Holding("ESTIMATED_AT_COST", "200")}
    return _Scenario(book=book, valuation_date=FRIDAY, net_worth="2030", total_gain_loss="130", cards=cards, holdings=holdings)


async def _security_in_transit(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "secflight", ("S", "R"), ("X",))
    departure = Transaction(broker_id=book.brokers["S"].id, asset_id=book.assets["X"].id, type=TransactionType.TRANSFER, date=DEPARTURE, quantity=Decimal("-10"), amount=ZERO)
    arrival = Transaction(broker_id=book.brokers["R"].id, asset_id=book.assets["X"].id, type=TransactionType.TRANSFER, date=ARRIVAL, quantity=Decimal("10"), amount=ZERO)
    await _persist(
        session,
        keep_alive,
        _cash(book, "S", TransactionType.DEPOSIT, TRANSIT_OPEN, "5000"),
        _trade(book, "S", "X", TransactionType.BUY, TRANSIT_OPEN, "10", "-1000"),
        departure,
        arrival,
        _cash(book, "R", TransactionType.DEPOSIT, TRANSIT_OPEN, "300"),
        _close(book, "X", TRANSIT_CLOSE, "120"),
    )
    await _link(session, departure, arrival)
    # S holds no X (it left), R holds none yet (it arrives later): no holding row; the 10 X in flight, 10 × 120, are S's.
    cards = {"S": _Card("5200", "200", "4000", in_transit="1200"), "R": _Card("300", "0", "300")}
    return _Scenario(book=book, valuation_date=IN_FLIGHT, net_worth="5500", total_gain_loss="200", cards=cards, holdings={}, in_transit_market_value="1200")


async def _cash_in_transit(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    book = await _book(session, keep_alive, "cashflight", ("S", "R"), ("X",))
    departure = _cash(book, "S", TransactionType.CASH_TRANSFER, DEPARTURE, "-1000")
    arrival = _cash(book, "R", TransactionType.CASH_TRANSFER, ARRIVAL, "1000")
    await _persist(
        session,
        keep_alive,
        _cash(book, "S", TransactionType.DEPOSIT, TRANSIT_OPEN, "5000"),
        _trade(book, "S", "X", TransactionType.BUY, TRANSIT_OPEN, "10", "-1000"),
        departure,
        arrival,
        _cash(book, "R", TransactionType.DEPOSIT, TRANSIT_OPEN, "300"),
        _close(book, "X", TRANSIT_CLOSE, "120"),
    )
    await _link(session, departure, arrival)
    # S: 1200 + cash 5000 − 1000 − 1000 + the 1000 in flight; R's arrival is after the valuation date.
    cards = {"S": _Card("5200", "200", "3000", in_transit="1000"), "R": _Card("300", "0", "300")}
    return _Scenario(book=book, valuation_date=IN_FLIGHT, net_worth="5500", total_gain_loss="200", cards=cards, holdings={("S", "X"): _Holding("MARKET_PRICE", "1200", TRANSIT_CLOSE)}, in_transit_market_value="1000")


async def _dust_residual(session: AsyncSession, keep_alive: list[object]) -> _Scenario:
    residual = Decimal("1") - Decimal("0.999998")
    assert ZERO < residual <= QUANTITY_DUST_THRESHOLD, f"precondition: {residual} is a dust residual"
    book = await _book(session, keep_alive, "dust", ("A", "B"), ("X", "Z"))
    await _persist(
        session,
        keep_alive,
        _cash(book, "A", TransactionType.DEPOSIT, OPEN_DAY, "5000"),
        _trade(book, "A", "X", TransactionType.BUY, OPEN_DAY, "1", "-1000"),
        _trade(book, "A", "X", TransactionType.SELL, SELL_DAY, "-0.999998", "999.998"),
        _cash(book, "B", TransactionType.DEPOSIT, OPEN_DAY, "3000"),
        _trade(book, "B", "Z", TransactionType.BUY, OPEN_DAY, "20", "-1000"),
        _close(book, "X", FRIDAY, "1000"),
        _close(book, "Z", FRIDAY, "61"),
    )
    # A: no holding row (0.000002 X is dust), cash 5000 − 1000 + 999.998, and the dust's 0.000002 × 1000 = 0.002.
    cards = {"A": _Card("5000", "0", "4999.998", dust="0.002"), "B": _Card("3220", "220", "2000")}
    return _Scenario(book=book, valuation_date=FRIDAY, net_worth="8220", total_gain_loss="220", cards=cards, holdings={("B", "Z"): _Holding("MARKET_PRICE", "1220", FRIDAY)})


SCENARIOS: dict[str, Callable[[AsyncSession, list[object]], Awaitable[_Scenario]]] = {
    "two-eur-brokers": _two_eur_brokers,
    "no-event-on-the-valuation-day": _no_event_on_the_valuation_day,
    "foreign-cash-revalued": _foreign_cash_revalued,
    "held-at-cost": _held_at_cost,
    "security-in-transit": _security_in_transit,
    "cash-in-transit": _cash_in_transit,
    # Red on HEAD: the card left the dust position out, the headline did not.
    "dust-residual": _dust_residual,
}


# =============================================================================
# READING AND CHECKING
# =============================================================================


def _cards_by_label(summary: PortfolioSummary, book: _Book) -> dict[str, BrokerBreakdown]:
    by_id = {card.broker_id: card for card in summary.by_broker or []}
    return {label: by_id[broker.id] for label, broker in book.brokers.items() if broker.id in by_id}


def _holding_problems(summary: PortfolioSummary, scenario: _Scenario) -> list[str]:
    """The holding rows against the scenario's: one per expected (broker, asset), each valued as expected."""
    problems: list[str] = []
    broker_labels = {broker.id: label for label, broker in scenario.book.brokers.items()}
    asset_labels = {asset.id: label for label, asset in scenario.book.assets.items()}
    shown = {(broker_labels.get(h.broker_id, h.broker_id), asset_labels.get(h.asset_id, h.asset_id)): h for h in summary.holdings}
    if set(shown) != set(scenario.holdings):
        problems.append(f"holdings {sorted(map(str, shown))}, expected {sorted(map(str, scenario.holdings))}")
    for key, expected in scenario.holdings.items():
        holding = shown.get(key)
        if holding is None:
            continue
        if (holding.valuation_source, holding.current_value) != (expected.source, Decimal(expected.value)):
            problems.append(f"holding {key}: {holding.valuation_source} {holding.current_value}, expected {expected.source} {expected.value}")
        if expected.quoted_on is not None and holding.valuation_reference_date != expected.quoted_on:
            problems.append(f"holding {key}: priced as of {holding.valuation_reference_date}, expected {expected.quoted_on}")
    return problems


def _precondition_problems(summary: PortfolioSummary, scenario: _Scenario) -> list[str]:
    """Every figure the change does not touch, against the scenario: the headline, the holdings, each card's cash and
    the value in transit."""
    problems: list[str] = []
    book = scenario.book
    if (summary.net_worth.amount, summary.total_gain_loss.amount) != (Decimal(scenario.net_worth), Decimal(scenario.total_gain_loss)):
        problems.append(f"headline net_worth / total_gain_loss {summary.net_worth.amount} / {summary.total_gain_loss.amount}, expected {scenario.net_worth} / {scenario.total_gain_loss}")
    in_transit = summary.in_transit_market_value.amount if summary.in_transit_market_value is not None else None
    if in_transit != (Decimal(scenario.in_transit_market_value) if scenario.in_transit_market_value is not None else None):
        problems.append(f"headline in_transit_market_value {in_transit}, expected {scenario.in_transit_market_value}")
    problems += _holding_problems(summary, scenario)

    cards = _cards_by_label(summary, book)
    if summary.by_broker is None or len(summary.by_broker) != len(book.brokers) or set(cards) != set(book.brokers):
        problems.append(f"cards {[card.broker_id for card in summary.by_broker or []]}, expected one per broker {[broker.id for broker in book.brokers.values()]}")
    for label, expected in scenario.cards.items():
        card = cards.get(label)
        if card is not None and card.cash_total.amount != Decimal(expected.cash_total):
            problems.append(f"card {label}: cash_total {card.cash_total.amount}, expected {expected.cash_total}")
    return problems


async def _summary(session: AsyncSession, scenario: _Scenario) -> PortfolioSummary:
    """The scenario's summary with its cards, once proven to be the scenario intended."""
    summary = await PortfolioService(session).get_summary(user_id=scenario.book.user.id, include_breakdown=True, target_currency_override=EUR, date_to=scenario.valuation_date)
    problems = _precondition_problems(summary, scenario)
    assert not problems, "precondition — not the scenario intended:\n" + "\n".join(problems)
    return summary


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the foreign-cash-revalued scenario lives in 2046, after tomorrow, so the range bound is lifted for the
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


def _sum(cards: Mapping[str, BrokerBreakdown], read: Callable[[BrokerBreakdown], Decimal]) -> Decimal:
    return sum((read(card) for card in cards.values()), ZERO)


# =============================================================================
# TESTS — green on HEAD and after, but dust-residual (red on HEAD)
# =============================================================================


class TestBrokerCards:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(SCENARIOS))
    async def test_the_cards_add_up_to_the_headline(self, session, keep_alive, name):
        """Σ cards' net_worth == the headline net_worth and Σ cards' gain_loss == total_gain_loss, exactly."""
        print_section(f"MF-B broker cards add up to the headline: {name}")
        scenario = await SCENARIOS[name](session, keep_alive)
        summary = await _summary(session, scenario)
        cards = _cards_by_label(summary, scenario.book)

        net_worth = _sum(cards, lambda card: card.net_worth.amount)
        gain_loss = _sum(cards, lambda card: card.gain_loss.amount)

        problems = []
        if net_worth != summary.net_worth.amount:
            problems.append(f"Σ cards' net_worth {net_worth} != headline net_worth {summary.net_worth.amount}")
        if gain_loss != summary.total_gain_loss.amount:
            problems.append(f"Σ cards' gain_loss {gain_loss} != headline total_gain_loss {summary.total_gain_loss.amount}")
        assert not problems, "\n".join(problems)
        print_success(f"cards add up to {net_worth} / {gain_loss}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(SCENARIOS))
    async def test_each_card_is_its_holdings_its_cash_and_what_it_has_in_flight(self, session, keep_alive, name):
        """net_worth == Σ the broker's holdings' current_value + its cash_total + its value in transit + the value of
        its dust positions (the last two computed by hand)."""
        print_section(f"MF-B broker card composition: {name}")
        scenario = await SCENARIOS[name](session, keep_alive)
        summary = await _summary(session, scenario)
        cards = _cards_by_label(summary, scenario.book)

        problems = []
        for label, expected in scenario.cards.items():
            broker_id = scenario.book.brokers[label].id
            values = [holding.current_value for holding in summary.holdings if holding.broker_id == broker_id]
            assert None not in values, f"precondition: every holding of card {label} has a value"
            parts = sum(values, ZERO) + cards[label].cash_total.amount + Decimal(expected.in_transit) + Decimal(expected.dust)
            if cards[label].net_worth.amount != parts:
                problems.append(f"card {label}: net_worth {cards[label].net_worth.amount} != holdings {sum(values, ZERO)} + cash {cards[label].cash_total.amount} + in transit {expected.in_transit} + dust {expected.dust} = {parts}")
        assert not problems, "\n".join(problems)
        print_success("every card is its holdings, its cash and what it has in flight")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", list(SCENARIOS))
    async def test_each_card_shows_the_figures_computed_by_hand(self, session, keep_alive, name):
        """Each card's net_worth and gain_loss, as computed in the scenario."""
        print_section(f"MF-B broker card figures: {name}")
        scenario = await SCENARIOS[name](session, keep_alive)
        summary = await _summary(session, scenario)
        cards = _cards_by_label(summary, scenario.book)

        problems = []
        for label, expected in scenario.cards.items():
            shown = (cards[label].net_worth.amount, cards[label].gain_loss.amount)
            if shown != (Decimal(expected.net_worth), Decimal(expected.gain_loss)):
                problems.append(f"card {label}: net_worth / gain_loss {shown[0]} / {shown[1]}, expected {expected.net_worth} / {expected.gain_loss}")
        assert not problems, "\n".join(problems)
        print_success("every card as computed by hand")
