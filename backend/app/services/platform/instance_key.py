"""The instance key: one secret per installation, from which every encryption key of LibreFolio is derived.

Owner: workstream H (platform). Consumers never handle the key itself: ``derive_key(purpose)`` gives each purpose a key
of its own, so two uses (the secrets of the plugin settings, the backups) never share one. ``derive_key_from(key,
purpose)`` gives the same derivation from another instance's key, such as the key of a backup being restored.

Where the key comes from, first match wins:

1. ``LIBREFOLIO_INSTANCE_KEY``, the key itself;
2. ``LIBREFOLIO_INSTANCE_KEY_FILE``, a file holding it, as Docker secrets mount it (``env_secret``);
3. ``<data directory>/secrets/instance.key``, generated on first use: 32 random bytes in base64url, the folder ``0700``,
   the file ``0600``.

A key is a text of at least 32 characters, and its UTF-8 bytes are the input of the derivation. A key file that is empty
or too short is an error and is never replaced: whatever was encrypted with the old key would become unreadable. A key
file that is gone looks like a first use, though: a new key is generated, so ``secrets/`` must be restored with the data.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
import re
import secrets
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from backend.app.config import SecretFileError, get_data_dir, read_secret_file
from backend.app.config.platform import configured_instance_key, configured_instance_key_origin

INSTANCE_KEY_FILE = Path("secrets") / "instance.key"
INSTANCE_KEY_MIN_LENGTH = 32
_GENERATED_KEY_BYTES = 32
_DERIVATION_SALT = b"LibreFolio instance key derivation v1"
_PURPOSE = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
_SHA256_SIZE = 32
_HKDF_MAX_LENGTH = 255 * _SHA256_SIZE
_READ_ATTEMPTS = 10
_READ_RETRY_SECONDS = 0.05


class InstanceKeyError(RuntimeError):
    """The instance key cannot be used: its source is unreadable, empty or too short, or the key file cannot be made."""


@dataclass(frozen=True)
class InstanceKeyStatus:
    """What ``instance_key_status()`` finds, without creating the key or raising.

    ``source`` is ``configured`` (the environment), ``generated`` (the key file is there, or its folder cannot be
    searched) or ``not_created`` (no key yet: the first use generates it). ``problem`` says why the key cannot be used, ``None`` when it can. ``loose_modes`` maps
    ``directory`` and ``file`` to their octal mode when group or others have any access to the generated key.
    """

    source: Literal["configured", "generated", "not_created"]
    problem: str | None = None
    path: Path | None = None
    loose_modes: dict[str, str] = field(default_factory=dict)


def instance_key_path() -> Path:
    """Where the generated key lives: ``secrets/instance.key`` in the current data directory."""
    return get_data_dir() / INSTANCE_KEY_FILE


def derive_key(purpose: str, length: int = 32) -> bytes:
    """A key of ``length`` bytes for one ``purpose``, derived from the instance key with HKDF-SHA256.

    ``purpose`` names the use and its version, such as ``plugins.settings.v1``: lowercase letters, digits and
    ``. _ : -``, at most 128 characters. The same purpose always gets the same key while the instance key stays the
    same; two purposes never get the same key. The length is part of the derivation too: the same purpose at two
    lengths gives two unrelated keys, never one key and its prefix. Without a configured key, the first call generates
    the key file. Raises ``ValueError`` for an invalid purpose or length, before reading the key, and
    ``InstanceKeyError`` when the key cannot be used.
    """
    _check_purpose_and_length(purpose, length)
    return _derive(_instance_key(), purpose, length)


def derive_key_from(key: str, purpose: str, length: int = 32) -> bytes:
    """The key that ``derive_key(purpose, length)`` gives on an instance whose instance key is ``key``.

    For a key that is not this instance's: a restore re-encrypts what the instance of a backup encrypted with its own
    key (workstream B). A password-protected archive carries that key when LibreFolio generated it (decision 39, lot
    B4); otherwise (a clear archive, or a key the environment gives) it comes from the administrator's copy of the old
    ``secrets/instance.key``, read with ``read_secret_file()`` as this module reads its own, or from the old
    ``LIBREFOLIO_INSTANCE_KEY``. It reads neither the environment nor the data directory and never creates the key file.
    ``key`` is the text of the key, at least ``INSTANCE_KEY_MIN_LENGTH`` characters. Raises ``ValueError`` for an
    invalid purpose or length, before looking at the key, ``TypeError`` for a key that is not a text and
    ``InstanceKeyError`` for a key too short; no message holds the key.
    """
    _check_purpose_and_length(purpose, length)
    if not isinstance(key, str):
        raise TypeError(f"An instance key is a text, not {type(key).__name__}")
    return _derive(_checked(key, "the given key"), purpose, length)


def _check_purpose_and_length(purpose: str, length: int) -> None:
    if not _PURPOSE.fullmatch(purpose):
        raise ValueError(f"Invalid key purpose {purpose!r}: lowercase letters, digits and . _ : - only, at most 128 characters")
    if not isinstance(length, int) or not 0 < length <= _HKDF_MAX_LENGTH:
        raise ValueError(f"A derived key has 1 to {_HKDF_MAX_LENGTH} bytes, not {length!r}")


def _derive(key: str, purpose: str, length: int) -> bytes:
    """HKDF-SHA256 of the key's UTF-8 bytes; the purpose and the length are both in the context, so neither can be swapped."""
    info = purpose.encode("ascii") + b"\x00" + length.to_bytes(2, "big")
    return hkdf_sha256(key.encode("utf-8"), salt=_DERIVATION_SALT, info=info, length=length)


def hkdf_sha256(key_material: bytes, *, salt: bytes, info: bytes, length: int) -> bytes:
    """HKDF with SHA-256 (RFC 5869): extract a pseudorandom key from ``key_material``, then expand it to ``length`` bytes."""
    if not 0 < length <= _HKDF_MAX_LENGTH:
        raise ValueError(f"HKDF-SHA256 gives 1 to {_HKDF_MAX_LENGTH} bytes, not {length}")
    pseudorandom_key = hmac.new(salt, key_material, hashlib.sha256).digest()
    output, block, counter = b"", b"", 1
    while len(output) < length:
        block = hmac.new(pseudorandom_key, block + info + bytes([counter]), hashlib.sha256).digest()
        output += block
        counter += 1
    return output[:length]


def instance_key_status() -> InstanceKeyStatus:
    """The state of the instance key, read without creating the key file and without raising."""
    try:
        configured = configured_instance_key()
    except SecretFileError as exc:
        return InstanceKeyStatus("configured", problem=str(exc))
    if configured is not None:
        return InstanceKeyStatus("configured", problem=_length_problem(configured, _configured_origin()))
    path = instance_key_path()
    try:
        if not _key_file_present(path):
            return InstanceKeyStatus("not_created", path=path)
        problem = _length_problem(read_secret_file(path, "instance key file"), str(path))
    except (InstanceKeyError, SecretFileError) as exc:
        problem = str(exc)
    return InstanceKeyStatus("generated", problem=problem, path=path, loose_modes=_loose_modes(path))


def _instance_key() -> str:
    """The instance key, generating the key file on first use when the environment configures none."""
    try:
        configured = configured_instance_key()
    except SecretFileError as exc:
        raise InstanceKeyError(str(exc)) from exc
    if configured is not None:
        return _checked(configured, _configured_origin())
    path = instance_key_path()
    if not _key_file_present(path):
        try:
            _create_key_file(path)
        except OSError as exc:
            raise InstanceKeyError(f"{path}: the instance key cannot be generated ({exc.strerror or type(exc).__name__})") from exc
    return _read_generated_key(path)


def _read_generated_key(path: Path) -> str:
    """The key of the generated file; an unusable file is an error, never replaced.

    Without hard links, the file appears before its content (``_create_exclusively``): a read that finds it unusable
    is retried for up to half a second, the time for the process that created it to finish writing.
    """
    attempt = 1
    while True:
        try:
            return _checked(read_secret_file(path, "instance key file"), str(path))
        except (SecretFileError, InstanceKeyError) as exc:
            if attempt >= _READ_ATTEMPTS:
                raise InstanceKeyError(f"{exc}: restore the file from a backup; a new key could not read what the old one encrypted") from exc
        time.sleep(_READ_RETRY_SECONDS)
        attempt += 1


def _configured_origin() -> str:
    """The variable the configured key comes from, with the file path for ``LIBREFOLIO_INSTANCE_KEY_FILE``."""
    return configured_instance_key_origin() or "LIBREFOLIO_INSTANCE_KEY"


def _key_file_present(path: Path) -> bool:
    """Whether something is at the key file's path, a dangling link included.

    A folder that cannot be searched (another owner, mode ``0000``) raises ``InstanceKeyError``: the key may be there,
    so it is neither generated again nor reported as missing.
    """
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise InstanceKeyError(f"{path}: the instance key cannot be reached ({exc.strerror or type(exc).__name__})") from exc
    return True


def _length_problem(key: str, origin: str) -> str | None:
    if len(key) < INSTANCE_KEY_MIN_LENGTH:
        return f"{origin}: the instance key is {len(key)} characters long, it needs at least {INSTANCE_KEY_MIN_LENGTH}"
    return None


def _checked(key: str, origin: str) -> str:
    problem = _length_problem(key, origin)
    if problem is not None:
        raise InstanceKeyError(problem)
    return key


def _create_key_file(path: Path) -> None:
    """Generate the key file unless another process got there first: the first key published stays, no other replaces it.

    The key is written to a temporary file in the same folder and published with a hard link, which fails when the
    file exists: readers never see a half-written key, and of several workers starting together one key wins. A
    filesystem without hard links falls back to an exclusive create.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    content = (secrets.token_urlsafe(_GENERATED_KEY_BYTES) + "\n").encode("ascii")
    descriptor, temporary = tempfile.mkstemp(prefix=".instance.key-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return
        except OSError:
            if not _create_exclusively(path, content):
                return
    finally:
        os.unlink(temporary)
    _sync_directory(path.parent)


def _create_exclusively(path: Path, content: bytes) -> bool:
    """Create ``path`` holding ``content`` only if it does not exist: ``False`` when another process created it first."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _sync_directory(directory: Path) -> None:
    """Make the new entry survive a power cut; a platform that cannot open a folder (Windows) skips it."""
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        with contextlib.suppress(OSError):
            os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _loose_modes(path: Path) -> dict[str, str]:
    """The octal modes of the key folder and file that give group or others any access; none on Windows."""
    if os.name == "nt":
        return {}
    loose = {}
    for target, label in ((path.parent, "directory"), (path, "file")):
        try:
            mode = target.stat().st_mode & 0o777
        except OSError:
            continue
        if mode & 0o077:
            loose[label] = f"{mode:04o}"
    return loose
