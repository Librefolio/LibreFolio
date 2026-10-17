"""The pauses of the price providers after «too many requests», for this process (decision 34, release 1.3).

Owner: workstream Z. One ``Cooldowns`` instance, keyed ``(domain, provider, scope)``: the domain is ``"asset"`` or
``"fx"``, the provider its code, the scope None or the part of a provider a refusal is about (the host of a scraped
site). The provider-call boundary of each domain asks ``wait_before_call`` before calling, and reports how the call
ended: ``record_refusal`` on a ``RateLimitedError``, ``record_success`` on an answer, ``record_no_verdict`` on any other
end (another error, a timeout, a cancellation), which frees the trial of an expired pause for the next caller.

The settings are read at every call (``config/sleep_wake.py``). With ``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0``
nothing is recorded and nothing is skipped, as before release 1.3. A setting that cannot be used is logged once, and
the defaults apply. ``PROVIDER_COOLDOWNS`` is read at call time, so a test can replace it.
"""

from __future__ import annotations

import threading

from backend.app.config.sleep_wake import (
    DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS,
    DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS,
    ProviderCooldownSettings,
    SleepWakeConfigError,
    provider_cooldown_settings,
)
from backend.app.logging_config import get_logger
from backend.app.utils.runtime.cooldown import Cooldowns

logger = get_logger(__name__)

PROVIDER_COOLDOWNS = Cooldowns(DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS, DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS)

_DEFAULT_SETTINGS = ProviderCooldownSettings(base_seconds=DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS, max_seconds=DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS)
_reported: set[tuple[str, str]] = set()
_reported_lock = threading.Lock()


def _settings() -> ProviderCooldownSettings:
    """The settings in force; the defaults when a value cannot be used, logged once per variable and problem."""
    try:
        return provider_cooldown_settings()
    except SleepWakeConfigError as exc:
        with _reported_lock:
            first = (exc.variable, exc.code) not in _reported
            _reported.add((exc.variable, exc.code))
        if first:
            logger.error("Provider pause settings cannot be used: the defaults apply", variable=exc.variable, code=exc.code, reason=str(exc), base_seconds=_DEFAULT_SETTINGS.base_seconds, max_seconds=_DEFAULT_SETTINGS.max_seconds)
        return _DEFAULT_SETTINGS


def wait_before_call(domain: str, provider: str, scope: str | None = None) -> float:
    """0 when ``provider`` may be called now; else the seconds of pause left, and the call is not to be made."""
    if not _settings().enabled:
        return 0.0
    wait = PROVIDER_COOLDOWNS.check((domain, provider, scope))
    if wait > 0:
        logger.debug("Provider call skipped: paused after too many requests", domain=domain, provider=provider, scope=scope, wait_s=round(wait, 1))
    return wait


def record_refusal(domain: str, provider: str, scope: str | None = None, retry_after: float | None = None) -> float:
    """``provider`` answered «too many requests»: pause it, and return the pause in seconds (0 with the pauses off)."""
    settings = _settings()
    if not settings.enabled:
        return 0.0
    wait = PROVIDER_COOLDOWNS.refused((domain, provider, scope), retry_after, base_seconds=settings.base_seconds, max_seconds=settings.max_seconds)
    logger.warning("Provider refused for too many requests: paused", domain=domain, provider=provider, scope=scope, wait_s=round(wait, 1), retry_after=retry_after)
    return wait


def record_success(domain: str, provider: str, scope: str | None = None) -> None:
    """``provider`` answered: its pause, if any, is over."""
    if not _settings().enabled:
        return
    refusals = PROVIDER_COOLDOWNS.succeeded((domain, provider, scope))
    if refusals:
        logger.info("Provider answering again after a pause", domain=domain, provider=provider, scope=scope, refusals=refusals)


def record_no_verdict(domain: str, provider: str, scope: str | None = None) -> None:
    """The call ended with neither an answer nor a refusal: the next caller may try."""
    if not _settings().enabled:
        return
    PROVIDER_COOLDOWNS.released((domain, provider, scope))
