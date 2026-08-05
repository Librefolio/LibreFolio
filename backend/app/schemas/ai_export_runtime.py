"""Public V1 contracts for component-based AI Export datasets and analyses."""

from __future__ import annotations

import math
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PositiveInt,
    field_validator,
    model_validator,
)

from backend.app.schemas.common import Currency
from backend.app.schemas.signals import SignalTemporalClass

_ID_PATTERN = r"^[a-z][a-z0-9_.-]*$"

AI_EXPORT_SCHEMA_VERSION = 1
AI_EXPORT_CATALOG_VERSION = 1
AI_EXPORT_SELECTION_VERSION = 1
AI_EXPORT_INSTRUCTION_TEMPLATE_VERSION = 1
AI_EXPORT_RESPONSE_CONTRACT_VERSION = 1


def _normalize_broker_ids(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise ValueError("broker_ids must contain unique values")
    return sorted(values)


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
NonEmptyBrokerIds = Annotated[
    list[PositiveInt],
    Field(min_length=1),
    AfterValidator(_normalize_broker_ids),
]
SelectionId = Annotated[
    str,
    Field(min_length=1, max_length=160, pattern=_ID_PATTERN),
]
ContractId = Annotated[
    str,
    Field(min_length=1, max_length=200, pattern=_ID_PATTERN),
]


class AiExportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AiExportDomain(StrEnum):
    PORTFOLIO = "portfolio"
    BROKER = "broker"
    ASSET = "asset"
    FX = "fx"


class AiExportDetailLevel(StrEnum):
    COMPACT = "compact"
    STANDARD = "standard"
    FULL = "full"


class AiExportSelectionKind(StrEnum):
    DATASET = "dataset"
    ANALYSIS = "analysis"


class AiExportPeriodSemantics(StrEnum):
    NONE = "none"
    AS_OF = "as_of"
    WINDOWED = "windowed"
    AGGREGATED = "aggregated"


class AiExportManifestRole(StrEnum):
    SELECTED = "selected"
    REQUIRED = "required"
    OPTIONAL = "optional"


class AiExportAdditionalExportPeriod(StrEnum):
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    MAXIMUM_AVAILABLE = "maximum_available"


class AiExportAdditionalExportNecessity(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class AiExportPeriod(AiExportModel):
    """Inclusive AI Export period with an always-explicit upper bound."""

    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end < self.start:
            raise ValueError("period end must not precede start")
        return self


class AiExportAdditionalExportSuggestion(AiExportModel):
    dataset_id: SelectionId
    reason_i18n_key: str = Field(..., min_length=1)
    recommended_period: AiExportAdditionalExportPeriod
    recommended_detail: AiExportDetailLevel
    necessity: AiExportAdditionalExportNecessity


class AiExportDatasetSelection(AiExportModel):
    kind: Literal["dataset"] = Field(json_schema_extra={"enum": ["dataset"]})
    id: SelectionId
    version: PositiveInt


class AiExportAnalysisSelection(AiExportModel):
    kind: Literal["analysis"] = Field(json_schema_extra={"enum": ["analysis"]})
    id: SelectionId
    version: PositiveInt
    instruction_template_id: ContractId
    instruction_template_version: PositiveInt
    response_contract_id: ContractId
    response_contract_version: PositiveInt


AiExportSelection = Annotated[
    Union[AiExportDatasetSelection, AiExportAnalysisSelection],
    Field(discriminator="kind"),
]


class AiExportSnapshotRequestBase(AiExportModel):
    domain: AiExportDomain
    selection: AiExportSelection
    detail_level: AiExportDetailLevel
    period: AiExportPeriod
    target_currency: CurrencyCode
    expected_catalog_version: PositiveInt

    @model_validator(mode="after")
    def validate_period_and_selection(self) -> Self:
        domain = self.domain.value if isinstance(self.domain, AiExportDomain) else self.domain
        if not self.selection.id.startswith(f"{domain}."):
            raise ValueError("selection id must belong to request domain")
        return self


class AiExportPortfolioSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal["portfolio"] = Field(json_schema_extra={"enum": ["portfolio"]})
    broker_ids: NonEmptyBrokerIds = Field(default_factory=list)


class AiExportBrokerSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal["broker"] = Field(json_schema_extra={"enum": ["broker"]})
    broker_id: PositiveInt


class AiExportAssetSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal["asset"] = Field(json_schema_extra={"enum": ["asset"]})
    asset_id: PositiveInt
    broker_ids: NonEmptyBrokerIds = Field(default_factory=list)


class AiExportFxSnapshotRequest(AiExportSnapshotRequestBase):
    domain: Literal["fx"] = Field(json_schema_extra={"enum": ["fx"]})
    base_currency: CurrencyCode
    quote_currency: CurrencyCode
    broker_ids: NonEmptyBrokerIds = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pair(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        return self


AiExportSnapshotRequest = Annotated[
    Union[
        AiExportPortfolioSnapshotRequest,
        AiExportBrokerSnapshotRequest,
        AiExportAssetSnapshotRequest,
        AiExportFxSnapshotRequest,
    ],
    Field(discriminator="domain"),
]


class AiExportDatasetCatalogEntry(AiExportModel):
    kind: Literal["dataset"] = Field(json_schema_extra={"enum": ["dataset"]})
    id: SelectionId
    version: PositiveInt
    domain: AiExportDomain
    display_i18n_key: str = Field(..., min_length=1)
    description_i18n_key: str = Field(..., min_length=1)
    icon: str = Field(..., min_length=1)
    applicability_code: str = Field(..., min_length=1, pattern=_ID_PATTERN)
    applicable_pages: tuple[str, ...]
    supported_detail_levels: tuple[AiExportDetailLevel, ...]
    period_semantics: AiExportPeriodSemantics
    required_component_ids: tuple[SelectionId, ...]
    optional_component_ids: tuple[SelectionId, ...]

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if not self.id.startswith(f"{self.domain.value}."):
            raise ValueError("dataset id must belong to domain")
        if len(self.supported_detail_levels) != len(set(self.supported_detail_levels)):
            raise ValueError("supported_detail_levels must be unique")
        if set(self.required_component_ids) & set(self.optional_component_ids):
            raise ValueError("required and optional components must not overlap")
        return self


class AiExportAnalysisCatalogEntry(AiExportModel):
    kind: Literal["analysis"] = Field(json_schema_extra={"enum": ["analysis"]})
    id: SelectionId
    version: PositiveInt
    domain: AiExportDomain
    display_i18n_key: str = Field(..., min_length=1)
    description_i18n_key: str = Field(..., min_length=1)
    icon: str = Field(..., min_length=1)
    applicability_code: str = Field(..., min_length=1, pattern=_ID_PATTERN)
    applicable_pages: tuple[str, ...]
    supported_detail_levels: tuple[AiExportDetailLevel, ...]
    required_dataset_ids: tuple[SelectionId, ...]
    optional_dataset_ids: tuple[SelectionId, ...]
    instruction_template_id: ContractId
    instruction_template_version: PositiveInt
    response_contract_id: ContractId
    response_contract_version: PositiveInt
    supports_user_notes: bool = True
    additional_export_suggestions: tuple[AiExportAdditionalExportSuggestion, ...] = ()

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if not self.id.startswith(f"{self.domain.value}."):
            raise ValueError("analysis id must belong to domain")
        if set(self.required_dataset_ids) & set(self.optional_dataset_ids):
            raise ValueError("required and optional datasets must not overlap")
        suggestion_ids = [suggestion.dataset_id for suggestion in self.additional_export_suggestions]
        if len(suggestion_ids) != len(set(suggestion_ids)):
            raise ValueError("additional export suggestion dataset IDs must be unique")
        if any(not dataset_id.startswith(f"{self.domain.value}.") for dataset_id in suggestion_ids):
            raise ValueError("additional export suggestions must belong to the analysis domain")
        return self


class AiExportCatalogResponse(AiExportModel):
    schema_version: Literal[AI_EXPORT_SCHEMA_VERSION] = AI_EXPORT_SCHEMA_VERSION
    catalog_version: Literal[AI_EXPORT_CATALOG_VERSION] = AI_EXPORT_CATALOG_VERSION
    datasets: tuple[AiExportDatasetCatalogEntry, ...]
    analyses: tuple[AiExportAnalysisCatalogEntry, ...]

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        dataset_ids = [entry.id for entry in self.datasets]
        analysis_ids = [entry.id for entry in self.analyses]
        if len(dataset_ids) != len(set(dataset_ids)):
            raise ValueError("dataset catalog ids must be unique")
        if len(analysis_ids) != len(set(analysis_ids)):
            raise ValueError("analysis catalog ids must be unique")
        if set(dataset_ids) & set(analysis_ids):
            raise ValueError("dataset and analysis ids must not overlap")
        return self


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


AiExportTargetReference = Annotated[
    Union[
        AiExportPortfolioTargetReference,
        AiExportBrokerTargetReference,
        AiExportAssetTargetReference,
        AiExportFxPairTargetReference,
    ],
    Field(discriminator="kind"),
]


class AiExportAssetDirectoryEntry(AiExportModel):
    asset_id: PositiveInt
    display_name: str = Field(..., min_length=1)
    ticker: str | None = None
    isin: str | None = None
    cusip: str | None = None
    sedol: str | None = None
    figi: str | None = None
    other_identifiers: tuple[str, ...] = ()
    currency: CurrencyCode
    asset_type: str = Field(..., min_length=1)
    quote_base_quantity: PositiveInt


class AiExportBrokerDirectoryEntry(AiExportModel):
    broker_id: PositiveInt
    display_name: str = Field(..., min_length=1)


class AiExportFxPairDirectoryEntry(AiExportModel):
    base_currency: CurrencyCode
    quote_currency: CurrencyCode


class AiExportEntityDirectory(AiExportModel):
    assets: tuple[AiExportAssetDirectoryEntry, ...] = ()
    brokers: tuple[AiExportBrokerDirectoryEntry, ...] = ()
    fx_pairs: tuple[AiExportFxPairDirectoryEntry, ...] = ()

    @model_validator(mode="after")
    def validate_directory(self) -> Self:
        asset_ids = [entry.asset_id for entry in self.assets]
        broker_ids = [entry.broker_id for entry in self.brokers]
        fx_pairs = [(entry.base_currency, entry.quote_currency) for entry in self.fx_pairs]
        if asset_ids != sorted(set(asset_ids)):
            raise ValueError("entity directory assets must be unique and sorted by asset_id")
        if broker_ids != sorted(set(broker_ids)):
            raise ValueError("entity directory brokers must be unique and sorted by broker_id")
        if fx_pairs != sorted(set(fx_pairs)):
            raise ValueError("entity directory FX pairs must be unique and sorted")
        return self


class AiExportHistoryCoverage(AiExportModel):
    requested_period: AiExportPeriod
    available_period: AiExportPeriod | None = None
    requested_calendar_days: PositiveInt
    covered_calendar_days: int = Field(..., ge=0)
    coverage_ratio: float = Field(..., ge=0, le=1)
    complete: bool
    reason_code: Literal["insufficient_source_history"] | None = None
    observed_count: int = Field(..., ge=0)
    backward_filled_count: int = Field(..., ge=0)
    earliest_source_date: date | None = None

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        expected_requested_days = (self.requested_period.end - self.requested_period.start).days + 1
        if self.requested_calendar_days != expected_requested_days:
            raise ValueError("requested_calendar_days must match requested_period")
        if self.available_period is None:
            if self.covered_calendar_days != 0 or self.coverage_ratio != 0:
                raise ValueError("missing available_period requires zero coverage")
        else:
            if self.available_period.start < self.requested_period.start or self.available_period.end > self.requested_period.end:
                raise ValueError("available_period must fall inside requested_period")
            expected_covered_days = (self.available_period.end - self.available_period.start).days + 1
            if self.covered_calendar_days != expected_covered_days:
                raise ValueError("covered_calendar_days must match available_period")
        expected_ratio = self.covered_calendar_days / self.requested_calendar_days
        if not math.isclose(self.coverage_ratio, expected_ratio, rel_tol=0, abs_tol=1e-12):
            raise ValueError("coverage_ratio must reconcile calendar-day coverage")
        if self.complete != (self.covered_calendar_days == self.requested_calendar_days):
            raise ValueError("complete must reflect full requested-period coverage")
        if self.complete != (self.reason_code is None):
            raise ValueError("reason_code must be absent only for complete coverage")
        if self.earliest_source_date is None and (self.observed_count > 0 or self.backward_filled_count > 0):
            raise ValueError("non-empty history coverage requires earliest_source_date")
        return self


class AiExportSnapshotMeta(AiExportModel):
    schema_version: Literal[AI_EXPORT_SCHEMA_VERSION] = AI_EXPORT_SCHEMA_VERSION
    catalog_version: Literal[AI_EXPORT_CATALOG_VERSION] = AI_EXPORT_CATALOG_VERSION
    request_id: str = Field(..., min_length=1)
    generated_at: datetime
    snapshot_as_of: date
    exported_period: AiExportPeriod
    calculation_range: AiExportPeriod | None = None
    warmup_policy: Literal["component_owned"] = "component_owned"
    earliest_calculation_date: date | None = None
    target_currency: CurrencyCode
    history_coverage: AiExportHistoryCoverage | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.exported_period.end != self.snapshot_as_of:
            raise ValueError("exported_period.end must equal snapshot_as_of")
        if self.calculation_range is not None and self.calculation_range.start > self.exported_period.start:
            raise ValueError("calculation_range cannot start after exported_period")
        return self


class AiExportDatasetManifestEntry(AiExportModel):
    dataset_id: SelectionId
    dataset_version: PositiveInt
    role: AiExportManifestRole


class AiExportSectionEnvelope(AiExportModel):
    component_id: SelectionId
    component_version: PositiveInt
    schema_id: SelectionId
    schema_version: PositiveInt
    payload: dict[str, JsonValue]

    @field_validator("payload", mode="before")
    @classmethod
    def validate_payload(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "payload")


class AiExportAnalysisContract(AiExportModel):
    instruction_template_id: ContractId
    instruction_template_version: PositiveInt
    response_contract_id: ContractId
    response_contract_version: PositiveInt


class AiExportSnapshotStats(AiExportModel):
    dataset_count: int = Field(..., ge=1)
    section_count: int = Field(..., ge=1)
    serialized_characters: int = Field(..., ge=0)
    serialized_bytes: int = Field(..., ge=0)
    estimated_tokens: int = Field(..., ge=0)
    token_estimation_method: Literal["chars_div_4_v1"] = "chars_div_4_v1"


class AiExportPriceSamplingPolicy(AiExportModel):
    bucket_count: PositiveInt


class AiExportIndicatorSamplingPolicy(AiExportModel):
    signal_instance_id: str = Field(..., min_length=1)
    signal_code: str = Field(..., min_length=1)
    temporal_class: SignalTemporalClass
    bucket_count: PositiveInt


class AiExportTechnicalSamplingManifest(AiExportModel):
    detail_level: AiExportDetailLevel
    price_policy: AiExportPriceSamplingPolicy | None = None
    indicator_policies: tuple[AiExportIndicatorSamplingPolicy, ...] = ()
    indicator_history_row_limit: int | None = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        if self.price_policy is None and not self.indicator_policies:
            raise ValueError("technical sampling manifest must declare a price or indicator policy")
        instance_ids = [policy.signal_instance_id for policy in self.indicator_policies]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("indicator sampling policies must have unique signal_instance_id")
        if instance_ids != sorted(instance_ids):
            raise ValueError("indicator sampling policies must be sorted by signal_instance_id")
        return self


class AiExportEventSelectionManifest(AiExportModel):
    minimum_latest_events_per_annotation: int = Field(20, ge=1)
    complete_recent_window_days: int = Field(30, ge=0)
    grouped_by: tuple[
        Literal["entity_id"],
        Literal["annotation_key"],
    ] = ("entity_id", "annotation_key")


class AiExportSnapshotResponse(AiExportModel):
    domain: AiExportDomain
    selection: AiExportSelection
    detail_level: AiExportDetailLevel
    target: AiExportTargetReference
    entity_directory: AiExportEntityDirectory = Field(default_factory=AiExportEntityDirectory)
    meta: AiExportSnapshotMeta
    dataset_manifest: tuple[AiExportDatasetManifestEntry, ...] = Field(..., min_length=1)
    analysis_contract: AiExportAnalysisContract | None = None
    technical_sampling: AiExportTechnicalSamplingManifest | None = None
    event_selection: AiExportEventSelectionManifest | None = None
    sections: tuple[AiExportSectionEnvelope, ...] = Field(..., min_length=1)
    stats: AiExportSnapshotStats

    @model_validator(mode="after")
    def validate_response(self) -> Self:
        if self.selection.kind == "analysis" and self.analysis_contract is None:
            raise ValueError("analysis selection requires analysis_contract")
        if self.selection.kind == "dataset" and self.analysis_contract is not None:
            raise ValueError("dataset selection must not include analysis_contract")
        dataset_ids = [entry.dataset_id for entry in self.dataset_manifest]
        if len(dataset_ids) != len(set(dataset_ids)):
            raise ValueError("dataset_manifest ids must be unique")
        section_ids = [section.component_id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("section component_ids must be unique")
        if self.stats.dataset_count != len(self.dataset_manifest):
            raise ValueError("stats.dataset_count must match dataset_manifest")
        if self.stats.section_count != len(self.sections):
            raise ValueError("stats.section_count must match sections")
        expected_target_kind = {
            AiExportDomain.PORTFOLIO: "portfolio",
            AiExportDomain.BROKER: "broker",
            AiExportDomain.ASSET: "asset",
            AiExportDomain.FX: "fx_pair",
        }[self.domain]
        if self.target.kind != expected_target_kind:
            raise ValueError("target kind must match response domain")
        return self


class AiExportProblemCode(StrEnum):
    VERSION_MISMATCH = "version_mismatch"
    UNSUPPORTED_SELECTION = "unsupported_selection"
    SELECTION_NOT_APPLICABLE = "selection_not_applicable"
    BROKER_ACCESS_DENIED = "broker_access_denied"
    ENTITY_NOT_FOUND = "entity_not_found"
    SNAPSHOT_SOURCE_FAILURE = "snapshot_source_failure"


class AiExportProblemBase(AiExportModel):
    code: AiExportProblemCode
    message: str = Field(..., min_length=1)
    domain: AiExportDomain
    selection_kind: AiExportSelectionKind
    selection_id: SelectionId
    detail_level: AiExportDetailLevel


class AiExportVersionMismatchProblem(AiExportProblemBase):
    code: Literal["version_mismatch"] = Field(json_schema_extra={"enum": ["version_mismatch"]})
    field: str = Field(..., min_length=1, pattern=_ID_PATTERN)
    expected: str = Field(..., min_length=1)
    actual: str = Field(..., min_length=1)


class AiExportUnsupportedSelectionProblem(AiExportProblemBase):
    code: Literal["unsupported_selection"] = Field(json_schema_extra={"enum": ["unsupported_selection"]})


class AiExportSelectionNotApplicableProblem(AiExportProblemBase):
    code: Literal["selection_not_applicable"] = Field(json_schema_extra={"enum": ["selection_not_applicable"]})
    applicability_code: str = Field(..., min_length=1, pattern=_ID_PATTERN)
    reason_code: str = Field(..., min_length=1, pattern=_ID_PATTERN)


class AiExportBrokerAccessDeniedProblem(AiExportProblemBase):
    code: Literal["broker_access_denied"] = Field(json_schema_extra={"enum": ["broker_access_denied"]})
    denied_broker_ids: NonEmptyBrokerIds


class AiExportEntityNotFoundProblem(AiExportProblemBase):
    code: Literal["entity_not_found"] = Field(json_schema_extra={"enum": ["entity_not_found"]})
    entity_reference: AiExportTargetReference


class AiExportSnapshotSourceFailureProblem(AiExportProblemBase):
    code: Literal["snapshot_source_failure"] = Field(json_schema_extra={"enum": ["snapshot_source_failure"]})
    component_id: SelectionId
    retryable: bool
    reason_code: str | None = Field(None, min_length=1, pattern=_ID_PATTERN)


AiExportProblem = Annotated[
    Union[
        AiExportVersionMismatchProblem,
        AiExportUnsupportedSelectionProblem,
        AiExportSelectionNotApplicableProblem,
        AiExportBrokerAccessDeniedProblem,
        AiExportEntityNotFoundProblem,
        AiExportSnapshotSourceFailureProblem,
    ],
    Field(discriminator="code"),
]


class AiExportProblemResponse(AiExportModel):
    detail: AiExportProblem


__all__ = [
    "AiExportAdditionalExportNecessity",
    "AiExportAdditionalExportPeriod",
    "AiExportAdditionalExportSuggestion",
    "AiExportAnalysisCatalogEntry",
    "AiExportAnalysisContract",
    "AiExportAnalysisSelection",
    "AiExportAssetSnapshotRequest",
    "AiExportAssetTargetReference",
    "AiExportBrokerAccessDeniedProblem",
    "AiExportBrokerSnapshotRequest",
    "AiExportBrokerTargetReference",
    "AiExportCatalogResponse",
    "AiExportDatasetCatalogEntry",
    "AiExportDatasetManifestEntry",
    "AiExportDatasetSelection",
    "AiExportDetailLevel",
    "AiExportDomain",
    "AiExportEntityNotFoundProblem",
    "AiExportFxPairTargetReference",
    "AiExportFxSnapshotRequest",
    "AiExportHistoryCoverage",
    "AiExportManifestRole",
    "AiExportPeriod",
    "AiExportPeriodSemantics",
    "AiExportPortfolioSnapshotRequest",
    "AiExportPortfolioTargetReference",
    "AiExportProblem",
    "AiExportProblemBase",
    "AiExportProblemCode",
    "AiExportProblemResponse",
    "AiExportPriceSamplingPolicy",
    "AiExportSectionEnvelope",
    "AiExportSelection",
    "AiExportSelectionKind",
    "AiExportSelectionNotApplicableProblem",
    "AiExportSnapshotMeta",
    "AiExportSnapshotRequest",
    "AiExportSnapshotResponse",
    "AiExportSnapshotSourceFailureProblem",
    "AiExportSnapshotStats",
    "AiExportTechnicalSamplingManifest",
    "AiExportIndicatorSamplingPolicy",
    "AiExportEventSelectionManifest",
    "AiExportTargetReference",
    "AiExportUnsupportedSelectionProblem",
    "AiExportVersionMismatchProblem",
]
