"""Yahoo Finance provider — error and edge paths (no network, no DB, no server).

The live Yahoo happy path is covered by the network suite. Here the ``yf``
module the provider imported is replaced by a fake exposing ``Ticker`` and
``Search``, so every branch the real API can force — missing price fields,
empty / malformed history frames, NaN closes, dividends and splits, search
failures, metadata assembly — is driven with exact, fixed inputs. No socket is
opened. Non-retry cases avoid transient-retry keywords; the dedicated retry
case stubs ``_time_mod.sleep`` and records the requested backoff delays. The
«too many requests» cases (X-RL X3) replace it with a sleep that fails the
test: a refusal leaves at once as ``AssetRateLimitedError``, after one request,
and search and metadata no longer turn it into ``[]`` / ``None``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.prices import FAHistoricalData
from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError

# A type Yahoo does not accept (only TICKER and ISIN are valid).
INVALID_TYPE = IdentifierType.CUSIP


class _FakeTicker:
    """Configurable stand-in for ``yfinance.Ticker``."""

    def __init__(
        self,
        *,
        info=None,
        info_exc=None,
        fast_info=None,
        history=None,
        history_exc=None,
        dividends=None,
        dividends_exc=None,
        splits=None,
        splits_exc=None,
        isin=None,
        isin_exc=None,
    ):
        self._info = info if info is not None else {}
        self._info_exc = info_exc
        self._fast_info = fast_info if fast_info is not None else {}
        self._history = history
        self._history_exc = history_exc
        self.history_calls: list[dict] = []
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
        self.history_calls.append(dict(kwargs))
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
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "pd", pd)
    monkeypatch.setattr(yfp, "yf", fake)


def _utc_index(days: list[str]):
    return pd.to_datetime(days).tz_localize("UTC")


class _MalformedEventSeries:
    """Series-like event data whose index fails during date normalization."""

    empty = False

    def __init__(self, value: float):
        self._value = value

    def items(self):
        return [(object(), self._value)]


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
async def test_history_finite_range_uses_exclusive_remote_end_and_inclusive_utc_dates(monkeypatch):
    requested_start = date(2026, 1, 2)
    requested_end = date(2026, 1, 3)
    hist = pd.DataFrame(
        {
            "Open": [89.0, 99.0, 109.0, 119.0],
            "High": [91.0, 101.0, 111.0, 121.0],
            "Low": [88.0, 98.0, 108.0, 118.0],
            "Close": [90.0, 100.0, 110.0, 120.0],
            "Volume": [900, 1000, 1100, 1200],
        },
        index=pd.to_datetime(
            [
                "2026-01-01 18:00:00-05:00",  # 2026-01-01 UTC, outside
                "2026-01-01 20:00:00-05:00",  # 2026-01-02 UTC, start boundary
                "2026-01-03 18:00:00-05:00",  # 2026-01-03 UTC, end boundary
                "2026-01-03 20:00:00-05:00",  # 2026-01-04 UTC, outside
            ]
        ),
    )
    ticker = _FakeTicker(history=hist, info={"currency": "USD"})
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, requested_start, requested_end)

    assert ticker.history_calls == [{"start": "2026-01-02", "end": "2026-01-04"}]
    assert [point.date for point in result.prices] == [requested_start, requested_end]
    assert [point.close for point in result.prices] == [Decimal("100.0"), Decimal("110.0")]


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
async def test_history_nan_optional_fields_map_to_none_but_close_is_required(monkeypatch):
    hist = pd.DataFrame(
        {
            "Open": [float("nan"), 10.0],
            "High": [float("nan"), 12.0],
            "Low": [float("nan"), 9.0],
            "Close": [101.5, float("nan")],
            "Volume": [float("nan"), 500.0],
        },
        index=_utc_index(["2026-01-05", "2026-01-06"]),
    )
    _install_yf(monkeypatch, ticker=_FakeTicker(history=hist, info={"currency": "USD"}))

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))

    assert [point.date for point in result.prices] == [date(2026, 1, 5)]
    point = next(point for point in result.prices if point.date == date(2026, 1, 5))
    assert point.close == Decimal("101.5")
    assert point.open is None
    assert point.high is None
    assert point.low is None
    assert point.volume is None


@pytest.mark.asyncio
async def test_history_fetch_error(monkeypatch):
    _install_yf(monkeypatch, ticker=_FakeTicker(history_exc=RuntimeError("kaboom")))
    with pytest.raises(AssetSourceError) as exc:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_history_retries_transient_fetch_through_retry_boundary(monkeypatch):
    hist = _ohlcv(["2026-01-05"], [100.0])

    class _TransientHistoryTicker(_FakeTicker):
        def __init__(self):
            super().__init__(history=hist, info={"currency": "USD"})
            self.attempts = 0

        def history(self, **kwargs):
            self.history_calls.append(dict(kwargs))
            self.attempts += 1
            if self.attempts < 3:
                raise RuntimeError("connection reset by peer")
            return self._history

    ticker = _TransientHistoryTicker()
    delays: list[float] = []
    retry_labels: list[str] = []
    real_retry = yfp._yf_with_retry

    def recording_retry(fn, *, label="yfinance"):
        retry_labels.append(label)
        return real_retry(fn, label=label)

    _install_yf(monkeypatch, ticker=ticker)
    monkeypatch.setattr(yfp, "_yf_with_retry", recording_retry)
    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=delays.append))

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))

    expected_kwargs = {"start": "2026-01-01", "end": "2026-02-01"}
    assert ticker.history_calls == [expected_kwargs, expected_kwargs, expected_kwargs]
    assert retry_labels == ["history(AAPL)"]
    assert delays == [1.5, 3.0]
    assert [point.close for point in result.prices] == [Decimal("100.0")]


@pytest.mark.asyncio
async def test_history_min_period_and_currency_fallback(monkeypatch):
    # start_date == "min" takes the period="max" branch; info raising → USD fallback.
    hist = _ohlcv(["2026-01-05"], [100.0])
    ticker = _FakeTicker(history=hist, info_exc=RuntimeError("no info"), dividends=None, splits=None)
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, "min", date(2026, 1, 31))
    assert ticker.history_calls == [{"period": "max"}]
    assert result.currency == "USD"
    assert [point.date for point in result.prices] == [date(2026, 1, 5)]


@pytest.mark.asyncio
async def test_history_falsy_info_falls_back_to_usd(monkeypatch):
    hist = _ohlcv(["2026-01-05"], [100.0])
    ticker = _FakeTicker(history=hist, info={})
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert result.currency == "USD"


@pytest.mark.parametrize(
    ("broken_kind", "failure_mode", "expected_type", "expected_amount"),
    [
        ("dividends", "acquisition", "SPLIT", Decimal("2.0")),
        ("splits", "acquisition", "DIVIDEND", Decimal("0.5")),
        ("dividends", "parsing", "SPLIT", Decimal("2.0")),
        ("splits", "parsing", "DIVIDEND", Decimal("0.5")),
    ],
    ids=[
        "dividend-acquisition",
        "split-acquisition",
        "dividend-parsing",
        "split-parsing",
    ],
)
@pytest.mark.asyncio
async def test_history_event_failures_are_independent_best_effort(monkeypatch, broken_kind, failure_mode, expected_type, expected_amount):
    hist = _ohlcv(["2026-01-05"], [100.0])
    ticker_kwargs = {
        "history": hist,
        "info": {"currency": "USD"},
        "dividends": pd.Series([0.5], index=_utc_index(["2026-01-05"])),
        "splits": pd.Series([2.0], index=_utc_index(["2026-01-05"])),
    }
    if failure_mode == "acquisition":
        ticker_kwargs[f"{broken_kind}_exc"] = RuntimeError(f"{broken_kind} fetch failed")
    else:
        ticker_kwargs[broken_kind] = _MalformedEventSeries(0.5 if broken_kind == "dividends" else 2.0)

    _install_yf(monkeypatch, ticker=_FakeTicker(**ticker_kwargs))

    result = await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))

    assert [point.close for point in result.prices] == [Decimal("100.0")]
    assert {event.type for event in result.events} == {expected_type}
    event = next(event for event in result.events if event.type == expected_type)
    assert event.date == date(2026, 1, 5)
    assert event.value.amount == expected_amount


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


# ── «too many requests» (X-RL X3): raised at once, never retried in the thread ──


class _RefusingTicker(_FakeTicker):
    """A ticker whose every request is refused with ``refusal``, counting how often it was asked."""

    def __init__(self, refusal: Exception):
        super().__init__(history_exc=refusal)
        self._refusal = refusal
        self.info_reads = 0

    @property
    def info(self):
        self.info_reads += 1
        raise self._refusal


def _sleeping_fails(monkeypatch) -> None:
    """A sleep in the provider's thread fails the test: a refusal is never waited out there."""

    def forbidden(seconds):
        raise AssertionError(f"slept {seconds} s in the provider's thread")

    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=forbidden))


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(YFRateLimitError(), id="yfinance-class"),
        pytest.param(RuntimeError("429 Client Error: Too Many Requests for url: https://query2.finance.yahoo.com/v10"), id="429-whole-word"),
        pytest.param(RuntimeError("Too Many Requests"), id="too-many-requests"),
        pytest.param(RuntimeError("Rate limit reached, slow down"), id="rate-limit"),
    ],
)
def test_is_rate_limited_recognises_a_refusal(error):
    assert yfp._is_rate_limited(error) is True


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError("No data found for 4290.T"), id="ticker-4290"),
        pytest.param(RuntimeError("1429 rows returned"), id="1429"),
        pytest.param(RuntimeError("connection reset by peer"), id="transient"),
        pytest.param(RuntimeError("503 Service Unavailable"), id="503"),
    ],
)
def test_is_rate_limited_ignores_anything_else(error):
    assert yfp._is_rate_limited(error) is False


@pytest.mark.parametrize("refusal", [YFRateLimitError(), RuntimeError("HTTP Error 429: Too Many Requests")], ids=["yfinance-class", "message"])
def test_a_refusal_is_raised_after_one_call_without_sleep(monkeypatch, refusal):
    """The first refusal leaves ``_yf_with_retry`` as ``AssetRateLimitedError`` from it: one call, no sleep, no retry."""
    _sleeping_fails(monkeypatch)
    calls: list[int] = []

    def refused():
        calls.append(1)
        raise refusal

    with pytest.raises(AssetRateLimitedError) as raised:
        yfp._yf_with_retry(refused, label="current_value(AAPL)")

    assert len(calls) == 1
    assert raised.value.__cause__ is refusal
    assert (raised.value.error_code, raised.value.retry_after, raised.value.scope) == ("RATE_LIMITED", None, None)


def test_a_refusal_after_a_transient_error_stops_the_retries(monkeypatch):
    """A transient error is still retried after its backoff; the refusal that follows ends the loop at once."""
    delays: list[float] = []
    monkeypatch.setattr(yfp, "_time_mod", SimpleNamespace(sleep=delays.append))
    outcomes = iter([RuntimeError("connection reset by peer"), YFRateLimitError(), RuntimeError("never reached")])
    calls: list[int] = []

    def flaky():
        calls.append(1)
        raise next(outcomes)

    with pytest.raises(AssetRateLimitedError):
        yfp._yf_with_retry(flaky, label="history(AAPL)")

    assert (len(calls), delays) == (2, [1.5])


@pytest.mark.asyncio
async def test_current_value_and_history_refused_raise_rate_limited(monkeypatch):
    """Not ``FETCH_ERROR``: the refusal reaches the core, one request each, without sleeping."""
    _sleeping_fails(monkeypatch)
    ticker = _RefusingTicker(YFRateLimitError())
    _install_yf(monkeypatch, ticker=ticker)

    with pytest.raises(AssetRateLimitedError) as current:
        await YahooFinanceProvider().get_current_value("AAPL", IdentifierType.TICKER)
    with pytest.raises(AssetRateLimitedError) as history:
        await YahooFinanceProvider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))

    assert (current.value.error_code, history.value.error_code) == ("RATE_LIMITED", "RATE_LIMITED")
    assert (ticker.info_reads, len(ticker.history_calls)) == (1, 1)


@pytest.mark.asyncio
async def test_search_refused_raises_instead_of_answering_nothing(monkeypatch):
    """Search used to turn every error into ``[]``: a refusal now reaches the core; any other error still gives ``[]``."""
    _sleeping_fails(monkeypatch)
    searches: list[str] = []

    def refused(query):
        searches.append(query)
        raise YFRateLimitError()

    _install_yf(monkeypatch, search_factory=refused)
    with pytest.raises(AssetRateLimitedError):
        await YahooFinanceProvider().search("Apple")
    assert searches == ["Apple"]

    def broken(query):
        raise RuntimeError("kaboom")

    _install_yf(monkeypatch, search_factory=broken)
    assert await YahooFinanceProvider().search("Apple") == []


@pytest.mark.asyncio
async def test_metadata_refused_raises_instead_of_answering_none(monkeypatch):
    """Metadata used to turn every error into ``None``: a refusal now reaches the core, after one request."""
    _sleeping_fails(monkeypatch)
    ticker = _RefusingTicker(RuntimeError("Too Many Requests. Rate limited. Try after a while."))
    _install_yf(monkeypatch, ticker=ticker)

    with pytest.raises(AssetRateLimitedError):
        await YahooFinanceProvider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)

    assert ticker.info_reads == 1


# ── Z-32 (c): the quote currency as Yahoo reports it — contract guards, green before and after ──
#
# Yahoo quotes a London line in pence, with the currency «GBp». The price points fold it to «GBP» (Currency.validate_code)
# and keep the numbers; the history result keeps the code as reported, and the refresh stores it on the assignment for
# the data-quality warning (Z-32 (c) §4). Two guards on what that warning reads, both green today: a validator on
# FAHistoricalData.currency, or pence converted in the plugin, would each make the warning wrong without a red anywhere
# else.


def test_historical_data_keeps_the_reported_currency_as_it_is():
    """Z-32 (c) guard: ``FAHistoricalData.currency`` has no validator — ``GBp`` stays ``GBp``.

    The price points' ``currency`` folds ``GBp`` to ``GBP``; this field must not: it is the one place the minor unit
    survives, the code the refresh keeps on the assignment and the warning reads.
    """
    assert FAHistoricalData(prices=[], currency="GBp").currency == "GBp"


@pytest.mark.asyncio
async def test_history_of_a_london_line_reports_pence_while_its_points_carry_pounds(monkeypatch):
    """Z-32 (c) guard: a ticker whose ``info["currency"]`` is ``GBp``, its history as yfinance returns it — an index at
    midnight Europe/London (January: no summer time), the ``Dividends`` and ``Stock Splits`` columns beside OHLCV — gives
    a result whose ``currency`` is ``GBp`` and whose price points carry ``GBP`` with the numbers in pence as quoted.

    The numbers matter as much as the codes: the warning says «quoted in pence, set the quote base to 100»; that holds
    only while the plugin stores the pence as they come.
    """
    days = ["2026-01-05", "2026-01-06"]
    hist = pd.DataFrame(
        {
            "Open": [7230.0, 7262.0],
            "High": [7280.0, 7290.0],
            "Low": [7215.0, 7240.0],
            "Close": [7250.0, 7268.5],
            "Volume": [21_500_000, 18_250_000],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0.0, 0.0],
        },
        index=pd.DatetimeIndex(pd.to_datetime(days).tz_localize("Europe/London"), name="Date"),
    )
    _install_yf(monkeypatch, ticker=_FakeTicker(history=hist, info={"currency": "GBp", "symbol": "VOD.L"}))

    result = await YahooFinanceProvider().get_history_value("VOD.L", IdentifierType.TICKER, None, date(2026, 1, 5), date(2026, 1, 6))

    assert result.currency == "GBp"
    assert [(point.date, point.close, point.currency) for point in result.prices] == [
        (date(2026, 1, 5), Decimal("7250.0"), "GBP"),
        (date(2026, 1, 6), Decimal("7268.5"), "GBP"),
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
