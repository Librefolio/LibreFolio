"""The sealed nightly backup of a hosting panel (L3): a ``.tar`` whose password only the provider's key opens.

The contract agreed with the cloud coordinator (``LibreFolio_prj/BACKUP-contratto-L3.md``, 2026-10-22) fixes the file:
a POSIX ustar archive, not compressed, of exactly three members in this order:

1. ``manifest.json``, in clear: what the archive is (``format`` ``lfbk-tar``, ``version`` 1), whom its password is
   encrypted for (``recipients``, one or two ``age1…``), the size and SHA-256 of the envelope, when it was made, by which
   LibreFolio and at which database revision. Written in a canonical form; read by its content, unknown keys refused.
2. ``password.age``: the backup's random password (43 base64url characters) encrypted with age for the recipients,
   binary, through ``pyrage``: no cryptography of LibreFolio's own.
3. ``backup.lfbk``: the version-1 envelope of the backup (``envelope.py``), which that password opens.

The two small members come first, so that the first 10 240 bytes hold the manifest, the password and the envelope's
header: a reader checks a copy without downloading it whole. The instance never keeps the password: it lives in the
job's thread, and only whoever holds a recipient's private key reads it back.

The reader here is LibreFolio's own, strict and short: ustar headers only, regular files only, no PAX or GNU header
(the contract lets each side choose its reader, with the same rules). It never extracts by name: it reads the members
at the offsets it checked.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import secrets
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Literal

import pyrage
from pyrage import x25519

from backend.app.services.platform.instance_backup.envelope import HEADER_SIZE, MAGIC, EncryptedFile, EnvelopeError, EnvelopeHeader, EnvelopeKey, _NewFile, unlock_header

MEMBERS = ("manifest.json", "password.age", "backup.lfbk")
FORMAT = "lfbk-tar"
FORMAT_VERSION = 1
#: 32 random bytes in base64url without padding.
PASSWORD_LENGTH = 43
#: The most ``manifest.json`` or ``password.age`` may hold.
SMALL_MEMBER_MAX = 4096
#: What a reader needs to check a copy without the rest: one tar record.
HEAD_BYTES = 10240
FILE_SUFFIX = ".tar"
MAX_RECIPIENTS = 2

_BLOCK = 512
_PASSWORD = re.compile(r"[A-Za-z0-9_-]{43}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MANIFEST_KEYS = frozenset({"format", "version", "recipients", "lfbk_sha256", "lfbk_size", "created_at", "librefolio_version", "db_revision", "password_member"})
_COPY_CHUNK = 1 << 20

SealedErrorCode = Literal["sealed_tar_invalid", "sealed_manifest_invalid", "sealed_no_identity", "sealed_password_invalid", "sealed_identity_invalid"]


class SealedError(Exception):
    """A sealed backup cannot be read or opened: ``code`` says why, in a stable word; the message holds no path or secret.

    ``sealed_tar_invalid``: not the three members of the contract, in order, as plain ustar files. ``sealed_manifest_invalid``:
    a manifest that is not the contract's, or that does not describe the envelope. ``sealed_no_identity``: none of the
    keys given opens the password. ``sealed_password_invalid``: the password opened is not one LibreFolio writes.
    ``sealed_identity_invalid``: a key file that holds no usable age key.
    """

    def __init__(self, code: SealedErrorCode, message: str):
        super().__init__(message)
        self.code: SealedErrorCode = code


@dataclass(frozen=True)
class SealedArchive:
    """A sealed backup, read and checked, nothing decrypted: its manifest, its encrypted password, where its envelope is."""

    manifest: dict[str, Any]
    password_age: bytes
    envelope_offset: int
    envelope_size: int
    envelope_header: EnvelopeHeader


# =============================================================================
# Writing
# =============================================================================


def new_password() -> str:
    """A fresh password for one backup: 32 random bytes in base64url without padding."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")


def seal_password(password: str, recipients: Sequence[str]) -> bytes:
    """``password`` encrypted with age for ``recipients`` (``age1…``), in age's binary form."""
    return pyrage.encrypt(password.encode("ascii"), [x25519.Recipient.from_str(recipient) for recipient in recipients])


def build_manifest(*, created_at: datetime, lfbk_sha256: str, lfbk_size: int, recipients: Sequence[str], librefolio_version: str, db_revision: str | None) -> bytes:
    """``manifest.json`` in its canonical form: sorted keys, no spaces, UTF-8, no final line break."""
    document = {
        "created_at": created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db_revision": db_revision,
        "format": FORMAT,
        "lfbk_sha256": lfbk_sha256,
        "lfbk_size": lfbk_size,
        "librefolio_version": librefolio_version,
        "password_member": MEMBERS[1],
        "recipients": list(recipients),
        "version": FORMAT_VERSION,
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class _HashingFile:
    """What ``tarfile`` writes to: the job's new file, its position, and the SHA-256 of what went through."""

    def __init__(self, target: _NewFile):
        self._target = target
        self._digest = hashlib.sha256()

    def write(self, data: bytes) -> int:
        self._target.write(data)
        self._digest.update(data)
        return len(data)

    def tell(self) -> int:
        return self._target.size

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def write_sealed(dst: Path, *, manifest: bytes, password_age: bytes, envelope: Path, mtime: int) -> EncryptedFile:
    """Write the sealed ``.tar`` at ``dst`` (new, ``0600``, through ``<dst>.part``); its size and SHA-256.

    The members' fields are the contract's (§3.4): mode ``0600``, owner and group 0 without names, ``mtime``; the same
    members give the same bytes. ``FileExistsError`` when ``dst`` exists.
    """
    with _NewFile(dst) as out:
        hashing = _HashingFile(out)
        with tarfile.open(fileobj=hashing, mode="w", format=tarfile.USTAR_FORMAT) as tar:  # type: ignore[call-overload]
            tar.addfile(_member(MEMBERS[0], len(manifest), mtime), io.BytesIO(manifest))
            tar.addfile(_member(MEMBERS[1], len(password_age), mtime), io.BytesIO(password_age))
            with envelope.open("rb") as source:
                tar.addfile(_member(MEMBERS[2], envelope.stat().st_size, mtime), source)
        size = out.size
    return EncryptedFile(size=size, sha256=hashing.hexdigest())


def _member(name: str, size: int, mtime: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime = size, 0o600, mtime
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


# =============================================================================
# Reading
# =============================================================================


def is_sealed(path: Path) -> bool:
    """Whether the file at ``path`` is a POSIX tar, as a sealed backup is; ``False`` for one shorter or unreadable."""
    try:
        with path.open("rb") as handle:
            head = handle.read(_BLOCK)
    except OSError:
        return False
    return len(head) == _BLOCK and head[257:262] == b"ustar"


def read_sealed(path: Path) -> SealedArchive:
    """The sealed backup at ``path``, checked against the contract (§3.5), nothing decrypted. ``SealedError`` otherwise."""
    with path.open("rb") as handle:
        members = _members(handle)
        manifest_raw = _read_at(handle, *members[0][1:])
        password_age = _read_at(handle, *members[1][1:])
        _, offset, size = members[2]
        handle.seek(offset)
        raw_header = handle.read(HEADER_SIZE)
    if len(raw_header) < HEADER_SIZE or not raw_header.startswith(MAGIC):
        raise SealedError("sealed_tar_invalid", "backup.lfbk is not a LibreFolio envelope")
    try:
        header = EnvelopeHeader.from_bytes(raw_header)
    except EnvelopeError:
        raise SealedError("sealed_tar_invalid", "backup.lfbk is not a version-1 envelope this LibreFolio reads") from None
    manifest = _manifest(manifest_raw)
    if manifest["lfbk_size"] != size or manifest["lfbk_sha256"] != _sha256_of(path, offset, size):
        raise SealedError("sealed_manifest_invalid", "The manifest does not describe backup.lfbk: its size or SHA-256 differs")
    return SealedArchive(manifest=manifest, password_age=password_age, envelope_offset=offset, envelope_size=size, envelope_header=header)


def _members(handle: BinaryIO) -> list[tuple[str, int, int]]:
    """The three members as ``(name, data offset, size)``, every header checked; then only the end of the archive: two
    zero blocks, and nothing but zeros up to the end of the file. A member after a single zero block, which ``tar -i``
    would extract, or bytes after the end, are refused (security review of 22/10, finding 2)."""
    members: list[tuple[str, int, int]] = []
    position = 0
    while True:
        handle.seek(position)
        block = handle.read(_BLOCK)
        if len(block) < _BLOCK:
            raise SealedError("sealed_tar_invalid", "The archive is cut short")
        if block == bytes(_BLOCK):
            _end_of_archive(handle)
            break
        if len(members) == len(MEMBERS):
            raise SealedError("sealed_tar_invalid", "The archive holds more than the three members of a sealed backup")
        name, size = _header(block)
        members.append((name, position + _BLOCK, size))
        position += _BLOCK + -(-size // _BLOCK) * _BLOCK
    if tuple(name for name, _, _ in members) != MEMBERS:
        raise SealedError("sealed_tar_invalid", "The archive does not hold manifest.json, password.age and backup.lfbk, in this order")
    for name, _, size in members[:2]:
        if size > SMALL_MEMBER_MAX:
            raise SealedError("sealed_tar_invalid", f"{name} is larger than {SMALL_MEMBER_MAX} bytes")
    return members


def _end_of_archive(handle: BinaryIO) -> None:
    """After the first zero block (just read): a second one, then only zeros to the end of the file."""
    if handle.read(_BLOCK) != bytes(_BLOCK):
        raise SealedError("sealed_tar_invalid", "The archive goes on after a single zero block: it hides something, or is not a sealed backup")
    while chunk := handle.read(_COPY_CHUNK):
        if chunk.count(0) != len(chunk):
            raise SealedError("sealed_tar_invalid", "The archive holds bytes after its end")


def _header(block: bytes) -> tuple[str, int]:
    """The name and size of one ustar header of a regular file; anything else (PAX, GNU, a link, a folder) is refused."""
    if block[257:263] != b"ustar\x00" or block[263:265] != b"00":
        raise SealedError("sealed_tar_invalid", "A member's header is not a POSIX ustar header")
    stored = _octal(block[148:156])
    if stored != sum(block[:148]) + 8 * 32 + sum(block[156:]):
        raise SealedError("sealed_tar_invalid", "A member's header fails its checksum")
    if block[156:157] not in (b"0", b"\x00"):
        raise SealedError("sealed_tar_invalid", "A member is not a regular file")
    if block[345:500].strip(b"\x00"):
        raise SealedError("sealed_tar_invalid", "A member's name has a prefix")
    try:
        name = block[:100].split(b"\x00", 1)[0].decode("ascii")
    except UnicodeDecodeError:
        raise SealedError("sealed_tar_invalid", "A member's name is not ASCII") from None
    return name, _octal(block[124:136])


def _octal(field: bytes) -> int:
    text = field.split(b"\x00", 1)[0].strip()
    if not text or not all(48 <= byte <= 55 for byte in text):
        raise SealedError("sealed_tar_invalid", "A member's header holds a number that is not octal")
    return int(text, 8)


def _read_at(handle: BinaryIO, offset: int, size: int) -> bytes:
    handle.seek(offset)
    data = handle.read(size)
    if len(data) != size:
        raise SealedError("sealed_tar_invalid", "The archive is cut short")
    return data


def _sha256_of(path: Path, offset: int, size: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        handle.seek(offset)
        left = size
        while left:
            chunk = handle.read(min(_COPY_CHUNK, left))
            if not chunk:
                raise SealedError("sealed_tar_invalid", "The archive is cut short")
            digest.update(chunk)
            left -= len(chunk)
    return digest.hexdigest()


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise SealedError("sealed_manifest_invalid", f"The manifest holds the key {key!r} twice")
        document[key] = value
    return document


def _manifest(raw: bytes) -> dict[str, Any]:
    """The manifest's content, checked: the contract's keys, no other, each of its type (§3.2)."""
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError):
        raise SealedError("sealed_manifest_invalid", "The manifest is not JSON in UTF-8") from None
    if not isinstance(document, dict) or set(document) != _MANIFEST_KEYS:
        raise SealedError("sealed_manifest_invalid", "The manifest does not hold exactly the keys of the contract")
    recipients = document["recipients"]
    checks = (
        document["format"] == FORMAT,
        type(document["version"]) is int and document["version"] == FORMAT_VERSION,
        isinstance(recipients, list) and 1 <= len(recipients) <= MAX_RECIPIENTS and all(isinstance(item, str) and item.startswith("age1") for item in recipients),
        isinstance(document["lfbk_sha256"], str) and _SHA256.fullmatch(document["lfbk_sha256"]) is not None,
        type(document["lfbk_size"]) is int and document["lfbk_size"] >= 0,
        isinstance(document["created_at"], str),
        isinstance(document["librefolio_version"], str),
        document["db_revision"] is None or isinstance(document["db_revision"], str),
        document["password_member"] == MEMBERS[1],
    )
    if not all(checks):
        raise SealedError("sealed_manifest_invalid", "The manifest is not the contract's: a format, a version or a value of the wrong kind")
    return document


# =============================================================================
# Keys and opening
# =============================================================================


def read_identities(path: Path) -> list[x25519.Identity]:
    """The age keys of a key file as ``age-keygen`` writes it: comments, blank lines, ``AGE-SECRET-KEY-1…`` lines."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise SealedError("sealed_identity_invalid", "The key file cannot be read") from None
    identities = []
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            identities.append(x25519.Identity.from_str(text))
        except pyrage.IdentityError:
            raise SealedError("sealed_identity_invalid", f"Line {number} of the key file is not an age key") from None
    if not identities:
        raise SealedError("sealed_identity_invalid", "The key file holds no age key")
    return identities


def identity_file_text(identity: x25519.Identity, created_at: datetime) -> str:
    """A key file as ``age-keygen`` writes it, which ``age -d -i`` and ``read_identities`` read."""
    return f"# created: {created_at.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}\n# public key: {identity.to_public()}\n{identity}\n"


def open_password(archive: SealedArchive, identities: Sequence[x25519.Identity]) -> str:
    """The backup's password, opened with one of ``identities``."""
    try:
        clear = pyrage.decrypt(archive.password_age, list(identities))
    except pyrage.DecryptError:
        raise SealedError("sealed_no_identity", "None of the keys given opens the password of this backup") from None
    try:
        password = clear.decode("ascii")
    except UnicodeDecodeError:
        password = ""
    if _PASSWORD.fullmatch(password) is None:
        raise SealedError("sealed_password_invalid", "The password inside is not one LibreFolio writes")
    return password


def check_password(archive: SealedArchive, password: str) -> EnvelopeKey:
    """The key of the envelope, when ``password`` opens it; ``EnvelopeError`` ``wrong_password`` otherwise."""
    return unlock_header(archive.envelope_header, password)


def extract_envelope(path: Path, archive: SealedArchive, dst: Path) -> None:
    """Copy the envelope of the sealed backup at ``path`` to the new file ``dst`` (``0600``, through ``<dst>.part``)."""
    with path.open("rb") as source, _NewFile(dst) as out:
        source.seek(archive.envelope_offset)
        left = archive.envelope_size
        while left:
            chunk = source.read(min(_COPY_CHUNK, left))
            if not chunk:
                raise SealedError("sealed_tar_invalid", "The archive is cut short")
            out.write(chunk)
            left -= len(chunk)
