"""Live contract of the PAC planner behind the Tool platform (C0b, TB1).

test_tools_api.py pins the platform's own transport: catalog shape, unknown
tools, envelope sanitization, disconnects. This file drives the one Tool the
application ships, ``pac_allocator`` / ``plan``, end to end through
``POST /tools/compute``: a real worker process, the real planner, the real wire
codec.

* Authentication is not repeated here: the 401 on every Tool endpoint, compute
  included, is ``test_tools_endpoints_require_authentication`` in
  test_tools_api.py.
* The Tool identity (contract, implementation, schema fingerprint) is read from
  the served catalog, never hard-coded. The fingerprint value itself is pinned
  by the schema suite (test_pac_planner_schemas.py).
* A batch never holds more than two items that need a worker: the platform runs
  two lanes, and a third item would measure queue time instead of the contract.

Each test registers its own user and deletes it before returning; nothing else
is written.
"""

from __future__ import annotations

import copy
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.pac_allocator import PAC_PLAN_INPUT_ADAPTER, PAC_PLAN_OUTPUT_ADAPTER
from backend.app.services import user_service
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
# The plan operation's client deadline is 65 s (tool_plugins/pac_allocator.py):
# the transport must outwait it, or a slow worker reads as a transport error.
COMPUTE_TIMEOUT = 70.0
PASSWORD = "PacToolApiPass123!"
SOLE_ADMIN_DELETE_DETAIL = "Cannot delete account: you are the only administrator"

TOOL_CODE = "pac_allocator"
IDENTITY_KEYS = ("tool_code", "contract_version", "implementation_version", "schema_fingerprint")
MIN_REQUEST_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "pac_plan_request.min.v2.json"


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ---------------------------------------------------------------------------
# A user of our own for the length of one test
# ---------------------------------------------------------------------------


async def _register_and_login(client: httpx.AsyncClient) -> int:
    username = f"pac_tool_{uuid4().hex[:16]}"
    registered = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
        timeout=TIMEOUT,
    )
    assert registered.status_code == 201, registered.text
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": PASSWORD}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    assert session is not None
    client.cookies.set("session", session)
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200, me.text
    return me.json()["user"]["id"]


async def _delete_own_user(client: httpx.AsyncClient, user_id: int) -> None:
    """Delete only this test's account, with the exact sole-admin fallback."""
    response = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
    if response.status_code == 400 and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL:
        is_test_db, _ = verify_test_database()
        assert is_test_db, "Refusing sole-admin cleanup outside the test database"
        async with AsyncSession(get_async_engine()) as session:
            assert await user_service.delete_user(session, user_id)
        return
    assert response.status_code == 200, response.text


@asynccontextmanager
async def _tool_user() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        user_id = await _register_and_login(client)
        try:
            yield client
        finally:
            await _delete_own_user(client, user_id)


# ---------------------------------------------------------------------------
# Catalog identity, compute envelope, parameters
# ---------------------------------------------------------------------------


async def _served_descriptor(client: httpx.AsyncClient) -> dict:
    response = await client.get(f"{API_BASE}/tools/catalog", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    descriptor = next((item for item in response.json()["items"] if item["tool_code"] == TOOL_CODE), None)
    assert descriptor is not None, "pac_allocator is not served by the catalog"
    return descriptor


async def _served_identity(client: httpx.AsyncClient) -> dict[str, str]:
    descriptor = await _served_descriptor(client)
    return {key: descriptor[key] for key in IDENTITY_KEYS}


async def _served_engine_timeout_ms(client: httpx.AsyncClient, operation: str) -> int:
    """The engine window a worker claims for ``operation``: the catalog serves the effective policy the executor enforces."""
    policies = (await _served_descriptor(client))["operations"]
    policy = next((policy for policy in policies if policy["operation"] == operation), None)
    assert policy is not None, f"{TOOL_CODE} serves no {operation!r} operation"
    return policy["engine_timeout_ms"]


def _item(identity: dict[str, str], parameters: dict, **identity_overrides: str) -> dict:
    return {"correlation_id": f"pac-{uuid4().hex}", **identity, **identity_overrides, "parameters": parameters}


async def _compute(client: httpx.AsyncClient, *items: dict) -> tuple[dict, dict[str, dict]]:
    """One batch; returns the envelope and its results keyed by correlation id."""
    envelope = {"request_id": f"pac-request-{uuid4().hex}", "items": list(items)}
    response = await client.post(f"{API_BASE}/tools/compute", json=envelope, timeout=COMPUTE_TIMEOUT)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["request_id"] == envelope["request_id"]
    assert [result["correlation_id"] for result in payload["results"]] == [item["correlation_id"] for item in items]
    return payload, {result["correlation_id"]: result for result in payload["results"]}


def _min_request() -> dict:
    return json.loads(MIN_REQUEST_FIXTURE.read_text(encoding="utf-8"))


def _buying_request() -> dict:
    """The min fixture with €50 against its €10 whole unit: five units to buy.

    Unmodified, the fixture holds €5, so doing nothing is the proven optimum.
    """
    payload = _min_request()
    for cash in payload["existing_cash"]:
        cash["available"]["amount"] = "50.00"
        cash["selected"]["amount"] = "50.00"
    return payload


def _unpriced_request() -> dict:
    """A draft whose only Asset has no quote yet."""
    payload = _min_request()
    asset = next(row for row in payload["assets"] if row["asset_id"] == "asset-one")
    asset["quote"] = None
    return payload


def _rounding_tie_request() -> dict:
    """The min fixture at €33.335 a whole unit with €100.00 of cash: a HALF_UP tie.

    The fixture already trades in EUR with a zero fee. SCIP buys three units
    (€100.005 at the exact price), whose BUY debit posts HALF_UP as €100.01:
    broker-one/EUR ends one cent short, over one rounded posting.
    """
    payload = _min_request()
    asset = next(row for row in payload["assets"] if row["asset_id"] == "asset-one")
    asset["quote"]["amount"] = "33.335"
    for cash in payload["existing_cash"]:
        cash["available"]["amount"] = "100.00"
        cash["selected"]["amount"] = "100.00"
    return payload


def _other_version(version: str) -> str:
    major, _, rest = version.partition(".")
    return f"{int(major) + 1}.{rest}"


def _other_fingerprint(fingerprint: str) -> str:
    return fingerprint[:-1] + ("1" if fingerprint.endswith("0") else "0")


# ---------------------------------------------------------------------------
# (a) a plan, (b) a draft that needs input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pac_compute_plans_a_buying_scenario_to_a_proven_optimum(test_server):
    async with _tool_user() as client:
        identity = await _served_identity(client)
        engine_timeout_ms = await _served_engine_timeout_ms(client, "plan")
        item = _item(identity, _buying_request())
        payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    assert result["status"] == "success", result
    assert (payload["success_count"], payload["failed_count"]) == (1, 0)
    assert {key: result[key] for key in IDENTITY_KEYS} == identity
    plan = result["result"]
    assert plan["result_state"] == "ready_incumbent"
    assert plan["proof"]["kind"] == "optimal_proven"
    (order,) = plan["primary_solution"]["order_rows"]
    assert order["cash_debit"]["currency"] == "EUR"
    assert Decimal(order["cash_debit"]["amount"]) == 50
    assert plan["catalogs"]["currencies"] == [{"currency": "EUR", "minor_unit": "0.01"}]
    # The served engine window is the budget the worker handed SCIP: every stage
    # publishes it as its `time_budget` setting.
    solver_time_budget_seconds = engine_timeout_ms / 1000
    stages = plan["solver_evidence"]["stages"]
    assert [setting["value"] for stage in stages for setting in stage["settings"] if setting["name"] == "time_budget"] == [f"{solver_time_budget_seconds:g}"] * len(stages)
    # The worker publishes exactly what the planner computes in process. That
    # budget is part of what it publishes, so the in-process call claims the same
    # window, as tool_plugins/pac_allocator.py does, instead of solver.py's
    # fallback for a caller with no window to claim.
    in_process = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(_buying_request()), solver_time_budget_seconds=solver_time_budget_seconds)
    assert plan == PAC_PLAN_OUTPUT_ADAPTER.dump_python(in_process, mode="json", by_alias=True)


@pytest.mark.asyncio
async def test_pac_compute_publishes_a_rounding_tie_with_its_top_up(test_server):
    """A plan that posts one cent over the cash reaches the caller, with the top-up that covers it (QX1-b).

    The Decimal replay stays authoritative: a deficit within the pool's rounded
    postings (here one, the BUY debit) no longer suppresses the plan, it travels
    as a ``ready_incumbent`` whose top-up says what to add. The rejection path
    (beyond the threshold, reported as ``execution_failed``) stays a service
    test: the worker runs in a spawned child, out of reach of any seam.
    """
    async with _tool_user() as client:
        identity = await _served_identity(client)
        engine_timeout_ms = await _served_engine_timeout_ms(client, "plan")
        item = _item(identity, _rounding_tie_request())
        payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    assert result["status"] == "success", result
    assert (payload["success_count"], payload["failed_count"]) == (1, 0)
    plan = result["result"]
    assert (plan["result_state"], plan["stop_reason"]) == ("ready_incumbent", "completed")
    (order,) = plan["primary_solution"]["order_rows"]
    assert (order["broker_id"], order["instruction"]["kind"], Decimal(order["instruction"]["quantity"])) == ("broker-one", "whole_quantity", 3)
    (top_up,) = plan["primary_solution"]["rounding_top_ups"]
    assert (top_up["broker_id"], top_up["currency"], top_up["rounded_postings"]) == ("broker-one", "EUR", 1)
    assert Decimal(top_up["amount"]) == Decimal("0.01")
    # The worker publishes what the planner computes in process, in the same engine window.
    in_process = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(_rounding_tie_request()), solver_time_budget_seconds=engine_timeout_ms / 1000)
    assert plan == PAC_PLAN_OUTPUT_ADAPTER.dump_python(in_process, mode="json", by_alias=True)


@pytest.mark.asyncio
async def test_pac_compute_answers_a_draft_without_a_price_with_needs_input(test_server):
    async with _tool_user() as client:
        identity = await _served_identity(client)
        item = _item(identity, _unpriced_request())
        payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    # A planning outcome is a successful computation, not a platform error.
    assert result["status"] == "success", result
    assert (payload["success_count"], payload["failed_count"]) == (1, 0)
    plan = result["result"]
    assert (plan["result_state"], plan["availability"]) == ("needs_input", "needs_input")
    assert "primary_solution" not in plan
    assert {(issue["code"], issue["kind"], issue["path"]["entity_id"], issue["path"]["field"]) for issue in plan["issues"]} == {
        ("allocation.price_missing", "missing", "asset-one", "quote.amount"),
        ("allocation.quote_base_quantity_missing", "missing", "asset-one", "quote.quote_base_quantity"),
        ("allocation.price_date_missing", "missing", "asset-one", "quote.reference_date"),
    }


# ---------------------------------------------------------------------------
# (c) a stale identity, item by item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pac_compute_refuses_a_stale_tool_identity_per_item(test_server):
    async with _tool_user() as client:
        identity = await _served_identity(client)
        stale = [
            _item(identity, _buying_request(), contract_version=_other_version(identity["contract_version"])),
            _item(identity, _buying_request(), implementation_version=_other_version(identity["implementation_version"])),
            _item(identity, _buying_request(), schema_fingerprint=_other_fingerprint(identity["schema_fingerprint"])),
        ]
        current = _item(identity, _buying_request())
        payload, results = await _compute(client, *stale, current)

    for item in stale:
        result = results[item["correlation_id"]]
        assert result["status"] == "error", result
        # Refused before any worker starts, echoing the identity the caller sent.
        assert result["execution_id"] is None
        assert result["error"] == {"code": "version_mismatch", "retryable": True, "issues": [], "issue_count": 0}
        assert {key: result[key] for key in IDENTITY_KEYS} == {key: item[key] for key in IDENTITY_KEYS}
    # The refusals are item-level: the current sibling in the same batch still runs.
    assert results[current["correlation_id"]]["status"] == "success"
    assert results[current["correlation_id"]]["result"]["result_state"] == "ready_incumbent"
    assert (payload["success_count"], payload["failed_count"]) == (1, 3)


# ---------------------------------------------------------------------------
# (d) the same parameters twice in one batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pac_compute_answers_repeated_parameters_once_per_correlation(test_server):
    async with _tool_user() as client:
        identity = await _served_identity(client)
        parameters = _buying_request()
        first, second = _item(identity, parameters), _item(identity, copy.deepcopy(parameters))
        assert first["correlation_id"] != second["correlation_id"]
        payload, results = await _compute(client, first, second)

    answers = [results[first["correlation_id"]], results[second["correlation_id"]]]
    assert [answer["status"] for answer in answers] == ["success", "success"]
    assert (payload["success_count"], payload["failed_count"]) == (2, 0)
    # deduplication="none": two executions, and a deterministic plan for both.
    assert answers[0]["execution_id"] != answers[1]["execution_id"]
    assert answers[0]["result"] == answers[1]["result"]
    assert answers[0]["result"]["result_state"] == "ready_incumbent"


# ---------------------------------------------------------------------------
# (e) inputs C0b withdrew from the wire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pac_compute_rejects_withdrawn_inputs_as_invalid_parameters(test_server):
    min_fragmentation = _buying_request()
    min_fragmentation["policy"] = "min_fragmentation"
    currency_specs = _buying_request()
    currency_specs["currency_specs"] = [{"currency": "EUR", "minor_unit": "0.01"}]

    async with _tool_user() as client:
        identity = await _served_identity(client)
        expected = {
            "policy": (_item(identity, min_fragmentation), {"code": "literal_error", "path": ["policy"]}),
            "currency_specs": (_item(identity, currency_specs), {"code": "extra_forbidden", "path": ["currency_specs"]}),
        }
        payload, results = await _compute(client, *(item for item, _issue in expected.values()))

    assert (payload["success_count"], payload["failed_count"]) == (0, 2)
    for field, (item, issue) in expected.items():
        result = results[item["correlation_id"]]
        assert result["status"] == "error", (field, result)
        assert "result" not in result
        assert result["error"] == {"code": "invalid_parameters", "retryable": False, "issues": [issue], "issue_count": 1}, field
