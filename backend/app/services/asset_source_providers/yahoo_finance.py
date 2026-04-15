"""
Yahoo Finance asset pricing provider.

Uses yfinance library to fetch stock/ETF/crypto prices from Yahoo Finance.
Supports both current values and historical OHLC (Open, High, Low, Close) data.
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

import time as _time_mod
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.utils.cache_utils import get_ttl_cache

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
from backend.app.schemas.assets import (
    FACurrentValue,
    FAPricePoint,
    FAHistoricalData,
    FAAssetEventPoint,
    FAAssetPatchItem,
    FAClassificationParams,
    FASectorArea,
    )
from backend.app.schemas.common import Currency as CurrencyAmount
from backend.app.utils.sector_fin_utils import validate_sector
from datetime import datetime as _dt, timezone as _tz

logger = get_logger(__name__)

# ── Retry helpers for transient yfinance errors ─────────────────────────

# Keywords that indicate transient network/API errors worth retrying
_TRANSIENT_KEYWORDS = frozenset([
    "curl", "connection", "timeout", "timed out", "reset", "abruptly",
    "nonetype", "temporary", "503", "429", "too many requests",
    "rate limit", "ssl", "eof", "broken pipe", "gaierror",
])

_YF_MAX_RETRIES = 3
_YF_BASE_DELAY = 1.5  # seconds


def _is_transient(exc: Exception) -> bool:
    """Return True if the exception looks like a transient network error."""
    err = str(exc).lower()
    return any(kw in err for kw in _TRANSIENT_KEYWORDS)


def _yf_with_retry(fn, *, label: str = "yfinance"):
    """
    Execute a yfinance operation with retry on transient errors.

    Uses simple exponential backoff (1.5s → 3s → 6s).
    Non-transient errors are raised immediately.

    Args:
        fn: Zero-arg callable that performs the yfinance operation
        label: Human-readable label for logging

    Returns:
        Result of fn()

    Raises:
        The last exception if all retries are exhausted or non-transient
    """
    last_exc: Exception | None = None
    for attempt in range(1, _YF_MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if not _is_transient(e) or attempt == _YF_MAX_RETRIES:
                raise
            delay = _YF_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                f"{label} transient error (attempt {attempt}/{_YF_MAX_RETRIES}): {e}, "
                f"retrying in {delay:.1f}s"
            )
            _time_mod.sleep(delay)
    raise last_exc  # pragma: no cover – safety net


@register_provider(AssetProviderRegistry)
class YahooFinanceProvider(AssetSourceProvider):
    """Yahoo Finance data provider using yfinance library."""

    _MIN_SEARCH_CHARS = 2

    def __init__(self):
        super().__init__()
        # TTLCache for currency lookups (24h TTL — currency doesn't change)
        # This is a sub-operation cache (currency discovery), NOT a pricing cache.
        # The core handles caching for get_current_value/get_history_value/search.
        self._currency_cache = get_ttl_cache("yfinance_currency", maxsize=2000, ttl=86400)

    def _fetch_currency(self, symbol: str) -> str | None:
        """
        Fetch currency for a symbol using yfinance fast_info.
        Uses cache to avoid repeated API calls.

        Returns:
            Currency code (e.g., 'USD', 'EUR') or None if not available
        """
        cached, ok = self._currency_cache.get(symbol)
        if ok:
            return cached

        try:
            ticker = yf.Ticker(symbol)
            currency = ticker.fast_info.get("currency")
            self._currency_cache.set(symbol, currency)
            return currency
        except Exception as e:
            logger.debug(f"Could not fetch currency for {symbol}: {e}")
            self._currency_cache.set(symbol, None)
            return None

    @property
    def provider_code(self) -> str:
        return "yfinance"

    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.TICKER, ProviderInputType.ISIN]

    @property
    def get_icon(self) -> str:
        """Return provider icon URL (hardcoded)"""
        return "https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png"  # Yahoo Finance logo

    @property
    def provider_help_url(self) -> str:
        return "/mkdocs/user/assets/providers/yahoo-finance/"

    def get_asset_url(self, identifier, identifier_type=None, provider_params=None) -> str | None:
        """Generate URL to Yahoo Finance page for this asset."""
        return f"https://finance.yahoo.com/quote/{identifier}"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                "identifier": "AAPL",
                "identifier_type": IdentifierType.TICKER,
                "provider_params": None,
                "expected_symbol": "AAPL",
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

        The core runs this method in a dedicated thread with its own event loop,
        so sync yfinance calls are safe here. The core also caches the result
        (TTL 2min), so we don't need our own cache.

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
                {"identifier": identifier, "identifier_type": identifier_type},
                )

        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier},
                )

        try:
            # The core executes this entire method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            # Wrapped in _yf_with_retry to handle transient network errors
            # (e.g., curl 56, connection reset, 429 rate limits).
            info = _yf_with_retry(
                lambda: yf.Ticker(identifier).info,
                label=f"current_value({identifier})",
            )

            price = info.get("regularMarketPrice")
            if price is None:
                price = info.get("currentPrice") or info.get("previousClose")
            if price is None:
                raise AssetSourceError(
                    f"No price available for ticker: {identifier}",
                    "NO_DATA",
                    {"identifier": identifier},
                    )

            currency = info.get("currency") or info.get("financialCurrency") or "USD"

            # Date from regularMarketTime (Unix timestamp) or today
            rmt = info.get("regularMarketTime")
            if rmt:
                as_of_date = _dt.fromtimestamp(rmt, tz=_tz.utc).date()
            else:
                as_of_date = date.today()

            result = FACurrentValue(
                value=Decimal(str(price)),
                currency=currency,
                as_of_date=as_of_date,
                source=self.provider_name,
                )
            logger.debug(f"current_value for {identifier}: {price} {currency}")
            return result

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch current value for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
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
                {"identifier": identifier, "identifier_type": identifier_type},
                )

        if not YFINANCE_AVAILABLE:
            raise AssetSourceError(
                "yfinance library not available - install with: pipenv install yfinance",
                "NOT_AVAILABLE",
                {"identifier": identifier},
                )

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            _start = start_date.isoformat()
            _end = (end_date + timedelta(days=1)).isoformat()

            t = yf.Ticker(identifier)

            # Wrap history fetch in retry for transient network errors
            # (e.g., curl 56, NoneType from empty responses).
            hist = _yf_with_retry(
                lambda: t.history(start=_start, end=_end),
                label=f"history({identifier})",
            )

            # Defensive: handle None or non-DataFrame return (yfinance edge-case)
            if hist is None or not hasattr(hist, "empty"):
                raise AssetSourceError(
                    f"yfinance returned invalid data for {identifier} (got {type(hist).__name__})",
                    "FETCH_ERROR",
                    {"identifier": identifier},
                )

            # Currency (separate API call)
            currency = "USD"
            try:
                info = t.info
                if info:
                    currency = info.get("currency", "USD") or "USD"
            except Exception:
                pass
            # Dividends & splits (may trigger additional requests)
            try:
                dividends = t.dividends
            except Exception:
                dividends = None
            try:
                splits = t.splits
            except Exception:
                splits = None

            if hist.empty:
                raise AssetSourceError(
                    f"No historical data for ticker: {identifier}",
                    "NO_DATA",
                    {"identifier": identifier, "start": str(start_date), "end": str(end_date)},
                    )

            # Convert DataFrame to FAPricePoint list (pure CPU, no I/O)
            prices = []
            required_cols = {"Open", "High", "Low", "Close", "Volume"}
            actual_cols = set(hist.columns)
            if not required_cols.issubset(actual_cols):
                raise AssetSourceError(
                    f"Unexpected DataFrame columns for {identifier}: {list(hist.columns)}",
                    "FETCH_ERROR",
                    {"identifier": identifier, "columns": list(hist.columns)},
                )

            for idx, row in hist.iterrows():
                # yfinance returns DatetimeIndex with market timezone.
                # Convert to UTC for consistent backend date handling.
                # Frontend will handle local display.
                if hasattr(idx, "tz_convert"):
                    date_utc = idx.tz_convert("UTC").date()
                else:
                    date_utc = idx.date()

                prices.append(
                    FAPricePoint(
                        date=date_utc,
                        open=Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None,
                        high=Decimal(str(row["High"])) if pd.notna(row["High"]) else None,
                        low=Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None,
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                        currency=currency,
                        )
                    )

            # --- Parse asset events (dividends + splits) ---
            events: list[FAAssetEventPoint] = []

            try:
                # Dividends: pre-fetched in _sync_fetch_history (Series or None)
                if dividends is not None and not dividends.empty:
                    # Filter to requested date range
                    for idx, amount in dividends.items():
                        if pd.notna(amount) and amount > 0:
                            div_date = idx.tz_convert("UTC").date() if hasattr(idx, "tz_convert") else idx.date()
                            if start_date <= div_date <= end_date:
                                events.append(FAAssetEventPoint(
                                    date=div_date,
                                    type="DIVIDEND",
                                    value=CurrencyAmount(code=currency, amount=Decimal(str(amount))),
                                    notes=f"Yahoo Finance dividend for {identifier}",
                                ))
                    if events:
                        logger.info(f"Parsed {len(events)} DIVIDEND events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse dividends for {identifier}: {e}")

            try:
                # Splits: pre-fetched in _sync_fetch_history (Series or None)
                if splits is not None and not splits.empty:
                    split_count = 0
                    for idx, ratio in splits.items():
                        if pd.notna(ratio) and ratio != 0 and ratio != 1:
                            split_date = idx.tz_convert("UTC").date() if hasattr(idx, "tz_convert") else idx.date()
                            if start_date <= split_date <= end_date:
                                events.append(FAAssetEventPoint(
                                    date=split_date,
                                    type="SPLIT",
                                    value=CurrencyAmount(code=currency, amount=Decimal(str(ratio))),
                                    notes=f"Stock split {ratio}:1",
                                ))
                                split_count += 1
                    if split_count:
                        logger.info(f"Parsed {split_count} SPLIT events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse splits for {identifier}: {e}")

            return FAHistoricalData(prices=prices, events=events, currency=currency, source=self.provider_name)

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
                )

    @property
    def test_search_query(self) -> str | None:
        """Search query to use in tests."""
        return "Apple"

    async def search(self, query: str) -> list[dict]:
        """
        Search Yahoo Finance for matching tickers.

        Uses yfinance.Search for real search functionality.
        The core caches results (Layer 2 query cache, 15min TTL)
        and runs this in a dedicated thread.

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
                {"query": query},
                )

        # Minimum search length
        if len(query) < self._MIN_SEARCH_CHARS:
            return []

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            search_result = _yf_with_retry(
                lambda: yf.Search(query),
                label=f"search({query})",
            )
            raw_quotes = getattr(search_result, "quotes", []) or []

            results = []

            # Same mapping as fetch_asset_metadata, for normalizing search results
            search_type_map = {
                "equity": "STOCK",
                "etf": "ETF",
                "mutualfund": "FUND",
                "cryptocurrency": "CRYPTO",
                "currency": "OTHER",
                "future": "OTHER",
                "option": "OTHER",
                "index": "INDEX",
            }

            for quote in raw_quotes[:20]:
                if not quote.get("isYahooFinance", True):
                    continue
                symbol = quote.get("symbol", "")
                currency = self._fetch_currency(symbol) if symbol else None

                # Normalize quoteType using the same map as fetch_asset_metadata
                raw_type = (quote.get("quoteType", "Unknown") or "").lower()
                normalized_type = search_type_map.get(raw_type, "OTHER")

                results.append(
                    {
                        "identifier": symbol,
                        "identifier_type": IdentifierType.TICKER,  # YFinance uses ticker symbols
                        "display_name": quote.get("longname", quote.get("shortname", symbol)),
                        "currency": currency,
                        "type": normalized_type,
                    }
                )

            logger.info(f"Search for '{query}': found {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
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
                {"identifier": identifier, "identifier_type": identifier_type},
                )

        if not YFINANCE_AVAILABLE:
            logger.warning(f"yfinance not available, cannot fetch metadata for {identifier}")
            return None

        try:
            # The core executes this method in a dedicated thread,
            # so sync yfinance calls are safe — no asyncio.to_thread needed.
            t = yf.Ticker(identifier)
            info = _yf_with_retry(
                lambda: t.info,
                label=f"metadata({identifier})",
            )
            # Also attempt ISIN lookup (may not be available for all markets)
            identifier_isin = None
            try:
                isin_val = t.isin
                if isin_val and isin_val != "-" and len(isin_val) == 12:
                    identifier_isin = isin_val
            except Exception:
                pass

            if not info:
                logger.warning(f"No info data returned from yfinance for {identifier}")
                return None

            # Map quoteType to asset_type
            quote_type = info.get("quoteType", "").lower()
            asset_type_map = {
                "equity": "STOCK",
                "etf": "ETF",
                "mutualfund": "FUND",
                "cryptocurrency": "CRYPTO",
                "currency": "OTHER",
                "future": "OTHER",
                "option": "OTHER",
                "index": "INDEX",
                }
            asset_type = asset_type_map.get(quote_type, "OTHER")

            # Get description (truncate to 500 chars)
            long_business_summary = info.get("longBusinessSummary", "")
            short_name = info.get("shortName", "")
            long_name = info.get("longName", "")

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
            sector = info.get("sector")

            # Build FAClassificationParams
            classification_data = {"short_description": short_description}
            if sector:
                # Log warning if sector is not in standard classification
                if not validate_sector(sector):
                    logger.warning(
                        "Unknown sector from provider, mapped to Other",
                        provider_code="yfinance",
                        identifier=identifier,
                        original_sector=sector,
                        mapped_to="Other",
                        )
                # Convert single sector string to FASectorArea distribution
                classification_data["sector_area"] = FASectorArea(
                    distribution={sector: Decimal("1.0")}
                    )

            classification = FAClassificationParams(**classification_data)

            # Extract currency from info
            currency = info.get("currency") or info.get("financialCurrency")

            # Extract identifiers
            symbol = info.get("symbol")
            identifier_ticker = symbol if symbol else None

            # identifier_isin already fetched in _sync_fetch_metadata above

            # Build FAAssetPatchItem (asset_id will be filled by caller)
            patch_item = FAAssetPatchItem(
                asset_id=0,  # Placeholder, will be set by caller
                asset_type=asset_type,
                currency=currency,
                classification_params=classification,
                identifier_ticker=identifier_ticker,
                identifier_isin=identifier_isin,
                )

            logger.info(
                f"Fetched metadata from yfinance for {identifier}: asset_type={asset_type}, sector={sector}"
                )
            return patch_item

        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
