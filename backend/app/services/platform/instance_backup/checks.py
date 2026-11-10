"""Configuration checks of the backup, in the shape of the platform's (``config_audit.ConfigCheck``), lot B-9.

Four checks: the recipients a hosting panel's backups are sealed for (``LIBREFOLIO_BACKUP_RECIPIENTS``, L3), the hosting panel's token (``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` or its ``_FILE``), the largest archive a
restore accepts (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``) and the most it may unpack to (``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``,
B-35). Without them, a value that cannot be used shows only at the panel's first request, or at the first restore upload
or check: a 503 and a line in the log. Like every configuration check, they
read the configuration, change nothing, never raise, and never put a secret in their result: never the token, never
what a file holds. The i18n keys are ``backup.checks.*``.

They are part of the platform's ``CONFIG_CHECKS``, right after the platform's own checks and before workstream A's and
E's (E's close it): the startup audit logs them. ``config_audit`` imports this module to build that list, so this module
imports ``ConfigCheck`` only when a check runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.config import ProfileDefaultError, SecretFileError
from backend.app.config.backup import (
    MAX_RESTORE_VARIABLE,
    MAX_UPLOAD_VARIABLE,
    PANEL_TOKEN_MIN_LENGTH,
    PANEL_TOKEN_VARIABLE,
    RECIPIENTS_VARIABLE,
    BackupConfigError,
    backup_download_token,
    backup_max_restore_mb,
    backup_max_upload_mb,
    backup_recipients,
    backup_requires_recipients,
)

if TYPE_CHECKING:
    from backend.app.services.platform.config_audit import ConfigCheck

#: The ``BackupConfigError`` code of a token too short; any other code of the token is a character it cannot carry.
_TOKEN_TOO_SHORT = "BACKUP_DOWNLOAD_TOKEN_TOO_SHORT"
_PANEL_OFF_503 = "the hosting panel's backup routes answer 503 until it is fixed"
#: H-27 and H-37: the table is code, so a missing entry or one of the wrong type is a bug; setting the variable bypasses it.
_PROFILE_TABLE_SUMMARY = f"The profile's default for {MAX_UPLOAD_VARIABLE} is missing or of the wrong type, an error of LibreFolio itself: restore uploads answer 503 until {MAX_UPLOAD_VARIABLE} is set to a whole number of megabytes"
#: The same for the restore limit, which follows the upload limit while unset outside the self-hosted profile (B-35).
_RESTORE_PROFILE_TABLE_SUMMARY = f"The profile's default for {MAX_UPLOAD_VARIABLE}, which {MAX_RESTORE_VARIABLE} follows while unset, is missing or of the wrong type, an error of LibreFolio itself: restore checks answer 503 until {MAX_RESTORE_VARIABLE} is set"


def check_panel_token() -> ConfigCheck:
    """``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN``: unset, the panel's backup routes are off, the default (ok: nothing logged at
    startup); unusable, they answer 503 (error)."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "backup.panel_token"
    try:
        token = backup_download_token()
    except SecretFileError as exc:
        return ConfigCheck(check_id, "error", "backup.checks.panelToken.unreadable", {"reason": str(exc)}, f"The hosting panel's backup token cannot be read: {exc}")
    except BackupConfigError as exc:
        if exc.code == _TOKEN_TOO_SHORT:
            return ConfigCheck(check_id, "error", "backup.checks.panelToken.tooShort", {"minimum": PANEL_TOKEN_MIN_LENGTH}, f"{PANEL_TOKEN_VARIABLE} is too short: use at least {PANEL_TOKEN_MIN_LENGTH} random characters; {_PANEL_OFF_503}")
        return ConfigCheck(check_id, "error", "backup.checks.panelToken.notVisibleAscii", summary=f"{PANEL_TOKEN_VARIABLE} holds a space, a tab or a character outside visible ASCII: write it without them; {_PANEL_OFF_503}")
    if token is None:
        return ConfigCheck(check_id, "ok", "backup.checks.panelToken.off")
    return ConfigCheck(check_id, "ok", "backup.checks.panelToken.ok")


def check_upload_limit() -> ConfigCheck:
    """``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``: the largest archive a restore accepts. One that cannot be read refuses every
    restore upload (503) until it is fixed. An entry of the profiles' table that is missing (any profile but
    ``selfhosted``, H-37) or of the wrong type (H-27) is LibreFolio's own error, and refuses them too."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "backup.upload_limit"
    try:
        limit_mb = backup_max_upload_mb()
    except BackupConfigError:
        return ConfigCheck(check_id, "error", "backup.checks.uploadLimit.invalid", summary=f"{MAX_UPLOAD_VARIABLE} cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed")
    except ProfileDefaultError:
        return ConfigCheck(check_id, "error", "backup.checks.uploadLimit.profileTable", summary=_PROFILE_TABLE_SUMMARY)
    if limit_mb == 0:
        return ConfigCheck(check_id, "ok", "backup.checks.uploadLimit.unlimited")
    return ConfigCheck(check_id, "ok", "backup.checks.uploadLimit.limited", {"limit_mb": limit_mb})


def check_restore_limit() -> ConfigCheck:
    """``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``: the most an archive may unpack to in a restore's check (B-35). One that cannot
    be read refuses every check (503) until it is fixed. Unset outside the self-hosted profile it follows the upload
    limit, so an upload limit that cannot be read, or a broken profile entry of it, refuses them too: the error names
    the variable at fault."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "backup.restore_limit"
    try:
        limit_mb = backup_max_restore_mb()
    except BackupConfigError as exc:
        return ConfigCheck(check_id, "error", "backup.checks.restoreLimit.invalid", {"variable": exc.variable}, f"{exc.variable} cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed")
    except ProfileDefaultError:
        return ConfigCheck(check_id, "error", "backup.checks.restoreLimit.profileTable", summary=_RESTORE_PROFILE_TABLE_SUMMARY)
    if limit_mb == 0:
        return ConfigCheck(check_id, "ok", "backup.checks.restoreLimit.unlimited")
    return ConfigCheck(check_id, "ok", "backup.checks.restoreLimit.limited", {"limit_mb": limit_mb})


def check_recipients() -> ConfigCheck:
    """``LIBREFOLIO_BACKUP_RECIPIENTS`` (L3): the age recipients a hosting panel's backups are sealed for. Unset, the panel
    gets clear zips on a self-hosted instance (ok) and none on a managed one (error: 503); unusable, none either (error)."""
    from backend.app.services.platform.config_audit import ConfigCheck  # noqa: PLC0415 — config_audit imports this module

    check_id = "backup.recipients"
    try:
        recipients = backup_recipients()
    except BackupConfigError as exc:
        return ConfigCheck(check_id, "error", "backup.checks.recipients.invalid", {"reason": exc.code}, f"{exc}; the hosting panel's backups answer 503 until it is fixed")
    if recipients is None:
        if backup_requires_recipients():
            return ConfigCheck(check_id, "error", "backup.checks.recipients.missingManaged", summary=f"{RECIPIENTS_VARIABLE} is not set: a managed instance never hands a clear backup to its hosting panel, whose backups answer 503 until it is set")
        return ConfigCheck(check_id, "ok", "backup.checks.recipients.off")
    return ConfigCheck(check_id, "ok", "backup.checks.recipients.ok", {"count": len(recipients)})


BACKUP_CONFIG_CHECKS = (check_panel_token, check_upload_limit, check_restore_limit, check_recipients)
