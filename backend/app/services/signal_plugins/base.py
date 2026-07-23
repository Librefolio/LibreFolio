"""Library-agnostic abstract contract for technical signal plugins."""

from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import ClassVar, Optional

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from backend.app.schemas.signals import (
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


class SignalPlugin(ABC):
    """Complete implementation boundary for one technical signal."""

    signal_code: ClassVar[str]
    implementation_version: ClassVar[str]
    category: ClassVar[SignalCategory]
    display_name_key: ClassVar[str]
    description_key: ClassVar[str]
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
        if not issubclass(cls.params_model, BaseModel):
            raise TypeError("params_model must be a Pydantic BaseModel subclass")
        if cls.params_model.model_config.get("extra") != "forbid":
            raise ValueError("signal params_model must use ConfigDict(extra='forbid')")
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


__all__ = ["SignalPlugin"]
