"""Contracts for the component-based public AI Export v1 API."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.ai_export_runtime import (
    AiExportCatalogResponse,
    AiExportDatasetCatalogEntry,
    AiExportDatasetManifestEntry,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportManifestRole,
    AiExportPeriodSemantics,
    AiExportProblem,
    AiExportSectionEnvelope,
    AiExportSnapshotMeta,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotStats,
)

START = date(2026, 1, 1)
END = date(2026, 3, 31)


def _dataset_selection(domain: str = "portfolio") -> dict[str, object]:
    return {
        "kind": "dataset",
        "id": f"{domain}.overview",
        "version": 1,
    }


def _analysis_selection(domain: str = "asset") -> dict[str, object]:
    return {
        "kind": "analysis",
        "id": f"{domain}.trend_analysis",
        "version": 1,
        "instruction_template_id": f"{domain}.trend_analysis.instructions",
        "instruction_template_version": 1,
        "response_contract_id": f"{domain}.trend_analysis.response",
        "response_contract_version": 1,
    }


def _request_payload(domain: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "domain": domain,
        "selection": (_analysis_selection(domain) if domain == "asset" else _dataset_selection(domain)),
        "detail_level": "standard",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "expected_catalog_version": 1,
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
        version=1,
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

    assert catalog.schema_version == 1
    assert catalog.catalog_version == 1
    assert "prompt" not in serialized.lower()
    assert "web_research" not in serialized.lower()


def test_snapshot_response_accepts_json_sections_and_enforces_stats():
    selection = AiExportDatasetSelection(
        kind="dataset",
        id="portfolio.overview",
        version=1,
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
                dataset_version=1,
                role=AiExportManifestRole.SELECTED,
            ),
        ),
        sections=(section,),
        stats=AiExportSnapshotStats(
            dataset_count=1,
            section_count=1,
            serialized_characters=100,
            estimated_tokens=25,
        ),
    )

    assert response.sections[0].payload == {"nav": 100.0}
    invalid = response.model_dump(mode="python")
    invalid["stats"]["section_count"] = 2
    with pytest.raises(ValidationError, match="section_count"):
        AiExportSnapshotResponse.model_validate(invalid)


def test_analysis_selection_requires_complete_contract_identity():
    payload = _request_payload("asset")
    selection = dict(payload["selection"])
    selection.pop("response_contract_version")
    payload["selection"] = selection

    with pytest.raises(ValidationError, match="response_contract_version"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)
