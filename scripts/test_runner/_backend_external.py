"""
External service tests: FX providers, asset providers, BRIM providers.
Includes provider discovery for dynamic CLI help.
"""

import inspect
import re
from pathlib import Path

from ._common import (
    _RESUME_MODE,
    PROJECT_ROOT, _run_test_suite, _build_pytest_cmd, run_command,
    print_section, print_info,
    make_category, add_test,
)


# ── Provider discovery for dynamic CLI help & filtering ─────────────────

_PROVIDER_CODE_RE = re.compile(
    r'def\s+provider_code\s*\(self\).*?\n\s+(?:"""[^"]*"""\n\s+)?return\s+["\']([^"\']+)["\']',
    re.MULTILINE,
)

_CODE_RE = re.compile(
    r'def\s+code\s*\(self\).*?\n\s+return\s+["\']([^"\']+)["\']',
    re.MULTILINE,
)

_PROVIDER_FOLDERS = {
    "asset": "asset_source_providers",
    "fx":    "fx_providers",
    "brim":  "brim_providers",
}


def _discover_provider_codes(registry_type: str) -> list[str]:
    """Discover provider codes by scanning source files with regex."""
    folder_name = _PROVIDER_FOLDERS.get(registry_type)
    if not folder_name:
        return []

    target_dir = PROJECT_ROOT / "backend" / "app" / "services" / folder_name
    if not target_dir.exists():
        return []

    codes: list[str] = []
    for py in target_dir.glob("*.py"):
        if py.name == "__init__.py":
            continue
        try:
            text = py.read_text(encoding="utf-8")
            match = _PROVIDER_CODE_RE.search(text)
            if not match:
                match = _CODE_RE.search(text)
            if match:
                codes.append(match.group(1))
        except Exception:
            continue
    return sorted(codes)


# Cache at module level (discovered once per run)
_ASSET_PROVIDER_CODES: list[str] | None = None
_FX_PROVIDER_CODES: list[str] | None = None
_BRIM_PROVIDER_CODES: list[str] | None = None


def get_asset_provider_codes() -> list[str]:
    """Get available asset provider codes (cached)."""
    global _ASSET_PROVIDER_CODES
    if _ASSET_PROVIDER_CODES is None:
        _ASSET_PROVIDER_CODES = _discover_provider_codes("asset")
    return _ASSET_PROVIDER_CODES


def get_fx_provider_codes() -> list[str]:
    """Get available FX provider codes (cached)."""
    global _FX_PROVIDER_CODES
    if _FX_PROVIDER_CODES is None:
        _FX_PROVIDER_CODES = _discover_provider_codes("fx")
    return _FX_PROVIDER_CODES


def get_brim_provider_codes() -> list[str]:
    """Get available BRIM provider codes (cached)."""
    global _BRIM_PROVIDER_CODES
    if _BRIM_PROVIDER_CODES is None:
        _BRIM_PROVIDER_CODES = _discover_provider_codes("brim")
    return _BRIM_PROVIDER_CODES


def _build_provider_filter_expr(providers: list[str] | None, exclude_providers: list[str] | None) -> str | None:
    """Build a pytest -k expression to include/exclude providers."""
    if providers:
        return " or ".join(providers)
    elif exclude_providers:
        return " and ".join(f"not {p}" for p in exclude_providers)
    return None


def _get_external_extra_args() -> list[tuple]:
    """Generate --providers / --exclude-providers argparse arguments."""
    asset_codes = get_asset_provider_codes()
    fx_codes = get_fx_provider_codes()
    brim_codes = get_brim_provider_codes()
    provider_help = (
        "Only test these provider(s). "
        f"Asset: {', '.join(asset_codes) or '(none)'}. "
        f"FX: {', '.join(fx_codes) or '(none)'}. "
        f"BRIM: {', '.join(brim_codes) or '(none)'}. "
        "If omitted, ALL providers are tested."
    )
    exclude_help = (
        "Exclude these provider(s) from testing. "
        f"Asset: {', '.join(asset_codes) or '(none)'}. "
        f"FX: {', '.join(fx_codes) or '(none)'}. "
        f"BRIM: {', '.join(brim_codes) or '(none)'}."
    )
    return [
        (
            "--providers", {
            "nargs": "+",
            "dest": "providers",
            "metavar": "CODE",
            "help": provider_help,
            "default": None,
            }
            ),
        (
            "--exclude-providers", {
            "nargs": "+",
            "dest": "exclude_providers",
            "metavar": "CODE",
            "help": exclude_help,
            "default": None,
            }
            ),
    ]


# ── Test functions ──────────────────────────────────────────────────────

def external_fx_providers(verbose: bool = False, test_names: list = None,
                          providers: list = None, exclude_providers: list = None) -> bool:
    """Run FX providers external tests (network-dependent)."""
    print_section("External: FX Providers Tests (including multi-unit)")
    print_info("Testing: All registered FX providers (ECB, FED, BOE, etc.)")
    print_info("Tests: Metadata, currencies, rate fetching, normalization, multi-unit handling")
    print_info("Note: Multi-unit tests auto-skip for providers without multi-unit support")
    print_info("⚠️  WARNING: Requires internet connection")
    print_info("⚠️  WARNING: May be slow due to API rate limiting")

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_fx_providers.py",
                            effective_names or None)
    return run_command(cmd, "FX providers external tests", verbose=verbose)


def external_asset_providers(verbose: bool = False, test_names: list = None,
                             providers: list = None, exclude_providers: list = None) -> bool:
    """Test all registered asset pricing providers."""
    print_section("External: Asset Providers Tests")
    print_info("Testing: All registered asset pricing providers")
    print_info("Tests: Metadata, current value, historical data, search, error handling")
    print_info("⚠️  WARNING: Requires internet connection")
    print_info("⚠️  WARNING: May be slow due to API rate limiting")

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_asset_providers.py",
                            effective_names or None)
    return run_command(cmd, "Asset providers tests", verbose=verbose)


def external_justetf_multicurrency(verbose: bool = False, test_names: list = None) -> bool:
    """Test JustETF multi-currency support (EUR/USD/CHF/GBP)."""
    print_section("External: JustETF Multi-Currency Tests")
    print_info("Testing: JustETF provider with all 4 supported currencies")
    print_info("Tests: Current price (EUR-only), history (all 4), search (4× results), params validation")
    print_info("⚠️  WARNING: Requires internet connection")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_justetf_multicurrency.py",
                            test_names or None)
    return run_command(cmd, "JustETF multi-currency tests", verbose=verbose)


def external_brim_providers(verbose: bool = False, test_names: list = None,
                            providers: list = None, exclude_providers: list = None) -> bool:
    """Test BRIM providers."""
    print_section("External: BRIM Providers Tests")
    print_info("Testing: Broker Report Import Manager (BRIM) plugins")
    print_info("Tests: Plugin discovery, file parsing, auto-detection, sample coverage")
    print_info("Brokers: Directa, DEGIRO, Trading212, IBKR, eToro, Revolut, Schwab, etc.")

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_providers.py",
                            effective_names or None)
    return run_command(cmd, "BRIM providers tests", verbose=verbose)


def external_all(verbose: bool = False,
                 providers: list = None, exclude_providers: list = None) -> bool:
    """Run all external tests (network-dependent)."""
    from ._registry import TEST_REGISTRY

    tests = []
    for action, info in TEST_REGISTRY.get("external", {}).items():
        if action in ("_meta", "all"):
            continue
        func = info["func"]
        name = info.get("name", action)
        func_params = inspect.signature(func).parameters
        if "providers" in func_params:
            tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers:
                          f(verbose=v, providers=p, exclude_providers=ep)))
        else:
            tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="External Tests",
        tests=tests,
        verbose=verbose,
        info_msgs=[
            "Testing external provider integrations",
            "⚠️  WARNING: Requires internet connection for FX/Asset providers",
            "⚠️  WARNING: May be slow",
            ],
            resume=_RESUME_MODE,
        )


def populate_registry(registry: dict) -> None:
    """Register all external test entries."""
    cat = make_category(
        help_text="External service integration tests (no backend server)",
        description="""
External Services Tests

These tests verify external API integrations:
  • No backend server required
  • Tests network calls to external APIs
  • May be slow or fail if external services are down
""")
    add_test(cat, "fx-providers", external_fx_providers, name="FX Providers",
             desc="Test FX rate providers (ECB, FED, BOE, SNB)", prereq="Internet connection",
             tests="ECB, FED, BOE, SNB API calls")
    add_test(cat, "asset-providers", external_asset_providers, name="Asset Providers",
             desc="Test asset pricing providers", prereq="Internet connection",
             tests="yfinance, cssscraper, etc.")
    add_test(cat, "justetf-multicurrency", external_justetf_multicurrency, name="JustETF Multi-Currency",
             desc="Test JustETF provider with EUR/USD/CHF/GBP currencies", prereq="Internet connection",
             tests="Current price, history, search, params validation")
    add_test(cat, "brim-providers", external_brim_providers, name="BRIM Providers",
             desc="Test broker report import plugins", prereq="Sample files in test fixtures",
             tests="Plugin discovery, file parsing, auto-detection")
    add_test(cat, "all", external_all, test_names=False, name="All External Tests",
             desc="Run all external tests")
    registry["external"] = cat

