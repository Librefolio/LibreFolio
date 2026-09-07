"""Tests for grouped technical signals in FX bulk conversion."""

from __future__ import annotations

import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1 import fx as fx_api
from backend.app.config import get_settings
from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(
    client: httpx.AsyncClient,
) -> None:
    username = f"fx_signal_{int(time.time() * 1000)}_" f"{uuid.uuid4().hex[:6]}"
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


async def set_rate(
    base: str,
    quote: str,
    rate_date: date,
    rate: Decimal,
) -> None:
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        statement = (
            insert(FxRate)
            .values(
                base=base,
                quote=quote,
                date=rate_date,
                rate=rate,
                source="MANUAL",
            )
            .on_conflict_do_update(
                index_elements=[
                    "date",
                    "base",
                    "quote",
                ],
                set_={
                    "rate": rate,
                    "source": "MANUAL",
                },
            )
        )
        await session.execute(statement)
        await session.commit()


@pytest.mark.asyncio
async def test_handler_uses_one_combined_convert_bulk_call(
    monkeypatch,
):
    calls: list[list] = []

    async def fake_convert_bulk(
        session,
        conversions,
        raise_on_error,
    ):
        calls.append(conversions)
        return (
            [
                (
                    Currency(
                        code=to_currency,
                        amount=amount.amount,
                    ),
                    on_date,
                    False,
                )
                for amount, to_currency, on_date in conversions
            ],
            [],
        )

    monkeypatch.setattr(
        fx_api,
        "convert_bulk",
        fake_convert_bulk,
    )
    start = date(2026, 1, 10)
    response = await fx_api.convert_currency_bulk(
        request=[
            FXConversionRequest(
                from_amount=Currency(
                    code="EUR",
                    amount=Decimal("100"),
                ),
                to="EUR",
                date_range=DateRangeModel(
                    start=start,
                    end=start + timedelta(days=2),
                ),
                signals=[
                    {
                        "instance_id": "sma",
                        "signal_code": "SMA",
                        "params": {"period": 2},
                    }
                ],
            )
        ],
        session=object(),
        _current_user=object(),
    )

    assert len(calls) == 1
    assert len(calls[0]) == 8
    assert len(response.results) == 3
    assert len(response.signal_results) == 1
    assert response.signal_results[0].signals[0].status.value == "ok"


@pytest.mark.asyncio
async def test_fx_identity_and_direct_signals(test_server):
    start = date(2025, 6, 1)
    end = start + timedelta(days=9)
    await set_rate(
        "EUR",
        "USD",
        start - timedelta(days=2),
        Decimal("2"),
    )
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[
                {
                    "from_amount": {
                        "code": "EUR",
                        "amount": "100",
                    },
                    "to": "EUR",
                    "date_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "signals": [
                        {
                            "instance_id": "identity-sma",
                            "signal_code": "SMA",
                            "params": {"period": 2},
                        }
                    ],
                },
                {
                    "from_amount": {
                        "code": "EUR",
                        "amount": "100",
                    },
                    "to": "USD",
                    "date_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "signals": [
                        {
                            "instance_id": "direct-sma",
                            "signal_code": "SMA",
                            "params": {"period": 2},
                        },
                        {
                            "instance_id": "atr",
                            "signal_code": "ATR",
                            "params": {"period": 14},
                        },
                    ],
                },
            ],
            timeout=TIMEOUT,
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 20
    assert len(payload["signal_results"]) == 2
    identity = payload["signal_results"][0]
    direct = payload["signal_results"][1]
    assert identity["request_index"] == 0
    assert direct["request_index"] == 1
    assert identity["signals"][0]["status"] == "ok"
    assert all(point["value"] == 1.0 for point in identity["signals"][0]["series"][0]["points"])
    assert direct["signals"][0]["status"] == "ok"
    assert all(point["value"] == 2.0 for point in direct["signals"][0]["series"][0]["points"])
    assert direct["signals"][1]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_fx_inverse_signal_uses_effective_rate(test_server):
    start = date(2025, 7, 1)
    end = start + timedelta(days=5)
    await set_rate(
        "EUR",
        "USD",
        start - timedelta(days=2),
        Decimal("2"),
    )
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[
                {
                    "from_amount": {
                        "code": "USD",
                        "amount": "100",
                    },
                    "to": "EUR",
                    "date_range": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "signals": [
                        {
                            "instance_id": "inverse-sma",
                            "signal_code": "SMA",
                            "params": {"period": 2},
                        }
                    ],
                }
            ],
            timeout=TIMEOUT,
        )

    assert response.status_code == 200
    signal = response.json()["signal_results"][0]["signals"][0]
    assert signal["status"] == "ok"
    assert all(point["value"] == 0.5 for point in signal["series"][0]["points"])


@pytest.mark.asyncio
async def test_missing_rate_returns_grouped_unavailable(test_server):
    start = date(2025, 8, 1)
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        await session.execute(
            delete(FxRate).where(
                FxRate.base == "BMD",
                FxRate.quote == "CAD",
            )
        )
        await session.commit()

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[
                {
                    "from_amount": {
                        "code": "BMD",
                        "amount": "100",
                    },
                    "to": "CAD",
                    "date_range": {
                        "start": start.isoformat(),
                        "end": (start + timedelta(days=2)).isoformat(),
                    },
                    "signals": [
                        {
                            "instance_id": "ema",
                            "signal_code": "EMA",
                            "params": {"period": 14},
                        }
                    ],
                }
            ],
            timeout=TIMEOUT,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["errors"]
    assert payload["signal_results"][0]["signals"][0]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_no_signal_response_keeps_daily_contract(test_server):
    start = date(2025, 9, 1)
    await set_rate(
        "EUR",
        "USD",
        start,
        Decimal("1.5"),
    )
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[
                {
                    "from_amount": {
                        "code": "EUR",
                        "amount": "10",
                    },
                    "to": "USD",
                    "date_range": {
                        "start": start.isoformat(),
                        "end": (start + timedelta(days=2)).isoformat(),
                    },
                }
            ],
            timeout=TIMEOUT,
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 3
    assert payload["success_count"] == 3
    assert payload["signal_results"] == []
    assert all(Decimal(result["to_amount"]["amount"]) == Decimal("15") for result in payload["results"])


@pytest.mark.asyncio
async def test_fx_annotation_references_fail_with_422(test_server):
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[
                {
                    "from_amount": {
                        "code": "EUR",
                        "amount": "10",
                    },
                    "to": "EUR",
                    "date_range": {
                        "start": "2025-01-01",
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
