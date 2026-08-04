"""Focused tests for the broker concentration + cost-efficiency AI Export adequacy
evidence `ComponentSpec` builders (Phase 0 AI Export adequacy remediation).

Covers `backend.app.services.ai_export.components.broker_concentration_context`
(`broker.concentration_context` + `broker.concentration_comparison`) and
`backend.app.services.ai_export.components.broker_cost_efficiency`
(`broker.cost_efficiency`):

- multi-currency native allocation with an explicit unknown/coverage bucket,
- broker-vs-whole-portfolio comparator (filtered vs unfiltered report, single
  memoized whole-portfolio load, access enforced through PortfolioService),
- typed ``unavailable`` comparator reasons,
- deterministic turnover signs/types, zero-denominator and missing-fee handling
  (never coerced to zero),
- no asset/lot/transaction row-id leakage,
- deterministic ordering.

`PortfolioService.get_report` and the broker period-transaction DB loader are
monkeypatched (no live DB), matching
`test_ai_export_components_portfolio_broker_financial.py`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    AllocationItem,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportResponse,
    PortfolioSummary,
)
from backend.app.services.ai_export.components import broker_concentration_context, broker_cost_efficiency, broker_financial
from backend.app.services.ai_export.components.broker_concentration_context import ConcentrationComparisonStatus
from backend.app.services.ai_export.components.broker_cost_efficiency import FeeStatus, TradeActivityRecord
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, RequiredComponentBuildError, build_bucket_plan_for_scope
from backend.app.services.portfolio_service import PortfolioService

CURRENCY = "EUR"


def _money(amount: object, code: str = CURRENCY) -> Currency:
    return Currency(code=code, amount=Decimal(str(amount)))


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-1",
        "user_id": 1,
        "domain": Domain.BROKER,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 31),
        "target_currency": CURRENCY,
        "broker_id": 7,
        "broker_scope": (7,),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _make_async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


async def _make_real_db_session() -> AsyncSession:
    """A real in-memory SQLite session with the ORM schema created (for DB-level loader tests)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return AsyncSession(engine)


def _tx(broker_id: int, type_: TransactionType, tx_date: date, *, amount: object | None = None, currency: str | None = CURRENCY, quantity: object = 0) -> Transaction:
    return Transaction(broker_id=broker_id, type=type_, date=tx_date, quantity=Decimal(str(quantity)), amount=(Decimal("0") if amount is None else Decimal(str(amount))), currency=currency)


async def _seed_parents(session: AsyncSession, *, user_id: int, broker_ids: tuple[int, ...]) -> None:
    """Insert the minimal User/Broker parent rows so FK-enforced transaction inserts succeed."""
    session.add(User(id=user_id, username=f"user{user_id}", email=f"user{user_id}@example.test", hashed_password="x"))
    for broker_id in broker_ids:
        session.add(Broker(id=broker_id, name=f"Broker {broker_id}"))
    await session.flush()


def _registry() -> ComponentRegistry:
    return ComponentRegistry(
        (
            *broker_financial.BROKER_FINANCIAL_COMPONENTS,
            *broker_concentration_context.BROKER_CONCENTRATION_COMPONENTS,
            *broker_cost_efficiency.BROKER_COST_EFFICIENCY_COMPONENTS,
        )
    )


def _make_context(scope: BuildScope, registry: ComponentRegistry, session: AsyncSession) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(registry, request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


def _metadata(scope: BuildScope) -> PortfolioReportMetadata:
    return PortfolioReportMetadata(target_currency=scope.target_currency, generated_at=scope.snapshot_as_of)


def _holding(
    asset_id: int,
    *,
    broker_id: int = 7,
    current_value: object | None = 1000,
    native_currency: str | None = CURRENCY,
    nav_weight_percent: object | None = 10,
) -> PortfolioHolding:
    return PortfolioHolding(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        quantity=Decimal("10"),
        current_value=(None if current_value is None else Decimal(str(current_value))),
        valuation_effective_currency=native_currency,
        valuation_source=("MISSING" if current_value is None else "MARKET_PRICE"),
        nav_weight_percent=(None if nav_weight_percent is None else Decimal(str(nav_weight_percent))),
    )


def _summary(*, holdings=(), **overrides) -> PortfolioSummary:
    defaults = {
        "net_worth": _money(1000),
        "total_invested": _money(1000),
        "total_gain_loss": _money(0),
        "total_gain_loss_percent": Decimal("0"),
        "cash_total": _money(0),
        "simple_roi_percent": Decimal("0"),
        "holdings": list(holdings),
        "market_value": _money(sum((h.current_value or Decimal("0")) for h in holdings)),
    }
    defaults.update(overrides)
    return PortfolioSummary(**defaults)


def _report(scope: BuildScope, *, summary: PortfolioSummary | None) -> PortfolioReportResponse:
    return PortfolioReportResponse(metadata=_metadata(scope), summary=summary, history=[], positions_contribution=None)


def _patch_report(monkeypatch, report: PortfolioReportResponse) -> list[int]:
    calls: list[int] = []

    async def _fake(self, user_id, query):  # noqa: ARG001
        calls.append(1)
        return report

    monkeypatch.setattr(PortfolioService, "get_report", _fake)
    return calls


def _patch_split_report(monkeypatch, *, broker_report: PortfolioReportResponse, portfolio_report: PortfolioReportResponse) -> dict[str, int]:
    """Returns the broker-filtered report when query.broker_ids is set, the whole-portfolio one when None."""
    counts = {"broker": 0, "portfolio": 0}

    async def _fake(self, user_id, query):  # noqa: ARG001
        if query.broker_ids:
            counts["broker"] += 1
            return broker_report
        counts["portfolio"] += 1
        return portfolio_report

    monkeypatch.setattr(PortfolioService, "get_report", _fake)
    return counts


def _patch_activity(monkeypatch, records: list[TradeActivityRecord], *, ownership_share: object = 1) -> list[int]:
    calls: list[int] = []

    async def _fake_load(context, scope):  # noqa: ARG001
        calls.append(1)
        return broker_cost_efficiency.BrokerPeriodActivity(records=tuple(records), ownership_share=Decimal(str(ownership_share)))

    monkeypatch.setattr(broker_cost_efficiency, "_load_broker_period_activity", _fake_load)
    return calls


def _trade(type_: TransactionType, amount: object | None, currency: str | None = CURRENCY) -> TradeActivityRecord:
    return TradeActivityRecord(type=type_, amount=(None if amount is None else Decimal(str(amount))), currency=currency)


# =============================================================================
# broker.concentration_context
# =============================================================================


class TestConcentrationContext:
    @pytest.mark.asyncio
    async def test_exposes_existing_dimensions_and_preserves_hhi_and_largest(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            holdings=[_holding(1, nav_weight_percent=60), _holding(2, nav_weight_percent=40)],
            allocation_by_type=[AllocationItem(name="ETF", value=Decimal("70"), amount=Decimal("1400")), AllocationItem(name="Stock", value=Decimal("30"), amount=Decimal("600"))],
            allocation_by_sector=[AllocationItem(name="Tech", value=Decimal("100"), amount=Decimal("2000"))],
            allocation_by_geography=[AllocationItem(name="US", value=Decimal("100"), amount=Decimal("2000"))],
        )
        _patch_report(monkeypatch, _report(scope, summary=summary))
        context = _make_context(scope, _registry(), _make_async_session())

        envelope = await context.resolve("broker.concentration_context", required=True)
        payload = envelope.payload

        assert [slice_["name"] for slice_ in payload["allocation_by_type"]] == ["ETF", "Stock"]
        assert payload["allocation_by_sector"][0]["name"] == "Tech"
        assert payload["allocation_by_geography"][0]["name"] == "US"
        assert payload["allocation_dimension_semantics"].startswith("Asset type, sector, and geography")
        assert payload["currency_allocation_semantics"].endswith("broker cash fields.")
        assert payload["concentration_semantics"].endswith("Cash is included in the denominator but is not itself an HHI term.")
        # HHI = 60^2 + 40^2 = 5200; largest = 60 - reconciles with broker.allocation_concentration.
        assert Decimal(payload["herfindahl_index_points"]) == Decimal("5200")
        assert Decimal(payload["largest_position_weight_percent"]) == Decimal("60")

    @pytest.mark.asyncio
    async def test_multi_currency_allocation_sums_and_orders_deterministically(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            holdings=[
                _holding(1, current_value=600, native_currency="EUR"),
                _holding(2, current_value=300, native_currency="USD"),
                _holding(3, current_value=100, native_currency="EUR"),
            ]
        )
        _patch_report(monkeypatch, _report(scope, summary=summary))
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_context", required=True)).payload
        slices = payload["allocation_by_currency"]

        # EUR = 700 (70%), USD = 300 (30%); descending share, all amounts in target ccy.
        assert [(s["currency"], s["amount"]["code"], Decimal(s["amount"]["amount"]), Decimal(s["percent"])) for s in slices] == [
            ("EUR", CURRENCY, Decimal("700"), Decimal("70")),
            ("USD", CURRENCY, Decimal("300"), Decimal("30")),
        ]
        coverage = payload["currency_coverage"]
        assert coverage["unknown_position_count"] == 0
        assert Decimal(coverage["covered_market_value"]["amount"]) == Decimal("1000")

    @pytest.mark.asyncio
    async def test_unknown_currency_and_unpriced_positions_go_to_explicit_bucket(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            holdings=[
                _holding(1, current_value=800, native_currency="EUR"),
                _holding(2, current_value=200, native_currency=None),  # undetermined currency
                _holding(3, current_value=None, native_currency=None),  # unpriced (MISSING)
            ]
        )
        _patch_report(monkeypatch, _report(scope, summary=summary))
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_context", required=True)).payload
        slices = payload["allocation_by_currency"]

        unknown = [s for s in slices if s["currency"] is None]
        assert len(unknown) == 1
        assert unknown[0]["position_count"] == 2
        assert Decimal(unknown[0]["amount"]["amount"]) == Decimal("200")
        # Unknown slice is always last.
        assert slices[-1]["currency"] is None
        coverage = payload["currency_coverage"]
        assert coverage["unknown_position_count"] == 2
        assert coverage["covered_position_count"] == 1
        assert Decimal(coverage["valued_market_value"]["amount"]) == Decimal("1000")

    @pytest.mark.asyncio
    async def test_empty_broker_builds_successfully(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=None))
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_context", required=True)).payload
        assert payload["position_count"] == 0
        assert payload["allocation_by_currency"] == []
        assert payload["herfindahl_index_points"] is None


# =============================================================================
# broker.concentration_comparison
# =============================================================================


class TestConcentrationComparison:
    @pytest.mark.asyncio
    async def test_filtered_broker_vs_unfiltered_portfolio_deltas(self, monkeypatch):
        scope = _scope()
        broker_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=60), _holding(2, nav_weight_percent=40)], market_value=_money(2000)))
        portfolio_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=30), _holding(2, nav_weight_percent=30), _holding(3, nav_weight_percent=40)], market_value=_money(5000)))
        counts = _patch_split_report(monkeypatch, broker_report=broker_report, portfolio_report=portfolio_report)
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_comparison", required=True)).payload

        assert payload["status"] == ConcentrationComparisonStatus.OK.value
        assert payload["broker_position_count"] == 2
        assert payload["portfolio_position_count"] == 3
        # broker HHI 60^2+40^2=5200; portfolio 30^2+30^2+40^2=3400; delta 1800.
        assert Decimal(payload["broker_herfindahl_index_points"]) == Decimal("5200")
        assert Decimal(payload["portfolio_herfindahl_index_points"]) == Decimal("3400")
        assert Decimal(payload["herfindahl_index_delta_points"]) == Decimal("1800")
        assert Decimal(payload["largest_position_weight_delta_percent"]) == Decimal("20")
        assert Decimal(payload["broker_share_of_portfolio_market_value_percent"]) == Decimal("40")
        # One filtered load + one unfiltered load only.
        assert counts == {"broker": 1, "portfolio": 1}

    @pytest.mark.asyncio
    async def test_whole_portfolio_loaded_once_and_shared_with_other_broker_components(self, monkeypatch):
        scope = _scope()
        broker_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=100)], market_value=_money(1000)))
        portfolio_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=50), _holding(9, nav_weight_percent=50)], market_value=_money(2000)))
        counts = _patch_split_report(monkeypatch, broker_report=broker_report, portfolio_report=portfolio_report)
        context = _make_context(scope, _registry(), _make_async_session())

        # Resolve the comparator plus other broker components that reuse broker.report.
        await context.resolve("broker.concentration_comparison", required=True)
        await context.resolve("broker.concentration_context", required=True)
        await context.resolve("broker.allocation_concentration", required=True)

        # broker.report memoized (1 filtered call) and whole-portfolio memoized (1 unfiltered call).
        assert counts == {"broker": 1, "portfolio": 1}

    @pytest.mark.asyncio
    async def test_unavailable_when_broker_empty(self, monkeypatch):
        scope = _scope()
        _patch_split_report(monkeypatch, broker_report=_report(scope, summary=None), portfolio_report=_report(scope, summary=_summary(holdings=[_holding(1)])))
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_comparison", required=True)).payload
        assert payload["status"] == ConcentrationComparisonStatus.UNAVAILABLE.value
        assert payload["reason_code"] == broker_concentration_context.REASON_BROKER_EMPTY
        assert payload["broker_herfindahl_index_points"] is None

    @pytest.mark.asyncio
    async def test_unavailable_when_portfolio_empty(self, monkeypatch):
        scope = _scope()
        _patch_split_report(monkeypatch, broker_report=_report(scope, summary=_summary(holdings=[_holding(1)])), portfolio_report=_report(scope, summary=None))
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_comparison", required=True)).payload
        assert payload["status"] == ConcentrationComparisonStatus.UNAVAILABLE.value
        assert payload["reason_code"] == broker_concentration_context.REASON_PORTFOLIO_EMPTY

    @pytest.mark.asyncio
    async def test_no_asset_or_row_ids_leaked(self, monkeypatch):
        scope = _scope()
        broker_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=100)], market_value=_money(1000)))
        portfolio_report = _report(scope, summary=_summary(holdings=[_holding(1, nav_weight_percent=100)], market_value=_money(1000)))
        _patch_split_report(monkeypatch, broker_report=broker_report, portfolio_report=portfolio_report)
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.concentration_comparison", required=True)).payload
        # Only broker_id (the scoped entity) is present; no asset_id/lot_id/transaction_id.
        leaking = [key for key in payload if key.endswith("asset_id") or key.endswith("lot_id") or key.endswith("transaction_id")]
        assert leaking == []
        assert payload["broker_id"] == 7


# =============================================================================
# broker.cost_efficiency
# =============================================================================


class TestCostEfficiency:
    @pytest.mark.asyncio
    async def test_turnover_signs_types_and_counts(self, monkeypatch):
        scope = _scope()
        summary = _summary(period_fees=_money(10))
        _patch_report(monkeypatch, _report(scope, summary=summary))
        records = [
            _trade(TransactionType.BUY, -1000),
            _trade(TransactionType.SELL, 400),
            _trade(TransactionType.DIVIDEND, 50),  # not a trade
        ]
        _patch_activity(monkeypatch, records)
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["transaction_count"] == 3
        assert payload["trade_count"] == 2
        assert payload["buy_count"] == 1
        assert payload["sell_count"] == 1
        turnover = payload["turnover"]
        assert Decimal(turnover["buy_turnover"]["amount"]) == Decimal("1000")
        assert Decimal(turnover["sell_turnover"]["amount"]) == Decimal("400")
        assert Decimal(turnover["gross_turnover"]["amount"]) == Decimal("1400")
        assert turnover["coverage"]["complete"] is True
        assert turnover["coverage"]["unusable_trade_count"] == 0
        assert Decimal(payload["ownership_share_ratio"]) == Decimal("1")
        # fees_to_turnover = 10 / 1400
        assert Decimal(payload["fees_to_turnover"]["value_ratio"]) == Decimal("10") / Decimal("1400")
        assert payload["fees_to_turnover"]["status"] == FeeStatus.RECORDED.value
        assert payload["fees_to_turnover"]["formula"] == "recorded_fees / gross_traded_amount"
        assert payload["fees_to_turnover"]["numerator"]["code"] == CURRENCY
        assert payload["fees_to_turnover"]["denominator"]["code"] == CURRENCY

    @pytest.mark.asyncio
    async def test_foreign_currency_trades_excluded_from_turnover_and_ratio_unavailable(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        records = [_trade(TransactionType.BUY, -1000, currency="EUR"), _trade(TransactionType.SELL, 500, currency="USD")]
        _patch_activity(monkeypatch, records)
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        turnover = payload["turnover"]
        assert Decimal(turnover["gross_turnover"]["amount"]) == Decimal("1000")  # USD leg excluded
        assert turnover["coverage"]["complete"] is False
        assert turnover["coverage"]["other_currency_trade_count"] == 1
        # Mixed-basis: ratio declined, never fabricated.
        assert payload["fees_to_turnover"]["value_ratio"] is None
        assert payload["fees_to_turnover"]["status"] == FeeStatus.UNAVAILABLE.value
        assert payload["fees_to_turnover"]["reason_code"] == broker_cost_efficiency.REASON_TURNOVER_INCOMPLETE

    @pytest.mark.asyncio
    async def test_zero_turnover_denominator_declines_ratio(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        _patch_activity(monkeypatch, [])  # no trades
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert Decimal(payload["turnover"]["gross_turnover"]["amount"]) == Decimal("0")
        assert payload["fees_to_turnover"]["value_ratio"] is None
        assert payload["fees_to_turnover"]["status"] == FeeStatus.NOT_APPLICABLE.value
        assert payload["fees_to_turnover"]["reason_code"] == broker_cost_efficiency.REASON_TURNOVER_ZERO

    @pytest.mark.asyncio
    async def test_missing_fees_stay_unavailable_not_zero(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=None)))
        _patch_activity(monkeypatch, [_trade(TransactionType.BUY, -1000)])
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["fees"]["status"] == FeeStatus.UNAVAILABLE.value
        assert payload["fees"]["amount"] is None
        for ratio_key in ("fees_to_turnover", "fees_to_invested", "fees_to_average_nav", "fees_to_income"):
            assert payload[ratio_key]["value_ratio"] is None
            assert payload[ratio_key]["status"] == FeeStatus.UNAVAILABLE.value
            assert payload[ratio_key]["reason_code"] == broker_cost_efficiency.REASON_FEES_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_fees_to_invested_and_average_nav_when_available(self, monkeypatch):
        scope = _scope()
        summary = _summary(period_fees=_money(20), total_invested=_money(1000), period_nav_start=_money(500), net_worth=_money(1500))
        _patch_report(monkeypatch, _report(scope, summary=summary))
        _patch_activity(monkeypatch, [_trade(TransactionType.BUY, -1000)])
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        # fees_to_invested = 20 / 1000
        assert Decimal(payload["fees_to_invested"]["value_ratio"]) == Decimal("20") / Decimal("1000")
        # No history fixture: endpoint mean NAV proxy = (500 + 1500) / 2 = 1000.
        assert Decimal(payload["fees_to_average_nav"]["value_ratio"]) == Decimal("20") / Decimal("1000")
        assert payload["denominators"]["average_nav_method"] == "endpoint_mean_nav_proxy"

    @pytest.mark.asyncio
    async def test_no_transaction_row_ids_leaked(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        _patch_activity(monkeypatch, [_trade(TransactionType.BUY, -1000)])
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        leaking = [key for key in payload if key.endswith("transaction_id") or key.endswith("asset_id") or key.endswith("lot_id")]
        assert leaking == []

    @pytest.mark.asyncio
    async def test_share_adjusted_turnover_and_ratio_reconciliation(self, monkeypatch):
        scope = _scope()
        # Engine fees are already share-adjusted; use the co-owned (0.5) fee value directly.
        summary = _summary(period_fees=_money(5), total_invested=_money(500))
        _patch_report(monkeypatch, _report(scope, summary=summary))
        _patch_activity(monkeypatch, [_trade(TransactionType.BUY, -1000)], ownership_share="0.5")
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert Decimal(payload["ownership_share_ratio"]) == Decimal("0.5")
        # Turnover is share-adjusted: |−1000| × 0.5 = 500.
        assert Decimal(payload["turnover"]["gross_turnover"]["amount"]) == Decimal("500")
        # fees_to_turnover = 5 / 500; both numerator and denominator on the same 0.5-ownership basis.
        assert Decimal(payload["fees_to_turnover"]["value_ratio"]) == Decimal("5") / Decimal("500")
        assert Decimal(payload["fees_to_invested"]["value_ratio"]) == Decimal("5") / Decimal("500")

    @pytest.mark.asyncio
    async def test_missing_amount_or_currency_counted_unusable_and_incomplete(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        records = [
            _trade(TransactionType.BUY, -800, currency=CURRENCY),  # usable
            _trade(TransactionType.SELL, None, currency=CURRENCY),  # missing amount
            _trade(TransactionType.BUY, -200, currency=None),  # missing currency
        ]
        _patch_activity(monkeypatch, records)
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        coverage = payload["turnover"]["coverage"]
        assert payload["trade_count"] == 3  # all counted, none silently omitted
        assert coverage["unusable_trade_count"] == 2
        assert coverage["target_currency_trade_count"] == 1
        assert coverage["complete"] is False
        assert Decimal(payload["turnover"]["gross_turnover"]["amount"]) == Decimal("800")  # never crashed on None
        assert payload["fees_to_turnover"]["reason_code"] == broker_cost_efficiency.REASON_TURNOVER_INCOMPLETE

    @pytest.mark.asyncio
    async def test_nonpositive_denominator_declines_invested_and_nav_ratios(self, monkeypatch):
        scope = _scope()
        # Negative invested and non-positive average NAV must decline, not divide.
        summary = _summary(period_fees=_money(10), total_invested=_money(-100), period_nav_start=_money(-50), net_worth=_money(0))
        _patch_report(monkeypatch, _report(scope, summary=summary))
        _patch_activity(monkeypatch, [_trade(TransactionType.BUY, -1000)])
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["fees_to_invested"]["value_ratio"] is None
        assert payload["fees_to_invested"]["status"] == FeeStatus.NOT_APPLICABLE.value
        assert payload["fees_to_invested"]["reason_code"] == broker_cost_efficiency.REASON_DENOMINATOR_NONPOSITIVE
        assert payload["fees_to_average_nav"]["value_ratio"] is None
        assert payload["fees_to_average_nav"]["status"] == FeeStatus.NOT_APPLICABLE.value
        assert payload["fees_to_average_nav"]["reason_code"] == broker_cost_efficiency.REASON_DENOMINATOR_NONPOSITIVE

    @pytest.mark.asyncio
    async def test_recorded_zero_fee_is_distinct_from_unavailable(self, monkeypatch):
        scope = _scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=None)))
        _patch_activity(
            monkeypatch,
            [
                _trade(TransactionType.FEE, 0),
                _trade(TransactionType.BUY, -1000),
            ],
        )
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["fees"]["status"] == FeeStatus.RECORDED.value
        assert Decimal(payload["fees"]["amount"]["amount"]) == Decimal("0")
        assert payload["fees_to_turnover"]["status"] == FeeStatus.RECORDED.value
        assert Decimal(payload["fees_to_turnover"]["value_ratio"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_fees_taxes_contributors_and_subtype_limits_are_separate(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            period_fees=_money(10),
            period_taxes=_money(4),
            period_fees_taxes=_money(14),
            period_income=_money(100),
            period_nav_start=_money(900),
            net_worth=_money(1100),
        )
        _patch_report(monkeypatch, _report(scope, summary=summary))
        _patch_activity(
            monkeypatch,
            [
                _trade(TransactionType.FEE, -10),
                _trade(TransactionType.TAX, -4),
                _trade(TransactionType.BUY, -1000),
            ],
        )
        context = _make_context(scope, _registry(), _make_async_session())

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["fees"]["status"] == FeeStatus.RECORDED.value
        assert payload["taxes"]["status"] == FeeStatus.RECORDED.value
        assert payload["total_costs"]["status"] == FeeStatus.RECORDED.value
        assert Decimal(payload["fees"]["amount"]["amount"]) == Decimal("10")
        assert Decimal(payload["taxes"]["amount"]["amount"]) == Decimal("4")
        assert Decimal(payload["total_costs"]["amount"]["amount"]) == Decimal("14")
        assert [row["category"] for row in payload["cost_contributors"]] == ["fees", "taxes"]
        assert Decimal(payload["unallocated_costs"]["amount"]) == Decimal("0")
        for key in ("trading_costs", "fx_costs", "other_costs"):
            assert payload[key]["status"] == FeeStatus.UNAVAILABLE.value
            assert payload[key]["reason_code"] == broker_cost_efficiency.REASON_SUBTYPE_UNAVAILABLE
        assert Decimal(payload["fees_to_income"]["value_ratio"]) == Decimal("0.1")
        assert Decimal(payload["total_costs_to_average_nav"]["value_ratio"]) == Decimal("0.014")


class TestCostEfficiencyPeriodActivityLoader:
    """DB-level tests of the real ``_load_broker_period_activity`` loader (boundary + share + access)."""

    @pytest.mark.asyncio
    async def test_boundary_is_start_exclusive_end_inclusive(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        session = await _make_real_db_session()
        await _seed_parents(session, user_id=scope.user_id, broker_ids=(scope.broker_id, 999))
        session.add(BrokerUserAccess(user_id=scope.user_id, broker_id=scope.broker_id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        session.add_all(
            [
                _tx(scope.broker_id, TransactionType.BUY, date(2026, 1, 1), amount=-100),  # excluded: on start boundary
                _tx(scope.broker_id, TransactionType.BUY, date(2026, 1, 2), amount=-200),  # included
                _tx(scope.broker_id, TransactionType.SELL, date(2026, 1, 31), amount=300),  # included: end boundary
                _tx(scope.broker_id, TransactionType.BUY, date(2026, 2, 1), amount=-400),  # excluded: after end
                _tx(999, TransactionType.BUY, date(2026, 1, 15), amount=-500),  # excluded: other broker
            ]
        )
        await session.commit()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        context = _make_context(scope, _registry(), session)

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert payload["transaction_count"] == 2
        assert payload["trade_count"] == 2
        # |−200| (BUY) + 300 (SELL) = 500; boundary-start and after-end trades excluded.
        assert Decimal(payload["turnover"]["gross_turnover"]["amount"]) == Decimal("500")
        await session.close()

    @pytest.mark.asyncio
    async def test_share_loaded_from_broker_user_access(self, monkeypatch):
        scope = _scope()
        session = await _make_real_db_session()
        await _seed_parents(session, user_id=scope.user_id, broker_ids=(scope.broker_id,))
        session.add(BrokerUserAccess(user_id=scope.user_id, broker_id=scope.broker_id, role=UserRole.OWNER, share_percentage=Decimal("0.25")))
        session.add(_tx(scope.broker_id, TransactionType.BUY, date(2026, 1, 10), amount=-1000))
        await session.commit()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        context = _make_context(scope, _registry(), session)

        payload = (await context.resolve("broker.cost_efficiency", required=True)).payload
        assert Decimal(payload["ownership_share_ratio"]) == Decimal("0.25")
        assert Decimal(payload["turnover"]["gross_turnover"]["amount"]) == Decimal("250")  # 1000 × 0.25
        await session.close()

    @pytest.mark.asyncio
    async def test_no_access_row_fails_explicitly(self, monkeypatch):
        scope = _scope()
        session = await _make_real_db_session()
        await _seed_parents(session, user_id=scope.user_id, broker_ids=(scope.broker_id,))
        # No BrokerUserAccess row for this user/broker.
        session.add(_tx(scope.broker_id, TransactionType.BUY, date(2026, 1, 10), amount=-1000))
        await session.commit()
        _patch_report(monkeypatch, _report(scope, summary=_summary(period_fees=_money(10))))
        context = _make_context(scope, _registry(), session)

        with pytest.raises(RequiredComponentBuildError):
            await context.resolve("broker.cost_efficiency", required=True)
        await session.close()
