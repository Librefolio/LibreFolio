"""What the copy a check opened can tell before a restore (release 1.3, lot C9-8 and C9-10).

A check leaves the archive's data opened in ``.restore/stage/<stage id>/data``: a data directory as the restore would put
it in place. Two things an administrator may ask of it before confirming:

- ``verify_admin_password``: whether a password is the one an administrator of the backup signs in with after the
  restore. The hash is read from the copy's database and compared with bcrypt, never logged, kept or sent back.
- ``admin_avatar``: the avatar picture of an administrator of the backup, read from the copy's uploaded files.

Both read the copy only, never the live data, and never through a link. The database is opened read-only and immutable:
nothing is written beside it. A copy that is gone (dropped, expired, or given back because of the space limit) is
``StageCopyGoneError``.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from backend.app.services.accounts.auth_service import verify_password_or_dummy
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, is_job_id, is_plain_dir, stage_data_dir

#: A file id of the uploads (a UUID), as the avatar URL of an account names it: ``/api/v1/uploads/file/<id>``.
_UPLOAD_URL = re.compile(r"^/api/v1/uploads/(?:file/)?([0-9a-fA-F-]{8,64})(?:[/?].*)?$")
_EXTENSION = re.compile(r"^\.[A-Za-z0-9]{1,8}$")


class StageCopyGoneError(Exception):
    """The check has no opened copy any more."""


class StageAdminNotFoundError(Exception):
    """The backup has no active administrator with this username."""


def _copy(data_dir: Path, stage_id: str) -> Path:
    if not is_job_id(stage_id):
        raise StageCopyGoneError("No check has this id")
    root = stage_data_dir(data_dir, stage_id)
    if not is_plain_dir(root) or not (root / DATABASE_ENTRY).is_file() or (root / DATABASE_ENTRY).is_symlink():
        raise StageCopyGoneError("The opened copy of this check is gone")
    return root


def _admin_row(root: Path, username: str) -> tuple[str, str | None]:
    """``(hashed_password, avatar_url)`` of the active administrator ``username`` of the copy."""
    database = (root / DATABASE_ENTRY).resolve()
    with closing(sqlite3.connect(f"{database.as_uri()}?immutable=1", uri=True)) as conn:
        # The avatar is a setting of the account (``user_settings``), which an account may not have yet.
        row = conn.execute(
            "SELECT u.hashed_password, s.avatar_url FROM users AS u LEFT JOIN user_settings AS s ON s.user_id = u.id WHERE u.username = ? AND u.is_superuser = 1 AND u.is_active = 1",
            (username,),
        ).fetchone()
    if row is None:
        raise StageAdminNotFoundError("The backup has no active administrator with this username")
    return str(row[0]), (str(row[1]) if row[1] is not None else None)


def verify_admin_password(data_dir: Path, stage_id: str, username: str, password: str) -> bool:
    """Whether ``password`` is the one the administrator ``username`` of the backup signs in with after the restore.
    ``StageCopyGoneError``, ``StageAdminNotFoundError``. Synchronous: bcrypt is slow on purpose, run it in a thread."""
    hashed, _avatar = _admin_row(_copy(data_dir, stage_id), username)
    return verify_password_or_dummy(password, hashed)


def admin_avatar(data_dir: Path, stage_id: str, username: str) -> Path | None:
    """The avatar picture of the administrator ``username`` of the backup, inside the copy; ``None`` when the account has
    none, or it is not an upload of the copy (a picture elsewhere is never fetched). ``StageCopyGoneError``,
    ``StageAdminNotFoundError``."""
    root = _copy(data_dir, stage_id)
    _hashed, avatar_url = _admin_row(root, username)
    match = _UPLOAD_URL.match(avatar_url or "")
    if match is None:
        return None
    uploads = root / "custom-uploads"
    if not is_plain_dir(uploads):
        return None
    file_id = match.group(1)
    for candidate in uploads.iterdir():
        if candidate.stem == file_id and candidate.suffix != ".json" and _EXTENSION.match(candidate.suffix) and candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None
