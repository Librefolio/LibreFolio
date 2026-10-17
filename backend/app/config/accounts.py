"""Accounts section of the configuration.

Owner: workstream A (accounts). Read from the process environment only, never from ``.env``.
"""

import os
import string
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter, ValidationError

from backend.app.config import env_secret, env_url


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


LOGIN_LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"


def login_limit_value() -> str | None:
    """``LIBREFOLIO_LOGIN_LIMIT`` as set, stripped, or None when it is unset or blank: the value its check names."""
    return _blank_to_none(LOGIN_LIMIT_VARIABLE)


def login_limit_enabled() -> bool:
    """``LIBREFOLIO_LOGIN_LIMIT``: the limit on failed sign-ins (F15) is on unless this says ``off``.

    Unset, blank or ``on``, in any case: on. ``off``, in any case: off — for test instances, whose suites sign in
    wrongly on purpose from one address; the configuration checks then warn. Any other value raises ``ValueError``, naming
    it: the start stops on it. Read at each call.
    """
    value = login_limit_value()
    if value is None or value.lower() == "on":
        return True
    if value.lower() == "off":
        return False
    raise ValueError(f"{LOGIN_LIMIT_VARIABLE}={value!r}: expected on or off")


def public_url() -> str | None:
    """``LIBREFOLIO_PUBLIC_URL``: the address users reach the instance at, for links built outside a browser (CLI, email)."""
    return env_url("LIBREFOLIO_PUBLIC_URL")


def billing_url() -> str | None:
    """``LIBREFOLIO_BILLING_URL``: where the administrator manages the subscription of a managed instance."""
    return env_url("LIBREFOLIO_BILLING_URL")


# F02 — the initial administrator, created at startup on an instance without accounts (bootstrap_admin_service.py).
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
ADMIN_USERNAME_VARIABLE = "LIBREFOLIO_ADMIN_USERNAME"
ADMIN_BOOTSTRAP_TOKEN_VARIABLE = "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN"
DEFAULT_ADMIN_USERNAME = "admin"
#: The username rules of registration (``AuthRegisterRequest``).
ADMIN_USERNAME_MIN_LENGTH = 3
ADMIN_USERNAME_MAX_LENGTH = 50
#: The character no new username may hold (A-21a): the sign-in reads an identifier holding it as an email address first
#: (``user_service.get_user_by_username_or_email``). Registration, a change of username, ``./dev.py user create`` and
#: ``LIBREFOLIO_ADMIN_USERNAME`` refuse it; a username from before A-21a keeps it, and its account signs in by address.
USERNAME_RESERVED_CHARACTER = "@"
#: Why a new username holding it is refused, as the server says it (over HTTP with ``error_code`` ``USERNAME_INVALID``).
USERNAME_RESERVED_MESSAGE = "A username cannot contain @: the sign-in reads it as an email address"
#: The setup link opens the administrator account: a shorter token is refused, so a guessable value never does.
ADMIN_BOOTSTRAP_TOKEN_MIN_LENGTH = 32
#: The longest token the link's requests accept (``TokenInspectRequest``, ``AdminSetupRequest``).
ADMIN_BOOTSTRAP_TOKEN_MAX_LENGTH = 200
#: The unreserved characters of a URL: the token travels in a link (``/setup#token=…``) and must reach it as written.
ADMIN_BOOTSTRAP_TOKEN_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-._~")

_EMAIL = TypeAdapter(EmailStr)


class AdminBootstrapConfigError(ValueError):
    """An F02 variable that cannot be used: ``variable`` names it, ``code`` says what is wrong, never the token."""

    def __init__(self, variable: str, code: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable
        self.code = code


@dataclass(frozen=True)
class AdminBootstrapConfig:
    """The initial administrator the operator asked for; ``token`` is the setup link's, None for a generated one."""

    email: str
    username: str
    token: str | None


def _admin_bootstrap_token() -> str | None:
    """``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN``, or the content of its ``_FILE``; None when neither is set."""
    token = env_secret(ADMIN_BOOTSTRAP_TOKEN_VARIABLE)
    if token is None:
        return None
    if not ADMIN_BOOTSTRAP_TOKEN_CHARACTERS.issuperset(token):
        raise AdminBootstrapConfigError(
            ADMIN_BOOTSTRAP_TOKEN_VARIABLE,
            "ADMIN_BOOTSTRAP_TOKEN_INVALID_CHARACTERS",
            "expected letters, digits and - . _ ~ only, without spaces: the token travels in a link",
        )
    if len(token) < ADMIN_BOOTSTRAP_TOKEN_MIN_LENGTH:
        raise AdminBootstrapConfigError(
            ADMIN_BOOTSTRAP_TOKEN_VARIABLE,
            "ADMIN_BOOTSTRAP_TOKEN_TOO_SHORT",
            f"expected at least {ADMIN_BOOTSTRAP_TOKEN_MIN_LENGTH} characters, for example the output of `openssl rand -hex 32`",
        )
    if len(token) > ADMIN_BOOTSTRAP_TOKEN_MAX_LENGTH:
        raise AdminBootstrapConfigError(ADMIN_BOOTSTRAP_TOKEN_VARIABLE, "ADMIN_BOOTSTRAP_TOKEN_TOO_LONG", f"expected at most {ADMIN_BOOTSTRAP_TOKEN_MAX_LENGTH} characters")
    return token


def admin_bootstrap_config() -> AdminBootstrapConfig | None:
    """F02: the initial administrator of ``LIBREFOLIO_ADMIN_EMAIL``, read at every call; None while it is not set.

    ``LIBREFOLIO_ADMIN_USERNAME`` defaults to ``admin``; ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` (or its ``_FILE``) is the
    setup link's token, given by a hosting panel. A blank value counts as unset; spaces around the email and the
    username are ignored. A value that cannot be used raises ``AdminBootstrapConfigError``: a token or a username
    without the email, an email that is not an address, a username outside 3 to 50 characters or holding an ``@``
    (A-21a), a token of another character than the unreserved ones of a URL, shorter than 32 or longer than 200
    characters. A ``_FILE`` that cannot give its secret raises ``SecretFileError``. The startup audit calls it, so such
    a value stops the server.
    """
    email = _blank_to_none(ADMIN_EMAIL_VARIABLE)
    username = _blank_to_none(ADMIN_USERNAME_VARIABLE)
    token = _admin_bootstrap_token()
    if email is None:
        if token is not None:
            raise AdminBootstrapConfigError(
                ADMIN_BOOTSTRAP_TOKEN_VARIABLE,
                "ADMIN_BOOTSTRAP_TOKEN_WITHOUT_EMAIL",
                f"set {ADMIN_EMAIL_VARIABLE} too: the token is the setup link of that administrator",
            )
        if username is not None:
            raise AdminBootstrapConfigError(
                ADMIN_USERNAME_VARIABLE,
                "ADMIN_USERNAME_WITHOUT_EMAIL",
                f"set {ADMIN_EMAIL_VARIABLE} too: it is what turns the initial administrator on",
            )
        return None
    try:
        address = _EMAIL.validate_python(email)
    except ValidationError:
        raise AdminBootstrapConfigError(ADMIN_EMAIL_VARIABLE, "ADMIN_EMAIL_INVALID", "expected an email address") from None
    name = username or DEFAULT_ADMIN_USERNAME
    if not ADMIN_USERNAME_MIN_LENGTH <= len(name) <= ADMIN_USERNAME_MAX_LENGTH:
        raise AdminBootstrapConfigError(
            ADMIN_USERNAME_VARIABLE,
            "ADMIN_USERNAME_INVALID",
            f"expected {ADMIN_USERNAME_MIN_LENGTH} to {ADMIN_USERNAME_MAX_LENGTH} characters, as a username chosen at registration",
        )
    if USERNAME_RESERVED_CHARACTER in name:
        raise AdminBootstrapConfigError(
            ADMIN_USERNAME_VARIABLE,
            "ADMIN_USERNAME_INVALID",
            f"expected a username without {USERNAME_RESERVED_CHARACTER}, as registration asks: the sign-in reads a name with one as an email address, and the administrator signs in with {ADMIN_EMAIL_VARIABLE} anyway",
        )
    return AdminBootstrapConfig(email=address, username=name, token=token)
