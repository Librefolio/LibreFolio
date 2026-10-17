"""Links of the instance that the app shows to its users.

Owner: workstream H (platform). Each function reads its address from ``backend/app/config/platform.py`` and never
raises: an invalid address is logged once per process, with what it costs until it is fixed, and the app falls back to
its default (for the support address: a new GitHub issue on a self-hosted instance, no report link on a managed one).
"""

import functools

from backend.app.config.platform import support_url
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: What an invalid support address costs until it is fixed, as the error log says it (N61: no public fallback when managed).
_DEFAULT_SUPPORT = "until it is fixed, the asset search offers a new GitHub issue on a self-hosted instance and no report link on a managed one"


@functools.cache
def _report_invalid(problem: str, consequence: str) -> None:
    """Log an invalid link setting once per process, with what it costs until it is fixed."""
    logger.error("Invalid instance link", problem=problem, consequence=consequence)


def support_link() -> str | None:
    """``LIBREFOLIO_SUPPORT_URL``, or None when it is unset or invalid (logged once): the asset search then offers a new
    GitHub issue on a self-hosted instance, and no report link on a managed one."""
    try:
        return support_url()
    except ValueError as exc:
        _report_invalid(str(exc), _DEFAULT_SUPPORT)
        return None
