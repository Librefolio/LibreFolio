"""
The administrators' route (the app) next to the restore that KEEPS the owner's password and sessions (workstream B, lot
B5-1l; contract ``B-5-1l-contratto.md``). Selector: ``api backup-owner-kept-app``. The hosting panel's side is in
``test_backup_owner_kept_api.py``; the service-level contract in ``test_backup_owner_kept.py``.

The exception is the PANEL's alone: a restore confirmed by an administrator from the app on the same managed instance, for the
same copy, with the owner chosen, revokes the owner's password and sessions as ever. Through the routes:

1. A real check of a backup with one marked administrator that holds the owner's address (the report counts the mark:
   ``owner_marks`` 1 — red before B5-1l, the check counts nothing). A real upload and check, read from the route.
2. GUARD: the same copy confirmed with ``{"owner_user_id": <that account>}`` is 202 and ``restore.json`` records the account
   chosen and NO outcome (never ``kept``); the administrators' status view has its twelve fields and not a word of the owner,
   the outcome or an id; the confirmation's body stays ``{owner_user_id}``.

How. The fixtures of ``test_backup_restore_apply.py`` and ``test_backup_restore.py`` are imported (an app of each test holds
``backup_router``, ``get_current_user`` overridden; the data directory of the routes under ``tmp_path``; fake check threads),
as ``test_backup_users_limit_api.py`` does. Pure; no lane server, database or network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.paths import restore_dir
from backend.app.services.platform.instance_backup.staging import read_report
from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_api import test_backup_restore_apply as apply_api
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of the neighbours, re-exported: ``instance`` (autouse), the real databases and archives.
instance = api.instance
databases = api.databases
head_archive = api.head_archive

#: The owner's address (``example.com``: ``.test`` is refused as ``LIBREFOLIO_ADMIN_EMAIL``) and the account of the backup that holds it.
OWNER_EMAIL = "anna.owner.b51l@example.com"
#: (username, email, is_active, is_superuser): anna is marked in the backup and holds the owner's address.
ACCOUNTS = (
    ("anna_l", OWNER_EMAIL.upper(), 1, 1),
    ("bruno_l", "bruno.b51l@example.com", 1, 1),
    ("carla_l", "carla.b51l@example.com", 1, 0),
)


@dataclass(frozen=True)
class Backup:
    """The backup as an archive, and the ids of its accounts."""

    archive: Any
    ids: dict[str, int]


@pytest.fixture(scope="module")
def backup(databases, tmp_path_factory) -> Backup:
    root = tmp_path_factory.mktemp("b51l-app-archive")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            archive, described = cases.backup_with_accounts(root / "backup", databases, ACCOUNTS, flagged=("anna_l",))
        finally:
            cases.get_git_version.cache_clear()
    assert not (root / "configured-data-dir").exists(), "precondition: the archive was built without writing in the configured data directory"
    assert described["anna_l"]["is_instance_owner"] is True, "precondition: the backup marks anna as the instance's owner"
    return Backup(archive=archive, ids={name: entry["user_id"] for name, entry in described.items()})


def on_disk(inst: api.Instance) -> dict[str, Any]:
    return json.loads(apply_api.state_path(inst.root).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_the_check_of_a_backup_with_one_marked_administrator_counts_the_mark(instance, backup, monkeypatch):
    """B5-1l: a real check through the administrators' route, managed, the owner's address held by the one marked active
    administrator: the report the check keeps has ``owner_marks`` 1 and that candidate marked. Red before B5-1l: the report
    has no such count."""
    print_section("B5-1l app: the check counts the mark")
    apply_api.owner_setting(monkeypatch, "managed", OWNER_EMAIL)
    stage_id = await apply_api.checked(backup.archive)
    report = read_report(instance.root, stage_id)
    marked = [candidate.username for candidate in report.owner_candidates if candidate.is_instance_owner]
    assert marked == ["anna_l"], f"barrier: anna is the marked candidate: {marked}"
    assert getattr(report, "owner_marks", "<missing>") == 1, f"[new] B5-1l: the check counts the one mark: {getattr(report, 'owner_marks', '<missing>')!r}"
    print_success("owner_marks 1")


@pytest.mark.asyncio
async def test_the_same_copy_confirmed_by_an_administrator_with_the_owner_chosen_is_never_kept_and_the_status_says_nothing(instance, backup, monkeypatch):
    """B5-1l, a GUARD: the copy the rule keeps for the panel, confirmed from the app with ``{"owner_user_id": anna}`` (the
    holder of the address, the forced choice): 202, a plain ``RestoreStatus`` (its twelve fields), and ``restore.json``
    records the account chosen and NO outcome. The status view has not a word of the owner, the outcome or an id."""
    print_section("B5-1l app: the same copy is not kept")
    apply_api.owner_setting(monkeypatch, "managed", OWNER_EMAIL)
    stage_id = await apply_api.checked(backup.archive)
    anna = backup.ids["anna_l"]
    response = await apply_api.confirm_with(stage_id, {"owner_user_id": anna})
    assert response.status_code == 202, f"accepted: {api.shown(response)}"
    assert set(response.json()) == apply_api.STATUS_FIELDS, f"a plain RestoreStatus: {sorted(response.json())}"
    record = on_disk(instance)
    assert (record["confirmed_via"], record["owner_user_id"], record["owner_outcome"]) == ("admin", anna, None), f"the choice, no outcome, never kept: {record}"
    status = await apply_api.restore_status()
    assert status.status_code == 200 and set(status.json()) == apply_api.STATUS_FIELDS, f"the status has its fields: {api.shown(status)}"
    text = (response.text + status.text).lower()
    shown = [secret for secret in ("owner", "kept", OWNER_EMAIL, "anna_l", f'"{anna}"') if secret in text]
    assert shown == [], f"the answers hold {shown}: {response.text} {status.text}"
    assert restore_dir(instance.root).is_dir(), "the restore waits"
    print_success("app: chosen, not kept, nothing in the views")
