"""
A backup with more active accounts than ``LIBREFOLIO_MAX_USERS``, restored across the real start sequence and then met by
workstream A's over-limit state (workstream B, lot B5-1k2, last piece; A5-7). Selector: ``e2e backup-roundtrip-over-limit``.

The contract of B5-1k2: a restore never refuses a backup for the number of its accounts. The check reports the numbers
(``users_active``, ``users_limit``, ``users_over_limit``) and the warning ``users_over_limit``; the confirmation takes no
field about accounts and is accepted; the restore brings ALL the backup's data, accounts included. What the instance is
afterwards is A's: while the active accounts outnumber the limit ordinary routes answer ``423 user_limit_exceeded`` (A5-7,
``api/v1/user_limit.py``), an administrator sees ``GET /users/over-limit`` and chooses who keeps the access with ``POST
/users/over-limit/resolve``; the others are deactivated, never deleted.

The scene is the analysis' example: five active accounts (Anna, an administrator; Bruno, an administrator; Carla; Dario;
Elena) and a disabled administrator (Olga), eight brokers with twenty transactions (the brokers of Carla and Elena, among
them), restored on an instance that accepts three accounts.

1. From the app, on a SELF-HOSTED target: the check says 5 / 3 / 2 and carries the warning; the confirmation (no account in
   the body) is 202; after the restart and the start that commits it, every account, broker, access and transaction is there
   (the ledger's control totals are the source's); an administrator and a plain user sign in and meet 423 on a data route;
   the administrator sees the choice and the full backup routes, the plain user only the 423; the administrator keeps three
   accounts (himself and two more); a kept account reaches its data, a deactivated one is refused ``ACCOUNT_DISABLED``;
   still nothing deleted and the totals are the source's.
2. From the app, on a MANAGED target (the pattern of ``test_backup_roundtrip_owner.py``): the same restore; the owner's
   account has its password closed (``link_only``), so the other administrator signs in; 423 on a data route; the choice marks
   the owner as protected; a resolution that does not keep the owner is refused (422 ``PROTECTED_MISSING``, nothing changed);
   one that keeps the owner works.
3. From the COMMAND LINE, self-hosted: ``backup restore ARCHIVE --yes`` exits 0 and leaves the restore pending, with ONE
   ``⚠️`` line that says the numbers and names nobody; the next start commits it and every account is there.

The instances are real servers: ``uvicorn backend.app.main:app`` in a child process in test mode on a data directory of the
test, on a Unix socket in a short folder under ``/tmp`` (``test_backup_roundtrip_owner.Server``, imported): the lane's port,
database and server are never touched. The source is a new instance at the head (a copy of the staging tests' alembic database,
a first start) holding the scene with accounts whose passwords the test knows, archived by ``jobs.run_backup``. A server is
stopped (SIGTERM, which checkpoints the database) before the ledger's control totals are read from its files.

PURE: data directories, archives and sockets of the test. POSIX only.
"""

from __future__ import annotations

import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from backend.app.services.accounts.auth_service import hash_password
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.app.services.platform.instance_backup.totals import ledger_totals_of
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_e2e import test_backup_roundtrip as b3
from backend.test_scripts.test_e2e import test_backup_roundtrip_owner as owner_e2e
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# Autouse and module fixtures of the neighbours, re-exported: the production data directory that must stay absent, the
# folder of the sockets, the real databases.
configured_data_dir = cases.configured_data_dir
socket_dir = owner_e2e.socket_dir
databases = cases.databases

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Unix sockets and process groups are POSIX only")

API = owner_e2e.API
LIMIT = 3
LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
STAGE = owner_e2e.RESTORE_STAGE
REGISTER = f"{API}/auth/register"
BROKERS = f"{API}/brokers"
OVER_LIMIT = f"{API}/users/over-limit"
RESOLVE = f"{API}/users/over-limit/resolve"
#: A route of the full backup of an administrator (A's ``ALLOWED_WHEN_OVER_LIMIT_ADMIN``): cheap, it starts no job.
BACKUP_OPTIONS = f"{API}/backup/instance/options"
USER_LIMIT_EXCEEDED = "user_limit_exceeded"

ACTIVE = ("anna", "bruno", "carla", "dario", "elena")
PASSWORDS = {name: f"{name.title()}-Pass-B51k2-2026!" for name in (*ACTIVE, "olga")}
#: How many brokers each active account owns ALONE in the scene (the choice shows it).
ALONE = {"anna": 1, "bruno": 1, "carla": 2, "dario": 0, "elena": 1}

TARGET_ADMIN = "target_admin"
TARGET_ADMIN_EMAIL = "target.admin@example.com"
TARGET_ADMIN_PASSWORD = "Target-Admin-Pass-2026!"

# =============================================================================
# The scene: the analysis' example (five active accounts, a disabled one, eight brokers, twenty transactions)
# =============================================================================

OWNER, EDITOR, VIEWER = "OWNER", "EDITOR", "VIEWER"
HASH = "$argon2id$v=19$not-a-real-hash"


@dataclass(frozen=True)
class BrokerSpec:
    """A broker of the scene: its name, who holds which role with which share, and how many DEPOSITs it has."""

    key: str
    name: str
    grants: tuple[tuple[str, str, str], ...]
    transactions: int


#: (username, is_active, is_superuser). Olga is an administrator whose account is disabled (never counted).
SCENE_USERS = (("anna", 1, 1), ("bruno", 1, 1), ("carla", 1, 0), ("dario", 1, 0), ("elena", 1, 0), ("olga", 0, 1))
SCENE_BROKERS = (
    BrokerSpec("anna_main", "Anna Main", (("anna", OWNER, "1"),), 2),
    BrokerSpec("bruno_private", "Bruno Private", (("bruno", OWNER, "1"), ("carla", VIEWER, "0")), 1),
    BrokerSpec("carla_fineco", "Carla Fineco", (("carla", OWNER, "1"),), 3),
    BrokerSpec("carla_team", "Carla Team", (("carla", OWNER, "1"), ("dario", EDITOR, "0"), ("bruno", VIEWER, "0")), 2),
    BrokerSpec("dario_shared", "Dario Shared", (("dario", OWNER, "0.5"), ("elena", OWNER, "0.5"), ("bruno", EDITOR, "0")), 2),
    BrokerSpec("elena_solo", "Elena Solo", (("elena", OWNER, "1"), ("dario", VIEWER, "0")), 4),
    BrokerSpec("orphan", "Orphan", (("carla", EDITOR, "0"), ("dario", VIEWER, "0")), 1),
    BrokerSpec("joint", "Joint", (("carla", OWNER, "0.5"), ("elena", OWNER, "0.5"), ("anna", VIEWER, "0")), 5),
)
SCENE_TRANSACTIONS = sum(spec.transactions for spec in SCENE_BROKERS)


def insert_broker(conn: sqlite3.Connection, spec: BrokerSpec, user_ids: dict[str, int]) -> int:
    """``spec`` written through ``conn`` (not committed): the broker, its accesses and its DEPOSITs; the broker's id."""
    broker_id = conn.execute("INSERT INTO brokers (name, created_at, updated_at) VALUES (?, ?, ?)", (spec.name, cases.CREATED, cases.CREATED)).lastrowid
    conn.executemany(
        "INSERT INTO broker_user_access (user_id, broker_id, role, share_percentage, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [(user_ids[holder], broker_id, role, share, cases.CREATED, cases.CREATED) for holder, role, share in spec.grants],
    )
    conn.executemany(cases.INSERT_TRANSACTION, [(broker_id, None, "DEPOSIT", f"2026-01-{day + 1:02d}", "0", "100", "EUR", cases.CREATED, cases.CREATED) for day in range(spec.transactions)])
    return broker_id


def seed(database: Path) -> tuple[dict[str, int], dict[str, int]]:
    """The scene written into ``database`` (a LibreFolio database at the head) with ``sqlite3``, passwords the test knows:
    the ids of the accounts and of the brokers by name/key."""
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.executemany(cases.INSERT_ACCOUNT, [(name, f"{name}.{number}@example.com", hash_password(PASSWORDS[name]), active, admin, cases.CREATED, cases.CREATED) for number, (name, active, admin) in enumerate(SCENE_USERS)])
        user_ids = {name: conn.execute("SELECT id FROM users WHERE username = ?", (name,)).fetchone()[0] for name, _active, _admin in SCENE_USERS}
        broker_ids = {spec.key: insert_broker(conn, spec, user_ids) for spec in SCENE_BROKERS}
    return user_ids, broker_ids


# =============================================================================
# Reading an instance's files (a stopped server's: read-only, the totals as immutable)
# =============================================================================


@dataclass(frozen=True)
class Snapshot:
    """What an instance holds, read from its files: accounts by name, brokers by id, accesses (broker, user) → (role, share),
    transactions per broker, and the ledger's control totals."""

    users: dict[str, dict[str, Any]]
    brokers: dict[int, str]
    accesses: dict[tuple[int, int], tuple[str, float]]
    transactions: dict[int, int]
    totals: dict[str, Any]


def rows(database: Path, sql: str, *params: Any) -> list[tuple]:
    with closing(cases.read_only(database)) as conn:
        return conn.execute(sql, params).fetchall()


def snapshot_of(root: Path) -> Snapshot:
    """The instance at ``root`` (its server stopped, so the write-ahead log is checkpointed)."""
    database = root / DATABASE_ENTRY
    totals = ledger_totals_of(database)
    assert totals is not None, f"the ledger's control totals of {root.name} can be read (is its server stopped?)"
    return Snapshot(
        users=owner_e2e.users_of(root),
        brokers=dict(rows(database, "SELECT id, name FROM brokers")),
        accesses={(broker, user): (role, float(share)) for broker, user, role, share in rows(database, "SELECT broker_id, user_id, role, share_percentage FROM broker_user_access")},
        transactions=dict(rows(database, "SELECT broker_id, count(*) FROM transactions GROUP BY broker_id")),
        totals=totals,
    )


@dataclass(frozen=True)
class Source:
    """The scene's instance (stopped), its archive, and what it holds."""

    root: Path
    archive: Path
    instance_key: str
    user_ids: dict[str, int]
    broker_ids: dict[str, int]
    held: Snapshot


@pytest.fixture(scope="module")
def source(databases, tmp_path_factory) -> Source:
    """A new instance at the head holding the scene, a first start, then its archive."""
    base = tmp_path_factory.mktemp("over-limit-source")
    root = base / "source"
    (root / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(databases.head, root / DATABASE_ENTRY)
    started = b3.start(root, b3.FIRST_START)
    assert started.returncode == 0, f"precondition: the source's first start: {b3.shown(started)}"
    user_ids, broker_ids = seed(root / DATABASE_ENTRY)
    database = root / DATABASE_ENTRY
    assert rows(database, "SELECT count(*) FROM users WHERE is_active = 1")[0][0] == len(ACTIVE), "precondition: five active accounts"
    assert rows(database, "SELECT count(*) FROM users")[0][0] == len(SCENE_USERS), "precondition: six accounts in all"
    key_file = root / "secrets" / "instance.key"
    instance_key = key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else secrets.token_urlsafe(32)
    with pytest.MonkeyPatch.context() as patch:
        configured = cases.configure(patch, base / "configured-data-dir")
        try:
            job, folder = jobs.run_backup(origin="cli", data_dir=root)
        finally:
            get_git_version.cache_clear()
    assert not configured.exists(), f"the backup wrote in the configured data directory: {cases.listing(configured)}"
    assert (job.status, job.error_code) == ("done", None) and job.file_name, f"precondition: the source is archived: {job}"
    held = snapshot_of(root)
    assert sum(held.transactions.values()) == SCENE_TRANSACTIONS and len(held.brokers) == len(SCENE_BROKERS), f"precondition: the scene's ledger: {held.transactions}"
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return Source(root=root, archive=folder / job.file_name, instance_key=instance_key, user_ids=user_ids, broker_ids=broker_ids, held=held)


def selfhosted_variables(source: Source) -> dict[str, str]:
    """A self-hosted instance that accepts three accounts, the source's instance key (every secret of the backup readable)."""
    return {"LIBREFOLIO_PROFILE": "selfhosted", "LIBREFOLIO_INSTANCE_KEY": source.instance_key, LIMIT_VARIABLE: str(LIMIT)}


def managed_variables(source: Source) -> dict[str, str]:
    """A managed instance that accepts three accounts: the owner's address, no SMTP (the owner's link is only in the log)."""
    return {
        "LIBREFOLIO_PROFILE": "managed",
        "LIBREFOLIO_ADMIN_EMAIL": owner_e2e.OWNER_EMAIL,
        "LIBREFOLIO_ADMIN_USERNAME": owner_e2e.SETUP_USERNAME,
        "LIBREFOLIO_INSTANCE_KEY": source.instance_key,
        LIMIT_VARIABLE: str(LIMIT),
    }


# =============================================================================
# What the tests ask of a running target
# =============================================================================


def cookie_of(instance: owner_e2e.Server, name: str) -> str:
    """The session of ``name`` (an account of the backup, its own password); the sign-in must succeed."""
    response = owner_e2e.signed_in(instance, name, PASSWORDS[name])
    assert response.status_code == 200, f"{name} signs in with the password the backup holds: {owner_e2e.shown(response)}"
    cookie = owner_e2e.session_of(response)
    assert cookie, f"{name}'s sign-in sets a session"
    return cookie


def over_limit_users(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["username"]: row for row in body["users"]}


def assert_user_limit_exceeded(response: httpx.Response, who: str) -> None:
    assert (response.status_code, owner_e2e.code_of(response)) == (423, USER_LIMIT_EXCEEDED), f"{who} meets 423 user_limit_exceeded: {owner_e2e.shown(response)}"


def broker_names(response: httpx.Response) -> set[str]:
    assert response.status_code == 200, f"the brokers answer: {owner_e2e.shown(response)}"
    return {item["name"] for item in response.json()["items"]}


def assert_nothing_deleted(source: Source, found: Snapshot) -> None:
    """Every account, broker, access and transaction of the backup is there as it was, and the ledger's totals are the source's."""
    assert set(found.users) == set(source.held.users), f"no account was deleted or added: {sorted(found.users)} / {sorted(source.held.users)}"
    assert {name: row["id"] for name, row in found.users.items()} == {name: row["id"] for name, row in source.held.users.items()}, "every account keeps its id"
    assert found.brokers == source.held.brokers, f"every broker is there: {found.brokers}"
    assert found.transactions == source.held.transactions, f"every broker keeps all its transactions: {found.transactions} / {source.held.transactions}"
    assert found.accesses == source.held.accesses, f"no access moved: missing {sorted(set(source.held.accesses) - set(found.accesses))}, unexpected {sorted(set(found.accesses) - set(source.held.accesses))}"
    assert found.totals == source.held.totals, "the ledger's control totals are exactly the source's"


def active_names(found: Snapshot) -> set[str]:
    return {name for name, row in found.users.items() if row["is_active"]}


def assert_warning_before_credentials(report: dict[str, Any]) -> None:
    warnings = report["warnings"]
    assert warnings.count("users_over_limit") == 1, f"the warning users_over_limit, once: {warnings}"
    assert "credentials_from_backup" in warnings, f"barrier: the backup carries credentials, so its warning has a place to be compared with: {warnings}"
    assert warnings.index("users_over_limit") < warnings.index("credentials_from_backup"), f"users_over_limit comes before credentials_from_backup: {warnings}"


# =============================================================================
# 1. From the app, self-hosted
# =============================================================================


@pytest.fixture(scope="module")
def app_flow(source, tmp_path_factory, socket_dir):
    """The whole restore on a self-hosted target that accepts three accounts, and what an administrator and a user then meet,
    run once. The server is stopped to read the files and started again on the same data."""
    base = tmp_path_factory.mktemp("over-limit-app-target")
    root = base / "target"
    root.mkdir()
    variables = selfhosted_variables(source)
    found = SimpleNamespace(root=root)
    with owner_e2e.server("app", root, socket_dir, base) as target:
        target.start(variables)
        # The first account of an empty instance is an administrator, whatever the registration mode.
        registered = target.call("POST", REGISTER, json={"username": TARGET_ADMIN, "email": TARGET_ADMIN_EMAIL, "password": TARGET_ADMIN_PASSWORD})
        assert registered.status_code == 201, f"precondition: the first account registers: {owner_e2e.shown(registered)}"
        first = owner_e2e.signed_in(target, TARGET_ADMIN, TARGET_ADMIN_PASSWORD)
        cookie = owner_e2e.session_of(first)
        assert first.status_code == 200 and cookie and first.json()["user"]["is_superuser"] is True, f"precondition: the first account is an administrator: {owner_e2e.shown(first)}"
        found.check = owner_e2e.checked(target, cookie, source.archive)
        found.confirmed = target.call("POST", f"{STAGE}/{found.check['stage_id']}/confirm", cookie=cookie, json={})
        assert found.confirmed.status_code == 202, f"the confirmation is never refused for the accounts: {owner_e2e.shown(found.confirmed)}"
        owner_e2e.restarted(target, cookie)

        # A new process, the same variables: the restore applied and committed.
        target.start(variables)
        found.state = b3.restore_state(root)
        target.stop()
        found.restored = snapshot_of(root)
        target.start(variables)

        # Over the limit: an administrator and a plain user.
        found.bruno = cookie_of(target, "bruno")
        found.carla = cookie_of(target, "carla")
        found.bruno_brokers = target.call("GET", BROKERS, cookie=found.bruno)
        found.carla_brokers = target.call("GET", BROKERS, cookie=found.carla)
        found.bruno_choice = target.call("GET", OVER_LIMIT, cookie=found.bruno)
        found.carla_choice = target.call("GET", OVER_LIMIT, cookie=found.carla)
        found.bruno_backup = target.call("GET", BACKUP_OPTIONS, cookie=found.bruno)
        found.carla_backup = target.call("GET", BACKUP_OPTIONS, cookie=found.carla)
        found.anonymous = target.call("GET", BROKERS)

        # The administrator keeps himself, Carla and Dario; Anna and Elena lose the access.
        choice = found.bruno_choice.json()
        found.keep = [row["id"] for row in choice["users"] if row["username"] in ("bruno", "carla", "dario")]
        found.resolved = target.call("POST", RESOLVE, cookie=found.bruno, json={"keep_user_ids": found.keep})
        found.after_choice = target.call("GET", OVER_LIMIT, cookie=found.bruno)
        found.resolved_again = target.call("POST", RESOLVE, cookie=found.bruno, json={"keep_user_ids": found.keep})
        found.carla_after = owner_e2e.signed_in(target, "carla", PASSWORDS["carla"])
        found.carla_brokers_after = target.call("GET", BROKERS, cookie=owner_e2e.session_of(found.carla_after))
        found.bruno_brokers_after = target.call("GET", BROKERS, cookie=found.bruno)
        found.dario_after = owner_e2e.signed_in(target, "dario", PASSWORDS["dario"])
        found.anna_after = owner_e2e.signed_in(target, "anna", PASSWORDS["anna"])
        found.elena_after = owner_e2e.signed_in(target, "elena", PASSWORDS["elena"])
        target.stop()
        found.resolved_snapshot = snapshot_of(root)
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return found


def test_the_check_reports_the_numbers_and_the_warning_and_the_confirmation_is_accepted(app_flow):
    """B5-1k2: 5 active accounts, a limit of 3, 2 over; the warning ``users_over_limit`` before ``credentials_from_backup``; the
    confirmation, with no field about accounts, is 202 (``pending``) — the restore never refuses a backup for its accounts."""
    print_section("B5-1k2 e2e 1a the check and the confirmation")
    report = app_flow.check["report"]
    assert [report.get(name, "<missing>") for name in ("users_active", "users_limit", "users_over_limit")] == [5, 3, 2], f"5 accounts, limit 3, 2 over: {sorted(report)}"
    assert_warning_before_credentials(report)
    assert (app_flow.confirmed.status_code, app_flow.confirmed.json()["state"]) == (202, "pending"), f"confirmed: {owner_e2e.shown(app_flow.confirmed)}"
    print_success("5 / 3 / 2, the warning in place, the confirmation 202")


def test_the_restore_brings_every_account_and_all_the_data(app_flow, source):
    """B5-1k2: the first start commits the restore; nothing is removed for the number of accounts: the six accounts (the five
    active ones still active), every broker, access and transaction, and the ledger's control totals equal the source's."""
    print_section("B5-1k2 e2e 1b the restore keeps everything")
    state = app_flow.state
    assert state is not None and state["status"] == "committed", f"committed by the new process: {state}"
    assert_nothing_deleted(source, app_flow.restored)
    assert active_names(app_flow.restored) == set(ACTIVE), f"the five accounts are still active, Olga still disabled: {sorted(active_names(app_flow.restored))}"
    print_success("six accounts, eight brokers, twenty transactions, the totals of the source")


def test_over_the_limit_the_data_routes_answer_423_and_only_the_administrator_chooses(app_flow, source):
    """A5-7: an administrator and a plain user both sign in, and a data route answers each of them ``423 user_limit_exceeded``
    (an anonymous caller still gets the 401). The administrator reads the choice (the numbers, the five active accounts, how many
    brokers each owns alone, the account that chooses protected as ``you``) and the full backup's routes; the plain user is
    refused all of them with the same 423."""
    print_section("B5-1k2 e2e 1c the instance is over the limit")
    assert_user_limit_exceeded(app_flow.bruno_brokers, "the administrator")
    assert_user_limit_exceeded(app_flow.carla_brokers, "a plain user")
    assert app_flow.anonymous.status_code == 401, f"without a session the answer is the 401 of every route: {owner_e2e.shown(app_flow.anonymous)}"

    assert app_flow.bruno_choice.status_code == 200, f"the administrator reads the choice: {owner_e2e.shown(app_flow.bruno_choice)}"
    choice = app_flow.bruno_choice.json()
    assert (choice["over_limit"], choice["active"], choice["max_users"], choice["max_keep"]) == (True, 5, 3, 3), f"over the limit: {choice}"
    by_name = over_limit_users(choice)
    assert set(by_name) == set(ACTIVE), f"the five active accounts to choose from, not the disabled one: {sorted(by_name)}"
    assert {name: row["id"] for name, row in by_name.items()} == {name: source.user_ids[name] for name in ACTIVE}, "the accounts of the backup, with their ids"
    assert {name: row["is_superuser"] for name, row in by_name.items()} == {"anna": True, "bruno": True, "carla": False, "dario": False, "elena": False}, "who is an administrator"
    assert {name: row["owned_brokers_alone"] for name, row in by_name.items()} == ALONE, "the brokers each account owns alone"
    assert {name: row["protected"] for name, row in by_name.items()} == {"anna": None, "bruno": "you", "carla": None, "dario": None, "elena": None}, "self-hosted: only the administrator who chooses must stay"

    assert app_flow.bruno_backup.status_code == 200, f"the administrator still reaches the full backup: {owner_e2e.shown(app_flow.bruno_backup)}"
    assert_user_limit_exceeded(app_flow.carla_choice, "a plain user asking for the choice")
    assert_user_limit_exceeded(app_flow.carla_backup, "a plain user asking for the full backup")
    print_success("423 for both, the choice and the backup only for the administrator")


def test_the_administrator_keeps_three_accounts_and_the_others_lose_the_access_not_their_data(app_flow, source):
    """A5-7 on a restored instance: the administrator keeps himself, Carla and Dario (200: kept 3, deactivated 2, no invitation);
    the instance is no longer over the limit and a second resolution is 409 ``NOT_OVER_LIMIT``; a kept account reaches its own
    brokers; the deactivated ones are refused ``ACCOUNT_DISABLED`` with their right password. In the files: still six accounts,
    exactly Bruno, Carla and Dario active, every broker (the deactivated accounts' too), access and transaction in place, the
    totals the source's."""
    print_section("B5-1k2 e2e 1d the administrator chooses")
    assert len(app_flow.keep) == 3, f"barrier: three accounts chosen: {app_flow.keep}"
    resolved = app_flow.resolved
    assert resolved.status_code == 200, f"the choice is accepted: {owner_e2e.shown(resolved)}"
    assert resolved.json() == {"kept": 3, "deactivated": 2, "revoked_invites": 0}, f"three kept, two deactivated: {resolved.json()}"
    after = app_flow.after_choice.json()
    assert (app_flow.after_choice.status_code, after["over_limit"], after["users"]) == (200, False, []), f"no longer over the limit: {owner_e2e.shown(app_flow.after_choice)}"
    assert (app_flow.resolved_again.status_code, owner_e2e.code_of(app_flow.resolved_again)) == (409, "NOT_OVER_LIMIT"), f"nothing left to choose: {owner_e2e.shown(app_flow.resolved_again)}"

    assert broker_names(app_flow.carla_brokers_after) >= {"Carla Fineco", "Carla Team", "Joint"}, f"a kept account reaches its brokers: {app_flow.carla_brokers_after.text[:500]}"
    assert broker_names(app_flow.bruno_brokers_after) >= {"Bruno Private"}, "the administrator reaches his"
    assert app_flow.dario_after.status_code == 200, f"a kept account signs in: {owner_e2e.shown(app_flow.dario_after)}"
    for name, response in (("anna", app_flow.anna_after), ("elena", app_flow.elena_after)):
        assert (response.status_code, owner_e2e.code_of(response)) == (403, "ACCOUNT_DISABLED"), f"{name} is refused as a disabled account: {owner_e2e.shown(response)}"
        assert owner_e2e.session_of(response) is None, f"{name} gets no session"

    found = app_flow.resolved_snapshot
    assert active_names(found) == {"bruno", "carla", "dario"}, f"three active accounts: {sorted(active_names(found))}"
    assert_nothing_deleted(source, found)
    names = found.brokers
    assert (names[source.broker_ids["anna_main"]], found.transactions[source.broker_ids["anna_main"]]) == ("Anna Main", 2), "the deactivated Anna's broker and its ledger are there"
    assert (names[source.broker_ids["elena_solo"]], found.transactions[source.broker_ids["elena_solo"]]) == ("Elena Solo", 4), "the deactivated Elena's broker and its ledger are there"
    print_success("3 kept, 2 deactivated (ACCOUNT_DISABLED), nothing deleted, totals equal")


# =============================================================================
# 2. From the app, managed
# =============================================================================


@pytest.fixture(scope="module")
def managed_flow(source, tmp_path_factory, socket_dir):
    """The same restore on a managed target (owner's address in ``LIBREFOLIO_ADMIN_EMAIL``, no SMTP), run once: Anna is chosen as
    the owner, her password is closed (``link_only``), Bruno is the administrator who then chooses."""
    base = tmp_path_factory.mktemp("over-limit-managed-target")
    root = base / "target"
    root.mkdir()
    variables = managed_variables(source)
    anna = source.user_ids["anna"]
    found = SimpleNamespace(root=root)
    with owner_e2e.server("managed", root, socket_dir, base) as target:
        target.start(variables)
        cookie = owner_e2e.first_session(target)
        found.check = owner_e2e.checked(target, cookie, source.archive)
        found.confirmed = target.call("POST", f"{STAGE}/{found.check['stage_id']}/confirm", cookie=cookie, json={"owner_user_id": anna})
        assert found.confirmed.status_code == 202, f"the confirmation with the owner's account: {owner_e2e.shown(found.confirmed)}"
        owner_e2e.restarted(target, cookie)

        target.start(variables)
        found.state = b3.restore_state(root)
        target.stop()
        found.restored = snapshot_of(root)
        target.start(variables)

        found.anna_login = owner_e2e.signed_in(target, "anna", PASSWORDS["anna"])
        found.bruno = cookie_of(target, "bruno")
        found.carla = cookie_of(target, "carla")
        found.bruno_brokers = target.call("GET", BROKERS, cookie=found.bruno)
        found.carla_brokers = target.call("GET", BROKERS, cookie=found.carla)
        found.bruno_choice = target.call("GET", OVER_LIMIT, cookie=found.bruno)

        # Without the owner: refused by A's rule, nothing changed. With the owner: accepted.
        without_owner = [row["id"] for row in found.bruno_choice.json()["users"] if row["username"] in ("bruno", "carla", "dario")]
        with_owner = [row["id"] for row in found.bruno_choice.json()["users"] if row["username"] in ("anna", "bruno", "dario")]
        found.refused = target.call("POST", RESOLVE, cookie=found.bruno, json={"keep_user_ids": without_owner})
        found.choice_after_refusal = target.call("GET", OVER_LIMIT, cookie=found.bruno)
        found.resolved = target.call("POST", RESOLVE, cookie=found.bruno, json={"keep_user_ids": with_owner})
        found.bruno_brokers_after = target.call("GET", BROKERS, cookie=found.bruno)
        found.dario_after = owner_e2e.signed_in(target, "dario", PASSWORDS["dario"])
        found.carla_after = owner_e2e.signed_in(target, "carla", PASSWORDS["carla"])
        found.elena_after = owner_e2e.signed_in(target, "elena", PASSWORDS["elena"])
        target.stop()
        found.resolved_snapshot = snapshot_of(root)
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return found


def test_a_managed_restore_is_never_refused_for_the_accounts_and_keeps_everything(managed_flow, source):
    """B5-1k2 on a managed instance: the same numbers and warning in the check, 202 for a confirmation that names the owner's
    account only; the restore is committed with the owner given (``link_only``) and every account, broker and transaction is there."""
    print_section("B5-1k2 e2e 2a managed: the check and the restore")
    report = managed_flow.check["report"]
    assert [report.get(name, "<missing>") for name in ("users_active", "users_limit", "users_over_limit")] == [5, 3, 2], f"5 accounts, limit 3, 2 over: {sorted(report)}"
    assert_warning_before_credentials(report)
    assert managed_flow.confirmed.json()["state"] == "pending", f"confirmed: {owner_e2e.shown(managed_flow.confirmed)}"
    state = managed_flow.state
    assert state is not None and (state["status"], state["owner_user_id"], state["owner_outcome"]) == ("committed", source.user_ids["anna"], "link_only"), f"committed, Anna is the owner, the link only in the log: {state}"
    restored = managed_flow.restored
    assert_nothing_deleted_but_the_owner(source, restored)
    assert active_names(restored) == set(ACTIVE), f"the five accounts are still active: {sorted(active_names(restored))}"
    assert restored.users["anna"]["is_instance_owner"] is True and restored.users["anna"]["is_superuser"] is True, "Anna is the owner and an administrator"
    print_success("managed: 5 / 3 / 2, committed, Anna the owner, everything in place")


def assert_nothing_deleted_but_the_owner(source: Source, found: Snapshot, deactivated: tuple[str, ...] = ()) -> None:
    """``assert_nothing_deleted`` for a managed restore: the owner's account has the owner's address and the flag now, which the
    source's does not, so the accounts are compared by name, id and state (``deactivated`` ones are inactive now); everything
    else is the source's."""
    assert set(found.users) == set(source.held.users), f"no account was deleted or added: {sorted(found.users)}"
    assert {name: (row["id"], row["is_active"], row["is_superuser"]) for name, row in found.users.items()} == {name: (row["id"], row["is_active"] and name not in deactivated, row["is_superuser"]) for name, row in source.held.users.items()}, "every account keeps its id and its state"
    assert found.brokers == source.held.brokers and found.transactions == source.held.transactions, "every broker and all its transactions are there"
    assert found.accesses == source.held.accesses, "no access moved"
    assert found.totals == source.held.totals, "the ledger's control totals are exactly the source's"


def test_a_managed_instance_over_the_limit_protects_the_owner_in_the_choice(managed_flow, source):
    """A5-7 on a managed instance: the owner's password is closed (her backup password is refused), the other administrator
    signs in and meets 423 on a data route, and the choice marks the owner (only her) as protected ``owner``."""
    print_section("B5-1k2 e2e 2b managed: 423 and the protected owner")
    anna_login = managed_flow.anna_login
    assert anna_login.status_code in (400, 401, 403) and owner_e2e.session_of(anna_login) is None, f"the owner's password of the backup is closed: {owner_e2e.shown(anna_login)}"
    assert_user_limit_exceeded(managed_flow.bruno_brokers, "the other administrator")
    assert_user_limit_exceeded(managed_flow.carla_brokers, "a plain user")
    choice = managed_flow.bruno_choice
    assert choice.status_code == 200, f"the administrator reads the choice: {owner_e2e.shown(choice)}"
    body = choice.json()
    assert (body["over_limit"], body["active"], body["max_users"], body["max_keep"]) == (True, 5, 3, 3), f"over the limit: {body}"
    assert {name: row["protected"] for name, row in over_limit_users(body).items()} == {"anna": "owner", "bruno": None, "carla": None, "dario": None, "elena": None}, "the owner is protected, nobody else"
    print_success("owner: password closed, 423 for the others, the owner protected in the choice")


def test_a_choice_that_drops_the_owner_is_refused_and_one_that_keeps_her_works(managed_flow, source):
    """A5-7: keeping Bruno, Carla and Dario but not the owner is 422 ``PROTECTED_MISSING`` and changes nothing (the instance is
    still over the limit); keeping the owner, Bruno and Dario is 200 (kept 3, deactivated 2); then the administrator reaches his
    brokers, Dario signs in, Carla is refused ``ACCOUNT_DISABLED``; nothing deleted, totals equal."""
    print_section("B5-1k2 e2e 2c managed: the owner must stay")
    refused = managed_flow.refused
    assert (refused.status_code, owner_e2e.code_of(refused)) == (422, "PROTECTED_MISSING"), f"a choice without the owner: {owner_e2e.shown(refused)}"
    assert managed_flow.choice_after_refusal.json()["over_limit"] is True, "nothing changed: still over the limit"
    resolved = managed_flow.resolved
    assert (resolved.status_code, resolved.json()) == (200, {"kept": 3, "deactivated": 2, "revoked_invites": 0}), f"a choice with the owner: {owner_e2e.shown(resolved)}"
    assert broker_names(managed_flow.bruno_brokers_after) >= {"Bruno Private"}, "the administrator reaches his brokers"
    assert managed_flow.dario_after.status_code == 200, f"a kept account signs in: {owner_e2e.shown(managed_flow.dario_after)}"
    for name, response in (("carla", managed_flow.carla_after), ("elena", managed_flow.elena_after)):
        assert (response.status_code, owner_e2e.code_of(response)) == (403, "ACCOUNT_DISABLED"), f"{name} is refused as a disabled account: {owner_e2e.shown(response)}"
    found = managed_flow.resolved_snapshot
    assert active_names(found) == {"anna", "bruno", "dario"}, f"the owner, Bruno and Dario are active: {sorted(active_names(found))}"
    assert_nothing_deleted_but_the_owner(source, found, deactivated=("carla", "elena"))
    print_success("PROTECTED_MISSING, then the owner kept; Carla and Elena deactivated, nothing deleted")


# =============================================================================
# 3. The command line, self-hosted
# =============================================================================


def cli_restore(target: owner_e2e.Server, root: Path, variables: Mapping[str, str], archive: Path) -> subprocess.CompletedProcess[str]:
    """``dev.py backup restore ARCHIVE --yes`` on the stopped instance at ``root``, as the operator runs it."""
    env = b3.child_env(root)
    env.update(LIBREFOLIO_TEST_LANE_ID=target.lane_id, **variables)
    return subprocess.run(
        [sys.executable, str(b3.SCRIPT), "--test-db", "restore", str(archive), "--yes"],
        cwd=root.parent,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=b3.CHILD_TIMEOUT_S,
        check=False,
    )


def test_a_command_line_restore_of_the_same_backup_is_confirmed_with_one_warning_and_keeps_every_account(source, tmp_path, socket_dir):
    """B5-1k2: self-hosted, a limit of 3. ``restore --yes`` exits 0 and leaves the restore pending (no refusal, no ❌ line); the
    output holds ONE ⚠️ line, «The backup holds 5 active accounts; this instance accepts 3 (LIBREFOLIO_MAX_USERS)…», that names
    no account; the next start commits it with all six accounts, their brokers and the source's totals."""
    print_section("B5-1k2 e2e 3 the command line")
    root = tmp_path / "target"
    root.mkdir()
    variables = selfhosted_variables(source)
    with owner_e2e.server("cli", root, socket_dir, tmp_path) as target:
        target.start(variables)
        target.stop()
        confirmed = cli_restore(target, root, variables, source.archive)
        said = confirmed.stdout + confirmed.stderr
        assert confirmed.returncode == 0, f"restore --yes is not refused for the accounts: {owner_e2e.redacted(b3.shown(confirmed))}"
        assert not [line for line in said.splitlines() if line.startswith("❌")], f"no refusal line: {owner_e2e.redacted(said)}"
        lines = [line for line in said.splitlines() if "LIBREFOLIO_MAX_USERS" in line]
        assert len(lines) == 1, f"ONE line about the limit: {owner_e2e.redacted(said)}"
        assert lines[0].startswith("⚠️") and "The backup holds 5 active accounts; this instance accepts 3 (LIBREFOLIO_MAX_USERS)" in lines[0], f"the numbers, as a warning: {lines[0]}"
        assert not [name for name in (*ACTIVE, "olga") if name in lines[0].lower()], f"the line names nobody: {lines[0]}"
        pending = b3.restore_state(root)
        assert pending is not None and (pending["status"], pending["confirmed_via"]) == ("pending", "cli"), f"waiting for the start, confirmed from the command line: {pending}"

        target.start(variables)
        state = b3.restore_state(root)
        assert state is not None and state["status"] == "committed", f"committed by the start: {state}"
        target.stop()
        found = snapshot_of(root)
        assert_nothing_deleted(source, found)
        assert active_names(found) == set(ACTIVE), f"the five accounts are active: {sorted(active_names(found))}"
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    print_success("CLI: confirmed, one warning line, committed, six accounts, totals equal")
