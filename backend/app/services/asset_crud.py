"""
Asset CRUD Service.

Handles Create, Read (List), Update, and Delete operations for assets.
Supports bulk operations with partial success.
"""
from typing import List

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    FAAssetCreateResult,
    FAAinfoFiltersRequest,
    FAinfoResponse,
    FABulkAssetDeleteResponse,
    FAAssetDeleteResult,
    )

logger = get_logger(__name__)


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
        results = []

        for item in assets:
            try:
                # Check if identifier already exists
                stmt = select(Asset).where(Asset.identifier == item.identifier)
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    results.append(FAAssetCreateResult(
                        asset_id=None,
                        success=False,
                        message=f"Asset with identifier '{item.identifier}' already exists",
                        display_name=item.display_name,
                        identifier=item.identifier
                        ))
                    continue

                # Create asset record
                asset = Asset(
                    display_name=item.display_name,
                    identifier=item.identifier,
                    identifier_type=item.identifier_type,
                    currency=item.currency,
                    asset_type=item.asset_type,
                    valuation_model=item.valuation_model,
                    interest_schedule=item.interest_schedule.model_dump_json(exclude_none=True) if item.interest_schedule else None,
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
                    display_name=item.display_name,
                    identifier=item.identifier
                    ))

                logger.info(f"Asset created: id={asset.id}, identifier={item.identifier}")

            except Exception as e:
                logger.error(f"Error creating asset {item.identifier}: {e}")
                results.append(FAAssetCreateResult(
                    asset_id=None,
                    success=False,
                    message=f"Error: {str(e)}",
                    display_name=item.display_name,
                    identifier=item.identifier
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
            failed_count=len(results) - success_count
            )

    @staticmethod
    async def list_assets(
        filters: FAAinfoFiltersRequest,
        session: AsyncSession
        ) -> List[FAinfoResponse]:
        """
        List assets with optional filters.

        Args:
            filters: Query filters
            session: Database session

        Returns:
            List of assets matching filters
        """
        # Build base query with LEFT JOIN to check provider assignment
        stmt = select(
            Asset,
            AssetProviderAssignment.id.label('provider_id')
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

        if filters.valuation_model:
            conditions.append(Asset.valuation_model == filters.valuation_model)

        conditions.append(Asset.active == filters.active)

        if filters.search:
            search_pattern = f"%{filters.search}%"
            conditions.append(
                or_(
                    Asset.display_name.ilike(search_pattern),
                    Asset.identifier.ilike(search_pattern)
                    )
                )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Order by display_name
        stmt = stmt.order_by(Asset.display_name.asc())

        # Execute query
        result = await session.execute(stmt)
        rows = result.all()

        # Build response
        assets = []
        for row in rows:
            asset = row[0]  # Asset object
            provider_id = row[1]  # provider_id from join

            assets.append(FAinfoResponse(
                id=asset.id,
                display_name=asset.display_name,
                identifier=asset.identifier,
                identifier_type=asset.identifier_type,
                currency=asset.currency,
                asset_type=asset.asset_type,
                valuation_model=asset.valuation_model,
                active=asset.active,
                has_provider=provider_id is not None,
                has_metadata=asset.classification_params is not None
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
            failed_count=len(results) - success_count
            )
