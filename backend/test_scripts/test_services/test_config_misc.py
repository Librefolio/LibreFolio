"""
Small coverage tests for config helpers.
"""

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
