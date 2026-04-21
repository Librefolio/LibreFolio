"""
Transfer Promotion API tests (Block H.4).

Covers POST /transactions/transfers/promote end-to-end over HTTP.
Service-level matrix is in test_transaction_service.py → TestTransferPromotion.
"""

import uuid
from datetime import date

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def _u() -> str:
    return f"promote_test_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


async def _auth(client: httpx.AsyncClient) -> None:
    username = _u()
    email = f"{username}@test.com"
    password = "TestPass123!"
    r = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert r.status_code == 201, r.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    session_cookie = login.cookies.get("session")
    if session_cookie:
        client.cookies.set("session", session_cookie)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _create_broker(client: httpx.AsyncClient, name_suffix: str, allow_overdraft: bool = True) -> int:
    payload = [{"name": f"Promote Broker {name_suffix} {uuid.uuid4().hex[:6]}", "allow_cash_overdraft": allow_overdraft}]
    r = await client.post(f"{API_BASE}/brokers", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["results"][0]["broker_id"]


async def _create_cash_pair(client: httpx.AsyncClient, broker_a: int, broker_b: int, currency_a: str, currency_b: str, amount: str) -> tuple[int, int]:
    payload = [
        {
            "broker_id": broker_a,
            "type": "WITHDRAWAL",
            "date": date.today().isoformat(),
            "cash": {"code": currency_a, "amount": f"-{amount}"},
        },
        {
            "broker_id": broker_b,
            "type": "DEPOSIT",
            "date": date.today().isoformat(),
            "cash": {"code": currency_b, "amount": amount},
        },
    ]
    r = await client.post(f"{API_BASE}/transactions/bulk", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["rolled_back"] is False, data
    return data["results"][0]["transaction_id"], data["results"][1]["transaction_id"]


@pytest.mark.asyncio
async def test_promote_fx_conversion_happy_path(test_server):
    """Intra-broker DEPOSIT/WITHDRAWAL with different currencies → FX_CONVERSION."""
    async with httpx.AsyncClient() as client:
        await _auth(client)
        broker_id = await _create_broker(client, "FX")
        from_id, to_id = await _create_cash_pair(client, broker_id, broker_id, "EUR", "USD", "500")

        r = await client.post(
            f"{API_BASE}/transactions/transfers/promote",
            json={
                "from_tx_id": from_id,
                "to_tx_id": to_id,
                "new_type": "FX_CONVERSION",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["rolled_back"] is False, data
        assert data["new_from_tx_id"] is not None
        assert data["new_to_tx_id"] is not None

        # Verify the new transactions are FX_CONVERSION (originals were DEPOSIT/WITHDRAWAL).
        # Note: SQLite may reuse auto-incremented ids from deleted rows, so we
        # can't assert "originals gone" by id — we check by type/link instead.
        check = await client.get(
            f"{API_BASE}/transactions",
            params=[("ids", data["new_from_tx_id"]), ("ids", data["new_to_tx_id"])],
            timeout=TIMEOUT,
        )
        assert check.status_code == 200
        rows = check.json()
        assert len(rows) == 2
        assert all(r["type"] == "FX_CONVERSION" for r in rows)
        assert rows[0]["related_transaction_id"] == rows[1]["id"]
        assert rows[1]["related_transaction_id"] == rows[0]["id"]


@pytest.mark.asyncio
async def test_promote_rejects_transfer_same_broker(test_server):
    async with httpx.AsyncClient() as client:
        await _auth(client)
        broker_id = await _create_broker(client, "SameBrokerReject")
        from_id, to_id = await _create_cash_pair(client, broker_id, broker_id, "EUR", "EUR", "100")

        # Create a dummy asset first (POST /assets accepts a list).
        asset_resp = await client.post(
            f"{API_BASE}/assets",
            json=[
                {
                    "display_name": f"Promote Asset {uuid.uuid4().hex[:6]}",
                    "asset_type": "STOCK",
                    "currency": "EUR",
                }
            ],
            timeout=TIMEOUT,
        )
        assert asset_resp.status_code in (200, 201), asset_resp.text
        asset_data = asset_resp.json()
        # bulk response shape
        if isinstance(asset_data, dict) and "results" in asset_data:
            asset_id = asset_data["results"][0].get("asset_id") or asset_data["results"][0].get("id")
        elif isinstance(asset_data, list):
            asset_id = asset_data[0]["id"]
        else:
            asset_id = asset_data["id"]

        r = await client.post(
            f"{API_BASE}/transactions/transfers/promote",
            json={
                "from_tx_id": from_id,
                "to_tx_id": to_id,
                "new_type": "TRANSFER",
                "asset_id": asset_id,
                "quantity": "10",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["rolled_back"] is True
        assert any("distinct brokers" in e for e in data["errors"])


@pytest.mark.asyncio
async def test_query_amount_abs_range_filter(test_server):
    """H.3 — verify new query params are accepted by the API."""
    async with httpx.AsyncClient() as client:
        await _auth(client)
        broker_id = await _create_broker(client, "H3")

        await client.post(
            f"{API_BASE}/transactions/bulk",
            json=[
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "100"},
                },
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "500"},
                },
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "2000"},
                },
            ],
            timeout=TIMEOUT,
        )

        r = await client.get(
            f"{API_BASE}/transactions",
            params={
                "broker_id": broker_id,
                "amount_abs_min": "450",
                "amount_abs_max": "550",
                "only_unlinked": "true",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        for row in rows:
            amt = abs(float(row["cash"]["amount"]))
            assert 450 <= amt <= 550
            assert row["related_transaction_id"] is None
