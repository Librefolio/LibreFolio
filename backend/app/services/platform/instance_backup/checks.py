"""Configuration checks of the backup, in the shape of the platform's (``config_audit.ConfigCheck``), lot B-9.

Two checks: the hosting panel's token (``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` or its ``_FILE``) and the largest archive a
restore accepts (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``). Without them, a value that cannot be used shows only at the
panel's first request or at the first restore upload: a 503 and a line in the log. Like every configuration check, they
read the configuration, change nothing, never raise, and never put a secret in their result: never the token, never
what a file holds. The i18n keys are ``backup.checks.*``.

They are part of the platform's ``CONFIG_CHECKS``, right after the platform's own checks and before workstream A's and
E's (E's close it): the startup audit logs them. ``config_audit`` imports this module to build that list, so this module
imports ``ConfigCheck`` only when a check runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.config import ProfileDefaultError, SecretFileError
from backend.app.config.backup import MAX_UPLOAD_VARIABLE, PANEL_TOKEN_MIN_LENGTH, PANEL_TOKEN_VARIABLE, BackupConfigError, backup_download_token, backup_max_upload_mb

if TYPE_CHECKING:
    from backend.app.services.platform.config_audit import ConfigCheck

#: The ``BackupConfigError`` code of a token too short; any other code of the token is a character it cannot carry.
_TOKEN_TOO_SHORT = "BACKUP_DOWNLOAD_TOKEN_TOO_SHORT"
_PANEL_OFF_503 = "the hosting panel's backup routes answer 503 until it is fixed"
#: H-27 and H-37: the table is code, so a missing entry or one of the wrong type is a bug; setting the variable bypasses it.
_PROFILE_TABLE_SUMMARY = f"The profile's default for {MAX_UPLOAD_VARIABLE} is missing or of the wrong type, an error of LibreFolio itself: restore uploads answer 503 until {MAX_UPLOAD_VARIABLE} is set to a whole number of megabytes"


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


BACKUP_CONFIG_CHECKS = (check_panel_token, check_upload_limit)
