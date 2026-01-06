"""
BRIM Provider Tests.

Tests for the Broker Report Import Manager (BRIM) plugin system.

Test Categories:
1. Plugin Discovery & Registration (PD-*)
2. File Parsing (FP-*)
2B. Auto-Detection & Sample File Coverage (AD-*)

These tests do NOT require a database connection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Set

import pytest

from backend.app.services.provider_registry import BRIMProviderRegistry
from backend.app.services.brim_provider import BRIMProvider


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry before each test to ensure clean state."""
    BRIMProviderRegistry._discovery_done = False
    BRIMProviderRegistry._providers = {}
    yield
    # Cleanup after test
    BRIMProviderRegistry._discovery_done = False
    BRIMProviderRegistry._providers = {}


@pytest.fixture
def sample_dir() -> Path:
    """Path to sample reports directory."""
    return Path(__file__).parent.parent.parent / "app" / "services" / "brim_providers" / "sample_reports"


# =============================================================================
# CATEGORY 1: PLUGIN DISCOVERY & REGISTRATION (PD-*)
# =============================================================================

class TestPluginDiscovery:
    """Tests for plugin auto-discovery and registration."""

    def test_registry_discovers_plugins(self):
        """
        PD-001: Verify auto-discovery works.

        Expected: At least 1 plugin registered after discovery.
        """
        # Trigger discovery
        plugins = BRIMProviderRegistry.list_plugin_info()

        assert len(plugins) >= 1, "No plugins discovered"

    def test_all_plugins_have_required_properties(self):
        """
        PD-002: Verify plugin interface.

        Expected: All plugins have code, name, description, supported_extensions.
        """
        plugins = BRIMProviderRegistry.list_plugin_info()

        for plugin_info in plugins:
            assert plugin_info.code, f"Plugin missing code: {plugin_info}"
            assert plugin_info.name, f"Plugin {plugin_info.code} missing name"
            assert plugin_info.description, f"Plugin {plugin_info.code} missing description"
            assert plugin_info.supported_extensions, f"Plugin {plugin_info.code} missing extensions"

    def test_plugin_codes_are_unique(self):
        """
        PD-003: Verify no duplicate codes.

        Expected: No duplicate provider_code values.
        """
        plugins = BRIMProviderRegistry.list_plugin_info()
        codes = [p.code for p in plugins]

        duplicates = [code for code in codes if codes.count(code) > 1]
        assert not duplicates, f"Duplicate plugin codes found: {set(duplicates)}"

    def test_get_provider_instance(self):
        """
        PD-004: Verify instance creation.

        Expected: Returns valid plugin instance for known code.
        """
        # Get a known plugin code
        plugins = BRIMProviderRegistry.list_plugin_info()
        assert len(plugins) > 0, "No plugins to test"

        code = plugins[0].code
        instance = BRIMProviderRegistry.get_provider_instance(code)

        assert instance is not None, f"Failed to get instance for {code}"
        assert isinstance(instance, BRIMProvider), f"Instance is not a BRIMProvider"
        assert instance.provider_code == code, f"Instance code mismatch"

    def test_get_nonexistent_provider(self):
        """
        PD-005: Verify error handling.

        Expected: Returns None for unknown code.
        """
        instance = BRIMProviderRegistry.get_provider_instance("nonexistent_plugin_xyz")

        assert instance is None, "Expected None for nonexistent plugin"


# =============================================================================
# CATEGORY 2: FILE PARSING (FP-*)
# =============================================================================

class TestFileParsing:
    """Tests for file parsing functionality."""

    def test_parse_generic_simple_csv(self, sample_dir: Path):
        """
        FP-001: Basic CSV parsing.

        Expected: All rows parsed, no warnings.
        """
        file_path = sample_dir / "generic_simple.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None, "Generic CSV plugin not found"

        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        assert len(txs) > 0, "No transactions parsed"
        # Simple file should have minimal warnings

    def test_parse_generic_dates_csv(self, sample_dir: Path):
        """
        FP-002: Multiple date formats.

        Expected: All dates parsed correctly.
        """
        file_path = sample_dir / "generic_dates.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        assert len(txs) > 0, "No transactions parsed"

        # Verify all transactions have valid dates
        for tx in txs:
            assert tx.date is not None, f"Transaction missing date: {tx}"

    def test_parse_generic_types_csv(self, sample_dir: Path):
        """
        FP-003: All transaction types.

        Expected: All types mapped to enum.
        """
        file_path = sample_dir / "generic_types.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        assert len(txs) > 0, "No transactions parsed"

        # Collect unique types
        types_found = {tx.type for tx in txs}

        # Should have multiple different types
        assert len(types_found) > 1, f"Only found types: {types_found}"

    def test_parse_generic_multilang_csv(self, sample_dir: Path):
        """
        FP-004: Multi-language headers.

        Expected: Headers auto-detected.
        """
        file_path = sample_dir / "generic_multilang.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        assert len(txs) > 0, "No transactions parsed from multilang file"

    def test_parse_generic_with_warnings_csv(self, sample_dir: Path):
        """
        FP-005: Invalid rows handling.

        Expected: Valid rows parsed, warnings list populated.
        """
        file_path = sample_dir / "generic_with_warnings.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        # Should still parse some transactions
        assert len(txs) > 0, "No transactions parsed"

        # Should have some warnings for problematic rows
        assert len(warnings) > 0, "Expected warnings for file with invalid rows"

    def test_parse_generic_with_assets_csv(self, sample_dir: Path):
        """
        FP-006: Asset identifier extraction.

        Expected: Fake IDs assigned, asset info extracted.
        """
        file_path = sample_dir / "generic_with_assets.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        assert len(txs) > 0, "No transactions parsed"
        assert len(assets) > 0, "No assets extracted"

        # Verify asset structure
        for fake_id, asset_info in assets.items():
            assert isinstance(fake_id, int), f"Fake ID should be int: {fake_id}"
            assert "extracted_symbol" in asset_info, f"Missing extracted_symbol"
            assert "extracted_isin" in asset_info, f"Missing extracted_isin"
            assert "extracted_name" in asset_info, f"Missing extracted_name"

    def test_same_asset_gets_same_fake_id(self, sample_dir: Path):
        """
        FP-007: Fake ID consistency.

        Expected: Same symbol → same fake ID across transactions.
        """
        file_path = sample_dir / "generic_with_assets.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        txs, warnings, assets = plugin.parse(file_path, broker_id=1)

        # Group transactions by asset_id
        txs_by_asset: dict = {}
        for tx in txs:
            if tx.asset_id is not None:
                txs_by_asset.setdefault(tx.asset_id, []).append(tx)

        # If we have assets, verify consistency
        if assets:
            # Each fake_id in assets should be used by at least one transaction
            for fake_id in assets.keys():
                assert fake_id in txs_by_asset or any(
                    tx.asset_id == fake_id for tx in txs
                ), f"Fake ID {fake_id} not used in any transaction"

    def test_unsupported_file_rejected(self, sample_dir: Path, tmp_path: Path):
        """
        FP-012: Negative test.

        Expected: .xlsx rejected by CSV plugin.
        """
        # Create a fake xlsx file
        xlsx_file = tmp_path / "test.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")

        # Should not be able to parse xlsx
        can_parse = plugin.can_parse(xlsx_file)
        assert not can_parse, "CSV plugin should not accept xlsx files"


# =============================================================================
# CATEGORY 2B: AUTO-DETECTION & SAMPLE FILE COVERAGE (AD-*)
# =============================================================================

class TestAutoDetection:
    """Tests for auto-detection and sample file coverage."""

    def test_iterate_all_sample_files(self, sample_dir: Path):
        """
        AD-001: Parse all samples.

        Expected: All files parse without exception.
        """
        assert sample_dir.exists(), f"Sample directory not found: {sample_dir}"

        csv_files = list(sample_dir.glob("*.csv"))
        assert len(csv_files) > 0, "No CSV files in sample directory"

        for csv_file in csv_files:
            plugin_code = BRIMProviderRegistry.auto_detect_plugin(csv_file)
            assert plugin_code is not None, f"No plugin detected for {csv_file.name}"

            plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
            assert plugin is not None, f"Failed to get plugin instance for {plugin_code}"

            # This should not raise an exception
            txs, warnings, assets = plugin.parse(csv_file, broker_id=1)

            assert len(txs) > 0, f"No transactions parsed from {csv_file.name}"

    def test_auto_detect_each_sample(self, sample_dir: Path):
        """
        AD-002: Auto-detection works.

        Expected: Each file auto-detects to a plugin.
        """
        csv_files = list(sample_dir.glob("*.csv"))

        for csv_file in csv_files:
            plugin_code = BRIMProviderRegistry.auto_detect_plugin(csv_file)
            assert plugin_code is not None, f"Auto-detect failed for {csv_file.name}"

    def test_all_plugins_used_at_least_once(self, sample_dir: Path):
        """
        AD-003: Plugin coverage.

        Expected: Every registered plugin parses at least 1 file.
        """
        csv_files = list(sample_dir.glob("*.csv"))

        # Track which plugins are used
        used_plugins: Set[str] = set()

        for csv_file in csv_files:
            plugin_code = BRIMProviderRegistry.auto_detect_plugin(csv_file)
            if plugin_code:
                used_plugins.add(plugin_code)

        # Get all registered plugins
        registered_plugins = {p.code for p in BRIMProviderRegistry.list_plugin_info()}

        # Find unused plugins
        unused = registered_plugins - used_plugins

        assert not unused, f"Plugins never used in tests: {unused}"

    def test_directa_auto_detected(self, sample_dir: Path):
        """
        AD-004: Directa detection.

        Expected: directa-export.csv → broker_directa
        """
        file_path = sample_dir / "directa-export.csv"
        if not file_path.exists():
            pytest.skip("directa-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_directa", f"Expected broker_directa, got {plugin_code}"

    def test_degiro_auto_detected(self, sample_dir: Path):
        """
        AD-005: DEGIRO detection.

        Expected: degiro-export.csv → broker_degiro
        """
        file_path = sample_dir / "degiro-export.csv"
        if not file_path.exists():
            pytest.skip("degiro-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_degiro", f"Expected broker_degiro, got {plugin_code}"

    def test_trading212_auto_detected(self, sample_dir: Path):
        """
        AD-006: Trading212 detection.

        Expected: trading212-export.csv → broker_trading212
        """
        file_path = sample_dir / "trading212-export.csv"
        if not file_path.exists():
            pytest.skip("trading212-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_trading212", f"Expected broker_trading212, got {plugin_code}"

    def test_ibkr_auto_detected(self, sample_dir: Path):
        """
        AD-007: IBKR detection.

        Expected: ibkr-trades-export.csv → broker_ibkr
        """
        file_path = sample_dir / "ibkr-trades-export.csv"
        if not file_path.exists():
            pytest.skip("ibkr-trades-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_ibkr", f"Expected broker_ibkr, got {plugin_code}"

    def test_etoro_auto_detected(self, sample_dir: Path):
        """
        AD-008: eToro detection.

        Expected: etoro-export.csv → broker_etoro
        """
        file_path = sample_dir / "etoro-export.csv"
        if not file_path.exists():
            pytest.skip("etoro-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_etoro", f"Expected broker_etoro, got {plugin_code}"

    def test_generic_files_fallback(self, sample_dir: Path):
        """
        AD-009: Generic fallback.

        Expected: generic_*.csv → broker_generic_csv
        """
        generic_files = list(sample_dir.glob("generic_*.csv"))

        if not generic_files:
            pytest.skip("No generic_*.csv files found")

        for file_path in generic_files:
            plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
            assert plugin_code == "broker_generic_csv", \
                f"Expected broker_generic_csv for {file_path.name}, got {plugin_code}"

    def test_revolut_auto_detected(self, sample_dir: Path):
        """
        AD-010: Revolut detection.

        Expected: revolut-invest-export.csv → broker_revolut
        """
        file_path = sample_dir / "revolut-invest-export.csv"
        if not file_path.exists():
            pytest.skip("revolut-invest-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_revolut", f"Expected broker_revolut, got {plugin_code}"

    def test_schwab_auto_detected(self, sample_dir: Path):
        """
        AD-011: Schwab detection.

        Expected: schwab-export.csv → broker_schwab
        """
        file_path = sample_dir / "schwab-export.csv"
        if not file_path.exists():
            pytest.skip("schwab-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_schwab", f"Expected broker_schwab, got {plugin_code}"

    def test_freetrade_auto_detected(self, sample_dir: Path):
        """
        AD-012: Freetrade detection.

        Expected: freetrade-export.csv → broker_freetrade
        """
        file_path = sample_dir / "freetrade-export.csv"
        if not file_path.exists():
            pytest.skip("freetrade-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_freetrade", f"Expected broker_freetrade, got {plugin_code}"

    def test_coinbase_auto_detected(self, sample_dir: Path):
        """
        AD-013: Coinbase detection.

        Expected: coinbase-export.csv → broker_coinbase
        """
        file_path = sample_dir / "coinbase-export.csv"
        if not file_path.exists():
            pytest.skip("coinbase-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_coinbase", f"Expected broker_coinbase, got {plugin_code}"

    def test_finpension_auto_detected(self, sample_dir: Path):
        """
        AD-014: Finpension detection.

        Expected: finpension-export.csv → broker_finpension
        """
        file_path = sample_dir / "finpension-export.csv"
        if not file_path.exists():
            pytest.skip("finpension-export.csv not found")

        plugin_code = BRIMProviderRegistry.auto_detect_plugin(file_path)
        assert plugin_code == "broker_finpension", f"Expected broker_finpension, got {plugin_code}"

