"""
Backend service tests: FX conversion, asset source, provider registry, transactions, etc.
"""


from ._backend_db import db_create
from ._common import (
    _RESUME_MODE,
    _build_pytest_cmd,
    _get_category_tests_for_all,
    _run_test_suite,
    add_test,
    make_category,
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
    print_warning,
    run_command,
)


def services_fx_conversion(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX conversion service logic."""
    print_section("Services: FX Conversion Logic")
    print_info("Testing: backend/app/services/fx.py convert() function")
    print_info("Scenarios: Identity, Direct, Inverse, Roundtrip, Different Dates, Forward-fill")
    print_info("Safety: Verifies test database usage before modifying data")
    print_info("Note: Mock FX rates automatically inserted for 3 dates")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_conversion.py", test_names)
    return run_command(cmd, "FX conversion service tests", verbose=verbose)


def services_asset_metadata(verbose: bool = False, test_names: list = None) -> bool:
    """Test AssetMetadataService static utility behavior."""
    print_section("Services: Asset Metadata Service")
    print_info("Testing: backend/app/services/asset_metadata.py")
    print_info("Tests: parse/serialize, diff, patch semantics")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_metadata.py", test_names)
    return run_command(cmd, "Asset metadata service tests", verbose=verbose)


def services_asset_source(verbose: bool = False, test_names: list = None) -> bool:
    """Test Asset Source service logic."""
    print_section("Services: Asset Source Logic")
    print_info("Testing: backend/app/services/asset_source.py")
    print_info("Tests: Helper functions, Provider assignment, Synthetic yield")
    print_info("Note: Test assets automatically created and cleaned up")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source.py", test_names)
    return run_command(cmd, "Asset source service tests", verbose=verbose)


def services_asset_source_refresh(verbose: bool = False, test_names: list = None) -> bool:
    """Smoke test: Asset Source refresh orchestration."""
    print_section("Services: Asset Source Refresh (smoke)")
    print_info("Testing: backend/app/services/asset_source bulk refresh orchestration (smoke)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source_refresh.py", test_names)
    return run_command(cmd, "Asset source refresh smoke test", verbose=verbose)


def services_provider_registry(verbose: bool = False, test_names: list = None) -> bool:
    """Test registry dei provider (asset & fx)."""
    print_section("Services: Provider Registry")
    print_info("Testing: backend/app/services/provider_registry.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_registry.py", test_names)
    return run_command(cmd, "Provider registry tests", verbose=verbose)


def services_provider_contracts(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider interface contracts (FX, Asset, BRIM)."""
    print_section("Services: Provider Contract Tests")
    print_info("Testing: Interface compliance for ALL registered providers (offline, no HTTP)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_contracts.py", test_names)
    return run_command(cmd, "Provider contract tests", verbose=verbose)


def services_synthetic_yield(verbose: bool = False, test_names: list = None) -> bool:
    """Test synthetic yield calculation for SCHEDULED_YIELD assets."""
    print_section("Services: Synthetic Yield Calculation")
    print_info("Testing: SCHEDULED_YIELD asset valuation (ACT/365 SIMPLE interest)")
    print_info("Covers: Rate lookup, accrued interest, full valuation, DB integration")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_synthetic_yield.py", test_names)
    return run_command(cmd, "Synthetic yield tests", verbose=verbose)


def services_synthetic_yield_integration(verbose: bool = False, test_names: list = None) -> bool:
    """Test E2E synthetic yield integration scenarios."""
    print_section("Services: Synthetic Yield Integration E2E")
    print_info("Testing: ScheduledInvestmentProvider end-to-end scenarios")
    print_info("Scenarios: P2P loan (grace + late), bond compound quarterly, mixed SIMPLE/COMPOUND")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_synthetic_yield_integration.py", test_names)
    return run_command(cmd, "Synthetic yield integration E2E tests", verbose=verbose)


def services_transaction(verbose: bool = False, test_names: list = None) -> bool:
    """Test TransactionService CRUD operations, balance validation, and link resolution."""
    print_section("Services: Transaction Service")
    print_info("Testing: backend/app/services/transaction_service.py")
    print_info("Tests: CRUD, balance validation, link resolution, balance queries")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_service.py", test_names)

    return run_command(cmd, "Transaction service tests", verbose=verbose)


def services_broker(verbose: bool = False, test_names: list = None) -> bool:
    """Test BrokerService CRUD operations, initial balances, and flag validation."""
    print_section("Services: Broker Service")
    print_info("Testing: backend/app/services/broker_service.py")
    print_info("Tests: CRUD, initial deposits, get_summary, flag validation")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_broker_service.py", test_names)

    return run_command(cmd, "Broker service tests", verbose=verbose)


def services_user_profile(verbose: bool = False, test_names: list = None) -> bool:
    """Test user profile update service."""
    print_section("Services: User Profile")
    print_info("Testing: backend/app/services/user_service.py (update_profile)")
    print_info("Tests: Update username/email, uniqueness validation, error handling")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_user_profile.py", test_names)
    return run_command(cmd, "User profile service tests", verbose=verbose)


def services_edge_cases(verbose: bool = False, test_names: list = None) -> bool:
    """Test edge cases and regression scenarios for transactions."""
    print_section("Services: Transaction Edge Cases")
    print_info("Testing: Edge cases, boundary conditions, regression scenarios")
    print_info("Tests: Decimal precision, currency validation, date edge cases, null handling")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_edge_cases.py", test_names)
    return run_command(cmd, "Transaction edge cases tests", verbose=verbose)


def services_global_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test GlobalSettingsService."""
    print_section("Services: Global Settings Service")
    print_info("Testing: backend/app/services/global_settings_service.py")
    print_info("Tests: Type conversion, DB reads with defaults, TTL/upload/registration getters")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_global_settings_service.py", test_names)
    return run_command(cmd, "Global settings service tests", verbose=verbose)


def services_fx_core(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX core helpers."""
    print_section("Services: FX Core Helpers")
    print_info("Testing: backend/app/services/fx.py (core functions not covered by fx-conversion)")
    print_info("Tests: normalize_rate, upsert_rates_bulk, delete_rates_bulk, _count_actual_changes")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_core.py", test_names)
    return run_command(cmd, "FX core helpers tests", verbose=verbose)


def services_static_uploads(verbose: bool = False, test_names: list = None) -> bool:
    """Test static uploads service."""
    print_section("Services: Static Uploads")
    print_info("Testing: backend/app/services/static_uploads.py")
    print_info("Tests: File save/list/get/delete, security validation, user filtering")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_static_uploads.py", test_names)
    return run_command(cmd, "Static uploads service tests", verbose=verbose)


def services_brim_parse_error(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIMParseError exception class."""
    print_section("Services: BRIM Parse Error")
    print_info("Testing: backend/app/services/brim_provider.py (BRIMParseError)")
    print_info("Tests: Constructor, message/details attributes, exception hierarchy")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_error.py", test_names)
    return run_command(cmd, "BRIM parse error tests", verbose=verbose)


def services_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test settings service: get_session_ttl_sync."""
    print_section("Services: Settings Service")
    print_info("Testing: backend/app/services/settings_service.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_settings_service.py", test_names)
    return run_command(cmd, "Settings service tests", verbose=verbose)


def services_current_price_bootstrap(verbose: bool = False, test_names: list = None) -> bool:
    """Test F.2/F.3 unit helper `_extend_ohlc_bounds` in asset_source."""
    print_section("Services: Current Price Bootstrap (F.2/F.3)")
    print_info("Testing OHLC widening helper used by /assets/prices/current side-effect")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_current_price_bootstrap.py", test_names)
    return run_command(cmd, "Current price bootstrap tests", verbose=verbose)


def services_scheduled_investment_param_change(verbose: bool = False, test_names: list = None) -> bool:
    """Test #R6-4 symmetric wipe on scheduled_investment provider_params change."""
    print_section("Services: Scheduled Investment Param-Change Wipe (#R6-4)")
    print_info("Testing bulk_assign_providers wipe: prices + auto-events + tx disconnect")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduled_investment_param_change.py", test_names)
    return run_command(cmd, "Scheduled investment param-change tests", verbose=verbose)


def services_brim_provider_base(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIMProvider abstract base default properties."""
    print_section("Services: BRIMProvider Base Defaults (G-batch6)")
    print_info("Testing default property values inherited by all BRIM provider subclasses")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_provider_base.py", test_names)
    return run_command(cmd, "BRIM provider base tests", verbose=verbose)


def services_financial_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test pure-math financial utilities (WAC calculation, target currency)."""
    print_section("Services: Financial Utils (WAC)")
    print_info("Testing: backend/app/utils/financial_utils.py")
    print_info("Tests: compute_wac_from_txlist, determine_target_currency")
    print_info("Pure math — no server, no DB required")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial_utils.py", test_names)
    return run_command(cmd, "Financial utils tests", verbose=verbose)


def services_asset_sync_counts(verbose: bool = False, test_names: list = None) -> bool:
    """Test asset sync count tracking."""
    print_section("Services: Asset Sync Counts")
    print_info("Testing: Asset sync count logic")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_sync_counts.py", test_names)
    return run_command(cmd, "Asset sync counts tests", verbose=verbose)


def services_brim_versioning(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIM provider versioning."""
    print_section("Services: BRIM Versioning")
    print_info("Testing: BRIM provider version detection and compatibility")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_versioning.py", test_names)
    return run_command(cmd, "BRIM versioning tests", verbose=verbose)


def services_all(verbose: bool = False) -> bool:
    """Run all backend service tests."""
    print_header("LibreFolio Backend Services Tests")
    print_info("Testing business logic and service layer")
    print_info("No backend server required")

    print_info("\n⚙️  Creating clean test database for services tests...")
    if not db_create(verbose=False):
        print_error("Failed to create clean test database")
        print_warning("Services tests may fail due to dirty database state")
    else:
        print_success("Clean test database created\n")

    return _run_test_suite(
        suite_name="Backend Services Tests",
        tests=_get_category_tests_for_all("services", verbose),
        verbose=verbose,
        header_msg=None,
        summary_title="Backend Services Test Summary",
        success_msg="All backend services tests passed! 🎉",
            resume=_RESUME_MODE,
        )


def populate_registry(registry: dict) -> None:
    """Register all service test entries."""
    cat = make_category(
        help_text="Backend service logic tests (conversions, calculations, CRUD)",
        description="""
Backend Service Tests

Tests for business logic and service layer:
  • FX conversion (direct, inverse, roundtrip, forward-fill)
  • Asset source (provider assignment, synthetic yield)
  • Provider registry (lookup, priority, fallback)
  • Transaction service (CRUD, balance, links)
  • Broker service (CRUD, summaries)

Note: No backend server required.
""")
    add_test(cat, "fx-conversion", services_fx_conversion, name="FX Conversion", desc="Currency conversion algorithms", prereq="Database created")
    add_test(cat, "asset-metadata", services_asset_metadata, name="Asset Metadata", desc="Parse/serialize, diff, patch semantics")
    add_test(cat, "asset-source", services_asset_source, name="Asset Source", desc="Provider assignment, synthetic yield")
    add_test(cat, "asset-source-refresh", services_asset_source_refresh, name="Asset Source Refresh", desc="Bulk refresh orchestration smoke test")
    add_test(cat, "provider-registry", services_provider_registry, name="Provider Registry", desc="Registration, lookup, priority, fallback")
    add_test(cat, "provider-contracts", services_provider_contracts, name="Provider Contracts", desc="ABC compliance for ALL registered providers")
    add_test(cat, "synthetic-yield", services_synthetic_yield, name="Synthetic Yield", desc="SCHEDULED_YIELD asset valuation")
    add_test(cat, "synthetic-yield-integration", services_synthetic_yield_integration, name="Synthetic Yield Integration", desc="E2E scenarios (P2P, bond, mixed)")
    add_test(cat, "transaction", services_transaction, name="Transaction Service", desc="CRUD, balance validation, link resolution")
    add_test(cat, "broker", services_broker, name="Broker Service", desc="CRUD, initial deposits, summaries")
    add_test(cat, "user-profile", services_user_profile, name="User Profile", desc="Username/email update, validation")
    add_test(cat, "edge-cases", services_edge_cases, name="Transaction Edge Cases", desc="Decimal precision, currency validation, date edge cases")
    add_test(cat, "global-settings", services_global_settings, name="Global Settings", desc="Type conversion, DB reads, TTL getters")
    add_test(cat, "fx-core", services_fx_core, name="FX Core Helpers", desc="normalize_rate, upsert/delete bulk, changes")
    add_test(cat, "static-uploads", services_static_uploads, name="Static Uploads", desc="File save/list/get/delete, security")
    add_test(cat, "brim-parse-error", services_brim_parse_error, name="BRIM Parse Error", desc="Exception class tests")
    add_test(cat, "settings", services_settings, name="Settings Service", desc="get_session_ttl_sync")
    add_test(cat, "current-price-bootstrap", services_current_price_bootstrap, name="Current Price Bootstrap", desc="OHLC widening helper (F.2/F.3)")
    add_test(cat, "scheduled-investment-param-change", services_scheduled_investment_param_change, name="Scheduled Investment Param Change", desc="Symmetric wipe on provider_params change")
    add_test(cat, "brim-provider-base", services_brim_provider_base, name="BRIM Provider Base", desc="Abstract base default properties")
    add_test(cat, "financial-utils", services_financial_utils, name="Financial Utils", desc="WAC pure math (compute_wac_from_txlist, determine_target_currency)")
    add_test(cat, "asset-sync-counts", services_asset_sync_counts, name="Asset Sync Counts", desc="Asset sync count tracking")
    add_test(cat, "brim-versioning", services_brim_versioning, name="BRIM Versioning", desc="Provider version detection and compatibility")
    add_test(cat, "all", services_all, test_names=False, name="All Services Tests", desc="Run all service tests")
    registry["services"] = cat

