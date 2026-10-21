"""A 5xx answers with a request id and the failure's type, and its cause reaches the log once (lot H-60).

``install_server_error_handler(app)`` registers one handler for ``HTTPException``; ``main.py`` installs it next to the
422 handler (``validation_errors.py``) and the response-validation one (``response_validation.py``).

- Below 500 it is FastAPI's own ``http_exception_handler``: the same body, the same headers, no log line.
- From 500 the body is FastAPI's ``{"detail": ...}`` plus ``request_id`` and ``error_type``
  (``services/platform/failure_report.py``), and the log gets the failure once: an error line with the traceback of a
  cause nobody logged, a warning line for a 5xx with no cause and nothing logged, nothing when the code that caught the
  failure logged it already (AP-API-12, the backup routes: a warning inside the ``except``, then ``from None``).
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.platform.failure_report import error_body, report_server_error
from backend.app.services.platform.request_id import request_id_of


async def _http_exception(request: Request, exc: Exception) -> Response:
    """FastAPI's answer below 500; from 500, the same with the request id and the cause's type, and one log line."""
    if not isinstance(exc, StarletteHTTPException) or exc.status_code < 500:
        return await http_exception_handler(request, exc)
    request_id = request_id_of(request)
    error_type = report_server_error(exc, status=exc.status_code, method=request.method, path=request.url.path, request_id=request_id)
    return JSONResponse(error_body(exc.detail, request_id, error_type), status_code=exc.status_code, headers=exc.headers)


def install_server_error_handler(app: FastAPI) -> None:
    """Answer every ``HTTPException`` of ``app``: as FastAPI below 500, with ``request_id`` and ``error_type`` from 500."""
    app.add_exception_handler(StarletteHTTPException, _http_exception)
