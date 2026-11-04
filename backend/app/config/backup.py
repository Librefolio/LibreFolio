"""Backup section of the configuration: the backup of the whole instance.

Owner: workstream B (backup and Docker). Read from the process environment only, never from ``.env``: ``./dev.py`` and
Docker Compose put them there. Every default leaves an install as it was before release 1.3.

``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` (or ``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE``, as Docker secrets mount it) is the
token a hosting panel presents to download backups of the instance (``api/v1/backup/panel.py``). Unset, those routes
answer 404, as if they did not exist.

``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` is the largest archive a restore accepts (decision 43): the hosting provider sets
it, since in the cloud the customer is the administrator. Unset, there is no limit on a self-hosted instance, and the
managed profile's value (500 MB) comes from ``ENVIRONMENT_PROFILE_DEFAULTS`` of ``config/__init__.py`` (H-17).

``LIBREFOLIO_BACKUP_RECIPIENTS`` (L3) is one or two age recipients (``age1…``), comma-separated: the public keys a
hosting panel's nightly backups are sealed for (``instance_backup/sealed.py``). Not a secret: no ``_FILE``. Unset, the
panel's backups are clear zips on a self-hosted instance, and refused on a managed one.

``LIBREFOLIO_BACKUP_MAX_RESTORE_MB`` is the most an archive may unpack to in a restore's check (B-35): the upload limit
bounds only the compressed archive. Unset, there is no limit on a self-hosted instance; in any other profile it is
``RESTORE_TO_UPLOAD_RATIO`` times the upload limit (decision N82), so it follows the provider's own upload limit.
"""

import os

from backend.app.config import env_secret, get_settings, profile_default

#: The variable of the recipients a hosting panel's backups are sealed for (L3).
RECIPIENTS_VARIABLE = "LIBREFOLIO_BACKUP_RECIPIENTS"
#: Two during a rotation of the key, one otherwise.
MAX_RECIPIENTS = 2

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


#: The variable of the most an archive may unpack to in a restore's check, in megabytes; 0 is no limit (B-35).
MAX_RESTORE_VARIABLE = "LIBREFOLIO_BACKUP_MAX_RESTORE_MB"
#: Outside the self-hosted profile, an unset restore limit is this many times the upload limit (B-35, decision N82).
#: LibreFolio's SQLite databases deflate about 4:1 (measured on 17/10: the test database 4.1, a synthetic price history
#: 3.9) and the uploaded files barely: 8 leaves twice the densest measured, and still cuts deflate's worst case, about
#: 1000:1, by more than a hundred.
RESTORE_TO_UPLOAD_RATIO = 8


def backup_max_restore_mb() -> int:
    """``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``: the most an archive may unpack to in a restore's check, in megabytes; ``0``
    is no limit.

    Unset or blank: ``0`` in the ``selfhosted`` profile, as before 1.3; in any other profile ``RESTORE_TO_UPLOAD_RATIO``
    times the upload limit (``backup_max_upload_mb()``, ``0`` when that is none), raising what that raises
    (``BackupConfigError``, ``ProfileDefaultError``: fail closed). An explicit value always wins, ``0`` included.
    Anything but a whole number of ASCII digits raises ``BackupConfigError``.
    """
    raw = os.environ.get(MAX_RESTORE_VARIABLE, "").strip()
    if not raw:
        if get_settings().LIBREFOLIO_PROFILE == "selfhosted":
            return 0
        return RESTORE_TO_UPLOAD_RATIO * backup_max_upload_mb()
    if not (raw.isascii() and raw.isdigit()):
        raise BackupConfigError(MAX_RESTORE_VARIABLE, "BACKUP_MAX_RESTORE_MB_INVALID", "expected a whole number of megabytes, 0 for no limit")
    return int(raw)


def backup_recipients() -> tuple[str, ...] | None:
    """``LIBREFOLIO_BACKUP_RECIPIENTS``: the age recipients a hosting panel's backups are sealed for, in their canonical
    form (``age1…`` in lower case) and the order written; ``None`` when unset or blank.

    Comma-separated, the spaces around each one ignored. ``BackupConfigError``: ``BACKUP_RECIPIENTS_INVALID`` (an empty
    item, or anything but an X25519 ``age1…`` recipient: an SSH key, a private key), ``BACKUP_RECIPIENTS_TOO_MANY``
    (more than ``MAX_RECIPIENTS``), ``BACKUP_RECIPIENTS_DUPLICATE``. The message never quotes the value: a private key
    pasted by mistake must not reach a log.
    """
    from pyrage import RecipientError, x25519  # noqa: PLC0415 — only when the variable is read

    raw = os.environ.get(RECIPIENTS_VARIABLE, "")
    if not raw.strip():
        return None
    items = [item.strip() for item in raw.split(",")]
    recipients: list[str] = []
    for position, item in enumerate(items, start=1):
        if not item.lower().startswith("age1"):
            raise BackupConfigError(RECIPIENTS_VARIABLE, "BACKUP_RECIPIENTS_INVALID", f"item {position} is not an age recipient: expected age1… as age-keygen prints it")
        try:
            recipient = str(x25519.Recipient.from_str(item))
        except RecipientError:
            raise BackupConfigError(RECIPIENTS_VARIABLE, "BACKUP_RECIPIENTS_INVALID", f"item {position} is not an age recipient: expected age1… as age-keygen prints it") from None
        if recipient in recipients:
            raise BackupConfigError(RECIPIENTS_VARIABLE, "BACKUP_RECIPIENTS_DUPLICATE", f"item {position} repeats an earlier recipient")
        recipients.append(recipient)
    # Counted once every item is one: an empty item between two commas is a typo, said as such.
    if len(recipients) > MAX_RECIPIENTS:
        raise BackupConfigError(RECIPIENTS_VARIABLE, "BACKUP_RECIPIENTS_TOO_MANY", f"expected at most {MAX_RECIPIENTS} recipients, comma-separated")
    return tuple(recipients)


def backup_requires_recipients() -> bool:
    """Whether a hosting panel's backup must be sealed: the managed profile never hands out a clear zip (decision D1, L3)."""
    return get_settings().LIBREFOLIO_PROFILE == "managed"
