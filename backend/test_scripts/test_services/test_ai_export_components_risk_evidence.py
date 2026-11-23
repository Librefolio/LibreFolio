"""The AI Export risk evidence of the portfolio (78 L8a): `portfolio.risk_concentration` and `portfolio.tail_risk`.

Covers the request the components send (today's holdings, 12 months up to the end of the period, the 95 % 30-day bad
month, the broker filter behind its one switch), the copy of the Risk results into the payloads (figures, measured
window, the holdings that shortened it, the holdings left out), the honest statuses (a Risk refusal is `unavailable`,
a Risk error is `failed`, never an exception), one Risk call for both sections, the payload invariants, and the
catalog wiring. `RiskService` is stubbed: the risk engine is reviewed and tested on its own.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.ai_export.components.risk_evidence as risk_evidence_module
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.risk.outputs import RiskContributionItem, RiskContributionOutput, RiskVarCvarOutput, RiskWorstHorizonWindow
from backend.app.schemas.risk.results import RiskAnalyticResult, RiskError, RiskExcludedAsset, RiskQueryResponse, RiskResultMetadata, RiskWarning
from backend.app.schemas.risk.vocabulary import RiskCompositionPolicy, RiskErrorCode, RiskMode, RiskResultStatus, RiskReturnBasis
from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.risk_evidence import (
    BAD_MONTH_SEMANTICS,
    REASON_RISK_ERROR,
    WEIGHT_BASIS,
    PortfolioRiskConcentrationPayload,
    PortfolioTailRiskPayload,
    RiskEvidenceStatus,
    _build_risk_concentration,
    _build_tail_risk,
)
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope

PERIOD_START = date(2026, 8, 23)
PERIOD_END = date(2026, 11, 23)
WINDOW_START = date(2025, 11, 23)
CONTRIBUTION_ID = "ai_export_risk_concentration"
BAD_MONTH_ID = "ai_export_bad_month"


# =============================================================================
# Test doubles
# =============================================================================


class _FakeRiskService:
    """Records every execute call and answers with the response the test sets (or raises)."""

    captured: list[dict] = []
    response_factory = None

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def execute(self, *, user_id: int, request) -> RiskQueryResponse:
        _FakeRiskService.captured.append({"user_id": user_id, "request": request})
        assert _FakeRiskService.response_factory is not None
        return _FakeRiskService.response_factory(request)


@pytest.fixture(autouse=True)
def _stub_risk_service(monkeypatch):
    _FakeRiskService.captured = []
    _FakeRiskService.response_factory = None
    monkeypatch.setattr(risk_evidence_module, "RiskService", _FakeRiskService)
    yield


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s


def _scope(*, broker_scope: tuple[int, ...] = ()) -> BuildScope:
    return BuildScope(
        request_id="req-portfolio-risk-evidence",
        user_id=42,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency="EUR",
        broker_scope=broker_scope,
    )


def _context(session: AsyncSession, scope: BuildScope) -> BuildContext:
    return BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)


def _metadata(*, analyzed_start: date = date(2025, 11, 24), excluded: tuple[RiskExcludedAsset, ...] = ()) -> RiskResultMetadata:
    # model_construct: the components read only these fields; the metadata validator is the Risk engine's concern.
    return RiskResultMetadata.model_construct(
        analyzed_range=DateRangeModel(start=analyzed_start, end=PERIOD_END),
        n_observations=250,
        calendar_days=364,
        annualization_factor=252.0,
        coverage=0.98,
        currency="EUR",
        composition_as_of=PERIOD_END,
        mode=RiskMode.CURRENT_COMPOSITION,
        return_basis=RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST,
        excluded_assets=list(excluded),
        algorithm_version="test",
        computed_at=datetime(2026, 11, 23, tzinfo=UTC),
    )


def _result(instance_id: str, code: str, output, *, warnings: list[RiskWarning] | None = None, metadata: RiskResultMetadata | None = None, status: RiskResultStatus = RiskResultStatus.OK) -> RiskAnalyticResult:
    return RiskAnalyticResult.model_construct(
        instance_id=instance_id,
        analytic_code=code,
        status=status,
        output=output,
        metadata=metadata or _metadata(),
        data_quality=DataQualityReport(),
        warnings=list(warnings or []),
        error=None,
    )


def _refused(instance_id: str, code: str, error_code: RiskErrorCode, status: RiskResultStatus = RiskResultStatus.UNAVAILABLE) -> RiskAnalyticResult:
    return RiskAnalyticResult(instance_id=instance_id, analytic_code=code, status=status, error=RiskError(code=error_code, message="refused"))


def _contribution() -> RiskContributionOutput:
    return RiskContributionOutput(
        portfolio_volatility=0.18,
        cash_weight=0.40,
        excluded_weight=0.05,
        effective_number_of_assets=2.6,
        diversification_ratio=1.3,
        items=[
            RiskContributionItem(asset_id=3, weight=0.10, marginal_contribution=0.1, component_contribution=0.01, percentage_contribution=0.05),
            RiskContributionItem(asset_id=1, weight=0.30, marginal_contribution=0.2, component_contribution=0.06, percentage_contribution=0.75),
            RiskContributionItem(asset_id=2, weight=0.15, marginal_contribution=0.1, component_contribution=0.02, percentage_contribution=0.20),
        ],
    )


def _bad_month() -> RiskVarCvarOutput:
    return RiskVarCvarOutput(
        confidence_level=0.95,
        horizon_days=30,
        horizon_observations=21,
        observations=230,
        value_at_risk=0.07,
        conditional_value_at_risk=0.09,
        worst_horizon=RiskWorstHorizonWindow(compounded_return=-0.12, start_date=date(2026, 3, 2), end_date=date(2026, 3, 30)),
    )


def _both_ok(**kwargs) -> RiskQueryResponse:
    return RiskQueryResponse(items=[_result(CONTRIBUTION_ID, "risk_contribution", _contribution(), **kwargs), _result(BAD_MONTH_ID, "historical_var", _bad_month(), **kwargs)])


# =============================================================================
# The request
# =============================================================================


class TestRiskRequest:
    @pytest.mark.asyncio
    async def test_one_request_today_holdings_twelve_months_and_the_bad_month(self, session):
        _FakeRiskService.response_factory = lambda request: _both_ok()
        context = _context(session, _scope())

        await _build_risk_concentration(context, {})
        await _build_tail_risk(context, {})

        assert len(_FakeRiskService.captured) == 1, "both sections must share one Risk call (one joint calendar, one window)"
        call = _FakeRiskService.captured[0]
        request = call["request"]
        assert call["user_id"] == 42
        assert request.mode == RiskMode.CURRENT_COMPOSITION
        assert request.composition_policy == RiskCompositionPolicy.CURRENT_BUY_AND_HOLD
        assert request.date_range == DateRangeModel(start=WINDOW_START, end=PERIOD_END)
        assert request.target_currency == "EUR"
        analytics = {item.analytic_code: item for item in request.analytics}
        assert set(analytics) == {"risk_contribution", "historical_var"}
        assert analytics["historical_var"].parameters == {"confidence_level": 0.95, "horizon_days": 30}
        assert request.scope.broker_ids is None
        assert request.scope.apply_ownership_share is True

    @pytest.mark.asyncio
    async def test_the_broker_filter_follows_its_switch(self, session, monkeypatch):
        _FakeRiskService.response_factory = lambda request: _both_ok()
        await _build_risk_concentration(_context(session, _scope(broker_scope=(7, 3))), {})
        assert _FakeRiskService.captured[-1]["request"].scope.broker_ids == [3, 7]

        monkeypatch.setattr(risk_evidence_module, "RISK_EVIDENCE_FOLLOWS_BROKER_FILTER", False)
        await _build_risk_concentration(_context(session, _scope(broker_scope=(7, 3))), {})
        assert _FakeRiskService.captured[-1]["request"].scope.broker_ids is None


# =============================================================================
# The payloads
# =============================================================================


class TestRiskConcentration:
    @pytest.mark.asyncio
    async def test_copies_the_result_rows_by_risk_share_with_the_window(self, session):
        shortened = RiskWarning(code="short_history", message="late", details={"asset_ids": [2]}, degrades_result=False)
        metadata = _metadata(analyzed_start=date(2026, 2, 2), excluded=(RiskExcludedAsset(asset_id=17, reason="no_price_source"),))
        _FakeRiskService.response_factory = lambda request: _both_ok(warnings=[shortened], metadata=metadata)

        payload = await _build_risk_concentration(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.OK
        assert (payload.requested_start, payload.requested_end) == (WINDOW_START, PERIOD_END)
        assert (payload.analyzed_start, payload.analyzed_end) == (date(2026, 2, 2), PERIOD_END)
        assert payload.n_observations == 250
        assert payload.composition_as_of == PERIOD_END
        assert [row.asset_id for row in payload.window_shortened_by] == [2]
        assert [(row.asset_id, row.reason) for row in payload.excluded_assets] == [(17, "no_price_source")]
        assert payload.warning_codes == ("short_history",)
        assert (payload.portfolio_volatility_ratio, payload.cash_weight_ratio, payload.excluded_weight_ratio) == (0.18, 0.40, 0.05)
        assert payload.diversification_multiple == 1.3
        assert payload.effective_number_of_assets == 2.6
        assert [(row.asset_id, row.weight_ratio, row.risk_share_ratio) for row in payload.rows] == [(1, 0.30, 0.75), (2, 0.15, 0.20), (3, 0.10, 0.05)]
        assert payload.weight_basis == WEIGHT_BASIS

    @pytest.mark.asyncio
    async def test_too_short_a_history_is_unavailable_with_the_reason(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse(items=[_refused(CONTRIBUTION_ID, "risk_contribution", RiskErrorCode.INSUFFICIENT_HISTORY), _refused(BAD_MONTH_ID, "historical_var", RiskErrorCode.INSUFFICIENT_HISTORY)])

        payload = await _build_risk_concentration(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.UNAVAILABLE
        assert payload.reason_code == RiskErrorCode.INSUFFICIENT_HISTORY.value
        assert payload.message
        assert (payload.requested_start, payload.requested_end) == (WINDOW_START, PERIOD_END)
        assert payload.rows == () and payload.portfolio_volatility_ratio is None and payload.analyzed_start is None


class TestTailRisk:
    @pytest.mark.asyncio
    async def test_copies_the_bad_month_with_its_signs_and_its_window(self, session):
        _FakeRiskService.response_factory = lambda request: _both_ok()

        payload = await _build_tail_risk(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.OK
        assert (payload.confidence_level, payload.horizon_days, payload.horizon_observations, payload.overlapping_windows) == (0.95, 30, 21, 230)
        assert (payload.value_at_risk_loss_ratio, payload.expected_shortfall_loss_ratio) == (0.07, 0.09)
        assert (payload.worst_window_return_ratio, payload.worst_window_start, payload.worst_window_end) == (-0.12, date(2026, 3, 2), date(2026, 3, 30))
        assert payload.bad_month_semantics == BAD_MONTH_SEMANTICS
        assert "overlapping" in payload.bad_month_semantics

    @pytest.mark.asyncio
    async def test_an_incompatible_composition_is_unavailable(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse(items=[_refused(CONTRIBUTION_ID, "risk_contribution", RiskErrorCode.DATA_UNAVAILABLE), _refused(BAD_MONTH_ID, "historical_var", RiskErrorCode.DATA_UNAVAILABLE)])

        payload = await _build_tail_risk(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.UNAVAILABLE
        assert payload.reason_code == RiskErrorCode.DATA_UNAVAILABLE.value
        assert payload.value_at_risk_loss_ratio is None and payload.worst_window_start is None


class TestNeverAFailedSnapshot:
    @pytest.mark.asyncio
    async def test_a_risk_error_fails_both_sections_without_raising_and_runs_once(self, session):
        def _raise(request):
            raise RuntimeError("engine down")

        _FakeRiskService.response_factory = _raise
        context = _context(session, _scope())

        concentration = await _build_risk_concentration(context, {})
        tail = await _build_tail_risk(context, {})

        assert len(_FakeRiskService.captured) == 1, "the failed call is memoized, not retried by the second section"
        for payload in (concentration, tail):
            assert payload.status is RiskEvidenceStatus.FAILED
            assert payload.reason_code == REASON_RISK_ERROR
            assert (payload.requested_start, payload.requested_end) == (WINDOW_START, PERIOD_END)

    @pytest.mark.asyncio
    async def test_an_analytic_failed_by_the_engine_is_failed_with_its_code(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse(
            items=[
                _refused(CONTRIBUTION_ID, "risk_contribution", RiskErrorCode.EXECUTION_FAILED, status=RiskResultStatus.FAILED),
                _result(BAD_MONTH_ID, "historical_var", _bad_month()),
            ]
        )
        context = _context(session, _scope())

        concentration = await _build_risk_concentration(context, {})
        tail = await _build_tail_risk(context, {})

        assert (concentration.status, concentration.reason_code) == (RiskEvidenceStatus.FAILED, RiskErrorCode.EXECUTION_FAILED.value)
        assert tail.status is RiskEvidenceStatus.OK


# =============================================================================
# Payload invariants
# =============================================================================


def _window(**extra) -> dict:
    return {"composition_as_of": PERIOD_END, "requested_start": WINDOW_START, "requested_end": PERIOD_END, "calculation_currency": "EUR", **extra}


class TestPayloadInvariants:
    def test_an_available_section_needs_its_figures_and_window(self):
        with pytest.raises(ValueError, match="requires"):
            PortfolioRiskConcentrationPayload(**_window(status=RiskEvidenceStatus.OK))

    def test_an_unavailable_section_carries_a_reason_and_no_figure(self):
        with pytest.raises(ValueError, match="reason_code"):
            PortfolioTailRiskPayload(**_window(status=RiskEvidenceStatus.UNAVAILABLE))
        with pytest.raises(ValueError, match="must not carry metrics"):
            PortfolioTailRiskPayload(**_window(status=RiskEvidenceStatus.UNAVAILABLE, reason_code="insufficient_history", message="m", value_at_risk_loss_ratio=0.1))

    def test_the_worst_window_comes_whole(self):
        with pytest.raises(ValueError, match="worst window"):
            PortfolioTailRiskPayload(
                **_window(
                    status=RiskEvidenceStatus.OK,
                    analyzed_start=WINDOW_START,
                    analyzed_end=PERIOD_END,
                    n_observations=250,
                    coverage_ratio=1.0,
                    horizon_observations=21,
                    overlapping_windows=230,
                    value_at_risk_loss_ratio=0.07,
                    expected_shortfall_loss_ratio=0.09,
                    worst_window_return_ratio=-0.1,
                )
            )

    def test_losses_are_positive(self):
        with pytest.raises(ValueError):
            PortfolioTailRiskPayload(**_window(status=RiskEvidenceStatus.OK, value_at_risk_loss_ratio=-0.07))


# =============================================================================
# Catalog wiring
# =============================================================================


class TestCatalogWiring:
    def test_internal_dataset_required_by_protection_strategies(self):
        components = build_component_registry()
        datasets = build_dataset_registry(components)
        analyses = build_analysis_registry(datasets)

        for component_id in ("portfolio.risk_concentration", "portfolio.tail_risk"):
            spec = components.get(component_id)
            assert spec.version == 1 and spec.period_behavior is PeriodBehavior.AS_OF
        dataset = datasets.get("portfolio.risk_evidence")
        assert dataset.version == 2
        assert dataset.required_component_ids == ("portfolio.risk_concentration", "portfolio.tail_risk")
        assert dataset.period_semantics is PeriodBehavior.AS_OF
        assert dataset.visibility.value == "internal"
        assert "portfolio.risk_evidence" in analyses.get("portfolio.protection_strategies").required_dataset_ids
