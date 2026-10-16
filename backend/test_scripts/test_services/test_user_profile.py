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
from backend.app.services.accounts import user_service

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
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.transactions.transaction_service import TransactionService


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


# ============================================================================
# AN EMAIL CHANGE RESETS THE VERIFICATION — lot A6e, C6 (release 1.3, workstream A)
# ============================================================================
# These helpers serve TestUpdateProfileEmailVerification only, so they live next to it. Every test runs on the
# private database of isolated_engine. The users are set up and committed in a session of their own, so update_profile
# runs in isolated_session, which has never loaded them, and starts from the committed row, as a request does: a
# session still holding the row as created (email_verified_at NULL) would turn the reset into a no-op UPDATE and fail
# a correct cure. The outcome is read in a fresh session.

#: When the address was verified: any value that is not NULL; what a kept verification keeps is the value read back.
_VERIFIED_AT = datetime(2026, 10, 2, 8, 0, 0)


@dataclass(frozen=True)
class _StoredProfile:
    """A committed users row, as far as a profile change goes, read in a fresh session."""

    username: str
    email: str
    email_verified_at: Optional[datetime]


async def _stored_profile(engine: AsyncEngine, user_id: int) -> _StoredProfile:
    """The committed row of ``user_id``, read in a fresh session (never the identity map of the session under test)."""
    async with AsyncSession(engine) as fresh:
        row = (await fresh.execute(select(User.username, User.email, User.email_verified_at).where(User.id == user_id))).one()
        return _StoredProfile(row.username, row.email, row.email_verified_at)


async def _committed_user(engine: AsyncEngine, role: str, *, verified: bool) -> tuple[_UserRef, _StoredProfile]:
    """A regular user, its address verified when asked, committed in a setup session of its own; and its row as read back."""
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        ref = await _new_user(setup, role, is_superuser=False)
        if verified:
            user = await setup.get(User, ref.id)
            user.email_verified_at = _VERIFIED_AT
            await setup.commit()
    stored = await _stored_profile(engine, ref.id)
    assert (stored.email_verified_at is not None) == verified, f"Setup: {ref.username} must {'' if verified else 'not '}have a verified address: {stored}"
    return ref, stored


class TestUpdateProfileEmailVerification:
    """C6 of lot A6e: an email change sets users.email_verified_at back to NULL, in the commit of the new address (the
    verification was of the old one); a change that is no email change leaves it as it was.

    An email change is the one of C2: ``email`` given and different from the stored one, compared exactly, as
    update_profile compares it. Today update_profile never touches email_verified_at: the two resets are red on their
    last assertion, after a change that is committed; the keeps are guards, green today and after.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("with_username", [False, True], ids=["email-only", "email-and-username"])
    async def test_an_email_change_clears_the_verification(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, with_username: bool):
        """NEW, red today (email_verified_at stays set): the new address is not verified, alone or beside a new username."""
        ref, before = await _committed_user(isolated_engine, "verified", verified=True)
        tag = uuid.uuid4().hex[:8]
        new_email = f"changed_{tag}@example.com"
        new_username = f"renamed_{tag}" if with_username else None

        updated, error = await user_service.update_profile(session=isolated_session, user_id=ref.id, username=new_username, email=new_email)

        assert error is None and updated is not None, f"The change of {ref.username}'s email must succeed: error {error!r}"
        after = await _stored_profile(isolated_engine, ref.id)
        assert (after.username, after.email) == (new_username or before.username, new_email), f"The change must be committed: {before} → {after}"
        assert after.email_verified_at is None, f"An email change must set email_verified_at back to NULL, in the commit of the new address: {before} → {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("change", ["username-only", "same-email", "username-and-same-email"])
    async def test_a_change_that_is_no_email_change_keeps_the_verification(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, change: str):
        """GUARD, green today and after: a new username, the account's own email sent again, or both, change no address,
        so email_verified_at stays as it was; the username changes when one is given."""
        ref, before = await _committed_user(isolated_engine, "verified", verified=True)
        username = None if change == "same-email" else f"renamed_{uuid.uuid4().hex[:8]}"
        email = None if change == "username-only" else before.email

        updated, error = await user_service.update_profile(session=isolated_session, user_id=ref.id, username=username, email=email)

        assert error is None and updated is not None, f"The {change} change must succeed: error {error!r}"
        after = await _stored_profile(isolated_engine, ref.id)
        expected = _StoredProfile(username or before.username, before.email, before.email_verified_at)
        assert after == expected, f"A {change} change must keep the address and its verification: {before} → {after}"

    @pytest.mark.asyncio
    async def test_a_refused_email_change_keeps_the_verification(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """GUARD, green today and after: an address another account already uses is refused, and nothing is written,
        the verification included."""
        ref, before = await _committed_user(isolated_engine, "verified", verified=True)
        _, holder = await _committed_user(isolated_engine, "holder", verified=False)

        updated, error = await user_service.update_profile(session=isolated_session, user_id=ref.id, email=holder.email)

        assert (updated, error) == (None, "Email already registered"), f"{holder.email} is {holder.username}'s: the change must be refused, got {(updated, error)}"
        after = await _stored_profile(isolated_engine, ref.id)
        assert after == before, f"A refused change must write nothing, the verification included: {before} → {after}"


# ============================================================================
# NO ADDRESS IN THE LOGS — lot A7c (release 1.3, workstream A; the rule of workstream E)
# ============================================================================
# These imports and helpers serve TestUpdateProfileLogsNoAddress only, so they live next to it. Every test runs on the
# private database of isolated_engine. Its accounts are rows committed in a setup session of their own before any
# capture, so update_profile runs in isolated_session, which has never loaded them, as in a request; what it committed
# is read back in a fresh session, after the capture. Each address has a local part of its own that no username
# shares: a log may carry the username, never the address, and the check looks for the local part alone too.

import logging
from collections.abc import Iterable
from typing import Any

import structlog
from structlog.testing import capture_logs

#: update_profile's logger: structlog.get_logger(__name__) in user_service.
USER_SERVICE_LOGGER = user_service.__name__
#: The event update_profile logs once a change is committed, word for word.
USER_PROFILE_UPDATED = "User profile updated"
CANARY = "canary: the capture sees the events of the user service's logger"
#: The SQL loggers. Below WARNING they print every statement with its parameters and every row read, so the addresses an
#: UPDATE writes and a SELECT reads too. configure_logging (backend/app/logging_config.py) sets them to WARNING: a running
#: server never writes those records, caplog sees them only because it lowers the root's level. UADM-030
#: (test_users_admin_api.py) pins that premise, read from configure_logging's source.
SQL_LOGGERS = ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool")


@dataclass(frozen=True)
class _AddressedUser:
    """A user the test committed, as plain values: its username and its address carry tags of their own."""

    id: int
    username: str
    email: str


def _address(prefix: str) -> str:
    """An address nobody has, in lower case at example.com, its local part a tag of its own."""
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


async def _committed_addressed_user(engine: AsyncEngine, role: str) -> _AddressedUser:
    """A regular user written as a row, with no service call, and committed in a setup session of its own, before any
    capture. The hash is a marker, never used: nobody signs in."""
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        user = User(username=f"{role}_{uuid.uuid4().hex[:8]}", email=_address("mailbox"), hashed_password="$2b$04$marker.nobody.signs.in")
        setup.add(user)
        await setup.commit()
    return _AddressedUser(user.id, user.username, user.email)


async def _logged_update(session: AsyncSession, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, user_id: int, username: Optional[str], email: Optional[str]) -> tuple[tuple[Optional[User], Optional[str]], list[dict[str, Any]], list[logging.LogRecord]]:
    """update_profile in ``session``, and everything it logged, from the canaries to its return: the structlog events
    (capture_logs) and the stdlib records (caplog at DEBUG, on the root and on the service's logger, enabled even if a
    configuration disabled it).

    Barriers first: a canary through the service's logger name must reach both captures, or a capture that sees nothing
    would pass for a service that logs nothing.
    """
    monkeypatch.setattr(logging.getLogger(USER_SERVICE_LOGGER), "disabled", False)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=USER_SERVICE_LOGGER)
    caplog.clear()
    with capture_logs() as events:
        structlog.get_logger(USER_SERVICE_LOGGER).debug(CANARY)
        logging.getLogger(USER_SERVICE_LOGGER).debug(CANARY)
        outcome = await user_service.update_profile(session=session, user_id=user_id, username=username, email=email)
    records = list(caplog.records)
    assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the user service's logger do not reach capture_logs"
    assert any(record.name == USER_SERVICE_LOGGER and record.getMessage() == CANARY for record in records), "barrier: stdlib records of the user service's logger do not reach caplog at DEBUG"
    return outcome, events, records


def _shows_an_address(text: str, addresses: Iterable[str]) -> bool:
    """Whether ``text`` shows one of ``addresses``, whole or by its local part alone, compared in lower case."""
    lowered = text.lower()
    return any(address.lower() in lowered or address.lower().partition("@")[0] in lowered for address in addresses)


def _record_text(record: logging.LogRecord) -> str:
    """All a stdlib record shows: its message and every attribute."""
    return record.getMessage() + repr(vars(record))


def _written_by_a_server(record: logging.LogRecord) -> bool:
    """Whether a running server writes ``record``: every record but those below WARNING of the SQL loggers and their children."""
    of_sql = any(record.name == name or record.name.startswith(f"{name}.") for name in SQL_LOGGERS)
    return record.levelno >= logging.WARNING or not of_sql


def _assert_no_address(events: list[dict[str, Any]], records: list[logging.LogRecord], addresses: Iterable[str], call: str) -> None:
    """No structlog event, and no stdlib record a server would write, shows one of ``addresses``: in any key, value or
    message, whole or by its local part, in any case."""
    needles = sorted(set(addresses))
    leaked_events = [event for event in events if _shows_an_address(repr(event), needles)]
    leaked_records = [f"{record.name}: {record.getMessage()}" for record in records if _written_by_a_server(record) and _shows_an_address(_record_text(record), needles)]
    assert leaked_events == [], f"{call}: structlog events showing {needles}, whole or by the local part: {leaked_events}"
    assert leaked_records == [], f"{call}: stdlib records showing {needles}, whole or by the local part: {leaked_records}"


def _the_user_profile_updated_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    """The «User profile updated» event of the capture, asserted to be there once."""
    updated = [event for event in events if event.get("event") == USER_PROFILE_UPDATED]
    assert len(updated) == 1, f"update_profile must log «{USER_PROFILE_UPDATED}» once for the change: {updated}"
    return updated[0]


class TestUpdateProfileLogsNoAddress:
    """Lot A7c: update_profile writes no email address in any log — the rule of workstream E, which matters most on
    the hosted cloud. Its «User profile updated» keeps ``user_id`` and ``username``, and ``email`` gives way to
    ``email_changed``: exactly True when the address changed, False otherwise.

    What is checked is everything the call logged, captured at DEBUG by ``_logged_update``: no structlog event and no
    stdlib record shows the old address or the new one, whole or by its local part, in any case — the SQL loggers'
    records below WARNING aside, which no server writes (``SQL_LOGGERS``).

    Today update_profile logs ``email=user.email``: UPROF-001 is red on that keyword alone, in each of its four changes
    (the change itself succeeds and is committed); the refusal of UPROF-002 logs nothing and is a guard.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("with_username", "email_sent", "email_changed"),
        [
            pytest.param(False, "new", True, id="email-only"),
            pytest.param(True, "new", True, id="username-and-email"),
            pytest.param(True, None, False, id="username-only"),
            pytest.param(False, "same", False, id="same-email"),
        ],
    )
    async def test_the_update_logs_email_changed_never_an_address(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, with_username: bool, email_sent: Optional[str], email_changed: bool):
        """UPROF-001 — NEW, red today only because of update_profile's ``email=`` keyword (the route's is PROF-017's and
        PROF-018's): «User profile updated» carries the address, and no ``email_changed``. An email change alone, a
        username and an email together, a username alone, the account's own email sent again: no event and no record
        shows the old address or the new one, and «User profile updated» is there once, without ``email``, with
        ``email_changed`` exactly True for the two email changes and exactly False for the other two, ``user_id`` and
        ``username`` as the change left them."""
        account = await _committed_addressed_user(isolated_engine, "logged")
        username = f"renamed_{uuid.uuid4().hex[:8]}" if with_username else None
        email = {"new": _address("moved"), "same": account.email}.get(email_sent)
        username_after, email_after = username or account.username, email or account.email

        (updated, error), events, records = await _logged_update(isolated_session, caplog, monkeypatch, account.id, username, email)

        assert error is None and updated is not None, f"barrier: the change must succeed: error {error!r}"
        after = await _stored_profile(isolated_engine, account.id)
        assert (after.username, after.email) == (username_after, email_after), f"barrier: the change must be committed: {account} → {after}"
        _assert_no_address(events, records, [account.email, email_after], f"update_profile(username={username!r}, email={email!r})")
        event = _the_user_profile_updated_event(events)
        assert "email" not in event, f"«{USER_PROFILE_UPDATED}» must carry no 'email' key: {event}"
        assert event.get("email_changed") is email_changed, f"«{USER_PROFILE_UPDATED}» must carry email_changed={email_changed}, exactly: {event}"
        assert (event.get("user_id"), event.get("username")) == (account.id, username_after), f"«{USER_PROFILE_UPDATED}» keeps user_id and username, as the change left them: {event}"

    @pytest.mark.asyncio
    async def test_a_refused_email_change_logs_no_address(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """UPROF-002 — GUARD, green today and after: an address another account already uses is refused («Email already
        registered»), and no event and no record shows either address, the account's or the one it asked for; nothing is
        updated, so there is no «User profile updated» either."""
        account = await _committed_addressed_user(isolated_engine, "refused")
        holder = await _committed_addressed_user(isolated_engine, "holder")

        outcome, events, records = await _logged_update(isolated_session, caplog, monkeypatch, account.id, None, holder.email)

        assert outcome == (None, "Email already registered"), f"barrier: {holder.email} is {holder.username}'s, so the change must be refused: {outcome}"
        _assert_no_address(events, records, [account.email, holder.email], "The refused update_profile")
        assert [event for event in events if event.get("event") == USER_PROFILE_UPDATED] == [], f"A refused change updates nothing, so it logs no «{USER_PROFILE_UPDATED}»: {events}"


# ============================================================================
# THE WAITING ADMINISTRATOR'S NEW ADDRESS — lot A7b-2, A-33 (release 1.3, workstream A; N60)
# ============================================================================
# These imports and helpers serve TestUpdateProfileSetupLinks only, so they live next to it. A pending administrator
# never enters the lane's database: there it would be one more administrator account for every unit that shares it.
# Every test runs on the private database of isolated_engine, the administrator made there by the real bootstrap —
# run_admin_bootstrap on the empty instance, with a token of the test in its config, so that the test holds the link —,
# while bootstrap_admin_service.get_async_engine is a tripwire and bcrypt runs at its lowest cost. update_profile reads
# the clock: the scene is dated from it, the administrator created an hour ago, its link live for 71 hours more.
# update_profile runs in isolated_session, which never loaded the account, as a request does; every outcome is read in
# a fresh session.

from datetime import timedelta

from sqlalchemy import text

from backend.app.config.accounts import AdminBootstrapConfig
from backend.app.db.models import AccountTokenPurpose
from backend.app.services.accounts import auth_service, bootstrap_admin_service, registration_service, token_service
from backend.app.services.accounts.auth_service import verify_password
from backend.app.services.accounts.token_service import TokenStatus
from backend.app.utils.datetime_utils import utcnow

#: The waiting administrator's setup link, the token its config gives: the test holds it.
_SETUP_TOKEN = "uprofA7b2-setup-link-0123456789abcdefghijklmn"
#: What the waiting administrator chooses through its link, and what whoever holds an old link tries to set.
_SETUP_PASSWORD = "Setup-Pass-2026!"
_INTRUDER_PASSWORD = "Intruder-Pass-2026!"
#: The address the waiting administrator is created with, unless a test needs another.
_ADMIN_ADDRESS = "admin@example.com"


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("bootstrap_admin_service.get_async_engine() was called: a pending administrator must never reach the lane's database")


@pytest.fixture
def private_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    """For the tests of the waiting administrator: bcrypt at its lowest cost, and the bootstrap module's own road to the lane's database closed."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(bootstrap_admin_service, "get_async_engine", _lane_database_tripwire)


@dataclass(frozen=True)
class _WaitingAdmin:
    """The waiting administrator the bootstrap made, as plain values, and the moment its scene is read at."""

    id: int
    moment: datetime


async def _setup_waits(engine: AsyncEngine, user_id: int) -> bool:
    """Whether the account waits for its F02 setup, as ``registration_service.is_pending_admin`` says, in a fresh session."""
    async with AsyncSession(engine) as fresh:
        user = await fresh.get(User, user_id)
        assert user is not None, f"account {user_id} is not in the database"
        return await registration_service.is_pending_admin(fresh, user)


async def _setup_link(engine: AsyncEngine, token: str, moment: datetime) -> token_service.TokenInspection:
    """What ``inspect_token`` says of the setup link ``token`` at ``moment``, in a fresh session."""
    async with AsyncSession(engine, expire_on_commit=False) as fresh:
        return await token_service.inspect_token(fresh, token, AccountTokenPurpose.ADMIN_SETUP, now=moment)


async def _accounts_and_tokens(engine: AsyncEngine) -> dict[str, list[dict[str, Any]]]:
    """Every row of users and of account_tokens, as a fresh connection reads them: «nothing written», to the letter."""
    async with engine.connect() as connection:
        users = (await connection.execute(text("SELECT * FROM users ORDER BY id"))).mappings().all()
        tokens = (await connection.execute(text("SELECT * FROM account_tokens ORDER BY id"))).mappings().all()
    return {"users": [dict(row) for row in users], "tokens": [dict(row) for row in tokens]}


async def _waiting_admin(engine: AsyncEngine, email: str = _ADMIN_ADDRESS) -> _WaitingAdmin:
    """The F02 administrator ``admin`` at ``email``, created by the real bootstrap on the empty private instance an hour before now, its link _SETUP_TOKEN.

    Barrier: it waits for its setup, and its link is valid now.
    """
    moment = utcnow()
    config = AdminBootstrapConfig(email=email, username="admin", token=_SETUP_TOKEN)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await bootstrap_admin_service.run_admin_bootstrap(session, config, now=moment - timedelta(hours=1))
    assert result.action == bootstrap_admin_service.BootstrapAction.CREATED and result.user_id is not None, f"setup: the empty instance must create its administrator: {result!r}"
    assert await _setup_waits(engine, result.user_id), "barrier: the administrator waits for its setup"
    status = (await _setup_link(engine, _SETUP_TOKEN, moment)).status
    assert status == TokenStatus.VALID, f"barrier: its setup link must be valid: {status}"
    return _WaitingAdmin(result.user_id, moment)


async def _complete_setup(engine: AsyncEngine, token: str, password: str, moment: datetime) -> Optional[User]:
    """``complete_admin_setup`` in a session of its own, committed afterwards: whatever a refusal left pending would stay."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await bootstrap_admin_service.complete_admin_setup(session, token, password, now=moment)
        await session.commit()
    return user


@pytest.mark.usefixtures("private_bootstrap")
class TestUpdateProfileSetupLinks:
    """Lot A7b-2, A-33: the waiting administrator's setup link went to its address. update_profile to another address —
    behind ``./dev.py user set-email`` and ``PUT /auth/profile`` — must revoke, in the commit of the change, the account's
    live setup links: revoked, not retired — the account still waits, and a new link is one ``./dev.py user setup-link``
    away —, so the link delivered to the old address sets nothing. A change that keeps the address (the same one in other
    A–Z capitals, P18; the username alone) or that is refused revokes nothing.

    Today update_profile touches no setup link: UPROF-003 is red on its first contract assertion, after a change that
    succeeds and is committed; UPROF-004 and UPROF-005 are guards, green today and after.
    """

    # red until A7b-2
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("old", "new"),
        [
            pytest.param(_ADMIN_ADDRESS, "admin.elsewhere@example.com", id="another-address"),
            pytest.param("émile@example.com", "Émile@example.com", id="a-letter-outside-a-z-in-capitals"),
        ],
    )
    async def test_a_new_address_revokes_the_waiting_administrators_setup_link(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, old: str, new: str):
        """UPROF-003 — NEW, red until A7b-2 (the link stays valid): update_profile moves the waiting administrator to another address — another mailbox, or the same one with a letter outside A–Z in capitals, which P18 compares as written. The change is committed (the barrier); its commit must revoke the setup link delivered to the old address — ``inspect_token`` says ``revoked`` —, not retire it (``consumed_at`` empty): the account still waits. The old link sets nothing — ``complete_admin_setup`` is ``None``, nothing written —, and ``issue_setup_link`` still gives the account a new link, valid."""
        admin = await _waiting_admin(isolated_engine, old)
        assert not user_service.same_email(new, old), f"setup: {new} must be another address than {old}, under P18"

        updated, error = await user_service.update_profile(isolated_session, admin.id, email=new)

        later = admin.moment + timedelta(minutes=5)
        assert error is None and updated is not None, f"barrier: update_profile must accept {new}: {error!r}"
        assert (await _stored_profile(isolated_engine, admin.id)).email == new, "barrier: the new address is committed"
        link = await _setup_link(isolated_engine, _SETUP_TOKEN, later)
        assert link.status == TokenStatus.REVOKED, f"red until A7b-2: a new address of the waiting administrator must revoke the setup link delivered to the old one: it is {link.status}"
        assert link.record is not None and link.record.consumed_at is None, "revoked, not retired: the account still waits for its setup"
        assert await _setup_waits(isolated_engine, admin.id), "the account still waits for its setup"
        before = await _accounts_and_tokens(isolated_engine)
        assert await _complete_setup(isolated_engine, _SETUP_TOKEN, _INTRUDER_PASSWORD, later) is None, "the link delivered to the old address must set nothing"
        assert await _accounts_and_tokens(isolated_engine) == before, "the old link must change nothing"
        async with AsyncSession(isolated_engine, expire_on_commit=False) as session:
            issued = await bootstrap_admin_service.issue_setup_link(session, now=later)
            await session.commit()
        assert issued is not None and issued.record.user_id == admin.id, f"./dev.py user setup-link must still give the waiting account a new link: {issued!r}"
        assert (await _setup_link(isolated_engine, issued.token, later)).status == TokenStatus.VALID, "the new link must be valid"

    # guard
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            pytest.param({"email": "ADMIN@Example.com"}, ("admin", "ADMIN@Example.com"), id="the-own-address-in-other-capitals"),
            pytest.param({"username": "admin_renamed"}, ("admin_renamed", _ADMIN_ADDRESS), id="the-username-alone"),
        ],
    )
    async def test_a_change_that_keeps_the_address_revokes_no_setup_link(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine, arguments: dict[str, str], expected: tuple[str, str]):
        """UPROF-004 — GUARD, green today and after: the waiting administrator's own address in other A–Z capitals — the same address (P18), its new form stored — or a new username alone: the change is committed, no token moves, the setup link stays valid, and it still completes the setup."""
        admin = await _waiting_admin(isolated_engine)
        tokens_before = (await _accounts_and_tokens(isolated_engine))["tokens"]

        updated, error = await user_service.update_profile(isolated_session, admin.id, **arguments)

        later = admin.moment + timedelta(minutes=5)
        stored = await _stored_profile(isolated_engine, admin.id)
        assert error is None and updated is not None, f"barrier: the change must succeed: {error!r}"
        assert (stored.username, stored.email) == expected, f"barrier: the change is committed: {stored}"
        assert (await _accounts_and_tokens(isolated_engine))["tokens"] == tokens_before, "no setup link may move: the address is the same one"
        assert (await _setup_link(isolated_engine, _SETUP_TOKEN, later)).status == TokenStatus.VALID, "the setup link must stay valid"
        user = await _complete_setup(isolated_engine, _SETUP_TOKEN, _SETUP_PASSWORD, later)
        assert user is not None and user.id == admin.id and user.is_active, f"the link must still complete the setup: {user!r}"
        assert verify_password(_SETUP_PASSWORD, user.hashed_password), "the setup must set the password chosen through the link"

    # guard
    @pytest.mark.asyncio
    async def test_a_refused_new_address_revokes_no_setup_link(self, isolated_session: AsyncSession, isolated_engine: AsyncEngine):
        """UPROF-005 — GUARD, green today and after: an address another account already holds is refused («Email already registered»), and nothing is written, even once the caller commits: every account and every token as they were, the setup link valid."""
        admin = await _waiting_admin(isolated_engine)
        holder = await _committed_addressed_user(isolated_engine, "holder")
        before = await _accounts_and_tokens(isolated_engine)

        outcome = await user_service.update_profile(isolated_session, admin.id, email=holder.email)
        await isolated_session.commit()

        assert outcome == (None, "Email already registered"), f"barrier: {holder.email} is {holder.username}'s, so the change must be refused: {outcome}"
        assert await _accounts_and_tokens(isolated_engine) == before, "a refused change must write nothing"
        assert (await _setup_link(isolated_engine, _SETUP_TOKEN, admin.moment + timedelta(minutes=5))).status == TokenStatus.VALID, "the setup link must stay valid"
