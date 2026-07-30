"""Public v1 contracts for component-based AI Export datasets and analyses."""

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


class AiExportPeriod(AiExportModel):
    """Inclusive AI Export period with an always-explicit upper bound."""

    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end < self.start:
            raise ValueError("period end must not precede start")
        return self


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

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if not self.id.startswith(f"{self.domain.value}."):
            raise ValueError("analysis id must belong to domain")
        if set(self.required_dataset_ids) & set(self.optional_dataset_ids):
            raise ValueError("required and optional datasets must not overlap")
        return self


class AiExportCatalogResponse(AiExportModel):
    schema_version: Literal[1] = 1
    catalog_version: Literal[1] = 1
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


class AiExportSnapshotMeta(AiExportModel):
    schema_version: Literal[1] = 1
    catalog_version: Literal[1] = 1
    request_id: str = Field(..., min_length=1)
    generated_at: datetime
    snapshot_as_of: date
    exported_period: AiExportPeriod
    calculation_range: AiExportPeriod | None = None
    warmup_policy: Literal["component_owned"] = "component_owned"
    earliest_calculation_date: date | None = None
    target_currency: CurrencyCode

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
    estimated_tokens: int = Field(..., ge=0)
    token_estimation_method: Literal["chars_div_4_v1"] = "chars_div_4_v1"


class AiExportPriceSamplingPolicy(AiExportModel):
    detail_level: AiExportDetailLevel
    p: PositiveInt
    m: PositiveInt
    k: PositiveInt
    bucket_count: PositiveInt


class AiExportIndicatorSamplingPolicy(AiExportModel):
    signal_instance_id: str = Field(..., min_length=1)
    signal_code: str = Field(..., min_length=1)
    temporal_class: SignalTemporalClass
    detail_level: AiExportDetailLevel
    p: PositiveInt
    m: PositiveInt
    k: PositiveInt
    bucket_count: PositiveInt


class AiExportTechnicalSamplingManifest(AiExportModel):
    price_policy: AiExportPriceSamplingPolicy | None = None
    indicator_policies: tuple[AiExportIndicatorSamplingPolicy, ...] = ()

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
    minimum_latest_events_per_annotation: Literal[20] = 20
    complete_recent_window_days: Literal[30] = 30
    grouped_by: tuple[
        Literal["entity_id"],
        Literal["annotation_key"],
    ] = ("entity_id", "annotation_key")


class AiExportSnapshotResponse(AiExportModel):
    domain: AiExportDomain
    selection: AiExportSelection
    detail_level: AiExportDetailLevel
    target: AiExportTargetReference
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
