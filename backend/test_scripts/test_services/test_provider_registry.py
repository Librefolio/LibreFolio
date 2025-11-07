from __future__ import annotations

import asyncio
from typing import Dict

from backend.app.services.provider_registry import AssetProviderRegistry
from backend.test_scripts.test_utils import (
    print_test_header,
    print_section,
    print_info,
    print_success,
    print_error,
    print_test_summary,
    exit_with_result,
)


# ---------------------------------------------------------------------------
# Subtests
# ---------------------------------------------------------------------------

def test_asset_provider_discovery() -> Dict:
    """Test that asset providers are auto-discovered and listed by the registry."""
    print_section("Test 1: Asset Provider Auto-Discovery")

    try:
        providers = AssetProviderRegistry.list_providers()
        # Normalize providers to list of codes if registry returns detailed dicts
        if providers and isinstance(providers[0], dict):
            provider_codes = [p.get("code") or p.get("provider_code") for p in providers]
        else:
            provider_codes = list(providers)

        print_info(f"Registered asset providers: {provider_codes}")

        # Expect at least yfinance to be present in development workspace
        if 'yfinance' not in provider_codes:
            # Log as warning but keep test failing to surface missing auto-discovery
            raise AssertionError(f"Expected 'yfinance' in providers, got: {provider_codes}")

        print_success(f"✓ Asset providers discovery OK ({len(provider_codes)} providers)")
        return {"passed": True, "message": f"Found {len(provider_codes)} asset provider(s)", "providers": provider_codes}

    except Exception as e:
        print_error(f"Asset provider discovery failed: {e}")
        return {"passed": False, "message": str(e)}

# TODO: In migration step 1.4, enhance this test to assert specific FX providers.
def test_fx_provider_discovery() -> Dict:
    """Smoke test for FX provider registry auto-discovery (non-blocking placeholder).

    This test is intentionally permissive to allow incremental migration: it will
    return pass if the registry API is callable and returns a list. Later we will
    assert specific FX providers (ECB, FED, BOE, SNB) once migration is completed.
    """
    print_section("Test 2: FX Provider Auto-Discovery (smoke test)")

    try:
        from backend.app.services.provider_registry import FXProviderRegistry

        providers = FXProviderRegistry.list_providers()
        if providers and isinstance(providers[0], dict):
            provider_codes = [p.get("code") or p.get("provider_code") for p in providers]
        else:
            provider_codes = list(providers)

        print_info(f"Registered FX providers (smoke): {provider_codes}")

        # Do not assert presence yet; migration step 1.4 will add strict checks.
        print_success(f"✓ FX registry reachable ({len(provider_codes)} providers)")
        return {"passed": True, "message": f"Found {len(provider_codes)} FX provider(s)", "providers": provider_codes}

    except Exception as e:
        print_error(f"FX provider discovery smoke test failed: {e}")
        return {"passed": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_all_tests() -> bool:
    """Run provider registry subtests and print a summary similar to asset_source tests."""
    print_test_header("Provider Registry Tests", description="Verify provider auto-discovery for Asset and FX providers.")

    # Run subtests
    results = {}

    res1 = test_asset_provider_discovery()
    results["Asset Provider Discovery"] = bool(res1.get("passed", False))

    res2 = test_fx_provider_discovery()
    results["FX Provider Discovery (smoke)"] = bool(res2.get("passed", False))

    # Print detailed info for each
    def print_result_detail(name: str, data: Dict):
        if not isinstance(data, dict):
            print_info(f"{name}: {data}")
            return
        msg = data.get("message")
        if msg:
            print_info(f"{name}: {msg}")
        extra = {k: v for k, v in data.items() if k not in ("passed", "message")}
        if extra:
            print_info(f"  details: {extra}")

    print_result_detail("Asset Provider Discovery", res1)
    print_result_detail("FX Provider Discovery (smoke)", res2)

    # Summary
    success = print_test_summary(results, "Provider Registry")
    return success


if __name__ == '__main__':
    exit_with_result(run_all_tests())
