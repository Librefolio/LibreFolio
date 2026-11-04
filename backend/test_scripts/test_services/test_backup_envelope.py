"""
Instance backup, the envelope of a «secure» archive (workstream B, lot B4): ``instance_backup/envelope.py``, the ``.lfbk``.

The contract frozen for B4 (§1; decisions 38 and P12), pinned here:

(a) The file. A 52-byte header, big-endian: ``0-3`` the magic ``LFBK`` · ``4`` version 1 · ``5`` kdf 1 (scrypt) ·
    ``6`` log2(n) · ``7`` r · ``8`` p · ``9-24`` salt · ``25-40`` check value · ``41-44`` chunk size (u32) · ``45-51``
    nonce prefix. Then the plaintext in chunks of the chunk size, at least one: the last holds the rest, empty only for
    an empty file, full when the size is a multiple. Each chunk is ``AESGCM(key).encrypt(nonce, chunk, header)``, the
    chunk and its 16-byte tag, the 52 header bytes as associated data, ``nonce = prefix (7) ‖ counter (u32, from 0) ‖
    0x00, or 0x01 on the last chunk``. B4 writes log2(n) 15, r 8, p 1 and 1 MiB chunks, with a fresh salt and nonce
    prefix each time. Pinned byte for byte against the same construction computed here with ``cryptography``'s own
    ``Scrypt`` and ``AESGCM``.
(b) The key. ``Scrypt(salt, length=48, n=2**log2_n, r, p)`` on the password in NFC, as UTF-8: the AES-256 key is bytes
    0-31, the check value bytes 32-47. A wrong check value is ``wrong_password``; so, by design, is a changed salt,
    log2(n), r, p or check byte. ``EnvelopeKey`` never shows the AES key, in its ``repr`` or its ``str``.
(c) The read bounds, checked before scrypt runs: fewer than 52 bytes, or another magic, is ``envelope_damaged``; a
    version or a kdf other than 1, log2(n) outside 14..16, r outside 1..8, p outside 1..2, a chunk size outside
    64 KiB..16 MiB is ``envelope_unsupported``, in milliseconds, whatever the header asks for.
(d) Integrity. A changed chunk size or nonce prefix (the header is every chunk's associated data), a changed byte of a
    chunk or of a tag, a truncation (at a chunk boundary, inside a chunk, down to the header alone), a chunk appended,
    repeated, dropped or swapped: the envelope still unlocks, and ``decrypt_file`` refuses it as ``envelope_damaged``,
    leaving nothing behind: neither the destination nor its ``.part``.
(e) The files. Written through ``<dst name>.part`` beside ``dst``, 0600 from its creation, renamed onto ``dst`` at the
    end: an existing ``dst`` is ``FileExistsError`` and keeps its bytes; any failure removes the ``.part``.
    ``progress(done, total)`` counts the source's bytes, never going back, up to the source's size. Memory stays
    constant: 24 MiB go through within 8 MiB of traced allocations. ``is_envelope``: the first four bytes are ``LFBK``.

Pure: every file lives in ``tmp_path``; no database, no server, no network. The module is imported by each test (the
``envelope`` fixture, and the two envelopes sealed once for the module), never at collection: until lot B4 writes it,
every test fails on its own with the ``ModuleNotFoundError`` of ``backend.app.services.platform.instance_backup.envelope``.

Scrypt is honest but cheap: the tests that pin the default derive at log2(n) 15 (~0.1 s); the others pass
``log2_n=14`` to ``encrypt_file``, the only function that takes it. A derivation that must not happen is caught twice:
scrypt is replaced by a recorder that refuses to run (the module's ``Scrypt``, ``cryptography``'s, ``hashlib``'s), and
the refusal must come within 50 ms (best of three), while a derivation at the base header's log2(n) 15 takes twice that.
No megabyte is left to pytest's diff: large bytes are compared through their first difference or their SHA-256.
tracemalloc does not see OpenSSL's memory, so scrypt's own 16 MiB never counts against the budget. A write is observed
half-way through its ``progress`` callback: a three-chunk file reports its bytes as it goes, which the UI's phases
``encrypting`` and ``decrypting`` rely on. File modes are POSIX-only.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import importlib
import os
import random
import stat
import time
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf import scrypt as cryptography_scrypt
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.test_scripts.test_utils import print_section, print_success

ENVELOPE_MODULE = "backend.app.services.platform.instance_backup.envelope"

POSIX = os.name != "nt"
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")

# The contract's values (§1), written here independently of the module.
MAGIC = b"LFBK"
HEADER_SIZE = 52
TAG_SIZE = 16
#: The chunk size B4 writes: 1 MiB.
CHUNK = 1 << 20
#: The derivation B4 writes: scrypt n = 2^15, r = 8, p = 1 (P12).
DEFAULT_LOG2_N, R, P = 15, 8, 1
#: What a test that derives several times passes to ``encrypt_file``: the lowest log2(n) the reader accepts.
FAST_LOG2_N = 14
#: Every constant the module publishes, with the contract's value.
CONTRACT_CONSTANTS = {
    "MAGIC": b"LFBK",
    "FORMAT_VERSION": 1,
    "KDF_SCRYPT": 1,
    "HEADER_SIZE": 52,
    "SALT_SIZE": 16,
    "CHECK_SIZE": 16,
    "NONCE_PREFIX_SIZE": 7,
    "TAG_SIZE": 16,
    "LOG2_N": 15,
    "R": 8,
    "P": 1,
    "CHUNK_SIZE": 1 << 20,
    "MIN_LOG2_N": 14,
    "MAX_LOG2_N": 16,
    "MAX_R": 8,
    "MAX_P": 2,
    "MIN_CHUNK_SIZE": 1 << 16,
    "MAX_CHUNK_SIZE": 1 << 24,
    "FILE_SUFFIX": ".lfbk",
}

#: Where the header's fields lie.
VERSION_AT, KDF_AT, LOG2_N_AT, R_AT, P_AT = 4, 5, 6, 7, 8
SALT_AT = slice(9, 25)
CHECK_AT = slice(25, 41)
CHUNK_SIZE_AT = slice(41, 45)
NONCE_PREFIX_AT = slice(45, 52)

PASSWORD = "Correct-Horse-Battery-9"
#: The fixed inputs of the known answers and of the headers built here.
SALT = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
CHECK = bytes.fromhex("c0c1c2c3c4c5c6c7c8c9cacbcccdcecf")
NONCE_PREFIX = bytes.fromhex("a0a1a2a3a4a5a6")
#: The last chunk of the three-chunk envelope the tampering tests start from: two full chunks, then these bytes.
LAST_CHUNK_BYTES = 4321
#: A header refused before scrypt answers in microseconds; scrypt at the base header's log2(n) 15 alone takes ~0.1 s.
REFUSAL_SECONDS = 0.05
#: The constant-memory case: 24 MiB through the envelope, within 8 MiB of traced allocations.
MEMORY_FILE_SIZE = 24 * CHUNK
MEMORY_BUDGET = 8 * CHUNK

#: One password for a human, two strings for Python: «é» precomposed (U+00E9), and «e» with the combining acute (U+0301).
COMPOSED = "Caff\u00e9-Corretto-2026"
DECOMPOSED = "Caffe\u0301-Corretto-2026"
#: Latin with diacritics, Greek, Chinese and an emoji: «Pässwört-κλειδί-密码-🔑-42».
NON_ASCII = "P\u00e4ssw\u00f6rt-\u03ba\u03bb\u03b5\u03b9\u03b4\u03af-\u5bc6\u7801-\U0001f511-42"
#: Compatibility characters NFC keeps and NFKC would fold: the «ﬁ» ligature, a full-width letter and full-width digits.
COMPATIBLE = "\ufb01nance-\uff30ass-\uff12\uff10\uff12\uff16"
COMPATIBLE_FOLDED = "finance-Pass-2026"


# =============================================================================
# Helpers
# =============================================================================


def _envelope_module() -> ModuleType:
    """``instance_backup.envelope``, imported when a test runs and never at collection: until lot B4 writes it, each
    test fails on its own with the module's ``ModuleNotFoundError``, the red this file is written to give."""
    return importlib.import_module(ENVELOPE_MODULE)


@pytest.fixture
def envelope() -> ModuleType:
    """The module under test, for the test that asks for it."""
    return _envelope_module()


@pytest.fixture
def no_derivation(envelope: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every scrypt the module could reach, replaced by a recorder that refuses to derive; the list of the attempts.

    The name the module imports (``Scrypt``, set even where the module has none), ``cryptography``'s own class for a
    module that reaches it through its package, and ``hashlib.scrypt`` for one that would not use ``cryptography``.
    """
    attempts: list[str] = []

    def refuse(*args: object, **kwargs: object) -> None:
        attempts.append(f"args={args!r} kwargs={kwargs!r}")
        raise AssertionError("scrypt was called for a header that must be refused before any derivation")

    monkeypatch.setattr(envelope, "Scrypt", refuse, raising=False)
    monkeypatch.setattr(cryptography_scrypt, "Scrypt", refuse)
    monkeypatch.setattr(hashlib, "scrypt", refuse, raising=False)
    return attempts


@dataclass(frozen=True)
class Sealed:
    """An envelope sealed once for the module: the tampering tests' common start, never changed (each builds its own file)."""

    path: Path

    def parts(self) -> tuple[bytes, list[bytes]]:
        """The 52-byte header, and the chunks as written: each its ciphertext and its 16-byte tag."""
        raw = self.path.read_bytes()
        step = CHUNK + TAG_SIZE
        return raw[:HEADER_SIZE], [raw[start : start + step] for start in range(HEADER_SIZE, len(raw), step)]


def _seal_once(tmp_path_factory: pytest.TempPathFactory, name: str, size: int) -> Sealed:
    """``size`` bytes sealed at log2(n) 14 with ``PASSWORD``, in a folder of the module's own."""
    module = _envelope_module()
    folder = tmp_path_factory.mktemp(name)
    src = _write(folder / "plain.zip", _payload(size, seed=name))
    path = folder / f"{name}.lfbk"
    module.encrypt_file(src, path, PASSWORD, log2_n=FAST_LOG2_N)
    return Sealed(path)


@pytest.fixture(scope="module")
def three_chunks(tmp_path_factory: pytest.TempPathFactory) -> Sealed:
    """Two full chunks and a last one of 4321 bytes."""
    return _seal_once(tmp_path_factory, "three-chunks", 2 * CHUNK + LAST_CHUNK_BYTES)


@pytest.fixture(scope="module")
def two_full_chunks(tmp_path_factory: pytest.TempPathFactory) -> Sealed:
    """Exactly two chunks: a size that is a multiple of the chunk size ends on a full chunk, no empty one after it."""
    return _seal_once(tmp_path_factory, "two-full-chunks", 2 * CHUNK)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _listing(folder: Path) -> list[str]:
    """The names in ``folder``, sorted."""
    return sorted(os.listdir(folder))


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _payload(size: int, seed: str = "payload") -> bytes:
    """``size`` bytes that look random, as a zip's do, and are the same at every run: a mistake shows on any byte."""
    return random.Random(f"{seed}-{size}").randbytes(size)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    """The SHA-256 of a file, read by blocks: a large one is never whole in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _difference(actual: bytes, expected: bytes) -> str | None:
    """``None`` when the two are equal, else where they part: never a diff of megabytes for pytest to print."""
    if actual == expected:
        return None
    common = min(len(actual), len(expected))
    first = next((index for index in range(common) if actual[index] != expected[index]), common)
    return f"{len(actual)} bytes against {len(expected)} expected, first difference at byte {first}"


def _header(
    *,
    magic: bytes = MAGIC,
    version: int = 1,
    kdf: int = 1,
    log2_n: int = DEFAULT_LOG2_N,
    r: int = R,
    p: int = P,
    salt: bytes = SALT,
    check: bytes = CHECK,
    chunk_size: int = CHUNK,
    nonce_prefix: bytes = NONCE_PREFIX,
) -> bytes:
    """The 52 bytes of §1, big-endian: ``0-3`` magic · ``4`` version · ``5`` kdf · ``6`` log2(n) · ``7`` r · ``8`` p ·
    ``9-24`` salt · ``25-40`` check · ``41-44`` chunk size (u32) · ``45-51`` nonce prefix."""
    return magic + bytes([version, kdf, log2_n, r, p]) + salt + check + chunk_size.to_bytes(4, "big") + nonce_prefix


def _derive(secret: bytes, salt: bytes, log2_n: int, r: int = R, p: int = P) -> bytes:
    """The 48 bytes of §1, computed here with ``cryptography``'s own ``Scrypt``: the AES key ``[0:32]``, the check value
    ``[32:48]``. ``secret`` is the password already in NFC and UTF-8: each test says which bytes it means."""
    return Scrypt(salt=salt, length=48, n=2**log2_n, r=r, p=p).derive(secret)


def _nonce(prefix: bytes, counter: int, last: bool) -> bytes:
    """``prefix (7) ‖ counter (u32, big-endian, from 0) ‖ 0x01 on the last chunk, else 0x00``: 12 bytes."""
    return prefix + counter.to_bytes(4, "big") + (b"\x01" if last else b"\x00")


def _expected_envelope(plaintext: bytes, secret: bytes, *, salt: bytes, nonce_prefix: bytes, log2_n: int) -> tuple[bytes, bytes]:
    """The envelope §1 describes, built from ``cryptography``'s primitives alone, and the 48 derived bytes.

    Chunks of 1 MiB, at least one: an empty file is one empty chunk; a multiple of the chunk size ends on a full chunk.
    """
    derived = _derive(secret, salt, log2_n)
    header = _header(log2_n=log2_n, salt=salt, check=derived[32:48], nonce_prefix=nonce_prefix)
    pieces = [plaintext[start : start + CHUNK] for start in range(0, len(plaintext), CHUNK)] or [b""]
    aead = AESGCM(derived[:32])
    body = b"".join(aead.encrypt(_nonce(nonce_prefix, index, index == len(pieces) - 1), piece, header) for index, piece in enumerate(pieces))
    return header + body, derived


def _authentic(key: bytes, nonce: bytes, chunk: bytes, header: bytes) -> bytes | None:
    """The plaintext of ``chunk`` when its tag holds for that key, nonce and header; ``None`` when it does not."""
    try:
        return AESGCM(key).decrypt(nonce, chunk, header)
    except InvalidTag:
        return None


def _chunk_count(size: int) -> int:
    """``max(1, ceil(size / CHUNK))``: an empty file still has its one, empty, chunk."""
    return max(1, -(-size // CHUNK))


def _flip(data: bytes, index: int) -> bytes:
    """``data`` with the lowest bit of the byte at ``index`` flipped (a negative index counts from the end)."""
    changed = bytearray(data)
    changed[index] ^= 0x01
    return bytes(changed)


def _with_byte(data: bytes, index: int, value: int) -> bytes:
    """``data`` with the byte at ``index`` set to ``value``."""
    changed = bytearray(data)
    changed[index] = value
    return bytes(changed)


def _refused(envelope: ModuleType, call: Callable[[], object]) -> str:
    """The ``code`` of the ``EnvelopeError`` that ``call`` raises; any other outcome fails the test where it happens."""
    with pytest.raises(envelope.EnvelopeError) as raised:
        call()
    return raised.value.code


def _seal(envelope: ModuleType, folder: Path, plaintext: bytes, password: str = PASSWORD) -> Path:
    """``plaintext`` written as ``folder/plain.zip`` and sealed at log2(n) 14 into ``folder/sealed/backup.lfbk``."""
    src = _write(folder / "plain.zip", plaintext)
    dst = folder / "sealed" / "backup.lfbk"
    dst.parent.mkdir(parents=True)
    envelope.encrypt_file(src, dst, password, log2_n=FAST_LOG2_N)
    return dst


def _open(envelope: ModuleType, sealed: Path, password: str, restored: Path) -> int:
    """``sealed`` unlocked with ``password`` and decrypted into ``restored``: what ``decrypt_file`` returns."""
    restored.parent.mkdir(parents=True, exist_ok=True)
    key = envelope.unlock(sealed, password)
    return envelope.decrypt_file(sealed, restored, key)


def _assert_damaged(envelope: ModuleType, tmp_path: Path, content: bytes) -> None:
    """``content`` unlocks with the right password (its check value is intact), then ``decrypt_file`` refuses it as
    ``envelope_damaged`` and leaves nothing in the destination's folder: no file under the final name, no ``.part``."""
    tampered = _write(tmp_path / "tampered.lfbk", content)
    key = envelope.unlock(tampered, PASSWORD)
    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    code = _refused(envelope, lambda: envelope.decrypt_file(tampered, restored_dir / "backup.zip", key))
    assert code == "envelope_damaged", f"decrypt_file of a damaged envelope must answer envelope_damaged: {code}"
    assert _listing(restored_dir) == [], f"nothing may be left, neither backup.zip nor its .part: {_listing(restored_dir)}"


def _assert_progress(calls: list[tuple[int, int]], total: int, what: str) -> None:
    """Reports never going back, the source's size as ``total`` on every one, the last at ``total``."""
    assert calls, f"{what}: progress was never called"
    totals = sorted({reported for _, reported in calls})
    assert totals == [total], f"{what}: total is the source's size, {total}, on every report: {totals}"
    done = [value for value, _ in calls]
    assert done == sorted(done), f"{what}: done never goes back: {done}"
    assert done[0] >= 0 and done[-1] == total, f"{what}: done goes from 0 or more up to {total}: {done}"


def _watch(dst: Path, seen: list[tuple[int, int, list[str], int | None]]) -> Callable[[int, int], None]:
    """A ``progress`` that records, at each report, the names in ``dst``'s folder and the mode of ``<dst name>.part``."""
    part = dst.with_name(dst.name + ".part")

    def report(done: int, total: int) -> None:
        seen.append((done, total, _listing(dst.parent), _mode(part) if part.exists() else None))

    return report


def _assert_written_through_part(dst: Path, seen: list[tuple[int, int, list[str], int | None]], what: str) -> None:
    """While the work goes on (``0 < done < total``) the folder holds ``<dst name>.part`` alone, 0600; at the end ``dst``."""
    part_name = dst.name + ".part"
    during = [(names, part_mode) for done, total, names, part_mode in seen if 0 < done < total]
    reports = [(done, total) for done, total, _, _ in seen]
    assert during, f"{what}: no report while the work went on (0 < done < total), nothing to observe; a three-chunk file must report its bytes as it goes: {reports}"
    assert all(names == [part_name] for names, _ in during), f"{what}: while it works, the folder holds {part_name} alone, nothing under the final name: {during}"
    if POSIX:
        assert all(part_mode == 0o600 for _, part_mode in during), f"{what}: {part_name} is 0600 from its creation: {[oct(mode) for _, mode in during if mode is not None]}"
    assert _listing(dst.parent) == [dst.name], f"{what}: at the end {dst.name} alone, the .part renamed onto it: {_listing(dst.parent)}"


class _Stopped(Exception):
    """Raised by a progress callback to make a write fail half-way."""


def _stop_half_way(done: int, total: int) -> None:
    """A ``progress`` that fails at its first report between the first byte and the last."""
    if 0 < done < total:
        raise _Stopped(f"stopped at {done} of {total}")


def _write_large(path: Path, size: int) -> str:
    """``size`` bytes written block by block, never whole in memory; their SHA-256."""
    digest = hashlib.sha256()
    blocks = random.Random("constant-memory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        remaining = size
        while remaining:
            block = blocks.randbytes(min(CHUNK, remaining))
            digest.update(block)
            handle.write(block)
            remaining -= len(block)
    return digest.hexdigest()


def _traced_peak[T](tracer: ModuleType, action: Callable[[], T]) -> tuple[T, int]:
    """``action()`` and the peak of the memory tracemalloc saw it allocate, above what was traced when it started (as
    ``test_risk_metrics_oracle`` measures it). Started here only when nobody else traces; stopped only if started here."""
    started_here = not tracer.is_tracing()
    if started_here:
        tracer.start()
    try:
        tracer.reset_peak()
        baseline, _ = tracer.get_traced_memory()
        result = action()
        _, peak = tracer.get_traced_memory()
    finally:
        if started_here:
            tracer.stop()
    return result, peak - baseline


# =============================================================================
# 1. THE CONTRACT'S CONSTANTS AND THE ROUND TRIP
# =============================================================================


def test_the_module_publishes_the_contract_constants(envelope):
    """§1: the format, what B4 writes (log2(n) 15, r 8, p 1, 1 MiB chunks) and the read bounds checked before scrypt."""
    published = {name: getattr(envelope, name, "<missing>") for name in CONTRACT_CONSTANTS}
    differing = {name: (value, CONTRACT_CONSTANTS[name]) for name, value in published.items() if value != CONTRACT_CONSTANTS[name]}
    assert differing == {}, f"these constants differ from the contract, (published, contract): {differing}"
    assert issubclass(envelope.EnvelopeError, Exception), "EnvelopeError is an exception"


ROUND_TRIP_SIZES = [
    pytest.param(0, id="empty"),
    pytest.param(1, id="one-byte"),
    pytest.param(CHUNK - 1, id="one-chunk-minus-one-byte"),
    pytest.param(CHUNK, id="one-full-chunk"),
    pytest.param(CHUNK + 1, id="one-chunk-plus-one-byte"),
    pytest.param(3 * CHUNK + 5, id="three-chunks-plus-five-bytes"),
]


@pytest.mark.parametrize("size", ROUND_TRIP_SIZES)
def test_a_file_round_trips_through_the_envelope(envelope, tmp_path, size):
    """1: encrypt_file, unlock and decrypt_file give the very bytes back, and decrypt_file returns their size; the
    envelope is 52 + size + 16 per chunk, at least one; EncryptedFile is the envelope's size and SHA-256; each folder
    ends with its file alone, no ``.part`` left."""
    print_section(f"1: round trip of {size} bytes")
    plaintext = _payload(size)
    src = _write(tmp_path / "plain.zip", plaintext)
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()

    written = envelope.encrypt_file(src, sealed, PASSWORD, log2_n=FAST_LOG2_N)
    expected_size = HEADER_SIZE + size + TAG_SIZE * _chunk_count(size)
    assert sealed.stat().st_size == expected_size, f"52 + {size} + 16 × {_chunk_count(size)} chunk(s) = {expected_size} bytes: {sealed.stat().st_size}"
    assert isinstance(written, envelope.EncryptedFile), f"encrypt_file returns an EncryptedFile: {written!r}"
    assert (written.size, written.sha256) == (expected_size, _file_sha256(sealed)), f"EncryptedFile is the envelope's size and SHA-256: {written!r}"
    assert _listing(sealed.parent) == ["backup.lfbk"], f"the envelope alone, no .part left: {_listing(sealed.parent)}"

    restored = tmp_path / "restored" / "backup.zip"
    returned = _open(envelope, sealed, PASSWORD, restored)
    assert returned == size, f"decrypt_file returns the plaintext's size, {size}: {returned}"
    assert restored.stat().st_size == size, f"{size} bytes written back: {restored.stat().st_size}"
    assert _file_sha256(restored) == _sha256(plaintext), "the bytes come back as they were"
    assert _listing(restored.parent) == ["backup.zip"], f"the plaintext alone, no .part left: {_listing(restored.parent)}"
    print_success(f"{size} bytes → a {expected_size}-byte envelope → {size} bytes")


# =============================================================================
# 2. THE HEADER
# =============================================================================


def test_encrypt_file_writes_the_documented_header_with_the_default_parameters(envelope, tmp_path):
    """2: by default log2(n) 15, r 8, p 1 and 1 MiB chunks, each at its offset; bytes 25-40 are scrypt's bytes 32-47 at
    those parameters; read_header gives the whole header back, to_bytes its 52 bytes, from_bytes the same header; and
    the only chunk opens with scrypt's bytes 0-31, counter 0 and the last flag."""
    print_section("2: the header of a default envelope")
    plaintext = _payload(1000, seed="default")
    src = _write(tmp_path / "plain.zip", plaintext)
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    envelope.encrypt_file(src, sealed, PASSWORD)
    raw = sealed.read_bytes()

    assert raw[:4] == MAGIC, f"bytes 0-3 are the magic: {raw[:4]!r}"
    fields = {"version": raw[VERSION_AT], "kdf": raw[KDF_AT], "log2_n": raw[LOG2_N_AT], "r": raw[R_AT], "p": raw[P_AT]}
    assert fields == {"version": 1, "kdf": 1, "log2_n": 15, "r": 8, "p": 1}, f"bytes 4-8: {fields}"
    assert raw[CHUNK_SIZE_AT] == b"\x00\x10\x00\x00", f"bytes 41-44 are 1 MiB as a big-endian u32: {raw[CHUNK_SIZE_AT].hex()}"
    salt, check, nonce_prefix = raw[SALT_AT], raw[CHECK_AT], raw[NONCE_PREFIX_AT]
    derived = _derive(PASSWORD.encode("utf-8"), salt, DEFAULT_LOG2_N)
    assert check == derived[32:48], f"bytes 25-40 are scrypt's bytes 32-47 at log2(n) 15, r 8, p 1: {check.hex()} != {derived[32:48].hex()}"

    header = envelope.read_header(sealed)
    expected = envelope.EnvelopeHeader(version=1, kdf=1, log2_n=15, r=8, p=1, salt=salt, check=check, chunk_size=CHUNK, nonce_prefix=nonce_prefix)
    assert header == expected, f"read_header: {header!r}"
    assert header.to_bytes() == raw[:HEADER_SIZE], f"to_bytes gives back the 52 bytes written: {header.to_bytes().hex()}"
    assert envelope.EnvelopeHeader.from_bytes(raw[:HEADER_SIZE]) == header, "from_bytes reads the 52 bytes as read_header does"
    opened = _authentic(derived[:32], _nonce(nonce_prefix, 0, last=True), raw[HEADER_SIZE:], raw[:HEADER_SIZE])
    assert opened is not None, "the only chunk opens with scrypt's bytes 0-31, nonce prefix ‖ counter 0 ‖ 0x01, the header as associated data"
    assert _sha256(opened) == _sha256(plaintext), "and holds the plaintext"
    print_success(f"log2(n) 15, r 8, p 1, 1 MiB chunks; salt {salt.hex()}, nonce prefix {nonce_prefix.hex()}")


def test_a_header_serialises_to_its_52_bytes_and_back(envelope):
    """2: to_bytes is the documented layout, field by field, the chunk size a big-endian u32; from_bytes reads it back
    equal; the header is frozen."""
    header = envelope.EnvelopeHeader(version=1, kdf=1, log2_n=16, r=3, p=2, salt=SALT, check=CHECK, chunk_size=1 << 17, nonce_prefix=NONCE_PREFIX)
    raw = header.to_bytes()
    expected = _header(log2_n=16, r=3, p=2, chunk_size=1 << 17)
    assert len(raw) == HEADER_SIZE, f"exactly 52 bytes: {len(raw)}"
    assert raw == expected, f"the documented layout: {raw.hex()} != {expected.hex()}"
    assert raw[CHUNK_SIZE_AT] == b"\x00\x02\x00\x00", f"128 KiB as a big-endian u32: {raw[CHUNK_SIZE_AT].hex()}"
    assert envelope.EnvelopeHeader.from_bytes(raw) == header, "from_bytes gives the same header back"
    with pytest.raises(dataclasses.FrozenInstanceError):
        header.log2_n = 14


def test_two_encryptions_of_one_file_differ_and_both_open(envelope, tmp_path):
    """2: a fresh salt and a fresh nonce prefix each time, so other ciphertext; each envelope opens to the same file."""
    plaintext = _payload(3000, seed="twice")
    src = _write(tmp_path / "plain.zip", plaintext)
    sealed_dir = tmp_path / "sealed"
    sealed_dir.mkdir()
    first, second = sealed_dir / "first.lfbk", sealed_dir / "second.lfbk"
    envelope.encrypt_file(src, first, PASSWORD, log2_n=FAST_LOG2_N)
    envelope.encrypt_file(src, second, PASSWORD, log2_n=FAST_LOG2_N)
    one, other = first.read_bytes(), second.read_bytes()

    assert one[SALT_AT] != other[SALT_AT], f"a fresh salt each time: {one[SALT_AT].hex()} twice"
    assert one[NONCE_PREFIX_AT] != other[NONCE_PREFIX_AT], f"a fresh nonce prefix each time: {one[NONCE_PREFIX_AT].hex()} twice"
    assert _sha256(one[HEADER_SIZE:]) != _sha256(other[HEADER_SIZE:]), "the same file twice gives other ciphertext"
    for name, sealed in (("first", first), ("second", second)):
        restored = tmp_path / "restored" / f"{name}.zip"
        assert _open(envelope, sealed, PASSWORD, restored) == len(plaintext), f"the {name} envelope opens"
        assert _file_sha256(restored) == _sha256(plaintext), f"the {name} envelope holds the file"


# =============================================================================
# 3. THE KNOWN ANSWER, COMPUTED HERE WITH cryptography'S PRIMITIVES
# =============================================================================


KNOWN_ANSWER_SIZES = [
    pytest.param(CHUNK + 3, id="two-chunks-the-last-of-3-bytes"),
    pytest.param(CHUNK, id="one-full-chunk-and-no-empty-chunk-after-it"),
    pytest.param(0, id="an-empty-file-is-one-empty-chunk"),
]


@pytest.mark.parametrize("size", KNOWN_ANSWER_SIZES)
def test_the_envelope_is_the_documented_construction_byte_for_byte(envelope, tmp_path, size):
    """3: with a fixed salt and nonce prefix at log2(n) 14 the file is exactly the header, then each chunk under
    scrypt's bytes 0-31 with nonce prefix ‖ counter ‖ last flag and the 52 header bytes as associated data, computed here
    with cryptography's own Scrypt and AESGCM; bytes 25-40 are scrypt's bytes 32-47."""
    print_section(f"3: known answer, {size} bytes")
    plaintext = _payload(size, seed="known-answer")
    src = _write(tmp_path / "plain.zip", plaintext)
    sealed = tmp_path / "sealed" / "fixed.lfbk"
    sealed.parent.mkdir()
    expected, derived = _expected_envelope(plaintext, PASSWORD.encode("utf-8"), salt=SALT, nonce_prefix=NONCE_PREFIX, log2_n=FAST_LOG2_N)

    written = envelope.encrypt_file(src, sealed, PASSWORD, salt=SALT, nonce_prefix=NONCE_PREFIX, log2_n=FAST_LOG2_N)
    actual = sealed.read_bytes()
    assert actual[CHECK_AT] == derived[32:48], f"bytes 25-40 are scrypt's bytes 32-47: {actual[CHECK_AT].hex()} != {derived[32:48].hex()}"
    assert actual[:HEADER_SIZE] == expected[:HEADER_SIZE], f"the header: {actual[:HEADER_SIZE].hex()} != {expected[:HEADER_SIZE].hex()}"
    difference = _difference(actual, expected)
    assert difference is None, f"the envelope is not the construction of §1: {difference}"
    assert (written.size, written.sha256) == (len(expected), _sha256(expected)), f"EncryptedFile describes these bytes: {written!r}"
    print_success(f"{_chunk_count(size)} chunk(s), {len(expected)} bytes, sha256 {_sha256(expected)[:16]}…")


# =============================================================================
# 4. THE READ BOUNDS, BEFORE ANY DERIVATION
# =============================================================================


UNSUPPORTED_HEADERS = [
    pytest.param({"version": 0}, id="version-0"),
    pytest.param({"version": 2}, id="version-2"),
    pytest.param({"kdf": 0}, id="kdf-0"),
    pytest.param({"kdf": 2}, id="kdf-2"),
    pytest.param({"log2_n": 0}, id="log2_n-0"),
    pytest.param({"log2_n": 13}, id="log2_n-13"),
    pytest.param({"log2_n": 17}, id="log2_n-17"),
    pytest.param({"log2_n": 30}, id="log2_n-30"),
    pytest.param({"log2_n": 255}, id="log2_n-255"),
    pytest.param({"r": 0}, id="r-0"),
    pytest.param({"r": 9}, id="r-9"),
    pytest.param({"p": 0}, id="p-0"),
    pytest.param({"p": 3}, id="p-3"),
    pytest.param({"chunk_size": 0}, id="chunk-size-0"),
    pytest.param({"chunk_size": 1}, id="chunk-size-1"),
    pytest.param({"chunk_size": (1 << 16) - 1}, id="chunk-size-65535"),
    pytest.param({"chunk_size": (1 << 24) + 1}, id="chunk-size-16MiB-plus-1"),
    pytest.param({"chunk_size": 0xFFFFFFFF}, id="chunk-size-4GiB"),
]


@pytest.mark.parametrize("fields", UNSUPPORTED_HEADERS)
def test_a_header_beyond_the_read_bounds_is_unsupported_before_any_derivation(envelope, no_derivation, tmp_path, fields):
    """4: a version or a kdf other than 1, log2(n) outside 14..16, r outside 1..8, p outside 1..2, a chunk size outside
    64 KiB..16 MiB: envelope_unsupported from from_bytes, read_header and unlock, scrypt never called, unlock refused
    within 50 ms (best of three); every other field asks for log2(n) 15, so a derivation first would cost ~0.1 s."""
    raw = _header(**fields)
    path = _write(tmp_path / "hostile.lfbk", raw + bytes(TAG_SIZE))
    code = _refused(envelope, lambda: envelope.EnvelopeHeader.from_bytes(raw))
    assert code == "envelope_unsupported", f"from_bytes of a header with {fields}: {code}"
    code = _refused(envelope, lambda: envelope.read_header(path))
    assert code == "envelope_unsupported", f"read_header of a header with {fields}: {code}"
    elapsed: list[float] = []
    for _ in range(3):
        started = time.perf_counter()
        code = _refused(envelope, lambda: envelope.unlock(path, PASSWORD))
        elapsed.append(time.perf_counter() - started)
        assert code == "envelope_unsupported", f"unlock of a header with {fields}: {code}"
    assert no_derivation == [], f"scrypt was called for a header with {fields}: {no_derivation}"
    assert min(elapsed) < REFUSAL_SECONDS, f"unlock refused {fields} in {min(elapsed):.3f} s at best, not within {REFUSAL_SECONDS} s: {elapsed}"


WITHIN_BOUNDS = [
    pytest.param({"log2_n": 14}, id="log2_n-14"),
    pytest.param({"log2_n": 16}, id="log2_n-16"),
    pytest.param({"r": 1}, id="r-1"),
    pytest.param({"p": 2}, id="p-2"),
    pytest.param({"chunk_size": 1 << 16}, id="chunk-size-64KiB"),
    pytest.param({"chunk_size": 1 << 24}, id="chunk-size-16MiB"),
    pytest.param({"log2_n": 14, "r": 1, "p": 1, "chunk_size": 1 << 16}, id="every-lower-bound"),
    pytest.param({"log2_n": 16, "r": 8, "p": 2, "chunk_size": 1 << 24}, id="every-upper-bound"),
]


@pytest.mark.parametrize("fields", WITHIN_BOUNDS)
def test_a_header_on_the_read_bounds_is_read_as_written(envelope, no_derivation, tmp_path, fields):
    """4: the bounds are inclusive: log2(n) 14 and 16, r 1 and 8, p 1 and 2, chunks of 64 KiB and 16 MiB are read as
    written, from the 52 bytes alone, without a derivation."""
    raw = _header(**fields)
    path = _write(tmp_path / "edge.lfbk", raw)
    header = envelope.read_header(path)
    expected = {"version": 1, "kdf": 1, "log2_n": DEFAULT_LOG2_N, "r": R, "p": P, "salt": SALT, "check": CHECK, "chunk_size": CHUNK, "nonce_prefix": NONCE_PREFIX} | fields
    read = {name: getattr(header, name) for name in expected}
    assert read == expected, f"read_header of a header with {fields}: {read}"
    assert envelope.EnvelopeHeader.from_bytes(raw) == header, "from_bytes reads the same header"
    assert header.to_bytes() == raw, f"and to_bytes writes the same 52 bytes back: {header.to_bytes().hex()}"
    assert no_derivation == [], f"reading a header never derives: {no_derivation}"


NOT_A_HEADER = [
    pytest.param(b"", id="empty"),
    pytest.param(b"L", id="one-byte"),
    pytest.param(_header()[: HEADER_SIZE - 1], id="51-bytes-of-a-header"),
    pytest.param(b"LFBX" + _header()[4:], id="another-magic"),
    pytest.param(b"PK\x03\x04" + _header()[4:], id="a-zip-signature"),
    pytest.param(bytes(HEADER_SIZE), id="52-zero-bytes"),
]


@pytest.mark.parametrize("content", NOT_A_HEADER)
def test_a_file_too_short_or_not_ours_is_damaged_before_any_derivation(envelope, no_derivation, tmp_path, content):
    """4: fewer than 52 bytes, or 52 bytes under another magic: envelope_damaged from from_bytes, read_header and
    unlock, without a derivation."""
    path = _write(tmp_path / "not-ours.lfbk", content)
    code = _refused(envelope, lambda: envelope.EnvelopeHeader.from_bytes(content))
    assert code == "envelope_damaged", f"from_bytes of {content[:8]!r}… ({len(content)} bytes): {code}"
    code = _refused(envelope, lambda: envelope.read_header(path))
    assert code == "envelope_damaged", f"read_header of {content[:8]!r}… ({len(content)} bytes): {code}"
    code = _refused(envelope, lambda: envelope.unlock(path, PASSWORD))
    assert code == "envelope_damaged", f"unlock of {content[:8]!r}… ({len(content)} bytes): {code}"
    assert no_derivation == [], f"scrypt was called for a file that is not an envelope: {no_derivation}"


# =============================================================================
# 5. UNLOCK
# =============================================================================


WRONG_PASSWORDS = [
    pytest.param("Correct-Horse-Battery-8", id="one-character-off"),
    pytest.param(PASSWORD + " ", id="a-trailing-space"),
    pytest.param(PASSWORD.upper(), id="another-case"),
]


@pytest.mark.parametrize("wrong", WRONG_PASSWORDS)
def test_unlock_with_a_wrong_password_is_wrong_password(envelope, tmp_path, wrong):
    """5: the check value does not match: wrong_password, nothing stripped nor folded; the error shows no password."""
    sealed = _seal(envelope, tmp_path, _payload(100, seed="wrong"))
    with pytest.raises(envelope.EnvelopeError) as refused:
        envelope.unlock(sealed, wrong)
    assert refused.value.code == "wrong_password", f"unlock with a wrong password: {refused.value.code}"
    shown = f"{refused.value!s} {refused.value!r}"
    assert wrong not in shown and PASSWORD not in shown, f"the error never shows a password: {shown}"


def test_unlock_with_the_right_password_gives_the_key_of_this_header(envelope, tmp_path):
    """5: an EnvelopeKey whose header is read_header's."""
    sealed = _seal(envelope, tmp_path, _payload(100, seed="right"))
    key = envelope.unlock(sealed, PASSWORD)
    assert isinstance(key, envelope.EnvelopeKey), f"unlock returns an EnvelopeKey: {type(key)}"
    assert key.header == envelope.read_header(sealed), f"the key's header is the file's: {key.header!r}"


# =============================================================================
# 6. TAMPERING
# =============================================================================


#: A header byte the derivation depends on, changed within the read bounds: the right password no longer matches.
KEY_PARAMETER_CHANGES = [
    pytest.param(lambda header: _flip(header, SALT_AT.start), id="salt-first-byte"),
    pytest.param(lambda header: _flip(header, SALT_AT.stop - 1), id="salt-last-byte"),
    pytest.param(lambda header: _flip(header, CHECK_AT.start), id="check-first-byte"),
    pytest.param(lambda header: _flip(header, CHECK_AT.stop - 1), id="check-last-byte"),
    pytest.param(lambda header: _with_byte(header, LOG2_N_AT, 15), id="log2_n-14-to-15"),
    pytest.param(lambda header: _with_byte(header, LOG2_N_AT, 16), id="log2_n-14-to-16"),
    pytest.param(lambda header: _with_byte(header, R_AT, 7), id="r-8-to-7"),
    pytest.param(lambda header: _with_byte(header, P_AT, 2), id="p-1-to-2"),
]


@pytest.mark.parametrize("change", KEY_PARAMETER_CHANGES)
def test_a_changed_key_parameter_reads_as_a_wrong_password(envelope, three_chunks, tmp_path, change):
    """6: salt, log2(n), r, p and the check value decide whether a password matches: one of them changed, the header
    still within the read bounds, the right password is wrong_password at unlock, by design."""
    header, chunks = three_chunks.parts()
    changed = change(header)
    assert len(changed) == HEADER_SIZE and changed != header, "precondition: one byte of the header changed"
    tampered = _write(tmp_path / "tampered.lfbk", changed + b"".join(chunks))
    assert envelope.read_header(tampered).to_bytes() == changed, "precondition: still a header within the read bounds"
    code = _refused(envelope, lambda: envelope.unlock(tampered, PASSWORD))
    assert code == "wrong_password", f"unlock of an envelope whose key parameters changed: {code}"


#: From the header and the three chunks of the module's envelope, a file that still unlocks (salt, parameters and check
#: value intact) but whose chunks can no longer be authenticated.
DAMAGE = [
    pytest.param(lambda h, c: _with_byte(h, CHUNK_SIZE_AT.start + 1, 0x20) + b"".join(c), id="chunk-size-1MiB-read-as-2MiB"),
    pytest.param(lambda h, c: _with_byte(h, CHUNK_SIZE_AT.start + 1, 0x08) + b"".join(c), id="chunk-size-1MiB-read-as-512KiB"),
    pytest.param(lambda h, c: _flip(h, NONCE_PREFIX_AT.start) + b"".join(c), id="nonce-prefix-first-byte"),
    pytest.param(lambda h, c: _flip(h, NONCE_PREFIX_AT.stop - 1) + b"".join(c), id="nonce-prefix-last-byte"),
    pytest.param(lambda h, c: h + _flip(c[0], 0) + c[1] + c[2], id="chunk-0-ciphertext-byte"),
    pytest.param(lambda h, c: h + _flip(c[0], -1) + c[1] + c[2], id="chunk-0-tag-byte"),
    pytest.param(lambda h, c: h + c[0] + _flip(c[1], CHUNK // 2) + c[2], id="chunk-1-ciphertext-byte"),
    pytest.param(lambda h, c: h + c[0] + c[1] + _flip(c[2], 0), id="last-chunk-ciphertext-byte"),
    pytest.param(lambda h, c: h + c[0] + c[1] + _flip(c[2], -1), id="last-tag-byte"),
    pytest.param(lambda h, c: h + c[0] + c[1], id="truncated-at-a-chunk-boundary"),
    pytest.param(lambda h, c: h + c[0] + c[1] + c[2][:-1], id="truncated-inside-the-last-chunk"),
    pytest.param(lambda h, c: h + c[0] + c[1] + c[2][: TAG_SIZE - 1], id="last-chunk-shorter-than-a-tag"),
    pytest.param(lambda h, c: h + c[0] + c[1][: len(c[1]) // 2], id="truncated-inside-a-middle-chunk"),
    pytest.param(lambda h, c: h, id="the-header-alone"),
    pytest.param(lambda h, c: h + c[0] + c[1] + c[2] + c[2], id="the-last-chunk-appended-again"),
    pytest.param(lambda h, c: h + c[0] + c[1] + c[2] + random.Random("tail").randbytes(32), id="32-random-bytes-appended"),
    pytest.param(lambda h, c: h + c[1] + c[0] + c[2], id="chunks-0-and-1-swapped"),
    pytest.param(lambda h, c: h + c[0] + c[2], id="chunk-1-dropped"),
    pytest.param(lambda h, c: h + c[1] + c[2], id="chunk-0-dropped"),
    pytest.param(lambda h, c: h + c[0] + c[0] + c[1] + c[2], id="chunk-0-repeated"),
]


@pytest.mark.parametrize("damage", DAMAGE)
def test_a_damaged_envelope_never_decrypts_and_leaves_nothing(envelope, three_chunks, tmp_path, damage):
    """6: a changed chunk size or nonce prefix, a changed byte of a chunk or of a tag, a truncation, a chunk appended,
    repeated, dropped or swapped: the envelope still unlocks, decrypt_file answers envelope_damaged, and neither the
    destination nor its .part is left."""
    header, chunks = three_chunks.parts()
    sizes = [len(chunk) for chunk in chunks]
    assert sizes == [CHUNK + TAG_SIZE, CHUNK + TAG_SIZE, LAST_CHUNK_BYTES + TAG_SIZE], f"precondition: two full chunks and a last one of {LAST_CHUNK_BYTES} bytes, each with its tag: {sizes}"
    _assert_damaged(envelope, tmp_path, damage(header, chunks))


FULL_LAST_CHUNK_DAMAGE = [
    pytest.param(lambda h, c: h + c[0], id="the-full-last-chunk-dropped"),
    pytest.param(lambda h, c: h + c[0] + c[1] + c[1], id="the-full-last-chunk-appended-again"),
    pytest.param(lambda h, c: h + c[0] + c[1] + bytes(TAG_SIZE), id="an-empty-chunk-appended"),
]


@pytest.mark.parametrize("damage", FULL_LAST_CHUNK_DAMAGE)
def test_an_envelope_ending_on_a_full_chunk_is_damaged_by_a_chunk_less_or_more(envelope, two_full_chunks, tmp_path, damage):
    """6: when the size is a multiple of the chunk size, the last flag alone marks the end: the last chunk dropped,
    appended again, or an empty chunk added after it, envelope_damaged, and nothing left."""
    header, chunks = two_full_chunks.parts()
    sizes = [len(chunk) for chunk in chunks]
    assert sizes == [CHUNK + TAG_SIZE, CHUNK + TAG_SIZE], f"precondition: exactly two full chunks, no empty chunk after them: {sizes}"
    _assert_damaged(envelope, tmp_path, damage(header, chunks))


# =============================================================================
# 7. THE PASSWORD IN NFC, AS UTF-8
# =============================================================================


@pytest.mark.parametrize(
    ("written", "typed"),
    [pytest.param(DECOMPOSED, COMPOSED, id="sealed-decomposed-typed-precomposed"), pytest.param(COMPOSED, DECOMPOSED, id="sealed-precomposed-typed-decomposed")],
)
def test_both_forms_of_one_accent_are_one_password(envelope, tmp_path, written, typed):
    """7: «é» precomposed (U+00E9) and «e» + U+0301 are one password: the check value is scrypt of its NFC form in
    UTF-8, and each form opens what the other sealed."""
    assert written != typed and unicodedata.normalize("NFC", written) == unicodedata.normalize("NFC", typed) == COMPOSED, "precondition: two strings, one NFC form"
    plaintext = _payload(500, seed="nfc")
    sealed = _seal(envelope, tmp_path, plaintext, password=written)
    raw = sealed.read_bytes()
    assert raw[CHECK_AT] == _derive(COMPOSED.encode("utf-8"), raw[SALT_AT], FAST_LOG2_N)[32:48], "the check value is derived from the NFC form, in UTF-8"
    restored = tmp_path / "restored" / "backup.zip"
    assert _open(envelope, sealed, typed, restored) == len(plaintext), "the other form unlocks and decrypts"
    assert _file_sha256(restored) == _sha256(plaintext), "the file comes back"


def test_compatibility_characters_are_kept_as_nfc_keeps_them(envelope, tmp_path):
    """7: NFC, never NFKC: a password with the «ﬁ» ligature and full-width characters is not its folded form, which is
    wrong_password; it opens itself, its check value derived from its own UTF-8 bytes."""
    assert unicodedata.normalize("NFC", COMPATIBLE) == COMPATIBLE, "precondition: NFC keeps compatibility characters"
    assert unicodedata.normalize("NFKC", COMPATIBLE) == COMPATIBLE_FOLDED, "precondition: NFKC would fold them"
    plaintext = _payload(500, seed="nfkc")
    sealed = _seal(envelope, tmp_path, plaintext, password=COMPATIBLE)
    raw = sealed.read_bytes()
    assert raw[CHECK_AT] == _derive(COMPATIBLE.encode("utf-8"), raw[SALT_AT], FAST_LOG2_N)[32:48], "the check value is derived from the password as typed: NFC changes nothing here"
    code = _refused(envelope, lambda: envelope.unlock(sealed, COMPATIBLE_FOLDED))
    assert code == "wrong_password", f"the NFKC form is another password: {code}"
    restored = tmp_path / "restored" / "backup.zip"
    assert _open(envelope, sealed, COMPATIBLE, restored) == len(plaintext), "the password as typed opens"
    assert _file_sha256(restored) == _sha256(plaintext), "the file comes back"


def test_a_non_ascii_password_round_trips(envelope, tmp_path):
    """7: Latin with diacritics, Greek, Chinese and an emoji: derived from the NFC form's UTF-8 bytes; the file comes
    back."""
    plaintext = _payload(CHUNK + 17, seed="non-ascii")
    sealed = _seal(envelope, tmp_path, plaintext, password=NON_ASCII)
    raw = sealed.read_bytes()
    secret = unicodedata.normalize("NFC", NON_ASCII).encode("utf-8")
    assert raw[CHECK_AT] == _derive(secret, raw[SALT_AT], FAST_LOG2_N)[32:48], "the check value is scrypt of the UTF-8 bytes"
    restored = tmp_path / "restored" / "backup.zip"
    assert _open(envelope, sealed, NON_ASCII, restored) == len(plaintext), "the password unlocks and decrypts"
    assert _file_sha256(restored) == _sha256(plaintext), "the file comes back"


# =============================================================================
# 8. THE FILES: NO OVERWRITE, PRIVATE MODES, .part, PROGRESS
# =============================================================================


def test_encrypt_file_never_overwrites_its_destination(envelope, tmp_path):
    """8: dst already there: FileExistsError, its bytes as they were, nothing written beside it."""
    src = _write(tmp_path / "plain.zip", _payload(1000, seed="exists"))
    dst = _write(tmp_path / "sealed" / "backup.lfbk", b"an earlier backup, to keep")
    with pytest.raises(FileExistsError):
        envelope.encrypt_file(src, dst, PASSWORD, log2_n=FAST_LOG2_N)
    assert dst.read_bytes() == b"an earlier backup, to keep", f"the existing file is untouched: {dst.read_bytes()[:40]!r}"
    assert _listing(dst.parent) == ["backup.lfbk"], f"nothing written beside it: {_listing(dst.parent)}"


def test_decrypt_file_never_overwrites_its_destination(envelope, tmp_path):
    """8: dst already there: FileExistsError, its bytes as they were, nothing written beside it."""
    sealed = _seal(envelope, tmp_path, _payload(1000, seed="exists"))
    key = envelope.unlock(sealed, PASSWORD)
    restored = _write(tmp_path / "restored" / "backup.zip", b"a zip already there, to keep")
    with pytest.raises(FileExistsError):
        envelope.decrypt_file(sealed, restored, key)
    assert restored.read_bytes() == b"a zip already there, to keep", f"the existing file is untouched: {restored.read_bytes()[:40]!r}"
    assert _listing(restored.parent) == ["backup.zip"], f"nothing written beside it: {_listing(restored.parent)}"


@needs_posix_modes
def test_the_envelope_and_the_decrypted_file_are_created_private(envelope, tmp_path):
    """8: both files are 0600, whatever the mode of the file they come from (here 0644): an archive and its plaintext
    are for the owner alone."""
    src = _write(tmp_path / "plain.zip", _payload(1000, seed="modes"))
    src.chmod(0o644)
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    envelope.encrypt_file(src, sealed, PASSWORD, log2_n=FAST_LOG2_N)
    assert _mode(sealed) == 0o600, f"the envelope is 0600: {oct(_mode(sealed))}"

    sealed.chmod(0o644)
    restored = tmp_path / "restored" / "backup.zip"
    _open(envelope, sealed, PASSWORD, restored)
    assert _mode(restored) == 0o600, f"the decrypted file is 0600: {oct(_mode(restored))}"


def test_progress_counts_the_source_bytes_up_to_the_source_size(envelope, tmp_path):
    """8: encrypt_file reports the plaintext's bytes, decrypt_file the envelope's: done never goes back, total is the
    source's size on every report, and the last report is the whole source."""
    plaintext = _payload(2 * CHUNK + 7, seed="progress")
    src = _write(tmp_path / "plain.zip", plaintext)
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    encrypting: list[tuple[int, int]] = []
    envelope.encrypt_file(src, sealed, PASSWORD, progress=lambda done, total: encrypting.append((done, total)), log2_n=FAST_LOG2_N)
    _assert_progress(encrypting, len(plaintext), "encrypt_file")

    restored = tmp_path / "restored" / "backup.zip"
    restored.parent.mkdir()
    decrypting: list[tuple[int, int]] = []
    envelope.decrypt_file(sealed, restored, envelope.unlock(sealed, PASSWORD), progress=lambda done, total: decrypting.append((done, total)))
    _assert_progress(decrypting, sealed.stat().st_size, "decrypt_file")


def test_the_bytes_go_to_a_private_part_file_beside_the_destination_until_the_end(envelope, tmp_path):
    """8: while a three-chunk file is processed, the destination's folder holds ``<dst name>.part`` alone, 0600, and
    nothing under the final name; at the end the destination alone: for encrypt_file and for decrypt_file."""
    src = _write(tmp_path / "plain.zip", _payload(2 * CHUNK + LAST_CHUNK_BYTES, seed="part"))
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    sealing: list[tuple[int, int, list[str], int | None]] = []
    envelope.encrypt_file(src, sealed, PASSWORD, progress=_watch(sealed, sealing), log2_n=FAST_LOG2_N)
    _assert_written_through_part(sealed, sealing, "encrypt_file")

    restored = tmp_path / "restored" / "backup.zip"
    restored.parent.mkdir()
    opening: list[tuple[int, int, list[str], int | None]] = []
    envelope.decrypt_file(sealed, restored, envelope.unlock(sealed, PASSWORD), progress=_watch(restored, opening))
    _assert_written_through_part(restored, opening, "decrypt_file")


def test_a_failure_half_way_through_encrypting_leaves_nothing(envelope, tmp_path):
    """8: any failure removes the .part and never leaves dst: the progress callback raises after the first chunk, its
    error reaches the caller, and the destination's folder stays empty."""
    src = _write(tmp_path / "plain.zip", _payload(2 * CHUNK + LAST_CHUNK_BYTES, seed="stop"))
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    with pytest.raises(_Stopped):
        envelope.encrypt_file(src, sealed, PASSWORD, progress=_stop_half_way, log2_n=FAST_LOG2_N)
    assert _listing(sealed.parent) == [], f"neither backup.lfbk nor its .part is left: {_listing(sealed.parent)}"


def test_a_failure_half_way_through_decrypting_leaves_no_plaintext(envelope, tmp_path):
    """8: a decryption's .part holds plaintext: a failure after the first chunk removes it, its error reaches the
    caller, and the destination never appears."""
    sealed = _seal(envelope, tmp_path, _payload(2 * CHUNK + LAST_CHUNK_BYTES, seed="stop"))
    key = envelope.unlock(sealed, PASSWORD)
    restored = tmp_path / "restored" / "backup.zip"
    restored.parent.mkdir()
    with pytest.raises(_Stopped):
        envelope.decrypt_file(sealed, restored, key, progress=_stop_half_way)
    assert _listing(restored.parent) == [], f"neither backup.zip nor its .part is left: {_listing(restored.parent)}"


# =============================================================================
# 9. is_envelope
# =============================================================================


def test_is_envelope_tells_an_envelope_from_a_zip(envelope, tmp_path):
    """9: True for the envelope encrypt_file wrote, False for the zip it was made from."""
    archive = tmp_path / "backup.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", '{"format": "librefolio-backup"}')
    sealed = tmp_path / "sealed" / "backup.lfbk"
    sealed.parent.mkdir()
    envelope.encrypt_file(archive, sealed, PASSWORD, log2_n=FAST_LOG2_N)
    assert envelope.is_envelope(sealed) is True, "an envelope is an envelope"
    assert envelope.is_envelope(archive) is False, "a zip is not"


FIRST_BYTES = [
    pytest.param(b"", False, id="an-empty-file"),
    pytest.param(b"LFB", False, id="three-bytes-of-the-magic"),
    pytest.param(b"LFBK", True, id="the-magic-alone"),
    pytest.param(b"LFBK" + bytes(100), True, id="the-magic-then-anything"),
    pytest.param(b"lfbk" + _header()[4:], False, id="the-magic-in-lower-case"),
    pytest.param(b"PK\x03\x04" + bytes(100), False, id="a-zip-signature"),
]


@pytest.mark.parametrize(("content", "expected"), FIRST_BYTES)
def test_is_envelope_reads_the_first_four_bytes(envelope, tmp_path, content, expected):
    """9: the first four bytes are LFBK; a shorter file is not an envelope."""
    path = _write(tmp_path / "upload.bin", content)
    assert envelope.is_envelope(path) is expected, f"is_envelope of {content[:8]!r}… ({len(content)} bytes) must be {expected}"


# =============================================================================
# 10. THE KEY NEVER SHOWS ITSELF
# =============================================================================


def test_the_key_never_shows_its_aes_key(envelope, tmp_path):
    """10: repr and str of an EnvelopeKey hold neither the AES key (scrypt's bytes 0-31, derived here), nor its hex, nor
    its base64; nor the password, which the key never keeps."""
    sealed = _seal(envelope, tmp_path, _payload(100, seed="repr"))
    key = envelope.unlock(sealed, PASSWORD)
    aes_key = _derive(PASSWORD.encode("utf-8"), sealed.read_bytes()[SALT_AT], FAST_LOG2_N)[:32]
    shown = f"{key!r}\n{key!s}\n{key}"
    forbidden = {
        "the key's bytes": repr(aes_key)[2:-1],
        "its hex": aes_key.hex(),
        "its hex in upper case": aes_key.hex().upper(),
        "the hex of its first 8 bytes": aes_key[:8].hex(),
        "its base64": base64.b64encode(aes_key).decode("ascii"),
        "its URL-safe base64": base64.urlsafe_b64encode(aes_key).decode("ascii"),
        "the password": PASSWORD,
    }
    leaks = [name for name, text in forbidden.items() if text in shown]
    assert leaks == [], f"repr/str of the key show {leaks}: {shown}"


# =============================================================================
# 11. CONSTANT MEMORY
# =============================================================================


def test_encrypting_and_decrypting_24_mib_stay_within_8_mib(envelope, tmp_path):
    """11 (constant memory): a 24 MiB file is encrypted and decrypted chunk by chunk: tracemalloc's peak stays below
    8 MiB for each, a third of the file. Scrypt's memory is OpenSSL's and is not traced."""
    tracer = pytest.importorskip("tracemalloc")
    print_section("11: constant memory, 24 MiB through the envelope")
    src = tmp_path / "large.zip"
    digest = _write_large(src, MEMORY_FILE_SIZE)
    sealed = tmp_path / "sealed" / "large.lfbk"
    sealed.parent.mkdir()
    restored = tmp_path / "restored" / "large.zip"
    restored.parent.mkdir()

    _, encrypt_peak = _traced_peak(tracer, lambda: envelope.encrypt_file(src, sealed, PASSWORD, log2_n=FAST_LOG2_N))
    key = envelope.unlock(sealed, PASSWORD)
    size, decrypt_peak = _traced_peak(tracer, lambda: envelope.decrypt_file(sealed, restored, key))

    assert size == MEMORY_FILE_SIZE, f"decrypt_file returns {MEMORY_FILE_SIZE}: {size}"
    assert _file_sha256(restored) == digest, "the 24 MiB come back"
    assert encrypt_peak < MEMORY_BUDGET, f"encrypt_file peaked at {encrypt_peak / CHUNK:.1f} MiB for a {MEMORY_FILE_SIZE // CHUNK} MiB file: it does not stream"
    assert decrypt_peak < MEMORY_BUDGET, f"decrypt_file peaked at {decrypt_peak / CHUNK:.1f} MiB for a {MEMORY_FILE_SIZE // CHUNK} MiB file: it does not stream"
    print_success(f"peaks: encrypt {encrypt_peak / CHUNK:.1f} MiB, decrypt {decrypt_peak / CHUNK:.1f} MiB")
