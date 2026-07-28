"""Strict, non-persisted contracts for risk-series preparation and results."""

from __future__ import annotations

import math
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, JsonValue, PositiveInt, field_validator, model_validator

from backend.app.schemas.common import Currency, DateRangeModel, SafeDecimal
from backend.app.schemas.portfolio import DataQualityReport


class RiskDataFrequency(StrEnum):
    """Mathematical sampling frequency supported by Release 2."""

    DAILY = "daily"


class RiskMode(StrEnum):
    """Portfolio semantics used by a risk calculation."""

    HISTORICAL = "historical"
    CURRENT_COMPOSITION = "current_composition"


class RiskCompositionPolicy(StrEnum):
    """Weight-evolution policy supported for current composition."""

    CURRENT_BUY_AND_HOLD = "current_buy_and_hold"


class RiskReturnBasis(StrEnum):
    """Financial series consumed by a risk result."""

    PRICE_ONLY = "price_only"
    TWRR = "twrr"


class RiskScopeKind(StrEnum):
    """Domain scope resolved before risk analytics execute."""

    ASSET = "asset"
    ASSET_SET = "asset_set"
    PORTFOLIO = "portfolio"
    BROKER = "broker"


class RiskOutputKind(StrEnum):
    """Serializable output family advertised by the risk catalog."""

    KPI = "kpi"
    MATRIX = "matrix"
    CONTRIBUTION = "contribution"
    STRESS = "stress"
    COMPARISON = "comparison"
    VAR_CVAR = "var_cvar"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"


class RiskResultStatus(StrEnum):
    """Per-analytic bulk execution status."""

    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class RiskValueStatus(StrEnum):
    """Status for values that can be undefined independently."""

    OK = "ok"
    INSUFFICIENT = "insufficient"
    UNDEFINED = "undefined"


class RiskErrorCode(StrEnum):
    """Stable machine-readable failures for one analytic result."""

    ANALYTIC_NOT_FOUND = "analytic_not_found"
    INCOMPATIBLE_SCOPE = "incompatible_scope"
    INCOMPATIBLE_MODE = "incompatible_mode"
    INVALID_PARAMETERS = "invalid_parameters"
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNDEFINED_METRIC = "undefined_metric"
    DATA_UNAVAILABLE = "data_unavailable"
    INVALID_COVARIANCE = "invalid_covariance"
    RESOURCE_LIMIT = "resource_limit"
    WORKER_BUSY = "worker_busy"
    EXECUTION_TIMEOUT = "execution_timeout"
    OPTIMIZATION_INFEASIBLE = "optimization_infeasible"
    EXECUTION_FAILED = "execution_failed"


class RiskStressMethod(StrEnum):
    """Deterministic stress methods shipped in Step 4."""

    HYPOTHETICAL = "hypothetical"
    HISTORICAL_REPLAY = "historical_replay"


class RiskSimulationProcess(StrEnum):
    """Stochastic process exposed by the first simulation implementation."""

    GBM = "gbm"


class RiskSamplingStrategy(StrEnum):
    """Sampling strategy used for stochastic simulation."""

    MC = "mc"
    QMC = "qmc"


class RiskOptimizationStrategy(StrEnum):
    """Mean-variance strategies exposed by portfolio optimization."""

    MIN_RISK = "min_risk"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"


class RiskCovarianceEstimator(StrEnum):
    """Riskfolio covariance estimators approved for production."""

    HISTORICAL = "historical"
    LEDOIT_WOLF = "ledoit_wolf"
    OAS = "oas"


class RiskOptimizationSolver(StrEnum):
    """Open-source solvers accepted by the optimization worker."""

    CLARABEL = "clarabel"
    SCS = "scs"


class RiskSimulationDriftEstimator(StrEnum):
    """Drift estimator disclosed by simulation results."""

    HISTORICAL_LOG_MLE = "historical_log_mle"


class RiskSimulationCovarianceEstimator(StrEnum):
    """Covariance estimator disclosed by simulation results."""

    SAMPLE_LOG_RETURNS = "sample_log_returns"


class RiskExcludedAsset(BaseModel):
    """Metric-specific asset exclusion recorded in result metadata."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    reason: str = Field(..., min_length=1)


class RiskFreeReference(BaseModel):
    """Deterministic risk-free reference used only by eligible metrics."""

    model_config = ConfigDict(extra="forbid")

    annual_rate: FiniteFloat = Field(0.0, gt=-1)
    source: str = Field("config", min_length=1)
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)


class AssetValuationPoint(BaseModel):
    """One target-currency valuation with price and FX provenance."""

    model_config = ConfigDict(extra="forbid")

    valuation_date: date
    effective_price_date: date
    is_price_carried_forward: bool
    native_close: SafeDecimal = Field(..., gt=0)
    native_currency: str
    fx_rate: Optional[SafeDecimal] = Field(None, gt=0)
    fx_rate_date: Optional[date] = None
    is_fx_carried_forward: bool = False
    target_close: SafeDecimal = Field(..., gt=0)
    target_currency: str
    price_source: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    @field_validator("native_currency", "target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_provenance(self) -> AssetValuationPoint:
        if self.effective_price_date > self.valuation_date:
            raise ValueError("effective_price_date cannot follow valuation_date")
        if self.is_price_carried_forward != (self.effective_price_date < self.valuation_date):
            raise ValueError("is_price_carried_forward must match effective_price_date")
        if self.native_currency != self.target_currency and (self.fx_rate is None or self.fx_rate_date is None):
            raise ValueError("converted valuations require fx_rate and fx_rate_date")
        if self.is_fx_carried_forward:
            if self.fx_rate_date is None or self.fx_rate_date >= self.valuation_date:
                raise ValueError("carried FX requires an earlier fx_rate_date")
        return self


class AssetReturnPoint(BaseModel):
    """Simple return derived from two converted valuation points."""

    model_config = ConfigDict(extra="forbid")

    date: date
    previous_valuation_date: date
    value: FiniteFloat = Field(..., gt=-1)

    @model_validator(mode="after")
    def validate_dates(self) -> AssetReturnPoint:
        if self.previous_valuation_date >= self.date:
            raise ValueError("previous_valuation_date must precede date")
        return self


class AssetValuationSeries(BaseModel):
    """Converted valuation series for one asset on the joint calendar."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    target_currency: str
    points: List[AssetValuationPoint] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_points(self) -> AssetValuationSeries:
        dates = [point.valuation_date for point in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("valuation points must have unique ascending dates")
        if any(point.target_currency != self.target_currency for point in self.points):
            raise ValueError("valuation point target currency must match its series")
        return self


class AssetReturnSeries(BaseModel):
    """Price-only simple-return series for one asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    target_currency: str
    return_basis: RiskReturnBasis = RiskReturnBasis.PRICE_ONLY
    points: List[AssetReturnPoint] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_points(self) -> AssetReturnSeries:
        dates = [point.date for point in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("return points must have unique ascending dates")
        return self


class PreparedAssetSeries(BaseModel):
    """Canonical valuation and return series for one asset."""

    model_config = ConfigDict(extra="forbid")

    valuations: AssetValuationSeries
    returns: AssetReturnSeries

    @model_validator(mode="after")
    def validate_alignment(self) -> PreparedAssetSeries:
        if self.valuations.asset_id != self.returns.asset_id:
            raise ValueError("valuation and return series asset_id must match")
        if self.valuations.target_currency != self.returns.target_currency:
            raise ValueError("valuation and return series currency must match")
        valuation_dates = [point.valuation_date for point in self.valuations.points]
        return_dates = [point.date for point in self.returns.points]
        expected_return_dates = valuation_dates[1:]
        if return_dates != expected_return_dates:
            raise ValueError("returns must be derived from consecutive valuation points")
        for previous, current, return_point in zip(
            valuation_dates[:-1],
            valuation_dates[1:],
            self.returns.points,
            strict=True,
        ):
            if return_point.previous_valuation_date != previous or return_point.date != current:
                raise ValueError("return provenance must match valuation dates")
        return self


class PreparedAssetSeriesSet(BaseModel):
    """Canonical common-calendar series ready for risk analytics."""

    model_config = ConfigDict(extra="forbid")

    requested_range: DateRangeModel
    baseline_date: Optional[date] = None
    effective_range: Optional[DateRangeModel] = None
    target_currency: str
    series: List[PreparedAssetSeries] = Field(default_factory=list)
    joint_valuation_dates: List[date] = Field(default_factory=list)
    joint_return_dates: List[date] = Field(default_factory=list)
    n_observations: int = Field(0, ge=0)
    calendar_days: int = Field(0, ge=0)
    annualization_factor: Optional[FiniteFloat] = Field(None, gt=0)
    calendar_coverage: FiniteFloat = Field(0.0, ge=0, le=1)
    fresh_quote_coverage: FiniteFloat = Field(0.0, ge=0, le=1)
    data_quality: DataQualityReport = Field(default_factory=DataQualityReport)
    fx_fingerprint: str = Field(..., pattern="^[0-9a-f]{64}$")
    warnings: List[str] = Field(default_factory=list)

    @field_validator("target_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_alignment(self) -> PreparedAssetSeriesSet:
        asset_ids = [item.valuations.asset_id for item in self.series]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("prepared asset series must have unique asset IDs")
        if self.joint_valuation_dates != sorted(set(self.joint_valuation_dates)):
            raise ValueError("joint valuation dates must be unique and ascending")
        if self.joint_return_dates != sorted(set(self.joint_return_dates)):
            raise ValueError("joint return dates must be unique and ascending")
        if self.joint_return_dates != self.joint_valuation_dates[1:]:
            raise ValueError("joint return dates must exclude only the valuation baseline")
        if self.n_observations != len(self.joint_return_dates):
            raise ValueError("n_observations must match joint return dates")
        if any([point.valuation_date for point in item.valuations.points] != self.joint_valuation_dates or [point.date for point in item.returns.points] != self.joint_return_dates or item.valuations.target_currency != self.target_currency for item in self.series):
            raise ValueError("every asset series must use the same joint calendar and target currency")
        if self.n_observations == 0:
            if self.calendar_days != 0 or self.annualization_factor is not None or self.effective_range is not None:
                raise ValueError("empty prepared series cannot expose annualization metadata")
            return self
        if self.baseline_date is None or self.effective_range is None:
            raise ValueError("non-empty prepared series requires baseline and effective range")
        if self.effective_range.start != self.joint_return_dates[0] or self.effective_range.end != self.joint_return_dates[-1]:
            raise ValueError("effective_range must match joint return dates")
        expected_days = (self.joint_return_dates[-1] - self.baseline_date).days
        if self.calendar_days != expected_days or self.calendar_days <= 0:
            raise ValueError("calendar_days must span baseline to final return")
        expected_factor = self.n_observations * 365 / self.calendar_days
        if self.annualization_factor is None or not math.isclose(self.annualization_factor, expected_factor, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("annualization_factor must equal n_observations * 365 / calendar_days")
        return self


class RiskResultMetadata(BaseModel):
    """Execution context shared by all serialized risk results."""

    model_config = ConfigDict(extra="forbid")

    analyzed_range: DateRangeModel
    frequency: RiskDataFrequency = RiskDataFrequency.DAILY
    n_observations: int = Field(..., ge=0)
    calendar_days: int = Field(..., ge=0)
    annualization_factor: Optional[FiniteFloat] = Field(None, gt=0)
    coverage: FiniteFloat = Field(..., ge=0, le=1)
    currency: str
    scope: Optional[RiskScopeKind] = None
    method: Optional[str] = None
    params: Dict[str, JsonValue] = Field(default_factory=dict)
    mode: Optional[RiskMode] = None
    composition_policy: Optional[RiskCompositionPolicy] = None
    return_basis: RiskReturnBasis
    comparison_asset_id: Optional[int] = None
    risk_free: Optional[RiskFreeReference] = None
    excluded_assets: List[RiskExcludedAsset] = Field(default_factory=list)
    algorithm_version: str = Field(..., min_length=1)
    computed_at: datetime
    sampling_method: Optional[RiskSamplingStrategy] = None
    path_count: Optional[int] = Field(None, ge=1)
    random_seed: Optional[int] = Field(None, ge=0, le=2**32 - 1)
    sobol_start_index: Optional[int] = Field(None, ge=0, le=2**32 - 1)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @field_validator("computed_at")
    @classmethod
    def validate_computed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("computed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> RiskResultMetadata:
        if self.n_observations == 0:
            if self.calendar_days != 0 or self.annualization_factor is not None:
                raise ValueError("empty results cannot expose annualization metadata")
        else:
            if self.calendar_days <= 0:
                raise ValueError("non-empty results require positive calendar_days")
            expected_factor = self.n_observations * 365 / self.calendar_days
            if self.annualization_factor is None or not math.isclose(self.annualization_factor, expected_factor, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError("annualization_factor must equal n_observations * 365 / calendar_days")
        if self.mode == RiskMode.HISTORICAL and self.composition_policy is not None:
            raise ValueError("historical mode cannot declare a composition policy")
        if self.mode == RiskMode.CURRENT_COMPOSITION and self.composition_policy is None:
            raise ValueError("current_composition requires a composition policy")
        if self.sampling_method is None:
            if self.path_count is not None or self.random_seed is not None or self.sobol_start_index is not None:
                raise ValueError("simulation metadata fields require sampling_method")
        elif self.path_count is None:
            raise ValueError("simulation metadata requires path_count")
        elif self.sampling_method == RiskSamplingStrategy.MC:
            if self.random_seed is None or self.sobol_start_index is not None:
                raise ValueError("MC metadata requires random_seed and forbids sobol_start_index")
        elif self.sobol_start_index is None or self.random_seed is not None:
            raise ValueError("QMC metadata requires sobol_start_index and forbids random_seed")
        return self


class RiskScopeBase(BaseModel):
    """Base for the discriminated risk query scope."""

    model_config = ConfigDict(extra="forbid")

    kind: RiskScopeKind


class AssetRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.ASSET] = Field(json_schema_extra={"enum": ["asset"]})
    asset_id: PositiveInt


class AssetSetRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.ASSET_SET] = Field(json_schema_extra={"enum": ["asset_set"]})
    asset_ids: List[PositiveInt] = Field(..., min_length=1, max_length=100)

    @field_validator("asset_ids")
    @classmethod
    def validate_unique_asset_ids(cls, value: List[int]) -> List[int]:
        if len(value) != len(set(value)):
            raise ValueError("asset_ids must be unique")
        return value


class PortfolioRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.PORTFOLIO] = Field(json_schema_extra={"enum": ["portfolio"]})


class BrokerRiskScope(RiskScopeBase):
    kind: Literal[RiskScopeKind.BROKER] = Field(json_schema_extra={"enum": ["broker"]})
    broker_id: PositiveInt


RiskScope = Annotated[
    Union[
        AssetRiskScope,
        AssetSetRiskScope,
        PortfolioRiskScope,
        BrokerRiskScope,
    ],
    Field(discriminator="kind"),
]


class RiskAnalyticRequest(BaseModel):
    """One independently executable analytic in a bulk risk query."""

    model_config = ConfigDict(extra="forbid")

    instance_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    analytic_code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    parameters: Dict[str, JsonValue] = Field(default_factory=dict)


class RiskQueryRequest(BaseModel):
    """Bulk deterministic risk query sharing one scope and prepared data set."""

    model_config = ConfigDict(extra="forbid")

    scope: RiskScope
    date_range: DateRangeModel
    target_currency: str
    mode: RiskMode
    composition_policy: Optional[RiskCompositionPolicy] = None
    analytics: List[RiskAnalyticRequest] = Field(..., min_length=1, max_length=32)

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, value: str) -> str:
        return Currency.validate_code(value)

    @model_validator(mode="after")
    def validate_query(self) -> RiskQueryRequest:
        instance_ids = [analytic.instance_id for analytic in self.analytics]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("analytic instance_id values must be unique")
        if self.mode == RiskMode.CURRENT_COMPOSITION:
            if self.composition_policy != RiskCompositionPolicy.CURRENT_BUY_AND_HOLD:
                raise ValueError("current_composition mode requires composition_policy='current_buy_and_hold'")
        elif self.composition_policy is not None:
            raise ValueError("composition_policy is only valid for current_composition mode")
        return self


class RiskCatalogDefinition(BaseModel):
    """Static definition published by one RiskAnalytic plugin."""

    model_config = ConfigDict(extra="forbid")

    analytic_code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    name_i18n_key: str = Field(..., min_length=1)
    description_i18n_key: str = Field(..., min_length=1)
    output_kind: RiskOutputKind
    supported_scopes: List[RiskScopeKind] = Field(..., min_length=1)
    supported_modes: List[RiskMode] = Field(..., min_length=1)
    parameters_schema: Dict[str, JsonValue] = Field(default_factory=dict)
    min_observations: PositiveInt
    algorithm_version: str = Field(..., min_length=1)

    @field_validator("supported_scopes", "supported_modes")
    @classmethod
    def validate_unique_capabilities(cls, value: List[StrEnum]) -> List[StrEnum]:
        if len(value) != len(set(value)):
            raise ValueError("catalog capabilities must be unique")
        return value


class RiskCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[RiskCatalogDefinition] = Field(default_factory=list)


class RiskKpiOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.KPI] = Field(default=RiskOutputKind.KPI, json_schema_extra={"enum": ["kpi"]})
    volatility: FiniteFloat = Field(..., ge=0)
    max_drawdown: FiniteFloat = Field(..., le=0)
    max_drawdown_duration_days: int = Field(..., ge=0)
    sharpe: Optional[FiniteFloat] = None
    sortino: Optional[FiniteFloat] = None


class RiskMatrixCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_asset_id: PositiveInt
    column_asset_id: PositiveInt
    value: Optional[FiniteFloat] = Field(None, ge=-1, le=1)
    observations: int = Field(..., ge=0)
    coverage: FiniteFloat = Field(..., ge=0, le=1)
    status: RiskValueStatus


class RiskCorrelationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.MATRIX] = Field(default=RiskOutputKind.MATRIX, json_schema_extra={"enum": ["matrix"]})
    asset_ids: List[PositiveInt] = Field(..., min_length=1)
    cells: List[RiskMatrixCell] = Field(default_factory=list)


class RiskContributionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: PositiveInt
    weight: FiniteFloat
    marginal_contribution: FiniteFloat
    component_contribution: FiniteFloat
    percentage_contribution: Optional[FiniteFloat] = None


class RiskContributionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.CONTRIBUTION] = Field(default=RiskOutputKind.CONTRIBUTION, json_schema_extra={"enum": ["contribution"]})
    portfolio_volatility: FiniteFloat = Field(..., ge=0)
    cash_weight: FiniteFloat = Field(0, ge=0)
    items: List[RiskContributionItem] = Field(default_factory=list)


class RiskStressImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: PositiveInt
    weight: Optional[FiniteFloat] = None
    shock_return: FiniteFloat
    contribution_return: Optional[FiniteFloat] = None
    impact_amount: Optional[SafeDecimal] = None


class RiskStressOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.STRESS] = Field(default=RiskOutputKind.STRESS, json_schema_extra={"enum": ["stress"]})
    method: RiskStressMethod
    portfolio_return: Optional[FiniteFloat] = None
    impact_amount: Optional[SafeDecimal] = None
    replay_range: Optional[DateRangeModel] = None
    impacts: List[RiskStressImpact] = Field(default_factory=list)


class RiskComparisonPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    primary_cumulative_return: FiniteFloat
    comparison_cumulative_return: FiniteFloat
    primary_drawdown: FiniteFloat = Field(..., le=0)
    comparison_drawdown: FiniteFloat = Field(..., le=0)


class RiskComparisonOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.COMPARISON] = Field(default=RiskOutputKind.COMPARISON, json_schema_extra={"enum": ["comparison"]})
    comparison_asset_id: PositiveInt
    active_return: FiniteFloat
    tracking_error: FiniteFloat = Field(..., ge=0)
    information_ratio: Optional[FiniteFloat] = None
    correlation: Optional[FiniteFloat] = Field(None, ge=-1, le=1)
    beta: Optional[FiniteFloat] = None
    observations: int = Field(..., ge=0)
    series: List[RiskComparisonPoint] = Field(default_factory=list)


class RiskVarCvarOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.VAR_CVAR] = Field(default=RiskOutputKind.VAR_CVAR, json_schema_extra={"enum": ["var_cvar"]})
    confidence_level: FiniteFloat = Field(..., gt=0, lt=1)
    horizon_days: PositiveInt
    observations: PositiveInt
    value_at_risk: FiniteFloat = Field(..., ge=0)
    conditional_value_at_risk: FiniteFloat = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_tail_ordering(self) -> RiskVarCvarOutput:
        if self.conditional_value_at_risk < self.value_at_risk:
            raise ValueError("conditional_value_at_risk must be >= value_at_risk")
        return self


class RiskSimulationBandPoint(BaseModel):
    """One cumulative-return percentile band at a simulated day."""

    model_config = ConfigDict(extra="forbid")

    day: int = Field(..., ge=0)
    p05: FiniteFloat = Field(..., gt=-1)
    p50: FiniteFloat = Field(..., gt=-1)
    p95: FiniteFloat = Field(..., gt=-1)

    @model_validator(mode="after")
    def validate_percentile_order(self) -> RiskSimulationBandPoint:
        if not self.p05 <= self.p50 <= self.p95:
            raise ValueError("simulation percentiles must satisfy p05 <= p50 <= p95")
        return self


class RiskSimulationOutput(BaseModel):
    """Renderer-neutral conditional simulation result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[RiskOutputKind.SIMULATION] = Field(default=RiskOutputKind.SIMULATION, json_schema_extra={"enum": ["simulation"]})
    process: RiskSimulationProcess
    sampling_method: RiskSamplingStrategy
    horizon_days: PositiveInt
    path_count: PositiveInt
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

    @model_validator(mode="after")
    def validate_band_horizon(self) -> RiskSimulationOutput:
        expected_days = list(range(self.horizon_days + 1))
        if [point.day for point in self.percentile_bands] != expected_days:
            raise ValueError("simulation percentile bands must cover every day from zero through horizon_days")
        initial = self.percentile_bands[0]
        if not all(math.isclose(value, 0.0, rel_tol=0.0, abs_tol=1e-12) for value in (initial.p05, initial.p50, initial.p95)):
            raise ValueError("simulation percentile bands must start at zero cumulative return")
        return self


class RiskOptimizationWeight(BaseModel):
    """One optimized asset weight and its volatility contribution."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    weight: FiniteFloat = Field(..., ge=0, le=1)
    marginal_risk_contribution: FiniteFloat
    component_risk_contribution: FiniteFloat
    percentage_risk_contribution: FiniteFloat


class RiskOptimizationConstraintSummary(BaseModel):
    """Effective long-only budget constraints."""

    model_config = ConfigDict(extra="forbid")

    min_weight: FiniteFloat = Field(..., ge=0, le=1)
    max_weight: FiniteFloat = Field(..., ge=0, le=1)
    budget: Literal[1] = 1
    long_only: Literal[True] = True
    leverage_allowed: Literal[False] = False


class RiskOptimizationFrontierPoint(BaseModel):
    """One portfolio on the efficient frontier."""

    model_config = ConfigDict(extra="forbid")

    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    sharpe_ratio: Optional[FiniteFloat] = None
    weights: List[RiskOptimizationWeight] = Field(..., min_length=2)


class RiskOptimizationSensitivityPoint(BaseModel):
    """Recomputed solution under another covariance estimator."""

    model_config = ConfigDict(extra="forbid")

    covariance_estimator: RiskCovarianceEstimator
    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    max_absolute_weight_delta: FiniteFloat = Field(..., ge=0)
    weights: List[RiskOptimizationWeight] = Field(..., min_length=2)


class RiskPortfolioOptimizationOutput(BaseModel):
    """Renderer-neutral long-only portfolio optimization result."""

    model_config = ConfigDict(extra="forbid")

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


RiskAnalyticOutput = Annotated[
    Union[
        RiskKpiOutput,
        RiskCorrelationOutput,
        RiskContributionOutput,
        RiskStressOutput,
        RiskComparisonOutput,
        RiskVarCvarOutput,
        RiskSimulationOutput,
        RiskPortfolioOptimizationOutput,
    ],
    Field(discriminator="kind"),
]


class RiskWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)


class RiskError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: RiskErrorCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)


class RiskAnalyticResult(BaseModel):
    """One isolated result in a bulk risk response."""

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    analytic_code: str
    status: RiskResultStatus
    output: Optional[RiskAnalyticOutput] = None
    metadata: Optional[RiskResultMetadata] = None
    data_quality: Optional[DataQualityReport] = None
    warnings: List[RiskWarning] = Field(default_factory=list)
    error: Optional[RiskError] = None

    @model_validator(mode="after")
    def validate_status_payload(self) -> RiskAnalyticResult:
        if self.status in {RiskResultStatus.OK, RiskResultStatus.PARTIAL}:
            if self.output is None or self.metadata is None or self.data_quality is None:
                raise ValueError("successful results require output, metadata, and data_quality")
            if self.error is not None:
                raise ValueError("successful results must not include error")
        else:
            if self.output is not None:
                raise ValueError("unavailable or failed results must not include output")
            if self.error is None:
                raise ValueError("unavailable or failed results require error")
        return self


class RiskQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[RiskAnalyticResult] = Field(default_factory=list)


__all__ = [
    "AssetRiskScope",
    "AssetReturnPoint",
    "AssetReturnSeries",
    "AssetSetRiskScope",
    "AssetValuationPoint",
    "AssetValuationSeries",
    "BrokerRiskScope",
    "PortfolioRiskScope",
    "PreparedAssetSeries",
    "PreparedAssetSeriesSet",
    "RiskAnalyticOutput",
    "RiskAnalyticRequest",
    "RiskAnalyticResult",
    "RiskCatalogDefinition",
    "RiskCatalogResponse",
    "RiskComparisonOutput",
    "RiskComparisonPoint",
    "RiskCompositionPolicy",
    "RiskContributionItem",
    "RiskContributionOutput",
    "RiskCorrelationOutput",
    "RiskDataFrequency",
    "RiskError",
    "RiskErrorCode",
    "RiskExcludedAsset",
    "RiskFreeReference",
    "RiskKpiOutput",
    "RiskMatrixCell",
    "RiskMode",
    "RiskOutputKind",
    "RiskQueryRequest",
    "RiskQueryResponse",
    "RiskResultMetadata",
    "RiskResultStatus",
    "RiskReturnBasis",
    "RiskSimulationCovarianceEstimator",
    "RiskSimulationDriftEstimator",
    "RiskSamplingStrategy",
    "RiskScope",
    "RiskScopeBase",
    "RiskScopeKind",
    "RiskStressImpact",
    "RiskStressMethod",
    "RiskStressOutput",
    "RiskSimulationBandPoint",
    "RiskSimulationOutput",
    "RiskSimulationProcess",
    "RiskValueStatus",
    "RiskVarCvarOutput",
    "RiskWarning",
]
