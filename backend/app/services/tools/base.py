"""Pure, typed plugin boundary for atomic Tool jobs."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from pydantic import BaseModel, TypeAdapter

from backend.app.schemas.tools import ToolDiscoveryReason, ToolDocumentation, ToolErrorCode, ToolOperationPolicy, ToolUIDescriptor


class ToolDefinitionError(ValueError):
    def __init__(self, reason: ToolDiscoveryReason):
        super().__init__(reason)
        self.reason = reason


class ToolExecutionError(RuntimeError):
    def __init__(self, code: ToolErrorCode, *, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    execution_id: str
    soft_deadline: float
    hard_deadline: float
    cancelled: Callable[[], bool]

    def checkpoint(self) -> None:
        if self.cancelled():
            raise ToolExecutionError("execution_limit", retryable=True)
        if time.monotonic() >= self.soft_deadline:
            raise ToolExecutionError("execution_limit", retryable=True)


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

    def input_adapter(self) -> TypeAdapter:
        return TypeAdapter(self.input_type)

    def output_adapter(self) -> TypeAdapter:
        return TypeAdapter(self.output_type)


class ToolPlugin(ABC):
    """A packaged pure computation exposing one or more public services."""

    contract_version: ClassVar[str]
    implementation_version: ClassVar[str]
    services: ClassVar[tuple[ToolService, ...]]

    @abstractmethod
    def compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> BaseModel:
        """Return a complete result; all child work belongs to this job."""
