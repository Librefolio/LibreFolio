"""End-to-end integration tests for the Portfolio/Broker domain fragment
(Phase 0 AI Export refinement, `ai-refinement-portfolio-broker` domain
integration gate).

Covers `backend.app.services.ai_export.components.portfolio_broker_registry`:
placeholder-vs-real metadata validation, real `ComponentRegistry`/
`DatasetRegistry`/`AnalysisRegistry` construction (merged with the untouched
Asset/FX placeholders from the frozen central catalog), and full `Composer`
driven end-to-end composition of every Portfolio/Broker dataset and analysis
against mocked engine/price resources - never against `components.catalog`
itself (that file is intentionally left untouched here; wiring real builders
into it is owned by the later `ai-refinement-component-registry-integration`
serial gate).

Mirrors the sibling unit-test files' lightweight pattern: no real database
schema (a tableless in-memory `AsyncSession` only satisfies `BuildContext`'s
`isinstance` check); `PortfolioService.get_report`/`LotsAnalysisService.
get_lots_analysis`/`AssetSourceManager.get_prices_bulk`/asset+broker metadata
loaders are monkeypatched with deterministic synthetic data, but price
monkeypatching still drives the **real** `SignalService.compute` so technical
indicator/breadth/event composition is genuinely exercised end-to-end, not
stubbed away.
"""

from __future__ import annotations

import ast
import asyncio
import json
import math
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
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
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.schemas.signals import SignalCadence, SignalDomain, SignalPricePoint
from backend.app.services.ai_export.analyses.catalog import EXPECTED_ANALYSIS_COUNT
from backend.app.services.ai_export.components import broker_cost_efficiency, broker_financial, portfolio_financial
from backend.app.services.ai_export.components import portfolio_broker_registry as portfolio_broker_registry_module
from backend.app.services.ai_export.components.catalog import (
    ALL_FOUNDATION_COMPONENTS,
    ComponentNotImplementedError,
    build_component_registry,
)
from backend.app.services.ai_export.components.payloads import portfolio_broker as shared_payloads
from backend.app.services.ai_export.components.portfolio_broker_registry import (
    BROKER_REAL_COMPONENT_COUNT,
    BROKER_REAL_COMPONENT_IDS,
    PORTFOLIO_BROKER_COMPONENTS,
    PORTFOLIO_REAL_COMPONENT_COUNT,
    PORTFOLIO_REAL_COMPONENT_IDS,
    DuplicateReplacementComponentIdError,
    MissingPlaceholderComponentError,
    PlaceholderMetadataMismatchError,
    build_portfolio_broker_analysis_registry,
    build_portfolio_broker_component_registry,
    build_portfolio_broker_dataset_registry,
    validate_replacements_against_placeholders,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import (
    BROKER_LOTS_RESULTS_RESOURCE,
    BROKER_PRICE_RESULTS_RESOURCE,
    BROKER_REPORT_RESOURCE,
    PORTFOLIO_LOTS_RESULTS_RESOURCE,
    PORTFOLIO_PRICE_RESULTS_RESOURCE,
    PORTFOLIO_REPORT_RESOURCE,
)
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain, PeriodBehavior, ResourceKey, TemporalAggregatorSpec
from backend.app.services.ai_export.composer import Composer
from backend.app.services.ai_export.datasets.catalog import EXPECTED_DATASET_COUNT
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    RequiredComponentBuildError,
    ResourceKeyConflictError,
    build_bucket_plan_for_scope,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.signal_service import SignalExecutionContext, SignalService

CURRENCY = "USD"

# =============================================================================
# Generic construction helpers (mirrors the sibling financial/technical test
# files' conventions - real pydantic schema instances everywhere the builders
# read strongly-typed fields, no SimpleNamespace substitutes).
# =============================================================================


def _money(amount: object) -> Currency:
    return Currency(code=CURRENCY, amount=Decimal(str(amount)))


def _portfolio_scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-portfolio",
        "user_id": 1,
        "domain": Domain.PORTFOLIO,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 20),
        "target_currency": CURRENCY,
        "broker_scope": (),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _broker_scope(broker_id: int = 9, **overrides) -> BuildScope:
    defaults = {
        "request_id": "req-broker",
        "user_id": 1,
        "domain": Domain.BROKER,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 20),
        "target_currency": CURRENCY,
        "broker_id": broker_id,
        "broker_scope": (broker_id,),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _make_async_session() -> AsyncSession:
    """Tableless in-memory `AsyncSession`: only satisfies `BuildContext`'s isinstance check."""
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


def _contribution_row(asset_id: int, broker_id: int, *, period_pnl: object = 100, end_value: object = 1000, is_fully_sold: bool = False) -> AssetPeriodContribution:
    return AssetPeriodContribution(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        period_pnl=Decimal(str(period_pnl)),
        end_value=(Decimal(str(end_value)) if end_value is not None else None),
        is_fully_sold=is_fully_sold,
    )


def _summary(*, holdings=(), allocation_by_type=(), **overrides) -> PortfolioSummary:
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


def _report(
    scope: BuildScope,
    *,
    summary: PortfolioSummary | None = None,
    history=(),
    contribution: PositionsContribution | None = None,
) -> PortfolioReportResponse:
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
        calculation_metadata=LotsAnalysisMetadata(requested_analyses=[LotAnalysisType.LOT_SUMMARY], generated_at=date(2026, 1, 20)),
        lots=list(lots),
    )


def _asset_meta(asset_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=asset_id, display_name=f"Asset {asset_id}", identifier_ticker=f"A{asset_id}")


def _broker_meta(broker_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=broker_id, name=f"Broker {broker_id}")


def _patch_report(monkeypatch: pytest.MonkeyPatch, report: PortfolioReportResponse) -> list[int]:
    calls: list[int] = []

    async def _fake_get_report(self, user_id, query):  # noqa: ARG001
        calls.append(1)
        return report

    monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
    return calls


def _patch_lots(monkeypatch: pytest.MonkeyPatch, responses_by_asset: dict[int, LotsAnalysisResponse], *, asset_ids: set[int] | None = None) -> list[int]:
    calls: list[int] = []

    async def _fake_get_lots_analysis(self, **kwargs):  # noqa: ARG001
        calls.append(1)
        return responses_by_asset[kwargs["asset_id"]]

    async def _fake_discover(session, scope):  # noqa: ARG001
        return set(asset_ids if asset_ids is not None else responses_by_asset)

    async def _fake_resolve_accessible_broker_ids(session, user_id):  # noqa: ARG001
        return []

    monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", _fake_get_lots_analysis)
    monkeypatch.setattr(shared_payloads, "discover_transacted_asset_ids", _fake_discover)
    monkeypatch.setattr(shared_payloads, "resolve_accessible_broker_ids", _fake_resolve_accessible_broker_ids)
    return calls


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, *, asset_ids: list[int] = (), broker_ids: list[int] = ()) -> None:
    async def _fake_assets(session, ids):  # noqa: ARG001
        return {asset_id: _asset_meta(asset_id) for asset_id in asset_ids}

    monkeypatch.setattr(portfolio_financial, "_load_asset_metadata", _fake_assets)
    monkeypatch.setattr(broker_financial, "_load_asset_metadata", _fake_assets)


def _synthetic_close(asset_id: int, day: date) -> Decimal:
    ordinal = day.toordinal()
    base = 100 + asset_id * 5
    wave = 10 * math.sin(ordinal / 7.0)
    return Decimal(str(round(base + wave, 4)))


def _synthetic_volume(asset_id: int, day: date) -> Decimal:
    ordinal = day.toordinal()
    return Decimal(1000 + asset_id * 10 + (ordinal % 50) * 10)


def _fa_price_point(asset_id: int, day: date) -> FAPricePoint:
    close = _synthetic_close(asset_id, day)
    return FAPricePoint(
        date=day,
        open=close,
        high=close * Decimal("1.01"),
        low=close * Decimal("0.99"),
        close=close,
        volume=_synthetic_volume(asset_id, day),
        currency=CURRENCY,
        source_plugin_key="yfinance",
        backward_fill_info=None,
    )


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _patch_get_prices_bulk(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Fake `AssetSourceManager.get_prices_bulk` driving the real `SignalService`.

    For each `FAPriceQueryItem`, computes the real warm-up plan, generates
    synthetic deterministic OHLCV prices over `[visible_start - warmup,
    visible_end]`, computes real signals over the full warm-up-inclusive
    series via `SignalService.compute`, then slices `result.prices` back to
    the visible period only - exactly mirroring the production contract, per
    `test_ai_export_components_technical.py`'s established pattern.
    """
    calls: list[int] = []

    async def _fake(requests, session):  # noqa: ARG001
        calls.append(len(requests))
        signal_service = SignalService()
        results: list[FAPriceQueryResult] = []
        for req in requests:
            visible_start = req.date_range.start
            visible_end = req.date_range.end or visible_start
            signal_context = SignalExecutionContext(
                domain=SignalDomain.ASSET,
                requested_range=req.date_range,
                cadence=SignalCadence.DAILY,
                source_reference=f"asset:{req.asset_id}",
            )
            plan = signal_service.prepare_plan(req.signals, signal_context, req.annotation_requests)
            warmup_days = min(plan.max_history_points_before_visible, (visible_start - date.min).days)
            load_start = visible_start - timedelta(days=warmup_days)

            fa_points = [_fa_price_point(req.asset_id, day) for day in _daterange(load_start, visible_end)]
            signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
            capability = AssetSourceManager.derive_signal_source_capability(fa_points)
            signals = await signal_service.compute(
                req.signals,
                signal_points,
                signal_context,
                annotation_requests=req.annotation_requests,
                source_capability=capability,
            )
            visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end] if req.include_price else []
            results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
        return results

    monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_fake))
    return calls


def _full_registry() -> ComponentRegistry:
    return build_component_registry()


def _full_context(scope: BuildScope, session: AsyncSession) -> BuildContext:
    return _make_context(scope, _full_registry(), session)


# =============================================================================
# Shared multi-asset/multi-broker fixture scenario used by the composition
# tests below: 3 held Portfolio positions (brokers 1/2), one held Broker-9
# position, one closed lot before the FIFO cutoff (excluded), one closed lot
# after the cutoff (included) and one still-open lot (always included).
# =============================================================================

_HELD_ASSET_IDS = (1, 2, 3)
_CUTOFF = date(2026, 1, 1)  # == _portfolio_scope()/_broker_scope() period_start


def _portfolio_holdings() -> list[PortfolioHolding]:
    return [_holding(1, 1), _holding(2, 1), _holding(3, 2)]


def _portfolio_contributions() -> PositionsContribution:
    return PositionsContribution(positions=[_contribution_row(asset_id, broker_id) for asset_id, broker_id in ((1, 1), (2, 1), (3, 2))])


def _portfolio_report_full(scope: BuildScope) -> PortfolioReportResponse:
    return _report(
        scope,
        summary=_summary(holdings=_portfolio_holdings()),
        history=[_history_point(date(2026, 1, 1), nav=1000, capital_baseline=1000, total_pnl=0), _history_point(date(2026, 1, 20), nav=1100, capital_baseline=1000, total_pnl=100)],
        contribution=_portfolio_contributions(),
    )


def _broker_report_full(scope: BuildScope, broker_id: int = 9) -> PortfolioReportResponse:
    return _report(
        scope,
        summary=_summary(holdings=[_holding(4, broker_id)]),
        history=[_history_point(date(2026, 1, 1), nav=500, capital_baseline=500, total_pnl=0)],
        contribution=PositionsContribution(positions=[_contribution_row(4, broker_id)]),
    )


def _fifo_lots_by_asset() -> dict[int, LotsAnalysisResponse]:
    """One closed lot before cutoff (excluded), one closed after (included), one open lot (always included), per asset."""
    lots_by_asset: dict[int, LotsAnalysisResponse] = {}
    for asset_id in _HELD_ASSET_IDS:
        lots = [
            _lot(asset_id, asset_id * 100 + 1, opening_broker_id=1 if asset_id != 3 else 2, closing_date=date(2025, 6, 1), open_quantity=0, realized_quantity=10),  # closed before cutoff
            _lot(asset_id, asset_id * 100 + 2, opening_broker_id=1 if asset_id != 3 else 2, closing_date=date(2026, 1, 10), open_quantity=0, realized_quantity=10),  # closed after cutoff
            _lot(asset_id, asset_id * 100 + 3, opening_broker_id=1 if asset_id != 3 else 2, closing_date=None, open_quantity=10, realized_quantity=0),  # open
        ]
        lots_by_asset[asset_id] = _lots_response(asset_id, lots)
    return lots_by_asset


def _setup_portfolio_scenario(monkeypatch: pytest.MonkeyPatch, scope: BuildScope) -> None:
    _patch_report(monkeypatch, _portfolio_report_full(scope))
    _patch_lots(monkeypatch, _fifo_lots_by_asset(), asset_ids=set(_HELD_ASSET_IDS))
    _patch_metadata(monkeypatch, asset_ids=list(_HELD_ASSET_IDS), broker_ids=[1, 2])
    _patch_get_prices_bulk(monkeypatch)


def _broker_fifo_lots_response(broker_id: int) -> LotsAnalysisResponse:
    """Same before/after-cutoff/open lot triad as `_fifo_lots_by_asset`, scoped to the single Broker-9 held asset (id 4)."""
    lots = [
        _lot(4, 401, opening_broker_id=broker_id, closing_date=date(2025, 6, 1), open_quantity=0, realized_quantity=10),  # closed before cutoff
        _lot(4, 402, opening_broker_id=broker_id, closing_date=date(2026, 1, 10), open_quantity=0, realized_quantity=10),  # closed after cutoff
        _lot(4, 403, opening_broker_id=broker_id, closing_date=None, open_quantity=10, realized_quantity=0),  # open
    ]
    return _lots_response(4, lots)


def _patch_broker_period_activity(monkeypatch: pytest.MonkeyPatch, *, ownership_share: str = "1") -> None:
    """Patches the DB-backed broker activity loader so `broker.cost_efficiency`
    builds without a real `broker_user_access`/transactions table. An empty record
    set yields a valid payload (turnover zero, ratios unavailable-with-reason)."""

    async def _fake_load(context, scope):  # noqa: ARG001
        return broker_cost_efficiency.BrokerPeriodActivity(records=(), ownership_share=Decimal(ownership_share))

    monkeypatch.setattr(broker_cost_efficiency, "_load_broker_period_activity", _fake_load)


def _setup_broker_scenario(monkeypatch: pytest.MonkeyPatch, scope: BuildScope, broker_id: int = 9) -> None:
    _patch_report(monkeypatch, _broker_report_full(scope, broker_id))
    _patch_lots(monkeypatch, {4: _broker_fifo_lots_response(broker_id)}, asset_ids={4})
    _patch_metadata(monkeypatch, asset_ids=[4], broker_ids=[broker_id])
    _patch_get_prices_bulk(monkeypatch)
    _patch_broker_period_activity(monkeypatch)


# =============================================================================
# 1. Fragment sanity: exact counts, no duplicates, placeholder-match validation
# =============================================================================


class TestPortfolioBrokerFragmentSanity:
    def test_exact_component_counts(self):
        assert len(PORTFOLIO_BROKER_COMPONENTS) == 41
        assert PORTFOLIO_REAL_COMPONENT_COUNT == 21
        assert BROKER_REAL_COMPONENT_COUNT == 20
        assert len(PORTFOLIO_REAL_COMPONENT_IDS) == 21
        assert len(BROKER_REAL_COMPONENT_IDS) == 20

    def test_no_duplicate_component_ids(self):
        ids = [spec.component_id for spec in PORTFOLIO_BROKER_COMPONENTS]
        assert len(ids) == len(set(ids))

    def test_expected_portfolio_ids_exact(self):
        expected = {
            "portfolio.summary",
            "portfolio.positions",
            "portfolio.allocations_cash",
            "portfolio.provenance",
            "portfolio.performance",
            "portfolio.flows_income",
            "portfolio.fees_taxes",
            "portfolio.reconciliation",
            "portfolio.technical_prices",
            "portfolio.technical_indicators",
            "portfolio.technical_breadth",
            "portfolio.technical_events",
            "portfolio.fifo_summary",
            "portfolio.fifo_lots",
            # V2 context components
            "portfolio.technical_coverage",
            "portfolio.asset_market_context",
            "portfolio.asset_drawdown_snapshot",
            "portfolio.context_events",
            "portfolio.event_digest",
            # V1 drawdown context component
            "portfolio.drawdown_summary",
            # AI adequacy remediation: income timeline evidence
            "portfolio.income_timeline",
        }
        assert set(PORTFOLIO_REAL_COMPONENT_IDS) == expected

    def test_expected_broker_ids_exact(self):
        expected = {
            "broker.summary",
            "broker.positions",
            "broker.allocation_concentration",
            "broker.provenance",
            "broker.performance",
            "broker.flows_income_costs",
            "broker.reconciliation",
            "broker.technical_prices",
            "broker.technical_indicators",
            "broker.technical_breadth",
            "broker.technical_events",
            "broker.fifo_summary",
            "broker.fifo_lots",
            # V2 context components
            "broker.technical_coverage",
            "broker.asset_market_context",
            "broker.context_events",
            # V1 drawdown context component
            "broker.drawdown_summary",
            # AI adequacy remediation: concentration + cost efficiency evidence
            "broker.concentration_context",
            "broker.concentration_comparison",
            "broker.cost_efficiency",
        }
        assert set(BROKER_REAL_COMPONENT_IDS) == expected

    def test_validation_passes_for_real_replacements(self):
        validate_replacements_against_placeholders(PORTFOLIO_BROKER_COMPONENTS)

    def test_validation_rejects_duplicate_component_id(self):
        duplicated = (*PORTFOLIO_BROKER_COMPONENTS, PORTFOLIO_BROKER_COMPONENTS[0])
        with pytest.raises(DuplicateReplacementComponentIdError):
            validate_replacements_against_placeholders(duplicated)

    def test_validation_rejects_missing_placeholder(self):
        placeholders_without_summary = tuple(spec for spec in ALL_FOUNDATION_COMPONENTS if spec.component_id != "portfolio.summary")
        with pytest.raises(MissingPlaceholderComponentError):
            validate_replacements_against_placeholders(PORTFOLIO_BROKER_COMPONENTS, placeholders=placeholders_without_summary)

    @pytest.mark.parametrize(
        ("component_id", "field", "override"),
        [
            ("portfolio.summary", "version", 2),
            ("portfolio.summary", "domains", frozenset({Domain.BROKER})),
            ("portfolio.summary", "dependencies", ("portfolio.positions",)),
            ("portfolio.summary", "period_behavior", PeriodBehavior.WINDOWED),
            ("portfolio.technical_prices", "aggregator", TemporalAggregatorSpec(kind="different_kind")),
            ("broker.technical_indicators", "dependencies", ()),
            ("broker.technical_prices", "aggregator", TemporalAggregatorSpec(kind="different_kind")),
        ],
    )
    def test_validation_rejects_metadata_drift(self, component_id, field, override):
        real_spec = next(spec for spec in PORTFOLIO_BROKER_COMPONENTS if spec.component_id == component_id)
        drifted = replace(real_spec, **{field: override})
        drifted_set = tuple(spec if spec.component_id != component_id else drifted for spec in PORTFOLIO_BROKER_COMPONENTS)
        with pytest.raises(PlaceholderMetadataMismatchError):
            validate_replacements_against_placeholders(drifted_set)


# =============================================================================
# 2. ComponentRegistry construction: real PB + untouched Asset/FX placeholders
# =============================================================================


class TestComponentRegistryConstruction:
    def test_merged_registry_has_67_components(self):
        registry = build_portfolio_broker_component_registry()
        assert len(registry) == 67

    def test_pb_component_ids_resolve_to_real_specs(self):
        registry = build_portfolio_broker_component_registry()
        for component_id in (*PORTFOLIO_REAL_COMPONENT_IDS, *BROKER_REAL_COMPONENT_IDS):
            spec = registry.get(component_id)
            assert spec in PORTFOLIO_BROKER_COMPONENTS

    def test_non_pb_placeholders_remain_untouched_and_fail_closed(self):
        registry = build_portfolio_broker_component_registry()
        placeholder_ids = {spec.component_id for spec in ALL_FOUNDATION_COMPONENTS if spec.component_id not in {s.component_id for s in PORTFOLIO_BROKER_COMPONENTS}}
        assert placeholder_ids  # sanity: Asset/FX placeholders exist
        asset_or_fx_id = next(iter(sorted(placeholder_ids)))
        spec = registry.get(asset_or_fx_id)
        placeholder_spec = registry_placeholder(asset_or_fx_id)
        assert spec.builder is placeholder_spec.builder
        # still the frozen fail-closed placeholder: invoking it must still raise
        # ComponentNotImplementedError, never a real payload.
        with pytest.raises(ComponentNotImplementedError):
            spec.builder(None, {})

    def test_canonical_order_preserved_from_frozen_catalog(self):
        registry = build_portfolio_broker_component_registry()
        expected_order = tuple(spec.component_id for spec in ALL_FOUNDATION_COMPONENTS)
        assert registry.canonical_order == expected_order

    def test_broker_technical_prices_precede_and_feed_indicators_like_portfolio(self):
        registry = build_portfolio_broker_component_registry()
        order = registry.canonical_order
        broker_prices = registry.get("broker.technical_prices")
        broker_indicators = registry.get("broker.technical_indicators")
        portfolio_prices = registry.get("portfolio.technical_prices")
        portfolio_indicators = registry.get("portfolio.technical_indicators")

        assert broker_prices.domains == frozenset({Domain.BROKER})
        assert broker_prices.period_behavior == portfolio_prices.period_behavior == PeriodBehavior.AGGREGATED
        assert broker_prices.aggregator == portfolio_prices.aggregator
        assert broker_indicators.dependencies == ("broker.technical_prices",)
        assert portfolio_indicators.dependencies == ("portfolio.technical_prices",)
        assert order.index("broker.technical_prices") + 1 == order.index("broker.technical_indicators")

    def test_catalog_module_is_not_mutated(self):
        """`ALL_FOUNDATION_COMPONENTS` itself must remain the exact frozen placeholder tuple after building the fragment registry."""
        before = tuple(ALL_FOUNDATION_COMPONENTS)
        build_portfolio_broker_component_registry()
        assert ALL_FOUNDATION_COMPONENTS == before


def registry_placeholder(component_id: str):
    return next(spec for spec in ALL_FOUNDATION_COMPONENTS if spec.component_id == component_id)


# =============================================================================
# 3. DatasetRegistry/AnalysisRegistry construction over the real fragment
# =============================================================================


class TestDatasetAndAnalysisRegistryConstruction:
    def test_dataset_registry_has_40_datasets(self):
        registry = build_portfolio_broker_dataset_registry()
        assert len(registry) == EXPECTED_DATASET_COUNT == 40

    def test_analysis_registry_has_22_analyses(self):
        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        assert len(analysis_registry) == EXPECTED_ANALYSIS_COUNT == 22

    def test_portfolio_and_broker_datasets_present(self):
        registry = build_portfolio_broker_dataset_registry()
        portfolio_ids = {spec.dataset_id for spec in registry.for_domain(Domain.PORTFOLIO)}
        broker_ids = {spec.dataset_id for spec in registry.for_domain(Domain.BROKER)}
        assert portfolio_ids == {
            "portfolio.overview",
            "portfolio.performance_flows",
            "portfolio.technical",
            "portfolio.fifo",
            "portfolio.all_data",
            # V2 derived public datasets
            "portfolio.technical_summary",
            "portfolio.asset_snapshot",
            "portfolio.asset_comparison",
            "portfolio.drawdown_context",
            "portfolio.income_evidence",
            "portfolio.overview_and_history",
            "portfolio.asset_history",
        }
        assert broker_ids == {
            "broker.overview",
            "broker.performance_flows",
            "broker.technical",
            "broker.fifo",
            "broker.all_data",
            # V2 derived public datasets
            "broker.technical_summary",
            "broker.asset_comparison",
            "broker.drawdown_context",
            "broker.concentration_evidence",
            "broker.cost_efficiency_evidence",
            "broker.overview_and_history",
            "broker.asset_history",
        }

    def test_portfolio_and_broker_analyses_present(self):
        analysis_registry = build_portfolio_broker_analysis_registry()
        portfolio_analysis_ids = {spec.analysis_id for spec in analysis_registry if spec.domain == Domain.PORTFOLIO}
        broker_analysis_ids = {spec.analysis_id for spec in analysis_registry if spec.domain == Domain.BROKER}
        assert len(portfolio_analysis_ids) == 10
        assert len(broker_analysis_ids) == 5


# =============================================================================
# 4. Resource sharing: one report/price/lots load per request, no key conflicts
# =============================================================================


class TestResourceSharingAcrossFinancialAndTechnical:
    @pytest.mark.asyncio
    async def test_single_portfolio_report_load_shared_by_financial_and_technical(self, monkeypatch):
        scope = _portfolio_scope()
        calls = _patch_report(monkeypatch, _portfolio_report_full(scope))
        _patch_lots(monkeypatch, _fifo_lots_by_asset(), asset_ids=set(_HELD_ASSET_IDS))
        _patch_metadata(monkeypatch, asset_ids=list(_HELD_ASSET_IDS), broker_ids=[1, 2])
        _patch_get_prices_bulk(monkeypatch)
        context = _full_context(scope, _make_async_session())

        for component_id in ("portfolio.summary", "portfolio.positions", "portfolio.technical_prices", "portfolio.technical_indicators", "portfolio.fifo_summary"):
            await context.resolve(component_id, required=True)

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_single_broker_report_load_shared_by_financial_and_technical(self, monkeypatch):
        scope = _broker_scope()
        calls = _patch_report(monkeypatch, _broker_report_full(scope))
        _patch_lots(monkeypatch, {4: _broker_fifo_lots_response(9)}, asset_ids={4})
        _patch_metadata(monkeypatch, asset_ids=[4], broker_ids=[9])
        _patch_get_prices_bulk(monkeypatch)
        context = _full_context(scope, _make_async_session())

        for component_id in ("broker.summary", "broker.positions", "broker.technical_indicators", "broker.fifo_lots"):
            await context.resolve(component_id, required=True)

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_technical_price_resource_loads_once_across_indicators_breadth_events(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        price_calls = _patch_get_prices_bulk(monkeypatch)
        context = _full_context(scope, _make_async_session())

        for component_id in ("portfolio.technical_prices", "portfolio.technical_indicators", "portfolio.technical_breadth", "portfolio.technical_events"):
            await context.resolve(component_id, required=True)

        assert len(price_calls) == 1

    @pytest.mark.asyncio
    async def test_fifo_lots_resource_loads_once_across_summary_and_lots(self, monkeypatch):
        scope = _portfolio_scope()
        _patch_report(monkeypatch, _portfolio_report_full(scope))
        lots_calls = _patch_lots(monkeypatch, _fifo_lots_by_asset(), asset_ids=set(_HELD_ASSET_IDS))
        _patch_metadata(monkeypatch, asset_ids=list(_HELD_ASSET_IDS), broker_ids=[1, 2])
        context = _full_context(scope, _make_async_session())

        await context.resolve("portfolio.fifo_summary", required=True)
        await context.resolve("portfolio.fifo_lots", required=True)

        assert len(lots_calls) == len(_HELD_ASSET_IDS)  # one get_lots_analysis call per asset, not doubled across fifo_summary/fifo_lots

    def test_portfolio_and_broker_report_resource_keys_are_distinct(self):
        assert PORTFOLIO_REPORT_RESOURCE.name != BROKER_REPORT_RESOURCE.name
        assert PORTFOLIO_PRICE_RESULTS_RESOURCE.name != BROKER_PRICE_RESULTS_RESOURCE.name
        assert PORTFOLIO_LOTS_RESULTS_RESOURCE.name != BROKER_LOTS_RESULTS_RESOURCE.name

    @pytest.mark.asyncio
    async def test_reusing_same_key_with_same_type_never_raises_conflict(self, monkeypatch):
        """Sanity check for requirement 4's "no ResourceKey conflict": resolving the
        same `PORTFOLIO_REPORT_RESOURCE` key repeatedly (same expected type) within
        one request never raises `ResourceKeyConflictError` - only a genuinely
        mismatched type/mode reuse would (see the sibling negative test below).
        """
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        context = _full_context(scope, _make_async_session())

        result_a = await context.db_resource(PORTFOLIO_REPORT_RESOURCE, lambda s: _portfolio_report_full(scope))  # noqa: ARG005
        result_b = await context.db_resource(PORTFOLIO_REPORT_RESOURCE, lambda s: _portfolio_report_full(scope))  # noqa: ARG005
        assert result_a is result_b  # memoized, not reloaded

    @pytest.mark.asyncio
    async def test_reusing_same_key_name_with_conflicting_type_raises(self, monkeypatch):
        """Negative counterpart: a *different* `ResourceKey` instance sharing the same
        stable `name` as `PORTFOLIO_REPORT_RESOURCE` but a conflicting `expected_type`
        must raise `ResourceKeyConflictError` - proving the runtime actually guards
        against exactly the kind of Portfolio/Broker key collision requirement 4
        rules out, rather than merely happening not to collide by construction.
        """
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        context = _full_context(scope, _make_async_session())

        await context.db_resource(PORTFOLIO_REPORT_RESOURCE, lambda s: _portfolio_report_full(scope))  # noqa: ARG005
        conflicting_key = ResourceKey(PORTFOLIO_REPORT_RESOURCE.name, dict)
        with pytest.raises(ResourceKeyConflictError):
            await context.db_resource(conflicting_key, lambda s: {})  # noqa: ARG005


# =============================================================================
# 5. Concurrency: composing multiple datasets concurrently cannot deadlock
# =============================================================================


class TestConcurrentCompositionNoDeadlock:
    @pytest.mark.asyncio
    async def test_concurrent_dataset_composition_completes_within_timeout(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        datasets = [dataset_registry.get(dataset_id) for dataset_id in ("portfolio.overview", "portfolio.performance_flows", "portfolio.technical", "portfolio.fifo", "portfolio.all_data")]

        async def _compose_all():
            return await asyncio.gather(*(composer.compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD) for dataset in datasets))

        results = await asyncio.wait_for(_compose_all(), timeout=15)
        assert len(results) == 5
        assert all(result.sections for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_broker_and_technical_resolution_no_deadlock(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)
        context = _full_context(scope, _make_async_session())

        component_ids = ("broker.summary", "broker.positions", "broker.allocation_concentration", "broker.technical_indicators", "broker.technical_breadth", "broker.technical_events", "broker.fifo_lots")
        results = await asyncio.wait_for(asyncio.gather(*(context.resolve(cid, required=True) for cid in component_ids)), timeout=15)
        assert all(envelope is not None for envelope in results)


# =============================================================================
# 6. End-to-end dataset composition: real payloads, section order, all_data
# =============================================================================


class TestPortfolioDatasetComposition:
    @pytest.mark.asyncio
    async def test_all_five_portfolio_datasets_compose_with_real_payloads(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        for dataset_id in ("portfolio.overview", "portfolio.performance_flows", "portfolio.technical", "portfolio.fifo", "portfolio.all_data"):
            dataset = dataset_registry.get(dataset_id)
            composition = await composer.compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
            assert composition.dataset_id == dataset_id
            built_ids = tuple(section.component_id for section in composition.sections)
            assert built_ids == tuple(cid for cid in dataset.section_order if cid in built_ids)  # section_order preserved
            assert set(dataset.required_component_ids).issubset(built_ids)  # every required component actually resolved (no ComponentNotImplementedError)

    @pytest.mark.asyncio
    async def test_all_data_is_dedup_union_of_the_other_four_datasets(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        source_ids = ("portfolio.overview", "portfolio.performance_flows", "portfolio.technical", "portfolio.fifo")
        union_component_ids: set[str] = set()
        for dataset_id in source_ids:
            union_component_ids.update(dataset_registry.get(dataset_id).section_order)

        all_data = dataset_registry.get("portfolio.all_data")
        assert set(all_data.section_order) == union_component_ids

        composition = await composer.compose_dataset(all_data, context, detail_level=DetailLevel.STANDARD)
        composed_ids = [section.component_id for section in composition.sections]
        assert len(composed_ids) == len(set(composed_ids))  # deduplicated
        assert set(composed_ids) == union_component_ids


class TestBrokerDatasetComposition:
    @pytest.mark.asyncio
    async def test_all_five_broker_datasets_compose_with_real_payloads(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        for dataset_id in ("broker.overview", "broker.performance_flows", "broker.technical", "broker.fifo", "broker.all_data"):
            dataset = dataset_registry.get(dataset_id)
            composition = await composer.compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
            built_ids = tuple(section.component_id for section in composition.sections)
            assert set(dataset.required_component_ids).issubset(built_ids)

    @pytest.mark.asyncio
    async def test_broker_all_data_dedup_union(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        source_ids = ("broker.overview", "broker.performance_flows", "broker.technical", "broker.fifo")
        union_component_ids: set[str] = set()
        for dataset_id in source_ids:
            union_component_ids.update(dataset_registry.get(dataset_id).section_order)
        all_data = dataset_registry.get("broker.all_data")
        assert set(all_data.section_order) == union_component_ids

        composition = await composer.compose_dataset(all_data, context, detail_level=DetailLevel.STANDARD)
        composed_ids = [section.component_id for section in composition.sections]
        assert len(composed_ids) == len(set(composed_ids))


# =============================================================================
# 7. End-to-end analysis composition: all Portfolio/Broker registry analyses
# =============================================================================


class TestAnalysisComposition:
    @pytest.mark.asyncio
    async def test_all_ten_portfolio_analyses_compose(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        portfolio_analyses = [spec for spec in analysis_registry if spec.domain == Domain.PORTFOLIO]
        assert len(portfolio_analyses) == 10
        for analysis in portfolio_analyses:
            composition = await composer.compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)
            assert set(analysis.required_dataset_ids).issubset(set(composition.dataset_ids))
            assert composition.sections  # real payloads, never empty given the fixture scenario

    @pytest.mark.asyncio
    async def test_all_five_broker_analyses_compose(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        broker_analyses = [spec for spec in analysis_registry if spec.domain == Domain.BROKER]
        assert len(broker_analyses) == 5
        for analysis in broker_analyses:
            composition = await composer.compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)
            assert set(analysis.required_dataset_ids).issubset(set(composition.dataset_ids))
            assert composition.sections

    @pytest.mark.asyncio
    async def test_entity_cardinality_identical_across_detail_levels_only_bucket_count_differs(self, monkeypatch):
        bucket_counts: dict[DetailLevel, int] = {}
        position_counts: dict[DetailLevel, int] = {}
        for detail_level in (DetailLevel.COMPACT, DetailLevel.STANDARD, DetailLevel.FULL):
            scope = _portfolio_scope(detail_level=detail_level)
            _setup_portfolio_scenario(monkeypatch, scope)
            context = _full_context(scope, _make_async_session())

            positions_envelope = await context.resolve("portfolio.positions", required=True)
            position_counts[detail_level] = positions_envelope.payload["position_count"]
            bucket_counts[detail_level] = len(context.bucket_plan.buckets)

        assert len(set(position_counts.values())) == 1  # same entity cardinality across every detail level
        assert len(set(bucket_counts.values())) > 1  # bucket granularity K is the only thing that differs


# =============================================================================
# 8. Optional-only semantics: analysis-level optional dataset omission
# =============================================================================


class TestOptionalDatasetSemantics:
    @pytest.mark.asyncio
    async def test_rebalancing_analysis_omits_optional_datasets_when_technical_fails(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)

        async def _boom(requests, session):  # noqa: ARG001
            raise RuntimeError("price engine unavailable")

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_boom))

        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        rebalancing = next(spec for spec in analysis_registry if spec.analysis_id == "portfolio.rebalancing")
        composition = await composer.compose_analysis(rebalancing, dataset_registry, context, detail_level=DetailLevel.STANDARD)

        assert composition.dataset_ids == ("portfolio.overview_and_history",)
        assert not any(section.component_id.startswith("portfolio.technical_") for section in composition.sections)

    @pytest.mark.asyncio
    async def test_broker_review_omits_optional_technical_and_fifo_independently(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)

        async def _boom_lots(self, **kwargs):  # noqa: ARG001
            raise RuntimeError("fifo engine unavailable")

        monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", _boom_lots)

        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        review = next(spec for spec in analysis_registry if spec.analysis_id == "broker.review")
        composition = await composer.compose_analysis(review, dataset_registry, context, detail_level=DetailLevel.STANDARD)

        assert composition.dataset_ids == ("broker.overview_and_history",)
        assert "broker.fifo_summary" not in {section.component_id for section in composition.sections}
        assert "broker.asset_market_context" in {section.component_id for section in composition.sections}


# =============================================================================
# 9. Empty portfolio/broker is a valid success (never a build failure)
# =============================================================================


class TestEmptyPortfolioAndBroker:
    @pytest.mark.asyncio
    async def test_empty_portfolio_composes_all_datasets_successfully(self, monkeypatch):
        scope = _portfolio_scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(holdings=[]), history=[]))  # empty-but-valid summary, not a missing one
        _patch_lots(monkeypatch, {}, asset_ids=set())
        _patch_metadata(monkeypatch)
        _patch_get_prices_bulk(monkeypatch)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        for dataset_id in ("portfolio.overview", "portfolio.performance_flows", "portfolio.technical", "portfolio.fifo", "portfolio.all_data"):
            composition = await composer.compose_dataset(dataset_registry.get(dataset_id), context, detail_level=DetailLevel.STANDARD)
            assert composition.sections  # every required component still built (successfully, with empty data)

        positions_envelope = await context.resolve("portfolio.positions", required=True)
        assert positions_envelope.payload["position_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_broker_composes_all_datasets_successfully(self, monkeypatch):
        scope = _broker_scope()
        _patch_report(monkeypatch, _report(scope, summary=_summary(holdings=[]), history=[]))
        _patch_lots(monkeypatch, {}, asset_ids=set())
        _patch_metadata(monkeypatch)
        _patch_get_prices_bulk(monkeypatch)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        for dataset_id in ("broker.overview", "broker.performance_flows", "broker.technical", "broker.fifo", "broker.all_data"):
            composition = await composer.compose_dataset(dataset_registry.get(dataset_id), context, detail_level=DetailLevel.STANDARD)
            assert composition.sections

        positions_envelope = await context.resolve("broker.positions", required=True)
        assert positions_envelope.payload["position_count"] == 0


# =============================================================================
# 10. Required source failure propagates as RequiredComponentBuildError
# =============================================================================


class TestRequiredSourceFailurePropagation:
    @pytest.mark.asyncio
    async def test_get_report_failure_propagates_through_dataset_composition(self, monkeypatch):
        scope = _portfolio_scope()

        async def _boom(self, user_id, query):  # noqa: ARG001
            raise RuntimeError("engine unavailable")

        monkeypatch.setattr(PortfolioService, "get_report", _boom)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await composer.compose_dataset(dataset_registry.get("portfolio.overview"), context, detail_level=DetailLevel.STANDARD)
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_get_report_failure_propagates_through_analysis_composition(self, monkeypatch):
        scope = _broker_scope()

        async def _boom(self, user_id, query):  # noqa: ARG001
            raise RuntimeError("engine unavailable")

        monkeypatch.setattr(PortfolioService, "get_report", _boom)
        dataset_registry = build_portfolio_broker_dataset_registry()
        analysis_registry = build_portfolio_broker_analysis_registry(dataset_registry)
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        broker_review = next(spec for spec in analysis_registry if spec.analysis_id == "broker.review")
        with pytest.raises(RequiredComponentBuildError):
            await composer.compose_analysis(broker_review, dataset_registry, context, detail_level=DetailLevel.STANDARD)


# =============================================================================
# 11. Period-aware FIFO cutoff (bucket K aside, this is the only other
#     legitimate "temporal" difference this fragment should exhibit)
# =============================================================================


class TestPeriodAwareFifoCutoff:
    @pytest.mark.asyncio
    async def test_closed_lot_before_cutoff_excluded_after_included_open_always_included(self, monkeypatch):
        scope = _portfolio_scope(period_start=_CUTOFF)
        _patch_report(monkeypatch, _portfolio_report_full(scope))
        _patch_lots(monkeypatch, _fifo_lots_by_asset(), asset_ids=set(_HELD_ASSET_IDS))
        _patch_metadata(monkeypatch, asset_ids=list(_HELD_ASSET_IDS), broker_ids=[1, 2])
        context = _full_context(scope, _make_async_session())

        envelope = await context.resolve("portfolio.fifo_lots", required=True)
        # `FifoLotRow` deliberately has no `lot_id` field - rows are identified
        # here by (asset_id, closing_date) instead: closing_date=None is the
        # always-eligible open lot, the two closed dates are the before-/after-
        # cutoff pair from `_fifo_lots_by_asset`.
        rows_by_asset: dict[int, set[str | None]] = {}
        for row in envelope.payload["lots"]:
            rows_by_asset.setdefault(row["asset_id"], set()).add(row["closing_date"])

        for asset_id in _HELD_ASSET_IDS:
            closing_dates = rows_by_asset[asset_id]
            assert "2025-06-01" not in closing_dates  # closed before cutoff: excluded
            assert "2026-01-10" in closing_dates  # closed after cutoff: included
            assert None in closing_dates  # still open: always included


# =============================================================================
# 12. Breadth/technical composition analyzes the complete universe (no top-N)
# =============================================================================


class TestBreadthCompleteUniverseNoTopN:
    @pytest.mark.asyncio
    async def test_all_eligible_assets_present_in_technical_prices_indicators_breadth(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        context = _full_context(scope, _make_async_session())

        prices_envelope = await context.resolve("portfolio.technical_prices", required=True)
        indicators_envelope = await context.resolve("portfolio.technical_indicators", required=True)
        breadth_envelope = await context.resolve("portfolio.technical_breadth", required=True)

        assert {asset["asset_id"] for asset in prices_envelope.payload["assets"]} == set(_HELD_ASSET_IDS)
        assert {asset["asset_id"] for asset in indicators_envelope.payload["assets"]} == set(_HELD_ASSET_IDS)
        assert prices_envelope.payload["eligible_asset_count"] == len(_HELD_ASSET_IDS)
        assert breadth_envelope is not None


# =============================================================================
# 13. Section payload JSON safety
# =============================================================================


class TestSectionPayloadJsonSafety:
    @pytest.mark.asyncio
    async def test_all_composed_sections_are_json_serializable(self, monkeypatch):
        scope = _portfolio_scope()
        _setup_portfolio_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        composition = await composer.compose_dataset(dataset_registry.get("portfolio.all_data"), context, detail_level=DetailLevel.STANDARD)
        assert composition.sections
        for section in composition.sections:
            serialized = json.dumps(section.payload)
            assert json.loads(serialized) == section.payload

    @pytest.mark.asyncio
    async def test_broker_all_data_sections_are_json_serializable(self, monkeypatch):
        scope = _broker_scope()
        _setup_broker_scenario(monkeypatch, scope)
        dataset_registry = build_portfolio_broker_dataset_registry()
        context = _full_context(scope, _make_async_session())
        composer = Composer()

        composition = await composer.compose_dataset(dataset_registry.get("broker.all_data"), context, detail_level=DetailLevel.STANDARD)
        assert composition.sections
        for section in composition.sections:
            serialized = json.dumps(section.payload)
            assert json.loads(serialized) == section.payload


# =============================================================================
# 14. Import-cycle safety: the fragment must never gain a module-level
# dependency on `components.catalog`, `datasets.catalog` or `analyses.catalog`
# =============================================================================
#
# The later "component-registry-integration" gate is expected to have the real
# `components/catalog.py` import `PORTFOLIO_BROKER_COMPONENTS` from this
# fragment at module scope. For that to be safe, `portfolio_broker_registry.py`
# itself must have zero *module-level* (import-time) dependency on `catalog`,
# `datasets.catalog` or `analyses.catalog` - only function-local/lazy imports,
# deferred until the functions are actually called (by which point every
# module involved has already finished its own top-level execution). These
# tests prove that property both statically (AST) and dynamically (subprocess,
# fresh interpreter, no cached `sys.modules` state from other tests).
#
# Note: `backend.app.services.ai_export.components.catalog` still ends up in
# `sys.modules` after importing the fragment alone - but that is *solely*
# because the shared package `components/__init__.py` (a pre-existing, PB-out-
# of-scope file, unrelated to this task) unconditionally imports `catalog` at
# the top of its own body, for every import of *any* submodule of `components`
# (this is equally true for `portfolio_financial`/`broker_financial`/etc., not
# something this fragment introduces). That is a one-directional dependency
# (`__init__.py -> catalog`, never `catalog -> __init__.py`), so it is not a
# circular-import risk. What *would* be a new, genuinely circular risk - and
# what this fragment must not (and, per the assertions below, does not) do -
# is pull in `datasets.catalog`/`analyses.catalog` at module scope, since a
# future `catalog.py` importing this fragment at its own module scope would
# then transitively re-enter `components.catalog` while it is still
# mid-initialization.


def _fragment_module_source_path() -> str:
    return portfolio_broker_registry_module.__file__


def _module_level_import_targets(source: str) -> set[str]:
    """Returns every module dotted-path referenced by a *module-level* import statement.

    Deliberately skips imports nested inside function/async-function bodies
    (lazy imports) and inside `if TYPE_CHECKING:` blocks (type-only, erased at
    runtime because of `from __future__ import annotations`), since neither
    contributes to this module's *import-time* dependency graph.
    """
    tree = ast.parse(source)
    targets: set[str] = set()

    def is_type_checking_guard(node: ast.If) -> bool:
        test = node.test
        return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.If) and is_type_checking_guard(node):
            continue
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)

    return targets


class TestImportCycleSafety:
    def test_fragment_source_has_no_module_level_catalog_imports(self):
        """Static (AST) proof: no top-level import of catalog/datasets.catalog/analyses.catalog."""
        source = open(_fragment_module_source_path(), encoding="utf-8").read()
        module_level_targets = _module_level_import_targets(source)
        forbidden = {
            "backend.app.services.ai_export.components.catalog",
            "backend.app.services.ai_export.datasets.catalog",
            "backend.app.services.ai_export.analyses.catalog",
        }
        offending = module_level_targets & forbidden
        assert not offending, f"fragment module must not import {forbidden} at module scope, found: {offending}"

    def test_fragment_source_defers_catalog_datasets_analyses_imports_to_function_bodies(self):
        """Sanity counterpart: the lazy imports must still exist *somewhere* in the source (inside functions)."""
        source = open(_fragment_module_source_path(), encoding="utf-8").read()
        assert "from backend.app.services.ai_export.components.catalog import" in source
        assert "from backend.app.services.ai_export.datasets.catalog import" in source
        assert "from backend.app.services.ai_export.analyses.catalog import" in source

    def test_fresh_process_import_of_fragment_does_not_pull_in_datasets_or_analyses_catalog(self):
        """Dynamic proof, fresh interpreter: importing the fragment alone never loads `datasets.catalog`/`analyses.catalog`.

        `components.catalog` is expected to still appear (see the section
        docstring above: it is forced in by the pre-existing, unrelated
        `components/__init__.py` package init, not by this fragment) - that is
        asserted too, so this test fails loudly (rather than silently drifting)
        if that pre-existing package-level coupling ever changes.
        """
        probe = (
            "import sys\n"
            "import importlib\n"
            "importlib.import_module('backend.app.services.ai_export.components.portfolio_broker_registry')\n"
            "print('catalog' if 'backend.app.services.ai_export.components.catalog' in sys.modules else 'no-catalog')\n"
            "print('datasets-catalog' if 'backend.app.services.ai_export.datasets.catalog' in sys.modules else 'no-datasets-catalog')\n"
            "print('analyses-catalog' if 'backend.app.services.ai_export.analyses.catalog' in sys.modules else 'no-analyses-catalog')\n"
        )
        result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f"fresh-process import failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        lines = result.stdout.strip().splitlines()
        assert "catalog" in lines, "expected components.catalog to be present (pulled in by the pre-existing components/__init__.py, unrelated to the fragment)"
        assert "no-datasets-catalog" in lines, "fragment import must never pull in datasets.catalog at module scope"
        assert "no-analyses-catalog" in lines, "fragment import must never pull in analyses.catalog at module scope"

    def test_fresh_process_end_to_end_registry_construction_still_works(self):
        """After a fresh-process fragment import, all three lazy-importing builder functions must still work end-to-end."""
        probe = (
            "import importlib\n"
            "frag = importlib.import_module('backend.app.services.ai_export.components.portfolio_broker_registry')\n"
            "component_registry = frag.build_portfolio_broker_component_registry()\n"
            "dataset_registry = frag.build_portfolio_broker_dataset_registry(component_registry)\n"
            "analysis_registry = frag.build_portfolio_broker_analysis_registry(dataset_registry)\n"
            "print(len(component_registry), len(dataset_registry), len(analysis_registry))\n"
        )
        result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f"fresh-process registry construction failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        assert result.stdout.strip() == "67 40 22"
