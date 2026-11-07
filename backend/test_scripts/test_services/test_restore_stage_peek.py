"""What the opened copy of a check tells before a restore (release 1.3, lot C9-8 and C9-10): ``stage_peek``.

- ``verify_admin_password``: the password of an active administrator of the backup matches its hash in the copy's
  database, a wrong one does not; a username that is no active administrator of the backup is
  ``StageAdminNotFoundError``; a check without its copy (gone, never there, not an id) is ``StageCopyGoneError``. The
  database is opened immutable: nothing is written beside it.
- ``admin_avatar``: the picture an administrator's avatar URL names, among the copy's uploads; ``None`` without one, for a
  URL that is no upload of the copy, and for a link.

How: a copy built under ``tmp_path`` as a check leaves it, with a ``users`` table of the columns read. Isolation: pure.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from backend.app.services.accounts.auth_service import hash_password
from backend.app.services.platform.instance_backup import stage_peek
from backend.app.services.platform.instance_backup.paths import stage_data_dir
from backend.test_scripts.test_utils import print_section, print_success

STAGE = "a" * 32
AVATAR_ID = "0f8fad5b-d9cb-469f-a165-70867728950e"


@pytest.fixture
def data_dir(tmp_path) -> Path:
    root = tmp_path / "data"
    copy = stage_data_dir(root, STAGE)
    (copy / "sqlite").mkdir(parents=True)
    (copy / "custom-uploads").mkdir()
    (copy / "custom-uploads" / f"{AVATAR_ID}.png").write_bytes(b"\x89PNG avatar")
    (copy / "custom-uploads" / f"{AVATAR_ID}.json").write_text("{}")
    with closing(sqlite3.connect(copy / "sqlite" / "app.db")) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, hashed_password TEXT, avatar_url TEXT, is_superuser INTEGER, is_active INTEGER)")
        rows = [
            (1, "ada_admin", hash_password("Right-Pass-123!"), f"/api/v1/uploads/file/{AVATAR_ID}", 1, 1),
            (2, "zoe_admin", hash_password("Other-Pass-456!"), "https://example.org/zoe.png", 1, 1),
            (3, "plain_user", hash_password("User-Pass-789!"), None, 0, 1),
            (4, "old_admin", hash_password("Old-Pass-000!"), None, 1, 0),
        ]
        conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
    return root


def test_the_password_of_an_administrator_of_the_backup_matches_and_a_wrong_one_does_not(data_dir):
    print_section("verify_admin_password")
    assert stage_peek.verify_admin_password(data_dir, STAGE, "ada_admin", "Right-Pass-123!") is True
    assert stage_peek.verify_admin_password(data_dir, STAGE, "ada_admin", "wrong") is False
    assert stage_peek.verify_admin_password(data_dir, STAGE, "zoe_admin", "Right-Pass-123!") is False
    print_success("matches only its own password")


@pytest.mark.parametrize("username", ["plain_user", "old_admin", "nobody"])
def test_only_an_active_administrator_of_the_backup_can_be_asked(data_dir, username):
    with pytest.raises(stage_peek.StageAdminNotFoundError):
        stage_peek.verify_admin_password(data_dir, STAGE, username, "anything")


@pytest.mark.parametrize("stage_id", ["b" * 32, "not-an-id"])
def test_a_check_without_its_copy_is_gone(data_dir, stage_id):
    with pytest.raises(stage_peek.StageCopyGoneError):
        stage_peek.verify_admin_password(data_dir, stage_id, "ada_admin", "Right-Pass-123!")


def test_reading_the_copy_writes_nothing_beside_its_database(data_dir):
    folder = stage_data_dir(data_dir, STAGE) / "sqlite"
    before = sorted(path.name for path in folder.iterdir())
    stage_peek.verify_admin_password(data_dir, STAGE, "ada_admin", "Right-Pass-123!")
    stage_peek.admin_avatar(data_dir, STAGE, "ada_admin")
    assert sorted(path.name for path in folder.iterdir()) == before


def test_the_avatar_of_an_administrator_is_the_upload_of_the_copy_its_url_names(data_dir):
    print_section("admin_avatar")
    picture = stage_peek.admin_avatar(data_dir, STAGE, "ada_admin")
    assert picture is not None and picture.name == f"{AVATAR_ID}.png"
    assert stage_peek.admin_avatar(data_dir, STAGE, "zoe_admin") is None, "a picture outside the copy is never fetched"
    with pytest.raises(stage_peek.StageAdminNotFoundError):
        stage_peek.admin_avatar(data_dir, STAGE, "plain_user")
    print_success("the copy's upload, nothing else")


def test_an_avatar_that_is_a_link_is_not_served(data_dir, tmp_path):
    uploads = stage_data_dir(data_dir, STAGE) / "custom-uploads"
    (uploads / f"{AVATAR_ID}.png").unlink()
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"secret")
    (uploads / f"{AVATAR_ID}.png").symlink_to(outside)
    assert stage_peek.admin_avatar(data_dir, STAGE, "ada_admin") is None


# =====================================================================================================================
# C9-9: a backup the server keeps, taken as the archive of a restore
# =====================================================================================================================


def _kept(tmp_path: Path, monkeypatch, *, name: str = "librefolio-backup-20261107-120000.zip", sealed: bool = False):
    from types import SimpleNamespace  # noqa: PLC0415

    from backend.app.services.platform.instance_backup import retention  # noqa: PLC0415

    folder = tmp_path / "data" / "backups" / "kept-one"
    folder.mkdir(parents=True)
    (folder / name).write_bytes(b"PK\x03\x04 the archive")
    job = SimpleNamespace(job_id="c" * 32, file_name=name, sealed=sealed, created_at=None)
    monkeypatch.setattr(retention, "list_kept", lambda _data_dir: [SimpleNamespace(job=job, folder=folder, size=20)])
    return tmp_path / "data", folder / name


def test_a_kept_backup_becomes_an_upload_by_a_link_and_stays(tmp_path, monkeypatch):
    from backend.app.services.platform.instance_backup import restore_jobs  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.paths import upload_path  # noqa: PLC0415

    print_section("upload_from_kept")
    data_dir, archive = _kept(tmp_path, monkeypatch)
    uploaded = restore_jobs.upload_from_kept("c" * 32, data_dir=data_dir)
    target = upload_path(data_dir, uploaded.upload_id)
    assert (uploaded.kind, uploaded.size) == ("zip", archive.stat().st_size)
    assert target.read_bytes() == archive.read_bytes()
    assert target.stat().st_ino == archive.stat().st_ino, "a hard link: no byte copied"
    target.unlink()
    assert archive.is_file(), "the check removes its upload, never the kept backup"
    print_success("linked, the kept backup untouched")


def test_an_unknown_or_sealed_kept_backup_is_refused(tmp_path, monkeypatch):
    from backend.app.services.platform.instance_backup import restore_jobs  # noqa: PLC0415

    data_dir, _archive = _kept(tmp_path, monkeypatch, name="librefolio-backup-20261107-120000.tar", sealed=True)
    with pytest.raises(restore_jobs.KeptBackupNotFoundError):
        restore_jobs.upload_from_kept("d" * 32, data_dir=data_dir)
    with pytest.raises(restore_jobs.KeptBackupSealedError):
        restore_jobs.upload_from_kept("c" * 32, data_dir=data_dir)
