"""AI Export dataset ("fotografia dati") runtime foundations (Phase 0 refinement, workstream D)."""

from __future__ import annotations

from backend.app.services.ai_export.datasets.catalog import (
    EXPECTED_DATASET_COUNT,
    build_dataset_registry,
)
from backend.app.services.ai_export.datasets.spec import (
    DatasetComponentDomainMismatchError,
    DatasetRegistry,
    DatasetRegistryError,
    DatasetSpec,
    DatasetSpecError,
    DuplicateDatasetIdError,
    UnknownDatasetComponentError,
    UnknownDatasetError,
    build_all_data_dataset,
)

__all__ = [
    "EXPECTED_DATASET_COUNT",
    "DatasetComponentDomainMismatchError",
    "DatasetRegistry",
    "DatasetRegistryError",
    "DatasetSpec",
    "DatasetSpecError",
    "DuplicateDatasetIdError",
    "UnknownDatasetComponentError",
    "UnknownDatasetError",
    "build_all_data_dataset",
    "build_dataset_registry",
]
