"""Portfolio WAC API Tests (A1-A8). POST /api/v1/portfolio/wac."""

import uuid
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.services import user_service
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
SOLE_ADMIN_DELETE_DETAIL = "Cannot delete account: you are the only administrator"


async def create_test_user(client: httpx.AsyncClient) -> str:
    username = f"anwac_{uuid.uuid4().hex[:8]}"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"}, timeout=TIMEOUT)
    assert resp.status_code == 201
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
    if s := login_resp.cookies.get("session"):
        client.cookies.set("session", s)
    return username


async def get_current_user_id(client: httpx.AsyncClient) -> int:
    resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()["user"]["id"]


async def delete_current_test_user(
    client: httpx.AsyncClient,
    user_id: int,
) -> None:
    """Delete this test's account, including the isolated sole-admin case."""
    response = await client.delete(
        f"{API_BASE}/auth/users/me",
        timeout=TIMEOUT,
    )
    if (
        response.status_code == 400
        and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL
    ):
        is_test_db, _ = verify_test_database()
        assert is_test_db, "Refusing sole-admin cleanup outside the test database"
        async with AsyncSession(get_async_engine()) as session:
            assert await user_service.delete_user(session, user_id)
        return
    assert response.status_code == 200, response.text


async def create_broker(client: httpx.AsyncClient) -> int:
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": f"AnBk_{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200
    return resp.json()["results"][0]["broker_id"]


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"AnAs_{uuid.uuid4().hex[:6]}", "currency": currency, "asset_type": "STOCK"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201)
    return resp.json()["results"][0]["asset_id"]


async def setup_env(client: httpx.AsyncClient, *, currency: str = "EUR") -> tuple[int, int]:
    await create_test_user(client)
    return await create_broker(client), await create_asset(client, currency=currency)


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    resp = await client.post(f"{API_BASE}/transactions/commit", json=kwargs, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Commit HTTP failed: {resp.status_code}"
    data = resp.json()
    assert data.get("committed") is True, f"Not committed: {data.get('issues', [])}"
    return data


async def portfolio_wac(client: httpx.AsyncClient, queries: list[dict]) -> dict:
    resp = await client.post(f"{API_BASE}/portfolio/wac", json={"queries": queries}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Portfolio WAC failed: {resp.status_code}: {resp.text}"
    return resp.json()


async def create_split_event(client: httpx.AsyncClient, asset_id: int, event_date: str, ratio: str, currency: str = "EUR") -> int:
    """Create a manual SPLIT AssetEvent (value = ratio) and return its id.

    Mirrors how yahoo_finance.py populates SPLIT events: `value` carries the
    ratio (e.g. "2" for a 2:1 split, "0.5" for a 1:2 reverse split), `currency`
    is set to the asset's currency but is not semantically meaningful for SPLIT.
    """
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"date": event_date, "type": "SPLIT", "value": {"code": currency, "amount": ratio}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Event upsert failed: {resp.status_code}: {resp.text}"
    query_resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[{"asset_id": asset_id, "date_range": {"start": event_date, "end": event_date}}],
        timeout=TIMEOUT,
    )
    assert query_resp.status_code == 200, f"Event query failed: {query_resp.status_code}: {query_resp.text}"
    events = query_resp.json()["items"][0]["events"]
    split_events = [e for e in events if e["type"] == "SPLIT"]
    assert len(split_events) == 1, f"Expected 1 SPLIT event, got {events}"
    return split_events[0]["id"]


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as mgr:
        if not mgr.start_server():
            pytest.fail("Failed to start test server")
        yield mgr


@pytest.mark.asyncio
class TestPortfolioWAC:
    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        pass

    async def test_a1_empty_pool(self):
        """A1: No transactions -> empty series."""
        print_section("A1: Empty pool")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            assert result["results"][0]["series"] == []
            print_success("OK empty series")

    async def test_a2_single_buy(self):
        """A2: Single BUY -> 1 point, WAC = unit price."""
        print_section("A2: Single BUY")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 1
            assert s[0]["date"] == "2026-01-15"
            assert Decimal(s[0]["wac"]) == Decimal("50")
            assert Decimal(s[0]["pool_qty"]) == Decimal("10")
            assert s[0]["effect"] == "add"
            print_success("OK WAC=50 qty=10")

    async def test_a3_evolving_wac(self):
        """A3: Multiple BUYs -> WAC evolves."""
        print_section("A3: Evolving WAC")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-01", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-15", "quantity": "5", "cash": {"code": "EUR", "amount": "-800"}},
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert Decimal(s[0]["wac"]) == Decimal("100")
            assert Decimal(s[1]["wac"]) == Decimal("120")
            assert Decimal(s[1]["pool_qty"]) == Decimal("15")
            print_success("OK WAC 100->120")

    async def test_a4_date_range_filter(self):
        """A4: date_range filters series."""
        print_section("A4: date_range filter")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-700"}},
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-02-01", "end": "2026-03-31"}}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert s[0]["date"] == "2026-02-10"
            assert s[1]["date"] == "2026-03-10"
            print_success("OK filtered Feb-Mar")

    async def test_a5_sell_reduces_pool(self):
        """A5: SELL reduces pool, WAC unchanged."""
        print_section("A5: SELL reduces pool")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-20", "quantity": "-3", "cash": {"code": "EUR", "amount": "450"}},
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert Decimal(s[1]["wac"]) == Decimal("100")
            assert Decimal(s[1]["pool_qty"]) == Decimal("7")
            assert s[1]["effect"] == "reduce"
            print_success("OK SELL pool 10->7")

    async def test_a6_authorized_broker_with_verified_missing_asset(self):
        """A6: An authorized Broker plus a verified-missing Asset -> empty series."""
        print_section("A6: Authorized Broker with missing Asset")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            user_id = await get_current_user_id(client)
            broker_id = None
            asset_id = None
            asset_deleted = False
            try:
                broker_id = await create_broker(client)
                asset_id = await create_asset(client)
                deleted = await client.delete(
                    f"{API_BASE}/assets",
                    params={"asset_ids": [asset_id]},
                    timeout=TIMEOUT,
                )
                assert deleted.status_code == 200, deleted.text
                deleted_row = next(
                    row
                    for row in deleted.json()["results"]
                    if row["asset_id"] == asset_id
                )
                assert deleted_row["success"] is True
                asset_deleted = True

                result = await portfolio_wac(
                    client,
                    [{"broker_id": broker_id, "asset_id": asset_id}],
                )
                missing_asset_result = next(
                    row
                    for row in result["results"]
                    if row["broker_id"] == broker_id
                    and row["asset_id"] == asset_id
                )
                assert missing_asset_result["series"] == []
                print_success("OK graceful empty")
            finally:
                if asset_id is not None and not asset_deleted:
                    await client.delete(
                        f"{API_BASE}/assets",
                        params={"asset_ids": [asset_id]},
                        timeout=TIMEOUT,
                    )
                if broker_id is not None:
                    cleanup = await client.delete(
                        f"{API_BASE}/brokers",
                        params={"ids": [broker_id], "force": True},
                        timeout=TIMEOUT,
                    )
                    assert cleanup.status_code == 200, cleanup.text
                await delete_current_test_user(client, user_id)

    async def test_a7_open_range_end_only(self):
        """A7: OpenDateRangeModel end only -> history up to end."""
        print_section("A7: Open range (end only)")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id, "date_range": {"end": "2026-02-01"}}])
            s = result["results"][0]["series"]
            assert len(s) == 1
            assert s[0]["date"] == "2026-01-10"
            print_success("OK end=Feb -> only Jan")

    async def test_a8_multiple_queries(self):
        """A8: Multiple queries -> results in order."""
        print_section("A8: Multiple queries")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset1 = await create_asset(client, currency="EUR")
            asset2 = await create_asset(client, currency="USD")
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset1, "type": "BUY", "date": "2026-01-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            result = await portfolio_wac(
                client,
                [
                    {"broker_id": broker_id, "asset_id": asset1},
                    {"broker_id": broker_id, "asset_id": asset2},
                ],
            )
            assert len(result["results"]) == 2
            assert len(result["results"][0]["series"]) == 1
            assert len(result["results"][1]["series"]) == 0
            print_success("OK batch query")


# ============================================================
# Retyping the SPLIT event a split ADJUSTMENT links to (workstream I)
# ============================================================
#
# The event editor may change the type of an event a transaction links to; the
# developer decided this is allowed and the link is kept. For a SPLIT this changes
# what the linked ADJUSTMENT means to the cost pool, because a split is recognised
# by a live join on the linked event's type:
#
# * portfolio_service.compute_wac_iterative treats an ADJUSTMENT as split-linked only
#   while its AssetEvent.type == SPLIT, and adds that set to the WAC cache fingerprint,
#   so a retype is picked up although the transaction itself is not touched;
# * average_cost.cost_movement_from_transaction rescales the pool for a split-linked
#   row; otherwise a negative quantity is a REDUCTION, and a positive one is an
#   acquisition costing its cost_basis_override, or an unknown cost when there is none.
#
# The two tests below pin that consequence down. Before the fix (108a2adf5) both
# failed at the retype itself: the upsert point had no ``id`` field, so the request
# was rejected with 422.


def _created_tx_id(result: dict, index: int = 0) -> int:
    """Id of the transaction produced by the ``index``-th create of a commit."""
    return next(r for r in result["results"] if r["operation"] == "create" and r["index"] == index)["ids"][0]


async def _read_tx(client: httpx.AsyncClient, tx_id: int) -> dict:
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": [tx_id]}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(t for t in resp.json() if t["id"] == tx_id)


async def _wac_points(client: httpx.AsyncClient, broker_id: int, asset_id: int) -> dict[str, dict]:
    """The WAC series of one position, keyed by date (one transaction per date in these tests)."""
    result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
    series = next(r for r in result["results"] if r["broker_id"] == broker_id and r["asset_id"] == asset_id)["series"]
    points = {p["date"]: p for p in series}
    assert len(points) == len(series), f"expected one point per date: {series}"
    return points


def _assert_point(points: dict[str, dict], day: str, *, effect: str, wac: str, pool_qty: str) -> None:
    assert day in points, f"no WAC point on {day}: {points}"
    point = points[day]
    assert point["effect"] == effect, point
    assert Decimal(str(point["wac"])) == Decimal(wac), point
    assert Decimal(str(point["pool_qty"])) == Decimal(pool_qty), point


async def _retype_event(client: httpx.AsyncClient, asset_id: int, event_id: int, event_date: str, new_type: str, amount: str, currency: str = "EUR") -> None:
    """Edit event ``event_id`` in place, by id, as the event editor does."""
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"id": event_id, "date": event_date, "type": new_type, "value": {"code": currency, "amount": amount}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Retyping event {event_id} failed: {resp.status_code}: {resp.text}"


async def _events_on_date(client: httpx.AsyncClient, asset_id: int, event_date: str) -> list[tuple[int, str]]:
    resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[{"asset_id": asset_id, "date_range": {"start": event_date, "end": event_date}}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    events = next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["events"]
    return [(e["id"], e["type"]) for e in events]


async def _drop_broker(client: httpx.AsyncClient, broker_id: int) -> list[str]:
    """Force-delete a broker together with its transactions. Never raises."""
    try:
        resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
        done = resp.status_code == 200 and any(r.get("id") == broker_id and r.get("success") for r in resp.json().get("results", []))
    except Exception as exc:
        return [f"broker {broker_id}: {exc!r}"]
    return [] if done else [f"broker {broker_id}: HTTP {resp.status_code} {resp.text}"]


async def _drop_asset(client: httpx.AsyncClient, asset_id: int) -> list[str]:
    """Delete an asset (its events cascade). Never raises."""
    try:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        done = resp.status_code == 200 and any(r.get("asset_id") == asset_id and r.get("success") for r in resp.json().get("results", []))
    except Exception as exc:
        return [f"asset {asset_id}: {exc!r}"]
    return [] if done else [f"asset {asset_id}: HTTP {resp.status_code} {resp.text}"]


async def _drop_wac_env(client: httpx.AsyncClient, *, user_id: int, broker_id: int, asset_id: int) -> list[str]:
    """Undo setup_env in FK-safe order: broker (with its transactions), asset (with its events), user."""
    problems = await _drop_broker(client, broker_id) + await _drop_asset(client, asset_id)
    try:
        await delete_current_test_user(client, user_id)
    except Exception as exc:  # report it next to the others instead of masking the test's own outcome
        problems.append(f"user {user_id}: {exc!r}")
    return problems


@pytest.mark.asyncio
class TestPortfolioWACSplit:
    """Regression coverage: SPLIT-linked ADJUSTMENT rescales WAC instead of add/reduce.

    Fase 0 fix (fifo-engine reports 1-6): the "auto" cost-basis fallback used to
    write the *current* WAC as cost_basis_override for ANY auto-mode item —
    including SPLIT-linked ADJUSTMENTs — doubling total cost for forward splits
    and halving it for reverse splits instead of preserving it.
    """

    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        pass

    async def test_forward_split_preserves_total_cost(self):
        """BUY 15@100 (cost 1500) + SPLIT-linked ADJUSTMENT +15 (auto) -> WAC=50, not 100."""
        print_section("Split A1: Forward split preserves total cost")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "15", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )
            event_id = await create_split_event(client, asset_id, "2026-02-01", "2")
            adj_result = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_id,
                        "asset_id": asset_id,
                        "type": "ADJUSTMENT",
                        "date": "2026-02-01",
                        "quantity": "15",
                        "asset_event_id": event_id,
                        "cost_basis_mode": "auto",
                    },
                ],
            )
            # transaction_service.py hygiene fix: auto-mode must NOT write "current
            # WAC" as cost_basis_override for a SPLIT-linked item (it would be
            # misleading — WAC/FIFO ignore it regardless: a split only rescales the
            # pool, see financial_math/average_cost.py).
            assert adj_result["wac_results"][0]["wac"] is None
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert Decimal(s[0]["wac"]) == Decimal("100")
            assert Decimal(s[0]["pool_qty"]) == Decimal("15")
            # Without the fix, this would be 100 (doubling total cost to 3000).
            assert Decimal(s[1]["wac"]) == Decimal("50")
            assert Decimal(s[1]["pool_qty"]) == Decimal("30")
            assert Decimal(s[1]["wac"]) * Decimal(s[1]["pool_qty"]) == Decimal("1500")
            print_success("OK forward split: 15@100 -> 30@50, cost 1500 preserved")

    async def test_reverse_split_preserves_total_cost(self):
        """BUY 30@50 (cost 1500) + SPLIT-linked ADJUSTMENT -15 (auto) -> WAC=100, not 50."""
        print_section("Split A2: Reverse split preserves total cost")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "30", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )
            event_id = await create_split_event(client, asset_id, "2026-02-01", "0.5")
            await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_id,
                        "asset_id": asset_id,
                        "type": "ADJUSTMENT",
                        "date": "2026-02-01",
                        "quantity": "-15",
                        "asset_event_id": event_id,
                        # NOTE: cost_basis_mode is rejected by business validation for
                        # ADJUSTMENT qty<0 ("only valid for qty>0") — the split rescale
                        # fix is keyed purely on asset_event_id -> AssetEvent.type==SPLIT,
                        # so a plain reduction (no cost_basis_mode at all) is the correct
                        # and only reachable shape for a reverse split via this API today.
                    },
                ],
            )
            result = await portfolio_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            # Without the fix, this would stay 50 (halving total cost to 750).
            assert Decimal(s[1]["wac"]) == Decimal("100")
            assert Decimal(s[1]["pool_qty"]) == Decimal("15")
            assert Decimal(s[1]["wac"]) * Decimal(s[1]["pool_qty"]) == Decimal("1500")
            print_success("OK reverse split: 30@50 -> 15@100, cost 1500 preserved")

    async def test_forward_split_relabelled_as_price_adjustment_becomes_an_unknown_cost_acquisition(self):
        """Retyping a forward SPLIT to PRICE_ADJUSTMENT makes its +15 ADJUSTMENT 15 shares of UNKNOWN cost.

        BUY 15 for 1500 EUR, SPLIT "2" on 2026-02-01, ADJUSTMENT +15 linked to it with
        cost_basis_mode auto. For a split-linked row, auto mode stores no cost_basis_override.
        Before the retype the ADJUSTMENT rescales the pool: split_rescale, 30 shares, WAC 50.

        After the event becomes a PRICE_ADJUSTMENT, the ADJUSTMENT keeps its link but is no
        longer split-linked. It is therefore an acquisition with no cost basis: effect
        add_zero_cost (the preview's name for an add of unknown cost), and the pool's cost
        becomes INCOMPLETE. The numbers shown do not move (30 shares, WAC 50, cost 1500), but
        their meaning does: the 1500 now covers only the 15 bought shares, and the other 15
        entered at a cost nobody knows. Nothing in this series tells the two cases apart.

        Before the fix: failed at the retype itself, with 422 (the upsert point had no ``id`` field).
        """
        print_section("Split A3: forward SPLIT retyped to PRICE_ADJUSTMENT")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            user_id = await get_current_user_id(client)
            try:
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "15", "cash": {"code": "EUR", "amount": "-1500"}},
                    ],
                )
                event_id = await create_split_event(client, asset_id, "2026-02-01", "2")
                adj_result = await commit_batch(
                    client,
                    creates=[
                        {
                            "broker_id": broker_id,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-02-01",
                            "quantity": "15",
                            "asset_event_id": event_id,
                            "cost_basis_mode": "auto",
                        },
                    ],
                )
                adj_tx_id = _created_tx_id(adj_result)
                adj_tx = await _read_tx(client, adj_tx_id)
                assert adj_tx["asset_event_id"] == event_id, adj_tx
                # Precondition of the AFTER half: with an override the retyped row would be a
                # costed acquisition ("add"), not an acquisition of unknown cost.
                assert adj_tx["cost_basis_override"] is None, adj_tx

                before = await _wac_points(client, broker_id, asset_id)
                assert set(before) == {"2026-01-15", "2026-02-01"}, before
                _assert_point(before, "2026-01-15", effect="add", wac="100", pool_qty="15")
                _assert_point(before, "2026-02-01", effect="split_rescale", wac="50", pool_qty="30")

                await _retype_event(client, asset_id, event_id, "2026-02-01", "PRICE_ADJUSTMENT", "2")

                assert await _events_on_date(client, asset_id, "2026-02-01") == [(event_id, "PRICE_ADJUSTMENT")]
                assert (await _read_tx(client, adj_tx_id))["asset_event_id"] == event_id
                after = await _wac_points(client, broker_id, asset_id)
                assert set(after) == {"2026-01-15", "2026-02-01"}, after
                _assert_point(after, "2026-01-15", effect="add", wac="100", pool_qty="15")
                _assert_point(after, "2026-02-01", effect="add_zero_cost", wac="50", pool_qty="30")
                print_success("OK forward split retyped: +15 is now an unknown-cost add, 30@50 unchanged")
            finally:
                problems = await _drop_wac_env(client, user_id=user_id, broker_id=broker_id, asset_id=asset_id)
        assert not problems, problems

    async def test_reverse_split_relabelled_as_price_adjustment_becomes_a_reduction(self):
        """Retyping a reverse SPLIT to PRICE_ADJUSTMENT makes its -15 ADJUSTMENT a sale-like REDUCTION.

        BUY 30 for 1500 EUR, SPLIT "0.5" on 2026-02-01, ADJUSTMENT -15 linked to it (no
        cost_basis_mode: it is rejected for qty < 0). Before the retype the ADJUSTMENT
        rescales the pool: split_rescale, 15 shares, WAC 100, total cost 1500 preserved.

        After the event becomes a PRICE_ADJUSTMENT, the ADJUSTMENT is a plain reduction. It
        takes away 15 of the 30 shares together with their share of the cost, so the total
        cost HALVES to 750 and the WAC falls back to 50: effect reduce, 15 shares, WAC 50.

        Before the fix: failed at the retype itself, with 422 (the upsert point had no ``id`` field).
        """
        print_section("Split A4: reverse SPLIT retyped to PRICE_ADJUSTMENT")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            user_id = await get_current_user_id(client)
            try:
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "30", "cash": {"code": "EUR", "amount": "-1500"}},
                    ],
                )
                event_id = await create_split_event(client, asset_id, "2026-02-01", "0.5")
                adj_result = await commit_batch(
                    client,
                    creates=[{"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-02-01", "quantity": "-15", "asset_event_id": event_id}],
                )
                adj_tx_id = _created_tx_id(adj_result)
                assert (await _read_tx(client, adj_tx_id))["asset_event_id"] == event_id

                before = await _wac_points(client, broker_id, asset_id)
                assert set(before) == {"2026-01-15", "2026-02-01"}, before
                _assert_point(before, "2026-01-15", effect="add", wac="50", pool_qty="30")
                _assert_point(before, "2026-02-01", effect="split_rescale", wac="100", pool_qty="15")

                await _retype_event(client, asset_id, event_id, "2026-02-01", "PRICE_ADJUSTMENT", "0.5")

                assert await _events_on_date(client, asset_id, "2026-02-01") == [(event_id, "PRICE_ADJUSTMENT")]
                assert (await _read_tx(client, adj_tx_id))["asset_event_id"] == event_id
                after = await _wac_points(client, broker_id, asset_id)
                assert set(after) == {"2026-01-15", "2026-02-01"}, after
                _assert_point(after, "2026-01-15", effect="add", wac="50", pool_qty="30")
                _assert_point(after, "2026-02-01", effect="reduce", wac="50", pool_qty="15")
                print_success("OK reverse split retyped: -15 is now a reduction, 15@50, total cost 750")
            finally:
                problems = await _drop_wac_env(client, user_id=user_id, broker_id=broker_id, asset_id=asset_id)
        assert not problems, problems
