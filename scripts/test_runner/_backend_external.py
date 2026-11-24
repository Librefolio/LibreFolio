"""
External service tests: FX providers, asset providers, BRIM providers.
Includes provider discovery for dynamic CLI help.
"""

import re

from . import _common
from ._common import (
    PROJECT_ROOT,
    _build_pytest_cmd,
    _get_category_tests_for_all,
    _run_test_suite,
    add_test,
    make_category,
    print_info,
    print_section,
    run_command,
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
    "fx": "fx_providers",
    "brim": "brim_providers",
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
    # A plugin is a folder: its code is in ``<name>/plugin.py`` (helpers are ``_*.py`` beside it, never scanned).
    for py in target_dir.glob("*/plugin.py"):
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
    provider_help = "Only test these provider(s). " f"Asset: {', '.join(asset_codes) or '(none)'}. " f"FX: {', '.join(fx_codes) or '(none)'}. " f"BRIM: {', '.join(brim_codes) or '(none)'}. " "If omitted, ALL providers are tested."
    exclude_help = "Exclude these provider(s) from testing. " f"Asset: {', '.join(asset_codes) or '(none)'}. " f"FX: {', '.join(fx_codes) or '(none)'}. " f"BRIM: {', '.join(brim_codes) or '(none)'}."
    return [
        (
            "--providers",
            {
                "nargs": "+",
                "dest": "providers",
                "metavar": "CODE",
                "help": provider_help,
                "default": None,
            },
        ),
        (
            "--exclude-providers",
            {
                "nargs": "+",
                "dest": "exclude_providers",
                "metavar": "CODE",
                "help": exclude_help,
                "default": None,
            },
        ),
    ]


# ── Test functions ──────────────────────────────────────────────────────


def external_fx_providers(verbose: bool = False, test_names: list = None, providers: list = None, exclude_providers: list = None) -> bool:
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

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_fx_providers.py", effective_names or None)
    return run_command(cmd, "FX providers external tests", verbose=verbose)


def external_asset_providers(verbose: bool = False, test_names: list = None, providers: list = None, exclude_providers: list = None) -> bool:
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

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_asset_providers.py", effective_names or None)
    return run_command(cmd, "Asset providers tests", verbose=verbose)


def external_justetf_multicurrency(verbose: bool = False, test_names: list = None) -> bool:
    """Test JustETF multi-currency support (EUR/USD/CHF/GBP)."""
    print_section("External: JustETF Multi-Currency Tests")
    print_info("Testing: JustETF provider with all 4 supported currencies")
    print_info("Tests: Current price (EUR-only), history (all 4), search (4× results), params validation")
    print_info("⚠️  WARNING: Requires internet connection")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_justetf_multicurrency.py", test_names or None)
    return run_command(cmd, "JustETF multi-currency tests", verbose=verbose)


def external_enrichers(verbose: bool = False, test_names: list = None) -> bool:
    """Test every real enricher against its source: its test_cases recognized and read, a not-found case, search (plan 68 §C)."""
    print_section("External: Enrichers Tests")
    print_info("Testing: every non-test-only enricher of EnricherRegistry (backend/app/services/enricher_providers/)")
    print_info("Tests: recognize and read of each test case (values declared, stored forms), not found, search")
    print_info("⚠️  WARNING: Requires internet connection")
    # -s: the values each read gives are printed, so the log shows what the source answered today
    cmd = [*_build_pytest_cmd("backend/test_scripts/test_external/test_enrichers.py", test_names or None), "-s"]
    return run_command(cmd, "Enrichers external tests", verbose=verbose)


def external_brim_providers(verbose: bool = False, test_names: list = None, providers: list = None, exclude_providers: list = None) -> bool:
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

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_providers.py", effective_names or None)
    return run_command(cmd, "BRIM providers tests", verbose=verbose)


def external_brim_danske_bank(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Danske Bank report-set plugin (custody XLSX + cash CSV)."""
    print_section("External: BRIM Danske Bank Report-Set Tests")
    print_info("Testing: broker_danske_bank — recognition, reading, classification, rule M, pairing")
    print_info("Tests: zones and outcomes, truth points, combined format, parse of the combined file, sample facts")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_danske_bank.py", test_names or None)
    return run_command(cmd, "BRIM Danske Bank tests", verbose=verbose)


def external_brim_credit_agricole(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Crédit Agricole report-set modules (rows, classes, rule M, pairs, balances)."""
    print_section("External: BRIM Crédit Agricole Report-Set Tests")
    print_info("Testing: broker_credit_agricole — rows, testata, classes, rule M, pairing, balances, truth points")
    print_info("Tests: reading, roles, describe member/set, outcomes, holes and gaps, in-flight cash, opening positions, zones")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_credit_agricole.py", test_names or None)
    return run_command(cmd, "BRIM Crédit Agricole tests", verbose=verbose)


def external_brim_degiro(verbose: bool = False, test_names: list = None) -> bool:
    """Test the DEGIRO plugin (Account Statement by position, any language)."""
    print_section("External: BRIM DEGIRO Tests")
    print_info("Testing: broker_degiro — recognition, reading by position, types, FX pairs, numbers, messages")
    print_info("Tests: Dutch and English samples row by row, orders list, warnings with evidence")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_degiro.py", test_names or None)
    return run_command(cmd, "BRIM DEGIRO tests", verbose=verbose)


def external_brim_traderepublic(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Trade Republic plugin (the Transaction export in both shapes, and the Dutch CSV)."""
    print_section("External: BRIM Trade Republic Tests")
    print_info("Testing: broker_traderepublic — recognition by required columns, the date column, legs read verbatim, notices")
    print_info("Tests: clean and Excel samples row by row, ; variant, tax refunds, unsettled rows, rows not recognised or unreadable, assets")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_traderepublic.py", test_names or None)
    return run_command(cmd, "BRIM Trade Republic tests", verbose=verbose)


def external_brim_fineco(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Fineco plugin's linked charges (project 66, wave P2a); the rest of Fineco is in brim-providers."""
    print_section("External: BRIM Fineco Tests")
    print_info("Testing: broker_fineco — each commission names the trade of its row (also across currencies), the previous version's snapshot, the reimport")
    print_info("Tests: the four samples (Variant B links, Variant A has no charge), structure, only names change, reimport adds nothing, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_fineco.py", test_names or None)
    return run_command(cmd, "BRIM Fineco tests", verbose=verbose)


def external_brim_directa(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Directa plugin's linked charges (project 66, lot P3); the rest of Directa is in brim-providers."""
    print_section("External: BRIM Directa Tests")
    print_info("Testing: broker_directa — commissions, «Rit. etf» and Tobin tax by order reference, withholdings by date and ISIN, «Rit.provento etf» as a TAX")
    print_info("Tests: the sample and invented rows, one candidate only, order kept, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_directa.py", test_names or None)
    return run_command(cmd, "BRIM Directa tests", verbose=verbose)


def external_brim_cointracking(verbose: bool = False, test_names: list = None) -> bool:
    """Test the CoinTracking plugin's linked charges (project 66, lot P4a); the rest of CoinTracking is in brim-providers."""
    print_section("External: BRIM CoinTracking Tests")
    print_info("Testing: broker_cointracking — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_cointracking.py", test_names or None)
    return run_command(cmd, "BRIM CoinTracking tests", verbose=verbose)


def external_brim_delta(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Delta plugin's linked charges (project 66, lot P4a); the rest of Delta is in brim-providers."""
    print_section("External: BRIM Delta Tests")
    print_info("Testing: broker_delta — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_delta.py", test_names or None)
    return run_command(cmd, "BRIM Delta tests", verbose=verbose)


def external_brim_relai(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Relai plugin's linked charges (project 66, lot P4a); the rest of Relai is in brim-providers."""
    print_section("External: BRIM Relai Tests")
    print_info("Testing: broker_relai — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_relai.py", test_names or None)
    return run_command(cmd, "BRIM Relai tests", verbose=verbose)


def external_brim_investimental(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Investimental plugin's linked charges (project 66, lot P4a); the rest of Investimental is in brim-providers."""
    print_section("External: BRIM Investimental Tests")
    print_info("Testing: broker_investimental — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_investimental.py", test_names or None)
    return run_command(cmd, "BRIM Investimental tests", verbose=verbose)


def external_brim_ibkr(verbose: bool = False, test_names: list = None) -> bool:
    """Test the IBKR plugin's linked charges (project 66, lot P4a); the rest of IBKR is in brim-providers."""
    print_section("External: BRIM IBKR Tests")
    print_info("Testing: broker_ibkr — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_ibkr.py", test_names or None)
    return run_command(cmd, "BRIM IBKR tests", verbose=verbose)


def external_brim_parqet(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Parqet plugin's linked charges (project 66, lot P4a); the rest of Parqet is in brim-providers."""
    print_section("External: BRIM Parqet Tests")
    print_info("Testing: broker_parqet — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_parqet.py", test_names or None)
    return run_command(cmd, "BRIM Parqet tests", verbose=verbose)


def external_brim_trading212(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Trading 212 plugin's linked charges (project 66, lot P4a); the rest of Trading 212 is in brim-providers."""
    print_section("External: BRIM Trading 212 Tests")
    print_info("Testing: broker_trading212 — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_trading212.py", test_names or None)
    return run_command(cmd, "BRIM Trading 212 tests", verbose=verbose)


def external_brim_revolut(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Revolut plugin's linked charges (project 66, lot P4a); the rest of Revolut is in brim-providers."""
    print_section("External: BRIM Revolut Tests")
    print_info("Testing: broker_revolut — a fee or a tax linked to the booking of its own row")
    print_info("Tests: the sample and invented rows, free charges by rule, snapshot of the previous version, reimport, version")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_revolut.py", test_names or None)
    return run_command(cmd, "BRIM Revolut tests", verbose=verbose)


def external_brim_scalable(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Scalable Capital plugins (broker account and overnight account)."""
    print_section("External: BRIM Scalable Capital Tests")
    print_info("Testing: broker_scalable and broker_scalable_deposit — recognition by header, refusals with a code, mapping, legs, notices")
    print_info("Tests: PRIME and exporter samples row by row, mirrored internal transfers, synthetic edge cases")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_scalable.py", test_names or None)
    return run_command(cmd, "BRIM Scalable Capital tests", verbose=verbose)


def external_brim_xtb(verbose: bool = False, test_names: list = None) -> bool:
    """Test the XTB plugin: the History report workbook, the only format it reads since 2.0.0 (lane 83)."""
    print_section("External: BRIM XTB Tests")
    print_info("Testing: broker_xtb — the History report workbook (.xlsx)")
    print_info("Tests: samples, account currency, sub-account transfers, partial fills, rows left out, positions outside the period")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_xtb.py", test_names or None)
    return run_command(cmd, "BRIM XTB tests", verbose=verbose)


def external_brim_row_skips(verbose: bool = False, test_names: list = None) -> bool:
    """Test the rows BRIM plugins leave out: known quietly, unknown loudly (W-B86)."""
    print_section("External: BRIM Row Skips Tests")
    print_info("Testing: the shared RowSkips helper, the rows each stable plugin leaves out, the contract over every registered plugin, the catalogue keys")
    print_info("Tests: one file per case (a sample plus one row), report_issue, silent rows, versions, samples, plugin classification")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_row_skips.py", test_names or None)
    return run_command(cmd, "BRIM row skips tests", verbose=verbose)


def external_brim_operation_date(verbose: bool = False, test_names: list = None) -> bool:
    """Test that BRIM plugins record the operation date, never the value / settlement date (W-B88)."""
    print_section("External: BRIM Operation Date Tests")
    print_info("Testing: the transaction date is the day of the operation, not the value / settlement date")
    print_info("Tests: rows whose two dates differ, per plugin; the Disnat settlement-date fallback for rows with no trade date")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_operation_date.py", test_names or None)
    return run_command(cmd, "BRIM operation date tests", verbose=verbose)


def external_brim_economic_rows(verbose: bool = False, test_names: list = None) -> bool:
    """Test that eToro, Swissquote, Revolut and Trading 212 import the rows with an economic effect they used to leave out (W-B87)."""
    print_section("External: BRIM Economic Rows Tests")
    print_info("Testing: overnight fees, SDRT, forex pairs and stock splits become transactions; the rows that cannot are still listed")
    print_info("Tests: eToro FEE and TAX, Swissquote FX_CONVERSION pairs, Revolut and Trading 212 ADJUSTMENT with a possible_split todo")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_economic_rows.py", test_names or None)
    return run_command(cmd, "BRIM economic rows tests", verbose=verbose)


def external_brim_date_order(verbose: bool = False, test_names: list = None) -> bool:
    """Test the generic CSV plugin's date_order field: parity with the old behaviour, month_first, the declaration (CP12, W5-8)."""
    print_section("External: BRIM Date Order Tests")
    print_info("Testing: broker_generic_csv parse_date(value, order), the date_order setting and its declaration")
    print_info("Tests: day_first is the old behaviour bit for bit, month_first mirrors the slash, dash and dot dates, the plugin declares the field")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_date_order.py", test_names or None)
    return run_command(cmd, "BRIM date order tests", verbose=verbose)


def external_brim_rewards(verbose: bool = False, test_names: list = None) -> bool:
    """Test rewards in kind imported as REWARD by Coinbase, Crypto.com, Freetrade and the generic CSV (project 79, STK-4a), Bitvavo and CoinTracking (STK-4b)."""
    print_section("External: BRIM Rewards Tests")
    print_info("Testing: reward_unit_value and reward_value_todo, the REWARD rows of four plugins (1.1.0), their value on receipt; Bitvavo 1.1.0 and CoinTracking 1.2.0 staking rewards (STK-4b)")
    print_info("Tests: type, units, no cash, per-unit value and currency, the reward_value todo, rows not imported with a warning, samples")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_rewards.py", test_names or None)
    return run_command(cmd, "BRIM rewards tests", verbose=verbose)


def external_all(verbose: bool = False, providers: list = None, exclude_providers: list = None) -> bool:
    """Run all external tests (network-dependent)."""
    return _run_test_suite(
        suite_name="External Tests",
        tests=_get_category_tests_for_all("external", verbose, providers=providers, exclude_providers=exclude_providers),
        verbose=verbose,
        info_msgs=[
            "Testing external provider integrations",
            "⚠️  WARNING: Requires internet connection for FX/Asset providers",
            "⚠️  WARNING: May be slow",
        ],
        resume=_common._RESUME_MODE,
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
""",
    )
    add_test(cat, "fx-providers", external_fx_providers, name="FX Providers", desc="Test FX rate providers (ECB, FED, BOE, SNB)", prereq="Internet connection", tests="ECB, FED, BOE, SNB API calls")
    add_test(cat, "asset-providers", external_asset_providers, name="Asset Providers", desc="Test asset pricing providers", prereq="Internet connection", tests="yfinance, cssscraper, etc.")
    # PURE: no database, no server; network calls to each enricher's own source (justETF today), paced by the plugin
    add_test(
        cat,
        "enrichers",
        external_enrichers,
        name="Enrichers",
        desc="Plan 68 §C: every real enricher's test_cases recognized and read (OK, declared voices, every value passing the catalogue; an ETF has ter, fund_provider, distribution_policy), a well-formed unknown identifier not found, a search for MSCI World bound by ISIN; a 429 fails with its reason",
        prereq="Internet connection",
        tests="justETF: SWDA (ETF), iShares Physical Gold (COMMODITY), Enel not found, search",
        isolation="pure",
    )
    add_test(cat, "justetf-multicurrency", external_justetf_multicurrency, name="JustETF Multi-Currency", desc="Test JustETF provider with EUR/USD/CHF/GBP currencies", prereq="Internet connection", tests="Current price, history, search, params validation")
    add_test(cat, "brim-providers", external_brim_providers, name="BRIM Providers", desc="Test broker report import plugins", prereq="Sample files in test fixtures", tests="Plugin discovery, file parsing, auto-detection")
    add_test(cat, "brim-danske-bank", external_brim_danske_bank, name="BRIM Danske Bank", desc="Test the Danske Bank report-set plugin", prereq="Sample files in test fixtures", tests="Roles, combine (zones, pairing, truth points), parse of the combined file")
    add_test(
        cat,
        "brim-credit-agricole",
        external_brim_credit_agricole,
        name="BRIM Crédit Agricole",
        desc="Test the Crédit Agricole report-set modules",
        prereq="None (synthetic files)",
        tests="Rows and testata, roles, rule M, classes, pairing, balances, holes, truth points, in-flight cash",
        isolation="pure",
    )
    add_test(cat, "brim-degiro", external_brim_degiro, name="BRIM DEGIRO", desc="Test the DEGIRO plugin", prereq="Sample files in test fixtures", tests="Recognition, reading by position, types, FX pairs, numbers, messages, orders list")
    add_test(
        cat,
        "brim-traderepublic",
        external_brim_traderepublic,
        name="BRIM Trade Republic",
        desc="Test the Trade Republic plugin (Transaction export, also re-saved by Excel, and the Dutch CSV)",
        prereq="Sample files in test fixtures",
        tests="Recognition, both shapes and ; identical, sample row by row, date column, tax refund, unsettled rows, duplicates, rows left out, assets, linked charges",
        isolation="pure",
    )
    add_test(
        cat,
        "brim-fineco",
        external_brim_fineco,
        name="BRIM Fineco",
        desc="Test the Fineco plugin's linked charges (project 66, wave P2a)",
        prereq="Sample files in test fixtures",
        tests="Each commission names its trade (EUR fee on a USD trade too), Variant A without charges, structure, snapshot of the previous version, reimport, version",
        # PURE: the samples and tmp_path files; the reimport tests open a private in-memory SQLite each and dispose it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-directa",
        external_brim_directa,
        name="BRIM Directa",
        desc="Test the Directa plugin's linked charges (project 66, lot P3)",
        prereq="Sample files in test fixtures",
        tests="Commission / «Rit. etf» / Tobin tax by order reference, coupon and ETF income withholdings by date and ISIN, «Rit.provento etf» as a TAX, one candidate only, order, snapshot, reimport, version, XLSX",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-cointracking",
        external_brim_cointracking,
        name="BRIM CoinTracking",
        desc="Test the CoinTracking plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-delta",
        external_brim_delta,
        name="BRIM Delta",
        desc="Test the Delta plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-relai",
        external_brim_relai,
        name="BRIM Relai",
        desc="Test the Relai plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-investimental",
        external_brim_investimental,
        name="BRIM Investimental",
        desc="Test the Investimental plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-ibkr",
        external_brim_ibkr,
        name="BRIM IBKR",
        desc="Test the IBKR plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-parqet",
        external_brim_parqet,
        name="BRIM Parqet",
        desc="Test the Parqet plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-trading212",
        external_brim_trading212,
        name="BRIM Trading 212",
        desc="Test the Trading 212 plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-revolut",
        external_brim_revolut,
        name="BRIM Revolut",
        desc="Test the Revolut plugin's linked charges (project 66, lot P4a)",
        prereq="Sample files in test fixtures",
        tests="Same-row fee and tax linked to their booking, free charges by rule, snapshot, reimport, version",
        # PURE: the sample and tmp_path files; the reimport test opens a private in-memory SQLite and disposes it.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-scalable",
        external_brim_scalable,
        name="BRIM Scalable Capital",
        desc="Test the Scalable Capital plugins (broker and overnight account)",
        prereq="Sample files in test fixtures",
        tests="Recognition, refusals with a code, PRIME and exporter samples, legs, notices, synthetic edge cases, linked charges",
    )
    add_test(
        cat,
        "brim-xtb",
        external_brim_xtb,
        name="BRIM XTB",
        desc="Test the XTB plugin: the History report workbook (.xlsx only)",
        prereq="Sample files in test fixtures",
        tests="Samples, account currency from Open Positions, sub-account transfer pairs, partial fills, RowSkips, positions outside the period, the old CSV refused",
        # PURE: the samples and workbooks/CSVs written in tmp_path; no server, no database.
        isolation="pure",
    )
    add_test(
        cat,
        "brim-row-skips",
        external_brim_row_skips,
        name="BRIM Row Skips",
        desc="Test the rows BRIM plugins leave out (known quietly, unknown loudly)",
        prereq="Sample files in test fixtures",
        tests="RowSkips helper, report_issue per plugin, silent rows, versions, plugin classification, catalogue keys",
    )
    add_test(
        cat,
        "brim-operation-date",
        external_brim_operation_date,
        name="BRIM Operation Date",
        desc="Test that BRIM plugins date a transaction with the operation date, never the value / settlement date",
        prereq="Sample files in test fixtures",
        tests="Directa, DEGIRO, InvestEngine, Saxo, Credit Agricole, Schwab, Disnat (incl. settlement fallback)",
    )
    add_test(
        cat,
        "brim-economic-rows",
        external_brim_economic_rows,
        name="BRIM Economic Rows",
        desc="Test that eToro, Swissquote, Revolut and Trading 212 import the rows with an economic effect",
        prereq="Sample files in test fixtures",
        tests="eToro overnight fee and SDRT, Swissquote forex pairs, Revolut and Trading 212 stock splits, rows still listed",
    )
    add_test(
        cat,
        "brim-date-order",
        external_brim_date_order,
        name="BRIM Date Order",
        desc="Test the generic CSV plugin's date_order field (CP12, W5-8): day_first parity with the old behaviour, month_first, the declaration",
        prereq="Sample files in test fixtures",
        tests="parse_date parity with a frozen reference, generic samples with and without day_first bound, month_first on slash/dash/dot, field declared as the contract says",
        isolation="pure",
    )
    add_test(
        cat,
        "brim-rewards",
        external_brim_rewards,
        name="BRIM Rewards",
        desc="Test rewards in kind imported as REWARD (project 79, STK-4a): Coinbase, Crypto.com, Freetrade, generic CSV; STK-4b: Bitvavo and CoinTracking staking rewards",
        prereq="Sample files in test fixtures",
        tests="reward_unit_value, reward_value_todo, REWARD type/units/no cash/value per plugin, the todo, rows not imported, samples, version 1.1.0; Bitvavo 1.1.0 (staking → REWARD + todo, Distributed settled for staking only, negative → ADJUSTMENT, the sample's 9 rewards), CoinTracking 1.2.0 (crypto staking → REWARD + todo, its fee a free FEE, fiat staking still a linked INTEREST)",
        # PURE: untouched samples and files of tmp_path; no server, no database, no network.
        isolation="pure",
    )
    add_test(cat, "all", external_all, test_names=False, name="All External Tests", desc="Run all external tests")
    registry["external"] = cat
