"""A Tool's settings through the real executor and the real spawn worker (CP12, X5-4b).

The contract of the cure, end to end: the PARENT resolves the values and hands them over with the job, the child binds them on
the plugin right after creating it, and the plugin reads them inside ``compute`` (``self.settings.get(...)``). Pinned here with
real ``multiprocessing`` spawn children, because what must hold is the pickled hand-over itself:

1. the plugin sees the value the parent delivered (a personal choice, an instance value); with none it sees the declared
   default, which is what the Tool did before the field existed;
2. the values follow the item: the items of one batch get the values of their own tool code (the two services of a bundle
   included), and two callers computing at the same time never see each other's;
3. a Tool whose required field has no value is refused before any worker starts (``service_unavailable``, not retryable, no
   execution id) while the other items of the batch run normally;
4. a Tool that declares no field is called with nothing bound.

Why this file is its own exclusive unit (``services tool-settings-lifecycle``) and not a part of ``tools-registry``: every test
starts real spawn workers, which own native POSIX process sessions, and the executor's pool is process-wide state, the same
reason ``tools-lifecycle`` is exclusive. The checks that need no process (the declaration, the registry, the in-process worker,
the refusal of a batch of unconfigured Tools) are in ``test_tool_settings_contract.py``, which is pure.

No database and no server: the values are built by ``build_bound_settings`` from the rows the database would hold, and the
registry is ``_tool_settings_fixtures.SettingsToolRegistry``, which the child re-creates by importing that module.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio

from backend.app.schemas.tools import ToolComputeBatchRequest, ToolPlatformPolicy
from backend.app.services.plugin_settings.fields import env_name, env_variables
from backend.app.services.plugin_settings.resolver import build_bound_settings
from backend.app.services.tools import executor as executor_module
from backend.app.services.tools.executor import ToolExecutor
from backend.test_scripts.test_services import _tool_settings_fixtures as fx

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Tool workers need POSIX process sessions")
_WAIT = 60.0


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch):
    """No ambient variable of the fixture Tools (the child inherits the environment)."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    for code in (fx.ROUNDING_CODE, fx.PAIR_A_CODE, fx.PAIR_B_CODE, fx.REQUIRED_CODE):
        for declared in (*fx.ROUNDING_FIELDS, fx.REGION):
            for name in {*env_variables("tool", code, declared), env_name("tool", code, declared.key)}:
                monkeypatch.delenv(name, raising=False)


@pytest.fixture
def started_workers(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The tool code of every physical job the executor starts, recorded around the real owner."""
    real = executor_module._run_owned_job
    started: list[str] = []

    def spy(job, *args, **kwargs):
        started.append(job.spec.tool_code)
        return real(job, *args, **kwargs)

    monkeypatch.setattr(executor_module, "_run_owned_job", spy)
    return started


@pytest_asyncio.fixture
async def executor() -> AsyncIterator[ToolExecutor]:
    value = ToolExecutor(ToolPlatformPolicy(), fx.SettingsToolRegistry)
    try:
        yield value
    finally:
        await value.shutdown()


async def _until(predicate: Callable[[], bool], description: str) -> None:
    """Poll a stated condition with a deadline."""
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"Condition did not become true: {description}")


def _round_item(code: str, correlation: str, halves: int = 5):
    return fx.item_for(fx.SettingsToolRegistry, code, {"operation": "round", "halves": halves}, correlation)


async def _compute(executor: ToolExecutor, items: list, *, principal: str = "p1", **kwargs) -> dict:
    """The results of one batch by correlation id; the executor's credit must come back."""
    response = await asyncio.wait_for(executor.compute(ToolComputeBatchRequest(request_id=f"r-{principal}", items=items), principal_key=principal, **kwargs), timeout=_WAIT)
    await _until(lambda: executor.snapshot().pending == 0, "the credits of the batch returned")
    return {result.correlation_id: result for result in response.results}


def _seen(result) -> dict:
    assert result.status == "success", getattr(result, "error", result)
    return result.result


@pytest.mark.asyncio
async def test_the_plugin_in_the_worker_sees_the_values_the_parent_delivered(executor: ToolExecutor):
    """Half of 5 is a tie: her rule gives 3 (the default would give 2); the instance's integer arrives too."""
    bound = fx.bound_rounding(rounding="half_up", max_points=700)

    results = await _compute(executor, [_round_item(fx.ROUNDING_CODE, "mine")], settings={fx.ROUNDING_CODE: bound})

    assert _seen(results["mine"]) == {"tool_code": fx.ROUNDING_CODE, "rounded": 3, "rounding": "half_up", "max_points": 700}


@pytest.mark.asyncio
@pytest.mark.parametrize("settings", [pytest.param(None, id="none"), pytest.param({}, id="empty"), pytest.param("omitted", id="omitted"), pytest.param("another-tool", id="only-another-tool")])
async def test_with_no_values_the_plugin_sees_the_defaults(executor: ToolExecutor, settings: object):
    """The behaviour before the field: the tie goes to the even neighbour, the integer is its default."""
    kwargs: dict = {}
    if settings == "another-tool":
        kwargs["settings"] = {fx.PAIR_A_CODE: fx.bound_rounding(fx.PAIR_A_CODE, rounding="half_up")}
    elif settings != "omitted":
        kwargs["settings"] = settings

    results = await _compute(executor, [_round_item(fx.ROUNDING_CODE, "old")], **kwargs)

    assert _seen(results["old"]) == {"tool_code": fx.ROUNDING_CODE, "rounded": 2, "rounding": "half_even", "max_points": 500}


@pytest.mark.asyncio
async def test_the_items_of_one_batch_get_the_values_of_their_own_tool_code(executor: ToolExecutor):
    """One plugin, two services, and a third Tool: the mapping is by tool code. ``settings_pair_a`` has her choice,
    ``settings_pair_b`` of the same class has none, and two items of one tool code share the value of that code."""
    settings = {fx.PAIR_A_CODE: fx.bound_rounding(fx.PAIR_A_CODE, rounding="half_up", max_points=900), fx.ROUNDING_CODE: fx.bound_rounding(rounding="half_up")}
    items = [_round_item(fx.PAIR_A_CODE, "a"), _round_item(fx.PAIR_B_CODE, "b"), _round_item(fx.ROUNDING_CODE, "r1", halves=5), _round_item(fx.ROUNDING_CODE, "r2", halves=9)]

    results = await _compute(executor, items, settings=settings)

    assert {key: (value["tool_code"], value["rounded"], value["rounding"], value["max_points"]) for key, value in ((c, _seen(r)) for c, r in results.items())} == {
        "a": (fx.PAIR_A_CODE, 3, "half_up", 900),
        "b": (fx.PAIR_B_CODE, 2, "half_even", 500),
        "r1": (fx.ROUNDING_CODE, 3, "half_up", 500),
        "r2": (fx.ROUNDING_CODE, 5, "half_up", 500),
    }


@pytest.mark.asyncio
async def test_two_callers_computing_together_never_see_each_others_values(executor: ToolExecutor):
    """The same Tool, the same parameters, two principals at the same time: each result carries its caller's rule."""
    alice = fx.bound_rounding(rounding="half_up", max_points=111, user_id=1)
    bob = fx.bound_rounding(rounding="half_even", max_points=222, user_id=2)

    first, second = await asyncio.gather(
        _compute(executor, [_round_item(fx.ROUNDING_CODE, "alice")], principal="alice", settings={fx.ROUNDING_CODE: alice}),
        _compute(executor, [_round_item(fx.ROUNDING_CODE, "bob")], principal="bob", settings={fx.ROUNDING_CODE: bob}),
    )

    assert (_seen(first["alice"])["rounded"], _seen(first["alice"])["max_points"]) == (3, 111)
    assert (_seen(second["bob"])["rounded"], _seen(second["bob"])["max_points"]) == (2, 222)


@pytest.mark.asyncio
async def test_an_unconfigured_tool_starts_no_worker_and_its_sibling_runs(executor: ToolExecutor, started_workers: list[str]):
    """The required ``region`` has no value: ``service_unavailable``, not retryable, no execution id, no process for it; the
    other item of the batch succeeds with its own values."""
    unconfigured = build_bound_settings("tool", fx.REQUIRED_CODE, (fx.REGION,), {}, {}, user_id=1)
    assert unconfigured.missing == ("region",), "barrier: the core reports the missing field"
    settings = {fx.REQUIRED_CODE: unconfigured, fx.ROUNDING_CODE: fx.bound_rounding(rounding="half_up")}
    items = [fx.item_for(fx.SettingsToolRegistry, fx.REQUIRED_CODE, correlation="needs-region"), _round_item(fx.ROUNDING_CODE, "fine")]

    results = await _compute(executor, items, settings=settings)

    refused = results["needs-region"]
    assert (refused.status, refused.error.code, refused.error.retryable, refused.execution_id) == ("error", "service_unavailable", False, None)
    assert _seen(results["fine"])["rounded"] == 3
    assert started_workers == [fx.ROUNDING_CODE], "a worker was started for the unconfigured Tool"


@pytest.mark.asyncio
async def test_a_tool_whose_required_field_has_a_value_runs_and_sees_it(executor: ToolExecutor, started_workers: list[str]):
    configured = build_bound_settings("tool", fx.REQUIRED_CODE, (fx.REGION,), {"region": fx.stored("us")}, {}, user_id=1)
    assert configured.missing == ()

    results = await _compute(executor, [fx.item_for(fx.SettingsToolRegistry, fx.REQUIRED_CODE, correlation="ok")], settings={fx.REQUIRED_CODE: configured})

    assert _seen(results["ok"]) == {"region": "us"}
    assert started_workers == [fx.REQUIRED_CODE]


@pytest.mark.asyncio
async def test_a_tool_without_fields_is_called_with_nothing_bound(executor: ToolExecutor):
    """No entry for it (``bound_settings_for_batch`` leaves it out): the worker binds nothing, as today."""
    results = await _compute(executor, [fx.item_for(fx.SettingsToolRegistry, fx.PLAIN_CODE, correlation="plain")], settings={})

    assert _seen(results["plain"]) == {"pong": True, "bound": False}
