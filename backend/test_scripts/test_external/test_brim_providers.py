"""
BRIM Provider Tests - Parametrized Test Suite.

Tests all registered BRIM (Broker Report Import Manager) plugins with uniform test suite.
Pattern similar to test_asset_providers.py and test_fx_providers.py.

Test Categories:
1. Plugin Discovery & Registration (run once)
2. Parametrized tests for each plugin (run for ALL registered plugins)
3. Sample File Coverage (ensure all samples are processed)

These tests do NOT require a database connection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest

from backend.app.services.provider_registry import BRIMProviderRegistry
from backend.app.services.brim_provider import BRIMProvider
from backend.app.schemas.transactions import TXCreateItem


# =============================================================================
# CONSTANTS
# =============================================================================

SAMPLE_DIR = Path(__file__).parent.parent.parent / "app" / "services" / "brim_providers" / "sample_reports"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_brim_providers() -> List[str]:
    """
    Get all registered BRIM providers for parametrization.

    This ensures tests run for ALL registered providers dynamically.
    """
    BRIMProviderRegistry.auto_discover()
    providers = BRIMProviderRegistry.list_plugin_info()

    if not providers:
        pytest.skip("No BRIM providers registered")

    return [p.code for p in providers]


def get_sample_files_for_plugin(plugin_code: str) -> List[Path]:
    """
    Get sample files that a plugin can parse.

    Returns list of sample files the plugin claims to be able to parse.
    """
    if not SAMPLE_DIR.exists():
        return []

    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if not plugin:
        return []

    parseable_files = []
    for sample_file in SAMPLE_DIR.glob("*.csv"):
        if plugin.can_parse(sample_file):
            parseable_files.append(sample_file)

    return parseable_files


def get_all_sample_files() -> List[Path]:
    """Get all sample files in the sample_reports directory."""
    if not SAMPLE_DIR.exists():
        return []
    return [f for ext in ['csv', 'xlsx', 'xls', 'json'] for f in SAMPLE_DIR.glob(f"**/*.{ext}")]


# =============================================================================
# CATEGORY 1: PLUGIN DISCOVERY & REGISTRATION (run once, not parametrized)
# =============================================================================

class TestPluginDiscovery:
    """Tests for plugin auto-discovery and registration."""

    def test_registry_discovers_plugins(self):
        """PD-001: Verify auto-discovery finds at least 1 plugin."""
        plugins = BRIMProviderRegistry.list_plugin_info()
        assert len(plugins) >= 1, "No plugins discovered"
        print(f"✓ Discovered {len(plugins)} plugins")

    def test_all_plugins_have_required_properties(self):
        """PD-002: Verify all plugins have code, name, description."""
        plugins = BRIMProviderRegistry.list_plugin_info()

        for plugin_info in plugins:
            assert plugin_info.code, f"Plugin missing code"
            assert plugin_info.name, f"Plugin {plugin_info.code} missing name"
            assert plugin_info.description, f"Plugin {plugin_info.code} missing description"
            assert plugin_info.supported_extensions, f"Plugin {plugin_info.code} missing extensions"

        print(f"✓ All {len(plugins)} plugins have required properties")

    def test_plugin_codes_are_unique(self):
        """PD-003: Verify no duplicate plugin codes."""
        plugins = BRIMProviderRegistry.list_plugin_info()
        codes = [p.code for p in plugins]

        duplicates = [code for code in codes if codes.count(code) > 1]
        assert not duplicates, f"Duplicate plugin codes: {set(duplicates)}"
        print(f"✓ All {len(codes)} plugin codes are unique")

    def test_get_nonexistent_provider_returns_none(self):
        """PD-005: Returns None for unknown code."""
        instance = BRIMProviderRegistry.get_provider_instance("nonexistent_xyz_plugin")
        assert instance is None, "Expected None for nonexistent plugin"
        print("✓ Nonexistent provider returns None")

    def test_all_sample_files_have_compatible_plugin(self):
        """AD-003: Every sample file should be parseable by at least one plugin."""
        sample_files = get_all_sample_files()
        assert len(sample_files) > 0, "No sample files found"

        uncovered_files = []
        for sample_file in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
            if not detected:
                uncovered_files.append(sample_file.name)

        assert not uncovered_files, f"Files without compatible plugin: {uncovered_files}"
        print(f"✓ All {len(sample_files)} sample files have a compatible plugin")

    def test_all_plugins_used_at_least_once(self):
        """AD-003b: Every registered plugin should parse at least 1 sample file."""
        plugins = BRIMProviderRegistry.list_plugin_info()
        sample_files = get_all_sample_files()

        used_plugins: Set[str] = set()
        for sample_file in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
            if detected:
                used_plugins.add(detected)

        # Generic CSV is always a fallback, so we exclude it from "must be used" check
        registered = {p.code for p in plugins}
        unused = registered - used_plugins - {"broker_generic_csv"}

        # Plugins without samples should be flagged - we want full coverage
        assert not unused, f"Plugins without sample files (add samples!): {unused}"

        print(f"✓ All {len(used_plugins)} non-generic plugins have sample files")


# =============================================================================
# CATEGORY 2: PARAMETRIZED PLUGIN TESTS (run for each plugin)
# =============================================================================

@pytest.mark.parametrize("provider_code", get_all_brim_providers())
class TestPluginInterface:
    """Parametrized tests that run for EACH registered plugin."""

    def test_provider_instance_creation(self, provider_code: str):
        """PD-004: Verify instance creation works for plugin."""
        instance = BRIMProviderRegistry.get_provider_instance(provider_code)

        assert instance is not None, f"Failed to get instance for {provider_code}"
        assert isinstance(instance, BRIMProvider), f"Instance is not BRIMProvider"
        assert instance.provider_code == provider_code, "Code mismatch"
        print(f"✓ {provider_code}: Instance created successfully")

    def test_provider_has_valid_metadata(self, provider_code: str):
        """Verify provider metadata is valid."""
        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)

        assert plugin.provider_code, "Empty provider_code"
        assert plugin.provider_name, "Empty provider_name"
        assert plugin.description, "Empty description"
        assert plugin.supported_extensions, "No supported extensions"
        assert all(ext.startswith('.') for ext in plugin.supported_extensions), \
            "Extensions should start with '.'"

        print(f"✓ {provider_code}: Valid metadata")

    def test_provider_can_parse_at_least_one_sample(self, provider_code: str):
        """Verify plugin can parse at least one sample file (if not generic fallback)."""
        if provider_code == "broker_generic_csv":
            pytest.skip("Generic CSV is a fallback, always parseable")

        parseable = get_sample_files_for_plugin(provider_code)

        # Non-generic plugins should have sample files
        if not parseable:
            pytest.skip(f"{provider_code} has no sample files yet")

        print(f"✓ {provider_code}: Can parse {len(parseable)} sample file(s)")

    def test_parse_returns_correct_types(self, provider_code: str):
        """Verify parse() returns (List[TXCreateItem], List[str], Dict[int, BRIMExtractedAssetInfo])."""
        parseable = get_sample_files_for_plugin(provider_code)

        if not parseable:
            pytest.skip(f"{provider_code} has no parseable sample files")

        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)
        sample_file = parseable[0]

        result = plugin.parse(sample_file, broker_id=1)

        assert isinstance(result, tuple), "parse() should return tuple"
        assert len(result) == 3, "parse() should return 3 values"

        transactions, warnings, extracted_assets = result
        assert isinstance(transactions, list), "First return should be list"
        assert isinstance(warnings, list), "Second return should be list"
        assert isinstance(extracted_assets, dict), "Third return should be dict"

        if transactions:
            assert isinstance(transactions[0], TXCreateItem), \
                "Transactions should be TXCreateItem instances"

        print(f"✓ {provider_code}: parse() returns correct types")

    def test_parse_produces_transactions(self, provider_code: str):
        """Verify parse() produces at least one transaction."""
        parseable = get_sample_files_for_plugin(provider_code)

        if not parseable:
            pytest.skip(f"{provider_code} has no parseable sample files")

        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)
        sample_file = parseable[0]

        transactions, warnings, _ = plugin.parse(sample_file, broker_id=1)

        assert len(transactions) > 0, \
            f"No transactions parsed from {sample_file.name}"

        print(f"✓ {provider_code}: Parsed {len(transactions)} transactions from {sample_file.name}")

    def test_transactions_have_required_fields(self, provider_code: str):
        """Verify all transactions have required fields populated."""
        parseable = get_sample_files_for_plugin(provider_code)

        if not parseable:
            pytest.skip(f"{provider_code} has no parseable sample files")

        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)
        sample_file = parseable[0]

        transactions, _, _ = plugin.parse(sample_file, broker_id=1)

        for i, tx in enumerate(transactions):
            assert tx.broker_id == 1, f"TX {i}: broker_id not set"
            assert tx.type is not None, f"TX {i}: type is None"
            assert tx.date is not None, f"TX {i}: date is None"
            # quantity can be 0 for deposits
            # cash can be None for adjustments

        print(f"✓ {provider_code}: All {len(transactions)} transactions have required fields")

    def test_get_extracted_assets_from_parse(self, provider_code: str):
        """Verify parse() returns extracted_assets dict with correct structure."""
        parseable = get_sample_files_for_plugin(provider_code)

        if not parseable:
            pytest.skip(f"{provider_code} has no parseable sample files")

        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)
        sample_file = parseable[0]

        # Parse returns (transactions, warnings, extracted_assets)
        transactions, warnings, assets = plugin.parse(sample_file, broker_id=1)

        assert isinstance(assets, dict), "extracted_assets should be dict"

        # Each value should be BRIMExtractedAssetInfo
        from backend.app.schemas.brim import BRIMExtractedAssetInfo
        for fake_id, info in assets.items():
            assert isinstance(fake_id, int), "Fake ID should be int"
            assert isinstance(info, BRIMExtractedAssetInfo), \
                f"Asset info should be BRIMExtractedAssetInfo, got {type(info)}"

        # Verify consistency: every asset_id in transactions should be in extracted_assets
        # (except None for non-asset transactions like deposits)
        tx_asset_ids = {tx.asset_id for tx in transactions if tx.asset_id is not None}
        missing_from_assets = tx_asset_ids - set(assets.keys())
        assert not missing_from_assets, \
            f"Transaction asset_ids not in extracted_assets: {missing_from_assets}"

        print(f"✓ {provider_code}: parse() returns {len(assets)} extracted assets, all consistent with transactions")

    def test_all_parseable_samples_succeed(self, provider_code: str):
        """Verify plugin can parse ALL its compatible sample files without error."""
        # For generic CSV, only test files that are auto-detected as generic
        # (not files that have a specific plugin)
        if provider_code == "broker_generic_csv":
            sample_files = get_all_sample_files()
            parseable = []
            for f in sample_files:
                detected = BRIMProviderRegistry.auto_detect_plugin(f)
                if detected == "broker_generic_csv":
                    parseable.append(f)
        else:
            parseable = get_sample_files_for_plugin(provider_code)

        if not parseable:
            pytest.skip(f"{provider_code} has no parseable sample files")

        plugin = BRIMProviderRegistry.get_provider_instance(provider_code)

        for sample_file in parseable:
            try:
                transactions, warnings, _ = plugin.parse(sample_file, broker_id=1)
                assert len(transactions) > 0, f"No transactions from {sample_file.name}"
            except Exception as e:
                pytest.fail(f"Failed to parse {sample_file.name}: {e}")

        print(f"✓ {provider_code}: Successfully parsed all {len(parseable)} sample files")


# =============================================================================
# CATEGORY 3: AUTO-DETECTION TESTS
# =============================================================================

class TestAutoDetection:
    """Tests for plugin auto-detection functionality."""

    def test_auto_detect_returns_valid_plugin(self):
        """Verify auto_detect_plugin returns a valid plugin code."""
        sample_files = get_all_sample_files()
        assert len(sample_files) > 0, "No sample files to test"

        for sample_file in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
            assert detected is not None, f"No plugin detected for {sample_file.name}"

            # Verify detected plugin exists
            plugin = BRIMProviderRegistry.get_provider_instance(detected)
            assert plugin is not None, f"Detected plugin {detected} doesn't exist"

        print(f"✓ Auto-detection works for all {len(sample_files)} sample files")

    def test_detection_prefers_specific_over_generic(self):
        """Verify specific plugins are preferred over generic CSV."""
        sample_files = get_all_sample_files()

        specific_detections = 0
        generic_detections = 0

        for sample_file in sample_files:
            detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
            if detected == "broker_generic_csv":
                generic_detections += 1
            else:
                specific_detections += 1

        # Should have some specific detections if broker-specific samples exist
        print(f"  Specific: {specific_detections}, Generic: {generic_detections}")

        # At least directa, degiro, etc. should be detected specifically
        assert specific_detections > 0, "No broker-specific plugins detected"
        print(f"✓ Specific plugins preferred: {specific_detections} specific, {generic_detections} generic")

    def test_specific_broker_detection_via_plugin_pattern(self):
        """Verify plugins with test_file_pattern are correctly detected for matching files."""
        sample_files = get_all_sample_files()
        plugins = BRIMProviderRegistry.list_plugin_info()

        for plugin_info in plugins:
            plugin = BRIMProviderRegistry.get_provider_instance(plugin_info.code)
            pattern = plugin.test_file_pattern

            if pattern is None:
                # Generic plugin or no test pattern defined
                continue

            # Find sample files matching this pattern
            matching = [f for f in sample_files if pattern in f.name.lower()]

            if not matching:
                # No sample file for this plugin's pattern
                continue

            # Verify the plugin is detected for its matching files
            for sample_file in matching:
                detected = BRIMProviderRegistry.auto_detect_plugin(sample_file)
                assert detected == plugin_info.code, \
                    f"{sample_file.name} detected as {detected}, expected {plugin_info.code}"
                print(f"✓ {sample_file.name} → {detected}")


# =============================================================================
# CATEGORY 4: GENERIC CSV SPECIFIC TESTS
# =============================================================================

class TestGenericCSVPlugin:
    """Specific tests for the generic CSV fallback plugin."""

    # Required generic sample files for E2E testing
    REQUIRED_GENERIC_FILES = [
        "generic_simple.csv",
        "generic_dates.csv",
        "generic_types.csv",
        "generic_with_assets.csv",
    ]

    def test_required_generic_files_exist(self):
        """Verify all required generic sample files exist."""
        for filename in self.REQUIRED_GENERIC_FILES:
            filepath = SAMPLE_DIR / filename
            assert filepath.exists(), f"Required generic sample file missing: {filename}"

        print(f"✓ All {len(self.REQUIRED_GENERIC_FILES)} required generic files exist")

    def test_generic_can_parse_any_csv(self):
        """Generic plugin should be able to parse any CSV file."""
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None, "Generic CSV plugin not registered"

        sample_files = get_all_sample_files()

        for sample_file in sample_files:
            assert plugin.can_parse(sample_file), \
                f"Generic plugin should be able to parse {sample_file.name}"

        print(f"✓ Generic plugin can parse all {len(sample_files)} sample files")

    def test_generic_handles_multiple_date_formats(self):
        """Generic plugin should handle various date formats."""
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")

        # Find generic_dates.csv if it exists
        dates_file = SAMPLE_DIR / "generic_dates.csv"
        if not dates_file.exists():
            pytest.skip("generic_dates.csv not found")

        transactions, warnings, _ = plugin.parse(dates_file, broker_id=1)

        assert len(transactions) > 0, "Should parse some transactions"

        # All should have valid dates
        for tx in transactions:
            assert tx.date is not None, f"Transaction missing date"

        print(f"✓ Generic plugin parsed {len(transactions)} transactions with various date formats")

    def test_generic_has_lowest_priority(self):
        """Generic plugin should have lower priority than specific plugins."""
        generic = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")

        assert generic.detection_priority < 100, \
            f"Generic priority ({generic.detection_priority}) should be < 100"

        # Check that specific plugins have higher priority
        for info in BRIMProviderRegistry.list_plugin_info():
            if info.code != "broker_generic_csv":
                other = BRIMProviderRegistry.get_provider_instance(info.code)
                assert other.detection_priority >= generic.detection_priority, \
                    f"{info.code} priority should be >= generic"

        print(f"✓ Generic plugin has lowest priority ({generic.detection_priority})")

    def test_generic_has_no_test_file_pattern(self):
        """Generic plugin should return None for test_file_pattern."""
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")

        assert plugin.test_file_pattern is None, \
            "Generic plugin should have no test_file_pattern"

        print("✓ Generic plugin has no test_file_pattern")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

