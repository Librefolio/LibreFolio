"""
Unit tests for the donation-popup trigger decision logic.

Pure-function tests — no DB session, no HTTP server. Follows the same lightweight
pattern as test_config_misc.py (plain pytest functions + monkeypatch for env vars).
"""

from datetime import timedelta

from backend.app.db.models import User
from backend.app.services.donation_popup_service import (
    is_donation_popup_disabled,
    record_login_and_maybe_show_popup,
    should_show_donation_popup,
)
from backend.app.utils.datetime_utils import utcnow


def make_user(**overrides) -> User:
    """Build an in-memory (non-persisted) User with sensible defaults for these tests."""
    defaults = {
        "username": "donation_popup_test_user",
        "email": "donation_popup_test_user@example.com",
        "hashed_password": "not-a-real-hash",
        "created_at": utcnow(),
    }
    defaults.update(overrides)
    return User(**defaults)


# =============================================================================
# is_donation_popup_disabled()
# =============================================================================


def test_is_donation_popup_disabled_false_when_unset(monkeypatch):
    monkeypatch.delenv("LIBREFOLIO_DISABLE_DONATION_POPUP", raising=False)
    assert is_donation_popup_disabled() is False


def test_is_donation_popup_disabled_true_variants(monkeypatch):
    for value in ("1", "true", "True", "yes", "YES"):
        monkeypatch.setenv("LIBREFOLIO_DISABLE_DONATION_POPUP", value)
        assert is_donation_popup_disabled() is True


def test_is_donation_popup_disabled_false_variants(monkeypatch):
    for value in ("0", "false", "no", ""):
        monkeypatch.setenv("LIBREFOLIO_DISABLE_DONATION_POPUP", value)
        assert is_donation_popup_disabled() is False


# =============================================================================
# should_show_donation_popup() — pure decision function
# =============================================================================


def test_never_shown_blocked_before_one_week_even_with_many_logins():
    """New user, never shown: 1-week cooldown (from created_at) still applies."""
    now = utcnow()
    created_at = now  # account created right now
    assert should_show_donation_popup(100, None, created_at, now) is False


def test_never_shown_blocked_below_login_threshold():
    now = utcnow()
    created_at = now - timedelta(days=10)
    assert should_show_donation_popup(49, None, created_at, now) is False


def test_never_shown_shows_at_threshold_after_cooldown():
    now = utcnow()
    created_at = now - timedelta(days=10)
    assert should_show_donation_popup(50, None, created_at, now) is True


def test_never_shown_forced_after_two_months_since_registration():
    """User decision (also_cap_new_users): 60-day rule uses created_at as baseline too."""
    now = utcnow()
    created_at = now - timedelta(days=61)
    assert should_show_donation_popup(0, None, created_at, now) is True


def test_never_shown_not_yet_forced_at_59_days():
    now = utcnow()
    created_at = now - timedelta(days=59)
    assert should_show_donation_popup(0, None, created_at, now) is False


def test_previously_shown_blocked_by_cooldown_despite_login_count():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=3)
    assert should_show_donation_popup(100, last_shown_at, created_at, now) is False


def test_previously_shown_triggers_after_cooldown_and_threshold():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=8)
    assert should_show_donation_popup(50, last_shown_at, created_at, now) is True


def test_previously_shown_not_enough_logins_yet():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=8)
    assert should_show_donation_popup(49, last_shown_at, created_at, now) is False


def test_previously_shown_forced_after_two_months_regardless_of_logins():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=61)
    assert should_show_donation_popup(0, last_shown_at, created_at, now) is True


def test_boundary_exactly_seven_days_and_fifty_logins():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=7)
    assert should_show_donation_popup(50, last_shown_at, created_at, now) is True


def test_boundary_exactly_sixty_days_forces_regardless_of_logins():
    now = utcnow()
    created_at = now - timedelta(days=400)
    last_shown_at = now - timedelta(days=60)
    assert should_show_donation_popup(0, last_shown_at, created_at, now) is True


def test_handles_naive_datetimes_from_sqlite():
    """
    Regression test: SQLite round-trips DateTime columns as naive (no tzinfo), while
    utcnow() is timezone-aware. Mixing them must not raise
    "can't subtract offset-naive and offset-aware datetimes" (see ensure_utc()).
    """
    now = utcnow()
    naive_created_at = (now - timedelta(days=400)).replace(tzinfo=None)
    naive_last_shown_at = (now - timedelta(days=8)).replace(tzinfo=None)

    assert should_show_donation_popup(50, naive_last_shown_at, naive_created_at, now) is True
    assert should_show_donation_popup(10, naive_last_shown_at, naive_created_at, now) is False


# =============================================================================
# record_login_and_maybe_show_popup() — mutates counters on the User instance
# =============================================================================


def test_record_login_increments_counters_unconditionally(monkeypatch):
    monkeypatch.delenv("LIBREFOLIO_DISABLE_DONATION_POPUP", raising=False)
    user = make_user(login_count=5, donation_popup_logins_since_shown=3)

    record_login_and_maybe_show_popup(user)

    assert user.login_count == 6
    assert user.donation_popup_logins_since_shown == 4


def test_record_login_resets_counters_when_popup_shown():
    now = utcnow()
    user = make_user(
        created_at=now - timedelta(days=400),
        donation_popup_last_shown_at=now - timedelta(days=8),
        donation_popup_logins_since_shown=49,
    )

    show_popup = record_login_and_maybe_show_popup(user, now=now)

    assert show_popup is True
    assert user.donation_popup_logins_since_shown == 0
    assert user.donation_popup_last_shown_at == now


def test_record_login_keeps_counting_when_not_yet_due():
    now = utcnow()
    user = make_user(
        created_at=now - timedelta(days=400),
        donation_popup_last_shown_at=now - timedelta(days=8),
        donation_popup_logins_since_shown=10,
    )

    show_popup = record_login_and_maybe_show_popup(user, now=now)

    assert show_popup is False
    # Not reset — keeps accumulating towards the next threshold.
    assert user.donation_popup_logins_since_shown == 11
    assert user.donation_popup_last_shown_at == now - timedelta(days=8)


def test_record_login_disabled_env_var_still_counts_but_never_signals(monkeypatch):
    """Hidden switch: counters stay accurate, but the popup never fires and
    last_shown_at/logins_since_shown are NOT reset (so behaviour resumes cleanly
    if the switch is later removed)."""
    monkeypatch.setenv("LIBREFOLIO_DISABLE_DONATION_POPUP", "1")
    now = utcnow()
    user = make_user(
        created_at=now - timedelta(days=400),
        donation_popup_last_shown_at=now - timedelta(days=61),  # would force-show
        donation_popup_logins_since_shown=999,
        login_count=10,
    )

    show_popup = record_login_and_maybe_show_popup(user, now=now)

    assert show_popup is False
    assert user.login_count == 11
    assert user.donation_popup_logins_since_shown == 1000
    assert user.donation_popup_last_shown_at == now - timedelta(days=61)
