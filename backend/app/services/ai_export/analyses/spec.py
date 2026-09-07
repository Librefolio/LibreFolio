"""Immutable `AnalysisSpec`/`AnalysisRegistry` contracts for the AI Export analysis catalog.

An `AnalysisSpec` declares which datasets an AI analysis requires/optionally uses,
plus the frontend-owned instruction template and response contract identity it is
paired with. `AnalysisRegistry` validates analysis ID uniqueness, that every
referenced dataset exists and belongs to the analysis's domain, and that
required/optional dataset IDs never overlap.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.types import CODE_PATTERN, PAGE_PATTERN, DetailLevel, Domain
from backend.app.services.ai_export.datasets.spec import DatasetRegistry

from .._int_validation import require_positive_int

_ANALYSIS_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_DATASET_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
# i18n keys must be dotted with at least 2 segments (e.g. "aiExport.analysis.x.display"),
# never bare English text - mirrors the pattern used by `datasets.spec`.
_I18N_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")


class AnalysisSpecError(ValueError):
    """Raised when an `AnalysisSpec` declaration is internally inconsistent."""


class AdditionalExportPeriod(StrEnum):
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    MAXIMUM_AVAILABLE = "maximum_available"


class AdditionalExportNecessity(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass(frozen=True, slots=True)
class AdditionalExportSuggestion:
    """Structured, frontend-localized recommendation for a separate public dataset."""

    dataset_id: str
    reason_i18n_key: str
    recommended_period: AdditionalExportPeriod
    recommended_detail: DetailLevel
    necessity: AdditionalExportNecessity = AdditionalExportNecessity.OPTIONAL

    def __post_init__(self) -> None:
        if not _DATASET_ID_PATTERN.fullmatch(self.dataset_id):
            raise AnalysisSpecError(f"additional export dataset_id has invalid format: {self.dataset_id!r}")
        if not _I18N_KEY_PATTERN.fullmatch(self.reason_i18n_key):
            raise AnalysisSpecError(f"{self.dataset_id}: reason_i18n_key must be a dotted i18n key, got {self.reason_i18n_key!r}")
        if not isinstance(self.recommended_period, AdditionalExportPeriod):
            raise AnalysisSpecError(f"{self.dataset_id}: recommended_period must be an AdditionalExportPeriod member")
        if not isinstance(self.recommended_detail, DetailLevel):
            raise AnalysisSpecError(f"{self.dataset_id}: recommended_detail must be a DetailLevel member")
        if not isinstance(self.necessity, AdditionalExportNecessity):
            raise AnalysisSpecError(f"{self.dataset_id}: necessity must be an AdditionalExportNecessity member")


def _validate_code_tuple(values: tuple[str, ...], *, label: str, analysis_id: str, pattern: re.Pattern[str], allow_empty: bool) -> tuple[str, ...]:
    values = tuple(values)
    if not allow_empty and not values:
        raise AnalysisSpecError(f"{analysis_id}: {label} must not be empty")
    if len(values) != len(set(values)):
        raise AnalysisSpecError(f"{analysis_id}: {label} must be unique")
    for value in values:
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise AnalysisSpecError(f"{analysis_id}: {label} entry has invalid format: {value!r}")
    return values


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    """Immutable declaration of a single AI Export analysis profile.

    - `analysis_id`/`version`: stable identity (dotted lowercase id, e.g.
      `"portfolio.pac_planning"`).
    - `domain`: the domain this analysis applies to; every referenced dataset must
      belong to the same domain (no cross-domain analyses in this catalog).
    - `display_i18n_key`/`description_i18n_key`: i18n keys only (never literal
      text) for catalog presentation - the frontend/docs own the localized
      strings, this backend catalog only tracks the key identity.
    - `icon`: a stable icon identifier (frontend-owned icon set key).
    - `applicable_pages`: stable page/scope slugs where this analysis may be
      offered (e.g. `("dashboard",)`).
    - `applicability_code`: a stable, non-i18n programmatic code (not free text)
      for a future applicability/selection engine to key logic off of - distinct
      from the i18n display/description keys above.
    - `required_dataset_ids`/`optional_dataset_ids`: dataset composition;
      disjoint by construction. `dataset_order` gives the deterministic
      required-then-optional composition order.
    - `instruction_template_id`/`instruction_template_version`: frontend-owned
      localized instruction template reference (backend only tracks identity).
    - `response_contract_id`/`response_contract_version`: frontend-owned response
      contract reference used for the fail-closed handshake.
    - `supports_notes`: whether user-provided notes are accepted for this analysis.
    - `visibility`: direct public selection boundary; defaults internal/fail-closed.
    """

    analysis_id: str
    version: int
    domain: Domain
    display_i18n_key: str
    description_i18n_key: str
    icon: str
    applicability_code: str
    applicable_pages: tuple[str, ...]
    required_dataset_ids: tuple[str, ...]
    optional_dataset_ids: tuple[str, ...]
    instruction_template_id: str
    instruction_template_version: int
    response_contract_id: str
    response_contract_version: int
    supports_notes: bool = True
    additional_export_suggestions: tuple[AdditionalExportSuggestion, ...] = ()
    visibility: CatalogVisibility = CatalogVisibility.INTERNAL

    def __post_init__(self) -> None:  # noqa: C901 — flat field-validation chain
        if not _ANALYSIS_ID_PATTERN.fullmatch(self.analysis_id):
            raise AnalysisSpecError(f"analysis_id has invalid format: {self.analysis_id!r}")
        require_positive_int(self.version, "version", owner_id=self.analysis_id, error_cls=AnalysisSpecError)
        if not isinstance(self.domain, Domain):
            raise AnalysisSpecError(f"{self.analysis_id}: domain must be a Domain member, got {type(self.domain).__name__}")
        if not self.display_i18n_key or not _I18N_KEY_PATTERN.fullmatch(self.display_i18n_key):
            raise AnalysisSpecError(f"{self.analysis_id}: display_i18n_key must be a dotted i18n key, got {self.display_i18n_key!r}")
        if not self.description_i18n_key or not _I18N_KEY_PATTERN.fullmatch(self.description_i18n_key):
            raise AnalysisSpecError(f"{self.analysis_id}: description_i18n_key must be a dotted i18n key, got {self.description_i18n_key!r}")
        if not self.icon:
            raise AnalysisSpecError(f"{self.analysis_id}: icon must not be empty")
        if not self.applicability_code or not CODE_PATTERN.fullmatch(self.applicability_code):
            raise AnalysisSpecError(f"{self.analysis_id}: applicability_code has invalid format: {self.applicability_code!r}")
        applicable_pages = _validate_code_tuple(self.applicable_pages, label="applicable_pages", analysis_id=self.analysis_id, pattern=PAGE_PATTERN, allow_empty=False)
        object.__setattr__(self, "applicable_pages", applicable_pages)
        required = tuple(self.required_dataset_ids)
        optional = tuple(self.optional_dataset_ids)
        if not required:
            raise AnalysisSpecError(f"{self.analysis_id}: required_dataset_ids must not be empty")
        if len(required) != len(set(required)):
            raise AnalysisSpecError(f"{self.analysis_id}: required_dataset_ids must be unique")
        if len(optional) != len(set(optional)):
            raise AnalysisSpecError(f"{self.analysis_id}: optional_dataset_ids must be unique")
        overlap = set(required) & set(optional)
        if overlap:
            raise AnalysisSpecError(f"{self.analysis_id}: dataset cannot be both required and optional: {sorted(overlap)}")
        object.__setattr__(self, "required_dataset_ids", required)
        object.__setattr__(self, "optional_dataset_ids", optional)
        if not self.instruction_template_id:
            raise AnalysisSpecError(f"{self.analysis_id}: instruction_template_id must not be empty")
        require_positive_int(self.instruction_template_version, "instruction_template_version", owner_id=self.analysis_id, error_cls=AnalysisSpecError)
        if not self.response_contract_id:
            raise AnalysisSpecError(f"{self.analysis_id}: response_contract_id must not be empty")
        require_positive_int(self.response_contract_version, "response_contract_version", owner_id=self.analysis_id, error_cls=AnalysisSpecError)
        suggestions = tuple(self.additional_export_suggestions)
        if any(not isinstance(suggestion, AdditionalExportSuggestion) for suggestion in suggestions):
            raise AnalysisSpecError(f"{self.analysis_id}: additional_export_suggestions must contain AdditionalExportSuggestion values")
        suggestion_ids = [suggestion.dataset_id for suggestion in suggestions]
        if len(suggestion_ids) != len(set(suggestion_ids)):
            raise AnalysisSpecError(f"{self.analysis_id}: additional export dataset IDs must be unique")
        object.__setattr__(self, "additional_export_suggestions", suggestions)
        if not isinstance(self.visibility, CatalogVisibility):
            raise AnalysisSpecError(f"{self.analysis_id}: visibility must be a CatalogVisibility member, got {self.visibility!r}")

    @property
    def dataset_order(self) -> tuple[str, ...]:
        """Deterministic composition order: required datasets first, then optional, both in declaration order."""
        return self.required_dataset_ids + self.optional_dataset_ids


class AnalysisRegistryError(ValueError):
    """Base error for invalid `AnalysisRegistry` construction or lookup."""


class DuplicateAnalysisIdError(AnalysisRegistryError):
    """Raised when two `AnalysisSpec` entries share the same `analysis_id`."""


class UnknownAnalysisError(AnalysisRegistryError):
    """Raised when an analysis_id is looked up but not registered."""


class UnknownAnalysisDatasetError(AnalysisRegistryError):
    """Raised when an `AnalysisSpec` references a dataset_id absent from the `DatasetRegistry`."""


class AnalysisDatasetDomainMismatchError(AnalysisRegistryError):
    """Raised when an `AnalysisSpec` references a dataset belonging to a different domain."""


class AnalysisSuggestionVisibilityError(AnalysisRegistryError):
    """Raised when a public analysis suggests a non-public dataset."""


class AnalysisRegistry:
    """Immutable collection of `AnalysisSpec`, validated against a `DatasetRegistry`."""

    def __init__(self, specs: Iterable[AnalysisSpec], *, dataset_registry: DatasetRegistry):  # noqa: C901 — flat registry cross-validation loops
        ordered: dict[str, AnalysisSpec] = {}
        for spec in specs:
            if not isinstance(spec, AnalysisSpec):
                raise AnalysisRegistryError(f"expected AnalysisSpec, got {type(spec).__name__}")
            if spec.analysis_id in ordered:
                raise DuplicateAnalysisIdError(f"duplicate analysis_id: {spec.analysis_id!r}")
            ordered[spec.analysis_id] = spec
        for spec in ordered.values():
            for dataset_id in spec.dataset_order:
                if dataset_id not in dataset_registry:
                    raise UnknownAnalysisDatasetError(f"{spec.analysis_id} references unknown dataset {dataset_id!r}")
                dataset_spec = dataset_registry.get(dataset_id)
                if dataset_spec.domain != spec.domain:
                    raise AnalysisDatasetDomainMismatchError(f"{spec.analysis_id}: dataset {dataset_id!r} belongs to domain {dataset_spec.domain.value!r}, expected {spec.domain.value!r}")
            for suggestion in spec.additional_export_suggestions:
                if suggestion.dataset_id not in dataset_registry:
                    raise UnknownAnalysisDatasetError(f"{spec.analysis_id} suggests unknown dataset {suggestion.dataset_id!r}")
                dataset_spec = dataset_registry.get(suggestion.dataset_id)
                if dataset_spec.domain != spec.domain:
                    raise AnalysisDatasetDomainMismatchError(f"{spec.analysis_id}: suggested dataset {suggestion.dataset_id!r} belongs to domain {dataset_spec.domain.value!r}, expected {spec.domain.value!r}")
                if spec.visibility is CatalogVisibility.PUBLIC and dataset_spec.visibility is not CatalogVisibility.PUBLIC:
                    raise AnalysisSuggestionVisibilityError(f"{spec.analysis_id}: public additional export suggestion {suggestion.dataset_id!r} must reference a public dataset")
        self._specs: MappingProxyType[str, AnalysisSpec] = MappingProxyType(ordered)
        self._dataset_registry = dataset_registry

    def __contains__(self, analysis_id: str) -> bool:
        return analysis_id in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[AnalysisSpec]:
        return iter(self._specs.values())

    def get(self, analysis_id: str) -> AnalysisSpec:
        try:
            return self._specs[analysis_id]
        except KeyError:
            raise UnknownAnalysisError(f"unknown analysis_id: {analysis_id!r}") from None

    def for_domain(self, domain: Domain) -> tuple[AnalysisSpec, ...]:
        return tuple(spec for spec in self._specs.values() if spec.domain == domain)

    def for_visibility(self, visibility: CatalogVisibility) -> tuple[AnalysisSpec, ...]:
        if not isinstance(visibility, CatalogVisibility):
            raise TypeError("visibility must be a CatalogVisibility member")
        return tuple(spec for spec in self._specs.values() if spec.visibility is visibility)
