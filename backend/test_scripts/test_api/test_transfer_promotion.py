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
    r = await client.post(f"{API_BASE}/transactions/commit", json={"creates": payload}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["committed"] is True, data
    return data["results"][0]["ids"][0], data["results"][1]["ids"][0]


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
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
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
                ]
            },
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


# =============================================================================
# R13-SEC7-3 — THE PROMOTION'S QUANTITY AND COST BASIS: A 422 AT THE BOUNDARY
# =============================================================================


async def _create_asset(client: httpx.AsyncClient) -> int:
    """A STOCK asset of the test, uniquely named: its id."""
    r = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"Promote Bound Asset {uuid.uuid4().hex[:8]}", "asset_type": "STOCK", "currency": "EUR"}], timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    return r.json()["results"][0]["asset_id"]


async def _remove_owned(client: httpx.AsyncClient, broker_ids: list[int], asset_ids: list[int]) -> list[str]:
    """Whoever writes, cleans up: force-delete the test's brokers (their transactions with them), then its assets. What
    could not be removed, for the caller to fail on — also after a red."""
    errors: list[str] = []
    if broker_ids:
        r = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
        deleted = {result["id"] for result in r.json()["results"] if result["success"]} if r.status_code == 200 else set()
        errors += [f"Broker {broker_id} not deleted: {r.status_code} {r.text[:200]}" for broker_id in broker_ids if broker_id not in deleted]
    if asset_ids:
        r = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        deleted = {result["asset_id"] for result in r.json()["results"] if result["success"]} if r.status_code == 200 else set()
        errors += [f"Asset {asset_id} not deleted: {r.status_code} {r.text[:200]}" for asset_id in asset_ids if asset_id not in deleted]
    return errors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "loc_tail"),
    [
        pytest.param("quantity", "1E+5000000", ("quantity",), id="quantity-1E+5000000"),
        pytest.param("cost_basis_override", {"code": "EUR", "amount": "1E+5000000"}, ("cost_basis_override", "amount"), id="cost-basis-1E+5000000"),
    ],
)
async def test_promote_past_the_exponent_bound_answers_422_and_changes_nothing(test_server, field, value, loc_tail):
    """R13-SEC7-3 (E's R13-SEC7, finding 3): ``TXTransferPromoteRequest.quantity`` and its ``cost_basis_override`` (a
    ``Currency``) are bounded at the boundary, ``adjusted()`` within [-100, 100].

    Red today: the quantity makes ``abs()`` raise ``decimal.Overflow`` in ``promote_transfer`` (a 500); the cost basis is
    expanded by ``format(v, "f")`` to 5 MB, and the batch refuses it (200, rolled back).

    Contract: 422 before any work, its error on the field; the cash pair reads back as it was, and neither broker holds a
    TRANSFER.
    """
    async with httpx.AsyncClient() as client:
        await _auth(client)
        broker_ids: list[int] = []
        asset_ids: list[int] = []
        try:
            broker_ids += [await _create_broker(client, "BoundFrom"), await _create_broker(client, "BoundTo")]
            asset_ids.append(await _create_asset(client))
            from_id, to_id = await _create_cash_pair(client, broker_ids[0], broker_ids[1], "EUR", "EUR", "100")
            payload = {"from_tx_id": from_id, "to_tx_id": to_id, "new_type": "TRANSFER", "asset_id": asset_ids[0], "quantity": "10", "cost_basis_override": {"code": "EUR", "amount": "50"}}
            payload[field] = value

            try:
                # A client of its own, with the session's cookie: a request the server drops must not leave a dead
                # connection in the pool the reads and the cleanup below go through.
                async with httpx.AsyncClient(cookies=client.cookies) as poster:
                    r = await poster.post(f"{API_BASE}/transactions/transfers/promote", json=payload, timeout=TIMEOUT)
                answer = f"{r.status_code}: {r.text[:400]}"
            except httpx.TransportError as exc:
                # An unhandled exception in the route: the server closes the connection without a response.
                r, answer = None, f"no response — the server dropped the connection ({exc!r}), an unhandled exception"

            pair = await client.get(f"{API_BASE}/transactions", params=[("ids", from_id), ("ids", to_id)], timeout=TIMEOUT)
            assert pair.status_code == 200, pair.text
            pair_state = sorted((row["id"], row["type"], row["related_transaction_id"]) for row in pair.json())
            transfers = []
            for broker_id in broker_ids:
                listed = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_id}, timeout=TIMEOUT)
                assert listed.status_code == 200, listed.text
                transfers += [row["id"] for row in listed.json() if row["type"] == "TRANSFER"]
        finally:
            leftovers = await _remove_owned(client, broker_ids, asset_ids)

        assert r is not None and r.status_code == 422, f"R13-SEC7-3: a promotion with {field}={value} must answer 422 at the boundary; it answered {answer}"
        locs = [tuple(error["loc"]) for error in r.json()["detail"]]
        assert any(loc[-len(loc_tail) :] == loc_tail for loc in locs), f"R13-SEC7-3: the 422 must name {'.'.join(loc_tail)}; its errors sit on {locs}"
        assert pair_state == sorted([(from_id, "WITHDRAWAL", None), (to_id, "DEPOSIT", None)]), f"R13-SEC7-3: the promotion was refused, yet the cash pair reads back {pair_state}"
        assert transfers == [], f"R13-SEC7-3: the promotion was refused, yet the brokers hold the TRANSFER rows {transfers}"
        assert leftovers == [], f"Cleanup failed: {leftovers}"
