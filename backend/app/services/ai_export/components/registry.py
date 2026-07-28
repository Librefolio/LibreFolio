"""Immutable, validated registry of `ComponentSpec` declarations.

`ComponentRegistry` validates unique component IDs, that every declared dependency
references a registered component, and that the dependency graph is acyclic. It
also exposes a deterministic canonical registration order used by dataset
composition (e.g. for `*.all_data` union ordering).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType

from backend.app.services.ai_export.components.spec import ComponentSpec


class ComponentRegistryError(ValueError):
    """Base error for invalid `ComponentRegistry` construction or lookup."""


class DuplicateComponentIdError(ComponentRegistryError):
    """Raised when two `ComponentSpec` entries share the same `component_id`."""


class UnknownComponentError(ComponentRegistryError):
    """Raised when a component_id is looked up or referenced but not registered."""


class ComponentDependencyCycleError(ComponentRegistryError):
    """Raised when the component dependency graph contains a cycle."""

    def __init__(self, cycle: tuple[str, ...]):
        self.cycle = cycle
        super().__init__(f"component dependency cycle detected: {' -> '.join(cycle)}")


class ComponentRegistry:
    """Immutable collection of `ComponentSpec`, validated as a whole (unique IDs, resolvable dependencies, no cycles)."""

    def __init__(self, specs: Iterable[ComponentSpec]):
        ordered: dict[str, ComponentSpec] = {}
        for spec in specs:
            if not isinstance(spec, ComponentSpec):
                raise ComponentRegistryError(f"expected ComponentSpec, got {type(spec).__name__}")
            if spec.component_id in ordered:
                raise DuplicateComponentIdError(f"duplicate component_id: {spec.component_id!r}")
            ordered[spec.component_id] = spec
        for spec in ordered.values():
            for dep_id in spec.dependencies:
                if dep_id not in ordered:
                    raise UnknownComponentError(f"{spec.component_id} depends on unknown component {dep_id!r}")
        self._specs: Mapping[str, ComponentSpec] = MappingProxyType(ordered)
        self._canonical_order: tuple[str, ...] = tuple(ordered.keys())
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        white, gray, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(self._specs, white)
        path: list[str] = []

        def visit(node: str) -> None:
            color[node] = gray
            path.append(node)
            for dep in self._specs[node].dependencies:
                if color[dep] == gray:
                    cycle_start = path.index(dep)
                    raise ComponentDependencyCycleError((*path[cycle_start:], dep))
                if color[dep] == white:
                    visit(dep)
            path.pop()
            color[node] = black

        for node in tuple(self._specs):
            if color[node] == white:
                visit(node)

    def __contains__(self, component_id: str) -> bool:
        return component_id in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[ComponentSpec]:
        return iter(self._specs.values())

    def get(self, component_id: str) -> ComponentSpec:
        try:
            return self._specs[component_id]
        except KeyError:
            raise UnknownComponentError(f"unknown component_id: {component_id!r}") from None

    @property
    def canonical_order(self) -> tuple[str, ...]:
        """Component IDs in deterministic registration order (used e.g. by `*.all_data` union ordering)."""
        return self._canonical_order

    def transitive_dependencies(self, component_id: str) -> tuple[str, ...]:
        """Dependency IDs (transitively) in dependency-first topological order, excluding `component_id` itself."""
        self.get(component_id)  # raises UnknownComponentError if absent
        visited: set[str] = set()
        order: list[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            for dep in self._specs[node].dependencies:
                visit(dep)
            if node != component_id:
                order.append(node)

        visit(component_id)
        return tuple(order)
