"""
The hosting panel's confirmation that KEEPS the owner's password and sessions, through the API (workstream B, lot B5-1l;
contract ``B-5-1l-contratto.md``). Selector: ``api backup-owner-kept``. Written RED before the implementation. The service-level
contract is in ``test_backup_owner_kept.py``; the administrators' route (the app) is in ``test_backup_owner_kept_app_api.py``.

On a ``managed`` instance whose ``LIBREFOLIO_ADMIN_EMAIL`` is set, the panel's route (workstream H's ``panel_restore.py``, not
touched by this lot) only calls ``restore_jobs.confirm_check(..., confirmed_via="panel")`` and maps ``RestoreStateError.code`` to
HTTP. So, through the route:

1. A real check of the panel's backup, its report made to say what a check of a backup would say when the rule holds — one
   account (the active administrator that holds the owner's address) is the only one marked as the instance's owner:
   ``owner_marks`` 1 and the candidate marked — then the panel's confirmation: 202 with the same body as ever
   (``PanelRestoreStatus``, eleven fields, nothing about an owner), and ``restore.json`` records that account and
   ``owner_outcome`` ``kept``. Red before B5-1l: the outcome stayed ``None``.
2. The panel's status view, afterwards (GUARD): still the same eleven fields, and no word of the owner, the outcome or an id.
3. GUARD: a second mark in the report, or the holder not marked, is B5-1j's pick: 202, the holder as the owner, no outcome.
   Owner conflicts are still 409 ``owner_conflict`` first.

How. The fixtures of ``test_panel_restore_api.py`` (the app of ``main.py`` in process, the panel's tickets, real archives, fake
check threads) and the helpers of ``test_backup_owner_channels_api.py`` are reused as they are, imported: nothing of H's files
is changed. The panel's backup is built with the canary accounts of ``test_panel_restore_api.py``, so that its report is made
to mark the holder by rewriting ``report.json`` (the way the neighbour file gives it the owner's address). Pure: data
directories under ``tmp_path``, no lane server, no network.
"""

from __future__ import annotations

import json

import pytest

from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, STAGE_DATA_FOLDER, STAGE_REPORT_FILE, stage_dir
from backend.test_scripts.test_api import test_backup_owner_channels_api as channels
from backend.test_scripts.test_api import test_panel_restore_api as panel_cases
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of the panel's tests, reused as they are (the app, the panel of a test, the real archives, the databases).
app = panel_cases.app
panel = panel_cases.panel
archives = panel_cases.archives
databases = panel_cases.databases

HOLDER = channels.HOLDER
HOLDER_ADDRESS = channels.HOLDER_ADDRESS


def report_as_if_the_backup_marked(panel: panel_cases.Panel, stage_id: str, *, marked: bool = True, marks: int = 1) -> None:
    """The checked copy as a check of a backup that marks ``HOLDER`` as the instance's owner would have left it: the copy's
    database flags the account (``marked``), the report's candidate says so, and ``owner_marks`` is ``marks``. Raw JSON, so
    that it reads before B5-1l too (the key then ignored)."""
    database = stage_dir(panel.root, stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    if marked:
        cases.execute(database, f"UPDATE users SET is_instance_owner = 1 WHERE username = '{HOLDER}'")
    path = stage_dir(panel.root, stage_id) / STAGE_REPORT_FILE
    record = json.loads(path.read_text(encoding="utf-8"))
    held = [candidate for candidate in record["owner_candidates"] if candidate["username"] == HOLDER]
    assert len(held) == 1, f"precondition: the check listed {HOLDER}: {record['owner_candidates']}"
    held[0]["is_instance_owner"] = marked
    record["owner_marks"] = marks
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


async def keepable(panel: panel_cases.Panel, archives: panel_cases.Archives, **marking: object) -> tuple[str, int]:
    """A real check of the panel's backup on a managed instance whose owner's address ``HOLDER`` holds, its report saying the
    holder is marked (``marking``: see ``report_as_if_the_backup_marked``): the stage id and the holder's id in the copy."""
    channels.managed(panel, HOLDER_ADDRESS)
    stage_id = (await panel_cases.checked(panel, archives.changed_lfbk))["stage_id"]
    channels.give_the_address_to_the_holder(panel, stage_id)
    report_as_if_the_backup_marked(panel, stage_id, **marking)
    return stage_id, channels.staged_id_of(panel, stage_id, HOLDER)


# =============================================================================
# 1. The panel's confirmation keeps the owner
# =============================================================================


@pytest.mark.asyncio
async def test_a_panel_confirmation_of_the_copy_the_rule_keeps_is_202_and_records_the_outcome_kept(panel, archives):
    """B5-1l, through the panel: the one marked account is an active administrator and holds the owner's address (the report
    was read for it, no conflict): 202, ``pending`` via ``panel``, ``PanelRestoreStatus`` exactly (eleven fields); the state
    records that account as the owner and ``owner_outcome`` ``kept``, and ``restore.json`` says the same. The answer holds
    no account, no address, no word about the owner or the outcome. Red before B5-1l: the outcome stayed ``None``."""
    print_section("B5-1l panel: the owner is kept")
    stage_id, holder_id = await keepable(panel, archives)
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"the confirmation → 202: {panel_cases.shown(response)}"
    assert set(response.json()) == panel_cases.STATUS_FIELDS, f"PanelRestoreStatus, exactly: {sorted(response.json())}"
    state = apply_module.read_restore(panel.root)
    assert state is not None, "a restore waits"
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("pending", "panel", holder_id, "kept"), f"[new] B5-1l: the holder is the owner, kept: {state}"
    record = json.loads((panel.root / ".restore" / "restore.json").read_text(encoding="utf-8"))
    assert (record["owner_user_id"], record["owner_outcome"]) == (holder_id, "kept"), f"restore.json says it: {record}"
    text = response.text.lower()
    shown = [secret for secret in (HOLDER, HOLDER_ADDRESS, "owner", "kept") if secret in text]
    assert shown == [], f"the answer holds {shown}: {response.text}"
    print_success("panel: 202, kept")


@pytest.mark.asyncio
async def test_the_panel_s_status_after_a_kept_confirmation_says_nothing_of_the_owner(panel, archives):
    """B5-1l, a GUARD: after the confirmation that kept the owner, the panel's status view has its eleven fields and not a
    word of the owner, the outcome or an id; the panel learns nothing from this lot. Barrier: the confirmation recorded
    the owner (``kept``) — red before B5-1l."""
    stage_id, holder_id = await keepable(panel, archives)
    assert (await panel_cases.confirm(panel, stage_id)).status_code == 202, "precondition: confirmed"
    state = apply_module.read_restore(panel.root)
    assert (state.owner_user_id, state.owner_outcome) == (holder_id, "kept"), f"[new] B5-1l: barrier: kept: {state}"
    response = await panel_cases.restore_status(panel)
    assert response.status_code == 200 and set(response.json()) == panel_cases.STATUS_FIELDS, f"PanelRestoreStatus, exactly: {panel_cases.shown(response)}"
    text = response.text.lower()
    shown = [secret for secret in (HOLDER, HOLDER_ADDRESS, "owner", "kept", f'"{holder_id}"') if secret in text]
    assert shown == [], f"the status holds {shown}: {response.text}"
    print_success("panel status: nothing of the owner")


# =============================================================================
# 3. GUARDS: what the lot leaves as it was
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("marking", "why"),
    [
        pytest.param({"marks": 2}, "a second account of the backup is marked", id="two-marks"),
        pytest.param({"marked": False, "marks": 1}, "the one mark is on an account outside the candidates", id="the-holder-is-not-marked"),
        pytest.param({"marked": False, "marks": 0}, "nobody is marked", id="nobody-marked"),
    ],
)
async def test_a_panel_confirmation_where_a_condition_is_missing_is_b5_1j_and_keeps_nothing(panel, archives, marking, why):
    """B5-1l, a GUARD: the rule does not hold (``why``): 202 all the same, the holder of the address picked as the owner by
    B5-1j, and NO outcome — never ``kept``."""
    stage_id, holder_id = await keepable(panel, archives, **marking)
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"{why}: confirmed as before: {panel_cases.shown(response)}"
    state = apply_module.read_restore(panel.root)
    assert (state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("panel", holder_id, None), f"{why}: B5-1j's pick, not kept: {state}"
    print_success(f"{why}: not kept")


@pytest.mark.asyncio
async def test_a_panel_confirmation_with_owner_conflicts_is_still_409_owner_conflict_first(panel, archives):
    """B5-1l, a GUARD: the report would let the rule keep the owner but has an owner conflict: 409 ``owner_conflict``, as
    B5-1j gave it; nothing pending."""
    stage_id, _holder_id = await keepable(panel, archives)
    channels.rewrite_report(panel, stage_id, owner_conflicts=["duplicate_email"])
    response = await panel_cases.confirm(panel, stage_id)
    assert panel_cases.code(response) == (409, "owner_conflict"), f"409 owner_conflict: {panel_cases.shown(response)}"
    assert apply_module.read_restore(panel.root) is None, "nothing pending"
    print_success("owner_conflict first")
