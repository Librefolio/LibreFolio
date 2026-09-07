"""Live API tests for Asset price-query signal integration."""

from __future__ import annotations

import time
import uuid
from datetime import date, timedelta

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(
    client: httpx.AsyncClient,
) -> None:
    username = f"asset_signal_{int(time.time() * 1000)}_" f"{uuid.uuid4().hex[:6]}"
    password = "TestPass123!"
    register = await client.post(
        f"{API_BASE}/auth/register",
        json={
            "username": username,
            "email": f"{username}@test.com",
            "password": password,
        },
        timeout=TIMEOUT,
    )
    assert register.status_code == 201
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={
            "username": username,
            "password": password,
        },
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


async def create_asset_with_prices(
    client: httpx.AsyncClient,
) -> tuple[int, date, date]:
    create = await client.post(
        f"{API_BASE}/assets",
        json=[
            {
                "display_name": (f"Signal API Asset {uuid.uuid4().hex[:8]}"),
                "currency": "EUR",
                "asset_type": "STOCK",
            }
        ],
        timeout=TIMEOUT,
    )
    assert create.status_code == 201
    asset_id = create.json()["results"][0]["asset_id"]

    start = date(2025, 1, 1)
    end = start + timedelta(days=149)
    prices = []
    for offset in range(150):
        close = 100 + offset
        prices.append(
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "open": str(close - 0.5),
                "high": str(close + 1),
                "low": str(close - 1),
                "close": str(close),
                "volume": str(1000 + offset),
            }
        )
    upsert = await client.post(
        f"{API_BASE}/assets/prices",
        json=[
            {
                "asset_id": asset_id,
                "prices": prices,
            }
        ],
        timeout=TIMEOUT,
    )
    assert upsert.status_code == 200
    return asset_id, start, end


@pytest.mark.asyncio
async def test_asset_signal_query_end_to_end(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, start, end = await create_asset_with_prices(client)
        visible_start = end - timedelta(days=29)

        legacy = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {
                        "start": visible_start.isoformat(),
                        "end": end.isoformat(),
                    },
                }
            ],
            timeout=TIMEOUT,
        )
        signal_only = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {
                        "start": visible_start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "include_price": False,
                    "signals": [
                        {
                            "instance_id": "invalid",
                            "signal_code": "EMA",
                            "params": {"period": 1},
                        },
                        {
                            "instance_id": "ema",
                            "signal_code": "EMA",
                            "params": {"period": 14},
                        },
                    ],
                    "annotation_requests": [
                        {
                            "kind": "threshold_crossing",
                            "key": "price-threshold",
                            "attach_to_instance_id": "ema",
                            "source": {
                                "kind": "price",
                                "field": "close",
                            },
                            "threshold": 225,
                        }
                    ],
                }
            ],
            timeout=TIMEOUT,
        )

    assert legacy.status_code == 200
    legacy_item = legacy.json()["items"][0]
    assert len(legacy_item["prices"]) == 30
    assert legacy_item["signals"] == []

    assert signal_only.status_code == 200
    item = signal_only.json()["items"][0]
    assert item["prices"] == []
    assert len(item["signals"]) == 2
    assert item["signals"][0]["status"] == "failed"
    assert item["signals"][1]["status"] == "ok"
    assert len(item["signals"][1]["series"][0]["points"]) == 30
    assert item["signals"][1]["annotations"]


@pytest.mark.asyncio
async def test_asset_annotation_references_fail_with_422(
    test_server,
):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": 999999,
                    "date_range": {
                        "start": "2025-01-01",
                        "end": "2025-01-02",
                    },
                    "signals": [
                        {
                            "instance_id": "ema",
                            "signal_code": "EMA",
                            "params": {},
                        }
                    ],
                    "annotation_requests": [
                        {
                            "kind": "threshold_crossing",
                            "key": "bad-target",
                            "attach_to_instance_id": "missing",
                            "source": {
                                "kind": "signal",
                                "instance_id": "ema",
                                "series_key": "ema",
                            },
                            "threshold": 0,
                        }
                    ],
                }
            ],
            timeout=TIMEOUT,
        )

    assert response.status_code == 422
