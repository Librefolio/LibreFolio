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
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    LotAnalysisType,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportResponse,
    PortfolioSummary,
    PositionsContribution,
)
from backend.app.services.ai_export.components import broker_financial, portfolio_financial
from backend.app.services.ai_export.components.envelope import ComponentPayloadValidationError
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


def _history_point(day: date, *, nav: object, capital_baseline: object, total_pnl: object) -> PortfolioHistoryPoint:
    return PortfolioHistoryPoint(
        date=day,
        cash_value=_money(0),
        market_value=_money(nav),
        nav_value=_money(nav),
        capital_baseline=_money(capital_baseline),
        book_asset_like=_money(0),
        cash_from_contributed_capital=_money(0),
        cash_from_generated_returns=_money(0),
        total_pnl=_money(total_pnl),
    )


def _holding(asset_id: int, broker_id: int, *, quantity: object = 10, current_value: object = 1000) -> PortfolioHolding:
    return PortfolioHolding(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        quantity=Decimal(str(quantity)),
        current_value=Decimal(str(current_value)),
        nav_weight_percent=Decimal("10"),
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
        realized_pnl=Decimal("0"),
        cumulative_proceeds=Decimal("0"),
    )


def _lots_response(asset_id: int, lots: list[LotSummarySchema]) -> LotsAnalysisResponse:
    return LotsAnalysisResponse(
        asset_id=asset_id,
        target_currency=CURRENCY,
        calculation_status="COMPLETE",
        calculation_metadata=LotsAnalysisMetadata(requested_analyses=[LotAnalysisType.LOT_SUMMARY], generated_at=date(2026, 1, 10)),
        lots=list(lots),
    )


def _asset_meta(asset_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=asset_id, display_name=f"Asset {asset_id}", identifier_ticker=f"A{asset_id}")


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

    async def _fake_brokers(session, ids):  # noqa: ARG001
        return {broker_id: _broker_meta(broker_id) for broker_id in broker_ids}

    monkeypatch.setattr(portfolio_financial, "_load_asset_metadata", _fake_assets)
    monkeypatch.setattr(portfolio_financial, "_load_broker_metadata", _fake_brokers)
    monkeypatch.setattr(broker_financial, "_load_asset_metadata", _fake_assets)
    monkeypatch.setattr(broker_financial, "_load_broker_metadata", _fake_brokers)


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
            assert performance_envelope.payload["contributor_count"] == 3
            assert len(performance_envelope.payload["contributors"]) == 3


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


class TestEngineReconciliation:
    @pytest.mark.asyncio
    async def test_reconciled_true_when_engine_fields_sum_exactly(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            period_pnl=_money(100),
            period_unrealized_gain_loss_delta=_money(60),
            period_realized_gain_loss=_money(20),
            period_income=_money(30),
            period_fees_taxes=_money(10),
            period_other_result=_money(0),
        )
        # period_pnl == unrealized_delta + realized + income - fees_taxes + other_result -> 60+20+30-10+0=100
        report = _report(scope, summary=summary)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.reconciliation", required=True)

        assert envelope.payload["reconciled"] is True
        assert Decimal(envelope.payload["residual"]["amount"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_reconciled_false_and_residual_reported_when_engine_fields_do_not_sum(self, monkeypatch):
        scope = _scope()
        summary = _summary(
            period_pnl=_money(999),
            period_unrealized_gain_loss_delta=_money(60),
            period_realized_gain_loss=_money(20),
            period_income=_money(30),
            period_fees_taxes=_money(10),
            period_other_result=_money(0),
        )
        report = _report(scope, summary=summary)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.reconciliation", required=True)

        assert envelope.payload["reconciled"] is False
        assert Decimal(envelope.payload["residual"]["amount"]) == Decimal("899")

    @pytest.mark.asyncio
    async def test_reconciliation_none_when_engine_fields_missing_not_fabricated(self, monkeypatch):
        scope = _scope()
        summary = _summary(period_pnl=None, period_unrealized_gain_loss_delta=None, period_realized_gain_loss=None, period_income=None, period_fees_taxes=None, period_other_result=None)
        report = _report(scope, summary=summary)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.reconciliation", required=True)

        assert envelope.payload["reconciled"] is None
        assert envelope.payload["residual"] is None


# =============================================================================
# Performance bucket edges + explicit empty buckets
# =============================================================================


class TestPerformanceBuckets:
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
        assert buckets[-1]["end_date"] == "2026-01-10"
        empty_buckets = [bucket for bucket in buckets if not bucket["has_data"]]
        assert empty_buckets, "expected at least one explicit empty bucket for the uncovered tail of the period"
        for bucket in empty_buckets:
            assert bucket["start_value"] is None
            assert bucket["end_value"] is None
            assert bucket["return_percent"] is None

    @pytest.mark.asyncio
    async def test_bucket_reconciliation_diff_is_zero_when_flow_and_pnl_explain_full_delta(self, monkeypatch):
        # A period far longer than the ramp-start offset (7 days) so the oldest
        # bucket is wide enough (COMPACT policy, up to 30 days) to span the two
        # history points below in a single bucket - a short period would put
        # each day in its own single-point (daily) bucket, making any
        # within-bucket flow/return check trivially vacuous.
        scope = _scope(period_start=date(2025, 1, 1), period_end=date(2026, 1, 10), detail_level=DetailLevel.COMPACT)
        bucket_plan = build_bucket_plan_for_scope(scope)
        oldest_bucket = bucket_plan.buckets[0]
        start_day = oldest_bucket.start_date
        end_day = min(oldest_bucket.end_date, start_day + timedelta(days=5))
        history = [
            _history_point(start_day, nav=1000, capital_baseline=1000, total_pnl=0),
            _history_point(end_day, nav=1110, capital_baseline=1100, total_pnl=10),
        ]
        report = _report(scope, summary=_summary(), history=history)
        _patch_report(monkeypatch, report)
        _patch_lots(monkeypatch, {})
        _patch_metadata(monkeypatch)
        registry = _registry(portfolio_financial.PORTFOLIO_FINANCIAL_COMPONENTS)
        context = _make_context(scope, registry, _make_async_session())

        envelope = await context.resolve("portfolio.performance", required=True)
        bucket = envelope.payload["buckets"][0]

        assert Decimal(bucket["net_external_flow"]["amount"]) == Decimal("100")
        assert Decimal(bucket["period_pnl"]["amount"]) == Decimal("10")
        assert Decimal(bucket["reconciliation_diff"]["amount"]) == Decimal("0")
        # A non-zero external flow means no simple return% is reported (never re-derives TWRR).
        assert bucket["return_percent"] is None


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

        assert "lot_id" not in envelope.payload["lots"][0]

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
                broker_count=0,
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
