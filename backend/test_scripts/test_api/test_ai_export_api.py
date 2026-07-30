"""Focused ASGI tests for the component-based AI Export v1 API."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import TypeAdapter

from backend.app.api.v1.ai_export import get_ai_export_snapshot_service, router
from backend.app.api.v1.auth import get_current_user
from backend.app.schemas.ai_export_runtime import (
    AiExportProblem,
    AiExportProblemResponse,
    AiExportSnapshotResponse,
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

API_BASE = "/api/v1/ai-export"
USER_ID = 41
START = date(2026, 1, 1)
END = date(2026, 3, 31)


def _app(*, authenticated: bool = False, service=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if authenticated:

        async def override_current_user():
            return SimpleNamespace(id=USER_ID)

        app.dependency_overrides[get_current_user] = override_current_user

    if service is not None:

        def override_service():
            return service

        app.dependency_overrides[get_ai_export_snapshot_service] = override_service

    return app


def _dataset_selection(domain: str) -> dict[str, object]:
    return {
        "kind": "dataset",
        "id": f"{domain}.overview",
        "version": 1,
    }


def _payload(domain: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "domain": domain,
        "selection": _dataset_selection(domain),
        "detail_level": "standard",
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "expected_catalog_version": 1,
    }
    if domain == "broker":
        payload["broker_id"] = 1
    elif domain == "asset":
        payload["asset_id"] = 7
    elif domain == "fx":
        payload["base_currency"] = "USD"
        payload["quote_currency"] = "EUR"
    return payload


def _target(domain: str) -> dict[str, object]:
    if domain == "portfolio":
        return {"kind": "portfolio"}
    if domain == "broker":
        return {"kind": "broker", "broker_id": 1}
    if domain == "asset":
        return {"kind": "asset", "asset_id": 7}
    return {
        "kind": "fx_pair",
        "base_currency": "USD",
        "quote_currency": "EUR",
    }


def _response(domain: str) -> AiExportSnapshotResponse:
    component_id = {
        "portfolio": "portfolio.summary",
        "broker": "broker.summary",
        "asset": "asset.identity",
        "fx": "fx.pair_identity",
    }[domain]
    return AiExportSnapshotResponse.model_validate(
        {
            "domain": domain,
            "selection": _dataset_selection(domain),
            "detail_level": "standard",
            "target": _target(domain),
            "meta": {
                "request_id": f"req-{domain}",
                "generated_at": datetime(2026, 3, 31, tzinfo=UTC),
                "snapshot_as_of": END,
                "exported_period": {"start": START, "end": END},
                "calculation_range": None,
                "warmup_policy": "component_owned",
                "earliest_calculation_date": None,
                "target_currency": "EUR",
            },
            "dataset_manifest": [
                {
                    "dataset_id": f"{domain}.overview",
                    "dataset_version": 1,
                    "role": "selected",
                }
            ],
            "sections": [
                {
                    "component_id": component_id,
                    "component_version": 1,
                    "schema_id": component_id,
                    "schema_version": 1,
                    "payload": {"ok": True},
                }
            ],
            "stats": {
                "dataset_count": 1,
                "section_count": 1,
                "serialized_characters": 100,
                "estimated_tokens": 25,
                "token_estimation_method": "chars_div_4_v1",
            },
        }
    )


def _service(*, result=None, error: BaseException | None = None):
    service = MagicMock(spec=AiExportSnapshotService)
    service.build_snapshot = AsyncMock(return_value=result, side_effect=error)
    return service


def _typed_problem(response: httpx.Response) -> AiExportProblem:
    envelope = AiExportProblemResponse.model_validate(response.json())
    return TypeAdapter(AiExportProblem).validate_python(envelope.detail)


@pytest.mark.asyncio
async def test_catalog_returns_18_datasets_and_17_analyses():
    app = _app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["catalog_version"] == 1
    assert len(payload["datasets"]) == 18
    assert len(payload["analyses"]) == 17
    serialized = json.dumps(payload).lower()
    assert "prompt" not in serialized
    assert "web_research" not in serialized


@pytest.mark.asyncio
async def test_snapshot_requires_authentication():
    app = _app(service=_service(result=_response("portfolio")))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/snapshot",
            json=_payload("portfolio"),
        )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["portfolio", "broker", "asset", "fx"])
async def test_authenticated_four_domains_return_new_snapshot_contract(domain: str):
    expected = _response(domain)
    service = _service(result=expected)
    app = _app(authenticated=True, service=service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/snapshot",
            json=_payload(domain),
        )

    assert response.status_code == 200
    validated = AiExportSnapshotResponse.model_validate(response.json())
    assert validated.domain == domain
    assert validated.selection.kind == "dataset"
    service.build_snapshot.assert_awaited_once()
    assert service.build_snapshot.await_args.args[0] == USER_ID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (
            AiExportBrokerAccessDeniedError((3, 2)),
            403,
            "broker_access_denied",
        ),
        (AiExportEntityNotFoundError("missing"), 404, "entity_not_found"),
        (
            AiExportVersionMismatchError(
                "selection.version",
                expected=1,
                actual=2,
            ),
            409,
            "version_mismatch",
        ),
        (
            AiExportUnsupportedSelectionError("portfolio.unknown"),
            422,
            "unsupported_selection",
        ),
        (
            AiExportSelectionNotApplicableError(
                "requires_position",
                "no_position",
            ),
            422,
            "selection_not_applicable",
        ),
        (
            AiExportSnapshotSourceError(
                "portfolio.summary",
                retryable=False,
            ),
            503,
            "snapshot_source_failure",
        ),
    ],
)
async def test_typed_problem_mapping(error, status_code: int, code: str):
    app = _app(authenticated=True, service=_service(error=error))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/snapshot",
            json=_payload("portfolio"),
        )

    assert response.status_code == status_code
    problem = _typed_problem(response)
    assert problem.code == code
    assert problem.selection_id == "portfolio.overview"


@pytest.mark.asyncio
async def test_legacy_task_payload_is_rejected_by_public_v1_contract():
    payload = _payload("portfolio")
    payload["task"] = "pac_planning"
    payload["date_range"] = payload.pop("period")
    app = _app(
        authenticated=True,
        service=_service(result=_response("portfolio")),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"{API_BASE}/snapshot", json=payload)

    assert response.status_code == 422


def test_openapi_declares_new_discriminators_and_typed_problem_statuses():
    schema = _app().openapi()
    operation = schema["paths"][f"{API_BASE}/snapshot"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]

    assert request_schema["discriminator"]["propertyName"] == "domain"
    assert {"403", "404", "409", "422", "503"} <= set(operation["responses"])
    schema_text = json.dumps(schema)
    assert '"AiExportDatasetSelection"' in schema_text
    assert '"AiExportAnalysisSelection"' in schema_text
    assert '"task"' not in json.dumps(request_schema)
