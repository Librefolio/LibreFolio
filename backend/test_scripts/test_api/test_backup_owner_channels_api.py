"""
The owner of a restore confirmed by the hosting panel or from the command line, through the API (workstream B, lot B5-1j).
Selector: ``api backup-owner-channels``. Written RED before B5-1j; the analysis is
``B-5-1j-analisi-titolare-nel-restore-cli.md`` (§2, §4, §6, §8). The service-level contract is in ``test_backup_apply.py`` (v).

On a ``managed`` instance whose ``LIBREFOLIO_ADMIN_EMAIL`` is set, ``apply.confirm_restore`` of a confirmation via ``panel``
or ``cli`` picks the owner's account itself from the staged report. The hosting panel's route (workstream H's
``panel_restore.py``, not touched by this lot) only calls ``restore_jobs.confirm_check(..., confirmed_via="panel")`` and maps
``RestoreStateError.code`` to HTTP; so, through the route:

1. A real check of a backup in which an account holds the owner's address, then the panel's confirmation: 202, and the state
   records that account (``owner_user_id``), no outcome yet; the answer (``PanelRestoreStatus``) names no account and no
   address. Nobody found (the address is held by none, no account is marked): 202 all the same, ``owner_outcome`` ``none``.
2. A report with owner conflicts: 409 ``owner_conflict``, the message says to make a new backup, nothing pending. A report
   checked with another address than the current one: 409 ``restore_stage_outdated``. A self-hosted instance reads neither
   (a guard).
3. The guard: a committed restore confirmed from the command line (or the panel) whose owner is still to be given serves no
   data (423 ``instance_restore_interrupted``, reason ``owner_assignment``); it serves again once the other worker records
   the outcome; an ``error:<CODE>`` keeps refusing, and the reset (``backup pending --recover owner``) is allowed for it.
   H's own tests (``test_restore_owner_guard_api.py``) fake the hook or use a restore confirmed by an administrator; this file
   uses the real hook (``apply.owner_assignment_problem``) with a state of the command line, as ``_pending_at_start`` does.

How. The fixtures of ``test_panel_restore_api.py`` (the app of ``main.py`` in process, the panel's tickets, real archives, fake
check threads) and of ``test_await_restore_mode_api.py`` (an instance on a private database) are reused as they are, imported:
nothing of H's files is changed. Pure: data directories under ``tmp_path``, no lane server, no network.
"""

from __future__ import annotations

import json

import pytest

from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, STAGE_DATA_FOLDER, STAGE_REPORT_FILE, stage_dir
from backend.test_scripts.test_api import test_panel_restore_api as panel_cases
from backend.test_scripts.test_api import test_restore_owner_guard_api as guard_cases
from backend.test_scripts.test_api.test_await_restore_mode_api import instance as instance_fixture
from backend.test_scripts.test_api.test_await_restore_mode_api import signed_in
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_services.test_backup_owner import STAGE_ID, write_state
from backend.test_scripts.test_services.test_restore_owner_guard import Clock, guard_name, guard_set
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of the panel's tests, reused as they are (the app, the panel of a test, the real archives, the databases).
app = panel_cases.app
panel = panel_cases.panel
archives = panel_cases.archives
databases = panel_cases.databases
instance = instance_fixture

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
OWNER_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
#: The accounts of the panel's backup are ``<name>@example.test`` (``test_backup_staging.account``), and a ``.test`` address is
#: refused as ``LIBREFOLIO_ADMIN_EMAIL`` (``ADMIN_EMAIL_INVALID``): the owner's address is an ``example.com`` one, and this
#: account of the checked copy is given it (``give_the_address_to_the_holder``).
HOLDER = "h62canary_admin_two"
HOLDER_ADDRESS = "h62canary.owner.b51j@example.com"
OTHER_ADDRESS = "nobody.holds.this.b51j@example.com"
CONFLICT_ADVICE = "make a new backup"


def managed(panel: panel_cases.Panel, owner_email: str | None) -> None:
    """The panel's instance awaiting its restore, managed, with that owner's address (``None``: unset)."""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    if owner_email is None:
        panel.monkeypatch.delenv(OWNER_EMAIL_VARIABLE, raising=False)
    else:
        panel.monkeypatch.setenv(OWNER_EMAIL_VARIABLE, owner_email)


def staged_id_of(panel: panel_cases.Panel, stage_id: str, username: str) -> int:
    """The id of ``username`` in the checked copy of ``stage_id``."""
    database = stage_dir(panel.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    return cases.rows_of(database, f"SELECT id FROM users WHERE username = '{username}'")[0][0]


def give_the_address_to_the_holder(panel: panel_cases.Panel, stage_id: str) -> None:
    """The checked copy as if the owner's address had been the backup's own: ``HOLDER`` holds ``HOLDER_ADDRESS`` in the copy's
    database and in the candidates of its report (the check ran with the address set, so it listed the active administrators)."""
    database = stage_dir(panel.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    cases.execute(database, f"UPDATE users SET email = '{HOLDER_ADDRESS}' WHERE username = '{HOLDER}'")
    path = stage_dir(panel.root, stage_id) / STAGE_REPORT_FILE
    record = json.loads(path.read_text(encoding="utf-8"))
    held = [candidate for candidate in record["owner_candidates"] if candidate["username"] == HOLDER]
    assert len(held) == 1 and record["owner_email_checked"] == HOLDER_ADDRESS, f"precondition: the check listed {HOLDER} and used the address: {record['owner_candidates']}, {record['owner_email_checked']}"
    held[0]["email"] = HOLDER_ADDRESS
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def rewrite_report(panel: panel_cases.Panel, stage_id: str, **changes: object) -> None:
    """The checked copy's ``report.json`` with ``changes`` (raw JSON): what a check of another copy would have written."""
    path = stage_dir(panel.root, stage_id) / STAGE_REPORT_FILE
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update(changes)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


# =============================================================================
# 1. The panel's confirmation picks the owner
# =============================================================================


@pytest.mark.asyncio
async def test_a_panel_confirmation_on_a_managed_instance_picks_the_account_that_holds_the_owner_s_address(panel, archives):
    """B5-1j §2, through the panel: a real check of the backup with the owner's address set — one of its accounts holds it —,
    then the panel's confirmation: 202 ``pending`` via ``panel``; the state records that account as the owner (and no outcome
    yet). The answer holds no username and no address. Red before B5-1j: the state named nobody."""
    print_section("B5-1j panel: the owner is picked")
    managed(panel, HOLDER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    give_the_address_to_the_holder(panel, stage_id)
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"the confirmation → 202: {panel_cases.shown(response)}"
    assert set(response.json()) == panel_cases.STATUS_FIELDS, f"PanelRestoreStatus, exactly: {sorted(response.json())}"
    state = apply_module.read_restore(panel.root)
    assert state is not None, "a restore waits"
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("pending", "panel", staged_id_of(panel, stage_id, HOLDER), None), f"[new] B5-1j: the account that holds the address is the owner: {state}"
    text = response.text.lower()
    assert HOLDER not in text and HOLDER_ADDRESS not in text and "owner" not in text, f"the answer names no account and no address: {response.text}"
    print_success("panel: the holder of the address is the owner")


@pytest.mark.asyncio
async def test_a_panel_confirmation_where_nobody_can_be_picked_is_202_and_records_none(panel, archives):
    """B5-1j §2.3, through the panel: nobody holds the owner's address and the backup marks no administrator: not refused — 202
    — and the state records ``owner_outcome`` ``none`` with no owner. Red before B5-1j: no outcome was recorded."""
    managed(panel, OTHER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"nobody picked is no refusal: {panel_cases.shown(response)}"
    state = apply_module.read_restore(panel.root)
    assert state is not None and (state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("panel", None, "none"), f"[new] B5-1j: no owner, outcome none: {state}"
    assert OTHER_ADDRESS not in response.text.lower(), f"no address in the answer: {response.text}"
    print_success("panel: nobody picked → 202, outcome none")


# =============================================================================
# 2. Refusals through the panel
# =============================================================================


@pytest.mark.asyncio
async def test_a_panel_confirmation_of_a_copy_with_owner_conflicts_is_409_owner_conflict_with_what_to_do(panel, archives):
    """B5-1j §2: the checked copy has owner conflicts (its report says so): 409 ``owner_conflict`` — the code the generic
    mapping of ``RestoreStateError`` gives — whose message says to make a new backup; nothing pending. Red before B5-1j: 202."""
    print_section("B5-1j panel: owner_conflict")
    managed(panel, HOLDER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    give_the_address_to_the_holder(panel, stage_id)
    rewrite_report(panel, stage_id, owner_conflicts=["duplicate_email"])
    response = await panel_cases.confirm(panel, stage_id)
    assert panel_cases.code(response) == (409, "owner_conflict"), f"[new] B5-1j: 409 owner_conflict: {panel_cases.shown(response)}"
    message = str(response.json().get("detail", {}).get("message", ""))
    assert CONFLICT_ADVICE in message, f"the message says what to do ({CONFLICT_ADVICE!r}): {message!r}"
    assert apply_module.read_restore(panel.root) is None, "nothing pending"
    assert HOLDER_ADDRESS not in response.text.lower(), f"no address in the answer: {response.text}"
    print_success("panel: 409 owner_conflict, with advice")


@pytest.mark.asyncio
async def test_a_panel_confirmation_of_a_check_made_with_another_address_is_409_restore_stage_outdated(panel, archives):
    """B5-1j §2: the owner's address changed since the check (the hosting provider updated the variable): 409
    ``restore_stage_outdated``, nothing pending. Red before B5-1j: 202."""
    managed(panel, HOLDER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    panel.monkeypatch.setenv(OWNER_EMAIL_VARIABLE, OTHER_ADDRESS)
    response = await panel_cases.confirm(panel, stage_id)
    assert panel_cases.code(response) == (409, "restore_stage_outdated"), f"[new] B5-1j: 409 restore_stage_outdated: {panel_cases.shown(response)}"
    assert apply_module.read_restore(panel.root) is None, "nothing pending"
    print_success("panel: 409 restore_stage_outdated")


@pytest.mark.asyncio
async def test_a_panel_confirmation_on_a_self_hosted_instance_reads_no_owner_and_no_conflict(panel, archives):
    """B5-1j, a guard: self-hosted, the same conflict in the report changes nothing: 202, no owner, no outcome."""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    panel.monkeypatch.setenv(OWNER_EMAIL_VARIABLE, HOLDER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    rewrite_report(panel, stage_id, owner_conflicts=["duplicate_email"])
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"self-hosted: confirmed as before: {panel_cases.shown(response)}"
    state = apply_module.read_restore(panel.root)
    assert state is not None and (state.owner_user_id, state.owner_outcome) == (None, None), f"no owner, no outcome: {state}"
    print_success("selfhosted panel: unchanged")


# =============================================================================
# 3. The restore guard for a restore of the command line (or the panel)
# =============================================================================


async def pending_owner_at_start(instance, via: str):
    """A real committed ``restore.json`` confirmed via ``via`` that names the owner and records no outcome, the guard's real
    probe as the start makes it (no fake of the hook), its clock at 1 000 s. The clock and a signed-in session."""
    session = await signed_in(instance)
    instance.switches()
    (instance.root / ".restore").mkdir(exist_ok=True)
    write_state(instance.root, confirmed_via=via, owner_user_id=1)
    guard_set(instance.monkeypatch, "_interrupted", False)
    guard_set(instance.monkeypatch, "_owner_problem", None)
    clock = Clock(1_000.0)
    guard_set(instance.monkeypatch, "_monotonic", clock)
    guard_set(instance.monkeypatch, "_owner_checked_at", clock.now)
    probed = guard_name("probe_owner_assignment")()
    assert probed == "pending", f"[new] B5-1j: the real hook says a restore via {via} waits for its owner: {probed!r}"
    return clock, session


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["cli", "panel"])
async def test_a_restore_of_the_command_line_or_the_panel_whose_owner_is_pending_serves_no_data(instance, via):
    """B5-1j §6: the filter of the restore guard's hook is gone: a committed restore via ``cli`` or ``panel`` that names the
    owner and records no outcome is ``pending`` to the guard, which answers 423 to a signed-in user until the outcome
    is recorded; then, after ``OWNER_RECHECK_SECONDS``, the next request is served."""
    print_section(f"B5-1j guard: owner pending after a restore via {via}")
    clock, session = await pending_owner_at_start(instance, via)
    refused = await guard_cases.brokers(instance, session)
    assert guard_cases.code(refused) == (423, guard_cases.INTERRUPTED_CODE), f"pending at the start: refused: {guard_cases.shown(refused)}"
    apply_module.record_owner_outcome(instance.root, STAGE_ID, "sent")
    clock.now += guard_name("OWNER_RECHECK_SECONDS")
    served = await guard_cases.brokers(instance, session)
    assert served.status_code == 200, f"sent in the file: served after the interval: {guard_cases.shown(served)}"
    print_success(f"via {via}: 423 then served")


@pytest.mark.asyncio
@pytest.mark.parametrize("via", ["cli", "panel"])
async def test_a_failed_owner_assignment_of_a_command_line_or_panel_restore_keeps_refusing_until_it_is_reset(instance, via):
    """B5-1j §6: ``error:EMAIL_TAKEN`` recorded for a restore via ``cli`` or ``panel``: refused (423) with the reason
    ``owner_assignment``; ``reset_owner_assignment`` (``backup pending --recover owner``) clears it for such a restore too,
    and the file alone does not open the guard (a code is final for the process: the administrator restarts)."""
    clock, session = await pending_owner_at_start(instance, via)
    apply_module.record_owner_outcome(instance.root, STAGE_ID, "error:EMAIL_TAKEN")
    clock.now += guard_name("OWNER_RECHECK_SECONDS")
    refused = await guard_cases.brokers(instance, session)
    assert guard_cases.code(refused) == (423, guard_cases.INTERRUPTED_CODE), f"error in the file: refused: {guard_cases.shown(refused)}"
    assert (guard_name("_owner_problem"), guard_name("restore_interrupted_reason")()) == ("EMAIL_TAKEN", "owner_assignment"), "the guard holds the code"
    assert apply_module.reset_owner_assignment(instance.root) is False, f"[new] B5-1j: the reset is allowed for a restore via {via}"
    print_success(f"via {via}: error keeps refusing; reset allowed")


@pytest.mark.asyncio
async def test_a_restore_where_nobody_was_picked_never_keeps_the_instance_from_serving(instance):
    """B5-1j §2.3, a guard: a committed command-line restore with ``owner_outcome`` ``none`` and no owner is nothing for the
    guard: the real hook answers ``None`` and a signed-in user is served at once."""
    session = await signed_in(instance)
    instance.switches()
    (instance.root / ".restore").mkdir(exist_ok=True)
    write_state(instance.root, confirmed_via="cli", owner_user_id=None, owner_outcome="none")
    guard_set(instance.monkeypatch, "_interrupted", False)
    guard_set(instance.monkeypatch, "_owner_problem", None)
    assert guard_name("probe_owner_assignment")() is None, "the hook finds nothing pending"
    served = await guard_cases.brokers(instance, session)
    assert served.status_code == 200, f"served: {guard_cases.shown(served)}"
    print_success("nobody picked: served")
