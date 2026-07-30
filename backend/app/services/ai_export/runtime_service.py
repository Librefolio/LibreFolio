"""Authenticated component-based AI Export catalog and snapshot orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess
from backend.app.schemas.ai_export_runtime import (
    AiExportAnalysisCatalogEntry,
    AiExportAnalysisContract,
    AiExportAnalysisSelection,
    AiExportAssetSnapshotRequest,
    AiExportAssetTargetReference,
    AiExportBrokerSnapshotRequest,
    AiExportBrokerTargetReference,
    AiExportCatalogResponse,
    AiExportDatasetCatalogEntry,
    AiExportDatasetManifestEntry,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportFxPairTargetReference,
    AiExportFxSnapshotRequest,
    AiExportManifestRole,
    AiExportPeriodSemantics,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioTargetReference,
    AiExportSectionEnvelope,
    AiExportSnapshotMeta,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotStats,
    AiExportTargetReference,
)
from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.analyses.spec import (
    AnalysisRegistry,
    AnalysisSpec,
    UnknownAnalysisError,
)
from backend.app.services.ai_export.components.asset_resources import AssetNotFoundError
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.composer import (
    AnalysisVersionMismatchError,
    Composer,
    DatasetVersionMismatchError,
    UnsupportedDetailLevelError,
)
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.datasets.spec import (
    DatasetRegistry,
    DatasetSpec,
    UnknownDatasetError,
)
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    RequiredComponentBuildError,
    build_bucket_plan_for_scope,
)

SCHEMA_VERSION = 1
CATALOG_VERSION = 1

_DETAIL_ORDER = {
    DetailLevel.COMPACT: 0,
    DetailLevel.STANDARD: 1,
    DetailLevel.FULL: 2,
}


class AiExportRuntimeError(RuntimeError):
    """Base error for public component-based AI Export orchestration."""


class AiExportBrokerAccessDeniedError(AiExportRuntimeError):
    def __init__(self, denied_broker_ids: tuple[int, ...]) -> None:
        self.denied_broker_ids = tuple(sorted(set(denied_broker_ids)))
        super().__init__("requested broker scope is not fully accessible")


class AiExportVersionMismatchError(AiExportRuntimeError):
    def __init__(self, field: str, *, expected: object, actual: object) -> None:
        self.field = field
        self.expected = str(expected)
        self.actual = str(actual)
        super().__init__(f"{field} mismatch: expected {expected!r}, got {actual!r}")


class AiExportUnsupportedSelectionError(AiExportRuntimeError):
    def __init__(self, selection_id: str) -> None:
        self.selection_id = selection_id
        super().__init__(f"unsupported AI Export selection: {selection_id}")


class AiExportSelectionNotApplicableError(AiExportRuntimeError):
    def __init__(self, applicability_code: str, reason_code: str) -> None:
        self.applicability_code = applicability_code
        self.reason_code = reason_code
        super().__init__(f"selection not applicable: {reason_code}")


class AiExportEntityNotFoundError(AiExportRuntimeError):
    """Raised when a requested domain entity does not exist."""


class AiExportSnapshotSourceError(AiExportRuntimeError):
    def __init__(self, component_id: str, *, retryable: bool) -> None:
        self.component_id = component_id
        self.retryable = retryable
        super().__init__(f"required AI Export component failed: {component_id}")


@dataclass(frozen=True, slots=True)
class AiExportPreparedRequest:
    request: AiExportSnapshotRequest
    broker_scope: tuple[int, ...]
    scope: BuildScope
    dataset: DatasetSpec | None = None
    analysis: AnalysisSpec | None = None


def _api_domain(domain: Domain) -> AiExportDomain:
    return AiExportDomain(domain.value)


def _api_detail(detail_level: DetailLevel) -> AiExportDetailLevel:
    return AiExportDetailLevel(detail_level.value)


def _target_reference(request: AiExportSnapshotRequest) -> AiExportTargetReference:
    if isinstance(request, AiExportPortfolioSnapshotRequest):
        return AiExportPortfolioTargetReference(kind="portfolio")
    if isinstance(request, AiExportBrokerSnapshotRequest):
        return AiExportBrokerTargetReference(kind="broker", broker_id=request.broker_id)
    if isinstance(request, AiExportAssetSnapshotRequest):
        return AiExportAssetTargetReference(kind="asset", asset_id=request.asset_id)
    if isinstance(request, AiExportFxSnapshotRequest):
        return AiExportFxPairTargetReference(
            kind="fx_pair",
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
        )
    raise TypeError(f"unsupported AI Export request type: {type(request).__name__}")


def _root_cause(error: BaseException) -> BaseException:
    current = error
    while isinstance(current, RequiredComponentBuildError):
        current = current.cause
    return current


class AiExportSnapshotService:
    """Standalone service used by HTTP today and future MCP transport later."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        component_registry: ComponentRegistry | None = None,
        dataset_registry: DatasetRegistry | None = None,
        analysis_registry: AnalysisRegistry | None = None,
        composer: Composer | None = None,
    ) -> None:
        self.db = db
        self.component_registry = component_registry if component_registry is not None else build_component_registry()
        self.dataset_registry = dataset_registry if dataset_registry is not None else build_dataset_registry(self.component_registry)
        self.analysis_registry = analysis_registry if analysis_registry is not None else build_analysis_registry(self.dataset_registry)
        self.composer = composer if composer is not None else Composer()

    @staticmethod
    def get_catalog() -> AiExportCatalogResponse:
        component_registry = build_component_registry()
        dataset_registry = build_dataset_registry(component_registry)
        analysis_registry = build_analysis_registry(dataset_registry)
        return AiExportSnapshotService._catalog_response(dataset_registry, analysis_registry)

    @staticmethod
    def _catalog_response(
        dataset_registry: DatasetRegistry,
        analysis_registry: AnalysisRegistry,
    ) -> AiExportCatalogResponse:
        datasets = tuple(
            AiExportDatasetCatalogEntry(
                kind="dataset",
                id=dataset.dataset_id,
                version=dataset.version,
                domain=_api_domain(dataset.domain),
                display_i18n_key=dataset.display_i18n_key,
                description_i18n_key=dataset.description_i18n_key,
                icon=dataset.icon,
                applicability_code=dataset.applicability_code,
                applicable_pages=dataset.applicable_pages,
                supported_detail_levels=tuple(
                    _api_detail(level)
                    for level in sorted(
                        dataset.supported_detail_levels,
                        key=_DETAIL_ORDER.__getitem__,
                    )
                ),
                period_semantics=AiExportPeriodSemantics(dataset.period_semantics.value),
                required_component_ids=dataset.required_component_ids,
                optional_component_ids=dataset.optional_component_ids,
            )
            for dataset in dataset_registry
        )
        analyses = []
        for analysis in analysis_registry:
            required_datasets = tuple(dataset_registry.get(dataset_id) for dataset_id in analysis.required_dataset_ids)
            supported = set(DetailLevel)
            for dataset in required_datasets:
                supported.intersection_update(dataset.supported_detail_levels)
            analyses.append(
                AiExportAnalysisCatalogEntry(
                    kind="analysis",
                    id=analysis.analysis_id,
                    version=analysis.version,
                    domain=_api_domain(analysis.domain),
                    display_i18n_key=analysis.display_i18n_key,
                    description_i18n_key=analysis.description_i18n_key,
                    icon=analysis.icon,
                    applicability_code=analysis.applicability_code,
                    applicable_pages=analysis.applicable_pages,
                    supported_detail_levels=tuple(_api_detail(level) for level in sorted(supported, key=_DETAIL_ORDER.__getitem__)),
                    required_dataset_ids=analysis.required_dataset_ids,
                    optional_dataset_ids=analysis.optional_dataset_ids,
                    instruction_template_id=analysis.instruction_template_id,
                    instruction_template_version=analysis.instruction_template_version,
                    response_contract_id=analysis.response_contract_id,
                    response_contract_version=analysis.response_contract_version,
                    supports_user_notes=analysis.supports_notes,
                )
            )
        return AiExportCatalogResponse(
            schema_version=SCHEMA_VERSION,
            catalog_version=CATALOG_VERSION,
            datasets=datasets,
            analyses=tuple(analyses),
        )

    async def _accessible_broker_ids(self, user_id: int) -> tuple[int, ...]:
        result = await self.db.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id))
        return tuple(sorted(set(result.scalars().all())))

    def _resolve_selection(
        self,
        request: AiExportSnapshotRequest,
    ) -> tuple[DatasetSpec | None, AnalysisSpec | None]:
        selection = request.selection
        expected_domain = Domain(request.domain)
        if isinstance(selection, AiExportDatasetSelection):
            try:
                dataset = self.dataset_registry.get(selection.id)
            except UnknownDatasetError as exc:
                raise AiExportUnsupportedSelectionError(selection.id) from exc
            if dataset.domain != expected_domain:
                raise AiExportUnsupportedSelectionError(selection.id)
            if selection.version != dataset.version:
                raise AiExportVersionMismatchError(
                    "selection.version",
                    expected=dataset.version,
                    actual=selection.version,
                )
            return dataset, None

        if isinstance(selection, AiExportAnalysisSelection):
            try:
                analysis = self.analysis_registry.get(selection.id)
            except UnknownAnalysisError as exc:
                raise AiExportUnsupportedSelectionError(selection.id) from exc
            if analysis.domain != expected_domain:
                raise AiExportUnsupportedSelectionError(selection.id)
            expected_fields = {
                "selection.version": analysis.version,
                "selection.instruction_template_id": analysis.instruction_template_id,
                "selection.instruction_template_version": analysis.instruction_template_version,
                "selection.response_contract_id": analysis.response_contract_id,
                "selection.response_contract_version": analysis.response_contract_version,
            }
            actual_fields = {
                "selection.version": selection.version,
                "selection.instruction_template_id": selection.instruction_template_id,
                "selection.instruction_template_version": selection.instruction_template_version,
                "selection.response_contract_id": selection.response_contract_id,
                "selection.response_contract_version": selection.response_contract_version,
            }
            for field, expected in expected_fields.items():
                actual = actual_fields[field]
                if actual != expected:
                    raise AiExportVersionMismatchError(
                        field,
                        expected=expected,
                        actual=actual,
                    )
            return None, analysis
        raise TypeError(f"unsupported selection type: {type(selection).__name__}")

    async def prepare_request(
        self,
        user_id: int,
        request: AiExportSnapshotRequest,
    ) -> AiExportPreparedRequest:
        if request.expected_catalog_version != CATALOG_VERSION:
            raise AiExportVersionMismatchError(
                "expected_catalog_version",
                expected=CATALOG_VERSION,
                actual=request.expected_catalog_version,
            )
        dataset, analysis = self._resolve_selection(request)
        accessible = await self._accessible_broker_ids(user_id)

        if isinstance(request, AiExportBrokerSnapshotRequest):
            requested = (request.broker_id,)
        elif not request.broker_ids:
            requested = accessible
        else:
            requested = tuple(request.broker_ids)
        denied = tuple(sorted(set(requested).difference(accessible)))
        if denied:
            raise AiExportBrokerAccessDeniedError(denied)

        scope = BuildScope(
            request_id=uuid4().hex,
            user_id=user_id,
            domain=Domain(request.domain),
            detail_level=DetailLevel(request.detail_level.value),
            period_start=request.period.start,
            period_end=request.period.end,
            target_currency=request.target_currency,
            broker_scope=tuple(sorted(requested)),
            asset_id=(request.asset_id if isinstance(request, AiExportAssetSnapshotRequest) else None),
            broker_id=(request.broker_id if isinstance(request, AiExportBrokerSnapshotRequest) else None),
            base_currency=(request.base_currency if isinstance(request, AiExportFxSnapshotRequest) else None),
            quote_currency=(request.quote_currency if isinstance(request, AiExportFxSnapshotRequest) else None),
        )
        return AiExportPreparedRequest(
            request=request,
            broker_scope=scope.broker_scope,
            scope=scope,
            dataset=dataset,
            analysis=analysis,
        )

    @staticmethod
    def _check_analysis_applicability(
        analysis: AnalysisSpec,
        sections: tuple[AiExportSectionEnvelope, ...],
    ) -> None:
        by_id = {section.component_id: section for section in sections}
        if analysis.applicability_code == "requires_direct_exposure":
            rows = by_id["fx.exposure_base_quote"].payload.get("rows", [])
            if not rows:
                raise AiExportSelectionNotApplicableError(
                    analysis.applicability_code,
                    "no_direct_exposure",
                )
        elif analysis.applicability_code == "requires_position":
            positions = by_id["asset.positions_by_broker"].payload.get("positions", [])
            if not positions:
                raise AiExportSelectionNotApplicableError(
                    analysis.applicability_code,
                    "no_position",
                )
        elif analysis.applicability_code == "requires_price_history":
            buckets = by_id["asset.ohlc_returns"].payload.get("buckets", [])
            observations = sum(int(bucket.get("observation_count", 0)) for bucket in buckets if isinstance(bucket, dict))
            if observations < 2:
                raise AiExportSelectionNotApplicableError(
                    analysis.applicability_code,
                    "insufficient_price_history",
                )

    @staticmethod
    def _response_with_stable_stats(
        *,
        domain: AiExportDomain,
        selection,
        detail_level: AiExportDetailLevel,
        target: AiExportTargetReference,
        meta: AiExportSnapshotMeta,
        dataset_manifest: tuple[AiExportDatasetManifestEntry, ...],
        analysis_contract: AiExportAnalysisContract | None,
        sections: tuple[AiExportSectionEnvelope, ...],
    ) -> AiExportSnapshotResponse:
        stats = AiExportSnapshotStats(
            dataset_count=len(dataset_manifest),
            section_count=len(sections),
            serialized_characters=0,
            estimated_tokens=0,
        )
        response = None
        for _attempt in range(6):
            response = AiExportSnapshotResponse(
                domain=domain,
                selection=selection,
                detail_level=detail_level,
                target=target,
                meta=meta,
                dataset_manifest=dataset_manifest,
                analysis_contract=analysis_contract,
                sections=sections,
                stats=stats,
            )
            serialized_characters = len(
                json.dumps(
                    response.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            )
            updated = AiExportSnapshotStats(
                dataset_count=len(dataset_manifest),
                section_count=len(sections),
                serialized_characters=serialized_characters,
                estimated_tokens=(serialized_characters + 3) // 4,
            )
            if updated == stats:
                return response
            stats = updated
        assert response is not None
        return response.model_copy(update={"stats": stats})

    async def build_snapshot(
        self,
        user_id: int,
        request: AiExportSnapshotRequest,
    ) -> AiExportSnapshotResponse:
        prepared = await self.prepare_request(user_id, request)
        context = BuildContext(
            self.component_registry,
            request_id=prepared.scope.request_id,
            scope=prepared.scope,
            bucket_plan=build_bucket_plan_for_scope(prepared.scope),
            session=self.db,
        )
        detail_level = DetailLevel(request.detail_level.value)
        try:
            if prepared.dataset is not None:
                composition = await self.composer.compose_dataset(
                    prepared.dataset,
                    context,
                    detail_level=detail_level,
                    expected_version=request.selection.version,
                )
                dataset_manifest = (
                    AiExportDatasetManifestEntry(
                        dataset_id=composition.dataset_id,
                        dataset_version=composition.dataset_version,
                        role=AiExportManifestRole.SELECTED,
                    ),
                )
                analysis_contract = None
                envelopes = composition.sections
            else:
                assert prepared.analysis is not None
                composition = await self.composer.compose_analysis(
                    prepared.analysis,
                    self.dataset_registry,
                    context,
                    detail_level=detail_level,
                    expected_version=request.selection.version,
                )
                required_ids = set(prepared.analysis.required_dataset_ids)
                dataset_manifest = tuple(
                    AiExportDatasetManifestEntry(
                        dataset_id=dataset_id,
                        dataset_version=self.dataset_registry.get(dataset_id).version,
                        role=(AiExportManifestRole.REQUIRED if dataset_id in required_ids else AiExportManifestRole.OPTIONAL),
                    )
                    for dataset_id in composition.dataset_ids
                )
                analysis_contract = AiExportAnalysisContract(
                    instruction_template_id=prepared.analysis.instruction_template_id,
                    instruction_template_version=prepared.analysis.instruction_template_version,
                    response_contract_id=prepared.analysis.response_contract_id,
                    response_contract_version=prepared.analysis.response_contract_version,
                )
                envelopes = composition.sections
        except (DatasetVersionMismatchError, AnalysisVersionMismatchError) as exc:
            raise AiExportVersionMismatchError(
                "selection.version",
                expected=(prepared.dataset.version if prepared.dataset is not None else prepared.analysis.version),
                actual=request.selection.version,
            ) from exc
        except UnsupportedDetailLevelError as exc:
            applicability_code = prepared.dataset.applicability_code if prepared.dataset is not None else prepared.analysis.applicability_code
            raise AiExportSelectionNotApplicableError(
                applicability_code,
                "unsupported_detail_level",
            ) from exc
        except RequiredComponentBuildError as exc:
            if isinstance(_root_cause(exc), AssetNotFoundError):
                raise AiExportEntityNotFoundError(str(_root_cause(exc))) from exc
            raise AiExportSnapshotSourceError(
                exc.component_id,
                retryable=False,
            ) from exc

        sections = tuple(AiExportSectionEnvelope.model_validate(envelope.model_dump(mode="json")) for envelope in envelopes)
        if prepared.analysis is not None:
            self._check_analysis_applicability(prepared.analysis, sections)

        generated_at = datetime.now(UTC)
        meta = AiExportSnapshotMeta(
            request_id=prepared.scope.request_id,
            generated_at=generated_at,
            snapshot_as_of=request.period.end,
            exported_period=request.period,
            calculation_range=None,
            earliest_calculation_date=None,
            target_currency=request.target_currency,
        )
        return self._response_with_stable_stats(
            domain=AiExportDomain(request.domain),
            selection=request.selection,
            detail_level=request.detail_level,
            target=_target_reference(request),
            meta=meta,
            dataset_manifest=dataset_manifest,
            analysis_contract=analysis_contract,
            sections=sections,
        )


__all__ = [
    "AiExportBrokerAccessDeniedError",
    "AiExportEntityNotFoundError",
    "AiExportPreparedRequest",
    "AiExportRuntimeError",
    "AiExportSelectionNotApplicableError",
    "AiExportSnapshotService",
    "AiExportSnapshotSourceError",
    "AiExportUnsupportedSelectionError",
    "AiExportVersionMismatchError",
    "CATALOG_VERSION",
    "SCHEMA_VERSION",
]
