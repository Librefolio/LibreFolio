"""
A backup with more active accounts than ``LIBREFOLIO_MAX_USERS``, from the command line: one warning line, no refusal
(workstream B, lot B5-1k2; contract ``B-5-1k2-contratto.md`` «CLI»). Selector: ``utils backup-cli-users-limit``.

Written RED, before B5-1k2: the report prints nothing about the limit. The tests of the restore itself prove first that the
line is there (red today) and then that the command confirms as before.

(a) The report (``_print_stage_report``): when ``users_over_limit > 0``, ONE line
    ``⚠️  The backup holds {N} active accounts; this instance accepts {M} (LIBREFOLIO_MAX_USERS): at the first sign-in the
    administrator chooses who keeps access, the others are deactivated (not deleted)`` (``N`` is ``users_active``, ``M``
    ``users_limit``), no username, no address, and not a second time through the generic warnings loop (the code
    ``users_over_limit`` is said apart). Nothing when not over (at the limit, no limit, an invalid one).
(b) ``backup restore ARCHIVE`` of such a backup (self-hosted and managed): the line is printed before the confirmation, then
    ``--yes`` confirms (exit 0, the restore pending via ``cli``, today's fields in the state), ``--dry-run`` exits 0 saying the
    archive can be restored; nothing refuses.
(c) No option is added: ``--remove-user`` is not in the help and argparse refuses it (exit 2).

Pure: data directories under tmp_path, the real databases of the command line's tests (alembic at the head), no lane
database, no server, no network. POSIX only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.staging import StagingReport
from backend.test_scripts.test_services import test_backup_apply as applied
from backend.test_scripts.test_utilities import test_backup_cli as cli
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

LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
CODE = "users_over_limit"
OVER_LINE = re.compile(r"^⚠️\s+The backup holds (\d+) active accounts; this instance accepts (\d+) \(LIBREFOLIO_MAX_USERS\)")
#: What the line says after the numbers, word for word (contract «CLI»).
OVER_TAIL = ": at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)"
#: (username, is_active, is_superuser): five active accounts, a disabled one. Their address is ``<name>@example.test``.
EXAMPLE = (("anna_k", 1, 1), ("bruno_k", 1, 1), ("carla_k", 1, 0), ("dario_k", 1, 0), ("elena_k", 1, 0), ("olga_k", 0, 1))
PLAIN_USERS = ("carla_k", "dario_k", "elena_k", "olga_k")


@pytest.fixture(autouse=True)
def no_inherited_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)


def limited(monkeypatch: pytest.MonkeyPatch, limit: str | None) -> None:
    if limit is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, limit)


def over_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if OVER_LINE.match(line)]


def limit_mentions(out: str) -> list[str]:
    return [line for line in out.splitlines() if "LIBREFOLIO_MAX_USERS" in line]


def users_report(*, active: int = 5, limit: int | None = 3, **more: Any) -> StagingReport:
    """The report of a check as B5-1k2 writes it: ``test_backup_cli.upgrade_report`` with the three numbers and, when over the
    limit, the warning before ``credentials_from_backup`` (raw JSON, so that it reads before B5-1k2 too: the fields are then
    ignored, and only the warning, a code the command does not know, is left)."""
    data = cli.upgrade_report().model_dump(mode="json")
    over = 0 if limit is None else max(0, active - limit)
    warnings = [warning for warning in data["warnings"] if warning != "credentials_from_backup"]
    if over:
        warnings.append(CODE)
    data.update(users_active=active, users_limit=limit, users_over_limit=over, warnings=[*warnings, "credentials_from_backup"], **more)
    return StagingReport.model_validate(data)


# =============================================================================
# (a) The report
# =============================================================================


def test_the_report_says_how_many_accounts_the_backup_holds_and_how_many_the_instance_accepts_once(capsys):
    """(a) B5-1k2: 5 active accounts, a limit of 3: ONE ⚠️ line with both numbers and ``LIBREFOLIO_MAX_USERS``, ending as the
    contract says; the code is not said a second time by the generic loop."""
    print_section("(a) B5-1k2 the report over the limit")
    capsys.readouterr()
    backup_cli._print_stage_report(users_report())
    out = capsys.readouterr().out
    lines = over_lines(out)
    assert len(lines) == 1, f"[new] B5-1k2: one ⚠️ line «The backup holds 5 active accounts; this instance accepts 3 (LIBREFOLIO_MAX_USERS)»: {out}"
    assert OVER_LINE.match(lines[0]).groups() == ("5", "3"), f"N is users_active, M users_limit: {lines[0]!r}"
    assert lines[0].endswith(OVER_TAIL), f"the line ends as the contract says: {lines[0]!r}"
    assert len(limit_mentions(out)) == 1 and CODE not in out, f"said once, the code never printed raw: {out}"
    print_success(lines[0])


def test_the_line_names_no_account_and_no_address(monkeypatch, capsys):
    """(a) B5-1k2: a managed report carries the owner's candidates with their usernames and addresses; the limit's line holds
    none of them, only its two numbers."""
    capsys.readouterr()
    restore_cli.managed_owner(monkeypatch)
    candidates = [restore_cli.ANNA, restore_cli.CARL]
    backup_cli._print_stage_report(users_report(owner_candidates=candidates, owner_email_checked=restore_cli.NEW_OWNER_EMAIL))
    out = capsys.readouterr().out
    lines = over_lines(out)
    assert len(lines) == 1, f"[new] B5-1k2: the line is there: {out}"
    assert lines[0] == f"⚠️  The backup holds 5 active accounts; this instance accepts 3 (LIBREFOLIO_MAX_USERS){OVER_TAIL}", f"only the numbers vary: {lines[0]!r}"
    named = [word for word in (restore_cli.ANNA["username"], restore_cli.CARL["username"], restore_cli.ANNA["email"], restore_cli.CARL["email"], restore_cli.NEW_OWNER_EMAIL) if word in lines[0]]
    assert named == [], f"the line names {named}"
    print_success("numbers only")


@pytest.mark.parametrize(("active", "limit"), [(5, None), (5, 5), (5, 6), (2, 3)], ids=["no-limit", "at-the-limit", "below-the-limit", "few-accounts"])
def test_the_report_says_nothing_of_the_limit_when_the_backup_fits(capsys, active, limit):
    """(a) B5-1k2: not over the limit (or no limit, which is also what an invalid value is read as): no such line."""
    capsys.readouterr()
    backup_cli._print_stage_report(users_report(active=5, limit=3))
    assert over_lines(capsys.readouterr().out), "[new] B5-1k2: barrier: the same accounts over a limit of 3 do print the line"
    backup_cli._print_stage_report(users_report(active=active, limit=limit))
    out = capsys.readouterr().out
    assert over_lines(out) == [] and limit_mentions(out) == [], f"nothing about the limit: {out}"
    print_success("fits: silent")


# =============================================================================
# (b) backup restore
# =============================================================================


def example_archive(tmp_path: Path, database: Path, *, flagged: tuple[str, ...] = ()) -> Path:
    """The archive of a backup of the example: five active accounts, a disabled one (restore_cli's builder)."""
    return restore_cli.owner_archive(tmp_path, database, EXAMPLE, flagged=flagged)


def restored(tmp_path: Path, monkeypatch, capsys, database: Path, *flags: str, limit: str | None = "3", managed: bool = False, flagged: tuple[str, ...] = ()) -> tuple[int, str, Path]:
    root = restore_cli.instance(tmp_path, monkeypatch)
    limited(monkeypatch, limit)
    if managed:
        restore_cli.managed_owner(monkeypatch)
    source = example_archive(tmp_path, database, flagged=flagged)
    capsys.readouterr()
    code = restore_cli.run("restore", str(source), *flags)
    return code, capsys.readouterr().out, root


def no_account_named(out: str) -> None:
    shown = [word for word in (*PLAIN_USERS, "@example") if word in out]
    assert shown == [], f"no plain user's name and no address in the output: {shown}\n{out}"


def test_a_restore_with_yes_of_the_example_warns_once_and_confirms(tmp_path, monkeypatch, capsys, head_database):
    """(b) B5-1k2: ``restore ARCHIVE --yes`` of the example (5 active accounts, limit 3): the report prints ONE line with 5 and
    3 BEFORE the confirmation; exit 0, ✅ the restore waits for the next start; the state is ``pending`` via ``cli`` and holds
    today's fields; the copy is kept; the live data untouched; no plain user's name and no address printed."""
    print_section("(b) B5-1k2 --yes of too many accounts")
    root = restore_cli.instance(tmp_path, monkeypatch)
    limited(monkeypatch, "3")
    before = restore_cli.live(root)
    capsys.readouterr()
    code = restore_cli.run("restore", str(example_archive(tmp_path, head_database)), "--yes")
    out = capsys.readouterr().out
    lines = out.splitlines()
    over = over_lines(out)
    assert len(over) == 1 and OVER_LINE.match(over[0]).groups() == ("5", "3"), f"[new] B5-1k2: one line, 5 and 3: {out}"
    assert len(limit_mentions(out)) == 1 and CODE not in out, f"not said a second time, the code never raw: {out}"
    assert code == 0, f"nothing refuses: exit 0: {out}"
    confirmed_at = next((index for index, line in enumerate(lines) if line.startswith("✅") and "waits for the next start" in line), None)
    assert confirmed_at is not None and lines.index(over[0]) < confirmed_at, f"the restore waits, and the line came before it: {out}"
    state = json.loads(restore_cli.state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["confirmed_via"]) == ("pending", "cli") and set(state) == applied.STATE_FIELDS, f"pending via cli, today's fields: {sorted(set(state) ^ applied.STATE_FIELDS)} {state}"
    assert len(cli.stages_left(root)) == 1, "the copy is kept for the next start"
    assert restore_cli.live(root) == before, "the live data is as it was"
    no_account_named(out)
    print_success(over[0])


def test_a_dry_run_of_the_example_warns_once_and_exits_0(tmp_path, monkeypatch, capsys, head_database):
    """(b) B5-1k2: ``--dry-run``: the line once, exit 0, «can be restored», nothing confirmed, the copy removed."""
    root = restore_cli.instance(tmp_path, monkeypatch)
    limited(monkeypatch, "3")
    capsys.readouterr()
    code = restore_cli.run("restore", str(example_archive(tmp_path, head_database)), "--dry-run")
    out = capsys.readouterr().out
    assert len(over_lines(out)) == 1, f"[new] B5-1k2: the line, once: {out}"
    assert code == 0 and "can be restored" in out, f"a dry run is not refused: exit {code}: {out}"
    restore_cli.nothing_pending(root)
    no_account_named(out)
    print_success("dry run: exit 0")


def test_on_a_managed_instance_the_restore_is_confirmed_all_the_same(tmp_path, monkeypatch, capsys, head_database):
    """(b) B5-1k2: managed, ``LIBREFOLIO_ADMIN_EMAIL`` set, Anna the administrator the backup marks as its owner: the line once,
    exit 0, the restore pending via ``cli`` with today's fields."""
    code, out, root = restored(tmp_path, monkeypatch, capsys, head_database, "--yes", managed=True, flagged=("anna_k",))
    assert len(over_lines(out)) == 1, f"[new] B5-1k2: the line, once: {out}"
    assert code == 0 and not any(line.startswith("❌") for line in out.splitlines()), f"nothing refuses: exit {code}: {out}"
    state = json.loads(restore_cli.state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["confirmed_via"]) == ("pending", "cli") and set(state) == applied.STATE_FIELDS, f"pending via cli, today's fields: {state}"
    no_account_named(out)
    print_success("managed: exit 0, pending")


@pytest.mark.parametrize(("limit", "reason"), [("5", "at the limit"), ("9", "below it"), (None, "no limit"), ("not a number", "an invalid limit is no limit")], ids=["at-the-limit", "below", "none", "invalid"])
def test_a_backup_that_fits_prints_no_line_and_is_confirmed(tmp_path, monkeypatch, capsys, head_database, limit, reason):
    """(b) B5-1k2: the same backup when it fits (or the limit is none): no line about the limit; exit 0, pending."""
    code, out, root = restored(tmp_path, monkeypatch, capsys, head_database, "--yes", limit=limit)
    assert code == 0 and restore_cli.state_path(root).is_file(), f"{reason}: confirmed: exit {code}: {out}"
    assert over_lines(out) == [] and limit_mentions(out) == [], f"{reason}: nothing about the limit: {out}"
    print_success(reason)


# =============================================================================
# (c) No option is added
# =============================================================================


def test_the_help_has_no_remove_user_and_argparse_refuses_it(monkeypatch, capsys):
    """(c) B5-1k2, a guard that stays green: ``backup restore --help`` does not mention ``--remove-user`` and the command line
    refuses it (argparse exit 2): the design that deleted accounts is gone."""
    text = cli.help_of(monkeypatch, capsys, "backup", "restore")
    assert "--yes" in text and "--dry-run" in text, f"barrier: the help is the restore's: {text}"
    assert "--remove-user" not in text and "remove-user" not in text, f"the help mentions no removal: {text}"
    parser = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(parser.add_subparsers(dest="command"))
    with pytest.raises(SystemExit) as refused:
        parser.parse_args(["backup", "restore", "archive.zip", "--remove-user", "carla_k"])
    assert refused.value.code == 2, f"argparse refuses the option: exit {refused.value.code}"
    capsys.readouterr()
    print_success("no --remove-user")
