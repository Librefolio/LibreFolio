"""Plugin settings, the encryption of the secrets and the re-encryption a restore needs (plan 03, CP10, §4.5).

Module under test: ``services/plugin_settings/crypto.py``. The contract pinned here:

1. **Cipher**: AES-256-GCM; a blob is the format byte ``1``, a fresh 96-bit nonce, then the ciphertext and its 16-byte tag;
   the plaintext never appears in it, and two encryptions of one value differ. Anything else — another key, a changed
   byte, an unknown format, a blob too short — is ``UnreadableSecretError``, whose message never holds the plaintext.
2. **Associated data**: the row's context, ``["lf-plugin-setting/v1", family, plugin, field, scope, user_id]`` in JSON:
   a blob moved to another user, field, scope, plugin or family does not decrypt, and two different contexts never
   serialise alike.
3. **Key id**: the first 16 bytes of ``HMAC-SHA256(subkey, "LibreFolio plugin settings key id v1")`` in hex — stable
   for a subkey, different for another, revealing neither. The subkeys come from the instance key with two fixed
   purposes, ``plugins.settings.v1`` and ``plugins.settings.fingerprint.v1``: another instance key gives other subkeys.
4. **A restore** (workstream B) on a ``sqlite3`` copy: ``count_unreadable_secrets`` counts, by scope and read-only, the
   secrets a subkey cannot read (another key id, or the right one on a damaged blob, or a row the blob was not made
   for); ``rekey_plugin_secrets`` re-encrypts the rows of the old subkey under the new one with a fresh nonce, leaves a
   current row alone (a second run writes nothing, nor does a run between two instances sharing a key) and leaves every
   other row exactly as it is, counted unreadable by scope. Without the tables (a backup older than 007) both give
   zeros. Both work inside a ``SAVEPOINT``: on their own they commit; inside the caller's transaction they are part of
   it and its rollback undoes them; a structural error undoes their own work only and propagates.
5. **At startup** (workstream H): ``plugin_secrets_key_status`` counts the secrets stored under another key id, by
   scope, without decrypting, deriving the key in a worker thread — with no secret stored it reads no key at all, so it
   never creates the key file; with an unusable key it raises nothing and counts every stored secret.

Pure: every database is a private file under ``tmp_path`` built by ``SQLModel.metadata.create_all``; the restore
functions get fixed test subkeys, never a real key; where an instance key is needed it is a test key set with
``monkeypatch``, and the data directory points into ``tmp_path`` so that no key file can ever be created elsewhere.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.services.platform.instance_key import derive_key
from backend.app.services.plugin_settings import crypto
from backend.app.services.plugin_settings.crypto import (
    FINGERPRINT_PURPOSE,
    SUBKEY_PURPOSE,
    RekeyReport,
    UnreadableSecretError,
    UnreadableSecrets,
    count_unreadable_secrets,
    decrypt_secret,
    encrypt_secret,
    fingerprint_subkey,
    key_id_of,
    plugin_secrets_key_status,
    rekey_plugin_secrets,
    secret_aad,
    settings_subkey,
)
from backend.test_scripts.test_utils import print_section, print_success

KEY_A = "LibreFolio-plugin-settings-test-key-A-0123456789"
KEY_B = "LibreFolio-plugin-settings-test-key-B-9876543210"
#: Fixed test subkeys for the restore functions: never derived from a real key.
OLD = bytes(range(32))
NEW = bytes(range(100, 132))
OTHER = bytes([7]) * 32
KEY_ID_LABEL = b"LibreFolio plugin settings key id v1"
STAMP = "2026-10-15 12:00:00.000000"

SYSTEM_TABLE, USER_TABLE = "plugin_system_settings", "plugin_user_settings"


def _marker() -> str:
    return f"SECRET-{uuid.uuid4().hex}"


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture
def instance_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The test key A as the instance key, and a data directory of this test: no key file can be read or made elsewhere."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data_dir))
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY_FILE", raising=False)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_A)
    return data_dir


def _build_schema(db: Path, usernames: tuple[str, ...] = ("alice", "bob")) -> dict[str, int]:
    """A private database with the whole ORM schema and a few users; their ids by name."""
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            users = {name: User(username=name, email=f"{name}@example.test", hashed_password="$argon2id$test") for name in usernames}
            session.add_all(users.values())
            session.commit()
            return {name: user.id for name, user in users.items()}
    finally:
        engine.dispose()


@pytest.fixture
def copy_db(tmp_path: Path) -> tuple[Path, dict[str, int]]:
    """The 'copy' a restore works on: a private file at the head schema, with two users."""
    db = tmp_path / "copy.db"
    return db, _build_schema(db)


@contextmanager
def _connect(db: Path) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(db)) as conn:
        yield conn


def _insert_secret(conn: sqlite3.Connection, scope: str, family: str, code: str, key: str, user_id: int | None, blob: bytes, key_id: str) -> int:
    """One secret row, written with plain SQL as a restored copy holds it."""
    if scope == "system":
        sql = f"INSERT INTO {SYSTEM_TABLE} (family, plugin_code, field_key, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        return conn.execute(sql, (family, code, key, blob, key_id, STAMP)).lastrowid
    sql = f"INSERT INTO {USER_TABLE} (user_id, family, plugin_code, field_key, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    return conn.execute(sql, (user_id, family, code, key, blob, key_id, STAMP)).lastrowid


def _insert_plain(conn: sqlite3.Connection, scope: str, code: str, key: str, value: object, user_id: int | None = None) -> int:
    if scope == "system":
        sql = f"INSERT INTO {SYSTEM_TABLE} (family, plugin_code, field_key, value_json, updated_at) VALUES ('asset', ?, ?, ?, ?)"
        return conn.execute(sql, (code, key, json.dumps(value), STAMP)).lastrowid
    sql = f"INSERT INTO {USER_TABLE} (user_id, family, plugin_code, field_key, value_json, updated_at) VALUES (?, 'asset', ?, ?, ?, ?)"
    return conn.execute(sql, (user_id, code, key, json.dumps(value), STAMP)).lastrowid


def _encrypted(subkey: bytes, scope: str, family: str, code: str, key: str, user_id: int | None, plaintext: str) -> bytes:
    return encrypt_secret(subkey, secret_aad(family, code, key, scope, user_id), plaintext)


def _snapshot(db: Path) -> dict[str, list[tuple]]:
    """Every row of the two tables, exactly as SQLite holds them."""
    with _connect(db) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall() for table in (SYSTEM_TABLE, USER_TABLE)}


def _row(db: Path, table: str, row_id: int) -> tuple[bytes, str]:
    """(secret_ciphertext, key_id) of one row, read by a connection of its own: what is committed."""
    with _connect(db) as conn:
        blob, key_id = conn.execute(f"SELECT secret_ciphertext, key_id FROM {table} WHERE id = ?", (row_id,)).fetchone()
    return bytes(blob), key_id


def _plain_rows(db: Path) -> dict[str, list[tuple]]:
    """The rows that hold a plain value, every column, by table."""
    with _connect(db) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} WHERE value_json IS NOT NULL ORDER BY id").fetchall() for table in (SYSTEM_TABLE, USER_TABLE)}


# =============================================================================
# 1. THE CIPHER
# =============================================================================


def test_a_secret_roundtrips_and_the_blob_has_the_documented_shape():
    """1: format byte 1, a 12-byte nonce, the ciphertext and a 16-byte tag; the plaintext nowhere in the blob."""
    print_section("1: AES-256-GCM roundtrip")
    plaintext = f"{_marker()} — ünïcödé ✓"
    aad = secret_aad("asset", "lab", "api_key", "system", None)

    blob = encrypt_secret(OLD, aad, plaintext)

    assert blob[:1] == b"\x01", "the format byte"
    assert len(blob) == 1 + 12 + len(plaintext.encode("utf-8")) + 16
    assert plaintext.encode("utf-8") not in blob
    assert decrypt_secret(OLD, aad, blob) == plaintext
    print_success("decrypted back; 1 + 12 + n + 16 bytes; no plaintext in the blob")


def test_two_encryptions_of_one_value_differ():
    """1: a fresh nonce each time: two rows holding the same secret do not show it."""
    aad = secret_aad("asset", "lab", "api_key", "system", None)
    first, second = encrypt_secret(OLD, aad, "same-secret-value"), encrypt_secret(OLD, aad, "same-secret-value")

    assert first != second and first[1:13] != second[1:13]
    assert decrypt_secret(OLD, aad, first) == decrypt_secret(OLD, aad, second) == "same-secret-value"


@pytest.mark.parametrize(
    "damage",
    [
        pytest.param(lambda blob: blob[:-1] + bytes([blob[-1] ^ 1]), id="tag-changed"),
        pytest.param(lambda blob: blob[:20] + bytes([blob[20] ^ 1]) + blob[21:], id="ciphertext-changed"),
        pytest.param(lambda blob: blob[:5] + bytes([blob[5] ^ 1]) + blob[6:], id="nonce-changed"),
        pytest.param(lambda blob: b"\x02" + blob[1:], id="unknown-format"),
        pytest.param(lambda blob: blob[:28], id="too-short"),
        pytest.param(lambda blob: b"", id="empty"),
    ],
)
def test_a_damaged_blob_is_unreadable(damage):
    aad = secret_aad("asset", "lab", "api_key", "system", None)
    plaintext = _marker()
    blob = encrypt_secret(OLD, aad, plaintext)

    with pytest.raises(UnreadableSecretError) as unreadable:
        decrypt_secret(OLD, aad, damage(blob))
    assert plaintext not in str(unreadable.value)


def test_another_key_cannot_read_a_secret():
    aad = secret_aad("asset", "lab", "api_key", "system", None)
    with pytest.raises(UnreadableSecretError):
        decrypt_secret(NEW, aad, encrypt_secret(OLD, aad, "s3cret-value"))


# =============================================================================
# 2. ASSOCIATED DATA
# =============================================================================

_HOME = ("asset", "lab", "personal_token", "user", 7)


@pytest.mark.parametrize(
    "moved",
    [
        pytest.param(("asset", "lab", "personal_token", "user", 8), id="another-user"),
        pytest.param(("asset", "lab", "other_token", "user", 7), id="another-field"),
        pytest.param(("asset", "lab", "personal_token", "system", None), id="to-the-instance"),
        pytest.param(("asset", "other", "personal_token", "user", 7), id="another-plugin"),
        pytest.param(("fx", "lab", "personal_token", "user", 7), id="another-family"),
    ],
)
def test_a_blob_moved_to_another_row_does_not_decrypt(moved):
    """2: the AAD binds a ciphertext to its row: copied anywhere else, it is unreadable, never another user's value."""
    blob = encrypt_secret(OLD, secret_aad(*_HOME), "s3cret-of-user-7")

    with pytest.raises(UnreadableSecretError):
        decrypt_secret(OLD, secret_aad(*moved), blob)
    assert decrypt_secret(OLD, secret_aad(*_HOME), blob) == "s3cret-of-user-7", "control: at home it decrypts"


def test_the_associated_data_is_the_documented_json_and_never_ambiguous():
    """2: ``["lf-plugin-setting/v1", family, plugin, field, scope, user_id]``; a separator inside a name cannot fake another context."""
    assert secret_aad("asset", "mockprov", "api_key", "system", None) == b'["lf-plugin-setting/v1","asset","mockprov","api_key","system",null]'
    assert secret_aad("asset", "a,b", "c", "user", 1) != secret_aad("asset", "a", "b,c", "user", 1)
    assert secret_aad("asset", "a", "b", "user", 0) != secret_aad("asset", "a", "b", "user", None)


# =============================================================================
# 3. KEY ID AND SUBKEYS
# =============================================================================


def test_the_key_id_is_the_documented_hmac_stable_and_key_dependent():
    """3: 32 hex characters, ``HMAC-SHA256(subkey, label)[:16]``; the same for one subkey, another for another."""
    key_id = key_id_of(OLD)

    assert key_id == hmac.new(OLD, KEY_ID_LABEL, hashlib.sha256).digest()[:16].hex()
    assert len(key_id) == 32 and int(key_id, 16) >= 0
    assert key_id_of(OLD) == key_id and key_id_of(NEW) != key_id
    assert OLD.hex() not in key_id and key_id not in OLD.hex()


def test_the_subkeys_come_from_the_instance_key_with_their_fixed_purposes(instance_key: Path, monkeypatch: pytest.MonkeyPatch):
    """3: ``plugins.settings.v1`` and ``plugins.settings.fingerprint.v1``, 32 bytes; another instance key, other subkeys."""
    print_section("3: the subkeys")
    assert (SUBKEY_PURPOSE, FINGERPRINT_PURPOSE) == ("plugins.settings.v1", "plugins.settings.fingerprint.v1")

    encryption, fingerprint = settings_subkey(), fingerprint_subkey()
    assert len(encryption) == len(fingerprint) == 32 and encryption != fingerprint
    assert encryption == derive_key("plugins.settings.v1", 32) and fingerprint == derive_key("plugins.settings.fingerprint.v1", 32)
    assert settings_subkey() == encryption, "the same instance key always gives the same subkey"

    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", KEY_B)
    assert settings_subkey() != encryption and fingerprint_subkey() != fingerprint
    assert key_id_of(settings_subkey()) != key_id_of(encryption)
    assert not (instance_key / "secrets").exists(), "a configured key never creates the key file"
    print_success("two distinct 32-byte subkeys, other ones under another instance key, no key file")


# =============================================================================
# 4. A RESTORE: COUNT AND REKEY ON A sqlite3 COPY
# =============================================================================


@pytest.fixture
def mixed_copy(copy_db) -> dict:
    """The copy of a backup with every kind of row, as ``rekey`` and ``count`` meet them.

    Under OLD (the backup's key): two readable system secrets, one readable user secret, a system one with its tag
    damaged, a user one copied onto another user (AAD mismatch). Under NEW (this instance): one system and one user
    secret. Under a third key: one of each scope. And two plain rows, which neither function may touch.
    """
    db, users = copy_db
    alice, bob = users["alice"], users["bob"]
    plaintexts: dict[int | tuple, str] = {}
    with _connect(db) as conn:
        rows = {}
        for name, (scope, key, subkey, user_id) in {
            "sys_old_1": ("system", "api_key", OLD, None),
            "sys_old_2": ("system", "other_key", OLD, None),
            "usr_old": ("user", "personal_token", OLD, alice),
            "sys_new": ("system", "third_key", NEW, None),
            "usr_new": ("user", "second_token", NEW, alice),
            "sys_other": ("system", "fourth_key", OTHER, None),
            "usr_other": ("user", "personal_token", OTHER, bob),
        }.items():
            plaintext = _marker()
            blob = _encrypted(subkey, scope, "asset", "lab", key, user_id, plaintext)
            rows[name] = (SYSTEM_TABLE if scope == "system" else USER_TABLE, _insert_secret(conn, scope, "asset", "lab", key, user_id, blob, key_id_of(subkey)))
            plaintexts[name] = plaintext
        damaged = bytearray(_encrypted(OLD, "system", "asset", "lab", "damaged_key", None, "s3cret-damaged"))
        damaged[-1] ^= 1
        rows["sys_damaged"] = (SYSTEM_TABLE, _insert_secret(conn, "system", "asset", "lab", "damaged_key", None, bytes(damaged), key_id_of(OLD)))
        moved = _encrypted(OLD, "user", "asset", "lab", "moved_token", alice, "s3cret-of-alice")
        rows["usr_moved"] = (USER_TABLE, _insert_secret(conn, "user", "asset", "lab", "moved_token", bob, moved, key_id_of(OLD)))
        rows["sys_plain"] = (SYSTEM_TABLE, _insert_plain(conn, "system", "lab", "region", "us"))
        rows["usr_plain"] = (USER_TABLE, _insert_plain(conn, "user", "lab", "limit", 7, alice))
        conn.commit()
    return {"db": db, "users": users, "rows": rows, "plaintexts": plaintexts}


def test_count_reads_the_unreadable_secrets_by_scope_and_writes_nothing(mixed_copy):
    """4: under NEW, unreadable are the OLD and third-key rows: by key id, and the damaged one even with OLD."""
    print_section("4: count_unreadable_secrets")
    db = mixed_copy["db"]
    before = _snapshot(db)
    with _connect(db) as conn:
        under_new = count_unreadable_secrets(conn, NEW)
        under_old = count_unreadable_secrets(conn, OLD)
        assert conn.total_changes == 0 and not conn.in_transaction, "count is read-only"

    # NEW reads sys_new and usr_new; every other secret (OLD ×3 system incl. damaged, OLD ×2 user incl. moved, third key ×2) is unreadable.
    assert under_new == UnreadableSecrets(system=4, user=3), under_new
    # OLD reads sys_old_1, sys_old_2, usr_old; the damaged and the moved rows carry its key id but do not decrypt.
    assert under_old == UnreadableSecrets(system=3, user=3), under_old
    assert under_new.total == 7
    assert _snapshot(db) == before
    print_success(f"under the new key {under_new}, under the old {under_old}; nothing written")


def test_rekey_reencrypts_the_old_rows_leaves_the_rest_and_reports_counts_only(mixed_copy):
    """4: OLD rows decryptable in their own context get NEW with a fresh nonce; current rows stay; the others stay as they are."""
    print_section("4: rekey_plugin_secrets")
    db, rows, plaintexts = mixed_copy["db"], mixed_copy["rows"], mixed_copy["plaintexts"]
    alice = mixed_copy["users"]["alice"]
    before = {name: _row(db, *rows[name]) for name in rows if not name.endswith("_plain")}
    plain_before = _plain_rows(db)

    with _connect(db) as conn:
        report = rekey_plugin_secrets(conn, OLD, NEW)
        assert not conn.in_transaction, "on its own the rekey commits"

    assert report == RekeyReport(rekeyed=3, already_current=2, unreadable_system=2, unreadable_user=2), report
    contexts = {"sys_old_1": ("api_key", "system", None), "sys_old_2": ("other_key", "system", None), "usr_old": ("personal_token", "user", alice)}
    for name, (key, scope, user_id) in contexts.items():
        blob, key_id = _row(db, *rows[name])
        assert key_id == key_id_of(NEW), f"{name}: a re-encrypted row records the new key id"
        assert blob[1:13] != before[name][0][1:13], f"{name}: a fresh nonce"
        assert decrypt_secret(NEW, secret_aad("asset", "lab", key, scope, user_id), blob) == plaintexts[name], f"{name}: the same secret, under the new key"
    for name in ("sys_new", "usr_new", "sys_other", "usr_other", "sys_damaged", "usr_moved"):
        assert _row(db, *rows[name]) == before[name], f"{name} must be left exactly as it was"
    assert _plain_rows(db) == plain_before, "the plain rows must be left exactly as they were"
    print_success(f"{report}")


def test_a_second_rekey_writes_nothing(mixed_copy):
    """4: idempotent: the second run finds every readable row current, the unreadable ones unchanged, and writes nothing."""
    db = mixed_copy["db"]
    with _connect(db) as conn:
        first = rekey_plugin_secrets(conn, OLD, NEW)
    after_first = _snapshot(db)

    with _connect(db) as conn:
        second = rekey_plugin_secrets(conn, OLD, NEW)
        assert conn.total_changes == 0, f"the second run wrote {conn.total_changes} row(s)"

    assert second == RekeyReport(rekeyed=0, already_current=first.rekeyed + first.already_current, unreadable_system=first.unreadable_system, unreadable_user=first.unreadable_user)
    assert _snapshot(db) == after_first


def test_two_instances_sharing_a_key_write_nothing(copy_db):
    """4: old and new subkey alike: every row is current, no write."""
    db, users = copy_db
    with _connect(db) as conn:
        _insert_secret(conn, "system", "asset", "lab", "api_key", None, _encrypted(OLD, "system", "asset", "lab", "api_key", None, "s3cret-1"), key_id_of(OLD))
        _insert_secret(conn, "user", "asset", "lab", "token", users["alice"], _encrypted(OLD, "user", "asset", "lab", "token", users["alice"], "s3cret-2"), key_id_of(OLD))
        conn.commit()
    before = _snapshot(db)

    with _connect(db) as conn:
        report = rekey_plugin_secrets(conn, OLD, OLD)
        assert conn.total_changes == 0

    assert report == RekeyReport(rekeyed=0, already_current=2)
    assert _snapshot(db) == before


def test_without_the_tables_both_give_zeros(tmp_path: Path):
    """4: a copy older than 007 has no plugin tables: zeros, and no error."""
    db = tmp_path / "before-007.db"
    with _connect(db) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        conn.commit()
        assert count_unreadable_secrets(conn, NEW) == UnreadableSecrets()
        assert rekey_plugin_secrets(conn, OLD, NEW) == RekeyReport()
        conn.execute(f"CREATE TABLE {SYSTEM_TABLE} (id INTEGER PRIMARY KEY, family TEXT, plugin_code TEXT, field_key TEXT, secret_ciphertext BLOB, key_id TEXT)")
        conn.execute(f"INSERT INTO {SYSTEM_TABLE} (family, plugin_code, field_key, secret_ciphertext, key_id) VALUES ('asset', 'lab', 'k', ?, ?)", (_encrypted(OTHER, "system", "asset", "lab", "k", None, "s3cret-x"), key_id_of(OTHER)))
        conn.commit()
        assert count_unreadable_secrets(conn, NEW) == UnreadableSecrets(system=1, user=0), "one table present: that one is counted"


def test_inside_the_callers_transaction_the_rekey_is_undone_by_its_rollback(mixed_copy):
    """4: B's open transaction: the rekey joins it, never commits B's work, and B's rollback undoes both."""
    print_section("4: rekey inside the caller's transaction")
    db, rows = mixed_copy["db"], mixed_copy["rows"]
    before = _snapshot(db)

    with _connect(db) as conn:
        conn.execute("BEGIN")
        _insert_plain(conn, "system", "lab", "callers_row", "written by the caller")
        report = rekey_plugin_secrets(conn, OLD, NEW)
        assert conn.in_transaction, "the rekey must not end the caller's transaction"
        assert _row(db, *rows["sys_old_1"])[1] == key_id_of(OLD), "nothing is committed while the caller's transaction is open"
        conn.rollback()

    assert report.rekeyed == 3, "barrier: the rekey did re-encrypt inside the transaction, or the rollback proves nothing"
    assert _snapshot(db) == before, "the caller's rollback must undo the rekey and the caller's own row"
    print_success("joined the caller's transaction; its rollback undid everything")


def test_inside_the_callers_transaction_a_committed_rekey_lands_with_the_callers_work(mixed_copy):
    """4: the same, committed by the caller: the rekey and the caller's row land together."""
    db, rows = mixed_copy["db"], mixed_copy["rows"]
    with _connect(db) as conn:
        conn.execute("BEGIN")
        callers_row = _insert_plain(conn, "system", "lab", "callers_row", "written by the caller")
        rekey_plugin_secrets(conn, OLD, NEW)
        conn.commit()

    assert _row(db, *rows["sys_old_1"])[1] == key_id_of(NEW)
    with _connect(db) as conn:
        assert conn.execute(f"SELECT field_key FROM {SYSTEM_TABLE} WHERE id = ?", (callers_row,)).fetchone() == ("callers_row",)


@pytest.mark.parametrize("callers_transaction", [False, True], ids=["standalone", "in-the-callers-transaction"])
def test_a_structural_error_undoes_the_rekeys_own_work_and_propagates(mixed_copy, monkeypatch: pytest.MonkeyPatch, callers_transaction: bool):
    """4: an error after the first re-encrypted row rolls back to the savepoint: no row of the rekey stays; the caller's work does."""
    db = mixed_copy["db"]
    before = _snapshot(db)
    real_encrypt, calls = crypto.encrypt_secret, []

    def failing_encrypt(subkey: bytes, aad: bytes, plaintext: str) -> bytes:
        calls.append(aad)
        if len(calls) == 2:
            raise RuntimeError("disk full while re-encrypting")
        return real_encrypt(subkey, aad, plaintext)

    monkeypatch.setattr(crypto, "encrypt_secret", failing_encrypt)
    with _connect(db) as conn:
        if callers_transaction:
            conn.execute("BEGIN")
            _insert_plain(conn, "system", "lab", "callers_row", "kept")
        with pytest.raises(RuntimeError, match="disk full"):
            rekey_plugin_secrets(conn, OLD, NEW)
        assert conn.in_transaction is callers_transaction, "the caller's transaction stays open; a standalone run leaves none"
        if callers_transaction:
            assert conn.execute(f"SELECT COUNT(*) FROM {SYSTEM_TABLE} WHERE field_key = 'callers_row'").fetchone() == (1,), "the caller's own row survives the rekey's failure"
            conn.rollback()

    assert len(calls) == 2, "barrier: one row was re-encrypted before the failure, or there was nothing to undo"
    assert _snapshot(db) == before, "the row re-encrypted before the error must be rolled back"


# =============================================================================
# 5. AT STARTUP: THE KEY STATUS, WITHOUT DECRYPTING
# =============================================================================


@pytest_asyncio.fixture
async def private_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the ORM schema, opened as production opens its own; disposed at teardown."""
    db = tmp_path / "status.db"
    _build_schema(db, ())
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _add_user(engine: AsyncEngine, name: str) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=f"{name}@example.test", hashed_password="$argon2id$test")
        session.add(user)
        await session.commit()
        return user.id


def _no_key(*_args, **_kwargs):
    raise AssertionError("the key was derived: plugin_secrets_key_status must read no key without stored secrets")


@pytest.mark.asyncio
async def test_without_secrets_the_status_reads_no_key(private_engine: AsyncEngine, instance_key: Path, monkeypatch: pytest.MonkeyPatch):
    """5: no row, then only plain rows: zeros, and the subkey is never derived (a startup check creates no key file)."""
    print_section("5: no stored secret, no key read")
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY")
    monkeypatch.setattr(crypto, "settings_subkey", _no_key)
    alice = await _add_user(private_engine, "alice")

    async with AsyncSession(private_engine) as session:
        assert await plugin_secrets_key_status(session) == UnreadableSecrets()
        session.add(PluginSystemSetting(family="asset", plugin_code="lab", field_key="region", value_json='"us"'))
        session.add(PluginUserSetting(user_id=alice, family="asset", plugin_code="lab", field_key="limit", value_json="7"))
        await session.commit()
        assert await plugin_secrets_key_status(session) == UnreadableSecrets()

    assert not (instance_key / "secrets").exists(), "no key file may be created by a status read without secrets"
    print_success("zeros twice, the key never derived, no key file")


@pytest.mark.asyncio
async def test_the_status_counts_the_secrets_of_another_key_by_scope(private_engine: AsyncEngine, instance_key: Path, monkeypatch: pytest.MonkeyPatch):
    """5: counted by key id against the current subkey, never decrypted: a current row with a damaged blob counts as fine."""
    print_section("5: the key status by scope")
    current = settings_subkey()
    monkeypatch.setattr(crypto, "decrypt_secret", lambda *_args: pytest.fail("the status must not decrypt"))
    alice, bob = await _add_user(private_engine, "alice"), await _add_user(private_engine, "bob")

    def secret_row(model, key: str, subkey: bytes, user_id: int | None = None, *, damaged: bool = False):
        scope = "user" if model is PluginUserSetting else "system"
        blob = bytearray(_encrypted(subkey, scope, "asset", "lab", key, user_id, _marker()))
        if damaged:
            blob[-1] ^= 1
        extra = {"user_id": user_id} if model is PluginUserSetting else {}
        return model(family="asset", plugin_code="lab", field_key=key, secret_ciphertext=bytes(blob), key_id=key_id_of(subkey), updated_at=datetime(2026, 10, 15), **extra)

    async with AsyncSession(private_engine) as session:
        session.add_all(
            [
                secret_row(PluginSystemSetting, "current", current),
                secret_row(PluginSystemSetting, "current_damaged", current, damaged=True),
                secret_row(PluginSystemSetting, "foreign_1", OTHER),
                secret_row(PluginSystemSetting, "foreign_2", NEW),
                secret_row(PluginUserSetting, "current", current, alice),
                secret_row(PluginUserSetting, "foreign", OTHER, bob),
                PluginSystemSetting(family="asset", plugin_code="lab", field_key="plain", value_json="1"),
            ]
        )
        await session.commit()
        status = await plugin_secrets_key_status(session)

    assert status == UnreadableSecrets(system=2, user=1), status
    assert status.total == 3
    print_success(f"{status}: by key id, without decrypting")


async def _store_three_secrets_and_a_plain_value(engine: AsyncEngine) -> None:
    """Two system secrets and one of a user, under the current key; and a plain row, which is never counted."""
    alice = await _add_user(engine, "alice")
    subkey = settings_subkey()
    rows = [
        PluginSystemSetting(family="asset", plugin_code="lab", field_key="api_key", secret_ciphertext=_encrypted(subkey, "system", "asset", "lab", "api_key", None, _marker()), key_id=key_id_of(subkey)),
        PluginSystemSetting(family="fx", plugin_code="LAB", field_key="api_key", secret_ciphertext=_encrypted(subkey, "system", "fx", "LAB", "api_key", None, _marker()), key_id=key_id_of(subkey)),
        PluginUserSetting(user_id=alice, family="asset", plugin_code="lab", field_key="token", secret_ciphertext=_encrypted(subkey, "user", "asset", "lab", "token", alice, _marker()), key_id=key_id_of(subkey)),
        PluginSystemSetting(family="asset", plugin_code="lab", field_key="region", value_json='"us"'),
    ]
    async with AsyncSession(engine) as session:
        session.add_all(rows)
        await session.commit()


@pytest.mark.asyncio
async def test_with_an_unusable_key_the_status_counts_every_secret_as_unreadable(private_engine: AsyncEngine, instance_key: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """5: ``LIBREFOLIO_INSTANCE_KEY_FILE`` naming a file that is gone: no exception, every stored secret counted, by scope."""
    print_section("5: the key status with an unusable key")
    await _store_three_secrets_and_a_plain_value(private_engine)
    monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY")
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY_FILE", str(tmp_path / "gone-instance.key"))

    async with AsyncSession(private_engine) as session:
        status = await plugin_secrets_key_status(session)

    assert status == UnreadableSecrets(system=2, user=1), status
    assert not (instance_key / "secrets").exists(), "an unusable configured key is never replaced by a generated one"
    print_success(f"{status}: all of them, and nothing raised")


@pytest.mark.asyncio
async def test_the_status_derives_the_key_off_the_event_loop(private_engine: AsyncEngine, instance_key: Path, monkeypatch: pytest.MonkeyPatch):
    """5: deriving the key reads the environment and maybe a file: in a worker thread, never on the loop's own thread."""
    await _store_three_secrets_and_a_plain_value(private_engine)
    real, threads = crypto.settings_subkey, []

    def recording() -> bytes:
        threads.append(threading.get_ident())
        return real()

    monkeypatch.setattr(crypto, "settings_subkey", recording)
    async with AsyncSession(private_engine) as session:
        status = await plugin_secrets_key_status(session)

    assert status == UnreadableSecrets(), "every secret is under the current key"
    assert threads and all(thread != threading.get_ident() for thread in threads), f"derived on the loop's thread: {threads}"
