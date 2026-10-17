"""Platform section of the configuration: switches of the runtime itself.

Owner: workstream H (platform). Every environment variable of the application is read inside this package,
``backend/app/config/``: a module elsewhere calls a function here instead of reading ``os.environ``. The base
(constants, data directories, test mode, ``Settings``, the ``NAME_FILE`` reader of secrets) is in ``__init__.py``; each
owner keeps its variables in its own section module.

The variables below are read from the process environment only, never from ``.env``: ``./dev.py`` and Docker Compose
put them there. Each function keeps the exact semantics the call site had before it moved here, except that a blank
secret counts as unset.
"""

import os
from datetime import date

from pydantic import EmailStr, TypeAdapter, ValidationError

from backend.app.config import env_secret, env_secret_origin, env_url

_SUPPORT_URL = "LIBREFOLIO_SUPPORT_URL"
#: The legal pages of the instance (F09, workstream A): public, linked by the legal notice every user sees.
_TOS_URL = "LIBREFOLIO_TOS_URL"
_PRIVACY_URL = "LIBREFOLIO_PRIVACY_URL"
#: What the address after ``mailto:`` may not hold: a query, a fragment, an escape, a second address, the
#: ``Name <address>`` form or a path (``mailto://``). ``EmailStr`` accepts ``?``, ``#``, ``%`` and ``/`` in a local part
#: and unwraps angle brackets, so they are refused before it reads the address; it strips whitespace, refused anywhere.
_MAILTO_FORBIDDEN = frozenset('?#%,;<>"/')
_EMAIL = TypeAdapter(EmailStr)


def scheduler_disabled() -> bool:
    """``LIBREFOLIO_NO_SCHEDULER``: any non-empty value keeps the scheduler loop from starting.

    ``./dev.py server --no-scheduler`` sets it for test servers and the gallery. Every non-empty value counts, ``0``
    included.
    """
    return bool(os.environ.get("LIBREFOLIO_NO_SCHEDULER"))


def configured_jwt_secret() -> str | None:
    """``JWT_SECRET``, the key that signs session tokens, or else the content of the file named by ``JWT_SECRET_FILE``.

    ``None`` when neither is set: an empty or blank value counts as unset, so a stray space is never used as a key and
    the server makes a random one. A ``JWT_SECRET_FILE`` that cannot give its secret raises ``SecretFileError``
    (``env_secret``).
    """
    return env_secret("JWT_SECRET")


def configured_jwt_secret_origin() -> str | None:
    """Where the JWT secret comes from, for messages: ``JWT_SECRET``, ``JWT_SECRET_FILE (<path>)`` or ``None``."""
    return env_secret_origin("JWT_SECRET")


def configured_instance_key() -> str | None:
    """``LIBREFOLIO_INSTANCE_KEY``, or else the content of ``LIBREFOLIO_INSTANCE_KEY_FILE``; ``None`` when neither is set.

    Without one, ``services/platform/instance_key.py`` generates the key in the data directory on first use.
    """
    return env_secret("LIBREFOLIO_INSTANCE_KEY")


def configured_instance_key_origin() -> str | None:
    """Where the configured instance key comes from, for messages: the variable, or the ``_FILE`` one with its path."""
    return env_secret_origin("LIBREFOLIO_INSTANCE_KEY")


def owning_test_lane_id() -> str | None:
    """``LIBREFOLIO_TEST_LANE_ID``: the token of the test process tree that owns this server, set by the test runner."""
    return os.environ.get("LIBREFOLIO_TEST_LANE_ID")


def frozen_app_version() -> str | None:
    """``LF_APP_VERSION``: the version a build is frozen at, reported instead of ``git describe`` or ``VERSION``.

    The release workflow sets it from ``VERSION`` right after the checkout, for every later step of the job: the
    frontend builds (``frontend/vite.config.ts`` reads it too) and the servers of the gallery. ``None`` when unset or
    blank, as for every install.
    """
    return os.environ.get("LF_APP_VERSION", "").strip() or None


_BLOCKED_TRUE = frozenset({"1", "true", "yes", "on"})
_BLOCKED_FALSE = frozenset({"0", "false", "no", "off"})


def instance_blocked() -> bool:
    """``LIBREFOLIO_BLOCKED``: a hosting provider blocks the instance, and only a few API routes answer.

    ``api/v1/instance_block.py`` holds those routes. Unset or blank: not blocked, as for every install. ``1``, ``true``,
    ``yes`` or ``on`` block, ``0``, ``false``, ``no`` or ``off`` do not, in any case; any other value raises
    ``ValueError``, and the startup checks stop the server on it, so that a typo never leaves the choice to chance.
    """
    value = os.environ.get("LIBREFOLIO_BLOCKED", "").strip().lower()
    if not value or value in _BLOCKED_FALSE:
        return False
    if value in _BLOCKED_TRUE:
        return True
    raise ValueError("LIBREFOLIO_BLOCKED must be one of 1/0, true/false, yes/no, on/off, or unset")


def instance_deletion_date() -> date | None:
    """``LIBREFOLIO_DELETION_DATE``: the day the hosting provider will delete a blocked instance and its data.

    An ISO date (``2026-11-14``), shown on the block page. Unset or blank: no date. Any other value raises
    ``ValueError``, and the startup checks stop the server on it.
    """
    value = os.environ.get("LIBREFOLIO_DELETION_DATE", "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"LIBREFOLIO_DELETION_DATE must be an ISO date such as 2026-11-14, not {value!r}") from exc


def support_url() -> str | None:
    """``LIBREFOLIO_SUPPORT_URL``: where the users of the instance ask for help, such as an asset the search does not find.

    Two forms: an ``http(s)://`` page, by the rule of ``env_url``, or ``mailto:`` and one email address, checked by
    pydantic's ``EmailStr`` without any DNS lookup and returned as ``mailto:`` and the address as it normalizes it (the
    scheme in any case, saved lowercase). The address is public: the app shows it to every user. A hosting provider sets
    its own. Unset or blank: ``None``: the asset search then offers a new issue on the project's GitHub on a self-hosted
    instance, and no report link on a managed one (N61). Any other value raises ``ValueError``, naming the variable: the
    service that publishes it logs the error and publishes ``None``.
    """
    value = os.environ.get(_SUPPORT_URL, "").strip()
    if value[:7].lower() == "mailto:":
        return _mailto(value)
    return env_url(_SUPPORT_URL)


def tos_url() -> str | None:
    """``LIBREFOLIO_TOS_URL``: the terms of service of the instance, an ``http(s)://`` page by the rule of ``env_url`` (F09).

    Public: the legal notice links it for every user (the About tab, the sign-in pages, the welcome, the sidebar). A
    hosting provider sets its own. Unset or blank: ``None``, no link. Any other value raises ``ValueError``, naming the
    variable: the service that publishes it logs the error and publishes ``None``.
    """
    return env_url(_TOS_URL)


def privacy_url() -> str | None:
    """``LIBREFOLIO_PRIVACY_URL``: the privacy policy of the instance, by the rule of ``tos_url`` (F09)."""
    return env_url(_PRIVACY_URL)


def _mailto(value: str) -> str:
    """``mailto:`` and the one address ``value`` holds after it, as ``EmailStr`` normalizes it; ``ValueError`` otherwise."""
    address = value[7:]
    problem = f"{_SUPPORT_URL}={value!r}: expected mailto: and one email address, with nothing else"
    if not address or any(character.isspace() or character in _MAILTO_FORBIDDEN for character in address):
        raise ValueError(problem)
    try:
        return f"mailto:{_EMAIL.validate_python(address)}"
    except ValidationError as exc:
        raise ValueError(problem) from exc
