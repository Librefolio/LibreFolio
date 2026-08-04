"""Focused tests for the real Asset AI Export core `ComponentSpec` builders
(Phase 0 AI Export refinement, workstream E2 - "Asset core" wave).

Covers `backend.app.services.ai_export.components.asset_core` /
`asset_payloads` / `asset_resources`: one `AssetMetadataResource`/
`PortfolioReportResponse` load per request shared across every Asset-core
component (memoized, regardless of how many independent builders guard on
asset existence), the "missing asset" typed failure surfacing uniformly
from every one of the eight components (not only the ones with a declared
dependency on `asset.identity`), empty/no-position valid overviews,
per-broker row retention with deterministic ordering, identical entity
cardinality across `DetailLevel`s, observed-market-price vs WAC valuation
semantics, engine period-contribution performance aggregation, lot
period-cutoff/no-identifier/no-limit semantics for `asset.lot_detail`,
optional-component fail-soft isolation, malicious free-text passthrough
(never interpreted, just data) and deterministic output across independent
builds.

`PortfolioService.get_report`/`LotsAnalysisService.get_lots_analysis` are
monkeypatched at the class level (matching the existing
`test_ai_export_components_portfolio_broker_financial.py` pattern); the
asset metadata raw-SQL loader (no analogous service class to intercept) is
monkeypatched at the `asset_core.load_asset_metadata` factory-function seam,
and the shared Asset price load (`asset.market_snapshot` consolidated onto
the same `ASSET_PRICE_RESULTS_RESOURCE` the technical sibling wave uses -
parent integration gate, requirement 4) is monkeypatched at the
`asset_core.load_asset_price_results` seam instead. No real database schema
is created or touched - matching the existing
`test_ai_export_component_runtime.py`/`test_ai_export_components_portfolio_broker_financial.py`
pattern of exercising the builder/runtime layer without a live DB.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    LotAnalysisType,
    LotCustodySummarySchema,
    LotsAnalysisMetadata,
    LotsAnalysisResponse,
    LotSummarySchema,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportResponse,
    PortfolioSummary,
    PositionsContribution,
)
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.services.ai_export.components import asset_core
from backend.app.services.ai_export.components.asset_payloads import AssetLotCustodyRow, AssetLotDetailRow
from backend.app.services.ai_export.components.asset_resources import AssetMetadataResource, AssetNotFoundError
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import PriceResultsResource
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    RequiredComponentBuildError,
    build_bucket_plan_for_scope,
)
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

CURRENCY = "EUR"
ASSET_ID = 42

REGISTRY = ComponentRegistry(asset_core.ASSET_CORE_COMPONENTS)


# =============================================================================
# Construction helpers
# =============================================================================


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-asset-1",
        "user_id": 1,
        "domain": Domain.ASSET,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 1, 31),
        "target_currency": CURRENCY,
        "broker_scope": (),
        "asset_id": ASSET_ID,
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _make_async_session() -> AsyncSession:
    """Tableless in-memory `AsyncSession`: only satisfies `BuildContext`'s isinstance check.

    No statement is ever actually executed against it in these tests - every
    raw-resource loader is monkeypatched before touching the DB.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


def _make_context(scope: BuildScope, session: AsyncSession) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(REGISTRY, request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


def _metadata(*, short_description: str | None = None, geographic_area=None, sector_area=None, provider_code: str | None = None, **overrides) -> AssetMetadataResource:
    classification = None
    if short_description is not None or geographic_area is not None or sector_area is not None:
        classification = FAClassificationParams(short_description=short_description, geographic_area=geographic_area, sector_area=sector_area)
    defaults = {
        "asset_id": ASSET_ID,
        "display_name": "Test Asset",
        "currency": CURRENCY,
        "asset_type": "STOCK",
        "quote_base_quantity": 1,
        "active": True,
        "identifier_isin": "US0000000000",
        "identifier_ticker": "TST",
        "identifier_cusip": None,
        "identifier_sedol": None,
        "identifier_figi": None,
        "identifier_other": (),
        "classification": classification,
        "provider_code": provider_code,
        "provider_identifier": "TST" if provider_code else None,
        "provider_identifier_type": "TICKER" if provider_code else None,
        "provider_last_fetch_date": date(2026, 1, 1) if provider_code else None,
    }
    defaults.update(overrides)
    return AssetMetadataResource(**defaults)


def _price_results(*, observed_close: object | None = None, observed_currency: str = CURRENCY, source_plugin_key: str = "manual", observed_date: date = date(2026, 1, 31)) -> PriceResultsResource:
    """Builds the canned `PriceResultsResource` consumed by `asset_core.load_asset_price_results`.

    Mirrors the shape `AssetSourceManager.get_prices_bulk` actually returns
    (see `asset_resources.market_snapshot_from_price_result`): a single
    genuinely-observed point (`backward_fill_info=None`) when
    `observed_close` is given, or an empty result set (no `FAPriceQueryResult`
    for `ASSET_ID`) when `observed_close is None` - the "no price history"
    case.
    """
    if observed_close is None:
        return PriceResultsResource.from_results([])

    point = FAPricePoint(date=observed_date, close=Decimal(str(observed_close)), currency=observed_currency, source_plugin_key=source_plugin_key, backward_fill_info=None)
    return PriceResultsResource.from_results([FAPriceQueryResult(asset_id=ASSET_ID, prices=[point])])


def _holding(
    broker_id: int, *, asset_id: int = ASSET_ID, quantity: object = 10, wac_per_unit: object | None = 40, current_price: object | None = 50, current_value: object | None = 500, gain_loss: object | None = 100, gain_loss_percent: object | None = 25, valuation_source: str | None = "MARKET_PRICE"
) -> PortfolioHolding:
    return PortfolioHolding(
        asset_id=asset_id,
        asset_name="Test Asset" if asset_id == ASSET_ID else f"Other Asset {asset_id}",
        asset_type="STOCK",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        quantity=Decimal(str(quantity)),
        wac_per_unit=Decimal(str(wac_per_unit)) if wac_per_unit is not None else None,
        current_price=Decimal(str(current_price)) if current_price is not None else None,
        current_value=Decimal(str(current_value)) if current_value is not None else None,
        gain_loss=Decimal(str(gain_loss)) if gain_loss is not None else None,
        gain_loss_percent=Decimal(str(gain_loss_percent)) if gain_loss_percent is not None else None,
        valuation_source=valuation_source,
    )


def _contribution(broker_id: int, *, start_value: object | None = 1000, end_value: object | None = 1100, period_pnl: object | None = 100) -> AssetPeriodContribution:
    start = Decimal(str(start_value)) if start_value is not None else None
    end = Decimal(str(end_value)) if end_value is not None else None
    pnl = Decimal(str(period_pnl)) if period_pnl is not None else None
    return AssetPeriodContribution(
        asset_id=ASSET_ID,
        asset_name="Test Asset",
        asset_type="STOCK",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        start_value=start,
        end_value=end,
        period_pnl=pnl,
        period_pnl_percent=(pnl / abs(start)) if (pnl is not None and start is not None and start != 0) else None,
        period_realized_gain_loss=Decimal("0"),
        period_unrealized_delta=pnl,
        period_income=Decimal("0"),
        period_fees_taxes=Decimal("0"),
        is_fully_sold=False,
    )


def _report_metadata(scope: BuildScope) -> PortfolioReportMetadata:
    return PortfolioReportMetadata(target_currency=scope.target_currency, generated_at=scope.snapshot_as_of)


def _report(scope: BuildScope, *, holdings=(), contribution: PositionsContribution | None = None) -> PortfolioReportResponse:
    summary = PortfolioSummary(
        net_worth=_money(sum((h.current_value or Decimal("0")) for h in holdings)),
        total_invested=_money(0),
        total_gain_loss=_money(0),
        total_gain_loss_percent=Decimal("0"),
        cash_total=_money(0),
        simple_roi_percent=Decimal("0"),
        holdings=list(holdings),
    )
    return PortfolioReportResponse(metadata=_report_metadata(scope), summary=summary, positions_contribution=contribution)


def _money(amount: object):
    return Currency(code=CURRENCY, amount=Decimal(str(amount)))


def _lot(
    *,
    opening_broker_id: int = 1,
    opening_date: date = date(2025, 6, 1),
    closing_date: date | None = None,
    original_quantity: object = 10,
    open_quantity: object = 10,
    custody: tuple[LotCustodySummarySchema, ...] = (),
    lot_id: int = 1,
) -> LotSummarySchema:
    return LotSummarySchema(
        lot_id=lot_id,
        opening_transaction_id=lot_id,
        asset_id=ASSET_ID,
        direction="LONG",
        opening_broker_id=opening_broker_id,
        opening_date=opening_date,
        closing_date=closing_date,
        opening_unit_price=Decimal("100"),
        original_quantity=Decimal(str(original_quantity)),
        original_cost=Decimal("1000"),
        open_quantity=Decimal(str(open_quantity)),
        realized_quantity=Decimal(str(Decimal(str(original_quantity)) - Decimal(str(open_quantity)))),
        realized_pnl=Decimal("0"),
        cumulative_proceeds=Decimal("0"),
        current_custody=list(custody),
    )


def _lots_response(scope: BuildScope, lots: list[LotSummarySchema]) -> LotsAnalysisResponse:
    return LotsAnalysisResponse(
        asset_id=ASSET_ID,
        target_currency=scope.target_currency,
        calculation_status="COMPLETE",
        calculation_metadata=LotsAnalysisMetadata(requested_analyses=[LotAnalysisType.LOT_SUMMARY], generated_at=scope.snapshot_as_of),
        lots=list(lots),
    )


# =============================================================================
# Monkeypatch helpers
# =============================================================================


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, outcome: AssetMetadataResource | BaseException) -> list[int]:
    """Patches `asset_core.load_asset_metadata`'s factory; returns a call counter for the loader body."""
    calls: list[int] = []

    def _factory(scope):
        async def _load(session):  # noqa: ARG001
            calls.append(1)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        return _load

    monkeypatch.setattr(asset_core, "load_asset_metadata", _factory)
    return calls


def _patch_market_snapshot(monkeypatch: pytest.MonkeyPatch, price_results: PriceResultsResource) -> None:
    def _fake_load_asset_market_prices(scope):  # noqa: ARG001
        async def _load(session):  # noqa: ARG001
            return price_results

        return _load

    monkeypatch.setattr(
        asset_core,
        "load_asset_market_prices",
        _fake_load_asset_market_prices,
    )


def _patch_report(monkeypatch: pytest.MonkeyPatch, report: PortfolioReportResponse) -> list[int]:
    """Monkeypatches `PortfolioService.get_report` (class level); returns a call counter."""
    calls: list[int] = []

    async def _fake_get_report(self, user_id, query):  # noqa: ARG001
        calls.append(1)
        return report

    monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
    return calls


def _patch_lots(monkeypatch: pytest.MonkeyPatch, response: LotsAnalysisResponse | BaseException) -> list[int]:
    """Monkeypatches `LotsAnalysisService.get_lots_analysis` (class level); returns a call counter."""
    calls: list[int] = []

    async def _fake_get_lots_analysis(self, **kwargs):  # noqa: ARG001
        calls.append(1)
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(LotsAnalysisService, "get_lots_analysis", _fake_get_lots_analysis)
    return calls


# =============================================================================
# Missing asset - uniform typed failure across every component
# =============================================================================


class TestMissingAssetTypedFailure:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "component_id",
        [
            "asset.identity",
            "asset.market_snapshot",
            "asset.position_scope",
            "asset.provenance",
            "asset.positions_by_broker",
            "asset.cost_value_pl",
            "asset.performance",
            "asset.lot_detail",
        ],
    )
    async def test_missing_asset_propagates_as_required_component_build_error(self, monkeypatch, component_id):
        scope = _scope()
        _patch_metadata(monkeypatch, AssetNotFoundError(f"Asset {ASSET_ID} not found"))
        context = _make_context(scope, _make_async_session())

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve(component_id, required=True)

        assert isinstance(exc_info.value.cause, AssetNotFoundError) or isinstance(exc_info.value.__cause__, AssetNotFoundError) or "not found" in str(exc_info.value.cause)


# =============================================================================
# Empty / no-position valid overview
# =============================================================================


class TestEmptyOverviewIsValid:
    @pytest.mark.asyncio
    async def test_no_holdings_yields_empty_position_scope_not_a_failure(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.position_scope", required=True)

        assert envelope.payload["brokers"] == []
        assert envelope.payload["broker_count"] == 0
        assert envelope.payload["total_quantity"] == "0"

    @pytest.mark.asyncio
    async def test_no_price_history_yields_empty_market_snapshot_not_a_failure(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_market_snapshot(monkeypatch, _price_results(observed_close=None))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.market_snapshot", required=True)

        assert envelope.payload["observed"] is None
        assert envelope.payload["converted_price"] is None
        assert envelope.payload["conversion"] is None


class TestPositionUnitPrice:
    @pytest.mark.asyncio
    async def test_positions_export_target_currency_price_per_single_unit(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(
            monkeypatch,
            _report(
                scope,
                holdings=(
                    _holding(
                        1,
                        quantity=15000,
                        current_price=97.74,
                        current_value=14661,
                    ),
                ),
            ),
        )
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.positions_by_broker", required=True)

        assert envelope.payload["positions"][0]["unit_price"] == "0.9774"

    @pytest.mark.asyncio
    async def test_no_provider_assignment_yields_provenance_without_provider(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata(provider_code=None))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.provenance", required=True)

        assert envelope.payload["provider"] is None
        assert len(envelope.payload["valuation_source_semantics"]) == 3


# =============================================================================
# Per-broker rows + deterministic ordering + cardinality across detail levels
# =============================================================================


class TestPerBrokerRowsAndCardinality:
    @pytest.mark.asyncio
    async def test_position_scope_and_positions_by_broker_retain_one_row_per_broker(self, monkeypatch):
        scope = _scope()
        # Deliberately unsorted broker order in the source holdings.
        holdings = [_holding(3, quantity=1), _holding(1, quantity=2), _holding(2, quantity=3)]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        scope_envelope = await context.resolve("asset.position_scope", required=True)
        positions_envelope = await context.resolve("asset.positions_by_broker", required=True)

        assert [b["broker_id"] for b in scope_envelope.payload["brokers"]] == [1, 2, 3]
        assert [p["broker_id"] for p in positions_envelope.payload["positions"]] == [1, 2, 3]
        assert scope_envelope.payload["broker_count"] == 3

    @pytest.mark.asyncio
    async def test_cardinality_identical_across_every_detail_level(self, monkeypatch):
        holdings = [_holding(1), _holding(2), _holding(3)]
        for detail_level in (DetailLevel.COMPACT, DetailLevel.STANDARD, DetailLevel.FULL):
            scope = _scope(detail_level=detail_level)
            _patch_metadata(monkeypatch, _metadata())
            _patch_report(monkeypatch, _report(scope, holdings=holdings))
            context = _make_context(scope, _make_async_session())

            scope_envelope = await context.resolve("asset.position_scope", required=True)
            positions_envelope = await context.resolve("asset.positions_by_broker", required=True)
            cost_value_envelope = await context.resolve("asset.cost_value_pl", required=True)

            assert len(scope_envelope.payload["brokers"]) == 3
            assert len(positions_envelope.payload["positions"]) == 3
            assert len(cost_value_envelope.payload["brokers"]) == 3


# =============================================================================
# Valuation semantics: observed market price vs WAC/cost
# =============================================================================


class TestValuationSemantics:
    @pytest.mark.asyncio
    async def test_market_snapshot_is_observed_price_not_wac(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        # Observed market close (60) deliberately differs from the broker's WAC (40).
        _patch_market_snapshot(monkeypatch, _price_results(observed_close=60))
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1, wac_per_unit=40, current_price=60, current_value=600)]))
        context = _make_context(scope, _make_async_session())

        snapshot_envelope = await context.resolve("asset.market_snapshot", required=True)
        cost_value_envelope = await context.resolve("asset.cost_value_pl", required=True)

        assert snapshot_envelope.payload["observed"]["native_price"]["amount"] == "60"
        assert snapshot_envelope.payload["converted_price"]["amount"] == "60"
        broker_row = cost_value_envelope.payload["brokers"][0]
        assert broker_row["wac_per_unit"] == "40"
        assert broker_row["cost_basis"] == "400"  # wac(40) * quantity(10), never the observed market price
        assert snapshot_envelope.payload["observed"]["native_price"]["amount"] != broker_row["wac_per_unit"]

    @pytest.mark.asyncio
    async def test_cost_value_pl_separates_cost_basis_current_value_and_gain_loss(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1, quantity=10, wac_per_unit=40, current_value=600, gain_loss=200, gain_loss_percent=50)]))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.cost_value_pl", required=True)

        broker_row = envelope.payload["brokers"][0]
        assert broker_row["cost_basis"] == "400"
        assert broker_row["current_value"] == "600"
        assert broker_row["unrealized_gain_loss"] == "200"
        assert envelope.payload["total_cost_basis"] == "400"
        assert envelope.payload["total_current_value"] == "600"
        assert envelope.payload["total_unrealized_gain_loss"] == "200"
        assert envelope.payload["coverage"] == {"total_broker_count": 1, "valued_broker_count": 1, "omitted": [], "is_complete": True}


# =============================================================================
# Cost/value/P&L coverage: never fabricate a partial aggregate as complete
# =============================================================================


class TestCostValuePlCoverage:
    @pytest.mark.asyncio
    async def test_missing_current_value_with_known_wac_does_not_fabricate_full_loss(self, monkeypatch):
        scope = _scope()
        # Broker 1 has a known WAC (cost basis is computable) but no current valuation at all
        # (e.g. missing FX rate) - it must NOT be treated as a total loss (current_value=0).
        holdings = [
            _holding(1, quantity=10, wac_per_unit=40, current_price=None, current_value=None, gain_loss=None, gain_loss_percent=None, valuation_source="MISSING"),
            _holding(2, quantity=5, wac_per_unit=20, current_price=30, current_value=150, gain_loss=50, gain_loss_percent=50),
        ]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.cost_value_pl", required=True)

        # Both broker rows are always retained...
        assert [b["broker_id"] for b in envelope.payload["brokers"]] == [1, 2]
        # ...but the aggregate only reflects broker 2's fully-valued row - broker 1's
        # known 400 cost basis is never combined with an implicit 0 current value.
        assert envelope.payload["total_cost_basis"] == "100"  # 20 * 5, broker 2 only
        assert envelope.payload["total_current_value"] == "150"  # broker 2 only
        assert envelope.payload["total_unrealized_gain_loss"] == "50"  # broker 2's own gain_loss, never recomputed
        coverage = envelope.payload["coverage"]
        assert coverage["total_broker_count"] == 2
        assert coverage["valued_broker_count"] == 1
        assert coverage["is_complete"] is False
        assert coverage["omitted"] == [{"broker_id": 1, "missing_fields": ["current_value", "unrealized_gain_loss"]}]

    @pytest.mark.asyncio
    async def test_current_value_with_missing_cost_basis_is_omitted_from_totals(self, monkeypatch):
        scope = _scope()
        # Broker 1 is missing wac_per_unit (no FX rate) so cost_basis cannot be derived,
        # even though it does carry a current_value/gain_loss.
        holdings = [
            _holding(1, quantity=10, wac_per_unit=None, current_price=60, current_value=600, gain_loss=100, gain_loss_percent=None),
            _holding(2, quantity=5, wac_per_unit=20, current_price=30, current_value=150, gain_loss=50, gain_loss_percent=50),
        ]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.cost_value_pl", required=True)

        assert len(envelope.payload["brokers"]) == 2  # both rows retained
        assert envelope.payload["total_cost_basis"] == "100"
        assert envelope.payload["total_current_value"] == "150"
        assert envelope.payload["total_unrealized_gain_loss"] == "50"
        coverage = envelope.payload["coverage"]
        assert coverage["valued_broker_count"] == 1
        assert coverage["omitted"] == [{"broker_id": 1, "missing_fields": ["cost_basis"]}]

    @pytest.mark.asyncio
    async def test_no_fully_valued_rows_totals_are_none_not_zero(self, monkeypatch):
        scope = _scope()
        holdings = [_holding(1, wac_per_unit=None, current_value=None, gain_loss=None, gain_loss_percent=None, current_price=None, valuation_source="MISSING")]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.cost_value_pl", required=True)

        assert envelope.payload["total_cost_basis"] is None
        assert envelope.payload["total_current_value"] is None
        assert envelope.payload["total_unrealized_gain_loss"] is None
        coverage = envelope.payload["coverage"]
        assert coverage["total_broker_count"] == 1
        assert coverage["valued_broker_count"] == 0
        assert coverage["is_complete"] is False


# =============================================================================
# Performance over the unified scope period
# =============================================================================


class TestPerformance:
    @pytest.mark.asyncio
    async def test_performance_aggregates_engine_contributions_over_the_scope_period(self, monkeypatch):
        scope = _scope(period_start=date(2026, 2, 1), period_end=date(2026, 2, 28))
        contributions = PositionsContribution(positions=[_contribution(1, start_value=1000, end_value=1100, period_pnl=100), _contribution(2, start_value=500, end_value=600, period_pnl=100)])
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1), _holding(2)], contribution=contributions))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.performance", required=True)

        assert envelope.payload["period"] == {"start": "2026-02-01", "end": "2026-02-28"}
        assert len(envelope.payload["brokers"]) == 2
        assert envelope.payload["total_start_value"] == "1500"
        assert envelope.payload["total_end_value"] == "1700"
        assert envelope.payload["total_period_pnl"] == "200"
        assert envelope.payload["zero_semantics"].startswith("The Portfolio Engine omits zero-valued")
        # Same ratio formula the engine already uses per-broker (period_pnl / |start_value|), applied once at the aggregate level.
        assert Decimal(envelope.payload["total_period_pnl_percent"]) == Decimal("200") / Decimal("1500")
        assert envelope.payload["coverage"] == {"total_broker_count": 2, "valued_broker_count": 2, "omitted": [], "is_complete": True}

    @pytest.mark.asyncio
    async def test_engine_omitted_zero_contribution_fields_render_as_recorded_zero(self, monkeypatch):
        scope = _scope(period_start=date(2026, 2, 1), period_end=date(2026, 2, 28))
        contribution = _contribution(1).model_copy(
            update={
                "period_realized_gain_loss": None,
                "period_income": None,
                "period_fees_taxes": None,
            }
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1)], contribution=PositionsContribution(positions=[contribution])))
        context = _make_context(scope, _make_async_session())

        row = (await context.resolve("asset.performance", required=True)).payload["brokers"][0]

        assert row["period_realized_gain_loss"] == "0"
        assert row["period_income"] == "0"
        assert row["period_fees_taxes"] == "0"


# =============================================================================
# Performance coverage: never let a missing field distort numerator/denominator
# =============================================================================


class TestPerformanceCoverage:
    @pytest.mark.asyncio
    async def test_missing_start_value_does_not_inflate_aggregate_percent(self, monkeypatch):
        scope = _scope(period_start=date(2026, 2, 1), period_end=date(2026, 2, 28))
        # Broker 1 has a period P&L but no start_value (e.g. a mid-period opening whose
        # opening valuation could not be reconstructed) - it must not silently contribute
        # its P&L to the numerator while its start_value is dropped from the denominator.
        contributions = PositionsContribution(
            positions=[
                _contribution(1, start_value=None, end_value=300, period_pnl=300),
                _contribution(2, start_value=1000, end_value=1100, period_pnl=100),
            ]
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1), _holding(2)], contribution=contributions))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.performance", required=True)

        assert len(envelope.payload["brokers"]) == 2  # both broker rows retained
        # Aggregate reflects broker 2 only - broker 1's 300 P&L never distorts the ratio.
        assert envelope.payload["total_start_value"] == "1000"
        assert envelope.payload["total_period_pnl"] == "100"
        assert Decimal(envelope.payload["total_period_pnl_percent"]) == Decimal("100") / Decimal("1000")
        coverage = envelope.payload["coverage"]
        assert coverage["total_broker_count"] == 2
        assert coverage["valued_broker_count"] == 1
        assert coverage["is_complete"] is False
        assert coverage["omitted"] == [{"broker_id": 1, "missing_fields": ["start_value"]}]

    @pytest.mark.asyncio
    async def test_no_fully_valued_rows_totals_and_percent_are_none(self, monkeypatch):
        scope = _scope()
        contributions = PositionsContribution(positions=[_contribution(1, start_value=None, end_value=None, period_pnl=None)])
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1)], contribution=contributions))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.performance", required=True)

        assert envelope.payload["total_start_value"] is None
        assert envelope.payload["total_end_value"] is None
        assert envelope.payload["total_period_pnl"] is None
        assert envelope.payload["total_period_pnl_percent"] is None
        coverage = envelope.payload["coverage"]
        assert coverage["valued_broker_count"] == 0
        assert coverage["is_complete"] is False


# =============================================================================
# Lot detail: period cutoff, local audit refs, no database identifiers, no limit
# =============================================================================


class TestLotDetail:
    @pytest.mark.asyncio
    async def test_open_lot_and_recently_closed_lot_are_included_older_closed_lot_excluded(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        lots = [
            _lot(lot_id=1, closing_date=None, open_quantity=10),  # still open -> included
            _lot(lot_id=2, closing_date=date(2026, 1, 15), open_quantity=0),  # closed within period -> included
            _lot(lot_id=3, closing_date=date(2025, 12, 1), open_quantity=0),  # closed before period_start -> excluded
        ]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        _patch_lots(monkeypatch, _lots_response(scope, lots))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.lot_detail", required=True)

        assert len(envelope.payload["lots"]) == 2
        assert envelope.payload["cost_allocation_semantics"].startswith("Lot fees and taxes include only costs deterministically allocated")
        open_quantities = sorted(row["open_quantity"] for row in envelope.payload["lots"])
        assert open_quantities == ["0", "10"]  # lot 1 (open) and lot 2 (closed in-period) retained, lot 3 excluded
        assert all(row["original_cost"] == "1000" for row in envelope.payload["lots"])
        assert all(row["allocated_fees"] == "0" for row in envelope.payload["lots"])
        assert all(row["allocated_taxes"] == "0" for row in envelope.payload["lots"])
        assert all(row["closing_date"] is None or row["closing_date"] >= "2026-01-01" for row in envelope.payload["lots"])
        assert [row["lot_ref"] for row in envelope.payload["lots"]] == ["L1", "L2"]

    @pytest.mark.asyncio
    async def test_lot_rows_carry_no_lot_or_transaction_identifiers(self):
        assert "lot_id" not in AssetLotDetailRow.model_fields
        assert "opening_transaction_id" not in AssetLotDetailRow.model_fields
        assert "transaction_id" not in AssetLotDetailRow.model_fields
        assert "lot_ref" in AssetLotDetailRow.model_fields
        assert "lot_id" not in AssetLotCustodyRow.model_fields
        assert "transaction_id" not in AssetLotCustodyRow.model_fields

    @pytest.mark.asyncio
    async def test_no_top_n_truncation_every_qualifying_lot_is_retained(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        lots = [_lot(lot_id=i, closing_date=None, open_quantity=1) for i in range(1, 13)]  # 12 open lots, well above any 7+3/top-N cap
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        _patch_lots(monkeypatch, _lots_response(scope, lots))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.lot_detail", required=True)

        assert len(envelope.payload["lots"]) == 12

    @pytest.mark.asyncio
    async def test_empty_lots_is_a_valid_result_not_a_failure(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        _patch_lots(monkeypatch, _lots_response(scope, []))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.lot_detail", required=True)

        assert envelope.payload["lots"] == []

    @pytest.mark.asyncio
    async def test_closed_lot_missing_closing_date_is_omitted_not_treated_as_open(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        lots = [
            _lot(lot_id=1, closing_date=None, open_quantity=0),  # fully closed (open_quantity==0) but no authoritative closing_date -> data-quality problem
            _lot(lot_id=2, closing_date=None, open_quantity=5),  # genuinely open -> retained
        ]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        _patch_lots(monkeypatch, _lots_response(scope, lots))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.lot_detail", required=True)

        # The degraded (closed, null-closing-date) lot is omitted, never silently kept as open...
        assert len(envelope.payload["lots"]) == 1
        assert envelope.payload["lots"][0]["open_quantity"] == "5"
        # ...and the omission is surfaced as a count, never a lot/transaction identifier.
        assert envelope.payload["omitted_degraded_lot_count"] == 1

    @pytest.mark.asyncio
    async def test_partially_closed_lot_is_retained_regardless_of_closing_date(self, monkeypatch):
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        # open_quantity > 0 with realized_quantity > 0 (PARTIALLY_CLOSED per FifoEngineResult.get_lot_states())
        # must be retained the same as a fully OPEN lot - eligibility is driven by open_quantity, not closing_date.
        lots = [_lot(lot_id=1, closing_date=None, original_quantity=10, open_quantity=4)]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        _patch_lots(monkeypatch, _lots_response(scope, lots))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.lot_detail", required=True)

        assert len(envelope.payload["lots"]) == 1
        assert envelope.payload["omitted_degraded_lot_count"] == 0


# =============================================================================
# Optional lot failure fails soft, no placeholder leaks
# =============================================================================


class TestOptionalLotFailureFailsSoft:
    @pytest.mark.asyncio
    async def test_lot_detail_failure_is_isolated_when_resolved_as_optional(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=[_holding(1)]))
        _patch_lots(monkeypatch, RuntimeError("lots analysis backend unavailable"))
        context = _make_context(scope, _make_async_session())

        result = await context.resolve("asset.lot_detail", required=False)

        assert result is None
        assert any(d.component_id == "asset.lot_detail" for d in context.diagnostics)

        # An unrelated required component in the same request still succeeds -
        # the lot failure never leaks a placeholder or breaks sibling components.
        positions_envelope = await context.resolve("asset.positions_by_broker", required=True)
        assert len(positions_envelope.payload["positions"]) == 1


# =============================================================================
# Memoization: one report/metadata load shared across every component
# =============================================================================


class TestMemoization:
    @pytest.mark.asyncio
    async def test_single_report_load_shared_across_every_dependent_component(self, monkeypatch):
        scope = _scope()
        holdings = [_holding(1)]
        contributions = PositionsContribution(positions=[_contribution(1)])
        metadata_calls = _patch_metadata(monkeypatch, _metadata())
        report_calls = _patch_report(monkeypatch, _report(scope, holdings=holdings, contribution=contributions))
        context = _make_context(scope, _make_async_session())

        for component_id in ("asset.position_scope", "asset.positions_by_broker", "asset.cost_value_pl", "asset.performance"):
            await context.resolve(component_id, required=True)

        assert len(report_calls) == 1
        assert len(metadata_calls) == 1

    @pytest.mark.asyncio
    async def test_single_metadata_load_shared_across_all_eight_components(self, monkeypatch):
        scope = _scope()
        holdings = [_holding(1)]
        metadata_calls = _patch_metadata(monkeypatch, _metadata())
        _patch_market_snapshot(monkeypatch, _price_results(observed_close=50))
        _patch_report(monkeypatch, _report(scope, holdings=holdings, contribution=PositionsContribution(positions=[_contribution(1)])))
        _patch_lots(monkeypatch, _lots_response(scope, []))
        context = _make_context(scope, _make_async_session())

        for component_id in (
            "asset.identity",
            "asset.market_snapshot",
            "asset.position_scope",
            "asset.provenance",
            "asset.positions_by_broker",
            "asset.cost_value_pl",
            "asset.performance",
            "asset.lot_detail",
        ):
            await context.resolve(component_id, required=True)

        assert len(metadata_calls) == 1


# =============================================================================
# Malicious free text remains inert data
# =============================================================================


class TestMaliciousTextRemainsData:
    @pytest.mark.asyncio
    async def test_short_description_is_passed_through_verbatim(self, monkeypatch):
        scope = _scope()
        payload_text = "<script>alert('xss')</script>; DROP TABLE assets; --"
        _patch_metadata(monkeypatch, _metadata(short_description=payload_text))
        context = _make_context(scope, _make_async_session())

        envelope = await context.resolve("asset.identity", required=True)

        assert envelope.payload["classification"]["short_description"] == payload_text


# =============================================================================
# Deterministic output
# =============================================================================


class TestDeterministicOutput:
    @pytest.mark.asyncio
    async def test_same_inputs_produce_identical_payloads_across_independent_builds(self, monkeypatch):
        scope = _scope()
        holdings = [_holding(2), _holding(1)]
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))

        context_a = _make_context(scope, _make_async_session())
        context_b = _make_context(scope, _make_async_session())

        envelope_a = await context_a.resolve("asset.position_scope", required=True)
        envelope_b = await context_b.resolve("asset.position_scope", required=True)

        assert envelope_a.payload == envelope_b.payload


# =============================================================================
# Portfolio-role basis (asset.position_scope) — deterministic weight/role data
# =============================================================================


def _role(envelope) -> dict:
    """Extracts the serialized `portfolio_role` object from a position_scope envelope."""
    role = envelope.payload["portfolio_role"]
    assert role is not None
    return role


class TestPortfolioRoleBasis:
    @pytest.mark.asyncio
    async def test_single_broker_whole_portfolio_asset_is_full_weight(self, monkeypatch):
        scope = _scope()
        # Only this asset is held -> it IS the whole portfolio (ratio == 1).
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=(_holding(1, current_value=500),)))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["broker_scope_mode"] == "WHOLE_ACCESSIBLE_PORTFOLIO"
        assert role["target_currency"] == CURRENCY
        assert role["valuation_basis"] == "current_market_value"
        assert role["denominator_basis"] == "gross_absolute_open_position_value"
        assert role["asset_market_value"] == "500"
        assert role["asset_gross_absolute_value"] == "500"
        assert role["portfolio_gross_absolute_value"] == "500"
        assert role["portfolio_weight_ratio"] == "1"
        assert role["position_leg_count"] == 1
        assert role["broker_count"] == 1
        assert role["unavailable"] == []

    @pytest.mark.asyncio
    async def test_multi_broker_duplicate_asset_legs_aggregated_once(self, monkeypatch):
        scope = _scope()
        # Same asset across three brokers + one unrelated asset leg in the portfolio.
        holdings = (
            _holding(1, current_value=200),
            _holding(2, current_value=300),
            _holding(3, current_value=500),
            _holding(1, asset_id=99, current_value=1000),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        # Asset legs aggregated once: 200 + 300 + 500.
        assert role["asset_market_value"] == "1000"
        assert role["asset_gross_absolute_value"] == "1000"
        assert role["position_leg_count"] == 3
        assert role["broker_count"] == 3
        # Denominator spans the whole scoped portfolio incl. the unrelated asset.
        assert role["portfolio_gross_absolute_value"] == "2000"
        assert role["portfolio_weight_ratio"] == "0.5"

    @pytest.mark.asyncio
    async def test_scoped_vs_whole_portfolio_denominator(self, monkeypatch):
        # Whole portfolio: asset (500) + other (1500) -> ratio 0.25.
        whole_holdings = (_holding(1, current_value=500), _holding(2, asset_id=99, current_value=1500))
        scope_whole = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope_whole, holdings=whole_holdings))
        context_whole = _make_context(scope_whole, _make_async_session())
        role_whole = _role(await context_whole.resolve("asset.position_scope", required=True))

        assert role_whole["broker_scope_mode"] == "WHOLE_ACCESSIBLE_PORTFOLIO"
        assert role_whole["portfolio_gross_absolute_value"] == "2000"
        assert role_whole["portfolio_weight_ratio"] == "0.25"

        # Broker-scoped: PortfolioService returns only broker 1's leg (the asset).
        scope_scoped = _scope(broker_scope=(1,))
        _patch_report(monkeypatch, _report(scope_scoped, holdings=(_holding(1, current_value=500),)))
        context_scoped = _make_context(scope_scoped, _make_async_session())
        role_scoped = _role(await context_scoped.resolve("asset.position_scope", required=True))

        assert role_scoped["broker_scope_mode"] == "SCOPED_BROKERS"
        assert role_scoped["portfolio_gross_absolute_value"] == "500"
        assert role_scoped["portfolio_weight_ratio"] == "1"

    @pytest.mark.asyncio
    async def test_short_negative_values_use_gross_absolute_semantics(self, monkeypatch):
        scope = _scope()
        # A short/negative leg for another asset must contribute its magnitude,
        # never cancel the asset's long value in the denominator.
        holdings = (
            _holding(1, quantity=10, current_value=600),
            _holding(2, asset_id=99, quantity=-4, current_value=-400),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["asset_market_value"] == "600"
        assert role["asset_gross_absolute_value"] == "600"
        # Gross absolute denominator = |600| + |-400| = 1000 (not net 200).
        assert role["portfolio_gross_absolute_value"] == "1000"
        assert role["portfolio_weight_ratio"] == "0.6"

    @pytest.mark.asyncio
    async def test_asset_own_short_leg_nets_value_but_gross_is_magnitude(self, monkeypatch):
        scope = _scope()
        # This asset itself has a long and a short leg across brokers.
        holdings = (
            _holding(1, quantity=10, current_value=500),
            _holding(2, quantity=-3, current_value=-150),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["asset_market_value"] == "350"  # net 500 + (-150)
        assert role["asset_gross_absolute_value"] == "650"  # |500| + |-150|
        assert role["portfolio_gross_absolute_value"] == "650"
        assert role["position_leg_count"] == 2
        assert role["broker_count"] == 2

    @pytest.mark.asyncio
    async def test_empty_portfolio_ratio_unavailable_not_zero(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=()))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["asset_market_value"] == "0"
        assert role["portfolio_gross_absolute_value"] == "0"
        assert role["portfolio_weight_ratio"] is None
        assert role["position_leg_count"] == 0
        assert role["broker_count"] == 0
        reasons = {u["field"]: u["reason"] for u in role["unavailable"]}
        assert "portfolio_weight_ratio" in reasons
        assert "zero" in reasons["portfolio_weight_ratio"].lower()

    @pytest.mark.asyncio
    async def test_missing_asset_valuation_yields_unavailable_reason_not_zero(self, monkeypatch):
        scope = _scope()
        # One of the asset's legs has no current_value.
        holdings = (
            _holding(1, current_value=500),
            _holding(2, current_value=None),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["asset_market_value"] is None
        assert role["asset_gross_absolute_value"] is None
        assert role["portfolio_weight_ratio"] is None
        # Leg count still reflects both brokers hold the asset.
        assert role["position_leg_count"] == 2
        reasons = {u["field"]: u["reason"] for u in role["unavailable"]}
        assert "asset_market_value" in reasons
        assert "portfolio_weight_ratio" in reasons

    @pytest.mark.asyncio
    async def test_missing_portfolio_leg_valuation_breaks_denominator_only(self, monkeypatch):
        scope = _scope()
        # This asset is fully valued, but an unrelated portfolio leg is not.
        holdings = (
            _holding(1, current_value=500),
            _holding(3, asset_id=99, current_value=None),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert role["asset_market_value"] == "500"
        assert role["asset_gross_absolute_value"] == "500"
        assert role["portfolio_gross_absolute_value"] is None
        assert role["portfolio_weight_ratio"] is None
        reasons = {u["field"]: u["reason"] for u in role["unavailable"]}
        assert "portfolio_gross_absolute_value" in reasons
        assert "portfolio_weight_ratio" in reasons

    @pytest.mark.asyncio
    async def test_ratio_reconciles_with_numerator_and_denominator(self, monkeypatch):
        scope = _scope()
        holdings = (
            _holding(1, current_value=333),
            _holding(2, asset_id=99, current_value=667),
        )
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        numerator = Decimal(role["asset_gross_absolute_value"])
        denominator = Decimal(role["portfolio_gross_absolute_value"])
        ratio = Decimal(role["portfolio_weight_ratio"])
        # Backend precomputes the ratio; it reconciles with the exposed basis.
        assert numerator == Decimal("333")
        assert denominator == Decimal("1000")
        assert ratio == numerator / denominator

    @pytest.mark.asyncio
    async def test_ratio_is_precomputed_backend_value_no_frontend_calc(self, monkeypatch):
        scope = _scope()
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(
            monkeypatch,
            _report(scope, holdings=(_holding(1, current_value=250), _holding(2, asset_id=99, current_value=750))),
        )
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        # Every value a renderer needs is already present as data (string
        # Decimal / int), so the frontend never has to compute the weight.
        assert isinstance(role["portfolio_weight_ratio"], str)
        assert role["portfolio_weight_ratio"] == "0.25"
        assert isinstance(role["position_leg_count"], int)
        assert isinstance(role["broker_count"], int)

    @pytest.mark.asyncio
    async def test_denominator_delegates_user_and_broker_access_to_portfolio_service(self, monkeypatch):
        # The portfolio denominator is only ever what PortfolioService returns
        # for this user_id + broker scope, so access control is never bypassed.
        scope = _scope(user_id=7, broker_scope=(1, 2))
        _patch_metadata(monkeypatch, _metadata())
        captured: dict = {}

        async def _fake_get_report(self, user_id, query):  # noqa: ARG001
            captured["user_id"] = user_id
            captured["broker_ids"] = query.broker_ids
            return _report(scope, holdings=(_holding(1, current_value=500),))

        monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
        context = _make_context(scope, _make_async_session())

        role = _role(await context.resolve("asset.position_scope", required=True))

        assert captured["user_id"] == 7
        assert captured["broker_ids"] == [1, 2]
        assert role["broker_scope_mode"] == "SCOPED_BROKERS"
        assert role["portfolio_gross_absolute_value"] == "500"

    @pytest.mark.asyncio
    async def test_role_deterministic_across_independent_builds(self, monkeypatch):
        scope = _scope()
        holdings = (_holding(2, current_value=300), _holding(1, current_value=200), _holding(3, asset_id=99, current_value=500))
        _patch_metadata(monkeypatch, _metadata())
        _patch_report(monkeypatch, _report(scope, holdings=holdings))

        context_a = _make_context(scope, _make_async_session())
        context_b = _make_context(scope, _make_async_session())
        role_a = _role(await context_a.resolve("asset.position_scope", required=True))
        role_b = _role(await context_b.resolve("asset.position_scope", required=True))

        assert role_a == role_b
