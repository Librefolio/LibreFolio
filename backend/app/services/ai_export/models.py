"""Immutable internal contracts for the curated AI Export profile catalog."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from backend.app.schemas.ai_export import (
    AiExportAssetTask,
    AiExportBrokerTask,
    AiExportCatalogEntry,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportFxTask,
    AiExportPortfolioTask,
    AiExportTask,
)

SCHEMA_VERSION = 1
PROFILE_VERSION = 1
FRONTEND_RESPONSE_CONTRACT_VERSION = 1
EXPECTED_TASK_COUNT = 19
EXPECTED_PROFILE_COUNT = 57

DETAIL_LEVEL_ORDER = (
    AiExportDetailLevel.COMPACT,
    AiExportDetailLevel.STANDARD,
    AiExportDetailLevel.FULL,
)

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
_SIGNAL_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_INSTANCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")

_TASK_DOMAIN_BY_VALUE = {
    **{task.value: AiExportDomain.PORTFOLIO for task in AiExportPortfolioTask},
    **{task.value: AiExportDomain.ASSET for task in AiExportAssetTask},
    **{task.value: AiExportDomain.FX for task in AiExportFxTask},
    **{task.value: AiExportDomain.BROKER for task in AiExportBrokerTask},
}


def _validate_code(value: str, label: str, pattern: re.Pattern[str] = _CODE_PATTERN) -> None:
    if not pattern.fullmatch(value):
        raise ValueError(f"{label} has invalid format: {value!r}")


def _freeze_json(value: Any, path: str = "value") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[{index}]") for index, item in enumerate(value))
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            frozen[key] = _freeze_json(item, f"{path}.{key}")
        return MappingProxyType(frozen)
    raise ValueError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _freeze_mapping(value: Mapping[Any, Any]) -> Mapping[Any, Any]:
    return MappingProxyType(dict(value))


def _enum_or_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


class SignalOutputMode(StrEnum):
    LATEST = "latest"
    SAMPLED = "sampled"
    FULL_WINDOW = "full_window"
    STATE_EVENT_ONLY = "state_event_only"


class SignalEligibility(StrEnum):
    ALWAYS = "always"
    VOLUME_REQUIRED = "volume_required"


class AnnotationSourceKind(StrEnum):
    PRICE = "price"
    SIGNAL_COMPONENT = "signal_component"
    CONSTANT = "constant"


class BandComponent(StrEnum):
    LOWER = "lower"
    MIDDLE = "middle"
    UPPER = "upper"


class AnnotationRequestKind(StrEnum):
    LINE_CROSSOVER = "line_crossover"
    THRESHOLD_CROSSING = "threshold_crossing"


class AnnotationDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    BOTH = "both"


class TechnicalDepth(StrEnum):
    NONE = "none"
    LATEST_STATES = "latest_states"
    LATEST_BREADTH = "latest_breadth"
    BREADTH_ONLY = "breadth_only"
    STANDARD_SUMMARY = "standard_summary"
    STANDARD = "standard"
    FULL = "full"
    SAMPLED_STANDARD = "sampled_standard"
    STANDARD_WITH_SERIES = "standard_with_series"
    LATEST_TREND_MOMENTUM_VOLATILITY = "latest_trend_momentum_volatility"
    LATEST_NEUTRAL_CONTEXT = "latest_neutral_context"
    STANDARD_WITH_SAMPLING = "standard_with_sampling"
    LATEST_DRAWDOWN_CONTEXT = "latest_drawdown_context"
    STANDARD_WITH_RECOVERY_EVENTS = "standard_with_recovery_events"
    LATEST_RATE_AND_STATES = "latest_rate_and_states"
    LATEST_EXPOSURE_AND_STATES = "latest_exposure_and_states"
    LATEST_TREND_AND_VOLATILITY = "latest_trend_and_volatility"


class RoundingStage(StrEnum):
    AFTER_SAMPLING = "after_sampling"


class EventLimitMode(StrEnum):
    RECENT_TASK_SPECIFIC = "recent_task_specific"
    CURATED_TASK_SPECIFIC = "curated_task_specific"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class SignalInstanceSpec:
    instance_id: str
    signal_code: str
    params: Mapping[str, Any]
    requested_components: tuple[str, ...]
    mode: SignalOutputMode
    eligibility: SignalEligibility = SignalEligibility.ALWAYS

    def __post_init__(self) -> None:
        _validate_code(self.instance_id, "instance_id", _INSTANCE_ID_PATTERN)
        _validate_code(self.signal_code, "signal_code", _SIGNAL_CODE_PATTERN)
        if self.signal_code != self.signal_code.upper():
            raise ValueError("signal_code must be canonical uppercase")
        if not self.requested_components:
            raise ValueError("requested_components must not be empty")
        if len(self.requested_components) != len(set(self.requested_components)):
            raise ValueError("requested_components must be unique")
        for component in self.requested_components:
            _validate_code(component, "requested component")
        object.__setattr__(self, "params", _freeze_json(self.params, "params"))
        object.__setattr__(self, "requested_components", tuple(self.requested_components))


@dataclass(frozen=True, slots=True)
class AnnotationSourceSpec:
    kind: AnnotationSourceKind
    price_field: str | None = None
    signal_instance_id: str | None = None
    component: str | None = None
    band_component: BandComponent | None = None
    constant: int | float | None = None

    def __post_init__(self) -> None:
        if self.kind == AnnotationSourceKind.PRICE:
            if self.price_field is None:
                raise ValueError("price annotation source requires price_field")
            _validate_code(self.price_field, "price_field")
            if any(value is not None for value in (self.signal_instance_id, self.component, self.band_component, self.constant)):
                raise ValueError("price annotation source cannot define signal or constant fields")
            return
        if self.kind == AnnotationSourceKind.SIGNAL_COMPONENT:
            if self.signal_instance_id is None or self.component is None:
                raise ValueError("signal annotation source requires signal_instance_id and component")
            _validate_code(self.signal_instance_id, "signal_instance_id", _INSTANCE_ID_PATTERN)
            _validate_code(self.component, "component")
            if self.price_field is not None or self.constant is not None:
                raise ValueError("signal annotation source cannot define price or constant fields")
            return
        if self.constant is None or isinstance(self.constant, bool):
            raise ValueError("constant annotation source requires a numeric constant")
        if isinstance(self.constant, float) and not math.isfinite(self.constant):
            raise ValueError("constant annotation source must be finite")
        if any(value is not None for value in (self.price_field, self.signal_instance_id, self.component, self.band_component)):
            raise ValueError("constant annotation source cannot define price or signal fields")


@dataclass(frozen=True, slots=True)
class AnnotationRequestSpec:
    key: str
    kind: AnnotationRequestKind
    attach_to_instance_id: str
    left: AnnotationSourceSpec | None = None
    right: AnnotationSourceSpec | None = None
    source: AnnotationSourceSpec | None = None
    threshold: int | float | None = None
    direction: AnnotationDirection = AnnotationDirection.BOTH
    observed_only: bool = True
    min_gap_days: int = 0

    def __post_init__(self) -> None:
        _validate_code(self.key, "annotation key")
        _validate_code(self.attach_to_instance_id, "attach_to_instance_id", _INSTANCE_ID_PATTERN)
        if self.min_gap_days < 0:
            raise ValueError("min_gap_days must be non-negative")
        if self.kind == AnnotationRequestKind.LINE_CROSSOVER:
            if self.left is None or self.right is None:
                raise ValueError("line crossover requires left and right sources")
            if self.source is not None or self.threshold is not None:
                raise ValueError("line crossover cannot define threshold fields")
            return
        if self.source is None or self.threshold is None or isinstance(self.threshold, bool):
            raise ValueError("threshold crossing requires source and numeric threshold")
        if isinstance(self.threshold, float) and not math.isfinite(self.threshold):
            raise ValueError("threshold must be finite")
        if self.left is not None or self.right is not None:
            raise ValueError("threshold crossing cannot define left or right sources")


@dataclass(frozen=True, slots=True)
class TechnicalBundleSpec:
    bundle_id: str
    detail_level: AiExportDetailLevel
    target_domain: AiExportDomain
    signals: tuple[SignalInstanceSpec, ...]
    annotations: tuple[AnnotationRequestSpec, ...]

    def __post_init__(self) -> None:
        _validate_code(self.bundle_id, "bundle_id")
        if self.target_domain not in (AiExportDomain.ASSET, AiExportDomain.FX):
            raise ValueError("technical bundles must target asset or FX inputs")
        expected_bundle_id = f"{self.target_domain.value}.{self.detail_level.value}"
        if self.bundle_id != expected_bundle_id:
            raise ValueError(f"bundle_id must be {expected_bundle_id}")
        object.__setattr__(self, "signals", tuple(self.signals))
        object.__setattr__(self, "annotations", tuple(self.annotations))
        instance_ids = [signal.instance_id for signal in self.signals]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError(f"{self.bundle_id} has duplicate signal instance IDs")
        annotation_keys = [annotation.key for annotation in self.annotations]
        if len(annotation_keys) != len(set(annotation_keys)):
            raise ValueError(f"{self.bundle_id} has duplicate annotation keys")
        available_instances = set(instance_ids)
        for annotation in self.annotations:
            if annotation.attach_to_instance_id not in available_instances:
                raise ValueError(f"{annotation.key} attaches to unknown signal instance")
            sources = (annotation.left, annotation.right, annotation.source)
            for source in sources:
                if source is not None and source.kind == AnnotationSourceKind.SIGNAL_COMPONENT and source.signal_instance_id not in available_instances:
                    raise ValueError(f"{annotation.key} references unknown signal instance")


@dataclass(frozen=True, slots=True)
class SamplingSpec:
    include_latest: bool
    include_aggregates: bool
    include_series: bool
    recent_daily_points: int
    preceding_weekly_points: int | None
    weekly_across_technical_window: bool

    def __post_init__(self) -> None:
        if self.recent_daily_points < 0:
            raise ValueError("recent_daily_points must be non-negative")
        if self.preceding_weekly_points is not None and self.preceding_weekly_points < 0:
            raise ValueError("preceding_weekly_points must be non-negative")
        if self.weekly_across_technical_window and self.preceding_weekly_points is not None:
            raise ValueError("full-window weekly sampling cannot also have a weekly point cap")


@dataclass(frozen=True, slots=True)
class PrecisionSpec:
    policy_id: str
    rounding_stage: RoundingStage

    def __post_init__(self) -> None:
        _validate_code(self.policy_id, "precision policy_id")


@dataclass(frozen=True, slots=True)
class EventLimitSpec:
    mode: EventLimitMode
    max_events: int | None
    deduplicate: bool

    def __post_init__(self) -> None:
        if self.mode == EventLimitMode.FIXED:
            if self.max_events is None or self.max_events < 1:
                raise ValueError("fixed event limit requires max_events >= 1")
        elif self.max_events is not None:
            raise ValueError("task-specific event limit cannot define a generic max_events")


@dataclass(frozen=True, slots=True)
class CardinalitySpec:
    complete_aggregates: bool
    all_positions: bool
    all_entities: bool
    all_contributions: bool
    requires_compact_selection: bool


@dataclass(frozen=True, slots=True)
class CompactSelectionSpec:
    rule: str
    entity_limit: int
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        _validate_code(self.rule, "compact selection rule")
        if self.entity_limit < 1:
            raise ValueError("compact selection entity_limit must be positive")
        object.__setattr__(self, "parameters", _freeze_json(self.parameters, "selection parameters"))


@dataclass(frozen=True, slots=True)
class TechnicalDetailSpec:
    detail_level: AiExportDetailLevel
    depth: TechnicalDepth
    bundle: TechnicalBundleSpec | None
    event_limit_override: int | None = None

    def __post_init__(self) -> None:
        if self.depth == TechnicalDepth.NONE:
            if self.bundle is not None:
                raise ValueError("technical depth none cannot define a bundle")
        else:
            if self.bundle is None:
                raise ValueError("non-empty technical depth requires a bundle")
            if self.bundle.detail_level != self.detail_level:
                raise ValueError("technical bundle detail must match task detail")
        if self.event_limit_override is not None and self.event_limit_override < 1:
            raise ValueError("event_limit_override must be positive")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    domain: AiExportDomain
    task: AiExportTask
    required_sections: tuple[str, ...]
    optional_sections: tuple[str, ...]
    applicability_code: str
    frontend_response_contract_id: str
    frontend_response_contract_version: int
    supports_user_notes: bool
    supports_web_research: bool
    compact_selection: CompactSelectionSpec
    technical_by_detail: Mapping[AiExportDetailLevel, TechnicalDetailSpec]

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_sections", tuple(self.required_sections))
        object.__setattr__(self, "optional_sections", tuple(self.optional_sections))
        object.__setattr__(self, "technical_by_detail", _freeze_mapping(self.technical_by_detail))
        if not self.required_sections:
            raise ValueError("task spec requires at least one required section")
        if len(self.required_sections) != len(set(self.required_sections)):
            raise ValueError("required_sections must be unique")
        if len(self.optional_sections) != len(set(self.optional_sections)):
            raise ValueError("optional_sections must be unique")
        if set(self.required_sections) & set(self.optional_sections):
            raise ValueError("required_sections and optional_sections must not overlap")
        for section in (*self.required_sections, *self.optional_sections):
            _validate_code(section, "section")
        _validate_code(self.applicability_code, "applicability_code")
        expected_contract_id = f"{self.domain.value}.{self.task.value}"
        if self.frontend_response_contract_id != expected_contract_id:
            raise ValueError(f"frontend_response_contract_id must be {expected_contract_id}")
        if self.frontend_response_contract_version != FRONTEND_RESPONSE_CONTRACT_VERSION:
            raise ValueError("frontend response contract version must be 1")
        if tuple(self.technical_by_detail) != DETAIL_LEVEL_ORDER:
            raise ValueError("technical_by_detail must declare compact, standard, and full in stable order")
        if any(detail != spec.detail_level for detail, spec in self.technical_by_detail.items()):
            raise ValueError("technical detail key and payload must match")
        if self.domain in (AiExportDomain.ASSET, AiExportDomain.FX):
            if self.compact_selection.rule != "single_entity" or self.compact_selection.entity_limit != 1:
                raise ValueError("single-entity task compact selection must be single_entity with limit 1")


@dataclass(frozen=True, slots=True)
class DetailOverlay:
    detail_level: AiExportDetailLevel
    cardinality: CardinalitySpec
    sampling: SamplingSpec
    precision: PrecisionSpec
    event_limits: EventLimitSpec


@dataclass(frozen=True, slots=True)
class ResolvedProfile:
    task_spec: TaskSpec
    detail_overlay: DetailOverlay
    profile_id: str
    profile_version: int = PROFILE_VERSION
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        expected_profile_id = f"{self.domain.value}.{self.task.value}.{self.detail_level.value}"
        if self.profile_id != expected_profile_id:
            raise ValueError(f"profile_id must be {expected_profile_id}")
        if self.profile_version != PROFILE_VERSION:
            raise ValueError("profile_version must be 1")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("schema_version must be 1")
        self.to_catalog_entry()

    @property
    def domain(self) -> AiExportDomain:
        return self.task_spec.domain

    @property
    def task(self) -> AiExportTask:
        return self.task_spec.task

    @property
    def detail_level(self) -> AiExportDetailLevel:
        return self.detail_overlay.detail_level

    @property
    def frontend_response_contract_id(self) -> str:
        return self.task_spec.frontend_response_contract_id

    @property
    def frontend_response_contract_version(self) -> int:
        return self.task_spec.frontend_response_contract_version

    @property
    def applicability_code(self) -> str:
        return self.task_spec.applicability_code

    @property
    def supports_user_notes(self) -> bool:
        return self.task_spec.supports_user_notes

    @property
    def supports_web_research(self) -> bool:
        return self.task_spec.supports_web_research

    @property
    def required_sections(self) -> tuple[str, ...]:
        return self.task_spec.required_sections

    @property
    def optional_sections(self) -> tuple[str, ...]:
        return self.task_spec.optional_sections

    @property
    def compact_selection(self) -> CompactSelectionSpec:
        return self.task_spec.compact_selection

    @property
    def selection(self) -> CompactSelectionSpec | None:
        if self.detail_level == AiExportDetailLevel.COMPACT:
            return self.task_spec.compact_selection
        return None

    @property
    def technical(self) -> TechnicalDetailSpec:
        return self.task_spec.technical_by_detail[self.detail_level]

    @property
    def technical_bundle(self) -> TechnicalBundleSpec | None:
        return self.technical.bundle

    @property
    def technical_depth(self) -> TechnicalDepth:
        return self.technical.depth

    def to_catalog_entry(self) -> AiExportCatalogEntry:
        return AiExportCatalogEntry(
            domain=self.domain,
            task=self.task,
            detail_level=self.detail_level,
            profile_id=self.profile_id,
            profile_version=self.profile_version,
            frontend_response_contract_id=self.frontend_response_contract_id,
            frontend_response_contract_version=self.frontend_response_contract_version,
            applicability_code=self.applicability_code,
            supports_user_notes=self.supports_user_notes,
            supports_web_research=self.supports_web_research,
        )


@dataclass(frozen=True, slots=True)
class UnsupportedProfileRequest:
    domain: str
    task: str
    detail_level: str


class UnsupportedAiExportProfileError(LookupError):
    """Raised when an exact domain/task/detail profile is not allow-listed."""

    def __init__(self, request: UnsupportedProfileRequest, supported_profile_ids: Sequence[str]) -> None:
        self.request = request
        self.supported_profile_ids = tuple(supported_profile_ids)
        requested_id = f"{request.domain}.{request.task}.{request.detail_level}"
        super().__init__(f"Unsupported AI Export profile: {requested_id}")


UnsupportedProfileError = UnsupportedAiExportProfileError


def profile_request(domain: object, task: object, detail_level: object) -> UnsupportedProfileRequest:
    return UnsupportedProfileRequest(
        domain=_enum_or_value(domain),
        task=_enum_or_value(task),
        detail_level=_enum_or_value(detail_level),
    )


def validate_task_specs(task_specs: Sequence[TaskSpec]) -> None:
    if len(task_specs) != EXPECTED_TASK_COUNT:
        raise ValueError(f"AI Export catalog requires exactly {EXPECTED_TASK_COUNT} task specs")
    keys = [(spec.domain, spec.task) for spec in task_specs]
    if len(keys) != len(set(keys)):
        raise ValueError("AI Export task keys must be unique")
    contracts = [spec.frontend_response_contract_id for spec in task_specs]
    if len(contracts) != len(set(contracts)):
        raise ValueError("AI Export response contract IDs must be unique")
    if {spec.task for spec in task_specs} != set(AiExportTask):
        raise ValueError("AI Export task specs must cover the frozen 19-task schema")
    for spec in task_specs:
        if _TASK_DOMAIN_BY_VALUE.get(spec.task.value) != spec.domain:
            raise ValueError(f"task {spec.task.value} does not belong to domain {spec.domain.value}")
        if tuple(spec.technical_by_detail) != DETAIL_LEVEL_ORDER:
            raise ValueError(f"task {spec.task.value} does not declare all detail levels")


def validate_detail_overlays(detail_overlays: Sequence[DetailOverlay]) -> None:
    if len(detail_overlays) != len(DETAIL_LEVEL_ORDER):
        raise ValueError("AI Export catalog requires exactly three detail overlays")
    if tuple(overlay.detail_level for overlay in detail_overlays) != DETAIL_LEVEL_ORDER:
        raise ValueError("detail overlays must use compact, standard, full stable order")
    if len({overlay.detail_level for overlay in detail_overlays}) != len(DETAIL_LEVEL_ORDER):
        raise ValueError("detail overlays must be unique")


def build_resolved_profiles(task_specs: Sequence[TaskSpec], detail_overlays: Sequence[DetailOverlay]) -> tuple[ResolvedProfile, ...]:
    validate_task_specs(task_specs)
    validate_detail_overlays(detail_overlays)
    profiles = tuple(
        ResolvedProfile(
            task_spec=task_spec,
            detail_overlay=overlay,
            profile_id=f"{task_spec.domain.value}.{task_spec.task.value}.{overlay.detail_level.value}",
        )
        for task_spec in task_specs
        for overlay in detail_overlays
    )
    if len(profiles) != EXPECTED_PROFILE_COUNT:
        raise ValueError(f"AI Export catalog requires exactly {EXPECTED_PROFILE_COUNT} resolved profiles")
    keys = [(profile.domain, profile.task, profile.detail_level) for profile in profiles]
    if len(keys) != len(set(keys)):
        raise ValueError("resolved AI Export profile keys must be unique")
    profile_ids = [profile.profile_id for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("resolved AI Export profile IDs must be unique")
    task_detail_counts: dict[tuple[AiExportDomain, AiExportTask], set[AiExportDetailLevel]] = {}
    for profile in profiles:
        task_detail_counts.setdefault((profile.domain, profile.task), set()).add(profile.detail_level)
        expected_contract_id = f"{profile.domain.value}.{profile.task.value}"
        if profile.frontend_response_contract_id != expected_contract_id:
            raise ValueError("resolved profile response contract identity mismatch")
        profile.to_catalog_entry()
    if any(details != set(DETAIL_LEVEL_ORDER) for details in task_detail_counts.values()):
        raise ValueError("every AI Export task must resolve all three detail levels")
    return profiles


AiExportSignalInstanceSpec = SignalInstanceSpec
AiExportAnnotationSourceSpec = AnnotationSourceSpec
AiExportAnnotationRequestSpec = AnnotationRequestSpec
AiExportTechnicalBundleSpec = TechnicalBundleSpec
AiExportTaskSpec = TaskSpec
AiExportDetailOverlay = DetailOverlay
AiExportResolvedProfile = ResolvedProfile
