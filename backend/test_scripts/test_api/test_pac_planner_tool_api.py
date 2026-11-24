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
is written. The engine failure log tests at the end are pure: no user, no
server, no database.
"""

from __future__ import annotations

import ast
import copy
import json
import traceback
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.pac_allocator.preview import PAC_TOOL_INPUT_ADAPTER, PAC_TOOL_OUTPUT_ADAPTER, REBALANCER_TOOL_INPUT_ADAPTER, REBALANCER_TOOL_OUTPUT_ADAPTER
from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER, PAC_PLAN_OUTPUT_ADAPTER, REBALANCER_PLAN_INPUT_ADAPTER, REBALANCER_PLAN_OUTPUT_ADAPTER
from backend.app.services.accounts import user_service
from backend.app.services.pac_allocator.evaluation.errors import ExactReplayRejectedError
from backend.app.services.pac_allocator.planner import SeededRunsFailedError, plan_pac_allocation, plan_rebalancing
from backend.app.services.pac_allocator.preview import preview_pac_allocation, preview_rebalancing
from backend.app.services.pac_allocator.solver import SolverStageError
from backend.app.services.tool_plugins.pac_allocator.plugin import MESSAGE_SAFE_ERRORS, _log_engine_failure
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import TEST_SERVER_PLANNER_SEEDS, _TestingServerManager, without_time_limits
from backend.test_scripts.test_services import _reb_small_requests as reb

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
# The plan operation's client deadline is 65 s (tool_plugins/pac_allocator/plugin.py):
# the transport must outwait it, or a slow worker reads as a transport error.
COMPUTE_TIMEOUT = 70.0
PASSWORD = "PacToolApiPass123!"
SOLE_ADMIN_DELETE_DETAIL = {"error_code": "LAST_ADMIN", "message": "Cannot delete account: you are the last active administrator"}

TOOL_CODE = "pac_allocator"
IDENTITY_KEYS = ("tool_code", "contract_version", "implementation_version", "schema_fingerprint")
MIN_REQUEST_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "pac_plan_request.min.2-0-0.json"
# The same request as the UI sends it: every default omitted, no fee schedule (contract compaction).
COMPACT_REQUEST_FIXTURE = MIN_REQUEST_FIXTURE.with_name("pac_plan_request.compact.2-0-0.json")


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


async def _served_descriptor(client: httpx.AsyncClient, tool_code: str = TOOL_CODE) -> dict:
    response = await client.get(f"{API_BASE}/tools/catalog", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    descriptor = next((item for item in response.json()["items"] if item["tool_code"] == tool_code), None)
    assert descriptor is not None, f"{tool_code} is not served by the catalog"
    return descriptor


async def _served_identity(client: httpx.AsyncClient, tool_code: str = TOOL_CODE) -> dict[str, str]:
    descriptor = await _served_descriptor(client, tool_code)
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


def _compact_request() -> dict:
    return json.loads(COMPACT_REQUEST_FIXTURE.read_text(encoding="utf-8"))


def _buying_request(payload: dict | None = None) -> dict:
    """The min fixture (or ``payload``) with €50 against its €10 whole unit: five units to buy.

    Unmodified, the fixture holds €5, so doing nothing is the proven optimum.
    """
    payload = _min_request() if payload is None else payload
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
    """The min fixture at €33.335 a whole unit with €100.00 of cash: a rounding tie.

    The fixture already trades in EUR with a zero fee. Three units cost €100.005
    at the exact price, half a cent over the cash; rounded against the plan,
    their BUY debit is ceiled to €100.01, one cent more than broker-one/EUR
    holds. Two units cost exactly €66.67, which the cash covers.
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
    # window, as tool_plugins/pac_allocator/plugin.py does, instead of solver.py's
    # fallback for a caller with no window to claim.
    in_process = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(_buying_request()), solver_time_budget_seconds=solver_time_budget_seconds)
    assert plan == PAC_PLAN_OUTPUT_ADAPTER.dump_python(in_process, mode="json", by_alias=True)


@pytest.mark.asyncio
async def test_pac_compute_plans_a_rounding_tie_within_its_cash(test_server):
    """A rounding tie reaches the caller as a proven plan the cash covers: two units, no top-up.

    Every posting is rounded against the plan and the model encodes the same
    rule, so the third unit, whose ceiled debit is one cent over the cash, is
    not bought: a ``ready_incumbent`` / ``optimal_proven`` buying two units for
    exactly €66.67, with ``rounding_top_ups`` published and empty. A top-up
    (QX1-b) is now a safety net no natural plan reaches, so its publication is
    no longer observable over HTTP; the service suite reaches it through a seam
    (``test_rounding_top_up_*``), as it does the rejection path beyond the
    threshold (reported as ``execution_failed``): the worker runs in a spawned
    child, out of reach of any seam.
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
    assert plan["proof"]["kind"] == "optimal_proven"
    (order,) = plan["primary_solution"]["order_rows"]
    assert (order["broker_id"], order["instruction"]["kind"], Decimal(order["instruction"]["quantity"])) == ("broker-one", "whole_quantity", 2)
    assert (order["cash_debit"]["currency"], Decimal(order["cash_debit"]["amount"])) == ("EUR", Decimal("66.67"))
    assert plan["primary_solution"]["rounding_top_ups"] == []
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
# (e) inputs withdrawn from the wire (C0b, contract compaction)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pac_compute_rejects_withdrawn_inputs_as_invalid_parameters(test_server):
    """Every input the wire withdrew is refused at its exact path, never silently dropped.

    C0b withdrew ``policy=min_fragmentation`` and ``currency_specs``; contract
    compaction withdrew the quote's ``freshness`` and ``reference_date`` and the
    cash's ``source_kind``. Each case is the buying request plus the one stale
    input, sent back the way an old client would. The items need a worker to
    be refused, so they travel two per batch (module docstring).
    """
    min_fragmentation = _buying_request()
    min_fragmentation["policy"] = "min_fragmentation"
    currency_specs = _buying_request()
    currency_specs["currency_specs"] = [{"currency": "EUR", "minor_unit": "0.01"}]
    quote_freshness = _buying_request()
    quote_freshness["assets"][0]["quote"]["freshness"] = {"kind": "fresh"}
    quote_reference_date = _buying_request()
    quote_reference_date["assets"][0]["quote"]["reference_date"] = "2026-09-15"
    cash_source_kind = _buying_request()
    cash_source_kind["existing_cash"][0]["source_kind"] = "local_broker_cash"

    async with _tool_user() as client:
        identity = await _served_identity(client)
        cases = [
            ("policy", _item(identity, min_fragmentation), {"code": "literal_error", "path": ["policy"]}),
            ("currency_specs", _item(identity, currency_specs), {"code": "extra_forbidden", "path": ["currency_specs"]}),
            ("quote.freshness", _item(identity, quote_freshness), {"code": "extra_forbidden", "path": ["assets", 0, "quote", "freshness"]}),
            ("quote.reference_date", _item(identity, quote_reference_date), {"code": "extra_forbidden", "path": ["assets", 0, "quote", "reference_date"]}),
            ("existing_cash.source_kind", _item(identity, cash_source_kind), {"code": "extra_forbidden", "path": ["existing_cash", 0, "source_kind"]}),
        ]
        batches = []
        for start in range(0, len(cases), 2):
            batch = cases[start : start + 2]
            payload, results = await _compute(client, *(item for _field, item, _issue in batch))
            batches.append((batch, payload, results))

    assert sum(len(batch) for batch, _payload, _results in batches) == 5
    for batch, payload, results in batches:
        assert (payload["success_count"], payload["failed_count"]) == (0, len(batch))
        for field, item, issue in batch:
            result = results[item["correlation_id"]]
            assert result["status"] == "error", (field, result)
            assert "result" not in result
            assert result["error"] == {"code": "invalid_parameters", "retryable": False, "issues": [issue], "issue_count": 1}, field


# ---------------------------------------------------------------------------
# (f) the compact wire: a request without its defaults plans the same
# ---------------------------------------------------------------------------


def _economic_projection(plan: dict) -> dict:
    """What the user acts on: each order (by route) with its debit and fee, and the objectives."""
    solution = plan["primary_solution"]
    orders = {row["route_id"]: (row["kind"], row["asset_id"], row["broker_id"], row["instruction"], row["cash_debit"], row["fee"]) for row in solution["order_rows"]}
    assert len(orders) == len(solution["order_rows"]), solution["order_rows"]
    return {"orders": orders, "costs": solution["costs"], "objectives": solution["objectives"]}


def _batch_outcomes(payload: dict, results: dict[str, dict], **items: dict) -> str:
    """Why a batch's counts are off: each item's ``(status, error)`` by name, details of any item that did not succeed, and the batch metrics.

    Never a plan, which would bury the cause. The details are the item's
    ``execution_id`` (None if it never reached a worker, otherwise the id the
    worker logs with a ``PAC planner engine failure``) and its metrics, whose
    timings and observed memory peak tell a worker that never became ready from
    one that crashed or ran out of time later. The batch metrics carry
    ``server_processing_ms``. Read with ``.get`` only, so a missing item or key
    prints as None instead of raising inside the message.
    """
    found = {name: results.get(item.get("correlation_id")) or {} for name, item in items.items()}
    outcomes = {name: (result.get("status"), result.get("error")) for name, result in found.items()}
    unsuccessful = {name: {"execution_id": result.get("execution_id"), "metrics": result.get("metrics")} for name, result in found.items() if result.get("status") != "success"}
    return f"(status, error) by item: {outcomes}; items that did not succeed: {unsuccessful}; batch metrics: {payload.get('metrics')}"


@pytest.mark.asyncio
async def test_pac_compute_plans_the_compact_twin_like_the_explicit_request(test_server):
    """The compact twin (no defaults, no fee schedule) and ``min`` written in full buy the same thing.

    Both carry the same €50 of cash, so the reference really trades. The two
    results are not compared whole: the twin's implicit zero fee schedule has
    its own ID, so its ``request_fingerprint`` may differ by design.
    """
    async with _tool_user() as client:
        identity = await _served_identity(client)
        explicit = _item(identity, _buying_request())
        compact = _item(identity, _buying_request(_compact_request()))
        payload, results = await _compute(client, explicit, compact)

    assert (payload["success_count"], payload["failed_count"]) == (2, 0), _batch_outcomes(payload, results, explicit=explicit, compact=compact)
    plans = {}
    for name, item in (("explicit", explicit), ("compact", compact)):
        result = results[item["correlation_id"]]
        assert result["status"] == "success", (name, result)
        plan = result["result"]
        assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), name
        assert plan["primary_solution"]["order_rows"], f"positive control: the {name} request must buy something"
        plans[name] = plan
    assert _economic_projection(plans["compact"]) == _economic_projection(plans["explicit"])


# ---------------------------------------------------------------------------
# Engine failure log: the calling frames, never the values
# ---------------------------------------------------------------------------
#
# The worker writes this line, and the worker is a spawned child that no seam
# can reach, so these tests call _log_engine_failure directly: pure, no user,
# no server. Each one raises through module-level functions and catches the
# exception in its own body, so the traceback starts at the test function. This
# file lives under backend/, so its functions are LibreFolio's own frames; the
# "library" is compiled under a file name outside the repository, and no file
# has to exist there.
#
# capture_logs swaps structlog's processors for a LogCapture inside the
# configured list, so the module's logger reaches it whether or not
# configure_logging ran first in this process (test_post_migration.py, section
# 13, explains why). The barrier in _logged_engine_failure says so if that ever
# changes.

ENGINE_FAILURE_EVENT = "PAC planner engine failure"
ENGINE_FAILURE_LOGGER = "backend.app.services.tool_plugins.pac_allocator.plugin"
# Not keyword arguments of the log call: the event name, and what the capture adds.
CAPTURE_KEYS = frozenset({"event", "log_level", "logger"})
OWN_FILE = "backend/test_scripts/test_api/test_pac_planner_tool_api.py"
FAKE_LIBRARY_PATH = "/tmp/libreFolio_fake_library.py"
FAKE_LIBRARY_SOURCE = "def boom():\n    raise ValueError('library failure')\n"
# Line 2 of FAKE_LIBRARY_SOURCE raises; a library frame is shown by its file name only.
LIBRARY_FRAME = "libreFolio_fake_library.py:2:boom"
# Out of every source line a frame points at: a figure found in the log can only be a value.
MESSAGE_FIGURE = "4242.42"
LOCAL_FIGURE = "98765.43"


# ---------------------------------------------------------------------------
# B3 (project 67): the Rebalancer, the plugin's second service
# ---------------------------------------------------------------------------

REBALANCER_TOOL_CODE = "portfolio_rebalancer"


@pytest.mark.asyncio
async def test_rebalancer_compute_plans_to_a_proven_optimum(test_server):
    """B3 test 13: T4 through ``POST /tools/compute`` buys 195 of B, proven optimal, exactly as the planner in process."""
    async with _tool_user() as client:
        identity = await _served_identity(client, REBALANCER_TOOL_CODE)
        engine_timeout_ms = (await _served_descriptor(client, REBALANCER_TOOL_CODE))["operations"][0]["engine_timeout_ms"]
        item = _item(identity, reb.t4())
        payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    assert result["status"] == "success", result
    assert {key: result[key] for key in IDENTITY_KEYS} == identity
    plan = result["result"]
    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven")
    (order,) = plan["primary_solution"]["order_rows"]
    assert (order["asset_id"], order["instruction"]["amount"]) == ("asset-b", {"amount": "195", "currency": "EUR"})
    in_process = plan_rebalancing(REBALANCER_PLAN_INPUT_ADAPTER.validate_python(reb.t4()), solver_time_budget_seconds=engine_timeout_ms / 1000, seeds=TEST_SERVER_PLANNER_SEEDS)
    # Compared without the time limits: on a machine with fewer usable CPUs than runs, a later run has the time left.
    assert without_time_limits(plan) == without_time_limits(REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(in_process, mode="json", by_alias=True))


@pytest.mark.asyncio
@pytest.mark.parametrize("two_cells", [pytest.param(False, id="one-cell"), pytest.param(True, id="two-cells")])
async def test_rebalancer_compute_publishes_a_wide_plan_with_its_top_up(test_server, two_cells):
    """Lot ZB-b of project 67: the consultant's case Y through ``POST /tools/compute``. The plan of the wide model needs a
    top-up of 0.01 EUR and, with one cash cell, leaves no cash: it is published, not proven, with its top-up, exactly as the
    planner in process."""
    async with _tool_user() as client:
        identity = await _served_identity(client, REBALANCER_TOOL_CODE)
        engine_timeout_ms = (await _served_descriptor(client, REBALANCER_TOOL_CODE))["operations"][0]["engine_timeout_ms"]
        item = _item(identity, reb.y_top_up(two_cells=two_cells))
        payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    assert result["status"] == "success", result
    plan = result["result"]
    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "not_proven")
    assert [(row["broker_id"], row["amount"]) for row in plan["primary_solution"]["rounding_top_ups"]] == [(reb.BROKER, "0.01")]
    in_process = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(plan_rebalancing(REBALANCER_PLAN_INPUT_ADAPTER.validate_python(reb.y_top_up(two_cells=two_cells)), solver_time_budget_seconds=engine_timeout_ms / 1000, seeds=TEST_SERVER_PLANNER_SEEDS), mode="json", by_alias=True)
    # The wide model is solved with the time the prudent one left, a wall-clock figure each stage publishes among its
    # settings (``time_budget``). That one value is the run's; everything else, the bounds included, is compared as it is.
    assert without_time_limits(plan) == without_time_limits(in_process)


@pytest.mark.asyncio
async def test_rebalancer_compute_answers_missing_holdings_with_needs_input(test_server):
    """B3 test 14: a Rebalancer request with no holdings is a planning outcome, ``needs_input`` with its code."""
    payload_without_holdings = reb.t4()
    payload_without_holdings["holdings"] = []
    async with _tool_user() as client:
        identity = await _served_identity(client, REBALANCER_TOOL_CODE)
        item = _item(identity, payload_without_holdings)
        _payload, results = await _compute(client, item)

    result = results[item["correlation_id"]]
    assert result["status"] == "success", result
    plan = result["result"]
    assert (plan["result_state"], plan["availability"]) == ("needs_input", "needs_input")
    assert "portfolio_rebalancer.holdings_missing" in {issue["code"] for issue in plan["issues"]}


@pytest.mark.asyncio
async def test_rebalancer_and_pac_items_share_one_batch(test_server):
    """B3 test 15: one batch, a Rebalancer item and a PAC item (two, the platform's two lanes): two successes."""
    async with _tool_user() as client:
        rebalancer = _item(await _served_identity(client, REBALANCER_TOOL_CODE), reb.t5())
        pac = _item(await _served_identity(client), _buying_request())
        payload, results = await _compute(client, rebalancer, pac)

    assert (payload["success_count"], payload["failed_count"]) == (2, 0)
    assert results[rebalancer["correlation_id"]]["result"]["result_state"] == "ready_no_op"
    assert results[pac["correlation_id"]]["result"]["result_state"] == "ready_incumbent"


async def _stream(client: httpx.AsyncClient, *items: dict) -> list[dict]:
    """One batch through ``POST /tools/compute/stream``, through the server's whole middleware stack; its lines."""
    envelope = {"request_id": f"pac-request-{uuid4().hex}", "items": list(items)}
    async with client.stream("POST", f"{API_BASE}/tools/compute/stream", json=envelope, headers={"Accept-Encoding": "gzip"}, timeout=COMPUTE_TIMEOUT) as response:
        body = b"".join([chunk async for chunk in response.aiter_bytes()])
    assert response.status_code == 200, body
    assert "content-encoding" not in response.headers
    return [json.loads(line) for line in body.decode("utf-8").split("\n") if line]


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool_code", "parameters", "searches"), [pytest.param(TOOL_CODE, _buying_request, 5, id="pac"), pytest.param(REBALANCER_TOOL_CODE, reb.t4, 3, id="rebalancer-t4")])
async def test_compute_forwards_progress_to_the_context(test_server, tool_code, parameters, searches):
    """V2 test 8 (project 67): the plugin hands ``report_progress`` to the engine, and a served plan streams its phases in
    order — validate, model, search «n of m», verify, report — then the result of ``/compute`` for the same request.

    On a server with fewer usable CPUs than the Rebalancer's searches, «n of m» counts every turn's stages (TURNI 4d): the
    turns are read off the served plan's window, 30 s per turn and 5 s of grace between turns, never guessed from the
    machine that runs the test. The PAC runs one turn."""
    async with _tool_user() as client:
        descriptor = await _served_descriptor(client, tool_code)
        plan_policy = next(policy for policy in descriptor["operations"] if policy["operation"] == "plan")
        identity = {key: descriptor[key] for key in IDENTITY_KEYS}
        item = _item(identity, parameters())
        lines = await _stream(client, item)
        _payload, computed = await _compute(client, _item(identity, parameters()))

    assert plan_policy["progress_phases"] == ["validate", "model", "search", "verify", "report"]
    *progress, last = lines
    assert {line["correlation_id"] for line in progress} == {item["correlation_id"]}
    turns = (plan_policy["engine_timeout_ms"] + 5_000) // 35_000
    whole = searches * turns
    expected = [("validate", None, None), ("model", None, None), *(("search", step, whole) for step in range(1, whole + 1)), ("verify", None, None), ("report", None, None)]
    assert [(line["phase"], line["step"], line["total"]) for line in progress] == expected
    assert last["kind"] == "result"
    (streamed,) = last["response"]["results"]
    (planned,) = computed.values()
    assert streamed["status"] == planned["status"] == "success", streamed
    assert streamed["result"] == planned["result"]


@pytest.mark.asyncio
async def test_rebalancer_compute_rejects_a_pac_request_and_invest_and_sell(test_server):
    """B3 tests 16 and 19 (service half): parameters of the wrong kind, and «Invest and sell» before C1, are refused as
    ``invalid_parameters`` with their path, never ``execution_failed``, never a plan."""
    invest_and_sell = reb.t4()
    invest_and_sell["policy"] = "invest_and_sell"
    async with _tool_user() as client:
        identity = await _served_identity(client, REBALANCER_TOOL_CODE)
        pac_shaped = _item(identity, _buying_request())
        selling = _item(identity, invest_and_sell)
        payload, results = await _compute(client, pac_shaped, selling)

    assert (payload["success_count"], payload["failed_count"]) == (0, 2)
    for item in (pac_shaped, selling):
        result = results[item["correlation_id"]]
        assert result["status"] == "error" and "result" not in result, result
        assert result["error"]["code"] == "invalid_parameters"
    assert {"code": "literal_error", "path": ["policy"]} in results[selling["correlation_id"]]["error"]["issues"]


@pytest.mark.asyncio
async def test_preview_over_http(test_server):
    """B4 test 14 (contract §11): ``operation="preview"`` through ``POST /tools/compute`` gives, for each service, exactly the
    numbers the preview computes in process: the PAC's total, the Rebalancer's F, items and the λ of its fidelity levels."""
    pac_payload = {**_buying_request(), "operation": "preview"}
    rebalancer_payload = {**reb.t4(), "operation": "preview"}
    async with _tool_user() as client:
        pac = _item(await _served_identity(client), pac_payload)
        rebalancer = _item(await _served_identity(client, REBALANCER_TOOL_CODE), rebalancer_payload)
        payload, results = await _compute(client, pac, rebalancer)

    assert (payload["success_count"], payload["failed_count"]) == (2, 0)
    pac_in_process = preview_pac_allocation(PAC_TOOL_INPUT_ADAPTER.validate_python(pac_payload))
    rebalancer_in_process = preview_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(rebalancer_payload))
    assert results[pac["correlation_id"]]["result"] == PAC_TOOL_OUTPUT_ADAPTER.dump_python(pac_in_process, mode="json", by_alias=True)
    assert results[rebalancer["correlation_id"]]["result"] == REBALANCER_TOOL_OUTPUT_ADAPTER.dump_python(rebalancer_in_process, mode="json", by_alias=True)
    assert results[rebalancer["correlation_id"]]["result"]["result_state"] == "preview_ready"
    assert results[rebalancer["correlation_id"]]["result"]["total"] == {"value": {"kind": "finite_decimal", "value": "10000"}, "currency": "EUR"}


def _compile_library_boom() -> Callable[[], None]:
    """``boom``, compiled under ``FAKE_LIBRARY_PATH``: its frame lies outside the repository, as a library's does."""
    namespace: dict[str, Any] = {}
    exec(compile(FAKE_LIBRARY_SOURCE, FAKE_LIBRARY_PATH, "exec"), namespace)
    return namespace["boom"]


_library_boom = _compile_library_boom()


def _frame_a() -> None:
    _frame_b()


def _frame_b() -> None:
    _frame_c()


def _frame_c() -> None:
    _frame_d()


def _frame_d() -> None:
    raise ValueError("raised in own code")


def _frame_x() -> None:
    _frame_y()


def _frame_y() -> None:
    _library_boom()


def _frame_holding_an_amount() -> None:
    amount = Decimal(LOCAL_FIGURE)
    _frame_refusing_the_amount(amount)


def _frame_refusing_the_amount(amount: Decimal) -> None:
    if amount > 0:
        raise ValueError(f"PRIVATE-{MESSAGE_FIGURE}: a positive amount is refused")


def _logged_engine_failure(exc: Exception, execution_id: str) -> dict[str, Any]:
    """The one event ``_log_engine_failure`` writes for ``exc``, from the module's logger at level ``error``; barrier first."""
    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        _log_engine_failure(exc, execution_id=execution_id)
    events = [entry for entry in logs if entry.get("event") == ENGINE_FAILURE_EVENT]
    assert events, f"barrier: capture_logs saw no {ENGINE_FAILURE_EVENT!r} among {[entry.get('event') for entry in logs]}: the module's logger does not reach the capture"
    assert [(entry.get("logger"), entry.get("log_level")) for entry in events] == [(ENGINE_FAILURE_LOGGER, "error")], events
    return events[0]


def _frame_parts(text: object) -> tuple[str, str, str]:
    """``(path, line, function)`` of a logged frame ``<path>:<line>:<function>``, whose line is a number."""
    assert isinstance(text, str), f"a logged frame is a str '<path>:<line>:<function>'; got {text!r}"
    parts = text.rsplit(":", 2)
    assert len(parts) == 3 and parts[1].isdigit(), f"a logged frame reads '<path>:<line>:<function>'; got {text!r}"
    path, line, function = parts
    return path, line, function


def _own_function(text: object) -> str:
    """The function an own frame names, once its path is shown from the repository root."""
    path, _line, function = _frame_parts(text)
    assert path == OWN_FILE, f"an own frame shows its repository-relative path {OWN_FILE!r}; got {text!r}"
    return function


def _callers(event: dict[str, Any]) -> list[str]:
    """``event['callers']``: the own frames that called ``where``, at most two, nearest first, each a str like ``where``."""
    callers = event.get("callers", "<missing>")
    assert isinstance(callers, list), f"the event must carry 'callers', a list[str] of the own frames above 'where' (at most two, nearest first); got {callers!r} in {event}"
    assert all(isinstance(text, str) for text in callers), f"'callers' holds frames as str '<path>:<line>:<function>'; got {callers!r}"
    return callers


def test_pac_engine_failure_log_names_at_most_two_callers_nearest_first():
    """``callers`` names the two own frames nearest above ``where``, nearest first, and no more.

    This test -> ``_frame_a`` -> ``_frame_b`` -> ``_frame_c`` -> ``_frame_d``,
    which raises in own code: ``where`` is ``_frame_d``, there is no
    ``raised_in``, and the cap of two leaves ``_frame_a`` and this test out.
    """
    try:
        _frame_a()
    except ValueError as exc:
        caught = exc
    else:
        pytest.fail("setup: _frame_a() must raise from _frame_d()")

    event = _logged_engine_failure(caught, execution_id="pac-log-own-chain")

    assert (event.get("error_type"), event.get("execution_id")) == (ValueError.__qualname__, "pac-log-own-chain")
    assert _own_function(event.get("where")) == _frame_d.__name__
    assert "raised_in" not in event, f"raised in own code, so no library frame: {event}"
    assert set(event) - CAPTURE_KEYS == {"error_type", "execution_id", "where", "callers"}, f"the keys of the log call: {sorted(set(event) - CAPTURE_KEYS)}"
    callers = _callers(event)
    assert [_own_function(text) for text in callers] == [_frame_c.__name__, _frame_b.__name__], callers


def test_pac_engine_failure_log_names_a_lone_caller_alone():
    """One own frame above ``where`` makes ``callers`` a list of that frame alone.

    This test -> ``_frame_d``, which raises in own code: "at most two" also
    means one, with no error for the missing second.
    """
    try:
        _frame_d()
    except ValueError as exc:
        caught = exc
    else:
        pytest.fail("setup: _frame_d() must raise")

    event = _logged_engine_failure(caught, execution_id="pac-log-lone-caller")

    assert (event.get("error_type"), event.get("execution_id")) == (ValueError.__qualname__, "pac-log-lone-caller")
    assert _own_function(event.get("where")) == _frame_d.__name__
    assert "raised_in" not in event, f"raised in own code, so no library frame: {event}"
    callers = _callers(event)
    assert [_own_function(text) for text in callers] == [test_pac_engine_failure_log_names_a_lone_caller_alone.__name__], callers


def test_pac_engine_failure_log_has_no_callers_key_without_an_own_caller():
    """No own frame above ``where``: the event has no ``callers`` key, not an empty list.

    This test calls the fake library directly: ``where`` is this test and
    ``raised_in`` the library frame, shown by its file name only.
    """
    try:
        _library_boom()
    except ValueError as exc:
        caught = exc
    else:
        pytest.fail("setup: the fake library must raise")

    event = _logged_engine_failure(caught, execution_id="pac-log-no-caller")

    assert (event.get("error_type"), event.get("execution_id")) == (ValueError.__qualname__, "pac-log-no-caller")
    assert _own_function(event.get("where")) == test_pac_engine_failure_log_has_no_callers_key_without_an_own_caller.__name__
    assert event.get("raised_in") == LIBRARY_FRAME, event
    assert "callers" not in event, f"no own frame above 'where': 'callers' must be absent, not {event.get('callers')!r}"
    assert set(event) - CAPTURE_KEYS == {"error_type", "execution_id", "where", "raised_in"}


def test_pac_engine_failure_log_names_the_callers_of_a_library_failure():
    """A library failure: ``raised_in`` is the library frame, ``where`` the own frame that called it, ``callers`` the two above.

    This test -> ``_frame_x`` -> ``_frame_y`` -> the fake library, which
    raises: the library frame shows its file name only, and the callers are
    ``_frame_x`` and this test, nearest first.
    """
    try:
        _frame_x()
    except ValueError as exc:
        caught = exc
    else:
        pytest.fail("setup: _frame_x() must raise through the fake library")

    event = _logged_engine_failure(caught, execution_id="pac-log-library-chain")

    assert (event.get("error_type"), event.get("execution_id")) == (ValueError.__qualname__, "pac-log-library-chain")
    assert event.get("raised_in") == LIBRARY_FRAME, event
    assert _own_function(event.get("where")) == _frame_y.__name__
    callers = _callers(event)
    assert [_own_function(text) for text in callers] == [_frame_x.__name__, test_pac_engine_failure_log_names_the_callers_of_a_library_failure.__name__], callers
    assert set(event) - CAPTURE_KEYS == {"error_type", "execution_id", "where", "raised_in", "callers"}


def test_pac_engine_failure_log_never_shows_the_message_or_the_amounts():
    """The event carries neither the exception message nor an argument or a local: they can hold the user's amounts.

    This test -> ``_frame_holding_an_amount`` -> ``_frame_refusing_the_amount``,
    which raises with a figure in its message while a Decimal amount is a local
    of one frame and an argument of the other. Barriers first: both figures are
    really there to leak, and the event describes those frames.
    """
    try:
        _frame_holding_an_amount()
    except ValueError as exc:
        caught = exc
    else:
        pytest.fail("setup: _frame_holding_an_amount() must raise")

    assert MESSAGE_FIGURE in str(caught), f"setup: the exception message must carry the figure; got {str(caught)!r}"
    amounts = [frame.f_locals["amount"] for frame, _lineno in traceback.walk_tb(caught.__traceback__) if "amount" in frame.f_locals]
    assert Decimal(LOCAL_FIGURE) in amounts, f"setup: the traceback's frames must hold the amount; got {amounts!r}"

    event = _logged_engine_failure(caught, execution_id="pac-log-private")

    assert _own_function(event.get("where")) == _frame_refusing_the_amount.__name__, event
    logged = repr(event)
    assert MESSAGE_FIGURE not in logged, f"the exception message reached the log: {logged}"
    assert LOCAL_FIGURE not in logged, f"a local variable or an argument reached the log: {logged}"


# ---------------------------------------------------------------------------
# The reason: the message of a closed list of classes (R1-B of project 67)
# ---------------------------------------------------------------------------
#
# The developer's rule of 20/11/2026: the log carries the message of an engine failure only for a closed list of classes,
# matched by exact type, each one in the list once every place that raises it has been read. The scan below makes that
# reading durable: it finds every construction of a listed class in backend/app, pins how many there are, and admits as
# arguments only fixed text and the named interpolations (identifiers, closed codes). A new raise site, or one that
# interpolates anything else (an amount, a name), is red until it is read and added here.

# Each listed class, its number of constructions in backend/app, and the interpolations they may carry.
READ_RAISE_SITES: dict[str, tuple[int, frozenset[str]]] = {
    # evaluation/evaluator.py: a Broker's id and a currency code (``PlannerId``, ``^[A-Za-z0-9][A-Za-z0-9._:@/-]*$``,
    # built by the page from the database's ids), and the replay's conflict codes (``ExactConstraintCode``, a Literal).
    "ExactReplayRejectedError": (8, frozenset({"entry.broker_id", "entry.currency", "ledger.broker_id", "ledger.currency", "', '.join(evaluation.conflict_codes)"})),
    # solver.py: the stage's code (``objectives.py``: fixed words, or ``tie:`` and a decision id).
    "SolverStageError": (1, frozenset({"stage.code"})),
    # planner.py: the verdict of the seeded runs (``SeededVerdict.state``, a Literal).
    "SeededRunsFailedError": (1, frozenset({"verdict.state"})),
}
APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def _constructions(name: str) -> list[tuple[str, ast.Call]]:
    """Every call ``name(...)`` or ``module.name(...)`` in backend/app, with its ``file:line``."""
    found = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if isinstance(node, ast.Call) and _called_name(node.func) == name:
                found.append((f"{path.relative_to(APP_ROOT)}:{node.lineno}", node))
    return found


def _called_name(func: ast.expr) -> str | None:
    """The name a call reaches: ``name`` for ``name(...)`` and for ``module.name(...)``."""
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def _interpolations(argument: ast.expr) -> list[str] | None:
    """The interpolated expressions of a str literal or an f-string; ``None`` for anything else."""
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return []
    if isinstance(argument, ast.JoinedStr):
        return [ast.unparse(part.value) for part in argument.values if isinstance(part, ast.FormattedValue)]
    return None


def test_pac_engine_failure_log_lists_exactly_the_read_classes():
    """The closed list is the classes whose raise sites were read, no more: a class enters with its line above."""
    assert sorted(error.__name__ for error in MESSAGE_SAFE_ERRORS) == sorted(READ_RAISE_SITES)
    assert {ExactReplayRejectedError, SolverStageError, SeededRunsFailedError} == set(MESSAGE_SAFE_ERRORS)


@pytest.mark.parametrize("name", sorted(READ_RAISE_SITES))
def test_every_raise_of_a_listed_class_carries_no_amount(name: str):
    """Each construction of a listed class: one argument, fixed text with only the interpolations read for it."""
    count, allowed = READ_RAISE_SITES[name]
    sites = _constructions(name)
    assert len(sites) == count, f"{name} is constructed {len(sites)} times, read {count}: read the new site, then update READ_RAISE_SITES: {[where for where, _ in sites]}"
    for where, call in sites:
        assert len(call.args) == 1 and not call.keywords, f"{where}: {name} takes one message argument; got {ast.unparse(call)}"
        parts = _interpolations(call.args[0])
        assert parts is not None, f"{where}: the message of {name} must be a literal or an f-string; got {ast.unparse(call.args[0])}"
        assert set(parts) <= allowed, f"{where}: {name} interpolates {sorted(set(parts) - allowed)}, not read as free of amounts"


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ExactReplayRejectedError("the exact replay left broker:1/EUR short beyond its rounded postings"), id="replay-rejected"),
        pytest.param(SolverStageError("SCIP failed inside stage 'fixed_l2' before holding any plan"), id="stage-error"),
        pytest.param(SeededRunsFailedError("no run of the Rebalancer could be published (failed)"), id="seeded-runs"),
    ],
)
def test_pac_engine_failure_log_gives_the_reason_of_a_listed_class(error: Exception):
    """A listed class adds ``reason``, its message, to the line; the rest of the line is unchanged."""
    try:
        raise error
    except type(error) as exc:
        caught = exc

    event = _logged_engine_failure(caught, execution_id="pac-log-reason")

    assert (event.get("error_type"), event.get("reason")) == (type(error).__qualname__, str(error)), event
    # ``callers`` is there only when an own frame called ``where``: raised in this test's body, none did.
    assert set(event) - CAPTURE_KEYS == {"error_type", "execution_id", "where", "reason"}, sorted(event)


def test_pac_engine_failure_log_keeps_the_message_of_a_subclass_out():
    """The list matches the exact class: a subclass of a listed class was never read, so its message stays out."""

    class UnreadRejection(ExactReplayRejectedError):
        pass

    try:
        raise UnreadRejection(f"PRIVATE-{MESSAGE_FIGURE}: an unread message")
    except UnreadRejection as exc:
        caught = exc

    event = _logged_engine_failure(caught, execution_id="pac-log-subclass")

    assert "reason" not in event, event
    assert MESSAGE_FIGURE not in repr(event), event
