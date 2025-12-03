"""
Yahoo Finance asset pricing provider.

Uses yfinance library to fetch stock/ETF/crypto prices from Yahoo Finance.
Supports both current values and historical OHLC (Open, High, Low, Close) data.
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict

from backend.app.logging_config import get_logger
from backend.app.utils.datetime_utils import utcnow

try:
    import yfinance as yf
    import pandas as pd

    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    pd = None
    YFINANCE_AVAILABLE = False

from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.schemas.assets import FACurrentValue, FAPricePoint, FAHistoricalData, FAClassificationParams

logger = get_logger(__name__)


@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    """Yahoo Finance data provider using yfinance library."""

    # Cache for search results (10 min TTL)
    # TODO: implementare pulizia cache quando ttl si esaurisce, con cache system a livello di sistema
    _search_cache: Dict[str, tuple[list[dict], datetime]] = {}
    _CACHE_TTL_SECONDS = 600  # 10 minutes
    _MIN_SEARCH_CHARS = 2

    @property
    def provider_code(self) -> str:
        return "yfinance"

    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                'identifier': 'AAPL',
                'provider_params': None
                }
            ]

    async def get_current_value(
        self,
        identifier: str,
        provider_params: Dict | None = None,
        ) -> FACurrentValue:
        """
        Fetch current price from Yahoo Finance.

        Uses fast_info.last_price for speed, falls back to history if unavailable.

        Args:
            identifier: Yahoo Finance ticker symbol (e.g., "AAPL", "BTC-USD")
            provider_params: Optional parameters (unused for Yahoo Finance)

        Returns:
            FACurrentValue with value, currency, as_of_date, source

        Raises:
            AssetSourceError: If yfinance not available or data fetch fails
        """
        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier}
                )

        try:
            ticker = yf.Ticker(identifier)

            # Try fast_info first (faster, cached)
            try:
                last_price = ticker.fast_info.get('lastPrice')
                if last_price and last_price > 0:
                    currency = ticker.fast_info.get('currency', 'USD')
                    return FACurrentValue(
                        value=Decimal(str(last_price)),
                        currency=currency,
                        as_of_date=date.today(),
                        source=self.provider_name
                        )
            except Exception as e:
                logger.debug(f"fast_info failed for {identifier}, trying history: {e}")

            # Fallback to history (last close)
            hist = ticker.history(period='5d')
            if hist.empty:
                raise AssetSourceError(
                    f"No data available for ticker: {identifier}",
                    "NO_DATA",
                    {"identifier": identifier}
                    )

            last_row = hist.iloc[-1]
            last_date = hist.index[-1].date()

            # Get currency from info (may be slow, but we're already in fallback)
            currency = None
            try:
                info = ticker.info
                currency = info.get('currency')
            except Exception:
                logger.warning(f"Could not get currency for {identifier}, using USD")

            return FACurrentValue(
                value=Decimal(str(last_row['Close'])),
                currency=currency,
                as_of_date=last_date,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch current value for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)}
                )

    async def get_history_value(
        self,
        identifier: str,
        provider_params: Dict | None,
        start_date: date,
        end_date: date,
        ) -> FAHistoricalData:
        """
        Fetch historical OHLC data from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            provider_params: Optional parameters (unused)

        Returns:
            FAHistoricalData with prices list, currency, source

        Raises:
            AssetSourceError: If yfinance not available or data fetch fails
        """
        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier}
                )

        try:
            ticker = yf.Ticker(identifier)

            # Fetch history (end+1 because yfinance end is exclusive)
            hist = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat()
                )

            if hist.empty:
                raise AssetSourceError(
                    f"No historical data for ticker: {identifier}",
                    "NO_DATA",
                    {
                        "identifier": identifier,
                        "start": str(start_date),
                        "end": str(end_date)
                        }
                    )

            # Get currency
            currency = 'USD'
            try:
                info = ticker.info
                currency = info.get('currency', 'USD')
            except Exception:
                logger.warning(f"Could not get currency for {identifier}, using USD")

            # Convert DataFrame to FAPricePoint list
            prices = []
            for idx, row in hist.iterrows():
                prices.append(FAPricePoint(
                    date=idx.date(),  # TODO: verify timezone handling
                    open=Decimal(str(row['Open'])) if pd.notna(row['Open']) else None,
                    high=Decimal(str(row['High'])) if pd.notna(row['High']) else None,
                    low=Decimal(str(row['Low'])) if pd.notna(row['Low']) else None,
                    close=Decimal(str(row['Close'])),
                    volume=int(row['Volume']) if pd.notna(row['Volume']) else None,
                    currency=currency
                    ))

            return FAHistoricalData(
                prices=prices,
                currency=currency,
                source=self.provider_name
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)}
                )

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests."""
        return 'AAPL'

    async def search(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for matching tickers.

        Note: yfinance doesn't have native search API, so we try exact match.
        Results are cached for 10 minutes.

        Args:
            query: Ticker symbol to search (e.g., "AAPL")

        Returns:
            List of matching tickers (0 or 1 result)
            Each result: {identifier, display_name, currency, type}

        Raises:
            AssetSourceError: If yfinance not available or search fails
        """
        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"query": query}
                )

        # Check cache
        cache_key = query.upper()
        # TODO: implementare ricerca fuzzy
        if cache_key in self._search_cache:
            results, timestamp = self._search_cache[cache_key]
            age = (utcnow() - timestamp).total_seconds()
            if age < self._CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for '{query}' (age: {age:.0f}s)")
                return results

        try:
            # yfinance doesn't have native search, try exact match
            ticker = yf.Ticker(query.upper())

            try:
                info = ticker.info
                if not info or 'symbol' not in info:
                    # Not found
                    self._search_cache[cache_key] = ([], utcnow())
                    return []

                result = [
                    {
                        "identifier": info.get('symbol', query.upper()),
                        "display_name": info.get('longName', info.get('shortName', query.upper())),
                        "currency": info.get('currency', 'USD'),
                        "type": info.get('quoteType', 'Unknown')  # EQUITY, ETF, CRYPTOCURRENCY, etc.
                        }
                    ]

                # Cache result
                self._search_cache[cache_key] = (result, utcnow())
                logger.info(f"Search for '{query}': found {info.get('symbol')}")
                return result

            except Exception as e:
                logger.debug(f"Ticker '{query}' not found: {e}")
                # Cache empty result
                self._search_cache[cache_key] = ([], datetime.utcnow())
                return []

        except Exception as e:
            raise AssetSourceError(
                f"Search failed for '{query}': {e}",
                "SEARCH_ERROR",
                {"query": query, "error": str(e)}
                )

    def validate_params(self, params: Dict | None) -> None:
        """
        Validate provider parameters.

        For Yahoo Finance, identifier is passed directly to methods,
        no special params needed.
        """
        # Yahoo Finance doesn't require specific params
        # Identifier is passed as method argument
        pass

    async def fetch_asset_metadata(
        self,
        identifier: str,
        provider_params: Dict | None = None,
        ) -> FAClassificationParams | None:
        """
        Fetch asset metadata from Yahoo Finance.

        Extracts investment type, description, and sector from yfinance ticker info.
        Geographic area is not available from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            provider_params: Optional parameters (unused)

        Returns:
            Dict with metadata fields or None if fetch fails:
            {
                "short_description": str,
                "sector": str,
                "geographic_area": None  # Not available
            }

        Note:
            Returns RAW data - normalization happens in core service layer.
        """
        if not YFINANCE_AVAILABLE:
            logger.warning(f"yfinance not available, cannot fetch metadata for {identifier}")
            return None

        try:
            ticker = yf.Ticker(identifier)
            info = ticker.info

            if not info:
                logger.warning(f"No info data returned from yfinance for {identifier}")
                return None

            # TODO: da ora investment_type non è più un metadato, ma un campo primario di Asset,
            #  è stato commentato qui, ma in futuro bisogna farlo scrivere alla creazione dell'asset
            # Map quoteType to investment_type
            quote_type = info.get('quoteType', '').lower()
            investment_type_map = {
                'equity': 'stock',
                'etf': 'etf',
                'mutualfund': 'mutual_fund',
                'cryptocurrency': 'crypto',
                'currency': 'currency',
                'future': 'future',
                'option': 'option',
                }
            investment_type = investment_type_map.get(quote_type, 'stock')

            # Get description (truncate to 500 chars)
            long_business_summary = info.get('longBusinessSummary', '')
            short_name = info.get('shortName', '')
            long_name = info.get('longName', '')

            # Prefer longBusinessSummary, fallback to names
            if long_business_summary:
                short_description = long_business_summary[:500]
            elif long_name:
                short_description = long_name
            elif short_name:
                short_description = short_name
            else:
                short_description = f"{identifier} from Yahoo Finance"

            # Get sector
            sector = info.get('sector')

            metadata = FAClassificationParams(sector=sector, short_description=short_description)
            logger.info(f"Fetched metadata from yfinance for {identifier}: type={investment_type}, sector={sector}")
            return metadata

        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
