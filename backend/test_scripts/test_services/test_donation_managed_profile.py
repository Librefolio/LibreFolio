"""
The donation popup on a managed instance (workstream A, lot A9: F05, decision D-A8).

Under test: ``is_donation_popup_disabled()`` and ``record_login_and_maybe_show_popup()``
(``backend/app/services/accounts/donation_popup_service.py``) under the instance profile ``LIBREFOLIO_PROFILE``, as
``get_settings()`` reads it. Decision D-A8: on a managed instance, one a hosting provider runs for its customers, every
invitation to donate disappears; the hidden ``LIBREFOLIO_DISABLE_DONATION_POPUP`` (D-A7) stays for a self-hosted one.
The contract:

1. Managed (``LIBREFOLIO_PROFILE=managed``, spaces and case aside, as ``Settings`` normalises it):
   ``is_donation_popup_disabled()`` is ``True`` whatever the hidden variable says, unset, a false value (``0``) or a true
   one (``1``): the variable cannot bring the popup back on a managed instance.
2. Managed: ``record_login_and_maybe_show_popup()`` returns ``False`` at every login, also when the schedule
   (``should_show_donation_popup``) would show the popup (forced 60 days after the last one, due at the tenth login
   after the 7-day cooldown, forced 60 days after registration when never shown), and ``login_count`` and
   ``donation_popup_logins_since_shown`` still grow by exactly one per login. Nothing is reset and
   ``donation_popup_last_shown_at`` keeps its value: the popup was not shown, and the schedule stands where it stood
   should the instance become self-hosted.
3. Self-hosted (the profile unset, or ``selfhosted``): unchanged, the hidden variable alone decides.
   ``is_donation_popup_disabled()`` is ``True`` with ``1``, ``False`` unset or ``0``. A login the schedule makes due shows
   the popup without the variable (``True``, ``logins_since_shown`` back to 0, ``last_shown_at`` the login's time,
   ``login_count`` one more) and not with it (``False``, both counters one more, nothing reset). Controls: green before
   A9 and after.

How: pure. In-memory ``User`` objects, never persisted; no database, no server, no network. The profile and the hidden
variable are set with ``monkeypatch``, restored after each case, with ``LIBREFOLIO_TEST_MODE=1`` so that
``get_settings()`` reads no ``.env`` and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path`` so that it never looks at the
lane's data; a barrier checks that ``get_settings()`` reads the intended profile. ``get_settings()`` builds its settings
at each call today: should it ever cache them, the cache is emptied before and after each case. Each login of case 2
comes after a barrier (the schedule, asked with the counters the login will reach, makes the popup due), so that a
``False`` means "suppressed", never "not due". The service's functions are looked up when a test runs: a rename fails
the tests that need it, with the reason, never the collection. Red until A9: cases 1 and 2, but for the managed instance
whose hidden variable says ``1``, which the variable alone already turns off.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from backend.app import config
from backend.app.db.models import User
from backend.app.services.accounts import donation_popup_service
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_utils import print_section, print_success

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: D-A7: the hidden switch, never documented. On a self-hosted instance it alone turns the popup off.
HIDDEN_VARIABLE = "LIBREFOLIO_DISABLE_DONATION_POPUP"
#: How many logins in a row case 2 makes: "at every login", not only the first.
LOGINS = 3

#: Logins the schedule makes due, as (days since registration, days since the popup was last shown or None for never,
#: logins since it was last shown, before this login).
DUE_LOGINS = [
    pytest.param(400, 61, 0, id="forced-60-days-after-the-last-popup"),
    pytest.param(400, 8, 9, id="tenth-login-after-the-7-day-cooldown"),
    pytest.param(61, None, 0, id="never-shown-forced-60-days-after-registration"),
]
DUE_LOGIN_FIELDS = ("days_since_registration", "days_since_shown", "logins_since_shown")
#: The self-hosted profile, written both ways: unset, and named.
SELF_HOSTED = [pytest.param(None, id="profile-unset"), pytest.param("selfhosted", id="selfhosted")]


# =============================================================================
# HELPERS
# =============================================================================


def _service_function(name: str) -> Callable[..., Any]:
    """The function ``name`` of the donation popup service, looked up when the test runs."""
    function = getattr(donation_popup_service, name, None)
    assert callable(function), f"backend.app.services.accounts.donation_popup_service has no {name}() (found {function!r}): the contract of A9 is written against it"
    return function


def _forget_cached_settings() -> None:
    """``get_settings()`` builds its settings at each call today; should it ever cache them, the cache is emptied here."""
    cache_clear = getattr(config.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """No case inherits the settings another one read, nor leaves its own behind."""
    _forget_cached_settings()
    yield
    _forget_cached_settings()


def use_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, expected: str) -> None:
    """``get_settings()`` reads ``LIBREFOLIO_PROFILE`` as ``written`` (``None``: unset) from this environment alone; barrier: it reads ``expected``."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    if written is None:
        monkeypatch.delenv(PROFILE_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(PROFILE_VARIABLE, written)
    _forget_cached_settings()

    resolved = config.get_settings().LIBREFOLIO_PROFILE

    assert resolved == expected, f"barrier: with {PROFILE_VARIABLE}={written!r}, get_settings() reads the profile {resolved!r}, not {expected!r}"


def set_hidden_switch(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_DISABLE_DONATION_POPUP`` set to ``value``; ``None`` unsets it."""
    if value is None:
        monkeypatch.delenv(HIDDEN_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(HIDDEN_VARIABLE, value)


def make_user(now: datetime, days_since_registration: int, days_since_shown: int | None, logins_since_shown: int) -> User:
    """An in-memory (never persisted) ``User`` at the given point of the schedule, with 20 logins in all."""
    return User(
        username="donation_managed_profile_user",
        email="donation_managed_profile_user@example.com",
        hashed_password="not-a-real-hash",
        created_at=now - timedelta(days=days_since_registration),
        donation_popup_last_shown_at=None if days_since_shown is None else now - timedelta(days=days_since_shown),
        donation_popup_logins_since_shown=logins_since_shown,
        login_count=20,
    )


def counters(user: User) -> tuple[int, int]:
    """``(login_count, donation_popup_logins_since_shown)``."""
    return user.login_count, user.donation_popup_logins_since_shown


def assert_due(user: User, now: datetime, login: int) -> None:
    """Barrier: the schedule, asked with the counters this login will reach, makes the popup due; else a ``False`` proves nothing."""
    schedule = _service_function("should_show_donation_popup")
    due = schedule(user.donation_popup_logins_since_shown + 1, user.donation_popup_last_shown_at, user.created_at, now)
    assert due is True, f"barrier: at login {login} the schedule must make the popup due, or the answer proves nothing (logins since shown {user.donation_popup_logins_since_shown + 1}, last shown {user.donation_popup_last_shown_at}, registered {user.created_at})"


# =============================================================================
# 1. MANAGED: THE POPUP IS OFF, WHATEVER THE HIDDEN VARIABLE SAYS
# =============================================================================


# red until A9 (but for hidden-true, which the hidden variable alone already turns off): the profile is not read
@pytest.mark.parametrize("hidden", [pytest.param(None, id="hidden-unset"), pytest.param("0", id="hidden-false"), pytest.param("1", id="hidden-true")])
@pytest.mark.parametrize("written", [pytest.param("managed", id="managed"), pytest.param(" MANAGED ", id="managed-any-case-and-spaces")])
def test_a_managed_instance_turns_the_donation_popup_off_whatever_the_hidden_variable_says(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str, hidden: str | None) -> None:
    """DMP-001 (1): managed, ``is_donation_popup_disabled()`` is ``True``, the hidden variable unset, false or true."""
    print_section(f"DMP-001: {PROFILE_VARIABLE}={written!r}, {HIDDEN_VARIABLE}={hidden!r}")
    is_disabled = _service_function("is_donation_popup_disabled")
    use_profile(monkeypatch, tmp_path, written, "managed")
    set_hidden_switch(monkeypatch, hidden)

    disabled = is_disabled()

    assert disabled is True, f"red until A9: on a managed instance the donation popup is off whatever {HIDDEN_VARIABLE} says ({hidden!r}); is_donation_popup_disabled() gave {disabled!r}"
    print_success(f"managed, {HIDDEN_VARIABLE}={hidden!r}: the donation popup is off")


# =============================================================================
# 2. MANAGED: NO POPUP AT ANY LOGIN, EVERY LOGIN COUNTED
# =============================================================================


# red until A9: a managed instance shows the popup when the schedule makes it due, and resets the counters
@pytest.mark.parametrize("hidden", [pytest.param(None, id="hidden-unset"), pytest.param("0", id="hidden-false")])
@pytest.mark.parametrize(DUE_LOGIN_FIELDS, DUE_LOGINS)
def test_a_managed_instance_never_shows_the_popup_yet_counts_every_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, days_since_registration: int, days_since_shown: int | None, logins_since_shown: int, hidden: str | None) -> None:
    """DMP-002 (2): managed, ``record_login_and_maybe_show_popup()`` is ``False`` at each of three logins the schedule makes due, both counters one more at each, nothing reset, ``last_shown_at`` unchanged."""
    print_section(f"DMP-002: managed, {LOGINS} due logins, {HIDDEN_VARIABLE}={hidden!r}")
    record_login = _service_function("record_login_and_maybe_show_popup")
    use_profile(monkeypatch, tmp_path, "managed", "managed")
    set_hidden_switch(monkeypatch, hidden)
    now = utcnow()
    user = make_user(now, days_since_registration, days_since_shown, logins_since_shown)
    last_shown_at = user.donation_popup_last_shown_at

    for login in range(1, LOGINS + 1):
        assert_due(user, now, login)
        before = counters(user)

        shown = record_login(user, now=now)

        assert shown is False, f"red until A9: login {login} of {LOGINS} on a managed instance: record_login_and_maybe_show_popup() must never ask for the donation popup, even when the schedule makes it due; it gave {shown!r}"
        assert counters(user) == (before[0] + 1, before[1] + 1), f"login {login} on a managed instance: login_count and donation_popup_logins_since_shown must each grow by one, nothing reset: {before} -> {counters(user)}"

    assert user.donation_popup_last_shown_at == last_shown_at, f"the popup was never shown: donation_popup_last_shown_at must stay {last_shown_at}, became {user.donation_popup_last_shown_at}"
    print_success(f"managed: {LOGINS} due logins, no popup, counters {counters(user)}")


# =============================================================================
# 3. SELF-HOSTED: UNCHANGED, THE HIDDEN VARIABLE ALONE DECIDES (controls)
# =============================================================================


# control: green before A9 and after
@pytest.mark.parametrize(("hidden", "expected"), [pytest.param(None, False, id="hidden-unset-popup-on"), pytest.param("0", False, id="hidden-false-popup-on"), pytest.param("1", True, id="hidden-true-popup-off")])
@pytest.mark.parametrize("written", SELF_HOSTED)
def test_a_self_hosted_instance_leaves_the_popup_to_the_hidden_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, hidden: str | None, expected: bool) -> None:
    """DMP-003 (3): self-hosted, ``is_donation_popup_disabled()`` is ``True`` exactly when the hidden variable says ``1``."""
    print_section(f"DMP-003: {PROFILE_VARIABLE}={written!r}, {HIDDEN_VARIABLE}={hidden!r}")
    is_disabled = _service_function("is_donation_popup_disabled")
    use_profile(monkeypatch, tmp_path, written, "selfhosted")
    set_hidden_switch(monkeypatch, hidden)

    disabled = is_disabled()

    assert disabled is expected, f"self-hosted, {HIDDEN_VARIABLE}={hidden!r}: the hidden variable alone decides, is_donation_popup_disabled() must give {expected!r}, gave {disabled!r}"
    print_success(f"self-hosted, {HIDDEN_VARIABLE}={hidden!r}: disabled={disabled}")


# control: green before A9 and after
@pytest.mark.parametrize(DUE_LOGIN_FIELDS, DUE_LOGINS)
@pytest.mark.parametrize("written", SELF_HOSTED)
def test_a_self_hosted_instance_shows_a_due_popup_without_the_hidden_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, days_since_registration: int, days_since_shown: int | None, logins_since_shown: int) -> None:
    """DMP-004 (3): self-hosted, no hidden variable, a due login shows the popup: ``True``, ``logins_since_shown`` back to 0, ``last_shown_at`` the login's time, ``login_count`` one more. It also proves the logins of DMP-002 due through the whole function."""
    print_section(f"DMP-004: {PROFILE_VARIABLE}={written!r}, a due login, no {HIDDEN_VARIABLE}")
    record_login = _service_function("record_login_and_maybe_show_popup")
    use_profile(monkeypatch, tmp_path, written, "selfhosted")
    set_hidden_switch(monkeypatch, None)
    now = utcnow()
    user = make_user(now, days_since_registration, days_since_shown, logins_since_shown)
    assert_due(user, now, 1)
    login_count = user.login_count

    shown = record_login(user, now=now)

    assert shown is True, f"self-hosted, no {HIDDEN_VARIABLE}: a due login must show the donation popup, record_login_and_maybe_show_popup() gave {shown!r}"
    assert counters(user) == (login_count + 1, 0), f"the popup shown: login_count one more and donation_popup_logins_since_shown back to 0, got {counters(user)}"
    assert user.donation_popup_last_shown_at == now, f"the popup shown: donation_popup_last_shown_at must be the login's time {now}, got {user.donation_popup_last_shown_at}"
    print_success(f"self-hosted: the due popup shown, counters {counters(user)}")


# control: green before A9 and after
@pytest.mark.parametrize(DUE_LOGIN_FIELDS, DUE_LOGINS)
@pytest.mark.parametrize("written", SELF_HOSTED)
def test_a_self_hosted_instance_with_the_hidden_variable_never_shows_the_popup_yet_counts_the_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, written: str | None, days_since_registration: int, days_since_shown: int | None, logins_since_shown: int) -> None:
    """DMP-005 (3): self-hosted with ``LIBREFOLIO_DISABLE_DONATION_POPUP=1``, a due login: ``False``, both counters one more, nothing reset, ``last_shown_at`` unchanged."""
    print_section(f"DMP-005: {PROFILE_VARIABLE}={written!r}, a due login, {HIDDEN_VARIABLE}=1")
    record_login = _service_function("record_login_and_maybe_show_popup")
    use_profile(monkeypatch, tmp_path, written, "selfhosted")
    set_hidden_switch(monkeypatch, "1")
    now = utcnow()
    user = make_user(now, days_since_registration, days_since_shown, logins_since_shown)
    assert_due(user, now, 1)
    before = counters(user)
    last_shown_at = user.donation_popup_last_shown_at

    shown = record_login(user, now=now)

    assert shown is False, f"self-hosted with {HIDDEN_VARIABLE}=1: the popup is off, record_login_and_maybe_show_popup() gave {shown!r}"
    assert counters(user) == (before[0] + 1, before[1] + 1), f"the login still counts, nothing reset: {before} -> {counters(user)}"
    assert user.donation_popup_last_shown_at == last_shown_at, f"the popup was not shown: donation_popup_last_shown_at must stay {last_shown_at}, became {user.donation_popup_last_shown_at}"
    print_success(f"self-hosted with the hidden variable: no popup, counters {counters(user)}")
