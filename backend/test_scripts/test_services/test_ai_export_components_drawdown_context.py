"""Behavioral tests for the isolated AI Export drawdown context components.

Covers the ``ai-adequacy-v1-drawdown-export`` contract: Risk request parameters
(scope kind, broker filter, target currency, mode, analytic code), asset native
currency basis, TWRR pass-through for Portfolio/Broker, deterministic ratio
semantics, honest unavailable/failed payloads, request-scoped caching (Risk runs
at most once), and catalog wiring (component/dataset/analysis counts + optional
mappings). ``RiskService`` is stubbed so these tests are deterministic and never
touch the real risk engine (which is separately reviewed and green).
"""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.ai_export.components.drawdown_context as drawdown_module
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskDrawdownOutput,
    RiskDrawdownRecoveryStatus,
    RiskError,
    RiskErrorCode,
    RiskMode,
    RiskQueryResponse,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.ai_export.analyses.catalog import EXPECTED_ANALYSIS_COUNT, build_analysis_registry
from backend.app.services.ai_export.components.asset_payloads import AssetMarketSnapshotPayload, AssetPriceObservation
from backend.app.services.ai_export.components.catalog import ALL_COMPONENTS, build_component_registry
from backend.app.services.ai_export.components.drawdown_context import (
    REASON_NO_NATIVE_PRICE,
    DrawdownContextPayload,
    DrawdownContextStatus,
    PortfolioAssetDrawdownSnapshotPayload,
    _asset_drawdown_row,
    _build_asset_drawdown,
    _build_broker_drawdown,
    _build_portfolio_drawdown,
)
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.datasets.catalog import EXPECTED_DATASET_COUNT, build_dataset_registry
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope

PERIOD_START = date(2024, 1, 1)
PERIOD_END = date(2024, 12, 31)


# =============================================================================
# Test doubles
# =============================================================================


class _FakeRiskService:
    """Records the single execute call and returns a caller-supplied response."""

    captured: list[dict] = []
    response_factory = None  # set per test

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def execute(self, *, user_id: int, request) -> RiskQueryResponse:
        _FakeRiskService.captured.append({"user_id": user_id, "request": request})
        assert _FakeRiskService.response_factory is not None
        return _FakeRiskService.response_factory(request)


def _drawdown_output(*, return_basis: RiskReturnBasis, calculation_basis: str) -> RiskDrawdownOutput:
    return RiskDrawdownOutput(
        current_drawdown=-0.08,
        current_peak_date=date(2024, 10, 1),
        current_drawdown_duration_days=30,
        maximum_drawdown=-0.20,
        maximum_drawdown_peak_date=date(2024, 3, 1),
        maximum_drawdown_trough_date=date(2024, 5, 1),
        maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus.RECOVERED,
        maximum_drawdown_recovery_date=date(2024, 7, 1),
        maximum_drawdown_duration_days=120,
        maximum_drawdown_recovered_ratio=1.0,
        remaining_to_peak_ratio=0.087,
        available_start=PERIOD_START,
        available_end=PERIOD_END,
        n_observations=250,
        coverage=0.95,
        calculation_basis=calculation_basis,
        return_basis=return_basis,
    )


def _ok_result(output: RiskDrawdownOutput, *, warnings: list[RiskWarning] | None = None, status: RiskResultStatus = RiskResultStatus.OK) -> RiskAnalyticResult:
    # model_construct: bypass the success-requires-metadata/data_quality validator;
    # the component only reads status/output/error/warnings.
    return RiskAnalyticResult.model_construct(
        instance_id="ai_export_drawdown_context",
        analytic_code="drawdown_summary",
        status=status,
        output=output,
        metadata=None,
        data_quality=DataQualityReport(),
        warnings=list(warnings or []),
        error=None,
    )


def _unavailable_result(*, code: RiskErrorCode, message: str, status: RiskResultStatus = RiskResultStatus.UNAVAILABLE) -> RiskAnalyticResult:
    return RiskAnalyticResult(
        instance_id="ai_export_drawdown_context",
        analytic_code="drawdown_summary",
        status=status,
        error=RiskError(code=code, message=message),
    )


@pytest.fixture(autouse=True)
def _stub_risk_service(monkeypatch):
    _FakeRiskService.captured = []
    _FakeRiskService.response_factory = None
    monkeypatch.setattr(drawdown_module, "RiskService", _FakeRiskService)
    yield


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s


def _context(session: AsyncSession, scope: BuildScope) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


def _portfolio_scope(*, broker_scope: tuple[int, ...] = (), target: str = "EUR") -> BuildScope:
    return BuildScope(
        request_id="req-portfolio-drawdown",
        user_id=42,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=target,
        broker_scope=broker_scope,
    )


def _broker_scope(*, broker_id: int, target: str = "EUR") -> BuildScope:
    return BuildScope(
        request_id="req-broker-drawdown",
        user_id=42,
        domain=Domain.BROKER,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=target,
        broker_scope=(broker_id,),
        broker_id=broker_id,
    )


def _asset_scope(*, asset_id: int, target: str = "EUR") -> BuildScope:
    return BuildScope(
        request_id="req-asset-drawdown",
        user_id=42,
        domain=Domain.ASSET,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency=target,
        asset_id=asset_id,
    )


def _market_snapshot_envelope(*, native_currency: str | None) -> SectionEnvelope:
    observed = None
    if native_currency is not None:
        observed = AssetPriceObservation(date=PERIOD_END, native_price=Currency(code=native_currency, amount="123.45"), source_plugin_key="yfinance")
    payload = AssetMarketSnapshotPayload(asset_id=7, as_of_date=PERIOD_END, target_currency="EUR", observed=observed)
    return SectionEnvelope(
        component_id="asset.market_snapshot",
        component_version=1,
        schema_id="asset.market_snapshot",
        schema_version=1,
        payload=payload.model_dump(mode="json"),
    )


# =============================================================================
# Portfolio
# =============================================================================


class TestPortfolioDrawdown:
    @pytest.mark.asyncio
    async def test_portfolio_request_parameters_and_twrr_passthrough(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(_drawdown_output(return_basis=RiskReturnBasis.TWRR, calculation_basis="historical_twrr"))])
        context = _context(session, _portfolio_scope(target="EUR"))
        payload = await _build_portfolio_drawdown(context, {})

        assert len(_FakeRiskService.captured) == 1
        call = _FakeRiskService.captured[0]
        request = call["request"]
        assert call["user_id"] == 42
        assert request.scope.kind == RiskScopeKind.PORTFOLIO
        assert request.scope.broker_ids is None
        assert request.target_currency == "EUR"
        assert request.mode == RiskMode.HISTORICAL
        assert [a.analytic_code for a in request.analytics] == ["drawdown_summary"]
        assert request.date_range.start == PERIOD_START and request.date_range.end == PERIOD_END

        assert payload.status == DrawdownContextStatus.OK
        assert payload.return_basis == "twrr"
        assert payload.calculation_basis == "historical_twrr"
        assert payload.calculation_currency == "EUR"

    @pytest.mark.asyncio
    async def test_ratio_semantics_are_verbatim_from_risk(self, session):
        output = _drawdown_output(return_basis=RiskReturnBasis.TWRR, calculation_basis="historical_twrr")
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(output)])
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})

        assert payload.current_drawdown_ratio == output.current_drawdown
        assert payload.maximum_drawdown_ratio == output.maximum_drawdown
        assert payload.maximum_drawdown_recovered_ratio == output.maximum_drawdown_recovered_ratio
        assert payload.remaining_to_peak_ratio == output.remaining_to_peak_ratio
        assert payload.coverage_ratio == output.coverage
        assert payload.n_observations == output.n_observations
        assert payload.maximum_drawdown_recovery_status == RiskDrawdownRecoveryStatus.RECOVERED.value
        assert payload.current_peak_date == output.current_peak_date

    @pytest.mark.asyncio
    async def test_risk_runs_at_most_once_per_request(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(_drawdown_output(return_basis=RiskReturnBasis.TWRR, calculation_basis="historical_twrr"))])
        context = _context(session, _portfolio_scope())
        first = await _build_portfolio_drawdown(context, {})
        second = await _build_portfolio_drawdown(context, {})
        assert len(_FakeRiskService.captured) == 1
        assert first.model_dump() == second.model_dump()

    @pytest.mark.asyncio
    async def test_warnings_are_carried_on_partial(self, session):
        warnings = [RiskWarning(code="coverage_degraded", message="Coverage below target")]
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(_drawdown_output(return_basis=RiskReturnBasis.TWRR, calculation_basis="historical_twrr"), warnings=warnings, status=RiskResultStatus.PARTIAL)])
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})
        assert payload.status == DrawdownContextStatus.PARTIAL
        assert payload.warnings == ("coverage_degraded: Coverage below target",)


# =============================================================================
# Broker
# =============================================================================


class TestBrokerDrawdown:
    @pytest.mark.asyncio
    async def test_broker_request_uses_exact_selected_broker_filter(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(_drawdown_output(return_basis=RiskReturnBasis.TWRR, calculation_basis="historical_twrr"))])
        payload = await _build_broker_drawdown(_context(session, _broker_scope(broker_id=9)), {})
        request = _FakeRiskService.captured[0]["request"]
        assert request.scope.kind == RiskScopeKind.PORTFOLIO
        assert request.scope.broker_ids == [9]
        assert payload.status == DrawdownContextStatus.OK
        assert payload.return_basis == "twrr"


# =============================================================================
# Asset
# =============================================================================


class TestAssetDrawdown:
    @pytest.mark.asyncio
    async def test_asset_request_uses_native_price_currency(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_ok_result(_drawdown_output(return_basis=RiskReturnBasis.PRICE_ONLY, calculation_basis="price_only_close"))])
        deps = {"asset.market_snapshot": _market_snapshot_envelope(native_currency="USD")}
        payload = await _build_asset_drawdown(_context(session, _asset_scope(asset_id=7, target="EUR")), deps)

        request = _FakeRiskService.captured[0]["request"]
        assert request.scope.kind == RiskScopeKind.ASSET
        assert request.scope.asset_id == 7
        # native price currency (USD), NOT the portfolio target currency (EUR)
        assert request.target_currency == "USD"
        assert payload.status == DrawdownContextStatus.OK
        assert payload.return_basis == "price_only"
        assert payload.calculation_basis == "price_only_close"
        assert payload.calculation_currency == "USD"

    @pytest.mark.asyncio
    async def test_asset_without_native_observation_is_unavailable_without_calling_risk(self, session):
        _FakeRiskService.response_factory = lambda request: pytest.fail("RiskService must not be called without a native observation")
        deps = {"asset.market_snapshot": _market_snapshot_envelope(native_currency=None)}
        payload = await _build_asset_drawdown(_context(session, _asset_scope(asset_id=7)), deps)
        assert payload.status == DrawdownContextStatus.UNAVAILABLE
        assert payload.reason_code == REASON_NO_NATIVE_PRICE
        assert payload.current_drawdown_ratio is None
        assert payload.coverage_ratio is None
        assert _FakeRiskService.captured == []

    @pytest.mark.asyncio
    async def test_asset_without_snapshot_dependency_is_unavailable(self, session):
        payload = await _build_asset_drawdown(_context(session, _asset_scope(asset_id=7)), {})
        assert payload.status == DrawdownContextStatus.UNAVAILABLE
        assert payload.reason_code == REASON_NO_NATIVE_PRICE


# =============================================================================
# Portfolio per-asset compact Drawdown snapshot
# =============================================================================


class TestPortfolioAssetDrawdownSnapshot:
    def test_uses_canonical_episode_math_without_history_rows(self):
        row = _asset_drawdown_row(
            asset_id=7,
            points=(
                (date(2024, 1, 1), 100.0),
                (date(2024, 6, 1), 80.0),
                (date(2024, 12, 31), 90.0),
            ),
            scope=_portfolio_scope(),
            calculation_currency="EUR",
        )

        assert row.current_drawdown_ratio == pytest.approx(-0.1)
        assert row.maximum_drawdown_ratio == pytest.approx(-0.2)
        assert row.maximum_drawdown_recovery_status == "open"
        assert row.remaining_to_peak_ratio == pytest.approx(1 / 9)
        assert row.n_observations == 3
        assert "history" not in PortfolioAssetDrawdownSnapshotPayload(rows=(row,)).model_dump()

    def test_sparse_asset_is_explicitly_unavailable(self):
        row = _asset_drawdown_row(
            asset_id=7,
            points=((date(2024, 12, 31), 90.0),),
            scope=_portfolio_scope(),
            calculation_currency="EUR",
        )

        assert row.status == DrawdownContextStatus.UNAVAILABLE
        assert row.reason_code == "insufficient_observed_prices"
        assert row.current_drawdown_ratio is None


# =============================================================================
# Unavailable / failed pass-through (no success-shaped fallback)
# =============================================================================


class TestHonestDegradation:
    @pytest.mark.asyncio
    async def test_unavailable_risk_result_becomes_unavailable_payload(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_unavailable_result(code=RiskErrorCode.INSUFFICIENT_HISTORY, message="Not enough returns")])
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})
        assert payload.status == DrawdownContextStatus.UNAVAILABLE
        assert payload.reason_code == RiskErrorCode.INSUFFICIENT_HISTORY.value
        assert payload.message == "Drawdown data is unavailable for the selected scope and period."
        assert payload.current_drawdown_ratio is None
        assert payload.calculation_basis is None

    @pytest.mark.asyncio
    async def test_failed_risk_result_becomes_failed_payload(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[_unavailable_result(code=RiskErrorCode.EXECUTION_FAILED, message="boom", status=RiskResultStatus.FAILED)])
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})
        assert payload.status == DrawdownContextStatus.FAILED
        assert payload.reason_code == RiskErrorCode.EXECUTION_FAILED.value

    @pytest.mark.asyncio
    async def test_risk_raising_becomes_failed_payload_not_a_build_failure(self, session):
        def _raise(request):
            raise RuntimeError("scope resolution exploded")

        _FakeRiskService.response_factory = _raise
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})
        assert payload.status == DrawdownContextStatus.FAILED
        assert payload.message == "Drawdown calculation could not be completed for the selected scope and period."

    @pytest.mark.asyncio
    async def test_empty_risk_response_becomes_failed_payload(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse.model_construct(items=[])
        payload = await _build_portfolio_drawdown(_context(session, _portfolio_scope()), {})
        assert payload.status == DrawdownContextStatus.FAILED


# =============================================================================
# Catalog wiring
# =============================================================================


class TestDrawdownCatalogWiring:
    def test_components_present_in_registry(self):
        registry = build_component_registry()
        for component_id, deps, output_model in (
            ("portfolio.drawdown_summary", (), DrawdownContextPayload),
            ("portfolio.asset_drawdown_snapshot", ("portfolio.asset_market_context",), PortfolioAssetDrawdownSnapshotPayload),
            ("broker.drawdown_summary", (), DrawdownContextPayload),
            ("asset.drawdown_summary", ("asset.market_snapshot",), DrawdownContextPayload),
        ):
            spec = registry.get(component_id)
            assert spec.output_model is output_model
            assert spec.version == 1
            assert spec.dependencies == deps

    def test_counts_are_67_40_24(self):
        assert len(ALL_COMPONENTS) == 67
        assert EXPECTED_DATASET_COUNT == 40
        assert len(build_dataset_registry()) == 40
        assert EXPECTED_ANALYSIS_COUNT == 24
        assert len(build_analysis_registry()) == 24

    def test_drawdown_datasets_excluded_from_all_data(self):
        registry = build_dataset_registry()
        for all_data_id, drawdown_id in (
            ("portfolio.all_data", "portfolio.drawdown_summary"),
            ("broker.all_data", "broker.drawdown_summary"),
            ("asset.all_data", "asset.drawdown_summary"),
        ):
            all_data = registry.get(all_data_id)
            assert drawdown_id not in all_data.section_order
            assert drawdown_id not in all_data.required_component_ids
            assert drawdown_id not in all_data.optional_component_ids

    def test_public_general_datasets_include_optional_drawdown_context(self):
        datasets = build_dataset_registry()
        assert "portfolio.drawdown_summary" in datasets.get("portfolio.overview_and_history").optional_component_ids
        assert "broker.drawdown_summary" in datasets.get("broker.overview_and_history").optional_component_ids
        assert "asset.drawdown_summary" in datasets.get("asset.position_and_history").optional_component_ids

        analyses = build_analysis_registry(datasets)
        assert analyses.get("portfolio.pac_planning").required_dataset_ids == ("portfolio.overview_and_history",)
        assert analyses.get("broker.review").required_dataset_ids == ("broker.overview_and_history",)
        assert analyses.get("asset.position_review").required_dataset_ids == ("asset.position_and_history",)
