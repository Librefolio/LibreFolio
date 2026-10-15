"""Accounts section of the configuration.

Owner: workstream A (accounts). Read from the process environment only, never from ``.env``.
"""

import os


def donation_popup_disabled() -> bool:
    """``LIBREFOLIO_DISABLE_DONATION_POPUP``: ``1``, ``true`` or ``yes``, in any case, turns the donation popup off."""
    return os.environ.get("LIBREFOLIO_DISABLE_DONATION_POPUP", "").lower() in ("1", "true", "yes")


REGISTRATION_MODES: tuple[str, ...] = ("open", "invite", "disabled")


def _blank_to_none(name: str) -> str | None:
    """The variable ``name`` stripped, or None when it is unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or None


def registration_mode_override() -> str | None:
    """``LIBREFOLIO_REGISTRATION``: who may create an account, pinned by the operator (``open``, ``invite`` or ``disabled``).

    None when unset or blank: the ``registration_mode`` global setting decides. Any other value raises ``ValueError``.
    """
    value = _blank_to_none("LIBREFOLIO_REGISTRATION")
    if value is None:
        return None
    mode = value.lower()
    if mode not in REGISTRATION_MODES:
        raise ValueError(f"LIBREFOLIO_REGISTRATION={value!r}: expected one of {', '.join(REGISTRATION_MODES)}")
    return mode


def registration_mode_pinned() -> bool:
    """Whether ``LIBREFOLIO_REGISTRATION`` is set at all, valid or not: the global setting is then read-only."""
    return _blank_to_none("LIBREFOLIO_REGISTRATION") is not None


def max_users() -> int | None:
    """``LIBREFOLIO_MAX_USERS``: how many accounts the instance may hold (active users plus pending invitations).

    None when unset or blank: no limit. A whole number of at least 1 otherwise; any other value raises ``ValueError``.
    """
    value = _blank_to_none("LIBREFOLIO_MAX_USERS")
    if value is None:
        return None
    try:
        limit = int(value)
    except ValueError:
        raise ValueError(f"LIBREFOLIO_MAX_USERS={value!r}: expected a whole number of at least 1") from None
    if limit < 1:
        raise ValueError(f"LIBREFOLIO_MAX_USERS={value!r}: expected a whole number of at least 1")
    return limit


def _url(name: str) -> str | None:
    """The http(s) URL in the variable ``name``, one trailing slash removed; None when unset or blank."""
    value = _blank_to_none(name)
    if value is None:
        return None
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError(f"{name}={value!r}: expected an http:// or https:// address")
    return value[:-1] if value.endswith("/") else value


def public_url() -> str | None:
    """``LIBREFOLIO_PUBLIC_URL``: the address users reach the instance at, for links built outside a browser (CLI, email)."""
    return _url("LIBREFOLIO_PUBLIC_URL")


def billing_url() -> str | None:
    """``LIBREFOLIO_BILLING_URL``: where the administrator manages the subscription of a managed instance."""
    return _url("LIBREFOLIO_BILLING_URL")
