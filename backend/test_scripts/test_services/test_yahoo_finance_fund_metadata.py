"""Yahoo Finance provider — a fund's metadata reads no fund data (no network, no DB, no server).

Lot #50 read ``Ticker.funds_data`` for an ETF or a mutual fund: the sector weightings into
``classification_params.sector_area``, the fund's own description, «TER: x%» and the issuer. Plan 68, lot D6: the
description, countries and sectors of an asset are its profile, which the enrichers read (the Yahoo enricher reads the
same fund data); the price provider gives none of them. So ``fetch_asset_metadata`` never reads ``funds_data`` any more,
for any type of asset: four calls to Yahoo fewer for each fund, and no ``classification_params``.

The ``yf`` module the provider imported is replaced by a fake whose ``Ticker`` counts the reads of ``funds_data``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider


class _FakeTicker:
    """``info`` and ``isin`` as given; ``funds_data`` counts its reads and fails, as a fund Yahoo has no data for."""

    def __init__(self, *, info, isin=None):
        self._info = info
        self._isin = isin
        self.funds_data_reads = 0

    @property
    def info(self):
        return self._info

    @property
    def isin(self):
        return self._isin

    @property
    def funds_data(self):
        self.funds_data_reads += 1
        raise AssertionError("funds_data read by the price provider")


def _install(monkeypatch, ticker):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "pd", pd)
    monkeypatch.setattr(yfp, "yf", SimpleNamespace(Ticker=lambda symbol: ticker, Search=lambda query: SimpleNamespace(quotes=[])))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("quote_type", "asset_type"),
    [("ETF", "ETF"), ("MUTUALFUND", "FUND"), ("EQUITY", "STOCK")],
)
async def test_metadata_reads_no_fund_data_and_gives_no_classification(monkeypatch, quote_type, asset_type):
    info = {"quoteType": quote_type, "currency": "EUR", "symbol": "VWCE.DE", "longName": "Vanguard FTSE All-World UCITS ETF", "longBusinessSummary": "A fund.", "sector": "Technology"}
    ticker = _FakeTicker(info=info, isin="IE00BK5BQT80")
    _install(monkeypatch, ticker)

    result = await YahooFinanceProvider().fetch_asset_metadata("VWCE.DE", IdentifierType.TICKER)

    assert result is not None
    assert (result.asset_type, result.currency, result.identifier_ticker, result.identifier_isin) == (asset_type, "EUR", "VWCE.DE", "IE00BK5BQT80")
    assert ticker.funds_data_reads == 0, "the fund data are the enricher's"
    assert result.classification_params is None
