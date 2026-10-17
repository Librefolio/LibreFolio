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
    "backend/test_scripts/test_services/test_ai_export_structural_invariants.py",
    "backend/test_scripts/test_services/test_ai_export_telemetry.py",
    "backend/test_scripts/test_services/test_ai_export_temporal.py",
)

# Pure-calculation AI Export contracts: value-object invariants and observed-math
# helpers only. Kept apart from AI_EXPORT_SERVICE_TEST_PATHS (which builds against
# the shared DB) so the unit can honestly declare PURE isolation and run beside
# anything.
AI_EXPORT_PURE_TEST_PATHS = (
    "backend/test_scripts/test_services/test_ai_export_components_drawdown_total_loss.py",
    "backend/test_scripts/test_services/test_ai_export_fx_payload_invariants.py",
    "backend/test_scripts/test_services/test_ai_export_fx_timing_invariants.py",
    "backend/test_scripts/test_services/test_ai_export_int_validation.py",
    "backend/test_scripts/test_services/test_ai_export_technical_payload_invariants.py",
    "backend/test_scripts/test_services/test_ai_export_technical_shared_pure.py",
    "backend/test_scripts/test_services/test_ai_export_temporal_aggregator_invariants.py",
)

# Provider error paths: what the price and FX providers do when the source
# misbehaves. Every HTTP client is doubled, so these never leave the machine —
# which is also the only way the assertions can be exact rather than "something
# arrived". No session and no server either, hence PURE and its own unit: folding
# them into a DB-backed unit would demote them to that unit's isolation class and
# waste the parallelism on tests that touch nothing.
PROVIDER_ERROR_TEST_PATHS = (
    "backend/test_scripts/test_services/test_borsa_italiana_errors.py",
    "backend/test_scripts/test_services/test_fx_parse_errors.py",
    "backend/test_scripts/test_services/test_justetf_errors.py",
    "backend/test_scripts/test_services/test_snb_errors.py",
    "backend/test_scripts/test_services/test_yahoo_finance_errors.py",
)

RISK_SERVICE_TEST_PATHS = (
    "backend/test_scripts/test_services/test_quantlib_smoke.py",
    "backend/test_scripts/test_services/test_market_calendar.py",
    "backend/test_scripts/test_services/test_series_preparation.py",
    "backend/test_scripts/test_services/test_risk_metrics.py",
    "backend/test_scripts/test_services/test_risk_metrics_oracle.py",
    "backend/test_scripts/test_services/test_risk_registry.py",
    "backend/test_scripts/test_services/test_risk_signal_plugins.py",
    "backend/test_scripts/test_services/test_risk_service.py",
    "backend/test_scripts/test_services/test_risk_scenario_catalog.py",
    "backend/test_scripts/test_services/test_risk_analytics.py",
    "backend/test_scripts/test_services/test_risk_asset_set.py",
    "backend/test_scripts/test_services/test_risk_simulation.py",
    "backend/test_scripts/test_services/test_risk_optimization.py",
    "backend/test_scripts/test_services/test_risk_spawn_worker.py",
    "backend/test_scripts/test_services/test_data_quality_thresholds.py",
    "backend/test_scripts/test_services/test_risk_warnings_i18n.py",
    "backend/test_scripts/test_services/test_risk_eligibility.py",
    "backend/test_scripts/test_services/test_risk_exclusion_reasons.py",
)

PAC_PLANNER_CORE_TEST_PATHS = (
    "backend/test_scripts/test_services/test_pac_planner_exact.py",
    "backend/test_scripts/test_services/test_pac_planner_normalize.py",
    "backend/test_scripts/test_services/test_pac_planner_engine_boundaries.py",
)
PAC_PLANNER_EVALUATOR_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_evaluator.py"
PAC_PLANNER_ORACLE_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_oracle.py"
PAC_PLANNER_POLICIES_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_policies.py"
PAC_PLANNER_SOLVER_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_solver.py"
PAC_PLANNER_PROOF_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_proof.py"
PAC_PLANNER_WIRE_NUMBERS_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_wire_numbers.py"
PAC_PLANNER_REPORT_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_report.py"
PAC_PLANNER_SERVICE_TEST_PATH = "backend/test_scripts/test_services/test_pac_planner_planner.py"


def services_pac_planner_core(verbose: bool = False, test_names: list = None) -> bool:
    """Test exact PAC/Rebalancer primitives, models, normalization, and the engine's data boundary."""
    print_section("Services: PAC/Rebalancer Exact Core")
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *PAC_PLANNER_CORE_TEST_PATHS, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return run_command(cmd, "PAC/Rebalancer exact core tests", verbose=verbose)


def services_pac_planner_evaluator(verbose: bool = False, test_names: list = None) -> bool:
    """Test exact PAC/Rebalancer policy views, ledger replay, and evaluation."""
    print_section("Services: PAC/Rebalancer Exact Evaluator")
    cmd = _build_pytest_cmd(PAC_PLANNER_EVALUATOR_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer exact evaluator tests", verbose=verbose)


def services_pac_planner_oracle(verbose: bool = False, test_names: list = None) -> bool:
    """Test the exhaustive oracle, a test-only referee with zero SCIP dependency, over one policy view's discrete domain."""
    print_section("Services: PAC/Rebalancer Exhaustive Oracle")
    cmd = _build_pytest_cmd(PAC_PLANNER_ORACLE_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer exhaustive oracle tests", verbose=verbose)


def services_pac_planner_policies(verbose: bool = False, test_names: list = None) -> bool:
    """Test the SCIP policy compiler: scenario facts, hard constraints, objective cascade and scope guard."""
    print_section("Services: PAC/Rebalancer Policy Compiler")
    cmd = _build_pytest_cmd(PAC_PLANNER_POLICIES_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer policy compiler tests", verbose=verbose)


def services_pac_planner_solver(verbose: bool = False, test_names: list = None) -> bool:
    """Test the lexicographic SCIP search adapter against the exhaustive oracle's exact optimum."""
    print_section("Services: PAC/Rebalancer Lexicographic Solver")
    cmd = _build_pytest_cmd(PAC_PLANNER_SOLVER_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer lexicographic solver tests", verbose=verbose)


def services_pac_planner_proof(verbose: bool = False, test_names: list = None) -> bool:
    """Test that a proof comes only from SCIP's own closed statuses, through a sealed witness."""
    print_section("Services: PAC/Rebalancer Proof Semantics")
    cmd = _build_pytest_cmd(PAC_PLANNER_PROOF_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer proof semantics tests", verbose=verbose)


def services_pac_planner_wire_numbers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the exact-rational to wire-number projection every published figure passes through."""
    print_section("Services: PAC/Rebalancer Wire Numbers")
    cmd = _build_pytest_cmd(PAC_PLANNER_WIRE_NUMBERS_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer wire number tests", verbose=verbose)


def services_pac_planner_report(verbose: bool = False, test_names: list = None) -> bool:
    """Test the wire projection: rows, exposure closure, solver evidence and proof."""
    print_section("Services: PAC/Rebalancer Wire Projection")
    cmd = _build_pytest_cmd(PAC_PLANNER_REPORT_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer wire projection tests", verbose=verbose)


def services_pac_planner_service(verbose: bool = False, test_names: list = None) -> bool:
    """Test the plan orchestration end to end, from a wire request to a wire result."""
    print_section("Services: PAC/Rebalancer Plan Orchestration")
    cmd = _build_pytest_cmd(PAC_PLANNER_SERVICE_TEST_PATH, test_names)
    return run_command(cmd, "PAC/Rebalancer plan orchestration tests", verbose=verbose)


def services_fx_conversion(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX conversion service logic."""
    print_section("Services: FX Conversion Logic")
    print_info("Testing: backend/app/services/fx/conversion.py (convert_bulk)")
    print_info("Scenarios: Identity, Direct, Inverse, Roundtrip, Different Dates, Forward-fill")
    print_info("Safety: Verifies test database usage before modifying data")
    print_info("Note: Mock FX rates automatically inserted for 3 dates")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_conversion.py", test_names)
    return run_command(cmd, "FX conversion service tests", verbose=verbose)


def services_asset_source(verbose: bool = False, test_names: list = None) -> bool:
    """Test Asset Source service logic."""
    print_section("Services: Asset Source Logic")
    print_info("Testing: backend/app/services/assets/")
    print_info("Tests: Helper functions, Provider assignment, Synthetic yield")
    print_info("Note: Test assets automatically created and cleaned up")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source.py", test_names)
    return run_command(cmd, "Asset source service tests", verbose=verbose)


def services_asset_source_refresh(verbose: bool = False, test_names: list = None) -> bool:
    """Smoke test: Asset Source refresh orchestration."""
    print_section("Services: Asset Source Refresh (smoke)")
    print_info("Testing: backend/app/services/assets/refresh.py bulk refresh orchestration (smoke)")
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


def services_risk_asset_set(verbose: bool = False, test_names: list = None) -> bool:
    """Test the weightless ASSET_SET analytic family and the shapes that keep an aggregate inexpressible."""
    print_section("Services: Risk Asset Set")
    print_info("Testing: five per-asset analytics, one preparation per request, refused set-level aggregate")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_risk_asset_set.py",
        test_names,
    )
    return run_command(cmd, "Risk asset-set tests", verbose=verbose)


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


def services_risk_oracle(verbose: bool = False, test_names: list = None) -> bool:
    """Pin hand-written risk mathematics against riskfolio, NumPy and SciPy."""
    print_section("Services: Risk Metrics Oracle")
    print_info("Testing: risk/metrics.py and signals/risk_adapters.py against independent references")
    print_info("Guards: the four name traps, undefined-window semantics, matrix/scalar consistency")
    print_info("Note: riskfolio is imported here and only here — never in the web process")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_risk_metrics_oracle.py", test_names)
    return run_command(cmd, "Risk metrics oracle tests", verbose=verbose)


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


def services_period_changes(verbose: bool = False, test_names: list = None) -> bool:
    """Test the MF-P2 fixed-period changes of asset prices and FX rates."""
    print_section("Services: Period Changes (MF-P2)")
    print_info("Testing: assets/period_changes.py (get_period_changes_bulk), fx/period_changes.py (get_fx_period_changes_bulk)")
    print_info("Parity: the Assets page's computePeriodDelta on the price query's series, the FX page's on per-day conversions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_period_changes.py", test_names)
    return run_command(cmd, "Period changes service tests", verbose=verbose)


def services_provider_contracts(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider interface contracts (FX, Asset, BRIM)."""
    print_section("Services: Provider Contract Tests")
    print_info("Testing: Interface compliance for ALL registered providers (offline, no HTTP)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_contracts.py", test_names)
    return run_command(cmd, "Provider contract tests", verbose=verbose)


def services_provider_policy(verbose: bool = False, test_names: list = None) -> bool:
    """Test where the asset providers stand in the asset search (F21): tier, priority and search order."""
    print_section("Services: Asset Provider Policy")
    print_info("Testing: LIBREFOLIO_ASSET_PROVIDERS_PREMIUM/ORDER, provider_policy (tier, priority, search order), AssetSourceProvider declarations, AssetSearchService.search order (offline, no DB)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_policy.py", test_names)
    return run_command(cmd, "Asset provider policy tests", verbose=verbose)


def services_synthetic_yield(verbose: bool = False, test_names: list = None) -> bool:
    """Test synthetic yield calculation for SCHEDULED_YIELD assets."""
    print_section("Services: Synthetic Yield Calculation")
    print_info("Testing: SCHEDULED_YIELD asset valuation (ACT/365 SIMPLE interest)")
    print_info("Covers: Rate lookup, accrued interest, full valuation, DB integration, the accrual golden (33 schedules, every number)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_synthetic_yield.py", test_names)
    return run_command(cmd, "Synthetic yield tests", verbose=verbose)


def services_scheduled_investment_cost_bounds(verbose: bool = False, test_names: list = None) -> bool:
    """R13-SEC7-2: the Scheduled Investment provider's cost."""
    print_section("Services: Scheduled Investment Cost Bounds (R13-SEC7-2)")
    print_info("Testing: scheduled_investment/plugin.py (COMPOUND late interest closed form, late history, cache cap, late horizon)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduled_investment_cost_bounds.py", test_names)
    return run_command(cmd, "Scheduled investment cost bounds tests", verbose=verbose)


def services_scheduled_investment_min_start(verbose: bool = False, test_names: list = None) -> bool:
    """MF-SI1: the Scheduled Investment history from "min"."""
    print_section('Services: Scheduled Investment History From "min" (MF-SI1)')
    print_info('Testing: scheduled_investment/plugin.py get_history_value(start_date="min"), explicit-start parity')
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduled_investment_min_start.py", test_names)
    return run_command(cmd, "Scheduled investment min start tests", verbose=verbose)


def services_scheduled_investment_late_alignment(verbose: bool = False, test_names: list = None) -> bool:
    """J's note on R13-SEC7-2: one late value per day, whoever reads it."""
    print_section("Services: Scheduled Investment Late Alignment")
    print_info("Testing: scheduled_investment/plugin.py COMPOUND late interest: current value = history close = settlement = closed form, by str")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduled_investment_late_alignment.py", test_names)
    return run_command(cmd, "Scheduled investment late alignment tests", verbose=verbose)


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
    print_info("Testing: backend/app/services/transactions/transaction_service.py")
    print_info("Tests: CRUD, balance validation, link resolution, balance queries")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_service.py", test_names)

    return run_command(cmd, "Transaction service tests", verbose=verbose)


def services_transaction_cost_basis_rule(verbose: bool = False, test_names: list = None) -> bool:
    """Test which transaction rows need a cost basis (read from TX_TYPE_METADATA) and when a batch holds them to it."""
    print_section("Services: Transaction Cost Basis Rule")
    print_info("Testing: backend/app/services/transactions/validation.py (_requires_cost_basis) + batch_costs.py (validate_cost_basis)")
    print_info("Tests: the rule follows TX_TYPE_METADATA; creates without a cost refused on their row; updates held to it when they change type, quantity or cost; notes/tags edits of rows stored without a cost")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_cost_basis_rule.py", test_names)
    return run_command(cmd, "Transaction cost basis rule tests", verbose=verbose)


def services_transaction_decimal_places(verbose: bool = False, test_names: list = None) -> bool:
    """Test how many decimal places a transaction keeps, where a batch refuses more, and the balances summed exactly (C-97a)."""
    print_section("Services: Transaction Decimal Places")
    print_info("Testing: transaction_batch_stages.py (check_decimal_limits) + transactions/balances.py + assets/crud.py (held) + BRIMProvider._create_transaction")
    print_info("Tests: quantities read back to 10 decimals; over the limit refused at /validate and /commit on its row, never rounded; exact balances; held set; BRIM parse does not refuse (D2)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_decimal_places.py", test_names)
    return run_command(cmd, "Transaction decimal places tests", verbose=verbose)


def services_brim_parse_pool(verbose: bool = False, test_names: list = None) -> bool:
    """Test that parsing off-loads to a process pool and degrades safely."""
    print_section("Services: BRIM Parse Pool")
    print_info("Testing: backend/app/services/brim/brim_parse_pool.py")
    print_info("Tests: real parse through the pool, pickle round-trip, thread fallback")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_pool.py", test_names)

    return run_command(cmd, "BRIM parse pool tests", verbose=verbose)


def services_broker(verbose: bool = False, test_names: list = None) -> bool:
    """Test BrokerService CRUD operations, initial balances, and flag validation."""
    print_section("Services: Broker Service")
    print_info("Testing: backend/app/services/brokers/broker_service.py")
    print_info("Tests: CRUD, initial deposits, get_summary, flag validation")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_broker_service.py", test_names)

    return run_command(cmd, "Broker service tests", verbose=verbose)


def services_user_profile(verbose: bool = False, test_names: list = None) -> bool:
    """Test user profile update service."""
    print_section("Services: User Profile")
    print_info("Testing: backend/app/services/accounts/user_service.py (update_profile)")
    print_info("Tests: Update username/email, uniqueness validation, error handling")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_user_profile.py", test_names)
    return run_command(cmd, "User profile service tests", verbose=verbose)


def services_account_tokens(verbose: bool = False, test_names: list = None) -> bool:
    """Test the single-use account tokens: invites, password resets, e-mail verification, admin setup."""
    print_section("Services: Account Tokens")
    print_info("Testing: backend/app/services/accounts/token_service.py")
    print_info("Tests: hash-only storage, one purpose per token, expiry boundary, atomic single use, revocation, caller-owned transaction, no plaintext in logs")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_account_tokens.py", test_names)
    return run_command(cmd, "Account token service tests", verbose=verbose)


def services_login_throttle(verbose: bool = False, test_names: list = None) -> bool:
    """Test the limit on failed sign-ins (F15): per identifier and per address, its switch."""
    print_section("Services: Login Throttle")
    print_info("Testing: backend/app/services/accounts/login_throttle.py")
    print_info("Tests: 10 failures per identifier and 50 per address in 15 minutes, a refusal not counted, a success forgets the identifier, LIBREFOLIO_LOGIN_LIMIT=off")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_login_throttle.py", test_names)
    return run_command(cmd, "Login throttle service tests", verbose=verbose)


def services_accounts_checks(verbose: bool = False, test_names: list = None) -> bool:
    """Test the accounts' configuration check and its switch: LIBREFOLIO_LOGIN_LIMIT."""
    print_section("Services: Accounts Configuration Checks")
    print_info("Testing: backend/app/config/accounts.py (login_limit_enabled), backend/app/services/accounts/checks.py")
    print_info("Tests: on/off/invalid, the check in CONFIG_CHECKS, the startup audit stopping on an invalid value")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_accounts_checks.py", test_names)
    return run_command(cmd, "Accounts configuration check tests", verbose=verbose)


def services_registration(verbose: bool = False, test_names: list = None) -> bool:
    """Test who may create an account: registration modes, invitations, the user limit, and their variables."""
    print_section("Services: Registration")
    print_info("Testing: backend/app/services/accounts/registration_service.py, backend/app/config/accounts.py, the registration_mode setting")
    print_info("Tests: the four variables, the effective mode (variable over row, invalid closes), usage, invitations, every register_user branch, the limit under a race, bcrypt off the loop")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_registration_service.py", test_names)
    return run_command(cmd, "Registration service tests", verbose=verbose)


def services_admin_bootstrap(verbose: bool = False, test_names: list = None) -> bool:
    """Test F02, the initial administrator: its variables, the startup bootstrap, the setup link, setup-link."""
    print_section("Services: Initial Administrator (F02)")
    print_info("Testing: backend/app/config/accounts.py admin_bootstrap_config, services/accounts/bootstrap_admin_service.py, token_service.issue_token(token=), user_usage, scripts/user_cli.py setup-link")
    print_info("Tests: the variables and their errors, created/ignored/pending/rearmed/expired, two workers, the link logged once and emailed, setup completed, the waiting administrator in the usage")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_admin_bootstrap.py", test_names)
    return run_command(cmd, "Initial administrator tests", verbose=verbose)


def services_email_case(verbose: bool = False, test_names: list = None) -> bool:
    """Test P18: email addresses unique regardless of A–Z case, in the rule, the index, the lookups and the writes."""
    print_section("Services: Email Addresses Regardless of Case (P18)")
    print_info("Testing: user_service.email_fold/same_email, the index ux_users_email_lower, get_user_by_email and get_user_by_username_or_email, create_user, register_user, update_profile, the F02 bootstrap")
    print_info("Tests: A–Z folded and nothing else, the index refusing a case variant through the ORM and plain SQL, lookups in any case, case-only changes of one's own address, the non-ASCII limit")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_case.py", test_names)
    return run_command(cmd, "Email case tests", verbose=verbose)


def services_username_rules(verbose: bool = False, test_names: list = None) -> bool:
    """Test A-21a, rules 1 and 2: no new username with an @, no address that is another account's username."""
    print_section("Services: Username Rules (A-21a)")
    print_info("Testing: config/accounts.py admin_bootstrap_config, user_service.create_user/update_profile, register_user, scripts/user_cli.py create-user/set-email")
    print_info("Tests: the @ refused in every new username and nothing else of the character set, legacy names left as they are, an address equal to a username refused in any A–Z case")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_username_rules.py", test_names)
    return run_command(cmd, "Username rules tests", verbose=verbose)


def services_username_lookup(verbose: bool = False, test_names: list = None) -> bool:
    """Test A-21a, rule 3: the sign-in's lookup reads an identifier with an @ as an address first."""
    print_section("Services: Username Lookup (A-21a)")
    print_info("Testing: user_service.get_user_by_username_or_email")
    print_info("Tests: an address finds its owner before a legacy name written like it, in both orders of the rows; the exact legacy fallback; without an @ a username only, exact")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_username_lookup.py", test_names)
    return run_command(cmd, "Username lookup tests", verbose=verbose)


def services_password_policy(verbose: bool = False, test_names: list = None) -> bool:
    """Test the password rules in one place: what a new password must meet, for the API, the CLI and the app."""
    print_section("Services: Password Policy")
    print_info("Testing: backend/app/services/accounts/password_policy.py")
    print_info("Tests: the five rules published in order, failed_rules in the policy's order, Unicode classes (Lu, Ll, Nd, symbols), length in code points")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_password_policy.py", test_names)
    return run_command(cmd, "Password policy tests", verbose=verbose)


def services_email_config(verbose: bool = False, test_names: list = None) -> bool:
    """Test the SMTP configuration accessors of the optional e-mail: LIBREFOLIO_SMTP_* read at call time."""
    print_section("Services: E-mail Configuration")
    print_info("Testing: backend/app/config/email.py")
    print_info("Tests: blank is unset, TLS modes and their ports, ASCII-digit port and hourly limit, one mailbox for From and Reply-To, password through env_secret, EmailConfigError codes, no password in a message")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_config.py", test_names)
    return run_command(cmd, "E-mail configuration tests", verbose=verbose)


def services_email_messages(verbose: bool = False, test_names: list = None) -> bool:
    """Test the e-mail texts: typed builders, the four-language catalogue and the composed message."""
    print_section("Services: E-mail Messages")
    print_info("Testing: backend/app/services/email/messages.py, backend/app/services/email/templates/")
    print_info("Tests: languages, keyword-only builders, http(s) links only, escaping, no user data in subjects, Babel durations, catalogue guard, headers and multipart/alternative, one recipient, every value on one line")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_messages.py", test_names)
    return run_command(cmd, "E-mail message tests", verbose=verbose)


def services_email_delivery(verbose: bool = False, test_names: list = None) -> bool:
    """Test SMTP delivery against a fake server on 127.0.0.1, the configuration state, the hourly budget and send_email."""
    print_section("Services: E-mail Delivery")
    print_info("Testing: backend/app/services/email/smtp.py, backend/app/services/email/delivery.py")
    print_info("Tests: the fake SMTP server, error codes (TLS never falls back to plain), config state and its one-time log, budget on a fake clock, smtplib off the event loop, no secret in the logs, a blocked instance sends nothing")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_delivery.py", test_names)
    return run_command(cmd, "E-mail delivery tests", verbose=verbose)


def services_email_checks(verbose: bool = False, test_names: list = None) -> bool:
    """Test the configuration checks of the optional e-mail (email.smtp, email.smtp_encryption, email.links)."""
    print_section("Services: E-mail Configuration Checks")
    print_info("Testing: backend/app/services/email/checks.py, their place in backend/app/services/platform/config_audit.py")
    print_info("Tests: off/ok/invalid with problem and variable, plain text local or public, links ok/missing/invalid, EMAIL_CONFIG_CHECKS, no password, host, user or sender in a detail")
    print_info("Tests: the end of CONFIG_CHECKS, run_config_checks, either module imported first in a fresh interpreter, the startup log")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_checks.py", test_names)
    return run_command(cmd, "E-mail configuration check tests", verbose=verbose)


def services_email_flows(verbose: bool = False, test_names: list = None) -> bool:
    """Test what an action of the application sends: the language of an account's emails, the test email, the links an administrator emails and the forgotten password."""
    print_section("Services: E-mail Flows")
    print_info("Testing: backend/app/services/email/flows.py")
    print_info("Tests: account language (its own, else default_language, else English; no settings row created), the test email to the account's own address in its language, nothing sent when e-mail is off or unusable, configuration read off the event loop")
    print_info("Tests: send_link_email (order of refusals, token states, recipients, languages, the PUBLIC_URL link)")
    print_info("Tests: forgotten password admission (limits per address and identifier, budget) and work (per-account limits, revocation, silence, never raises)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_flows.py", test_names)
    return run_command(cmd, "E-mail flow tests", verbose=verbose)


def services_email_verification(verbose: bool = False, test_names: list = None) -> bool:
    """Test the verification of an email address at sign-up (developer decision 44): the hold, the emailed link, the click and «resend»."""
    print_section("Services: E-mail Verification")
    print_info("Testing: backend/app/services/email/verification.py")
    print_info("Tests: the option and whether a link can go, hold_for_verification, awaiting_verification, registration_email_work, confirm_email, resend_verification (limits per address and per account, the password as the login checks it), no secret in the logs")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_verification.py", test_names)
    return run_command(cmd, "E-mail verification tests", verbose=verbose)


def services_email_verification_hooks(verbose: bool = False, test_names: list = None) -> bool:
    """Test the email-verification hooks in A's services (lot E5b): user_usage, register_user, the changes of status, holds_place, the setting's guard."""
    print_section("Services: E-mail Verification Hooks")
    print_info("Testing: registration_service.user_usage/register_user, user_service.update_user_status/set_user_active, verification.holds_place/place_holders, settings_service._refuse_what_cannot_turn_on")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_verification_hooks.py", test_names)
    return run_command(cmd, "E-mail verification hooks tests", verbose=verbose)


def services_email_links(verbose: bool = False, test_names: list = None) -> bool:
    """Test the links an email carries: built from LIBREFOLIO_PUBLIC_URL alone (developer decision 45)."""
    print_section("Services: E-mail Links")
    print_info("Testing: backend/app/services/email/links.py")
    print_info("Tests: links_state missing/invalid/ready (an address no link can start from, trailing slash, path prefix, never raises, never echoes), the instance host with its port, require_links, email_link = base + page + token in the fragment, email_instance_config in every combination")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_email_links.py", test_names)
    return run_command(cmd, "E-mail link tests", verbose=verbose)


def services_provider_cooldown(verbose: bool = False, test_names: list = None) -> bool:
    """Test the process's provider pauses after HTTP 429 and their two variables."""
    print_section("Services: Provider Cooldown")
    print_info("Testing: backend/app/services/platform/provider_cooldown.py, backend/app/config/sleep_wake.py")
    print_info("Tests: LIBREFOLIO_PROVIDER_COOLDOWN_BASE/MAX_SECONDS and settings, instance read per call, (domain, provider, scope) keys, base/max read at each refusal, in-flight answers ignored, base 0 off, defaults if invalid, logged once per (variable, code) per process (fake clock)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_cooldown.py", test_names)
    return run_command(cmd, "Provider cooldown tests", verbose=verbose)


def services_rate_limit_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Test the «too many requests» errors of the asset and FX domains and the helpers that recognise a refusal (X-RL X1/X2)."""
    print_section("Services: Rate-Limit Errors")
    print_info("Testing: backend/app/services/assets/base.py, backend/app/services/fx/base.py, the CSS scraper's cooldown_scope")
    print_info("Tests: AssetRateLimitedError/FXRateLimitedError, a 429 (httpx, requests) with Retry-After in seconds or as an HTTP date, «status (code) 429» / «HTTP (Error) 429» / «Too Many Requests» text but never «4290» or «4291», passthrough, cooldown_scope hook, longest_refusal")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_rate_limit_errors.py", test_names)
    return run_command(cmd, "Rate-limit error tests", verbose=verbose)


def services_rate_limit_boundaries(verbose: bool = False, test_names: list = None) -> bool:
    """Test the pauses after «too many requests» at the asset and FX provider-call boundaries (X-RL X4)."""
    print_section("Services: Rate-Limit Boundaries")
    print_info("Testing: backend/app/services/assets/core.py (call_provider, cooldown_scope_for), backend/app/services/fx/runtime.py (call_fx_provider)")
    print_info("Tests: pause = max(base, Retry-After), no plugin call while paused, one trial after it, an answer ends it, another error or a cancellation frees the trial, pauses off, one pause per CSS host, test doubles, foreign and secret-bearing refusals (private Cooldowns, fake clock)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_rate_limit_boundaries.py", test_names)
    return run_command(cmd, "Rate-limit boundary tests", verbose=verbose)


def services_rate_limit_http_providers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the CSS scraper and the four FX providers on an HTTP 429 (X-RL X3)."""
    print_section("Services: Rate-Limit HTTP Providers")
    print_info("Testing: css_scraper, fx_providers/ecb, fed, boe, snb on an httpx.MockTransport")
    print_info("Tests: refusals with Retry-After and host scope, other statuses unchanged, FED/BOE whole-call refusal with the longest wait, ECB stopping at the first refused currency, SNB map and data, an ECB 429 through the FX boundary")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_rate_limit_http_providers.py", test_names)
    return run_command(cmd, "Rate-limit HTTP provider tests", verbose=verbose)


def services_rate_limit_results(verbose: bool = False, test_names: list = None) -> bool:
    """Test the results that carry a provider refusal: live price, refresh, FX sync, probe, search (X-RL X5)."""
    print_section("Services: Rate-Limit Results")
    print_info("Testing: assets/price_query.py, assets/refresh.py, fx/sync.py, assets/provider_management.py, assets/search.py")
    print_info("Tests: error_code RATE_LIMITED and retry_after on each result, the last known price kept, data kept beside a refusal, the shortest wait of a pair's refused providers, INFO not tracebacks, the SSE provider_error fields (private DB, private Cooldowns)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_rate_limit_results.py", test_names)
    return run_command(cmd, "Rate-limit result tests", verbose=verbose)


def services_shutdown_budget(verbose: bool = False, test_names: list = None) -> bool:
    """Test the shutdown time budget: the server exits within about 8 s of SIGTERM or SIGINT (decision 35)."""
    print_section("Services: Shutdown Budget")
    print_info("Testing: backend/app/services/platform/shutdown_budget.py, backend/app/config/sleep_wake.py, entrypoint.sh, the shutdown grace of the runner and of Playwright")
    print_info("Tests: LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS, its 3/8 drain, entrypoint.sh, graces >= budget + 2 s, the watchdog (once, exit 1 on fakes) only under uvicorn's handle_exit, its wrappers, deadlines that never arm it, the child step idle without it, children terminated then killed")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_shutdown_budget.py", test_names)
    return run_command(cmd, "Shutdown budget tests", verbose=verbose)


def services_shutdown_process(verbose: bool = False, test_names: list = None) -> bool:
    """Test the shutdown budget in real server processes under the uvicorn CLI, signalled with SIGTERM and SIGINT."""
    print_section("Services: Shutdown Budget in a Server Process")
    print_info("Testing: backend/app/services/platform/lifecycle.py and shutdown_budget.py under uvicorn, the wiring of backend/app/services/platform/app_lifespan.py")
    print_info("Tests: budget 2 s, drain 1 s: a request in flight cancelled, a step that never ends cut, SIGINT with a blocked thread ended by the watchdog, a child ignoring SIGTERM killed, budget 0 runs a 4 s step to its end, nothing pending exits at once; first and last steps")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_shutdown_budget_process.py", test_names)
    return run_command(cmd, "Shutdown budget process tests", verbose=verbose)


def services_sleep_wake_activity(verbose: bool = False, test_names: list = None) -> bool:
    """Test the process's record of the user's presence and of the work in progress, read by sleep and wake (lot Z2a)."""
    print_section("Services: Sleep and Wake Activity")
    print_info("Testing: backend/app/services/platform/sleep_wake/activity.py, its entry in backend/app/services/platform/middleware.py")
    print_info("Tests: request_kind, Activity on a fake clock (in flight and stamped, return listeners, idle seconds, busy spans and checks, threads), current_activity, ActivityMiddleware (scopes, probes, wake-sync, 404, streaming, background tasks, errors), activity first in MIDDLEWARE_STACK")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_sleep_wake_activity.py", test_names)
    return run_command(cmd, "Sleep and wake activity tests", verbose=verbose)


def services_sleep_wake_suspend(verbose: bool = False, test_names: list = None) -> bool:
    """Test the idle suspension of a Fly machine: its configuration, the suspender, the idle monitor and its hooks (lot Z2b)."""
    print_section("Services: Sleep and Wake Suspend")
    print_info("Testing: backend/app/config/sleep_wake.py, backend/app/services/platform/sleep_wake/suspend.py and idle_monitor.py, their hooks in backend/app/api/v1/system/wake.py and backend/app/services/platform/app_lifespan.py")
    print_info("Tests: IDLE_SUSPEND_MODE/MINUTES, FlySuspender on a MockTransport (request, 2xx, http_<status>, connection, not_on_fly, socket, timeout), IdleMonitor.check (outcomes, backoff, a warning per streak), the loop, requested checks, start/stop, busy checks, wake hook, lifespan steps")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_sleep_wake_suspend.py", test_names)
    return run_command(cmd, "Sleep and wake suspend tests", verbose=verbose)


def services_session_version(verbose: bool = False, test_names: list = None) -> bool:
    """Test session revocation through the session version (the sv claim of the session cookie)."""
    print_section("Services: Session Version")
    print_info("Testing: auth_service.py (SessionClaims, sv), api/v1/auth.py (get_current_user), user_service.py (end_sessions, reset/active/admin)")
    print_info("Tests: claims round trip, cookies without sv at version 0, untrusted tokens never raise, another version refused, raised by one only by reset/deactivate/demote, bcrypt off the loop; A-27, the live reset links revoked by reset_password and a real address change, and by nothing else")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_session_version.py", test_names)
    return run_command(cmd, "Session version tests", verbose=verbose)


def services_address_probe(verbose: bool = False, test_names: list = None) -> bool:
    """Test the address probe: the signed nonce of the Invite dialog's server-address check (A6a, D-A3)."""
    print_section("Services: Address Probe")
    print_info("Testing: backend/app/services/accounts/address_probe.py (issue_probe_nonce, verify_probe_nonce)")
    print_info("Tests: 56-byte layout under derive_key('accounts.address-probe.v1'), valid while expiry >= now, every forgery and malformed text refused, another instance refused, hmac.compare_digest, never raises")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_address_probe.py", test_names)
    return run_command(cmd, "Address probe tests", verbose=verbose)


def services_account_deletion_preview(verbose: bool = False, test_names: list = None) -> bool:
    """Test what deleting an account would take, the one helper both deletions use, and the hook of lot A7 (A6a)."""
    print_section("Services: Account Deletion Preview")
    print_info("Testing: backend/app/services/accounts/user_service.py (preview_user_deletion, delete_account, account_protection)")
    print_info(
        "Tests: the preview is what delete_user then deletes in seven scenarios, transaction counts, transfers left unpaired in both directions, writes nothing; report files removed once after the commit, off the loop, never when nothing is deleted or the deletion fails; the hook protects nobody"
    )

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_account_deletion_preview.py", test_names)
    return run_command(cmd, "Account deletion preview service tests", verbose=verbose)


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
    print_info("Testing: backend/app/services/accounts/global_settings_service.py")
    print_info("Tests: Type conversion, DB reads with defaults, TTL/upload getters, the registration_mode row")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_global_settings_service.py", test_names)
    return run_command(cmd, "Global settings service tests", verbose=verbose)


def services_fx_core(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX core helpers."""
    print_section("Services: FX Core Helpers")
    print_info("Testing: backend/app/services/fx/ (core functions not covered by fx-conversion)")
    print_info("Tests: normalize_rate, upsert_rates_bulk, delete_rates_bulk, _count_actual_changes")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_core.py", test_names)
    return run_command(cmd, "FX core helpers tests", verbose=verbose)


def services_fx_catalog(verbose: bool = False, test_names: list = None) -> bool:
    """Test the cached supported-currency catalog of the FX providers (X-R8)."""
    print_section("Services: FX Provider Currency Catalog")
    print_info("Testing: backend/app/services/fx/catalog.py (get_supported_currencies_cached, behind GET /fx/providers)")
    print_info("Tests: 24 h cache and copies, last known list on failure/timeout, 5-minute retry delay, one fetch per event loop, cache panel")
    print_info("Fake providers only — no network, no database, no server")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_catalog.py", test_names)
    return run_command(cmd, "FX provider currency catalog tests", verbose=verbose)


def services_static_uploads(verbose: bool = False, test_names: list = None) -> bool:
    """Test static uploads service."""
    print_section("Services: Static Uploads")
    print_info("Testing: backend/app/services/files/static_uploads.py")
    print_info("Tests: File save/list/get/delete, security validation, user filtering")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_static_uploads.py", test_names)
    return run_command(cmd, "Static uploads service tests", verbose=verbose)


def services_brim_parse_error(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIMParseError exception class."""
    print_section("Services: BRIM Parse Error")
    print_info("Testing: backend/app/services/brim/brim_provider.py (BRIMParseError)")
    print_info("Tests: Constructor, message/details attributes, exception hierarchy")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_error.py", test_names)
    return run_command(cmd, "BRIM parse error tests", verbose=verbose)


def services_brim_parse_race(verbose: bool = False, test_names: list = None) -> bool:
    """Test parse resilience when the file is renamed underfoot."""
    print_section("Services: BRIM Parse Race")
    print_info("Testing: backend/app/services/brim/brim_provider.py (uploaded → parsed rename race)")
    print_info("Tests: retry after the rename, no retry on a genuine read error, path resolution on stale metadata")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_race.py", test_names)
    return run_command(cmd, "BRIM parse race tests", verbose=verbose)


def services_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test settings service: user settings CRUD, get_effective_base_currency."""
    print_section("Services: Settings Service")
    print_info("Testing: backend/app/services/accounts/settings_service.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_settings_service.py", test_names)
    return run_command(cmd, "Settings service tests", verbose=verbose)


def services_current_price_bootstrap(verbose: bool = False, test_names: list = None) -> bool:
    """Test F.2/F.3 unit helper `_extend_ohlc_bounds` in assets.price_query."""
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


def services_brim_report_sets(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIM report-set schemas, plugin-contract defaults and combined-file storage."""
    print_section("Services: BRIM Report Sets")
    print_info("Testing: backend/app/schemas/brim.py + backend/app/services/brim/brim_provider.py (report roles, truth points, combined files)")
    print_info("Tests: schemas, BRIMProvider set defaults, two-role fake plugin, batch_id, combined-file write/save/reuse/stale/delete/list")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_report_sets.py", test_names)
    return run_command(cmd, "BRIM report sets tests", verbose=verbose)


def services_brim_gap_fix(verbose: bool = False, test_names: list = None) -> bool:
    """Test the BRIM gap-fix: LibreFolio's balances at a date, the gap-fix schemas and compute_gap_fix."""
    print_section("Services: BRIM Gap-fix")
    print_info("Testing: backend/app/services/brim/brim_gap_fix.py + TransactionService balances at a date + gap-fix schemas in backend/app/schemas/brim.py")
    print_info("Tests: exclude_tx_ids, get_balances_at_end_of, request/response schemas, proposals, cost todos, explanation, verifications, one import vs three")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_gap_fix.py", test_names)
    return run_command(cmd, "BRIM gap-fix tests", verbose=verbose)


def services_brim_create_transaction(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIMProvider._create_transaction and _loc_to_field."""
    print_section("Services: BRIM Create Transaction")
    print_info("Testing: BRIMProvider._create_transaction + BRIMProvider._loc_to_field")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_create_transaction.py", test_names)
    return run_command(cmd, "BRIM create-transaction tests", verbose=verbose)


def services_financial_math(verbose: bool = False, test_names: list = None) -> bool:
    """Test the financial_math layer: average cost, native cash, returns, periods, ledger control totals, and the boundaries of the whole layer."""
    print_section("Services: Financial Math (average cost, native cash, returns, periods, ledger totals, layer boundaries)")
    print_info("Testing: backend/app/services/financial_math/ (average_cost.py, native_cash.py, returns.py, portfolio/period.py, ledger_totals.py; imports and packages of every module)")
    print_info("Tests: average costs and cost movements, native cash and cash movements, effective share, exchange results, rebasing and ratios, the verified MWRR root, periods and unit costs, control totals, layer boundaries")
    print_info("Pure — convert_bulk is stubbed: no server, no shared DB (the ledger totals read private SQLite files under tmp_path)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial_math/", test_names)
    return run_command(cmd, "Financial math tests", verbose=verbose)


def services_roi_fifo_engine(verbose: bool = False, test_names: list = None) -> bool:
    """Test ROI, FIFO, and PortfolioService pure-math utilities."""
    print_section("Services: ROI / FIFO / Portfolio Utils")
    print_info("Testing: backend/app/services/financial_math/returns.py")
    print_info("Testing: backend/app/services/portfolio_service.py (compute_wac_iterative, get_report)")
    print_info("Tests: TWRR/MWRR/SimpleROI + series, FIFO lots (FifoLotEngine), price marks, WAC")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial/", test_names)
    return run_command(cmd, "ROI/FIFO/Portfolio service tests", verbose=verbose)


def services_orphan_transfer_numbers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the lots and the Dashboard of a broker whose TRANSFER partner was deleted with its broker (V-3, D-J4)."""
    print_section("Services: Orphan Transfer After Broker Delete (V-3 numbers)")
    print_info("Testing: LotsAnalysisService and PortfolioService after BrokerService.delete_bulk leaves the other half of a TRANSFER")
    print_info("Tests: TRANSFER_PAIR_MISSING vs the ADJUSTMENT-in lot, in-kind capital at market value vs at cost basis, against a control book")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_financial/test_orphan_transfer_after_broker_delete.py", test_names)
    return run_command(cmd, "Orphan transfer numbers tests", verbose=verbose)


def services_lone_transfer_legs(verbose: bool = False, test_names: list = None) -> bool:
    """Test decision 47's conversion of the lone giving TRANSFER legs a broker deletion left before 1.3."""
    print_section("Services: Lone Transfer Legs (decision 47)")
    print_info("Testing: backend/app/services/transactions/lone_transfer_legs.py, its startup step (app_lifespan) and the offline post-migration script")
    print_info("Tests: handed over at the leg's own broker's Auto cost, a missing conversion left a TRANSFER, receiving and linked legs untouched, dry run, second run, startup step and wrapper, script lines and exit code")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_lone_transfer_legs.py", test_names)
    return run_command(cmd, "Lone transfer legs tests", verbose=verbose)


def services_portfolio_allocation_source(verbose: bool = False, test_names: list = None) -> bool:
    """Test the read-only PAC/Rebalancer portfolio source snapshot."""
    print_section("Services: Portfolio Allocation Source")
    print_info("Testing: backend/app/services/pac_allocator/source/")
    print_info("Tests: selectors, exact facts, saved evidence, provenance and no side effects")

    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_portfolio_allocation_source.py",
        test_names,
    )
    return run_command(cmd, "Portfolio allocation-source tests", verbose=verbose)


def services_lots_analysis_pure(verbose: bool = False, test_names: list = None) -> bool:
    """Run the pure lots-analysis builders (no DB, no server, no network)."""
    print_section("Services: Lots Analysis Pure Builders")
    print_info("Testing: backend/app/services/financial_math/lots/ and lots_analysis_service.py (sync, argument-driven builders)")
    print_info("Tests: SHORT lots, estimated_mode, price-series gaps, ADJUSTMENT cost basis, transfer scope, the reference price and the days at cost")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_lots_analysis_pure.py", test_names)
    return run_command(cmd, "Lots Analysis pure builder tests", verbose=verbose)


def services_asset_source_guards(verbose: bool = False, test_names: list = None) -> bool:
    """Run the AssetSourceManager integrity guards and event FX conversion tests."""
    print_section("Services: Asset Source Guards")
    print_info("Testing: backend/app/services/assets/ (bulk_upsert_prices, get_prices_bulk, list_assets)")
    print_info("Tests: OHLC rejection policy, close-only bound widening, identifier filters, event FX pass")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source_upsert_guards.py", test_names)
    return run_command(cmd, "Asset Source guard tests", verbose=verbose)


def services_asset_event_store(verbose: bool = False, test_names: list = None) -> bool:
    """Run the manual asset-event store contract tests (release 1.3, W E1a: decisions 20-23)."""
    print_section("Services: Asset Event Store")
    print_info("Testing: backend/app/services/assets/event_store.py, backend/app/schemas/assets/events.py")
    print_info("Tests: type normalisation, all-or-nothing upsert with located errors, create mode, event_ids, delete scoped by asset")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_event_store.py", test_names)
    return run_command(cmd, "Asset Event Store tests", verbose=verbose)


def services_asset_digit_limits(verbose: bool = False, test_names: list = None) -> bool:
    """Run the C-97a digit limits: manual prices and events refused beyond them, provider prices truncated."""
    print_section("Services: Asset Digit Limits")
    print_info("Testing: backend/app/services/assets/price_store.py, event_store.py, backend/app/api/v1/assets/events.py")
    print_info("Tests: manual prices (12 decimals) and events (6) beyond the limit or 15 significant digits refused with nothing written, provider prices truncated, what fits read back exactly")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_digit_limits.py", test_names)
    return run_command(cmd, "Asset digit limit tests", verbose=verbose)


def services_current_price_storable(verbose: bool = False, test_names: list = None) -> bool:
    """Run X-R40 + W-B62: the current price and the price refresh serve, cache and announce only what the database can keep."""
    print_section("Services: Current Price Storable")
    print_info("Testing: backend/app/services/assets/price_query.py (get_current_prices_bulk), refresh.py (bulk_refresh_prices)")
    print_info("Tests: an unstorable quote never served nor cached (database fallback) and logged once per value, a valid one served and cached as the database keeps it, a refresh's changed_points and current-value cache limited to what is stored, a fallback past an unreadable close")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_current_price_storable.py", test_names)
    return run_command(cmd, "Current price storable tests", verbose=verbose)


def services_event_split_ratio(verbose: bool = False, test_names: list = None) -> bool:
    """Run X-R47: a SPLIT event's ratio checked when it is written, manual SPLITs of 0 or below refused, a provider's dropped; and R13-SEC7: the P-10 refusal shows only the caller's transactions."""
    print_section("Services: Event Split Ratio")
    print_info("Testing: backend/app/services/assets/event_store.py (bulk_upsert_events, _upsert_asset_events, _reject_split_retype_without_costs), backend/app/api/v1/assets/events.py")
    print_info("Tests: a manual SPLIT of ratio 0 or below refused with EVENT_INVALID_SPLIT_RATIO (HTTP 400) in every way it is written, nothing written; a provider's dropped with one warning; valid ratios accepted; the P-10 refusal naming only the caller's transactions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_event_split_ratio.py", test_names)
    return run_command(cmd, "Event split ratio tests", verbose=verbose)


def services_portfolio_engine_vnext(verbose: bool = False, test_names: list = None) -> bool:
    """Test Portfolio Engine vNext: inline WAC, last_buy_price, 3-pool, position states."""
    print_section("Services: Portfolio Engine vNext")
    print_info("Testing: backend/app/services/financial_math/portfolio/daily_state.py (DailyStateBuilder)")
    print_info("Tests: inline WAC, last_buy_price fallback, 3-pool K/R/W, position snapshots, period accumulators, one replay with states from date_from")

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
    print_info("Testing: backend/app/services/platform/scheduler/state.py")
    print_info("Tests: load/save, atomic write, corrupt/partial JSON recovery")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_state.py", test_names)
    return run_command(cmd, "Scheduler state persistence tests", verbose=verbose)


def services_scheduler_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler settings parsing (_parse_times, _parse_days)."""
    print_section("Services: Scheduler Settings Parsing")
    print_info("Testing: backend/app/services/platform/scheduler/settings.py")
    print_info("Tests: _parse_times, _parse_days — pure functions, no DB")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_settings.py", test_names)
    return run_command(cmd, "Scheduler settings parsing tests", verbose=verbose)


def services_scheduler_due(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler due-check logic (due_current_price, due_history_sync)."""
    print_section("Services: Scheduler Due-Check Logic")
    print_info("Testing: backend/app/services/platform/scheduler/scheduler.py")
    print_info("Tests: SD-001..022 — never run, overdue, wrong day, multi-slot, midnight crossing, time zones, DST, missed slots of the last 7 days (D-Z3-1)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_due.py", test_names)
    return run_command(cmd, "Scheduler due-check tests", verbose=verbose)


def services_scheduler_leader(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler leader election (mocked psutil)."""
    print_section("Services: Scheduler Leader Election")
    print_info("Testing: backend/app/services/platform/scheduler/leader.py")
    print_info("Tests: SL-001..007 — single/multi-worker, zombie, PID1, --reload, exception safe")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_leader.py", test_names)
    return run_command(cmd, "Scheduler leader election tests", verbose=verbose)


def services_scheduler_run_lock(verbose: bool = False, test_names: list = None) -> bool:
    """Test the scheduler's lock across processes: scheduler_run_lock, a flock on the data directory's .scheduler.lock (Z-11, N71)."""
    print_section("Services: Scheduler Lock Across Processes")
    print_info("Testing: backend/app/services/platform/scheduler/run_lock.py (scheduler_run_lock, cross_process_lock_available, run_lock_path), against real child processes")
    print_info(
        "Tests: RL-001..009 — the block waits while another process holds the lock (LOCK_EX | LOCK_NB, POLL_SECONDS apart) and runs once it lets go or is killed; a cancelled wait, even with an attempt in flight, leaves no descriptor nor lock; released on an exception; 0o600 file kept, symlink refused; open/flock/close off the loop; constants, availability, path; without fcntl"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_run_lock.py", test_names)
    return run_command(cmd, "Scheduler lock across processes tests", verbose=verbose)


def services_scheduler_multiprocess(verbose: bool = False, test_names: list = None) -> bool:
    """Test two real processes running the scheduler's due jobs at once: each job once, behind the lock across processes (Z-11, N71)."""
    print_section("Services: Scheduler Across Two Processes")
    print_info("Testing: backend/app/services/platform/scheduler/scheduler.py (run_due_jobs) with run_lock.py, in two child processes on one data directory")
    print_info("Tests: MP-001..002 — each due job once across the two, one report ok, the other not_due, never not_leader nor am_i_leader; the state written once per job and re-read inside the lock; the data directory's .scheduler.lock")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_multiprocess.py", test_names)
    return run_command(cmd, "Scheduler across processes tests", verbose=verbose)


def services_scheduler_loop(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler loop integration (due_* + state roundtrip, no real loop)."""
    print_section("Services: Scheduler Loop Integration")
    print_info("Testing: due_* functions with real SchedulerSettings/SchedulerState objects")
    print_info("Tests: SLO-001..003 — both jobs due, enabled flag, state serialization roundtrip")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_loop.py", test_names)
    return run_command(cmd, "Scheduler loop integration tests", verbose=verbose)


def services_scheduler_catchup(verbose: bool = False, test_names: list = None) -> bool:
    """Test the scheduler's catch-up on return and its shared lock: run_due_jobs and scheduler_loop (lot Z3)."""
    print_section("Services: Scheduler Catch-up and Lock")
    print_info("Testing: backend/app/services/platform/scheduler/scheduler.py (run_due_jobs, scheduler_loop), with sleep_wake/activity.py")
    print_info(
        "Tests: SCU-001..034 — constants, types, busy span, settle before clock and lock, a lock per event loop, short circuits in order, the lock across processes or the leader without fcntl (Z-11), off-loop I/O, jobs and outcomes, failures by class name, cancellation, status, blocked then caught up, the loop: listener, nudges, shutdown"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_catchup.py", test_names)
    return run_command(cmd, "Scheduler catch-up tests", verbose=verbose)


def services_scheduler_backoff(verbose: bool = False, test_names: list = None) -> bool:
    """Test the scheduler's retry of deferred items and its backoff after a job that raises (lot Z7b)."""
    print_section("Services: Scheduler Retry and Backoff")
    print_info("Testing: backend/app/services/platform/scheduler/scheduler.py (due_current_price, due_history_sync, run_due_jobs, JobOutcome)")
    print_info(
        "Tests: SBO-001..012 — next_attempt_at holds a job back, retry_at makes it due before its regular round, unreadable timestamps absent; a job or its save that raises: failure recorded and saved, backoff 60 s doubling to its cap, each job its own, reset by a run that ends; outcomes: items_deferred, retry_at"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_backoff.py", test_names)
    return run_command(cmd, "Scheduler retry and backoff tests", verbose=verbose)


def services_scheduler_price_refresh(verbose: bool = False, test_names: list = None) -> bool:
    """Test «Aggiornamento prezzi…»: the catch-up tracker PRICE_REFRESH, its wiring in run_due_jobs and scheduler_loop (lot Z5)."""
    print_section("Services: Scheduler Price Refresh")
    print_info("Testing: backend/app/services/platform/scheduler/scheduler.py (PriceRefreshTracker, PRICE_REFRESH, run_due_jobs, scheduler_loop), with sleep_wake/activity.py's response headers")
    print_info(
        "Tests: SPR-001..032 — names and types, idle/starting/running, announce and runs (first reason kept, overlap, no-op end, reset), jobs ran/refreshed, tick never shown; run_due_jobs: an unknown reason counts nothing, run_started before the settle, finished on raise and cancel, job_finished(None) on cancel; the loop: startup announced, header published then removed and reset, return announced on the request, the answers' header"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_price_refresh.py", test_names)
    return run_command(cmd, "Scheduler price refresh tests", verbose=verbose)


def services_brim_versioning(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIM provider versioning."""
    print_section("Services: BRIM Versioning")
    print_info("Testing: BRIM provider version detection and compatibility")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_versioning.py", test_names)
    return run_command(cmd, "BRIM versioning tests", verbose=verbose)


def services_config_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test config.get_data_dir test-mode/env-override branches and the LIBREFOLIO_PROFILE setting."""
    print_section("Services: Config Helpers")
    print_info("Testing: backend/app/config/__init__.py (get_data_dir, LIBREFOLIO_PROFILE)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_misc.py", test_names)
    return run_command(cmd, "Config helper tests", verbose=verbose)


def services_config_package(verbose: bool = False, test_names: list = None) -> bool:
    """Test the config package: env vars read only in backend/app/config/, section accessors keep their semantics."""
    print_section("Services: Config Package")
    print_info("Testing: backend/app/config/ (env reads, section accessors)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_package.py", test_names)
    return run_command(cmd, "Config package tests", verbose=verbose)


def services_config_secrets(verbose: bool = False, test_names: list = None) -> bool:
    """Test secrets given as NAME or NAME_FILE: precedence, file rules and errors, secrets set twice."""
    print_section("Services: Config Secrets")
    print_info("Testing: backend/app/config/__init__.py (env_secret, read_secret_file, secrets_set_twice)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_secrets.py", test_names)
    return run_command(cmd, "Config secrets tests", verbose=verbose)


def services_config_instance_key(verbose: bool = False, test_names: list = None) -> bool:
    """Test the instance key: HKDF-SHA256, key sources, first-use generation, never replaced, race between processes."""
    print_section("Services: Instance Key")
    print_info("Testing: backend/app/services/platform/instance_key.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_instance_key.py", test_names)
    return run_command(cmd, "Instance key tests", verbose=verbose)


def services_config_audit(verbose: bool = False, test_names: list = None) -> bool:
    """Test the startup configuration checks: states, no secret in results, startup stops on a broken configured secret."""
    print_section("Services: Configuration Checks")
    print_info("Testing: backend/app/services/platform/config_audit.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_audit.py", test_names)
    return run_command(cmd, "Configuration checks tests", verbose=verbose)


def services_plugin_secrets_check(verbose: bool = False, test_names: list = None) -> bool:
    """Test the startup check of the stored plugin secrets: its result, its log, never raising, no key generated (H-15)."""
    print_section("Services: Plugin Secrets Check")
    print_info("Testing: backend/app/services/platform/plugin_secrets_check.py (check_plugin_secrets, log_plugin_secrets_check)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_secrets_check.py", test_names)
    return run_command(cmd, "Plugin secrets check tests", verbose=verbose)


def services_config_env_example(verbose: bool = False, test_names: list = None) -> bool:
    """Test the .env.example guard: every variable read is documented, the uncommented lines unchanged."""
    print_section("Services: .env.example Guard")
    print_info("Testing: .env.example against backend/app/, Settings and the compose files")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_env_example.py", test_names)
    return run_command(cmd, ".env.example guard tests", verbose=verbose)


def services_config_brim(verbose: bool = False, test_names: list = None) -> bool:
    """Test LIBREFOLIO_BRIM_PREWARM: unset or blank follows the test mode, the on/off words, any other value an error."""
    print_section("Services: Config BRIM")
    print_info("Testing: backend/app/config/brim.py (brim_prewarm_enabled, BrimConfigError)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_config_brim.py", test_names)
    return run_command(cmd, "Config BRIM tests", verbose=verbose)


def services_profile_defaults(verbose: bool = False, test_names: list = None) -> bool:
    """Test the profile defaults of the settings: PROFILE_DEFAULTS, applied only to the fields nobody set (D5, F27)."""
    print_section("Services: Profile Defaults")
    print_info("Testing: backend/app/config/__init__.py (PROFILE_DEFAULTS, its Settings validator, LIBREFOLIO_FRAME_PROTECTION, LIBREFOLIO_CSP_REPORT_ONLY; ENVIRONMENT_PROFILE_DEFAULTS and profile_default(), H-17)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_profile_defaults.py", test_names)
    return run_command(cmd, "Profile defaults tests", verbose=verbose)


def services_request_float_inputs(verbose: bool = False, test_names: list = None) -> bool:
    """Test that every float a request can carry refuses infinity and NaN in its schema (H-32)."""
    print_section("Services: Request Float Inputs")
    print_info("Testing: every route of backend.app.main (iter_route_contexts): bodies, nested models, query, path, header and cookie parameters")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_request_float_inputs.py", test_names)
    return run_command(cmd, "Request float inputs tests", verbose=verbose)


def services_response_validation(verbose: bool = False, test_names: list = None) -> bool:
    """Test that a response breaking its model is logged without its content, and answered 500 (H-33)."""
    print_section("Services: Response Validation")
    print_info("Testing: backend/app/api/response_validation.py (install_response_validation_handler) and its install in backend/app/main.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_response_validation.py", test_names)
    return run_command(cmd, "Response validation tests", verbose=verbose)


def services_client_address(verbose: bool = False, test_names: list = None) -> bool:
    """Test the client address behind a trusted proxy: LIBREFOLIO_CLIENT_IP_HEADER, client_address and client_rate_key (P17); no function only for the tests (N58)."""
    print_section("Services: Client Address")
    print_info("Testing: backend/app/config/__init__.py (LIBREFOLIO_CLIENT_IP_HEADER), backend/app/services/platform/client_address.py (client_address, client_rate_key)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_client_address.py", test_names)
    return run_command(cmd, "Client address tests", verbose=verbose)


def services_plugin_settings_contract(verbose: bool = False, test_names: list = None) -> bool:
    """Test what a plugin declares to have settings, the values a field accepts, and what the core binds."""
    print_section("Services: Plugin Settings Contract")
    print_info("Testing: backend/app/services/plugin_settings/fields.py, contract.py, provider_registry.register")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_settings_contract.py", test_names)
    return run_command(cmd, "Plugin settings contract tests", verbose=verbose)


def services_plugin_settings_crypto(verbose: bool = False, test_names: list = None) -> bool:
    """Test the encryption of the secret plugin settings and the re-encryption a restore needs."""
    print_section("Services: Plugin Settings Encryption")
    print_info("Testing: backend/app/services/plugin_settings/crypto.py (AES-256-GCM, AAD, key id, rekey, key status)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_settings_crypto.py", test_names)
    return run_command(cmd, "Plugin settings encryption tests", verbose=verbose)


def services_plugin_settings_runtime(verbose: bool = False, test_names: list = None) -> bool:
    """Test the resolution of plugin settings and their delivery at the asset and FX call boundaries."""
    print_section("Services: Plugin Settings Resolution and Delivery")
    print_info("Testing: plugin_settings/resolver.py, runtime.py, assets/core.py (call_provider), fx/runtime.py (call_fx_provider)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_settings_runtime.py", test_names)
    return run_command(cmd, "Plugin settings runtime tests", verbose=verbose)


def services_plugin_settings_service(verbose: bool = False, test_names: list = None) -> bool:
    """Test the plugin settings catalogue and the all-or-nothing writes on a private database."""
    print_section("Services: Plugin Settings Service")
    print_info("Testing: backend/app/services/plugin_settings/service.py (read_catalogue, write_settings)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_settings_service.py", test_names)
    return run_command(cmd, "Plugin settings service tests", verbose=verbose)


def services_secret_masking(verbose: bool = False, test_names: list = None) -> bool:
    """Test the masking of the secrets a plugin call carries, in its errors and its log lines."""
    print_section("Services: Secret Masking")
    print_info("Testing: backend/app/utils/runtime/secret_masking.py and its wiring in logging_config.configure_logging")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_secret_masking.py", test_names)
    return run_command(cmd, "Secret masking tests", verbose=verbose)


def services_plugin_settings_guards(verbose: bool = False, test_names: list = None) -> bool:
    """Test the plugin settings guards: variables documented, derived names unique, AI Export never reads them."""
    print_section("Services: Plugin Settings Guards")
    print_info("Testing: registered declarations against .env.example, derived variable names, imports of services/ai_export/")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_plugin_settings_guards.py", test_names)
    return run_command(cmd, "Plugin settings guard tests", verbose=verbose)


def services_platform_readiness(verbose: bool = False, test_names: list = None) -> bool:
    """Test the readiness checks: database and migration codes, the head read once, no detail in the response."""
    print_section("Services: Instance Readiness")
    print_info("Testing: backend/app/services/platform/readiness.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_platform_readiness.py", test_names)
    return run_command(cmd, "Instance readiness tests", verbose=verbose)


def services_app_lifecycle(verbose: bool = False, test_names: list = None) -> bool:
    """Test the app's startup and shutdown steps and their runner, the middleware stack and the static site's routes."""
    print_section("Services: App Lifecycle")
    print_info("Testing: backend/app/services/platform/lifecycle.py, app_lifespan.py, middleware.py, static_site.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_app_lifecycle.py", test_names)
    return run_command(cmd, "App lifecycle tests", verbose=verbose)


def services_static_cache_policy(verbose: bool = False, test_names: list = None) -> bool:
    """Test the cache policy of the web app's files: hashed chunks immutable, the rest of /_app and the HTML revalidated (F28)."""
    print_section("Services: Static Cache Policy")
    print_info("Testing: backend/app/services/platform/static_site.py (the /_app mount, the HTML documents)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_static_cache_policy.py", test_names)
    return run_command(cmd, "Static cache policy tests", verbose=verbose)


def services_security_headers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the security headers every response carries: nosniff and Referrer-Policy, never overwritten (F15, D5)."""
    print_section("Services: Security Headers")
    print_info("Testing: backend/app/services/platform/security_headers.py (SecurityHeadersMiddleware), middleware.py (MIDDLEWARE_STACK), the app of backend/app/main.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_security_headers.py", test_names)
    return run_command(cmd, "Security headers tests", verbose=verbose)


def services_managed_headers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the headers of the managed profile: frame protection and the report-only CSP, read when the middleware is built (D5)."""
    print_section("Services: Managed Profile Headers")
    print_info("Testing: backend/app/services/platform/security_headers.py (SecurityHeadersMiddleware with LIBREFOLIO_FRAME_PROTECTION and LIBREFOLIO_CSP_REPORT_ONLY), on fresh apps with the stack's entries and the static site")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_managed_headers.py", test_names)
    return run_command(cmd, "Managed profile headers tests", verbose=verbose)


def services_backup_archive(verbose: bool = False, test_names: list = None) -> bool:
    """Test the instance backup archive: layout, consistent database copy, manifest, build and check."""
    print_section("Services: Instance Backup Archive")
    print_info("Testing: backend/app/services/platform/instance_backup/paths.py, snapshot.py, manifest.py, archive.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_archive.py", test_names)
    return run_command(cmd, "Instance backup archive tests", verbose=verbose)


def services_backup_jobs(verbose: bool = False, test_names: list = None) -> bool:
    """Test the instance backup jobs: background and foreground runs, one at a time, state on disk, retention."""
    print_section("Services: Instance Backup Jobs")
    print_info("Testing: backend/app/services/platform/instance_backup/jobs.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_jobs.py", test_names)
    return run_command(cmd, "Instance backup jobs tests", verbose=verbose)


def services_backup_staging(verbose: bool = False, test_names: list = None) -> bool:
    """Test the check of a backup archive for a restore, on a copy: refusals, upgrade of the copy, report, one at a time."""
    print_section("Services: Instance Backup Staging")
    print_info("Testing: backend/app/services/platform/instance_backup/staging.py, paths.py (the restore's folders)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_staging.py", test_names)
    return run_command(cmd, "Instance backup staging tests", verbose=verbose)


def services_backup_apply(verbose: bool = False, test_names: list = None) -> bool:
    """Test a checked restore confirmed, applied at the next start, committed or rolled back; the restart."""
    print_section("Services: Instance Backup Restore")
    print_info("Testing: backend/app/services/platform/instance_backup/apply.py, restart.py, paths.py (the restore's state and folders), app_lifespan.py (the two steps)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_apply.py", test_names)
    return run_command(cmd, "Instance backup restore tests", verbose=verbose)


def services_backup_outcome(verbose: bool = False, test_names: list = None) -> bool:
    """Test the outcome of a restore read with a one-time ticket, without a session (lot B5c)."""
    print_section("Services: Instance Backup Restore Outcome")
    print_info("Testing: backend/app/services/platform/instance_backup/outcome.py, paths.py (the ticket's file), schemas/backup.py (RestoreOutcome)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_outcome.py", test_names)
    return run_command(cmd, "Instance backup restore outcome tests", verbose=verbose)


def services_backup_totals(verbose: bool = False, test_names: list = None) -> bool:
    """Test the ledger's control totals of a backup: read read-only from a database file, compared at a restore's check."""
    print_section("Services: Instance Backup Ledger Totals")
    print_info("Testing: backend/app/services/platform/instance_backup/totals.py (ledger_totals_of, compare_totals)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_totals.py", test_names)
    return run_command(cmd, "Instance backup ledger totals tests", verbose=verbose)


def services_backup_envelope(verbose: bool = False, test_names: list = None) -> bool:
    """Test the envelope of a secure backup (.lfbk): scrypt and AES-256-GCM in chunks, its header, every tampering."""
    print_section("Services: Secure Backup Envelope")
    print_info("Testing: backend/app/services/platform/instance_backup/envelope.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_envelope.py", test_names)
    return run_command(cmd, "Secure backup envelope tests", verbose=verbose)


def services_backup_secure_rules(verbose: bool = False, test_names: list = None) -> bool:
    """Test the rules of a secure backup: its password (the accounts' rules, at least 12 characters) and the key it carries."""
    print_section("Services: Secure Backup Rules")
    print_info("Testing: backend/app/services/platform/instance_backup/secure.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_secure_rules.py", test_names)
    return run_command(cmd, "Secure backup rules tests", verbose=verbose)


def services_backup_secure(verbose: bool = False, test_names: list = None) -> bool:
    """Test a secure backup through the services: the job that encrypts it with the key, the check of an envelope, the secrets re-encrypted."""
    print_section("Services: Secure Backup")
    print_info("Testing: backend/app/services/platform/instance_backup/jobs.py, archive.py, staging.py, restore_jobs.py (lot B4)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_secure.py", test_names)
    return run_command(cmd, "Secure backup tests", verbose=verbose)


def services_backup_leftovers(verbose: bool = False, test_names: list = None) -> bool:
    """Test the startup cleanup of what killed runs left in clear (lot B4b, B-23, decision N66)."""
    print_section("Services: Backup Leftovers")
    print_info("Testing: backend/app/services/platform/instance_backup/leftovers.py, restore_jobs.py, jobs.py (lot B4b)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_leftovers.py", test_names)
    return run_command(cmd, "Backup leftovers tests", verbose=verbose)


def services_backup_checks(verbose: bool = False, test_names: list = None) -> bool:
    """Test the backup's configuration checks: the hosting panel's token and the restore's upload limit (lot B-9)."""
    print_section("Services: Backup Configuration Checks")
    print_info("Testing: backend/app/services/platform/instance_backup/checks.py, config_audit.py (BACKUP_CONFIG_CHECKS)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_backup_checks.py", test_names)
    return run_command(cmd, "Backup configuration checks tests", verbose=verbose)


def services_logging_access_filter(verbose: bool = False, test_names: list = None) -> bool:
    """Test the credential mask of uvicorn's request lines: the rule, the filter on any record, uvicorn's HTTP and WebSocket records, configure_logging installing it once on each logger and closing the handlers it removes."""
    print_section("Services: Credentials in uvicorn's Request Lines")
    print_info("Testing: backend/app/logging_config.py (mask_query_credentials, _QueryCredentialFilter, configure_logging)")
    print_info("Tests: the rule (decoded names, nested URL, encoded-value limit), every string arg masked in place, the message without args, format strings never rewritten, uvicorn's h11/httptools access and WebSocket handshake lines with negative controls, one filter per logger after two calls")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_logging_access_filter.py", test_names)
    return run_command(cmd, "Access log credential tests", verbose=verbose)


def services_donation_popup(verbose: bool = False, test_names: list = None) -> bool:
    """Test donation-popup trigger decision logic (should_show_donation_popup, record_login_and_maybe_show_popup)."""
    print_section("Services: Donation Popup")
    print_info("Testing: backend/app/services/accounts/donation_popup_service.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_donation_popup_service.py", test_names)
    return run_command(cmd, "Donation popup service tests", verbose=verbose)


def services_date_sentinel(verbose: bool = False, test_names: list = None) -> bool:
    """Test date sentinel resolution (min/max/passthrough, broker filter)."""
    print_section("Services: Date Sentinel Resolution")
    print_info("Testing: backend/app/services/platform/date_sentinel.py (resolve_date_sentinels)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_date_sentinel.py", test_names)
    return run_command(cmd, "Date sentinel tests", verbose=verbose)


def services_file_preview(verbose: bool = False, test_names: list = None) -> bool:
    """Test file preview service helpers (CSV/Excel/text detection)."""
    print_section("Services: File Preview Helpers")
    print_info("Testing: backend/app/services/files/file_preview.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_file_preview.py", test_names)
    return run_command(cmd, "File preview tests", verbose=verbose)


def services_fx_sync(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX pair-sync orchestration branches in services/fx/sync.py."""
    print_section("Services: FX Sync Orchestration")
    print_info("Testing: backend/app/services/fx/sync.py")
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
    print_info("Testing: backend/app/services/platform/scheduler/joblog.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_joblog_misc.py", test_names)
    return run_command(cmd, "Scheduler job log tests", verbose=verbose)


def services_scheduler_jobs(verbose: bool = False, test_names: list = None) -> bool:
    """Test the two scheduler job bodies end to end, with the bulk calls doubled."""
    print_section("Services: Scheduler Job Bodies")
    print_info("Testing: backend/app/services/platform/scheduler/jobs.py")
    print_info("Tests: _classify_job_status, run_current_price_refresh, run_history_sync")
    print_info("get_current_prices_bulk / bulk_refresh_prices / sync_pairs_bulk doubled — no provider calls, no price writes")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_jobs.py", test_names)
    return run_command(cmd, "Scheduler job body tests", verbose=verbose)


def services_scheduler_joblog_builders(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler job log entry builders and the append/rotate/read round trip."""
    print_section("Services: Scheduler Job Log Builders")
    print_info("Testing: backend/app/services/platform/scheduler/joblog.py")
    print_info("Tests: append/rotate/read round trip, build_current_price_entry, build_history_sync_entry, StrEnum guard")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_scheduler_joblog_builders.py", test_names)
    return run_command(cmd, "Scheduler job log builder tests", verbose=verbose)


def services_scheduler_settings_misc(verbose: bool = False, test_names: list = None) -> bool:
    """Test scheduler settings local-time-to-UTC conversion."""
    print_section("Services: Scheduler Settings TZ Conversion")
    print_info("Testing: backend/app/services/platform/scheduler/settings.py (_local_times_to_utc)")
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


def services_ai_export_pure(verbose: bool = False, test_names: list = None) -> bool:
    """Run the pure AI Export calculation contracts (no DB, no server, no network)."""
    print_section("Services: AI Export Pure Contracts")
    print_info("Testing payload invariants, temporal aggregators, observed FX math, and shared technical helpers")
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *AI_EXPORT_PURE_TEST_PATHS, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return run_command(cmd, "AI Export pure contract tests", verbose=verbose)


def services_ai_export_period_bounds(verbose: bool = False, test_names: list = None) -> bool:
    """Run the AI Export period bound (R13-SEC7-1): the period a snapshot hands its components (no DB, no network)."""
    print_section("Services: AI Export Period Bounds (R13-SEC7-1)")
    print_info("Testing: backend/app/services/ai_export/runtime_service.py (prepare_request, build_snapshot)")
    print_info("Tests: period end clamped to tomorrow, start to 100 years before it, extreme periods bounded fast")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_ai_export_period_bounds.py", test_names)
    return run_command(cmd, "AI Export period bound tests", verbose=verbose)


def services_provider_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Run the provider error-path contracts (no DB, no server, no network)."""
    print_section("Services: Provider Error Paths")
    print_info("Testing what happens when a price provider misbehaves: empty response, HTML instead of JSON,")
    print_info("missing field, unexpected date format, timeout, unknown ticker")
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", *PROVIDER_ERROR_TEST_PATHS, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return run_command(cmd, "Provider error-path tests", verbose=verbose)


def services_borsa_italiana_search(verbose: bool = False, test_names: list = None) -> bool:
    """Test Borsa Italiana provider search (single-fetch, IT+EN variants, ISIN hit)."""
    print_section("Services: Borsa Italiana Search")
    print_info("Testing: backend/app/services/asset_source_providers/borsa_italiana/plugin.py (search)")
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
    print_info("Testing: backend/app/services/assets/web_link_finder.py")
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


def services_tools_registry(verbose: bool = False, test_names: list = None) -> bool:
    """Test private Tool registry publication and read-only catalog projection."""
    print_section("Services: Tool Registry")
    print_info("Testing: private typed plugins, transactional discovery and catalog policies")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_tools_registry.py", test_names)
    return run_command(cmd, "Tool registry tests", verbose=verbose)


def services_tools_lifecycle(verbose: bool = False, test_names: list = None) -> bool:
    """Test owned Tool worker lifecycles in a separately authorized resource slot."""
    print_section("Services: Tool Lifecycle")
    print_info("Testing: real POSIX spawn, pipes, quotas, cancellation and descendant teardown")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_tools_executor.py", test_names)
    return run_command(cmd, "Tool lifecycle tests", verbose=verbose)


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
        #
        # That last sentence is the load-bearing claim, and it is a claim about
        # every unit, so any unit that breaks it must opt out with
        # `exclusive_because`. Three did, and only 8 workers exposed them: an
        # autouse fixture that truncates a whole shared table is not "its own
        # rows", and a unit that reads rows it seeded once per *module* loses
        # them to a neighbour that truncates once per *test*.
        default_isolation="write-scoped",
    )
    add_test(
        cat,
        "fx-conversion",
        services_fx_conversion,
        name="FX Conversion",
        desc="Currency conversion algorithms",
        prereq="Database created",
        exclusive_because="its assertions are about the oldest and newest EUR/USD row in the whole fx_rates table (backward fill, missing-rate boundary), and the service under test queries that table without a source filter, so a neighbour inserting any EUR/USD rate moves the boundary this unit measures",
    )
    add_test(
        cat,
        "pac-planner-core",
        services_pac_planner_core,
        name="PAC/Rebalancer Exact Core",
        desc="Canonical rational arithmetic, posting, fee, FX and tax primitives plus strict v2 normalization, exact model mapping, typed issue precedence and the engine's data boundary (no database, no planner source)",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-evaluator",
        services_pac_planner_evaluator,
        name="PAC/Rebalancer Exact Evaluator",
        desc="Exact policy views, Broker-qualified decisions, ledger replay, constraints, objectives and deterministic conflicts",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-oracle",
        services_pac_planner_oracle,
        name="PAC/Rebalancer Exhaustive Oracle",
        desc="Test-only referee: exhaustive candidate enumeration, domain-size estimation and cap, lexicographic best-candidate selection and checkpoint cancellation",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-policies",
        services_pac_planner_policies,
        name="PAC/Rebalancer Policy Compiler",
        desc="Scenario facts, hard constraint boundaries, objective cascade and scope guard over a compiled SCIP MIP",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-solver",
        services_pac_planner_solver,
        name="PAC/Rebalancer Lexicographic Solver",
        desc="Lexicographic SCIP cascade adapter: exhaustive-oracle agreement, stage scoping, evidence shape, honest limits and the first-stage infeasible verdict",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-proof",
        services_pac_planner_proof,
        name="PAC/Rebalancer Proof Semantics",
        desc="Sealed solver-status witnesses: optimal only when every stage closed, infeasible only at the first stage, limits and anomalies never proven",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-wire-numbers",
        services_pac_planner_wire_numbers,
        name="PAC/Rebalancer Wire Numbers",
        desc="Lossless exact-to-wire projection, canonical spelling, non-authoritative display and fail-closed envelope limits",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-report",
        services_pac_planner_report,
        name="PAC/Rebalancer Wire Projection",
        desc="Asset, action, ledger and exposure rows, exact exposure closure, tie-filtered solver evidence and proof projection",
        isolation="pure",
    )
    add_test(
        cat,
        "pac-planner-service",
        services_pac_planner_service,
        name="PAC/Rebalancer Plan Orchestration",
        desc="plan_pac_allocation end to end: ready states, failure availabilities, solver-status proofs, no domain enumeration, test-only oracle and SCIP import isolation",
        isolation="pure",
    )
    add_test(cat, "asset-source", services_asset_source, name="Asset Source", desc="Provider assignment, synthetic yield")
    add_test(cat, "asset-source-refresh", services_asset_source_refresh, name="Asset Source Refresh", desc="Bulk refresh orchestration smoke test")
    add_test(cat, "provider-registry", services_provider_registry, name="Provider Registry", desc="Registration, lookup, priority, fallback")
    add_test(cat, "quantlib-runtime", services_quantlib_runtime, name="QuantLib Runtime", desc="Pinned version, required APIs and seeded path reproducibility")
    add_test(cat, "risk-simulation", services_risk_simulation, name="Risk Simulation", desc="Serializable contracts, sampling, moments, chunking and cache")
    add_test(
        cat,
        "risk-asset-set",
        services_risk_asset_set,
        name="Risk Asset Set",
        desc="Five per-asset analytics for a weightless selection: one preparation per request whatever the number of codes, a set-level aggregate that the payload cannot express rather than one it declines to fill, and a required items list so an empty result and an absent key cannot read the same",
    )
    add_test(cat, "risk-optimization", services_risk_optimization, name="Risk Optimization", desc="Riskfolio objectives, estimators, constraints, frontier and cache")
    add_test(cat, "risk-workers", services_risk_workers, name="Risk Workers", desc="Spawn lifecycle, queue bounds, timeout, recycle and cancellation")
    add_test(cat, "risk-oracle", services_risk_oracle, name="Risk Metrics Oracle", desc="riskfolio/NumPy/SciPy reference pins, name traps, undefined windows and matrix consistency", isolation="pure")
    add_test(cat, "risk-all", services_risk_all, name="Risk Analysis", desc="Complete canonical-series, analytic, QuantLib, Riskfolio and worker suite, plus data-quality thresholds, translatable warnings, per-window eligibility/replay coverage and exclusion reasons")
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
    # Write-scoped (the category default): unique-name assets deleted with their prices; FX rows only on AMD/BDT, AMD/SZL,
    # AMD/LSL, BBD/BZD (MVR/SCR never seeded), pairs no other test uses, dated 1980-1987, wiped before and after.
    add_test(cat, "period-changes", services_period_changes, name="Period Changes", desc="MF-P2: 1D … 5Y asset and FX changes from stored data, equal to the Assets/FX pages' numbers; order, weekend 1D = 0, gaps")
    add_test(cat, "provider-contracts", services_provider_contracts, name="Provider Contracts", desc="ABC compliance for ALL registered providers")
    add_test(
        cat,
        "provider-policy",
        services_provider_policy,
        name="Provider Policy",
        desc="F21, where the asset providers stand in the search: LIBREFOLIO_ASSET_PROVIDERS_PREMIUM/ORDER read stripped, lowercased, in order, once each; effective tier and priority (declared, else the variables'; unknown codes dropped and warned once per process); search order premium first, then priority, ties and repeated codes as given (D-X3); search_rank; tier/search_priority checked at class definition; the non-streaming search answers provider by provider in that order",
        # PURE: no lane DB, no server, no network. Both variables are set with monkeypatch in this process; the registry
        # provider_policy sees and core.configured_provider are replaced by stand-ins; each search runs a query of its own.
        isolation="pure",
    )
    add_test(cat, "synthetic-yield", services_synthetic_yield, name="Synthetic Yield", desc="SCHEDULED_YIELD asset valuation; the accrual golden: every number of the accrual walk pinned (regen: LIBREFOLIO_TEST_REGEN_SI_ACCRUAL_GOLDEN=1)")
    add_test(cat, "synthetic-yield-integration", services_synthetic_yield_integration, name="Synthetic Yield Integration", desc="E2E scenarios (P2P, bond, mixed)")
    add_test(cat, "scheduled-investment-cost-bounds", services_scheduled_investment_cost_bounds, name="Scheduled Investment Cost Bounds", desc="R13-SEC7-2 (N73): late interest in closed form per date, bounded day counts, cache cap, horizon")
    # Pure: no lane DB, no server, no network; each test deletes its own process-local _CACHE entry before and after.
    add_test(cat, "scheduled-investment-min-start", services_scheduled_investment_min_start, name="Scheduled Investment Min Start", desc='MF-SI1: history from "min" = from the earliest value or manual event, as the explicit-start call', isolation="pure")
    # Pure: the plugin's date_type is swapped in-process for one with-block; each test deletes its own _CACHE entry.
    add_test(cat, "scheduled-investment-late-alignment", services_scheduled_investment_late_alignment, name="Scheduled Investment Late Alignment", desc="COMPOUND late interest: current value = history close = settlement = closed form, by str", isolation="pure")
    add_test(cat, "transaction", services_transaction, name="Transaction Service", desc="CRUD, balance validation, link resolution")
    add_test(
        cat,
        "transaction-cost-basis-rule",
        services_transaction_cost_basis_rule,
        name="Transaction Cost Basis Rule",
        desc="Which rows need a cost basis, read from TX_TYPE_METADATA; creates refused without one; updates held to it only when they change type, quantity or cost; notes/tags edits of rows stored without a cost commit",
    )
    add_test(
        cat,
        "transaction-decimal-places",
        services_transaction_decimal_places,
        name="Transaction Decimal Places",
        desc="C-97a: quantities keep 10 decimals; over a limit (quantity 10, cash and cost basis 6, 15 significant digits) refused at /validate and /commit on its row, never rounded; balances summed exactly; held set; BRIM parse does not refuse (D2)",
    )
    add_test(cat, "broker", services_broker, name="Broker Service", desc="CRUD, initial deposits, summaries")
    add_test(cat, "user-profile", services_user_profile, name="User Profile", desc="Username/email update, validation")
    add_test(
        cat,
        "account-tokens",
        services_account_tokens,
        name="Account Tokens",
        desc="issue/inspect/consume/revoke: hash only, one purpose, expiry at expires_at, single use under concurrency, the caller commits, no plaintext in logs; the pages of token_path are the API client's LINK_PAGES (A7b)",
        # PURE: every database is a private file under tmp_path built with create_all; no session on the lane DB, no
        # server. The concurrency test races two connections on that private file only.
        isolation="pure",
    )
    add_test(
        cat,
        "login-throttle",
        services_login_throttle,
        name="Login Throttle",
        desc="F15 (A8a): 10 failed sign-ins per identifier (A–Z folded) and 50 per address (IPv6 by /64) in 15 minutes; a refusal is not counted, a success forgets the identifier only, the longer wait wins; LIBREFOLIO_LOGIN_LIMIT=off records and refuses nothing",
        # PURE: module limiters replaced by fresh ones on an injected clock; no DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "accounts-checks",
        services_accounts_checks,
        name="Accounts Configuration Checks",
        desc="LIBREFOLIO_LOGIN_LIMIT (A8a): unset/on/off, any other value a ValueError; accounts.login_limit ok/warning/error in CONFIG_CHECKS; the startup audit stops on an invalid value before logging anything",
        # PURE: environment through monkeypatch, the audit's logger recorded; three fresh interpreters check the import
        # order, as email-checks does. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "registration",
        services_registration,
        name="Registration",
        desc="registration_mode in the registry, LIBREFOLIO_REGISTRATION/MAX_USERS/PUBLIC_URL/BILLING_URL accessors, effective mode, usage, invitations, register_user rule, limit under a race, bcrypt off the loop",
        # PURE: every database is a private file under tmp_path built with create_all; no session on the lane DB, no
        # server. The variables are set with monkeypatch in this process, and the once-per-process error log is checked
        # in this process too (the report cache cleared around each test); the race holds two connections to that
        # private file only.
        isolation="pure",
    )
    add_test(
        cat,
        "admin-bootstrap",
        services_admin_bootstrap,
        name="Initial Administrator (F02)",
        desc="LIBREFOLIO_ADMIN_* read and refused by code, the startup bootstrap (created, ignored, pending, rearmed, expired, two workers), the link logged once and emailed, complete_admin_setup, the waiting administrator in user_usage, user setup-link",
        # PURE: every database is a private file under tmp_path built with create_all; variables set with monkeypatch; the
        # email faked in this process; the race holds two connections to that private file only. No lane DB, no server.
        isolation="pure",
    )
    add_test(
        cat,
        "email-case",
        services_email_case,
        name="Email Addresses Regardless of Case (P18)",
        desc="email_fold and same_email fold A–Z only, the unique index on lower(email), lookups in any case, case variants refused on create and register, a case-only change of one's own address keeps sessions and verification, F02, the non-ASCII limit",
        # PURE: every database is a private file under tmp_path built with create_all; variables removed with monkeypatch.
        isolation="pure",
    )
    add_test(
        cat,
        "username-rules",
        services_username_rules,
        name="Username Rules (A-21a)",
        desc="No @ in a new username (user create, LIBREFOLIO_ADMIN_USERNAME), spaces, accents and punctuation still taken, legacy names left as they are; no address equal to another account's username, A–Z case aside (register_user, user set-email, user create)",
        # PURE: every database is a private file under tmp_path built with create_all; the command line runs in this
        # process on that file, get_async_engine a tripwire; variables removed with monkeypatch. No lane DB, no server.
        isolation="pure",
    )
    add_test(
        cat,
        "username-lookup",
        services_username_lookup,
        name="Username Lookup (A-21a)",
        desc="get_user_by_username_or_email: an address first, then the exact legacy name; without an @ a username only, exact, never an address; both orders of the rows",
        # PURE: every database is a private file under tmp_path built with create_all; get_async_engine a tripwire.
        isolation="pure",
    )
    add_test(
        cat,
        "password-policy",
        services_password_policy,
        name="Password Policy",
        desc="the five rules of a new password in one place: published in order (GET /system/instance), failed_rules in the policy's order, Unicode classes Lu/Ll/Nd and symbols, length in code points; lists made from them (rules=, rules_with_minimum_length: a minimum raised, never lowered, the rules read at each call), as a secure backup's password takes them",
        # PURE: a module of plain functions; no database, no server, no environment variable.
        isolation="pure",
    )
    add_test(
        cat,
        "email-config",
        services_email_config,
        name="E-mail Configuration",
        desc="LIBREFOLIO_SMTP_* accessors read at call time: blank is unset, three TLS modes with their default ports, port and hourly limit in ASCII digits, one mailbox for From and Reply-To (no CR/LF, no second address), the password through env_secret, EmailConfigError naming the variable and never the password",
        # PURE: no lane DB, no server; every LIBREFOLIO_SMTP_* is removed then set with monkeypatch, password files in tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "email-messages",
        services_email_messages,
        name="E-mail Messages",
        desc="EMAIL_LANGUAGES = default_language choices, email_language, keyword-only builders, http(s) links only, user values escaped in the HTML and absent from subjects, Babel durations, one more sentence for admin invites, catalogue guard (same keys and placeholders in en/it/fr/es, valid templates), compose_message headers, plain then HTML, exactly one recipient; every value shown on one line (control characters and line separators as spaces, bidirectional controls removed)",
        # PURE: no lane DB, no server, no environment read (inherited SMTP variables removed with monkeypatch); reads the committed templates only.
        isolation="pure",
    )
    add_test(
        cat,
        "email-delivery",
        services_email_delivery,
        name="E-mail Delivery",
        desc="Fake SMTP server self-checks; deliver: plain, AUTH, AUTH_FAILED, TLS_FAILED without fallback, CONNECTION_FAILED, TIMEOUT, refusals, non-221 QUIT is success; email_config_state never raises, one problem and variable per fault, logged once per process without the password; hourly budget on a fake clock; send_email off the event loop; no password, link or body in the logs; a blocked instance (LIBREFOLIO_BLOCKED, or unreadable) sends nothing, before any other check; sending_blocked",
        # PURE: no lane DB, no server; env set with monkeypatch; the fake SMTP server listens on an ephemeral 127.0.0.1 port.
        isolation="pure",
    )
    add_test(
        cat,
        "email-checks",
        services_email_checks,
        name="E-mail Configuration Checks",
        desc="email.smtp: off, ok, or error with problem and variable; email.smtp_encryption: ok unless plain text to a non-local host (warning); email.links: ok when email is not usable or links are ready, info without LIBREFOLIO_PUBLIC_URL, warning when it is not http(s) or no link can start from it; EMAIL_CONFIG_CHECKS (three); no password anywhere, no host, user or sender in a detail; config_audit.CONFIG_CHECKS ends with them, run_config_checks carries their results, either module imports first in a fresh interpreter; the startup audit logs an error, warnings, an info, nothing when off, never the password",
        # PURE: no lane DB, no server; every LIBREFOLIO_SMTP_* is removed then set with monkeypatch, password files in tmp_path; the
        # startup audit runs in test mode with its data directory in tmp_path, and so do the fresh interpreters of the import order.
        isolation="pure",
    )
    add_test(
        cat,
        "email-flows",
        services_email_flows,
        name="E-mail Flows",
        desc="account_language: the account's own language when it names one of the four (an unknown one counts as unset, like an empty one), else default_language, else English, the language column alone, never creating a user_settings row; supported_email_language; send_test_email: one message to the account's own address in its language, EmailUnavailableError and no connection when e-mail is off or unusable, EmailRecipientError (a ValueError) for an address that is not one address, the configuration and its password file read off the event loop; send_link_email: email, then links, then the token, then the recipient, an inactive account's reset link refused, exactly the PUBLIC_URL link, the token never logged; admit_forgotten_password: open as shipped (no hold since lot E4), per address keyed by H's client_rate_key, its one home (IPv6 by its /64, a mapped IPv4 as the IPv4, none without one), per identifier, the budget peeked; forgotten_password_work: per-account limits, an administrator's live link, per mailbox, the configuration read again before the link is made, a link made meanwhile rolled back, the new link revoked whatever stops the email, never raises, an unexpected error logged as its type alone; a blocked instance is refused first by every flow and makes no link",
        # PURE: every database is a private file under tmp_path built with create_all; no session on the lane DB, no
        # server; LIBREFOLIO_SMTP_* removed then set with monkeypatch; the fake SMTP server listens on an ephemeral 127.0.0.1 port.
        isolation="pure",
    )
    add_test(
        cat,
        "email-verification",
        services_email_verification,
        name="E-mail Verification",
        desc="verification_required (the global setting, off by default); links_can_go/ensure_verification_can_be_enabled (not blocked, email usable, links ready; read off the event loop); hold_for_verification: never the first account nor with the option off, EMAIL_VERIFICATION_UNAVAILABLE when no link can go, else inactive + a hold without address, 24 h, flushed not committed, its text never out; awaiting_verification: inactive + an unspent verification token; registration_email_work: a new link with the address replaces the hold, exactly build_verification in the account's language from LIBREFOLIO_PUBLIC_URL, nothing for an account that no longer waits or when no email can go, any failure after the commit leaves the token without its address (the account waits, nothing counted), never twice in 5 minutes, never raises; confirm_email: live links only, a token without address refused as revoked but left live, another address revoked, the account active and verified, its other tokens revoked, a link spent meanwhile consumed; resend_verification: per address (H's client_rate_key) before the password, the password as the login checks it, NOT_NEEDED/ACCOUNT_DISABLED before the configuration, per account on emailed links (5 min, 3/h), USER_LIMIT_REACHED for an expired link on a full instance (counted again inside the write), the budget, a link emailed meanwhile rolled back; per recipient mailbox (case-folded, across accounts) 3 an hour, a failed email not counted; an account that stopped waiting meanwhile gets no new link; a wrong password logged without what was typed; no token, password, identifier or address in the logs",
        # PURE: every database is a private file under tmp_path built with create_all, the option set in that file only; no
        # session on the lane DB, no server; LIBREFOLIO_SMTP_*, PUBLIC_URL, BLOCKED and MAX_USERS removed then set with
        # monkeypatch; the limiters are private on a fake clock; the fake SMTP server listens on an ephemeral 127.0.0.1 port.
        isolation="pure",
    )
    add_test(
        cat,
        "email-verification-hooks",
        services_email_verification_hooks,
        name="E-mail Verification Hooks",
        desc="user_usage counts an inactive account with a live verification link once (not expired, revoked or consumed; an active account once); register_user holds the account and the limit counts it, or rolls everything back on EMAIL_VERIFICATION_UNAVAILABLE (the invitation live); update_user_status revokes the verification links on a change of is_active, and on a deactivation of an account already inactive that waits (a regular inactive account unchanged), set_user_active either way (deactivating ends the wait); registration_email_allowed: 10 an hour per client address; holds_place/place_holders: inactive with a live link, now deciding; _refuse_what_cannot_turn_on: only require_email_verification off → on without an email with a link",
        # PURE: every database is a private file under tmp_path built with create_all; no session on the lane DB, no
        # server, no SMTP conversation; the email variables removed then set with monkeypatch; the loopback only resolves.
        isolation="pure",
    )
    add_test(
        cat,
        "email-links",
        services_email_links,
        name="E-mail Links",
        desc="links_state: LIBREFOLIO_PUBLIC_URL missing, invalid (not http(s), or no host, a space, a ? or #, a bad port, credentials, a bracket the parser cannot read; never echoed) or ready (spaces and one trailing slash removed, path prefix kept), read at each call, never raises; LinksState.instance = host with port; require_links; email_link = base + /reset-password or /invite + the token urlencoded in the fragment, nothing from a request; email_instance_config: available, and links only with email usable and links ready",
        # PURE: no lane DB, no server, no network; LIBREFOLIO_SMTP_* and LIBREFOLIO_PUBLIC_URL removed then set with monkeypatch.
        isolation="pure",
    )
    add_test(
        cat,
        "provider-cooldown",
        services_provider_cooldown,
        name="Provider Cooldown",
        desc="config.sleep_wake: LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS (ASCII digits, 0–86400, 0 = off, default 60) and _MAX_SECONDS (1–86400, default 3600) read at each call, blank is unset, SleepWakeConfigError with variable and code, a max below an enabled base refused; provider_cooldown: PROVIDER_COOLDOWNS read at call time, keys (domain, provider, scope), wait_before_call/record_refusal/record_success/record_no_verdict over check/refused/succeeded/released with base and max read at each refusal and retry_after passed on; the answers of calls in flight while a pause runs change nothing (five 429s at once count one refusal, a late success does not lift the pause); base 0 records and skips nothing; an invalid configuration never raises, works on 60/3600 and is logged once per (variable, code) per process",
        # PURE: no DB, no server; environment changed only through monkeypatch, process-local; the module instance
        # replaced by monkeypatch. The once-per-process log is read in a fresh interpreter of its own (sys.executable,
        # run in tmp_path, with a copy of this environment): no DB, no server there either.
        isolation="pure",
    )
    add_test(
        cat,
        "rate-limit-errors",
        services_rate_limit_errors,
        name="Rate-Limit Errors",
        desc="AssetRateLimitedError (an AssetSourceError, RATE_LIMITED) and FXRateLimitedError (an FXServiceError); a 429 of httpx or requests is a refusal with its Retry-After in seconds or as an HTTP date, None when absent or unreadable, any other status none; «status 429», «status code 429», «HTTP 429» or «HTTP Error 429» (a colon allowed) or the reason phrase «Too Many Requests» in a message is one, the texts of urllib, requests and httpx included, «4290» and «4291» never; raise_if_rate_limited raises from the error and passes a refusal through as it is; cooldown_scope None by default, the URL's host for the CSS scraper, None or a text for every provider; longest_refusal and raise_longest_refusal",
        # PURE: no DB, no server, no network; responses built in memory, the HTTP-date clock replaced in the cooldown
        # module only, with monkeypatch.
        isolation="pure",
    )
    add_test(
        cat,
        "rate-limit-boundaries",
        services_rate_limit_boundaries,
        name="Rate-Limit Boundaries",
        desc="call_provider and call_fx_provider with mockprov and MockFX: a refusal pauses for max(base, Retry-After) and leaves with that wait; while paused no operation reaches the plugin; after it one trial goes, a concurrent caller is refused, the answer ends the pause, another error or a cancellation frees the trial; pauses off call the plugin every time and keep its Retry-After; two CSS hosts pause apart, the plugin's scope applies when the caller has none, a broken or textless cooldown_scope means the whole provider (logged); test doubles bypass; a foreign or secret-bearing refusal leaves as a fresh, masked domain RATE_LIMITED error",
        # PURE: no DB, no server, no network (the CSS sites are an httpx.MockTransport). Each test replaces
        # PROVIDER_COOLDOWNS with a private Cooldowns on a fake clock and sets the pause variables and MockFX's class
        # attributes with monkeypatch: no pause outlives a test or reaches another unit of the same process.
        isolation="pure",
    )
    add_test(
        cat,
        "rate-limit-http-providers",
        services_rate_limit_http_providers,
        name="Rate-Limit HTTP Providers",
        desc="CSS scraper 429 → AssetRateLimitedError with Retry-After and the host as scope, other statuses HTTP_ERROR; ECB, FED, BOE and SNB 429 → FXRateLimitedError with Retry-After, other statuses unchanged; FED and BOE refuse the whole call with the longest Retry-After, ECB stops at the first refused currency and still skips other failures, SNB's currency map and data requests; an ECB 429 through call_fx_provider pauses ECB and the next call asks nothing",
        # PURE: no DB, no server, no network: each plugin module's httpx answers through an httpx.MockTransport,
        # replaced with monkeypatch; SNB's class-level currency map and the pause instance are put back after each test.
        isolation="pure",
    )
    add_test(
        cat,
        "rate-limit-results",
        services_rate_limit_results,
        name="Rate-Limit Results",
        desc="error_code RATE_LIMITED and retry_after on: the live current price (last known price kept, or the error item; no call while paused), the refresh result (FAILED with nothing stored, PARTIAL or OK with what came stored), the FX sync pair (FAILED or PARTIAL through a refused provider, the shortest wait; a fallback-served pair and a plain failure untouched; INFO, no traceback), each probe operation (on the result and in error_details), the search (providers_with_errors, INFO not a traceback, a cached query still answered) and its SSE provider_error event",
        # PURE: every database is a private file under tmp_path built with create_all and put in place of the process's
        # engine (db.session.async_engine) with monkeypatch; no session on the lane DB, no server. Pauses, MockFX's mode,
        # the registries' hand-outs and the plugin settings variables are monkeypatched per test; identifiers, queries
        # and FX date ranges are unique, so the process's provider caches answer for no other test.
        isolation="pure",
    )
    add_test(
        cat,
        "shutdown-budget",
        services_shutdown_budget,
        name="Shutdown Budget",
        desc="config.sleep_wake: LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS (0 = no limit, ASCII digits 2–600, default 8) read at call time, the drain max(1, budget*3//8), uvicorn_drain_env (a value set by hand wins, never raises); entrypoint.sh exports UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN under sh and dash; the runner's and Playwright's plain grace >= budget + 2 s; shutdown_budget: shutdown_budget_seconds never raises and logs once per process, ShutdownWatchdog arms once (re-entrant, one daemon thread) and fires once (ERROR log of step, threads and children, terminate_children(0.5), coverage saved only if measuring, flush, exit 1 even after a failing step), install_shutdown_watchdog only under uvicorn's Server.handle_exit on SIGTERM (a subclass's too; SIGINT wrapped only when uvicorn's; budget 0, another thread or any other SIGTERM handler, pytest's main thread included: nothing), the wrappers arm then call uvicorn's handler with (signum, frame), shutdown_deadline (an armed watchdog's less 0.75 s; otherwise clock + budget - drain at each call, never arming), the child-processes step terminates nothing without a watchdog, terminate_child_processes (terminate, timeout, kill, recursive, keep)",
        # PURE: no DB, no server, no lane port; environment only through monkeypatch; SIGTERM/SIGINT handlers saved and
        # restored around each test, never delivered (the wrappers are called directly); os._exit and the default
        # terminate_children replaced by recorders. Its subprocesses are `sh entrypoint.sh` runs and short-lived python
        # children of its own (fresh interpreters in tmp_path included), all reaped.
        isolation="pure",
    )
    add_test(
        cat,
        "shutdown-process",
        services_shutdown_process,
        name="Shutdown Budget in a Server Process",
        desc="A fixture app with the real lifecycle and shutdown_budget under the uvicorn CLI, LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=2 and UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=1: SIGTERM cancels a request in flight after the drain, cuts a shutdown step that never ends, kills a child that ignores SIGTERM, each within 6 s; SIGINT with a blocked non-daemon thread ends by the watchdog (status 1, 'Shutdown budget exhausted'); budget 0 runs a 4 s step to its end (status -SIGTERM, no watchdog); nothing pending exits within 3 s; app_lifespan: shutdown-watchdog first, child-processes last, shutdown_deadline from shutdown_budget",
        # PURE: its own server processes on a Unix socket of their own (in a short directory under /tmp: an AF_UNIX path
        # holds 104 bytes on macOS), data and logs in tmp_path; no lane port, no DB. Every process it starts — each server,
        # in a session of its own, with its process group — is killed if still running and reaped.
        isolation="pure",
    )
    add_test(
        cat,
        "sleep-wake-activity",
        services_sleep_wake_activity,
        name="Sleep and Wake Activity",
        desc="request_kind: the probes (system/health, ready, test-lane-health) and system/wake-sync under API_V1_PREFIX, trailing slashes ignored, then exact and case-sensitive, anything else user; Activity on an injected clock (time.time by default): request(presence) in flight for its whole body, an exception or a cancellation included, presence stamped at start and at end, return listeners at or below the silence called with it in registration order on the calling thread before the body (one that raises logged and skipped, a name registered again replaced, remove_return_listener: never called again, an unknown name a no-op, a blank one refused), presence=False only in flight, idle_seconds from started_at or the last user request and never below 0; busy(reason) nestable across threads, a blank reason refused; busy checks read at every call, true or raising = busy, a raising one warned once per streak; busy_reasons without duplicates; thread safety; current_activity read at call time; ActivityMiddleware: other scopes untouched, probes uncounted, wake-sync in flight without presence, any other path (a 404 included) presence and in flight through the last chunk of a stream and its background tasks, errors and cancellations propagate, current_activity read per request without activity=; activity the outermost entry of MIDDLEWARE_STACK",
        # PURE: no DB, no server, no lane port, no network; every Activity is the test's own, on a fake clock, and the
        # process's ACTIVITY is replaced only through monkeypatch; the FastAPI apps are built in the test and served in
        # this process by httpx.ASGITransport (no socket); its threads are daemon threads joined within a deadline.
        isolation="pure",
    )
    add_test(
        cat,
        "sleep-wake-suspend",
        services_sleep_wake_suspend,
        name="Sleep and Wake Suspend",
        desc="config.sleep_wake: LIBREFOLIO_IDLE_SUSPEND_MODE (unset/blank none; none or fly in any case, spaces around; else IDLE_SUSPEND_MODE_INVALID) and LIBREFOLIO_IDLE_SUSPEND_MINUTES (unset/blank 5; ASCII digits 1-1440; else IDLE_SUSPEND_MINUTES_INVALID), read at every call; FlySuspender: transport_factory (the one given, else httpx.AsyncHTTPTransport(uds=/.fly/api)), FLY_APP_NAME/FLY_MACHINE_ID read at each call (environ or os.environ), one POST http://flaps/v1/apps/<app>/machines/<id>/suspend without body or Authorization, the timeout on every phase, 2xx None, else SuspendError http_<status>, an httpx.HTTPError connection, a variable missing or blank not_on_fly before any request; IdleMonitor.check: waiting while the backoff runs (nothing touched), busy_reasons off the loop thread and any reason busy, active under minutes*60, else suspend (INFO Idle suspend requested), a failure backoff 30 doubling to 600 (bounds read at the call), one WARNING Idle suspend failed per streak, a success starts a new streak, any other exception reason error, never raising; exactly N*60 s suspends, N*60-1 does not; run: a check at once, sleep(IDLE_CHECK_SECONDS) after busy/active/waiting, at least RESUME_GRACE_SECONDS after suspended/failed, the stop (during a wait, during a check, before the start), a check that raises logged and the loop goes on; request_check: ends a wait early, from any thread, requests during a check make one check; start_idle_monitor returns None (none mode, an invalid one logged once: nothing; fly: FlySuspender(), busy checks tools and backup on current_activity(), a task, Idle monitor started; invalid minutes logged once, 5 used), globals read at the call, stop_idle_monitor returns the task, request_idle_check forwards from any thread, a fresh interpreter has none; never suspended while busy; wake.py calls request_idle_check(2.0) in the run's task after Wake-up run finished; app_lifespan: idle-monitor right after scheduler at startup, first at shutdown, late-bound, the startup step completes while the monitor runs",
        # PURE: no DB, no server, no lane port, no network. The Fly Machines API is an httpx.MockTransport, the socket's
        # transport class replaced on httpx by a recorder; every Activity is the test's own on a fake clock, the process's
        # ACTIVITY replaced through monkeypatch; the monitor runs on fake clocks with an injected sleep, its collaborators
        # replaced on its module; the wake-up is served in this process by httpx.ASGITransport with run_due_jobs replaced.
        # One fresh interpreter of its own, run to its end; checks held at a gate are released before each test ends.
        isolation="pure",
    )
    add_test(
        cat,
        "session-version",
        services_session_version,
        name="Session Version",
        desc="sv claim: SessionClaims round trip, no sv = version 0, untrusted tokens are None, get_current_user refuses another version, end_sessions, +1 by reset/deactivate/demote only, refusals change nothing; A-27: reset_password and a real address change revoke the live reset links, nothing else",
        # PURE: every database is a private file under tmp_path built with create_all; no session on the lane DB, no
        # server. The JWT secret and hash_password are replaced with monkeypatch, in this process only.
        isolation="pure",
    )
    add_test(
        cat,
        "address-probe",
        services_address_probe,
        name="Address Probe",
        desc="issue_probe_nonce/verify_probe_nonce: base64url(rand16 ‖ expiry_be8 ‖ HMAC-SHA256(derive_key('accounts.address-probe.v1'))), 120 s while expiry >= now, every altered, malformed, oversized, non-canonical or foreign nonce refused, hmac.compare_digest, never raises",
        # PURE: no lane DB, no server, no network; the instance key is set with monkeypatch and the data directory points
        # to tmp_path, where the generated keys of the «another instance» case live.
        isolation="pure",
    )
    add_test(
        cat,
        "account-deletion-preview",
        services_account_deletion_preview,
        name="Account Deletion Preview",
        desc="preview_user_deletion = what delete_user deletes (sole owner, two owners, owner over editor and viewer, editor/viewer only, inactive co-owner, mixed, no broker), transaction counts, transfers_unpaired both directions, writes nothing; delete_account: report files once after the commit, off the loop, not when nothing is deleted, nothing on failure; account_protection None",
        # PURE: every database is a private file under tmp_path, copied from one taken to head by the real migrations in a
        # child process (create_all lacks the ON DELETE CASCADE of broker_user_access that delete_user relies on); no session
        # on the lane DB, no server. The BRIM report directory is moved under tmp_path and the report cleanup replaced with
        # monkeypatch, in this process only.
        isolation="pure",
    )
    add_test(cat, "edge-cases", services_edge_cases, name="Transaction Edge Cases", desc="Decimal precision, currency validation, date edge cases")
    add_test(
        cat,
        "global-settings",
        services_global_settings,
        name="Global Settings",
        desc="Type conversion, DB reads, TTL getters",
        exclusive_because="an autouse fixture truncates global_settings before every test; that table holds registration_mode, which conftest seeds once per process, so a concurrent unit loses it mid-run and fails far from the cause",
    )
    add_test(
        cat,
        "fx-core",
        services_fx_core,
        name="FX Core Helpers",
        desc="normalize_rate, upsert/delete bulk, changes",
        exclusive_because="an autouse fixture truncates fx_rates before every test, so any concurrent unit reading rates loses them mid-test",
    )
    add_test(
        cat,
        "fx-catalog",
        services_fx_catalog,
        name="FX Provider Currency Catalog",
        desc="Supported currencies cached 24 h and handed out as copies, last known list on failure or timeout, 5-minute retry delay, one fetch per provider and event loop, listed in the cache panel",
        # PURE: fake providers only, no session and no server. The one shared surface is this process's
        # fx_provider_currencies cache and last known lists, which an autouse fixture empties before and after each test.
        isolation="pure",
    )
    add_test(cat, "static-uploads", services_static_uploads, name="Static Uploads", desc="File save/list/get/delete, security")
    add_test(cat, "brim-parse-error", services_brim_parse_error, name="BRIM Parse Error", desc="Exception class tests")
    add_test(
        cat,
        "brim-parse-pool",
        services_brim_parse_pool,
        name="BRIM Parse Pool",
        desc="Process-pool off-loading, pickle round-trip, thread fallback; W-B53: workers born from a forkserver preloaded with the BRIM module, its plugins and the discovery (brim_parse_preload, whose import never raises), started early by prewarm() (never raises, the pool stays lazy), importing the pool stays light",
    )
    add_test(cat, "brim-parse-race", services_brim_parse_race, name="BRIM Parse Race", desc="Parse survives the uploaded→parsed rename; genuine read errors still fail")
    add_test(cat, "settings", services_settings, name="Settings Service", desc="User settings CRUD, get_effective_base_currency")
    add_test(cat, "current-price-bootstrap", services_current_price_bootstrap, name="Current Price Bootstrap", desc="OHLC widening helper (F.2/F.3)")
    add_test(cat, "scheduled-investment-param-change", services_scheduled_investment_param_change, name="Scheduled Investment Param Change", desc="Symmetric wipe on provider_params change")
    add_test(cat, "brim-provider-base", services_brim_provider_base, name="BRIM Provider Base", desc="Abstract base defaults + text-encoding fallback")
    add_test(cat, "brim-report-sets", services_brim_report_sets, name="BRIM Report Sets", desc="Report-set schemas, contract defaults, combined-file storage")
    add_test(cat, "brim-gap-fix", services_brim_gap_fix, name="BRIM Gap-fix", desc="Gap-fix: bank truth points vs LibreFolio state, proposals and verifications")
    add_test(cat, "brim-create-transaction", services_brim_create_transaction, name="BRIM Create Transaction", desc="_create_transaction + _loc_to_field")
    add_test(
        cat,
        "financial-math",
        services_financial_math,
        name="Financial Math",
        desc="Average cost, native cash, returns and periods, the ledger control totals: movements, conversions through the FX service, diagnostics; boundaries of the whole layer, the day-count primitives' one home",
        # PURE: each module's only I/O is convert_bulk, which every test replaces on its
        # module with a double; the session handed to it is None or a sentinel, or, for the
        # ledger control totals, one on a private SQLite file under tmp_path that no other
        # test reads. The layer guard only parses source files.
        isolation="pure",
    )
    add_test(cat, "roi-fifo-utils", services_roi_fifo_engine, name="ROI/FIFO/Portfolio Utils", desc="TWRR/MWRR/SimpleROI series, FIFO lots (FifoLotEngine), WAC multi-broker, price marks")
    add_test(
        cat,
        "orphan-transfer-numbers",
        services_orphan_transfer_numbers,
        name="Orphan Transfer Numbers",
        desc="Lots and Dashboard once a broker deletion leaves the other half of a TRANSFER: the orphan against an ADJUSTMENT-in control",
        # The file sits in test_financial/, which roi-fifo-utils runs whole: the derived "all"
        # skips this action so that the file runs once there.
        in_all=False,
    )
    add_test(
        cat,
        "lone-transfer-legs",
        services_lone_transfer_legs,
        name="Lone Transfer Legs",
        desc="Decision 47: the lone giving TRANSFER legs a broker deletion left before 1.3, handed over at their own broker's Auto cost — a missing conversion leaves the leg, dry run, second run, the startup step after post-migration-fixes, the offline script's lines and exit code",
        # The category default (write-scoped), although every database is a private file under tmp_path built by the
        # real migrations: the startup wrapper's cases make such a file's engine the configured one, and a wrapper that
        # reached the lane's engine all the same would open a session there — through a double that writes nothing.
    )
    add_test(
        cat,
        "portfolio-allocation-source",
        services_portfolio_allocation_source,
        name="Portfolio Allocation Source",
        desc="Read-only exact planner facts, authorization boundaries, provenance and saved evidence",
        isolation="pure",
    )
    add_test(
        cat,
        "lots-analysis-pure",
        services_lots_analysis_pure,
        name="Lots Analysis Pure Builders",
        desc="SHORT lots, estimated_mode, price gaps, ADJUSTMENT cost basis, transfer scope, FX resolver, reference price and days at cost",
        # PURE: no database, server or network. The builders under test are sync methods that take all
        # of their inputs as arguments, so the service is built with db=None; the async cases stub
        # convert_bulk, and the reference-price and at-cost cases drive get_lots_analysis on loader
        # doubles and a session double, all in EUR, so no rate is asked and nothing reaches a database.
        # Kept out of the DB-backed lots units on purpose: folding it in would declass it to the
        # category default (write-scoped).
        isolation="pure",
    )
    add_test(
        cat,
        "asset-source-guards",
        services_asset_source_guards,
        name="Asset Source Guards",
        desc="bulk_upsert_prices OHLC policy, close-only widening, identifier filters, event FX conversion",
        # WRITE_GLOBAL: Asset, PriceHistory and AssetEvent carry no user_id, so the
        # asset this unit creates and every price/event row written against it are
        # visible to all concurrent tests. Rows are uniquely named and dropped in
        # teardown, but the tables themselves are shared surfaces.
        isolation="write-global",
    )
    add_test(
        cat,
        "asset-event-store",
        services_asset_event_store,
        name="Asset Event Store",
        desc="Manual events: type normalisation, all-or-nothing upsert with located errors, create mode, event_ids, delete scoped by asset, a SPLIT retype refused while a linked incoming adjustment has no cost (P-10)",
        # WRITE_GLOBAL: Asset and AssetEvent carry no user_id (nor do the AssetProviderAssignment,
        # Broker and Transaction written beside them), so the two assets this unit creates and
        # every event and transaction written against them are visible to all concurrent tests.
        # Rows are uniquely named and dropped in teardown, but the tables are shared surfaces.
        isolation="write-global",
    )
    add_test(
        cat,
        "asset-digit-limits",
        services_asset_digit_limits,
        name="Asset Digit Limits",
        desc="C-97a: a manual price whose open/high/low/close exceeds 12 decimals or 15 significant digits refused (ValueError naming the asset, the maximum and the dates) before anything of the call is written, for every asset and every chunk; the -1 sentinel, trailing zeros and values at the limits accepted; a provider price truncated (12 decimals, 15 significant digits, ROUND_DOWN) and stored; a manual event beyond 6 decimals or 15 significant digits refused with EVENT_TOO_MANY_DIGITS (HTTP 400), nothing written; what fits read back exactly and in today's form",
        # WRITE-SCOPED, the category default, as asset-source: every row is this unit's own -- two assets
        # created under a unique name, and only their prices and events, written, read and wiped by asset id.
        # Nothing here counts or reads a row it did not write.
    )
    add_test(
        cat,
        "current-price-storable",
        services_current_price_storable,
        name="Current Price Storable",
        desc="X-R40 + W-B62: a current quote no price column keeps (storable_price None: 1E+50000000, 1E+60, 1E-13, a float inf) never served nor cached -- the item falls back to the latest stored close that reads a number (db:last_known) or to an error, the next call asks the provider again -- and its refusal logged once per (asset, provider, value), never at every poll; a valid quote served and cached as the database keeps it (65432.1234567890999 -> 65432.123456789), one that already fits served in its own form; a refresh leaves out of changed_points a date no column keeps, and neither caches nor stores nor announces an unstorable current value, while it caches a valid one as stored; the database fallback passes over a close that reads None and never raises",
        # WRITE-SCOPED, the category default, as asset-digit-limits: every row is this unit's own -- two assets
        # created under a unique name, and only their prices, events and provider assignment, written, read and
        # wiped by asset id. The provider codes are unique per test, so the current-value cache entries and the
        # log-once keys are the test's own; the cache's set is patched for one test only (monkeypatch).
        # Nothing here counts or reads a row it did not write.
    )
    add_test(
        cat,
        "event-split-ratio",
        services_event_split_ratio,
        name="Event Split Ratio",
        desc="X-R47: a manual SPLIT whose ratio is not valid (0, -2, -0.000001) refused with EVENT_INVALID_SPLIT_RATIO before anything of the request is written -- new (upsert or create), upserted on the key of a stored SPLIT, edited by id, or turned into a SPLIT by an edit -- its details naming the item and every offending event (event_index, date, type), HTTP 400 with each ratio as sent; a provider's SPLIT with an invalid ratio dropped by _upsert_asset_events (a stored SPLIT on its key kept), the other events written, one warning naming it and the asset; valid ratios (2, 0.5, 1.5, 0.000001) accepted manual in every way or from a provider, other event types of 0 and a SPLIT edited into a DIVIDEND of 0 accepted. R13-SEC7: given the caller (current_user_id, which POST /assets/events passes), the P-10 refusal EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST lists only the costless adjustments on a broker the caller holds an access to and counts the others in hidden_transactions_count, the message unchanged, nothing written; X-R47b: without a caller it names none and counts them all (fail closed). The split predicate financial_math.splits.is_split_event_type (rule d of the layer boundaries): the member and text reading SPLIT in any case, blanks around ignored, are a split; anything else, None and non-text included, is not, and it never raises",
        # WRITE-SCOPED, the category default, as asset-digit-limits: every row is this unit's own -- two assets
        # created under a unique name, the first assigned to a provider code of the unit's own that no provider has,
        # two users and two brokers under the same marker with one access each, and only the events of those assets
        # and the transactions on those brokers, written, read and wiped by asset and broker id; the log capture is the
        # test's own (structlog's testing capture, proved live by a barrier event); the route runs in process on an app
        # of the call's own, get_current_user overridden there and never on the shared app. Nothing here counts or
        # reads a row it did not write.
    )
    add_test(cat, "portfolio-engine", services_portfolio_engine_vnext, name="Portfolio Engine vNext", desc="Inline WAC, last_buy_price, 3-pool, position states, accumulators, one replay from the first movement")
    add_test(cat, "asset-sync-counts", services_asset_sync_counts, name="Asset Sync Counts", desc="Asset sync count tracking")
    add_test(cat, "brim-versioning", services_brim_versioning, name="BRIM Versioning", desc="Provider version detection and compatibility")
    add_test(
        cat,
        "scheduler-state",
        services_scheduler_state,
        name="Scheduler State",
        desc="Load/save/atomic write, corrupt/partial JSON recovery; the fields of lot Z7b (last_items_deferred, retry_at, consecutive_failures, next_attempt_at) saved, defaulted in an older file, a newer file's unknown keys ignored",
    )
    add_test(cat, "scheduler-settings", services_scheduler_settings, name="Scheduler Settings", desc="_parse_times, _parse_days pure functions")
    add_test(cat, "scheduler-due", services_scheduler_due, name="Scheduler Due-Check", desc="due_current_price + due_history_sync edge cases; a missed slot of a configured day in the last 7 days is due once a run exists (D-Z3-1)")
    add_test(cat, "scheduler-leader", services_scheduler_leader, name="Scheduler Leader Election", desc="Mock psutil, multi-worker, Docker PID1, --reload, exception safe")
    add_test(
        cat,
        "scheduler-run-lock",
        services_scheduler_run_lock,
        name="Scheduler Lock Across Processes",
        desc="Z-11 (N71), run_lock.py: scheduler_run_lock(path) waits while another process holds the lock (each attempt LOCK_EX | LOCK_NB in a thread, POLL_SECONDS apart) and runs the block once it lets go or is SIGKILLed; a cancelled wait goes through, never runs the block, and leaves no descriptor nor lock, an attempt in flight that took it included; released on an exception (another process takes it at once); the file created 0o600 with its folder and never deleted; a symbolic link refused at once with OSError, nothing behind it created or locked; open/flock/close never on the event loop's thread; LOCK_FILE_NAME .scheduler.lock, POLL_SECONDS 0.2, cross_process_lock_available() with fcntl (false with fcntl None or not importable), run_lock_path() the data directory's, read at the call",
        # PURE: no DB, no server, no lane port, no network. Every lock file lives under the test's tmp_path, and an autouse
        # fixture points the data directory (LIBREFOLIO_TEST_DATA_DIR) there too, for the test and its children: no
        # .scheduler.lock reaches the lane's. The other processes are real child interpreters the test starts (a holder of the
        # lock, a one-shot probe), coordinated by files under tmp_path against deadlines of their own; each holder gives up
        # by itself, and every child is killed and reaped in a finally.
        isolation="pure",
    )
    add_test(
        cat,
        "scheduler-multiprocess",
        services_scheduler_multiprocess,
        name="Scheduler Across Two Processes",
        desc="Z-11 (N71): two real processes call run_due_jobs('wake') at once on one data directory, both jobs due and am_i_leader answering yes: each job runs once across the two, in the process that took the lock first (both ok), the other finds both not_due; neither reports not_leader, neither asks am_i_leader; the state file holds each last_run_at written once, the second process loaded it inside the lock; the lock file is the data directory's .scheduler.lock",
        # PURE: no DB, no server, no lane port, no network. The two processes are child interpreters the test starts, their
        # LIBREFOLIO_DATA_DIR a folder of tmp_path (test mode off, no switch nor coverage variable inherited): the state file
        # and the lock file are real, both under tmp_path. Settings, jobs and the leader are patched in each child's memory;
        # both are killed and reaped in a finally.
        isolation="pure",
    )
    add_test(cat, "scheduler-loop", services_scheduler_loop, name="Scheduler Loop Integration", desc="due_* + state roundtrip, no real loop")
    add_test(
        cat,
        "scheduler-catchup",
        services_scheduler_catchup,
        name="Scheduler Catch-up and Lock",
        desc="run_due_jobs: an unknown reason refused before anything; busy 'scheduler' from start to end (settle and lock wait included, also on an exception or a cancellation); return/wake settle the clock before the due checks and before the lock; one asyncio.Lock per event loop (no overlap, the second run loads what the first saved, two loops in a row); under the lock disabled, blocked, setting off, in order, without loading the state; with fcntl the lock across processes (Z-11, N71) entered after the setting, the leader never asked, the state and the clock read inside it, a lock that cannot be taken raising before the state loads; without fcntl the leader instead (not_leader); the lock or am_i_leader, load_state and save_state off the loop; one now for both due checks; jobs in order, each saved, outcomes copied from JobState; a job or a save raising is an error outcome by class name only, logged, the next job runs; report status ok/partial/error; blocked runs nothing, then the missed slot is caught up (D-Z3-4, D-Z3-1). scheduler_loop: disabled registers nothing; listener scheduler-catch-up at 60 s; startup after the first delay or a nudge; tick or return; a nudge from any thread; two nudges, one run; a failing run logged; shutdown ends it and removes the listener",
        # PURE: no DB, no server, no lane port, no network. Every collaborator of run_due_jobs (switches, leader, settings, state
        # store, jobs, due functions, utc_now, settle_clock) is a fake set with monkeypatch; the process's ACTIVITY is replaced
        # only through monkeypatch by an Activity on a fake clock. The loop runs as a task of the test's own event loop, against
        # a recorder in place of run_due_jobs, and is stopped and awaited within a deadline; its worker threads are asyncio's.
        isolation="pure",
    )
    add_test(
        cat,
        "scheduler-backoff",
        services_scheduler_backoff,
        name="Scheduler Retry and Backoff",
        desc="Lot Z7b. Due rules first: next_attempt_at ahead holds a job back (even past its retry_at or an overdue round), else retry_at reached makes it due before its regular round (a history sync deferred at 23:00 retries at 23:0x), else today's rule; unreadable timestamps absent. run_due_jobs: a job that raises keeps its previous JobState (last_run_at too) with consecutive_failures+1, next_attempt_at now+backoff, error by class name, saved and logged; a save that raises after the job records it on the job's fresh JobState; backoff 60 s doubling, capped at 1 h for history and at the price frequency for the price; each job its own; a run that ends resets. JobOutcome items_deferred and retry_at: copied, next attempt of a failure, pending time of a job not due, whatever the reason",
        # PURE: no DB, no server, no lane port, no network. The due functions are called as they are; for run_due_jobs every
        # other collaborator (switches, leader, settings, state store, jobs, utc_now, settle_clock) is a fake set with
        # monkeypatch, the state store in memory, and the process's ACTIVITY is replaced only through monkeypatch by an
        # Activity on a fake clock. Nothing sleeps: every moment is a fake wall clock's.
        isolation="pure",
    )
    add_test(
        cat,
        "scheduler-price-refresh",
        services_scheduler_price_refresh,
        name="Scheduler Price Refresh",
        desc="Lot Z5, «Aggiornamento prezzi…» (N-Z5-1…5). PriceRefreshTracker on an injected clock: idle (all None, not refreshed, no header); announce(reason) idle → starting with reason and since, first reason and since kept while pending; tick or unknown reasons refused for announce and run_started, nothing counted; run_started counts overlapping runs, run_finished ends the catch-up with the last one (no-op without a counted run): last_finished_at and last_refreshed (a job with items_ok > 0) only if a job finished while pending, else kept; a cancelled job (None) ran, not refreshed; a job while idle invisible; running with the current job (a tick's job at once on an announced return), starting without; header_value; reset forgets the count and the job. run_due_jobs: catch-up reasons run_started before the settle and run_finished in a finally (raise, cancel), a tick never; job_started/job_finished around each job. scheduler_loop: startup announced, X-LibreFolio-Price-Refresh registered on current_activity(), the return listener announces on the request's thread, removed and reset at the end; the answers through ActivityMiddleware say starting, running, then nothing",
        # PURE: no DB, no server, no lane port, no network. Every collaborator of run_due_jobs past PRICE_REFRESH (switches,
        # leader, settings, state store, due functions, jobs, settle_clock) is a fake set with monkeypatch; the process's
        # PRICE_REFRESH is reset before and after each test, and its ACTIVITY replaced only through monkeypatch by an
        # Activity on a fake clock. The loop runs as a task of the test's own event loop and is stopped and awaited within
        # a deadline; the FastAPI app of the header case is served in this process by httpx.ASGITransport (no socket).
        isolation="pure",
    )
    add_test(
        cat,
        "scheduler-jobs",
        services_scheduler_jobs,
        name="Scheduler Job Bodies",
        desc="_classify_job_status, run_current_price_refresh, run_history_sync (bulk calls doubled); lot Z7b: RATE_LIMITED items deferred whatever their status or value, retry_at at the shortest pause, a run that ends resets the failure backoff, deferred marks and counters in the job log",
        # READ, not write-global: the three bulk entry points that rewrite prices for
        # every active asset and every FX route are replaced by doubles, so only the
        # two SELECTs reach the shared DB. The job log is redirected to a per-test
        # sandbox dir, and jobs.py mutates the SchedulerState object it is handed
        # without ever calling save_state(), so nothing global is written.
        isolation="read",
    )
    add_test(cat, "config-misc", services_config_misc, name="Config Helpers", desc="get_data_dir test-mode/env-override branches, LIBREFOLIO_PROFILE validation")
    add_test(cat, "config-package", services_config_package, name="Config Package", desc="Env vars read only in backend/app/config/, section accessors keep their semantics", isolation="pure")
    add_test(cat, "config-secrets", services_config_secrets, name="Config Secrets", desc="NAME / NAME_FILE secrets: precedence, file rules and errors, secrets set twice", isolation="pure")
    add_test(cat, "config-instance-key", services_config_instance_key, name="Instance Key", desc="HKDF-SHA256 (RFC 5869), key sources, first-use generation 0700/0600, never replaced, race between processes", isolation="pure")
    add_test(cat, "config-audit", services_config_audit, name="Configuration Checks", desc="Startup configuration checks: states, no secret in results, startup stops on a broken configured secret", isolation="pure")
    add_test(
        cat,
        "plugin-secrets-check",
        services_plugin_secrets_check,
        name="Plugin Secrets Check",
        desc="H-15: platform.plugin_secrets ok without unreadable system secret, else error with detail {count: system} only, the user count nowhere; at startup ok logs nothing, not ok logged at its severity, an exception of the status one warning naming its class, never raising; on a private DB without stored secret nothing logged and no key file generated",
        # The status is a stub on an engine never opened, or the real one on a private SQLite file under tmp_path put in
        # place of get_async_engine; the data directory in tmp_path, the key variables removed by monkeypatch. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(cat, "config-env-example", services_config_env_example, name=".env.example Guard", desc="Every variable read is documented in .env.example; uncommented lines unchanged", isolation="pure")
    add_test(cat, "config-brim", services_config_brim, name="Config BRIM", desc="LIBREFOLIO_BRIM_PREWARM (N56): unset or blank follows the test mode; 1/true/yes/on, 0/false/no/off in any case, stripped; else a BrimConfigError naming it; read at each call", isolation="pure")
    add_test(
        cat,
        "profile-defaults",
        services_profile_defaults,
        name="Profile Defaults",
        desc="D5/F27: PROFILE_DEFAULTS has one entry per profile LIBREFOLIO_PROFILE accepts; selfhosted lists nothing, managed lists RISK_SIMULATION_IDLE_TIMEOUT_SECONDS and RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS at 60.0, LIBREFOLIO_FRAME_PROTECTION and LIBREFOLIO_CSP_REPORT_ONLY True (two new booleans, False in the code); managed gives its value to every field nobody set, a value set in the environment or in .env wins (600 the code default, 0, false) and the other fields keep theirs; selfhosted, unset or explicit, keeps the code default of every field any profile lists (parametrised over the union of the tables); every entry a Settings field with a code default and a value valid in strict mode; MANAGED and ' Managed ' read as managed; H-17: ENVIRONMENT_PROFILE_DEFAULTS has one entry per profile, selfhosted empty, managed equal to the decided table with exact types (LIBREFOLIO_BACKUP_MAX_UPLOAD_MB 500), no Settings field among its keys, every key read by a section module and documented in .env.example; profile_default() gives the fallback itself under selfhosted and the table's value under managed, the profile read at each call; H-27: an entry not of the very type of the reader's literal fallback raises ProfileDefaultError (a TypeError naming the variable, the profile, both types and the table), None for the upload limit stops backup_max_upload_mb(), and the sources' profile_default(NAME, literal) calls are checked against every profile's entries; H-37 (E, R13-SEC7): under any profile but selfhosted a variable the profile does not list raises ProfileDefaultError instead of the self-hosted fallback (fail closed), the upload limit's managed entry removed stops its reader while selfhosted keeps 0, every call's variable is listed by every profile but selfhosted (guard and self-test), and an entry equal to its reader's own default is fine",
        # Settings built from the environment alone (_env_file=None), the variables set and removed by monkeypatch; the
        # .env case writes its own file under tmp_path and turns test mode off for that call. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "request-float-inputs",
        services_request_float_inputs,
        name="Request Float Inputs",
        desc="H-32: every float a request can carry (body, nested model, query, path, header, cookie) refuses inf, -inf, NaN and 1E+400 in its schema; barriers on the number of routes walked",
        # The app is imported, never served: its routes are walked with iter_route_contexts and each float judged with a
        # TypeAdapter. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "response-validation",
        services_response_validation,
        name="Response Validation",
        desc="H-33: a response that breaks its response_model is logged with its route, endpoint, error types and locations, never its content, and answered 500 in plain text",
        # Fresh FastAPI apps in process, and the real app's handler table; logs captured with structlog. No DB, no server.
        isolation="pure",
    )
    add_test(
        cat,
        "client-address",
        services_client_address,
        name="Client Address",
        desc="P17: LIBREFOLIO_CLIENT_IP_HEADER a str, '' in the code, stripped, empty or blank unset, a header token kept as written (case kept), anything else (space, colon, slash, comma, tab or line break inside, quotes, '=', non-ASCII letter or digit) refused naming the variable, X-Forwarded-For and Forwarded in any case refused naming FORWARDED_ALLOW_IPS too, listed by no profile and '' under every one, managed included; client_address(connection), Request and WebSocket alike: unset the peer exactly as it is (None without a client) and no header read; set, the name matched whatever its case, one line of one IP address normalised (IPv4-mapped as its IPv4, IPv6 compressed, lower case), absent the peer without a warning, malformed (two lines even valid, a list, a port, brackets, a zone, a leading zero, empty or blank, text, a space inside, a network) the peer and one warning per process, word for word, with header (lower case), lines and length only, the value and the address inside it in no log record; the name read once per process, the warning once too (a test starts both over as a new process: the cache of _configured_header cleared, _warned emptied, N58); client_rate_key (IPv4 as is, IPv4-mapped as its IPv4, IPv6 by its /64, a zone ignored, a name as written, no key for None or ''); neither reset_client_address_cache nor mask_client_address in the module (H-22)",
        # PURE: Settings built from the environment alone (_env_file=None), or read through get_settings() in test mode with
        # a data directory under tmp_path, every variable set and removed by monkeypatch; connections are Starlette Request
        # and WebSocket objects on raw scopes; the module's logger is replaced by a recorder, and its cache is reset before
        # and after each test. No DB, no server, no network.
        isolation="pure",
    )
    # Plugin settings (CP10). PURE, all six: no lane DB and no server. The databases are private files under tmp_path
    # built with create_all, the call boundaries read their rows through a private engine put in place of
    # get_async_engine, the instance key is a test key set with monkeypatch (the data directory pointed into tmp_path,
    # so no key file is ever read or made in the lane), and the real plugin registries are only read.
    add_test(cat, "plugin-settings-contract", services_plugin_settings_contract, name="Plugin Settings Contract", desc="Declarations per family, refusal at registration, values per type, refusals without the value, derived variable names, BoundSettings and the test doubles", isolation="pure")
    add_test(cat, "plugin-settings-crypto", services_plugin_settings_crypto, name="Plugin Settings Encryption", desc="AES-256-GCM blob and AAD, key id, subkeys, count and rekey on a sqlite3 copy (savepoint, idempotent, unreadable rows kept), key status (unusable key: totals)", isolation="pure")
    add_test(cat, "plugin-settings-runtime", services_plugin_settings_runtime, name="Plugin Settings Resolution", desc="env > _FILE > row > default, invalid variable unconfigures, unusable key, fingerprints, configure_instance, NOT_CONFIGURED and masking at both boundaries", isolation="pure")
    add_test(cat, "plugin-settings-service", services_plugin_settings_service, name="Plugin Settings Service", desc="Catalogue and all-or-nothing writes on a private DB: scopes, LOCKED_BY_ENV, managed profile, item rules, log without values, key unavailable, MOCKFX writes", isolation="pure")
    add_test(cat, "secret-masking", services_secret_masking, name="Secret Masking", desc="mask_text with the URL forms, mask_exception through chains and groups, structlog processor and logging filter, the context variable across threads and tasks, the wiring in configure_logging", isolation="pure")
    add_test(cat, "plugin-settings-guards", services_plugin_settings_guards, name="Plugin Settings Guards", desc="Shipped system-field variables in .env.example, derived names unique, no alias read by the app itself, services/ai_export/ never imports the plugin settings", isolation="pure")
    add_test(cat, "platform-readiness", services_platform_readiness, name="Instance Readiness", desc="Database and migration checks: ready, mismatch, unknown, unreachable; head read once, failure not kept; codes only in the response", isolation="pure")
    add_test(cat, "app-lifecycle", services_app_lifecycle, name="App Lifecycle", desc="Step runner (order, awaits, deadline cuts, a failure never skips the shutdown, step in progress); app steps in relative order, late-bound; middleware outermost first; SPA catch-all last", isolation="pure")
    add_test(
        cat,
        "static-cache-policy",
        services_static_cache_policy,
        name="Static Cache Policy",
        desc="F28: a file under /_app/immutable/ (named after its content) is sent with Cache-Control: public, max-age=31536000, immutable, and so is the 304 of its revalidation; any other file under /_app (env.js, version.json, immutable.json named like the folder) has one Cache-Control with no-cache and neither immutable nor max-age=31536000, its 304 too; the HTML documents (/, /index.html, the SPA fallback) keep no-cache, must-revalidate; with the build folder itself and behind a symlink",
        # A fresh FastAPI() holding the static site of a fake build under tmp_path (FRONTEND_BUILD_DIR swapped in by
        # monkeypatch), called through httpx's in-process ASGI transport. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "security-headers",
        services_security_headers,
        name="Security Headers",
        desc="F15 (D5, always): MIDDLEWARE_STACK holds one security_headers entry, SecurityHeadersMiddleware, outside gzip (relative order), and the app carries it outside GZip; every response has X-Content-Type-Options: nosniff and Referrer-Policy: strict-origin-when-cross-origin exactly once (JSON, HTML, streamed, the router's 404, a CORS preflight, a gzip-compressed body, a start without headers); a route's Referrer-Policy: no-referrer is kept and its nosniff not repeated; lifespan and websocket scopes pass untouched; on the app, the health route, the SPA catch-all and the 500 of an exception (still re-raised to the server) carry both",
        # Raw ASGI calls on fresh apps holding the stack's own entries and on the global app (its lifespan never runs);
        # the health route's session dependency, the catch-all's build and frontend_available swapped by monkeypatch.
        # No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "managed-headers",
        services_managed_headers,
        name="Managed Profile Headers",
        desc="F15 (D5, managed): with frame protection on (managed, or LIBREFOLIO_FRAME_PROTECTION=true) every response carries X-Frame-Options: SAMEORIGIN and Content-Security-Policy: frame-ancestors 'self' once each, with it off (selfhosted, or false over managed) neither; with the report-only policy on (managed, or LIBREFOLIO_CSP_REPORT_ONLY=true) Content-Security-Policy-Report-Only is on the web app's HTML only (/, a client-side route, also gzipped, /200.html), never on /mkdocs, the API's JSON or HTML (Swagger UI, the HTML 404 of an unknown API path), /_app JavaScript, a text file, a CORS preflight or a 500; its default-src 'self', object-src 'none', base-uri 'self', frame-ancestors 'self', script-src with 'self', each directive once, no report-uri nor report-to; a route's own X-Frame-Options, CSP or report-only CSP kept alone and the others added; the settings read when the middleware is built, never per request; nosniff and Referrer-Policy still on every response",
        # Fresh FastAPI() apps holding the stack's security_headers, gzip and cors, a few routes and the static site of a
        # fake build and documentation under tmp_path (FRONTEND_BUILD_DIR and SITE_DIR swapped by monkeypatch); test mode,
        # a data directory under tmp_path and the profile variables set by monkeypatch before an app is built; raw ASGI
        # calls. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-archive",
        services_backup_archive,
        name="Instance Backup Archive",
        desc="Layout and job ids, private folders never written through a link; VACUUM INTO copy as of one instant beside a WAL writer it never blocks, in rollback mode with nothing beside it; read-only description (integrity, foreign keys, rows, revision); manifest round trip, unknown fields ignored, UTC dates, database first, no entry twice, entry paths, every from_bytes code; an archive of the database and custom-uploads, broker_reports, scenario_catalog only (no logs, secrets, scheduler state, backups, -wal/-shm or post-migration files), the -wal's rows included, links, FIFOs and non-UTF-8 names left out and never followed, 0600, written as .part then renamed, space checked first; a file that fails before its entry starts left out with no descriptor left open, one that fails after it (read or write) stops the build (PartialEntryError); check_archive: missing, mismatched, unexpected and duplicated entries, archive_unreadable, manifest codes, reads bounded by the declared size",
        # PURE: every data directory, database and archive is built under tmp_path; the concurrent WAL writer is a
        # thread of this process on its own file. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-jobs",
        services_backup_jobs,
        name="Instance Backup Jobs",
        desc="start_backup to done in the background, job_archive, delete_job; run_backup in the calling thread; busy for both while the run lock is held; a running state with a free lock read as backup_interrupted and written down; a failed build (backup_failed) and no space (backup_no_space) end with the work files removed and the lock free, the final state on disk before the lock is released; one-hour retention of finished, dead and unreadable jobs, never links or other entries, a running job holding the lock kept; job ids never paths; state round trip, unknown keys ignored, 50 left-out entries kept; the process-local lock without fcntl; a full disk or quota during the build (ENOSPC, EDQUOT, SQLITE_FULL, through causes and contexts) ends as backup_no_space, any other failure as backup_failed; backup_in_progress (the run lock or the restore checks' lock held by anyone, read only, without fcntl the process's locks)",
        # PURE: data directories under tmp_path, every call given its data_dir (jobs.get_data_dir is a guard that fails
        # the test); every background run ends, joined, inside its test. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-staging",
        services_backup_staging,
        name="Instance Backup Staging",
        desc="restore --dry-run's check, on a copy in .restore/stage/<id>/: a backup at the head restored as it is (database and files byte for byte, 0700/0600, report.json read back equal, 24 h expiry), an older one upgraded for real by alembic in its own process (migrations after its revision, oldest first, as the migration files describe them; the copy at the head, its data converted; rows before/after); the active administrators named, none a blocker (no_administrator); every StagingError code (not a backup, unreadable or damaged zip, manifest codes, too many entries, duplicates even by case or Unicode form or as the folder of another, unexpected, folder/link/encrypted/bzip2/lzma entries, size or SHA-256 mismatch, missing entry, no space before or while writing, write failure, damaged database, manifest mismatch, revision missing, unknown (never downgraded) or unreadable head, upgrade failed, post-migration fix failed), each leaving no stage, the lock free, no path in its message, a refusal from the directory before any byte written; one check at a time (StagingBusyError, a caller's lock kept for it to release, the check's own released); .restore links refused, stages never written over, a linked stage unlinked, nothing removed while .restore or its stage folder is a link or a file; progress phases; warnings rows_changed, foreign_key_violations(_added); the live data directory (WAL database, files, secrets) byte-identical; B-28: a database holding a trigger, a view or a virtual table refused as database_foreign_objects (a schema SQLite refuses to read, database_damaged) before anything else opens the copy, its schema read by its SQL, read only, the warning without names; this LibreFolio's own schema only tables and indexes; trusted_schema=OFF first on every connection B opens on the copy",
        # PURE: every data directory, database and archive under tmp_path; two alembic processes make the module's
        # databases and two more are the product's upgrade of a copy, all on tmp_path files, with a production data
        # directory of the test configured (which must stay absent). No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-apply",
        services_backup_apply,
        name="Instance Backup Restore",
        desc="The restore of a checked copy (lot B3): paths (.restore/restore.json, apply.lock, previous/, failed/, SWAPPED_FOLDERS, stage_data_dir); the errors and their codes, frozen models; boots (server_pid and the creation time, a reused pid another boot); read_restore and protected_stage (an ordinary start creates nothing; links, files, unreadable states never followed); confirm_restore (refusals in order: .restore not a folder, copy missing, blockers, expired at expires_at, head moved, already active; pending written atomically 0600, leftovers removed); cancel_restore; apply_pending_restore: the four folders in every live/staged layout with their modes, the journal before the first rename, the same boot, another live one, a dead or reused one (first_start_failed), killed after any rename of the swap or of the undo, a rename failing (swap_failed; RestoreApplyError, finished at the next start), waiting (another data directory, a backup running), stage_missing, a live link or file, two workers of one server making one swap; finish_pending_restore (committed, every account at max(R, A + 1, B + 1), leftovers removed, idempotent; rolled back cleaned; anything else untouched); the sessions in-process (the clock ahead or behind, a restore on a restore, then a password change + 1); the startup steps in place and off the loop; restart (SIGTERM to the server through send_signal); B2 then B3 with real archives at the head and at an older revision; after the security review (§10): the boot read once per process, fail closed with restore_in_use, the serving lock (shared from data-directories, exclusive while the folders move, server_running), the strict state; P7 (§11): no restore applied while LIBREFOLIO_BLOCKED (instance_blocked, after other_data_directory and before server_running and backup_running; an unreadable value counts as blocked), the undo and the commit unchanged; B5c (n): the outcome ticket dropped by a confirmation and by a cancel, kept by their refusals, the swap, the commit and a rollback, read again until it expires (N53), prepare_restart issuing it under the restore's lock and writing nothing without a pending restore",
        # PURE: every data directory, database and archive under tmp_path, with a production data directory of the test
        # configured (which must stay absent); two alembic processes make the module's databases, two spawn children
        # play two workers on a tmp_path instance; send_signal and os.kill replaced: no signal. No lane DB, no server,
        # no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-outcome",
        services_backup_outcome,
        name="Instance Backup Restore Outcome",
        desc="The outcome of a restart's restore read with a one-time ticket, without a session (lot B5c): .restore/outcome-ticket.json (OUTCOME_TICKET_FILE, outcome_ticket_path), OUTCOME_TICKET_TTL one hour, OutcomeTicket frozen with its five fields only, RestoreOutcome state/reason/waiting only; issue_ticket: 43 URL-safe characters, a new one at each call, its file holding its SHA-256 and never the ticket, the stage, issued_at, expires_at an hour later, 0600, written beside then renamed, a link in its place replaced and never written through, .restore a link or a file BackupPathError, a stage id only, a second ticket replacing the first; read_outcome: the outcome of the restore of its stage (applying, applied, rolling_back in_progress; reason and waiting as recorded) until expires_at excluded, None alike for every other case (no, empty or malformed ticket, no file, a file unreadable or not a ticket, an extra key, a folder, a link never followed, another ticket compared in constant time, expired and its file removed, no restore, another stage), a wrong ticket never removing it, an expired one removed only by its own ticket; N53, one restore one ticket: every outcome, committed and rolled_back included, read again with the same answer and its file kept until expires_at; drop_ticket removes it, does nothing without one, never raises (logged), never through a link; neither a ticket nor its hash ever logged (structlog and stdlib); data_dir and now default to the configured data directory and the clock",
        # PURE: every data directory under tmp_path, with a production data directory of the test configured (which must
        # stay absent) but in the one case that configures the test's own instance; the restore's state is a model built
        # in the test. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-envelope",
        services_backup_envelope,
        name="Secure Backup Envelope",
        desc="The .lfbk envelope (lot B4, decisions 38 and P12): its constants; round trips at the chunk edges; the 52-byte header at its offsets; known answers built with cryptography's Scrypt and AESGCM; bounds refused before any derivation (envelope_unsupported), too short or not ours (envelope_damaged); wrong_password, also for changed key parameters; every tampering of the chunks (a byte, a tag, truncations, an appended, swapped, dropped or repeated chunk) envelope_damaged with nothing left; NFC, not NFKC; no overwrite, 0600, .part only while writing, progress; the key never in its repr; constant memory",
        # PURE: files under tmp_path only. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-secure-rules",
        services_backup_secure_rules,
        name="Secure Backup Rules",
        desc="The rules of a secure backup (lot B4, P12, decision 39): the password's, the accounts' rules with at least 12 characters and up to 1024, following a longer minimum of the accounts; the instance key a backup may carry, the generated one only, as its text, never a configured one, never an unusable one, never created",
        # PURE: data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables. No DB, no server, no
        # network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-secure",
        services_backup_secure,
        name="Secure Backup",
        desc="A secure backup through the services (lot B4): run_backup with a password writes an .lfbk (encrypting phase; no clear zip, part or password left; the envelope's size and hash), the generated instance key inside (never a configured, missing or unusable one: instance_key_unusable), its failures (backup_no_space, backup_failed); the check of an envelope (decrypting first, the same report as its zip's, no archive.zip or secrets/ left), password_required and envelope_damaged, start_check keeping the upload on a missing or wrong password; the key entry's rules; the plugin secrets re-encrypted with this instance's key, or counted unreadable",
        # PURE: data directories, databases and archives under tmp_path. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-leftovers",
        services_backup_leftovers,
        name="Backup Leftovers",
        desc="The startup cleanup of what runs killed outright left in clear (lot B4b, B-23, decision N66): a check its server left running ended (restore_interrupted, copy and upload removed); a decrypted archive.zip left in a copy removed while no check runs, never a link, the rest of the copy kept; the inspect folders .decrypt-* older than an hour removed, younger ones, links and files kept; a backup that died with its process ended (backup_interrupted) with its work files removed, also by get_job; nothing touched under a held lock; expired jobs removed; a part that fails logged while the others still run, never raised; quiet on a clean data directory; the step backup-leftovers",
        # PURE: data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables. No lane DB, no server,
        # no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-totals",
        services_backup_totals,
        name="Instance Backup Ledger Totals",
        desc="Lot B-13 (contract §7). ledger_totals_of: J's JSON of a real database's ledger, equal to J's control_totals of the same rows read with sqlite3, no line for an empty ledger; read as immutable (bytes, mtime, nothing created beside it, in rollback-journal mode, in WAL mode, with an empty -wal and its -shm); a -wal still holding frames never read past (None, PendingWriteAheadLog); the path a name, never a URI (spaces, accents, #, ?, &, %41); never raises (missing, folder, not a database, empty, truncated, no ledger table, a decimal trap, a running event loop): None and one error with the exception's type only. compare_totals: the decision order (absent; other_version before reading; absent for amounts that are not plain text and lines not lists of objects, refused by J's from_json (one rule, J's home since J-27; never expanding 1E+999999999), and for the rest from_json refuses, a version that is not an int included; unreadable; then the lines as maps, canonical text, zero lines dropped: same without a difference, reordered or zero lines included, changed with one line at least); differences cash first, by broker, currency or asset, canonical text, None for an absent line, the first 20 kept and all counted, none for another status; frozen; the documents given unchanged",
        # PURE: one alembic process makes the module's database on a tmp_path file; every file read is a copy under
        # tmp_path, with a production data directory of the test configured (which must stay absent). No lane DB, no
        # server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-checks",
        services_backup_checks,
        name="Backup Configuration Checks",
        desc="Lot B-9 (instance_backup/checks.py, in the platform's CONFIG_CHECKS). check_panel_token, backup.panel_token: unset or blank ok .off (a default start logs nothing new), usable (32 characters included) ok, 31 characters tooShort {minimum: 32}, a space, a tab or a letter outside ASCII notVisibleAscii, a _FILE missing, blank or not UTF-8 unreadable with the reader's error as reason, the variable winning over its broken file. check_upload_limit, backup.upload_limit: 0 or unset self-hosted unlimited, a number or the managed 500 limited {limit_mb}, letters, negative or decimal invalid, H's managed entry of another type or removed profileTable (H-27, H-37), self-hosted reading no entry, the variable winning over a wrong table. Never raises on each documented error of its reader; no token in any result, record or event of the startup audit (canary); BACKUP_CONFIG_CHECKS in order, in CONFIG_CHECKS together before the email checks; either module imported first in a fresh interpreter; the startup audit logs an unusable configuration as one ERROR and goes on, a default start logs nothing about them; the nine messages in the four backup catalogues with their placeholders",
        # PURE: variables through monkeypatch, secret files under tmp_path. No lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "logging-access-filter",
        services_logging_access_filter,
        name="Credentials in uvicorn's Request Lines",
        desc="mask_query_credentials: an exact code, or a name holding token/secret/password/passwd/api_key/apikey/api-key/signature/ticket, judged percent-decoded, masked in any case (a ticker kept); a URL nested unencoded read too; other parameters, the path, the fragment and an encoded value kept. The filter masks every string arg where it stands and a message without args, never a format string with args; mappings and non-string args untouched. uvicorn's h11/httptools access line and WebSocket handshake line (--ws auto) masked, each with a negative control; configure_logging twice leaves one filter on uvicorn.access and on uvicorn.error; H-9: configure_logging closes every handler it takes off the root, a second call's log file included",
        # PURE: uvicorn's protocol objects get one request or handshake in memory through a fake transport, no socket
        # and no server; records go to private loggers or to the real uvicorn loggers inside a block that puts every
        # logger and structlog's configuration back (configure_logging with file logging off, except section (e), whose
        # log files go under tmp_path). No DB, no network, no file written outside tmp_path.
        isolation="pure",
    )
    add_test(cat, "donation-popup", services_donation_popup, name="Donation Popup", desc="Trigger decision logic (50-login/7-day/60-day rules), hidden env var, counter updates")
    add_test(cat, "date-sentinel", services_date_sentinel, name="Date Sentinel", desc="resolve_date_sentinels min/max/passthrough, broker filter")
    add_test(cat, "file-preview", services_file_preview, name="File Preview", desc="CSV/Excel/text preview detection helpers")
    add_test(
        cat,
        "fx-sync-service",
        services_fx_sync,
        name="FX Sync Orchestration",
        desc="_is_date_within_sync_range, _process_route/_compute_multi_step",
        exclusive_because="an autouse fixture truncates fx_rates and fx_conversion_routes before every test, so any concurrent unit reading rates or routes loses them mid-test",
    )
    add_test(cat, "provider-registry-misc", services_provider_registry_misc, name="Provider Registry Helpers", desc="auto_discover, register, get_provider_instance, BRIM plugin detection")
    add_test(cat, "scheduler-joblog-misc", services_scheduler_joblog_misc, name="Scheduler Job Log Helpers", desc="read_entries, _rotate_if_needed")
    add_test(cat, "scheduler-joblog-builders", services_scheduler_joblog_builders, name="Scheduler Job Log Builders", desc="append/rotate/read round trip, entry builders, SyncStatus StrEnum guard")
    add_test(cat, "scheduler-settings-misc", services_scheduler_settings_misc, name="Scheduler Settings TZ Conversion", desc="_local_times_to_utc")
    add_test(cat, "ai-export", services_ai_export, name="AI Export", desc="Component runtime, datasets, analyses, financial/technical builders, and temporal policy")
    add_test(
        cat,
        "ai-export-pure",
        services_ai_export_pure,
        name="AI Export Pure Contracts",
        desc="Payload/aggregate invariants, observed FX math, shared technical helpers",
        isolation="pure",
    )
    add_test(
        cat,
        "ai-export-period-bounds",
        services_ai_export_period_bounds,
        name="AI Export Period Bounds",
        desc="R13-SEC7-1: the period a snapshot hands its components ends at tomorrow at the latest and spans 100 years at most (mocked session, test-owned registry)",
        isolation="pure",
    )
    add_test(
        cat,
        "provider-errors",
        services_provider_errors,
        name="Provider Error Paths",
        desc="justETF, Borsa Italiana, Yahoo Finance, SNB, BOE, FED and ECB when the source misbehaves or refuses for too many requests (every client doubled); a value that is no number skips its line only (X-R50, X-R52)",
        isolation="pure",
    )
    add_test(cat, "borsa-italiana-search", services_borsa_italiana_search, name="Borsa Italiana Search", desc="Single-fetch search, IT+EN variants, ISIN direct hit (engine mocked)")
    add_test(cat, "borsa-italiana-funds", services_borsa_italiana_funds, name="Borsa Italiana Funds", desc="Mutual-fund NAV via codice_fondo detail page + resolve_url (scraper mocked)")
    add_test(cat, "web-link-finder", services_web_link_finder, name="Web Link Finder", desc="find_candidate_urls + search orchestration augmentation (ddgs mocked)")
    add_test(
        cat,
        "tools-registry",
        services_tools_registry,
        name="Tool Registry",
        desc="Typed plugins, transactional discovery, quarantine and read-only catalog",
        isolation="pure",
    )
    add_test(
        cat,
        "tools-lifecycle",
        services_tools_lifecycle,
        name="Tool Lifecycle",
        desc="Owned spawn workers, quotas, ready/ACK, cancellation, PID identity and full-tree cleanup",
        exclusive_because=("owns native POSIX process groups and exercises forceful teardown and executor quarantine; " "requires an explicitly leased lifecycle run rather than concurrent shared-backend manual review"),
    )
    add_test(cat, "all", services_all, test_names=False, name="All Services Tests", desc="Run all service tests")
    registry["services"] = cat
