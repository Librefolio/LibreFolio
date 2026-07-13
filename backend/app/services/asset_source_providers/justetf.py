"""
JustETF provider for asset pricing.

Uses the justetf-scraping library to fetch ETF data from justetf.com.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType, ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAAssetEventPoint,
    FAAssetPatchItem,
    FAClassificationParams,
    FACurrentValue,
    FAGeographicArea,
    FAHistoricalData,
    FAPricePoint,
    FASectorArea,
)
from backend.app.schemas.common import Currency as CurrencyAmount
from backend.app.services.asset_source import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider
from backend.app.utils.cache_utils import get_ttl_cache
from backend.app.utils.sector_fin_utils import validate_sector

try:
    import justetf_scraping
    import pandas as pd
    from justetf_scraping import get_etf_overview, iterate_live_quote, load_chart, load_live_quote, load_overview

    JUSTETF_AVAILABLE = True
except ImportError:
    justetf_scraping = None
    get_etf_overview = None
    load_live_quote = None
    iterate_live_quote = None
    load_chart = None
    load_overview = None
    pd = None
    JUSTETF_AVAILABLE = False

logger = get_logger(__name__)

# Global TTL caches (auto-expire, no manual cleanup needed)
_overview_cache = get_ttl_cache("justetf_overview", maxsize=500, ttl=3600)  # 1 hour
_chart_cache = get_ttl_cache("justetf_chart", maxsize=500, ttl=3600)  # 1 hour
_etf_list_cache = get_ttl_cache("justetf_etf_list", maxsize=100, ttl=3600)  # 1 hour

# ============================================================================
# LIVE QUOTE STREAMING — Persistent WebSocket feeds
# ============================================================================
# Instead of opening a WebSocket per get_current_value() call, we keep
# background threads that continuously receive quotes and store the latest
# value in a dict.  get_current_value() reads from this dict (instant, no I/O).
#
# - _live_quote_store:  {isin: Quote}  — latest quote per ISIN
# - _live_quote_threads: {isin: threading.Thread}  — one daemon thread per ISIN
# - _live_quote_stop:    threading.Event  — set at shutdown to stop all threads
# ============================================================================
import threading

_live_quote_store: dict[str, object] = {}  # isin → latest Quote object
_live_quote_threads: dict[str, threading.Thread] = {}
_live_quote_stop = threading.Event()
_live_quote_lock = threading.Lock()


def _live_quote_worker(isin: str) -> None:
    """
    Background thread: keeps a WebSocket open and updates _live_quote_store.
    Reconnects automatically on error.  Exits when _live_quote_stop is set.
    """
    if not JUSTETF_AVAILABLE or iterate_live_quote is None:
        return

    backoff = 1  # seconds — exponential backoff on error, capped at 60
    while not _live_quote_stop.is_set():
        try:
            for quote in iterate_live_quote(isin):
                _live_quote_store[isin] = quote
                backoff = 1  # reset on success
                if _live_quote_stop.is_set():
                    return
        except Exception as e:
            # WebSocket closed or error — reconnect after backoff
            if not _live_quote_stop.is_set():
                logger.debug(f"Live quote WebSocket for {isin} error: {e}, retrying in {backoff}s")
                _live_quote_stop.wait(timeout=backoff)
                backoff = min(backoff * 2, 60)


def _ensure_live_feed(isin: str) -> None:
    """Start a live-feed thread for this ISIN if not already running."""
    if not JUSTETF_AVAILABLE or _live_quote_stop.is_set():
        return
    with _live_quote_lock:
        thread = _live_quote_threads.get(isin)
        if thread is not None and thread.is_alive():
            return
        t = threading.Thread(target=_live_quote_worker, args=(isin,), daemon=True, name=f"justetf-live-{isin}")
        _live_quote_threads[isin] = t
        t.start()
        logger.debug(f"Started live quote feed for {isin}")


def shutdown_live_feeds() -> None:  # pragma: no cover
    """Stop all live-feed threads.  Called from app shutdown."""
    _live_quote_stop.set()
    with _live_quote_lock:
        for _isin, t in _live_quote_threads.items():
            t.join(timeout=3)
        _live_quote_threads.clear()
    logger.debug("All JustETF live quote feeds stopped")


def _country_name_to_iso3(country_name: str) -> Optional[str]:  # pragma: no cover
    """
    Convert country name to ISO 3166-1 alpha-3 code.
    Uses pycountry via geo_normalization utility.
    Returns "Other" for the "other" category (truthy, so it's preserved in distribution).
    Returns None if not found.
    """
    # Preserve "Other" category — normalize_country_keys handles it downstream
    if country_name.lower() == "other":
        return "Other"

    try:
        from backend.app.utils.geo_utils import normalize_country_to_iso3  # noqa: PLC0415 — lazy import / avoid circular

        return normalize_country_to_iso3(country_name)
    except (ValueError, ImportError) as e:
        logger.debug(f"Could not normalize country '{country_name}': {e}")
        return None


@register_provider(AssetProviderRegistry)
class JustETFProvider(AssetSourceProvider):
    """JustETF.com data provider using the justetf-scraping library."""

    @classmethod
    def etf_list(cls) -> pd.DataFrame:
        """Get cached ETF list."""
        cached, ok = _etf_list_cache.get("etf_list")
        if ok:
            return cached

        df = load_overview()
        _etf_list_cache.set("etf_list", df)
        return df

    def _get_currency(self, provider_params: Dict | None) -> str:
        """Extract currency from provider_params, default EUR."""
        if provider_params and provider_params.get("currency"):
            return provider_params["currency"]
        return "EUR"

    def _check_availability(self):
        """Raise AssetSourceError if the library is not installed."""
        if not JUSTETF_AVAILABLE:
            raise AssetSourceError(
                "justetf-scraping library not available - install with: pipenv install justetf-scraping",
                "NOT_AVAILABLE",
            )

    @property
    def provider_code(self) -> str:
        return "justetf"

    @property
    def provider_name(self) -> str:
        return "JustETF"

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.ISIN]

    @property
    def get_icon(self) -> str:
        """Return provider icon URL (hardcoded)."""
        return "https://www.justetf.com/android-chrome-144x144.png?v2"

    @property
    def provider_help_url(self) -> str:
        return "/mkdocs/user/assets/providers/justetf/"

    def get_asset_url(self, identifier, identifier_type=None, provider_params=None) -> str | None:
        """Generate URL to JustETF ETF profile page."""
        return f"https://www.justetf.com/en/etf-profile.html?isin={identifier}"

    # Supported currencies for JustETF chart API
    SUPPORTED_CURRENCIES = ("EUR", "USD", "CHF", "GBP")
    CURRENCY_FLAGS = {"EUR": "🇪🇺", "USD": "🇺🇸", "CHF": "🇨🇭", "GBP": "🇬🇧"}

    @property
    def params_schema(self) -> list[dict]:
        return [
            {
                "key": "currency",
                "type": "select",
                "required": False,
                "options": list(self.SUPPORTED_CURRENCIES),
                "default": "EUR",
                "description": "Price currency. EUR = real-time + history. USD/CHF/GBP = history only (converted by JustETF).",
            }
        ]

    @property
    def test_cases(self) -> list[dict]:
        """Test cases for the generic provider test framework.

        Only EUR is included here because the generic test expects get_current_value
        to succeed for all cases. Non-EUR currencies only support history (no current).
        Multi-currency is validated via the search test and manual testing.
        """
        return [
            {
                "identifier": "IE00B4L5Y983",  # iShares Core MSCI World UCITS ETF USD (Acc)
                "identifier_type": IdentifierType.ISIN,
                "provider_params": {"currency": "EUR"},
                "expected_symbol": "IE00B4L5Y983",
            },
        ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FACurrentValue:
        """
        Fetch current price from JustETF (gettex WebSocket, EUR only).

        Strategy (fastest first):
        1. Check _live_quote_store (instant, no I/O — populated by background WebSocket)
        2. One-shot load_live_quote (opens WebSocket, reads first quote, closes)
        3. Both paths also ensure a persistent live-feed is running for future calls

        Raises NOT_SUPPORTED if currency ≠ EUR (gettex only provides EUR quotes).
        """
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            raise AssetSourceError(
                f"JustETF provider only supports ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
            )

        currency = self._get_currency(provider_params)
        if currency != "EUR":
            raise AssetSourceError(
                f"Current price only available in EUR (gettex exchange). " f"For {currency} prices, only historical data is available.",
                "NOT_SUPPORTED",
                {"currency": currency, "supported_for_current": "EUR"},
            )

        try:
            # Ensure persistent WebSocket feed is running for this ISIN
            _ensure_live_feed(identifier)

            # 1. Try live store first (instant, no I/O)
            quote = _live_quote_store.get(identifier)

            # 2. Fallback: one-shot fetch (first call before WS delivers)
            if quote is None:
                quote = load_live_quote(identifier)

            if quote is None:
                raise AssetSourceError(
                    f"No gettex quote available for {identifier}",
                    "NOT_FOUND",
                )

            # Extract price from Quote dataclass
            price = quote.last or quote.mid
            currency = quote.currency
            timestamp = quote.timestamp

            if price is None:
                raise AssetSourceError(
                    f"No price data in gettex quote for {identifier}",
                    "NOT_FOUND",
                )

            # Convert timestamp to date
            as_of_date = timestamp.date() if timestamp else date.today()

            return FACurrentValue(
                value=Decimal(str(price)),
                currency=currency,
                as_of_date=as_of_date,
                source=self.provider_name,
            )
        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch current value for {identifier} from JustETF: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    @property
    def supports_history(self) -> bool:
        return True

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
        end_date: date,
    ) -> FAHistoricalData:
        """
        Fetch historical data from JustETF using load_chart.
        Adds current value only if end_date is today.
        """
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            raise AssetSourceError(
                f"JustETF provider only supports ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
            )

        try:
            currency = self._get_currency(provider_params)
            effective_start = ASSET_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
            # add_current appends today's gettex quote — only valid for EUR (gettex = EUR exchange)
            add_current = end_date >= date.today() and currency == "EUR"

            # Check cache (keyed by currency)
            cache_key = f"chart_{identifier}_{currency}_{add_current}"
            cached_df, ok = _chart_cache.get(cache_key)

            if not ok:
                df = load_chart(identifier, currency, add_current)
                _chart_cache.set(cache_key, df)
            else:
                df = cached_df

            df = df.reset_index()

            # Filter by date range
            df["date_only"] = pd.to_datetime(df["date"]).dt.date
            df = df[(df["date_only"] >= effective_start) & (df["date_only"] <= end_date)]

            prices: List[FAPricePoint] = []
            for row in df.itertuples():
                # date_only is added above, always available
                row_date = row.date_only
                prices.append(
                    FAPricePoint(
                        date=row_date,
                        open=None,
                        high=None,
                        low=None,
                        close=Decimal(str(row.quote)),
                        volume=None,
                        currency=currency,
                        backward_fill_info=None,
                    )
                )

            # --- Parse dividend events from chart data ---
            # load_chart() returns a DataFrame with a 'dividends' column
            # where values > 0 represent actual distribution payouts.
            events: List[FAAssetEventPoint] = []
            try:
                if "dividends" in df.columns:
                    div_rows = df[df["dividends"] > 0]
                    for row in div_rows.itertuples():
                        events.append(
                            FAAssetEventPoint(
                                date=row.date_only,
                                type="DIVIDEND",
                                value=CurrencyAmount(code=currency, amount=Decimal(str(row.dividends))),
                                notes=f"JustETF distribution for {identifier}",
                            )
                        )
                    if events:
                        logger.debug(f"Parsed {len(events)} DIVIDEND events for {identifier} from chart data")
            except Exception as e:
                logger.debug(f"Could not parse dividends from chart for {identifier}: {e}")

            return FAHistoricalData(prices=prices, events=events, currency=currency, source=self.provider_name)
        except Exception as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier} from JustETF: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    @property
    def test_search_query(self) -> str | None:
        return "iShares Core S&P 500"

    async def search(self, query: str) -> list[dict]:
        """Search for ETFs in the cached ETF list, returning 4 currency variants per match."""
        self._check_availability()
        try:
            df_all = JustETFProvider.etf_list()
            # Define only the normal columns (exclude index 'isin' from here)
            cols_only = ["name", "ticker", "wkn"]
            # Search in columns (Vectorized)
            mask_cols = df_all[cols_only].fillna("").astype(str).agg(" ".join, axis=1).str.contains(query, case=False)
            # Search in Index (Directly, without reset_index)
            mask_index = df_all.index.to_series().astype(str).str.contains(query, case=False)
            # Combine results with logical OR
            final_filter = mask_cols | mask_index
            # Apply the filter
            result = df_all[final_filter]

            items = []
            for idx, row in result.iterrows():
                fund_currency = row.get("currency", "USD")  # fundCurrency from overview
                etf_name = row["name"]

                for ccy in self.SUPPORTED_CURRENCIES:
                    flag = self.CURRENCY_FLAGS[ccy]
                    # 👑 marks the fund's native NAV currency
                    crown = "👑" if ccy == fund_currency else ""
                    items.append(
                        {
                            "identifier": idx,
                            "identifier_type": IdentifierType.ISIN,
                            "display_name": f"{flag}{crown} {etf_name}",
                            "currency": ccy,
                            "type": "ETF",
                        }
                    )
            return items
        except Exception as e:
            raise AssetSourceError(
                f"Search failed for '{query}' on JustETF: {e}",
                "SEARCH_ERROR",
                {"query": query, "error": str(e)},
            ) from e

    def validate_params(self, params: Dict | None) -> None:
        """Validate provider_params: currency must be in SUPPORTED_CURRENCIES."""
        if not params:
            return
        currency = params.get("currency")
        if currency and currency not in self.SUPPORTED_CURRENCIES:
            raise AssetSourceError(
                f"Unsupported currency '{currency}'. Must be one of: {', '.join(self.SUPPORTED_CURRENCIES)}",
                "INVALID_PARAMS",
                {"currency": currency, "supported": list(self.SUPPORTED_CURRENCIES)},
            )

    async def fetch_asset_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAAssetPatchItem | None:
        """Fetch asset metadata from JustETF using get_etf_overview."""
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            return None

        try:
            # Check cache
            cache_key = f"overview_{identifier}"
            cached, ok = _overview_cache.get(cache_key)

            if not ok:
                overview = get_etf_overview(identifier, include_gettex=False)
                _overview_cache.set(cache_key, overview)
            else:
                overview = cached

            # Build description
            description_parts = []

            if overview.get("description"):
                description_parts.append(overview["description"])

            ter = overview.get("ter")
            if ter:
                description_parts.append(f"TER: {ter}%")

            dist_policy = overview.get("distribution_policy")
            if dist_policy:
                description_parts.append(f"Distribution: {dist_policy}")

            short_description = " | ".join(description_parts) if description_parts else None
            if short_description and len(short_description) > 500:
                short_description = short_description[:497] + "..."

            # Build geographic area from countries
            geographic_area = None
            countries = overview.get("countries", [])
            if countries:
                distribution = {}
                total = Decimal("0")
                for country in countries:
                    country_name = country.get("name")
                    percentage = country.get("percentage")
                    if country_name and percentage is not None:
                        iso3 = _country_name_to_iso3(country_name)
                        if iso3:  # Skip unknown countries (None), keep "Other"
                            weight = Decimal(str(percentage)) / Decimal("100")
                            distribution[iso3] = weight
                            total += weight

                # Only create geographic_area if we have valid data
                if distribution and total > Decimal("0"):
                    # Renormalize to sum to 1.0
                    distribution = {k: v / total for k, v in distribution.items()}
                    try:
                        geographic_area = FAGeographicArea(distribution=distribution)
                    except Exception as e:
                        logger.warning(f"Could not create FAGeographicArea for {identifier}: {e}")

            # Build sector distribution using FASectorArea
            sector_area = None
            sectors = overview.get("sectors", [])
            if sectors:
                sector_distribution = {}
                sector_total = Decimal("0")
                for sector_item in sectors:
                    sector_name = sector_item.get("name")
                    percentage = sector_item.get("percentage")
                    if sector_name and percentage is not None:
                        weight = Decimal(str(percentage)) / Decimal("100")
                        # Accumulate if sector appears multiple times
                        if sector_name in sector_distribution:
                            sector_distribution[sector_name] += weight
                        else:
                            sector_distribution[sector_name] = weight
                        sector_total += weight

                if sector_distribution and sector_total > Decimal("0"):
                    # Renormalize to sum to 1.0
                    sector_distribution = {k: v / sector_total for k, v in sector_distribution.items()}
                    # Log warning for unknown sectors before normalization
                    for sector_name in sector_distribution:
                        if not validate_sector(sector_name):
                            logger.warning(
                                "Unknown sector from provider, mapped to Other",
                                provider_code="justetf",
                                identifier=identifier,
                                original_sector=sector_name,
                                mapped_to="Other",
                            )
                    try:
                        # FASectorArea will normalize sector names using FinancialSector enum
                        sector_area = FASectorArea(distribution=sector_distribution)
                    except Exception as e:
                        logger.warning(f"Could not create FASectorArea for {identifier}: {e}")

            classification = FAClassificationParams(
                short_description=short_description,
                geographic_area=geographic_area,
                sector_area=sector_area,
            )

            # Return the currency from provider_params (user's choice).
            # fund_currency from overview is the NAV denomination (e.g. USD) — informational only.
            selected_currency = self._get_currency(provider_params)

            # Extract ticker from overview (best-effort)
            ticker_val = overview.get("ticker") if "ticker" in overview else None

            return FAAssetPatchItem(
                asset_id=0,  # Placeholder, will be set by caller
                display_name=None,
                currency=selected_currency,
                asset_type=AssetType.ETF,
                icon_url=None,
                classification_params=classification,
                active=None,
                identifier_isin=identifier,  # ISIN is the search key for JustETF
                identifier_ticker=ticker_val if ticker_val else None,
            )
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier} from JustETF: {e}")
            return None

    def shutdown(self) -> None:  # pragma: no cover
        """Stop all persistent live-quote WebSocket threads."""
        shutdown_live_feeds()
