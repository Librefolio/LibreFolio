"""The envelope of a «secure» backup (``.lfbk``): the archive encrypted with a password its maker chooses (decisions 38, P12).

LibreFolio's own format, built from standard pieces of ``cryptography``:

- **Key**: scrypt on the password in its NFC form, so a password typed on two keyboards gives one key. ``n = 2^15``,
  ``r = 8``, ``p = 1``: 32 MiB for about a tenth of a second, once per backup or restore, so that each guess costs as
  much (P12: a small machine's memory). The 48 derived bytes are the AES-256 key and a 16-byte check value, which
  tells a wrong password at once, before any data is read.
- **Cipher**: AES-256-GCM over chunks of 1 MiB, the STREAM construction. A chunk's nonce is a random prefix, the
  chunk's counter and a flag set on the last chunk only, and the header is every chunk's associated data: a changed
  byte, a chunk moved, dropped or added, a file cut short at any point, a header edited after the fact, each makes a
  tag fail.
- **Header**, 52 bytes, big-endian: magic ``LFBK``, format version, KDF id, log2(n), r, p, salt (16), check value (16),
  chunk size (4), nonce prefix (7). A reader refuses parameters outside its bounds before any derivation: a hostile or
  newer header never makes it spend more than 64 MiB, twice what is written, nor work for minutes.

The password is never kept: what goes from opening an envelope to reading it is an ``EnvelopeKey``, which never shows
its key. Files are written through ``<name>.part``, readable by their owner only, and published once complete.
"""

from __future__ import annotations

import errno
import hashlib
import hmac
import os
import secrets
import struct
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, Literal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"LFBK"
FORMAT_VERSION = 1
KDF_SCRYPT = 1
SALT_SIZE = 16
CHECK_SIZE = 16
NONCE_PREFIX_SIZE = 7
TAG_SIZE = 16
#: What an envelope is written with (P12).
LOG2_N = 15
R = 8
P = 1
CHUNK_SIZE = 1 << 20
#: What a reader accepts, checked before any derivation: at most ``128 · r · 2^log2_n`` = 64 MiB.
MIN_LOG2_N = 14
MAX_LOG2_N = 16
MAX_R = 8
MAX_P = 2
MIN_CHUNK_SIZE = 1 << 16
MAX_CHUNK_SIZE = 1 << 24
FILE_SUFFIX = ".lfbk"

_HEADER = struct.Struct(">4sBBBBB16s16sI7s")
HEADER_SIZE = _HEADER.size
_KEY_SIZE = 32
_MAX_CHUNKS = 1 << 32
_PART_SUFFIX = ".part"

EnvelopeErrorCode = Literal["wrong_password", "envelope_damaged", "envelope_unsupported"]
Progress = Callable[[int, int], None]


class EnvelopeError(Exception):
    """An envelope cannot be opened or read: ``code`` says why, in a stable word; the message holds no path or secret.

    ``wrong_password``: the password does not open it (or its key parameters were changed). ``envelope_damaged``: not an
    envelope, cut short, or changed. ``envelope_unsupported``: a format version or parameters this LibreFolio does not
    read, most likely from a newer one.
    """

    def __init__(self, code: EnvelopeErrorCode, message: str):
        super().__init__(message)
        self.code: EnvelopeErrorCode = code


@dataclass(frozen=True)
class EnvelopeHeader:
    """The first 52 bytes of an envelope: how its key is derived, and how its chunks are cut and numbered."""

    version: int
    kdf: int
    log2_n: int
    r: int
    p: int
    salt: bytes
    check: bytes
    chunk_size: int
    nonce_prefix: bytes

    def to_bytes(self) -> bytes:
        return _HEADER.pack(MAGIC, self.version, self.kdf, self.log2_n, self.r, self.p, self.salt, self.check, self.chunk_size, self.nonce_prefix)

    @classmethod
    def from_bytes(cls, raw: bytes) -> EnvelopeHeader:
        """The header in ``raw``, exactly ``HEADER_SIZE`` bytes; ``EnvelopeError`` when it is not one this LibreFolio reads."""
        if len(raw) != HEADER_SIZE or not raw.startswith(MAGIC):
            raise EnvelopeError("envelope_damaged", "The file is not a LibreFolio backup envelope, or its header is cut short")
        _magic, version, kdf, log2_n, r, p, salt, check, chunk_size, nonce_prefix = _HEADER.unpack(raw)
        header = cls(version, kdf, log2_n, r, p, salt, check, chunk_size, nonce_prefix)
        _check_supported(header)
        return header


class EnvelopeKey:
    """What opens one envelope: its header and the key its password gives. Neither its repr nor its text shows the key."""

    __slots__ = ("_cipher", "header")

    def __init__(self, header: EnvelopeHeader, key: bytes):
        self.header = header
        self._cipher = AESGCM(key)

    def __repr__(self) -> str:
        return f"EnvelopeKey(version={self.header.version}, log2_n={self.header.log2_n}, r={self.header.r}, p={self.header.p})"

    __str__ = __repr__


@dataclass(frozen=True)
class EncryptedFile:
    """The envelope ``encrypt_file`` wrote: its size and its SHA-256, in hex."""

    size: int
    sha256: str


def is_envelope(path: Path) -> bool:
    """Whether the file at ``path`` starts as an envelope does; ``False`` for a shorter file or one that cannot be read."""
    try:
        with path.open("rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def read_header(path: Path) -> EnvelopeHeader:
    """The header of the envelope at ``path``. ``EnvelopeError`` when it is not one this LibreFolio reads."""
    with path.open("rb") as handle:
        raw = handle.read(HEADER_SIZE)
    return EnvelopeHeader.from_bytes(raw)


def unlock(path: Path, password: str) -> EnvelopeKey:
    """The key of the envelope at ``path`` for ``password``; ``EnvelopeError`` ``wrong_password`` when it does not open it."""
    return unlock_header(read_header(path), password)


def unlock_header(header: EnvelopeHeader, password: str) -> EnvelopeKey:
    """The key of the envelope whose header is ``header`` for ``password``; ``EnvelopeError`` ``wrong_password`` when it
    does not open it. Without the file: a sealed backup (L3) checks the password of the envelope it holds this way."""
    key, check = _derive(password, header)
    if not hmac.compare_digest(check, header.check):
        raise EnvelopeError("wrong_password", "The password does not open this backup")
    return EnvelopeKey(header, key)


def encrypt_file(
    src: Path,
    dst: Path,
    password: str,
    *,
    progress: Progress | None = None,
    salt: bytes | None = None,
    nonce_prefix: bytes | None = None,
    log2_n: int = LOG2_N,
) -> EncryptedFile:
    """Encrypt the file ``src`` into a new envelope ``dst`` with ``password``; its size and SHA-256.

    ``dst`` must not exist (``FileExistsError``). ``salt``, ``nonce_prefix`` and ``log2_n`` are for tests: by default a
    fresh random salt and prefix, and the written cost. ``progress(done, total)`` counts the bytes of ``src`` encrypted.
    """
    salt = secrets.token_bytes(SALT_SIZE) if salt is None else salt
    nonce_prefix = secrets.token_bytes(NONCE_PREFIX_SIZE) if nonce_prefix is None else nonce_prefix
    if len(salt) != SALT_SIZE or len(nonce_prefix) != NONCE_PREFIX_SIZE:
        raise ValueError(f"A salt has {SALT_SIZE} bytes and a nonce prefix {NONCE_PREFIX_SIZE}")
    unchecked = EnvelopeHeader(FORMAT_VERSION, KDF_SCRYPT, log2_n, R, P, salt, bytes(CHECK_SIZE), CHUNK_SIZE, nonce_prefix)
    _check_supported(unchecked)
    total = src.stat().st_size
    key, check = _derive(password, unchecked)
    header = replace(unchecked, check=check).to_bytes()
    cipher = AESGCM(key)
    digest = hashlib.sha256(header)
    done = 0
    with src.open("rb") as source, _NewFile(dst) as out:
        out.write(header)
        for index, chunk, last in _chunks(source, CHUNK_SIZE):
            sealed = cipher.encrypt(_nonce(nonce_prefix, index, last), chunk, header)
            out.write(sealed)
            digest.update(sealed)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
        size = out.size
    return EncryptedFile(size=size, sha256=digest.hexdigest())


def decrypt_file(src: Path, dst: Path, key: EnvelopeKey, *, progress: Progress | None = None) -> int:
    """Decrypt the envelope ``src``, opened with ``key``, into the new file ``dst``; the size of what was written.

    ``dst`` must not exist (``FileExistsError``). ``EnvelopeError`` ``envelope_damaged`` when a chunk fails: nothing is
    left at ``dst``. ``progress(done, total)`` counts the bytes of ``src`` read.
    """
    header = key.header.to_bytes()
    sealed_size = key.header.chunk_size + TAG_SIZE
    total = src.stat().st_size
    written = 0
    with src.open("rb") as source, _NewFile(dst) as out:
        if source.read(HEADER_SIZE) != header:
            raise EnvelopeError("envelope_damaged", "The envelope changed since it was opened")
        done = HEADER_SIZE
        for index, sealed, last in _chunks(source, sealed_size):
            if len(sealed) < TAG_SIZE:
                raise EnvelopeError("envelope_damaged", "The envelope is cut short")
            try:
                chunk = key._cipher.decrypt(_nonce(key.header.nonce_prefix, index, last), sealed, header)
            except InvalidTag:
                raise EnvelopeError("envelope_damaged", "The envelope is damaged or was changed") from None
            out.write(chunk)
            written += len(chunk)
            done += len(sealed)
            if progress is not None:
                progress(done, total)
    return written


def _check_supported(header: EnvelopeHeader) -> None:
    if header.version != FORMAT_VERSION or header.kdf != KDF_SCRYPT:
        raise EnvelopeError("envelope_unsupported", "The backup envelope comes from a newer LibreFolio: update LibreFolio first")
    if not (MIN_LOG2_N <= header.log2_n <= MAX_LOG2_N and 1 <= header.r <= MAX_R and 1 <= header.p <= MAX_P):
        raise EnvelopeError("envelope_unsupported", "The backup envelope asks for a key cost this LibreFolio does not accept")
    if not MIN_CHUNK_SIZE <= header.chunk_size <= MAX_CHUNK_SIZE:
        raise EnvelopeError("envelope_unsupported", "The backup envelope uses a chunk size this LibreFolio does not read")


def _derive(password: str, header: EnvelopeHeader) -> tuple[bytes, bytes]:
    """The AES key and the check value ``password`` gives with the header's salt and cost."""
    if not isinstance(password, str):
        raise TypeError(f"A password is a text, not {type(password).__name__}")
    material = unicodedata.normalize("NFC", password).encode("utf-8")
    derived = Scrypt(salt=header.salt, length=_KEY_SIZE + CHECK_SIZE, n=1 << header.log2_n, r=header.r, p=header.p).derive(material)
    return derived[:_KEY_SIZE], derived[_KEY_SIZE:]


def _nonce(prefix: bytes, index: int, last: bool) -> bytes:
    return prefix + index.to_bytes(4, "big") + (b"\x01" if last else b"\x00")


def _chunks(handle: BinaryIO, size: int) -> Iterator[tuple[int, bytes, bool]]:
    """The file's chunks of ``size`` bytes, numbered, the last one flagged: at least one, empty only for an empty file.

    One chunk is read ahead, so that a chunk is known to be the last before it is handed out.
    """
    current = handle.read(size)
    index = 0
    while True:
        following = handle.read(size) if len(current) == size else b""
        last = not following
        yield index, current, last
        if last:
            return
        index += 1
        if index >= _MAX_CHUNKS:
            raise EnvelopeError("envelope_damaged", "The envelope holds more chunks than its format can number")
        current = following


class _NewFile:
    """A file written through ``<name>.part`` (new, ``0600``, never through a link), synced and renamed once complete;
    removed on any error, so a reader never meets a half-written envelope or archive."""

    def __init__(self, path: Path):
        if os.path.lexists(path):
            raise FileExistsError(errno.EEXIST, "The file already exists", str(path))
        self.path = path
        self.part = path.with_name(path.name + _PART_SUFFIX)
        self.size = 0

    def __enter__(self) -> _NewFile:
        fd = os.open(self.part, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), 0o600)
        self._handle = os.fdopen(fd, "wb")
        return self

    def write(self, data: bytes) -> None:
        self._handle.write(data)
        self.size += len(data)

    def __exit__(self, exc_type, exc, traceback) -> None:
        published = False
        try:
            if exc_type is None:
                self._handle.flush()
                os.fsync(self._handle.fileno())
            self._handle.close()
            if exc_type is None:
                if os.path.lexists(self.path):
                    raise FileExistsError(errno.EEXIST, "The file already exists", str(self.path))
                os.replace(self.part, self.path)
                published = True
                _sync_folder(self.path.parent)
        finally:
            if not published:
                if not self._handle.closed:
                    self._handle.close()
                self.part.unlink(missing_ok=True)


def _sync_folder(folder: Path) -> None:
    """Flush a folder's entries to disk; a platform that cannot open a folder skips it."""
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
