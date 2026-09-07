"""Deterministic composer for the AI Export catalog/component runtime.

`Composer` turns a `DatasetSpec` (or an `AnalysisSpec`'s required/optional
datasets) into concrete, ordered, deduplicated section envelopes for a single
`BuildContext`:

- resolves required components/datasets and fails closed (propagates
  `RequiredComponentBuildError`) if any of them cannot be built;
- includes optional components/datasets only when they are applicable and
  actually buildable, silently omitting them otherwise (diagnostics stay
  internal, see `BuildContext.diagnostics`);
- deduplicates sections shared across datasets by `(component_id,
  component_version)`, keeping the first (canonical) occurrence;
- fails closed on a detail level unsupported by a dataset, or on an explicit
  dataset/analysis version mismatch requested by the caller;
- never trims sections by token/size budget - that is explicitly out of scope
  per the refinement plan.

Binding "failure" vs "empty" semantics (per architecture review): "buildable" above
means the builder ran without raising - it does NOT mean the resulting payload is
non-empty. A required component/dataset that legitimately has no data (e.g.
`fx.direct_exposure` for a portfolio holding no foreign-currency positions) still
succeeds and is included with its (empty) payload; the catalog statically declares
the capability regardless of whether any given request happens to have exposure,
so composing it never raises/503s for that reason. Genuine build failures (a
raised exception) are the only case handled as "unavailable". Deciding whether an
*analysis* is inapplicable because one of its required datasets came back empty
(a future HTTP 422) is a separate, higher-level concern this composer does not
implement.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from backend.app.services.ai_export.analyses.spec import AnalysisSpec
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.types import DetailLevel
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec
from backend.app.services.ai_export.dependencies import BuildContext, RequiredComponentBuildError


class ComposerError(RuntimeError):
    """Base error raised while composing datasets/analyses."""


class UnsupportedDetailLevelError(ComposerError):
    """Raised when a dataset does not support the requested detail level."""


class DatasetVersionMismatchError(ComposerError):
    """Raised when the caller's expected dataset version does not match the registry."""


class AnalysisVersionMismatchError(ComposerError):
    """Raised when the caller's expected analysis version does not match the registry."""


@dataclass(frozen=True, slots=True)
class DatasetComposition:
    """Result of composing a single `DatasetSpec`: ordered, deduplicated sections."""

    dataset_id: str
    dataset_version: int
    detail_level: DetailLevel
    sections: tuple[SectionEnvelope, ...]


@dataclass(frozen=True, slots=True)
class AnalysisComposition:
    """Result of composing an `AnalysisSpec`: which datasets were actually used, and the deduplicated union of their sections."""

    analysis_id: str
    analysis_version: int
    detail_level: DetailLevel
    dataset_ids: tuple[str, ...]
    sections: tuple[SectionEnvelope, ...]


def _dedup_envelopes(envelopes: Iterable[SectionEnvelope]) -> tuple[SectionEnvelope, ...]:
    seen: set[tuple[str, int]] = set()
    ordered: list[SectionEnvelope] = []
    for envelope in envelopes:
        key = (envelope.component_id, envelope.component_version)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(envelope)
    return tuple(ordered)


class Composer:
    """Stateless composer over an explicit `BuildContext`; holds no request state of its own."""

    async def compose_dataset(
        self,
        dataset: DatasetSpec,
        context: BuildContext,
        *,
        detail_level: DetailLevel,
        expected_version: int | None = None,
    ) -> DatasetComposition:
        """Resolves `dataset`'s required+applicable-optional components in `section_order`.

        Fails closed (raises) if `expected_version` is given and does not match the
        dataset's registered version, or if `detail_level` is unsupported by the
        dataset. Required-component build failures propagate as
        `RequiredComponentBuildError`; optional-component failures are silently
        omitted (diagnostics recorded on `context`).
        """
        if expected_version is not None and expected_version != dataset.version:
            raise DatasetVersionMismatchError(f"{dataset.dataset_id}: expected version {expected_version}, registry has {dataset.version}")
        if detail_level not in dataset.supported_detail_levels:
            raise UnsupportedDetailLevelError(f"{dataset.dataset_id} does not support detail level {detail_level.value!r}")
        required_ids = set(dataset.required_component_ids)
        envelopes: list[SectionEnvelope] = []
        for component_id in dataset.section_order:
            envelope = await context.resolve(component_id, required=component_id in required_ids)
            if envelope is not None:
                envelopes.append(envelope)
        return DatasetComposition(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            detail_level=detail_level,
            sections=_dedup_envelopes(envelopes),
        )

    async def compose_analysis(
        self,
        analysis: AnalysisSpec,
        dataset_registry: DatasetRegistry,
        context: BuildContext,
        *,
        detail_level: DetailLevel,
        expected_version: int | None = None,
    ) -> AnalysisComposition:
        """Resolves `analysis`'s required datasets (fail closed) plus applicable/buildable optional datasets.

        Required datasets propagate any `RequiredComponentBuildError` from
        `compose_dataset`. Optional datasets are skipped entirely (not partially
        included) if unsupported at this `detail_level` or if any required
        component within them fails to build. Shared components across datasets
        are deduplicated by `(component_id, component_version)`.
        """
        if expected_version is not None and expected_version != analysis.version:
            raise AnalysisVersionMismatchError(f"{analysis.analysis_id}: expected version {expected_version}, registry has {analysis.version}")
        used_dataset_ids: list[str] = []
        all_envelopes: list[SectionEnvelope] = []
        for dataset_id in analysis.required_dataset_ids:
            dataset_spec = dataset_registry.get(dataset_id)
            composition = await self.compose_dataset(dataset_spec, context, detail_level=detail_level)
            used_dataset_ids.append(dataset_id)
            all_envelopes.extend(composition.sections)
        for dataset_id in analysis.optional_dataset_ids:
            dataset_spec = dataset_registry.get(dataset_id)
            if detail_level not in dataset_spec.supported_detail_levels:
                continue
            try:
                composition = await self.compose_dataset(dataset_spec, context, detail_level=detail_level)
            except RequiredComponentBuildError:
                continue
            used_dataset_ids.append(dataset_id)
            all_envelopes.extend(composition.sections)
        return AnalysisComposition(
            analysis_id=analysis.analysis_id,
            analysis_version=analysis.version,
            detail_level=detail_level,
            dataset_ids=tuple(used_dataset_ids),
            sections=_dedup_envelopes(all_envelopes),
        )
