"""Write the common test vectors of the sealed nightly backup (contract L3, §9.1), once.

The contract (``LibreFolio_prj/BACKUP-contratto-L3.md``, agreed on 2026-10-22 between the product and the cloud
coordinator) fixes a ``.tar`` of three members, in this order: ``manifest.json`` (clear), ``password.age`` (the random
password of the backup, encrypted with age for the instance's recipients) and ``backup.lfbk`` (the version-1 envelope
that password opens). This script writes the files both sides test against, beside it, with ``vectors.json`` as their
index. It uses ``pyrage``, the envelope's ``encrypt_file`` and ``tarfile`` only, never the product's sealed backup: the
product must rebuild the same ``.tar`` bytes from the same members, which is what the vectors prove.

age encrypts with fresh randomness, so ``password.age`` is never reproducible: the files are written once and kept. The
script refuses to write over them; ``--force`` writes a new set, which the cloud coordinator must copy again.

Every key here is a TEST ONLY key, published with the repository: never use one for a real backup.

    PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python backend/test_scripts/fixtures/backup_l3/generate_vectors.py
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import sys
import tarfile
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pyrage
from pyrage import x25519

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.app.services.platform.instance_backup.envelope import HEADER_SIZE, encrypt_file, read_header  # noqa: E402

HERE = Path(__file__).resolve().parent
TEST_ONLY = "TEST ONLY - LibreFolio L3 sealed backup vectors - never use for real backups"
#: The moment of the good case, as the contract's §9.1 writes it.
CREATED_AT = datetime(2026, 10, 23, 3, 0, 12, tzinfo=UTC)
TAR_NAME = "librefolio-backup-20261023-030012.tar"
MEMBERS = ("manifest.json", "password.age", "backup.lfbk")
#: Fixed so that ``backup.lfbk`` is reproducible from the password (``encrypt_file``'s parameters for tests).
SALT = bytes.fromhex("4c46424b2d4c332d746573742d73616c")
NONCE_PREFIX = bytes.fromhex("4c332d74657374")
#: The cloud coordinator's derivation vector (contract §9.3), checked by the product with pyrage.
CLOUD_DERIVATION = [
    {"instance": 42, "version": 1, "private_hex": "2b024accd96c2edc8f1990c9f7967326537529ffa4a6c5b622aeb0d2295dbc23", "identity": "AGE-SECRET-KEY-19VPY4NXEDSHDERCEJRYL09NNYEFH220L5JNVTD3Z46CDY22AHS3SKVW4RR", "recipient": "age158ex3dmayyml4rx9md6pzehzlc96zlh8w7zn4vd0t6ya8dmn4egqn87h8q"},
    {"instance": 42, "version": 2, "private_hex": "da2bf4d45d78406574b751a0db1c5d62425c4fe7ab3bb5f1996bb1c86b1c94f2", "identity": "AGE-SECRET-KEY-1MG4LF4ZA0PQX2A9H2XSDK8ZAVFP9CNL84VAMTUVEDWCUS6CUJNEQEDQDFZ", "recipient": "age1sg09nv32ud36umafrg587hqx4mfnldqe8njnx0xty9luv9f6w36qyh9xcx"},
    {"instance": 43, "version": 1, "private_hex": "180f86f37e409203f99249d7a7d45fab0d1473878c617bbd422f7720a31dad91", "identity": "AGE-SECRET-KEY-1RQ8CDUM7GZFQ87VJF8T604ZL4VX3GUU833SHH02Z9AMJPGCA4KGSSHHW6A", "recipient": "age1q8daau6vzt306qx6034e2wxxwxfn8qucjgqynuw9v6gkgn6pr5fscq0jf0"},
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def password_of(label: str) -> str:
    """A 43-character base64url password, fixed by ``label``: the form of the contract's §3.3."""
    return base64.urlsafe_b64encode(hashlib.sha256(f"{TEST_ONLY} / {label}".encode()).digest()).rstrip(b"=").decode()


def identity_file(identity: x25519.Identity, created: str) -> str:
    """The text of an ``age-keygen`` key file, which ``age -d -i`` and pyrage read."""
    return f"# {TEST_ONLY}\n# created: {created}\n# public key: {identity.to_public()}\n{identity}\n"


def known_zip() -> bytes:
    """A small zip with fixed entries and dates: what the envelope of the vectors holds."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in (("hello.txt", f"{TEST_ONLY}\n"), ("data/numbers.csv", "a,b\n1,2\n")):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 3, 0, 12))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, text)
    return out.getvalue()


def envelope(clear: bytes, password: str) -> bytes:
    """The version-1 envelope of ``clear`` with ``password``, its salt and nonce prefix fixed."""
    with tempfile.TemporaryDirectory() as folder:
        src, dst = Path(folder) / "clear.zip", Path(folder) / "backup.lfbk"
        src.write_bytes(clear)
        encrypt_file(src, dst, password, salt=SALT, nonce_prefix=NONCE_PREFIX)
        return dst.read_bytes()


def manifest(lfbk: bytes, recipients: list[str]) -> bytes:
    """``manifest.json`` as the contract's §3.2 writes it: sorted keys, no spaces, no final line break."""
    document = {
        "created_at": CREATED_AT.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db_revision": "test-only-revision",
        "format": "lfbk-tar",
        "lfbk_sha256": sha256(lfbk),
        "lfbk_size": len(lfbk),
        "librefolio_version": "1.3.0-test",
        "password_member": "password.age",
        "recipients": recipients,
        "version": 1,
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def tar_bytes(members: list[tuple[str, bytes]], *, link: str | None = None) -> bytes:
    """A POSIX ustar archive of ``members``, with the fields of the contract's §3.4. ``link``: that member is written as
    a symbolic link to ``backup.lfbk`` instead of a file (a negative vector)."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.mode, info.uid, info.gid, info.uname, info.gname = 0o600, 0, 0, "", ""
            info.mtime = int(CREATED_AT.timestamp())
            if name == link:
                info.type, info.linkname, info.size = tarfile.SYMTYPE, "backup.lfbk", 0
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return out.getvalue()


def sealed(lfbk: bytes, password: str, recipients: list[x25519.Recipient]) -> tuple[bytes, bytes]:
    """``password.age`` for ``recipients``, and the manifest naming them."""
    return pyrage.encrypt(password.encode("ascii"), recipients), manifest(lfbk, [str(r) for r in recipients])


#: The end of a tar: two zero blocks.
_END = bytes(1024)


def _members_end(data: bytes) -> int:
    """Where the members of a tar written by ``tar_bytes`` end: the offset of its first zero block."""
    position = 0
    while data[position : position + 512] != bytes(512):
        size = int(data[position + 124 : position + 136].split(b"\0", 1)[0].strip() or b"0", 8)
        position += 512 + -(-size // 512) * 512
    return position


def extended_cases() -> list[tuple[str, bytes, str, str]]:
    """The cases added after the first set (security review of 22/10, finding 2), built from the good case's bytes, so
    that no file of the first set changes: a member hidden after a single zero block, and bytes after the end."""
    good = (HERE / TAR_NAME).read_bytes()
    end = _members_end(good)
    hidden = io.BytesIO()
    with tarfile.open(fileobj=hidden, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        info = tarfile.TarInfo("evil.sh")
        payload = b"#!/bin/sh\necho hidden after one zero block\n"
        info.size, info.mode, info.mtime = len(payload), 0o600, int(CREATED_AT.timestamp())
        tar.addfile(info, io.BytesIO(payload))
    member = hidden.getvalue()[: 512 + -(-len(payload) // 512) * 512]
    with_hidden = good[:end] + bytes(512) + member + _END
    with_hidden += bytes(-len(with_hidden) % 10240)
    return [
        ("neg-hidden-member.tar", with_hidden, "sealed_tar_invalid", "a fourth member after a single zero block: tar -i would extract it"),
        ("neg-trailing-garbage.tar", good + b"\xff" * 100, "sealed_tar_invalid", "100 bytes that are not zeros after the end of the archive"),
    ]


def extend() -> int:
    """Add the cases of ``extended_cases`` that ``vectors.json`` lacks; every existing file stays as it is."""
    index = json.loads((HERE / "vectors.json").read_text())
    known = {case["file"] for case in index["cases"]}
    added = 0
    for name, data, expect, note in extended_cases():
        if name in known:
            continue
        (HERE / name).write_bytes(data)
        index["cases"].append({"file": name, "expect": expect, "note": note, "tar_sha256": sha256(data), "tar_size": len(data), "identities": ["test-identity-1.txt"]})
        added += 1
    (HERE / "vectors.json").write_text(json.dumps(index, indent=2, sort_keys=False) + "\n")
    print(f"✅ {added} cases added to {HERE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="write a new set over the old one (the cloud must copy it again)")
    parser.add_argument("--extend", action="store_true", help="add the cases written after the first set, keeping every existing file")
    args = parser.parse_args()
    if args.extend:
        return extend()
    if (HERE / "vectors.json").exists() and not args.force:
        print(f"❌ {HERE / 'vectors.json'} exists: the vectors are written once (age is not reproducible); --force writes a new set")
        return 1

    created = CREATED_AT.isoformat().replace("+00:00", "Z")
    first, second, stranger = x25519.Identity.generate(), x25519.Identity.generate(), x25519.Identity.generate()
    (HERE / "test-identity-1.txt").write_text(identity_file(first, created))
    (HERE / "test-identity-2.txt").write_text(identity_file(second, created))

    clear = known_zip()
    password = password_of("good")
    lfbk = envelope(clear, password)
    with tempfile.TemporaryDirectory() as folder:
        probe = Path(folder) / "probe.lfbk"
        probe.write_bytes(lfbk)
        check = read_header(probe).check.hex()
    cases: list[dict] = []

    def write(name: str, members: list[tuple[str, bytes]], expect: str, note: str, *, link: str | None = None, **extra) -> bytes:
        data = tar_bytes(members, link=link)
        (HERE / name).write_bytes(data)
        cases.append({"file": name, "expect": expect, "note": note, "tar_sha256": sha256(data), "tar_size": len(data), **extra})
        return data

    age_first, manifest_first = sealed(lfbk, password, [first.to_public()])
    good = [("manifest.json", manifest_first), ("password.age", age_first), ("backup.lfbk", lfbk)]
    write(
        TAR_NAME,
        good,
        "ok",
        "the good case: one recipient (identity 1)",
        identities=["test-identity-1.txt"],
        password=password,
        manifest=json.loads(manifest_first),
        lfbk_sha256=sha256(lfbk),
        lfbk_size=len(lfbk),
        lfbk_header_hex=lfbk[:HEADER_SIZE].hex(),
        lfbk_check_hex=check,
        zip_sha256=sha256(clear),
        mtime=int(CREATED_AT.timestamp()),
    )
    age_both, manifest_both = sealed(lfbk, password, [first.to_public(), second.to_public()])
    write("rotation-two-recipients.tar", [("manifest.json", manifest_both), ("password.age", age_both), ("backup.lfbk", lfbk)], "ok", "a rotation: the password opens with either identity", identities=["test-identity-1.txt", "test-identity-2.txt"], password=password)
    age_stranger, manifest_stranger = sealed(lfbk, password, [stranger.to_public()])
    write("neg-other-recipient.tar", [("manifest.json", manifest_stranger), ("password.age", age_stranger), ("backup.lfbk", lfbk)], "sealed_no_identity", "the password is for a key that is not kept: neither test identity opens it", identities=["test-identity-1.txt", "test-identity-2.txt"])
    age_other, manifest_other = sealed(lfbk, password_of("other"), [first.to_public()])
    write("neg-wrong-password.tar", [("manifest.json", manifest_other), ("password.age", age_other), ("backup.lfbk", lfbk)], "wrong_password", "password.age opens, but its password does not open backup.lfbk (the check differs)", identities=["test-identity-1.txt"], password=password_of("other"))
    bad_manifest = json.loads(manifest_first)
    bad_manifest["lfbk_sha256"] = "0" * 64
    write("neg-manifest-mismatch.tar", [("manifest.json", json.dumps(bad_manifest, sort_keys=True, separators=(",", ":")).encode()), ("password.age", age_first), ("backup.lfbk", lfbk)], "sealed_manifest_invalid", "lfbk_sha256 of the manifest is not the member's", identities=["test-identity-1.txt"])
    write("neg-extra-member.tar", [*good, ("notes.txt", b"one member too many\n")], "sealed_tar_invalid", "four members", identities=["test-identity-1.txt"])
    write("neg-bad-order.tar", [good[2], good[0], good[1]], "sealed_tar_invalid", "backup.lfbk first", identities=["test-identity-1.txt"])
    write("neg-traversal.tar", [good[0], ("../password.age", age_first), good[2]], "sealed_tar_invalid", "a member named with a path", identities=["test-identity-1.txt"])
    write("neg-symlink.tar", good, "sealed_tar_invalid", "password.age is a symbolic link", identities=["test-identity-1.txt"], link="password.age")
    tampered = bytearray(lfbk)
    tampered[HEADER_SIZE + 5] ^= 0x01
    tampered_lfbk = bytes(tampered)
    write(
        "neg-tampered-lfbk.tar",
        [("manifest.json", manifest(tampered_lfbk, [str(first.to_public())])), ("password.age", age_first), ("backup.lfbk", tampered_lfbk)],
        "envelope_damaged",
        "one byte of the first chunk changed; the manifest matches it, so the tar reads and the password checks, and the decryption fails",
        identities=["test-identity-1.txt"],
        password=password,
    )

    index = {
        "comment": f"{TEST_ONLY}. Contract L3 §9: written once by generate_vectors.py; files beside this index.",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pyrage": "1.4.0",
        "members": list(MEMBERS),
        "recipients": {"test-identity-1.txt": str(first.to_public()), "test-identity-2.txt": str(second.to_public())},
        "cases": cases,
        "cloud_derivation": CLOUD_DERIVATION,
    }
    (HERE / "vectors.json").write_text(json.dumps(index, indent=2, sort_keys=False) + "\n")
    print(f"✅ {len(cases)} cases written to {HERE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
