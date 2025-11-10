from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Dict

try:
    import yfinance as yf
except Exception:
    yf = None

from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError


@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    provider_code = "yfinance"
    provider_name = "Yahoo Finance (yfinance)"

    def validate_params(self, params: Dict) -> None:
        if not params or "ticker" not in params:
            raise AssetSourceError("Missing 'ticker' in provider_params", "INVALID_PARAMS", {"params": params})

    async def get_current_value(self, provider_params: Dict, session) -> Dict:
        self.validate_params(provider_params)
        ticker = provider_params["ticker"]

        if yf is None:
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            t = yf.Ticker(ticker)
            info = t.history(period="1d")
            if info.empty:
                raise AssetSourceError(f"No data for ticker {ticker}", "NO_DATA")

            latest = info.iloc[-1]
            close = Decimal(str(latest["Close"]))
            return {
                "value": close,
                "currency": "USD",
                "as_of_date": date.today(),
                "source": self.provider_code
                }
        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(str(e), "FETCH_ERROR")

    async def get_history_value(self, provider_params: Dict, start_date: date, end_date: date, session) -> Dict:
        self.validate_params(provider_params)
        ticker = provider_params["ticker"]

        if yf is None:
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=str(start_date), end=str(end_date))

            if hist.empty:
                raise AssetSourceError(f"No data for ticker {ticker}", "NO_DATA")

            prices: List[Dict] = []
            for idx, row in hist.iterrows():
                d = idx.date()
                prices.append({
                    "date": d,
                    "open": Decimal(str(row["Open"])) if row["Open"] is not None else None,
                    "high": Decimal(str(row["High"])) if row["High"] is not None else None,
                    "low": Decimal(str(row["Low"])) if row["Low"] is not None else None,
                    "close": Decimal(str(row["Close"])),
                    "currency": "USD"
                    })

            return {
                "prices": prices,
                "currency": "USD",
                "source": self.provider_code
                }
        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(str(e), "FETCH_ERROR")

    async def search(self, query: str) -> List[Dict]:
        if yf is None:
            raise AssetSourceError("yfinance library not available in environment", "NOT_AVAILABLE")

        try:
            return [{"identifier": query.upper(), "display_name": query.upper(), "currency": "USD", "type": "STOCK"}]
        except Exception as e:
            raise AssetSourceError(str(e), "SEARCH_ERROR")
