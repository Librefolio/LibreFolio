"""
A restore from the hosting PANEL on a MANAGED instance keeps the owner's password and sessions (workstream B, lot B5-1l;
contract ``B-5-1l-contratto.md``). Selector: ``services backup-owner-kept``. Written RED before the implementation: no
production code exists for it yet, so every test of a NEW behaviour fails for the missing function, field, outcome or
behaviour it names ("[new] B5-1l: ..."). The tests marked GUARD are green before and after: they pin what the lot must NOT
change (B5-1j's fallback, the command line and the app, the startup step, the guard).

The rule (all four together, otherwise B5-1j stays to the letter): (1) the channel is the panel (``confirmed_via == "panel"``;
never the app, never the command line); (2) the profile is ``managed`` and ``LIBREFOLIO_ADMIN_EMAIL`` is set; (3) exactly ONE
account of the backup is marked as the instance's owner (``users.is_instance_owner = 1``, counted over EVERY account, of any
role, active or not: ``StagingReport.owner_marks``) and it is an ACTIVE administrator; (4) that account holds the address of
``LIBREFOLIO_ADMIN_EMAIL`` (``user_service.same_email``). The report must have no ``owner_conflicts`` (as today: ``owner_conflict``
first) and must have been read for this address (``restore_stage_outdated``, as today).

(a) Staging: ``staging._owner_marks(database) -> int`` (read only, every account, a column that is absent reads 0);
    ``StagingReport.owner_marks`` (default 0: a report written before reads 0), kept in ``report.json`` and read back;
    ``staging._owner_check`` keeps its three values.
(b) ``apply.keeps_owner(candidates, owner_marks, owner_email) -> int | None``: the truth table of the rule;
    ``apply.OWNER_OUTCOME_KEPT == "kept"``; ``RestoreState`` gains no field.
(c) ``confirm_restore``: via the panel, managed, the address set, the rule holding: ``owner_user_id`` is that account and
    ``owner_outcome`` is ``"kept"`` at once. Each missing condition falls back to exactly what B5-1j does (the pick); the
    command line and the app never keep, with the SAME copy; self-hosted and an unset address never; conflicts and a report
    read for another address are refused as before.
(d) The commit (``finish_pending_restore`` -> ``_close_the_way_in(..., kept_owner_user_id=)``) on a real restored database:
    the kept account's ``hashed_password`` and ``session_version`` are unchanged, it stays the instance's owner (flag 1),
    address and role unchanged; every other account's session version is raised and its flag cleared; the one-time links
    are revoked all the same (the owner's too); one warning line ``Panel restore: the owner's password and sessions are
    kept`` with the stage and the account only. If the account no longer fits the rule at the commit (not an administrator,
    disabled, another address, a second marked account, the address unset), the owner is treated as B5-1j (password closed,
    sessions ended, flag only on it where B5-1j sets it) and the outcome goes back to ``None`` so that the first start gives
    the link. The command line and the app revoke the owner's password and sessions all the same.
(e) The startup step ``owner.assign_restored_owner`` does nothing for ``kept`` (A's function is not even looked up, the state
    is untouched) and the restore guard lets the data go at once (GUARD: green already, since an outcome is recorded).
(f) The whole round on real databases (``confirm`` -> ``apply_pending_restore`` -> ``finish_pending_restore`` ->
    ``assign_restored_owner``): the owner signs in with their old password, a cookie of theirs from before is still valid,
    another account's old cookie is refused. This is the full path of the E2E of the lot: the hosting panel's route cannot be
    driven on a real server without new infrastructure (see the report of the lot), so the real-database round stands for it.

Pure: every data directory under ``tmp_path`` (the helpers of ``test_backup_apply.py``), real databases at the head made once
by alembic in a process of their own, real bcrypt hashes (cost 4). No lane database, no server, no network.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.services.accounts import auth_service, instance_owner, user_service
from backend.app.services.platform.instance_backup import staging
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, STAGE_REPORT_FILE, stage_dir
from backend.app.services.platform.instance_backup.staging import read_report, stage_archive
from backend.test_scripts.test_services import test_backup_apply as base
from backend.test_scripts.test_services import test_backup_owner as owner_cases
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_services import test_session_version as sessions
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = base.pytestmark

# The module fixtures of the neighbours, re-exported (the autouse ones are autouse here too): the real databases and archives,
# the checked copy, the configured data directory that must stay absent, the JWT secret, the boots cache, no inherited block,
# the owner's data directory and module of the startup step.
databases = cases.databases
head_archive = cases.head_archive
checked = base.checked
configured_data_dir = cases.configured_data_dir
secret = sessions.secret
fresh_boots = base.fresh_boots
no_inherited_block = base.no_inherited_block
staging_instance = cases.instance
finished_check = cases.finished_check
data_dir = owner_cases.data_dir
owner = owner_cases.owner

OWNER_MODULE = "backend.app.services.platform.instance_backup.owner"
#: The owner's address as the operator writes it, and as the backup's account stores it (another A-Z case: ``same_email``).
OWNER_EMAIL = base.OWNER_EMAIL
KEPT_ADDRESS = "OWNER.b51@EXAMPLE.com"
#: The line a commit that keeps the owner's password logs (contract «apply»): a warning, the stage and the account only.
KEPT_LINE = "Panel restore: the owner's password and sessions are kept"
#: The accounts of the backup (``cases.ACCOUNTS``): ada (id 4) is the one that holds the owner's address.
ADA_ID = base.ADA["user_id"]
ZOE_ID = base.ZOE["user_id"]
#: A candidate as a check writes it for the account that holds the owner's address, marked as the instance's owner.
HOLDER_ADA = {**base.ADA, "email": KEPT_ADDRESS, "is_instance_owner": True}
HOLDER_ZOE = {**base.ZOE, "email": KEPT_ADDRESS, "is_instance_owner": True}
#: The session versions the backup's accounts carry: the owner's must survive the restore, the others' must not.
OLD_VERSIONS = {"ada_admin": 41, "zoe_admin": 7, "bob_user": 11, "olga_former_admin": 5}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The variables of the owner a developer's shell may carry are removed: each case sets its own."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_ADMIN_") or name in ("LIBREFOLIO_PROFILE", "LIBREFOLIO_MAX_USERS"):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real bcrypt hashes, at the cheapest cost: ``with_backup_passwords`` hashes every account of the backup."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def kept_function() -> Callable[..., Any]:
    function = getattr(base.apply_module(), "keeps_owner", None)
    if function is None:
        pytest.fail("[new] B5-1l: apply.keeps_owner does not exist yet (contract «apply»)", pytrace=False)
    return function


def marks_of(report: Any) -> Any:
    found = getattr(report, "owner_marks", None)
    if found is None:
        pytest.fail("[new] B5-1l: StagingReport has no owner_marks yet (contract «Staging»)", pytrace=False)
    return found


def owner_marks_function() -> Callable[[Path], int]:
    function = getattr(staging, "_owner_marks", None)
    if function is None:
        pytest.fail("[new] B5-1l: staging._owner_marks does not exist yet (contract «Staging»)", pytrace=False)
    return function


def kept_constant() -> str:
    value = getattr(base.apply_module(), "OWNER_OUTCOME_KEPT", None)
    if value is None:
        pytest.fail("[new] B5-1l: apply.OWNER_OUTCOME_KEPT does not exist yet (contract «apply»)", pytrace=False)
    return value


# =============================================================================
# (a) Staging: how many accounts of the copy are marked as the instance's owner
# =============================================================================


def marked_copy(tmp_path: Path, databases: cases.Databases, names: tuple[str, ...], *, column: bool = True) -> Path:
    """A database of a copy at the head with ``cases.OWNER_ACCOUNTS`` and ``names`` marked as the instance's owner, whatever
    their role or state: the unique index is dropped first, as a crafted copy has it (a legitimate backup marks one)."""
    database = cases.owner_check_copy(tmp_path, databases, column=column)
    if names:
        quoted = ", ".join(f"'{name}'" for name in names)
        cases.execute(database, "DROP INDEX ux_users_instance_owner", f"UPDATE users SET is_instance_owner = 1 WHERE username IN ({quoted})")
        assert sorted(name for name, value in base.flags_of(database).items() if value) == sorted(names), f"precondition: the copy marks exactly {names}"
    return database


#: (the accounts marked, the count): any role, active or not.
MARKS = [
    pytest.param((), 0, id="nobody"),
    pytest.param(("ada_admin",), 1, id="an-active-administrator"),
    pytest.param(("bob_user",), 1, id="an-active-plain-user"),
    pytest.param(("olga_former_admin",), 1, id="an-inactive-administrator"),
    pytest.param(("owen_user",), 1, id="the-holder-of-the-owner-s-address"),
    pytest.param(("ada_admin", "bob_user"), 2, id="two-an-administrator-and-a-plain-user"),
    pytest.param(("bob_user", "olga_former_admin", "owen_user"), 3, id="three-none-of-them-a-candidate-but-owen"),
]


@pytest.mark.parametrize(("names", "count"), MARKS)
def test_owner_marks_counts_every_marked_account_of_the_copy_whatever_its_role_or_state(tmp_path, databases, monkeypatch, names, count):
    """(a) B5-1l: ``_owner_marks(database)`` is the number of accounts with ``is_instance_owner = 1``, counted over ALL the
    accounts (an inactive one, a plain user, the one that is no candidate), an ``int``; the copy is only read (its bytes
    are the same after). Red before B5-1l: the function does not exist."""
    print_section("(a) B5-1l _owner_marks")
    cases.owner_email_is(monkeypatch, cases.OWNER_EMAIL)
    function = owner_marks_function()
    database = marked_copy(tmp_path, databases, names)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    found = function(database)
    assert type(found) is int and found == count, f"{names}: {count} marked account(s), not {found!r}"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before, "the copy is only read"
    print_success(f"{names or 'nobody'}: {found}")


def test_owner_marks_of_a_copy_without_the_owner_column_is_zero(tmp_path, databases, monkeypatch):
    """(a) B5-1l: a copy whose ``users`` has no ``is_instance_owner`` column (an old or crafted backup): 0, no error."""
    cases.owner_email_is(monkeypatch, cases.OWNER_EMAIL)
    function = owner_marks_function()
    database = marked_copy(tmp_path, databases, (), column=False)
    assert "is_instance_owner" not in [row[1] for row in cases.rows_of(database, "PRAGMA table_info(users)")], "precondition: the copy has no owner column"
    assert function(database) == 0, "no column, nobody marked"
    print_success("no column: 0")


def test_owner_check_keeps_its_three_values(tmp_path, databases, monkeypatch):
    """(a) GUARD, B5-1l: ``staging._owner_check`` is unchanged: the owner's address, the candidates, the conflicts. The marks
    are counted apart, by ``_owner_marks``."""
    cases.owner_email_is(monkeypatch, cases.OWNER_EMAIL)
    database = cases.owner_check_copy(tmp_path, databases, flagged=("ada_admin",))
    answer = staging._owner_check(database)
    assert isinstance(answer, tuple) and len(answer) == 3, f"three values, not {len(answer)}: {answer!r}"
    address, candidates, conflicts = answer
    assert (address.lower(), sorted(candidate.username for candidate in candidates), conflicts) == (cases.OWNER_EMAIL.lower(), cases.CANDIDATES_WITH_OWNER, []), f"the same answer as before: {answer!r}"
    print_success("_owner_check: three values")


#: (the owner's address, the accounts marked in the backup, the count the report must carry).
REPORT_MARKS = [
    pytest.param(cases.OWNER_EMAIL, (), 0, id="nobody-marked"),
    pytest.param(cases.OWNER_EMAIL, ("ada_admin",), 1, id="an-active-administrator"),
    pytest.param(cases.OWNER_EMAIL, ("bob_user",), 1, id="a-plain-user-is-counted"),
    pytest.param(cases.OWNER_EMAIL, ("olga_former_admin",), 1, id="an-inactive-administrator-is-counted"),
    pytest.param(None, ("ada_admin",), 1, id="owner-address-unset-still-counted"),
]


@pytest.mark.parametrize(("configured", "flagged", "count"), REPORT_MARKS)
def test_the_report_carries_the_owner_marks_keeps_them_in_report_json_and_reads_them_back(staging_instance, databases, tmp_path, monkeypatch, configured, flagged, count):
    """(a) B5-1l: a real check of a backup that marks ``flagged``: ``report.owner_marks`` is ``count``, ``report.json`` holds
    ``owner_marks`` and ``read_report`` gives it back. Red before B5-1l: the report has no such field."""
    print_section("(a) B5-1l StagingReport.owner_marks")
    cases.owner_email_is(monkeypatch, configured)
    archive, _described = cases.backup_with_accounts(tmp_path, databases, cases.OWNER_ACCOUNTS, flagged=flagged)
    report = stage_archive(archive.path, staging_instance.root)
    assert marks_of(report) == count, f"{flagged}: owner_marks {count}"
    written = json.loads((stage_dir(staging_instance.root, report.stage_id) / STAGE_REPORT_FILE).read_text(encoding="utf-8"))
    assert written.get("owner_marks") == count, f"report.json keeps owner_marks {count}: {written.get('owner_marks', '<missing>')}"
    assert marks_of(read_report(staging_instance.root, report.stage_id)) == count, "read_report gives it back"
    print_success(f"{flagged or 'nobody'}: {count}")


@pytest.mark.parametrize(("written", "expected"), [pytest.param(None, 0, id="no-key-a-report-written-before"), pytest.param(2, 2, id="a-value-written")])
def test_a_report_without_owner_marks_reads_zero_and_one_with_it_reads_it(tmp_path, finished_check, written, expected):
    """(a) B5-1l: a ``report.json`` without the key (every report written before B5-1l) still reads, ``owner_marks`` 0; one
    that holds the key reads it."""
    path = cases.a_finished_check_in(tmp_path / "instance", finished_check)
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("owner_marks", None)
    if written is not None:
        record["owner_marks"] = written
    path.write_text(json.dumps(record), encoding="utf-8")
    report = read_report(tmp_path / "instance", finished_check.report.stage_id)
    assert marks_of(report) == expected, f"owner_marks {expected}"
    print_success(f"reads {expected}")


# =============================================================================
# (b) apply.keeps_owner: the truth table of the rule
# =============================================================================


def marked_holder(**changes: Any) -> dict[str, Any]:
    """A candidate that is marked, an active administrator and holds the owner's address, with ``changes``."""
    return {**HOLDER_ADA, **changes}


#: (the candidates, ``owner_marks``, the owner's address, the account kept: ``None`` for nobody).
RULE = [
    pytest.param([marked_holder(), base.ZOE], 1, OWNER_EMAIL, ADA_ID, id="the-one-marked-active-administrator-that-holds-the-address"),
    pytest.param([marked_holder(), base.ZOE], 1, OWNER_EMAIL.upper(), ADA_ID, id="the-address-in-upper-case"),
    pytest.param([marked_holder(), base.ZOE], 1, OWNER_EMAIL.lower(), ADA_ID, id="the-address-in-lower-case"),
    pytest.param([base.ADA, HOLDER_ZOE], 1, OWNER_EMAIL, ZOE_ID, id="the-holder-is-the-first-by-id-not-the-first-by-name"),
    pytest.param([marked_holder(), base.ZOE], 2, OWNER_EMAIL, None, id="none-two-accounts-are-marked-the-other-is-no-candidate"),
    pytest.param([marked_holder(), base.ZOE], 3, OWNER_EMAIL, None, id="none-three-marked"),
    pytest.param([marked_holder(is_active=False), base.ZOE], 1, OWNER_EMAIL, None, id="none-marked-but-inactive"),
    pytest.param([marked_holder(is_superuser=False), base.ZOE], 1, OWNER_EMAIL, None, id="none-marked-but-not-an-administrator"),
    pytest.param([{**base.ADA, "is_instance_owner": True}, base.ZOE], 1, OWNER_EMAIL, None, id="none-marked-but-another-address"),
    pytest.param([{**base.ADA, "email": None, "is_instance_owner": True}, base.ZOE], 1, OWNER_EMAIL, None, id="none-marked-but-no-address"),
    pytest.param([{**base.ZOE, "is_instance_owner": True}, {**base.OWEN, "is_instance_owner": False}], 1, OWNER_EMAIL, None, id="none-marked-and-the-address-is-held-by-someone-else"),
    pytest.param([marked_holder(is_instance_owner=False), base.ZOE], 0, OWNER_EMAIL, None, id="none-nobody-is-marked"),
    pytest.param([marked_holder(is_instance_owner=False), base.ZOE], 1, OWNER_EMAIL, None, id="none-the-one-mark-is-on-an-account-outside-the-candidates"),
    pytest.param([marked_holder(), base.ZOE], 0, OWNER_EMAIL, None, id="none-an-inconsistent-report-zero-marks-and-a-marked-candidate"),
    pytest.param([], 1, OWNER_EMAIL, None, id="none-no-candidate"),
    pytest.param([{**marked_holder(), "email": "Ünal.b51l@example.com"}, base.ZOE], 1, "ünal.b51l@example.com", None, id="none-a-letter-outside-a-z-is-not-folded"),
]


@pytest.mark.parametrize(("rows", "marks", "owner_email", "expected"), RULE)
def test_keeps_owner_is_the_account_of_the_rule_and_nobody_else(rows, marks, owner_email, expected):
    """(b) B5-1l: ``keeps_owner(candidates, owner_marks, owner_email)`` answers the id of the ONE marked account that is an
    active administrator and holds the address (``same_email``: A-Z folded and nothing else), and nobody (``None``) when
    any part of that fails — it needs ``owner_marks == 1``, which is the count over ALL the accounts. It changes nothing it
    is given. Red before B5-1l: the function does not exist."""
    print_section("(b) B5-1l keeps_owner")
    function = kept_function()
    candidates = base.as_candidates(rows)
    before = [candidate.model_dump() for candidate in candidates]
    found = function(candidates, marks, owner_email)
    assert found == expected and (found is None or type(found) is int), f"{marks} mark(s): {expected!r}, not {found!r}"
    assert [candidate.model_dump() for candidate in candidates] == before, "the candidates were not changed"
    print_success(f"{expected!r}")


def test_the_kept_outcome_is_the_word_kept_and_a_state_gains_no_field():
    """(b) B5-1l: ``OWNER_OUTCOME_KEPT == "kept"``. GUARD: ``RestoreState`` gains no field (the outcome is a value of
    ``owner_outcome``), and a state that records ``kept`` reads and writes back as it is."""
    assert kept_constant() == "kept", "the outcome is the word kept"
    apply = base.apply_module()
    assert set(apply.RestoreState.model_fields) == base.STATE_FIELDS, f"no new field in the state: {sorted(set(apply.RestoreState.model_fields) ^ base.STATE_FIELDS)}"
    print_success("kept; no new field")


# =============================================================================
# (c) confirm_restore: the outcome recorded at the confirmation
# =============================================================================


def kept_instance(tmp_path, databases, checked, monkeypatch, *, candidates=None, owner_email=OWNER_EMAIL, profile="managed", **report) -> base.Instance:
    """An instance whose checked copy is the one the rule keeps: ``ada_admin`` marked, an active administrator, holding the
    owner's address (another A-Z case); the report says so as a check writes it (the candidates and ``owner_marks`` 1)."""
    rows = [HOLDER_ADA, base.ZOE] if candidates is None else candidates
    return base.owner_case(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=owner_email, candidates=rows, **{"owner_marks": 1, **report})


#: (the owner's address, the candidates, the account kept).
KEPT_AT_THE_CONFIRMATION = [
    pytest.param(OWNER_EMAIL, [HOLDER_ADA, base.ZOE], ADA_ID, id="the-address-as-written"),
    pytest.param(OWNER_EMAIL.upper(), [HOLDER_ADA, base.ZOE], ADA_ID, id="the-address-in-upper-case"),
    pytest.param(OWNER_EMAIL.lower(), [HOLDER_ADA, base.ZOE], ADA_ID, id="the-address-in-lower-case"),
    pytest.param(OWNER_EMAIL, [base.ADA, HOLDER_ZOE], ZOE_ID, id="the-holder-is-zoe-the-first-by-id"),
]


@pytest.mark.parametrize(("owner_email", "candidates", "expected"), KEPT_AT_THE_CONFIRMATION)
def test_a_panel_confirmation_where_the_rule_holds_records_the_owner_and_the_outcome_kept(tmp_path, databases, checked, monkeypatch, owner_email, candidates, expected):
    """(c) B5-1l: managed, the address set, the report read for it, no conflict, the one marked active administrator holds the
    address: a confirmation via ``panel`` records ``owner_user_id`` = that account and ``owner_outcome`` = ``"kept"`` at once,
    in the state returned, in ``restore.json`` and in what ``read_restore`` reads; ``pending``; no warning about the owner,
    no address or name in the log. Red before B5-1l: the outcome stayed ``None``."""
    print_section("(c) B5-1l the panel keeps the owner")
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, candidates=candidates, owner_email=owner_email)
    state, events = base.confirmed_via_with_logs(apply, instance, "panel")
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("pending", "panel", expected, "kept"), f"[new] B5-1l: the owner {expected}, kept: {state}"
    assert base.on_disk_owner(instance.root) == (expected, "kept"), f"restore.json records it: {base.on_disk_owner(instance.root)}"
    read_back = apply.read_restore(instance.root)
    assert (read_back.owner_user_id, read_back.owner_outcome) == (expected, "kept"), "read_restore reads it back"
    assert base.owner_warnings(events) == [], f"keeping the owner is no warning: {base.logged(events)}"
    base.nothing_secret_logged(events, owner_email, KEPT_ADDRESS, *(row["email"] for row in candidates), *(row["username"] for row in candidates))
    print_success(f"owner {expected} kept")


#: (the candidates, ``owner_marks`` — ``base.ABSENT``: the key left out —, what B5-1j does with them: the owner picked and the outcome).
NOT_KEPT = [
    pytest.param([HOLDER_ADA, base.ZOE], 2, (ADA_ID, None), id="two-accounts-are-marked"),
    pytest.param([marked_holder(is_active=False), base.ZOE], 1, (ADA_ID, None), id="the-holder-is-inactive"),
    pytest.param([marked_holder(is_superuser=False), base.ZOE], 1, (ADA_ID, None), id="the-holder-is-not-an-administrator"),
    pytest.param([{**base.ADA, "is_instance_owner": True}, base.ZOE], 1, (ADA_ID, None), id="the-marked-administrator-has-another-address"),
    pytest.param([{**base.ZOE, "is_instance_owner": True}, base.OWEN], 1, (base.OWEN["user_id"], None), id="the-address-is-held-by-someone-else"),
    pytest.param([marked_holder(is_instance_owner=False), base.ZOE], 0, (ADA_ID, None), id="nobody-is-marked"),
    pytest.param([marked_holder(is_instance_owner=False), base.ZOE], 1, (ADA_ID, None), id="the-one-mark-is-outside-the-candidates"),
    pytest.param([HOLDER_ADA, base.ZOE], 0, (ADA_ID, None), id="an-inconsistent-report-zero-marks"),
    pytest.param([HOLDER_ADA, base.ZOE], base.ABSENT, (ADA_ID, None), id="a-report-written-before-has-no-owner-marks"),
    pytest.param([base.ADA, base.ZOE], 0, (None, "none"), id="nobody-can-be-picked"),
]


@pytest.mark.parametrize(("candidates", "marks", "expected"), NOT_KEPT)
def test_a_panel_confirmation_where_a_condition_is_missing_does_what_b5_1j_did(tmp_path, databases, checked, monkeypatch, candidates, marks, expected):
    """(c) GUARD, B5-1l: when the rule does not hold, a panel confirmation records exactly what B5-1j recorded — the picked
    account (``pick_owner``), the outcome ``None`` or ``none`` — and never ``kept``. The sibling test above is the same copy
    with the condition met."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, candidates=candidates, owner_marks=marks)
    state, _events = base.confirmed_via_with_logs(apply, instance, "panel")
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", *expected), f"B5-1j's pick, not kept: {state}"
    assert base.on_disk_owner(instance.root) == expected, f"restore.json: {base.on_disk_owner(instance.root)}"
    print_success(f"{expected}")


def test_the_same_copy_confirmed_from_the_command_line_is_never_kept(tmp_path, databases, checked, monkeypatch):
    """(c) GUARD, B5-1l: the copy the rule keeps (marked, active administrator, holds the address, one mark), confirmed via the
    command line: B5-1j's pick, outcome ``None``. The command line revokes the owner's password all the same."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch)
    state, _events = base.confirmed_via_with_logs(apply, instance, "cli")
    assert (state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("cli", ADA_ID, None), f"cli: picked, not kept: {state}"
    print_success("cli: not kept")


def test_the_same_copy_confirmed_by_an_administrator_with_the_owner_chosen_is_never_kept(tmp_path, databases, checked, monkeypatch):
    """(c) GUARD, B5-1l: the copy the rule keeps, confirmed from the app (``admin``) with the owner chosen — the holder is the
    forced choice —: ``owner_user_id`` is the choice and the outcome ``None``. The app revokes the owner's password all the
    same."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=base.CONFIRMED_BY, confirmed_via="admin", owner_user_id=ADA_ID, data_dir=instance.root, now=instance.confirm_at)
    assert (state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("admin", ADA_ID, None), f"admin: chosen, not kept: {state}"
    print_success("admin: not kept")


#: (the profile, the owner's address): where the owner is no concept of the instance.
NO_OWNER_CONCEPT = [
    pytest.param("selfhosted", OWNER_EMAIL, id="selfhosted"),
    pytest.param("managed", None, id="managed-no-address"),
]


@pytest.mark.parametrize(("profile", "owner_email"), NO_OWNER_CONCEPT)
def test_a_self_hosted_or_addressless_panel_confirmation_keeps_nothing(tmp_path, databases, checked, monkeypatch, profile, owner_email):
    """(c) GUARD, B5-1l: self-hosted, or managed without ``LIBREFOLIO_ADMIN_EMAIL``: the copy the rule would keep is confirmed
    via the panel with no owner and no outcome, as before."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=owner_email)
    state, events = base.confirmed_via_with_logs(apply, instance, "panel")
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", None, None), f"{profile}: no owner, no outcome: {state}"
    assert base.owner_warnings(events) == [], f"no warning about an owner: {base.logged(events)}"
    print_success(f"{profile}: nothing kept")


@pytest.mark.parametrize("conflicts", [["duplicate_email"], ["address_is_a_username"], ["duplicate_username", "pending_administrator"]], ids=["duplicate_email", "address_is_a_username", "two-codes"])
def test_a_panel_confirmation_with_owner_conflicts_is_refused_before_anything_is_kept(tmp_path, databases, checked, monkeypatch, conflicts):
    """(c) GUARD, B5-1l: the report has owner conflicts: ``owner_conflict`` first, as today, whatever the rule would keep;
    nothing written."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, owner_conflicts=conflicts)
    error = base.refused_via(apply, instance, "panel")
    assert (type(error).__name__, error.code) == ("RestoreOwnerConflictError", "owner_conflict"), f"owner_conflict, not {type(error).__name__} {error.code}: {error}"
    print_success("owner_conflict first")


@pytest.mark.parametrize("checked_with", base.STALE_CHECKS)
def test_a_panel_confirmation_of_a_check_made_for_another_address_is_outdated_before_anything_is_kept(tmp_path, databases, checked, monkeypatch, checked_with):
    """(c) GUARD, B5-1l: the report was read for another address, or for none, or before the addendum: ``restore_stage_outdated``
    as today — the candidates and the marks were read for an address that is not the owner's; nothing written."""
    apply = base.apply_module()
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, owner_email_checked=checked_with)
    error = base.refused_via(apply, instance, "panel")
    assert error.code == "restore_stage_outdated", f"restore_stage_outdated, not {error.code}: {error}"
    print_success("restore_stage_outdated first")


# =============================================================================
# (d) The commit on a real restored database
# =============================================================================


def plant_links(database: Path, *user_ids: int) -> list[str]:
    """A live password-reset link for each account, whoever prepared the backup may have written them: their hashes."""
    hashes = []
    with closing(sqlite3.connect(database)) as conn, conn:
        for user_id in user_ids:
            token_hash = hashlib.sha256(f"b51l-planted-{user_id}".encode()).hexdigest()
            conn.execute(
                "INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_at, expires_at) VALUES ('password_reset', ?, ?, ?, 0, '2026-10-20 10:00:00.000000', '2126-10-20 10:00:00.000000')",
                (token_hash, user_id, "planted@other-instance.example.net"),
            )
            hashes.append(token_hash)
    return hashes


def revoked_links(database: Path, token_hashes: list[str]) -> dict[str, bool]:
    """Whether each planted link is revoked, by its hash."""
    quoted = ", ".join(f"'{value}'" for value in token_hashes)
    return {value: revoked is not None for value, revoked in cases.rows_of(database, f"SELECT token_hash, revoked_at FROM account_tokens WHERE token_hash IN ({quoted})")}


class Scene:
    """A kept-owner restore up to the commit: the instance, the backup's password hashes, its accounts before, the links."""

    def __init__(self, instance: base.Instance, hashes: dict[str, str], before: dict[str, dict[str, Any]], links: list[str]) -> None:
        self.instance = instance
        self.hashes = hashes
        self.before = before
        self.links = links

    @property
    def database(self) -> Path:
        return self.instance.root / DATABASE_ENTRY


def scene(tmp_path, databases, checked, monkeypatch, *, candidates=None, **report) -> Scene:
    """The instance of ``kept_instance`` whose copy really is what the report says: ``ada_admin`` marked as the instance's
    owner and holding the owner's address, every account with a real bcrypt hash of the backup's password, the session
    versions of ``OLD_VERSIONS``, a live reset link for ada and for zoe."""
    instance = kept_instance(tmp_path, databases, checked, monkeypatch, candidates=candidates, **report)
    database = instance.copy / DATABASE_ENTRY
    cases.execute(database, f"UPDATE users SET email = '{KEPT_ADDRESS}', is_instance_owner = 1 WHERE username = 'ada_admin'")
    hashes = base.with_backup_passwords(database)
    base.set_versions(database, OLD_VERSIONS)
    links = plant_links(database, ADA_ID, ZOE_ID)
    before = base.accounts_of(database)
    assert sorted(name for name, value in base.flags_of(database).items() if value) == ["ada_admin"], "precondition: the backup marks ada only"
    assert base.versions_of(database) == OLD_VERSIONS, "precondition: the backup's session versions"
    return Scene(instance, hashes, before, links)


def run_restore(apply: Any, what: Scene, *, via: str = "panel", owner_user_id: int | None = None, before_apply: Callable[[], None] | None = None, before_commit: Callable[[], None] | None = None) -> tuple[Any, Any, list[dict[str, Any]]]:
    """The restore confirmed via ``via``, applied and committed as a start does: the state the confirmation returned, the
    committed state, and what the commit logged (its canary left out)."""
    instance = what.instance
    by = base.CONFIRMED_BY if via == "admin" else via
    extra = {} if owner_user_id is None else {"owner_user_id": owner_user_id}
    confirmed = apply.confirm_restore(instance.stage_id, confirmed_by=by, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at, **extra)
    if before_apply is not None:
        before_apply()
    boot = base.never_ran(apply)
    apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    if before_commit is not None:
        before_commit()
    with base.logs() as events:
        state = apply.finish_pending_restore(instance.root, boot=boot, now=instance.committed_at)
    return confirmed, state, [event for event in events if event.get("event") != base.LOG_CANARY]


def kept_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("event") == KEPT_LINE]


def test_the_commit_of_a_kept_owner_keeps_their_password_and_sessions_and_ends_every_other(tmp_path, databases, checked, monkeypatch):
    """(d) B5-1l, end to end up to the commit: a restore via the panel whose confirmation kept the owner. At the commit
    ``ada_admin`` (the owner) is untouched — ``hashed_password`` and ``session_version`` as the backup held them (the backup's
    password still opens it), address, role and state, and ``is_instance_owner`` still 1 — her whole row is as it was; every
    other account's session version is the restore's and its flag is 0; the one-time links are revoked, ada's and zoe's; the
    restore is ``committed`` with ``owner_outcome`` ``kept`` and nothing pending for the startup step or the guard. One line
    ``Panel restore: the owner's password and sessions are kept`` (a warning) with the stage and the account only. Red before
    B5-1l: the commit closed the owner's password and ended their sessions."""
    print_section("(d) B5-1l the commit keeps the owner")
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    confirmed, state, events = run_restore(apply, what)
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, "kept"), f"[new] B5-1l: confirmed as kept: {confirmed}"
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", ADA_ID, "kept"), f"committed, the outcome still kept: {state}"
    after = base.accounts_of(what.database)
    assert after["ada_admin"] == what.before["ada_admin"], f"the owner's row is untouched: {sorted(key for key in what.before['ada_admin'] if after['ada_admin'][key] != what.before['ada_admin'][key])}"
    assert auth_service.verify_password(base.BACKUP_PASSWORD, after["ada_admin"]["hashed_password"]), "the owner signs in with their old password"
    assert (after["ada_admin"]["session_version"], after["ada_admin"][base.OWNER_COLUMN]) == (OLD_VERSIONS["ada_admin"], 1), "their session version and their flag stay"
    others = {name: row for name, row in after.items() if name != "ada_admin"}
    assert {row["session_version"] for row in others.values()} == {state.session_version} and state.session_version > max(OLD_VERSIONS.values()), f"every other account gets the restore's session version: {state.session_version}"
    assert {row[base.OWNER_COLUMN] for row in others.values()} == {0}, "no other account is the owner"
    base.untouched_but(what.before, after, "ada_admin")
    assert revoked_links(what.database, what.links) == dict.fromkeys(what.links, True), "the one-time links are revoked, the owner's too"
    assert (apply.owner_assignment_problem(what.instance.root), apply.owner_pending(what.instance.root)) == (None, None), "nothing keeps the guard or the startup step waiting"
    lines = kept_lines(events)
    assert len(lines) == 1, f"[new] B5-1l: one line «{KEPT_LINE}»: {base.logged(events)}"
    assert (lines[0].get("log_level"), set(lines[0]) - {"event", "log_level"}) == ("warning", {"stage_id", "user_id"}), f"a warning with the stage and the account only: {lines[0]}"
    assert (lines[0]["stage_id"], lines[0]["user_id"]) == (what.instance.stage_id, ADA_ID), f"it names this restore and this account: {lines[0]}"
    assert base.owner_line(events, what.instance.stage_id, ADA_ID) == [], f"B5-1j's «closed» line is not logged: {base.logged(events)}"
    base.nothing_secret_logged(events, OWNER_EMAIL, base.configured_address(), KEPT_ADDRESS, base.BACKUP_PASSWORD, *what.hashes.values(), *(row["email"] for row in what.before.values()), *what.before)
    print_success("the owner untouched, the others ended, one line")


def test_the_commit_of_a_kept_owner_ends_every_session_of_the_others_whatever_the_owner_flag_of_the_backup(tmp_path, databases, checked, monkeypatch):
    """(d) B5-1l: the commit keeps the owner's row apart from the others in the SAME transaction: even with the clock behind
    the largest session version the backup holds (a restore on top of a later history), the owner keeps theirs and the rest
    end strictly above everything either database held."""
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    ahead = base.millis(what.instance.committed_at) + 5000
    base.set_versions(what.instance.copy / DATABASE_ENTRY, {"bob_user": ahead})
    _confirmed, state, _events = run_restore(apply, what)
    after = base.accounts_of(what.database)
    assert state.session_version == ahead + 1, f"the others end above the largest version either database held: {state.session_version}"
    assert (after["ada_admin"]["session_version"], {row["session_version"] for name, row in after.items() if name != "ada_admin"}) == (OLD_VERSIONS["ada_admin"], {ahead + 1}), f"the owner keeps theirs, the rest {ahead + 1}"
    print_success("the others above both histories, the owner kept")


@pytest.mark.parametrize("via", ["cli", "admin"])
def test_the_command_line_and_the_app_revoke_the_owner_s_password_and_sessions_all_the_same(tmp_path, databases, checked, monkeypatch, via):
    """(d) GUARD, B5-1l: the SAME copy restored via the command line, or via the app with the owner chosen: B5-1j to the letter.
    The owner's password is closed (a real hash the backup's password does not open), every account — hers too — gets the
    restore's session version, the flag stays on her alone; the outcome stays ``None`` for the first start; the «kept» line is
    not logged."""
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    confirmed, state, events = run_restore(apply, what, via=via, owner_user_id=ADA_ID if via == "admin" else None)
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, None), f"via {via}: picked, not kept: {confirmed}"
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", ADA_ID, None), f"via {via}: committed, the first start still to give the link: {state}"
    after = base.accounts_of(what.database)
    base.closed(after["ada_admin"], what.hashes["ada_admin"])
    assert {row["session_version"] for row in after.values()} == {state.session_version}, "every session ended, the owner's too"
    assert {name: row[base.OWNER_COLUMN] for name, row in after.items()} == {name: int(name == "ada_admin") for name in after}, "she is the only owner"
    assert kept_lines(events) == [], f"nothing kept: {base.logged(events)}"
    assert apply.owner_pending(what.instance.root) == (what.instance.stage_id, ADA_ID), "the startup step has the account to give"
    print_success(f"via {via}: revoked as before")


# --- the re-check at the commit ------------------------------------------------------


def second_marked_account(database: Path) -> None:
    """A second account marked as the owner, as a copy without the unique index has it."""
    cases.execute(database, "DROP INDEX ux_users_instance_owner", "UPDATE users SET is_instance_owner = 1 WHERE username = 'zoe_admin'")


#: (what changes in the copy after the confirmation — the report still says the rule holds —, the case's id).
CHANGED_AFTER_THE_CONFIRMATION = [
    pytest.param("UPDATE users SET is_superuser = 0 WHERE username = 'ada_admin'", id="the-owner-is-no-longer-an-administrator"),
    pytest.param("UPDATE users SET is_active = 0 WHERE username = 'ada_admin'", id="the-owner-is-disabled"),
    pytest.param("UPDATE users SET email = 'ada.moved.b51l@example.com' WHERE username = 'ada_admin'", id="the-owner-has-another-address"),
    pytest.param(second_marked_account, id="a-second-account-is-marked"),
]


@pytest.mark.parametrize("change", CHANGED_AFTER_THE_CONFIRMATION)
def test_when_the_account_no_longer_fits_the_rule_at_the_commit_the_owner_is_treated_as_b5_1j_and_the_outcome_goes_back_to_none(tmp_path, databases, checked, monkeypatch, change):
    """(d) B5-1l: the confirmation said ``kept`` but the account in the copy was changed after it (not an administrator,
    disabled, another address, a second marked account): the commit re-checks, and the owner is treated as B5-1j —
    the password closed (a real hash the backup's password does not open), the account an active administrator with the
    owner's address and the only one flagged, every session ended, the link to the first start — and ``owner_outcome`` goes
    back to ``None`` so that the first start gives the owner the link; nothing is logged as kept; the owner is pending for
    the startup step and the guard. Red before B5-1l: the barrier — the confirmation did not say ``kept``."""
    print_section("(d) B5-1l the re-check at the commit")
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    copy_database = what.instance.copy / DATABASE_ENTRY

    def changed() -> None:
        if callable(change):
            change(copy_database)
        else:
            cases.execute(copy_database, change)

    confirmed, state, events = run_restore(apply, what, before_apply=changed)
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, "kept"), f"[new] B5-1l: barrier: the confirmation kept the owner: {confirmed}"
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", ADA_ID, None), f"[new] B5-1l: committed, the outcome back to None: {state}"
    after = base.accounts_of(what.database)
    base.closed(after["ada_admin"], what.hashes["ada_admin"])
    ada = after["ada_admin"]
    assert (ada["email"], ada["is_superuser"], ada["is_active"]) == (base.configured_address(), 1, 1), "the owner's address, an active administrator"
    assert {name: row[base.OWNER_COLUMN] for name, row in after.items()} == {name: int(name == "ada_admin") for name in after}, f"{base.OWNER_COLUMN}: the owner only: {base.flags_of(what.database)}"
    assert {row["session_version"] for row in after.values()} == {state.session_version}, "every session ended, the owner's too"
    assert kept_lines(events) == [], f"not logged as kept: {base.logged(events)}"
    assert base.owner_line(events, what.instance.stage_id, ADA_ID) == [True], f"B5-1j's line: the account closed and assigned: {base.logged(events)}"
    assert (apply.owner_assignment_problem(what.instance.root), apply.owner_pending(what.instance.root)) == ("pending", (what.instance.stage_id, ADA_ID)), "the first start gives the link"
    assert revoked_links(what.database, what.links) == dict.fromkeys(what.links, True), "the links are revoked all the same"
    print_success("re-check failed: B5-1j, outcome None")


def test_when_the_owner_s_address_is_unset_at_the_commit_the_owner_is_treated_as_b5_1j(tmp_path, databases, checked, monkeypatch):
    """(d) B5-1l: the confirmation kept the owner but ``LIBREFOLIO_ADMIN_EMAIL`` is unset when the commit runs: nobody holds
    «the address» any more, so the re-check fails and B5-1j's treatment applies without an address — the password closed,
    every session ended, no account flagged, the address and role as the backup held them — and the outcome goes back to
    ``None``."""
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    confirmed, state, events = run_restore(apply, what, before_commit=lambda: base.owner_email_is(monkeypatch, None))
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, "kept"), f"[new] B5-1l: barrier: the confirmation kept the owner: {confirmed}"
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", ADA_ID, None), f"[new] B5-1l: the outcome back to None: {state}"
    after = base.accounts_of(what.database)
    base.closed(after["ada_admin"], what.hashes["ada_admin"])
    assert after["ada_admin"]["email"] == what.before["ada_admin"]["email"], "no address to give: hers stays"
    assert set(base.flags_of(what.database).values()) == {0}, "nobody is the owner: the first start derives it"
    assert {row["session_version"] for row in after.values()} == {state.session_version}, "every session ended"
    assert kept_lines(events) == [], f"not logged as kept: {base.logged(events)}"
    print_success("address unset at the commit: B5-1j")


def test_close_the_way_in_takes_kept_owner_user_id_and_defaults_to_none():
    """(d) B5-1l: ``_close_the_way_in`` gains the keyword ``kept_owner_user_id`` (default ``None``: every caller of before is
    unchanged), beside ``owner_user_id``. Red before B5-1l: the keyword does not exist."""
    apply = base.apply_module()
    parameter = inspect.signature(apply._close_the_way_in).parameters.get("kept_owner_user_id")
    if parameter is None:
        pytest.fail("[new] B5-1l: apply._close_the_way_in() takes no kept_owner_user_id yet (contract «apply»)", pytrace=False)
    assert parameter.default is None and parameter.kind is parameter.KEYWORD_ONLY, f"a keyword with the default None: {parameter}"
    assert "owner_user_id" in inspect.signature(apply._close_the_way_in).parameters, "owner_user_id stays"
    print_success("kept_owner_user_id: keyword, None")


# =============================================================================
# (e) The startup step and the guard
# =============================================================================


def spy_on_a(monkeypatch: pytest.MonkeyPatch, owner: ModuleType) -> owner_cases.FakeA:
    """``owner._assign_owner`` replaced by a fake of A's function that records each call, and counts each lookup."""
    fake = owner_cases.FakeA(outcome=owner_cases.FakeOutcome.SENT)
    owner_cases.use_fake(monkeypatch, owner, fake)
    return fake


@pytest.mark.asyncio
async def test_the_startup_step_does_nothing_for_a_kept_owner_and_the_guard_lets_the_data_go(data_dir, owner, monkeypatch):
    """(e) GUARD, B5-1l: a committed restore via the panel whose outcome is ``kept``, with its owner named: the step
    ``assign_restored_owner`` calls nothing of A's, logs no assignment, and leaves ``restore.json`` byte for byte; the guard's
    hook finds nothing pending and ``owner_pending`` is ``None``. Green already, since an outcome is recorded: the lot must
    keep it so."""
    print_section("(e) B5-1l the startup step: kept")
    fake = spy_on_a(monkeypatch, owner)
    before = owner_cases.write_state(data_dir.root, confirmed_via="panel", owner_user_id=data_dir.owner_id, owner_outcome="kept")
    returned, raised, events = await owner_cases.assigned(owner, data_dir.root)
    assert raised is None and returned is None, f"the step does nothing: {returned!r}, {raised!r}"
    assert fake.calls == [], f"A's function is not called: {fake.calls}"
    assert owner_cases.state_bytes(data_dir.root) == before, "restore.json as it was"
    assert [event for event in events if "owner" in str(event.get("event")).lower()] == [], f"no log about an assignment: {base.logged(events)}"
    apply = base.apply_module()
    assert (apply.owner_assignment_problem(data_dir.root), apply.owner_pending(data_dir.root)) == (None, None), "the guard lets the data go, nothing is pending"
    print_success("kept: nothing runs")


@pytest.mark.asyncio
async def test_the_startup_step_still_gives_the_link_to_an_owner_whose_outcome_went_back_to_none(data_dir, owner, monkeypatch):
    """(e) GUARD, B5-1l: the same restore with no outcome (what the commit leaves when the re-check failed): the step calls A
    once with the account and records the outcome — the link goes to the owner."""
    fake = spy_on_a(monkeypatch, owner)
    owner_cases.write_state(data_dir.root, confirmed_via="panel", owner_user_id=data_dir.owner_id, owner_outcome=None)
    returned, raised, _events = await owner_cases.assigned(owner, data_dir.root)
    assert raised is None and [call["user_id"] for call in fake.calls] == [data_dir.owner_id], f"A called once with the account: {fake.calls}"
    assert returned is not None and returned.owner_outcome == "sent", f"the outcome recorded: {returned}"
    print_success("outcome None: the link goes")


# =============================================================================
# (f) The whole round on real databases
# =============================================================================


async def sign_in(engine: Any, user_id: int, version: int) -> tuple[int, Any] | None:
    """What a cookie of ``user_id`` issued at ``version`` gets from the server: ``None`` when it signs in, else the refusal
    (status, detail)."""
    outcome = await sessions._current_user(engine, sessions._cookie(user_id, version))
    return None if sessions._signed_in_as(outcome, user_id) else (sessions._refusal(outcome) or ("not the user", sessions._describe(outcome)))


@pytest.mark.asyncio
async def test_after_the_restart_the_owner_signs_in_with_their_old_password_and_cookie_and_everybody_else_is_refused(tmp_path, databases, checked, monkeypatch):
    """(f) B5-1l, the full path of the lot on real databases (the E2E stand-in): a restore via the panel, confirmed, applied
    and committed as the lifecycle does, then the startup step ``assign_restored_owner``. The step runs nothing (A's function
    is never called, ``restore.json`` is as the commit left it, ``kept``). Then: the owner's old password opens the owner's
    account (a real bcrypt check of the hash the backup held); a cookie of the owner's issued at the version the backup held
    still signs in (``get_current_user`` on the restored database); the old cookies of two other accounts are refused
    («Session expired or invalid»); a login of another account after the restore signs in. Red before B5-1l: the owner's
    cookie was refused."""
    print_section("(f) B5-1l the round: password, cookie, others refused")
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    confirmed, state, _events = run_restore(apply, what)
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, "kept"), f"[new] B5-1l: barrier: the confirmation kept the owner: {confirmed}"
    owner_module = importlib.import_module(OWNER_MODULE)
    fake = spy_on_a(monkeypatch, owner_module)
    state_before = base.state_file(what.instance.root).read_bytes()
    returned = await owner_module.assign_restored_owner(what.instance.root)
    assert returned is None and fake.calls == [], f"the first start gives nobody a link: {returned!r}, {fake.calls}"
    assert base.state_file(what.instance.root).read_bytes() == state_before, "restore.json as the commit left it"
    assert apply.read_restore(what.instance.root).owner_outcome == "kept", f"[new] B5-1l: the outcome stays kept: {state}"
    after = base.accounts_of(what.database)
    assert auth_service.verify_password(base.BACKUP_PASSWORD, after["ada_admin"]["hashed_password"]), "the owner signs in with their old password"
    engine = create_async_engine(f"sqlite+aiosqlite:///{what.database}", poolclass=NullPool)
    try:
        assert await sign_in(engine, ADA_ID, OLD_VERSIONS["ada_admin"]) is None, "[new] B5-1l: the owner's cookie from before the restore is still valid"
        for name, user_id in (("zoe_admin", ZOE_ID), ("bob_user", base.BOB_ID)):
            refused = await sign_in(engine, user_id, OLD_VERSIONS[name])
            assert refused == sessions.SESSION_EXPIRED, f"{name}: the old cookie is refused: {refused}"
        assert await sign_in(engine, ZOE_ID, state.session_version) is None, "a login of another account after the restore signs in"
    finally:
        await engine.dispose()
    print_success("the owner's password and cookie stand; the others are refused")


@pytest.mark.asyncio
async def test_after_a_failed_recheck_the_owner_loses_the_password_and_cookie_and_the_first_start_gives_the_link(tmp_path, databases, checked, monkeypatch):
    """(f) B5-1l: the round when the account stops fitting the rule between the confirmation and the commit (it was disabled
    in the copy): the owner's old password and old cookie are refused as B5-1j has it, and ``assign_restored_owner`` calls A
    once with the account and records the outcome — the link goes to the owner's address."""
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    copy_database = what.instance.copy / DATABASE_ENTRY
    confirmed, state, _events = run_restore(apply, what, before_apply=lambda: cases.execute(copy_database, "UPDATE users SET is_active = 0 WHERE username = 'ada_admin'"))
    assert confirmed.owner_outcome == "kept", f"[new] B5-1l: barrier: the confirmation kept the owner: {confirmed}"
    owner_module = importlib.import_module(OWNER_MODULE)
    fake = spy_on_a(monkeypatch, owner_module)
    returned = await owner_module.assign_restored_owner(what.instance.root)
    assert [call["user_id"] for call in fake.calls] == [ADA_ID], f"A is called once with the owner's account: {fake.calls}"
    assert returned is not None and returned.owner_outcome == "sent", f"the outcome recorded: {returned}"
    after = base.accounts_of(what.database)
    base.closed(after["ada_admin"], what.hashes["ada_admin"])
    engine = create_async_engine(f"sqlite+aiosqlite:///{what.database}", poolclass=NullPool)
    try:
        refused = await sign_in(engine, ADA_ID, OLD_VERSIONS["ada_admin"])
        assert refused == sessions.SESSION_EXPIRED, f"the owner's old cookie is refused: {refused}"
    finally:
        await engine.dispose()
    assert state.owner_outcome is None, "the commit left the outcome for the first start"
    print_success("failed re-check: refused, the first start gives the link")


# =============================================================================
# (g) The address fold: the confirmation and the commit fold it the same way (A's review of the lot)
# =============================================================================

#: (the address the account stores, the owner's address, whether both folds see the same address): A–Z folds, nothing else.
FOLDS = [
    pytest.param("OWNER.b51@EXAMPLE.com", "owner.b51@example.com", True, id="a-to-z-in-upper-case"),
    pytest.param("owner.b51@example.com", "OWNER.B51@Example.COM", True, id="a-to-z-in-another-case"),
    pytest.param("Ünal.b51l@example.com", "ünal.b51l@example.com", False, id="a-capital-umlaut-is-not-its-small-one"),
    pytest.param("ÉLAN.b51l@example.com", "élan.b51l@example.com", False, id="a-capital-e-acute-is-not-its-small-one"),
    pytest.param("élan.b51l@example.com", "élan.b51l@example.com", True, id="the-same-non-ascii-address-is-the-same"),
]


@pytest.mark.parametrize(("stored", "variable", "same"), FOLDS)
def test_the_confirmation_and_the_commit_see_the_same_address_whatever_the_case(tmp_path, monkeypatch, stored, variable, same):
    """(g) B5-1l: the confirmation compares addresses with ``user_service.same_email`` and the commit's re-check with SQLite's
    ``lower()``. Both fold A-Z and nothing else, so the account the confirmation keeps is the one the commit keeps: an address
    in another A-Z case is kept by both, ``É`` against ``é`` by neither (it falls back on B5-1j at the confirmation). Guards
    the symmetry, so that it does not depend on the case of the data."""
    apply = base.apply_module()
    candidate = base.as_candidates([{**HOLDER_ADA, "email": stored}, base.ZOE])
    at_the_confirmation = apply.keeps_owner(candidate, 1, variable) == ADA_ID
    database = tmp_path / "copy.db"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, is_active INTEGER, is_superuser INTEGER, is_instance_owner INTEGER)")
        conn.execute("INSERT INTO users VALUES (?, ?, 1, 1, 1)", (ADA_ID, stored))
    monkeypatch.setattr("backend.app.services.platform.instance_backup.owner.configured_owner_email", lambda: variable)
    at_the_commit = apply._kept_owner_valid(database, ADA_ID)
    assert at_the_confirmation == at_the_commit == same, f"{stored!r} against {variable!r}: the confirmation {at_the_confirmation}, the commit {at_the_commit}, expected {same}"
    print_success(f"same address: {same}")


# =============================================================================
# (h) A's owner sync on the restored database (A's review of the lot)
# =============================================================================


def tokens_by_purpose(database: Path) -> dict[str, int]:
    with closing(sqlite3.connect(database)) as conn:
        return dict(conn.execute("SELECT purpose, COUNT(*) FROM account_tokens GROUP BY purpose").fetchall())


@pytest.mark.asyncio
async def test_after_a_kept_restore_the_owner_sync_finds_the_same_owner_and_changes_nothing(tmp_path, databases, checked, monkeypatch):
    """(h) B5-1l: after a kept restore (confirmed, applied, committed, the startup step done) workstream A's ``owner-sync``
    (``startup_owner_sync``) runs on the restored database as the next step of the start: it reads ``ada_admin`` as the
    recorded owner (the flag the commit kept), finds the address equal to ``LIBREFOLIO_ADMIN_EMAIL`` (another A-Z case) and
    answers ``unchanged``: no ``email_change`` link is created, nothing is delivered, and ``account_protection`` protects the
    account as the paying administrator. The account is the same one, with its password."""
    apply = base.apply_module()
    what = scene(tmp_path, databases, checked, monkeypatch)
    confirmed, _state, _events = run_restore(apply, what)
    assert (confirmed.owner_user_id, confirmed.owner_outcome) == (ADA_ID, "kept"), f"[new] B5-1l: barrier: the confirmation kept the owner: {confirmed}"
    monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)  # the sync notes the owner: restored after
    delivered: list[Any] = []

    async def deliver(*args: Any, **kwargs: Any) -> None:
        delivered.append((args, kwargs))

    monkeypatch.setattr(instance_owner, "deliver_owner_change_link", deliver)
    before = tokens_by_purpose(what.database)
    engine = create_async_engine(f"sqlite+aiosqlite:///{what.database}", poolclass=NullPool)
    try:
        result = await instance_owner.startup_owner_sync(engine)
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

        from backend.app.db.models import User  # noqa: PLC0415

        async with AsyncSession(engine, expire_on_commit=False) as session:
            owner_account = await session.get(User, ADA_ID)
            protection = user_service.account_protection(owner_account)
    finally:
        await engine.dispose()
    assert (result.action, result.user_id) == (instance_owner.OwnerSyncAction.UNCHANGED, ADA_ID), f"the sync reads the same owner and changes nothing: {result}"
    assert getattr(result, "link_token", None) is None and delivered == [], f"no link, nothing delivered: {delivered}"
    after = tokens_by_purpose(what.database)
    assert after.get("email_change", 0) == 0 and after.get("email_change", 0) <= before.get("email_change", 0), f"no email_change link: {before} -> {after}"
    assert protection == user_service.PAYING_ADMINISTRATOR, f"the owner is protected as the paying administrator: {protection!r}"
    assert auth_service.verify_password(base.BACKUP_PASSWORD, base.accounts_of(what.database)["ada_admin"]["hashed_password"]), "the owner keeps the password"
    print_success("owner sync: unchanged, protected")
