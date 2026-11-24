"""Pure, typed plugin boundary for atomic Tool jobs."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Protocol

from pydantic import BaseModel, TypeAdapter

from backend.app.schemas.tools import ToolDiscoveryReason, ToolDocumentation, ToolErrorCode, ToolOperationPolicy, ToolUIDescriptor
from backend.app.services.plugin_settings.contract import PluginSettingsMixin


class ToolDefinitionError(ValueError):
    def __init__(self, reason: ToolDiscoveryReason):
        super().__init__(reason)
        self.reason = reason


class ToolExecutionError(RuntimeError):
    def __init__(self, code: ToolErrorCode, *, retryable: bool = False, reason: str | None = None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        # Where a ``worker_crashed`` was raised, one of the executor's ``CRASH_REASONS``: for the server log, never the wire.
        self.reason = reason


@dataclass(frozen=True, slots=True)
class ToolEngineWindow:
    """One cooperative engine budget inside the Tool soft wall."""

    deadline: float
    timeout_ms: int
    post_engine_reserve_ms: int


class ToolProgressChannel(Protocol):
    """Where a child's progress messages go (lot V1 of project 67): the worker's pipe to its parent."""

    def report(self, phase: str, step: int | None = None, total: int | None = None) -> None: ...


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    execution_id: str
    soft_deadline: float
    hard_deadline: float
    cancelled: Callable[[], bool]
    engine_timeout_ms: int = 4_000
    progress: ToolProgressChannel | None = None

    def report_progress(self, phase: str, step: int | None = None, total: int | None = None) -> None:
        """Tell the platform the calculation is in ``phase`` (one the operation declares), optionally at ``step`` of
        ``total``. Never a datum of the scenario or the result, never a percentage. It never blocks, raises or slows the
        calculation: a message the platform does not accept is dropped, and without a channel it does nothing."""
        if self.progress is not None:
            self.progress.report(phase, step, total)

    def checkpoint(self) -> None:
        if self.cancelled():
            raise ToolExecutionError("execution_limit", retryable=True)
        if time.monotonic() >= self.soft_deadline:
            raise ToolExecutionError("execution_limit", retryable=True)

    def remaining_soft_ms(self) -> int:
        return max(0, int((self.soft_deadline - time.monotonic()) * 1000))

    def claim_engine_window(self, *, post_engine_reserve_ms: int) -> ToolEngineWindow:
        """Reserve a full engine window plus caller-owned post-processing time."""
        if type(post_engine_reserve_ms) is not int or post_engine_reserve_ms < 0:
            raise ValueError("Post-engine reserve must be a non-negative integer")
        self.checkpoint()
        started = time.monotonic()
        required_ms = self.engine_timeout_ms + post_engine_reserve_ms
        if (self.soft_deadline - started) * 1000 < required_ms:
            raise ToolExecutionError("execution_limit", retryable=True)
        return ToolEngineWindow(
            deadline=started + self.engine_timeout_ms / 1000,
            timeout_ms=self.engine_timeout_ms,
            post_engine_reserve_ms=post_engine_reserve_ms,
        )


@dataclass(frozen=True, slots=True)
class ToolService:
    """One public calculation exposed by a packaged plugin."""

    tool_code: str
    name: str
    description: str
    category: str
    icon_key: str
    ui: ToolUIDescriptor
    documentation: ToolDocumentation
    operations: tuple[ToolOperationPolicy, ...]
    input_type: object
    output_type: object
    name_i18n_key: str | None = None
    description_i18n_key: str | None = None
    #: The operations' limits by the machine's usable CPUs (TURNI of project 67): rows of (fewest CPUs, operations), from one
    #: CPU up. The platform picks the row when it builds its executor (``catalog.operations_for``); a row changes only the
    #: time limits of ``operations``. Empty: ``operations`` hold on every machine.
    operations_by_usable_cpus: tuple[tuple[int, tuple[ToolOperationPolicy, ...]], ...] = ()

    def input_adapter(self) -> TypeAdapter:
        return TypeAdapter(self.input_type)

    def output_adapter(self) -> TypeAdapter:
        return TypeAdapter(self.output_type)


class ToolPlugin(PluginSettingsMixin, ABC):
    """A packaged pure computation exposing one or more public services.

    A plugin may declare ``settings_fields`` (family ``tool``, CP12): the core resolves the values of the user who asks in the
    parent process and delivers them with the job; ``compute`` reads ``self.settings`` and still touches no database, request or
    provider. The values are keyed by the **tool code** of each service: a plugin that bundles several services gets one set of
    values per service.
    """

    contract_version: ClassVar[str]
    implementation_version: ClassVar[str]
    services: ClassVar[tuple[ToolService, ...]]

    @abstractmethod
    def compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> BaseModel:
        """Return a complete result; all child work belongs to this job."""
