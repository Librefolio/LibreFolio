"""Plugins section of the configuration: the plugin families and the asset search.

Owner: workstream X (plugins and asset search); the reads moved here from ``services/assets/web_link_finder.py`` in
workstream H's lot after checkpoint CP3. Read from the process environment only, never from ``.env``: ``./dev.py`` and
Docker Compose put them there. Each function keeps the exact semantics the call site had before it moved here, except
the timeout and the maximum of the link finder, which take their default for a value below 1 or not finite (X-R6); the
API key also accepts ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE``, as every secret does.

The plugin settings (``services/plugin_settings/``) read their variables through ``plugin_setting_env``: the names are
derived from the fields the plugins declare, ``LIBREFOLIO_PLUGIN_<FAMILY>_<CODE>_<FIELD>``, or are a field's declared
alias.

The order of the asset providers in the search (F21) has two overrides, ``asset_providers_premium()`` and
``asset_providers_order()``; ``services/assets/provider_policy.py`` applies them.

The per-user limit of the provider probe (MF-SI2) is ``probe_rate_limit()``; ``api/v1/assets/providers.py`` applies it.
"""

import math
import os
import re

from backend.app.config import env_secret, env_secret_origin


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
    """``LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT``, seconds, as ``float()`` reads it; ``default`` when unset, blank, not a
    number, not finite or below 1 (a timeout under a second used to mean no timeout at all)."""
    raw = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT", "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        return default
    return value if math.isfinite(value) and value >= 1 else default


def web_link_finder_max_results(default: int) -> int:
    """``LIBREFOLIO_WEB_LINK_FINDER_MAX``, as ``int()`` reads it; ``default`` when unset, blank, not an integer or below
    1 (``0`` used to return one URL all the same)."""
    raw = os.environ.get("LIBREFOLIO_WEB_LINK_FINDER_MAX", "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return value if value >= 1 else default


def plugin_setting_env(name: str) -> str | None:
    """The value the variable ``name`` gives a plugin setting, as ``env_secret`` reads it: ``NAME``, or the content of
    ``NAME_FILE``; ``None`` when neither is set or both are blank.

    Every field accepts the ``_FILE`` form, secret or not. A ``NAME_FILE`` that cannot give its value raises
    ``SecretFileError``, which names the variable and the path, never the content.
    """
    return env_secret(name)


def plugin_setting_env_origin(name: str) -> str | None:
    """Where ``plugin_setting_env(name)`` would take its value from: ``NAME``, ``NAME_FILE (<path>)``, or ``None`` when
    neither is set. Reads no file: enough to know that a variable locks its field."""
    return env_secret_origin(name)


def _provider_codes(name: str) -> tuple[str, ...] | None:
    """The provider codes listed in ``name``: comma-separated, stripped, lowercased, in order, each once.

    None when the variable is unset or blank, and when it lists no code at all (``,,``): then nothing is overridden.
    """
    codes: list[str] = []
    for part in os.environ.get(name, "").split(","):
        code = part.strip().lower()
        if code and code not in codes:
            codes.append(code)
    return tuple(codes) or None


def asset_providers_premium() -> tuple[str, ...] | None:
    """``LIBREFOLIO_ASSET_PROVIDERS_PREMIUM``: the asset providers this instance counts as premium in the search (F21).

    Comma-separated provider codes, in any case. Unset or blank: None, and each provider's declared tier applies. Set:
    exactly the listed providers are premium; a code that no provider has is ignored, and logged once.
    """
    return _provider_codes("LIBREFOLIO_ASSET_PROVIDERS_PREMIUM")


def asset_providers_order() -> tuple[str, ...] | None:
    """``LIBREFOLIO_ASSET_PROVIDERS_ORDER``: the order of the asset providers in the search (F21).

    Comma-separated provider codes, in any case. Unset or blank: None, and each provider's declared priority applies.
    Set: the listed providers come first, in that order, and the others follow by their declared priority; premium
    providers still come before the others. A code that no provider has is ignored, and logged once.
    """
    return _provider_codes("LIBREFOLIO_ASSET_PROVIDERS_ORDER")


#: Provider probes (``POST /api/v1/assets/provider/probe``) one user may start in a minute (MF-SI2), and the most a
#: setting may allow.
DEFAULT_PROBE_RATE_LIMIT = 30
PROBE_RATE_LIMIT_MAX = 10_000
PROBE_RATE_LIMIT_VARIABLE = "LIBREFOLIO_PROBE_RATE_LIMIT"
_WHOLE_NUMBER = re.compile(r"[0-9]+")


def probe_rate_limit() -> int:
    """``LIBREFOLIO_PROBE_RATE_LIMIT``: how many provider probes one user may start in a minute (MF-SI2).

    30 when unset or blank; ``0`` turns the limit off, as ``./dev.py server --test`` does for the test lanes, whose E2E
    suites probe many times as one user. Otherwise a whole number from 1 to 10 000, spaces around allowed. Any other value
    raises ``ValueError`` naming the variable and the value: ``api/v1/assets/providers.py`` logs it and keeps 30.
    """
    raw = os.environ.get("LIBREFOLIO_PROBE_RATE_LIMIT", "").strip()
    if not raw:
        return DEFAULT_PROBE_RATE_LIMIT
    if not _WHOLE_NUMBER.fullmatch(raw) or int(raw) > PROBE_RATE_LIMIT_MAX:
        raise ValueError(f"{PROBE_RATE_LIMIT_VARIABLE}={raw!r}: expected 0 (off) or a whole number of probes per minute up to {PROBE_RATE_LIMIT_MAX}")
    return int(raw)
