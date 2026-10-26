"""
A backup with more active accounts than ``LIBREFOLIO_MAX_USERS``, through the administrators' API: the report warns, the
confirmation never refuses (workstream B, lot B5-1k2; contract ``B-5-1k2-contratto.md`` «Backend»). Selector: ``api
backup-users-limit``. The hosting panel's side is in ``test_backup_users_limit_panel_api.py``.

Written RED, before B5-1k2: the report has no ``users_*`` fields and the warning code is not in the ``Literal``. The tests of
the confirmation are guards of a refusal that must never come: each one first proves, from the stage report, that the scene
IS over the limit (so it is red today for that field).

(a) ``GET /backup/restore/stage/{id}`` (``RestoreStageReport``): ``users_active``, ``users_limit`` (``null`` unset or invalid),
    ``users_over_limit`` and the warning ``users_over_limit`` before ``credentials_from_backup``; nothing else new, no list of
    accounts, no username of a plain user.
(b) ``POST .../confirm``: 202 with a plain ``RestoreStatus`` for the example (5 active accounts, limit 3), self-hosted and
    managed with an owner; the body stays ``{owner_user_id}`` (``RestoreConfirmRequest``, ``extra="forbid"``); ``restore.json``
    keeps today's fields; a limit changed after the check is not ``restore_stage_outdated``.
(c) OpenAPI: the three fields and the code in the ``Literal``; the confirmation's body unchanged; no new route.

How. The fixtures of ``test_backup_restore_apply.py`` and ``test_backup_restore.py`` are imported (an app of each test holds
``backup_router``, ``get_current_user`` overridden; the data directory of the routes under ``tmp_path``; fake check threads).
The archive is the example, built once for the module. Pure; no lane server, database or network.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import pytest

from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_api import test_backup_restore_apply as apply_api
from backend.test_scripts.test_services import test_backup_apply as applied
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of the neighbours, re-exported: ``instance`` (autouse), the real databases and archives.
instance = api.instance
databases = api.databases
head_archive = api.head_archive

LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
CODE = "users_over_limit"
USERS_FIELDS = ("users_active", "users_limit", "users_over_limit")
#: The exact keys of ``RestoreStageReport`` before B5-1k2.
FIELDS_BEFORE = {
    "backup_created_at",
    "backup_app_version",
    "backup_origin",
    "backup_revision",
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
    "warnings",
    "blockers",
    "control_totals",
    "control_totals_differences",
    "control_totals_differences_count",
    "restorable",
    "expires_at",
    "owner_choice",
}
#: (username, email, is_active, is_superuser): five active accounts and a disabled one.
ACCOUNTS = (
    ("anna_k", "anna.b51k2@example.com", 1, 1),
    ("bruno_k", "bruno.b51k2@example.com", 1, 1),
    ("carla_k", "carla.b51k2@example.com", 1, 0),
    ("dario_k", "dario.b51k2@example.com", 1, 0),
    ("elena_k", "elena.b51k2@example.com", 1, 0),
    ("olga_k", "olga.b51k2@example.com", 0, 1),
)
PLAIN_USERS = ("carla_k", "dario_k", "elena_k", "olga_k")


@dataclass(frozen=True)
class Backup:
    """The example as an archive, and the ids of its accounts."""

    archive: Any
    ids: dict[str, int]


@pytest.fixture(scope="module")
def backup(databases, tmp_path_factory) -> Backup:
    root = tmp_path_factory.mktemp("b51k2-api-archive")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            archive, described = cases.backup_with_accounts(root / "backup", databases, ACCOUNTS)
        finally:
            cases.get_git_version.cache_clear()
    assert not (root / "configured-data-dir").exists(), "precondition: the archive was built without writing in the configured data directory"
    return Backup(archive=archive, ids={name: entry["user_id"] for name, entry in described.items()})


@pytest.fixture(autouse=True)
def limit_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)


async def check(scene: Backup, monkeypatch: pytest.MonkeyPatch, limit: str | None = "3") -> str:
    """The example checked under that limit (``None``: unset); the stage id."""
    if limit is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, limit)
    return await apply_api.checked(scene.archive)


async def report_of(stage_id: str) -> dict[str, Any]:
    return (await api.poll(stage_id, user=apply_api.B3_ADMIN)).json()["report"]


async def over_the_limit(stage_id: str) -> None:
    """Barrier: the stage report says 5 active accounts, limit 3, 2 over (fields B5-1k2 adds)."""
    report = await report_of(stage_id)
    assert [report.get(name, "<missing>") for name in USERS_FIELDS] == [5, 3, 2], f"[new] B5-1k2: barrier: the report says 5, 3, 2: {sorted(report)}"


def on_disk(inst: api.Instance) -> dict[str, Any]:
    return json.loads(apply_api.state_path(inst.root).read_text(encoding="utf-8"))


# =============================================================================
# (a) The report
# =============================================================================


@pytest.mark.asyncio
async def test_the_report_over_the_limit_carries_the_numbers_and_the_warning(instance, backup, monkeypatch):
    """(a) B5-1k2: 5 active accounts, limit 3: ``users_active`` 5, ``users_limit`` 3, ``users_over_limit`` 2, and the warning
    ``users_over_limit`` before ``credentials_from_backup``. The keys of the report are the ones of before and the three
    numbers, exactly; no plain user's name anywhere in the answer; the check stays restorable."""
    print_section("(a) B5-1k2 the report over the limit")
    stage_id = await check(backup, monkeypatch)
    response = await api.poll(stage_id, user=apply_api.B3_ADMIN)
    report = response.json()["report"]
    assert [report.get(name, "<missing>") for name in USERS_FIELDS] == [5, 3, 2], f"[new] B5-1k2: 5 active, limit 3, 2 over: {sorted(report)}"
    assert set(report) == FIELDS_BEFORE | set(USERS_FIELDS), f"exactly the keys of before and the three numbers: {sorted(set(report) ^ (FIELDS_BEFORE | set(USERS_FIELDS)))}"
    assert report["warnings"] == api.as_read_by_admin(CODE), f"the warning, then credentials_from_backup, then the viewer's own: {report['warnings']}"
    assert report["restorable"] and report["blockers"] == [], "over the limit is no blocker of the check"
    assert [name for name in (*PLAIN_USERS, "@example") if name in response.text] == [], "no plain user's name and no address in the answer"
    print_success("5, 3, 2 and the warning")


#: (the limit variable, users_limit, users_over_limit, whether the warning is there).
FITS = [
    pytest.param(None, None, 0, False, id="no-limit"),
    pytest.param("5", 5, 0, False, id="at-the-limit"),
    pytest.param("9", 9, 0, False, id="below-the-limit"),
    pytest.param("not a number", None, 0, False, id="an-invalid-limit-is-no-limit"),
    pytest.param("4", 4, 1, True, id="one-over"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("limit", "recorded", "over", "warned"), FITS)
async def test_the_report_that_fits_has_no_warning_and_an_invalid_limit_is_none(instance, backup, monkeypatch, limit, recorded, over, warned):
    """(a) B5-1k2: not over the limit (no limit, at it, below it, or an invalid value read as none): ``users_active`` 5,
    ``users_limit`` as read (``null`` for none), ``users_over_limit`` 0, no warning. One over: 1 and the warning."""
    stage_id = await check(backup, monkeypatch, limit=limit)
    report = await report_of(stage_id)
    assert [report.get(name, "<missing>") for name in USERS_FIELDS] == [5, recorded, over], f"[new] B5-1k2: {LIMIT_VARIABLE}={limit!r}: {[report.get(name, '<missing>') for name in USERS_FIELDS]}"
    assert (CODE in report["warnings"]) == warned, f"the warning only when over the limit: {report['warnings']}"
    print_success(f"{limit!r}: {recorded!r}, {over}")


# =============================================================================
# (b) The confirmation
# =============================================================================


@pytest.mark.asyncio
async def test_a_confirmation_of_the_example_is_202_with_the_body_and_the_state_of_before(instance, backup, monkeypatch):
    """(b) B5-1k2: the example (5 accounts, limit 3), confirmed with no body: 202, a plain ``RestoreStatus``, ``pending``;
    ``restore.json`` holds exactly today's fields. A body with a key the confirmation does not know (``remove_user_ids`` of the
    design that is gone) is still 422."""
    print_section("(b) B5-1k2 too many accounts: confirmed")
    stage_id = await check(backup, monkeypatch)
    await over_the_limit(stage_id)
    odd = await apply_api.confirm_with(stage_id, {"remove_user_ids": [backup.ids["carla_k"]]})
    assert odd.status_code == 422, f"the body stays {{owner_user_id}}: {api.shown(odd)}"
    response = await apply_api.confirm(stage_id)
    assert response.status_code == 202, f"accepted: {api.shown(response)}"
    assert set(response.json()) == apply_api.STATUS_FIELDS and response.json()["state"] == "pending", f"a plain RestoreStatus: {response.json()}"
    assert set(on_disk(instance)) == applied.STATE_FIELDS, f"restore.json gains no field: {sorted(set(on_disk(instance)) ^ applied.STATE_FIELDS)}"
    print_success("202, state unchanged")


@pytest.mark.asyncio
async def test_on_a_managed_instance_the_owner_is_chosen_as_before_and_nothing_else_is_asked(instance, backup, monkeypatch):
    """(b) B5-1k2: managed with an owner's address nobody holds, Anna chosen as the owner: ``{"owner_user_id": anna}`` is 202;
    the state records the owner and holds today's fields."""
    apply_api.owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await check(backup, monkeypatch)
    await over_the_limit(stage_id)
    response = await apply_api.confirm_with(stage_id, {"owner_user_id": backup.ids["anna_k"]})
    assert response.status_code == 202, f"accepted: {api.shown(response)}"
    record = on_disk(instance)
    assert record["owner_user_id"] == backup.ids["anna_k"] and set(record) == applied.STATE_FIELDS, f"the owner and today's fields: {record}"
    print_success("managed: 202, owner recorded")


@pytest.mark.asyncio
@pytest.mark.parametrize("now", ["4", "2", None, "not a number"], ids=["raised", "lowered", "removed", "became-invalid"])
async def test_a_limit_changed_since_the_check_is_not_stage_outdated(instance, backup, monkeypatch, now):
    """(b) B5-1k2: checked under a limit of 3, confirmed under another (or none): 202, never 409 ``restore_stage_outdated``."""
    stage_id = await check(backup, monkeypatch)
    await over_the_limit(stage_id)
    if now is None:
        monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LIMIT_VARIABLE, now)
    response = await apply_api.confirm(stage_id)
    assert response.status_code == 202, f"limit 3 at the check, {now!r} now: {api.shown(response)}"
    assert os.path.lexists(apply_api.state_path(instance.root)), "the restore waits"
    print_success(f"3 -> {now!r}: 202")


# =============================================================================
# (c) OpenAPI
# =============================================================================


def test_openapi_documents_the_three_numbers_and_the_code_and_nothing_in_the_confirmation():
    """(c) B5-1k2: ``RestoreStageReport`` has the three fields and ``users_over_limit`` among the warnings; the confirmation's
    body stays ``{owner_user_id}`` and forbids any other key; no route about removing accounts."""
    document = api.restore_app().openapi()
    schemas = document["components"]["schemas"]
    properties = schemas["RestoreStageReport"]["properties"]
    assert set(USERS_FIELDS) <= set(properties), f"[new] B5-1k2: RestoreStageReport documents {USERS_FIELDS}: {sorted(properties)}"
    assert api.enum_of(properties["warnings"]["items"], schemas) >= {CODE}, f"[new] B5-1k2: the Literal of the warnings holds {CODE}: {properties['warnings']}"
    confirm_request = schemas["RestoreConfirmRequest"]
    assert set(confirm_request.get("properties", {})) == {"owner_user_id"} and confirm_request.get("additionalProperties") is False, f"RestoreConfirmRequest stays {{owner_user_id}}: {confirm_request}"
    removal_routes = [path for path in document["paths"] if "removal" in path or "trim" in path]
    assert removal_routes == [], f"no route about removing accounts: {removal_routes}"
    print_success("OpenAPI: three fields, the code, nothing else")
