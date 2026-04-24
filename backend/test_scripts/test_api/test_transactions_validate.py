"""
Test Suite: POST /transactions/validate (dry-run mixed batch)

Covers Phase 7 Part 3 Blocco C.1 + Blocco G.3.

Contract under test (see ``backend/app/services/transaction_service.py``
L558 ``validate_batch`` + ``backend/app/api/v1/transactions.py`` L228):

- **Pure dry-run**: applies deletes → updates → creates in ONE session
  that is **always rolled back**. No DB mutation is visible after the
  call, regardless of success/failure.
- **Collects all issues** (never stops at the first) — each issue is a
  ``TXValidationIssue`` with ``operation``, ``index``, ``ref_id``, ``error``.
- ``would_rollback=True`` iff any issue OR a balance violation exists.
- ``balance_preview`` / ``holdings_preview`` are populated **only** on
  a clean batch (``would_rollback=False``); keys are
  ``"{broker_id}:{currency}"`` for cash and
  ``"{broker_id}:asset:{asset_id}"`` for holdings.
- Balance violation on a broker that does NOT allow overdraft/shorting
  produces an issue *and* ``would_rollback=True``; preview dicts stay
  empty.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.3.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ============================================================================
# Fixtures & helpers
# ============================================================================


def _uname() -> str:
    return f"g3_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> None:
    username = _uname()
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


async def _create_broker(client: httpx.AsyncClient, *, allow_cash_overdraft: bool, allow_asset_shorting: bool = True) -> int:
    """Create a broker with configurable overdraft/shorting flags."""
    payload = [
        {
            "name": f"G3 Broker {uuid.uuid4().hex[:6]}",
            "allow_cash_overdraft": allow_cash_overdraft,
            "allow_asset_shorting": allow_asset_shorting,
        }
    ]
    resp = await client.post(f"{API_BASE}/brokers", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()["results"][0]["broker_id"]


async def _create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    payload = [{"display_name": f"G3 Asset {uuid.uuid4().hex[:6]}", "currency": currency, "asset_type": "STOCK"}]
    resp = await client.post(f"{API_BASE}/assets", json=payload, timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["results"][0]["asset_id"]


async def _post_tx(client: httpx.AsyncClient, items: list[dict]) -> list[int]:
    """Actually persist transactions; return their IDs."""
    resp = await client.post(f"{API_BASE}/transactions/bulk", json=items, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids: list[int] = []
    for r in body.get("results", []):
        assert r.get("success"), f"create failed: {r}"
        ids.append(r["transaction_id"])
    return ids


async def _validate(
    client: httpx.AsyncClient,
    *,
    creates: list[dict] | None = None,
    updates: list[dict] | None = None,
    deletes: list[int] | None = None,
) -> dict:
    payload = {
        "creates": creates or [],
        "updates": updates or [],
        "deletes": deletes or [],
    }
    resp = await client.post(f"{API_BASE}/transactions/validate", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _list_txs(client: httpx.AsyncClient, broker_id: int) -> list[dict]:
    resp = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_id}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # GET /transactions returns a raw list (List[TXReadItem]).
    if isinstance(data, list):
        return data
    return data.get("items") or data.get("results") or []


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_clean_batch_populates_previews(test_server):
    """Clean create-only batch → would_rollback=False + previews populated."""
    print_section("G.3.1 — clean batch populates balance/holdings preview")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await _create_broker(client, allow_cash_overdraft=True)
        asset_id = await _create_asset(client)
        today = date.today()

        body = await _validate(
            client,
            creates=[
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": today.isoformat(),
                    "cash": {"code": "EUR", "amount": "10000"},
                },
                {
                    "broker_id": broker_id,
                    "asset_id": asset_id,
                    "type": "BUY",
                    "date": today.isoformat(),
                    "quantity": "5",
                    "cash": {"code": "EUR", "amount": "-500"},
                },
            ],
        )
        assert body["would_rollback"] is False, body
        assert body["issues"] == []
        assert body["balance_preview"].get(f"{broker_id}:EUR") == "9500.00" or Decimal(
            body["balance_preview"][f"{broker_id}:EUR"]
        ) == Decimal("9500"), body["balance_preview"]
        assert Decimal(body["holdings_preview"][f"{broker_id}:asset:{asset_id}"]) == Decimal("5")
        print_success(
            f"cash preview={body['balance_preview'][f'{broker_id}:EUR']}, "
            f"holdings={body['holdings_preview'][f'{broker_id}:asset:{asset_id}']}"
        )


@pytest.mark.asyncio
async def test_validate_never_persists(test_server):
    """Validate must NEVER persist — DB unchanged after a clean call."""
    print_section("G.3.2 — dry-run never commits")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await _create_broker(client, allow_cash_overdraft=True)
        today = date.today()

        before = await _list_txs(client, broker_id)
        body = await _validate(
            client,
            creates=[
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": today.isoformat(),
                    "cash": {"code": "EUR", "amount": "777"},
                }
            ],
        )
        assert body["would_rollback"] is False
        after = await _list_txs(client, broker_id)
        # Lists should be identical — dry-run rolled back the create.
        assert len(after) == len(before), f"DB mutated: before={len(before)} after={len(after)}"
        print_success(f"DB unchanged after validate (rows before/after = {len(before)})")


@pytest.mark.asyncio
async def test_validate_collects_all_issues(test_server):
    """Multiple bad ops in one batch → each surfaces as its own issue."""
    print_section("G.3.3 — collects all issues (no early stop)")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)

        # NOTE: we can't mix a malformed `create` here because Pydantic
        # rejects structurally-invalid payloads at schema-validation time
        # (BEFORE ``validate_batch`` runs), returning a 422 instead of the
        # service-level TXValidationIssue we want to exercise. Ghost
        # updates+deletes are enough to show that both op categories
        # contribute issues independently — the "never stops at first"
        # invariant is covered by observing ≥2 issues from ≥2 ops.
        body = await _validate(
            client,
            updates=[
                {"id": 999999997, "description": "ghost u1"},
                {"id": 999999998, "description": "ghost u2"},
            ],
            deletes=[999999999],
        )
        assert body["would_rollback"] is True
        issues = body["issues"]
        ops = sorted({i["operation"] for i in issues})
        assert "delete" in ops, body
        assert "update" in ops, body
        assert len(issues) >= 3, f"expected ≥3 issues, got {len(issues)}"
        # Preview dicts must be empty on a dirty batch.
        assert body["balance_preview"] == {}
        assert body["holdings_preview"] == {}
        print_success(f"Collected {len(issues)} issues across ops: {ops}")


@pytest.mark.asyncio
async def test_validate_flags_balance_violation(test_server):
    """Broker without overdraft → negative cash preview triggers balance issue."""
    print_section("G.3.4 — balance violation → would_rollback=True + no preview")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await _create_broker(client, allow_cash_overdraft=False, allow_asset_shorting=False)
        today = date.today()

        body = await _validate(
            client,
            creates=[
                {
                    "broker_id": broker_id,
                    "type": "WITHDRAWAL",
                    "date": today.isoformat(),
                    "cash": {"code": "EUR", "amount": "-500"},
                }
            ],
        )
        assert body["would_rollback"] is True, body
        assert body["issues"], "expected at least one balance-violation issue"
        # Previews must stay empty on a violating batch.
        assert body["balance_preview"] == {}
        assert body["holdings_preview"] == {}
        print_success(f"Balance violation surfaced: {body['issues'][0]['error'][:80]}")


@pytest.mark.asyncio
async def test_validate_update_delete_existing_tx(test_server):
    """Validate an update+delete against REAL persisted txs — no DB change."""
    print_section("G.3.5 — update+delete on real txs is rolled back")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await _create_broker(client, allow_cash_overdraft=True)
        today = date.today()

        ids = await _post_tx(
            client,
            [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": today.isoformat(),
                    "cash": {"code": "EUR", "amount": "1000"},
                },
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": today.isoformat(),
                    "cash": {"code": "EUR", "amount": "2000"},
                },
            ],
        )
        assert len(ids) == 2

        body = await _validate(
            client,
            updates=[{"id": ids[0], "description": "would-be-updated"}],
            deletes=[ids[1]],
        )
        assert body["would_rollback"] is False, body
        assert body["issues"] == []
        # Post-validate previews reflect the hypothetical state:
        # after deleting tx #2 (€2000), only tx #1 (€1000) survives.
        assert Decimal(body["balance_preview"][f"{broker_id}:EUR"]) == Decimal("1000")

        # Verify rollback: both txs must still be present with the original
        # description (NOT "would-be-updated").
        all_txs = await _list_txs(client, broker_id)
        desc_for_tx0 = next((t.get("description") for t in all_txs if t.get("id") == ids[0]), None)
        surviving_ids = {t.get("id") for t in all_txs}
        assert ids[0] in surviving_ids and ids[1] in surviving_ids, surviving_ids
        assert desc_for_tx0 != "would-be-updated", f"update leaked: {desc_for_tx0}"
        print_success("Update + delete dry-run rolled back — DB intact")


@pytest.mark.asyncio
async def test_validate_ghost_id_reports_not_found(test_server):
    """Update/delete targeting non-existent tx IDs → 'not found' issues."""
    print_section("G.3.6 — ghost tx IDs reported per-op")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        # No broker/asset needed — only lookups.

        body = await _validate(
            client,
            updates=[{"id": 987654321, "description": "ghost"}],
            deletes=[987654322],
        )
        assert body["would_rollback"] is True
        ref_ids = {i.get("ref_id") for i in body["issues"]}
        assert 987654321 in ref_ids, body
        assert 987654322 in ref_ids, body
        for issue in body["issues"]:
            if issue.get("ref_id") in {987654321, 987654322}:
                assert "not found" in issue["error"].lower()
        print_info(f"Per-op not-found issues: {len(body['issues'])}")
        print_success("Ghost IDs correctly surfaced per operation")




