"""Admission, absolute deadlines and owned lifecycles for independent Tool jobs."""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import threading
import time
import uuid
from contextlib import ExitStack
from dataclasses import dataclass, field
from multiprocessing.connection import Connection

from pydantic import ValidationError

from backend.app.schemas.tools import (
    ToolBatchMetrics,
    ToolComputeBatchRequest,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolComputeItem,
    ToolComputeResult,
    ToolComputeSuccess,
    ToolError,
    ToolErrorCode,
    ToolItemMetrics,
    ToolOperationPolicy,
    ToolPlatformPolicy,
    ToolPoolSnapshot,
)
from backend.app.services.tools.base import ToolDefinitionError, ToolExecutionError
from backend.app.services.tools.catalog import effective_operation
from backend.app.services.tools.process_tree import OwnedProcessTree
from backend.app.services.tools.registry import ToolPluginRegistry, ToolRegistrySnapshot
from backend.app.services.tools.wire import decode_json, encode_json, plain_json_object
from backend.app.services.tools.worker import PipeCancellation, ToolWorkerJob, execute_tool_job


def _milliseconds(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _error(code: ToolErrorCode, *, retryable: bool = False) -> ToolError:
    return ToolError(code=code, retryable=retryable)


def _identity(item: ToolComputeItem, execution_id: str | None, metrics: ToolItemMetrics) -> dict[str, object]:
    return {
        "correlation_id": item.correlation_id,
        "tool_code": item.tool_code,
        "contract_version": item.contract_version,
        "implementation_version": item.implementation_version,
        "schema_fingerprint": item.schema_fingerprint,
        "execution_id": execution_id,
        "metrics": metrics,
    }


@dataclass(frozen=True, slots=True)
class _Outcome:
    value: object
    error: ToolError | None
    metrics: ToolItemMetrics
    cleaned: bool


@dataclass(slots=True)
class _OwnedJob:
    spec: ToolWorkerJob
    principal_key: str
    lane: int
    admitted_at: float
    granted_at: float
    cancel: threading.Event = field(default_factory=threading.Event)
    tree: OwnedProcessTree | None = None
    io_task: asyncio.Task[_Outcome] | None = None
    quarantined: bool = False
    metrics: ToolItemMetrics = field(default_factory=ToolItemMetrics)


@dataclass(slots=True)
class _ItemTicket:
    principal_key: str
    job: _OwnedJob | None = None


def _read_frame(connection: Connection, job: _OwnedJob) -> dict[str, object]:
    payload = connection.recv_bytes(job.spec.max_result_bytes + 65_536)
    frame = plain_json_object(decode_json(payload, max_depth=job.spec.max_json_depth + 4))
    if frame.get("execution_id") != job.spec.execution_id:
        raise ToolExecutionError("worker_crashed")
    return dict(frame)


def _accept_ready(frame: dict[str, object], job: _OwnedJob) -> None:
    if set(frame) != {"kind", "execution_id", "pid", "pgid", "created_at"} or job.tree is None:
        raise ToolExecutionError("worker_crashed")
    pid, group_id, created_at = frame["pid"], frame["pgid"], frame["created_at"]
    if type(pid) is not int or type(group_id) is not int or type(created_at) is not float:
        raise ToolExecutionError("worker_crashed")
    job.tree.confirm_session(pid=pid, group_id=group_id, created_at=created_at)
    job.metrics = job.metrics.model_copy(update={"startup_ms": _milliseconds(job.granted_at)})


def _accept_result(frame: dict[str, object], job: _OwnedJob) -> tuple[object, ToolError | None]:
    success = frame.get("status") == "success"
    expected = {"kind", "execution_id", "status", "metrics", "result" if success else "error"}
    if set(frame) != expected or frame.get("status") not in ("success", "error"):
        raise ToolExecutionError("worker_crashed")
    child_metrics = ToolItemMetrics.model_validate(frame["metrics"])
    job.metrics = child_metrics.model_copy(update={"queue_wait_ms": job.metrics.queue_wait_ms, "startup_ms": job.metrics.startup_ms})
    if success:
        encode_json(frame["result"], max_depth=job.spec.max_json_depth, max_bytes=job.spec.max_result_bytes, limit_code="output_limit_exceeded")
        return frame["result"], None
    return None, ToolError.model_validate(frame["error"])


def _wait_result(response: Connection, cancellation: Connection, job: _OwnedJob) -> tuple[object, ToolError | None]:
    ready = False
    while True:
        if job.cancel.is_set():
            raise ToolExecutionError("execution_limit", retryable=True)
        remaining = job.spec.hard_deadline - time.monotonic()
        if remaining <= 0:
            raise ToolExecutionError("execution_timeout", retryable=True)
        if not response.poll(min(0.05, remaining)):
            if job.tree is not None and job.tree.process.exitcode is not None:
                raise ToolExecutionError("worker_crashed")
            continue
        frame = _read_frame(response, job)
        if frame.get("kind") == "ready" and not ready:
            _accept_ready(frame, job)
            ready = True
            cancellation.send_bytes(b"\x00")
        elif frame.get("kind") == "result" and ready:
            return _accept_result(frame, job)
        else:
            raise ToolExecutionError("worker_crashed")


def _finish_physical_job(job: _OwnedJob, cancellation: Connection, cleanup_ms: int) -> bool:
    try:
        cancellation.send_bytes(b"\x01")
    except (BrokenPipeError, EOFError, OSError):
        pass
    started = time.monotonic()
    cleaned = job.tree is not None and job.tree.cleanup(started + cleanup_ms / 1000)
    job.metrics = job.metrics.model_copy(update={"cleanup_ms": _milliseconds(started), "total_ms": _milliseconds(job.admitted_at)})
    return cleaned


def _run_owned_job(job: _OwnedJob, registry_class: type[ToolPluginRegistry], cleanup_ms: int) -> _Outcome:
    """The sole I/O owner starts, reads, signals and closes this physical job."""
    value: object = None
    error: ToolError | None = None
    cancellation: Connection | None = None
    with ExitStack() as resources:
        try:
            context = multiprocessing.get_context("spawn")
            response, child_response = context.Pipe(duplex=False)
            resources.callback(response.close)
            resources.callback(child_response.close)
            child_cancel, cancellation = context.Pipe(duplex=False)
            resources.callback(child_cancel.close)
            resources.callback(cancellation.close)
            process = context.Process(
                target=execute_tool_job,
                args=(job.spec, child_response, PipeCancellation(child_cancel), registry_class),
                name=f"tool-{job.spec.execution_id}",
                daemon=False,
            )
            job.tree = OwnedProcessTree(process)
            process.start()
            child_response.close()
            child_cancel.close()
            job.tree.bind_started_process()
            value, error = _wait_result(response, cancellation, job)
        except ToolExecutionError as exc:
            error = _error(exc.code, retryable=exc.retryable)
        except (EOFError, OSError, ValueError):
            error = _error("worker_crashed")
        except Exception:
            error = _error("execution_failed")
        finally:
            job.metrics = job.metrics.model_copy(update={"execution_ms": _milliseconds(job.granted_at)})
            if cancellation is not None and job.tree is not None:
                cleaned = _finish_physical_job(job, cancellation, cleanup_ms)
            else:
                cleaned = job.tree is None
                job.metrics = job.metrics.model_copy(update={"total_ms": _milliseconds(job.admitted_at)})
    if not cleaned:
        error = _error("cleanup_failed")
        value = None
    return _Outcome(value, error, job.metrics, cleaned)


class ToolExecutor:
    """Per-API-process quotas; no I/O or workers are started by construction."""

    def __init__(self, policy: ToolPlatformPolicy | None = None, registry_class: type[ToolPluginRegistry] = ToolPluginRegistry):
        self.policy = policy or ToolPlatformPolicy()
        self.registry_class = registry_class
        self.runtime_id = uuid.uuid4().hex
        self._lock = threading.RLock()
        self._available: asyncio.Queue[int] = asyncio.Queue()
        for lane in range(self.policy.workers):
            self._available.put_nowait(lane)
        self._jobs: dict[str, _OwnedJob] = {}
        self._items: dict[asyncio.Task[ToolComputeResult], _ItemTicket] = {}
        self._batches: set[str] = set()
        self._principals: dict[str, int] = {}
        self._pending = 0
        self._queued = 0
        self._completed = 0
        self._failed = 0
        self._closed = False

    def snapshot(self) -> ToolPoolSnapshot:
        with self._lock:
            degraded = sum(job.quarantined for job in self._jobs.values())
            return ToolPoolSnapshot(
                available=not self._closed and os.name == "posix" and degraded < self.policy.workers,
                active=len(self._jobs),
                queued=self._queued,
                pending=self._pending,
                degraded_lanes=degraded,
                completed=self._completed,
                failed=self._failed,
            )

    def _admit(self, principal_key: str, count: int) -> float:
        with self._lock:
            if self._closed or os.name != "posix" or all(job.quarantined for job in self._jobs.values()) and len(self._jobs) >= self.policy.workers:
                raise ToolExecutionError("service_unavailable", retryable=True)
            if not principal_key or principal_key in self._batches or count > self.policy.max_batch_items or self._pending + count > self.policy.max_pending_items or self._principals.get(principal_key, 0) + count > self.policy.max_pending_per_principal:
                raise ToolExecutionError("queue_full", retryable=True)
            self._batches.add(principal_key)
            self._principals[principal_key] = self._principals.get(principal_key, 0) + count
            self._pending += count
            return time.monotonic()

    def _release_credit(self, principal_key: str) -> None:
        self._pending -= 1
        remaining = self._principals[principal_key] - 1
        if remaining:
            self._principals[principal_key] = remaining
        else:
            del self._principals[principal_key]

    def _job_finished(self, job: _OwnedJob, task: asyncio.Task[_Outcome]) -> None:
        with self._lock:
            if task.cancelled() or task.exception() is not None or not task.result().cleaned:
                job.quarantined = True
                return
            self._jobs.pop(job.spec.execution_id)
            self._release_credit(job.principal_key)
            self._available.put_nowait(job.lane)

    def _item_finished(self, task: asyncio.Task[ToolComputeResult]) -> None:
        with self._lock:
            ticket = self._items.pop(task)
            if ticket.job is None:
                self._release_credit(ticket.principal_key)
            succeeded = not task.cancelled() and task.exception() is None and task.result().status == "success"
            self._completed += 1
            self._failed += not succeeded

    def _operation(self, item: ToolComputeItem, snapshot: ToolRegistrySnapshot) -> ToolOperationPolicy:
        definition = snapshot.definitions.get(item.tool_code)
        if definition is None:
            unavailable = any(failure.tool_code == item.tool_code for failure in snapshot.failures)
            raise ToolExecutionError("tool_unavailable" if unavailable else "unknown_tool")
        descriptor = definition.descriptor
        if (item.contract_version, item.implementation_version, item.schema_fingerprint) != (descriptor.contract_version, descriptor.implementation_version, descriptor.schema_fingerprint):
            raise ToolExecutionError("version_mismatch", retryable=True)
        operation = item.parameters.get("operation") if isinstance(item.parameters, dict) else None
        selected = next((candidate for candidate in descriptor.operations if candidate.operation == operation), None)
        if selected is None:
            raise ToolExecutionError("invalid_parameters")
        try:
            return effective_operation(selected, self.policy)
        except ToolDefinitionError as exc:
            raise ToolExecutionError("tool_unavailable") from exc

    async def _await_job(self, job: _OwnedJob) -> _Outcome:
        if job.io_task is None:
            raise RuntimeError("Tool I/O owner is missing")
        remaining = job.spec.hard_deadline + self.policy.cleanup_timeout_ms / 1000 - time.monotonic()
        try:
            return await asyncio.wait_for(asyncio.shield(job.io_task), timeout=max(0, remaining))
        except TimeoutError:
            job.cancel.set()
            with self._lock:
                job.quarantined = True
            metrics = job.metrics.model_copy(update={"total_ms": _milliseconds(job.admitted_at)})
            return _Outcome(None, _error("cleanup_failed"), metrics, False)
        except asyncio.CancelledError:
            job.cancel.set()
            try:
                await asyncio.wait_for(asyncio.shield(job.io_task), timeout=self.policy.cleanup_timeout_ms / 1000)
            except TimeoutError:
                with self._lock:
                    job.quarantined = True
            raise

    async def _run_item(self, item: ToolComputeItem, snapshot: ToolRegistrySnapshot, ticket: _ItemTicket, admitted_at: float, request_deadline: float) -> ToolComputeResult:
        job: _OwnedJob | None = None
        lane: int | None = None
        queued = False
        try:
            operation = self._operation(item, snapshot)
            try:
                parameters = encode_json(item.parameters, max_depth=self.policy.max_json_depth, max_bytes=operation.max_parameter_bytes)
            except ValueError as exc:
                raise ToolExecutionError("invalid_parameters") from exc
            with self._lock:
                self._queued += 1
                queued = True
            queue_deadline = min(admitted_at + operation.queue_timeout_ms / 1000, request_deadline - (self.policy.cleanup_timeout_ms + self.policy.response_reserve_ms) / 1000)
            lane = await asyncio.wait_for(self._available.get(), timeout=max(0, queue_deadline - time.monotonic()))
            with self._lock:
                self._queued -= 1
                queued = False
            if time.monotonic() >= queue_deadline:
                raise ToolExecutionError("queue_timeout", retryable=True)
            job = self._start_job(item, operation, parameters, ticket.principal_key, lane, admitted_at, request_deadline)
            ticket.job = job
            outcome = await self._await_job(job)
            identity = _identity(item, job.spec.execution_id, outcome.metrics)
            if outcome.error is not None:
                return ToolComputeFailure(status="error", error=outcome.error, **identity)
            return ToolComputeSuccess(status="success", result=outcome.value, **identity)
        except TimeoutError:
            metrics = ToolItemMetrics(queue_wait_ms=_milliseconds(admitted_at), total_ms=_milliseconds(admitted_at))
            return ToolComputeFailure(status="error", error=_error("queue_timeout", retryable=True), **_identity(item, None, metrics))
        except ToolExecutionError as exc:
            metrics = ToolItemMetrics(total_ms=_milliseconds(admitted_at))
            return ToolComputeFailure(status="error", error=_error(exc.code, retryable=exc.retryable), **_identity(item, None, metrics))
        except ValidationError:
            metrics = job.metrics if job is not None else ToolItemMetrics(total_ms=_milliseconds(admitted_at))
            return ToolComputeFailure(status="error", error=_error("invalid_output"), **_identity(item, job.spec.execution_id if job is not None else None, metrics))
        finally:
            with self._lock:
                if queued:
                    self._queued -= 1
                if job is None and lane is not None:
                    self._available.put_nowait(lane)

    def _start_job(
        self,
        item: ToolComputeItem,
        operation: ToolOperationPolicy,
        parameters: bytes,
        principal_key: str,
        lane: int,
        admitted_at: float,
        request_deadline: float,
    ) -> _OwnedJob:
        with self._lock:
            if self._closed:
                raise ToolExecutionError("service_unavailable", retryable=True)
        granted_at = time.monotonic()
        hard_deadline = min(granted_at + operation.job_timeout_ms / 1000, request_deadline - (self.policy.cleanup_timeout_ms + self.policy.response_reserve_ms) / 1000)
        soft_deadline = min(granted_at + operation.soft_timeout_ms / 1000, hard_deadline - self.policy.output_reserve_ms / 1000)
        if soft_deadline <= granted_at:
            raise ToolExecutionError("queue_timeout", retryable=True)
        spec = ToolWorkerJob(
            execution_id=uuid.uuid4().hex,
            tool_code=item.tool_code,
            contract_version=item.contract_version,
            implementation_version=item.implementation_version,
            schema_fingerprint=item.schema_fingerprint,
            parameters=parameters,
            soft_deadline=soft_deadline,
            hard_deadline=hard_deadline,
            max_parameter_bytes=operation.max_parameter_bytes,
            max_result_bytes=operation.max_result_bytes,
            max_json_depth=self.policy.max_json_depth,
        )
        job = _OwnedJob(spec, principal_key, lane, admitted_at, granted_at, metrics=ToolItemMetrics(queue_wait_ms=_milliseconds(admitted_at)))
        with self._lock:
            self._jobs[spec.execution_id] = job
        job.io_task = asyncio.create_task(asyncio.to_thread(_run_owned_job, job, self.registry_class, self.policy.cleanup_timeout_ms))
        job.io_task.add_done_callback(lambda task: self._job_finished(job, task))
        return job

    async def compute(self, batch: ToolComputeBatchRequest, *, principal_key: str, request_started: float | None = None) -> ToolComputeBatchResponse:
        started = time.monotonic() if request_started is None else request_started
        snapshot = await asyncio.to_thread(self.registry_class.get_snapshot)
        admitted_at = self._admit(principal_key, len(batch.items))
        deadline = started + self.policy.request_timeout_ms / 1000
        tasks: list[asyncio.Task[ToolComputeResult]] = []
        for item in batch.items:
            ticket = _ItemTicket(principal_key)
            task = asyncio.create_task(self._run_item(item, snapshot, ticket, admitted_at, deadline))
            with self._lock:
                self._items[task] = ticket
            task.add_done_callback(self._item_finished)
            tasks.append(task)
        try:
            results = await asyncio.gather(*tasks)
            return ToolComputeBatchResponse(request_id=batch.request_id, results=results, metrics=ToolBatchMetrics(server_processing_ms=_milliseconds(started)))
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            with self._lock:
                self._batches.discard(principal_key)

    async def shutdown(self) -> None:
        deadline = time.monotonic() + self.policy.cleanup_timeout_ms / 1000
        with self._lock:
            self._closed = True
            jobs = tuple(self._jobs.values())
            items = tuple(self._items)
        for task in items:
            task.cancel()
        for job in jobs:
            job.cancel.set()
        pending = set(items) | {job.io_task for job in jobs if job.io_task is not None and not job.io_task.done()}
        if pending:
            await asyncio.wait(pending, timeout=max(0, deadline - time.monotonic()))
        for job in jobs:
            if job.io_task is not None and job.io_task.done() and job.tree is not None and not job.tree.closed and time.monotonic() < deadline:
                cleaned = await asyncio.to_thread(job.tree.cleanup, deadline)
                if cleaned:
                    with self._lock:
                        if self._jobs.pop(job.spec.execution_id, None) is not None:
                            self._release_credit(job.principal_key)
            elif job.io_task is not None and not job.io_task.done():
                with self._lock:
                    job.quarantined = True


_executor: ToolExecutor | None = None
_executor_lock = threading.Lock()


def get_tool_executor() -> ToolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ToolExecutor()
        return _executor


async def shutdown_tool_executor() -> None:
    global _executor
    with _executor_lock:
        current = _executor
    if current is None:
        return
    await current.shutdown()
    if current.snapshot().pending == 0:
        with _executor_lock:
            if _executor is current:
                _executor = None
