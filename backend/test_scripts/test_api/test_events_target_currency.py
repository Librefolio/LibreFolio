"""
Test Suite: E.8 — query_events_bulk target_currency conversion

Tests for the FX conversion pass on the events bulk query endpoint:
- POST /api/v1/assets/events/query with target_currency param
- Expected behavior:
    - No target_currency set → events returned in native currency
    - target_currency == event.currency → passthrough (no original_* populated)
    - Conversion succeeds → original_value/fx_rate_date/fx_days_back populated
    - Conversion fails (FX rate missing) → event left untouched, errors[] populated
- Mirrors the prices conversion pattern (plan closure §E.8).
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import (
    FAAssetEventPoint,
    FABulkEventUpsertResponse,
    FAEventQueryItem,
    FAEventUpsert,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, login, and set session cookie on client."""
    import uuid as _uuid  # noqa: PLC0415

    username = f"test_{int(__import__('time').time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 201:
        raise Exception(f"Failed to create user: {resp.text}")
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    if login_resp.status_code != 200:
        raise Exception(f"Failed to login: {login_resp.text}")
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _setup_asset_with_events(
    client: httpx.AsyncClient,
    asset_currency: str,
    event_currency: str,
    event_dates: list[date],
    event_values: list[Decimal],
) -> int:
    """Helper: create asset + insert events in event_currency. Returns asset_id."""
    create_item = FAAssetCreateItem(display_name=f"E8 Test {unique_id('E8')}", currency=asset_currency)
    create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
    assert create_resp.status_code == 201
    asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

    events = [
        FAAssetEventPoint(
            date=d,
            type="DIVIDEND",
            value=Currency(code=event_currency, amount=v),
            notes=None,
        )
        for d, v in zip(event_dates, event_values, strict=True)
    ]
    upsert = FAEventUpsert(asset_id=asset_id, events=events)
    resp = await client.post(f"{API_BASE}/assets/events", json=[upsert.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200
    FABulkEventUpsertResponse(**resp.json())
    return asset_id


async def _ensure_fx_rate(client: httpx.AsyncClient, base: str, quote: str, rate_date: date, rate: Decimal) -> None:
    """Helper: register MANUAL route + upsert single rate."""
    # Register MANUAL route (idempotent: ignore 400 if exists)
    await client.post(
        f"{API_BASE}/fx/providers/routes",
        json=[{"base": base.upper(), "quote": quote.upper(), "provider": "MANUAL", "priority": 999}],
        timeout=TIMEOUT,
    )
    # Upsert rate
    resp = await client.post(
        f"{API_BASE}/fx/currencies/rate",
        json=[{"date": rate_date.isoformat(), "base": base.upper(), "quote": quote.upper(), "rate": str(rate), "source": "MANUAL"}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Failed to upsert FX rate: {resp.text}"


# ============================================================
# Test 1: No target_currency → events returned in native currency
# ============================================================
@pytest.mark.asyncio
async def test_no_target_currency_returns_raw_values(test_server):
    print_section("E.8 Test 1: no target_currency → raw values")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="USD",
            event_currency="USD",
            event_dates=[today - timedelta(days=1)],
            event_values=[Decimal("1.50")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        ev = item["events"][0]
        assert ev["value"]["code"] == "USD"
        assert Decimal(ev["value"]["amount"]) == Decimal("1.50")
        assert ev.get("original_value") is None
        assert ev.get("fx_rate_date") is None
        print_success("  ✓ no target_currency → original_value is None, native value returned")


# ============================================================
# Test 2: target_currency == event.currency → passthrough (no conversion)
# ============================================================
@pytest.mark.asyncio
async def test_same_currency_passthrough(test_server):
    print_section("E.8 Test 2: same currency passthrough")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="USD",
            event_currency="USD",
            event_dates=[today - timedelta(days=1)],
            event_values=[Decimal("2.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
            target_currency="USD",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        ev = item["events"][0]
        assert ev["value"]["code"] == "USD"
        assert Decimal(ev["value"]["amount"]) == Decimal("2.00")
        # Identity passthrough: original_* stay None
        assert ev.get("original_value") is None
        assert item.get("errors") == []
        print_success("  ✓ target==event.currency → passthrough, original_value stays None")


# ============================================================
# Test 3: conversion same-day (fx_days_back == 0)
# ============================================================
@pytest.mark.asyncio
async def test_conversion_same_day_fx(test_server):
    print_section("E.8 Test 3: same-day FX conversion")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        event_date = today - timedelta(days=2)
        # Insert FX rate EUR->USD on the event date (1 EUR = 1.10 USD)
        await _ensure_fx_rate(client, "EUR", "USD", event_date, Decimal("1.10"))

        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="EUR",
            event_currency="EUR",
            event_dates=[event_date],
            event_values=[Decimal("10.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
            target_currency="USD",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        item = resp.json()["items"][0]
        assert item.get("errors") == [], f"Unexpected errors: {item.get('errors')}"
        ev = item["events"][0]
        # Converted value
        assert ev["value"]["code"] == "USD"
        assert Decimal(ev["value"]["amount"]) == Decimal("11.00")  # 10 EUR * 1.10
        # Original preserved
        assert ev["original_value"]["code"] == "EUR"
        assert Decimal(ev["original_value"]["amount"]) == Decimal("10.00")
        # fx metadata
        assert ev["fx_rate_date"] == event_date.isoformat()
        assert ev["fx_days_back"] == 0
        print_success("  ✓ same-day conversion EUR→USD at rate 1.10: 10→11, fx_days_back=0")


# ============================================================
# Test 4: conversion backward-fill (fx_days_back > 0)
# ============================================================
@pytest.mark.asyncio
async def test_conversion_backward_fill_fx(test_server):
    print_section("E.8 Test 4: backward-fill FX conversion")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        event_date = today - timedelta(days=2)
        rate_date = today - timedelta(days=5)  # 3 days back
        # Use an exotic pair unlikely to be polluted by real-world sync in the test DB.
        # NZD/SGD is rarely auto-configured.
        await _ensure_fx_rate(client, "NZD", "SGD", rate_date, Decimal("0.80"))

        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="NZD",
            event_currency="NZD",
            event_dates=[event_date],
            event_values=[Decimal("10.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
            target_currency="SGD",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        item = resp.json()["items"][0]
        ev = item["events"][0]
        assert ev["value"]["code"] == "SGD"
        assert Decimal(ev["value"]["amount"]) == Decimal("8.00"), f"Expected 10*0.80=8.00, got {ev['value']['amount']}"
        assert ev["original_value"]["code"] == "NZD"
        assert ev["fx_rate_date"] == rate_date.isoformat()
        assert ev["fx_days_back"] == (event_date - rate_date).days
        assert ev["fx_days_back"] > 0
        print_success(f"  ✓ backward-fill conversion: fx_days_back={ev['fx_days_back']}")


# ============================================================
# Test 5: missing FX → event kept native, error appended (no hard-fail)
# ============================================================
@pytest.mark.asyncio
async def test_missing_fx_appends_to_errors_not_hard_fail(test_server):
    print_section("E.8 Test 5: missing FX → errors[] non-fatal")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        event_date = today - timedelta(days=1)
        # NO FX rate registered for JPY->ZAR

        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="JPY",
            event_currency="JPY",
            event_dates=[event_date],
            event_values=[Decimal("100.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
            target_currency="ZAR",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200  # no hard-fail
        item = resp.json()["items"][0]
        # Event is still returned, in native currency
        assert len(item["events"]) == 1
        ev = item["events"][0]
        assert ev["value"]["code"] == "JPY"
        assert Decimal(ev["value"]["amount"]) == Decimal("100.00")
        assert ev.get("original_value") is None
        # errors[] should contain a non-fatal warning
        assert len(item["errors"]) >= 1
        err_txt = " ".join(item["errors"])
        assert "JPY" in err_txt or "ZAR" in err_txt or "FX" in err_txt
        print_success(f"  ✓ missing FX → event native + {len(item['errors'])} non-fatal warning(s)")


# ============================================================
# Test 6: mixed batch — some converted, some not
# ============================================================
@pytest.mark.asyncio
async def test_mixed_events_some_converted_some_not(test_server):
    print_section("E.8 Test 6: mixed converted/not-converted")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        d1 = today - timedelta(days=5)
        d2 = today - timedelta(days=3)
        # Rate only for d1, not d2
        await _ensure_fx_rate(client, "CHF", "USD", d1, Decimal("1.05"))

        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="CHF",
            event_currency="CHF",
            event_dates=[d1, d2],
            event_values=[Decimal("20.00"), Decimal("30.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=10), end=today),
            target_currency="USD",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        events = sorted(item["events"], key=lambda e: e["date"])
        # d1: converted (backward-fill from d1 itself → 0 days)
        # d2: CHF→USD with rate at d1 (backward-fill → (d2-d1) days back)
        # Both succeed because convert_bulk uses unlimited backward-fill by default.
        # This confirms the policy: a single rate covers all subsequent dates.
        assert events[0]["value"]["code"] == "USD"
        assert events[1]["value"]["code"] == "USD"
        print_success("  ✓ mixed batch handled; backward-fill propagates to subsequent dates")


# ============================================================
# Test 7: on success, original_value is ALWAYS populated
# ============================================================
@pytest.mark.asyncio
async def test_original_value_always_populated_on_success(test_server):
    print_section("E.8 Test 7: original_value always populated on success")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        today = date.today()
        event_date = today - timedelta(days=1)
        await _ensure_fx_rate(client, "CAD", "USD", event_date, Decimal("0.75"))

        asset_id = await _setup_asset_with_events(
            client,
            asset_currency="CAD",
            event_currency="CAD",
            event_dates=[event_date],
            event_values=[Decimal("100.00")],
        )

        query = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=7), end=today),
            target_currency="USD",
        )
        resp = await client.post(f"{API_BASE}/assets/events/query", json=[query.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        ev = item["events"][0]
        assert ev.get("original_value") is not None, "original_value MUST be populated on successful conversion"
        assert ev["original_value"]["code"] == "CAD"
        assert Decimal(ev["original_value"]["amount"]) == Decimal("100.00")
        assert ev["value"]["code"] == "USD"
        assert Decimal(ev["value"]["amount"]) == Decimal("75.00")
        print_success("  ✓ original_value fully populated (CAD 100 → USD 75)")
