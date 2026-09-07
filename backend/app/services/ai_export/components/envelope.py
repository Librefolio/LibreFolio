"""Public-ready section envelope for a single built AI Export component.

Every component output MUST pass through `build_envelope` before being exposed as
a section: it enforces Pydantic validation against the component's declared
`output_model` and guarantees the resulting payload is JSON-safe (via pydantic's
`JsonValue`), so no `Any` leakage reaches callers of the runtime.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, JsonValue

from backend.app.services.ai_export.components.spec import ComponentSpec


class ComponentPayloadValidationError(ValueError):
    """Raised when a builder's raw output fails validation against its output_model."""


class SectionEnvelope(BaseModel):
    """Immutable, JSON-safe section envelope for a single built component.

    `component_id`/`component_version` identify the builder/logic that produced the
    payload; `schema_id`/`schema_version` identify the payload shape, which may
    evolve independently of the builder implementation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str
    component_version: int
    schema_id: str
    schema_version: int
    payload: dict[str, JsonValue]


def build_envelope(spec: ComponentSpec, raw: BaseModel | Mapping[str, object]) -> SectionEnvelope:
    """Validates `raw` against `spec.output_model` and wraps it in a `SectionEnvelope`.

    Accepts either an already-constructed instance of `spec.output_model` or a plain
    mapping to be validated against it. Raises `ComponentPayloadValidationError` on
    any other type or on validation failure.
    """
    if isinstance(raw, spec.output_model):
        validated = raw
    elif isinstance(raw, Mapping):
        try:
            validated = spec.output_model.model_validate(raw)
        except Exception as exc:
            raise ComponentPayloadValidationError(f"{spec.component_id}: output failed validation against {spec.output_model.__name__}: {exc}") from exc
    else:
        raise ComponentPayloadValidationError(f"{spec.component_id}: builder returned unsupported type {type(raw).__name__}")
    payload = validated.model_dump(mode="json")
    if not isinstance(payload, dict):
        raise ComponentPayloadValidationError(f"{spec.component_id}: output_model must serialize to a JSON object")
    return SectionEnvelope(
        component_id=spec.component_id,
        component_version=spec.version,
        schema_id=spec.schema_id or spec.component_id,
        schema_version=spec.schema_version,
        payload=payload,
    )
