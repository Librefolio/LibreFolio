"""Focused ASGI tests for deterministic risk endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.risk import get_risk_service, router
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskError,
    RiskErrorCode,
    RiskQueryResponse,
    RiskResultStatus,
)
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskScopeNotFoundError,
    RiskService,
)

API_BASE = "/api/v1/risk"
USER_ID = 41


def app_with_service(
    service: RiskService,
    *,
    authenticated: bool,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if authenticated:

        async def current_user():
            return SimpleNamespace(id=USER_ID)

    else:

        async def current_user():
            raise HTTPException(status_code=401, detail="Not authenticated")

    def risk_service():
        return service

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_risk_service] = risk_service
    return app


def query_payload() -> dict[str, object]:
    return {
        "scope": {
            "kind": "asset_set",
            "asset_ids": [1, 2],
        },
        "date_range": {
            "start": "2026-01-01",
            "end": "2026-01-31",
        },
        "target_currency": "EUR",
        "mode": "historical",
        "analytics": [
            {
                "instance_id": "matrix",
                "analytic_code": "correlation",
            }
        ],
    }


@pytest.mark.asyncio
async def test_risk_catalog_requires_auth_and_lists_plugins():
    service = AsyncMock(spec=RiskService)
    unauthenticated = app_with_service(service, authenticated=False)
    authenticated = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=unauthenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/catalog")
        assert response.status_code == 401

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=authenticated),
        base_url="http://test",
    ) as client:
        response = await client.get(f"{API_BASE}/catalog")
        assert response.status_code == 200
        assert [item["analytic_code"] for item in response.json()["items"]] == [
            "comparison",
            "correlation",
            "historical_var",
            "portfolio_kpi",
            "risk_contribution",
            "stress",
        ]


@pytest.mark.asyncio
async def test_risk_query_delegates_authenticated_bulk_request():
    service = AsyncMock(spec=RiskService)
    service.execute.return_value = RiskQueryResponse(
        items=[
            RiskAnalyticResult(
                instance_id="matrix",
                analytic_code="correlation",
                status=RiskResultStatus.UNAVAILABLE,
                error=RiskError(
                    code=RiskErrorCode.INSUFFICIENT_HISTORY,
                    message="Not enough observations",
                ),
            )
        ]
    )
    app = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=query_payload(),
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "unavailable"
    service.execute.assert_awaited_once()
    call = service.execute.await_args.kwargs
    assert call["user_id"] == USER_ID
    assert call["request"].scope.kind.value == "asset_set"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (RiskScopeAccessError("Broker is not accessible"), 403),
        (RiskScopeNotFoundError("Asset does not exist"), 404),
    ],
)
async def test_risk_query_maps_scope_errors(error, status_code):
    service = AsyncMock(spec=RiskService)
    service.execute.side_effect = error
    app = app_with_service(service, authenticated=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=query_payload(),
        )

    assert response.status_code == status_code


@pytest.mark.asyncio
async def test_risk_query_rejects_invalid_discriminator_before_service():
    service = AsyncMock(spec=RiskService)
    app = app_with_service(service, authenticated=True)
    payload = query_payload()
    payload["scope"] = {"kind": "unknown"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"{API_BASE}/query",
            json=payload,
        )

    assert response.status_code == 422
    service.execute.assert_not_awaited()
