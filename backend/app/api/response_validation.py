"""
A response that breaks its model, logged without its content (H-33).

When an endpoint returns what its ``response_model`` refuses, FastAPI raises ``ResponseValidationError``. FastAPI has
no handler for it: Starlette's ``ServerErrorMiddleware`` answers ``500 Internal Server Error`` and uvicorn logs the
traceback, whose message is ``str(exc)``: every error with its ``input``, that is the response itself, the data of the
user who asked. This handler logs the route and, for each error, its ``type`` and ``loc`` only: never the ``input``,
nor the ``msg`` (a validator may build it from the value), nor the traceback (its message is ``str(exc)``). It gives
the same answer as before, ``500 Internal Server Error`` in plain text. ``main.py`` installs it next to the 422 handler
of ``validation_errors.py``.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import PlainTextResponse

from backend.app.logging_config import get_logger

logger = get_logger(__name__)


async def _without_content(request: Request, exc: Exception) -> PlainTextResponse:
    """Log which part of its model a response broke, and answer as an unhandled error does: nothing of it is kept."""
    errors = exc.errors() if isinstance(exc, ResponseValidationError) else []
    # FastAPI writes "GET /api/v1/…": the full template, with the prefixes of the included routers, which
    # scope["route"] lacks
    _method, _, template = (getattr(exc, "endpoint_path", None) or "").partition(" ")
    endpoint = request.scope.get("endpoint")
    # logger.error, never logger.exception nor exc_info (despite the TRY400 convention): the traceback's message is
    # str(exc), which writes every error with its input, the response itself
    logger.error(
        "A response does not match its model",
        method=request.method,
        route=template or request.url.path,
        endpoint=getattr(endpoint, "__name__", None),
        errors=[{"type": error.get("type"), "loc": list(error.get("loc", ()))} for error in errors],
    )
    return PlainTextResponse("Internal Server Error", status_code=500)


def install_response_validation_handler(app: FastAPI) -> None:
    """Log every response of ``app`` that breaks its model without its content, and answer 500."""
    app.add_exception_handler(ResponseValidationError, _without_content)
