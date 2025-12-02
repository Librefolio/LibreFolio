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
from abc import ABC, abstractmethod
from datetime import date as date_type, timedelta
from typing import Optional, List, Dict

import structlog
from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
    PriceHistory,
    )
from backend.app.schemas import (
    FACurrentValue, FAHistoricalData, FAClassificationParams,
    FAMetadataRefreshResult, FAPricePoint, BackwardFillInfo,
    FAUpsert, FAUpsertItem, FAAssetDelete, FAProviderAssignmentItem,
    FAProviderAssignmentResult, FARefreshItem, FABulkMetadataRefreshResponse,
    FABulkDeleteResponse, FAPriceDeleteResult, FABulkRemoveResponse,
    FAProviderRemovalResult, FABulkRefreshResponse, FARefreshResult)
from backend.app.services.asset_metadata import AssetMetadataService
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
        provider_params: dict,
        ) -> FACurrentValue:
        """
        Fetch current price for asset.

        Args:
            identifier: Asset identifier in the plugin contest (e.g., ticker)
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
        provider_params: Dict | None,
        start_date: date_type,
        end_date: date_type,
        ) -> FAHistoricalData:
        """
        Fetch historical prices for date range.

        Args:
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
        provider_params: dict | None = None,
        ) -> dict | None:
        """
        Fetch asset metadata from provider (optional feature).

        Override this method if your provider can fetch classification metadata
        (investment_type, sector, geographic_area, short_description).

        Args:
            identifier: Asset identifier
            provider_params: Provider-specific configuration (JSON)

        Returns:
            dict with metadata fields or None if not supported/available
            Expected keys: investment_type, sector, geographic_area, short_description

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
                metadata_updated=None,
                metadata_changes=None
                )

            # Try to auto-populate metadata from provider
            try:
                # Get provider instance
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)

                # Check if provider supports metadata fetch
                if provider and hasattr(provider, 'fetch_asset_metadata'):
                    # Get asset to fetch identifier
                    asset_result = await session.execute(select(Asset).where(Asset.id == assignment.asset_id))
                    asset = asset_result.scalar_one_or_none()

                    if asset:
                        # Try to fetch metadata
                        try:
                            metadata = await provider.fetch_asset_metadata(asset.identifier, assignment.provider_params)

                            if metadata:
                                # Parse current metadata
                                current_params = None
                                if asset.classification_params:
                                    try:
                                        current_params = FAClassificationParams.model_validate_json(asset.classification_params)
                                    except Exception as e:
                                        logger.error(
                                            "Failed to parse classification_params during provider assignment",
                                            asset_id=assignment.asset_id,
                                            error=str(e),
                                            classification_params=asset.classification_params[:200] if len(asset.classification_params) > 200 else asset.classification_params
                                            )
                                        pass

                                # Merge with provider data
                                updated_params = AssetMetadataService.merge_provider_metadata(
                                    current_params,
                                    metadata
                                    )

                                # Compute diff
                                changes = AssetMetadataService.compute_metadata_diff(
                                    current_params,
                                    updated_params
                                    )

                                # Serialize and update asset
                                asset.classification_params = updated_params.model_dump_json(exclude_none=True)

                                await session.commit()

                                # Add metadata info to result
                                if changes:
                                    result.metadata_updated = True
                                    result.metadata_changes = [{"field": c.field, "old": c.old_value, "new": c.new_value} for c in changes]
                                    logger.info(
                                        "Metadata auto-populated from provider",
                                        asset_id=assignment.asset_id,
                                        provider=assignment.provider_code,
                                        changes_count=len(changes)
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
        results = [FAProviderRemovalResult(asset_id=aid, success=True, message="Provider removed") for aid in asset_ids]
        return FABulkRemoveResponse(results=results, success_count=len(results))

    @staticmethod
    async def _refresh_single_metadata(asset_id: int, session: AsyncSession) -> FAMetadataRefreshResult:
        """
        Refresh metadata for a single asset (internal helper).

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            FAMetadataRefreshResult
        """
        try:
            # Load asset and provider assignment
            asset_result = await session.execute(select(Asset).where(Asset.id == asset_id))
            asset = asset_result.scalar_one_or_none()

            if not asset:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Asset {asset_id} not found")

            # Get provider assignment
            provider_result = await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id))
            provider_assignment = provider_result.scalar_one_or_none()

            if not provider_assignment:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message="No provider assigned to asset")

            # Get provider instance
            provider = AssetProviderRegistry.get_provider_instance(provider_assignment.provider_code)

            if not provider:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Provider {provider_assignment.provider_code} not found")

            # Check if provider supports metadata fetch
            if not hasattr(provider, 'fetch_asset_metadata'):
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Provider {provider_assignment.provider_code} doesn't support metadata fetch")

            # Parse provider params
            import json
            provider_params = None
            if provider_assignment.provider_params:
                try:
                    provider_params = json.loads(provider_assignment.provider_params)
                except json.JSONDecodeError:
                    provider_params = provider_assignment.provider_params

            # Fetch metadata from provider
            try:
                metadata = await provider.fetch_asset_metadata(asset.identifier, provider_params)
            except Exception as e:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Failed to fetch metadata: {str(e)}")

            if not metadata:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message="Provider returned no metadata")

            # Parse current metadata
            current_params = None
            if asset.classification_params:
                try:
                    current_params = FAClassificationParams.model_validate_json(asset.classification_params)
                except Exception as e:
                    logger.error(
                        "Failed to parse classification_params during metadata refresh",
                        asset_id=asset_id,
                        error=str(e),
                        classification_params=asset.classification_params[:200] if len(asset.classification_params) > 200 else asset.classification_params
                        )

            # Merge with provider data
            try:
                merged = AssetMetadataService.merge_provider_metadata(current_params, metadata)
            except ValueError as e:
                return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Validation failed: {str(e)}")

            # Compute diff
            changes = AssetMetadataService.compute_metadata_diff(current_params, merged)

            # Update asset
            asset.classification_params = merged.model_dump_json(exclude_none=True)

            await session.commit()

            # Log success
            logger.info(
                "Metadata refreshed from provider",
                asset_id=asset_id,
                provider=provider_assignment.provider_code,
                changes_count=len(changes)
                )

            # Build result
            changes_list = None
            if changes:
                changes_list = [{"field": c.field, "old_value": c.old_value, "new_value": c.new_value} for c in changes]

            return FAMetadataRefreshResult(
                asset_id=asset_id,
                success=True,
                message=f"Metadata refreshed from {provider_assignment.provider_code}",
                changes=changes_list
                )

        except Exception as e:
            logger.error("Error refreshing metadata", asset_id=asset_id, error=str(e))
            return FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Internal error: {str(e)}")

    @staticmethod
    async def bulk_refresh_metadata(asset_ids: list[int], session: AsyncSession) -> FABulkMetadataRefreshResponse:
        """
        Bulk refresh metadata for multiple assets (PRIMARY bulk method).

        Supports partial success - each asset refresh is independent.
        Uses asyncio.gather for parallel processing.

        Args:
            asset_ids: List of asset IDs
            session: Database session

        Returns:
            FABulkMetadataRefreshResponse with results and counts
        """
        if not asset_ids:
            return FABulkMetadataRefreshResponse(results=[], success_count=0, failed_count=0)

        # Process all assets in parallel
        tasks = [AssetSourceManager._refresh_single_metadata(asset_id, session) for asset_id in asset_ids]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Count successes
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        return FABulkMetadataRefreshResponse(results=list(results), success_count=success_count, failed_count=failed_count)

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
                deleted=asset_delete_counts.get(item.asset_id, 0),
                message=f"Deleted prices in {len(item.date_ranges)} range(s)"
                )
            for item in data
            ]

        return FABulkDeleteResponse(deleted_count=deleted_count, results=results)

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
            start = item.start_date
            end = item.end_date

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

            # Convert prices to FAUpsertItem objects
            price_items = []
            for p in prices:
                price_items.append(FAUpsertItem(
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

        return FABulkRefreshResponse(results=list(completed))
