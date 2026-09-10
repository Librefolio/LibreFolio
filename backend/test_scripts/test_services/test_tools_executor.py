"""Tool lifecycle contracts: owned POSIX workers, pipes and deterministic gates.

This entire file requires a dedicated lifecycle lease, not a schemas/PURE slot.
It never starts the application or accesses a database. State-machine doubles
make cancellation/deadline races reproducible; separate cases use the real spawn
worker and process-tree supervisor. Emergency fixture cleanup is deliberately
after the assertions about production cleanup.
"""

from __future__ import annotations

import asyncio
import errno
import os
import signal
import struct
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Literal
from uuid import uuid4

import psutil
import pytest
import pytest_asyncio
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.tools import ToolComputeBatchRequest, ToolComputeItem, ToolError, ToolItemMetrics, ToolPlatformPolicy
from backend.app.services.tools import executor as executor_module
from backend.app.services.tools import process_tree as tree_module
from backend.app.services.tools import worker as worker_module
from backend.app.services.tools.base import ToolExecutionError
from backend.app.services.tools.executor import ToolExecutor
from backend.app.services.tools.registry import build_tool_definition
from backend.app.services.tools.wire import decode_json, encode_json
from backend.app.services.tools.worker import PipeCancellation, ToolWorkerJob
from backend.test_scripts.test_services._tools_executor_fixtures import (
    FixtureOutput,
    FixturePlugin,
    FixtureRegistry,
    SpawnHandle,
    SpawnHarness,
)

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Tool lifecycle ownership requires POSIX process sessions")
_WAIT = 30.0


class _AliasedWorkerOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["ready"]
    text: str = Field(validation_alias="wire_text", serialization_alias="wire_text")


class _AliasedWorkerPlugin(FixturePlugin):
    tool_code = "private_worker_alias"
    output_type = _AliasedWorkerOutput

    def compute(self, parameters, context):
        return _AliasedWorkerOutput.model_validate({"status": "ready", "wire_text": parameters.text})


def _policy(**changes) -> ToolPlatformPolicy:
    """Leave generous real startup headroom; timeout races use explicit clocks."""
    values = {
        "workers": 2,
        "max_pending_items": 8,
        "max_pending_per_principal": 4,
        "queue_timeout_ms": 30_000,
        "job_timeout_ms": 60_000,
        "soft_timeout_ms": 50_000,
        "output_reserve_ms": 5_000,
        "cleanup_timeout_ms": 5_000,
        "request_timeout_ms": 120_000,
        "client_timeout_ms": 130_000,
    }
    values.update(changes)
    return ToolPlatformPolicy.model_validate(values)


def _item(correlation: str, scenario: str = "echo", **parameters) -> ToolComputeItem:
    descriptor = FixtureRegistry.get_definition(FixturePlugin.tool_code).descriptor
    return ToolComputeItem(
        correlation_id=correlation,
        tool_code=descriptor.tool_code,
        contract_version=descriptor.contract_version,
        implementation_version=descriptor.implementation_version,
        schema_fingerprint=descriptor.schema_fingerprint,
        parameters={"operation": "exercise", "scenario": scenario, **parameters},
    )


def _batch(*items: ToolComputeItem) -> ToolComputeBatchRequest:
    return ToolComputeBatchRequest(request_id=uuid4().hex, items=list(items))


def _owned_job(item: ToolComputeItem | None = None, *, max_result_bytes: int = 262_144):
    item = item or _item("private-item")
    started = time.monotonic()
    spec = ToolWorkerJob(
        execution_id=uuid4().hex,
        tool_code=item.tool_code,
        contract_version=item.contract_version,
        implementation_version=item.implementation_version,
        schema_fingerprint=item.schema_fingerprint,
        parameters=encode_json(item.parameters),
        soft_deadline=started + 50,
        hard_deadline=started + 60,
        max_parameter_bytes=131_072,
        max_result_bytes=max_result_bytes,
        max_json_depth=32,
    )
    return executor_module._OwnedJob(spec, "private-principal", 0, started, started)


async def _until(predicate, description: str):
    """Poll a stated condition with a deadline, never delay before an assertion."""
    loop = asyncio.get_running_loop()
    result = loop.create_future()
    scheduled = None

    def inspect_condition():
        nonlocal scheduled
        if result.done():
            return
        try:
            value = predicate()
        except Exception as exc:
            result.set_exception(exc)
        else:
            if value:
                result.set_result(value)
            else:
                scheduled = loop.call_later(0.01, inspect_condition)

    inspect_condition()
    try:
        return await asyncio.wait_for(result, timeout=_WAIT)
    except TimeoutError as exc:
        raise AssertionError(f"Condition did not become true: {description}") from exc
    finally:
        if scheduled is not None:
            scheduled.cancel()


def _assert_native_termination(handle: SpawnHandle) -> None:
    assert handle.owned_identities, "A boot/identity barrier must precede termination assertions"
    for identity in handle.owned_identities:
        assert identity.current() is None, f"Production cleanup left {identity.role} {identity.pid} alive"
    # Every recorded sender is now terminated, so this drain is a real closing
    # barrier rather than a timing-dependent absence probe on a living worker.
    handle.drain()


async def _begin_worker(harness: SpawnHarness, *, stage: str | None = "compute") -> SpawnHandle:
    handle = await asyncio.to_thread(harness.next_handle, _WAIT)
    boot = await asyncio.to_thread(handle.receive, "boot", _WAIT)
    assert boot["execution_id"] == handle.execution_id
    assert handle.requested_daemon is False
    await asyncio.to_thread(handle.send, "start")
    if stage is not None:
        await asyncio.to_thread(handle.receive, stage, _WAIT)
    return handle


@dataclass
class _Runtime:
    harness: SpawnHarness
    executors: list[ToolExecutor] = field(default_factory=list)
    tasks: list[asyncio.Task] = field(default_factory=list)

    def executor(self, **policy_changes) -> ToolExecutor:
        value = ToolExecutor(_policy(**policy_changes), FixtureRegistry)
        self.executors.append(value)
        return value

    def compute(self, executor: ToolExecutor, batch: ToolComputeBatchRequest, principal: str = "private-principal") -> asyncio.Task:
        task = asyncio.create_task(executor.compute(batch, principal_key=principal))
        self.tasks.append(task)
        return task


@pytest_asyncio.fixture
async def runtime(monkeypatch):
    harness = SpawnHarness()
    # Replace only this module's binding, not multiprocessing.get_context globally.
    monkeypatch.setattr(executor_module, "multiprocessing", harness)
    owned = _Runtime(harness)
    try:
        yield owned
    finally:
        for task in owned.tasks:
            if not task.done():
                task.cancel()
        try:
            for executor in owned.executors:
                await executor.shutdown()
        finally:
            try:
                await asyncio.to_thread(harness.cleanup)
            finally:
                if owned.tasks:
                    await asyncio.wait_for(asyncio.gather(*owned.tasks, return_exceptions=True), timeout=_WAIT)
                io_tasks = {
                    job.io_task
                    for executor in owned.executors
                    for job in executor._jobs.values()
                    if job.io_task is not None
                }
                if io_tasks:
                    await asyncio.wait_for(asyncio.gather(*io_tasks, return_exceptions=True), timeout=_WAIT)


class _Clock:
    def __init__(self, now: float):
        self.now = now

    def monotonic(self) -> float:
        return self.now


class _AccountingOwner:
    """No native processes: an event-gated completion source for quota races."""

    def __init__(self, *, cleaned: bool = True, tree=None):
        self.release = threading.Event()
        self.entered = threading.Condition()
        self.jobs = []
        self.cleaned = cleaned
        self.tree = tree

    def __call__(self, job, registry_class, cleanup_ms):
        if self.tree is not None:
            job.tree = self.tree
        with self.entered:
            self.jobs.append(job)
            self.entered.notify_all()
        if not self.release.wait(_WAIT):
            raise AssertionError("The test did not release its accounting owner")
        error = None if self.cleaned else ToolError(code="cleanup_failed", retryable=False)
        value = FixtureOutput(status="ready", text="private", pid=1, execution_id=job.spec.execution_id).model_dump()
        return executor_module._Outcome(value if self.cleaned else None, error, ToolItemMetrics(), self.cleaned)

    def wait_for_jobs(self, count: int):
        with self.entered:
            if not self.entered.wait_for(lambda: len(self.jobs) >= count, timeout=_WAIT):
                raise AssertionError(f"Expected {count} owned accounting jobs, received {len(self.jobs)}")
            return tuple(self.jobs)


@asynccontextmanager
async def _accounting_executor(monkeypatch, *, policy=None, owner=None):
    owner = owner or _AccountingOwner()
    executor = ToolExecutor(policy or _policy(), FixtureRegistry)
    monkeypatch.setattr(executor_module, "_run_owned_job", owner)
    try:
        yield executor, owner
    finally:
        owner.release.set()
        await executor.shutdown()
        io_tasks = [job.io_task for job in owner.jobs if job.io_task is not None]
        if io_tasks:
            await asyncio.wait_for(asyncio.gather(*io_tasks, return_exceptions=True), timeout=_WAIT)


@pytest.mark.asyncio
async def test_independent_lanes_run_identical_items_without_coalescing(runtime):
    executor = runtime.executor()
    task = runtime.compute(executor, _batch(_item("owned-a", "hold"), _item("owned-b", "hold")))
    handles = [await _begin_worker(runtime.harness) for _ in range(2)]

    # Both real computes are blocked at their own control pipe simultaneously.
    assert len({handle.execution_id for handle in handles}) == 2
    roots = {identity.pid for handle in handles for identity in handle.owned_identities if identity.role == "root"}
    assert len(roots) == 2
    assert executor.snapshot().active == 2
    assert executor.snapshot().pending == 2
    for handle in handles:
        await asyncio.to_thread(handle.send, "release")

    response = await asyncio.wait_for(task, timeout=_WAIT)
    assert [result.correlation_id for result in response.results] == ["owned-a", "owned-b"]
    assert {result.execution_id for result in response.results} == {handle.execution_id for handle in handles}
    assert response.success_count == 2
    assert response.failed_count == 0
    for result in response.results:
        assert result.result["execution_id"] == result.execution_id
        assert result.result["pid"] in roots
    for handle in handles:
        await asyncio.to_thread(_assert_native_termination, handle)
    await _until(lambda: executor.snapshot().pending == 0, "all physical job credits returned")
    assert executor.snapshot().active == 0
    assert executor.snapshot().degraded_lanes == 0


@pytest.mark.asyncio
async def test_out_of_order_completion_preserves_request_order_and_correlation(runtime):
    executor = runtime.executor()
    task = runtime.compute(
        executor,
        _batch(_item("owned-first", "hold", text="first"), _item("owned-second", "hold", text="second")),
    )
    handles = [await _begin_worker(runtime.harness) for _ in range(2)]
    by_text = {
        decode_json(executor._jobs[handle.execution_id].spec.parameters)["text"]: handle
        for handle in handles
    }
    await asyncio.to_thread(by_text["second"].send, "release")
    await _until(lambda: executor.snapshot().completed == 1, "second physical item completed while first remains gated")
    await asyncio.to_thread(_assert_native_termination, by_text["second"])
    assert not task.done(), "The batch must still wait for its explicitly gated first item"
    await asyncio.to_thread(by_text["first"].send, "release")

    response = await asyncio.wait_for(task, timeout=_WAIT)
    assert [result.correlation_id for result in response.results] == ["owned-first", "owned-second"]
    by_correlation = {result.correlation_id: result for result in response.results}
    for correlation, text in (("owned-first", "first"), ("owned-second", "second")):
        result = by_correlation[correlation]
        assert result.status == "success"
        assert result.execution_id == by_text[text].execution_id
        assert result.result["text"] == text
    await asyncio.to_thread(_assert_native_termination, by_text["first"])


@pytest.mark.asyncio
async def test_batch_principal_and_global_quotas_do_not_consume_rejected_credit(monkeypatch):
    policy = _policy(workers=2, max_pending_items=4, max_pending_per_principal=2)
    async with _accounting_executor(monkeypatch, policy=policy) as (executor, owner):
        first = asyncio.create_task(executor.compute(_batch(_item("first-a"), _item("first-b")), principal_key="owned-first"))
        second = None
        try:
            await asyncio.to_thread(owner.wait_for_jobs, 2)
            before = executor.snapshot()
            with pytest.raises(ToolExecutionError) as same_principal:
                await executor.compute(_batch(_item("rejected-same")), principal_key="owned-first")
            assert same_principal.value.code == "queue_full"
            assert same_principal.value.retryable is True
            assert executor.snapshot() == before

            second = asyncio.create_task(executor.compute(_batch(_item("second-a"), _item("second-b")), principal_key="owned-second"))
            await _until(lambda: executor.snapshot().pending == 4 and executor.snapshot().queued == 2, "second principal queued behind two occupied lanes")
            before = executor.snapshot()
            with pytest.raises(ToolExecutionError) as global_capacity:
                await executor.compute(_batch(_item("rejected-global")), principal_key="owned-third")
            assert global_capacity.value.code == "queue_full"
            assert executor.snapshot() == before

            second.cancel()
            with pytest.raises(asyncio.CancelledError):
                await second
            await _until(lambda: executor.snapshot().pending == 2 and executor.snapshot().queued == 0, "only cancelled queued tickets released")
            assert executor.snapshot().active == 2
            assert len(owner.jobs) == 2
            owner.release.set()
            response = await asyncio.wait_for(first, timeout=_WAIT)
            assert response.success_count == 2
            await _until(lambda: executor.snapshot().pending == 0, "all owned quota credits returned once")
        finally:
            owner.release.set()
            for task in (first, second):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(*(task for task in (first, second) if task is not None), return_exceptions=True)


@pytest.mark.asyncio
async def test_per_principal_item_limit_is_checked_before_any_job(monkeypatch):
    async with _accounting_executor(monkeypatch, policy=_policy(max_pending_per_principal=1)) as (executor, owner):
        with pytest.raises(ToolExecutionError) as caught:
            await executor.compute(_batch(_item("owned-a"), _item("owned-b")), principal_key="owned-principal")
        assert caught.value.code == "queue_full"
        assert executor.snapshot().pending == 0
        assert executor.snapshot().active == 0
        assert owner.jobs == []


@pytest.mark.asyncio
async def test_cancellation_before_item_body_returns_every_ticket_exactly_once():
    entered = []

    class CancelBeforeStartExecutor(ToolExecutor):
        def _admit(self, principal_key, count):
            admitted = super()._admit(principal_key, count)

            def cancel_registered_items():
                for task in tuple(self._items):
                    task.cancel()

            # This callback is queued before compute schedules the item bodies.
            asyncio.get_running_loop().call_soon(cancel_registered_items)
            return admitted

        async def _run_item(self, *args, **kwargs):
            entered.append(True)
            return await super()._run_item(*args, **kwargs)

    executor = CancelBeforeStartExecutor(_policy(), FixtureRegistry)
    try:
        with pytest.raises(asyncio.CancelledError):
            await executor.compute(_batch(_item("owned-a"), _item("owned-b")), principal_key="owned-principal")
        await _until(lambda: executor.snapshot().completed == 2, "both cancelled task callbacks completed")
        assert entered == []
        snapshot = executor.snapshot()
        assert (snapshot.pending, snapshot.active, snapshot.queued, snapshot.failed) == (0, 0, 0, 2)
        assert not executor._items
        assert not executor._principals
        assert not executor._batches
        assert executor._available.qsize() == executor.policy.workers
    finally:
        await executor.shutdown()


@pytest.mark.asyncio
async def test_queued_items_keep_the_common_admission_deadline(monkeypatch):
    clock = _Clock(100.0)
    monkeypatch.setattr(executor_module, "time", clock)
    async with _accounting_executor(monkeypatch, policy=_policy(workers=1)) as (executor, owner):
        task = asyncio.create_task(executor.compute(_batch(_item("owned-first"), _item("owned-queued")), principal_key="owned-principal"))
        try:
            (job,) = await asyncio.to_thread(owner.wait_for_jobs, 1)
            assert job.admitted_at == 100.0
            await _until(lambda: executor.snapshot().queued == 1, "second item waiting on the occupied lane")
            clock.now = 131.0
            owner.release.set()
            response = await asyncio.wait_for(task, timeout=_WAIT)
            by_id = {item.correlation_id: item for item in response.results}
            assert by_id["owned-first"].status == "success"
            assert by_id["owned-queued"].status == "error"
            assert by_id["owned-queued"].error.code == "queue_timeout"
            assert by_id["owned-queued"].execution_id is None
            assert len(owner.jobs) == 1
            await _until(lambda: executor.snapshot().pending == 0, "expired queued ticket returned its credit")
            assert executor._available.qsize() == 1
        finally:
            owner.release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_request_origin_caps_job_deadlines_before_startup(monkeypatch):
    clock = _Clock(100.0)
    monkeypatch.setattr(executor_module, "time", clock)
    policy = _policy(
        workers=1,
        ingress_timeout_ms=1_000,
        queue_timeout_ms=1_000,
        job_timeout_ms=2_000,
        soft_timeout_ms=1_000,
        output_reserve_ms=500,
        cleanup_timeout_ms=1_000,
        response_reserve_ms=1_000,
        request_timeout_ms=6_000,
        client_timeout_ms=7_000,
    )
    async with _accounting_executor(monkeypatch, policy=policy) as (executor, owner):
        task = asyncio.create_task(executor.compute(_batch(_item("owned")), principal_key="owned-principal", request_started=98.0))
        try:
            (job,) = await asyncio.to_thread(owner.wait_for_jobs, 1)
            assert job.admitted_at == job.granted_at == 100.0
            assert job.spec.hard_deadline == 102.0
            assert job.spec.soft_deadline == 101.0
            owner.release.set()
            response = await asyncio.wait_for(task, timeout=_WAIT)
            assert response.success_count == 1
        finally:
            owner.release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_cancel_before_ready_never_constructs_the_plugin_and_reaps_root(runtime):
    executor = runtime.executor(workers=1)
    task = runtime.compute(executor, _batch(_item("owned", "hold")))
    handle = await asyncio.to_thread(runtime.harness.next_handle, _WAIT)
    await asyncio.to_thread(handle.receive, "boot", _WAIT)
    # The wrapper gate has not opened: production ready/ACK cannot have happened.
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=_WAIT)

    await _until(lambda: executor.snapshot().pending == 0, "pre-ready cancellation finished physical cleanup")
    await asyncio.to_thread(_assert_native_termination, handle)
    assert {frame["kind"] for frame in handle.frames} == {"boot"}
    assert executor.snapshot().active == 0
    assert executor._available.qsize() == 1


@pytest.mark.asyncio
async def test_cold_start_is_inside_the_absolute_hard_deadline(monkeypatch):
    harness = SpawnHarness()
    monkeypatch.setattr(executor_module, "multiprocessing", harness)
    clock = _Clock(time.monotonic())
    monkeypatch.setattr(executor_module, "time", clock)
    job = _owned_job()
    task = asyncio.create_task(asyncio.to_thread(executor_module._run_owned_job, job, FixtureRegistry, 5_000))
    try:
        handle = await asyncio.to_thread(harness.next_handle, _WAIT)
        await asyncio.to_thread(handle.receive, "boot", _WAIT)
        # Advance only the supervisor's clock; asyncio and native cleanup clocks
        # remain real. The child has not been permitted to send ready.
        clock.now = job.spec.hard_deadline + 1
        outcome = await asyncio.wait_for(asyncio.shield(task), timeout=_WAIT)
        assert outcome.error.code == "execution_timeout"
        assert outcome.error.retryable is True
        assert outcome.cleaned is True
        assert outcome.metrics.startup_ms is None
        assert outcome.metrics.compute_ms is None
        assert job.tree.closed is True
        await asyncio.to_thread(_assert_native_termination, handle)
        assert {frame["kind"] for frame in handle.frames} == {"boot"}
    finally:
        job.cancel.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=_WAIT)
        finally:
            await asyncio.to_thread(harness.cleanup)


@pytest.mark.asyncio
async def test_partial_raw_frame_honors_hard_deadline_and_releases_owned_lane(runtime, monkeypatch):
    clock = _Clock(time.monotonic())
    monkeypatch.setattr(executor_module, "time", clock)
    executor = runtime.executor(workers=1)
    task = runtime.compute(executor, _batch(_item("owned", "partial_frame")))
    handle = await _begin_worker(runtime.harness, stage="partial-frame")
    job = executor._jobs[handle.execution_id]

    assert not task.done(), "A partial frame must keep the physical reader pending"
    clock.now = job.spec.hard_deadline + 1
    response = await asyncio.wait_for(task, timeout=_WAIT)
    (result,) = response.results

    assert result.status == "error"
    assert result.error.code == "execution_timeout"
    assert result.error.retryable is True
    assert result.metrics.cleanup_ms is not None
    await asyncio.to_thread(_assert_native_termination, handle)
    await _until(lambda: executor.snapshot().pending == 0, "partial-frame timeout completed physical cleanup")
    assert job.io_task is not None and job.io_task.done()
    assert job.tree is not None and job.tree.closed is True
    snapshot = executor.snapshot()
    assert (snapshot.pending, snapshot.active, snapshot.degraded_lanes, snapshot.available) == (0, 0, 0, True)
    assert executor._available.qsize() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scenario", "parameters", "expected_code"),
    [
        ("crash", {}, "worker_crashed"),
        ("oversize", {"size": 2_048}, "output_limit_exceeded"),
        ("unicode", {}, "invalid_output"),
        ("invalid_output", {}, "invalid_output"),
        ("not_model", {}, "invalid_output"),
        ("echo", {"text": 123}, "invalid_parameters"),
    ],
)
async def test_real_worker_failures_are_platform_errors_and_leave_no_owned_process(runtime, scenario, parameters, expected_code):
    executor = runtime.executor(workers=1, max_result_bytes=1_024)
    task = runtime.compute(executor, _batch(_item("owned", scenario, **parameters)))
    handle = await _begin_worker(runtime.harness, stage=None)
    response = await asyncio.wait_for(task, timeout=_WAIT)
    (result,) = response.results

    assert result.correlation_id == "owned"
    assert result.execution_id == handle.execution_id
    assert result.status == "error"
    assert result.error.code == expected_code
    assert response.success_count == 0
    assert response.failed_count == 1
    assert "PRIVATE_OUTPUT_REJECTED" not in result.error.model_dump_json()
    await _until(lambda: executor.snapshot().pending == 0, "failed job released only after cleanup")
    await asyncio.to_thread(_assert_native_termination, handle)
    assert executor.snapshot().active == 0
    assert executor.snapshot().degraded_lanes == 0
    if scenario == "invalid_output":
        assert result.metrics.output_validation_ms is not None
        assert result.error.issue_count > 0
    if expected_code == "invalid_parameters":
        assert result.metrics.input_validation_ms is not None
        assert result.metrics.compute_ms is None
        assert not any(frame["kind"] in {"constructed", "compute"} for frame in handle.frames)


@pytest.mark.asyncio
async def test_each_completed_item_gets_a_new_execution_instead_of_a_cached_worker(runtime):
    executor = runtime.executor(workers=1)
    execution_ids = set()
    for correlation in ("owned-first", "owned-next"):
        task = runtime.compute(executor, _batch(_item(correlation)))
        handle = await _begin_worker(runtime.harness)
        response = await asyncio.wait_for(task, timeout=_WAIT)
        (result,) = response.results
        assert result.status == "success"
        assert result.correlation_id == correlation
        assert result.execution_id == handle.execution_id
        assert result.execution_id not in execution_ids
        execution_ids.add(result.execution_id)
        await asyncio.to_thread(_assert_native_termination, handle)
        await _until(lambda: executor.snapshot().pending == 0, "completed execution credit returned")
    assert len(runtime.harness.handles) == len(execution_ids) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["release", "fail", "crash"])
@pytest.mark.parametrize("ignore_term", [False, True], ids=["term", "force-kill"])
async def test_root_child_and_grandchild_are_reaped_before_publishing_result(runtime, command, ignore_term):
    executor = runtime.executor(workers=1)
    task = runtime.compute(executor, _batch(_item("owned", "descendants", ignore_term=ignore_term, text="PRIVATE_TREE_SENTINEL")))
    handle = await _begin_worker(runtime.harness, stage="tree")
    assert {identity.role for identity in handle.owned_identities} == {"root", "child", "grandchild"}
    live = await asyncio.to_thread(lambda: all(identity.current() is not None for identity in handle.owned_identities))
    assert live, "The complete live tree must be observed before requesting teardown"

    await asyncio.to_thread(handle.send, command)
    response = await asyncio.wait_for(task, timeout=_WAIT)
    (result,) = response.results
    if command == "release":
        assert result.status == "success"
    else:
        assert result.status == "error"
        assert result.error.code == ("execution_failed" if command == "fail" else "worker_crashed")
        assert "PRIVATE_TREE_SENTINEL" not in result.error.model_dump_json()
    assert result.metrics.cleanup_ms is not None
    await asyncio.to_thread(_assert_native_termination, handle)
    await _until(lambda: executor.snapshot().pending == 0, "tree teardown released its lane")
    assert executor.snapshot().active == 0
    assert executor.snapshot().degraded_lanes == 0


@pytest.mark.asyncio
async def test_hard_timeout_reaps_a_live_descendant_tree(monkeypatch):
    harness = SpawnHarness()
    monkeypatch.setattr(executor_module, "multiprocessing", harness)
    clock = _Clock(time.monotonic())
    monkeypatch.setattr(executor_module, "time", clock)
    job = _owned_job(_item("owned", "descendants", ignore_term=True))
    task = asyncio.create_task(asyncio.to_thread(executor_module._run_owned_job, job, FixtureRegistry, 5_000))
    try:
        handle = await _begin_worker(harness, stage="tree")
        assert {identity.role for identity in handle.owned_identities} == {"root", "child", "grandchild"}
        clock.now = job.spec.hard_deadline + 1
        outcome = await asyncio.wait_for(asyncio.shield(task), timeout=_WAIT)
        assert outcome.error.code == "execution_timeout"
        assert outcome.cleaned is True
        assert outcome.value is None
        await asyncio.to_thread(_assert_native_termination, handle)
        assert job.tree.closed is True
    finally:
        job.cancel.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=_WAIT)
        finally:
            await asyncio.to_thread(harness.cleanup)


@pytest.mark.asyncio
@pytest.mark.parametrize("stop", ["cancel", "shutdown"])
async def test_cancellation_and_shutdown_reap_descendants_and_preserve_credit_ownership(runtime, stop):
    executor = runtime.executor(workers=1)
    task = runtime.compute(executor, _batch(_item("owned", "descendants", ignore_term=True)))
    handle = await _begin_worker(runtime.harness, stage="tree")
    if stop == "cancel":
        task.cancel()
    else:
        await executor.shutdown()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=_WAIT)
    await _until(lambda: executor.snapshot().pending == 0, "cancelled tree completed cleanup")
    await asyncio.to_thread(_assert_native_termination, handle)
    assert executor.snapshot().active == 0
    assert executor.snapshot().degraded_lanes == 0
    if stop == "shutdown":
        assert executor.snapshot().available is False
        with pytest.raises(ToolExecutionError) as caught:
            await executor.compute(_batch(_item("after-shutdown")), principal_key="owned-new-principal")
        assert caught.value.code == "service_unavailable"
        assert len(runtime.harness.handles) == 1


class _RetainedTree:
    """A non-native teardown witness: false means no proof of termination."""

    def __init__(self):
        self.closed = False
        self.can_clean = False
        self.attempts = []

    def cleanup(self, deadline):
        self.attempts.append(deadline)
        self.closed = self.can_clean
        return self.closed


@pytest.mark.asyncio
async def test_quarantine_retains_credit_and_prevents_singleton_replacement_until_reaped(monkeypatch):
    tree = _RetainedTree()
    owner = _AccountingOwner(cleaned=False, tree=tree)
    async with _accounting_executor(monkeypatch, policy=_policy(workers=1), owner=owner) as (executor, _):
        monkeypatch.setattr(executor_module, "_executor", executor)
        task = asyncio.create_task(executor.compute(_batch(_item("owned")), principal_key="owned-principal"))
        try:
            await asyncio.to_thread(owner.wait_for_jobs, 1)
            owner.release.set()
            response = await asyncio.wait_for(task, timeout=_WAIT)
            (result,) = response.results
            assert result.status == "error"
            assert result.error.code == "cleanup_failed"
            snapshot = executor.snapshot()
            assert (snapshot.pending, snapshot.active, snapshot.degraded_lanes, snapshot.available) == (1, 1, 1, False)
            assert executor._available.qsize() == 0
            with pytest.raises(ToolExecutionError) as unavailable:
                await executor.compute(_batch(_item("not-a-replacement")), principal_key="owned-other")
            assert unavailable.value.code == "service_unavailable"
            assert len(owner.jobs) == 1

            await executor_module.shutdown_tool_executor()
            assert tree.attempts
            assert executor_module.get_tool_executor() is executor
            assert executor.snapshot().pending == 1

            tree.can_clean = True
            await executor_module.shutdown_tool_executor()
            assert executor.snapshot().pending == 0
            assert executor_module._executor is None
            replacement = executor_module.get_tool_executor()
            assert replacement is not executor
            await executor_module.shutdown_tool_executor()
            assert executor_module._executor is None
        finally:
            tree.can_clean = True
            owner.release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await executor.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["cancelled", "exception", "unclean"])
async def test_physical_owner_callback_never_releases_an_unproven_job(terminal):
    executor = ToolExecutor(_policy(workers=1), FixtureRegistry)
    executor._admit("owned-principal", 1)
    lane = executor._available.get_nowait()
    job = _owned_job()
    job.principal_key = "owned-principal"
    job.lane = lane
    job.tree = _RetainedTree()
    executor._jobs[job.spec.execution_id] = job
    future = asyncio.get_running_loop().create_future()
    job.io_task = future
    if terminal == "cancelled":
        future.cancel()
    elif terminal == "exception":
        future.set_exception(RuntimeError("PRIVATE_OWNER_FAILURE"))
    else:
        future.set_result(executor_module._Outcome(None, ToolError(code="cleanup_failed", retryable=False), ToolItemMetrics(), False))
    try:
        executor._job_finished(job, future)
        assert job.quarantined is True
        snapshot = executor.snapshot()
        assert (snapshot.pending, snapshot.active, snapshot.degraded_lanes) == (1, 1, 1)
        assert executor._available.qsize() == 0
    finally:
        job.tree.can_clean = True
        await executor.shutdown()
    assert executor.snapshot().pending == 0


class _Frames:
    def __init__(self, frames, events):
        self._reader, writer = os.pipe()
        self._kinds = deque(frame["kind"] for frame in frames)
        self._fileno_calls = 0
        self.events = events
        try:
            for frame in frames:
                payload = encode_json(frame)
                framed = struct.pack("!i", len(payload)) + payload
                written = os.write(writer, framed)
                assert written == len(framed)
        finally:
            os.close(writer)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        os.close(self._reader)

    def fileno(self):
        if self._fileno_calls % 2 == 0:
            assert self._kinds, "Protocol fixture exhausted before the expected terminal state"
            self.events.append(("read", self._kinds.popleft()))
        self._fileno_calls += 1
        return self._reader


class _Commands:
    def __init__(self, events):
        self.events = events

    def send_bytes(self, value):
        self.events.append(("command", value))


class _SessionWitness:
    def __init__(self, events):
        self.events = events
        self.process = SimpleNamespace(exitcode=None)

    def confirm_session(self, **identity):
        self.events.append(("adopt", identity))


def _ready(job):
    return {"kind": "ready", "execution_id": job.spec.execution_id, "pid": 101, "pgid": 101, "created_at": 1.25}


def _result(job):
    return {
        "kind": "result",
        "execution_id": job.spec.execution_id,
        "status": "success",
        "metrics": ToolItemMetrics().model_dump(),
        "result": {"private": True},
    }


def test_ready_is_adopted_before_ack_and_result_consumption():
    job = _owned_job()
    events = []
    job.tree = _SessionWitness(events)
    with _Frames([_ready(job), _result(job)], events) as frames:
        value, error = executor_module._wait_result(frames, _Commands(events), job)

    assert error is None
    assert value == {"private": True}
    assert events == [
        ("read", "ready"),
        ("adopt", {"pid": 101, "group_id": 101, "created_at": 1.25}),
        ("command", b"\x00"),
        ("read", "result"),
    ]
    assert job.metrics.startup_ms is not None


@pytest.mark.parametrize("fault", ["result-before-ready", "duplicate-ready", "wrong-execution", "ready-extra", "ready-boolean-pid"])
def test_malformed_handshake_cannot_authorize_or_publish_a_result(fault):
    job = _owned_job()
    events = []
    job.tree = _SessionWitness(events)
    ready = _ready(job)
    frames = [ready]
    if fault == "result-before-ready":
        frames = [_result(job)]
    elif fault == "duplicate-ready":
        frames = [ready, dict(ready)]
    elif fault == "wrong-execution":
        ready["execution_id"] = "unrelated-execution"
    elif fault == "ready-extra":
        ready["unexpected"] = "private"
    else:
        ready["pid"] = True
    with _Frames(frames, events) as response:
        with pytest.raises(ToolExecutionError) as caught:
            executor_module._wait_result(response, _Commands(events), job)
    assert caught.value.code == "worker_crashed"
    commands = [value for kind, value in events if kind == "command"]
    assert commands == ([b"\x00"] if fault == "duplicate-ready" else [])


def test_parent_rechecks_result_byte_limit_instead_of_truncating():
    job = _owned_job(max_result_bytes=4)
    frame = _result(job)
    frame["result"] = "é"
    value, error = executor_module._accept_result(frame, job)
    assert value == "é"
    assert error is None
    frame["result"] = "éa"
    with pytest.raises(ToolExecutionError) as caught:
        executor_module._accept_result(frame, job)
    assert caught.value.code == "output_limit_exceeded"


def test_raw_frame_length_over_the_owned_limit_is_rejected_before_payload_read():
    job = _owned_job(max_result_bytes=4)
    reader, writer = os.pipe()
    try:
        declared_length = (1 << 31) - 1
        assert os.write(writer, struct.pack("!i", declared_length)) == 4
    finally:
        os.close(writer)

    with os.fdopen(reader, "rb") as response:
        with pytest.raises(ToolExecutionError) as caught:
            executor_module._read_frame(response, job)

    assert caught.value.code == "output_limit_exceeded"


def test_frame_completed_at_deadline_is_not_published_after_decode(monkeypatch):
    job = _owned_job()
    clock = _Clock(job.spec.hard_deadline - 1)
    decode = executor_module.decode_json

    def decode_then_expire(payload, *, max_depth):
        value = decode(payload, max_depth=max_depth)
        clock.now = job.spec.hard_deadline
        return value

    monkeypatch.setattr(executor_module, "time", clock)
    monkeypatch.setattr(executor_module, "decode_json", decode_then_expire)
    with _Frames([_result(job)], []) as response:
        with pytest.raises(ToolExecutionError) as caught:
            executor_module._read_frame(response, job)

    assert caught.value.code == "execution_timeout"
    assert caught.value.retryable is True


def test_worker_serializes_aliases_and_revalidates_the_exact_wire_payload():
    definition = build_tool_definition(_AliasedWorkerPlugin)

    class AliasedRegistry:
        @classmethod
        def get_definition(cls, code):
            return definition if code == definition.descriptor.tool_code else None

    class NeverCancelled:
        @staticmethod
        def is_set():
            return False

    now = time.monotonic()
    descriptor = definition.descriptor
    job = ToolWorkerJob(
        execution_id=uuid4().hex,
        tool_code=descriptor.tool_code,
        contract_version=descriptor.contract_version,
        implementation_version=descriptor.implementation_version,
        schema_fingerprint=descriptor.schema_fingerprint,
        parameters=encode_json({"operation": "exercise", "scenario": "echo", "text": "private"}),
        soft_deadline=now + 50,
        hard_deadline=now + 60,
        max_parameter_bytes=131_072,
        max_result_bytes=262_144,
        max_json_depth=32,
    )

    frame = worker_module._execute(job, NeverCancelled(), AliasedRegistry)

    assert frame["status"] == "success"
    assert frame["result"] == {"status": "ready", "wire_text": "private"}
    assert definition.output_adapter.validate_json(encode_json(frame["result"]), strict=True) == _AliasedWorkerOutput.model_validate({"status": "ready", "wire_text": "private"})


class _CancellationPipe:
    def __init__(self, messages):
        self.messages = deque(messages)
        self.reads = 0

    def poll(self, timeout):
        return bool(self.messages)

    def recv_bytes(self, maxlength):
        self.reads += 1
        value = self.messages.popleft()
        if isinstance(value, Exception):
            raise value
        if len(value) > maxlength:
            raise OSError("Fixture message exceeds the requested bound")
        return value


@pytest.mark.parametrize("first", [b"\x01", b"bad", EOFError(), OSError(), None])
def test_cancel_or_closed_pipe_before_ack_is_terminal(first):
    pipe = _CancellationPipe([] if first is None else [first])
    cancellation = PipeCancellation(pipe)
    assert cancellation.await_start(time.monotonic() + 60) is False
    reads = pipe.reads
    assert cancellation.is_set() is True
    assert pipe.reads == reads


def test_ack_opens_start_once_and_later_cancellation_is_sticky():
    pipe = _CancellationPipe([b"\x00", b"\x01"])
    cancellation = PipeCancellation(pipe)
    assert cancellation.await_start(time.monotonic() + 60) is True
    assert cancellation.is_set() is True
    reads = pipe.reads
    assert cancellation.is_set() is True
    assert pipe.reads == reads == 2


@dataclass
class _NativeProcess:
    pid: int
    born: float
    state: str = "running"
    running: bool = True
    descendants: tuple = ()
    signals: list = field(default_factory=list)
    children_calls: list = field(default_factory=list)

    def create_time(self):
        return self.born

    def is_running(self):
        return self.running

    def status(self):
        return self.state

    def children(self, recursive=False):
        self.children_calls.append(recursive)
        return list(self.descendants)

    def terminate(self):
        self.signals.append(signal.SIGTERM)

    def kill(self):
        self.signals.append(signal.SIGKILL)


class _ProcessHandle:
    def __init__(self, pid=101, exitcode=0):
        self.pid = pid
        self.exitcode = exitcode
        self.closed = False
        self.calls = []

    def is_alive(self):
        return self.exitcode is None

    def join(self, timeout):
        self.calls.append(("join", timeout))

    def close(self):
        self.closed = True
        self.calls.append(("close",))

    def terminate(self):
        self.calls.append(("terminate",))

    def kill(self):
        self.calls.append(("kill",))


def _native_view(monkeypatch, processes, groups=None):
    events = []
    groups = groups or {}

    def process(pid):
        if pid not in processes:
            raise psutil.NoSuchProcess(pid)
        return processes[pid]

    monkeypatch.setattr(
        tree_module,
        "psutil",
        SimpleNamespace(
            Process=process,
            process_iter=lambda attrs: iter(processes.values()),
            NoSuchProcess=psutil.NoSuchProcess,
            AccessDenied=psutil.AccessDenied,
            STATUS_ZOMBIE=psutil.STATUS_ZOMBIE,
        ),
    )
    monkeypatch.setattr(
        tree_module,
        "os",
        SimpleNamespace(getpgrp=lambda: 999, getpgid=lambda pid: groups.get(pid, -1), killpg=lambda pgid, sig: events.append((pgid, sig))),
    )
    return events


@pytest.mark.parametrize("state", ["different-birth", "zombie", "not-running", "gone"])
def test_process_identity_never_targets_a_reused_or_terminated_pid(state, monkeypatch):
    native = _NativeProcess(101, 1.25)
    processes = {101: native}
    if state == "different-birth":
        native.born = 2.5
    elif state == "zombie":
        native.state = psutil.STATUS_ZOMBIE
    elif state == "not-running":
        native.running = False
    else:
        processes.clear()
    _native_view(monkeypatch, processes)
    assert tree_module.ProcessIdentity(101, 1.25).current() is None
    assert native.signals == []


def test_reused_session_leader_pid_cannot_receive_group_or_individual_signals(monkeypatch):
    replacement = _NativeProcess(101, 2.5)
    events = _native_view(monkeypatch, {101: replacement}, {101: 101})
    handle = _ProcessHandle()
    tree = tree_module.OwnedProcessTree(handle)
    tree.root = tree_module.ProcessIdentity(101, 1.25)
    tree.known[101] = tree.root
    tree.group_id = 101

    tree._signal(force=True)

    assert events == []
    assert replacement.signals == []
    assert handle.calls == []


@pytest.mark.parametrize(
    ("pid", "pgid", "birth"),
    [(102, 102, 1.25), (101, 102, 1.25), (101, 101, 2.5)],
)
def test_session_confirmation_rejects_foreign_or_changed_identity(pid, pgid, birth, monkeypatch):
    _native_view(monkeypatch, {})
    tree = tree_module.OwnedProcessTree(_ProcessHandle())
    original = tree_module.ProcessIdentity(101, 1.25)
    tree.root = original
    with pytest.raises(ValueError):
        tree.confirm_session(pid=pid, group_id=pgid, created_at=birth)
    assert tree.root == original
    assert tree.group_id is None
    assert not tree.known


def test_session_confirmation_rejects_the_supervisor_process_group(monkeypatch):
    _native_view(monkeypatch, {})
    tree = tree_module.OwnedProcessTree(_ProcessHandle(pid=999))
    with pytest.raises(ValueError):
        tree.confirm_session(pid=999, group_id=999, created_at=1.25)
    assert tree.group_id is None


def test_tree_tracks_recursive_children_and_group_members_after_leader_exit(monkeypatch):
    child = _NativeProcess(102, 1.5)
    grandchild = _NativeProcess(103, 1.75)
    unrelated = _NativeProcess(201, 2.0)
    root = _NativeProcess(101, 1.25, descendants=(child, grandchild))
    processes = {member.pid: member for member in (root, child, grandchild, unrelated)}
    events = _native_view(monkeypatch, processes, {101: 101, 102: 101, 103: 101, 201: 201})
    tree = tree_module.OwnedProcessTree(_ProcessHandle())
    tree.root = tree_module.ProcessIdentity(101, 1.25)
    tree.known[101] = tree.root
    tree.group_id = 101

    assert {member.pid for member in tree.running_members()} == {101, 102, 103}
    assert root.children_calls == [True]
    del processes[101]
    assert {member.pid for member in tree.running_members()} == {102, 103}
    tree._signal(force=True)
    assert events == [(101, signal.SIGKILL)]
    assert child.signals == grandchild.signals == [signal.SIGKILL]
    assert unrelated.signals == []


def test_wait_empty_requires_kernel_confirmation_after_process_snapshot_is_empty(monkeypatch):
    handle = _ProcessHandle(exitcode=0)
    _native_view(monkeypatch, {})
    events = []
    probes = iter([None, ProcessLookupError(errno.ESRCH, "No such process")])

    def killpg(group_id, signal_number):
        assert (group_id, signal_number) == (101, 0)
        outcome = next(probes)
        events.append("group-alive" if outcome is None else "group-gone")
        if outcome is not None:
            raise outcome

    monkeypatch.setattr(tree_module.os, "killpg", killpg)
    monkeypatch.setattr(
        tree_module,
        "time",
        SimpleNamespace(
            monotonic=lambda: 100.0,
            sleep=lambda _duration: events.append("recheck"),
        ),
    )
    tree = tree_module.OwnedProcessTree(handle)
    tree.root = tree_module.ProcessIdentity(101, 1.25)
    tree.known[101] = tree.root
    tree.group_id = 101

    assert tree._wait_empty(101.0) is True
    assert events == ["group-alive", "recheck", "group-gone"]


@pytest.mark.asyncio
async def test_leaderless_reused_group_is_not_signalled_and_quarantines_its_lane(monkeypatch):
    handle = _ProcessHandle(exitcode=0)
    _native_view(monkeypatch, {})
    now = [100.0]
    group_calls = []

    def killpg(group_id, signal_number):
        group_calls.append((group_id, signal_number))

    def advance_clock(_duration):
        now[0] = 101.0

    monkeypatch.setattr(tree_module.os, "killpg", killpg)
    monkeypatch.setattr(
        tree_module,
        "time",
        SimpleNamespace(monotonic=lambda: now[0], sleep=advance_clock),
    )
    tree = tree_module.OwnedProcessTree(handle)
    tree.root = tree_module.ProcessIdentity(101, 1.25)
    tree.known[101] = tree.root
    tree.group_id = 101

    cleaned = tree.cleanup(100.03)

    assert cleaned is False
    assert group_calls
    assert all(call == (101, 0) for call in group_calls)
    assert tree.closed is False
    assert handle.closed is False
    assert handle.calls == []

    executor = ToolExecutor(_policy(workers=1), FixtureRegistry)
    executor._admit("leaderless-owner", 1)
    job = _owned_job()
    job.principal_key = "leaderless-owner"
    job.lane = executor._available.get_nowait()
    job.tree = tree
    executor._jobs[job.spec.execution_id] = job
    future = asyncio.get_running_loop().create_future()
    future.set_result(
        executor_module._Outcome(
            None,
            ToolError(code="cleanup_failed", retryable=False),
            ToolItemMetrics(),
            cleaned,
        )
    )
    job.io_task = future
    try:
        executor._job_finished(job, future)

        snapshot = executor.snapshot()
        assert job.quarantined is True
        assert (snapshot.pending, snapshot.active, snapshot.degraded_lanes, snapshot.available) == (1, 1, 1, False)
        assert executor._available.qsize() == 0
    finally:
        tree.group_id = None
        await executor.shutdown()

    assert executor.snapshot().pending == 0


@pytest.mark.parametrize("with_child", [False, True], ids=["root-only", "surviving-child"])
def test_root_exit_between_identity_check_and_child_scan_fails_closed_for_unknown_survivors(with_child, monkeypatch):
    handle = _ProcessHandle(exitcode=None)
    processes = {}

    class RemainingChild(_NativeProcess):
        def terminate(self):
            super().terminate()
            self.running = False

        def kill(self):
            super().kill()
            self.running = False

    class ExitingRoot(_NativeProcess):
        def children(self, recursive=False):
            assert recursive is True
            processes.pop(self.pid)
            handle.exitcode = 0
            raise psutil.NoSuchProcess(self.pid)

    root = ExitingRoot(101, 1.25)
    child = RemainingChild(102, 1.5)
    processes[root.pid] = root
    if with_child:
        processes[child.pid] = child
    events = _native_view(monkeypatch, processes, {101: 101, 102: 101})
    tree = tree_module.OwnedProcessTree(handle)
    tree.root = tree_module.ProcessIdentity(101, 1.25)
    tree.known[101] = tree.root
    tree.group_id = 101
    now = [100.0]

    def killpg(group_id, signal_number):
        if signal_number != 0:
            events.append((group_id, signal_number))
            return
        if any(process.running for process in processes.values()):
            return
        raise ProcessLookupError(errno.ESRCH, "No such process")

    monkeypatch.setattr(tree_module.os, "killpg", killpg)
    monkeypatch.setattr(tree_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(tree_module.time, "sleep", lambda _duration: now.__setitem__(0, 101.0))

    assert tree.cleanup(100.05) is (not with_child)
    assert tree.closed is (not with_child)
    assert handle.closed is (not with_child)
    assert root.signals == []
    if with_child:
        assert child.running is True
        assert child.signals == []
        assert handle.calls == []
    else:
        assert events == []


@pytest.mark.parametrize("confirmed_empty", [False, True], ids=["retain-handles", "close-after-proof"])
def test_cleanup_escalates_and_retains_handles_until_termination_is_observed(confirmed_empty, monkeypatch):
    handle = _ProcessHandle()
    tree = tree_module.OwnedProcessTree(handle)
    observations = iter([False, False, confirmed_empty])
    events = []
    monkeypatch.setattr(tree, "running_members", lambda: [])
    monkeypatch.setattr(tree, "_wait_empty", lambda deadline: next(observations))
    monkeypatch.setattr(tree, "_signal", lambda force: events.append(force))

    assert tree.cleanup(time.monotonic() + 5) is confirmed_empty
    assert events == [False, True]
    assert tree.closed is confirmed_empty
    assert handle.closed is confirmed_empty
    assert handle.calls == ([("join", 0), ("close",)] if confirmed_empty else [])


def test_cleanup_does_not_claim_success_when_native_inspection_is_denied(monkeypatch):
    handle = _ProcessHandle()
    tree = tree_module.OwnedProcessTree(handle)

    def denied():
        raise psutil.AccessDenied(101)

    monkeypatch.setattr(tree, "running_members", denied)
    assert tree.cleanup(time.monotonic() + 5) is False
    assert tree.closed is False
    assert handle.closed is False
    assert handle.calls == []
