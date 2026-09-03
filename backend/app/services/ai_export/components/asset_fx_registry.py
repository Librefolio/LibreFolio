"""Asset/FX domain fragment: real `ComponentRegistry`/`DatasetRegistry`/
`AnalysisRegistry` builders wiring the real Asset and FX component waves in
place of their frozen `components.catalog` placeholders.

This module is a **domain integration gate**, not the central catalog wiring: it
deliberately does **not** edit `backend.app.services.ai_export.components.catalog`
(that file is owned by the later serial "component-registry-integration" gate that
cuts over every domain at once - see the sibling `portfolio_broker_registry`
module, which follows the exact same pattern for Portfolio/Broker). Instead it
builds a *local* real `ComponentRegistry` fragment - substituting only the 20
Asset/FX `component_id`s (11 Asset + 9 FX) with their real implementations from
`asset_core`, `fx_core` and `asset_fx_technical`, while every other `component_id`
(Portfolio/Broker and anything else the frozen catalog declares) keeps its
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
`ASSET_FX_COMPONENTS` (the raw real-spec tuple this module exists to export) is
built purely from `asset_core`/`fx_core`/`asset_fx_technical` and carries no
import-time dependency on `components.catalog` at all - not even transitively.
Note that `datasets.catalog` (and therefore `analyses.catalog`, which imports it)
*does* import `components.catalog` at module scope, so every function here that
needs `build_dataset_registry`/`build_analysis_registry`/
`ALL_FOUNDATION_COMPONENTS` imports them **lazily, inside the function body**,
rather than at module scope:

- `validate_replacements_against_placeholders`/`build_asset_fx_component_registry`
  lazily import `catalog.ALL_FOUNDATION_COMPONENTS` (direct dependency).
- `build_asset_fx_dataset_registry` lazily imports
  `datasets.catalog.build_dataset_registry` (transitive dependency on
  `components.catalog` via `datasets.catalog`).
- `build_asset_fx_analysis_registry` lazily imports
  `analyses.catalog.build_analysis_registry` (transitive dependency on
  `components.catalog` via `analyses.catalog -> datasets.catalog`).

This is deliberate: the later "component-registry-integration" gate is expected
to have `catalog` import `ASSET_FX_COMPONENTS` from this module to build the real
merged catalog. A module-level import of `catalog`, `datasets.catalog`, or
`analyses.catalog` here would make that a circular import (directly or
transitively back through `catalog -> asset_fx_registry -> ... -> catalog`).
Keeping all of them local/lazy avoids that cycle while `ASSET_FX_COMPONENTS`
itself stays independently importable with zero `catalog`/`datasets.catalog`/
`analyses.catalog` dependency - importing this module alone must never add
`components.catalog` to `sys.modules`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from backend.app.services.ai_export.components.asset_core import ASSET_CORE_COMPONENTS
from backend.app.services.ai_export.components.asset_fx_technical import ASSET_FX_TECHNICAL_COMPONENTS
from backend.app.services.ai_export.components.drawdown_context import ASSET_DRAWDOWN_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.fx_core import FX_CORE_COMPONENTS
from backend.app.services.ai_export.components.fx_timing_context import FX_TIMING_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_context import ASSET_TECHNICAL_CONTEXT_COMPONENTS, FX_TECHNICAL_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.types import Domain

if TYPE_CHECKING:
    # Type-only: `analyses.spec`/`datasets.spec` do not import `components.catalog`
    # themselves, but `analyses.catalog`/`datasets.catalog` (the modules that own
    # the actual `build_analysis_registry`/`build_dataset_registry` *callables*) do
    # - transitively pulling in `components.catalog` at module scope. Those
    # callables are therefore imported lazily inside the functions that need them
    # (see `build_asset_fx_dataset_registry`/`build_asset_fx_analysis_registry`)
    # so this module never triggers a `components.catalog` import just by being
    # imported, keeping it safe for `components.catalog` to import
    # `ASSET_FX_COMPONENTS` from here without a circular import.
    from backend.app.services.ai_export.analyses.spec import AnalysisRegistry
    from backend.app.services.ai_export.datasets.spec import DatasetRegistry

__all__ = [
    "ASSET_FX_COMPONENTS",
    "ASSET_REAL_COMPONENT_COUNT",
    "ASSET_REAL_COMPONENT_IDS",
    "FX_REAL_COMPONENT_COUNT",
    "FX_REAL_COMPONENT_IDS",
    "AssetFxRegistryError",
    "DuplicateReplacementComponentIdError",
    "MissingPlaceholderComponentError",
    "PlaceholderMetadataMismatchError",
    "build_asset_fx_analysis_registry",
    "build_asset_fx_component_registry",
    "build_asset_fx_dataset_registry",
    "validate_replacements_against_placeholders",
]


class AssetFxRegistryError(ValueError):
    """Base error for this domain fragment's registry construction/validation."""


class DuplicateReplacementComponentIdError(AssetFxRegistryError):
    """Raised when two real Asset/FX replacement `ComponentSpec`s share a `component_id`."""


class MissingPlaceholderComponentError(AssetFxRegistryError):
    """Raised when a replacement `component_id` has no counterpart in the frozen catalog placeholders."""


class PlaceholderMetadataMismatchError(AssetFxRegistryError):
    """Raised when a replacement's id/version/domain/dependencies/period_behavior/aggregator drifts from its placeholder."""


# Real Asset/FX replacement waves, combined (own scope only - never
# Portfolio/Broker, never anything outside `asset_core`/`fx_core`/
# `asset_fx_technical`).
ASSET_FX_COMPONENTS: tuple[ComponentSpec, ...] = (
    *ASSET_CORE_COMPONENTS,
    *FX_CORE_COMPONENTS,
    *ASSET_FX_TECHNICAL_COMPONENTS,
    *ASSET_TECHNICAL_CONTEXT_COMPONENTS,
    *FX_TECHNICAL_CONTEXT_COMPONENTS,
    *ASSET_DRAWDOWN_CONTEXT_COMPONENTS,
    *FX_TIMING_CONTEXT_COMPONENTS,
)

# 8 Asset core + 3 full technical + 2 context + 1 drawdown = 14; 5 FX core + 4 full
# technical + 2 context + 1 timing context = 12; combined = 26. Asserted at import
# time so any future drift in the source waves' tuples fails immediately, not deep
# inside a test.
ASSET_REAL_COMPONENT_IDS: tuple[str, ...] = tuple(spec.component_id for spec in ASSET_FX_COMPONENTS if Domain.ASSET in spec.domains)
FX_REAL_COMPONENT_IDS: tuple[str, ...] = tuple(spec.component_id for spec in ASSET_FX_COMPONENTS if Domain.FX in spec.domains)
ASSET_REAL_COMPONENT_COUNT = 14
FX_REAL_COMPONENT_COUNT = 12

assert len(ASSET_FX_COMPONENTS) == ASSET_REAL_COMPONENT_COUNT + FX_REAL_COMPONENT_COUNT, f"ASSET_FX_COMPONENTS must contain exactly {ASSET_REAL_COMPONENT_COUNT + FX_REAL_COMPONENT_COUNT} real component_ids, got {len(ASSET_FX_COMPONENTS)}"
assert len(ASSET_REAL_COMPONENT_IDS) == ASSET_REAL_COMPONENT_COUNT, f"expected {ASSET_REAL_COMPONENT_COUNT} Asset component_ids, got {len(ASSET_REAL_COMPONENT_IDS)}"
assert len(FX_REAL_COMPONENT_IDS) == FX_REAL_COMPONENT_COUNT, f"expected {FX_REAL_COMPONENT_COUNT} FX component_ids, got {len(FX_REAL_COMPONENT_IDS)}"
assert len(set(ASSET_REAL_COMPONENT_IDS) | set(FX_REAL_COMPONENT_IDS)) == ASSET_REAL_COMPONENT_COUNT + FX_REAL_COMPONENT_COUNT, "Asset and FX component_ids must not overlap"


def _default_placeholders() -> Sequence[ComponentSpec]:
    """Lazily imports the frozen central catalog's `ALL_FOUNDATION_COMPONENTS`.

    Imported *inside* this function (not at module scope) so that this module has
    no import-time dependency on `components.catalog`: the later
    "component-registry-integration" gate is expected to have `catalog` import
    `ASSET_FX_COMPONENTS` from this module, and a module-level `catalog` import
    here would turn that into a circular import.
    """
    from backend.app.services.ai_export.components.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle
        ALL_FOUNDATION_COMPONENTS,
    )

    return ALL_FOUNDATION_COMPONENTS


def validate_replacements_against_placeholders(  # noqa: C901 — flat spec-field comparison, early raises
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


def build_asset_fx_component_registry(
    *,
    replacements: Sequence[ComponentSpec] = ASSET_FX_COMPONENTS,
    placeholders: Sequence[ComponentSpec] | None = None,
) -> ComponentRegistry:
    """Builds a real `ComponentRegistry` fragment: Asset/FX replacements + untouched non-Asset/FX placeholders.

    Validates `replacements` against `placeholders` first (see
    `validate_replacements_against_placeholders`), then merges by walking
    `placeholders` in its own canonical order and substituting each entry whose
    `component_id` has a replacement - this preserves the frozen catalog's
    declaration order (and therefore `ComponentRegistry.canonical_order`, which
    `*.all_data` dataset union ordering depends on) exactly, whether or not any
    given component_id was replaced. Non-Asset/FX placeholders (Portfolio/Broker
    and anything else the frozen catalog declares) are never modified or
    reordered.

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


def build_asset_fx_dataset_registry(component_registry: ComponentRegistry | None = None) -> DatasetRegistry:
    """Builds the frozen 32-dataset `DatasetRegistry` over a real Asset/FX `ComponentRegistry`.

    Defaults to `build_asset_fx_component_registry()` when no registry is
    supplied. Every dataset (all 4 domains, per `datasets.catalog`'s frozen
    32-dataset wiring) is still validated as a whole - the DatasetRegistry does
    not know or care which component_ids are backed by real builders vs.
    placeholders, only that every declared component_id/domain pairing resolves.
    Asset's 4 datasets (`asset.overview`, `asset.position_performance`,
    `asset.market_technical`, `asset.all_data`) and FX's 4 datasets
    (`fx.overview`, `fx.market_technical`, `fx.direct_exposure`, `fx.all_data`)
    now compose real payloads end-to-end; Portfolio/Broker datasets still
    compose against their fail-closed placeholders until that sibling gate lands.

    `datasets.catalog.build_dataset_registry` is imported lazily here (not at
    module scope) because `datasets.catalog` itself imports `components.catalog`
    at module scope - a module-level import here would transitively pull in
    `components.catalog` just from importing this module, which is exactly the
    cycle this module is designed to avoid (see the module docstring).
    """
    from backend.app.services.ai_export.datasets.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle (transitively via datasets.catalog)
        build_dataset_registry,
    )

    registry = component_registry or build_asset_fx_component_registry()
    return build_dataset_registry(registry)


def build_asset_fx_analysis_registry(dataset_registry: DatasetRegistry | None = None) -> AnalysisRegistry:
    """Builds the 17-analysis `AnalysisRegistry` over a real Asset/FX `DatasetRegistry`.

    Defaults to `build_asset_fx_dataset_registry()` when no registry is
    supplied. Asset's 3 analyses and FX's 3 analyses now resolve against real
    datasets/components.

    `analyses.catalog.build_analysis_registry` is imported lazily here for the
    same reason as `build_asset_fx_dataset_registry`: `analyses.catalog` imports
    `datasets.catalog`, which imports `components.catalog` at module scope.
    """
    from backend.app.services.ai_export.analyses.catalog import (  # noqa: PLC0415 - intentionally local to avoid a catalog<->fragment import cycle (transitively via analyses.catalog -> datasets.catalog)
        build_analysis_registry,
    )

    registry = dataset_registry or build_asset_fx_dataset_registry()
    return build_analysis_registry(registry)
