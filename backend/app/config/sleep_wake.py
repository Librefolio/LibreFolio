"""Sleep-and-wake section of the configuration: how LibreFolio rests, wakes up and spares the remote services it calls.

Owner: workstream Z (sleep and wake, release 1.3). Read from the process environment only, never from ``.env`` nor
from the database, at the moment of use: a test, or a server restarted with new values, sees the value in force.

Every default leaves a self-hosted install as it was, except where a developer decision says otherwise:

- the pauses a provider gets after answering «too many requests» are on by default (decision 34, 15/10/2026: «a
  prescindere»); ``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0`` turns them off;
- the server has 8 seconds to stop after a SIGTERM or a SIGINT, for every install (decision 35, 15/10/2026);
  ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=0`` removes the limit. 0 gives back the behaviour before release 1.3 in both.

``LIBREFOLIO_WAKE_TOKEN`` (or its ``_FILE``, as Docker secrets mount it) turns on the scheduled wake-up,
``POST /api/v1/system/wake-sync``: unset, the route answers 404 as before release 1.3. ``LIBREFOLIO_IDLE_SUSPEND_MODE``
(``none`` by default) and ``LIBREFOLIO_IDLE_SUSPEND_MINUTES`` (5) let a Fly.io machine suspend itself when unused.

A value that cannot be used raises ``SleepWakeConfigError``, which names the variable and says what is wrong; the
caller decides what follows (``services/platform/provider_cooldown.py`` logs it once and keeps the defaults).
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from backend.app.config import env_secret
from backend.app.config.backup import PANEL_TOKEN_CHARACTERS, PANEL_TOKEN_MIN_LENGTH

DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS = 60
DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS = 3600
#: The longest pause a setting may ask for, one day: the ceiling of ``Cooldowns`` too.
PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS = 86_400

DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 8
SHUTDOWN_TIMEOUT_MIN_SECONDS = 2
SHUTDOWN_TIMEOUT_MAX_SECONDS = 600
#: The variable uvicorn reads for how long it waits for the requests in flight before cancelling them.
UVICORN_DRAIN_VARIABLE = "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN"

DEFAULT_IDLE_SUSPEND_MINUTES = 5
IDLE_SUSPEND_MINUTES_MAX = 1440
#: The values of ``LIBREFOLIO_IDLE_SUSPEND_MODE``: ``none`` never suspends, ``fly`` asks Fly.io's Machines API.
IDLE_SUSPEND_MODES = ("none", "fly")

#: The variable of the scheduled wake-up's token (``api/v1/system/wake.py``); ``env_secret`` also reads ``<name>_FILE``.
WAKE_TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"

_DIGITS = re.compile(r"[0-9]+")


class SleepWakeConfigError(ValueError):
    """A value of this section that cannot be used: ``variable`` names it, ``code`` says what is wrong."""

    def __init__(self, variable: str, code: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable
        self.code = code


@dataclass(frozen=True)
class ProviderCooldownSettings:
    """The pauses after a provider's «too many requests»: the first one and the longest, in seconds. Base 0 is off."""

    base_seconds: int
    max_seconds: int

    @property
    def enabled(self) -> bool:
        return self.base_seconds > 0


def _value(name: str, environ: Mapping[str, str] | None = None) -> str | None:
    """The variable ``name`` of ``environ`` (the process environment by default) stripped, or None when unset or blank.

    The process environment is read as ``os.environ.get(name)``, the form the ``.env.example`` guard follows through.
    """
    if environ is None:
        return os.environ.get(name, "").strip() or None
    return environ.get(name, "").strip() or None


def _seconds(name: str, code: str, default: int, minimum: int) -> int:
    raw = _value(name)
    if raw is None:
        return default
    if not _DIGITS.fullmatch(raw) or not minimum <= int(raw) <= PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS:
        raise SleepWakeConfigError(name, code, f"expected a whole number of seconds from {minimum} to {PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS}")
    return int(raw)


def provider_cooldown_base_seconds() -> int:
    """``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS``: the first pause after a refusal, doubled at each refusal in a row.

    60 when unset or blank; 0 turns the pauses off. At most 86400 (one day).
    """
    return _seconds("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "PROVIDER_COOLDOWN_BASE_INVALID", DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS, 0)


def provider_cooldown_max_seconds() -> int:
    """``LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS``: the longest pause the doubling reaches; 3600 when unset or blank.

    From 1 to 86400. A ``Retry-After`` sent by the provider may still ask for more, up to one day.
    """
    return _seconds("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "PROVIDER_COOLDOWN_MAX_INVALID", DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS, 1)


def provider_cooldown_settings() -> ProviderCooldownSettings:
    """Both settings of the pauses; with the pauses on, the longest may not be shorter than the first."""
    base = provider_cooldown_base_seconds()
    cap = provider_cooldown_max_seconds()
    if base > 0 and cap < base:
        raise SleepWakeConfigError("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "PROVIDER_COOLDOWN_MAX_INVALID", "must be at least LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS")
    return ProviderCooldownSettings(base_seconds=base, max_seconds=cap)


def shutdown_timeout_seconds(environ: Mapping[str, str] | None = None) -> int:
    """``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS``: how long the server may take to stop after a SIGTERM or a SIGINT.

    8 when unset or blank; 0 removes the limit; otherwise a whole number from 2 to 600. ``environ`` is the process
    environment by default; a launcher passes the one it prepares for the server.
    """
    raw = _value("LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS", environ)
    if raw is None:
        return DEFAULT_SHUTDOWN_TIMEOUT_SECONDS
    if not _DIGITS.fullmatch(raw) or not (int(raw) == 0 or SHUTDOWN_TIMEOUT_MIN_SECONDS <= int(raw) <= SHUTDOWN_TIMEOUT_MAX_SECONDS):
        raise SleepWakeConfigError("LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS", "SHUTDOWN_TIMEOUT_INVALID", f"expected 0 (no limit) or a whole number of seconds from {SHUTDOWN_TIMEOUT_MIN_SECONDS} to {SHUTDOWN_TIMEOUT_MAX_SECONDS}")
    return int(raw)


def shutdown_drain_seconds(budget: int) -> int | None:
    """The part of the shutdown budget uvicorn may spend draining the requests in flight: 3/8, at least 1 s.

    None with no limit (budget 0). ``entrypoint.sh`` makes the same sum in shell.
    """
    if budget == 0:
        return None
    return max(1, budget * 3 // 8)


def uvicorn_drain_env(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """What a launcher adds to the environment of uvicorn: its drain time, derived from the shutdown budget.

    Empty when ``UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN`` is already set (a value set by hand wins) or with no limit. A
    budget that cannot be used counts as the default: the server logs the bad value itself. Never raises.
    """
    if _value(UVICORN_DRAIN_VARIABLE, environ) is not None:
        return {}
    try:
        budget = shutdown_timeout_seconds(environ)
    except SleepWakeConfigError:
        budget = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS
    drain = shutdown_drain_seconds(budget)
    return {} if drain is None else {UVICORN_DRAIN_VARIABLE: str(drain)}


def wake_token() -> str | None:
    """``LIBREFOLIO_WAKE_TOKEN``, or the content of its ``_FILE``: the token of the scheduled wake-up, as written.

    ``None`` when neither is set: ``POST /api/v1/system/wake-sync`` is off and answers 404. The rules are those of the
    hosting panel's backup token (``config/backup.py``, decision D-W2): a token holding anything but visible ASCII
    characters raises ``SleepWakeConfigError`` ``WAKE_TOKEN_NOT_VISIBLE_ASCII``, one shorter than
    ``PANEL_TOKEN_MIN_LENGTH`` characters ``WAKE_TOKEN_TOO_SHORT``; a ``_FILE`` that cannot give its secret raises
    ``SecretFileError`` (``env_secret``). The value is never in a message.
    """
    token = env_secret(WAKE_TOKEN_VARIABLE)
    if token is None:
        return None
    if not PANEL_TOKEN_CHARACTERS.issuperset(token):
        raise SleepWakeConfigError(
            WAKE_TOKEN_VARIABLE,
            "WAKE_TOKEN_NOT_VISIBLE_ASCII",
            "expected visible ASCII characters only, without spaces: a request header carries nothing else as written",
        )
    if len(token) < PANEL_TOKEN_MIN_LENGTH:
        raise SleepWakeConfigError(
            WAKE_TOKEN_VARIABLE,
            "WAKE_TOKEN_TOO_SHORT",
            f"expected at least {PANEL_TOKEN_MIN_LENGTH} characters, for example the output of `openssl rand -hex 32`",
        )
    return token


def idle_suspend_mode() -> str:
    """``LIBREFOLIO_IDLE_SUSPEND_MODE``: ``none`` (unset or blank, the default: never suspend) or ``fly``, in any case.

    Any other value raises ``SleepWakeConfigError`` ``IDLE_SUSPEND_MODE_INVALID``; the idle monitor then never suspends.
    """
    raw = _value("LIBREFOLIO_IDLE_SUSPEND_MODE")
    if raw is None:
        return "none"
    mode = raw.lower()
    if mode not in IDLE_SUSPEND_MODES:
        raise SleepWakeConfigError("LIBREFOLIO_IDLE_SUSPEND_MODE", "IDLE_SUSPEND_MODE_INVALID", "expected none or fly")
    return mode


def idle_suspend_minutes() -> int:
    """``LIBREFOLIO_IDLE_SUSPEND_MINUTES``: the minutes without a request of the user before a suspension, 1 to 1440.

    5 when unset or blank (developer decision 32). Any other value raises ``SleepWakeConfigError``
    ``IDLE_SUSPEND_MINUTES_INVALID``. Used only with ``LIBREFOLIO_IDLE_SUSPEND_MODE=fly``.
    """
    raw = _value("LIBREFOLIO_IDLE_SUSPEND_MINUTES")
    if raw is None:
        return DEFAULT_IDLE_SUSPEND_MINUTES
    if not _DIGITS.fullmatch(raw) or not 1 <= int(raw) <= IDLE_SUSPEND_MINUTES_MAX:
        raise SleepWakeConfigError("LIBREFOLIO_IDLE_SUSPEND_MINUTES", "IDLE_SUSPEND_MINUTES_INVALID", f"expected whole minutes from 1 to {IDLE_SUSPEND_MINUTES_MAX}")
    return int(raw)


def fly_machine_identity(environ: Mapping[str, str] | None = None) -> tuple[str, str] | None:
    """The app and the machine of this Fly.io machine, ``FLY_APP_NAME`` and ``FLY_MACHINE_ID``; None off Fly.

    Fly sets both on every machine: they are not options of LibreFolio. The idle suspension reads them
    (``services/platform/sleep_wake/suspend.py``); ``environ`` replaces the process environment in tests.
    """
    app = _value("FLY_APP_NAME", environ)
    machine = _value("FLY_MACHINE_ID", environ)
    if app is None or machine is None:
        return None
    return app, machine
