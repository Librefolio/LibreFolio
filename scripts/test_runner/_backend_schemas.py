"""
Backend schema validation tests: computed fields, common, assets, transactions, brokers.
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


def schemas_computed_fields(verbose: bool = False, test_names: list = None) -> bool:
    """Test computed properties across all schemas."""
    print_section("Schemas: Computed Fields")
    print_info("Testing: computed properties at 0% across brokers, common, fx, prices, transactions schemas")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_schema_computed_fields.py", test_names)
    return run_command(cmd, "Schema computed fields tests", verbose=verbose)


def schemas_common(verbose: bool = False, test_names: list = None) -> bool:
    """Test common Pydantic schemas."""
    print_section("Schemas: Common (Currency, DateRangeModel, OldNew)")
    print_info("Testing: backend/app/schemas/common.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_common_schemas.py", test_names)
    return run_command(cmd, "Common schemas tests", verbose=verbose)


def schemas_assets(verbose: bool = False, test_names: list = None) -> bool:
    """Test asset-related Pydantic schemas."""
    print_section("Schemas: Assets (FAGeographicArea, FAInterestRatePeriod, etc.)")
    print_info("Testing: backend/app/schemas/assets/ (scheduled_investment.py, metadata.py, assets.py)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_asset_schemas.py", test_names)
    return run_command(cmd, "Asset schemas tests", verbose=verbose)


def schemas_scheduled_investment_bounds(verbose: bool = False, test_names: list = None) -> bool:
    """R13-SEC7-2: the bounds of a scheduled investment schedule."""
    print_section("Schemas: Scheduled Investment Bounds (R13-SEC7-2)")
    print_info("Testing: backend/app/schemas/assets/scheduled_investment.py (dates, span, periods, grace), ScheduledInvestmentProvider.validate_params")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_scheduled_investment_bounds.py", test_names)
    return run_command(cmd, "Scheduled investment bounds tests", verbose=verbose)


def schemas_period_changes_bounds(verbose: bool = False, test_names: list = None) -> bool:
    """R13-SEC8 (MF-P2b): the as_of floor of a fixed-period changes item."""
    print_section("Schemas: Period Changes Bounds (R13-SEC8, MF-P2b)")
    print_info("Testing: backend/app/schemas/prices.py (FAPeriodChangesQueryItem), backend/app/schemas/fx.py (FXPeriodChangesRequest)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_period_changes_bounds.py", test_names)
    return run_command(cmd, "Period changes bounds tests", verbose=verbose)


def schemas_price_write_point(verbose: bool = False, test_names: list = None) -> bool:
    """N92 (i): the write model of a manual price ("clear" | number | null) and an answer model that checks no sign."""
    print_section("Schemas: Price Write Point (N92)")
    print_info("Testing: backend/app/schemas/prices.py (FAPriceWritePoint, FAUpsert, FAPricePoint)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_price_write_point.py", test_names)
    return run_command(cmd, "Price write point tests", verbose=verbose)


def schemas_currency_write_strict(verbose: bool = False, test_names: list = None) -> bool:
    """MF-SEC9b (E-18): strict ISO 4217 codes on the write paths, tolerant reads."""
    print_section("Schemas: Currency Write Strict (MF-SEC9b, E-18)")
    print_info("Testing: backend/app/schemas/common.py (iso_currency_code, IsoCurrencyCode, IsoCurrencyAmount) and the write schemas")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_currency_write_strict.py", test_names)
    return run_command(cmd, "Currency write strict tests", verbose=verbose)


def schemas_currency_suggestion(verbose: bool = False, test_names: list = None) -> bool:
    """E-19a: the ISO code a stored currency value stands for, the 422 naming it, a user's base currency strict."""
    print_section("Schemas: Currency Suggestion (E-19a)")
    print_info("Testing: backend/app/schemas/common.py (suggested_iso_currency, iso_currency_code's text), schemas/settings.py (base_currency)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_currency_suggestion.py", test_names)
    return run_command(cmd, "Currency suggestion tests", verbose=verbose)


def schemas_currency_candidates(verbose: bool = False, test_names: list = None) -> bool:
    """E-19b1: the ISO codes a stored currency value may stand for, the public base of the suggestion."""
    print_section("Schemas: Currency Candidates (E-19b1)")
    print_info("Testing: backend/app/schemas/common.py (iso_currency_candidates, suggested_iso_currency)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_currency_candidates.py", test_names)
    return run_command(cmd, "Currency candidates tests", verbose=verbose)


def schemas_transactions(verbose: bool = False, test_names: list = None) -> bool:
    """Test transaction Pydantic schemas."""
    print_section("Schemas: Transactions (TXCreateItem, TXReadItem, etc.)")
    print_info("Testing: backend/app/schemas/transactions/transactions.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_transaction_schemas.py", test_names)

    return run_command(cmd, "Transaction schemas tests", verbose=verbose)


def schemas_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """Test broker Pydantic schemas."""
    print_section("Schemas: Brokers (BRCreateItem, BRReadItem, etc.)")
    print_info("Testing: backend/app/schemas/brokers.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_broker_schemas.py", test_names)

    return run_command(cmd, "Broker schemas tests", verbose=verbose)


def schemas_fx_routes(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX route request and response metadata contracts."""
    print_section("Schemas: FX Routes")
    print_info("Testing: backend/app/schemas/fx.py route input/output separation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_fx_route_schemas.py", test_names)
    return run_command(cmd, "FX route schema tests", verbose=verbose)


def schemas_signals(verbose: bool = False, test_names: list = None) -> bool:
    """Test library-independent technical signal schemas."""
    print_section("Schemas: Technical Signals")
    print_info("Testing: backend/app/schemas/signals.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_signal_schemas.py", test_names)
    return run_command(cmd, "Signal schemas tests", verbose=verbose)


def schemas_risk(verbose: bool = False, test_names: list = None) -> bool:
    """Test canonical risk-series and metadata schemas."""
    print_section("Schemas: Risk Analysis")
    print_info("Testing: backend/app/schemas/risk.py and DataQualityReport extensions")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_risk_schemas.py", test_names)
    return run_command(cmd, "Risk schemas tests", verbose=verbose)


def schemas_pac_planner(verbose: bool = False, test_names: list = None) -> bool:
    """Test the strict PAC/Rebalancer v2 planner wire contract."""
    print_section("Schemas: PAC/Rebalancer Planner")
    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_pac_planner_schemas.py", test_names)
    return run_command(cmd, "PAC/Rebalancer planner schema tests", verbose=verbose)


def schemas_ai_export(verbose: bool = False, test_names: list = None) -> bool:
    """Test AI Export request, response, and catalog schemas."""
    print_section("Schemas: AI Export")
    print_info("Testing: component-based public runtime contracts")

    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_schemas/test_ai_export_runtime_schemas.py",
        test_names,
    )
    return run_command(cmd, "AI Export schemas tests", verbose=verbose)


def schemas_tools(verbose: bool = False, test_names: list = None) -> bool:
    """Test strict Tool transport contracts with private Pydantic fixtures."""
    print_section("Schemas: Tools")
    print_info("Testing: Tool envelopes, discriminators, policies and metrics")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_tools_schemas.py", test_names)
    return run_command(cmd, "Tool schemas tests", verbose=verbose)


def schemas_openapi_client_text(verbose: bool = False, test_names: list = None) -> bool:
    """Test the texts the API client generator pastes unescaped into the TypeScript client (backlog E-5)."""
    print_section("Schemas: OpenAPI Client Text")
    print_info("Testing: app.openapi() texts openapi-zod-client 1.18.3 writes unescaped into frontend/src/lib/api/generated.ts")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_openapi_client_text.py", test_names)
    return run_command(cmd, "OpenAPI client text tests", verbose=verbose)


def schemas_all(verbose: bool = False) -> bool:
    """Run all schema validation tests."""
    if _common.nothing_left_to_run("schemas"):
        return _common.consolidated_verdict("schemas")
    return _run_test_suite(
        suite_name="Schema Validation Tests",
        tests=_get_category_tests_for_all("schemas", verbose),
        verbose=verbose,
        info_msgs=["Testing Pydantic schema validation rules"],
        summary_title="Schema Tests Summary",
        success_msg="All schema tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all schema test entries."""
    cat = make_category(
        help_text="Pydantic schema validation tests (computed fields, assets, transactions, brokers)",
        description="""
Schema Validation Tests

Tests for Pydantic/SQLModel schema validation:
  • Computed fields, Common schemas, Asset schemas
  • Transaction schemas, Broker schemas
""",
        # Pydantic validation: no shared state to contend for.
        default_isolation="write-scoped",
    )
    add_test(cat, "computed-fields", schemas_computed_fields, name="Computed Fields", desc="Computed properties across all schemas")
    add_test(cat, "common", schemas_common, name="Common Schemas", desc="Currency, DateRangeModel, OldNew")
    add_test(cat, "assets", schemas_assets, name="Asset Schemas", desc="FAGeographicArea, FAInterestRatePeriod")
    add_test(cat, "transactions", schemas_transactions, name="Transaction Schemas", desc="TXCreateItem, TXReadItem")
    add_test(cat, "brokers", schemas_brokers, name="Broker Schemas", desc="BRCreateItem, BRReadItem")
    add_test(cat, "fx-routes", schemas_fx_routes, name="FX Route Schemas", desc="Request validation and response-only chain/provider membership metadata")
    add_test(cat, "signals", schemas_signals, name="Signal Schemas", desc="Plugin, catalog, canonical output, status and availability contracts")
    add_test(cat, "risk", schemas_risk, name="Risk Schemas", desc="Canonical valuations, returns, metadata and data-quality contracts")
    add_test(
        cat,
        "pac-planner",
        schemas_pac_planner,
        name="PAC/Rebalancer Planner Schemas",
        desc="Strict v2 request/result codecs, exact-number evidence, Option-B wire bounds and fixture roundtrips",
        isolation="pure",
    )
    add_test(cat, "ai-export", schemas_ai_export, name="AI Export Schemas", desc="Strict requests, responses, catalog, and typed problem contracts")
    add_test(
        cat,
        "tools",
        schemas_tools,
        name="Tool Schemas",
        desc="Strict transport, required metadata, correlation IDs, resource policies and platform outcomes",
        isolation="pure",
    )
    add_test(
        cat,
        "openapi-client-text",
        schemas_openapi_client_text,
        name="OpenAPI Client Text",
        desc="Text the API client generator writes unescaped: describe(), endpoint descriptions, JSDoc",
        # No isolation= on purpose, so the category's write-scoped holds: no row, no server, no network, but importing
        # backend.app.main (the real document, read as api sync reads it) runs configure_logging, which creates
        # <data dir>/logs/ and opens librefolio.log there, the lane's log that the shared backend writes too.
    )
    add_test(cat, "scheduled-investment-bounds", schemas_scheduled_investment_bounds, name="Scheduled Investment Bounds", desc="R13-SEC7-2 (N73): period dates 1900-2200, span ≤ 36 525 days, ≤ 1 200 periods, grace ≤ 36 525 days")
    add_test(
        cat,
        "period-changes-bounds",
        schemas_period_changes_bounds,
        name="Period Changes Bounds",
        desc="X5-6 (R13-SEC8 withdrawn): the as_of and range_start of an asset or FX period-changes item are any day of the calendar (0001-01-01 …, no floor, no upper bound); range_start not after as_of",
        # PURE: imports schemas.prices and schemas.fx only and validates items; no row, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "price-write-point",
        schemas_price_write_point,
        name="Price Write Point",
        desc="N92 (i): a manual price's open, high, low and volume take a number of 0 or more, 'clear' (empty the stored value) or null (leave it); -1, any other text, a value not finite and a boolean refused on their field (422); close above 0; FAUpsert reads write points; FAPricePoint, the provider's and the answer's model, checks no sign",
        # PURE: imports schemas.prices only and validates items; no row, no server, no network, no file.
        isolation="pure",
    )
    add_test(
        cat,
        "currency-write-strict",
        schemas_currency_write_strict,
        name="Currency Write Strict",
        desc="MF-SEC9b (E-18): write paths take ISO 4217 alpha-3 codes only; read paths stay tolerant",
        # PURE: schemas and plain functions only; no row, no server, no network, no file.
        isolation="pure",
    )
    add_test(
        cat,
        "currency-suggestion",
        schemas_currency_suggestion,
        name="Currency Suggestion",
        desc="E-19a: the ISO code a stored currency value stands for (none when ambiguous or a subunit), the 422 naming it, base_currency strict",
        # PURE: schemas and plain functions over pycountry's data; no row, no server, no network, no file.
        isolation="pure",
    )
    add_test(
        cat,
        "currency-candidates",
        schemas_currency_candidates,
        name="Currency Candidates",
        desc="E-19b1: the ISO codes a stored currency value may stand for (VED and VES for Bolívar Soberano), the base of the suggestion",
        # PURE: plain functions over pycountry's data; no row, no server, no network, no file.
        isolation="pure",
    )
    add_test(cat, "all", schemas_all, test_names=False, name="All Schema Tests", desc="Run all schema tests")
    registry["schemas"] = cat
