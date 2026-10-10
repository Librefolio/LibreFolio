"""
WAC Inline Validate/Commit Tests (P16-P28).

Tests for cost_basis_mode='auto'/'auto-detail' triggering WAC computation
directly in the /validate and /commit batch pipeline response.

Reference: plan-WacInlineValidateCommit.prompt.md
"""

import uuid
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ============================================================================
# HELPERS
# ============================================================================


def unique_username() -> str:
    return f"waci_test_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> str:
    """Create a test user, login, return username."""
    username = unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    session_cookie = login_resp.cookies.get("session")
    if session_cookie:
        client.cookies.set("session", session_cookie)

    return username


async def create_broker(client: httpx.AsyncClient, name: str) -> int:
    """Create a broker and return its ID."""
    unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": unique_name, "allow_cash_overdraft": True}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create broker failed: {resp.text}"
    data = resp.json()
    assert data["results"][0]["success"], f"Broker not successful: {data}"
    return data["results"][0]["broker_id"]


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    """Create an asset and return its ID."""
    unique_name = f"WACiAsset_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[{"display_name": unique_name, "currency": currency, "asset_type": "STOCK"}],
        timeout=TIMEOUT,
    )
    assert resp.status_code in (200, 201), f"Create asset failed: {resp.text}"
    return resp.json()["results"][0]["asset_id"]


async def create_user_broker_asset(client: httpx.AsyncClient, *, currency: str = "EUR") -> tuple[int, int]:
    """Create user + broker + asset, return (broker_id, asset_id)."""
    await create_test_user(client)
    broker_id = await create_broker(client, "WACiBroker")
    asset_id = await create_asset(client, currency=currency)
    return broker_id, asset_id


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    """POST /transactions/commit, return response JSON."""
    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json=kwargs,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Commit failed ({resp.status_code}): {resp.text}"
    return resp.json()


async def validate_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    """POST /transactions/validate, return response JSON."""
    resp = await client.post(
        f"{API_BASE}/transactions/validate",
        json=kwargs,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Validate failed ({resp.status_code}): {resp.text}"
    return resp.json()


async def get_txs_by_ids(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    """GET /transactions?ids=..., return list of TX dicts."""
    resp = await client.get(
        f"{API_BASE}/transactions",
        params={"ids": ids},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"GET transactions failed: {resp.text}"
    return resp.json()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
class TestWACInlineValidateCommit:
    """P16-P28: WAC inline computation in /validate and /commit."""

    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ P16
    async def test_wacp16_validate_transfer_auto_wac(self):
        """validate with TRANSFER auto → wac_results[0].wac = source broker WAC."""
        print_section("P16 — validate TRANSFER auto → WAC from source broker")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P16B")

            # Setup: BUY 10 @ 50 EUR on broker_a
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )

            # Validate: TRANSFER pair with auto WAC on receiver
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "5", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            assert data["committed"] is False
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1
            wr = data["wac_results"][0]
            assert wr["operation"] == "create"
            assert wr["index"] == 1
            assert wr["source_broker_id"] == broker_a_id
            assert wr["wac"] is not None
            assert Decimal(wr["wac"]["amount"]) == Decimal("50")
            assert wr["wac"]["code"] == "EUR"
            print_success("P16 ✓")

    # ------------------------------------------------------------------ P17
    async def test_wacp17_validate_adjustment_auto_wac(self):
        """validate ADJUSTMENT auto → own broker WAC (pool invariant, exclude self)."""
        print_section("P17 — validate ADJUSTMENT auto → own broker WAC")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "20", "cash": {"code": "EUR", "amount": "-2000"}},
                ],
            )

            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-10", "quantity": "5", "cost_basis_mode": "auto"},
                ],
            )

            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["source_broker_id"] == broker_id
            assert Decimal(wr["wac"]["amount"]) == Decimal("100")
            print_success("P17 ✓")

    # ------------------------------------------------------------------ P18
    async def test_wacp18_commit_transfer_auto_persists_cbo(self):
        """commit TRANSFER auto → DB row has cost_basis_override populated."""
        print_section("P18 — commit TRANSFER auto → cbo persisted")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P18B")

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-03", "quantity": "10", "cash": {"code": "EUR", "amount": "-800"}},
                ],
            )

            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-05", "quantity": "-3", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-05", "quantity": "3", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )
            assert data["committed"] is True

            receiver_id = data["results"][1]["ids"][0]
            txs = await get_txs_by_ids(client, [receiver_id])
            assert len(txs) == 1
            assert txs[0]["cost_basis_override"] is not None
            assert Decimal(txs[0]["cost_basis_override"]["amount"]) == Decimal("80")
            assert txs[0]["cost_basis_override"]["code"] == "EUR"
            print_success("P18 ✓")

    # ------------------------------------------------------------------ P19
    async def test_wacp19_auto_detail_includes_qualifying(self):
        """auto-detail → response includes qualifying_txs."""
        print_section("P19 — auto-detail returns qualifying_txs")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-01", "quantity": "5", "cash": {"code": "EUR", "amount": "-250"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-03-01", "quantity": "10", "cash": {"code": "EUR", "amount": "-700"}},
                ],
            )

            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-01", "quantity": "2", "cost_basis_mode": "auto-detail"},
                ],
            )

            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["wac_qualifying_txs"] is not None
            assert len(wr["wac_qualifying_txs"]) >= 2
            print_success("P19 ✓")

    # ------------------------------------------------------------------ P20
    async def test_wacp20_no_auto_items_no_wac_results(self):
        """validate without auto items → wac_results is null."""
        print_section("P20 — no auto → wac_results null")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "5000"}},
                ],
            )

            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-01", "quantity": "5", "cash": {"code": "EUR", "amount": "-250"}},
                ],
            )

            assert data.get("wac_results") is None
            print_success("P20 ✓")

    # ------------------------------------------------------------------ P21
    async def test_wacp21_commit_source_detection_link_uuid(self):
        """commit TRANSFER auto: source_broker from link_uuid partner."""
        print_section("P21 — source broker via link_uuid")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P21B")

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1200"}},
                ],
            )

            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-05-01", "quantity": "-4", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-05-01", "quantity": "4", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )
            assert data["committed"] is True
            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["source_broker_id"] == broker_a_id
            assert Decimal(wr["wac"]["amount"]) == Decimal("120")
            print_success("P21 ✓")

    # ------------------------------------------------------------------ P22
    async def test_wacp22_update_auto_wac(self):
        """update with cost_basis_mode='auto' → WAC excluding self."""
        print_section("P22 — update with auto WAC")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-2000"}},
                ],
            )
            adj_data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-03-01", "quantity": "5", "cost_basis_override": {"code": "EUR", "amount": "999"}},
                ],
            )
            adj_id = adj_data["results"][0]["ids"][0]

            data = await validate_batch(
                client,
                updates=[
                    {"id": adj_id, "cost_basis_mode": "auto"},
                ],
            )

            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["operation"] == "update"
            assert Decimal(wr["wac"]["amount"]) == Decimal("200")
            print_success("P22 ✓")

    # ------------------------------------------------------------------ P23
    async def test_wacp23_mixed_batch_only_auto_in_wac_results(self):
        """mixed batch: only auto items appear in wac_results."""
        print_section("P23 — mixed batch → only auto in wac_results")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P23B")

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )

            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-04-01", "quantity": "5", "cash": {"code": "EUR", "amount": "-300"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-02", "quantity": "-3", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-02", "quantity": "3", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            assert data.get("wac_results") is not None
            assert len(data["wac_results"]) == 1
            assert data["wac_results"][0]["index"] == 2
            print_success("P23 ✓")

    # ------------------------------------------------------------------ P24
    async def test_wacp24_link_uuid_resolves_source(self):
        """TRANSFER pair in same creates → link_uuid resolves source broker."""
        print_section("P24 — link_uuid resolution")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P24B")

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )

            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-05-15", "quantity": "-3", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-05-15", "quantity": "3", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["source_broker_id"] == broker_a_id
            assert Decimal(wr["wac"]["amount"]) == Decimal("150")
            print_success("P24 ✓")

    # ------------------------------------------------------------------ P25
    async def test_wacp25_delete_excludes_from_pool(self):
        """delete in batch excludes TX from WAC pool."""
        print_section("P25 — delete affects WAC pool")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-2000"}},
                ],
            )
            buy1_id = setup["results"][1]["ids"][0]

            # Without delete: WAC=(1000+2000)/20=150. With delete of buy1: WAC=2000/10=200
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-01", "quantity": "5", "cost_basis_mode": "auto"},
                ],
                deletes=[buy1_id],
            )

            assert data.get("wac_results") is not None
            assert Decimal(data["wac_results"][0]["wac"]["amount"]) == Decimal("200")
            print_success("P25 ✓")

    # ------------------------------------------------------------------ P26
    async def test_wacp26_intra_batch_buy_affects_wac(self):
        """BUY + TRANSFER auto in same batch → WAC includes the BUY."""
        print_section("P26 — intra-batch BUY in WAC")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P26B")

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "100000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )

            # BUY 10@200 + TRANSFER 5 auto → WAC should be (1000+2000)/20=150
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-04-01", "quantity": "10", "cash": {"code": "EUR", "amount": "-2000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-02", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-02", "quantity": "5", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            assert data.get("wac_results") is not None
            assert Decimal(data["wac_results"][0]["wac"]["amount"]) == Decimal("150")
            print_success("P26 ✓")

    # ------------------------------------------------------------------ P27
    async def test_wacp27_empty_pool_wac_zero(self):
        """TRANSFER auto from empty pool → WAC = 0."""
        print_section("P27 — empty pool → WAC=0")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P27B")

            # No BUYs. WAC computed before balance walk.
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "5", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            if data.get("wac_results") is not None:
                wr = data["wac_results"][0]
                assert wr["wac"] is not None
                assert Decimal(wr["wac"]["amount"]) == Decimal("0")
            print_success("P27 ✓")

    # ------------------------------------------------------------------ P28
    async def test_wacp28_auto_detail_qualifying_effects(self):
        """auto-detail on ADJUSTMENT → qualifying has add + reduce effects."""
        print_section("P28 — qualifying effects")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-02-01", "quantity": "-3", "cash": {"code": "EUR", "amount": "350"}},
                ],
            )

            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-01", "quantity": "2", "cost_basis_mode": "auto-detail"},
                ],
            )

            assert data.get("wac_results") is not None
            wr = data["wac_results"][0]
            assert wr["wac_qualifying_txs"] is not None
            effects = [q["effect"] for q in wr["wac_qualifying_txs"]]
            assert "add" in effects, f"Missing 'add': {effects}"
            assert "reduce" in effects, f"Missing 'reduce': {effects}"
            print_success("P28 ✓")

    # ------------------------------------------------------------------ P29
    async def test_wacp29_missing_fx_returns_pair_with_dates(self):
        """validate auto WAC with cross-currency BUY but no FX rates → wac_missing_pairs has pair+dates."""
        print_section("P29 — missing FX pairs returns pair + dates")
        async with httpx.AsyncClient() as client:
            # Create asset in EUR
            broker_id, asset_id = await create_user_broker_asset(client, currency="EUR")

            # BUY in USD — no FX rate exists for USD/EUR
            # The ADJUSTMENT requests WAC in EUR (via cost_basis_override.code),
            # forcing USD→EUR conversion which will fail due to missing FX rates
            resp = await client.post(
                f"{API_BASE}/transactions/validate",
                json={
                    "creates": [
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2024-03-15", "quantity": "10", "cash": {"code": "USD", "amount": "-500"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2024-04-20", "quantity": "5", "cash": {"code": "USD", "amount": "-300"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2024-05-01", "quantity": "3", "cost_basis_mode": "auto-detail", "cost_basis_override": {"code": "EUR", "amount": "0"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            print(f"P29 validate status: {resp.status_code}")
            assert resp.status_code == 200, f"Validate failed ({resp.status_code}): {resp.text[:500]}"
            data = resp.json()

            # WAC should fail due to missing FX
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            wr = data["wac_results"][0]
            assert wr["wac"] is None, f"Expected wac=None due to missing FX, got: {wr['wac']}"
            assert len(wr["wac_missing_pairs"]) > 0, "Expected wac_missing_pairs to be non-empty"

            # Verify new format: list of {pair, dates}
            mp = wr["wac_missing_pairs"][0]
            assert "pair" in mp, f"Expected 'pair' field in wac_missing_pairs item: {mp}"
            assert "dates" in mp, f"Expected 'dates' field in wac_missing_pairs item: {mp}"
            assert mp["pair"] == "USD/EUR", f"Expected pair 'USD/EUR', got: {mp['pair']}"
            # Should contain dates from both BUY transactions
            assert len(mp["dates"]) >= 2, f"Expected at least 2 dates, got: {mp['dates']}"
            assert "2024-03-15" in mp["dates"], f"Missing date 2024-03-15: {mp['dates']}"
            assert "2024-04-20" in mp["dates"], f"Missing date 2024-04-20: {mp['dates']}"

            # Verify issue is also emitted with pair_details
            fx_issues = [i for i in data.get("issues", []) if i.get("code") == "wacFxUnavailable"]
            assert len(fx_issues) > 0, f"Expected wacFxUnavailable issue, got: {data.get('issues')}"
            issue = fx_issues[0]
            assert "pair_details" in issue["params"], f"Expected pair_details in issue params: {issue['params']}"
            pd = issue["params"]["pair_details"][0]
            assert pd["pair"] == "USD/EUR"
            assert len(pd["dates"]) >= 2

            print_success("P29 ✓")

    # ------------------------------------------------------------------ P30
    async def test_wacp30_full_position_transfer_auto_validate_keeps_source_wac(self):
        """validate TRANSFER auto moving the WHOLE position → WAC of the source pool (100), not 0."""
        print_section("P30 — validate full-position TRANSFER auto → source WAC, not 0")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P30B")

            # Setup: BUY 10 for 1000 EUR on broker_a → WAC 100
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"

            # Validate: the WHOLE position (10 of 10) moves to the empty broker_b, auto WAC on the receiver.
            # The source pool is read post-flush with date <= 2026-04-01, so it also contains the
            # sender's own outgoing leg; applied before the average is read, that leg empties the pool.
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-10", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "10", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )

            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1, f"Expected exactly one wac_results item: {data['wac_results']}"
            wr = data["wac_results"][0]
            assert wr["index"] == 1, f"Expected the WAC of the receiver (create index 1): {wr}"
            assert wr["source_broker_id"] == broker_a_id, f"Expected source broker A={broker_a_id}, got {wr['source_broker_id']} (B={broker_b_id}): {wr}"
            assert wr["wac"] is not None, f"Expected a WAC, got none: {wr}"
            assert Decimal(wr["wac"]["amount"]) == Decimal("100"), f"Full-position TRANSFER: expected the source WAC before the transfer, 100 EUR (BUY 10 for 1000 EUR on A), got {wr['wac']['amount']} {wr['wac']['code']}: {wr}"
            assert wr["wac"]["code"] == "EUR", f"Expected EUR: {wr}"
            print_success("P30 ✓")

    # ------------------------------------------------------------------ P31
    async def test_wacp31_full_position_transfer_auto_commit_persists_source_wac(self):
        """commit TRANSFER auto moving the WHOLE position → receiver row stores the source WAC (100), not 0."""
        print_section("P31 — commit full-position TRANSFER auto → source WAC persisted")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P31B")

            # Setup: BUY 10 for 1000 EUR on broker_a → WAC 100
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"

            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-10", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "10", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
            )
            assert data["committed"] is True, f"Pair not committed: {data}"

            receiver_results = [r for r in data["results"] if r["operation"] == "create" and r["index"] == 1]
            assert len(receiver_results) == 1, f"No create result for the receiver (index 1): {data['results']}"
            receiver_id = receiver_results[0]["ids"][0]
            txs = await get_txs_by_ids(client, [receiver_id])
            assert len(txs) == 1, f"Receiver {receiver_id} not returned: {txs}"
            receiver = txs[0]
            assert receiver["cost_basis_override"] is not None, f"Receiver {receiver_id} stored no cost basis: {receiver}"
            assert Decimal(receiver["cost_basis_override"]["amount"]) == Decimal("100"), f"Full-position TRANSFER: expected receiver {receiver_id} to store the source WAC, 100 EUR, got cost_basis_override={receiver['cost_basis_override']} (wac_results={data.get('wac_results')})"
            assert receiver["cost_basis_override"]["code"] == "EUR", f"Expected EUR: {receiver['cost_basis_override']}"
            print_success("P31 ✓")

    # ------------------------------------------------------------------ P32
    async def test_wacp32_update_transfer_receiver_auto_uses_source_broker(self):
        """update a saved TRANSFER receiver to auto → WAC from the partner's (source) broker, not the receiver's own."""
        print_section("P32 — update TRANSFER receiver to auto → source broker WAC")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P32B")

            # A: BUY 10 for 1000 EUR → WAC 100. B: BUY 4 for 800 EUR → WAC 200 (deliberately different)
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_b_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-03", "quantity": "4", "cash": {"code": "EUR", "amount": "-800"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"

            # Saved TRANSFER A→B of 5, receiver in manual mode
            link = str(uuid.uuid4())
            pair = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "5", "link_uuid": link, "cost_basis_override": {"code": "EUR", "amount": "1"}},
                ],
            )
            assert pair["committed"] is True, f"Pair not committed: {pair}"
            receiver_results = [r for r in pair["results"] if r["operation"] == "create" and r["index"] == 1]
            assert len(receiver_results) == 1, f"No create result for the receiver (index 1): {pair['results']}"
            receiver_id = receiver_results[0]["ids"][0]

            # Switch the saved receiver to auto. An update carries no link_uuid: the partner is the saved row on A.
            data = await validate_batch(
                client,
                updates=[
                    {"id": receiver_id, "cost_basis_mode": "auto"},
                ],
            )

            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1, f"Expected exactly one wac_results item: {data['wac_results']}"
            wr = data["wac_results"][0]
            assert wr["operation"] == "update", f"Expected operation 'update': {wr}"
            assert wr["source_broker_id"] == broker_a_id, f"TRANSFER receiver update: expected source_broker_id = partner's broker A={broker_a_id} (pool WAC 100), got {wr['source_broker_id']} with wac={wr['wac']} (the receiver's own broker is B={broker_b_id}, pool WAC 200): {wr}"
            assert wr["wac"] is not None, f"Expected a WAC, got none: {wr}"
            assert Decimal(wr["wac"]["amount"]) == Decimal("100"), f"TRANSFER receiver update: expected the source (A) WAC 100 EUR, got {wr['wac']}: {wr}"
            print_success("P32 ✓")

    # ------------------------------------------------------------------ P33
    async def test_wacp33_promote_saved_new_auto_uses_source_broker(self):
        """validate saved ADJUSTMENT(-5) promoted with a new ADJUSTMENT(+5) auto → WAC from the saved row's broker."""
        print_section("P33 — promote saved+new, new receiver auto → source broker WAC")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P33B")

            # A: BUY 10 for 1000 EUR → WAC 100, then a saved outgoing ADJUSTMENT -5 (negative: no cost basis)
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"
            adjustment = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-01", "quantity": "-5"},
                ],
            )
            assert adjustment["committed"] is True, f"Saved ADJUSTMENT not committed: {adjustment}"
            adjustment_results = [r for r in adjustment["results"] if r["operation"] == "create" and r["index"] == 0]
            assert len(adjustment_results) == 1, f"No create result for the saved ADJUSTMENT: {adjustment['results']}"
            saved_adj_id = adjustment_results[0]["ids"][0]

            # What the bulk editor sends when a saved row and a new row are promoted into a pair:
            # the new row's link_uuid has no partner among the creates, its partner is the saved row.
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-04-01", "quantity": "5", "link_uuid": link, "cost_basis_mode": "auto"},
                ],
                promotes=[{"id_a": saved_adj_id, "link_uuid_b": link}],
            )

            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            promote_results = [r for r in data["results"] if r["operation"] == "promote"]
            assert len(promote_results) == 1, f"Promote not applied: {data['results']}"
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1, f"Expected exactly one wac_results item: {data['wac_results']}"
            wr = data["wac_results"][0]
            assert wr["source_broker_id"] == broker_a_id, f"Promoted saved+new pair: expected source_broker_id = saved partner's broker A={broker_a_id} (pool WAC 100), got {wr['source_broker_id']} with wac={wr['wac']} (the new receiver's own broker is B={broker_b_id}, empty): {wr}"
            assert wr["wac"] is not None, f"Expected a WAC, got none: {wr}"
            assert Decimal(wr["wac"]["amount"]) == Decimal("100"), f"Promoted saved+new pair: expected the source (A) WAC 100 EUR, got {wr['wac']}: {wr}"
            print_success("P33 ✓")

    # ------------------------------------------------------------------ P34
    async def test_wacp34_update_full_position_transfer_receiver_auto_uses_source_wac(self):
        """update to auto the receiver of a saved TRANSFER that moved the WHOLE position → source (A) WAC before the transfer (100)."""
        print_section("P34 — update full-position TRANSFER receiver to auto → source WAC before the transfer")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P34B")

            # A: BUY 10 for 1000 EUR → WAC 100. B: BUY 4 for 800 EUR → WAC 200 (deliberately different)
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_b_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-03", "quantity": "4", "cash": {"code": "EUR", "amount": "-800"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"

            # Saved TRANSFER A→B of the WHOLE position (10 of 10), receiver in manual mode
            link = str(uuid.uuid4())
            pair = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-10", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "10", "link_uuid": link, "cost_basis_override": {"code": "EUR", "amount": "1"}},
                ],
            )
            assert pair["committed"] is True, f"Pair not committed: {pair}"
            receiver_results = [r for r in pair["results"] if r["operation"] == "create" and r["index"] == 1]
            assert len(receiver_results) == 1, f"No create result for the receiver (index 1): {pair['results']}"
            receiver_id = receiver_results[0]["ids"][0]

            # Switch the saved receiver to auto. The source is the partner's broker A, and the partner's
            # outgoing -10 (same date) must not count: applied before the average, it empties A's pool (WAC 0).
            data = await validate_batch(
                client,
                updates=[
                    {"id": receiver_id, "cost_basis_mode": "auto"},
                ],
            )

            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1, f"Expected exactly one wac_results item: {data['wac_results']}"
            wr = data["wac_results"][0]
            assert wr["operation"] == "update", f"Expected operation 'update': {wr}"
            assert wr["source_broker_id"] == broker_a_id, f"Full-position TRANSFER receiver update: expected source_broker_id = partner's broker A={broker_a_id} (WAC 100 before the transfer), got {wr['source_broker_id']} with wac={wr['wac']} (own broker B={broker_b_id}, pool WAC 200): {wr}"
            assert wr["wac"] is not None, f"Expected a WAC, got none: {wr}"
            assert Decimal(wr["wac"]["amount"]) == Decimal("100"), f"Full-position TRANSFER receiver update: expected the source (A) WAC before the transfer, 100 EUR, got {wr['wac']['amount']} {wr['wac']['code']} (0 = the partner's outgoing -10 was counted): {wr}"
            assert wr["wac"]["code"] == "EUR", f"Expected EUR: {wr}"
            print_success("P34 ✓")

    # ------------------------------------------------------------------ P35
    async def test_wacp35_in_transit_transfer_auto_uses_source_pool_when_units_left(self):
        """validate an in-transit TRANSFER auto with a BUY on A between the two legs → A's pool when the units left (100).

        A holds 10 bought for 1000 EUR on 2026-01-02 (WAC 100). 5 units leave A on 2026-04-01 and reach B on
        2026-04-05; on 2026-04-03, while they are in transit, A buys 5 more at 300 EUR each. The receiver's Auto cost:
        - receiver's date, partner's outgoing leg included (old behaviour): (5×100 + 5×300) / 10 = 200;
        - receiver's date, only the outgoing leg excluded: (10×100 + 5×300) / 15 = 166.67;
        - partner's date, outgoing leg excluded — the source pool when the units left: (10×100) / 10 = 100.
        A purchase on A dated strictly between the two legs must not change the receiver's WAC.
        """
        print_section("P35 — validate in-transit TRANSFER auto → source pool when the units left")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "P35B")

            # Setup: BUY 10 for 1000 EUR on broker_a → WAC 100
            setup = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "100000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert setup["committed"] is True, f"Setup not committed: {setup}"

            # Validate: 5 units leave A on 04-01 and reach B on 04-05, auto WAC on the receiver; on 04-03,
            # while they are in transit, A buys 5 more at 300 EUR each. The receiver averages A's pool as of
            # the partner's date (04-01) without the outgoing leg, so the 04-03 BUY must stay out.
            link = str(uuid.uuid4())
            data = await validate_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-01", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-04-05", "quantity": "5", "link_uuid": link, "cost_basis_mode": "auto"},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-04-03", "quantity": "5", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )

            assert data["committed"] is False, f"validate must not commit: {data}"
            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            assert data.get("wac_results") is not None, f"wac_results missing: {data}"
            assert len(data["wac_results"]) == 1, f"Expected exactly one wac_results item: {data['wac_results']}"
            wr = data["wac_results"][0]
            assert wr["operation"] == "create", f"Expected operation 'create': {wr}"
            assert wr["index"] == 1, f"Expected the WAC of the receiver (create index 1): {wr}"
            assert wr["source_broker_id"] == broker_a_id, f"In-transit TRANSFER: expected source_broker_id = partner's broker A={broker_a_id}, got {wr['source_broker_id']} with wac={wr['wac']} (the receiver's own broker is B={broker_b_id}): {wr}"
            assert wr["wac"] is not None, f"Expected a WAC, got none: {wr}"
            assert Decimal(wr["wac"]["amount"]) == Decimal("100"), f"In-transit TRANSFER: expected A's pool when the units left (2026-04-01), 100 EUR, got {wr['wac']['amount']} {wr['wac']['code']} (200 = receiver's date with the leg, 166.67 = receiver's date without it): {wr}"
            assert wr["wac"]["code"] == "EUR", f"Expected EUR: {wr}"
            print_success("P35 ✓")
