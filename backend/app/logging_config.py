"""
Logging configuration for LibreFolio backend.

Uses structlog for structured logging with:
- Console output (development)
- File output with weekly rotation (production)
- JSON formatting for production
- Human-readable formatting for development

Log rotation: Weekly with 52 weeks (1 year) retention, gzip compression.
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
import shutil
import sys
from pathlib import Path
from typing import Any

import structlog
import structlog.stdlib
from structlog.types import EventDict

from backend.app.config import get_data_dir

# TRACE level constant — importable by other modules
TRACE: int = 5


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


def configure_logging(log_level: str = "INFO", enable_file_logging: bool = True) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL, TRACE)
        enable_file_logging: Whether to enable file logging (default: True)
    """
    # Register TRACE level (5) as a formal named level
    logging.addLevelName(TRACE, "TRACE")
    logging.TRACE = TRACE  # type: ignore[attr-defined]  # needed for getattr(logging, "TRACE")

    # Add trace() method to stdlib Logger so structlog can dispatch it
    if not hasattr(logging.Logger, "trace"):

        def _trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
            if self.isEnabledFor(TRACE):
                self._log(TRACE, message, args, **kwargs)  # type: ignore[arg-type]

        logging.Logger.trace = _trace  # type: ignore[attr-defined]

    # Register level 5 in structlog's dispatch table (BoundLogger.log uses this dict)
    if TRACE not in structlog.stdlib.LEVEL_TO_NAME:
        structlog.stdlib.LEVEL_TO_NAME[TRACE] = "trace"

    # Convert string level to logging constant (supports TRACE after addLevelName)
    numeric_level = getattr(logging, log_level.upper(), logging.getLevelName(log_level.upper()))
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Remove all existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

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

    # Configure handlers
    handlers = []

    # Console handler (always enabled) - human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
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
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


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
