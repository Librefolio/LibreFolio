"""78 L10 — `portfolio.drawdown_summary` measures the export's own brokers, not every broker the user can see.

WHAT. ``portfolio.drawdown_summary`` (``drawdown_context._build_portfolio_drawdown``) asks Risk for ``drawdown_summary``
on ``export_risk_scope(scope)``: ``broker_ids`` = the export's ``broker_scope``, the owner's share of each counted. This
file pins two facts, each by comparing the component's payload with direct ``RiskService.execute`` calls that mirror
the component's own request (the loader of ``_execute_drawdown``: HISTORICAL mode, EUR, from the scope's first
transaction to the period end, the same analytic):

- Fact 1: a user who only OWNS brokers, one at a partial share, and the Dashboard's list (its owned brokers): the
  drawdown is the one the old call gave, ``PortfolioRiskScope(broker_ids=None)``. Status, current and maximum drawdown,
  their dates, recovery status and observations are equal.
- Fact 2: the same user with a broker only SHARED with them (VIEWER) and the same Dashboard list: the shared broker is
  out. The component equals a direct call on ``broker_ids=[owned ids]`` and differs from the old None call, which is
  far deeper because the shared broker's asset falls hard.

WHY. Before 78 L10 the component passed ``broker_ids=None``, which Risk reads as every broker the user can access, of
any role: a viewer or editor broker was counted whole (``native_cash.effective_share``) in a drawdown the export
presented as the portfolio's. The positions and the cash of the same export read only ``broker_scope``, so the
drawdown described another portfolio. Fact 2 is the case that is red on the old code (it gave the None figure); fact 1
is green on both and pins that nothing moves for a user without shared brokers. The None call inside fact 2 is the
proof of the difference, since the old code cannot be run.

THE BOOK, on a private SQLite file under ``tmp_path``. Everything in EUR, no exchange rate involved. User U OWNS B1
(share 1) and B2 (share 0.5); user O OWNS B3 (share 1) and, in fact 2 only, grants U a VIEWER access on B3.

- B1: DEPOSIT 10 000, BUY 50 ``ETF_A`` at 100 → cash 5 000.
- B2: DEPOSIT 10 000, BUY 100 ``STOCK_B`` at 100 → no cash; U counts half of it.
- B3: DEPOSIT 20 000, BUY 200 ``CRASH`` at 100 → no cash; a viewer counts it whole.
- Every broker's first transaction is on the same day, so the date range a call resolves is the same whatever the
  broker set: only the brokers can differ.
- Weekday closes from January 2023, a step path: 100 until the end of February 2024, a plateau in March–April
  (``ETF_A`` 110, ``STOCK_B`` 120, ``CRASH`` 110), then a fall from May to the period end (``ETF_A`` 104.5, −5 %;
  ``STOCK_B`` 108, −10 %; ``CRASH`` 44, −60 %). No flow after the buys, so the TWRR index follows U's value.

U's value on B1 + half of B2: 15 000 → 16 500 on the plateau → 15 625 after the fall, a drawdown of −5.30 % (B2 whole
would give −6.56 %: the share is not decorative). With B3 whole on top: 38 500 → 24 425, −36.56 %.

The period is 1 April – 28 June 2024; the drawdown reads the full history from the first transaction (E1).

Isolation: PURE with respect to the lane. The real ``RiskService`` and ``PortfolioService`` run in process on the
private file (the app schema by ``create_all``, NullPool, the engine disposed at teardown). The portfolio L2, WAC and
engine blob caches are process-global, and every private book's user has the same id: they are emptied before and
after each test. The market holiday table is an empty one (built for real it takes a QuantLib process). No lane
database, no server, no network, no sleep.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_drawdown_broker_scope.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import DateRangeModel, OpenDateRangeModel
from backend.app.schemas.risk.outputs import RiskDrawdownOutput
from backend.app.schemas.risk.results import RiskAnalyticResult
from backend.app.schemas.risk.scope import PortfolioRiskScope, RiskAnalyticRequest, RiskQueryRequest
from backend.app.schemas.risk.vocabulary import RiskMode, RiskResultStatus, RiskScopeKind
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.drawdown_context import (
    _DRAWDOWN_ANALYTIC_CODE,
    _DRAWDOWN_INSTANCE_ID,
    DrawdownContextPayload,
    DrawdownContextStatus,
    _build_portfolio_drawdown,
)
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.assets import price_query
from backend.app.services.platform.date_sentinel import resolve_date_sentinels
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.service import RiskService

EUR = "EUR"
PERIOD_START = date(2024, 4, 1)
PERIOD_END = date(2024, 6, 28)  # a Friday
CLOSES_FROM = date(2023, 1, 2)
PLATEAU_FROM = date(2024, 3, 1)
FALL_FROM = date(2024, 5, 1)
DEPOSIT_DAY = date(2024, 1, 15)
BUY_DAY = date(2024, 1, 16)
UNIT_PRICE = Decimal("100")

# (plateau close, close after the fall) of each asset; 100 before the plateau.
PATHS = {
    "ETF_A": (Decimal("110"), Decimal("104.5")),
    "STOCK_B": (Decimal("120"), Decimal("108")),
    "CRASH": (Decimal("110"), Decimal("44")),
}

# U's value on B1 + half of B2: 16 500 on the plateau, 15 625 after the fall; with B3 whole: 38 500 → 24 425.
OWNED_DRAWDOWN = 15625 / 16500 - 1
WITH_SHARED_DRAWDOWN = 24425 / 38500 - 1

# The same Risk run twice may reach the engine by two paths (None vs an explicit list): a float tolerance, no more.
FLOAT_TOLERANCE = 1e-9
# The hand-computed figure is a premise, checked loosely: the TWRR series Risk reads is rounded upstream (observed
# −0.05303 for 15 625 / 16 500 − 1 = −0.0530303…).
PREMISE_TOLERANCE = 1e-5


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_ids: dict[str, int]


def _closes(label: str) -> list[tuple[date, Decimal]]:
    """(day, close) on every weekday from CLOSES_FROM to PERIOD_END: 100, then the plateau, then the fall."""
    plateau, fallen = PATHS[label]
    closes = []
    for offset in range((PERIOD_END - CLOSES_FROM).days + 1):
        day = CLOSES_FROM + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        close = fallen if day >= FALL_FROM else plateau if day >= PLATEAU_FROM else UNIT_PRICE
        closes.append((day, close))
    return closes


async def _seed(engine: AsyncEngine, *, share_b3_with_u: bool) -> _Book:
    """U owns B1 and B2 (share 0.5), O owns B3; with ``share_b3_with_u`` O grants U a VIEWER access on B3."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="l10_dd_scope_u", email="l10_dd_scope_u@test.com", hashed_password="fakehash", is_active=True)
        other = User(username="l10_dd_scope_o", email="l10_dd_scope_o@test.com", hashed_password="fakehash", is_active=True)
        brokers = {
            "B1": Broker(name="L10 drawdown scope B1"),
            "B2": Broker(name="L10 drawdown scope B2 half"),
            "B3": Broker(name="L10 drawdown scope B3 shared"),
        }
        assets = {
            "ETF_A": Asset(display_name="L10 ETF_A", currency=EUR, asset_type=AssetType.ETF),
            "STOCK_B": Asset(display_name="L10 STOCK_B", currency=EUR, asset_type=AssetType.STOCK),
            "CRASH": Asset(display_name="L10 CRASH", currency=EUR, asset_type=AssetType.STOCK),
        }
        session.add_all([user, other, *brokers.values(), *assets.values()])
        await session.flush()
        accesses = [
            BrokerUserAccess(broker_id=brokers["B1"].id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
            BrokerUserAccess(broker_id=brokers["B2"].id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("0.5")),
            BrokerUserAccess(broker_id=brokers["B3"].id, user_id=other.id, role=UserRole.OWNER, share_percentage=Decimal("1")),
        ]
        if share_b3_with_u:
            accesses.append(BrokerUserAccess(broker_id=brokers["B3"].id, user_id=user.id, role=UserRole.VIEWER))
        session.add_all(accesses)

        def deposit(broker: str, amount: int) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=None, type=TransactionType.DEPOSIT, date=DEPOSIT_DAY, quantity=Decimal("0"), amount=Decimal(amount), currency=EUR)

        def buy(broker: str, asset: str, quantity: int) -> Transaction:
            return Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(quantity), amount=-UNIT_PRICE * quantity, currency=EUR)

        session.add_all(
            [
                deposit("B1", 10000),
                buy("B1", "ETF_A", 50),
                deposit("B2", 10000),
                buy("B2", "STOCK_B", 100),
                deposit("B3", 20000),
                buy("B3", "CRASH", 200),
            ]
        )
        for label, asset in assets.items():
            session.add_all(PriceHistory(asset_id=asset.id, date=day, open=close, high=close, low=close, close=close, currency=EUR, source_plugin_key="MANUAL") for day, close in _closes(label))
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_ids={label: broker.id for label, broker in brokers.items()})


# =============================================================================
# THE COMPONENT AND THE DIRECT RISK CALLS
# =============================================================================


def _owned_ids(book: _Book) -> tuple[int, ...]:
    """The Dashboard's broker list for U: its owned brokers."""
    return (book.broker_ids["B1"], book.broker_ids["B2"])


def _scope(book: _Book) -> BuildScope:
    return BuildScope(
        request_id="l10-drawdown-broker-scope",
        user_id=book.user_id,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=EUR,
        broker_scope=_owned_ids(book),
    )


async def _component(book: _Book) -> DrawdownContextPayload:
    """`portfolio.drawdown_summary` of one build over the Dashboard's list."""
    scope = _scope(book)
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
        payload = await _build_portfolio_drawdown(context, {})
    assert payload.status in {DrawdownContextStatus.OK, DrawdownContextStatus.PARTIAL}, f"component drawdown {payload.status}: reason_code={payload.reason_code} message={payload.message}"
    return payload


async def _direct(book: _Book, broker_ids: list[int] | None) -> RiskAnalyticResult:
    """A direct Risk ``drawdown_summary`` built as the component's loader builds it, on ``broker_ids``.

    The start is the loader's: the first transaction of the export's ``broker_scope`` (unchanged by 78 L10), or the
    period start if earlier. ``apply_ownership_share`` is left at its default, True, as the old call left it.
    """
    scope = _scope(book)
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        resolved = await resolve_date_sentinels(OpenDateRangeModel(start="min", end=scope.period_end), scope.user_id, session, broker_ids=list(scope.broker_scope) or None)
        inception = resolved.start if resolved is not None and isinstance(resolved.start, date) else None
        start = min(inception, scope.period_start) if inception is not None else scope.period_start
        request = RiskQueryRequest(
            scope=PortfolioRiskScope(kind=RiskScopeKind.PORTFOLIO, broker_ids=broker_ids),
            date_range=DateRangeModel(start=start, end=scope.period_end),
            target_currency=EUR,
            mode=RiskMode.HISTORICAL,
            analytics=[RiskAnalyticRequest(instance_id=_DRAWDOWN_INSTANCE_ID, analytic_code=_DRAWDOWN_ANALYTIC_CODE)],
        )
        response = await RiskService(session).execute(user_id=scope.user_id, request=request)
    assert len(response.items) == 1, f"one analytic was asked, Risk answered {len(response.items)}"
    result = response.items[0]
    assert result.status in {RiskResultStatus.OK, RiskResultStatus.PARTIAL}, f"direct drawdown on {broker_ids} {result.status}: {result.error}"
    assert isinstance(result.output, RiskDrawdownOutput), type(result.output).__name__
    return result


def _from_payload(payload: DrawdownContextPayload) -> dict[str, Any]:
    return {
        "status": payload.status.value,
        "current_drawdown": payload.current_drawdown_ratio,
        "current_peak_date": payload.current_peak_date,
        "maximum_drawdown": payload.maximum_drawdown_ratio,
        "maximum_drawdown_peak_date": payload.maximum_drawdown_peak_date,
        "maximum_drawdown_trough_date": payload.maximum_drawdown_trough_date,
        "maximum_drawdown_recovery_status": payload.maximum_drawdown_recovery_status,
        "n_observations": payload.n_observations,
    }


def _from_result(result: RiskAnalyticResult) -> dict[str, Any]:
    output = result.output
    return {
        "status": result.status.value,
        "current_drawdown": output.current_drawdown,
        "current_peak_date": output.current_peak_date,
        "maximum_drawdown": output.maximum_drawdown,
        "maximum_drawdown_peak_date": output.maximum_drawdown_peak_date,
        "maximum_drawdown_trough_date": output.maximum_drawdown_trough_date,
        "maximum_drawdown_recovery_status": output.maximum_drawdown_recovery_status.value,
        "n_observations": output.n_observations,
    }


def _assert_same_drawdown(component: dict[str, Any], direct: dict[str, Any], label: str) -> None:
    """Equal figures: exact on status, dates and counts, a float tolerance on the two ratios."""
    for key, value in component.items():
        if isinstance(value, float):
            assert value == pytest.approx(direct[key], abs=FLOAT_TOLERANCE), f"{label}: {key} component {value} vs direct {direct[key]}"
        else:
            assert value == direct[key], f"{label}: {key} component {value!r} vs direct {direct[key]!r}"


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _no_market_holidays() -> frozenset[date]:
    return frozenset()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request: pytest.FixtureRequest) -> None:
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The market holiday table, empty, wherever the build awaits it: the price reads and the Risk run."""
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'l10_drawdown_scope.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


# =============================================================================
# THE FACTS
# =============================================================================


@pytest.mark.asyncio
async def test_fact1_owned_brokers_only_the_drawdown_is_the_old_one(private_engine):
    """Fact 1 — U owns B1 and B2 (half), nothing shared: the component equals the old None call.

    The Dashboard's list is U's owned brokers, which is also every broker U can access, so None and the list name the
    same set at the same shares. The drawdown is real (−5.30 %, half of B2 counted), so the equality is not 0 == 0.
    """
    book = await _seed(private_engine, share_b3_with_u=False)

    component = _from_payload(await _component(book))
    old = _from_result(await _direct(book, None))

    assert component["maximum_drawdown"] == pytest.approx(OWNED_DRAWDOWN, abs=PREMISE_TOLERANCE), f"premise: U's owned drawdown is {OWNED_DRAWDOWN}, the component says {component['maximum_drawdown']}"
    _assert_same_drawdown(component, old, "owned only vs old None call")


@pytest.mark.asyncio
async def test_fact2_a_broker_only_shared_with_the_user_is_out_of_the_drawdown(private_engine):
    """Fact 2 — B3 shared with U as VIEWER, the Dashboard's list B1 + B2: B3 is out.

    The component equals a direct call on ``[B1, B2]`` (−5.30 %) and differs from the old None call, which counts B3
    whole and its −60 % fall with it (−36.56 %): deeper by about 31 points, not noise.
    """
    book = await _seed(private_engine, share_b3_with_u=True)

    component = _from_payload(await _component(book))
    owned = _from_result(await _direct(book, list(_owned_ids(book))))
    old = _from_result(await _direct(book, None))

    _assert_same_drawdown(component, owned, "component vs direct call on the owned brokers")
    assert component["maximum_drawdown"] == pytest.approx(OWNED_DRAWDOWN, abs=PREMISE_TOLERANCE)
    assert old["maximum_drawdown"] == pytest.approx(WITH_SHARED_DRAWDOWN, abs=PREMISE_TOLERANCE), f"premise: the old None call counts B3 whole, {WITH_SHARED_DRAWDOWN}; it says {old['maximum_drawdown']}"
    assert old["maximum_drawdown"] < component["maximum_drawdown"] - 0.25, f"the shared broker must deepen the old figure: old {old['maximum_drawdown']} vs component {component['maximum_drawdown']}"
    assert old["current_drawdown"] < component["current_drawdown"] - 0.25
