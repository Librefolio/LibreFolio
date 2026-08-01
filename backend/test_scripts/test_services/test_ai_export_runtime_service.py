"""Service tests for the component-based public AI Export V2 runtime."""

from __future__ import annotations

import decimal
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.ai_export.runtime_service as rs_module
from backend.app.db.models import Asset, Broker, BrokerUserAccess
from backend.app.schemas.ai_export_runtime import (
    AiExportAnalysisSelection,
    AiExportAssetSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportFxSnapshotRequest,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.schemas.signals import SignalTemporalClass
from backend.app.services.ai_export.analyses.spec import AnalysisRegistry, AnalysisSpec
from backend.app.services.ai_export.components.asset_resources import AssetNotFoundError
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import FxRateObservation, FxRateSeriesResource
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_shared import FxRateHistoryError
from backend.app.services.ai_export.components.types import (
    ALL_DETAIL_LEVELS,
    Domain,
    PeriodBehavior,
)
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec
from backend.app.services.ai_export.dependencies import (
    build_indicator_bucket_plan_for_scope,
)
from backend.app.services.ai_export.runtime_service import (
    AiExportBrokerAccessDeniedError,
    AiExportEntityNotFoundError,
    AiExportSelectionNotApplicableError,
    AiExportSnapshotService,
    AiExportSnapshotSourceError,
    AiExportUnsupportedSelectionError,
    AiExportVersionMismatchError,
)

START = date(2026, 1, 1)
END = date(2026, 3, 31)


class _ValuePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class _RowsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: tuple[int, ...] = ()


class _PositionsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positions: tuple[int, ...] = ()


class _EntityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    broker_id: int


def _session_with_accessible_brokers(broker_ids: list[int]) -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)

    async def _execute(statement):
        entity = statement.column_descriptions[0].get("entity")
        result = MagicMock()
        if entity is not None and entity.__name__ == "BrokerUserAccess":
            result.scalars.return_value.all.return_value = broker_ids
        else:
            result.scalars.return_value = ()
        return result

    session.execute.side_effect = _execute
    return session


def _component(
    component_id: str,
    domain: Domain,
    output_model: type[BaseModel],
    output: BaseModel | None = None,
    *,
    error: BaseException | None = None,
) -> ComponentSpec:
    def _build(context, dependencies):  # noqa: ARG001
        if error is not None:
            raise error
        assert output is not None
        return output

    return ComponentSpec(
        component_id=component_id,
        version=1,
        domains=frozenset({domain}),
        output_model=output_model,
        builder=_build,
        period_behavior=PeriodBehavior.WINDOWED,
    )


def _dataset(
    dataset_id: str,
    domain: Domain,
    component_ids: tuple[str, ...],
) -> DatasetSpec:
    return DatasetSpec(
        dataset_id=dataset_id,
        version=1,
        domain=domain,
        display_i18n_key=f"aiExport.dataset.{dataset_id}.display",
        description_i18n_key=f"aiExport.dataset.{dataset_id}.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=(domain.value,),
        required_component_ids=component_ids,
        optional_component_ids=(),
        section_order=component_ids,
        technical_requirements=(),
        period_semantics=PeriodBehavior.WINDOWED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
    )


def _analysis(
    analysis_id: str,
    domain: Domain,
    dataset_ids: tuple[str, ...],
    *,
    applicability_code: str = "always_applicable",
) -> AnalysisSpec:
    return AnalysisSpec(
        analysis_id=analysis_id,
        version=1,
        domain=domain,
        display_i18n_key=f"aiExport.analysis.{analysis_id}.display",
        description_i18n_key=f"aiExport.analysis.{analysis_id}.description",
        icon="activity",
        applicability_code=applicability_code,
        applicable_pages=(domain.value,),
        required_dataset_ids=dataset_ids,
        optional_dataset_ids=(),
        instruction_template_id=f"{analysis_id}.instructions",
        instruction_template_version=1,
        response_contract_id=f"{analysis_id}.response",
        response_contract_version=1,
    )


def _service(
    session: AsyncSession,
    components: tuple[ComponentSpec, ...],
    datasets: tuple[DatasetSpec, ...],
    analyses: tuple[AnalysisSpec, ...] = (),
) -> AiExportSnapshotService:
    component_registry = ComponentRegistry(components)
    dataset_registry = DatasetRegistry(
        datasets,
        component_registry=component_registry,
    )
    analysis_registry = AnalysisRegistry(
        analyses,
        dataset_registry=dataset_registry,
    )
    return AiExportSnapshotService(
        session,
        component_registry=component_registry,
        dataset_registry=dataset_registry,
        analysis_registry=analysis_registry,
    )


def _portfolio_dataset_request() -> AiExportPortfolioSnapshotRequest:
    return AiExportPortfolioSnapshotRequest(
        domain="portfolio",
        selection=AiExportDatasetSelection(
            kind="dataset",
            id="portfolio.overview",
            version=1,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": START, "end": END},
        target_currency="EUR",
        expected_catalog_version=2,
    )


def _portfolio_analysis_request() -> AiExportPortfolioSnapshotRequest:
    return AiExportPortfolioSnapshotRequest(
        domain="portfolio",
        selection=AiExportAnalysisSelection(
            kind="analysis",
            id="portfolio.review",
            version=1,
            instruction_template_id="portfolio.review.instructions",
            instruction_template_version=1,
            response_contract_id="portfolio.review.response",
            response_contract_version=1,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": START, "end": END},
        target_currency="EUR",
        expected_catalog_version=2,
    )


def test_catalog_exposes_exact_25_datasets_and_16_analyses_without_prompts():
    catalog = AiExportSnapshotService.get_catalog()
    serialized = catalog.model_dump_json()

    assert len(catalog.datasets) == 32
    assert len(catalog.analyses) == 16
    assert {entry.id for entry in catalog.datasets} >= {
        "portfolio.overview",
        "broker.overview",
        "asset.overview",
        "fx.overview",
    }
    assert {entry.id for entry in catalog.analyses} >= {
        "portfolio.pac_planning",
        "broker.review",
        "asset.position_review",
        "fx.exposure_impact",
    }
    assert "prompt" not in serialized.lower()
    assert "web_research" not in serialized.lower()


@pytest.mark.asyncio
async def test_dataset_selection_builds_manifest_sections_and_stable_stats():
    session = _session_with_accessible_brokers([2, 1])
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _ValuePayload,
        _ValuePayload(value=7),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    service = _service(session, (component,), (dataset,))

    response = await service.build_snapshot(41, _portfolio_dataset_request())

    assert response.selection.kind == "dataset"
    assert response.dataset_manifest[0].role == "selected"
    assert response.sections[0].payload == {"value": 7}
    assert response.technical_sampling is None
    assert response.event_selection is None
    serialized = json.dumps(
        response.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert response.stats.serialized_characters == len(serialized)
    assert response.stats.serialized_bytes == len(serialized.encode("utf-8"))
    assert response.stats.estimated_tokens == (len(serialized) + 3) // 4


@pytest.mark.asyncio
async def test_snapshot_exposes_deduplicated_sampling_manifests_in_v1():
    session = _session_with_accessible_brokers([])
    sampling_diagnostics = {}

    def _build(context, dependencies):  # noqa: ARG001
        context.register_price_sampling()
        indicator_plan = build_indicator_bucket_plan_for_scope(
            context.scope,
            SignalTemporalClass.MEDIUM,
        )
        for _ in range(2):
            context.register_indicator_sampling(
                signal_instance_id="ema_20",
                signal_code="EMA",
                temporal_class=SignalTemporalClass.MEDIUM,
                bucket_plan=indicator_plan,
            )
        context.register_event_selection()
        sampling_diagnostics["price"] = context.price_sampling
        sampling_diagnostics["indicator"] = context.indicator_sampling[0]
        return _ValuePayload(value=1)

    component = ComponentSpec(
        component_id="portfolio.technical_prices",
        version=1,
        domains=frozenset({Domain.PORTFOLIO}),
        output_model=_ValuePayload,
        builder=_build,
        period_behavior=PeriodBehavior.WINDOWED,
    )
    dataset = _dataset(
        "portfolio.technical",
        Domain.PORTFOLIO,
        ("portfolio.technical_prices",),
    )
    service = _service(session, (component,), (dataset,))
    request = _portfolio_dataset_request().model_copy(
        update={
            "selection": AiExportDatasetSelection(
                kind="dataset",
                id="portfolio.technical",
                version=1,
            )
        }
    )

    response = await service.build_snapshot(41, request)

    assert response.meta.schema_version == 2
    assert response.meta.catalog_version == 2
    assert response.technical_sampling is not None
    assert response.technical_sampling.detail_level == "standard"
    assert response.technical_sampling.price_policy is not None
    assert response.technical_sampling.price_policy.bucket_count == sampling_diagnostics["price"].bucket_count
    assert len(response.technical_sampling.indicator_policies) == 1
    indicator = response.technical_sampling.indicator_policies[0]
    assert indicator.signal_instance_id == "ema_20"
    assert indicator.temporal_class == SignalTemporalClass.MEDIUM
    assert indicator.bucket_count == sampling_diagnostics["indicator"].bucket_count
    assert sampling_diagnostics["price"].exponent == 2
    assert sampling_diagnostics["price"].half_life_offset == 30
    assert sampling_diagnostics["price"].max_bucket_days == 14
    assert sampling_diagnostics["indicator"].exponent == 2
    assert sampling_diagnostics["indicator"].half_life_offset == 15
    assert sampling_diagnostics["indicator"].max_bucket_days == 20
    serialized_sampling = response.technical_sampling.model_dump_json()
    assert '"p":' not in serialized_sampling
    assert '"m":' not in serialized_sampling
    assert '"k":' not in serialized_sampling
    assert response.event_selection is not None
    assert response.event_selection.minimum_latest_events_per_annotation == 20
    assert response.event_selection.complete_recent_window_days == 30
    assert response.event_selection.grouped_by == (
        "entity_id",
        "annotation_key",
    )


@pytest.mark.asyncio
async def test_snapshot_builds_minimal_entity_directory_from_component_references():
    session = AsyncMock(spec=AsyncSession)

    async def _execute(statement):
        entity = statement.column_descriptions[0].get("entity")
        result = MagicMock()
        if entity is BrokerUserAccess:
            result.scalars.return_value.all.return_value = [3]
        elif entity is Asset:
            result.scalars.return_value = (
                SimpleNamespace(
                    id=7,
                    display_name="Named Asset",
                    identifier_ticker="NAMED",
                    identifier_isin="IT0000000007",
                    identifier_cusip=None,
                    identifier_sedol=None,
                    identifier_figi=None,
                    identifier_other=["provider:7"],
                    currency="EUR",
                    asset_type=SimpleNamespace(value="ETF"),
                    quote_base_quantity=100,
                ),
            )
        elif entity is Broker:
            result.scalars.return_value = (SimpleNamespace(id=3, name="Named Broker"),)
        else:
            raise AssertionError(f"unexpected entity query: {entity}")
        return result

    session.execute.side_effect = _execute
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _EntityPayload,
        _EntityPayload(asset_id=7, broker_id=3),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    service = _service(session, (component,), (dataset,))

    response = await service.build_snapshot(
        41,
        _portfolio_dataset_request().model_copy(update={"broker_ids": [3]}),
    )

    assert response.entity_directory.assets[0].display_name == "Named Asset"
    assert response.entity_directory.assets[0].isin == "IT0000000007"
    assert response.entity_directory.assets[0].quote_base_quantity == 100
    assert response.entity_directory.brokers[0].display_name == "Named Broker"


@pytest.mark.asyncio
async def test_all_accessible_scope_keeps_inactive_broker_in_entity_directory():
    session = AsyncMock(spec=AsyncSession)

    async def _execute(statement):
        entity = statement.column_descriptions[0].get("entity")
        result = MagicMock()
        if entity is BrokerUserAccess:
            result.scalars.return_value.all.return_value = [3, 4]
        elif entity is Asset:
            result.scalars.return_value = (
                SimpleNamespace(
                    id=7,
                    display_name="Named Asset",
                    identifier_ticker=None,
                    identifier_isin=None,
                    identifier_cusip=None,
                    identifier_sedol=None,
                    identifier_figi=None,
                    identifier_other=None,
                    currency="EUR",
                    asset_type=SimpleNamespace(value="ETF"),
                    quote_base_quantity=1,
                ),
            )
        elif entity is Broker:
            result.scalars.return_value = (
                SimpleNamespace(id=3, name="Position Broker"),
                SimpleNamespace(id=4, name="Inactive Scoped Broker"),
            )
        else:
            raise AssertionError(f"unexpected entity query: {entity}")
        return result

    session.execute.side_effect = _execute
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _EntityPayload,
        _EntityPayload(asset_id=7, broker_id=3),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    service = _service(session, (component,), (dataset,))

    response = await service.build_snapshot(41, _portfolio_dataset_request())

    assert [entry.broker_id for entry in response.entity_directory.brokers] == [3, 4]
    assert [entry.display_name for entry in response.entity_directory.brokers] == [
        "Position Broker",
        "Inactive Scoped Broker",
    ]


@pytest.mark.asyncio
async def test_analysis_selection_echoes_contract_and_required_manifest():
    session = _session_with_accessible_brokers([])
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _ValuePayload,
        _ValuePayload(value=1),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    analysis = _analysis(
        "portfolio.review",
        Domain.PORTFOLIO,
        ("portfolio.overview",),
    )
    service = _service(session, (component,), (dataset,), (analysis,))

    response = await service.build_snapshot(41, _portfolio_analysis_request())

    assert response.selection.kind == "analysis"
    assert response.analysis_contract is not None
    assert response.analysis_contract.response_contract_id == "portfolio.review.response"
    assert response.dataset_manifest[0].role == "required"


@pytest.mark.asyncio
async def test_prepare_request_rejects_catalog_selection_and_contract_mismatches():
    session = _session_with_accessible_brokers([])
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _ValuePayload,
        _ValuePayload(value=1),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    analysis = _analysis(
        "portfolio.review",
        Domain.PORTFOLIO,
        ("portfolio.overview",),
    )
    service = _service(session, (component,), (dataset,), (analysis,))

    catalog_mismatch = _portfolio_dataset_request().model_copy(update={"expected_catalog_version": 3})
    with pytest.raises(AiExportVersionMismatchError):
        await service.prepare_request(41, catalog_mismatch)

    unsupported = _portfolio_dataset_request().model_copy(
        update={
            "selection": AiExportDatasetSelection(
                kind="dataset",
                id="portfolio.unknown",
                version=1,
            )
        }
    )
    with pytest.raises(AiExportUnsupportedSelectionError):
        await service.prepare_request(41, unsupported)

    analysis_request = _portfolio_analysis_request()
    bad_selection = analysis_request.selection.model_copy(update={"response_contract_version": 2})
    with pytest.raises(AiExportVersionMismatchError):
        await service.prepare_request(
            41,
            analysis_request.model_copy(update={"selection": bad_selection}),
        )


@pytest.mark.asyncio
async def test_explicit_inaccessible_broker_scope_is_rejected_without_filtering():
    session = _session_with_accessible_brokers([1])
    component = _component(
        "portfolio.summary",
        Domain.PORTFOLIO,
        _ValuePayload,
        _ValuePayload(value=1),
    )
    dataset = _dataset(
        "portfolio.overview",
        Domain.PORTFOLIO,
        ("portfolio.summary",),
    )
    service = _service(session, (component,), (dataset,))
    request = _portfolio_dataset_request().model_copy(update={"broker_ids": [1, 2]})

    with pytest.raises(AiExportBrokerAccessDeniedError) as exc_info:
        await service.prepare_request(41, request)

    assert exc_info.value.denied_broker_ids == (2,)


@pytest.mark.asyncio
async def test_required_component_failure_and_missing_asset_are_typed():
    session = _session_with_accessible_brokers([])
    source_component = _component(
        "asset.identity",
        Domain.ASSET,
        _ValuePayload,
        error=RuntimeError("source unavailable"),
    )
    dataset = _dataset(
        "asset.overview",
        Domain.ASSET,
        ("asset.identity",),
    )
    source_service = _service(session, (source_component,), (dataset,))
    request = AiExportAssetSnapshotRequest(
        domain="asset",
        selection=AiExportDatasetSelection(
            kind="dataset",
            id="asset.overview",
            version=1,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": START, "end": END},
        target_currency="EUR",
        expected_catalog_version=2,
        asset_id=7,
    )

    with pytest.raises(AiExportSnapshotSourceError) as source_error:
        await source_service.build_snapshot(41, request)
    assert source_error.value.component_id == "asset.identity"

    missing_component = _component(
        "asset.identity",
        Domain.ASSET,
        _ValuePayload,
        error=AssetNotFoundError("missing"),
    )
    missing_service = _service(session, (missing_component,), (dataset,))
    with pytest.raises(AiExportEntityNotFoundError):
        await missing_service.build_snapshot(41, request)


@pytest.mark.asyncio
async def test_fx_exposure_analysis_with_empty_rows_is_not_applicable():
    session = _session_with_accessible_brokers([])
    exposure = _component(
        "fx.exposure_base_quote",
        Domain.FX,
        _RowsPayload,
        _RowsPayload(),
    )
    dataset = _dataset(
        "fx.direct_exposure",
        Domain.FX,
        ("fx.exposure_base_quote",),
    )
    analysis = _analysis(
        "fx.exposure_impact",
        Domain.FX,
        ("fx.direct_exposure",),
        applicability_code="requires_direct_exposure",
    )
    service = _service(session, (exposure,), (dataset,), (analysis,))
    request = {
        "domain": "fx",
        "selection": {
            "kind": "analysis",
            "id": "fx.exposure_impact",
            "version": 1,
            "instruction_template_id": "fx.exposure_impact.instructions",
            "instruction_template_version": 1,
            "response_contract_id": "fx.exposure_impact.response",
            "response_contract_version": 1,
        },
        "detail_level": "standard",
        "period": {"start": START, "end": END},
        "target_currency": "EUR",
        "expected_catalog_version": 2,
        "base_currency": "USD",
        "quote_currency": "EUR",
    }

    with pytest.raises(AiExportSelectionNotApplicableError) as exc_info:
        await service.build_snapshot(41, AiExportFxSnapshotRequest.model_validate(request))

    assert exc_info.value.reason_code == "no_direct_exposure"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "analysis_id",
        "applicability_code",
        "component_id",
        "output_model",
        "output",
        "reason_code",
    ),
    [
        (
            "asset.position_review",
            "requires_position",
            "asset.positions_by_broker",
            _PositionsPayload,
            _PositionsPayload(),
            "no_position",
        ),
    ],
)
async def test_asset_analysis_applicability_uses_real_component_payloads(
    analysis_id,
    applicability_code,
    component_id,
    output_model,
    output,
    reason_code,
):
    session = _session_with_accessible_brokers([])
    component = _component(
        component_id,
        Domain.ASSET,
        output_model,
        output,
    )
    dataset_id = "asset.position_performance" if analysis_id == "asset.position_review" else "asset.market_technical"
    dataset = _dataset(dataset_id, Domain.ASSET, (component_id,))
    analysis = _analysis(
        analysis_id,
        Domain.ASSET,
        (dataset_id,),
        applicability_code=applicability_code,
    )
    service = _service(session, (component,), (dataset,), (analysis,))
    request = AiExportAssetSnapshotRequest(
        domain="asset",
        selection=AiExportAnalysisSelection(
            kind="analysis",
            id=analysis_id,
            version=1,
            instruction_template_id=f"{analysis_id}.instructions",
            instruction_template_version=1,
            response_contract_id=f"{analysis_id}.response",
            response_contract_version=1,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": START, "end": END},
        target_currency="EUR",
        expected_catalog_version=2,
        asset_id=7,
    )

    with pytest.raises(AiExportSelectionNotApplicableError) as exc_info:
        await service.build_snapshot(41, request)

    assert exc_info.value.reason_code == reason_code


# =============================================================================
# FX partial history (requirement 7): history_coverage meta and reason_code
# =============================================================================


def _fx_request_with_catalog_v2(*, start: date, end: date) -> AiExportFxSnapshotRequest:
    return AiExportFxSnapshotRequest(
        domain="fx",
        selection=AiExportDatasetSelection(
            kind="dataset",
            id="fx.overview",
            version=1,
        ),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": start, "end": end},
        target_currency="EUR",
        expected_catalog_version=2,
        base_currency="USD",
        quote_currency="EUR",
    )


@pytest.mark.asyncio
async def test_fx_direct_exposure_does_not_force_rate_history_coverage():
    period_start = date(2026, 1, 1)
    period_end = date(2026, 3, 31)
    session = _session_with_accessible_brokers([])
    component = _component("fx.exposure_base_quote", Domain.FX, _RowsPayload, _RowsPayload())
    dataset = _dataset("fx.direct_exposure", Domain.FX, ("fx.exposure_base_quote",))
    service = _service(session, (component,), (dataset,))
    request = AiExportFxSnapshotRequest(
        domain="fx",
        selection=AiExportDatasetSelection(kind="dataset", id="fx.direct_exposure", version=1),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": period_start, "end": period_end},
        target_currency="EUR",
        expected_catalog_version=2,
        base_currency="USD",
        quote_currency="EUR",
    )

    original_load = rs_module.load_fx_rate_series

    async def _unexpected_load(context):
        raise AssertionError("fx.direct_exposure must not load base/quote rate history")

    rs_module.load_fx_rate_series = _unexpected_load
    try:
        response = await service.build_snapshot(41, request)
    finally:
        rs_module.load_fx_rate_series = original_load

    assert response.meta.history_coverage is None


@pytest.mark.asyncio
async def test_fx_snapshot_with_complete_history_has_no_history_coverage_warning():
    """When FX source history fully covers the requested period, meta.history_coverage
    must be None (no partial-history warning is surfaced)."""
    period_start = date(2026, 1, 1)
    period_end = date(2026, 3, 31)
    session = _session_with_accessible_brokers([])

    # Full coverage: history starts exactly at period_start
    full_observations = [
        FxRateObservation(
            requested_date=period_start + timedelta(days=i),
            actual_date=period_start + timedelta(days=i),
            rate=__import__("decimal").Decimal("1.10"),
            backward_filled=False,
        )
        for i in range((period_end - period_start).days + 1)
    ]
    full_series = FxRateSeriesResource.from_observations(full_observations)

    component = _component("fx.overview", Domain.FX, _ValuePayload, _ValuePayload(value=1))
    dataset = _dataset("fx.overview", Domain.FX, ("fx.overview",))
    service = _service(session, (component,), (dataset,))
    request = _fx_request_with_catalog_v2(start=period_start, end=period_end)

    original_load = rs_module.load_fx_rate_series

    async def _stub_load(context):
        return full_series

    rs_module.load_fx_rate_series = _stub_load
    try:
        response = await service.build_snapshot(41, request)
    finally:
        rs_module.load_fx_rate_series = original_load

    # Complete coverage → history_coverage must have complete=True and reason_code=None
    assert response.meta.history_coverage is not None
    assert response.meta.history_coverage.complete is True
    assert response.meta.history_coverage.reason_code is None


@pytest.mark.asyncio
async def test_fx_snapshot_with_partial_history_yields_coverage_and_reason():
    """When FX history starts mid-period, meta.history_coverage has calendar
    ratio < 1, reason_code='insufficient_source_history', and observed/backfill counts."""
    period_start = date(2025, 10, 1)  # 6M period
    period_end = date(2026, 3, 31)
    history_start = date(2026, 1, 1)  # data only from Jan → short history

    visible_range = range((period_end - history_start).days + 1)
    observations = []
    for i in visible_range:
        day = history_start + timedelta(days=i)
        is_bf = i % 7 == 6  # simulate ~1/7 backward-filled
        observations.append(
            FxRateObservation(
                requested_date=day,
                actual_date=(day - timedelta(days=1)) if is_bf else day,
                rate=decimal.Decimal("1.10"),
                backward_filled=is_bf,
            )
        )
    partial_series = FxRateSeriesResource.from_observations(observations)

    session = _session_with_accessible_brokers([])
    component = _component("fx.overview", Domain.FX, _ValuePayload, _ValuePayload(value=1))
    dataset = _dataset("fx.overview", Domain.FX, ("fx.overview",))
    service = _service(session, (component,), (dataset,))
    request = _fx_request_with_catalog_v2(start=period_start, end=period_end)

    original_load = rs_module.load_fx_rate_series

    async def _stub_load(context):
        return partial_series

    rs_module.load_fx_rate_series = _stub_load
    try:
        response = await service.build_snapshot(41, request)
    finally:
        rs_module.load_fx_rate_series = original_load

    coverage = response.meta.history_coverage
    assert coverage is not None
    assert coverage.complete is False
    assert coverage.reason_code == "insufficient_source_history"
    expected_requested_days = (period_end - period_start).days + 1
    expected_covered_days = (period_end - history_start).days + 1
    assert coverage.requested_calendar_days == expected_requested_days
    assert coverage.covered_calendar_days == expected_covered_days
    assert coverage.coverage_ratio == pytest.approx(expected_covered_days / expected_requested_days)
    assert coverage.observed_count + coverage.backward_filled_count == expected_covered_days


@pytest.mark.asyncio
async def test_fx_snapshot_source_error_propagates_reason_code():
    """A FxRateHistoryError with reason_code='fx_no_usable_rate' propagates through
    RequiredComponentBuildError to AiExportSnapshotSourceError.reason_code."""

    def _build_with_fx_error(context, dependencies):  # noqa: ARG001
        raise FxRateHistoryError(
            "fx_no_usable_rate",
            "no FX rate exists for USD->EUR on or before 2026-03-31",
        )

    component = ComponentSpec(
        component_id="fx.overview",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=_ValuePayload,
        builder=_build_with_fx_error,
        period_behavior=PeriodBehavior.WINDOWED,
    )
    session = _session_with_accessible_brokers([])
    dataset = _dataset("fx.overview", Domain.FX, ("fx.overview",))
    service = _service(session, (component,), (dataset,))
    request = _fx_request_with_catalog_v2(start=date(2026, 1, 1), end=date(2026, 3, 31))

    with pytest.raises(AiExportSnapshotSourceError) as exc_info:
        await service.build_snapshot(41, request)

    assert exc_info.value.component_id == "fx.overview"
    assert exc_info.value.reason_code == "fx_no_usable_rate"
