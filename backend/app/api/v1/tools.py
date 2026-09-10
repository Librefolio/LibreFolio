"""Authenticated catalogue, atomic bulk compute and sanitized Tool diagnostics."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.responses import Response
from starlette.types import Message, Receive, Scope

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.tools import ToolCatalogResponse, ToolComputeBatchRequest, ToolComputeBatchResponse, ToolDiagnosticsResponse, ToolPlatformPolicy
from backend.app.services.tools.base import ToolExecutionError
from backend.app.services.tools.catalog import effective_catalog_entries
from backend.app.services.tools.catalog import get_tool_catalog as build_tool_catalog
from backend.app.services.tools.executor import get_tool_executor
from backend.app.services.tools.wire import parse_json, validate_json_value


def _validate_envelope_strings(value: object, max_depth: int) -> None:
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        scaffold = {
            **value,
            "items": [{key: None if key == "parameters" else item_value for key, item_value in item.items()} if isinstance(item, dict) else item for item in value["items"]],
        }
        validate_json_value(scaffold, max_depth=max_depth)
    else:
        validate_json_value(value, max_depth=max_depth)


class _ToolRequest(Request):
    def __init__(self, scope: Scope, receive: Receive, *, policy: ToolPlatformPolicy, started: float, timeout: asyncio.Timeout):
        self.policy = policy
        self.started = started
        self._timeout = timeout
        self._decoded: object = None
        self._has_decoded = False
        self._received_bytes = 0

        async def bounded_receive() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                self._received_bytes += len(message.get("body", b""))
                if self._received_bytes > policy.max_request_bytes:
                    raise HTTPException(status_code=413, detail="Tool request body limit exceeded")
            return message

        super().__init__(scope, receive=bounded_receive)

    async def json(self) -> object:
        if not self._has_decoded:
            payload = await self.body()
            try:
                self._decoded = parse_json(payload)
            except (UnicodeError, ValueError, RecursionError) as exc:
                raise HTTPException(status_code=400, detail="Invalid Tool JSON request") from exc
            try:
                _validate_envelope_strings(self._decoded, self.policy.max_json_depth)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Invalid Tool request envelope") from exc
            self._has_decoded = True
        return self._decoded

    def begin_execution(self) -> None:
        remaining = self.started + self.policy.request_timeout_ms / 1000 - time.monotonic()
        if remaining <= 0:
            raise HTTPException(status_code=503, detail="Tool request deadline exceeded")
        self._timeout.reschedule(asyncio.get_running_loop().time() + remaining)


class ToolRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def bounded_handler(request: Request) -> Response:
            policy = get_tool_executor().policy
            started = time.monotonic()
            content_length = request.headers.get("content-length")
            if content_length is not None:
                if not content_length.isascii() or not content_length.isdecimal():
                    raise HTTPException(status_code=400, detail="Invalid Tool content length")
                significant_length = content_length.lstrip("0") or "0"
                if len(significant_length) > len(str(policy.max_request_bytes)) or int(significant_length) > policy.max_request_bytes:
                    raise HTTPException(status_code=413, detail="Tool request body limit exceeded")
            try:
                async with asyncio.timeout(policy.ingress_timeout_ms / 1000) as timeout:
                    bounded_request = _ToolRequest(request.scope, request.receive, policy=policy, started=started, timeout=timeout)
                    response = await handler(bounded_request)
                    if request.method == "POST" and len(response.body) > policy.max_response_bytes:
                        raise HTTPException(status_code=503, detail="Tool response body limit exceeded")
                    return response
            except RequestValidationError as exc:
                # Raw validation details may contain malformed Unicode or scenario values.
                raise HTTPException(status_code=422, detail="Invalid Tool request envelope") from exc
            except TimeoutError as exc:
                raise HTTPException(status_code=503, detail="Tool request deadline exceeded") from exc

        return bounded_handler


router = APIRouter(prefix="/tools", tags=["Tools"], route_class=ToolRoute)


def _execution_request(request: Request) -> _ToolRequest:
    if not isinstance(request, _ToolRequest):
        raise RuntimeError("Tool endpoints require their bounded transport route")
    request.begin_execution()
    return request


async def _client_disconnected(request: Request) -> None:
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def _compute_until_disconnect(batch: ToolComputeBatchRequest, request: _ToolRequest, principal_key: str) -> ToolComputeBatchResponse | Response:
    work = asyncio.create_task(get_tool_executor().compute(batch, principal_key=principal_key, request_started=request.started))
    disconnect = asyncio.create_task(_client_disconnected(request))
    try:
        completed, _pending = await asyncio.wait((work, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if work in completed:
            return work.result()
        disconnect.result()
        work.cancel()
        await asyncio.gather(work, return_exceptions=True)
        return Response(status_code=499)
    finally:
        disconnect.cancel()
        if not work.done():
            work.cancel()
        await asyncio.gather(work, disconnect, return_exceptions=True)


@router.get("/catalog", response_model=ToolCatalogResponse)
async def get_tool_catalog(request: Request, current_user: User = Depends(get_current_user)) -> ToolCatalogResponse:
    _execution_request(request)
    executor = get_tool_executor()
    return await asyncio.to_thread(build_tool_catalog, executor.policy)


@router.post("/compute", response_model=ToolComputeBatchResponse)
async def compute_tools(batch: ToolComputeBatchRequest, request: Request, current_user: User = Depends(get_current_user)) -> ToolComputeBatchResponse | Response:
    bounded_request = _execution_request(request)
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await _compute_until_disconnect(batch, bounded_request, str(current_user.id))
    except ToolExecutionError as exc:
        status_code = 429 if exc.code == "queue_full" else 503
        raise HTTPException(status_code=status_code, detail={"code": exc.code, "retryable": exc.retryable}) from exc


@router.get("/diagnostics", response_model=ToolDiagnosticsResponse)
async def get_tool_diagnostics(request: Request, current_user: User = Depends(get_current_user)) -> ToolDiagnosticsResponse:
    _execution_request(request)
    executor = get_tool_executor()
    descriptors, failures = await asyncio.to_thread(effective_catalog_entries, executor.policy)
    return ToolDiagnosticsResponse(
        scope="api_process",
        runtime_id=executor.runtime_id,
        policy=executor.policy,
        loaded=descriptors,
        failures=list(failures),
        pool=executor.snapshot(),
    )
