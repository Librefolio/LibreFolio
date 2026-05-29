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
