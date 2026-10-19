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
and search and metadata no longer turn it into ``[]`` / ``None``. The Z-33
cases (N86) build their frames as yfinance 1.7.0 stamps them — midnight in the
exchange's timezone — and pin the exchange-day dating of the history and of
the current value, and the warning the plugin gives, once per zone, on a host
without a timezone database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import pytest
import structlog
from structlog.testing import capture_logs
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


def _exchange_midnights(days: list[str], tz: str | None) -> pd.DatetimeIndex:
    """``days`` stamped as yfinance 1.7.0 stamps a daily series (``scrapers/history.py``): midnight in the exchange's
    timezone, its DST edges resolved as yfinance resolves them (``ambiguous=True``: the first of two midnights;
    ``nonexistent="shift_forward"``: the first instant after a midnight the clocks skip). ``tz`` None: a tz-naive index."""
    index = pd.to_datetime(days)
    if tz is not None:
        index = index.tz_localize(tz, ambiguous=True, nonexistent="shift_forward")
    return pd.DatetimeIndex(index, name="Date")


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
async def test_history_finite_range_uses_exclusive_remote_end_and_inclusive_exchange_dates(monkeypatch):
    """A finite range asks yfinance up to the day after ``end`` (its ``end`` is exclusive) and keeps the bars of the
    exchange days from ``start`` to ``end``, both included, the days around them dropped.

    Z-33 (N86 §1) rewrites this test: it pinned the UTC rule (a bar at 20:00 -05:00 counted for the next UTC day), which
    the contract replaces with the exchange's own calendar. The bars are now stamped as yfinance stamps them, at midnight
    in Milan. Red until Z-33: read in UTC each Milan bar is a day early, so the closes kept are those of the next day
    (110 and 120 instead of 100 and 110).
    """
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
        # 2026-01-01 outside, 2026-01-02 the start, 2026-01-03 the end, 2026-01-04 outside
        index=_exchange_midnights(["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"], "Europe/Rome"),
    )
    ticker = _FakeTicker(history=hist, info={"currency": "EUR"})
    _install_yf(monkeypatch, ticker=ticker)

    result = await YahooFinanceProvider().get_history_value("ENI.MI", IdentifierType.TICKER, None, requested_start, requested_end)

    assert ticker.history_calls == [{"start": "2026-01-02", "end": "2026-01-04"}]
    assert [(point.date, point.close) for point in result.prices] == [(requested_start, Decimal("100.0")), (requested_end, Decimal("110.0"))], "each Milan bar must count for its own exchange day"


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


# ── Z-33: each bar, dividend and split on its exchange's own day (decision N86) ──
#
# yfinance 1.7.0 (``scrapers/history.py``) re-stamps every daily quote, dividend and split at midnight in the exchange's
# timezone (``_exchange_midnights``). The plugin read that midnight in UTC (``tz_convert("UTC").date()``): the day before
# for every exchange east of UTC — Milan all year, London in summer time, Tokyo —, right for New York and a 24/7 UTC line.
# N86 §1: each index value is dated on its own wall calendar (a tz-naive one by ``.date()``); the current value dates
# ``regularMarketTime`` in the timezone of ``info["exchangeTimezoneName"]``, in UTC when that is missing or unknown.
#
# Red on HEAD 22b9b90ce: the plugin reads the dates in UTC, and a tz-naive index fails the whole history (a pandas
# ``Timestamp`` always has ``tz_convert``, which refuses a naive one, so the plugin's own ``.date()`` branch is never
# reached: FETCH_ERROR). The cases named ``-guard`` are green before and after: the contract must not move them.


def _z33_ticker(days: list[str], tz: str | None, info: dict) -> _FakeTicker:
    """A ticker answering as yfinance 1.7.0 does for ``days`` on an exchange of ``tz``: the daily frame (OHLCV, then
    ``Dividends`` and ``Stock Splits``), a 0.5 dividend on the first day and a 2:1 split on the last, all stamped alike."""
    closes = [100.0 + 10 * position for position in range(len(days))]
    index = _exchange_midnights(days, tz)
    hist = pd.DataFrame(
        {
            "Open": [close - 1 for close in closes],
            "High": [close + 1 for close in closes],
            "Low": [close - 2 for close in closes],
            "Close": closes,
            "Volume": [1000 + position for position in range(len(days))],
            "Dividends": [0.5] + [0.0] * (len(days) - 1),
            "Stock Splits": [0.0] * (len(days) - 1) + [2.0],
        },
        index=index,
    )
    dividends = pd.Series([0.5], index=_exchange_midnights(days[:1], tz), name="Dividends")
    splits = pd.Series([2.0], index=_exchange_midnights(days[-1:], tz), name="Stock Splits")
    return _FakeTicker(history=hist, info=info, dividends=dividends, splits=splits)


async def _z33_history(monkeypatch, days: list[str], tz: str | None, info: dict) -> FAHistoricalData:
    """The plugin's history of ``days`` (a week of margin each side, so a day read early or late is still in range)."""
    _install_yf(monkeypatch, ticker=_z33_ticker(days, tz, info))
    start, end = date.fromisoformat(days[0]) - timedelta(days=7), date.fromisoformat(days[-1]) + timedelta(days=7)
    return await YahooFinanceProvider().get_history_value("Z33", IdentifierType.TICKER, None, start, end)


@pytest.mark.parametrize(
    ("tz", "days"),
    [
        pytest.param("Europe/Rome", ["2025-07-14", "2025-07-15"], id="milan-july"),
        pytest.param("Europe/Rome", ["2026-01-12", "2026-01-13"], id="milan-january"),
        pytest.param("Europe/London", ["2025-07-14", "2025-07-15"], id="london-july"),
        pytest.param("Europe/London", ["2026-01-12", "2026-01-13"], id="london-january-guard"),
        # Friday in GMT, then Monday 2025-03-31, the first in BST
        pytest.param("Europe/London", ["2025-03-28", "2025-03-31"], id="london-spring-dst-monday-2025-03-31"),
        # Friday 2025-10-24, the last in BST, then Monday 2025-10-27 in GMT
        pytest.param("Europe/London", ["2025-10-24", "2025-10-27"], id="london-autumn-dst-2025-10-24-and-27"),
        pytest.param("Asia/Tokyo", ["2025-07-14", "2025-07-15"], id="tokyo"),
        # Sunday 2025-03-30 has no midnight in Beirut (00:00 → 01:00): yfinance stamps it 01:00, still that Sunday
        pytest.param("Asia/Beirut", ["2025-03-28", "2025-03-30"], id="beirut-skipped-midnight"),
        pytest.param("America/New_York", ["2025-07-14", "2025-07-15"], id="new-york-guard"),
        # A Saturday and a Sunday: a line that trades every day, on UTC
        pytest.param("UTC", ["2025-07-12", "2025-07-13"], id="utc-24-7-guard"),
        pytest.param(None, ["2025-07-14", "2025-07-15"], id="tz-naive"),
    ],
)
@pytest.mark.asyncio
async def test_z33_history_dates_each_bar_and_event_on_its_exchange_day(monkeypatch, tz, days):
    """Z-33 (N86 §1): a history as yfinance 1.7.0 stamps it gives every price point, the dividend and the split the
    exchange day they were stamped on, whatever the zone and its DST edges; a tz-naive index gives its own dates.

    Red until Z-33 for every zone east of UTC: read in UTC, each day is the day before (Milan all year, London in summer
    time only — around both 2025 changes one of the two days moves, the other does not —, Tokyo, Beirut). Red for the
    tz-naive index too: the plugin fails the whole history (FETCH_ERROR, «Cannot convert tz-naive Timestamp»). The
    ``-guard`` cases are green before and after.
    """
    result = await _z33_history(monkeypatch, days, tz, {"currency": "EUR"})

    exchange_days = [date.fromisoformat(day) for day in days]
    assert [point.date for point in result.prices] == exchange_days, f"each bar must be dated on its exchange day {exchange_days}"
    assert sorted((event.date, str(event.type)) for event in result.events) == [(exchange_days[0], "DIVIDEND"), (exchange_days[-1], "SPLIT")], "the dividend and the split must be dated as the bars they were stamped with"


_Z33_SYDNEY_MORNING = datetime(2026, 1, 14, 23, 30, tzinfo=UTC)  # 10:30 on Thursday 2026-01-15 in Sydney (AEDT, +11)


@pytest.mark.parametrize(
    ("info_tz", "expected"),
    [
        pytest.param("Australia/Sydney", date(2026, 1, 15), id="sydney-the-next-day"),
        pytest.param(None, date(2026, 1, 14), id="unknown-zone-utc-guard"),
    ],
)
@pytest.mark.asyncio
async def test_z33_current_value_is_dated_in_the_exchange_timezone(monkeypatch, info_tz, expected):
    """Z-33 (N86 §1): ``regularMarketTime`` 23:30 UTC is 10:30 the next day in Sydney: the current value is dated that
    next day, the exchange's; with no ``exchangeTimezoneName`` it is dated in UTC (the guard, green before and after).

    Red until Z-33 for Sydney: the plugin dates the instant by UTC, the day before.
    """
    info = {"regularMarketPrice": 8.5, "currency": "AUD", "regularMarketTime": int(_Z33_SYDNEY_MORNING.timestamp())} | ({"exchangeTimezoneName": info_tz} if info_tz else {})
    _install_yf(monkeypatch, ticker=_FakeTicker(info=info))

    result = await YahooFinanceProvider().get_current_value("Z33.AX", IdentifierType.TICKER)

    assert result.as_of_date == expected


# ── Z-33 follow-up 3 (H's review, LOW): a host without a timezone database says so ──
#
# Without a timezone database (no system zoneinfo, no ``tzdata`` package) ``ZoneInfo`` raises ``ZoneInfoNotFoundError``
# for every name: the plugin's ``_exchange_zone`` gives None for all of them, and every current value is dated in UTC
# instead of on its exchange's day, without a word. As approved: ``_exchange_zone(name)``, a private helper of the plugin
# module since Z-33r (D3/D4), logs a warning naming the zone (``timezone=``), once per name and process, when
# ``ZoneInfo`` raises ``ZoneInfoNotFoundError`` for an Area/Location name (one with a "/", ``Europe/Rome``), and still
# gives None; nothing is logged for a fixed offset or another name without a "/" (``UTC+02:00``, ``legacy-utc``), an
# empty name, or a known zone. The names already logged are the plugin's ``_UNKNOWN_ZONES_LOGGED``, a module-level set
# each test empties (``raising=False``: it does not exist before Z-33r). The missing database is the plugin's own
# ``ZoneInfo``, imported at the module's top, patched to raise; the log is read with ``capture_logs``, behind a barrier.
# The level and the ``timezone`` the event carries are pinned, never its wording.
#
# Red on HEAD 97fe88996: the plugin has no ``_exchange_zone`` yet; each test fails on that first (``_z33_exchange_zone``).

_Z33_ZONE_LOG_CANARY = "Z-33 test: canary through a logger of the Yahoo plugin's name"


def _z33_exchange_zone():
    """The plugin's ``_exchange_zone`` (Z-33r, D3/D4); until the plugin has it the test fails here, before any patch."""
    zone_of = getattr(yfp, "_exchange_zone", None)
    if zone_of is None:
        pytest.fail("red until Z-33r: the Yahoo plugin has no _exchange_zone (D3/D4: the exchange's zone and the warning for an unknown one become the plugin's own)", pytrace=False)
    return zone_of


def _z33_no_zone_logged_yet(monkeypatch) -> None:
    """No zone name logged yet in this process: the plugin's ``_UNKNOWN_ZONES_LOGGED`` an empty set for the test."""
    monkeypatch.setattr(yfp, "_UNKNOWN_ZONES_LOGGED", set(), raising=False)


def _z33_no_zone_database(monkeypatch) -> None:
    """A host without a timezone database: ``ZoneInfo``, as the plugin calls it, raises ``ZoneInfoNotFoundError`` for every
    name, as it does when neither the system nor the ``tzdata`` package has one. The plugin imports ``ZoneInfo`` at its
    module's top (D4); where it does not, the test fails here: there is no database to take away."""
    if not hasattr(yfp, "ZoneInfo"):
        pytest.fail("red until Z-33r: the Yahoo plugin imports no ZoneInfo at its module's top (D4), so the test cannot take the timezone database away", pytrace=False)

    def no_zone(key: str) -> ZoneInfo:
        raise ZoneInfoNotFoundError(f"No time zone found with key {key}")

    monkeypatch.setattr(yfp, "ZoneInfo", no_zone)


@contextmanager
def _z33_zone_log() -> Iterator[list[dict]]:
    """What is logged inside the block, behind a barrier: a warning sent through a logger of the plugin module's own name
    reaches the capture first — else a warning missing from it would prove nothing."""
    with capture_logs() as logs:
        structlog.get_logger(yfp.__name__).warning(_Z33_ZONE_LOG_CANARY)
        assert [entry.get("event") for entry in logs] == [_Z33_ZONE_LOG_CANARY], f"barrier: a logger of {yfp.__name__}'s name does not reach capture_logs: {logs}"
        yield logs


def _z33_zone_warnings(logs: list[dict]) -> list[tuple[object, object]]:
    """``(level, timezone)`` of each warning or worse captured, in order, the barrier's canary aside."""
    return [(entry.get("log_level"), entry.get("timezone")) for entry in logs if entry.get("log_level") in ("warning", "error", "critical") and entry.get("event") != _Z33_ZONE_LOG_CANARY]


def test_z33_an_unknown_area_zone_is_logged_once(monkeypatch):
    """Z-33 (H's review, LOW; the plugin's own since Z-33r): without a timezone database, ``_exchange_zone("Europe/Rome")``
    gives None and one warning naming the zone (``timezone="Europe/Rome"``); the same name again, None and no other
    warning; then ``_exchange_zone("Asia/Tokyo")``, None and one more warning, naming Tokyo — once per name, not once in
    all. A warning: neither silence nor an error; its wording free.

    Red on HEAD 97fe88996: the plugin has no ``_exchange_zone``.
    """
    zone_of = _z33_exchange_zone()
    _z33_no_zone_logged_yet(monkeypatch)
    _z33_no_zone_database(monkeypatch)

    with _z33_zone_log() as logs:
        rome = zone_of("Europe/Rome")
        first = _z33_zone_warnings(logs)
        again = zone_of("Europe/Rome")
        second = _z33_zone_warnings(logs)
        tokyo = zone_of("Asia/Tokyo")
        third = _z33_zone_warnings(logs)

    assert (rome, again, tokyo) == (None, None, None), f"without a timezone database no zone is given, as before: {(rome, again, tokyo)}"
    assert first == [("warning", "Europe/Rome")], f"an Area/Location name ZoneInfo cannot find must be logged as one warning naming it: (level, timezone) {first}"
    assert second == first, f"the same name must not be logged again in the process: (level, timezone) {second}"
    assert third == [("warning", "Europe/Rome"), ("warning", "Asia/Tokyo")], f"another name must be logged too, once: (level, timezone) {third}"


def test_z33_an_unknown_name_without_area_is_not_logged(monkeypatch):
    """Z-33 (H's review, LOW, the other side; the plugin's own since Z-33r): the warning is for an Area/Location name
    alone. A known zone gives its ``ZoneInfo`` and no warning; then, without a timezone database, a fixed offset
    (``UTC+02:00``), ``legacy-utc`` (no mark any more: a name without an area like any other), an empty name and None
    give None and no warning either.

    Red on HEAD 97fe88996: the plugin has no ``_exchange_zone``. Green once it has, and must stay green.
    """
    zone_of = _z33_exchange_zone()
    _z33_no_zone_logged_yet(monkeypatch)
    names = ("UTC+02:00", "legacy-utc", "", None)

    with _z33_zone_log() as logs:
        known = zone_of("Europe/Rome")
        _z33_no_zone_database(monkeypatch)
        unknown = {name: zone_of(name) for name in names}

    assert isinstance(known, ZoneInfo) and known.key == "Europe/Rome", f"a known zone gives its ZoneInfo: {known!r}"
    assert unknown == dict.fromkeys(names), f"no zone for these names: {unknown}"
    assert _z33_zone_warnings(logs) == [], f"nothing may be logged for a known zone, a name without a '/' or an empty name: (level, timezone) {_z33_zone_warnings(logs)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
