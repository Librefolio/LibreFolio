"""Configuration checks: the settings that leave an instance weaker than it should be.

Owner: workstream H (platform). Each check reads the configuration and returns its state as a ``ConfigCheck``: an id,
a severity, the i18n key of its message for the admin interface (``instance.checks.*``, or ``auth.checks.*``,
``backup.checks.*`` and ``email.checks.*`` for the checks of workstreams A, B and E, written whole so the i18n audit sees
it), the parameters of that message and an English summary for the log. A check changes nothing, never raises and never
puts a secret value in its result.

At startup, ``log_configuration_audit()`` first stops on a configured secret that cannot be used, then logs every check
that is not ``ok``. The «Security» tab of the admin settings will evaluate the same checks on demand. A check may report
what the server has met since it started, as ``platform.client_address`` does: at startup it has met nothing yet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from backend.app.config import SecretFileError, get_settings, secrets_set_twice
from backend.app.config.accounts import admin_bootstrap_config, login_limit_enabled
from backend.app.config.platform import configured_jwt_secret, configured_jwt_secret_origin, instance_blocked, instance_deletion_date
from backend.app.logging_config import get_logger
from backend.app.services.accounts.checks import ACCOUNTS_CONFIG_CHECKS
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS
from backend.app.services.platform.client_address import PUBLIC_FORWARDING_SUMMARY, UNTRUSTED_PROXY_SUMMARY, untrusted_forwarding_seen
from backend.app.services.platform.instance_backup.checks import BACKUP_CONFIG_CHECKS
from backend.app.services.platform.instance_key import InstanceKeyError, instance_key_status

logger = get_logger(__name__)

Severity = Literal["ok", "info", "warning", "error"]

JWT_SECRET_MIN_LENGTH = 32


class WeakSecretError(ValueError):
    """A configured secret too short for the profile: in the managed profile, a short ``JWT_SECRET`` stops the start."""


@dataclass(frozen=True)
class ConfigCheck:
    """The state of one configuration check: ``detail`` holds the parameters of the ``i18n_key`` message."""

    check_id: str
    severity: Severity
    i18n_key: str
    detail: dict[str, str | int] = field(default_factory=dict)
    summary: str = ""


def check_jwt_secret() -> ConfigCheck:
    """``JWT_SECRET``: unset means a new key at every start (the default, so only info); a short one is weak.

    In the managed profile a short key is an error, and ``log_configuration_audit()`` stops the start on it.
    """
    check_id = "platform.jwt_secret"
    try:
        secret = configured_jwt_secret()
    except SecretFileError as exc:
        return ConfigCheck(check_id, "error", "instance.checks.jwtSecret.unreadable", {"reason": str(exc)}, f"The session signing key cannot be read: {exc}")
    if secret is None:
        return ConfigCheck(
            check_id,
            "info",
            "instance.checks.jwtSecret.ephemeral",
            summary="JWT_SECRET is not set: every start makes a new session signing key, so a restart signs every user out",
        )
    if len(secret) < JWT_SECRET_MIN_LENGTH:
        origin = configured_jwt_secret_origin() or "JWT_SECRET"
        return ConfigCheck(
            check_id,
            "error" if get_settings().LIBREFOLIO_PROFILE == "managed" else "warning",
            "instance.checks.jwtSecret.short",
            {"source": origin, "length": len(secret), "minimum": JWT_SECRET_MIN_LENGTH},
            f"The session signing key from {origin} is {len(secret)} characters long: use at least {JWT_SECRET_MIN_LENGTH} random characters",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.jwtSecret.ok")


def check_secrets_set_twice() -> ConfigCheck:
    """A secret set both as ``NAME`` and as ``NAME_FILE``: ``NAME`` wins, so the file the admin meant is ignored."""
    check_id = "platform.secrets_set_twice"
    names = secrets_set_twice()
    if not names:
        return ConfigCheck(check_id, "ok", "instance.checks.secretsSetTwice.ok")
    listed = ", ".join(names)
    return ConfigCheck(
        check_id,
        "warning",
        "instance.checks.secretsSetTwice.found",
        {"variables": listed},
        f"Set both directly and through a *_FILE variable: {listed}. The direct value wins and the file is ignored",
    )


def check_instance_key() -> ConfigCheck:
    """The instance key: unusable is an error; a generated key file open to group or others is a warning."""
    check_id = "platform.instance_key"
    status = instance_key_status()
    if status.problem is not None:
        return ConfigCheck(check_id, "error", "instance.checks.instanceKey.unusable", {"source": status.source, "reason": status.problem}, f"The instance key cannot be used: {status.problem}")
    if status.loose_modes:
        modes = ", ".join(f"{target} {mode}" for target, mode in status.loose_modes.items())
        return ConfigCheck(
            check_id,
            "warning",
            "instance.checks.instanceKey.permissions",
            {"path": str(status.path), **status.loose_modes},
            f"{status.path} is open to other users ({modes}): the folder should be 0700 and the file 0600",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.instanceKey.ok", {"source": status.source})


def check_session_cookie() -> ConfigCheck:
    """``SESSION_COOKIE_SECURE=never``: the session cookie may travel over plain HTTP."""
    check_id = "platform.session_cookie"
    if get_settings().SESSION_COOKIE_SECURE == "never":
        return ConfigCheck(
            check_id,
            "warning",
            "instance.checks.sessionCookie.never",
            summary="SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.sessionCookie.ok")


def check_client_address() -> ConfigCheck:
    """Forwarding headers from peers nobody trusts, met since the start (decision N70, ``client_address.py``).

    From a local peer they come from a reverse proxy LibreFolio does not trust, whose address every visitor shares: the
    limits per client address skip those requests, a warning. From public peers only, a client or a proxy on a public
    address sent them, and they were ignored: info. Nothing met, as at startup, is ok. The names of the headers only,
    never an address (N58).
    """
    check_id = "platform.client_address"
    local = untrusted_forwarding_seen("local")
    if local:
        return ConfigCheck(check_id, "warning", "instance.checks.clientAddress.untrustedProxy", {"headers": ", ".join(local)}, UNTRUSTED_PROXY_SUMMARY)
    public = untrusted_forwarding_seen("public")
    if public:
        return ConfigCheck(check_id, "info", "instance.checks.clientAddress.publicForwarding", {"headers": ", ".join(public)}, PUBLIC_FORWARDING_SUMMARY)
    return ConfigCheck(check_id, "ok", "instance.checks.clientAddress.ok")


#: The managed profile's expectations the two checks below hold, written here and not read from ``PROFILE_DEFAULTS``: a
#: managed entry lost from that table would otherwise change the expectation along with the value, and nothing would show.
MANAGED_PROFILE = "managed"


def check_frame_protection() -> ConfigCheck:
    """``LIBREFOLIO_FRAME_PROTECTION`` off in the managed profile, which turns it on (D5): any site can frame the app.

    Self-hosted, off is the default (dashboards at another address may embed the app), so it is ok either way. In the
    managed profile, off means its ``PROFILE_DEFAULTS`` entry was lost or a hosting panel switched it off (H-39): a
    warning, at startup and in the admin's security checks.
    """
    check_id = "platform.frame_protection"
    settings = get_settings()
    if settings.LIBREFOLIO_FRAME_PROTECTION:
        return ConfigCheck(check_id, "ok", "instance.checks.frameProtection.on")
    if settings.LIBREFOLIO_PROFILE == MANAGED_PROFILE:
        return ConfigCheck(
            check_id,
            "warning",
            "instance.checks.frameProtection.offManaged",
            summary="LIBREFOLIO_FRAME_PROTECTION is off in the managed profile: any site can show LibreFolio in a frame; the managed profile turns it on",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.frameProtection.offSelfHosted")


def check_csp_report_only() -> ConfigCheck:
    """``LIBREFOLIO_CSP_REPORT_ONLY`` off in the managed profile, which turns it on (D5): no violation is listed.

    The policy only reports and blocks nothing, so losing it is info, not a warning. Self-hosted, off is the default,
    ok either way (H-39).
    """
    check_id = "platform.csp_report_only"
    settings = get_settings()
    if settings.LIBREFOLIO_CSP_REPORT_ONLY:
        return ConfigCheck(check_id, "ok", "instance.checks.cspReportOnly.on")
    if settings.LIBREFOLIO_PROFILE == MANAGED_PROFILE:
        return ConfigCheck(
            check_id,
            "info",
            "instance.checks.cspReportOnly.offManaged",
            summary="LIBREFOLIO_CSP_REPORT_ONLY is off in the managed profile: browsers list no Content-Security-Policy violation; the managed profile turns it on",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.cspReportOnly.offSelfHosted")


def check_log_level() -> ConfigCheck:
    """A ``DEBUG`` or ``TRACE`` log records operational detail that a production log does not need."""
    check_id = "platform.log_level"
    level = get_settings().LOG_LEVEL.upper()
    if level in ("DEBUG", "TRACE"):
        return ConfigCheck(
            check_id,
            "info",
            "instance.checks.logLevel.verbose",
            {"log_level": level},
            f"The log level is {level}: the log records operational detail; INFO is enough in production",
        )
    return ConfigCheck(check_id, "ok", "instance.checks.logLevel.ok")


CONFIG_CHECKS: tuple[Callable[[], ConfigCheck], ...] = (
    check_jwt_secret,
    check_secrets_set_twice,
    check_instance_key,
    check_session_cookie,
    check_client_address,
    check_frame_protection,
    check_csp_report_only,
    check_log_level,
    # Workstream B: the hosting panel's backup token and the restore's upload limit (instance_backup/checks.py, B-9)
    *BACKUP_CONFIG_CHECKS,
    # Workstream A: the limit on failed sign-ins (services/accounts/checks.py)
    *ACCOUNTS_CONFIG_CHECKS,
    # Workstream E: the SMTP configuration and its encryption (services/email/checks.py)
    *EMAIL_CONFIG_CHECKS,
)


def run_config_checks() -> list[ConfigCheck]:
    """Every configuration check, evaluated now, in the order of ``CONFIG_CHECKS``."""
    return [check() for check in CONFIG_CHECKS]


def log_configuration_audit() -> None:
    """Startup: stop on a configuration the server must not start with, then log every check that is not ``ok``.

    A ``JWT_SECRET_FILE`` that cannot be read raises ``SecretFileError``, a configured instance key that cannot be
    used raises ``InstanceKeyError``: the admin asked for that source, so the server must not start without it. In the
    managed profile, a ``JWT_SECRET`` shorter than ``JWT_SECRET_MIN_LENGTH`` raises ``WeakSecretError``. A
    ``LIBREFOLIO_BLOCKED`` or ``LIBREFOLIO_DELETION_DATE`` that cannot be read raises ``ValueError``. A generated key
    file gone bad is logged as an error instead, and the start goes on.
    """
    secret = configured_jwt_secret()
    if secret is not None and len(secret) < JWT_SECRET_MIN_LENGTH and get_settings().LIBREFOLIO_PROFILE == "managed":
        origin = configured_jwt_secret_origin() or "JWT_SECRET"
        raise WeakSecretError(f"In the managed profile the session signing key from {origin} must be at least {JWT_SECRET_MIN_LENGTH} characters long; it is {len(secret)}")
    if instance_blocked():
        deletion_date = instance_deletion_date()
        logger.warning("Instance blocked by its hosting provider (LIBREFOLIO_BLOCKED): only a few API routes answer", deletion_date=deletion_date.isoformat() if deletion_date else None)
    else:
        instance_deletion_date()
    # F02 (workstream A): an unusable LIBREFOLIO_ADMIN_* variable raises AdminBootstrapConfigError, naming it
    admin_bootstrap_config()
    # F15 (workstream A): a LIBREFOLIO_LOGIN_LIMIT other than on or off raises ValueError, naming it
    login_limit_enabled()
    status = instance_key_status()
    if status.source == "configured" and status.problem is not None:
        raise InstanceKeyError(status.problem)
    for result in run_config_checks():
        if result.severity == "ok":
            continue
        log = {"info": logger.info, "warning": logger.warning, "error": logger.error}[result.severity]
        log(result.summary, check=result.check_id, detail=result.detail)
