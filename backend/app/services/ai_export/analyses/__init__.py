"""AI Export analysis runtime foundations (Phase 0 refinement, workstream D)."""

from __future__ import annotations

from backend.app.services.ai_export.analyses.catalog import (
    EXPECTED_ANALYSIS_COUNT,
    PUBLIC_ANALYSES,
    build_analysis_registry,
)
from backend.app.services.ai_export.analyses.spec import (
    AnalysisDatasetDomainMismatchError,
    AnalysisRegistry,
    AnalysisRegistryError,
    AnalysisSpec,
    AnalysisSpecError,
    DuplicateAnalysisIdError,
    UnknownAnalysisDatasetError,
    UnknownAnalysisError,
)

__all__ = [
    "EXPECTED_ANALYSIS_COUNT",
    "PUBLIC_ANALYSES",
    "AnalysisDatasetDomainMismatchError",
    "AnalysisRegistry",
    "AnalysisRegistryError",
    "AnalysisSpec",
    "AnalysisSpecError",
    "DuplicateAnalysisIdError",
    "UnknownAnalysisDatasetError",
    "UnknownAnalysisError",
    "build_analysis_registry",
]
