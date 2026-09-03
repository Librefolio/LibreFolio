"""Immutable `ComponentSpec` contract for the AI Export component runtime.

A `ComponentSpec` is the smallest declarative unit of the new catalog/component
runtime (Phase 0 AI Export refinement, workstream D): it pairs a stable
identity/version with a validated Pydantic output model, its dependency graph and
period/aggregation metadata, and a builder callable that produces the raw payload.

See `backend.app.services.ai_export.components.registry.ComponentRegistry` for the
collection-level validation (uniqueness, dependency existence, cycle detection) and
`backend.app.services.ai_export.dependencies.BuildContext` for the request-scoped
resolver/memoization seam that actually invokes builders.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel

from backend.app.services.ai_export.components.types import Domain, PeriodBehavior, TemporalAggregatorSpec

from .._int_validation import require_positive_int

if TYPE_CHECKING:
    from backend.app.services.ai_export.components.envelope import SectionEnvelope
    from backend.app.services.ai_export.dependencies import BuildContext

_COMPONENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class ComponentSpecError(ValueError):
    """Raised when a `ComponentSpec` declaration is internally inconsistent."""


@runtime_checkable
class ComponentBuilder(Protocol):
    """Callable contract every component builder must satisfy.

    Receives the request-scoped `BuildContext` and the already-resolved envelopes
    of this component's declared dependencies (keyed by dependency component_id),
    and returns either a validated instance of the component's `output_model` or a
    plain mapping to be validated against it. May be a regular function or a
    coroutine function; `BuildContext` awaits the result transparently either way.
    """

    def __call__(
        self,
        context: BuildContext,
        dependencies: Mapping[str, SectionEnvelope],
    ) -> BaseModel | Mapping[str, object] | Awaitable[BaseModel | Mapping[str, object]]: ...


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    """Immutable declaration of a single AI Export component.

    - `component_id`/`version` identify the builder/logic (dotted lowercase id,
      e.g. `"portfolio.summary"`).
    - `schema_id`/`schema_version` identify the payload shape and may evolve
      independently of the builder implementation; they default to
      `component_id`/1 when not overridden.
    - `domains` lists every domain this component is applicable to.
    - `dependencies` lists other component IDs that must be built first; the
      `BuildContext` resolves and memoizes them before invoking `builder`.
    - `period_behavior`/`aggregator` are metadata only (see `PeriodBehavior`).
    """

    component_id: str
    version: int
    domains: frozenset[Domain]
    output_model: type[BaseModel]
    builder: ComponentBuilder
    dependencies: tuple[str, ...] = ()
    period_behavior: PeriodBehavior = PeriodBehavior.NONE
    aggregator: TemporalAggregatorSpec | None = None
    schema_id: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:  # noqa: C901 — flat field-validation chain
        if not _COMPONENT_ID_PATTERN.fullmatch(self.component_id):
            raise ComponentSpecError(f"component_id has invalid format: {self.component_id!r}")
        require_positive_int(self.version, "version", owner_id=self.component_id, error_cls=ComponentSpecError)
        domains = frozenset(self.domains)
        if not domains:
            raise ComponentSpecError(f"{self.component_id}: domains must not be empty")
        for domain in domains:
            if not isinstance(domain, Domain):
                raise ComponentSpecError(f"{self.component_id}: domains must contain only Domain members, got {domain!r}")
        object.__setattr__(self, "domains", domains)
        if not isinstance(self.output_model, type) or not issubclass(self.output_model, BaseModel):
            raise ComponentSpecError(f"{self.component_id}: output_model must be a pydantic BaseModel subclass")
        if not callable(self.builder):
            raise ComponentSpecError(f"{self.component_id}: builder must be callable")
        deps = tuple(self.dependencies)
        if len(deps) != len(set(deps)):
            raise ComponentSpecError(f"{self.component_id}: dependencies must be unique")
        if self.component_id in deps:
            raise ComponentSpecError(f"{self.component_id}: cannot depend on itself")
        for dep_id in deps:
            if not _COMPONENT_ID_PATTERN.fullmatch(dep_id):
                raise ComponentSpecError(f"{self.component_id}: dependency id has invalid format: {dep_id!r}")
        object.__setattr__(self, "dependencies", deps)
        if not isinstance(self.period_behavior, PeriodBehavior):
            raise ComponentSpecError(f"{self.component_id}: period_behavior must be a PeriodBehavior member, got {self.period_behavior!r}")
        if self.period_behavior == PeriodBehavior.AGGREGATED and self.aggregator is None:
            raise ComponentSpecError(f"{self.component_id}: period_behavior=AGGREGATED requires an aggregator")
        if self.period_behavior != PeriodBehavior.AGGREGATED and self.aggregator is not None:
            raise ComponentSpecError(f"{self.component_id}: aggregator requires period_behavior=AGGREGATED")
        object.__setattr__(self, "schema_id", self.schema_id or self.component_id)
        require_positive_int(self.schema_version, "schema_version", owner_id=self.component_id, error_cls=ComponentSpecError)
