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


class ToolPlugin[InputT: BaseModel, OutputT: BaseModel](ABC):
    """A packaged pure computation; inputs never carry ambient authority."""

    tool_code: ClassVar[str]
    contract_version: ClassVar[str]
    implementation_version: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    name_i18n_key: ClassVar[str | None] = None
    description_i18n_key: ClassVar[str | None] = None
    category: ClassVar[str]
    icon_key: ClassVar[str]
    ui: ClassVar[ToolUIDescriptor]
    documentation: ClassVar[ToolDocumentation]
    operations: ClassVar[tuple[ToolOperationPolicy, ...]]
    input_type: ClassVar[object]
    output_type: ClassVar[object]

    @classmethod
    def input_adapter(cls) -> TypeAdapter[InputT]:
        return TypeAdapter[InputT](cls.input_type)

    @classmethod
    def output_adapter(cls) -> TypeAdapter[OutputT]:
        return TypeAdapter[OutputT](cls.output_type)

    @abstractmethod
    def compute(self, parameters: InputT, context: ToolExecutionContext) -> OutputT:
        """Return a complete result; all child work belongs to this job."""
