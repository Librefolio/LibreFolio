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
from abc import ABC, abstractmethod
from datetime import date as date_type, timedelta
from typing import Optional, List, Dict

import structlog
from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset, AssetProviderAssignment,
    PriceHistory, IdentifierType, AssetType,
    )
from backend.app.schemas import (
    FACurrentValue, FAHistoricalData,
    FAMetadataRefreshResult, BackwardFillInfo,
    FAUpsert, FAPricePoint, FAAssetDelete, FAProviderAssignmentItem,
    FAProviderAssignmentResult, FARefreshItem, FABulkMetadataRefreshResponse,
    FABulkDeleteResponse, FAPriceDeleteResult, FABulkRemoveResponse,
    FAProviderRemovalResult, FABulkRefreshResponse, FARefreshResult)
from backend.app.schemas.assets import FAAssetPatchItem, FAClassificationParams, FAAssetCreateItem, FABulkAssetCreateResponse, FAAssetCreateResult, FAAinfoFiltersRequest, \
    FAinfoResponse, FABulkAssetDeleteResponse, FAAssetDeleteResult, FABulkAssetPatchResponse, FAAssetPatchResult, FAMetadataChangeDetail
from backend.app.schemas.common import OldNew
from backend.app.schemas.provider import FAProviderRefreshFieldsDetail, FAProviderSearchResponse, FAProviderSearchResultItem
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.decimal_utils import truncate_priceHistory

# Initialize structured logger
logger = structlog.get_logger(__name__)


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

    def get_icon(self) -> str | None:
        """
        Provider icon URL for UI display.

        Returns:
            URL string (remote or local path), or None for default icon
        """
        return None

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
            {"provider": self.provider_code}
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

    # TODO: definire metodo da far chiamare periodicamente ad un job garbage collector, per ripulire eventuali cache


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

        from backend.app.schemas.provider import FAProviderAssignmentResult

        results = []
        asset_ids = [a.asset_id for a in assignments]

        # Delete existing assignments (upsert pattern)
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids)))

        # Bulk insert new assignments
        new_assignments = []
        import json
        for a in assignments:
            raw_params = a.provider_params
            if isinstance(raw_params, dict):
                params_to_store = json.dumps(raw_params)
            else:
                params_to_store = raw_params

            new_assignments.append(
                AssetProviderAssignment(
                    asset_id=a.asset_id,
                    provider_code=a.provider_code,
                    identifier=a.identifier,
                    identifier_type=a.identifier_type,
                    provider_params=params_to_store,
                    fetch_interval=a.fetch_interval,  # Already has default from Pydantic
                    last_fetch_at=None,  # Never fetched yet
                    )
                )

        session.add_all(new_assignments)
        await session.commit()

        # Build results and auto-populate metadata
        for assignment in assignments:
            result = FAProviderAssignmentResult(
                asset_id=assignment.asset_id,
                success=True,
                message=f"Provider {assignment.provider_code} assigned",
                fields_detail=None  # No auto-refresh during assignment
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
                            patch_item = await provider.fetch_asset_metadata(
                                assignment.identifier,
                                assignment.identifier_type,
                                assignment.provider_params
                                )

                            if patch_item:
                                # Set correct asset_id
                                patch_item.asset_id = assignment.asset_id

                                # Apply metadata to asset
                                import json

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
                                    changes_count=changes_count
                                    )
                            else:
                                result.metadata_updated = False
                        except Exception as e:
                            # Log but don't fail assignment
                            logger.warning(
                                "Failed to fetch metadata from provider",
                                asset_id=assignment.asset_id,
                                provider=assignment.provider_code,
                                error=str(e)
                                )
            except Exception as e:
                # Log but don't fail assignment
                logger.warning(
                    "Error during metadata auto-populate",
                    asset_id=assignment.asset_id,
                    error=str(e)
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
                message="Provider removed"
                ) for aid in asset_ids
            ]
        return FABulkRemoveResponse(
            results=results,
            success_count=len(results),
            errors=[]
            )

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
        all_possible_fields = set(FAAssetPatchItem.model_fields.keys()) - {'asset_id'}

        for asset_id in asset_ids:
            try:
                # Get asset and assignment
                asset_stmt = select(Asset).where(Asset.id == asset_id)
                asset_result = await session.execute(asset_stmt)
                asset = asset_result.scalar_one_or_none()

                if not asset:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Asset {asset_id} not found"
                        ))
                    continue

                assignment_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)
                assignment_result = await session.execute(assignment_stmt)
                assignment = assignment_result.scalar_one_or_none()

                if not assignment:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"No provider assigned to asset {asset_id}"
                        ))
                    continue

                # Get provider instance
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
                if not provider:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Provider {assignment.provider_code} not found"
                        ))
                    continue

                # Fetch metadata from provider (returns None if not supported)
                provider_params = json.loads(assignment.provider_params) if assignment.provider_params else None

                try:
                    patch_item = await provider.fetch_asset_metadata(
                        assignment.identifier,
                        assignment.identifier_type,
                        provider_params
                        )
                except Exception as e:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Failed to fetch metadata: {str(e)}"
                        ))
                    continue

                if not patch_item:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Provider {assignment.provider_code} returned no metadata (may not support metadata fetch)"
                        ))
                    continue

                # Set correct asset_id
                patch_item.asset_id = asset_id

                # Calculate refreshed_fields with old/new values from patch_item
                patch_dict = patch_item.model_dump(exclude={'asset_id'}, exclude_unset=True)

                # Build OldNew list by comparing asset's current values with patch values
                refreshed_fields_with_changes: list[OldNew[str | None]] = []
                for field_name, new_value in patch_dict.items():
                    # Get old value from asset
                    old_value = getattr(asset, field_name, None)
                    # Convert to string representation for comparison
                    old_str = str(old_value) if old_value is not None else None
                    new_str = str(new_value) if new_value is not None else None

                    refreshed_fields_with_changes.append(OldNew(
                        info=field_name,
                        old=old_str,
                        new=new_str
                        ))

                # Calculate missing_data_fields
                # Fields that are patchable but not returned by provider
                # Exclude fields that are not typically refreshable: display_name, currency, active
                refreshable_fields = all_possible_fields - {'display_name', 'currency', 'active'}
                provider_returned_fields = set(patch_dict.keys())
                missing_data_fields = list(refreshable_fields - provider_returned_fields)

                # Store patch and fields detail
                patches_to_apply.append(patch_item)
                asset_fields_map[asset_id] = FAProviderRefreshFieldsDetail(
                    refreshed_fields=refreshed_fields_with_changes,
                    missing_data_fields=missing_data_fields,
                    ignored_fields=[]  # Future use
                    )

            except Exception as e:
                logger.error(f"Error preparing refresh for asset {asset_id}: {e}")
                results.append(FAMetadataRefreshResult(
                    asset_id=asset_id,
                    success=False,
                    message=f"Error: {str(e)}"
                    ))

        # Apply all patches in bulk using AssetCRUDService
        if patches_to_apply:
            patch_response = await AssetCRUDService.patch_assets_bulk(patches_to_apply, session)

            # Map patch results to refresh results with fields_detail
            for patch_result in patch_response.results:
                fields_detail = asset_fields_map.get(patch_result.asset_id)

                # Convert to FAMetadataRefreshResult with fields_detail
                results.append(FAMetadataRefreshResult(
                    asset_id=patch_result.asset_id,
                    success=patch_result.success,
                    message=patch_result.message,
                    fields_detail=fields_detail
                    ))

        success_count = sum(1 for r in results if r.success)

        return FABulkMetadataRefreshResponse(
            results=results,
            success_count=success_count,
            errors=[]
            )

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

        Optimized: Batch operations per asset, minimize DB roundtrips
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

            # Build PriceHistory objects for upsert
            # Strategy: DELETE existing dates + INSERT new (avoids SQLite ON CONFLICT issues)
            price_objects = []
            dates_to_upsert = []

            for price in prices:
                dates_to_upsert.append(price.date)

                price_obj = PriceHistory(
                    asset_id=asset_id,
                    date=price.date,
                    open=truncate_priceHistory(price.open, "open") if price.open is not None else None,
                    high=truncate_priceHistory(price.high, "high") if price.high is not None else None,
                    low=truncate_priceHistory(price.low, "low") if price.low is not None else None,
                    close=truncate_priceHistory(price.close, "close"),
                    volume=price.volume,
                    currency=price.currency or default_currency,
                    source_plugin_key="MANUAL",
                    fetched_at=None,
                    )
                price_objects.append(price_obj)

            # Delete existing prices for these dates (upsert = delete + insert)
            if dates_to_upsert:
                delete_stmt = delete(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates_to_upsert)))
                await session.execute(delete_stmt)

            # Bulk insert new prices
            session.add_all(price_objects)
            await session.commit()

            # Count as inserted
            total_inserted += len(price_objects)

            results.append({"asset_id": asset_id, "count": len(price_objects), "message": f"Upserted {len(price_objects)} prices"})
        # update_count = 0 because SQLite doesn't distinguish
        return {"inserted_count": total_inserted, "updated_count": 0, "results": results}

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
                count_stmt = select(func.count()).select_from(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date >= start, PriceHistory.date <= end))
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
                conditions.append(and_(PriceHistory.asset_id == asset_id, PriceHistory.date >= start, PriceHistory.date <= end))

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
                message=f"Deleted prices in {len(item.date_ranges)} range(s)"
                )
            for item in data
            ]

        return FABulkDeleteResponse(
            results=results,
            success_count=len(results),
            total_deleted=deleted_count,
            errors=[]
            )

    # ========================================================================
    # PRICE QUERY WITH BACKWARD-FILL + Special logic for PROVIDER DELEGATION
    # ========================================================================

    @staticmethod
    def _parse_provider_params(raw_params):
        """Parse provider params from DB (string/dict) into dict safely."""
        import json
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
    async def _fetch_provider_history(
        assignment: AssetProviderAssignment,
        asset_id: int,
        start_date: date_type,
        end_date: date_type,
        ) -> Optional[list[FAPricePoint]]:
        """Delegate to provider history fetch, returning FAPricePoint list or None on failure.

        Logs warnings with context when provider fetch fails for diagnostics.
        """
        provider_code = assignment.provider_code
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        if not provider:
            logger.warning(
                "Provider not registered in registry, falling back to DB",
                provider_code=provider_code,
                asset_id=asset_id,
                start_date=str(start_date),
                end_date=str(end_date)
                )
            return None

        params = AssetSourceManager._parse_provider_params(assignment.provider_params)

        try:
            historical = await provider.get_history_value(str(asset_id), params, start_date, end_date)
            # historical expected FAHistoricalData with prices: List[FAPricePoint]
            return historical.prices
        except Exception as e:
            logger.warning(
                "Provider fetch failed with exception, falling back to DB",
                provider_code=provider_code,
                asset_id=asset_id,
                start_date=str(start_date),
                end_date=str(end_date),
                exception_type=type(e).__name__,
                exception_message=str(e)
                )
            return None

    @staticmethod
    async def _fetch_db_price_map(
        session: AsyncSession,
        asset_id: int,
        start_date: date_type,
        end_date: date_type,
        ) -> dict[date_type, PriceHistory]:
        stmt = select(PriceHistory).where(
            and_(
                PriceHistory.asset_id == asset_id,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date,
                )
            ).order_by(PriceHistory.date)
        db_result = await session.execute(stmt)
        return {p.date: p for p in db_result.scalars().all()}

    @staticmethod
    def _build_backward_filled_series(price_map: dict[date_type, PriceHistory], start_date: date_type, end_date: date_type, ) -> list[FAPricePoint]:
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
                        backward_fill_info=BackwardFillInfo(actual_rate_date=last_known.date, days_back=days_back),
                        )
                    )
            # else: skip days before first known price
            current += timedelta(days=1)
        return results

    @staticmethod
    async def get_prices(
        asset_id: int,
        start_date: date_type,
        end_date: date_type,
        session: AsyncSession,
        ) -> list[FAPricePoint]:
        """Get prices for asset with backward-fill and provider delegation.

        Logic:
        1. Validate date range
        2. Fetch asset
        3. If provider assignment exists -> try provider fetch
        4. Fallback to DB with backward-fill

        Returns List[FAPricePoint] (uniform output).
        Synthetic yield (scheduled investment) handled entirely inside the dedicated provider plugin.
        """
        if start_date > end_date:
            raise ValueError(f"Start date {start_date} is after end date {end_date}")

        asset = await session.get(Asset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        assignment = await AssetSourceManager.get_asset_provider(asset_id, session)
        if assignment:
            provider_prices = await AssetSourceManager._fetch_provider_history(assignment, asset_id, start_date, end_date)
            if provider_prices is not None:
                return provider_prices
        # Fallback DB if no provider is assigned at current asset
        price_map = await AssetSourceManager._fetch_db_price_map(session, asset_id, start_date, end_date)
        return AssetSourceManager._build_backward_filled_series(price_map, start_date, end_date)

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

        Args:
            requests: List of FARefreshItem (asset_id, start_date, end_date)
            session: Database session
            concurrency: Max concurrent provider calls
            semaphore_timeout: Timeout for acquiring semaphore (seconds)

        Returns:
            FABulkRefreshResponse with per-item results

        Note: Already parallelized with asyncio.gather and semaphore
        """
        if not requests:
            return FABulkRefreshResponse(results=[])

        results = []
        sem = asyncio.Semaphore(concurrency)

        async def _process_single(item: FARefreshItem) -> FARefreshResult:
            asset_id = item.asset_id
            start = item.date_range.start
            end = item.date_range.end

            fetched_count = 0
            inserted_count = 0
            updated_count = 0
            errors = []

            # Resolve provider assignment
            try:
                assignment = await AssetSourceManager.get_asset_provider(asset_id, session)
                if not assignment:
                    errors.append("No provider assigned for asset")
                    return FARefreshResult(
                        asset_id=asset_id,
                        fetched_count=fetched_count,
                        inserted_count=inserted_count,
                        updated_count=updated_count,
                        errors=errors
                        )

                provider_code = assignment.provider_code
                provider_params = assignment.provider_params or {}
                identifier = assignment.identifier  # Identifier is in assignment, not asset

                # Verify asset exists
                asset_stmt = select(Asset).where(Asset.id == asset_id)
                asset_res = await session.execute(asset_stmt)
                asset = asset_res.scalar_one_or_none()
                if not asset:
                    errors.append(f"Asset {asset_id} not found")
                    return FARefreshResult(
                        asset_id=asset_id,
                        fetched_count=fetched_count,
                        inserted_count=inserted_count,
                        updated_count=updated_count,
                        errors=errors
                        )
            except Exception as e:
                errors.append(f"Failed to resolve provider or asset: {str(e)}")
                return FARefreshResult(
                    asset_id=asset_id,
                    fetched_count=fetched_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    errors=errors
                    )

            # Instantiate provider from registry
            prov = AssetProviderRegistry.get_provider_instance(provider_code)
            if not prov:
                errors.append(f"Provider not found: {provider_code}")
                return FARefreshResult(
                    asset_id=asset_id,
                    fetched_count=fetched_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    errors=errors
                    )

            # Parse provider_params if stored as JSON string
            try:
                import json
                if isinstance(provider_params, str):
                    provider_params = json.loads(provider_params)
            except Exception:
                # keep as-is if parsing fails
                pass

            # Validate params if provider supports it
            try:
                prov.validate_params(provider_params)
            except Exception as e:
                errors.append(f"Invalid provider params: {str(e)}")
                return FARefreshResult(
                    asset_id=asset_id,
                    fetched_count=fetched_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    errors=errors
                    )

            # Fetch existing DB entries (prefetch) while calling remote
            async def _fetch_db_existing():
                # Query all existing price dates in range for this asset
                stmt = select(PriceHistory).where(
                    and_(
                        PriceHistory.asset_id == asset_id,
                        PriceHistory.date >= start,
                        PriceHistory.date <= end,
                        )
                    )
                db_res = await session.execute(stmt)
                return {p.date: p for p in db_res.scalars().all()}

            # Provider fetch coroutine
            async def _fetch_remote():
                try:
                    prices_data = []
                    today = date_type.today()
                    identifier_type = assignment.identifier_type

                    # 1. Try to fetch historical data if provider supports it AND date range includes past dates
                    if prov.supports_history and start < today:
                        try:
                            # Fetch history up to yesterday (or end if end < today)
                            history_end = min(end, today - timedelta(days=1)) if end >= today else end
                            if start <= history_end:
                                hist_data = await prov.get_history_value(
                                    identifier, identifier_type, provider_params, start, history_end
                                    )
                                if hist_data and hist_data.prices:
                                    prices_data = [p.model_dump() for p in hist_data.prices]
                                    logger.debug(f"Fetched {len(prices_data)} historical prices for asset {asset_id}")
                        except Exception as hist_e:
                            logger.warning(f"History fetch failed for asset {asset_id}: {hist_e}")
                            # Continue - we'll try current value

                    # 2. Always try to get current value if end date includes today
                    if end >= today:
                        try:
                            current_data = await prov.get_current_value(
                                identifier, identifier_type, provider_params
                                )
                            if current_data and current_data.value:
                                # Create a price point for today
                                current_price = {
                                    "date": current_data.as_of_date or today,
                                    "close": current_data.value,
                                    "currency": current_data.currency or "USD"
                                    }

                                # Remove any existing entry for today from history (current value takes precedence)
                                prices_data = [p for p in prices_data if p.get("date") != current_price["date"]]
                                prices_data.append(current_price)
                                logger.debug(f"Added current price for asset {asset_id}: {current_data.value}")
                        except Exception as curr_e:
                            logger.warning(f"Current value fetch failed for asset {asset_id}: {curr_e}")
                            # Continue - we may still have history data

                    if not prices_data:
                        raise AssetSourceError(
                            "No price data available from provider",
                            "NO_DATA",
                            {"asset_id": asset_id, "provider": provider_code}
                            )

                    return {
                        "prices": prices_data,
                        "source": provider_code
                        }
                except AssetSourceError:
                    raise
                except Exception as e:
                    raise AssetSourceError(f"Provider fetch failed: {str(e)}", "PROVIDER_FETCH_ERROR", {})

            # Run both in parallel with semaphore
            try:
                async with asyncio.timeout(semaphore_timeout):
                    async with sem:
                        db_task = asyncio.create_task(_fetch_db_existing())
                        fetch_task = asyncio.create_task(_fetch_remote())

                        db_existing, remote_data = await asyncio.gather(db_task, fetch_task)
            except Exception as e:
                errors.append(str(e))
                return FARefreshResult(
                    asset_id=asset_id,
                    fetched_count=fetched_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    errors=errors
                    )

            # remote_data expected shape: {"prices": [ {date, open?, high?, low?, close, volume?, currency}, ... ], "source": "..."}
            prices = remote_data.get("prices", []) if isinstance(remote_data, dict) else []
            if not prices:
                errors.append("No prices returned from provider")
                return FARefreshResult(
                    asset_id=asset_id,
                    fetched_count=fetched_count,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    errors=errors
                    )

            # Convert prices to FAPricePoint objects
            price_items = []
            for p in prices:
                price_items.append(FAPricePoint(
                    date=p["date"],
                    open=p.get("open"),
                    high=p.get("high"),
                    low=p.get("low"),
                    close=p["close"],
                    volume=p.get("volume"),
                    currency=p.get("currency", "USD")
                    ))

            # Build FAUpsert object
            upsert_obj = FAUpsert(asset_id=asset_id, prices=price_items)

            try:
                upsert_res = await AssetSourceManager.bulk_upsert_prices([upsert_obj], session)
                fetched_count = len(prices)
                inserted_count = upsert_res.get("inserted_count", 0)
            except Exception as e:
                errors.append(f"DB upsert failed: {str(e)}")

            # Update last_fetch_at on assignment
            try:
                assignment.last_fetch_at = utcnow()
                session.add(assignment)
                await session.commit()
            except Exception:
                # Not critical, skip
                pass

            return FARefreshResult(
                asset_id=asset_id,
                fetched_count=fetched_count,
                inserted_count=inserted_count,
                updated_count=updated_count,
                errors=errors
                )

        # Create tasks for all items
        tasks = [asyncio.create_task(_process_single(item)) for item in requests]

        # Wait for all to complete
        completed = await asyncio.gather(*tasks)

        results = list(completed)
        return FABulkRefreshResponse(
            results=results,
            success_count=sum(1 for r in results if not r.errors),  # Success = no errors
            errors=[]
            )


# ============================================================================
# ASSET CRUD SERVICE
# ============================================================================


class AssetCRUDService:
    """Service for asset CRUD operations."""

    @staticmethod
    async def create_assets_bulk(
        assets: List[FAAssetCreateItem],
        session: AsyncSession
        ) -> FABulkAssetCreateResponse:
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
                    results.append(FAAssetCreateResult(
                        asset_id=None,
                        success=False,
                        message=f"Asset with display_name '{item.display_name}' already exists",
                        display_name=item.display_name,
                        identifier=None
                        ))
                    continue

                # Create asset record
                asset = Asset(
                    display_name=item.display_name,
                    currency=item.currency,
                    asset_type=item.asset_type or AssetType.OTHER,
                    icon_url=item.icon_url,
                    active=True,
                    )

                # Handle classification_params
                if item.classification_params:
                    asset.classification_params = item.classification_params.model_dump_json(exclude_none=True)

                session.add(asset)
                await session.flush()  # Get ID without committing

                results.append(FAAssetCreateResult(
                    asset_id=asset.id,
                    success=True,
                    message="Asset created successfully",
                    display_name=item.display_name
                    ))

                logger.info(f"Asset created: id={asset.id}, display_name={item.display_name}")

            except Exception as e:
                logger.error(f"Error creating asset {item.display_name}: {e}")
                results.append(FAAssetCreateResult(
                    asset_id=None,
                    success=False,
                    message=f"Error: {str(e)}",
                    display_name=item.display_name
                    ))

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
        return FABulkAssetCreateResponse(
            results=results,
            success_count=success_count,
            errors=[]
            )

    @staticmethod
    async def list_assets(
        filters: FAAinfoFiltersRequest,
        session: AsyncSession
        ) -> List[FAinfoResponse]:
        """
        List assets with optional filters - enhanced for BRIM asset matching.

        Supports filtering by:
        - currency, asset_type, active (existing)
        - search: partial match in display_name
        - isin: exact ISIN match via AssetProviderAssignment
        - symbol: exact ticker match via AssetProviderAssignment
        - identifier_contains: partial match in identifier field

        Args:
            filters: Query filters (see FAAinfoFiltersRequest)
            session: Database session

        Returns:
            List of assets matching filters, with identifier info
        """
        # Build base query with LEFT JOIN to get provider assignment data
        stmt = select(
            Asset,
            AssetProviderAssignment.id.label('provider_id'),
            AssetProviderAssignment.identifier.label('identifier'),
            AssetProviderAssignment.identifier_type.label('identifier_type')
            ).outerjoin(
            AssetProviderAssignment,
            Asset.id == AssetProviderAssignment.asset_id
            )

        # Apply filters
        conditions = []

        if filters.currency:
            conditions.append(Asset.currency == filters.currency)

        if filters.asset_type:
            conditions.append(Asset.asset_type == filters.asset_type)

        conditions.append(Asset.active == filters.active)

        if filters.search:
            search_pattern = f"%{filters.search}%"
            conditions.append(Asset.display_name.ilike(search_pattern))

        # NEW: ISIN exact match (identifier_type = ISIN)
        if filters.isin:
            conditions.append(and_(
                AssetProviderAssignment.identifier == filters.isin,
                AssetProviderAssignment.identifier_type == IdentifierType.ISIN
                ))

        # NEW: Symbol/ticker exact match (identifier_type = TICKER)
        if filters.symbol:
            conditions.append(and_(
                AssetProviderAssignment.identifier == filters.symbol,
                AssetProviderAssignment.identifier_type == IdentifierType.TICKER
                ))

        # NEW: Partial identifier match (any type)
        if filters.identifier_contains:
            conditions.append(
                AssetProviderAssignment.identifier.ilike(f"%{filters.identifier_contains}%")
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
            provider_id = row[1]  # provider_id from join
            identifier = row[2]  # identifier from join
            identifier_type = row[3]  # identifier_type from join

            assets.append(FAinfoResponse(
                id=asset.id,
                display_name=asset.display_name,
                currency=asset.currency,
                icon_url=asset.icon_url,
                asset_type=asset.asset_type,
                active=asset.active,
                has_provider=provider_id is not None,
                has_metadata=asset.classification_params is not None,
                identifier=identifier,
                identifier_type=identifier_type  # Pass enum directly
                ))

        return assets

    @staticmethod
    async def delete_assets_bulk(
        asset_ids: List[int],
        session: AsyncSession
        ) -> FABulkAssetDeleteResponse:
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
            try:
                # Check if asset exists
                stmt = select(Asset).where(Asset.id == asset_id)
                result = await session.execute(stmt)
                asset = result.scalar_one_or_none()

                if not asset:
                    results.append(FAAssetDeleteResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Asset with ID {asset_id} not found"
                        ))
                    continue

                # Try to delete (will fail if transactions exist due to FK constraint)
                await session.delete(asset)
                await session.flush()  # Check FK constraints before commit

                results.append(FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=True,
                    deleted_count=1,
                    message="Asset deleted successfully"
                    ))

                logger.info(f"Asset deleted: id={asset_id}")

            except Exception as e:
                await session.rollback()
                error_msg = str(e)

                # Check if error is due to FK constraint (transactions exist)
                if "FOREIGN KEY constraint failed" in error_msg or "foreign key" in error_msg.lower():
                    message = f"Cannot delete asset {asset_id}: has existing transactions"
                else:
                    message = f"Error deleting asset {asset_id}: {error_msg}"

                results.append(FAAssetDeleteResult(
                    asset_id=asset_id,
                    success=False,
                    deleted_count=0,
                    message=message
                    ))
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
            errors=[]  # Operation-level errors (none for now)
            )

    @staticmethod
    async def patch_assets_bulk(
        patches: List[FAAssetPatchItem],
        session: AsyncSession
        ) -> FABulkAssetPatchResponse:
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
                    results.append(FAAssetPatchResult(asset_id=patch.asset_id, success=False, message=f"Asset {patch.asset_id} not found", updated_fields=None))
                    continue
                asset_classification_params_before = json.loads(asset.classification_params) if asset.classification_params else {}
                logger.debug(f"Asset found for patching: id={patch.asset_id}: {asset.model_dump_json()}")

                # Track updated fields
                updated_fields: List[OldNew[str]] = []

                # Update fields if present in patch (use model_dump to detect presence)
                # Use exclude_unset=True to only include fields that were explicitly set
                # Use exclude_none=True to exclude None values (except classification_params which we handle specially)
                patch_dict = patch.model_dump(mode='json', exclude={'asset_id'}, exclude_unset=True, exclude_none=True)

                # Special handling for classification_params=None (clearing the field)
                # Check if it was explicitly set to None in the original patch object
                if 'classification_params' not in patch_dict and patch.classification_params is None:
                    # Check if the field was explicitly set (not just default None)
                    # We can use __pydantic_fields_set__ to check
                    if 'classification_params' in patch.model_fields_set:
                        patch_dict['classification_params'] = None

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
                            value = FAClassificationParams(**merged).model_dump(mode='json', exclude_none=True)
                            if not value:  # If result is empty dict, set to None
                                value = None
                    if not value:
                        value = None  # Explicitly set to None if falsey value (e.g., empty string)
                    if isinstance(value, dict):
                        value = json.dumps(value)  # Transform dict as serialized JSON
                    oldVal = getattr(asset, field)
                    setattr(asset, field, value)
                    updated_fields.append(OldNew(info=field, old=oldVal, new=value))
                    logger.debug(f"updated field '{field}': '{oldVal}' -> '{value}'")

                await session.flush()

                results.append(FAAssetPatchResult(
                    asset_id=patch.asset_id,
                    success=True,
                    message=f"Asset patched successfully ({len(updated_fields)} fields)",
                    updated_fields=updated_fields
                    ))

                logger.info(f"Asset patched: id={patch.asset_id}, fields={updated_fields}")

            except Exception as e:
                logger.error(f"Error patching asset {patch.asset_id}: {e}")
                results.append(FAAssetPatchResult(
                    asset_id=patch.asset_id,
                    success=False,
                    message=f"Error: {str(e)}",
                    updated_fields=None
                    ))

        # Commit all successful patches
        await session.commit()

        success_count = sum(1 for r in results if r.success)

        return FABulkAssetPatchResponse(
            results=results,
            success_count=success_count,
            errors=[]
            )


# ============================================================================
# ASSET METADATA SERVICES MANAGER
# ============================================================================


class AssetMetadataService:
    """
    Static service for asset metadata operations.

    All methods are static - no instance state required.
    """

    @staticmethod
    def compute_metadata_diff(
        old: Optional[FAClassificationParams],
        new: Optional[FAClassificationParams]
        ) -> list[FAMetadataChangeDetail]:
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

                changes.append(FAMetadataChangeDetail(
                    field=field,
                    old_value=old_display,
                    new_value=new_display
                    ))

        return changes

    @staticmethod
    def apply_partial_update(
        current: Optional[FAClassificationParams],
        patch: FAClassificationParams
        ) -> FAClassificationParams:
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
        current_dict = current.model_dump(exclude_none=False) if current else {
            'short_description': None,
            'geographic_area': None,
            'sector_area': None,
            }

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
            raise ValueError(f"Validation failed after applying PATCH: {e}")

    @staticmethod
    def merge_provider_metadata(
        current: Optional[FAClassificationParams],
        provider_data: dict
        ) -> FAClassificationParams:
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
        current_dict = current.model_dump(exclude_none=False) if current else {
            'short_description': None,
            'geographic_area': None,
            'sector_area': None,
            }

        # Update with provider data (only non-None values)
        for field in ['short_description', 'geographic_area', 'sector_area']:
            if field in provider_data and provider_data[field] is not None:
                current_dict[field] = provider_data[field]

        # Validate and return merged model
        return FAClassificationParams(**current_dict)

    @staticmethod
    async def update_asset_metadata(
        asset_id: int,
        patch: FAClassificationParams,
        session: 'AsyncSession'
        ) -> 'FAMetadataRefreshResult':
        """
        Update asset metadata with PATCH semantics.

        Loads asset, applies PATCH update, validates, persists to database,
        and computes changes for tracking.

        Args:
            asset_id: Asset ID to update
            patch: PATCH request with fields to update
            session: Database session

        Returns:
            FAMetadataRefreshResult with success status and changes

        Raises:
            ValueError: If asset not found or validation fails

        Examples:
            >>> from backend.app.schemas.assets import FAClassificationParams
            >>> patch = FAClassificationParams(sector="Technology")
            >>> result = await AssetMetadataService.update_asset_metadata(1, patch, session)
            >>> result.success
            True
            >>> result.changes
            [FAMetadataChangeDetail(field='sector', old=None, new='"Technology"')]
        """

        # Load asset from DB
        result = await session.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        # Parse current classification_params
        current_params = None
        if asset.classification_params:
            try:
                current_params = FAClassificationParams.model_validate_json(asset.classification_params)
            except Exception as e:
                logger.error(
                    "Failed to parse classification_params from database",
                    asset_id=asset_id,
                    error=str(e),
                    classification_params=asset.classification_params[:200] if len(asset.classification_params) > 200 else asset.classification_params
                    )
                pass  # Treat invalid JSON as None

        # Apply PATCH update
        try:
            updated_params = AssetMetadataService.apply_partial_update(
                current_params,
                patch
                )
        except ValueError as e:
            # Re-raise validation errors (will become 422 in API layer)
            raise ValueError(f"Validation failed: {e}")

        # Compute changes before persisting
        changes = AssetMetadataService.compute_metadata_diff(current_params, updated_params)

        # Serialize back to JSON
        asset.classification_params = updated_params.model_dump_json(exclude_none=True) if updated_params else None

        # Commit transaction
        await session.commit()

        # Refresh to get updated data
        await session.refresh(asset)

        # Build response with changes
        return FAMetadataRefreshResult(
            asset_id=asset.id,
            success=True,
            message="Metadata updated successfully",
            changes=changes
            )


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
    async def search(
        query: str,
        provider_codes: Optional[list[str]] = None
        ) -> FAProviderSearchResponse:
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
            provider_codes = [p['code'] for p in all_providers]

        # Filter to valid providers only
        valid_providers: list[tuple[str, object]] = []
        for code in provider_codes:
            provider_instance = AssetProviderRegistry.get_provider_instance(code)
            if provider_instance:
                valid_providers.append((code, provider_instance))
            else:
                logger.warning(f"Provider '{code}' not found, skipping")

        if not valid_providers:
            return FAProviderSearchResponse(
                query=query,
                total_results=0,
                results=[],
                providers_queried=[],
                providers_with_errors=[]
                )

        # Create search tasks for parallel execution
        async def search_single_provider(code: str, provider) -> tuple[str, list[dict], str | None]:
            """
            Search a single provider and return (code, results, error).
            Error is None if successful, error message string if failed.
            """
            try:
                search_results = await provider.search(query)
                return (code, search_results, None)
            except Exception as e:
                error_str = str(e).lower()
                if "not_supported" in error_str or "not supported" in error_str:
                    # Not an error, just unsupported
                    logger.debug(f"Provider '{code}' does not support search")
                    return (code, [], None)
                else:
                    logger.error(f"Search error from provider '{code}': {e}")
                    return (code, [], str(e))

        # Execute all searches in parallel
        tasks = [
            search_single_provider(code, provider)
            for code, provider in valid_providers
            ]

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
                results.append(FAProviderSearchResultItem(
                    identifier=item.get("identifier", ""),
                    identifier_type=item.get("identifier_type"),
                    display_name=item.get("display_name", item.get("name", "")),
                    provider_code=code,
                    currency=item.get("currency"),
                    asset_type=item.get("type")
                    ))

        return FAProviderSearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            providers_queried=providers_queried,
            providers_with_errors=providers_with_errors
            )
