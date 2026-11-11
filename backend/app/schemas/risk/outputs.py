"""Risk analytic outputs: one output model per analytic (KPI, correlation, contribution, returns, stress, comparison, VaR/CVaR, simulation, optimization, drawdown, asset-set views) and their union."""

from __future__ import annotations

import math
from datetime import date
from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field, FiniteFloat, PositiveInt, model_validator

from backend.app.schemas.common import DateRangeModel, SafeDecimal, StrictModel
from backend.app.schemas.risk.scenarios import (
    RiskScenarioDimension,
)
from backend.app.schemas.risk.vocabulary import (
    RiskCompositionPolicy,
    RiskCovarianceEstimator,
    RiskDrawdownRecoveryStatus,
    RiskOptimizationSolver,
    RiskOptimizationStrategy,
    RiskOutputKind,
    RiskReturnBasis,
    RiskSamplingStrategy,
    RiskSimulationCovarianceEstimator,
    RiskSimulationDriftEstimator,
    RiskSimulationProcess,
    RiskSimulationRegime,
    RiskStressApplicationRule,
    RiskStressMethod,
    RiskValueStatus,
)


class RiskKpiOutput(StrictModel):
    kind: Literal[RiskOutputKind.KPI] = Field(default=RiskOutputKind.KPI, json_schema_extra={"enum": ["kpi"]})
    volatility: FiniteFloat = Field(..., ge=0)
    max_drawdown: FiniteFloat = Field(..., le=0)
    max_drawdown_duration_days: int = Field(..., ge=0)
    sharpe: Optional[FiniteFloat] = None
    sortino: Optional[FiniteFloat] = None
    # Acquired measures. Sign convention for this output: drawdowns and returns are
    # negative, dispersions are non-negative — so ulcer_index is ge=0 like volatility
    # above, while every other field added here is le=0.
    # max_drawdown already *is* the peak-relative maximum drawdown; no second field
    # restates it.
    worst_realization: Optional[FiniteFloat] = Field(None, le=0)
    worst_realization_date: Optional[date] = None
    drawdown_confidence_level: Optional[FiniteFloat] = Field(None, gt=0, lt=1)
    drawdown_at_risk: Optional[FiniteFloat] = Field(None, le=0)
    conditional_drawdown_at_risk: Optional[FiniteFloat] = Field(None, le=0)
    ulcer_index: Optional[FiniteFloat] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_drawdown_tail_ordering(self) -> RiskKpiOutput:
        """Catches a swapped assignment, which no range constraint can see.

        Both values are negative and both are plausible on their own; only their
        order distinguishes the quantile from its conditional mean. Mirrors
        ``RiskVarCvarOutput.validate_tail_ordering`` with the sign reversed.
        """
        if self.drawdown_at_risk is not None and self.conditional_drawdown_at_risk is not None and self.conditional_drawdown_at_risk > self.drawdown_at_risk:
            raise ValueError("conditional_drawdown_at_risk must be <= drawdown_at_risk")
        if self.conditional_drawdown_at_risk is not None and self.max_drawdown > self.conditional_drawdown_at_risk:
            raise ValueError("conditional_drawdown_at_risk must be >= max_drawdown")
        return self


class RiskMatrixCell(StrictModel):
    row_asset_id: PositiveInt
    column_asset_id: PositiveInt
    value: Optional[FiniteFloat] = Field(None, ge=-1, le=1)
    observations: int = Field(..., ge=0)
    coverage: FiniteFloat = Field(..., ge=0, le=1)
    status: RiskValueStatus


class RiskCorrelationOutput(StrictModel):
    kind: Literal[RiskOutputKind.MATRIX] = Field(default=RiskOutputKind.MATRIX, json_schema_extra={"enum": ["matrix"]})
    asset_ids: List[PositiveInt] = Field(..., min_length=1)
    cells: List[RiskMatrixCell] = Field(default_factory=list)


class RiskContributionItem(StrictModel):
    asset_id: PositiveInt
    weight: FiniteFloat
    marginal_contribution: FiniteFloat
    component_contribution: FiniteFloat
    percentage_contribution: Optional[FiniteFloat] = None


class RiskContributionOutput(StrictModel):
    kind: Literal[RiskOutputKind.CONTRIBUTION] = Field(default=RiskOutputKind.CONTRIBUTION, json_schema_extra={"enum": ["contribution"]})
    portfolio_volatility: FiniteFloat = Field(..., ge=0)
    cash_weight: FiniteFloat = Field(0, ge=0)
    # Σ weights of the scope assets left without a series, which weigh in `cash_weight` as cash
    # would. Inside it while true cash is not negative; with negative true cash (weights above 1)
    # the two are not nested, so no rule ties them.
    excluded_weight: FiniteFloat = Field(0, ge=0)
    items: List[RiskContributionItem] = Field(default_factory=list)
    # Concentration, acquired. These two are published together on purpose: the
    # effective count is blind to correlation, so ten equally weighted holdings score
    # ten whether they are independent or move as one. Only the ratio tells them apart.
    # Unit of effective_number_of_assets is *positions*, never a percentage.
    effective_number_of_assets: Optional[FiniteFloat] = Field(None, gt=0)
    # >= 1 for long-only weights by Cauchy-Schwarz, but constrained only to gt=0 so a
    # portfolio sitting exactly at the bound cannot fail validation on a rounding.
    diversification_ratio: Optional[FiniteFloat] = Field(None, gt=0)


class RiskReturnItem(StrictModel):
    """One point of a risk/return plot: what it risks, what it is expected to pay."""

    asset_id: PositiveInt
    # Share of net worth, exactly as risk_contribution states it — not renormalized to
    # the invested part. A plot whose bubbles sum to less than the whole is telling the
    # truth about cash; one renormalized behind the reader's back is not.
    weight: FiniteFloat
    volatility: FiniteFloat = Field(..., ge=0)
    # Arithmetic. See services/risk/metrics.annualized_expected_return: this is the
    # mean-variance expected return, the quantity in which a line through the risk-free
    # intercept has the Sharpe ratio as its slope. It is NOT what the holder earned —
    # on a highly volatile asset the two differ by tens of percentage points.
    expected_annual_return: FiniteFloat
    # The holding's reward per unit of risk, on the returns and the annualization of this very
    # point. Sharpe charges each observation the rate `expm1(log1p(rf) / f)`, so the line through
    # the point with this slope crosses the return axis at `f` times that rate — at the origin when
    # the rate is zero. Sortino charges the target return (MAR) instead, against the downside
    # deviation. Either is None when undefined, never 0, and a warning names the holding.
    sharpe: Optional[FiniteFloat] = None
    sortino: Optional[FiniteFloat] = None


class RiskReturnOutput(StrictModel):
    """Per-asset risk and reward for the composition held today, plus the whole."""

    kind: Literal[RiskOutputKind.RISK_RETURN] = Field(default=RiskOutputKind.RISK_RETURN, json_schema_extra={"enum": ["risk_return"]})
    portfolio_volatility: FiniteFloat = Field(..., ge=0)
    portfolio_expected_annual_return: FiniteFloat
    # Published beside the points because it is the difference between them: the asset
    # weights sum to 1 - cash_weight, so a reader who adds up the bubbles and finds
    # they miss the whole deserves the reason rather than the puzzle.
    cash_weight: FiniteFloat = Field(0, ge=0)
    # Weight of the scope assets left without a series: see RiskContributionOutput.excluded_weight.
    excluded_weight: FiniteFloat = Field(0, ge=0)
    items: List[RiskReturnItem] = Field(default_factory=list)


class RiskStressBucketAudit(StrictModel):
    """Auditable resolution of one asset exposure bucket."""

    exposure_bucket_id: str = Field(..., min_length=1, max_length=80)
    exposure: FiniteFloat = Field(..., ge=0, le=1)
    candidate_bucket_ids: List[str] = Field(default_factory=list, max_length=100)
    applied_bucket_id: Optional[str] = Field(None, min_length=1, max_length=80)
    bucket_shock: FiniteFloat
    shock_contribution: FiniteFloat
    rule: RiskStressApplicationRule

    @model_validator(mode="after")
    def validate_resolution(self) -> RiskStressBucketAudit:
        if len(self.candidate_bucket_ids) != len(set(self.candidate_bucket_ids)):
            raise ValueError("candidate_bucket_ids must be unique")
        if self.applied_bucket_id is not None and self.applied_bucket_id not in self.candidate_bucket_ids:
            raise ValueError("applied_bucket_id must be one of candidate_bucket_ids")
        if self.rule == RiskStressApplicationRule.UNCONFIGURED_ZERO:
            if self.applied_bucket_id is not None or self.bucket_shock != 0:
                raise ValueError("unconfigured-zero audit cannot apply a configured bucket")
        elif self.applied_bucket_id is None:
            raise ValueError("configured stress rules require applied_bucket_id")
        expected = self.exposure * self.bucket_shock
        if not math.isclose(
            self.shock_contribution,
            expected,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("shock_contribution must equal exposure * bucket_shock")
        return self


class RiskStressConfiguredBucketImpact(StrictModel):
    """Scope usage of one configured bucket, including explicit zero exposure."""

    bucket_id: str = Field(..., min_length=1, max_length=80)
    shock: FiniteFloat
    applied_asset_count: int = Field(..., ge=0)
    asset_exposure_total: FiniteFloat = Field(
        ...,
        ge=0,
        description="Unweighted sum of this bucket's applied exposures across scope assets; may exceed 1 for multi-asset scopes.",
    )
    contribution_return: Optional[FiniteFloat] = None


class RiskStressImpact(StrictModel):
    asset_id: PositiveInt
    return_source_asset_id: Optional[PositiveInt] = None
    weight: Optional[FiniteFloat] = None
    shock_return: FiniteFloat
    contribution_return: Optional[FiniteFloat] = None
    impact_amount: Optional[SafeDecimal] = None
    dimension: Optional[RiskScenarioDimension] = None
    metadata_fallback: bool = False
    bucket_audit: List[RiskStressBucketAudit] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bucket_audit(self) -> RiskStressImpact:
        if not self.bucket_audit:
            if self.dimension is not None or self.metadata_fallback:
                raise ValueError("hypothetical stress impacts require bucket_audit")
            return self
        if self.dimension is None:
            raise ValueError("bucket_audit requires a stress dimension")
        exposure_total = math.fsum(item.exposure for item in self.bucket_audit)
        if not math.isclose(exposure_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("stress bucket exposures must sum to 1")
        expected_shock = math.fsum(item.shock_contribution for item in self.bucket_audit)
        if not math.isclose(
            self.shock_return,
            expected_shock,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("shock_return must equal bucket shock contributions")
        if self.metadata_fallback and self.dimension == RiskScenarioDimension.ASSET_CLASS:
            raise ValueError("asset-class stress cannot use metadata fallback")
        return self


class RiskStressOutput(StrictModel):
    kind: Literal[RiskOutputKind.STRESS] = Field(default=RiskOutputKind.STRESS, json_schema_extra={"enum": ["stress"]})
    method: RiskStressMethod
    dimension: Optional[RiskScenarioDimension] = None
    portfolio_return: Optional[FiniteFloat] = None
    impact_amount: Optional[SafeDecimal] = None
    replay_range: Optional[DateRangeModel] = None
    classification_coverage: Optional[FiniteFloat] = Field(None, ge=0, le=1)
    impacts: List[RiskStressImpact] = Field(default_factory=list)
    configured_buckets: List[RiskStressConfiguredBucketImpact] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_method_contract(self) -> RiskStressOutput:
        if self.method == RiskStressMethod.HYPOTHETICAL:
            if self.dimension is None:
                raise ValueError("hypothetical stress requires a dimension")
            if self.replay_range is not None:
                raise ValueError("hypothetical stress cannot expose replay_range")
            if self.classification_coverage is None:
                raise ValueError("hypothetical stress requires classification_coverage")
            if any(item.dimension != self.dimension for item in self.impacts):
                raise ValueError("hypothetical impacts must use the output dimension")
            bucket_ids = [item.bucket_id for item in self.configured_buckets]
            if bucket_ids != sorted(bucket_ids) or len(bucket_ids) != len(set(bucket_ids)):
                raise ValueError("configured stress buckets must be unique and ordered")
        elif self.dimension is not None or self.classification_coverage is not None or self.configured_buckets:
            raise ValueError("historical replay cannot expose hypothetical bucket metadata")
        return self


class RiskComparisonPoint(StrictModel):
    date: date
    primary_cumulative_return: FiniteFloat
    comparison_cumulative_return: FiniteFloat
    primary_drawdown: FiniteFloat = Field(..., le=0)
    comparison_drawdown: FiniteFloat = Field(..., le=0)


class RiskComparisonHoldingItem(StrictModel):
    """One holding of the scope against the same comparison asset, measured in the same request."""

    asset_id: PositiveInt
    beta: Optional[FiniteFloat] = None
    correlation: Optional[FiniteFloat] = Field(None, ge=-1, le=1)


class RiskComparisonOutput(StrictModel):
    kind: Literal[RiskOutputKind.COMPARISON] = Field(default=RiskOutputKind.COMPARISON, json_schema_extra={"enum": ["comparison"]})
    comparison_asset_id: PositiveInt
    active_return: FiniteFloat
    tracking_error: FiniteFloat = Field(..., ge=0)
    information_ratio: Optional[FiniteFloat] = None
    correlation: Optional[FiniteFloat] = Field(None, ge=-1, le=1)
    beta: Optional[FiniteFloat] = None
    observations: int = Field(..., ge=0)
    # The reference's own risk and reward, so a risk/return plot can place the
    # benchmark without a second analytic and without re-deriving the arithmetic in
    # the client. Both are measured on the *common* observations the beta above used,
    # never on the comparison asset's full history: a diamond drawn from a different
    # window than the dots would sit somewhere no measurement puts it.
    comparison_volatility: Optional[FiniteFloat] = Field(None, ge=0)
    # Arithmetic, matching RiskReturnItem.expected_annual_return. See
    # services/risk/metrics.annualized_expected_return for why the convention is not
    # interchangeable with a compounded one.
    comparison_expected_annual_return: Optional[FiniteFloat] = None
    # The reference's own Sharpe and Sortino, on the observations and the factor of its volatility
    # and return above, so a benchmark row reads one measurement. They are charged the request's
    # risk-free rate and target return, as the portfolio's KPI is.
    comparison_sharpe: Optional[FiniteFloat] = None
    comparison_sortino: Optional[FiniteFloat] = None
    series: List[RiskComparisonPoint] = Field(default_factory=list)
    # On a portfolio scope, each holding against the same reference, measured in this request on
    # its joint calendar — in current composition the calendar the portfolio's own beta is read on.
    # The reference is never one of them, even when it is held (D371): it is the yardstick. Empty on
    # an asset scope, whose only subject is the asset the fields above describe.
    items: List[RiskComparisonHoldingItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_holdings(self) -> RiskComparisonOutput:
        """The reference is the yardstick, so it is never also measured; each holding appears once."""
        asset_ids = [item.asset_id for item in self.items]
        if self.comparison_asset_id in asset_ids:
            raise ValueError("the comparison asset cannot appear among the compared holdings")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("a holding cannot appear twice among the compared holdings")
        return self


class RiskVarCvarBin(StrictModel):
    """One bucket of the horizon-compounded return distribution.

    ⚠️ SIGN CONVENTION — this model lives in **signed return space**: a loss is a
    negative bound, so the left-hand bins are the losing ones. Its sibling fields
    ``value_at_risk`` and ``conditional_value_at_risk`` on :class:`RiskVarCvarOutput`
    are **positive loss magnitudes** instead, because a zero floor is applied there.
    Two conventions therefore coexist in one payload, deliberately: the histogram
    must show gains, while the headline tail figures must never render negative.
    Cross the boundary with :attr:`RiskVarCvarOutput.var_bin_edge`, which is the
    same cut expressed in this model's space.

    Bounds are decimal ratios (``-0.1`` == a 10% loss over the horizon), never
    percentages. The interval is half-open ``[lower_bound, upper_bound)`` except for
    the last bin of a series, which includes its upper bound.
    """

    lower_bound: FiniteFloat
    upper_bound: FiniteFloat
    count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_bin_width(self) -> RiskVarCvarBin:
        if self.upper_bound <= self.lower_bound:
            raise ValueError("upper_bound must be greater than lower_bound")
        return self


class RiskWorstHorizonWindow(StrictModel):
    """The worst stretch of one horizon the series actually went through.

    The VaR and the CVaR are statistics of the whole distribution of compounded windows; this is
    the single lowest window, the one a reader can look up. `compounded_return` is the holding-period
    return of the window (a loss when negative). `start_date` and `end_date` are the dates of the
    first and of the last daily return compounded in it, both inclusive, so the stretch ran from the
    close before `start_date` to the close of `end_date`.
    """

    compounded_return: FiniteFloat = Field(..., ge=-1)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> RiskWorstHorizonWindow:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class RiskVarCvarOutput(StrictModel):
    """Historical VaR and CVaR at one confidence level and one horizon.

    `horizon_days` is the requested horizon in **calendar days**. The tail is
    estimated on returns compounded over `horizon_observations` consecutive
    observations: the number the series holds in that many calendar days at its
    observed frequency, so a 30-day month is 21 observations of a series quoted on
    trading days and 30 of one quoted every day. `observations` counts the
    compounded windows the tail was estimated from, `horizon_observations - 1`
    fewer than the series' returns.
    """

    kind: Literal[RiskOutputKind.VAR_CVAR] = Field(default=RiskOutputKind.VAR_CVAR, json_schema_extra={"enum": ["var_cvar"]})
    confidence_level: FiniteFloat = Field(..., gt=0, lt=1)
    horizon_days: PositiveInt
    horizon_observations: PositiveInt
    observations: PositiveInt
    value_at_risk: FiniteFloat = Field(..., ge=0)
    conditional_value_at_risk: FiniteFloat = Field(..., ge=0)
    return_bins: List[RiskVarCvarBin] = Field(default_factory=list)
    var_bin_edge: Optional[FiniteFloat] = None
    worst_horizon: Optional[RiskWorstHorizonWindow] = None

    @model_validator(mode="after")
    def validate_tail_ordering(self) -> RiskVarCvarOutput:
        if self.conditional_value_at_risk < self.value_at_risk:
            raise ValueError("conditional_value_at_risk must be >= value_at_risk")
        return self

    @model_validator(mode="after")
    def validate_return_bins(self) -> RiskVarCvarOutput:
        previous: Optional[RiskVarCvarBin] = None
        for current in self.return_bins:
            if previous is not None and current.lower_bound <= previous.lower_bound:
                raise ValueError("return_bins must be ordered by ascending lower_bound")
            previous = current
        return self


class RiskSimulationBandPoint(StrictModel):
    """One cumulative-return percentile band at a simulated day."""

    day: int = Field(..., ge=0)
    p05: FiniteFloat = Field(..., gt=-1)
    p50: FiniteFloat = Field(..., gt=-1)
    p95: FiniteFloat = Field(..., gt=-1)

    @model_validator(mode="after")
    def validate_percentile_order(self) -> RiskSimulationBandPoint:
        if not self.p05 <= self.p50 <= self.p95:
            raise ValueError("simulation percentiles must satisfy p05 <= p50 <= p95")
        return self


class RiskSimulationOutput(StrictModel):
    """Renderer-neutral conditional simulation result."""

    kind: Literal[RiskOutputKind.SIMULATION] = Field(default=RiskOutputKind.SIMULATION, json_schema_extra={"enum": ["simulation"]})
    process: RiskSimulationProcess
    regime: RiskSimulationRegime = RiskSimulationRegime.NONE
    sampling_method: RiskSamplingStrategy
    horizon_days: PositiveInt
    path_count: PositiveInt
    block_length_days: PositiveInt | None = None
    regime_declared_days: PositiveInt | None = None
    regime_applied_days: PositiveInt | None = None
    drift_estimator: RiskSimulationDriftEstimator
    covariance_estimator: RiskSimulationCovarianceEstimator
    aggregation_policy: RiskCompositionPolicy
    costs_included: bool = False
    cash_flows_included: bool = False
    inflation_included: bool = False
    rebalanced: bool = False
    percentile_bands: List[RiskSimulationBandPoint] = Field(..., min_length=2)
    terminal_mean_return: FiniteFloat = Field(..., gt=-1)
    terminal_volatility: FiniteFloat = Field(..., ge=0)
    probability_of_loss: FiniteFloat = Field(..., ge=0, le=1)
    drift_uncertainty_factor: Optional[FiniteFloat] = Field(
        None,
        ge=1,
        description="95% confidence factor on the cumulative drift, from estimation error alone. Multiplicative: the band it qualifies is compounded.",
    )
    drift_uncertainty_observations: Optional[PositiveInt] = Field(
        None,
        description="Sample size the drift was estimated from, so the factor can be read as a consequence rather than a verdict.",
    )

    @model_validator(mode="after")
    def validate_drift_uncertainty_disclosure(self) -> RiskSimulationOutput:
        """A factor without its sample size is a number nobody can argue with."""
        if (self.drift_uncertainty_factor is None) != (self.drift_uncertainty_observations is None):
            raise ValueError("drift uncertainty must disclose both the factor and the observation count")
        return self

    @model_validator(mode="after")
    def validate_regime_disclosure(self) -> RiskSimulationOutput:
        """Force every prescribed hypothesis to be disclosed, never implied."""
        if self.process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
            if self.block_length_days is None:
                raise ValueError("block bootstrap results must disclose block_length_days")
        elif self.block_length_days is not None:
            raise ValueError("block_length_days is meaningful only for the block bootstrap process")
        if self.regime == RiskSimulationRegime.NONE:
            if self.regime_declared_days is not None or self.regime_applied_days is not None:
                raise ValueError("regime day counts are meaningful only for a prescribed regime")
            return self
        if self.process != RiskSimulationProcess.BLOCK_BOOTSTRAP:
            raise ValueError("prescribed regimes require the block bootstrap process")
        if self.regime_declared_days is None or self.regime_applied_days is None:
            raise ValueError("a prescribed regime must disclose declared and applied day counts")
        if self.regime_applied_days > self.regime_declared_days:
            raise ValueError("regime_applied_days cannot exceed regime_declared_days")
        return self

    @model_validator(mode="after")
    def validate_band_horizon(self) -> RiskSimulationOutput:
        expected_days = list(range(self.horizon_days + 1))
        if [point.day for point in self.percentile_bands] != expected_days:
            raise ValueError("simulation percentile bands must cover every day from zero through horizon_days")
        initial = self.percentile_bands[0]
        if not all(math.isclose(value, 0.0, rel_tol=0.0, abs_tol=1e-12) for value in (initial.p05, initial.p50, initial.p95)):
            raise ValueError("simulation percentile bands must start at zero cumulative return")
        return self


class RiskOptimizationWeight(StrictModel):
    """One optimized asset weight and its volatility contribution."""

    asset_id: int
    weight: FiniteFloat = Field(..., ge=0, le=1)
    marginal_risk_contribution: FiniteFloat
    component_risk_contribution: FiniteFloat
    percentage_risk_contribution: FiniteFloat


class RiskOptimizationConstraintSummary(StrictModel):
    """Effective long-only budget constraints."""

    min_weight: FiniteFloat = Field(..., ge=0, le=1)
    max_weight: FiniteFloat = Field(..., ge=0, le=1)
    budget: Literal[1] = 1
    long_only: Literal[True] = True
    leverage_allowed: Literal[False] = False


class RiskOptimizationFrontierPoint(StrictModel):
    """One portfolio on the efficient frontier."""

    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    sharpe_ratio: Optional[FiniteFloat] = None
    weights: List[RiskOptimizationWeight] = Field(..., min_length=2)


class RiskOptimizationSensitivityPoint(StrictModel):
    """Recomputed solution under another covariance estimator."""

    covariance_estimator: RiskCovarianceEstimator
    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    max_absolute_weight_delta: FiniteFloat = Field(..., ge=0)
    weights: List[RiskOptimizationWeight] = Field(..., min_length=2)


class RiskPortfolioOptimizationOutput(StrictModel):
    """Renderer-neutral long-only portfolio optimization result."""

    kind: Literal[RiskOutputKind.OPTIMIZATION] = Field(
        default=RiskOutputKind.OPTIMIZATION,
        json_schema_extra={"enum": ["optimization"]},
    )
    strategy: RiskOptimizationStrategy
    covariance_estimator: RiskCovarianceEstimator
    solver: RiskOptimizationSolver
    solver_status: str = Field(..., min_length=1)
    risk_free_annual_rate: Optional[FiniteFloat] = None
    expected_period_return: FiniteFloat
    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    sharpe_ratio: Optional[FiniteFloat] = None
    weights: List[RiskOptimizationWeight] = Field(..., min_length=2)
    constraints: RiskOptimizationConstraintSummary
    frontier: List[RiskOptimizationFrontierPoint] = Field(default_factory=list)
    sensitivity: List[RiskOptimizationSensitivityPoint] = Field(default_factory=list)
    method: str = Field(..., min_length=1)
    algorithm_version: str = Field(..., min_length=1)


class RiskDrawdownPoint(StrictModel):
    """One dated point of the underwater (peak-relative) drawdown curve.

    ``drawdown`` is a decimal ratio and never positive: ``0.0`` means the series is
    at a new high, ``-0.1`` means 10% below the running peak. The convention matches
    :class:`RiskComparisonPoint`, and percentage formatting stays a renderer concern.
    """

    date: date
    drawdown: FiniteFloat = Field(..., le=0)


class RiskDrawdownOutput(StrictModel):
    """Renderer-neutral current and maximum drawdown episode summary.

    All magnitudes are decimal ratios (``-0.1`` == 10% peak-relative decline);
    percentage formatting is a renderer concern handled by a later todo.
    """

    kind: Literal[RiskOutputKind.DRAWDOWN] = Field(default=RiskOutputKind.DRAWDOWN, json_schema_extra={"enum": ["drawdown"]})
    current_drawdown: FiniteFloat = Field(..., le=0)
    current_peak_date: date
    current_drawdown_duration_days: int = Field(..., ge=0)
    maximum_drawdown: FiniteFloat = Field(..., le=0)
    maximum_drawdown_peak_date: Optional[date] = None
    maximum_drawdown_trough_date: Optional[date] = None
    maximum_drawdown_recovery_status: RiskDrawdownRecoveryStatus
    maximum_drawdown_recovery_date: Optional[date] = None
    maximum_drawdown_duration_days: int = Field(..., ge=0)
    maximum_drawdown_recovered_ratio: Optional[FiniteFloat] = Field(None, ge=0, le=1)
    maximum_drawdown_trough_to_peak_ratio: Optional[FiniteFloat] = Field(
        None,
        ge=0,
        description="Gain needed to climb from the maximum drawdown's trough back to the peak before it (0.25 = +25 %); 0 without a drawdown, null for a total loss.",
    )
    remaining_to_peak_ratio: Optional[FiniteFloat] = Field(..., ge=0, description="Gain still needed to climb from the current value back to the running peak; 0 when not underwater, null for a total loss.")
    available_start: date
    available_end: date
    n_observations: int = Field(..., ge=0)
    coverage: FiniteFloat = Field(..., ge=0, le=1)
    calculation_basis: str = Field(..., min_length=1)
    return_basis: RiskReturnBasis
    underwater_series: List[RiskDrawdownPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_episode_contract(self) -> RiskDrawdownOutput:  # noqa: C901 — flat status-branch invariant raises
        if self.available_end < self.available_start:
            raise ValueError("available_end must not precede available_start")
        status = self.maximum_drawdown_recovery_status
        if status == RiskDrawdownRecoveryStatus.NO_DRAWDOWN:
            if self.maximum_drawdown != 0:
                raise ValueError("no_drawdown requires a zero maximum_drawdown")
            if self.maximum_drawdown_peak_date is not None or self.maximum_drawdown_trough_date is not None or self.maximum_drawdown_recovery_date is not None:
                raise ValueError("no_drawdown must not expose episode dates")
            if self.maximum_drawdown_recovered_ratio is not None:
                raise ValueError("no_drawdown must not expose a recovered ratio")
            if self.maximum_drawdown_trough_to_peak_ratio is not None and self.maximum_drawdown_trough_to_peak_ratio > 0:
                raise ValueError("no_drawdown must not expose a positive trough-to-peak ratio")
            if self.maximum_drawdown_duration_days != 0:
                raise ValueError("no_drawdown must report a zero maximum duration")
        else:
            if self.maximum_drawdown >= 0:
                raise ValueError("a drawdown episode requires a negative maximum_drawdown")
            if self.maximum_drawdown_peak_date is None or self.maximum_drawdown_trough_date is None:
                raise ValueError("a drawdown episode requires peak and trough dates")
            if self.maximum_drawdown_trough_date < self.maximum_drawdown_peak_date:
                raise ValueError("maximum_drawdown_trough_date must not precede the peak date")
            if self.maximum_drawdown_recovered_ratio is None:
                raise ValueError("a drawdown episode requires a recovered ratio")
            if status == RiskDrawdownRecoveryStatus.RECOVERED:
                if self.maximum_drawdown_recovery_date is None:
                    raise ValueError("recovered episodes require a recovery date")
                if self.maximum_drawdown_recovery_date < self.maximum_drawdown_trough_date:
                    raise ValueError("recovery date must not precede the trough date")
            elif self.maximum_drawdown_recovery_date is not None:
                raise ValueError("open episodes must not expose a recovery date")
        return self


# ---------------------------------------------------------------------------
# The weightless multi-asset family — outputs for the ASSET_SET scope.
#
# WHY THESE ARE NEW SHAPES AND NOT NEW FIELDS ON THE FOUR ABOVE.
# An asset set is *n* independent series with no weights. The four singular
# outputs above each describe **one** series, and their leading scalars
# (`volatility`, `max_drawdown`, `value_at_risk`, …) are required. Adding a
# per-asset list to them would have meant making those scalars optional — a
# substitutive change to a shipped contract, and worse, the precise mechanism by
# which an absent quantity becomes expressible again. A separate shape that
# simply **has no field** for the aggregate cannot be handed one by accident:
# every model here inherits `extra="forbid"`, so fabricating a set-level figure
# would require editing this file, which is visible in a diff and pinned by a
# test.
#
# WHY NO PER-ASSET `n_observations`. `PreparedAssetSeriesSet` validates that
# every series in one prepared set uses the same joint calendar, so within a
# single request that number is a **constant**. Publishing it per asset would
# not be redundant but misleading: it would suggest the values could differ,
# which is exactly what the one-preparation-per-request rule guarantees they
# cannot. It travels once, in `RiskResultMetadata.n_observations`.
#
# WHY NO `weight` ANYWHERE. `RiskStressImpact.weight` is `Optional` because
# `stress` serves weighted and weightless scopes with one shape. These models
# serve only the weightless one, so the field is absent rather than always-null.
# WHY `items` IS REQUIRED ON ALL FIVE, where every sibling output above defaults
# it to an empty list. The list *is* the payload here: these analytics have no
# set-level figure to fall back on, so an output that omitted `items` would carry
# nothing at all. Defaulting it would let "the analytic returned no rows" and
# "the key never arrived" collapse into the same `[]` on the client, which is the
# distinction clause (3) — declare an omission, never zero-fill it — exists to
# keep. A successful result always states its rows, even when there are none.
#
# It also keeps the family uniform with the ten singular outputs in one respect
# that matters to the build: each of those has at least one required field, and a
# schema with no required field at all is emitted by openapi-zod-client as
# `z.object({...}).partial()`, which makes every property optional — including
# the `kind` discriminator that `z.discriminatedUnion` needs to be required.
# ---------------------------------------------------------------------------


class RiskAssetSetKpiItem(StrictModel):
    """Historical risk KPIs of one asset, measured on the shared joint calendar."""

    asset_id: PositiveInt
    volatility: FiniteFloat = Field(..., ge=0)
    max_drawdown: FiniteFloat = Field(..., le=0)
    max_drawdown_duration_days: int = Field(..., ge=0)
    sharpe: Optional[FiniteFloat] = None
    sortino: Optional[FiniteFloat] = None
    worst_realization: Optional[FiniteFloat] = Field(None, le=0)
    worst_realization_date: Optional[date] = None
    drawdown_at_risk: Optional[FiniteFloat] = Field(None, le=0)
    conditional_drawdown_at_risk: Optional[FiniteFloat] = Field(None, le=0)
    ulcer_index: Optional[FiniteFloat] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_drawdown_tail_ordering(self) -> RiskAssetSetKpiItem:
        """Same invariant as :class:`RiskKpiOutput`, applied per asset.

        Both tail values are negative and both are plausible alone; only their
        order distinguishes the quantile from its conditional mean, so no range
        constraint can catch a swapped assignment.
        """
        if self.drawdown_at_risk is not None and self.conditional_drawdown_at_risk is not None and self.conditional_drawdown_at_risk > self.drawdown_at_risk:
            raise ValueError("conditional_drawdown_at_risk must be <= drawdown_at_risk")
        if self.conditional_drawdown_at_risk is not None and self.max_drawdown > self.conditional_drawdown_at_risk:
            raise ValueError("conditional_drawdown_at_risk must be >= max_drawdown")
        return self


class RiskAssetSetKpiOutput(StrictModel):
    """One KPI row per selected asset, and deliberately no row for the set."""

    kind: Literal[RiskOutputKind.KPI_SET] = Field(default=RiskOutputKind.KPI_SET, json_schema_extra={"enum": ["kpi_set"]})
    # An echo of the request parameter, identical for every item. It is a choice
    # the caller made, not a measurement, which is why it sits at set level.
    drawdown_confidence_level: Optional[FiniteFloat] = Field(None, gt=0, lt=1)
    items: List[RiskAssetSetKpiItem]


class RiskAssetSetVarCvarItem(StrictModel):
    """Historical-simulation tail risk of one asset."""

    asset_id: PositiveInt
    value_at_risk: FiniteFloat = Field(..., ge=0)
    conditional_value_at_risk: FiniteFloat = Field(..., ge=0)
    worst_horizon: Optional[RiskWorstHorizonWindow] = None

    @model_validator(mode="after")
    def validate_tail_ordering(self) -> RiskAssetSetVarCvarItem:
        if self.conditional_value_at_risk < self.value_at_risk:
            raise ValueError("conditional_value_at_risk must be >= value_at_risk")
        return self


class RiskAssetSetVarCvarOutput(StrictModel):
    """Per-asset VaR and CVaR at one confidence level and one horizon.

    `observations` sits here and not on each row for the same reason
    `n_observations` is not repeated per asset: one joint calendar compounded to
    one horizon gives every asset the same count, so a per-row copy would suggest
    they could differ. It is stated anyway, rather than left to the metadata,
    because compounding to a multi-day horizon *consumes* observations — this is
    the count the tail was actually estimated from, which is
    `horizon_observations - 1` fewer than the window's. As on the singular output,
    `horizon_days` is in calendar days and `horizon_observations` is what the joint
    calendar holds in them.

    No `return_bins`. The singular :class:`RiskVarCvarOutput` publishes a
    histogram because one surface draws one distribution; *n* histograms would
    be *n* charts nobody has asked for. Adding them later is additive, whereas
    shipping them now would put weight on a contract to carry something unread.
    """

    kind: Literal[RiskOutputKind.VAR_CVAR_SET] = Field(default=RiskOutputKind.VAR_CVAR_SET, json_schema_extra={"enum": ["var_cvar_set"]})
    confidence_level: FiniteFloat = Field(..., gt=0, lt=1)
    horizon_days: PositiveInt
    horizon_observations: PositiveInt
    observations: PositiveInt
    items: List[RiskAssetSetVarCvarItem]


class RiskAssetSetDrawdownItem(StrictModel):
    """Dated current and maximum drawdown episode of one asset."""

    asset_id: PositiveInt
    current_drawdown: FiniteFloat = Field(..., le=0)
    current_peak_date: date
    current_drawdown_duration_days: int = Field(..., ge=0)
    maximum_drawdown: FiniteFloat = Field(..., le=0)
    maximum_drawdown_peak_date: Optional[date] = None
    maximum_drawdown_trough_date: Optional[date] = None
    maximum_drawdown_recovery_status: RiskDrawdownRecoveryStatus
    maximum_drawdown_recovery_date: Optional[date] = None
    maximum_drawdown_duration_days: int = Field(..., ge=0)
    maximum_drawdown_recovered_ratio: Optional[FiniteFloat] = Field(None, ge=0, le=1)
    maximum_drawdown_trough_to_peak_ratio: Optional[FiniteFloat] = Field(
        None,
        ge=0,
        description="Gain needed to climb from the maximum drawdown's trough back to the peak before it (0.25 = +25 %); 0 without a drawdown, null for a total loss.",
    )
    remaining_to_peak_ratio: Optional[FiniteFloat] = Field(..., ge=0, description="Gain still needed to climb from the current value back to the running peak; 0 when not underwater, null for a total loss.")

    @model_validator(mode="after")
    def validate_episode_contract(self) -> RiskAssetSetDrawdownItem:  # noqa: C901 — flat status-branch invariant raises
        """Same episode contract as :class:`RiskDrawdownOutput`, applied per asset."""
        status = self.maximum_drawdown_recovery_status
        if status == RiskDrawdownRecoveryStatus.NO_DRAWDOWN:
            if self.maximum_drawdown != 0:
                raise ValueError("no_drawdown requires a zero maximum_drawdown")
            if self.maximum_drawdown_peak_date is not None or self.maximum_drawdown_trough_date is not None or self.maximum_drawdown_recovery_date is not None:
                raise ValueError("no_drawdown must not expose episode dates")
            if self.maximum_drawdown_recovered_ratio is not None:
                raise ValueError("no_drawdown must not expose a recovered ratio")
            if self.maximum_drawdown_trough_to_peak_ratio is not None and self.maximum_drawdown_trough_to_peak_ratio > 0:
                raise ValueError("no_drawdown must not expose a positive trough-to-peak ratio")
            if self.maximum_drawdown_duration_days != 0:
                raise ValueError("no_drawdown must report a zero maximum duration")
            return self
        if self.maximum_drawdown >= 0:
            raise ValueError("a drawdown episode requires a negative maximum_drawdown")
        if self.maximum_drawdown_peak_date is None or self.maximum_drawdown_trough_date is None:
            raise ValueError("a drawdown episode requires peak and trough dates")
        if self.maximum_drawdown_trough_date < self.maximum_drawdown_peak_date:
            raise ValueError("maximum_drawdown_trough_date must not precede the peak date")
        if self.maximum_drawdown_recovered_ratio is None:
            raise ValueError("a drawdown episode requires a recovered ratio")
        if status == RiskDrawdownRecoveryStatus.RECOVERED:
            if self.maximum_drawdown_recovery_date is None:
                raise ValueError("recovered episodes require a recovery date")
            if self.maximum_drawdown_recovery_date < self.maximum_drawdown_trough_date:
                raise ValueError("recovery date must not precede the trough date")
        elif self.maximum_drawdown_recovery_date is not None:
            raise ValueError("open episodes must not expose a recovery date")
        return self


class RiskAssetSetDrawdownOutput(StrictModel):
    """One drawdown episode per selected asset over one shared window.

    `available_start` / `available_end` sit at set level rather than on every
    item because the joint calendar makes them identical for all of them — the
    same reason `n_observations` is not repeated per asset.

    No per-asset `underwater_series`. The singular output carries one dated curve
    for one chart; *n* curves would be a different chart that does not exist yet,
    and publishing them unread is how a payload grows fields nobody maintains.
    """

    kind: Literal[RiskOutputKind.DRAWDOWN_SET] = Field(default=RiskOutputKind.DRAWDOWN_SET, json_schema_extra={"enum": ["drawdown_set"]})
    available_start: date
    available_end: date
    calculation_basis: str = Field(..., min_length=1)
    return_basis: RiskReturnBasis
    items: List[RiskAssetSetDrawdownItem]

    @model_validator(mode="after")
    def validate_window(self) -> RiskAssetSetDrawdownOutput:
        if self.available_end < self.available_start:
            raise ValueError("available_end must not precede available_start")
        return self


class RiskAssetSetReturnItem(StrictModel):
    """One point of a weightless risk/return plot: what it risks, what it is expected to pay."""

    asset_id: PositiveInt
    volatility: FiniteFloat = Field(..., ge=0)
    # Arithmetic, exactly as RiskReturnItem.expected_annual_return. See
    # services/risk/metrics.annualized_expected_return: paired with the
    # annualized volatility it makes the slope from a risk-free intercept
    # identically the Sharpe ratio. It is NOT what a holder earned.
    expected_annual_return: FiniteFloat


class RiskAssetSetReturnOutput(StrictModel):
    """Per-asset risk and reward for a selection that has no composition.

    🔴 THERE IS NO PORTFOLIO PAIR IN THIS MODEL, AND ITS ABSENCE IS THE FEATURE.

    On a scatter, the judgement "paid well for the risk" is the Capital Market
    Line, and the line is not suppressed by a setting: it is drawn only when the
    payload yields a point whose role is the portfolio, which in turn exists only
    when a portfolio volatility *and* expected return are both present. A
    selection of assets has no weights, so it has no whole — the point cannot be
    measured, the line cannot be drawn, and the judgement the comparison surface
    forbids is impossible rather than merely disabled.

    That impossibility lasts exactly as long as this model has no field to put an
    aggregate in. An equally weighted average computed "for convenience" would
    restore the point, restore the line, and restore the judgement **through the
    data**, invisible to any test of the renderer — because the renderer would be
    doing precisely its job. So the defence lives here, in a shape, and not in a
    flag: `extra="forbid"` means the fabricated figure is not merely absent but
    unexpressible, and making it expressible again requires an edit to this file.

    There is also no `cash_weight`: a selection holds no cash residual, so a zero
    would be a measurement of something that was never measured.
    """

    kind: Literal[RiskOutputKind.RISK_RETURN_SET] = Field(default=RiskOutputKind.RISK_RETURN_SET, json_schema_extra={"enum": ["risk_return_set"]})
    items: List[RiskAssetSetReturnItem]


class RiskAssetSetComparisonItem(StrictModel):
    """One asset's relative performance against the shared comparison asset."""

    asset_id: PositiveInt
    active_return: FiniteFloat
    tracking_error: FiniteFloat = Field(..., ge=0)
    information_ratio: Optional[FiniteFloat] = None
    correlation: Optional[FiniteFloat] = Field(None, ge=-1, le=1)
    beta: Optional[FiniteFloat] = None


class RiskAssetSetComparisonOutput(StrictModel):
    """Per-asset beta against one reference, plus the reference's own coordinates.

    `comparison_volatility` and `comparison_expected_annual_return` describe the
    **reference asset**, which is a real series with a real measurement — not an
    aggregate of the selection. They are published so a scatter can place the
    benchmark next to the holdings without a second analytic, and they are
    measured on the same joint calendar as every item, because the reference is
    prepared inside the same request as the scope.
    """

    kind: Literal[RiskOutputKind.COMPARISON_SET] = Field(default=RiskOutputKind.COMPARISON_SET, json_schema_extra={"enum": ["comparison_set"]})
    comparison_asset_id: PositiveInt
    observations: int = Field(..., ge=0)
    comparison_volatility: Optional[FiniteFloat] = Field(None, ge=0)
    comparison_expected_annual_return: Optional[FiniteFloat] = None
    # The reference's own Sharpe and Sortino, on the same returns and factor as the two above.
    comparison_sharpe: Optional[FiniteFloat] = None
    comparison_sortino: Optional[FiniteFloat] = None
    items: List[RiskAssetSetComparisonItem]

    @model_validator(mode="after")
    def validate_reference_is_not_a_subject(self) -> RiskAssetSetComparisonOutput:
        """The reference is the yardstick, so it cannot also be one of the measured."""
        if any(item.asset_id == self.comparison_asset_id for item in self.items):
            raise ValueError("the comparison asset cannot appear among the compared items")
        return self


RiskAnalyticOutput = Annotated[
    Union[
        RiskKpiOutput,
        RiskCorrelationOutput,
        RiskContributionOutput,
        RiskReturnOutput,
        RiskStressOutput,
        RiskComparisonOutput,
        RiskVarCvarOutput,
        RiskSimulationOutput,
        RiskPortfolioOptimizationOutput,
        RiskDrawdownOutput,
        RiskAssetSetKpiOutput,
        RiskAssetSetVarCvarOutput,
        RiskAssetSetDrawdownOutput,
        RiskAssetSetReturnOutput,
        RiskAssetSetComparisonOutput,
    ],
    Field(discriminator="kind"),
]
