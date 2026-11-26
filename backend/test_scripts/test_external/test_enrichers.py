"""
External suite of the enrichers (plan 68 §C): every real enricher against its real source.

For each enricher ``EnricherRegistry`` serves that is not test-only (justETF, Borsa Italiana, Yahoo, ESMA and CoinGecko, each
declaring ``test_cases``), and each of its ``test_cases``
(``{"binding": {"identifier_type", "identifier", …params}, "asset_type": "<AssetType value>"}``):

- ``recognize`` finds the binding, with a name;
- ``read([binding])`` yields exactly one item, ``OK``, whose values are a non-empty subset of the plugin's
  ``voices[asset_type]``, every value passing the real catalogue (``normalize_value``); for an ETF ``ter``,
  ``fund_provider`` and ``distribution_policy`` are there.

Then, per enricher, the not-found side when this file knows one for it (``NOT_FOUND_CASES``: for justETF the ISIN of a
stock, Enel, which the site answers with its empty «ETF Screener» sheet; for CoinGecko an id no coin has), and, when it
searches, one search with at least one result bound by the type the enricher binds (``SEARCH_CASES``): «MSCI World» by
ISIN by default (justETF, Borsa Italiana), by TICKER for Yahoo Finance (the symbol with its market's suffix), and for
CoinGecko «bitcoin» by ``COINGECKO_ID``, with ``bitcoin`` among the results. ESMA does not search.

An enricher whose required settings, its own or its groups', have no value (CoinGecko without its API key) is skipped with
«<code>: not configured», in the recognize, read, not-found and search tests, **before any request**. The settings are
bound offline, from the environment only (``LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY``), with no database: the same
resolver the app uses (``build_bound_settings``).

A refusal for too many requests fails the test with a message saying so, never a silent skip. The plugin's own pause
between page calls is kept. Network: yes, by design. No database, no server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from backend.app.db.models import AssetType
from backend.app.services.assets.base import rate_limited_from_exception
from backend.app.services.assets.profile.catalogue import ProfileValueError, normalize_value
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherReadStatus
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.groups import plugin_groups
from backend.app.services.plugin_settings.resolver import build_bound_settings
from backend.test_scripts.test_utils import print_info, print_success

#: The voices an ETF's read must give, among those its enricher declares for the type: justETF declares all three,
#: Yahoo (C3) ``ter`` and ``fund_provider`` only (it never gives a distribution policy).
ETF_REQUIRED_VOICES = frozenset({"ter", "fund_provider", "distribution_policy"})
#: Per enricher code, bindings its source does not know (well formed, so the «not found» path of the source is
#: exercised, not the plugin's own refusal of a malformed identifier).
NOT_FOUND_CASES: dict[str, list[EnricherBinding]] = {
    # Enel, a stock: justETF answers its empty «ETF Screener» sheet
    "justetf": [EnricherBinding("ISIN", "IT0003128367")],
    # An id CoinGecko does not have (its answer is a 404, «not found», never an error)
    "coingecko": [EnricherBinding("COINGECKO_ID", "librefolio-no-such-coin")],
}


@dataclass(frozen=True)
class SearchCase:
    """What one enricher's search is asked and must answer: the text, the identifier type of the bindings it gives, and an
    identifier that must be among them (None: any result of the type is enough)."""

    query: str = "MSCI World"
    identifier_type: str = "ISIN"
    expected_identifier: str | None = None


#: Per enricher code, when it is not the default («MSCI World», bound by ISIN: justETF and Borsa Italiana). ESMA does not search.
SEARCH_CASES: dict[str, SearchCase] = {
    # Yahoo's search binds the symbol with its market's suffix (ENR-3b)
    "yfinance": SearchCase(identifier_type="TICKER"),
    "coingecko": SearchCase(query="bitcoin", identifier_type="COINGECKO_ID", expected_identifier="bitcoin"),
}


def _real_enricher_codes() -> list[str]:
    """The codes of the enrichers the registry serves, the test-only ones left out."""
    return sorted(code for code in EnricherRegistry.list_plugin_codes() if not getattr(EnricherRegistry.get_plugin(code), "test_only", False))


REAL_CODES = _real_enricher_codes()


def _plugin(code: str) -> EnricherPlugin:
    """The registry's instance with its settings bound offline (the environment and the defaults, no database)."""
    plugin = EnricherRegistry.get_plugin_instance(code)
    assert plugin is not None, f"{code}: the registry serves no instance"
    if isinstance(plugin, PluginSettingsMixin):
        groups = plugin_groups(type(plugin))
        fields = getattr(type(plugin), "settings_fields", ())
        plugin.bind_settings(build_bound_settings(EnricherRegistry.settings_family(), plugin.code, fields, {}, None, user_id=None, groups=[(group, {}) for group in groups]))
    return plugin


def _ready(code: str) -> EnricherPlugin:
    """The bound plugin, or a skip, with no request, when a required setting of it has no value (as the asset providers'
    external suite does for CoinGecko without its key)."""
    plugin = _plugin(code)
    if isinstance(plugin, PluginSettingsMixin) and plugin.settings.missing:
        print_info(f"{code} is not configured ({', '.join(plugin.settings.missing)}) - SKIPPING")
        pytest.skip(f"{code}: not configured")
    return plugin


def _binding(case: dict[str, Any]) -> EnricherBinding:
    raw = dict(case["binding"])
    identifier_type, identifier = raw.pop("identifier_type"), raw.pop("identifier")
    return EnricherBinding(identifier_type, identifier, raw)


def _cases() -> list[Any]:
    params = []
    for code in REAL_CODES:
        for index, case in enumerate(_plugin(code).test_cases):
            label = f"{code}-{case['binding']['identifier']}-{case['asset_type']}"
            params.append(pytest.param(code, index, id=label))
    return params


def _fail_if_refused(code: str, error: BaseException, what: str) -> None:
    if rate_limited_from_exception(error, code) is not None:
        pytest.fail(f"{code}: the source refused {what} for too many requests (429): {error!r}. Not a defect of the plugin: run the suite again later, once")


def _read_one(code: str, plugin: EnricherPlugin, binding: EnricherBinding) -> EnricherReadItem:
    try:
        items = list(plugin.read([binding]))
    except Exception as exc:  # noqa: BLE001 — read must never raise: say so, with the cause, instead of a bare traceback
        _fail_if_refused(code, exc, f"the read of {binding.identifier}")
        pytest.fail(f"{code}: read raised for {binding.identifier} (it must yield an ERROR item instead): {exc!r}")
    assert len(items) == 1 and items[0].index == 0, f"{code}: one item for one binding: {items}"
    item = items[0]
    if item.status == EnricherReadStatus.ERROR and item.error_code == RATE_LIMITED:
        pytest.fail(f"{code}: the source refused the read of {binding.identifier} for too many requests (429, retry_after={item.retry_after}). Run the suite again later, once")
    return item


# =============================================================================
# Barrier
# =============================================================================


def test_at_least_one_real_enricher_is_served():
    """Barrier: without a real enricher every parametrised test below would be an empty, green collection."""
    failures = list(EnricherRegistry.get_discovery_errors())
    assert failures == [], f"enricher plugins failed to load: {failures}"
    assert REAL_CODES, "no real (non-test-only) enricher is served"
    for code in REAL_CODES:
        assert _plugin(code).test_cases, f"{code}: declares no test_cases, so the external suite never reaches its source"


# =============================================================================
# Each test case: recognize and read
# =============================================================================


@pytest.mark.parametrize(("code", "index"), _cases())
def test_recognize_finds_the_case(code: str, index: int):
    plugin = _ready(code)
    case = plugin.test_cases[index]
    binding = _binding(case)
    try:
        recognition = plugin.recognize(binding)
    except Exception as exc:  # noqa: BLE001 — name a 429 for what it is; any other failure is reported with its cause
        _fail_if_refused(code, exc, f"the recognition of {binding.identifier}")
        pytest.fail(f"{code}: recognize raised for {binding.identifier}: {exc!r}")
    assert recognition.found is True, f"{code}: {binding.identifier} not recognized: {recognition}"
    assert isinstance(recognition.name, str) and recognition.name.strip(), f"{code}: found without a name: {recognition}"
    print_success(f"{code}: {binding.identifier} recognized as «{recognition.name}» ({recognition.page_url})")


@pytest.mark.parametrize(("code", "index"), _cases())
def test_read_gives_declared_voices_in_stored_form(code: str, index: int):
    plugin = _ready(code)
    case = plugin.test_cases[index]
    binding = _binding(case)
    asset_type = AssetType(case["asset_type"])
    declared = plugin.voices.get(asset_type, frozenset())
    assert declared, f"{code}: a test case of type {asset_type.value}, which it declares no voices for"

    item = _read_one(code, plugin, binding)

    assert item.status == EnricherReadStatus.OK, f"{code}: {binding.identifier}: {item.status} {item.error_code} {item.error_message}"
    assert item.values, f"{code}: {binding.identifier} read with no value at all"
    undeclared = sorted(set(item.values) - declared)
    assert not undeclared, f"{code}: voices not declared for {asset_type.value}: {undeclared}"
    stored: dict[str, Any] = {}
    refused: dict[str, str] = {}
    for key, value in item.values.items():
        try:
            stored[key] = normalize_value(key, value)
        except ProfileValueError as exc:
            refused[key] = f"{value!r}: {exc.reason}"
    assert not refused, f"{code}: {binding.identifier}: values the catalogue refuses: {refused}"
    if asset_type == AssetType.ETF:
        missing = sorted((ETF_REQUIRED_VOICES & declared) - set(stored))
        assert not missing, f"{code}: {binding.identifier}: an ETF read without {missing}"

    print_info(f"{code}: {binding.identifier} ({asset_type.value}) read {len(stored)} voices, source_date={item.source_date}")
    for key in sorted(stored):
        value = stored[key]
        shown = sorted(value) if key in ("geography", "sector") and isinstance(value, dict) else value
        if key == "description":
            shown = f"{str(value)[:80]}…"
        print_info(f"    {key}: {shown}")


# =============================================================================
# Per enricher: not found, search
# =============================================================================


def _not_found_params() -> list[Any]:
    return [pytest.param(code, binding, id=f"{code}-{binding.identifier}") for code in REAL_CODES for binding in NOT_FOUND_CASES.get(code, [])]


@pytest.mark.parametrize(("code", "binding"), _not_found_params())
def test_unknown_identifier_is_not_found(code: str, binding: EnricherBinding):
    item = _read_one(code, _ready(code), binding)
    assert item.status == EnricherReadStatus.NOT_FOUND, f"{code}: {binding.identifier} should be unknown to the source: {item}"
    print_success(f"{code}: {binding.identifier} not found, as expected")


@pytest.mark.parametrize("code", REAL_CODES)
def test_search_finds_a_result_bound_as_the_enricher_binds(code: str):
    plugin = _ready(code)
    if not plugin.supports_search:
        print_info(f"{code}: does not search")
        return
    case = SEARCH_CASES.get(code, SearchCase())
    try:
        results = plugin.search(case.query)
    except Exception as exc:  # noqa: BLE001 — name a 429 for what it is; any other failure is reported with its cause
        _fail_if_refused(code, exc, f"the search for {case.query!r}")
        pytest.fail(f"{code}: search raised for {case.query!r}: {exc!r}")
    bound = [result for result in results if result.binding.identifier_type == case.identifier_type and result.binding.identifier]
    assert bound, f"{code}: no result bound by {case.identifier_type} for {case.query!r} among {len(results)}: {results[:5]}"
    if case.expected_identifier is not None:
        found = {result.binding.identifier for result in bound}
        assert case.expected_identifier in found, f"{code}: {case.expected_identifier!r} is not among the results for {case.query!r}: {sorted(found)[:10]}"
    print_success(f"{code}: {len(results)} results for {case.query!r}, {len(bound)} bound by {case.identifier_type}, e.g. {bound[0].name} ({bound[0].binding.identifier})")
