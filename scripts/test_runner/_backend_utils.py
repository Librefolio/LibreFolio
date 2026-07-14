"""
Backend utility tests: decimal precision, datetime, day count, geo, version, etc.
"""

from . import _common
from ._common import (
    _build_pytest_cmd,
    _get_category_tests_for_all,
    _run_test_suite,
    add_test,
    make_category,
    print_info,
    print_section,
    run_command,
)


def utils_decimal_precision(verbose: bool = False, test_names: list = None) -> bool:
    """Test decimal precision utilities."""
    print_section("Utils: Decimal Precision")
    print_info("Testing: backend/app/utils/decimal_utils.py")
    print_info("Tests: Model precision extraction, Truncation, Edge cases")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_decimal_utils.py", test_names)
    return run_command(cmd, "Decimal precision tests", verbose=verbose)


def utils_datetime(verbose: bool = False, test_names: list = None) -> bool:
    """Test datetime utilities."""
    print_section("Utils: Datetime")
    print_info("Testing: backend/app/utils/datetime_utils.py")
    print_info("Tests: Timezone-aware datetime helpers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_datetime_utils.py", test_names)
    return run_command(cmd, "Datetime utils tests", verbose=verbose)


def utils_day_count(verbose: bool = False, test_names: list = None) -> bool:
    """Test day count conventions."""
    print_section("Utils: Day Count Conventions")
    print_info("Testing: backend/app/services/asset_source_providers/scheduled_investment.py (day count functions)")
    print_info("Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_day_count_conventions.py", test_names)
    return run_command(cmd, "Day count convention tests", verbose=verbose)


def utils_geo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test geographic area normalization utilities."""
    print_section("Utils: Geographic Area Normalization")
    print_info("Testing: backend/app/utils/geo_utils.py")
    print_info("Tests: ISO-3166-A3 normalization, weight parsing, validation pipeline")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_geo_utils.py", test_names)
    return run_command(cmd, "Geographic area normalization tests", verbose=verbose)


def utils_version(verbose: bool = False, test_names: list = None) -> bool:
    """Test version utilities."""
    print_section("Utils: Version")
    print_info("Testing: backend/app/utils/version.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_version.py", test_names)
    return run_command(cmd, "Version utility tests", verbose=verbose)


def utils_sector_normalization(verbose: bool = False, test_names: list = None) -> bool:
    """Test FinancialSector enum and sector normalization."""
    print_section("Utils: Sector Normalization")
    print_info("Testing: backend/app/utils/sector_fin_utils.py")
    print_info("Tests: FinancialSector enum, aliases, normalization, validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_sector_normalization.py", test_names)
    return run_command(cmd, "Sector normalization tests", verbose=verbose)


def utils_currency_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test currency listing, flag mapping, and validation."""
    print_section("Utils: Currency Utils")
    print_info("Testing: backend/app/utils/currency_utils.py")
    print_info("Tests: list_currencies (pycountry), flag_emoji mapping, crypto, validation consistency")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_currency_utils.py", test_names)
    return run_command(cmd, "Currency utils tests", verbose=verbose)


def utils_cache_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test NamedCache wrapper, TTL expiration, and global cache registry."""
    print_section("Utils: Cache Utils")
    print_info("Testing: backend/app/utils/cache_utils.py")
    print_info("Tests: NamedCache set/get/delete/clear, TTL, registry, stats")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_cache_utils.py", test_names)
    return run_command(cmd, "Cache utils tests", verbose=verbose)


def utils_provider_core_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider core cache & thread isolation infrastructure."""
    print_section("Utils: Provider Core Cache & Thread Isolation")
    print_info("Testing: backend/app/services/asset_source.py (core cache + _run_provider_in_thread)")
    print_info("Tests: Thread isolation, timeout, caches (history/current/metadata/search), probe bypass")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_provider_core_cache.py", test_names)
    return run_command(cmd, "Provider core cache tests", verbose=verbose)


def utils_all(verbose: bool = False) -> bool:
    """Run all utility tests."""
    return _run_test_suite(
        suite_name="Utility Tests",
        tests=_get_category_tests_for_all("utils", verbose),
        verbose=verbose,
        info_msgs=["Testing utility modules and helper functions"],
            resume=_common._RESUME_MODE,
        )


def populate_registry(registry: dict) -> None:
    """Register all utility test entries."""
    cat = make_category(
        help_text="Utility module tests (decimal, datetime, geo, currency, cache)",
        description="""
Utility Module Tests

Tests for utility modules and helper functions:
  • Decimal precision, Datetime, Day count conventions
  • Geographic area normalization, Sector normalization
  • Currency utilities, Cache utilities
  • Provider core cache & thread isolation
""")
    add_test(cat, "decimal-precision", utils_decimal_precision, name="Decimal Precision", desc="Model precision, truncation, edge cases")
    add_test(cat, "datetime", utils_datetime, name="Datetime Utils", desc="Timezone-aware datetime helpers")
    add_test(cat, "day-count", utils_day_count, name="Day Count Conventions", desc="ACT/365, ACT/360, ACT/ACT, 30/360")
    add_test(cat, "geo-utils", utils_geo_utils, name="Geographic Utils", desc="ISO-3166-A3 normalization, weights")
    add_test(cat, "version", utils_version, name="Version Utils", desc="get_git_version, get_version_info")
    add_test(cat, "sector-normalization", utils_sector_normalization, name="Sector Normalization", desc="FinancialSector enum, aliases")
    add_test(cat, "currency-utils", utils_currency_utils, name="Currency Utils", desc="Currency listing, flag mapping, crypto")
    add_test(cat, "cache-utils", utils_cache_utils, name="Cache Utils", desc="NamedCache, TTL, registry, stats")
    add_test(cat, "provider-core-cache", utils_provider_core_cache, name="Provider Core Cache", desc="Thread isolation, timeout, caches")
    add_test(cat, "all", utils_all, test_names=False, name="All Utils Tests", desc="Run all utility tests")
    registry["utils"] = cat

