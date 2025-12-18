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

from backend.app.db import IdentifierType
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
from backend.app.schemas.assets import FACurrentValue, FAPricePoint, FAHistoricalData, FAAssetPatchItem, FAClassificationParams, FASectorArea

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

    def get_icon(self) -> str:
        """ Return provider icon URL (hardcoded) """
        return "https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png"  # Yahoo Finance logo

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                'identifier': 'AAPL',
                'identifier_type': IdentifierType.TICKER,
                'provider_params': None
                }
            ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
        ) -> FACurrentValue:
        """
        Fetch current price from Yahoo Finance.

        Uses fast_info.last_price for speed, falls back to history if unavailable.

        Args:
            identifier: Yahoo Finance ticker symbol (e.g., "AAPL", "BTC-USD")
            identifier_type: Type of identifier (must be TICKER or ISIN)
            provider_params: Optional parameters (unused for Yahoo Finance)

        Returns:
            FACurrentValue with value, currency, as_of_date, source

        Raises:
            AssetSourceError: If yfinance not available, identifier_type invalid, or data fetch fails
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type}
                )

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
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: date,
        end_date: date,
        ) -> FAHistoricalData:
        """
        Fetch historical OHLC data from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            identifier_type: Type of identifier (must be TICKER or ISIN)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            provider_params: Optional parameters (unused)

        Returns:
            FAHistoricalData with prices list, currency, source

        Raises:
            AssetSourceError: If yfinance not available, identifier_type invalid, or data fetch fails
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type}
                )

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
        return 'Apple'

    async def search(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for matching tickers.

        Uses yfinance.Search for real search functionality.
        Results are cached for 10 minutes.

        Args:
            query: Search query (e.g., "Apple", "Microsoft", "AAPL")

        Returns:
            List of matching tickers with metadata.
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

        # Minimum search length
        if len(query) < self._MIN_SEARCH_CHARS:
            return []

        # Check cache
        cache_key = query.lower()
        if cache_key in self._search_cache:
            results, timestamp = self._search_cache[cache_key]
            age = (utcnow() - timestamp).total_seconds()
            if age < self._CACHE_TTL_SECONDS:
                logger.debug(f"Cache hit for '{query}' (age: {age:.0f}s)")
                return results

        try:
            # Use yfinance Search for real search functionality
            from yfinance import Search
            search_result = Search(query)

            results = []
            quotes = getattr(search_result, 'quotes', []) or []

            for quote in quotes[:20]:  # Limit to top 20 results
                # Skip non-Yahoo Finance results
                if not quote.get('isYahooFinance', True):
                    continue

                results.append({
                    "identifier": quote.get('symbol', ''),
                    "identifier_type": IdentifierType.TICKER,  # YFinance uses ticker symbols
                    "display_name": quote.get('longname', quote.get('shortname', quote.get('symbol', ''))),
                    "currency": None,  # TODO: capire se un modo per avere la valuta ci può essere
                    "type": quote.get('quoteType', 'Unknown')  # EQUITY, ETF, CRYPTOCURRENCY, etc.
                    })

            # Cache result
            self._search_cache[cache_key] = (results, utcnow())
            logger.info(f"Search for '{query}': found {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            # Cache empty result to avoid repeated failures
            self._search_cache[cache_key] = ([], utcnow())
            return []

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
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
        ) -> FAAssetPatchItem | None:
        """
        Fetch asset metadata from Yahoo Finance.

        Extracts investment type, description, and sector from yfinance ticker info.
        Geographic area is not available from Yahoo Finance.

        Args:
            identifier: Yahoo Finance ticker symbol
            identifier_type: Type of identifier (must be TICKER or ISIN)
            provider_params: Optional parameters (unused)

        Returns:
            FAAssetPatchItem with metadata fields (asset_id will be None, filled by caller)
            or None if fetch fails.
            Contains: asset_type, classification_params (sector, short_description)

        Note:
            Returns RAW data - normalization happens in core service layer.
        """
        # Validate identifier_type
        if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
            raise AssetSourceError(
                f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
                {"identifier": identifier, "identifier_type": identifier_type}
                )

        if not YFINANCE_AVAILABLE:
            logger.warning(f"yfinance not available, cannot fetch metadata for {identifier}")
            return None

        try:
            ticker = yf.Ticker(identifier)
            info = ticker.info

            if not info:
                logger.warning(f"No info data returned from yfinance for {identifier}")
                return None

            # Map quoteType to asset_type
            quote_type = info.get('quoteType', '').lower()
            asset_type_map = {
                'equity': 'STOCK',
                'etf': 'ETF',
                'mutualfund': 'FUND',
                'cryptocurrency': 'CRYPTO',
                'currency': 'OTHER',
                'future': 'OTHER',
                'option': 'OTHER',
                }
            asset_type = asset_type_map.get(quote_type, 'OTHER')

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

            # Build FAClassificationParams
            classification_data = {'short_description': short_description}
            if sector:
                # Convert single sector string to FASectorArea distribution
                classification_data['sector_area'] = FASectorArea(distribution={sector: Decimal("1.0")})

            classification = FAClassificationParams(**classification_data)

            # Extract currency from info
            currency = info.get('currency') or info.get('financialCurrency')

            # Build FAAssetPatchItem (asset_id will be filled by caller)
            patch_item = FAAssetPatchItem(
                asset_id=0,  # Placeholder, will be set by caller
                asset_type=asset_type,
                currency=currency,
                classification_params=classification
                )

            logger.info(f"Fetched metadata from yfinance for {identifier}: asset_type={asset_type}, sector={sector}")
            return patch_item

        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
