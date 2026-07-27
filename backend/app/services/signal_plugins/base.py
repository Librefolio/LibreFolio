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
    SignalWarmupRequirement,
)

_SIGNAL_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SEMANTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


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
        if len(output_semantic_ids) != len(set(output_semantic_ids)):
            raise ValueError("output semantic_ids must not contain duplicates")
        if cls.semantic_id in output_semantic_ids:
            raise ValueError("signal and output semantic_ids must be unique")
        if not issubclass(cls.params_model, BaseModel):
            raise TypeError("params_model must be a Pydantic BaseModel subclass")
        if cls.params_model.model_config.get("extra") != "forbid":
            raise ValueError("signal params_model must use ConfigDict(extra='forbid')")
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
