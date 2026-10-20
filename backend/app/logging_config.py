"""
Logging configuration for LibreFolio backend.

Uses structlog for structured logging with:
- Console output (development)
- File output with weekly rotation (production)
- JSON formatting for production
- Human-readable formatting for development

Log rotation: Weekly with 52 weeks (1 year) retention, gzip compression.

Errors (lot H-60): ``logger.exception()`` writes its traceback once, inside the JSON line, at level ``ERROR``
(``LibreFolioBoundLogger``); a warning or a higher line written with an exception, or while one is handled, marks it
as reported (``utils/runtime/errors.py``), so the platform's safety net — the 5xx handler, the unhandled 500 — does
not write it a second time, and uvicorn's own «Exception in ASGI application» for it is dropped.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# LOG LEVEL POLICY — LibreFolio
# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL (50): process cannot continue, immediate intervention required
# ERROR    (40): handled error, operation failed or data corrupted
# WARNING  (30): anomaly but recoverable (fallback activated, missing data)
# INFO     (20): significant user operations (sync done, import, login, create)
# DEBUG    (10): operational details (provider used, SQL, intermediate results)
# TRACE    ( 5): high-frequency granular data (single rate, single data point)
#
# Practical rule:
#   "User did X"          → INFO
#   "System decided X"    → DEBUG
#   "Value X for date Y"  → TRACE (if repeated N times per operation)
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
import logging
import logging.handlers
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote_plus

import structlog
import structlog.stdlib
from structlog.types import EventDict

from backend.app.config import get_data_dir
from backend.app.utils.runtime.errors import is_reported, mark_reported, mark_traceback_reported
from backend.app.utils.runtime.secret_masking import SecretMaskingFilter, mask_event_dict

# TRACE level constant — importable by other modules
TRACE: int = 5

# Register TRACE at import time so logger.log(TRACE, ...) works everywhere,
# including test contexts where configure_logging() hasn't been called yet.
logging.addLevelName(TRACE, "TRACE")
logging.TRACE = TRACE  # type: ignore[attr-defined]
if TRACE not in structlog.stdlib.LEVEL_TO_NAME:
    structlog.stdlib.LEVEL_TO_NAME[TRACE] = "trace"

# Add trace() method to stdlib Logger so structlog can dispatch logger.log(5, ...)
if not hasattr(logging.Logger, "trace"):

    def _trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kwargs)  # type: ignore[arg-type]

    logging.Logger.trace = _trace  # type: ignore[attr-defined]

#: The methods of a logger that report a failure: a warning or higher.
_REPORTING_LEVELS = {"warning": logging.WARNING, "warn": logging.WARNING, "error": logging.ERROR, "exception": logging.ERROR, "critical": logging.CRITICAL, "fatal": logging.CRITICAL}


def _reported_exception(exc_info: Any) -> tuple[BaseException | None, bool]:
    """The exception a log call is about, and whether the line renders its traceback.

    The one given as ``exc_info`` (an exception or a tuple holding one), its traceback rendered; else the one being
    handled, its traceback rendered when ``exc_info`` is any other true value (``True``, ``exception()``), as structlog's
    ``format_exc_info`` reads it.
    """
    if isinstance(exc_info, BaseException):
        return exc_info, True
    if isinstance(exc_info, tuple) and len(exc_info) == 3 and isinstance(exc_info[1], BaseException):
        return exc_info[1], True
    return sys.exc_info()[1], bool(exc_info) and not isinstance(exc_info, tuple)


def _line_request_id(context: Any, event_kw: dict[str, Any]) -> str | None:
    """The ``request_id`` a line carries: the call's keyword, else the logger's bound context, else structlog's contextvars."""
    if "request_id" in event_kw:
        return event_kw["request_id"]
    if isinstance(context, dict) and "request_id" in context:
        return context["request_id"]
    return structlog.contextvars.get_contextvars().get("request_id")


class LibreFolioBoundLogger(structlog.stdlib.BoundLogger):
    """structlog's stdlib logger, with one traceback per exception and the «reported» mark (lot H-60).

    - ``exception()`` logs at error with ``exc_info``: the processors render the traceback into the JSON line, and the
      stdlib ``error`` adds none (``Logger.exception`` would add it a second time, in plain text, at level EXCEPTION).
    - A warning or a higher call, when its logger is enabled for that level, marks as reported the exception it is
      about (``exc_info``, else the one being handled), for the request the line names (its ``request_id``, H-60r), with
      every exception the line's traceback shows when it renders one. In the wrapper, not in a processor:
      ``capture_logs()`` replaces the processors, and the code under test must behave as in production.
    """

    def exception(self, event: str | None = None, *args: Any, **kw: Any) -> Any:
        kw.setdefault("exc_info", True)
        return self._proxy_to_logger("error", event, *args, **kw)

    def _proxy_to_logger(self, method_name: str, event: str | None = None, *event_args: Any, **event_kw: Any) -> Any:
        level = _REPORTING_LEVELS.get(method_name)
        if level is not None and self._logger.isEnabledFor(level):
            error, with_traceback = _reported_exception(event_kw.get("exc_info"))
            if error is not None:
                request_id = _line_request_id(self._context, event_kw)
                if with_traceback:
                    mark_traceback_reported(error, request_id)
                else:
                    mark_reported(error, request_id)
        return super()._proxy_to_logger(method_name, event, *event_args, **event_kw)


# Minimal structlog bootstrap: use stdlib LoggerFactory so custom levels (TRACE)
# work immediately. Full configure_logging() overrides this later with processors,
# handlers, and formatting. Without this, structlog defaults to PrintLogger which
# lacks a 'trace' method.
if not structlog.is_configured():
    structlog.configure(
        wrapper_class=LibreFolioBoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,  # allow reconfiguration by configure_logging()
    )


def get_log_directory() -> Path:
    """Get or create the log directory based on current environment (prod/test)."""
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add log level to the event dict.
    """
    if method_name == "warn":
        method_name = "warning"
    elif method_name == "exception":
        method_name = "error"
    event_dict["level"] = method_name.upper()
    return event_dict


def _get_rotated_filename(default_name: str) -> str:  # pragma: no cover
    """
    Custom namer for rotated log files.
    Adds .gz extension for compression.

    Example: librefolio.log.2025-11-28 -> librefolio.log.2025-11-28.gz
    """
    return default_name + ".gz"


def _compress_rotated_file(source: str, dest: str) -> None:  # pragma: no cover
    """
    Compress rotated log files with gzip.

    Args:
        source: Source log file path
        dest: Destination compressed file path (with .gz extension)
    """
    with open(source, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Remove original uncompressed file
    Path(source).unlink()


#: A query parameter in a log line: separator, name, value. A value ends at the next separator, so a URL nested unencoded
#: in another parameter's value is read parameter by parameter too.
_QUERY_PARAMETER = re.compile(r"([?&])([^=&#?\s]*)=([^&#?\s]*)")
#: A word that makes a parameter name a credential's, in any case.
_CREDENTIAL_WORD = re.compile(r"token|secret|password|passwd|api[-_]?key|signature|ticket", re.IGNORECASE)


def _is_credential_name(name: str) -> bool:
    """Whether a query parameter named ``name`` carries a credential, judged on the name as the app reads it (decoded)."""
    decoded = unquote_plus(name)
    return decoded.lower() == "code" or _CREDENTIAL_WORD.search(decoded) is not None


def mask_query_credentials(text: str) -> str:
    """``text`` with the value of every credential-like query parameter replaced by ``***``; the rest unchanged.

    A credential-like parameter is named exactly ``code``, or its name holds token, secret, password, passwd,
    api_key/apikey/api-key, signature or ticket (the restore's outcome ticket, lot B5c), in any case and once
    percent-decoded. A value is not decoded: a URL encoded
    inside another parameter's value is not read.
    """
    return _QUERY_PARAMETER.sub(lambda match: f"{match[1]}{match[2]}=***" if _is_credential_name(match[2]) else match[0], text)


class _QueryCredentialFilter(logging.Filter):
    """Mask credentials in the request lines uvicorn logs: HTTP on ``uvicorn.access``, WebSocket handshakes on ``uvicorn.error``.

    uvicorn passes the request's path, query string included, as one argument of the record: ``(client, method, path,
    http_version, status)`` for an HTTP request, ``(client, path[, status])`` for a WebSocket handshake. A ``?token=…``
    typed by hand would reach the log in clear; the links the app writes carry their tokens in the URL fragment, which
    the browser never sends.

    Every string argument is masked where it stands, so the arguments keep their number and order (uvicorn's
    ``AccessFormatter`` unpacks them); a message logged without arguments is masked itself. A format string with
    arguments is never rewritten, so its placeholders keep matching them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not args:
            if isinstance(record.msg, str):
                record.msg = mask_query_credentials(record.msg)
        elif isinstance(args, tuple):
            masked = tuple(mask_query_credentials(arg) if isinstance(arg, str) else arg for arg in args)
            if masked != args:
                record.args = masked
        return True


class _ReportedExceptionFilter(logging.Filter):
    """Drop a record of an exception the app already logged (lot H-60): uvicorn's «Exception in ASGI application» for the
    500 that ``security_headers.py`` answered and logged as JSON, with the request id. Every other record passes.

    The mark of any request will do (H-60r): ``security_headers.py`` writes a line for the request it answers, unless
    that request's log has one, before it raises the exception again, so uvicorn's record is always a second copy.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        info = record.exc_info
        return not (isinstance(info, tuple) and len(info) == 3 and isinstance(info[1], BaseException) and is_reported(info[1]))


_QUERY_CREDENTIAL_FILTER = _QueryCredentialFilter()
_REPORTED_EXCEPTION_FILTER = _ReportedExceptionFilter()
_SECRET_MASKING_FILTER = SecretMaskingFilter()


def configure_logging(log_level: str = "INFO", enable_file_logging: bool = True) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL, TRACE)
        enable_file_logging: Whether to enable file logging (default: True)
    """
    # TRACE registration already done at module level (idempotent guard)

    # Convert string level to logging constant (supports TRACE after addLevelName)
    numeric_level = getattr(logging, log_level.upper(), logging.getLevelName(log_level.upper()))
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Remove all existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        # basicConfig(force=True) below would close it, but finds nothing left: a log file would stay open
        handler.close()

    # Silence verbose third-party loggers
    # aiosqlite logs every SQL operation at DEBUG level
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    # sqlalchemy.pool logs connection pool operations
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    # sqlalchemy.engine logs SQL statements
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # httpx/httpcore log every TCP connection, TLS handshake, request header etc.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # yfinance logs every HTTP request, cookie/crumb negotiation, and response at DEBUG
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    # peewee (used internally by yfinance) logs DB operations
    logging.getLogger("peewee").setLevel(logging.WARNING)
    # watchfiles (used by uvicorn reload) logs every change detection at DEBUG level
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    # ddgs (web link-finder) uses primp, a Rust HTTP client that forwards its crates'
    # logs into Python logging via pyo3-log. At DEBUG those flood the console with DNS
    # resolution (hickory-dns), TLS handshakes (rustls), HTTP/2 framing (h2/hpack) and
    # connection traces (reqwest/hyper_util/cookie_store) — hundreds of lines per search.
    for _noisy in ("primp", "hickory_resolver", "hickory_net", "rustls", "h2", "hpack", "hyper_util", "reqwest", "cookie_store"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)
    # urllib3 (HTTP pool) and asyncio (event-loop selector) are also verbose at DEBUG
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    # uvicorn's request lines (HTTP on uvicorn.access, WebSocket handshakes on uvicorn.error): credentials in a query
    # string are masked. The same filter object, so a second call never adds it twice.
    for uvicorn_logger in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(uvicorn_logger).addFilter(_QUERY_CREDENTIAL_FILTER)
    # uvicorn's own line for an exception the app already logged (H-60): the same filter object, once.
    logging.getLogger("uvicorn.error").addFilter(_REPORTED_EXCEPTION_FILTER)

    # Configure handlers
    handlers = []

    # Console handler (always enabled) - human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    # The secrets a plugin call carries, masked in the records of every logger while the call runs (plugin settings).
    console_handler.addFilter(_SECRET_MASKING_FILTER)
    handlers.append(console_handler)

    # File handler with weekly rotation (if enabled)
    if enable_file_logging:
        log_dir = get_log_directory()
        log_file = log_dir / "librefolio.log"

        # TimedRotatingFileHandler: rotate weekly (W0 = Monday), keep 52 backups (1 year)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_file),
            when="W0",  # Rotate every Monday at midnight
            interval=1,  # Every 1 week
            backupCount=52,  # Keep 52 weeks (1 year)
            encoding="utf-8",
            utc=True,  # Use UTC for rotation timing
        )
        file_handler.setLevel(numeric_level)
        file_handler.addFilter(_SECRET_MASKING_FILTER)

        # Enable compression of rotated files
        file_handler.rotator = _compress_rotated_file
        file_handler.namer = _get_rotated_filename

        handlers.append(file_handler)

    # Configure standard logging
    logging.basicConfig(format="%(message)s", handlers=handlers, level=numeric_level, force=True)

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # After the traceback is formatted and before rendering: JSON would escape a secret into another text.
        mask_event_dict,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=LibreFolioBoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def client_log_level(log_level: str) -> Literal["error", "debug"]:
    """How much the web app writes to the browser console about failed API calls (``/system/instance``, H-60, D4):
    ``debug`` when ``log_level`` is DEBUG or TRACE, in any case, ``error`` otherwise. Two states, never the level."""
    return "debug" if str(log_level).strip().upper() in ("DEBUG", "TRACE") else "error"


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance (structured logger).

    Args:
        name: Logger name (typically __name__)

    Returns:
        structlog.stdlib.BoundLogger: Configured logger

    Usage:
        logger = get_logger(__name__)
        logger.info("message", key="value")
    """
    return structlog.get_logger(name)
