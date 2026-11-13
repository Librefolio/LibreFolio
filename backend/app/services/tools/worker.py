"""Child-side validation and execution; the supervisor owns process-tree cleanup."""

from __future__ import annotations

import multiprocessing
import os
import threading
import time
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Protocol

import psutil
from pydantic import BaseModel, ValidationError

from backend.app.schemas.tools import ToolError, ToolErrorCode, ToolItemMetrics
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.tools.base import ToolExecutionContext, ToolExecutionError
from backend.app.services.tools.registry import ToolDefinition, ToolPluginRegistry
from backend.app.services.tools.wire import PROGRESS_FRAME_MAX_BYTES, decode_json, encode_json, encode_progress_frame, plain_json_object, validation_error


class CancellationSignal(Protocol):
    def is_set(self) -> bool: ...


@dataclass(slots=True)
class PipeCancellation:
    connection: Connection
    stopped: bool = False

    def await_start(self, deadline: float) -> bool:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self.connection.poll(remaining):
            self.stopped = True
            return False
        try:
            self.stopped = self.connection.recv_bytes(1) != b"\x00"
        except (EOFError, OSError):
            self.stopped = True
        return not self.stopped

    def is_set(self) -> bool:
        if not self.stopped:
            try:
                if self.connection.poll(0):
                    self.connection.recv_bytes(1)
                    self.stopped = True
            except (EOFError, OSError):
                self.stopped = True
        return self.stopped


#: The most progress frames a child writes: well above the parent's cap of forwarded messages, and so few small frames that
#: the pipe never fills, so the child never waits for its parent to report progress.
CHILD_PROGRESS_FRAME_CAP = 64


class PipeProgressReporter:
    """The child's progress channel (lot V1 of project 67): small frames on the response pipe, between ``ready`` and the
    result. It never blocks for long, never raises: a malformed call is dropped, past its cap it stops, a broken pipe is
    swallowed, and once closed (compute returned) it sends nothing, so a stray thread cannot split the result frame. The
    parent checks every frame again: declared phase, shape, duplicates, its own cap."""

    def __init__(self, connection: Connection, execution_id: str) -> None:
        self._connection = connection
        self._execution_id = execution_id
        self._lock = threading.Lock()
        self._sent = 0
        self._closed = False

    def report(self, phase: str, step: int | None = None, total: int | None = None) -> None:
        if not isinstance(phase, str) or not all(value is None or (type(value) is int and value >= 0) for value in (step, total)):
            return
        try:
            frame = encode_progress_frame(self._execution_id, phase, step, total)
        except ValueError:
            return
        self._send(frame)

    def send_frame(self, frame: dict[str, object]) -> None:
        """The raw transport, bounded like ``report``: a plugin calls ``context.report_progress``."""
        try:
            payload = encode_json(frame, max_depth=1, max_bytes=PROGRESS_FRAME_MAX_BYTES, limit_code="output_limit_exceeded")
        except (ValueError, ToolExecutionError):
            return
        self._send(payload)

    def _send(self, payload: bytes) -> None:
        with self._lock:
            if self._closed or self._sent >= CHILD_PROGRESS_FRAME_CAP:
                return
            self._sent += 1
            try:
                self._connection.send_bytes(payload)
            except (OSError, ValueError):
                # A broken pipe ends the reporting, not the calculation: the parent sees the crash on the result frame.
                self._closed = True

    def close(self) -> None:
        with self._lock:
            self._closed = True


@dataclass(frozen=True, slots=True)
class ToolWorkerJob:
    """Only bounded input bytes and server-owned identity/policy cross this boundary."""

    execution_id: str
    tool_code: str
    contract_version: str
    implementation_version: str
    schema_fingerprint: str
    parameters: bytes
    soft_deadline: float
    hard_deadline: float
    max_parameter_bytes: int
    max_result_bytes: int
    max_json_depth: int
    engine_timeout_ms: int = 4_000
    memory_limit_bytes: int = 1_073_741_824
    #: The values of the plugin's settings for this job (resolved by the parent for the user who asks), or None for a tool without fields.
    settings: BoundSettings | None = None


def _elapsed_ms(started_ns: int) -> int:
    return (time.monotonic_ns() - started_ns) // 1_000_000


def _job_definition(job: ToolWorkerJob, registry_class: type[ToolPluginRegistry]) -> ToolDefinition:
    definition = registry_class.get_definition(job.tool_code)
    if definition is None:
        raise ToolExecutionError("tool_unavailable")
    descriptor = definition.descriptor
    if descriptor.tool_code != job.tool_code or descriptor.contract_version != job.contract_version or descriptor.implementation_version != job.implementation_version or descriptor.schema_fingerprint != job.schema_fingerprint:
        raise ToolExecutionError("version_mismatch", retryable=True)
    return definition


def _validated_input(job: ToolWorkerJob, definition: ToolDefinition) -> BaseModel:
    if len(job.parameters) > job.max_parameter_bytes:
        raise ToolExecutionError("input_limit_exceeded")
    original = plain_json_object(decode_json(job.parameters, max_depth=job.max_json_depth))
    parameters = definition.input_adapter.validate_json(job.parameters, strict=True)
    operation = getattr(parameters, "operation", None)
    if not isinstance(parameters, BaseModel) or not isinstance(operation, str):
        raise ToolExecutionError("invalid_parameters")
    if operation != original.get("operation"):
        raise ToolExecutionError("invalid_parameters")
    if operation not in {policy.operation for policy in definition.descriptor.operations}:
        raise ToolExecutionError("invalid_parameters")
    return parameters


def _failure_frame(job: ToolWorkerJob, error: ToolError, metrics: dict[str, int | None]) -> dict[str, object]:
    return {
        "kind": "result",
        "execution_id": job.execution_id,
        "status": "error",
        "error": error.model_dump(mode="json"),
        "metrics": ToolItemMetrics.model_validate(metrics).model_dump(mode="json"),
    }


def _error_code_for_phase(phase: str) -> ToolErrorCode:
    if phase == "input":
        return "invalid_parameters"
    if phase in ("serialization", "output"):
        return "invalid_output"
    return "execution_failed"


def _execute(job: ToolWorkerJob, cancellation: CancellationSignal, registry_class: type[ToolPluginRegistry], progress: PipeProgressReporter | None = None) -> dict[str, object]:
    metrics: dict[str, int | None] = {}
    phase = "definition"
    context = ToolExecutionContext(
        execution_id=job.execution_id,
        soft_deadline=job.soft_deadline,
        hard_deadline=job.hard_deadline,
        cancelled=cancellation.is_set,
        engine_timeout_ms=job.engine_timeout_ms,
        progress=progress,
    )
    try:
        context.checkpoint()
        definition = _job_definition(job, registry_class)
        phase = "input"
        started = time.monotonic_ns()
        try:
            parameters = _validated_input(job, definition)
        finally:
            metrics["input_validation_ms"] = _elapsed_ms(started)
        context.checkpoint()
        phase = "construction"
        plugin = definition.plugin_class()
        if job.settings is not None:
            plugin.bind_settings(job.settings)
        context.checkpoint()
        phase = "compute"
        started = time.monotonic_ns()
        try:
            result = plugin.compute(definition.descriptor.tool_code, parameters, context)
        finally:
            metrics["compute_ms"] = _elapsed_ms(started)
            if progress is not None:
                progress.close()
        context.checkpoint()
        if not isinstance(result, BaseModel):
            raise ToolExecutionError("invalid_output")
        phase = "serialization"
        started = time.monotonic_ns()
        try:
            output = definition.output_adapter.dump_python(result, mode="json", by_alias=True, warnings="error")
            payload = encode_json(output, max_depth=job.max_json_depth, max_bytes=job.max_result_bytes, limit_code="output_limit_exceeded")
        finally:
            metrics["serialization_ms"] = _elapsed_ms(started)
        phase = "output"
        started = time.monotonic_ns()
        try:
            definition.output_adapter.validate_json(payload, strict=True)
        finally:
            metrics["output_validation_ms"] = _elapsed_ms(started)
        if time.monotonic() >= job.hard_deadline:
            raise ToolExecutionError("execution_timeout", retryable=True)
        if cancellation.is_set():
            raise ToolExecutionError("execution_limit", retryable=True)
        return {
            "kind": "result",
            "execution_id": job.execution_id,
            "status": "success",
            "result": output,
            "metrics": ToolItemMetrics.model_validate(metrics).model_dump(mode="json"),
        }
    except ValidationError as exc:
        return _failure_frame(job, validation_error(exc, code=_error_code_for_phase(phase)), metrics)
    except ToolExecutionError as exc:
        return _failure_frame(job, ToolError(code=exc.code, retryable=exc.retryable), metrics)
    except Exception:
        # A packaged plugin failure becomes a code, not an exception/input disclosure.
        return _failure_frame(job, ToolError(code=_error_code_for_phase(phase), retryable=False), metrics)


def execute_tool_job(
    job: ToolWorkerJob,
    response: Connection,
    cancellation: PipeCancellation,
    registry_class: type[ToolPluginRegistry] = ToolPluginRegistry,
) -> None:
    """Run only in an owned spawn child; a result frame is not a cleanup ACK."""
    if multiprocessing.parent_process() is None:
        raise RuntimeError("Tool worker entry requires an owned child process")
    try:
        if os.name != "posix":
            frame = _failure_frame(job, ToolError(code="service_unavailable", retryable=False), {})
        else:
            os.setsid()
            response.send_bytes(
                encode_json(
                    {
                        "kind": "ready",
                        "execution_id": job.execution_id,
                        "pid": os.getpid(),
                        "pgid": os.getpgrp(),
                        "created_at": psutil.Process().create_time(),
                    }
                )
            )
            # No plugin code runs before the supervisor has adopted the owned session.
            progress = PipeProgressReporter(response, job.execution_id)
            if cancellation.await_start(job.hard_deadline):
                try:
                    frame = _execute(job, cancellation, registry_class, progress)
                finally:
                    progress.close()
            else:
                frame = _failure_frame(job, ToolError(code="execution_limit", retryable=True), {})
        response.send_bytes(encode_json(frame, max_depth=job.max_json_depth + 4, max_bytes=job.max_result_bytes + 65_536, limit_code="output_limit_exceeded"))
    finally:
        response.close()
        if isinstance(cancellation, PipeCancellation):
            cancellation.connection.close()
