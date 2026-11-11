"""Risk results: the assets left out, the historical replay audit, the result metadata, warnings, errors and the result of one analytic."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import Field, FiniteFloat, JsonValue, PositiveInt, field_validator, model_validator

from backend.app.schemas.common import Currency, DateRangeModel, StrictModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.risk.outputs import RiskAnalyticOutput
from backend.app.schemas.risk.scenarios import (
    RiskScenarioMissingHistoryPolicy,
)
from backend.app.schemas.risk.series import RiskFreeReference
from backend.app.schemas.risk.vocabulary import RiskCompositionPolicy, RiskDataFrequency, RiskErrorCode, RiskHistoricalReplayExclusionReason, RiskHistoricalReplayExclusionTreatment, RiskMode, RiskResultStatus, RiskReturnBasis, RiskSamplingStrategy, RiskScopeKind
from backend.app.services.financial_math.returns import observations_per_year  # MF-D3: a pure house function, no service


class RiskExcludedAsset(StrictModel):
    """Metric-specific asset exclusion recorded in result metadata."""

    asset_id: int
    reason: str = Field(..., min_length=1)


class RiskHistoricalReplayProxyAsset(StrictModel):
    """Manual original-to-proxy return-series mapping."""

    asset_id: PositiveInt
    proxy_asset_id: PositiveInt

    @model_validator(mode="after")
    def validate_distinct_assets(self) -> RiskHistoricalReplayProxyAsset:
        if self.asset_id == self.proxy_asset_id:
            raise ValueError("historical replay proxy must differ from the original asset")
        return self


class RiskHistoricalReplayExcludedAsset(StrictModel):
    """Auditable outcome of one replay exclusion, manual or automatic."""

    asset_id: PositiveInt
    reason: RiskHistoricalReplayExclusionReason = RiskHistoricalReplayExclusionReason.MANUAL_EXCLUSION
    weight: Optional[FiniteFloat] = Field(None, ge=0, le=1)
    treatment: RiskHistoricalReplayExclusionTreatment


class RiskHistoricalReplayAudit(StrictModel):
    """Serializable execution choices for one historical replay."""

    proxy_count: int = Field(..., ge=0)
    proxy_assets: List[RiskHistoricalReplayProxyAsset] = Field(default_factory=list)
    excluded_count: int = Field(..., ge=0)
    excluded_assets: List[RiskHistoricalReplayExcludedAsset] = Field(default_factory=list)
    excluded_weight_total: FiniteFloat = Field(0, ge=0, le=1)
    missing_history_policy: RiskScenarioMissingHistoryPolicy
    composition_policy: RiskCompositionPolicy
    proxy_series_usage: Literal["returns_only"] = "returns_only"
    suggested_range: Optional[DateRangeModel] = Field(
        None,
        description="Part of the replay window in which every asset excluded by the window's edges is priced; offered only when replaying it brings them back without losing any other asset",
    )
    suggested_range_recovers: List[PositiveInt] = Field(default_factory=list, description="Assets the suggested range brings back, ordered by asset")

    @model_validator(mode="after")
    def validate_audit(self) -> RiskHistoricalReplayAudit:
        if self.proxy_count != len(self.proxy_assets):
            raise ValueError("proxy_count must match proxy_assets")
        if self.excluded_count != len(self.excluded_assets):
            raise ValueError("excluded_count must match excluded_assets")
        proxy_asset_ids = [item.asset_id for item in self.proxy_assets]
        if proxy_asset_ids != sorted(proxy_asset_ids) or len(proxy_asset_ids) != len(set(proxy_asset_ids)):
            raise ValueError("proxy_assets must be unique and ordered by original asset")
        excluded_asset_ids = [item.asset_id for item in self.excluded_assets]
        if excluded_asset_ids != sorted(excluded_asset_ids) or len(excluded_asset_ids) != len(set(excluded_asset_ids)):
            raise ValueError("excluded_assets must be unique and ordered by asset")
        if set(proxy_asset_ids) & set(excluded_asset_ids):
            raise ValueError("an asset cannot be both proxied and excluded")
        if self.composition_policy != RiskCompositionPolicy.CURRENT_BUY_AND_HOLD:
            raise ValueError("historical replay requires current_buy_and_hold composition")
        expected_excluded_weight = math.fsum(item.weight or 0.0 for item in self.excluded_assets)
        if not math.isclose(
            self.excluded_weight_total,
            expected_excluded_weight,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("excluded_weight_total must match excluded asset weights")
        return self

    @model_validator(mode="after")
    def validate_suggested_range(self) -> RiskHistoricalReplayAudit:
        recovered = self.suggested_range_recovers
        if recovered != sorted(set(recovered)):
            raise ValueError("suggested_range_recovers must be unique and ordered by asset")
        if (self.suggested_range is None) != (not recovered):
            raise ValueError("suggested_range and suggested_range_recovers must be set together")
        automatic = {item.asset_id for item in self.excluded_assets if item.reason != RiskHistoricalReplayExclusionReason.MANUAL_EXCLUSION}
        if not set(recovered) <= automatic:
            raise ValueError("a suggested range can only recover automatically excluded assets")
        return self


class RiskResultMetadata(StrictModel):
    """Execution context shared by all serialized risk results."""

    analyzed_range: DateRangeModel
    frequency: RiskDataFrequency = RiskDataFrequency.DAILY
    n_observations: int = Field(..., ge=0)
    calendar_days: int = Field(..., ge=0)
    annualization_factor: Optional[FiniteFloat] = Field(None, gt=0)
    coverage: FiniteFloat = Field(..., ge=0, le=1)
    currency: str
    scope: Optional[RiskScopeKind] = None
    scope_reference: Optional[str] = None
    broker_ids: Optional[List[PositiveInt]] = None
    sliced_asset_ids: Optional[List[PositiveInt]] = Field(
        None,
        description="Effective asset slice of a portfolio scope. When set, weights are renormalized to 100% of the slice and no zero-return cash residual remains.",
    )
    composition_as_of: Optional[date] = None
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
    bootstrap_seed: Optional[int] = Field(None, ge=0, le=2**32 - 1)
    historical_replay_audit: Optional[RiskHistoricalReplayAudit] = None

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

    @field_validator("broker_ids")
    @classmethod
    def normalize_broker_ids(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is None:
            return None
        if len(value) != len(set(value)):
            raise ValueError("broker_ids must be unique")
        return sorted(value)

    @field_validator("sliced_asset_ids")
    @classmethod
    def normalize_sliced_asset_ids(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is None:
            return None
        if not value:
            raise ValueError("sliced_asset_ids cannot be empty")
        if len(value) != len(set(value)):
            raise ValueError("sliced_asset_ids must be unique")
        return sorted(value)

    @model_validator(mode="after")
    def validate_context(self) -> RiskResultMetadata:  # noqa: C901 — flat invariant raises, no nested logic
        if self.n_observations == 0:
            if self.calendar_days != 0 or self.annualization_factor is not None:
                raise ValueError("empty results cannot expose annualization metadata")
        else:
            if self.calendar_days <= 0:
                raise ValueError("non-empty results require positive calendar_days")
            expected_factor = observations_per_year(self.n_observations, self.calendar_days)
            if self.annualization_factor is None or not math.isclose(self.annualization_factor, expected_factor, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError("annualization_factor must equal n_observations * 365 / calendar_days")
        if self.mode == RiskMode.HISTORICAL and self.composition_policy is not None:
            raise ValueError("historical mode cannot declare a composition policy")
        if self.mode == RiskMode.CURRENT_COMPOSITION and self.composition_policy is None:
            raise ValueError("current_composition requires a composition policy")
        if self.broker_ids is not None and self.scope != RiskScopeKind.PORTFOLIO:
            raise ValueError("broker_ids metadata requires portfolio scope")
        if self.sliced_asset_ids is not None and self.scope != RiskScopeKind.PORTFOLIO:
            raise ValueError("sliced_asset_ids metadata requires portfolio scope")
        if self.composition_as_of is not None and self.scope != RiskScopeKind.PORTFOLIO:
            raise ValueError("composition_as_of metadata requires portfolio scope")
        if self.sampling_method is None:
            if self.path_count is not None or self.random_seed is not None or self.sobol_start_index is not None or self.bootstrap_seed is not None:
                raise ValueError("simulation metadata fields require sampling_method")
        elif self.path_count is None:
            raise ValueError("simulation metadata requires path_count")
        elif self.sampling_method == RiskSamplingStrategy.MC:
            # Pseudo-random sampling covers two engines, not one. The parametric
            # engine draws its normals from `random_seed`; the block bootstrap
            # resamples real history under `bootstrap_seed` and is forbidden a
            # `random_seed` by `SimulationParams` itself. Metadata carries no
            # `process` field, but it does not need one: the params validator
            # makes the seeds mutually exclusive, so *which* seed is present is
            # the process, encoded. Asking for `random_seed` unconditionally made
            # this model unable to describe the default engine at all.
            if self.sobol_start_index is not None:
                raise ValueError("MC metadata forbids sobol_start_index")
            if self.bootstrap_seed is not None:
                if self.random_seed is not None:
                    raise ValueError("block bootstrap metadata forbids random_seed")
            elif self.random_seed is None:
                raise ValueError("parametric MC metadata requires random_seed")
        elif self.sobol_start_index is None or self.random_seed is not None:
            raise ValueError("QMC metadata requires sobol_start_index and forbids random_seed")
        return self


class RiskWarning(StrictModel):
    code: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)
    degrades_result: bool = True
    # The translatable form of `message`, rendered by the frontend with `message_params`, the same
    # contract as `DataQualityIssue`. `message` stays the English fallback for a warning without a
    # key, so a code added later is shown verbatim instead of as a raw key.
    message_i18n_key: Optional[str] = Field(None, min_length=1, max_length=160, pattern=r"^risk\.warnings\.[A-Za-z0-9_.]+$")
    message_params: Dict[str, JsonValue] = Field(default_factory=dict)


class RiskError(StrictModel):
    code: RiskErrorCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)


class RiskAnalyticResult(StrictModel):
    """One isolated result in a bulk risk response."""

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


class RiskQueryResponse(StrictModel):
    items: List[RiskAnalyticResult] = Field(default_factory=list)
