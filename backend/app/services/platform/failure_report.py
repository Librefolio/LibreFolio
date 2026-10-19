"""The body of a 5xx answer, and the log line of a server error (lot H-60).

One shape for every 5xx the platform builds — the ``HTTPException`` handler (``api/server_errors.py``), the unhandled
500 (``security_headers.py``), the 500 of a response that breaks its model (``api/response_validation.py``):
``{"detail": ..., "request_id": ..., "error_type": ...}``. ``request_id`` is the request's (``request_id.py``) and
``error_type`` the class name of the failure's root cause (``utils/runtime/errors.py``); each key is absent when there
is nothing to say. Never the cause's message nor its traceback: a message can hold data, a traceback paths and values.
They go to the log, once: ``report_server_error`` and ``report_unhandled_error`` write the line, unless the code that
caught the failure already did (``chain_reported``/``is_reported``). A line carries the method and the path, never the
query string (it can carry a token), the headers or the body.
"""

from typing import Any

from backend.app.logging_config import get_logger
from backend.app.utils.runtime.errors import chain_reported, is_reported, mark_reported, root_cause, shown_error, visible_causes

logger = get_logger(__name__)


def error_body(detail: Any, request_id: str | None, error_type: str | None) -> dict[str, Any]:
    """``{"detail": detail}``, with ``request_id`` and ``error_type`` when they are known."""
    body: dict[str, Any] = {"detail": detail}
    if request_id is not None:
        body["request_id"] = request_id
    if error_type is not None:
        body["error_type"] = error_type
    return body


def cause_type(error: BaseException) -> str | None:
    """The class name of the root cause of ``error``, or None when ``error`` has no visible cause."""
    root = root_cause(error)
    return type(root).__name__ if root is not error else None


def _chain_names(error: BaseException) -> list[str]:
    return [type(item).__name__ for item in visible_causes(error)]


def report_server_error(error: BaseException, *, status: int, method: str, path: str, request_id: str | None) -> str | None:
    """Log a 5xx raised as ``error`` unless the log has it already; the ``error_type`` its body carries.

    A visible cause nobody logged: an error line with its type, its chain and its traceback. No visible cause and
    nothing logged: a warning line, so every request id a client sees is found in the log. Already logged: nothing.
    """
    error_type = cause_type(error)
    if not chain_reported(error):
        where = {"request_id": request_id, "status": status, "method": method, "path": path}
        if error_type is None:
            logger.warning("Request answered a server error", **where)
        else:
            shown = shown_error(error)
            logger.error("Request failed", **where, error_type=error_type, error_chain=_chain_names(error), exc_info=shown)
            mark_reported(shown)
        mark_reported(error)
    return error_type


def report_unhandled_error(error: BaseException, *, method: str | None, path: str | None, request_id: str | None) -> str:
    """Log an exception that left the app unless the log has it already; the ``error_type`` the 500's body carries."""
    error_type = type(root_cause(error)).__name__
    if not is_reported(error):
        logger.error(
            "Unhandled error",
            request_id=request_id,
            method=method,
            path=path,
            error_type=error_type,
            error_chain=_chain_names(error),
            exc_info=shown_error(error),
        )
        mark_reported(error)
    return error_type
