"""Links of the instance that the app shows to its users.

Owner: workstream H (platform). Each function reads its address from ``backend/app/config/platform.py`` and never
raises: an invalid address is logged once per process, with what it costs until it is fixed, and the app falls back to
its default (for the support address: a new GitHub issue on a self-hosted instance, no report link on a managed one;
for the legal addresses of F09, written by workstream A: no link, the legal notice alone).
"""

import functools

from backend.app.config.platform import privacy_url, support_url, tos_url
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: What an invalid support address costs until it is fixed, as the error log says it (N61: no public fallback when managed).
_DEFAULT_SUPPORT = "until it is fixed, the asset search offers a new GitHub issue on a self-hosted instance and no report link on a managed one"
#: What an invalid legal address costs until it is fixed (F09): its link stays hidden, the legal notice shows without it.
_HIDDEN_TERMS = "the terms of service link stays hidden until it is fixed: the legal notice shows without it"
_HIDDEN_PRIVACY = "the privacy policy link stays hidden until it is fixed: the legal notice shows without it"


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


def terms_link() -> str | None:
    """``LIBREFOLIO_TOS_URL``, or None when it is unset or invalid (logged once): the legal notice then shows no terms link."""
    try:
        return tos_url()
    except ValueError as exc:
        _report_invalid(str(exc), _HIDDEN_TERMS)
        return None


def privacy_link() -> str | None:
    """``LIBREFOLIO_PRIVACY_URL``, or None when it is unset or invalid (logged once): the legal notice then shows no privacy link."""
    try:
        return privacy_url()
    except ValueError as exc:
        _report_invalid(str(exc), _HIDDEN_PRIVACY)
        return None
