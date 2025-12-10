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

TODO (Plan 05b - Step 12): Schema changes to implement
1. Update FAPriceDeleteResult construction:
   - CRITICAL: Rename field 'deleted' to 'deleted_count'
   - Ensure success field is always populated
   - Handle optional message field
2. Update FABulkDeleteResponse construction:
   - Now inherits from BaseBulkDeleteResponse
   - Use 'total_deleted' instead of 'deleted_count' for aggregate
3. Update FARefreshItem usage:
   - Handle date_range: DateRangeModel instead of start_date/end_date
   - Extract date_range.start and date_range.end for internal logic
4. Update FABulkRefreshResponse construction:
   - Populate success_count (required by BaseBulkResponse)
5. Update FAProviderRemovalResult construction:
   - Ensure deleted_count is 0 or 1 for single provider removal
6. Update FABulkAssignResponse and FABulkRemoveResponse:
   - Populate success_count (required by BaseBulkResponse)
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
    PriceHistory, IdentifierType,
    )
from backend.app.schemas import (
    FACurrentValue, FAHistoricalData,
    FAMetadataRefreshResult, FAPricePoint, BackwardFillInfo,
    FAUpsert, FAPricePoint, FAAssetDelete, FAProviderAssignmentItem,
    FAProviderAssignmentResult, FARefreshItem, FABulkMetadataRefreshResponse,
    FABulkDeleteResponse, FAPriceDeleteResult, FABulkRemoveResponse,
    FAProviderRemovalResult, FABulkRefreshResponse, FARefreshResult)
from backend.app.schemas.assets import FAAssetPatchItem
from backend.app.schemas.provider import FAProviderRefreshFieldsDetail
from backend.app.services.asset_crud import AssetCRUDService
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
    Abstract base class for asset pricing providers.

    All providers must implement:
    - get_current_value(): Fetch current price
    - get_history_value(): Fetch historical prices
    - search(): Search for assets (if supported)
    - validate_params(): Validate provider_params

    Providers auto-register via @register_provider(AssetProviderRegistry) decorator.
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider code (e.g., 'yfinance', 'cssscraper')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    def get_icon(self) -> str | None:
        """
        Return provider icon URL (hardcoded).

        Returns:
            Optional icon URL string (can be remote or local path)
        """
        return None  # Default: no icon

    @property
    @abstractmethod
    def test_cases(self) -> list[dict]:
        """
        List of test cases with 'identifier' and 'provider_params' for testing.
        :return: [{"identifier": str, "provider_params": dict | None}, ...]
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
        Fetch current price for asset.

        Args:
            identifier: Asset identifier for provider (e.g., ticker, ISIN, UUID)
            identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
            provider_params: Provider-specific configuration (JSON)

        Returns:
            CurrentValue with latest price

        Raises:
            AssetSourceError: On fetch failure
        """
        pass

    @property
    def supports_history(self) -> bool:
        """Whether this provider supports historical data."""
        return True  # In theory except special case, all plugin should support this feature

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
        Fetch historical prices for date range.

        Args:
            identifier: Asset identifier for provider (e.g., ticker, ISIN, UUID)
            identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
            provider_params: Provider-specific configuration (JSON)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            HistoricalData with price series

        Raises:
            AssetSourceError: On fetch failure
        """
        pass

    @property
    @abstractmethod
    def test_search_query(self) -> str | None:
        """Search query to use in tests, return None if query feature is not supported"""
        pass

    async def search(self, query: str) -> list[dict]:
        """
        Search for assets via provider (if supported).

        Args:
            query: Search query string

        Returns:
            List of {identifier, display_name, currency, type}

        Raises:
            AssetSourceError: If search not supported or fails
        """
        raise AssetSourceError(
            f"Search not supported by {self.provider_name}",
            "NOT_SUPPORTED",
            {"provider": self.provider_code}
            )

    @abstractmethod
    def validate_params(self, params: dict | None) -> None:
        """
        Validate provider_params structure.

        Base implementation accepts None or empty dict (no params required).
        Override this method if your provider requires specific parameters.

        Args:
            params: Provider parameters to validate (can be None)

        Raises:
            AssetSourceError: If params invalid
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

        Override this method if your provider can fetch metadata
        (asset_type, sector, geographic_area, short_description).

        Args:
            identifier: Asset identifier for provider
            identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
            provider_params: Provider-specific configuration (JSON)

        Returns:
            FAAssetPatchItem with metadata fields (asset_id placeholder=0, caller sets real ID)
            or None if not supported/fetch fails

        Raises:
            AssetSourceError: On fetch failure
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

                # Check if provider supports metadata fetch
                if provider and hasattr(provider, 'fetch_asset_metadata'):
                    # Get asset to fetch currency and current metadata
                    asset_result = await session.execute(select(Asset).where(Asset.id == assignment.asset_id))
                    asset = asset_result.scalar_one_or_none()

                    if asset:
                        # Try to fetch metadata
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
                                from backend.app.services.asset_metadata import AssetMetadataService
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
                        message=f"Asset {asset_id} not found",
                        changes=None
                        ))
                    continue

                assignment_stmt = select(AssetProviderAssignment).where(
                    AssetProviderAssignment.asset_id == asset_id
                    )
                assignment_result = await session.execute(assignment_stmt)
                assignment = assignment_result.scalar_one_or_none()

                if not assignment:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"No provider assigned to asset {asset_id}",
                        changes=None
                        ))
                    continue

                # Get provider instance
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
                if not provider:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Provider {assignment.provider_code} not found",
                        changes=None
                        ))
                    continue

                # Check if provider supports metadata fetch
                if not hasattr(provider, 'fetch_asset_metadata'):
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message=f"Provider {assignment.provider_code} doesn't support metadata fetch",
                        changes=None
                        ))
                    continue

                # Fetch metadata from provider
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
                        message=f"Failed to fetch metadata: {str(e)}",
                        changes=None
                        ))
                    continue

                if not patch_item:
                    results.append(FAMetadataRefreshResult(
                        asset_id=asset_id,
                        success=False,
                        message="Provider returned no metadata",
                        changes=None
                        ))
                    continue

                # Set correct asset_id
                patch_item.asset_id = asset_id

                # Calculate refreshed_fields from patch_item
                patch_dict = patch_item.model_dump(exclude={'asset_id'}, exclude_unset=True)
                refreshed_fields = list(patch_dict.keys())

                # Calculate missing_data_fields
                # Fields that are patchable but not returned by provider
                # Exclude fields that are not typically refreshable: display_name, currency, active
                refreshable_fields = all_possible_fields - {'display_name', 'currency', 'active'}
                provider_returned_fields = set(patch_dict.keys())
                missing_data_fields = list(refreshable_fields - provider_returned_fields)

                # Store patch and fields detail
                patches_to_apply.append(patch_item)
                asset_fields_map[asset_id] = FAProviderRefreshFieldsDetail(
                    refreshed_fields=refreshed_fields,
                    missing_data_fields=missing_data_fields,
                    ignored_fields=[]  # Future use
                    )

            except Exception as e:
                logger.error(f"Error preparing refresh for asset {asset_id}: {e}")
                results.append(FAMetadataRefreshResult(
                    asset_id=asset_id,
                    success=False,
                    message=f"Error: {str(e)}",
                    changes=None
                    ))

        # Apply all patches in bulk using AssetCRUDService
        if patches_to_apply:
            patch_response = await AssetCRUDService.patch_assets_bulk(patches_to_apply, session)

            # Map patch results to refresh results with fields_detail
            for patch_result in patch_response.results:
                fields_detail = asset_fields_map.get(patch_result.asset_id)

                # Convert to FAMetadataRefreshResult
                # Note: fields_detail should be embedded in changes or as separate field
                # For now, keep backward compatibility with changes=None and log fields_detail
                results.append(FAMetadataRefreshResult(
                    asset_id=patch_result.asset_id,
                    success=patch_result.success,
                    message=patch_result.message,
                    changes=None  # TODO: Use fields_detail instead of changes
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

                # Fetch asset to get identifier
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

                identifier = asset.identifier
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
                    hist_data = await prov.get_history_value(identifier, provider_params, start, end)
                    # Convert FAHistoricalData to dict for compatibility
                    return {
                        "prices": [p.model_dump() for p in hist_data.prices],
                        "source": hist_data.source
                        }
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
