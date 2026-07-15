"""
Donation Popup Service

Decides, on each successful login, whether the frontend should show the
"support LibreFolio" popup (Buy Me a Coffee CTA).

Trigger rules (baseline = donation_popup_last_shown_at, or created_at if never shown):
- Forced re-prompt if >= 60 days have passed since the baseline.
- Otherwise, prompt if >= 50 logins have happened since the baseline AND
  >= 7 days have passed since the baseline (cooldown, avoids nagging too soon).

login_count and donation_popup_logins_since_shown are incremented on every login,
unconditionally — even when the popup signal itself is suppressed (see below) — so the
counters stay accurate and ready to resume normal behaviour if the suppression is lifted.

Hidden switch (intentionally undocumented — reserved for a future paid/hosted tier):
setting LIBREFOLIO_DISABLE_DONATION_POPUP forces the emitted signal to False, but does
NOT stop the counters above from being tracked. This variable is never exposed via any
API response and must never be added to .env.example or the docs.
"""

import os
from datetime import datetime
from typing import Optional

from backend.app.db.models import User
from backend.app.utils.datetime_utils import ensure_utc, utcnow

MIN_LOGINS_BETWEEN_PROMPTS = 50
MIN_DAYS_BETWEEN_PROMPTS = 7
MAX_DAYS_WITHOUT_PROMPT = 60


def is_donation_popup_disabled() -> bool:
    """
    Hidden switch — checks env var directly (never part of Settings/.env.example),
    same pattern as config.is_test_mode().
    """
    return os.environ.get("LIBREFOLIO_DISABLE_DONATION_POPUP", "").lower() in ("1", "true", "yes")


def should_show_donation_popup(
    logins_since_shown: int,
    last_shown_at: Optional[datetime],
    created_at: datetime,
    now: datetime,
) -> bool:
    """
    Pure decision function (no DB/HTTP), easy to unit test.

    Args:
        logins_since_shown: donation_popup_logins_since_shown counter
        last_shown_at: donation_popup_last_shown_at (None if never shown)
        created_at: user's account creation date (baseline fallback for "never shown")
        now: current time (UTC)

    Returns:
        True if the popup should be shown on this login.
    """
    baseline = ensure_utc(last_shown_at) or ensure_utc(created_at)
    days_since_baseline = (ensure_utc(now) - baseline).days

    if days_since_baseline >= MAX_DAYS_WITHOUT_PROMPT:
        return True

    return logins_since_shown >= MIN_LOGINS_BETWEEN_PROMPTS and days_since_baseline >= MIN_DAYS_BETWEEN_PROMPTS


def record_login_and_maybe_show_popup(user: User, now: Optional[datetime] = None) -> bool:
    """
    Updates the user's login/popup counters for this login and decides whether the
    frontend should show the donation popup. Mutates `user` in place; caller is
    responsible for session.add(user) + commit.

    Args:
        user: the User who just logged in successfully
        now: override for the current time (tests); defaults to utcnow()

    Returns:
        True if the frontend should show the popup on this login.
    """
    now = now or utcnow()

    # Unconditional counters — kept accurate regardless of the hidden suppression switch.
    user.login_count += 1
    user.donation_popup_logins_since_shown += 1

    if is_donation_popup_disabled():
        return False

    show_popup = should_show_donation_popup(
        user.donation_popup_logins_since_shown,
        user.donation_popup_last_shown_at,
        user.created_at,
        now,
    )

    if show_popup:
        user.donation_popup_last_shown_at = now
        user.donation_popup_logins_since_shown = 0

    return show_popup
