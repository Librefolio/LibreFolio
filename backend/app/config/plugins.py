"""Plugins section of the configuration: the plugin families and the asset search.

Owner: workstream X (plugins and asset search); the reads moved here from ``services/assets/web_link_finder.py`` in
workstream H's lot after checkpoint CP3. Read from the process environment only, never from ``.env``: ``./dev.py`` and
Docker Compose put them there. Each function keeps the exact semantics the call site had before it moved here; the API
key also accepts ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE``, as every secret does.
"""

import os

from backend.app.config import env_secret


def web_link_finder_enabled() -> bool:
    """``LIBREFOLIO_WEB_LINK_FINDER_ENABLED``: on with ``1``, ``true``, ``yes`` or ``on``, in any case, spaces around too.

    Unset counts as ``1``; any other value, the empty one included, turns the link finder off.
    """
    return os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")


def web_link_finder_engine() -> str:
    """``LIBREFOLIO_WEB_LINK_FINDER_ENGINE``, stripped and lowercased; ``ddgs`` when unset, the empty string when blank."""
    return os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_ENGINE", "ddgs").strip().lower()


def web_link_finder_api_key() -> str:
    """``LIBREFOLIO_WEB_LINK_FINDER_API_KEY``, or the content of ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE``, stripped.

    The empty string when neither is set. A ``_FILE`` that cannot give its secret raises ``SecretFileError``
    (``env_secret``).
    """
    return (env_secret("LIBREFOLIO_WEB_LINK_FINDER_API_KEY") or "").strip()


def web_link_finder_ddgs_region() -> str:
    """``LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION``, stripped; ``wt-wt`` when unset or blank."""
    return os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION", "wt-wt").strip() or "wt-wt"


def web_link_finder_ddgs_backend() -> str:
    """``LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND``, stripped; ``auto`` when unset or blank."""
    return os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND", "auto").strip() or "auto"


def web_link_finder_timeout(default: float) -> float:
    """``LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT``, seconds, as ``float()`` reads it; ``default`` when unset, blank or not a number."""
    raw = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT", "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def web_link_finder_max_results(default: int) -> int:
    """``LIBREFOLIO_WEB_LINK_FINDER_MAX``, as ``int()`` reads it; ``default`` when unset, blank or not an integer."""
    raw = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_MAX", "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default
