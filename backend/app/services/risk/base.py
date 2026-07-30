"""Pure execution contract for multi-asset risk analytics."""

from __future__ import annotations

import asyncio
import inspect
import re
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar, Optional

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.risk import (
    PreparedAssetSeriesSet,
    RiskAnalyticOutput,
    RiskCatalogDefinition,
    RiskCompositionPolicy,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskFreeReference,
    RiskHistoricalReplayAudit,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskSamplingStrategy,
    RiskScopeKind,
    RiskWarning,
)

_ANALYTIC_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class RiskUnavailableError(ValueError):
    """Report an unavailable analytic without treating it as an internal failure."""

    def __init__(
        self,
        message: str,
        *,
        code: RiskErrorCode,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class RiskHistoricalReplayContext:
    """Prepared replay-only series and original-to-source identity."""

    prepared_series: PreparedAssetSeriesSet
    source_asset_ids: Mapping[int, int]
    excluded_asset_ids: tuple[int, ...]
    data_quality: DataQualityReport


@dataclass(frozen=True, slots=True)
class RiskAssetClassification:
    """Canonical classification inputs consumed by hypothetical stress."""

    asset_class: str
    sector_exposures: Optional[Mapping[str, float]] = None
    geography_exposures: Optional[Mapping[str, float]] = None
    metadata_error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class RiskExecutionContext:
    """Prepared, DB-free inputs shared by every analytic in one bulk query."""

    scope_kind: RiskScopeKind
    scope_reference: str
    requested_range: DateRangeModel
    target_currency: str
    mode: RiskMode
    composition_policy: Optional[RiskCompositionPolicy]
    scope_asset_ids: tuple[int, ...]
    prepared_series: Optional[PreparedAssetSeriesSet]
    primary_baseline_date: Optional[date]
    primary_return_dates: tuple[date, ...]
    primary_returns: tuple[float, ...]
    primary_return_basis: RiskReturnBasis
    annualization_factor: Optional[float]
    calendar_days: int
    coverage: float
    data_quality: DataQualityReport
    requested_scope_asset_ids: tuple[int, ...] = ()
    excluded_assets: tuple[RiskExcludedAsset, ...] = ()
    execution_warnings: tuple[RiskWarning, ...] = ()
    portfolio_data_quality: Optional[DataQualityReport] = None
    prepared_data_quality: Optional[DataQualityReport] = None
    weights: Mapping[int, float] = field(default_factory=dict)
    asset_values: Mapping[int, Decimal] = field(default_factory=dict)
    cash_weight: float = 0.0
    scope_value: Optional[Decimal] = None
    broker_ids: tuple[int, ...] = ()
    composition_as_of: Optional[date] = None
    historical_replay: Optional[RiskHistoricalReplayContext] = None
    asset_classifications: Mapping[int, RiskAssetClassification] = field(default_factory=dict)
    geography_groups: Mapping[str, frozenset[str]] = field(default_factory=dict)

    @property
    def n_observations(self) -> int:
        return len(self.primary_returns)


@dataclass(frozen=True, slots=True)
class RiskComputation:
    """Pure analytic output plus metadata additions owned by the plugin."""

    output: RiskAnalyticOutput
    method: str
    warnings: tuple[RiskWarning, ...] = ()
    excluded_assets: tuple[RiskExcludedAsset, ...] = ()
    comparison_asset_id: Optional[int] = None
    risk_free: Optional[RiskFreeReference] = None
    analyzed_range: Optional[DateRangeModel] = None
    n_observations: Optional[int] = None
    calendar_days: Optional[int] = None
    annualization_factor: Optional[float] = None
    coverage: Optional[float] = None
    return_basis: Optional[RiskReturnBasis] = None
    sampling_method: Optional[RiskSamplingStrategy] = None
    path_count: Optional[int] = None
    random_seed: Optional[int] = None
    sobol_start_index: Optional[int] = None
    historical_replay_audit: Optional[RiskHistoricalReplayAudit] = None


class RiskAnalytic(ABC):
    """Complete implementation boundary for one risk analytic."""

    analytic_code: ClassVar[str]
    algorithm_version: ClassVar[str]
    name_i18n_key: ClassVar[str]
    description_i18n_key: ClassVar[str]
    output_kind: ClassVar[RiskOutputKind]
    supported_scopes: ClassVar[tuple[RiskScopeKind, ...]]
    supported_modes: ClassVar[tuple[RiskMode, ...]]
    params_model: ClassVar[type[BaseModel]]
    min_observations: ClassVar[int]

    @classmethod
    def validate_params(cls, params: Mapping[str, object] | BaseModel) -> BaseModel:
        """Validate and normalize request parameters with the plugin-owned model."""
        if isinstance(params, cls.params_model):
            return params
        if isinstance(params, BaseModel):
            params = params.model_dump()
        return cls.params_model.model_validate(params)

    @classmethod
    def catalog_definition(cls) -> RiskCatalogDefinition:
        """Build the static schema-driven catalog entry."""
        return RiskCatalogDefinition(
            analytic_code=cls.analytic_code,
            name_i18n_key=cls.name_i18n_key,
            description_i18n_key=cls.description_i18n_key,
            output_kind=cls.output_kind,
            supported_scopes=list(cls.supported_scopes),
            supported_modes=list(cls.supported_modes),
            parameters_schema=to_jsonable_python(cls.params_model.model_json_schema()),
            min_observations=cls.min_observations,
            algorithm_version=cls.algorithm_version,
        )

    @classmethod
    def validate_definition(cls) -> None:
        """Reject incomplete or unsafe declarations at registration."""
        if cls is RiskAnalytic or inspect.isabstract(cls):
            raise TypeError("RiskAnalyticRegistry accepts concrete RiskAnalytic subclasses only")
        required_attributes = (
            "analytic_code",
            "algorithm_version",
            "name_i18n_key",
            "description_i18n_key",
            "output_kind",
            "supported_scopes",
            "supported_modes",
            "params_model",
            "min_observations",
        )
        missing = [attribute for attribute in required_attributes if not hasattr(cls, attribute)]
        if missing:
            raise ValueError(f"risk analytic is missing required attributes: {', '.join(missing)}")
        if not isinstance(cls.analytic_code, str) or cls.analytic_code != cls.analytic_code.strip().lower() or not _ANALYTIC_CODE_PATTERN.fullmatch(cls.analytic_code):
            raise ValueError("analytic_code must be canonical lowercase letters, numbers, and underscores")
        if not isinstance(cls.algorithm_version, str) or not cls.algorithm_version.strip():
            raise ValueError("algorithm_version must be a non-empty string")
        if not isinstance(cls.name_i18n_key, str) or not cls.name_i18n_key.strip():
            raise ValueError("name_i18n_key must be a non-empty string")
        if not isinstance(cls.description_i18n_key, str) or not cls.description_i18n_key.strip():
            raise ValueError("description_i18n_key must be a non-empty string")
        if not isinstance(cls.output_kind, RiskOutputKind):
            raise TypeError("output_kind must be a RiskOutputKind")
        if not cls.supported_scopes or len(cls.supported_scopes) != len(set(cls.supported_scopes)):
            raise ValueError("supported_scopes must be non-empty and unique")
        if not all(isinstance(scope, RiskScopeKind) for scope in cls.supported_scopes):
            raise TypeError("supported_scopes must contain RiskScopeKind values")
        if not cls.supported_modes or len(cls.supported_modes) != len(set(cls.supported_modes)):
            raise ValueError("supported_modes must be non-empty and unique")
        if not all(isinstance(mode, RiskMode) for mode in cls.supported_modes):
            raise TypeError("supported_modes must contain RiskMode values")
        if not issubclass(cls.params_model, BaseModel):
            raise TypeError("params_model must be a Pydantic BaseModel subclass")
        if cls.params_model.model_config.get("extra") != "forbid":
            raise ValueError("risk params_model must use ConfigDict(extra='forbid')")
        if not isinstance(cls.min_observations, int) or isinstance(cls.min_observations, bool) or cls.min_observations <= 0:
            raise ValueError("min_observations must be a positive integer")
        if cls.compute is RiskAnalytic.compute and cls.execute is RiskAnalytic.execute:
            raise TypeError(
                "risk analytics must implement compute() or execute()",
            )
        try:
            inspect.signature(cls).bind()
        except TypeError as exc:
            raise TypeError("risk analytics must be instantiable without arguments") from exc
        cls.catalog_definition()

    def compute(
        self,
        params: BaseModel,
        context: RiskExecutionContext,
    ) -> RiskComputation:
        """Compute a result from already prepared, I/O-free inputs."""
        raise NotImplementedError

    async def execute(
        self,
        params: BaseModel,
        context: RiskExecutionContext,
    ) -> RiskComputation:
        """Execute lightweight analytics without blocking the event loop."""
        return await asyncio.to_thread(
            self.compute,
            params,
            context,
        )


__all__ = [
    "RiskAnalytic",
    "RiskAssetClassification",
    "RiskComputation",
    "RiskExecutionContext",
    "RiskHistoricalReplayContext",
    "RiskUnavailableError",
]
