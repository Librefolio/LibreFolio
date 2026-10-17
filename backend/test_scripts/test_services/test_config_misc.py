"""
Small coverage tests for config helpers, and for the Settings field LIBREFOLIO_PROFILE (the profile GET /system/instance
answers).
"""

import pytest
from pydantic import ValidationError

from backend.app import config


def test_get_data_dir_ignores_prod_override_in_test_mode(monkeypatch):
    """Test mode ignores custom prod override when no test override is set."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", "backend/data/custom-prod")
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)

    assert config.get_data_dir() == config.DEFAULT_TEST_DATA_DIR


def test_get_data_dir_prefers_test_override_in_test_mode(monkeypatch):
    """Test mode uses the explicit test data directory override."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", "backend/data/custom-prod")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", "backend/data/custom-test")

    assert config.get_data_dir() == config.PROJECT_ROOT / "backend/data/custom-test"


def test_get_data_dir_uses_relative_env_override_outside_test_mode(monkeypatch):
    """Relative override resolves from project root."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "0")
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", "backend/data/custom-prod")
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)

    assert config.get_data_dir() == config.PROJECT_ROOT / "backend/data/custom-prod"


def test_get_data_dir_falls_back_to_default_prod_dir(monkeypatch):
    """Prod default used when no override configured."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_DATA_DIR", raising=False)
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)

    assert config.get_data_dir() == config.DEFAULT_PROD_DATA_DIR


def test_instance_profile_defaults_to_selfhosted(monkeypatch):
    """LIBREFOLIO_PROFILE unset, and no .env read: selfhosted, an install run by its owner."""
    monkeypatch.delenv("LIBREFOLIO_PROFILE", raising=False)

    assert config.Settings(_env_file=None).LIBREFOLIO_PROFILE == "selfhosted"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("selfhosted", "selfhosted", id="selfhosted"),
        pytest.param("managed", "managed", id="managed"),
        pytest.param(" MANAGED ", "managed", id="stripped-and-lowercased"),
        pytest.param("SelfHosted", "selfhosted", id="any-case"),
    ],
)
def test_instance_profile_is_read_stripped_and_lowercased(monkeypatch, value, expected):
    """LIBREFOLIO_PROFILE: selfhosted or managed, spaces and case aside, as SESSION_COOKIE_SECURE is read."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", value)

    assert config.get_settings().LIBREFOLIO_PROFILE == expected


@pytest.mark.parametrize("value", [pytest.param("cloud", id="cloud"), pytest.param("self-hosted", id="self-hosted"), pytest.param("", id="empty")])
def test_an_unknown_instance_profile_stops_the_settings(monkeypatch, value):
    """Any other value makes get_settings() raise, so the server does not start on a profile it does not know."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", value)

    with pytest.raises(ValidationError) as raised:
        config.get_settings()

    assert ("LIBREFOLIO_PROFILE",) in [error["loc"] for error in raised.value.errors()], f"the error must be about LIBREFOLIO_PROFILE: {raised.value}"
