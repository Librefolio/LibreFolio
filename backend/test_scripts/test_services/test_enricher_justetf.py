"""
The justETF enricher (plan 68, lot C1): ``enricher_providers/justetf/plugin.py``, class ``JustETFEnricher``.

What it promises, pinned here with no network:

1. **Declarations**: ``code`` ``justetf``, ``name`` ``justETF``, ``terms`` ``PRICE_SOURCE``, ISIN only, no
   ``params_schema``, no settings, not test-only (the registry serves it on a production instance too). It covers the
   ETF family (``ETF`` and every ``ETF_*``) and ``COMMODITY`` (the ETCs) at degree 10, every other type ``None``. It
   declares twelve fund voices for each covered type, and ``legal_form`` too only where an ETC or ETN can sit (``ETF``
   generic, ``ETF_COMMODITY``, ``ETF_CRYPTO``, ``COMMODITY``; correction C1b-2). ``page_url`` is the English fund page. C5: one
   module-level ``Pacer`` spaces every call to justetf.com, whatever read, «Riconosci» or search it comes from (the
   tests replace it with one on a fake clock: no test waits).

2. **Mapping**, each yielded value passed through the real catalogue (``normalize_value``) and compared in its
   **stored** form, never the raw one only:

   - from the recorded overviews in ``fixtures/justetf/`` (``swda``, ``vwce``, ``etf_bond``, ``etf_hedged``, ``etc_gold``):
     every voice the page gives, nothing else (``currency_hedged``, ``top_holdings``, ``listings`` are not read; the
     item's ``source_date`` stays ``None``);
   - **per-voice dates** (correction C1b-1): the sheet's ``holdings_date`` (day/month/year, «30/09/2026» in every
     recording) is the date of ``geography`` and ``sector`` only, given in the item's ``source_dates``; no other voice
     is dated, and only the voices the item gives. An empty, missing or unreadable ``holdings_date`` dates nothing and
     changes no value; a sheet without breakdowns (the gold ETC) has no ``source_dates``. Through ``merge_voices`` the
     two voices carry that date and the others none;
   - from synthetic overviews, a recording with one field overridden, for what the recordings miss: every replication
     text, an unknown one (absent, one log line), the distribution texts, a domicile name per country and an unknown
     one, the inception date's English months and unreadable dates, ``ter`` ``0.0`` (a value ``0``), ETC / ETN / ETF /
     other legal structures, empty text, an untranslatable country of the breakdown (its weight folded into «Other»,
     one log line: no weight is lost, so the catalogue never refuses the map), justETF's sector names translated by the
     plugin's own table (``_SECTORS``) to the standard sectors, an unknown one passed on and stored as «Other».
   - **sectors, the generic helper first** (correction C1b-3): a name ``utils/asset/sector.py`` knows is passed on as
     it is, never through ``_SECTORS``; the table holds only names the helper does not know (a guard), and a table row
     forced onto a name the helper knows (``monkeypatch``) is not used.

3. **Not found**: an ISIN justETF does not know comes back as an «ETF Screener» sheet with every data field null (the
   recordings ``enel`` and ``mutual_fund``). Found when any of ``legal_structure``, ``ter``, ``fund_provider``, ``index`` is not
   ``None`` (``ter == 0.0`` counts).

4. **recognize**: a non-ISIN binding is not found without a call; otherwise one ``get_etf_overview(isin,
   include_gettex=False)``; a 429 raises, as an exception ``rate_limited_from_exception`` recognises.

5. **read**: one item per binding, keyed by ``index``; ``OK`` / ``NOT_FOUND`` (empty sheet, non-ISIN with no call) /
   ``ERROR`` for a library failure, the next binding still read; a 429 (the library's ``RuntimeError`` text, an
   exception with a 429 ``response``, an ``AssetRateLimitedError``) is ``ERROR`` ``RATE_LIMITED`` with ``retry_after``
   when known, and every binding after it comes back ``RATE_LIMITED`` without a call.

6. **search**: over ``load_overview()`` (a fake DataFrame indexed by ISIN), case-insensitive on name, ticker, WKN and
   ISIN; one result per fund, bound by ISIN, ``AssetType.ETF``, with its page.

No network, by construction: the plugin module is imported in a fixture, which replaces ``get_etf_overview`` and
``load_overview`` on it (``raising=True``: the names must be imported at module level into the plugin) with fakes. The
fake page answers only the ISINs a test gave it and fails the test (``pytest.fail``, a ``BaseException`` no plugin
``except Exception`` swallows) for any other, so «without a call» is checked twice: by the call log and by that fail.
Assumed: the plugin keeps no page cache of its own between calls (the read cache is the core's): synthetic ISINs are
reused across cases and the call logs are exact. A cached list of ``load_overview`` is harmless (one fake list for all).

Red before C1: the plugin module does not exist; every test fails on its own at the fixture's import
(``ModuleNotFoundError``), nothing at collection.

PURE: no database, no server, no network.
"""

from __future__ import annotations

import copy
import importlib
import json
import threading
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from structlog.testing import capture_logs

from backend.app.config import is_test_mode
from backend.app.db.models import AssetType
from backend.app.services.assets.base import AssetRateLimitedError, rate_limited_from_exception
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherRateLimited,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.refresh import ReadOutcome, merge_voices
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.call_limits import CALL_LIMIT_KEYS
from backend.app.utils.asset.sector import FinancialSector, validate_sector
from backend.app.utils.runtime.pacing import Pacer

PLUGIN_MODULE = "backend.app.services.enricher_providers.justetf.plugin"
CODE = "justetf"
TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
FIXTURES = Path(__file__).parent / "fixtures" / "justetf"

#: Every voice it can give: the voices of a covered type where an ETC or ETN can sit.
VOICES = frozenset(
    {
        "description",
        "ter",
        "fund_size",
        "index_name",
        "fund_provider",
        "replication",
        "distribution_policy",
        "fund_domicile",
        "fund_currency",
        "inception_date",
        "geography",
        "sector",
        "legal_form",
    }
)
COVERED = frozenset({AssetType.ETF, AssetType.COMMODITY} | {asset_type for asset_type in AssetType if asset_type.value.startswith("ETF_")})
#: The covered types where an ETC or ETN can sit: the only ones that declare ``legal_form`` (correction C1b-2), written
#: out, never derived from a prefix.
LEGAL_FORM_TYPES = frozenset({AssetType.ETF, AssetType.ETF_COMMODITY, AssetType.ETF_CRYPTO, AssetType.COMMODITY})
#: The voices of every other covered type: the same twelve, without ``legal_form``.
FUND_VOICES = VOICES - {"legal_form"}
DEGREE = 10
#: The ``holdings_date`` of every recording that has one («30/09/2026»), as a date.
HOLDINGS_DATE = date(2026, 9, 30)


def _page(isin: str) -> str:
    return f"https://www.justetf.com/en/etf-profile.html?isin={isin}"


def _recorded(name: str) -> dict[str, Any]:
    """The overview dict of a recording, as ``get_etf_overview`` returned it."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["calls"]["get_etf_overview"]["response"]


# =============================================================================
# Expected stored forms (from the real catalogue, written out: never recomputed with the plugin's own logic)
# =============================================================================

SWDA_GEOGRAPHY = {
    "AUS": "0.0152",
    "CAN": "0.0324",
    "CHE": "0.0247",
    "DEU": "0.0203",
    "FRA": "0.0201",
    "GBR": "0.0360",
    "IRL": "0.0109",
    "JPN": "0.0591",
    "NLD": "0.0169",
    "Other": "0.0563",
    "USA": "0.7081",
}
# justETF's sector names translated by the plugin (Finance → Financials, Consumer Cyclicals and Consumer Services →
# Consumer Discretionary, Business Services → Industrials, …), names it shares with the catalogue passed on;
# Non-Corporate is not translated (it appears in equity funds too, where it is no government bond): with justETF's own
# «Other» it is stored as «Other»
SWDA_SECTOR = {
    "Basic Materials": "0.0369",
    "Consumer Discretionary": "0.0535",
    "Consumer Staples": "0.0825",
    "Energy": "0.0406",
    "Financials": "0.1722",
    "Health Care": "0.0895",
    "Industrials": "0.1066",
    "Other": "0.0042",
    "Technology": "0.3777",
    "Telecommunication": "0.0141",
    "Utilities": "0.0222",
}

VWCE_GEOGRAPHY = {
    "AUS": "0.0150",
    "CAN": "0.0284",
    "CHE": "0.0218",
    "CHN": "0.0244",
    "DEU": "0.0175",
    "FRA": "0.0174",
    "GBR": "0.0316",
    "IND": "0.0150",
    "JPN": "0.0604",
    "KOR": "0.0260",
    "NLD": "0.0146",
    "Other": "0.0893",
    "TWN": "0.0353",
    "USA": "0.6033",
}
VWCE_SECTOR = {
    "Basic Materials": "0.0425",
    "Consumer Discretionary": "0.0537",
    "Consumer Staples": "0.0788",
    "Energy": "0.0394",
    "Financials": "0.1787",
    "Health Care": "0.0804",
    "Industrials": "0.1018",
    "Other": "0.0054",
    "Technology": "0.3827",
    "Telecommunication": "0.0142",
    "Utilities": "0.0224",
}

BOND_GEOGRAPHY = {
    "AUS": "0.0164",
    "BEL": "0.0180",
    "CAN": "0.0347",
    "CHN": "0.1131",
    "DEU": "0.0444",
    "ESP": "0.0212",
    "FRA": "0.0497",
    "GBR": "0.0419",
    "IRL": "0.0272",
    "ITA": "0.0296",
    "JPN": "0.0807",
    "KOR": "0.0133",
    "NLD": "0.0120",
    "Other": "0.2098",
    "USA": "0.2880",
}
# Sovereign, Municipal and Government Agencies summed into Government Bonds; Non-Corporate (2.4 %) into «Other»
BOND_SECTOR = {
    "Basic Materials": "0.0058",
    "Consumer Discretionary": "0.0111",
    "Consumer Staples": "0.0108",
    "Energy": "0.0114",
    "Financials": "0.1833",
    "Government Bonds": "0.5688",
    "Health Care": "0.0114",
    "Industrials": "0.0199",
    "Other": "0.1358",
    "Technology": "0.0118",
    "Telecommunication": "0.0094",
    "Utilities": "0.0205",
}

HEDGED_GEOGRAPHY = {
    "AUS": "0.0152",
    "CAN": "0.0322",
    "CHE": "0.0247",
    "DEU": "0.0201",
    "FRA": "0.0197",
    "GBR": "0.0359",
    "IRL": "0.0129",
    "JPN": "0.0586",
    "NLD": "0.0168",
    "Other": "0.0607",
    "USA": "0.7032",
}
HEDGED_SECTOR = {
    "Basic Materials": "0.0368",
    "Consumer Discretionary": "0.0526",
    "Consumer Staples": "0.0821",
    "Energy": "0.0402",
    "Financials": "0.1709",
    "Health Care": "0.0889",
    "Industrials": "0.1058",
    "Other": "0.0112",
    "Technology": "0.3752",
    "Telecommunication": "0.0140",
    "Utilities": "0.0223",
}

#: Per recording: every voice in stored form but ``description`` (compared with the recording's own text).
EXPECTED_STORED: dict[str, dict[str, Any]] = {
    "swda": {
        "ter": "0.002",
        "fund_size": {"amount": "128202000000", "currency": "EUR"},
        "index_name": "MSCI World",
        "fund_provider": "iShares",
        "replication": "physical_sampling",
        "distribution_policy": "accumulating",
        "fund_domicile": "IRL",
        "fund_currency": "USD",
        "inception_date": "2009-09-25",
        "geography": SWDA_GEOGRAPHY,
        "sector": SWDA_SECTOR,
    },
    "vwce": {
        "ter": "0.0014",
        "fund_size": {"amount": "55173000000", "currency": "EUR"},
        "index_name": "FTSE All-World",
        "fund_provider": "Vanguard",
        "replication": "physical_sampling",
        "distribution_policy": "accumulating",
        "fund_domicile": "IRL",
        "fund_currency": "USD",
        "inception_date": "2019-07-23",
        "geography": VWCE_GEOGRAPHY,
        "sector": VWCE_SECTOR,
    },
    "etf_bond": {
        "ter": "0.001",
        "fund_size": {"amount": "2468000000", "currency": "EUR"},
        "index_name": "Bloomberg Global Aggregate Bond",
        "fund_provider": "iShares",
        "replication": "physical_sampling",
        "distribution_policy": "distributing",
        "fund_domicile": "IRL",
        "fund_currency": "USD",
        "inception_date": "2017-11-21",
        "geography": BOND_GEOGRAPHY,
        "sector": BOND_SECTOR,
    },
    "etf_hedged": {
        "ter": "0.0055",
        "fund_size": {"amount": "5213000000", "currency": "EUR"},
        "index_name": "MSCI World (EUR Hedged)",
        "fund_provider": "iShares",
        "replication": "physical_sampling",
        "distribution_policy": "accumulating",
        "fund_domicile": "IRL",
        "fund_currency": "EUR",
        "inception_date": "2010-09-30",
        "geography": HEDGED_GEOGRAPHY,
        "sector": HEDGED_SECTOR,
    },
    # An ETC: legal form etc_etn, no breakdown by country or sector (both lists empty on the page)
    "etc_gold": {
        "ter": "0.0012",
        "fund_size": {"amount": "33660000000", "currency": "EUR"},
        "index_name": "Gold",
        "fund_provider": "iShares",
        "replication": "physical_backed",
        "distribution_policy": "accumulating",
        "fund_domicile": "IRL",
        "fund_currency": "USD",
        "inception_date": "2011-04-08",
        "legal_form": "etc_etn",
    },
}


# =============================================================================
# The fake library and the plugin
# =============================================================================


class FakeLibrary:
    """``get_etf_overview`` answering only the ISINs a test gave it (an overview dict, or an exception to raise), with a
    log of its calls; ``load_overview`` answering the fake list. Any other ISIN fails the test: no page is ever fetched."""

    def __init__(self) -> None:
        self.pages: dict[str, Any] = {}
        self.calls: list[tuple[str, bool]] = []
        self.list_calls = 0

    def give(self, isin: str, answer: Any) -> str:
        self.pages[isin] = answer
        return isin

    def get_etf_overview(self, isin: str, include_gettex: bool = True, expand_allocations: bool = True) -> dict[str, Any]:
        self.calls.append((isin, include_gettex))
        if isin not in self.pages:
            pytest.fail(f"get_etf_overview called for {isin!r}, which this test never offered (a call the contract forbids, or a fetch from justetf.com)")
        answer = self.pages[isin]
        if isinstance(answer, BaseException):
            raise answer
        return copy.deepcopy(answer)

    def load_overview(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        self.list_calls += 1
        return _overview_list()

    @property
    def isins_called(self) -> list[str]:
        return [isin for isin, _ in self.calls]


@pytest.fixture
def je(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """The plugin module, with the library replaced by fakes that fail the test (no network ever)."""
    module = importlib.import_module(PLUGIN_MODULE)
    monkeypatch.setattr(module, "get_etf_overview", lambda *a, **k: pytest.fail(f"unpatched get_etf_overview{a}"), raising=True)
    monkeypatch.setattr(module, "load_overview", lambda *a, **k: pytest.fail("unpatched load_overview"), raising=True)
    yield module


@pytest.fixture
def library(je: ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeLibrary:
    fake = FakeLibrary()
    monkeypatch.setattr(je, "get_etf_overview", fake.get_etf_overview, raising=True)
    monkeypatch.setattr(je, "load_overview", fake.load_overview, raising=True)
    return fake


@pytest.fixture
def plugin(je: ModuleType, library: FakeLibrary):
    return je.JustETFEnricher()


def _isin(isin: str) -> EnricherBinding:
    return EnricherBinding("ISIN", isin)


def _read_one(plugin, binding: EnricherBinding) -> EnricherReadItem:
    items = list(plugin.read([binding]))
    assert len(items) == 1 and items[0].index == 0, f"one item for one binding: {items}"
    return items[0]


def _stored(values: dict[str, Any]) -> dict[str, Any]:
    """Every yielded voice in its stored form: a value the catalogue refuses fails the test here."""
    return {key: normalize_value(key, value) for key, value in values.items()}


def _synthetic(library: FakeLibrary, isin: str, **overrides: Any) -> EnricherBinding:
    """SWDA's recording with ``overrides``, offered under ``isin``."""
    overview = {**_recorded("swda"), "isin": isin, **overrides}
    library.give(isin, overview)
    return _isin(isin)


def _read_synthetic(plugin, library: FakeLibrary, isin: str, **overrides: Any) -> dict[str, Any]:
    item = _read_one(plugin, _synthetic(library, isin, **overrides))
    assert item.status == EnricherReadStatus.OK, f"a synthetic sheet with data is found: {item}"
    return _stored(dict(item.values))


def _log_lines_naming(events: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    return [event for event in events if text in repr(event)]


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations(je):
    cls = je.JustETFEnricher
    assert cls.code == CODE
    assert cls.name == "justETF"
    assert cls.terms is EnricherTerms.PRICE_SOURCE
    assert cls.accepted_identifier_types == ("ISIN",)
    own = tuple(field.key for field in cls.settings_fields if field.key not in CALL_LIMIT_KEYS)
    assert own == (), "no settings of its own"
    assert tuple(field.key for field in cls.settings_fields if field.key in CALL_LIMIT_KEYS) == CALL_LIMIT_KEYS, "it calls a source: the core gives it the five call limits (76 U4)"
    assert not getattr(cls, "test_only", False), "a real enricher, served outside test mode"
    instance = cls()
    assert instance.params_schema == [], "no extra parameters of a binding"
    assert instance.supports_search is True


def test_coverage_and_voices(je):
    """Changed by design in C1b (correction 2): it pinned the thirteen voices for every covered type; ``legal_form`` is
    now declared only where an ETC or ETN can sit, the other covered types declare the same twelve without it."""
    cls = je.JustETFEnricher
    assert set(cls.default_priority) == set(AssetType), "a degree for every AssetType"
    for asset_type in AssetType:
        expected = DEGREE if asset_type in COVERED else None
        assert cls.default_priority[asset_type] == expected, f"{asset_type.value}: degree {cls.default_priority[asset_type]!r}, expected {expected!r}"
    assert set(cls.voices) == set(COVERED), f"voices for the covered types only: {sorted(t.value for t in cls.voices)}"
    assert LEGAL_FORM_TYPES <= COVERED and COVERED - LEGAL_FORM_TYPES, "barrier: the legal-form types are covered, and some covered types are not among them"
    assert len(FUND_VOICES) == 12, f"barrier: twelve fund voices: {sorted(FUND_VOICES)}"
    for asset_type in sorted(COVERED):
        expected = VOICES if asset_type in LEGAL_FORM_TYPES else FUND_VOICES
        assert cls.voices[asset_type] == expected, f"{asset_type.value}: {sorted(cls.voices[asset_type])}, expected {sorted(expected)}"


def test_registered_and_served_in_production(je, monkeypatch):
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, "barrier: test mode on"
    assert EnricherRegistry.get_plugin(CODE) is je.JustETFEnricher
    failures = [failure for failure in EnricherRegistry.get_discovery_errors() if CODE in repr(failure)]
    assert failures == [], f"justetf failed to load: {failures}"
    with monkeypatch.context() as patch:
        patch.setenv(TEST_MODE_VARIABLE, "0")
        assert is_test_mode() is False, "barrier: production"
        assert CODE in EnricherRegistry.list_plugin_codes(), "not test-only: listed on a production instance"
        assert EnricherRegistry.get_plugin(CODE) is je.JustETFEnricher


def test_page_url(plugin):
    assert plugin.page_url(_isin("IE00B4L5Y983")) == _page("IE00B4L5Y983")


def test_the_pace_between_page_calls_is_positive(pace):
    """C5: the module's pace (the ``pace`` fixture checks it is a module-level Pacer) waits more than nothing."""
    assert pace.interval > 0


# =============================================================================
# 2. Mapping: the recordings
# =============================================================================


@pytest.mark.parametrize("recording", sorted(EXPECTED_STORED))
def test_read_recording_stored_forms(plugin, library, recording):
    overview = _recorded(recording)
    isin = library.give(overview["isin"], overview)

    item = _read_one(plugin, _isin(isin))

    assert item.status == EnricherReadStatus.OK, f"{recording}: {item}"
    assert item.source_date is None, "justETF gives no date of its data"
    assert all(value is not None for value in item.values.values()), f"a voice the page does not give is absent, never None: {item.values}"
    assert set(item.values) <= VOICES, f"only the declared voices: {sorted(set(item.values) - VOICES)}"
    stored = _stored(dict(item.values))
    expected = {**EXPECTED_STORED[recording], "description": overview["description"].strip()}
    assert stored == expected, f"{recording}: stored forms differ\n got      {stored}\n expected {expected}"
    assert library.calls == [(isin, False)], f"one page call, include_gettex=False: {library.calls}"


def test_swda_other_stays_other_not_a_country(plugin, library):
    """«Other» is kept as it is: the geo helper's fuzzy search would read it as GBR (and add 5.63 % to the UK)."""
    overview = _recorded("swda")
    stored = _stored(dict(_read_one(plugin, _isin(library.give(overview["isin"], overview))).values))
    assert stored["geography"]["Other"] == "0.0563"
    assert stored["geography"]["GBR"] == "0.0360"


def test_raw_geography_keys_are_iso3_or_other(plugin, library):
    overview = _recorded("vwce")
    values = _read_one(plugin, _isin(library.give(overview["isin"], overview))).values
    keys = set(values["geography"])
    assert all(key == "Other" or (len(key) == 3 and key.isupper()) for key in keys), f"raw keys ISO3 → weight: {sorted(keys)}"
    assert {"KOR", "TWN", "USA", "Other"} <= keys


def test_fields_not_read_change_nothing(plugin, library):
    """``currency_hedged``, ``top_holdings``, ``listings``: changing them changes no value. (Changed by design in C1b:
    ``holdings_date`` left this list, it is now read as the date of geography and sector.)"""
    base = _recorded("swda")
    first = library.give("IE00TESTNR001", {**base, "isin": "IE00TESTNR001"})
    second = library.give(
        "IE00TESTNR002",
        {**base, "isin": "IE00TESTNR002", "currency_hedged": not base["currency_hedged"], "top_holdings": [], "listings": []},
    )
    items = {item.index: item for item in plugin.read([_isin(first), _isin(second)])}
    assert _stored(dict(items[0].values)) == _stored(dict(items[1].values))
    assert items[0].source_date is None and items[1].source_date is None


# =============================================================================
# 2. Mapping: the date of geography and sector (correction C1b-1)
# =============================================================================

#: The voices the sheet's ``holdings_date`` dates: the breakdowns, nothing else.
DATED_VOICES = frozenset({"geography", "sector"})
_BOTH_DATED = {"geography": HOLDINGS_DATE, "sector": HOLDINGS_DATE}


def _source_dates(item: EnricherReadItem) -> dict[str, date]:
    """The item's per-voice dates. Before C1b the contract has no such field: the test fails here, naming it."""
    assert hasattr(item, "source_dates"), f"EnricherReadItem has no per-voice source_dates (correction C1b-1): {item}"
    return dict(item.source_dates)


@pytest.mark.parametrize(
    ("recording", "dates"),
    [("swda", _BOTH_DATED), ("vwce", _BOTH_DATED), ("etf_bond", _BOTH_DATED), ("etf_hedged", _BOTH_DATED), ("etc_gold", {})],
)
def test_recording_dates_geography_and_sector_only(plugin, library, recording, dates):
    """The four ETFs: geography and sector dated with the sheet's «30/09/2026», no other voice; the gold ETC, with no
    breakdown (and no holdings date), dates nothing. The item's own ``source_date`` stays None."""
    overview = _recorded(recording)
    if dates:
        assert overview["holdings_date"] == "30/09/2026", f"barrier: the recording's holdings date: {overview.get('holdings_date')!r}"
    else:
        assert not overview.get("countries") and not overview.get("sectors"), "barrier: the ETC has no breakdown"
    item = _read_one(plugin, _isin(library.give(overview["isin"], overview)))

    assert item.status == EnricherReadStatus.OK, item
    assert item.source_date is None, f"no date for the whole read: {item.source_date}"
    assert _source_dates(item) == dates, f"{recording}: per-voice dates {_source_dates(item)}, expected {dates}"
    assert set(dates) <= set(item.values), f"a dated voice is a voice the item gives: {sorted(item.values)}"


def test_swda_dates_reach_the_merged_voices(plugin, library):
    """SWDA's item through ``merge_voices``: geography and sector carry 30/09/2026, TER and every other voice none."""
    overview = _recorded("swda")
    isin = library.give(overview["isin"], overview)
    item = _read_one(plugin, _isin(isin))
    dates = _source_dates(item)
    assert dates == _BOTH_DATED, f"barrier: SWDA's per-voice dates: {dates}"
    outcome = ReadOutcome(owner=0, code=CODE, binding=_isin(isin), status=item.status, values=_stored(dict(item.values)), source_date=item.source_date, source_dates=dates)

    merged = merge_voices([CODE], [outcome])

    assert set(merged) == set(item.values), f"every voice merged: {sorted(merged)}"
    assert "ter" in merged and merged["ter"].source_date is None, f"TER has no date: {merged.get('ter')}"
    expected = {key: (HOLDINGS_DATE if key in DATED_VOICES else None) for key in item.values}
    assert {key: voice.source_date for key, voice in merged.items()} == expected


def test_holdings_date_is_read_day_first(plugin, library):
    """«05/03/2026» is the 5th of March: the recordings' «30/09» cannot tell day-first from month-first."""
    item = _read_one(plugin, _synthetic(library, "IE00TESTHD001", holdings_date="05/03/2026"))
    assert item.status == EnricherReadStatus.OK, item
    assert _source_dates(item) == {"geography": date(2026, 3, 5), "sector": date(2026, 3, 5)}


@pytest.mark.parametrize(
    "holdings_date",
    ["<missing>", None, "", "   ", "not a date", "31/02/2026", "09/30/2026"],
    ids=["missing", "none", "empty", "blank", "text", "no-such-day", "month-first"],
)
def test_no_readable_holdings_date_dates_nothing_and_changes_nothing(plugin, library, holdings_date):
    """A missing, empty or unreadable holdings date: no per-voice date, and every value as SWDA's own."""
    base = _recorded("swda")
    baseline = library.give("IE00TESTHD002", {**base, "isin": "IE00TESTHD002"})
    sheet = {**base, "isin": "IE00TESTHD003"}
    if holdings_date == "<missing>":
        sheet.pop("holdings_date")
    else:
        sheet["holdings_date"] = holdings_date
    undated = library.give("IE00TESTHD003", sheet)

    items = _by_index(list(plugin.read([_isin(baseline), _isin(undated)])), 2)

    assert items[1].status == EnricherReadStatus.OK, items[1]
    assert _source_dates(items[1]) == {}, f"{holdings_date!r} dates nothing: {_source_dates(items[1])}"
    assert items[1].source_date is None
    assert _stored(dict(items[1].values)) == _stored(dict(items[0].values)), "no value changes"


@pytest.mark.parametrize(
    ("countries", "sectors", "dates"),
    [
        (True, False, {"geography": HOLDINGS_DATE}),
        (False, True, {"sector": HOLDINGS_DATE}),
        (False, False, {}),
    ],
    ids=["countries-only", "sectors-only", "no-breakdown"],
)
def test_only_the_breakdowns_the_sheet_gives_are_dated(plugin, library, countries, sectors, dates):
    """SWDA with its holdings date kept and one or both breakdowns emptied: a voice the item does not give has no date
    (the gold ETC cannot show this: it has no holdings date either)."""
    base = _recorded("swda")
    overrides = {"countries": base["countries"] if countries else [], "sectors": base["sectors"] if sectors else []}
    item = _read_one(plugin, _synthetic(library, "IE00TESTHD004", **overrides))
    assert item.status == EnricherReadStatus.OK, item
    assert _source_dates(item) == dates


# =============================================================================
# 2. Mapping: synthetic sheets
# =============================================================================


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Physical(Full replication)", "physical_full"),
        ("Physical(Optimized sampling)", "physical_sampling"),
        ("Physical(Sampling)", "physical_sampling"),
        ("Physical(Physically backed)", "physical_backed"),
        ("Synthetic(Unfunded swap)", "synthetic_unfunded_swap"),
        ("Synthetic(Funded swap)", "synthetic_funded_swap"),
    ],
)
def test_replication_texts(plugin, library, text, code):
    stored = _read_synthetic(plugin, library, "IE00TESTRP001", replication=text)
    assert stored["replication"] == code


def test_unknown_replication_is_absent_and_logged_once(plugin, library):
    binding = _synthetic(library, "IE00TESTRP002", replication="Synthetic(Total return swap)")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK
    assert "replication" not in item.values
    assert len(_log_lines_naming(events, "Synthetic(Total return swap)")) == 1, f"one log line names the text: {events}"
    assert _stored(dict(item.values))["ter"] == "0.002", "the other voices are still read"


def test_missing_replication_is_absent(plugin, library):
    assert "replication" not in _read_synthetic(plugin, library, "IE00TESTRP003", replication=None)


@pytest.mark.parametrize(("text", "code"), [("Accumulating", "accumulating"), ("Distributing", "distributing"), ("Monthly", None), (None, None)])
def test_distribution_policy(plugin, library, text, code):
    stored = _read_synthetic(plugin, library, "IE00TESTDP001", distribution_policy=text)
    assert stored.get("distribution_policy") == code


@pytest.mark.parametrize(
    ("name", "code"),
    [("Ireland", "IRL"), ("Switzerland", "CHE"), ("Jersey", "JEY"), ("Luxembourg", "LUX"), ("Germany", "DEU"), ("France", "FRA"), ("Liechtenstein", "LIE"), ("Atlantis", None), (None, None)],
)
def test_fund_domicile(plugin, library, name, code):
    stored = _read_synthetic(plugin, library, "IE00TESTFD001", fund_domicile=name)
    assert stored.get("fund_domicile") == code


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        ("25 September 2009", "2009-09-25"),
        ("8 April 2011", "2011-04-08"),
        ("1 May 2020", "2020-05-01"),
        ("31 December 1999", "1999-12-31"),
        ("29 February 2024", "2024-02-29"),
        ("25 Septembre 2009", None),
        ("31 June 2020", None),
        ("unknown", None),
        (None, None),
    ],
)
def test_inception_date(plugin, library, text, iso):
    stored = _read_synthetic(plugin, library, "IE00TESTID001", inception_date=text)
    assert stored.get("inception_date") == iso


@pytest.mark.parametrize(("ter", "stored_ter"), [(0.0, "0"), (0.12, "0.0012"), (1.0, "0.01"), (0.07, "0.0007"), (None, None)])
def test_ter_is_a_fraction(plugin, library, ter, stored_ter):
    stored = _read_synthetic(plugin, library, "IE00TESTTR001", ter=ter)
    assert stored.get("ter") == stored_ter


@pytest.mark.parametrize(("size", "amount"), [(1234.5, "1234500000"), (0.5, "500000"), (None, None)])
def test_fund_size_is_millions_of_eur(plugin, library, size, amount):
    stored = _read_synthetic(plugin, library, "IE00TESTFS001", fund_size_eur=size)
    assert stored.get("fund_size") == (None if amount is None else {"amount": amount, "currency": "EUR"})


@pytest.mark.parametrize(("structure", "form"), [("ETC", "etc_etn"), ("ETN", "etc_etn"), ("ETF", None), ("ETP", None), (None, None)])
def test_legal_form(plugin, library, structure, form):
    """ETF → absent: the library does not read the «UCITS compliance» line, and an ETF is not necessarily UCITS."""
    stored = _read_synthetic(plugin, library, "IE00TESTLF001", legal_structure=structure)
    assert stored.get("legal_form") == form


@pytest.mark.parametrize("field", ["description", "index", "fund_provider", "fund_currency"])
@pytest.mark.parametrize("empty", [None, "", "   "])
def test_empty_texts_are_absent(plugin, library, field, empty):
    voice = {"description": "description", "index": "index_name", "fund_provider": "fund_provider", "fund_currency": "fund_currency"}[field]
    stored = _read_synthetic(plugin, library, "IE00TESTTX001", **{field: empty})
    assert voice not in stored


def test_untranslatable_country_weight_goes_to_other(plugin, library):
    """A country name the helper cannot translate is not dropped: its weight is added to «Other», one log line names it."""
    countries = [
        {"name": "United States", "percentage": 60.0},
        {"name": "Atlantis", "percentage": 0.5},
        {"name": "Switzerland", "percentage": 10.0},
        {"name": "Other", "percentage": 29.5},
    ]
    binding = _synthetic(library, "IE00TESTGE001", countries=countries)
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert len(_log_lines_naming(events, "Atlantis")) == 1, f"one log line names the untranslatable country: {events}"
    assert "Atlantis" not in item.values["geography"]
    assert _stored(dict(item.values))["geography"] == {"CHE": "0.1000", "Other": "0.3000", "USA": "0.6000"}


@pytest.mark.parametrize(
    ("countries", "geography"),
    [
        (
            [{"name": "United States", "percentage": 65.0}, {"name": "Supranational", "percentage": 5.0}, {"name": "Other", "percentage": 30.0}],
            {"Other": "0.3500", "USA": "0.6500"},
        ),
        # no «Other» on the page: the folding creates it
        ([{"name": "United States", "percentage": 90.0}, {"name": "Supranational", "percentage": 10.0}], {"Other": "0.1000", "USA": "0.9000"}),
    ],
    ids=["other-on-the-page", "no-other-on-the-page"],
)
def test_untranslatable_country_with_a_large_weight_is_folded_into_other(plugin, library, countries, geography):
    """5 % or 10 % untranslatable: dropped, the rest would sum outside the catalogue's ±1 % and the map be refused.
    Folded into «Other», the map sums to 1 and is stored."""
    binding = _synthetic(library, "IE00TESTGE002", countries=countries)
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK
    assert len(_log_lines_naming(events, "Supranational")) == 1, f"one log line names the untranslatable country: {events}"
    assert "Supranational" not in item.values["geography"]
    assert _stored(dict(item.values))["geography"] == geography


def test_empty_breakdowns_are_absent(plugin, library):
    stored = _read_synthetic(plugin, library, "IE00TESTGE003", countries=[], sectors=[])
    assert "geography" not in stored and "sector" not in stored


def test_sector_map_normalised_by_the_catalogue(plugin, library):
    """Finance translated by the plugin; Healthcare, a name the catalogue knows as an alias, passed on and stored as
    Health Care."""
    sectors = [{"name": "Technology", "percentage": 50.0}, {"name": "Finance", "percentage": 30.0}, {"name": "Healthcare", "percentage": 20.0}]
    stored = _read_synthetic(plugin, library, "IE00TESTSE001", sectors=sectors)
    assert stored["sector"] == {"Financials": "0.3000", "Health Care": "0.2000", "Technology": "0.5000"}


@pytest.mark.parametrize(
    ("name", "sector"),
    [
        ("Finance", "Financials"),
        ("Consumer Non-Cyclicals", "Consumer Staples"),
        ("Consumer Cyclicals", "Consumer Discretionary"),
        ("Consumer Services", "Consumer Discretionary"),
        ("Non-Energy Materials", "Basic Materials"),
        ("Business Services", "Industrials"),
        ("Sovereign", "Government Bonds"),
        ("Government Agencies", "Government Bonds"),
        ("Municipal", "Government Bonds"),
        ("Non-Corporate", "Other"),
        ("FINANCE", "Financials"),
        ("Space Mining", "Other"),
    ],
)
def test_sector_translation_table(plugin, library, name, sector):
    """The plugin's table, one justETF name at a time beside Technology: the standard sector it is stored under (any
    case); a name neither the table nor the catalogue knows ends in «Other»."""
    sectors = [{"name": name, "percentage": 40.0}, {"name": "Technology", "percentage": 60.0}]
    stored = _read_synthetic(plugin, library, "IE00TESTSE002", sectors=sectors)
    assert stored["sector"] == {sector: "0.4000", "Technology": "0.6000"}


def test_sector_table_holds_only_names_the_helper_does_not_know(je):
    """Correction C1b-3, a guard (green before C1b too): every key of ``_SECTORS`` is a justETF word the generic helper
    (``utils/asset/sector.py``) does not know, and every value a standard sector."""
    known = sorted(key for key in je._SECTORS if validate_sector(key))
    assert known == [], f"rows of the table the helper already knows: {known}"
    standard = set(FinancialSector.list_all_with_other())
    assert all(value in standard for value in je._SECTORS.values()), f"values outside the standard sectors: {je._SECTORS}"
    assert "non-corporate" not in je._SECTORS, "Non-Corporate is left to the catalogue («Other»)"


@pytest.mark.parametrize(("name", "stored"), [("Healthcare", "Health Care"), ("Corporate", "Corporate Bonds")])
def test_a_name_the_helper_knows_never_goes_through_the_table(je, plugin, library, monkeypatch, name, stored):
    """The helper is asked first: a name it knows is passed on as it is, even when a (decoy) row of ``_SECTORS`` would
    translate it; the catalogue then normalises it."""
    assert validate_sector(name), f"barrier: the helper knows {name!r}"
    monkeypatch.setitem(je._SECTORS, name.lower(), "Government Bonds")
    sectors = [{"name": name, "percentage": 40.0}, {"name": "Technology", "percentage": 60.0}]

    item = _read_one(plugin, _synthetic(library, "IE00TESTSE003", sectors=sectors))

    assert item.status == EnricherReadStatus.OK, item
    assert set(item.values["sector"]) == {name, "Technology"}, f"{name!r} passed on as it is, not through the table: {item.values['sector']}"
    assert _stored(dict(item.values))["sector"] == {stored: "0.4000", "Technology": "0.6000"}


# =============================================================================
# 3. Not found
# =============================================================================


@pytest.mark.parametrize("recording", ["enel", "mutual_fund"])
def test_empty_sheet_is_not_found(plugin, library, recording):
    overview = _recorded(recording)
    isin = library.give(overview["isin"], overview)
    assert _read_one(plugin, _isin(isin)).status == EnricherReadStatus.NOT_FOUND
    assert plugin.recognize(_isin(isin)).found is False


@pytest.mark.parametrize(("field", "value"), [("legal_structure", "ETC"), ("ter", 0.0), ("ter", 0.2), ("fund_provider", "iShares"), ("index", "Gold")])
def test_one_key_field_is_enough_to_be_found(plugin, library, field, value):
    """The empty sheet with one of the four fields set is a fund: ``ter == 0.0`` counts as present."""
    isin = "IE00TESTKF001"
    library.give(isin, {**_recorded("enel"), "isin": isin, "name": "Lab fund", field: value})
    recognition = plugin.recognize(_isin(isin))
    assert recognition.found is True, f"{field}={value!r}: {recognition}"
    assert _read_one(plugin, _isin(isin)).status == EnricherReadStatus.OK


# =============================================================================
# 4. recognize
# =============================================================================


def test_recognize_found(plugin, library):
    overview = _recorded("swda")
    isin = library.give(overview["isin"], overview)
    assert plugin.recognize(_isin(isin)) == EnricherRecognition(found=True, name=overview["name"], page_url=_page(isin), identifiers={})
    assert library.calls == [(isin, False)]


@pytest.mark.parametrize("binding", [EnricherBinding("TICKER", "SWDA"), EnricherBinding("LEI", "549300MLUDYVRQOOXS22")])
def test_recognize_non_isin_without_a_call(plugin, library, binding):
    assert plugin.recognize(binding).found is False
    assert library.calls == []


def test_recognize_rate_limited_raises(plugin, library):
    isin = library.give("IE00TESTRL001", RuntimeError("Failed to fetch ETF page for IE00TESTRL001: status 429"))
    with pytest.raises(Exception) as raised:
        plugin.recognize(_isin(isin))
    assert rate_limited_from_exception(raised.value, CODE) is not None, f"the core must read it as a 429: {raised.value!r}"


# =============================================================================
# 5. read
# =============================================================================


def _by_index(items: list[EnricherReadItem], count: int) -> dict[int, EnricherReadItem]:
    indices = [item.index for item in items]
    assert sorted(indices) == list(range(count)), f"exactly one item per binding: {indices}"
    return {item.index: item for item in items}


def test_read_mixed_list(plugin, library):
    swda, vwce, enel = _recorded("swda"), _recorded("vwce"), _recorded("enel")
    for overview in (swda, vwce, enel):
        library.give(overview["isin"], overview)
    bindings = [_isin(swda["isin"]), _isin(enel["isin"]), EnricherBinding("TICKER", "VWCE"), _isin(vwce["isin"])]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert [items[i].status for i in range(4)] == [EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.OK]
    assert _stored(dict(items[3].values))["index_name"] == "FTSE All-World"
    assert library.calls == [(swda["isin"], False), (enel["isin"], False), (vwce["isin"], False)], "no call for the ticker"


@pytest.mark.parametrize("error", [RuntimeError("Failed to fetch ETF page for IE00TESTER001: status 500"), ValueError("unexpected page layout")])
def test_read_library_error_is_an_error_item_and_the_next_is_read(plugin, library, error):
    swda = _recorded("swda")
    failing = library.give("IE00TESTER001", error)
    library.give(swda["isin"], swda)

    items = _by_index(list(plugin.read([_isin(failing), _isin(swda["isin"])])), 2)

    assert items[0].status == EnricherReadStatus.ERROR
    assert items[0].error_code and items[0].error_code != RATE_LIMITED, f"an error code, not RATE_LIMITED: {items[0]}"
    assert items[1].status == EnricherReadStatus.OK
    assert library.isins_called == [failing, swda["isin"]]


class _HTTPError(Exception):
    def __init__(self, response: object):
        super().__init__("HTTP error")
        self.response = response


@pytest.mark.parametrize(
    ("error", "retry_after"),
    [
        (RuntimeError("Failed to fetch ETF page for IE00TESTRL002: status 429"), "unknown"),
        (_HTTPError(SimpleNamespace(status_code=429, headers={"Retry-After": "120"})), 120.0),
        (AssetRateLimitedError("justETF: too many requests", retry_after=45.0), 45.0),
    ],
    ids=["library-text", "response-429", "asset-rate-limited"],
)
def test_read_rate_limited_defers_every_remaining_binding(plugin, library, error, retry_after):
    swda = _recorded("swda")
    library.give(swda["isin"], swda)
    refused = library.give("IE00TESTRL002", error)
    # never offered: a call for either fails the test
    bindings = [_isin(swda["isin"]), _isin(refused), _isin("IE00TESTRL003"), _isin("IE00TESTRL004")]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert items[0].status == EnricherReadStatus.OK
    for index in (1, 2, 3):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    if retry_after != "unknown":
        assert items[1].retry_after == retry_after
    assert library.isins_called == [swda["isin"], refused], "no call after the refusal"


def test_read_three_bindings_in_one_call(plugin, library):
    """Three pages read in one ``read``, with the instance's pause set to 0: one OK item each, one call each."""
    for name in ("swda", "vwce", "etf_bond"):
        overview = _recorded(name)
        library.give(overview["isin"], overview)
    bindings = [_isin(_recorded(name)["isin"]) for name in ("swda", "vwce", "etf_bond")]
    items = _by_index(list(plugin.read(bindings)), 3)
    assert all(item.status == EnricherReadStatus.OK for item in items.values())
    assert library.isins_called == [binding.identifier for binding in bindings]


# =============================================================================
# 6. search
# =============================================================================

SWDA_ISIN, VWCE_ISIN, GOLD_ISIN, SWAP_ISIN = "IE00B4L5Y983", "IE00BK5BQT80", "IE00B4ND3602", "LU0274208692"
NAMES = {
    SWDA_ISIN: "iShares Core MSCI World UCITS ETF USD (Acc)",
    VWCE_ISIN: "Vanguard FTSE All-World UCITS ETF (USD) Accumulating",
    GOLD_ISIN: "iShares Physical Gold ETC",
    SWAP_ISIN: "Xtrackers MSCI World Swap UCITS ETF 1C",
}


def _overview_list() -> pd.DataFrame:
    """A tiny ``load_overview()``: indexed by ISIN, one row per fund, a WKN missing."""
    frame = pd.DataFrame(
        {
            "name": [NAMES[SWDA_ISIN], NAMES[VWCE_ISIN], NAMES[GOLD_ISIN], NAMES[SWAP_ISIN]],
            "ticker": ["SWDA", "VWCE", "SGLN", "XDWD"],
            "wkn": ["A0RPWH", "A2PKXG", "A1KWPQ", None],
            "currency": ["USD", "USD", "USD", "USD"],
        },
        index=[SWDA_ISIN, VWCE_ISIN, GOLD_ISIN, SWAP_ISIN],
    )
    frame.index.name = "isin"
    return frame


@pytest.mark.parametrize(
    ("query", "isins"),
    [
        ("msci world", {SWDA_ISIN, SWAP_ISIN}),
        ("ISHARES", {SWDA_ISIN, GOLD_ISIN}),
        ("vwce", {VWCE_ISIN}),
        ("xdwd", {SWAP_ISIN}),
        ("a1kwpq", {GOLD_ISIN}),
        ("ie00bk5bqt80", {VWCE_ISIN}),
        ("zz-no-such-fund-zz", set()),
    ],
)
def test_search(plugin, library, query, isins):
    results = plugin.search(query)
    assert all(isinstance(result, EnricherSearchResult) for result in results)
    found = [result.binding.identifier for result in results]
    assert sorted(found) == sorted(isins), f"{query!r}: one result per fund: {found}"
    for result in results:
        isin = result.binding.identifier
        assert result == EnricherSearchResult(name=NAMES[isin], binding=EnricherBinding("ISIN", isin), asset_type=AssetType.ETF, page_url=_page(isin))
    assert library.calls == [], "search reads the list, never a page"


@pytest.mark.parametrize(
    ("error", "retry_after"),
    [
        (RuntimeError("Failed to fetch overview: status 429"), None),
        (_HTTPError(SimpleNamespace(status_code=429, headers={"Retry-After": "120"})), 120.0),
        (AssetRateLimitedError("justETF: too many requests", retry_after=45.0), 45.0),
    ],
    ids=["library-text", "response-429", "asset-rate-limited"],
)
def test_search_refusal_is_enricher_rate_limited(je, plugin, monkeypatch, error, retry_after):
    """ENR-3b: a refusal while the list loads is never an empty result."""
    assert rate_limited_from_exception(error, CODE) is not None, "barrier: the core reads it as a refusal"

    def refused(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise error

    monkeypatch.setattr(je, "load_overview", refused, raising=True)
    with pytest.raises(EnricherRateLimited) as raised:
        plugin.search("msci world")
    assert raised.value.retry_after == retry_after
    assert raised.value.__cause__ is error


def test_search_another_failure_is_not_a_refusal(je, plugin, monkeypatch):
    failure = ValueError("unexpected table layout")
    assert rate_limited_from_exception(failure, CODE) is None, "barrier: not a refusal"

    def broken(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise failure

    monkeypatch.setattr(je, "load_overview", broken, raising=True)
    with pytest.raises(ValueError) as raised:
        plugin.search("msci world")
    assert raised.value is failure and not isinstance(raised.value, EnricherRateLimited)


# =============================================================================
# C5: one pace for every call of the plugin, whatever read it comes from
# =============================================================================


class FakePace:
    """The module's ``_PACER`` replaced by one on a fake clock that only moves when it sleeps: no test ever waits, and
    the waits are recorded. ``interval`` is the plugin's own."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.now = 1000.0
        self.slept: list[float] = []
        self._lock = threading.Lock()

    def clock(self) -> float:
        with self._lock:
            return self.now

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.slept.append(seconds)
            self.now += seconds


@pytest.fixture(autouse=True)
def pace(monkeypatch: pytest.MonkeyPatch) -> FakePace:
    """Every test of this file runs on the fake pace: the module must hold its ``_PACER`` (C5)."""
    module = importlib.import_module(PLUGIN_MODULE)
    real = module._PACER
    assert isinstance(real, Pacer) and real.interval_seconds > 0, "the plugin paces its calls with a module-level Pacer"
    fake = FakePace(real.interval_seconds)
    monkeypatch.setattr(module, "_PACER", Pacer(real.interval_seconds, clock=fake.clock, sleep=fake.sleep), raising=True)
    return fake


def test_two_reads_share_one_pace(je, library, pace):
    """Two reads, from two instances as the registry builds them («Aggiorna» and the weekly read): the second page call
    waits the plugin's interval, though it opens its own read."""
    first, second = je.JustETFEnricher(), je.JustETFEnricher()
    bindings = [_synthetic(library, "IE00TESTPACE01"), _synthetic(library, "IE00TESTPACE02")]
    assert list(first.read([bindings[0]]))[0].status == EnricherReadStatus.OK
    assert pace.slept == [], "the first call does not wait"
    assert list(second.read([bindings[1]]))[0].status == EnricherReadStatus.OK
    assert pace.slept == [pace.interval], f"the second read waited the interval: {pace.slept}"


def test_recognize_is_paced_with_the_reads(je, library, pace, plugin):
    binding = _synthetic(library, "IE00TESTPACE03")
    plugin.recognize(binding)
    list(plugin.read([binding]))
    assert pace.slept == [pace.interval], f"recognize and read share the pace: {pace.slept}"


def test_concurrent_reads_are_spaced(je, library, pace):
    """Two reads at once, each in its own worker thread: their page calls are at least the interval apart."""
    bindings = [_synthetic(library, "IE00TESTPACE04"), _synthetic(library, "IE00TESTPACE05")]
    start = threading.Barrier(2)
    results: list[Any] = []

    def worker(binding: EnricherBinding) -> None:
        start.wait()
        results.extend(je.JustETFEnricher().read([binding]))

    threads = [threading.Thread(target=worker, args=(binding,)) for binding in bindings]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == 2 and all(item.status == EnricherReadStatus.OK for item in results)
    assert sum(pace.slept) >= pace.interval - 1e-9, f"one of the two waited the interval: {pace.slept}"
