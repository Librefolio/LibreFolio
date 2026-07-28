"""AI Export component runtime foundations (Phase 0 refinement, workstream D)."""

from __future__ import annotations

from backend.app.services.ai_export.components.catalog import (
    ALL_FOUNDATION_COMPONENTS,
    ComponentNotImplementedError,
    FoundationComponentPayload,
    build_component_registry,
)
from backend.app.services.ai_export.components.envelope import (
    ComponentPayloadValidationError,
    SectionEnvelope,
    build_envelope,
)
from backend.app.services.ai_export.components.registry import (
    ComponentDependencyCycleError,
    ComponentRegistry,
    ComponentRegistryError,
    DuplicateComponentIdError,
    UnknownComponentError,
)
from backend.app.services.ai_export.components.spec import (
    ComponentBuilder,
    ComponentSpec,
    ComponentSpecError,
)
from backend.app.services.ai_export.components.types import (
    ALL_DETAIL_LEVELS,
    DetailLevel,
    Domain,
    PeriodBehavior,
    TemporalAggregatorSpec,
)

__all__ = [
    "ALL_DETAIL_LEVELS",
    "ALL_FOUNDATION_COMPONENTS",
    "ComponentBuilder",
    "ComponentDependencyCycleError",
    "ComponentNotImplementedError",
    "ComponentPayloadValidationError",
    "ComponentRegistry",
    "ComponentRegistryError",
    "ComponentSpec",
    "ComponentSpecError",
    "DetailLevel",
    "Domain",
    "DuplicateComponentIdError",
    "FoundationComponentPayload",
    "PeriodBehavior",
    "SectionEnvelope",
    "TemporalAggregatorSpec",
    "UnknownComponentError",
    "build_component_registry",
    "build_envelope",
]
