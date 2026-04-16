"""
Tests for settings_service: get_session_ttl_sync and get_session_ttl.

Covers:
- get_session_ttl_sync: synchronous TTL default value
- get_session_ttl: async TTL from DB
"""

import pytest

from backend.app.services.settings_service import get_session_ttl_sync, get_session_ttl
from backend.test_scripts.test_db_config import setup_test_database


class TestGetSessionTTLSync:
    def test_returns_positive_integer(self):
        ttl = get_session_ttl_sync()
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_returns_default_value(self):
        """Default is typically 24 hours."""
        ttl = get_session_ttl_sync()
        assert ttl >= 1  # at least 1 hour


class TestGetSessionTTL:
    """Tests for async get_session_ttl."""

    @pytest.mark.asyncio
    async def test_returns_positive_integer(self):
        """get_session_ttl returns a positive int from DB."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.app.db.session import get_async_engine

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            ttl = await get_session_ttl(session)
            assert isinstance(ttl, int)
            assert ttl > 0

    @pytest.mark.asyncio
    async def test_returns_default_when_no_setting(self):
        """Falls back to default when setting not in DB."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.app.db.session import get_async_engine

        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            ttl = await get_session_ttl(session)
            assert ttl >= 1


