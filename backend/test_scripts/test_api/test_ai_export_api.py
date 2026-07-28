"""Focused ASGI tests for AI Export snapshot integration."""

import re
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.ai_export import get_ai_export_snapshot_service, router
from backend.app.api.v1.auth import get_current_user
from backend.app.db.session import get_session_generator
from backend.app.schemas.ai_export import (
    AiExportAssetSnapshotResponse,
    AiExportBrokerAccessDeniedProblem,
    AiExportBrokerSnapshotResponse,
    AiExportEntityNotFoundProblem,
    AiExportFxSnapshotResponse,
    AiExportPortfolioSnapshotResponse,
    AiExportProblem,
    AiExportProblemResponse,
    AiExportSnapshotResponse,
    AiExportSnapshotSourceFailureProblem,
    AiExportTaskNotApplicableProblem,
)
from backend.app.services.ai_export.assemblers import (
    AiExportEntityNotFoundError,
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
)
from backend.app.services.ai_export.service import AiExportSnapshotService

API_BASE = "/api/v1/ai-export"
USER_ID = 41
START = date(2026, 1, 1)
END = date(2026, 7, 26)


def _session_with_accessible_brokers(broker_ids: list[int]) -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = broker_ids
    session.execute.return_value = result
    return session


def _app(
    session: AsyncSession | None = None,
    *,
    authenticated: bool = False,
    service: AiExportSnapshotService | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if session is not None:

        async def override_session():
            yield session

        app.dependency_overrides[get_session_generator] = override_session

    if authenticated:

        async def override_current_user():
            return SimpleNamespace(id=USER_ID)

        app.dependency_overrides[get_current_user] = override_current_user

    if service is not None:

        def override_service():
            return service

        app.dependency_overrides[get_ai_export_snapshot_service] = override_service

    return app


def _portfolio_payload(broker_ids: list[int] | None = None) -> dict[str, object]:
    return {
        "domain": "portfolio",
        "task": "pac_planning",
        "detail_level": "standard",
        "date_range": {"start": "2026-01-01", "end": "2026-07-26"},
        "target_currency": "EUR",
        "broker_ids": broker_ids,
    }


def _asset_payload(
    *,
    task: str = "asset_snapshot",
    broker_ids: list[int] | None = None,
) -> dict[str, object]:
    return {
        "domain": "asset",
        "task": task,
        "detail_level": "compact",
        "date_range": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "asset_id": 7,
        "broker_ids": broker_ids,
    }


def _broker_payload(
    *,
    task: str = "broker_review",
    broker_id: int = 1,
) -> dict[str, object]:
    return {
        "domain": "broker",
        "task": task,
        "detail_level": "compact",
        "date_range": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "broker_id": broker_id,
    }


def _fx_payload(
    *,
    task: str = "fx_trend_review",
    broker_ids: list[int] | None = None,
) -> dict[str, object]:
    return {
        "domain": "fx",
        "task": task,
        "detail_level": "compact",
        "date_range": {"start": START.isoformat(), "end": END.isoformat()},
        "target_currency": "EUR",
        "base_currency": "EUR",
        "quote_currency": "USD",
        "broker_ids": broker_ids,
    }


def _response_base(domain: str, task: str, *, detail_level: str = "compact") -> dict[str, object]:
    return {
        "domain": domain,
        "task": task,
        "detail_level": detail_level,
        "meta": {
            "schema_version": 1,
            "profile_id": f"{domain}.{task}.{detail_level}",
            "profile_version": 1,
            "frontend_response_contract_id": f"{domain}.{task}",
            "frontend_response_contract_version": 1,
            "generated_at": datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
            "snapshot_as_of": END,
            "selected_range": {"start": START, "end": END},
            "target_currency": "EUR",
        },
        "methodology": {},
        "export_stats": {
            "canonical_json": {"serialized_characters": 0},
            "token_estimate": {
                "method": "chars_div_4_v1",
                "estimated_tokens": 0,
            },
        },
    }


def _money(amount: str = "0") -> dict[str, str]:
    return {"code": "EUR", "amount": amount}


def _portfolio_response() -> AiExportPortfolioSnapshotResponse:
    return AiExportPortfolioSnapshotResponse.model_validate(
        {
            **_response_base("portfolio", "pac_planning", detail_level="standard"),
            "facts": {
                "summary": {
                    "base_currency": "EUR",
                    "nav": _money(),
                    "market_value": _money(),
                    "cash": _money(),
                    "book_value": _money(),
                }
            },
        }
    )


def _asset_response() -> AiExportAssetSnapshotResponse:
    return AiExportAssetSnapshotResponse.model_validate(
        {
            **_response_base("asset", "asset_snapshot"),
            "facts": {
                "identity": {
                    "asset_id": 7,
                    "name": "Mock Asset",
                    "trading_currency": "USD",
                    "valuation_currency": "EUR",
                }
            },
        }
    )


def _fx_response() -> AiExportFxSnapshotResponse:
    return AiExportFxSnapshotResponse.model_validate(
        {
            **_response_base("fx", "fx_trend_review"),
            "facts": {
                "identity": {
                    "base_currency": "EUR",
                    "quote_currency": "USD",
                },
                "current_rate": {
                    "date": END,
                    "rate": "1.10",
                    "provider": "mock",
                },
            },
        }
    )


def _broker_response() -> AiExportBrokerSnapshotResponse:
    return AiExportBrokerSnapshotResponse.model_validate(
        {
            **_response_base("broker", "broker_review"),
            "facts": {
                "summary": {
                    "broker_id": 1,
                    "name": "Mock Broker",
                    "base_currency": "EUR",
                    "nav": _money(),
                    "market_value": _money(),
                    "cash": _money(),
                }
            },
        }
    )


def _assembler(*, result: object | None = None, error: Exception | None = None) -> MagicMock:
    assembler = MagicMock()
    assembler.assemble = AsyncMock(return_value=result, side_effect=error)
    return assembler


def _typed_problem(response: httpx.Response) -> AiExportProblem:
    envelope = AiExportProblemResponse.model_validate(response.json())
    return TypeAdapter(AiExportProblem).validate_python(envelope.detail)


@pytest.mark.asyncio
async def test_catalog_returns_exact_static_57_entry_contract():
    app = _app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"{API_BASE}/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["entries"]) == 57
    assert all("prompt" not in key and "label" not in key for entry in payload["entries"] for key in entry)


@pytest.mark.asyncio
async def test_snapshot_requires_authentication():
    session = _session_with_accessible_brokers([1])
    app = _app(session)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=_portfolio_payload([1]))

    assert response.status_code == 401
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "response_model", "assembler_name"),
    [
        (_portfolio_payload(broker_ids=[1]), _portfolio_response(), "portfolio"),
        (_asset_payload(broker_ids=[1]), _asset_response(), "asset"),
        (_fx_payload(broker_ids=[1]), _fx_response(), "fx"),
        (_broker_payload(broker_id=1), _broker_response(), "broker"),
    ],
)
async def test_authenticated_all_four_domains_succeed_via_mocked_assemblers(
    payload: dict[str, object],
    response_model: AiExportSnapshotResponse,
    assembler_name: str,
):
    session = _session_with_accessible_brokers([1])
    assembler = _assembler(result=response_model)
    service = AiExportSnapshotService(
        session,
        **{f"{assembler_name}_assembler": assembler},
    )
    app = _app(authenticated=True, service=service)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=payload)

    assert response.status_code == 200
    validated = TypeAdapter(AiExportSnapshotResponse).validate_python(response.json())
    assert isinstance(validated, type(response_model))
    assembler.assemble.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "assembler_name", "entity_type", "entity_id", "expected_reference"),
    [
        (
            _portfolio_payload(broker_ids=[1]),
            "portfolio",
            "portfolio",
            "all",
            {"kind": "portfolio"},
        ),
        (
            _asset_payload(broker_ids=[1]),
            "asset",
            "asset",
            7,
            {"kind": "asset", "asset_id": 7},
        ),
        (
            _broker_payload(broker_id=1),
            "broker",
            "broker",
            1,
            {"kind": "broker", "broker_id": 1},
        ),
    ],
)
async def test_entity_not_found_mapping_includes_portfolio_and_broker(
    payload: dict[str, object],
    assembler_name: str,
    entity_type: str,
    entity_id: int | str,
    expected_reference: dict[str, object],
):
    session = _session_with_accessible_brokers([1])
    assembler = _assembler(
        error=AiExportEntityNotFoundError(
            entity_type,
            entity_id,
            context={"account_number": "SECRET-ACCOUNT"},
        )
    )
    service = AiExportSnapshotService(
        session,
        **{f"{assembler_name}_assembler": assembler},
    )
    app = _app(authenticated=True, service=service)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=payload)

    assert response.status_code == 404
    problem = _typed_problem(response)
    assert isinstance(problem, AiExportEntityNotFoundProblem)
    assert problem.entity_reference.model_dump(mode="json", exclude_none=True) == expected_reference
    assert "SECRET-ACCOUNT" not in response.text
    assert f"{entity_type} {entity_id} was not found" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "assembler_name", "applicability_code", "reason_code"),
    [
        (
            _asset_payload(task="position_review", broker_ids=[1]),
            "asset",
            "positive_open_quantity_in_scope",
            "no_positive_open_position",
        ),
        (
            _fx_payload(task="fx_exposure_impact", broker_ids=[1]),
            "fx",
            "linked_cash_or_position_available",
            "no_linked_exposure",
        ),
        (
            _portfolio_payload(broker_ids=[1]),
            "portfolio",
            "portfolio_has_eligible_positions",
            "no_eligible_positions",
        ),
        (
            _broker_payload(task="broker_review", broker_id=1),
            "broker",
            "broker_has_activity",
            "no_broker_activity",
        ),
    ],
)
async def test_not_applicable_mapping_includes_portfolio_and_broker(
    payload: dict[str, object],
    assembler_name: str,
    applicability_code: str,
    reason_code: str,
):
    session = _session_with_accessible_brokers([1])
    assembler = _assembler(
        error=AiExportTaskNotApplicableError(
            applicability_code,
            reason_code,
            context={"account_number": "SECRET-ACCOUNT"},
        )
    )
    service = AiExportSnapshotService(
        session,
        **{f"{assembler_name}_assembler": assembler},
    )
    app = _app(authenticated=True, service=service)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=payload)

    assert response.status_code == 409
    problem = _typed_problem(response)
    assert isinstance(problem, AiExportTaskNotApplicableProblem)
    assert problem.applicability_code == applicability_code
    assert problem.reason_code == reason_code
    assert "SECRET-ACCOUNT" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "assembler_name", "source_code"),
    [
        (_portfolio_payload(broker_ids=[1]), "portfolio", "portfolio_service"),
        (_asset_payload(broker_ids=[1]), "asset", "asset_source"),
        (_fx_payload(broker_ids=[1]), "fx", "fx_service"),
        (_broker_payload(broker_id=1), "broker", "broker_service"),
    ],
)
async def test_source_failure_mapping_includes_portfolio_and_broker(
    payload: dict[str, object],
    assembler_name: str,
    source_code: str,
):
    session = _session_with_accessible_brokers([1])
    assembler = _assembler(
        error=AiExportSourceFailureError(
            source_code,
            "load_snapshot",
            retryable=True,
            context={"account_number": "SECRET-ACCOUNT"},
        )
    )
    service = AiExportSnapshotService(
        session,
        **{f"{assembler_name}_assembler": assembler},
    )
    app = _app(authenticated=True, service=service)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=payload)

    assert response.status_code == 503
    problem = _typed_problem(response)
    assert isinstance(problem, AiExportSnapshotSourceFailureProblem)
    assert problem.source_code == f"{source_code}.load_snapshot"
    assert re.fullmatch(r"[a-z][a-z0-9_.-]*", problem.source_code)
    assert problem.retryable is True
    assert "SECRET-ACCOUNT" not in response.text
    assert "AI Export source failed" not in response.text


@pytest.mark.asyncio
async def test_inaccessible_brokers_return_typed_403_without_silent_filtering():
    session = _session_with_accessible_brokers([1, 5])
    app = _app(session, authenticated=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{API_BASE}/snapshot", json=_portfolio_payload([5, 4, 1, 3]))

    assert response.status_code == 403
    problem = _typed_problem(response)
    assert isinstance(problem, AiExportBrokerAccessDeniedProblem)
    assert problem.denied_broker_ids == [3, 4]
    assert "facts" not in response.json()
    session.execute.assert_awaited_once()


def test_openapi_declares_unchanged_snapshot_and_problem_response_models():
    schema = _app().openapi()
    responses = schema["paths"][f"{API_BASE}/snapshot"]["post"]["responses"]
    success_schema = responses["200"]["content"]["application/json"]["schema"]
    expected_mapping = {
        "portfolio": "#/components/schemas/AiExportPortfolioSnapshotResponse",
        "asset": "#/components/schemas/AiExportAssetSnapshotResponse",
        "fx": "#/components/schemas/AiExportFxSnapshotResponse",
        "broker": "#/components/schemas/AiExportBrokerSnapshotResponse",
    }

    assert success_schema["oneOf"] == [{"$ref": reference} for reference in expected_mapping.values()]
    assert success_schema["discriminator"] == {
        "propertyName": "domain",
        "mapping": expected_mapping,
    }

    for status in ("403", "404", "409", "422", "503"):
        response_schema = responses[status]["content"]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/AiExportProblemResponse"}
