"""API tests for static Asset and FX signal catalogs."""

from __future__ import annotations

import inspect
import time
import uuid

import httpx
import pytest

from backend.app.api.v1.assets import list_asset_signal_catalog
from backend.app.api.v1.fx import list_fx_signal_catalog
from backend.app.config import get_settings
from backend.app.schemas.signals import SignalCatalogResponse
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

ASSET_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
    "ATR",
    "ADX",
    "NATR",
    "AROON",
    "DONCHIAN",
    "CCI",
    "OBV",
    "MFI",
    "RISK_DRAWDOWN",
    "RISK_ROLLING_BETA",
    "RISK_ROLLING_RETURN",
    "RISK_ROLLING_SHARPE",
    "RISK_ROLLING_VOLATILITY",
}
FX_CODES = {
    "EMA",
    "SMA",
    "RSI",
    "MACD",
    "BOLLINGER",
    "ROC",
    "STOCH_RSI",
    "KAMA",
    "PPO",
}


async def create_user_and_login(
    client: httpx.AsyncClient,
) -> None:
    username = f"signal_catalog_{int(time.time() * 1000)}_" f"{uuid.uuid4().hex[:6]}"
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


@pytest.mark.asyncio
async def test_signal_catalogs_require_authentication(test_server):
    async with httpx.AsyncClient() as client:
        asset = await client.get(
            f"{API_BASE}/assets/prices/signals",
            timeout=TIMEOUT,
        )
        fx = await client.get(
            f"{API_BASE}/fx/currencies/signals",
            timeout=TIMEOUT,
        )

    assert asset.status_code == 401
    assert fx.status_code == 401


@pytest.mark.asyncio
async def test_asset_and_fx_catalogs_are_static_and_filtered(
    test_server,
):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        first_asset = await client.get(
            f"{API_BASE}/assets/prices/signals",
            timeout=TIMEOUT,
        )
        second_asset = await client.get(
            f"{API_BASE}/assets/prices/signals",
            timeout=TIMEOUT,
        )
        first_fx = await client.get(
            f"{API_BASE}/fx/currencies/signals",
            timeout=TIMEOUT,
        )
        second_fx = await client.get(
            f"{API_BASE}/fx/currencies/signals",
            timeout=TIMEOUT,
        )

    assert first_asset.status_code == 200
    assert first_fx.status_code == 200
    assert first_asset.json() == second_asset.json()
    assert first_fx.json() == second_fx.json()

    asset_catalog = SignalCatalogResponse.model_validate(first_asset.json())
    fx_catalog = SignalCatalogResponse.model_validate(first_fx.json())
    assert {item.signal_code for item in asset_catalog.items} == ASSET_CODES
    assert {item.signal_code for item in fx_catalog.items} == FX_CODES
    assert [item.signal_code for item in asset_catalog.items] == sorted(ASSET_CODES)
    assert [item.signal_code for item in fx_catalog.items] == sorted(FX_CODES)
    beta = next(item for item in asset_catalog.items if item.signal_code == "RISK_ROLLING_BETA")
    comparison_param = beta.params_schema["properties"]["comparison_asset_id"]
    assert comparison_param["x-control"] == "comparison_asset"
    assert beta.input_requirements.comparison_asset_param == "comparison_asset_id"


@pytest.mark.asyncio
async def test_catalog_shape_is_schema_driven_without_availability(
    test_server,
):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(
            f"{API_BASE}/assets/prices/signals",
            timeout=TIMEOUT,
        )

    for item in response.json()["items"]:
        assert item["implementation_version"]
        assert item["display_name_key"]
        assert item["description_key"]
        assert item["params_schema"]["type"] == "object"
        assert item["input_requirements"]["price_fields"]
        assert item["output_specs"]
        assert item["compatible_domains"]
        for forbidden in (
            "status",
            "availability",
            "available_points",
            "warmup_complete",
            "missing_fields",
        ):
            assert forbidden not in item


@pytest.mark.asyncio
async def test_catalog_handlers_have_no_db_or_history_dependency():
    asset_signature = inspect.signature(list_asset_signal_catalog)
    fx_signature = inspect.signature(list_fx_signal_catalog)
    assert "session" not in asset_signature.parameters
    assert "session" not in fx_signature.parameters

    asset = await list_asset_signal_catalog(_current_user=object())
    fx = await list_fx_signal_catalog(_current_user=object())
    assert len(asset.items) == 22
    assert len(fx.items) == 9
