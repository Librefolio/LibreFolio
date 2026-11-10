"""``user_service`` and the deletion of an account: what it would take, the one helper both deletions use, and the hook of lot A7 (plan phase01Accounts §A6.1, lot A6a).

The contract pinned here:

1. ``preview_user_deletion(session, user_id) -> Optional[AccountDeletionPreview]``, ``None`` for an unknown user. Frozen
   dataclasses of ``user_service``: ``AccountDeletionPreview(user_id, username, brokers_deleted, brokers_left,
   transfers_unpaired)``, ``BrokerDeletionItem(broker_id, name, transactions)``, ``BrokerAccessItem(broker_id, name,
   role)``; both lists in broker id order; ``transactions`` is the number of transactions of the broker.
2. The rule is the one ``delete_user`` applies through ``BrokerService.leave_broker``: a broker the user is an OWNER of,
   with no other OWNER row — whoever holds it, an inactive account included —, is deleted with its transactions; on
   every other broker only the user's access goes. Pinned as an EQUIVALENCE: in every scenario, the ids of
   ``brokers_deleted`` are exactly the ``deleted_broker_ids`` of a ``delete_user`` run afterwards on the same data, every
   broker of ``brokers_left`` is still there without the user's access, and nothing else moved.
3. ``transfers_unpaired`` (backlog V-3): the transactions that stay — on any broker not deleted, those the user cannot
   access included — linked to a deleted transaction, in either direction of ``related_transaction_id``: the halves left
   alone, each counted once. A pair inside one deleted broker, or between two deleted brokers, is not counted; nor is a
   pair whose two halves stay.
4. The preview writes nothing: no add, no flush, no commit; the caller's session holds no pending change afterwards, and
   the database is as it was.
5. ``delete_account(session, user) -> AccountDeletionResult(deleted_broker_ids, files_removed)``: ``delete_user``, then,
   after its commit, ``brim_provider.delete_files_for_brokers`` of the deleted brokers, off the event loop
   (``asyncio.to_thread``), once, its count as ``files_removed``; not called when no broker was deleted. A failure of the
   deletion propagates out of ``delete_account``, deletes nothing and touches no file.
6. ``account_protection(user) -> Optional[str]``, a plain function (A7 will give a reason for the paying administrator of
   a managed instance): ``None`` for every account today.

Every database is a private SQLite file under ``tmp_path``: a copy of one taken to head by the real migrations, in a child
process, once for the module (``_alembic_upgrade_head`` of ``test_autoincrement_schema``). Not ``create_all``: the models
do not declare the ``ON DELETE CASCADE`` that ``broker_user_access`` has in ``001_initial`` — the one ``delete_user``
relies on to drop the access rows of a broker it deletes —, so on a ``create_all`` schema every deletion of a broker
fails on a foreign key, and the equivalence could never be shown. Opened as production opens its own: aiosqlite,
NullPool, and the PRAGMA listener of ``backend.app.db.session``, foreign keys on (checked: the cascade needs them). No
lane database, no server, no clock.

The BRIM report directory moves under ``tmp_path`` for every test: private broker ids start at 1 like the lane's, and a
real ``delete_files_for_brokers`` of private broker 1 would remove the reports of the lane's broker 1. The tests about the
reports replace the function with a spy, under both names a caller may reach: ``brim_provider``'s attribute, and the one
``user_service`` would hold after importing it by name. The spy reads the database through a connection of its own, so
"after the commit" is what another connection sees, not what the session believes.

Red until A6a: ``preview_user_deletion``, ``delete_account``, ``account_protection`` and their dataclasses do not exist.
"""

from __future__ import annotations

import contextlib
import inspect
import sqlite3
import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.services.accounts import user_service
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService
from backend.test_scripts.test_db.test_autoincrement_schema import _alembic_upgrade_head
from backend.test_scripts.test_utils import print_section, print_success

OWNER, EDITOR, VIEWER = UserRole.OWNER, UserRole.EDITOR, UserRole.VIEWER

#: The accounts of every scene, by key, and whether each is active: ``u`` is the one whose deletion is previewed.
USERS = {"u": True, "p": True, "q": True, "r": False}
TARGET = "u"
SEEDED_HASH = "$argon2id$seeded-account"  # a marker: the accounts seeded here never log in
TRANSACTION_DATE = date(2026, 1, 5)
#: Far above any id a private database of a few rows reaches.
NEVER_ISSUED_ID = 987_654_321
#: What the spy of delete_files_for_brokers answers: a count no real call on an empty directory could give.
FILES_REMOVED = 7

#: The four types of the preview and of the result, and their fields (contracts 1 and 5).
PREVIEW_TYPES = {
    "AccountDeletionPreview": frozenset({"user_id", "username", "brokers_deleted", "brokers_left", "transfers_unpaired"}),
    "BrokerDeletionItem": frozenset({"broker_id", "name", "transactions"}),
    "BrokerAccessItem": frozenset({"broker_id", "name", "role"}),
}
RESULT_FIELDS = frozenset({"deleted_broker_ids", "files_removed"})


# =============================================================================
# THE SCENES
# =============================================================================


@dataclass(frozen=True)
class _BrokerSpec:
    """A broker of a scene: who holds which role on it, and how many DEPOSITs it has."""

    key: str
    grants: tuple[tuple[str, UserRole], ...]
    deposits: int = 0


@dataclass(frozen=True)
class _Scenario:
    """Brokers in creation order, and what the rule makes of each for ``u``: deleted, or left with ``u``'s role."""

    brokers: tuple[_BrokerSpec, ...]
    deleted: tuple[str, ...]
    left: tuple[tuple[str, UserRole], ...]


SOLE = _BrokerSpec("sole", (("u", OWNER),), deposits=2)
SHARED = _BrokerSpec("shared", (("u", OWNER), ("p", OWNER)), deposits=1)
TEAM = _BrokerSpec("team", (("u", OWNER), ("p", EDITOR), ("q", VIEWER)), deposits=3)
EDITED = _BrokerSpec("edited", (("p", OWNER), ("u", EDITOR)), deposits=1)
VIEWED = _BrokerSpec("viewed", (("q", OWNER), ("u", VIEWER)))
#: The other OWNER is an inactive account: leave_broker counts OWNER rows, whoever holds them.
DORMANT_PARTNER = _BrokerSpec("dormant_partner", (("u", OWNER), ("r", OWNER)), deposits=1)
EMPTY_SOLE = _BrokerSpec("empty_sole", (("u", OWNER),))
#: A broker ``u`` cannot access: it never appears in u's preview.
ELSEWHERE = _BrokerSpec("elsewhere", (("p", OWNER), ("q", VIEWER)), deposits=2)

#: Created in an order that interleaves what goes and what stays, and that their names do not follow.
MIXED = (VIEWED, SOLE, SHARED, TEAM, EDITED, EMPTY_SOLE, DORMANT_PARTNER, ELSEWHERE)
MIXED_DELETED = ("sole", "team", "empty_sole")
MIXED_LEFT = (("viewed", VIEWER), ("shared", OWNER), ("edited", EDITOR), ("dormant_partner", OWNER))

SCENARIOS = [
    pytest.param(_Scenario((SOLE, ELSEWHERE), deleted=("sole",), left=()), id="sole-owner"),
    pytest.param(_Scenario((SHARED,), deleted=(), left=(("shared", OWNER),)), id="two-owners"),
    pytest.param(_Scenario((TEAM,), deleted=("team",), left=()), id="owner-over-an-editor-and-a-viewer"),
    pytest.param(_Scenario((EDITED, VIEWED), deleted=(), left=(("edited", EDITOR), ("viewed", VIEWER))), id="editor-and-viewer-only"),
    pytest.param(_Scenario((DORMANT_PARTNER,), deleted=(), left=(("dormant_partner", OWNER),)), id="the-other-owner-is-inactive"),
    pytest.param(_Scenario(MIXED, deleted=MIXED_DELETED, left=MIXED_LEFT), id="several-brokers-mixed"),
    pytest.param(_Scenario((ELSEWHERE,), deleted=(), left=()), id="no-broker"),
]

NOTHING_DELETED = [
    pytest.param((EDITED, VIEWED, SHARED), id="brokers-it-only-leaves"),
    pytest.param((ELSEWHERE,), id="no-broker"),
]

# The transfer scene (contract 3): D1 and D2 go (u their last OWNER), S1, S2 and S3 stay — S2 without u at all.
TRANSFER_BROKERS = (
    _BrokerSpec("d1", (("u", OWNER),)),
    _BrokerSpec("d2", (("u", OWNER), ("p", EDITOR))),
    _BrokerSpec("s1", (("p", OWNER), ("u", EDITOR))),
    _BrokerSpec("s2", (("p", OWNER),)),
    _BrokerSpec("s3", (("u", OWNER), ("p", OWNER))),
)
#: Each cash leg of the transfer scene, by key: its broker.
TRANSFER_LEGS = {
    "d1_pair": "d1",
    "s1_pair": "s1",
    "d1_out": "d1",
    "s2_in": "s2",
    "s3_out": "s3",
    "d2_in": "d2",
    "d1_inner_a": "d1",
    "d1_inner_b": "d1",
    "d1_cross": "d1",
    "d2_cross": "d2",
    "s1_kept": "s1",
    "s2_kept": "s2",
}
#: ``(a, b)``: ``a.related_transaction_id = b.id``. A pair links both ways; two links go one way only.
TRANSFER_LINKS = (
    ("d1_pair", "s1_pair"),  # a pair across D1 and S1: S1's half stays alone
    ("s1_pair", "d1_pair"),
    ("d1_out", "s2_in"),  # a deleted leg points at S2's, which points nowhere: S2's stays alone
    ("s3_out", "d2_in"),  # S3's leg points at a deleted one, which points nowhere: S3's stays alone
    ("d1_inner_a", "d1_inner_b"),  # a pair inside D1: both go
    ("d1_inner_b", "d1_inner_a"),
    ("d1_cross", "d2_cross"),  # a pair between D1 and D2: both go
    ("d2_cross", "d1_cross"),
    ("s1_kept", "s2_kept"),  # a pair between two brokers that stay: untouched
    ("s2_kept", "s1_kept"),
)
#: The halves the deletion leaves alone.
UNPAIRED = frozenset({"s1_pair", "s2_in", "s3_out"})


@dataclass(frozen=True)
class _Scene:
    """What a scene became in the database: ids and names, by key."""

    users: dict[str, int]
    usernames: dict[str, str]
    brokers: dict[str, int]
    names: dict[str, str]


@dataclass(frozen=True)
class _State:
    """Every row a deletion can touch, read in a fresh session: the database belongs to the test, all of it."""

    users: frozenset[int]
    brokers: frozenset[int]
    grants: frozenset[tuple[int, int, UserRole]]
    transactions: frozenset[tuple[int, int, Optional[int]]]


@dataclass(frozen=True)
class _FilesCall:
    """One call of the report-files spy: the broker ids, whether it ran on the event loop's thread, and what another connection saw then."""

    broker_ids: tuple[int, ...]
    on_the_loop: bool
    account_rows: int
    deleted_brokers_still_there: tuple[int, ...]


@dataclass
class _Writes:
    """What a session under watch did: its flushes of pending changes, its commits."""

    flushes: int = 0
    commits: int = 0


class _InjectedFailure(RuntimeError):
    """The technical error a test injects half-way through an account deletion."""


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def private_reports_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The BRIM report directory under tmp_path: whatever reaches brim_provider here never touches the lane's reports."""
    reports = tmp_path / "broker_reports"
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    return reports


@pytest.fixture(scope="module")
def head_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations, in a child process, once for the module. Read-only: each test works on a copy."""
    data_dir = tmp_path_factory.mktemp("account-deletion-head") / "data"
    db = data_dir / "sqlite" / "app.db"
    _alembic_upgrade_head(db, data_dir)
    return db


@pytest.fixture
def database(head_template: Path, tmp_path: Path) -> Path:
    """This test's private database: a consistent copy of the template, through SQLite's backup API."""
    target = tmp_path / "accounts.db"
    with contextlib.closing(sqlite3.connect(head_template)) as source, contextlib.closing(sqlite3.connect(target)) as copy:
        source.backup(copy)
    return target


@pytest_asyncio.fixture
async def engine(database: Path) -> AsyncIterator[AsyncEngine]:
    """The private database opened as production opens its own, foreign keys on; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            foreign_keys = (await connection.exec_driver_sql("PRAGMA foreign_keys")).scalar_one()
        assert foreign_keys == 1, "barrier: foreign keys must be on, as backend.app.db.session turns them on in production: the cascade of broker_user_access needs them"
        yield engine
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS — writing a scene
# =============================================================================


def _deposit(broker_id: int) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=TRANSACTION_DATE, amount=Decimal("100"), currency="EUR")


def _cash_leg(broker_id: int) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.CASH_TRANSFER, date=TRANSACTION_DATE, amount=Decimal("10"), currency="EUR")


async def _seed(engine: AsyncEngine, brokers: tuple[_BrokerSpec, ...]) -> _Scene:
    """The four accounts of USERS and ``brokers``, in this order, with their grants and DEPOSITs; committed."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        accounts = {key: User(username=f"preview_{key}", email=f"preview_{key}@example.com", hashed_password=SEEDED_HASH, is_active=active) for key, active in USERS.items()}
        rows = {spec.key: Broker(name=f"Preview {spec.key}") for spec in brokers}
        session.add_all([*accounts.values(), *rows.values()])
        await session.flush()
        for spec in brokers:
            broker_id = rows[spec.key].id
            session.add_all([BrokerUserAccess(user_id=accounts[holder].id, broker_id=broker_id, role=role, share_percentage=Decimal("0")) for holder, role in spec.grants])
            session.add_all([_deposit(broker_id) for _ in range(spec.deposits)])
        await session.commit()
    return _Scene(
        users={key: user.id for key, user in accounts.items()},
        usernames={key: user.username for key, user in accounts.items()},
        brokers={key: broker.id for key, broker in rows.items()},
        names={key: broker.name for key, broker in rows.items()},
    )


async def _seed_legs(engine: AsyncEngine, scene: _Scene) -> dict[str, int]:
    """The cash legs of TRANSFER_LEGS, linked as TRANSFER_LINKS says; their ids, by key."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        legs = {key: _cash_leg(scene.brokers[broker]) for key, broker in TRANSFER_LEGS.items()}
        session.add_all(legs.values())
        await session.flush()
        for source, target in TRANSFER_LINKS:
            legs[source].related_transaction_id = legs[target].id
        await session.commit()
    return {key: leg.id for key, leg in legs.items()}


# =============================================================================
# HELPERS — reading the database
# =============================================================================


async def _state(engine: AsyncEngine) -> _State:
    async with AsyncSession(engine) as session:
        users = (await session.execute(select(User.id))).scalars().all()
        brokers = (await session.execute(select(Broker.id))).scalars().all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id, Transaction.related_transaction_id))).all()
    return _State(
        users=frozenset(users),
        brokers=frozenset(brokers),
        grants=frozenset((broker_id, user_id, UserRole(role)) for broker_id, user_id, role in grants),
        transactions=frozenset((tx_id, broker_id, related) for tx_id, broker_id, related in transactions),
    )


def _after_deletion(before: _State, user_id: int, deleted: set[int]) -> _State:
    """What deleting ``user_id`` leaves when the brokers ``deleted`` go: those brokers with their transactions and grants, the account with its grants, and a surviving link to a transaction that went, cleared — nothing else."""
    gone = {tx_id for tx_id, broker_id, _ in before.transactions if broker_id in deleted}
    return _State(
        users=before.users - {user_id},
        brokers=before.brokers - deleted,
        grants=frozenset(grant for grant in before.grants if grant[0] not in deleted and grant[1] != user_id),
        transactions=frozenset((tx_id, broker_id, None if related in gone else related) for tx_id, broker_id, related in before.transactions if broker_id not in deleted),
    )


def _left_alone(legs: dict[str, int], present: frozenset[int]) -> set[str]:
    """The legs still there that a link, in either direction, tied to a leg that is gone."""
    alone: set[str] = set()
    for source, target in TRANSFER_LINKS:
        for kept, other in ((source, target), (target, source)):
            if legs[kept] in present and legs[other] not in present:
                alone.add(kept)
    return alone


# =============================================================================
# HELPERS — calling the service as its callers do
# =============================================================================


def _watch_writes(session: AsyncSession, writes: _Writes) -> None:
    """Count the flushes of pending changes and the commits of ``session``: a flush with nothing pending fires no event."""

    def flushed(*_: Any) -> None:
        writes.flushes += 1

    def committed(*_: Any) -> None:
        writes.commits += 1

    event.listen(session.sync_session, "before_flush", flushed)
    event.listen(session.sync_session, "after_commit", committed)


async def _preview(engine: AsyncEngine, user_id: int) -> Any:
    """``preview_user_deletion`` in a session of its own, proven to write nothing (contract 4): no flush, no commit, nothing pending, the database as it was."""
    before = await _state(engine)
    writes = _Writes()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        _watch_writes(session, writes)
        preview = await user_service.preview_user_deletion(session, user_id)
        pending = {"new": list(session.new), "dirty": list(session.dirty), "deleted": list(session.deleted)}
    after = await _state(engine)
    assert (writes.flushes, writes.commits) == (0, 0), f"the preview of user {user_id} must neither flush nor commit: {writes}"
    assert pending == {"new": [], "dirty": [], "deleted": []}, f"the preview of user {user_id} left changes pending in the caller's session: {pending}"
    assert after == before, f"the preview of user {user_id} changed the database: before {before}, after {after}"
    return preview


async def _delete_user(engine: AsyncEngine, user_id: int) -> Any:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await user_service.delete_user(session, user_id)


async def _delete_account(engine: AsyncEngine, user_id: int) -> Any:
    """``delete_account`` as its callers call it: on the account loaded in the session it runs in."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await user_service.get_user_by_id(session, user_id)
        assert user is not None, f"setup: account {user_id} must exist"
        return await user_service.delete_account(session, user)


async def _outcome(call: Awaitable[Any]) -> tuple[Any, Optional[BaseException]]:
    """(returned value, raised exception): which of the two happens is what the test asserts."""
    try:
        return await call, None
    except Exception as exc:  # the assertions decide which exception is acceptable
        return None, exc


def _caused_by(failure: Optional[BaseException], kind: type[BaseException]) -> bool:
    """True when ``failure`` is ``kind`` or carries it in its cause chain: wrapping is allowed, swallowing is not."""
    seen: set[int] = set()
    while failure is not None and id(failure) not in seen:
        if isinstance(failure, kind):
            return True
        seen.add(id(failure))
        failure = failure.__cause__ or failure.__context__
    return False


async def _failing_delete_bulk(self: BrokerService, *args: Any, **kwargs: Any) -> Any:
    raise _InjectedFailure("injected technical failure while deleting a broker")


def _files_spy(db: Path, user_id: int, calls: list[_FilesCall]) -> Callable[[Any], int]:
    """A stand-in for ``delete_files_for_brokers`` that records each call and answers FILES_REMOVED.

    Built on the event loop's thread, it knows that thread. At each call it opens its own connection to ``db``: once the
    deletion is committed that connection sees ``user_id`` and the deleted brokers gone; before, it sees them all.
    """
    loop_thread = threading.get_ident()

    def delete_files_for_brokers(broker_ids: Any) -> int:
        ids = tuple(int(broker_id) for broker_id in broker_ids)
        with contextlib.closing(sqlite3.connect(db)) as connection:
            account_rows = connection.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,)).fetchone()[0]
            present = {row[0] for row in connection.execute("SELECT id FROM brokers")}
        calls.append(_FilesCall(ids, threading.get_ident() == loop_thread, account_rows, tuple(sorted(present & set(ids)))))
        return FILES_REMOVED

    return delete_files_for_brokers


def _replace_report_cleanup(monkeypatch: pytest.MonkeyPatch, spy: Callable[[Any], int]) -> None:
    """The spy under both names a caller may reach: brim_provider's attribute, and the name user_service would hold after importing it."""
    monkeypatch.setattr(brim_provider, "delete_files_for_brokers", spy)
    monkeypatch.setattr(user_service, "delete_files_for_brokers", spy, raising=False)


# =============================================================================
# HELPERS — reading a preview
# =============================================================================


def _plain(preview: Any) -> tuple[Any, ...]:
    """A preview as plain values, each list in the order given: what the comparisons read."""
    return (
        preview.user_id,
        preview.username,
        [(item.broker_id, item.name, item.transactions) for item in preview.brokers_deleted],
        [(item.broker_id, item.name, UserRole(item.role)) for item in preview.brokers_left],
        preview.transfers_unpaired,
    )


def _expected(scene: _Scene, scenario: _Scenario) -> tuple[Any, ...]:
    """The preview of ``u`` a scenario implies: its deleted brokers with their DEPOSITs, its left ones with u's role, both by id; no transfer."""
    deposits = {spec.key: spec.deposits for spec in scenario.brokers}
    deleted = sorted((scene.brokers[key], scene.names[key], deposits[key]) for key in scenario.deleted)
    left = sorted((scene.brokers[key], scene.names[key], role) for key, role in scenario.left)
    return (scene.users[TARGET], scene.usernames[TARGET], deleted, left, 0)


def _type_violations(preview: Any) -> list[str]:
    violations: list[str] = []
    if not isinstance(preview, user_service.AccountDeletionPreview):
        return [f"preview_user_deletion must return an AccountDeletionPreview, got {preview!r}"]
    if not all(isinstance(item, user_service.BrokerDeletionItem) for item in preview.brokers_deleted):
        violations.append(f"brokers_deleted must hold BrokerDeletionItem: {preview.brokers_deleted!r}")
    if not all(isinstance(item, user_service.BrokerAccessItem) for item in preview.brokers_left):
        violations.append(f"brokers_left must hold BrokerAccessItem: {preview.brokers_left!r}")
    return violations


def _dataclass_shape(candidate: Any) -> Optional[tuple[bool, frozenset[str]]]:
    """(frozen, field names) of a dataclass type; None for anything else, a missing name included."""
    if not (isinstance(candidate, type) and is_dataclass(candidate)):
        return None
    return bool(candidate.__dataclass_params__.frozen), frozenset(item.name for item in fields(candidate))


# =============================================================================
# 1. THE TYPES
# =============================================================================


def test_the_preview_and_the_result_are_the_dataclasses_of_the_contract() -> None:
    """Contracts 1 and 5: AccountDeletionPreview, BrokerDeletionItem and BrokerAccessItem are frozen dataclasses of ``user_service`` with exactly their fields; AccountDeletionResult is a dataclass of deleted_broker_ids and files_removed."""
    print_section("Contracts 1 and 5: the dataclasses")
    shapes = {name: _dataclass_shape(getattr(user_service, name, None)) for name in (*PREVIEW_TYPES, "AccountDeletionResult")}

    found = {name: shapes[name] for name in PREVIEW_TYPES}
    expected = {name: (True, names) for name, names in PREVIEW_TYPES.items()}
    assert found == expected, f"user_service must define these frozen dataclasses with exactly these fields: expected {expected}, found {found}"
    result = shapes["AccountDeletionResult"]
    assert result is not None and result[1] == RESULT_FIELDS, f"user_service.AccountDeletionResult must be a dataclass of exactly {sorted(RESULT_FIELDS)}: {result}"
    print_success("three frozen dataclasses for the preview, one for the result")


# =============================================================================
# 2. THE EQUIVALENCE WITH delete_user
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_the_preview_names_exactly_the_brokers_delete_user_then_deletes(engine: AsyncEngine, scenario: _Scenario) -> None:
    """Contracts 1, 2 and 4: the preview of ``u`` lists, by id, the brokers the rule deletes (with their transactions) and those it leaves (with u's role), and writes nothing; then ``delete_user(u)`` deletes exactly the brokers listed as deleted, and every broker listed as left is still there without u's access — nothing else moved.

    The expectation is written per scenario, not derived from the rule: the equivalence with delete_user is the proof,
    and a rule that both got wrong the same way would still miss the scenario's own list.
    """
    print_section(f"Contract 2: the preview is what delete_user deletes — {[spec.key for spec in scenario.brokers]}")
    scene = await _seed(engine, scenario.brokers)
    user_id = scene.users[TARGET]

    preview = await _preview(engine, user_id)

    violations = _type_violations(preview)
    assert not violations, f"the preview is not of the contract's types: {violations}"
    assert _plain(preview) == _expected(scene, scenario), f"preview of {scene.usernames[TARGET]}: expected {_expected(scene, scenario)}, got {_plain(preview)} (brokers by key: {scene.brokers})"
    before = await _state(engine)
    deletion = await _delete_user(engine, user_id)
    after = await _state(engine)
    deleted_ids = [item.broker_id for item in preview.brokers_deleted]
    left_ids = {item.broker_id for item in preview.brokers_left}
    assert deletion is not None and deletion.deleted_broker_ids == deleted_ids, f"the preview named {deleted_ids} as deleted; delete_user, run afterwards on the same data, deleted {deletion}"
    assert left_ids <= after.brokers, f"brokers listed as left are gone: {sorted(left_ids - after.brokers)}"
    assert not {grant for grant in after.grants if grant[1] == user_id}, f"the account kept access rows: {sorted(grant for grant in after.grants if grant[1] == user_id)}"
    assert after == _after_deletion(before, user_id, set(deleted_ids)), f"delete_user moved something the preview did not announce: expected {_after_deletion(before, user_id, set(deleted_ids))}, found {after}"
    print_success(f"deleted {deleted_ids}, left {sorted(left_ids)}: as previewed")


# =============================================================================
# 3. THE TRANSFERS LEFT UNPAIRED
# =============================================================================


@pytest.mark.asyncio
async def test_transfers_unpaired_counts_the_halves_the_deletion_leaves_alone(engine: AsyncEngine) -> None:
    """Contract 3: D1 and D2 go, S1, S2 and S3 stay (S2 is not even u's). Linked to a leg that goes: S1's half of a pair, S2's leg a deleted one points at, S3's leg that points at a deleted one — three, each once. Not counted: a pair inside D1, a pair between D1 and D2, a pair between S1 and S2.

    D1 holds five legs, D2 two. After the preview, ``delete_user`` deletes D1 and D2 as listed, and leaves alone exactly
    the three halves counted: the count is about what the deletion really does.
    """
    print_section("Contract 3: transfers_unpaired")
    scene = await _seed(engine, TRANSFER_BROKERS)
    legs = await _seed_legs(engine, scene)
    user_id = scene.users[TARGET]
    b, n = scene.brokers, scene.names

    preview = await _preview(engine, user_id)
    before = await _state(engine)
    deletion = await _delete_user(engine, user_id)
    after = await _state(engine)

    expected = (user_id, scene.usernames[TARGET], sorted([(b["d1"], n["d1"], 5), (b["d2"], n["d2"], 2)]), sorted([(b["s1"], n["s1"], EDITOR), (b["s3"], n["s3"], OWNER)]), len(UNPAIRED))
    assert _plain(preview) == expected, f"expected {expected}, got {_plain(preview)} (brokers {b}, legs {legs})"
    assert deletion is not None and deletion.deleted_broker_ids == sorted([b["d1"], b["d2"]]), f"delete_user deleted {deletion}, the preview named D1 {b['d1']} and D2 {b['d2']}"
    assert after == _after_deletion(before, user_id, {b["d1"], b["d2"]}), f"delete_user moved something else: {after}"
    alone = _left_alone(legs, frozenset(tx_id for tx_id, _, _ in after.transactions))
    assert alone == UNPAIRED, f"the scene must leave alone exactly {sorted(UNPAIRED)}, it leaves {sorted(alone)}: the count above would be about something else"
    print_success(f"{len(UNPAIRED)} halves left alone, counted once each; inner and D1–D2 pairs not counted")


# =============================================================================
# 4. AN UNKNOWN USER
# =============================================================================


@pytest.mark.asyncio
async def test_an_unknown_user_has_no_preview(engine: AsyncEngine) -> None:
    """Contract 1: ``None`` for an id no account holds — after a presence barrier: an account of the same database gets a preview — and the database untouched both times."""
    print_section("Contract 1: an unknown user")
    scene = await _seed(engine, (SOLE,))

    known = await _preview(engine, scene.users[TARGET])
    unknown = await _preview(engine, NEVER_ISSUED_ID)

    assert isinstance(known, user_service.AccountDeletionPreview), f"Presence barrier: an existing account must get a preview, or the None below proves nothing: {known!r}"
    assert unknown is None, f"an unknown user must have no preview: {unknown!r}"
    print_success("None for an unknown id")


# =============================================================================
# 5. delete_account
# =============================================================================


@pytest.mark.asyncio
async def test_delete_account_removes_the_reports_of_the_deleted_brokers_once_after_the_commit_off_the_loop(engine: AsyncEngine, database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 5: on the mixed scene, ``delete_account`` returns AccountDeletionResult(deleted_broker_ids=[sole, team, empty_sole] by id, files_removed=what the files function answered); that function ran once, for exactly those brokers, on a thread that is not the event loop's, and when another connection already saw the account and those brokers gone."""
    print_section("Contract 5: delete_account and the report files")
    scene = await _seed(engine, MIXED)
    user_id = scene.users[TARGET]
    deleted = sorted(scene.brokers[key] for key in MIXED_DELETED)
    calls: list[_FilesCall] = []
    _replace_report_cleanup(monkeypatch, _files_spy(database, user_id, calls))

    result = await _delete_account(engine, user_id)
    state = await _state(engine)

    assert isinstance(result, user_service.AccountDeletionResult), f"delete_account must return an AccountDeletionResult, got {result!r}"
    assert (result.deleted_broker_ids, result.files_removed) == (deleted, FILES_REMOVED), f"expected deleted_broker_ids {deleted} and files_removed {FILES_REMOVED} (the files function's count), got {result}"
    expected_call = _FilesCall(tuple(deleted), on_the_loop=False, account_rows=0, deleted_brokers_still_there=())
    assert calls == [expected_call], f"the report files must be removed once, for exactly the deleted brokers, off the event loop, after the commit (another connection sees the account and the brokers gone): expected [{expected_call}], got {calls}"
    assert user_id not in state.users and not state.brokers & set(deleted), f"the account and its deleted brokers must be gone: {state}"
    print_success(f"brokers {deleted} deleted, their reports removed once after the commit, off the loop")


@pytest.mark.asyncio
@pytest.mark.parametrize("brokers", NOTHING_DELETED)
async def test_delete_account_touches_no_report_when_no_broker_is_deleted(engine: AsyncEngine, database: Path, monkeypatch: pytest.MonkeyPatch, brokers: tuple[_BrokerSpec, ...]) -> None:
    """Contract 5: an account that is the last OWNER of no broker is deleted, ``AccountDeletionResult(deleted_broker_ids=[], files_removed=0)``, and the files function is never called."""
    print_section(f"Contract 5: delete_account with no broker to delete — {[spec.key for spec in brokers]}")
    scene = await _seed(engine, brokers)
    user_id = scene.users[TARGET]
    calls: list[_FilesCall] = []
    _replace_report_cleanup(monkeypatch, _files_spy(database, user_id, calls))

    result = await _delete_account(engine, user_id)
    state = await _state(engine)

    assert isinstance(result, user_service.AccountDeletionResult), f"delete_account must return an AccountDeletionResult, got {result!r}"
    assert (result.deleted_broker_ids, result.files_removed) == ([], 0), f"no broker deleted, no file removed: {result}"
    assert calls == [], f"with no broker deleted the files function must not be called: {calls}"
    assert user_id not in state.users and set(scene.brokers.values()) <= state.brokers, f"the account must be gone and every broker still there: {state}"
    print_success("account deleted, no broker, files function not called")


@pytest.mark.asyncio
async def test_a_failed_deletion_propagates_deletes_nothing_and_touches_no_report(engine: AsyncEngine, database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 5: ``BrokerService.delete_bulk`` raises when the deletion reaches ``sole`` — ``shared``, of a lower id, is already left inside the transaction. The failure propagates out of ``delete_account`` (itself, or in the cause chain), the database is exactly as before, and the files function is never called."""
    print_section("Contract 5: a failed deletion")
    scene = await _seed(engine, (SHARED, SOLE, TEAM))
    user_id = scene.users[TARGET]
    calls: list[_FilesCall] = []
    _replace_report_cleanup(monkeypatch, _files_spy(database, user_id, calls))
    before = await _state(engine)

    with monkeypatch.context() as patch:
        patch.setattr(BrokerService, "delete_bulk", _failing_delete_bulk)
        result, failure = await _outcome(_delete_account(engine, user_id))
    after = await _state(engine)

    assert _caused_by(failure, _InjectedFailure), f"the failure must surface from delete_account: it returned {result!r} and raised {failure!r}"
    assert after == before, f"a failed deletion must change nothing: before {before}, after {after}"
    assert calls == [], f"a failed deletion must touch no file: {calls}"
    print_success("the failure propagated, nothing deleted, no file touched")


# =============================================================================
# 6. THE HOOK OF LOT A7
# =============================================================================


def test_account_protection_is_a_plain_function_that_protects_nobody_today() -> None:
    """Contract 6: ``account_protection(user)`` is a plain function — the routes call it as such, and their tests replace it as such — and answers ``None`` for an active or inactive administrator and an active or inactive account."""
    print_section("Contract 6: account_protection")
    accounts = {
        "an active administrator": User(id=1, username="root", email="root@example.com", hashed_password=SEEDED_HASH, is_active=True, is_superuser=True),
        "an inactive administrator": User(id=2, username="dormant_admin", email="dormant_admin@example.com", hashed_password=SEEDED_HASH, is_active=False, is_superuser=True),
        "an active account": User(id=3, username="member", email="member@example.com", hashed_password=SEEDED_HASH, is_active=True, is_superuser=False),
        "an inactive account": User(id=4, username="dormant", email="dormant@example.com", hashed_password=SEEDED_HASH, is_active=False, is_superuser=False),
    }
    hook = getattr(user_service, "account_protection", None)

    assert callable(hook) and not inspect.iscoroutinefunction(hook), f"user_service.account_protection must be a plain function: {hook!r}"
    reasons = {label: hook(user) for label, user in accounts.items()}
    assert reasons == dict.fromkeys(accounts), f"today no account is protected: {reasons}"
    print_success("None for every account")
