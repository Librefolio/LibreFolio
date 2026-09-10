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

import csv
import io
import re
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, List, Set
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from backend.app.config import PROJECT_ROOT
from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    BRIMExtractedAssetInfo,
    BRIMNotice,
    BRIMParseOutput,
    BRIMPluginInfo,
    is_fake_asset_id,
)
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers import broker_credit_agricole as ca
from backend.app.services.brim_providers._brim_io import MATURITY_NOTICE_KIND, model_bond_maturity, read_rows
from backend.app.services.brim_providers.broker_coinbase import CoinbaseBrokerProvider, _parse_coinbase_amount, _parse_coinbase_datetime
from backend.app.services.brim_providers.broker_credit_agricole import CreditAgricoleBrokerProvider
from backend.app.services.brim_providers.broker_degiro import DegiroBrokerProvider, _extract_quantity_from_description, _parse_degiro_date
from backend.app.services.brim_providers.broker_directa import DirectaBrokerProvider, _parse_directa_date, _parse_directa_number
from backend.app.services.brim_providers.broker_etoro import EtoroBrokerProvider, _parse_etoro_date, _parse_etoro_number
from backend.app.services.brim_providers.broker_fineco import FinecoBrokerProvider
from backend.app.services.brim_providers.broker_finpension import FinpensionBrokerProvider, _parse_finpension_date, _parse_finpension_number
from backend.app.services.brim_providers.broker_freetrade import FreetradeBrokerProvider, _parse_freetrade_datetime, _parse_freetrade_number
from backend.app.services.brim_providers.broker_generic_csv import parse_decimal
from backend.app.services.brim_providers.broker_ibkr import IBKRBrokerProvider, _parse_ibkr_date, _parse_ibkr_number
from backend.app.services.brim_providers.broker_intesa import IntesaSanpaoloBrokerProvider
from backend.app.services.brim_providers.broker_revolut import RevolutBrokerProvider, _parse_revolut_amount, _parse_revolut_datetime, _parse_revolut_quantity
from backend.app.services.brim_providers.broker_schwab import SchwabBrokerProvider, _parse_schwab_amount, _parse_schwab_date
from backend.app.services.brim_providers.broker_trading212 import Trading212BrokerProvider, _parse_trading212_datetime, _parse_trading212_number
from backend.app.services.portfolio_engine import ClassifiedTransaction, DailyStateBuilder
from backend.app.services.price_resolver import build_asset_price_series
from backend.app.services.provider_registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS & HELPERS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
DEGIRO_SAMPLE = SAMPLE_DIR / "degiro-export.csv"
DIRECTA_SAMPLE = SAMPLE_DIR / "directa-export.csv"
CA_SAMPLE = SAMPLE_DIR / "credit_agricole-export.csv"
CA_SAMPLE_XLSX = SAMPLE_DIR / "credit_agricole-export.xlsx"
CA_CONTI_SAMPLE = SAMPLE_DIR / "credit_agricole-conti.csv"
CA_CONTI_SAMPLE_XLSX = SAMPLE_DIR / "credit_agricole-conti.xlsx"
INTESA_PATRIMONIO_SAMPLE = SAMPLE_DIR / "intesa-patrimonio.csv"
INTESA_LISTA_SAMPLE = SAMPLE_DIR / "intesa-lista.csv"
ETORO_SAMPLE = SAMPLE_DIR / "etoro-export.csv"
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
    samples = _all_samples_for_plugin(plugin)
    if samples:
        return samples[0]
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


def _all_samples_for_plugin(plugin: BRIMProvider) -> List[Path]:
    """Return every sample this plugin owns via its ``test_file_patterns``.

    A plugin may declare several format variants (e.g. Revolut invest + crypto);
    the representative-sample tests loop over all of them so each variant is
    exercised, not just the first. Falls back to an empty list when the plugin
    declares no patterns (generic fallback).
    """
    patterns = [p.lower() for p in plugin.test_file_patterns]
    if not patterns:
        return []
    matches: list[Path] = []
    for candidate in sorted(SAMPLE_DIR.iterdir()):
        if not (candidate.is_file() and candidate.suffix.lower() == ".csv"):
            continue
        name = candidate.name.lower()
        if any(pat in name for pat in patterns):
            matches.append(candidate)
    return matches


def _representative_samples(plugin: BRIMProvider) -> List[Path]:
    """All samples to exercise for a plugin: every declared variant, else one fallback."""
    samples = _all_samples_for_plugin(plugin)
    if samples:
        return samples
    single = _first_sample_for_plugin(plugin)
    return [single] if single else []


def _json_safe(value: Any) -> Any:
    """Recursively normalize a parsed BRIM value into JSON-comparable primitives.

    ``Decimal`` -> ``str`` (exact, never a binary-rounded float), ``date`` -> ISO
    string, ``Enum`` -> its ``.value``, a pydantic model -> its (recursively
    normalized) field dict, dict/list/tuple -> recursed. Used to compare two
    ``BRIMParseOutput`` trees (e.g. a CSV read against an XLSX read of the same
    sample) for structural equality regardless of which concrete Python type a
    given source format happened to produce for a cell (native XLSX number vs.
    CSV string, etc.) — the comparison is on shape and value, not on type identity.
    """
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump())
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _normalize_ca_xlsx_evidence_row_numbers(value: Any, offset: int) -> Any:
    """Normalize only CA's documented XLSX source-evidence row offset.

    The XLSX securities export has nine presentation rows before the CSV header;
    the account layouts have no offset.  Every other field remains part of the
    comparison, including messages, contexts, reasons, ordering and fake IDs.
    """
    normalized = _json_safe(value)
    if isinstance(normalized, dict):
        return {key: ([row_number - offset for row_number in item] if key == "row_numbers" else _normalize_ca_xlsx_evidence_row_numbers(item, offset)) for key, item in normalized.items()}
    if isinstance(normalized, list):
        return [_normalize_ca_xlsx_evidence_row_numbers(item, offset) for item in normalized]
    return normalized


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
        samples = _representative_samples(plugin)
        if not samples:
            pytest.skip(f"No compatible sample report for {code}")
        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            assert isinstance(out, BRIMParseOutput), f"{code} [{sample.name}]"
            assert isinstance(out.transactions, list)
            assert isinstance(out.warnings, list)
            assert isinstance(out.extracted_assets, dict)

    def test_parse_produces_transactions(self, code: str, plugin: BRIMProvider):
        samples = _representative_samples(plugin)
        if not samples:
            pytest.skip(f"No compatible sample report for {code}")
        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            assert len(out.transactions) > 0, f"No transactions parsed from {sample.name}"
            assert all(isinstance(tx, TXCreateItem) for tx in out.transactions)

    def test_extracted_assets_consistent_with_transactions(self, code: str, plugin: BRIMProvider):
        samples = _representative_samples(plugin)
        if not samples:
            pytest.skip(f"No compatible sample report for {code}")
        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            for fake_id, info in out.extracted_assets.items():
                assert isinstance(fake_id, int)
                assert isinstance(info, BRIMExtractedAssetInfo)
            tx_asset_ids = {tx.asset_id for tx in out.transactions if tx.asset_id is not None}
            missing = tx_asset_ids - set(out.extracted_assets.keys())
            assert not missing, f"{code} [{sample.name}]: transaction asset_ids not in extracted_assets: {missing}"

    def test_parse_is_idempotent(self, code: str, plugin: BRIMProvider):
        """Same input → same output. Required for plugin_version-driven caching.

        Compares ``.model_dump(mode="json")`` of BRIMParseOutput to avoid
        false negatives from object identity.
        """
        samples = _representative_samples(plugin)
        if not samples:
            pytest.skip(f"No compatible sample report for {code}")
        for sample in samples:
            out1 = plugin.parse(sample, broker_id=1)
            out2 = plugin.parse(sample, broker_id=1)
            assert out1.model_dump(mode="json") == out2.model_dump(mode="json"), f"{code}: parse() is not idempotent on {sample.name}"

    def test_parse_produces_valid_fake_ids(self, code: str, plugin: BRIMProvider):
        """Every asset_id key in extracted_assets must be a recognized fake id."""
        samples = _representative_samples(plugin)
        if not samples:
            pytest.skip(f"No compatible sample report for {code}")
        for sample in samples:
            out = plugin.parse(sample, broker_id=1)
            for fake_id in out.extracted_assets.keys():
                assert is_fake_asset_id(fake_id), f"{code} [{sample.name}]: extracted_assets key {fake_id} is not a valid fake id"

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
            if sample_file.suffix.lower() != ".csv":
                # The generic plugin is a CSV catch-all and intentionally rejects
                # binary spreadsheet samples (see GenericCSVBrokerProvider.can_parse).
                continue
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
            (CreditAgricoleBrokerProvider(), "credit_agricole-export.csv"),
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
        ids=["coinbase", "credit-agricole", "degiro", "directa", "etoro", "finpension", "freetrade", "ibkr", "revolut", "schwab", "trading212"],
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

    def test_directa_number_helper_handles_dot_comma_and_native_cells(self):
        """Directa exports are inconsistent: some rows use dot decimals ("20.95"),
        others comma ("-16,95"); XLSX cells arrive as native ``float``/``int``.
        All variants must parse. Guards a regression where an Italian-style
        (thousands=".") parser turned "20.95" into 2095.
        """
        assert _parse_directa_number("20.95") == Decimal("20.95")
        assert _parse_directa_number("-16,95") == Decimal("-16.95")
        assert _parse_directa_number(20.95) == Decimal("20.95")
        assert _parse_directa_number(2) == Decimal("2")
        assert _parse_directa_number(None) is None

    def test_directa_csv_and_xlsx_parse_identically(self, tmp_path):
        """The XLSX reader must yield the same transactions as the CSV reader.
        The generated XLSX stores amounts/quantities as native numbers (dot
        decimals), so this also guards the dot-decimal regression on the native
        cell path.
        """
        openpyxl = pytest.importorskip("openpyxl")

        rows = read_rows(DIRECTA_SAMPLE)
        numeric_cols = {7, 8, 9}  # Quantità, Importo euro, Importo Divisa
        wb = openpyxl.Workbook()
        ws = wb.active
        header_seen = False
        for row in rows:
            if not header_seen:
                header_seen = any("data operazione" in str(c).lower() for c in row)
                ws.append(row)
                continue
            out_row: List[object] = []
            for idx, cell in enumerate(row):
                text = "" if cell is None else str(cell).strip()
                num = _parse_directa_number(text) if (idx in numeric_cols and text) else None
                out_row.append(float(num) if num is not None else cell)
            ws.append(out_row)
        xlsx_path = tmp_path / "directa-export.xlsx"
        wb.save(xlsx_path)

        csv_out = DirectaBrokerProvider().parse(DIRECTA_SAMPLE, broker_id=1)
        xlsx_out = DirectaBrokerProvider().parse(xlsx_path, broker_id=1)

        def isin_of(result, tx):
            if tx.asset_id is None:
                return None
            asset = result.extracted_assets.get(tx.asset_id)
            return asset.extracted_isin if asset else None

        assert len(xlsx_out.transactions) == len(csv_out.transactions)
        assert xlsx_out.warnings == csv_out.warnings
        for csv_tx, xlsx_tx in zip(csv_out.transactions, xlsx_out.transactions, strict=True):
            assert xlsx_tx.date == csv_tx.date
            assert xlsx_tx.type == csv_tx.type
            assert xlsx_tx.quantity == csv_tx.quantity
            assert (xlsx_tx.cash is None) == (csv_tx.cash is None)
            if csv_tx.cash is not None:
                assert xlsx_tx.cash.amount == csv_tx.cash.amount
                assert xlsx_tx.cash.code == csv_tx.cash.code
            assert isin_of(xlsx_out, xlsx_tx) == isin_of(csv_out, csv_tx)

    def test_credit_agricole_imports_succession_as_cashless_adjustment(self):
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        succession = [tx for tx in out.transactions if tx.description and "successione" in tx.description]
        assert succession, "sample must contain succession rows"
        # A succession is a cashless transfer-in from an untracked dossier: an ADJUSTMENT
        # that seeds the position and carries the per-unit book price via
        # cost_basis_override, with no cash amount and no DEPOSIT counter-entry (nothing
        # was spent here).
        assert all(tx.type == TransactionType.ADJUSTMENT for tx in succession)
        assert all(tx.cash is None for tx in succession)
        assert all(tx.cost_basis_override is not None for tx in succession)
        assert not any(tx.type == TransactionType.DEPOSIT and tx.description and "successione" in tx.description for tx in out.transactions)
        # Correct, intentional behaviour is announced as INFO (blue), not as a warning,
        # and carries the transferred rows as evidence so the user can check them.
        # The prose itself is only the Italian fallback — the frontend prefers the
        # localised `importWizard.brimNotice.<code>` keyed on `code` and interpolated
        # with `context` — so assert the contract the UI actually depends on, not the
        # wording, which is free to change per locale.
        notice = next(n for n in out.warnings if n.code == "ca_succession_transfer_in")
        assert notice.severity == "info"
        assert notice.context == {"row_count": len(succession)}
        assert "Rettifica" in notice.message
        assert notice.evidence and len(notice.evidence[0].rows) == len(succession)

    def test_credit_agricole_buy_has_deposit_before(self):
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)
        buy = next(tx for tx in out.transactions if tx.type == TransactionType.BUY and tx.description and tx.description.startswith("SICAV: SOTTOSCR"))

        idx = out.transactions.index(buy)
        deposit = out.transactions[idx - 1]
        assert deposit.type == TransactionType.DEPOSIT
        assert deposit.date == buy.date
        assert deposit.cash is not None and buy.cash is not None
        assert deposit.cash.amount == abs(buy.cash.amount)

    def test_credit_agricole_sell_has_withdrawal_after(self):
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)
        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and tx.description.startswith("FONDI: RIMBORSO"))

        idx = out.transactions.index(sell)
        withdrawal = out.transactions[idx + 1]
        assert withdrawal.type == TransactionType.WITHDRAWAL
        assert withdrawal.date == sell.date
        assert withdrawal.cash is not None and sell.cash is not None
        assert withdrawal.cash.amount == -abs(sell.cash.amount)

    def test_credit_agricole_all_cash_is_neutral(self):
        """The securities-only export is fully balanced: BUY/SELL, coupons and
        maturity premiums each get a cash counter-entry, so *total* broker cash
        (every leg, not just trades) nets to zero — no phantom liquidity."""
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        total_cash = sum((tx.cash.amount for tx in out.transactions if tx.cash is not None), Decimal("0"))
        assert total_cash == Decimal("0.00")

    def test_credit_agricole_coupon_has_balancing_withdrawal(self):
        """Each coupon (CEDOLA -> INTEREST) is offset by a same-day auto-cash
        WITHDRAWAL of the opposite amount, so the securities-only export does not
        accumulate unbalanced liquidity (regression for the coupon-cash fix)."""
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        coupon = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description and tx.description.startswith("CEDOLA"))
        assert coupon.cash is not None
        offset = next(tx for tx in out.transactions if tx.type == TransactionType.WITHDRAWAL and tx.date == coupon.date and tx.cash is not None and tx.cash.amount == -coupon.cash.amount and "auto_cash" in (tx.tags or []))
        assert offset is not None

    def test_credit_agricole_securities_ignores_recap_footer(self):
        """CA can append a recap/summary row at the very end of the XLSX export
        ("Riepilogo ..."). It must be recognised and dropped silently, never
        warned about nor turned into a phantom transaction."""
        base = CreditAgricoleBrokerProvider()._parse_securities(read_rows(CA_SAMPLE), broker_id=1)

        rows = read_rows(CA_SAMPLE)
        rows.append(["", "Riepilogo movimenti deposito titoli", "", "", "", "", "", "", "", ""])
        out = CreditAgricoleBrokerProvider()._parse_securities(rows, broker_id=1)

        assert not any("missing date/causale" in n.message for n in out.warnings)
        assert not any("Riepilogo" in n.message for n in out.warnings)
        assert len(out.transactions) == len(base.transactions)

    # ------------------------------------------------------------------
    # Account "Lista Movimenti Conto" layout (liquidity / fees / taxes / income)
    # ------------------------------------------------------------------

    def test_credit_agricole_account_can_parse_and_routes(self):
        prov = CreditAgricoleBrokerProvider()
        assert prov.can_parse(CA_CONTI_SAMPLE)
        # The account layout must auto-detect to Crédit Agricole, not another bank.
        assert BRIMProviderRegistry.auto_detect_plugin(CA_CONTI_SAMPLE) == "broker_credit_agricole"

    def test_credit_agricole_account_maps_types_by_causale(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        types = [tx.type for tx in out.transactions]
        assert types.count(TransactionType.WITHDRAWAL) == 5
        assert types.count(TransactionType.DEPOSIT) == 4
        # ``COMPRAVENDITA`` rows are real trades, not cash: two purchases (one at par,
        # one above par) plus one sale. The remaining SICAV subscription has no coupon
        # to recover its quantity from, so it stays cash and is blocked instead.
        assert types.count(TransactionType.BUY) == 2
        # One sale, plus the unidentifiable ``TITOLI SCADUTI O ESTRATTI`` row (no
        # same-day coupon), booked entirely as a SELL at par rather than a cash DEPOSIT.
        assert types.count(TransactionType.SELL) == 2
        assert types.count(TransactionType.INTEREST) == 4
        assert types.count(TransactionType.DIVIDEND) == 1
        # Two charge rows + the withholding split out of the grossed-up coupon.
        assert types.count(TransactionType.TAX) == 3
        assert types.count(TransactionType.FEE) == 3
        assert len(out.validation_issues) == 0

    def test_credit_agricole_account_tax_vs_fee_split(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        # Capital gain / imposta bollo -> TAX; management / coupon-detach / canone -> FEE.
        tax_descs = " | ".join(tx.description for tx in out.transactions if tx.type == TransactionType.TAX)
        assert "CAPITAL GAIN" in tax_descs and "Imposta bollo" in tax_descs
        fee_descs = " | ".join(tx.description for tx in out.transactions if tx.type == TransactionType.FEE)
        assert "SPESE STACCO CEDOLA" in fee_descs
        assert "SPESE DI GESTIONE" in fee_descs
        assert "CANONE MENSILE" in fee_descs
        # A charge always carries negative cash.
        assert all(tx.cash is not None and tx.cash.amount < 0 for tx in out.transactions if tx.type in {TransactionType.FEE, TransactionType.TAX})

    def test_credit_agricole_account_coupon_and_dividend_link_asset_by_isin(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        # A bond coupon (CEDOLA) that names its bond by ISIN is INTEREST linked to
        # that bond, so it shows under the asset in the FIFO lot detail.
        coupon = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description.startswith("CEDOLA:"))
        assert coupon.cash is not None and coupon.cash.amount > 0
        assert coupon.asset_id is not None and coupon.asset_id in out.extracted_assets
        assert out.extracted_assets[coupon.asset_id].extracted_isin == "IT0000000001"
        # A dividend that names a security (ISIN) is DIVIDEND, asset-linked.
        dividend = next(tx for tx in out.transactions if tx.type == TransactionType.DIVIDEND)
        assert dividend.asset_id is not None
        assert dividend.asset_id in out.extracted_assets
        assert out.extracted_assets[dividend.asset_id].extracted_isin == "IT0000000002"
        # A dividend WITHOUT an identifiable asset degrades to unallocated INTEREST.
        no_asset_div = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and "SENZA TITOLO" in tx.description)
        assert no_asset_div.asset_id is None
        # Bank credit interest carries no ISIN and stays unallocated INTEREST.
        bank_interest = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and "INTERESSI CREDITORI" in tx.description)
        assert bank_interest.asset_id is None

    def test_credit_agricole_account_deposits_withdrawals_by_sign(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        # Pension credit -> DEPOSIT (positive); utility debit -> WITHDRAWAL (negative).
        deposit = next(tx for tx in out.transactions if tx.type == TransactionType.DEPOSIT and "PENSIONE" in tx.description)
        assert deposit.cash is not None and deposit.cash.amount > 0
        withdrawal = next(tx for tx in out.transactions if tx.type == TransactionType.WITHDRAWAL and "UTILITY" in tx.description)
        assert withdrawal.cash is not None and withdrawal.cash.amount < 0

    def test_credit_agricole_account_identifiable_maturity_closes_wac_cost_basis(self):
        """Account-only maturity rows must not stay cash-only when same-day coupon identifies ISIN + nominal.

        This mirrors the real Nonna Anna 2025 case: the truncated securities export
        opened BTP 20-25, while the later account export had only
        ``TITOLI SCADUTI O ESTRATTI`` cash. The plugin must emit a SELL leg so the
        engine's ``book_asset_like`` drops instead of staying flat forever.
        """
        rows = read_rows(CA_CONTI_SAMPLE)
        rows.extend(
            [
                ["26/05/2025", "26/05/2025", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP 20-25 1.40FOICU IT0005410904 DOS:00496/05246854 NOMINALE: 95.000,00 TASSO: 3,62", "1.506,00", "EUR"],
                ["26/05/2025", "26/05/2025", "TITOLI SCADUTI O ESTRATTI", "RIMB.TIT. BTP 20-25 1.40FOICUM(0541090 ) DOS:0496/05246854 26/05/25", "95.665,00", "EUR"],
            ]
        )

        out = CreditAgricoleBrokerProvider()._parse_account_movements(rows, broker_id=1)
        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and "BTP 20-25" in tx.description)
        assert sell.asset_id is not None
        assert sell.quantity == Decimal("-95000.00")
        assert sell.cash is not None and sell.cash.amount == Decimal("95000.00")
        assert "account_maturity" in (sell.tags or [])
        assert out.extracted_assets[sell.asset_id].extracted_isin == "IT0005410904"
        assert not any(tx.type == TransactionType.DEPOSIT and tx.cash and tx.cash.amount == Decimal("95665.00") and tx.description and "BTP 20-25" in tx.description for tx in out.transactions)

        premium = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description and "premio/rivalutazione da conto" in tx.description)
        assert premium.asset_id == sell.asset_id
        assert premium.cash is not None and premium.cash.amount == Decimal("665.00")

        opening = MagicMock()
        opening.id = 999001
        opening.broker_id = 1
        opening.type = TransactionType.ADJUSTMENT
        opening.date = date(2025, 5, 25)
        opening.asset_id = sell.asset_id
        opening.quantity = Decimal("95000")
        opening.amount = Decimal("0")
        opening.currency = None
        opening.cost_basis_override = Decimal("1")
        opening.cost_basis_currency = "EUR"
        opening.related_transaction_id = None
        opening.asset_event_id = None

        parsed_txs = [tx for tx in out.transactions if tx.date == date(2025, 5, 26) and (tx.asset_id == sell.asset_id or (tx.description and "BTP 20-25" in tx.description))]

        def as_engine_tx(idx: int, item: TXCreateItem) -> MagicMock:
            tx = MagicMock()
            tx.id = 999100 + idx
            tx.broker_id = item.broker_id
            tx.type = item.type
            tx.date = item.date
            tx.asset_id = item.asset_id
            tx.quantity = Decimal(item.quantity or 0)
            tx.amount = item.cash.amount if item.cash else Decimal("0")
            tx.currency = item.cash.code if item.cash else None
            tx.cost_basis_override = item.cost_basis_override.amount if item.cost_basis_override else None
            tx.cost_basis_currency = item.cost_basis_override.code if item.cost_basis_override else None
            tx.related_transaction_id = None
            tx.asset_event_id = None
            return tx

        engine_txs = [opening] + [as_engine_tx(idx, item) for idx, item in enumerate(parsed_txs)]
        mark_series = {
            sell.asset_id: build_asset_price_series(
                price_rows=[],
                transactions=engine_txs,
                split_linked_tx_ids=set(),
                asset_currency="EUR",
                quote_base_quantity=1,
            )
        }
        states = (
            DailyStateBuilder(
                classified_txs=[ClassifiedTransaction(tx=tx, classification="normal", share=Decimal("1"), paired_tx=None) for tx in engine_txs],
                in_transit_intervals=[],
                external_cash_flows=[],
                price_map={},
                quote_base_map={},
                fx_rate_map={},
                asset_classifications={},
                asset_types={},
                asset_currencies={sell.asset_id: "EUR"},
                mark_series=mark_series,
                target_currency="EUR",
                date_from=date(2025, 5, 25),
                date_to=date(2025, 5, 27),
            )
            .build()
            .daily_states
        )
        assert states[0].book_asset_like == Decimal("95000")
        assert states[1].book_asset_like == Decimal("0")
        assert states[2].book_asset_like == Decimal("0")

    def test_credit_agricole_account_unidentifiable_maturity_books_full_sell(self):
        """A maturity row with no same-day coupon (no recoverable ISIN + NOMINALE) is
        booked entirely as a SELL — everything as sold, unknown nominal (quantity 0),
        no INTEREST split — never a plain cash DEPOSIT, plus a warning."""
        rows = read_rows(CA_CONTI_SAMPLE)
        rows.append(
            ["10/06/2025", "10/06/2025", "TITOLI SCADUTI O ESTRATTI", "RIMB.TIT. MYSTERY BOND 30(9999999 ) DOS:0496/05246854 10/06/25", "12.345,00", "EUR"],
        )
        out = CreditAgricoleBrokerProvider()._parse_account_movements(rows, broker_id=1)
        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and "MYSTERY BOND" in tx.description)
        assert sell.asset_id is not None
        assert sell.quantity == Decimal("-12345")
        assert sell.cash is not None and sell.cash.amount == Decimal("12345.00")
        assert "account_maturity" in (sell.tags or [])
        assert not any(tx.type == TransactionType.INTEREST and tx.description and "MYSTERY BOND" in tx.description for tx in out.transactions)
        assert not any(tx.type == TransactionType.DEPOSIT and tx.cash and tx.cash.amount == Decimal("12345.00") for tx in out.transactions)
        assert any("non collegabile" in n.message and "vendita" in n.message for n in out.warnings)

    def test_credit_agricole_account_maturity_flags_the_asset_as_expired(self):
        """A redemption seen in the *account* statement must raise the maturity advisory
        on its asset, exactly like one seen in the securities export.

        This is the only warning the user gets that the security is delisted and no price
        provider will ever quote it. It used to be emitted by ``_parse_securities`` only,
        so a bond whose redemption appears in the account statement — the common case,
        since the account file is the one that spans years — was created silently and
        then failed to price with no explanation.
        """
        out = CreditAgricoleBrokerProvider()._parse_account_movements(read_rows(CA_CONTI_SAMPLE), broker_id=1)
        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and "account_maturity" in (tx.tags or []))
        assert sell.asset_id is not None
        info = out.extracted_assets[sell.asset_id]
        kinds = [n.kind for n in info.notices]
        assert MATURITY_NOTICE_KIND in kinds, f"expected a maturity notice on {info.extracted_name!r}, got {kinds}"

    def test_credit_agricole_account_cash_refund_is_not_a_maturity(self):
        """``SCT:RIMBORSO`` on a bank transfer is a cash refund, not a redemption.

        The advisory keys off the word "rimborso", which the file also uses for tax and
        promo refunds. Those rows carry no asset, so they cannot mislabel an instrument —
        this test keeps that true if the row ever gains one.
        """
        out = CreditAgricoleBrokerProvider()._parse_account_movements(read_rows(CA_CONTI_SAMPLE), broker_id=1)
        flagged = {aid for aid, info in out.extracted_assets.items() if any(n.kind == MATURITY_NOTICE_KIND for n in info.notices)}
        for tx in out.transactions:
            if tx.description and "SCT:RIMBORSO" in tx.description:
                assert tx.asset_id not in flagged

    # ------------------------------------------------------------------
    # Account causale registry (4 tiers) — a causale can never pass unnoticed
    # ------------------------------------------------------------------

    def test_credit_agricole_registry_tiers_are_disjoint_and_complete(self):
        """Each registered causale belongs to exactly one tier.

        Guards the registry itself: a causale accidentally listed in two tiers would
        make classification depend on dispatch order, which is exactly the kind of
        silent ambiguity the registry exists to remove.
        """
        tiers = [ca._ACCT_INCOME_CAUSALI, ca._ACCT_MATURITY_CAUSALI, ca._ACCT_FEETAX_CAUSALI, ca._ACCT_CANONE_CAUSALI, ca._ACCT_UNRESOLVED_CAUSALI, ca._ACCT_DECLARED_CASH_CAUSALI]
        seen: Set[str] = set()
        for tier in tiers:
            assert not (seen & tier), f"causale listed in more than one tier: {seen & tier}"
            seen |= tier

    def test_credit_agricole_declared_cash_causali_raise_no_alarm(self):
        """Tier 3 is the whole point of the registry: real bank cash stays silent.

        A net that cries wolf gets ignored, so the invariant worth protecting is not
        only "the trade is flagged" but also "nothing else is". POS payments, utility
        bills, ATM withdrawals, salary credits and transfers must produce neither a
        todo nor a notice.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        declared_cash_slugs = {ca._slug_causale(c) for c in ca._ACCT_DECLARED_CASH_CAUSALI}
        cash_rows = [tx for tx in out.transactions if declared_cash_slugs & set(tx.tags or [])]
        assert cash_rows, "fixture must exercise the declared-cash tier"
        assert all(tx.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL) for tx in cash_rows)

        flagged = {todo.tx_index for todo in out.field_todos}
        # One transfer is deliberately promoted out of tier 3 — a fund redemption paid by
        # wire, which has its own test. Every *other* declared-cash row must stay silent.
        promoted = {t.tx_index for t in out.field_todos if (t.context or {}).get("reason") == "fund_redemption"}
        cash_idx = {out.transactions.index(tx) for tx in cash_rows} - promoted
        assert len(cash_idx) >= 4, "fixture must exercise several declared-cash rows"
        assert not (flagged & cash_idx)
        assert not any(n.code == "ca_unknown_causale" for n in out.warnings)

    def test_credit_agricole_fund_redemption_by_wire_is_flagged(self):
        """A fund disinvestment never reaches the account as a securities operation.

        The fund house wires the money over, so the row lands under the ordinary
        transfer causale and is indistinguishable, by causale alone, from a salary or a
        tax refund. Booked as a plain deposit the position stays open forever and the
        loss surfaces much later as an unexplained gap in the cost basis — the same
        failure mode as the 50k bug, arriving through a different door.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        idx = next(i for i, tx in enumerate(out.transactions) if "SAMPLE FUND SICAV" in (tx.description or ""))
        tx = out.transactions[idx]
        # Cash is right and must stay right: only the security is missing.
        assert tx.type == TransactionType.DEPOSIT
        assert tx.cash is not None and tx.cash.amount == Decimal("9984.47")
        assert tx.asset_id is None

        todo = next(t for t in out.field_todos if t.tx_index == idx)
        assert todo.field == "asset_id"
        assert todo.severity == "blocker"
        assert todo.context.get("reason") == "fund_redemption"
        # The fund is named, so the two AMUNDI-style funds of one statement stay distinct.
        assert "SAMPLE FUND SICAV" in todo.message
        # The quantity is genuinely unknowable here — a fund states the countervalue, not
        # the units, and this layout has no coupon to recover it from. Asking beats guessing.
        assert todo.evidence and "quote" in todo.evidence[0].comment.lower()

    def test_credit_agricole_ordinary_transfer_refund_stays_silent(self):
        """The guard that makes the redemption rule safe: the payer must be the subject.

        A refund from the tax office or an energy-cost rebate also says "RIMBORSO" on an
        incoming transfer. The keyword alone fires on three real rows out of four, so the
        rule additionally requires the ordering party to be named again inside the
        operation text — a fund redeems *itself*, a refund is about something else.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        idx = next(i for i, tx in enumerate(out.transactions) if "MITTENTE SAMPLE" in (tx.description or ""))
        assert out.transactions[idx].type == TransactionType.DEPOSIT
        assert not [t for t in out.field_todos if t.tx_index == idx]

    def test_credit_agricole_fund_redemption_detector_survives_column_wrapping(self):
        """The name is cut mid-word by the export, so the match cannot keep whitespace.

        The real statement prints ``AMUNDI PRIMO INVES TIMENTO`` because the column ends
        there — comparing token by token, or by equality, misses exactly the rows the
        rule exists for.
        """
        wrapped = "ORD:SAMPLE FUND SICAV DT.ORD:000000 DESCR.OPERAZIONESCT::RIMBORSI: : : :SU SAMPLE FUND SIC AV CL B<*>"
        assert ca._sct_fund_redemption_name(wrapped) == "SAMPLE FUND SICAV"
        # No redemption wording at all.
        assert ca._sct_fund_redemption_name("ORD:SAMPLE FUND SICAV DT.ORD:000000 DESCR.OPERAZIONE SCT:BONIFICO SU SAMPLE FUND SICAV") == ""
        # Redemption wording, but the payer is not the subject of the payment.
        assert ca._sct_fund_redemption_name("ORD:DIVISIONE SERVIZI DT.ORD:000000 DESCR.OPERAZIONE SCT:RIMBORSO IRPEF - 730 ANNO 2023") == ""
        # No ordering party to identify anything with.
        assert ca._sct_fund_redemption_name("BONIFICO SCT:RIMBORSI SU QUALCOSA") == ""

    def test_credit_agricole_account_trade_becomes_a_real_buy(self):
        """The 50k bug: a COMPRAVENDITA row used to become an anonymous withdrawal.

        The description names the direction and the sign confirms it, so the row is a
        purchase — booking it as cash lost the position entirely, and the loss only
        surfaced much later as an unexplained gap in the cost basis.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        trade = next(tx for tx in out.transactions if "TIT:BTP SAMPLE" in (tx.description or ""))
        assert trade.type == TransactionType.BUY
        assert trade.cash is not None and trade.cash.amount == Decimal("-40000.00")
        assert trade.asset_id is not None
        # Same fake asset as the coupon that named it: the purchase and its income must
        # land on one instrument, not two.
        coupon = next(tx for tx in out.transactions if "CEDOLA:BTP SAMPLE" in (tx.description or ""))
        assert trade.asset_id == coupon.asset_id
        assert not any(n.code == "ca_unknown_causale" for n in out.warnings)

    def test_credit_agricole_account_trade_emits_no_cash_counterpart(self):
        """⚠️ The most insidious risk of the two layouts: opposite cash rules.

        ``_parse_securities`` synthesises a DEPOSIT before a BUY because that export
        carries no cash at all. On the account statement **the row itself is the cash**,
        so a counterpart here would double every trade — and the doubling is invisible
        in the transaction list, showing up only as a wrong balance much later.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        assert not any("auto_cash" in (tx.tags or []) for tx in out.transactions)
        trade_dates = {tx.date for tx in out.transactions if "account_trade" in (tx.tags or [])}
        cash_legs = [tx for tx in out.transactions if tx.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL) and tx.date in trade_dates]
        assert cash_legs == []

    def test_credit_agricole_account_trade_recovers_quantity_from_coupon(self):
        """The quantity is missing from the trade row but present in the bond's coupons.

        The two are printed at *different* widths ("BTP SAMPLE" vs "BTP SAMPLE 1/12/2026"),
        so the match is a normalized prefix in both directions — equality would find nothing.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        at_par = next(tx for tx in out.transactions if "TIT:BTP SAMPLE" in (tx.description or ""))
        above_par = next(tx for tx in out.transactions if "ACQ. TIT:BTP OTHER" in (tx.description or ""))
        assert at_par.quantity == Decimal("40000.00")  # NOMINALE of IT0000000001
        assert above_par.quantity == Decimal("20000.00")  # NOMINALE of IT0000000003
        # Nothing was flagged for these: the quantity was read, not guessed.
        blocked = {t.tx_index for t in out.field_todos if t.severity == "blocker"}
        assert out.transactions.index(at_par) not in blocked
        assert out.transactions.index(above_par) not in blocked

    def test_credit_agricole_account_sell_declares_its_presumed_quantity(self):
        """⚠️ Fixture-only branch: the real export contains no sales.

        A coupon says how much of the bond was *held*, not how much was sold. For a full
        sale the two coincide; for a partial one they do not, and the file never says
        which — so the quantity ships as a declared presumption, never as a silent read.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        sale = next(tx for tx in out.transactions if "VEND. TIT:BTP OTHER" in (tx.description or ""))
        assert sale.type == TransactionType.SELL
        assert sale.quantity == Decimal("-20000.00")
        assert sale.cash is not None and sale.cash.amount > 0

        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_sell_quantity_presumed")
        assert todo.severity == "warning"  # usable as-is, but visible
        assert out.transactions[todo.tx_index] is sale

    def test_credit_agricole_account_trade_without_quantity_stays_blocked(self):
        """A fund subscription names its instrument but no coupon can supply a quantity.

        Funds do not pay a NOMINALE-bearing coupon, so the number is genuinely absent from
        the file. Booking a BUY would require inventing it; the row therefore keeps its
        (correct) cash amount and blocks until the user supplies the quantity.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        fund = next(tx for tx in out.transactions if "SOTTOSC SICAV" in (tx.description or ""))
        assert fund.type == TransactionType.WITHDRAWAL
        assert fund.cash is not None and fund.cash.amount == Decimal("-5000.00")

        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")
        assert todo.severity == "blocker"
        assert out.transactions[todo.tx_index] is fund
        assert todo.context.get("reason") == "no_quantity"
        # The instrument *is* readable — the message must say so, or the user goes
        # looking for a name the plugin already had.
        assert "SAMPLE GLOB EQ FUND" in todo.message
        # A recognised-but-unresolved causale is tier 2, never tier 4: reporting it as
        # an unknown causale would send the user looking for a registry gap that is not there.
        assert not any(n.code == "ca_unknown_causale" for n in out.warnings)

    def test_credit_agricole_account_trade_direction_conflict_is_never_guessed(self):
        """Word and sign disagree: a purchase that brings money in is not a purchase.

        Typing it either way opens (or closes) a position that then poisons every FIFO
        match downstream, so the row stays cash and is blocked instead.
        """
        header = read_rows(CA_CONTI_SAMPLE)[0]
        conflicting = ["21/05/2026", "21/05/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:00000/00000000", "15.000,00", "EUR"]
        out = CreditAgricoleBrokerProvider()._parse_account_movements([header, conflicting], broker_id=1)

        assert [tx.type for tx in out.transactions] == [TransactionType.DEPOSIT]
        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")
        assert todo.severity == "blocker"
        assert todo.context.get("reason") == "sign_mismatch"

    def test_credit_agricole_account_trade_ambiguous_name_is_never_guessed(self):
        """Two bonds share the trade's (truncated) name — a wrong nominal is worse than none.

        Picking either one would open a position on the wrong instrument, and nothing
        downstream can detect it: the amounts stay plausible.
        """
        header = read_rows(CA_CONTI_SAMPLE)[0]
        coupon_a = ["01/06/2026", "01/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 NOMINALE: 40.000,00", "218,75", "EUR"]
        coupon_b = ["01/06/2026", "01/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP SAMPLE 1/9/2030 IT0000000009 DOS:00000/00000000 NOMINALE: 10.000,00", "100,00", "EUR"]
        trade = ["21/05/2026", "21/05/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:00000/00000000", "'-15.000,00", "EUR"]
        out = CreditAgricoleBrokerProvider()._parse_account_movements([header, coupon_a, coupon_b, trade], broker_id=1)

        booked = next(tx for tx in out.transactions if "NOTA INF. ACQ." in (tx.description or ""))
        assert booked.type == TransactionType.WITHDRAWAL
        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")
        assert todo.severity == "blocker"
        assert todo.context.get("reason") == "ambiguous_name"
        # Both candidates must be named, or the user cannot resolve what we could not.
        assert "IT0000000001" in todo.evidence[0].comment and "IT0000000009" in todo.evidence[0].comment

    def test_credit_agricole_account_trade_ambiguous_nominal_is_never_guessed(self):
        """The same bond shows two different nominals: the position changed over time.

        Either value would be a guess about *which* trade this row is, so the quantity
        goes back to the user rather than being picked by arrival order.
        """
        header = read_rows(CA_CONTI_SAMPLE)[0]
        coupon_1 = ["01/06/2026", "01/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 NOMINALE: 40.000,00", "218,75", "EUR"]
        coupon_2 = ["01/12/2026", "01/12/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 NOMINALE: 25.000,00", "136,72", "EUR"]
        trade = ["21/05/2026", "21/05/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:00000/00000000", "'-15.000,00", "EUR"]
        out = CreditAgricoleBrokerProvider()._parse_account_movements([header, coupon_1, coupon_2, trade], broker_id=1)

        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")
        assert todo.severity == "blocker"
        assert todo.context.get("reason") == "ambiguous_nominal"

    def test_credit_agricole_account_trade_at_par_is_flagged_too(self):
        """Even a purchase whose total matches the nominal to the cent gets the flag.

        ⚠️ This inverts an earlier decision, on purpose. Firing only on a measured gap
        made the warning depend on a coupon happening to sit in the same export: import
        the very same purchase alone, in a window with no coupon, and it passed silently.
        The layout never separates price from charges, so the honest trigger is "this is
        a trade", not "I caught a contradiction". The at-par wording says as much, and
        the noise stays bounded because the file books few trades (3 on 507 real rows).
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        bundled = [t for t in out.field_todos if t.reason_code == "ca_account_trade_bundled_amount"]
        at_par = next(t for t in bundled if t.context["row"] == 16)  # the 40.000 = 40.000 purchase
        assert Decimal(at_par.context["delta"]) == 0
        assert "all'emissione" in at_par.evidence[0].comment
        # Only trades carry it: a coupon or a fee row has nothing to split.
        assert {t.context["row"] for t in bundled} == {16, 18, 19}

    def test_credit_agricole_account_trade_suggestions_read_the_rest_of_the_file(self):
        """The panel's hints are read off the export, never inferred from market data.

        The one that matters is the double-counting guard: when the file already books a
        charge as a row of its own, extracting it again from the trade total would count
        it twice — a wrong import, not just a clumsy one.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        fund = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")
        # A blocked trade is still a trade: it gets the same split affordance once the
        # user has supplied type, asset and quantity.
        assert fund.context["split_hint"] == "trade_charges"
        hints = fund.context["split_suggestions"]
        assert any("conti due volte" in h for h in hints)  # charge row 10 sits near it
        assert any("fondo" in h for h in hints)  # no accrued interest on a fund
        assert all("rateo cedolare che hai rimborsato" not in h for h in hints)

        # The bond purchase has no charge row nearby, so the hint says the opposite.
        bond = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_bundled_amount" and t.context["row"] == 18)
        assert any("non registra nessuna riga di commissioni" in h for h in bond.context["split_suggestions"])

    def test_credit_agricole_account_trade_above_par_declares_the_gap(self):
        """Cash ≠ nominal means the total also packs accrued interest and/or commissions.

        The plugin measures the gap and shows both rows it compared — it does **not**
        compute the accrued interest: that was tried on the real data and does not
        reconcile (one residue comes out negative), and an invented split is worse than a
        declared gap, because the first is a silent error and the second a known one.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        gap = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_bundled_amount" and t.context["row"] == 18)

        assert gap.severity == "warning"  # a heuristic never blocks
        # It rides on the purchase itself, so the correction step can offer the split there.
        assert out.transactions[gap.tx_index].type == "BUY"
        assert gap.field == "cash"
        assert gap.context["nominale"] == "20000.00"
        assert Decimal(gap.context["delta"]) == Decimal("412.33")
        # Two tables: the purchase, and the coupon that supplied the number it was compared to.
        assert len(gap.evidence) == 2
        assert "ACQ. TIT:BTP OTHER" in gap.evidence[0].rows[0][2]
        assert "CEDOLA:BTP OTHER" in gap.evidence[1].rows[0][2]
        assert gap.evidence[1].row_numbers == [17]
        # Not also a notice: the same finding shown twice teaches the user to skim past it,
        # and only the todo can be acted upon.
        assert all(n.code != "ca_account_trade_bundled_amount" for n in out.warnings)

    def test_credit_agricole_account_coupon_is_grossed_up_with_its_withholding(self):
        """The bank credits a coupon net, but the description spells out the tax it suffered.

        Importing the net amount silently loses a fiscally relevant number that is *right
        there in the file*. Gross income + a separate TAX leg sum back to the same cash, so
        the balance still reconciles against the bank's Saldo Finale.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        coupon = next(tx for tx in out.transactions if (tx.description or "").startswith("CEDOLA:BTP SAMPLE"))
        tax = next(tx for tx in out.transactions if "withholding_tax" in (tx.tags or []))

        assert coupon.cash is not None and coupon.cash.amount == Decimal("250.00")  # 218,75 net + 31,25
        assert tax.type == TransactionType.TAX
        assert tax.cash is not None and tax.cash.amount == Decimal("-31.25")
        assert tax.date == coupon.date
        assert tax.asset_id == coupon.asset_id  # the tax belongs to the bond that paid it
        # Net effect on cash is unchanged — this is what keeps the balance reconcilable.
        assert coupon.cash.amount + tax.cash.amount == Decimal("218.75")

    def test_credit_agricole_account_income_clawback_is_never_grossed_up(self):
        """A negative "CEDOLA" is a clawback, classified as cash — grossing it up would
        invent a tax refund the bank never paid."""
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        clawback = next(tx for tx in out.transactions if "STORNO CEDOLA ERRATA" in (tx.description or ""))
        assert clawback.type == TransactionType.WITHDRAWAL
        assert clawback.cash is not None and clawback.cash.amount == Decimal("-50.00")

    def test_credit_agricole_account_todo_carries_the_source_row(self):
        """The todo ships the originating row so the message can be checked, not trusted.

        The plugin attaches it at the moment it gives up — the only moment the row is
        still in hand. Re-reading the file preview later would cost a second fetch and
        could misalign row indexes if that preview truncates or paginates.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        todo = next(t for t in out.field_todos if t.reason_code == "ca_account_trade_unresolved")

        evidence = todo.evidence[0]
        assert evidence.headers[:4] == ["Data Op.", "Causale", "Descrizione", "Importo"]
        assert len(evidence.rows) == 1 and len(evidence.rows[0]) == len(evidence.headers)
        assert "SOTTOSC SICAV" in evidence.rows[0][2]
        assert evidence.row_numbers == [20]  # 1-based line in the source file
        assert evidence.comment and "L'importo è giusto" in evidence.comment

    def test_credit_agricole_charge_never_names_an_asset_after_itself(self):
        """A charge line describes the charge, never the security it is charged on.

        "SPESE STACCO CEDOLA DEL 21/05/2026 DOSSIER: 00496/05246854 TIT: IT000..." would
        become an asset called after its own fee wording, which then shows up in the
        user's asset picker as a nonsense instrument. The ISIN is the only honest name a
        charge can supply, and a real one must be able to replace it — rows arrive in file
        order, so the charge can be read before the coupon that names the bond.
        """
        rows = read_rows(CA_CONTI_SAMPLE)
        header = rows[0]
        charge = ["21/05/2026", "21/05/2026", "COMMISS./SPESE SU OPERAZ. TITOLI", "SPESE STACCO CEDOLA DEL 21/05/2026 DOSSIER: 00496/05246854 TIT: IT0009999999", "'-1,50", "EUR"]
        coupon = ["01/06/2026", "01/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP TF 3,35% MZ35 IT0009999999 DOS:00496/05246854", "12,00", "EUR"]

        # Charge first: the placeholder must survive only until the coupon names the bond.
        out = CreditAgricoleBrokerProvider()._parse_account_movements([header, charge, coupon], broker_id=1)
        fee = next(tx for tx in out.transactions if "SPESE STACCO" in (tx.description or ""))

        assert fee.asset_id is not None
        assert out.extracted_assets[fee.asset_id].extracted_name == "BTP TF 3,35% MZ35"
        assert out.extracted_assets[fee.asset_id].extracted_isin == "IT0009999999"

        # Charge alone: the ISIN stands in, never the fee's own wording.
        alone = CreditAgricoleBrokerProvider()._parse_account_movements([header, charge], broker_id=1)
        lone_fee = alone.transactions[0]
        assert alone.extracted_assets[lone_fee.asset_id].extracted_name == "IT0009999999"

    def test_credit_agricole_prefers_the_untruncated_security_name(self):
        """Crédit Agricole prints the same name at two different widths.

        The coupon line cuts it at 19 characters ("BTP 05/26 0.55FOICU") while the
        charge line prints it in full ("BTP 05/26 0.55FOICUM"). Importing the short
        form creates a second asset that will never match the one already held, so
        the longer form has to win whichever row is read first.
        """
        rows = read_rows(CA_CONTI_SAMPLE)
        header = rows[0]
        coupon = ["21/11/2024", "21/11/2024", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP 05/26 0.55FOICU IT0005332827 DOS:00496/05246854", "12,00", "EUR"]
        charge = ["21/11/2024", "21/11/2024", "COMMISS./SPESE SU OPERAZ. TITOLI", "SPESE STACCO CEDOLA DEL 21/11/2024 DOSSIER: 00496/05246854 TIT: IT0005332827 BTP 05/26 0.55FOICUM MOV:252419599", "'-1,50", "EUR"]

        for ordered in ([header, coupon, charge], [header, charge, coupon]):
            out = CreditAgricoleBrokerProvider()._parse_account_movements(ordered, broker_id=1)
            names = {info.extracted_name for info in out.extracted_assets.values()}
            assert names == {"BTP 05/26 0.55FOICUM"}, names

    def test_credit_agricole_securities_charge_links_to_the_isin_it_names(self):
        """A fee that names its security belongs to that security, not to the account.

        "SPESE STACCO CEDOLA ... TIT: IT000..." is charged for one bond. Booked
        unallocated it silently understates that bond's cost basis, and the gap only
        surfaces much later as a return that does not match the statement.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        fee = next(t for t in out.transactions if "SPESE STACCO CEDOLA" in (t.description or ""))
        coupon = next(t for t in out.transactions if "CEDOLA:BTP SAMPLE" in (t.description or ""))

        assert fee.asset_id is not None
        assert fee.asset_id == coupon.asset_id  # same bond as the coupon it was charged on

    def test_credit_agricole_unallocated_securities_charge_is_flagged_as_warning(self):
        """A securities charge with no security named is anomalous, but not a blocker.

        The file may genuinely never say which instrument it belonged to, and the expense
        is real either way — so it is surfaced for review and stays approvable as-is.
        Account charges (canone, bollo) are correctly unallocated and must NOT be flagged,
        or the review list drowns in noise and gets ignored.
        """
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        todos = [t for t in out.field_todos if t.reason_code == "ca_account_charge_unallocated"]

        assert len(todos) == 1
        assert todos[0].severity == "warning" and todos[0].field == "asset_id"
        flagged = out.transactions[todos[0].tx_index]
        assert "ADDEBITO CAPITAL GAIN" in (flagged.description or "")
        assert flagged.asset_id is None

        # Account-level charges stay silent: they belong to no instrument by nature.
        account_charges = [t for t in out.transactions if "Imposta bollo" in (t.description or "") or "CANONE MENSILE" in (t.description or "")]
        assert account_charges and not any(out.transactions[t.tx_index] in account_charges for t in todos)

    def test_credit_agricole_account_unknown_causale_is_declared_as_info(self):
        """Tier 4: an unregistered causale is still booked as cash, but never in silence.

        COMPRAVENDITA hid in the fallback for exactly this reason, so a causale the
        registry has never seen must announce itself — as INFO, because the cash
        movement itself is correct.
        """
        rows = read_rows(CA_CONTI_SAMPLE)
        rows.append(["12/07/2026", "12/07/2026", "OPERAZIONE MAI VISTA", "QUALCOSA DI NUOVO", "'-250,00", "EUR"])
        out = CreditAgricoleBrokerProvider()._parse_account_movements(rows, broker_id=1)

        booked = next(tx for tx in out.transactions if "QUALCOSA DI NUOVO" in (tx.description or ""))
        assert booked.type == TransactionType.WITHDRAWAL
        assert booked.cash is not None and booked.cash.amount == Decimal("-250.00")

        notice = next(n for n in out.warnings if n.code == "ca_unknown_causale")
        assert notice.severity == "info"
        assert notice.context is not None and notice.context["causali"] == ["OPERAZIONE MAI VISTA"]
        assert notice.evidence[0].row_numbers == [len(rows)]  # the appended row, 1-based
        # An unknown causale is a disclosure, not a blocker: nothing to fix, only to check.
        assert not any(t.context and t.context.get("causale") == "OPERAZIONE MAI VISTA" for t in out.field_todos)

    def test_brim_notice_coerces_legacy_string_warnings(self):
        """Every plugin still appends plain strings; the schema must keep accepting them.

        This is the test that protects the providers this work never touched: without
        the coercion, widening ``warnings`` to a structured type would have required
        editing every ``warnings.append("...")`` call in the codebase at once.
        """
        out = BRIMParseOutput(warnings=["riga saltata"])
        assert out.warnings[0].severity == "warning"
        assert out.warnings[0].message == "riga saltata"
        assert out.warnings[0].evidence == []

        untouched = FinecoBrokerProvider().parse(PROJECT_ROOT / "backend/app/services/brim_providers/sample_reports/fineco-export.csv", broker_id=1)
        assert all(isinstance(n, BRIMNotice) for n in untouched.warnings)

    def test_credit_agricole_account_carries_causale_tag_and_currency(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        for tx in out.transactions:
            tags = tx.tags or []
            assert "credit_agricole" in tags
            # The causale slug is preserved as the 3rd tag, for traceability.
            assert len(tags) >= 3
            assert tx.cash is not None and tx.cash.code == "EUR"

    def test_credit_agricole_account_fee_refund_and_income_clawback_edges(self):
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        # A positive amount on a fee causale is a refund -> DEPOSIT.
        refund = next(tx for tx in out.transactions if "RIMBORSO COMMISSIONI" in tx.description)
        assert refund.type == TransactionType.DEPOSIT and refund.cash.amount > 0
        # A negative amount on an income causale is a clawback -> WITHDRAWAL.
        clawback = next(tx for tx in out.transactions if "STORNO CEDOLA" in tx.description)
        assert clawback.type == TransactionType.WITHDRAWAL and clawback.cash.amount < 0

    def test_credit_agricole_account_strips_apostrophe_amount_guard(self):
        """Negative amounts in the CSV carry a leading ``'`` Excel text-guard
        (``'-61,20``); the parser must strip it and keep the sign."""
        out = CreditAgricoleBrokerProvider().parse(CA_CONTI_SAMPLE, broker_id=1)
        utility = next(tx for tx in out.transactions if "UTILITY" in tx.description)
        assert utility.cash is not None and utility.cash.amount == Decimal("-61.20")

    def test_credit_agricole_account_ignores_recap_footer(self):
        """The XLSX account export closes with numeric recap totals
        ("Totale Entrate/Uscite/Movimenti €"). They must be recognised and
        dropped: no noisy warning, and never leaked as a huge phantom deposit."""
        base = CreditAgricoleBrokerProvider()._parse_account_movements(read_rows(CA_CONTI_SAMPLE), broker_id=1)

        rows = read_rows(CA_CONTI_SAMPLE)
        rows.append(["", "", "", "Totale Entrate €", "214.739,70", ""])
        rows.append(["", "", "", "Totale Uscite €", "-164.652,53", ""])
        rows.append(["", "", "", "Totale Movimenti €", "50.087,17", ""])
        out = CreditAgricoleBrokerProvider()._parse_account_movements(rows, broker_id=1)

        assert not any("missing date/causale" in n.message for n in out.warnings)
        assert not any("Totale" in n.message for n in out.warnings)
        assert len(out.transactions) == len(base.transactions)
        assert all(tx.cash is None or abs(tx.cash.amount) != Decimal("214739.70") for tx in out.transactions)

    def test_credit_agricole_preserves_faithful_succession_multi_rows(self):
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        btp_2037 = [tx for tx in out.transactions if tx.description and "successione" in tx.description and "BTP FUT 27-04-37 CUM" in tx.description]
        # Each leg is preserved faithfully as its own ADJUSTMENT, keeping its distinct
        # per-unit price via cost_basis_override (a bond is quoted per 100 -> price / 100).
        assert [(tx.quantity, tx.cost_basis_override.amount if tx.cost_basis_override else None) for tx in btp_2037] == [
            (Decimal("7000"), Decimal("0.7261")),
            (Decimal("7000"), Decimal("1")),
            (Decimal("6000"), Decimal("1")),
        ]

    def test_credit_agricole_matured_bond_closes_position_at_par(self):
        """A ``TITOLI SCADUTI`` bond redemption must close the *held* nominal at par
        (100) and book the amount credited above par as a separate INTEREST leg. The
        held nominal comes from the succession legs (3×10000 = 30000 for BTP 05/26,
        32000+32000+31000 = 95000 for BTP 20-25), never from Ctv/Prezzo (which would
        give the wrong 29985 / 94906)."""
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        # BTP 05/26: held 30000, ctv 30105 -> SELL -30000 @par + INTEREST 105.
        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and tx.description.startswith("TITOLI SCADUTI: BTP 05/26"))
        assert sell.quantity == Decimal("-30000.000")
        assert sell.cash is not None and sell.cash.amount == Decimal("30000.00")

        premium = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description and "premio/rivalutazione" in tx.description and "BTP 05/26" in tx.description)
        assert premium.cash is not None and premium.cash.amount == Decimal("105.00")
        assert premium.asset_id == sell.asset_id
        assert "maturity_premium" in (premium.tags or [])

        # BTP 20-25: held 95000, ctv 95665 -> SELL -95000 @par + INTEREST 665.
        sell2 = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and tx.description.startswith("TITOLI SCADUTI: BTP 20-25"))
        assert sell2.quantity == Decimal("-95000.000")
        assert sell2.cash is not None and sell2.cash.amount == Decimal("95000.00")
        premium2 = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description and "premio/rivalutazione" in tx.description and "BTP 20-25" in tx.description)
        assert premium2.cash is not None and premium2.cash.amount == Decimal("665.00")

    def test_credit_agricole_matured_bond_position_leaves_no_verify_flag(self):
        """When the held nominal is known (position built from succession legs), the
        redemption must NOT raise a ``derived_quantity`` field-todo: the SELL closes
        an exact position, so there is nothing for the user to verify."""
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        derived = [ft for ft in out.field_todos if ft.reason_code == "derived_quantity"]
        assert derived == [], "position-backed maturities must not need a verify flag"

    def test_credit_agricole_matured_bond_net_position_is_zero(self):
        """End-to-end: after import the net quantity of each matured bond must be 0
        (succession transfers in via ADJUSTMENT, par redemption out via SELL)."""
        out = CreditAgricoleBrokerProvider().parse(CA_SAMPLE, broker_id=1)

        for name in ("BTP 05/26 0.55FOICUM", "BTP 20-25 1.40FOICUM"):
            net = sum((tx.quantity for tx in out.transactions if tx.description and name in tx.description and tx.type in {TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT}), Decimal("0"))
            assert net == Decimal("0"), f"{name} should net to zero, got {net}"

    def test_model_bond_maturity_prefers_position_over_derivation(self):
        """Unit test for the shared helper: with a known position the nominal is the
        held quantity (source ``position``, no verify needed); without one it falls
        back to a derivation from ``ctv/price`` (source ``derived``)."""
        # Position known: exact close at par, surplus = ctv - nominal.
        m = model_bond_maturity(ctv=Decimal("30105.00"), price=Decimal("100.40"), held_qty=Decimal("30000"))
        assert m.source == "position"
        assert m.nominal == Decimal("30000.000")
        assert m.principal_cash == Decimal("30000.00")
        assert m.surplus_cash == Decimal("105.00")

        # Orphan (no position): the nominal is derived from ctv/price and flagged.
        d = model_bond_maturity(ctv=Decimal("30105.00"), price=Decimal("100.40"), held_qty=None)
        assert d.source == "derived"

    def test_model_bond_maturity_derives_nominal_from_ctv_and_price(self):
        """Partial-download case: no position in the file, so the nominal is derived
        from ``ctv/price`` (best effort) and the surplus over par is booked as income.
        ``source`` stays ``derived`` so the caller flags the row for verification. The
        value is imprecise (29985 vs a true 30000) — accepted per the documented
        'redeemed at par 100' assumption; the flag lets the user correct it."""
        d = model_bond_maturity(ctv=Decimal("30105.00"), price=Decimal("100.40"), held_qty=None)
        assert d.source == "derived"
        assert d.nominal == Decimal("29985.060")
        assert d.principal_cash == Decimal("29985.06")
        assert d.surplus_cash == Decimal("119.94")

    def test_credit_agricole_matured_bond_without_position_derives_and_flags(self, tmp_path):
        """A partial CA export that contains a ``TITOLI SCADUTI`` row but *not* the
        succession/buy legs (e.g. a 'last 3 months' download) cannot see the position.
        The plugin must still model the redemption — deriving the nominal from
        Ctv/Prezzo and booking the premium as INTEREST — and it must raise a
        ``derived_quantity`` warning so the user verifies the nominal."""
        header = "Data operazione;Nome;Divisa;Causale;Prezzo;Divisa;Cambio;Quantità;Controvalore in Euro;Data valuta"
        row = "21/05/2026;BTP 05/26 0.55FOICUM;EUR;TITOLI SCADUTI;100,40;000;1;0;30.105,00;21/05/2026"
        csv_path = tmp_path / "credit_agricole-partial.csv"
        csv_path.write_text("\n".join([header, row]) + "\n", encoding="utf-8")

        out = CreditAgricoleBrokerProvider().parse(csv_path, broker_id=1)

        sell = next(tx for tx in out.transactions if tx.type == TransactionType.SELL)
        assert sell.quantity == Decimal("-29985.060")
        assert sell.cash is not None and sell.cash.amount == Decimal("29985.06")
        premium = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST)
        assert premium.cash is not None and premium.cash.amount == Decimal("119.94")

        derived = [ft for ft in out.field_todos if ft.reason_code == "derived_quantity"]
        assert len(derived) == 1, "orphan redemption must flag the derived nominal for verification"

    def test_model_bond_maturity_below_par_has_no_negative_surplus(self):
        """A redemption priced below par yields no surplus (no invented negative
        income); the whole amount stays principal."""
        m = model_bond_maturity(ctv=Decimal("9900.00"), price=Decimal("99.00"), held_qty=Decimal("10000"))
        assert m.principal_cash == Decimal("9900.00")
        assert m.surplus_cash == Decimal("0")

    def test_fineco_bond_redeemed_above_par_splits_interest(self, tmp_path):
        """Fineco ``Rimborso`` of a bond priced above par must close the nominal at
        par (SELL) and book the surplus as INTEREST. A bond at par and a stock
        redemption are left as a single SELL (pass-through)."""
        header = "Operazione,Data valuta,Descrizione,Titolo,Isin,Segno,Quantita,Divisa,Prezzo,Cambio,Controvalore,C1,C2,C3,C4"
        rows = [
            "01/09/2024,03/09/2024,Rimborso,BTP ITALIA FOI NV28,IT0005000001, ,10000,EUR,100.40000,1.00000,10040.00,,,,",
            "01/09/2024,03/09/2024,Rimborso,BTP VALORE SC MZ30,IT0005583478, ,2000,EUR,100.00000,1.00000,2000.00,,,,",
            "13/10/2024,13/10/2024,Rimborso,APPLE INC,US0378331005, ,5,USD,95.00000,1.05380,450.81,,,,",
        ]
        csv_path = tmp_path / "fineco-redemption.csv"
        csv_path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")

        out = FinecoBrokerProvider().parse(csv_path, broker_id=1)

        # Above-par bond -> par SELL + INTEREST surplus.
        above = next(tx for tx in out.transactions if tx.type == TransactionType.SELL and tx.description and "BTP ITALIA FOI NV28" in tx.description)
        assert above.quantity == Decimal("-10000")
        assert above.cash is not None and above.cash.amount == Decimal("10000.00")
        premium = next(tx for tx in out.transactions if tx.type == TransactionType.INTEREST and tx.description and "BTP ITALIA FOI NV28" in tx.description)
        assert premium.cash is not None and premium.cash.amount == Decimal("40.00")
        assert "maturity_premium" in (premium.tags or [])
        assert premium.asset_id == above.asset_id

        # At-par bond -> single SELL, no INTEREST leg.
        at_par = [tx for tx in out.transactions if tx.description and "BTP VALORE SC MZ30" in tx.description]
        assert [tx.type for tx in at_par] == [TransactionType.SELL]
        assert at_par[0].cash is not None and at_par[0].cash.amount == Decimal("2000.00")

        # Stock redemption (not a bond) -> single SELL, no INTEREST leg.
        stock = [tx for tx in out.transactions if tx.description and "APPLE INC" in tx.description]
        assert [tx.type for tx in stock] == [TransactionType.SELL]

    def test_intesa_patrimonio_seed_cost_basis_is_per_unit(self):
        """Regression: the patrimonio snapshot must store ``cost_basis_override`` as a
        PER-UNIT weighted-average cost (the portfolio engine and lot analysis multiply
        it by quantity). The bank export reports a TOTAL ``Controvalore di carico
        fiscale €``, so the plugin has to divide it by quantity — otherwise the cost
        basis explodes to qty×total (the ~3.95 billion € regression seen in production).
        """
        out = IntesaSanpaoloBrokerProvider().parse(INTESA_PATRIMONIO_SAMPLE, broker_id=9)

        seeds = [tx for tx in out.transactions if tx.type == TransactionType.ADJUSTMENT and tx.cost_basis_override is not None]
        assert len(seeds) == 7, "snapshot has 4 funds + 3 govt bonds"

        # Per-unit cost basis must reconstruct the TOTAL controvalore, never qty×total.
        total_cost = sum((tx.cost_basis_override.amount * tx.quantity for tx in seeds), Decimal("0"))
        assert abs(total_cost - Decimal("135688.54")) < Decimal("0.01")

        by_isin = {out.extracted_assets[tx.asset_id].extracted_isin: tx for tx in seeds}

        # BTP nominal position: controvalore 50000 / qty 50000 → 1.0 per unit (not 50000).
        btpfut = by_isin["IT0005425753"]
        assert btpfut.quantity == Decimal("50000")
        assert btpfut.cost_basis_override.amount == Decimal("1")
        assert btpfut.cost_basis_override.code == "EUR"

        # Fund position: controvalore 9990.96 / qty 91.861 → ~108.76 per unit (not 9990.96).
        eurizon = by_isin["LU2178932757"]
        assert eurizon.cost_basis_override.amount < Decimal("1000")
        assert abs(eurizon.cost_basis_override.amount * eurizon.quantity - Decimal("9990.96")) < Decimal("0.01")

        # Cash liquidity is seeded as a DEPOSIT, not folded into an ADJUSTMENT.
        deposit = next(tx for tx in out.transactions if tx.type == TransactionType.DEPOSIT)
        assert deposit.cash is not None and deposit.cash.amount == Decimal("14757.45")

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

    def test_etoro_withdrawal_conversion_fee_with_units_is_not_dropped(self, tmp_path):
        """A cash-only conversion fee remains a FEE even when eToro says Units=2."""
        header, *sample_rows = read_rows(ETORO_SAMPLE)
        type_col = header.index("Type")
        amount_col = header.index("Amount")
        units_col = header.index("Units")
        zero_fee = next(row.copy() for row in sample_rows if row[type_col] == "Withdraw Fee")
        conversion = next(row.copy() for row in sample_rows if row[type_col] == "Withdrawal Conversion Fee")
        request = next(row.copy() for row in sample_rows if row[type_col] == "Withdraw Request")
        conversion[amount_col] = "-1.36"
        conversion[units_col] = "2"

        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerows([header, zero_fee, conversion, request])
        synthetic = tmp_path / "etoro-withdrawal-conversion-fee.csv"
        synthetic.write_text(stream.getvalue(), encoding="utf-8")

        out = EtoroBrokerProvider().parse(synthetic, broker_id=1)

        assert len(out.transactions) == 2, "only the zero-value fee may be dropped from the three source rows"
        fees = [tx for tx in out.transactions if tx.type == TransactionType.FEE]
        assert len(fees) == 1, "the conversion fee must produce exactly one FEE"
        fee = fees[0]
        assert fee.quantity == Decimal("0")
        assert fee.cash is not None
        assert fee.cash.amount == Decimal("-1.36")

        withdrawals = [tx for tx in out.transactions if tx.type == TransactionType.WITHDRAWAL]
        assert len(withdrawals) == 1, "the original withdrawal must remain exactly once"
        withdrawal = withdrawals[0]
        assert withdrawal.cash is not None
        assert withdrawal.cash.amount == Decimal("-100.11")
        assert not any(issue.code == "qtyZero" for issue in out.validation_issues)
        assert sum(
            (tx.cash.amount for tx in out.transactions if tx.cash is not None),
            Decimal("0"),
        ) == Decimal("-101.47")

    def test_intesa_maturity_movement_flags_the_asset_as_expired(self):
        """Regression for the *shared* maturity-notice helper (``_brim_io.detect_maturity_hits``
        / ``MATURITY_NOTICE_KIND``), adopted by Crédit Agricole's account layout
        (see ``test_credit_agricole_account_maturity_flags_the_asset_as_expired``
        above) and by Intesa Sanpaolo's movements parser the same way.

        The repository sample (``intesa-lista.csv``) contains no maturity/redemption
        row on its own, so one minimal synthetic coupon row is appended — same
        column shape as every other row in the file, with "RIMBORSO" (a shared
        maturity keyword) folded into its ``Dettagli`` free text, exactly the way a
        real bond-redemption coupon would read.

        Asserts the *contract* the frontend actually reads — ``kind`` and the index
        into ``transactions`` — never the Italian prose in ``reason`` (rule: never
        assert on translated/localized text).
        """
        rows = read_rows(INTESA_LISTA_SAMPLE)
        rows.append(
            [
                "01/08/2026",
                "Cedole",
                "Cedole Su EUR 35.00000 BTPIT 28GN30 RIMBORSO FINALE",
                "Conto 0000/00000000",
                "CONTABILIZZATO",
                "Interessi e cedole",
                "EUR",
                "122,5",
                "",
                "",
            ]
        )

        out = IntesaSanpaoloBrokerProvider()._parse_movements(rows, broker_id=1)

        coupon_index = next(i for i, tx in enumerate(out.transactions) if tx.type == TransactionType.INTEREST and tx.date == date(2026, 8, 1) and tx.cash is not None and tx.cash.amount == Decimal("122.5"))
        coupon = out.transactions[coupon_index]
        assert coupon.asset_id is not None

        info = out.extracted_assets[coupon.asset_id]
        kinds = [n.kind for n in info.notices]
        assert MATURITY_NOTICE_KIND in kinds, f"expected a maturity notice on {info.extracted_name!r}, got {kinds}"

        notice = next(n for n in info.notices if n.kind == MATURITY_NOTICE_KIND)
        assert notice.transaction_indexes == [coupon_index]
        # Contract only: a reason must be present, its wording is not part of the contract.
        assert notice.reason and notice.reason.strip()


# =============================================================================
# PLUGIN -> FRONTEND CONTRACT
# =============================================================================


class TestPluginFrontendContract:
    """The shape a plugin must speak so the wizard can render it.

    The per-behaviour tests above assert *what* Crédit Agricole says about a given row.
    These assert the *form* every plugin owes the frontend, on every sample we ship: a
    todo the user cannot reach, a split hint with nothing to split, evidence with no
    comment or a notice with no code are all silent breakages — the wizard renders an
    empty panel and no test would otherwise notice.

    They are deliberately written against the whole parse output rather than a chosen
    row, so a new causale added tomorrow is covered the day it is written.
    """

    # Samples whose plugin emits the richest contract surface. Add a file here and the
    # whole class applies to it.
    CONTRACT_SAMPLES = [
        ("broker_credit_agricole", CA_CONTI_SAMPLE),
        ("broker_credit_agricole", CA_SAMPLE),
    ]

    KNOWN_ASSET_NOTICE_KINDS = {MATURITY_NOTICE_KIND}

    # Every correction reason the frontend has a panel heading for.
    KNOWN_REASON_CODES = {
        "ca_account_charge_unallocated",
        "ca_account_trade_bundled_amount",
        "ca_account_trade_sell_quantity_presumed",
        "ca_account_trade_unresolved",
        "derived_quantity",
    }

    @staticmethod
    def _parse(path):
        return CreditAgricoleBrokerProvider().parse(path, broker_id=1)

    @staticmethod
    def _line_count(path) -> int:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return sum(1 for _ in fh)

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_every_field_todo_is_addressable(self, plugin, path):
        """A todo must point at a row the user can actually open, and name a field.

        ``tx_index`` is a position in the returned transaction list: out of range, the
        wizard shows a correction card wired to nothing.
        """
        out = self._parse(path)

        for todo in out.field_todos:
            assert 0 <= todo.tx_index < len(out.transactions), f"{todo.reason_code}: tx_index {todo.tx_index} outside 0..{len(out.transactions) - 1}"
            assert todo.field, f"{todo.reason_code}: empty field"
            assert todo.severity in {"blocker", "warning"}, f"{todo.reason_code}: severity {todo.severity!r}"
            assert todo.message and todo.message.strip(), f"{todo.reason_code}: empty message"

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_every_todo_carries_a_stable_reason_code(self, plugin, path):
        """The frontend groups the correction step by ``reason_code`` and titles each
        panel from it. A missing or free-form code lands every todo in one anonymous
        group, which is the state the step was built to replace.
        """
        out = self._parse(path)

        for todo in out.field_todos:
            assert todo.reason_code, f"todo on tx {todo.tx_index} has no reason_code"
            assert re.fullmatch(r"[a-z][a-z0-9_]*", todo.reason_code), f"reason_code {todo.reason_code!r} is not a stable snake_case key"

    def test_every_split_hint_comes_with_something_to_split(self):
        """``split_hint`` opens the N-leg editor; ``split_suggestions`` is what it shows.

        A hint without suggestions renders an editor with no guidance on a row the plugin
        itself could not break down — the worst possible place to leave the user alone.

        Only the account layout bundles several charges into one amount; the securities
        layout states them separately and legitimately never opens this channel.
        """
        out = self._parse(CA_CONTI_SAMPLE)

        hinted = [t for t in out.field_todos if isinstance(t.context, dict) and "split_hint" in t.context]
        assert hinted, "account sample must exercise the split channel"

        for todo in hinted:
            assert todo.context["split_hint"], f"{todo.reason_code}: empty split_hint"
            suggestions = todo.context.get("split_suggestions")
            assert isinstance(suggestions, list) and suggestions, f"{todo.reason_code}: split_hint with no suggestions"
            assert all(isinstance(s, str) and s.strip() for s in suggestions), f"{todo.reason_code}: blank suggestion"

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_every_referenced_source_row_exists(self, plugin, path):
        """``row`` and ``nominale_row`` are line numbers the user is invited to go and read.

        They are 1-based and must fall inside the file: the evidence table renders them as
        a link, and a number past the end sends the reader nowhere.
        """
        out = self._parse(path)
        lines = self._line_count(path)

        for todo in out.field_todos:
            if not isinstance(todo.context, dict):
                continue
            for key in ("row", "nominale_row"):
                value = todo.context.get(key)
                if value is None:
                    continue
                assert isinstance(value, int), f"{todo.reason_code}: {key} is {type(value).__name__}, not a line number"
                assert 1 <= value <= lines, f"{todo.reason_code}: {key}={value} outside 1..{lines}"

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_every_notice_is_renderable(self, plugin, path):
        """A notice is a headline plus, optionally, the data behind it.

        The frontend keys its icon and its colour off ``severity``, and its i18n label off
        ``code``; evidence is rendered as a table with the comment as its explanation, so
        a table without one is a grid of numbers with no statement about them.
        """
        out = self._parse(path)

        for notice in out.warnings:
            assert notice.severity in {"info", "warning"}, f"{notice.code}: severity {notice.severity!r}"
            assert notice.code and notice.code.strip(), "notice with no code"
            assert notice.message and notice.message.strip(), f"{notice.code}: empty message"
            for ev in notice.evidence:
                assert ev.title and ev.title.strip(), f"{notice.code}: evidence with no title"
                assert ev.comment and ev.comment.strip(), f"{notice.code}: evidence table with no comment"
                assert all(len(row) == len(ev.headers) for row in ev.rows), f"{notice.code}: evidence row width does not match headers"
                assert not ev.row_numbers or len(ev.row_numbers) == len(ev.rows), f"{notice.code}: row_numbers must be empty or aligned with rows"

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_every_todo_evidence_is_renderable(self, plugin, path):
        """Same contract on the correction step's own evidence tables."""
        out = self._parse(path)

        for todo in out.field_todos:
            for ev in todo.evidence:
                assert ev.title and ev.title.strip(), f"{todo.reason_code}: evidence with no title"
                assert ev.comment and ev.comment.strip(), f"{todo.reason_code}: evidence table with no comment"
                assert all(len(row) == len(ev.headers) for row in ev.rows), f"{todo.reason_code}: evidence row width does not match headers"

    def test_the_account_sample_exercises_every_reason_code_we_ship(self):
        """The registry of correction reasons, asserted as a closed set.

        Grouping, ordering and the per-panel wording are all keyed off these codes. A new
        one appearing unannounced would render under a generic heading; one disappearing
        would leave dead translations behind. Either way the change should be deliberate.

        ``derived_quantity`` is raised by the shared maturity model rather than by the
        account parser, so it is expected from the securities layout, not from this one.
        """
        out = self._parse(CA_CONTI_SAMPLE)

        emitted = {t.reason_code for t in out.field_todos}
        assert emitted == {
            "ca_account_charge_unallocated",
            "ca_account_trade_bundled_amount",
            "ca_account_trade_sell_quantity_presumed",
            "ca_account_trade_unresolved",
        }, f"reason codes drifted: {sorted(emitted)}"
        assert emitted <= self.KNOWN_REASON_CODES

    @pytest.mark.parametrize("plugin,path", CONTRACT_SAMPLES, ids=lambda v: getattr(v, "name", v))
    def test_no_sample_invents_a_reason_code_outside_the_registry(self, plugin, path):
        """Whatever the layout, the codes come from one declared list."""
        out = self._parse(path)

        assert {t.reason_code for t in out.field_todos} <= self.KNOWN_REASON_CODES

    def test_every_correction_reason_shows_its_working(self):
        """Each reason must arrive with at least one evidence table carrying a comment.

        The step asks the user to overrule the plugin; doing that on an assertion alone,
        with the source row not on screen, is guesswork.
        """
        out = self._parse(CA_CONTI_SAMPLE)

        by_reason: dict = {}
        for todo in out.field_todos:
            by_reason.setdefault(todo.reason_code, []).append(todo)

        for reason, todos in by_reason.items():
            assert any(t.evidence for t in todos), f"{reason}: no todo carries evidence"
            assert any(ev.comment for t in todos for ev in t.evidence), f"{reason}: evidence carries no comment"

    def test_asset_notices_declare_a_known_kind_and_a_reason(self):
        """The maturity advisory, as the frontend reads it.

        ``kind`` selects the banner label and groups the bullets; ``reason`` is the bullet.
        An unknown kind still renders — under a generic heading — so the assertion is here,
        where a new kind can be paired with its translation, and not in the component.
        """
        out = self._parse(CA_CONTI_SAMPLE)

        noticed = [(aid, n) for aid, info in out.extracted_assets.items() for n in info.notices]
        assert noticed, "account sample must raise at least one asset notice"

        for aid, notice in noticed:
            assert notice.kind in self.KNOWN_ASSET_NOTICE_KINDS, f"asset {aid}: unknown notice kind {notice.kind!r}"
            assert notice.reason and notice.reason.strip(), f"asset {aid}: notice with no reason"
            assert all(0 <= i < len(out.transactions) for i in notice.transaction_indexes), f"asset {aid}: notice points outside the transaction list"

    def test_an_unknown_causale_never_escalates_past_information(self):
        """A causale we have never seen is news, not a fault.

        It is reported so the user knows the row was booked on a guess, and so we can add
        it to the registry; raising it to ``warning`` would put a red banner on a file that
        parsed correctly. The shipped sample contains no unmapped causale on purpose, so
        one is appended here — the same way the behavioural test does.
        """
        rows = read_rows(CA_CONTI_SAMPLE)
        rows.append(["12/07/2026", "12/07/2026", "CAUSALE MAI VISTA", "MOVIMENTO IGNOTO", "'-10,00", "EUR"])
        out = CreditAgricoleBrokerProvider()._parse_account_movements(rows, broker_id=1)

        unknown = [n for n in out.warnings if n.code == "ca_unknown_causale"]
        assert unknown, "an unmapped causale must be declared"
        assert all(n.severity == "info" for n in unknown)
        assert all(n.context and n.context.get("causali") for n in unknown), "the notice must name the causali it saw"
        assert all(ev.row_numbers for n in unknown for ev in n.evidence), "the user must be able to go and read the row"

    def test_a_blocker_always_names_a_field_the_user_can_edit(self):
        """A blocker gates the step, so it must be answerable there.

        The correction step edits type, date, quantity, the instrument and the cash leg;
        blocking on anything else would be a wall with no door — the reason a cost-basis
        complaint is deliberately left to the bulk editor.
        """
        editable = {"type", "date", "quantity", "asset_id", "cash", "cash.amount", "cash.code"}
        out = self._parse(CA_CONTI_SAMPLE)

        for todo in out.field_todos:
            if todo.severity != "blocker":
                continue
            assert todo.field in editable, f"{todo.reason_code}: blocker on non-editable field {todo.field!r}"


# =============================================================================
# CRÉDIT AGRICOLE — CANONICAL CHARACTERIZATION (CSV/XLSX PARITY)
# =============================================================================


class TestCreditAgricoleCanonicalCharacterization:
    """Freeze the complete canonical CA parse outputs and CSV/XLSX parity.

    The expected values below are deliberately literal, readable Python structures:
    they are not hashes, serialized blobs, or values computed from parser output at
    test runtime. Every BRIMParseOutput channel and every nested field participates.
    """

    LAYOUTS = [
        ("securities", CA_SAMPLE, CA_SAMPLE_XLSX, 9),
        ("account", CA_CONTI_SAMPLE, CA_CONTI_SAMPLE_XLSX, 0),
    ]

    EXPECTED_OUTPUTS = {
        "securities": {
            "transactions": [
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "INTEREST",
                    "date": "2026-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/12/2026 1.25%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/12/2026 1.25% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "INTEREST",
                    "date": "2026-05-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "SELL",
                    "date": "2026-05-21",
                    "quantity": "-30000.000",
                    "cash": {"code": "EUR", "amount": "30000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "TITOLI SCADUTI: BTP 05/26 0.55FOICUM (redeemed at par 100, nominal 30000.000 [position], premium 105.00)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2026-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "maturity_premium"],
                    "description": "[TITOLI SCADUTI — premio/rivalutazione a scadenza] BTP 05/26 0.55FOICUM (surplus over par 105.00)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-30000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for SELL BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2026-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "338.04"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 05/26 0.55FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-338.04"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "INTEREST",
                    "date": "2026-05-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 17-11-28 FUT CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 17-11-28 FUT CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "INTEREST",
                    "date": "2026-05-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "324.84"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 16-11-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-05-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-324.84"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 16-11-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "INTEREST",
                    "date": "2026-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "258.99"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65%FOIEX",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-258.99"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65%FOIEX (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "INTEREST",
                    "date": "2026-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "295.99"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-295.99"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "INTEREST",
                    "date": "2026-04-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 27-04-37 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-04-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 27-04-37 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483639,
                    "type": "INTEREST",
                    "date": "2026-03-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "732.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/03/35 3,35%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-03-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-732.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/03/35 3,35% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483638,
                    "type": "INTEREST",
                    "date": "2026-03-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "360.94"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/3/32 1,65%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-03-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-360.94"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/3/32 1,65% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "INTEREST",
                    "date": "2026-02-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-02-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "INTEREST",
                    "date": "2026-02-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 15/02/29 0,45%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-02-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 15/02/29 0,45% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "INTEREST",
                    "date": "2026-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/08/30 0.95%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/08/30 0.95% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "INTEREST",
                    "date": "2026-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/08/31 0,60%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/08/31 0,60% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "INTEREST",
                    "date": "2025-12-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/12/2026 1.25%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-12-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/12/2026 1.25% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "INTEREST",
                    "date": "2025-11-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-11-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2025-11-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "167.74"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 05/26 0.55FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-11-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-167.74"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "INTEREST",
                    "date": "2025-11-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 17-11-28 FUT CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-11-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 17-11-28 FUT CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "INTEREST",
                    "date": "2025-11-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 16-11-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-11-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 16-11-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483634,
                    "type": "SELL",
                    "date": "2025-11-10",
                    "quantity": "-1867.178",
                    "cash": {"code": "EUR", "amount": "9984.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "FONDI: RIMBORSO: AMUNDI PRIMO INV LC",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-11-10",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-9984.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for SELL AMUNDI PRIMO INV LC (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2025-11-07",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "20129.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for BUY AMUNDI PIO GLOB EQ G (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483633,
                    "type": "BUY",
                    "date": "2025-11-07",
                    "quantity": "1843.575",
                    "cash": {"code": "EUR", "amount": "-20129.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "SICAV: SOTTOSCR: AMUNDI PIO GLOB EQ G",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "INTEREST",
                    "date": "2025-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "322.67"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-322.67"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "INTEREST",
                    "date": "2025-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "282.34"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65%FOIEX",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-282.34"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65%FOIEX (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "INTEREST",
                    "date": "2025-10-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 27-04-37 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-10-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 27-04-37 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483638,
                    "type": "INTEREST",
                    "date": "2025-09-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "360.94"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/3/32 1,65%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-09-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-360.94"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/3/32 1,65% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483639,
                    "type": "INTEREST",
                    "date": "2025-09-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "732.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/03/35 3,35%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-09-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-732.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/03/35 3,35% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "INTEREST",
                    "date": "2025-08-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-08-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "INTEREST",
                    "date": "2025-08-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 15/02/29 0,45%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-08-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 15/02/29 0,45% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "INTEREST",
                    "date": "2025-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/08/30 0.95%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/08/30 0.95% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "INTEREST",
                    "date": "2025-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/08/31 0,60%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/08/31 0,60% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2025-07-24",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "50683.13"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for BUY BTP 01/03/35 3,35% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483639,
                    "type": "BUY",
                    "date": "2025-07-24",
                    "quantity": "50000",
                    "cash": {"code": "EUR", "amount": "-50683.13"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "ACQ.CONT.SU MERC.: BTP 01/03/35 3,35%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2025-07-24",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "46603.73"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for BUY BTP 1/3/32 1,65% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483638,
                    "type": "BUY",
                    "date": "2025-07-24",
                    "quantity": "50000",
                    "cash": {"code": "EUR", "amount": "-46603.73"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "ACQ.CONT.SU MERC.: BTP 1/3/32 1,65%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "INTEREST",
                    "date": "2025-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/12/2026 1.25%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/12/2026 1.25% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "SELL",
                    "date": "2025-05-26",
                    "quantity": "-95000.000",
                    "cash": {"code": "EUR", "amount": "95000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "TITOLI SCADUTI: BTP 20-25 1.40FOICUM (redeemed at par 100, nominal 95000.000 [position], premium 665.00)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "INTEREST",
                    "date": "2025-05-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "665.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "maturity_premium"],
                    "description": "[TITOLI SCADUTI — premio/rivalutazione a scadenza] BTP 20-25 1.40FOICUM (surplus over par 665.00)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-665.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 20-25 1.40FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-95000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for SELL BTP 20-25 1.40FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "INTEREST",
                    "date": "2025-05-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "1506.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 20-25 1.40FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-1506.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 20-25 1.40FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "INTEREST",
                    "date": "2025-05-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-25",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-93.52"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2025-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "348.57"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 05/26 0.55FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-348.57"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "INTEREST",
                    "date": "2025-05-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 17-11-28 FUT CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 17-11-28 FUT CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "INTEREST",
                    "date": "2025-05-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 16-11-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-05-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 16-11-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "INTEREST",
                    "date": "2025-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "404.14"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-404.14"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "INTEREST",
                    "date": "2025-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "353.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65%FOIEX",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-04-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-353.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65%FOIEX (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "INTEREST",
                    "date": "2025-04-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "65.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 27-04-37 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-04-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-65.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 27-04-37 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2025-02-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "15000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for BUY BTP PIU 25-2-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "BUY",
                    "date": "2025-02-17",
                    "quantity": "15000",
                    "cash": {"code": "EUR", "amount": "-15000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "ACQ.CONT.SU MERC.: BTP PIU 25-2-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "INTEREST",
                    "date": "2025-02-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 15/02/29 0,45%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-02-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 15/02/29 0,45% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "INTEREST",
                    "date": "2025-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/08/30 0.95%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/08/30 0.95% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "INTEREST",
                    "date": "2025-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/08/31 0,60%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2025-02-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/08/31 0,60% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "INTEREST",
                    "date": "2024-12-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/12/2026 1.25%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-12-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-218.75"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/12/2026 1.25% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "INTEREST",
                    "date": "2024-11-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "1028.03"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 20-25 1.40FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-11-26",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-1028.03"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 20-25 1.40FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2024-11-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "219.59"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 05/26 0.55FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-11-21",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-219.59"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 05/26 0.55FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "INTEREST",
                    "date": "2024-11-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 17-11-28 FUT CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-11-17",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-223.12"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 17-11-28 FUT CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "INTEREST",
                    "date": "2024-11-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 16-11-33 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-11-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-180.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 16-11-33 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "INTEREST",
                    "date": "2024-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "345.50"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65FOICUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-345.50"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65FOICUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "INTEREST",
                    "date": "2024-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "302.31"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 19-27 0.65%FOIEX",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-10-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-302.31"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 19-27 0.65%FOIEX (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "INTEREST",
                    "date": "2024-10-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "65.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP FUT 27-04-37 CUM",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-10-27",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-65.62"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP FUT 27-04-37 CUM (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "INTEREST",
                    "date": "2024-08-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 15/02/29 0,45%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-08-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-98.44"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 15/02/29 0,45% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "INTEREST",
                    "date": "2024-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 1/08/30 0.95%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-207.81"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 1/08/30 0.95% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "INTEREST",
                    "date": "2024-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "CEDOLA: BTP 01/08/31 0,60%",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2024-08-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-131.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "auto_cash"],
                    "description": "Auto cash for INTEREST BTP 01/08/31 0,60% (Crédit Agricole securities-only export)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483634,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-13",
                    "quantity": "618.458",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[VERS.TITOLI — successione / transfer-in] AMUNDI PRIMO INV LC (price 4.98, qty 618.458)",
                    "cost_basis_override": {"code": "EUR", "amount": "4.98"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483634,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-10",
                    "quantity": "624.36",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[VERS.TITOLI — successione / transfer-in] AMUNDI PRIMO INV LC (price 5.26, qty 624.36)",
                    "cost_basis_override": {"code": "EUR", "amount": "5.26"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483634,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-10",
                    "quantity": "624.36",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[VERS.TITOLI — successione / transfer-in] AMUNDI PRIMO INV LC (price 5.26, qty 624.36)",
                    "cost_basis_override": {"code": "EUR", "amount": "5.26"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "14000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/12/2026 1.25% (price 95.14, qty 14000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9514"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "10000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 05/26 0.55FOICUM (price 96.42, qty 10000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9642"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "14000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65FOICUM (price 95.10, qty 14000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.951"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "12000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65%FOIEX (price 95.10, qty 12000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.951"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/08/30 0.95% (price 86.09, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.8609"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "32000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 20-25 1.40FOICUM (price 98.73, qty 32000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9873"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "29000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 17-11-28 FUT CUM (price 88.48, qty 29000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.8848"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 01/08/31 0,60% (price 81.58, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.8158"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "7000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 27-04-37 CUM (price 72.61, qty 7000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.7261"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "19000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 16-11-33 CUM (price 80.16, qty 19000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.8016"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 15/02/29 0,45% (price 87.52, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.8752"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "13000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/12/2026 1.25% (price 97.24, qty 13000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9724"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "10000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 05/26 0.55FOICUM (price 100.00, qty 10000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "13000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65FOICUM (price 100.00, qty 13000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "12000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65%FOIEX (price 99.18, qty 12000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9918"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/08/30 0.95% (price 94.97, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9497"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "32000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 20-25 1.40FOICUM (price 100.00, qty 32000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "28000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 17-11-28 FUT CUM (price 100.00, qty 28000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 01/08/31 0,60% (price 90.48, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9048"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "7000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 27-04-37 CUM (price 100.00, qty 7000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "18000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 16-11-33 CUM (price 100.00, qty 18000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "17000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 15/02/29 0,45% (price 93.69, qty 17000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9369"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "13000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/12/2026 1.25% (price 97.24, qty 13000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9724"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "10000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 05/26 0.55FOICUM (price 100.00, qty 10000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483641,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "13000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65FOICUM (price 100.00, qty 13000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483642,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "11000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 19-27 0.65%FOIEX (price 99.18, qty 11000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9918"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483636,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "16000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 1/08/30 0.95% (price 94.97, qty 16000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9497"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483632,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "31000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 20-25 1.40FOICUM (price 100.00, qty 31000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "28000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 17-11-28 FUT CUM (price 100.00, qty 28000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483635,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "16000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 01/08/31 0,60% (price 90.48, qty 16000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9048"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483640,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "6000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 27-04-37 CUM (price 100.00, qty 6000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483643,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "18000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP FUT 16-11-33 CUM (price 100.00, qty 18000)",
                    "cost_basis_override": {"code": "EUR", "amount": "1.00"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483637,
                    "type": "ADJUSTMENT",
                    "date": "2024-06-05",
                    "quantity": "16000",
                    "cash": None,
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole"],
                    "description": "[GIRO ALTRO DOSSIER — successione / transfer-in] BTP 15/02/29 0,45% (price 93.69, qty 16000)",
                    "cost_basis_override": {"code": "EUR", "amount": "0.9369"},
                    "cost_basis_mode": "manual",
                    "asset_event_id": None,
                },
            ],
            "warnings": [
                {
                    "severity": "info",
                    "code": "ca_succession_transfer_in",
                    "message": "Sono stati identificati dei titoli trasferiti da un altro dossier (36 righe).\n"
                    "Sono stati registrati come transazioni di tipo «Rettifica» perché non hanno un movimento di cassa associato: si "
                    "suppone quindi che fossero già tuoi presso un altro broker.\n"
                    "In caso affermativo, e se quel broker è tracciato su LibreFolio, importando l'altra metà della transazione il "
                    "sistema proporrà di collegare le due e di trasformarle in un «Trasferimento titoli».\n"
                    "Di seguito le righe in dettaglio:",
                    "evidence": [
                        {
                            "title": "Righe di trasferimento",
                            "headers": ["Data operazione", "Nome", "Causale", "Prezzo", "Quantità", "Controvalore in Euro"],
                            "rows": [
                                ["13/06/2024", "AMUNDI PRIMO INV LC", "VERS.TITOLI", "4,98", "618.458", "0,00"],
                                ["10/06/2024", "AMUNDI PRIMO INV LC", "VERS.TITOLI", "5,26", "624.36", "0,00"],
                                ["10/06/2024", "AMUNDI PRIMO INV LC", "VERS.TITOLI", "5,26", "624.36", "0,00"],
                                ["05/06/2024", "BTP 1/12/2026 1.25%", "GIRO ALTRO DOSSIER", "95,14", "14000", "0,00"],
                                ["05/06/2024", "BTP 05/26 0.55FOICUM", "GIRO ALTRO DOSSIER", "96,42", "10000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65FOICUM", "GIRO ALTRO DOSSIER", "95,10", "14000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65%FOIEX", "GIRO ALTRO DOSSIER", "95,10", "12000", "0,00"],
                                ["05/06/2024", "BTP 1/08/30 0.95%", "GIRO ALTRO DOSSIER", "86,09", "17000", "0,00"],
                                ["05/06/2024", "BTP 20-25 1.40FOICUM", "GIRO ALTRO DOSSIER", "98,73", "32000", "0,00"],
                                ["05/06/2024", "BTP 17-11-28 FUT CUM", "GIRO ALTRO DOSSIER", "88,48", "29000", "0,00"],
                                ["05/06/2024", "BTP 01/08/31 0,60%", "GIRO ALTRO DOSSIER", "81,58", "17000", "0,00"],
                                ["05/06/2024", "BTP FUT 27-04-37 CUM", "GIRO ALTRO DOSSIER", "72,61", "7000", "0,00"],
                                ["05/06/2024", "BTP FUT 16-11-33 CUM", "GIRO ALTRO DOSSIER", "80,16", "19000", "0,00"],
                                ["05/06/2024", "BTP 15/02/29 0,45%", "GIRO ALTRO DOSSIER", "87,52", "17000", "0,00"],
                                ["05/06/2024", "BTP 1/12/2026 1.25%", "GIRO ALTRO DOSSIER", "97,24", "13000", "0,00"],
                                ["05/06/2024", "BTP 05/26 0.55FOICUM", "GIRO ALTRO DOSSIER", "100,00", "10000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65FOICUM", "GIRO ALTRO DOSSIER", "100,00", "13000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65%FOIEX", "GIRO ALTRO DOSSIER", "99,18", "12000", "0,00"],
                                ["05/06/2024", "BTP 1/08/30 0.95%", "GIRO ALTRO DOSSIER", "94,97", "17000", "0,00"],
                                ["05/06/2024", "BTP 20-25 1.40FOICUM", "GIRO ALTRO DOSSIER", "100,00", "32000", "0,00"],
                                ["05/06/2024", "BTP 17-11-28 FUT CUM", "GIRO ALTRO DOSSIER", "100,00", "28000", "0,00"],
                                ["05/06/2024", "BTP 01/08/31 0,60%", "GIRO ALTRO DOSSIER", "90,48", "17000", "0,00"],
                                ["05/06/2024", "BTP FUT 27-04-37 CUM", "GIRO ALTRO DOSSIER", "100,00", "7000", "0,00"],
                                ["05/06/2024", "BTP FUT 16-11-33 CUM", "GIRO ALTRO DOSSIER", "100,00", "18000", "0,00"],
                                ["05/06/2024", "BTP 15/02/29 0,45%", "GIRO ALTRO DOSSIER", "93,69", "17000", "0,00"],
                                ["05/06/2024", "BTP 1/12/2026 1.25%", "GIRO ALTRO DOSSIER", "97,24", "13000", "0,00"],
                                ["05/06/2024", "BTP 05/26 0.55FOICUM", "GIRO ALTRO DOSSIER", "100,00", "10000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65FOICUM", "GIRO ALTRO DOSSIER", "100,00", "13000", "0,00"],
                                ["05/06/2024", "BTP 19-27 0.65%FOIEX", "GIRO ALTRO DOSSIER", "99,18", "11000", "0,00"],
                                ["05/06/2024", "BTP 1/08/30 0.95%", "GIRO ALTRO DOSSIER", "94,97", "16000", "0,00"],
                                ["05/06/2024", "BTP 20-25 1.40FOICUM", "GIRO ALTRO DOSSIER", "100,00", "31000", "0,00"],
                                ["05/06/2024", "BTP 17-11-28 FUT CUM", "GIRO ALTRO DOSSIER", "100,00", "28000", "0,00"],
                                ["05/06/2024", "BTP 01/08/31 0,60%", "GIRO ALTRO DOSSIER", "90,48", "16000", "0,00"],
                                ["05/06/2024", "BTP FUT 27-04-37 CUM", "GIRO ALTRO DOSSIER", "100,00", "6000", "0,00"],
                                ["05/06/2024", "BTP FUT 16-11-33 CUM", "GIRO ALTRO DOSSIER", "100,00", "18000", "0,00"],
                                ["05/06/2024", "BTP 15/02/29 0,45%", "GIRO ALTRO DOSSIER", "93,69", "16000", "0,00"],
                            ],
                            "row_numbers": [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95],
                            "comment": "Ogni riga qui sotto è un versamento titoli senza contropartita di cassa: nessun denaro è uscito dal " "conto, quindi la posizione è stata aperta come «Rettifica».",
                        }
                    ],
                    "context": {"row_count": 36},
                }
            ],
            "validation_issues": [],
            "field_todos": [],
            "extracted_assets": {
                2147483647: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 1/12/2026 1.25%", "notices": []},
                2147483646: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP PIU 25-2-33 CUM", "notices": []},
                2147483645: {
                    "extracted_symbol": None,
                    "extracted_isin": None,
                    "extracted_name": "BTP 05/26 0.55FOICUM",
                    "notices": [{"kind": "maturity_suspected", "reason": "Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: " "RIMBORSO»).", "transaction_indexes": [4, 5]}],
                },
                2147483644: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 17-11-28 FUT CUM", "notices": []},
                2147483643: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP FUT 16-11-33 CUM", "notices": []},
                2147483642: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 19-27 0.65%FOIEX", "notices": []},
                2147483641: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 19-27 0.65FOICUM", "notices": []},
                2147483640: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP FUT 27-04-37 CUM", "notices": []},
                2147483639: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 01/03/35 3,35%", "notices": []},
                2147483638: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 1/3/32 1,65%", "notices": []},
                2147483637: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 15/02/29 0,45%", "notices": []},
                2147483636: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 1/08/30 0.95%", "notices": []},
                2147483635: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP 01/08/31 0,60%", "notices": []},
                2147483634: {
                    "extracted_symbol": None,
                    "extracted_isin": None,
                    "extracted_name": "AMUNDI PRIMO INV LC",
                    "notices": [{"kind": "maturity_suspected", "reason": "Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: " "RIMBORSO»).", "transaction_indexes": [42]}],
                },
                2147483633: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "AMUNDI PIO GLOB EQ G", "notices": []},
                2147483632: {
                    "extracted_symbol": None,
                    "extracted_isin": None,
                    "extracted_name": "BTP 20-25 1.40FOICUM",
                    "notices": [{"kind": "maturity_suspected", "reason": "Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: " "RIMBORSO»).", "transaction_indexes": [70, 71]}],
                },
            },
        },
        "account": {
            "transactions": [
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-07-30",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-61.20"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "pagamento_utenze"],
                    "description": "SDD A : UTILITY PROVIDER ADDEBITO SDD NUMERO 0000000001",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-07-29",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-500.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "prelievo_sport_autom_altra_banca"],
                    "description": "PREL. CON CARTA 00000000 DEL 29/07/26 ALTRA BANCA -SPORT. ROMA",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-07-28",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-42.10"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "pagamento_tramite_pos"],
                    "description": "POS CARTA 00000000 DEL 28/07/26 C/O SUPERMARKET - ROMA",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2026-07-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "2879.70"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "accredito_emolumenti"],
                    "description": "PENSIONE INPS 0000 000 00000000 01 DEL 01.07.2026",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2026-07-05",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "231.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "giroconto_bonifico"],
                    "description": "ORD:MITTENTE SAMPLE DT.ORD:000000 DESCR.OPERAZIONE SCT:RIMBORSO",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "INTEREST",
                    "date": "2026-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "250.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
                    "description": "CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 NOMINALE: 40.000,00 TASSO: 1,25 ALIQ: 12,50 " "RITENUTA: 31,25 DATA : 01/06/2026 N.MOVIM: 1",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "TAX",
                    "date": "2026-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-31.25"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti", "withholding_tax"],
                    "description": "[CEDOLE, DIVIDENDI, PREMI ESTRATTI — ritenuta] CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 " "NOMINALE: 40.000,00 TASSO: 1,25 ALIQ: 12,50 RITENUTA: 31,25 DATA : 01/06/2026 N.MOVIM: 1",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483646,
                    "type": "DIVIDEND",
                    "date": "2026-06-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "95.40"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
                    "description": "DIVIDENDO AZIONE SAMPLE IT0000000002 DOS:00000/00000000",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "INTEREST",
                    "date": "2026-06-16",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "12.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
                    "description": "DIVIDENDO CONGUAGLIO SENZA TITOLO IDENTIFICATO",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "TAX",
                    "date": "2026-07-14",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-21.42"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "commiss_spese_su_operaz_titoli"],
                    "description": "ADDEBITO CAPITAL GAIN (D.LGS 461/97) 0000000000000 DATA:21/05/2026",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "FEE",
                    "date": "2026-06-01",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-1.50"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "commiss_spese_su_operaz_titoli"],
                    "description": "SPESE STACCO CEDOLA DEL 01/06/2026 DOSSIER: 00000/00000000 TIT: IT0000000001",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "TAX",
                    "date": "2026-06-30",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-87.50"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "commissioni_spese"],
                    "description": "Imposta bollo prodotti finanziari DATA 30/06/2026 RAPP.00000/0000000000000 TIT",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "FEE",
                    "date": "2026-06-30",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-10.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "commissioni_spese"],
                    "description": "SPESE DI GESTIONE E AMMINISTRAZ. DOS:0000/00000000 DATA:30/06/2026",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "FEE",
                    "date": "2026-06-30",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-4.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "interessi_competenze"],
                    "description": "CANONE MENSILE CONTO SMART 06/26",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "INTEREST",
                    "date": "2025-12-31",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "3.20"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "interessi_competenze"],
                    "description": "INTERESSI CREDITORI LORDI ANNO 2025",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483647,
                    "type": "BUY",
                    "date": "2026-05-21",
                    "quantity": "40000.00",
                    "cash": {"code": "EUR", "amount": "-40000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "compravendita_titoli_fondi_opzioni", "account_trade"],
                    "description": "NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:00000/00000000",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "INTEREST",
                    "date": "2026-06-02",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "200.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
                    "description": "CEDOLA:BTP OTHER 1/9/2030 IT0000000003 DOS:00000/00000000 NOMINALE: 20.000,00 TASSO: 2,00",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "BUY",
                    "date": "2026-05-10",
                    "quantity": "20000.00",
                    "cash": {"code": "EUR", "amount": "-20412.33"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "compravendita_titoli_fondi_opzioni", "account_trade"],
                    "description": "NOTA INF. ACQ. TIT:BTP OTHER 1/9/2030 DOSS:00000/00000000",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483645,
                    "type": "SELL",
                    "date": "2026-07-20",
                    "quantity": "-20000.00",
                    "cash": {"code": "EUR", "amount": "20180.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "compravendita_titoli_fondi_opzioni", "account_trade"],
                    "description": "NOTA INF. VEND. TIT:BTP OTHER 1/9/2030 DOSS:00000/00000000",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-07-15",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-5000.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "compravendita_titoli_fondi_opzioni"],
                    "description": "SOTTOSC SICAV ORD.:2026/000000001 SAMPLE GLOB EQ FUND",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": 2147483644,
                    "type": "SELL",
                    "date": "2025-05-26",
                    "quantity": "-30105.000",
                    "cash": {"code": "EUR", "amount": "30105.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "titoli_scaduti_o_estratti", "account_maturity"],
                    "description": "[TITOLI SCADUTI O ESTRATTI — rimborso/scadenza da conto, titolo non identificato] BTP SAMPLE (source: RIMB.TIT. " "BTP SAMPLE (0000000 ) DOS:00000/00000000 26/05/25; venduto interamente a par 100, nominale derivato 30105.000)",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2026-07-10",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "5.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "commissioni_spese"],
                    "description": "STORNO SPESE - RIMBORSO COMMISSIONI PROMO",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "WITHDRAWAL",
                    "date": "2026-06-20",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "-50.00"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
                    "description": "STORNO CEDOLA ERRATA IT0000000001 DOS:00000/00000000",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
                {
                    "broker_id": 1,
                    "asset_id": None,
                    "type": "DEPOSIT",
                    "date": "2025-11-11",
                    "quantity": "0",
                    "cash": {"code": "EUR", "amount": "9984.47"},
                    "link_uuid": None,
                    "tags": ["import", "credit_agricole", "giroconto_bonifico"],
                    "description": "ORD:SAMPLE FUND SICAV DT.ORD:000000 DESCR.OPERAZIONESCT::RIMBORSI: : : :SU SAMPLE FUND SIC AV CL B<*> " "RIFERIMENTO SCT:XX-2025-11-10-000000001 IDENTIFICATIVO SCT:",
                    "cost_basis_override": None,
                    "cost_basis_mode": None,
                    "asset_event_id": None,
                },
            ],
            "warnings": [
                {
                    "severity": "warning",
                    "code": "ca_account_maturity_unlinked",
                    "message": "Riga 21: scadenza/rimborso 'RIMB.TIT. BTP SAMPLE (0000000 ) DOS:00000/00000000 26/05/25' non collegabile a un titolo "
                    "(ISIN e nominale non trovati nella stessa data); importata interamente come vendita a valore nominale (par 100, nessuna "
                    "quota di interesse) — verifica il nominale.",
                    "evidence": [
                        {
                            "title": "Riga del file",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["26/05/2025", "TITOLI SCADUTI O ESTRATTI", "RIMB.TIT. BTP SAMPLE (0000000 ) DOS:00000/00000000 26/05/25", "30.105,00", "EUR"]],
                            "row_numbers": [21],
                            "comment": "Per scorporare il capitale dal premio mi serve il nominale, che di solito ricavo dalla cedola pagata lo " "stesso giorno. Qui quella cedola non c'è, quindi ho trattato tutto l'importo come rimborso alla pari.",
                        }
                    ],
                    "context": {"causale": "TITOLI SCADUTI O ESTRATTI", "row": 21},
                }
            ],
            "validation_issues": [],
            "field_todos": [
                {
                    "tx_index": 9,
                    "field": "asset_id",
                    "severity": "warning",
                    "reason_code": "ca_account_charge_unallocated",
                    "message": "Riga 10: spesa su operazione titoli non collegata a nessun titolo. Assegnala al titolo giusto, oppure tienila così " "se riguarda il conto.",
                    "context": {"causale": "COMMISS./SPESE SU OPERAZ. TITOLI", "row": 10},
                    "evidence": [
                        {
                            "title": "Riga del file",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["14/07/2026", "COMMISS./SPESE SU OPERAZ. TITOLI", "ADDEBITO CAPITAL GAIN (D.LGS 461/97) 0000000000000 DATA:21/05/2026", "'-21,42", "EUR"]],
                            "row_numbers": [10],
                            "comment": "Questa è una spesa o imposta su un'operazione in titoli, ma la descrizione non dice su quale. Resta a "
                            "carico del conto invece che del titolo, e il costo di carico di quel titolo risulta più basso del "
                            "reale. Scegli il titolo a cui appartiene, oppure tienila com'è se è una spesa di conto.",
                        }
                    ],
                },
                {
                    "tx_index": 15,
                    "field": "cash",
                    "severity": "warning",
                    "reason_code": "ca_account_trade_bundled_amount",
                    "message": "Riga 16: acquisto di BTP SAMPLE 1/12/2026 — l'importo di questa riga potrebbe raggruppare più voci insieme.",
                    "context": {
                        "causale": "COMPRAVENDITA TITOLI/FONDI/OPZIONI",
                        "row": 16,
                        "isin": "IT0000000001",
                        "cash": "40000.00",
                        "nominale": "40000.00",
                        "delta": "0.00",
                        "currency": "EUR",
                        "nominale_row": 7,
                        "compare_nominal": True,
                        "split_hint": "trade_charges",
                        "split_suggestions": [
                            "Nei giorni intorno a questa operazione il file non registra nessuna riga di commissioni: se " "una commissione c'è stata, è dentro questo totale.",
                            "Se è un'obbligazione e non l'hai comprata all'emissione, il totale contiene anche il rateo " "cedolare che hai rimborsato al venditore: registralo come voce a parte, non fa parte del " "costo del titolo.",
                            "Il totale coincide al centesimo con il valore nominale: è il caso tipico dell'acquisto " "all'emissione, alla pari e senza oneri. Se è andata così, non c'è nulla da scorporare.",
                            "I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del " "solo titolo e le singole voci di spesa.",
                        ],
                    },
                    "evidence": [
                        {
                            "title": "Riga di acquisto",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["21/05/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. ACQ. TIT:BTP SAMPLE DOSS:00000/00000000", "'-40.000,00", "EUR"]],
                            "row_numbers": [16],
                            "comment": "Dal conto sono usciti 40.000,00 EUR, esattamente quanto il valore nominale dichiarato dalla cedola "
                            "alla riga 7. È il caso dell'acquisto all'emissione, alla pari e senza oneri: se è andata così non c'è "
                            "nulla da correggere. Se invece la nota informativa espone commissioni o rateo, il file li ha inglobati "
                            "qui dentro.",
                        },
                        {
                            "title": "Cedola che ha fornito il nominale",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["01/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001 DOS:00000/00000000 NOMINALE: 40.000,00 TASSO: 1,25 ALIQ: 12,50 " "RITENUTA: 31,25 DATA : 01/06/2026 N.MOVIM: 1", "218,75", "EUR"]],
                            "row_numbers": [7],
                            "comment": "L'ISIN IT0000000001 e il valore nominale 40.000,00 vengono da qui: è il capitale del titolo, cioè " "quanto la banca rimborsa a scadenza, non quanto hai pagato.",
                        },
                    ],
                },
                {
                    "tx_index": 17,
                    "field": "cash",
                    "severity": "warning",
                    "reason_code": "ca_account_trade_bundled_amount",
                    "message": "Riga 18: acquisto di BTP OTHER 1/9/2030 — l'importo di questa riga potrebbe raggruppare più voci insieme.",
                    "context": {
                        "causale": "COMPRAVENDITA TITOLI/FONDI/OPZIONI",
                        "row": 18,
                        "isin": "IT0000000003",
                        "cash": "20412.33",
                        "nominale": "20000.00",
                        "delta": "412.33",
                        "currency": "EUR",
                        "nominale_row": 17,
                        "compare_nominal": True,
                        "split_hint": "trade_charges",
                        "split_suggestions": [
                            "Nei giorni intorno a questa operazione il file non registra nessuna riga di commissioni: se " "una commissione c'è stata, è dentro questo totale.",
                            "Se è un'obbligazione e non l'hai comprata all'emissione, il totale contiene anche il rateo " "cedolare che hai rimborsato al venditore: registralo come voce a parte, non fa parte del " "costo del titolo.",
                            "I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del " "solo titolo e le singole voci di spesa.",
                        ],
                    },
                    "evidence": [
                        {
                            "title": "Riga di acquisto",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["10/05/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. ACQ. TIT:BTP OTHER 1/9/2030 DOSS:00000/00000000", "'-20.412,33", "EUR"]],
                            "row_numbers": [18],
                            "comment": "Dal conto sono usciti 20.412,33 EUR. Guardando il resto del file ho trovato una cedola dello stesso "
                            "titolo (riga 17) che dichiara 20.000,00 di valore nominale, cioè il capitale del titolo. I due numeri "
                            "non coincidono (412,33 EUR di differenza): il totale di questa riga mette insieme il prezzo del "
                            "titolo, il rateo cedolare maturato e le eventuali commissioni, e il file non li separa. La cassa è "
                            "comunque giusta; è il costo di carico a essere approssimato.",
                        },
                        {
                            "title": "Cedola che ha fornito il nominale",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["02/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP OTHER 1/9/2030 IT0000000003 DOS:00000/00000000 NOMINALE: 20.000,00 TASSO: 2,00", "200,00", "EUR"]],
                            "row_numbers": [17],
                            "comment": "L'ISIN IT0000000003 e il valore nominale 20.000,00 vengono da qui: è il capitale del titolo, cioè " "quanto la banca rimborsa a scadenza, non quanto hai pagato.",
                        },
                    ],
                },
                {
                    "tx_index": 18,
                    "field": "quantity",
                    "severity": "warning",
                    "reason_code": "ca_account_trade_sell_quantity_presumed",
                    "message": "Riga 19: vendita di BTP OTHER 1/9/2030. Ho usato 20.000,00 come quantità, cioè il valore nominale che risulta dalle " "cedole. Se hai venduto solo una parte, correggila.",
                    "context": {"causale": "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "row": 19, "isin": "IT0000000003", "nominale": "20000.00"},
                    "evidence": [
                        {
                            "title": "Riga del file",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["20/07/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. VEND. TIT:BTP OTHER 1/9/2030 DOSS:00000/00000000", "20.180,00", "EUR"]],
                            "row_numbers": [19],
                            "comment": "Il file dice quanto denaro è entrato, non quante quote sono uscite. Le cedole di IT0000000003 " "riportano un nominale di 20000.00: è la posizione, quindi è giusto solo se hai venduto tutto.",
                        }
                    ],
                },
                {
                    "tx_index": 18,
                    "field": "cash",
                    "severity": "warning",
                    "reason_code": "ca_account_trade_bundled_amount",
                    "message": "Riga 19: vendita di BTP OTHER 1/9/2030 — l'importo di questa riga potrebbe raggruppare più voci insieme.",
                    "context": {
                        "causale": "COMPRAVENDITA TITOLI/FONDI/OPZIONI",
                        "row": 19,
                        "isin": "IT0000000003",
                        "cash": "20180.00",
                        "nominale": "20000.00",
                        "delta": "180.00",
                        "currency": "EUR",
                        "nominale_row": 17,
                        "compare_nominal": False,
                        "split_hint": "trade_charges",
                        "split_suggestions": [
                            "Nei giorni intorno a questa operazione il file non registra nessuna riga di commissioni: se " "una commissione c'è stata, è dentro questo totale.",
                            "Su una vendita l'importo accreditato è già netto: per registrare il ricavo lordo scorpora qui " "le spese trattenute, l'incasso sul conto non cambia.",
                            "I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del " "solo titolo e le singole voci di spesa.",
                        ],
                    },
                    "evidence": [
                        {
                            "title": "Riga di vendita",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["20/07/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "NOTA INF. VEND. TIT:BTP OTHER 1/9/2030 DOSS:00000/00000000", "20.180,00", "EUR"]],
                            "row_numbers": [19],
                            "comment": "Sul conto sono entrati 20.180,00 EUR, ed è un importo netto: le spese sulla vendita sono già state " "trattenute e il file non le espone. Il ricavo lordo e le singole spese non sono quindi ricavabili da " "questa riga.",
                        },
                        {
                            "title": "Cedola che ha fornito il nominale",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["02/06/2026", "CEDOLE, DIVIDENDI, PREMI ESTRATTI", "CEDOLA:BTP OTHER 1/9/2030 IT0000000003 DOS:00000/00000000 NOMINALE: 20.000,00 TASSO: 2,00", "200,00", "EUR"]],
                            "row_numbers": [17],
                            "comment": "L'ISIN IT0000000003 e il valore nominale 20.000,00 vengono da qui: è il capitale del titolo, cioè " "quanto la banca rimborsa a scadenza, non quanto hai pagato.",
                        },
                    ],
                },
                {
                    "tx_index": 19,
                    "field": "asset_id",
                    "severity": "blocker",
                    "reason_code": "ca_account_trade_unresolved",
                    "message": "Riga 20: operazione su 'SAMPLE GLOB EQ FUND' senza quantità ricavabile. Scegli il titolo e inserisci la quantità.",
                    "context": {
                        "causale": "COMPRAVENDITA TITOLI/FONDI/OPZIONI",
                        "row": 20,
                        "reason": "no_quantity",
                        "split_hint": "trade_charges",
                        "cash": "5000.00",
                        "currency": "EUR",
                        "compare_nominal": False,
                        "split_suggestions": [
                            "Il file registra già delle spese su titoli a ridosso di questa data — riga 10 (21,42 EUR). " "Sono transazioni a sé: se le scorpori anche da qui le conti due volte.",
                            "È un fondo, non un'obbligazione: non ci sono ratei cedolari da scorporare, quindi la " "differenza rispetto al prezzo sono commissioni o imposte.",
                            "I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del " "solo titolo e le singole voci di spesa.",
                        ],
                    },
                    "evidence": [
                        {
                            "title": "Riga del file",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["15/07/2026", "COMPRAVENDITA TITOLI/FONDI/OPZIONI", "SOTTOSC SICAV ORD.:2026/000000001 SAMPLE GLOB EQ FUND", "'-5.000,00", "EUR"]],
                            "row_numbers": [20],
                            "comment": "Questa riga è un'operazione su titoli e il titolo si legge ('SAMPLE GLOB EQ FUND'), ma la quantità no: "
                            "nel file non ci sono cedole di questo strumento da cui ricavarla (i fondi non ne staccano). L'importo "
                            "è giusto, l'ho registrata come prelievo di cassa.",
                        }
                    ],
                },
                {
                    "tx_index": 23,
                    "field": "asset_id",
                    "severity": "blocker",
                    "reason_code": "ca_account_trade_unresolved",
                    "message": "Riga 24: sembra il disinvestimento di 'SAMPLE FUND SICAV', arrivato come bonifico. Scegli il fondo e inserisci le " "quote vendute.",
                    "context": {
                        "causale": "GIROCONTO/BONIFICO",
                        "row": 24,
                        "reason": "fund_redemption",
                        "split_hint": "trade_charges",
                        "cash": "9984.47",
                        "currency": "EUR",
                        "compare_nominal": False,
                        "split_suggestions": [
                            "Nei giorni intorno a questa operazione il file non registra nessuna riga di commissioni: se " "una commissione c'è stata, è dentro questo totale.",
                            "È un fondo, non un'obbligazione: non ci sono ratei cedolari da scorporare, quindi la " "differenza rispetto al prezzo sono commissioni o imposte.",
                            "Su una vendita l'importo accreditato è già netto: per registrare il ricavo lordo scorpora qui " "le spese trattenute, l'incasso sul conto non cambia.",
                            "I numeri esatti sono sulla nota informativa dell'operazione: da lì leggi il controvalore del " "solo titolo e le singole voci di spesa.",
                        ],
                    },
                    "evidence": [
                        {
                            "title": "Riga del file",
                            "headers": ["Data Op.", "Causale", "Descrizione", "Importo", "Divisa"],
                            "rows": [["11/11/2025", "GIROCONTO/BONIFICO", "ORD:SAMPLE FUND SICAV DT.ORD:000000 DESCR.OPERAZIONESCT::RIMBORSI: : : :SU SAMPLE FUND SIC AV CL B<*> " "RIFERIMENTO SCT:XX-2025-11-10-000000001 IDENTIFICATIVO SCT:", "9.984,47", "EUR"]],
                            "row_numbers": [24],
                            "comment": "Il denaro arriva da 'SAMPLE FUND SICAV' e la causale parla di rimborso sullo stesso fondo: è un "
                            "disinvestimento pagato per bonifico, non un accredito qualsiasi. Le quote vendute il file non le dice "
                            "— un fondo riporta il controvalore, non il numero di quote — quindi l'ho registrata come versamento di "
                            "cassa. Cambiala in vendita, scegli il fondo e inserisci le quote: altrimenti la posizione resta aperta "
                            "per sempre.",
                        }
                    ],
                },
            ],
            "extracted_assets": {
                2147483647: {"extracted_symbol": None, "extracted_isin": "IT0000000001", "extracted_name": "BTP SAMPLE 1/12/2026", "notices": []},
                2147483646: {"extracted_symbol": None, "extracted_isin": "IT0000000002", "extracted_name": "AZIONE SAMPLE", "notices": []},
                2147483645: {"extracted_symbol": None, "extracted_isin": "IT0000000003", "extracted_name": "BTP OTHER 1/9/2030", "notices": []},
                2147483644: {"extracted_symbol": None, "extracted_isin": None, "extracted_name": "BTP SAMPLE", "notices": [{"kind": "maturity_suspected", "reason": "Rilevata almeno una transazione di scadenza/rimborso (es. «TITOLI SCADUTI» o «FONDI: " "RIMBORSO»).", "transaction_indexes": [20]}]},
            },
        },
    }

    @staticmethod
    def _parse(path: Path) -> BRIMParseOutput:
        return CreditAgricoleBrokerProvider().parse(path, broker_id=1)

    @pytest.mark.parametrize(
        ("layout", "csv_path"),
        [(layout, csv_path) for layout, csv_path, _, _ in LAYOUTS],
        ids=[layout for layout, _, _, _ in LAYOUTS],
    )
    def test_csv_freezes_entire_output(self, layout: str, csv_path: Path):
        """Match every CSV value, order, fake ID, message, context and reason."""
        expected = self.EXPECTED_OUTPUTS[layout]
        csv_out = self._parse(csv_path)

        assert set(BRIMParseOutput.model_fields) == {
            "transactions",
            "warnings",
            "validation_issues",
            "field_todos",
            "extracted_assets",
        }
        assert set(TXCreateItem.model_fields) == {
            "broker_id",
            "asset_id",
            "type",
            "date",
            "quantity",
            "cash",
            "link_uuid",
            "tags",
            "description",
            "cost_basis_override",
            "cost_basis_mode",
            "asset_event_id",
        }
        assert _json_safe(csv_out) == expected, f"{layout}: complete CSV parse output drifted"

    @pytest.mark.parametrize(
        ("layout", "xlsx_path", "xlsx_evidence_offset"),
        [(layout, xlsx_path, offset) for layout, _, xlsx_path, offset in LAYOUTS],
        ids=[layout for layout, _, _, _ in LAYOUTS],
    )
    def test_xlsx_matches_entire_literal_csv_output(
        self,
        layout: str,
        xlsx_path: Path,
        xlsx_evidence_offset: int,
    ):
        """Match XLSX after only the documented +9/0 evidence-row offset."""
        pytest.importorskip("openpyxl")
        expected = self.EXPECTED_OUTPUTS[layout]
        xlsx_out = self._parse(xlsx_path)

        assert _normalize_ca_xlsx_evidence_row_numbers(xlsx_out, xlsx_evidence_offset) == expected, f"{layout}: complete XLSX parse output drifted beyond its documented evidence-row offset"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
