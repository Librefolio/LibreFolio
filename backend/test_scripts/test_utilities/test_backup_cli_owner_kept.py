"""
The command line and a restore from the hosting panel that KEPT the owner's password and sessions (workstream B, lot B5-1l;
contract ``B-5-1l-contratto.md`` «CLI»). Selector: ``utils backup-cli-owner-kept``. Written RED before the implementation.

(a) ``backup pending`` of a committed restore whose ``owner_outcome`` is ``kept``: ONE line more than the same restore
    without an outcome, word for word ``🔑 The owner's account kept its password and its open sessions (restore from the
    hosting panel)``; no id, no address, no ``❌``, no link, no ``--recover``. Red before B5-1l: the outcome is not one the
    printer knows, so it says ``❌ The owner's account could not be set (kept)``.
(b) ``backup pending --json`` is unchanged for it (GUARD): the usual keys, ``committed``, no reason, no choices, byte for
    byte the line of the same restore with no owner; nothing of the owner in it. ``--recover owner`` is not offered (exit 4
    ``choice_not_valid``) and changes nothing.
(c) ``backup restore`` from the command line of the SAME copy (the marked administrator holds the owner's address, one mark) on
    a managed instance never keeps (GUARD): the report and the line after the confirmation say the account's password is
    CLOSED at the restore, the state records the picked account and no outcome, nothing says ``kept``, and no address is
    printed. The command line revokes the owner's password all the same.

Pure, as ``test_backup_cli_restore.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen
through ``LIBREFOLIO_DATA_DIR``, a real database at the head made once by alembic. POSIX only.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.archive import build_archive
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.app.services.platform.instance_backup.staging import StagingReport
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utilities import test_backup_cli_recover as recover
from backend.test_scripts.test_utilities import test_backup_cli_restore as restore_cli
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

pytestmark = restore_cli.pytestmark

# The fixtures of the command line's tests, re-exported (the autouse ones included).
app_version = cli.app_version
head_database = cli.head_database
no_restart = restore_cli.no_restart
no_inherited_block = restore_cli.no_inherited_block
no_inherited_restore_limit = restore_cli.no_inherited_restore_limit
no_inherited_instance_key = restore_cli.no_inherited_instance_key

#: The line of the contract, word for word (the command line is English only).
KEPT_LINE = "🔑 The owner's account kept its password and its open sessions (restore from the hosting panel)"
#: A distinctive id of the owner's account: it must never be printed.
OWNER_ID = 4217
#: The owner's address (``LIBREFOLIO_ADMIN_EMAIL``, an ``example.com`` one: ``.test`` is refused there) and the backup's other one.
OWNER_ADDRESS = "keeper.owner.b51l@example.com"
OTHER_ADDRESS = "bob.b51l@example.com"


def state_with(root: Path, **owner: Any) -> None:
    """A committed restore via the hosting panel, the owner's fields ``owner`` in it."""
    restore_cli.write_state(root, "committed", confirmed_by="panel", confirmed_via="panel", **owner)


# =============================================================================
# (a) pending
# =============================================================================


def test_pending_says_in_one_line_that_the_owner_kept_their_password_and_sessions(tmp_path, monkeypatch, capsys):
    """(a) B5-1l: a committed panel restore with the owner named and the outcome ``kept``: ``pending`` prints exactly one line
    more than the same restore without an outcome, and it is the contract's line, word for word. No account id, no address,
    no ``❌``, no link, no ``--recover``. Red before B5-1l: the line is the error one."""
    print_section("(a) B5-1l pending: kept")
    capsys.readouterr()  # the section title is output too
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_ADDRESS)
    extra, out = restore_cli.owner_lines_via(tmp_path, monkeypatch, capsys, "panel", owner_user_id=OWNER_ID, owner_outcome="kept")
    assert extra == [KEPT_LINE], f"[new] B5-1l: one line, the contract's: {extra}\n{out}"
    shown = [secret for secret in (str(OWNER_ID), OWNER_ADDRESS, "❌", "--recover", "reset-password", "could not") if secret in out]
    assert shown == [], f"pending holds {shown}: {out}"
    print_success(extra[0])


def test_the_owner_outcome_printer_says_the_kept_line_and_nothing_else(capsys):
    """(a) B5-1l: ``_print_owner_outcome`` of an owner named with the outcome ``kept`` prints the one line and no other."""
    capsys.readouterr()
    backup_cli._print_owner_outcome(SimpleNamespace(owner_user_id=OWNER_ID, owner_outcome="kept"))
    said = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert said == [KEPT_LINE], f"[new] B5-1l: the kept line: {said}"
    print_success("kept: the line")


# =============================================================================
# (b) pending --json
# =============================================================================


def test_pending_json_of_a_kept_restore_is_the_line_of_a_restore_with_no_owner(tmp_path, monkeypatch, capsys):
    """(b) GUARD, B5-1l: ``pending --json`` of the kept restore is exactly the line of the same restore with no owner — the
    six keys, ``committed``, ``reason`` null, no choices — and names nothing of the owner (no word ``owner`` or ``kept``, no
    id, no address)."""
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_ADDRESS)
    baseline_root = restore_cli.instance(tmp_path / "baseline", monkeypatch)
    state_with(baseline_root)
    baseline = recover.the_line(recover.go(capsys, "pending", "--json"))
    root = restore_cli.instance(tmp_path / "kept", monkeypatch)
    state_with(root, owner_user_id=OWNER_ID, owner_outcome="kept")
    ran = recover.go(capsys, "pending", "--json")
    line = recover.the_line(ran)
    assert ran.code == 0 and set(line) == recover.KEYS, f"the usual keys: {line}"
    assert (line["state"], line["reason"], line["choices"]) == ("committed", None, []), f"committed, nothing to recover: {line}"
    assert line == baseline, f"the line of a restore with no owner: {line} / {baseline}"
    both = (ran.out + ran.err).lower()
    shown = [secret for secret in ("owner", "kept", str(OWNER_ID), OWNER_ADDRESS.lower()) if secret in both]
    assert shown == [], f"pending --json holds {shown}: {ran.out}"
    print_success("pending --json: unchanged")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_owner_is_not_offered_for_a_kept_restore_and_changes_nothing(tmp_path, monkeypatch, capsys, as_json):
    """(b) GUARD, B5-1l: nothing failed, so ``--recover owner`` is exit 4 ``choice_not_valid`` and nothing on disk changes."""
    root = restore_cli.instance(tmp_path, monkeypatch)
    state_with(root, owner_user_id=OWNER_ID, owner_outcome="kept")
    before = restore_cli.everything(root)
    argv = ("pending", *(("--json",) if as_json else ()), "--recover", "owner")
    ran = recover.go(capsys, *argv)
    assert ran.code == 4, f"{' '.join(argv)}: exit 4, not {ran.code}\n{ran.out}{ran.err}"
    if as_json:
        line = recover.the_line(ran)
        assert (line["error"], line["recover"]) == (recover.NOT_VALID, {"choice": "owner", "done": False}), f"not valid, not done: {line}"
    else:
        assert ran.refused and not any(line.startswith("✅") for line in ran.lines), f"not done: {ran.out}"
    assert restore_cli.everything(root) == before, "nothing changed"
    print_success("--recover owner: exit 4")


# =============================================================================
# (c) the command line never keeps
# =============================================================================


def kept_copy_archive(tmp_path: Path, database: Path) -> Path:
    """The archive of a backup the panel would keep: ``anna_admin``, an active administrator, marked as the instance's owner
    (the only mark), holding ``OWNER_ADDRESS``; and ``bob_user``, a plain user."""
    data = cli.make_data_dir(tmp_path / "source", database=False)
    (data / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(database, data / DATABASE_ENTRY)
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        conn.executemany(restore_cli.INSERT, [("anna_admin", OWNER_ADDRESS.upper(), "$argon2id$not-a-real-hash", 1, 1, cli.CREATED, cli.CREATED), ("bob_user", OTHER_ADDRESS, "$argon2id$not-a-real-hash", 1, 0, cli.CREATED, cli.CREATED)])
        conn.execute("UPDATE users SET is_instance_owner = 1 WHERE username = 'anna_admin'")
    work = tmp_path / "work"
    work.mkdir()
    return build_archive(data, work, work / cli.NAME, origin="cli").path


def test_restore_yes_of_the_copy_the_panel_would_keep_closes_the_password_and_never_says_kept(tmp_path, monkeypatch, capsys, head_database):
    """(c) GUARD, B5-1l: ``restore ARCHIVE --yes`` on a managed instance of the copy the rule keeps for the panel: confirmed,
    exit 0, the state records the picked account and NO outcome (never ``kept``), via ``cli``; the owner line, in the report
    and after the ✅, names ``anna_admin`` and says her password is closed at the restore; the word ``kept`` and any address
    are nowhere in the output."""
    print_section("(c) B5-1l the command line never keeps")
    capsys.readouterr()  # the section title is output too
    root = restore_cli.instance(tmp_path, monkeypatch)
    restore_cli.managed_owner(monkeypatch, owner_email=OWNER_ADDRESS)
    archive = kept_copy_archive(tmp_path, head_database)
    code = restore_cli.run("restore", str(archive), "--yes")
    out = capsys.readouterr().out
    assert code == 0, f"confirmed: exit 0: {out}"
    lines = restore_cli.owner_words(out)
    assert len(lines) == 2 and all("anna_admin" in line and "password is closed" in line for line in lines), f"twice, naming anna and saying the password is closed: {lines}\n{out}"
    state = json.loads(restore_cli.state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["confirmed_via"], state["owner_user_id"], state["owner_outcome"]) == ("pending", "cli", restore_cli.id_of(root, "anna_admin"), None), f"the picked account, no outcome: {state}"
    shown = [secret for secret in ("kept", OWNER_ADDRESS.lower(), OTHER_ADDRESS) if secret in out.lower()]
    assert shown == [], f"the output holds {shown}: {out}"
    print_success("cli: picked, closed, never kept")


def test_the_report_of_the_copy_the_panel_would_keep_still_says_the_password_is_closed_for_the_command_line(monkeypatch, capsys):
    """(c) GUARD, B5-1l: a report that carries ``owner_marks`` 1 with the marked administrator holding the owner's address —
    what the lot adds — prints, for the command line, the same owner line as before: the account by username, its password
    closed at the restore. The CLI never says ``kept``."""
    restore_cli.managed_owner(monkeypatch, owner_email=OWNER_ADDRESS)
    holder = {"user_id": 3, "username": "anna_admin", "email": OWNER_ADDRESS.upper(), "is_superuser": True, "is_active": True, "is_instance_owner": True}
    data = restore_cli.owner_report([holder], checked=OWNER_ADDRESS).model_dump(mode="json")
    report = StagingReport.model_validate({**data, "owner_marks": 1})
    capsys.readouterr()
    backup_cli._print_stage_report(report)
    out = capsys.readouterr().out
    lines = restore_cli.owner_words(out)
    assert len(lines) == 1 and "anna_admin" in lines[0] and "password is closed" in lines[0], f"one owner line, the password closed: {lines}\n{out}"
    assert "kept" not in out.lower() and OWNER_ADDRESS.lower() not in out.lower(), f"nothing kept, no address: {out}"
    print_success("report: closed, never kept")
