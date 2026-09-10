"""Child-side validation and execution; the supervisor owns process-tree cleanup."""

from __future__ import annotations

import multiprocessing
import os
import time
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Protocol

import psutil
from pydantic import BaseModel, ValidationError

from backend.app.schemas.tools import ToolError, ToolErrorCode, ToolItemMetrics
from backend.app.services.tools.base import ToolExecutionContext, ToolExecutionError
from backend.app.services.tools.registry import ToolDefinition, ToolPluginRegistry
from backend.app.services.tools.wire import decode_json, encode_json, plain_json_object, validation_error


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


def _execute(job: ToolWorkerJob, cancellation: CancellationSignal, registry_class: type[ToolPluginRegistry]) -> dict[str, object]:
    metrics: dict[str, int | None] = {}
    phase = "definition"
    context = ToolExecutionContext(job.execution_id, job.soft_deadline, job.hard_deadline, cancellation.is_set)
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
        context.checkpoint()
        phase = "compute"
        started = time.monotonic_ns()
        try:
            result = plugin.compute(parameters, context)
        finally:
            metrics["compute_ms"] = _elapsed_ms(started)
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
            if cancellation.await_start(job.hard_deadline):
                frame = _execute(job, cancellation, registry_class)
            else:
                frame = _failure_frame(job, ToolError(code="execution_limit", retryable=True), {})
        response.send_bytes(encode_json(frame, max_depth=job.max_json_depth + 4, max_bytes=job.max_result_bytes + 65_536, limit_code="output_limit_exceeded"))
    finally:
        response.close()
        if isinstance(cancellation, PipeCancellation):
            cancellation.connection.close()
