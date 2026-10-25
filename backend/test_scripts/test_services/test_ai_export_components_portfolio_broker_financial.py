"""Focused tests for the real Portfolio/Broker AI Export financial `ComponentSpec`
builders (Phase 0 AI Export refinement, workstream E1).

Covers `backend.app.services.ai_export.components.portfolio_financial`,
`backend.app.services.ai_export.components.broker_financial` and their shared
`backend.app.services.ai_export.components.payloads.portfolio_broker` helpers:
one `PortfolioReportResponse`/`LotsAnalysisResponse` load per request across
every component (memoized, concurrency-safe), entity identity across detail
levels, empty portfolio/broker success, retaining every contributor/position,
engine-derived reconciliation, bucket edges/empty buckets, FIFO period-cutoff
and open-lot/no-`lot_id`/no-limit semantics, Broker scoping, deterministic
ordering, source-failure propagation and payload validation (`extra="forbid"`).

`PortfolioService.get_report`/`LotsAnalysisService.get_lots_analysis` are
monkeypatched at the class level (the actual engine entry points the builders
call through `payloads.portfolio_broker.load_portfolio_report`/
`load_lots_results`); no real database schema is created, matching the
existing `test_ai_export_component_runtime.py`/`test_ai_export_portfolio_broker.py`
pattern of exercising the builder/runtime layer without a live DB.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    LotAnalysisType,
    LotCustodySummarySchema,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportResponse,
    PortfolioSummary,
    PositionsContribution,
    YieldOnCostProvenance,
    YieldOnCostResult,
    YieldOnCostStatus,
)
from backend.app.services.ai_export.components import broker_financial, portfolio_financial
from backend.app.services.ai_export.components.envelope import ComponentPayloadValidationError, SectionEnvelope
from backend.app.services.ai_export.components.payloads import portfolio_broker as shared_payloads
from backend.app.services.ai_export.components.payloads.portfolio_broker import FifoLotRow
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    RequiredComponentBuildError,
    build_bucket_plan_for_scope,
)
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

CURRENCY = "USD"


# =============================================================================
# Construction helpers (real pydantic schema instances - no SimpleNamespace for
# anything the builders read strongly-typed fields from)
# =============================================================================


def _money(amount: object) -> Currency:
    return Currency(code=CURRENCY, amount=Decimal(str(amount)))


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-1",
        "user_id": 1,
        "domain": Domain.PORTFOLIO,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 10),
        "target_currency": CURRENCY,
        "broker_scope": (),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _make_async_session() -> AsyncSession:
    """Tableless in-memory `AsyncSession`: only satisfies `BuildContext`'s isinstance check.

    No statement is ever actually executed against it in these tests -
    `PortfolioService.get_report`/`LotsAnalysisService.get_lots_analysis` and the
    asset/broker metadata loaders are always monkeypatched before touching the DB.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


def _make_context(scope: BuildScope, registry: ComponentRegistry, session: AsyncSession) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(registry, request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


def _report_metadata(scope: BuildScope) -> PortfolioReportMetadata:
    return PortfolioReportMetadata(target_currency=scope.target_currency, generated_at=scope.snapshot_as_of)


class _StepHistoryPoint(PortfolioHistoryPoint):
    """``PortfolioHistoryPoint`` with the ``through`` of a step (D-P4, cure B) until the model itself carries it (MF)."""

    through: date


def _history_point(
    day: date,
    *,
    nav: object,
    capital_baseline: object,
    total_pnl: object,
    twrr: object | None = None,
    through: date | None = None,
) -> PortfolioHistoryPoint:
    """A history point that holds from ``day`` to ``through`` (D-P4: a step); one day when ``through`` is not given."""
    return _StepHistoryPoint(
        date=day,
        through=through or day,
        cash_value=_money(0),
        market_value=_money(nav),
        nav_value=_money(nav),
        capital_baseline=_money(capital_baseline),
        book_asset_like=_money(0),
        cash_from_contributed_capital=_money(0),
        cash_from_generated_returns=_money(0),
        total_pnl=_money(total_pnl),
        twrr=(Decimal(str(twrr)) if twrr is not None else None),
    )


def _required_yoc() -> YieldOnCostResult:
    return YieldOnCostResult(
        status=YieldOnCostStatus.NO_INCOME,
        value=Decimal("0"),
        provenance=YieldOnCostProvenance(
            window_start=date(2025, 1, 1),
            window_end=date(2025, 12, 31),
            first_pair_transaction_date=date(2025, 1, 1),
            gross_income_transaction_count=0,
            gross_income_per_unit=_money(0),
            net_zero=False,
        ),
    )


def _holding(asset_id: int, broker_id: int, *, quantity: object = 10, current_value: object = 1000, valuation_source: str | None = None) -> PortfolioHolding:
    return PortfolioHolding(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        quantity=Decimal(str(quantity)),
        current_value=Decimal(str(current_value)),
        valuation_source=valuation_source,
        nav_weight_percent=Decimal("10"),
        yield_on_cost=_required_yoc(),
    )


def _contribution_row(asset_id: int, broker_id: int, *, period_pnl: object = 100) -> AssetPeriodContribution:
    return AssetPeriodContribution(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        period_pnl=Decimal(str(period_pnl)),
    )


def _summary(*, holdings=(), allocation_by_type=(), contribution: PositionsContribution | None = None, **overrides) -> PortfolioSummary:  # noqa: ARG001 - contribution lives on PortfolioReportResponse.positions_contribution, not PortfolioSummary; kept for call-site symmetry
    defaults = {
        "net_worth": _money(1000),
        "total_invested": _money(1000),
        "total_gain_loss": _money(0),
        "total_gain_loss_percent": Decimal("0"),
        "cash_total": _money(0),
        "simple_roi_percent": Decimal("0"),
        "holdings": list(holdings),
        "allocation_by_type": list(allocation_by_type),
        "period_pnl": _money(0),
        "period_unrealized_gain_loss_delta": _money(0),
        "period_realized_gain_loss": _money(0),
        "period_income": _money(0),
        "period_fees_taxes": _money(0),
        "period_other_result": _money(0),
    }
    defaults.update(overrides)
    return PortfolioSummary(**defaults)


def _report(scope: BuildScope, *, summary: PortfolioSummary | None = None, history=(), contribution: PositionsContribution | None = None) -> PortfolioReportResponse:
    return PortfolioReportResponse(
        metadata=_report_metadata(scope),
        summary=summary,
        history=list(history),
        positions_contribution=contribution,
    )


def _lot(
    asset_id: int,
    lot_id: int,
    *,
    opening_broker_id: int = 1,
    opening_date: date = date(2025, 1, 1),
    closing_date: date | None = None,
    open_quantity: object = 10,
    realized_quantity: object = 0,
    original_quantity: object = 10,
    current_custody: list[LotCustodySummarySchema] | None = None,
    open_value: object | None = None,
    market_pnl: object | None = None,
    realized_pnl: object = 0,
    cumulative_proceeds: object = 0,
    total_pnl: object | None = None,
    net_total_pnl: object | None = None,
    asset_income: object = 0,
    allocated_fees: object = 0,
    allocated_taxes: object = 0,
    states: list[str] | None = None,
    net_metrics_status: str = "AVAILABLE",
) -> LotSummarySchema:
    return LotSummarySchema(
        lot_id=lot_id,
        opening_transaction_id=lot_id,
        asset_id=asset_id,
        direction="LONG",
        opening_broker_id=opening_broker_id,
        opening_date=opening_date,
        closing_date=closing_date,
        opening_unit_price=Decimal("100"),
        original_quantity=Decimal(str(original_quantity)),
        original_cost=Decimal("1000"),
        open_quantity=Decimal(str(open_quantity)),
        realized_quantity=Decimal(str(realized_quantity)),
        realized_pnl=Decimal(str(realized_pnl)),
        cumulative_proceeds=Decimal(str(cumulative_proceeds)),
        current_custody=current_custody or [],
        open_value=(Decimal(str(open_value)) if open_value is not None else None),
        market_pnl=(Decimal(str(market_pnl)) if market_pnl is not None else None),
        total_pnl=(Decimal(str(total_pnl)) if total_pnl is not None else None),
        net_total_pnl=(Decimal(str(net_total_pnl)) if net_total_pnl is not None else None),
        asset_income=Decimal(str(asset_income)),
        allocated_fees=Decimal(str(allocated_fees)),
        allocated_taxes=Decimal(str(allocated_taxes)),
        states=states or [],
        net_metrics_status=net_metrics_status,
    )


def _lots_response(asset_id: int, lots: list[LotSummarySchema]) -> LotsAnalysisResponse:
    return LotsAnalysisResponse(
        asset_id=asset_id,
        target_currency=CURRENCY,
        calculation_status="COMPLETE",
        calculation_metadata=LotsAnalysisMetadata(requested_analyses=[LotAnalysisType.LOT_SUMMARY], generated_at=date(2026, 1, 10)),
        lots=list(lots),
    )


# B3b: the lot figures the lots analysis leaves None when a rate they need is missing...
_UNVALUED_LOT_FIELDS = ("opening_unit_price", "original_cost", "cumulative_proceeds", "realized_pnl", "asset_income", "allocated_fees", "allocated_taxes")
# ...the `FifoLotRow` fields they become (plus `residual_cost_basis`, derived from the original cost)...
_UNVALUED_ROW_FIELDS = ("opening_unit_price", "original_cost", "cumulative_proceeds", "realized_pnl", "income", "fees", "taxes")
# ...and the per-asset `FifoAssetSummaryRow` totals summed from them.
_SUMMED_MONEY_FIELDS = ("original_cost", "residual_cost_basis", "cumulative_proceeds", "realized_pnl", "income", "fees", "taxes")
# The eight `FifoLotRow` amounts B3b made nullable: a lot with one of them unknown is what `count_unavailable_amount_lots` counts.
_NULLABLE_ROW_FIELDS = ("opening_unit_price", *_SUMMED_MONEY_FIELDS)
# The market-dependent amounts, optional before B3b: None for a lot without a market price, which is no B3b unknown.
_MARKET_FIGURES = {"open_value": _money(700), "unrealized_pnl": _money(200), "total_pnl": _money(300), "net_total_pnl": _money(285)}


def _unvalued_lot(asset_id: int, lot_id: int, **kwargs) -> LotSummarySchema:
    """A lot whose target-currency figures the lots analysis could not value (B3b): each None, its net metrics UNAVAILABLE."""
    lot = _lot(asset_id, lot_id, **kwargs)
    return LotSummarySchema.model_validate({**lot.model_dump(), **dict.fromkeys(_UNVALUED_LOT_FIELDS), "net_metrics_status": "UNAVAILABLE"})


def _fifo_row(lot_ref: str, **overrides) -> FifoLotRow:
    """A validated FIFO row of asset 1: 5 of 10 still open (cost 500 of 1000), the other 5 sold for 600."""
    fields = {
        "lot_ref": lot_ref,
        "asset_id": 1,
        "asset_name": "Asset 1",
        "asset_ticker": "A1",
        "opening_broker_id": 1,
        "direction": "LONG",
        "status": "PARTIAL",
        "opening_date": date(2025, 1, 1),
        "opening_unit_price": _money(100),
        "original_quantity": Decimal("10"),
        "open_quantity": Decimal("5"),
        "realized_quantity": Decimal("5"),
        "original_cost": _money(1000),
        "residual_cost_basis": _money(500),
        "cumulative_proceeds": _money(600),
        "realized_pnl": _money(100),
        "income": _money(20),
        "fees": _money(10),
        "taxes": _money(5),
        "net_metrics_status": "AVAILABLE",
    }
    return FifoLotRow.model_validate({**fields, **overrides})


# The summed totals of two default `_fifo_row`s.
_TWO_ROW_TOTALS = {"original_cost": 2000, "residual_cost_basis": 1000, "cumulative_proceeds": 1200, "realized_pnl": 200, "income": 40, "fees": 20, "taxes": 10}


def _total_fifo_residual_cost_basis():
    """The helper B3b adds, looked up when called: until it exists only the tests using it fail, not the module."""
    helper = getattr(shared_payloads, "total_fifo_residual_cost_basis", None)
    assert helper is not None, "payloads.portfolio_broker.total_fifo_residual_cost_basis does not exist"
    return helper


def _count_unavailable_amount_lots():
    """The counting helper of `unavailable_amount_lot_count`, looked up when called: until it exists only the tests using it fail."""
    helper = getattr(shared_payloads, "count_unavailable_amount_lots", None)
    assert helper is not None, "payloads.portfolio_broker.count_unavailable_amount_lots does not exist"
    return helper


def _asset_meta(asset_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=asset_id,
        display_name=f"Asset {asset_id}",
        identifier_ticker=f"A{asset_id}",
    )


def _broker_meta(broker_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=broker_id, name=f"Broker {broker_id}")


def _patch_report(monkeypatch: pytest.MonkeyPatch, report: PortfolioReportResponse) -> list[int]:
    """Monkeypatches `PortfolioService.get_report` to always return `report`; returns a call counter."""
    calls: list[int] = []

    async def _fake_get_report(self, user_id, query):  # noqa: ARG001 - signature must match PortfolioService.get_report
        calls.append(1)
        return report

    monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
    return calls


def _patch_lots(monkeypatch: pytest.MonkeyPatch, responses_by_asset: dict[int, LotsAnalysisResponse], *, asset_ids: set[int] | None = None) -> list[int]:
    """Monkeypatches asset discovery + `LotsAnalysisService.get_lots_analysis`; returns a call counter for the latter."""
    calls: list[int] = []

    async def _fake_get_lots_analysis(self, **kwargs):  # noqa: ARG001
        calls.append(1)
        return responses_by_asset[kwargs["asset_id"]]

    async def _fake_discover(session, scope):  # noqa: ARG001
        return set(asset_ids if asset_ids is not None else responses_by_asset)

    async def _fake_resolve_accessible_broker_ids(session, user_id):  # noqa: ARG001
        return []

    monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", _fake_get_lots_analysis)
    # `discover_transacted_asset_ids`/`resolve_accessible_broker_ids` are called
    # as module-globals from within `load_lots_results`'s closure, which is
    # defined in `shared_payloads` itself - patching them there (not on
    # portfolio_financial/broker_financial, which never import those names) is
    # what actually takes effect. `resolve_accessible_broker_ids` is only
    # exercised for a whole-portfolio (empty `broker_scope`) scope; tests that
    # pass an explicit non-empty `broker_scope` never reach it.
    monkeypatch.setattr(shared_payloads, "discover_transacted_asset_ids", _fake_discover)
    monkeypatch.setattr(shared_payloads, "resolve_accessible_broker_ids", _fake_resolve_accessible_broker_ids)
    return calls


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, *, asset_ids: list[int] = (), broker_ids: list[int] = ()) -> None:
    async def _fake_assets(session, ids):  # noqa: ARG001
        return {asset_id: _asset_meta(asset_id) for asset_id in asset_ids}

    monkeypatch.setattr(portfolio_financial, "_load_asset_metadata", _fake_assets)
    monkeypatch.setattr(broker_financial, "_load_asset_metadata", _fake_assets)


def _registry(components) -> ComponentRegistry:
    return ComponentRegistry(components)


# =============================================================================
# One report load per request, across components and under concurrency
# =============================================================================


class TestOneReportLoadPerRequest:
    @pytest.mark.asyncio
    async def test_single_get_report_call_shared_across_every_portfolio_component(self, monkeypatch):
        scope = _scope()
        report = _report(scope, summary=_summary(holdings=[_holding(1, 1)]), history=[_history_point(date(2026, 1, 1), nav=1000, capital_baseline=1000, total_pnl=0)])
        calls = _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        for component_id in ("portfolio.summary", "portfolio.positions", "portfolio.allocations_cash", "portfolio.performance", "portfolio.flows_income", "portfolio.fees_taxes"):
            await context.resolve(component_id, required=True)

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_memoized_under_concurrent_resolution(self, monkeypatch):
        scope = _scope()
        report = _report(scope, summary=_summary(holdings=[_holding(1, 1)]))
        calls = _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        await asyncio.gather(*(context.resolve(cid, required=True) for cid in ("portfolio.summary", "portfolio.positions", "portfolio.allocations_cash") for _ in range(3)))

        assert len(calls) == 1


# =============================================================================
# Entity identity across detail levels
# =============================================================================


class TestEntityIdentityAcrossDetailLevels:
    @pytest.mark.asyncio
    async def test_position_and_contributor_cardinality_identical_across_detail_levels(self, monkeypatch):
        holdings = [_holding(1, 1), _holding(2, 1), _holding(3, 2)]
        contributions = PositionsContribution(positions=[_contribution_row(1, 1), _contribution_row(2, 1), _contribution_row(3, 2)])

        for detail_level in (DetailLevel.COMPACT, DetailLevel.STANDARD, DetailLevel.FULL):
            scope = _scope(detail_level=detail_level)
            report = _report(scope, summary=_summary(holdings=holdings), history=[_history_point(date(2026, 1, 1), nav=1000, capital_baseline=1000, total_pnl=0)], contribution=contributions)
            _patch_report(monkeypatch, report)
            _patch_lots(monkeypatch, {})
            _patch_metadata(monkeypatch)
            registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
            context = _make_context(scope, registry, _make_async_session())

            positions_envelope = await context.resolve("portfolio.positions", required=True)
            performance_envelope = await context.resolve("portfolio.performance", required=True)

            assert positions_envelope.payload["position_count"] == 3
            assert len(positions_envelope.payload["positions"]) == 3
            assert positions_envelope.payload["positions"][0]["unit_price"] == {
                "code": CURRENCY,
                "amount": "100",
            }
            assert performance_envelope.payload["contributor_count"] == 3
            assert len(performance_envelope.payload["contributors"]) == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("broker_scope", "holding_brokers", "contributor_brokers", "expected_position", "expected_period_contributor"),
        (
            ((1,), (1,), (1,), 1, 1),
            ((1, 2), (1, 2), (1, 2), 2, 2),
            ((1, 2), (1,), (1,), 1, 1),
            ((1, 2), (1,), (1, 2), 1, 2),
        ),
    )
    async def test_broker_universe_counts_are_explicit(
        self,
        monkeypatch,
        broker_scope,
        holding_brokers,
        contributor_brokers,
        expected_position,
        expected_period_contributor,
    ):
        scope = _scope(broker_scope=broker_scope)
        holdings = [_holding(index, broker_id) for index, broker_id in enumerate(holding_brokers, start=1)]
        contributions = PositionsContribution(positions=[_contribution_row(index, broker_id) for index, broker_id in enumerate(contributor_brokers, start=1)])
        report = _report(
            scope,
            summary=_summary(holdings=holdings),
            history=[
                _history_point(
                    date(2026, 1, 1),
                    nav=1000,
                    capital_baseline=1000,
                    total_pnl=0,
                )
            ],
            contribution=contributions,
        )
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        summary = await context.resolve("portfolio.summary", required=True)
        provenance = await context.resolve("portfolio.provenance", required=True)
        performance = await context.resolve("portfolio.performance", required=True)

        assert "broker_count" not in summary.payload
        assert summary.payload["position_broker_count"] == expected_position
        assert provenance.payload["scoped_broker_count"] == len(broker_scope)
        assert provenance.payload["broker_scope"] == list(broker_scope)
        assert performance.payload["period_contributor_broker_count"] == expected_period_contributor

    @pytest.mark.asyncio
    async def test_position_unit_price_reconciles_quantity_and_current_value(self, monkeypatch):
        scope = _scope()
        report = _report(
            scope,
            summary=_summary(
                holdings=[
                    _holding(
                        1,
                        1,
                        quantity=15000,
                        current_value=14661,
                    )
                ]
            ),
        )
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        positions = await context.resolve("portfolio.positions", required=True)

        assert positions.payload["positions"][0]["unit_price"] == {
            "code": CURRENCY,
            "amount": "0.9774",
        }

    def test_hhi_contract_uses_points_without_percent_label(self):
        positions = [
            shared_payloads.PositionRow(
                asset_id=1,
                asset_name="Asset 1",
                asset_type="ETF",
                quantity=Decimal("1"),
                nav_weight_percent=Decimal("30"),
            ),
            shared_payloads.PositionRow(
                asset_id=2,
                asset_name="Asset 2",
                asset_type="ETF",
                quantity=Decimal("1"),
                nav_weight_percent=Decimal("70"),
            ),
        ]

        largest, herfindahl = broker_financial._concentration_metrics(positions)
        payload = broker_financial.BrokerAllocationConcentrationPayload(
            broker_id=1,
            as_of=date(2026, 1, 10),
            target_currency=CURRENCY,
            position_count=2,
            cash_total=_money(0),
            largest_position_weight_percent=largest,
            herfindahl_index_points=herfindahl,
        ).model_dump(mode="json")

        assert payload["largest_position_weight_percent"] == "70"
        assert payload["herfindahl_index_points"] == "5800"
        assert "herfindahl_index_percent" not in payload


# =============================================================================
# Empty portfolio/broker is valid success, never a source failure
# =============================================================================


class TestEmptyPortfolioIsValidSuccess:
    @pytest.mark.asyncio
    async def test_empty_portfolio_summary_and_positions_build_successfully(self, monkeypatch):
        scope = _scope()
        report = _report(scope, summary=_summary(holdings=[]), history=[])
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        summary_envelope = await context.resolve("portfolio.summary", required=True)
        positions_envelope = await context.resolve("portfolio.positions", required=True)
        fifo_summary_envelope = await context.resolve("portfolio.fifo_summary", required=True)
        fifo_lots_envelope = await context.resolve("portfolio.fifo_lots", required=True)

        assert summary_envelope.payload["position_count"] == 0
        assert positions_envelope.payload["positions"] == []
        assert fifo_summary_envelope.payload["asset_count"] == 0
        assert fifo_lots_envelope.payload["lots"] == []

    @pytest.mark.asyncio
    async def test_empty_broker_builds_successfully(self, monkeypatch):
        scope = _scope(domain=Domain.BROKER, broker_id=7, broker_scope=(7,))
        report = _report(scope, summary=_summary(holdings=[]), history=[])
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(broker_financial.BROKER_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        summary_envelope = await context.resolve("broker.summary", required=True)
        fifo_envelope = await context.resolve("broker.fifo_lots", required=True)

        assert summary_envelope.payload["broker_id"] == 7
        assert summary_envelope.payload["position_count"] == 0
        assert fifo_envelope.payload["lots"] == []


# =============================================================================
# All contributors retained (no top-N filtering)
# =============================================================================


class TestAutonomousGeneralEvidence:
    @pytest.mark.asyncio
    async def test_portfolio_allocations_include_currency_hhi_and_largest_position(self, monkeypatch):
        scope = _scope()
        first = _holding(1, 1, current_value=600).model_copy(
            update={
                "nav_weight_percent": Decimal("60"),
                "valuation_effective_currency": "USD",
            }
        )
        second = _holding(2, 2, current_value=400).model_copy(
            update={
                "nav_weight_percent": Decimal("40"),
                "valuation_effective_currency": "EUR",
            }
        )
        report = _report(scope, summary=_summary(holdings=[first, second], market_value=_money(1000)))
        _patch_report(monkeypatch, report)
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.allocations_cash", required=True)

        assert envelope.payload["position_count"] == 2
        assert Decimal(envelope.payload["largest_position_weight_percent"]) == Decimal("60")
        assert Decimal(envelope.payload["herfindahl_index_points"]) == Decimal("5200")
        assert envelope.payload["currency_allocation_semantics"].startswith("Currency allocation groups current position market value")
        assert envelope.payload["concentration_semantics"].endswith("Cash is included in the denominator but is not itself an HHI term.")
        assert [(row["currency"], Decimal(row["amount"]["amount"])) for row in envelope.payload["by_currency"]] == [
            ("USD", Decimal("600")),
            ("EUR", Decimal("400")),
        ]
        assert envelope.payload["currency_coverage"]["unknown_position_count"] == 0

    @pytest.mark.asyncio
    async def test_fifo_summary_exports_per_asset_economics_and_coverage(self, monkeypatch):
        scope = _scope(broker_scope=(1, 2))
        open_lot = _lot(
            1,
            701,
            opening_broker_id=1,
            open_quantity=10,
            open_value=1300,
            market_pnl=300,
            total_pnl=320,
            net_total_pnl=305,
            asset_income=20,
            allocated_fees=10,
            allocated_taxes=5,
            states=["OPEN"],
            current_custody=[
                LotCustodySummarySchema(custody_type="BROKER", broker_id=2, quantity=Decimal("8")),
                LotCustodySummarySchema(custody_type="IN_TRANSIT", broker_id=None, quantity=Decimal("2")),
            ],
        )
        closed_lot = _lot(
            1,
            702,
            opening_broker_id=2,
            closing_date=date(2026, 1, 5),
            open_quantity=0,
            realized_quantity=10,
            realized_pnl=100,
            cumulative_proceeds=1100,
            total_pnl=110,
            net_total_pnl=100,
            asset_income=10,
            allocated_fees=5,
            allocated_taxes=5,
            states=["CLOSED"],
        )
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [closed_lot, open_lot])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1, 2])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_summary", required=True)
        row = envelope.payload["assets"][0]

        assert envelope.payload["asset_count"] == 1
        assert envelope.payload["cost_allocation_semantics"].startswith("Fees and taxes are amounts deterministically allocated")
        assert row["open_lot_count"] == 1
        assert row["closed_lot_count"] == 1
        assert Decimal(row["open_value"]["amount"]) == Decimal("1300")
        assert Decimal(row["unrealized_pnl"]["amount"]) == Decimal("300")
        assert Decimal(row["potential_gain"]["amount"]) == Decimal("300")
        assert Decimal(row["potential_loss"]["amount"]) == Decimal("0")
        assert Decimal(row["realized_pnl"]["amount"]) == Decimal("100")
        assert Decimal(row["income"]["amount"]) == Decimal("30")
        assert Decimal(row["fees"]["amount"]) == Decimal("15")
        assert Decimal(row["taxes"]["amount"]) == Decimal("10")
        assert row["value_coverage_status"] == "complete"
        assert row["broker_ids"] == [1, 2]
        assert row["has_in_transit_custody"] is True


class TestAllContributorsRetained:
    @pytest.mark.asyncio
    async def test_every_contributor_and_unallocated_and_effect_row_retained(self, monkeypatch):
        scope = _scope()
        contributions = PositionsContribution(
            positions=[_contribution_row(asset_id, asset_id % 3 + 1, period_pnl=asset_id) for asset_id in range(1, 26)],
            gross_gains=Decimal("500"),
            gross_losses=Decimal("50"),
        )
        report = _report(scope, summary=_summary(holdings=[_holding(a, a % 3 + 1) for a in range(1, 26)]), history=[_history_point(date(2026, 1, 1), nav=1000, capital_baseline=1000, total_pnl=0)], contribution=contributions)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.performance", required=True)

        assert envelope.payload["contributor_count"] == 25
        assert len(envelope.payload["contributors"]) == 25
        assert Decimal(envelope.payload["gross_gains"]["amount"]) == Decimal("500")
        assert Decimal(envelope.payload["gross_losses"]["amount"]) == Decimal("50")


# =============================================================================
# Engine reconciliation validation
# =============================================================================


# Each domain's reconciliation, resolved over its own scope: the broker component reads the very same engine fields
# off a single-broker report.
_RECONCILIATION_SCOPES = {
    "portfolio": ({}, portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS),
    "broker": ({"domain": Domain.BROKER, "broker_id": 7, "broker_scope": (7,)}, broker_financial.BROKER_FINANCIAL_COMPONENTS),
}


async def _resolve_reconciliation(monkeypatch: pytest.MonkeyPatch, domain: str, summary: PortfolioSummary) -> SectionEnvelope:
    """The `{domain}.reconciliation` envelope built over a report whose summary is `summary`."""
    scope_overrides, components = _RECONCILIATION_SCOPES[domain]
    scope = _scope(**scope_overrides)
    _patch_report(monkeypatch, _report(scope, summary=summary))
    _patch_lots(monkeypatch, {})
    _patch_metadata(monkeypatch)
    context = _make_context(scope, _registry(components), _make_async_session())
    return await context.resolve(f"{domain}.reconciliation", required=True)


def _summary_with_residual(residual: Decimal) -> PortfolioSummary:
    """Engine fields decomposing into exactly 100 (60 + 20 + 30 - 10 + 0) under a period P&L of 100 + `residual`."""
    return _summary(
        period_pnl=_money(Decimal("100") + residual),
        period_unrealized_gain_loss_delta=_money(60),
        period_realized_gain_loss=_money(20),
        period_income=_money(30),
        period_fees_taxes=_money(10),
        period_other_result=_money(0),
    )


class TestEngineReconciliation:
    """`reconciled` says whether the engine's period P&L decomposition closes: period_pnl == unrealized delta + realized
    + income - fees/taxes + other result. The engine builds `period_other_result` as the closing term of that very
    identity, so the residual is zero by construction up to Decimal rounding: a residual below CONVERSION_DUST is that
    rounding and reconciles (C-53), one of CONVERSION_DUST or more does not, and `residual` always states the exact
    difference, never zeroed. Portfolio and Broker read the same engine fields and share the rule."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_reconciled_true_when_engine_fields_sum_exactly(self, monkeypatch, domain):
        summary = _summary(
            period_pnl=_money(100),
            period_unrealized_gain_loss_delta=_money(60),
            period_realized_gain_loss=_money(20),
            period_income=_money(30),
            period_fees_taxes=_money(10),
            period_other_result=_money(0),
        )
        # period_pnl == unrealized_delta + realized + income - fees_taxes + other_result -> 60+20+30-10+0=100
        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        assert envelope.payload["reconciled"] is True
        assert Decimal(envelope.payload["residual"]["amount"]) == Decimal("0")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_reconciled_false_and_residual_reported_when_engine_fields_do_not_sum(self, monkeypatch, domain):
        summary = _summary(
            period_pnl=_money(999),
            period_unrealized_gain_loss_delta=_money(60),
            period_realized_gain_loss=_money(20),
            period_income=_money(30),
            period_fees_taxes=_money(10),
            period_other_result=_money(0),
        )
        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        assert envelope.payload["reconciled"] is False
        assert Decimal(envelope.payload["residual"]["amount"]) == Decimal("899")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_reconciliation_none_when_engine_fields_missing_not_fabricated(self, monkeypatch, domain):
        summary = _summary(period_pnl=None, period_unrealized_gain_loss_delta=None, period_realized_gain_loss=None, period_income=None, period_fees_taxes=None, period_other_result=None)
        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        assert envelope.payload["reconciled"] is None
        assert envelope.payload["residual"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    @pytest.mark.parametrize(
        "residual",
        [
            pytest.param(Decimal("1E-24"), id="rounding-dust"),
            pytest.param(Decimal("-1E-24"), id="negative-rounding-dust"),
            pytest.param(CONVERSION_DUST - Decimal("1E-18"), id="just-below-conversion-dust"),
        ],
    )
    async def test_residual_below_conversion_dust_is_reconciled_and_still_stated_exactly(self, monkeypatch, domain, residual):
        """Rounding, not a reconciliation gap: reconciled. The residual is not zeroed: it is the exact difference."""
        envelope = await _resolve_reconciliation(monkeypatch, domain, _summary_with_residual(residual))

        assert (envelope.payload["reconciled"], Decimal(envelope.payload["residual"]["amount"])) == (True, residual)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    @pytest.mark.parametrize(
        "residual",
        [
            pytest.param(CONVERSION_DUST, id="exactly-conversion-dust"),
            pytest.param(-CONVERSION_DUST, id="negative-exactly-conversion-dust"),
            pytest.param(Decimal("-99"), id="negative-material"),
        ],
    )
    async def test_residual_of_conversion_dust_or_more_is_not_reconciled(self, monkeypatch, domain, residual):
        """The tolerance is strict and two-sided: a residual as large as CONVERSION_DUST, of either sign, is a gap."""
        envelope = await _resolve_reconciliation(monkeypatch, domain, _summary_with_residual(residual))

        assert (envelope.payload["reconciled"], Decimal(envelope.payload["residual"]["amount"])) == (False, residual)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_engine_closing_term_reconciles_despite_decimal_rounding(self, monkeypatch, domain):
        """The defect as real snapshots showed it: figures converted to the report currency carry Decimal's 28 digits,
        and `period_other_result` is the engine's closing term of the identity the component re-adds (PortfolioService:
        pnl - unrealized delta - realized - income + fees/taxes). Grouped differently, the re-addition rounds
        differently and leaves 1E-24: reconciled, with the 1E-24 still stated."""
        pnl, unrealized_delta, realized, income, fees_taxes = (Decimal(amount) / Decimal("1.09") for amount in ("2500", "1500", "700", "400", "150"))
        summary = _summary(
            period_pnl=_money(pnl),
            period_unrealized_gain_loss_delta=_money(unrealized_delta),
            period_realized_gain_loss=_money(realized),
            period_income=_money(income),
            period_fees_taxes=_money(fees_taxes),
            period_other_result=_money(pnl - unrealized_delta - realized - income + fees_taxes),
        )

        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        assert (envelope.payload["reconciled"], Decimal(envelope.payload["residual"]["amount"])) == (True, Decimal("1E-24"))


# J-14: the residual and the tolerance the two reconciliation components wrote in line at `e6d3e61e0`
# (portfolio_financial.py:491-495, broker_financial.py:432-436), as written, and the module each domain's builder lives in.
_RECONCILIATION_MODULES = {"portfolio": portfolio_financial, "broker": broker_financial}


def _head_inline_residual(summary: PortfolioSummary) -> Decimal:
    return summary.period_pnl.amount - (summary.period_unrealized_gain_loss_delta.amount + summary.period_realized_gain_loss.amount + summary.period_income.amount - summary.period_fees_taxes.amount + summary.period_other_result.amount)


def _head_inline_reconciled(residual_amount: Decimal) -> bool:
    return abs(residual_amount) < CONVERSION_DUST


_IDENTITY_ARGUMENTS = ("pnl", "ugl_delta", "realized", "income", "fees_taxes", "other_result")


def _identity_summary(figures: tuple[Decimal, ...]) -> PortfolioSummary:
    """A summary whose six period figures are `figures`, in `period_identity_residual`'s order."""
    pnl, ugl_delta, realized, income, fees_taxes, other_result = figures
    return _summary(
        period_pnl=_money(pnl),
        period_unrealized_gain_loss_delta=_money(ugl_delta),
        period_realized_gain_loss=_money(realized),
        period_income=_money(income),
        period_fees_taxes=_money(fees_taxes),
        period_other_result=_money(other_result),
    )


def _identity_figures(summary: PortfolioSummary) -> tuple[Decimal, ...]:
    """The six period figures of `summary`, in `period_identity_residual`'s order."""
    return (
        summary.period_pnl.amount,
        summary.period_unrealized_gain_loss_delta.amount,
        summary.period_realized_gain_loss.amount,
        summary.period_income.amount,
        summary.period_fees_taxes.amount,
        summary.period_other_result.amount,
    )


def _closed_by_the_engine() -> tuple[Decimal, ...]:
    """Five figures in one currency converted at 1.19533 (28 significant digits each), closed by PortfolioService's own
    term (pnl - unrealized delta - realized - income + fees/taxes): the identity leaves 6E-23 of rounding, a figure
    every other association of the sum misses (test_period_and_unit_costs, the-last-digit)."""
    pnl, ugl_delta, realized, income, fees_taxes = (Decimal(amount) / Decimal("1.19533") for amount in ("92967.16", "42957.89", "31465", "58674.48", "8109.5"))
    return pnl, ugl_delta, realized, income, fees_taxes, pnl - ugl_delta - realized - income + fees_taxes


def _missing_a_converted_amount() -> tuple[Decimal, ...]:
    """Amounts times 10-digit rates (23 and 22 significant digits) and amounts converted by division and across two
    rates (28): a closing term that misses 12.5 / 1.0876543219, a real gap stated to its last digit."""
    ugl_delta = Decimal("1234567.891234") * Decimal("1.0876543219")
    realized = Decimal("-987654.321987") * Decimal("0.9123456789")
    income = Decimal("8109.5") / Decimal("1.19533") * Decimal("1.0876543219")
    fees_taxes = Decimal("2500") / Decimal("1.09")
    pnl = Decimal("-31465") / Decimal("1.19533")
    return pnl, ugl_delta, realized, income, fees_taxes, pnl - ugl_delta - realized - income + fees_taxes - Decimal("12.5") / Decimal("1.0876543219")


def _off_by(offset: Decimal) -> tuple[Decimal, ...]:
    """Amounts times 10-digit rates (20 to 23 significant digits, exact), under a P&L that exceeds their sum by
    `offset`: the identity leaves `offset` exactly."""
    ugl_delta = Decimal("1234567.891234") * Decimal("1.0876543219")
    realized = Decimal("-987654.321987") * Decimal("0.9123456789")
    income = Decimal("4321.123456") * Decimal("1.0876543219")
    fees_taxes = Decimal("9876.543219") * Decimal("0.9123456789")
    other_result = Decimal("-1234.567891") * Decimal("1.0876543219")
    return ugl_delta + realized + income - fees_taxes + other_result + offset, ugl_delta, realized, income, fees_taxes, other_result


class TestReconciliationFromTheHouse:
    """J-14: each reconciliation component takes its residual from `financial_math.portfolio.period.
    period_identity_residual` and its flag from `is_reconciled`, which replace the expression and the tolerance both
    wrote in line, with no value change. On long-digit figures, where the association of the sum shows, the stated
    residual is the house's and the old inline's to the last digit and exponent, and so is the flag, on either side
    of CONVERSION_DUST."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    @pytest.mark.parametrize(
        ("figures", "residual_text", "reconciled"),
        [
            pytest.param(_closed_by_the_engine(), "6E-23", True, id="closed-by-the-engine"),
            pytest.param(_missing_a_converted_amount(), "11.49262201079109232011977", False, id="a-converted-gap"),
            pytest.param(_off_by(CONVERSION_DUST - Decimal("1E-18")), "9.99999999E-10", True, id="just-under-conversion-dust"),
            pytest.param(_off_by(CONVERSION_DUST), "1.0000000E-9", False, id="at-conversion-dust"),
        ],
    )
    async def test_long_digit_residual_and_flag_are_the_house_s_and_today_s(self, monkeypatch, domain, figures, residual_text, reconciled):
        """The payload states the residual in fixed point (SafeDecimal): the very text of the house's figure, which
        reads back to it with its exponent."""
        summary = _identity_summary(figures)
        assert all(len(figure.as_tuple().digits) >= 20 for figure in figures)
        today = _head_inline_residual(summary)
        assert (str(today), _head_inline_reconciled(today)) == (residual_text, reconciled)

        house = period_math.period_identity_residual(*_identity_figures(summary))
        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        stated = envelope.payload["residual"]["amount"]
        assert str(house) == str(today)
        assert stated == format(house, "f")
        assert str(Decimal(stated)) == str(today)
        assert period_math.is_reconciled(house) is reconciled
        assert envelope.payload["reconciled"] is reconciled

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_the_component_asks_the_house_once_per_build(self, monkeypatch, domain):
        """A structural guard, not a value test: it keeps the identity from being written in line again. Recorders
        that delegate to the real functions replace them in the component's own module; one build calls each exactly
        once, the residual with the summary's six figures in order, the flag with that residual, and the payload states
        what they returned. An inline copy, whatever it computed, would never call them."""
        module = _RECONCILIATION_MODULES[domain]
        real_residual, real_reconciled = period_math.period_identity_residual, period_math.is_reconciled
        residual_calls: list[tuple[dict[str, object], Decimal]] = []
        reconciled_calls: list[tuple[dict[str, object], bool]] = []

        def residual_recorder(*args, **kwargs):
            result = real_residual(*args, **kwargs)
            residual_calls.append((dict(inspect.signature(real_residual).bind(*args, **kwargs).arguments), result))
            return result

        def reconciled_recorder(*args, **kwargs):
            result = real_reconciled(*args, **kwargs)
            reconciled_calls.append((dict(inspect.signature(real_reconciled).bind(*args, **kwargs).arguments), result))
            return result

        monkeypatch.setattr(module, "period_identity_residual", residual_recorder)
        monkeypatch.setattr(module, "is_reconciled", reconciled_recorder)
        summary = _identity_summary(_closed_by_the_engine())

        envelope = await _resolve_reconciliation(monkeypatch, domain, summary)

        assert (len(residual_calls), len(reconciled_calls)) == (1, 1)
        ((residual_arguments, residual),) = residual_calls
        ((reconciled_arguments, reconciled),) = reconciled_calls
        assert {name: str(value) for name, value in residual_arguments.items()} == {name: str(figure) for name, figure in zip(_IDENTITY_ARGUMENTS, _identity_figures(summary), strict=True)}
        assert reconciled_arguments == {"residual": residual} and reconciled_arguments["residual"] is residual
        assert (envelope.payload["residual"]["amount"], envelope.payload["reconciled"]) == (format(residual, "f"), reconciled)
        assert (str(residual), reconciled) == ("6E-23", True)


class TestReconciliationComponentVersion:
    """C-53 made `reconciled` tolerate a residual below CONVERSION_DUST: each reconciliation component moved from
    version 1 to 2, on the real spec and on the frozen catalog placeholder together. The payload shape is unchanged, so
    the schema stays version 1. The catalog is imported in the test, as in `TestFifoComponentVersion`, so that a
    parity failure on import reds these tests only."""

    @pytest.mark.parametrize(
        ("component_id", "components"),
        [
            pytest.param("portfolio.reconciliation", portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS, id="portfolio-reconciliation"),
            pytest.param("broker.reconciliation", broker_financial.BROKER_FINANCIAL_COMPONENTS, id="broker-reconciliation"),
        ],
    )
    def test_reconciliation_component_is_versioned_v2_in_registry_and_placeholder(self, component_id, components):
        from backend.app.services.ai_export.components import catalog  # noqa: PLC0415 — test-local: a real/placeholder parity failure on import must red these tests only

        real = next(spec for spec in components if spec.component_id == component_id)
        placeholder = next(spec for spec in catalog.ALL_FOUNDATION_COMPONENTS if spec.component_id == component_id)
        assert (real.version, placeholder.version) == (2, 2)
        assert real.schema_version == 1


# =============================================================================
# Performance bucket edges + explicit empty buckets
# =============================================================================


class TestPerformanceBuckets:
    @pytest.mark.parametrize(
        ("detail_level", "expected_count"),
        (
            (DetailLevel.COMPACT, 8),
            (DetailLevel.STANDARD, 16),
            (DetailLevel.FULL, 30),
        ),
    )
    @pytest.mark.parametrize(
        ("domain", "component_id", "components"),
        (
            (Domain.PORTFOLIO, "portfolio.performance", portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS),
            (Domain.BROKER, "broker.performance", broker_financial.BROKER_FINANCIAL_COMPONENTS),
        ),
    )
    @pytest.mark.asyncio
    async def test_performance_path_uses_detail_owned_uniform_density(self, monkeypatch, detail_level, expected_count, domain, component_id, components):
        period_start = date(2026, 1, 1)
        period_end = date(2026, 3, 31)
        scope_kwargs = {
            "domain": domain,
            "detail_level": detail_level,
            "period_start": period_start,
            "period_end": period_end,
        }
        if domain is Domain.BROKER:
            scope_kwargs.update({"broker_id": 7, "broker_scope": (7,)})
        scope = _scope(**scope_kwargs)
        history = [
            _history_point(
                period_start + timedelta(days=index),
                nav=1000 + index,
                capital_baseline=1000,
                total_pnl=index,
                twrr=Decimal(index) / Decimal("1000"),
            )
            for index in range((period_end - period_start).days + 1)
        ]
        _patch_report(monkeypatch, _report(scope, summary=_summary(), history=history))
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        context = _make_context(scope, _registry(components), _make_async_session())

        payload = (await context.resolve(component_id, required=True)).payload

        assert payload["path_policy_code"] == "uniform_calendar_path_v1"
        assert payload["path_value_basis"] == "nav_value_including_external_flows"
        assert payload["path_return_basis"] == "historical_twrr"
        assert payload["target_bucket_count"] == expected_count
        assert payload["bucket_count"] == expected_count
        assert payload["buckets"][0]["start_date"] == period_start.isoformat()
        assert payload["buckets"][-1]["end_date"] == period_end.isoformat()
        assert Decimal(payload["buckets"][0]["normalized_index_base_100"]) >= Decimal("100")
        assert Decimal(payload["buckets"][-1]["normalized_index_base_100"]) == Decimal("1089") / Decimal("1000") * Decimal("100")
        assert Decimal(payload["buckets"][-1]["return_from_first_ratio"]) == Decimal("0.089")

    @pytest.mark.asyncio
    async def test_bucket_plan_edges_match_scope_period_and_gaps_are_explicit_empty(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 10))
        # History only covers the first half of the period; the remainder must
        # be reported as explicit has_data=False buckets, never fabricated.
        history = [
            _history_point(date(2026, 1, 1), nav=1000, capital_baseline=1000, total_pnl=0),
            _history_point(date(2026, 1, 2), nav=1010, capital_baseline=1000, total_pnl=10),
            _history_point(date(2026, 1, 3), nav=1020, capital_baseline=1000, total_pnl=20),
        ]
        report = _report(scope, summary=_summary(), history=history)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.performance", required=True)
        buckets = envelope.payload["buckets"]

        assert buckets[0]["start_date"] == "2026-01-01"
        assert buckets[0]["return_percent"] is None
        assert buckets[0]["period_pnl"] is None
        assert buckets[0]["variation_start_date"] is None
        assert buckets[-1]["end_date"] == "2026-01-10"
        empty_buckets = [bucket for bucket in buckets if not bucket["has_data"]]
        assert empty_buckets, "expected at least one explicit empty bucket for the uncovered tail of the period"
        for bucket in empty_buckets:
            assert bucket["start_value"] is None
            assert bucket["end_value"] is None
            assert bucket["return_percent"] is None

    @pytest.mark.parametrize(
        ("domain", "component_id", "components"),
        (
            (
                Domain.PORTFOLIO,
                "portfolio.performance",
                portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS,
            ),
            (
                Domain.BROKER,
                "broker.performance",
                broker_financial.BROKER_FINANCIAL_COMPONENTS,
            ),
        ),
    )
    @pytest.mark.asyncio
    async def test_one_day_bucket_uses_previous_close_and_engine_twrr(
        self,
        monkeypatch,
        domain,
        component_id,
        components,
    ):
        scope_kwargs = {
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 3),
            "domain": domain,
        }
        if domain is Domain.BROKER:
            scope_kwargs.update({"broker_id": 7, "broker_scope": (7,)})
        scope = _scope(**scope_kwargs)
        history = [
            _history_point(
                date(2026, 1, 1),
                nav=1000,
                capital_baseline=1000,
                total_pnl=0,
                twrr=0,
            ),
            _history_point(
                date(2026, 1, 2),
                nav=1110,
                capital_baseline=1100,
                total_pnl=10,
                twrr="0.01",
            ),
            _history_point(
                date(2026, 1, 3),
                nav=1120,
                capital_baseline=1100,
                total_pnl=20,
                twrr="0.02",
            ),
        ]
        report = _report(scope, summary=_summary(), history=history)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(components)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve(component_id, required=True)
        first, second, third = envelope.payload["buckets"]

        assert first["return_percent"] is None
        assert first["period_pnl"] is None
        assert first["net_external_flow"] is None
        assert first["variation_start_date"] is None
        assert Decimal(first["normalized_index_base_100"]) == Decimal("100")
        assert Decimal(first["return_from_first_ratio"]) == Decimal("0")

        assert second["variation_start_date"] == "2026-01-01"
        assert Decimal(second["variation_start_value"]["amount"]) == Decimal("1000")
        assert Decimal(second["net_external_flow"]["amount"]) == Decimal("100")
        assert Decimal(second["period_pnl"]["amount"]) == Decimal("10")
        assert Decimal(second["reconciliation_diff"]["amount"]) == Decimal("0")
        assert Decimal(second["return_percent"]) == Decimal("0.01")
        assert second["min_date"] == second["max_date"] == "2026-01-02"

        assert third["variation_start_date"] == "2026-01-02"
        assert Decimal(third["net_external_flow"]["amount"]) == Decimal("0")
        assert Decimal(third["period_pnl"]["amount"]) == Decimal("10")
        assert Decimal(third["reconciliation_diff"]["amount"]) == Decimal("0")
        assert Decimal(third["return_percent"]) == (Decimal("1.02") / Decimal("1.01") - Decimal(1))
        assert Decimal(third["normalized_index_base_100"]) == Decimal("102")
        assert Decimal(third["return_from_first_ratio"]) == Decimal("0.02")


# =============================================================================
# FIFO bookkeeping helpers
# =============================================================================


class TestFifoBookkeepingHelpers:
    def test_status_residual_cost_and_open_detection(self):
        open_lot = _lot(1, 1)
        partial_lot = _lot(
            1,
            2,
            open_quantity=5,
            realized_quantity=5,
        )
        closed_lot = _lot(
            1,
            3,
            open_quantity=0,
            realized_quantity=10,
            closing_date=date(2026, 1, 5),
        )

        assert shared_payloads.lot_status(open_lot).value == "open"
        assert shared_payloads.lot_status(partial_lot).value == "partial"
        assert shared_payloads.lot_status(closed_lot).value == "closed"
        assert shared_payloads.lot_residual_cost_basis(open_lot) == Decimal("1000")
        assert shared_payloads.lot_residual_cost_basis(partial_lot) == Decimal("500")
        assert shared_payloads.lot_residual_cost_basis(closed_lot) == Decimal("0")
        assert shared_payloads.has_nonzero_open_lot([closed_lot, partial_lot]) is True
        assert shared_payloads.has_nonzero_open_lot([closed_lot]) is False

    def test_residual_cost_handles_zero_original_quantity(self):
        lot = SimpleNamespace(
            open_quantity=Decimal("1"),
            original_quantity=Decimal("0"),
            original_cost=Decimal("100"),
        )
        assert shared_payloads.lot_residual_cost_basis(lot) == Decimal("0")

    def test_eligibility_keeps_open_and_in_period_closed_lots(self):
        cutoff = date(2026, 1, 1)
        open_lot = _lot(1, 1)
        before = _lot(
            1,
            2,
            open_quantity=0,
            realized_quantity=10,
            closing_date=date(2025, 12, 31),
        )
        boundary = _lot(
            1,
            3,
            open_quantity=0,
            realized_quantity=10,
            closing_date=cutoff,
        )

        assert shared_payloads.lot_is_eligible(open_lot, cutoff=cutoff) is True
        assert shared_payloads.lot_is_eligible(before, cutoff=cutoff) is False
        assert shared_payloads.lot_is_eligible(boundary, cutoff=cutoff) is True

    @pytest.mark.asyncio
    async def test_transaction_asset_loader_is_bulk_scoped_and_deduplicated(self):
        session = AsyncMock(spec=AsyncSession)
        result = MagicMock()
        result.scalars.return_value.all.return_value = [9, 3, 9, None]
        session.execute.return_value = result

        asset_ids = await shared_payloads.default_transaction_asset_ids_loader(
            session,
            (5, 2, 5),
            date(2026, 1, 31),
        )

        assert asset_ids == {3, 9}
        session.execute.assert_awaited_once()
        statement = session.execute.await_args.args[0]
        params = statement.compile().params
        assert [2, 5] in params.values()
        assert date(2026, 1, 31) in params.values()

    @pytest.mark.asyncio
    async def test_transaction_asset_loader_skips_empty_scope(self):
        session = AsyncMock(spec=AsyncSession)
        assert (
            await shared_payloads.default_transaction_asset_ids_loader(
                session,
                (),
                date(2026, 1, 31),
            )
            == set()
        )
        session.execute.assert_not_awaited()


# =============================================================================
# FIFO: period cutoff, open lots always included, no lot_id, no limit
# =============================================================================


class TestFifoLots:
    @pytest.mark.asyncio
    async def test_closed_lot_before_period_start_excluded_on_or_after_included(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), broker_scope=(1,))
        excluded = _lot(1, 101, closing_date=date(2025, 12, 31), open_quantity=0, realized_quantity=10)
        included_on_boundary = _lot(1, 102, closing_date=date(2026, 1, 1), open_quantity=0, realized_quantity=10)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [excluded, included_on_boundary])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)
        lots = envelope.payload["lots"]

        assert len(lots) == 1
        assert lots[0]["closing_date"] == "2026-01-01"

    @pytest.mark.asyncio
    async def test_open_and_partial_lots_always_included_regardless_of_opening_date(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), broker_scope=(1,))
        ancient_open = _lot(1, 201, opening_date=date(2010, 1, 1), open_quantity=10, realized_quantity=0)
        ancient_partial = _lot(1, 202, opening_date=date(2011, 1, 1), open_quantity=5, realized_quantity=5)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [ancient_open, ancient_partial])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)
        lots = envelope.payload["lots"]

        assert len(lots) == 2
        statuses = {lot["status"] for lot in lots}
        assert statuses == {"OPEN", "PARTIAL"}

    @pytest.mark.asyncio
    async def test_lot_id_never_serialized(self, monkeypatch):
        scope = _scope(broker_scope=(1,))
        lot = _lot(1, 301, open_quantity=10, realized_quantity=0)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [lot])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)

        public_lot = envelope.payload["lots"][0]
        assert "lot_id" not in public_lot
        assert public_lot["lot_ref"] == "L1"
        assert "opening_broker_name" not in public_lot

    @pytest.mark.asyncio
    async def test_distinct_economically_identical_lots_keep_distinct_local_refs_and_custody(self, monkeypatch):
        scope = _scope(broker_scope=(1,))
        custody = [
            LotCustodySummarySchema(
                broker_id=1,
                custody_type="BROKER",
                quantity=Decimal("8"),
            ),
            LotCustodySummarySchema(
                broker_id=None,
                custody_type="IN_TRANSIT",
                quantity=Decimal("2"),
            ),
        ]
        lot_a = _lot(1, 311, current_custody=custody)
        lot_b = _lot(1, 312, current_custody=custody)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [lot_b, lot_a])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)
        lots = envelope.payload["lots"]

        assert [lot["lot_ref"] for lot in lots] == ["L1", "L2"]
        assert lots[0]["current_custody"] == [
            {"broker_id": 1, "custody_type": "BROKER", "quantity": "8"},
            {"broker_id": None, "custody_type": "IN_TRANSIT", "quantity": "2"},
        ]
        assert {key: value for key, value in lots[0].items() if key != "lot_ref"} == {key: value for key, value in lots[1].items() if key != "lot_ref"}

    def test_duplicate_internal_lot_ids_fail_before_local_ref_assignment(self):
        duplicate = _lot(1, 321)

        with pytest.raises(ValueError, match="must be unique"):
            shared_payloads.build_fifo_lot_refs(
                {
                    1: [duplicate],
                    2: [duplicate.model_copy(update={"asset_id": 2})],
                }
            )

    @pytest.mark.asyncio
    async def test_no_top_n_limit_all_open_lots_retained(self, monkeypatch):
        scope = _scope(broker_scope=(1,))
        lots = [_lot(1, 400 + i, opening_date=date(2020, 1, 1) + timedelta(days=i), open_quantity=1, realized_quantity=0) for i in range(25)]
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, lots)})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)

        assert envelope.payload["lot_count"] == 25
        assert len(envelope.payload["lots"]) == 25

    @pytest.mark.asyncio
    async def test_deterministic_lot_order_independent_of_input_order(self, monkeypatch):
        scope = _scope(broker_scope=(1,))
        lot_a = _lot(2, 501, opening_date=date(2024, 1, 1), open_quantity=1, realized_quantity=0)
        lot_b = _lot(1, 502, opening_date=date(2024, 6, 1), open_quantity=1, realized_quantity=0)
        lot_c = _lot(1, 503, opening_date=date(2024, 1, 1), open_quantity=1, realized_quantity=0)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [lot_b, lot_c]), 2: _lots_response(2, [lot_a])})
        _patch_metadata(monkeypatch, asset_ids=[1, 2], broker_ids=[1])
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        first_run = await context.resolve("portfolio.fifo_lots", required=True)

        # Rebuild with the lots supplied in a different order: the output order
        # must be identical (asset_id, opening_date, lot_id), never input-order dependent.
        registry2 = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context2 = _make_context(scope, registry2, _make_async_session())
        _patch_lots(monkeypatch, {1: _lots_response(1, [lot_c, lot_b]), 2: _lots_response(2, [lot_a])})
        second_run = await context2.resolve("portfolio.fifo_lots", required=True)

        assert first_run.payload["lots"] == second_run.payload["lots"]
        asset_ids_in_order = [lot["asset_id"] for lot in first_run.payload["lots"]]
        assert asset_ids_in_order == sorted(asset_ids_in_order)
        assert [lot["lot_ref"] for lot in first_run.payload["lots"]] == ["L1", "L2", "L3"]


# =============================================================================
# FIFO: a figure without a rate is null, never zero (B3b)
# =============================================================================

_FIFO_SCOPES = {
    "portfolio": ({"broker_scope": (5,)}, portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS),
    "broker": ({"domain": Domain.BROKER, "broker_id": 5, "broker_scope": (5,)}, broker_financial.BROKER_FINANCIAL_COMPONENTS),
}


class TestUnvaluedFifoFigures:
    """B3b: a lot figure the lots analysis could not value in the target currency (a missing FX rate) is None.

    The FIFO rows and summaries export it as null -- unavailable -- and a total with an unknown part is unknown:
    never a 0, nor a partial sum, that would read as recorded.
    """

    def test_residual_cost_basis_is_unknown_while_the_lot_is_open_and_its_cost_is(self):
        """An open or partial lot's residual cost is a share of its original cost, so it is unknown with it. A closed
        lot has nothing left open: its residual is 0 whatever its cost."""
        open_lot = _unvalued_lot(1, 1)
        partial_lot = _unvalued_lot(1, 2, open_quantity=5, realized_quantity=5)
        closed_lot = _unvalued_lot(1, 3, open_quantity=0, realized_quantity=10, closing_date=date(2026, 1, 5))

        assert [shared_payloads.lot_residual_cost_basis(lot) for lot in (open_lot, partial_lot, closed_lot)] == [None, None, Decimal("0")]

    def test_residual_cost_with_zero_original_quantity_is_unknown_when_its_cost_is(self):
        """The cost is read before the zero original quantity: an open lot with an unknown cost has an unknown residual,
        whatever its quantities. The 0 of `test_residual_cost_handles_zero_original_quantity` needs a known cost."""
        lot = SimpleNamespace(open_quantity=Decimal("1"), original_quantity=Decimal("0"), original_cost=None)

        assert shared_payloads.lot_residual_cost_basis(lot) is None

    @pytest.mark.parametrize(
        ("open_quantity", "realized_quantity", "closing_date", "status", "residual_cost_basis"),
        [
            pytest.param(10, 0, None, "OPEN", None, id="open"),
            pytest.param(5, 5, None, "PARTIAL", None, id="partial"),
            pytest.param(0, 10, date(2026, 1, 5), "CLOSED", Decimal("0"), id="closed"),
        ],
    )
    def test_unvalued_lot_maps_to_a_row_with_null_figures_never_zero(self, open_quantity, realized_quantity, closing_date, status, residual_cost_basis):
        lot = _unvalued_lot(1, 1, open_quantity=open_quantity, realized_quantity=realized_quantity, closing_date=closing_date)

        row = shared_payloads.map_fifo_lot_row(lot, lot_ref="L1", asset_id=1, currency_code=CURRENCY, asset_name="Asset 1", asset_ticker="A1")

        assert (row.status, row.open_quantity, row.net_metrics_status) == (status, Decimal(str(open_quantity)), "UNAVAILABLE")
        assert {name: getattr(row, name) for name in _UNVALUED_ROW_FIELDS} == dict.fromkeys(_UNVALUED_ROW_FIELDS)
        assert row.residual_cost_basis == (_money(residual_cost_basis) if residual_cost_basis is not None else None)

    def test_lot_with_only_its_fees_unknown_keeps_every_other_figure(self):
        """The lot a FEE pool split by trades in mixed currencies reaches: only its fees are unknown."""
        valued = _lot(1, 1, open_quantity=5, realized_quantity=5, realized_pnl=100, cumulative_proceeds=600, asset_income=20, allocated_taxes=5)
        lot = LotSummarySchema.model_validate({**valued.model_dump(), "allocated_fees": None, "net_metrics_status": "UNAVAILABLE"})

        row = shared_payloads.map_fifo_lot_row(lot, lot_ref="L1", asset_id=1, currency_code=CURRENCY, asset_name="Asset 1", asset_ticker="A1")

        assert row.fees is None
        known = ("opening_unit_price", "original_cost", "residual_cost_basis", "cumulative_proceeds", "realized_pnl", "income", "taxes")
        assert {name: getattr(row, name) for name in known} == {
            "opening_unit_price": _money(100),
            "original_cost": _money(1000),
            "residual_cost_basis": _money(500),
            "cumulative_proceeds": _money(600),
            "realized_pnl": _money(100),
            "income": _money(20),
            "taxes": _money(5),
        }

    def test_summary_sums_known_lot_figures_as_before(self):
        """Control: with every part known, each total is the plain sum."""
        summary = shared_payloads.summarize_fifo_asset_rows([_fifo_row("L1"), _fifo_row("L2")])

        assert {name: getattr(summary, name) for name in _SUMMED_MONEY_FIELDS} == {name: _money(total) for name, total in _TWO_ROW_TOTALS.items()}

    @pytest.mark.parametrize("unknown_field", _SUMMED_MONEY_FIELDS)
    def test_summary_total_is_unknown_when_one_lot_part_is(self, unknown_field):
        """Summing the known parts would present a partial figure as the asset's: the total is unknown. The other
        totals keep their sums."""
        rows = [_fifo_row("L1"), _fifo_row("L2", **{unknown_field: None})]

        summary = shared_payloads.summarize_fifo_asset_rows(rows)

        assert getattr(summary, unknown_field) is None
        known = {name: _money(total) for name, total in _TWO_ROW_TOTALS.items() if name != unknown_field}
        assert {name: getattr(summary, name) for name in known} == known

    def test_summary_of_rows_without_any_valued_figure_does_not_raise(self):
        """The one-currency check reads the known figures only: rows whose money figures are all unknown have no
        currency to disagree on, and summarize to unknown totals with their quantities still counted."""
        no_money = dict.fromkeys(_NULLABLE_ROW_FIELDS)
        rows = [_fifo_row("L1", **no_money), _fifo_row("L2", **no_money)]

        summary = shared_payloads.summarize_fifo_asset_rows(rows)

        assert (summary.partial_lot_count, summary.original_quantity, summary.open_quantity) == (2, Decimal("20"), Decimal("10"))
        assert {name: getattr(summary, name) for name in _SUMMED_MONEY_FIELDS} == dict.fromkeys(_SUMMED_MONEY_FIELDS)

    @pytest.mark.parametrize("unrealized_pnl", [None, Decimal("200")], ids=["market-value-only", "with-unrealized-pnl"])
    def test_summary_takes_its_currency_from_a_market_value_when_every_nullable_amount_is_unknown(self, unrealized_pnl):
        """A lot can have all eight nullable amounts unknown (no rate at its opening nor at its closures) and still a
        market value, priced at today's rate. The summary's currency is read from every known amount: its market totals
        keep that currency -- EUR here, appearing nowhere else -- and nothing raises. The summed totals stay unknown.

        MF-E1 (T-B8): the market totals sum the lots valued in full, open value and unrealized P&L both known. A lot with
        its market value alone is not one of them, so its 700 is no longer summed: the open value is unknown with its
        P&L. Before MF-E1: ``open_value`` was EUR 700 in the market-value-only case too."""
        unknown = dict.fromkeys(_NULLABLE_ROW_FIELDS)

        def eur(amount: object) -> Currency:
            return Currency(code="EUR", amount=Decimal(str(amount)))

        priced = _fifo_row("L1", **unknown, open_value=eur(700), unrealized_pnl=eur(unrealized_pnl) if unrealized_pnl is not None else None)
        unpriced = _fifo_row("L2", **unknown)

        summary = shared_payloads.summarize_fifo_asset_rows([priced, unpriced])

        expected_market = (eur(700), eur(200), eur(200), eur(0)) if unrealized_pnl is not None else (None, None, None, None)
        assert (summary.open_value, summary.unrealized_pnl, summary.potential_gain, summary.potential_loss) == expected_market
        assert {name: getattr(summary, name) for name in _SUMMED_MONEY_FIELDS} == dict.fromkeys(_SUMMED_MONEY_FIELDS)

    def test_summary_still_rejects_known_figures_in_two_currencies(self):
        """Skipping the unknown figures must not skip the known ones: two currencies among them still fail."""
        rows = [_fifo_row("L1"), _fifo_row("L2", original_cost=None, residual_cost_basis=None, fees=Currency(code="EUR", amount=Decimal("10")))]

        with pytest.raises(ValueError, match="one target currency"):
            shared_payloads.summarize_fifo_asset_rows(rows)

    def test_summary_market_value_totals_keep_summing_the_valued_open_lots(self):
        """Unchanged by B3b: open value, unrealized P&L and potential gain/loss sum the open lots that have a market
        value, and say how many those are -- `value_coverage_status`, valued and unavailable counts."""
        priced = _fifo_row("L1", **_MARKET_FIGURES)
        unpriced = _fifo_row("L2")  # open as well, but without a market price

        summary = shared_payloads.summarize_fifo_asset_rows([priced, unpriced])

        market = ("open_value", "unrealized_pnl", "potential_gain", "potential_loss")
        assert {name: getattr(summary, name) for name in market} == {"open_value": _money(700), "unrealized_pnl": _money(200), "potential_gain": _money(200), "potential_loss": _money(0)}
        assert (summary.valued_open_lot_count, summary.unavailable_open_lot_count, summary.value_coverage_status) == (1, 1, "partial")

    @pytest.mark.parametrize(
        "half_valued",
        [
            # The case the lots analysis produces: a market price, but a P&L it could not form (a proceeds rate missing).
            pytest.param({"open_value": _money(300), "unrealized_pnl": None}, id="value-known-pnl-unknown"),
            # Its mirror, which the row model admits: the same rule holds the other way round.
            pytest.param({"open_value": None, "unrealized_pnl": _money(50)}, id="pnl-known-value-unknown"),
        ],
    )
    def test_summary_market_totals_sum_the_same_lots_the_coverage_counts(self, half_valued):
        """MF-E1 (T-B8): open value and unrealized P&L sum the same open lots -- those with both known, the
        `valued_open_rows` that `valued_open_lot_count` counts. Three open lots: both known, one of the two known,
        neither: each total is the first lot's alone, and the coverage it states is one valued lot of three.

        Before MF-E1 each total summed the lots where it alone was known: open value 1000 (700 + 300) beside an
        unrealized P&L of 200 -- two figures over two different sets of lots, and a coverage that matched neither
        (mirror: unrealized P&L 250 beside an open value of 700)."""
        rows = [_fifo_row("L1", **_MARKET_FIGURES), _fifo_row("L2", **half_valued), _fifo_row("L3")]
        assert all(row.open_quantity != 0 for row in rows), "precondition: the three lots are open"

        summary = shared_payloads.summarize_fifo_asset_rows(rows)

        market = ("open_value", "unrealized_pnl", "potential_gain", "potential_loss")
        assert {name: getattr(summary, name) for name in market} == {"open_value": _money(700), "unrealized_pnl": _money(200), "potential_gain": _money(200), "potential_loss": _money(0)}
        # Unchanged: the coverage counts already read the lots with both figures known.
        assert (summary.valued_open_lot_count, summary.unavailable_open_lot_count, summary.value_coverage_status) == (1, 2, "partial")

    @pytest.mark.parametrize(
        ("second_lot", "expected"),
        [
            # no market price: neither its total nor its net P&L is known
            pytest.param({}, {"total_pnl": None, "net_total_pnl": None}, id="unpriced"),
            # priced, but its fees unknown (a FEE pool without a rate): its total is known, its net is not
            pytest.param({**_MARKET_FIGURES, "net_total_pnl": None}, {"total_pnl": _money(600), "net_total_pnl": None}, id="net-unknown"),
        ],
    )
    def test_summary_total_and_net_pnl_are_unknown_when_one_lot_part_is(self, second_lot, expected):
        """B3b: total and net P&L follow the rule of the cost sums. With no coverage field of their own, summing the
        lots that have them would present a part as the asset's figure: one unknown part makes the total unknown."""
        rows = [_fifo_row("L1", **_MARKET_FIGURES), _fifo_row("L2", **second_lot)]

        summary = shared_payloads.summarize_fifo_asset_rows(rows)

        assert {name: getattr(summary, name) for name in expected} == expected

    def test_summary_total_and_net_pnl_sum_when_every_lot_has_them(self):
        """Control: every lot's total and net P&L known, the summary's are their plain sums, as before."""
        summary = shared_payloads.summarize_fifo_asset_rows([_fifo_row("L1", **_MARKET_FIGURES), _fifo_row("L2", **_MARKET_FIGURES)])

        assert (summary.total_pnl, summary.net_total_pnl) == (_money(600), _money(570))

    def test_total_residual_cost_basis_is_unknown_when_one_asset_residual_is(self):
        """`total_fifo_residual_cost_basis`, the portfolio and broker FIFO summaries' total: the sum of the assets'
        residual cost, unknown when one of them is; 0 with no asset."""
        total_fifo_residual_cost_basis = _total_fifo_residual_cost_basis()
        known_a = shared_payloads.summarize_fifo_asset_rows([_fifo_row("L1")])
        known_b = shared_payloads.summarize_fifo_asset_rows([_fifo_row("L2", asset_id=2, asset_name="Asset 2")])
        unknown = shared_payloads.summarize_fifo_asset_rows([_fifo_row("L3", asset_id=3, asset_name="Asset 3", original_cost=None, residual_cost_basis=None)])

        assert total_fifo_residual_cost_basis([], CURRENCY) == _money(0)
        assert total_fifo_residual_cost_basis([known_a, known_b], CURRENCY) == _money(1000)
        assert total_fifo_residual_cost_basis([known_a, unknown], CURRENCY) is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_fifo_summary_leaves_unknown_what_an_unvalued_lot_leaves_unknown(self, monkeypatch, domain):
        """Builder level: an asset whose only lot is unvalued has its summed figures null, and so has the payload's
        total residual cost basis, which includes it. The valued asset keeps its figures."""
        scope_overrides, components = _FIFO_SCOPES[domain]
        scope = _scope(**scope_overrides)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [_lot(1, 801, opening_broker_id=5)]), 2: _lots_response(2, [_unvalued_lot(2, 802, opening_broker_id=5)])})
        _patch_metadata(monkeypatch, asset_ids=[1, 2], broker_ids=[5])
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(f"{domain}.fifo_summary", required=True)

        assets = {row["asset_id"]: row for row in envelope.payload["assets"]}
        assert set(assets) == {1, 2}
        assert {name: Decimal(assets[1][name]["amount"]) for name in ("original_cost", "residual_cost_basis")} == {"original_cost": Decimal("1000"), "residual_cost_basis": Decimal("1000")}
        assert {name: assets[2][name] for name in _SUMMED_MONEY_FIELDS} == dict.fromkeys(_SUMMED_MONEY_FIELDS)
        assert envelope.payload["total_residual_cost_basis"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_fifo_lots_export_an_unvalued_lot_with_null_figures(self, monkeypatch, domain):
        """Builder level: the unvalued lot is still exported, with its quantities and UNAVAILABLE net metrics, and every
        figure it could not value null."""
        scope_overrides, components = _FIFO_SCOPES[domain]
        scope = _scope(**scope_overrides)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [_unvalued_lot(1, 811, opening_broker_id=5)])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[5])
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(f"{domain}.fifo_lots", required=True)

        (row,) = envelope.payload["lots"]
        assert (row["lot_ref"], row["status"], row["open_quantity"], row["net_metrics_status"]) == ("L1", "OPEN", "10", "UNAVAILABLE")
        null_fields = ("residual_cost_basis", *_UNVALUED_ROW_FIELDS)
        assert {name: row[name] for name in null_fields} == dict.fromkeys(null_fields)


class TestUnavailableAmountLotCount:
    """`unavailable_amount_lot_count` of `portfolio.fifo_lots` / `broker.fifo_lots` (B3b): how many of the payload's
    lots have at least one of the eight amounts B3b made nullable unknown. The amounts optional before B3b (open value,
    unrealized, total and net P&L) are unknown for other reasons, such as no market price, and their coverage is stated
    elsewhere: they do not count. A required count, never a default 0.

    Counted by `payloads.portfolio_broker.count_unavailable_amount_lots`, looked up when called so that, until it
    exists, only the tests using it fail."""

    def test_helper_is_public(self):
        _count_unavailable_amount_lots()

        assert "count_unavailable_amount_lots" in shared_payloads.__all__

    def test_lots_with_every_amount_known_count_zero(self):
        count_unavailable_amount_lots = _count_unavailable_amount_lots()

        assert count_unavailable_amount_lots([_fifo_row("L1", **_MARKET_FIGURES), _fifo_row("L2", **_MARKET_FIGURES)]) == 0

    @pytest.mark.parametrize("unknown_field", _NULLABLE_ROW_FIELDS)
    def test_a_lot_with_one_unknown_amount_counts_once(self, unknown_field):
        count_unavailable_amount_lots = _count_unavailable_amount_lots()
        rows = [_fifo_row("L1", **_MARKET_FIGURES), _fifo_row("L2", **_MARKET_FIGURES, **{unknown_field: None}), _fifo_row("L3", **_MARKET_FIGURES)]

        assert count_unavailable_amount_lots(rows) == 1

    def test_a_lot_with_several_unknown_amounts_counts_once(self):
        count_unavailable_amount_lots = _count_unavailable_amount_lots()
        rows = [_fifo_row("L1", **_MARKET_FIGURES, **dict.fromkeys(_NULLABLE_ROW_FIELDS)), _fifo_row("L2", **_MARKET_FIGURES)]

        assert count_unavailable_amount_lots(rows) == 1

    @pytest.mark.parametrize(
        "unknown_fields",
        [("open_value",), ("unrealized_pnl",), ("total_pnl",), ("net_total_pnl",), tuple(_MARKET_FIGURES)],
        ids=["open_value", "unrealized_pnl", "total_pnl", "net_total_pnl", "no-market-price"],
    )
    def test_a_lot_missing_only_amounts_optional_before_b3b_does_not_count(self, unknown_fields):
        count_unavailable_amount_lots = _count_unavailable_amount_lots()
        row = _fifo_row("L1", **{**_MARKET_FIGURES, **dict.fromkeys(unknown_fields)})

        assert count_unavailable_amount_lots([row]) == 0

    def test_no_lots_count_zero(self):
        count_unavailable_amount_lots = _count_unavailable_amount_lots()

        assert count_unavailable_amount_lots([]) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    @pytest.mark.parametrize(
        ("case", "exported", "expected"),
        [
            pytest.param("all-valued", 2, 0, id="all-valued"),
            pytest.param("two-with-an-unknown-amount", 3, 2, id="two-with-an-unknown-amount"),
            pytest.param("unknown-but-not-exported", 1, 0, id="unknown-but-not-exported"),
        ],
    )
    async def test_fifo_lots_count_the_exported_lots_with_an_unknown_amount(self, monkeypatch, domain, case, exported, expected):
        """Builder level. The valued lots have no market price: their open value and P&L are None, which does not count.
        A lot closed before the period is not in `lots`, so it does not count however unvalued."""
        scope_overrides, components = _FIFO_SCOPES[domain]
        scope = _scope(**scope_overrides)
        valued = _lot(1, 821, opening_broker_id=5)
        fees_unknown = LotSummarySchema.model_validate({**_lot(1, 823, opening_broker_id=5).model_dump(), "allocated_fees": None, "net_metrics_status": "UNAVAILABLE"})
        lots = {
            "all-valued": [valued, _lot(1, 822, opening_broker_id=5, open_quantity=5, realized_quantity=5)],
            "two-with-an-unknown-amount": [valued, _unvalued_lot(1, 822, opening_broker_id=5), fees_unknown],
            "unknown-but-not-exported": [valued, _unvalued_lot(1, 824, opening_broker_id=5, open_quantity=0, realized_quantity=10, closing_date=date(2025, 12, 31))],
        }[case]
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, lots)})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[5])
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(f"{domain}.fifo_lots", required=True)

        assert envelope.payload["lot_count"] == exported
        assert envelope.payload.get("unavailable_amount_lot_count") == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["portfolio", "broker"])
    async def test_fifo_lots_count_is_required_and_never_negative(self, monkeypatch, domain):
        """A stated count, never a default: the builder's own payload validates, the same payload without the count or
        with a negative one does not."""
        scope_overrides, components = _FIFO_SCOPES[domain]
        payload_model = {"portfolio": portfolio_financial.PortfolioFifoLotsPayload, "broker": broker_financial.BrokerFifoLotsPayload}[domain]
        scope = _scope(**scope_overrides)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [_lot(1, 831, opening_broker_id=5)])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[5])
        context = _make_context(scope, _registry(components), _make_async_session())
        payload = (await context.resolve(f"{domain}.fifo_lots", required=True)).payload

        payload_model.model_validate(payload)
        with pytest.raises(ValidationError):
            payload_model.model_validate({name: value for name, value in payload.items() if name != "unavailable_amount_lot_count"})
        with pytest.raises(ValidationError):
            payload_model.model_validate({**payload, "unavailable_amount_lot_count": -1})


class TestFifoComponentVersion:
    """B3b made the FIFO lot and summary money figures nullable (null = unavailable): each FIFO component moved from
    version 1 to 2, on the real spec and on the frozen catalog placeholder together. MF-E1 (T-B8) moves the two FIFO
    summaries on to 3 -- an asset's open value and unrealized P&L sum the same lots, those valued in full -- with the
    same payload shape. J-12 (N81) declares an asset whose lot reconstruction FAILED (`failed_reconstruction_asset_count`,
    `failed_lot_reconstructions`) instead of exporting its wrong lots: the FIFO lots move 2 -> 3, the summaries stay at 3
    (already moved in this cycle; at most +1 over the released v1.2.1). The catalog is imported in the test rather than
    at module level, so a parity failure on import reds these tests only."""

    @pytest.mark.parametrize(
        ("component_id", "components", "version"),
        [
            # Before MF-E1: 2.
            pytest.param("portfolio.fifo_summary", portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS, 3, id="portfolio-fifo-summary"),
            # Before J-12: 2.
            pytest.param("portfolio.fifo_lots", portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS, 3, id="portfolio-fifo-lots"),
            # Before MF-E1: 2.
            pytest.param("broker.fifo_summary", broker_financial.BROKER_FINANCIAL_COMPONENTS, 3, id="broker-fifo-summary"),
            # Before J-12: 2.
            pytest.param("broker.fifo_lots", broker_financial.BROKER_FINANCIAL_COMPONENTS, 3, id="broker-fifo-lots"),
        ],
    )
    def test_fifo_component_version_in_registry_and_placeholder(self, component_id, components, version):
        from backend.app.services.ai_export.components import catalog  # noqa: PLC0415 — test-local: a real/placeholder parity failure on import must red these tests only

        real = next(spec for spec in components if spec.component_id == component_id)
        placeholder = next(spec for spec in catalog.ALL_FOUNDATION_COMPONENTS if spec.component_id == component_id)
        assert (real.version, placeholder.version, real.schema_version) == (version, version, 1)


# =============================================================================
# Broker scope correctness
# =============================================================================


class TestBrokerScope:
    @pytest.mark.asyncio
    async def test_broker_positions_report_query_uses_single_broker_scope(self, monkeypatch):
        scope = _scope(domain=Domain.BROKER, broker_id=9, broker_scope=(9,))
        captured_queries = []

        async def _fake_get_report(self, user_id, query):  # noqa: ARG001
            captured_queries.append(query)
            return _report(scope, summary=_summary(holdings=[_holding(1, 9)]))

        monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(broker_financial.BROKER_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("broker.positions", required=True)

        assert captured_queries[0].broker_ids == [9]
        assert envelope.payload["broker_id"] == 9

    @pytest.mark.asyncio
    async def test_broker_fifo_lots_scoped_to_single_broker(self, monkeypatch):
        scope = _scope(domain=Domain.BROKER, broker_id=5, broker_scope=(5,))
        lot = _lot(1, 601, opening_broker_id=5, open_quantity=10, realized_quantity=0)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, [lot])})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[5])
        registry = _registry(broker_financial.BROKER_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("broker.fifo_lots", required=True)

        assert envelope.payload["broker_id"] == 5
        assert all(row["opening_broker_id"] == 5 for row in envelope.payload["lots"])

    @pytest.mark.asyncio
    async def test_broker_fifo_summary_is_compact_and_economic(self, monkeypatch):
        scope = _scope(domain=Domain.BROKER, broker_id=5, broker_scope=(5,))
        lots = [
            _lot(1, 611, opening_broker_id=5, open_quantity=10, open_value=1250, market_pnl=250, total_pnl=250, net_total_pnl=235, allocated_fees=10, allocated_taxes=5),
            _lot(1, 612, opening_broker_id=5, closing_date=date(2026, 1, 5), open_quantity=0, realized_quantity=10, realized_pnl=75, total_pnl=75, net_total_pnl=70, allocated_fees=5),
        ]
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {1: _lots_response(1, lots)})
        _patch_metadata(monkeypatch, asset_ids=[1], broker_ids=[5])
        registry = _registry(broker_financial.BROKER_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("broker.fifo_summary", required=True)
        row = envelope.payload["assets"][0]

        assert envelope.payload["broker_id"] == 5
        assert envelope.payload["asset_count"] == 1
        assert envelope.payload["cost_allocation_semantics"].startswith("Fees and taxes are amounts deterministically allocated")
        assert "lots" not in envelope.payload
        assert row["open_lot_count"] == 1
        assert row["closed_lot_count"] == 1
        assert Decimal(row["unrealized_pnl"]["amount"]) == Decimal("250")
        assert Decimal(row["realized_pnl"]["amount"]) == Decimal("75")
        assert Decimal(row["fees"]["amount"]) == Decimal("15")


# =============================================================================
# Provenance component version (D12(a), issue #32)
# =============================================================================


class TestProvenanceComponentVersion:
    """What the Snapshot Data renderer reads off each section: the provenance envelopes say
    component_version 3, schema_version 1 (the payload shape is unchanged). Version 2 (D12(a)): the
    WAC semantics moved to the single average cost; version 3 (J-17): the valuation hierarchy names
    ESTIMATED_AT_COST and an ADJUSTMENT is never a price. No prompt wording is asserted."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("component_id", "scope_overrides", "components"),
        [
            pytest.param("portfolio.provenance", {}, portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS, id="portfolio"),
            pytest.param("broker.provenance", {"domain": Domain.BROKER, "broker_id": 5, "broker_scope": (5,)}, broker_financial.BROKER_FINANCIAL_COMPONENTS, id="broker"),
        ],
    )
    async def test_provenance_envelope_is_component_version_3_schema_version_1(self, monkeypatch, component_id, scope_overrides, components):
        """Before J-17: component_version 2."""
        scope = _scope(**scope_overrides)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(component_id, required=True)

        assert (envelope.component_id, envelope.component_version, envelope.schema_version) == (component_id, 3, 1)
        assert envelope.payload["domain"] == component_id.split(".")[0]


# =============================================================================
# J-17 — a holding valued at cost has no unit_price (portfolio.positions / broker.positions v2)
# =============================================================================


_POSITIONS_COMPONENTS = [
    pytest.param("portfolio.positions", {}, portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS, id="portfolio"),
    pytest.param("broker.positions", {"domain": Domain.BROKER, "broker_id": 5, "broker_scope": (5,)}, broker_financial.BROKER_FINANCIAL_COMPONENTS, id="broker"),
]


class TestValuedAtCostPositions:
    """J-17 (developer's option A, 16/10): a holding with no price at all is valued at its book cost,
    ``valuation_source == "ESTIMATED_AT_COST"``, with no price. Its value per unit would be its unit cost,
    not a price, so its position row exports no ``unit_price``; the rows priced at the market or at a trade
    keep theirs (value / quantity). Both positions components move to version 2 with the same payload
    shape (schema_version 1): what the Snapshot Data renderer reads off each section. No prompt wording is
    asserted; rows are read by asset."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("component_id", "scope_overrides", "components"), _POSITIONS_COMPONENTS)
    async def test_an_at_cost_row_has_no_unit_price(self, monkeypatch, component_id, scope_overrides, components):
        """Before J-17: ValidationError — PortfolioHolding.valuation_source accepted MARKET_PRICE,
        LAST_TRADE_PRICE and MISSING only. (J-17's first version exported the at-cost row's unit cost,
        300 / 4 = 75, as its unit_price.)"""
        scope = _scope(**scope_overrides)
        holdings = [
            _holding(1, 5, quantity=10, current_value=1000, valuation_source="MARKET_PRICE"),
            _holding(2, 5, quantity=4, current_value=300, valuation_source="ESTIMATED_AT_COST"),
            _holding(3, 5, quantity=5, current_value=450, valuation_source="LAST_TRADE_PRICE"),
        ]
        _patch_report(monkeypatch, _report(scope, summary=_summary(holdings=holdings)))
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(component_id, required=True)

        rows = {row["asset_id"]: row for row in envelope.payload["positions"]}
        assert {asset_id: (row["valuation_source"], row["unit_price"]) for asset_id, row in rows.items()} == {
            1: ("MARKET_PRICE", {"code": CURRENCY, "amount": "100"}),
            2: ("ESTIMATED_AT_COST", None),
            3: ("LAST_TRADE_PRICE", {"code": CURRENCY, "amount": "90"}),
        }
        assert rows[2]["current_value"] == {"code": CURRENCY, "amount": "300"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("component_id", "scope_overrides", "components"), _POSITIONS_COMPONENTS)
    async def test_positions_envelope_is_component_version_2_schema_version_1(self, monkeypatch, component_id, scope_overrides, components):
        """Before J-17: component_version 1."""
        scope = _scope(**scope_overrides)
        _patch_report(monkeypatch, _report(scope))
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        context = _make_context(scope, _registry(components), _make_async_session())

        envelope = await context.resolve(component_id, required=True)

        assert (envelope.component_id, envelope.component_version, envelope.schema_version) == (component_id, 2, 1)


# =============================================================================
# Source failure propagation (no broad-success fallback)
# =============================================================================


class TestSourceFailurePropagation:
    @pytest.mark.asyncio
    async def test_get_report_exception_propagates_as_required_component_build_error(self, monkeypatch):
        scope = _scope()

        async def _boom(self, user_id, query):  # noqa: ARG001
            raise RuntimeError("engine unavailable")

        monkeypatch.setattr(PortfolioService, "get_report", _boom)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("portfolio.summary", required=True)
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_get_lots_analysis_exception_propagates(self, monkeypatch):
        scope = _scope(broker_scope=(1,))
        _patch_report(monkeypatch, _report(scope))

        async def _boom(self, **kwargs):  # noqa: ARG001
            raise RuntimeError("lots engine unavailable")

        monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", _boom)

        async def _fake_discover(session, scope):  # noqa: ARG001
            return {1}

        monkeypatch.setattr(shared_payloads, "discover_transacted_asset_ids", _fake_discover)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("portfolio.fifo_summary", required=True)
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_wrong_domain_scope_raises_scope_error(self, monkeypatch):
        scope = _scope(domain=Domain.BROKER, broker_id=1, broker_scope=(1,))
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("portfolio.summary", required=True)
        assert isinstance(exc_info.value.cause, portfolio_financial.PortfolioComponentScopeError)


# =============================================================================
# Payload validation (extra="forbid", currency-safe)
# =============================================================================


class TestPayloadValidation:
    def test_summary_payload_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            portfolio_financial.PortfolioSummaryPayload(
                as_of=date(2026, 1, 10),
                period_start=date(2026, 1, 1),
                target_currency=CURRENCY,
                position_count=0,
                position_broker_count=0,
                net_worth=_money(0),
                total_invested=_money(0),
                total_gain_loss=_money(0),
                total_gain_loss_percent=Decimal("0"),
                cash_total=_money(0),
                simple_roi_percent=Decimal("0"),
                unexpected_field="nope",
            )

    def test_fifo_lot_row_rejects_lot_id_field(self):
        with pytest.raises(ValidationError):
            FifoLotRow(
                lot_ref="L1",
                asset_id=1,
                asset_name="Asset 1",
                opening_broker_id=1,
                direction="LONG",
                status="OPEN",
                opening_date=date(2026, 1, 1),
                opening_unit_price=_money(100),
                original_quantity=Decimal("10"),
                open_quantity=Decimal("10"),
                realized_quantity=Decimal("0"),
                original_cost=_money(1000),
                residual_cost_basis=_money(1000),
                cumulative_proceeds=_money(0),
                realized_pnl=_money(0),
                income=_money(0),
                fees=_money(0),
                taxes=_money(0),
                net_metrics_status="AVAILABLE",
                lot_id=999,
            )

    @pytest.mark.asyncio
    async def test_builder_output_validated_against_envelope_output_model(self, monkeypatch):
        scope = _scope()
        report = _report(scope, summary=_summary(holdings=[_holding(1, 1)]))
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.summary", required=True)

        # Round-trips cleanly back through the declared output_model.
        portfolio_financial.PortfolioSummaryPayload.model_validate(envelope.payload)

    def test_currency_forbids_unknown_field(self):
        with pytest.raises(ValidationError):
            Currency(code=CURRENCY, amount=Decimal("1"), unexpected="nope")

    @pytest.mark.asyncio
    async def test_malformed_builder_output_raises_payload_validation_error_not_broad_success(self, monkeypatch):
        scope = _scope()
        bad_spec_components = list(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)

        def _broken_builder(context, dependencies):  # noqa: ARG001
            return {"not": "a valid PortfolioSummaryPayload"}

        broken = ComponentSpec(
            component_id="portfolio.summary",
            version=1,
            domains=frozenset({Domain.PORTFOLIO}),
            output_model=portfolio_financial.PortfolioSummaryPayload,
            builder=_broken_builder,
        )
        bad_spec_components[0] = broken
        registry = _registry(bad_spec_components)
        context = _make_context(scope, registry, _make_async_session())

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("portfolio.summary", required=True)
        assert isinstance(exc_info.value.cause, ComponentPayloadValidationError)
