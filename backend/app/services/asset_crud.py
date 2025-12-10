"""
Asset CRUD Service.

Handles Create, Read (List), Update, and Delete operations for assets.
Supports bulk operations with partial success.

TODO (Plan 05b - Step 12): Schema changes to implement
1. Update FAAssetDeleteResult construction:
   - Ensure deleted_count is 0 (failure) or 1 (success) for single asset
   - Populate success field based on deletion outcome
   - Provide meaningful message field
2. Update all bulk response construction:
   - Populate success_count (required by BaseBulkResponse)
   - Count successful operations in results list
   - Ensure errors list is populated for operation-level errors
3. Update FABulkAssetDeleteResponse:
   - Now inherits from BaseBulkDeleteResponse (no changes needed if using base correctly)
"""
import json
from typing import List, Any

import mergedeep
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, AssetType
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    FAAssetCreateResult,
    FAAinfoFiltersRequest,
    FAinfoResponse,
    FABulkAssetDeleteResponse,
    FAAssetDeleteResult,
    FAAssetPatchItem,
    FABulkAssetPatchResponse,
    FAAssetPatchResult, FAClassificationParams,
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
        List assets with optional filters.

        Args:
            filters: Query filters
            session: Database session

        Returns:
            List of assets matching filters
        """
        # Build base query with LEFT JOIN to check provider assignment
        stmt = select(Asset, AssetProviderAssignment.id.label('provider_id')).outerjoin(
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
                currency=asset.currency,
                icon_url=asset.icon_url,
                asset_type=asset.asset_type,
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
                # TODO: trasforma il log in debug una volta testato
                logger.info(f"Asset found for patching: id={patch.asset_id}: {asset.model_dump_json()}")

                # Track updated fields
                updated_fields:List[tuple[str, Any,Any]] = []

                # Update fields if present in patch (use model_dump to detect presence)
                patch_dict = patch.model_dump(mode='json', exclude={'asset_id'}, exclude_unset=True, exclude_none=True)
                for field, value in patch_dict.items():
                    # TODO: trasforma il log in debug una volta testato
                    logger.info(f"Patching field '{field}': '{value}'")
                    if field == "classification_params": # merge new sub-field with old ones
                        # Empty dict = clear all classification_params
                        if not value:  # Empty dict or None
                            value = {}
                        else:
                            value = mergedeep.merge({}, asset_classification_params_before, value)
                        # Set empty strings to None to allow exclusion
                        value = {k: v if v != "" else None for k, v in value.items()}
                        # Store only setted params, delete
                        value = FAClassificationParams(**value).model_dump(mode='json', exclude_none=True)
                    if not value:
                        value = None  # Explicitly set to None if falsey value (e.g., empty string)
                    if isinstance(value, dict):
                        value = json.dumps(value)  # Transform dict as serialized JSON
                    oldVal=getattr(asset, field)
                    setattr(asset, field, value)
                    updated_fields.append((field, oldVal, value))
                    # TODO: trasforma il log in debug una volta testato
                    logger.info(f"updated field '{field}': '{oldVal}' -> '{value}'")

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
