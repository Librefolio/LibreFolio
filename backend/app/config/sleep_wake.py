"""Sleep-and-wake section of the configuration: how LibreFolio rests, wakes up and spares the remote services it calls.

Owner: workstream Z (sleep and wake, release 1.3). Read from the process environment only, never from ``.env`` nor
from the database, at the moment of use: a test, or a server restarted with new values, sees the value in force.

Every default leaves a self-hosted install as it was, except where a developer decision says otherwise. The pauses a
provider gets after answering «too many requests» are on by default (decision 34, 15/10/2026: «a prescindere»);
``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0`` turns them off and gives back the behaviour before release 1.3.

A value that cannot be used raises ``SleepWakeConfigError``, which names the variable and says what is wrong; the
caller decides what follows (``services/platform/provider_cooldown.py`` logs it once and keeps the defaults).
"""

import os
import re
from dataclasses import dataclass

DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS = 60
DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS = 3600
#: The longest pause a setting may ask for, one day: the ceiling of ``Cooldowns`` too.
PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS = 86_400

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


def _value(name: str) -> str | None:
    """The variable ``name`` stripped, or None when it is unset or blank."""
    return os.environ.get(name, "").strip() or None


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
