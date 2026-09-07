"""JustETF provider — error and edge paths (no network, no DB, no server).

The live justETF happy path is covered by the network suite. Everything the
scraping library can throw at us on a bad day is covered here, by binding fakes
onto the module-level functions the provider imported (``load_live_quote``,
``load_raw_chart``, ``load_chart``, ``load_intraday_ohlc``, ``get_etf_overview``,
``load_overview``) and neutralising the live-feed thread. No socket is opened,
so every assertion is on an exact value.

Covered: library-unavailable, wrong identifier type, the EUR real-time quote
path, the USD chart-fallback path, price-not-found, fetch failures, history with
dividend events and intraday OHL enrichment, search (4 currency variants) and
its failure, param validation, and metadata assembly / failure.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType, ProviderInputType
from backend.app.services.asset_source import AssetSourceError
from backend.app.services.asset_source_providers import justetf as je
from backend.app.services.asset_source_providers.justetf import JustETFProvider

# Captured at import, before the autouse fixture swaps in the no-op stub, so the
# real function's early-return can be exercised directly.
_REAL_ENSURE_LIVE_FEED = je._ensure_live_feed


@pytest.fixture(autouse=True)
def _reset_caches_and_livefeed(monkeypatch):
    """Rebuild the module caches and stub the live-feed thread for every test."""
    je._overview_cache.clear()
    je._chart_cache.clear()
    je._etf_list_cache.clear()
    # Never start a real WebSocket thread from a unit test.
    monkeypatch.setattr(je, "_ensure_live_feed", lambda isin: None, raising=True)
    yield
    je._overview_cache.clear()
    je._chart_cache.clear()
    je._etf_list_cache.clear()


def _provider() -> JustETFProvider:
    return JustETFProvider()


# ── identity / pure helpers ─────────────────────────────────────────────────


def test_identity_and_url():
    p = _provider()
    assert p.provider_code == "justetf"
    assert p.provider_name == "JustETF"
    assert p.supports_history is True
    assert p.supports_meaningful_volume is False
    assert p.accepted_identifier_types == [ProviderInputType.ISIN]
    assert p.get_icon.startswith("https://")
    assert p.provider_help_url.startswith("/mkdocs/")
    assert p.get_asset_url("IE00B4L5Y983") == "https://www.justetf.com/en/etf-profile.html?isin=IE00B4L5Y983"
    # params_schema advertises the currency select; test_cases is non-empty
    assert p.params_schema[0]["key"] == "currency"
    assert p.test_cases
    assert p.test_search_query  # advertised query for the generic search test


def test_ensure_live_feed_early_return_when_unavailable(monkeypatch):
    # Library missing → the real feed starter returns without spawning a thread.
    monkeypatch.setattr(je, "JUSTETF_AVAILABLE", False)
    _REAL_ENSURE_LIVE_FEED("IE00B4L5Y983")  # must not raise, must not start a thread
    assert "IE00B4L5Y983" not in je._live_quote_threads


def test_get_currency_default_and_override():
    p = _provider()
    assert p._get_currency(None) == "EUR"
    assert p._get_currency({}) == "EUR"
    assert p._get_currency({"currency": "USD"}) == "USD"


# ── availability guard ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unavailable_library_raises(monkeypatch):
    monkeypatch.setattr(je, "JUSTETF_AVAILABLE", False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN)
    assert exc.value.error_code == "NOT_AVAILABLE"


# ── get_current_value ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_current_value_invalid_identifier_type():
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("AAPL", IdentifierType.TICKER)
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_current_value_eur_live_quote(monkeypatch):
    quote = SimpleNamespace(mid=101.25, last=100.0, currency="EUR", timestamp=datetime(2026, 2, 11, 15, 30))
    monkeypatch.setattr(je, "load_live_quote", lambda isin: quote, raising=False)

    result = await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "EUR"})
    assert result.value == Decimal("101.25")  # mid preferred over last
    assert result.currency == "EUR"
    assert result.as_of_date == date(2026, 2, 11)
    assert result.source == "JustETF"


@pytest.mark.asyncio
async def test_current_value_usd_chart_fallback(monkeypatch):
    raw_chart = {"latestQuote": {"raw": 123.45}, "latestQuoteDate": "2026-02-10"}
    monkeypatch.setattr(je, "load_raw_chart", lambda isin, ccy: raw_chart, raising=False)

    result = await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"})
    assert result.value == Decimal("123.45")
    assert result.currency == "USD"
    assert result.as_of_date == date(2026, 2, 10)


@pytest.mark.asyncio
async def test_current_value_not_found(monkeypatch):
    monkeypatch.setattr(je, "load_live_quote", lambda isin: None, raising=False)
    monkeypatch.setattr(je, "load_raw_chart", lambda isin, ccy: {}, raising=False)

    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "EUR"})
    assert exc.value.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_current_value_fetch_error(monkeypatch):
    def boom(isin, ccy):
        raise RuntimeError("chart backend down")

    monkeypatch.setattr(je, "load_raw_chart", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"})
    assert exc.value.error_code == "FETCH_ERROR"
    assert exc.value.details and exc.value.details["identifier"] == "IE00B4L5Y983"


# ── get_history_value ───────────────────────────────────────────────────────


def _chart_df(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    """Build a chart DataFrame shaped like load_chart's output (date index)."""
    idx = pd.to_datetime([r[0] for r in rows])
    idx.name = "date"
    return pd.DataFrame({"quote": [r[1] for r in rows], "dividends": [r[2] for r in rows]}, index=idx)


@pytest.mark.asyncio
async def test_history_invalid_identifier_type():
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("AAPL", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_history_prices_and_dividends(monkeypatch):
    df = _chart_df(
        [
            ("2026-01-05", 100.0, 0.0),
            ("2026-01-06", 101.0, 0.5),  # dividend event
            ("2026-01-07", 102.5, 0.0),
            ("2025-12-01", 90.0, 0.0),  # before range → filtered out
        ]
    )
    monkeypatch.setattr(je, "load_chart", lambda isin, ccy, add_current: df, raising=False)

    result = await _provider().get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"}, date(2026, 1, 1), date(2026, 1, 31))
    assert result.currency == "USD"
    assert [p.date for p in result.prices] == [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
    assert result.prices[0].close == Decimal("100.0")
    # exactly one dividend event, on the row whose dividends > 0
    assert len(result.events) == 1
    ev = result.events[0]
    assert ev.type == "DIVIDEND"
    assert ev.date == date(2026, 1, 6)
    assert ev.value.amount == Decimal("0.5")
    assert ev.value.code == "USD"


@pytest.mark.asyncio
async def test_history_intraday_ohl_enrichment(monkeypatch):
    today = date.today()
    df = _chart_df([((today - timedelta(days=1)).isoformat(), 100.0, 0.0), (today.isoformat(), 101.0, 0.0)])
    monkeypatch.setattr(je, "load_chart", lambda isin, ccy, add_current: df, raising=False)
    monkeypatch.setattr(
        je,
        "load_intraday_ohlc",
        lambda isin: {"date": today.isoformat(), "open": 99.0, "high": 103.0, "low": 98.5},
        raising=False,
    )

    result = await _provider().get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "EUR"}, today - timedelta(days=5), today)
    todays = next(p for p in result.prices if p.date == today)
    assert todays.open == Decimal("99.0")
    assert todays.high == Decimal("103.0")
    assert todays.low == Decimal("98.5")
    assert todays.close == Decimal("101.0")


@pytest.mark.asyncio
async def test_history_fetch_error(monkeypatch):
    def boom(isin, ccy, add_current):
        raise RuntimeError("chart 500")

    monkeypatch.setattr(je, "load_chart", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"}, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


# ── search ──────────────────────────────────────────────────────────────────


def _overview_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"name": ["iShares Core S&P 500"], "ticker": ["CSPX"], "wkn": ["A0YEDG"], "currency": ["USD"]},
        index=["IE00B5BMR087"],
    )


@pytest.mark.asyncio
async def test_search_returns_four_currency_variants(monkeypatch):
    monkeypatch.setattr(je, "load_overview", lambda: _overview_df(), raising=False)

    items = await _provider().search("S&P 500")
    assert len(items) == len(JustETFProvider.SUPPORTED_CURRENCIES)
    assert {it["currency"] for it in items} == set(JustETFProvider.SUPPORTED_CURRENCIES)
    assert all(it["identifier"] == "IE00B5BMR087" for it in items)
    assert all(it["identifier_type"] == IdentifierType.ISIN for it in items)
    # Exactly one variant carries the crown — the fund's native currency (USD).
    crowned = [it for it in items if "👑" in it["display_name"]]
    assert len(crowned) == 1
    assert crowned[0]["currency"] == "USD"


@pytest.mark.asyncio
async def test_search_error(monkeypatch):
    def boom():
        raise RuntimeError("overview download failed")

    monkeypatch.setattr(je, "load_overview", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().search("anything")
    assert exc.value.error_code == "SEARCH_ERROR"


# ── validate_params ─────────────────────────────────────────────────────────


def test_validate_params_accepts_none_and_supported():
    p = _provider()
    p.validate_params(None)  # no-op
    p.validate_params({"currency": "USD"})  # supported → no raise


def test_validate_params_rejects_unsupported():
    with pytest.raises(AssetSourceError) as exc:
        _provider().validate_params({"currency": "JPY"})
    assert exc.value.error_code == "INVALID_PARAMS"


# ── fetch_asset_metadata ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_non_isin_returns_none():
    result = await _provider().fetch_asset_metadata("AAPL", IdentifierType.TICKER)
    assert result is None


@pytest.mark.asyncio
async def test_metadata_happy(monkeypatch):
    overview = {
        "description": "Tracks the MSCI World index.",
        "ter": 0.2,
        "distribution_policy": "Accumulating",
        "ticker": "IWDA",
        "countries": [
            {"name": "United States", "percentage": 60},
            {"name": "Other", "percentage": 40},
        ],
        "sectors": [
            {"name": "Technology", "percentage": 30},
            {"name": "Technology", "percentage": 10},  # accumulate branch
            {"name": "Health Care", "percentage": 60},
        ],
    }
    monkeypatch.setattr(je, "get_etf_overview", lambda isin, include_gettex=False: overview, raising=False)

    result = await _provider().fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "CHF"})
    assert result is not None
    assert result.asset_type == AssetType.ETF
    assert result.currency == "CHF"  # user's chosen currency, not fund NAV currency
    assert result.identifier_isin == "IE00B4L5Y983"
    assert result.identifier_ticker == "IWDA"
    sd = result.classification_params.short_description
    assert "TER: 0.2%" in sd and "Distribution: Accumulating" in sd
    assert result.classification_params.geographic_area is not None
    assert result.classification_params.sector_area is not None


@pytest.mark.asyncio
async def test_metadata_exception_returns_none(monkeypatch):
    def boom(isin, include_gettex=False):
        raise RuntimeError("overview parse error")

    monkeypatch.setattr(je, "get_etf_overview", boom, raising=False)
    result = await _provider().fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN)
    assert result is None


# ── cache-hit and remaining edge branches ───────────────────────────────────


@pytest.mark.asyncio
async def test_etf_list_and_overview_cache_hit(monkeypatch):
    """Second call to a cached path must not re-invoke the scraping library."""
    overview_calls = {"n": 0}

    def counting_overview():
        overview_calls["n"] += 1
        return _overview_df()

    monkeypatch.setattr(je, "load_overview", counting_overview, raising=False)
    await _provider().search("S&P 500")
    await _provider().search("S&P 500")
    assert overview_calls["n"] == 1  # second search hit the etf_list cache


@pytest.mark.asyncio
async def test_current_value_store_hit_then_chart_when_price_unusable(monkeypatch):
    """A live quote already in the store is used; if it has no usable price the
    provider falls through to the daily chart quote."""
    dead_quote = SimpleNamespace(mid=None, last=None, currency="EUR", timestamp=None)
    monkeypatch.setitem(je._live_quote_store, "IE00B4L5Y983", dead_quote)

    def load_live_quote_should_not_run(isin):  # store hit → must not be called
        raise AssertionError("load_live_quote called despite store hit")

    monkeypatch.setattr(je, "load_live_quote", load_live_quote_should_not_run, raising=False)
    monkeypatch.setattr(je, "load_raw_chart", lambda isin, ccy: {"latestQuote": {"raw": 55.5}}, raising=False)

    result = await _provider().get_current_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "EUR"})
    # chart fallback supplied the price; with no latestQuoteDate, as_of stays today
    assert result.value == Decimal("55.5")
    assert result.as_of_date == date.today()


@pytest.mark.asyncio
async def test_history_cache_hit_and_no_dividend_column(monkeypatch):
    idx = pd.to_datetime(["2026-01-05", "2026-01-06"])
    idx.name = "date"
    df = pd.DataFrame({"quote": [100.0, 101.0]}, index=idx)  # no 'dividends' column
    calls = {"n": 0}

    def counting_chart(isin, ccy, add_current):
        calls["n"] += 1
        return df

    monkeypatch.setattr(je, "load_chart", counting_chart, raising=False)
    p = _provider()
    r1 = await p.get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"}, date(2026, 1, 1), date(2026, 1, 31))
    r2 = await p.get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "USD"}, date(2026, 1, 1), date(2026, 1, 31))
    assert calls["n"] == 1  # second call served from cache
    assert r1.events == [] and r2.events == []  # no dividend column → no events
    assert len(r1.prices) == 2


@pytest.mark.asyncio
async def test_history_intraday_error_is_swallowed(monkeypatch):
    today = date.today()
    df = _chart_df([(today.isoformat(), 101.0, 0.0)])
    monkeypatch.setattr(je, "load_chart", lambda isin, ccy, add_current: df, raising=False)

    def boom(isin):
        raise RuntimeError("intraday feed down")

    monkeypatch.setattr(je, "load_intraday_ohlc", boom, raising=False)
    # The intraday failure is logged and swallowed; the daily close survives.
    result = await _provider().get_history_value("IE00B4L5Y983", IdentifierType.ISIN, {"currency": "EUR"}, today - timedelta(days=3), today)
    pt = next(p for p in result.prices if p.date == today)
    assert pt.close == Decimal("101.0")
    assert pt.open is None  # enrichment did not happen


@pytest.mark.asyncio
async def test_metadata_minimal_overview(monkeypatch):
    """An overview with no optional fields yields a patch with empty classification.

    Also exercises the overview cache: the second call must not re-scrape.
    """
    calls = {"n": 0}

    def counting_overview(isin, include_gettex=False):
        calls["n"] += 1
        return {}

    monkeypatch.setattr(je, "get_etf_overview", counting_overview, raising=False)
    p = _provider()
    result = await p.fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN)
    await p.fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN)  # cache hit
    assert calls["n"] == 1
    assert result is not None
    assert result.classification_params.short_description is None
    assert result.classification_params.geographic_area is None
    assert result.classification_params.sector_area is None
    assert result.identifier_ticker is None


@pytest.mark.asyncio
async def test_metadata_long_description_truncated(monkeypatch):
    long_desc = "x" * 600
    monkeypatch.setattr(je, "get_etf_overview", lambda isin, include_gettex=False: {"description": long_desc}, raising=False)
    result = await _provider().fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN)
    sd = result.classification_params.short_description
    assert len(sd) == 500 and sd.endswith("...")


@pytest.mark.asyncio
async def test_metadata_unknown_sector_maps_to_other(monkeypatch):
    overview = {"sectors": [{"name": "Definitely Not A Real Sector", "percentage": 100}]}
    monkeypatch.setattr(je, "get_etf_overview", lambda isin, include_gettex=False: overview, raising=False)
    # Unknown sector triggers the warn-and-map branch; still produces a sector area.
    result = await _provider().fetch_asset_metadata("IE00B4L5Y983", IdentifierType.ISIN)
    assert result is not None
    assert result.classification_params.sector_area is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
