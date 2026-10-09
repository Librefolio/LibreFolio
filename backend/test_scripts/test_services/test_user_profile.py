"""
Tests for user_service.update_profile function.

Tests profile update (username/email) with uniqueness validation.
"""

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model, so SQLModel.metadata holds the whole schema
from backend.app.db.session import get_async_engine
from backend.app.services import user_service

# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """Get async engine."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh session for each test with rollback."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def isolated_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, disposed at teardown.

    Only the users a test creates exist there. That is what the shared lane DB cannot give once the
    answer depends on every other user: its other active admins (e2e_test_admin, ...) are always there.
    NullPool as in get_async_engine, so a fresh session is a fresh connection; the connect listener of
    backend.app.db.session applies its PRAGMAs (foreign_keys, WAL, busy_timeout) here too.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'users.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def isolated_session(isolated_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """The session under test, on the private database: read outcomes in a fresh session, never through this one."""
    async with AsyncSession(isolated_engine, expire_on_commit=False) as session:
        yield session


import uuid


@pytest_asyncio.fixture
async def test_user(session: AsyncSession):
    """Create a test user with unique credentials."""
    unique_id = str(uuid.uuid4())[:8]
    user, error = await user_service.create_user(
        session=session,
        username=f"profiletest_{unique_id}",
        email=f"profiletest_{unique_id}@example.com",
        password="TestPass123!",
        is_active=True,
    )
    if error:
        raise RuntimeError(f"Failed to create test user: {error}")
    yield user
    # Cleanup happens via rollback


# ============================================================================
# SERVICE LAYER TESTS
# ============================================================================


class TestUpdateProfileService:
    """Tests for user_service.update_profile."""

    @pytest.mark.asyncio
    async def test_update_username(self, session: AsyncSession, test_user):
        """Should update username successfully."""
        original_email = test_user.email
        new_username = f"newuser_{uuid.uuid4().hex[:8]}"
        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            username=new_username,
        )

        assert error is None
        assert updated is not None
        assert updated.username == new_username
        assert updated.email == original_email  # unchanged

    @pytest.mark.asyncio
    async def test_update_email(self, session: AsyncSession, test_user):
        """Should update email successfully."""
        original_username = test_user.username
        new_email = f"newemail_{uuid.uuid4().hex[:8]}@example.com"
        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            email=new_email,
        )

        assert error is None
        assert updated is not None
        assert updated.username == original_username  # unchanged
        assert updated.email == new_email

    @pytest.mark.asyncio
    async def test_update_both(self, session: AsyncSession, test_user):
        """Should update both username and email."""
        unique_id = uuid.uuid4().hex[:8]
        new_username = f"bothuser_{unique_id}"
        new_email = f"both_{unique_id}@example.com"
        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            username=new_username,
            email=new_email,
        )

        assert error is None
        assert updated is not None
        assert updated.username == new_username
        assert updated.email == new_email

    @pytest.mark.asyncio
    async def test_no_changes(self, session: AsyncSession, test_user):
        """Should return user unchanged when no updates provided."""
        original_username = test_user.username
        original_email = test_user.email
        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
        )

        assert error is None
        assert updated is not None
        assert updated.username == original_username
        assert updated.email == original_email

    @pytest.mark.asyncio
    async def test_username_taken(self, session: AsyncSession, test_user):
        """Should fail when username is already taken."""
        # Create another user with unique credentials
        unique_id = uuid.uuid4().hex[:8]
        existing_username = f"existing_{unique_id}"
        await user_service.create_user(
            session=session,
            username=existing_username,
            email=f"existing_{unique_id}@example.com",
            password="TestPass123!",
        )

        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            username=existing_username,
        )

        assert error == "Username already taken"
        assert updated is None

    @pytest.mark.asyncio
    async def test_email_taken(self, session: AsyncSession, test_user):
        """Should fail when email is already taken."""
        # Create another user with unique credentials
        unique_id = uuid.uuid4().hex[:8]
        taken_email = f"taken_{unique_id}@example.com"
        await user_service.create_user(
            session=session,
            username=f"another_{unique_id}",
            email=taken_email,
            password="TestPass123!",
        )

        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            email=taken_email,
        )

        assert error == "Email already registered"
        assert updated is None

    @pytest.mark.asyncio
    async def test_same_username_allowed(self, session: AsyncSession, test_user):
        """Should allow setting same username (no actual change)."""
        original_username = test_user.username
        updated, error = await user_service.update_profile(
            session=session,
            user_id=test_user.id,
            username=original_username,  # same as current
        )

        assert error is None
        assert updated is not None
        assert updated.username == original_username

    @pytest.mark.asyncio
    async def test_user_not_found(self, session: AsyncSession):
        """Should fail for non-existent user."""
        updated, error = await user_service.update_profile(
            session=session,
            user_id=99999,
            username="newname",
        )

        assert error == "User not found"
        assert updated is None


class TestCountSuperusers:
    """Tests for user_service.count_superusers()."""

    @pytest.mark.asyncio
    async def test_count_superusers_none(self, session: AsyncSession):
        """Should return 0 when no superusers exist."""
        # Note: Test DB may already have superusers from other tests
        # We just verify the function works without error
        count = await user_service.count_superusers(session)
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_count_superusers_after_create(self, session: AsyncSession):
        """Should count superusers correctly."""
        initial_count = await user_service.count_superusers(session)

        # Create a superuser
        unique_id = uuid.uuid4().hex[:8]
        new_user, error = await user_service.create_user(
            session=session,
            username=f"superuser_{unique_id}",
            email=f"super_{unique_id}@example.com",
            password="SuperPass123!",
            is_superuser=True,
        )
        assert error is None
        assert new_user.is_superuser is True

        new_count = await user_service.count_superusers(session)
        assert new_count == initial_count + 1


# ============================================================================
# DELETE USER — plan 34_accountAndIdReuse §2.1 and D6 (workstream L)
# ============================================================================
# These imports and helpers serve the delete_user tests only, so they live next to them.

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, select

from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.schemas.brokers import BRCreateItem, BRDeleteItem
from backend.app.schemas.common import Currency
from backend.app.services.broker_service import BrokerService
from backend.app.services.transaction_service import TransactionService


class _InjectedFailure(RuntimeError):
    """The technical error a test injects half-way through an account deletion."""


@dataclass
class _Account:
    """The account a delete_user test removes and what surrounds it, recorded once committed.

    Brokers, created in this order so that their ids ascend:
    - sole_1, sole_2: the account is the only OWNER, a DEPOSIT each → deleted (F4);
    - co_owned: the account and its partner both OWNER, a DEPOSIT → stays, the account leaves it;
    - last_owner: the account OWNER, the partner EDITOR, a DEPOSIT → deleted (F4);
    - viewed: the partner OWNER, the account VIEWER → stays. Created last, a surviving broker holds
      the highest id: SQLite without AUTOINCREMENT only reuses the highest id, so no deleted id can
      be handed to a neighbour's new broker while the test still reads it.
    """

    user_id: int = 0
    partner_id: int = 0
    usernames: dict[int, str] = field(default_factory=dict)
    brokers: dict[str, int] = field(default_factory=dict)
    deposits: dict[int, int] = field(default_factory=dict)  # broker id → its DEPOSIT id


@dataclass(frozen=True)
class _AccountState:
    """What the test database holds, read in a fresh session (never the identity map of the session under test)."""

    user_exists: bool
    brokers: frozenset[int]
    grants: frozenset[tuple[int, int, UserRole]]
    deposits: frozenset[int]


async def _create_broker(service: BrokerService, owner_id: int, with_deposit: bool) -> int:
    balances = [Currency(code="EUR", amount=Decimal("100"))] if with_deposit else None
    response = await service.create_bulk([BRCreateItem(name=f"DelUser {uuid.uuid4().hex}", initial_balances=balances)], user_id=owner_id)
    (result,) = response.results
    assert result.success and not response.errors, f"Broker setup failed: {response}"
    return result.broker_id


async def _create_account(engine, account: _Account) -> None:
    """Commit the account, its partner and the five brokers of ``_Account``, recording each only once committed."""
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        created: list[int] = []
        for _ in range(2):
            tag = uuid.uuid4().hex[:8]
            user, error = await user_service.create_user(session=setup, username=f"deluser_{tag}", email=f"deluser_{tag}@example.com", password="DeleteUser123!")
            assert error is None, f"User setup failed: {error}"
            account.usernames[user.id] = user.username  # create_user commits
            created.append(user.id)
        account.user_id, account.partner_id = created

        u, v = account.user_id, account.partner_id
        service = BrokerService(setup)
        brokers = {}
        for name, owner_id, with_deposit in (("sole_1", u, True), ("co_owned", u, True), ("last_owner", u, True), ("sole_2", u, True), ("viewed", v, False)):
            brokers[name] = await _create_broker(service, owner_id, with_deposit)
        setup.add_all(
            [
                BrokerUserAccess(user_id=v, broker_id=brokers["co_owned"], role=UserRole.OWNER, share_percentage=Decimal("0")),
                BrokerUserAccess(user_id=v, broker_id=brokers["last_owner"], role=UserRole.EDITOR, share_percentage=Decimal("0")),
                BrokerUserAccess(user_id=u, broker_id=brokers["viewed"], role=UserRole.VIEWER, share_percentage=Decimal("0")),
            ]
        )
        rows = await setup.execute(select(Transaction.broker_id, Transaction.id).where(Transaction.broker_id.in_(list(brokers.values())), Transaction.type == TransactionType.DEPOSIT))
        deposit_rows = rows.all()
        await setup.commit()
    account.brokers.update(brokers)
    account.deposits.update(dict(deposit_rows))
    expected = sorted(brokers[name] for name in ("sole_1", "co_owned", "last_owner", "sole_2"))
    assert sorted(broker_id for broker_id, _ in deposit_rows) == expected, f"Precondition: one DEPOSIT per broker created with a balance: {deposit_rows}"


def _initial_state(account: _Account) -> _AccountState:
    b, u, v = account.brokers, account.user_id, account.partner_id
    return _AccountState(
        user_exists=True,
        brokers=frozenset(b.values()),
        grants=frozenset(
            {
                (b["sole_1"], u, UserRole.OWNER),
                (b["co_owned"], u, UserRole.OWNER),
                (b["co_owned"], v, UserRole.OWNER),
                (b["last_owner"], u, UserRole.OWNER),
                (b["last_owner"], v, UserRole.EDITOR),
                (b["sole_2"], u, UserRole.OWNER),
                (b["viewed"], v, UserRole.OWNER),
                (b["viewed"], u, UserRole.VIEWER),
            }
        ),
        deposits=frozenset(account.deposits.values()),
    )


async def _read_state(engine, account: _Account) -> _AccountState:
    """Every read is scoped to this test's own rows."""
    broker_ids = list(account.brokers.values())
    async with AsyncSession(engine) as session:
        user = await session.scalar(select(User.id).where(User.id == account.user_id, User.username == account.usernames[account.user_id]))
        brokers = await session.scalars(select(Broker.id).where(Broker.id.in_(broker_ids)))
        grants = await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role).where(BrokerUserAccess.broker_id.in_(broker_ids)))
        deposits = await session.scalars(select(Transaction.id).where(Transaction.id.in_(list(account.deposits.values())), Transaction.broker_id.in_(broker_ids)))
        return _AccountState(user_exists=user is not None, brokers=frozenset(brokers.all()), grants=frozenset(tuple(row) for row in grants.all()), deposits=frozenset(deposits.all()))


async def _remove_account(engine, account: _Account) -> None:
    """Delete what the test created and still exists, also after a red: brokers through the service, then the users."""
    async with AsyncSession(engine) as session:
        surviving = await session.scalars(select(Broker.id).where(Broker.id.in_(list(account.brokers.values()))))
        surviving_ids = sorted(surviving.all())
        if surviving_ids:
            # as_user_id="all": no access check, so brokers left without an owner go too.
            response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker_id, force=True) for broker_id in surviving_ids], user_id=account.partner_id, as_user_id="all")
            assert all(result.success for result in response.results), f"Broker cleanup failed: {response}"
        if account.usernames:
            await session.execute(delete(User).where(User.id.in_(list(account.usernames)), User.username.in_(list(account.usernames.values()))))
        await session.commit()


async def _outcome_of_delete_user(session: AsyncSession, user_id: int) -> tuple[object, Optional[BaseException]]:
    """(returned value, raised exception): which of the two happens is the contract under test."""
    try:
        return await user_service.delete_user(session, user_id), None
    except Exception as exc:  # the assertions decide which exception is acceptable
        return None, exc


def _fail_on_second_call(original, calls: list):
    """Wrap a service method: its first call runs for real, the second raises _InjectedFailure.

    Counting calls instead of naming a broker keeps the test independent of the iteration order:
    whichever broker comes first is really deleted inside the transaction before the failure.
    """

    async def wrapper(self, *args, **kwargs):
        calls.append(args[0] if args else kwargs)
        if len(calls) == 2:
            raise _InjectedFailure(f"injected technical failure on the second call of {original.__qualname__}")
        return await original(self, *args, **kwargs)

    return wrapper


def _caused_by(failure: Optional[BaseException], kind: type[BaseException]) -> bool:
    """True when ``failure`` is ``kind`` or carries it in its cause chain: wrapping is allowed, swallowing is not."""
    seen: set[int] = set()
    while failure is not None and id(failure) not in seen:
        if isinstance(failure, kind):
            return True
        seen.add(id(failure))
        failure = failure.__cause__ or failure.__context__
    return False


class TestDeleteUser:
    """Tests for user_service.delete_user() — plan 34_accountAndIdReuse §2.1 and D6.

    The contract: delete_user applies BrokerService.leave_broker (the single last-owner rule, F4)
    to every broker the user has access to, deletes the user and commits, all in one transaction,
    and returns AccountDeletion(deleted_broker_ids=[...]); None when the user does not exist.
    A technical failure half-way commits nothing (D6): delete_user raises — it never returns after
    a failure — and the account, its brokers and its access rows are all still there.

    Today delete_user deletes the user row only and returns a bool: every test below fails on its
    first contract assertion, after a setup that succeeds.
    """

    @pytest.mark.asyncio
    async def test_delete_user_success(self, session: AsyncSession):
        """NEW contract, red today (returns True): a user without brokers gives an AccountDeletion
        with no deleted broker, and the user is gone."""
        # Create a user to delete
        unique_id = uuid.uuid4().hex[:8]
        user_to_delete, error = await user_service.create_user(
            session=session,
            username=f"todelete_{unique_id}",
            email=f"delete_{unique_id}@example.com",
            password="DeleteMe123!",
        )
        assert error is None
        user_id = user_to_delete.id

        # Delete the user
        result = await user_service.delete_user(session, user_id)
        assert isinstance(result, user_service.AccountDeletion), f"delete_user must return AccountDeletion, got {result!r}"
        assert result.deleted_broker_ids == [], f"A user without brokers deletes none: {result}"

        # Verify user is gone
        deleted_user = await user_service.get_user_by_id(session, user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, session: AsyncSession):
        """GUARD on the not-found path, adapted to the new signature: nothing to delete, nothing
        raised, and None — not an empty AccountDeletion, which would be truthy for the callers that
        test the result (cleanup_owned_user_account). Red today on the value only: the old
        signature answers False."""
        missing_id = 99999
        assert await user_service.get_user_by_id(session, missing_id) is None, f"Precondition: user {missing_id} must not exist"
        result = await user_service.delete_user(session, missing_id)
        assert result is None, f"delete_user must return None for a missing user, got {result!r}"

    @pytest.mark.asyncio
    async def test_delete_user_deletes_the_brokers_it_was_last_owner_of(self, session: AsyncSession, engine):
        """NEW, red today (returns True and leaves sole_1, last_owner and sole_2 without an owner).

        The account is the last OWNER of sole_1 and sole_2 (alone) and of last_owner (beside an
        EDITOR): those three are in deleted_broker_ids and gone with their DEPOSITs. co_owned
        (another OWNER remains) and viewed (the account is a VIEWER) stay with the partner, and
        co_owned keeps its DEPOSIT. The account keeps no access row and no user row.
        """
        account = _Account()
        try:
            await _create_account(engine, account)
            assert await _read_state(engine, account) == _initial_state(account), "Precondition: the account and its five brokers must be committed"

            try:
                result = await user_service.delete_user(session, account.user_id)
            finally:
                await session.rollback()  # a no-op after a commit; releases the write lock if delete_user raised

            assert isinstance(result, user_service.AccountDeletion), f"delete_user must return AccountDeletion, got {result!r}"
            b, v = account.brokers, account.partner_id
            assert sorted(result.deleted_broker_ids) == sorted([b["sole_1"], b["last_owner"], b["sole_2"]]), f"deleted_broker_ids {result.deleted_broker_ids} for brokers {b}"
            expected = _AccountState(
                user_exists=False,
                brokers=frozenset({b["co_owned"], b["viewed"]}),
                grants=frozenset({(b["co_owned"], v, UserRole.OWNER), (b["viewed"], v, UserRole.OWNER)}),
                deposits=frozenset({account.deposits[b["co_owned"]]}),
            )
            assert await _read_state(engine, account) == expected, f"brokers {b}"
        finally:
            await _remove_account(engine, account)

    @pytest.mark.asyncio
    async def test_delete_user_is_all_or_nothing_when_a_broker_deletion_raises(self, session: AsyncSession, engine, monkeypatch):
        """NEW (D6), red today (returns True: delete_bulk is never called, the failure never happens).

        BrokerService.delete_bulk runs for real on its first call and raises on the second: in
        broker_id order, sole_1 is already deleted and co_owned already left inside the transaction
        when last_owner fails. The choice pinned here: the exception propagates out of delete_user —
        itself, or wrapped with it in the cause chain; delete_user never returns after a failure —
        and nothing is committed: account, brokers, access rows and DEPOSITs exactly as before.
        """
        account = _Account()
        calls: list = []
        try:
            await _create_account(engine, account)
            before = await _read_state(engine, account)
            assert before == _initial_state(account), "Precondition: the account and its five brokers must be committed"

            with monkeypatch.context() as patch:
                patch.setattr(BrokerService, "delete_bulk", _fail_on_second_call(BrokerService.delete_bulk, calls))
                result, failure = await _outcome_of_delete_user(session, account.user_id)
            await session.rollback()  # release the write lock whatever delete_user did, before reading and cleaning up

            assert _caused_by(failure, _InjectedFailure), f"The injected failure must surface from delete_user: it returned {result!r} and raised {failure!r} (delete_bulk calls: {calls})"
            assert await _read_state(engine, account) == before, "A technical failure half-way must commit nothing (D6)"
        finally:
            await _remove_account(engine, account)

    @pytest.mark.asyncio
    async def test_delete_user_is_all_or_nothing_when_a_broker_deletion_reports_failure(self, session: AsyncSession, engine, monkeypatch):
        """NEW (D6), red today (returns True). The path a real DB error takes.

        BrokerService.delete_bulk catches every exception into a success=False result, so an error
        while deleting a broker's transactions reaches delete_user as leave_broker(...) returning
        (False, message, False), not as an exception. TransactionService.delete_by_broker runs for
        real on its first call (sole_1) and raises on the second (last_owner). delete_user must
        treat the reported failure as the technical error it is: raise — any exception, it never
        returns — and commit nothing.
        """
        account = _Account()
        calls: list = []
        try:
            await _create_account(engine, account)
            before = await _read_state(engine, account)
            assert before == _initial_state(account), "Precondition: the account and its five brokers must be committed"

            with monkeypatch.context() as patch:
                patch.setattr(TransactionService, "delete_by_broker", _fail_on_second_call(TransactionService.delete_by_broker, calls))
                result, failure = await _outcome_of_delete_user(session, account.user_id)
            await session.rollback()  # release the write lock whatever delete_user did, before reading and cleaning up

            assert failure is not None, f"delete_user returned {result!r} although leaving a broker failed (delete_by_broker calls: {calls})"
            assert len(calls) >= 2, f"delete_user raised {failure!r} before reaching the injected failure (delete_by_broker calls: {calls})"
            assert await _read_state(engine, account) == before, "A technical failure half-way must commit nothing (D6)"
        finally:
            await _remove_account(engine, account)


# ============================================================================
# LIST USERS TESTS (C13b)
# ============================================================================


class TestListUsers:
    """Tests for user_service.list_users()."""

    @pytest.mark.asyncio
    async def test_list_users_returns_list(self, session: AsyncSession):
        """Should return a list."""
        users = await user_service.list_users(session)
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_list_users_includes_created(self, session: AsyncSession):
        """Should include a freshly created user."""
        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"listtest_{unique_id}",
            email=f"listtest_{unique_id}@example.com",
            password="ListPass123!",
        )
        assert error is None

        users = await user_service.list_users(session)
        usernames = [u.username for u in users]
        assert f"listtest_{unique_id}" in usernames

    @pytest.mark.asyncio
    async def test_list_users_multiple(self, session: AsyncSession):
        """Creating 2 users should increase the list by at least 2."""
        initial = await user_service.list_users(session)
        initial_count = len(initial)

        for _i in range(2):
            uid = uuid.uuid4().hex[:8]
            await user_service.create_user(
                session=session,
                username=f"multi_{uid}",
                email=f"multi_{uid}@example.com",
                password="MultiPass123!",
            )

        after = await user_service.list_users(session)
        assert len(after) >= initial_count + 2


# ============================================================================
# RESET PASSWORD TESTS (C13b)
# ============================================================================


class TestResetPassword:
    """Tests for user_service.reset_password()."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self, session: AsyncSession):
        """Should reset password and return success."""
        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"resetpw_{unique_id}",
            email=f"resetpw_{unique_id}@example.com",
            password="OldPass123!",
        )
        assert error is None

        success, err_msg = await user_service.reset_password(
            session=session,
            username=f"resetpw_{unique_id}",
            new_password="NewPass456!",
        )
        assert success is True
        assert err_msg is None

    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_user(self, session: AsyncSession):
        """Should fail for non-existent user."""
        success, err_msg = await user_service.reset_password(
            session=session,
            username="nonexistent_user_xyz",
            new_password="Whatever123!",
        )
        assert success is False
        assert err_msg is not None
        assert "not found" in err_msg


# ============================================================================
# SET USER ACTIVE TESTS (C13b)
# ============================================================================


class TestSetUserActive:
    """Tests for user_service.set_user_active()."""

    @pytest.mark.asyncio
    async def test_deactivate_user(self, session: AsyncSession):
        """Should deactivate a user successfully."""
        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"deact_{unique_id}",
            email=f"deact_{unique_id}@example.com",
            password="DeactPass123!",
            is_active=True,
        )
        assert error is None
        assert user.is_active is True

        success, err_msg = await user_service.set_user_active(
            session=session,
            username=f"deact_{unique_id}",
            active=False,
        )
        assert success is True
        assert err_msg is None

        # Verify user is deactivated
        updated_user = await user_service.get_user_by_username(session, f"deact_{unique_id}")
        assert updated_user.is_active is False

    @pytest.mark.asyncio
    async def test_reactivate_user(self, session: AsyncSession):
        """Should reactivate a deactivated user."""
        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"react_{unique_id}",
            email=f"react_{unique_id}@example.com",
            password="ReactPass123!",
            is_active=False,
        )
        assert error is None

        success, err_msg = await user_service.set_user_active(
            session=session,
            username=f"react_{unique_id}",
            active=True,
        )
        assert success is True

        updated_user = await user_service.get_user_by_username(session, f"react_{unique_id}")
        assert updated_user.is_active is True

    @pytest.mark.asyncio
    async def test_set_active_nonexistent_user(self, session: AsyncSession):
        """Should fail for non-existent user."""
        success, err_msg = await user_service.set_user_active(
            session=session,
            username="nonexistent_user_xyz",
            active=False,
        )
        assert success is False
        assert "not found" in err_msg


class TestSetUserAdmin:
    """Tests for user_service.set_user_admin()."""

    @pytest.mark.asyncio
    async def test_promote_user_to_admin(self, session: AsyncSession):
        """Should promote a regular user to admin."""
        unique_id = uuid.uuid4().hex[:8]
        user, error = await user_service.create_user(
            session=session,
            username=f"promote_{unique_id}",
            email=f"promote_{unique_id}@example.com",
            password="AdminPass123!",
            is_superuser=False,
        )
        assert error is None
        assert user.is_superuser is False

        success, err_msg = await user_service.set_user_admin(
            session=session,
            username=f"promote_{unique_id}",
            is_admin=True,
        )
        assert success is True
        assert err_msg is None

        updated_user = await user_service.get_user_by_username(session, f"promote_{unique_id}")
        assert updated_user.is_superuser is True

    @pytest.mark.asyncio
    async def test_demote_user_from_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """Should demote an admin user while another active admin remains.

        On the private database: on the shared lane DB it passed only because other active admins
        (e2e_test_admin, ...) happen to exist there. It brings its own second active admin instead, so it
        passes today and once demoting the last active administrator is refused (plan 34 step 2).
        """
        unique_id = uuid.uuid4().hex[:8]
        colleague, error = await user_service.create_user(
            session=isolated_session,
            username=f"colleague_{unique_id}",
            email=f"colleague_{unique_id}@example.com",
            password=uuid.uuid4().hex,  # never used: nobody logs in
            is_superuser=True,
        )
        assert error is None
        assert (colleague.is_superuser, colleague.is_active) == (True, True)

        user, error = await user_service.create_user(
            session=isolated_session,
            username=f"demote_{unique_id}",
            email=f"demote_{unique_id}@example.com",
            password="AdminPass123!",
            is_superuser=True,
        )
        assert error is None
        assert user.is_superuser is True

        success, err_msg = await user_service.set_user_admin(
            session=isolated_session,
            username=f"demote_{unique_id}",
            is_admin=False,
        )
        assert success is True
        assert err_msg is None

        async with AsyncSession(isolated_engine) as fresh:  # the committed row, not the identity map of the session under test
            updated_user = await user_service.get_user_by_username(fresh, f"demote_{unique_id}")
            assert updated_user.is_superuser is False


# ============================================================================
# THE LAST ACTIVE ADMINISTRATOR — plan 34_accountAndIdReuse, step 2 (workstream L)
# ============================================================================
# These imports and helpers serve the last-administrator tests only, so they live next to them.
# Every test runs on the private database of isolated_engine: whether an admin is the last one
# depends on every other user, and on the shared lane DB other active admins always exist.

from datetime import datetime


@dataclass(frozen=True)
class _StoredUser:
    """A committed users row, read in a fresh session (never the identity map of the session under test)."""

    username: str
    is_superuser: bool
    is_active: bool
    updated_at: datetime


@dataclass(frozen=True)
class _UserRef:
    """A user the test created, as plain values: nothing to expire if the service under test rolls back its session."""

    id: int
    username: str


async def _stored_users(engine: AsyncEngine) -> dict[int, _StoredUser]:
    """Every user of the private database, by id: the test owns all of them, so the whole table is its own rows."""
    async with AsyncSession(engine) as fresh:
        rows = await fresh.execute(select(User.id, User.username, User.is_superuser, User.is_active, User.updated_at))
        return {row.id: _StoredUser(row.username, row.is_superuser, row.is_active, row.updated_at) for row in rows}


def _flags(users: dict[int, _StoredUser]) -> dict[int, tuple[bool, bool]]:
    """(is_superuser, is_active) by user id."""
    return {user_id: (user.is_superuser, user.is_active) for user_id, user in users.items()}


async def _new_user(session: AsyncSession, role: str, *, is_superuser: bool, is_active: bool = True) -> _UserRef:
    """A user created through the service, inactive from the start when asked.

    create_user(is_active=False), never set_user_active: deactivating the only active admin is refused.
    The uuid tag keeps the username out of any fixed message text; the password is never used, nobody logs in.
    """
    tag = uuid.uuid4().hex[:8]
    user, error = await user_service.create_user(session=session, username=f"{role}_{tag}", email=f"{role}_{tag}@example.com", password=uuid.uuid4().hex, is_superuser=is_superuser, is_active=is_active)
    assert error is None, f"User setup failed: {error}"
    return _UserRef(user.id, user.username)


# The population of the mixed scenarios: (is_superuser, is_active) by role.
_MIXED = {"admin": (True, True), "colleague": (True, True), "dormant": (True, False), "member": (False, True), "idle": (False, False)}


def _mixed_flags(users: dict[str, _UserRef]) -> dict[int, tuple[bool, bool]]:
    """The flags of _MIXED, by the ids of ``users``."""
    return {users[role].id: flags for role, flags in _MIXED.items()}


async def _mixed_users(session: AsyncSession, engine: AsyncEngine) -> dict[str, _UserRef]:
    """Two active admins, an inactive admin, an active and an inactive regular user, and nobody else in the database."""
    users: dict[str, _UserRef] = {}
    for role, (is_superuser, is_active) in _MIXED.items():
        users[role] = await _new_user(session, role, is_superuser=is_superuser, is_active=is_active)
    stored = _flags(await _stored_users(engine))
    assert stored == _mixed_flags(users), f"Precondition: the private database must hold exactly the five users of _MIXED: {stored}"
    return users


async def _assert_refused_as_last_active_admin(outcome: tuple[bool, Optional[str]], session: AsyncSession, engine: AsyncEngine, admin: _UserRef, before: dict[int, _StoredUser]) -> None:
    """What demoting or deactivating ``admin``, the only active admin, must answer: (False, a message naming it), and no change.

    The caller's session is committed before reading back: a refusal must leave nothing pending in it either.
    """
    success, message = outcome
    assert success is False, f"{admin.username} is the only active administrator: the call must be refused, got {outcome}"
    assert message is not None and "last active administrator" in message and admin.username in message, f"The refusal must say 'last active administrator' and name {admin.username}: {message!r}"
    await session.commit()
    after = await _stored_users(engine)
    assert (after[admin.id].is_superuser, after[admin.id].is_active) == (True, True), f"{admin.username} must still be an active admin after the refusal: {after[admin.id]}"
    assert after == before, "A refusal changes nothing in the database"


class TestCountActiveSuperusers:
    """Tests for user_service.count_active_superusers() — plan 34 step 2, on the private database.

    The contract: the users that are both is_superuser and is_active (those who can still log in and
    administer), with ``excluding_user_id`` left out. count_superusers stays as it is.

    Today the function is a stub returning 0: both tests fail on their first count, after a setup that succeeds.
    """

    @pytest.mark.asyncio
    async def test_counts_only_the_active_superusers(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (0 instead of 2): the two active admins count; the inactive admin and the regular users, active or not, do not."""
        await _mixed_users(isolated_session, isolated_engine)

        count = await user_service.count_active_superusers(isolated_session)
        assert count == 2, f"2 active superusers expected among {sorted(_MIXED)}, got {count}"

    @pytest.mark.asyncio
    async def test_excluding_user_id_leaves_that_user_out(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (0 instead of 1): leaving out an active admin counts one less; leaving out the
        inactive admin or a regular user still counts 2, since neither was counted."""
        users = await _mixed_users(isolated_session, isolated_engine)

        for role, expected in (("admin", 1), ("dormant", 2), ("member", 2)):
            count = await user_service.count_active_superusers(isolated_session, excluding_user_id=users[role].id)
            assert count == expected, f"excluding_user_id of {role} ({users[role].id}): {expected} active superuser(s) expected, got {count}"


class TestLastActiveAdministrator:
    """Neither demoting nor deactivating leaves the instance without an active admin — plan 34 step 2.

    The contract, for set_user_admin(..., is_admin=False) and set_user_active(..., active=False): on an
    ACTIVE superuser while no other active superuser exists, the answer is (False, message), the message
    says "last active administrator" and names the user, and nothing changes in the database: the user
    stays an active admin. Another active admin keeps the call allowed, and so does a target that is no
    active admin: a regular user, or an admin already inactive (login refuses inactive users, so it
    administers nothing).

    Today there is no guard: the four refusals are red on their first assertion (the call succeeds and
    is committed); the five permissions are guards, green today and after the cure.
    """

    # ---- demote: set_user_admin(..., is_admin=False) ----

    @pytest.mark.asyncio
    async def test_demoting_the_only_active_admin_is_refused(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (returns (True, None) and demotes): the only admin, beside a regular user, who is no admin."""
        only = await _new_user(isolated_session, "onlyadmin", is_superuser=True)
        member = await _new_user(isolated_session, "member", is_superuser=False)
        before = await _stored_users(isolated_engine)
        assert _flags(before) == {only.id: (True, True), member.id: (False, True)}, f"Precondition: one active admin and one active regular user, nobody else: {before}"

        outcome = await user_service.set_user_admin(session=isolated_session, username=only.username, is_admin=False)

        await _assert_refused_as_last_active_admin(outcome, isolated_session, isolated_engine, only, before)

    @pytest.mark.asyncio
    async def test_demoting_the_only_active_admin_is_refused_beside_an_inactive_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (returns (True, None) and demotes): an inactive admin cannot log in to administer, so it does not count."""
        only = await _new_user(isolated_session, "onlyadmin", is_superuser=True)
        dormant = await _new_user(isolated_session, "dormant", is_superuser=True, is_active=False)
        before = await _stored_users(isolated_engine)
        assert _flags(before) == {only.id: (True, True), dormant.id: (True, False)}, f"Precondition: one active and one inactive admin, nobody else: {before}"

        outcome = await user_service.set_user_admin(session=isolated_session, username=only.username, is_admin=False)

        await _assert_refused_as_last_active_admin(outcome, isolated_session, isolated_engine, only, before)

    @pytest.mark.asyncio
    async def test_demoting_is_allowed_while_another_active_admin_remains(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD, green today and after the cure: the colleague stays an active admin, so the demotion goes
        through, and only the target loses the role, beside an inactive admin and the regular users."""
        users = await _mixed_users(isolated_session, isolated_engine)
        admin = users["admin"]

        outcome = await user_service.set_user_admin(session=isolated_session, username=admin.username, is_admin=False)

        assert outcome == (True, None), f"Demoting {admin.username} must be allowed while another active admin remains"
        after = _flags(await _stored_users(isolated_engine))
        assert after == _mixed_flags(users) | {admin.id: (False, True)}, f"Only {admin.username} loses the role: {after}"

    @pytest.mark.asyncio
    async def test_demoting_an_inactive_admin_is_allowed_with_no_active_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD, green today and after the cure: the only admin is inactive, so demoting it takes no active
        admin away (there is none to protect)."""
        dormant = await _new_user(isolated_session, "dormant", is_superuser=True, is_active=False)
        member = await _new_user(isolated_session, "member", is_superuser=False)
        assert _flags(await _stored_users(isolated_engine)) == {dormant.id: (True, False), member.id: (False, True)}, "Precondition: one inactive admin and one active regular user, nobody else"

        outcome = await user_service.set_user_admin(session=isolated_session, username=dormant.username, is_admin=False)

        assert outcome == (True, None), f"Demoting the inactive {dormant.username} removes no active admin: it must be allowed"
        after = _flags(await _stored_users(isolated_engine))
        assert after == {dormant.id: (False, False), member.id: (False, True)}, f"Only {dormant.username} loses the role: {after}"

    # ---- deactivate: set_user_active(..., active=False) ----

    @pytest.mark.asyncio
    async def test_deactivating_the_only_active_admin_is_refused(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (returns (True, None) and deactivates): the only admin, beside a regular user, stays active."""
        only = await _new_user(isolated_session, "onlyadmin", is_superuser=True)
        member = await _new_user(isolated_session, "member", is_superuser=False)
        before = await _stored_users(isolated_engine)
        assert _flags(before) == {only.id: (True, True), member.id: (False, True)}, f"Precondition: one active admin and one active regular user, nobody else: {before}"

        outcome = await user_service.set_user_active(session=isolated_session, username=only.username, active=False)

        await _assert_refused_as_last_active_admin(outcome, isolated_session, isolated_engine, only, before)

    @pytest.mark.asyncio
    async def test_deactivating_the_only_active_admin_is_refused_beside_an_inactive_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """NEW, red today (returns (True, None) and deactivates): the inactive admin does not count, so the active one stays active."""
        only = await _new_user(isolated_session, "onlyadmin", is_superuser=True)
        dormant = await _new_user(isolated_session, "dormant", is_superuser=True, is_active=False)
        before = await _stored_users(isolated_engine)
        assert _flags(before) == {only.id: (True, True), dormant.id: (True, False)}, f"Precondition: one active and one inactive admin, nobody else: {before}"

        outcome = await user_service.set_user_active(session=isolated_session, username=only.username, active=False)

        await _assert_refused_as_last_active_admin(outcome, isolated_session, isolated_engine, only, before)

    @pytest.mark.asyncio
    async def test_deactivating_an_admin_is_allowed_while_another_active_admin_remains(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD, green today and after the cure: the colleague stays an active admin, so the deactivation goes
        through, and only the target becomes inactive (still an admin), beside an inactive admin and the regular users."""
        users = await _mixed_users(isolated_session, isolated_engine)
        admin = users["admin"]

        outcome = await user_service.set_user_active(session=isolated_session, username=admin.username, active=False)

        assert outcome == (True, None), f"Deactivating {admin.username} must be allowed while another active admin remains"
        after = _flags(await _stored_users(isolated_engine))
        assert after == _mixed_flags(users) | {admin.id: (True, False)}, f"Only {admin.username} becomes inactive: {after}"

    @pytest.mark.asyncio
    async def test_deactivating_a_regular_user_is_allowed_beside_the_only_active_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD, green today and after the cure: a regular user administers nothing, so deactivating one is
        allowed while a single admin is active, and that admin stays active."""
        only = await _new_user(isolated_session, "onlyadmin", is_superuser=True)
        member = await _new_user(isolated_session, "member", is_superuser=False)
        assert _flags(await _stored_users(isolated_engine)) == {only.id: (True, True), member.id: (False, True)}, "Precondition: one active admin and one active regular user, nobody else"

        outcome = await user_service.set_user_active(session=isolated_session, username=member.username, active=False)

        assert outcome == (True, None), f"Deactivating the regular user {member.username} takes no admin away: it must be allowed"
        after = _flags(await _stored_users(isolated_engine))
        assert after == {only.id: (True, True), member.id: (False, False)}, f"Only {member.username} becomes inactive: {after}"

    @pytest.mark.asyncio
    async def test_deactivating_an_already_inactive_admin_still_succeeds_with_no_active_admin(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD on today's behaviour, plain in the code (set_user_active has no "already inactive" check):
        deactivating the only admin, already inactive, answers (True, None) and leaves the flags as they were.
        It takes no active admin away, so the guard must not catch it. updated_at is not pinned."""
        dormant = await _new_user(isolated_session, "dormant", is_superuser=True, is_active=False)
        member = await _new_user(isolated_session, "member", is_superuser=False)
        assert _flags(await _stored_users(isolated_engine)) == {dormant.id: (True, False), member.id: (False, True)}, "Precondition: one inactive admin and one active regular user, nobody else"

        outcome = await user_service.set_user_active(session=isolated_session, username=dormant.username, active=False)

        assert outcome == (True, None), f"Deactivating {dormant.username}, already inactive, takes no active admin away: today's (True, None) must stay"
        after = _flags(await _stored_users(isolated_engine))
        assert after == {dormant.id: (True, False), member.id: (False, True)}, f"The flags stay as they were: {after}"
