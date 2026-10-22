"""Yahoo Finance provider — fund metadata from ``Ticker.funds_data`` (no network, no DB, no server).

Lot #50: for an ETF or a mutual fund (``quoteType`` ``etf`` / ``mutualfund``) ``fetch_asset_metadata`` reads the fund's
data besides ``info``: the sector weightings into ``classification_params.sector_area``, the fund's own description when
``longBusinessSummary`` is missing, and «TER: x%» and the issuer at the end of the description. The ``yf`` module the
provider imported is replaced by a fake whose ``Ticker`` carries a fake ``funds_data`` shaped as yfinance 1.7.0 returns
it (sector keys with underscores, the expense ratio as a fraction, ``None`` for what Yahoo does not know, as for
VWCE.DE). A missing piece of fund data never fails the metadata; a «too many requests» refusal still leaves at once.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest
from structlog.testing import capture_logs

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers.yahoo_finance import plugin as yfp
from backend.app.services.asset_source_providers.yahoo_finance.plugin import YahooFinanceProvider
from backend.app.services.assets.base import AssetRateLimitedError

# Yahoo's eleven sectors as ``sector_weightings`` returns them (VOO, rounded), the keys with underscores.
YAHOO_SECTORS = {
    "realestate": 0.02,
    "consumer_cyclical": 0.09,
    "basic_materials": 0.02,
    "consumer_defensive": 0.04,
    "technology": 0.40,
    "communication_services": 0.10,
    "financial_services": 0.11,
    "utilities": 0.02,
    "industrials": 0.08,
    "energy": 0.03,
    "healthcare": 0.09,
}


class _FakeFundsData:
    """``funds_data`` as yfinance 1.7.0 shapes it; a value of ``Exception`` instance is raised when read."""

    def __init__(self, *, sectors=None, expense_ratio=None, family=None, description="", reads: list[str] | None = None):
        self._sectors = sectors if sectors is not None else {}
        self._expense_ratio = expense_ratio
        self._family = family
        self._description = description
        self.reads = reads if reads is not None else []

    @property
    def sector_weightings(self):
        self.reads.append("sector_weightings")
        if isinstance(self._sectors, Exception):
            raise self._sectors
        return self._sectors

    @property
    def fund_operations(self):
        self.reads.append("fund_operations")
        value = pd.NA if self._expense_ratio is None else self._expense_ratio
        return pd.DataFrame({"Attributes": ["Annual Report Expense Ratio"], "FUND": [value], "Category Average": [pd.NA]}).set_index("Attributes")

    @property
    def fund_overview(self):
        self.reads.append("fund_overview")
        return {"categoryName": None, "family": self._family, "legalType": "Exchange Traded Fund"}

    @property
    def description(self):
        self.reads.append("description")
        return self._description


class _FakeTicker:
    def __init__(self, *, info, funds_data=None, funds_data_exc=None, isin=None):
        self._info = info
        self._funds_data = funds_data
        self._funds_data_exc = funds_data_exc
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
        if self._funds_data_exc is not None:
            raise self._funds_data_exc
        return self._funds_data


def _install(monkeypatch, ticker):
    monkeypatch.setattr(yfp, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yfp, "pd", pd)
    monkeypatch.setattr(yfp, "yf", SimpleNamespace(Ticker=lambda symbol: ticker, Search=lambda query: SimpleNamespace(quotes=[])))


def _etf_info(**extra):
    return {"quoteType": "ETF", "currency": "EUR", "symbol": "VWCE.DE", "longName": "Vanguard FTSE All-World UCITS ETF", **extra}


async def _metadata(monkeypatch, ticker):
    _install(monkeypatch, ticker)
    return await YahooFinanceProvider().fetch_asset_metadata("VWCE.DE", IdentifierType.TICKER)


@pytest.mark.asyncio
async def test_fund_sectors_are_mapped_to_the_standard_sectors_and_sum_to_one(monkeypatch):
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(sectors=YAHOO_SECTORS, family="Vanguard"))

    result = await _metadata(monkeypatch, ticker)

    distribution = result.classification_params.sector_area.distribution
    # Every Yahoo key lands on a standard sector, none in «Other» (Yahoo spells them with underscores).
    assert set(distribution) == {
        "Real Estate",
        "Consumer Discretionary",
        "Basic Materials",
        "Consumer Staples",
        "Technology",
        "Telecommunication",
        "Financials",
        "Utilities",
        "Industrials",
        "Energy",
        "Health Care",
    }
    assert sum(distribution.values()) == Decimal("1")
    # The weights are renormalised, not taken raw: Yahoo's eleven sum to 1.00 here, but the shares keep their ratio.
    assert distribution["Technology"] == Decimal("0.40")


@pytest.mark.asyncio
async def test_fund_sector_weights_with_float_noise_are_renormalised(monkeypatch):
    noisy = {"technology": 0.317, "healthcare": 0.083500005, "energy": 0.0398}  # sums to 0.4403, as Yahoo's rounding does
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(sectors=noisy))

    result = await _metadata(monkeypatch, ticker)

    distribution = result.classification_params.sector_area.distribution
    assert sum(distribution.values()) == Decimal("1")
    assert distribution["Technology"] > Decimal("0.7")


@pytest.mark.asyncio
async def test_fund_unknown_sector_key_goes_to_other_with_a_warning(monkeypatch):
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(sectors={"technology": 0.9, "space_mining": 0.1}))

    with capture_logs() as logs:
        result = await _metadata(monkeypatch, ticker)

    distribution = result.classification_params.sector_area.distribution
    assert distribution["Other"] == Decimal("0.1")
    assert any("sector" in str(entry.get("event", "")).lower() and entry.get("log_level") == "warning" for entry in logs)


@pytest.mark.asyncio
async def test_fund_description_gets_ter_and_issuer_after_the_summary(monkeypatch):
    info = _etf_info(longBusinessSummary="Tracks the S&P 500.")
    ticker = _FakeTicker(info=info, funds_data=_FakeFundsData(sectors=YAHOO_SECTORS, expense_ratio=0.00029999999, family="Vanguard"))

    result = await _metadata(monkeypatch, ticker)

    # The ratio is a fraction (0.0003 = 0.03 %), shown as a percentage rounded to two decimals.
    assert result.classification_params.short_description == "Tracks the S&P 500. | TER: 0.03% | Issuer: Vanguard"


@pytest.mark.asyncio
async def test_fund_without_ter_like_vwce_keeps_the_issuer_and_the_fund_description(monkeypatch):
    # VWCE.DE: no TER, an empty description, but an issuer and the sectors.
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(sectors=YAHOO_SECTORS, expense_ratio=None, family="Vanguard Group (Ireland) Limited", description=""))

    result = await _metadata(monkeypatch, ticker)

    description = result.classification_params.short_description
    assert "TER" not in description
    # No summary and no fund description: the name stays, as for any asset, with the issuer after it.
    assert description == "Vanguard FTSE All-World UCITS ETF | Issuer: Vanguard Group (Ireland) Limited"
    assert result.classification_params.sector_area is not None


@pytest.mark.asyncio
async def test_fund_description_replaces_the_name_when_the_summary_is_missing(monkeypatch):
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(sectors={}, expense_ratio=0.0022, family="iShares", description="Invests in world equities."))

    result = await _metadata(monkeypatch, ticker)

    assert result.classification_params.short_description == "Invests in world equities. | TER: 0.22% | Issuer: iShares"


@pytest.mark.asyncio
async def test_fund_summary_wins_over_the_fund_description(monkeypatch):
    info = _etf_info(longBusinessSummary="From the quote summary.")
    ticker = _FakeTicker(info=info, funds_data=_FakeFundsData(description="From the fund profile.", family="X"))

    result = await _metadata(monkeypatch, ticker)

    assert result.classification_params.short_description.startswith("From the quote summary.")
    assert "From the fund profile." not in result.classification_params.short_description


@pytest.mark.asyncio
async def test_fund_long_summary_is_cut_but_ter_and_issuer_survive_within_500_characters(monkeypatch):
    info = _etf_info(longBusinessSummary="y" * 600)
    ticker = _FakeTicker(info=info, funds_data=_FakeFundsData(expense_ratio=0.0007, family="Vanguard"))

    result = await _metadata(monkeypatch, ticker)

    description = result.classification_params.short_description
    assert len(description) <= 500
    assert description.endswith(" | TER: 0.07% | Issuer: Vanguard")
    assert description.startswith("yyyy")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_ratio", [float("nan"), 0, -0.1])
async def test_fund_unusable_ter_is_left_out(monkeypatch, bad_ratio):
    ticker = _FakeTicker(info=_etf_info(), funds_data=_FakeFundsData(expense_ratio=bad_ratio, family="Vanguard"))

    result = await _metadata(monkeypatch, ticker)

    assert "TER" not in result.classification_params.short_description
    assert result.classification_params.short_description.endswith("| Issuer: Vanguard")


@pytest.mark.asyncio
async def test_mutual_fund_is_read_like_an_etf(monkeypatch):
    info = {"quoteType": "MUTUALFUND", "currency": "USD", "symbol": "VFIAX", "longName": "Vanguard 500 Index Admiral"}
    ticker = _FakeTicker(info=info, funds_data=_FakeFundsData(sectors=YAHOO_SECTORS, expense_ratio=0.0004, family="Vanguard"))

    result = await _metadata(monkeypatch, ticker)

    assert result.asset_type == "FUND"
    assert result.classification_params.sector_area is not None
    assert "TER: 0.04%" in result.classification_params.short_description


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [KeyError("topHoldings"), ValueError("No Fund data found."), AttributeError("funds_data"), RuntimeError("boom")])
async def test_fund_without_data_still_returns_the_metadata(monkeypatch, exc):
    ticker = _FakeTicker(info=_etf_info(longBusinessSummary="A fund."), funds_data_exc=exc)

    result = await _metadata(monkeypatch, ticker)

    assert result is not None
    assert result.asset_type == "ETF"
    assert result.classification_params.short_description == "A fund."
    assert result.classification_params.sector_area is None


@pytest.mark.asyncio
async def test_fund_whose_sectors_fail_keeps_ter_and_issuer(monkeypatch):
    funds_data = _FakeFundsData(sectors=RuntimeError("no sectors"), expense_ratio=0.0022, family="iShares")
    ticker = _FakeTicker(info=_etf_info(longBusinessSummary="A fund."), funds_data=funds_data)

    result = await _metadata(monkeypatch, ticker)

    assert result.classification_params.sector_area is None
    assert result.classification_params.short_description == "A fund. | TER: 0.22% | Issuer: iShares"


@pytest.mark.asyncio
async def test_fund_data_refusal_for_too_many_requests_leaves_at_once(monkeypatch):
    ticker = _FakeTicker(info=_etf_info(), funds_data_exc=RuntimeError("429 Too Many Requests"))

    with pytest.raises(AssetRateLimitedError):
        await _metadata(monkeypatch, ticker)


@pytest.mark.asyncio
async def test_equity_is_unchanged_and_never_reads_fund_data(monkeypatch):
    info = {"quoteType": "EQUITY", "currency": "USD", "symbol": "AAPL", "longBusinessSummary": "y" * 600, "sector": "Technology"}
    ticker = _FakeTicker(info=info, funds_data=_FakeFundsData(sectors=YAHOO_SECTORS, expense_ratio=0.5, family="Nobody"))

    result = await _metadata(monkeypatch, ticker)

    assert ticker.funds_data_reads == 0
    assert result.classification_params.short_description == "y" * 500
    assert result.classification_params.sector_area.distribution == {"Technology": Decimal("1.0")}
