"""Configuration checks of the accounts section, in the shape of the platform's (``config_audit.ConfigCheck``).

One check so far: whether the limit on failed sign-ins (F15) is on. Like every configuration check it reads the
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


ACCOUNTS_CONFIG_CHECKS = (check_login_limit,)
