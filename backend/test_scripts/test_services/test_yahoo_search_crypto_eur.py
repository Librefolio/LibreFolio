"""Yahoo search: the euro ticker of a crypto beside its dollar one (project 76, lot Y1).

On Yahoo a cryptocurrency has one ticker per currency it is quoted in (``BTC-USD``, ``BTC-EUR``, ``BTC-GBP``: the same
coin, the price in another currency). Yahoo's search answers the dollar one only («bitcoin» → ``BTC-USD``). The contract:

1. For every crypto result (``quoteType`` ``CRYPTOCURRENCY``) whose symbol ends in ``-USD`` and whose ``-EUR`` twin is
   not among the results already, the search asks Yahoo for the twins in ONE v7 quote-list request
   (``_fetch_v7_quotes``, the one of C5), and adds, right after each dollar row, the euro row of a twin Yahoo returned
   quoted in EUR: ``identifier`` the twin, ``currency`` ``EUR``, ``type`` ``CRYPTO``, ``display_name`` the quote's name.
2. Nothing to ask (no crypto, the twin already listed): no request.
3. A twin Yahoo does not return, or returns in another currency: no row.
4. Best effort: the extra request failing leaves the search as it was, the dollar rows only, never an error; the v7
   helper unavailable (``_bulk_quote_available`` false): no request. **Except a refusal for too many requests**
   (``AssetRateLimitedError``): it leaves the search, as a refusal on a result's currency does, so the core pauses
   Yahoo (the method's own rule).
5. Prices of assets only: the exchange-rate providers are untouched.

Pure: ``yf`` is a fake (``Search``, ``Ticker``), and ``YfData.get_raw_json`` is replaced, so no socket is opened. One
test answers with the RECORDED ``BTC-EUR`` quote of ``fixtures/yahoo/v7_quote_five_symbols.json`` (its ``longName`` is
null, its ``shortName`` «Bitcoin EUR»): the real shape of the fields read.
Red on HEAD f113b4549: the search answers the dollar rows only and asks nothing more.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider
from backend.app.services.assets.base import AssetRateLimitedError
from backend.test_scripts.test_utils import print_section, print_success

GET_RAW_JSON = "yfinance.data.YfData.get_raw_json"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "yahoo" / "v7_quote_five_symbols.json"


def _coin(label: str) -> str:
    """A coin symbol of this test (the currency cache is per symbol and per process)."""
    return f"Y1{label.upper()}{uuid4().hex[:6].upper()}"


class _Wire:
    """Replaces ``YfData.get_raw_json``: answers the v7 quotes it holds for the symbols asked, records every call."""

    def __init__(self, quotes: list[dict] | None = None, exc: BaseException | None = None):
        self.quotes = quotes or []
        self.exc = exc
        self.calls: list[list[str]] = []

    def __call__(self, url, params=None):
        asked = [symbol for symbol in (params or {}).get("symbols", "").split(",") if symbol]
        self.calls.append(asked)
        if self.exc is not None:
            raise self.exc
        return {"quoteResponse": {"result": [quote for quote in self.quotes if quote["symbol"] in asked], "error": None}}


def _install(monkeypatch: pytest.MonkeyPatch, quotes: list[dict], wire: _Wire) -> None:
    """A fake ``yf`` whose search answers ``quotes`` and whose tickers are quoted in USD; the v7 wire replaced."""
    ticker = SimpleNamespace(fast_info={"currency": "USD"})
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "yf", SimpleNamespace(Search=lambda query: SimpleNamespace(quotes=quotes), Ticker=lambda symbol: ticker))
    monkeypatch.setattr(GET_RAW_JSON, lambda _yf_data, url, params=None, *args, **kwargs: wire(url, params))
    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=lambda _s: pytest.fail("a retry slept")))


def _crypto(symbol: str, name: str) -> dict:
    return {"symbol": symbol, "quoteType": "CRYPTOCURRENCY", "shortname": name, "isYahooFinance": True}


def _v7(symbol: str, currency: str, name: str) -> dict:
    return {"symbol": symbol, "currency": currency, "shortName": name, "quoteType": "CRYPTOCURRENCY", "regularMarketPrice": 1.0}


@pytest.mark.asyncio
async def test_y1_the_euro_twin_follows_its_dollar_row(monkeypatch: pytest.MonkeyPatch):
    """1: «bitcoin» → BTC-USD, then BTC-EUR (EUR, CRYPTO, the quote's name), asked in one request."""
    print_section("Y1: the euro twin")
    coin = _coin("btc")
    wire = _Wire([_v7(f"{coin}-EUR", "EUR", "Bitcoin EUR")])
    _install(monkeypatch, [_crypto(f"{coin}-USD", "Bitcoin USD")], wire)

    results = await YahooFinanceProvider().search("bitcoin")

    assert [row["identifier"] for row in results] == [f"{coin}-USD", f"{coin}-EUR"]
    euro = results[1]
    assert (euro["currency"], euro["type"], euro["display_name"]) == ("EUR", "CRYPTO", "Bitcoin EUR")
    assert wire.calls == [[f"{coin}-EUR"]]
    print_success("dollar row, then the euro twin")


@pytest.mark.asyncio
async def test_y1_every_twin_is_asked_in_one_request_and_sits_after_its_own_row(monkeypatch: pytest.MonkeyPatch):
    """1: two coins and a stock between them: one request for both twins; each euro row right after its dollar row."""
    first, second = _coin("a"), _coin("b")
    wire = _Wire([_v7(f"{first}-EUR", "EUR", "First EUR"), _v7(f"{second}-EUR", "EUR", "Second EUR")])
    stock = {"symbol": f"{_coin('s')}", "quoteType": "EQUITY", "longname": "A stock", "isYahooFinance": True}
    _install(monkeypatch, [_crypto(f"{first}-USD", "First USD"), stock, _crypto(f"{second}-USD", "Second USD")], wire)

    results = await YahooFinanceProvider().search("coins")

    assert [row["identifier"] for row in results] == [f"{first}-USD", f"{first}-EUR", stock["symbol"], f"{second}-USD", f"{second}-EUR"]
    assert len(wire.calls) == 1 and sorted(wire.calls[0]) == sorted([f"{first}-EUR", f"{second}-EUR"])


@pytest.mark.asyncio
async def test_y1_nothing_is_asked_without_a_crypto_or_when_the_twin_is_listed(monkeypatch: pytest.MonkeyPatch):
    """2: a stock only, or the euro twin already a result: no request, no duplicate."""
    coin = _coin("listed")
    wire = _Wire([_v7(f"{coin}-EUR", "EUR", "Listed EUR")])
    _install(monkeypatch, [_crypto(f"{coin}-USD", "Listed USD"), _crypto(f"{coin}-EUR", "Listed EUR")], wire)
    results = await YahooFinanceProvider().search("listed")
    assert [row["identifier"] for row in results] == [f"{coin}-USD", f"{coin}-EUR"]
    assert wire.calls == []

    stock_wire = _Wire()
    _install(monkeypatch, [{"symbol": _coin("only"), "quoteType": "EQUITY", "longname": "A stock", "isYahooFinance": True}], stock_wire)
    await YahooFinanceProvider().search("stock")
    assert stock_wire.calls == []


@pytest.mark.asyncio
async def test_y1_a_twin_yahoo_does_not_return_in_eur_gives_no_row(monkeypatch: pytest.MonkeyPatch):
    """3: a twin not returned, or returned in another currency: the dollar row alone."""
    missing, other = _coin("missing"), _coin("other")
    wire = _Wire([_v7(f"{other}-EUR", "USD", "Odd")])
    _install(monkeypatch, [_crypto(f"{missing}-USD", "Missing USD"), _crypto(f"{other}-USD", "Other USD")], wire)

    results = await YahooFinanceProvider().search("twins")

    assert [row["identifier"] for row in results] == [f"{missing}-USD", f"{other}-USD"]
    assert len(wire.calls) == 1, "barrier: the twins were asked"


@pytest.mark.asyncio
async def test_y1_the_extra_request_failing_leaves_the_search_as_it_was(monkeypatch: pytest.MonkeyPatch):
    """4: best effort — the dollar rows, never an error, when the extra request fails."""
    coin = _coin("fail")
    wire = _Wire(exc=RuntimeError("down"))
    _install(monkeypatch, [_crypto(f"{coin}-USD", "Fail USD")], wire)

    results = await YahooFinanceProvider().search("fail")

    assert [row["identifier"] for row in results] == [f"{coin}-USD"]
    assert len(wire.calls) >= 1, "barrier: the twin was asked"


@pytest.mark.asyncio
async def test_y1_a_refusal_for_too_many_requests_on_the_extra_request_leaves_the_search(monkeypatch: pytest.MonkeyPatch):
    """4: a refusal is not swallowed: the search leaves as rate limited, once, so the core pauses Yahoo."""
    coin = _coin("refused")
    wire = _Wire(exc=AssetRateLimitedError("too many", retry_after=30.0))
    _install(monkeypatch, [_crypto(f"{coin}-USD", "Refused USD")], wire)

    with pytest.raises(AssetRateLimitedError):
        await YahooFinanceProvider().search("refused")
    assert len(wire.calls) == 1, "asked once, never retried"


@pytest.mark.asyncio
async def test_y1_the_recorded_euro_quote_gives_the_row(monkeypatch: pytest.MonkeyPatch):
    """1, on real data: the recorded ``BTC-EUR`` v7 quote (``longName`` null) gives the euro row, named by its
    ``shortName``."""
    recorded = next(quote for quote in json.loads(FIXTURE.read_text())["quoteResponse"]["result"] if quote["symbol"] == "BTC-EUR")
    wire = _Wire([recorded])
    _install(monkeypatch, [_crypto("BTC-USD", "Bitcoin USD")], wire)

    results = await YahooFinanceProvider().search("bitcoin")

    assert [row["identifier"] for row in results] == ["BTC-USD", "BTC-EUR"]
    assert (results[1]["currency"], results[1]["type"], results[1]["display_name"]) == ("EUR", "CRYPTO", "Bitcoin EUR")


@pytest.mark.asyncio
async def test_y1_no_request_when_the_v7_helper_is_unavailable(monkeypatch: pytest.MonkeyPatch):
    """4: ``_bulk_quote_available`` false (a yfinance release without the helper): the dollar rows, nothing asked."""
    coin = _coin("nohelper")
    wire = _Wire([_v7(f"{coin}-EUR", "EUR", "No helper EUR")])
    _install(monkeypatch, [_crypto(f"{coin}-USD", "No helper USD")], wire)
    monkeypatch.setattr(yfp, "_bulk_quote_available", lambda: False)

    results = await YahooFinanceProvider().search("nohelper")

    assert [row["identifier"] for row in results] == [f"{coin}-USD"]
    assert wire.calls == []
