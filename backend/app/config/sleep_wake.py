"""Sleep-and-wake section of the configuration: how LibreFolio rests, wakes up and spares the remote services it calls.

Owner: workstream Z (sleep and wake, release 1.3). Read from the process environment only, never from ``.env`` nor
from the database, at the moment of use: a test, or a server restarted with new values, sees the value in force.

Every default leaves a self-hosted install as it was, except where a developer decision says otherwise:

- the pauses a provider gets after answering «too many requests» are on by default (decision 34, 15/10/2026: «a
  prescindere»); ``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0`` turns them off;
- the server has 8 seconds to stop after a SIGTERM or a SIGINT, for every install (decision 35, 15/10/2026);
  ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=0`` removes the limit. 0 gives back the behaviour before release 1.3 in both.

A value that cannot be used raises ``SleepWakeConfigError``, which names the variable and says what is wrong; the
caller decides what follows (``services/platform/provider_cooldown.py`` logs it once and keeps the defaults).
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS = 60
DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS = 3600
#: The longest pause a setting may ask for, one day: the ceiling of ``Cooldowns`` too.
PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS = 86_400

DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 8
SHUTDOWN_TIMEOUT_MIN_SECONDS = 2
SHUTDOWN_TIMEOUT_MAX_SECONDS = 600
#: The variable uvicorn reads for how long it waits for the requests in flight before cancelling them.
UVICORN_DRAIN_VARIABLE = "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN"

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
