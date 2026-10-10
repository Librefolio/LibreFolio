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
- a transfer between a broker that goes and one that stays keeps its surviving half, unlinked
  (``related_transaction_id`` NULL), its ``cost_basis_override`` untouched;
- the sole administrator is still refused (400): a product rule, not a technical error. Since plan
  34 step 2 (§3.2) «sole» means the last ACTIVE administrator: login refuses an inactive account,
  so the guard counts the other active administrators (``user_service.count_active_superusers``).

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
"""

import asyncio
import io
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Union

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.config import is_test_mode
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.services import brim_provider, user_service
from backend.app.services.broker_service import BrokerService
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
from backend.test_scripts.test_utils import print_section, print_success

DEPOSIT_DATE = "2026-01-05"
TRANSFER_DATE = "2026-01-10"
TRANSFER_QUANTITY = Decimal("5")
TRANSFER_COST_BASIS = ("USD", Decimal("50"))
REPORT_CSV = b"date,description,amount,currency\n2026-01-05,account deletion probe,1000.00,EUR\n"
PRIVATE_PASSWORD = "PrivateInstance123!"
ACCOUNT_DELETED = {"message": "Account deleted successfully"}


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
    """The incoming leg in Y survives its partner: unlinked by delete_by_broker, its cost basis untouched (D6)."""
    violations: list[str] = []
    leg = (await _read_transactions(client_b, [s.y_leg])).get(s.y_leg)
    _expect(violations, leg is not None, f"[guard] the incoming TRANSFER leg {s.y_leg} must survive in Y, which B still owns")
    if leg is None:
        return violations
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
        """ACCDEL-001 — NEW, red today: one account deletion, four brokers, four outcomes of the same rule.

        A and B are this test's own users:
        - X: A the only OWNER; a DEPOSIT, the outgoing leg of an asset TRANSFER to Y, a BRIM file;
        - Y: A and B both OWNER; the incoming leg, with a cost_basis_override;
        - Z: A OWNER, B EDITOR, so A is its last owner (F4); a DEPOSIT, a BRIM file uploaded by B;
        - W: B OWNER, A VIEWER.

        After DELETE /auth/users/me as A, seen by B and in the test database:
        - [new] X and Z are gone: rows, transactions, reads and access lists (404), listings, files (404);
        - [new] the incoming leg in Y is unlinked: related_transaction_id and partner_broker_id null;
        - [guard] that leg keeps its broker, quantity and cost_basis_override;
        - [guard] Y and W survive with B as their only OWNER; A keeps no access row and no user row.

        Today the endpoint deletes the user row only: the final assertion lists the [new] lines and
        no [guard] line. A [guard] line after the fix is a regression.
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

        print_success("✓ X and Z went with their transactions and files; Y and W stayed with B; the surviving leg is unlinked with its cost basis")

    @pytest.mark.asyncio
    async def test_sole_administrator_is_still_refused(self, private_instance: _PrivateInstance):
        """ACCDEL-002 — GUARD, green today and after the fix (D6: refusing the only administrator is a product rule).

        On a private instance (fixture private_instance) «the only administrator» is a real state,
        not a patched counter: today's handler counts with count_superusers, the cure with
        count_active_superusers, and a patch on either name simulates nothing the day the handler
        calls the other. The shared admin is never involved: it does not exist there.

        A, the instance's only administrator, is the only OWNER of a broker with a DEPOSIT and a
        BRIM report. C, a regular active user, is there too, so a guard counting active accounts
        instead of active administrators would let A go.

        The refusal must be the exact 400 the cleanup helpers recognise (SOLE_ADMIN_DELETE_DETAIL),
        and it must come before anything is touched: both accounts, the broker, its DEPOSIT, its
        access row and its BRIM file all still exist afterwards — leaving the brokers or cleaning
        the files before the check would delete them.
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
        assert outcome.detail == SOLE_ADMIN_DELETE_DETAIL, f"Unexpected refusal detail: {outcome.detail}"
        assert after == before, f"The refusal must touch nothing: before {before}, after {after}"

        print_success("✓ Sole administrator refused with the exact 400; accounts, broker, transaction, access and file intact")


class TestLastActiveAdministrator:
    """DELETE /auth/users/me refuses the last ACTIVE administrator (plan 34 step 2, §3.2), on a private instance.

    Login refuses an inactive account, so an inactive administrator administers nothing. The cure
    counts the OTHER ACTIVE administrators (user_service.count_active_superusers, the caller
    excluded): when there is none, the 400 and the message of today, and nothing deleted.
    """

    @pytest.mark.asyncio
    async def test_active_administrator_whose_only_fellow_is_inactive_is_refused(self, private_instance: _PrivateInstance):
        """ACCDEL-003 — NEW, red today: an inactive fellow administrator does not count.

        A and B are administrators; B is then deactivated through set_user_active (`dev.py user
        deactivate`, still allowed after the cure because A is active). A asks to delete the
        account: the same 400 as the only administrator, with the same message, and both accounts
        still there afterwards.

        Today the guard counts every superuser (count_superusers: 2, B included), so the handler
        deletes A and answers {'message': 'Account deleted successfully'}. The instance is left
        with B alone, who cannot log in: no active administrator. That is the red.
        """
        print_section("ACCDEL-003: the last ACTIVE administrator is refused, an inactive fellow does not count")
        engine = private_instance.engine
        ids = await _create_accounts(engine, _Account("admin_a", superuser=True), _Account("admin_b", superuser=True))
        await _deactivate(engine, "admin_b")
        before = await _accounts(engine)
        assert before == {"admin_a": (True, True), "admin_b": (True, False)}, f"Precondition: A an active administrator, B an inactive one: {before}"

        outcome = await _delete_own_account(engine, ids["admin_a"])
        after = await _accounts(engine)

        assert isinstance(outcome, HTTPException), f"[new] A is the last ACTIVE administrator (B is inactive, and login refuses it): the deletion must be refused with 400 «{SOLE_ADMIN_DELETE_DETAIL}», but the handler answered {outcome!r} and left the accounts {after}"
        assert (outcome.status_code, outcome.detail) == (400, SOLE_ADMIN_DELETE_DETAIL), f"The refusal must be today's 400 with today's message, got {outcome.status_code}: {outcome.detail}"
        assert after == before, f"The refusal must delete nothing: before {before}, after {after}"

        print_success("✓ The last active administrator is refused; the inactive fellow does not count")

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
