"""
Provider Registry Tests

Tests provider auto-discovery for Asset and FX providers.
"""

import pytest

from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.asset_source import AssetSourceProvider
from backend.app.services.fx import FXRateProvider
from backend.app.services.provider_registry import AssetProviderRegistry, FXProviderRegistry


def test_asset_provider_discovery():
    """Test that asset providers are auto-discovered and listed by the registry."""
    providers = AssetProviderRegistry.list_providers()

    # Normalize providers to list of codes if registry returns detailed dicts
    if providers and isinstance(providers[0], dict):
        provider_codes = [p.get("code") or p.get("provider_code") for p in providers]
    else:
        provider_codes = list(providers)

    # Expect at least yfinance to be present in development workspace
    assert "yfinance" in provider_codes, f"Expected 'yfinance' in providers, got: {provider_codes}"
    assert len(provider_codes) > 0, "Should have at least one provider"


def test_fx_provider_discovery():
    """Test that FX providers are auto-discovered and registered correctly.

    After Phase 1.4 migration, we expect all 4 central bank providers to be registered.
    """
    providers = FXProviderRegistry.list_providers()

    # Extract codes from provider dicts
    if providers and isinstance(providers[0], dict):
        provider_codes = [p.get("code") or p.get("provider_code") for p in providers]
    else:
        provider_codes = list(providers)

    # After Phase 1.4 migration, assert all 4 providers are present
    expected_providers = {"ECB", "FED", "BOE", "SNB"}
    provider_set = set(provider_codes)

    assert expected_providers.issubset(provider_set), f"Missing expected FX providers: {expected_providers - provider_set}. Found: {provider_codes}"
    assert len(provider_codes) >= 4, f"Expected at least 4 providers, got {len(provider_codes)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# ============================================================================
# GENERATE STATIC URL TESTS (C13b)
# ============================================================================


def test_fx_generate_static_url():
    """FXRateProvider.generate_static_url returns correct URL path."""
    url = FXRateProvider.generate_static_url("ecb/logo.svg")
    assert url == "/api/v1/uploads/plugin/fx/ecb/logo.svg"


def test_asset_generate_static_url():
    """AssetSourceProvider.generate_static_url returns correct URL path."""
    url = AssetSourceProvider.generate_static_url("yfinance/logo.png")
    assert url == "/api/v1/uploads/plugin/asset/yfinance/logo.png"


def test_fx_static_url_nested_path():
    """generate_static_url handles nested paths correctly."""
    url = FXRateProvider.generate_static_url("snb/icons/small.png")
    assert url == "/api/v1/uploads/plugin/fx/snb/icons/small.png"


# ============================================================================
# MEANINGFUL-VOLUME CAPABILITY AUDIT (workstream B, item 4)
# ============================================================================


def test_meaningful_volume_capability_is_declared_only_where_authoritative():
    """Only providers with an unambiguous traded-volume meaning declare
    supports_meaningful_volume=True; all others default/override to False.
    """
    expected_traded_shares = {"yfinance", "borsa_italiana"}
    expected_false = {"justetf", "css_scraper", "scheduled_investment", "mockprov"}

    for code in expected_traded_shares:
        provider = AssetProviderRegistry.get_provider_instance(code)
        assert provider is not None, f"Expected provider {code!r} to be registered"
        assert provider.supports_meaningful_volume is True, f"{code} should declare meaningful volume support"
        assert provider.volume_kind == FAVolumeKind.TRADED_SHARES, f"{code} should declare TRADED_SHARES volume kind"

    for code in expected_false:
        provider = AssetProviderRegistry.get_provider_instance(code)
        assert provider is not None, f"Expected provider {code!r} to be registered"
        assert provider.supports_meaningful_volume is False, f"{code} should NOT declare meaningful volume support"
        assert provider.volume_kind == FAVolumeKind.UNKNOWN, f"{code} should default to UNKNOWN volume kind"


def test_base_provider_defaults_to_no_meaningful_volume():
    """AssetSourceProvider base class defaults are safe (unknown/false) for
    any provider that doesn't explicitly override the capability."""

    class _MinimalProvider(AssetSourceProvider):
        provider_code = "test_minimal_provider"
        provider_name = "Test Minimal Provider"
        test_cases = []
        test_search_query = None

        def validate_params(self, params):
            return None

        async def get_current_value(self, *args, **kwargs):
            raise NotImplementedError

        async def get_history_value(self, *args, **kwargs):
            raise NotImplementedError

    provider = _MinimalProvider()
    assert provider.supports_meaningful_volume is False
    assert provider.volume_kind == FAVolumeKind.UNKNOWN
