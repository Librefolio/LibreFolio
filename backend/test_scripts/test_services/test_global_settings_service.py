"""
Test: GlobalSettingsService — _convert_value, get_setting_value, typed getters.

Tests the global settings service layer including type conversion,
DB reads with defaults, the two convenience getters, and the registration
mode row read through the registry key (release 1.3: ``registration_mode``,
open / invite / disabled, replaces the ``enable_registration`` switch, and
defaults to ``invite`` since lot A6d, decision 36; the effective mode, with
its environment override, is registration_service's).
"""

import asyncio
import sys

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import GlobalSetting
from backend.app.db.session import get_async_engine
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts.global_settings_service import (
    _convert_value,
    get_max_upload_mb,
    get_session_ttl_hours,
    get_setting_value,
)
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# FIXTURE — clean settings table before each test
# ============================================================================


@pytest.fixture()
def _clean_settings():
    """Ensure GlobalSetting table is empty before each test."""

    async def _purge():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            from sqlmodel import delete  # noqa: PLC0415 — test setup — imports after sys.path/db config

            await session.execute(delete(GlobalSetting))
            await session.commit()

    asyncio.run(_purge())
    yield


# ============================================================================
# _convert_value — pure function tests (no DB)
# ============================================================================


class TestConvertValue:
    """Tests for _convert_value() type conversion helper."""

    def test_convert_int_valid(self):
        print_section("_convert_value: int valid")
        assert _convert_value("42", "int") == 42
        assert _convert_value("0", "int") == 0
        assert _convert_value("-5", "int") == -5
        print_success("Integer conversion OK")

    def test_convert_int_invalid(self):
        print_section("_convert_value: int invalid → fallback 0")
        assert _convert_value("abc", "int") == 0
        assert _convert_value("", "int") == 0
        print_success("Invalid int falls back to 0")

    def test_convert_int_none(self):
        print_section("_convert_value: int None → fallback 0")
        assert _convert_value(None, "int") == 0
        print_success("None int falls back to 0")

    def test_convert_bool_truthy(self):
        print_section("_convert_value: bool truthy values")
        for val in ("true", "True", "TRUE", "1", "yes", "on"):
            assert _convert_value(val, "bool") is True, f"Expected True for '{val}'"
        print_success("All truthy values → True")

    def test_convert_bool_falsy(self):
        print_section("_convert_value: bool falsy values")
        for val in ("false", "0", "no", "off", "anything", ""):
            assert _convert_value(val, "bool") is False, f"Expected False for '{val}'"
        print_success("All falsy values → False")

    def test_convert_json_valid(self):
        print_section("_convert_value: json valid")
        result = _convert_value('{"key": "value", "num": 42}', "json")
        assert result == {"key": "value", "num": 42}
        print_success("JSON parsed correctly")

    def test_convert_json_invalid(self):
        print_section("_convert_value: json invalid → fallback {}")
        assert _convert_value("not json", "json") == {}
        print_success("Invalid JSON falls back to {}")

    def test_convert_json_none(self):
        print_section("_convert_value: json None → fallback {}")
        assert _convert_value(None, "json") == {}
        print_success("None JSON falls back to {}")

    def test_convert_string(self):
        print_section("_convert_value: string/unknown type")
        assert _convert_value("hello", "string") == "hello"
        assert _convert_value("hello", "str") == "hello"
        assert _convert_value("raw", "unknown_type") == "raw"
        print_success("String type returns raw value")


# ============================================================================
# get_setting_value — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestGetSettingValue:
    """Tests for get_setting_value() with DB interaction."""

    async def test_setting_from_db(self, _clean_settings):
        print_section("get_setting_value: key present in DB")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            # Insert a setting
            setting = GlobalSetting(
                key="test_key",
                value="99",
                value_type="int",
                description="Test setting",
                updated_at=utcnow(),
            )
            session.add(setting)
            await session.commit()

            # Read it back
            result = await get_setting_value(session, "test_key")
            assert result == 99
            print_success("DB setting read and converted correctly")

    async def test_setting_default_param(self, _clean_settings):
        print_section("get_setting_value: key absent, no global default → use param default")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            result = await get_setting_value(session, "nonexistent_key_xyz", default="fallback")
            assert result == "fallback"
            print_success("Param default returned for missing key")

    async def test_setting_global_default(self, _clean_settings):
        print_section("get_setting_value: key absent but in GLOBAL_SETTINGS_DEFAULTS")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            # "session_ttl_hours" is in GLOBAL_SETTINGS_DEFAULTS with value "24", type "int"
            result = await get_setting_value(session, "session_ttl_hours")
            assert result == 24
            print_success("Global default returned and converted")

    async def test_setting_none_default(self, _clean_settings):
        print_section("get_setting_value: key absent, no default → None")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            result = await get_setting_value(session, "totally_unknown_key")
            assert result is None
            print_success("None returned for unknown key with no default")


# ============================================================================
# Typed getters
# ============================================================================


@pytest.mark.asyncio
class TestTypedGetters:
    """Tests for get_session_ttl_hours, get_max_upload_mb, and the registration_mode row through its registry key."""

    async def test_session_ttl_default(self, _clean_settings):
        print_section("get_session_ttl_hours: default (no DB row)")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            result = await get_session_ttl_hours(session)
            assert result == 24
            print_success(f"Default TTL = {result}")

    async def test_session_ttl_custom(self, _clean_settings):
        print_section("get_session_ttl_hours: custom value in DB")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            session.add(GlobalSetting(key="session_ttl_hours", value="48", value_type="int", updated_at=utcnow()))
            await session.commit()
            result = await get_session_ttl_hours(session)
            assert result == 48
            print_success(f"Custom TTL = {result}")

    async def test_max_upload_default(self, _clean_settings):
        print_section("get_max_upload_mb: default (no DB row)")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            result = await get_max_upload_mb(session)
            assert result == 10
            print_success(f"Default upload MB = {result}")

    async def test_max_upload_custom(self, _clean_settings):
        print_section("get_max_upload_mb: custom value in DB")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            session.add(GlobalSetting(key="max_file_upload_mb", value="50", value_type="int", updated_at=utcnow()))
            await session.commit()
            result = await get_max_upload_mb(session)
            assert result == 50
            print_success(f"Custom upload MB = {result}")

    async def test_registration_mode_default(self, _clean_settings):
        print_section("registration_mode: default (no DB row) is invite")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            result = await get_setting_value(session, SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key)
            assert result == "invite", f"Without a row registration is by invitation: new installs register by invitation since lot A6d (decision 36), the first account being always creatable; got {result!r}"
            print_success(f"Default registration mode = {result}")

    async def test_registration_mode_disabled(self, _clean_settings):
        print_section("registration_mode: disabled in DB")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            session.add(GlobalSetting(key=SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key, value="disabled", value_type="string", updated_at=utcnow()))
            await session.commit()
            result = await get_setting_value(session, SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key)
            assert result == "disabled", f"The stored mode must read back as written: got {result!r}"
            print_success(f"Registration mode = {result}")
