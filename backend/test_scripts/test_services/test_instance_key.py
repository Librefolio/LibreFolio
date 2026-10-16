"""
The instance key (workstream H, platform, checkpoint CP3).

Under test: ``backend/app/services/platform/instance_key.py``. One secret per installation, from which every encryption
key of LibreFolio is derived: ``derive_key(purpose)`` gives each use (the secrets of the plugin settings, the backups) a
key of its own, and no consumer handles the instance key itself. The contract:

(a) The derivation is HKDF-SHA256 (RFC 5869), checked on the three SHA-256 test vectors of the RFC and on its length
    bounds. Its inputs never change: known answers (computed independently with ``openssl kdf``) pin the salt, the info
    (the purpose, a zero byte, the length on two bytes big-endian) and the key encoding, because a change would make
    everything encrypted with a derived key unreadable.
(b) ``derive_key``: deterministic, one key per purpose and per length, so a short key is never the prefix of a longer
    one; a purpose outside ``[a-z0-9][a-z0-9._:-]{0,127}`` or a length that is not an ``int`` from 1 to 8160 is refused
    before the key is even looked for: no key file is generated, and a key source that cannot be read is not reached.
(c) Where the key comes from, first match wins: ``LIBREFOLIO_INSTANCE_KEY``, ``LIBREFOLIO_INSTANCE_KEY_FILE``, the
    generated ``<data dir>/secrets/instance.key``. A blank variable counts as unset; a byte order mark at the start of a
    key file is not part of the key. A configured key shorter than 32 characters is an ``InstanceKeyError`` naming its
    origin (the variable, or the file variable with its path), and so is a ``_FILE`` that cannot give its secret; neither
    falls back to a generated key, and a configured key creates nothing.
(d) Generation on first use: the folder ``0700``, the file ``0600`` holding 32 random bytes in base64url and a newline,
    published by a hard link from a temporary file in the same folder (an exclusive create where hard links are refused),
    the temporary file always removed; later calls reuse the file. Of several processes generating at once, the first key
    published wins and every process uses it: shown with injected losses at both publication points, and with six real
    processes released together by a barrier, with hard links and without.
(e) A key file that is empty or blank, too short, not UTF-8 or too large is an error and is NEVER replaced, since
    whatever the old key encrypted would become unreadable; the error says to restore it from a backup. Without hard
    links the file appears before its content, so a reader that finds it unusable waits for the writer, for half a second
    at most, and accepts the key once written, without rewriting anything. A key file that cannot be reached (a
    ``secrets`` folder the server cannot search, a ``secrets`` that is not a folder) or that is a dangling link is an
    error too: the key may still exist, so none is generated in its place. A data directory where the file cannot be
    made is an error.
(f) ``instance_key_status()`` reports the source, the problem and the permissions open to group or others, without
    creating the key, without waiting and without raising.
(g) ``derive_key_from(key, purpose, length=32)`` (1.3.0, H-14): the derivation of ``derive_key`` from a key it is given,
    for a restore that re-encrypts what a backup's instance key encrypted. Known answers computed by ``derive_key`` with
    that key configured; equal to ``derive_key`` when given the instance key, configured or generated (read as the module
    reads it); the key given wins over the instance's. Pure: it never looks for the instance key, generates no key file,
    and a broken key source does not affect it. Checked in order: an invalid purpose or length is a ``ValueError`` with
    the message of ``derive_key``, whatever the key; a key that is not a ``str`` is a ``TypeError``; a key shorter than
    32 characters (bytes do not count) is an ``InstanceKeyError`` that never shows it, 32 is enough. Two keys, two
    derived keys. Until it exists, each of its tests fails on its own barrier, ``derive_key_from is missing``.

Pure: the data directory is in ``tmp_path`` (``LIBREFOLIO_TEST_MODE=1`` and ``LIBREFOLIO_TEST_DATA_DIR``) and the
configured key is set or removed through ``monkeypatch``: no database, no server, no network, nothing written in the
repository. The cases of a key file that cannot be reached run on a production data directory in ``tmp_path``
(``LIBREFOLIO_TEST_MODE=0``, ``LIBREFOLIO_DATA_DIR``): in test mode ``get_data_dir()`` first validates the test root,
which stops on such a ``secrets`` folder by a rule of its own, before the key code runs. The waits of a reader are
recorded instead of slept, the writer it waits for finishing during the first one. The mode checks run on POSIX only,
and the permission-denied cases are skipped as root, which bypasses them.
"""

from __future__ import annotations

import errno
import multiprocessing
import os
import queue
import re
import stat
import time
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import SECRET_FILE_MAX_BYTES, SecretFileError, read_secret_file
from backend.app.services.platform import instance_key
from backend.app.services.platform.instance_key import (
    INSTANCE_KEY_FILE,
    INSTANCE_KEY_MIN_LENGTH,
    InstanceKeyError,
    InstanceKeyStatus,
    derive_key,
    hkdf_sha256,
    instance_key_path,
    instance_key_status,
)
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")
needs_posix_paths = pytest.mark.skipif(not POSIX, reason="Windows reports a path below a file as missing, not as ENOTDIR")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")

KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"

#: The fixed inputs of the derivation, written out here so that a change to them in the module is caught.
DERIVATION_SALT = b"LibreFolio instance key derivation v1"
KNOWN_KEY = "LibreFolio-known-answer-instance-key-0123456789"
#: HKDF-SHA256(ikm=KNOWN_KEY, salt=DERIVATION_SALT, info=purpose || 0x00 || length on 2 bytes big-endian, L=length),
#: computed with OpenSSL 3, independently of the code under test:
#: openssl kdf -keylen <length> -kdfopt digest:SHA256 -kdfopt key:<KNOWN_KEY> -kdfopt "salt:<DERIVATION_SALT>" -kdfopt hexinfo:<info> HKDF
KNOWN_ANSWERS = {
    ("plugins.settings.v1", 32): "ef886b05a0fb9710b6684a6c433cec761fab2fd8c1dfef56c9547f2130de127a",
    ("backup.v1", 32): "7bb5c4c568b646c61648ff37bd5249431ac6a3c68b76f40932072842b1a8aabe",
    ("plugins.settings.v1", 16): "9db5983d380b357265d7b25cdb0a2fd0",
    ("plugins.settings.v1", 64): "e243f930f1aec87407a15a640090b46e176472e8503d5837c09eae0b43fbc6bfd8e89e156678be543b3991e2d3730cb317d65308c60b1797c78e78d402a20552",
}
PURPOSE = "plugins.settings.v1"
KNOWN_ANSWER = KNOWN_ANSWERS[(PURPOSE, 32)]

#: What a generated key file holds: 32 random bytes in base64url without padding (43 characters), then a newline.
GENERATED_KEY = re.compile(rb"[A-Za-z0-9_-]{43}\n")
#: A key another process published first, in the tests that inject that loss.
WINNER_KEY = "key-published-first-by-another-process-0123"

#: Key files that cannot give a usable key, with what the error must say.
UNUSABLE_KEY_FILES = [
    pytest.param(b"", "is empty or blank", id="empty"),
    pytest.param(b"\n\r\n", "is empty or blank", id="line-breaks-only"),
    pytest.param(b" " * 40 + b"\n", "is empty or blank", id="blank-40-spaces"),
    pytest.param(b"too-short-key\n", "13 characters long", id="too-short"),
    pytest.param(b"k" * (INSTANCE_KEY_MIN_LENGTH - 1) + b"\n", f"{INSTANCE_KEY_MIN_LENGTH - 1} characters long", id="one-character-short"),
    pytest.param(b"\xff\xfe" * 24, "is not UTF-8 text", id="not-utf8"),
    pytest.param(b"k" * (SECRET_FILE_MAX_BYTES + 1), "is larger than", id="larger-than-64-KiB"),
]

RACE_PROCESSES = 6
#: Generous: a spawned process imports the application first, and a loaded parallel run is slow. A hang still ends.
RACE_TIMEOUT_SECONDS = 120
#: The longest a reader may wait for a key file still being written, as the module documents it.
MAX_SETTLE_SECONDS = 0.5
#: The hint every error about an unusable generated key ends with: a new key would lose what the old one encrypted.
RESTORE_HINT = "restore the file from a backup"


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    """The waits of a reader of the key file, recorded instead of slept: the tests stay fast, and the waits are visible."""
    recorded: list[float] = []
    monkeypatch.setattr(instance_key, "time", SimpleNamespace(sleep=recorded.append))
    return recorded


@pytest.fixture
def data_dir(monkeypatch, tmp_path) -> Path:
    """A data directory of this test only, with no configured key: the generated key file lives in it.

    It does not exist yet: whatever the code under test creates there is visible.
    """
    for variable in (KEY_VARIABLE, KEY_FILE_VARIABLE, "LIBREFOLIO_DATA_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    data = (tmp_path / "data").resolve()
    assert instance_key_path() == data / INSTANCE_KEY_FILE, f"the key file must live in the data directory of this test, not at {instance_key_path()}"
    return data


@pytest.fixture
def production_data_dir(monkeypatch, tmp_path) -> Path:
    """A production data directory of this test only, with no configured key: not created yet.

    Production mode leaves the guard of test roots out of the way, which stops on a ``secrets`` folder it cannot search
    before the key code runs; the key code itself is the subject here.
    """
    for variable in (KEY_VARIABLE, KEY_FILE_VARIABLE, "LIBREFOLIO_TEST_DATA_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "0")
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(tmp_path / "production-data"))
    data = (tmp_path / "production-data").resolve()
    assert instance_key_path() == data / INSTANCE_KEY_FILE, f"the key file must live in the data directory of this test, not at {instance_key_path()}"
    return data


def _derived_from(key: str, purpose: str, length: int = 32) -> bytes:
    """What ``derive_key`` must give with ``key`` as instance key: HKDF-SHA256, with the purpose and the length as info."""
    info = purpose.encode("ascii") + b"\x00" + length.to_bytes(2, "big")
    return hkdf_sha256(key.encode("utf-8"), salt=DERIVATION_SALT, info=info, length=length)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def _write_key_file(data: Path, content: bytes) -> Path:
    """A key file as a previous run (or a damaged disk) left it, in a ``0700`` folder with mode ``0600``."""
    key_file = data / INSTANCE_KEY_FILE
    key_file.parent.mkdir(mode=0o700, parents=True)
    key_file.write_bytes(content)
    key_file.chmod(0o600)
    return key_file


def _assert_generated(key_file: Path, derived: bytes, purpose: str = PURPOSE) -> None:
    """``key_file`` is a generated key alone in its folder, and ``derived`` comes from it."""
    content = key_file.read_bytes()
    assert GENERATED_KEY.fullmatch(content), f"a generated key file holds 43 base64url characters and a newline, not {len(content)} bytes {content[:60]!r}"
    assert derived == _derived_from(content.decode("ascii").rstrip("\n"), purpose), "the derived key does not come from the key file: the newline must not be part of the key"
    assert _entries(key_file.parent) == [key_file.name], f"the key folder must hold the key file alone, no temporary file: {_entries(key_file.parent)}"


# =============================================================================
# (a) HKDF-SHA256
# =============================================================================


@pytest.mark.parametrize(
    ("ikm", "salt", "info", "length", "okm"),
    [
        pytest.param(
            bytes.fromhex("0b" * 22),
            bytes.fromhex("000102030405060708090a0b0c"),
            bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"),
            42,
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865",
            id="rfc5869-test-case-1",
        ),
        pytest.param(
            bytes(range(0x00, 0x50)),
            bytes(range(0x60, 0xB0)),
            bytes(range(0xB0, 0x100)),
            82,
            "b11e398dc80327a1c8e7f78c596a49344f012eda2d4efad8a050cc4c19afa97c59045a99cac7827271cb41c65e590e09da3275600c2f09b8367793a9aca3db71cc30c58179ec3e87c14c01d5c1f3434f1d87",
            id="rfc5869-test-case-2-long-inputs",
        ),
        pytest.param(
            bytes.fromhex("0b" * 22),
            b"",
            b"",
            42,
            "8da4e775a563c18f715f802a063c5a31b8a11f5c5ee1879ec3454e5f3c738d2d9d201395faa4b61a96c8",
            id="rfc5869-test-case-3-empty-salt-and-info",
        ),
    ],
)
def test_hkdf_sha256_matches_the_rfc_5869_test_vectors(ikm, salt, info, length, okm):
    """(a) The test vectors of RFC 5869, appendix A.1-A.3 (SHA-256)."""
    derived = hkdf_sha256(ikm, salt=salt, info=info, length=length)
    assert derived.hex() == okm, f"HKDF-SHA256 disagrees with RFC 5869: got {derived.hex()}, expected {okm}"
    print_success(f"{length} bytes, as the RFC says")


@pytest.mark.parametrize("length", [pytest.param(-1, id="negative"), pytest.param(0, id="zero"), pytest.param(255 * 32 + 1, id="8161")])
def test_hkdf_sha256_refuses_a_length_outside_1_to_8160_bytes(length):
    """(a) HKDF gives at most 255 blocks of the hash: 8160 bytes for SHA-256, and at least one byte."""
    with pytest.raises(ValueError, match=str(length)):
        hkdf_sha256(b"key material", salt=b"salt", info=b"info", length=length)
    print_success(f"length {length} refused")


@pytest.mark.parametrize("length", [pytest.param(1, id="1"), pytest.param(255 * 32, id="8160")])
def test_hkdf_sha256_gives_any_length_from_1_to_8160_bytes(length):
    derived = hkdf_sha256(b"key material", salt=b"salt", info=b"info", length=length)
    assert len(derived) == length, f"asked for {length} bytes, got {len(derived)}"
    print_success(f"{length} bytes")


# =============================================================================
# (b) derive_key
# =============================================================================


@pytest.mark.parametrize(("purpose", "length", "expected"), [(purpose, length, answer) for (purpose, length), answer in KNOWN_ANSWERS.items()], ids=[f"{purpose}-{length}" for purpose, length in KNOWN_ANSWERS])
def test_the_derivation_never_changes(data_dir, monkeypatch, purpose, length, expected):
    """(a)(b) Known answers: salt, info and key encoding are part of every ciphertext ever made with a derived key."""
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    derived = derive_key(purpose, length).hex()
    assert derived == expected, f"derive_key({purpose!r}, {length}) changed ({derived}, was {expected}): every value encrypted with it would become unreadable"
    print_success(f"{purpose}, {length} bytes: {derived}")


def test_derive_key_is_deterministic_and_gives_each_purpose_its_own_key(data_dir, monkeypatch):
    """(b) Same purpose, same key; two purposes, two keys; each is HKDF of the instance key with the purpose and length as info."""
    print_section("Instance key: one key per purpose")
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    purposes = ["plugins.settings.v1", "plugins.settings.v2", "backup.v1", "a", "0", "a._:-", "z" * 128]

    keys = {purpose: derive_key(purpose) for purpose in purposes}

    changed = [purpose for purpose, key in keys.items() if derive_key(purpose) != key]
    assert not changed, f"derive_key is not deterministic for {changed}"
    assert len(set(keys.values())) == len(purposes), "two purposes got the same key"
    wrong = [purpose for purpose, key in keys.items() if key != _derived_from(KNOWN_KEY, purpose)]
    assert not wrong, f"not HKDF-SHA256 of the instance key with the purpose and the length as info: {wrong}"
    print_success(f"{len(purposes)} purposes, {len(purposes)} distinct keys, stable across calls")


@pytest.mark.parametrize("length", [1, 16, 32, 64, 255 * 32])
def test_derive_key_gives_the_length_asked(data_dir, monkeypatch, length):
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    derived = derive_key(PURPOSE, length=length)
    assert derived == _derived_from(KNOWN_KEY, PURPOSE, length), f"derive_key({PURPOSE!r}, length={length}) is not the {length}-byte HKDF output with the length in the info"
    print_success(f"{length} bytes")


def test_the_length_is_part_of_the_derivation(data_dir, monkeypatch):
    """(b) Two lengths, two unrelated keys: a short key of a purpose is never the prefix of a longer one."""
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    keys = {length: derive_key(PURPOSE, length) for length in (16, 32, 64)}

    prefixes = [f"{short} of {long}" for short in keys for long in keys if short < long and keys[long].startswith(keys[short])]

    assert not prefixes, f"the key of {PURPOSE!r} at one length is the prefix of the key at another ({prefixes}): the length must be part of the info"
    assert keys[16] != derive_key(PURPOSE, 32)[:16], "derive_key(purpose, 16) must not be derive_key(purpose, 32)[:16]"
    print_success("16, 32 and 64 bytes: three unrelated keys")


@pytest.mark.parametrize(
    "purpose",
    [
        pytest.param("", id="empty"),
        pytest.param("Plugins.settings.v1", id="uppercase"),
        pytest.param("plugins settings.v1", id="space"),
        pytest.param("a" * 129, id="129-characters"),
        pytest.param(".plugins.v1", id="leading-dot"),
        pytest.param("-plugins.v1", id="leading-dash"),
        pytest.param("_plugins.v1", id="leading-underscore"),
        pytest.param("plugins/settings.v1", id="slash"),
        pytest.param("plugins.v1\n", id="trailing-newline"),
        pytest.param("plügins.v1", id="non-ascii"),
    ],
)
def test_derive_key_refuses_an_invalid_purpose_before_looking_for_the_key(data_dir, purpose):
    """(b) Lowercase letters, digits and . _ : - only, starting with a letter or a digit, at most 128 characters."""
    with pytest.raises(ValueError, match="Invalid key purpose"):
        derive_key(purpose)
    assert not data_dir.exists(), "an invalid purpose must be refused before the key file is generated"
    print_success(f"{purpose[:40]!r} refused, nothing generated")


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(255 * 32 + 1, id="8161"),
        pytest.param(16.0, id="float"),
        pytest.param("32", id="string"),
        pytest.param(None, id="none"),
    ],
)
def test_derive_key_refuses_an_invalid_length_before_looking_for_the_key(data_dir, length):
    """(b) An ``int`` from 1 to 8160 bytes, what HKDF-SHA256 can give; anything else is refused and generates nothing."""
    with pytest.raises(ValueError, match="1 to 8160 bytes"):
        derive_key(PURPOSE, length)
    assert not data_dir.exists(), "an invalid length must be refused before the key file is generated"
    print_success(f"length {length!r} refused, nothing generated")


@pytest.mark.parametrize(("purpose", "length"), [pytest.param("Not a purpose", 32, id="invalid-purpose"), pytest.param(PURPOSE, 0, id="invalid-length")])
def test_an_invalid_request_is_refused_before_the_key_is_read(data_dir, monkeypatch, tmp_path, purpose, length):
    """(b) The request is checked first: with a key source that cannot be read, the error is still about the request."""
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(tmp_path / "missing-key"))

    with pytest.raises(ValueError):
        derive_key(purpose, length)

    print_success(f"{purpose!r}, {length}: ValueError, the broken key source never reached")


# =============================================================================
# (c) Where the key comes from
# =============================================================================


def test_the_key_file_lives_in_the_secrets_folder_of_the_data_directory(data_dir):
    """(c) ``secrets/instance.key``: the path the docs, the backups and the permission checks name."""
    assert Path("secrets") / "instance.key" == INSTANCE_KEY_FILE, f"the key file moved to {INSTANCE_KEY_FILE}: the docs, the backups and validate_test_data_dir name secrets/instance.key"
    assert INSTANCE_KEY_MIN_LENGTH == 32, f"the minimum key length is documented as 32 characters, not {INSTANCE_KEY_MIN_LENGTH}"
    print_success(f"{instance_key_path()}")


def test_a_configured_key_is_used_and_no_key_file_is_created(data_dir, monkeypatch):
    """(c) LIBREFOLIO_INSTANCE_KEY: the key itself; nothing is written in the data directory."""
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    assert derive_key(PURPOSE).hex() == KNOWN_ANSWER, f"derive_key did not use {KEY_VARIABLE}"
    assert not data_dir.exists(), f"a configured key must not create anything in the data directory: {list(data_dir.rglob('*'))}"
    print_success(f"{KEY_VARIABLE} used, nothing created")


def test_a_key_file_named_by_the_environment_is_used(data_dir, monkeypatch, tmp_path):
    """(c) LIBREFOLIO_INSTANCE_KEY_FILE: the key is the file's text without its newline, so the same key as the variable."""
    mounted = tmp_path / "run-secrets" / "instance_key"
    mounted.parent.mkdir()
    mounted.write_text(KNOWN_KEY + "\n", encoding="utf-8")
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))

    assert derive_key(PURPOSE).hex() == KNOWN_ANSWER, f"derive_key did not use {KEY_FILE_VARIABLE}, or kept the newline in the key"
    assert not data_dir.exists(), f"a configured key file must not create anything in the data directory: {list(data_dir.rglob('*'))}"
    print_success(f"{KEY_FILE_VARIABLE} used, nothing created")


def test_the_variable_wins_over_the_file_and_both_over_the_generated_key(data_dir, monkeypatch, tmp_path):
    """(c) First match wins: the variable, then the file, then the generated key, which a configured key leaves untouched."""
    print_section("Instance key: the order of the sources")
    generated = _write_key_file(data_dir, b"generated-key-of-a-previous-run-0123456789\n")
    mounted = tmp_path / "mounted-key"
    mounted.write_text("mounted-key-from-a-docker-secret-0123456789\n", encoding="utf-8")

    monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))
    assert derive_key(PURPOSE) == _derived_from("mounted-key-from-a-docker-secret-0123456789", PURPOSE), f"{KEY_FILE_VARIABLE} must win over the generated key"
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    assert derive_key(PURPOSE).hex() == KNOWN_ANSWER, f"{KEY_VARIABLE} must win over {KEY_FILE_VARIABLE}"
    assert generated.read_bytes() == b"generated-key-of-a-previous-run-0123456789\n", "a configured key must leave the generated key file as it is"
    print_success("variable > file > generated, the generated file untouched")


@pytest.mark.parametrize("source", ["variable", "file"])
@pytest.mark.parametrize(("length", "usable"), [pytest.param(INSTANCE_KEY_MIN_LENGTH - 1, False, id="31-characters"), pytest.param(INSTANCE_KEY_MIN_LENGTH, True, id="32-characters")])
def test_a_configured_key_needs_at_least_32_characters(data_dir, monkeypatch, tmp_path, source, length, usable):
    """(c) Shorter than 32 characters is an InstanceKeyError naming the origin and the length, never the key; 32 is enough."""
    key = "K" * (length - 4) + "tail"
    if source == "variable":
        monkeypatch.setenv(KEY_VARIABLE, key)
        origin = KEY_VARIABLE
    else:
        mounted = tmp_path / "mounted-key"
        mounted.write_text(key + "\n", encoding="utf-8")
        monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))
        origin = f"{KEY_FILE_VARIABLE} ({mounted})"

    if usable:
        assert derive_key(PURPOSE) == _derived_from(key, PURPOSE), f"a configured key of {length} characters must be used"
    else:
        with pytest.raises(InstanceKeyError) as raised:
            derive_key(PURPOSE)
        message = str(raised.value)
        expected = f"{origin}: the instance key is {length} characters long, it needs at least {INSTANCE_KEY_MIN_LENGTH}"
        assert message == expected, f"the error must name where the key comes from and its length:\n  expected {expected!r}\n  got      {message!r}"
        assert key not in message, f"the error shows the key: {message!r}"
    assert not data_dir.exists(), "a configured key, usable or not, must never generate a key file"
    print_success(f"{source}, {length} characters: {'used' if usable else 'refused'}")


@pytest.mark.parametrize("variable", [KEY_VARIABLE, KEY_FILE_VARIABLE])
def test_a_blank_configured_key_is_no_key(data_dir, monkeypatch, variable):
    """(c) A blank LIBREFOLIO_INSTANCE_KEY or _FILE counts as unset: the generated key is used, never forty spaces as a key."""
    monkeypatch.setenv(variable, " " * 40)
    assert instance_key_status() == InstanceKeyStatus("not_created", path=data_dir / INSTANCE_KEY_FILE), f"a blank {variable} must leave the key to be generated: {instance_key_status()}"

    derived = derive_key(PURPOSE)

    _assert_generated(data_dir / INSTANCE_KEY_FILE, derived)
    assert derived != _derived_from(" " * 40, PURPOSE), f"forty spaces in {variable} were used as the instance key"
    print_success(f"blank {variable}: the generated key used")


def test_a_byte_order_mark_is_not_part_of_a_mounted_key(data_dir, monkeypatch, tmp_path):
    """(c) A key file written by an editor that adds a UTF-8 BOM and CRLF gives the same key as the bare text."""
    mounted = tmp_path / "mounted-key"
    mounted.write_bytes(b"\xef\xbb\xbf" + KNOWN_KEY.encode("utf-8") + b"\r\n")
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))

    assert derive_key(PURPOSE).hex() == KNOWN_ANSWER, "the byte order mark or the CRLF of the key file became part of the instance key"
    print_success("BOM and CRLF dropped: the known answer")


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        pytest.param(None, "does not exist", id="missing"),
        pytest.param(b"", "is empty", id="empty"),
        pytest.param(b"\xff" * 40, "is not UTF-8 text", id="not-utf8"),
        pytest.param("directory", "cannot be read (", id="a-directory"),
    ],
)
def test_a_key_file_variable_that_cannot_give_the_key_is_an_error_never_a_generated_key(data_dir, monkeypatch, tmp_path, content, problem):
    """(c) The admin asked for that source: a broken LIBREFOLIO_INSTANCE_KEY_FILE never falls back to generating a key."""
    mounted = tmp_path / "mounted-key"
    if content == "directory":
        mounted.mkdir()
    elif content is not None:
        mounted.write_bytes(content)
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))

    with pytest.raises(InstanceKeyError) as raised:
        derive_key(PURPOSE)

    message = str(raised.value)
    assert message.startswith(f"{KEY_FILE_VARIABLE}: {mounted} ") and problem in message, f"the error must name {KEY_FILE_VARIABLE}, the path and the problem ({problem!r}): {message!r}"
    assert isinstance(raised.value.__cause__, SecretFileError), f"the InstanceKeyError must carry the SecretFileError it comes from, not {raised.value.__cause__!r}"
    assert not data_dir.exists(), f"a broken {KEY_FILE_VARIABLE} must not fall back to generating a key file"
    print_success(message)


# =============================================================================
# (d) Generation on first use
# =============================================================================


def test_the_first_use_generates_the_key_file(data_dir):
    """(d) No configured key: the first derive_key writes a random key in secrets/instance.key and derives from it."""
    print_section("Instance key: generated on first use")
    assert not data_dir.exists(), "the data directory must not exist before the first use"

    derived = derive_key(PURPOSE)

    key_file = data_dir / INSTANCE_KEY_FILE
    assert key_file.is_file(), f"the first use must generate {key_file}"
    _assert_generated(key_file, derived)
    print_success(f"{key_file} generated: 43 base64url characters and a newline, no temporary file left")


@needs_posix_modes
def test_the_generated_key_is_private_to_its_owner(data_dir):
    """(d) The folder 0700 and the file 0600: nobody but the server's user may read the key."""
    derive_key(PURPOSE)
    key_file = data_dir / INSTANCE_KEY_FILE
    modes = {"folder": f"{_mode(key_file.parent):04o}", "file": f"{_mode(key_file):04o}"}
    assert modes == {"folder": "0700", "file": "0600"}, f"the key folder must be 0700 and the key file 0600, not {modes}"
    print_success(f"folder {modes['folder']}, file {modes['file']}")


def test_later_uses_reuse_the_key_file_without_touching_it(data_dir):
    """(d) Same key file, same derived key: the file is neither rewritten nor replaced."""
    first = derive_key(PURPOSE)
    key_file = data_dir / INSTANCE_KEY_FILE
    before = key_file.read_bytes(), key_file.stat().st_ino, key_file.stat().st_mtime_ns

    second = derive_key(PURPOSE)

    assert second == first, "a second use must derive the same key from the same key file"
    assert (key_file.read_bytes(), key_file.stat().st_ino, key_file.stat().st_mtime_ns) == before, "a second use must not rewrite or replace the key file"
    print_success("reused, untouched")


def test_every_installation_generates_its_own_key(data_dir, monkeypatch, tmp_path):
    """(d) The key is random: two data directories, two keys, two derived keys for the same purpose."""
    first_derived, first_file = derive_key(PURPOSE), (data_dir / INSTANCE_KEY_FILE).read_bytes()
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "another-installation"))

    second_derived = derive_key(PURPOSE)

    second_file = ((tmp_path / "another-installation").resolve() / INSTANCE_KEY_FILE).read_bytes()
    assert second_file != first_file and second_derived != first_derived, "two installations got the same instance key: it must be random"
    print_success("two data directories, two keys")


def test_without_hard_links_the_key_file_is_created_exclusively(data_dir, monkeypatch):
    """(d) A filesystem that refuses hard links: the key is created with O_EXCL, still 0600, the temporary file removed."""
    refused: list[Path] = []

    def refuse_hard_links(source, destination, *args, **kwargs):
        refused.append(Path(destination))
        raise OSError(errno.EPERM, "Operation not permitted", str(destination))

    monkeypatch.setattr(os, "link", refuse_hard_links)

    derived = derive_key(PURPOSE)

    key_file = data_dir / INSTANCE_KEY_FILE
    assert refused == [key_file], f"the key must first be published with a hard link onto {key_file}, then fall back: link calls {refused}"
    _assert_generated(key_file, derived)
    if POSIX:
        assert _mode(key_file) == 0o600, f"the key file created without a hard link must be 0600 too, not {_mode(key_file):04o}"
    print_success("hard link refused, key created exclusively, temporary file removed")


def test_a_key_published_first_by_another_process_wins(data_dir, monkeypatch):
    """(d) Another process publishes its key between our check and our hard link: its key is used, ours is dropped."""
    real_link = os.link

    def another_process_publishes_first(source, destination, *args, **kwargs):
        Path(destination).write_text(WINNER_KEY + "\n", encoding="ascii")
        return real_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "link", another_process_publishes_first)

    derived = derive_key(PURPOSE)

    key_file = data_dir / INSTANCE_KEY_FILE
    assert key_file.read_text(encoding="ascii") == WINNER_KEY + "\n", "the key published first must stay: a later process must never replace it"
    assert derived == _derived_from(WINNER_KEY, PURPOSE), "the process that lost the race must use the key that won it"
    assert _entries(key_file.parent) == ["instance.key"], f"the losing process must remove its temporary file: {_entries(key_file.parent)}"
    print_success("the first key published won, the temporary file of the loser removed")


def test_without_hard_links_a_key_created_first_by_another_process_wins(data_dir, monkeypatch):
    """(d) Hard links refused, and another process creates the file before our exclusive create: its key is used."""

    def refuse_after_another_process_created_the_key(source, destination, *args, **kwargs):
        Path(destination).write_text(WINNER_KEY + "\n", encoding="ascii")
        raise OSError(errno.EPERM, "Operation not permitted", str(destination))

    monkeypatch.setattr(os, "link", refuse_after_another_process_created_the_key)

    derived = derive_key(PURPOSE)

    key_file = data_dir / INSTANCE_KEY_FILE
    assert key_file.read_text(encoding="ascii") == WINNER_KEY + "\n", "the exclusive create must not overwrite a key another process created"
    assert derived == _derived_from(WINNER_KEY, PURPOSE), "the process that lost the race must use the key that won it"
    assert _entries(key_file.parent) == ["instance.key"], f"the losing process must remove its temporary file: {_entries(key_file.parent)}"
    print_success("the key created first won, nothing overwritten")


def _refuse_hard_links(source, destination, *args, **kwargs):
    """``os.link`` of a filesystem without hard links."""
    raise OSError(errno.EPERM, "Operation not permitted", str(destination))


def _derive_in_a_racing_process(barrier, results, hard_links: bool) -> None:
    """Runs in a spawned process: wait for every racer, then derive at the same moment as the others.

    Module level, so that the spawned interpreter can import it by name. Without ``hard_links`` this process refuses
    them as such a filesystem would, so the key is created exclusively and appears before its content. Any failure is
    sent back: the parent reports it instead of waiting for an answer that never comes.
    """
    try:
        if not hard_links:
            os.link = _refuse_hard_links  # this spawned interpreter only
        barrier.wait(timeout=RACE_TIMEOUT_SECONDS)
        results.put(("derived", derive_key("race.v1").hex()))
    except Exception as exc:
        results.put(("failed", f"{type(exc).__name__}: {exc}"))


def _race_outcomes(results, racers: list[BaseProcess]) -> list[tuple[str, str]]:
    """One answer per racer, polled with a deadline: a racer that dies or hangs fails the test instead of blocking it."""
    outcomes: list[tuple[str, str]] = []
    deadline = time.monotonic() + RACE_TIMEOUT_SECONDS
    while len(outcomes) < len(racers):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            pytest.fail(f"only {len(outcomes)} of {len(racers)} racing processes answered within {RACE_TIMEOUT_SECONDS} s: {outcomes}")
        try:
            outcomes.append(results.get(timeout=min(remaining, 1.0)))
        except queue.Empty:
            if not any(racer.is_alive() for racer in racers) and results.empty():
                pytest.fail(f"the racing processes exited without answering (exit codes {[racer.exitcode for racer in racers]}): {outcomes}")
    return outcomes


@pytest.mark.parametrize("hard_links", [pytest.param(True, id="hard-links"), pytest.param(False, id="without-hard-links")])
def test_processes_generating_together_all_use_the_one_key_published_first(data_dir, hard_links):
    """(d)(e) Six real processes, released together by a barrier, find no key and generate one: one key file, used by all.

    Without hard links the losers may read the file between its creation and its content: they must wait for it.
    """
    print_section(f"Instance key: {RACE_PROCESSES} processes generating at once, {'with' if hard_links else 'without'} hard links")
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(RACE_PROCESSES)
    results = context.Queue()
    racers = [context.Process(target=_derive_in_a_racing_process, args=(barrier, results, hard_links), daemon=True) for _ in range(RACE_PROCESSES)]
    for racer in racers:
        racer.start()
    try:
        outcomes = _race_outcomes(results, racers)
    finally:
        for racer in racers:
            racer.join(timeout=RACE_TIMEOUT_SECONDS)
            if racer.is_alive():
                racer.kill()
                racer.join(timeout=10)

    failures = [detail for outcome, detail in outcomes if outcome != "derived"]
    assert not failures, f"racing processes failed: {failures}"
    keys = {detail for _, detail in outcomes}
    assert len(keys) == 1, f"{len(keys)} different keys derived by processes generating together: the first key published must be the only one used"
    key_file = data_dir / INSTANCE_KEY_FILE
    _assert_generated(key_file, bytes.fromhex(next(iter(keys))), purpose="race.v1")
    assert derive_key("race.v1").hex() in keys, "this process must derive the key the racing processes derived"
    assert [racer.exitcode for racer in racers] == [0] * RACE_PROCESSES, f"every racing process must exit cleanly: {[racer.exitcode for racer in racers]}"
    print_success(f"{RACE_PROCESSES} processes, one key file, one derived key")


# =============================================================================
# (e) A key file is never replaced
# =============================================================================


@pytest.mark.parametrize(("content", "problem"), UNUSABLE_KEY_FILES)
def test_an_unusable_key_file_is_an_error_and_is_never_replaced(data_dir, waits, content, problem):
    """(e) A new key could not read what the old one encrypted: the file stays exactly as it is, use after use."""
    key_file = _write_key_file(data_dir, content)

    for attempt in (1, 2):
        with pytest.raises(InstanceKeyError) as raised:
            derive_key(PURPOSE)
        message = str(raised.value)
        assert str(key_file) in message and problem in message, f"attempt {attempt}: the error must name {key_file} and the problem ({problem!r}): {message[:300]!r}"
        assert RESTORE_HINT in message, f"attempt {attempt}: the error must say to {RESTORE_HINT}, since a new key could not read the old data: {message[:300]!r}"
        assert key_file.read_bytes() == content, f"attempt {attempt}: an unusable key file was rewritten: it must never be replaced"
        assert _entries(key_file.parent) == ["instance.key"], f"attempt {attempt}: nothing may be added next to the key file: {_entries(key_file.parent)}"
    print_success(f"{problem}: refused twice, the file unchanged")


@pytest.mark.parametrize("written_so_far", [pytest.param(0, id="empty"), pytest.param(10, id="partly-written")])
def test_a_key_file_still_being_written_is_waited_for_and_never_rewritten(data_dir, waits, monkeypatch, written_so_far):
    """(e) Without hard links the file appears before its content: the reader waits, then takes the key as written."""
    complete = (WINNER_KEY + "\n").encode("ascii")
    key_file = _write_key_file(data_dir, complete[:written_so_far])
    inode = key_file.stat().st_ino

    def the_writer_finishes_during_the_first_wait(seconds: float) -> None:
        waits.append(seconds)
        if len(waits) == 1:
            with key_file.open("ab") as handle:
                handle.write(complete[written_so_far:])

    monkeypatch.setattr(instance_key, "time", SimpleNamespace(sleep=the_writer_finishes_during_the_first_wait))

    derived = derive_key(PURPOSE)

    assert derived == _derived_from(WINNER_KEY, PURPOSE), "the reader must use the key the writer finished writing"
    assert len(waits) == 1, f"the reader must read, wait once for the writer, then read the complete key: {len(waits)} waits"
    assert (key_file.read_bytes(), key_file.stat().st_ino) == (complete, inode), "the reader must never rewrite or replace the key file it waits for"
    print_success(f"{written_so_far} of {len(complete)} bytes at the first read: waited once, the writer's key used")


def test_a_key_file_that_stays_unusable_is_given_up_after_half_a_second(data_dir, waits, monkeypatch):
    """(e) The wait is bounded: a file that never becomes usable is read again a few times, then reported."""
    key_file = _write_key_file(data_dir, b"")
    reads: list[Path] = []
    read_secret_file = instance_key.read_secret_file

    def counted_read(path: Path, label: str) -> str:
        reads.append(path)
        return read_secret_file(path, label)

    monkeypatch.setattr(instance_key, "read_secret_file", counted_read)

    with pytest.raises(InstanceKeyError, match=RESTORE_HINT):
        derive_key(PURPOSE)

    assert len(reads) > 1 and len(reads) == len(waits) + 1, f"an unusable key file must be read again after each wait: {len(reads)} reads, {len(waits)} waits"
    assert 0 < sum(waits) <= MAX_SETTLE_SECONDS, f"the reader must wait for the writer, {MAX_SETTLE_SECONDS} s at most in all, not {sum(waits):.3f} s"
    assert key_file.read_bytes() == b"", "the unusable key file must be left as it is"
    print_success(f"{len(reads)} reads over {sum(waits):.2f} s of waits, then the error")


@needs_permission_checks
@pytest.mark.parametrize("read_only", ["data directory", "secrets folder"])
def test_a_key_file_that_cannot_be_created_is_an_error(data_dir, read_only):
    """(e) A data directory where the key cannot be written: InstanceKeyError naming the path, nothing left behind."""
    target = data_dir if read_only == "data directory" else data_dir / INSTANCE_KEY_FILE.parent
    target.mkdir(parents=True)
    target.chmod(0o500)
    try:
        with pytest.raises(InstanceKeyError) as raised:
            derive_key(PURPOSE)
        left = sorted(path.relative_to(data_dir).as_posix() for path in data_dir.rglob("*"))
    finally:
        target.chmod(0o700)

    message = str(raised.value)
    assert message.startswith(f"{data_dir / INSTANCE_KEY_FILE}: the instance key cannot be generated ("), f"the error must name the key file and say it cannot be generated: {message!r}"
    assert left == ([] if read_only == "data directory" else ["secrets"]), f"a failed generation must leave nothing behind: {left}"
    print_success(f"read-only {read_only}: {message}")


@needs_permission_checks
@pytest.mark.parametrize("folder_mode", [pytest.param(0o000, id="no-access"), pytest.param(0o600, id="readable-not-searchable")])
def test_a_key_file_that_cannot_be_reached_is_an_error_and_is_never_replaced(production_data_dir, waits, folder_mode):
    """(e)(f) A ``secrets`` folder the server cannot search: the key may be in it, so it is neither generated again nor called missing."""
    print_section(f"Instance key: a secrets folder of mode {folder_mode:04o}")
    derive_key(PURPOSE)
    key_file = production_data_dir / INSTANCE_KEY_FILE
    before = key_file.read_bytes(), key_file.stat().st_ino
    expected = f"{key_file}: the instance key cannot be reached ({os.strerror(errno.EACCES)})"

    key_file.parent.chmod(folder_mode)
    try:
        status = instance_key_status()
        with pytest.raises(InstanceKeyError) as raised:
            derive_key(PURPOSE)
    finally:
        key_file.parent.chmod(0o700)

    assert status == InstanceKeyStatus("generated", problem=expected, path=key_file), f"the status must report the key file as unreachable, without raising: {status}"
    assert str(raised.value) == expected, f"derive_key must say the key cannot be reached:\n  expected {expected!r}\n  got      {raised.value!r}"
    assert (key_file.read_bytes(), key_file.stat().st_ino) == before, "the key file behind a folder that could not be searched was replaced"
    assert _entries(key_file.parent) == ["instance.key"], f"nothing may be added next to the key file: {_entries(key_file.parent)}"
    print_success(expected)


@needs_posix_paths
def test_a_secrets_path_that_is_not_a_folder_is_an_error(production_data_dir, waits):
    """(e)(f) ``secrets`` is a file: the key cannot be reached, nothing is created next to it or in its place."""
    production_data_dir.mkdir()
    secrets_file = production_data_dir / INSTANCE_KEY_FILE.parent
    secrets_file.write_bytes(b"a file where the key folder should be\n")
    secrets_file.chmod(0o600)
    key_file = production_data_dir / INSTANCE_KEY_FILE
    expected = f"{key_file}: the instance key cannot be reached ({os.strerror(errno.ENOTDIR)})"

    status = instance_key_status()
    with pytest.raises(InstanceKeyError) as raised:
        derive_key(PURPOSE)

    assert (status.source, status.problem, status.path) == ("generated", expected, key_file), f"the status must report the key file as unreachable, without raising: {status}"
    assert str(raised.value) == expected, f"derive_key must say the key cannot be reached:\n  expected {expected!r}\n  got      {raised.value!r}"
    assert secrets_file.read_bytes() == b"a file where the key folder should be\n", "the file in the way of the key folder was changed"
    assert _entries(production_data_dir) == ["secrets"], f"nothing may be created in the data directory: {_entries(production_data_dir)}"
    print_success(expected)


@needs_symlinks
def test_a_dangling_key_link_is_an_error_and_is_never_replaced(production_data_dir, waits):
    """(e)(f) A link to a key that is gone: an error saying so; the link stays, and nothing is written where it points."""
    folder = production_data_dir / INSTANCE_KEY_FILE.parent
    folder.mkdir(mode=0o700, parents=True)
    target = production_data_dir / "restored-elsewhere" / "instance.key"
    key_file = production_data_dir / INSTANCE_KEY_FILE
    key_file.symlink_to(target)
    missing = f"instance key file: {key_file} does not exist"

    status = instance_key_status()
    with pytest.raises(InstanceKeyError) as raised:
        derive_key(PURPOSE)

    assert status == InstanceKeyStatus("generated", problem=missing, path=key_file), f"a dangling link must read as a generated key that does not exist: {status}"
    assert str(raised.value).startswith(missing) and RESTORE_HINT in str(raised.value), f"derive_key must say the key file does not exist and to restore it: {raised.value!r}"
    assert key_file.is_symlink() and os.readlink(key_file) == str(target), "the dangling link was replaced"
    assert not target.parent.exists(), f"something was written where the dangling link points: {target.parent}"
    assert _entries(folder) == ["instance.key"], f"nothing may be added next to the link: {_entries(folder)}"
    print_success(f"{missing}: the link left as it is")


# =============================================================================
# (f) instance_key_status
# =============================================================================


def test_status_before_the_first_use_creates_nothing(data_dir):
    """(f) not_created: the path where the first use will generate the key, and nothing created to find it out."""
    status = instance_key_status()
    assert status == InstanceKeyStatus("not_created", path=data_dir / INSTANCE_KEY_FILE), f"no key yet must read as not_created at the key path: {status}"
    assert not data_dir.exists(), f"instance_key_status must not create anything: {list(data_dir.rglob('*'))}"
    print_success(f"{status}")


def test_status_of_a_generated_key(data_dir):
    """(f) generated: the key file is usable and, as generated, private to its owner."""
    derive_key(PURPOSE)
    status = instance_key_status()
    assert status == InstanceKeyStatus("generated", path=data_dir / INSTANCE_KEY_FILE), f"a freshly generated key must read as generated, with no problem and no loose mode: {status}"
    print_success(f"{status}")


@pytest.mark.parametrize(("content", "problem"), UNUSABLE_KEY_FILES)
def test_status_of_an_unusable_generated_key(data_dir, waits, content, problem):
    """(f) generated with a problem that names the file, never the content, found without waiting; the file left as it is."""
    key_file = _write_key_file(data_dir, content)
    status = instance_key_status()
    assert (status.source, status.path) == ("generated", key_file), f"an existing key file must read as generated at its path: {status}"
    assert status.problem is not None and str(key_file) in status.problem and problem in status.problem, f"the problem must name the file and what is wrong ({problem!r}): {status.problem!r}"
    assert waits == [], f"instance_key_status must answer at once, never wait for a writer: it waited {waits}"
    assert key_file.read_bytes() == content, "instance_key_status must not touch the key file"
    print_success(f"{status.problem[:120]}")


@pytest.mark.parametrize(
    ("variables", "expected_problem"),
    [
        pytest.param({KEY_VARIABLE: KNOWN_KEY}, None, id="variable"),
        pytest.param({KEY_FILE_VARIABLE: "<mounted key>"}, None, id="file"),
        pytest.param({KEY_VARIABLE: "short-key"}, f"{KEY_VARIABLE}: the instance key is 9 characters long, it needs at least {INSTANCE_KEY_MIN_LENGTH}", id="variable-too-short"),
        pytest.param({KEY_FILE_VARIABLE: "<short key>"}, f"{KEY_FILE_VARIABLE} (<short key>): the instance key is 9 characters long, it needs at least {INSTANCE_KEY_MIN_LENGTH}", id="file-too-short"),
        pytest.param({KEY_FILE_VARIABLE: "<missing>"}, f"{KEY_FILE_VARIABLE}: <missing> does not exist", id="file-missing"),
    ],
)
def test_status_of_a_configured_key(data_dir, monkeypatch, tmp_path, variables, expected_problem):
    """(f) configured: no path, no permission check; the problem, if any, names the origin and never the key."""
    mounted, short, missing = tmp_path / "mounted-key", tmp_path / "short-key", tmp_path / "missing-key"
    mounted.write_text(KNOWN_KEY + "\n", encoding="utf-8")
    short.write_text("short-key\n", encoding="utf-8")
    placeholders = {"<mounted key>": str(mounted), "<short key>": str(short), "<missing>": str(missing)}
    for name, value in variables.items():
        monkeypatch.setenv(name, placeholders.get(value, value))
    for placeholder, path in placeholders.items():
        expected_problem = expected_problem.replace(placeholder, path) if expected_problem is not None else None

    status = instance_key_status()

    assert status == InstanceKeyStatus("configured", problem=expected_problem), f"expected configured with problem {expected_problem!r}, got {status}"
    assert not data_dir.exists(), "the status of a configured key must not create anything"
    print_success(f"{status}")


def test_status_of_a_configured_key_ignores_a_broken_generated_one(data_dir, monkeypatch):
    """(f) The configured key is the one in use: a damaged key file left in the data directory is not its problem."""
    _write_key_file(data_dir, b"")
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    status = instance_key_status()
    assert status == InstanceKeyStatus("configured"), f"a configured key must be reported alone, whatever the key file holds: {status}"
    print_success(f"{status}")


@needs_posix_modes
@pytest.mark.parametrize(
    ("folder_mode", "file_mode", "expected"),
    [
        pytest.param(0o755, 0o644, {"directory": "0755", "file": "0644"}, id="both-open"),
        pytest.param(0o750, 0o600, {"directory": "0750"}, id="folder-open-to-group"),
        pytest.param(0o700, 0o640, {"file": "0640"}, id="file-open-to-group"),
        pytest.param(0o700, 0o604, {"file": "0604"}, id="file-open-to-others"),
        pytest.param(0o700, 0o600, {}, id="private"),
        pytest.param(0o700, 0o400, {}, id="read-only-for-the-owner-is-private"),
    ],
)
def test_status_reports_the_permissions_open_to_group_or_others(data_dir, folder_mode, file_mode, expected):
    """(f) loose_modes: the octal mode of the folder and of the file whenever group or others have any access."""
    derive_key(PURPOSE)
    key_file = data_dir / INSTANCE_KEY_FILE
    key_file.chmod(file_mode)
    key_file.parent.chmod(folder_mode)
    try:
        status = instance_key_status()
    finally:
        key_file.parent.chmod(0o700)
        key_file.chmod(0o600)
    assert (status.source, status.problem, status.loose_modes) == ("generated", None, expected), f"folder {folder_mode:04o} and file {file_mode:04o} must report {expected}: {status}"
    print_success(f"folder {folder_mode:04o}, file {file_mode:04o}: {status.loose_modes}")


# =============================================================================
# (g) derive_key_from
# =============================================================================

#: The key the known answers below were computed with: by today's ``derive_key``, this key configured.
DERIVE_FROM_KEY = "kat-key-for-derive-key-from-0123456789abcdef"
DERIVE_FROM_ANSWERS = {
    ("plugins.settings.v1", 32): "3d849b483f1ea4469d7f3262ce1d39d1c0b872379bdad562a78b61dc6a9f2e44",
    ("test.vector:v1", 64): "52d0832aa8a14ca82040fbfdc1522a07b80884079a08a54fad1764cc22a58b17b24b183e20293e3213bca6fc3948b248c3df1d24987726075d05a9c3cb59eaa7",
    ("a", 1): "45",
}
#: The purposes and lengths over which ``derive_key_from`` given the instance key must agree with ``derive_key``.
EQUIVALENCE_REQUESTS = [("plugins.settings.v1", 32), ("plugins.settings.fingerprint.v1", 32), ("backup.v1", 32), ("plugins.settings.v1", 16), ("test.vector:v1", 64), ("a", 1), ("z" * 128, 255 * 32)]
#: Starts every key of the error tests: no part of it may appear in a message.
KEY_CANARY = "Zq7canary"

#: Requests ``derive_key`` refuses, whatever the key: the same ones must be refused by ``derive_key_from`` first.
INVALID_REQUESTS = [
    pytest.param("Bad Purpose", 32, id="purpose-uppercase-and-space"),
    pytest.param("", 32, id="purpose-empty"),
    pytest.param("a" * 129, 32, id="purpose-129-characters"),
    pytest.param("plugins.v1\n", 32, id="purpose-trailing-newline"),
    pytest.param(PURPOSE, 0, id="length-zero"),
    pytest.param(PURPOSE, 255 * 32 + 1, id="length-8161"),
    pytest.param(PURPOSE, 16.0, id="length-float"),
    pytest.param(PURPOSE, None, id="length-none"),
]
#: A usable key, and keys each refused for a reason of its own: none may hide that the request is invalid.
KEYS_OF_EVERY_KIND = [
    pytest.param(KNOWN_KEY, id="usable-key"),
    pytest.param("short", id="key-too-short"),
    pytest.param(KNOWN_KEY.encode("utf-8"), id="key-bytes"),
    pytest.param(None, id="key-none"),
]


def _derive_key_from():
    """``instance_key.derive_key_from``, looked up when a test runs: until it exists, its tests fail here, and only they."""
    function = getattr(instance_key, "derive_key_from", None)
    assert function is not None, "derive_key_from is missing from backend/app/services/platform/instance_key.py (H-14)"
    return function


@pytest.mark.parametrize(("purpose", "length", "expected"), [(purpose, length, answer) for (purpose, length), answer in DERIVE_FROM_ANSWERS.items()], ids=[f"{purpose}-{length}" for purpose, length in DERIVE_FROM_ANSWERS])
def test_derive_key_from_gives_the_known_answers(data_dir, monkeypatch, purpose, length, expected):
    """(g) Known answers of ``derive_key`` with the key configured: given the same key, ``derive_key_from`` gives them too."""
    monkeypatch.setenv(KEY_VARIABLE, DERIVE_FROM_KEY)
    assert derive_key(purpose, length).hex() == expected, f"barrier: derive_key({purpose!r}, {length}) with the key configured no longer gives the pinned answer, so the answer itself is in question"
    derive_key_from = _derive_key_from()

    derived = derive_key_from(DERIVE_FROM_KEY, purpose, length).hex()

    assert derived == expected, f"derive_key_from(<key>, {purpose!r}, {length}) gives {derived}, derive_key with that key configured gives {expected}"
    print_success(f"{purpose}, {length} bytes: {derived}")


@pytest.mark.parametrize("source", ["configured", "generated"])
def test_derive_key_from_given_the_instance_key_is_derive_key(data_dir, monkeypatch, source):
    """(g) Given the instance key itself, configured or generated, ``derive_key_from`` gives what ``derive_key`` gives."""
    print_section(f"derive_key_from: the derivation of derive_key, {source} key")
    if source == "configured":
        monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
        key = KNOWN_KEY
    else:
        derive_key(PURPOSE)
        assert instance_key_path().is_file(), f"barrier: the first use of derive_key must have generated {instance_key_path()}"
        # Read as the module reads the generated key: read_secret_file drops a byte order mark and the trailing line breaks
        key = read_secret_file(instance_key_path(), "instance key file")
    derive_key_from = _derive_key_from()

    differing = [(purpose[:24], length) for purpose, length in EQUIVALENCE_REQUESTS if derive_key_from(key, purpose, length) != derive_key(purpose, length)]

    assert not differing, f"derive_key_from(<instance key>, purpose, length) differs from derive_key(purpose, length) for {differing}"
    print_success(f"{len(EQUIVALENCE_REQUESTS)} purposes and lengths, the same derived keys")


def test_derive_key_from_uses_the_key_given_never_the_instances(data_dir, monkeypatch):
    """(g) Another instance key configured: ``derive_key_from(K, purpose)`` is what K gives, not what the instance gives."""
    monkeypatch.setenv(KEY_VARIABLE, KNOWN_KEY)
    with_k_configured = derive_key(PURPOSE)
    monkeypatch.setenv(KEY_VARIABLE, DERIVE_FROM_KEY)
    of_the_instance = derive_key(PURPOSE)
    assert of_the_instance != with_k_configured, "barrier: two instance keys must give two derived keys"
    derive_key_from = _derive_key_from()

    derived = derive_key_from(KNOWN_KEY, PURPOSE)

    assert derived != of_the_instance, "derive_key_from used the instance's key instead of the key it was given"
    assert derived == with_k_configured, "derive_key_from(K, purpose) must be what derive_key(purpose) gives with K configured"
    assert derived.hex() == KNOWN_ANSWER, "derive_key_from(K, purpose) must default to 32 bytes and give the OpenSSL known answer of K"
    print_success("the key given, not the instance's")


def test_derive_key_from_never_generates_the_key_file(data_dir):
    """(g) No key configured and no key file yet: ``derive_key_from`` derives from its argument and creates nothing."""
    derive_key_from = _derive_key_from()

    derived = derive_key_from(KNOWN_KEY, PURPOSE)

    assert derived.hex() == KNOWN_ANSWER, "derive_key_from(K, purpose) must be the derivation of K"
    assert not instance_key_path().exists(), f"derive_key_from generated {instance_key_path()}: it must never look for the instance key"
    assert not data_dir.exists(), f"derive_key_from created something in the data directory: {list(data_dir.rglob('*'))}"
    print_success("derived, nothing generated")


def test_derive_key_from_never_reads_the_environment_or_the_data_directory(data_dir, monkeypatch):
    """(g) Pure: neither the configured key, nor its origin, nor the data directory, nor a key file is read."""

    def tripwire(*_args, **_kwargs):
        raise AssertionError("derive_key_from looked for the instance key: it must use only the key it is given")

    for name in ("configured_instance_key", "configured_instance_key_origin", "get_data_dir", "read_secret_file"):
        monkeypatch.setattr(instance_key, name, tripwire)
    derive_key_from = _derive_key_from()

    derived = derive_key_from(KNOWN_KEY, PURPOSE)

    assert derived.hex() == KNOWN_ANSWER, "derive_key_from(K, purpose) must be the derivation of K"
    print_success("no source of the instance key read")


@pytest.mark.parametrize("broken", ["key-file-variable-missing", "configured-key-too-short", "generated-key-file-empty"])
def test_a_broken_instance_key_does_not_affect_derive_key_from(data_dir, monkeypatch, tmp_path, waits, broken):
    """(g) The instance's own key unusable: ``derive_key_from`` derives all the same and leaves every source as it was."""
    key_file = data_dir / INSTANCE_KEY_FILE
    if broken == "key-file-variable-missing":
        monkeypatch.setenv(KEY_FILE_VARIABLE, str(tmp_path / "missing-key"))
    elif broken == "configured-key-too-short":
        monkeypatch.setenv(KEY_VARIABLE, "short-key")
    else:
        _write_key_file(data_dir, b"")
    with pytest.raises(InstanceKeyError):
        derive_key(PURPOSE)  # barrier: the instance key is really unusable
    waits_before = len(waits)
    derive_key_from = _derive_key_from()

    derived = derive_key_from(KNOWN_KEY, PURPOSE)

    assert derived.hex() == KNOWN_ANSWER, f"{broken}: derive_key_from(K, purpose) must be the derivation of K"
    assert len(waits) == waits_before, f"{broken}: derive_key_from waited for a key file: {waits[waits_before:]}"
    if broken == "generated-key-file-empty":
        assert key_file.read_bytes() == b"", "derive_key_from touched the damaged key file"
    else:
        assert not data_dir.exists(), f"{broken}: derive_key_from created something in the data directory: {list(data_dir.rglob('*'))}"
    print_success(f"{broken}: derived from the key given, nothing touched")


@pytest.mark.parametrize("key", KEYS_OF_EVERY_KIND)
@pytest.mark.parametrize(("purpose", "length"), INVALID_REQUESTS)
def test_derive_key_from_refuses_an_invalid_request_before_looking_at_the_key(data_dir, purpose, length, key):
    """(g) An invalid purpose or length is a ``ValueError`` with the message of ``derive_key``, whatever the key."""
    with pytest.raises(ValueError) as refused_by_derive_key:
        derive_key(purpose, length)  # barrier: derive_key refuses this request, and says how
    derive_key_from = _derive_key_from()

    with pytest.raises(ValueError) as raised:
        derive_key_from(key, purpose, length)

    assert str(raised.value) == str(refused_by_derive_key.value), f"derive_key_from must refuse the request as derive_key does:\n  expected {str(refused_by_derive_key.value)!r}\n  got      {str(raised.value)!r}"
    assert not data_dir.exists(), "an invalid request must create nothing"
    print_success(f"{str(purpose)[:24]!r}, {length!r}: {str(raised.value)[:60]}")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param(KNOWN_KEY.encode("utf-8"), id="bytes"),
        pytest.param(b"short", id="short-bytes"),
        pytest.param(None, id="none"),
        pytest.param(12345678901234567890123456789012345, id="int-of-35-digits"),
    ],
)
def test_derive_key_from_refuses_a_key_that_is_not_text(data_dir, key):
    """(g) The key is text, as the instance key is: bytes, ``None`` or a number is a ``TypeError``, whatever its length."""
    derive_key_from = _derive_key_from()

    with pytest.raises(TypeError) as raised:
        derive_key_from(key, PURPOSE)

    assert KNOWN_KEY not in str(raised.value), f"the error shows the key: {raised.value!r}"
    assert not data_dir.exists(), "a refused key must create nothing"
    print_success(f"{type(key).__name__}: {raised.value}")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param(KEY_CANARY, id="9-characters"),
        pytest.param((KEY_CANARY + "x" * INSTANCE_KEY_MIN_LENGTH)[: INSTANCE_KEY_MIN_LENGTH - 1], id="31-characters"),
        pytest.param(KEY_CANARY + "é" * (INSTANCE_KEY_MIN_LENGTH - 1 - len(KEY_CANARY)), id="31-characters-53-bytes"),
    ],
)
def test_derive_key_from_refuses_a_key_shorter_than_32_characters_without_showing_it(data_dir, key):
    """(g) Shorter than 32 characters, however many bytes: an ``InstanceKeyError`` whose message holds no part of the key."""
    assert len(key) < INSTANCE_KEY_MIN_LENGTH, f"precondition: {len(key)} characters"
    derive_key_from = _derive_key_from()

    with pytest.raises(InstanceKeyError) as raised:
        derive_key_from(key, PURPOSE)

    message = str(raised.value)
    assert key not in message and KEY_CANARY not in message, f"the error shows the key: {message!r}"
    assert not data_dir.exists(), "a refused key must create nothing"
    print_success(f"{len(key)} characters refused: {message}")


@pytest.mark.parametrize(
    "key",
    [
        pytest.param((KEY_CANARY + "x" * INSTANCE_KEY_MIN_LENGTH)[:INSTANCE_KEY_MIN_LENGTH], id="32-characters"),
        pytest.param("é" * INSTANCE_KEY_MIN_LENGTH, id="32-characters-64-bytes"),
    ],
)
def test_derive_key_from_accepts_a_key_of_32_characters(data_dir, monkeypatch, key):
    """(g) 32 characters is enough, as for a configured key; the key's UTF-8 bytes are the input of the derivation."""
    monkeypatch.setenv(KEY_VARIABLE, key)
    configured = derive_key(PURPOSE)
    derive_key_from = _derive_key_from()

    derived = derive_key_from(key, PURPOSE)

    assert derived == configured, "a key of 32 characters must give what derive_key gives with it configured"
    assert derived == _derived_from(key, PURPOSE), "the derivation must be HKDF-SHA256 of the key's UTF-8 bytes"
    print_success(f"{len(key)} characters, {len(key.encode('utf-8'))} bytes: accepted")


def test_two_keys_give_two_derived_keys(data_dir):
    """(g) Another key, even by one character, gives another derived key for the same purpose and length."""
    derive_key_from = _derive_key_from()
    keys = [KNOWN_KEY, KNOWN_KEY[:-1] + "8", DERIVE_FROM_KEY]
    requests = [(PURPOSE, 32), ("backup.v1", 16), ("test.vector:v1", 64)]

    collisions = [(purpose, length) for purpose, length in requests if len({derive_key_from(key, purpose, length) for key in keys}) != len(keys)]

    assert not collisions, f"two keys gave the same derived key for {collisions}"
    print_success(f"{len(keys)} keys, {len(requests)} requests: all different")
