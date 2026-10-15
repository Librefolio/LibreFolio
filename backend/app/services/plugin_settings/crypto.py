"""Encryption of the secret plugin settings, and the re-encryption a restore needs.

- **Key**: ``derive_key("plugins.settings.v1", 32)`` from the instance key (``services/platform/instance_key.py``,
  workstream H). HKDF has no work factor, so the instance key must be random, never a passphrase: the generated key is,
  and the documentation of ``LIBREFOLIO_INSTANCE_KEY`` says so.
- **Cipher**: AES-256-GCM. The stored blob is a format byte (``1``), a random 96-bit nonce, then the ciphertext with
  its 16-byte tag.
- **Associated data**: the row's context — family, plugin, field, scope and user id — so a ciphertext copied to another
  row, or to another user's, does not decrypt.
- **Key id**: the first 16 bytes of ``HMAC-SHA256(subkey, label)``, in hex. Each row records the key that encrypted it,
  which makes a lost or replaced instance key visible by counting rows, without decrypting anything
  (``plugin_secrets_key_status``), and lets a restore re-encrypt only what needs it. It reveals neither the subkey nor
  the instance key.

A restore (workstream B) works on a ``sqlite3`` copy of the database, after upgrading it to the head revision:
``rekey_plugin_secrets`` re-encrypts the copy's secrets from the backup's key to this instance's, and
``count_unreadable_secrets`` counts what stays unreadable when the backup carries no key. Both take subkeys, never the
instance key, run inside a ``SAVEPOINT`` (atomic on their own, part of the caller's transaction when there is one, and
never committing the caller's work), report counts only, and leave an unreadable row as it is: «set but unreadable,
enter it again», never deleted, never a wrong value. Synchronous on purpose: call them from the app in
``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PluginSystemSetting, PluginUserSetting
from backend.app.services.platform.instance_key import InstanceKeyError, derive_key

#: The purpose of the subkey that encrypts the secrets: fixed, so the same instance key always gives the same subkey.
SUBKEY_PURPOSE = "plugins.settings.v1"
#: The purpose of the subkey that fingerprints the values a call received, for the cache keys.
FINGERPRINT_PURPOSE = "plugins.settings.fingerprint.v1"
SUBKEY_LENGTH = 32

_KEY_ID_LABEL = b"LibreFolio plugin settings key id v1"
_FORMAT = b"\x01"
_NONCE_BYTES = 12
_TABLES = (("plugin_system_settings", "system"), ("plugin_user_settings", "user"))


class UnreadableSecretError(Exception):
    """A stored secret cannot be decrypted with this key: another key, a damaged blob, or a row it was not made for."""


@dataclass(frozen=True)
class UnreadableSecrets:
    """How many stored secrets the current key cannot read, by scope."""

    system: int = 0
    user: int = 0

    @property
    def total(self) -> int:
        return self.system + self.user


@dataclass(frozen=True)
class RekeyReport:
    """What ``rekey_plugin_secrets`` did: counts only, never a name or a value."""

    rekeyed: int = 0
    already_current: int = 0
    unreadable_system: int = 0
    unreadable_user: int = 0


def settings_subkey() -> bytes:
    """The subkey of this instance that encrypts the secret plugin settings."""
    return derive_key(SUBKEY_PURPOSE, SUBKEY_LENGTH)


def fingerprint_subkey() -> bytes:
    """The subkey of this instance that fingerprints the settings a call received."""
    return derive_key(FINGERPRINT_PURPOSE, SUBKEY_LENGTH)


def key_id_of(subkey: bytes) -> str:
    """The id a row records for the key that encrypted it: 32 hex characters."""
    return hmac.new(subkey, _KEY_ID_LABEL, hashlib.sha256).digest()[:16].hex()


def secret_aad(family: str, plugin_code: str, field_key: str, scope: str, user_id: int | None) -> bytes:
    """The associated data that binds a ciphertext to its row."""
    return json.dumps(["lf-plugin-setting/v1", family, plugin_code, field_key, scope, user_id], separators=(",", ":")).encode("utf-8")


def encrypt_secret(subkey: bytes, aad: bytes, plaintext: str) -> bytes:
    """The blob stored for ``plaintext``: format byte, a fresh nonce, the ciphertext and its tag."""
    nonce = os.urandom(_NONCE_BYTES)
    return _FORMAT + nonce + AESGCM(subkey).encrypt(nonce, plaintext.encode("utf-8"), aad)


def decrypt_secret(subkey: bytes, aad: bytes, blob: bytes) -> str:
    """The secret a blob holds; ``UnreadableSecretError`` when this key and this row cannot read it."""
    if len(blob) < 1 + _NONCE_BYTES + 16 or blob[:1] != _FORMAT:
        raise UnreadableSecretError("not a secret blob of a known format")
    nonce, ciphertext = blob[1 : 1 + _NONCE_BYTES], blob[1 + _NONCE_BYTES :]
    try:
        return AESGCM(subkey).decrypt(nonce, ciphertext, aad).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError) as error:
        raise UnreadableSecretError("the secret cannot be decrypted with this key for this row") from error


async def plugin_secrets_key_status(session: AsyncSession) -> UnreadableSecrets:
    """How many stored secrets the instance's key cannot read, counted by key id: all of them when it cannot be used.

    Without stored secrets it reads no key at all, so a check at startup never creates the instance key file. The
    startup check and the admin's Security tab belong to workstream H: they show only the ``system`` count.
    """
    counts = []
    for model in (PluginSystemSetting, PluginUserSetting):
        total = await session.scalar(select(func.count()).select_from(model).where(model.secret_ciphertext.is_not(None)))
        counts.append(int(total or 0))
    if not any(counts):
        return UnreadableSecrets()
    try:
        current = key_id_of(await asyncio.to_thread(settings_subkey))
    except InstanceKeyError:
        return UnreadableSecrets(system=counts[0], user=counts[1])
    foreign = []
    for model in (PluginSystemSetting, PluginUserSetting):
        total = await session.scalar(select(func.count()).select_from(model).where(model.secret_ciphertext.is_not(None), model.key_id != current))
        foreign.append(int(total or 0))
    return UnreadableSecrets(system=foreign[0], user=foreign[1])


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _secret_rows(conn: sqlite3.Connection, table: str, scope: str) -> list[tuple]:
    user_column = "user_id" if scope == "user" else "NULL"
    sql = f"SELECT id, family, plugin_code, field_key, {user_column}, secret_ciphertext, key_id FROM {table} WHERE secret_ciphertext IS NOT NULL"  # noqa: S608 — table names are constants
    return conn.execute(sql).fetchall()


def _readable(subkey: bytes, aad: bytes, blob: bytes) -> str | None:
    try:
        return decrypt_secret(subkey, aad, bytes(blob))
    except UnreadableSecretError:
        return None


def count_unreadable_secrets(conn: sqlite3.Connection, subkey: bytes) -> UnreadableSecrets:
    """How many secrets of the copy ``subkey`` cannot read: another key id, or the right one on a damaged blob."""
    present = _existing_tables(conn)
    current = key_id_of(subkey)
    counts = {"system": 0, "user": 0}
    for table, scope in _TABLES:
        if table not in present:
            continue
        for _row_id, family, plugin_code, field_key, user_id, blob, key_id in _secret_rows(conn, table, scope):
            aad = secret_aad(family, plugin_code, field_key, scope, user_id)
            if key_id != current or _readable(subkey, aad, blob) is None:
                counts[scope] += 1
    return UnreadableSecrets(system=counts["system"], user=counts["user"])


def rekey_plugin_secrets(conn: sqlite3.Connection, old_subkey: bytes, new_subkey: bytes) -> RekeyReport:
    """Re-encrypt the copy's secrets from ``old_subkey`` (the backup's) to ``new_subkey`` (this instance's).

    A row already under the new key is left alone, so a second run changes nothing, and two instances sharing a key
    write nothing. A row under the old key is decrypted with its own context and encrypted again with a fresh nonce. Any
    other row stays as it is and is counted unreadable.
    """
    present = _existing_tables(conn)
    old_id, new_id = key_id_of(old_subkey), key_id_of(new_subkey)
    rekeyed = current = 0
    unreadable = {"system": 0, "user": 0}
    conn.execute("SAVEPOINT lf_rekey_plugin_secrets")
    try:
        for table, scope in _TABLES:
            if table not in present:
                continue
            for row_id, family, plugin_code, field_key, user_id, blob, key_id in _secret_rows(conn, table, scope):
                aad = secret_aad(family, plugin_code, field_key, scope, user_id)
                if key_id == new_id and _readable(new_subkey, aad, blob) is not None:
                    current += 1
                    continue
                plaintext = _readable(old_subkey, aad, blob) if key_id == old_id else None
                if plaintext is None:
                    unreadable[scope] += 1
                    continue
                conn.execute(
                    f"UPDATE {table} SET secret_ciphertext = ?, key_id = ? WHERE id = ?",  # noqa: S608 — table names are constants
                    (encrypt_secret(new_subkey, aad, plaintext), new_id, row_id),
                )
                rekeyed += 1
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT lf_rekey_plugin_secrets")
        conn.execute("RELEASE SAVEPOINT lf_rekey_plugin_secrets")
        raise
    conn.execute("RELEASE SAVEPOINT lf_rekey_plugin_secrets")
    return RekeyReport(rekeyed=rekeyed, already_current=current, unreadable_system=unreadable["system"], unreadable_user=unreadable["user"])
