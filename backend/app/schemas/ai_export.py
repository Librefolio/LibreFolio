"""Typed contracts for curated AI Export requests, catalog entries, and snapshots."""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self, Union

from pydantic import (
    AfterValidator,
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PositiveInt,
    field_validator,
    model_validator,
)

from backend.app.schemas.common import Currency, DateRangeModel, SafeDecimal

_CODE_PATTERN = r"^[a-z][a-z0-9_.-]*$"
_PROFILE_PATTERN = r"^[a-z][a-z0-9_.-]*$"
_SIGNAL_CODE_PATTERN = r"^[A-Z][A-Z0-9_]*$"
_INSTANCE_ID_PATTERN = r"^[a-z][a-z0-9_.-]*$"


def _normalize_broker_ids(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise ValueError("broker_ids must contain unique values")
    return sorted(values)


def _normalize_signal_code(value: Any) -> Any:
    return value.strip().upper() if isinstance(value, str) else value


def _normalize_instance_id(value: Any) -> Any:
    return value.strip().lower() if isinstance(value, str) else value


def _ensure_json_safe(value: Any, path: str = "value") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_json_safe(item, f"{path}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            _ensure_json_safe(item, f"{path}.{key}")
        return value
    raise ValueError(f"{path} contains a non-JSON value of type {type(value).__name__}")


CurrencyCode = Annotated[str, BeforeValidator(Currency.validate_code)]
BrokerIds = Annotated[list[PositiveInt], AfterValidator(_normalize_broker_ids)]
NonEmptyBrokerIds = Annotated[BrokerIds, Field(min_length=1)]
Percentage = Annotated[SafeDecimal, Field(ge=Decimal("0"), le=Decimal("100"))]
Ratio = Annotated[SafeDecimal, Field(ge=Decimal("0"), le=Decimal("1"))]
NonNegativeDecimal = Annotated[SafeDecimal, Field(ge=Decimal("0"))]
SignedNavWeightPercentage = SafeDecimal
GrossNavWeightPercentage = NonNegativeDecimal
SignalCode = Annotated[
    str,
    BeforeValidator(_normalize_signal_code),
    Field(min_length=1, max_length=64, pattern=_SIGNAL_CODE_PATTERN),
]
SignalInstanceId = Annotated[
    str,
    BeforeValidator(_normalize_instance_id),
    Field(min_length=1, max_length=128, pattern=_INSTANCE_ID_PATTERN),
]
ProfileId = Annotated[str, Field(min_length=1, max_length=160, pattern=_PROFILE_PATTERN)]
ContractId = Annotated[str, Field(min_length=1, max_length=160, pattern=_PROFILE_PATTERN)]
CodeKey = Annotated[str, Field(min_length=1, max_length=128, pattern=_CODE_PATTERN)]


class AiExportModel(BaseModel):
    """Base for every AI Export contract."""

    model_config = ConfigDict(extra="forbid")


class AiExportDomain(StrEnum):
    PORTFOLIO = "portfolio"
    ASSET = "asset"
    FX = "fx"
    BROKER = "broker"


class AiExportDetailLevel(StrEnum):
    COMPACT = "compact"
    STANDARD = "standard"
    FULL = "full"


class AiExportTask(StrEnum):
    PAC_PLANNING = "pac_planning"
    REBALANCING = "rebalancing"
    PERFORMANCE_ATTRIBUTION = "performance_attribution"
    INCOME_REVIEW = "income_review"
    PORTFOLIO_FIFO_LOT_REVIEW = "portfolio_fifo_lot_review"
    TECHNICAL_BREADTH = "technical_breadth"
    PORTFOLIO_DESCRIPTION = "portfolio_description"
    ASSET_SNAPSHOT = "asset_snapshot"
    ASSET_TREND_ANALYSIS = "asset_trend_analysis"
    POSITION_REVIEW = "position_review"
    ASSET_PAC_TIMING_CONTEXT = "asset_pac_timing_context"
    DRAWDOWN_RECOVERY = "drawdown_recovery"
    FX_TREND_REVIEW = "fx_trend_review"
    FX_EXPOSURE_IMPACT = "fx_exposure_impact"
    FX_CONVERSION_TIMING_CONTEXT = "fx_conversion_timing_context"
    BROKER_REVIEW = "broker_review"
    BROKER_COST_EFFICIENCY = "broker_cost_efficiency"
    BROKER_CONCENTRATION_CONTEXT = "broker_concentration_context"
    BROKER_FIFO_LOT_REVIEW = "broker_fifo_lot_review"


class AiExportPortfolioTask(StrEnum):
    PAC_PLANNING = "pac_planning"
    REBALANCING = "rebalancing"
    PERFORMANCE_ATTRIBUTION = "performance_attribution"
    INCOME_REVIEW = "income_review"
    PORTFOLIO_FIFO_LOT_REVIEW = "portfolio_fifo_lot_review"
    TECHNICAL_BREADTH = "technical_breadth"
    PORTFOLIO_DESCRIPTION = "portfolio_description"


class AiExportAssetTask(StrEnum):
    ASSET_SNAPSHOT = "asset_snapshot"
    ASSET_TREND_ANALYSIS = "asset_trend_analysis"
    POSITION_REVIEW = "position_review"
    ASSET_PAC_TIMING_CONTEXT = "asset_pac_timing_context"
    DRAWDOWN_RECOVERY = "drawdown_recovery"


class AiExportFxTask(StrEnum):
    FX_TREND_REVIEW = "fx_trend_review"
    FX_EXPOSURE_IMPACT = "fx_exposure_impact"
    FX_CONVERSION_TIMING_CONTEXT = "fx_conversion_timing_context"


class AiExportBrokerTask(StrEnum):
    BROKER_REVIEW = "broker_review"
    BROKER_COST_EFFICIENCY = "broker_cost_efficiency"
    BROKER_CONCENTRATION_CONTEXT = "broker_concentration_context"
    BROKER_FIFO_LOT_REVIEW = "broker_fifo_lot_review"


class AiExportNoteSource(StrEnum):
    USER = "user"
    PROVIDER = "provider"
    PROVIDER_OR_USER = "provider_or_user"
    MANUAL = "manual"


class AiExportProblemCode(StrEnum):
    UNSUPPORTED_PROFILE = "unsupported_profile"
    PROFILE_CONTRACT_MISMATCH = "profile_contract_mismatch"
    TASK_NOT_APPLICABLE = "task_not_applicable"
    BROKER_ACCESS_DENIED = "broker_access_denied"
    ENTITY_NOT_FOUND = "entity_not_found"
    SNAPSHOT_SOURCE_FAILURE = "snapshot_source_failure"


class AiExportSignalStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"


class AiExportNormalizedReturnBaseSource(StrEnum):
    OBSERVED_MARKET_PRICE = "observed_market_price"
    FIRST_OBSERVED_MARKET_PRICE_IN_WINDOW = "first_observed_market_price_in_window"


class AiExportValuationReferenceSource(StrEnum):
    LAST_VISIBLE_BUY_UNIT_PRICE = "last_visible_buy_unit_price"
    LAST_SEED_COST = "last_seed_cost"


class AiExportValuationSource(StrEnum):
    MARKET_PRICE = "market_price"
    LAST_VISIBLE_BUY_UNIT_PRICE = "last_visible_buy_unit_price"
    LAST_SEED_COST = "last_seed_cost"
    MIXED = "mixed"
    MISSING = "missing"


class AiExportTokenEstimationMethod(StrEnum):
    CHARS_DIV_4_V1 = "chars_div_4_v1"


class AiExportNoteSubject(StrEnum):
    PORTFOLIO = "portfolio"
    ASSET = "asset"
    FX = "fx"
    BROKER = "broker"
    EVENT = "event"
    TRANSACTION = "transaction"


class AiExportEventDirection(StrEnum):
    UP = "up"
    DOWN = "down"


class AiExportFxExposureKind(StrEnum):
    CASH = "cash"
    POSITION = "position"


class AiExportFxExposureLinkage(StrEnum):
    CASH_CURRENCY = "cash_currency"
    TRADING_CURRENCY = "trading_currency"
    VALUATION_CURRENCY = "valuation_currency"


_TASK_DOMAIN_BY_VALUE: dict[str, AiExportDomain] = {
    **{task.value: AiExportDomain.PORTFOLIO for task in AiExportPortfolioTask},
    **{task.value: AiExportDomain.ASSET for task in AiExportAssetTask},
    **{task.value: AiExportDomain.FX for task in AiExportFxTask},
    **{task.value: AiExportDomain.BROKER for task in AiExportBrokerTask},
}


class AiExportSnapshotRequestBase(AiExportModel):
    domain: AiExportDomain
    task: AiExportTask
    detail_level: AiExportDetailLevel
    date_range: DateRangeModel
    technical_window: DateRangeModel | None = Field(
        None,
        description="Optional inclusive technical-analysis window. Its end must equal snapshot_as_of; omitted defaults to 3 calendar months.",
    )
    target_currency: CurrencyCode

    @model_validator(mode="after")
    def validate_technical_window(self) -> Self:
        if self.technical_window is None:
            return self
        snapshot_as_of = self.date_range.end or self.date_range.start
        technical_end = self.technical_window.end or self.technical_window.start
        if technical_end != snapshot_as_of:
            raise ValueError("technical_window.end must equal snapshot_as_of")
        return self


class AiExportPortfolioSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal[AiExportDomain.PORTFOLIO] = Field(json_schema_extra={"enum": ["portfolio"]})
    task: AiExportPortfolioTask
    broker_ids: NonEmptyBrokerIds | None = None


class AiExportAssetSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal[AiExportDomain.ASSET] = Field(json_schema_extra={"enum": ["asset"]})
    task: AiExportAssetTask
    asset_id: PositiveInt
    broker_ids: NonEmptyBrokerIds | None = None


class AiExportFxSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal[AiExportDomain.FX] = Field(json_schema_extra={"enum": ["fx"]})
    task: AiExportFxTask
    base_currency: CurrencyCode
    quote_currency: CurrencyCode
    broker_ids: NonEmptyBrokerIds | None = None

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        return self


class AiExportBrokerSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal[AiExportDomain.BROKER] = Field(json_schema_extra={"enum": ["broker"]})
    task: AiExportBrokerTask
    broker_id: PositiveInt


AiExportSnapshotRequest = Annotated[
    Union[
        AiExportPortfolioSnapshotRequest,
        AiExportAssetSnapshotRequest,
        AiExportFxSnapshotRequest,
        AiExportBrokerSnapshotRequest,
    ],
    Field(discriminator="domain"),
]


class AiExportCatalogEntry(AiExportModel):
    domain: AiExportDomain
    task: AiExportTask
    detail_level: AiExportDetailLevel
    profile_id: str = Field(..., min_length=1, max_length=160, pattern=_PROFILE_PATTERN)
    profile_version: PositiveInt
    frontend_response_contract_id: str = Field(..., min_length=1, max_length=160, pattern=_PROFILE_PATTERN)
    frontend_response_contract_version: PositiveInt
    applicability_code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    supports_user_notes: bool
    supports_web_research: bool

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if _TASK_DOMAIN_BY_VALUE[self.task.value] != self.domain:
            raise ValueError("task does not belong to domain")
        expected_profile_id = f"{self.domain.value}.{self.task.value}.{self.detail_level.value}"
        if self.profile_id != expected_profile_id:
            raise ValueError(f"profile_id must be {expected_profile_id}")
        expected_contract_id = f"{self.domain.value}.{self.task.value}"
        if self.frontend_response_contract_id != expected_contract_id:
            raise ValueError(f"frontend_response_contract_id must be {expected_contract_id}")
        return self


class AiExportCatalogResponse(AiExportModel):
    schema_version: PositiveInt
    entries: list[AiExportCatalogEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entries(self) -> Self:
        identities = [(entry.domain, entry.task, entry.detail_level) for entry in self.entries]
        if len(identities) != len(set(identities)):
            raise ValueError("catalog entries must be unique by domain, task, and detail_level")
        profile_ids = [entry.profile_id for entry in self.entries]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("catalog profile_id values must be unique")
        return self


class AiExportSnapshotMeta(AiExportModel):
    schema_version: PositiveInt
    profile_id: str = Field(..., min_length=1, max_length=160, pattern=_PROFILE_PATTERN)
    profile_version: PositiveInt
    frontend_response_contract_id: str = Field(..., min_length=1, max_length=160, pattern=_PROFILE_PATTERN)
    frontend_response_contract_version: PositiveInt
    generated_at: datetime
    snapshot_as_of: date
    selected_range: DateRangeModel
    technical_window: DateRangeModel | None = None
    calculation_range: DateRangeModel | None = None
    calculation_warmup_start: date | None = None
    target_currency: CurrencyCode

    @model_validator(mode="after")
    def validate_warmup(self) -> Self:
        if self.calculation_warmup_start is not None and self.technical_window is not None and self.calculation_warmup_start > self.technical_window.start:
            raise ValueError("calculation_warmup_start must not be after technical_window.start")
        return self


class AiExportMethodology(AiExportModel):
    date_range_semantics: Literal["inclusive"] = "inclusive"
    price_observation_policy: Literal["observed_only"] = "observed_only"
    normalized_return_policy: Literal["observed_market_prices_only"] = "observed_market_prices_only"
    technical_calculation_policy: Literal["warmup_then_slice"] = "warmup_then_slice"
    position_cost_basis_method: Literal["weighted_average_cost"] | None = None
    position_cost_basis_is_not_market_price: Literal[True] | None = None
    lot_matching_method: Literal["runtime_fifo"] | None = None
    cash_decomposition_source: Literal["portfolio_engine"] | None = None


class AiExportPortfolioTargetReference(AiExportModel):
    kind: Literal["portfolio"] = Field(json_schema_extra={"enum": ["portfolio"]})


class AiExportBrokerTargetReference(AiExportModel):
    kind: Literal["broker"] = Field(json_schema_extra={"enum": ["broker"]})
    broker_id: PositiveInt


class AiExportAssetTargetReference(AiExportModel):
    kind: Literal["asset"] = Field(json_schema_extra={"enum": ["asset"]})
    asset_id: PositiveInt


class AiExportFxPairTargetReference(AiExportModel):
    kind: Literal["fx_pair"] = Field(json_schema_extra={"enum": ["fx_pair"]})
    base_currency: CurrencyCode
    quote_currency: CurrencyCode

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        return self


AiExportTargetReference = Annotated[
    Union[
        AiExportPortfolioTargetReference,
        AiExportBrokerTargetReference,
        AiExportAssetTargetReference,
        AiExportFxPairTargetReference,
    ],
    Field(discriminator="kind"),
]

AiExportTechnicalTargetReference = Annotated[
    Union[AiExportAssetTargetReference, AiExportFxPairTargetReference],
    Field(discriminator="kind"),
]


class AiExportSampledPoint(AiExportModel):
    date: date
    value: SafeDecimal


class AiExportTechnicalComponent(AiExportModel):
    component_code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    semantic_id: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    unit: str = Field(..., min_length=1, max_length=64, pattern=_CODE_PATTERN)
    latest: AiExportSampledPoint | None = None
    sampled_points: list[AiExportSampledPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_points(self) -> Self:
        if self.latest is None and not self.sampled_points:
            raise ValueError("technical component requires latest or sampled_points")
        dates = [point.date for point in self.sampled_points]
        if any(current >= following for current, following in zip(dates, dates[1:], strict=False)):
            raise ValueError("sampled_points dates must be strictly increasing and unique")
        return self


class AiExportTechnicalSignal(AiExportModel):
    instance_id: SignalInstanceId
    signal_code: SignalCode
    implementation_version: str = Field(..., min_length=1, max_length=64)
    normalized_params: dict[str, JsonValue]
    status: AiExportSignalStatus
    components: list[AiExportTechnicalComponent] = Field(..., min_length=1)

    @field_validator("normalized_params", mode="before")
    @classmethod
    def validate_normalized_params(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "normalized_params")

    @model_validator(mode="after")
    def validate_components(self) -> Self:
        codes = [component.component_code for component in self.components]
        if len(codes) != len(set(codes)):
            raise ValueError("technical component codes must be unique within a signal")
        return self


class AiExportTechnicalTarget(AiExportModel):
    target: AiExportTechnicalTargetReference
    signals: list[AiExportTechnicalSignal] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_signals(self) -> Self:
        instance_ids = [signal.instance_id for signal in self.signals]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("technical signal instance_id values must be unique within a target")
        return self


class AiExportTechnicalSnapshot(AiExportModel):
    targets: list[AiExportTechnicalTarget] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_targets(self) -> Self:
        identities = [target.target.model_dump_json() for target in self.targets]
        if len(identities) != len(set(identities)):
            raise ValueError("technical targets must be unique")
        return self


class AiExportDerivedState(AiExportModel):
    target: AiExportTargetReference
    code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    state: str = Field(..., min_length=1, max_length=64, pattern=_CODE_PATTERN)
    as_of: date
    signal_instance_id: SignalInstanceId | None = None
    signal_code: SignalCode | None = None
    component_code: str | None = Field(None, min_length=1, max_length=128, pattern=_CODE_PATTERN)
    value: SafeDecimal | None = None


class AiExportEvent(AiExportModel):
    target: AiExportTargetReference
    date: date
    code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    signal_instance_id: SignalInstanceId | None = None
    signal_code: SignalCode | None = None
    component_code: str | None = Field(None, min_length=1, max_length=128, pattern=_CODE_PATTERN)
    direction: AiExportEventDirection | None = None
    values: dict[CodeKey, SafeDecimal] = Field(..., min_length=1)


class AiExportTechnicalCoverage(AiExportModel):
    portfolio_assets: int = Field(..., ge=0)
    technically_eligible_assets: int = Field(..., ge=0)
    technically_analyzed_assets: int = Field(..., ge=0)
    analyzed_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute NAV exposure analyzed; may exceed 100 under leverage.",
    )

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.technically_eligible_assets > self.portfolio_assets:
            raise ValueError("technically_eligible_assets cannot exceed portfolio_assets")
        if self.technically_analyzed_assets > self.technically_eligible_assets:
            raise ValueError("technically_analyzed_assets cannot exceed technically_eligible_assets")
        return self


class AiExportVolumeSignalCoverage(AiExportModel):
    eligible_assets: int = Field(..., ge=0)
    analyzed_assets: int = Field(..., ge=0)
    analyzed_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute NAV exposure analyzed for volume signals; may exceed 100 under leverage.",
    )

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.analyzed_assets > self.eligible_assets:
            raise ValueError("analyzed_assets cannot exceed eligible_assets")
        return self


class AiExportBreadthMetric(AiExportModel):
    code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    asset_count: int = Field(..., ge=0)
    eligible_asset_count: int = Field(..., ge=0)
    portfolio_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute portfolio NAV exposure matching the metric; may exceed 100 under leverage.",
    )
    eligible_nav_weight_pct: Percentage

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.asset_count > self.eligible_asset_count:
            raise ValueError("asset_count cannot exceed eligible_asset_count")
        return self


class AiExportWeightedBreadth(AiExportModel):
    eligible_assets: int = Field(..., ge=0)
    eligible_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute portfolio NAV exposure eligible for breadth; may exceed 100 under leverage.",
    )
    metrics: list[AiExportBreadthMetric] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_metrics(self) -> Self:
        codes = [metric.code for metric in self.metrics]
        if len(codes) != len(set(codes)):
            raise ValueError("breadth metric codes must be unique")
        if any(metric.eligible_asset_count != self.eligible_assets for metric in self.metrics):
            raise ValueError("breadth metric eligible_asset_count must match eligible_assets")
        return self


class AiExportCoverage(AiExportModel):
    technical: AiExportTechnicalCoverage | None = None
    volume: AiExportVolumeSignalCoverage | None = None
    weighted_breadth: AiExportWeightedBreadth | None = None


class AiExportMetricSemantic(AiExportModel):
    metric_code: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    unit: str = Field(..., min_length=1, max_length=64, pattern=_CODE_PATTERN)
    denominator: str | None = Field(None, min_length=1, max_length=160, pattern=_CODE_PATTERN)
    method: str | None = Field(None, min_length=1, max_length=128, pattern=_CODE_PATTERN)
    period: DateRangeModel | None = None
    universe: str | None = Field(None, min_length=1, max_length=128, pattern=_CODE_PATTERN)
    annualized: bool | None = None
    cumulative: bool | None = None


class AiExportSignalSemantic(AiExportModel):
    semantic_id: str = Field(..., min_length=1, max_length=128, pattern=_CODE_PATTERN)
    description: str = Field(..., min_length=1, max_length=500)


class AiExportCurrencySemantics(AiExportModel):
    trading_currency: CurrencyCode | None = None
    valuation_currency: CurrencyCode
    underlying_currency_exposure_available: bool = False
    allocation_semantics: Literal[
        "position_or_valuation_currency_not_lookthrough_exposure",
        "lookthrough_exposure",
    ] = "position_or_valuation_currency_not_lookthrough_exposure"

    @model_validator(mode="after")
    def validate_exposure_semantics(self) -> Self:
        if self.allocation_semantics == "position_or_valuation_currency_not_lookthrough_exposure" and self.underlying_currency_exposure_available:
            raise ValueError("non-lookthrough allocation semantics cannot claim underlying currency exposure")
        return self


class AiExportSemantics(AiExportModel):
    metric_semantics: list[AiExportMetricSemantic] = Field(default_factory=list)
    signal_semantics: list[AiExportSignalSemantic] = Field(default_factory=list)
    currency_semantics: AiExportCurrencySemantics | None = None

    @model_validator(mode="after")
    def validate_semantics(self) -> Self:
        metric_codes = [semantic.metric_code for semantic in self.metric_semantics]
        signal_codes = [semantic.semantic_id for semantic in self.signal_semantics]
        if len(metric_codes) != len(set(metric_codes)):
            raise ValueError("metric semantic codes must be unique")
        if len(signal_codes) != len(set(signal_codes)):
            raise ValueError("signal semantic ids must be unique")
        return self


class AiExportDomainNote(AiExportModel):
    subject: AiExportNoteSubject
    source: AiExportNoteSource
    text: str = Field(..., min_length=1, max_length=4000)
    subject_reference: str | None = Field(None, min_length=1, max_length=160)
    observed_at: date | None = None


class AiExportCanonicalJsonStats(AiExportModel):
    positions: int = Field(0, ge=0)
    technical_assets: int = Field(0, ge=0)
    series_points: int = Field(0, ge=0)
    events: int = Field(0, ge=0)
    serialized_characters: int = Field(..., ge=0)


class AiExportTokenEstimate(AiExportModel):
    method: AiExportTokenEstimationMethod
    estimated_tokens: int = Field(..., ge=0)


class AiExportExportStats(AiExportModel):
    canonical_json: AiExportCanonicalJsonStats
    token_estimate: AiExportTokenEstimate


class AiExportSelectionMetadata(AiExportModel):
    selection_rule: str = Field(
        ...,
        min_length=1,
        max_length=160,
        pattern=_CODE_PATTERN,
        validation_alias=AliasChoices("selection_rule", "rule"),
    )
    limit: PositiveInt
    total_entity_count: int = Field(..., ge=0)
    included_entity_count: int = Field(..., ge=0)
    total_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute NAV exposure of all selection candidates; may exceed 100 under leverage.",
    )
    included_nav_weight_pct: GrossNavWeightPercentage = Field(
        ...,
        description="Gross absolute NAV exposure of included candidates; may exceed 100 under leverage.",
    )

    @property
    def rule(self) -> str:
        return self.selection_rule

    @property
    def entity_limit(self) -> int:
        return self.limit

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if self.included_entity_count > self.total_entity_count:
            raise ValueError("included_entity_count cannot exceed total_entity_count")
        if self.included_nav_weight_pct > self.total_nav_weight_pct:
            raise ValueError("included_nav_weight_pct cannot exceed total_nav_weight_pct")
        return self


class AiExportPosition(AiExportModel):
    asset_id: PositiveInt
    name: str = Field(..., min_length=1, max_length=300)
    ticker: str | None = Field(None, min_length=1, max_length=64)
    asset_type: str | None = Field(None, min_length=1, max_length=128)
    broker_id: PositiveInt | None = None
    broker_name: str | None = Field(None, min_length=1, max_length=300)
    broker_ids: BrokerIds = Field(default_factory=list)
    quantity: SafeDecimal
    trading_currency: CurrencyCode | None = None
    valuation_currency: CurrencyCode | None = None
    valuation_source: AiExportValuationSource
    current_unit_price: Currency | None = None
    valuation_effective_unit_price: Currency | None = None
    valuation_reference_date: date | None = None
    valuation_reference_unit_price: Currency | None = None
    valuation_split_adjusted: bool | None = None
    missing_fx_pair: str | None = Field(None, min_length=1, max_length=32)
    average_unit_cost: Currency | None = None
    cost_basis: Currency | None = None
    market_value: Currency | None = None
    weight_pct: SignedNavWeightPercentage | None = Field(
        None,
        description="Signed position market value as a percentage of NAV; unbounded under shorting or leverage.",
    )
    period_pnl_amount: Currency | None = None
    period_pnl_pct: SafeDecimal | None = None
    realized_pnl_amount: Currency | None = None
    unrealized_pnl_amount: Currency | None = None
    period_unrealized_delta_amount: Currency | None = None
    period_income_amount: Currency | None = None
    period_fees_taxes_amount: Currency | None = None

    @model_validator(mode="after")
    def validate_valuation(self) -> Self:
        valuation_dependent_fields = {
            "current_unit_price": self.current_unit_price,
            "market_value": self.market_value,
            "weight_pct": self.weight_pct,
            "unrealized_pnl_amount": self.unrealized_pnl_amount,
        }
        if self.valuation_source == AiExportValuationSource.MISSING:
            present = [name for name, value in valuation_dependent_fields.items() if value is not None]
            if present:
                raise ValueError("missing valuation_source requires valuation-dependent fields to be omitted: " + ", ".join(present))
        elif self.valuation_source == AiExportValuationSource.MARKET_PRICE and self.market_value is None:
            raise ValueError("market_price valuation_source requires market_value")
        return self


class AiExportContribution(AiExportModel):
    asset_id: PositiveInt
    name: str = Field(..., min_length=1, max_length=300)
    ticker: str | None = Field(None, min_length=1, max_length=64)
    asset_type: str | None = Field(None, min_length=1, max_length=128)
    broker_id: PositiveInt | None = None
    broker_name: str | None = Field(None, min_length=1, max_length=300)
    period_unrealized_delta_amount: Currency | None = None
    period_realized_pnl_amount: Currency | None = None
    period_pnl_amount: Currency | None = None
    period_income_amount: Currency | None = None
    fees_taxes_amount: Currency | None = None
    contribution_pct: SafeDecimal | None = None
    start_value: Currency | None = None
    end_value: Currency | None = None
    is_fully_sold: bool = False


class AiExportUnallocatedContribution(AiExportModel):
    broker_id: PositiveInt
    broker_name: str | None = Field(None, min_length=1, max_length=300)
    unallocated_income_amount: Currency | None = None
    unallocated_fees_taxes_amount: Currency | None = None


class AiExportOtherPeriodEffect(AiExportModel):
    description: str = Field(..., min_length=1, max_length=500)
    category: Literal["Income", "Cost", "Other"]
    period_pnl_amount: Currency
    broker_id: PositiveInt | None = None
    broker_name: str | None = Field(None, min_length=1, max_length=300)


class AiExportAllocationEntry(AiExportModel):
    key: str = Field(..., min_length=1, max_length=160)
    label: str | None = Field(None, min_length=1, max_length=300)
    amount: Currency | None = None
    weight_pct: SignedNavWeightPercentage = Field(
        ...,
        description="Signed allocation amount as a percentage of the metric-specific denominator declared in metric semantics; unbounded under shorting or leverage.",
    )
    is_other: bool = False


class AiExportPortfolioAllocations(AiExportModel):
    by_asset: list[AiExportAllocationEntry] = Field(default_factory=list)
    by_asset_type: list[AiExportAllocationEntry] = Field(default_factory=list)
    by_sector: list[AiExportAllocationEntry] = Field(default_factory=list)
    by_geography: list[AiExportAllocationEntry] = Field(default_factory=list)
    by_currency: list[AiExportAllocationEntry] = Field(default_factory=list)
    by_broker: list[AiExportAllocationEntry] = Field(default_factory=list)


class AiExportCashContext(AiExportModel):
    total_cash: Currency
    cash_from_capital: Currency
    cash_from_generated_returns: Currency


class AiExportPortfolioSummary(AiExportModel):
    base_currency: CurrencyCode
    nav: Currency
    market_value: Currency
    cash: Currency
    book_value: Currency
    net_contributed_capital: Currency | None = None
    start_nav: Currency | None = None
    net_deposits: Currency | None = None
    lifetime_pnl_amount: Currency | None = None
    period_pnl_amount: Currency | None = None
    realized_pnl_amount: Currency | None = None
    unrealized_pnl_amount: Currency | None = None
    income_amount: Currency | None = None
    fees_taxes_amount: Currency | None = None
    twrr_cumulative_pct: SafeDecimal | None = None
    mwrr_annualized_pct: SafeDecimal | None = None
    roi_cumulative_pct: SafeDecimal | None = None


class AiExportFifoLotDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class AiExportFifoLotStatus(StrEnum):
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


class AiExportFifoLotValueSource(StrEnum):
    MARKET_PRICE = "MARKET_PRICE"
    ESTIMATED_AT_COST = "ESTIMATED_AT_COST"


class AiExportFifoLotRow(AiExportModel):
    """One authoritative FIFO lot row: every open/partial lot plus fully closed lots whose
    authoritative closing_date falls within the reporting cutoff (previous 3 calendar months
    relative to snapshot_as_of). Primary identity is asset + opening_date + opening broker;
    lot_id/opening_transaction_id are internal engine identifiers and are never serialized.
    """

    asset_id: PositiveInt
    asset_name: str = Field(..., min_length=1, max_length=300)
    asset_symbol: str | None = Field(None, min_length=1, max_length=64)
    opening_broker_id: PositiveInt
    opening_broker_name: str | None = Field(None, min_length=1, max_length=300)
    opening_date: date
    closing_date: date | None = Field(None, description="Authoritative closing date; set only when status=closed.")
    direction: AiExportFifoLotDirection
    status: AiExportFifoLotStatus
    opening_unit_price: Currency
    original_quantity: SafeDecimal
    open_quantity: SafeDecimal
    realized_quantity: SafeDecimal
    original_cost: Currency
    residual_cost_basis: Currency = Field(..., description="original_cost * open_quantity / original_quantity; 0 for closed lots.")
    cumulative_proceeds: Currency
    open_value: Currency | None = None
    realized_pnl: Currency
    unrealized_pnl: Currency | None = None
    total_pnl: Currency | None = None
    income: Currency
    fees: Currency
    taxes: Currency
    net_total_pnl: Currency | None = None
    value_source: AiExportFifoLotValueSource | None = None
    states: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_closing_date(self) -> Self:
        if self.status == AiExportFifoLotStatus.CLOSED and self.closing_date is None:
            raise ValueError("closed lot rows require closing_date")
        if self.status != AiExportFifoLotStatus.CLOSED and self.closing_date is not None:
            raise ValueError("only closed lot rows may set closing_date")
        return self


class AiExportFifoSummary(AiExportModel):
    open_lot_count: int = Field(0, ge=0)
    partial_lot_count: int = Field(0, ge=0)
    closed_lot_count: int = Field(0, ge=0)
    average_age_days: NonNegativeDecimal | None = None
    oldest_lot_date: date | None = None
    residual_cost_basis: Currency | None = None
    market_value: Currency | None = None
    realized_pnl_amount: Currency | None = None
    unrealized_pnl_amount: Currency | None = None
    income_amount: Currency | None = None
    in_transit_quantity: SafeDecimal | None = None
    short_quantity: SafeDecimal | None = None
    estimated_at_cost_value: Currency | None = None


class AiExportPortfolioFacts(AiExportModel):
    summary: AiExportPortfolioSummary
    positions: list[AiExportPosition] = Field(default_factory=list)
    contributions: list[AiExportContribution] = Field(default_factory=list)
    unallocated_contributions: list[AiExportUnallocatedContribution] = Field(default_factory=list)
    other_period_effects: list[AiExportOtherPeriodEffect] = Field(default_factory=list)
    allocations: AiExportPortfolioAllocations = Field(default_factory=AiExportPortfolioAllocations)
    cash_context: AiExportCashContext | None = None
    fifo_summary: AiExportFifoSummary | None = None
    fifo_lots: list[AiExportFifoLotRow] = Field(default_factory=list)
    fifo_lot_selection: AiExportSelectionMetadata | None = None
    selection: AiExportSelectionMetadata | None = None


class AiExportNormalizedReturnPoint(AiExportModel):
    date: date
    source_value: SafeDecimal
    return_from_base_pct: SafeDecimal


class AiExportNormalizedReturn(AiExportModel):
    requested_range: DateRangeModel
    base_date: date
    base_source: AiExportNormalizedReturnBaseSource
    base_value: SafeDecimal = Field(..., gt=0)
    source_currency: CurrencyCode | None = None
    window_complete: bool
    points: list[AiExportNormalizedReturnPoint] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_points(self) -> Self:
        if not self.requested_range.start <= self.base_date <= self.requested_range.end:
            raise ValueError("base_date must be inside requested_range")

        first = self.points[0]
        if first.date != self.base_date:
            raise ValueError("first normalized return point date must equal base_date")
        if first.source_value != self.base_value:
            raise ValueError("first normalized return point source_value must equal base_value")
        if first.return_from_base_pct != 0:
            raise ValueError("first normalized return point return_from_base_pct must be zero")

        dates = [point.date for point in self.points]
        if any(point_date < self.requested_range.start or point_date > self.requested_range.end for point_date in dates):
            raise ValueError("normalized return point dates must be inside requested_range")
        if any(current >= following for current, following in zip(dates, dates[1:], strict=False)):
            raise ValueError("normalized return point dates must be strictly increasing and unique")

        if self.base_source == AiExportNormalizedReturnBaseSource.OBSERVED_MARKET_PRICE and self.base_date != self.requested_range.start:
            raise ValueError("observed_market_price requires base_date equal to requested_range.start")
        if self.base_source == AiExportNormalizedReturnBaseSource.FIRST_OBSERVED_MARKET_PRICE_IN_WINDOW and self.base_date <= self.requested_range.start:
            raise ValueError("first_observed_market_price_in_window requires base_date after requested_range.start")
        return self


class AiExportValuationReference(AiExportModel):
    date: date
    source: AiExportValuationReferenceSource
    unit_price: Currency
    effective_unit_price: Currency | None = None
    split_adjusted: bool = False
    semantics: Literal[
        "valuation_fallback_not_observed_market_return",
        "estimated_at_cost_not_observed_market_return",
    ] = "valuation_fallback_not_observed_market_return"

    @model_validator(mode="before")
    @classmethod
    def default_semantics_for_source(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "semantics" in data:
            return data
        source = data.get("source")
        if source == AiExportValuationReferenceSource.LAST_VISIBLE_BUY_UNIT_PRICE:
            semantics = "valuation_fallback_not_observed_market_return"
        elif source == AiExportValuationReferenceSource.LAST_SEED_COST:
            semantics = "estimated_at_cost_not_observed_market_return"
        else:
            return data
        return {**data, "semantics": semantics}

    @model_validator(mode="after")
    def validate_source_semantics(self) -> Self:
        expected = "valuation_fallback_not_observed_market_return" if self.source == AiExportValuationReferenceSource.LAST_VISIBLE_BUY_UNIT_PRICE else "estimated_at_cost_not_observed_market_return"
        if self.semantics != expected:
            raise ValueError(f"{self.source.value} requires semantics={expected}")
        reference_amount = self.unit_price.amount
        effective_amount = self.effective_unit_price.amount if self.effective_unit_price is not None else None
        if self.source == AiExportValuationReferenceSource.LAST_VISIBLE_BUY_UNIT_PRICE:
            if reference_amount <= 0 or (effective_amount is not None and effective_amount <= 0):
                raise ValueError("last_visible_buy_unit_price requires strictly positive unit prices")
        elif reference_amount < 0 or (effective_amount is not None and effective_amount < 0):
            raise ValueError("last_seed_cost requires non-negative unit prices")
        if self.split_adjusted and self.effective_unit_price is None:
            raise ValueError("split_adjusted valuation reference requires effective_unit_price")
        return self


class AiExportAssetIdentity(AiExportModel):
    asset_id: PositiveInt
    name: str = Field(..., min_length=1, max_length=300)
    ticker: str | None = Field(None, min_length=1, max_length=64)
    isin: str | None = Field(None, min_length=1, max_length=32)
    asset_type: str | None = Field(None, min_length=1, max_length=128)
    sector: str | None = Field(None, min_length=1, max_length=160)
    geography: str | None = Field(None, min_length=1, max_length=160)
    trading_currency: CurrencyCode
    valuation_currency: CurrencyCode


class AiExportAssetPricePoint(AiExportModel):
    date: date
    close: Currency
    volume: NonNegativeDecimal | None = None


class AiExportAssetMarketFacts(AiExportModel):
    current_price: Currency
    price_date: date
    period_change_pct: SafeDecimal | None = None
    drawdown_from_period_high_pct: SafeDecimal | None = None
    sampled_prices: list[AiExportAssetPricePoint] = Field(default_factory=list)


class AiExportAssetFacts(AiExportModel):
    identity: AiExportAssetIdentity
    market: AiExportAssetMarketFacts | None = None
    current_position: AiExportPosition | None = None
    lot_summary: AiExportFifoSummary | None = None
    normalized_return: AiExportNormalizedReturn | None = None
    valuation_reference: AiExportValuationReference | None = None

    @model_validator(mode="after")
    def validate_return_source(self) -> Self:
        if self.normalized_return is not None and self.valuation_reference is not None:
            raise ValueError("asset facts cannot contain both normalized_return and valuation_reference")
        if self.valuation_reference is not None:
            if self.market is not None:
                raise ValueError("asset facts with valuation_reference cannot contain market facts")
            if self.current_position is not None and self.current_position.valuation_source.value != self.valuation_reference.source.value:
                raise ValueError("current_position valuation_source must match valuation_reference source")
        return self


class AiExportFxIdentity(AiExportModel):
    base_currency: CurrencyCode
    quote_currency: CurrencyCode
    rate_semantics: Literal["quote_currency_per_base_currency"] = "quote_currency_per_base_currency"

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        return self


class AiExportFxRatePoint(AiExportModel):
    date: date
    rate: SafeDecimal = Field(..., gt=0)
    provider: str | None = Field(None, min_length=1, max_length=128)


class AiExportFxExtrema(AiExportModel):
    low_rate: SafeDecimal = Field(..., gt=0)
    low_date: date
    high_rate: SafeDecimal = Field(..., gt=0)
    high_date: date

    @model_validator(mode="after")
    def validate_rates(self) -> Self:
        if self.low_rate > self.high_rate:
            raise ValueError("low_rate cannot exceed high_rate")
        return self


class AiExportFxVolatility(AiExportModel):
    period_return_pct: SafeDecimal | None = None
    annualized_volatility_pct: NonNegativeDecimal | None = None
    max_drawdown_pct: SafeDecimal | None = None


class AiExportFxExposureLink(AiExportModel):
    kind: AiExportFxExposureKind
    linkage: AiExportFxExposureLinkage
    linked_currency: CurrencyCode
    exposure_amount: Currency
    asset_id: PositiveInt | None = None
    broker_id: PositiveInt | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> Self:
        if self.kind == AiExportFxExposureKind.POSITION and self.asset_id is None:
            raise ValueError("position exposure requires asset_id")
        if self.kind == AiExportFxExposureKind.CASH and self.asset_id is not None:
            raise ValueError("cash exposure cannot reference asset_id")
        return self


class AiExportFxFacts(AiExportModel):
    identity: AiExportFxIdentity
    current_rate: AiExportFxRatePoint
    sampled_rates: list[AiExportFxRatePoint] = Field(default_factory=list)
    extrema: AiExportFxExtrema | None = None
    volatility: AiExportFxVolatility | None = None
    normalized_return: AiExportNormalizedReturn | None = None
    exposure_links: list[AiExportFxExposureLink] = Field(default_factory=list)


class AiExportBrokerSummary(AiExportModel):
    broker_id: PositiveInt
    name: str = Field(..., min_length=1, max_length=300)
    base_currency: CurrencyCode
    nav: Currency
    market_value: Currency
    cash: Currency
    book_value: Currency | None = None
    net_contributed_capital: Currency | None = None
    start_nav: Currency | None = None
    net_deposits: Currency | None = None
    lifetime_pnl_amount: Currency | None = None
    period_pnl_amount: Currency | None = None
    realized_pnl_amount: Currency | None = None
    unrealized_pnl_amount: Currency | None = None
    income_amount: Currency | None = None
    fees_taxes_amount: Currency | None = None
    twrr_cumulative_pct: SafeDecimal | None = None
    mwrr_annualized_pct: SafeDecimal | None = None
    roi_cumulative_pct: SafeDecimal | None = None


class AiExportConcentrationEntry(AiExportModel):
    asset_id: PositiveInt
    name: str = Field(..., min_length=1, max_length=300)
    market_value: Currency
    weight_pct: Percentage


class AiExportBrokerConcentration(AiExportModel):
    position_count: int = Field(..., ge=0)
    largest_position_weight_pct: Percentage | None = None
    top_five_weight_pct: Percentage | None = None
    herfindahl_index: Ratio | None = None
    entries: list[AiExportConcentrationEntry] = Field(default_factory=list)


class AiExportLatestTransaction(AiExportModel):
    transaction_date: date
    transaction_type: str = Field(..., min_length=1, max_length=128)
    asset_id: PositiveInt | None = None
    quantity: SafeDecimal | None = None
    gross_amount: Currency | None = None
    fees_taxes_amount: Currency | None = None


class AiExportBrokerFacts(AiExportModel):
    summary: AiExportBrokerSummary
    positions: list[AiExportPosition] = Field(default_factory=list)
    contributions: list[AiExportContribution] = Field(default_factory=list)
    unallocated_contributions: list[AiExportUnallocatedContribution] = Field(default_factory=list)
    other_period_effects: list[AiExportOtherPeriodEffect] = Field(default_factory=list)
    concentration: AiExportBrokerConcentration | None = None
    latest_transaction: AiExportLatestTransaction | None = None
    fifo_summary: AiExportFifoSummary | None = None
    fifo_lots: list[AiExportFifoLotRow] = Field(default_factory=list)
    fifo_lot_selection: AiExportSelectionMetadata | None = None
    selection: AiExportSelectionMetadata | None = None


class AiExportSnapshotResponseBase(AiExportModel):
    domain: AiExportDomain
    task: AiExportTask
    detail_level: AiExportDetailLevel
    meta: AiExportSnapshotMeta
    methodology: AiExportMethodology
    states: list[AiExportDerivedState] = Field(default_factory=list)
    technical: AiExportTechnicalSnapshot | None = None
    events: list[AiExportEvent] = Field(default_factory=list)
    coverage: AiExportCoverage = Field(default_factory=AiExportCoverage)
    semantics: AiExportSemantics = Field(default_factory=AiExportSemantics)
    domain_notes: list[AiExportDomainNote] = Field(default_factory=list)
    export_stats: AiExportExportStats

    @model_validator(mode="after")
    def validate_contract_identity(self) -> Self:
        expected_profile_id = f"{self.domain.value}.{self.task.value}.{self.detail_level.value}"
        if self.meta.profile_id != expected_profile_id:
            raise ValueError(f"meta.profile_id must be {expected_profile_id}")
        expected_contract_id = f"{self.domain.value}.{self.task.value}"
        if self.meta.frontend_response_contract_id != expected_contract_id:
            raise ValueError(f"meta.frontend_response_contract_id must be {expected_contract_id}")
        return self


class AiExportPortfolioSnapshotResponse(AiExportSnapshotResponseBase):
    domain: Literal[AiExportDomain.PORTFOLIO] = Field(json_schema_extra={"enum": ["portfolio"]})
    task: AiExportPortfolioTask
    facts: AiExportPortfolioFacts


class AiExportAssetSnapshotResponse(AiExportSnapshotResponseBase):
    domain: Literal[AiExportDomain.ASSET] = Field(json_schema_extra={"enum": ["asset"]})
    task: AiExportAssetTask
    facts: AiExportAssetFacts


class AiExportFxSnapshotResponse(AiExportSnapshotResponseBase):
    domain: Literal[AiExportDomain.FX] = Field(json_schema_extra={"enum": ["fx"]})
    task: AiExportFxTask
    facts: AiExportFxFacts


class AiExportBrokerSnapshotResponse(AiExportSnapshotResponseBase):
    domain: Literal[AiExportDomain.BROKER] = Field(json_schema_extra={"enum": ["broker"]})
    task: AiExportBrokerTask
    facts: AiExportBrokerFacts


AiExportSnapshotResponse = Annotated[
    Union[
        AiExportPortfolioSnapshotResponse,
        AiExportAssetSnapshotResponse,
        AiExportFxSnapshotResponse,
        AiExportBrokerSnapshotResponse,
    ],
    Field(discriminator="domain"),
]


class AiExportProblemBase(AiExportModel):
    message: str = Field(..., min_length=1, max_length=1000)
    domain: AiExportDomain | None = None
    task: AiExportTask | None = None
    detail_level: AiExportDetailLevel | None = None
    profile_id: ProfileId | None = None

    @model_validator(mode="after")
    def validate_task_domain(self) -> Self:
        if self.domain is not None and self.task is not None:
            if _TASK_DOMAIN_BY_VALUE[self.task.value] != self.domain:
                raise ValueError("task does not belong to domain")
        return self


class AiExportUnsupportedProfileProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.UNSUPPORTED_PROFILE] = Field(json_schema_extra={"enum": ["unsupported_profile"]})
    domain: AiExportDomain
    task: AiExportTask
    detail_level: AiExportDetailLevel
    supported_profiles: list[ProfileId] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_supported_profiles(self) -> Self:
        if len(self.supported_profiles) != len(set(self.supported_profiles)):
            raise ValueError("supported_profiles must contain unique profile ids")
        return self


class AiExportProfileContractMismatchProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.PROFILE_CONTRACT_MISMATCH] = Field(json_schema_extra={"enum": ["profile_contract_mismatch"]})
    profile_id: ProfileId
    expected_frontend_response_contract_id: ContractId
    expected_frontend_response_contract_version: PositiveInt
    actual_frontend_response_contract_id: ContractId
    actual_frontend_response_contract_version: PositiveInt

    @model_validator(mode="after")
    def validate_contract_mismatch(self) -> Self:
        expected = (
            self.expected_frontend_response_contract_id,
            self.expected_frontend_response_contract_version,
        )
        actual = (
            self.actual_frontend_response_contract_id,
            self.actual_frontend_response_contract_version,
        )
        if expected == actual:
            raise ValueError("expected and actual frontend response contracts must differ")
        return self


class AiExportTaskNotApplicableProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.TASK_NOT_APPLICABLE] = Field(json_schema_extra={"enum": ["task_not_applicable"]})
    domain: AiExportDomain
    task: AiExportTask
    detail_level: AiExportDetailLevel
    profile_id: ProfileId
    applicability_code: CodeKey
    reason_code: CodeKey = "not_applicable"

    @model_validator(mode="after")
    def validate_profile_identity(self) -> Self:
        expected_profile_id = f"{self.domain.value}.{self.task.value}.{self.detail_level.value}"
        if self.profile_id != expected_profile_id:
            raise ValueError(f"profile_id must be {expected_profile_id}")
        return self


class AiExportBrokerAccessDeniedProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.BROKER_ACCESS_DENIED] = Field(json_schema_extra={"enum": ["broker_access_denied"]})
    denied_broker_ids: NonEmptyBrokerIds


class AiExportEntityNotFoundProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.ENTITY_NOT_FOUND] = Field(json_schema_extra={"enum": ["entity_not_found"]})
    entity_reference: AiExportTargetReference


class AiExportSnapshotSourceFailureProblem(AiExportProblemBase):
    code: Literal[AiExportProblemCode.SNAPSHOT_SOURCE_FAILURE] = Field(json_schema_extra={"enum": ["snapshot_source_failure"]})
    source_code: CodeKey
    retryable: bool


AiExportProblem = Annotated[
    Union[
        AiExportUnsupportedProfileProblem,
        AiExportProfileContractMismatchProblem,
        AiExportTaskNotApplicableProblem,
        AiExportBrokerAccessDeniedProblem,
        AiExportEntityNotFoundProblem,
        AiExportSnapshotSourceFailureProblem,
    ],
    Field(discriminator="code"),
]


class AiExportProblemResponse(AiExportModel):
    """FastAPI HTTPException envelope for typed AI Export problems."""

    detail: AiExportProblem
