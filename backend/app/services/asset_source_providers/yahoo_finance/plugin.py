"""
Yahoo Finance asset pricing provider.

Uses yfinance library to fetch stock/ETF/crypto prices from Yahoo Finance.
Supports both current values and historical OHLC (Open, High, Low, Close) data.
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

import re
import time as _time_mod
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.utils.runtime.cache import get_ttl_cache

try:
    import pandas as pd
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    pd = None
    YFINANCE_AVAILABLE = False

try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:  # pragma: no cover — yfinance missing, or a version without it: the message words still count
    YFRateLimitError = None

from datetime import UTC
from datetime import datetime as _dt

from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.assets.metadata import (
    FAClassificationParams,
    FASectorArea,
)
from backend.app.schemas.common import Currency as CurrencyAmount
from backend.app.schemas.prices import (
    FACurrentValue,
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.assets.base import AssetHistoryStartDate, AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.provider_registry import register_provider
from backend.app.utils.asset.sector import validate_sector

logger = get_logger(__name__)

# ── Retry helpers for transient yfinance errors ─────────────────────────

# «Too many requests» is never retried in the thread: the core pauses the provider (decision 34, release 1.3).
# A whole-word 429, so a ticker such as 4290.T in a message is no refusal.
_RATE_LIMIT_PATTERN = re.compile(r"\b429\b|too many requests|rate limit")

# Keywords that indicate transient network/API errors worth retrying
_TRANSIENT_KEYWORDS = frozenset(
    [
        "curl",
        "connection",
        "timeout",
        "timed out",
        "reset",
        "abruptly",
        "nonetype",
        "temporary",
        "503",
        "ssl",
        "eof",
        "broken pipe",
        "gaierror",
    ]
)

_YF_MAX_RETRIES = 3
_YF_BASE_DELAY = 1.5  # seconds


def _is_rate_limited(exc: Exception) -> bool:
    """True for a «too many requests» refusal: yfinance's ``YFRateLimitError``, or its words in the message."""
    if YFRateLimitError is not None and isinstance(exc, YFRateLimitError):
        return True
    return _RATE_LIMIT_PATTERN.search(str(exc).lower()) is not None


def _is_transient(exc: Exception) -> bool:  # pragma: no cover
    """Return True if the exception looks like a transient network error."""
    err = str(exc).lower()
    return any(kw in err for kw in _TRANSIENT_KEYWORDS)


def _yf_with_retry(fn, *, label: str = "yfinance"):
    """
    Execute a yfinance operation with retry on transient errors.

    Up to three attempts, with exponential backoff between them (1.5 s, then 3 s).
    Non-transient errors are raised immediately. A «too many requests» refusal is raised at once as
    ``AssetRateLimitedError``, never retried: the call boundary pauses the provider (``core.call_provider``).

    Args:
        fn: Zero-arg callable that performs the yfinance operation
        label: Human-readable label for logging

    Returns:
        Result of fn()

    Raises:
        AssetRateLimitedError on a refusal for too many requests; otherwise the last exception if all retries are
        exhausted or non-transient
    """
    last_exc: Exception | None = None
    for attempt in range(1, _YF_MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            if _is_rate_limited(e):
                raise AssetRateLimitedError(f"Yahoo Finance refused for too many requests ({label})") from e
            last_exc = e
            if not _is_transient(e) or attempt == _YF_MAX_RETRIES:
                raise
            delay = _YF_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"{label} transient error (attempt {attempt}/{_YF_MAX_RETRIES}): {e}, " f"retrying in {delay:.1f}s")
            _time_mod.sleep(delay)
    raise last_exc  # pragma: no cover – safety net


@dataclass(frozen=True)
class _YahooHistoryAcquisition:
    history: object
    currency: str
    dividends: object | None
    splits: object | None


#: The unknown Area/Location names ``_exchange_zone`` already logged, once per name and process
_UNKNOWN_ZONES_LOGGED: set[str] = set()


def _exchange_zone(name: str | None) -> ZoneInfo | None:
    """Yahoo's ``exchangeTimezoneName`` as a ``ZoneInfo``, or None when it is empty or names no known zone.

    An Area/Location name (``Europe/Rome``) the server's timezone database does not know is logged once per name and
    process: on a host without one (Windows without the ``tzdata`` package, a minimal container) the current value is
    then dated in UTC, the day before for a session that crosses UTC midnight (backlog Z-36). A fixed offset or another
    name without an area is not logged.
    """
    if not name or not name.strip():
        return None
    key = name.strip()
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        if "/" in key and key not in _UNKNOWN_ZONES_LOGGED:
            _UNKNOWN_ZONES_LOGGED.add(key)
            logger.warning("Exchange timezone unknown to this server's timezone database: the current value is dated in UTC", timezone=key[:64])
        return None
    except ValueError:
        return None


def _normalize_yahoo_date(index_value) -> date:
    """The calendar date of a Yahoo index value, in its own timezone.

    yfinance stamps a daily bar, a dividend or a split at midnight in the exchange's timezone (``scrapers/history.py``:
    ``tz_localize(tz_exchange)``), so the wall date is the session's date. Converting to UTC first gave the day before
    for every exchange east of UTC (Z-33).
    """
    return index_value.date()


def _acquire_history_data(
    ticker,
    identifier: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> _YahooHistoryAcquisition:
    """Fetch Yahoo history plus best-effort metadata/event series."""
    if start_date == "min":
        history = _yf_with_retry(
            lambda: ticker.history(period="max"),
            label=f"history-max({identifier})",
        )
    else:
        remote_end = (end_date + timedelta(days=1)).isoformat()
        history = _yf_with_retry(
            lambda: ticker.history(
                start=start_date.isoformat(),
                end=remote_end,
            ),
            label=f"history({identifier})",
        )

    if history is None or not hasattr(history, "empty"):
        raise AssetSourceError(
            f"yfinance returned invalid data for {identifier} (got {type(history).__name__})",
            "FETCH_ERROR",
            {"identifier": identifier},
        )

    currency = "USD"
    try:
        info = ticker.info
        if info:
            currency = info.get("currency", "USD") or "USD"
    except Exception:
        logger.exception(
            "Failed to fetch yfinance currency metadata; falling back to USD",
            identifier=identifier,
        )

    try:
        dividends = ticker.dividends
    except Exception as exc:
        logger.debug(f"Could not fetch dividends for {identifier}: {exc}")
        dividends = None

    try:
        splits = ticker.splits
    except Exception as exc:
        logger.debug(f"Could not fetch splits for {identifier}: {exc}")
        splits = None

    return _YahooHistoryAcquisition(
        history=history,
        currency=currency,
        dividends=dividends,
        splits=splits,
    )


def _map_history_prices(
    history,
    identifier: str,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAPricePoint]:
    """Map Yahoo OHLCV rows to canonical price points."""
    if history.empty:
        raise AssetSourceError(
            f"No historical data for ticker: {identifier}",
            "NO_DATA",
            {
                "identifier": identifier,
                "start": str(start_date),
                "end": str(end_date),
            },
        )

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    if not required_columns.issubset(set(history.columns)):
        raise AssetSourceError(
            f"Unexpected DataFrame columns for {identifier}: {list(history.columns)}",
            "FETCH_ERROR",
            {
                "identifier": identifier,
                "columns": list(history.columns),
            },
        )

    prices: list[FAPricePoint] = []
    for index_value, row in history.iterrows():
        point_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and point_date < start_date:
            continue
        if point_date > end_date:
            continue
        if not pd.notna(row["Close"]):
            logger.debug(f"Skipping {point_date} for {identifier}: Close is NaN")
            continue

        prices.append(
            FAPricePoint(
                date=point_date,
                open=(Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None),
                high=(Decimal(str(row["High"])) if pd.notna(row["High"]) else None),
                low=(Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None),
                close=Decimal(str(row["Close"])),
                volume=(int(row["Volume"]) if pd.notna(row["Volume"]) else None),
                currency=currency,
            )
        )

    if not prices:
        raise AssetSourceError(
            f"No usable price points for ticker: {identifier} (all Close values are NaN)",
            "NO_DATA",
            {
                "identifier": identifier,
                "start": str(start_date),
                "end": str(end_date),
            },
        )
    return prices


def _parse_dividend_events(
    dividends,
    identifier: str,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAAssetEventPoint]:
    """Map positive, in-range Yahoo dividends to canonical events."""
    if dividends is None or dividends.empty:
        return []

    events: list[FAAssetEventPoint] = []
    for index_value, amount in dividends.items():
        if not pd.notna(amount) or amount <= 0:
            continue
        event_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and event_date < start_date:
            continue
        if event_date > end_date:
            continue
        events.append(
            FAAssetEventPoint(
                date=event_date,
                type="DIVIDEND",
                value=CurrencyAmount(
                    code=currency,
                    amount=Decimal(str(amount)),
                ),
                notes=f"Yahoo Finance dividend for {identifier}",
            )
        )
    return events


def _parse_split_events(
    splits,
    currency: str,
    start_date: AssetHistoryStartDate,
    end_date: date,
) -> list[FAAssetEventPoint]:
    """Map non-trivial, in-range Yahoo split ratios to canonical events."""
    if splits is None or splits.empty:
        return []

    events: list[FAAssetEventPoint] = []
    for index_value, ratio in splits.items():
        if not pd.notna(ratio) or ratio == 0 or ratio == 1:
            continue
        event_date = _normalize_yahoo_date(index_value)
        if start_date != "min" and event_date < start_date:
            continue
        if event_date > end_date:
            continue
        events.append(
            FAAssetEventPoint(
                date=event_date,
                type="SPLIT",
                value=CurrencyAmount(
                    code=currency,
                    amount=Decimal(str(ratio)),
                ),
                notes=f"Stock split {ratio}:1",
            )
        )
    return events


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
        """The currency Yahoo gives for ``symbol`` (``fast_info``), e.g. ``USD`` or ``GBp``; None when Yahoo has none or
        the read failed.

        Only an answer is cached, 24 h: a currency, or Yahoo answering without one. A refusal for too many requests is
        raised at once as ``AssetRateLimitedError``, with no retry and nothing cached, so that the call boundary pauses
        the provider («never swallow a refusal»): the whole search leaves as rate limited. Any other error gives None,
        not cached, so the next call asks again (Z-39).
        """
        cached, ok = self._currency_cache.get(symbol)
        if ok:
            return cached

        try:
            currency = yf.Ticker(symbol).fast_info.get("currency")
        except Exception as e:
            if _is_rate_limited(e):
                raise AssetRateLimitedError(f"Yahoo Finance refused for too many requests (currency({symbol}))") from e
            logger.debug(f"Could not fetch currency for {symbol}: {e}")
            return None
        self._currency_cache.set(symbol, currency)
        return currency

    @property
    def provider_code(self) -> str:
        return "yfinance"

    @property
    def provider_name(self) -> str:
        return "Yahoo Finance"

    @property
    def supports_meaningful_volume(self) -> bool:
        """Yahoo Finance reports real exchange-traded share volume (the
        `Volume` column from the underlying OHLCV history)."""
        return True

    @property
    def volume_kind(self) -> FAVolumeKind:
        return FAVolumeKind.TRADED_SHARES

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

            # Date from regularMarketTime (Unix timestamp), in the exchange's timezone (Z-33: a session that crosses UTC
            # midnight, Sydney's or Auckland's, belongs to its local day; UTC when the timezone is unknown), or today
            zone = _exchange_zone(info.get("exchangeTimezoneName"))
            rmt = info.get("regularMarketTime")
            if rmt:
                as_of_date = _dt.fromtimestamp(rmt, tz=zone or UTC).date()
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
            ) from e

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
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
            acquisition = _acquire_history_data(
                yf.Ticker(identifier),
                identifier,
                start_date,
                end_date,
            )
            prices = _map_history_prices(
                acquisition.history,
                identifier,
                acquisition.currency,
                start_date,
                end_date,
            )

            events: list[FAAssetEventPoint] = []
            try:
                dividend_events = _parse_dividend_events(
                    acquisition.dividends,
                    identifier,
                    acquisition.currency,
                    start_date,
                    end_date,
                )
                events.extend(dividend_events)
                if dividend_events:
                    logger.debug(f"Parsed {len(dividend_events)} DIVIDEND events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse dividends for {identifier}: {e}")

            try:
                split_events = _parse_split_events(
                    acquisition.splits,
                    acquisition.currency,
                    start_date,
                    end_date,
                )
                events.extend(split_events)
                if split_events:
                    logger.debug(f"Parsed {len(split_events)} SPLIT events for {identifier}")
            except Exception as e:
                logger.debug(f"Could not parse splits for {identifier}: {e}")

            return FAHistoricalData(
                prices=prices,
                events=events,
                currency=acquisition.currency,
                source=self.provider_name,
            )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

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

            logger.debug(f"Search for '{query}': found {len(results)} results")
            return results

        except AssetRateLimitedError:
            raise  # the core pauses the provider: not an empty result
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

    async def fetch_asset_metadata(  # noqa: C901 — flat field mapping with fallbacks
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
                logger.exception("Failed to fetch yfinance ISIN metadata", identifier=identifier)

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
                classification_data["sector_area"] = FASectorArea(distribution={sector: Decimal("1.0")})

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

            logger.debug(f"Fetched metadata from yfinance for {identifier}: asset_type={asset_type}, sector={sector}")
            return patch_item

        except AssetRateLimitedError:
            raise  # the core pauses the provider: not "no metadata"
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
