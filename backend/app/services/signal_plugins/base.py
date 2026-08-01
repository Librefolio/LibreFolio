"""Library-agnostic abstract contract for technical signal plugins."""

from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Optional

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from backend.app.schemas.signals import (
    SignalAiDescription,
    SignalAiEventDescription,
    SignalAiExportTemporalRule,
    SignalAiOutputDescription,
    SignalAvailabilityReason,
    SignalCatalogDefinition,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalOutputSpec,
    SignalPricePoint,
    SignalTemporalClass,
    SignalWarmupRequirement,
)

_SIGNAL_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SEMANTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


def _json_exact_match(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_json_exact_match(actual[key], expected[key]) for key in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_json_exact_match(actual_item, expected_item) for actual_item, expected_item in zip(actual, expected, strict=True))
    return actual == expected


class SignalUnavailableError(ValueError):
    """Report a mathematically unavailable result without treating it as failure."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: SignalAvailabilityReason,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}


class SignalPlugin(ABC):
    """Complete implementation boundary for one technical signal."""

    signal_code: ClassVar[str]
    implementation_version: ClassVar[str]
    category: ClassVar[SignalCategory]
    display_name_key: ClassVar[str]
    description_key: ClassVar[str]
    semantic_id: ClassVar[str]
    semantic_description: ClassVar[str]
    icon: ClassVar[str]
    docs_path: ClassVar[Optional[str]] = None
    params_model: ClassVar[type[BaseModel]]
    input_requirements: ClassVar[SignalInputRequirements]
    output_specs: ClassVar[tuple[SignalOutputSpec, ...]]
    compatible_domains: ClassVar[tuple[SignalDomain, ...]]
    annotation_capabilities: ClassVar[tuple[str, ...]] = ()
    ai_export_temporal_rules: ClassVar[tuple[SignalAiExportTemporalRule, ...]] = ()

    @classmethod
    def validate_params(cls, params: Mapping[str, object] | BaseModel) -> BaseModel:
        """Validate and normalize request params with the plugin-owned model."""
        if isinstance(params, cls.params_model):
            return params
        if isinstance(params, BaseModel):
            params = params.model_dump()
        return cls.params_model.model_validate(params)

    @classmethod
    def default_params(cls) -> dict[str, object]:
        """Return JSON-safe defaults without requiring every param to have one."""
        defaults = {field.serialization_alias or field.alias or name: field.get_default(call_default_factory=True) for name, field in cls.params_model.model_fields.items() if not field.is_required()}
        return to_jsonable_python(defaults)

    @classmethod
    def catalog_definition(cls) -> SignalCatalogDefinition:
        """Build the static, schema-driven catalog entry for this plugin."""
        return SignalCatalogDefinition(
            signal_code=cls.signal_code,
            implementation_version=cls.implementation_version,
            category=cls.category,
            display_name_key=cls.display_name_key,
            description_key=cls.description_key,
            semantic_id=cls.semantic_id,
            semantic_description=cls.semantic_description,
            icon=cls.icon,
            docs_path=cls.docs_path,
            params_schema=cls.params_model.model_json_schema(),
            default_params=cls.default_params(),
            input_requirements=cls.input_requirements.model_copy(deep=True),
            output_specs=[spec.model_copy(deep=True) for spec in cls.output_specs],
            compatible_domains=list(cls.compatible_domains),
            annotation_capabilities=list(cls.annotation_capabilities),
            ai_description=cls.describe_for_ai(),
            ai_events=list(cls.describe_events_for_ai()),
            ai_export_temporal_rules=[rule.model_copy(deep=True) for rule in cls.ai_export_temporal_rules],
        )

    @classmethod
    def resolve_ai_export_temporal_class(
        cls,
        params: Mapping[str, object] | BaseModel,
    ) -> SignalTemporalClass:
        """Resolve one plugin-owned temporal class from normalized parameters."""
        normalized_params = cls.validate_params(params).model_dump(mode="json", by_alias=True)
        matches = [rule for rule in cls.ai_export_temporal_rules if all(key in normalized_params and _json_exact_match(normalized_params[key], value) for key, value in rule.parameter_match.items())]
        if len(matches) != 1:
            raise ValueError(f"{cls.signal_code} AI Export temporal resolution requires exactly one matching rule; " f"found {len(matches)} for normalized params {normalized_params}")
        return matches[0].temporal_class

    @classmethod
    def describe_for_ai(cls) -> SignalAiDescription:
        """AI-consumable description of this signal.

        Default derived purely from existing catalog metadata
        (`semantic_id`/`semantic_description`/`category`/`output_specs`) so
        plugins need zero boilerplate. Override only when the AI-facing
        description should diverge from the catalog's own public metadata.
        """
        return SignalAiDescription(
            signal_code=cls.signal_code,
            semantic_id=cls.semantic_id,
            semantic_description=cls.semantic_description,
            category=cls.category,
            outputs=tuple(
                SignalAiOutputDescription(
                    key=spec.key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                )
                for spec in cls.output_specs
            ),
        )

    @classmethod
    def describe_events_for_ai(cls) -> tuple[SignalAiEventDescription, ...]:
        """AI-consumable description of event types this plugin consumes.

        Default derives one entry per declared `event_types`, falling back
        to the signal's own `semantic_description` when no per-event
        signal_description is defined. Returns an empty tuple when the
        plugin does not consume events (the common case today — no current
        plugin declares `requires_events=True`). Override for plugins that
        need per-event-type descriptions or non-default deduplication.
        """
        if not cls.input_requirements.requires_events:
            return ()
        return tuple(
            SignalAiEventDescription(
                event_type=event_type,
                semantic_description=cls.semantic_description,
            )
            for event_type in cls.input_requirements.event_types
        )

    @classmethod
    def validate_input(
        cls,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> None:
        """Optional plugin-owned semantic input validation.

        Runs after generic coverage/warmup/availability resolution and
        before `compute()`. Default is a no-op. Override to reject inputs
        the plugin cannot honor despite generic coverage passing (e.g.
        volume that is structurally present but semantically unusable).

        Raise `SignalUnavailableError` (preferred — reported as
        `SignalStatus.UNAVAILABLE`) or `ValueError`/`ValidationError`
        (reported as `SignalStatus.FAILED`) to reject. Failures here are
        isolated per-signal by `SignalService` and never block sibling
        signals in the same batch.
        """
        return None

    @classmethod
    def validate_output(
        cls,
        computation: SignalComputation,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> None:
        """Optional plugin-owned semantic output validation.

        Runs alongside the central output contract validation
        (`SignalService._validate_plugin_output`), after `compute()`.
        Default is a no-op. Same exception-handling contract as
        `validate_input`.
        """
        return None

    @staticmethod
    def validate_meaningful_volume_input(
        price_points: Sequence[SignalPricePoint],
        *,
        minimum_coverage: float,
    ) -> None:
        """Shared structural volume validation for plugins that declare
        `requires_meaningful_volume=True` (MFI, OBV today).

        Complements — does not replace — the semantic gate SignalService
        enforces centrally via `resolve_signal_availability` (comparing
        `context.source_capability.supports_meaningful_volume` against
        `input_requirements.requires_meaningful_volume`, before `validate_input`
        is even called). This helper instead checks structural usability of
        the already-selected points:

        - non-empty input,
        - strictly increasing, unique dates (defense in depth — the full
          series is already validated on construction, but selection logic
          could change),
        - every present volume value is non-negative (finiteness is already
          enforced by the `SignalDecimal` schema type),
        - sufficient fraction of *directly observed* (non-backward-filled)
          non-null volume, using the plugin's own `minimum_coverage` as the
          threshold. Backward-filled volume carries a stale value forward
          and must not count as fresh evidence for a volume-flow indicator.

        Raises `SignalUnavailableError` so the signal is reported
        `UNAVAILABLE` rather than `FAILED`.
        """
        if not price_points:
            raise SignalUnavailableError(
                "no price points available for volume validation",
                reason_code=SignalAvailabilityReason.INSUFFICIENT_HISTORY,
            )
        previous_date = None
        observed_non_null = 0
        for point in price_points:
            if previous_date is not None and point.date <= previous_date:
                raise SignalUnavailableError(
                    "price points must have strictly increasing, unique dates",
                    reason_code=SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
                )
            previous_date = point.date
            if point.volume is None:
                continue
            if point.volume < 0:
                raise SignalUnavailableError(
                    "volume must be non-negative",
                    reason_code=SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
                    details={"date": point.date.isoformat()},
                )
            if point.backward_fill_info is None:
                observed_non_null += 1
        observed_ratio = observed_non_null / len(price_points)
        if observed_ratio < minimum_coverage:
            raise SignalUnavailableError(
                "insufficient directly observed volume coverage",
                reason_code=SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
                details={
                    "observed_ratio": observed_ratio,
                    "minimum_coverage": minimum_coverage,
                },
            )

    @classmethod
    def validate_definition(cls) -> None:
        """Reject incomplete or unsafe plugin declarations at registration."""
        if cls is SignalPlugin or inspect.isabstract(cls):
            raise TypeError("SignalPluginRegistry accepts concrete SignalPlugin subclasses only")
        required_attributes = (
            "signal_code",
            "implementation_version",
            "category",
            "display_name_key",
            "description_key",
            "semantic_id",
            "semantic_description",
            "icon",
            "params_model",
            "input_requirements",
            "output_specs",
            "compatible_domains",
        )
        missing = [attribute for attribute in required_attributes if not hasattr(cls, attribute)]
        if missing:
            raise ValueError(f"signal plugin is missing required attributes: {', '.join(missing)}")
        if not isinstance(cls.signal_code, str) or cls.signal_code != cls.signal_code.strip().upper() or not _SIGNAL_CODE_PATTERN.fullmatch(cls.signal_code):
            raise ValueError("signal_code must be canonical uppercase letters, numbers, and underscores")
        if not isinstance(cls.semantic_id, str) or not _SEMANTIC_ID_PATTERN.fullmatch(cls.semantic_id):
            raise ValueError("semantic_id must be canonical lower-case letters, numbers, dots, hyphens, and underscores")
        if not isinstance(cls.semantic_description, str) or not cls.semantic_description.strip():
            raise ValueError("semantic_description must be a non-empty string")
        output_semantic_ids = [spec.semantic_id for spec in cls.output_specs]
        implicit_aggregation = [spec.key for spec in cls.output_specs if "aggregation_profile" not in spec.model_fields_set]
        if implicit_aggregation:
            raise ValueError("signal output specs must declare aggregation_profile explicitly: " + ", ".join(implicit_aggregation))
        if len(output_semantic_ids) != len(set(output_semantic_ids)):
            raise ValueError("output semantic_ids must not contain duplicates")
        if cls.semantic_id in output_semantic_ids:
            raise ValueError("signal and output semantic_ids must be unique")
        if not issubclass(cls.params_model, BaseModel):
            raise TypeError("params_model must be a Pydantic BaseModel subclass")
        if cls.params_model.model_config.get("extra") != "forbid":
            raise ValueError("signal params_model must use ConfigDict(extra='forbid')")
        if not isinstance(cls.ai_export_temporal_rules, tuple):
            raise TypeError("ai_export_temporal_rules must be a tuple")
        if not all(isinstance(rule, SignalAiExportTemporalRule) for rule in cls.ai_export_temporal_rules):
            raise TypeError("ai_export_temporal_rules must contain SignalAiExportTemporalRule instances")
        normalized_param_keys = {field.serialization_alias or field.alias or name for name, field in cls.params_model.model_fields.items()}
        for index, rule in enumerate(cls.ai_export_temporal_rules):
            unknown_keys = set(rule.parameter_match) - normalized_param_keys
            if unknown_keys:
                raise ValueError(f"ai_export_temporal_rules[{index}] references unknown normalized params: " + ", ".join(sorted(unknown_keys)))
        for left_index, left_rule in enumerate(cls.ai_export_temporal_rules):
            for right_index, right_rule in enumerate(
                cls.ai_export_temporal_rules[left_index + 1 :],
                start=left_index + 1,
            ):
                if left_rule == right_rule:
                    raise ValueError("ai_export_temporal_rules must not contain duplicate rules")
                shared_keys = set(left_rule.parameter_match) & set(right_rule.parameter_match)
                if all(_json_exact_match(left_rule.parameter_match[key], right_rule.parameter_match[key]) for key in shared_keys):
                    raise ValueError("ai_export_temporal_rules contains ambiguous rules " f"at indexes {left_index} and {right_index}")
        comparison_asset_param = cls.input_requirements.comparison_asset_param
        if comparison_asset_param is not None and comparison_asset_param not in cls.params_model.model_fields:
            raise ValueError("comparison_asset_param must reference a declared plugin parameter")
        try:
            inspect.signature(cls).bind()
        except TypeError as exc:
            raise TypeError("signal plugins must be instantiable without arguments") from exc
        cls.catalog_definition()

    @classmethod
    @abstractmethod
    def warmup_requirement(
        cls,
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        """Return parameter-aware minimum and stabilization history."""

    @abstractmethod
    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        """Compute and normalize output using the plugin-owned implementation."""


__all__ = ["SignalPlugin", "SignalUnavailableError"]
