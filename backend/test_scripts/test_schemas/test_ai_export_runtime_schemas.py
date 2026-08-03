"""Contracts for the component-based public AI Export V2 API."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.ai_export_runtime import (
    AiExportAssetDirectoryEntry,
    AiExportBrokerDirectoryEntry,
    AiExportCatalogResponse,
    AiExportDatasetCatalogEntry,
    AiExportDatasetManifestEntry,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportEntityDirectory,
    AiExportEventSelectionManifest,
    AiExportFxPairDirectoryEntry,
    AiExportHistoryCoverage,
    AiExportIndicatorSamplingPolicy,
    AiExportManifestRole,
    AiExportPeriod,
    AiExportPeriodSemantics,
    AiExportPriceSamplingPolicy,
    AiExportProblem,
    AiExportSectionEnvelope,
    AiExportSnapshotMeta,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotSourceFailureProblem,
    AiExportSnapshotStats,
    AiExportTechnicalSamplingManifest,
)
from backend.app.schemas.signals import SignalTemporalClass

START = date(2026, 1, 1)
END = date(2026, 3, 31)


def _dataset_selection(domain: str = "portfolio") -> dict[str, object]:
    return {
        "kind": "dataset",
        "id": f"{domain}.overview",
        "version": 2,
    }


def _analysis_selection(domain: str = "asset") -> dict[str, object]:
    return {
        "kind": "analysis",
        "id": f"{domain}.trend_analysis",
        "version": 2,
        "instruction_template_id": f"{domain}.trend_analysis.instructions",
        "instruction_template_version": 2,
        "response_contract_id": f"{domain}.trend_analysis.response",
        "response_contract_version": 2,
    }


def _request_payload(domain: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "domain": domain,
        "selection": (_analysis_selection(domain) if domain == "asset" else _dataset_selection(domain)),
        "detail_level": "standard",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "expected_catalog_version": 2,
    }
    if domain == "broker":
        payload["broker_id"] = 3
    elif domain == "asset":
        payload["asset_id"] = 7
    elif domain == "fx":
        payload["base_currency"] = "USD"
        payload["quote_currency"] = "EUR"
    return payload


@pytest.mark.parametrize("domain", ["portfolio", "broker", "asset", "fx"])
def test_snapshot_request_discriminates_all_four_domains(domain: str):
    request = TypeAdapter(AiExportSnapshotRequest).validate_python(_request_payload(domain))

    assert request.domain == domain
    assert request.period.end == END


def test_snapshot_request_rejects_legacy_task_windows_and_web_flags():
    payload = _request_payload("portfolio")
    payload["task"] = "pac_planning"
    payload["technical_window"] = {
        "start": START.isoformat(),
        "end": END.isoformat(),
    }
    payload["supports_web_research"] = True

    with pytest.raises(ValidationError, match="extra_forbidden"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_snapshot_request_requires_period_end_and_matching_domain_selection():
    missing_end = _request_payload("portfolio")
    missing_end["period"] = {"start": START.isoformat()}
    with pytest.raises(ValidationError, match="end"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(missing_end)

    wrong_domain = _request_payload("portfolio")
    wrong_domain["selection"] = _dataset_selection("broker")
    with pytest.raises(ValidationError, match="selection id must belong"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(wrong_domain)


def test_optional_broker_scope_is_clean_array_and_rejects_explicit_empty_or_null():
    omitted = TypeAdapter(AiExportSnapshotRequest).validate_python(_request_payload("portfolio"))
    assert omitted.broker_ids == []

    for invalid in ([], None):
        payload = _request_payload("portfolio")
        payload["broker_ids"] = invalid
        with pytest.raises(ValidationError, match="broker_ids"):
            TypeAdapter(AiExportSnapshotRequest).validate_python(payload)

    payload = _request_payload("portfolio")
    payload["broker_ids"] = [3, 1]
    scoped = TypeAdapter(AiExportSnapshotRequest).validate_python(payload)
    assert scoped.broker_ids == [1, 3]


def test_request_and_problem_unions_publish_discriminators():
    request_schema = TypeAdapter(AiExportSnapshotRequest).json_schema()
    problem_schema = TypeAdapter(AiExportProblem).json_schema()

    assert request_schema["discriminator"]["propertyName"] == "domain"
    assert problem_schema["discriminator"]["propertyName"] == "code"


def test_catalog_separates_datasets_and_analyses_without_prompt_text():
    dataset = AiExportDatasetCatalogEntry(
        kind="dataset",
        id="portfolio.overview",
        version=2,
        domain=AiExportDomain.PORTFOLIO,
        display_i18n_key="aiExport.dataset.portfolio.overview.display",
        description_i18n_key="aiExport.dataset.portfolio.overview.description",
        icon="layout-dashboard",
        applicability_code="always_applicable",
        applicable_pages=("dashboard",),
        supported_detail_levels=tuple(AiExportDetailLevel),
        period_semantics=AiExportPeriodSemantics.AS_OF,
        required_component_ids=("portfolio.summary",),
        optional_component_ids=(),
    )
    catalog = AiExportCatalogResponse(
        datasets=(dataset,),
        analyses=(),
    )
    serialized = catalog.model_dump_json()

    assert catalog.schema_version == 2
    assert catalog.catalog_version == 2
    assert "prompt" not in serialized.lower()
    assert "web_research" not in serialized.lower()


def test_snapshot_response_accepts_json_sections_and_enforces_stats():
    selection = AiExportDatasetSelection(
        kind="dataset",
        id="portfolio.overview",
        version=2,
    )
    section = AiExportSectionEnvelope(
        component_id="portfolio.summary",
        component_version=1,
        schema_id="portfolio.summary",
        schema_version=1,
        payload={"nav": 100.0},
    )
    response = AiExportSnapshotResponse(
        domain=AiExportDomain.PORTFOLIO,
        selection=selection,
        detail_level=AiExportDetailLevel.STANDARD,
        target={"kind": "portfolio"},
        meta=AiExportSnapshotMeta(
            request_id="req-1",
            generated_at=datetime(2026, 3, 31, tzinfo=UTC),
            snapshot_as_of=END,
            exported_period={"start": START, "end": END},
            calculation_range=None,
            target_currency="EUR",
        ),
        dataset_manifest=(
            AiExportDatasetManifestEntry(
                dataset_id="portfolio.overview",
                dataset_version=2,
                role=AiExportManifestRole.SELECTED,
            ),
        ),
        sections=(section,),
        stats=AiExportSnapshotStats(
            dataset_count=1,
            section_count=1,
            serialized_characters=100,
            serialized_bytes=100,
            estimated_tokens=25,
        ),
    )

    assert response.sections[0].payload == {"nav": 100.0}
    invalid = response.model_dump(mode="python")
    invalid["stats"]["section_count"] = 2
    with pytest.raises(ValidationError, match="section_count"):
        AiExportSnapshotResponse.model_validate(invalid)


def test_sampling_manifests_are_strict_deduplicated_v1_contracts():
    price = AiExportPriceSamplingPolicy(
        bucket_count=75,
    )
    indicator = AiExportIndicatorSamplingPolicy(
        signal_instance_id="ema_20",
        signal_code="EMA",
        temporal_class=SignalTemporalClass.MEDIUM,
        bucket_count=51,
    )
    manifest = AiExportTechnicalSamplingManifest(
        detail_level="full",
        price_policy=price,
        indicator_policies=(indicator,),
        indicator_history_row_limit=None,
    )
    event_policy = AiExportEventSelectionManifest()

    assert manifest.detail_level == "full"
    assert manifest.price_policy.bucket_count == 75
    assert manifest.indicator_policies[0].temporal_class == "medium"
    assert manifest.model_dump(mode="json") == {
        "detail_level": "full",
        "price_policy": {"bucket_count": 75},
        "indicator_policies": [
            {
                "signal_instance_id": "ema_20",
                "signal_code": "EMA",
                "temporal_class": "medium",
                "bucket_count": 51,
            }
        ],
        "indicator_history_row_limit": None,
    }
    assert event_policy.grouped_by == ("entity_id", "annotation_key")

    with pytest.raises(ValidationError, match="unique signal_instance_id"):
        AiExportTechnicalSamplingManifest(
            detail_level="full",
            indicator_policies=(indicator, indicator),
            indicator_history_row_limit=None,
        )
    with pytest.raises(ValidationError, match="price or indicator policy"):
        AiExportTechnicalSamplingManifest(
            detail_level="full",
            indicator_history_row_limit=None,
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AiExportPriceSamplingPolicy.model_validate(
            {
                "bucket_count": 75,
                "p": 2,
                "m": 30,
                "k": 7,
            }
        )
    with pytest.raises(ValidationError):
        AiExportEventSelectionManifest(
            minimum_latest_events_per_annotation=0,
        )


def test_entity_directory_is_sorted_unique_and_carries_minimal_identity():
    directory = AiExportEntityDirectory(
        assets=(
            AiExportAssetDirectoryEntry(
                asset_id=7,
                display_name="Named Asset",
                ticker="NAMED",
                isin="IT0000000007",
                other_identifiers=("provider:7",),
                currency="EUR",
                asset_type="ETF",
                quote_base_quantity=100,
            ),
        ),
        brokers=(
            AiExportBrokerDirectoryEntry(
                broker_id=3,
                display_name="Named Broker",
            ),
        ),
        fx_pairs=(
            AiExportFxPairDirectoryEntry(
                base_currency="EUR",
                quote_currency="USD",
            ),
        ),
    )

    assert directory.assets[0].quote_base_quantity == 100
    assert directory.assets[0].other_identifiers == ("provider:7",)
    assert directory.brokers[0].display_name == "Named Broker"
    assert directory.fx_pairs[0].base_currency == "EUR"

    with pytest.raises(ValidationError, match="unique and sorted"):
        AiExportEntityDirectory(
            assets=(directory.assets[0], directory.assets[0]),
        )


def test_analysis_selection_requires_complete_contract_identity():
    payload = _request_payload("asset")
    selection = dict(payload["selection"])
    selection.pop("response_contract_version")
    payload["selection"] = selection

    with pytest.raises(ValidationError, match="response_contract_version"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_fx_history_coverage_validates_calendar_ratio_and_reason_code():
    """V2: AiExportHistoryCoverage carries observed/backfilled counts,
    calendar-day ratio, and an optional reason_code for partial history."""
    complete = AiExportHistoryCoverage(
        requested_period=AiExportPeriod(start=date(2026, 1, 1), end=date(2026, 3, 31)),
        available_period=AiExportPeriod(start=date(2026, 1, 1), end=date(2026, 3, 31)),
        requested_calendar_days=90,
        covered_calendar_days=90,
        coverage_ratio=1.0,
        complete=True,
        reason_code=None,
        observed_count=80,
        backward_filled_count=10,
        earliest_source_date=date(2025, 6, 1),
    )
    assert complete.complete is True
    assert complete.reason_code is None
    assert complete.coverage_ratio == pytest.approx(1.0)

    partial = AiExportHistoryCoverage(
        requested_period=AiExportPeriod(start=date(2025, 10, 1), end=date(2026, 3, 31)),
        available_period=AiExportPeriod(start=date(2026, 1, 1), end=date(2026, 3, 31)),
        requested_calendar_days=182,
        covered_calendar_days=90,
        coverage_ratio=90 / 182,
        complete=False,
        reason_code="insufficient_source_history",
        observed_count=80,
        backward_filled_count=10,
        earliest_source_date=date(2026, 1, 1),
    )
    assert partial.complete is False
    assert partial.reason_code == "insufficient_source_history"
    assert partial.coverage_ratio == pytest.approx(90 / 182)


def test_fx_history_coverage_rejects_mismatched_complete_and_reason_code():
    with pytest.raises(ValidationError, match="reason_code must be absent only for complete coverage"):
        AiExportHistoryCoverage(
            requested_period=AiExportPeriod(start=date(2026, 1, 1), end=date(2026, 3, 31)),
            available_period=AiExportPeriod(start=date(2026, 1, 1), end=date(2026, 3, 31)),
            requested_calendar_days=90,
            covered_calendar_days=90,
            coverage_ratio=1.0,
            complete=True,
            reason_code="insufficient_source_history",  # must be None when complete=True
            observed_count=80,
            backward_filled_count=10,
            earliest_source_date=date(2025, 6, 1),
        )


def test_snapshot_source_failure_problem_carries_optional_reason_code():
    """V2: AiExportSnapshotSourceFailureProblem includes an optional reason_code
    that surfaces machine-readable FX or component failure details."""
    base_kwargs = {
        "code": "snapshot_source_failure",
        "message": "A required AI Export component is unavailable.",
        "domain": "fx",
        "selection_kind": "dataset",
        "selection_id": "fx.overview",
        "detail_level": "standard",
        "component_id": "fx.technical_coverage",
        "retryable": False,
    }

    without_reason = AiExportSnapshotSourceFailureProblem(**base_kwargs, reason_code=None)
    assert without_reason.reason_code is None

    with_reason = AiExportSnapshotSourceFailureProblem(**base_kwargs, reason_code="fx_no_usable_rate")
    assert with_reason.reason_code == "fx_no_usable_rate"
    serialized = with_reason.model_dump(mode="json")
    assert serialized["reason_code"] == "fx_no_usable_rate"
