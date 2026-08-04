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


def _history_point(
    day: date,
    *,
    nav: object,
    capital_baseline: object,
    total_pnl: object,
    twrr: object | None = None,
) -> PortfolioHistoryPoint:
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
        twrr=(Decimal(str(twrr)) if twrr is not None else None),
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
