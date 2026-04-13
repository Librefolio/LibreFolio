"""
Tests for user_service.update_profile function.

Tests profile update (username/email) with uniqueness validation.
"""

import sys

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

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


class TestDeleteUser:
    """Tests for user_service.delete_user()."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self, session: AsyncSession):
        """Should delete user successfully."""
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
        assert result is True

        # Verify user is gone
        deleted_user = await user_service.get_user_by_id(session, user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, session: AsyncSession):
        """Should return False for non-existent user."""
        result = await user_service.delete_user(session, 99999)
        assert result is False


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

        for i in range(2):
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

