"""
Test Suite: parametric provider — what survives a removal and a switch

Two rules that live in places a future change could break silently, so they get
a test that speaks in outcomes rather than in schema clauses.

1. **Removing** the provider keeps the prices and the *manual* events, and drops
   the ones the provider generated. Nothing here is enforced by application
   code: the deletion of the generated events comes from an ``ON DELETE
   CASCADE`` on ``AssetEvent.provider_assignment_id`` (db/models.py) plus
   ``PRAGMA foreign_keys=ON`` (db/session.py). A migration that recreates the
   table without the clause — or with ``SET NULL`` — would turn generated events
   into orphaned "manual" ones and no test would notice.

2. **Switching away** from a parametric provider discards the generated series.
   A parametric series is invented from ``provider_params``; under a market
   provider it is not history. Keeping it would also poison the next sync, which
   resumes from the day after the last stored price and would therefore never
   backfill the real past.
"""

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import (
    AssetType,
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.provider import (
    FAProviderAssignmentItem,
    IdentifierType,
    ProviderInputType,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 60.0

SCHEDULE_PARAMS = {
    "initial_value": {"code": "EUR", "amount": 10000},
    "interest_type": "SIMPLE",
    "day_count": "ACT/365",
    "schedule": [
        {
            "start_date": "2024-01-15",
            "end_date": "2026-01-15",
            "annual_rate": 0.035,
            "maturation_frequency": "MONTHLY",
            "generate_interest": True,
        }
    ],
}

MANUAL_EVENT_DATE = "2024-03-07"
# Query ranges want real dates: "min" is a *sync* keyword, the query schema rejects it.
QUERY_RANGE = {"start": "1900-01-01", "end": "2026-12-31"}


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    import time  # noqa: PLC0415 — test setup — imports after sys.path/db config
    import uuid as _uuid  # noqa: PLC0415

    username = f"test_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
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
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _count_prices(client: httpx.AsyncClient, asset_id: int) -> int:
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[{"asset_id": asset_id, "date_range": QUERY_RANGE, "include_events": False}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    return len(item.get("prices") or item.get("points") or [])


async def _events(client: httpx.AsyncClient, asset_id: int) -> list[dict]:
    resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[{"asset_id": asset_id, "date_range": QUERY_RANGE}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"][0].get("events") or []


async def _seed_parametric_asset(client: httpx.AsyncClient, label: str) -> int:
    """Asset with a parametric provider, a synced series, and one manual event."""
    asset_item = FAAssetCreateItem(
        display_name=f"{label} {unique_id('PARAM')}",
        currency="EUR",
        asset_type=AssetType.BOND,
    )
    create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
    assert create_resp.status_code == 201, create_resp.text
    asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

    assignment = FAProviderAssignmentItem(
        asset_id=asset_id,
        provider_code="scheduled_investment",
        identifier="",
        identifier_type=ProviderInputType.AUTO_GENERATED,
        provider_params=SCHEDULE_PARAMS,
    )
    assign_resp = await client.post(
        f"{API_BASE}/assets/provider",
        json=[assignment.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert assign_resp.status_code == 200, assign_resp.text

    sync_resp = await client.post(
        f"{API_BASE}/assets/prices/sync",
        json=[{"asset_id": asset_id, "date_range": {"start": "2024-01-15", "end": "2026-01-15"}}],
        timeout=TIMEOUT,
    )
    assert sync_resp.status_code == 200, sync_resp.text

    manual_resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[
            {
                "asset_id": asset_id,
                "events": [
                    {
                        "date": MANUAL_EVENT_DATE,
                        "type": "DIVIDEND",
                        "value": {"code": "EUR", "amount": 42},
                        "notes": "manual — must survive",
                    }
                ],
            }
        ],
        timeout=TIMEOUT,
    )
    assert manual_resp.status_code in (200, 201), manual_resp.text
    return asset_id


def _split_events(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """(generated, manual) — ``is_auto`` is the public name of ``provider_assignment_id IS NOT NULL``."""
    generated = [e for e in events if e.get("is_auto")]
    manual = [e for e in events if not e.get("is_auto")]
    return generated, manual


@pytest.mark.asyncio
async def test_provider_removal_keeps_prices_and_manual_events(test_server):
    """Removing the provider: prices stay, manual events stay, generated events go."""
    print_section("Parametric provider removal — what survives")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _seed_parametric_asset(client, "Removal")

        prices_before = await _count_prices(client, asset_id)
        generated_before, manual_before = _split_events(await _events(client, asset_id))
        print_info(f"  before: {prices_before} price(s), {len(generated_before)} generated, {len(manual_before)} manual")

        # The test is only meaningful if the provider actually produced something.
        assert prices_before > 0, "the parametric sync produced no prices — nothing to protect"
        assert len(generated_before) > 0, "the parametric sync produced no events — nothing to cascade"
        assert len(manual_before) == 1, f"expected exactly the one manual event, got {len(manual_before)}"

        remove_resp = await client.request(
            "DELETE",
            f"{API_BASE}/assets/provider",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT,
        )
        assert remove_resp.status_code == 200, remove_resp.text

        prices_after = await _count_prices(client, asset_id)
        generated_after, manual_after = _split_events(await _events(client, asset_id))

        assert prices_after == prices_before, f"prices must survive provider removal: {prices_before} → {prices_after}"
        assert len(generated_after) == 0, f"generated events must be cascaded away, {len(generated_after)} left"
        assert len(manual_after) == 1, f"the manual event must survive, {len(manual_after)} left"
        assert manual_after[0]["date"] == MANUAL_EVENT_DATE
        print_success(f"✓ {prices_after} price(s) and the manual event survived; {len(generated_before)} generated event(s) gone")


@pytest.mark.asyncio
async def test_switch_away_from_parametric_discards_generated_series(test_server):
    """Switching provider: the invented series is discarded, the manual event is not."""
    print_section("Parametric provider switch — the invented series is discarded")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _seed_parametric_asset(client, "Switch")

        prices_before = await _count_prices(client, asset_id)
        generated_before, manual_before = _split_events(await _events(client, asset_id))
        assert prices_before > 0 and len(generated_before) > 0 and len(manual_before) == 1

        switch = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER,
            provider_params=None,
        )
        switch_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[switch.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert switch_resp.status_code == 200, switch_resp.text

        prices_after = await _count_prices(client, asset_id)
        generated_after, manual_after = _split_events(await _events(client, asset_id))

        assert prices_after == 0, f"the invented series must not survive under a market provider, {prices_after} left"
        assert len(generated_after) == 0, f"generated events must go with it, {len(generated_after)} left"
        assert len(manual_after) == 1, f"the manual event must survive, {len(manual_after)} left"
        print_success(f"✓ {prices_before} invented price(s) and {len(generated_before)} generated event(s) discarded; manual event kept")
