"""``backend.app.config.sleep_wake`` and ``backend.app.services.platform.provider_cooldown``: the process's provider pauses and their two variables (plan phase01SleepWake §Z7a, decision 34, lot Z7a).

A provider that answers HTTP 429 is paused for every caller of the process, through one ``Cooldowns`` instance keyed by
``(domain, provider, scope)``; two variables of Z's section of the configuration size the pauses, and 0 switches them
off. The contract pinned here:

1. ``config.sleep_wake``: ``DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS`` 60, ``DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS``
   3600, ``PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS`` 86 400; ``SleepWakeConfigError(variable, code, message)``, a
   ``ValueError`` carrying ``variable`` and ``code``, its message naming the variable.
2. ``provider_cooldown_base_seconds()``: ``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS``, stripped; unset or blank is
   60; a whole number from 0 (pauses off) to 86 400; anything else ``PROVIDER_COOLDOWN_BASE_INVALID``.
3. ``provider_cooldown_max_seconds()``: ``LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS``; unset or blank is 3600; a whole
   number from 1 to 86 400; anything else ``PROVIDER_COOLDOWN_MAX_INVALID``.
4. ``provider_cooldown_settings()``: ``ProviderCooldownSettings(base_seconds, max_seconds)``, frozen, ``enabled`` when
   the base is above 0. Pauses on, a max below the base is ``PROVIDER_COOLDOWN_MAX_INVALID`` on the max's variable; an
   invalid variable raises its own error. Every accessor reads the environment at each call.
5. ``provider_cooldown.PROVIDER_COOLDOWNS``: a ``Cooldowns`` built with the defaults, read by every function at call
   time; the key of a provider is ``(domain, provider, scope)``, and keys pause apart. A fresh ``Cooldowns`` put in its
   place is therefore how a test starts clean — the module has no function that forgets the pauses (N58) —: every
   function then works on that one alone, and the instance it replaced keeps its own.
6. ``wait_before_call`` is ``check``; ``record_refusal`` is ``refused`` with the base and max of
   ``provider_cooldown_settings()`` read at each call and ``retry_after`` passed on; ``record_success`` is ``succeeded``;
   ``record_no_verdict`` is ``released``. So the answers of calls already in flight when a pause began — a burst of
   429s, a late success — change nothing (``Cooldowns``' rule for a running pause): refusals in a row are those of
   calls made after each pause ended.
7. Pauses off (base 0): nothing is skipped — ``wait_before_call`` is always 0, even for a pause recorded before — and
   nothing is recorded — ``record_refusal`` returns 0 —; ``record_success`` and ``record_no_verdict`` do nothing.
8. An invalid configuration never makes a function raise: they work on the defaults, 60 and 3600, and the fault is
   logged as one error event per (variable, code) per process, naming the variable — another value for the same
   variable and code is not logged again.

Pure: no database, no server, no network. An autouse fixture removes every ``LIBREFOLIO_PROVIDER_COOLDOWN_*`` the lane
may have inherited, and each test sets its own with ``monkeypatch``; another replaces
``provider_cooldown.PROVIDER_COOLDOWNS`` with a private ``Cooldowns(60, 3600)`` on a fake clock and a random source
fixed at 0, so the process's instance is never paused by a test. What the functions recorded is read on the instance
they wrote to, ``snapshot()`` and ``len()`` of the one in place: the module has no function that reads its pauses
(N58). "Once per process" is checked in a fresh interpreter (``sys.executable``, run in ``tmp_path``), where nothing
was logged before: its environment is a copy of this one, and it is the only test that waits for anything — that
interpreter's start, about half a second.

Red until ``backend/app/config/sleep_wake.py``, ``backend/app/utils/runtime/cooldown.py`` and
``backend/app/services/platform/provider_cooldown.py`` exist: the modules do not import.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from backend.app.config.sleep_wake import (
    DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS,
    DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS,
    PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS,
    ProviderCooldownSettings,
    SleepWakeConfigError,
    provider_cooldown_base_seconds,
    provider_cooldown_max_seconds,
    provider_cooldown_settings,
)
from backend.app.services.platform import provider_cooldown
from backend.app.services.platform.provider_cooldown import (
    record_no_verdict,
    record_refusal,
    record_success,
    wait_before_call,
)
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Written out, not imported: the fixture that empties the environment must not trust the module under test.
COOLDOWN_PREFIX = "LIBREFOLIO_PROVIDER_COOLDOWN_"
BASE_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS"
MAX_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS"
BASE_INVALID = "PROVIDER_COOLDOWN_BASE_INVALID"
MAX_INVALID = "PROVIDER_COOLDOWN_MAX_INVALID"

START = 1_000.0
#: The first refusals in a row on the defaults, without jitter: 60 s doubling, an hour at most.
DOUBLING = [60.0, 120.0, 240.0, 480.0, 960.0, 1_920.0, 3_600.0, 3_600.0]

#: What the module ships with, read at import, before any fixture replaces it.
SHIPPED_COOLDOWNS = getattr(provider_cooldown, "PROVIDER_COOLDOWNS", None)

ACCESSORS = [
    pytest.param(BASE_VARIABLE, provider_cooldown_base_seconds, 60, id="base"),
    pytest.param(MAX_VARIABLE, provider_cooldown_max_seconds, 3_600, id="max"),
]

#: ``(BASE, MAX)`` pairs ``provider_cooldown_settings()`` refuses (``None``: unset).
INVALID_CONFIGURATIONS = [
    pytest.param("abc", None, id="base-not-a-number"),
    pytest.param("-1", None, id="base-negative"),
    pytest.param("86401", None, id="base-above-the-limit"),
    pytest.param(None, "0", id="max-0"),
    pytest.param(None, "86401", id="max-above-the-limit"),
    pytest.param("100", "50", id="max-below-base"),
    pytest.param("10", "0", id="valid-base-beside-an-invalid-max"),
]


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _no_inherited_cooldown_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_PROVIDER_COOLDOWN_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(COOLDOWN_PREFIX):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def cooldowns(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> Cooldowns:
    """A private instance on the fake clock, without jitter, in place of the process's: no test pauses, or depends on, the shipped one."""
    private = Cooldowns(60, 3600, clock=clock, rng=lambda: 0.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


def _set(monkeypatch: pytest.MonkeyPatch, base: str | None, maximum: str | None) -> None:
    """Both variables as given, ``None`` leaving one unset."""
    for name, value in ((BASE_VARIABLE, base), (MAX_VARIABLE, maximum)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _refusals(clock: FakeClock, domain: str, provider: str, count: int, *, scope: str | None = None) -> list[float]:
    """``count`` refusals in a row as a provider boundary records them, and their waits.

    Refusals in a row are those of calls made after each pause ended: each one here answers the trial call
    ``wait_before_call`` lets through once the previous pause is over. The clock is left at the end of the last pause.
    """
    waits = []
    for _ in range(count):
        assert wait_before_call(domain, provider, scope=scope) == 0.0, f"no trial let through for {(domain, provider, scope)} at {clock.now}"
        wait = record_refusal(domain, provider, scope=scope)
        waits.append(wait)
        clock.now += wait
    return waits


def _texts(value: object) -> Iterator[str]:
    """Every piece of text in a decoded log event: its keys, and each leaf as ``str``."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _texts(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _texts(item)
    else:
        yield str(value)


def _holds(value: object, needle: str) -> bool:
    return any(needle in text for text in _texts(value))


# =============================================================================
# 1-4. config.sleep_wake
# =============================================================================


def test_the_section_constants_and_its_error() -> None:
    """PCD-001 — contract 1: the defaults 60 and 3600 and the limit 86 400; ``SleepWakeConfigError`` is a ``ValueError`` with ``variable`` and ``code``, its message naming the variable."""
    print_section("PCD-001: constants and SleepWakeConfigError")

    assert (DEFAULT_PROVIDER_COOLDOWN_BASE_SECONDS, DEFAULT_PROVIDER_COOLDOWN_MAX_SECONDS, PROVIDER_COOLDOWN_MAX_LIMIT_SECONDS) == (60, 3_600, 86_400)
    assert issubclass(SleepWakeConfigError, ValueError)
    error = SleepWakeConfigError(BASE_VARIABLE, BASE_INVALID, "expected a whole number from 0 to 86400")
    assert (error.variable, error.code) == (BASE_VARIABLE, BASE_INVALID)
    assert BASE_VARIABLE in str(error)
    print_success("60, 3600, 86400; a ValueError naming its variable")


@pytest.mark.parametrize("value", [None, "", "   "], ids=["unset", "empty", "blank"])
@pytest.mark.parametrize(("variable", "accessor", "default"), ACCESSORS)
def test_a_blank_variable_takes_the_default(monkeypatch: pytest.MonkeyPatch, variable: str, accessor: Callable[[], int], default: int, value: str | None) -> None:
    """PCD-002 — contracts 2 and 3: unset, empty or blank is the default — 60 for the base, 3600 for the max."""
    print_section(f"PCD-002: {variable}={value!r}")
    if value is not None:
        monkeypatch.setenv(variable, value)

    assert accessor() == default
    print_success(f"{default}")


@pytest.mark.parametrize(("value", "expected"), [("0", 0), ("1", 1), ("60", 60), (" 90 ", 90), ("7200", 7_200), ("86400", 86_400)])
def test_the_base_is_a_whole_number_from_0_to_86400(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """PCD-003 — contract 2: digits, stripped, from 0 — pauses off — to the limit; an ``int``. Above the default max is the base's own business: the pair is the settings' (PCD-009)."""
    print_section(f"PCD-003: base {value!r}")
    monkeypatch.setenv(BASE_VARIABLE, value)

    result = provider_cooldown_base_seconds()
    assert result == expected and type(result) is int
    print_success(f"{expected}")


@pytest.mark.parametrize("value", ["abc", "-1", "1.5", "+5", "86401", "99999999999999999999", "60s", "1_0", "\uff11\uff10"])
def test_the_base_refuses_anything_else(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """PCD-004 — contract 2: a word, a negative, a decimal, a sign, a value above 86 400, a unit, Python's digit separator or non-ASCII digits are ``PROVIDER_COOLDOWN_BASE_INVALID`` on the base's variable, never a guess."""
    print_section(f"PCD-004: base {value!r}")
    monkeypatch.setenv(BASE_VARIABLE, value)

    with pytest.raises(SleepWakeConfigError) as caught:
        provider_cooldown_base_seconds()
    assert (caught.value.variable, caught.value.code) == (BASE_VARIABLE, BASE_INVALID)
    assert BASE_VARIABLE in str(caught.value)
    print_success(BASE_INVALID)


@pytest.mark.parametrize(("value", "expected"), [("1", 1), ("40", 40), (" 7200 ", 7_200), ("86400", 86_400)])
def test_the_max_is_a_whole_number_from_1_to_86400(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """PCD-005 — contract 3: digits, stripped, from 1 to the limit; an ``int``."""
    print_section(f"PCD-005: max {value!r}")
    monkeypatch.setenv(MAX_VARIABLE, value)

    result = provider_cooldown_max_seconds()
    assert result == expected and type(result) is int
    print_success(f"{expected}")


@pytest.mark.parametrize("value", ["0", "86401", "abc", "-3", "1.5", "+5", "1h", "1_0", "\uff11\uff10"])
def test_the_max_refuses_anything_else(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """PCD-006 — contract 3: 0, a value above 86 400, a word, a negative, a decimal, a sign, a unit, Python's digit separator or non-ASCII digits are ``PROVIDER_COOLDOWN_MAX_INVALID`` on the max's variable."""
    print_section(f"PCD-006: max {value!r}")
    monkeypatch.setenv(MAX_VARIABLE, value)

    with pytest.raises(SleepWakeConfigError) as caught:
        provider_cooldown_max_seconds()
    assert (caught.value.variable, caught.value.code) == (MAX_VARIABLE, MAX_INVALID)
    assert MAX_VARIABLE in str(caught.value)
    print_success(MAX_INVALID)


def test_provider_cooldown_settings_is_a_frozen_pair_with_enabled() -> None:
    """PCD-007 — contract 4: two fields in order, compared by value, never edited; ``enabled`` exactly when the base is above 0."""
    print_section("PCD-007: ProviderCooldownSettings")

    assert [field.name for field in dataclasses.fields(ProviderCooldownSettings)] == ["base_seconds", "max_seconds"]
    settings = ProviderCooldownSettings(60, 3_600)
    assert settings == ProviderCooldownSettings(base_seconds=60, max_seconds=3_600)
    assert (settings.enabled, ProviderCooldownSettings(1, 1).enabled, ProviderCooldownSettings(0, 3_600).enabled) == (True, True, False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.base_seconds = 0  # type: ignore[misc]
    print_success("frozen (base_seconds, max_seconds), enabled = base > 0")


@pytest.mark.parametrize(
    ("base", "maximum", "expected", "enabled"),
    [
        pytest.param(None, None, (60, 3_600), True, id="defaults"),
        pytest.param("10", "40", (10, 40), True, id="both-set"),
        pytest.param("40", "40", (40, 40), True, id="max-equal-to-base"),
        pytest.param("86400", "86400", (86_400, 86_400), True, id="both-at-the-limit"),
        pytest.param("0", None, (0, 3_600), False, id="off"),
        # A max is never below a base of 0 (it is at least 1): the closest case of "off, the pair rule does not apply".
        pytest.param("0", "1", (0, 1), False, id="off-with-the-smallest-max"),
    ],
)
def test_provider_cooldown_settings_reads_both(monkeypatch: pytest.MonkeyPatch, base: str | None, maximum: str | None, expected: tuple[int, int], enabled: bool) -> None:
    """PCD-008 — contract 4: the two accessors together, with ``enabled`` following the base."""
    print_section(f"PCD-008: base {base!r}, max {maximum!r}")
    _set(monkeypatch, base, maximum)

    settings = provider_cooldown_settings()
    assert settings == ProviderCooldownSettings(*expected)
    assert settings.enabled is enabled
    print_success(f"{expected}, enabled {enabled}")


@pytest.mark.parametrize(
    ("base", "maximum", "variable", "code"),
    [
        pytest.param("100", "50", MAX_VARIABLE, MAX_INVALID, id="max-below-base"),
        pytest.param("7200", None, MAX_VARIABLE, MAX_INVALID, id="default-max-below-base"),
        pytest.param("abc", None, BASE_VARIABLE, BASE_INVALID, id="base-invalid"),
        pytest.param(None, "0", MAX_VARIABLE, MAX_INVALID, id="max-invalid"),
    ],
)
def test_provider_cooldown_settings_refuses_an_unusable_pair(monkeypatch: pytest.MonkeyPatch, base: str | None, maximum: str | None, variable: str, code: str) -> None:
    """PCD-009 — contract 4: pauses on, a max below the base — written, or the default 3600 under a base of 7200 — is ``PROVIDER_COOLDOWN_MAX_INVALID`` on the max's variable; an invalid variable raises its own error."""
    print_section(f"PCD-009: base {base!r}, max {maximum!r}")
    _set(monkeypatch, base, maximum)

    with pytest.raises(SleepWakeConfigError) as caught:
        provider_cooldown_settings()
    assert (caught.value.variable, caught.value.code) == (variable, code)
    print_success(f"{code} on {variable}")


def test_every_accessor_reads_the_environment_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """PCD-010 — contract 4: a change of either variable is seen by the next call, and so is its removal: nothing is cached."""
    print_section("PCD-010: read at each call")

    def read() -> tuple[int, int, ProviderCooldownSettings]:
        return provider_cooldown_base_seconds(), provider_cooldown_max_seconds(), provider_cooldown_settings()

    _set(monkeypatch, "10", "40")
    assert read() == (10, 40, ProviderCooldownSettings(10, 40))
    _set(monkeypatch, "20", "80")
    assert read() == (20, 80, ProviderCooldownSettings(20, 80))
    _set(monkeypatch, None, None)
    assert read() == (60, 3_600, ProviderCooldownSettings(60, 3_600))
    print_success("10/40, 20/80, then the defaults")


# =============================================================================
# 5-6. THE PROCESS'S INSTANCE AND ITS FUNCTIONS
# =============================================================================


def test_the_process_instance_is_a_cooldowns_built_with_the_defaults() -> None:
    """PCD-011 — contract 5: ``PROVIDER_COOLDOWNS``, as shipped, is a ``Cooldowns``; refused once on a key of this test's own, on the real clock and random source, it waits 60 to 66 s — the base of 60 and a jitter of 10 % at most — and the key is removed at once."""
    print_section("PCD-011: PROVIDER_COOLDOWNS as shipped")

    assert isinstance(SHIPPED_COOLDOWNS, Cooldowns)
    key = ("asset", "pcd-011-probe", None)
    try:
        wait = SHIPPED_COOLDOWNS.refused(key)
        assert 60.0 <= wait <= 66.0
        assert 0.0 < SHIPPED_COOLDOWNS.check(key) <= wait
    finally:
        SHIPPED_COOLDOWNS.reset(key)
    assert SHIPPED_COOLDOWNS.check(key) == 0.0
    print_success(f"a Cooldowns; a first wait of {wait:.3f} s")


def test_the_functions_use_the_instance_of_the_moment_keyed_by_domain_provider_scope(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-012 — contracts 5 and 6: the instance put in place after the import receives the refusals, under ``(domain, provider, scope)``, and ``wait_before_call`` reads its pauses; replaced again mid-test, the next call goes to the new one — nothing to wait for there, the next refusal recorded there — and the one replaced keeps its two keys. The shipped instance is never touched."""
    print_section("PCD-012: the instance of the moment, (domain, provider, scope)")
    shipped_keys = len(SHIPPED_COOLDOWNS)

    assert record_refusal("asset", "yfinance") == 60.0
    assert record_refusal("asset", "css_scraper", scope="example.com") == 60.0
    assert {state.key for state in cooldowns.snapshot()} == {("asset", "yfinance", None), ("asset", "css_scraper", "example.com")}
    assert cooldowns.check(("asset", "yfinance", None)) == 60.0
    assert wait_before_call("asset", "yfinance") == 60.0

    replacement = Cooldowns(60, 3600, clock=clock, rng=lambda: 0.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", replacement)
    assert wait_before_call("asset", "yfinance") == 0.0
    assert record_refusal("fx", "ECB") == 60.0
    assert [state.key for state in replacement.snapshot()] == [("fx", "ECB", None)]
    assert len(cooldowns) == 2
    assert len(SHIPPED_COOLDOWNS) == shipped_keys
    print_success("keys (domain, provider, scope); the instance read at each call")


def test_wait_before_call_counts_the_pause_down_and_lets_one_trial_through(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-013 — contract 6: after a refusal at 1000, ``wait_before_call`` gives 60, then 45 s at 1015; at 1060 one trial goes and the next caller waits the trial window; ``record_success`` forgets the provider: nothing to wait for, nothing tracked."""
    print_section("PCD-013: wait_before_call and record_success")

    assert record_refusal("asset", "yfinance") == 60.0
    assert wait_before_call("asset", "yfinance") == 60.0
    clock.now = 1_015.0
    assert wait_before_call("asset", "yfinance") == 45.0
    clock.now = 1_060.0
    assert wait_before_call("asset", "yfinance") == 0.0
    assert wait_before_call("asset", "yfinance") == 60.0
    assert record_success("asset", "yfinance") is None
    assert (wait_before_call("asset", "yfinance"), wait_before_call("asset", "yfinance")) == (0.0, 0.0)
    assert cooldowns.snapshot() == ()
    print_success("60, 45, a trial, then forgotten on success")


def test_record_no_verdict_frees_the_trial_and_keeps_the_count(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-014 — contract 6: the trial at the end of a pause ends without a verdict: the next caller is the new trial, and a refusal of it is the second in a row, 120 s."""
    print_section("PCD-014: record_no_verdict")

    assert record_refusal("fx", "ECB") == 60.0
    clock.now = 1_060.0
    assert wait_before_call("fx", "ECB") == 0.0
    assert wait_before_call("fx", "ECB") == 60.0
    assert record_no_verdict("fx", "ECB") is None
    assert wait_before_call("fx", "ECB") == 0.0
    assert record_refusal("fx", "ECB") == 120.0
    print_success("trial freed, count kept")


def test_domains_providers_and_scopes_pause_apart(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-015 — contract 5: a refusal for one site of ``css_scraper`` pauses that site only — not another site, not the provider without a scope, not the same name in another domain, not another provider on the same site —; outcomes recorded for those leave it paused."""
    print_section("PCD-015: independent keys")

    assert record_refusal("asset", "css_scraper", scope="example.com") == 60.0
    clock.now = 1_010.0
    others = [("asset", "css_scraper", "other.org"), ("asset", "css_scraper", None), ("fx", "css_scraper", "example.com"), ("asset", "yfinance", "example.com")]
    assert [wait_before_call(domain, provider, scope=scope) for domain, provider, scope in others] == [0.0] * len(others)
    record_success("asset", "css_scraper", scope="other.org")
    record_no_verdict("asset", "css_scraper")
    assert wait_before_call("asset", "css_scraper", scope="example.com") == 50.0
    assert len(cooldowns) == 1
    print_success("one site paused, everything else free")


def test_record_refusal_reads_base_and_max_at_each_call(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-016 — contract 6: with ``BASE=10`` and ``MAX=40`` four refusals in a row wait 10, 20, 40, 40; set to 100 and 1000, the fifth waits ``min(100 × 2^4, 1000)`` and another provider's first waits 100."""
    print_section("PCD-016: base and max read at each refusal")

    _set(monkeypatch, "10", "40")
    assert _refusals(clock, "asset", "yfinance", 4) == [10.0, 20.0, 40.0, 40.0]
    _set(monkeypatch, "100", "1000")
    assert _refusals(clock, "asset", "yfinance", 1) == [1_000.0]
    assert _refusals(clock, "asset", "justetf", 1) == [100.0]
    print_success("10, 20, 40, 40, then 1000 and 100")


def test_record_refusal_passes_retry_after_on(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns) -> None:
    """PCD-017 — contract 6: a ``Retry-After`` of 500 s outweighs a base of 10 and a max of 40; one of 200 000 s stops at the hard max, 24 h."""
    print_section("PCD-017: retry_after passed on")

    _set(monkeypatch, "10", "40")
    assert record_refusal("asset", "yfinance", retry_after=500.0) == 500.0
    assert wait_before_call("asset", "yfinance") == 500.0
    assert record_refusal("fx", "ECB", retry_after=200_000.0) == 86_400.0
    print_success("500 s, then 86 400 s")


def test_answers_of_calls_in_flight_when_a_pause_began_change_nothing(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-023 — contract 6: the asset list asks up to five prices of one provider at once. All five come back 429 at 1000: each ``record_refusal`` answers 60 s, and one refusal is counted. A success of a call that left before the pause, arriving at 1030, does not lift it: 30 s still to wait. Once it is over, the next refusal is the second in a row, 120 s — not the sixth."""
    print_section("PCD-023: a burst of 429s and a late success")

    assert [record_refusal("asset", "yfinance") for _ in range(5)] == [60.0] * 5
    assert [(state.key, state.refusals) for state in cooldowns.snapshot()] == [(("asset", "yfinance", None), 1)]
    clock.now = 1_030.0
    assert record_success("asset", "yfinance") is None
    assert wait_before_call("asset", "yfinance") == 30.0

    clock.now = 1_060.0
    assert _refusals(clock, "asset", "yfinance", 1) == [120.0]
    assert [state.refusals for state in cooldowns.snapshot()] == [2]
    print_success("five 429s, one refusal; the late success ignored; then 120 s")


def test_a_fresh_instance_put_in_place_forgets_every_pause(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns, clock: FakeClock) -> None:
    """PCD-018 — contract 5: the module has no function that forgets the pauses (N58): a test puts a fresh ``Cooldowns`` in place of ``PROVIDER_COOLDOWNS``, and every function reads that one. Pauses in both domains, with and without a scope, a second refusal in a row among them, are gone from every function's view — nothing to wait for, nothing for a success or an outcome without a verdict to find, and the next refusal the first in a row, 60 s, not the third, 240 s —; the instance replaced keeps them all."""
    print_section("PCD-018: a fresh instance in place forgets every pause")
    keys = [("asset", "yfinance", None), ("fx", "ECB", None), ("asset", "css_scraper", "example.com")]
    for domain, provider, scope in keys:
        assert record_refusal(domain, provider, scope=scope) == 60.0
    clock.now = 1_060.0
    assert _refusals(clock, "asset", "yfinance", 1) == [120.0]
    before = cooldowns.snapshot()
    assert {(state.key, state.refusals) for state in before} == {(keys[0], 2), (keys[1], 1), (keys[2], 1)}, "barrier: three pauses, a second refusal in a row among them"

    fresh = Cooldowns(60, 3600, clock=clock, rng=lambda: 0.0)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", fresh)

    assert [wait_before_call(domain, provider, scope=scope) for domain, provider, scope in keys] == [0.0] * len(keys)
    assert record_success("asset", "yfinance") is None
    assert record_no_verdict("fx", "ECB") is None
    assert len(fresh) == 0
    assert record_refusal("asset", "yfinance") == 60.0
    assert [state.key for state in fresh.snapshot()] == [keys[0]]
    assert cooldowns.snapshot() == before
    print_success("every pause gone from the functions' view; the replaced instance untouched")


# =============================================================================
# 7. PAUSES OFF
# =============================================================================


def test_with_pauses_off_nothing_is_recorded_and_nothing_skipped(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns) -> None:
    """PCD-019 — contract 7: with ``BASE=0`` a refusal — with or without ``Retry-After`` — returns 0 and records nothing; every call may go; a success and an outcome without a verdict raise nothing and record nothing."""
    print_section("PCD-019: pauses off")
    monkeypatch.setenv(BASE_VARIABLE, "0")

    assert record_refusal("asset", "yfinance") == 0.0
    assert record_refusal("asset", "yfinance", retry_after=500.0) == 0.0
    assert (len(cooldowns), cooldowns.snapshot()) == (0, ())
    assert wait_before_call("asset", "yfinance") == 0.0
    assert record_success("asset", "yfinance") is None
    assert record_no_verdict("asset", "yfinance") is None
    assert len(cooldowns) == 0
    print_success("nothing recorded, nothing skipped")


def test_switched_off_a_pause_recorded_before_skips_nothing(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns) -> None:
    """PCD-020 — contract 7: a pause recorded while on stops holding calls back as soon as ``BASE=0`` is read, and a refusal then adds nothing to it."""
    print_section("PCD-020: switched off over a running pause")

    assert record_refusal("asset", "yfinance") == 60.0
    monkeypatch.setenv(BASE_VARIABLE, "0")
    assert wait_before_call("asset", "yfinance") == 0.0
    assert record_refusal("asset", "yfinance") == 0.0
    assert [(state.key, state.refusals) for state in cooldowns.snapshot()] == [(("asset", "yfinance", None), 1)]
    print_success("0 while off; the recorded refusal untouched")


# =============================================================================
# 8. AN INVALID CONFIGURATION
# =============================================================================


@pytest.mark.parametrize(("base", "maximum"), INVALID_CONFIGURATIONS)
def test_an_invalid_configuration_never_raises_and_falls_back_to_the_defaults(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns, clock: FakeClock, base: str | None, maximum: str | None) -> None:
    """PCD-021 — contract 8: once ``provider_cooldown_settings()`` refuses the configuration — whichever variable is at fault, a valid base beside an invalid max included — every function still works, on 60 s doubling up to an hour."""
    print_section(f"PCD-021: base {base!r}, max {maximum!r}")
    _set(monkeypatch, base, maximum)
    with pytest.raises(SleepWakeConfigError):
        provider_cooldown_settings()

    assert _refusals(clock, "asset", "yfinance", 8) == DOUBLING
    assert wait_before_call("asset", "yfinance") == 0.0
    assert wait_before_call("asset", "yfinance") == 60.0
    assert record_no_verdict("asset", "yfinance") is None
    assert record_success("asset", "yfinance") is None
    assert cooldowns.snapshot() == ()
    print_success("no exception; 60 → 3600 as by default")


LOG_PROBE_MARKER = "PROVIDER-COOLDOWN-LOG-PROBE "

#: The probe's steps — ``(BASE, MAX)``, ``None`` leaving one unset — each with the error events expected so far.
LOG_STEPS = [
    (("abc", None), 1),  # PROVIDER_COOLDOWN_BASE_INVALID, the first time in the process: logged
    (("-1", None), 1),  # the same variable and code with another value: not again
    (("86401", None), 1),  # idem
    ((None, "0"), 2),  # PROVIDER_COOLDOWN_MAX_INVALID, the first time: logged
    ((None, "86401"), 2),  # the same variable and code
    (("100", "50"), 2),  # a max below the base: the max's variable and code again
    (("10", "40"), 2),  # valid: nothing to report
]

#: Runs in the child, a fresh interpreter where nothing was logged yet. argv[1]: the JSON list of the steps' values.
LOG_PROBE = """
import json, os, sys

from structlog.testing import capture_logs

from backend.app.services.platform import provider_cooldown
from backend.app.utils.runtime.cooldown import Cooldowns

provider_cooldown.PROVIDER_COOLDOWNS = Cooldowns(60, 3600, clock=lambda: 1000.0, rng=lambda: 0.0)
names = ("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS")
waits, errors_after_step = [], []
with capture_logs() as events:
    for step, values in enumerate(json.loads(sys.argv[1])):
        for name, value in zip(names, values):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        provider = "log-probe-%d" % step
        for _ in range(3):
            provider_cooldown.wait_before_call("asset", provider)
        waits.append(provider_cooldown.record_refusal("asset", provider))
        provider_cooldown.record_no_verdict("asset", provider)
        provider_cooldown.record_success("asset", provider)
        errors_after_step.append(sum(1 for event in events if event.get("log_level") == "error"))
errors = [event for event in events if event.get("log_level") == "error"]
print("RESULT_MARKER" + json.dumps({"waits": waits, "errors_after_step": errors_after_step, "errors": errors}, default=repr))
""".replace("RESULT_MARKER", LOG_PROBE_MARKER)


def test_an_invalid_configuration_is_logged_once_per_variable_and_code_per_process(tmp_path: Path) -> None:
    """PCD-022 — contract 8: in a fresh interpreter, three invalid bases, then two invalid maxes and a max below its base, then a valid pair, each read several times by every function: two error events in all — the first naming the base's variable, at the first invalid base; the second naming the max's, at the first invalid max — and every refusal waits 60 s until the valid pair's 10.

    A fresh interpreter, because "once per process" can only start over in a new one: in this process an earlier test
    may have logged the same fault already.
    """
    print_section("PCD-022: once per (variable, code) per process")
    env = {name: value for name, value in os.environ.items() if not name.startswith(COOLDOWN_PREFIX)}
    env["PYTHONPATH"] = os.pathsep.join(part for part in (str(REPO_ROOT), os.environ.get("PYTHONPATH")) if part)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    done = subprocess.run(
        [sys.executable, "-c", LOG_PROBE, json.dumps([values for values, _ in LOG_STEPS])],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, f"the probe failed:\n{done.stderr}"
    lines = [line for line in done.stdout.splitlines() if line.startswith(LOG_PROBE_MARKER)]
    assert len(lines) == 1, f"the probe printed no result:\n{done.stdout}\n{done.stderr}"
    result = json.loads(lines[0].removeprefix(LOG_PROBE_MARKER))

    assert result["waits"] == [60.0] * (len(LOG_STEPS) - 1) + [10.0], "barrier: every step ran, the invalid ones on the defaults"
    assert result["errors_after_step"] == [expected for _, expected in LOG_STEPS], result["errors"]
    base_event, max_event = result["errors"]
    assert _holds(base_event, BASE_VARIABLE), base_event
    assert _holds(max_event, MAX_VARIABLE), max_event
    print_success("two error events: the base's, then the max's")
