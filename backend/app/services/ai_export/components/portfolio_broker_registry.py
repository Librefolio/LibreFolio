"""Portfolio/Broker domain fragment: real `ComponentRegistry`/`DatasetRegistry`/
`AnalysisRegistry` builders wiring the real Portfolio/Broker component waves in
place of their frozen `components.catalog` placeholders.

This module is a **domain integration gate**, not the central catalog wiring: it
deliberately does **not** edit `backend.app.services.ai_export.components.catalog`
(that file is owned by the later serial "component-registry-integration" gate that
cuts over every domain at once). Instead it builds a *local* real
`ComponentRegistry` fragment - substituting only the 39 Portfolio/Broker
`component_id`s with their real implementations from `portfolio_financial`,
`broker_financial` and `portfolio_broker_technical`, while every other
`component_id` (Asset/FX and anything else the frozen catalog declares) keeps its
untouched fail-closed placeholder from `components.catalog.ALL_FOUNDATION_COMPONENTS`.

`validate_replacements_against_placeholders` is the defensive seam that makes this
safe: before any replacement `ComponentSpec` is allowed into the merged registry,
it must have a placeholder counterpart in the frozen catalog with the *exact same*
`component_id`/`version`/`domains`/`dependencies`/`period_behavior`/`aggregator` -
only `output_model`/`builder` (and the freely-evolvable `schema_id`/
`schema_version`) are expected to differ, since those are precisely what "replacing
a placeholder with real domain logic" means. Any drift (a missing placeholder, or a
mismatched id/version/domain/dependency/period-behavior/aggregator) fails loudly at
construction time rather than silently wiring in a component the frozen dataset/
analysis catalog never declared.

**No module-level dependency on `components.catalog`, direct or transitive.**
`PORTFOLIO_BROKER_COMPONENTS` (the raw real-spec tuple this module exists to
export) is built purely from
`portfolio_financial`/`broker_financial`/`portfolio_broker_technical` and carries
no import-time dependency on `components.catalog` at all - not even transitively.
Note that `datasets.catalog` (and therefore `analyses.catalog`, which imports it)
*does* import `components.catalog` at module scope, so every function here that
needs `build_dataset_registry`/`build_analysis_registry`/
`ALL_FOUNDATION_COMPONENTS` imports them **lazily, inside the function body**,
rather than at module scope:

- `validate_replacements_against_placeholders`/`build_portfolio_broker_component_registry`
  lazily import `catalog.ALL_FOUNDATION_COMPONENTS` (direct dependency).
- `build_portfolio_broker_dataset_registry` lazily imports
  `datasets.catalog.build_dataset_registry` (transitive dependency on
  `components.catalog` via `datasets.catalog`).
- `build_portfolio_broker_analysis_registry` lazily imports
  `analyses.catalog.build_analysis_registry` (transitive dependency on
  `components.catalog` via `analyses.catalog -> datasets.catalog`).

This is deliberate: the later "component-registry-integration" gate is expected
to have `catalog` import `PORTFOLIO_BROKER_COMPONENTS` from this module to build
the real merged catalog. A module-level import of `catalog`, `datasets.catalog`,
or `analyses.catalog` here would make that a circular import (directly or
transitively back through `catalog -> portfolio_broker_registry -> ... ->
catalog`). Keeping all of them local/lazy avoids that cycle while
`PORTFOLIO_BROKER_COMPONENTS` itself stays independently importable with zero
`catalog`/`datasets.catalog`/`analyses.catalog` dependency - importing this
module alone must never add `components.catalog` to `sys.modules`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from backend.app.services.ai_export.components.broker_concentration_context import BROKER_CONCENTRATION_COMPONENTS
from backend.app.services.ai_export.components.broker_cost_efficiency import BROKER_COST_EFFICIENCY_COMPONENTS
from backend.app.services.ai_export.components.broker_financial import BROKER_FINANCIAL_COMPONENTS
from backend.app.services.ai_export.components.drawdown_context import BROKER_DRAWDOWN_CONTEXT_COMPONENTS, PORTFOLIO_DRAWDOWN_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.portfolio_broker_technical import PORTFOLIO_BROKER_TECHNICAL_COMPONENTS
from backend.app.services.ai_export.components.portfolio_financial import PORTFOLIO_FINANCIAL_COMPONENTS
from backend.app.services.ai_export.components.portfolio_income import PORTFOLIO_INCOME_TIMELINE_COMPONENTS
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_context import BROKER_TECHNICAL_CONTEXT_COMPONENTS, PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.types import Domain

if TYPE_CHECKING:
    # Type-only: `analyses.spec`/`datasets.spec` do not import `components.catalog`
    # themselves, but `analyses.catalog`/`datasets.catalog` (the modules that own
    # the actual `build_analysis_registry`/`build_dataset_registry` *callables*) do
    # - transitively pulling in `components.catalog` at module scope. Those
    # callables are therefore imported lazily inside the functions that need them
    # (see `build_portfolio_broker_dataset_registry`/`build_portfolio_broker_analysis_registry`)
    # so this module never triggers a `components.catalog` import just by being
    # imported, keeping it safe for `components.catalog` to import
    # `PORTFOLIO_BROKER_COMPONENTS` from here without a circular import.
    from backend.app.services.ai_export.analyses.spec import AnalysisRegistry
    from backend.app.services.ai_export.datasets.spec import DatasetRegistry

__all__ = [
    "BROKER_REAL_COMPONENT_COUNT",
    "BROKER_REAL_COMPONENT_IDS",
    "PORTFOLIO_BROKER_COMPONENTS",
    "PORTFOLIO_REAL_COMPONENT_COUNT",
    "PORTFOLIO_REAL_COMPONENT_IDS",
    "DuplicateReplacementComponentIdError",
    "MissingPlaceholderComponentError",
    "PlaceholderMetadataMismatchError",
    "PortfolioBrokerRegistryError",
    "build_portfolio_broker_analysis_registry",
    "build_portfolio_broker_component_registry",
    "build_portfolio_broker_dataset_registry",
    "validate_replacements_against_placeholders",
]


class PortfolioBrokerRegistryError(ValueError):
    """Base error for this domain fragment's registry construction/validation."""


class DuplicateReplacementComponentIdError(PortfolioBrokerRegistryError):
    """Raised when two real Portfolio/Broker replacement `ComponentSpec`s share a `component_id`."""


class MissingPlaceholderComponentError(PortfolioBrokerRegistryError):
    """Raised when a replacement `component_id` has no counterpart in the frozen catalog placeholders."""


class PlaceholderMetadataMismatchError(PortfolioBrokerRegistryError):
    """Raised when a replacement's id/version/domain/dependencies/period_behavior/aggregator drifts from its placeholder."""


# Real Portfolio/Broker replacement waves, combined (own scope only - never
# Asset/FX, never anything outside `portfolio_financial`/`broker_financial`/
# `portfolio_broker_technical`).
PORTFOLIO_BROKER_COMPONENTS: tuple[ComponentSpec, ...] = (
    *PORTFOLIO_FINANCIAL_COMPONENTS,
    *BROKER_FINANCIAL_COMPONENTS,
    *PORTFOLIO_BROKER_TECHNICAL_COMPONENTS,
    *PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS,
    *BROKER_TECHNICAL_CONTEXT_COMPONENTS,
    *PORTFOLIO_DRAWDOWN_CONTEXT_COMPONENTS,
    *BROKER_DRAWDOWN_CONTEXT_COMPONENTS,
    *PORTFOLIO_INCOME_TIMELINE_COMPONENTS,
    *BROKER_CONCENTRATION_COMPONENTS,
    *BROKER_COST_EFFICIENCY_COMPONENTS,
)

# 10 Portfolio financial + 4 full technical + 4 context + 2 drawdown + 1 income
# timeline = 21; 8 Broker financial + 3 full technical + 3 context + 1 drawdown +
# 2 concentration + 1 cost efficiency = 18; combined = 39. Asserted at import time
# so any future drift in the source waves' tuples fails immediately, not deep
# inside a test.
PORTFOLIO_REAL_COMPONENT_IDS: tuple[str, ...] = tuple(spec.component_id for spec in PORTFOLIO_BROKER_COMPONENTS if Domain.PORTFOLIO in spec.domains)
BROKER_REAL_COMPONENT_IDS: tuple[str, ...] = tuple(spec.component_id for spec in PORTFOLIO_BROKER_COMPONENTS if Domain.BROKER in spec.domains)
PORTFOLIO_REAL_COMPONENT_COUNT = 21
BROKER_REAL_COMPONENT_COUNT = 18

assert len(PORTFOLIO_BROKER_COMPONENTS) == PORTFOLIO_REAL_COMPONENT_COUNT + BROKER_REAL_COMPONENT_COUNT, f"PORTFOLIO_BROKER_COMPONENTS must contain exactly {PORTFOLIO_REAL_COMPONENT_COUNT + BROKER_REAL_COMPONENT_COUNT} real component_ids, got {len(PORTFOLIO_BROKER_COMPONENTS)}"
assert len(PORTFOLIO_REAL_COMPONENT_IDS) == PORTFOLIO_REAL_COMPONENT_COUNT, f"expected {PORTFOLIO_REAL_COMPONENT_COUNT} Portfolio component_ids, got {len(PORTFOLIO_REAL_COMPONENT_IDS)}"
assert len(BROKER_REAL_COMPONENT_IDS) == BROKER_REAL_COMPONENT_COUNT, f"expected {BROKER_REAL_COMPONENT_COUNT} Broker component_ids, got {len(BROKER_REAL_COMPONENT_IDS)}"


def _default_placeholders() -> Sequence[ComponentSpec]:
    """Lazily imports the frozen central catalog's `ALL_FOUNDATION_COMPONENTS`.

    Imported *inside* this function (not at module scope) so that this module has
    no import-time dependency on `components.catalog`: the later
    "component-registry-integration" gate is expected to have `catalog` import
    `PORTFOLIO_BROKER_COMPONENTS` from this module, and a module-level `catalog`
    import here would turn that into a circular import.
    """
    from backend.app.services.ai_export.components.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle
        ALL_FOUNDATION_COMPONENTS,
    )

    return ALL_FOUNDATION_COMPONENTS


def validate_replacements_against_placeholders(
    replacements: Sequence[ComponentSpec],
    *,
    placeholders: Sequence[ComponentSpec] | None = None,
) -> None:
    """Validates every `replacements` entry against its frozen placeholder counterpart.

    - `replacements` must not declare duplicate `component_id`s.
    - Every `replacement.component_id` must exist in `placeholders` (defaults to
      the frozen central catalog's `ALL_FOUNDATION_COMPONENTS`, lazily imported and
      read-only - this function never mutates or re-registers the central catalog).
    - `version`/`domains`/`dependencies`/`period_behavior`/`aggregator` must be
      *exactly* equal between replacement and placeholder; `output_model`/
      `builder`/`schema_id`/`schema_version` are deliberately excluded from this
      check (they are precisely what a real domain implementation is expected,
      and free, to change).

    Raises `DuplicateReplacementComponentIdError`, `MissingPlaceholderComponentError`
    or `PlaceholderMetadataMismatchError` on any violation; returns `None` on success.
    """
    if placeholders is None:
        placeholders = _default_placeholders()
    seen_ids: set[str] = set()
    for replacement in replacements:
        if replacement.component_id in seen_ids:
            raise DuplicateReplacementComponentIdError(f"duplicate replacement component_id: {replacement.component_id!r}")
        seen_ids.add(replacement.component_id)

    placeholder_by_id = {spec.component_id: spec for spec in placeholders}
    for replacement in replacements:
        placeholder = placeholder_by_id.get(replacement.component_id)
        if placeholder is None:
            raise MissingPlaceholderComponentError(f"replacement component_id {replacement.component_id!r} has no frozen placeholder counterpart in the central catalog")
        mismatches: list[str] = []
        if replacement.version != placeholder.version:
            mismatches.append(f"version: replacement={replacement.version!r} placeholder={placeholder.version!r}")
        if replacement.domains != placeholder.domains:
            mismatches.append(f"domains: replacement={replacement.domains!r} placeholder={placeholder.domains!r}")
        if replacement.dependencies != placeholder.dependencies:
            mismatches.append(f"dependencies: replacement={replacement.dependencies!r} placeholder={placeholder.dependencies!r}")
        if replacement.period_behavior != placeholder.period_behavior:
            mismatches.append(f"period_behavior: replacement={replacement.period_behavior!r} placeholder={placeholder.period_behavior!r}")
        if replacement.aggregator != placeholder.aggregator:
            mismatches.append(f"aggregator: replacement={replacement.aggregator!r} placeholder={placeholder.aggregator!r}")
        if mismatches:
            raise PlaceholderMetadataMismatchError(f"{replacement.component_id}: replacement drifts from its frozen placeholder ({'; '.join(mismatches)})")


def build_portfolio_broker_component_registry(
    *,
    replacements: Sequence[ComponentSpec] = PORTFOLIO_BROKER_COMPONENTS,
    placeholders: Sequence[ComponentSpec] | None = None,
) -> ComponentRegistry:
    """Builds a real `ComponentRegistry` fragment: PB replacements + untouched non-PB placeholders.

    Validates `replacements` against `placeholders` first (see
    `validate_replacements_against_placeholders`), then merges by walking
    `placeholders` in its own canonical order and substituting each entry whose
    `component_id` has a replacement - this preserves the frozen catalog's
    declaration order (and therefore `ComponentRegistry.canonical_order`, which
    `*.all_data` dataset union ordering depends on) exactly, whether or not any
    given component_id was replaced. Non-PB placeholders (Asset/FX and anything
    else the frozen catalog declares) are never modified or reordered.

    `placeholders` defaults to `None`, resolved lazily to the frozen central
    catalog's `ALL_FOUNDATION_COMPONENTS` only when this function actually runs -
    see `_default_placeholders` for why the `catalog` import is deliberately not
    at module scope.
    """
    if placeholders is None:
        placeholders = _default_placeholders()
    validate_replacements_against_placeholders(replacements, placeholders=placeholders)
    replacement_by_id = {spec.component_id: spec for spec in replacements}
    merged = tuple(replacement_by_id.get(spec.component_id, spec) for spec in placeholders)
    return ComponentRegistry(merged)


def build_portfolio_broker_dataset_registry(component_registry: ComponentRegistry | None = None) -> DatasetRegistry:
    """Builds the frozen 32-dataset `DatasetRegistry` over a real Portfolio/Broker `ComponentRegistry`.

    Defaults to `build_portfolio_broker_component_registry()` when no registry is
    supplied. Every dataset (all 4 domains, per `datasets.catalog`'s frozen
    32-dataset wiring) is still validated as a whole - the DatasetRegistry does
    not know or care which component_ids are backed by real builders vs.
    placeholders, only that every declared component_id/domain pairing resolves.

    `datasets.catalog.build_dataset_registry` is imported lazily here (not at
    module scope) because `datasets.catalog` itself imports `components.catalog`
    at module scope - a module-level import here would transitively pull in
    `components.catalog` just from importing this module, which is exactly the
    cycle this module is designed to avoid (see the module docstring).
    """
    from backend.app.services.ai_export.datasets.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle (transitively via datasets.catalog)
        build_dataset_registry,
    )

    registry = component_registry or build_portfolio_broker_component_registry()
    return build_dataset_registry(registry)


def build_portfolio_broker_analysis_registry(dataset_registry: DatasetRegistry | None = None) -> AnalysisRegistry:
    """Builds the frozen 16-analysis `AnalysisRegistry` over a real Portfolio/Broker `DatasetRegistry`.

    Defaults to `build_portfolio_broker_dataset_registry()` when no registry is
    supplied.

    `analyses.catalog.build_analysis_registry` is imported lazily here for the
    same reason as `build_portfolio_broker_dataset_registry`: `analyses.catalog`
    imports `datasets.catalog`, which imports `components.catalog` at module
    scope.
    """
    from backend.app.services.ai_export.analyses.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle (transitively via analyses.catalog -> datasets.catalog)
        build_analysis_registry,
    )

    registry = dataset_registry or build_portfolio_broker_dataset_registry()
    return build_analysis_registry(registry)
