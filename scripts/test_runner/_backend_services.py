"""
Backend service tests: FX conversion, asset source, provider registry, transactions, etc.
"""

from scripts.cli_base import pipenv_prefix

from . import _common
from ._backend_db import db_create
from ._common import (
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

AI_EXPORT_SERVICE_TEST_PATHS = (
    "backend/test_scripts/test_services/test_ai_export_component_runtime.py",
    "backend/test_scripts/test_services/test_ai_export_components_asset.py",
    "backend/test_scripts/test_services/test_ai_export_components_asset_fx_integration.py",
    "backend/test_scripts/test_services/test_ai_export_components_broker_adequacy.py",
    "backend/test_scripts/test_services/test_ai_export_components_drawdown_context.py",
    "backend/test_scripts/test_services/test_ai_export_components_fx.py",
    "backend/test_scripts/test_services/test_ai_export_components_portfolio_broker_financial.py",
    "backend/test_scripts/test_services/test_ai_export_components_portfolio_broker_integration.py",
    "backend/test_scripts/test_services/test_ai_export_components_portfolio_income.py",
    "backend/test_scripts/test_services/test_ai_export_components_technical.py",
    "backend/test_scripts/test_services/test_ai_export_composer.py",
    "backend/test_scripts/test_services/test_ai_export_dataset_analysis_catalogs.py",
    "backend/test_scripts/test_services/test_ai_export_runtime_service.py",
    "backend/test_scripts/test_services/test_ai_export_telemetry.py",
    "backend/test_scripts/test_services/test_ai_export_temporal.py",
)

RISK_SERVICE_TEST_PATHS = (
    "backend/test_scripts/test_services/test_quantlib_smoke.py",
    "backend/test_scripts/test_services/test_series_preparation.py",
    "backend/test_scripts/test_services/test_risk_metrics.py",
    "backend/test_scripts/test_services/test_risk_registry.py",
    "backend/test_scripts/test_services/test_risk_signal_plugins.py",
    "backend/test_scripts/test_services/test_risk_service.py",
    "backend/test_scripts/test_services/test_risk_scenario_catalog.py",
    "backend/test_scripts/test_services/test_risk_analytics.py",
    "backend/test_scripts/test_services/test_risk_simulation.py",
    "backend/test_scripts/test_services/test_risk_optimization.py",
    "backend/test_scripts/test_services/test_risk_spawn_worker.py",
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


def services_quantlib_runtime(verbose: bool = False, test_names: list = None) -> bool:
    """Smoke test the pinned QuantLib runtime and deterministic path generation."""
    print_section("Services: QuantLib Runtime")
    print_info("Testing: QuantLib version, required APIs and seeded path reproducibility")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_quantlib_smoke.py", test_names)
    return run_command(cmd, "QuantLib runtime smoke tests", verbose=verbose)


def services_risk_simulation(verbose: bool = False, test_names: list = None) -> bool:
    """Test serializable stochastic simulation contracts and numerical engine."""
    print_section("Services: Risk Simulation")
    print_info("Testing: contracts, sampling, seed, moments, chunking and cache")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_risk_simulation.py",
        test_names,
    )
    return run_command(cmd, "Risk simulation tests", verbose=verbose)


def services_risk_optimization(verbose: bool = False, test_names: list = None) -> bool:
    """Test Riskfolio strategies, estimators, constraints and cache."""
    print_section("Services: Risk Optimization")
    print_info("Testing: objectives, risk contribution, frontier, sensitivity and cache")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_risk_optimization.py",
        test_names,
    )
    return run_command(cmd, "Risk optimization tests", verbose=verbose)


def services_risk_workers(verbose: bool = False, test_names: list = None) -> bool:
    """Test spawned quantitative worker lifecycle and failure isolation."""
    print_section("Services: Risk Workers")
    print_info("Testing: lazy spawn, queues, timeout, recycle and cancellation")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_risk_spawn_worker.py",
        test_names,
    )
    return run_command(cmd, "Risk worker tests", verbose=verbose)


def services_risk_all(verbose: bool = False, test_names: list = None) -> bool:
    """Run the complete risk-analysis service test set."""
    print_section("Services: Risk Analysis")
    print_info("Testing canonical series, analytics, QuantLib, Riskfolio and workers")
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *RISK_SERVICE_TEST_PATHS, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return run_command(cmd, "Risk analysis service tests", verbose=verbose)


def services_series_preparation(verbose: bool = False, test_names: list = None) -> bool:
    """Test canonical target-currency valuation and return preparation."""
    print_section("Services: Canonical Series Preparation")
    print_info("Testing: joint calendar, FX/price provenance, annualization and fingerprints")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_series_preparation.py", test_names)
    return run_command(cmd, "Canonical series preparation tests", verbose=verbose)


def services_signal_registry(verbose: bool = False, test_names: list = None) -> bool:
    """Test SignalPlugin base, strict registry and discovery."""
    print_section("Services: Signal Plugin Registry")
    print_info("Testing: library-agnostic SignalPlugin + strict discovery")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_registry.py", test_names)
    return run_command(cmd, "Signal plugin registry tests", verbose=verbose)


def services_signal_runtime(verbose: bool = False, test_names: list = None) -> bool:
    """Test composite-stack fail-fast and startup integration."""
    print_section("Services: Signal Runtime")
    print_info("Testing: pandas-ta-classic + TA-Lib fail-fast")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_runtime.py", test_names)
    return run_command(cmd, "Signal runtime tests", verbose=verbose)


def services_signal_contracts(verbose: bool = False, test_names: list = None) -> bool:
    """Test auto-discovered test-only signal plugin fixtures."""
    print_section("Services: Signal Plugin Contracts")
    print_info("Testing: line, band/composite, warm-up, failure and event fixtures")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_contracts.py", test_names)
    return run_command(cmd, "Signal plugin contract tests", verbose=verbose)


def services_signal_service(verbose: bool = False, test_names: list = None) -> bool:
    """Test SignalService planning, availability, execution and slicing."""
    print_section("Services: Signal Service")
    print_info("Testing: dedup, warm-up, coverage, gaps, events, isolation and output validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_service.py", test_names)
    return run_command(cmd, "Signal service tests", verbose=verbose)


def services_signal_annotations(verbose: bool = False, test_names: list = None) -> bool:
    """Test cross/threshold annotation primitives."""
    print_section("Services: Signal Annotations")
    print_info("Testing: extended-range crossing, gaps, observed-only, dedup and sampling")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_annotations.py", test_names)
    return run_command(cmd, "Signal annotation tests", verbose=verbose)


def services_signal_plugins_core(verbose: bool = False, test_names: list = None) -> bool:
    """Test EMA, RSI, MACD and Bollinger production plugins."""
    print_section("Services: Core Signal Plugins")
    print_info("Testing: TA-Lib delegation, numerical parity, warm-up and canonical output")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_plugins_core.py", test_names)
    return run_command(cmd, "Core signal plugin tests", verbose=verbose)


def services_signal_plugins_close_only(verbose: bool = False, test_names: list = None) -> bool:
    """Test SMA, ROC, StochRSI, KAMA and PPO plugins."""
    print_section("Services: Close-only Signal Plugins")
    print_info("Testing: TA-Lib delegation, warm-up, composite output and Asset/FX parity")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_plugins_close_only.py", test_names)
    return run_command(cmd, "Close-only signal plugin tests", verbose=verbose)


def services_signal_plugins_ohlc(verbose: bool = False, test_names: list = None) -> bool:
    """Test ATR, ADX, NATR, Aroon, Donchian and CCI plugins."""
    print_section("Services: OHLC Signal Plugins")
    print_info("Testing: strict input coverage, TA-Lib delegation, Donchian native path and warm-up")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_plugins_ohlc.py", test_names)
    return run_command(cmd, "OHLC signal plugin tests", verbose=verbose)


def services_signal_plugins_volume(verbose: bool = False, test_names: list = None) -> bool:
    """Test OBV and MFI plugins."""
    print_section("Services: Volume Signal Plugins")
    print_info("Testing: zero/missing volume, OBV rebasing, MFI levels and TA-Lib delegation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_plugins_volume.py", test_names)
    return run_command(cmd, "Volume signal plugin tests", verbose=verbose)


def services_signal_plugin_matrix(verbose: bool = False, test_names: list = None) -> bool:
    """Run the uniform 17-plugin regression matrix."""
    print_section("Services: Full Signal Plugin Matrix")
    print_info("Testing: all 17 plugins, domains, fields, gaps, boundaries and isolation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_signal_plugin_matrix.py", test_names)
    return run_command(cmd, "Full signal plugin matrix", verbose=verbose)


def services_asset_signals(verbose: bool = False, test_names: list = None) -> bool:
    """Test AssetSourceManager signal integration."""
    print_section("Services: Asset Signals")
    print_info("Testing: extended bulk load, FX-before-compute, signal-only payload and isolation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_signals.py", test_names)
    return run_command(cmd, "Asset signal service tests", verbose=verbose)


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


def services_brim_parse_pool(verbose: bool = False, test_names: list = None) -> bool:
    """Test that parsing off-loads to a process pool and degrades safely."""
    print_section("Services: BRIM Parse Pool")
    print_info("Testing: backend/app/services/brim_parse_pool.py")
    print_info("Tests: real parse through the pool, pickle round-trip, thread fallback")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_pool.py", test_names)

    return run_command(cmd, "BRIM parse pool tests", verbose=verbose)


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


def services_brim_create_transaction(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIMProvider._create_transaction and _loc_to_field."""
    print_section("Services: BRIM Create Transaction")
    print_info("Testing: BRIMProvider._create_transaction + BRIMProvider._loc_to_field")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_create_transaction.py", test_names)
    return run_command(cmd, "BRIM create-transaction tests", verbose=verbose)


def services_financial_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test pure-math financial utilities (WAC calculation, target currency)."""
    print_section("Services: Financial Utils (WAC)")
    print_info("Testing: backend/app/utils/financial/wac_utils.py")
    print_info("Tests: compute_wac_from_txlist, determine_target_currency")
    print_info("Pure math — no server, no DB required")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial_utils.py", test_names)
    return run_command(cmd, "Financial utils tests", verbose=verbose)


def services_roi_fifo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test ROI, FIFO, and PortfolioService pure-math utilities."""
    print_section("Services: ROI / FIFO / Portfolio Utils")
    print_info("Testing: backend/app/utils/financial/ (roi_utils, fifo_utils)")
    print_info("Testing: backend/app/services/portfolio_service.py (_build_history_series)")
    print_info("Tests: TWRR, MWRR warm-start series, SimpleROI series, FIFO lots, history series")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial/", test_names)
    return run_command(cmd, "ROI/FIFO/Portfolio service tests", verbose=verbose)


def services_portfolio_engine_vnext(verbose: bool = False, test_names: list = None) -> bool:
    """Test Portfolio Engine vNext: inline WAC, last_buy_price, 3-pool, position states."""
    print_section("Services: Portfolio Engine vNext")
    print_info("Testing: backend/app/services/portfolio_engine.py (DailyStateBuilder)")
    print_info("Tests: inline WAC, last_buy_price fallback, 3-pool K/R/W, position snapshots, period accumulators, pre-frame/frame")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_portfolio_engine_vnext.py", test_names)
    return run_command(cmd, "Portfolio Engine vNext tests", verbose=verbose)


def services_asset_sync_counts(verbose: bool = False, test_names: list = None) -> bool:
    """Test asset sync count tracking."""
    print_section("Services: Asset Sync Counts")
    print_info("Testing: Asset sync count logic")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_sync_counts.py", test_names)
    return run_command(cmd, "Asset sync counts tests", verbose=verbose)


def services_scheduler_state(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler state persistence (load/save/atomic/corrupt)."""
    print_section("Services: Scheduler State Persistence")
    print_info("Testing: backend/app/services/scheduler/state.py")
    print_info("Tests: load/save, atomic write, corrupt/partial JSON recovery")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_state.py", test_names)
    return run_command(cmd, "Scheduler state persistence tests", verbose=verbose)


def services_scheduler_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler settings parsing (_parse_times, _parse_days)."""
    print_section("Services: Scheduler Settings Parsing")
    print_info("Testing: backend/app/services/scheduler/settings.py")
    print_info("Tests: _parse_times, _parse_days — pure functions, no DB")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_settings.py", test_names)
    return run_command(cmd, "Scheduler settings parsing tests", verbose=verbose)


def services_scheduler_due(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler due-check logic (due_current_price, due_history_sync)."""
    print_section("Services: Scheduler Due-Check Logic")
    print_info("Testing: backend/app/services/scheduler/scheduler.py")
    print_info("Tests: SD-001..010 — never run, overdue, wrong day, multi-slot, midnight crossing")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_due.py", test_names)
    return run_command(cmd, "Scheduler due-check tests", verbose=verbose)


def services_scheduler_leader(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler leader election (mocked psutil)."""
    print_section("Services: Scheduler Leader Election")
    print_info("Testing: backend/app/services/scheduler/leader.py")
    print_info("Tests: SL-001..007 — single/multi-worker, zombie, PID1, --reload, exception safe")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_leader.py", test_names)
    return run_command(cmd, "Scheduler leader election tests", verbose=verbose)


def services_scheduler_loop(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler loop integration (due_* + state roundtrip, no real loop)."""
    print_section("Services: Scheduler Loop Integration")
    print_info("Testing: due_* functions with real SchedulerSettings/SchedulerState objects")
    print_info("Tests: SLO-001..003 — both jobs due, enabled flag, state serialization roundtrip")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_loop.py", test_names)
    return run_command(cmd, "Scheduler loop integration tests", verbose=verbose)


def services_brim_versioning(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIM provider versioning."""
    print_section("Services: BRIM Versioning")
    print_info("Testing: BRIM provider version detection and compatibility")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_versioning.py", test_names)
    return run_command(cmd, "BRIM versioning tests", verbose=verbose)


def services_config_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test config.get_data_dir test-mode/env-override branches."""
    print_section("Services: Config Helpers")
    print_info("Testing: backend/app/config.py (get_data_dir)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_misc.py", test_names)
    return run_command(cmd, "Config helper tests", verbose=verbose)


def services_donation_popup(verbose: bool = False, test_names: list = None) -> bool:
    """Test donation-popup trigger decision logic (should_show_donation_popup, record_login_and_maybe_show_popup)."""
    print_section("Services: Donation Popup")
    print_info("Testing: backend/app/services/donation_popup_service.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_donation_popup_service.py", test_names)
    return run_command(cmd, "Donation popup service tests", verbose=verbose)


def services_date_sentinel(verbose: bool = False, test_names: list = None) -> bool:
    """Test date sentinel resolution (min/max/passthrough, broker filter)."""
    print_section("Services: Date Sentinel Resolution")
    print_info("Testing: backend/app/services/date_sentinel.py (resolve_date_sentinels)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_date_sentinel.py", test_names)
    return run_command(cmd, "Date sentinel tests", verbose=verbose)


def services_file_preview(verbose: bool = False, test_names: list = None) -> bool:
    """Test file preview service helpers (CSV/Excel/text detection)."""
    print_section("Services: File Preview Helpers")
    print_info("Testing: backend/app/services/file_preview.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_file_preview.py", test_names)
    return run_command(cmd, "File preview tests", verbose=verbose)


def services_fx_sync(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX pair-sync orchestration branches in services/fx.py."""
    print_section("Services: FX Sync Orchestration")
    print_info("Testing: backend/app/services/fx.py")
    print_info("Tests: _is_date_within_sync_range, sync_pairs_bulk._process_route/._compute_multi_step")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_sync_service.py", test_names)
    return run_command(cmd, "FX sync service tests", verbose=verbose)


def services_provider_registry_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider registry helper branches not covered by contract tests."""
    print_section("Services: Provider Registry Helpers")
    print_info("Testing: backend/app/services/provider_registry.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_registry_misc.py", test_names)
    return run_command(cmd, "Provider registry helper tests", verbose=verbose)


def services_scheduler_joblog_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler job log read/rotate helpers."""
    print_section("Services: Scheduler Job Log Helpers")
    print_info("Testing: backend/app/services/scheduler/joblog.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_joblog_misc.py", test_names)
    return run_command(cmd, "Scheduler job log tests", verbose=verbose)


def services_scheduler_settings_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler settings local-time-to-UTC conversion."""
    print_section("Services: Scheduler Settings TZ Conversion")
    print_info("Testing: backend/app/services/scheduler/settings.py (_local_times_to_utc)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_settings_misc.py", test_names)
    return run_command(cmd, "Scheduler settings TZ conversion tests", verbose=verbose)


def services_ai_export(verbose: bool = False, test_names: list = None) -> bool:
    """Run the complete component-based AI Export service test set."""
    print_section("Services: AI Export")
    print_info("Testing the component runtime, datasets, analyses, temporal policy, and serialization")
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *AI_EXPORT_SERVICE_TEST_PATHS, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return run_command(cmd, "AI Export service tests", verbose=verbose)


def services_borsa_italiana_search(verbose: bool = False, test_names: list = None) -> bool:
    """Test Borsa Italiana provider search (single-fetch, IT+EN variants, ISIN hit)."""
    print_section("Services: Borsa Italiana Search")
    print_info("Testing: backend/app/services/asset_source_providers/borsa_italiana.py (search)")
    print_info("External engine mocked — no live Borsa Italiana calls")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_borsa_italiana_search.py", test_names)
    return run_command(cmd, "Borsa Italiana search tests", verbose=verbose)


def services_borsa_italiana_funds(verbose: bool = False, test_names: list = None) -> bool:
    """Test Borsa Italiana mutual-fund NAV path + resolve_url capability."""
    print_section("Services: Borsa Italiana Funds")
    print_info("Testing: fund detail-page NAV via provider_params.codice_fondo")
    print_info("Scraping library mocked — no live Borsa Italiana calls")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_borsa_italiana_funds.py", test_names)
    return run_command(cmd, "Borsa Italiana funds tests", verbose=verbose)


def services_web_link_finder(verbose: bool = False, test_names: list = None) -> bool:
    """Test web_link_finder unit behaviour + search orchestration augmentation."""
    print_section("Services: Web Link Finder")
    print_info("Testing: backend/app/services/web_link_finder.py")
    print_info("External engine mocked — no live ddgs/network call")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_web_link_finder.py", test_names)
    return run_command(cmd, "Web link finder tests", verbose=verbose)


def _services_setup() -> bool:
    """Start this category from a clean, empty database."""
    print_info("\n⚙️  Creating clean test database for services tests...")
    if not db_create(verbose=False):
        print_error("Failed to create clean test database")
        print_warning("Services tests may fail due to dirty database state")
        return False
    print_success("Clean test database created\n")
    return True


def services_all(verbose: bool = False) -> bool:
    """Run all backend service tests."""
    if _common.nothing_left_to_run("services"):
        return _common.consolidated_verdict("services")
    print_header("LibreFolio Backend Services Tests")
    print_info("Testing business logic and service layer")
    print_info("No backend server required")

    _common.run_category_setup("services")

    return _run_test_suite(
        suite_name="Backend Services Tests",
        tests=_get_category_tests_for_all("services", verbose),
        verbose=verbose,
        header_msg=None,
        summary_title="Backend Services Test Summary",
        success_msg="All backend services tests passed! 🎉",
        resume=_common._RESUME_MODE,
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
""",
        setup=_services_setup,
        setup_exclusive=True,
        # Earned: all 85 units ran concurrently across 4 workers on the empty
        # database this category's setup builds — 2m42 → 1m16, zero reds. They
        # never talk to a server; each opens its own session and creates the rows
        # it then reads back.
        default_isolation="write-scoped",
    )
    add_test(cat, "fx-conversion", services_fx_conversion, name="FX Conversion", desc="Currency conversion algorithms", prereq="Database created")
    add_test(cat, "asset-metadata", services_asset_metadata, name="Asset Metadata", desc="Parse/serialize, diff, patch semantics")
    add_test(cat, "asset-source", services_asset_source, name="Asset Source", desc="Provider assignment, synthetic yield")
    add_test(cat, "asset-source-refresh", services_asset_source_refresh, name="Asset Source Refresh", desc="Bulk refresh orchestration smoke test")
    add_test(cat, "provider-registry", services_provider_registry, name="Provider Registry", desc="Registration, lookup, priority, fallback")
    add_test(cat, "quantlib-runtime", services_quantlib_runtime, name="QuantLib Runtime", desc="Pinned version, required APIs and seeded path reproducibility")
    add_test(cat, "risk-simulation", services_risk_simulation, name="Risk Simulation", desc="Serializable contracts, sampling, moments, chunking and cache")
    add_test(cat, "risk-optimization", services_risk_optimization, name="Risk Optimization", desc="Riskfolio objectives, estimators, constraints, frontier and cache")
    add_test(cat, "risk-workers", services_risk_workers, name="Risk Workers", desc="Spawn lifecycle, queue bounds, timeout, recycle and cancellation")
    add_test(cat, "risk-all", services_risk_all, name="Risk Analysis", desc="Complete canonical-series, analytic, QuantLib, Riskfolio and worker suite")
    add_test(cat, "series-preparation", services_series_preparation, name="Canonical Series", desc="Converted valuations, joint calendar, returns, annualization and FX fingerprint")
    add_test(cat, "signal-registry", services_signal_registry, name="Signal Registry", desc="SignalPlugin contract, strict discovery and duplicate rejection")
    add_test(cat, "signal-runtime", services_signal_runtime, name="Signal Runtime", desc="Composite-stack fail-fast and startup integration")
    add_test(cat, "signal-contracts", services_signal_contracts, name="Signal Contracts", desc="Auto-discovered test-only line, band/composite, warm-up, failure and event fixtures")
    add_test(cat, "signal-service", services_signal_service, name="Signal Service", desc="Planning, dedup, availability, one-thread batch, output validation and slicing")
    add_test(cat, "signal-annotations", services_signal_annotations, name="Signal Annotations", desc="Line crossover, threshold crossing, observed-only, dedup and sampling")
    add_test(cat, "signal-plugins-core", services_signal_plugins_core, name="Core Signal Plugins", desc="EMA, RSI, MACD and Bollinger TA-Lib delegation and numerical regression")
    add_test(cat, "signal-plugins-close-only", services_signal_plugins_close_only, name="Close-only Signal Plugins", desc="SMA, ROC, StochRSI, KAMA and PPO delegation, warm-up and Asset/FX parity")
    add_test(cat, "signal-plugins-ohlc", services_signal_plugins_ohlc, name="OHLC Signal Plugins", desc="ATR, ADX, NATR, Aroon, Donchian and CCI strict input and numerical regression")
    add_test(cat, "signal-plugins-volume", services_signal_plugins_volume, name="Volume Signal Plugins", desc="OBV rebasing and MFI zero/missing volume, levels and TA-Lib delegation")
    add_test(cat, "signal-plugin-matrix", services_signal_plugin_matrix, name="Full Signal Plugin Matrix", desc="Uniform 22-plugin domains, fields, gaps, boundaries and isolation gate")
    add_test(cat, "asset-signals", services_asset_signals, name="Asset Signals", desc="Extended bulk load, FX-before-compute, signal-only response and isolation")
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
    add_test(cat, "brim-parse-pool", services_brim_parse_pool, name="BRIM Parse Pool", desc="Process-pool off-loading, pickle round-trip, thread fallback")
    add_test(cat, "settings", services_settings, name="Settings Service", desc="get_session_ttl_sync")
    add_test(cat, "current-price-bootstrap", services_current_price_bootstrap, name="Current Price Bootstrap", desc="OHLC widening helper (F.2/F.3)")
    add_test(cat, "scheduled-investment-param-change", services_scheduled_investment_param_change, name="Scheduled Investment Param Change", desc="Symmetric wipe on provider_params change")
    add_test(cat, "brim-provider-base", services_brim_provider_base, name="BRIM Provider Base", desc="Abstract base default properties")
    add_test(cat, "brim-create-transaction", services_brim_create_transaction, name="BRIM Create Transaction", desc="_create_transaction + _loc_to_field")
    add_test(cat, "financial-utils", services_financial_utils, name="Financial Utils", desc="WAC pure math (compute_wac_from_txlist, determine_target_currency)")
    add_test(cat, "roi-fifo-utils", services_roi_fifo_utils, name="ROI/FIFO/Portfolio Utils", desc="TWRR, MWRR warm-start, SimpleROI series, FIFO lots, _build_history_series")
    add_test(cat, "portfolio-engine", services_portfolio_engine_vnext, name="Portfolio Engine vNext", desc="Inline WAC, last_buy_price, 3-pool, position states, accumulators, pre-frame/frame")
    add_test(cat, "asset-sync-counts", services_asset_sync_counts, name="Asset Sync Counts", desc="Asset sync count tracking")
    add_test(cat, "brim-versioning", services_brim_versioning, name="BRIM Versioning", desc="Provider version detection and compatibility")
    add_test(cat, "scheduler-state", services_scheduler_state, name="Scheduler State", desc="Load/save/atomic write, corrupt/partial JSON recovery")
    add_test(cat, "scheduler-settings", services_scheduler_settings, name="Scheduler Settings", desc="_parse_times, _parse_days pure functions")
    add_test(cat, "scheduler-due", services_scheduler_due, name="Scheduler Due-Check", desc="due_current_price + due_history_sync edge cases")
    add_test(cat, "scheduler-leader", services_scheduler_leader, name="Scheduler Leader Election", desc="Mock psutil, multi-worker, Docker PID1, --reload, exception safe")
    add_test(cat, "scheduler-loop", services_scheduler_loop, name="Scheduler Loop Integration", desc="due_* + state roundtrip, no real loop")
    add_test(cat, "config-misc", services_config_misc, name="Config Helpers", desc="get_data_dir test-mode/env-override branches")
    add_test(cat, "donation-popup", services_donation_popup, name="Donation Popup", desc="Trigger decision logic (50-login/7-day/60-day rules), hidden env var, counter updates")
    add_test(cat, "date-sentinel", services_date_sentinel, name="Date Sentinel", desc="resolve_date_sentinels min/max/passthrough, broker filter")
    add_test(cat, "file-preview", services_file_preview, name="File Preview", desc="CSV/Excel/text preview detection helpers")
    add_test(cat, "fx-sync-service", services_fx_sync, name="FX Sync Orchestration", desc="_is_date_within_sync_range, _process_route/_compute_multi_step")
    add_test(cat, "provider-registry-misc", services_provider_registry_misc, name="Provider Registry Helpers", desc="auto_discover, register, get_provider_instance, BRIM plugin detection")
    add_test(cat, "scheduler-joblog-misc", services_scheduler_joblog_misc, name="Scheduler Job Log Helpers", desc="read_entries, _rotate_if_needed")
    add_test(cat, "scheduler-settings-misc", services_scheduler_settings_misc, name="Scheduler Settings TZ Conversion", desc="_local_times_to_utc")
    add_test(cat, "ai-export", services_ai_export, name="AI Export", desc="Component runtime, datasets, analyses, financial/technical builders, and temporal policy")
    add_test(cat, "borsa-italiana-search", services_borsa_italiana_search, name="Borsa Italiana Search", desc="Single-fetch search, IT+EN variants, ISIN direct hit (engine mocked)")
    add_test(cat, "borsa-italiana-funds", services_borsa_italiana_funds, name="Borsa Italiana Funds", desc="Mutual-fund NAV via codice_fondo detail page + resolve_url (scraper mocked)")
    add_test(cat, "web-link-finder", services_web_link_finder, name="Web Link Finder", desc="find_candidate_urls + search orchestration augmentation (ddgs mocked)")
    add_test(cat, "all", services_all, test_names=False, name="All Services Tests", desc="Run all service tests")
    registry["services"] = cat
