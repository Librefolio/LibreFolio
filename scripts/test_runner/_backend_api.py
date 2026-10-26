"""
Backend API endpoint tests and E2E tests.
"""

import sqlite3
from contextlib import closing

from backend.test_scripts.test_db_config import get_test_db_path

from . import _common
from ._backend_db import db_populate
from ._common import (
    _build_pytest_cmd,
    _get_category_tests_for_all,
    _run_test_suite,
    add_test,
    make_category,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    run_command,
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


def api_fx_unit(verbose: bool = False, test_names: list = None) -> bool:
    """Run direct unit tests for FX API handlers (no live server/network)."""
    print_section("FX API Unit Tests")
    print_info("Testing happy-path/main-branch coverage in backend/app/api/v1/fx/")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_api_unit.py", test_names)
    return run_command(cmd, "FX API unit tests", verbose=verbose)


def api_fx_convert_sampling(verbose: bool = False, test_names: list = None) -> bool:
    """Run Z-29fx: POST /fx/currencies/convert sampled for a compact chart (handler in process, no server)."""
    print_section("FX Convert Sampling Tests")
    print_info("Testing max_points/resolution/sample_like on conversions, samples and their bounds, reduced and aligned signals")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_convert_sampling.py", test_names)
    return run_command(cmd, "FX convert sampling tests", verbose=verbose)


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


def api_period_changes(verbose: bool = False, test_names: list = None) -> bool:
    """Run the MF-P2 period-change route tests."""
    print_section("Period Changes API Tests (MF-P2)")
    print_info("Tests: POST /assets/prices/period-changes, POST /fx/currencies/period-changes")
    print_info("Tests: 401 without a session, 422 for base == quote, answer shape, the pages' numbers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_period_changes_api.py", test_names)
    return run_command(cmd, "Period changes API tests", verbose=verbose)


def api_signal_catalogs(verbose: bool = False, test_names: list = None) -> bool:
    """Run static Asset/FX signal catalog API tests."""
    print_section("Signal Catalog API Tests")
    print_info("Testing authenticated static Asset 22 / FX 9 catalogs without DB/history lookup")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_signal_catalogs.py", test_names)
    return run_command(cmd, "Signal catalog API tests", verbose=verbose)


def api_asset_signals(verbose: bool = False, test_names: list = None) -> bool:
    """Run Asset signal query API tests."""
    print_section("Asset Signal API Tests")
    print_info("Testing legacy, signal-only, isolation, annotations and structural validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_asset_signals_api.py", test_names)
    return run_command(cmd, "Asset signal API tests", verbose=verbose)


def api_fx_signals(verbose: bool = False, test_names: list = None) -> bool:
    """Run grouped FX signal conversion tests."""
    print_section("FX Signal API Tests")
    print_info("Testing combined bulk conversion, identity/rate mapping, grouping and legacy daily output")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_signals_api.py", test_names)
    return run_command(cmd, "FX signal API tests", verbose=verbose)


def api_signal_request_validation(verbose: bool = False, test_names: list = None) -> bool:
    """Run signal request validation API tests."""
    print_section("Signal Request Validation API Tests")
    print_info("Testing request validation for Asset and FX signal endpoints")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_signal_request_validation_api.py", test_names)
    return run_command(cmd, "Signal request validation API tests", verbose=verbose)


def api_signal_preview(verbose: bool = False, test_names: list = None) -> bool:
    """Run signal preview API tests (synthetic-data indicator compute)."""
    print_section("Signal Preview API Tests")
    print_info("Testing authenticated backend indicator compute on caller-supplied synthetic points")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_signal_preview_api.py", test_names)
    return run_command(cmd, "Signal preview API tests", verbose=verbose)


def api_ai_export(verbose: bool = False, test_names: list = None) -> bool:
    """Run AI Export API tests."""
    print_section("AI Export API Tests")
    print_info("Testing catalog, snapshot, authorization, and typed problem contracts")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_ai_export_api.py", test_names)
    return run_command(cmd, "AI Export API tests", verbose=verbose)


def api_ai_export_unpriced_asset(verbose: bool = False, test_names: list = None) -> bool:
    """Run the AI Export snapshot tests of a held asset with no price series (E-AI503), in-process on a private database."""
    print_section("AI Export API Tests: held asset without a price series")
    print_info("Testing POST /ai-export/snapshot when a held asset of any type has no stored price, or prices in mixed currencies")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_ai_export_unpriced_asset.py", test_names)
    return run_command(cmd, "AI Export unpriced asset API tests", verbose=verbose)


def api_tools(verbose: bool = False, test_names: list = None) -> bool:
    """Run Tool platform API tests."""
    print_section("Tools API Tests")
    print_info("Testing authenticated catalog, compute, diagnostics, and transport contracts")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_tools_api.py", test_names)
    return run_command(cmd, "Tools API tests", verbose=verbose)


def api_pac_planner_tool(verbose: bool = False, test_names: list = None) -> bool:
    """Run the PAC planner Tool through the live compute endpoint."""
    print_section("PAC Planner Tool API Tests")
    print_info("Testing pac_allocator/plan end to end: plan, needs_input, stale identity, repeats, withdrawn inputs")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_pac_planner_tool_api.py", test_names)
    return run_command(cmd, "PAC planner Tool API tests", verbose=verbose)


def api_risk(verbose: bool = False, test_names: list = None) -> bool:
    """Run deterministic risk catalog, query, and populated-DB tests."""
    print_section("Risk Analysis API Tests")
    print_info("Testing auth, contracts, error isolation, and real broker analytics")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_risk_api.py", test_names)
    return run_command(cmd, "Risk Analysis API tests", verbose=verbose)


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


def api_parametric_provider_semantics(verbose: bool = False, test_names: list = None) -> bool:
    """Run parametric-provider removal/switch semantics tests."""
    print_section("Parametric Provider Semantics Tests")
    print_info("Removal: prices and manual events survive, generated events cascade away")
    print_info("Switch: the invented series is discarded, the manual event is not")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_parametric_provider_semantics.py", test_names)
    return run_command(cmd, "Parametric provider semantics tests", verbose=verbose)


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


def api_asset_merge(verbose: bool = False, test_names: list = None) -> bool:
    """Run Asset Merge API endpoint tests (P3 — asset identity)."""
    print_section("Asset Merge API Endpoint Tests")
    print_info("Testing POST /assets/merge: dry-run preview, execution, identifier union, refusals")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_asset_merge_api.py", test_names)
    return run_command(cmd, "Asset Merge API tests", verbose=verbose)


def api_utilities(verbose: bool = False, test_names: list = None) -> bool:
    """Run Utilities API endpoint tests."""
    print_section("Utilities API Endpoint Tests")
    print_info("Testing REST API endpoints for frontend utilities")
    print_info("Tests: GET /utilities/sectors, GET /utilities/countries/normalize")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_utilities.py", test_names)
    return run_command(cmd, "Utilities API tests", verbose=verbose)


def api_utilities_currency_suggest(verbose: bool = False, test_names: list = None) -> bool:
    """E-19b1: GET /utilities/currencies/suggest, what a stored currency value stands for."""
    print_section("Utilities API: Currency Suggestion (E-19b1)")
    print_info("Tests: GET /utilities/currencies/suggest?value= -> {canonical, suggestion, candidates}; public; value of 1 to 200 characters")
    print_info("Note: Server will be automatically started and stopped by test")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_currency_suggest_api.py", test_names)
    return run_command(cmd, "Currency suggestion API tests", verbose=verbose)


def api_system(verbose: bool = False, test_names: list = None) -> bool:
    """Test system API."""
    print_section("System API Tests")
    print_info("Testing: system.py utility functions (parse_pipfile, deps)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_system_api.py", test_names)
    return run_command(cmd, "System API tests", verbose=verbose)


def api_instance_config_legal(verbose: bool = False, test_names: list = None) -> bool:
    """Test the legal block of GET /system/instance (A9, F09): in-process, the OpenAPI document, one live read."""
    print_section("Instance Configuration: Legal Links (A9)")
    print_info("Testing GET /api/v1/system/instance legal, LegalInstanceConfig, the OpenAPI document")
    print_info("In-process on private databases; one anonymous read on the lane's server, which sets neither variable")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_instance_config_legal_api.py", test_names)
    return run_command(cmd, "Instance configuration legal tests", verbose=verbose)


def api_system_wake(verbose: bool = False, test_names: list = None) -> bool:
    """Test the scheduled wake-up (POST /system/wake-sync) and its token, in an app of the test (no server reached)."""
    print_section("System API: the scheduled wake-up")
    print_info("Testing: LIBREFOLIO_WAKE_TOKEN(_FILE) → 404 off, 503 unusable, 401 without it; with it, one run at a time (409), a streamed 200 (spaces, then the run's report), a run left to end when its client goes (in-process app, run_due_jobs replaced)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_system_wake.py", test_names)
    return run_command(cmd, "System API wake-up tests", verbose=verbose)


def api_system_price_refresh(verbose: bool = False, test_names: list = None) -> bool:
    """Test «Aggiornamento prezzi…» (GET /system/price-refresh): 401 and a valid answer on the lane, the chosen states in-process (lot Z5)."""
    print_section("System API: the price refresh status")
    print_info(
        "Testing: GET /system/price-refresh → 401 without a session; any signed-in user 200 with state, reason, job, since, last_finished_at, last_refreshed; idle, starting, running, idle after a refreshed catch-up (in-process app, PRICE_REFRESH driven by the test); PriceRefreshResponse; OpenAPI"
    )
    print_info("Tests: PRAPI-001..008")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_system_price_refresh.py", test_names)
    return run_command(cmd, "System API price refresh tests", verbose=verbose)


def api_instance_block(verbose: bool = False, test_names: list = None) -> bool:
    """Test the instance block (workstream H, CP6): refuse_when_blocked, ALLOWED_WHEN_BLOCKED, GET /system/block."""
    print_section("Instance Block Tests")
    print_info("Testing: api/v1/instance_block.py and GET /system/block, blocked in process only (never the lane's backend)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_instance_block.py", test_names)
    return run_command(cmd, "Instance block tests", verbose=verbose)


def api_http_compression(verbose: bool = False, test_names: list = None) -> bool:
    """Test HTTP compression (GZipMiddleware) on the live backend."""
    print_section("HTTP Compression Tests")
    print_info("Testing: GZipMiddleware in main.py on API JSON, SvelteKit chunks, SPA fallback, PNG, SSE")
    print_info("Tests: gzip + Vary, small bodies untouched, immutable Cache-Control/ETag (304), Range (206), PNG/SSE never encoded")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_http_compression_api.py", test_names)
    return run_command(cmd, "HTTP compression tests", verbose=verbose)


def api_backup(verbose: bool = False, test_names: list = None) -> bool:
    """Test backup API."""
    print_section("Backup API Tests")
    print_info("Testing: instance backup jobs (start, poll, download, delete; admin only) and the /backup route order")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_api.py", test_names)
    return run_command(cmd, "Backup API tests", verbose=verbose)


def api_backup_instance_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Test what POST /backup/instance answers when the run cannot start, in an app of the test (no server reached)."""
    print_section("Backup API: start errors")
    print_info("Testing: POST /backup/instance → backup_folder_unusable, backup_failed, backup_busy (in-process app, jobs.start_backup replaced)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_instance_errors.py", test_names)
    return run_command(cmd, "Backup API start error tests", verbose=verbose)


def api_backup_panel(verbose: bool = False, test_names: list = None) -> bool:
    """Test the hosting panel's backup routes (/backup/panel/jobs) and their token, in an app of the test (no server reached)."""
    print_section("Backup API: the hosting panel's token")
    print_info("Testing: LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN(_FILE) → 404 off, 503 unusable (short, not visible ASCII), 401 without it; with it, the panel's own jobs only (in-process app, jobs replaced)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_panel.py", test_names)
    return run_command(cmd, "Backup API panel token tests", verbose=verbose)


def api_backup_restore(verbose: bool = False, test_names: list = None) -> bool:
    """Test the check of a backup archive before a restore (/backup/restore), in an app of the test (no server reached)."""
    print_section("Backup API: the restore check")
    print_info("Testing: PUT /backup/restore/upload (limit, space, links), POST/GET/DELETE /backup/restore/stage (report, refusals, one at a time, interrupted, prune) on real archives under tmp_path")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_restore.py", test_names)
    return run_command(cmd, "Backup API restore check tests", verbose=verbose)


def api_backup_restore_apply(verbose: bool = False, test_names: list = None) -> bool:
    """Test the confirmed restore through the API (/backup/restore, lot B3), in an app of the test (no server reached)."""
    print_section("Backup API: the restore confirmed")
    print_info("Testing: POST /backup/restore/stage/{id}/confirm, GET /backup/restore/status, DELETE /backup/restore/pending, POST /backup/restore/restart (the signal recorded, never sent); the copy of an active restore kept by DELETE /stage and prune")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_restore_apply.py", test_names)
    return run_command(cmd, "Backup API restore confirmation tests", verbose=verbose)


def api_backup_secure(verbose: bool = False, test_names: list = None) -> bool:
    """Test the secure backup through the API (lot B4): a password at the creation, the options, and the check of an envelope."""
    print_section("Backup API: the secure backup")
    print_info("Testing: POST /backup/instance with a password, GET /backup/instance/options, PUT /backup/restore/upload (kind), POST /backup/restore/stage with a password; no echo of a password")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_secure_api.py", test_names)
    return run_command(cmd, "Backup API secure backup tests", verbose=verbose)


def api_no_echo_route(verbose: bool = False, test_names: list = None) -> bool:
    """Test the route class whose 422 never repeats the body, shared by the routes that receive a secret."""
    print_section("API: 422 without echo")
    print_info("Testing: backend/app/api/no_echo.py (NoInputEchoRoute), on an app of the test; the routers that use it")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_no_echo_route.py", test_names)
    return run_command(cmd, "422 without echo tests", verbose=verbose)


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


def api_transactions_wac_inline(verbose: bool = False, test_names: list = None) -> bool:
    """Run WAC inline validate/commit tests (P16-P28)."""
    print_section("WAC Inline Validate/Commit Tests")
    print_info("Testing cost_basis_mode='auto'/'auto-detail' in /validate and /commit")
    print_info("Tests: P16-P28 (TRANSFER auto, ADJUSTMENT auto, source detection, intra-batch)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_wac_inline.py", test_names)
    return run_command(cmd, "WAC inline tests", verbose=verbose)


def api_assets_patch_fields(verbose: bool = False, test_names: list = None) -> bool:
    """Run asset PATCH fields tests."""
    print_section("Assets Patch Fields Tests")
    print_info("Testing PATCH /assets/{id} field-level updates")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_patch_fields.py", test_names)
    return run_command(cmd, "Assets patch fields tests", verbose=verbose)


def api_ohlc_sentinel(verbose: bool = False, test_names: list = None) -> bool:
    """Run OHLC sentinel semantics tests."""
    print_section("OHLC Sentinel (F.4) API Tests")
    print_info("Testing F.4 merge rules on POST /assets/prices: None/'clear'/value (N92: -1 is a negative number, refused)")

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
    print_info("Testing the hard reject on FAPricePoint.currency != asset.currency: 422 price_currency_mismatch, the whole upload (X-R71)")

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


def api_brim_scalable(verbose: bool = False, test_names: list = None) -> bool:
    """Run the Scalable Capital BRIM API flow tests."""
    print_section("BRIM Scalable API Tests")
    print_info("Testing the Scalable Capital plugins end to end: broker account and overnight account")
    print_info("Tests: upload, parse, commit, promote-suggest, promote, re-import as duplicates, one-broker cash")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_brim_scalable_api.py", test_names)
    return run_command(cmd, "BRIM Scalable API tests", verbose=verbose)


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


def api_admin_setup(verbose: bool = False, test_names: list = None) -> bool:
    """Run the API tests of the initial administrator's setup link (F02): POST /auth/setup, tokens/inspect admin_setup."""
    print_section("Initial Administrator Setup API Tests")
    print_info("Testing POST /auth/setup and POST /auth/tokens/inspect with purpose admin_setup")
    print_info("In-process on private databases for every case with a waiting administrator; on the lane's server only refusals that write nothing")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_admin_setup_api.py", test_names)
    return run_command(cmd, "Initial administrator setup API tests", verbose=verbose)


def api_validation_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Run the API tests of the 422 without the request's input (A-35): no password or token ever comes back."""
    print_section("Validation Errors API Tests")
    print_info("Testing that a 422 drops the input of every error, on the routes that carry a password or a token")
    print_info("In-process on a small app for the handler; on the lane's server only refusals, and seven accounts of its own")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_validation_errors_api.py", test_names)
    return run_command(cmd, "Validation errors API tests", verbose=verbose)


def api_login_throttle(verbose: bool = False, test_names: list = None) -> bool:
    """Run the API tests of the limit on failed sign-ins (F15) and of GET /security/checks, in-process."""
    print_section("Login Throttle API Tests")
    print_info("Testing the 429 TOO_MANY_ATTEMPTS of sign-in, change of password and change of address, and the Security checks")
    print_info("In-process on private databases, the limit turned on with limiters of its own: never the lane's server")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_login_throttle_api.py", test_names)
    return run_command(cmd, "Login throttle API tests", verbose=verbose)


def api_username_rules(verbose: bool = False, test_names: list = None) -> bool:
    """Run the API tests of A-21a, in-process: the @ in new usernames, addresses that are usernames, the sign-in's lookup."""
    print_section("Username Rules API Tests")
    print_info("Testing POST /auth/register, PUT /auth/profile and POST /auth/login under the rules of A-21a, workstream E's scenes")
    print_info("In-process on private databases with legacy accounts written as rows: never the lane's server")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_username_rules_api.py", test_names)
    return run_command(cmd, "Username rules API tests", verbose=verbose)


def api_whats_new(verbose: bool = False, test_names: list = None) -> bool:
    """Run the API tests of C-54, in-process: user.whats_new in the answers, POST /auth/whats-new/seen."""
    print_section("What's New API Tests")
    print_info("Testing user.whats_new in the answers of POST /auth/register, POST /auth/login, GET /auth/me and POST /auth/setup, and POST /auth/whats-new/seen")
    print_info("In-process on private databases, the running version patched, accounts written as rows: never the lane's server")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_whats_new_api.py", test_names)
    return run_command(cmd, "What's new API tests", verbose=verbose)


def api_security_checks(verbose: bool = False, test_names: list = None) -> bool:
    """Run the lane's tests of GET /security/checks: administrators only, the login limit off on the lane."""
    print_section("Security Checks API Tests")
    print_info("Testing GET /api/v1/security/checks on the lane's server: 200 admin, 403 member, 401 anonymous")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_security_checks_api.py", test_names)
    return run_command(cmd, "Security checks API tests", verbose=verbose)


def api_registration(verbose: bool = False, test_names: list = None) -> bool:
    """Run the registration API tests: modes, invitations, inspect, password reset, the public accounts block, the locked setting."""
    print_section("Registration API Tests")
    print_info("Testing POST /auth/register (invite_token), POST /auth/tokens/inspect, POST /auth/password-reset, GET /system/instance accounts, PATCH /settings/global/bulk lock")
    print_info("In-process on private databases where a mode, a variable or a limit is needed; on the lane's server only what changes nothing global")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_registration_api.py", test_names)
    return run_command(cmd, "Registration API tests", verbose=verbose)


def api_users_admin(verbose: bool = False, test_names: list = None) -> bool:
    """Run the users admin API tests: invitations, accounts and usage, PATCH with its guards, reset links, sessions, onboarding reset, logs."""
    print_section("Users Admin API Tests")
    print_info("Testing GET/POST /users/invites, DELETE /users/invites/{id}, GET /users, PATCH /users/{id}, POST /users/{id}/password-reset-link, /sessions/revoke, /onboarding/reset")
    print_info("In-process on private databases where a mode, a variable, a limit or the last administrator is needed; on the lane's server only the case's own accounts and tokens")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_users_admin_api.py", test_names)
    return run_command(cmd, "Users admin API tests", verbose=verbose)


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


def api_settings_currency_strict(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the E-19a settings currency tests: a user's base_currency strict, the 422 naming the code it stands for."""
    print_section("Settings Currency Strict API Tests (E-19a)")
    print_info("Tests: PUT /settings/user and the welcome flow refuse a non-ISO base_currency; an E-18 route's 422 names the ISO code")
    print_info("Note: Server will be automatically started and stopped by test")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_settings_currency_strict_api.py", test_names)
    return run_command(cmd, "Settings currency strict API tests", verbose=verbose)


def api_plugin_settings(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the plugin settings API tests: catalogue, all-or-nothing writes, write-only secrets, isolation, delivery."""
    print_section("Plugin Settings API Tests")
    print_info("Testing GET /settings/plugins and PATCH /settings/plugins/bulk with the test double mockprov (MOCKFX read-only)")
    print_info("Tests: catalogue and roles, write-only secrets, 422 with every item, no input echo, isolation, delivery to the plugin, CASCADE and SET NULL")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_plugin_settings_api.py", test_names)
    return run_command(cmd, "Plugin settings API tests", verbose=verbose)


def api_cache_admin(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run cache admin API tests."""
    print_section("Cache Admin API Tests")
    print_info("Testing REST API endpoints for cache administration")
    print_info("Tests: GET /settings/cache/status, POST /settings/cache/clear-all, POST /settings/cache/clear/{name}")
    print_info("Tests: CAPI-001..008 — auth levels, admin-only clears, functional clear verification")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_cache_admin_api.py", test_names)
    return run_command(cmd, "Cache Admin API tests", verbose=verbose)


def api_scheduler(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run scheduler API tests."""
    print_section("Scheduler API Tests")
    print_info("Testing REST API endpoints for scheduler state and log")
    print_info("Tests: GET /settings/scheduler/state, GET /settings/scheduler/log")
    print_info("Tests: SAPI-001..014 — admin-only access, structure, since filter, lot Z7b's deferred/retry/backoff fields")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_scheduler_api.py", test_names)
    return run_command(cmd, "Scheduler API tests", verbose=verbose)


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


def api_account_deletion(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run account deletion API tests: the last-owner rule applied to every broker of the account."""
    print_section("Account Deletion API Tests")
    print_info("Testing DELETE /auth/users/me: brokers solely owned go with their transactions and files")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_account_deletion_api.py", test_names)
    return run_command(cmd, "Account deletion API tests", verbose=verbose)


def api_session_revocation(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run session revocation API tests: a password change ends every other session of the account."""
    print_section("Session Revocation API Tests")
    print_info("Testing POST /auth/change-password: session version +1, the device that changed it gets a new cookie")
    print_info("Tests: other devices and the old cookie refused, other accounts untouched, refusals end nothing")
    print_info("A-27: a password change or a real address change kills the account's live reset links; capitals only and refusals keep them")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_session_revocation_api.py", test_names)
    return run_command(cmd, "Session revocation API tests", verbose=verbose)


def api_address_probe(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the address probe API tests: the administrator's nonce and the public, cross-origin check (A6a, D-A3)."""
    print_section("Address Probe API Tests")
    print_info("Testing POST /users/address-probe (admin) and GET /auth/address-probe (public): {nonce, expires_at}, exactly {match}")
    print_info("Tests: Access-Control-Allow-Origin * through the CORSMiddleware, Cache-Control no-store, forged/expired/foreign nonces false, cookies ignored, another instance in process")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_address_probe_api.py", test_names)
    return run_command(cmd, "Address probe API tests", verbose=verbose)


def api_address_probe_image(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the address probe image tests: GET /auth/address-probe.png, 1x1 for this instance's nonce, 2x1 otherwise (H-55 v2)."""
    print_section("Address Probe Image API Tests")
    print_info("Testing GET /auth/address-probe.png (public): a PNG, 1x1 or 2x1, no-store, no session; its own module; outside the blocked list")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_address_probe_image.py", test_names)
    return run_command(cmd, "Address probe image API tests", verbose=verbose)


def api_api_docs(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the API documentation tests: our Swagger UI and ReDoc pages, pinned with SRI, off without the debug flag (H-55 R5)."""
    print_section("API Docs Tests")
    print_info("Testing /api/v1/docs, /api/v1/redoc and their start scripts; LIBREFOLIO_API_DOCS and test mode; main.py's wiring")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_api_docs.py", test_names)
    return run_command(cmd, "API docs tests", verbose=verbose)


def api_hosting_panel_routes(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the hosting panel's route tests: the six routes under the single tag Hosting panel, their bearer schemes and documented answers (H-61)."""
    print_section("Hosting Panel Routes")
    print_info("Testing: the real app's route table and OpenAPI document: tag, endpoints, operation ids, BackupPanelToken/WakeToken/PanelStatusToken, 401/404/429/503")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_hosting_panel_routes.py", test_names)
    return run_command(cmd, "Hosting panel route tests", verbose=verbose)


def api_panel_restore(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the hosting panel's restore route tests: /backup/panel/restore/* (H-62, contract L3 §5)."""
    print_section("Hosting Panel Restore API")
    print_info("Testing: the scope backup:restore (ticket only), the order of the refusals (credential, block, mode), upload, check, the panel's report (R1), confirm, restart, status, cancel, no echo; Needs B (Q1, Q2, Q4) apart")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_panel_restore_api.py", test_names)
    return run_command(cmd, "Hosting panel restore API tests", verbose=verbose)


def api_await_restore_mode(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the «awaiting restore» mode's API tests: refuse_when_awaiting_restore, its allowed set, ready/instance/wake/panel status (H-62, §6)."""
    print_section("Awaiting Restore Mode API")
    print_info("Testing: 423 instance_awaiting_restore for anyone outside the allowed set (pinned), mode in /system/ready and /system/instance, wake-sync awaiting_restore, both switches and R4, GET /panel/status mode and restore; Needs B (Q3) apart")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_await_restore_mode_api.py", test_names)
    return run_command(cmd, "Awaiting restore mode API tests", verbose=verbose)


def api_restore_interrupted(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the interrupted restore's API tests: refuse_when_restore_interrupted, its allowed set, instance/wake/panel status (B-33, H)."""
    print_section("Restore Interrupted API")
    print_info("Testing: 423 instance_restore_interrupted for anyone outside the allowed set (the mode's), the third router dependency, restore_interrupted in /system/instance, wake-sync restore_interrupted, GET /panel/status restore unreadable (D7), the panel's backup start 409 backup_restore_interrupted")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_restore_interrupted_api.py", test_names)
    return run_command(cmd, "Restore interrupted API tests", verbose=verbose)


def api_panel_status(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the hosting panel's status route tests: GET /panel/status (H-61, R1)."""
    print_section("Hosting Panel Status API")
    print_info("Testing: GET /api/v1/panel/status: off 404, its own 401, the four setup states with the expiry of a pending one only, no personal data, a blocked instance, OpenAPI")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_panel_status_api.py", test_names)
    return run_command(cmd, "Hosting panel status API tests", verbose=verbose)


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


def api_portfolio(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run portfolio API tests."""
    print_section("Portfolio API Tests")
    print_info("Testing POST /portfolio/report plus GET asset-history and lots endpoints")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_portfolio_api.py", test_names)
    return run_command(cmd, "Portfolio API tests", verbose=verbose)


def api_portfolio_wac(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run portfolio WAC API tests."""
    print_section("Portfolio WAC API Tests")
    print_info("Testing POST /api/v1/portfolio/wac endpoint (A1-A8)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_portfolio_wac.py", test_names)
    return run_command(cmd, "Portfolio WAC API tests", verbose=verbose)


def api_email(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the email API tests: GET /email/status, POST /email/test, POST /email/links, POST /email/password-reset and the email part of GET /system/instance, in-process."""
    print_section("Email Administration API Tests")
    print_info("Testing GET /email/status and POST /email/test: admin only, state/checks/budget/links without the SMTP configuration, the test email in the admin's language, 409/429/502/422; GET /system/instance email.available/links")
    print_info("Testing POST /email/links (admin, links from LIBREFOLIO_PUBLIC_URL alone, 409/422/429/502) and POST /email/password-reset (anonymous, the same 202 for everyone, limits per address/identifier/budget, the background work)")
    print_info("In-process: the real auth and email routers and the instance route on a private SQLite, SMTP and public URL variables by monkeypatch, a fake SMTP server on 127.0.0.1; the lane's backend is never called")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_email_api.py", test_names)
    return run_command(cmd, "Email administration API tests", verbose=verbose)


def api_email_verification(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the email verification API tests: POST /email/verification/confirm and POST /email/verification/resend, in-process."""
    print_section("Email Verification API Tests")
    print_info("Testing POST /email/verification/confirm (anonymous: 200 {username}, 400 TOKEN_INVALID with the token's status, 422) and POST /email/verification/resend (anonymous: 200 {language}, the login's 401/403, 409 without problem, 429 with Retry-After, 502, 422)")
    print_info("In-process: the real auth and email routers on a private SQLite, SMTP and public URL variables by monkeypatch, a fake SMTP server on 127.0.0.1; the lane's backend is never called")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_email_verification_api.py", test_names)
    return run_command(cmd, "Email verification API tests", verbose=verbose)


def api_email_verification_hooks(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the tests of the email-verification hooks in A's routes (lot E5b): register, login, users, settings, in-process."""
    print_section("Email Verification Hooks API Tests")
    print_info("Testing POST /auth/register (verification_required, 409 EMAIL_VERIFICATION_UNAVAILABLE), POST /auth/login (403 EMAIL_NOT_VERIFIED), GET/PATCH /users (holds_place, the limit), PATCH /settings/global/bulk (off → on needs an email with a link)")
    print_info("In-process: the real auth, users, settings and email routers on a private SQLite, SMTP and public URL variables by monkeypatch, a fake SMTP server on 127.0.0.1; the lane's backend is never called")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_email_verification_hooks_api.py", test_names)
    return run_command(cmd, "Email verification hooks API tests", verbose=verbose)


def api_email_change_notice(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """Run the tests of the email-change notice that A's PUT /auth/profile schedules (lot E4b, on A6e), in-process."""
    print_section("Email Change Notice API Tests")
    print_info("Testing PUT /auth/profile: an accepted email change answers as before (200, a new session cookie), then emails the old address, with nothing of the new address nor the username; nothing without a change of mailbox, on a refused change or with email off (an info line)")
    print_info("In-process: the real auth router on a private SQLite, SMTP variables by monkeypatch, a fake SMTP server on 127.0.0.1; the lane's backend is never called")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_email_change_notice_api.py", test_names)
    return run_command(cmd, "Email change notice API tests", verbose=verbose)


def _api_setup() -> bool:
    """Reseed the fixture data the API units assert against.

    The `services` category recreates the database empty (see services_all →
    db_create), so by the time this category runs in a full suite the fixture
    users seeded by `db populate` are gone. Tests that assert against real
    portfolio data (risk analytics) look up `e2e_test_user` and would fail with
    an opaque NoResultFound.
    """
    print_info("\n⚙️  Populating test database for API tests...")
    if db_populate(verbose=False, force=True):
        print_success("Test database populated\n")
        return True
    print_error("Failed to populate test database")
    print_warning("API tests needing fixture data (risk analytics) will fail")
    return False


#: The users the API units sign in as, seeded by ``db populate`` (``test_user_defs`` in
#: ``backend/test_scripts/test_db/populate_mock_data.py``).
API_FIXTURE_USERS = ("e2e_test_admin", "e2e_test_user")


def _api_fixture_users_missing() -> str | None:
    """Why one ``api`` action must reseed first: the lane's test database lacks a fixture user. None when it has them.

    The category's ``setup_needed`` (H-21, W-B54). It never writes the database file: opened ``mode=ro``, never
    created. On a WAL database SQLite may create the empty ``-wal``/``-shm`` companions, as any reader does; while
    the shared backend runs they exist already. A database that cannot be read counts as one to reseed.
    """
    db = get_test_db_path()
    if not db.is_file():
        return f"no test database at {db}"
    placeholders = ", ".join("?" * len(API_FIXTURE_USERS))
    try:
        with closing(sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True, timeout=5)) as conn:
            rows = conn.execute(f"SELECT username FROM users WHERE username IN ({placeholders})", API_FIXTURE_USERS).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            return f"the test database {db} cannot be read ({exc})"
        rows = []
    except sqlite3.Error as exc:
        return f"the test database {db} cannot be read ({exc})"
    found = {username for (username,) in rows}
    missing = [username for username in API_FIXTURE_USERS if username not in found]
    return f"the test database {db} has no fixture user {', '.join(missing)}" if missing else None


def api_test(verbose: bool = False) -> bool:
    """Run all API tests."""
    if _common.nothing_left_to_run("api"):
        return _common.consolidated_verdict("api")
    _common.run_category_setup("api")

    return _run_test_suite(
        suite_name="API Tests",
        tests=_get_category_tests_for_all("api", verbose),
        verbose=verbose,
        info_msgs=[
            "Testing REST API endpoints",
            "Note: Server will be automatically started/stopped by tests",
        ],
        combine_coverage=True,
        resume=_common._RESUME_MODE,
    )


def e2e_brim(verbose: bool = False, test_names: list = None) -> bool:
    """Run BRIM E2E tests."""
    print_section("E2E Test: BRIM Import Flow")
    print_info("Testing complete broker report import workflow")
    print_info("Tests: Upload → Parse → Asset Mapping → Duplicate Detection → Import")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_brim_e2e.py", test_names)
    return run_command(cmd, "BRIM E2E tests", verbose=verbose)


def e2e_backup_roundtrip(verbose: bool = False, test_names: list = None) -> bool:
    """Test the founder's acceptance of the instance backup: a populated instance backed up, restored on an empty one."""
    print_section("E2E: Backup and Restore Round Trip")
    print_info("Testing: jobs.run_backup, scripts/backup_cli.py restore --yes, then a start (pending-restore … restore-commit) in a fresh process")
    print_info("Tests: the same totals after the restore; an older backup upgraded; a newer one refused")
    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_backup_roundtrip.py", test_names)
    return run_command(cmd, "Backup round trip E2E tests", verbose=verbose)


def e2e_backup_roundtrip_l3(verbose: bool = False, test_names: list = None) -> bool:
    """Test the sealed nightly backup restored through the hosting panel: two real servers on Unix sockets (contract L3)."""
    print_section("E2E: Sealed Backup Restored by the Panel (L3)")
    print_info("Testing: POST /backup/panel/jobs sealed (L3-2), sealed.read_sealed/open_password, the panel's restore routes and LIBREFOLIO_AWAIT_RESTORE (H-62)")
    print_info("Tests: sealed backup → awaiting-restore instance → upload, stage, confirm, restart → committed in a new process → out of the mode, same totals")
    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_backup_roundtrip_l3.py", test_names)
    return run_command(cmd, "Backup round trip L3 E2E tests", verbose=verbose)


def e2e_test(verbose: bool = False) -> bool:
    """Run all E2E tests."""
    if _common.nothing_left_to_run("e2e"):
        return _common.consolidated_verdict("e2e")
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
        resume=_common._RESUME_MODE,
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
""",
        setup=_api_setup,
        # One action alone reseeds only when the fixture users are missing (H-21).
        setup_needed=_api_fixture_users_missing,
        # Earned, not assumed: 50 of the 51 units ran concurrently on one shared
        # backend across two full runs with 4 workers — 579 tests, zero reds —
        # before this line was written. They are scoped because each creates its
        # own user and addresses its own rows by id. The two that are not say so
        # below, each with the run that proved it.
        default_isolation="write-scoped",
    )
    add_test(
        api,
        "fx",
        api_fx,
        name="FX API",
        desc="Conversion, providers, pair sources; X-R65 422 date_out_of_range on manual rates; X-R75: POST /fx/providers/routes?replace=true keeps exactly the posted routes of each pair named (the MANUAL item alone leaves the pair manual), a refused replace (400, 422) changes nothing, without replace the upsert as before",
    )
    add_test(api, "fx-compress-errors", api_fx_compress_errors, name="FX Compress Errors", desc="_compress_convert_errors utility")
    add_test(api, "preview-cache", api_preview_cache, name="Preview Cache", desc="PreviewCache in uploads API")
    add_test(api, "fx-unit", api_fx_unit, name="FX API Unit", desc="Direct handler unit tests, no live server")
    add_test(api, "fx-sync", api_fx_sync, name="FX Sync API", desc="FX rate synchronization endpoints")
    # PURE: the handler runs in process with convert_bulk replaced by a double; no database, no server.
    add_test(api, "fx-convert-sampling", api_fx_convert_sampling, name="FX Convert Sampling", desc="Z-29fx: max_points, resolution and sample_like on POST /fx/currencies/convert: the step from the fill's first day, the bucket results, samples with resolution and sample_bounds, request_index, sample_reference 422s, signals reduced and aligned (O1), the calendar rolling return in the FX domain, the day budget", isolation="pure")
    add_test(api, "assets-price", api_assets_price, name="Assets Price API", desc="Bulk upsert, delete, query, sync; X-R65 422 date_out_of_range; X-R71 422 price_currency_mismatch")
    # Write-scoped (the category default): own user, own asset (deleted), rates only on AWG/TMT, a pair no other test uses.
    add_test(api, "period-changes", api_period_changes, name="Period Changes API", desc="MF-P2: login, base == quote 422, answer shape, and the Assets/FX pages' numbers from the price query and the conversions; MF-P2b: list caps, ≤ 5 distinct as_of, as_of ≥ 1900")
    add_test(api, "signal-catalogs", api_signal_catalogs, name="Signal Catalogs", desc="Static authenticated Asset/FX signal definitions")
    add_test(api, "asset-signals", api_asset_signals, name="Asset Signals", desc="Price-query legacy, signal-only, annotations and isolation")
    add_test(api, "fx-signals", api_fx_signals, name="FX Signals", desc="Combined conversion, grouped signals, identity/rates and legacy output")
    add_test(api, "signal-request-validation", api_signal_request_validation, name="Signal Request Validation", desc="Asset/FX signal request validation contracts")
    add_test(api, "signal-preview", api_signal_preview, name="Signal Preview", desc="Backend indicator compute on synthetic points (global chart preview)")
    add_test(api, "ai-export", api_ai_export, name="AI Export API", desc="Catalog, snapshots, authorization, and typed problems")
    add_test(
        api,
        "ai-export-unpriced-asset",
        api_ai_export_unpriced_asset,
        name="AI Export Unpriced Asset API",
        desc="E-AI503, E-23: POST /ai-export/snapshot with a held asset of any type and no stored price, or prices stored only before the period, is 200, not 503: the asset is listed without a price series, with its reason (and its last stored price)",
        # PURE: the real AI Export router runs in-process on a private SQLite file under tmp_path, with the real snapshot
        # service, portfolio report and price query; the portfolio caches are emptied around each test: the lane's backend
        # is never called.
        isolation="pure",
    )
    add_test(api, "tools", api_tools, name="Tools API", desc="Catalog, bulk compute, diagnostics, and authorization")
    add_test(api, "pac-planner-tool", api_pac_planner_tool, name="PAC Planner Tool API", desc="pac_allocator plan through the live compute endpoint")
    add_test(api, "risk", api_risk, name="Risk Analysis API", desc="Catalog, bulk query, isolation, and populated-DB analytics, and per-period asset eligibility")
    add_test(api, "assets-provider", api_assets_provider, name="Assets Provider API", desc="Provider assignment endpoints")
    add_test(
        api,
        "parametric-provider-semantics",
        api_parametric_provider_semantics,
        name="Parametric Provider Semantics",
        desc="What survives a provider removal and a switch away from a parametric provider",
    )
    add_test(api, "assets-metadata", api_assets_metadata, name="Assets Metadata API", desc="PATCH metadata, bulk read, refresh")
    add_test(api, "assets-events", api_assets_events, name="Assets Events API", desc="Bulk upsert, delete, query")
    add_test(api, "events-target-currency", api_events_target_currency, name="Events Target Currency", desc="FX conversion on events query (E.8)")
    add_test(api, "assets-crud", api_assets_crud, name="Assets CRUD API", desc="Create, list, filter, delete assets, and held-now flags in the list")
    add_test(api, "asset-merge", api_asset_merge, name="Asset Merge API", desc="POST /assets/merge: dry-run, execution, identifier union, refusals")
    add_test(api, "utilities", api_utilities, name="Utilities API", desc="Sectors, countries")
    add_test(
        api,
        "utilities-currency-suggest",
        api_utilities_currency_suggest,
        name="Utilities API: Currency Suggestion (E-19b1)",
        desc="GET /utilities/currencies/suggest: canonical, the one ISO code a stored value stands for (978, EURO -> EUR), the candidates of an ambiguous one (VED, VES), none for a subunit; public; value of 1 to 200 characters, else 422",
    )
    add_test(api, "system", api_system, name="System API", desc="parse_pipfile, deps, info (public or full), connection, instance, ready, route order")
    # Read-only on the lane (one anonymous GET); every case with a variable runs in-process on a private database.
    add_test(api, "instance-legal", api_instance_config_legal, name="Instance Configuration: Legal Links (A9)", desc="GET /system/instance legal {terms_url, privacy_url}: valid, unset, invalid (null, still 200), no secret; the schema and the OpenAPI document; live on the lane: both null")
    add_test(
        api,
        "system-wake",
        api_system_wake,
        name="System API Wake-up",
        desc="POST /system/wake-sync and LIBREFOLIO_WAKE_TOKEN(_FILE): wake_token() (variable or file, BOM and trailing line breaks dropped, variable wins, blank is unset, the panel token's rule value for value: anything but visible ASCII refused first, 31 characters refused, never the value, 32 taken, unreadable file); unset → 404 Not Found as a path that does not exist; unusable → 503 wake_unavailable and one error line naming the variable; missing or wrong token → 401 wake_unauthorized, WWW-Authenticate: Bearer; with it, run_due_jobs('wake') as a task, one at a time (token first, then 409 wake_in_progress until the run ends, a disconnect included, the run never cancelled); 200 application/json no-store streamed: a space at once, one per WAKE_KEEPALIVE_SECONDS, then WakeSyncResponse mirroring the RunReport, any status; a raising run → error, its class name only; started/finished/failed logged; D-W3 on the real scheduler: blocked, nothing past the switches, the run lock included; Z-11 (N71) on the real run_due_jobs: a worker that is not the leader answers ok with its jobs through the lock across processes, not_leader only without fcntl; OpenAPI (WakeToken, WakeSyncResponse, 401/404/409/503) and the composition; through the middleware stack in flight without presence, the first gzip chunk before the run ends; the token never in an answer or the log",
        # PURE: an app of the test holds the system router under /api/v1 (the middleware stack added where it is under
        # test), run_due_jobs is replaced on the wake module by a fake (the real one runs once, blocked, every collaborator
        # past its switches trapped) and the token variables are set with monkeypatch: no data directory, DB, server or
        # network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    # Write-scoped (the category default), no exclusive_because: on the lane's server the module only reads the status, as
    # e2e_test_user, whose login counters (which no unit asserts) are the one write; the chosen states (starting, running,
    # idle after a refreshed catch-up) run in-process, an app of the test holding the system router, get_current_user
    # overridden and this pytest process's own PRICE_REFRESH driven and reset by the test, never the lane server's.
    add_test(
        api,
        "system-price-refresh",
        api_system_price_refresh,
        name="System API Price Refresh",
        desc="Lot Z5, «Aggiornamento prezzi…»: GET /system/price-refresh → 401 without a session; any signed-in user (e2e_test_user) 200, exactly state/reason/job/since/last_finished_at/last_refreshed with a valid state, whatever the lane's scheduler does; in-process: idle (all null, not refreshed), starting for wake with since, running for return with its job, idle after a refreshed catch-up with last_finished_at, datetimes ISO 8601 UTC; PriceRefreshResponse six fields, literals enforced (tick refused); OpenAPI, tag System, the 200 schema",
    )
    # H CP6: the block is set in the test process only (ASGI app + monkeypatch); the lane's backend stays unblocked, and
    # each test registers and deletes its own user, so the category's write-scoped holds.
    add_test(api, "instance-block", api_instance_block, name="Instance Block", desc="423 on a blocked instance but the allowed routes, 401 first for anonymous callers, GET /system/block, route guard")
    add_test(api, "backup", api_backup, name="Backup API", desc="Instance backup jobs (admin only): start, poll, download, delete, busy, job ids, removed placeholders; route order (C2)")
    add_test(
        api,
        "backup-instance-errors",
        api_backup_instance_errors,
        name="Backup API Start Errors",
        desc="POST /backup/instance when the run cannot start: a link or a file in place of backups/ or backups/.jobs (BackupPathError) → 500 backup_folder_unusable, any other OSError → 500 backup_failed, another run → 409 backup_busy, never the data directory's path or the system's words in the answer; a run that starts → 202 with its first state",
        # PURE: an app of the test holds instance_router, require_admin overridden and jobs.start_backup replaced: no
        # data directory, DB, server or network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "backup-panel",
        api_backup_panel,
        name="Backup API Panel Token",
        desc="The hosting panel's backup routes (/backup/panel/jobs) and LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN(_FILE): backup_download_token() (variable or file, BOM and trailing line breaks dropped, variable wins, blank is unset, anything but visible ASCII refused first, 31 characters refused, never the value, 32 taken, unreadable file); unset → 404 Not Found as a path that does not exist; unusable → 503 backup_panel_unavailable and one error line naming the variable; missing or wrong token → 401 backup_panel_unauthorized, WWW-Authenticate: Bearer; with it, the panel's own jobs only (another origin answers as no job, archive never read, never deleted), the archive's exact bytes with no-store, the shared start errors; an administrator still sees every job; the token never in an answer or the log",
        # PURE: an app of the test holds backup_router under /api/v1 (require_admin overridden where called) and the four
        # functions of jobs replaced by a fake under tmp_path; the token variables are set with monkeypatch: no data
        # directory, DB, server or network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "backup-restore",
        api_backup_restore,
        name="Backup API Restore Check",
        desc="The check of an archive before a restore (/backup/restore, lot B2b): PUT /upload as a raw body (201 with its id and size, 0600, written in 1 MiB pieces off the event loop; LIBREFOLIO_BACKUP_MAX_UPLOAD_MB → 413 backup_too_large with limit_mb on the Content-Length before anything is created or at the piece past it with no partial left, none self-hosted, 500 managed, 503 when unreadable; 507 without room; 400 empty or incomplete; a newer upload replaces the older but the one a running check reads; a link or a file for .restore → 500 restore_folder_unusable); POST /stage → 202, GET → done with the report mapped from staging (same, upgrade with its migrations and warnings, no administrator) or failed with its code, the upload removed; 404 unknown ids, 422 a malformed upload id; one check at a time (409 restore_busy, 409 restore_stage_running); the end written before the lock is let go, a poll as a check ends never interrupted; restore_interrupted when nobody holds the lock; prune (ended checks after 24 h, a check left running ended, unrecorded uploads and copies only while no check runs, never through a link; a start with a link in place of a folder → 500, nothing pruned); done_bytes/total_bytes follow the unpacking; 500 backup_upload_failed on any other write failure; administrators only (403); not allowed when blocked; OpenAPI octet-stream; backup_max_upload_mb(); B-35: LIBREFOLIO_BACKUP_MAX_RESTORE_MB caps what an archive declares unpacked (whole MiB, only above refused; archives of an exact declared size, the head data directory and a file of zeros): over it the check ends failed unpacked_too_large with a 200 GET, nothing unpacked (0/0 bytes), the stage removed and the upload consumed, at or under it checked as before; managed unset = 8 × the upload limit (1 MB → 8 MiB: a byte past refused), an explicit 0 lifts it; unreadable (the variable, or managed through the upload limit's variable or H's table entry) → 503 backup_restore_unavailable, one error naming the variable, no value or path in the answer, no check started, the upload kept and startable once readable; OpenAPI 503 and RestoreErrorCode unpacked_too_large",
        # PURE: an app of the test holds backup_router under /api/v1 (get_current_user overridden), the data directory
        # of restore.py and restore_jobs.py is under tmp_path and the process's own one is a folder of the test that
        # must stay absent; the checks run in fake threads, on real archives built under tmp_path (two alembic upgrades
        # of new databases, in processes of their own, as test_backup_staging.py makes them): no lane data directory,
        # DB, server or network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "backup-secure",
        api_backup_secure,
        name="Backup API Secure Backup",
        desc="The secure backup through the API (lot B4): GET /backup/instance/options (the archive rules, admins only); POST /backup/instance with a password (password_too_weak 400 with its rules and no job; an .lfbk, encrypted; no body, {} or null a zip; a 422 never echoing the password); the panel never encrypting; PUT /backup/restore/upload kind; POST /backup/restore/stage with a password (password_required, wrong_password 400 keeping the upload, envelope_damaged 400, envelope_unsupported 409, a zip ignoring it); the report's encrypted and secret counts",
        # Write-scoped (the category default): SECURE-001 to 005 start real backups on the lane's server, as an
        # administrator the module registers and deletes; the others run in an app of the test under tmp_path.
        exclusive_because="starts real backups on the lane's server, which hold its one backup run lock: api backup, run beside it, would meet 409 backup_busy",
    )
    add_test(
        api,
        "no-echo-route",
        api_no_echo_route,
        name="422 Without Echo",
        desc="NoInputEchoRoute (api/no_echo.py): a 422 keeps type, loc, msg and ctx and never repeats the body (a missing field, an extra field, a value too long, beside a password); a valid body and an HTTPException pass unchanged; the plugin settings' router and the backup routers that receive a password use the one shared class",
        # PURE: an app of the test, in this process; the routers are only imported. No DB, no server reached.
        isolation="pure",
    )
    add_test(
        api,
        "backup-restore-apply",
        api_backup_restore_apply,
        name="Backup API Restore Confirmation",
        desc="The restore confirmed through /backup/restore (lot B3): POST /stage/{id}/confirm → 202 pending, .restore/restore.json 0600 with the report's backup and action, confirmed_by the administrator, the copy kept; every refusal (404 restore_stage_not_found, 409 restore_stage_running / restore_not_restorable / restore_stage_outdated / restore_already_pending, 410 restore_stage_expired, 500 restore_folder_unusable for a .restore link or file; checks/ or stage/ a link → 404), nothing written; GET /status none (nothing created), each phase, links never followed; DELETE /pending 204 or 404 restore_not_pending without creating the lock; POST /restart 202 then one SIGTERM to the server's root process through restart.send_signal after the answer, 409 without a pending restore; the copy of an active restore: DELETE /stage 409 restore_pending, prune keeps it however old (the CLI's unrecorded copy too); administrators only (403); none of the routes allowed when blocked; OpenAPI; lot B5c: the restart's one-time ticket (43 characters, only its hash on disk, 0600, no-store, replaced by a second restart, none on a 409), GET /outcome without a session, the ticket in X-Restore-Ticket only, every invalid ticket the same 404 restore_outcome_not_found, the outcome's three fields, read again until it expires, a final outcome included (decision N53), never logged, answered on a blocked instance (H's allow-list entry); B-17: DELETE /pending drops the copy and its check record, and the ticket; B-32: a state the file system cannot read (os.open refusing restore.json alone with EACCES or EIO, or its mode 000 unless root): GET /status, DELETE /pending, POST /restart and the confirmation of a fresh check 500 restore_state_unreadable, the reader's error logged, no path or system words in the answer, nothing written (state, copy, check record, ticket untouched; no ticket issued, no restart), the restore still pending once readable; GET /outcome still the one 404, its ticket kept (guard); OpenAPI names restore_state_unreadable in the four 500s; B-41: a ticket that does not open the outcome never makes it open the state file nor log that it cannot (every case of (i) the ticket alone decides, the state made unreadable)",
        # PURE: an app of the test holds backup_router under /api/v1 (get_current_user overridden), the data directory
        # of restore.py, restore_jobs.py and apply.py is under tmp_path and the process's own one is a folder of the
        # test that must stay absent; restart.send_signal and os.kill as restart sees them record and never signal;
        # real archives built under tmp_path as test_backup_staging.py builds them: no lane data directory, DB, server
        # or network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(api, "transactions", api_transactions, name="Transactions API", desc="Bulk create, query, patch, delete")
    add_test(api, "transfer-promotion", api_transfer_promotion, name="Transfer Promotion", desc="DEPOSIT/WITHDRAWAL → TRANSFER")
    add_test(api, "transactions-validate", api_transactions_validate, name="Transactions Validate", desc="POST /transactions/validate dry-run")
    add_test(api, "tx-balance-walk", api_tx_balance_walk, name="TX Balance Walk", desc="Same-day ordering, cascade, end-of-day")
    add_test(api, "events-suggest", api_events_suggest, name="Events Suggest", desc="Candidate events within tolerance")
    add_test(api, "batch-split-promote", api_batch_split_promote, name="Batch Split/Promote", desc="Split/promote in unified batch + suggest")
    add_test(api, "transactions-wac", api_transactions_wac_inline, name="WAC Cost Basis", desc="WAC inline validate/commit (P16-P28)")
    add_test(api, "assets-patch-fields", api_assets_patch_fields, name="Assets Patch Fields", desc="PATCH /assets/{id} field-level updates")
    add_test(api, "ohlc-sentinel", api_ohlc_sentinel, name="OHLC Sentinel", desc="F.4 merge on POST /assets/prices (N92): null or absent keeps the stored value, 'clear' empties it, a number writes it; -1, any other text and a close not above 0 refused with 422, nothing written")
    add_test(api, "current-price-persistence", api_current_price_persistence, name="Current Price Persistence", desc="/current endpoint OHLC upsert")
    add_test(api, "prices-currency-coherence", api_prices_currency_coherence, name="Prices Currency Coherence", desc="Hard reject on currency mismatch; X-R71: 422 price_currency_mismatch (items per asset at fault, count), the whole upload refused, no asset written; an unknown asset still reported")
    add_test(api, "asset-currency-change", api_asset_currency_change, name="Asset Currency Change", desc="409 blocked, wipe + retry")
    add_test(api, "asset-prices-export", api_asset_prices_export, name="Asset Prices Export", desc="CSV/JSON export + round-trip")
    add_test(api, "prices-sync-delta", api_prices_sync_delta, name="Prices Sync Delta", desc="changed_points payload")
    add_test(api, "market-data-wipe", api_market_data_wipe, name="Market Data Wipe", desc="Summary + wipe (Policy D)")
    add_test(api, "backup-export-extras", api_backup_export_extras, name="Backup Export Extras", desc="Events + FX rates export")
    add_test(api, "uploads-serve-file", api_uploads_serve_file, name="Uploads Serve File", desc="Preview, download, MIME")
    add_test(api, "brokers", api_brokers, name="Brokers API", desc="CRUD broker endpoints")
    add_test(api, "brim", api_brim, name="BRIM API", desc="Upload, parse, import flow")
    add_test(api, "brim-scalable", api_brim_scalable, name="BRIM Scalable API", desc="Scalable broker + overnight account: transfers merged and re-imported as duplicates, one-broker cash")
    add_test(api, "auth", api_auth, name="Auth API", desc="Register, login, logout, me", exclusive_because="rewrites global_settings.registration_mode, one row shared by every user: a concurrent unit would register against whatever value this one left behind")
    # Write-scoped, no exclusive_because: every case that needs another registration mode, an accounts variable or a
    # user limit runs in-process on a private database (the lane's server is another process, its row is shared); on the
    # lane's server only cases that leave the mode alone, each with its own account and tokens, deleted afterwards.
    add_test(api, "registration", api_registration, name="Registration API", desc="Register with invitations by mode, tokens/inspect, password-reset, instance accounts block, registration_mode locked by the variable")
    # Write-scoped, no exclusive_because: the mode, the limit, the public and billing URLs and «the last administrator» are
    # tested in-process on private databases; on the lane's server each case acts only on accounts it registers (its
    # administrator promoted through user_service) and on their tokens, never counts the lane, and deletes them afterwards.
    add_test(api, "admin-setup", api_admin_setup, name="Initial Administrator Setup API", desc="POST /auth/setup (password rules first, TOKEN_INVALID, the login's cookie), tokens/inspect admin_setup")
    add_test(
        api,
        "validation-errors",
        api_validation_errors,
        name="Validation Errors API",
        desc="A-35: every 422 keeps loc, msg, type and ctx and drops input, so no password or token comes back (login, register, change-password, password-reset, setup, tokens/inspect, profile, email resend); a non-finite number (1E+400, NaN) on a Decimal is a readable 422, not a 500; the OpenAPI schema unchanged",
    )
    add_test(
        api,
        "login-throttle",
        api_login_throttle,
        name="Login Throttle API",
        desc="F15 (A8a): 429 TOO_MANY_ATTEMPTS with an exact Retry-After before any password check, the same for an unknown identifier; per address; change of password and of address under the account's username; the switch; GET /security/checks admin-only, every check once, no secret in the body",
        # PURE: in-process apps on private SQLite files under tmp_path, limiters of their own on a fake clock; no lane DB,
        # no server.
        isolation="pure",
    )
    add_test(
        api,
        "username-rules",
        api_username_rules,
        name="Username Rules API",
        desc="A-21a over HTTP: register and profile refuse a new username with an @ (400 USERNAME_INVALID) and an address that is a legacy username (400 Email already registered); the sign-in reads an address first, then the exact legacy name (E's point c, both orders)",
        # PURE: in-process apps on private SQLite files under tmp_path, legacy accounts written as rows, limiters of their
        # own; no lane DB, no server reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "whats-new",
        api_whats_new,
        name="What's New API",
        desc="C-54 over HTTP: user.whats_new, {since, release} or null, in the answers of register, login, /auth/me and setup — a fresh account null, NULL or an older release pending at every /auth/me without marking it, LIBREFOLIO_DISABLE_WHATS_NEW null —; POST /auth/whats-new/seen 401 without a session, 204 writing the server's running release (never a client's), nobody else's, idempotent",
        # PURE: in-process apps on private SQLite files under tmp_path, the running version patched in this process,
        # accounts written as rows, limiters of their own; no lane DB, no server reached (the api category still starts
        # the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "security-checks",
        api_security_checks,
        name="Security Checks API",
        desc="GET /api/v1/security/checks on the lane: an administrator sees accounts.login_limit as a warning (the lane's server runs with LIBREFOLIO_LOGIN_LIMIT=off) and the platform checks; a member 403, anonymous 401",
    )
    # Write-scoped, no exclusive_because: a waiting administrator exists only in-process on private databases; on the
    # lane's server only refusals that write nothing.
    add_test(api, "users-admin", api_users_admin, name="Users Admin API", desc="Invitations, accounts and usage, PATCH with the last-admin and limit guards, reset links, sessions revoke, onboarding reset, token-free logs")
    add_test(api, "profile", api_profile, name="Profile API", desc="Username/email update")
    add_test(api, "settings", api_settings, name="Settings API", desc="User and global settings")
    add_test(api, "settings-currency-strict", api_settings_currency_strict, name="Settings Currency Strict API", desc="E-19a: base_currency strict on PUT /settings/user and the welcome flow; the 422 names the ISO code")
    add_test(
        api,
        "plugin-settings",
        api_plugin_settings,
        name="Plugin Settings API",
        desc="Catalogue and roles, write-only secrets, all-or-nothing 422 with every item, no input echo in FastAPI's 422, user isolation, delivery to mockprov, CASCADE and SET NULL",
        # The user fields are written by accounts the module registers and deletes; the system fields are not scopable.
        exclusive_because="writes and clears the instance-wide plugin settings of mockprov, whose values make the fingerprint in the cache keys of every mockprov call: a concurrent unit would see its mockprov values change and miss its cache entries mid-test",
    )
    add_test(
        api,
        "cache-admin",
        api_cache_admin,
        name="Cache Admin API",
        desc="Cache status/clear endpoints",
        exclusive_because="clears the process-wide cache registry (clear-all and clear/{name}): entries other units populated and may assert on (fx_provider_responses, search_results, upload_metadata) would vanish mid-run",
    )
    # Write-scoped (the category default), no exclusive_because: on the lane's server the module only reads the scheduler's
    # state and log, with the users it registers; the cases that need a chosen scheduler_state.json or scheduler log (lot
    # Z7c-2, SAPI-010..014) run in-process on the test's own tmp_path, never on the lane's files.
    add_test(api, "scheduler", api_scheduler, name="Scheduler API", desc="Scheduler state/log endpoints, admin-only auth; lot Z7b's deferred items, retry_at and failure backoff passed through, files and entries written before it at the defaults")
    add_test(api, "uploads", api_uploads, name="Uploads API", desc="Upload, list, download, delete")
    add_test(api, "broker-access", api_broker_access, name="Broker Access API", desc="Access management, roles")
    add_test(api, "account-deletion", api_account_deletion, name="Account Deletion API", desc="Last-owner rule on every broker of a deleted account, files after commit")
    # The category's write-scoped holds: each test registers its own two users, reads only their rows and deletes them;
    # a password change ends the sessions of that account alone.
    add_test(api, "session-revocation", api_session_revocation, name="Session Revocation API", desc="Password change: version +1, the device's cookie re-issued, other sessions 401, refusals end nothing; A-27: a password or address change kills the live reset links (REVOKE-003…007)")
    # Write-scoped (the category default), no exclusive_because: a nonce is stateless, nothing is stored and no setting or
    # global row is written; the one write is the login counters of e2e_test_admin / e2e_test_user, which no unit asserts.
    # The instance key is switched in this process only (monkeypatch), never while the lane's server is asked.
    add_test(api, "address-probe", api_address_probe, name="Address Probe API", desc="Admin nonce 401/403/200, public {match} with ACAO * and no-store, Origin from elsewhere through the CORSMiddleware, forged/expired/foreign nonces false, cookies ignored, another instance in process")
    add_test(
        api,
        "address-probe-image",
        api_address_probe_image,
        name="Address Probe Image API",
        desc="H-55 v2: GET /auth/address-probe.png, a valid PNG 1x1 for a nonce this instance issued, 2x1 for forged, foreign, expired, empty, missing or too long, same status and type, no-store, no session; in address_probe_image.py, not auth.py; not allowed when blocked; the JSON probe unchanged",
    )
    add_test(
        api,
        "api-docs",
        api_api_docs,
        name="API Docs",
        desc="H-55 R5: /api/v1/docs, /api/v1/redoc and openapi.json only with LIBREFOLIO_API_DOCS or test mode (404 otherwise, Docker included); our pages, no inline script, the libraries from jsDelivr at an exact version with SRI and crossorigin, the start scripts served by the instance, out of the schema; main.py wiring; app.openapi() with openapi_url None",
        isolation="pure",
    )
    add_test(
        api,
        "hosting-panel-routes",
        api_hosting_panel_routes,
        name="Hosting Panel Routes",
        desc="H-61: the four backup panel routes, the wake-up and the status route carry the single tag Hosting panel, keep their endpoints and operation ids, ask for their own bearer scheme and document 429 beside 401, 404 and 503",
        isolation="pure",
    )
    add_test(
        api,
        "panel-status",
        api_panel_status,
        name="Hosting Panel Status API",
        desc="H-61 R1: GET /panel/status off 404 without a token, panel_status_unauthorized, the four states of the initial administrator's setup with the expiry of a pending one only, no personal data, answered on a blocked instance, its OpenAPI schema",
        isolation="pure",
    )
    add_test(
        api,
        "panel-restore",
        api_panel_restore,
        name="Hosting Panel Restore API",
        desc="H-62 (L3 §5): /backup/panel/restore/* with the ticket-only scope backup:restore: 404 without keys, 401 backup_restore_unauthorized to any L1 token (counted), wrong scope, replay, 429, 503 backup_restore_unavailable, then 423 instance_blocked, then 409 restore_mode_required, the same in every state; .lfbk only (400 restore_envelope_required), 413, R3 slow body; wrong_password keeps the upload; PanelRestoreStageReport (20 fields, administrators_count, no portfolio data); confirm via panel with the kid logged, restart once after the answer, status, cancel; no echo of the password; Needs B Q1/Q2/Q4 apart",
        # PURE: the app of main.py in this process (ASGI), the switches and the panel's variables by monkeypatch, the data
        # directory under tmp_path, the database session a stand-in that fails if reached, restart recorded, fake
        # threads; the archives from test_backup_staging.py's alembic databases under tmp_path: no lane server, DB or
        # network is reached (the api category still starts the lane's backend around it).
        isolation="pure",
    )
    add_test(
        api,
        "await-restore-mode",
        api_await_restore_mode,
        name="Awaiting Restore Mode API",
        desc="H-62 (L3 §6): LIBREFOLIO_AWAIT_RESTORE → 423 instance_awaiting_restore for anyone on every /api/v1 route but ALLOWED_WHEN_AWAITING_RESTORE (pinned by name and route), registration, setup, login and me included; the dependency right after refuse_when_blocked on every route; ready and instance say mode; wake-sync awaiting_restore with nothing past the switches; both switches 423; R4 the block at the first request; GET /panel/status mode and restore, an unreadable state as restore unreadable with its reason (D7); Needs B Q3 apart",
        # PURE: the app of main.py in this process (ASGI), every request's session on a private SQLite file under
        # tmp_path, the switches by monkeypatch, the data directory under tmp_path: the lane's backend and DB are never
        # reached.
        isolation="pure",
    )
    add_test(
        api,
        "restore-interrupted",
        api_restore_interrupted,
        name="Restore Interrupted API",
        desc="B-33 (H, 22/10): while restore_guard.restore_interrupted() every /api/v1 route but ALLOWED_WHEN_RESTORE_INTERRUPTED (= ALLOWED_WHEN_AWAITING_RESTORE, pinned by name and route) answers 423 instance_restore_interrupted to anyone, login, registration, setup, me and data included; refuse_when_restore_interrupted the third router dependency after block and mode; /system/instance restore_interrupted; wake-sync restore_interrupted with nothing past the switches; GET /panel/status still allowed (restore unreadable with its reason, D7); the panel's backup start 409 backup_restore_interrupted after its credential (D7), its poll, download and delete allowed",
        # PURE: the app of main.py in this process (ASGI), every request's session on a private SQLite file under
        # tmp_path, the interruption and the switches by monkeypatch: the lane's backend and DB are never reached.
        isolation="pure",
    )
    add_test(api, "broker-multiuser", api_broker_multiuser, name="Broker Multi-User", desc="Role-based permissions")
    add_test(api, "users-search", api_users_search, name="User Search API", desc="User search, share validation")
    add_test(api, "portfolio", api_portfolio, name="Portfolio API", desc="Summary, history, asset-history, FIFO lots endpoints")
    add_test(api, "portfolio-wac", api_portfolio_wac, name="Portfolio WAC API", desc="POST /portfolio/wac endpoint (A1-A8)")
    add_test(
        api,
        "email",
        api_email,
        name="Email Administration API",
        desc="GET /email/status (admin: off/ready/invalid, three checks, hourly budget, links from LIBREFOLIO_PUBLIC_URL, never the SMTP configuration) and POST /email/test (to the admin's own address in their language; 409 off or unusable, 429 with Retry-After, 502 with the SMTP code, 422 not one address; no secret in an answer); POST /email/links (admin: invite/reset link built from LIBREFOLIO_PUBLIC_URL alone, never the request; 409 email/links/token, 409 an inactive account's reset link, 422 recipient, 429, 502; token never logged); POST /email/password-reset (anonymous, open as shipped since lot E4: same 202 for every identifier, 409 without the problem, 429 per address (an IPv6 client by its /64, a mapped IPv4 as the IPv4)/identifier/budget, the background work emails a live link, makes nothing when the configuration went away, revokes a link it could not send and never raises; a client without an address is limited per identifier only); a public URL no link can start from is invalid on every route; on a blocked instance sending refuses (409 INSTANCE_BLOCKED) and /system/instance offers no email; GET /system/instance email.available/links (public, never the configuration nor the public URL, read off the event loop, optional in the OpenAPI); forgot password behind a reverse proxy LibreFolio does not trust, on a local address (172.17.0.1, fd00::2; X-Forwarded-For, Forwarded or X-Real-IP), no count per address, while a public client's own forwarding header or a LAN client without one is still counted (E-13, N70)",
        # PURE: the real auth and email routers and the instance route run in-process on a private SQLite file under tmp_path, the
        # SMTP and LIBREFOLIO_PUBLIC_URL variables are set with monkeypatch in this process, the limiters are private on a fake clock
        # and the fake SMTP server listens on 127.0.0.1: the lane's backend is never called.
        isolation="pure",
    )
    add_test(
        api,
        "email-verification",
        api_email_verification,
        name="Email Verification API",
        desc="POST /email/verification/confirm (anonymous, no cookie set: 200 {username} and the account signs in; 400 TOKEN_INVALID with expired/consumed/revoked/unknown, the hold refused as revoked and left live, a link emailed to another address revoked; 422 body) and POST /email/verification/resend (anonymous: 200 {language} and the verification email; 401 INVALID_CREDENTIALS (coded: any other 401 is the block's) and 403 byte for byte the login's; 409 NOT_NEEDED, EMAIL_UNAVAILABLE and EMAIL_LINKS_UNAVAILABLE without problem, USER_LIMIT_REACHED; 429 with Retry-After per address before the password, per account, per recipient mailbox, budget; 502 then resend at once; 422; an IPv6 /64 is one client, no address no count; accounts before the configuration); no token, password, identifier or address in the logs; the resend behind a reverse proxy LibreFolio does not trust, on a local address (172.17.0.1, fd00::2; X-Forwarded-For, Forwarded or X-Real-IP), no count per address, while a public client's own forwarding header or a LAN client without one is still counted (E-13, N70)",
        # PURE: the real auth and email routers run in-process on a private SQLite file under tmp_path, the SMTP, public URL,
        # block and user-limit variables are set with monkeypatch in this process, the limiters are private on a fake clock
        # and the fake SMTP server listens on 127.0.0.1: the lane's backend is never called.
        isolation="pure",
    )
    add_test(
        api,
        "email-verification-hooks",
        api_email_verification_hooks,
        name="Email Verification Hooks API",
        desc="With require_email_verification on: register 201 verification_required + inactive + the email from LIBREFOLIO_PUBLIC_URL, login 403 EMAIL_NOT_VERIFIED (wrong password the 401 of an unknown account), resend, click, login 200; the first account never waits; an invited one waits and spends its invitation; no email with a link → 409 EMAIL_VERIFICATION_UNAVAILABLE, nothing created, the invitation live; option off as before. A waiting account takes a place while its link is live (GET /users usage, holds_place, a registration refused when full), none once expired; PATCH /users reactivation on a full instance accepted while the link is live, refused once expired, the old link then revoked; PATCH is_active false on a waiting account ends the wait (its links revoked, its place freed, holds_place false); the PATCH answer and GET /users carry holds_place, true while the link is live and false once it expired; past LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS emails (20 by default; one count for registrations, resend and forgot password) from one client address, or with the instance's budget spent, the account waits without its email and the answer says verification_retry_after_seconds; a variable that cannot be used turns email off (register 409). Settings bulk: off → on 409 without email (nothing saved), 200 with email; on again or off always saved. The registration emails behind a reverse proxy LibreFolio does not trust, on a local address (172.17.0.1, fd00::2; X-Forwarded-For, Forwarded or X-Real-IP), no count per address, while a public client's own forwarding header or a LAN client without one is still counted (E-13, N70)",
        # PURE: the real auth, users, settings and email routers run in-process on a private SQLite file under tmp_path, the
        # option set in that file only, the SMTP, public URL and user-limit variables set with monkeypatch in this process,
        # the limiters private on a fake clock, the fake SMTP server on 127.0.0.1: the lane's backend is never called.
        isolation="pure",
    )
    add_test(
        api,
        "email-change-notice",
        api_email_change_notice,
        name="Email Change Notice API",
        desc="PUT /auth/profile (lot E4b, on A6e): an email change with the right current password answers as before (200, the new address, a new session cookie that signs in), then emails the old address only, in the account's language, with nothing of the new address nor the username, one budget unit; the work queued once, after the complete answer, with the account's id, both addresses and the request's own engine; nothing for a username-only change, the stored address sent again, an empty body or the same mailbox in other letters; email off: the same answer and an info line; a refused change (no or wrong current password, the address taken) sends nothing; the old address refused by the SMTP server: the answer unchanged and a warning; past 3 notices in the hour for the account, the change still answers 200 with a new cookie and no notice goes; E's log lines name neither address",
        # PURE: the real auth router runs in-process on a private SQLite file under tmp_path, the SMTP variables are set with
        # monkeypatch in this process, the hourly budget is private on a fake clock and the fake SMTP server listens on
        # 127.0.0.1: the lane's backend is never called.
        isolation="pure",
    )
    add_test(
        api,
        "http-compression",
        api_http_compression,
        name="HTTP Compression",
        desc="GZip Content-Encoding/Vary, immutable assets, 304/206, binaries untouched",
        # GETs on public resources and on the static build; the one write is the
        # throwaway user the SSE check needs for a session, deleted before it returns.
        isolation="write-scoped",
    )
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
""",
    )
    add_test(e2e, "search-to-prices", search2prices_test, name="Search to Prices", desc="Full asset lifecycle flow", prereq="Database created", tests="Search → Create → Assign → Metadata → Prices")
    add_test(e2e, "brim-e2e", e2e_brim, name="BRIM E2E", desc="Test complete BRIM import flow", prereq="Database created", tests="Upload → Parse → Asset Mapping → Import")
    add_test(
        e2e,
        "backup-roundtrip",
        e2e_backup_roundtrip,
        name="Backup Round Trip",
        desc="The founder's acceptance of F01: a populated instance (populate_mock_data in a data directory of the test, files of its own, a first start) backed up with jobs.run_backup, restored on an empty instance with backup_cli.py restore --yes, then a start in a fresh process (pending-restore … restore-commit): the same rows, files and portfolio reports of the official engine for every account with a broker (computed back to back), committed; an older backup upgraded through the check and committed at the head with the report's rows; a newer one refused (revision_unknown), the target untouched",
        tests="Populate → Backup → Restore --yes → Start → Same totals",
        # PURE: the source, the target and the archives are data directories under tmp_path, made by child processes in
        # test mode pointed at them (populate, alembic, the start); the lane's data directory, database and server are
        # never read nor written (the shared conftest's session fixture aside, as for every pure unit).
        isolation="pure",
    )
    add_test(
        e2e,
        "backup-roundtrip-l3",
        e2e_backup_roundtrip_l3,
        name="Backup Round Trip L3",
        desc="Contract L3 (lot B5): a populated instance served with LIBREFOLIO_BACKUP_RECIPIENTS makes a sealed backup for the hosting panel (a backup ticket): a .tar without the instance key, its download the job's SHA-256, read with read_sealed, its password opened by the test identity and checked against the envelope; an empty instance in LIBREFOLIO_AWAIT_RESTORE (the source's instance key) answers mode awaiting_restore, 423 instance_awaiting_restore, 409 backup_awaiting_restore; the panel uploads the envelope, checks it (R1: no administrators, differences or tables), confirms, restarts; a new process commits it; out of the mode the target has the source's rows, files, ledger totals and reports, and its administrator signs in; a backup ticket never opens the restore routes, and out of the mode they answer 409 restore_mode_required. RED until H-62",
        tests="Sealed backup → Await restore → Upload, Stage, Confirm, Restart → Committed → Same totals",
        # PURE: every data directory and archive under tmp_path, every server a child uvicorn of the test on a Unix socket
        # under /tmp (never a TCP port), in test mode on its own data directory; the lane's data directory, database and
        # server are never read nor written.
        isolation="pure",
    )
    add_test(e2e, "all", e2e_test, test_names=False, name="All E2E Tests", desc="Run all E2E tests")
    registry["e2e"] = e2e
