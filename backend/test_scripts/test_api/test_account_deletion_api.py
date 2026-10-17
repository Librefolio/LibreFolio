"""
Account Deletion API Tests — plan 34_accountAndIdReuse (workstream L), §2.1 and §7 «A, API».

``DELETE /auth/users/me`` used to delete the user row only. ``broker_user_access`` cascades at DB
level, but ``brokers`` has no FK to ``users``: the brokers the user was the LAST OWNER of stayed
behind, ownerless, with their transactions and their BRIM files (§1.1).

The decided contract (developer decisions D6 and «una sola funzione condivisa»):

- ``BrokerService.leave_broker`` is the single rule, unchanged: EDITOR/VIEWER leave, an OWNER
  leaves when another OWNER remains, the LAST owner leaving deletes the broker with its
  transactions (F4);
- ``user_service.delete_user`` applies it to every broker of the account, deletes the user and
  commits; the endpoint removes the BRIM files of the deleted brokers after the commit;
- a transfer from a broker that goes to one that stays leaves its incoming half as the ADJUSTMENT
  a split of the pair leaves (V-3, D-J4; the giving half of a transfer whose receiver goes becomes,
  with decision 47, an ADJUSTMENT handed over at its own broker's Auto cost, or stays a TRANSFER
  when that cost needs a missing conversion), unlinked (``related_transaction_id`` NULL), its
  ``cost_basis_override`` untouched;
- the sole administrator is still refused (400): a product rule, not a technical error. Since plan
  34 step 2 (§3.2) «sole» means the last ACTIVE administrator: login refuses an inactive account,
  so the guard counts the other active administrators (``user_service.count_active_superusers``).
  Since lot A-16 the refusal is coded, as the administrators' 409 for the same rule is: its detail is
  ``SOLE_ADMIN_DELETE_DETAIL``, ``{"error_code": "LAST_ADMIN", "message": "Cannot delete account:
  you are the last active administrator"}``. Red until A-16 on that detail alone: today's handler
  answers the plain string «Cannot delete account: you are the only administrator» (ACCDEL-002,
  ACCDEL-003).

Write-scoped: every user, broker, asset, transaction and file is created here and removed here,
also after a red. Two details keep the physical checks honest under ``--workers``:

- the brokers are created X, Y, Z, W and W survives: X and Z are never the highest broker id while
  W lives, and SQLite without AUTOINCREMENT only ever reuses the highest id (part B of the same
  plan), so no neighbour's new broker can take their id before the checks run;
- every physical read is scoped to this test's own broker ids.

The administrator guard (ACCDEL-002 to ACCDEL-005) runs on a private instance instead: a fresh
SQLite file and BRIM directory under ``tmp_path``, the handler called in-process. The shared lane
always has e2e_test_admin, so «the only active administrator» can be a real state only there, and
nothing of it reaches the lane.

Lot A6a (plan phase01Accounts §A6.1) adds what the account itself can ask before deleting:
``GET /auth/users/me/deletion-preview``, for any signed-in account, 401 without a session, answers
``{user_id, username, brokers_deleted: [{id, name, transactions}], brokers_left: [{id, name, role}],
transfers_unpaired}`` for the caller — the shape of the administrator's ``GET /users/{id}/deletion-preview``
—, both lists by broker id, by the rule above; it writes nothing. ACCDEL-006 and ACCDEL-007 run it on
the lane, on accounts and brokers of their own; red until A6a, the route does not exist. The handler
of ``DELETE /auth/users/me`` moves to ``user_service.delete_account`` in the same lot, its behaviour
unchanged: ACCDEL-001 to ACCDEL-005 hold as they are, and ACCDEL-002 to ACCDEL-005 still call it
with ``response``, ``http_request``, ``current_user`` and ``session``.

ACCDEL-008 (lot A6a) pins the failure path of ``DELETE /auth/users/me`` on a private instance: a
technical failure part-way — after a shared broker was already left inside the transaction — answers
500 «nothing was deleted», leaves every row in place, removes no report file, and logs «Account
deletion failed: nothing was deleted» with the account's ``user_id``. Red until the handler stops
reading ``current_user`` after ``delete_user``'s rollback, which expires it: ``MissingGreenlet``
escapes instead of the 500.

The lot «decide under the write lock» (A-52, A-54; contract approved by the coordinator, 17/10) pins
the decisions of ``DELETE /auth/users/me`` under SQLite's write lock, on a private instance. pysqlite
defers BEGIN to the first write, so nothing holds the rows the handler read until it writes: another
request may commit in between. The window is A-42/A-51's (``_rival_before_the_first_write`` of
``test_admin_bootstrap.py``): the rival commits on another connection right before the handler's
first write. ACCDEL-LOCK-01 (red until A-52): the last two active administrators delete themselves at
once — the second to decide is refused, 400 ``LAST_ADMIN``, nothing of its own deleted; today both go
and no administrator is left. ACCDEL-LOCK-02, a guard: the same window with nothing landing in it, the
administrator goes. ACCDEL-LOCK-03 (red until A-54): the account deleted by another request inside the
window answers 404 «User not found», the body ``GET``/``DELETE /users/{id}`` answer for a missing
account, and deletes nothing else; today the handler deletes rows that are no longer there and answers
200 «Account deleted successfully».
"""

import asyncio
import io
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Union

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import users as users_api
from backend.app.config import is_test_mode
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.services.accounts import user_service
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService
from backend.test_scripts.test_api.test_broker_access_api import (
    API_BASE,
    SOLE_ADMIN_DELETE_DETAIL,
    TIMEOUT,
    bulk_set_access,
    cleanup_owned_user_account,
    create_broker,
    create_user_and_login,
    get_access_list,
    unique_name,
)
from backend.test_scripts.test_db_config import get_test_db_path, verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_services.test_admin_bootstrap import _issuer_engine, _rival_before_the_first_write
from backend.test_scripts.test_utils import print_section, print_success

DEPOSIT_DATE = "2026-01-05"
TRANSFER_DATE = "2026-01-10"
TRANSFER_QUANTITY = Decimal("5")
TRANSFER_COST_BASIS = ("USD", Decimal("50"))
REPORT_CSV = b"date,description,amount,currency\n2026-01-05,account deletion probe,1000.00,EUR\n"
PRIVATE_PASSWORD = "PrivateInstance123!"
ACCOUNT_DELETED = {"message": "Account deleted successfully"}
SELF_PREVIEW_PATH = "/auth/users/me/deletion-preview"
NOTHING_WAS_DELETED = "nothing was deleted"
#: The one event the handler logs when the deletion fails, word for word.
DELETION_FAILED_EVENT = "Account deletion failed: nothing was deleted"
LOG_CANARY = "canary: the capture sees the events of the auth endpoints' own logger"


# ============================================================================
# DATA OWNED BY A TEST
# ============================================================================


@dataclass
class _Owned:
    """Everything a test created, recorded the moment it exists: the cleanup never guesses."""

    users: dict[int, tuple[httpx.AsyncClient, str]] = field(default_factory=dict)
    broker_ids: list[int] = field(default_factory=list)
    asset_ids: list[int] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Scenario:
    """Users A and B and the four brokers of §7: A deletes the account, B looks at what is left."""

    a_id: int
    a_username: str
    b_id: int
    x: int  # A the only OWNER: a DEPOSIT, the TRANSFER's outgoing leg, a BRIM file → goes
    y: int  # A and B both OWNER: the TRANSFER's incoming leg, with a cost_basis_override → stays
    z: int  # A OWNER, B EDITOR, so A is its last owner (F4): a DEPOSIT, a BRIM file → goes
    w: int  # B OWNER, A VIEWER → stays
    x_deposit: int
    x_leg: int
    y_leg: int
    z_deposit: int
    x_file: str
    z_file: str

    @property
    def broker_ids(self) -> list[int]:
        return [self.x, self.y, self.z, self.w]

    @property
    def doomed_transactions(self) -> set[tuple[int, int]]:
        """(transaction id, broker id) of every transaction that must go with X and Z."""
        return {(self.x_deposit, self.x), (self.x_leg, self.x), (self.z_deposit, self.z)}


# ============================================================================
# HELPERS
# ============================================================================


def _test_db_engine() -> AsyncEngine:
    """The runner's migrated test database, never a schema built from metadata nor another engine (as ACCESS-076).

    In test mode the BRIM directory derives from the same lane settings as the database, so this
    also guarantees that the cleanup fallback below removes files from the backend's directory.
    """
    is_test_db, database_url = verify_test_database()
    test_db_path = get_test_db_path().resolve()
    assert is_test_db and is_test_mode() and database_url == f"sqlite:///{test_db_path}", "Physical checks and the cleanup fallback require the configured test database"
    assert test_db_path.is_file(), "The runner must provide the migrated test database"
    engine = get_async_engine()
    assert engine.url.database and Path(engine.url.database).resolve() == test_db_path, "Refusing to use a non-test database engine"
    return engine


def _expect(violations: list[str], ok: bool, message: str) -> None:
    """Record a broken expectation instead of stopping at the first one: the red lists them all."""
    if not ok:
        violations.append(message)


def _cost_basis(transaction: dict) -> Optional[tuple[str, Decimal]]:
    override = transaction.get("cost_basis_override")
    return None if override is None else (override["code"], Decimal(str(override["amount"])))


async def _register(client: httpx.AsyncClient, owned: _Owned, prefix: str) -> tuple[int, str, str]:
    """Register and log in a user of this test; verify it is not the instance's administrator."""
    user_id, username, email, _ = await create_user_and_login(client, unique_name(prefix))
    owned.users[user_id] = (client, username)
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200, me.text
    assert me.json()["user"]["is_superuser"] is False, f"Precondition: {username} registered as the instance's first user, hence its administrator — the api setup (db populate, e2e_test_admin) did not run"
    return user_id, username, email


async def _create_broker_allowing_short(client: httpx.AsyncClient, name: str) -> int:
    """X sends the TRANSFER's outgoing leg without holding the asset: overdraft and shorting on, as in test_transactions_api's pair tests."""
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": True, "allow_asset_shorting": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
    (result,) = resp.json()["results"]
    assert result["success"], resp.text
    return result["broker_id"]


async def _set_access(client: httpx.AsyncClient, broker_id: int, grants: list[tuple[int, str, float]]) -> None:
    resp = await bulk_set_access(client, broker_id, [{"user_id": user_id, "role": role, "share_percentage": share} for user_id, role, share in grants])
    assert resp.status_code == 200, f"Access setup of broker {broker_id} failed: {resp.text}"


async def _commit(client: httpx.AsyncClient, creates: list[dict]) -> dict[int, int]:
    """Commit ``creates`` and return {index in ``creates``: transaction id}."""
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Commit HTTP failed: {resp.text}"
    body = resp.json()
    assert body["committed"] is True, f"Commit rejected: {body.get('issues')}"
    ids = {result["index"]: result["ids"] for result in body["results"] if result["operation"] == "create"}
    assert sorted(ids) == list(range(len(creates))) and all(len(tx_ids) == 1 for tx_ids in ids.values()), body
    return {index: tx_ids[0] for index, tx_ids in ids.items()}


async def _deposit(client: httpx.AsyncClient, broker_id: int) -> int:
    ids = await _commit(client, [{"broker_id": broker_id, "type": "DEPOSIT", "date": DEPOSIT_DATE, "cash": {"code": "EUR", "amount": "1000"}}])
    return ids[0]


async def _transfer(client: httpx.AsyncClient, source: int, target: int, asset_id: int) -> tuple[int, int]:
    """The asset TRANSFER pair of test_transactions_api (TestPairDescriptionTagsValidation): the incoming leg carries the cost basis."""
    link = str(uuid.uuid4())
    description = "Account deletion: transfer X to Y"
    code, amount = TRANSFER_COST_BASIS
    outgoing = {"broker_id": source, "asset_id": asset_id, "type": "TRANSFER", "date": TRANSFER_DATE, "quantity": str(-TRANSFER_QUANTITY), "link_uuid": link, "description": description}
    incoming = {"broker_id": target, "asset_id": asset_id, "type": "TRANSFER", "date": TRANSFER_DATE, "quantity": str(TRANSFER_QUANTITY), "link_uuid": link, "description": description, "cost_basis_override": {"code": code, "amount": str(amount)}}
    ids = await _commit(client, [outgoing, incoming])
    return ids[0], ids[1]


async def _create_asset(client: httpx.AsyncClient, owned: _Owned) -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": unique_name("AccDelAsset"), "asset_type": "STOCK", "currency": TRANSFER_COST_BASIS[0]}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"Asset creation failed: {resp.status_code} {resp.text}"
    (result,) = resp.json()["results"]
    assert result["success"], resp.text
    owned.asset_ids.append(result["asset_id"])
    return result["asset_id"]


async def _upload_report(client: httpx.AsyncClient, broker_id: int, owned: _Owned) -> str:
    files = {"file": (f"{unique_name('accdel_report')}.csv", io.BytesIO(REPORT_CSV), "text/csv")}
    resp = await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": str(broker_id)}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    info = resp.json()
    owned.file_ids.append(info["file_id"])
    assert info["target_broker_id"] == broker_id, info
    return info["file_id"]


async def _read_transactions(client: httpx.AsyncClient, tx_ids: list[int]) -> dict[int, dict]:
    """The transactions among ``tx_ids`` that ``client`` can see, by id."""
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": tx_ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return {transaction["id"]: transaction for transaction in resp.json()}


# ============================================================================
# SCENARIO
# ============================================================================


async def _build_scenario(client_a: httpx.AsyncClient, client_b: httpx.AsyncClient, owned: _Owned) -> _Scenario:
    a_id, a_username, _ = await _register(client_a, owned, "accdel_a")
    b_id, _, _ = await _register(client_b, owned, "accdel_b")

    # Creation order matters: W, which survives, comes last (module docstring).
    x = await _create_broker_allowing_short(client_a, unique_name("AccDelX"))
    owned.broker_ids.append(x)
    y = await create_broker(client_a, unique_name("AccDelY"))
    owned.broker_ids.append(y)
    z = await create_broker(client_a, unique_name("AccDelZ"))
    owned.broker_ids.append(z)
    w = await create_broker(client_b, unique_name("AccDelW"))
    owned.broker_ids.append(w)

    await _set_access(client_a, y, [(a_id, "OWNER", 0.5), (b_id, "OWNER", 0.5)])
    await _set_access(client_a, z, [(a_id, "OWNER", 1.0), (b_id, "EDITOR", 0)])
    await _set_access(client_b, w, [(b_id, "OWNER", 1.0), (a_id, "VIEWER", 0)])

    asset_id = await _create_asset(client_a, owned)
    x_deposit = await _deposit(client_a, x)
    z_deposit = await _deposit(client_a, z)
    x_leg, y_leg = await _transfer(client_a, x, y, asset_id)
    x_file = await _upload_report(client_a, x, owned)
    # Uploaded by the EDITOR: a broker's files go with the broker, whoever sent them.
    z_file = await _upload_report(client_b, z, owned)

    return _Scenario(a_id=a_id, a_username=a_username, b_id=b_id, x=x, y=y, z=z, w=w, x_deposit=x_deposit, x_leg=x_leg, y_leg=y_leg, z_deposit=z_deposit, x_file=x_file, z_file=z_file)


async def _assert_scenario_in_place(client_a: httpx.AsyncClient, client_b: httpx.AsyncClient, engine: AsyncEngine, s: _Scenario) -> None:
    """Presence barrier: every «gone» checked after the deletion was a «there» right before it."""
    expected_grants = {
        s.x: {(s.a_id, "OWNER")},
        s.y: {(s.a_id, "OWNER"), (s.b_id, "OWNER")},
        s.z: {(s.a_id, "OWNER"), (s.b_id, "EDITOR")},
        s.w: {(s.b_id, "OWNER"), (s.a_id, "VIEWER")},
    }
    for broker_id, grants in expected_grants.items():
        # Any authenticated user may read the access list of an existing broker (ACCESS-002).
        items = await get_access_list(client_b, broker_id)
        assert {(item["user_id"], item["role"]) for item in items} == grants, f"Precondition: broker {broker_id} access list {items}"

    legs = await _read_transactions(client_a, [s.x_leg, s.y_leg])
    assert set(legs) == {s.x_leg, s.y_leg}, f"Precondition: A must read both TRANSFER legs: {legs}"
    assert legs[s.x_leg]["related_transaction_id"] == s.y_leg and legs[s.y_leg]["related_transaction_id"] == s.x_leg, f"Precondition: the legs must be linked: {legs}"
    assert legs[s.y_leg]["partner_broker_id"] == s.x and _cost_basis(legs[s.y_leg]) == TRANSFER_COST_BASIS, f"Precondition: incoming leg {legs[s.y_leg]}"

    # 403 is how B sees a file that exists in a broker B cannot access: after the deletion, 404 means gone.
    for client, file_id, status in ((client_a, s.x_file, 200), (client_b, s.x_file, 403), (client_b, s.z_file, 200)):
        resp = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
        assert resp.status_code == status, f"Precondition: file {file_id} expected {status}, got {resp.status_code} {resp.text}"
    assert await asyncio.to_thread(brim_provider.get_file_info, s.x_file) is not None, "Precondition: pytest must see the backend's broker_reports directory, where the cleanup fallback removes leftover files"

    resp = await client_b.get(f"{API_BASE}/brokers/{s.z}", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Precondition: B, EDITOR of Z, must read Z: {resp.status_code}"
    assert s.z_deposit in await _read_transactions(client_b, [s.z_deposit]), "Precondition: B must read Z's DEPOSIT"

    async with AsyncSession(engine) as session:
        brokers = await session.scalars(select(Broker.id).where(Broker.id.in_(s.broker_ids)))
        assert set(brokers.all()) == set(s.broker_ids), "Precondition: the four brokers must exist"
        transactions = await session.execute(select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_([tx_id for tx_id, _ in s.doomed_transactions])))
        assert {tuple(row) for row in transactions.all()} == s.doomed_transactions, "Precondition: X's and Z's transactions must exist"


# ============================================================================
# WHAT MUST HOLD AFTER THE DELETION
# ============================================================================


async def _deleted_broker_violations(client_b: httpx.AsyncClient, engine: AsyncEngine, s: _Scenario) -> list[str]:
    """X and Z: A was their last owner, so the account deletion takes them with their transactions (F4)."""
    violations: list[str] = []
    async with AsyncSession(engine) as session:
        left = await session.scalars(select(Broker.id).where(Broker.id.in_([s.x, s.z])))
        left_ids = set(left.all())
        grants = await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role).where(BrokerUserAccess.broker_id.in_([s.x, s.z])))
        left_grants = sorted(tuple(row) for row in grants.all())
        transactions = await session.scalars(select(Transaction.id).where(Transaction.id.in_([tx_id for tx_id, _ in s.doomed_transactions]), Transaction.broker_id.in_([s.x, s.z])))
        left_transactions = set(transactions.all())
    _expect(violations, not left_ids, f"[new] brokers {sorted(left_ids)} of X={s.x}, Z={s.z} survived the deletion of their last owner; their access rows now: {left_grants} (a broker with none is ownerless, plan §1.1)")
    _expect(violations, not left_transactions, f"[new] transactions {sorted(left_transactions)} of X and Z survived their broker's last owner")

    probes = (
        ("new", f"/brokers/{s.z}", "B, EDITOR of Z, reads it until Z is gone"),
        ("new", f"/brokers/{s.z}/access", "any user reads the access list of an existing broker"),
        ("new", f"/brokers/{s.x}/access", "any user reads the access list of an existing broker"),
        ("guard", f"/brokers/{s.x}", "B never had access to X"),
    )
    for tag, path, why in probes:
        resp = await client_b.get(f"{API_BASE}{path}", timeout=TIMEOUT)
        _expect(violations, resp.status_code == 404, f"[{tag}] GET {path} as B must be 404 once the broker is gone ({why}), got {resp.status_code}")

    resp = await client_b.get(f"{API_BASE}/brokers", params={"include_inaccessible": True}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    listed = {item["id"] for item in resp.json()["items"]} | {item["id"] for item in resp.json()["inaccessible"]}
    _expect(violations, not listed & {s.x, s.z}, f"[new] GET /brokers?include_inaccessible=true as B still lists {sorted(listed & {s.x, s.z})}")
    _expect(violations, s.z_deposit not in await _read_transactions(client_b, [s.z_deposit]), f"[new] B still reads Z's DEPOSIT {s.z_deposit}")
    return violations


async def _file_violations(client_b: httpx.AsyncClient, s: _Scenario) -> list[str]:
    """The BRIM files of a deleted broker go after the commit, before the endpoint answers (as the two existing callers do)."""
    violations: list[str] = []
    for label, file_id in (("X", s.x_file), ("Z", s.z_file)):
        resp = await client_b.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
        _expect(violations, resp.status_code == 404, f"[new] {label}'s BRIM file {file_id} must be deleted with its broker: GET as B answered {resp.status_code} (403 = still on disk, 200 = still readable)")
    return violations


async def _transfer_violations(client_b: httpx.AsyncClient, s: _Scenario) -> list[str]:
    """The incoming leg in Y survives its partner as the ADJUSTMENT a split of the pair leaves (V-3, D-J4): unlinked by delete_by_broker, its cost basis untouched (D6)."""
    violations: list[str] = []
    leg = (await _read_transactions(client_b, [s.y_leg])).get(s.y_leg)
    _expect(violations, leg is not None, f"[guard] the incoming TRANSFER leg {s.y_leg} must survive in Y, which B still owns")
    if leg is None:
        return violations
    _expect(violations, leg["type"] == "ADJUSTMENT", f"[new] the surviving leg must become the ADJUSTMENT a split of the pair leaves (V-3, D-J4), not stay an unpaired TRANSFER: type={leg['type']}")
    _expect(violations, leg["related_transaction_id"] is None, f"[new] the surviving leg must be unlinked: related_transaction_id={leg['related_transaction_id']} (X's leg was {s.x_leg})")
    _expect(violations, leg["partner_broker_id"] is None, f"[new] the surviving leg must lose its partner broker: partner_broker_id={leg['partner_broker_id']} (X was {s.x})")
    _expect(violations, _cost_basis(leg) == TRANSFER_COST_BASIS, f"[guard] cost_basis_override must stay {TRANSFER_COST_BASIS}: {leg['cost_basis_override']}")
    _expect(violations, leg["broker_id"] == s.y and Decimal(str(leg["quantity"])) == TRANSFER_QUANTITY, f"[guard] the leg must stay in Y with quantity {TRANSFER_QUANTITY}: {leg}")
    return violations


async def _surviving_violations(client_b: httpx.AsyncClient, engine: AsyncEngine, s: _Scenario) -> list[str]:
    """Y and W stay with B, its only OWNER; A leaves no access row and no user row behind."""
    violations: list[str] = []
    for label, broker_id in (("Y", s.y), ("W", s.w)):
        resp = await client_b.get(f"{API_BASE}/brokers/{broker_id}", timeout=TIMEOUT)
        _expect(violations, resp.status_code == 200, f"[guard] {label} must survive with B: GET /brokers/{broker_id} answered {resp.status_code}")
        resp = await client_b.get(f"{API_BASE}/brokers/{broker_id}/access", timeout=TIMEOUT)
        grants = {(item["user_id"], item["role"]) for item in resp.json()["items"]} if resp.status_code == 200 else resp.status_code
        _expect(violations, grants == {(s.b_id, "OWNER")}, f"[guard] {label}'s access list must be B as its only OWNER, without A: {grants}")
    async with AsyncSession(engine) as session:
        rows = await session.scalars(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == s.a_id, BrokerUserAccess.broker_id.in_(s.broker_ids)))
        a_grants = sorted(rows.all())
        a_user = await session.scalar(select(User.id).where(User.id == s.a_id, User.username == s.a_username))
    _expect(violations, not a_grants, f"[guard] A keeps access rows on brokers {a_grants}")
    _expect(violations, a_user is None, f"[guard] A's user row {s.a_id} survived the account deletion")
    return violations


# ============================================================================
# CLEANUP — also after a red
# ============================================================================


async def _api_delete_brokers(client: httpx.AsyncClient, broker_ids: set[int]) -> list[str]:
    resp = await client.delete(f"{API_BASE}/brokers", params={"ids": sorted(broker_ids), "force": True}, timeout=TIMEOUT)
    if resp.status_code != 200:
        return [f"DELETE /brokers {sorted(broker_ids)}: {resp.status_code} {resp.text}"]
    results = {result["id"]: result for result in resp.json()["results"]}
    return [f"Broker {broker_id}: {results.get(broker_id)}" for broker_id in sorted(broker_ids) if not (results.get(broker_id) or {}).get("success")]


async def _service_delete_brokers(engine: AsyncEngine, broker_ids: set[int]) -> list[str]:
    """Brokers no user of this test owns any more (on today's code, those A left behind) cannot go through the API."""
    if not broker_ids:
        return []
    async with AsyncSession(engine) as session:
        # user_id is unused with as_user_id="all": no access check, as for a superuser.
        response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker_id, force=True) for broker_id in sorted(broker_ids)], user_id=0, as_user_id="all")
        failed = [result for result in response.results if not result.success]
        if failed:
            await session.rollback()
            return [f"Service cleanup of brokers {sorted(broker_ids)} failed: {failed}"]
        await session.commit()
    return []


async def _remove_brokers(owned: _Owned, engine: AsyncEngine) -> list[str]:
    """Through the API by an owner this test controls; through the service when nobody owns the broker any more."""
    if not owned.broker_ids:
        return []
    async with AsyncSession(engine) as session:
        surviving = await session.scalars(select(Broker.id).where(Broker.id.in_(owned.broker_ids)))
        surviving_ids = set(surviving.all())
        owners = await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id).where(BrokerUserAccess.broker_id.in_(surviving_ids), BrokerUserAccess.role == UserRole.OWNER, BrokerUserAccess.user_id.in_(list(owned.users))))
        owner_rows = sorted(owners.all())
    owner_of: dict[int, int] = {}
    for broker_id, user_id in owner_rows:
        owner_of.setdefault(broker_id, user_id)
    by_owner: dict[int, set[int]] = {}
    for broker_id, user_id in owner_of.items():
        by_owner.setdefault(user_id, set()).add(broker_id)
    errors: list[str] = []
    for user_id, broker_ids in by_owner.items():
        errors += await _api_delete_brokers(owned.users[user_id][0], broker_ids)
    errors += await _service_delete_brokers(engine, surviving_ids - set(owner_of))
    return errors


async def _remove_files(owned: _Owned) -> list[str]:
    """Files of brokers deleted through the API are already gone; this removes the ones a service-level cleanup left."""
    errors: list[str] = []
    for file_id in owned.file_ids:
        if await asyncio.to_thread(brim_provider.get_file_info, file_id) is None:
            continue
        if not await asyncio.to_thread(brim_provider.delete_file, file_id):
            errors.append(f"BRIM file {file_id} could not be removed")
    return errors


async def _authenticated_client(owned: _Owned) -> Optional[httpx.AsyncClient]:
    for client, _username in reversed(list(owned.users.values())):
        if (await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)).status_code == 200:
            return client
    return None


async def _remove_assets(owned: _Owned) -> list[str]:
    """Assets are global: delete the one this test created, once no transaction of its brokers holds it."""
    if not owned.asset_ids:
        return []
    client = await _authenticated_client(owned)
    if client is None:
        return [f"Assets {owned.asset_ids}: no user of this test is left to delete them"]
    resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned.asset_ids}, timeout=TIMEOUT)
    if resp.status_code != 200:
        return [f"DELETE /assets {owned.asset_ids}: {resp.status_code} {resp.text}"]
    failed = [result for result in resp.json()["results"] if not result["success"]]
    return [f"Asset cleanup failed: {failed}"] if failed else []


async def _remove_users(owned: _Owned, engine: AsyncEngine) -> list[str]:
    errors: list[str] = []
    for user_id, (client, username) in reversed(list(owned.users.items())):
        async with AsyncSession(engine) as session:
            still_there = await session.scalar(select(User.id).where(User.id == user_id, User.username == username))
        if still_there is None:
            continue
        error = await cleanup_owned_user_account(client=client, user_id=user_id, engine=engine)
        if error is not None:
            errors.append(error)
    return errors


async def _cleanup(owned: _Owned, engine: AsyncEngine) -> list[str]:
    """Remove what the test created and still exists: brokers, then their leftover files, the asset, the users."""
    errors: list[str] = []
    try:
        errors += await _remove_brokers(owned, engine)
        errors += await _remove_files(owned)
        errors += await _remove_assets(owned)
    finally:
        errors += await _remove_users(owned, engine)
    return errors


# ============================================================================
# THE ADMINISTRATOR GUARD, ON A PRIVATE INSTANCE (plan 34 step 2, §3.2)
# ============================================================================


@dataclass(frozen=True)
class _PrivateInstance:
    """A database and a BRIM directory this test owns entirely, both under its tmp_path."""

    engine: AsyncEngine
    reports_dir: Path


@dataclass(frozen=True)
class _Account:
    """An account of the private instance, created through user_service.create_user as the CLI creates one."""

    username: str
    superuser: bool
    active: bool = True


async def _create_accounts(engine: AsyncEngine, *accounts: _Account) -> dict[str, int]:
    """Create ``accounts`` in order on the private instance; return {username: id}."""
    ids: dict[str, int] = {}
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for account in accounts:
            user, error = await user_service.create_user(session, username=account.username, email=f"{account.username}@example.com", password=PRIVATE_PASSWORD, is_superuser=account.superuser, is_active=account.active)
            assert user is not None, f"Setup: create_user({account.username!r}) failed: {error}"
            ids[account.username] = user.id
    return ids


async def _deactivate(engine: AsyncEngine, username: str) -> None:
    """Deactivate an account through user_service.set_user_active, the path of `dev.py user deactivate`."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        deactivated, error = await user_service.set_user_active(session, username, False)
    assert deactivated, f"Setup: set_user_active({username!r}, False) refused: {error}"


async def _accounts(engine: AsyncEngine) -> dict[str, tuple[bool, bool]]:
    """Every account of the private instance, {username: (is_superuser, is_active)}, read in a fresh session."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(User.username, User.is_superuser, User.is_active))).all()
    return {username: (is_superuser, is_active) for username, is_superuser, is_active in rows}


def _plain_http_request() -> Request:
    """The handler's ``http_request`` over plain HTTP; Host and server make request.url absolute, as uvicorn's always is.

    The Secure attribute of the cookie it clears is not this file's subject: test_auth_api.py (COOKIE-005).
    """
    scope = {
        "type": "http",
        "scheme": "http",
        "method": "DELETE",
        "path": "/api/v1/auth/users/me",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"127.0.0.1")],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
    }
    return Request(scope)


async def _delete_own_account(engine: AsyncEngine, user_id: int) -> Union[dict[str, str], HTTPException]:
    """Call the DELETE /auth/users/me handler as ``user_id``, wired as FastAPI wires the request.

    get_current_user and the handler share the request's session (FastAPI resolves
    get_session_generator once per request, with expire_on_commit=False): the user is loaded
    through it as get_current_user loads it, then the handler runs on it, with a plain-HTTP
    request. The outcome is returned, never raised, so the caller reads the state before
    asserting and a red says what happened.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        current_user = await user_service.get_user_by_id(session, user_id)
        assert current_user is not None and current_user.is_active, f"Precondition: user {user_id} must exist and be active, as get_current_user requires"
        try:
            return await auth_api.delete_own_account(response=Response(), http_request=_plain_http_request(), current_user=current_user, session=session)
        except HTTPException as refusal:
            return refusal


async def _sole_owned_broker(engine: AsyncEngine, owner_id: int) -> tuple[int, int]:
    """A broker of the private instance whose only OWNER is ``owner_id``, with one DEPOSIT; return (broker id, deposit id)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        broker = Broker(name="AccDel sole administrator's broker")
        session.add(broker)
        await session.flush()
        session.add(BrokerUserAccess(user_id=owner_id, broker_id=broker.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        deposit = Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date.fromisoformat(DEPOSIT_DATE), amount=Decimal("1000"), currency="EUR")
        session.add(deposit)
        await session.commit()
        return broker.id, deposit.id


async def _private_report(instance: _PrivateInstance, broker_id: int, user_id: int) -> str:
    """A BRIM report of ``broker_id`` uploaded by ``user_id``, through the service the upload endpoint calls."""
    info = await asyncio.to_thread(brim_provider.save_uploaded_file, REPORT_CSV, "accdel_sole_admin_report.csv", user_id, broker_id)
    assert any(instance.reports_dir.rglob(f"{info.file_id}.json")), f"Report {info.file_id} must be stored under the private {instance.reports_dir}, never in the lane's broker_reports"
    return info.file_id


async def _sole_admin_holdings(instance: _PrivateInstance, broker_id: int, deposit_id: int, file_id: str) -> dict[str, object]:
    """What a refused deletion must leave in place: the accounts, the broker, its access rows, its DEPOSIT and its report."""
    async with AsyncSession(instance.engine) as session:
        broker = await session.scalar(select(Broker.id).where(Broker.id == broker_id))
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role).where(BrokerUserAccess.broker_id == broker_id))).all()
        deposits = (await session.execute(select(Transaction.id, Transaction.broker_id).where(Transaction.id == deposit_id))).all()
    report = await asyncio.to_thread(brim_provider.get_file_info, file_id)
    return {
        "accounts": await _accounts(instance.engine),
        "broker": broker,
        "grants": sorted(tuple(row) for row in grants),
        "deposits": [tuple(row) for row in deposits],
        "report of broker": None if report is None else report.target_broker_id,
    }


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest_asyncio.fixture
async def private_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_PrivateInstance]:
    """An instance this test owns entirely: a fresh SQLite file and a BRIM directory, both under tmp_path.

    «The only active administrator» depends on every account of the instance, and the shared lane
    always has e2e_test_admin and the administrators other units registered: there it could only
    be simulated, by patching the counter the handler happens to call, a patch that simulates
    nothing the day the handler calls another one. Here it is a real state.

    - The schema is SQLModel.metadata with every model imported (backend.app.db.base). NullPool as
      get_async_engine, and backend.app.db.session's connect listener applies the same PRAGMAs
      (foreign_keys, WAL, busy_timeout). Disposed at teardown.
    - The BRIM directory moves with it, because private ids start at 1 like the lane's. A report
      stored for private broker N in the lane's broker_reports would belong to the lane's broker N,
      and the handler's after-commit cleanup of a deleted private broker would remove a neighbour's
      files. Every storage path of brim_provider derives from get_broker_reports_dir, and
      ACCDEL-002 checks that its report really lands here.
    """
    reports_dir = tmp_path / "broker_reports"
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports_dir)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield _PrivateInstance(engine=engine, reports_dir=reports_dir)
    finally:
        await engine.dispose()


# ============================================================================
# TESTS
# ============================================================================


class TestAccountDeletion:
    """DELETE /auth/users/me applies BrokerService.leave_broker to every broker of the account (plan 34, §2.1)."""

    @pytest.mark.asyncio
    async def test_account_deletion_applies_the_last_owner_rule_to_every_broker(self, test_server):
        """ACCDEL-001 — NEW, red until delete_by_broker converts the surviving leg (V-3, D-J4): one account deletion, four brokers, four outcomes of the same rule.

        A and B are this test's own users:
        - X: A the only OWNER; a DEPOSIT, the outgoing leg of an asset TRANSFER to Y, a BRIM file;
        - Y: A and B both OWNER; the incoming leg, with a cost_basis_override;
        - Z: A OWNER, B EDITOR, so A is its last owner (F4); a DEPOSIT, a BRIM file uploaded by B;
        - W: B OWNER, A VIEWER.

        After DELETE /auth/users/me as A, seen by B and in the test database:
        - [new] X and Z are gone: rows, transactions, reads and access lists (404), listings, files (404);
        - [new] the incoming leg in Y becomes the ADJUSTMENT a split of the pair leaves (V-3, D-J4),
          unlinked: related_transaction_id and partner_broker_id null;
        - [guard] that leg keeps its broker, quantity and cost_basis_override;
        - [guard] Y and W survive with B as their only OWNER; A keeps no access row and no user row.

        The account deletion itself is in place (plan 34); what is still red is the conversion of
        the surviving leg (V-3, D-J4): delete_by_broker unlinks it but leaves it a TRANSFER, so the
        final assertion lists the [new] line on its type and no other. Any other line is a
        regression, a [guard] line above all; after the conversion, so is that one.
        """
        print_section("ACCDEL-001: account deletion applies the last-owner rule to every broker")
        engine = _test_db_engine()
        owned = _Owned()

        async with httpx.AsyncClient() as client_a, httpx.AsyncClient() as client_b:
            try:
                s = await _build_scenario(client_a, client_b, owned)
                await _assert_scenario_in_place(client_a, client_b, engine, s)

                resp = await client_a.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
                assert resp.status_code == 200, f"A's account deletion failed: {resp.status_code} {resp.text}"

                violations = await _deleted_broker_violations(client_b, engine, s)
                violations += await _file_violations(client_b, s)
                violations += await _transfer_violations(client_b, s)
                violations += await _surviving_violations(client_b, engine, s)
                assert not violations, "DELETE /auth/users/me broke its contract:\n- " + "\n- ".join(violations)
            finally:
                cleanup_errors = await _cleanup(owned, engine)
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

        print_success("✓ X and Z went with their transactions and files; Y and W stayed with B; the surviving leg is the unlinked ADJUSTMENT a split leaves, with its cost basis")

    @pytest.mark.asyncio
    async def test_sole_administrator_is_still_refused(self, private_instance: _PrivateInstance):
        """ACCDEL-002 — red until A-16 on the refusal's detail alone; the refusal and «nothing touched» are guards,
        green today and after (D6: refusing the last active administrator is a product rule).

        On a private instance (fixture private_instance) «the only administrator» is a real state,
        not a patched counter: the handler counts with count_active_superusers (plan 34 step 2), and
        a patch on that name would simulate nothing the day the handler calls another one. The
        shared admin is never involved: it does not exist there.

        A, the instance's only administrator, is the only OWNER of a broker with a DEPOSIT and a
        BRIM report. C, a regular active user, is there too, so a guard counting active accounts
        instead of active administrators would let A go.

        The refusal must be a 400 and it must come before anything is touched: both accounts, the
        broker, its DEPOSIT, its access row and its BRIM file all still exist afterwards — leaving
        the brokers or cleaning the files before the check would delete them. Its detail is coded
        (A-16), as the administrators' 409 for the same rule: error_code LAST_ADMIN, exactly
        SOLE_ADMIN_DELETE_DETAIL — ``{"error_code": "LAST_ADMIN", "message": "Cannot delete account:
        you are the last active administrator"}``, which the cleanup helpers of the API modules
        recognise. Today the detail is the plain string «Cannot delete account: you are the only
        administrator», with no error_code: that is the red.
        """
        print_section("ACCDEL-002: the sole administrator is still refused, and keeps everything")
        instance = private_instance
        ids = await _create_accounts(instance.engine, _Account("sole_admin", superuser=True), _Account("regular_user", superuser=False))
        broker_id, deposit_id = await _sole_owned_broker(instance.engine, ids["sole_admin"])
        file_id = await _private_report(instance, broker_id, ids["sole_admin"])

        # Presence barrier: every «still there» checked after the refusal was a «there» right before it.
        before = await _sole_admin_holdings(instance, broker_id, deposit_id, file_id)
        expected = {
            "accounts": {"sole_admin": (True, True), "regular_user": (False, True)},
            "broker": broker_id,
            "grants": [(broker_id, ids["sole_admin"], UserRole.OWNER)],
            "deposits": [(deposit_id, broker_id)],
            "report of broker": broker_id,
        }
        assert before == expected, f"Precondition: the private instance must hold {expected}, it holds {before}"

        outcome = await _delete_own_account(instance.engine, ids["sole_admin"])
        after = await _sole_admin_holdings(instance, broker_id, deposit_id, file_id)

        assert isinstance(outcome, HTTPException), f"The only administrator must be refused, the handler answered {outcome!r}; the instance now holds {after}"
        assert outcome.status_code == 400, f"The only administrator must be refused with 400, got {outcome.status_code}: {outcome.detail}"
        assert after == before, f"The refusal must touch nothing: before {before}, after {after}"
        assert isinstance(outcome.detail, dict) and outcome.detail.get("error_code") == "LAST_ADMIN", f"[new] red until A-16: the refusal of the last active administrator must carry error_code LAST_ADMIN, its detail is {outcome.detail!r}"
        assert outcome.detail == SOLE_ADMIN_DELETE_DETAIL, f"The refusal's detail must be exactly {SOLE_ADMIN_DELETE_DETAIL}, got {outcome.detail!r}"

        print_success("✓ Sole administrator refused with the coded 400 (LAST_ADMIN); accounts, broker, transaction, access and file intact")


class TestLastActiveAdministrator:
    """DELETE /auth/users/me refuses the last ACTIVE administrator (plan 34 step 2, §3.2), on a private instance.

    Login refuses an inactive account, so an inactive administrator administers nothing. The handler
    counts the OTHER ACTIVE administrators (user_service.count_active_superusers, the caller
    excluded): when there is none, the coded 400 of the only administrator — error_code LAST_ADMIN,
    SOLE_ADMIN_DELETE_DETAIL since A-16 —, and nothing deleted.
    """

    @pytest.mark.asyncio
    async def test_active_administrator_whose_only_fellow_is_inactive_is_refused(self, private_instance: _PrivateInstance):
        """ACCDEL-003 — red until A-16 on the refusal's detail alone; the refusal and «nothing deleted» are guards,
        green since plan 34 step 2: an inactive fellow administrator does not count.

        A and B are administrators; B is then deactivated through set_user_active (`dev.py user
        deactivate`, allowed because A is active). A asks to delete the account: the same refusal as
        the only administrator — 400, error_code LAST_ADMIN, exactly SOLE_ADMIN_DELETE_DETAIL — and
        both accounts still there afterwards.

        A guard that counted every superuser (count_superusers: 2, B included) would delete A and
        answer {'message': 'Account deleted successfully'}, leaving the instance with B alone, who
        cannot log in: no active administrator. Today the refusal is there, with the plain string
        «Cannot delete account: you are the only administrator» and no error_code: that is the red.
        """
        print_section("ACCDEL-003: the last ACTIVE administrator is refused, an inactive fellow does not count")
        engine = private_instance.engine
        ids = await _create_accounts(engine, _Account("admin_a", superuser=True), _Account("admin_b", superuser=True))
        await _deactivate(engine, "admin_b")
        before = await _accounts(engine)
        assert before == {"admin_a": (True, True), "admin_b": (True, False)}, f"Precondition: A an active administrator, B an inactive one: {before}"

        outcome = await _delete_own_account(engine, ids["admin_a"])
        after = await _accounts(engine)

        assert isinstance(outcome, HTTPException), f"A is the last ACTIVE administrator (B is inactive, and login refuses it): the deletion must be refused with 400 {SOLE_ADMIN_DELETE_DETAIL}, but the handler answered {outcome!r} and left the accounts {after}"
        assert outcome.status_code == 400, f"The refusal must be a 400, got {outcome.status_code}: {outcome.detail}"
        assert after == before, f"The refusal must delete nothing: before {before}, after {after}"
        assert isinstance(outcome.detail, dict) and outcome.detail.get("error_code") == "LAST_ADMIN", f"[new] red until A-16: the refusal of the last active administrator must carry error_code LAST_ADMIN, its detail is {outcome.detail!r}"
        assert outcome.detail == SOLE_ADMIN_DELETE_DETAIL, f"The refusal's detail must be exactly {SOLE_ADMIN_DELETE_DETAIL}, got {outcome.detail!r}"

        print_success("✓ The last active administrator is refused with the coded 400 (LAST_ADMIN); the inactive fellow does not count")

    @pytest.mark.asyncio
    async def test_administrator_with_another_active_administrator_can_delete_the_account(self, private_instance: _PrivateInstance):
        """ACCDEL-004 — GUARD, green today and after: another ACTIVE administrator remains, so A may go.

        A and B are both active administrators. A has no broker, so the after-commit BRIM cleanup
        has nothing to do. The handler returns normally, A is gone and B is untouched.

        This pins that the cure counts the other active administrators instead of refusing every
        administrator: a count stuck at 0 (the stub of today) would refuse A here.
        """
        print_section("ACCDEL-004: an administrator with another active administrator can delete the account")
        engine = private_instance.engine
        ids = await _create_accounts(engine, _Account("admin_a", superuser=True), _Account("admin_b", superuser=True))
        before = await _accounts(engine)
        assert before == {"admin_a": (True, True), "admin_b": (True, True)}, f"Precondition: two active administrators: {before}"

        outcome = await _delete_own_account(engine, ids["admin_a"])
        after = await _accounts(engine)

        assert outcome == ACCOUNT_DELETED, f"B is an active administrator, so A must be allowed to go; the handler answered {outcome!r}, the accounts are now {after}"
        assert after == {"admin_b": (True, True)}, f"A must be gone and B untouched: {after}"

        print_success("✓ Another active administrator remains: the account is deleted")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "others",
        [
            pytest.param((), id="no-administrator-at-all"),
            pytest.param((_Account("inactive_admin", superuser=True, active=False),), id="only-an-inactive-administrator"),
        ],
    )
    async def test_regular_user_is_never_refused_by_the_administrator_guard(self, private_instance: _PrivateInstance, others: tuple[_Account, ...]):
        """ACCDEL-005 — GUARD, green today and after: the guard concerns administrators only.

        A regular user deletes the account in the two states where no other account can
        administer the instance: no administrator at all, or an inactive one only. A guard applied
        to every account would refuse there. The handler returns normally, the regular user is gone
        and nobody else is touched.

        The inactive administrator is created inactive (create_user's is_active). After the cure,
        deactivating the last active administrator is refused, so this state predates the cure.
        """
        print_section("ACCDEL-005: a regular user is never refused by the administrator guard")
        engine = private_instance.engine
        ids = await _create_accounts(engine, _Account("regular_user", superuser=False), *others)
        expected_others = {account.username: (account.superuser, account.active) for account in others}
        before = await _accounts(engine)
        assert before == {"regular_user": (False, True), **expected_others}, f"Precondition: a regular user and no other active administrator: {before}"

        outcome = await _delete_own_account(engine, ids["regular_user"])
        after = await _accounts(engine)

        assert outcome == ACCOUNT_DELETED, f"A regular user is never refused by the administrator guard; the handler answered {outcome!r}, the accounts are now {after}"
        assert after == expected_others, f"The regular user must be gone and nobody else touched: {after}"

        print_success("✓ The regular user's account is deleted: the guard concerns administrators only")


# ============================================================================
# DECIDED UNDER THE WRITE LOCK (lot «decide under the write lock»: A-52, A-54), ON A PRIVATE INSTANCE
# ============================================================================
# pysqlite defers BEGIN to the first write: between the handler's reads — the account get_current_user loaded, the count
# of the other active administrators — and its first write, nothing holds the rows they read, and another request may
# commit there. The window is A-42/A-51's (test_admin_bootstrap.py): the handler runs on an engine of its own — a second
# engine on the instance's file, the only one ``_rival_before_the_first_write`` listens to, and only for that call —, and
# the rival, another request, commits on the instance's engine, another connection, right before the handler's first
# write. Today that write is the deletion's first step; after the cure it is ``begin_writes``, the write lock taken before
# any decision, and the decisions see the rival. The barrier: the rival landed once, right before a write of the handler
# (the statement is reported), its answer and the rows it left as expected.
#
# The account that deletes itself co-owns a broker with ``partner``, an ordinary account: its deletion only leaves that
# broker. A broker of its own would be deleted, and deleting a broker needs the ON DELETE CASCADE of the migrated schema,
# which create_all's lacks (ACCDEL-008): the deletion would fail for that, not for the race.

#: What a rival left once it committed: what it answered — or what escaped it —, and every row of the instance right after it.
Landing = tuple[object, dict[str, list[tuple[object, ...]]]]
#: The body of the 404 that GET and DELETE /users/{id} answer for an account that does not exist (``_user_or_404``).
USER_NOT_FOUND = "User not found"
#: How the account vanishes inside its own deletion's window (A-54): whether it is an administrator — the other branch of
#: the handler's guard —, and who deletes it meanwhile: an administrator through DELETE /users/{id}, or the account itself
#: from another tab, through DELETE /auth/users/me.
BY_AN_ADMINISTRATOR = "an administrator"
BY_ITS_OTHER_TAB = "its other tab"
VANISHED = [
    pytest.param(False, BY_AN_ADMINISTRATOR, id="an-ordinary-account-deleted-by-an-administrator"),
    pytest.param(True, BY_ITS_OTHER_TAB, id="an-administrator-deleted-from-its-other-tab"),
]


@dataclass(frozen=True)
class _Count:
    """One count of the other active administrators (``user_service.count_active_superusers``): whom it left out, what it answered, whether the rival had landed by then."""

    excluding_user_id: Optional[int]
    result: int
    after_the_rival: bool


def _spy_on_the_admin_count(monkeypatch: pytest.MonkeyPatch, landed: list[Landing]) -> list[_Count]:
    """Every count of the other active administrators, in order, through the real function: a spy, not a stand-in — no state is simulated.

    Evidence of what the handler decided on, and when. A cure may count another way: the spy then sees nothing of it,
    and nothing here requires it to.
    """
    real = user_service.count_active_superusers
    counts: list[_Count] = []

    async def count_active_superusers(session: AsyncSession, *, excluding_user_id: Optional[int] = None) -> int:
        result = await real(session, excluding_user_id=excluding_user_id)
        counts.append(_Count(excluding_user_id=excluding_user_id, result=result, after_the_rival=bool(landed)))
        return result

    monkeypatch.setattr(user_service, "count_active_superusers", count_active_superusers)
    return counts


async def _delete_as_administrator(engine: AsyncEngine, admin_id: int, user_id: int) -> Union[Response, HTTPException]:
    """Call the DELETE /users/{user_id} handler as the administrator ``admin_id``, wired as FastAPI wires it: require_admin's account loaded in the request's session. The outcome returned, never raised."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        admin = await user_service.get_user_by_id(session, admin_id)
        assert admin is not None and admin.is_active and admin.is_superuser, f"Precondition: user {admin_id} must be an active administrator, as require_admin requires"
        try:
            return await users_api.delete_account(user_id=user_id, admin=admin, session=session)
        except HTTPException as refusal:
            return refusal


async def _nothing_requested() -> None:
    """No request at all: the window opens and nothing lands in it."""


def _meanwhile(engine: AsyncEngine, request: Callable[[], Awaitable[object]], landed: list[Landing]) -> Callable[[], Awaitable[None]]:
    """The rival: ``request`` — another request, on ``engine``'s connections —, then (what it answered, every row right after it) appended to ``landed``.

    What escapes the request is recorded, not raised: raised inside the window, it would reach the handler under test as
    that handler's own failure.
    """

    async def rival() -> None:
        try:
            answer: object = await request()
        except Exception as escaped:  # recorded for the barrier: see above
            answer = escaped
        landed.append((answer, await _private_rows(engine)))

    return rival


async def _own_deletion_through_the_window(engine: AsyncEngine, user_id: int, rival: Callable[[], Awaitable[None]]) -> tuple[Union[dict[str, str], HTTPException, None], Optional[Exception], list[str]]:
    """``user_id`` deletes its own account on an engine of its own, ``rival`` committing on ``engine`` right before the handler's first write: (what the handler answered, what escaped it instead, the statement the rival ran before).

    The listener is armed on that engine alone and only for this call: the setup, the rival and the reads afterwards
    go through ``engine``, which nothing listens to.
    """
    async with _issuer_engine(engine) as own:
        with _rival_before_the_first_write(own, rival) as fired:
            outcome, escaped = await _attempt_own_deletion(own, user_id)
    return outcome, escaped, list(fired)


async def _accounts_beside_a_shared_broker(engine: AsyncEngine, *accounts: _Account, sharer: str) -> tuple[dict[str, int], int, dict[str, list[tuple[object, ...]]]]:
    """``accounts`` and ``partner``, an ordinary account, then a broker ``sharer`` co-owns with partner, with a DEPOSIT: ({username: id}, the broker's id, every row of the instance).

    Barrier: those accounts, both OWNER grants, the one DEPOSIT, and nothing else.
    """
    ids = await _create_accounts(engine, *accounts, _Account("partner", superuser=False))
    shared, deposit = await _co_owned_broker(engine, (ids[sharer], ids["partner"]))
    rows = await _private_rows(engine)
    expected_accounts = sorted((ids[account.username], account.username, account.active, account.superuser) for account in (*accounts, _Account("partner", superuser=False)))
    assert rows["accounts"] == expected_accounts, f"Precondition: the accounts {expected_accounts}, got {rows['accounts']}"
    assert rows["grants"] == sorted([(shared, ids[sharer], "OWNER"), (shared, ids["partner"], "OWNER")]), f"Precondition: {sharer} and partner both OWNER of the shared broker: {rows['grants']}"
    assert rows["transactions"] == [(deposit, shared)], f"Precondition: one DEPOSIT on the shared broker: {rows['transactions']}"
    return ids, shared, rows


def _without(rows: dict[str, list[tuple[object, ...]]], user_id: int) -> dict[str, list[tuple[object, ...]]]:
    """``rows`` without the account ``user_id`` and its access rows: what deleting that account alone leaves — its broker is shared, so it stays."""
    return {
        **rows,
        "accounts": [row for row in rows["accounts"] if row[0] != user_id],
        "grants": [row for row in rows["grants"] if row[1] != user_id],
    }


def _answered(outcome: object, escaped: Optional[Exception]) -> str:
    """What a handler did, in words, for a failure message."""
    if escaped is not None:
        return f"raised {type(escaped).__name__}: {escaped}"
    if isinstance(outcome, HTTPException):
        return f"answered {outcome.status_code} {outcome.detail!r}"
    if isinstance(outcome, Response):
        return f"answered {outcome.status_code}"
    return f"answered {outcome!r}"


class TestDecidedUnderTheWriteLock:
    """DELETE /auth/users/me decides under SQLite's write lock (lot «decide under the write lock»: A-52, A-54), on a private instance."""

    @pytest.mark.asyncio
    async def test_the_last_two_administrators_deleting_themselves_at_once_leave_one(self, private_instance: _PrivateInstance, monkeypatch: pytest.MonkeyPatch):
        """ACCDEL-LOCK-01 — NEW, red until A-52 (today both go, and the instance is left without an administrator).

        admin_a and admin_b are the instance's only administrators, both active; admin_a co-owns a broker with partner,
        an ordinary account, with a DEPOSIT. admin_a deletes its own account while admin_b's own deletion — DELETE
        /auth/users/me, another request — commits inside the window: after admin_a's handler read what it decides on,
        before its first write. admin_b goes, rightly: when it decided, admin_a was another active administrator. So
        admin_a, by then the last one, must be refused as ACCDEL-002/003 refuse it — 400, error_code LAST_ADMIN, exactly
        SOLE_ADMIN_DELETE_DETAIL — and nothing of its own deleted: the instance exactly as admin_b's deletion left it —
        admin_a active and an administrator, its access to the broker, the broker, the DEPOSIT, partner.

        Today the handler counts the other active administrators before its first write — admin_b, one —, and nothing
        reads them again: admin_b's deletion lands right before admin_a leaves the broker (``DELETE FROM
        broker_user_access``, the deletion's first write), admin_a is deleted too, its access to the broker with it, and
        no administrator is left — partner alone. After the cure the first write is the write lock, taken before the
        guard counts: the count sees admin_b gone.

        Barrier: admin_b's deletion lands once, right before a write of admin_a's handler (the statement is reported),
        answering «Account deleted successfully» and leaving everything else as it was, admin_a an active administrator;
        every count of admin_a's handler saw admin_b before it landed and nobody after; and when admin_a goes anyway, its
        handler had counted admin_b before it landed — the red is the race, not a guard skipped.
        """
        print_section("ACCDEL-LOCK-01: the last two active administrators delete themselves at once: the second is refused")
        engine = private_instance.engine
        ids, _, before = await _accounts_beside_a_shared_broker(engine, _Account("admin_a", superuser=True), _Account("admin_b", superuser=True), sharer="admin_a")
        a, b = ids["admin_a"], ids["admin_b"]
        landed: list[Landing] = []
        counts = _spy_on_the_admin_count(monkeypatch, landed)

        outcome, escaped, fired = await _own_deletion_through_the_window(engine, a, _meanwhile(engine, lambda: _delete_own_account(engine, b), landed))
        after = await _private_rows(engine)

        assert fired and len(landed) == 1, f"barrier: admin_b's deletion must land once, right before a write of admin_a's handler: it ran before {fired}, landed {len(landed)} time(s); admin_a's handler {_answered(outcome, escaped)}"
        b_answer, b_left = landed[0]
        assert (b_answer, b_left) == (ACCOUNT_DELETED, _without(before, b)), f"barrier: admin_b's own deletion must commit while admin_a is an active administrator, and touch nothing else: it answered {b_answer!r} and left {b_left}"
        a_counts = [count for count in counts if count.excluding_user_id == a]
        assert all(count.result == (0 if count.after_the_rival else 1) for count in a_counts), f"barrier: admin_a's handler must count admin_b before its deletion landed, and nobody after: {a_counts}"
        read_before = [count.result for count in a_counts if not count.after_the_rival]
        if outcome == ACCOUNT_DELETED:
            assert read_before, f"barrier: admin_a went without its handler counting the other active administrators before admin_b's deletion landed — a guard skipped, not the race of A-52: {counts}"
        accounts_left = [row[1:] for row in after["accounts"]]
        refused = isinstance(outcome, HTTPException) and outcome.status_code == 400 and isinstance(outcome.detail, dict) and outcome.detail.get("error_code") == "LAST_ADMIN"
        race = f"admin_b's own deletion committed after admin_a's handler had counted the other active administrators {read_before} and before its first write «{fired[0]}»"
        assert refused, f"red until A-52: {race}: admin_a, by then the last active administrator, must be refused with 400 LAST_ADMIN; the handler {_answered(outcome, escaped)}, and the accounts left are (username, active, administrator) {accounts_left}"
        assert outcome.detail == SOLE_ADMIN_DELETE_DETAIL, f"The refusal's detail must be exactly {SOLE_ADMIN_DELETE_DETAIL}, got {outcome.detail!r}"
        assert after == b_left, f"The refusal must delete nothing of admin_a's: the rows as admin_b's deletion left them {b_left}, after {after}"

        print_success("✓ admin_b went first; admin_a, the last active administrator, refused with 400 LAST_ADMIN, nothing of its own deleted")

    @pytest.mark.asyncio
    async def test_with_nothing_landing_in_the_window_the_administrator_goes(self, private_instance: _PrivateInstance):
        """ACCDEL-LOCK-02 — GUARD, green today and after: the control of ACCDEL-LOCK-01, admin_b not deleting itself.

        The same instance and the same window — admin_a's deletion on an engine of its own, the listener armed right
        before its first write — with nothing landing in it. admin_b stays an active administrator, so admin_a may go:
        «Account deleted successfully», admin_a and its access row gone, everything else in place — admin_b, partner,
        the broker with partner its OWNER, the DEPOSIT. The window alone refuses nothing.
        """
        print_section("ACCDEL-LOCK-02: nothing lands in the window: the administrator whose fellow stays goes")
        engine = private_instance.engine
        ids, _, before = await _accounts_beside_a_shared_broker(engine, _Account("admin_a", superuser=True), _Account("admin_b", superuser=True), sharer="admin_a")
        landed: list[Landing] = []

        outcome, escaped, fired = await _own_deletion_through_the_window(engine, ids["admin_a"], _meanwhile(engine, _nothing_requested, landed))
        after = await _private_rows(engine)

        assert fired and landed == [(None, before)], f"barrier: the window must open — right before a write of admin_a's handler: {fired} — with nothing landing in it: {landed}"
        assert outcome == ACCOUNT_DELETED and escaped is None, f"admin_b stays an active administrator, so admin_a must be allowed to go; the handler {_answered(outcome, escaped)}"
        assert after == _without(before, ids["admin_a"]), f"admin_a and its access must be gone, everything else in place: expected {_without(before, ids['admin_a'])}, got {after}"

        print_success("✓ Nothing landed: admin_a went, admin_b and everything else stayed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("leaver_is_admin", "deleter"), VANISHED)
    async def test_an_account_deleted_inside_its_own_deletions_window_answers_404(self, private_instance: _PrivateInstance, leaver_is_admin: bool, deleter: str):
        """ACCDEL-LOCK-03 — NEW, red until A-54 (today «Account deleted successfully», for an account another request deleted).

        leaver co-owns a broker with partner, an ordinary account; root is an active administrator. leaver deletes its
        own account while another request deletes it inside the window — after the handler read it, before its first
        write —: leaver an ordinary account deleted by root through DELETE /users/{id}, or leaver an administrator beside
        root, deleted by its own deletion from another tab. The handler answers 404 with detail «User not found» — the
        body GET and DELETE /users/{id} answer for an account that does not exist — and deletes nothing else: the
        instance exactly as the rival left it — root, partner, the broker with partner its OWNER, the DEPOSIT.

        Today the handler goes on with the account it read: the rival lands right before leaver leaves the broker
        (``DELETE FROM broker_user_access``, the deletion's first write); the handler then deletes leaver's access row
        and leaver's own row, both already gone — no row matches, SQLAlchemy only warns —, changes nothing else and
        answers 200 «Account deleted successfully». After the cure the first write is the write lock, and the account,
        read again under it, is not there.

        Barrier: the rival lands once, right before a write of leaver's handler (the statement is reported), its deletion
        done — 204 from DELETE /users/{id}, «Account deleted successfully» from the other tab —, leaving every row but
        leaver's and its access row.
        """
        print_section(f"ACCDEL-LOCK-03: the account deleted inside its own deletion's window, by {deleter}")
        engine = private_instance.engine
        ids, _, before = await _accounts_beside_a_shared_broker(engine, _Account("root", superuser=True), _Account("leaver", superuser=leaver_is_admin), sharer="leaver")
        root, leaver = ids["root"], ids["leaver"]
        if deleter == BY_ITS_OTHER_TAB:
            request, done = (lambda: _delete_own_account(engine, leaver)), _answered(ACCOUNT_DELETED, None)
        else:
            request, done = (lambda: _delete_as_administrator(engine, root, leaver)), _answered(Response(status_code=204), None)
        landed: list[Landing] = []

        outcome, escaped, fired = await _own_deletion_through_the_window(engine, leaver, _meanwhile(engine, request, landed))
        after = await _private_rows(engine)

        assert fired and len(landed) == 1, f"barrier: leaver's deletion by {deleter} must land once, right before a write of leaver's own handler: it ran before {fired}, landed {len(landed)} time(s); the handler {_answered(outcome, escaped)}"
        rival_answer, rival_left = landed[0]
        assert (_answered(rival_answer, None), rival_left) == (done, _without(before, leaver)), f"barrier: the deletion by {deleter} must commit, taking leaver and its access row and nothing else: it {_answered(rival_answer, None)} and left {rival_left}"
        assert after == rival_left, f"The handler must delete nothing else: the rows as the deletion by {deleter} left them {rival_left}, after {after}; the handler {_answered(outcome, escaped)}"
        not_found = isinstance(outcome, HTTPException) and outcome.status_code == 404 and outcome.detail == USER_NOT_FOUND
        assert not_found, f"red until A-54: leaver was deleted by {deleter} after its own handler read it and before that handler's first write «{fired[0]}»: the handler must answer 404 {USER_NOT_FOUND!r}, the answer for an account that does not exist; it {_answered(outcome, escaped)}"

        print_success(f"✓ Deleted by {deleter} meanwhile: 404 «User not found», nothing else deleted")


# ============================================================================
# WHAT A DELETION WOULD TAKE, ASKED BY THE ACCOUNT ITSELF (lot A6a)
# ============================================================================


async def _broker_facts(engine: AsyncEngine, broker_ids: list[int]) -> tuple[dict[int, str], dict[int, int]]:
    """(name, transaction count) of this test's brokers, by id: read in the test database, scoped to them."""
    async with AsyncSession(engine) as session:
        named = (await session.execute(select(Broker.id, Broker.name).where(Broker.id.in_(broker_ids)))).all()
        counted = (await session.execute(select(Transaction.broker_id, func.count()).where(Transaction.broker_id.in_(broker_ids)).group_by(Transaction.broker_id))).all()
    counts = dict(counted)
    return dict(named), {broker_id: counts.get(broker_id, 0) for broker_id in broker_ids}


def _preview_body(user_id: int, username: str, deleted: list[int], left: dict[int, str], facts: tuple[dict[int, str], dict[int, int]], *, unpaired: int) -> dict:
    """The exact answer of GET /auth/users/me/deletion-preview: both lists by broker id, the role as its value."""
    names, counts = facts
    return {
        "user_id": user_id,
        "username": username,
        "brokers_deleted": [{"id": broker_id, "name": names[broker_id], "transactions": counts[broker_id]} for broker_id in sorted(deleted)],
        "brokers_left": [{"id": broker_id, "name": names[broker_id], "role": role} for broker_id, role in sorted(left.items())],
        "transfers_unpaired": unpaired,
    }


async def _self_preview(client: httpx.AsyncClient) -> tuple[int, object]:
    """(status, body) of GET /auth/users/me/deletion-preview with ``client``'s session, if any; the text when the body is not JSON."""
    resp = await client.get(f"{API_BASE}{SELF_PREVIEW_PATH}", timeout=TIMEOUT)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, resp.text


class TestDeletionPreview:
    """GET /auth/users/me/deletion-preview: what deleting one's own account would take (lot A6a), on the lane."""

    @pytest.mark.asyncio
    async def test_each_account_previews_what_its_deletion_would_take(self, test_server):
        """ACCDEL-006 — NEW (A6a), red today: the route does not exist.

        On the scenario of ACCDEL-001, before anything is deleted, each account asks for itself:
        - A: X and Z would go (A their last OWNER) with their transactions; Y would stay with A an OWNER, W with A a
          VIEWER; one transfer half would be left alone — Y's incoming leg, once X's outgoing leg is gone;
        - B: W would go (B its only OWNER; A only views it), with no transaction; Y would stay with B an OWNER, Z with B
          an EDITOR; no half left alone.
        Names and transaction counts are read from the test database, scoped to this test's brokers. Asking writes
        nothing: the scenario is in place afterwards, files included.
        """
        print_section("ACCDEL-006: each account previews what its deletion would take")
        engine = _test_db_engine()
        owned = _Owned()

        async with httpx.AsyncClient() as client_a, httpx.AsyncClient() as client_b:
            try:
                s = await _build_scenario(client_a, client_b, owned)
                await _assert_scenario_in_place(client_a, client_b, engine, s)
                facts = await _broker_facts(engine, s.broker_ids)

                a_preview = await _self_preview(client_a)
                b_preview = await _self_preview(client_b)

                expected_a = _preview_body(s.a_id, s.a_username, [s.x, s.z], {s.y: "OWNER", s.w: "VIEWER"}, facts, unpaired=1)
                expected_b = _preview_body(s.b_id, owned.users[s.b_id][1], [s.w], {s.y: "OWNER", s.z: "EDITOR"}, facts, unpaired=0)
                violations: list[str] = []
                _expect(violations, a_preview == (200, expected_a), f"A: expected 200 with {expected_a}, got {a_preview}")
                _expect(violations, b_preview == (200, expected_b), f"B: expected 200 with {expected_b}, got {b_preview}")
                try:
                    await _assert_scenario_in_place(client_a, client_b, engine, s)
                except AssertionError as changed:
                    violations.append(f"asking must write nothing, yet the scenario changed: {changed}")
                assert not violations, "GET /auth/users/me/deletion-preview broke its contract:\n- " + "\n- ".join(violations)
            finally:
                cleanup_errors = await _cleanup(owned, engine)
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

        print_success("✓ A would lose X and Z and leave one transfer half alone; B would lose W; nothing written")

    @pytest.mark.asyncio
    async def test_anonymous_gets_401_and_an_account_without_brokers_has_nothing_to_lose(self, test_server):
        """ACCDEL-007 — NEW (A6a), red today: the route does not exist.

        A fresh account of this test, with no broker: 200, exactly {user_id, username, brokers_deleted: [],
        brokers_left: [], transfers_unpaired: 0} — the presence barrier that gives the 401 its meaning. Without a
        session: 401.
        """
        print_section("ACCDEL-007: anonymous 401; an account without brokers has nothing to lose")
        engine = _test_db_engine()
        owned = _Owned()

        async with httpx.AsyncClient() as client, httpx.AsyncClient() as anonymous:
            try:
                user_id, username, _ = await _register(client, owned, "accdel_bare")

                own = await _self_preview(client)
                stranger = await _self_preview(anonymous)

                expected = {"user_id": user_id, "username": username, "brokers_deleted": [], "brokers_left": [], "transfers_unpaired": 0}
                assert own == (200, expected), f"Presence barrier: an account without brokers must get 200 with {expected}, got {own}"
                assert stranger[0] == 401, f"Without a session the preview must be 401, got {stranger}"
            finally:
                cleanup_errors = await _cleanup(owned, engine)
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

        print_success("✓ 200 with nothing to lose for the account; 401 without a session")


# ============================================================================
# A TECHNICAL FAILURE DELETES NOTHING (lot A6a)
# ============================================================================


class _InjectedFailure(RuntimeError):
    """The technical error a test injects half-way through an account deletion."""


async def _co_owned_broker(engine: AsyncEngine, owner_ids: tuple[int, int]) -> tuple[int, int]:
    """A broker of the private instance with two OWNERs, ``owner_ids``, and one DEPOSIT; return (broker id, deposit id)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        broker = Broker(name="AccDel co-owned broker")
        session.add(broker)
        await session.flush()
        session.add_all([BrokerUserAccess(user_id=owner_id, broker_id=broker.id, role=UserRole.OWNER, share_percentage=Decimal("0.5")) for owner_id in owner_ids])
        deposit = Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=date.fromisoformat(DEPOSIT_DATE), amount=Decimal("1000"), currency="EUR")
        session.add(deposit)
        await session.commit()
        return broker.id, deposit.id


async def _private_rows(engine: AsyncEngine) -> dict[str, list[tuple[object, ...]]]:
    """Every account, broker, access row and transaction of the private instance, read in a fresh session: the test owns them all."""
    async with AsyncSession(engine) as session:
        accounts = (await session.execute(select(User.id, User.username, User.is_active, User.is_superuser))).all()
        brokers = (await session.execute(select(Broker.id, Broker.name))).all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id))).all()
    return {
        "accounts": sorted((user_id, username, bool(active), bool(superuser)) for user_id, username, active, superuser in accounts),
        "brokers": sorted(tuple(row) for row in brokers),
        "grants": sorted((broker_id, user_id, UserRole(role).value) for broker_id, user_id, role in grants),
        "transactions": sorted(tuple(row) for row in transactions),
    }


def _delete_bulk_that_fails(shared_id: int, user_id: int, reached: list[tuple[list[int], bool]]) -> Callable[..., Awaitable[Any]]:
    """A ``BrokerService.delete_bulk`` that raises ``_InjectedFailure``, the kind of failure UADM-054 injects.

    Before raising it records what it was asked to delete, and whether ``user_id`` still holds its access to
    ``shared_id`` — read in the deletion's own session, inside its transaction: the evidence that the failure strikes
    part-way, once the shared broker was already left.
    """

    async def delete_bulk(self: BrokerService, items: list[BRDeleteItem], *args: Any, **kwargs: Any) -> Any:
        access = await self.session.scalar(select(BrokerUserAccess.id).where(BrokerUserAccess.broker_id == shared_id, BrokerUserAccess.user_id == user_id))
        reached.append((sorted(item.id for item in items), access is not None))
        raise _InjectedFailure("injected technical failure while deleting a broker the account was the last owner of")

    return delete_bulk


def _spy_on_report_cleanup(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Replace delete_files_for_brokers, under both names a caller may reach, by a spy that removes nothing; the broker ids of each call."""
    calls: list[list[int]] = []

    def delete_files_for_brokers(broker_ids: Any) -> int:
        calls.append([int(broker_id) for broker_id in broker_ids])
        return 0

    monkeypatch.setattr(brim_provider, "delete_files_for_brokers", delete_files_for_brokers)
    monkeypatch.setattr(user_service, "delete_files_for_brokers", delete_files_for_brokers, raising=False)
    return calls


async def _attempt_own_deletion(engine: AsyncEngine, user_id: int) -> tuple[Union[dict[str, str], HTTPException, None], Optional[Exception]]:
    """``_delete_own_account``, with whatever else escapes the handler caught too: (what it answered, what escaped instead).

    The helper's own setup assertions are not the handler's doing: they propagate.
    """
    try:
        return await _delete_own_account(engine, user_id), None
    except AssertionError:
        raise
    except Exception as escaped:  # reported by the test: a red must say what escaped, not stop at it
        return None, escaped


def _answer_violations(outcome: object, escaped: Optional[Exception]) -> list[str]:
    """What is wrong with the handler's answer to the failure: anything but an HTTPException 500 saying «nothing was deleted»."""
    if escaped is not None:
        return [f"the handler must answer HTTPException 500 «{NOTHING_WAS_DELETED}»; instead {type(escaped).__name__} escaped from it ({escaped}), raised while handling {escaped.__context__!r}"]
    if not (isinstance(outcome, HTTPException) and outcome.status_code == 500 and NOTHING_WAS_DELETED in str(outcome.detail)):
        return [f"the handler must answer HTTPException 500 «{NOTHING_WAS_DELETED}», it answered {outcome!r}"]
    return []


class TestTechnicalFailure:
    """DELETE /auth/users/me when the deletion fails half-way: all or nothing (D6), on a private instance."""

    @pytest.mark.asyncio
    async def test_a_failure_part_way_answers_500_logs_it_and_deletes_nothing(self, private_instance: _PrivateInstance, monkeypatch: pytest.MonkeyPatch):
        """ACCDEL-008 — NEW (A6a), red today: the self-deletion twin of UADM-054.

        leaver, an ordinary account, is an OWNER of a broker it shares with partner and the only OWNER of a broker
        created after it, each with a DEPOSIT. Its deletion leaves the shared broker first (lower id), inside the
        transaction, then reaches its own broker, where BrokerService.delete_bulk raises: delete_user rolls back and the
        failure propagates.

        The handler runs on the request's shape: ``_delete_own_account`` loads ``current_user`` in the very session it
        hands to the handler, as get_current_user loads it in the request's session, so the rollback expires the very
        object the handler holds. Expected:
        - an HTTPException 500 whose detail says «nothing was deleted», and nothing else escaping;
        - every row as before: both accounts, leaver's access rows (the shared one restored by the rollback), both
          brokers and their DEPOSITs, partner's access;
        - the report cleanup never called;
        - exactly one structlog event «Account deletion failed: nothing was deleted», carrying leaver's user_id. Barrier
          first: a canary through the auth module's own logger reaches the capture.
        Evidence that the failure struck part-way: delete_bulk is reached once, for leaver's own broker, when leaver's
        access to the shared broker is already gone inside the transaction.

        Red today: the handler's except reads ``current_user.id`` to log, after the rollback expired it; that lazy load
        cannot run outside SQLAlchemy's greenlet, so MissingGreenlet escapes instead of the 500 and the event is never
        logged. create_all's schema is enough here: nothing is deleted on this path, so the ON DELETE CASCADE it lacks is
        never needed.
        """
        print_section("ACCDEL-008: a technical failure part-way answers 500, logs it and deletes nothing")
        engine = private_instance.engine
        ids = await _create_accounts(engine, _Account("leaver", superuser=False), _Account("partner", superuser=False))
        leaver, partner = ids["leaver"], ids["partner"]
        shared, shared_deposit = await _co_owned_broker(engine, (leaver, partner))
        sole, sole_deposit = await _sole_owned_broker(engine, leaver)
        calls = _spy_on_report_cleanup(monkeypatch)
        reached: list[tuple[list[int], bool]] = []
        monkeypatch.setattr(BrokerService, "delete_bulk", _delete_bulk_that_fails(shared, leaver, reached))

        # Presence barrier: every «still there» checked after the failure was a «there» right before it.
        before = await _private_rows(engine)
        assert shared < sole, f"Precondition: the shared broker must have the lower id, so that the deletion leaves it before failing: shared {shared}, sole {sole}"
        assert [row[1] for row in before["accounts"]] == ["leaver", "partner"], f"Precondition: the two accounts: {before}"
        assert before["grants"] == sorted([(shared, leaver, "OWNER"), (shared, partner, "OWNER"), (sole, leaver, "OWNER")]), f"Precondition: the three access rows: {before}"
        assert before["transactions"] == sorted([(shared_deposit, shared), (sole_deposit, sole)]), f"Precondition: one DEPOSIT per broker: {before}"

        with capture_logs() as events:
            auth_api.logger.info(LOG_CANARY)
            outcome, escaped = await _attempt_own_deletion(engine, leaver)
        after = await _private_rows(engine)

        assert any(event.get("event") == LOG_CANARY for event in events), "barrier: the events of the auth module's own logger do not reach capture_logs, so what this test reads of the log proves nothing"
        logged = [event.get("user_id", "<no user_id>") for event in events if event.get("event") == DELETION_FAILED_EVENT]
        violations = _answer_violations(outcome, escaped)
        _expect(violations, reached == [([sole], False)], f"the failure must strike part-way: delete_bulk reached once, for the sole broker {sole}, once the shared broker {shared} was left inside the transaction; reached {reached} as (brokers, access to the shared broker still there)")
        _expect(violations, after == before, f"a failed deletion must change nothing: before {before}, after {after}")
        _expect(violations, calls == [], f"a failed deletion must touch no report file: the cleanup was called with {calls}")
        _expect(violations, logged == [leaver], f"exactly one «{DELETION_FAILED_EVENT}» event carrying user_id {leaver} expected; the events with that message carry the user_ids {logged}")
        assert not violations, "A technical failure of DELETE /auth/users/me must answer 500 and delete nothing:\n- " + "\n- ".join(violations)

        print_success("✓ 500 «nothing was deleted», every row in place, no file touched, the failure logged with the account's id")
