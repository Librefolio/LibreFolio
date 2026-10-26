"""
A backup with more active accounts than ``LIBREFOLIO_MAX_USERS``: the check only WARNS, the confirmation never refuses
(workstream B, lot B5-1k2; contract ``B-5-1k2-contratto.md``). Selector: ``services backup-users-limit``.

The reduced design replaces B5-1k (delete the surplus accounts, archived in ``archive/b5-1k-delete-design``): the accounts
over the limit are deactivated at the first sign-in by the administrator's choice (A5-7), so a restore refuses nothing for
too many users and keeps no new state. It says so, before the confirmation, in the report.

Written RED, before B5-1k2: every test of (a) fails on a field the report does not have yet, named
``[new] B5-1k2: ...``. The tests of (b) are guards of a refusal that must never come: each one first proves, through
``new_field``, that the report of the scene IS over the limit (so it is red today for that field, and a real guard once the
field exists).

(a) The check (``staging.StagingReport``): ``users_active`` (the copy's active accounts, plus one when the instance is
    ``managed``, ``LIBREFOLIO_ADMIN_EMAIL`` is set and the account that holds that address exists and is INACTIVE: the
    restore activates it, A5-2; always computed, with or without a limit), ``users_limit`` (``config.accounts.max_users()``:
    the number, ``None`` when unset or invalid: an invalid value never fires the warning), ``users_over_limit``
    (``max(0, users_active - limit)``, 0 without a limit) and the warning ``users_over_limit`` in ``warnings``, BEFORE
    ``credentials_from_backup`` (which stays last), absent otherwise. No account list, no username, no address: the three
    numbers are the only new keys of ``report.json``; a report written before reads the defaults.
(b) ``apply.confirm_restore``: the example (5 active accounts, limit 3) is accepted through every channel (admin, cli, panel;
    self-hosted and managed with an owner): state ``pending``, no new field in ``restore.json`` (today's ``STATE_FIELDS``),
    no new parameter, no new error; a ``LIBREFOLIO_MAX_USERS`` that changed after the check is NOT ``restore_stage_outdated``.

Real databases come from ``test_backup_staging.py``; the instance of (b) from ``test_backup_apply.py``. Pure: tmp_path only;
no lane database, no server, no network.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.paths import STAGE_REPORT_FILE, stage_dir
from backend.app.services.platform.instance_backup.staging import StagingReport, read_report, stage_archive
from backend.test_scripts.test_services import test_backup_apply as applied
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of the neighbours, re-exported (autouse ones included): the real databases and archives, the live
# instance of the check, the production data directory that must stay absent, the boots and the block.
databases = cases.databases
head_archive = cases.head_archive
instance = cases.instance
configured_data_dir = cases.configured_data_dir
fresh_boots = applied.fresh_boots
no_inherited_block = applied.no_inherited_block

LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
OWNER_EMAIL = applied.OWNER_EMAIL
HOLDER_EMAIL = "Holder.B51k2@Example.COM"
CODE = "users_over_limit"
CREDENTIALS = "credentials_from_backup"

#: The accounts of a backup of the contract's example: (username, email, is_active, is_superuser). Five active, one disabled.
EXAMPLE_ACCOUNTS = (
    ("anna_k", "anna.b51k2@example.com", 1, 1),
    ("bruno_k", "bruno.b51k2@example.com", 1, 1),
    ("carla_k", "carla.b51k2@example.com", 1, 0),
    ("dario_k", "dario.b51k2@example.com", 1, 0),
    ("elena_k", "elena.b51k2@example.com", 1, 0),
    ("olga_k", "olga.b51k2@example.com", 0, 1),
)
#: The fields of ``StagingReport`` before B5-1k2: the only keys ``report.json`` may hold besides the three new ones.
FIELDS_BEFORE = {
    "stage_id",
    "staged_at",
    "expires_at",
    "backup",
    "app_version",
    "head_revision",
    "action",
    "migrations",
    "post_migration_fixes",
    "tables",
    "foreign_key_violations_before",
    "foreign_key_violations_after",
    "files",
    "files_size",
    "database_size",
    "instance_key_included",
    "encrypted",
    "secrets_rekeyed",
    "secrets_unreadable",
    "administrators",
    "owner_candidates",
    "owner_email_checked",
    "owner_conflicts",
    "control_totals",
    "control_totals_differences",
    "control_totals_differences_count",
    "warnings",
    "blockers",
}
USERS_FIELDS = ("users_active", "users_limit", "users_over_limit")


def new_field(report: Any, name: str) -> Any:
    """``report.<name>``, a field B5-1k2 adds; before it, a failure that says so."""
    if name not in type(report).model_fields:
        pytest.fail(f"[new] B5-1k2: {type(report).__name__} has no {name} yet (contract «staging.py»)", pytrace=False)
    return getattr(report, name)


def users_of(report: Any) -> tuple[Any, Any, Any]:
    return tuple(new_field(report, name) for name in USERS_FIELDS)


@pytest.fixture(autouse=True)
def no_inherited_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The limit a developer's shell may carry is removed for every test: a test sets its own."""
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)


# =============================================================================
# (a) The check
# =============================================================================


def checked_backup(instance, databases, tmp_path, monkeypatch, *, accounts=EXAMPLE_ACCOUNTS, limit: str | None = None, profile: str = "selfhosted", owner_email: str | None = None) -> StagingReport:
    """``accounts`` backed up, checked under that profile, owner's address and limit (``None``: unset)."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    cases.owner_email_is(monkeypatch, owner_email)
    if limit is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, limit)
    archive, _described = cases.backup_with_accounts(tmp_path, databases, accounts)
    return stage_archive(archive.path, instance.root)


def warned(report: StagingReport) -> bool:
    return CODE in report.warnings


def test_five_active_accounts_over_a_limit_of_three_are_reported_and_warned(instance, databases, tmp_path, monkeypatch):
    """(a) B5-1k2, the contract's example: five active accounts (and a disabled one), limit 3: ``users_active`` 5,
    ``users_limit`` 3, ``users_over_limit`` 2 and the warning ``users_over_limit``, once, BEFORE ``credentials_from_backup``,
    which stays the last of the warnings. The check is no refusal: the report stays restorable."""
    print_section("(a) B5-1k2 the report over the limit")
    report = checked_backup(instance, databases, tmp_path, monkeypatch, limit="3")
    assert users_of(report) == (5, 3, 2), f"5 active, limit 3, 2 over: {users_of(report)}"
    assert report.warnings.count(CODE) == 1, f"the warning is there, once: {report.warnings}"
    assert report.warnings[-1] == CREDENTIALS and report.warnings.index(CODE) < report.warnings.index(CREDENTIALS), f"before credentials_from_backup, which stays last: {report.warnings}"
    assert report.blockers == [] and report.restorable, f"over the limit is no blocker of the check: {report.blockers}"
    print_success("5, 3, 2 and the warning before credentials_from_backup")


#: (the limit variable, the limit the report records, the accounts over it).
LIMITS = [
    pytest.param(None, None, 0, id="no-limit"),
    pytest.param("   ", None, 0, id="a-blank-limit-is-no-limit"),
    pytest.param("5", 5, 0, id="exactly-at-the-limit"),
    pytest.param("6", 6, 0, id="below-the-limit"),
    pytest.param("4", 4, 1, id="one-over"),
    pytest.param("1", 1, 4, id="four-over"),
    pytest.param("not a number", None, 0, id="an-invalid-limit-is-no-limit"),
    pytest.param("0", None, 0, id="zero-is-invalid-so-no-limit"),
    pytest.param("-3", None, 0, id="negative-is-invalid-so-no-limit"),
]


@pytest.mark.parametrize(("limit", "recorded", "over"), LIMITS)
def test_the_limit_the_report_records_how_far_over_it_is_and_whether_it_warns(instance, databases, tmp_path, monkeypatch, limit, recorded, over):
    """(a) B5-1k2: ``users_limit`` is ``max_users()`` (``None`` when unset, blank or invalid: an invalid value never fires
    the warning, as in A5-7); ``users_over_limit`` is ``max(0, active - limit)``, 0 without a limit; the warning exists
    exactly when it is above 0. ``users_active`` is always the five active accounts (the disabled one never counts), limit
    or not."""
    report = checked_backup(instance, databases, tmp_path, monkeypatch, limit=limit)
    assert users_of(report) == (5, recorded, over), f"{LIMIT_VARIABLE}={limit!r}: (5, {recorded!r}, {over}), not {users_of(report)}"
    assert warned(report) == (over > 0), f"the warning only when over the limit ({over}): {report.warnings}"
    assert report.warnings[-1] == CREDENTIALS, f"credentials_from_backup stays last: {report.warnings}"
    print_success(f"{limit!r}: limit {recorded!r}, over {over}")


#: (profile, the owner's address of the instance, whether the holder of HOLDER_EMAIL is active, the active accounts counted).
HOLDERS = [
    pytest.param("managed", HOLDER_EMAIL, 0, 4, id="managed-the-inactive-holder-is-counted-it-will-be-activated"),
    pytest.param("managed", HOLDER_EMAIL, 1, 4, id="managed-an-active-holder-is-counted-once"),
    pytest.param("managed", "nobody.b51k2@example.com", 0, 3, id="managed-nobody-holds-the-address"),
    pytest.param("managed", None, 0, 3, id="managed-without-an-owner-s-address"),
    pytest.param("selfhosted", HOLDER_EMAIL, 0, 3, id="selfhosted-the-holder-is-nobody-special"),
]


@pytest.mark.parametrize(("profile", "owner_email", "holder_active", "counted"), HOLDERS)
def test_the_inactive_account_that_holds_the_owner_s_address_is_counted_on_a_managed_instance_only(instance, databases, tmp_path, monkeypatch, profile, owner_email, holder_active, counted):
    """(a) B5-1k2: three active accounts and one that holds the owner's address (in another A-Z case). The restore activates
    that account on a managed instance (A5-2), so when it is inactive it takes a place: ``users_active`` is 4. Never counted
    twice when active, nor on self-hosted, nor without the address, nor when nobody holds it. For a limit of 2 the warning
    follows the count."""
    print_section("(a) B5-1k2 the owner's account takes a place")
    accounts = (
        ("anna_k", "anna.b51k2@example.com", 1, 1),
        ("bruno_k", "bruno.b51k2@example.com", 1, 0),
        ("carla_k", "carla.b51k2@example.com", 1, 0),
        ("holder_k", "holder.b51k2@example.com", holder_active, 0),
    )
    report = checked_backup(instance, databases, tmp_path, monkeypatch, accounts=accounts, limit="2", profile=profile, owner_email=owner_email)
    assert users_of(report) == (counted, 2, counted - 2), f"{profile}, {owner_email!r}, holder active {holder_active}: {counted} counted, not {users_of(report)}"
    assert warned(report), f"{counted} accounts for a limit of 2: the warning: {report.warnings}"
    print_success(f"{counted} places")


def test_the_holder_is_counted_even_without_a_limit(instance, databases, tmp_path, monkeypatch):
    """(a) B5-1k2: ``users_active`` is computed with no limit at all: the managed instance's inactive holder is in it, the
    limit ``None``, nothing over, no warning."""
    accounts = (("anna_k", "anna.b51k2@example.com", 1, 1), ("holder_k", "holder.b51k2@example.com", 0, 0))
    report = checked_backup(instance, databases, tmp_path, monkeypatch, accounts=accounts, limit=None, profile="managed", owner_email=HOLDER_EMAIL)
    assert users_of(report) == (2, None, 0) and not warned(report), f"counted with no limit: {users_of(report)}, {report.warnings}"
    print_success("counted without a limit")


def test_the_new_keys_of_report_json_are_three_numbers_and_name_nobody(instance, databases, tmp_path, monkeypatch):
    """(a) B5-1k2: ``report.json`` gains exactly ``users_active``, ``users_limit`` and ``users_over_limit`` (integers, the
    limit possibly ``null``) and nothing else: no list of accounts, no username, no address. On a self-hosted instance (no
    candidates) the usernames of the plain users and every address of the backup are nowhere in the file. Read back by
    ``read_report``."""
    report = checked_backup(instance, databases, tmp_path, monkeypatch, limit="3")
    path = stage_dir(instance.root, report.stage_id) / STAGE_REPORT_FILE
    text = path.read_text(encoding="utf-8")
    written = json.loads(text)
    assert [written.get(name, "<missing>") for name in USERS_FIELDS] == [5, 3, 2], f"[new] B5-1k2: report.json: {[written.get(name, '<missing>') for name in USERS_FIELDS]}"
    assert set(written) - FIELDS_BEFORE == set(USERS_FIELDS), f"the only new keys are the three numbers: {sorted(set(written) - FIELDS_BEFORE)}"
    # The owner's candidates (B5-1, any active administrator, with the address it holds) and the owner's address the check
    # used were in the file before this lot; what B5-1k2 adds names nobody.
    rest = json.dumps({key: value for key, value in written.items() if key not in {"owner_candidates", "owner_email_checked"}})
    seen = [word for word in ("carla_k", "dario_k", "elena_k", "olga_k", "@example") if word in rest]
    assert seen == [], f"no plain username or address outside the owner's candidates in report.json: {seen}"
    again = read_report(instance.root, report.stage_id)
    assert users_of(again) == (5, 3, 2) and again.warnings == report.warnings, "read_report gives them back"
    print_success("three numbers, nobody named")


def test_a_report_written_before_reads_no_limit_and_no_warning(instance, databases, tmp_path, monkeypatch):
    """(a) B5-1k2: a ``report.json`` without the three keys still reads: 0, ``None``, 0; its warnings as written."""
    report = checked_backup(instance, databases, tmp_path, monkeypatch, limit="3")
    path = stage_dir(instance.root, report.stage_id) / STAGE_REPORT_FILE
    record = json.loads(path.read_text(encoding="utf-8"))
    barrier = [record.get(name, "<missing>") for name in USERS_FIELDS]
    assert barrier == [5, 3, 2], f"[new] B5-1k2: barrier: the check wrote the three numbers: {barrier}"
    for name in USERS_FIELDS:
        record.pop(name, None)
    record["warnings"] = [warning for warning in record["warnings"] if warning != CODE]
    path.write_text(json.dumps(record), encoding="utf-8")
    old = read_report(instance.root, report.stage_id)
    assert users_of(old) == (0, None, 0) and not warned(old), f"the defaults of a report of before: {users_of(old)}, {old.warnings}"
    print_success("defaults")


# =============================================================================
# (b) The confirmation never refuses
# =============================================================================

ANNA = "anna_k"


@dataclass(frozen=True)
class Example:
    """The contract's example checked once for the module under one profile: the report's copy and the ids of its accounts."""

    checked: applied.Checked
    ids: dict[str, int]


def _checked_example(databases, tmp_path_factory, name: str, *, profile: str, owner_email: str | None, flagged: tuple[str, ...]) -> Example:
    root = tmp_path_factory.mktemp(name)
    live = root / "instance"
    live.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        patch.setenv(PROFILE_VARIABLE, profile)
        patch.setenv(LIMIT_VARIABLE, "3")
        cases.owner_email_is(patch, owner_email)
        try:
            archive, described = cases.backup_with_accounts(root / "backup", databases, EXAMPLE_ACCOUNTS, flagged=flagged)
            report = stage_archive(archive.path, live)
        finally:
            cases.get_git_version.cache_clear()
    assert report.restorable, f"precondition: the example is restorable: {report.blockers}"
    return Example(checked=applied.Checked(stage=stage_dir(live, report.stage_id), report=report), ids={user: entry["user_id"] for user, entry in described.items()})


@pytest.fixture(scope="module")
def example_selfhosted(databases, tmp_path_factory) -> Example:
    return _checked_example(databases, tmp_path_factory, "b51k2-selfhosted", profile="selfhosted", owner_email=None, flagged=())


@pytest.fixture(scope="module")
def example_managed(databases, tmp_path_factory) -> Example:
    """Managed with an owner's address nobody holds: Anna, an active administrator the backup marks as its owner, is who the
    command line and the panel pick; the app's administrator chooses her."""
    return _checked_example(databases, tmp_path_factory, "b51k2-managed", profile="managed", owner_email=OWNER_EMAIL, flagged=(ANNA,))


def settings_now(monkeypatch: pytest.MonkeyPatch, profile: str, owner_email: str | None, limit: str | None) -> None:
    """The instance as it is when the restore is confirmed (the profile and owner of the check, the limit as told)."""
    applied.use_profile(monkeypatch, profile)
    cases.owner_email_is(monkeypatch, owner_email)
    if limit is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, limit)


def built(tmp_path, databases, scene: Example, monkeypatch: pytest.MonkeyPatch) -> applied.Instance:
    """A live instance with the scene's checked copy waiting in it. ``applied.build`` sets the session versions of the
    accounts of its own module's backup; here they are the example's."""
    monkeypatch.setattr(applied, "BACKUP_VERSIONS", {entry[0]: 1 for entry in EXAMPLE_ACCOUNTS})
    return applied.build(tmp_path / "instance", databases, scene.checked)


def over_the_limit(inst: applied.Instance) -> None:
    """Barrier: the report of the scene really is over the limit (a field B5-1k2 adds)."""
    assert users_of(read_report(inst.root, inst.stage_id)) == (5, 3, 2), "[new] B5-1k2: barrier: the copy's report says 5 active accounts, limit 3, 2 over"


#: (profile, the way it is confirmed, the owner's address, the owner chosen by name (admin only)).
CHANNELS = [
    pytest.param("selfhosted", "admin", None, None, id="selfhosted-the-app"),
    pytest.param("selfhosted", "cli", None, None, id="selfhosted-the-command-line"),
    pytest.param("selfhosted", "panel", None, None, id="selfhosted-the-hosting-panel"),
    pytest.param("managed", "admin", OWNER_EMAIL, ANNA, id="managed-the-app"),
    pytest.param("managed", "cli", OWNER_EMAIL, None, id="managed-the-command-line"),
    pytest.param("managed", "panel", OWNER_EMAIL, None, id="managed-the-hosting-panel"),
]


def confirm_arguments(inst: applied.Instance, via: str, owner_id: int | None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"confirmed_by": "ada" if via == "admin" else via, "confirmed_via": via, "data_dir": inst.root, "now": inst.confirm_at}
    if owner_id is not None:
        arguments["owner_user_id"] = owner_id
    return arguments


@pytest.mark.parametrize(("profile", "via", "owner_email", "owner_name"), CHANNELS)
def test_a_backup_with_too_many_accounts_is_confirmed_through_every_channel_and_adds_nothing_to_the_state(tmp_path, databases, example_selfhosted, example_managed, monkeypatch, profile, via, owner_email, owner_name):
    """(b) B5-1k2: 5 active accounts for a limit of 3: ``confirm_restore`` accepts it from the app, the command line and the
    hosting panel, self-hosted and managed with an owner: ``pending``, and ``restore.json`` holds exactly today's
    ``STATE_FIELDS`` (no count of accounts, no list, no outcome of a removal). The function takes no new parameter."""
    print_section("(b) B5-1k2 too many accounts: confirmed")
    scene = example_selfhosted if profile == "selfhosted" else example_managed
    inst = built(tmp_path, databases, scene, monkeypatch)
    settings_now(monkeypatch, profile, owner_email, "3")
    over_the_limit(inst)
    apply = applied.apply_module()
    owner_id = scene.ids[owner_name] if owner_name else None
    state = apply.confirm_restore(inst.stage_id, **confirm_arguments(inst, via, owner_id))
    assert (state.status, state.confirmed_via) == ("pending", via), f"accepted and waiting: {state}"
    record = json.loads(applied.state_file(inst.root).read_text(encoding="utf-8"))
    assert set(record) == set(apply.RestoreState.model_fields) == applied.STATE_FIELDS, f"the state gains no field: {sorted(set(record) ^ applied.STATE_FIELDS)}"
    assert sorted(inspect.signature(apply.confirm_restore).parameters) == ["confirmed_by", "confirmed_via", "data_dir", "now", "owner_user_id", "stage_id"], "confirm_restore takes no new parameter"
    assert apply.read_restore(inst.root) == state, "read_restore reads it back"
    print_success(f"{profile} via {via}: pending, state unchanged")


#: (the limit now): moved since the check, which saw 3.
MOVED_LIMITS = [
    pytest.param("4", id="raised"),
    pytest.param("2", id="lowered"),
    pytest.param(None, id="removed"),
    pytest.param("not a number", id="became-invalid"),
]


@pytest.mark.parametrize("now", MOVED_LIMITS)
def test_a_limit_that_changed_since_the_check_is_not_a_reason_to_check_again(tmp_path, databases, example_selfhosted, monkeypatch, now):
    """(b) B5-1k2: the report was made for another ``LIBREFOLIO_MAX_USERS`` than the one in force: confirmed all the same,
    no ``restore_stage_outdated`` (the warning is informative and the first sign-in decides with the limit then)."""
    inst = built(tmp_path, databases, example_selfhosted, monkeypatch)
    settings_now(monkeypatch, "selfhosted", None, now)
    over_the_limit(inst)
    state = applied.apply_module().confirm_restore(inst.stage_id, **confirm_arguments(inst, "admin", None))
    assert state.status == "pending", f"limit 3 at the check, {now!r} now: confirmed: {state}"
    print_success(f"3 -> {now!r}: confirmed")


def test_the_restore_knows_no_refusal_for_too_many_users():
    """(b) B5-1k2, a guard that stays green: no error class, no removal function and no state of a removal in ``apply`` (the
    B5-1k design is gone)."""
    apply = applied.apply_module()
    found = [name for name in ("RestoreTooManyUsersError", "RestoreRemoveUserInvalidError", "removal_pending", "record_removal_outcome") if hasattr(apply, name)]
    assert found == [], f"apply holds nothing of a removal: {found}"
    assert not [name for name in ("remove_user_ids", "removal_outcome") if name in apply.RestoreState.model_fields], "the state holds no removal"
    print_success("no refusal, no removal")
