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

from pathlib import Path
from typing import List, Set

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.brim import (
    BRIMExtractedAssetInfo,
    BRIMParseOutput,
    BRIMPluginInfo,
    BRIMPreviewColumn,
    is_fake_asset_id,
)
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS & HELPERS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"

_BASELINE_COLUMN_KEYS = {
    "date",
    "type",
    "quantity",
    "asset",
    "cash_amount",
    "cash_currency",
}


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

    def test_preview_columns_baseline(self, code: str, plugin: BRIMProvider):
        cols = plugin.preview_columns()
        assert isinstance(cols, list) and cols, f"{code} preview_columns must be a non-empty list"
        for col in cols:
            assert isinstance(col, BRIMPreviewColumn)
        keys = {c.key for c in cols}
        missing = _BASELINE_COLUMN_KEYS - keys
        assert not missing, f"{code} missing baseline columns: {missing}"

    def test_to_plugin_info_propagates_fields(self, code: str, plugin: BRIMProvider):
        info = plugin.to_plugin_info()
        assert isinstance(info, BRIMPluginInfo)
        assert info.code == code
        assert info.plugin_version == plugin.plugin_version
        assert info.preview_columns == plugin.preview_columns()
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

    def test_all_parseable_samples_succeed(self, code: str, plugin: BRIMProvider):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
