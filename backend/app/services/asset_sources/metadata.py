"""Provider metadata refresh operations."""

from __future__ import annotations

import json

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
)
from backend.app.schemas import (
    FABulkMetadataRefreshResponse,
    FAMetadataRefreshResult,
)
from backend.app.schemas.assets import (
    FAAssetPatchItem,
)
from backend.app.schemas.common import (
    OldNew,
)
from backend.app.schemas.provider import (
    FAProviderRefreshFieldsDetail,
)
from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.core import (
    AssetSourceProvider,
)
from backend.app.services.asset_sources.crud import AssetCRUDService
from backend.app.services.provider_registry import AssetProviderRegistry

logger = structlog.get_logger(__name__)


class MetadataOperations:
    """Provider metadata refresh operations."""

    @staticmethod
    async def refresh_assets_from_provider(asset_ids: list[int], session: AsyncSession) -> FABulkMetadataRefreshResponse:  # noqa: C901 — per-asset guard chain with early continues
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
                    cached_meta, meta_ok = core._asset_metadata_cache.get(meta_cache_key)
                    if meta_ok:
                        patch_item = cached_meta
                        logger.debug(f"Metadata cache HIT for asset {asset_id}")
                    else:
                        _id = assignment.identifier
                        _id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)
                        _params = provider_params
                        patch_item = await core._run_provider_in_thread(
                            lambda _p=provider, _i=_id, _it=_id_type, _pr=_params: _p.fetch_asset_metadata(_i, _it, _pr),
                            timeout=30.0,
                        )
                        core._asset_metadata_cache.set(meta_cache_key, patch_item)
                except Exception as e:
                    results.append(
                        FAMetadataRefreshResult(
                            asset_id=asset_id,
                            success=False,
                            message=f"Failed to fetch metadata: {e!s}",
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
                logger.exception(f"Error preparing refresh for asset {asset_id}: {e}")
                results.append(FAMetadataRefreshResult(asset_id=asset_id, success=False, message=f"Error: {e!s}"))

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
