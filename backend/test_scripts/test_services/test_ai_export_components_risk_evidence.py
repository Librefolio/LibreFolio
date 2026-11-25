"""The AI Export risk evidence of the portfolio: `portfolio.risk_concentration`, `portfolio.tail_risk` (78 L8a) and
`portfolio.correlated_pairs` (78 L8b).

Covers the request the components send (today's holdings, 12 months up to the end of the period, the 95 % 30-day bad
month, the correlation matrix, the broker filter behind its one switch), the copy of the Risk results into the payloads
(figures, measured window, the holdings that shortened it, the holdings left out), the selection of the pairs (weight
and correlation thresholds, caps, order, undefined cells), the honest statuses (a Risk refusal is `unavailable`, a
Risk error is `failed`, never an exception), one Risk call for the three sections, the payload invariants, and the
catalog wiring. `RiskService` is stubbed: the risk engine is reviewed and tested on its own. So is the scope's report
the cash share is read from (78 L8c): which report, and what happens when it cannot be read. That the share equals the
summary's to the digit, on a real book, is `test_ai_export_risk_evidence_cash_share.py`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.ai_export.components.risk_evidence as risk_evidence_module
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.risk.outputs import RiskContributionItem, RiskContributionOutput, RiskCorrelationOutput, RiskMatrixCell, RiskVarCvarOutput, RiskWorstHorizonWindow
from backend.app.schemas.risk.results import RiskAnalyticResult, RiskError, RiskExcludedAsset, RiskQueryResponse, RiskResultMetadata, RiskWarning
from backend.app.schemas.risk.vocabulary import RiskCompositionPolicy, RiskErrorCode, RiskMode, RiskResultStatus, RiskReturnBasis, RiskValueStatus
from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.resources import PORTFOLIO_REPORT_RESOURCE
from backend.app.services.ai_export.components.risk_evidence import (
    BAD_MONTH_SEMANTICS,
    PAIRS_MAX_HIGH,
    REASON_CASH_UNAVAILABLE,
    REASON_RISK_ERROR,
    REASON_RISK_SHARES_UNAVAILABLE,
    WEIGHT_BASIS,
    CorrelatedPairRow,
    PortfolioCorrelatedPairsPayload,
    PortfolioRiskConcentrationPayload,
    PortfolioTailRiskPayload,
    RiskEvidenceStatus,
    _build_correlated_pairs,
    _build_risk_concentration,
    _build_tail_risk,
    select_correlated_pairs,
)
from backend.app.services.ai_export.components.types import BrokerScopeSource, BuildScope, DetailLevel, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError, build_bucket_plan_for_scope

PERIOD_START = date(2026, 8, 23)
PERIOD_END = date(2026, 11, 23)
WINDOW_START = date(2025, 11, 23)
CONTRIBUTION_ID = "ai_export_risk_concentration"
BAD_MONTH_ID = "ai_export_bad_month"
CORRELATION_ID = "ai_export_correlated_pairs"


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


class _FakeReport:
    """Stands in for `load_portfolio_report`: records each call and answers a summary with the cash and the net worth set."""

    calls: list[dict] = []
    cash = Decimal("400")
    net_worth = Decimal("1000")
    error: BaseException | None = None

    @staticmethod
    async def load(context, scope, resource_key, *, apply_ownership_share=None):
        _FakeReport.calls.append({"scope": scope, "resource_key": resource_key})
        if _FakeReport.error is not None:
            raise _FakeReport.error
        summary = SimpleNamespace(cash_total=SimpleNamespace(amount=_FakeReport.cash), net_worth=SimpleNamespace(amount=_FakeReport.net_worth))
        return SimpleNamespace(summary=summary)


@pytest.fixture(autouse=True)
def _stub_report(monkeypatch):
    _FakeReport.calls = []
    _FakeReport.cash, _FakeReport.net_worth, _FakeReport.error = Decimal("400"), Decimal("1000"), None
    monkeypatch.setattr(risk_evidence_module, "load_portfolio_report", _FakeReport.load)
    yield


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s


_OWNED_BROKERS: tuple[int, ...] = (1, 2)
"""78 L10b: the whole portfolio is the owned brokers, named (an empty scope means no broker)."""


def _scope(*, broker_scope: tuple[int, ...] | None = None) -> BuildScope:
    """The whole portfolio (the owned brokers) without `broker_scope`; a filter with it."""
    return BuildScope(
        request_id="req-portfolio-risk-evidence",
        user_id=42,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency="EUR",
        broker_scope=_OWNED_BROKERS if broker_scope is None else broker_scope,
        broker_scope_source=BrokerScopeSource.OWNED if broker_scope is None else BrokerScopeSource.REQUESTED,
        owned_broker_ids=_OWNED_BROKERS,
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


def _matrix(values: dict[tuple[int, int], float | None], asset_ids: tuple[int, ...] = (1, 2, 3)) -> RiskCorrelationOutput:
    """A symmetric matrix over `asset_ids`: 1 on the diagonal, `values` (either order) elsewhere; None is undefined."""
    cells = []
    for row in asset_ids:
        for column in asset_ids:
            value = 1.0 if row == column else values.get((row, column), values.get((column, row)))
            status = RiskValueStatus.OK if value is not None else RiskValueStatus.UNDEFINED
            cells.append(RiskMatrixCell(row_asset_id=row, column_asset_id=column, value=value, observations=250, coverage=0.98, status=status))
    return RiskCorrelationOutput(asset_ids=list(asset_ids), cells=cells)


def _correlation() -> RiskCorrelationOutput:
    return _matrix({(1, 2): 0.92, (1, 3): 0.85, (2, 3): 0.10})


def _both_ok(contribution: RiskContributionOutput | None = None, **kwargs) -> RiskQueryResponse:
    return RiskQueryResponse(
        items=[
            _result(CONTRIBUTION_ID, "risk_contribution", contribution or _contribution(), **kwargs),
            _result(BAD_MONTH_ID, "historical_var", _bad_month(), **kwargs),
            _result(CORRELATION_ID, "correlation", _correlation(), **kwargs),
        ]
    )


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
        await _build_correlated_pairs(context, {})

        assert len(_FakeRiskService.captured) == 1, "the three sections must share one Risk call (one joint calendar, one window)"
        call = _FakeRiskService.captured[0]
        request = call["request"]
        assert call["user_id"] == 42
        assert request.mode == RiskMode.CURRENT_COMPOSITION
        assert request.composition_policy == RiskCompositionPolicy.CURRENT_BUY_AND_HOLD
        assert request.date_range == DateRangeModel(start=WINDOW_START, end=PERIOD_END)
        assert request.target_currency == "EUR"
        analytics = {item.analytic_code: item for item in request.analytics}
        assert set(analytics) == {"risk_contribution", "historical_var", "correlation"}
        assert analytics["historical_var"].parameters == {"confidence_level": 0.95, "horizon_days": 30}
        assert analytics["correlation"].parameters == {}
        # 78 L10b: the whole portfolio passes its brokers, never `None` (every accessible broker).
        assert request.scope.broker_ids == list(_OWNED_BROKERS)
        assert request.scope.apply_ownership_share is True

    @pytest.mark.asyncio
    async def test_the_measures_follow_the_broker_filter(self, session):
        # D10, decided (78 L10): the export's brokers, with the owner's share, always; the switch is gone.
        _FakeRiskService.response_factory = lambda request: _both_ok()
        await _build_risk_concentration(_context(session, _scope(broker_scope=(7, 3))), {})
        scope = _FakeRiskService.captured[-1]["request"].scope
        assert (scope.broker_ids, scope.apply_ownership_share) == ([3, 7], True)


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


class TestTrueCash:
    """78 L8c: the cash share is the scope's cash over its net worth, not Risk's residual at zero risk."""

    @pytest.mark.asyncio
    async def test_the_share_is_the_reports_cash_not_the_residual_at_zero_risk(self, session):
        # Risk's residual (0.40 in `_contribution`) holds the holdings left out too; the report says 0.25.
        _FakeRiskService.response_factory = lambda request: _both_ok()
        _FakeReport.cash = Decimal("250")

        payload = await _build_risk_concentration(_context(session, _scope()), {})

        assert payload.cash_weight_ratio == 0.25
        assert payload.excluded_weight_ratio == 0.05, "the holdings left out keep their own field"

    @pytest.mark.asyncio
    async def test_with_value_in_transit_the_share_stays_the_cash_and_the_warning_stays(self, session):
        # Risk's residual holds the value in transit (0.40); the cash is 0.25; the warning is the model's only trace of it.
        in_transit = RiskWarning(code="zero_risk_residual_includes_in_transit", message="in transit", details={}, degrades_result=False)
        _FakeRiskService.response_factory = lambda request: _both_ok(warnings=[in_transit])
        _FakeReport.cash = Decimal("250")

        payload = await _build_risk_concentration(_context(session, _scope()), {})

        assert payload.cash_weight_ratio == 0.25
        assert "zero_risk_residual_includes_in_transit" in payload.warning_codes
        assert "value in transit" in payload.weight_basis, "the base says the value in transit counts at zero risk"

    @pytest.mark.asyncio
    async def test_it_reads_the_summarys_report_on_the_measured_scope(self, session):
        _FakeRiskService.response_factory = lambda request: _both_ok()
        scope = _scope(broker_scope=(7, 3))

        await _build_risk_concentration(_context(session, scope), {})

        assert [(call["resource_key"], call["scope"]) for call in _FakeReport.calls] == [(PORTFOLIO_REPORT_RESOURCE, scope)]

    @pytest.mark.asyncio
    async def test_an_overdraft_is_a_negative_share(self, session):
        _FakeRiskService.response_factory = lambda request: _both_ok()
        _FakeReport.cash = Decimal("-50")

        payload = await _build_risk_concentration(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.OK
        assert payload.cash_weight_ratio == -0.05

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", ["unreadable", "no_net_worth"])
    async def test_without_the_cash_share_the_section_fails_alone(self, session, case):
        _FakeRiskService.response_factory = lambda request: _both_ok()
        if case == "unreadable":
            _FakeReport.error = ResourceLoadError("portfolio.report", RuntimeError("report down"))
        else:
            _FakeReport.net_worth = Decimal("0")
        context = _context(session, _scope())

        concentration = await _build_risk_concentration(context, {})
        tail = await _build_tail_risk(context, {})

        assert (concentration.status, concentration.reason_code) == (RiskEvidenceStatus.FAILED, REASON_CASH_UNAVAILABLE)
        assert concentration.rows == () and concentration.cash_weight_ratio is None
        assert tail.status is RiskEvidenceStatus.OK, "the other sections do not read the report"


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


def _pairs(rows: tuple[CorrelatedPairRow, ...]) -> list[tuple[int, int, float]]:
    return [(row.first_asset_id, row.second_asset_id, row.correlation) for row in rows]


class TestCorrelatedPairs:
    @pytest.mark.asyncio
    async def test_names_the_pairs_that_move_together_and_the_least_correlated(self, session):
        _FakeRiskService.response_factory = lambda request: _both_ok()

        payload = await _build_correlated_pairs(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.OK
        assert (payload.analyzed_start, payload.analyzed_end, payload.n_observations) == (date(2025, 11, 24), PERIOD_END, 250)
        assert (payload.min_risk_share_ratio, payload.min_correlation, payload.max_high_pairs) == (0.02, 0.8, 8)
        assert (payload.considered_asset_count, payload.considered_pair_count) == (3, 3)
        # The larger risk share comes first; the highest correlation first among the high pairs.
        assert _pairs(payload.high_pairs) == [(1, 2, 0.92), (1, 3, 0.85)]
        assert _pairs(payload.low_pairs) == [(2, 3, 0.10)]
        assert "empty" in payload.pairs_semantics and "not compared" in payload.pairs_semantics

    def test_a_holding_with_little_risk_and_an_undefined_pair_stay_out(self):
        # Asset 4 carries 1 % of the risk: below the threshold, its 0.99 with asset 1 is not named. The pair 2-3 is undefined.
        output = _matrix({(1, 2): 0.81, (1, 3): 0.30, (2, 3): None, (1, 4): 0.99, (2, 4): 0.5, (3, 4): 0.5}, asset_ids=(1, 2, 3, 4))
        risk_shares = {1: 0.60, 2: 0.25, 3: 0.10, 4: 0.01}

        assets, pairs, high, low = select_correlated_pairs(output, risk_shares)

        assert (assets, pairs) == (3, 2)
        assert _pairs(high) == [(1, 2, 0.81)]
        assert _pairs(low) == [(1, 3, 0.30)]

    def test_caps_the_high_pairs_and_takes_the_lowest_among_the_rest(self):
        # Six holdings, every pair correlated: 15 pairs, the 8 highest named, the 3 lowest of the other 7.
        asset_ids = (1, 2, 3, 4, 5, 6)
        values = {}
        step = 0
        for first in asset_ids:
            for second in asset_ids:
                if first < second:
                    values[(first, second)] = round(0.80 + 0.01 * step, 2)
                    step += 1
        risk_shares = dict.fromkeys(asset_ids, 0.1)

        assets, pairs, high, low = select_correlated_pairs(_matrix(values, asset_ids=asset_ids), risk_shares)

        assert (assets, pairs) == (6, 15)
        assert len(high) == PAIRS_MAX_HIGH
        assert [row.correlation for row in high] == sorted((row.correlation for row in high), reverse=True)
        assert [row.correlation for row in low] == [0.80, 0.81, 0.82]
        assert not {(row.first_asset_id, row.second_asset_id) for row in high} & {(row.first_asset_id, row.second_asset_id) for row in low}

    def test_a_negative_risk_share_counts_by_its_size(self):
        # Asset 2 moves against the others (a hedge already held): -15 % of the risk is in, by its absolute value.
        output = _matrix({(1, 2): -0.85, (1, 3): 0.95, (2, 3): 0.10})
        risk_shares = {1: 0.90, 2: -0.15, 3: 0.01}

        assets, pairs, high, low = select_correlated_pairs(output, risk_shares)

        assert (assets, pairs) == (2, 1)
        assert high == ()
        assert _pairs(low) == [(1, 2, -0.85)]

    def test_fewer_than_two_holdings_with_risk_is_an_empty_selection(self):
        output = _matrix({(1, 2): 0.95, (1, 3): 0.90, (2, 3): 0.99})

        assert select_correlated_pairs(output, {1: 0.99, 2: 0.006, 3: 0.004}) == (1, 0, (), ())

    @pytest.mark.asyncio
    async def test_one_holding_with_risk_keeps_the_status_and_empty_lists(self, session):
        contribution = _contribution().model_copy(update={"items": [item.model_copy(update={"percentage_contribution": share}) for item, share in zip(_contribution().items, (0.005, 0.99, 0.005), strict=True)]})
        _FakeRiskService.response_factory = lambda request: _both_ok(contribution=contribution)

        payload = await _build_correlated_pairs(_context(session, _scope()), {})

        assert payload.status is RiskEvidenceStatus.OK and payload.reason_code is None
        assert (payload.considered_asset_count, payload.considered_pair_count) == (1, 0)
        assert payload.high_pairs == () and payload.low_pairs == ()

    def test_todays_admin_rows(self):
        # The test admin's Dashboard on 24/11/2026 (78 L8b): Bitcoin (6), Ethereum (7) and Apple (1) carry risk; the two
        # real estate loans (4, 5) weigh 25 % but carry 0.6 % of it, so their 0.9352 is not named, and Ethereum's 0.8 %
        # of weight no longer keeps the Bitcoin-Ethereum pair out.
        values = {
            (1, 2): -0.0537,
            (1, 3): 0.0277,
            (1, 4): -0.0551,
            (1, 5): -0.0639,
            (1, 6): -0.0104,
            (1, 7): -0.0166,
            (2, 3): 0.0136,
            (2, 4): -0.0198,
            (2, 5): -0.0466,
            (2, 6): -0.0062,
            (2, 7): 0.0103,
            (3, 4): 0.0396,
            (3, 5): 0.064,
            (3, 6): -0.0307,
            (3, 7): -0.0407,
            (4, 5): 0.9352,
            (4, 6): 0.0914,
            (4, 7): 0.0585,
            (5, 6): 0.0937,
            (5, 7): 0.0811,
            (6, 7): 0.8223,
        }
        risk_shares = {1: 0.030875, 2: 0.000494, 3: 0.000716, 4: 0.004191, 5: 0.002172, 6: 0.925589, 7: 0.035964}

        assets, pairs, high, low = select_correlated_pairs(_matrix(values, asset_ids=(1, 2, 3, 4, 5, 6, 7)), risk_shares)

        assert (assets, pairs) == (3, 3)
        assert _pairs(high) == [(6, 7, 0.8223)]
        assert _pairs(low) == [(7, 1, -0.0166), (6, 1, -0.0104)]

    def test_todays_test_user_rows(self):
        # The test user: Bitcoin (3) and Ethereum (4) carry 99.9 % of the risk, one pair and no low one.
        values = {(1, 2): -0.0537, (1, 3): -0.0104, (1, 4): -0.0166, (2, 3): -0.0062, (2, 4): 0.0103, (3, 4): 0.8223}
        risk_shares = {3: 0.961267, 4: 0.037446, 1: 0.001043, 2: 0.000244}

        assets, pairs, high, low = select_correlated_pairs(_matrix(values, asset_ids=(1, 2, 3, 4)), risk_shares)

        assert (assets, pairs) == (2, 1)
        assert _pairs(high) == [(3, 4, 0.8223)]
        assert low == ()

    @pytest.mark.asyncio
    async def test_without_measured_risk_shares_no_pair_is_chosen(self, session):
        contribution = _contribution().model_copy(update={"items": [item.model_copy(update={"percentage_contribution": None}) for item in _contribution().items]})
        _FakeRiskService.response_factory = lambda request: _both_ok(contribution=contribution)

        payload = await _build_correlated_pairs(_context(session, _scope()), {})

        assert (payload.status, payload.reason_code) == (RiskEvidenceStatus.UNAVAILABLE, REASON_RISK_SHARES_UNAVAILABLE)
        assert payload.high_pairs == () and payload.low_pairs == () and payload.considered_pair_count is None

    @pytest.mark.asyncio
    async def test_without_the_risk_contribution_no_pair_is_chosen(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse(
            items=[
                _refused(CONTRIBUTION_ID, "risk_contribution", RiskErrorCode.DATA_UNAVAILABLE),
                _result(BAD_MONTH_ID, "historical_var", _bad_month()),
                _result(CORRELATION_ID, "correlation", _correlation()),
            ]
        )

        payload = await _build_correlated_pairs(_context(session, _scope()), {})

        assert (payload.status, payload.reason_code) == (RiskEvidenceStatus.UNAVAILABLE, REASON_RISK_SHARES_UNAVAILABLE)
        assert payload.high_pairs == () and payload.low_pairs == () and payload.considered_pair_count is None

    @pytest.mark.asyncio
    async def test_too_short_a_history_is_unavailable_with_the_reason(self, session):
        _FakeRiskService.response_factory = lambda request: RiskQueryResponse(items=[_refused(instance, code, RiskErrorCode.INSUFFICIENT_HISTORY) for instance, code in ((CONTRIBUTION_ID, "risk_contribution"), (BAD_MONTH_ID, "historical_var"), (CORRELATION_ID, "correlation"))])

        payload = await _build_correlated_pairs(_context(session, _scope()), {})

        assert (payload.status, payload.reason_code) == (RiskEvidenceStatus.UNAVAILABLE, RiskErrorCode.INSUFFICIENT_HISTORY.value)
        assert payload.high_pairs == () and payload.analyzed_start is None


class TestNeverAFailedSnapshot:
    @pytest.mark.asyncio
    async def test_a_risk_error_fails_both_sections_without_raising_and_runs_once(self, session):
        def _raise(request):
            raise RuntimeError("engine down")

        _FakeRiskService.response_factory = _raise
        context = _context(session, _scope())

        concentration = await _build_risk_concentration(context, {})
        tail = await _build_tail_risk(context, {})
        pairs = await _build_correlated_pairs(context, {})

        assert len(_FakeRiskService.captured) == 1, "the failed call is memoized, not retried by the other sections"
        for payload in (concentration, tail, pairs):
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

    def test_a_high_pair_reaches_the_threshold(self):
        with pytest.raises(ValueError, match="min_correlation"):
            PortfolioCorrelatedPairsPayload(
                **_window(
                    status=RiskEvidenceStatus.OK,
                    analyzed_start=WINDOW_START,
                    analyzed_end=PERIOD_END,
                    n_observations=250,
                    coverage_ratio=1.0,
                    considered_asset_count=2,
                    considered_pair_count=1,
                    high_pairs=(CorrelatedPairRow(first_asset_id=1, second_asset_id=2, correlation=0.5),),
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

        component_ids = ("portfolio.risk_concentration", "portfolio.tail_risk", "portfolio.correlated_pairs")
        for component_id in component_ids:
            spec = components.get(component_id)
            assert spec.version == 1 and spec.period_behavior is PeriodBehavior.AS_OF
        dataset = datasets.get("portfolio.risk_evidence")
        assert dataset.version == 2
        assert dataset.required_component_ids == component_ids
        assert dataset.period_semantics is PeriodBehavior.AS_OF
        assert dataset.visibility.value == "internal"
        assert "portfolio.risk_evidence" in analyses.get("portfolio.protection_strategies").required_dataset_ids
