"""The body of a 5xx answer, and the log line of a server error (lot H-60).

One shape for every 5xx the platform builds — the ``HTTPException`` handler (``api/server_errors.py``), the unhandled
500 (``security_headers.py``), the 500 of a response that breaks its model (``api/response_validation.py``):
``{"detail": ..., "request_id": ..., "error_type": ...}``. ``request_id`` is the request's (``request_id.py``) and
``error_type`` the class name of the failure's root cause (``utils/runtime/errors.py``); each key is absent when there
is nothing to say. Never the cause's message nor its traceback: a message can hold data, a traceback paths and values.

They go to the log, once per request (H-60r): ``report_server_error`` and ``report_unhandled_error`` write nothing when
the request's log has the failure already (the code that caught it wrote it); a short warning, «Request failed with an
error already logged», pointing to the first request that wrote it, when only another request's log has it (one
exception object can reach several requests: the portfolio engine and the risk engines hand the failure of one build to
every request waiting on it); else the failure with its traceback. So every request id a client sees is in the log, and
a traceback is written once. A line carries the method and the path, never the query string (it can carry a token),
the headers or the body.
"""

from typing import Any

from backend.app.logging_config import get_logger
from backend.app.utils.runtime.errors import (
    chain_reported,
    chain_reported_for,
    first_reporting_request,
    is_reported,
    is_reported_for,
    mark_reported,
    mark_traceback_reported,
    root_cause,
    shown_error,
    visible_causes,
)

logger = get_logger(__name__)

#: The line of a request that failed on an error another request's log has already, without its traceback.
ALREADY_LOGGED = "Request failed with an error already logged"


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


def _report_already_logged(error: BaseException, where: dict[str, Any], error_type: str | None) -> None:
    """The short line of a request that failed on an error the log has from another request: no traceback, a pointer."""
    pointer = first_reporting_request(error)
    logger.warning(
        ALREADY_LOGGED,
        **where,
        **({"error_type": error_type} if error_type is not None else {}),
        **({"logged_with_request_id": pointer} if pointer is not None else {}),
    )


def report_server_error(error: BaseException, *, status: int, method: str, path: str, request_id: str | None) -> str | None:
    """Log a 5xx raised as ``error`` unless the request's log has it already; the ``error_type`` its body carries.

    The request's log has the failure: nothing. Another request's log has it: the short line. Nobody logged it: an error
    line with its type, its chain and its traceback when it has a visible cause, a warning line when it has none.
    """
    error_type = cause_type(error)
    if not chain_reported_for(error, request_id):
        where = {"request_id": request_id, "status": status, "method": method, "path": path}
        if chain_reported(error):
            _report_already_logged(error, where, error_type)
        elif error_type is None:
            logger.warning("Request answered a server error", **where)
        else:
            shown = shown_error(error)
            logger.error("Request failed", **where, error_type=error_type, error_chain=_chain_names(error), exc_info=shown)
            mark_traceback_reported(shown, request_id)
        mark_reported(error, request_id)
    return error_type


def report_unhandled_error(error: BaseException, *, method: str | None, path: str | None, request_id: str | None) -> str:
    """Log an exception that left the app unless the request's log has it already; the ``error_type`` the 500's body carries.

    The request's log has it: nothing. Another request's log has it: the short line, without status. Else the error line
    with its traceback.
    """
    error_type = type(root_cause(error)).__name__
    if not is_reported_for(error, request_id):
        where = {"request_id": request_id, "method": method, "path": path}
        if is_reported(error):
            _report_already_logged(error, where, error_type)
        else:
            logger.error("Unhandled error", **where, error_type=error_type, error_chain=_chain_names(error), exc_info=shown_error(error))
        mark_reported(error, request_id)
    return error_type
