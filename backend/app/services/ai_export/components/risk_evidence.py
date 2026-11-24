"""AI Export risk evidence of the portfolio: where its risk is concentrated, the loss of a bad month (78 L8a) and the
pairs of holdings that move together (78 L8b).

The three components feed the internal dataset `portfolio.risk_evidence`, required by
`portfolio.protection_strategies`. They compute nothing: one `RiskService.execute` call per request, cached by
`BuildContext.db_resource`, runs the Risk analytics `risk_contribution`, `historical_var` (95 %, 30 calendar days) and
`correlation` together, so the sections share one joint calendar and one measured window. The payloads copy the
results; the only logic of their own is a selection, the pairs worth naming (`portfolio.correlated_pairs`).

Rules, decided with the AI Export consultant on 23/11/2026 (journal, 78 `L8-analisi-implementazione.md`):

- **Today's holdings** (`current_composition`, `current_buy_and_hold`): the question of whoever protects a portfolio.
  What the portfolio really lived through is `portfolio.drawdown_summary`. The Dashboard's Risk tab measures its bad
  month on the portfolio's history (TWRR) over the Dashboard period, so the two figures differ by design.
- **A fixed window of 12 months** up to the end of the export period, whatever the period chosen: the same day twelve
  calendar months before (`months_before`, the rule of the «1 year» presets). A holding quoted only recently moves
  the start of the joint calendar for every holding: the section carries the requested and the measured window, and
  names the holdings that shortened it. A holding with no usable price leaves the measures, and weighs as cash would.
- **Never a failure.** A required component that raises fails the whole snapshot (`503`), so every Risk refusal or
  error becomes a status of the payload (`unavailable` / `failed`) with a machine-readable `reason_code`, as in
  `drawdown_context.py`.
- **Percentages only**, with their base written beside them (`weight_basis`): the AI turns them into amounts on the net
  worth of the same scope, which the summary already carries.
- **Pairs, not the matrix** (L8b): models ignore an N×N correlation matrix, and grouping holdings would be new math.
  The section lists the most correlated pairs among the holdings that carry risk, and the least correlated ones, with
  the thresholds written beside them, so an empty list reads «no pair reaches the threshold», not «no correlation».
  A correlation has no scale: it says something only between holdings that carry risk, so the holdings are chosen by
  their risk share (absolute value: a negative share is a hedge the user already holds), not by their weight
  (decided with the consultant, 24/11/2026).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date as Date
from enum import StrEnum

from pydantic import Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel, StrictModel
from backend.app.schemas.risk.outputs import RiskContributionOutput, RiskCorrelationOutput, RiskVarCvarOutput
from backend.app.schemas.risk.results import RiskAnalyticResult, RiskQueryResponse
from backend.app.schemas.risk.scope import RiskAnalyticRequest, RiskQueryRequest
from backend.app.schemas.risk.vocabulary import RiskCompositionPolicy, RiskMode, RiskResultStatus, RiskValueStatus
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import export_risk_scope, load_portfolio_report
from backend.app.services.ai_export.components.resources import PORTFOLIO_REPORT_RESOURCE
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, ResourceLoadError
from backend.app.services.financial_math.weights import share_of
from backend.app.services.risk.service import RiskService
from backend.app.utils.datetime_utils import months_before
from backend.app.utils.runtime.errors import traceback_reported, traceback_reporting_request

logger = get_logger(__name__)

RISK_EVIDENCE_WINDOW_MONTHS = 12
"""The length of the measured window, in calendar months before the end of the export period."""
BAD_MONTH_CONFIDENCE_LEVEL = 0.95
BAD_MONTH_HORIZON_DAYS = 30
"""The bad month of the Dashboard's Risk tab (`MONTHLY_VAR_HORIZON_DAYS`): the same definition, on today's holdings."""

PAIRS_MIN_RISK_SHARE_RATIO = 0.02
"""A holding enters the pairs when its risk share, in absolute value, is at least this (fixed by hand, 78 L8b)."""
PAIRS_MIN_CORRELATION = 0.8
"""A pair is «moving together» at or above this correlation of daily returns."""
PAIRS_MAX_HIGH = 8
"""At most this many correlated pairs, the highest first."""
PAIRS_LOW_COUNT = 3
"""The least correlated pairs among the same holdings: where diversification works."""

_CONTRIBUTION_INSTANCE_ID = "ai_export_risk_concentration"
_BAD_MONTH_INSTANCE_ID = "ai_export_bad_month"
_CORRELATION_INSTANCE_ID = "ai_export_correlated_pairs"
_RISK_EVIDENCE_RESOURCE: ResourceKey[RiskQueryResponse] = ResourceKey("portfolio.risk_evidence_result", RiskQueryResponse)

WEIGHT_BASIS = "Weights and losses are shares of the net worth of the exported scope (cash included) on composition_as_of. " "Cash, value in transit and the holdings left out of the measures count as zero risk."
WINDOW_SEMANTICS = "Measured on today's holdings over the analyzed window, not on the AI period. A holding quoted only recently " "moves the start of the window for every holding (window_shortened_by)."
BAD_MONTH_SEMANTICS = (
    "Historical simulation on overlapping 30-day windows of today's holdings: consecutive windows share all but one " "observation, so the windows in the tail are a few independent episodes, not as many separate months. " "Losses are positive numbers; the worst window's return keeps its sign."
)

PAIRS_SEMANTICS = (
    "Pearson correlation of the daily returns of today's holdings over the analyzed window, only between the holdings whose risk "
    "share (absolute value, as in portfolio.risk_concentration) is at least min_risk_share_percent. Holdings below it were not "
    "compared, so a missing pair does not mean they are uncorrelated. high_pairs: at most max_high_pairs pairs at or above "
    "min_correlation, the highest first; an empty list means no compared pair reaches it. low_pairs: the least correlated of the other "
    "compared pairs. Fewer than two holdings above the threshold leave both lists empty: nothing to compare, not a missing measure. "
    "In each pair the first holding is the one with the larger risk share."
)

REASON_RISK_ERROR = "risk_execution_error"
REASON_RISK_SHARES_UNAVAILABLE = "risk_shares_unavailable"
REASON_RISK_MISSING = "risk_result_missing"
REASON_CASH_UNAVAILABLE = "cash_share_unavailable"
"""The section's cash share could not be read from the scope's report (78 L8c)."""


class RiskEvidenceStatus(StrEnum):
    """Lifecycle status of a risk evidence section, mirroring `RiskResultStatus`."""

    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class RiskEvidenceExcludedAsset(StrictModel):
    """A held asset left out of the measures, with the Risk reason (`missing_price`, `no_price_source`, `missing_fx`…)."""

    asset_id: int
    reason: str


class RiskEvidenceShortenedBy(StrictModel):
    """A held asset whose price history starts inside the requested window, and so moved its start for every holding."""

    asset_id: int


class RiskConcentrationRow(StrictModel):
    """One held asset (its brokers summed): its weight and its share of the portfolio's volatility."""

    asset_id: int
    weight_ratio: float
    risk_share_ratio: float | None = None


class _RiskEvidenceWindow(StrictModel):
    """The facts every risk evidence section states beside its figures."""

    status: RiskEvidenceStatus
    reason_code: str | None = None
    message: str | None = None
    mode: str = RiskMode.CURRENT_COMPOSITION.value
    composition_as_of: Date
    requested_start: Date
    requested_end: Date
    analyzed_start: Date | None = None
    analyzed_end: Date | None = None
    n_observations: int | None = Field(default=None, ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0, le=1)
    calculation_currency: str
    window_semantics: str = WINDOW_SEMANTICS
    weight_basis: str = WEIGHT_BASIS
    warning_codes: tuple[str, ...] = ()
    window_shortened_by: tuple[RiskEvidenceShortenedBy, ...] = ()
    excluded_assets: tuple[RiskEvidenceExcludedAsset, ...] = ()

    _WINDOW_METRICS = ("analyzed_start", "analyzed_end", "n_observations", "coverage_ratio")

    def _validate_window(self, metric_names: tuple[str, ...]) -> None:
        names = (*self._WINDOW_METRICS, *metric_names)
        if self.status in {RiskEvidenceStatus.OK, RiskEvidenceStatus.PARTIAL}:
            if self.reason_code is not None or self.message is not None:
                raise ValueError("an available risk evidence section must not carry reason_code/message")
            missing = [name for name in names if getattr(self, name) is None]
            if missing:
                raise ValueError(f"an available risk evidence section requires: {missing}")
            if self.analyzed_end < self.analyzed_start:
                raise ValueError("analyzed_end must not precede analyzed_start")
        else:
            if not self.reason_code or not self.message:
                raise ValueError("an unavailable risk evidence section requires reason_code and message")
            populated = [name for name in names if getattr(self, name) is not None]
            if populated:
                raise ValueError(f"an unavailable risk evidence section must not carry metrics: {populated}")


class PortfolioRiskConcentrationPayload(_RiskEvidenceWindow):
    """Where the portfolio's risk is concentrated (Risk `risk_contribution`, on today's holdings).

    `risk_share_ratio` is each holding's share of the portfolio's volatility (`percentage_contribution`); it can exceed
    1, or be negative for a holding that moves against the others. `effective_number_of_assets` is measured on the
    priced holdings alone, and `diversification_multiple` is the diversification ratio (≥ 1: the weighted volatilities
    over the portfolio's), a multiple, not a percentage.

    `cash_weight_ratio` is the true cash of the measured scope over its net worth, read from the same report as the
    export's summary, so it is the cash share the summary prints (78 L8c). It is not Risk's `cash_weight`, the residual
    at zero risk, which also holds the holdings left out of the measures and the value in transit. It can be negative
    (an overdraft): then Risk refuses the measures, unless value in transit covers it. The holdings left out are
    `excluded_weight_ratio`.
    """

    portfolio_volatility_ratio: float | None = Field(default=None, ge=0)
    effective_number_of_assets: float | None = Field(default=None, ge=0)
    diversification_multiple: float | None = Field(default=None, ge=0)
    cash_weight_ratio: float | None = None
    excluded_weight_ratio: float | None = Field(default=None, ge=0)
    rows: tuple[RiskConcentrationRow, ...] = ()

    @model_validator(mode="after")
    def _validate_status(self) -> PortfolioRiskConcentrationPayload:
        self._validate_window(("portfolio_volatility_ratio", "cash_weight_ratio", "excluded_weight_ratio"))
        if self.status in {RiskEvidenceStatus.UNAVAILABLE, RiskEvidenceStatus.FAILED} and self.rows:
            raise ValueError("an unavailable risk concentration section must not carry rows")
        return self


class PortfolioTailRiskPayload(_RiskEvidenceWindow):
    """The loss of a bad month (Risk `historical_var` at 95 %, 30 calendar days, on today's holdings).

    `value_at_risk_loss_ratio` and `expected_shortfall_loss_ratio` (the CVaR, the average loss beyond the VaR) are
    losses written as positive numbers; `worst_window_return_ratio` is the return of the worst 30-day window the
    holdings went through, with its sign. `overlapping_windows` counts the compounded windows the tail is estimated on.
    """

    confidence_level: float = BAD_MONTH_CONFIDENCE_LEVEL
    horizon_days: int = BAD_MONTH_HORIZON_DAYS
    horizon_observations: int | None = Field(default=None, ge=1)
    overlapping_windows: int | None = Field(default=None, ge=1)
    value_at_risk_loss_ratio: float | None = Field(default=None, ge=0)
    expected_shortfall_loss_ratio: float | None = Field(default=None, ge=0)
    worst_window_return_ratio: float | None = Field(default=None, ge=-1)
    worst_window_start: Date | None = None
    worst_window_end: Date | None = None
    bad_month_semantics: str = BAD_MONTH_SEMANTICS

    @model_validator(mode="after")
    def _validate_status(self) -> PortfolioTailRiskPayload:
        self._validate_window(("horizon_observations", "overlapping_windows", "value_at_risk_loss_ratio", "expected_shortfall_loss_ratio"))
        worst = (self.worst_window_return_ratio, self.worst_window_start, self.worst_window_end)
        if any(value is None for value in worst) and any(value is not None for value in worst):
            raise ValueError("the worst window carries its return and both dates, or none of them")
        if self.status in {RiskEvidenceStatus.UNAVAILABLE, RiskEvidenceStatus.FAILED} and self.worst_window_start is not None:
            raise ValueError("an unavailable tail risk section must not carry a worst window")
        if self.worst_window_start is not None and self.worst_window_end < self.worst_window_start:
            raise ValueError("worst_window_end must not precede worst_window_start")
        return self


class CorrelatedPairRow(StrictModel):
    """Two held assets and the correlation of their daily returns (a number between -1 and 1, not a percentage)."""

    first_asset_id: int
    second_asset_id: int
    correlation: float = Field(ge=-1, le=1)


class PortfolioCorrelatedPairsPayload(_RiskEvidenceWindow):
    """The pairs of holdings that move together, and the least correlated ones (Risk `correlation`, today's holdings).

    A selection of the correlation matrix, nothing more: the holdings whose absolute risk share reaches
    `min_risk_share_ratio`, their pairs with a defined correlation (`considered_pair_count`), the highest at or above
    `min_correlation` and the lowest of the rest. A pair whose correlation is undefined (a flat price series) is left
    out, and the `flat_series` warning says so. Fewer than two such holdings is an empty selection, not a missing one.
    """

    min_risk_share_ratio: float = PAIRS_MIN_RISK_SHARE_RATIO
    min_correlation: float = PAIRS_MIN_CORRELATION
    max_high_pairs: int = PAIRS_MAX_HIGH
    pairs_semantics: str = PAIRS_SEMANTICS
    considered_asset_count: int | None = Field(default=None, ge=0)
    considered_pair_count: int | None = Field(default=None, ge=0)
    high_pairs: tuple[CorrelatedPairRow, ...] = ()
    low_pairs: tuple[CorrelatedPairRow, ...] = ()

    @model_validator(mode="after")
    def _validate_status(self) -> PortfolioCorrelatedPairsPayload:
        self._validate_window(("considered_asset_count", "considered_pair_count"))
        if self.status in {RiskEvidenceStatus.UNAVAILABLE, RiskEvidenceStatus.FAILED} and (self.high_pairs or self.low_pairs):
            raise ValueError("an unavailable correlated pairs section must not carry pairs")
        if len(self.high_pairs) > self.max_high_pairs:
            raise ValueError("high_pairs exceeds max_high_pairs")
        if any(row.correlation < self.min_correlation for row in self.high_pairs):
            raise ValueError("a high pair must reach min_correlation")
        return self


def _require_portfolio_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None or scope.domain is not Domain.PORTFOLIO:
        raise ValueError("the risk evidence components require a Portfolio BuildScope")
    return scope


def risk_evidence_window(scope: BuildScope) -> DateRangeModel:
    """The requested window: twelve calendar months up to the end of the export period."""
    return DateRangeModel(start=months_before(scope.period_end, RISK_EVIDENCE_WINDOW_MONTHS), end=scope.period_end)


async def _load_risk_evidence(context: BuildContext, scope: BuildScope) -> RiskQueryResponse | None:
    """The one Risk request of the three sections, memoized; None (logged) when it could not be completed."""

    async def _loader(session: AsyncSession) -> RiskQueryResponse:
        request = RiskQueryRequest(
            scope=export_risk_scope(scope),
            date_range=risk_evidence_window(scope),
            target_currency=scope.target_currency,
            mode=RiskMode.CURRENT_COMPOSITION,
            composition_policy=RiskCompositionPolicy.CURRENT_BUY_AND_HOLD,
            analytics=[
                RiskAnalyticRequest(instance_id=_CONTRIBUTION_INSTANCE_ID, analytic_code="risk_contribution"),
                RiskAnalyticRequest(
                    instance_id=_BAD_MONTH_INSTANCE_ID,
                    analytic_code="historical_var",
                    parameters={"confidence_level": BAD_MONTH_CONFIDENCE_LEVEL, "horizon_days": BAD_MONTH_HORIZON_DAYS},
                ),
                RiskAnalyticRequest(instance_id=_CORRELATION_INSTANCE_ID, analytic_code="correlation"),
            ],
        )
        return await RiskService(session).execute(user_id=scope.user_id, request=request)

    try:
        return await context.db_resource(_RISK_EVIDENCE_RESOURCE, _loader)
    except ResourceLoadError as error:
        # Isolation boundary: a Risk failure becomes a `failed` section, never a failed snapshot. The sections read the
        # same memoized error, so its traceback is written once.
        if traceback_reported(error):
            logger.warning("AI Export risk evidence not computed", logged_with_request_id=traceback_reporting_request(error))
        else:
            logger.warning("AI Export risk evidence not computed", exc_info=error)
        return None


def _result(response: RiskQueryResponse | None, instance_id: str) -> RiskAnalyticResult | None:
    if response is None:
        return None
    return next((item for item in response.items if item.instance_id == instance_id), None)


def _window_fields(result: RiskAnalyticResult | None, scope: BuildScope) -> dict:
    """The facts of the window and of the scope, from a result's metadata and warnings (both may be missing)."""
    window = risk_evidence_window(scope)
    fields: dict = {
        "composition_as_of": scope.period_end,
        "requested_start": window.start,
        "requested_end": window.end,
        "calculation_currency": scope.target_currency,
    }
    if result is None:
        return fields
    metadata = result.metadata
    if metadata is not None:
        if metadata.composition_as_of is not None:
            fields["composition_as_of"] = metadata.composition_as_of
        fields["excluded_assets"] = tuple(RiskEvidenceExcludedAsset(asset_id=item.asset_id, reason=item.reason) for item in metadata.excluded_assets)
    shortened = sorted({int(asset_id) for warning in result.warnings if warning.code == "short_history" for asset_id in warning.details.get("asset_ids", []) if isinstance(asset_id, int)})
    fields["window_shortened_by"] = tuple(RiskEvidenceShortenedBy(asset_id=asset_id) for asset_id in shortened)
    fields["warning_codes"] = tuple(sorted({warning.code for warning in result.warnings}))
    if result.status in {RiskResultStatus.OK, RiskResultStatus.PARTIAL} and metadata is not None:
        fields.update(
            analyzed_start=metadata.analyzed_range.start,
            analyzed_end=metadata.analyzed_range.end or metadata.analyzed_range.start,
            n_observations=metadata.n_observations,
            coverage_ratio=metadata.coverage,
        )
    return fields


def _unavailable_fields(result: RiskAnalyticResult | None, *, subject: str) -> dict:
    if result is None:
        return {"status": RiskEvidenceStatus.FAILED, "reason_code": REASON_RISK_ERROR, "message": f"The {subject} could not be computed."}
    if result.status == RiskResultStatus.FAILED:
        reason = result.error.code.value if result.error is not None else REASON_RISK_ERROR
        return {"status": RiskEvidenceStatus.FAILED, "reason_code": reason, "message": f"The {subject} could not be computed."}
    reason = result.error.code.value if result.error is not None else REASON_RISK_MISSING
    return {"status": RiskEvidenceStatus.UNAVAILABLE, "reason_code": reason, "message": f"The {subject} is unavailable for these holdings over this window."}


def _concentration_rows(output: RiskContributionOutput) -> tuple[RiskConcentrationRow, ...]:
    rows = [RiskConcentrationRow(asset_id=item.asset_id, weight_ratio=item.weight, risk_share_ratio=item.percentage_contribution) for item in output.items]
    rows.sort(key=lambda row: (row.risk_share_ratio is None, -(row.risk_share_ratio or 0.0), row.asset_id))
    return tuple(rows)


async def _true_cash_weight(context: BuildContext, scope: BuildScope) -> float | None:
    """The cash of the scope Risk measured over its net worth, from the report the summary reads (78 L8c).

    Risk measures the export's own brokers (`export_risk_scope`, 78 L10), the scope of the summary's report: that report,
    memoized, so the share is the summary's to the digit. None, logged, when the report cannot be read or the net worth
    is not positive.
    """
    try:
        report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    except ResourceLoadError as error:
        # Isolation boundary: an unreadable report fails this section only, never the snapshot.
        if traceback_reported(error):
            logger.warning("AI Export risk evidence: cash share not read", logged_with_request_id=traceback_reporting_request(error))
        else:
            logger.warning("AI Export risk evidence: cash share not read", exc_info=error)
        return None
    summary = report.summary
    share = share_of(summary.cash_total.amount, summary.net_worth.amount) if summary is not None else None
    if share is None:
        logger.warning("AI Export risk evidence: no positive net worth for the cash share", user_id=scope.user_id)
        return None
    return float(share)


async def _build_risk_concentration(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioRiskConcentrationPayload:
    del dependencies
    scope = _require_portfolio_scope(context)
    result = _result(await _load_risk_evidence(context, scope), _CONTRIBUTION_INSTANCE_ID)
    fields = _window_fields(result, scope)
    if result is None or result.status not in {RiskResultStatus.OK, RiskResultStatus.PARTIAL} or not isinstance(result.output, RiskContributionOutput):
        return PortfolioRiskConcentrationPayload(**fields, **_unavailable_fields(result, subject="risk concentration"))
    output = result.output
    cash_weight = await _true_cash_weight(context, scope)
    if cash_weight is None:
        # A failed section carries the requested window only, never the measured one.
        return PortfolioRiskConcentrationPayload(**_window_fields(None, scope), status=RiskEvidenceStatus.FAILED, reason_code=REASON_CASH_UNAVAILABLE, message="The cash share of the measured scope could not be read.")
    return PortfolioRiskConcentrationPayload(
        **fields,
        status=RiskEvidenceStatus(result.status.value),
        portfolio_volatility_ratio=output.portfolio_volatility,
        effective_number_of_assets=output.effective_number_of_assets,
        diversification_multiple=output.diversification_ratio,
        cash_weight_ratio=cash_weight,
        excluded_weight_ratio=output.excluded_weight,
        rows=_concentration_rows(output),
    )


async def _build_tail_risk(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioTailRiskPayload:
    del dependencies
    scope = _require_portfolio_scope(context)
    result = _result(await _load_risk_evidence(context, scope), _BAD_MONTH_INSTANCE_ID)
    fields = _window_fields(result, scope)
    if result is None or result.status not in {RiskResultStatus.OK, RiskResultStatus.PARTIAL} or not isinstance(result.output, RiskVarCvarOutput):
        return PortfolioTailRiskPayload(**fields, **_unavailable_fields(result, subject="bad-month loss"))
    output = result.output
    worst = output.worst_horizon
    return PortfolioTailRiskPayload(
        **fields,
        status=RiskEvidenceStatus(result.status.value),
        horizon_observations=output.horizon_observations,
        overlapping_windows=output.observations,
        value_at_risk_loss_ratio=output.value_at_risk,
        expected_shortfall_loss_ratio=output.conditional_value_at_risk,
        worst_window_return_ratio=worst.compounded_return if worst is not None else None,
        worst_window_start=worst.start_date if worst is not None else None,
        worst_window_end=worst.end_date if worst is not None else None,
    )


def select_correlated_pairs(output: RiskCorrelationOutput, risk_shares: Mapping[int, float]) -> tuple[int, int, tuple[CorrelatedPairRow, ...], tuple[CorrelatedPairRow, ...]]:
    """The pairs worth naming: (holdings considered, pairs considered, high pairs, low pairs).

    A selection of the matrix the Risk engine computed, never a new figure: the holdings whose risk share, in absolute
    value, reaches `PAIRS_MIN_RISK_SHARE_RATIO`, each pair once with a defined correlation, the highest at or above
    `PAIRS_MIN_CORRELATION` (at most `PAIRS_MAX_HIGH`), then the `PAIRS_LOW_COUNT` lowest among the pairs not already
    listed. Ties fall back to the larger risk shares, then to the ids, so the selection is stable.
    """
    shares = {asset_id: abs(share) for asset_id, share in risk_shares.items()}
    eligible = {asset_id for asset_id in output.asset_ids if shares.get(asset_id, 0.0) >= PAIRS_MIN_RISK_SHARE_RATIO}

    def _ordered(first: int, second: int) -> tuple[int, int]:
        return (first, second) if (-shares[first], first) <= (-shares[second], second) else (second, first)

    pairs: dict[tuple[int, int], float] = {}
    for cell in output.cells:
        if cell.row_asset_id == cell.column_asset_id or cell.row_asset_id not in eligible or cell.column_asset_id not in eligible:
            continue
        if cell.status is not RiskValueStatus.OK or cell.value is None:
            continue
        pairs.setdefault(_ordered(cell.row_asset_id, cell.column_asset_id), cell.value)

    def _row(pair: tuple[int, int]) -> CorrelatedPairRow:
        return CorrelatedPairRow(first_asset_id=pair[0], second_asset_id=pair[1], correlation=pairs[pair])

    def _share_key(pair: tuple[int, int]) -> tuple[float, int, int]:
        return (-(shares[pair[0]] + shares[pair[1]]), pair[0], pair[1])

    high = sorted((pair for pair, value in pairs.items() if value >= PAIRS_MIN_CORRELATION), key=lambda pair: (-pairs[pair], *_share_key(pair)))[:PAIRS_MAX_HIGH]
    listed = set(high)
    low = sorted((pair for pair in pairs if pair not in listed), key=lambda pair: (pairs[pair], *_share_key(pair)))[:PAIRS_LOW_COUNT]
    return len(eligible), len(pairs), tuple(_row(pair) for pair in high), tuple(_row(pair) for pair in low)


async def _build_correlated_pairs(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioCorrelatedPairsPayload:
    del dependencies
    scope = _require_portfolio_scope(context)
    response = await _load_risk_evidence(context, scope)
    result = _result(response, _CORRELATION_INSTANCE_ID)
    fields = _window_fields(result, scope)
    if result is None or result.status not in {RiskResultStatus.OK, RiskResultStatus.PARTIAL} or not isinstance(result.output, RiskCorrelationOutput):
        return PortfolioCorrelatedPairsPayload(**fields, **_unavailable_fields(result, subject="correlation of the holdings"))
    contribution = _result(response, _CONTRIBUTION_INSTANCE_ID)
    risk_shares: dict[int, float] = {}
    if contribution is not None and contribution.status in {RiskResultStatus.OK, RiskResultStatus.PARTIAL} and isinstance(contribution.output, RiskContributionOutput):
        risk_shares = {item.asset_id: item.percentage_contribution for item in contribution.output.items if item.percentage_contribution is not None}
    if not risk_shares:
        # The risk shares that choose the holdings come from `risk_contribution`; without them no selection is honest,
        # and the weight is no stand-in under the same field.
        unavailable = dict.fromkeys(("analyzed_start", "analyzed_end", "n_observations", "coverage_ratio"))
        return PortfolioCorrelatedPairsPayload(
            **{**fields, **unavailable},
            status=RiskEvidenceStatus.UNAVAILABLE,
            reason_code=REASON_RISK_SHARES_UNAVAILABLE,
            message="The holdings' risk shares could not be measured, so the pairs worth naming cannot be chosen.",
        )
    considered_assets, considered_pairs, high, low = select_correlated_pairs(result.output, risk_shares)
    return PortfolioCorrelatedPairsPayload(
        **fields,
        status=RiskEvidenceStatus(result.status.value),
        considered_asset_count=considered_assets,
        considered_pair_count=considered_pairs,
        high_pairs=high,
        low_pairs=low,
    )


PORTFOLIO_RISK_CONCENTRATION_COMPONENT = ComponentSpec(
    component_id="portfolio.risk_concentration",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioRiskConcentrationPayload,
    builder=_build_risk_concentration,
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_TAIL_RISK_COMPONENT = ComponentSpec(
    component_id="portfolio.tail_risk",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioTailRiskPayload,
    builder=_build_tail_risk,
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_CORRELATED_PAIRS_COMPONENT = ComponentSpec(
    component_id="portfolio.correlated_pairs",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioCorrelatedPairsPayload,
    builder=_build_correlated_pairs,
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_RISK_EVIDENCE_COMPONENTS: tuple[ComponentSpec, ...] = (
    PORTFOLIO_RISK_CONCENTRATION_COMPONENT,
    PORTFOLIO_TAIL_RISK_COMPONENT,
    PORTFOLIO_CORRELATED_PAIRS_COMPONENT,
)


__all__ = [
    "BAD_MONTH_CONFIDENCE_LEVEL",
    "BAD_MONTH_HORIZON_DAYS",
    "PAIRS_LOW_COUNT",
    "PAIRS_MAX_HIGH",
    "PAIRS_MIN_CORRELATION",
    "PAIRS_MIN_RISK_SHARE_RATIO",
    "PORTFOLIO_CORRELATED_PAIRS_COMPONENT",
    "PORTFOLIO_RISK_CONCENTRATION_COMPONENT",
    "PORTFOLIO_RISK_EVIDENCE_COMPONENTS",
    "PORTFOLIO_TAIL_RISK_COMPONENT",
    "REASON_CASH_UNAVAILABLE",
    "REASON_RISK_ERROR",
    "REASON_RISK_MISSING",
    "REASON_RISK_SHARES_UNAVAILABLE",
    "RISK_EVIDENCE_WINDOW_MONTHS",
    "CorrelatedPairRow",
    "PortfolioCorrelatedPairsPayload",
    "PortfolioRiskConcentrationPayload",
    "PortfolioTailRiskPayload",
    "RiskConcentrationRow",
    "RiskEvidenceExcludedAsset",
    "RiskEvidenceShortenedBy",
    "RiskEvidenceStatus",
    "risk_evidence_window",
    "select_correlated_pairs",
]
