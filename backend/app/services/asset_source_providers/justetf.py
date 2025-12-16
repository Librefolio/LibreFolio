"""
JustETF provider for asset pricing.

Uses the justetf-scraping library to fetch ETF data from justetf.com.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FACurrentValue,
    FAHistoricalData,
    FAAssetPatchItem,
    FAPricePoint,
    FAClassificationParams,
    FAGeographicArea,
    FASectorArea,
)
from backend.app.services.asset_source import AssetSourceError, AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider

try:
    import justetf_scraping
    from justetf_scraping import get_etf_overview, get_gettex_quote, load_chart, load_overview
    import pandas as pd

    JUSTETF_AVAILABLE = True
except ImportError:
    justetf_scraping = None
    get_etf_overview = None
    get_gettex_quote = None
    load_chart = None
    load_overview = None
    pd = None
    JUSTETF_AVAILABLE = False

logger = get_logger(__name__)

# Cache TTL constants
CACHE_TTL_OVERVIEW = 3600  # 1 hour in seconds
CACHE_TTL_CHART = 3600  # 1 hour in seconds
CACHE_TTL_GETTEX = 30  # 30 seconds
CACHE_TTL_ETF_LIST = 3600  # 1 hour in seconds


class CachedData:
    """Simple cache wrapper with TTL support."""

    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, Any]] = {}

    def get(self, key: str, ttl_seconds: int) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            cached_time, value = self._cache[key]
            if (datetime.now() - cached_time).total_seconds() < ttl_seconds:
                return value
            # Expired, remove from cache
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self._cache[key] = (datetime.now(), value)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


# Global caches
_overview_cache = CachedData()
_chart_cache = CachedData()
_gettex_cache = CachedData()
_etf_list_cache = CachedData()


def _country_name_to_iso3(country_name: str) -> Optional[str]:
    """
    Convert country name to ISO 3166-1 alpha-3 code.
    Uses pycountry via geo_normalization utility.
    Returns None if not found or for "Other" category.
    """
    # Skip "Other" category
    if country_name.lower() == "other":
        return None

    try:
        from backend.app.utils.geo_normalization import normalize_country_to_iso3
        return normalize_country_to_iso3(country_name)
    except (ValueError, ImportError) as e:
        logger.debug(f"Could not normalize country '{country_name}': {e}")
        return None


@register_provider(AssetProviderRegistry)
class JustETFProvider(AssetSourceProvider):
    """JustETF.com data provider using the justetf-scraping library."""

    @classmethod
    def etf_list(cls) -> "pd.DataFrame":
        """Get cached ETF list."""
        cached = _etf_list_cache.get("etf_list", CACHE_TTL_ETF_LIST)
        if cached is not None:
            return cached

        df = load_overview()
        _etf_list_cache.set("etf_list", df)
        return df

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

    def get_icon(self) -> str:
        """Return provider icon URL (hardcoded)."""
        return "https://www.justetf.com/android-chrome-144x144.png?v2"

    @property
    def test_cases(self) -> list[dict]:
        """Test cases with identifier and provider_params."""
        return [
            {
                'identifier': 'IE00B4L5Y983',  # iShares Core MSCI World UCITS ETF USD (Acc)
                'identifier_type': IdentifierType.ISIN,
                'provider_params': None,
            }
        ]

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FACurrentValue:
        """
        Fetch current price from JustETF using gettex real-time WebSocket data.
        """
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            raise AssetSourceError(
                f"JustETF provider only supports ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
            )

        try:
            # Check cache first
            cache_key = f"gettex_{identifier}"
            cached = _gettex_cache.get(cache_key, CACHE_TTL_GETTEX)

            if cached is None:
                # Fetch from gettex WebSocket
                quote = await asyncio.to_thread(get_gettex_quote, identifier)
                if quote is None:
                    raise AssetSourceError(
                        f"No gettex quote available for {identifier}",
                        "NOT_FOUND",
                    )
                _gettex_cache.set(cache_key, quote)
            else:
                quote = cached

            # Use 'last' price as the current value
            price = quote.get('last') or quote.get('mid')
            if price is None:
                raise AssetSourceError(
                    f"No price data in gettex quote for {identifier}",
                    "NOT_FOUND",
                )

            currency = quote.get('currency', 'EUR')
            timestamp = quote.get('timestamp')

            # Convert timestamp to date
            if isinstance(timestamp, datetime):
                as_of_date = timestamp.date()
            elif isinstance(timestamp, str):
                as_of_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
            else:
                as_of_date = date.today()

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
        start_date: date,
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
            currency: str = "EUR"
            add_current = end_date >= date.today()

            # Check cache
            cache_key = f"chart_{identifier}_{add_current}"
            cached_df = _chart_cache.get(cache_key, CACHE_TTL_CHART)

            if cached_df is None:
                df = await asyncio.to_thread(load_chart, identifier, "EUR", add_current)
                _chart_cache.set(cache_key, df)
            else:
                df = cached_df

            df = df.reset_index()

            # Filter by date range
            df['date_only'] = pd.to_datetime(df['date']).dt.date
            df = df[(df['date_only'] >= start_date) & (df['date_only'] <= end_date)]

            prices: List[FAPricePoint] = []
            for row in df.itertuples():
                row_date = row.date_only if hasattr(row, 'date_only') else row.date.date()
                prices.append(FAPricePoint(
                    date=row_date,
                    open=None,
                    high=None,
                    low=None,
                    close=Decimal(str(row.quote)),
                    volume=None,
                    currency=currency,
                    backward_fill_info=None,
                ))

            return FAHistoricalData(prices=prices, currency=currency, source=self.provider_name)
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
        """Search for ETFs in the cached ETF list."""
        self._check_availability()
        try:
            df_all = await asyncio.to_thread(JustETFProvider.etf_list)
            # Define only the normal columns (exclude index 'isin' from here)
            cols_only = ['name', 'ticker', 'wkn']
            # Search in columns (Vectorized)
            mask_cols = df_all[cols_only].astype(str).agg(' '.join, axis=1).str.contains(query, case=False)
            # Search in Index (Directly, without reset_index)
            mask_index = df_all.index.to_series().astype(str).str.contains(query, case=False)
            # Combine results with logical OR
            final_filter = mask_cols | mask_index
            # Apply the filter
            result = df_all[final_filter]
            return [
                {
                    "identifier": idx,
                    "display_name": row['name'],
                    "currency": None,  # Not provided by search
                    "type": "ETF",
                }
                for idx, row in result.iterrows()
            ]
        except Exception as e:
            raise AssetSourceError(
                f"Search failed for '{query}' on JustETF: {e}",
                "SEARCH_ERROR",
                {"query": query, "error": str(e)},
            ) from e

    def validate_params(self, params: Dict | None) -> None:
        """JustETF provider does not require any params."""
        pass

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
            cached = _overview_cache.get(cache_key, CACHE_TTL_OVERVIEW)

            if cached is None:
                overview = await asyncio.to_thread(get_etf_overview, identifier, include_gettex=False)
                _overview_cache.set(cache_key, overview)
            else:
                overview = cached

            # Build description
            description_parts = []

            if overview.get('description'):
                description_parts.append(overview['description'])

            ter = overview.get('ter')
            if ter:
                description_parts.append(f"TER: {ter}%")

            dist_policy = overview.get('distribution_policy')
            if dist_policy:
                description_parts.append(f"Distribution: {dist_policy}")

            short_description = " | ".join(description_parts) if description_parts else None
            if short_description and len(short_description) > 500:
                short_description = short_description[:497] + "..."

            # Build geographic area from countries
            geographic_area = None
            countries = overview.get('countries', [])
            if countries:
                distribution = {}
                total = Decimal('0')
                for country in countries:
                    country_name = country.get('name')
                    percentage = country.get('percentage')
                    if country_name and percentage is not None:
                        iso3 = _country_name_to_iso3(country_name)
                        if iso3:  # Skip "Other" and unknown countries
                            weight = Decimal(str(percentage)) / Decimal('100')
                            distribution[iso3] = weight
                            total += weight

                # Only create geographic_area if we have valid data
                if distribution and total > Decimal('0'):
                    # Renormalize to sum to 1.0
                    distribution = {k: v / total for k, v in distribution.items()}
                    try:
                        geographic_area = FAGeographicArea(distribution=distribution)
                    except Exception as e:
                        logger.warning(f"Could not create FAGeographicArea for {identifier}: {e}")

            # Build sector distribution using FASectorArea
            sector_area = None
            sectors = overview.get('sectors', [])
            if sectors:
                sector_distribution = {}
                sector_total = Decimal('0')
                for sector_item in sectors:
                    sector_name = sector_item.get('name')
                    percentage = sector_item.get('percentage')
                    if sector_name and percentage is not None:
                        weight = Decimal(str(percentage)) / Decimal('100')
                        # Accumulate if sector appears multiple times
                        if sector_name in sector_distribution:
                            sector_distribution[sector_name] += weight
                        else:
                            sector_distribution[sector_name] = weight
                        sector_total += weight

                if sector_distribution and sector_total > Decimal('0'):
                    # Renormalize to sum to 1.0
                    sector_distribution = {k: v / sector_total for k, v in sector_distribution.items()}
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

            return FAAssetPatchItem(
                asset_id=0,  # Placeholder, will be set by caller
                display_name=None,
                currency=None,
                asset_type=AssetType.ETF,
                icon_url=None,
                classification_params=classification,
                active=None,
            )
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier} from JustETF: {e}")
            return None
