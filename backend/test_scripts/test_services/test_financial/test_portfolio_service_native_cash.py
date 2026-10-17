"""
PortfolioService on the engine's native cash (lot 41, steps F-3 and F-W).

Step F-3 makes the service read cash, period flows, histories and contribution flows from the
engine's single native-cash reconstruction (financial_math/native_cash.py) instead of its own
transaction loops, so that the cards, the headline, the period totals, the income / cost /
deposit histories and the contribution rows all describe the same movements.

Policy (a): a foreign movement with no rate on its own date stays out of value and capital, is
still listed in its own currency, and is reported as missing with its own date.

Red until step F-3:

- TestCardCashPolicyA, the first two tests: a card valued a foreign deposit that had no rate on
  its own date at the valuation-date rate, and the headline dropped a currency with no rate at
  all and reported it missing on the valuation date as well;
- TestNoDateToStopsAtToday (B12): without date_to, the deposit, income and cost histories and
  the contribution view read the rows dated after today, where the engine stops.

Pinned, green before and after F-3:

- TestCardCashPolicyA, zero-only and empty brokers;
- TestPeriodIncomeParity (B14): the summary's period income equals the contribution view's
  unallocated income;
- TestReportHistoriesEqualDirectCalls: get_report and the direct getters return the same
  histories, every Decimal with the same exponent.

Step F-W adds to the contribution view's other_effects one "FX on cash" row (category Other)
per broker of the scope whose foreign cash gained or lost to exchange over the period
(NativeCash.exchange_results), at least CONVERSION_DUST in absolute value, in the order the
service reads the user's broker accesses, after every unallocated income and cost row and
before the reconciliation residual, which shrinks by their sum. In a scope with foreign cash
the residual is shown only from CONVERSION_DUST up; a report-currency-only scope still shows
any non-zero residual. The summary's period_other_result does not change: the FX rows and the
residual add up to it.

Red until step F-W, in TestFxOnCashContributionRows: S1 and its unallocated-income variant, S2,
S3, S4 on the mixed scope, S5 and S7. Pinned, green before and after F-W: S4 restricted to the
EUR-only broker, and S6, cash in transit, whose exchange result stays in the residual (a
documented limit, as is S5's conversion spread).

Isolation: no other test uses SBD, VUV, TOP, WST, FJD or KMF, nor the years 2039 and 2040, so no
row outside a test can give these currencies a rate or a movement. Each test owns its users and
brokers, in a session that is rolled back; each F-W scenario has a month of 2040 to itself.
FxRate requires base < quote, so a rate is stored as base EUR, quote X, rate = X per 1 EUR
(EUR/FJD 1.25 is 1 FJD = 0.8 EUR). VUV and TOP never get a rate. The B12 rows are dated
relative to today and sit at least two days from it, so a midnight between the test and the
service cannot move a row to the other side of today.

Reference: backend/app/services/portfolio_service.py
"""

import sys
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.native_cash as native_cash_module
import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Broker, BrokerUserAccess, FxRate, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency, OpenDateRangeModel
from backend.app.schemas.portfolio import BrokerBreakdown, CostHistorySeries, DepositHistorySeries, IncomeHistorySeries, PortfolioReportQuery, PortfolioSummary, PositionsContribution
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services._range_bounds import lift_range_bound

_HistorySeries = IncomeHistorySeries | CostHistorySeries | DepositHistorySeries

# =============================================================================
# HELPERS
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one.

    The identity map holds flushed objects weakly: once nothing references one, a later query
    reloads it from the database, where a Numeric column comes back at its column scale. Kept
    alive, every query of the test returns the rows exactly as built, so two computations of
    the same test read the same Decimals."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


def _new_user(prefix: str) -> User:
    username = f"{prefix}_{uuid4().hex}"
    return User(username=username, email=f"{username}@test.com", hashed_password="fakehash", is_active=True)


async def _owned_broker(session: AsyncSession, keep_alive: list[object], owner: User, label: str, share: Decimal) -> Broker:
    """A new broker owned by ``owner`` at ``share`` (an OWNER's share scales every amount)."""
    broker = Broker(name=f"PfNc_{label}_{uuid4().hex[:12]}")
    await _persist(session, keep_alive, broker)
    await _persist(session, keep_alive, BrokerUserAccess(broker_id=broker.id, user_id=owner.id, role=UserRole.OWNER, share_percentage=share))
    return broker


async def _viewed_broker(session: AsyncSession, keep_alive: list[object], viewer: User, label: str) -> Broker:
    """A new broker owned 100% by a new user, that ``viewer`` only sees.

    A VIEWER carries share 0 (the column is NOT NULL, and the schema rule gives share to
    owners only) and is scaled at 1: it sees the broker's full data."""
    owner = _new_user("pfnc_o")
    broker = Broker(name=f"PfNc_{label}_{uuid4().hex[:12]}")
    await _persist(session, keep_alive, owner, broker)
    await _persist(
        session,
        keep_alive,
        BrokerUserAccess(broker_id=broker.id, user_id=owner.id, role=UserRole.OWNER, share_percentage=Decimal("1.000000")),
        BrokerUserAccess(broker_id=broker.id, user_id=viewer.id, role=UserRole.VIEWER, share_percentage=Decimal("0")),
    )
    return broker


def _cash_row(broker: Broker, tx_type: TransactionType, on: date, amount: str, currency: str) -> Transaction:
    """A cash-only row: no asset, quantity 0."""
    return Transaction(broker_id=broker.id, asset_id=None, type=tx_type, date=on, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)


def _eur_rate(quote: str, on: date, rate: str) -> FxRate:
    """1 EUR = ``rate`` ``quote`` from ``on`` (base EUR < quote, as FxRate's check requires)."""
    return FxRate(date=on, base="EUR", quote=quote, rate=Decimal(rate), source="TEST")


def _balances(balances: list[Currency]) -> list[tuple[str, Decimal]]:
    return [(balance.code, balance.amount) for balance in balances]


def _card(summary: PortfolioSummary, broker: Broker) -> BrokerBreakdown:
    card = next((card for card in summary.by_broker or [] if card.broker_id == broker.id), None)
    assert card is not None, f"the summary has no card for broker {broker.id}"
    return card


def _missing_dates(summary: PortfolioSummary, pair: str) -> list[date] | None:
    """The dates data_quality reports ``pair`` missing on, as listed; None if it does not report the pair."""
    entries = [entry for entry in (summary.data_quality.missing_fx_pairs if summary.data_quality else []) if entry.pair == pair]
    return [day for entry in entries for day in entry.dates] if entries else None


def _value_problems(when: str, rows: list[tuple[str, Any, Any]]) -> list[str]:
    """One line for each (name, expected, got) whose values differ."""
    return [f"{when}: {name} expected {want}, got {got}" for name, want, got in rows if got != want]


def _headline_problems(summary: PortfolioSummary, when: str) -> list[str]:
    """The headline cash_total, net_worth and total_gain_loss, each against its sum over the cards."""
    cards = summary.by_broker or []
    sums = (
        ("cash_total", sum((card.cash_total.amount for card in cards), Decimal("0")), summary.cash_total.amount),
        ("net_worth", sum((card.net_worth.amount for card in cards), Decimal("0")), summary.net_worth.amount),
        ("total_gain_loss", sum((card.gain_loss.amount for card in cards), Decimal("0")), summary.total_gain_loss.amount),
    )
    return [f"{when}: the cards add up to {cards_sum} of {name}, the headline says {headline}" for name, cards_sum, headline in sums if cards_sum != headline]


def _dump(value: Any) -> Any:
    """``value`` with every Decimal written by str() and every date in ISO form.

    Models are dumped in python mode and every Decimal goes through str(), which keeps its
    exponent: "10.0", "1E+1" and "10" stay distinct. mode="json" would not: SafeDecimal
    serializes with format(v, "f"), which hides an exponent drift."""
    if isinstance(value, BaseModel):
        return _dump(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_dump(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _section_problems(name: str, from_report: _HistorySeries | None, direct: _HistorySeries, minimum: int) -> list[str]:
    """The report's ``name`` section against the direct getter's, plus a floor on the points."""
    if from_report is None:
        return [f"{name}: get_report returned no section"]
    problems = []
    if _dump(from_report) != _dump(direct):
        problems.append(f"{name}: get_report returned {_dump(from_report)}, the direct getter {_dump(direct)}")
    problems += [f"{name}: {source} returned {len(series.points)} points, at least {minimum} expected" for source, series in (("get_report", from_report), ("the direct getter", direct)) if len(series.points) < minimum]
    return problems


async def _seed_around_today(session: AsyncSession, keep_alive: list[object], broker: Broker, today: date) -> None:
    """The B12 rows: each flow once five days before today and once five days after it."""
    before, after = today - timedelta(days=5), today + timedelta(days=5)
    await _persist(
        session,
        keep_alive,
        _cash_row(broker, TransactionType.DEPOSIT, before, "1000", "EUR"),
        _cash_row(broker, TransactionType.DEPOSIT, after, "400", "EUR"),
        _cash_row(broker, TransactionType.DIVIDEND, before, "30", "EUR"),
        _cash_row(broker, TransactionType.DIVIDEND, after, "20", "EUR"),
        _cash_row(broker, TransactionType.FEE, before, "-4", "EUR"),
        _cash_row(broker, TransactionType.FEE, after, "-6", "EUR"),
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the native-cash scenarios here live in 2039–2040, after tomorrow, so the range bound is lifted for the
    whole module, before any fixture builds data (see ``lift_range_bound``); the today-relative ones end by tomorrow."""
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


@pytest_asyncio.fixture
async def test_user(session, keep_alive) -> User:
    user = _new_user("pfnc_u")
    await _persist(session, keep_alive, user)
    return user


@pytest_asyncio.fixture
async def broker_a(session, keep_alive, test_user) -> Broker:
    """Broker A, owned 100% by test_user."""
    return await _owned_broker(session, keep_alive, test_user, "A", Decimal("1.0"))


@pytest.fixture(autouse=True)
def clean_portfolio_caches(request):
    """No cached report, WAC or engine blob crosses into or out of a test."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# TestCardCashPolicyA
# =============================================================================


class TestCardCashPolicyA:
    """Card and headline cash at a valuation date given by date_to, under policy (a)."""

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_foreign_deposit_without_rate_on_its_date_stays_out_of_card_value(self, session, keep_alive, test_user, broker_a):
        """A foreign deposit with no rate on its own date stays out of the card's value and
        capital, is still listed in its own currency, and is missing on its own date.

        Broker A (owned 100%): 900 SBD deposited on 2039-01-01, 1000 EUR on 01-02. The only
        EUR/SBD rate is 10 on 01-03 (1 SBD = 0.1 EUR): there is none on or before 01-01. Summary
        with breakdown at 2039-01-05: card A cash_total 1000, net_worth 1000, gain_loss 0,
        gain_loss_percent 0, cash_balances [SBD 900, EUR 1000] in this order. Headline
        cash_total 1000, net_worth 1000, total_gain_loss 0, each the sum over the cards; the
        headline cash_balances hold SBD 900 and EUR 1000. data_quality reports SBD/EUR missing
        on 2039-01-01 only.

        Before F-3 the card valued the 900 SBD at the 01-05 rate (backfilled from 01-03):
        cash_total 1090, net_worth 1090, gain_loss 90, gain_loss_percent 0.09, while the headline
        (the engine) said 1000 and 0, so the cards added up to 1090 against a headline of 1000."""
        await _persist(
            session,
            keep_alive,
            _eur_rate("SBD", date(2039, 1, 3), "10"),
            _cash_row(broker_a, TransactionType.DEPOSIT, date(2039, 1, 1), "900", "SBD"),
            _cash_row(broker_a, TransactionType.DEPOSIT, date(2039, 1, 2), "1000", "EUR"),
        )

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2039, 1, 5))

        when = "2039-01-05"
        card = _card(summary, broker_a)
        problems = _value_problems(
            when,
            [
                ("card A cash_total", Decimal("1000"), card.cash_total.amount),
                ("card A net_worth", Decimal("1000"), card.net_worth.amount),
                ("card A gain_loss", Decimal("0"), card.gain_loss.amount),
                ("card A gain_loss_percent", Decimal("0"), card.gain_loss_percent),
                ("card A cash_balances", [("SBD", Decimal("900")), ("EUR", Decimal("1000"))], _balances(card.cash_balances)),
                ("headline cash_total", Decimal("1000"), summary.cash_total.amount),
                ("headline net_worth", Decimal("1000"), summary.net_worth.amount),
                ("headline total_gain_loss", Decimal("0"), summary.total_gain_loss.amount),
                ("headline cash_balances, in any order", [("EUR", Decimal("1000")), ("SBD", Decimal("900"))], sorted(_balances(summary.cash_balances))),
                ("SBD/EUR missing dates", [date(2039, 1, 1)], _missing_dates(summary, "SBD/EUR")),
            ],
        )
        problems += _headline_problems(summary, when)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_currency_without_any_rate_is_listed_natively_and_missing_on_its_date(self, session, keep_alive, test_user, broker_a):
        """A currency with no rate at all is listed in its own currency on the card and in the
        headline, and is missing on its own date only.

        Broker A (owned 100%): 1000 EUR deposited on 2039-02-01, 500 VUV on 02-02; VUV has no
        rate on any date. Summary with breakdown at 2039-02-05: card A cash_total 1000 and
        cash_balances [EUR 1000, VUV 500]; headline cash_total 1000 and cash_balances
        [EUR 1000, VUV 500], the card lists summed by currency; data_quality reports VUV/EUR
        missing on 2039-02-02 only.

        Before F-3 the headline cash_balances held EUR 1000 only (a currency entered the list
        only if it converted at the valuation date), and VUV/EUR was missing on 2039-02-02 and
        2039-02-05 (the card conversion added the valuation date). The card values were already
        these."""
        await _persist(
            session,
            keep_alive,
            _cash_row(broker_a, TransactionType.DEPOSIT, date(2039, 2, 1), "1000", "EUR"),
            _cash_row(broker_a, TransactionType.DEPOSIT, date(2039, 2, 2), "500", "VUV"),
        )

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2039, 2, 5))

        card = _card(summary, broker_a)
        problems = _value_problems(
            "2039-02-05",
            [
                ("card A cash_total", Decimal("1000"), card.cash_total.amount),
                ("card A cash_balances", [("EUR", Decimal("1000")), ("VUV", Decimal("500"))], _balances(card.cash_balances)),
                ("headline cash_total", Decimal("1000"), summary.cash_total.amount),
                ("headline cash_balances", [("EUR", Decimal("1000")), ("VUV", Decimal("500"))], _balances(summary.cash_balances)),
                ("VUV/EUR missing dates", [date(2039, 2, 2)], _missing_dates(summary, "VUV/EUR")),
            ],
        )
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_summary_with_breakdown_zero_only_and_empty_brokers_show_zero_cash(self, session, keep_alive, test_user, broker_a):
        """A broker whose only row is a zero fee shows EUR 0 of cash; a broker with no row shows
        no cash at all.

        Broker A (owned 100%): its only row is a FEE of 0.000 EUR on 2039-05-02. Broker B (owned
        100%): no rows. Summary with breakdown at 2039-05-05: card A cash_total 0 and
        cash_balances [EUR 0]; card B cash_total 0 and cash_balances [].

        Pinned: the same before F-3. A currency whose movements add up to zero stays listed on
        the card; a broker without movements lists nothing."""
        broker_b = await _owned_broker(session, keep_alive, test_user, "B", Decimal("1.0"))
        await _persist(session, keep_alive, _cash_row(broker_a, TransactionType.FEE, date(2039, 5, 2), "0.000", "EUR"))

        summary = await PortfolioService(session).get_summary(user_id=test_user.id, include_breakdown=True, target_currency_override="EUR", date_to=date(2039, 5, 5))

        card_a, card_b = _card(summary, broker_a), _card(summary, broker_b)
        problems = _value_problems(
            "2039-05-05",
            [
                ("card A cash_total", Decimal("0"), card_a.cash_total.amount),
                ("card A cash_balances", [("EUR", Decimal("0"))], _balances(card_a.cash_balances)),
                ("card B cash_total", Decimal("0"), card_b.cash_total.amount),
                ("card B cash_balances", [], _balances(card_b.cash_balances)),
            ],
        )
        assert not problems, "\n".join(problems)


# =============================================================================
# TestNoDateToStopsAtToday (B12)
# =============================================================================


class TestNoDateToStopsAtToday:
    """B12: called directly without date_to, the getters stop at today, as the engine does.

    Broker A (owned 100%), all EUR, no asset, dated around today t: DEPOSIT 1000 at t-5 and 400
    at t+5; DIVIDEND 30 at t-5 and 20 at t+5; FEE -4 at t-5 and -6 at t+5. The rows dated t+5
    must reach no series and no contribution row."""

    @pytest.mark.asyncio
    async def test_deposit_history_without_date_to_stops_at_today(self, session, keep_alive, test_user, broker_a):
        """get_deposit_history with neither date_from nor date_to: one point, t-5 with 1000.

        Before F-3 the scan read every row of the broker: a second point followed, t+5 with
        400."""
        today = date.today()
        await _seed_around_today(session, keep_alive, broker_a, today)

        history = await PortfolioService(session).get_deposit_history(user_id=test_user.id, target_currency_override="EUR")

        assert [(point.date, point.deposit.amount) for point in history.points] == [(today - timedelta(days=5), Decimal("1000"))]

    @pytest.mark.asyncio
    async def test_income_history_without_date_to_stops_at_today(self, session, keep_alive, test_user, broker_a):
        """get_income_history with neither date_from nor date_to: one point, t-5 with dividend
        30 and interest 0.

        Before F-3 the scan read every row of the broker: a second point followed, t+5 with
        dividend 20."""
        today = date.today()
        await _seed_around_today(session, keep_alive, broker_a, today)

        history = await PortfolioService(session).get_income_history(user_id=test_user.id, target_currency_override="EUR")

        assert [(point.date, point.dividend.amount, point.interest.amount) for point in history.points] == [(today - timedelta(days=5), Decimal("30"), Decimal("0"))]

    @pytest.mark.asyncio
    async def test_cost_history_without_date_to_stops_at_today(self, session, keep_alive, test_user, broker_a):
        """get_cost_history with neither date_from nor date_to: one point, t-5 with cost -4
        (signed, as stored).

        Before F-3 the scan read every row of the broker: a second point followed, t+5 with
        -6."""
        today = date.today()
        await _seed_around_today(session, keep_alive, broker_a, today)

        history = await PortfolioService(session).get_cost_history(user_id=test_user.id, target_currency_override="EUR")

        assert [(point.date, point.cost.amount) for point in history.points] == [(today - timedelta(days=5), Decimal("-4"))]

    @pytest.mark.asyncio
    async def test_positions_contribution_without_date_to_stops_at_today(self, session, keep_alive, test_user, broker_a):
        """get_positions_contribution from t-10 without date_to: broker A's unallocated income
        30 and unallocated fees and taxes 4 (a positive figure), and its other_effects rows
        "Unallocated income" 30 (Income) and "Unallocated costs" -4 (Cost).

        Before F-3 the contribution loop read every row of the broker: 50 and 10, rows 50 and
        -10, beside the engine's period P&L of 26 (1026 - 1000), and a broker-less
        "Other / reconciliation residual" of -14 (26 - 50 + 10) made up the difference. The
        residual is not asserted here."""
        today = date.today()
        await _seed_around_today(session, keep_alive, broker_a, today)

        contribution = await PortfolioService(session).get_positions_contribution(user_id=test_user.id, date_from=today - timedelta(days=10), target_currency_override="EUR")

        unallocated = [(row.unallocated_income, row.unallocated_fees_taxes) for row in contribution.unallocated if row.broker_id == broker_a.id]
        effects = sorted((row.category, row.description, row.period_pnl) for row in contribution.other_effects if row.broker_id == broker_a.id)
        problems = _value_problems(
            f"{today} (no date_to)",
            [
                ("A unallocated (income, fees_taxes)", [(Decimal("30"), Decimal("4"))], unallocated),
                ("A other_effects (category, description, period_pnl)", [("Cost", "Unallocated costs", Decimal("-4")), ("Income", "Unallocated income", Decimal("30"))], effects),
            ],
        )
        assert not problems, "\n".join(problems)


# =============================================================================
# TestPeriodIncomeParity (B14)
# =============================================================================


class TestPeriodIncomeParity:
    """B14: the summary's period income and the contribution view's unallocated income are one figure."""

    @pytest.mark.asyncio
    async def test_period_income_equals_unallocated_contribution_income(self, session, keep_alive, test_user, broker_a):
        """Broker A (owned 100%): DEPOSIT 1000 EUR on 2039-03-01; INTEREST 100 EUR on 03-02 and
        50 TOP on 03-03, both without asset; TOP has no rate. Window (2039-03-01, 2039-03-05]:
        summary period_income 100; broker A's unallocated income in the contribution view 100,
        equal to it; the summary reports TOP/EUR missing on 2039-03-03, the interest's own date.

        Pinned: the same before F-3. The TOP date is checked by containment: before F-3 the
        summary listed [2039-03-03, 2039-03-05], its card conversion adding the valuation date;
        policy (a) leaves [2039-03-03], which the VUV test pins exactly."""
        await _persist(
            session,
            keep_alive,
            _cash_row(broker_a, TransactionType.DEPOSIT, date(2039, 3, 1), "1000", "EUR"),
            _cash_row(broker_a, TransactionType.INTEREST, date(2039, 3, 2), "100", "EUR"),
            _cash_row(broker_a, TransactionType.INTEREST, date(2039, 3, 3), "50", "TOP"),
        )
        start, end = date(2039, 3, 1), date(2039, 3, 5)
        service = PortfolioService(session)

        summary = await service.get_summary(user_id=test_user.id, target_currency_override="EUR", date_from=start, date_to=end)
        contribution = await service.get_positions_contribution(user_id=test_user.id, date_from=start, date_to=end, target_currency_override="EUR")

        when = f"({start}, {end}]"
        period_income = summary.period_income.amount if summary.period_income is not None else None
        unallocated_income = next((row.unallocated_income for row in contribution.unallocated if row.broker_id == broker_a.id), None)
        problems = _value_problems(
            when,
            [
                ("summary period_income", Decimal("100"), period_income),
                ("A unallocated_income", Decimal("100"), unallocated_income),
                ("A unallocated_income, against the summary period_income", period_income, unallocated_income),
            ],
        )
        top_dates = _missing_dates(summary, "TOP/EUR")
        if date(2039, 3, 3) not in (top_dates or []):
            problems.append(f"{when}: TOP/EUR should be missing on 2039-03-03, the summary reports {top_dates}")
        assert not problems, "\n".join(problems)


# =============================================================================
# TestReportHistoriesEqualDirectCalls
# =============================================================================

# (broker, type, day of April 2039, amount, currency): EUR/WST is 3 from 04-01 and 2.5 from
# 04-10; TOP has no rate.
_REPORT_ROWS = (
    ("A", TransactionType.DEPOSIT, 1, "1000", "EUR"),
    ("A", TransactionType.DIVIDEND, 5, "12.34", "EUR"),
    ("A", TransactionType.INTEREST, 6, "30", "WST"),
    ("A", TransactionType.FEE, 7, "-1.5", "EUR"),
    ("A", TransactionType.TAX, 8, "0.000", "EUR"),
    ("A", TransactionType.INTEREST, 9, "9", "TOP"),
    ("B", TransactionType.DEPOSIT, 2, "300", "WST"),
    ("B", TransactionType.DIVIDEND, 11, "7", "EUR"),
    ("B", TransactionType.FEE, 12, "-2", "WST"),
    ("C", TransactionType.DEPOSIT, 3, "200", "EUR"),
    ("C", TransactionType.INTEREST, 4, "5", "EUR"),
    ("C", TransactionType.TAX, 13, "-1", "EUR"),
)


class TestReportHistoriesEqualDirectCalls:
    """get_report's income, cost and deposit histories and the direct getters are one computation."""

    @pytest.mark.asyncio
    async def test_report_income_cost_deposit_histories_equal_direct_getters(self, session, keep_alive, test_user, broker_a):
        """get_report returns the same income, cost and deposit histories as the direct getters,
        every Decimal with the same exponent.

        User U: broker A owned 100%, broker B owned 50%, broker C owned by user O and only viewed
        by U (a viewer counts at 1). EUR/WST is 3 from 2039-04-01 and 2.5 from 04-10; TOP has no
        rate. A: DEPOSIT 1000 EUR 04-01; DIVIDEND 12.34 EUR 04-05; INTEREST 30 WST 04-06; FEE
        -1.5 EUR 04-07; TAX 0.000 EUR 04-08; INTEREST 9 TOP 04-09. B: DEPOSIT 300 WST 04-02;
        DIVIDEND 7 EUR 04-11; FEE -2 WST 04-12. C: DEPOSIT 200 EUR 04-03; INTEREST 5 EUR 04-04;
        TAX -1 EUR 04-13.

        Range 2039-04-02..2039-04-15, applied as (04-02, 04-15] like every period-gated flow.
        Income: 04-04 interest 5, 04-05 dividend 12.34, 04-06 interest 10, 04-11 dividend 3.5,
        TOP/EUR missing. Costs: 04-07 -1.5, 04-12 -0.4, 04-13 -1; the zero tax is left out.
        Deposits: 04-03 200 only, B's deposit falling on the excluded start. The dumps write
        every Decimal with str(), so an exponent that differs between the two paths fails the
        comparison.

        Pinned: the same before F-3."""
        broker_b = await _owned_broker(session, keep_alive, test_user, "B", Decimal("0.5"))
        broker_c = await _viewed_broker(session, keep_alive, test_user, "C")
        brokers = {"A": broker_a, "B": broker_b, "C": broker_c}
        await _persist(session, keep_alive, _eur_rate("WST", date(2039, 4, 1), "3"), _eur_rate("WST", date(2039, 4, 10), "2.5"))
        await _persist(session, keep_alive, *(_cash_row(brokers[label], tx_type, date(2039, 4, day), amount, currency) for label, tx_type, day, amount, currency in _REPORT_ROWS))
        start, end = date(2039, 4, 2), date(2039, 4, 15)
        service = PortfolioService(session)

        query = PortfolioReportQuery(date_range=OpenDateRangeModel(start=start, end=end), target_currency="EUR", include_income_history=True, include_cost_history=True, include_deposit_history=True)
        report = await service.get_report(user_id=test_user.id, query=query)
        # Each direct getter computes from scratch, never from what the report left in a cache.
        _clear_portfolio_caches()
        income = await service.get_income_history(user_id=test_user.id, date_from=start, date_to=end, target_currency_override="EUR")
        _clear_portfolio_caches()
        costs = await service.get_cost_history(user_id=test_user.id, date_from=start, date_to=end, target_currency_override="EUR")
        _clear_portfolio_caches()
        deposits = await service.get_deposit_history(user_id=test_user.id, date_from=start, date_to=end, target_currency_override="EUR")

        problems = _section_problems("income_history", report.income_history, income, 2)
        problems += _section_problems("cost_history", report.cost_history, costs, 2)
        # One point, not two: the start is exclusive, so B's 300 WST deposit on 04-02 is out, and
        # A's 1000 EUR on 04-01 is before the range. Only C's 200 EUR on 04-03 is in.
        problems += _section_problems("deposit_history", report.deposit_history, deposits, 1)
        problems += [f"income_history: {source} does not report TOP/EUR missing: {series.missing_fx_pairs}" for source, series in (("get_report", report.income_history), ("the direct getter", income)) if series is not None and "TOP/EUR" not in series.missing_fx_pairs]
        assert not problems, "\n".join(problems)


# =============================================================================
# TestFxOnCashContributionRows (step F-W)
# =============================================================================

# A row of the contribution view's other_effects as compared here:
# (description, category, period_pnl, broker_id, broker_name). Tuples compare their Decimals by
# value, so -262.5 and -262.50 are the same row.
_EffectRow = tuple[str, str, Decimal, int | None, str | None]

# The rows that make up the period other result between them: what the FX rows take, the
# residual no longer holds.
_OTHER_RESULT_ROWS = ("FX on cash", "Other / reconciliation residual")

# S1's rates, as (day, EUR/FJD): 1 FJD = 0.8 EUR from D1 (D2 falls back on it), 0.625 from D3.
_S1_RATES = ((1, "1.25"), (3, "1.6"))


def _days(month: int) -> tuple[date, date, date]:
    """D1, D2 and D3 of ``month`` 2040: each F-W scenario has a month of its own."""
    return date(2040, month, 1), date(2040, month, 2), date(2040, month, 3)


def _effect_rows(contribution: PositionsContribution) -> list[_EffectRow]:
    return [(row.description, row.category, row.period_pnl, row.broker_id, row.broker_name) for row in contribution.other_effects]


def _income_row(broker: Broker, pnl: str) -> _EffectRow:
    return ("Unallocated income", "Income", Decimal(pnl), broker.id, broker.name)


def _cost_row(broker: Broker, pnl: str) -> _EffectRow:
    return ("Unallocated costs", "Cost", Decimal(pnl), broker.id, broker.name)


def _fx_row(broker: Broker, pnl: str) -> _EffectRow:
    return ("FX on cash", "Other", Decimal(pnl), broker.id, broker.name)


def _residual_row(pnl: str) -> _EffectRow:
    return ("Other / reconciliation residual", "Other", Decimal(pnl), None, None)


async def _rates(session: AsyncSession, keep_alive: list[object], quote: str, month: int, *rates: tuple[int, str]) -> None:
    """EUR/``quote`` on the given (day, rate) of ``month`` 2040: EUR/FJD 1.25 is 1 FJD = 0.8 EUR."""
    await _persist(session, keep_alive, *(_eur_rate(quote, date(2040, month, day), rate) for day, rate in rates))


async def _fjd_deposits(session: AsyncSession, keep_alive: list[object], broker: Broker, month: int, on_d1: str, on_d2: str) -> None:
    """DEPOSIT ``on_d1`` FJD on D1 and ``on_d2`` FJD on D2 at ``broker``: S1's rows when 1000 and 500."""
    d1, d2, _ = _days(month)
    await _persist(session, keep_alive, _cash_row(broker, TransactionType.DEPOSIT, d1, on_d1, "FJD"), _cash_row(broker, TransactionType.DEPOSIT, d2, on_d2, "FJD"))


async def _linked_pair(session: AsyncSession, keep_alive: list[object], sent: Transaction, received: Transaction) -> None:
    """Persist the two legs of a CASH_TRANSFER or FX_CONVERSION, each linked to the other."""
    await _persist(session, keep_alive, sent, received)
    sent.related_transaction_id = received.id
    received.related_transaction_id = sent.id
    await session.flush()


async def _access_order(service: PortfolioService, user: User, broker_ids: list[int] | None = None) -> list[int]:
    """The broker ids in the order the service reads the user's accesses, the order of the FX rows.

    That query has no ORDER BY: the order is taken from the same call the service makes, never
    assumed from the ids or from the order of creation."""
    return [access.broker_id for access in await service._get_user_broker_access(user.id, broker_ids)]


async def _summary_other(service: PortfolioService, user: User, date_from: date | None, date_to: date, broker_ids: list[int] | None) -> Decimal | None:
    """The summary's period_other_result on the same scope and window, computed from scratch."""
    _clear_portfolio_caches()
    summary = await service.get_summary(user_id=user.id, broker_ids=broker_ids, target_currency_override="EUR", date_from=date_from, date_to=date_to)
    return summary.period_other_result.amount if summary.period_other_result is not None else None


def _reconciliation_problems(when: str, rows: list[_EffectRow], period_other: Decimal | None, tolerance: Decimal) -> list[str]:
    """The FX on cash rows plus the residual (0 when absent) against the summary's period_other_result.

    On a cash-only scope the period other result holds nothing else, so the FX rows and the
    residual must add up to it: to the digit, or within ``tolerance``."""
    if period_other is None:
        return [f"{when}: the summary computed no period_other_result"]
    shown = sum((pnl for description, _, pnl, _, _ in rows if description in _OTHER_RESULT_ROWS), Decimal("0"))
    if abs(shown - period_other) > tolerance:
        return [f"{when}: the FX on cash rows and the residual add up to {shown}, the summary's period_other_result is {period_other}"]
    return []


async def _other_effects_problems(service: PortfolioService, user: User, want: list[_EffectRow], date_from: date | None, date_to: date, broker_ids: list[int] | None = None) -> list[str]:
    """other_effects against ``want`` exactly (rows, values and order), then their sum against the summary."""
    when = f"({date_from}, {date_to}]"
    contribution = await service.get_positions_contribution(user_id=user.id, broker_ids=broker_ids, date_from=date_from, date_to=date_to, target_currency_override="EUR")
    got = _effect_rows(contribution)
    problems = [] if got == want else [f"{when}: other_effects expected {want}, got {got}"]
    return problems + _reconciliation_problems(when, got, await _summary_other(service, user, date_from, date_to, broker_ids), Decimal("0"))


def _single_fx_row_problems(when: str, rows: list[_EffectRow], broker: Broker, expected: Decimal, dust: Decimal) -> list[str]:
    """``rows`` is one FX on cash row (Other, ``broker``) within ``dust`` of ``expected``, and nothing else."""
    if [description for description, *_ in rows] != ["FX on cash"]:
        return [f"{when}: other_effects should be one FX on cash row and nothing else, got {rows}"]
    [(_, category, pnl, broker_id, broker_name)] = rows
    problems = [] if (category, broker_id, broker_name) == ("Other", broker.id, broker.name) else [f"{when}: the FX on cash row should be (Other, {broker.id}, {broker.name}), got {rows}"]
    if abs(pnl - expected) >= dust:
        problems.append(f"{when}: FX on cash {pnl} should be within {dust} of {expected}")
    return problems


class TestFxOnCashContributionRows:
    """Step F-W: the contribution view shows each broker's exchange result on its foreign cash.

    Every scenario holds cash only, in FJD (KMF in S7) against EUR, so its period other result
    is exchange on cash, plus what a documented limit leaves in the residual: a conversion
    spread (S5), cash in transit (S6). D1, D2 and D3 are the first three days of the
    scenario's month of 2040; date_to is D3 unless stated. Brokers are owned by the user at
    share 1 unless stated."""

    @pytest.mark.asyncio
    async def test_foreign_deposits_show_their_exchange_result_and_no_residual(self, session, keep_alive, test_user):
        """S1 (January). EUR/FJD 1.25 on D1 (1 FJD = 0.8 EUR) and 1.6 on D3 (0.625); D2 falls
        back on D1's rate. Broker F1: DEPOSIT 1000 FJD on D1 (capital 800) and 500 FJD on D2
        (capital 400). On D3 the 1500 FJD are worth 937.5: over (None, D3] the period other
        result is 937.5 - 1200 = -262.5, all of it exchange.

        Expected: other_effects == [FX on cash -262.5 (Other, F1)], no residual; the row is the
        summary's period_other_result. Before F-W: [Other / reconciliation residual -262.5]."""
        _, _, d3 = _days(1)
        broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 1, *_S1_RATES)
        await _fjd_deposits(session, keep_alive, broker, 1, "1000", "500")

        problems = await _other_effects_problems(PortfolioService(session), test_user, [_fx_row(broker, "-262.5")], None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_unallocated_income_comes_before_the_exchange_result(self, session, keep_alive, test_user):
        """S1 plus an INTEREST of 100 FJD on D2 at F1, without asset (February). The interest is
        income, converted at D2's rate: 80. On D3 the 1600 FJD are worth 1000, against 1200 of
        capital and 80 of income: the period other result is 1000 - 1200 - 80 = -280, all of it
        exchange (1000 - 800 - 400 - 80).

        Expected: [Unallocated income 80 (Income, F1), FX on cash -280 (Other, F1)], the income
        first, no residual; -280 is the summary's period_other_result. Before F-W:
        [Unallocated income 80, Other / reconciliation residual -280]."""
        _, d2, d3 = _days(2)
        broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 2, *_S1_RATES)
        await _fjd_deposits(session, keep_alive, broker, 2, "1000", "500")
        await _persist(session, keep_alive, _cash_row(broker, TransactionType.INTEREST, d2, "100", "FJD"))

        problems = await _other_effects_problems(PortfolioService(session), test_user, [_income_row(broker, "80"), _fx_row(broker, "-280")], None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.parametrize(("from_day", "to_day", "fx"), [(None, 3, "-362.5"), (2, 3, "-187.5"), (1, 2, "-175")], ids=["none-to-d3", "d2-to-d3", "d1-to-d2"])
    @pytest.mark.asyncio
    async def test_the_exchange_result_covers_the_window(self, session, keep_alive, test_user, from_day, to_day, fx):
        """S2 (March). EUR/FJD 1.25 on D1, 1.6 on D2 and 2 on D3 (1 FJD = 0.8, 0.625, 0.5 EUR).
        Broker F1: DEPOSIT 1000 FJD on D1 (800) and 500 FJD on D2 (312.5); the 1500 FJD are
        worth 937.5 on D2 and 750 on D3. Each window shows one FX row and no residual:
        (None, D3] 750 - 800 - 312.5 = -362.5; (D2, D3] 750 - 937.5 = -187.5;
        (D1, D2] 937.5 - 800 - 312.5 = -175. Each is the summary's period_other_result over
        the same window.

        Before F-W: the residual alone, with the same value."""
        date_from = date(2040, 3, from_day) if from_day else None
        broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 3, (1, "1.25"), (2, "1.6"), (3, "2"))
        await _fjd_deposits(session, keep_alive, broker, 3, "1000", "500")

        problems = await _other_effects_problems(PortfolioService(session), test_user, [_fx_row(broker, fx)], date_from, date(2040, 3, to_day))
        assert not problems, "\n".join(problems)

    @pytest.mark.parametrize(("access", "fx"), [("owner", "-131.25"), ("viewer", "-262.5")], ids=["owner-at-share-0.5", "viewer"])
    @pytest.mark.asyncio
    async def test_the_exchange_result_follows_the_users_share(self, session, keep_alive, test_user, access, fx):
        """S3 (April): S1's rates and rows at a broker F1 that the user owns at share 0.5, or
        only views. An owner's share scales every amount: 750 FJD worth 468.75 on D3 against
        600 of capital, -131.25. A viewer sees the broker's full data, at 1: -262.5, as in S1.

        Expected: one FX on cash row with that value, no residual; it is the summary's
        period_other_result. Before F-W: the residual alone, with the same value."""
        _, _, d3 = _days(4)
        if access == "viewer":
            broker = await _viewed_broker(session, keep_alive, test_user, "F1")
        else:
            broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("0.5"))
        await _rates(session, keep_alive, "FJD", 4, *_S1_RATES)
        await _fjd_deposits(session, keep_alive, broker, 4, "1000", "500")

        problems = await _other_effects_problems(PortfolioService(session), test_user, [_fx_row(broker, fx)], None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_each_foreign_cash_broker_gets_its_row_in_access_order(self, session, keep_alive, test_user):
        """S4 (May), three brokers and S1's rates. E holds EUR only: DEPOSIT 1000 EUR on D1. F1
        has S1's rows: -262.5. F2 has half of them, 500 FJD on D1 and 250 on D2: 750 FJD worth
        468.75 against 600, -131.25.

        Expected: [FX on cash -262.5 (F1), FX on cash -131.25 (F2)] in the order the service
        reads the user's accesses (taken from that same call: it has no ORDER BY), no row for
        E, no residual; together -393.75, the summary's period_other_result. Before F-W:
        [Other / reconciliation residual -393.75]."""
        d1, _, d3 = _days(5)
        broker_e = await _owned_broker(session, keep_alive, test_user, "E", Decimal("1.0"))
        broker_f1 = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        broker_f2 = await _owned_broker(session, keep_alive, test_user, "F2", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 5, *_S1_RATES)
        await _persist(session, keep_alive, _cash_row(broker_e, TransactionType.DEPOSIT, d1, "1000", "EUR"))
        await _fjd_deposits(session, keep_alive, broker_f1, 5, "1000", "500")
        await _fjd_deposits(session, keep_alive, broker_f2, 5, "500", "250")
        service = PortfolioService(session)

        fx_rows = {broker_f1.id: _fx_row(broker_f1, "-262.5"), broker_f2.id: _fx_row(broker_f2, "-131.25")}
        want = [fx_rows[broker_id] for broker_id in await _access_order(service, test_user) if broker_id in fx_rows]
        problems = await _other_effects_problems(service, test_user, want, None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_a_report_currency_only_scope_shows_no_exchange_row(self, session, keep_alive, test_user):
        """S4 restricted to E (June): the same three brokers, rows and rates, with
        broker_ids=[E]. E holds EUR only, so there is no FX row, and its period other result is
        1000 - 1000 = 0, so no residual either: other_effects == [], and the summary of the same
        scope says 0. F1 and F2 hold foreign cash but are out of the scope.

        Pinned: the same before F-W."""
        d1, _, d3 = _days(6)
        broker_e = await _owned_broker(session, keep_alive, test_user, "E", Decimal("1.0"))
        broker_f1 = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        broker_f2 = await _owned_broker(session, keep_alive, test_user, "F2", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 6, *_S1_RATES)
        await _persist(session, keep_alive, _cash_row(broker_e, TransactionType.DEPOSIT, d1, "1000", "EUR"))
        await _fjd_deposits(session, keep_alive, broker_f1, 6, "1000", "500")
        await _fjd_deposits(session, keep_alive, broker_f2, 6, "500", "250")

        problems = await _other_effects_problems(PortfolioService(session), test_user, [], None, d3, [broker_e.id])
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_a_conversion_spread_stays_in_the_residual(self, session, keep_alive, test_user):
        """S5 (July), S1's rates. Broker F1: DEPOSIT 1000 FJD on D1 (800); on D2, INTEREST 100
        FJD (80) and FEE -10 FJD (-8), both without asset, and an FX_CONVERSION of 500 FJD into
        390 EUR, both legs at F1 and linked to each other. At D2's rate 500 FJD are 400 EUR: the
        conversion loses 10 to its spread.

        On D3 F1 holds 590 FJD (368.75) and 390 EUR: NAV 758.75 against 800 of capital, P&L
        -41.25, period other result -41.25 - 80 + 8 = -113.25. The exchange result of the FJD
        cash is 368.75 - (800 + 80 - 8 - 400) = -103.25. The spread, -10, is not exchange on
        cash held: it stays in the residual (a documented limit).

        Expected, exactly and in this order: [Unallocated income 80, Unallocated costs -8, FX on
        cash -103.25 (F1), Other / reconciliation residual -10]; -103.25 - 10 is the summary's
        period_other_result. Before F-W: [Unallocated income 80, Unallocated costs -8, Other /
        reconciliation residual -113.25]."""
        d1, d2, d3 = _days(7)
        broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 7, *_S1_RATES)
        await _persist(
            session,
            keep_alive,
            _cash_row(broker, TransactionType.DEPOSIT, d1, "1000", "FJD"),
            _cash_row(broker, TransactionType.INTEREST, d2, "100", "FJD"),
            _cash_row(broker, TransactionType.FEE, d2, "-10", "FJD"),
        )
        await _linked_pair(session, keep_alive, _cash_row(broker, TransactionType.FX_CONVERSION, d2, "-500", "FJD"), _cash_row(broker, TransactionType.FX_CONVERSION, d2, "390", "EUR"))

        want = [_income_row(broker, "80"), _cost_row(broker, "-8"), _fx_row(broker, "-103.25"), _residual_row("-10")]
        problems = await _other_effects_problems(PortfolioService(session), test_user, want, None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_exchange_on_cash_in_transit_stays_in_the_residual(self, session, keep_alive, test_user):
        """S6 (August). EUR/FJD 1.25 on D1 (0.8) and 1.6 on D2 (0.625); D3 falls back on D2's
        rate. Brokers F1 and F2. DEPOSIT 1000 FJD at F1 on D1 (800); the same day a
        CASH_TRANSFER sends the 1000 FJD out of F1, and they reach F2 on D3, the two legs linked
        to each other.

        Neither broker holds the money while it travels. F1's FJD leave at the rate they came in
        with: 800 - 800 = 0. F2's arrive at D3's rate and are still worth it: 625 - 625 = 0. So
        neither broker gets an FX row, while the 1000 FJD lost 175 on the way (800 to 625): that
        stays in the residual, a documented limit. Expected: [Other / reconciliation residual
        -175], the summary's period_other_result.

        Pinned: the same before F-W."""
        d1, _, d3 = _days(8)
        broker_f1 = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        broker_f2 = await _owned_broker(session, keep_alive, test_user, "F2", Decimal("1.0"))
        await _rates(session, keep_alive, "FJD", 8, (1, "1.25"), (2, "1.6"))
        await _persist(session, keep_alive, _cash_row(broker_f1, TransactionType.DEPOSIT, d1, "1000", "FJD"))
        await _linked_pair(session, keep_alive, _cash_row(broker_f1, TransactionType.CASH_TRANSFER, d1, "-1000", "FJD"), _cash_row(broker_f2, TransactionType.CASH_TRANSFER, d3, "1000", "FJD"))

        problems = await _other_effects_problems(PortfolioService(session), test_user, [_residual_row("-175")], None, d3)
        assert not problems, "\n".join(problems)

    @pytest.mark.asyncio
    async def test_conversion_dust_leaves_no_residual(self, session, keep_alive, test_user):
        """S7 (September, KMF). EUR/KMF 1.1 on D1 and 1.2 on D3. Broker F1: DEPOSIT 5000 KMF on
        D1. The engine values cash as amount x (1 / rate), the native cash converts a movement
        as amount / rate: at 28 digits the two differ in the last digit (the precondition), so
        the period other result and the exchange result part by about 1E-24.

        Expected: one row and nothing else, FX on cash (Other, F1), within CONVERSION_DUST of
        5000 / 1.2 - 5000 / 1.1 (about -378.79); no residual row, since what is left is below
        CONVERSION_DUST; the row is within CONVERSION_DUST of the summary's
        period_other_result. Before F-W: [Other / reconciliation residual, about -378.79]; until
        F-W the test stops reading CONVERSION_DUST, which does not exist (AttributeError)."""
        assert Decimal(5000) * (Decimal(1) / Decimal("1.1")) != Decimal(5000) / Decimal("1.1"), "precondition: at 28 digits, 5000 x (1 / 1.1) and 5000 / 1.1 should differ in the last digit"
        dust = native_cash_module.CONVERSION_DUST
        d1, _, d3 = _days(9)
        broker = await _owned_broker(session, keep_alive, test_user, "F1", Decimal("1.0"))
        await _rates(session, keep_alive, "KMF", 9, (1, "1.1"), (3, "1.2"))
        await _persist(session, keep_alive, _cash_row(broker, TransactionType.DEPOSIT, d1, "5000", "KMF"))
        service = PortfolioService(session)

        when = f"(None, {d3}]"
        rows = _effect_rows(await service.get_positions_contribution(user_id=test_user.id, date_to=d3, target_currency_override="EUR"))
        problems = _single_fx_row_problems(when, rows, broker, Decimal(5000) / Decimal("1.2") - Decimal(5000) / Decimal("1.1"), dust)
        problems += _reconciliation_problems(when, rows, await _summary_other(service, test_user, None, d3, None), dust)
        assert not problems, "\n".join(problems)
