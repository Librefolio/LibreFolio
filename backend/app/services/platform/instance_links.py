"""Links of the instance that the app shows to its users.

Owner: workstream H (platform). Each function reads its address from ``backend/app/config/platform.py`` and never
raises: an invalid address is logged once per process, with what it costs until it is fixed, and the app shows its
default link instead.
"""

import functools

from backend.app.config.platform import support_url
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: What an invalid support address costs until it is fixed, as the error log says it.
_DEFAULT_SUPPORT = "the app links to the project's issues on GitHub until it is fixed"


@functools.cache
def _report_invalid(problem: str, consequence: str) -> None:
    """Log an invalid link setting once per process, with what it costs until it is fixed."""
    logger.error("Invalid instance link", problem=problem, consequence=consequence)


def support_link() -> str | None:
    """``LIBREFOLIO_SUPPORT_URL``, or None when it is unset or invalid (logged once): the app then links to GitHub issues."""
    try:
        return support_url()
    except ValueError as exc:
        _report_invalid(str(exc), _DEFAULT_SUPPORT)
        return None
