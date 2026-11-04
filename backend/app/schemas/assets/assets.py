"""
Financial Asset (FA) schemas: the asset and its CRUD.

``schemas/assets/`` has one module per theme (C3): this one, ``metadata.py`` (classification and metadata),
``scheduled_investment.py`` (the interest schedule of scheduled investments) and ``events.py`` (asset events). Price
schemas are in ``backend/app/schemas/prices.py``.

- ``FAAssetProviderAssignment``: the asset-to-provider mapping.
- Create: ``FAAssetCreateItem``, ``FAAssetCreateResult``, ``FABulkAssetCreateResponse``.
- Read: ``FAAinfoFiltersRequest``, ``FAinfoResponse``.
- Delete: ``FAAssetDeleteResult``, ``FABulkAssetDeleteResponse``.
- Patch (``PATCH /assets``): ``FAAssetPatchItem``, ``FAAssetPatchResult``, ``FABulkAssetPatchResponse``.
- Merge: ``FAAssetMergeRequest``, ``FAAssetMergePreview``, ``FAAssetMergeResponse``.

**Naming Conventions**:
- FA domain: Financial Assets (stocks, ETFs, bonds, P2P loans, etc.)

**Design Notes**:
- All numeric fields use Decimal for precision
- Pydantic v2 with strict validation (extra="forbid")
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from backend.app.db.models import AssetType, IdentifierType
from backend.app.schemas.assets.metadata import FAClassificationParams
from backend.app.schemas.common import (
    BaseBulkResponse,
    BaseDeleteResult,
    Currency,
    OldNew,
    StrictModel,
    iso_currency_code,
)
from backend.app.utils.asset.identifier import normalize_other_identifiers


# ============================================================================
# PROVIDER ASSIGNMENT
# ============================================================================
class FAAssetProviderAssignment(StrictModel):
    asset_id: int
    provider_code: str
    provider_params: Optional[dict] = None
    last_fetch_at: Optional[str] = None


# ============================================================================
# ASSET CRUD SCHEMAS
# ============================================================================


class FAAssetCreateItem(StrictModel):
    """Single asset to create in bulk operation.

    Identifier fields (identifier_isin, identifier_ticker, etc.) are stored directly on Asset.
    Provider assignment can be done separately via POST /assets/provider.
    """

    display_name: str = Field(..., description="Human-readable asset name (must be unique)")
    currency: str = Field(..., min_length=3, max_length=3, description="Asset currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Asset type (STOCK, ETF, BOND, CROWDFUND, etc.)")
    icon_url: Optional[str] = Field(None, description="URL to asset icon (local or remote)")
    quote_base_quantity: Optional[int] = Field(1, description="How many units the raw market quote refers to")
    active: bool = Field(True, description="Whether asset is active")
    is_benchmark: bool = Field(False, description="Offer this asset as a comparison benchmark in risk and chart selectors")
    user_url: Optional[str] = Field(None, description="User-defined URL (notes, external dashboard, etc.)")

    # Classification metadata (optional)
    classification_params: Optional[FAClassificationParams] = Field(None, description="Asset classification metadata")

    # Identifier fields (one per IdentifierType) - optional
    identifier_isin: Optional[str] = Field(None, max_length=12, description="ISIN code (12 chars)")
    identifier_ticker: Optional[str] = Field(None, max_length=20, description="Ticker symbol")
    identifier_cusip: Optional[str] = Field(None, max_length=9, description="CUSIP code (9 chars)")
    identifier_sedol: Optional[str] = Field(None, max_length=7, description="SEDOL code (7 chars)")
    identifier_figi: Optional[str] = Field(None, max_length=12, description="FIGI code (12 chars)")
    identifier_uuid: Optional[str] = Field(None, max_length=36, description="UUID for custom assets")
    identifier_other: Optional[List[str]] = Field(None, description="JSON list of other/soft identifiers (additive across imports)")

    @field_validator("identifier_other", mode="before")
    @classmethod
    def normalize_identifier_other(cls, v) -> Optional[List[str]]:
        return normalize_other_identifiers(v)

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        """An ISO 4217 alphabetic code, upper-case: never a name or a number (E-18)."""
        return iso_currency_code(v)

    @field_validator("quote_base_quantity", mode="before")
    @classmethod
    def normalize_quote_base_quantity(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return 1
        return 1 if int(v) <= 0 else int(v)

    @field_validator("identifier_isin")
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator("identifier_ticker")
    @classmethod
    def validate_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == "":
            return None
        return v.strip().upper()


class FAAssetCreateResult(StrictModel):
    """Result of single asset creation in bulk operation."""

    asset_id: Optional[int] = Field(None, description="Created asset ID (null if failed)")
    success: bool = Field(..., description="Whether creation succeeded")
    message: str = Field(..., description="Success message or error description")
    display_name: str = Field(..., description="Asset display name (for identification)")


class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
    """Bulk asset creation response (partial success allowed)."""

    # Inherits from BaseBulkResponse:
    # - results: List[FAAssetCreateResult]
    # - success_count: int
    # - errors: List[str]
    # Computed properties:
    # - total_count: int


class FAAinfoFiltersRequest(StrictModel):
    """Filters for asset list query - enhanced for BRIM asset matching.

    Supports exact match on all identifier columns (one per IdentifierType):
    - isin, ticker, cusip, sedol, figi, uuid: exact match
    - identifier_other: partial match (LIKE)
    - identifier_contains: partial match across ALL identifier columns
    """

    # Filters with proper validation
    currency: Optional[str] = Field(None, description="Filter by currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Filter by asset type enum")
    active: Optional[bool] = Field(None, description="Tri-state filter: True = only active, False = only inactive, None (default) = no filter (return both)")
    is_benchmark: Optional[bool] = Field(None, description="Tri-state filter: True = only benchmarks, False = only non-benchmarks, None (default) = no filter")

    # Search in display_name (partial match)
    search: Optional[str] = Field(None, description="Search in display_name (partial match)")

    # Identifier-based exact search (one per IdentifierType)
    isin: Optional[str] = Field(None, description="Exact ISIN match (Asset.identifier_isin)")
    ticker: Optional[str] = Field(None, description="Exact ticker/symbol match (Asset.identifier_ticker)")
    cusip: Optional[str] = Field(None, description="Exact CUSIP match (Asset.identifier_cusip)")
    sedol: Optional[str] = Field(None, description="Exact SEDOL match (Asset.identifier_sedol)")
    figi: Optional[str] = Field(None, description="Exact FIGI match (Asset.identifier_figi)")
    uuid: Optional[str] = Field(None, description="Exact UUID match (Asset.identifier_uuid)")

    # identifier_other uses partial match (LIKE) since it can contain anything
    identifier_other: Optional[str] = Field(None, description="Partial match in identifier_other")

    # Partial match across ALL identifier columns
    identifier_contains: Optional[str] = Field(None, description="Partial match in any identifier field")

    @field_validator("currency")
    @classmethod
    def validate_currency_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate currency using Currency.validate_code()."""
        if v is None:
            return None
        return Currency.validate_code(v)

    @field_validator("isin")
    @classmethod
    def validate_isin_format(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ISIN to uppercase."""
        if v is None:
            return None
        return v.strip().upper()

    @field_validator("ticker", "cusip", "sedol", "figi")
    @classmethod
    def validate_identifier_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """Normalize identifier to uppercase."""
        if v is None:
            return None
        return v.strip().upper()


class FAinfoResponse(StrictModel):
    """Single asset info - enhanced with identifier data for BRIM and frontend."""

    id: int = Field(..., description="Asset ID")
    display_name: str = Field(..., description="Asset display name")
    currency: str = Field(..., description="Asset currency")
    icon_url: Optional[str] = Field(None, description="Asset icon URL")
    asset_type: Optional[str] = Field(None, description="Asset type")
    quote_base_quantity: Optional[int] = Field(1, description="How many units the raw market quote refers to")
    active: bool = Field(..., description="Whether asset is active")
    is_benchmark: bool = Field(False, description="Asset is offered as a comparison benchmark")
    user_url: Optional[str] = Field(None, description="User-defined URL (notes, external dashboard, etc.)")
    provider_code: Optional[str] = Field(None, description="Provider code if assigned (e.g. 'yfinance')")
    has_metadata: bool = Field(..., description="Whether asset has classification metadata")

    # Usage counters (F15) — drive the "your assets / other users' assets / under
    # analysis" panels on the global assets page. `tx_count_own` counts only
    # transactions in brokers the current user OWNs with a positive share.
    tx_count: int = Field(0, description="Total transactions referencing this asset (any broker)")
    tx_count_own: int = Field(0, description="Transactions in brokers the current user owns (share > 0)")
    # Positions open now (quantity > 0), which a transaction count cannot tell: an asset sold in
    # full still has transactions. "My assets" means held now, not traded once.
    held_by_me: bool = Field(False, description="A positive quantity is held now in a broker the current user owns (share > 0)")
    held_by_others: bool = Field(False, description="A positive quantity is held now in a broker the current user does not own")

    # Identifier columns (one per IdentifierType)
    identifier_isin: Optional[str] = Field(None, description="ISIN code")
    identifier_ticker: Optional[str] = Field(None, description="Ticker symbol")
    identifier_cusip: Optional[str] = Field(None, description="CUSIP code")
    identifier_sedol: Optional[str] = Field(None, description="SEDOL code")
    identifier_figi: Optional[str] = Field(None, description="FIGI code")
    identifier_uuid: Optional[str] = Field(None, description="UUID for custom assets")
    identifier_other: Optional[List[str]] = Field(None, description="JSON list of other/soft identifiers")

    # Legacy fields for backward compatibility with provider assignment
    identifier: Optional[str] = Field(None, description="Primary identifier (from provider assignment)")
    identifier_type: Optional[IdentifierType] = Field(None, description="Primary identifier type")

    @field_validator("identifier_other", mode="before")
    @classmethod
    def normalize_identifier_other(cls, v) -> Optional[List[str]]:
        return normalize_other_identifiers(v)


class FAAssetDeleteResult(BaseDeleteResult):
    """Result of single asset deletion in bulk operation."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    display_name: Optional[str] = Field(None, description="Asset display name (for UI feedback)")
    error_code: Optional[str] = Field(None, description="Structured error code: 'HAS_TRANSACTIONS' | 'NOT_FOUND' | None")
    transaction_count: Optional[int] = Field(None, ge=0, description="Global transaction count when deletion is blocked")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (always 0 or 1 for single asset)
    # - message: Optional[str]


class FABulkAssetDeleteResponse(BaseBulkResponse[FAAssetDeleteResult]):
    """Bulk asset deletion response (partial success allowed)."""


# ============================================================================
# ASSET PATCH SCHEMAS (for PATCH /assets endpoint)
# ============================================================================


class FAAssetPatchItem(StrictModel):
    """Single asset patch item for bulk update operations.

    Merge logic:
    - Field present in patch (even if None): UPDATE or BLANK
    - Field absent in patch: IGNORE (keep existing value)

    For classification_params:
    - If None or an empty object: Set DB column to NULL
    - Otherwise: Replace provided fields atomically, preserve omitted fields
    - Explicit null subfields remove only that classification block
    """

    asset_id: int = Field(..., description="Asset ID to update")

    # Optional fields - if present (even if None), they will be updated
    display_name: Optional[str] = Field(None, description="Update display name")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Update currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Update asset type (STOCK, ETF, BOND, etc.)")
    icon_url: Optional[str] = Field(None, description="Update icon URL (None = clear)")
    quote_base_quantity: Optional[int] = Field(None, description="Update quote base quantity")
    classification_params: Optional[FAClassificationParams] = Field(None, description="Update classification (None = clear)")
    active: Optional[bool] = Field(None, description="Update active status")
    is_benchmark: Optional[bool] = Field(None, description="Update benchmark availability")
    user_url: Optional[str] = Field(None, description="Update user-defined URL (None = clear)")

    # Identifier fields (one per IdentifierType)
    identifier_isin: Optional[str] = Field(None, max_length=12, description="Update ISIN code")
    identifier_ticker: Optional[str] = Field(None, max_length=20, description="Update ticker symbol")
    identifier_cusip: Optional[str] = Field(None, max_length=9, description="Update CUSIP code")
    identifier_sedol: Optional[str] = Field(None, max_length=7, description="Update SEDOL code")
    identifier_figi: Optional[str] = Field(None, max_length=12, description="Update FIGI code")
    identifier_uuid: Optional[str] = Field(None, max_length=36, description="Update UUID")
    identifier_other: Optional[List[str]] = Field(None, description="Update other/soft identifiers (JSON list; None = leave unchanged)")

    @field_validator("identifier_other", mode="before")
    @classmethod
    def normalize_identifier_other(cls, v) -> Optional[List[str]]:
        return normalize_other_identifiers(v)

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """An ISO 4217 alphabetic code, upper-case: never a name or a number (E-18)."""
        return iso_currency_code(v) if v else None

    @field_validator("quote_base_quantity", mode="before")
    @classmethod
    def normalize_quote_base_quantity(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        return 1 if int(v) <= 0 else int(v)

    @field_validator("identifier_isin")
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator("identifier_ticker")
    @classmethod
    def validate_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == "":
            return None
        return v.strip().upper()


class FAAssetPatchResult(StrictModel):
    """Result of single asset patch in bulk operation."""

    asset_id: int = Field(..., description="Asset ID")
    success: bool = Field(..., description="Whether patch succeeded")
    message: str = Field(..., description="Success message or error description")
    updated_fields: Optional[List[OldNew[str | None]]] = Field(None, description="List of fields updated: [{info: field, old: old_value, new: new_value}]")


class FABulkAssetPatchResponse(BaseBulkResponse[FAAssetPatchResult]):
    """Bulk asset patch response (partial success allowed)."""


# ============================================================================
# ASSET MERGE SCHEMAS (P3/A-02)
# ============================================================================


class FAAssetMergeRequest(StrictModel):
    """Request body for ``POST /assets/merge``.

    Folds ``source_asset_id`` into ``target_asset_id`` and deletes the source.
    The target is always the asset the user wants to keep — the endpoint never
    picks for them.
    """

    source_asset_id: int = Field(..., description="Asset to fold in and delete")
    target_asset_id: int = Field(..., description="Asset to keep")
    identifier_primaries: Optional[Dict[str, str]] = Field(
        None,
        description="Optional per-column decision on which value stays primary, e.g. identifier_isin -> IT0005634800. Whatever loses is demoted into identifier_other rather than dropped. Values not belonging to either asset are rejected.",
    )
    dry_run: bool = Field(False, description="Compute and return the plan without writing anything")


class FAAssetMergePreview(StrictModel):
    """What a merge would move, so the user can confirm before anything is destroyed."""

    transactions: int = Field(0, description="Transactions that will be reassigned to the target")
    prices: int = Field(0, description="Price rows that will be reassigned")
    prices_discarded: int = Field(0, description="Source price rows dropped because the target already has that date")
    events: int = Field(0, description="Asset events that will be reassigned")
    events_discarded: int = Field(0, description="Source events dropped as duplicates of a target event")
    transactions_relinked: int = Field(0, description="Transactions whose asset_event_id was remapped onto the surviving event")
    provider_assignment_moved: bool = Field(False, description="Whether the source provider assignment was moved to the target")
    provider_assignment_dropped: bool = Field(False, description="Whether the source provider assignment was dropped (target already had one)")
    identifiers_added: List[str] = Field(default_factory=list, description="Values added to the target's identifier_other")


class FAAssetMergeResponse(StrictModel):
    """Outcome of an asset merge."""

    success: bool = Field(..., description="Whether the merge completed")
    source_asset_id: int = Field(..., description="Asset folded in (deleted unless dry_run)")
    target_asset_id: int = Field(..., description="Surviving asset")
    dry_run: bool = Field(False, description="True when nothing was written")
    preview: FAAssetMergePreview = Field(..., description="What was moved (or would be moved)")
    message: str = Field("", description="Human-readable outcome")
