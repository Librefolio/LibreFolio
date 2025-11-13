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
from datetime import date as date_type, timedelta, datetime
from typing import Optional

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
    PriceHistory,
    )
from backend.app.schemas import CurrentValueModel, HistoricalDataModel
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.utils.decimal_utils import truncate_price_to_db_precision
from backend.app.utils.financial_math import parse_decimal_value


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
        """
        pass

    @abstractmethod
    async def get_current_value(
        self,
        identifier: str,
        provider_params: dict,
        ) -> CurrentValueModel:
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
        provider_params: dict,
        start_date: date_type,
        end_date: date_type,
        ) -> HistoricalDataModel:
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
    def validate_params(self, params: dict) -> None:
        """
        Validate provider_params structure.

        Args:
            params: Provider parameters to validate

        Raises:
            AssetSourceError: If params invalid
        """
        pass  # Default: plugin need to validate params, if is not necessary override with pass

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
        assignments: list[dict],
        session: AsyncSession,
        ) -> list[dict]:
        """
        Bulk assign/update providers to assets (PRIMARY bulk method).

        Args:
            assignments: List of {asset_id, provider_code, provider_params}
            session: Database session

        Returns:
            List of results: [{asset_id, success, message}, ...]

        Optimized: 1 delete + 1 insert query
        """
        if not assignments:
            return []

        results = []
        asset_ids = [a["asset_id"] for a in assignments]

        # Delete existing assignments (upsert pattern)
        await session.execute(
            delete(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id.in_(asset_ids)
                )
            )

        # Bulk insert new assignments
        new_assignments = []
        import json
        for a in assignments:
            raw_params = a.get("provider_params")
            if isinstance(raw_params, dict):
                params_to_store = json.dumps(raw_params)
            else:
                params_to_store = raw_params

            new_assignments.append(
                AssetProviderAssignment(
                    asset_id=a["asset_id"],
                    provider_code=a["provider_code"],
                    provider_params=params_to_store,
                    last_fetch_at=None,  # Never fetched yet
                    )
                )

        session.add_all(new_assignments)
        await session.commit()

        # Build results
        for assignment in assignments:
            results.append({
                "asset_id": assignment["asset_id"],
                "success": True,
                "message": f"Provider {assignment['provider_code']} assigned"
                })

        return results

    @staticmethod
    async def assign_provider(
        asset_id: int,
        provider_code: str,
        provider_params: Optional[str],
        session: AsyncSession,
        ) -> dict:
        """
        Assign provider to single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            provider_code: Provider code
            provider_params: Provider parameters (JSON string)
            session: Database session

        Returns:
            Single result dict
        """
        results = await AssetSourceManager.bulk_assign_providers(
            [{"asset_id": asset_id, "provider_code": provider_code, "provider_params": provider_params}],
            session
            )
        return results[0]

    @staticmethod
    async def bulk_remove_providers(
        asset_ids: list[int],
        session: AsyncSession,
        ) -> list[dict]:
        """
        Bulk remove provider assignments (PRIMARY bulk method).

        Args:
            asset_ids: List of asset IDs
            session: Database session

        Returns:
            List of results: [{asset_id, success, message}, ...]

        Optimized: 1 DELETE query with WHERE IN
        """
        if not asset_ids:
            return []

        await session.execute(
            delete(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id.in_(asset_ids)
                )
            )
        await session.commit()

        return [
            {"asset_id": aid, "success": True, "message": "Provider removed"}
            for aid in asset_ids
            ]

    @staticmethod
    async def remove_provider(
        asset_id: int,
        session: AsyncSession,
        ) -> dict:
        """
        Remove provider from single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            Single result dict
        """
        results = await AssetSourceManager.bulk_remove_providers([asset_id], session)
        return results[0]

    @staticmethod
    async def get_asset_provider(
        asset_id: int,
        session: AsyncSession,
        ) -> Optional[AssetProviderAssignment]:
        """
        Fetch provider assignment for asset.

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            AssetProviderAssignment or None if not assigned
        """
        result = await session.execute(
            select(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id == asset_id
                )
            )
        return result.scalar_one_or_none()

    # ========================================================================
    # MANUAL PRICE CRUD METHODS
    # ========================================================================

    @staticmethod
    async def bulk_upsert_prices(
        data: list[dict],
        session: AsyncSession,
        ) -> dict:
        """
        Bulk upsert prices manually (PRIMARY bulk method).

        Args:
            data: List of {asset_id, prices: [{date, open?, high?, low?, close, volume?}, ...]}
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
            asset_id = item["asset_id"]
            prices = item.get("prices", [])

            if not prices:
                results.append({
                    "asset_id": asset_id,
                    "count": 0,
                    "message": "No prices to upsert"
                    })
                continue

            # Get asset currency for prices without explicit currency
            asset_result = await session.execute(
                select(Asset).where(Asset.id == asset_id)
                )
            asset = asset_result.scalar_one_or_none()
            if not asset:
                results.append({
                    "asset_id": asset_id,
                    "count": 0,
                    "message": f"Asset {asset_id} not found"
                    })
                continue

            default_currency = asset.currency

            # Build PriceHistory objects for upsert
            # Strategy: DELETE existing dates + INSERT new (avoids SQLite ON CONFLICT issues)
            price_objects = []
            dates_to_upsert = []

            for price in prices:
                dates_to_upsert.append(price["date"])

                # Normalize numeric inputs to Decimal
                open_v = parse_decimal_value(price.get("open"))
                high_v = parse_decimal_value(price.get("high"))
                low_v = parse_decimal_value(price.get("low"))
                close_v = parse_decimal_value(price.get("close"))
                volume_v = parse_decimal_value(price.get("volume"))

                price_obj = PriceHistory(
                    asset_id=asset_id,
                    date=price["date"],
                    open=truncate_price_to_db_precision(open_v, "open") if open_v is not None else None,
                    high=truncate_price_to_db_precision(high_v, "high") if high_v is not None else None,
                    low=truncate_price_to_db_precision(low_v, "low") if low_v is not None else None,
                    close=truncate_price_to_db_precision(close_v, "close") if close_v is not None else None,
                    volume=volume_v,
                    currency=price.get("currency", default_currency),  # Use asset currency as default
                    source_plugin_key="MANUAL",  # Manual price insert
                    fetched_at=None,  # Not fetched from external source
                    )
                price_objects.append(price_obj)

            # Delete existing prices for these dates (upsert = delete + insert)
            if dates_to_upsert:
                delete_stmt = delete(PriceHistory).where(
                    and_(
                        PriceHistory.asset_id == asset_id,
                        PriceHistory.date.in_(dates_to_upsert)
                        )
                    )
                await session.execute(delete_stmt)

            # Bulk insert new prices
            session.add_all(price_objects)
            await session.commit()

            # Count as inserted
            total_inserted += len(price_objects)

            results.append({
                "asset_id": asset_id,
                "count": len(price_objects),
                "message": f"Upserted {len(price_objects)} prices"
                })

        return {
            "inserted_count": total_inserted,
            "updated_count": 0,  # SQLite doesn't distinguish
            "results": results
            }

    @staticmethod
    async def upsert_prices(
        asset_id: int,
        prices: list[dict],
        session: AsyncSession,
        ) -> dict:
        """
        Upsert prices for single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            prices: List of price dicts
            session: Database session

        Returns:
            Single result dict
        """
        result = await AssetSourceManager.bulk_upsert_prices(
            [{"asset_id": asset_id, "prices": prices}],
            session
            )
        return result["results"][0]

    @staticmethod
    async def bulk_delete_prices(
        data: list[dict],
        session: AsyncSession,
        ) -> dict:
        """
        Bulk delete price ranges (PRIMARY bulk method).

        Args:
            data: List of {asset_id, date_ranges: [{start, end?}, ...]}
                  end is optional (single day if omitted)
            session: Database session

        Returns:
            {deleted_count, results: [{asset_id, deleted, message}, ...]}

        Optimized: 1 DELETE query with complex WHERE
        """
        if not data:
            return {"deleted_count": 0, "results": []}

        # Build complex OR conditions for all ranges
        conditions = []
        for item in data:
            asset_id = item["asset_id"]
            ranges = item.get("date_ranges", [])

            for date_range in ranges:
                start = date_range["start"]
                end = date_range.get("end", start)  # Single day if no end

                conditions.append(
                    and_(
                        PriceHistory.asset_id == asset_id,
                        PriceHistory.date >= start,
                        PriceHistory.date <= end
                        )
                    )

        if not conditions:
            return {"deleted_count": 0, "results": []}

        # Execute single DELETE with OR of all conditions
        stmt = delete(PriceHistory).where(or_(*conditions))
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount

        # Build results per asset (approximate - we don't track per-asset deletes)
        results = [
            {
                "asset_id": item["asset_id"],
                "deleted": deleted_count // len(data),  # Approximate
                "message": f"Deleted prices in {len(item.get('date_ranges', []))} range(s)"
                }
            for item in data
            ]

        return {
            "deleted_count": deleted_count,
            "results": results
            }

    @staticmethod
    async def delete_prices(
        asset_id: int,
        date_ranges: list[dict],
        session: AsyncSession,
        ) -> dict:
        """
        Delete price ranges for single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            date_ranges: List of {start, end?}
            session: Database session

        Returns:
            Single result dict
        """
        result = await AssetSourceManager.bulk_delete_prices(
            [{"asset_id": asset_id, "date_ranges": date_ranges}],
            session
            )
        return result["results"][0]

    # ========================================================================
    # PRICE QUERY WITH BACKWARD-FILL + SYNTHETIC YIELD
    # ========================================================================

    @staticmethod
    async def get_prices(
        asset_id: int,
        start_date: date_type,
        end_date: date_type,
        session: AsyncSession,
        ) -> list[dict]:
        """
        Get prices for asset with backward-fill and synthetic yield support.

        Logic:
        1. Fetch asset to check valuation_model
        2. If SCHEDULED_YIELD: Calculate synthetic values (no DB query for prices)
        3. If other types: Query price_history with backward-fill

        Args:
            asset_id: Asset ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            session: Database session

        Returns:
            List of price dicts with backward_fill_info:
            [{
                date, open, high, low, close, volume, currency,
                backward_fill_info: {actual_rate_date, days_back} or None
            }, ...]

        Raises:
            ValueError: If asset not found or date range invalid
        """
        # Validate date range
        if start_date > end_date:
            raise ValueError(f"Start date {start_date} is after end date {end_date}")

        # Fetch asset
        asset = await session.get(Asset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        # ====================================================================
        # CHECK FOR ASSIGNED PROVIDER FIRST
        # ====================================================================
        assignment = await AssetSourceManager.get_asset_provider(asset_id, session)
        if assignment:
            # Asset has a provider assigned - delegate to provider
            provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
            if provider:
                # Parse provider params
                import json
                provider_params = assignment.provider_params or {}
                if isinstance(provider_params, str):
                    try:
                        provider_params = json.loads(provider_params)
                    except:
                        provider_params = {}

                try:
                    # Get historical data from provider
                    historical_data = await provider.get_history_value(
                        str(asset_id),  # identifier (not used by most providers)
                        provider_params,
                        start_date,
                        end_date
                        )

                    # Convert to expected format
                    results = []
                    for price_point in historical_data.prices:
                        results.append({
                            "date": price_point.date,
                            "open": price_point.open,
                            "high": price_point.high,
                            "low": price_point.low,
                            "close": price_point.close,
                            "volume": price_point.volume,
                            "currency": price_point.currency,
                            "backward_fill_info": None  # Providers return exact data
                            })

                    return results

                except Exception as e:
                    # Provider failed - fall back to DB query
                    pass

        # TODO: capire se questo fallback ha senso farlo o è residuo di una mock precedente
        # ====================================================================
        # FALLBACK: Query price_history with backward-fill
        # ====================================================================

        # Query all available prices in range
        stmt = select(PriceHistory).where(
            and_(
                PriceHistory.asset_id == asset_id,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date
                )
            ).order_by(PriceHistory.date)

        db_result = await session.execute(stmt)
        db_prices = {p.date: p for p in db_result.scalars().all()}

        # Build results with backward-fill
        results = []
        current_date = start_date
        last_known_price = None

        while current_date <= end_date:
            if current_date in db_prices:
                # Exact match
                price = db_prices[current_date]
                last_known_price = price

                results.append({
                    "date": current_date,
                    "open": price.open,
                    "high": price.high,
                    "low": price.low,
                    "close": price.close,
                    "currency": price.currency,
                    "backward_fill_info": None
                    })
            elif last_known_price:
                # Backward-fill
                days_back = (current_date - last_known_price.date).days

                results.append({
                    "date": current_date,
                    "open": last_known_price.open,
                    "high": last_known_price.high,
                    "low": last_known_price.low,
                    "close": last_known_price.close,
                    "currency": last_known_price.currency,
                    "backward_fill_info": {
                        "actual_rate_date": str(last_known_price.date),
                        "days_back": days_back
                        }
                    })
            else:
                # No data available (TODO Step 03: fallback to last BUY transaction)
                # For now, skip this date
                pass

            current_date += timedelta(days=1)

        return results

    # ========================================================================
    # PRICE REFRESH (PROVIDER) METHODS - NEW
    # ========================================================================

    @staticmethod
    async def bulk_refresh_prices(
        requests: list[dict],
        session: AsyncSession,
        concurrency: int = 5,
        semaphore_timeout: int = 60,
        ) -> list[dict]:
        """
        Refresh prices for multiple assets using their configured providers.

        Args:
            requests: List of {asset_id, start_date, end_date, force: bool=false}
            session: Database session
            concurrency: Max concurrent provider calls
            semaphore_timeout: Timeout for acquiring semaphore (seconds)

        Returns:
            List of per-item results: {asset_id, fetched_count, inserted_count, updated_count, errors}
        """
        if not requests:
            return []

        results = []
        sem = asyncio.Semaphore(concurrency)

        async def _process_single(item: dict) -> dict:
            asset_id = item.get("asset_id")
            start = item.get("start_date")
            end = item.get("end_date")
            force = item.get("force", False)

            result = {
                "asset_id": asset_id,
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
                "errors": []
                }

            # Resolve provider assignment
            try:
                assignment = await AssetSourceManager.get_asset_provider(asset_id, session)
                if not assignment:
                    result["errors"].append("No provider assigned for asset")
                    return result

                provider_code = assignment.provider_code
                provider_params = assignment.provider_params or {}
            except Exception as e:
                result["errors"].append(f"Failed to resolve provider: {str(e)}")
                return result

            # Instantiate provider from registry
            prov = AssetProviderRegistry.get_provider_instance(provider_code)
            if not prov:
                result["errors"].append(f"Provider not found: {provider_code}")
                return result

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
                result["errors"].append(f"Invalid provider params: {str(e)}")
                return result

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
                    return await prov.get_history_value(provider_params, start, end, session)
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
                result["errors"].append(str(e))
                return result

            # remote_data expected shape: {"prices": [ {date, open?, high?, low?, close, volume?, currency}, ... ], "source": "..."}
            prices = remote_data.get("prices", []) if isinstance(remote_data, dict) else []
            if not prices:
                result["errors"].append("No prices returned from provider")
                return result

            # Build upsert payload for DB: we reuse bulk_upsert_prices() which performs delete+insert per asset
            upsert_payload = [
                {"asset_id": asset_id, "prices": prices}
                ]

            try:
                upsert_res = await AssetSourceManager.bulk_upsert_prices(upsert_payload, session)
                result["fetched_count"] = len(prices)
                result["inserted_count"] = upsert_res.get("inserted_count", 0)
            except Exception as e:
                result["errors"].append(f"DB upsert failed: {str(e)}")

            # Update last_fetch_at on assignment
            try:
                assignment.last_fetch_at = datetime.utcnow()
                session.add(assignment)
                await session.commit()
            except Exception:
                # Not critical, skip
                pass

            return result

        # Create tasks for all items
        tasks = [asyncio.create_task(_process_single(item)) for item in requests]

        # Wait for all to complete
        completed = await asyncio.gather(*tasks)

        return completed

    @staticmethod
    async def refresh_price(
        asset_id: int,
        start_date: date_type,
        end_date: date_type,
        session: AsyncSession,
        force: bool = False,
        concurrency: int = 5,
        ) -> dict:
        """
        Refresh prices for single asset (calls bulk with 1 element).

        Returns single result dict as produced by bulk_refresh_prices for one item.
        """
        res = await AssetSourceManager.bulk_refresh_prices(
            [{"asset_id": asset_id, "start_date": start_date, "end_date": end_date, "force": force}],
            session,
            concurrency=concurrency,
            )
        return res[0] if res else {"asset_id": asset_id, "fetched_count": 0, "inserted_count": 0, "updated_count": 0, "errors": ["no-op"]}
