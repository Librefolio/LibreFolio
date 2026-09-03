"""Authenticated component-based AI Export catalog and snapshot orchestration."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AI_EXPORT_SCHEMA_VERSION,
    AiExportAdditionalExportNecessity,
    AiExportAdditionalExportPeriod,
    AiExportAdditionalExportSuggestion,
    AiExportAnalysisCatalogEntry,
    AiExportAnalysisContract,
    AiExportAnalysisSelection,
    AiExportAssetDirectoryEntry,
    AiExportAssetSnapshotRequest,
    AiExportAssetTargetReference,
    AiExportBrokerDirectoryEntry,
    AiExportBrokerSnapshotRequest,
    AiExportBrokerTargetReference,
    AiExportCatalogResponse,
    AiExportDatasetCatalogEntry,
    AiExportDatasetManifestEntry,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportEntityDirectory,
    AiExportEventSelectionManifest,
    AiExportFxPairDirectoryEntry,
    AiExportFxPairTargetReference,
    AiExportFxSnapshotRequest,
    AiExportHistoryCoverage,
    AiExportIndicatorSamplingPolicy,
    AiExportManifestRole,
    AiExportPeriod,
    AiExportPeriodSemantics,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioTargetReference,
    AiExportPriceSamplingPolicy,
    AiExportSectionEnvelope,
    AiExportSnapshotMeta,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotStats,
    AiExportTargetReference,
    AiExportTechnicalSamplingManifest,
)
from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.analyses.spec import (
    AnalysisRegistry,
    AnalysisSpec,
    UnknownAnalysisError,
)
from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.asset_resources import AssetNotFoundError
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.technical_shared import load_fx_rate_series
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
    ResourceLoadError,
    build_bucket_plan_for_scope,
)
from backend.app.services.ai_export.telemetry import (
    canonical_json,
    estimate_tokens_chars_div_4,
)
from backend.app.services.ai_export.temporal.policy import (
    BucketDetailLevel,
    EventSelectionPolicy,
    indicator_history_row_limit,
)

SCHEMA_VERSION = AI_EXPORT_SCHEMA_VERSION
CATALOG_VERSION = AI_EXPORT_CATALOG_VERSION

_DETAIL_ORDER = {
    DetailLevel.COMPACT: 0,
    DetailLevel.STANDARD: 1,
    DetailLevel.FULL: 2,
}

_FX_HISTORY_COVERAGE_DATASET_IDS = frozenset(
    {
        "fx.overview",
        "fx.market_technical",
        "fx.market_context",
        "fx.conversion_timing_context",
        "fx.all_data",
        "fx.market_and_exposure",
        "fx.market_history",
    }
)

_DEFAULT_COMPONENT_REGISTRY = build_component_registry()
_DEFAULT_DATASET_REGISTRY = build_dataset_registry(_DEFAULT_COMPONENT_REGISTRY)
_DEFAULT_ANALYSIS_REGISTRY = build_analysis_registry(_DEFAULT_DATASET_REGISTRY)
_DEFAULT_COMPOSER = Composer()


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
    def __init__(self, component_id: str, *, retryable: bool, reason_code: str | None = None) -> None:
        self.component_id = component_id
        self.retryable = retryable
        self.reason_code = reason_code
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


_ASSET_ENTITY_ID = re.compile(r"^asset:(\d+)$")


def _collect_entity_ids(
    value: object,
    *,
    asset_ids: set[int],
    broker_ids: set[int],
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key == "entity_id" and isinstance(nested, str):
                match = _ASSET_ENTITY_ID.fullmatch(nested)
                if match:
                    asset_ids.add(int(match.group(1)))
            elif key.endswith("asset_id") and isinstance(nested, int) and not isinstance(nested, bool):
                asset_ids.add(nested)
            elif key.endswith("broker_id") and isinstance(nested, int) and not isinstance(nested, bool):
                broker_ids.add(nested)
            _collect_entity_ids(
                nested,
                asset_ids=asset_ids,
                broker_ids=broker_ids,
            )
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _collect_entity_ids(
                nested,
                asset_ids=asset_ids,
                broker_ids=broker_ids,
            )


def _other_identifiers(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(str(item) for item in value if item is not None and str(item))
    return (str(value),)


def _root_cause(error: BaseException) -> BaseException:
    current = error
    while isinstance(current, (RequiredComponentBuildError, ResourceLoadError)):
        current = current.cause
    return current


def _api_section_envelope(
    envelope: SectionEnvelope,
) -> AiExportSectionEnvelope:
    """Bridge an already validated component envelope without re-walking payload."""

    return AiExportSectionEnvelope.model_construct(
        component_id=envelope.component_id,
        component_version=envelope.component_version,
        schema_id=envelope.schema_id,
        schema_version=envelope.schema_version,
        payload=envelope.payload,
    )


def _stable_snapshot_stats(
    *,
    base_characters: int,
    base_bytes: int,
    dataset_count: int,
    section_count: int,
) -> AiExportSnapshotStats:
    """Solve self-referential size fields using integer digit lengths only."""

    values = (0, 0, 0)
    for _attempt in range(16):
        digit_delta = sum(len(str(value)) - 1 for value in values)
        serialized_characters = base_characters + digit_delta
        serialized_bytes = base_bytes + digit_delta
        estimated_tokens = estimate_tokens_chars_div_4(serialized_characters)
        updated = (
            serialized_characters,
            serialized_bytes,
            estimated_tokens,
        )
        if updated == values:
            return AiExportSnapshotStats(
                dataset_count=dataset_count,
                section_count=section_count,
                serialized_characters=serialized_characters,
                serialized_bytes=serialized_bytes,
                estimated_tokens=estimated_tokens,
            )
        values = updated
    raise RuntimeError("AI Export snapshot stats did not converge")


async def _fx_history_coverage(context: BuildContext) -> AiExportHistoryCoverage:
    scope = context.scope
    if scope is None or scope.domain is not Domain.FX:
        raise ValueError("FX history coverage requires an FX BuildScope")
    rate_series = await load_fx_rate_series(context)
    visible = tuple(item for item in rate_series.observations if scope.period_start <= item.requested_date <= scope.period_end)
    if not visible:
        raise ValueError("successful FX snapshot requires at least one visible rate observation")
    available_start = visible[0].requested_date
    requested_days = (scope.period_end - scope.period_start).days + 1
    covered_days = (scope.period_end - available_start).days + 1
    observed_count = sum(not item.backward_filled and item.actual_date == item.requested_date for item in visible)
    earliest_source_date = min(item.actual_date for item in rate_series.observations)
    complete = available_start == scope.period_start
    return AiExportHistoryCoverage(
        requested_period=AiExportPeriod(start=scope.period_start, end=scope.period_end),
        available_period=AiExportPeriod(start=available_start, end=scope.period_end),
        requested_calendar_days=requested_days,
        covered_calendar_days=covered_days,
        coverage_ratio=covered_days / requested_days,
        complete=complete,
        reason_code=None if complete else "insufficient_source_history",
        observed_count=observed_count,
        backward_filled_count=len(visible) - observed_count,
        earliest_source_date=earliest_source_date,
    )


def _requires_fx_history_coverage(dataset_manifest: tuple[AiExportDatasetManifestEntry, ...]) -> bool:
    """Return whether the selected composition consumes base/quote rate history."""

    return any(entry.dataset_id in _FX_HISTORY_COVERAGE_DATASET_IDS for entry in dataset_manifest)


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
        self.component_registry = component_registry if component_registry is not None else _DEFAULT_COMPONENT_REGISTRY
        self.dataset_registry = dataset_registry if dataset_registry is not None else _DEFAULT_DATASET_REGISTRY
        self.analysis_registry = analysis_registry if analysis_registry is not None else _DEFAULT_ANALYSIS_REGISTRY
        self.composer = composer if composer is not None else _DEFAULT_COMPOSER

    @staticmethod
    @cache
    def get_catalog() -> AiExportCatalogResponse:
        return AiExportSnapshotService._catalog_response(
            _DEFAULT_DATASET_REGISTRY,
            _DEFAULT_ANALYSIS_REGISTRY,
        )

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
            for dataset in dataset_registry.for_visibility(CatalogVisibility.PUBLIC)
        )
        analyses = []
        for analysis in analysis_registry.for_visibility(CatalogVisibility.PUBLIC):
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
                    additional_export_suggestions=tuple(
                        AiExportAdditionalExportSuggestion(
                            dataset_id=suggestion.dataset_id,
                            reason_i18n_key=suggestion.reason_i18n_key,
                            recommended_period=AiExportAdditionalExportPeriod(suggestion.recommended_period.value),
                            recommended_detail=_api_detail(suggestion.recommended_detail),
                            necessity=AiExportAdditionalExportNecessity(suggestion.necessity.value),
                        )
                        for suggestion in analysis.additional_export_suggestions
                    ),
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
            if dataset.domain != expected_domain or dataset.visibility is not CatalogVisibility.PUBLIC:
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
            if analysis.domain != expected_domain or analysis.visibility is not CatalogVisibility.PUBLIC:
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

    async def _entity_directory(
        self,
        request: AiExportSnapshotRequest,
        sections: tuple[AiExportSectionEnvelope, ...],
        *,
        broker_scope: tuple[int, ...],
    ) -> AiExportEntityDirectory:
        asset_ids: set[int] = set()
        broker_ids: set[int] = set()
        for section in sections:
            _collect_entity_ids(
                section.payload,
                asset_ids=asset_ids,
                broker_ids=broker_ids,
            )
        if isinstance(request, AiExportAssetSnapshotRequest):
            asset_ids.add(request.asset_id)
        elif isinstance(request, AiExportBrokerSnapshotRequest):
            broker_ids.add(request.broker_id)
        broker_ids.update(broker_scope)

        assets: tuple[AiExportAssetDirectoryEntry, ...] = ()
        if asset_ids:
            rows = (await self.db.execute(select(Asset).where(Asset.id.in_(sorted(asset_ids))))).scalars()
            by_id = {asset.id: asset for asset in rows if asset.id is not None}
            assets = tuple(
                AiExportAssetDirectoryEntry(
                    asset_id=asset_id,
                    display_name=by_id[asset_id].display_name,
                    ticker=by_id[asset_id].identifier_ticker,
                    isin=by_id[asset_id].identifier_isin,
                    cusip=by_id[asset_id].identifier_cusip,
                    sedol=by_id[asset_id].identifier_sedol,
                    figi=by_id[asset_id].identifier_figi,
                    other_identifiers=_other_identifiers(by_id[asset_id].identifier_other),
                    currency=by_id[asset_id].currency,
                    asset_type=by_id[asset_id].asset_type.value,
                    quote_base_quantity=by_id[asset_id].quote_base_quantity or 1,
                )
                for asset_id in sorted(asset_ids)
                if asset_id in by_id
            )

        brokers: tuple[AiExportBrokerDirectoryEntry, ...] = ()
        if broker_ids:
            rows = (await self.db.execute(select(Broker).where(Broker.id.in_(sorted(broker_ids))))).scalars()
            by_id = {broker.id: broker for broker in rows if broker.id is not None}
            brokers = tuple(
                AiExportBrokerDirectoryEntry(
                    broker_id=broker_id,
                    display_name=by_id[broker_id].name,
                )
                for broker_id in sorted(broker_ids)
                if broker_id in by_id
            )

        fx_pairs = (
            (
                AiExportFxPairDirectoryEntry(
                    base_currency=request.base_currency,
                    quote_currency=request.quote_currency,
                ),
            )
            if isinstance(request, AiExportFxSnapshotRequest)
            else ()
        )
        return AiExportEntityDirectory(
            assets=assets,
            brokers=brokers,
            fx_pairs=fx_pairs,
        )

    @staticmethod
    def _response_with_stable_stats(
        *,
        domain: AiExportDomain,
        selection,
        detail_level: AiExportDetailLevel,
        target: AiExportTargetReference,
        entity_directory: AiExportEntityDirectory,
        meta: AiExportSnapshotMeta,
        dataset_manifest: tuple[AiExportDatasetManifestEntry, ...],
        analysis_contract: AiExportAnalysisContract | None,
        technical_sampling: AiExportTechnicalSamplingManifest | None,
        event_selection: AiExportEventSelectionManifest | None,
        sections: tuple[AiExportSectionEnvelope, ...],
    ) -> AiExportSnapshotResponse:
        stats = AiExportSnapshotStats(
            dataset_count=len(dataset_manifest),
            section_count=len(sections),
            serialized_characters=0,
            serialized_bytes=0,
            estimated_tokens=0,
        )
        response = AiExportSnapshotResponse(
            domain=domain,
            selection=selection,
            detail_level=detail_level,
            target=target,
            entity_directory=entity_directory,
            meta=meta,
            dataset_manifest=dataset_manifest,
            analysis_contract=analysis_contract,
            technical_sampling=technical_sampling,
            event_selection=event_selection,
            sections=sections,
            stats=stats,
        )
        serialized = canonical_json(response.model_dump(mode="json"))
        stable_stats = _stable_snapshot_stats(
            base_characters=len(serialized),
            base_bytes=len(serialized.encode("utf-8")),
            dataset_count=len(dataset_manifest),
            section_count=len(sections),
        )
        return response.model_copy(update={"stats": stable_stats})

    @staticmethod
    def _technical_sampling_manifest(
        context: BuildContext,
    ) -> AiExportTechnicalSamplingManifest | None:
        indicator_policies = tuple(
            AiExportIndicatorSamplingPolicy(
                signal_instance_id=diagnostic.signal_instance_id,
                signal_code=diagnostic.signal_code,
                temporal_class=diagnostic.temporal_class,
                bucket_count=diagnostic.bucket_count,
            )
            for diagnostic in context.indicator_sampling
        )
        price = context.price_sampling
        if price is None and not indicator_policies:
            return None
        if context.scope is None:
            raise RuntimeError("technical sampling diagnostics require a request scope")
        return AiExportTechnicalSamplingManifest(
            detail_level=AiExportDetailLevel(context.scope.detail_level.value),
            price_policy=(
                AiExportPriceSamplingPolicy(
                    bucket_count=price.bucket_count,
                )
                if price is not None
                else None
            ),
            indicator_policies=indicator_policies,
            indicator_history_row_limit=indicator_history_row_limit(BucketDetailLevel(context.scope.detail_level.value)),
        )

    @staticmethod
    def _event_selection_manifest(
        context: BuildContext,
    ) -> AiExportEventSelectionManifest | None:
        if not context.event_selection_used:
            return None
        if context.scope is None:
            raise RuntimeError("event selection diagnostics require a request scope")
        policy = EventSelectionPolicy.for_detail_level(BucketDetailLevel(context.scope.detail_level.value))
        return AiExportEventSelectionManifest(
            minimum_latest_events_per_annotation=policy.minimum_latest_events_per_annotation,
            complete_recent_window_days=policy.complete_recent_window_days,
        )

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
            root_cause = _root_cause(exc)
            if isinstance(root_cause, AssetNotFoundError):
                raise AiExportEntityNotFoundError(str(root_cause)) from exc
            raise AiExportSnapshotSourceError(
                exc.component_id,
                retryable=False,
                reason_code=getattr(root_cause, "reason_code", None),
            ) from exc

        sections = tuple(_api_section_envelope(envelope) for envelope in envelopes)
        if prepared.analysis is not None:
            self._check_analysis_applicability(prepared.analysis, sections)
        entity_directory = await self._entity_directory(
            request,
            sections,
            broker_scope=prepared.broker_scope,
        )

        generated_at = datetime.now(UTC)
        history_coverage = await _fx_history_coverage(context) if isinstance(request, AiExportFxSnapshotRequest) and _requires_fx_history_coverage(dataset_manifest) else None
        meta = AiExportSnapshotMeta(
            request_id=prepared.scope.request_id,
            generated_at=generated_at,
            snapshot_as_of=request.period.end,
            exported_period=request.period,
            calculation_range=None,
            earliest_calculation_date=None,
            target_currency=request.target_currency,
            history_coverage=history_coverage,
        )
        return self._response_with_stable_stats(
            domain=AiExportDomain(request.domain),
            selection=request.selection,
            detail_level=request.detail_level,
            target=_target_reference(request),
            entity_directory=entity_directory,
            meta=meta,
            dataset_manifest=dataset_manifest,
            analysis_contract=analysis_contract,
            technical_sampling=self._technical_sampling_manifest(context),
            event_selection=self._event_selection_manifest(context),
            sections=sections,
        )


__all__ = [
    "CATALOG_VERSION",
    "SCHEMA_VERSION",
    "AiExportBrokerAccessDeniedError",
    "AiExportEntityNotFoundError",
    "AiExportPreparedRequest",
    "AiExportRuntimeError",
    "AiExportSelectionNotApplicableError",
    "AiExportSnapshotService",
    "AiExportSnapshotSourceError",
    "AiExportUnsupportedSelectionError",
    "AiExportVersionMismatchError",
]
