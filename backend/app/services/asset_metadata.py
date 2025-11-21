"""
Asset metadata normalization service.

This module provides services for managing asset classification metadata,
including parsing, serialization, diff computation, and PATCH operations.

Key Features:
- Parse/serialize classification_params JSON ↔ Pydantic models
- Compute metadata diffs for change tracking
- Apply partial updates with PATCH semantics
- Geographic area validation via geo_normalization utilities

Design:
- All methods are static (stateless service)
- Reuses geo_normalization utilities
- Follows PATCH semantics (absent=ignore, null=clear, value=update)
- Geographic area is indivisible block (full replace, no merge)

Usage:
    from backend.app.services.asset_metadata import AssetMetadataService

    # Parse from JSON
    params = AssetMetadataService.parse_classification_params(json_str)

    # Apply PATCH update
    updated = AssetMetadataService.apply_partial_update(current, patch)

    # Compute diff
    changes = AssetMetadataService.compute_metadata_diff(old, new)
"""
import json
from typing import Optional

from backend.app.schemas.assets import (
    FAClassificationParams,
    FAPatchMetadataRequest,
    FAMetadataChangeDetail,
    )


class AssetMetadataService:
    """
    Static service for asset metadata operations.

    All methods are static - no instance state required.
    """

    @staticmethod
    def parse_classification_params(json_str: Optional[str]) -> Optional[FAClassificationParams]:
        """
        Parse classification_params JSON string to Pydantic model.

        Args:
            json_str: JSON string from Asset.classification_params field

        Returns:
            FAClassificationParams if json_str is not None/empty, else None

        Raises:
            ValueError: If JSON is malformed or validation fails

        Examples:
            >>> json_str = '{"investment_type": "stock", "geographic_area": {"USA": 0.6, "ITA": 0.4}}'
            >>> params = AssetMetadataService.parse_classification_params(json_str)
            >>> params.investment_type
            'stock'
            >>> params.geographic_area
            {'USA': Decimal('0.6000'), 'ITA': Decimal('0.4000')}
        """
        if not json_str or json_str.strip() == "":
            return None

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in classification_params: {e}")

        if not isinstance(data, dict):
            raise ValueError(f"classification_params must be a JSON object, got {type(data).__name__}")

        try:
            return FAClassificationParams(**data)
        except Exception as e:
            raise ValueError(f"Validation failed for classification_params: {e}")

    @staticmethod
    def serialize_classification_params(model: Optional[FAClassificationParams]) -> Optional[str]:
        """
        Serialize FAClassificationParams to JSON string for database storage.

        Args:
            model: FAClassificationParams instance or None

        Returns:
            JSON string if model is not None, else None

        Examples:
            >>> from decimal import Decimal
            >>> params = FAClassificationParams(
            ...     investment_type="etf",
            ...     geographic_area={"USA": Decimal("0.5"), "EUR": Decimal("0.5")}
            ... )
            >>> json_str = AssetMetadataService.serialize_classification_params(params)
            >>> json_str
            '{"investment_type":"etf","geographic_area":{"USA":"0.5000","EUR":"0.5000"}}'
        """
        if model is None:
            return None

        # Export model to dict, excluding None values
        data = model.model_dump(exclude_none=True, mode='json')

        # Serialize to JSON
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

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
            >>> old = FAClassificationParams(investment_type="stock")
            >>> new = FAClassificationParams(investment_type="etf", sector="Technology")
            >>> changes = AssetMetadataService.compute_metadata_diff(old, new)
            >>> len(changes)
            2
            >>> changes[0].field
            'investment_type'
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
        patch: FAPatchMetadataRequest
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
            >>> current = FAClassificationParams(investment_type="stock", sector="Technology")
            >>> patch = FAPatchMetadataRequest(sector=None)  # Clear sector
            >>> updated = AssetMetadataService.apply_partial_update(current, patch)
            >>> updated.sector
            None
            >>> updated.investment_type  # Unchanged
            'stock'
        """
        # Start with current values (or empty dict)
        current_dict = current.model_dump(exclude_none=False) if current else {
            'investment_type': None,
            'short_description': None,
            'geographic_area': None,
            'sector': None,
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
            'investment_type': None,
            'short_description': None,
            'geographic_area': None,
            'sector': None,
            }

        # Update with provider data (only non-None values)
        for field in ['investment_type', 'short_description', 'geographic_area', 'sector']:
            if field in provider_data and provider_data[field] is not None:
                current_dict[field] = provider_data[field]

        # Validate and return merged model
        return FAClassificationParams(**current_dict)

    @staticmethod
    async def update_asset_metadata(
        asset_id: int,
        patch: FAPatchMetadataRequest,
        session: 'AsyncSession'
        ) -> 'FAAssetMetadataResponse':
        """
        Update asset metadata with PATCH semantics.

        Loads asset, applies PATCH update, validates, persists to database.

        Args:
            asset_id: Asset ID to update
            patch: PATCH request with fields to update
            session: Database session

        Returns:
            FAAssetMetadataResponse with updated metadata

        Raises:
            ValueError: If asset not found or validation fails

        Examples:
            >>> from backend.app.schemas.assets import FAPatchMetadataRequest
            >>> patch = FAPatchMetadataRequest(sector="Technology")
            >>> response = await AssetMetadataService.update_asset_metadata(1, patch, session)
            >>> response.classification_params.sector
            'Technology'
        """
        from sqlalchemy import select
        from backend.app.db.models import Asset
        from backend.app.schemas.assets import FAAssetMetadataResponse

        # Load asset from DB
        result = await session.execute(
            select(Asset).where(Asset.id == asset_id)
            )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        # Parse current classification_params
        current_params = AssetMetadataService.parse_classification_params(
            asset.classification_params
            )

        # Apply PATCH update
        try:
            updated_params = AssetMetadataService.apply_partial_update(
                current_params,
                patch
                )
        except ValueError as e:
            # Re-raise validation errors (will become 422 in API layer)
            raise ValueError(f"Validation failed: {e}")

        # Serialize back to JSON
        asset.classification_params = AssetMetadataService.serialize_classification_params(
            updated_params
            )

        # Commit transaction
        await session.commit()

        # Refresh to get updated data
        await session.refresh(asset)

        # Build response
        return FAAssetMetadataResponse(
            asset_id=asset.id,
            display_name=asset.display_name,
            identifier=asset.identifier,
            currency=asset.currency,
            classification_params=updated_params
            )
