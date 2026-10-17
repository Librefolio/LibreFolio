"""Backup section of the configuration: the backup of the whole instance.

Owner: workstream B (backup and Docker). Read from the process environment only, never from ``.env``: ``./dev.py`` and
Docker Compose put them there. Every default leaves an install as it was before release 1.3.

``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` (or ``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE``, as Docker secrets mount it) is the
token a hosting panel presents to download backups of the instance (``api/v1/backup/panel.py``). Unset, those routes
answer 404, as if they did not exist.

``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` is the largest archive a restore accepts (decision 43): the hosting provider sets
it, since in the cloud the customer is the administrator. Unset, there is no limit on a self-hosted instance, and the
managed profile's value (500 MB) comes from ``ENVIRONMENT_PROFILE_DEFAULTS`` of ``config/__init__.py`` (H-17).
"""

import os

from backend.app.config import env_secret, profile_default

#: The variable of the hosting panel's token; ``env_secret`` also reads it from ``<name>_FILE``.
PANEL_TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
#: A token hands out a copy of every user's data: a shorter one is refused, so a guessable value never opens the routes.
PANEL_TOKEN_MIN_LENGTH = 32
#: The characters a token may hold: the visible ASCII ones, which an ``Authorization`` header carries as written. A space
#: around a pasted token, or a character outside ASCII, would leave the panel refused at every request, with nothing in
#: the log; refused here, the routes answer 503 and the log names the variable.
PANEL_TOKEN_CHARACTERS = frozenset(chr(code) for code in range(0x21, 0x7F))


class BackupConfigError(ValueError):
    """A ``LIBREFOLIO_BACKUP_*`` value that cannot be used: ``variable`` names it, ``code`` says what is wrong.

    The message names the variable and the rule, never the value of a secret.
    """

    def __init__(self, variable: str, code: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable
        self.code = code


def backup_download_token() -> str | None:
    """``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN``, or the content of its ``_FILE``: the hosting panel's token, as written.

    ``None`` when neither is set: the panel routes are off. A token holding anything but visible ASCII characters (a
    space or a tab included), or shorter than ``PANEL_TOKEN_MIN_LENGTH`` characters, raises ``BackupConfigError``; a
    ``_FILE`` that cannot give its secret raises ``SecretFileError`` (``env_secret``).
    """
    token = env_secret(PANEL_TOKEN_VARIABLE)
    if token is None:
        return None
    if not PANEL_TOKEN_CHARACTERS.issuperset(token):
        raise BackupConfigError(
            PANEL_TOKEN_VARIABLE,
            "BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII",
            "expected visible ASCII characters only, without spaces: a request header carries nothing else as written",
        )
    if len(token) < PANEL_TOKEN_MIN_LENGTH:
        raise BackupConfigError(
            PANEL_TOKEN_VARIABLE,
            "BACKUP_DOWNLOAD_TOKEN_TOO_SHORT",
            f"expected at least {PANEL_TOKEN_MIN_LENGTH} characters, for example the output of `openssl rand -hex 32`",
        )
    return token


#: The variable of the largest archive a restore accepts, in megabytes; 0 is no limit.
MAX_UPLOAD_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"


def backup_max_upload_mb() -> int:
    """``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``: the largest archive a restore accepts, in megabytes; ``0`` is no limit.

    Unset or blank: ``0`` in the ``selfhosted`` profile, the self-hosted default; in any other profile, the profile's
    value (``profile_default``: 500 in the managed profile), and a profile that gives it none, or one of another type,
    raises ``ProfileDefaultError`` (H-37, H-27) rather than give the self-hosted ``0``, which is no limit. Anything but
    a whole number of ASCII digits raises ``BackupConfigError``.
    """
    raw = os.environ.get(MAX_UPLOAD_VARIABLE, "").strip()
    if not raw:
        return profile_default(MAX_UPLOAD_VARIABLE, 0)
    if not (raw.isascii() and raw.isdigit()):
        raise BackupConfigError(MAX_UPLOAD_VARIABLE, "BACKUP_MAX_UPLOAD_MB_INVALID", "expected a whole number of megabytes, 0 for no limit")
    return int(raw)
