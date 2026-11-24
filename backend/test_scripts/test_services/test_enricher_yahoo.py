"""
The Yahoo Finance enricher (plan 68, lot C3): ``enricher_providers/yahoo_finance/plugin.py``, class
``YahooFinanceEnricher``.

What it promises, pinned here with no network:

1. **Declarations**: ``code`` ``yfinance`` (the price provider's code, plan §3.4), ``name`` ``Yahoo Finance``,
   ``terms`` ``PRICE_SOURCE``, ``TICKER`` only (B4's cascade asks the strongest identifier first: an ISIN would let Yahoo
   pick the listing itself), no ``params_schema``, no search, not test-only. ``STOCK`` at degree 10 (the main source of a
   share), the ETF family (``ETF`` and every ``ETF_*``) and ``FUND`` at degree 20 (after justETF and Borsa Italiana),
   every other type ``None`` (``CRYPTO``, ``COMMODITY``, ``BOND`` among them). Voices: a share ``sector``, ``industry``,
   ``issuer_country``, ``market_cap``, ``description``; a fund ``ter``, ``fund_provider``, ``inception_date``,
   ``sector``, ``description``. ``page_url`` ``https://finance.yahoo.com/quote/<ticker>``. C5: one module-level ``Pacer``
   spaces every call to Yahoo (``.info``, ``funds_data``), whatever read or «Riconosci» it comes from (the tests replace
   it with one on a fake clock: no test waits). ``test_cases``: a
   ``STOCK`` and an ETF, both ``TICKER``. ``yfinance`` imported at module level as ``yf``; nothing imported from the price
   plugin of the same name.

2. **Mapping**, chosen by ``info["quoteType"]``, never by the asset type (Yahoo files an ETC as ``EQUITY``); every
   yielded value passed through the real catalogue (``normalize_value``) and compared in its **stored** form:

   - ``EQUITY``: ``sector`` one sector at 100 % when ``utils/asset/sector.py`` knows the name (Yahoo's eleven names),
     absent otherwise; ``industry`` as text; ``issuer_country`` through ``normalize_country_to_iso3``, absent with one log
     line when it cannot; ``market_cap`` ``{amount, currency}`` only when ``currency`` is an upper-case ISO 4217 code (a
     minor unit, ``GBp`` / ``ILA`` / ``ZAc``, is absent with one log line: the amount would be 100× off);
     ``description`` the ``longBusinessSummary``, never the name;
   - ``ETF`` / ``MUTUALFUND``: ``ter`` the ``netExpenseRatio`` PERCENT as a fraction; ``fund_provider`` the
     ``fundFamily``; ``inception_date`` the ``fundInceptionDate`` epoch as a **UTC** date; ``description`` when given;
     ``sector`` from ``funds_data.sector_weightings`` (fractions) only when ``sector`` is asked, Yahoo's keys through the
     helper first then the plugin's table, an unknown key folded into «Other» with one log line, zero or non-numeric
     weights dropped, an empty map absent. A failing ``funds_data`` (any error but a refusal) leaves the ``info`` voices;
     ``funds_data`` is never touched for a share, nor when ``sector`` is not asked;
   - any other ``quoteType`` (``CRYPTOCURRENCY``…): OK with no values;
   - never read: prices, P/E, the ISIN Yahoo gives for a ticker (wrong for Enel and ASML in the research), ``totalAssets``,
     ``legalType``, holdings. The fake ticker fails on any attribute but ``info`` and ``funds_data``, the fake fund data
     on any but ``sector_weightings``.
   - cross-check with justETF on the funds both recorded: ``ter`` equal for ``swda``, ``etf_bond``, ``etf_hedged``;
     ``inception_date`` equal for ``swda`` and ``etf_hedged``. For ``etf_bond`` (AGGG.L) the two sources disagree
     (Yahoo 2024-05-10, justETF 2017-11-21, the coordinator's correction): Yahoo's own date is pinned as it is.

3. **Not found**: an ``info`` empty or without ``quoteType`` (synthetic: no recording has an unknown ticker); the
   ``ValueError`` «Invalid ISIN number» (the recorded answer to a bond's ISIN, raised by ``yf.Ticker`` itself); the
   nameless ``EQUITY`` row (``btp_italia``'s Stuttgart listing).

4. **recognize**: non-TICKER → not found with no call; found → ``EnricherRecognition(found=True, name=longName or
   shortName, page_url, identifiers={})``, never an ISIN from Yahoo, never ``funds_data``; a refusal raises, as an
   exception ``rate_limited_from_exception`` recognises.

5. **read**: one item per binding with its index; non-TICKER ``NOT_FOUND`` with no call; yfinance's real
   ``YFRateLimitError`` → ``RATE_LIMITED`` for that binding and every later one, without a call (also when it comes from
   ``funds_data``); another error → ``SOURCE_ERROR``, isolated.

No network, by construction: the plugin module is imported in a fixture, which replaces ``yf`` on it (``raising=True``:
the name must be imported at module level) with a fake module whose ``Ticker`` answers only the symbols a test offered
and fails the test (``pytest.fail``, a ``BaseException`` no plugin ``except Exception`` swallows) on any other symbol,
any other module attribute but ``exceptions`` (yfinance's real one) and any other attribute of a ticker or of its fund
data. The real ``yfinance.Ticker``, ``Tickers``, ``Search`` and ``download`` fail the same way, whatever path the plugin
takes. The call log records the fetches of ``info`` (a second read on the same ``Ticker`` object is served from memory, as yfinance
does, and not logged), and the reads of ``funds_data`` and ``sector_weightings``, never the construction of a ``Ticker``;
each ticker's ``info`` is pinned as fetched once per ``read`` or ``recognize``; ``constructed`` lists the symbols asked, for «without
a call». Assumed: the plugin keeps no cache of its own between reads (the read cache is the core's).

Red before C3: the plugin module does not exist; every test fails on its own at the fixture's import
(``ModuleNotFoundError``), nothing at collection.

PURE: no database, no server, no network.
"""

from __future__ import annotations

import ast
import copy
import importlib
import importlib.util
import json
import threading
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yfinance
import yfinance.exceptions
from structlog.testing import capture_logs

from backend.app.config import is_test_mode
from backend.app.db.models import AssetType
from backend.app.services.assets.base import rate_limited_from_exception
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
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.call_limits import CALL_LIMIT_KEYS
from backend.app.utils.asset.sector import validate_sector
from backend.app.utils.runtime.pacing import Pacer

PLUGIN_MODULE = "backend.app.services.enricher_providers.yahoo_finance.plugin"
CODE = "yfinance"
TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
FIXTURES = Path(__file__).parent / "fixtures" / "yahoo_enricher"
JUSTETF_FIXTURES = Path(__file__).parent / "fixtures" / "justetf"
SOURCE_ERROR = "SOURCE_ERROR"

SHARE_VOICES = frozenset({"sector", "industry", "issuer_country", "market_cap", "description"})
FUND_VOICES = frozenset({"ter", "fund_provider", "inception_date", "sector", "description"})
ETF_FAMILY = frozenset({asset_type for asset_type in AssetType if asset_type == AssetType.ETF or asset_type.value.startswith("ETF_")})
FUND_TYPES = ETF_FAMILY | {AssetType.FUND}
SHARE_DEGREE = 10
FUND_DEGREE = 20

#: The log line the sector helper writes by itself for every name it does not know: not the plugin's.
HELPER_EVENTS = frozenset({"Sector not in standard classification"})

#: The recorded refusal text of yfinance's error, for the barrier.
RATE_LIMIT_ERROR = yfinance.exceptions.YFRateLimitError


def _page(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


def _recording(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _call(name: str, prefix: str) -> tuple[str, Any] | None:
    """``(symbol, response)`` of the recording's one ``<prefix>:<symbol>`` call, None when it has none."""
    calls = [(key.split(":", 1)[1], call["response"]) for key, call in _recording(name)["calls"].items() if key.startswith(f"{prefix}:")]
    assert len(calls) <= 1, f"barrier: one {prefix} call in {name}: {calls}"
    return calls[0] if calls else None


def _info(name: str) -> tuple[str, dict[str, Any]]:
    """``(ticker, info)`` as ``yf.Ticker(ticker).info`` returned it for the recording."""
    found = _call(name, "info_ticker")
    assert found is not None, f"barrier: {name} has an info_ticker call"
    return found


def _sector_weightings(name: str) -> dict[str, Any] | None:
    found = _call(name, "funds_data")
    return None if found is None else found[1]["sector_weightings"]


# =============================================================================
# Expected stored forms (from the real catalogue, written out: never recomputed with the plugin's own logic)
# =============================================================================

#: Yahoo's sector keys of a fund translated by hand (realestate → Real Estate, consumer_cyclical → Consumer
#: Discretionary, …) and stored through the catalogue, which renormalises to four places.
SWDA_SECTOR = {
    "Basic Materials": "0.0300",
    "Consumer Discretionary": "0.0861",
    "Consumer Staples": "0.0527",
    "Energy": "0.0461",
    "Financials": "0.1600",
    "Health Care": "0.1019",
    "Industrials": "0.1039",
    "Real Estate": "0.0161",
    "Technology": "0.3060",
    "Telecommunication": "0.0729",
    "Utilities": "0.0243",
}
VWCE_SECTOR = {
    "Basic Materials": "0.0353",
    "Consumer Discretionary": "0.0831",
    "Consumer Staples": "0.0443",
    "Energy": "0.0395",
    "Financials": "0.1601",
    "Health Care": "0.0829",
    "Industrials": "0.1014",
    "Real Estate": "0.0166",
    "Technology": "0.3347",
    "Telecommunication": "0.0796",
    "Utilities": "0.0225",
}
# The recording sums to 1.0001: the catalogue's renormalisation takes the remainder from the smallest weight
HEDGED_SECTOR = {
    "Basic Materials": "0.0301",
    "Consumer Discretionary": "0.0860",
    "Consumer Staples": "0.0528",
    "Energy": "0.0460",
    "Financials": "0.1597",
    "Health Care": "0.1018",
    "Industrials": "0.1039",
    "Real Estate": "0.0162",
    "Technology": "0.3062",
    "Telecommunication": "0.0727",
    "Utilities": "0.0246",
}

#: BlackRock's family as Yahoo names it on the three iShares funds.
BLACKROCK = "BlackRock Asset Management Ireland - ETF"

#: Per recording: every voice in stored form but ``description`` (compared with the recording's own text when it has
#: one). ``etc_gold`` is IGLN.L, an ETC Yahoo files as EQUITY with a name and nothing else: found, no values.
EXPECTED_STORED: dict[str, dict[str, Any]] = {
    "enel": {
        "sector": {"Utilities": "1.0000"},
        "industry": "Utilities - Diversified",
        "issuer_country": "ITA",
        "market_cap": {"amount": "98033917952", "currency": "EUR"},
    },
    "apple": {
        "sector": {"Technology": "1.0000"},
        "industry": "Consumer Electronics",
        "issuer_country": "USA",
        "market_cap": {"amount": "5054147854336", "currency": "USD"},
    },
    "asml": {
        "sector": {"Technology": "1.0000"},
        "industry": "Semiconductor Equipment & Materials",
        "issuer_country": "NLD",
        "market_cap": {"amount": "521855598592", "currency": "EUR"},
    },
    "swda": {"ter": "0.002", "fund_provider": BLACKROCK, "inception_date": "2009-09-25", "sector": SWDA_SECTOR},
    # VWRA.L: no netExpenseRatio in the recording, so no TER
    "vwce": {"fund_provider": "Vanguard Group (Ireland) Limited", "inception_date": "2019-07-23", "sector": VWCE_SECTOR},
    # AGGG.L: an empty sector map, so no sector; Yahoo's inception date (the coordinator's correction: not justETF's)
    "etf_bond": {"ter": "0.001", "fund_provider": BLACKROCK, "inception_date": "2024-05-10"},
    "etf_hedged": {"ter": "0.0055", "fund_provider": BLACKROCK, "inception_date": "2010-09-30", "sector": HEDGED_SECTOR},
    # 0P0001OS3T.F (Anima Dinamix, Frankfurt): no family, no expense ratio, an empty sector map; 1647216000 is UTC midnight
    "mutual_fund": {"inception_date": "2022-03-14"},
    "etc_gold": {},
}
SHARE_RECORDINGS = ("enel", "apple", "asml", "etc_gold")
FUND_RECORDINGS = ("swda", "vwce", "etf_bond", "etf_hedged", "mutual_fund")


# =============================================================================
# The fake yfinance and the plugin
# =============================================================================


def _dunder(name: str) -> None:
    """Python's own probes (``__deepcopy__``, ``__wrapped__``…) get a plain AttributeError, never a failed test."""
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)


class _RaisedAtProperty:
    """A ``funds_data`` answer that raises when the ``funds_data`` property is read, not at ``sector_weightings``."""

    def __init__(self, error: BaseException) -> None:
        self.error = error


class FakeFundsData:
    """``ticker.funds_data``: only ``sector_weightings`` may be read."""

    def __init__(self, yahoo: FakeYahoo, symbol: str, answer: Any) -> None:
        self._yahoo, self._symbol, self._answer = yahoo, symbol, answer

    @property
    def sector_weightings(self) -> dict[str, Any]:
        self._yahoo.calls.append((self._symbol, "sector_weightings"))
        if isinstance(self._answer, BaseException):
            raise self._answer
        return copy.deepcopy(self._answer)

    def __getattr__(self, name: str) -> Any:
        _dunder(name)
        pytest.fail(f"funds_data({self._symbol}).{name} read: the enricher reads sector_weightings only (no holdings, no fund size)")


class FakeTicker:
    """``yf.Ticker(symbol)``: only ``info`` and ``funds_data`` may be read; anything else (``isin``, ``history``,
    ``fast_info``…) fails the test."""

    def __init__(self, yahoo: FakeYahoo, symbol: str) -> None:
        self._yahoo, self._symbol, self._fetched = yahoo, symbol, False

    @property
    def info(self) -> dict[str, Any]:
        # yfinance fetches info once per Ticker object and serves it from memory after: the log counts fetches
        if not self._fetched:
            self._yahoo.calls.append((self._symbol, "info"))
        answer = self._yahoo.infos[self._symbol]
        if isinstance(answer, BaseException):
            raise answer
        self._fetched = True
        return copy.deepcopy(answer)

    @property
    def funds_data(self) -> FakeFundsData:
        self._yahoo.calls.append((self._symbol, "funds_data"))
        if self._symbol not in self._yahoo.funds:
            pytest.fail(f"Ticker({self._symbol}).funds_data read, which this test never offered (a share, or sector not asked)")
        answer = self._yahoo.funds[self._symbol]
        if isinstance(answer, _RaisedAtProperty):
            raise answer.error
        return FakeFundsData(self._yahoo, self._symbol, answer)

    def __getattr__(self, name: str) -> Any:
        _dunder(name)
        pytest.fail(f"Ticker({self._symbol}).{name} read: the enricher reads info and funds_data only")


class FakeYahoo:
    """The fake ``yf`` module: ``Ticker`` for the symbols a test offered, yfinance's real ``exceptions``; any other
    symbol or attribute fails the test."""

    exceptions = yfinance.exceptions

    def __init__(self) -> None:
        self.infos: dict[str, Any] = {}
        self.funds: dict[str, Any] = {}
        self.at_construction: dict[str, BaseException] = {}
        self.calls: list[tuple[str, str]] = []
        self.constructed: list[str] = []

    def give(self, symbol: str, info: Any, funds: Any = None) -> EnricherBinding:
        """Offer ``symbol``: its ``info`` (a dict or an exception) and, when not None, its sector weightings (a dict, an
        exception raised at ``sector_weightings``, or a ``_RaisedAtProperty``)."""
        self.infos[symbol] = info
        if funds is not None:
            self.funds[symbol] = funds
        return _ticker(symbol)

    def refuse_construction(self, symbol: str, error: BaseException) -> EnricherBinding:
        """``yf.Ticker(symbol)`` itself raises, as yfinance does for an ISIN it cannot resolve."""
        self.at_construction[symbol] = error
        return _ticker(symbol)

    def Ticker(self, symbol: str, *args: Any, **kwargs: Any) -> FakeTicker:  # noqa: N802 — yfinance's own name
        self.constructed.append(symbol)
        if symbol in self.at_construction:
            raise self.at_construction[symbol]
        if symbol not in self.infos:
            pytest.fail(f"yf.Ticker({symbol!r}): a symbol this test never offered (a call the contract forbids, or a fetch from Yahoo)")
        return FakeTicker(self, symbol)

    def __getattr__(self, name: str) -> Any:
        _dunder(name)
        pytest.fail(f"yf.{name} used: the enricher uses yf.Ticker and yf.Search only (no download)")

    def reads(self, symbol: str) -> list[str]:
        return [what for called, what in self.calls if called == symbol]

    @property
    def symbols_read(self) -> list[str]:
        """The symbols whose ``info`` was read, in order."""
        return [symbol for symbol, what in self.calls if what == "info"]


class _Forbidden:
    """A stand-in that fails the test whatever is done with it."""

    def __init__(self, label: str) -> None:
        self._label = label

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pytest.fail(f"{self._label}{args} called: no request ever reaches Yahoo in this suite")

    def __getattr__(self, name: str) -> Any:
        _dunder(name)
        pytest.fail(f"{self._label}.{name} used: no request ever reaches Yahoo in this suite")


@pytest.fixture
def yh(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """The plugin module, with ``yf`` replaced by a stub that fails the test, and yfinance's own entry points too."""
    module = importlib.import_module(PLUGIN_MODULE)
    for name in ("Ticker", "Tickers", "Search", "download"):
        monkeypatch.setattr(yfinance, name, _Forbidden(f"yfinance.{name}"), raising=True)
    monkeypatch.setattr(module, "yf", _Forbidden("unpatched yf"), raising=True)
    yield module


@pytest.fixture
def yahoo(yh: ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeYahoo:
    fake = FakeYahoo()
    monkeypatch.setattr(yh, "yf", fake, raising=True)
    return fake


@pytest.fixture
def plugin(yh: ModuleType, yahoo: FakeYahoo):
    return yh.YahooFinanceEnricher()


def _ticker(symbol: str) -> EnricherBinding:
    return EnricherBinding("TICKER", symbol)


def _offer(yahoo: FakeYahoo, name: str) -> tuple[EnricherBinding, dict[str, Any]]:
    """Offer a recording under its own ticker, with its sector weightings when it has a ``funds_data`` call."""
    symbol, info = _info(name)
    return yahoo.give(symbol, info, _sector_weightings(name)), info


def _read_one(plugin, binding: EnricherBinding, keys: Any = None) -> EnricherReadItem:
    items = list(plugin.read([binding]) if keys is None else plugin.read([binding], keys))
    assert len(items) == 1 and items[0].index == 0, f"one item for one binding: {items}"
    return items[0]


def _by_index(items: list[EnricherReadItem], count: int) -> dict[int, EnricherReadItem]:
    indices = [item.index for item in items]
    assert sorted(indices) == list(range(count)), f"exactly one item per binding: {indices}"
    return {item.index: item for item in items}


def _stored(values: Any) -> dict[str, Any]:
    """Every yielded voice in its stored form: a value the catalogue refuses (a float among them) fails the test here."""
    return {key: normalize_value(key, value) for key, value in dict(values).items()}


def _share_info(**overrides: Any) -> dict[str, Any]:
    """Apple's recorded ``info`` with ``overrides`` (a value ``None`` removes the key, as Yahoo leaves it out)."""
    info = {**_info("apple")[1], **overrides}
    return {key: value for key, value in info.items() if value is not None}


def _fund_info(**overrides: Any) -> dict[str, Any]:
    """IWDA.L's recorded ``info`` with ``overrides`` (a value ``None`` removes the key)."""
    info = {**_info("swda")[1], **overrides}
    return {key: value for key, value in info.items() if value is not None}


def _read_share(plugin, yahoo: FakeYahoo, symbol: str, **overrides: Any) -> EnricherReadItem:
    item = _read_one(plugin, yahoo.give(symbol, _share_info(**overrides)))
    assert item.status == EnricherReadStatus.OK, f"a share with data is found: {item}"
    return item


def _read_fund(plugin, yahoo: FakeYahoo, symbol: str, sectors: Any = None, **overrides: Any) -> EnricherReadItem:
    weights = _sector_weightings("swda") if sectors is None else sectors
    item = _read_one(plugin, yahoo.give(symbol, _fund_info(**overrides), weights))
    assert item.status == EnricherReadStatus.OK, f"a fund with data is found: {item}"
    return item


def _plugin_lines_naming(events: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """The log lines naming ``text``, the sector helper's own warning left out (it is not the plugin's line)."""
    return [event for event in events if text in repr(event) and event.get("event") not in HELPER_EVENTS]


# =============================================================================
# 0. The recordings themselves (green before C3: they check the fixtures, not the plugin)
# =============================================================================

RECORDINGS = ("enel", "apple", "asml", "swda", "vwce", "etf_bond", "etf_hedged", "etc_gold", "mutual_fund", "btp_italia", "btp_ord")


@pytest.mark.parametrize("name", RECORDINGS)
def test_recording_envelope_in_english(name):
    """A guard on the fixtures, green before C3: the English envelope of C1b and the English call names."""
    data = _recording(name)
    assert set(data) == {"source", "asset", "version", "recorded_at", "calls"}, sorted(data)
    assert (data["source"], data["asset"], data["version"]) == ("yahoo", name, "yfinance 1.7.0")
    for key, call in data["calls"].items():
        assert set(call) == {"seconds", "error", "response"}, f"{name} {key}: {sorted(call)}"
        assert key.split(":", 1)[0] in {"info_from_isin", "search_isin", "info_ticker", "funds_data", "isin_of_ticker"}, f"{name}: {key}"


def test_expected_tables_are_stored_forms():
    """A guard, green before C3: every expected value is its own stored form (the catalogue is idempotent on it)."""
    for name, voices in EXPECTED_STORED.items():
        assert _stored(voices) == voices, name


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations(yh):
    cls = yh.YahooFinanceEnricher
    assert cls.code == CODE, "the price provider's code (plan §3.4)"
    assert cls.name == "Yahoo Finance"
    assert cls.terms is EnricherTerms.PRICE_SOURCE
    assert cls.accepted_identifier_types == ("TICKER",), "the ticker only: an ISIN would let Yahoo pick the listing"
    own = tuple(field.key for field in cls.settings_fields if field.key not in CALL_LIMIT_KEYS)
    assert own == (), "no settings of its own"
    assert tuple(field.key for field in cls.settings_fields if field.key in CALL_LIMIT_KEYS) == CALL_LIMIT_KEYS, "it calls a source: the core gives it the five call limits (76 U4)"
    assert not getattr(cls, "test_only", False), "a real enricher, served outside test mode"
    instance = cls()
    assert instance.params_schema == [], "no extra parameters of a binding"
    assert instance.supports_search is True, "it searches by yf.Search (ENR-3b)"


def test_coverage_and_voices(yh):
    cls = yh.YahooFinanceEnricher
    assert set(cls.default_priority) == set(AssetType), "a degree for every AssetType"
    for asset_type in AssetType:
        expected = SHARE_DEGREE if asset_type == AssetType.STOCK else FUND_DEGREE if asset_type in FUND_TYPES else None
        assert cls.default_priority[asset_type] == expected, f"{asset_type.value}: degree {cls.default_priority[asset_type]!r}, expected {expected!r}"
    for uncovered in (AssetType.CRYPTO, AssetType.COMMODITY, AssetType.BOND):
        assert cls.default_priority[uncovered] is None, f"{uncovered.value} uncovered (the recognize API test without codes runs on CRYPTO)"
    assert set(cls.voices) == FUND_TYPES | {AssetType.STOCK}, f"voices for the covered types only: {sorted(t.value for t in cls.voices)}"
    assert cls.voices[AssetType.STOCK] == SHARE_VOICES, sorted(cls.voices[AssetType.STOCK])
    for asset_type in sorted(FUND_TYPES):
        assert cls.voices[asset_type] == FUND_VOICES, f"{asset_type.value}: {sorted(cls.voices[asset_type])}"


def test_registered_and_served_in_production(yh, monkeypatch):
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, "barrier: test mode on"
    assert EnricherRegistry.get_plugin(CODE) is yh.YahooFinanceEnricher
    failures = [failure for failure in EnricherRegistry.get_discovery_errors() if CODE in repr(failure) or "yahoo" in repr(failure).lower()]
    assert failures == [], f"yahoo_finance failed to load: {failures}"
    with monkeypatch.context() as patch:
        patch.setenv(TEST_MODE_VARIABLE, "0")
        assert is_test_mode() is False, "barrier: production"
        assert CODE in EnricherRegistry.list_plugin_codes(), "not test-only: listed on a production instance"
        assert EnricherRegistry.get_plugin(CODE) is yh.YahooFinanceEnricher


def test_yfinance_is_imported_at_module_level_as_yf():
    """The tests replace ``yf`` on the module: a plugin importing yfinance another way would escape the fake."""
    module = importlib.import_module(PLUGIN_MODULE)
    assert module.yf is yfinance, f"the module's yf is yfinance itself: {getattr(module, 'yf', None)!r}"


def _plugin_imports() -> list[str]:
    tree = ast.parse(Path(importlib.util.find_spec(PLUGIN_MODULE).origin).read_text(encoding="utf-8"))
    imported = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    return imported + [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]


def test_no_import_from_the_price_plugin(yh):
    """The two Yahoo plugins share nothing (plan §C, rule 1): no import from ``asset_source_providers``."""
    imported = _plugin_imports()
    assert not [name for name in imported if "asset_source_providers" in name], f"imports from the price plugin: {imported}"


@pytest.mark.parametrize("symbol", ["AAPL", "IWDA.L", "ENEL.MI", "0P0001OS3T.F"])
def test_page_url(plugin, yahoo, symbol):
    assert plugin.page_url(_ticker(symbol)) == _page(symbol)
    assert yahoo.constructed == [], "the page needs no call"


def test_the_pace_between_calls_is_positive(pace):
    """C5: the module's pace (the ``pace`` fixture checks it is a module-level Pacer) waits more than nothing."""
    assert pace.interval > 0


def test_test_cases_for_the_external_suite(plugin):
    cases = plugin.test_cases
    assert cases, "test_cases for the external suite"
    types = set()
    for case in cases:
        assert case["binding"]["identifier_type"] == "TICKER", f"a ticker binding: {case}"
        asset_type = AssetType(case["asset_type"])
        assert plugin.covers(asset_type) and plugin.voices.get(asset_type), f"a case of a covered type with voices: {case}"
        types.add(asset_type)
    assert AssetType.STOCK in types, f"at least one share: {cases}"
    assert types & ETF_FAMILY, f"at least one ETF: {cases}"


# =============================================================================
# 2. Mapping: the recordings
# =============================================================================


@pytest.mark.parametrize("recording", sorted(EXPECTED_STORED))
def test_read_recording_stored_forms(plugin, yahoo, recording):
    binding, info = _offer(yahoo, recording)

    item = _read_one(plugin, binding)

    assert item.status == EnricherReadStatus.OK, f"{recording}: {item}"
    assert all(value is not None for value in item.values.values()), f"a voice Yahoo does not give is absent, never None: {item.values}"
    declared = SHARE_VOICES if info["quoteType"] == "EQUITY" else FUND_VOICES
    assert set(item.values) <= declared, f"only the voices of its quoteType: {sorted(set(item.values) - declared)}"
    stored = _stored(item.values)
    summary = (info.get("longBusinessSummary") or "").strip()
    expected = {**EXPECTED_STORED[recording], **({"description": summary} if summary else {})}
    assert stored == expected, f"{recording}: stored forms differ\n got      {stored}\n expected {expected}"
    assert item.source_date is None and dict(item.source_dates) == {}, "Yahoo gives no date of its data"


@pytest.mark.parametrize("recording", SHARE_RECORDINGS)
def test_a_share_never_touches_funds_data(plugin, yahoo, recording):
    """EQUITY, the ETC included: one ``info`` read, never ``funds_data`` (offered here, so the log is the witness)."""
    symbol, info = _info(recording)
    binding = yahoo.give(symbol, info, {"technology": 1.0})
    assert _read_one(plugin, binding).status == EnricherReadStatus.OK
    assert "funds_data" not in yahoo.reads(symbol), f"funds_data read for a share: {yahoo.calls}"


@pytest.mark.parametrize("recording", ("enel", "apple", "asml"))
def test_a_share_description_is_the_business_summary_never_the_name(plugin, yahoo, recording):
    binding, info = _offer(yahoo, recording)
    assert info.get("longBusinessSummary"), "barrier: the recording has a business summary"
    stored = _stored(_read_one(plugin, binding).values)
    assert stored["description"] == info["longBusinessSummary"].strip()
    assert stored["description"] not in {info.get("longName"), info.get("shortName")}


def test_the_etc_filed_as_equity_is_read_as_a_share(plugin, yahoo):
    """IGLN.L, the gold ETC: quoteType EQUITY, so the share mapping (none of its fields given), never a fund voice."""
    binding, info = _offer(yahoo, "etc_gold")
    assert info["quoteType"] == "EQUITY" and info.get("longName"), "barrier: an ETC filed as a named EQUITY"
    item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK and dict(item.values) == {}, item


def test_fund_description_when_given(plugin, yahoo):
    """No recorded fund has a ``longBusinessSummary``: given, it is the description."""
    stored = _stored(_read_fund(plugin, yahoo, "LAB.FD1", longBusinessSummary="  A fund that tracks the world.  ").values)
    assert stored["description"] == "A fund that tracks the world."


@pytest.mark.parametrize("recording", ("swda", "etf_bond", "etf_hedged"))
def test_ter_agrees_with_justetf(plugin, yahoo, recording):
    """Cross-check: the TER Yahoo gives (a percent) stored equal to justETF's own recording of the same fund."""
    from backend.app.services.enricher_providers.justetf.plugin import overview_voices  # noqa: PLC0415 — the other source's own reading

    overview = json.loads((JUSTETF_FIXTURES / f"{recording}.json").read_text(encoding="utf-8"))["calls"]["get_etf_overview"]["response"]
    justetf_ter = normalize_value("ter", overview_voices(overview)["ter"])
    binding, _ = _offer(yahoo, recording)
    assert _stored(_read_one(plugin, binding).values)["ter"] == justetf_ter


@pytest.mark.parametrize("recording", ("swda", "etf_hedged"))
def test_inception_date_agrees_with_justetf(plugin, yahoo, recording):
    """Cross-check: the epoch as a UTC date equals the launch date justETF reads on its page."""
    from backend.app.services.enricher_providers.justetf.plugin import overview_voices  # noqa: PLC0415 — the other source's own reading

    overview = json.loads((JUSTETF_FIXTURES / f"{recording}.json").read_text(encoding="utf-8"))["calls"]["get_etf_overview"]["response"]
    justetf_date = normalize_value("inception_date", overview_voices(overview)["inception_date"])
    binding, _ = _offer(yahoo, recording)
    assert _stored(_read_one(plugin, binding).values)["inception_date"] == justetf_date


def test_etf_bond_inception_date_is_yahoos_own(plugin, yahoo):
    """AGGG.L: Yahoo says 2024-05-10 (1715299200, UTC midnight), justETF 2017-11-21. A real disagreement of the sources
    (the coordinator's correction), not a unit bug: Yahoo's date is stored as it is."""
    overview = json.loads((JUSTETF_FIXTURES / "etf_bond.json").read_text(encoding="utf-8"))["calls"]["get_etf_overview"]["response"]
    assert overview["inception_date"] == "21 November 2017", f"barrier: justETF's own date: {overview['inception_date']!r}"
    binding, info = _offer(yahoo, "etf_bond")
    assert info["fundInceptionDate"] == 1715299200, "barrier: the recorded epoch"
    assert _stored(_read_one(plugin, binding).values)["inception_date"] == "2024-05-10"


# =============================================================================
# 2. Mapping: a share, synthetic
# =============================================================================

YAHOO_SECTORS = [
    ("Utilities", "Utilities"),
    ("Technology", "Technology"),
    ("Healthcare", "Health Care"),
    ("Financial Services", "Financials"),
    ("Consumer Cyclical", "Consumer Discretionary"),
    ("Consumer Defensive", "Consumer Staples"),
    ("Communication Services", "Telecommunication"),
    ("Basic Materials", "Basic Materials"),
    ("Real Estate", "Real Estate"),
    ("Industrials", "Industrials"),
    ("Energy", "Energy"),
]


@pytest.mark.parametrize(("name", "stored"), YAHOO_SECTORS)
def test_share_sector_one_sector_at_100(plugin, yahoo, name, stored):
    assert validate_sector(name), f"barrier: the helper knows Yahoo's {name!r}"
    values = _stored(_read_share(plugin, yahoo, "LAB.SS1", sector=name).values)
    assert values["sector"] == {stored: "1.0000"}


@pytest.mark.parametrize("name", ["Conglomerates", "Space Mining", "", "   "])
def test_share_sector_the_helper_does_not_know_is_absent(plugin, yahoo, name):
    """Stored, an unknown name would be «Other» at 100 %, which says nothing: the voice is left out, the rest read."""
    item = _read_share(plugin, yahoo, "LAB.SS2", sector=name)
    assert "sector" not in item.values, f"an unknown sector is left out: {item.values}"
    assert _stored(item.values)["industry"] == "Consumer Electronics", "the other voices are still read"


def test_share_without_a_sector_has_none(plugin, yahoo):
    assert "sector" not in _read_share(plugin, yahoo, "LAB.SS3", sector=None).values


@pytest.mark.parametrize(
    ("country", "code"),
    [("Italy", "ITA"), ("United States", "USA"), ("Netherlands", "NLD"), ("United Kingdom", "GBR"), ("South Korea", "KOR"), ("Taiwan", "TWN")],
)
def test_share_issuer_country(plugin, yahoo, country, code):
    assert _stored(_read_share(plugin, yahoo, "LAB.CY1", country=country).values)["issuer_country"] == code


def test_share_untranslatable_country_is_absent_and_logged_once(plugin, yahoo):
    binding = yahoo.give("LAB.CY2", _share_info(country="Atlantis"))
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "issuer_country" not in item.values, item.values
    assert len(_plugin_lines_naming(events, "Atlantis")) == 1, f"one log line names the country: {events}"
    assert "industry" in item.values, "the other voices are still read"


def test_share_without_a_country_has_none(plugin, yahoo):
    assert "issuer_country" not in _read_share(plugin, yahoo, "LAB.CY3", country=None).values


@pytest.mark.parametrize(("amount", "currency"), [(98033917952, "EUR"), (5054147854336, "USD"), (123456, "CHF")])
def test_share_market_cap_in_an_iso_currency(plugin, yahoo, amount, currency):
    values = _stored(_read_share(plugin, yahoo, "LAB.MC1", marketCap=amount, currency=currency).values)
    assert values["market_cap"] == {"amount": str(amount), "currency": currency}


@pytest.mark.parametrize("currency", ["GBp", "ILA", "ZAc"], ids=["london-pence", "tel-aviv-agorot", "johannesburg-cents"])
def test_share_market_cap_in_a_minor_unit_is_absent_and_logged_once(plugin, yahoo, currency):
    """The amount would be 100× off. ``GBp`` passes the generic currency helper once upper-cased and ``ILA`` is upper
    case already: the plugin checks the code as given, case included."""
    binding = yahoo.give("LAB.MC2", _share_info(marketCap=123456789, currency=currency))
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "market_cap" not in item.values, f"{currency}: no market cap: {item.values}"
    assert len(_plugin_lines_naming(events, currency)) == 1, f"one log line names {currency}: {events}"
    assert _stored(item.values)["sector"] == {"Technology": "1.0000"}, "the other voices are still read"


@pytest.mark.parametrize(("overrides"), [{"marketCap": None}, {"currency": None}], ids=["no-amount", "no-currency"])
def test_share_market_cap_needs_both(plugin, yahoo, overrides):
    assert "market_cap" not in _read_share(plugin, yahoo, "LAB.MC3", **overrides).values


@pytest.mark.parametrize("field", ["industry", "longBusinessSummary"])
@pytest.mark.parametrize("empty", [None, "", "   "])
def test_share_empty_texts_are_absent(plugin, yahoo, field, empty):
    voice = {"industry": "industry", "longBusinessSummary": "description"}[field]
    assert voice not in _read_share(plugin, yahoo, "LAB.TX1", **{field: empty}).values


def test_share_without_a_summary_has_no_description_from_the_name(plugin, yahoo):
    item = _read_share(plugin, yahoo, "LAB.TX2", longBusinessSummary=None, longName="Lab Corp", shortName="LAB CORP")
    assert "description" not in item.values, f"never the name as a description: {item.values}"


# =============================================================================
# 2. Mapping: a fund, synthetic
# =============================================================================


@pytest.mark.parametrize(("ratio", "stored"), [(0.2, "0.002"), (0.07, "0.0007"), (0.55, "0.0055"), (1.0, "0.01"), (0.0, "0"), (0, "0")])
def test_fund_ter_is_a_percent_made_a_fraction(plugin, yahoo, ratio, stored):
    """``netExpenseRatio`` is a percent (0.2 is 0.2 %), a float: stored as the exact fraction."""
    assert _stored(_read_fund(plugin, yahoo, "LAB.TR1", netExpenseRatio=ratio).values)["ter"] == stored


def test_fund_without_an_expense_ratio_has_no_ter(plugin, yahoo):
    assert "ter" not in _read_fund(plugin, yahoo, "LAB.TR2", netExpenseRatio=None).values


@pytest.mark.parametrize("family", [None, "", "   "])
def test_fund_without_a_family_has_no_provider(plugin, yahoo, family):
    assert "fund_provider" not in _read_fund(plugin, yahoo, "LAB.FP1", fundFamily=family).values


def test_fund_provider_is_the_family(plugin, yahoo):
    assert _stored(_read_fund(plugin, yahoo, "LAB.FP2", fundFamily="Lab Asset Management").values)["fund_provider"] == "Lab Asset Management"


@pytest.mark.parametrize(
    ("epoch", "day"),
    [
        (1647216000, "2022-03-14"),
        # a second before UTC midnight: the 13th in UTC, already the 14th east of Greenwich
        (1647215999, "2022-03-13"),
        # 23:00 UTC: still the 14th in UTC, the 15th east of Greenwich
        (1647216000 + 23 * 3600, "2022-03-14"),
        (1253836800, "2009-09-25"),
    ],
    ids=["utc-midnight", "a-second-before", "late-evening", "swda"],
)
def test_fund_inception_date_is_the_epoch_in_utc(plugin, yahoo, epoch, day):
    """The day in UTC whatever the machine's zone: the two edges fail a local conversion east or west of Greenwich."""
    assert _stored(_read_fund(plugin, yahoo, "LAB.ID1", fundInceptionDate=epoch).values)["inception_date"] == day


@pytest.mark.parametrize("epoch", [None, "not a date"])
def test_fund_inception_date_absent_when_missing_or_unreadable(plugin, yahoo, epoch):
    assert "inception_date" not in _read_fund(plugin, yahoo, "LAB.ID2", fundInceptionDate=epoch).values


def test_mutual_fund_inception_date(plugin, yahoo):
    """The Frankfurt fund (exchange zone Europe/Berlin): 1647216000 is 2022-03-14 in UTC, Borsa Italiana's «Data di
    partenza» too (the coordinator's pin)."""
    binding, info = _offer(yahoo, "mutual_fund")
    assert info["quoteType"] == "MUTUALFUND" and info["fundInceptionDate"] == 1647216000, "barrier: the recorded fund"
    assert _stored(_read_one(plugin, binding).values) == {"inception_date": "2022-03-14"}


#: Yahoo's eleven fund sector keys, each with the standard sector it is stored under.
FUND_SECTOR_KEYS = [
    ("realestate", "Real Estate"),
    ("consumer_cyclical", "Consumer Discretionary"),
    ("basic_materials", "Basic Materials"),
    ("consumer_defensive", "Consumer Staples"),
    ("technology", "Technology"),
    ("communication_services", "Telecommunication"),
    ("financial_services", "Financials"),
    ("utilities", "Utilities"),
    ("industrials", "Industrials"),
    ("energy", "Energy"),
    ("healthcare", "Health Care"),
]


@pytest.mark.parametrize(("key", "sector"), FUND_SECTOR_KEYS)
def test_fund_sector_key(plugin, yahoo, key, sector):
    """One Yahoo key beside a fixed 60 % «Energy» (or «Utilities» beside energy): the standard sector it is stored under."""
    other_key, other_sector = ("utilities", "Utilities") if key == "energy" else ("energy", "Energy")
    item = _read_fund(plugin, yahoo, "LAB.SK1", sectors={key: 0.4, other_key: 0.6})
    assert _stored(item.values)["sector"] == {sector: "0.4000", other_sector: "0.6000"}


def test_fund_sector_unknown_key_folds_into_other_and_is_logged_once(plugin, yahoo):
    """A key neither the helper nor the table knows: its weight goes to «Other», never lost (the map still sums to one)."""
    binding = yahoo.give("LAB.SK2", _fund_info(), {"technology": 0.5, "space_mining": 0.2, "energy": 0.3})
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "space_mining" not in item.values["sector"], item.values["sector"]
    assert _stored(item.values)["sector"] == {"Energy": "0.3000", "Other": "0.2000", "Technology": "0.5000"}
    assert len(_plugin_lines_naming(events, "space_mining")) == 1, f"one log line names the key: {events}"


def test_fund_sector_two_unknown_keys_sum_in_other(plugin, yahoo):
    item = _read_fund(plugin, yahoo, "LAB.SK3", sectors={"technology": 0.5, "space_mining": 0.2, "deep_sea": 0.3})
    assert _stored(item.values)["sector"] == {"Other": "0.5000", "Technology": "0.5000"}


@pytest.mark.parametrize("junk", [0, 0.0, None, "n/a"], ids=["zero", "zero-float", "none", "text"])
def test_fund_sector_zero_or_non_numeric_weights_are_dropped(plugin, yahoo, junk):
    item = _read_fund(plugin, yahoo, "LAB.SK4", sectors={"technology": 0.7, "energy": 0.3, "realestate": junk})
    assert _stored(item.values)["sector"] == {"Energy": "0.3000", "Technology": "0.7000"}


@pytest.mark.parametrize("weights", [{}, {"technology": 0, "energy": 0.0}], ids=["empty", "all-zero"])
def test_fund_sector_empty_map_is_absent(plugin, yahoo, weights):
    item = _read_fund(plugin, yahoo, "LAB.SK5", sectors=weights)
    assert "sector" not in item.values, item.values
    assert _stored(item.values)["ter"] == "0.002", "the info voices are still read"


@pytest.mark.parametrize("keys", [frozenset({"ter", "fund_provider"}), ["ter"], ("inception_date", "description")], ids=["set", "list", "tuple"])
def test_fund_data_not_touched_when_sector_is_not_asked(plugin, yahoo, keys):
    symbol, info = _info("swda")
    binding = yahoo.give(symbol, info, _sector_weightings("swda"))
    item = _read_one(plugin, binding, keys)
    assert item.status == EnricherReadStatus.OK, item
    assert "sector" not in item.values
    assert "funds_data" not in yahoo.reads(symbol) and "sector_weightings" not in yahoo.reads(symbol), f"funds_data read without sector asked: {yahoo.calls}"


@pytest.mark.parametrize("keys", [None, frozenset({"sector"}), ["ter", "sector"]], ids=["all", "sector-only", "with-sector"])
def test_fund_data_read_when_sector_is_asked(plugin, yahoo, keys):
    symbol, info = _info("swda")
    item = _read_one(plugin, yahoo.give(symbol, info, _sector_weightings("swda")), keys)
    assert _stored(item.values)["sector"] == SWDA_SECTOR


@pytest.mark.parametrize("at_property", [False, True], ids=["at-sector-weightings", "at-funds-data"])
@pytest.mark.parametrize("error", [RuntimeError("fund profile missing"), KeyError("topHoldings"), ConnectionError("reset by peer")])
def test_fund_data_failure_keeps_the_info_voices(plugin, yahoo, error, at_property):
    symbol, info = _info("swda")
    binding = yahoo.give(symbol, info, _RaisedAtProperty(error) if at_property else error)
    item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, f"the info voices still go out: {item}"
    assert _stored(item.values) == {key: value for key, value in EXPECTED_STORED["swda"].items() if key != "sector"}


@pytest.mark.parametrize("at_property", [False, True], ids=["at-sector-weightings", "at-funds-data"])
def test_fund_data_refusal_is_a_refusal(plugin, yahoo, at_property):
    """A refusal on ``funds_data`` is not «a failing funds_data»: this binding and the next are RATE_LIMITED."""
    error = RATE_LIMIT_ERROR()
    symbol, info = _info("swda")
    refused = yahoo.give(symbol, info, _RaisedAtProperty(error) if at_property else error)
    # never offered: a call for it fails the test
    items = _by_index(list(plugin.read([refused, _ticker("LAB.NEVER1")])), 2)
    for index in (0, 1):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    assert yahoo.symbols_read == [symbol]


@pytest.mark.parametrize("quote_type", ["CRYPTOCURRENCY", "CURRENCY", "INDEX", "FUTURE"])
def test_another_quote_type_is_found_with_no_values(plugin, yahoo, quote_type):
    """Apple's info relabelled: the share fields are there, but only EQUITY reads them."""
    binding = yahoo.give("LAB.QT1", _share_info(quoteType=quote_type))
    item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK and dict(item.values) == {}, item
    assert "funds_data" not in yahoo.reads("LAB.QT1")


def test_the_quote_type_decides_not_the_fields(plugin, yahoo):
    """A fund's info relabelled EQUITY reads as a share: no TER, no fund provider, no funds_data."""
    binding = yahoo.give("LAB.QT2", _fund_info(quoteType="EQUITY"), _sector_weightings("swda"))
    item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert not set(item.values) & {"ter", "fund_provider", "inception_date"}, item.values
    assert "funds_data" not in yahoo.reads("LAB.QT2")


#: Fields Yahoo gives that the enricher never reads.
NEVER_READ = {
    "isin": "US0000000000",
    "totalAssets": 123,
    "legalType": "Something else",
    "regularMarketPrice": 1.0,
    "previousClose": 2.0,
    "trailingPE": 3.0,
    "forwardPE": 4.0,
    "category": "Lab",
    "netAssets": 5,
}


@pytest.mark.parametrize("recording", ("apple", "swda"))
def test_fields_not_read_change_nothing(plugin, yahoo, recording):
    """Prices, P/E, the ISIN Yahoo gives, fund size, legal type: changing them changes no stored value."""
    symbol, info = _info(recording)
    weights = _sector_weightings(recording)
    first = yahoo.give(f"{symbol}.A", info, weights)
    second = yahoo.give(f"{symbol}.B", {**info, **NEVER_READ}, weights)
    items = _by_index(list(plugin.read([first, second])), 2)
    assert items[0].status == items[1].status == EnricherReadStatus.OK
    assert _stored(items[0].values) == _stored(items[1].values)
    assert not set(items[1].values) & {"legal_form", "fund_size"}, items[1].values


# =============================================================================
# 3. Not found
# =============================================================================


@pytest.mark.parametrize("info", [{}, {"trailingPegRatio": None}, {"symbol": "LAB.NF1", "longName": "No type"}], ids=["empty", "no-quote-type", "named-no-quote-type"])
def test_unknown_ticker_is_not_found(plugin, yahoo, info):
    """Synthetic: no recording has an unknown ticker. An info empty or without ``quoteType`` is no instrument."""
    binding = yahoo.give("LAB.NF1", info)
    assert _read_one(plugin, binding).status == EnricherReadStatus.NOT_FOUND
    assert plugin.recognize(binding).found is False


@pytest.mark.parametrize("where", ["at-ticker", "at-info"])
def test_invalid_isin_error_is_not_found(plugin, yahoo, where):
    """The recorded answer to a bond's ISIN (``btp_ord``): yfinance raises «Invalid ISIN number» from ``Ticker`` itself
    (``TickerBase.__init__``); raised at ``info`` it means the same."""
    recorded = _recording("btp_ord")["calls"]["info_from_isin"]["error"]
    assert recorded == "ValueError: Invalid ISIN number: IT0001444378", f"barrier: the recorded error: {recorded!r}"
    error = ValueError("Invalid ISIN number: IT0001444378")
    binding = yahoo.refuse_construction("IT0001444378", error) if where == "at-ticker" else yahoo.give("IT0001444378", error)
    assert _read_one(plugin, binding).status == EnricherReadStatus.NOT_FOUND
    assert plugin.recognize(binding).found is False


def test_nameless_equity_row_is_not_found(plugin, yahoo):
    """``btp_italia``'s Stuttgart listing: EQUITY with prices and no name at all."""
    binding, info = _offer(yahoo, "btp_italia")
    assert info["quoteType"] == "EQUITY" and not info.get("longName") and not info.get("shortName"), "barrier: the nameless row"
    assert _read_one(plugin, binding).status == EnricherReadStatus.NOT_FOUND
    assert plugin.recognize(binding).found is False


def test_the_same_row_with_a_short_name_is_found(plugin, yahoo):
    _, info = _info("btp_italia")
    binding = yahoo.give("LAB.NF2", {**info, "shortName": "BTP ITALIA"})
    assert _read_one(plugin, binding).status == EnricherReadStatus.OK
    assert plugin.recognize(binding) == EnricherRecognition(found=True, name="BTP ITALIA", page_url=_page("LAB.NF2"), identifiers={})


# =============================================================================
# 4. recognize
# =============================================================================


@pytest.mark.parametrize(("recording", "name"), [("apple", "Apple Inc."), ("swda", "iShares Core MSCI World UCITS ETF USD (Acc)"), ("mutual_fund", "Anima Dinamix"), ("etc_gold", "iShares Physical Gold ETC")])
def test_recognize_found(plugin, yahoo, recording, name):
    """The long name, the page, no identifier (never the ISIN Yahoo gives for a ticker); ``funds_data`` never read."""
    binding, _ = _offer(yahoo, recording)
    assert plugin.recognize(binding) == EnricherRecognition(found=True, name=name, page_url=_page(binding.identifier), identifiers={})
    assert yahoo.reads(binding.identifier) == ["info"], f"recognize reads info only: {yahoo.calls}"


def test_recognize_short_name_when_no_long_name(plugin, yahoo):
    binding = yahoo.give("LAB.RC1", _share_info(longName=None, shortName="LAB SHORT"))
    assert plugin.recognize(binding).name == "LAB SHORT"


def test_recognize_never_gives_the_isin_yahoo_returns(plugin, yahoo):
    """Enel's recorded ``isin_of_ticker`` is a Chilean ISIN (CL0002266774): Yahoo's ISIN of a ticker is never read."""
    assert _recording("enel")["calls"]["isin_of_ticker:ENEL.MI"]["response"] == "CL0002266774", "barrier: the wrong ISIN"
    binding = yahoo.give("ENEL.MI", {**_info("enel")[1], "isin": "CL0002266774"})
    assert plugin.recognize(binding).identifiers == {}


@pytest.mark.parametrize("binding", [EnricherBinding("ISIN", "US0378331005"), EnricherBinding("LEI", "HWUPKR0MPOU8FGXBT394")])
def test_recognize_non_ticker_without_a_call(plugin, yahoo, binding):
    assert plugin.recognize(binding).found is False
    assert yahoo.constructed == [] and yahoo.calls == []


def test_recognize_rate_limited_raises(plugin, yahoo):
    assert rate_limited_from_exception(RATE_LIMIT_ERROR(), CODE) is not None, "barrier: the core reads yfinance's refusal as a 429"
    binding = yahoo.give("LAB.RL1", RATE_LIMIT_ERROR())
    with pytest.raises(Exception) as raised:
        plugin.recognize(binding)
    assert rate_limited_from_exception(raised.value, CODE) is not None, f"the core must read it as a refusal: {raised.value!r}"


# =============================================================================
# 5. read
# =============================================================================


def test_read_mixed_list(plugin, yahoo):
    apple, _ = _offer(yahoo, "apple")
    swda, _ = _offer(yahoo, "swda")
    unknown = yahoo.give("LAB.MX1", {})
    bindings = [EnricherBinding("ISIN", "US0378331005"), apple, unknown, swda]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert [items[i].status for i in range(4)] == [EnricherReadStatus.NOT_FOUND, EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.OK]
    assert _stored(items[1].values)["issuer_country"] == "USA"
    assert _stored(items[3].values)["ter"] == "0.002"
    assert "US0378331005" not in yahoo.constructed, "no call for the ISIN binding"
    assert yahoo.symbols_read == ["AAPL", "LAB.MX1", "IWDA.L"]


@pytest.mark.parametrize("error", [RuntimeError("HTTP Error 500"), ConnectionError("connection reset"), KeyError("quoteSummary")])
def test_read_error_is_a_source_error_and_the_next_is_read(plugin, yahoo, error):
    failing = yahoo.give("LAB.ER1", error)
    apple, _ = _offer(yahoo, "apple")

    items = _by_index(list(plugin.read([failing, apple])), 2)

    assert items[0].status == EnricherReadStatus.ERROR and items[0].error_code == SOURCE_ERROR, items[0]
    assert items[1].status == EnricherReadStatus.OK
    assert yahoo.symbols_read == ["LAB.ER1", "AAPL"]


def test_read_rate_limited_defers_every_remaining_binding(plugin, yahoo):
    """yfinance's real refusal: RATE_LIMITED for it and every later binding, with no call for them."""
    assert rate_limited_from_exception(RATE_LIMIT_ERROR(), CODE) is not None, "barrier: the core reads yfinance's refusal as a 429"
    apple, _ = _offer(yahoo, "apple")
    refused = yahoo.give("LAB.RL2", RATE_LIMIT_ERROR())
    # never offered: a call for either fails the test
    bindings = [apple, refused, _ticker("LAB.NEVER2"), _ticker("LAB.NEVER3")]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert items[0].status == EnricherReadStatus.OK
    for index in (1, 2, 3):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    assert yahoo.symbols_read == ["AAPL", "LAB.RL2"], "no call after the refusal"
    assert "LAB.NEVER2" not in yahoo.constructed and "LAB.NEVER3" not in yahoo.constructed


def test_read_rate_limited_at_ticker_construction(plugin, yahoo):
    """A refusal raised by ``yf.Ticker`` itself (its ISIN lookup can call Yahoo) is a refusal too."""
    refused = yahoo.refuse_construction("LAB.RL3", RATE_LIMIT_ERROR())
    items = _by_index(list(plugin.read([refused, _ticker("LAB.NEVER4")])), 2)
    assert all(item.status == EnricherReadStatus.ERROR and item.error_code == RATE_LIMITED for item in items.values()), items
    assert "LAB.NEVER4" not in yahoo.constructed


def test_read_every_recording_in_one_call(plugin, yahoo):
    """Every recording in one ``read``, pause 0: one item each, in a known status, each ticker's info read once."""
    names = sorted(EXPECTED_STORED) + ["btp_italia"]
    bindings = [_offer(yahoo, name)[0] for name in names]
    items = _by_index(list(plugin.read(bindings)), len(bindings))
    statuses = {name: items[index].status for index, name in enumerate(names)}
    assert statuses == {**dict.fromkeys(EXPECTED_STORED, EnricherReadStatus.OK), "btp_italia": EnricherReadStatus.NOT_FOUND}, statuses
    assert sorted(yahoo.symbols_read) == sorted(binding.identifier for binding in bindings)


def test_read_paces_between_tickers(plugin, yahoo, pace):
    """C5: the module's pace between two calls to Yahoo: three shares, two waits of the interval, none before the first."""
    bindings = [_offer(yahoo, name)[0] for name in ("enel", "apple", "asml")]
    items = _by_index(list(plugin.read(bindings)), 3)
    assert all(item.status == EnricherReadStatus.OK for item in items.values())
    assert pace.slept == [pace.interval, pace.interval], f"two waits of the interval: {pace.slept}"


def test_a_single_call_never_waits(plugin, yahoo, pace):
    assert len(list(plugin.read([_offer(yahoo, "enel")[0]]))) == 1
    assert pace.slept == [], f"one call, no wait: {pace.slept}"


def test_raw_values_are_never_floats(plugin, yahoo):
    """The catalogue refuses a float (0.1 is not 0.1): every number Yahoo gives as a float reaches it as text or Decimal."""
    for name in FUND_RECORDINGS:
        binding, _ = _offer(yahoo, name)
        values = dict(_read_one(plugin, binding).values)
        floats = {key: value for key, value in values.items() if isinstance(value, float)}
        floats.update({f"sector.{key}": weight for key, weight in (values.get("sector") or {}).items() if isinstance(weight, float)})
        assert floats == {}, f"{name}: floats among the raw values: {floats}"
        if "ter" in values:
            assert Decimal(str(values["ter"])) == Decimal(EXPECTED_STORED[name]["ter"]), f"{name}: the raw TER is the exact fraction"


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


def test_two_reads_share_one_pace(yh, yahoo, pace):
    """Two reads from two instances (as the registry builds them): the second waits the plugin's interval."""
    first, second = yh.YahooFinanceEnricher(), yh.YahooFinanceEnricher()
    assert list(first.read([_offer(yahoo, "enel")[0]]))[0].status == EnricherReadStatus.OK
    calls_before = len(pace.slept)
    assert list(second.read([_offer(yahoo, "apple")[0]]))[0].status == EnricherReadStatus.OK
    assert pace.interval in pace.slept[calls_before:], f"the second read waited the interval: {pace.slept}"


def test_recognize_is_paced_with_the_reads(yh, yahoo, pace, plugin):
    binding = _offer(yahoo, "enel")[0]
    plugin.recognize(binding)
    list(plugin.read([binding]))
    assert pace.interval in pace.slept, f"recognize and read share the pace: {pace.slept}"


# =============================================================================
# ENR-3b: search by ``yf.Search``
# =============================================================================


class _FakeSearch:
    """What ``yf.Search(text)`` returns: the ``quotes`` Yahoo answered."""

    def __init__(self, quotes: Any) -> None:
        self.quotes = quotes


def _offer_search(yahoo: FakeYahoo, quotes: Any = None, error: BaseException | None = None) -> list[str]:
    """Install ``yf.Search`` on the fake: it records the texts it is called with, then answers ``quotes`` or raises."""
    texts: list[str] = []

    def search(text: str, *args: Any, **kwargs: Any) -> _FakeSearch:
        texts.append(text)
        if error is not None:
            raise error
        return _FakeSearch(quotes)

    yahoo.Search = search  # type: ignore[attr-defined]
    return texts


def _quote(symbol: str, quote_type: str = "EQUITY", **fields: Any) -> dict[str, Any]:
    return {"symbol": symbol, "quoteType": quote_type, "isYahooFinance": True, **fields}


def test_search_maps_quotes_to_ticker_bindings(plugin, yahoo, pace):
    texts = _offer_search(
        yahoo,
        [
            _quote("ENEL.MI", "EQUITY", longname="Enel SpA", shortname="ENEL"),
            _quote("SWDA.MI", "ETF", shortname="ISHARESIV-CORE MSCI WORLD"),
            _quote("0P0001OS3T.F", "MUTUALFUND"),
        ],
    )

    results = plugin.search("  lab world  ")

    assert texts == ["lab world"], "the text is stripped before the call"
    expected = [
        ("Enel SpA", "ENEL.MI", AssetType.STOCK),
        ("ISHARESIV-CORE MSCI WORLD", "SWDA.MI", AssetType.ETF),
        ("0P0001OS3T.F", "0P0001OS3T.F", AssetType.FUND),
    ]
    assert results == [EnricherSearchResult(name=name, binding=EnricherBinding("TICKER", symbol), asset_type=asset_type, page_url=_page(symbol)) for name, symbol, asset_type in expected]
    assert yahoo.constructed == [], "search never builds a Ticker"


@pytest.mark.parametrize(
    ("fields", "market"),
    [
        ({"exchDisp": "Milan", "exchange": "MIL"}, "Milan"),
        ({"exchange": "MIL"}, "MIL"),
        ({"exchDisp": "  Milan  "}, "Milan"),
        ({"exchDisp": "", "exchange": "NMS"}, "NMS"),
        ({"exchDisp": "   ", "exchange": "  "}, None),
        ({}, None),
    ],
    ids=["display-name-wins", "exchange-code-fallback", "stripped", "blank-display-falls-back", "blank-both", "none-said"],
)
def test_search_result_market_is_the_exchange_display_name_else_its_code(plugin, yahoo, pace, fields, market):
    """ENR-3: two listings of one fund are told apart by the market Yahoo names; absent when it names none."""
    _offer_search(yahoo, [_quote("SWDA.MI", "ETF", shortname="LAB WORLD", **fields)])
    (result,) = plugin.search("lab market")
    assert result.binding.identifier == "SWDA.MI", "barrier: the quote was kept"
    assert result.market == market


def test_search_with_no_quotes_is_empty(plugin, yahoo, pace):
    _offer_search(yahoo, [])
    assert plugin.search("lab nothing") == []


@pytest.mark.parametrize("text", ["", " ", "   ", "a", " b "])
def test_search_of_a_short_or_blank_text_makes_no_call(plugin, yahoo, pace, text):
    texts = _offer_search(yahoo, [_quote("ENEL.MI")])
    assert plugin.search(text) == []
    assert texts == [] and pace.slept == [], "no call to Yahoo, no pace spent"


def test_search_skips_what_the_enricher_does_not_read(plugin, yahoo, pace):
    _offer_search(
        yahoo,
        [
            _quote("^FTSEMIB", "INDEX"),
            _quote("EURUSD=X", "CURRENCY"),
            _quote("BTC-USD", "CRYPTOCURRENCY"),
            _quote("ES=F", "FUTURE"),
            _quote("LAB.EXT", "EQUITY", isYahooFinance=False),
            {"quoteType": "EQUITY", "isYahooFinance": True},
            {"symbol": "LAB.NOTYPE", "isYahooFinance": True},
            "not a mapping",
            _quote("AAPL", "equity", longname="Apple Inc."),
        ],
    )
    results = plugin.search("lab mixed")
    assert [result.binding.identifier for result in results] == ["AAPL"], "only the readable listing is kept"
    assert results[0].asset_type == AssetType.STOCK


def test_search_takes_the_first_twenty_quotes(plugin, yahoo, pace):
    _offer_search(yahoo, [_quote(f"LAB{index:02d}.MI") for index in range(30)])
    results = plugin.search("lab many")
    assert [result.binding.identifier for result in results] == [f"LAB{index:02d}.MI" for index in range(20)]


def test_search_cut_applies_before_the_filter(plugin, yahoo, pace):
    """The cut is on Yahoo's quotes, not on the kept ones: a readable quote after the twentieth is never reached."""
    _offer_search(yahoo, [_quote(f"^LAB{index:02d}", "INDEX") for index in range(20)] + [_quote("LATE.MI")])
    assert plugin.search("lab late") == []


def test_search_refusal_is_enricher_rate_limited_with_the_source_wait(plugin, yahoo, pace):
    class _Response:
        status_code = 429
        headers = {"Retry-After": "12"}

    class _HTTPError(Exception):
        response = _Response()

    _offer_search(yahoo, error=_HTTPError("Too Many Requests"))
    with pytest.raises(EnricherRateLimited) as raised:
        plugin.search("lab refused")
    assert raised.value.retry_after == 12.0
    assert isinstance(raised.value.__cause__, _HTTPError), "raised from the library's error"


def test_search_refusal_by_yfinances_own_error_is_enricher_rate_limited(plugin, yahoo, pace):
    assert rate_limited_from_exception(RATE_LIMIT_ERROR(), CODE) is not None, "barrier: the core reads yfinance's refusal as a 429"
    _offer_search(yahoo, error=RATE_LIMIT_ERROR())
    with pytest.raises(EnricherRateLimited):
        plugin.search("lab refused")


def test_search_another_failure_is_reraised_as_it_is(plugin, yahoo, pace):
    failure = ValueError("unexpected answer")
    assert rate_limited_from_exception(failure, CODE) is None, "barrier: not a refusal"
    _offer_search(yahoo, error=failure)
    with pytest.raises(ValueError) as raised:
        plugin.search("lab broken")
    assert raised.value is failure


def test_search_without_yfinance_raises(yh, monkeypatch):
    monkeypatch.setattr(yh, "yf", None, raising=True)
    with pytest.raises(RuntimeError, match="yfinance is not installed"):
        yh.YahooFinanceEnricher().search("lab text")


def test_search_is_paced_with_the_reads(yahoo, pace, plugin):
    _offer_search(yahoo, [])
    plugin.search("lab paced")
    binding = _offer(yahoo, "enel")[0]
    list(plugin.read([binding]))
    assert pace.interval in pace.slept, f"a read after a search waits the interval: {pace.slept}"
