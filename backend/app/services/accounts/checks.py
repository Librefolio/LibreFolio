"""Configuration checks of the accounts section, in the shape of the platform's (``config_audit.ConfigCheck``).

Two checks: whether the limit on failed sign-ins (F15) is on, and where the change of the owner's address that a hosting
provider started stands (A5-1b, the check of lot H5-4). Like every configuration check it reads the
configuration, changes nothing, never raises and never puts a secret in its result. The i18n keys are ``auth.checks.*``.

They are part of the platform's ``CONFIG_CHECKS``: the startup audit logs them, and ``GET /security/checks`` returns
them, for the «Security» tab of the admin settings. ``config_audit`` imports this module to build that list, so this module
imports ``ConfigCheck`` only when a check runs: either module can then be imported first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.config.accounts import LOGIN_LIMIT_VARIABLE, login_limit_enabled, login_limit_value

if TYPE_CHECKING:
    from backend.app.services.platform.config_audit import ConfigCheck

CHECK_LOGIN_LIMIT = "accounts.login_limit"
CHECK_OWNER_EMAIL_CHANGE = "accounts.owner_email_change"


def check_login_limit() -> ConfigCheck:
    """``LIBREFOLIO_LOGIN_LIMIT``: on is ``ok``; ``off`` is a warning (a test instance, or a mistake); any other value is
    an error — the start stops on it, so the error shows only for a value seen after the start."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    try:
        enabled = login_limit_enabled()
    except ValueError:
        value = login_limit_value() or ""
        return ConfigCheck(
            CHECK_LOGIN_LIMIT,
            "error",
            "auth.checks.loginLimit.invalid",
            {"value": value},
            f"{LOGIN_LIMIT_VARIABLE}={value!r} is neither on nor off: the start stops on it",
        )
    if enabled:
        return ConfigCheck(CHECK_LOGIN_LIMIT, "ok", "auth.checks.loginLimit.ok")
    return ConfigCheck(
        CHECK_LOGIN_LIMIT,
        "warning",
        "auth.checks.loginLimit.off",
        summary=f"{LOGIN_LIMIT_VARIABLE}=off: failed sign-ins are not limited; turn it back on unless this is a test instance",
    )


def check_owner_email_change() -> ConfigCheck:
    """The change of the owner's address a hosting provider started with ``LIBREFOLIO_ADMIN_EMAIL``, as this process found it
    at its start (memory only, no database): ``ok`` when none waits, ``info`` while the new address has not confirmed it,
    ``warning`` when another account holds the new address and nothing changes. Never an address or a user name; never raises."""
    from backend.app.services.accounts import instance_owner  # noqa: PLC0415 — it imports the email and platform services
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    try:
        state = instance_owner.startup_change_state()
    except Exception:  # noqa: BLE001 — a check never raises: a state that cannot be read is no change waiting
        state = None
    if state == "pending":
        return ConfigCheck(
            CHECK_OWNER_EMAIL_CHANGE,
            "info",
            "auth.checks.ownerEmailChange.pending",
            summary="The hosting provider changed the owner's email address: the new address was sent a confirmation link, and the account keeps the old one until it is confirmed",
        )
    if state == "blocked":
        return ConfigCheck(
            CHECK_OWNER_EMAIL_CHANGE,
            "warning",
            "auth.checks.ownerEmailChange.blocked",
            summary="The hosting provider changed the owner's email address to one that another account already uses: nothing was changed; choose another address and restart",
        )
    return ConfigCheck(CHECK_OWNER_EMAIL_CHANGE, "ok", "auth.checks.ownerEmailChange.ok")


ACCOUNTS_CONFIG_CHECKS = (check_login_limit, check_owner_email_change)
