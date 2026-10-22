"""
Instance backup, the sealed nightly backup (workstream B, lot L3 checkpoint 2): ``instance_backup/sealed.py`` and
``envelope.unlock_header``.

The agreed contract L3 (``BACKUP-contratto-L3.md`` §2, §3, §9) and the checkpoint's interface (§3, §4), pinned here
against the common vectors committed in ``backend/test_scripts/fixtures/backup_l3/`` (``vectors.json`` is their index,
``generate_vectors.py`` shows how each file was built, with pyrage, the envelope and ``tarfile``, never with
``sealed.py``):

- SEALED-001 the constants (``MEMBERS``, ``FORMAT``, ``FORMAT_VERSION``, ``PASSWORD_LENGTH``, ``SMALL_MEMBER_MAX``,
  ``HEAD_BYTES``, ``FILE_SUFFIX``), ``SealedError`` and its ``code``, ``SealedArchive`` a frozen dataclass.
- SEALED-002 every case of ``vectors.json`` through the reader, with its expected outcome: ``ok`` (manifest, envelope
  offset, size, SHA-256 and header, the password with each identity on its own, ``check_password``, ``extract_envelope``
  then ``envelope.decrypt_file`` giving the zip of ``zip_sha256``), ``sealed_no_identity``, ``wrong_password`` (at
  ``check_password``), ``sealed_manifest_invalid``, ``sealed_tar_invalid`` and ``envelope_damaged`` (at the decryption of
  the extracted envelope). Every refusal holds no path.
- SEALED-003 ``write_sealed`` rebuilds the good ``.tar`` byte for byte from its three members and ``mtime`` 1792724412;
  ``FileExistsError`` over an existing file (kept); ``0600``; no ``.part`` left; the size and SHA-256 it returns.
- SEALED-004 ``build_manifest`` gives the good vector's ``manifest.json`` bytes from its fields; ``created_at`` in UTC.
- SEALED-005 ``new_password``: 43 characters of ``[A-Za-z0-9_-]``, 32 bytes once decoded, never twice the same.
- SEALED-006 ``seal_password`` (binary age, not armored) and ``open_password``: round trips with generated identities,
  one or two recipients; another identity ``sealed_no_identity``; a plaintext that is not 43 base64url characters
  ``sealed_password_invalid``, the plaintext never in the message.
- SEALED-007 ``read_sealed`` refusals beyond the vectors, each archive built here: PAX headers (per file and global), a
  GNU long name, a directory and a hard link, a member count or a name off, a small member over 4096 bytes (4096 itself
  read), an envelope that is not ``LFBK`` version 1, a truncated or empty file; a manifest that is not UTF-8 JSON of an
  object, with duplicate, unknown or missing keys, of a wrong type, another format or version, 0 or 3 recipients, a
  recipient that is not ``age1…``, a size or hash off, another ``password_member``. A manifest of the right content in
  another layout is read.
- SEALED-008 ``read_identities`` and ``identity_file_text``: the vectors' identity files, an ``age-keygen`` file with
  comments and blank lines, a bad key line or none ``sealed_identity_invalid`` (the line never quoted), and the text a
  new key file holds read back.
- SEALED-009 ``is_sealed``: every vector ``True``; a zip, an ``.lfbk``, an empty or short file, a missing path ``False``.
- SEALED-010 the cloud coordinator's derivation rows: pyrage gives each identity's recipient.
- SEALED-011 interoperability with the reference ``age`` binary (Go), skipped visibly when it is not installed.
- SEALED-012 ``envelope.unlock_header``: the right password a key that decrypts, a wrong one ``wrong_password``;
  ``unlock`` calls it and behaves as before.

Pure: every file lives in ``tmp_path`` or is a committed vector, read only; no database, no server, no network. The
module is imported by each test that needs it (the ``sealed`` fixture), never at collection: until checkpoint 2 writes
it, each of those tests FAILS (not skips) with the ``ModuleNotFoundError`` of
``backend.app.services.platform.instance_backup.sealed``, and SEALED-012 fails naming ``envelope.unlock_header``. The
age interoperability tests are the only ones that may skip, with a reason naming the missing binary. The vectors' keys
are TEST ONLY keys, published with the repository.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import zipfile
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import pyrage
import pytest
from pyrage import x25519

from backend.app.services.platform.instance_backup import envelope
from backend.test_scripts.test_utils import print_section, print_success

SEALED_MODULE = "backend.app.services.platform.instance_backup.sealed"

POSIX = os.name != "nt"
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")

#: The committed vectors (contract §9.1), found from this file's path, never from the working directory.
VECTORS_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "backup_l3"
VECTORS_INDEX = VECTORS_DIR / "vectors.json"
GOOD_TAR = "librefolio-backup-20261023-030012.tar"

# The contract's values (§3), written here independently of the module.
MEMBERS = ("manifest.json", "password.age", "backup.lfbk")
FORMAT = "lfbk-tar"
FORMAT_VERSION = 1
PASSWORD_LENGTH = 43
SMALL_MEMBER_MAX = 4096
HEAD_BYTES = 10240
FILE_SUFFIX = ".tar"
MTIME = 1792724412
CREATED_AT = datetime(2026, 10, 23, 3, 0, 12, tzinfo=UTC)
CONTRACT_CONSTANTS = {
    "MEMBERS": MEMBERS,
    "FORMAT": FORMAT,
    "FORMAT_VERSION": FORMAT_VERSION,
    "PASSWORD_LENGTH": PASSWORD_LENGTH,
    "SMALL_MEMBER_MAX": SMALL_MEMBER_MAX,
    "HEAD_BYTES": HEAD_BYTES,
    "FILE_SUFFIX": FILE_SUFFIX,
}
SEALED_CODES = ("sealed_tar_invalid", "sealed_manifest_invalid", "sealed_no_identity", "sealed_password_invalid", "sealed_identity_invalid")
#: A password of the contract's form (§3.3): 43 characters of the base64url alphabet, no padding.
PASSWORD_FORM = re.compile(r"[A-Za-z0-9_-]{43}")
#: What a binary age file starts with, and what an armored one would.
AGE_BINARY_HEADER = b"age-encryption.org/v1\n"
AGE_ARMOR_HEADER = b"-----BEGIN AGE ENCRYPTED FILE-----"
#: The reference age binary (Go), for the optional interoperability tests.
AGE_BINARY = "age"
AGE_TIMEOUT_SECONDS = 60


# =============================================================================
# The vectors, read once
# =============================================================================


def _load_index() -> dict:
    return json.loads(VECTORS_INDEX.read_text(encoding="utf-8"))


try:
    INDEX: dict = _load_index()
    CASES = [pytest.param(case, id=case["file"].removesuffix(".tar")) for case in INDEX["cases"]]
    DERIVATIONS = [pytest.param(row, id=f"instance-{row['instance']}-v{row['version']}") for row in INDEX["cloud_derivation"]]
except (OSError, ValueError, KeyError) as exc:  # the collection of the suite never crashes on a missing index
    INDEX = {}
    CASES = [pytest.param({"error": f"{VECTORS_INDEX} cannot be read: {exc}"}, id="vectors-unreadable")]
    DERIVATIONS = CASES


def _case(file: str) -> dict:
    return next(case for case in INDEX["cases"] if case["file"] == file)


def _require_index(case: dict) -> None:
    if "error" in case:
        pytest.fail(case["error"])


# =============================================================================
# Fixtures and helpers
# =============================================================================


@pytest.fixture
def sealed() -> ModuleType:
    """``instance_backup.sealed`` (checkpoint 2), imported by each test that needs it, never at collection: until it
    exists, each test FAILS on its own with this message (never a skip)."""
    try:
        return importlib.import_module(SEALED_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != SEALED_MODULE:
            raise
        pytest.fail(f"{SEALED_MODULE} does not exist: lot L3 checkpoint 2 is not written yet ({exc})")


@pytest.fixture
def unlock_header():
    """``envelope.unlock_header`` (checkpoint 2, interface §3), looked up when the test runs."""
    function = getattr(envelope, "unlock_header", None)
    if function is None:
        pytest.fail("[new] envelope.unlock_header(header, password) does not exist yet: lot L3 checkpoint 2 adds it (interface §3)")
    return function


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _listing(folder: Path) -> list[str]:
    return sorted(os.listdir(folder))


def _identities_of(name: str) -> list[x25519.Identity]:
    """The keys of a vector's identity file, parsed here with pyrage, independently of ``read_identities``."""
    lines = (VECTORS_DIR / name).read_text(encoding="utf-8").splitlines()
    return [x25519.Identity.from_str(line.strip()) for line in lines if line.startswith("AGE-SECRET-KEY-1")]


def _identity(name: str) -> x25519.Identity:
    (identity,) = _identities_of(name)
    return identity


def _good_members() -> dict[str, bytes]:
    """The three members of the good vector, read here with ``tarfile``: what ``write_sealed`` must seal again."""
    with tarfile.open(VECTORS_DIR / GOOD_TAR, mode="r:") as tar:
        members = tar.getmembers()
        assert [member.name for member in members] == list(MEMBERS) and all(member.isreg() for member in members), f"precondition: the good vector holds the three regular members: {[member.name for member in members]}"
        return {member.name: tar.extractfile(member).read() for member in members}


def _good_manifest() -> dict:
    return json.loads(_good_members()["manifest.json"])


def _canonical(document: dict) -> bytes:
    """A manifest as the contract writes one (§3.2): sorted keys, no spaces, UTF-8, no final line break."""
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def _info(name: str, size: int, kind: bytes = tarfile.REGTYPE) -> tarfile.TarInfo:
    """A member's header with the fields of the contract's §3.4."""
    info = tarfile.TarInfo(name)
    info.mode, info.uid, info.gid, info.uname, info.gname = 0o600, 0, 0, "", ""
    info.mtime = MTIME
    info.type = kind
    info.size = size if kind == tarfile.REGTYPE else 0
    if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
        info.linkname = "backup.lfbk"
    return info


def _tar(members: list[tuple[str, bytes]], *, kinds: dict[str, bytes] | None = None, pax: dict[str, dict[str, str]] | None = None, global_pax: dict[str, str] | None = None) -> bytes:
    """A tar of ``members``, ustar unless a PAX header is asked for: ``kinds`` gives a member another type, ``pax`` a
    member its own PAX header, ``global_pax`` a global one."""
    kinds, pax = kinds or {}, pax or {}
    use_pax = bool(pax or global_pax)
    out = io.BytesIO()
    options = {"format": tarfile.PAX_FORMAT, "pax_headers": global_pax or {}} if use_pax else {"format": tarfile.USTAR_FORMAT}
    with tarfile.open(fileobj=out, mode="w", **options) as tar:
        for name, data in members:
            info = _info(name, len(data), kinds.get(name, tarfile.REGTYPE))
            if name in pax:
                info.pax_headers = pax[name]
            if info.isreg():
                tar.addfile(info, io.BytesIO(data))
            else:
                tar.addfile(info)
    return out.getvalue()


def _gnu_long_name_tar(members: list[tuple[str, bytes]], long_named: str) -> bytes:
    """A tar whose member ``long_named`` is preceded by a GNU ``././@LongLink`` header carrying its own name: ``tarfile``
    then lists the very three names, regular files without PAX headers, so only the GNU header breaks the rules."""
    out = io.BytesIO()
    for name, data in members:
        if name == long_named:
            out.write(tarfile.TarInfo._create_gnu_long_header(name, tarfile.GNUTYPE_LONGNAME, "utf-8", "surrogateescape"))
        out.write(_info(name, len(data)).tobuf(tarfile.USTAR_FORMAT, "utf-8", "surrogateescape"))
        out.write(data + b"\0" * (-len(data) % 512))
    out.write(b"\0" * 1024)
    raw = out.getvalue()
    return raw + b"\0" * (-len(raw) % tarfile.RECORDSIZE)


def _members_with(**replaced: bytes) -> list[tuple[str, bytes]]:
    """The good vector's three members, in order, some replaced (``manifest_json``, ``password_age``, ``backup_lfbk``)."""
    good = _good_members()
    names = {"manifest_json": "manifest.json", "password_age": "password.age", "backup_lfbk": "backup.lfbk"}
    for key, data in replaced.items():
        good[names[key]] = data
    return [(name, good[name]) for name in MEMBERS]


def _manifest_with(**fields: object) -> bytes:
    """The good manifest with ``fields`` changed, written canonically."""
    document = _good_manifest()
    document.update(fields)
    return _canonical(document)


def _manifest_without(key: str) -> bytes:
    document = _good_manifest()
    del document[key]
    return _canonical(document)


def _envelope_with(lfbk: bytes) -> list[tuple[str, bytes]]:
    """The good members with another ``backup.lfbk``, the manifest following it, so that only the envelope is off."""
    return _members_with(manifest_json=_manifest_with(lfbk_sha256=_sha256(lfbk), lfbk_size=len(lfbk)), backup_lfbk=lfbk)


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _refused(sealed: ModuleType, code: str, call, *secrets_and_paths: str) -> Exception:
    """``call()`` raises ``SealedError`` with ``code``, its message holding none of ``secrets_and_paths``."""
    with pytest.raises(sealed.SealedError) as raised:
        call()
    assert raised.value.code == code, f"expected SealedError {code}, not {raised.value.code}: {raised.value}"
    shown = str(raised.value)
    leaks = [value for value in secrets_and_paths if value and value in shown]
    assert leaks == [], f"a SealedError message holds no path and no secret: {shown!r}"
    return raised.value


def _read_vector(sealed: ModuleType, name: str):
    return sealed.read_sealed(VECTORS_DIR / name)


def _member_bytes(path: Path, archive) -> bytes:
    """The envelope's bytes as ``archive`` locates them in the file."""
    with path.open("rb") as handle:
        handle.seek(archive.envelope_offset)
        return handle.read(archive.envelope_size)


# =============================================================================
# SEALED-001 The constants and the types
# =============================================================================


def test_sealed_001_constants_error_and_archive_type(sealed):
    """SEALED-001 Every constant the interface publishes, with the contract's value; ``SealedError`` an ``Exception``
    with a ``code``; ``SealedArchive`` a frozen dataclass with the five fields of §4."""
    print_section("SEALED-001: constants and types")
    found = {name: getattr(sealed, name, None) for name in CONTRACT_CONSTANTS}
    assert found == CONTRACT_CONSTANTS, f"the constants of interface §4: {found}"
    assert issubclass(sealed.SealedError, Exception)
    for code in SEALED_CODES:
        error = sealed.SealedError(code, "a message")
        assert error.code == code and str(error) == "a message", f"SealedError(code, message): .code {error.code!r}, str {str(error)!r}"
    assert dataclasses.is_dataclass(sealed.SealedArchive), "SealedArchive is a dataclass"
    assert sealed.SealedArchive.__dataclass_params__.frozen, "SealedArchive is frozen"
    fields = {field.name for field in dataclasses.fields(sealed.SealedArchive)}
    assert {"manifest", "password_age", "envelope_offset", "envelope_size", "envelope_header"} <= fields, f"the fields of SealedArchive: {sorted(fields)}"
    print_success(f"{len(found)} constants, {len(SEALED_CODES)} codes")


# =============================================================================
# SEALED-002 Every vector through the reader
# =============================================================================


@pytest.mark.parametrize("case", CASES)
def test_sealed_002_vector_file_is_the_committed_one(case):
    """SEALED-002 precondition: each vector file is the one ``vectors.json`` describes (size and SHA-256), so a red of
    the reader is never a changed fixture."""
    _require_index(case)
    data = (VECTORS_DIR / case["file"]).read_bytes()
    assert (len(data), _sha256(data)) == (case["tar_size"], case["tar_sha256"]), f"{case['file']} differs from vectors.json"
    print_success(f"{case['file']}: {len(data)} bytes, {case['tar_sha256'][:16]}…")


def _check_ok_case(sealed: ModuleType, case: dict, tmp_path: Path) -> None:
    good = _case(GOOD_TAR)
    path = VECTORS_DIR / case["file"]
    archive = sealed.read_sealed(path)
    assert isinstance(archive, sealed.SealedArchive)
    recipients = [INDEX["recipients"][name] for name in case["identities"]]
    if "manifest" in case:
        assert archive.manifest == case["manifest"], f"the manifest read: {archive.manifest}"
    else:
        assert archive.manifest["recipients"] == recipients, f"the recipients, in the order written: {archive.manifest['recipients']}"
    assert archive.envelope_size == good["lfbk_size"], f"envelope_size {archive.envelope_size}"
    assert _sha256(_member_bytes(path, archive)) == good["lfbk_sha256"], "envelope_offset/envelope_size locate the backup.lfbk member"
    assert archive.envelope_offset + envelope.HEADER_SIZE <= HEAD_BYTES, f"the envelope's header lies within the first {HEAD_BYTES} bytes (§3.1): offset {archive.envelope_offset}"
    assert archive.envelope_header == envelope.EnvelopeHeader.from_bytes(bytes.fromhex(good["lfbk_header_hex"])), "the 52 header bytes, parsed"
    assert archive.envelope_header.check.hex() == good["lfbk_check_hex"]
    if case["file"] == GOOD_TAR:
        assert archive.password_age == _good_members()["password.age"], "password_age is the member's bytes"

    for name in case["identities"]:
        assert sealed.open_password(archive, _identities_of(name)) == case["password"], f"{case['file']} opens with {name} on its own"
    key = sealed.check_password(archive, case["password"])
    assert isinstance(key, envelope.EnvelopeKey) and key.header == archive.envelope_header

    lfbk = tmp_path / "out" / "backup.lfbk"
    lfbk.parent.mkdir()
    sealed.extract_envelope(path, archive, lfbk)
    assert _sha256(lfbk.read_bytes()) == good["lfbk_sha256"], "extract_envelope copies the backup.lfbk member"
    if POSIX:
        assert _mode(lfbk) == 0o600, f"the extracted envelope is 0600, not {oct(_mode(lfbk))}"
    assert _listing(lfbk.parent) == ["backup.lfbk"], f"no .part left: {_listing(lfbk.parent)}"
    clear = tmp_path / "out" / "archive.zip"
    envelope.decrypt_file(lfbk, clear, key)
    assert _sha256(clear.read_bytes()) == good["zip_sha256"], "the decrypted envelope is the vectors' zip"


@pytest.mark.parametrize("case", CASES)
def test_sealed_002_every_vector_gives_its_expected_outcome(sealed, case, tmp_path):
    """SEALED-002 Each case of ``vectors.json`` through ``read_sealed`` → ``open_password`` → ``check_password`` →
    ``extract_envelope`` → ``envelope.decrypt_file``, stopping where its ``expect`` says, with that code."""
    _require_index(case)
    print_section(f"SEALED-002: {case['file']} → {case['expect']}")
    path = VECTORS_DIR / case["file"]
    expect = case["expect"]
    hidden = (str(path), str(VECTORS_DIR), case.get("password", ""))

    if expect in ("sealed_tar_invalid", "sealed_manifest_invalid"):
        _refused(sealed, expect, lambda: sealed.read_sealed(path), *hidden)
    elif expect == "ok":
        _check_ok_case(sealed, case, tmp_path)
    elif expect == "sealed_no_identity":
        archive = sealed.read_sealed(path)
        identities = [identity for name in case["identities"] for identity in _identities_of(name)]
        _refused(sealed, expect, lambda: sealed.open_password(archive, identities), *hidden)
    elif expect == "wrong_password":
        archive = sealed.read_sealed(path)
        password = sealed.open_password(archive, _identities_of(case["identities"][0]))
        assert password == case["password"], "password.age opens: the refusal comes from the envelope"
        with pytest.raises(envelope.EnvelopeError) as raised:
            sealed.check_password(archive, password)
        assert raised.value.code == "wrong_password", f"check_password: wrong_password, not {raised.value.code}"
        assert password not in str(raised.value)
    elif expect == "envelope_damaged":
        archive = sealed.read_sealed(path)
        password = sealed.open_password(archive, _identities_of(case["identities"][0]))
        assert password == case["password"]
        key = sealed.check_password(archive, password)
        lfbk = tmp_path / "backup.lfbk"
        sealed.extract_envelope(path, archive, lfbk)
        with pytest.raises(envelope.EnvelopeError) as raised:
            envelope.decrypt_file(lfbk, tmp_path / "archive.zip", key)
        assert raised.value.code == "envelope_damaged"
        assert not (tmp_path / "archive.zip").exists(), "nothing is left of a damaged decryption"
    else:
        pytest.fail(f"vectors.json names an outcome this test does not know: {expect}")
    print_success(f"{case['file']}: {expect}")


# =============================================================================
# SEALED-003 write_sealed
# =============================================================================


def _envelope_file(tmp_path: Path) -> Path:
    return _write(tmp_path / "source" / "backup.lfbk", _good_members()["backup.lfbk"])


def test_sealed_003_write_sealed_rebuilds_the_good_vector_byte_for_byte(sealed, tmp_path):
    """SEALED-003 §3.4, §9.1: the good vector's three members and ``mtime`` 1792724412 give its very bytes; the
    ``EncryptedFile`` returned is the ``.tar``'s size and SHA-256; ``0600``; no ``.part`` left beside it."""
    print_section("SEALED-003: write_sealed byte for byte")
    members = _good_members()
    dst = tmp_path / "out" / GOOD_TAR
    dst.parent.mkdir()

    written = sealed.write_sealed(dst, manifest=members["manifest.json"], password_age=members["password.age"], envelope=_envelope_file(tmp_path), mtime=MTIME)

    expected = (VECTORS_DIR / GOOD_TAR).read_bytes()
    data = dst.read_bytes()
    assert len(data) == len(expected) and data == expected, f"{len(data)} bytes, sha256 {_sha256(data)}; expected the good vector's {len(expected)}, {_sha256(expected)}"
    assert (written.size, written.sha256) == (len(data), _sha256(data)), f"write_sealed returns the .tar's size and SHA-256: {written}"
    if POSIX:
        assert _mode(dst) == 0o600, f"the .tar is 0600, not {oct(_mode(dst))}"
    assert _listing(dst.parent) == [GOOD_TAR], f"no .part left: {_listing(dst.parent)}"
    print_success(f"{len(data)} bytes, sha256 {written.sha256[:16]}…")


def test_sealed_003_write_sealed_never_writes_over_a_file(sealed, tmp_path):
    """SEALED-003 An existing ``dst`` is ``FileExistsError`` and keeps its bytes; no ``.part`` left."""
    members = _good_members()
    dst = _write(tmp_path / "out" / GOOD_TAR, b"already here")

    with pytest.raises(FileExistsError):
        sealed.write_sealed(dst, manifest=members["manifest.json"], password_age=members["password.age"], envelope=_envelope_file(tmp_path), mtime=MTIME)

    assert dst.read_bytes() == b"already here"
    assert _listing(dst.parent) == [GOOD_TAR], f"no .part left: {_listing(dst.parent)}"
    print_success("FileExistsError, the file kept")


# =============================================================================
# SEALED-004 build_manifest
# =============================================================================


def test_sealed_004_build_manifest_gives_the_good_vectors_bytes(sealed):
    """SEALED-004 §3.2: the good vector's ``manifest.json``, byte for byte, from its fields."""
    good = _case(GOOD_TAR)
    expected = _good_members()["manifest.json"]
    manifest = good["manifest"]

    built = sealed.build_manifest(
        created_at=CREATED_AT,
        lfbk_sha256=manifest["lfbk_sha256"],
        lfbk_size=manifest["lfbk_size"],
        recipients=manifest["recipients"],
        librefolio_version=manifest["librefolio_version"],
        db_revision=manifest["db_revision"],
    )

    assert built == expected, f"build_manifest:\n  got      {built!r}\n  expected {expected!r}"
    print_success(built.decode())


def test_sealed_004_build_manifest_writes_created_at_in_utc(sealed):
    """SEALED-004 ``created_at`` is written in UTC with the final ``Z``: the same instant given at +02:00."""
    manifest = _case(GOOD_TAR)["manifest"]
    elsewhere = CREATED_AT.astimezone(timezone(timedelta(hours=2)))

    built = sealed.build_manifest(created_at=elsewhere, lfbk_sha256=manifest["lfbk_sha256"], lfbk_size=manifest["lfbk_size"], recipients=manifest["recipients"], librefolio_version=manifest["librefolio_version"], db_revision=manifest["db_revision"])

    assert json.loads(built)["created_at"] == "2026-10-23T03:00:12Z", f"created_at in UTC: {json.loads(built)['created_at']}"
    print_success("05:00:12+02:00 → 2026-10-23T03:00:12Z")


# =============================================================================
# SEALED-005 new_password
# =============================================================================


def test_sealed_005_new_password_is_32_random_bytes_in_base64url(sealed):
    """SEALED-005 §3.3: 43 characters of ``[A-Za-z0-9_-]``, 32 bytes once decoded, a new one at each call."""
    first, second = sealed.new_password(), sealed.new_password()
    for password in (first, second):
        assert isinstance(password, str) and PASSWORD_FORM.fullmatch(password), f"43 base64url characters: {len(password)}"
        assert len(base64.urlsafe_b64decode(password + "=")) == 32
    assert first != second, "two calls give two passwords"
    print_success("43 characters, 32 bytes, never twice the same")


# =============================================================================
# SEALED-006 seal_password and open_password
# =============================================================================


@pytest.fixture
def good_archive(sealed):
    """The good vector, read: the start of the archives whose ``password_age`` a test replaces."""
    return _read_vector(sealed, GOOD_TAR)


def test_sealed_006_seal_password_is_binary_age_that_opens_round_trip(sealed, good_archive):
    """SEALED-006 ``seal_password`` writes binary age (never armor) that pyrage opens; ``open_password`` gives it back with
    either of two recipients' identities, and with a list holding a stranger first."""
    print_section("SEALED-006: seal and open")
    first, second, stranger = x25519.Identity.generate(), x25519.Identity.generate(), x25519.Identity.generate()
    password = sealed.new_password()

    sealed_bytes = sealed.seal_password(password, [str(first.to_public()), str(second.to_public())])

    assert isinstance(sealed_bytes, bytes) and sealed_bytes.startswith(AGE_BINARY_HEADER), "binary age"
    assert AGE_ARMOR_HEADER not in sealed_bytes, "never armored"
    assert password.encode() not in sealed_bytes
    assert pyrage.decrypt(sealed_bytes, [first]) == password.encode("ascii"), "the plaintext is the password in ASCII, no line break"
    archive = dataclasses.replace(good_archive, password_age=sealed_bytes)
    for identities in ([first], [second], [stranger, second]):
        assert sealed.open_password(archive, identities) == password
    print_success("binary age, opened with each identity")


def test_sealed_006_open_password_with_another_identity_is_no_identity(sealed, good_archive):
    """SEALED-006 No identity opens it: ``sealed_no_identity``."""
    password = sealed.new_password()
    archive = dataclasses.replace(good_archive, password_age=sealed.seal_password(password, [str(x25519.Identity.generate().to_public())]))

    _refused(sealed, "sealed_no_identity", lambda: sealed.open_password(archive, [x25519.Identity.generate()]), password)
    print_success("sealed_no_identity")


#: Plaintexts of ``password.age`` that are not a password of §3.3.
BAD_PLAINTEXTS = [
    pytest.param(b"A" * 42, id="42-characters"),
    pytest.param(b"A" * 44, id="44-characters"),
    pytest.param(b"A" * 43 + b"\n", id="a-final-line-break"),
    pytest.param(b"A" * 42 + b"=", id="padding"),
    pytest.param(b"A" * 42 + b"+", id="base64-not-url"),
    pytest.param(b"A" * 42 + b"/", id="slash"),
    pytest.param(b"A" * 41 + "é".encode(), id="not-ascii"),
    pytest.param(b"A" * 42 + b"\xff", id="not-utf8"),
    pytest.param(b"", id="empty"),
]


@pytest.mark.parametrize("plaintext", BAD_PLAINTEXTS)
def test_sealed_006_a_plaintext_that_is_no_password_is_refused(sealed, good_archive, plaintext):
    """SEALED-006 §3.5: the decrypted password must be exactly 43 base64url ASCII characters, else
    ``sealed_password_invalid``, the plaintext never in the message. Built with pyrage directly."""
    identity = x25519.Identity.generate()
    archive = dataclasses.replace(good_archive, password_age=pyrage.encrypt(plaintext, [identity.to_public()]))

    _refused(sealed, "sealed_password_invalid", lambda: sealed.open_password(archive, [identity]), plaintext.decode("utf-8", "ignore").strip())
    print_success(f"{len(plaintext)} bytes: sealed_password_invalid")


# =============================================================================
# SEALED-007 read_sealed refusals beyond the vectors
# =============================================================================


def _good_triplet() -> list[tuple[str, bytes]]:
    return _members_with()


#: (what the archive is, how it is built, the code): each archive breaks one rule, the rest as the good vector.
TAR_REFUSALS = [
    pytest.param(lambda: _tar(_good_triplet(), pax={"password.age": {"comment": "pax"}}), id="a-pax-header"),
    pytest.param(lambda: _tar(_good_triplet(), global_pax={"comment": "pax"}), id="a-global-pax-header"),
    pytest.param(lambda: _gnu_long_name_tar(_good_triplet(), "manifest.json"), id="a-gnu-long-name"),
    pytest.param(lambda: _tar(_good_triplet(), kinds={"password.age": tarfile.DIRTYPE}), id="a-directory"),
    pytest.param(lambda: _tar(_good_triplet(), kinds={"password.age": tarfile.LNKTYPE}), id="a-hard-link"),
    pytest.param(lambda: _tar(_good_triplet()[:2]), id="two-members"),
    pytest.param(lambda: _tar([("manifest.json", _good_members()["manifest.json"]), ("password.age", _good_members()["password.age"]), ("backup.LFBK", _good_members()["backup.lfbk"])]), id="another-name"),
    pytest.param(lambda: _tar([_good_triplet()[1], _good_triplet()[0], _good_triplet()[2]]), id="small-members-swapped"),
    pytest.param(lambda: _tar(_members_with(manifest_json=_good_members()["manifest.json"] + b" " * (SMALL_MEMBER_MAX + 1 - len(_good_members()["manifest.json"])))), id="manifest-4097-bytes"),
    pytest.param(lambda: _tar(_members_with(password_age=_good_members()["password.age"] + b"\0" * (SMALL_MEMBER_MAX + 1 - len(_good_members()["password.age"])))), id="password-age-4097-bytes"),
    pytest.param(lambda: _tar(_envelope_with(b"XFBK" + _good_members()["backup.lfbk"][4:])), id="lfbk-not-lfbk"),
    pytest.param(lambda: _tar(_envelope_with(b"LFBK\x02" + _good_members()["backup.lfbk"][5:])), id="lfbk-version-2"),
    pytest.param(lambda: _tar(_envelope_with(b"LFBK\x01")), id="lfbk-shorter-than-its-header"),
    pytest.param(lambda: (VECTORS_DIR / GOOD_TAR).read_bytes()[:2700], id="truncated-inside-the-envelope"),
    pytest.param(lambda: b"", id="an-empty-file"),
    pytest.param(lambda: b"PK\x03\x04" + b"\0" * 2000, id="not-a-tar"),
]


@pytest.mark.parametrize("build", TAR_REFUSALS)
def test_sealed_007_read_sealed_refuses_a_tar_that_breaks_a_rule(sealed, tmp_path, build):
    """SEALED-007 §3.5 and interface §4: ``sealed_tar_invalid``, its message without the path."""
    path = _write(tmp_path / "copy.tar", build())

    _refused(sealed, "sealed_tar_invalid", lambda: sealed.read_sealed(path), str(path), str(tmp_path))
    print_success("sealed_tar_invalid")


def test_sealed_007_the_gnu_and_pax_archives_hold_the_three_names_for_tarfile():
    """SEALED-007 barrier: the GNU long name archive lists exactly the three regular members without PAX headers, and the
    PAX one only adds PAX headers, so the refusals above come from the headers alone."""
    with tarfile.open(fileobj=io.BytesIO(_gnu_long_name_tar(_good_triplet(), "manifest.json")), mode="r:") as tar:
        listed = [(member.name, member.isreg(), dict(member.pax_headers)) for member in tar.getmembers()]
    assert listed == [(name, True, {}) for name in MEMBERS], f"the GNU archive, as tarfile lists it: {listed}"
    with tarfile.open(fileobj=io.BytesIO(_tar(_good_triplet(), pax={"password.age": {"comment": "pax"}})), mode="r:") as tar:
        listed = [(member.name, member.isreg(), bool(member.pax_headers)) for member in tar.getmembers()]
    assert listed == [("manifest.json", True, False), ("password.age", True, True), ("backup.lfbk", True, False)], f"the PAX archive: {listed}"
    print_success("GNU and PAX archives: the three names, regular")


def test_sealed_007_small_members_of_4096_bytes_are_read(sealed, tmp_path):
    """SEALED-007 The limit is «over 4096»: a manifest of exactly 4096 bytes (the right content, spaces after it) and a
    ``password.age`` of 4096 bytes (``read_sealed`` decrypts nothing) are read."""
    members = _good_members()
    manifest = members["manifest.json"] + b" " * (SMALL_MEMBER_MAX - len(members["manifest.json"]))
    password_age = members["password.age"] + b"\0" * (SMALL_MEMBER_MAX - len(members["password.age"]))
    path = _write(tmp_path / "copy.tar", _tar(_members_with(manifest_json=manifest, password_age=password_age)))

    archive = sealed.read_sealed(path)

    assert archive.manifest == _good_manifest()
    assert archive.password_age == password_age
    print_success("4096 + 4096 bytes read")


def test_sealed_007_a_manifest_in_another_layout_is_read_by_its_content(sealed, tmp_path):
    """SEALED-007 §3.2: «chi legge non la pretende»: the right content, keys in another order, spaces, a final line break."""
    document = _good_manifest()
    manifest = (json.dumps(dict(reversed(list(document.items()))), indent=2) + "\n").encode()
    path = _write(tmp_path / "copy.tar", _tar(_members_with(manifest_json=manifest)))

    assert sealed.read_sealed(path).manifest == document
    print_success("another layout, the same content")


#: (the manifest's bytes): each breaks one rule of the manifest, the members otherwise the good vector's.
MANIFEST_REFUSALS = [
    pytest.param(lambda: b"\xff\xfe" + _good_members()["manifest.json"], id="not-utf8"),
    pytest.param(lambda: b"{not json", id="not-json"),
    pytest.param(lambda: b"[]", id="a-list"),
    pytest.param(lambda: b'{"format":"lfbk-tar",' + _good_members()["manifest.json"][1:], id="duplicate-key"),
    pytest.param(lambda: _manifest_with(comment="a field of version 2"), id="unknown-key"),
    *[pytest.param(lambda key=key: _manifest_without(key), id=f"missing-{key}") for key in ("created_at", "db_revision", "format", "lfbk_sha256", "lfbk_size", "librefolio_version", "password_member", "recipients", "version")],
    pytest.param(lambda: _manifest_with(version="1"), id="version-a-string"),
    pytest.param(lambda: _manifest_with(version=True), id="version-a-boolean"),
    pytest.param(lambda: _manifest_with(version=1.0), id="version-a-float"),
    pytest.param(lambda: _manifest_with(version=2), id="version-2"),
    pytest.param(lambda: _manifest_with(format="lfbk-zip"), id="another-format"),
    pytest.param(lambda: _manifest_with(lfbk_size=str(_good_manifest()["lfbk_size"])), id="lfbk-size-a-string"),
    pytest.param(lambda: _manifest_with(lfbk_size=-1), id="lfbk-size-negative"),
    pytest.param(lambda: _manifest_with(lfbk_size=_good_manifest()["lfbk_size"] + 1), id="lfbk-size-not-the-members"),
    pytest.param(lambda: _manifest_with(lfbk_sha256=0), id="lfbk-sha256-not-a-string"),
    pytest.param(lambda: _manifest_with(created_at=1792724412), id="created-at-a-number"),
    pytest.param(lambda: _manifest_with(librefolio_version=13), id="librefolio-version-a-number"),
    pytest.param(lambda: _manifest_with(db_revision=42), id="db-revision-a-number"),
    pytest.param(lambda: _manifest_with(recipients=[]), id="no-recipient"),
    pytest.param(lambda: _manifest_with(recipients=[*INDEX["recipients"].values(), INDEX["cloud_derivation"][0]["recipient"]]), id="three-recipients"),
    pytest.param(lambda: _manifest_with(recipients=INDEX["recipients"]["test-identity-1.txt"]), id="recipients-a-string"),
    pytest.param(lambda: _manifest_with(recipients=["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"]), id="an-ssh-recipient"),
    pytest.param(lambda: _manifest_with(recipients=[42]), id="a-recipient-not-a-string"),
    pytest.param(lambda: _manifest_with(password_member="other.age"), id="password-member-other"),
]


@pytest.mark.parametrize("build", MANIFEST_REFUSALS)
def test_sealed_007_read_sealed_refuses_a_manifest_that_breaks_a_rule(sealed, tmp_path, build):
    """SEALED-007 §3.2, §3.5: ``sealed_manifest_invalid``, its message without the path."""
    path = _write(tmp_path / "copy.tar", _tar(_members_with(manifest_json=build())))

    _refused(sealed, "sealed_manifest_invalid", lambda: sealed.read_sealed(path), str(path), str(tmp_path))
    print_success("sealed_manifest_invalid")


def test_sealed_007_a_private_key_as_recipient_is_refused_and_never_shown(sealed, tmp_path):
    """SEALED-007 A manifest naming an ``AGE-SECRET-KEY-1…`` as recipient is ``sealed_manifest_invalid``, the key never in
    the message."""
    secret = str(x25519.Identity.generate())
    path = _write(tmp_path / "copy.tar", _tar(_members_with(manifest_json=_manifest_with(recipients=[secret]))))

    _refused(sealed, "sealed_manifest_invalid", lambda: sealed.read_sealed(path), secret, secret.lower(), str(path))
    print_success("a private key: sealed_manifest_invalid, not shown")


# =============================================================================
# SEALED-008 read_identities and identity_file_text
# =============================================================================


@pytest.mark.parametrize("name", ["test-identity-1.txt", "test-identity-2.txt"])
def test_sealed_008_read_identities_reads_the_vector_identity_files(sealed, name):
    """SEALED-008 Each vector's identity file (comments, then one key) is one identity, of the recipient ``vectors.json``
    names."""
    identities = sealed.read_identities(VECTORS_DIR / name)

    assert [str(identity.to_public()) for identity in identities] == [INDEX["recipients"][name]]
    print_success(f"{name}: {INDEX['recipients'][name]}")


def test_sealed_008_read_identities_reads_an_age_keygen_file_with_comments_and_blank_lines(sealed, tmp_path):
    """SEALED-008 An ``age-keygen`` file of two keys, with comments and blank lines: both, in order."""
    first, second = x25519.Identity.generate(), x25519.Identity.generate()
    text = f"# created: 2026-10-23T03:00:12Z\n# public key: {first.to_public()}\n{first}\n\n# created: 2026-10-24T03:00:12Z\n# public key: {second.to_public()}\n{second}\n\n"
    path = _write(tmp_path / "keys.txt", text.encode())

    identities = sealed.read_identities(path)

    assert [str(identity.to_public()) for identity in identities] == [str(first.to_public()), str(second.to_public())]
    print_success("two keys, in order")


def _bad_key_line() -> str:
    return "AGE-SECRET-KEY-1" + "Q" * 58


#: (the file's content, what must never be in the message).
IDENTITY_REFUSALS = [
    pytest.param(lambda: (f"# public key: x\n{_bad_key_line()}\n", _bad_key_line()), id="a-bad-key-line"),
    pytest.param(lambda: (f"{x25519.Identity.generate()}\n{_bad_key_line()}\n", _bad_key_line()), id="a-good-key-then-a-bad-one"),
    pytest.param(lambda: (f"{x25519.Identity.generate()}\nnot a key at all\n", "not a key at all"), id="a-line-that-is-no-key"),
    pytest.param(lambda: (lambda recipient: (f"{recipient}\n", recipient))(str(x25519.Identity.generate().to_public())), id="a-recipient-not-an-identity"),
    pytest.param(lambda: ("# created: 2026-10-23T03:00:12Z\n\n# nothing else\n", ""), id="comments-only"),
    pytest.param(lambda: ("", ""), id="empty"),
]


@pytest.mark.parametrize("build", IDENTITY_REFUSALS)
def test_sealed_008_read_identities_refuses_a_file_without_usable_keys(sealed, tmp_path, build):
    """SEALED-008 Nothing usable, or a bad line: ``sealed_identity_invalid``, the line never quoted."""
    text, hidden = build()
    path = _write(tmp_path / "keys.txt", text.encode())

    _refused(sealed, "sealed_identity_invalid", lambda: sealed.read_identities(path), hidden, str(path))
    print_success("sealed_identity_invalid")


def test_sealed_008_read_identities_refuses_a_file_that_is_not_utf8(sealed, tmp_path):
    """SEALED-008 A key file that is not UTF-8 is a bad line: ``sealed_identity_invalid``."""
    path = _write(tmp_path / "keys.txt", f"{x25519.Identity.generate()}\n".encode() + b"\xff\xfe\n")

    _refused(sealed, "sealed_identity_invalid", lambda: sealed.read_identities(path), str(path))
    print_success("not UTF-8: sealed_identity_invalid")


def test_sealed_008_identity_file_text_round_trips(sealed, tmp_path):
    """SEALED-008 ``identity_file_text``: ``# created: <iso>Z``, ``# public key: age1…``, the key line, ending with a line
    break; ``read_identities`` reads it back as the same identity."""
    identity = x25519.Identity.generate()

    text = sealed.identity_file_text(identity, CREATED_AT)

    assert text.splitlines() == ["# created: 2026-10-23T03:00:12Z", f"# public key: {identity.to_public()}", str(identity)], f"the key file's lines: {text!r}"
    assert text.endswith("\n")
    path = _write(tmp_path / "keys.txt", text.encode())
    assert [str(read.to_public()) for read in sealed.read_identities(path)] == [str(identity.to_public())]
    print_success(f"# public key: {identity.to_public()}")


# =============================================================================
# SEALED-009 is_sealed
# =============================================================================


@pytest.mark.parametrize("case", CASES)
def test_sealed_009_every_vector_is_sealed(sealed, case):
    """SEALED-009 Every vector is a ustar archive: ``is_sealed`` is ``True`` (the magic only, nothing checked)."""
    _require_index(case)
    assert sealed.is_sealed(VECTORS_DIR / case["file"]) is True
    print_success(f"{case['file']}: sealed")


def _zip_bytes() -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("manifest.json", "{}")
    return out.getvalue()


NOT_SEALED = [
    pytest.param(lambda: _zip_bytes(), id="a-zip"),
    pytest.param(lambda: _good_members()["backup.lfbk"], id="an-lfbk"),
    pytest.param(lambda: b"", id="empty"),
    pytest.param(lambda: (VECTORS_DIR / GOOD_TAR).read_bytes()[:200], id="shorter-than-the-magic"),
    pytest.param(lambda: None, id="missing"),
]


@pytest.mark.parametrize("build", NOT_SEALED)
def test_sealed_009_anything_else_is_not_sealed(sealed, tmp_path, build):
    """SEALED-009 ``False`` for a zip, an envelope, an empty or short file, a path that does not exist; never raises."""
    data = build()
    path = tmp_path / "file"
    if data is not None:
        path.write_bytes(data)

    assert sealed.is_sealed(path) is False
    print_success("not sealed")


# =============================================================================
# SEALED-010 The cloud coordinator's derivation rows
# =============================================================================


@pytest.mark.parametrize("row", DERIVATIONS)
def test_sealed_010_cloud_derivation_identity_gives_its_recipient(row):
    """SEALED-010 §9.3: for each row, pyrage reads the identity and gives the row's recipient."""
    _require_index(row)
    assert str(x25519.Identity.from_str(row["identity"]).to_public()) == row["recipient"]
    print_success(f"instance {row['instance']} v{row['version']}: {row['recipient']}")


# =============================================================================
# SEALED-011 Interoperability with the age binary (optional)
# =============================================================================


@pytest.fixture
def age_binary() -> str:
    """The reference ``age`` binary; the test is skipped, visibly, when it is not installed."""
    found = shutil.which(AGE_BINARY)
    if found is None:
        pytest.skip(f"the reference '{AGE_BINARY}' binary is not installed (shutil.which('{AGE_BINARY}') is None): interoperability not checked")
    return found


def test_sealed_011_age_decrypts_what_seal_password_writes(sealed, age_binary, tmp_path):
    """SEALED-011 (a) ``seal_password``'s output, written to a file, opens with ``age -d -i <identity file>`` written by
    ``identity_file_text``, and gives the password."""
    identity = x25519.Identity.generate()
    password = sealed.new_password()
    age_file = _write(tmp_path / "password.age", sealed.seal_password(password, [str(identity.to_public())]))
    keys = _write(tmp_path / "keys.txt", sealed.identity_file_text(identity, CREATED_AT).encode())

    completed = subprocess.run([age_binary, "-d", "-i", str(keys), str(age_file)], capture_output=True, timeout=AGE_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"age -d failed: {completed.stderr.decode(errors='replace')}"
    assert completed.stdout == password.encode("ascii")
    print_success("age -d gives the password")


def test_sealed_011_open_password_reads_what_age_writes(sealed, age_binary, tmp_path):
    """SEALED-011 (b) A ``password.age`` made by ``age -r <recipient> -o …`` from the good password, sealed with
    ``write_sealed`` around the good envelope: ``read_sealed`` → ``open_password`` gives the password, which
    ``check_password`` accepts."""
    good = _case(GOOD_TAR)
    recipient = INDEX["recipients"]["test-identity-1.txt"]
    out = tmp_path / "password.age"
    completed = subprocess.run([age_binary, "-r", recipient, "-o", str(out)], input=good["password"].encode("ascii"), capture_output=True, timeout=AGE_TIMEOUT_SECONDS, check=False)
    assert completed.returncode == 0, f"age -r failed: {completed.stderr.decode(errors='replace')}"
    members = _good_members()
    dst = tmp_path / "out" / GOOD_TAR
    dst.parent.mkdir()
    sealed.write_sealed(dst, manifest=members["manifest.json"], password_age=out.read_bytes(), envelope=_envelope_file(tmp_path), mtime=MTIME)

    archive = sealed.read_sealed(dst)

    assert sealed.open_password(archive, _identities_of("test-identity-1.txt")) == good["password"]
    sealed.check_password(archive, good["password"])
    print_success("age -r → open_password → check_password")


def test_sealed_011_age_decrypts_the_good_vectors_password(age_binary):
    """SEALED-011 (c) Contract §9.2, automated where the binary is installed: ``age -d -i test-identity-1.txt`` opens the
    good vector's ``password.age``."""
    good = _case(GOOD_TAR)
    completed = subprocess.run([age_binary, "-d", "-i", str(VECTORS_DIR / "test-identity-1.txt")], input=_good_members()["password.age"], capture_output=True, timeout=AGE_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"age -d failed: {completed.stderr.decode(errors='replace')}"
    assert completed.stdout == good["password"].encode("ascii")
    print_success("age -d opens the good vector's password.age")


# =============================================================================
# SEALED-012 envelope.unlock_header
# =============================================================================


def test_sealed_012_unlock_header_opens_with_the_right_password(unlock_header, tmp_path):
    """SEALED-012 The good vector's header and password give a key that decrypts its envelope into the vectors' zip."""
    good = _case(GOOD_TAR)
    header = envelope.EnvelopeHeader.from_bytes(bytes.fromhex(good["lfbk_header_hex"]))
    lfbk = _write(tmp_path / "backup.lfbk", _good_members()["backup.lfbk"])

    key = unlock_header(header, good["password"])

    assert isinstance(key, envelope.EnvelopeKey) and key.header == header
    envelope.decrypt_file(lfbk, tmp_path / "archive.zip", key)
    assert _sha256((tmp_path / "archive.zip").read_bytes()) == good["zip_sha256"]
    print_success("unlock_header: the key decrypts")


def test_sealed_012_unlock_header_refuses_a_wrong_password(unlock_header):
    """SEALED-012 A wrong password: ``EnvelopeError`` ``wrong_password``, the password not in the message."""
    good = _case(GOOD_TAR)
    header = envelope.EnvelopeHeader.from_bytes(bytes.fromhex(good["lfbk_header_hex"]))
    wrong = _case("neg-wrong-password.tar")["password"]

    with pytest.raises(envelope.EnvelopeError) as raised:
        unlock_header(header, wrong)

    assert raised.value.code == "wrong_password" and wrong not in str(raised.value)
    print_success("wrong_password")


def test_sealed_012_unlock_calls_unlock_header_and_behaves_as_before(unlock_header, monkeypatch, tmp_path):
    """SEALED-012 ``unlock(path, password)`` reads the header and calls ``unlock_header`` (interface §3): the right
    password a key with that header, a wrong one ``wrong_password``."""
    good = _case(GOOD_TAR)
    lfbk = _write(tmp_path / "backup.lfbk", _good_members()["backup.lfbk"])
    calls: list[envelope.EnvelopeHeader] = []

    def recorded(header, password):
        calls.append(header)
        return unlock_header(header, password)

    monkeypatch.setattr(envelope, "unlock_header", recorded)

    key = envelope.unlock(lfbk, good["password"])
    assert key.header == envelope.read_header(lfbk)
    assert calls == [key.header], f"unlock calls unlock_header once with the header it read: {calls}"
    with pytest.raises(envelope.EnvelopeError) as raised:
        envelope.unlock(lfbk, _case("neg-wrong-password.tar")["password"])
    assert raised.value.code == "wrong_password"
    print_success("unlock → unlock_header")
