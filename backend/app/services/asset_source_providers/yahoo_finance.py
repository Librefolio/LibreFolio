from __future__ import annotations
from typing import List, Dict
from datetime import date
from decimal import Decimal

try:
    import yfinance as yf
except Exception:
    yf = None

from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceProvider, CurrentValue, HistoricalData, PricePoint, AssetSourceError


@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    provider_code = "yfinance"
    provider_name = "Yahoo Finance (yfinance)"

    def validate_params(self, params: Dict) -> None:
        if not params or "ticker" not in params:
            raise AssetSourceError("Missing 'ticker' in provider_params", "INVALID_PARAMS", {"params": params})

    async def get_current_value(self, provider_params: Dict, session) -> CurrentValue:
        self.validate_params(provider_params)
        ticker = provider_params["ticker"]

        if yf is None:
            # Lightweight fallback: raise not implemented
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            t = yf.Ticker(ticker)
            info = t.history(period="1d")
            if info.empty:
                raise AssetSourceError(f"No data for ticker {ticker}", "NO_DATA")

            # Get latest close
            latest = info.iloc[-1]
            close = Decimal(str(latest["Close"]))
            return CurrentValue(value=close, currency="USD", as_of_date=date.today(), source=self.provider_code)  # type: ignore
        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(str(e), "FETCH_ERROR")

    async def get_history_value(self, provider_params: Dict, start_date: date, end_date: date, session) -> HistoricalData:
        self.validate_params(provider_params)
        ticker = provider_params["ticker"]

        if yf is None:
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            t = yf.Ticker(ticker)
            # yfinance expects strings
            hist = t.history(start=str(start_date), end=str(end_date + (end_date - start_date).resolution))
            # Fallback: if the above fails, use period
            if hist.empty:
                hist = t.history(start=str(start_date), end=str(end_date))

            prices: List[PricePoint] = []
            for idx, row in hist.iterrows():
                d = idx.date()
                prices.append(PricePoint(date=d, open=Decimal(str(row["Open"])) if not row["Open"] is None else None,
                                          high=Decimal(str(row["High"])) if not row["High"] is None else None,
                                          low=Decimal(str(row["Low"])) if not row["Low"] is None else None,
                                          close=Decimal(str(row["Close"])), currency="USD"))

            return HistoricalData(prices=prices, currency="USD", source=self.provider_code)  # type: ignore
        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(str(e), "FETCH_ERROR")

    async def search(self, query: str) -> List[Dict]:
        # Minimal implementation: use yfinance's ticker search if available
        if yf is None:
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            # yfinance doesn't expose a direct search API; use yahooquery or other in future
            # For now, simple heuristic: return query as ticker
            return [{"identifier": query.upper(), "display_name": query.upper(), "currency": "USD", "type": "STOCK"}]
        except Exception as e:
            raise AssetSourceError(str(e), "SEARCH_ERROR")

