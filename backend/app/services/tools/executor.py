"""Admission, absolute deadlines and owned lifecycles for independent Tool jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import os
import select
import struct
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from dataclasses import dataclass, field
from multiprocessing.connection import Connection

import structlog
from pydantic import ValidationError

from backend.app.logging_config import get_logger
from backend.app.schemas.tools import (
    ToolBatchMetrics,
    ToolComputeBatchRequest,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolComputeItem,
    ToolComputeProgress,
    ToolComputeResult,
    ToolComputeSuccess,
    ToolError,
    ToolErrorCode,
    ToolItemMetrics,
    ToolOperationPolicy,
    ToolPlatformPolicy,
    ToolPoolResourceReservation,
    ToolPoolSnapshot,
    ToolResourceCapabilities,
)
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.tools.base import ToolDefinitionError, ToolExecutionError
from backend.app.services.tools.catalog import effective_operation, operations_for
from backend.app.services.tools.cpus import cpu_count_usable
from backend.app.services.tools.process_tree import OwnedProcessTree
from backend.app.services.tools.registry import ToolPluginRegistry, ToolRegistrySnapshot
from backend.app.services.tools.resources import ToolResourceController
from backend.app.services.tools.wire import LOG_FRAME_MAX_BYTES, MAX_SAFE_JSON_INTEGER, PROGRESS_FRAME_MAX_BYTES, decode_json, encode_json, plain_json_object
from backend.app.services.tools.worker import CHILD_LOG_FRAME_CAP, PipeCancellation, ToolWorkerJob, execute_tool_job

logger = get_logger(__name__)

# A crashed worker's pipe closes a moment before the process can be reaped, longer under load: the most the parent waits
# to read its exit status. ``join`` returns as soon as the worker exits, so only a worker still alive waits it all.
_EXIT_GRACE_SECONDS = 0.5
#: The most progress messages one item hands to its listener (lot V1 of project 67); past it they are dropped.
TOOL_PROGRESS_MESSAGE_CAP = 50
_PROGRESS_KEYS = frozenset({"kind", "execution_id", "phase"})
_PROGRESS_OPTIONAL_KEYS = frozenset({"step", "total"})
#: The most worker log lines the parent writes for one job (lot LOGS of project 67): the child's cap and its count line.
TOOL_LOG_LINE_CAP = CHILD_LOG_FRAME_CAP + 1
_LOG_KEYS = frozenset({"kind", "execution_id", "level", "logger", "message"})
_LOG_LEVELS = frozenset({5, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL})
#: The keys of a child's rendered line that the parent's own processors write again, or that structlog reads as commands
#: (``positional_args`` would be formatted into the event). The keys the parent's context binds (``request_id``) are
#: dropped too, at each line: the child never overrides them.
_CHILD_LINE_OWN_KEYS = frozenset({"event", "level", "logger", "timestamp", "exc_info", "stack_info", "positional_args"})

#: What the executor calls with each accepted progress message, in the event loop of ``compute``.
type ToolProgressListener = Callable[[ToolComputeProgress], None]
#: The I/O owner's side of it: phase, step, total of an accepted frame.
type _ProgressForward = Callable[[str, int | None, int | None], None]


#: Where a ``worker_crashed`` was raised, as the crash line names it (GPAC-d follow-up of project 67): a crash that comes back
#: can be traced to its site without a traceback. A closed set: a new raising site adds its reason here.
CRASH_REASONS = (
    "exited_without_frame",  # the worker exited and nothing was left in the pipe
    "pipe_closed",  # the worker's end of the pipe closed (it exited, or closed it) before a whole frame
    "frame_length_invalid",  # a frame's declared length is negative
    "frame_of_another_job",  # a frame carries another job's execution id
    "ready_frame_invalid",  # the worker's first frame is not the ``ready`` frame it must be
    "result_frame_invalid",  # the result frame has the wrong shape
    "frame_out_of_order",  # a frame of a kind not expected at that point
    "start_failed",  # preparing or starting the worker raised ``EOFError``, ``OSError`` or ``ValueError``
    "pipe_error",  # after the start, reading the pipe or decoding a frame raised one of them (a pydantic error is a ``ValueError``)
)


def _crashed_exit_code(job: _OwnedJob) -> int | None:
    """The crashed worker's own exit status (J-19), read before the cleanup that may signal it: an exit code, or the
    negative number of the signal that ended it; None while it still runs, or when it cannot be read."""
    process = getattr(job.tree, "process", None)
    if process is None:
        return None
    try:
        process.join(timeout=_EXIT_GRACE_SECONDS)
        return process.exitcode
    except (OSError, ValueError, AssertionError):
        return None


def _log_worker_crash(job: _OwnedJob) -> None:
    """One structured line for a crashed worker (J-19): its identity, exit status, the site that saw the crash
    (``crash_reason``, one of ``CRASH_REASONS``, and ``crash_cause``, the exception's class when there is one), memory and
    time — never its input, its output or an exception's message."""
    memory = job.metrics.resources.memory if job.metrics.resources is not None else None
    logger.warning(
        "Tool worker crashed",
        execution_id=job.spec.execution_id,
        tool_code=job.spec.tool_code,
        exit_code=job.metrics.worker_exit_code,
        crash_reason=job.crash_reason,
        crash_cause=job.crash_cause,
        peak_observed_bytes=memory.peak_observed_bytes if memory is not None else None,
        memory_limit_bytes=memory.limit_bytes if memory is not None else None,
        memory_mode=memory.mode if memory is not None else None,
        execution_ms=job.metrics.execution_ms,
    )


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
    cleanup_timeout_ms: int = 2_000
    cancel: threading.Event = field(default_factory=threading.Event)
    tree: OwnedProcessTree | None = None
    io_task: asyncio.Task[_Outcome] | None = None
    quarantined: bool = False
    metrics: ToolItemMetrics = field(default_factory=ToolItemMetrics)
    progress_phases: tuple[str, ...] = ()
    on_progress: _ProgressForward | None = None
    progress_seen: set[tuple[str, int | None, int | None]] = field(default_factory=set)
    log_lines: int = 0
    #: Where a ``worker_crashed`` was raised, one of ``CRASH_REASONS``; None for every other outcome.
    crash_reason: str | None = None
    #: The class name of the exception a ``start_failed`` or ``pipe_error`` came from, never its message.
    crash_cause: str | None = None


@dataclass(slots=True)
class _ItemTicket:
    principal_key: str
    job: _OwnedJob | None = None


def _read_exact(connection: Connection, size: int, job: _OwnedJob) -> bytes:
    chunks = bytearray()
    descriptor = connection.fileno()
    while len(chunks) < size:
        if job.cancel.is_set():
            raise ToolExecutionError("execution_limit", retryable=True)
        if job.tree is not None:
            job.tree.observe_memory_limit()
        remaining = job.spec.hard_deadline - time.monotonic()
        if remaining <= 0:
            raise ToolExecutionError("execution_timeout", retryable=True)
        readable, _, _ = select.select([descriptor], [], [], min(0.05, remaining))
        if not readable:
            if job.tree is not None:
                job.tree.observe_memory_limit()
                # The worker may have written its last frames and exited after the empty poll (GPAC-d of project 67, a
                # busy machine): look at the pipe once more. This look is final, as an exited worker writes nothing more:
                # the exit is read first and the pipe second, an order that must not be swapped.
                if job.tree.process.exitcode is not None and not select.select([descriptor], [], [], 0)[0]:
                    raise ToolExecutionError("worker_crashed", reason="exited_without_frame")
            continue
        chunk = os.read(descriptor, size - len(chunks))
        if not chunk:
            if job.tree is not None:
                job.tree.observe_memory_limit()
            raise ToolExecutionError("worker_crashed", reason="pipe_closed")
        chunks.extend(chunk)
    return bytes(chunks)


def _read_frame(connection: Connection, job: _OwnedJob) -> dict[str, object]:
    length = struct.unpack("!i", _read_exact(connection, 4, job))[0]
    if length == -1:
        length = struct.unpack("!Q", _read_exact(connection, 8, job))[0]
    if length < 0:
        raise ToolExecutionError("worker_crashed", reason="frame_length_invalid")
    if length > job.spec.max_result_bytes + 65_536:
        raise ToolExecutionError("output_limit_exceeded")
    payload = _read_exact(connection, length, job)
    frame = plain_json_object(decode_json(payload, max_depth=job.spec.max_json_depth + 4))
    if time.monotonic() >= job.spec.hard_deadline:
        raise ToolExecutionError("execution_timeout", retryable=True)
    if frame.get("execution_id") != job.spec.execution_id:
        raise ToolExecutionError("worker_crashed", reason="frame_of_another_job")
    return dict(frame)


def _accept_ready(frame: dict[str, object], job: _OwnedJob) -> None:
    if set(frame) != {"kind", "execution_id", "pid", "pgid", "created_at"} or job.tree is None:
        raise ToolExecutionError("worker_crashed", reason="ready_frame_invalid")
    pid, group_id, created_at = frame["pid"], frame["pgid"], frame["created_at"]
    if type(pid) is not int or type(group_id) is not int or type(created_at) is not float:
        raise ToolExecutionError("worker_crashed", reason="ready_frame_invalid")
    job.tree.confirm_session(pid=pid, group_id=group_id, created_at=created_at)
    job.metrics = job.metrics.model_copy(update={"startup_ms": _milliseconds(job.granted_at)})


def _accept_result(frame: dict[str, object], job: _OwnedJob) -> tuple[object, ToolError | None]:
    success = frame.get("status") == "success"
    expected = {"kind", "execution_id", "status", "metrics", "result" if success else "error"}
    if set(frame) != expected or frame.get("status") not in ("success", "error"):
        raise ToolExecutionError("worker_crashed", reason="result_frame_invalid")
    child_metrics = ToolItemMetrics.model_validate(frame["metrics"])
    # The parent owns the worker's exit status (J-19): a value the worker sends is dropped.
    job.metrics = child_metrics.model_copy(update={"queue_wait_ms": job.metrics.queue_wait_ms, "startup_ms": job.metrics.startup_ms, "worker_exit_code": None})
    if success:
        encode_json(frame["result"], max_depth=job.spec.max_json_depth, max_bytes=job.spec.max_result_bytes, limit_code="output_limit_exceeded")
        return frame["result"], None
    return None, ToolError.model_validate(frame["error"])


def _progress_integer(value: object) -> bool:
    return value is None or (type(value) is int and 1 <= value <= MAX_SAFE_JSON_INTEGER)


def _accept_progress(frame: dict[str, object], job: _OwnedJob) -> None:
    """A child's progress frame after ``ready`` (lot V1 of project 67): forwarded when its phase is declared, its shape is
    exact, it is new and under the cap; otherwise dropped. A dropped frame is never a crash (contract §10)."""
    keys = set(frame)
    phase, step, total = frame.get("phase"), frame.get("step"), frame.get("total")
    if not _PROGRESS_KEYS <= keys <= _PROGRESS_KEYS | _PROGRESS_OPTIONAL_KEYS or phase not in job.progress_phases:
        return
    if not _progress_integer(step) or not _progress_integer(total) or (total is not None and (step is None or step > total)):
        return
    if len(encode_json(frame, max_depth=1)) > PROGRESS_FRAME_MAX_BYTES:
        return
    key = (phase, step, total)
    if key in job.progress_seen or len(job.progress_seen) >= TOOL_PROGRESS_MESSAGE_CAP:
        return
    job.progress_seen.add(key)
    if job.on_progress is not None:
        job.on_progress(phase, step, total)


def _accept_log(frame: dict[str, object], job: _OwnedJob) -> None:
    """A child's log line after ``ready`` (lot LOGS of project 67): written to the server's log as one of its own lines, at
    the child's level, with ``worker`` and the job's ``execution_id`` (the request's id comes from this thread's context).
    A structured line keeps its fields; a library's plain line is its text. A malformed frame, or one past the cap, is
    dropped, never a crash."""
    level, name, message = frame.get("level"), frame.get("logger"), frame.get("message")
    if set(frame) != _LOG_KEYS or type(level) is not int or level not in _LOG_LEVELS:
        return
    if not isinstance(name, str) or not 0 < len(name) <= 200 or not isinstance(message, str) or len(message) > LOG_FRAME_MAX_BYTES:
        return
    if job.log_lines >= TOOL_LOG_LINE_CAP:
        return
    job.log_lines += 1
    event, fields = message, {}
    try:
        rendered = json.loads(message)
    except ValueError:  # a parsing probe: a library's plain line is not JSON, and is written as text
        rendered = None
    if isinstance(rendered, dict) and isinstance(rendered.get("event"), str):
        event = rendered["event"]
        bound = structlog.contextvars.get_contextvars()
        fields = {key: value for key, value in rendered.items() if key not in _CHILD_LINE_OWN_KEYS and key not in bound}
        if isinstance(rendered.get("timestamp"), str):
            fields["worker_at"] = rendered["timestamp"]
    get_logger(name).log(level, event, **{**fields, "worker": "tool", "worker_logger": name, "execution_id": job.spec.execution_id})


def _wait_result(response: Connection, cancellation: Connection, job: _OwnedJob) -> tuple[object, ToolError | None]:
    ready = False
    while True:
        if job.cancel.is_set():
            raise ToolExecutionError("execution_limit", retryable=True)
        remaining = job.spec.hard_deadline - time.monotonic()
        if remaining <= 0:
            raise ToolExecutionError("execution_timeout", retryable=True)
        frame = _read_frame(response, job)
        if frame.get("kind") == "ready" and not ready:
            _accept_ready(frame, job)
            ready = True
            cancellation.send_bytes(b"\x00")
        elif frame.get("kind") == "result" and ready:
            result = _accept_result(frame, job)
            if time.monotonic() >= job.spec.hard_deadline:
                raise ToolExecutionError("execution_timeout", retryable=True)
            return result
        elif frame.get("kind") == "progress" and ready:
            _accept_progress(frame, job)
        elif frame.get("kind") == "log" and ready:
            _accept_log(frame, job)
        else:
            raise ToolExecutionError("worker_crashed", reason="frame_out_of_order")


def _finish_physical_job(job: _OwnedJob, cancellation: Connection | None, cleanup_ms: int) -> bool:
    if cancellation is not None:
        try:
            cancellation.send_bytes(b"\x01")
        except (BrokenPipeError, EOFError, OSError):
            pass
    started = time.monotonic()
    cleaned = job.tree is not None and job.tree.cleanup(started + cleanup_ms / 1000)
    resources = job.tree.resource_metrics() if job.tree is not None else None
    job.metrics = job.metrics.model_copy(update={"cleanup_ms": _milliseconds(started), "total_ms": _milliseconds(job.admitted_at), "resources": resources})
    return cleaned


def _run_owned_job(
    job: _OwnedJob,
    registry_class: type[ToolPluginRegistry],
    cleanup_ms: int | None = None,
    resource_controller: ToolResourceController | None = None,
) -> _Outcome:
    """The sole I/O owner starts, reads, signals and closes this physical job."""
    value: object = None
    error: ToolError | None = None
    cancellation: Connection | None = None
    started = False
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
            job.tree = OwnedProcessTree(
                process,
                memory_limit_bytes=job.spec.memory_limit_bytes,
                resource_controller=resource_controller,
            )
            job.tree.prepare_resources(job.spec.execution_id)
            process.start()
            child_response.close()
            child_cancel.close()
            job.tree.bind_started_process()
            started = True
            value, error = _wait_result(response, cancellation, job)
        except ToolExecutionError as exc:
            error = _error(exc.code, retryable=exc.retryable)
            job.crash_reason = exc.reason if exc.code == "worker_crashed" else None
        except (EOFError, OSError, ValueError) as exc:
            error = _error("worker_crashed")
            job.crash_reason = "pipe_error" if started else "start_failed"
            job.crash_cause = type(exc).__name__
        except Exception:
            error = _error("execution_failed")
        finally:
            job.metrics = job.metrics.model_copy(update={"execution_ms": _milliseconds(job.granted_at)})
            if job.tree is not None:
                if error is not None and error.code == "worker_crashed":
                    job.metrics = job.metrics.model_copy(update={"worker_exit_code": _crashed_exit_code(job)})
                cleaned = _finish_physical_job(job, cancellation, job.cleanup_timeout_ms if cleanup_ms is None else cleanup_ms)
            else:
                cleaned = job.tree is None
                job.metrics = job.metrics.model_copy(update={"total_ms": _milliseconds(job.admitted_at)})
    if not cleaned:
        error = _error("cleanup_failed")
        value = None
    elif job.tree is not None and job.tree.memory_limit_exceeded:
        error = _error("memory_limit")
        value = None
    if error is not None and error.code == "worker_crashed":
        _log_worker_crash(job)
    return _Outcome(value, error, job.metrics, cleaned)


def _progress_forward(correlation_id: str, admitted_at: float, listener: ToolProgressListener) -> _ProgressForward:
    """The I/O owner's thread hands an accepted message to the listener in the event loop; the loop also receives the
    item's outcome after it, so every message arrives before its result. A listener's failure never reaches the job."""
    loop = asyncio.get_running_loop()

    def deliver(event: ToolComputeProgress) -> None:
        try:
            listener(event)
        except Exception as exc:  # isolation boundary: a progress listener never fails the calculation
            logger.warning("Tool progress listener failed", correlation_id=correlation_id, phase=event.phase, exc_info=exc)

    def forward(phase: str, step: int | None, total: int | None) -> None:
        event = ToolComputeProgress(kind="progress", correlation_id=correlation_id, phase=phase, step=step, total=total, elapsed_ms=_milliseconds(admitted_at))
        try:
            loop.call_soon_threadsafe(deliver, event)
        except RuntimeError:
            pass  # the loop is closing: nobody is listening any more

    return forward


class ToolExecutor:
    """Per-API-process quotas; no I/O or workers are started by construction."""

    def __init__(
        self,
        policy: ToolPlatformPolicy | None = None,
        registry_class: type[ToolPluginRegistry] = ToolPluginRegistry,
        resource_controller: ToolResourceController | None = None,
        usable_cpus: int | None = None,
    ):
        self.policy = policy or ToolPlatformPolicy()
        #: The machine's usable CPUs, counted by ``get_tool_executor`` (TURNI of project 67): it picks each Tool's row of limits
        #: (``catalog.operations_for``). None, as a test builds it: no CPU table applies.
        self.usable_cpus = usable_cpus
        self.registry_class = registry_class
        self.resource_controller = resource_controller or ToolResourceController()
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
            memory_reserved_bytes = sum(job.spec.memory_limit_bytes for job in self._jobs.values())
            return ToolPoolSnapshot(
                available=not self._closed and os.name == "posix" and degraded < self.policy.workers,
                active=len(self._jobs),
                queued=self._queued,
                pending=self._pending,
                degraded_lanes=degraded,
                completed=self._completed,
                failed=self._failed,
                resources=ToolPoolResourceReservation(
                    memory_capacity_bytes=self.policy.workers * self.policy.memory_limit_bytes,
                    memory_reserved_bytes=memory_reserved_bytes,
                ),
            )

    def resource_capabilities(self) -> ToolResourceCapabilities:
        return ToolResourceCapabilities(memory=self.resource_controller.memory_capability())

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
        selected = next((candidate for candidate in operations_for(definition, self.usable_cpus) if candidate.operation == operation), None)
        if selected is None:
            raise ToolExecutionError("invalid_parameters")
        try:
            return effective_operation(selected, self.policy)
        except ToolDefinitionError as exc:
            raise ToolExecutionError("tool_unavailable") from exc

    def batch_request_timeout_ms(self, batch: ToolComputeBatchRequest, snapshot: ToolRegistrySnapshot | None = None) -> int:
        """Return the largest valid item budget; item execution budgets stay independent."""
        snapshot = snapshot or self.registry_class.get_snapshot()
        timeouts: list[int] = []
        for item in batch.items:
            try:
                timeouts.append(self._operation(item, snapshot).request_timeout_ms)
            except ToolExecutionError:
                continue
        return max(timeouts, default=min(20_000, self.policy.request_timeout_ms))

    async def _await_job(self, job: _OwnedJob) -> _Outcome:
        if job.io_task is None:
            raise RuntimeError("Tool I/O owner is missing")
        remaining = job.spec.hard_deadline + job.cleanup_timeout_ms / 1000 - time.monotonic()
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
                await asyncio.wait_for(asyncio.shield(job.io_task), timeout=job.cleanup_timeout_ms / 1000)
            except TimeoutError:
                with self._lock:
                    job.quarantined = True
            raise

    async def _run_item(
        self,
        item: ToolComputeItem,
        snapshot: ToolRegistrySnapshot,
        ticket: _ItemTicket,
        admitted_at: float,
        request_deadline: float,
        bound: BoundSettings | None = None,
        on_progress: ToolProgressListener | None = None,
    ) -> ToolComputeResult:
        job: _OwnedJob | None = None
        lane: int | None = None
        queued = False
        try:
            operation = self._operation(item, snapshot)
            if bound is not None and bound.missing:
                # A required field of the tool has no value: nothing is started for it (the other items of the batch run).
                raise ToolExecutionError("service_unavailable")
            try:
                parameters = encode_json(item.parameters, max_depth=self.policy.max_json_depth, max_bytes=operation.max_parameter_bytes)
            except ValueError as exc:
                raise ToolExecutionError("invalid_parameters") from exc
            with self._lock:
                self._queued += 1
                queued = True
            queue_deadline = min(admitted_at + operation.queue_timeout_ms / 1000, request_deadline - (operation.cleanup_timeout_ms + self.policy.response_reserve_ms) / 1000)
            lane = await asyncio.wait_for(self._available.get(), timeout=max(0, queue_deadline - time.monotonic()))
            with self._lock:
                self._queued -= 1
                queued = False
            if time.monotonic() >= queue_deadline:
                raise ToolExecutionError("queue_timeout", retryable=True)
            job = self._start_job(item, operation, parameters, ticket.principal_key, lane, admitted_at, request_deadline, bound, on_progress)
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
        bound: BoundSettings | None = None,
        on_progress: ToolProgressListener | None = None,
    ) -> _OwnedJob:
        with self._lock:
            if self._closed:
                raise ToolExecutionError("service_unavailable", retryable=True)
        granted_at = time.monotonic()
        hard_deadline = min(granted_at + operation.job_timeout_ms / 1000, request_deadline - (operation.cleanup_timeout_ms + self.policy.response_reserve_ms) / 1000)
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
            engine_timeout_ms=operation.engine_timeout_ms,
            memory_limit_bytes=operation.memory_limit_bytes,
            settings=bound,
            log_level=logging.getLogger().getEffectiveLevel(),
        )
        job = _OwnedJob(
            spec,
            principal_key,
            lane,
            admitted_at,
            granted_at,
            operation.cleanup_timeout_ms,
            metrics=ToolItemMetrics(queue_wait_ms=_milliseconds(admitted_at)),
            progress_phases=operation.progress_phases,
            on_progress=_progress_forward(item.correlation_id, admitted_at, on_progress) if on_progress is not None else None,
        )
        with self._lock:
            self._jobs[spec.execution_id] = job
        job.io_task = asyncio.create_task(asyncio.to_thread(_run_owned_job, job, self.registry_class, None, self.resource_controller))
        job.io_task.add_done_callback(lambda task: self._job_finished(job, task))
        return job

    async def compute(
        self,
        batch: ToolComputeBatchRequest,
        *,
        principal_key: str,
        request_started: float | None = None,
        settings: Mapping[str, BoundSettings] | None = None,
        on_progress: ToolProgressListener | None = None,
    ) -> ToolComputeBatchResponse:
        """Run every item; ``on_progress`` receives, in this event loop, the accepted progress messages of every item,
        each before its item's result."""
        started = time.monotonic() if request_started is None else request_started
        snapshot = await asyncio.to_thread(self.registry_class.get_snapshot)
        admitted_at = self._admit(principal_key, len(batch.items))
        deadline = started + self.batch_request_timeout_ms(batch, snapshot) / 1000
        tasks: list[asyncio.Task[ToolComputeResult]] = []
        for item in batch.items:
            ticket = _ItemTicket(principal_key)
            task = asyncio.create_task(self._run_item(item, snapshot, ticket, admitted_at, deadline, settings.get(item.tool_code) if settings else None, on_progress))
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
        with self._lock:
            self._closed = True
            jobs = tuple(self._jobs.values())
            items = tuple(self._items)
        cleanup_timeout_ms = max((job.cleanup_timeout_ms for job in jobs), default=min(2_000, self.policy.cleanup_timeout_ms))
        deadline = time.monotonic() + cleanup_timeout_ms / 1000
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
            # Once per API process: the CPUs pick each Tool's row of limits (TURNI of project 67). The line is the signal for
            # a server that counts more CPUs than its calculations then see.
            usable_cpus = cpu_count_usable()
            _executor = ToolExecutor(usable_cpus=usable_cpus)
            logger.info("Tool executor built", usable_cpus=usable_cpus)
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
