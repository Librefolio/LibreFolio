"""A request id for every HTTP request: in the response and in every log line of the request (lot H-60).

``RequestIdMiddleware`` is the second entry of ``MIDDLEWARE_STACK`` (``middleware.py``), right after the activity
tracking of workstream Z and outside the security headers. For each HTTP request it draws ``secrets.token_hex(8)`` — 16
lowercase hexadecimal characters, nothing derived from the request — and:

- stores it in ``scope["state"]["request_id"]``, where ``request.state.request_id`` and ``request_id_of`` read it;
- binds it in structlog's contextvars while the request runs (``merge_contextvars`` is the first processor of
  ``logging_config.py``), so every line written for the request carries ``request_id``;
- adds ``X-Request-Id`` to the response, the 500 of an unhandled exception included.

A user who reports an error quotes the id, and the administrator finds the request's lines with it. An id sent by the
client is not used: the ids in the log stay the server's own. The middleware writes no log line itself.
"""

import secrets
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: The response header, lower case as ASGI carries header names.
HEADER = b"x-request-id"


def new_request_id() -> str:
    """A new request id: 16 random lowercase hexadecimal characters."""
    return secrets.token_hex(8)


def request_id_of(source: Any) -> str | None:
    """The request id of a ``Request`` (or of its ASGI scope), or None for a request this middleware did not see."""
    scope = source if isinstance(source, dict) else getattr(source, "scope", None)
    state = scope.get("state") if isinstance(scope, dict) else None
    value = state.get("request_id") if isinstance(state, dict) else None
    return value if isinstance(value, str) else None


class RequestIdMiddleware:
    """Give every HTTP request an id: in ``scope["state"]``, in its log lines, in its response's ``X-Request-Id``."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        header = (HEADER, request_id.encode("ascii"))

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                if all(bytes(name).lower() != HEADER for name, _ in headers):
                    headers.append(header)
                    message = {**message, "headers": headers}
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            await self.app(scope, receive, send_with_id)
