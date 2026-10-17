"""The «secure» backup's rules: the password that protects an archive, and the instance key it may carry.

- **The password** (P12) follows the rules of the accounts (``services/accounts/password_policy.py``, decision 37),
  with a minimum of 12 characters: a backup holds every user's data, and whoever has the file can try passwords
  offline at their own pace. LibreFolio never generates it: whoever makes the backup chooses it, and gives it again to
  restore (decision 38).
- **The instance key** (decision 39) travels only inside a password-protected archive, and only when LibreFolio
  generated it (``secrets/instance.key``). A key given by the environment (``LIBREFOLIO_INSTANCE_KEY``, its ``_FILE``
  form, a hosting panel) never leaves: whoever gave it keeps it. The key is read with ``read_secret_file()``, as the
  instance key module reads its own (workstream H); it is never created here.
"""

from __future__ import annotations

from backend.app.config import SecretFileError, read_secret_file
from backend.app.services.accounts.password_policy import PasswordRule, failed_rules, rules_with_minimum_length
from backend.app.services.platform.instance_backup.archive import INSTANCE_KEY_MAX_BYTES
from backend.app.services.platform.instance_key import INSTANCE_KEY_MIN_LENGTH, instance_key_status

#: P12: the shortest password an archive accepts, unless the accounts' own minimum is longer.
ARCHIVE_PASSWORD_MIN_LENGTH = 12
#: The longest one: a password, not a file.
ARCHIVE_PASSWORD_MAX_LENGTH = 1024


def archive_password_rules() -> tuple[PasswordRule, ...]:
    """The rules a backup's password must meet: the accounts' rules, with at least ``ARCHIVE_PASSWORD_MIN_LENGTH`` characters."""
    return rules_with_minimum_length(ARCHIVE_PASSWORD_MIN_LENGTH)


def archive_password_problems(password: str) -> list[str]:
    """The codes of the rules ``password`` misses as a backup's password, in the rules' order; empty when it meets them."""
    return failed_rules(password, rules=archive_password_rules())


def exportable_instance_key() -> str | None:
    """The instance key a password-protected backup carries: the generated one, when it can be used; else ``None``.

    ``None`` for a key the environment configures, for an instance that has none yet (nothing is encrypted with a key
    that does not exist), and for a generated key that cannot be used (``generated_key_unusable``), a key longer than an
    archive can give back included. Never creates the key file, never raises.
    """
    status = instance_key_status()
    if status.source != "generated" or status.problem is not None or status.path is None:
        return None
    try:
        key = read_secret_file(status.path, "instance key file")
    except SecretFileError:
        return None
    return key if _fits_an_archive(key) else None


def generated_key_unusable() -> bool:
    """Whether a generated instance key is there but cannot be used: a secure backup then leaves it out, with a warning.

    Unusable: H's status names a problem, or the key is longer than an archive can give back (``INSTANCE_KEY_MAX_BYTES``
    in UTF-8: every restore refuses a longer entry; lot B4b). Never raises.
    """
    status = instance_key_status()
    if status.source != "generated":
        return False
    if status.problem is not None:
        return True
    if status.path is None:
        return False
    try:
        key = read_secret_file(status.path, "instance key file")
    except SecretFileError:
        return True
    return len(key.encode("utf-8")) > INSTANCE_KEY_MAX_BYTES


def _fits_an_archive(key: str) -> bool:
    """Whether a key can travel in an archive and come back: as long as H asks, and no longer in UTF-8 than every restore
    reads (``INSTANCE_KEY_MAX_BYTES``)."""
    return len(key) >= INSTANCE_KEY_MIN_LENGTH and len(key.encode("utf-8")) <= INSTANCE_KEY_MAX_BYTES
