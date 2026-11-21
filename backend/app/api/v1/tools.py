"""Authenticated catalogue, atomic bulk compute and sanitized Tool diagnostics."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.responses import Response, StreamingResponse
from starlette.types import Message, Receive, Scope

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.logging_config import get_logger
from backend.app.schemas.tools import ToolCatalogResponse, ToolComputeBatchRequest, ToolComputeBatchResponse, ToolComputeProgress, ToolComputeStreamLine, ToolDiagnosticsResponse, ToolPlatformPolicy
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.tools.base import ToolExecutionError
from backend.app.services.tools.catalog import effective_catalog_entries
from backend.app.services.tools.catalog import get_tool_catalog as build_tool_catalog
from backend.app.services.tools.executor import get_tool_executor
from backend.app.services.tools.settings import bound_settings_for_batch
from backend.app.services.tools.wire import encode_json, parse_json, validate_json_value

logger = get_logger(__name__)

# Request budget of the catalogue and diagnostics routes, capped by the platform's request_timeout_ms.
_READ_ROUTE_TIMEOUT_MS = 20_000


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
        self.deadline = started + policy.request_timeout_ms / 1000

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

    def begin_execution(self, timeout_ms: int = _READ_ROUTE_TIMEOUT_MS) -> None:
        bounded_timeout_ms = min(timeout_ms, self.policy.request_timeout_ms)
        remaining = self.started + bounded_timeout_ms / 1000 - time.monotonic()
        if remaining <= 0:
            raise HTTPException(status_code=503, detail="Tool request deadline exceeded")
        self.deadline = self.started + bounded_timeout_ms / 1000
        self._timeout.reschedule(asyncio.get_running_loop().time() + remaining)


class ToolRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()
        # The ingress window bounds receiving and validating a request body, and the dependencies resolved with it.
        # A route without a body has no ingress phase: it opens directly under its own request budget, so its
        # authentication cannot exhaust a window sized for a body it never reads.
        has_body = self.body_field is not None

        async def bounded_handler(request: Request) -> Response:
            policy = get_tool_executor().policy
            started = time.monotonic()
            opening_window_ms = policy.ingress_timeout_ms if has_body else min(_READ_ROUTE_TIMEOUT_MS, policy.request_timeout_ms)
            content_length = request.headers.get("content-length")
            if content_length is not None:
                if not content_length.isascii() or not content_length.isdecimal():
                    raise HTTPException(status_code=400, detail="Invalid Tool content length")
                significant_length = content_length.lstrip("0") or "0"
                if len(significant_length) > len(str(policy.max_request_bytes)) or int(significant_length) > policy.max_request_bytes:
                    raise HTTPException(status_code=413, detail="Tool request body limit exceeded")
            try:
                async with asyncio.timeout(opening_window_ms / 1000) as timeout:
                    bounded_request = _ToolRequest(request.scope, request.receive, policy=policy, started=started, timeout=timeout)
                    response = await handler(bounded_request)
                    # A stream's body is written after this window: it bounds its own lines and its own deadline.
                    if request.method == "POST" and not isinstance(response, StreamingResponse) and len(response.body) > policy.max_response_bytes:
                        raise HTTPException(status_code=503, detail="Tool response body limit exceeded")
                    return response
            except RequestValidationError as exc:
                # Raw validation details may contain malformed Unicode or scenario values.
                raise HTTPException(status_code=422, detail="Invalid Tool request envelope") from exc
            except TimeoutError as exc:
                raise HTTPException(status_code=503, detail="Tool request deadline exceeded") from exc

        return bounded_handler


router = APIRouter(prefix="/tools", tags=["Tools"], route_class=ToolRoute)


def _execution_request(request: Request, *, timeout_ms: int = _READ_ROUTE_TIMEOUT_MS) -> _ToolRequest:
    if not isinstance(request, _ToolRequest):
        raise RuntimeError("Tool endpoints require their bounded transport route")
    request.begin_execution(timeout_ms)
    return request


async def _client_disconnected(request: Request) -> None:
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return


async def _compute_until_disconnect(batch: ToolComputeBatchRequest, request: _ToolRequest, principal_key: str, settings: Mapping[str, BoundSettings] | None = None) -> ToolComputeBatchResponse | Response:
    work = asyncio.create_task(get_tool_executor().compute(batch, principal_key=principal_key, request_started=request.started, settings=settings))
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
    return await asyncio.to_thread(build_tool_catalog, executor.policy, usable_cpus=executor.usable_cpus)


@router.post("/compute", response_model=ToolComputeBatchResponse)
async def compute_tools(batch: ToolComputeBatchRequest, request: Request, current_user: User = Depends(get_current_user)) -> ToolComputeBatchResponse | Response:
    executor = get_tool_executor()
    request_timeout_ms = await asyncio.to_thread(executor.batch_request_timeout_ms, batch)
    bounded_request = _execution_request(request, timeout_ms=request_timeout_ms)
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # The values of the tools' settings are resolved here, in the parent, for the user who asks (CP12): the worker has no database.
        settings = await bound_settings_for_batch(batch, user_id=current_user.id)
        return await _compute_until_disconnect(batch, bounded_request, str(current_user.id), settings)
    except ToolExecutionError as exc:
        status_code = 429 if exc.code == "queue_full" else 503
        raise HTTPException(status_code=status_code, detail={"code": exc.code, "retryable": exc.retryable}) from exc


def _ndjson_line(value: dict[str, object]) -> bytes:
    return encode_json(value, max_depth=64) + b"\n"


def _release(*tasks: asyncio.Task) -> None:
    """Cancel without waiting (a cancelled stream must not await again), and retrieve what each task ends with."""
    for task in tasks:
        if not task.done():
            task.cancel()
        task.add_done_callback(lambda done: done.cancelled() or done.exception())


async def _stream_lines(work: asyncio.Task[ToolComputeBatchResponse], events: asyncio.Queue[ToolComputeProgress], first: ToolComputeProgress | None, deadline: float, max_bytes: int) -> AsyncIterator[bytes]:
    """The stream's body: every progress message as it comes, then ``{kind: "result", response}``. A stream that cannot
    end well (past its deadline, an unexpected failure, a result over the response ceiling) ends without a result line,
    which the client reads as a broken answer. A closed browser cancels it, and with it the calculation. The deadline is
    checked between lines, never around a ``yield``: a cancel must not land in the transport's send."""
    getter: asyncio.Task[ToolComputeProgress] | None = None
    try:
        if first is not None:
            yield _ndjson_line(first.model_dump(mode="json"))
        while not work.done():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning("Tool stream deadline exceeded before the result")
                return
            getter = asyncio.create_task(events.get())
            await asyncio.wait((work, getter), timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
            event = getter.result() if getter.done() else None
            if event is None:
                getter.cancel()
            getter = None
            if event is not None:
                yield _ndjson_line(event.model_dump(mode="json"))
        # The outcome reaches this loop after its item's last messages: hand them over first.
        while not events.empty():
            yield _ndjson_line(events.get_nowait().model_dump(mode="json"))
        response = work.result()
        line = _ndjson_line({"kind": "result", "response": response.model_dump(mode="json")})
        if len(line) > max_bytes:
            logger.warning("Tool stream result exceeds the response limit", request_id=response.request_id, size=len(line))
            return
        yield line
    except Exception as exc:  # isolation boundary: the headers are sent, the stream can only end without a result
        logger.error("Tool stream failed before the result", exc_info=exc)
    finally:
        _release(work, *((getter,) if getter is not None else ()))


def _refusal(exc: ToolExecutionError) -> HTTPException:
    """A refusal before any line: the status ``POST /tools/compute`` answers."""
    return HTTPException(status_code=429 if exc.code == "queue_full" else 503, detail={"code": exc.code, "retryable": exc.retryable})


class _NDJSONResponse(StreamingResponse):
    """A stream of JSON lines; its media type is what the OpenAPI document declares for the route."""

    media_type = "application/x-ndjson"


@router.post(
    "/compute/stream",
    response_class=_NDJSONResponse,
    responses={
        200: {
            "model": ToolComputeStreamLine,
            "description": "One ToolComputeStreamLine per line: progress lines, then the result line. A stream without its result line is a broken answer.",
        }
    },
)
async def compute_tools_stream(batch: ToolComputeBatchRequest, request: Request, current_user: User = Depends(get_current_user)) -> Response:
    """``POST /tools/compute`` with the progress of its calculations (lot V1 of project 67). The same admission,
    deadlines, cancellation and result; refusals before any job (429, 503) and a disconnect before the first line are
    the same HTTP answers. Then a stream of lines, never compressed (``MIDDLEWARE_STACK`` excludes the media type), so
    each line leaves as soon as it is written."""
    executor = get_tool_executor()
    request_timeout_ms = await asyncio.to_thread(executor.batch_request_timeout_ms, batch)
    bounded_request = _execution_request(request, timeout_ms=request_timeout_ms)
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        settings = await bound_settings_for_batch(batch, user_id=current_user.id)
    except ToolExecutionError as exc:
        raise _refusal(exc) from exc
    events: asyncio.Queue[ToolComputeProgress] = asyncio.Queue()
    work = asyncio.create_task(executor.compute(batch, principal_key=str(current_user.id), request_started=bounded_request.started, settings=settings, on_progress=events.put_nowait))
    first = asyncio.create_task(events.get())
    disconnect = asyncio.create_task(_client_disconnected(bounded_request))
    try:
        # Until a first line exists the answer is still an HTTP status: an admission refusal stays a 429 or a 503.
        await asyncio.wait((work, first, disconnect), return_when=asyncio.FIRST_COMPLETED)
    except BaseException:
        _release(work, first, disconnect)
        raise
    if disconnect.done() and not work.done():
        _release(work, first, disconnect)
        return Response(status_code=499)
    _release(disconnect)
    initial = first.result() if first.done() else None
    if not first.done():
        first.cancel()
    failure = work.exception() if work.done() and not work.cancelled() else None
    if isinstance(failure, ToolExecutionError):
        raise _refusal(failure) from failure
    if failure is not None:
        raise failure  # what /compute would answer for it, never a 200 with an empty stream
    # GZip leaves application/x-ndjson alone (platform/middleware.py); a proxy is asked not to transform or buffer it.
    headers = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}
    return _NDJSONResponse(_stream_lines(work, events, initial, bounded_request.deadline, executor.policy.max_response_bytes), headers=headers)


@router.get("/diagnostics", response_model=ToolDiagnosticsResponse)
async def get_tool_diagnostics(request: Request, current_user: User = Depends(get_current_user)) -> ToolDiagnosticsResponse:
    _execution_request(request)
    executor = get_tool_executor()
    descriptors, failures = await asyncio.to_thread(effective_catalog_entries, executor.policy, usable_cpus=executor.usable_cpus)
    capabilities = await asyncio.to_thread(executor.resource_capabilities)
    return ToolDiagnosticsResponse(
        scope="api_process",
        runtime_id=executor.runtime_id,
        policy=executor.policy,
        loaded=descriptors,
        failures=list(failures),
        capabilities=capabilities,
        pool=executor.snapshot(),
    )
