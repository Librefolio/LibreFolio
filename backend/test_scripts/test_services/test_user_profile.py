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
