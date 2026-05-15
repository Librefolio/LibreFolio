"""
Backend API endpoint tests and E2E tests.
"""

from ._common import (
    _run_test_suite, _get_category_tests_for_all, _build_pytest_cmd, run_command,
    print_section, print_info,
    make_category, add_test,
)


def api_fx(verbose: bool = False, test_names: list = None) -> bool:
    """Run FX API endpoint tests."""
    print_section("FX API Endpoint Tests")
    print_info("Testing REST API endpoints for FX functionality")
    print_info("Tests: Currency conversion, providers, pair sources CRUD")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_api.py", test_names)
    return run_command(cmd, "FX API tests", verbose=verbose)


def api_fx_compress_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Run tests for _compress_convert_errors utility in FX API."""
    print_section("FX Compress Errors Tests")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_compress_errors.py", test_names)
    return run_command(cmd, "FX compress errors tests", verbose=verbose)


def api_preview_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Run tests for PreviewCache in uploads API."""
    print_section("Preview Cache Tests")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_preview_cache.py", test_names)
    return run_command(cmd, "Preview cache tests", verbose=verbose)


def api_fx_sync(verbose: bool = False, test_names: list = None) -> bool:
    """Run FX Sync API endpoint tests."""
    print_section("FX Sync API Endpoint Tests")
    print_info("Testing FX rate synchronization endpoints")
    print_info("Tests: GET /fx/currencies/sync with all scenarios")
    print_info("Tests: Error handling (FXServiceError), auto-config mode, provider validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_sync.py", test_names)
    return run_command(cmd, "FX Sync API tests", verbose=verbose)


def api_assets_price(verbose: bool = False, test_names: list = None) -> bool:
    """Run Assets Price API endpoint tests."""
    print_section("Assets Price API Endpoint Tests")
    print_info("Testing asset price management endpoints")
    print_info("Tests: POST /assets/prices (bulk upsert)")
    print_info("Tests: DELETE /assets/prices (bulk delete)")
    print_info("Tests: POST /assets/prices/query (bulk read from DB)")
    print_info("Tests: POST /assets/prices/sync (from providers)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_prices.py", test_names)
    return run_command(cmd, "Assets Price API tests", verbose=verbose)


def api_assets_provider(verbose: bool = False, test_names: list = None) -> bool:
    """Run Assets Provider API endpoint tests."""
    print_section("Assets Provider API Endpoint Tests")
    print_info("Testing provider assignment endpoints")
    print_info("Tests: GET /assets/provider/assignments")
    print_info("Tests: POST /assets/provider (edge cases)")
    print_info("Tests: DELETE /assets/provider (edge cases)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_provider.py", test_names)
    return run_command(cmd, "Assets Provider API tests", verbose=verbose)


def api_assets_metadata(verbose: bool = False, test_names: list = None) -> bool:
    """Run Assets Metadata API endpoint tests."""
    print_section("Assets Metadata API Endpoint Tests")
    print_info("Testing REST API endpoints for asset metadata management")
    print_info("Tests: PATCH metadata, bulk read, refresh endpoints")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_metadata.py", test_names)
    return run_command(cmd, "Assets Metadata API tests", verbose=verbose)


def api_assets_events(verbose: bool = False, test_names: list = None) -> bool:
    """Run Assets Events API endpoint tests."""
    print_section("Assets Events API Endpoint Tests")
    print_info("Testing REST API endpoints for asset event management")
    print_info("Tests: POST /assets/events (bulk upsert manual)")
    print_info("Tests: DELETE /assets/events/{id} (delete by PK)")
    print_info("Tests: POST /assets/events/query (bulk query)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_events.py", test_names)
    return run_command(cmd, "Assets Events API tests", verbose=verbose)


def api_events_target_currency(verbose: bool = False, test_names: list = None) -> bool:
    """Run Events target_currency (E.8) FX conversion tests."""
    print_section("Events target_currency (E.8) Tests")
    print_info("Testing FX conversion pass on POST /assets/events/query")
    print_info("Covers: original_value, fx_rate_date, fx_days_back, errors[] non-fatal")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_events_target_currency.py", test_names)
    return run_command(cmd, "Events target_currency (E.8) tests", verbose=verbose)


def api_assets_crud(verbose: bool = False, test_names: list = None) -> bool:
    """Run Assets CRUD API endpoint tests."""
    print_section("Assets CRUD API Endpoint Tests")
    print_info("Testing REST API endpoints for asset CRUD operations")
    print_info("Tests: Create assets, list/filter assets, delete assets")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_crud.py", test_names)
    return run_command(cmd, "Assets CRUD API tests", verbose=verbose)


def api_utilities(verbose: bool = False, test_names: list = None) -> bool:
    """Run Utilities API endpoint tests."""
    print_section("Utilities API Endpoint Tests")
    print_info("Testing REST API endpoints for frontend utilities")
    print_info("Tests: GET /utilities/sectors, GET /utilities/countries/normalize")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_utilities.py", test_names)
    return run_command(cmd, "Utilities API tests", verbose=verbose)


def api_system(verbose: bool = False, test_names: list = None) -> bool:
    """Test system API."""
    print_section("System API Tests")
    print_info("Testing: system.py utility functions (parse_pipfile, deps)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_system_api.py", test_names)
    return run_command(cmd, "System API tests", verbose=verbose)


def api_backup(verbose: bool = False, test_names: list = None) -> bool:
    """Test backup API."""
    print_section("Backup API Tests")
    print_info("Testing: backup.py placeholder endpoints")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_api.py", test_names)
    return run_command(cmd, "Backup API tests", verbose=verbose)


def api_transactions(verbose: bool = False, test_names: list = None) -> bool:
    """Run Transactions API endpoint tests."""
    print_section("Transactions API Endpoint Tests")
    print_info("Testing REST API endpoints for transaction management")
    print_info("Tests: POST /transactions (bulk create), GET /transactions (query)")
    print_info("Tests: GET /transactions/{id}, PATCH /transactions, DELETE /transactions")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transactions_api.py", test_names)
    return run_command(cmd, "Transactions API tests", verbose=verbose)


def api_transfer_promotion(verbose: bool = False, test_names: list = None) -> bool:
    """Run Transfer Promotion API tests."""
    print_section("Transfer Promotion API Tests")
    print_info("Testing POST /transactions/transfers/promote (Block H.4)")
    print_info("Tests: DEPOSIT/WITHDRAWAL → TRANSFER / FX_CONVERSION atomic promotion")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transfer_promotion.py", test_names)
    return run_command(cmd, "Transfer Promotion API tests", verbose=verbose)


def api_transactions_validate(verbose: bool = False, test_names: list = None) -> bool:
    """Run POST /transactions/validate dry-run tests."""
    print_section("Transactions Validate (C.1) API Tests")
    print_info("Testing POST /transactions/validate — dry-run mixed batch")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transactions_validate.py", test_names)
    return run_command(cmd, "Transactions validate tests", verbose=verbose)


def api_tx_balance_walk(verbose: bool = False, test_names: list = None) -> bool:
    """Run transaction balance walk tests (same-day, cascade, end-of-day)."""
    print_section("Transaction Balance Walk Tests")
    print_info("Testing end-of-day balance validation, same-day ordering, cascading edits/deletes")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_tx_balance_walk.py", test_names)
    return run_command(cmd, "Balance walk tests", verbose=verbose)


def api_events_suggest(verbose: bool = False, test_names: list = None) -> bool:
    """Run POST /transactions/events/suggest tests."""
    print_section("Events Suggest (C.2) API Tests")
    print_info("Testing POST /transactions/events/suggest — candidate events within tolerance")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_events_suggest.py", test_names)
    return run_command(cmd, "Events suggest tests", verbose=verbose)


def api_batch_split_promote(verbose: bool = False, test_names: list = None) -> bool:
    """Run batch split, promote, and promote-suggest pipeline tests."""
    print_section("Batch Split/Promote Pipeline Tests")
    print_info("Testing splits[] and promotes[] in unified batch")
    print_info("Tests: Split TRANSFER/CASH_TRANSFER, Promote saved+saved/new+new/saved+new")
    print_info("Tests: POST /transactions/promote-suggest bulk candidate search")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transactions_batch_split_promote.py", test_names)
    return run_command(cmd, "Batch split/promote tests", verbose=verbose)


def api_transactions_wac(verbose: bool = False, test_names: list = None) -> bool:
    """Run WAC (Weighted Average Cost) API tests."""
    print_section("WAC Cost Basis API Tests")
    print_info("Testing cost_basis_override Currency, auto-calc WAC, recalc-wac endpoint")
    print_info("Tests: WAC-1→13 (override, auto-calc, cross-FX, missing, recalc, validation, promote)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transactions_wac.py", test_names)
    return run_command(cmd, "WAC cost basis tests", verbose=verbose)


def api_ohlc_sentinel(verbose: bool = False, test_names: list = None) -> bool:
    """Run OHLC sentinel semantics tests."""
    print_section("OHLC Sentinel (F.4) API Tests")
    print_info("Testing sentinel rules on POST /assets/prices: None/-1/value")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_ohlc_sentinel.py", test_names)
    return run_command(cmd, "OHLC sentinel tests", verbose=verbose)


def api_current_price_persistence(verbose: bool = False, test_names: list = None) -> bool:
    """Run /assets/prices/current side-effect persistence tests."""
    print_section("Current Price Persistence (F.2/F.3) API Tests")
    print_info("Testing side-effect: /current endpoint upserts today's OHLC via mockprov")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_current_price_persistence.py", test_names)
    return run_command(cmd, "Current price persistence tests", verbose=verbose)


def api_prices_currency_coherence(verbose: bool = False, test_names: list = None) -> bool:
    """Run currency-mismatch hard-reject tests."""
    print_section("Prices Currency Coherence (I.2) API Tests")
    print_info("Testing hard-400 on FAPricePoint.currency != asset.currency")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_prices_currency_coherence.py", test_names)
    return run_command(cmd, "Prices currency coherence tests", verbose=verbose)


def api_asset_currency_change(verbose: bool = False, test_names: list = None) -> bool:
    """Run asset currency-change flow tests."""
    print_section("Asset Currency Change (I.3 + I-bis #7) API Tests")
    print_info("Testing PATCH /assets currency change: 409 when blocked, wipe + retry happy path")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_asset_currency_change.py", test_names)
    return run_command(cmd, "Asset currency change tests", verbose=verbose)


def api_asset_prices_export(verbose: bool = False, test_names: list = None) -> bool:
    """Run asset prices export + CSV round-trip tests."""
    print_section("Asset Prices Export + CSV Round-Trip (I.4 + I-bis #5) API Tests")
    print_info("Testing GET /backup/asset/{id}/prices (CSV/JSON) + round-trip re-import")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_asset_prices_export.py", test_names)
    return run_command(cmd, "Asset prices export tests", verbose=verbose)


def api_prices_sync_delta(verbose: bool = False, test_names: list = None) -> bool:
    """Run sync delta payload tests."""
    print_section("Prices Sync Delta (I-bis #24) API Tests")
    print_info("Testing FARefreshResult.changed_points: populated/None/cap/idempotent")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_prices_sync_delta.py", test_names)
    return run_command(cmd, "Prices sync delta tests", verbose=verbose)


def api_market_data_wipe(verbose: bool = False, test_names: list = None) -> bool:
    """Run market-data wipe endpoint tests."""
    print_section("Market-Data Wipe (R3-3) API Tests")
    print_info("Testing GET /assets/{id}/market-data/summary + POST /wipe (Policy D)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_market_data_wipe.py", test_names)
    return run_command(cmd, "Market-data wipe tests", verbose=verbose)


def api_backup_export_extras(verbose: bool = False, test_names: list = None) -> bool:
    """Run backup export tests for events + fx_rates endpoints."""
    print_section("Backup Export Extras (events + FX) API Tests")
    print_info("Testing GET /backup/asset/{id}/events and /backup/fx/{base}/{quote}/rates")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_export_extras.py", test_names)
    return run_command(cmd, "Backup export extras tests", verbose=verbose)


def api_uploads_serve_file(verbose: bool = False, test_names: list = None) -> bool:
    """Run /uploads/file/{id} preview / download / MIME branch tests."""
    print_section("Uploads Serve-File API Tests (G-batch7)")
    print_info("Testing GET /uploads/file/{id}: plain, text+image preview, download flag")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_uploads_serve_file.py", test_names)
    return run_command(cmd, "Uploads serve-file tests", verbose=verbose)


def api_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """Run Brokers API endpoint tests."""
    print_section("Brokers API Endpoint Tests")
    print_info("Testing REST API endpoints for broker management")
    print_info("Tests: POST /brokers (create), GET /brokers (list)")
    print_info("Tests: GET /brokers/{id}, PATCH /brokers, DELETE /brokers")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_brokers_api.py", test_names)
    return run_command(cmd, "Brokers API tests", verbose=verbose)


def api_brim(verbose: bool = False, test_names: list = None) -> bool:
    """Run BRIM API endpoint tests."""
    print_section("BRIM API Endpoint Tests")
    print_info("Testing REST API endpoints for broker report import")
    print_info("Tests: POST /import/upload, GET /import/files, POST /import/files/{id}/parse")
    print_info("Tests: File storage, parse response, duplicate detection, E2E import flow")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_brim_api.py", test_names)
    return run_command(cmd, "BRIM API tests", verbose=verbose)


def search2prices_test(verbose: bool = False, test_names: list = None) -> bool:
    """Run E2E API tests: Search → Create → Assign → Metadata → Prices."""
    print_section("E2E API Test search-to-prices")
    print_info("Testing complete end-to-end flow via API")
    print_info("Tests: Search → Create Asset → Assign Provider → Refresh Metadata → Refresh Prices")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_search_to_prices.py", test_names)
    return run_command(cmd, "E2E API tests", verbose=verbose)


def api_auth(verbose: bool = False, test_names: list = None) -> bool:
    """Run Authentication API endpoint tests."""
    print_section("Authentication API Tests")
    print_info("Testing REST API endpoints for authentication")
    print_info("Tests: POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me")
    print_info("Tests: Session cookies, password validation, duplicate detection")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_auth_api.py", test_names)
    return run_command(cmd, "Auth API tests", verbose=verbose)


def api_profile(verbose: bool = False, test_names: list = None) -> bool:
    """Run Profile Update API endpoint tests."""
    print_section("Profile Update API Tests")
    print_info("Testing REST API endpoints for profile updates")
    print_info("Tests: PUT /auth/profile")
    print_info("Tests: Username update, email update, validation, uniqueness")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_profile_api.py", test_names)
    return run_command(cmd, "Profile API tests", verbose=verbose)


def api_settings(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run settings API tests."""
    print_section("Settings API Tests")
    print_info("Testing REST API endpoints for user and global settings")
    print_info("Tests: GET/PUT /settings/user, GET/PUT /settings/global")
    print_info("Tests: Admin permissions, setting validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_settings_api.py", test_names)
    return run_command(cmd, "Settings API tests", verbose=verbose)


def api_uploads(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run uploads API tests."""
    print_section("Uploads API Tests")
    print_info("Testing REST API endpoints for file uploads")
    print_info("Tests: POST /uploads, GET /uploads, DELETE /uploads/{id}")
    print_info("Tests: Download, plugin static assets")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_uploads_api.py", test_names)
    return run_command(cmd, "Uploads API tests", verbose=verbose)


def api_broker_access(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run broker access API tests."""
    print_section("Broker Access API Tests")
    print_info("Testing REST API endpoints for broker access management")
    print_info("Tests: GET/POST/PATCH/DELETE /brokers/{id}/access")
    print_info("Tests: Role hierarchy (OWNER > EDITOR > VIEWER)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_broker_access_api.py", test_names)
    return run_command(cmd, "Broker Access API tests", verbose=verbose)


def api_broker_multiuser(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run broker multi-user role tests."""
    print_section("Broker Multi-User Role Tests")
    print_info("Testing role-based permissions on broker operations")
    print_info("Tests: OWNER permissions, EDITOR permissions, VIEWER permissions")
    print_info("Tests: User isolation between different users")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_broker_multiuser_api.py", test_names)
    return run_command(cmd, "Broker Multi-User API tests", verbose=verbose)


def api_users_search(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run user search API tests."""
    print_section("User Search & Share Validation API Tests")
    print_info("Testing REST API endpoints for user search")
    print_info("Tests: GET /users/search, share_percentage sum validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_users_search.py", test_names)
    return run_command(cmd, "User Search API tests", verbose=verbose)


def api_test(verbose: bool = False) -> bool:
    """Run all API tests."""
    return _run_test_suite(
        suite_name="API Tests",
        tests=_get_category_tests_for_all("api", verbose),
        verbose=verbose,
        info_msgs=[
            "Testing REST API endpoints",
            "Note: Server will be automatically started/stopped by tests",
            ],
        combine_coverage=True,
        )


def e2e_brim(verbose: bool = False, test_names: list = None) -> bool:
    """Run BRIM E2E tests."""
    print_section("E2E Test: BRIM Import Flow")
    print_info("Testing complete broker report import workflow")
    print_info("Tests: Upload → Parse → Asset Mapping → Duplicate Detection → Import")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_brim_e2e.py", test_names)
    return run_command(cmd, "BRIM E2E tests", verbose=verbose)


def e2e_test(verbose: bool = False) -> bool:
    """Run all E2E tests."""
    return _run_test_suite(
        suite_name="E2E Tests",
        tests=_get_category_tests_for_all("e2e", verbose),
        verbose=verbose,
        header_msg="LibreFolio E2E Tests with API interaction",
        info_msgs=[
            "Testing E2E workflow using REST API endpoints",
            "Note: Server will be automatically started/stopped by tests",
            ],
        combine_coverage=True,
        )


def populate_registry(registry: dict) -> None:
    """Register all API and E2E test entries."""
    # ── API category ──
    api = make_category(
        help_text="REST API endpoint tests (requires test server)",
        description="""
API Endpoint Tests

Tests for REST API endpoints (server auto-started):
  • FX, Assets, Transactions, Brokers, Auth, Settings, Uploads, System, Backup
""")
    add_test(api, "fx", api_fx, name="FX API", desc="Conversion, providers, pair sources")
    add_test(api, "fx-compress-errors", api_fx_compress_errors, name="FX Compress Errors", desc="_compress_convert_errors utility")
    add_test(api, "preview-cache", api_preview_cache, name="Preview Cache", desc="PreviewCache in uploads API")
    add_test(api, "fx-sync", api_fx_sync, name="FX Sync API", desc="FX rate synchronization endpoints")
    add_test(api, "assets-price", api_assets_price, name="Assets Price API", desc="Bulk upsert, delete, query, sync")
    add_test(api, "assets-provider", api_assets_provider, name="Assets Provider API", desc="Provider assignment endpoints")
    add_test(api, "assets-metadata", api_assets_metadata, name="Assets Metadata API", desc="PATCH metadata, bulk read, refresh")
    add_test(api, "assets-events", api_assets_events, name="Assets Events API", desc="Bulk upsert, delete, query")
    add_test(api, "events-target-currency", api_events_target_currency, name="Events Target Currency", desc="FX conversion on events query (E.8)")
    add_test(api, "assets-crud", api_assets_crud, name="Assets CRUD API", desc="Create, list, filter, delete assets")
    add_test(api, "utilities", api_utilities, name="Utilities API", desc="Sectors, countries")
    add_test(api, "system", api_system, name="System API", desc="parse_pipfile, deps")
    add_test(api, "backup", api_backup, name="Backup API", desc="Placeholder endpoints")
    add_test(api, "transactions", api_transactions, name="Transactions API", desc="Bulk create, query, patch, delete")
    add_test(api, "transfer-promotion", api_transfer_promotion, name="Transfer Promotion", desc="DEPOSIT/WITHDRAWAL → TRANSFER")
    add_test(api, "transactions-validate", api_transactions_validate, name="Transactions Validate", desc="POST /transactions/validate dry-run")
    add_test(api, "tx-balance-walk", api_tx_balance_walk, name="TX Balance Walk", desc="Same-day ordering, cascade, end-of-day")
    add_test(api, "events-suggest", api_events_suggest, name="Events Suggest", desc="Candidate events within tolerance")
    add_test(api, "batch-split-promote", api_batch_split_promote, name="Batch Split/Promote", desc="Split/promote in unified batch + suggest")
    add_test(api, "transactions-wac", api_transactions_wac, name="WAC Cost Basis", desc="cost_basis_override Currency, auto-calc WAC, recalc-wac")
    add_test(api, "ohlc-sentinel", api_ohlc_sentinel, name="OHLC Sentinel", desc="Sentinel rules on POST /assets/prices")
    add_test(api, "current-price-persistence", api_current_price_persistence, name="Current Price Persistence", desc="/current endpoint OHLC upsert")
    add_test(api, "prices-currency-coherence", api_prices_currency_coherence, name="Prices Currency Coherence", desc="Hard-400 on currency mismatch")
    add_test(api, "asset-currency-change", api_asset_currency_change, name="Asset Currency Change", desc="409 blocked, wipe + retry")
    add_test(api, "asset-prices-export", api_asset_prices_export, name="Asset Prices Export", desc="CSV/JSON export + round-trip")
    add_test(api, "prices-sync-delta", api_prices_sync_delta, name="Prices Sync Delta", desc="changed_points payload")
    add_test(api, "market-data-wipe", api_market_data_wipe, name="Market Data Wipe", desc="Summary + wipe (Policy D)")
    add_test(api, "backup-export-extras", api_backup_export_extras, name="Backup Export Extras", desc="Events + FX rates export")
    add_test(api, "uploads-serve-file", api_uploads_serve_file, name="Uploads Serve File", desc="Preview, download, MIME")
    add_test(api, "brokers", api_brokers, name="Brokers API", desc="CRUD broker endpoints")
    add_test(api, "brim", api_brim, name="BRIM API", desc="Upload, parse, import flow")
    add_test(api, "auth", api_auth, name="Auth API", desc="Register, login, logout, me")
    add_test(api, "profile", api_profile, name="Profile API", desc="Username/email update")
    add_test(api, "settings", api_settings, name="Settings API", desc="User and global settings")
    add_test(api, "uploads", api_uploads, name="Uploads API", desc="Upload, list, download, delete")
    add_test(api, "broker-access", api_broker_access, name="Broker Access API", desc="Access management, roles")
    add_test(api, "broker-multiuser", api_broker_multiuser, name="Broker Multi-User", desc="Role-based permissions")
    add_test(api, "users-search", api_users_search, name="User Search API", desc="User search, share validation")
    add_test(api, "all", api_test, test_names=False, name="All API Tests", desc="Run all API tests")
    registry["api"] = api

    # ── E2E category ──
    e2e = make_category(
        help_text="End-to-end API workflow tests",
        description="""
E2E API Tests

Complete workflow tests via REST API:
  • Search → Create → Assign → Metadata → Prices
  • BRIM import flow: Upload → Parse → Import
""")
    add_test(e2e, "search-to-prices", search2prices_test, name="Search to Prices",
             desc="Full asset lifecycle flow", prereq="Database created",
             tests="Search → Create → Assign → Metadata → Prices")
    add_test(e2e, "brim-e2e", e2e_brim, name="BRIM E2E",
             desc="Test complete BRIM import flow", prereq="Database created",
             tests="Upload → Parse → Asset Mapping → Import")
    add_test(e2e, "all", e2e_test, test_names=False, name="All E2E Tests", desc="Run all E2E tests")
    registry["e2e"] = e2e

