"""
BRIM Provider Tests — Unified Parametrized Test Suite.

Tests all registered BRIM (Broker Report Import Manager) plugins with a
single uniform suite, parametrized over every plugin via
``@pytest.mark.parametrize(("code", "plugin"), _PLUGIN_PARAMS, ids=_PLUGIN_IDS)``.

Pattern is consistent with ``test_asset_providers.py`` and
``test_fx_providers.py``: instances are built at collection time
(fail-fast for broken constructors), ids are explicit.

Test Categories:
1. Plugin Discovery & Registration (not parametrized — tests on the registry itself)
2. Per-plugin contract + behaviour (parametrized over all plugins)
3. Auto-detection (not parametrized — tests the detector)
4. Generic CSV specific (non-plugin-loop tests)

These tests do NOT require a database connection.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Set

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    BRIMExtractedAssetInfo,
    BRIMParseOutput,
    BRIMPluginInfo,
    is_fake_asset_id,
)
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers.broker_coinbase import CoinbaseBrokerProvider, _parse_coinbase_amount, _parse_coinbase_datetime
from backend.app.services.brim_providers.broker_degiro import DegiroBrokerProvider, _extract_quantity_from_description, _parse_degiro_date
from backend.app.services.brim_providers.broker_directa import DirectaBrokerProvider, _parse_directa_date, _parse_directa_number
from backend.app.services.brim_providers.broker_etoro import EtoroBrokerProvider, _parse_etoro_date, _parse_etoro_number
from backend.app.services.brim_providers.broker_finpension import FinpensionBrokerProvider, _parse_finpension_date, _parse_finpension_number
from backend.app.services.brim_providers.broker_freetrade import FreetradeBrokerProvider, _parse_freetrade_datetime, _parse_freetrade_number
from backend.app.services.brim_providers.broker_generic_csv import parse_decimal
from backend.app.services.brim_providers.broker_ibkr import IBKRBrokerProvider, _parse_ibkr_date, _parse_ibkr_number
from backend.app.services.brim_providers.broker_revolut import RevolutBrokerProvider, _parse_revolut_amount, _parse_revolut_datetime, _parse_revolut_quantity
from backend.app.services.brim_providers.broker_schwab import SchwabBrokerProvider, _parse_schwab_amount, _parse_schwab_date
from backend.app.services.brim_providers.broker_trading212 import Trading212BrokerProvider, _parse_trading212_datetime, _parse_trading212_number
from backend.app.services.provider_registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS & HELPERS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
DEGIRO_SAMPLE = SAMPLE_DIR / "degiro-export.csv"
DIRECTA_SAMPLE = SAMPLE_DIR / "directa-export.csv"
FINPENSION_SAMPLE = SAMPLE_DIR / "finpension-export.csv"
IBKR_SAMPLE = SAMPLE_DIR / "ibkr-trades-export.csv"
IBKR_DEFAULT_CURRENCY_SAMPLE = SAMPLE_DIR / "ibkr-default-currency-export.csv"
# TODO: coinbase-export-sell.csv, freetrade-export-sell.csv and
# ibkr-default-currency-export.csv (used below by TestBrokerParserCoverageHelpers)
# are hand-crafted synthetic fixtures, not real broker exports — column schema
# matches the sibling real-export samples, but the row values were not verified
# against an actual account export. Replace with a real (anonymized) export row
# for each as soon as one becomes available.


def _all_plugins() -> list[tuple[str, BRIMProvider]]:
    """Return (code, instance) pairs for every registered BRIM plugin.

    Built once at collection time: any constructor failure fails the
    whole file immediately, which is what we want.
    """
    BRIMProviderRegistry.auto_discover()
    return [(code, cls()) for code, cls in BRIMProviderRegistry._providers.items()]


_PLUGIN_PARAMS = _all_plugins()
_PLUGIN_IDS = [code for code, _ in _PLUGIN_PARAMS]


def get_all_sample_files() -> List[Path]:
    """Get all sample files (valid ones) in sample_reports/.

    Excludes the ``malformed/`` subdirectory which holds deliberately
    broken fixtures used by :class:`TestGenericMalformedRow`.
    """
    if not SAMPLE_DIR.exists():
        return []
    files: list[Path] = []
    for ext in ["csv", "xlsx", "xls", "json"]:
        for f in SAMPLE_DIR.glob(f"**/*.{ext}"):
            if "malformed" in f.parts:
                continue
            files.append(f)
    return files


def get_sample_files_for_plugin(plugin: BRIMProvider) -> List[Path]:
    """Get sample files that a plugin can parse."""
    if not SAMPLE_DIR.exists():
        return []
    return [f for f in SAMPLE_DIR.glob("*.csv") if plugin.can_parse(f)]


def _first_sample_for_plugin(plugin: BRIMProvider) -> Path | None:
    """Pick a single representative sample for this plugin (pattern-based or any parseable)."""
    pattern = plugin.test_file_pattern
    if pattern:
        for candidate in SAMPLE_DIR.iterdir():
            if candidate.is_file() and pattern in candidate.name.lower():
                return candidate
    if plugin.provider_code == "broker_generic_csv":
        sample = SAMPLE_DIR / "generic_simple.csv"
        if sample.exists():
            return sample
    for candidate in sorted(SAMPLE_DIR.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() == ".csv":
            try:
                if plugin.can_parse(candidate):
                    return candidate
            except Exception:
                continue
    return None


# =============================================================================
# CATEGORY 1: PLUGIN DISCOVERY & REGISTRATION (not parametrized)
# =============================================================================


class TestPluginDiscovery:
    """Tests for plugin auto-discovery and registration (registry-level)."""

    def test_registry_discovers_plugins(self):
        plugins = BRIMProviderRegistry.list_plugin_info()
        assert len(plugins) >= 1, "No plugins discovered"

    def test_all_plugins_have_required_properties(self):
        plugins = BRIMProviderRegistry.list_plugin_info()
        for info in plugins:
            assert info.code, "Plugin missing code"
            assert info.name, f"Plugin {info.code} missing name"
            assert info.description, f"Plugin {info.code} missing description"
            assert info.supported_extensions, f"Plugin {info.code} missing extensions"

    def test_plugin_codes_are_unique(self):
        plugins = BRIMProviderRegistry.list_plugin_info()
        codes = [p.code for p in plugins]
        duplicates = [c for c in codes if codes.count(c) > 1]
        assert not duplicates, f"Duplicate plugin codes: {set(duplicates)}"

    def test_get_nonexistent_provider_returns_none(self):
        assert BRIMProviderRegistry.get_provider_instance("nonexistent_xyz_plugin") is None

    def test_all_sample_files_have_compatible_plugin(self):
        sample_files = get_all_sample_files()
        assert len(sample_files) > 0, "No sample files found"
        uncovered = [f.name for f in sample_files if not BRIMProviderRegistry.auto_detect_plugin(f)]
        assert not uncovered, f"Files without compatible plugin: {uncovered}"

    def test_all_plugins_used_at_least_once(self):
        plugins = BRIMProviderRegistry.list_plugin_info()
        sample_files = get_all_sample_files()

        used: Set[str] = set()
        for f in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(f)
            if detected:
                used.add(detected)

        registered = {p.code for p in plugins}
        unused = registered - used - {"broker_generic_csv"}
        assert not unused, f"Plugins without sample files (add samples!): {unused}"


# =============================================================================
# CATEGORY 2: PER-PLUGIN CONTRACT + BEHAVIOUR (parametrized over all plugins)
# =============================================================================


@pytest.mark.parametrize(("code", "plugin"), _PLUGIN_PARAMS, ids=_PLUGIN_IDS)
class TestBRIMPlugin:
    """Unified parametrized suite running for each registered BRIM plugin.

    Merges the former ``TestPluginInterface`` + ``TestBRIMPluginsContract``
    into a single class with consistent parametrization: each test receives
    ``(code, plugin)`` directly — no per-test registry lookup.
    """

    # --- Identity & metadata ---

    def test_provider_instance_identity(self, code: str, plugin: BRIMProvider):
        assert isinstance(plugin, BRIMProvider)
        assert plugin.provider_code == code

    def test_provider_metadata_is_valid(self, code: str, plugin: BRIMProvider):
        assert plugin.provider_code, "Empty provider_code"
        assert plugin.provider_name, "Empty provider_name"
        assert plugin.description, "Empty description"
        assert plugin.supported_extensions, "No supported extensions"
        assert all(ext.startswith(".") for ext in plugin.supported_extensions)

    def test_plugin_version_is_non_empty_string(self, code: str, plugin: BRIMProvider):
        version = plugin.plugin_version
        assert isinstance(version, str) and version.strip(), f"{code}: plugin_version must be non-empty string"

    def test_docs_url_is_string_or_none(self, code: str, plugin: BRIMProvider):
        url = plugin.docs_url
        if url is not None:
            assert isinstance(url, str) and url.strip()

    def test_to_plugin_info_propagates_fields(self, code: str, plugin: BRIMProvider):
        info = plugin.to_plugin_info()
        assert isinstance(info, BRIMPluginInfo)
        assert info.code == code
        assert info.plugin_version == plugin.plugin_version
        assert info.docs_url == plugin.docs_url

    # --- Parse behaviour ---

    def test_parse_returns_brim_parse_output(self, code: str, plugin: BRIMProvider):
        sample = _first_sample_for_plugin(plugin)
        if sample is None:
            pytest.skip(f"No compatible sample report for {code}")
        out = plugin.parse(sample, broker_id=1)
        assert isinstance(out, BRIMParseOutput)
        assert isinstance(out.transactions, list)
        assert isinstance(out.warnings, list)
        assert isinstance(out.extracted_assets, dict)

    def test_parse_produces_transactions(self, code: str, plugin: BRIMProvider):
        sample = _first_sample_for_plugin(plugin)
        if sample is None:
            pytest.skip(f"No compatible sample report for {code}")
        out = plugin.parse(sample, broker_id=1)
        assert len(out.transactions) > 0, f"No transactions parsed from {sample.name}"
        assert all(isinstance(tx, TXCreateItem) for tx in out.transactions)

    def test_extracted_assets_consistent_with_transactions(self, code: str, plugin: BRIMProvider):
        sample = _first_sample_for_plugin(plugin)
        if sample is None:
            pytest.skip(f"No compatible sample report for {code}")
        out = plugin.parse(sample, broker_id=1)
        for fake_id, info in out.extracted_assets.items():
            assert isinstance(fake_id, int)
            assert isinstance(info, BRIMExtractedAssetInfo)
        tx_asset_ids = {tx.asset_id for tx in out.transactions if tx.asset_id is not None}
        missing = tx_asset_ids - set(out.extracted_assets.keys())
        assert not missing, f"{code}: transaction asset_ids not in extracted_assets: {missing}"

    def test_parse_is_idempotent(self, code: str, plugin: BRIMProvider):
        """Same input → same output. Required for plugin_version-driven caching.

        Compares ``.model_dump(mode="json")`` of BRIMParseOutput to avoid
        false negatives from object identity.
        """
        sample = _first_sample_for_plugin(plugin)
        if sample is None:
            pytest.skip(f"No compatible sample report for {code}")
        out1 = plugin.parse(sample, broker_id=1)
        out2 = plugin.parse(sample, broker_id=1)
        assert out1.model_dump(mode="json") == out2.model_dump(mode="json"), f"{code}: parse() is not idempotent on {sample.name}"

    def test_parse_produces_valid_fake_ids(self, code: str, plugin: BRIMProvider):
        """Every asset_id key in extracted_assets must be a recognized fake id."""
        sample = _first_sample_for_plugin(plugin)
        if sample is None:
            pytest.skip(f"No compatible sample report for {code}")
        out = plugin.parse(sample, broker_id=1)
        for fake_id in out.extracted_assets.keys():
            assert is_fake_asset_id(fake_id), f"{code}: extracted_assets key {fake_id} is not a valid fake id"

    def test_broker_id_propagated_on_all_samples_and_all_tx(self, code: str, plugin: BRIMProvider):
        """broker_id must be propagated on every TX of every compatible sample."""
        if code == "broker_generic_csv":
            samples = [f for f in get_all_sample_files() if BRIMProviderRegistry.auto_detect_plugin(f) == "broker_generic_csv"]
        else:
            samples = get_sample_files_for_plugin(plugin)

        if not samples:
            pytest.skip(f"{code} has no compatible sample files")

        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            for i, tx in enumerate(out.transactions):
                assert tx.broker_id == 1, f"{code} [{sample.name}] tx[{i}] broker_id={tx.broker_id} != 1"

    def test_all_transactions_are_schema_valid(self, code: str, plugin: BRIMProvider):
        """Every TX the plugin creates must pass schema validation (no validation_issues).

        Warnings and explicit row-skips are acceptable — the plugin may choose
        not to import a row and that is fine.  But if ``_create_transaction()``
        is called and produces a ``BRIMValidationIssue``, the plugin has a
        sign-rule or field-rule bug that must be fixed before the sample data
        can be imported correctly.

        Runs against **all** compatible sample files for the plugin so that
        edge-case rows (dividends, fees, corporate actions) are exercised, not
        just the first file that happens to parse cleanly.
        """
        if code == "broker_generic_csv":
            samples = [f for f in get_all_sample_files() if BRIMProviderRegistry.auto_detect_plugin(f) == "broker_generic_csv"]
        else:
            samples = get_sample_files_for_plugin(plugin)

        if not samples:
            pytest.skip(f"{code} has no compatible sample files")

        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            if out.validation_issues:
                details = "\n".join(f"  Row {issue.row}: {issue.code}" + (f" field={issue.field}" if issue.field else "") + (f" ctx={issue.params}" if issue.params else "") + f" — {issue.message}" for issue in out.validation_issues)
                pytest.fail(f"{code} [{sample.name}] produced {len(out.validation_issues)}" f" schema validation issue(s):\n{details}\n" f"Fix the plugin's sign rules or add an explicit skip/warning" f" for rows that cannot be imported.")

        """Plugin must parse ALL its compatible sample files without raising."""
        if code == "broker_generic_csv":
            samples = [f for f in get_all_sample_files() if BRIMProviderRegistry.auto_detect_plugin(f) == "broker_generic_csv"]
        else:
            samples = get_sample_files_for_plugin(plugin)

        if not samples:
            pytest.skip(f"{code} has no compatible sample files")

        for sample in samples:
            try:
                out = plugin.parse(sample, broker_id=1)
                assert len(out.transactions) > 0, f"No transactions from {sample.name}"
            except Exception as e:
                pytest.fail(f"{code} failed to parse {sample.name}: {e}")


# =============================================================================
# CATEGORY 2b: MALFORMED INPUT — parser-level warnings (not parametrized)
# =============================================================================


class TestGenericMalformedRow:
    """Validate that the generic CSV plugin surfaces warnings or raises
    :class:`BRIMParseError` on a deliberately corrupt row, without
    crashing with a raw exception.

    Scope limited to the generic plugin because the malformed sample is
    format-agnostic; broker-specific plugins have their own structural
    constraints (tested via ``test_all_parseable_samples_succeed``).
    """

    MALFORMED_SAMPLE = SAMPLE_DIR / "malformed" / "generic_malformed_row.csv"

    def test_malformed_sample_file_exists(self):
        assert self.MALFORMED_SAMPLE.exists(), f"Required sample missing: {self.MALFORMED_SAMPLE.name}. " "Add a minimal CSV with one row that has an unparseable date or missing required column."

    def test_parse_malformed_either_warns_or_raises_brim_error(self):
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None

        try:
            out = plugin.parse(self.MALFORMED_SAMPLE, broker_id=1)
        except BRIMParseError:
            # Acceptable: structural error raised as BRIMParseError
            return
        # Non-raising path: must surface at least one warning
        assert len(out.warnings) > 0, "Malformed row should produce a warning or raise BRIMParseError"


# =============================================================================
# CATEGORY 3: AUTO-DETECTION TESTS (not parametrized)
# =============================================================================


class TestAutoDetection:
    """Tests for plugin auto-detection functionality."""

    def test_auto_detect_returns_valid_plugin(self):
        sample_files = get_all_sample_files()
        assert len(sample_files) > 0, "No sample files to test"
        for sample_file in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
            assert detected is not None, f"No plugin detected for {sample_file.name}"
            assert BRIMProviderRegistry.get_provider_instance(detected) is not None

    def test_detection_prefers_specific_over_generic(self):
        sample_files = get_all_sample_files()
        specific = sum(1 for f in sample_files if BRIMProviderRegistry.auto_detect_plugin(f) != "broker_generic_csv")
        assert specific > 0, "No broker-specific plugins detected"

    def test_specific_broker_detection_via_plugin_pattern(self):
        sample_files = get_all_sample_files()
        for info in BRIMProviderRegistry.list_plugin_info():
            plugin = BRIMProviderRegistry.get_provider_instance(info.code)
            pattern = plugin.test_file_pattern
            if pattern is None:
                continue
            matching = [f for f in sample_files if pattern in f.name.lower()]
            if not matching:
                continue
            for sample_file in matching:
                detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
                assert detected == info.code, f"{sample_file.name} detected as {detected}, expected {info.code}"


# =============================================================================
# CATEGORY 4: GENERIC CSV SPECIFIC TESTS (not parametrized)
# =============================================================================


class TestGenericCSVPlugin:
    """Specific tests for the generic CSV fallback plugin."""

    REQUIRED_GENERIC_FILES = [
        "generic_simple.csv",
        "generic_dates.csv",
        "generic_types.csv",
        "generic_with_assets.csv",
    ]

    def test_required_generic_files_exist(self):
        for filename in self.REQUIRED_GENERIC_FILES:
            filepath = SAMPLE_DIR / filename
            assert filepath.exists(), f"Required generic sample file missing: {filename}"

    def test_generic_can_parse_any_csv(self):
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None
        for sample_file in get_all_sample_files():
            assert plugin.can_parse(sample_file), f"Generic plugin should parse {sample_file.name}"

    def test_generic_handles_multiple_date_formats(self):
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        dates_file = SAMPLE_DIR / "generic_dates.csv"
        if not dates_file.exists():
            pytest.skip("generic_dates.csv not found")
        out = plugin.parse(dates_file, broker_id=1)
        assert len(out.transactions) > 0
        for tx in out.transactions:
            assert tx.date is not None

    def test_generic_has_lowest_priority(self):
        generic = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert generic.detection_priority < 100
        for info in BRIMProviderRegistry.list_plugin_info():
            if info.code != "broker_generic_csv":
                other = BRIMProviderRegistry.get_provider_instance(info.code)
                assert other.detection_priority >= generic.detection_priority, f"{info.code} priority should be >= generic"

    def test_generic_has_no_test_file_pattern(self):
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin.test_file_pattern is None


class TestBrokerParserCoverageHelpers:
    """Targeted helper and parser happy-path coverage for broker-specific plugins."""

    COINBASE_SELL_SAMPLE = SAMPLE_DIR / "coinbase-export-sell.csv"
    FREETRADE_SELL_SAMPLE = SAMPLE_DIR / "freetrade-export-sell.csv"
    IBKR_DEFAULT_CURRENCY_SAMPLE = SAMPLE_DIR / "ibkr-default-currency-export.csv"
    # NOTE: the 3 samples above are synthetic (hand-crafted to match the real
    # export column schema), not captured from a real broker account. See
    # TODO at their SAMPLE_DIR definitions above — swap in a real row when available.

    @pytest.mark.parametrize(
        ("provider", "sample_name"),
        [
            (CoinbaseBrokerProvider(), "coinbase-export.csv"),
            (DegiroBrokerProvider(), "degiro-export.csv"),
            (DirectaBrokerProvider(), "directa-export.csv"),
            (EtoroBrokerProvider(), "etoro-export.csv"),
            (FinpensionBrokerProvider(), "finpension-export.csv"),
            (FreetradeBrokerProvider(), "freetrade-export.csv"),
            (IBKRBrokerProvider(), "ibkr-trades-export.csv"),
            (RevolutBrokerProvider(), "revolut-invest-export.csv"),
            (SchwabBrokerProvider(), "schwab-export.csv"),
            (Trading212BrokerProvider(), "trading212-export.csv"),
        ],
        ids=["coinbase", "degiro", "directa", "etoro", "finpension", "freetrade", "ibkr", "revolut", "schwab", "trading212"],
    )
    def test_broker_specific_can_parse_true_and_reject_non_csv(self, provider: BRIMProvider, sample_name: str):
        assert provider.can_parse(SAMPLE_DIR / sample_name)
        assert not provider.can_parse(SAMPLE_DIR / "README.md")

    @pytest.mark.parametrize(
        ("parser", "value", "expected"),
        [
            (_parse_coinbase_datetime, "2025-01-17", date(2025, 1, 17)),
            (_parse_degiro_date, "17-12-2022", date(2022, 12, 17)),
            (_parse_directa_date, "30-12-2024", date(2024, 12, 30)),
            (_parse_etoro_date, "17/01/2025", date(2025, 1, 17)),
            (_parse_finpension_date, "2023-07-11", date(2023, 7, 11)),
            (_parse_freetrade_datetime, "2024-03-28", date(2024, 3, 28)),
            (_parse_ibkr_date, '"20230522"', date(2023, 5, 22)),
            (_parse_revolut_datetime, "2019-12-02", date(2019, 12, 2)),
            (_parse_schwab_date, "03/24/2025 as of 03/25/2025", date(2025, 3, 24)),
            (_parse_trading212_datetime, "2023-12-27 12:05:25", date(2023, 12, 27)),
        ],
        ids=["coinbase", "degiro", "directa", "etoro", "finpension", "freetrade", "ibkr", "revolut", "schwab", "trading212"],
    )
    def test_date_helpers_accept_supported_alternate_formats(self, parser, value: str, expected: date):
        assert parser(value) == expected

    @pytest.mark.parametrize(
        "parser",
        [
            _parse_degiro_date,
            _parse_directa_date,
            _parse_finpension_date,
            _parse_ibkr_date,
        ],
        ids=["degiro", "directa", "finpension", "ibkr"],
    )
    def test_targeted_date_helpers_return_none_for_blank_values(self, parser):
        assert parser("") is None

    @pytest.mark.parametrize(
        ("parser", "value", "expected"),
        [
            (_parse_coinbase_amount, "€1,234.56", Decimal("1234.56")),
            (_parse_directa_number, "-431,04", Decimal("-431.04")),
            (_parse_etoro_number, "1.234,56", Decimal("1234.56")),
            (_parse_finpension_number, "-0.821800", Decimal("-0.821800")),
            (_parse_freetrade_number, "250.50", Decimal("250.50")),
            (_parse_ibkr_number, '"-5"', Decimal("-5")),
            (_parse_revolut_quantity, "0,76672417", Decimal("0.76672417")),
            (_parse_schwab_amount, '"$1,259.59"', Decimal("1259.59")),
            (_parse_trading212_number, "€1,234.56", Decimal("1234.56")),
        ],
        ids=["coinbase", "directa", "etoro", "finpension", "freetrade", "ibkr", "revolut-qty", "schwab", "trading212"],
    )
    def test_number_helpers_accept_supported_formats(self, parser, value: str, expected: Decimal):
        assert parser(value) == expected

    @pytest.mark.parametrize(
        "parser",
        [
            _parse_directa_number,
            _parse_finpension_number,
            _parse_ibkr_number,
        ],
        ids=["directa", "finpension", "ibkr"],
    )
    def test_targeted_number_helpers_return_none_for_blank_values(self, parser):
        assert parser("") is None

    def test_revolut_amount_helper_parses_negative_euro_amount(self):
        assert _parse_revolut_amount("-€30,50") == (Decimal("-30.50"), "EUR")

    def test_degiro_extract_quantity_handles_product_name_format(self):
        assert _extract_quantity_from_description("Compra 6 ISHARES MSCI WOR A@49,785 EUR") == Decimal("6")

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("123.45", Decimal("123.45")),
            ("123,45", Decimal("123.45")),
            ("1,234.56", Decimal("1234.56")),
            ("1.234,56", Decimal("1234.56")),
            ("(123.45)", Decimal("-123.45")),
        ],
    )
    def test_generic_parse_decimal_handles_supported_formats(self, value: str, expected: Decimal):
        assert parse_decimal(value) == expected

    def test_coinbase_parse_sell_sample_creates_sell_and_fee_transactions(self):
        # TODO: COINBASE_SELL_SAMPLE is a synthetic fixture (see note above) —
        # replace with a real anonymized export row when available.
        out = CoinbaseBrokerProvider().parse(self.COINBASE_SELL_SAMPLE, broker_id=42)

        assert [tx.type for tx in out.transactions] == [TransactionType.SELL, TransactionType.FEE]
        sell_tx, fee_tx = out.transactions
        assert sell_tx.broker_id == 42
        assert sell_tx.date == date(2025, 2, 1)
        assert sell_tx.quantity == Decimal("-0.01000000")
        assert sell_tx.cash is not None and sell_tx.cash.amount == Decimal("995.00")
        assert fee_tx.cash is not None and fee_tx.cash.amount == Decimal("-5.00")
        assert sell_tx.asset_id in out.extracted_assets
        assert out.extracted_assets[sell_tx.asset_id].extracted_symbol == "BTC"

    def test_freetrade_parse_sell_sample_creates_negative_quantity(self):
        # TODO: FREETRADE_SELL_SAMPLE is a synthetic fixture (see note above) —
        # replace with a real anonymized export row when available.
        out = FreetradeBrokerProvider().parse(self.FREETRADE_SELL_SAMPLE, broker_id=7)

        assert len(out.transactions) == 1
        tx = out.transactions[0]
        assert tx.type == TransactionType.SELL
        assert tx.broker_id == 7
        assert tx.date == date(2024, 4, 20)
        assert tx.quantity == Decimal("-2.00000000")
        assert tx.cash is not None and tx.cash.amount == Decimal("250.50")
        assert tx.asset_id in out.extracted_assets
        assert out.extracted_assets[tx.asset_id].extracted_isin == "US17275R1023"

    def test_finpension_parse_sample_covers_asset_and_cash_transactions(self):
        out = FinpensionBrokerProvider().parse(FINPENSION_SAMPLE, broker_id=7)

        deposit = next(tx for tx in out.transactions if tx.type == TransactionType.DEPOSIT)
        dividend = next(tx for tx in out.transactions if tx.type == TransactionType.DIVIDEND)

        assert deposit.broker_id == 7
        assert deposit.asset_id is None
        assert deposit.cash is not None and deposit.cash.code == "CHF"
        assert dividend.asset_id in out.extracted_assets
        assert dividend.quantity == Decimal("0")
        assert out.extracted_assets[dividend.asset_id].extracted_isin is not None

    def test_ibkr_parse_sample_defaults_currency_and_normalizes_sell_quantity(self):
        # TODO: IBKR_DEFAULT_CURRENCY_SAMPLE is a synthetic fixture (see note above) —
        # replace with a real anonymized export row when available.
        out = IBKRBrokerProvider().parse(self.IBKR_DEFAULT_CURRENCY_SAMPLE, broker_id=11)

        sell_tx = next(tx for tx in out.transactions if tx.type == TransactionType.SELL)
        fee_tx = next(tx for tx in out.transactions if tx.type == TransactionType.FEE)

        assert sell_tx.broker_id == 11
        assert sell_tx.quantity == Decimal("-5")
        assert sell_tx.cash is not None and sell_tx.cash.code == "USD" and sell_tx.cash.amount == Decimal("950")
        assert fee_tx.cash is not None and fee_tx.cash.code == "USD" and fee_tx.cash.amount == Decimal("-1")
        assert sell_tx.asset_id in out.extracted_assets

    def test_directa_parse_sample_links_tax_to_asset(self):
        """TAX rows carrying ISIN (e.g. "Rit.cedola obb." bond withholding tax)
        must resolve asset_id — the sample already contains such real rows.
        """
        out = DirectaBrokerProvider().parse(DIRECTA_SAMPLE, broker_id=1)

        tax_txs = [tx for tx in out.transactions if tx.type == TransactionType.TAX]
        assert tax_txs, "sample must contain at least one TAX row"

        linked = [tx for tx in tax_txs if tx.asset_id is not None]
        assert linked, "at least one TAX row in the sample has an ISIN and must resolve an asset"
        for tx in linked:
            assert tx.asset_id in out.extracted_assets
            assert out.extracted_assets[tx.asset_id].extracted_isin is not None

        # "Ritenuta su plusvalenza" is a generic capital-gains tax row with no
        # ISIN/ticker in the source data — must stay unlinked, never a placeholder.
        generic_tax = next((tx for tx in tax_txs if tx.description and "plusvalenza" in tx.description.lower()), None)
        assert generic_tax is not None, "sample must contain the generic 'Ritenuta su plusvalenza' row"
        assert generic_tax.asset_id is None

    def test_schwab_parse_sample_links_adr_fee_and_tax_to_asset(self):
        """FEE/TAX rows carrying Symbol (e.g. "ADR Mgmt Fee", "Foreign Tax Paid")
        must resolve the same asset_id — the bundled sample already contains
        both for ticker "IBN". Account-level "Advisor Fee" rows (no Symbol)
        must remain unlinked — no regression on that existing behaviour.
        """
        out = SchwabBrokerProvider().parse(SAMPLE_DIR / "schwab-export.csv", broker_id=1)

        adr_fee = next(tx for tx in out.transactions if tx.type == TransactionType.FEE and tx.description and "adr mgmt fee" in tx.description.lower())
        foreign_tax = next(tx for tx in out.transactions if tx.type == TransactionType.TAX and tx.description and "foreign tax paid" in tx.description.lower())

        assert adr_fee.asset_id is not None
        assert foreign_tax.asset_id is not None
        assert adr_fee.asset_id == foreign_tax.asset_id, "same underlying symbol (IBN) must resolve to the same asset"
        assert out.extracted_assets[adr_fee.asset_id].extracted_symbol == "IBN"

        advisor_fees = [tx for tx in out.transactions if tx.type == TransactionType.FEE and tx.description and "advisor fee" in tx.description.lower()]
        assert advisor_fees, "sample must contain account-level Advisor Fee rows"
        assert all(tx.asset_id is None for tx in advisor_fees)

    def test_finpension_parse_sample_fee_without_asset_stays_unlinked(self):
        """'Flat-rate administrative fee' is account-level in the bundled sample
        (no ISIN/asset name) — regression lock proving the new asset_optional
        branch never forces a placeholder.
        """
        out = FinpensionBrokerProvider().parse(FINPENSION_SAMPLE, broker_id=1)

        fee_txs = [tx for tx in out.transactions if tx.type == TransactionType.FEE]
        assert fee_txs, "sample must contain at least one FEE row"
        assert all(tx.asset_id is None for tx in fee_txs)

    def test_revolut_parse_sample_fee_without_asset_stays_unlinked(self):
        """'Custody fee' is account-level in the bundled sample (no ticker) —
        regression lock for the new asset_optional branch.
        """
        out = RevolutBrokerProvider().parse(SAMPLE_DIR / "revolut-invest-export.csv", broker_id=1)

        fee_txs = [tx for tx in out.transactions if tx.type == TransactionType.FEE]
        assert fee_txs, "sample must contain at least one FEE row"
        assert all(tx.asset_id is None for tx in fee_txs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
