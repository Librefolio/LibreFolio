"""API tests for the domain-agnostic signal preview endpoint.

The chart-settings preview (global mode) computes backend indicators on a
synthetic curve supplied in the request body — no stored/DB data is involved.
"""

from __future__ import annotations

import time
import uuid
from datetime import date, timedelta

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.signals import SignalPreviewResponse
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
PREVIEW_URL = f"{API_BASE}/signals/preview"
TIMEOUT = 30.0


def _synthetic_points(count: int = 40) -> list[dict]:
    start = date(2024, 1, 1)
    return [{"date": (start + timedelta(days=index)).isoformat(), "value": 100 + (index % 5)} for index in range(count)]


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    username = f"signal_preview_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    password = "TestPass123!"
    register = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": password},
        timeout=TIMEOUT,
    )
    assert register.status_code == 201
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200
    session = login.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.mark.asyncio
async def test_signal_preview_requires_authentication(test_server):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PREVIEW_URL,
            json={"domain": "asset", "points": _synthetic_points(5), "signals": []},
            timeout=TIMEOUT,
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signal_preview_computes_backend_indicator(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            PREVIEW_URL,
            json={
                "domain": "asset",
                "points": _synthetic_points(40),
                "signals": [{"instance_id": "sma-1", "signal_code": "SMA", "params": {"period": 5}}],
            },
            timeout=TIMEOUT,
        )
    assert response.status_code == 200
    payload = SignalPreviewResponse.model_validate(response.json())
    assert len(payload.signals) == 1
    result = payload.signals[0]
    assert result.instance_id == "sma-1"
    assert result.signal_code == "SMA"
    # After the 5-point warm-up the SMA produces a value series.
    assert result.series
    assert any(point.value is not None for point in result.series[0].points)


@pytest.mark.asyncio
async def test_signal_preview_fx_domain_computes(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            PREVIEW_URL,
            json={
                "domain": "fx",
                "points": _synthetic_points(30),
                "signals": [{"instance_id": "ema-1", "signal_code": "EMA", "params": {"period": 10}}],
            },
            timeout=TIMEOUT,
        )
    assert response.status_code == 200
    payload = SignalPreviewResponse.model_validate(response.json())
    assert len(payload.signals) == 1
    assert payload.signals[0].signal_code == "EMA"


@pytest.mark.asyncio
async def test_signal_preview_empty_signals_returns_empty(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            PREVIEW_URL,
            json={"domain": "asset", "points": _synthetic_points(10), "signals": []},
            timeout=TIMEOUT,
        )
    assert response.status_code == 200
    payload = SignalPreviewResponse.model_validate(response.json())
    assert payload.signals == []


@pytest.mark.asyncio
async def test_signal_preview_no_points_returns_empty(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            PREVIEW_URL,
            json={
                "domain": "asset",
                "points": [],
                "signals": [{"instance_id": "sma-1", "signal_code": "SMA", "params": {"period": 5}}],
            },
            timeout=TIMEOUT,
        )
    assert response.status_code == 200
    payload = SignalPreviewResponse.model_validate(response.json())
    assert payload.signals == []
