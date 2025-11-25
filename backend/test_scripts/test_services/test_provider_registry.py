"""
Provider Registry Tests

Tests provider auto-discovery for Asset and FX providers.
"""
import pytest

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
    assert 'yfinance' in provider_codes, f"Expected 'yfinance' in providers, got: {provider_codes}"
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
    expected_providers = {'ECB', 'FED', 'BOE', 'SNB'}
    provider_set = set(provider_codes)

    assert expected_providers.issubset(provider_set), \
        f"Missing expected FX providers: {expected_providers - provider_set}. Found: {provider_codes}"
    assert len(provider_codes) >= 4, f"Expected at least 4 providers, got {len(provider_codes)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
