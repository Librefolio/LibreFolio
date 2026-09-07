"""Yahoo Finance provider — error and edge paths (no network, no DB, no server).

The live Yahoo happy path is covered by the network suite. Here the ``yf``
module the provider imported is replaced by a fake exposing ``Ticker`` and
``Search``, so every branch the real API can force — missing price fields,
empty / malformed history frames, NaN closes, dividends and splits, search
failures, metadata assembly — is driven with exact, fixed inputs. No socket is
opened. Error messages avoid the transient-retry keywords so ``_yf_with_retry``
raises on the first attempt and never sleeps.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.asset_source import AssetSourceError
from backend.app.services.asset_source_providers import yahoo_finance as yfp
from backend.app.services.asset_source_providers.yahoo_finance import YahooFinanceProvider

# A type Yahoo does not accept (only TICKER and ISIN are valid).
INVALID_TYPE = IdentifierType.CUSIP


class _FakeTicker:
    """Configurable stand-in for ``yfinance.Ticker``."""

    def __init__(self, *, info=None, info_exc=None, fast_info=None, history=None, history_exc=None, dividends=None, dividends_exc=None, splits=None, splits_exc=None, isin=None, isin_exc=None):
        self._info = info if info is not None else {}
        self._info_exc = info_exc
        self._fast_info = fast_info if fast_info is not None else {}
        self._history = history
        self._history_exc = history_exc
        self._dividends = dividends
        self._dividends_exc = dividends_exc
        self._splits = splits
        self._splits_exc = splits_exc
        self._isin = isin
        self._isin_exc = isin_exc

    @property
    def info(self):
        if self._info_exc is not None:
            raise self._info_exc
        return self._info

    @property
    def fast_info(self):
        return self._fast_info

    def history(self, **kwargs):
        if self._history_exc is not None:
            raise self._history_exc
        return self._history

    @property
    def dividends(self):
        if self._dividends_exc is not None:
            raise self._dividends_exc
        return self._dividends

    @property
    def splits(self):
        if self._splits_exc is not None:
            raise self._splits_exc
        return self._splits

    @property
    def isin(self):
        if self._isin_exc is not None:
            raise self._isin_exc
        return self._isin


def _install_yf(monkeypatch, *, ticker=None, ticker_factory=None, search=None, search_factory=None):
    """Bind a fake ``yf`` (Ticker + Search) into the yahoo_finance module only."""

    def default_ticker_factory(symbol):
        return ticker if ticker is not None else _FakeTicker()

    def default_search_factory(query):
        if isinstance(search, Exception):
            raise search
        return search if search is not None else SimpleNamespace(quotes=[])

    fake = SimpleNamespace(
        Ticker=ticker_factory or default_ticker_factory,
        Search=search_factory or default_search_factory,
    )
    monkeypatch.setattr(yfp, "yf", fake)


def _utc_index(days: list[str]):
    return pd.to_datetime(days).tz_localize("UTC")


# ── identity / pure ─────────────────────────────────────────────────────────


def test_identity_and_url():
    p = YahooFinanceProvider()
    assert p.provider_code == "yfinance"
    assert p.provider_name == "Yahoo Finance"
    assert p.supports_meaningful_volume is True
    assert p.volume_kind == FAVolumeKind.TRADED_SHARES
    assert set(p.accepted_identifier_types) == {ProviderInputType.TICKER, ProviderInputType.ISIN}
    assert p.get_icon.startswith("https://")
    assert p.provider_help_url.startswith("/mkdocs/")
    assert p.get_asset_url("AAPL") == "https://finance.yahoo.com/quote/AAPL"
    assert p.test_cases and p.test_search_query == "Apple"
    p.validate_params(None)  # no-op, must not raise


# ── get_current_value ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_current_value_invalid_type():
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_current_value("X", INVALID_TYPE)
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_current_value_unavailable(monkeypatch):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", False)
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert exc.value.error_code == "NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_current_value_regular_market(monkeypatch):
    rmt = int(datetime(2026, 2, 11, 20, 0, tzinfo=UTC).timestamp())
    info = {"regularMarketPrice": 150.25, "currency": "USD", "regularMarketTime": rmt}
    _install_yf(monkeypatch, ticker=_FakeTicker(info=info))

    result = await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert result.value == Decimal("150.25")
    assert result.currency == "USD"
    assert result.as_of_date == date(2026, 2, 11)
    assert result.source == "Yahoo Finance"


@pytest.mark.asyncio
async def test_current_value_fallback_fields_and_today(monkeypatch):
    # No regularMarketPrice, no currency, no regularMarketTime.
    info = {"previousClose": 42.0}
    _install_yf(monkeypatch, ticker=_FakeTicker(info=info))

    result = await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert result.value == Decimal("42.0")
    assert result.currency == "USD"  # defaulted
    assert result.as_of_date == date.today()


@pytest.mark.asyncio
async def test_current_value_no_data(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(info={}))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert exc.value.error_code == "NO_DATA"


@pytest.mark.asyncio
async def test_current_value_fetch_error(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(info_exc=RuntimeError("kaboom")))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert exc.value.error_code == "FETCH_ERROR"


# ── get_history_value ───────────────────────────────────────────────────────


def _ohlcv(dates: list[str], closes: list[float]) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame(
        {
            "Open": [c - 1 for c in closes],
            "High": [c + 1 for c in closes],
            "Low": [c - 2 for c in closes],
            "Close": closes,
            "Volume": [1000 + i for i in range(n)],
        },
        index=_utc_index(dates),
    )


@pytest.mark.asyncio
async def test_history_invalid_type():
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("X", INVALID_TYPE, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_history_unavailable(monkeypatch):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", False)
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_history_happy_with_dividends_and_splits(monkeypatch):
    hist = _ohlcv(["2026-01-05", "2026-01-06", "2026-01-07"], [100.0, 101.0, 102.5])
    dividends = pd.Series([0.5], index=_utc_index(["2026-01-06"]))
    splits = pd.Series([2.0], index=_utc_index(["2026-01-07"]))
    ticker = _FakeTicker(history=hist, info={"currency": "EUR"}, dividends=dividends, splits=splits)
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert result.currency == "EUR"
    assert [p.date for p in result.prices] == [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    assert result.prices[0].close == Decimal("100.0")
    assert result.prices[0].open == Decimal("99.0")
    assert result.prices[0].volume == 1000
    types = sorted(e.type for e in result.events)
    assert types == ["DIVIDEND", "SPLIT"]
    div = next(e for e in result.events if e.type == "DIVIDEND")
    assert div.date == date(2026, 1, 6) and div.value.amount == Decimal("0.5")


@pytest.mark.asyncio
async def test_history_invalid_data_object(monkeypatch):
    # yfinance edge case: returns None instead of a DataFrame.
    _install_yf(monkeypatch, ticker=_FakeTicker(history=None))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_history_empty_frame(monkeypatch):
    empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    _install_yf(monkeypatch, ticker=_FakeTicker(history=empty, info={"currency": "USD"}))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "NO_DATA"


@pytest.mark.asyncio
async def test_history_unexpected_columns(monkeypatch):
    bad = pd.DataFrame({"Foo": [1.0]}, index=_utc_index(["2026-01-05"]))
    _install_yf(monkeypatch, ticker=_FakeTicker(history=bad, info={"currency": "USD"}))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_history_all_nan_close_yields_no_data(monkeypatch):
    hist = _ohlcv(["2026-01-05", "2026-01-06"], [float("nan"), float("nan")])
    _install_yf(monkeypatch, ticker=_FakeTicker(history=hist, info={"currency": "USD"}))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "NO_DATA"


@pytest.mark.asyncio
async def test_history_fetch_error(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(history_exc=RuntimeError("kaboom")))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_history_min_period_and_currency_fallback(monkeypatch):
    # start_date == "min" takes the period="max" branch; info raising → USD fallback.
    hist = _ohlcv(["2026-01-05"], [100.0])
    ticker = _FakeTicker(history=hist, info_exc=RuntimeError("no info"), dividends=None, splits=None)
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, "min", date(2026, 1, 31))
    assert result.currency == "USD"
    assert len(result.prices) == 1


@pytest.mark.asyncio
async def test_history_empty_info_and_event_series_errors(monkeypatch):
    # info present but falsy (355->360), and dividends/splits access raises (362-363, 366-367).
    hist = _ohlcv(["2026-01-05"], [100.0])
    ticker = _FakeTicker(
        history=hist,
        info={},  # falsy → currency stays USD, `if info:` false branch
        dividends_exc=RuntimeError("dividends fetch failed"),
        splits_exc=RuntimeError("splits fetch failed"),
    )
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert result.currency == "USD"
    assert result.events == []


@pytest.mark.asyncio
async def test_history_filters_out_of_range_and_zero_dividends(monkeypatch):
    # Rows before start and after end are filtered (397, 399); a zero/out-of-range
    # dividend is skipped (435->434, 437->434).
    hist = _ohlcv(["2025-12-30", "2026-01-05", "2026-02-10"], [90.0, 100.0, 110.0])
    dividends = pd.Series([0.0, 0.5], index=_utc_index(["2026-01-05", "2026-06-01"]))
    ticker = _FakeTicker(history=hist, info={"currency": "USD"}, dividends=dividends)
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    # Only the in-range row survives.
    assert [p.date for p in result.prices] == [date(2026, 1, 5)]
    # Zero dividend skipped; the 0.5 one is outside the end date → no events.
    assert result.events == []


@pytest.mark.asyncio
async def test_current_value_retries_transient_error(monkeypatch):
    """A transient error is retried (backoff slept, but stubbed to no-op)."""

    class _FlakyTicker:
        calls = 0

        @property
        def info(self):
            _FlakyTicker.calls += 1
            if _FlakyTicker.calls == 1:
                raise RuntimeError("connection reset by peer")  # transient keyword
            return {"regularMarketPrice": 10.0, "currency": "USD"}

    flaky = _FlakyTicker()
    _install_yf(monkeypatch, ticker_factory=lambda sym: flaky)
    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=lambda s: None))

    result = await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    assert result.value == Decimal("10.0")
    assert _FlakyTicker.calls == 2  # failed once, succeeded on retry


@pytest.mark.asyncio
async def test_history_split_edge_cases_skipped(monkeypatch):
    # A 1:1 split (ratio==1 → skipped) and an out-of-range split date → no SPLIT events.
    hist = _ohlcv(["2026-01-05"], [100.0])
    splits = pd.Series([1.0, 3.0], index=_utc_index(["2026-01-05", "2026-09-01"]))
    ticker = _FakeTicker(history=hist, info={"currency": "USD"}, splits=splits)
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert [e for e in result.events if e.type == "SPLIT"] == []


# ── search ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_too_short_returns_empty(monkeypatch):
    _install_yf(monkeypatch)
    assert await YahooFinanceProvider().search("A") == []


@pytest.mark.asyncio
async def test_search_unavailable(monkeypatch):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", False)
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().search("Apple")
    assert exc.value.error_code == "NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_search_maps_quotes(monkeypatch):
    quotes = [
        {"symbol": "AAPL", "quoteType": "EQUITY", "longname": "Apple Inc.", "isYahooFinance": True},
        {"symbol": "SPY", "quoteType": "ETF", "shortname": "SPDR S&P 500", "isYahooFinance": True},
        {"symbol": "SKIP", "quoteType": "EQUITY", "isYahooFinance": False},  # skipped
    ]
    search = SimpleNamespace(quotes=quotes)
    ticker = _FakeTicker(fast_info={"currency": "USD"})
    _install_yf(monkeypatch, ticker=ticker, search=search)

    results = await YahooFinanceProvider().search("Apple")
    symbols = [r["identifier"] for r in results]
    assert symbols == ["AAPL", "SPY"]  # non-yahoo quote dropped
    assert results[0]["type"] == "STOCK"
    assert results[1]["type"] == "ETF"
    assert results[0]["display_name"] == "Apple Inc."
    assert results[1]["display_name"] == "SPDR S&P 500"  # shortname fallback
    assert results[0]["currency"] == "USD"


@pytest.mark.asyncio
async def test_search_swallows_errors(monkeypatch):
    def boom(query):
        raise RuntimeError("kaboom")

    _install_yf(monkeypatch, search_factory=boom)
    assert await YahooFinanceProvider().search("Apple") == []


# ── _fetch_currency ─────────────────────────────────────────────────────────


def test_fetch_currency_cache_hit_and_error(monkeypatch):
    p = YahooFinanceProvider()
    calls = {"n": 0}

    def ticker_factory(symbol):
        calls["n"] += 1
        return _FakeTicker(fast_info={"currency": "GBP"})

    _install_yf(monkeypatch, ticker_factory=ticker_factory)
    assert p._fetch_currency("VOD.L") == "GBP"
    assert p._fetch_currency("VOD.L") == "GBP"  # cache hit
    assert calls["n"] == 1

    # A ticker that raises → None, cached negatively.
    def boom(symbol):
        raise RuntimeError("kaboom")

    _install_yf(monkeypatch, ticker_factory=boom)
    assert p._fetch_currency("BROKEN") is None


# ── fetch_asset_metadata ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_invalid_type():
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().fetch_asset_metadata("X", INVALID_TYPE)
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_metadata_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", False)
    assert await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER) is None


@pytest.mark.asyncio
async def test_metadata_happy(monkeypatch):
    info = {
        "quoteType": "EQUITY",
        "longBusinessSummary": "y" * 600,  # truncated to 500
        "sector": "Technology",
        "currency": "USD",
        "symbol": "AAPL",
    }
    ticker = _FakeTicker(info=info, isin="US0378331005")
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)
    assert result is not None
    assert result.asset_type == "STOCK"
    assert result.currency == "USD"
    assert result.identifier_ticker == "AAPL"
    assert result.identifier_isin == "US0378331005"
    assert len(result.classification_params.short_description) == 500
    assert result.classification_params.sector_area is not None


@pytest.mark.asyncio
async def test_metadata_no_info_returns_none(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(info={}))
    assert await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER) is None


@pytest.mark.asyncio
async def test_metadata_name_fallbacks(monkeypatch):
    # No longBusinessSummary → longName wins; unknown quoteType → OTHER; bad ISIN ignored.
    info = {"quoteType": "weird", "longName": "Long Co", "shortName": "LC"}
    ticker = _FakeTicker(info=info, isin="-")
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)
    assert result.asset_type == "OTHER"
    assert result.classification_params.short_description == "Long Co"
    assert result.identifier_isin is None  # "-" rejected


@pytest.mark.asyncio
async def test_metadata_unknown_sector_still_builds(monkeypatch):
    info = {"quoteType": "ETF", "shortName": "Fund", "sector": "Nonexistent Sector"}
    _install_yf(monkeypatch, ticker=_FakeTicker(info=info))
    result = await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)
    # shortName fallback for description, unknown sector still yields a sector area.
    assert result.classification_params.short_description == "Fund"
    assert result.classification_params.sector_area is not None


@pytest.mark.asyncio
async def test_metadata_isin_error_and_default_description(monkeypatch):
    # t.isin raises (629-630) and no summary/longName/shortName → default description (663).
    info = {"quoteType": "EQUITY", "currency": "USD", "symbol": "AAPL"}
    ticker = _FakeTicker(info=info, isin_exc=RuntimeError("isin lookup failed"))
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)
    assert result is not None
    assert result.identifier_isin is None  # isin fetch failed, swallowed
    assert result.classification_params.short_description == "AAPL from Yahoo Finance"


@pytest.mark.asyncio
async def test_metadata_exception_returns_none(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(info_exc=RuntimeError("kaboom")))
    assert await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
