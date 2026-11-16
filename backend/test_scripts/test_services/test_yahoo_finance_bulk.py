"""Yahoo Finance provider: the bulk current-value read (project 76, lot C5; no network, no DB, no server).

Contract, pinned on one RECORDED v7 quote response (``fixtures/yahoo/v7_quote_five_symbols.json``: AAPL, SWDA.MI,
EUNL.DE, BTC-EUR, PEPE24478-USD). ``YfData.get_raw_json`` is replaced, so no socket is opened:

 1. ``get_current_values_bulk`` answers a TICKER item with the very value, currency and as_of_date that
    ``get_current_value`` gives on ``.info`` holding the same quote (one mapping, ``_quote_from_info``).
 2. The as_of_date is the day of ``regularMarketTime`` in the exchange's own zone (New York, Rome, UTC).
 3. All distinct symbols travel in ONE request: ``symbols`` joined by commas, ``formatted`` = ``"false"``.
 4. A symbol Yahoo did not return: its key is absent, the others are answered.
 5. No ``regularMarketPrice``: the previous close answers; no price at all: ``NO_DATA`` under that key.
 6. A 429 raises ``AssetRateLimitedError`` for the whole call, after one request (never retried).
 7. An ISIN item resolves to its symbol (``yf.Ticker(isin).ticker``) and is answered under its own key.
 8. A wrong identifier type answers ``INVALID_IDENTIFIER_TYPE`` for that item only; still one request.
 9. ``supports_bulk_current`` is True, ``bulk_current_max_items`` 50; ``_bulk_quote_available()`` is False when the
    yfinance internals cannot be imported.
10. Two items with the same symbol are both answered (two keys, one symbol in the request).

Red on HEAD b84aba43e: the provider does not override ``get_current_values_bulk`` and has none of the new names.
"""

from __future__ import annotations

import builtins
import copy
import importlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from yfinance.exceptions import YFRateLimitError

from backend.app.db import IdentifierType
from backend.app.schemas.prices import FACurrentValue, FACurrentValueRequest
from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.test_scripts.test_utils import print_section, print_success

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "yahoo" / "v7_quote_five_symbols.json"
RECORDED = {q["symbol"]: q for q in json.loads(FIXTURE.read_text())["quoteResponse"]["result"]}
SYMBOLS = list(RECORDED)
GET_RAW_JSON = "yfinance.data.YfData.get_raw_json"


class _Wire:
    """Replaces ``YfData.get_raw_json``: answers a v7 body, records every call."""

    def __init__(self, quotes=None, exc=None):
        self.quotes = list(RECORDED.values()) if quotes is None else quotes
        self.exc = exc
        self.calls: list[dict] = []

    def __call__(self, _self, url, params=None, *args, **kwargs):
        self.calls.append({"url": url, "params": dict(params or {})})
        if self.exc is not None:
            raise self.exc
        wanted = {s.upper() for s in (params or {}).get("symbols", "").split(",")}
        return {"quoteResponse": {"result": [q for q in self.quotes if q["symbol"].upper() in wanted], "error": None}}


def _install(monkeypatch, wire: _Wire, *, isin_map: dict | None = None, info_by_symbol: dict | None = None):
    """Wire for the v7 call; a fake ``yf`` whose Ticker resolves ISINs and serves ``.info``."""

    def ticker(identifier):
        symbol = (isin_map or {}).get(identifier, identifier)
        return SimpleNamespace(ticker=symbol, info=(info_by_symbol or RECORDED).get(symbol, {}))

    # A plain function, so that it binds as a method of YfData (a callable instance would not receive its self)
    monkeypatch.setattr(GET_RAW_JSON, lambda yf_data, url, params=None, *args, **kwargs: wire(yf_data, url, params, *args, **kwargs))
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "yf", SimpleNamespace(Ticker=ticker))
    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=lambda _s: pytest.fail("a retry slept")))


def _item(key, identifier, kind=IdentifierType.TICKER):
    return FACurrentValueRequest(key=key, identifier=identifier, identifier_type=kind)


def _day(symbol: str, zone: str):
    return datetime.fromtimestamp(RECORDED[symbol]["regularMarketTime"], tz=ZoneInfo(zone)).date()


@pytest.mark.asyncio
async def test_bulk_equals_single_read(monkeypatch):
    print_section("same result as get_current_value on the same quote")
    wire = _Wire()
    _install(monkeypatch, wire)
    provider = YahooFinanceProvider()
    answers = await provider.get_current_values_bulk([_item(s, s) for s in SYMBOLS])
    assert set(answers) == set(SYMBOLS)
    for symbol in SYMBOLS:
        single = await provider.get_current_value(symbol, IdentifierType.TICKER, {})
        got = answers[symbol]
        assert isinstance(got, FACurrentValue), (symbol, got)
        assert (got.value, got.currency, got.as_of_date) == (single.value, single.currency, single.as_of_date), symbol
        assert got.value == Decimal(str(RECORDED[symbol]["regularMarketPrice"]))
    print_success("5 recorded quotes: bulk == single")


@pytest.mark.asyncio
async def test_as_of_date_in_exchange_zone(monkeypatch):
    print_section("as_of_date in the exchange's zone")
    _install(monkeypatch, _Wire())
    answers = await YahooFinanceProvider().get_current_values_bulk([_item(s, s) for s in SYMBOLS])
    assert answers["AAPL"].as_of_date == _day("AAPL", "America/New_York")
    assert answers["SWDA.MI"].as_of_date == _day("SWDA.MI", "Europe/Rome")
    assert answers["BTC-EUR"].as_of_date == datetime.fromtimestamp(RECORDED["BTC-EUR"]["regularMarketTime"], tz=UTC).date()
    print_success("New York, Rome, UTC")


@pytest.mark.asyncio
async def test_one_request_for_all_symbols(monkeypatch):
    print_section("one request")
    wire = _Wire()
    _install(monkeypatch, wire)
    await YahooFinanceProvider().get_current_values_bulk([_item(s, s) for s in SYMBOLS])
    assert len(wire.calls) == 1
    params = wire.calls[0]["params"]
    assert params["symbols"].split(",") == SYMBOLS
    assert params["formatted"] == "false"
    assert wire.calls[0]["url"].rstrip("?").endswith("/v7/finance/quote")
    print_success("1 request, 5 symbols")


@pytest.mark.asyncio
async def test_unreturned_symbol_has_no_key(monkeypatch):
    print_section("a symbol Yahoo did not return")
    wire = _Wire()
    _install(monkeypatch, wire)
    answers = await YahooFinanceProvider().get_current_values_bulk([_item(s, s) for s in [*SYMBOLS, "NOPE.XX"]])
    assert "NOPE.XX" not in answers
    assert set(SYMBOLS) <= set(answers)
    assert "NOPE.XX" in wire.calls[0]["params"]["symbols"].split(",")
    print_success("key absent, the others answered")


@pytest.mark.asyncio
async def test_previous_close_fallback_and_no_data(monkeypatch):
    print_section("previous close, then NO_DATA")
    no_price = copy.deepcopy(RECORDED["AAPL"])
    del no_price["regularMarketPrice"]
    nothing = copy.deepcopy(RECORDED["EUNL.DE"])
    for field in ("regularMarketPrice", "regularMarketPreviousClose", "currentPrice", "previousClose"):
        nothing.pop(field, None)
    _install(monkeypatch, _Wire(quotes=[no_price, nothing]))
    answers = await YahooFinanceProvider().get_current_values_bulk([_item("AAPL", "AAPL"), _item("EUNL.DE", "EUNL.DE")])
    assert answers["AAPL"].value == Decimal(str(RECORDED["AAPL"]["regularMarketPreviousClose"]))
    err = answers["EUNL.DE"]
    assert isinstance(err, AssetSourceError) and err.error_code == "NO_DATA"
    print_success("previous close answers; no price -> NO_DATA")


@pytest.mark.asyncio
async def test_rate_limited_raises_once(monkeypatch):
    print_section("429 on the bulk call")
    for exc in (YFRateLimitError(), Exception("HTTP Error 429: Too Many Requests")):
        wire = _Wire(exc=exc)
        _install(monkeypatch, wire)
        with pytest.raises(AssetRateLimitedError):
            await YahooFinanceProvider().get_current_values_bulk([_item(s, s) for s in SYMBOLS])
        assert len(wire.calls) == 1
    print_success("whole call raises, one request, no retry")


@pytest.mark.asyncio
async def test_isin_item_resolved_to_symbol(monkeypatch):
    print_section("ISIN item")
    wire = _Wire()
    _install(monkeypatch, wire, isin_map={"IE00B4L5Y983": "SWDA.MI"})
    answers = await YahooFinanceProvider().get_current_values_bulk([_item("isin-key", "IE00B4L5Y983", IdentifierType.ISIN)])
    assert wire.calls[0]["params"]["symbols"].split(",") == ["SWDA.MI"]
    single = await YahooFinanceProvider().get_current_value("SWDA.MI", IdentifierType.TICKER, {})
    assert (answers["isin-key"].value, answers["isin-key"].currency, answers["isin-key"].as_of_date) == (single.value, single.currency, single.as_of_date)
    print_success("request carries SWDA.MI, answer under the ISIN's key")


@pytest.mark.asyncio
async def test_wrong_identifier_type_answers_error_only_for_it(monkeypatch):
    print_section("wrong identifier type")
    wire = _Wire()
    _install(monkeypatch, wire)
    items = [_item("bad-other", "AAPL", IdentifierType.OTHER), _item("bad-uuid", "AAPL", IdentifierType.UUID), _item("AAPL", "AAPL"), _item("BTC-EUR", "BTC-EUR")]
    answers = await YahooFinanceProvider().get_current_values_bulk(items)
    for key in ("bad-other", "bad-uuid"):
        assert isinstance(answers[key], AssetSourceError) and answers[key].error_code == "INVALID_IDENTIFIER_TYPE"
    assert isinstance(answers["AAPL"], FACurrentValue) and isinstance(answers["BTC-EUR"], FACurrentValue)
    assert len(wire.calls) == 1
    print_success("two refused, two answered, one request")


def test_capability_flags_and_availability(monkeypatch):
    print_section("capability")
    assert YahooFinanceProvider.supports_bulk_current is True
    assert YahooFinanceProvider.bulk_current_max_items == 50
    assert yfp._bulk_quote_available() is True

    real_import, real_import_module = builtins.__import__, importlib.import_module

    def blocked(name):
        return name.startswith(("yfinance.data", "yfinance.const"))

    def fake_import(name, *args, **kwargs):
        if blocked(name):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    def fake_import_module(name, *args, **kwargs):
        if blocked(name):
            raise ImportError(name)
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    assert yfp._bulk_quote_available() is False
    print_success("True here, False without yfinance.data")


@pytest.mark.asyncio
async def test_same_symbol_twice_answers_both_keys(monkeypatch):
    print_section("two items, one symbol")
    wire = _Wire()
    _install(monkeypatch, wire)
    answers = await YahooFinanceProvider().get_current_values_bulk([_item("a", "AAPL"), _item("b", "aapl")])
    assert set(answers) == {"a", "b"}
    assert answers["a"].value == answers["b"].value == Decimal(str(RECORDED["AAPL"]["regularMarketPrice"]))
    assert len(wire.calls) == 1
    assert [s.upper() for s in wire.calls[0]["params"]["symbols"].split(",")] == ["AAPL"]
    print_success("both keys answered, AAPL once in the request")
