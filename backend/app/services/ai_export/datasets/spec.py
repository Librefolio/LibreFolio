"""Immutable `DatasetSpec`/`DatasetRegistry` contracts for the AI Export data-photo catalog.

A `DatasetSpec` ("fotografia dati") composes one or more registered components into
a stable, versioned unit consumable directly (data-only) or as an analysis
dependency. `DatasetRegistry` validates dataset ID uniqueness, that every
referenced component exists and is applicable to the dataset's domain, and that
`section_order` is exactly the permutation of `required_component_ids` +
`optional_component_ids` (no missing/extra/duplicate entries).

`build_all_data_dataset` implements the declarative/computed `*.all_data` datasets
(workstream D, point 7): it unions the components of every non-`all_data` dataset
of the same domain, dedups by component ID and orders the result using the
`ComponentRegistry` canonical registration order - never a bespoke monolithic
builder, and never recursive (an `all_data` dataset cannot be one of its own
sources). Requiredness is preserved across the union: a component required by any
source dataset stays required; a component that is optional in every source it
appears in stays optional.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import CODE_PATTERN, PAGE_PATTERN, DetailLevel, Domain, PeriodBehavior

from .._int_validation import require_positive_int

_DATASET_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

# Dotted, alphanumeric i18n key identifier (e.g. "aiExport.dataset.portfolio.overview.display").
# Deliberately strict: catalog display/description fields must carry *only* i18n keys for the
# frontend translation layer to resolve, never literal human-readable text (any embedded
# whitespace is almost certainly a raw sentence, not a key, and is rejected).
_I18N_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")


class DatasetSpecError(ValueError):
    """Raised when a `DatasetSpec` declaration is internally inconsistent."""


def _validate_code_tuple(values: Sequence[str], *, field_name: str, owner_id: str, allow_empty: bool) -> tuple[str, ...]:
    values = tuple(values)
    if not allow_empty and not values:
        raise DatasetSpecError(f"{owner_id}: {field_name} must not be empty")
    if len(values) != len(set(values)):
        raise DatasetSpecError(f"{owner_id}: {field_name} must be unique")
    for value in values:
        if not CODE_PATTERN.fullmatch(value):
            raise DatasetSpecError(f"{owner_id}: {field_name} entries must be stable lowercase code identifiers, not free text: {value!r}")
    return values


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Immutable declaration of a single AI Export dataset ("fotografia dati").

    - `dataset_id`/`version`: stable identity (dotted lowercase id, e.g.
      `"portfolio.overview"`).
    - `display_i18n_key`/`description_i18n_key`/`icon`: frontend presentation refs.
      The i18n keys must be dotted key identifiers resolved by the frontend
      translation layer (e.g. `"aiExport.dataset.portfolio.overview.display"`) -
      never literal human-readable text; this is validated and enforced here.
    - `applicability_code`: a stable, programmatic code (never free text) a future
      selection/applicability layer (API/UI) can key logic off of - independent
      from the human-readable i18n keys.
    - `applicable_pages`: page/scope identifiers where this dataset is selectable.
    - `required_component_ids`/`optional_component_ids`: component composition;
      disjoint by construction.
    - `section_order`: stable output order; must be exactly the union of required
      and optional component IDs.
    - `technical_requirements`: stable technical prerequisite codes (e.g.
      `"requires_price_history"`).
    - `period_semantics`: how this dataset as a whole relates to the AI Export
      period (metadata only, see `PeriodBehavior`).
    - `supported_detail_levels`: subset of Compact/Standard/Full this dataset
      supports.
    - `scope_requirement_codes`: optional, stable codes describing additional
      scope requirements a future selection engine may filter on (e.g.
      `"requires_multi_currency"`); empty by default - populate only if useful.
    - `visibility`: direct public selection boundary. Internal datasets remain
      composable by analyses but are not catalog entries or accepted direct requests.
    """

    dataset_id: str
    version: int
    domain: Domain
    display_i18n_key: str
    description_i18n_key: str
    icon: str
    applicability_code: str
    applicable_pages: tuple[str, ...]
    required_component_ids: tuple[str, ...]
    optional_component_ids: tuple[str, ...]
    section_order: tuple[str, ...]
    technical_requirements: tuple[str, ...]
    period_semantics: PeriodBehavior
    supported_detail_levels: frozenset[DetailLevel]
    scope_requirement_codes: tuple[str, ...] = ()
    visibility: CatalogVisibility = CatalogVisibility.INTERNAL

    def __post_init__(self) -> None:  # noqa: C901 — flat field-validation chain
        if not _DATASET_ID_PATTERN.fullmatch(self.dataset_id):
            raise DatasetSpecError(f"dataset_id has invalid format: {self.dataset_id!r}")
        require_positive_int(self.version, "version", owner_id=self.dataset_id, error_cls=DatasetSpecError)
        if not isinstance(self.domain, Domain):
            raise DatasetSpecError(f"{self.dataset_id}: domain must be a Domain member, got {self.domain!r}")
        if not self.icon:
            raise DatasetSpecError(f"{self.dataset_id}: icon must not be empty")
        if not self.display_i18n_key or not self.description_i18n_key:
            raise DatasetSpecError(f"{self.dataset_id}: i18n keys must not be empty")
        if not _I18N_KEY_PATTERN.fullmatch(self.display_i18n_key):
            raise DatasetSpecError(f"{self.dataset_id}: display_i18n_key must be a dotted i18n key, not literal text: {self.display_i18n_key!r}")
        if not _I18N_KEY_PATTERN.fullmatch(self.description_i18n_key):
            raise DatasetSpecError(f"{self.dataset_id}: description_i18n_key must be a dotted i18n key, not literal text: {self.description_i18n_key!r}")
        if not self.applicability_code or not CODE_PATTERN.fullmatch(self.applicability_code):
            raise DatasetSpecError(f"{self.dataset_id}: applicability_code must be a stable lowercase code identifier, not free text: {self.applicability_code!r}")
        applicable_pages = tuple(self.applicable_pages)
        if not applicable_pages:
            raise DatasetSpecError(f"{self.dataset_id}: applicable_pages must not be empty")
        if len(applicable_pages) != len(set(applicable_pages)):
            raise DatasetSpecError(f"{self.dataset_id}: applicable_pages must be unique")
        for page in applicable_pages:
            if not PAGE_PATTERN.fullmatch(page):
                raise DatasetSpecError(f"{self.dataset_id}: applicable_pages entries must be stable page/scope slugs, not free text: {page!r}")
        object.__setattr__(self, "applicable_pages", applicable_pages)
        required = tuple(self.required_component_ids)
        optional = tuple(self.optional_component_ids)
        if not required and not optional:
            raise DatasetSpecError(f"{self.dataset_id}: must declare at least one component")
        if len(required) != len(set(required)):
            raise DatasetSpecError(f"{self.dataset_id}: required_component_ids must be unique")
        if len(optional) != len(set(optional)):
            raise DatasetSpecError(f"{self.dataset_id}: optional_component_ids must be unique")
        overlap = set(required) & set(optional)
        if overlap:
            raise DatasetSpecError(f"{self.dataset_id}: component cannot be both required and optional: {sorted(overlap)}")
        object.__setattr__(self, "required_component_ids", required)
        object.__setattr__(self, "optional_component_ids", optional)
        section_order = tuple(self.section_order)
        expected = set(required) | set(optional)
        if set(section_order) != expected or len(section_order) != len(expected):
            raise DatasetSpecError(f"{self.dataset_id}: section_order must be exactly a permutation of required+optional component IDs")
        object.__setattr__(self, "section_order", section_order)
        object.__setattr__(
            self,
            "technical_requirements",
            _validate_code_tuple(self.technical_requirements, field_name="technical_requirements", owner_id=self.dataset_id, allow_empty=True),
        )
        object.__setattr__(
            self,
            "scope_requirement_codes",
            _validate_code_tuple(self.scope_requirement_codes, field_name="scope_requirement_codes", owner_id=self.dataset_id, allow_empty=True),
        )
        if not isinstance(self.period_semantics, PeriodBehavior):
            raise DatasetSpecError(f"{self.dataset_id}: period_semantics must be a PeriodBehavior member, got {self.period_semantics!r}")
        detail_levels = frozenset(self.supported_detail_levels)
        if not detail_levels:
            raise DatasetSpecError(f"{self.dataset_id}: supported_detail_levels must not be empty")
        for level in detail_levels:
            if not isinstance(level, DetailLevel):
                raise DatasetSpecError(f"{self.dataset_id}: supported_detail_levels must contain only DetailLevel members, got {level!r}")
        object.__setattr__(self, "supported_detail_levels", detail_levels)
        if not isinstance(self.visibility, CatalogVisibility):
            raise DatasetSpecError(f"{self.dataset_id}: visibility must be a CatalogVisibility member, got {self.visibility!r}")


class DatasetRegistryError(ValueError):
    """Base error for invalid `DatasetRegistry` construction or lookup."""


class DuplicateDatasetIdError(DatasetRegistryError):
    """Raised when two `DatasetSpec` entries share the same `dataset_id`."""


class UnknownDatasetError(DatasetRegistryError):
    """Raised when a dataset_id is looked up or referenced but not registered."""


class UnknownDatasetComponentError(DatasetRegistryError):
    """Raised when a `DatasetSpec` references a component_id absent from the `ComponentRegistry`."""


class DatasetComponentDomainMismatchError(DatasetRegistryError):
    """Raised when a `DatasetSpec` references a component not applicable to its domain."""


class DatasetRegistry:
    """Immutable collection of `DatasetSpec`, validated against a `ComponentRegistry`."""

    def __init__(self, specs: Iterable[DatasetSpec], *, component_registry: ComponentRegistry):
        ordered: dict[str, DatasetSpec] = {}
        for spec in specs:
            if not isinstance(spec, DatasetSpec):
                raise DatasetRegistryError(f"expected DatasetSpec, got {type(spec).__name__}")
            if spec.dataset_id in ordered:
                raise DuplicateDatasetIdError(f"duplicate dataset_id: {spec.dataset_id!r}")
            ordered[spec.dataset_id] = spec
        for spec in ordered.values():
            for component_id in (*spec.required_component_ids, *spec.optional_component_ids):
                if component_id not in component_registry:
                    raise UnknownDatasetComponentError(f"{spec.dataset_id} references unknown component {component_id!r}")
                component_spec = component_registry.get(component_id)
                if spec.domain not in component_spec.domains:
                    raise DatasetComponentDomainMismatchError(f"{spec.dataset_id}: component {component_id!r} is not applicable to domain {spec.domain.value!r}")
        self._specs: MappingProxyType[str, DatasetSpec] = MappingProxyType(ordered)
        self._component_registry = component_registry

    def __contains__(self, dataset_id: str) -> bool:
        return dataset_id in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[DatasetSpec]:
        return iter(self._specs.values())

    def get(self, dataset_id: str) -> DatasetSpec:
        try:
            return self._specs[dataset_id]
        except KeyError:
            raise UnknownDatasetError(f"unknown dataset_id: {dataset_id!r}") from None

    def for_domain(self, domain: Domain) -> tuple[DatasetSpec, ...]:
        return tuple(spec for spec in self._specs.values() if spec.domain == domain)

    def for_visibility(self, visibility: CatalogVisibility) -> tuple[DatasetSpec, ...]:
        if not isinstance(visibility, CatalogVisibility):
            raise TypeError("visibility must be a CatalogVisibility member")
        return tuple(spec for spec in self._specs.values() if spec.visibility is visibility)


def build_all_data_dataset(
    *,
    dataset_id: str,
    version: int,
    domain: Domain,
    display_i18n_key: str,
    description_i18n_key: str,
    icon: str,
    applicability_code: str,
    applicable_pages: tuple[str, ...],
    technical_requirements: tuple[str, ...],
    period_semantics: PeriodBehavior,
    supported_detail_levels: frozenset[DetailLevel],
    source_specs: Sequence[DatasetSpec],
    component_registry: ComponentRegistry,
    visibility: CatalogVisibility = CatalogVisibility.INTERNAL,
) -> DatasetSpec:
    """Builds a declarative, computed `*.all_data` `DatasetSpec`.

    Unions the required+optional component IDs of every dataset in `source_specs`
    (expected to be all non-`all_data` datasets of `domain`), dedups by component
    ID, and orders the result using `component_registry.canonical_order` so the
    union is deterministic regardless of `source_specs` declaration order.

    Requiredness is preserved, not promoted: a component required by *any* source
    dataset stays required in the union; a component that is only ever optional
    across every source stays optional. `section_order` covers the full union
    (required and optional interleaved in canonical order). Never recurses: an
    `all_data` dataset cannot include itself, nor another `*.all_data` dataset, as
    a source.
    """
    if any(spec.domain != domain for spec in source_specs):
        raise DatasetSpecError(f"{dataset_id}: all source datasets must belong to domain {domain.value!r}")
    if any(spec.dataset_id == dataset_id for spec in source_specs):
        raise DatasetSpecError(f"{dataset_id}: an all_data dataset cannot include itself as a source")
    if any(spec.dataset_id.endswith(".all_data") for spec in source_specs):
        raise DatasetSpecError(f"{dataset_id}: an all_data dataset cannot source another all_data dataset (no recursion)")
    required_ids: set[str] = set()
    optional_ids: set[str] = set()
    for spec in source_specs:
        required_ids.update(spec.required_component_ids)
        optional_ids.update(spec.optional_component_ids)
    # a component required by any source is required in the union; only components
    # that are *never* required anywhere remain optional-only
    optional_only_ids = optional_ids - required_ids
    union_ids = required_ids | optional_only_ids
    canonical_order = component_registry.canonical_order
    try:
        ordered_union = tuple(sorted(union_ids, key=canonical_order.index))
    except ValueError as exc:
        raise DatasetSpecError(f"{dataset_id}: a source dataset references a component absent from the canonical registry order") from exc
    ordered_required = tuple(component_id for component_id in ordered_union if component_id in required_ids)
    ordered_optional = tuple(component_id for component_id in ordered_union if component_id in optional_only_ids)
    return DatasetSpec(
        dataset_id=dataset_id,
        version=version,
        domain=domain,
        display_i18n_key=display_i18n_key,
        description_i18n_key=description_i18n_key,
        icon=icon,
        applicability_code=applicability_code,
        applicable_pages=applicable_pages,
        required_component_ids=ordered_required,
        optional_component_ids=ordered_optional,
        section_order=ordered_union,
        technical_requirements=technical_requirements,
        period_semantics=period_semantics,
        supported_detail_levels=supported_detail_levels,
        visibility=visibility,
    )
