"""
Asset pricing source service.

This module provides:
- AssetSourceProvider: Abstract base class for pricing providers
- AssetSourceManager: Manager for provider operations and price data
- Synthetic yield calculation for SCHEDULED_YIELD assets
- Backward-fill logic for missing price data
- Helper functions for decimal precision

Similar to fx.py but for price_history table (asset prices vs FX rates).

Key differences from FX:
- Table: price_history (not fx_rates)
- Fields: OHLC (open/high/low/close) + volume (not single rate)
- Lookup: (asset_id, date) not (base, quote, date)
- Synthetic yield: Calculated on-demand for SCHEDULED_YIELD assets

Design principles:
- Bulk-first: All operations have bulk version as PRIMARY
- Singles call bulk with 1 element
- DB optimization: Minimize queries (typically 1-3 max)
- Parallel provider calls where possible
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import AsyncGenerator, Dict, List, Optional

import structlog
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetProviderAssignment,
    AssetType,
    BrokerUserAccess,
    IdentifierType,
    PriceHistory,
    ProviderInputType,
    Transaction,
    User,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkMetadataRefreshResponse,
    FABulkRefreshResponse,
    FABulkRemoveResponse,
    FACurrentValue,
    FAHistoricalData,
    FAMetadataRefreshResult,
    FAPriceDeleteResult,
    FAPricePoint,
    FAProviderAssignmentItem,
    FAProviderAssignmentResult,
    FAProviderRemovalResult,
    FARefreshItem,
    FARefreshResult,
    FAUpsert,
    SyncStatus,
)
from backend.app.schemas.assets import (
    FAAinfoFiltersRequest,
    FAAssetCreateItem,
    FAAssetCreateResult,
    FAAssetDeleteResult,
    FAAssetPatchItem,
    FAAssetPatchResult,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FAClassificationParams,
    FAinfoResponse,
    FAMetadataChangeDetail,
)
from backend.app.schemas.common import Currency, FxBackwardFillInfo, OldNew
from backend.app.schemas.prices import AssetBackwardFillInfo, FAAssetEventPoint, FAAssetEventPointOut, FAEventBulkDeleteResponse, FAEventDeleteItemResult, FAPriceQueryResult
from backend.app.schemas.provider import (
    FAProviderConfigBase,
    FAProviderProbeResponse,
    FAProviderRefreshFieldsDetail,
    FAProviderSearchResponse,
    FAProviderSearchResultItem,
    ProbeCurrentPriceResult,
    ProbeHistoryResult,
    ProbeMetadataResult,
    ProbeOperation,
)
from backend.app.services.fx import convert_bulk
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.utils.cache_utils import get_ttl_cache
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.decimal_utils import truncate_priceHistory

# Initialize structured logger
logger = structlog.get_logger(__name__)


# ============================================================================
# CORE CACHES — automatic TTL expiration via theine timer wheel
# ============================================================================

_asset_history_cache = get_ttl_cache("asset_history_fetch", maxsize=500, ttl=900)  # 15 min
_asset_current_cache = get_ttl_cache("asset_current_fetch", maxsize=300, ttl=120)  # 2 min
_asset_metadata_cache = get_ttl_cache("asset_metadata_fetch", maxsize=200, ttl=1800)  # 30 min
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)  # 24h — individual items
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)  # 15 min — query→results


# ============================================================================
# THREAD ISOLATION FOR PROVIDER CALLS
# ============================================================================


async def _run_provider_in_thread(coro_factory, *, timeout: float = 60.0):
    """
    Run a provider coroutine in a dedicated thread with its own event loop.

    Protects the main event loop from blocking provider implementations.
    Even a well-written async provider (httpx) works fine — it just uses
    the thread's event loop instead of the main one.

    A badly-written provider that does `requests.get()` directly in an
    async def will block the thread, NOT the main event loop.

    Args:
        coro_factory: Zero-arg callable that returns the coroutine to run.
                     Example: lambda: provider.get_current_value(id, type, params)
        timeout: Maximum time to wait (seconds). Default 60s.

    Returns:
        Result of the coroutine.

    Raises:
        asyncio.TimeoutError: If provider takes longer than timeout.
        Any exception raised by the provider.
    """

    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )


# (Pydantic models for API request/response live in backend.app.schemas.assets)
# They are imported by API modules when needed


# ============================================================================
# EXCEPTIONS
# ============================================================================


class AssetSourceError(Exception):
    """Base exception for asset source errors."""

    def __init__(self, message: str, error_code: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


class AssetSourceProvider(ABC):
    """
    Abstract base class for asset pricing providers (plugins).

    ARCHITECTURE: Plugin vs Core Responsibilities
    =============================================

    PLUGIN (this class implementations) is responsible for:
    - Fetching RAW data from external sources (APIs, web scraping, etc.)
    - Returning data in the expected schema format (FACurrentValue, FAHistoricalData)
    - Handling provider-specific errors and converting them to AssetSourceError
    - Validating provider_params specific to each provider

    CORE (AssetSourceService) is responsible for:
    - Database storage and caching of fetched data
    - Backward-filling historical prices (filling gaps with last known value)
    - Currency conversion if needed
    - Merging data from multiple sources
    - Transaction management and error recovery

    CORE INFRASTRUCTURE: Thread Isolation & Cache
    ==============================================

    The core runs ALL provider method calls (get_current_value, get_history_value,
    fetch_asset_metadata, search) in a **dedicated thread with its own event loop**
    via _run_provider_in_thread(). This means:

    - You do NOT need asyncio.to_thread() in your provider — the core handles it.
    - Even sync libraries (requests, yfinance) are safe to call directly in your
      async def methods — they block the dedicated thread, NOT the main event loop.
    - Timeout protection: the core enforces per-call timeouts.

    The core also caches results automatically:
    - get_history_value → smart range cache (15min TTL, per-date granularity)
    - get_current_value → 2min TTL cache
    - fetch_asset_metadata → 30min TTL cache
    - search → 2-layer cache (query-level 15min + item-level 24h)

    If you have expensive sub-operations (e.g., currency discovery, ETF list fetch),
    use your own internal caches — the core caches only the final result.

    Example flow for get_history_value:
    1. Core calls plugin.get_history_value(start, end)
    2. Plugin fetches RAW prices from external API (only trading days)
    3. Plugin returns FAHistoricalData with prices list (may have gaps)
    4. Core applies _backward_fill_prices() to fill weekends/holidays
    5. Core stores filled data in database

    Required implementations:
    - provider_code: Unique identifier for this provider
    - provider_name: Human-readable name
    - test_cases: Test data for automated testing
    - get_current_value(): Fetch latest price
    - get_history_value(): Fetch historical prices (raw, no filling)
    - test_search_query: Search query for tests (None if search unsupported)

    Optional overrides:
    - get_icon(): Provider icon URL
    - supports_history: False if provider cannot fetch historical data
    - search(): Search for assets by query
    - validate_params(): Validate provider-specific parameters
    - fetch_asset_metadata(): Fetch asset metadata (type, sector, etc.)

    Providers auto-register via @register_provider(AssetProviderRegistry) decorator.
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """
        Unique provider identifier used in database and API.

        Examples: 'yfinance', 'justetf', 'cssscraper'

        Must be:
        - Lowercase alphanumeric with underscores
        - Unique across all registered providers
        - Stable (changing breaks existing assets)
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable provider name for UI display.

        Examples: 'Yahoo Finance', 'JustETF', 'CSS Web Scraper'
        """
        pass

    @property
    def get_icon(self) -> str | None:
        """
        Provider icon URL for UI display.

        Returns:
            URL string (remote or local path), or None for default icon
        """
        return None

    @property
    def provider_help_url(self) -> str | None:
        """
        URL to the provider documentation page served by the running instance.

        Returns:
            URL string (e.g., "/mkdocs/user/assets/providers/yahoo-finance/"), or None
        """
        return None

    @classmethod
    def generate_static_url(cls, relative_path: str) -> str:
        """
        Generate URL for a static asset in the plugin's static folder.

        Use this to reference icons, images, or other static files
        bundled with your plugin.

        Structure:
            asset_source_providers/static/{relative_path}

        Args:
            relative_path: Path relative to static folder (e.g., "yfinance/logo.png")

        Returns:
            Full URL path (e.g., "/api/v1/uploads/plugin/asset/yfinance/logo.png")

        Example:
            class YahooFinanceProvider(AssetSourceProvider):
                def get_icon(self) -> str:
                    return self.generate_static_url("yfinance/logo.png")
        """
        return f"/api/v1/uploads/plugin/asset/{relative_path}"

    @property
    @abstractmethod
    def test_cases(self) -> list[dict]:
        """
        Test cases for automated provider testing.

        Each test case must include:
        - identifier: str - Asset identifier to test
        - identifier_type: IdentifierType - Type of identifier
        - provider_params: dict | None - Provider-specific params (if needed)

        Example:
            [
                {
                    'identifier': 'AAPL',
                    'identifier_type': IdentifierType.TICKER,
                    'provider_params': None
                },
                {
                    'identifier': 'https://example.com/price',
                    'identifier_type': IdentifierType.URL,
                    'provider_params': {'css_selector': '.price', 'currency': 'EUR'}
                }
            ]
        """
        pass

    @abstractmethod
    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
    ) -> FACurrentValue:
        """
        Fetch current/latest price for an asset.

        PLUGIN RESPONSIBILITY:
        - Fetch the latest available price from external source
        - Return price with currency and timestamp
        - Handle provider-specific authentication/rate limiting

        CORE WILL:
        - Cache the result if needed
        - Store in database
        - Handle currency conversion if requested

        Args:
            identifier: Asset identifier (ticker, ISIN, URL, etc.)
            identifier_type: Type of identifier (helps provider parse it)
            provider_params: Provider-specific config (e.g., CSS selectors, API keys)

        Returns:
            FACurrentValue with:
            - value: Decimal price
            - currency: ISO currency code (e.g., 'USD', 'EUR')
            - as_of_date: Date of the price
            - source: Provider name for attribution

        Raises:
            AssetSourceError: With appropriate error_code:
            - INVALID_IDENTIFIER_TYPE: Wrong identifier type for this provider
            - NO_DATA: Asset not found or no price available
            - FETCH_ERROR: Network/API error
            - MISSING_PARAMS: Required provider_params missing
        """
        pass

    @property
    def supports_history(self) -> bool:
        """
        Whether this provider can fetch historical price data.

        Override to return False for providers that only support current prices
        (e.g., simple web scrapers without historical data access).

        Default: True (most providers support history)
        """
        return True

    @property
    def supports_search(self) -> bool:
        """
        Whether this provider supports asset search functionality.

        Override to return False for providers that cannot search for assets
        (e.g., scheduled investments, CSS scrapers).

        Default: True if test_search_query is not None, False otherwise.
        This heuristic works for most providers. Override explicitly when needed.
        """
        return self.test_search_query is not None

    @abstractmethod
    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: date_type,
        end_date: date_type,
    ) -> FAHistoricalData:
        """
        Fetch historical prices for a date range.

        PLUGIN RESPONSIBILITY:
        - Fetch RAW historical prices from external source
        - Return only actual data points (trading days with prices)
        - DO NOT fill gaps (weekends, holidays) - core handles this
        - DO NOT set backward_filled flag - core handles this

        CORE WILL:
        - Apply backward_fill_prices() to fill gaps with last known value
        - Set backward_filled=True on filled records
        - Store all records (real + filled) in database
        - Handle date range chunking for large requests

        Example:
            Plugin returns: [Mon: 100, Tue: 101, Wed: 102, Fri: 104]
            Core fills to:  [Mon: 100, Tue: 101, Wed: 102, Thu: 102*, Fri: 104]
                            (* = backward_filled=True)

        Args:
            identifier: Asset identifier
            identifier_type: Type of identifier
            provider_params: Provider-specific config
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            FAHistoricalData with:
            - prices: List[FAPricePoint] - Raw prices from source
              Each FAPricePoint has: date, open, high, low, close, volume
              (open/high/low/volume can be None if not available)
            - currency: ISO currency code
            - source: Provider name

        Raises:
            AssetSourceError: With appropriate error_code:
            - NOT_SUPPORTED: If supports_history is False
            - NO_DATA: No data available for date range
            - FETCH_ERROR: Network/API error
        """
        pass

    @property
    @abstractmethod
    def test_search_query(self) -> str | None:
        """
        Search query string for automated testing.

        Return None if this provider does not support search functionality.
        Otherwise return a query that should return at least one result.

        Examples:
            'Apple' - for stock providers
            'MSCI World' - for ETF providers
            None - for CSS scrapers (no search)
        """
        pass

    async def search(self, query: str) -> list[dict]:
        """
        Search for assets matching a query string.

        PLUGIN RESPONSIBILITY:
        - Query external source for matching assets
        - Return standardized result format
        - Handle empty results gracefully (return [])

        CORE WILL:
        - Present results to user for selection
        - Use selected result to create/link asset

        Args:
            query: User search string (e.g., 'Apple', 'MSCI World ETF')

        Returns:
            List of dicts, each containing:
            - identifier: str - Provider-specific identifier
            - identifier_type: IdentifierType - Type of identifier (ISIN, TICKER, etc.)
            - display_name: str - Human-readable name
            - currency: str | None - Trading currency if known
            - type: str | None - Asset type if known (e.g., 'stock', 'etf')

            Empty list if no matches found.

        Raises:
            AssetSourceError:
            - NOT_SUPPORTED: If search not implemented (default behavior)
            - FETCH_ERROR: If search fails due to network/API error
        """
        raise AssetSourceError(
            f"Search not supported by {self.provider_name}",
            "NOT_SUPPORTED",
            {"provider": self.provider_code},
        )

    @abstractmethod
    def validate_params(self, params: dict | None) -> None:
        """
        Validate provider_params structure before use.

        PLUGIN RESPONSIBILITY:
        - Check that all required parameters are present
        - Validate parameter types and formats
        - Raise AssetSourceError if validation fails

        CORE WILL:
        - Call this before get_current_value/get_history_value
        - Store validated params in database

        Implementation patterns:

        1. No params required (most providers):
            def validate_params(self, params: dict | None) -> None:
                pass  # Accept anything

        2. Optional params with defaults:
            def validate_params(self, params: dict | None) -> None:
                if params is None:
                    return  # Use defaults
                # Validate specific keys if present

        3. Required params (e.g., CSS scraper):
            def validate_params(self, params: dict | None) -> None:
                if not params:
                    raise AssetSourceError("Params required", "MISSING_PARAMS")
                if 'css_selector' not in params:
                    raise AssetSourceError("css_selector required", "MISSING_PARAMS")

        Args:
            params: Provider parameters to validate (can be None)

        Raises:
            AssetSourceError: With error_code 'MISSING_PARAMS' or 'INVALID_PARAMS'
        """
        pass  # Default: no validation, accepts any params including None

    @property
    def params_schema(self) -> list[dict]:
        """
        Schema of fields required by provider_params for this provider.
        The frontend uses this to generate dynamic forms.
        Default: empty list (no parameters required).

        Returns:
            List of dicts with keys: key, type, required, description, options, default
        """
        return []

    @property
    def accepted_identifier_types(self) -> list[ProviderInputType]:  # pragma: no cover
        """
        Input types accepted by this provider (for frontend identifier type dropdown).
        Uses ProviderInputType (TICKER, ISIN, URL, AUTO_GENERATED), NOT IdentifierType.
        Default: [TICKER, ISIN].
        """
        return [ProviderInputType.TICKER, ProviderInputType.ISIN]

    @staticmethod
    def map_input_type_to_identifier_type(input_type: str) -> IdentifierType:
        """
        Map a ProviderInputType value to the corresponding IdentifierType.

        Used internally when provider plugin methods require IdentifierType
        (e.g., get_current_value, get_history_value) but the stored/incoming
        value is a ProviderInputType string.
        """
        mapping = {
            ProviderInputType.TICKER.value: IdentifierType.TICKER,
            ProviderInputType.ISIN.value: IdentifierType.ISIN,
            ProviderInputType.URL.value: IdentifierType.OTHER,
            ProviderInputType.AUTO_GENERATED.value: IdentifierType.UUID,
        }
        if input_type in mapping:
            return mapping[input_type]
        # Fallback: try direct match (e.g., TICKER → TICKER)
        try:
            return IdentifierType(input_type)
        except ValueError:
            return IdentifierType.OTHER

    @staticmethod
    def map_identifier_type_to_input_type(id_type: str) -> ProviderInputType | None:
        """
        Reverse mapping: IdentifierType → ProviderInputType.

        Used when auto-populating asset identifier columns from provider data.
        Returns None if no matching ProviderInputType exists (e.g., CUSIP, SEDOL, FIGI
        have no provider equivalent — they are asset-record-only identifiers).
        """
        mapping = {
            IdentifierType.TICKER.value: ProviderInputType.TICKER,
            IdentifierType.ISIN.value: ProviderInputType.ISIN,
            IdentifierType.OTHER.value: ProviderInputType.URL,
            IdentifierType.UUID.value: ProviderInputType.AUTO_GENERATED,
        }
        return mapping.get(id_type)

    async def fetch_asset_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> FAAssetPatchItem | None:
        """
        Fetch asset metadata from provider (optional feature).

        PLUGIN RESPONSIBILITY:
        - Fetch metadata from external source if available
        - Return FAAssetPatchItem with available fields
        - Return None if metadata not supported or unavailable
        - DO NOT store in database - core handles this

        CORE WILL:
        - Call this when user requests metadata refresh
        - Merge returned metadata with existing asset data
        - Store updated metadata in database

        Override this method if your provider can fetch:
        - asset_type: Stock, ETF, Bond, etc.
        - short_description: Brief description of the asset
        - classification_params: Sector, geographic distribution, etc.

        Args:
            identifier: Asset identifier for provider
            identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
            provider_params: Provider-specific configuration

        Returns:
            FAAssetPatchItem with metadata fields populated:
            - asset_id: Set to 0 (placeholder, core will set real ID)
            - asset_type: AssetType enum if known
            - classification_params: FAClassificationParams with:
              - sector: Primary sector (e.g., 'Technology')
              - geographic_area: FAGeographicArea with distribution dict
              - short_description: Brief description

            Return None if:
            - Metadata fetching not supported by this provider
            - Asset not found
            - Metadata unavailable for this asset

        Raises:
            AssetSourceError: On fetch failure (network error, etc.)
        """
        return None  # Default: metadata not supported

    def get_asset_url(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> str | None:
        """
        Generate URL to the provider's page for this specific asset.

        Used by the frontend to show a "Go to Provider Page" link.
        Override in subclasses that have public web pages.

        Args:
            identifier: Asset identifier
            identifier_type: Type of identifier
            provider_params: Provider-specific params

        Returns:
            URL string or None if provider has no web page for assets
        """
        return None

    def shutdown(self) -> None:  # pragma: no cover  # noqa: B027 — intentional no-op default
        """
        Cleanup resources on application shutdown.

        Override to release persistent connections, stop background threads,
        flush caches, etc.  Called once per provider during app lifespan teardown
        via ``AssetProviderRegistry.shutdown_all_providers()``.

        Default: no-op.
        """
        pass


# ============================================================================
# ASSET SOURCE MANAGER
# ============================================================================


class AssetSourceManager:
    """
    Manager for asset pricing operations.

    Responsibilities:
    - Provider assignment CRUD
    - Price data refresh (via providers)
    - Manual price CRUD
    - Price queries with backward-fill

    All methods follow bulk-first design:
    - Bulk operations are PRIMARY
    - Single operations call bulk with 1 element
    - DB queries optimized (typically 1-3 max)
    """

    # ========================================================================
    # PROVIDER ASSIGNMENT METHODS
    # ========================================================================
    @staticmethod
    async def bulk_assign_providers(
        assignments: List[FAProviderAssignmentItem],
        session: AsyncSession,
    ) -> list[FAProviderAssignmentResult]:
        """
        Bulk assign/update providers to assets (PRIMARY bulk method).

        Args:
            assignments: List of FAProviderAssignmentItem
            session: AsyncSession

        Returns:
            List of FAProviderAssignmentResult

        Optimized: 1 delete + 1 insert query
        """
        if not assignments:
            return []

        results = []
        asset_ids = [a.asset_id for a in assignments]

        # UPSERT pattern: SELECT existing, UPDATE if exists, INSERT if new
        # This preserves assignment IDs across reconfigurations,
        # keeping AssetEvent.provider_assignment_id FK valid.
        existing_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        existing_result = await session.execute(existing_stmt)
        existing_map: Dict[int, AssetProviderAssignment] = {row.asset_id: row for row in existing_result.scalars().all()}

        for a in assignments:
            raw_params = a.provider_params
            if isinstance(raw_params, dict):
                params_to_store = json.dumps(raw_params)
            else:
                params_to_store = raw_params

            # Map identifier_type to valid ProviderInputType before storing
            # Handles both ProviderInputType values ("TICKER","URL","AUTO_GENERATED")
            # and IdentifierType values ("OTHER"→URL, "UUID"→AUTO_GENERATED)
            mapped_type = a.identifier_type
            try:
                ProviderInputType(mapped_type)
            except ValueError:
                pit = AssetSourceProvider.map_identifier_type_to_input_type(mapped_type)
                mapped_type = pit.value if pit else ProviderInputType.URL.value

            # Handle identifier: if AUTO_GENERATED and empty/None, leave None
            identifier_val = a.identifier
            if mapped_type == ProviderInputType.AUTO_GENERATED.value and not identifier_val:
                identifier_val = None

            existing = existing_map.get(a.asset_id)
            if existing:
                # UPDATE existing assignment (preserves id → FK stays valid)
                existing.provider_code = a.provider_code
                existing.identifier = identifier_val
                existing.identifier_type = mapped_type
                existing.provider_params = params_to_store
                existing.fetch_interval = a.fetch_interval
            else:
                # INSERT new assignment
                new_assignment = AssetProviderAssignment(
                    asset_id=a.asset_id,
                    provider_code=a.provider_code,
                    identifier=identifier_val,
                    identifier_type=mapped_type,
                    provider_params=params_to_store,
                    fetch_interval=a.fetch_interval,
                    last_fetch_at=None,
                )
                session.add(new_assignment)

        # Remove assignments for asset_ids no longer in the batch
        # (only relevant when called from full-replace endpoints)
        await session.commit()

        # Build results and auto-populate metadata
        for assignment in assignments:
            result = FAProviderAssignmentResult(
                asset_id=assignment.asset_id,
                success=True,
                message=f"Provider {assignment.provider_code} assigned",
                fields_detail=None,  # No auto-refresh during assignment
            )

            # Try to auto-populate metadata from provider
            try:
                # Get provider instance
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)

                if provider:
                    # Get asset to fetch currency and current metadata
                    asset_result = await session.execute(select(Asset).where(Asset.id == assignment.asset_id))
                    asset = asset_result.scalar_one_or_none()

                    if asset:
                        # Try to fetch metadata (returns None if not supported)
                        try:
                            _id = assignment.identifier
                            _id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)
                            _params = assignment.provider_params
                            patch_item = await _run_provider_in_thread(lambda _p=provider, _i=_id, _it=_id_type, _pr=_params: _p.fetch_asset_metadata(_i, _it, _pr), timeout=30.0)

                            if patch_item:
                                # Set correct asset_id
                                patch_item.asset_id = assignment.asset_id

                                # Apply metadata to asset
                                changes_count = 0

                                # Update asset_type if provided
                                if patch_item.asset_type and patch_item.asset_type != asset.asset_type:
                                    asset.asset_type = patch_item.asset_type
                                    changes_count += 1

                                # Update classification_params if provided
                                if patch_item.classification_params:
                                    # Parse current classification_params (JSON string -> object)
                                    current_params = None
                                    if asset.classification_params:
                                        try:
                                            current_dict = json.loads(asset.classification_params)
                                            current_params = FAClassificationParams(**current_dict)
                                        except Exception:
                                            pass  # Invalid JSON, start fresh

                                    # Apply partial update
                                    updated_params = AssetMetadataService.apply_partial_update(current_params, patch_item.classification_params)

                                    # Serialize back to JSON
                                    asset.classification_params = json.dumps(updated_params.model_dump(mode="json", exclude_none=True))
                                    changes_count += 1

                                if changes_count > 0:
                                    await session.commit()

                                logger.info(
                                    "Metadata auto-populated from provider",
                                    asset_id=assignment.asset_id,
                                    provider=assignment.provider_code,
                                    changes_count=changes_count,
                                )
                            else:
                                result.metadata_updated = False
                        except Exception as e:
                            # Log but don't fail assignment
                            logger.warning(
                                "Failed to fetch metadata from provider",
                                asset_id=assignment.asset_id,
                                provider=assignment.provider_code,
                                error=str(e),
                            )
            except Exception as e:
                # Log but don't fail assignment
                logger.warning(
                    "Error during metadata auto-populate",
                    asset_id=assignment.asset_id,
                    error=str(e),
                )

            results.append(result)

        return results

    @staticmethod
    async def bulk_remove_providers(asset_ids: list[int], session: AsyncSession) -> FABulkRemoveResponse:
        """
        Bulk remove provider assignments (PRIMARY bulk method).

        Args:
            asset_ids: List of asset IDs
            session: Database session

        Returns:
            FABulkRemoveResponse with results and success count

        Optimized: 1 DELETE query with WHERE IN
        """
        if not asset_ids:
            return FABulkRemoveResponse(results=[], success_count=0)
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids)))
        await session.commit()
        results = [
            FAProviderRemovalResult(
                asset_id=aid,
                success=True,
                deleted_count=1,  # Always 1 for successful provider removal
                message="Provider removed",
            )
            for aid in asset_ids
        ]
        return FABulkRemoveResponse(results=results, success_count=len(results), errors=[])

    @staticmethod
    async def refresh_assets_from_provider(asset_ids: list[int], session: AsyncSession) -> FABulkMetadataRefreshResponse:
        """
        Refresh asset data from assigned providers (bulk operation).

        **EXPLICIT REFRESH** - No auto-refresh during provider assignment.

        For each asset:
        1. Get provider assignment (identifier, identifier_type, provider_params)
        2. Call provider.fetch_asset_metadata(identifier, identifier_type, provider_params)
        3. Receive FAAssetPatchItem from provider
        4. Call AssetCRUDService.patch_assets_bulk
        5. Calculate refreshed_fields, missing_data_fields, ignored_fields dynamically

        Field classification:
        - refreshed_fields: Fields actually updated (present in patch and provider returned them)
        - missing_data_fields: Fields in FAAssetPatchItem.model_fields but not in provider response
        - ignored_fields: Always empty (future use: provider explicitly says "I don't support X")

        Args:
            asset_ids: List of asset IDs to refresh
            session: Database session

        Returns:
            FABulkMetadataRefreshResponse with per-asset results including fields_detail
        """
        results = []
        patches_to_apply = []
        asset_fields_map = {}  # Map asset_id -> fields_detail

        # Get all patchable fields from FAAssetPatchItem
        all_possible_fields = set(FAAssetPatchItem.model_fields.keys()) - {"asset_id"}

        for asset_id in asset_ids:
            try:
                # Get asset and assignment
                asset_stmt = select(Asset).where(Asset.id == asset_id)
                asset_result = await session.execute(asset_stmt)
                asset = asset_result.scalar_one_or_none()

                if not asset:
                    results.append(FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Asset {asset_id} not found"))
                    continue

                assignment_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)
                assignment_result = await session.execute(assignment_stmt)
                assignment = assignment_result.scalar_one_or_none()

                if not assignment:
                    results.append(
                        FAMetadataRefreshResult(
                            asset_id=asset_id,
                            success=False,
                            message=f"No provider assigned to asset {asset_id}",
                        )
                    )
                    continue

                # Get provider instance
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
                if not provider:
                    results.append(
                        FAMetadataRefreshResult(
                            asset_id=asset_id,
                            success=False,
                            message=f"Provider {assignment.provider_code} not found",
                        )
                    )
                    continue

                # Fetch metadata from provider (returns None if not supported)
                provider_params = json.loads(assignment.provider_params) if assignment.provider_params else None

                try:
                    # Check metadata cache first
                    meta_cache_key = (
                        assignment.provider_code,
                        assignment.identifier,
                        str(assignment.identifier_type),
                    )
                    cached_meta, meta_ok = _asset_metadata_cache.get(meta_cache_key)
                    if meta_ok:
                        patch_item = cached_meta
                        logger.debug(f"Metadata cache HIT for asset {asset_id}")
                    else:
                        _id = assignment.identifier
                        _id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)
                        _params = provider_params
                        patch_item = await _run_provider_in_thread(
                            lambda _p=provider, _i=_id, _it=_id_type, _pr=_params: _p.fetch_asset_metadata(_i, _it, _pr),
                            timeout=30.0,
                        )
                        _asset_metadata_cache.set(meta_cache_key, patch_item)
                except Exception as e:
                    results.append(
                        FAMetadataRefreshResult(
                            asset_id=asset_id,
                            success=False,
                            message=f"Failed to fetch metadata: {str(e)}",
                        )
                    )
                    continue

                if not patch_item:
                    results.append(
                        FAMetadataRefreshResult(
                            asset_id=asset_id,
                            success=False,
                            message=f"Provider {assignment.provider_code} returned no metadata (may not support metadata fetch)",
                        )
                    )
                    continue

                # Set correct asset_id
                patch_item.asset_id = asset_id

                # Calculate refreshed_fields with old/new values from patch_item
                patch_dict = patch_item.model_dump(exclude={"asset_id"}, exclude_unset=True)

                # Build OldNew list by comparing asset's current values with patch values
                refreshed_fields_with_changes: list[OldNew[str | None]] = []
                for field_name, new_value in patch_dict.items():
                    # Get old value from asset
                    old_value = getattr(asset, field_name, None)
                    # Convert to string representation for comparison
                    old_str = str(old_value) if old_value is not None else None
                    new_str = str(new_value) if new_value is not None else None

                    refreshed_fields_with_changes.append(OldNew(info=field_name, old=old_str, new=new_str))

                # Calculate missing_data_fields
                # Fields that are patchable but not returned by provider
                # Exclude fields that are not typically refreshable: display_name, currency, active
                refreshable_fields = all_possible_fields - {"display_name", "currency", "active"}
                provider_returned_fields = set(patch_dict.keys())
                missing_data_fields = list(refreshable_fields - provider_returned_fields)

                # Store patch and fields detail
                patches_to_apply.append(patch_item)
                asset_fields_map[asset_id] = FAProviderRefreshFieldsDetail(
                    refreshed_fields=refreshed_fields_with_changes,
                    missing_data_fields=missing_data_fields,
                    ignored_fields=[],  # Future use
                )

            except Exception as e:
                logger.error(f"Error preparing refresh for asset {asset_id}: {e}")
                results.append(FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Error: {str(e)}"))

        # Apply all patches in bulk using AssetCRUDService
        if patches_to_apply:
            patch_response = await AssetCRUDService.patch_assets_bulk(patches_to_apply, session)

            # Map patch results to refresh results with fields_detail
            for patch_result in patch_response.results:
                fields_detail = asset_fields_map.get(patch_result.asset_id)

                # Convert to FAMetadataRefreshResult with fields_detail
                results.append(
                    FAMetadataRefreshResult(
                        asset_id=patch_result.asset_id,
                        success=patch_result.success,
                        message=patch_result.message,
                        fields_detail=fields_detail,
                    )
                )

        success_count = sum(1 for r in results if r.success)

        return FABulkMetadataRefreshResponse(results=results, success_count=success_count, errors=[])

    @staticmethod
    async def get_asset_provider(asset_id: int, session: AsyncSession) -> Optional[AssetProviderAssignment]:
        """
        Fetch provider assignment for asset.

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            AssetProviderAssignment or None if not assigned
        """
        result = await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id))
        return result.scalar_one_or_none()

    # ========================================================================
    # MANUAL PRICE CRUD METHODS
    # ========================================================================

    @staticmethod
    async def bulk_upsert_prices(data: List[FAUpsert], session: AsyncSession) -> dict:
        """
        Bulk upsert prices manually (PRIMARY bulk method).

        Args:
            data: List of FAUpsert (asset_id + prices)
            session: Database session

        Returns:
            {inserted_count, updated_count, results: [{asset_id, count, message}, ...]}

        Raises:
            ValueError: if any price point has a currency that doesn't match
                ``asset.currency`` (I.2 — Supersedes E.3). The router translates
                this into **HTTP 400** with the offending dates. This is the
                definitive semantics after Block I — soft-skip with ``errors[]``
                was dropped because, post-I.5/I.8, the DataEditor no longer
                sends a per-point currency. See
                ``plan-phase07-transaction-Part3_1_Closure.md`` §E.3.

        Optimized: Batch operations per asset, minimize DB roundtrips.
        """
        if not data:
            return {"inserted_count": 0, "updated_count": 0, "results": []}

        total_inserted = 0
        results = []

        for item in data:
            asset_id = item.asset_id
            prices = item.prices

            if not prices:
                results.append({"asset_id": asset_id, "count": 0, "message": "No prices to upsert"})
                continue

            # Get asset currency for prices without explicit currency
            asset_result = await session.execute(select(Asset).where(Asset.id == asset_id))
            asset = asset_result.scalar_one_or_none()
            if not asset:
                results.append({"asset_id": asset_id, "count": 0, "message": f"Asset {asset_id} not found"})
                continue

            default_currency = asset.currency

            # Build PriceHistory objects for upsert (F.4 MERGE + sentinel semantics)
            # Strategy: fetch existing rows, merge per-field, DELETE affected dates, INSERT merged rows.
            # Sentinel rules apply to open/high/low/volume only (close stays required and is written verbatim):
            #   - field == None (omitted)  → preserve existing DB value (no-op)
            #   - field == -1              → write NULL
            #   - field >= 0               → write the provided value
            price_objects = []
            dates_to_upsert = []

            # I.2 — Currency coherence validation (Supersedes E.3).
            # Hard reject (not per-item skip): if ANY point has a currency that doesn't
            # match asset.currency, raise ValueError immediately so the router returns
            # 400 with the offending dates. This is defensive — the frontend, after
            # Block I, no longer sends a per-point currency (the column was dropped
            # from the DataEditor), so reaching this branch means the client is buggy
            # or someone is hitting the API directly.
            offending_dates: list[str] = []
            for price in prices:
                effective_currency = price.currency or default_currency
                if effective_currency != default_currency:
                    offending_dates.append(f"{price.date.isoformat()} ({effective_currency})")
            if offending_dates:
                raise ValueError(
                    f"Currency mismatch for asset {asset_id}: expected {default_currency} for all prices, " f"got {len(offending_dates)} date(s) with different currency: " + ", ".join(offending_dates[:10]) + (f" (+ {len(offending_dates) - 10} more)" if len(offending_dates) > 10 else "")
                )

            # Index valid points by date (all inputs are guaranteed matching currency past this line)
            valid_inputs: dict = {}
            for price in prices:
                valid_inputs[price.date] = price
                dates_to_upsert.append(price.date)

            # Fetch existing rows for MERGE (F.4)
            existing_rows: dict = {}
            if dates_to_upsert:
                existing_stmt = select(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates_to_upsert)))
                existing_res = await session.execute(existing_stmt)
                for row in existing_res.scalars().all():
                    existing_rows[row.date] = row

            # F.4 sentinel helper: -1 → None (SET NULL), None → preserve, else → write
            def _merge_field(new_val, existing_val):
                """F.4 sentinel merge for open/high/low/volume."""
                if new_val is None:
                    return existing_val  # no-op: preserve
                if new_val == Decimal("-1"):
                    return None  # SET NULL
                return new_val  # write

            for date_key, price in valid_inputs.items():
                existing = existing_rows.get(date_key)
                # Sentinel merge for auxiliary OHLC fields (open/high/low) + volume
                merged_open = _merge_field(price.open, existing.open if existing else None)
                merged_high = _merge_field(price.high, existing.high if existing else None)
                merged_low = _merge_field(price.low, existing.low if existing else None)
                merged_volume = _merge_field(price.volume, existing.volume if existing else None)

                price_obj = PriceHistory(
                    asset_id=asset_id,
                    date=price.date,
                    open=(truncate_priceHistory(merged_open, "open") if merged_open is not None else None),
                    high=(truncate_priceHistory(merged_high, "high") if merged_high is not None else None),
                    low=(truncate_priceHistory(merged_low, "low") if merged_low is not None else None),
                    close=truncate_priceHistory(price.close, "close"),
                    volume=merged_volume,
                    currency=price.currency or default_currency,
                    source_plugin_key="MANUAL",
                    fetched_at=None,
                )
                price_objects.append(price_obj)

            # Delete existing prices for these dates (MERGE = fetch + delete + insert)
            if dates_to_upsert:
                delete_stmt = delete(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates_to_upsert)))
                await session.execute(delete_stmt)

            # Bulk insert new prices
            session.add_all(price_objects)
            await session.commit()

            # Count as inserted
            total_inserted += len(price_objects)

            # I.2 — after hard-reject validation all inputs were accepted
            msg = f"Upserted {len(price_objects)} prices"

            results.append(
                {
                    "asset_id": asset_id,
                    "count": len(price_objects),
                    "message": msg,
                }
            )
        # update_count = 0 because SQLite doesn't distinguish
        return {"inserted_count": total_inserted, "updated_count": 0, "results": results}

    @staticmethod
    async def _upsert_asset_events(
        session: AsyncSession,
        asset_id: int,
        events: list[dict | FAAssetEventPoint],
        provider_assignment_id: Optional[int],
        default_currency: str,
    ) -> int:
        """Upsert asset events into the AssetEvent table.

        Uses DELETE + INSERT strategy (same as prices) for dedup on (asset_id, date, type).

        Args:
            session: Database session
            asset_id: Asset ID
            events: List of FAAssetEventPoint or dicts (parsed via Pydantic)
            provider_assignment_id: FK to asset_provider_assignments.id (None = manual)
            default_currency: Fallback currency

        Returns:
            Number of events upserted
        """
        if not events:
            return 0

        event_objects = []
        keys_to_delete = []

        for raw_evt in events:
            # Parse through Pydantic if raw dict; if already FAAssetEventPoint, use directly
            evt: FAAssetEventPoint = raw_evt if isinstance(raw_evt, FAAssetEventPoint) else FAAssetEventPoint(**raw_evt)

            evt_date = evt.date
            evt_type = evt.type
            keys_to_delete.append((evt_date, evt_type))

            # Extract amount and currency from Currency value object
            amount = evt.value.amount
            currency = evt.value.code or default_currency

            event_objects.append(
                AssetEvent(
                    asset_id=asset_id,
                    date=evt_date,
                    type=evt_type,
                    value=amount,
                    currency=currency,
                    provider_assignment_id=provider_assignment_id,
                    notes=evt.notes,
                )
            )

        # Delete existing events for these (date, type) pairs — only for the SAME provider
        # When provider_assignment_id is None, SQLAlchemy generates IS NULL which is correct
        for evt_date, evt_type in keys_to_delete:
            del_stmt = delete(AssetEvent).where(
                and_(
                    AssetEvent.asset_id == asset_id,
                    AssetEvent.date == evt_date,
                    AssetEvent.type == evt_type,
                    AssetEvent.provider_assignment_id == provider_assignment_id,
                )
            )
            await session.execute(del_stmt)

        # Insert new events
        session.add_all(event_objects)
        await session.commit()

        return len(event_objects)

    @staticmethod
    async def bulk_delete_prices(data: List[FAAssetDelete], session: AsyncSession) -> FABulkDeleteResponse:
        """
        Bulk delete price ranges (PRIMARY bulk method).

        Args:
            data: List of FAAssetDelete (asset_id + date_ranges)
            session: Database session

        Returns:
            FABulkDeleteResponse with results and deleted count

        Optimized: 1 SELECT COUNT + 1 DELETE query with complex WHERE
        Note: Cannot parallelize with gather - DB operations are sequential and interdependent
        """
        if not data:
            return FABulkDeleteResponse(deleted_count=0, results=[])

        # Build count per asset before deletion
        asset_delete_counts = {}

        for item in data:
            asset_id = item.asset_id
            ranges = item.date_ranges
            count = 0

            for date_range in ranges:
                start = date_range.start
                end = date_range.end or start  # Single day if no end

                # Count rows for this specific range
                count_stmt = (
                    select(func.count())
                    .select_from(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.asset_id == asset_id,
                            PriceHistory.date >= start,
                            PriceHistory.date <= end,
                        )
                    )
                )
                result = await session.execute(count_stmt)
                count += result.scalar()

            asset_delete_counts[asset_id] = count

        # Build complex OR conditions for all ranges
        conditions = []
        for item in data:
            asset_id = item.asset_id
            ranges = item.date_ranges

            for date_range in ranges:
                start = date_range.start
                end = date_range.end or start  # Single day if no end
                conditions.append(
                    and_(
                        PriceHistory.asset_id == asset_id,
                        PriceHistory.date >= start,
                        PriceHistory.date <= end,
                    )
                )

        if not conditions:
            return FABulkDeleteResponse(deleted_count=0, results=[])

        # Execute single DELETE with OR of all conditions
        stmt = delete(PriceHistory).where(or_(*conditions))
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount

        # Build results per asset with exact counts
        results = [
            FAPriceDeleteResult(
                asset_id=item.asset_id,
                success=True,
                deleted_count=asset_delete_counts.get(item.asset_id, 0),
                message=f"Deleted prices in {len(item.date_ranges)} range(s)",
            )
            for item in data
        ]

        return FABulkDeleteResponse(results=results, success_count=len(results), total_deleted=deleted_count, errors=[])

    # ========================================================================
    # PROVIDER PROBE (DRY-RUN)
    # ========================================================================

    @staticmethod
    async def probe_provider_config(
        config: FAProviderConfigBase,
        operations: list[ProbeOperation],
    ) -> FAProviderProbeResponse:
        """
        Probe a provider configuration without persisting anything.

        Executes requested operations in **parallel** via asyncio.gather
        and returns results with per-operation execution time.

        Accepts FAProviderConfigBase — child objects (FAProviderAssignmentItem,
        FAProviderProbeRequest) pass directly without field copying.
        """
        provider = AssetProviderRegistry.get_provider_instance(config.provider_code)
        if not provider:
            raise AssetSourceError(f"Unknown provider: {config.provider_code}", "UNKNOWN_PROVIDER")

        params = AssetSourceManager._parse_provider_params(config.provider_params)
        total_start = time.monotonic_ns()

        # Map ProviderInputType (from frontend) to IdentifierType (for provider methods)
        mapped_id_type = AssetSourceProvider.map_input_type_to_identifier_type(config.identifier_type)

        # Provider URL (always computed, synchronous)
        provider_url = provider.get_asset_url(config.identifier, mapped_id_type, params)

        # --- Build async tasks for each requested operation ---

        async def _probe_current_price() -> ProbeCurrentPriceResult:
            op_start = time.monotonic_ns()
            try:
                value = await _run_provider_in_thread(
                    lambda: provider.get_current_value(config.identifier, mapped_id_type, params),
                    timeout=15.0,
                )
                return ProbeCurrentPriceResult(
                    success=True,
                    value=value.value,
                    currency=value.currency,
                    as_of_date=str(value.as_of_date),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeCurrentPriceResult(
                    success=False,
                    error="Timeout after 15s",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeCurrentPriceResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        async def _probe_history() -> ProbeHistoryResult:
            op_start = time.monotonic_ns()
            try:
                end_date = date_type.today()
                start_date = end_date - timedelta(days=7)
                hist = await _run_provider_in_thread(
                    lambda: provider.get_history_value(config.identifier, mapped_id_type, params, start_date, end_date),
                    timeout=15.0,
                )
                points = hist.prices if hist else []
                date_range_str = None
                sample = None
                if points:
                    dates = [p.date for p in points]
                    date_range_str = f"{min(dates)} → {max(dates)}"
                    sample = [{"date": str(p.date), "close": round(float(p.close), 2)} for p in points[:10]]
                return ProbeHistoryResult(
                    success=True,
                    points_count=len(points),
                    date_range=date_range_str,
                    sample_prices=sample,
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeHistoryResult(
                    success=False,
                    error="Timeout after 15s",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeHistoryResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        async def _probe_metadata() -> ProbeMetadataResult:
            op_start = time.monotonic_ns()
            try:
                patch = await _run_provider_in_thread(
                    lambda: provider.fetch_asset_metadata(config.identifier, mapped_id_type, params),
                    timeout=15.0,
                )
                return ProbeMetadataResult(
                    success=patch is not None,
                    patch_data=patch.model_dump(mode="json") if patch else None,
                    error=None if patch else "Provider returned no metadata",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except TimeoutError:
                return ProbeMetadataResult(
                    success=False,
                    error="Timeout after 15s",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                return ProbeMetadataResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        # --- Schedule requested operations in parallel ---
        tasks: dict[str, asyncio.Task] = {}
        if ProbeOperation.CURRENT_PRICE in operations:
            tasks["current_price"] = asyncio.ensure_future(_probe_current_price())
        if ProbeOperation.HISTORY in operations:
            tasks["history"] = asyncio.ensure_future(_probe_history())
        if ProbeOperation.METADATA in operations:
            tasks["metadata"] = asyncio.ensure_future(_probe_metadata())

        # Await all tasks in parallel
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)

        total_ms = (time.monotonic_ns() - total_start) // 1_000_000

        return FAProviderProbeResponse(
            provider_code=config.provider_code,
            identifier=config.identifier,
            total_execution_time_ms=total_ms,
            provider_url=provider_url,
            current_price=tasks["current_price"].result() if "current_price" in tasks else None,
            history=tasks["history"].result() if "history" in tasks else None,
            metadata=tasks["metadata"].result() if "metadata" in tasks else None,
        )

    # ========================================================================
    # PRICE QUERY WITH BACKWARD-FILL + Special logic for PROVIDER DELEGATION
    # ========================================================================

    @staticmethod
    def _parse_provider_params(raw_params):
        """Parse provider params from DB (string/dict) into dict safely."""
        if raw_params is None:
            return {}
        if isinstance(raw_params, dict):
            return raw_params
        if isinstance(raw_params, str):
            try:
                return json.loads(raw_params)
            except Exception:
                return {}
        return {}

    @staticmethod
    def _build_backward_filled_series(
        price_map: dict[date_type, PriceHistory],
        start_date: date_type,
        end_date: date_type,
    ) -> list[FAPricePoint]:
        results: list[FAPricePoint] = []
        last_known: Optional[PriceHistory] = None
        current = start_date
        while current <= end_date:
            ph = price_map.get(current)
            if ph:
                last_known = ph
                results.append(
                    FAPricePoint(
                        date=current,
                        open=ph.open,
                        high=ph.high,
                        low=ph.low,
                        close=ph.close,
                        volume=ph.volume,
                        currency=ph.currency,
                        backward_fill_info=None,
                    )
                )
            elif last_known:
                days_back = (current - last_known.date).days
                results.append(
                    FAPricePoint(
                        date=current,
                        open=last_known.open,
                        high=last_known.high,
                        low=last_known.low,
                        close=last_known.close,
                        volume=last_known.volume,
                        currency=last_known.currency,
                        backward_fill_info=AssetBackwardFillInfo(actual_rate_date=last_known.date, days_back=days_back),
                    )
                )
            # else: skip days before first known price
            current += timedelta(days=1)
        return results

    @staticmethod
    async def get_prices_bulk(
        requests: list,
        session: AsyncSession,
    ) -> list:
        """Bulk query prices for multiple assets with a single DB read.

        Fetches all prices in one query and partitions the result by asset_id.
        Each asset then gets its own backward-filled series.

        This method reads ONLY from DB — it does not delegate to providers.
        Provider fetch is a separate operation (POST /assets/prices/sync).
        """
        if not requests:
            return []

        # Build per-asset date ranges
        asset_ranges: dict[int, tuple[date_type, date_type]] = {}
        for req in requests:
            end = req.date_range.end or req.date_range.start
            asset_ranges[req.asset_id] = (req.date_range.start, end)

        asset_ids = list(asset_ranges.keys())

        # Compute global min/max date for single query
        global_start = min(r[0] for r in asset_ranges.values())
        global_end = max(r[1] for r in asset_ranges.values())

        # Single DB query for ALL assets in the date range
        stmt = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.asset_id.in_(asset_ids),
                    PriceHistory.date >= global_start,
                    PriceHistory.date <= global_end,
                )
            )
            .order_by(PriceHistory.asset_id, PriceHistory.date)
        )
        db_result = await session.execute(stmt)
        all_prices = db_result.scalars().all()

        # Partition by asset_id
        price_maps: dict[int, dict[date_type, PriceHistory]] = {aid: {} for aid in asset_ids}
        for p in all_prices:
            if p.asset_id in price_maps:
                price_maps[p.asset_id][p.date] = p

        # Build backward-filled series per asset (preserving request order)
        results = []

        # Check if any request wants events
        event_requests = {req.asset_id for req in requests if getattr(req, "include_events", False)}

        # Query events if needed
        event_maps: dict[int, list[FAAssetEventPointOut]] = {}
        if event_requests:
            evt_stmt = (
                select(AssetEvent)
                .where(
                    and_(
                        AssetEvent.asset_id.in_(list(event_requests)),
                        AssetEvent.date >= global_start,
                        AssetEvent.date <= global_end,
                    )
                )
                .order_by(AssetEvent.asset_id, AssetEvent.date)
            )
            evt_result = await session.execute(evt_stmt)
            for evt in evt_result.scalars().all():
                if evt.asset_id not in event_maps:
                    event_maps[evt.asset_id] = []
                event_maps[evt.asset_id].append(
                    FAAssetEventPointOut(
                        date=evt.date,
                        type=evt.type.value if hasattr(evt.type, "value") else str(evt.type),
                        value=Currency(code=evt.currency, amount=evt.value),
                        notes=evt.notes,
                        id=evt.id,
                        is_auto=evt.provider_assignment_id is not None,
                    )
                )

        for req in requests:
            aid = req.asset_id
            start, end = asset_ranges[aid]
            price_map = price_maps.get(aid, {})
            series = AssetSourceManager._build_backward_filled_series(price_map, start, end)
            events = event_maps.get(aid, []) if aid in event_requests else []
            results.append(FAPriceQueryResult(asset_id=aid, prices=series, events=events))

        # ── Currency conversion pass ──────────────────────────────────────
        # For each result whose request has target_currency, convert OHLC
        # values via FX rates in a single batch call per asset.
        # E.1 closure (2026-04-22) — the `fx_error` discriminator was removed
        # from the response: the frontend surfaces the remediation via the
        # `requiredFxPairs` derived in `routes/(app)/assets/[id]/+page.svelte`,
        # which already distinguishes 4 states (`ok`/`missing`/`no-data`/`partial-gap`)
        # with dedicated banners + CTA. Auto-registration is NOT performed:
        # pair registration is an explicit user action (E.4 cancelled).

        for req, result in zip(requests, results, strict=True):
            target = getattr(req, "target_currency", None)
            if not target or not result.prices:
                continue

            # Collect conversion requests for close (required) prices
            # We'll convert close first, then proportionally scale OHLC
            conversions = []
            price_indices = []  # track which prices need conversion
            for i, p in enumerate(result.prices):
                if p.currency == target:
                    continue  # already in target currency
                conversions.append((Currency(code=p.currency, amount=p.close), target, p.date))
                price_indices.append(i)

            if not conversions:
                continue

            converted, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

            # Apply conversion results
            conv_idx = 0
            for pi in price_indices:
                conv_result = converted[conv_idx]
                original_point = result.prices[pi]

                if conv_result is None:
                    # Conversion failed — keep native price. The FE will hide
                    # the point from converted chart (same policy as events,
                    # E.8.2) and surface the FX pair issue via `requiredFxPairs`.
                    old_bfi = original_point.backward_fill_info
                    failed_bfi = AssetBackwardFillInfo(
                        actual_rate_date=old_bfi.actual_rate_date if old_bfi else original_point.date,
                        days_back=old_bfi.days_back if old_bfi else 0,
                        fx_rate_date=None,
                        fx_days_back=None,
                    )
                    # Keep the same currency/values, only attach the bfi.
                    result.prices[pi] = FAPricePoint(
                        date=original_point.date,
                        open=original_point.open,
                        high=original_point.high,
                        low=original_point.low,
                        close=original_point.close,
                        volume=original_point.volume,
                        currency=original_point.currency,
                        original_currency=original_point.original_currency,
                        original_close=original_point.original_close,
                        original_open=original_point.original_open,
                        original_high=original_point.original_high,
                        original_low=original_point.original_low,
                        backward_fill_info=failed_bfi,
                    )
                    # Surface the per-pair error once per result (dedup)
                    for err in conv_errors:
                        if err not in result.errors:
                            result.errors.append(err)
                    conv_idx += 1
                    continue

                converted_currency, rate_date, _bfill_applied = conv_result
                original_point = result.prices[pi]
                original_close = original_point.close
                original_currency = original_point.currency

                # Compute conversion factor from close conversion
                if original_close and original_close != 0:
                    fx_factor = converted_currency.amount / original_close
                else:
                    conv_idx += 1
                    continue

                # Scale all OHLC values by the same factor
                new_open = original_point.open * fx_factor if original_point.open is not None else None
                new_high = original_point.high * fx_factor if original_point.high is not None else None
                new_low = original_point.low * fx_factor if original_point.low is not None else None
                new_close = converted_currency.amount

                # Compute FX staleness
                fx_days_back_val = (original_point.date - rate_date).days if rate_date < original_point.date else 0

                # Build new backward_fill_info preserving price staleness
                old_bfi = original_point.backward_fill_info
                if old_bfi:
                    new_bfi = AssetBackwardFillInfo(
                        actual_rate_date=old_bfi.actual_rate_date,
                        days_back=old_bfi.days_back,
                        fx_rate_date=rate_date,
                        fx_days_back=fx_days_back_val,
                    )
                elif fx_days_back_val > 0:
                    new_bfi = AssetBackwardFillInfo(
                        actual_rate_date=original_point.date,
                        days_back=0,
                        fx_rate_date=rate_date,
                        fx_days_back=fx_days_back_val,
                    )
                else:
                    new_bfi = None

                # Replace price point with converted version
                result.prices[pi] = FAPricePoint(
                    date=original_point.date,
                    open=new_open,
                    high=new_high,
                    low=new_low,
                    close=new_close,
                    volume=original_point.volume,
                    currency=target,
                    original_currency=original_currency,
                    original_close=original_close,
                    original_open=original_point.open,
                    original_high=original_point.high,
                    original_low=original_point.low,
                    backward_fill_info=new_bfi,
                )
                conv_idx += 1

        # ── Event conversion pass (E.8) ───────────────────────────────────
        # Mirror of the price conversion above, applied to ``result.events``
        # when the request has ``target_currency`` and ``include_events=True``.
        # On success: populate ``original_value``/``fx_rate_date``/``fx_days_back``.
        # On failure: keep the event in its native currency, all ``*_value``/
        # ``fx_*`` stay ``None`` — the FE uses this to hide the marker from
        # the converted chart (see plan closure §E.8.2).
        for req, result in zip(requests, results, strict=True):
            target = getattr(req, "target_currency", None)
            if not target or not result.events:
                continue

            conversions = []
            event_indices = []
            for i, ep in enumerate(result.events):
                if ep.value.code == target:
                    continue  # identity passthrough
                conversions.append((ep.value, target, ep.date))
                event_indices.append(i)

            if not conversions:
                continue

            conv_results, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

            for idx, ei in enumerate(event_indices):
                conv = conv_results[idx]
                original_ep = result.events[ei]
                if conv is None:
                    # FX miss — surface non-fatal warning, leave event untouched.
                    result.errors.append(f"Missing FX rate {original_ep.value.code}->{target} for event on {original_ep.date.isoformat()}")
                    continue
                new_cur, rate_date, _bfill = conv
                days_back = (original_ep.date - rate_date).days if rate_date else 0
                result.events[ei] = FAAssetEventPointOut(
                    date=original_ep.date,
                    type=original_ep.type,
                    value=new_cur,
                    notes=original_ep.notes,
                    id=original_ep.id,
                    is_auto=original_ep.is_auto,
                    original_value=original_ep.value,
                    fx_info=FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=days_back),
                )
            # Include any extra convert_bulk errors (dedup against per-event ones)
            for err in conv_errors:
                if err not in result.errors:
                    result.errors.append(err)

        return results

    # ========================================================================
    # PRICE REFRESH (PROVIDER) METHODS - NEW
    # ========================================================================

    @staticmethod
    async def bulk_refresh_prices(
        requests: List[FARefreshItem],
        session: AsyncSession,
        concurrency: int = 5,
        semaphore_timeout: int = 60,
    ) -> FABulkRefreshResponse:
        """
        Refresh prices for multiple assets using their configured providers.

        Uses a 3-phase pipeline (pattern from FX sync_pairs_bulk):
          Phase 1 — PREPARE: batch DB queries (shared session, read-only)
          Phase 2 — FETCH: parallel provider calls (no DB, semaphore-limited)
          Phase 3 — PERSIST: parallel upsert (per-task session, isolated commits)

        This design avoids concurrent commits on the same session which caused
        "This transaction is closed" errors in the previous monolithic approach.

        Args:
            requests: List of FARefreshItem (asset_id, start_date, end_date)
            session: Database session (used ONLY in Phase 1 for reading)
            concurrency: Max concurrent provider calls
            semaphore_timeout: Timeout for acquiring semaphore (seconds)

        Returns:
            FABulkRefreshResponse with per-item results
        """
        if not requests:
            return FABulkRefreshResponse(results=[], success_count=0, date_range=None, total_points_changed=0)

        t_bulk_start_ns = time.monotonic_ns()
        sem = asyncio.Semaphore(concurrency)

        # ── Phase 1: PREPARE (shared session, batch queries, read-only) ──
        asset_ids = [r.asset_id for r in requests]
        request_map = {r.asset_id: r for r in requests}

        # Batch query: all assignments for requested assets
        assign_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        assign_res = await session.execute(assign_stmt)
        assignment_map: Dict[int, AssetProviderAssignment] = {a.asset_id: a for a in assign_res.scalars().all()}

        # Batch query: all requested assets
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        asset_res = await session.execute(asset_stmt)
        asset_map: Dict[int, Asset] = {a.id: a for a in asset_res.scalars().all()}

        # Build prepared items and generate immediate SKIPPED/FAILED results
        prepared_items: Dict[int, dict] = {}  # asset_id → {assignment, asset, prov, params, ...}
        immediate_results: list[FARefreshResult] = []

        for asset_id in asset_ids:
            item = request_map[asset_id]
            assignment = assignment_map.get(asset_id)
            asset = asset_map.get(asset_id)

            if not asset:
                immediate_results.append(
                    FARefreshResult(
                        asset_id=asset_id,
                        status=SyncStatus.FAILED,
                        errors=[f"Asset {asset_id} not found"],
                        elapsed_ms=(time.monotonic_ns() - t_bulk_start_ns) // 1_000_000,
                    )
                )
                continue

            if not assignment:
                immediate_results.append(
                    FARefreshResult(
                        asset_id=asset_id,
                        status=SyncStatus.SKIPPED,
                        message="No provider assigned",
                        errors=["No provider assigned for asset"],
                        elapsed_ms=(time.monotonic_ns() - t_bulk_start_ns) // 1_000_000,
                    )
                )
                continue

            provider_code = assignment.provider_code
            prov = AssetProviderRegistry.get_provider_instance(provider_code)
            if not prov:
                immediate_results.append(
                    FARefreshResult(
                        asset_id=asset_id,
                        status=SyncStatus.FAILED,
                        provider_used=provider_code,
                        errors=[f"Provider not found: {provider_code}"],
                        elapsed_ms=(time.monotonic_ns() - t_bulk_start_ns) // 1_000_000,
                    )
                )
                continue

            # Parse provider_params
            provider_params = assignment.provider_params or {}
            try:
                if isinstance(provider_params, str):
                    provider_params = json.loads(provider_params)
            except Exception:
                pass

            # Validate params
            try:
                prov.validate_params(provider_params)
            except Exception as e:
                immediate_results.append(
                    FARefreshResult(
                        asset_id=asset_id,
                        status=SyncStatus.FAILED,
                        provider_used=provider_code,
                        errors=[f"Invalid provider params: {str(e)}"],
                        elapsed_ms=(time.monotonic_ns() - t_bulk_start_ns) // 1_000_000,
                    )
                )
                continue

            prepared_items[asset_id] = {
                "assignment": assignment,
                "asset": asset,
                "prov": prov,
                "provider_code": provider_code,
                "provider_params": provider_params,
                "identifier": assignment.identifier,
                "identifier_type": assignment.identifier_type,
                "start": item.date_range.start,
                "end": item.date_range.end,
            }

        # ── Phase 2: FETCH (no DB, parallel with semaphore) ──
        fetch_results: Dict[int, dict] = {}  # asset_id → {"prices": [...], "source": "..."}
        fetch_errors: Dict[int, str] = {}  # asset_id → error message

        async def _fetch_single(asset_id: int, prep: dict):
            """Fetch prices from provider for a single asset (no DB access)."""
            prov = prep["prov"]
            identifier = prep["identifier"]
            # Map ProviderInputType (stored in DB) to IdentifierType (expected by plugin methods)
            identifier_type = AssetSourceProvider.map_input_type_to_identifier_type(prep["identifier_type"])
            provider_params = prep["provider_params"]
            provider_code = prep["provider_code"]
            start = prep["start"]
            end = prep["end"]

            try:
                async with asyncio.timeout(semaphore_timeout):
                    async with sem:
                        prices_data = []
                        events_data = []
                        today = date_type.today()

                        # Cache key for this provider+identifier combo
                        cache_key = (provider_code, identifier, str(prep["identifier_type"]))

                        # 1. Fetch historical data (with core cache)
                        if prov.supports_history and start < today:
                            try:
                                history_end = min(end, today - timedelta(days=1)) if end >= today else end
                                if start <= history_end:
                                    # Check history cache (smart range)
                                    cached_entry, cache_ok = _asset_history_cache.get(cache_key)
                                    fetch_start, fetch_end = start, history_end
                                    cached_dates = {}

                                    if cache_ok and cached_entry:
                                        cached_dates = cached_entry.get("dates", {})
                                        cached_events = cached_entry.get("events", [])
                                        # Determine if we have a gap
                                        if cached_dates:
                                            # Check if requested range is fully covered
                                            needed_dates = set()
                                            d = start
                                            while d <= history_end:
                                                d_iso = d.isoformat()
                                                if d_iso not in cached_dates:
                                                    needed_dates.add(d)
                                                d += timedelta(days=1)
                                            if not needed_dates:
                                                # Full cache hit — use cached data
                                                prices_data = list(cached_dates.values())
                                                events_data = cached_events
                                                logger.debug(f"History cache HIT for asset {asset_id} ({len(prices_data)} points)")
                                                fetch_start = None  # skip fetch
                                            else:
                                                # Partial gap — fetch the missing range
                                                fetch_start = min(needed_dates)
                                                fetch_end = max(needed_dates)

                                    if fetch_start is not None:
                                        hist_data = await _run_provider_in_thread(
                                            lambda: prov.get_history_value(identifier, identifier_type, provider_params, fetch_start, fetch_end),
                                            timeout=55.0,
                                        )
                                        if hist_data and hist_data.prices:
                                            fetched_points = [p.model_dump() for p in hist_data.prices]
                                            # Merge into cached_dates
                                            for p in fetched_points:
                                                d_iso = p["date"].isoformat() if hasattr(p["date"], "isoformat") else str(p["date"])
                                                cached_dates[d_iso] = p
                                            logger.debug(f"Fetched {len(fetched_points)} historical prices for asset {asset_id}")
                                        if hist_data and hist_data.events:
                                            events_data = [e.model_dump() for e in hist_data.events]
                                            logger.debug(f"Fetched {len(events_data)} events for asset {asset_id}")

                                        # Update cache with merged data
                                        _asset_history_cache.set(cache_key, {"dates": cached_dates, "events": events_data})

                                        # Build prices_data from full cached_dates for requested range
                                        prices_data = []
                                        for _d_iso, p in cached_dates.items():
                                            prices_data.append(p)

                            except Exception as hist_e:
                                logger.warning(f"History fetch failed for asset {asset_id}: {hist_e}")

                        # 2. Fetch current value (with core cache)
                        if end >= today:
                            try:
                                cached_current, current_ok = _asset_current_cache.get(cache_key)
                                if current_ok and cached_current:
                                    current_data = cached_current
                                    logger.debug(f"Current cache HIT for asset {asset_id}")
                                else:
                                    current_data = await _run_provider_in_thread(
                                        lambda: prov.get_current_value(identifier, identifier_type, provider_params),
                                        timeout=15.0,
                                    )
                                    if current_data:
                                        _asset_current_cache.set(cache_key, current_data)

                                if current_data and current_data.value:
                                    current_price = {
                                        "date": current_data.as_of_date or today,
                                        "close": current_data.value,
                                        "currency": current_data.currency,
                                    }
                                    prices_data = [p for p in prices_data if p.get("date") != current_price["date"]]
                                    prices_data.append(current_price)
                                    logger.debug(f"Added current price for asset {asset_id}: {current_data.value}")
                            except Exception as curr_e:
                                logger.warning(f"Current value fetch failed for asset {asset_id}: {curr_e}")

                        if not prices_data:
                            fetch_errors[asset_id] = "No price data available from provider"
                            return

                        fetch_results[asset_id] = {"prices": prices_data, "source": provider_code, "events": events_data}

            except Exception as e:
                fetch_errors[asset_id] = str(e)

        fetch_tasks = [_fetch_single(aid, prep) for aid, prep in prepared_items.items()]
        if fetch_tasks:
            await asyncio.gather(*fetch_tasks)

        # ── Phase 3: PERSIST (per-task session, parallel, isolated commits) ──
        engine = get_async_engine()

        async def _count_actual_price_changes(
            session,
            asset_id: int,
            price_items: list,
        ) -> tuple[int, int]:
            """
            Compare fetched prices with existing DB prices.
            Returns (new_count, changed_count) — truly new inserts and actual value changes.
            """
            if not price_items:
                return 0, 0

            dates = [p.date for p in price_items]

            # Load existing prices for these dates
            stmt = select(PriceHistory.date, PriceHistory.close).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates)))
            result = await session.execute(stmt)
            existing: dict = {row[0]: row[1] for row in result.all()}

            new_count = 0
            changed_count = 0
            for p in price_items:
                old_close = existing.get(p.date)
                if old_close is None:
                    new_count += 1
                else:
                    # Truncate fetched value to DB precision before comparing
                    truncated_new = truncate_priceHistory(Decimal(str(p.close)), "close")
                    if float(old_close) != float(truncated_new):
                        changed_count += 1

            return new_count, changed_count

        async def _persist_single(asset_id: int) -> FARefreshResult:
            """Upsert fetched prices and update assignment in an isolated session."""
            t_start_ns = time.monotonic_ns()
            prep = prepared_items[asset_id]
            provider_code = prep["provider_code"]
            prov = prep["prov"]
            start = prep["start"]

            # Check if fetch failed
            if asset_id in fetch_errors:
                elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
                return FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    provider_used=provider_code,
                    errors=[fetch_errors[asset_id]],
                    elapsed_ms=elapsed_ms,
                )

            remote_data = fetch_results.get(asset_id)
            if not remote_data:
                elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
                return FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    provider_used=provider_code,
                    errors=["No data available from provider"],
                    elapsed_ms=elapsed_ms,
                )

            prices = remote_data.get("prices", [])
            if not prices:
                elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
                return FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    provider_used=provider_code,
                    errors=["No prices returned from provider"],
                    elapsed_ms=elapsed_ms,
                )

            # Convert to FAPricePoint objects — fallback to asset's own currency
            asset_currency = prep["asset"].currency
            price_items = [
                FAPricePoint(
                    date=p["date"],
                    open=p.get("open"),
                    high=p.get("high"),
                    low=p.get("low"),
                    close=p["close"],
                    volume=p.get("volume"),
                    currency=p.get("currency") or asset_currency,
                )
                for p in prices
            ]
            upsert_obj = FAUpsert(asset_id=asset_id, prices=price_items)

            errors = []
            fetched_count = len(prices)
            inserted_count = 0
            updated_count = 0
            events_fetched_count = len(remote_data.get("events", []))
            events_changed_count = 0

            # Isolated session for this asset's DB writes
            try:
                async with AsyncSession(engine, expire_on_commit=False) as persist_session:
                    # Count actual changes BEFORE upserting (compare with DB)
                    try:
                        new_count, changed_count = await _count_actual_price_changes(persist_session, asset_id, price_items)
                    except Exception:
                        new_count, changed_count = fetched_count, 0  # Fallback

                    try:
                        await AssetSourceManager.bulk_upsert_prices([upsert_obj], persist_session)
                        inserted_count = new_count
                        updated_count = changed_count
                    except Exception as e:
                        errors.append(f"DB upsert failed: {str(e)}")

                    # Upsert asset events (if any)
                    events_list = remote_data.get("events", [])
                    if events_list:
                        try:
                            assignment_id = prep["assignment"].id
                            events_changed_count = (
                                await AssetSourceManager._upsert_asset_events(
                                    persist_session,
                                    asset_id,
                                    events_list,
                                    assignment_id,
                                    prep["asset"].currency,
                                )
                                or 0
                            )
                        except Exception as e:
                            errors.append(f"Event upsert failed: {str(e)}")

                    # Update last_fetch_at on assignment
                    try:
                        assign_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)
                        assign_res = await persist_session.execute(assign_stmt)
                        fresh_assignment = assign_res.scalar_one_or_none()
                        if fresh_assignment:
                            fresh_assignment.last_fetch_at = utcnow()
                            persist_session.add(fresh_assignment)
                            await persist_session.commit()
                    except Exception:
                        pass  # Not critical
            except Exception as e:
                errors.append(f"Persist session error: {str(e)}")

            points_changed = inserted_count + updated_count
            elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000

            # Determine status
            message = None
            if errors:
                status = SyncStatus.FAILED if fetched_count == 0 else SyncStatus.PARTIAL
            elif fetched_count > 0:
                has_history = prov.supports_history and start < date_type.today()
                if has_history and fetched_count == 1:
                    status = SyncStatus.PARTIAL
                    message = "Current value only, history unavailable"
                else:
                    status = SyncStatus.OK
            else:
                status = SyncStatus.FAILED
                message = "No data available from provider"

            return FARefreshResult(
                asset_id=asset_id,
                status=status,
                provider_used=provider_code,
                points_fetched=fetched_count,
                points_changed=points_changed,
                inserted_count=inserted_count,
                updated_count=updated_count,
                events_fetched=events_fetched_count,
                events_changed=events_changed_count,
                message=message,
                errors=errors,
                elapsed_ms=elapsed_ms,
            )

        # Build persist tasks only for assets that had fetch results or errors
        persist_asset_ids = [aid for aid in prepared_items if aid in fetch_results or aid in fetch_errors]
        persist_tasks = [_persist_single(aid) for aid in persist_asset_ids]

        persist_results: list[FARefreshResult] = []
        if persist_tasks:
            persist_results = list(await asyncio.gather(*persist_tasks))

        # ── Combine all results ──
        results = immediate_results + persist_results
        total_points_changed = sum(r.points_changed for r in results)
        date_range_model = requests[0].date_range if requests else None

        return FABulkRefreshResponse(
            results=results,
            success_count=sum(1 for r in results if r.status in (SyncStatus.OK, SyncStatus.PARTIAL)),
            errors=[],
            date_range=date_range_model,
            total_points_changed=total_points_changed,
        )

    # ========================================================================
    # BULK CURRENT PRICE (READ-ONLY, NO DB WRITES)
    # ========================================================================

    @staticmethod
    async def get_current_prices_bulk(
        asset_ids: list[int],
        session: AsyncSession,
        concurrency: int = 5,
    ) -> list:
        """
        Fetch current/live prices for multiple assets.

        For each asset:
        1. If a provider is assigned → call provider.get_current_value() (parallel, semaphore-limited)
        2. Fallback → read latest PriceHistory row from DB

        **Side effect (F.2 + F.3)**: for every successful provider fetch whose
        ``as_of_date`` is today, the OHLC row for today is either created
        (``open=high=low=close=value``, ``volume=None``) or its intra-day
        range is extended (``low``/``high`` widened, ``open`` set if missing,
        ``close`` overwritten with the latest tick). DB-fallback results are
        not persisted (they are stale data, not fresh quotes). A commit
        failure on the OHLC persist is logged + rolled back without failing
        the fetch (the FACurrentPriceItem list is still returned).

        Args:
            asset_ids: Asset IDs to fetch prices for
            session: Database session (used for both read and the F.2/F.3 write-back)
            concurrency: Max parallel provider calls

        Returns:
            List of FACurrentPriceItem (one per requested asset_id, preserving order)
        """
        from backend.app.schemas.prices import FACurrentPriceItem  # noqa: PLC0415 — avoid circular import

        if not asset_ids:
            return []

        sem = asyncio.Semaphore(concurrency)

        # Batch query: assets + assignments
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        asset_res = await session.execute(asset_stmt)
        asset_map = {a.id: a for a in asset_res.scalars().all()}

        assign_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        assign_res = await session.execute(assign_stmt)
        assign_map = {a.asset_id: a for a in assign_res.scalars().all()}

        async def _fetch_one(asset_id: int) -> FACurrentPriceItem:
            """Fetch current price for one asset via provider or DB fallback."""
            asset = asset_map.get(asset_id)
            if not asset:
                return FACurrentPriceItem(asset_id=asset_id, error="Asset not found")

            assignment = assign_map.get(asset_id)

            # --- Try provider ---
            if assignment:
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
                if provider:
                    params = AssetSourceManager._parse_provider_params(assignment.provider_params)
                    mapped_id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)

                    # Check core cache first (TTL 2min)
                    cache_key = (assignment.provider_code, assignment.identifier, str(assignment.identifier_type))
                    cached_cv, cache_ok = _asset_current_cache.get(cache_key)
                    if cache_ok:
                        logger.debug(f"Current-price cache HIT for asset {asset_id}")
                        return FACurrentPriceItem(
                            asset_id=asset_id,
                            value=cached_cv.value,
                            currency=cached_cv.currency,
                            as_of_date=cached_cv.as_of_date,
                            source=f"provider:{assignment.provider_code}",
                        )

                    try:
                        # Capture variables for lambda (avoid late-binding)
                        _id = assignment.identifier
                        _id_type = mapped_id_type
                        _params = params
                        async with sem:
                            cv = await _run_provider_in_thread(
                                lambda: provider.get_current_value(_id, _id_type, _params),
                                timeout=10.0,
                            )
                        _asset_current_cache.set(cache_key, cv)
                        return FACurrentPriceItem(
                            asset_id=asset_id,
                            value=cv.value,
                            currency=cv.currency,
                            as_of_date=cv.as_of_date,
                            source=f"provider:{assignment.provider_code}",
                        )
                    except Exception as prov_err:
                        logger.debug(
                            "Provider current-price failed, falling back to DB",
                            asset_id=asset_id,
                            error=str(prov_err),
                        )

            # --- Fallback: last known price from DB ---
            last_stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc()).limit(1)
            last_res = await session.execute(last_stmt)
            last_price = last_res.scalar_one_or_none()

            if last_price:
                return FACurrentPriceItem(
                    asset_id=asset_id,
                    value=Decimal(str(last_price.close)),
                    currency=last_price.currency,
                    as_of_date=last_price.date,
                    source="db:last_known",
                )

            return FACurrentPriceItem(
                asset_id=asset_id,
                error="No price data available",
            )

        # Run all fetches in parallel
        tasks = [_fetch_one(aid) for aid in asset_ids]
        results = await asyncio.gather(*tasks)

        # F.2 + F.3 — persist current-price snapshots to PriceHistory.
        # ----------------------------------------------------------------
        # This call is NOT read-only anymore (docstring updated): for every
        # successful **provider** fetch whose ``as_of_date`` equals today we
        # either bootstrap a new row (F.2) or extend the existing intra-day
        # range (F.3). Results sourced from the DB fallback
        # (``source == "db:last_known"``) are **skipped**: they are not fresh
        # quotes, they are stale rows we just read — writing them back as
        # "today" would fabricate data.
        #
        # Concurrency note: multiple callers hitting this in parallel produce
        # last-write-wins semantics. Acceptable because fresh data flows from
        # the same provider (plus its cache), the value is the same, and the
        # realistic concurrency upper bound is (connected users + 1 scheduler).
        today = date_type.today()
        items_to_persist = [r for r in results if r.value is not None and r.currency and r.as_of_date == today and r.source and r.source.startswith("provider:")]

        if items_to_persist:
            existing_stmt = select(PriceHistory).where(and_(PriceHistory.asset_id.in_([r.asset_id for r in items_to_persist]), PriceHistory.date == today))
            existing_res = await session.execute(existing_stmt)
            existing_by_asset = {row.asset_id: row for row in existing_res.scalars().all()}

            logger.info(
                "Current-price persist: processing %d fresh provider quote(s) for %s (existing rows today: %d)",
                len(items_to_persist),
                today,
                len(existing_by_asset),
            )

            for item in items_to_persist:
                new_close = Decimal(str(item.value))
                existing = existing_by_asset.get(item.asset_id)
                if existing is None:
                    # F.2 bootstrap — open=high=low=close=new, volume=None
                    session.add(
                        PriceHistory(
                            asset_id=item.asset_id,
                            date=today,
                            open=new_close,
                            high=new_close,
                            low=new_close,
                            close=new_close,
                            volume=None,
                            currency=item.currency,
                            source_plugin_key=item.source or "provider:unknown",
                            fetched_at=utcnow(),
                        )
                    )
                    logger.info(
                        "  [F.2 bootstrap] asset=%s date=%s close=%s currency=%s source=%s",
                        item.asset_id,
                        today,
                        new_close,
                        item.currency,
                        item.source,
                    )
                else:
                    # F.3 intra-day extend
                    patch = AssetSourceManager._extend_ohlc_bounds(existing, new_close)
                    # Always overwrite close with the latest quote (per user spec)
                    patch["close"] = new_close
                    for field_name, new_val in patch.items():
                        setattr(existing, field_name, new_val)
                    existing.fetched_at = utcnow()
                    logger.info(
                        "  [Intra-day price extend] asset=%s date=%s new_close=%s patch_fields=%s",
                        item.asset_id,
                        today,
                        new_close,
                        list(patch.keys()),
                    )

            try:
                await session.commit()
                logger.info("Current-price persist: commit OK (%d row(s) written/updated)", len(items_to_persist))
            except Exception as commit_err:
                logger.warning("Current-price OHLC persist failed, rolling back: %s", commit_err)
                await session.rollback()
        else:
            # Only log when something was expected but filtered out (db:last_known or today mismatch)
            skipped_count = sum(1 for r in results if r.source == "db:last_known")
            if skipped_count > 0:
                logger.info(
                    "Current-price persist: skipped %d item(s) with source=db:last_known (stale fallback, not persisted)",
                    skipped_count,
                )

        return list(results)

    # F.3 helper — shared between current-price persist and future pipelines.
    @staticmethod
    def _extend_ohlc_bounds(existing: PriceHistory, new_close: Decimal) -> dict:
        """Compute the patch to apply to ``existing`` so the intra-day OHLC
        bounds cover ``new_close`` (F.3).

        Rules (per plan):
        - ``low``  = min(existing.low,  new_close) when existing.low is set, else new_close
        - ``high`` = max(existing.high, new_close) when existing.high is set, else new_close
        - ``open`` = new_close only when existing.open is None (first tick of the day)
        - ``volume`` untouched

        Close is intentionally NOT touched here: the caller decides whether to
        overwrite close with the latest tick (the current-price path does,
        see ``get_current_prices_bulk``).

        Returns a dict of only the fields that need to change, so the caller
        can SETATTR them directly on the ORM row (no over-write on stable
        fields, easier to log/inspect).
        """
        patch: dict = {}
        if existing.low is None or new_close < existing.low:
            patch["low"] = new_close
        if existing.high is None or new_close > existing.high:
            patch["high"] = new_close
        if existing.open is None:
            patch["open"] = new_close
        return patch

    # ========================================================================
    # EVENT CRUD — Manual event management
    # ========================================================================

    @staticmethod
    async def bulk_upsert_events(data: list, session: AsyncSession) -> dict:
        """
        Bulk upsert manual events (provider_assignment_id = NULL).

        Uses the existing _upsert_asset_events() method with provider_assignment_id=None.

        Args:
            data: List of FAEventUpsert objects (asset_id + events[])
            session: Database session

        Returns:
            dict with results list and success_count
        """
        results = []
        total_count = 0

        for item in data:
            asset_id = item.asset_id

            # Verify asset exists
            asset_stmt = select(Asset).where(Asset.id == asset_id)
            asset_res = await session.execute(asset_stmt)
            asset = asset_res.scalar_one_or_none()
            if not asset:
                results.append(
                    {
                        "asset_id": asset_id,
                        "count": 0,
                        "message": f"Asset {asset_id} not found",
                    }
                )
                continue

            # Determine default currency from asset or 'USD'
            default_currency = asset.currency or "USD"

            count = await AssetSourceManager._upsert_asset_events(
                session=session,
                asset_id=asset_id,
                events=item.events,
                provider_assignment_id=None,  # manual events
                default_currency=default_currency,
            )

            total_count += count
            results.append(
                {
                    "asset_id": asset_id,
                    "count": count,
                    "message": f"Upserted {count} manual events",
                }
            )

        return {"results": results, "success_count": sum(1 for r in results if r["count"] > 0)}

    @staticmethod
    async def query_events_bulk(requests: list, session: AsyncSession) -> list:
        """
        Bulk query events for multiple assets, returning FAAssetEventPointOut with id + is_auto.

        Args:
            requests: List of FAEventQueryItem (asset_id + date_range + optional target_currency)
            session: Database session

        Returns:
            List of FAEventQueryResult

        E.8 — when ``target_currency`` is set on a request, ``event.value`` is
        converted to that currency via FX rates at the event's date. FX misses
        are surfaced as non-fatal warnings in ``FAEventQueryResult.errors``
        (the event is still returned, in its native currency).
        """
        from backend.app.schemas.prices import FAAssetEventPointOut, FAEventQueryResult  # noqa: PLC0415 — avoid circular import
        from backend.app.services.fx import convert_bulk  # noqa: PLC0415 — avoid circular import at module load

        results = []

        for req in requests:
            asset_id = req.asset_id
            start = req.date_range.start
            end = req.date_range.end or start
            target_currency = getattr(req, "target_currency", None)

            stmt = (
                select(AssetEvent)
                .where(
                    and_(
                        AssetEvent.asset_id == asset_id,
                        AssetEvent.date >= start,
                        AssetEvent.date <= end,
                    )
                )
                .order_by(AssetEvent.date)
            )
            res = await session.execute(stmt)
            db_events = res.scalars().all()

            # Build native-currency event points first
            event_points: list = []
            for ev in db_events:
                event_points.append(
                    FAAssetEventPointOut(
                        date=ev.date,
                        type=ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                        value=Currency(code=ev.currency, amount=ev.value),
                        notes=ev.notes,
                        id=ev.id,
                        is_auto=ev.provider_assignment_id is not None,
                    )
                )

            errors: list[str] = []

            # E.8 — optional target_currency conversion pass
            if target_currency and event_points:
                conversions = [(ep.value, target_currency, ep.date) for ep in event_points]
                conv_results, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

                for idx, (ep, conv) in enumerate(zip(event_points, conv_results, strict=True)):
                    if conv is None:
                        # FX miss — keep native currency value, surface as non-fatal warning.
                        # original_* stays None → frontend will hide the event marker (E.8.2).
                        errors.append(f"Missing FX rate {ep.value.code}->{target_currency} for event on {ep.date.isoformat()}")
                        continue
                    new_cur, rate_date, _bfill = conv
                    # Identity conversion (from == to) → no-op, don't populate original_*/fx_*
                    # so the FE can distinguish "converted" from "passthrough".
                    if ep.value.code == target_currency:
                        continue
                    # Compute days_back magnitude (0 for same-day, >0 for backward-fill).
                    days_back = (ep.date - rate_date).days if rate_date else 0
                    event_points[idx] = FAAssetEventPointOut(
                        date=ep.date,
                        type=ep.type,
                        value=new_cur,
                        notes=ep.notes,
                        id=ep.id,
                        is_auto=ep.is_auto,
                        original_value=ep.value,
                        fx_info=FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=days_back),
                    )

                # Also include per-pair errors surfaced by convert_bulk (e.g. pair not registered)
                # (deduplicated against our per-event messages — convert_bulk errors are already
                # one per failed conversion, same index, so we skip duplicates by content).
                for err in conv_errors:
                    if err not in errors:
                        errors.append(err)

            results.append(
                FAEventQueryResult(
                    asset_id=asset_id,
                    events=event_points,
                    errors=errors,
                )
            )

        return results

    @staticmethod
    async def delete_events_bulk(
        event_ids: list[int],
        session: AsyncSession,
        current_user: User,
    ) -> FAEventBulkDeleteResponse:
        """
        Bulk delete asset events with RESTRICT-aware per-item result.

        For each requested id, returns one of:
        - ``deleted`` — event removed
        - ``not_found`` — id did not exist
        - ``in_use`` — referenced by one or more transactions; response exposes
          ``accessible_transactions`` (tx ids current user can see) and
          ``hidden_transactions_count`` (refs owned by other users).

        No partial rollback: deletable events are committed even if others are
        blocked. HTTP layer always returns 200 — inspect ``results`` for outcome.
        """
        results: list[FAEventDeleteItemResult] = []

        for event_id in event_ids:
            event = await session.get(AssetEvent, event_id)
            if event is None:
                results.append(FAEventDeleteItemResult(event_id=event_id, status="not_found"))
                continue

            # RESTRICT pre-check: enumerate transactions that reference this event.
            total_stmt = select(func.count(Transaction.id)).where(Transaction.asset_event_id == event_id)
            total_count_row = await session.execute(total_stmt)
            total_count = int(total_count_row.scalar_one() or 0)

            if total_count > 0:
                # Split by user accessibility via BrokerUserAccess join.
                accessible_stmt = (
                    select(Transaction.id)
                    .join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id)
                    .where(
                        Transaction.asset_event_id == event_id,
                        BrokerUserAccess.user_id == current_user.id,
                    )
                )
                acc_rows = await session.execute(accessible_stmt)
                accessible_ids = [int(r[0]) for r in acc_rows.all()]
                hidden = total_count - len(accessible_ids)

                results.append(
                    FAEventDeleteItemResult(
                        event_id=event_id,
                        status="in_use",
                        accessible_transactions=accessible_ids,
                        hidden_transactions_count=hidden,
                    )
                )
                continue

            # Safe to delete
            await session.delete(event)
            results.append(FAEventDeleteItemResult(event_id=event_id, status="deleted"))

        await session.commit()

        return FAEventBulkDeleteResponse(
            results=results,
            deleted_count=sum(1 for r in results if r.status == "deleted"),
            not_found_count=sum(1 for r in results if r.status == "not_found"),
            in_use_count=sum(1 for r in results if r.status == "in_use"),
        )


# ============================================================================
# ASSET CRUD SERVICE
# ============================================================================


class AssetCRUDService:
    """Service for asset CRUD operations."""

    @staticmethod
    async def create_assets_bulk(assets: List[FAAssetCreateItem], session: AsyncSession) -> FABulkAssetCreateResponse:
        """
        Create multiple assets in bulk (partial success allowed).

        Args:
            assets: List of assets to create
            session: Database session

        Returns:
            FABulkAssetCreateResponse with per-item results
        """
        results: list[FAAssetCreateResult] = []

        for item in assets:
            try:
                # Check if display_name already exists (UNIQUE constraint)
                stmt = select(Asset).where(Asset.display_name == item.display_name)
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    results.append(
                        FAAssetCreateResult(
                            asset_id=None,
                            success=False,
                            message=f"Asset with display_name '{item.display_name}' already exists",
                            display_name=item.display_name,
                        )
                    )
                    continue

                # Create asset record
                asset = Asset(
                    display_name=item.display_name,
                    currency=item.currency,
                    asset_type=item.asset_type or AssetType.OTHER,
                    icon_url=item.icon_url,
                    active=True,
                    # Identifier fields
                    identifier_isin=item.identifier_isin,
                    identifier_ticker=item.identifier_ticker,
                    identifier_cusip=item.identifier_cusip,
                    identifier_sedol=item.identifier_sedol,
                    identifier_figi=item.identifier_figi,
                    identifier_uuid=item.identifier_uuid,
                    identifier_other=item.identifier_other,
                )

                # Handle classification_params
                if item.classification_params:
                    asset.classification_params = item.classification_params.model_dump_json(exclude_none=True)

                session.add(asset)
                await session.flush()  # Get ID without committing

                results.append(
                    FAAssetCreateResult(
                        asset_id=asset.id,
                        success=True,
                        message="Asset created successfully",
                        display_name=item.display_name,
                    )
                )

                logger.info(f"Asset created: id={asset.id}, display_name={item.display_name}")

            except Exception as e:
                logger.error(f"Error creating asset {item.display_name}: {e}")
                results.append(
                    FAAssetCreateResult(
                        asset_id=None,
                        success=False,
                        message=f"Error: {str(e)}",
                        display_name=item.display_name,
                    )
                )

        # Commit all successful creates
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Error committing asset creation: {e}")
            await session.rollback()
            # Mark all as failed
            for result in results:
                if result.success:
                    result.success = False
                    result.message = f"Transaction failed: {str(e)}"
                    result.asset_id = None

        success_count = sum(1 for r in results if r.success)
        return FABulkAssetCreateResponse(results=results, success_count=success_count, errors=[])

    @staticmethod
    async def list_assets(filters: FAAinfoFiltersRequest, session: AsyncSession) -> List[FAinfoResponse]:
        """
        List assets with optional filters - enhanced for BRIM asset matching.

        Supports filtering by:
        - currency, asset_type, active (existing)
        - search: partial match in display_name
        - Exact match on identifier columns: isin, ticker, cusip, sedol, figi, uuid
        - identifier_other: partial match (LIKE)
        - identifier_contains: partial match across ALL identifier columns

        Args:
            filters: Query filters (see FAAinfoFiltersRequest)
            session: Database session

        Returns:
            List of assets matching filters, with identifier info
        """
        # Build base query with LEFT JOIN to get provider assignment data
        stmt = select(
            Asset,
            AssetProviderAssignment.id.label("provider_id"),
            AssetProviderAssignment.provider_code.label("provider_code_col"),
            AssetProviderAssignment.identifier.label("provider_identifier"),
            AssetProviderAssignment.identifier_type.label("provider_identifier_type"),
        ).outerjoin(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id)

        # Apply filters
        conditions = []

        if filters.currency:
            conditions.append(Asset.currency == filters.currency)

        if filters.asset_type:
            conditions.append(Asset.asset_type == filters.asset_type)

        # Tri-state active filter: None = no filter, True/False = exact match
        if filters.active is not None:
            conditions.append(Asset.active == filters.active)

        if filters.search:
            search_pattern = f"%{filters.search}%"
            conditions.append(Asset.display_name.ilike(search_pattern))

        # Exact match on identifier columns (one per IdentifierType)
        if filters.isin:
            conditions.append(Asset.identifier_isin == filters.isin.upper())

        if filters.ticker:
            conditions.append(Asset.identifier_ticker == filters.ticker.upper())

        if filters.cusip:
            conditions.append(Asset.identifier_cusip == filters.cusip.upper())

        if filters.sedol:
            conditions.append(Asset.identifier_sedol == filters.sedol.upper())

        if filters.figi:
            conditions.append(Asset.identifier_figi == filters.figi.upper())

        if filters.uuid:
            conditions.append(Asset.identifier_uuid == filters.uuid)

        # identifier_other uses partial match (LIKE) since it can contain anything
        if filters.identifier_other:
            conditions.append(Asset.identifier_other.ilike(f"%{filters.identifier_other}%"))

        # Partial identifier match (across all identifier columns)
        if filters.identifier_contains:
            pattern = f"%{filters.identifier_contains}%"
            conditions.append(
                or_(
                    Asset.identifier_isin.ilike(pattern),
                    Asset.identifier_ticker.ilike(pattern),
                    Asset.identifier_cusip.ilike(pattern),
                    Asset.identifier_sedol.ilike(pattern),
                    Asset.identifier_figi.ilike(pattern),
                    Asset.identifier_uuid.ilike(pattern),
                    Asset.identifier_other.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Order by display_name
        stmt = stmt.order_by(Asset.display_name.asc())

        # Execute query
        result = await session.execute(stmt)
        rows = result.all()

        # Build response with identifier info
        assets = []
        for row in rows:
            asset = row[0]  # Asset object
            _provider_id = row[1]  # provider_id from join (unused, kept for positional access)
            provider_code = row[2]  # provider_code from join
            provider_identifier = row[3]  # identifier from provider assignment
            provider_identifier_type = row[4]  # identifier_type from provider assignment

            assets.append(
                FAinfoResponse(
                    id=asset.id,
                    display_name=asset.display_name,
                    currency=asset.currency,
                    icon_url=asset.icon_url,
                    asset_type=asset.asset_type,
                    active=asset.active,
                    user_url=asset.user_url,
                    provider_code=provider_code,
                    has_metadata=asset.classification_params is not None,
                    # Identifier columns from Asset
                    identifier_isin=asset.identifier_isin,
                    identifier_ticker=asset.identifier_ticker,
                    identifier_cusip=asset.identifier_cusip,
                    identifier_sedol=asset.identifier_sedol,
                    identifier_figi=asset.identifier_figi,
                    identifier_uuid=asset.identifier_uuid,
                    identifier_other=asset.identifier_other,
                    # Legacy fields from provider assignment
                    identifier=provider_identifier,
                    identifier_type=(AssetSourceProvider.map_input_type_to_identifier_type(provider_identifier_type) if provider_identifier_type else None),
                )
            )

        return assets

    @staticmethod
    async def delete_assets_bulk(asset_ids: List[int], session: AsyncSession) -> FABulkAssetDeleteResponse:
        """
        Delete multiple assets (partial success allowed).

        Blocks deletion if asset has transactions (FK constraint).
        CASCADE deletes provider_assignments and price_history.

        Args:
            asset_ids: List of asset IDs to delete
            session: Database session

        Returns:
            FABulkAssetDeleteResponse with per-item results
        """
        results = []

        for asset_id in asset_ids:
            asset_name = None
            try:
                # Check if asset exists
                stmt = select(Asset).where(Asset.id == asset_id)
                result = await session.execute(stmt)
                asset = result.scalar_one_or_none()

                if not asset:
                    results.append(
                        FAAssetDeleteResult(
                            asset_id=asset_id,
                            success=False,
                            display_name=None,
                            error_code="NOT_FOUND",
                            message=f"Asset with ID {asset_id} not found",
                        )
                    )
                    continue

                asset_name = asset.display_name

                # Try to delete (will fail if transactions exist due to FK constraint)
                await session.delete(asset)
                await session.flush()  # Check FK constraints before commit

                results.append(
                    FAAssetDeleteResult(
                        asset_id=asset_id,
                        success=True,
                        deleted_count=1,
                        display_name=asset_name,
                        message="Asset deleted successfully",
                    )
                )

                logger.info(f"Asset deleted: id={asset_id}")

            except Exception as e:
                await session.rollback()
                error_msg = str(e)

                # Check if error is due to FK constraint (transactions exist)
                if "FOREIGN KEY constraint failed" in error_msg or "foreign key" in error_msg.lower():
                    message = f"Cannot delete asset {asset_id}: has existing transactions"
                    error_code = "HAS_TRANSACTIONS"
                else:
                    message = f"Error deleting asset {asset_id}: {error_msg}"
                    error_code = None

                results.append(
                    FAAssetDeleteResult(
                        asset_id=asset_id,
                        success=False,
                        deleted_count=0,
                        display_name=asset_name,
                        error_code=error_code,
                        message=message,
                    )
                )
                logger.error(f"Error deleting asset {asset_id}: {e}")

        # Commit successful deletions
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Error committing asset deletion: {e}")
            await session.rollback()

        success_count = sum(1 for r in results if r.success)
        return FABulkAssetDeleteResponse(
            results=results,
            success_count=success_count,
            errors=[],  # Operation-level errors (none for now)
        )

    @staticmethod
    async def patch_assets_bulk(patches: List[FAAssetPatchItem], session: AsyncSession) -> FABulkAssetPatchResponse:
        """
        Patch multiple assets in bulk (partial success allowed).

        Merge logic:
        - Field absent in patch or None: IGNORE (keep existing value)
        - Field present in patch: UPDATE or BLANK (to delete a string set to empty)

        For classification_params:
        - If None: Set DB column to NULL
        - If present: model_dump_json(exclude_none=True) to omit blank subfields

        Args:
            patches: List of asset patches
            session: Database session

        Returns:
            FABulkAssetPatchResponse with per-item results
        """

        results: list[FAAssetPatchResult] = []

        for patch in patches:
            try:
                # Fetch asset
                stmt = select(Asset).where(Asset.id == patch.asset_id)
                result = await session.execute(stmt)
                asset: Asset = result.scalar_one_or_none()

                if not asset:
                    results.append(
                        FAAssetPatchResult(
                            asset_id=patch.asset_id,
                            success=False,
                            message=f"Asset {patch.asset_id} not found",
                            updated_fields=None,
                        )
                    )
                    continue
                asset_classification_params_before = json.loads(asset.classification_params) if asset.classification_params else {}
                logger.debug(f"Asset found for patching: id={patch.asset_id}: {asset.model_dump_json()}")

                # Track updated fields
                updated_fields: List[OldNew[str]] = []

                # Update fields if present in patch (use model_dump to detect presence)
                # Use exclude_unset=True to only include fields that were explicitly set
                # Use exclude_none=True to exclude None values (except classification_params which we handle specially)
                patch_dict = patch.model_dump(mode="json", exclude={"asset_id"}, exclude_unset=True, exclude_none=True)

                # Special handling for classification_params=None (clearing the field)
                # Check if it was explicitly set to None in the original patch object
                if "classification_params" not in patch_dict and patch.classification_params is None:
                    # Check if the field was explicitly set (not just default None)
                    # We can use __pydantic_fields_set__ to check
                    if "classification_params" in patch.model_fields_set:
                        patch_dict["classification_params"] = None

                # I.3 — guard against currency change on assets with existing price history.
                # Rationale: changing asset.currency while `price_history` rows exist creates
                # a silent inconsistency (stored prices are in the old currency, future queries
                # would scale them against the new currency via FX conversion producing wrong
                # numbers). The agreed policy (see phase-07 plan, Blocco I) is "wipe on change":
                # the frontend must explicitly DELETE prices first, then re-PATCH, then re-sync.
                # Here we emit a structured failure so the frontend can parse it and open the
                # destructive-confirmation modal.
                if "currency" in patch_dict:
                    new_currency = patch_dict["currency"]
                    if new_currency and new_currency != asset.currency:
                        count_stmt = select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == patch.asset_id)
                        oldest_stmt = select(func.min(PriceHistory.date)).where(PriceHistory.asset_id == patch.asset_id)
                        newest_stmt = select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == patch.asset_id)
                        count_res = await session.execute(count_stmt)
                        existing_count = int(count_res.scalar() or 0)
                        if existing_count > 0:
                            oldest_res = await session.execute(oldest_stmt)
                            newest_res = await session.execute(newest_stmt)
                            oldest_date = oldest_res.scalar()
                            newest_date = newest_res.scalar()
                            # Structured token message: the frontend parses this to trigger
                            # the currency-change modal. Format intentionally stable so the
                            # parser is straightforward.
                            blocker_msg = f"CURRENCY_CHANGE_BLOCKED_BY_PRICES|count={existing_count}|oldest={oldest_date.isoformat() if oldest_date else ''}|newest={newest_date.isoformat() if newest_date else ''}|from={asset.currency}|to={new_currency}"
                            results.append(
                                FAAssetPatchResult(
                                    asset_id=patch.asset_id,
                                    success=False,
                                    message=blocker_msg,
                                    updated_fields=None,
                                )
                            )
                            continue

                for field, value in patch_dict.items():
                    logger.debug(f"Patching field '{field}': '{value}'")
                    if field == "classification_params":
                        # None = clear all classification_params
                        if value is None:
                            value = None  # Will set classification_params to NULL in DB
                        elif not value:  # Empty dict = also clear
                            value = None
                        else:
                            # PATCH semantics for classification_params:
                            # - If a field (e.g., sector_area, geographic_area) is present in patch, replace it completely
                            # - If a field is absent from patch, keep the existing value
                            # NO deep merge: each field is atomic (sector_area.distribution is replaced as a whole)

                            # Start with existing values
                            merged = dict(asset_classification_params_before)

                            # Replace only the fields present in the patch (shallow merge, not deep)
                            for key, val in value.items():
                                if val is not None and val != "":
                                    merged[key] = val
                                else:
                                    # Explicit null/empty = remove field
                                    merged.pop(key, None)

                            # Validate and serialize
                            value = FAClassificationParams(**merged).model_dump(mode="json", exclude_none=True)
                            if not value:  # If result is empty dict, set to None
                                value = None

                    # Convert empty strings/dicts to None, but preserve boolean False
                    if not isinstance(value, bool) and not value:
                        value = None

                    if isinstance(value, dict):
                        value = json.dumps(value)  # Transform dict as serialized JSON
                    oldVal = getattr(asset, field)
                    setattr(asset, field, value)
                    updated_fields.append(OldNew(info=field, old=oldVal, new=value))
                    logger.debug(f"updated field '{field}': '{oldVal}' -> '{value}'")

                await session.flush()

                results.append(
                    FAAssetPatchResult(
                        asset_id=patch.asset_id,
                        success=True,
                        message=f"Asset patched successfully ({len(updated_fields)} fields)",
                        updated_fields=updated_fields,
                    )
                )

                logger.info(f"Asset patched: id={patch.asset_id}, fields={updated_fields}")

            except Exception as e:
                logger.error(f"Error patching asset {patch.asset_id}: {e}")
                results.append(
                    FAAssetPatchResult(
                        asset_id=patch.asset_id,
                        success=False,
                        message=f"Error: {str(e)}",
                        updated_fields=None,
                    )
                )

        # Commit all successful patches
        await session.commit()

        success_count = sum(1 for r in results if r.success)

        return FABulkAssetPatchResponse(results=results, success_count=success_count, errors=[])


# ============================================================================
# ASSET METADATA SERVICES MANAGER
# ============================================================================


class AssetMetadataService:
    """
    Static service for asset metadata operations.

    All methods are static - no instance state required.
    """

    @staticmethod
    def compute_metadata_diff(old: Optional[FAClassificationParams], new: Optional[FAClassificationParams]) -> list[FAMetadataChangeDetail]:
        """
        Compute diff between old and new metadata.

        Tracks changes field-by-field for audit/display purposes.

        Args:
            old: Previous metadata state (or None)
            new: New metadata state (or None)

        Returns:
            List of FAMetadataChangeDetail objects describing changes

        Examples:
            >>> old = FAClassificationParams(sector="Energy")
            >>> new = FAClassificationParams(sector="Technology")
            >>> changes = AssetMetadataService.compute_metadata_diff(old, new)
            >>> len(changes)
            2
            >>> changes[0].field
            'sector'
        """
        changes = []

        # Convert to dicts for comparison
        old_dict = old.model_dump(exclude_none=False) if old else {}
        new_dict = new.model_dump(exclude_none=False) if new else {}

        # Get all fields from both dicts
        all_fields = set(old_dict.keys()) | set(new_dict.keys())

        for field in all_fields:
            old_value = old_dict.get(field)
            new_value = new_dict.get(field)

            # Check if changed
            if old_value != new_value:
                # Convert to JSON-serializable format for display
                old_display = json.dumps(old_value, default=str) if old_value is not None else None
                new_display = json.dumps(new_value, default=str) if new_value is not None else None

                changes.append(FAMetadataChangeDetail(field=field, old_value=old_display, new_value=new_display))

        return changes

    @staticmethod
    def apply_partial_update(current: Optional[FAClassificationParams], patch: FAClassificationParams) -> FAClassificationParams:
        """
        Apply PATCH request to current metadata.

        PATCH Semantics:
        - **Absent field** (not in patch dict) → ignored, keep current value
        - **null in JSON** (None in Python) → clear field (set to None)
        - **Value present** → update field
        - **geographic_area** → full block replace (no partial merge)

        Args:
            current: Current metadata state (or None for new metadata)
            patch: PATCH request with fields to update

        Returns:
            Updated FAClassificationParams

        Raises:
            ValueError: If validation fails (e.g., invalid geographic_area)

        Examples:
            >>> current = FAClassificationParams(sector="Technology")
            >>> patch = FAClassificationParams(sector=None)  # Clear sector
            >>> updated = AssetMetadataService.apply_partial_update(current, patch)
            >>> updated.sector
            None
        """
        # Start with current values (or empty dict)
        current_dict = (
            current.model_dump(exclude_none=False)
            if current
            else {
                "short_description": None,
                "geographic_area": None,
                "sector_area": None,
            }
        )

        # Get patch fields that were explicitly set (exclude unset fields)
        # This distinguishes between "field not in request" vs "field=null in request"
        patch_dict = patch.model_dump(exclude_unset=True)

        # Apply patch: only update fields that are present in patch_dict
        for field, value in patch_dict.items():
            current_dict[field] = value

        # Validate and return updated model
        try:
            return FAClassificationParams(**current_dict)
        except Exception as e:
            raise ValueError(f"Validation failed after applying PATCH: {e}") from e

    @staticmethod
    def merge_provider_metadata(current: Optional[FAClassificationParams], provider_data: dict) -> FAClassificationParams:
        """
        Merge provider-fetched metadata with current metadata.

        Strategy:
        - Provider data takes precedence over current values
        - Only updates fields that provider returns (non-None)
        - Current values preserved if provider doesn't return field

        Args:
            current: Current metadata state (or None)
            provider_data: Raw metadata dict from provider

        Returns:
            Merged FAClassificationParams

        Note:
            Provider data is already validated by FAClassificationParams
            when this is called (geo_normalization runs in field_validator)
        """
        # Start with current values
        current_dict = (
            current.model_dump(exclude_none=False)
            if current
            else {
                "short_description": None,
                "geographic_area": None,
                "sector_area": None,
            }
        )

        # Update with provider data (only non-None values)
        for field in ["short_description", "geographic_area", "sector_area"]:
            if field in provider_data and provider_data[field] is not None:
                current_dict[field] = provider_data[field]

        # Validate and return merged model
        return FAClassificationParams(**current_dict)


# ============================================================================
# ASSET SEARCE SERVICES
# ============================================================================


class AssetSearchService:
    """
    Service for searching assets across multiple providers.

    Features:
    - Parallel execution using asyncio.gather for performance
    - Graceful error handling per provider (errors don't fail entire search)
    - Provider filtering support
    - Aggregated results with metadata
    """

    @staticmethod
    async def search(query: str, provider_codes: Optional[list[str]] = None) -> FAProviderSearchResponse:
        """
        Search for assets across one or more providers in parallel.

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.
                           If None, queries all providers.

        Returns:
            FAProviderSearchResponse with aggregated results from all providers.

        Notes:
            - Providers that don't support search are silently skipped
            - Provider errors are logged but don't fail the entire search
            - Results are not deduplicated (same asset may appear from multiple providers)
        """
        # Get provider codes to query
        if not provider_codes:
            all_providers = AssetProviderRegistry.list_providers()
            provider_codes = [p["code"] for p in all_providers]

        # Filter to valid providers that support search
        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            provider_instance = AssetProviderRegistry.get_provider_instance(code)
            if provider_instance:
                if provider_instance.supports_search:
                    valid_providers.append((code, provider_instance))
                else:
                    logger.debug(f"Provider '{code}' does not support search, skipping")
            else:
                logger.warning(f"Provider '{code}' not found, skipping")

        if not valid_providers:
            return FAProviderSearchResponse(
                query=query,
                total_results=0,
                results=[],
                providers_queried=[],
                providers_with_errors=[],
            )

        # Create search tasks for parallel execution
        async def search_single_provider(code: str, provider) -> tuple[str, list[dict], str | None]:
            """
            Search a single provider and return (code, results, error).
            Error is None if successful, error message string if failed.
            Uses Layer 2 (query cache) and Layer 1 (item cache) for acceleration.
            """
            query_lower = query.lower().strip()
            query_cache_key = (code, query_lower)

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = _search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search query cache HIT for '{query}' on provider '{code}'")
                return (code, cached_query, None)

            # Layer 1: fuzzy match on cached individual items (24h)
            # Scan _search_result_cache keys for contains match
            # (theine doesn't expose keys() — we skip Layer 1 fuzzy for now
            #  and rely on Layer 2 for repeated queries)

            try:
                search_results = await _run_provider_in_thread(
                    lambda: provider.search(query),
                    timeout=30.0,
                )
                # Populate Layer 2
                _search_query_cache.set(query_cache_key, search_results)
                return (code, search_results, None)
            except Exception as e:
                error_str = str(e).lower()
                if "not_supported" in error_str or "not supported" in error_str:
                    logger.debug(f"Provider '{code}' does not support search")
                    return (code, [], None)
                else:
                    logger.error(f"Search error from provider '{code}': {e}")
                    return (code, [], str(e))

        # Execute all searches in parallel
        tasks = [search_single_provider(code, provider) for code, provider in valid_providers]

        search_results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results: list[FAProviderSearchResultItem] = []
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []

        for result in search_results_raw:
            if isinstance(result, Exception):
                # Unexpected exception from gather itself
                logger.error(f"Unexpected error in search task: {result}")
                continue

            code, items, error = result
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
                continue

            # Convert provider results to response schema
            for item in items:
                # Compute provider_url from provider instance
                provider_instance = AssetProviderRegistry.get_provider_instance(code)
                item_provider_url = None
                if provider_instance:
                    item_provider_url = provider_instance.get_asset_url(
                        item.get("identifier", ""),
                        item.get("identifier_type"),
                    )

                # Validate asset_type: fallback to OTHER if unknown
                raw_asset_type = item.get("type")
                if raw_asset_type and raw_asset_type not in AssetType.__members__:
                    logger.warning(f"Unknown asset_type '{raw_asset_type}' from provider '{code}', " f"falling back to OTHER")
                    raw_asset_type = "OTHER"

                results.append(
                    FAProviderSearchResultItem(
                        identifier=item.get("identifier", ""),
                        identifier_type=item.get("identifier_type"),
                        display_name=item.get("display_name", item.get("name", "")),
                        provider_code=code,
                        currency=item.get("currency"),
                        asset_type=raw_asset_type,
                        provider_url=item_provider_url,
                    )
                )

        return FAProviderSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            providers_queried=providers_queried,
            providers_with_errors=providers_with_errors,
        )

    @staticmethod
    async def search_stream(query: str, provider_codes: Optional[list[str]] = None) -> AsyncGenerator[str]:  # pragma: no cover
        """
        Stream search results as SSE events, one event per provider completion.

        Each provider runs concurrently; as each completes, its results are
        yielded immediately as an SSE event.

        SSE events:
        - provider_results: {provider_code, results: [...]}
        - done: {total_results, providers_queried, providers_with_errors}

        Args:
            query: Search query string
            provider_codes: Optional list of provider codes to query.

        Yields:
            SSE-formatted strings: "data: {...}\\n\\n"
        """
        # Resolve providers
        if not provider_codes:
            all_providers = AssetProviderRegistry.list_providers()
            provider_codes = [p["code"] for p in all_providers]

        valid_providers: list[tuple[str, AssetSourceProvider]] = []
        for code in provider_codes:
            instance = AssetProviderRegistry.get_provider_instance(code)
            if instance and instance.supports_search:
                valid_providers.append((code, instance))

        if not valid_providers:
            yield f'data: {json.dumps({"event": "done", "total_results": 0, "providers_queried": [], "providers_with_errors": []})}\n\n'
            return

        queue: asyncio.Queue = asyncio.Queue()
        total_results = 0
        providers_queried: list[str] = []
        providers_with_errors: list[str] = []

        async def _search_one(code: str, provider: object):
            """Run one provider search and put results on the queue."""
            query_lower = query.lower().strip()
            query_cache_key = (code, query_lower)

            # Layer 2: exact query cache (15min)
            cached_query, q_ok = _search_query_cache.get(query_cache_key)
            if q_ok and cached_query is not None:
                logger.debug(f"Search stream query cache HIT for '{query}' on provider '{code}'")
                await queue.put((code, cached_query, None))
                return

            try:
                items = await _run_provider_in_thread(
                    lambda: provider.search(query),
                    timeout=30.0,
                )
                # Populate Layer 2
                _search_query_cache.set(query_cache_key, items)
                await queue.put((code, items, None))
            except Exception as e:
                logger.warning(f"Search stream: provider '{code}' error: {e}")
                await queue.put((code, [], str(e)))

        # Launch all providers concurrently
        tasks = [asyncio.create_task(_search_one(code, prov)) for code, prov in valid_providers]

        # Yield results as they complete
        completed = 0
        while completed < len(tasks):
            code, items, error = await queue.get()
            completed += 1
            providers_queried.append(code)

            if error:
                providers_with_errors.append(code)
                yield f'data: {json.dumps({"event": "provider_error", "provider_code": code, "error": error})}\n\n'
                continue

            # Convert items to serializable dicts
            result_items = []
            for item in items:
                # Compute provider_url
                provider_instance = AssetProviderRegistry.get_provider_instance(code)
                item_provider_url = None
                if provider_instance:
                    item_provider_url = provider_instance.get_asset_url(
                        item.get("identifier", ""),
                        item.get("identifier_type"),
                    )

                # Validate asset_type
                raw_asset_type = item.get("type")
                if raw_asset_type and raw_asset_type not in AssetType.__members__:
                    raw_asset_type = "OTHER"

                # Extract enum .value to avoid "IdentifierType.TICKER" serialization
                raw_id_type = item.get("identifier_type", "")
                id_type_str = raw_id_type.value if hasattr(raw_id_type, "value") else str(raw_id_type)

                result_items.append(
                    {
                        "identifier": item.get("identifier", ""),
                        "identifier_type": id_type_str,
                        "display_name": item.get("display_name", item.get("name", "")),
                        "provider_code": code,
                        "currency": item.get("currency"),
                        "asset_type": raw_asset_type,
                        "provider_url": item_provider_url,
                    }
                )

            total_results += len(result_items)

            yield f'data: {json.dumps({"event": "provider_results", "provider_code": code, "results": result_items})}\n\n'

        # Final event
        yield f'data: {json.dumps({"event": "done", "total_results": total_results, "providers_queried": providers_queried, "providers_with_errors": providers_with_errors})}\n\n'

        # Ensure all tasks are awaited
        await asyncio.gather(*tasks, return_exceptions=True)
