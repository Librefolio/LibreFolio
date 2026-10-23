"""
The sealed backup on the command line (workstream B, lot L3-2, interface §6; contract L3 §3, §8, §9): ``dev.py backup
keygen``, ``create --recipient`` / ``--sealed``, and ``inspect``, ``decrypt``, ``restore --dry-run`` of a sealed
``.tar`` with ``--identity-file``. Selector: ``utils backup-cli-sealed``.

Written before the code (red until lot L3-2 lands): ``keygen``, ``--recipient``, ``--sealed`` and ``--identity-file`` do
not exist yet, so argparse refuses them and each test fails on its own with that message. The messages are not final:
the tests pin exit codes, what is on disk, and the stable codes on a ❌ line (``❌ <message> (<code>)``).

(a) ``keygen --identity-file F``: exit 0, F written 0600 in the format of ``age-keygen`` (``# created: …Z``,
    ``# public key: age1…``, one ``AGE-SECRET-KEY-1…`` line), readable by ``pyrage`` (a message encrypted to the
    printed recipient opens with it); the ``age1…`` recipient printed on a line of its own, the private key on no
    stream. An existing F: exit 1, a ❌ line saying it exists, F untouched.
(b) ``create --recipient age1…`` (once or twice): exit 0, one ``librefolio-backup-YYYYMMDD-HHMMSS.tar`` in
    ``<data dir>/backups/``, 0600, named on a ✅ line; its members ``manifest.json``, ``password.age``, ``backup.lfbk``
    in order; ``password.age`` opens with each identity, its manifest names the recipients in order. No ``.lfbk``, zip
    or partial left anywhere, no job folder. Three recipients: refused (argparse, exit 2, or exit 1 with a ❌ line),
    nothing written. ``--sealed`` reads ``LIBREFOLIO_BACKUP_RECIPIENTS``: set, the same tar; unset, exit 1 with a ❌
    line naming the variable, nothing written. ``--recipient`` with ``--encrypt``, ``--password-file`` or
    ``--password-stdin``: refused the same way, nothing written, nothing asked.
(c) ``decrypt`` of the vectors' good tar with ``test-identity-1.txt`` ``-o out.zip``: exit 0, out.zip the vector's zip
    (its ``zip_sha256``), 0600, alone in its folder; the rotation tar opens with ``test-identity-2.txt``. The vectors'
    zip is not a LibreFolio backup, so ``inspect`` and ``restore --dry-run`` run on a tar ``create --recipient`` made of
    the test's own data directory: ``inspect`` verifies the archive it holds; a dry run on an instance at the head
    reports it restorable, without the instance key, the copy removed and the data directory as it was.
(d) The vectors' negatives, through each of ``inspect``, ``decrypt``, ``restore --dry-run``: ``neg-other-recipient`` →
    ``sealed_no_identity``, ``neg-wrong-password`` → ``wrong_password``, ``neg-bad-order`` → ``sealed_tar_invalid``,
    ``neg-manifest-mismatch`` → ``sealed_manifest_invalid``, ``neg-tampered-lfbk`` → ``envelope_damaged``: exit 1 and
    the code on a ❌ line; nothing at ``-o``; no copy left in ``.restore/stage``. A ``.tar`` without
    ``--identity-file``: exit 1, ``sealed_backup_needs_key``, nothing asked. ``--identity-file`` given with a zip: exit
    1 and a ❌ line.
    After every one of (b), (c), (d): no temporary ``.lfbk`` (nor partial, nor clear zip) left anywhere under the
    test's folder — the data directory, the inputs, the system's temporary folder (moved there).
(e) SEC-5 of the security review of H-62 (finding 11; interface ``B-sec345-interface.md``). ``inspect``, ``decrypt``,
    ``restore --dry-run`` of the vectors' good tar with an identity file its group or others may read (0644, 0640):
    one line starting with ``⚠️`` names the file and its mode in octal (``0644``) and suggests ``chmod 600``; the
    command goes on (its ``🔏`` line; ``decrypt`` exits 0 and writes the vector's zip). A 0600 file: no such line.
    ``keygen``: the key is written to a temporary file in F's folder (0600), through ``os.write``, ``fsync``ed while F
    does not exist yet, then linked or renamed to F; a write or an ``fsync`` that fails (``os.write``, ``os.fsync``
    replaced for the files of F's folder alone): exit 1, a ❌ line, F does not exist, nothing left in the folder, the key
    on no stream; an F that appears while the key is written is never replaced: exit 1, F as it was, nothing beside it.
    An F there before: (a), unchanged. Written RED: no warning is printed, and ``keygen`` writes F itself through a file
    object, neither through ``os.write`` nor with an ``fsync``.

Pure, as ``test_backup_cli_secure.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen
through ``LIBREFOLIO_DATA_DIR`` (production mode, checked); the commands run in this process through the parser
``register_subparser`` builds; ``getpass`` answers as a closed terminal (no prompt waits); Python's temporary folder is
moved under ``tmp_path``. The vectors (``backend/test_scripts/fixtures/backup_l3/``, TEST ONLY keys) are copied into
the test's folder before use, never written. Identities other than the vectors' are made by ``pyrage`` for one test.
``LIBREFOLIO_BACKUP_RECIPIENTS`` is removed before every test and set only by those that say so. The dry run uses the
real database at the head made once for the module by ``alembic upgrade``. POSIX-only (modes).
"""

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import stat
import tarfile
from pathlib import Path
from typing import Any

import pyrage
import pytest
from pyrage import x25519

from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utilities import test_backup_cli_secure as secure
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = pytest.mark.skipif(os.name == "nt", reason="file modes are POSIX only")

# The fixtures of the command line's tests, re-exported: ``app_version`` and ``prompts`` (autouse), the real database at
# the head, the system's temporary folder moved under the test's.
app_version = cli.app_version
head_database = cli.head_database
prompts = secure.prompts
system_temp = secure.system_temp

run = secure.run
Ran = secure.Ran


def accepts(capsys, *argv: str) -> None:
    """Barrier: the arguments of ``dev.py backup <argv>`` are read without an error (nothing runs)."""
    capsys.readouterr()
    try:
        secure.backup_parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"precondition: dev.py backup {' '.join(argv)} must be accepted (lot L3-2's options, interface §6): argparse exit {exc.code}: {capsys.readouterr().err[-cli.TAIL:]}")


VECTORS = Path(__file__).resolve().parents[1] / "fixtures" / "backup_l3"
INDEX = json.loads((VECTORS / "vectors.json").read_text(encoding="utf-8"))
CASES = {case["file"]: case for case in INDEX["cases"]}
GOOD = "librefolio-backup-20261023-030012.tar"
ROTATION = "rotation-two-recipients.tar"
IDENTITY_1 = "test-identity-1.txt"
IDENTITY_2 = "test-identity-2.txt"

RECIPIENTS_VARIABLE = "LIBREFOLIO_BACKUP_RECIPIENTS"
MEMBERS = ["manifest.json", "password.age", "backup.lfbk"]
SEALED_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}\.tar")
RECIPIENT = re.compile(r"age1[0-9a-z]{58}")
ENVELOPE_MAGIC = b"LFBK"
#: What a user keeps in a file a command is told to write.
KEPT = b"a file the user keeps"
#: The negatives of the vectors and the code each must give (interface §4, §6).
NEGATIVES = [
    pytest.param("neg-other-recipient.tar", "sealed_no_identity", id="other-recipient"),
    pytest.param("neg-wrong-password.tar", "wrong_password", id="wrong-password"),
    pytest.param("neg-bad-order.tar", "sealed_tar_invalid", id="bad-order"),
    pytest.param("neg-manifest-mismatch.tar", "sealed_manifest_invalid", id="manifest-mismatch"),
    pytest.param("neg-tampered-lfbk.tar", "envelope_damaged", id="tampered-lfbk"),
]
#: The three commands that read a sealed tar.
READERS = ["inspect", "decrypt", "restore"]


@pytest.fixture(autouse=True)
def no_inherited_recipients(monkeypatch) -> None:
    """``LIBREFOLIO_BACKUP_RECIPIENTS`` a developer's shell or the runner may carry is removed for every test."""
    monkeypatch.delenv(RECIPIENTS_VARIABLE, raising=False)


# =============================================================================
# Inputs, identities, what is on disk
# =============================================================================


def vector(name: str, folder: Path) -> Path:
    """A file of the vectors, copied into ``folder`` (the vectors are never written)."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    shutil.copyfile(VECTORS / name, target)
    return target


def identity_file(folder: Path, identity: x25519.Identity, name: str = "identity.txt") -> Path:
    """An identity file in the format of ``age-keygen``, 0600, outside the data directory."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(f"# created: 2026-10-22T00:00:00Z\n# public key: {identity.to_public()}\n{identity}\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def new_identity() -> tuple[x25519.Identity, str]:
    identity = x25519.Identity.generate()
    return identity, str(identity.to_public())


def leftovers(root: Path) -> list[str]:
    """What a sealed command must never leave under ``root``: an envelope (``*.lfbk``, or a file starting with
    ``LFBK``), a partial (``*.part``), a clear zip it did not write (``*.zip`` or a zip's first bytes)."""
    found = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            head = handle.read(4)
        if path.suffix in (".lfbk", ".part", ".zip") or head in (ENVELOPE_MAGIC, secure.ZIP_MAGIC):
            found.append(path.relative_to(root).as_posix())
    return sorted(found)


def tar_members(path: Path) -> tuple[list[str], dict[str, bytes]]:
    """The member names of a tar, in order, and their bytes, read as streams."""
    with tarfile.open(path, mode="r:") as tar:
        infos = tar.getmembers()
        data = {info.name: tar.extractfile(info).read() for info in infos if info.isreg()}
    return [info.name for info in infos], data


def the_tar_written(root: Path, out: str) -> Path:
    """The one archive ``create`` wrote: a sealed tar in ``<data dir>/backups/``, 0600, named on a ✅ line; no job folder,
    no envelope or clear archive left in the data directory."""
    archives = secure.written_archives(root)
    assert len(archives) == 1 and SEALED_NAME.fullmatch(archives[0].name), f"one archive in backups/, librefolio-backup-YYYYMMDD-HHMMSS.tar: {[path.name for path in archives]}"
    archive = archives[0]
    mode = stat.S_IMODE(archive.stat().st_mode)
    assert mode == 0o600, f"the tar is readable by its owner only (0600), not {oct(mode)}"
    assert [line for line in out.splitlines() if line.startswith("✅") and str(archive) in line], f"a ✅ line names {archive}: {out[-cli.TAIL:]}"
    assert cli.job_folders(root) == [], f"the job's folder is removed: {cli.job_folders(root)}"
    assert leftovers(root) == [], f"no envelope, partial or clear archive left in the data directory: {leftovers(root)}"
    return archive


def refused(capsys, *argv: str) -> Ran:
    """``dev.py backup <argv>`` refused: by argparse (exit 2), or by the command (exit 1 and a ❌ line). An exception
    escaping the command fails the test."""
    capsys.readouterr()
    try:
        args = secure.backup_parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        captured = capsys.readouterr()
        return Ran(exc.code, captured.out, captured.err)
    try:
        code = args.func(args)
    except Exception as exc:
        pytest.fail(f"dev.py backup {' '.join(argv)} raised {type(exc).__name__} ({exc}): a traceback instead of a message")
    captured = capsys.readouterr()
    ran = Ran(code, captured.out, captured.err)
    assert ran.code == 1 and ran.refused, f"dev.py backup {' '.join(argv)}: refused with exit 1 and a ❌ line, not exit {ran.code}: {ran.text[-cli.TAIL:]}"
    return ran


def reader_argv(name: str, archive: Path, out: Path, *extra: str) -> list[str]:
    """``name`` reading ``archive``: ``inspect A``, ``decrypt A -o OUT``, ``restore A --dry-run``."""
    return {"inspect": ["inspect", str(archive)], "decrypt": ["decrypt", str(archive), "-o", str(out)], "restore": ["restore", str(archive), "--dry-run"]}[name] + list(extra)


def created_tar(capsys, root: Path, *recipients: str) -> Path:
    """A sealed tar ``create --recipient`` made of the data directory ``root``: the precondition of (c)."""
    flags = [item for recipient in recipients for item in ("--recipient", recipient)]
    ran = run(capsys, "create", *flags)
    assert ran.code == 0, f"precondition: create {' '.join(flags)} exits 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    return the_tar_written(root, ran.out)


# =============================================================================
# (a) keygen
# =============================================================================


def test_keygen_writes_a_new_identity_readable_by_its_owner_and_prints_its_recipient_only(tmp_path, monkeypatch, capsys):
    """(a) §6, contract §8: F written 0600 in ``age-keygen``'s format, readable by pyrage; the recipient printed on a line
    of its own; the private key on no stream."""
    print_section("dev.py backup keygen")
    secure.instance(tmp_path, monkeypatch)
    path = tmp_path / "keys" / "backup-identity.txt"
    path.parent.mkdir()
    ran = run(capsys, "keygen", "--identity-file", str(path))
    assert ran.code == 0 and path.is_file(), f"keygen: exit 0 and the file written, not {ran.code}: {ran.text[-cli.TAIL:]}"
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"the identity is readable by its owner only (0600), not {oct(mode)}"
    lines = path.read_text(encoding="utf-8").splitlines()
    keys = [line for line in lines if line.startswith("AGE-SECRET-KEY-1")]
    assert len(keys) == 1 and [line for line in lines if line.startswith("# created: ") and line.endswith("Z")], f"one key line and a '# created: …Z' comment: {[line[:16] for line in lines]}"
    identity = x25519.Identity.from_str(keys[0])
    recipient = str(identity.to_public())
    assert f"# public key: {recipient}" in lines, f"the '# public key:' comment names its recipient: {[line[:16] for line in lines]}"
    assert recipient in [line.strip() for line in ran.out.splitlines()], f"the recipient printed on a line of its own: {ran.out[-cli.TAIL:]}"
    assert keys[0] not in ran.text and keys[0].lower() not in ran.text.lower(), "the private key is printed on no stream"
    message = pyrage.encrypt(b"sealed for this identity", [x25519.Recipient.from_str(recipient)])
    assert pyrage.decrypt(message, [identity]) == b"sealed for this identity", "pyrage reads the identity written"
    print_success(f"keygen → {recipient[:12]}…, 0600")


def test_keygen_never_replaces_a_file(tmp_path, monkeypatch, capsys):
    """(a) §6: an existing F: exit 1, a ❌ line saying it exists, F untouched, nothing beside it."""
    secure.instance(tmp_path, monkeypatch)
    path = tmp_path / "keys" / "backup-identity.txt"
    path.parent.mkdir()
    path.write_bytes(KEPT)
    ran = refused(capsys, "keygen", "--identity-file", str(path))
    assert ran.code == 1 and [line for line in ran.refused if "exist" in line], f"exit 1, a ❌ line saying the file exists: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert path.read_bytes() == KEPT and sorted(entry.name for entry in path.parent.iterdir()) == [path.name], "F untouched, nothing written beside it"
    print_success("keygen over an existing file → exit 1, untouched")


# =============================================================================
# (b) create
# =============================================================================


@pytest.mark.parametrize("count", [1, 2])
def test_create_with_recipients_writes_a_sealed_tar_each_identity_opens(tmp_path, monkeypatch, capsys, system_temp, count):
    """(b) §6: one ``.tar`` in ``backups/``, its three members in order; ``password.age`` opens with each identity; the
    manifest names the recipients in order; nothing else left."""
    print_section(f"dev.py backup create --recipient ×{count}")
    root = secure.instance(tmp_path, monkeypatch)
    pairs = [new_identity() for _ in range(count)]
    archive = created_tar(capsys, root, *(recipient for _identity, recipient in pairs))
    names, data = tar_members(archive)
    assert names == MEMBERS, f"the three members, in order: {names}"
    passwords = {pyrage.decrypt(data["password.age"], [identity]).decode("ascii") for identity, _recipient in pairs}
    assert len(passwords) == 1 and len(next(iter(passwords))) == 43, "each identity opens the same 43-character password"
    assert json.loads(data["manifest.json"])["recipients"] == [recipient for _identity, recipient in pairs], "the manifest names the recipients, in order"
    assert leftovers(tmp_path) == [], f"no envelope, partial or clear archive left: {leftovers(tmp_path)}"
    print_success(f"{archive.name}: sealed for {count}")


def test_create_refuses_three_recipients_and_writes_nothing(tmp_path, monkeypatch, capsys):
    """(b) §6, contract §2: at most two recipients."""
    root = secure.instance(tmp_path, monkeypatch)
    accepts(capsys, "create", "--recipient", new_identity()[1])
    before = cli.listing(root)
    ran = refused(capsys, "create", *[item for _ in range(3) for item in ("--recipient", new_identity()[1])])
    assert ran.code in (1, 2), f"three recipients refused: exit {ran.code}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"


def test_create_sealed_reads_the_recipients_of_the_variable(tmp_path, monkeypatch, capsys):
    """(b) §6: ``--sealed`` with ``LIBREFOLIO_BACKUP_RECIPIENTS`` set: the tar sealed for its recipient."""
    root = secure.instance(tmp_path, monkeypatch)
    identity, recipient = new_identity()
    monkeypatch.setenv(RECIPIENTS_VARIABLE, recipient)
    ran = run(capsys, "create", "--sealed")
    assert ran.code == 0, f"create --sealed: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    _names, data = tar_members(the_tar_written(root, ran.out))
    assert json.loads(data["manifest.json"])["recipients"] == [recipient], "sealed for the variable's recipient"
    assert len(pyrage.decrypt(data["password.age"], [identity])) == 43, "its identity opens the password"
    print_success("create --sealed: the variable's recipient")


def test_create_sealed_without_the_variable_names_it_and_writes_nothing(tmp_path, monkeypatch, capsys):
    """(b) §6: ``--sealed`` with the variable unset: exit 1, a ❌ line naming it, nothing written."""
    root = secure.instance(tmp_path, monkeypatch)
    accepts(capsys, "create", "--sealed")
    before = cli.listing(root)
    ran = refused(capsys, "create", "--sealed")
    assert ran.code == 1 and [line for line in ran.refused if RECIPIENTS_VARIABLE in line], f"exit 1, a ❌ line naming {RECIPIENTS_VARIABLE}: {ran.text[-cli.TAIL:]}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"


@pytest.mark.parametrize("other", [["--encrypt"], ["--password-file", "{file}"], ["--password-stdin"]], ids=["encrypt", "password-file", "password-stdin"])
def test_create_refuses_a_recipient_with_a_password(tmp_path, monkeypatch, capsys, prompts, other):
    """(b) §6: ``--recipient`` is exclusive with ``--encrypt``, ``--password-file``, ``--password-stdin``: refused,
    nothing written, nothing asked."""
    root = secure.instance(tmp_path, monkeypatch)
    recipient = new_identity()[1]
    accepts(capsys, "create", "--recipient", recipient)
    file = secure.password_file(tmp_path / "inputs", f"{secure.PASSWORD}\n")
    argv = ["create", "--recipient", recipient, *[str(file) if item == "{file}" else item for item in other]]
    before = cli.listing(root)
    with secure.stdin_holding(monkeypatch, f"{secure.PASSWORD}\n"):
        ran = refused(capsys, *argv)
    assert ran.code in (1, 2), f"refused: exit {ran.code}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    assert prompts == [], f"nothing asked: {prompts}"


# =============================================================================
# (c) decrypt, inspect, restore --dry-run of a sealed tar
# =============================================================================


@pytest.mark.parametrize(("name", "key"), [(GOOD, IDENTITY_1), (ROTATION, IDENTITY_2)], ids=["good-identity-1", "rotation-identity-2"])
def test_decrypt_of_a_sealed_vector_writes_the_zip_it_holds(tmp_path, monkeypatch, capsys, prompts, system_temp, name, key):
    """(c) §6, contract §9.1: ``decrypt`` with the identity: OUT the vector's zip (``zip_sha256``), 0600, alone in its
    folder; no envelope left; nothing asked."""
    print_section(f"dev.py backup decrypt {name}")
    secure.instance(tmp_path, monkeypatch)
    inputs = tmp_path / "inputs"
    archive, identity = vector(name, inputs), vector(key, inputs)
    out = secure.output_path(tmp_path)
    ran = run(capsys, "decrypt", str(archive), "--identity-file", str(identity), "-o", str(out))
    assert ran.code == 0, f"decrypt with the identity: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert cli.sha256_of(out) == CASES[GOOD]["zip_sha256"], "OUT is the zip the vector seals"
    assert stat.S_IMODE(out.stat().st_mode) == 0o600, f"OUT readable by its owner only: {oct(stat.S_IMODE(out.stat().st_mode))}"
    assert sorted(entry.name for entry in out.parent.iterdir()) == [out.name], "OUT alone in its folder"
    assert [path for path in leftovers(tmp_path) if path != f"{out.parent.name}/{out.name}"] == [], f"no temporary envelope or partial left: {leftovers(tmp_path)}"
    assert prompts == [], f"nothing asked: {prompts}"
    print_success(f"{name} → the vector's zip")


def test_inspect_of_a_tar_create_made_verifies_the_archive_it_holds(tmp_path, monkeypatch, capsys, prompts, system_temp):
    """(c) §6: ``inspect TAR --identity-file F`` of a tar ``create --recipient`` made: exit 0, the archive verified; no
    temporary envelope left."""
    root = secure.instance(tmp_path, monkeypatch)
    identity, recipient = new_identity()
    archive = created_tar(capsys, root, recipient)
    ran = run(capsys, "inspect", str(archive), "--identity-file", str(identity_file(tmp_path / "keys", identity)))
    assert ran.code == 0 and secure.VERIFIED_LINE in ran.out, f"inspect: exit 0, the archive verified: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert leftovers(tmp_path) == [], f"no temporary envelope or clear archive left: {leftovers(tmp_path)}"
    assert prompts == [], f"nothing asked: {prompts}"
    print_success("inspect of a sealed tar → verified")


def test_a_dry_run_of_a_tar_create_made_reports_it_restorable_without_the_key(tmp_path, monkeypatch, capsys, prompts, system_temp, head_database):
    """(c) §6, contract §7: a dry run of a tar ``create --recipient`` made of an instance at the head: exit 0, restorable,
    the instance key not included; the copy removed, the data directory as it was, no temporary envelope left."""
    print_section("dev.py backup restore --dry-run of a sealed tar")
    root = cli.point_at(monkeypatch, secure.instance_at_head(tmp_path / "instance", head_database))
    identity, recipient = new_identity()
    archive = created_tar(capsys, root, recipient)
    key = identity_file(tmp_path / "keys", identity)
    before, database = cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY)
    ran = run(capsys, "restore", str(archive), "--dry-run", "--identity-file", str(key))
    assert ran.code == 0 and ran.refused == [], f"a dry run: exit 0, no ❌: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    missing = [line for line in (cli.RESTORABLE_LINE, "   Instance key: not included") if line not in ran.out]
    assert missing == [], f"restorable, without the instance key: {missing} missing: {ran.out[-cli.TAIL:]}"
    assert cli.stages_left(root) == [], f"the copy is removed: {cli.stages_left(root)}"
    assert (cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY)) == (before, database), f"the data directory is as it was: {sorted(set(cli.outside_restore(root)) ^ set(before))}"
    assert leftovers(tmp_path) == [], f"no temporary envelope or clear archive left: {leftovers(tmp_path)}"
    assert prompts == [], f"nothing asked: {prompts}"
    print_success("dry run of a sealed tar → restorable, no key")


# =============================================================================
# (d) What a sealed tar refuses
# =============================================================================


@pytest.mark.parametrize(("name", "code"), NEGATIVES)
@pytest.mark.parametrize("command", READERS)
def test_a_sealed_vector_that_cannot_be_opened_is_refused_with_its_code_and_leaves_nothing(tmp_path, monkeypatch, capsys, prompts, system_temp, command, name, code):
    """(d) §6, contract §3.5, §9.1: exit 1, the code on a ❌ line; nothing at ``-o``; no copy in ``.restore/stage``; no
    temporary envelope, partial or clear zip left anywhere; nothing asked."""
    root = secure.instance(tmp_path, monkeypatch)
    inputs = tmp_path / "inputs"
    archive = vector(name, inputs)
    key = vector(IDENTITY_1, inputs)
    out = secure.output_path(tmp_path)
    ran = run(capsys, *reader_argv(command, archive, out, "--identity-file", str(key)))
    assert ran.code == 1 and ran.refusals(code), f"{command} {name}: exit 1, a ❌ line naming {code}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"nothing at -o: {sorted(entry.name for entry in out.parent.iterdir())}"
    assert cli.stages_left(root) == [], f"no copy left: {cli.stages_left(root)}"
    assert leftovers(tmp_path) == [], f"no temporary envelope, partial or clear zip left: {leftovers(tmp_path)}"
    assert prompts == [], f"nothing asked: {prompts}"
    print_success(f"{command} {name} → ({code})")


@pytest.mark.parametrize("command", READERS)
def test_a_sealed_tar_without_an_identity_file_is_refused_sealed_backup_needs_key(tmp_path, monkeypatch, capsys, prompts, system_temp, command):
    """(d) §6: a ``.tar`` without ``--identity-file``: exit 1, ``sealed_backup_needs_key``; nothing asked, nothing at
    ``-o``, nothing left. Barrier: the command takes ``--identity-file``."""
    root = secure.instance(tmp_path, monkeypatch)
    archive = vector(GOOD, tmp_path / "inputs")
    out = secure.output_path(tmp_path)
    accepts(capsys, *reader_argv(command, archive, out, "--identity-file", str(tmp_path / "inputs" / IDENTITY_1)))
    ran = run(capsys, *reader_argv(command, archive, out))
    assert ran.code == 1 and ran.refusals("sealed_backup_needs_key"), f"{command}: exit 1, a ❌ line naming sealed_backup_needs_key: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [] and cli.stages_left(root) == [], "nothing written, no copy left"
    assert leftovers(tmp_path) == [], f"nothing left: {leftovers(tmp_path)}"
    assert prompts == [], f"nothing asked: {prompts}"


@pytest.mark.parametrize("command", READERS)
def test_an_identity_file_given_with_a_zip_is_refused(tmp_path, monkeypatch, capsys, prompts, command):
    """(d) §6: ``--identity-file`` on an archive that is not sealed (a zip): exit 1 and a ❌ line; nothing at ``-o``."""
    secure.instance(tmp_path, monkeypatch)
    clear = secure.clear_archive(tmp_path / "backup")
    key = identity_file(tmp_path / "keys", new_identity()[0])
    out = secure.output_path(tmp_path)
    ran = run(capsys, *reader_argv(command, clear, out, "--identity-file", str(key)))
    assert ran.code == 1 and ran.refused, f"{command} of a zip with --identity-file: exit 1 and a ❌ line, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"nothing at -o: {sorted(entry.name for entry in out.parent.iterdir())}"


# =============================================================================
# (e) SEC-5: the key file on the command line
# =============================================================================

#: (e) The modes of a key file its group or others may read, and the one only its owner reads.
LOOSE_MODES = [pytest.param(0o644, id="0644"), pytest.param(0o640, id="0640")]
#: (e) The line every reader prints once the password is opened: the command went on.
OPENED = "🔏 Sealed backup "


def loose_key_warnings(ran: Ran, key: Path) -> list[str]:
    """The ``⚠️`` lines naming ``key``."""
    return [line for line in ran.text.splitlines() if line.startswith("⚠️") and str(key) in line]


def read_with_key_of_mode(tmp_path: Path, monkeypatch, capsys, command: str, mode: int) -> tuple[Ran, Path, Path]:
    """``command`` of the vectors' good tar, ``test-identity-1.txt`` copied with ``mode``: what it did, the key, ``-o``."""
    secure.instance(tmp_path, monkeypatch)
    inputs = tmp_path / "inputs"
    archive, key = vector(GOOD, inputs), vector(IDENTITY_1, inputs)
    key.chmod(mode)
    out = secure.output_path(tmp_path)
    return run(capsys, *reader_argv(command, archive, out, "--identity-file", str(key))), key, out


@pytest.mark.parametrize("mode", LOOSE_MODES)
@pytest.mark.parametrize("command", READERS)
def test_a_key_file_others_may_read_is_warned_of_and_the_command_goes_on(tmp_path, monkeypatch, capsys, prompts, system_temp, command, mode):
    """(e) SEC-5: one ``⚠️`` line names the key file, its mode in octal and ``chmod 600``; the password is opened all the
    same (the ``🔏`` line), and ``decrypt`` exits 0 with the vector's zip. Red until the cure: no warning."""
    print_section(f"SEC-5: {command} with a key file of mode {mode:04o}")
    ran, key, out = read_with_key_of_mode(tmp_path, monkeypatch, capsys, command, mode)
    assert stat.S_IMODE(key.stat().st_mode) == mode, f"precondition: the key file's mode is {mode:04o}"
    assert [line for line in ran.out.splitlines() if line.startswith(OPENED)], f"{command}: the command goes on, the password opened: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    if command == "decrypt":
        assert ran.code == 0 and cli.sha256_of(out) == CASES[GOOD]["zip_sha256"], f"decrypt: exit 0, the vector's zip written: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    warned = loose_key_warnings(ran, key)
    assert len(warned) == 1, f"{command}: one ⚠️ line naming {key.name}: {warned}: {ran.text[-cli.TAIL:]}"
    assert f"{mode:04o}" in warned[0] and "chmod 600" in warned[0], f"{command}: the line says the mode {mode:04o} and suggests chmod 600: {warned[0]}"
    print_success(f"{command}, {mode:04o}: warned, went on")


@pytest.mark.parametrize("command", READERS)
def test_a_key_file_only_its_owner_reads_is_not_warned_of(tmp_path, monkeypatch, capsys, prompts, system_temp, command):
    """(e) SEC-5, a GUARD: a 0600 key file: no ``⚠️`` line names it, nothing suggests ``chmod 600``; the command goes on."""
    ran, key, _out = read_with_key_of_mode(tmp_path, monkeypatch, capsys, command, 0o600)
    assert [line for line in ran.out.splitlines() if line.startswith(OPENED)], f"{command}: the password opened: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert loose_key_warnings(ran, key) == [] and "chmod 600" not in ran.text, f"{command}: no warning for a 0600 key file: {ran.text[-cli.TAIL:]}"


def in_folder(fd: int, folder: Path) -> bool:
    """Whether ``fd`` is a regular file of ``folder``: one of its entries, or a file of its file system without a name
    yet (``O_TMPFILE``)."""
    found = os.fstat(fd)
    if not stat.S_ISREG(found.st_mode):
        return False
    if found.st_nlink == 0 and found.st_dev == folder.stat().st_dev:
        return True
    return any(entry.inode() == found.st_ino and entry.stat(follow_symlinks=False).st_dev == found.st_dev for entry in os.scandir(folder))


def name_in_folder(fd: int, folder: Path) -> str | None:
    found = os.fstat(fd)
    return next((entry.name for entry in os.scandir(folder) if entry.inode() == found.st_ino), None)


def keygen_target(tmp_path: Path, monkeypatch) -> Path:
    secure.instance(tmp_path, monkeypatch)
    folder = tmp_path / "keys"
    folder.mkdir()
    return folder / "backup-identity.txt"


def test_keygen_writes_its_key_to_a_private_temporary_file_then_links_it(tmp_path, monkeypatch, capsys):
    """(e) SEC-5: every byte of the key goes through ``os.write`` to a file of F's folder that is not F, of mode 0600,
    ``fsync``ed while F does not exist yet; then F holds the key (exit 0) and nothing else is left in the folder. Red
    until the cure: ``keygen`` writes F itself, through a file object, without an ``fsync``."""
    print_section("SEC-5: keygen writes its key atomically")
    target = keygen_target(tmp_path, monkeypatch)
    folder = target.parent
    real_write, real_fsync = os.write, os.fsync
    writes: list[tuple[str | None, int]] = []
    fsyncs: list[tuple[str | None, bool]] = []

    def write(fd: int, data: Any) -> int:
        if in_folder(fd, folder):
            writes.append((name_in_folder(fd, folder), stat.S_IMODE(os.fstat(fd).st_mode)))
        return real_write(fd, data)

    def fsync(fd: int) -> None:
        if in_folder(fd, folder):
            fsyncs.append((name_in_folder(fd, folder), os.path.lexists(target)))
        real_fsync(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", write)
        patch.setattr(os, "fsync", fsync)
        ran = run(capsys, "keygen", "--identity-file", str(target))
    assert ran.code == 0 and target.is_file(), f"keygen: exit 0 and F written: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert writes, "the key is written through os.write to a file of F's folder (none seen)"
    assert all(name != target.name and mode == 0o600 for name, mode in writes), f"every write goes to a temporary file, never F, of mode 0600: {writes}"
    assert fsyncs and all(name != target.name and not existed for name, existed in fsyncs), f"the temporary file is fsynced while F does not exist yet: {fsyncs}"
    assert sorted(entry.name for entry in folder.iterdir()) == [target.name] and stat.S_IMODE(target.stat().st_mode) == 0o600, f"F alone in its folder, 0600: {sorted(entry.name for entry in folder.iterdir())}"
    assert [line for line in target.read_text(encoding="utf-8").splitlines() if line.startswith("AGE-SECRET-KEY-1")], "F holds the key"
    print_success("keygen: a temporary 0600 file, fsynced, then F")


#: (e) What fails while ``keygen`` writes the key: (the function of ``os``, its errno).
KEYGEN_FAILURES = [
    pytest.param("write", errno.EIO, id="os.write-EIO"),
    pytest.param("write", errno.ENOSPC, id="os.write-ENOSPC"),
    pytest.param("fsync", errno.EIO, id="os.fsync-EIO"),
]


@pytest.mark.parametrize(("failing", "error_number"), KEYGEN_FAILURES)
def test_keygen_that_fails_while_writing_leaves_no_key_file_and_no_temporary_file(tmp_path, monkeypatch, capsys, failing, error_number):
    """(e) SEC-5: ``os.write`` or ``os.fsync`` fails for the files of F's folder: exit 1, a ❌ line, F does not exist,
    nothing left in the folder, the private key on no stream. Barrier: the failure was met. Red until the cure: keygen
    calls neither, exits 0 and leaves F."""
    target = keygen_target(tmp_path, monkeypatch)
    folder = target.parent
    real = getattr(os, failing)
    met: list[str] = []

    def failing_call(fd: int, *args: Any) -> Any:
        if in_folder(fd, folder):
            met.append(failing)
            raise OSError(error_number, os.strerror(error_number))
        return real(fd, *args)

    with monkeypatch.context() as patch:
        patch.setattr(os, failing, failing_call)
        ran = run(capsys, "keygen", "--identity-file", str(target))
    assert ran.code == 1 and ran.refused, f"os.{failing} failing: exit 1 and a ❌ line, not exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert met, f"barrier: os.{failing} was called for the key, and failed"
    assert not os.path.lexists(target) and list(folder.iterdir()) == [], f"F does not exist, no temporary file left: {sorted(entry.name for entry in folder.iterdir())}"
    assert "AGE-SECRET-KEY" not in ran.text.upper(), "the private key on no stream"
    print_success(f"keygen, os.{failing} failing: exit 1, nothing left")


def test_keygen_never_replaces_a_key_file_that_appears_while_it_writes(tmp_path, monkeypatch, capsys):
    """(e) SEC-5: F does not exist when ``keygen`` starts, and appears (another process's key) once the temporary file is
    ``fsync``ed: exit 1, a ❌ line saying it exists, F as it was, nothing beside it. Barrier: the ``fsync`` of the key
    ran. Red until the cure: no ``fsync``, and F written directly."""
    target = keygen_target(tmp_path, monkeypatch)
    folder = target.parent
    real_fsync = os.fsync
    met: list[str] = []

    def fsync(fd: int) -> None:
        real_fsync(fd)
        if in_folder(fd, folder) and not os.path.lexists(target):
            met.append("fsync")
            target.write_bytes(KEPT)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fsync)
        ran = run(capsys, "keygen", "--identity-file", str(target))
    assert met, f"barrier: the temporary key was fsynced before F existed (exit {ran.code}): {ran.text[-cli.TAIL:]}"
    assert ran.code == 1 and [line for line in ran.refused if "exist" in line], f"exit 1, a ❌ line saying F exists: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert target.read_bytes() == KEPT and sorted(entry.name for entry in folder.iterdir()) == [target.name], f"F as it was, nothing beside it: {sorted(entry.name for entry in folder.iterdir())}"
    print_success("keygen: an F that appeared is never replaced")
