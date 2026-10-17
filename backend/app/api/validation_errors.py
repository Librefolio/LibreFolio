"""
A 422 without the request's input (A-35).

FastAPI answers a request that fails validation with every error and the input that caused it: the value of a field
that is wrong, and — for a field that is missing — the whole body around it, a password or a token included. This
handler gives the same answer without the ``input`` of any error: ``type``, ``loc``, ``msg`` and ``ctx`` stay, so a
client still knows which field is wrong and why. ``main.py`` installs it once, for every route.

The OpenAPI schema keeps FastAPI's ``ValidationError``, where ``input`` was always optional.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def _without_input(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI's own 422, built from a new error without the inputs: nothing of the request's body is kept."""
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return await request_validation_exception_handler(request, RequestValidationError([{key: value for key, value in error.items() if key != "input"} for error in errors]))


def install_validation_error_handler(app: FastAPI) -> None:
    """Answer every 422 of ``app`` as FastAPI does, without the input of any error."""
    app.add_exception_handler(RequestValidationError, _without_input)
