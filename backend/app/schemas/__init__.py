"""
Pydantic schemas for LibreFolio.

Used across multiple subsystems (DB, API, Services) to validate data structures
and standardize data exchange between components.

**Organization by Domain**:
- common.py: Shared schemas (BackwardFillInfo, DateRangeModel, OldNew, BaseBulkResponse, BaseDeleteResult)
- assets.py: Asset-related schemas (FAPricePoint, ScheduledInvestment*, etc.)
- provider.py: Provider assignment schemas (FA + FX)
- prices.py: FA price operation schemas (upsert, delete, query)
- refresh.py: FA refresh + FX sync operational schemas
- fx.py: FX-specific schemas (conversion, upsert, delete, pair sources)
- transactions.py: Transaction CRUD schemas (TX prefix)
- brokers.py: Broker CRUD schemas

**Naming Conventions**:
- FA prefix: Financial Assets (stocks, ETFs, bonds, loans)
- FX prefix: Foreign Exchange (currency rates)
- TX prefix: Transactions

**Design Notes**:
- No backward compatibility maintained during v2.1 refactoring
- All models use Pydantic v2 with strict validation
- Schemas separated from API layer (no inline definitions)
- Plan 05b: Removed 16 wrapper classes (now use List[ItemType] directly)
"""

from backend.app.schemas.assets import (
    # Distribution models
    BaseDistribution,
    FAAinfoFiltersRequest,
    # Asset CRUD
    FAAssetCreateItem,
    FAAssetCreateResult,
    FAAssetDeleteResult,
    FAAssetEventPoint,
    FAAssetMetadataResponse,
    FAAssetPatchItem,
    FAAssetPatchResult,
    FAAssetProviderAssignment,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FABulkMetadataRefreshResponse,
    FAClassificationParams,
    FACurrentValue,
    # Metadata & classification
    FAGeographicArea,
    FAHistoricalData,
    FAinfoResponse,
    FAMetadataChangeDetail,
    FAMetadataRefreshResult,
    FASectorArea,
)
from backend.app.schemas.brim import (
    # Constants and helpers
    FAKE_ASSET_ID_BASE,
    # Asset mapping
    BRIMAssetCandidate,
    BRIMAssetMapping,
    BRIMDuplicateLevel,
    # Duplicate detection
    BRIMDuplicateMatch,
    BRIMDuplicateReport,
    # File management
    BRIMFileInfo,
    # Enums
    BRIMFileStatus,
    BRIMMatchConfidence,
    # Parse (import uses POST /transactions)
    BRIMParseRequest,
    BRIMParseResponse,
    BRIMPluginInfo,
    BRIMTXDuplicateCandidate,
    is_fake_asset_id,
)
from backend.app.schemas.brokers import (
    BRAccessBulkItem,
    BRAccessBulkResponse,
    BRAccessItem,
    BRAccessListResponse,
    BRAssetHolding,
    BRBulkCreateResponse,
    BRBulkDeleteResponse,
    BRBulkUpdateResponse,
    BRCreateItem,
    BRCreateResult,
    BRDeleteItem,
    BRDeleteResult,
    BRReadItem,
    BRSummary,
    BRUpdateItem,
    BRUpdateResult,
)
from backend.app.schemas.common import (
    BackwardFillInfo,
    BaseBulkDeleteResponse,
    BaseBulkResponse,
    BaseDeleteResult,
    Currency,
    DateRangeModel,
    OldNew,
)
from backend.app.schemas.fx import (
    FXBulkDeleteResponse,
    FXBulkUpsertResponse,
    FXConversionRequest,
    FXConversionResult,
    FXConversionRouteItem,
    FXConversionRouteResult,
    FXConversionRoutesResponse,
    FXConvertResponse,
    FXCreateRoutesResponse,
    FXDeleteItem,
    FXDeleteResult,
    FXDeleteRouteItem,
    FXDeleteRouteResult,
    FXDeleteRoutesResponse,
    FXProviderInfo,
    FXRouteStep,
    FXUpsertItem,
    validate_chain_steps,
)
from backend.app.schemas.prices import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkUpsertResponse,
    FAPriceDeleteResult,
    FAPricePoint,
    FAUpsert,
    FAUpsertResult,
)
from backend.app.schemas.provider import (
    FABulkAssignResponse,
    FABulkRemoveResponse,
    FAProviderAssignmentItem,
    FAProviderAssignmentReadItem,
    FAProviderAssignmentResult,
    FAProviderInfo,
    FAProviderRefreshFieldsDetail,
    FAProviderRemovalResult,
)
from backend.app.schemas.refresh import (
    CHANGED_POINTS_PAYLOAD_CAP,
    FABulkRefreshResponse,
    FARefreshItem,
    FARefreshResult,
    FXSyncBulkResponse,
    FXSyncPairRequest,
    FXSyncPairResult,
    FXSyncStatus,
    SyncStatus,
)
from backend.app.schemas.transactions import (
    TX_TYPE_METADATA,
    FieldMode,
    PairFieldConstraint,
    PairFieldRelation,
    PairFormLayout,
    PromoteRule,
    # Type aliases
    SignType,
    SplitMeta,
    TXBatchResponse,
    TXBatchResultItem,
    TXCreateItem,
    TXDeleteItem,
    TXDeleteResult,
    TXMixedBatch,
    TXQueryParams,
    TXReadItem,
    TXTypeMetadata,
    TXUpdateItem,
    TXValidationIssue,
    tags_to_csv,
    # Shared utilities
    validate_tags_list,
)

__all__ = [
    # Common (base classes)
    "Currency",
    "BackwardFillInfo",
    "DateRangeModel",
    "OldNew",
    "BaseBulkResponse",
    "BaseDeleteResult",
    "BaseBulkDeleteResponse",
    # Brokers (BR prefix)
    "BRCreateItem",
    "BRReadItem",
    "BRSummary",
    "BRAssetHolding",
    "BRUpdateItem",
    "BRDeleteItem",
    "BRDeleteResult",
    "BRBulkDeleteResponse",
    "BRCreateResult",
    "BRBulkCreateResponse",
    "BRUpdateResult",
    "BRBulkUpdateResponse",
    "BRAccessItem",
    "BRAccessListResponse",
    "BRAccessBulkItem",
    "BRAccessBulkResponse",
    # Transactions (TX prefix)
    "TXCreateItem",
    "TXReadItem",
    "TXUpdateItem",
    "TXDeleteItem",
    "TXQueryParams",
    "TXDeleteResult",
    "TXMixedBatch",
    "TXBatchResultItem",
    "TXBatchResponse",
    "TXValidationIssue",
    "TXTypeMetadata",
    "TX_TYPE_METADATA",
    # Transaction type aliases
    "SignType",
    "FieldMode",
    "PairFormLayout",
    "PairFieldRelation",
    "PairFieldConstraint",
    "SplitMeta",
    "PromoteRule",
    # Transaction utilities
    "validate_tags_list",
    "tags_to_csv",
    # Assets (FA prefix)
    "FACurrentValue",
    "FAPricePoint",
    "FAHistoricalData",
    "FAAssetEventPoint",
    "FAAssetProviderAssignment",
    "FAAssetPatchItem",
    # Assets: Distribution models
    "BaseDistribution",
    # Assets: Metadata & classification
    "FAGeographicArea",
    "FASectorArea",
    "FAClassificationParams",
    "FAAssetMetadataResponse",
    "FAMetadataChangeDetail",
    "FAMetadataRefreshResult",
    "FABulkMetadataRefreshResponse",
    "FABulkAssetPatchResponse",
    "FAAssetPatchResult",
    # Assets: CRUD
    "FAAssetCreateItem",
    "FAAssetCreateResult",
    "FABulkAssetCreateResponse",
    "FAAinfoFiltersRequest",
    "FAinfoResponse",
    "FAAssetDeleteResult",
    "FABulkAssetDeleteResponse",
    # Provider
    "FAProviderInfo",
    "FABulkAssignResponse",
    "FABulkRemoveResponse",
    "FAProviderAssignmentItem",
    "FAProviderAssignmentReadItem",
    "FAProviderAssignmentResult",
    "FAProviderRemovalResult",
    "FAProviderRefreshFieldsDetail",
    # Prices
    "FAUpsert",
    "FAPricePoint",  # Note: FAUpsertItem merged into FAPricePoint
    "FAAssetDelete",
    "FABulkUpsertResponse",
    "FABulkDeleteResponse",
    "FAPriceDeleteResult",
    "FAUpsertResult",
    # Refresh
    "CHANGED_POINTS_PAYLOAD_CAP",
    "FARefreshItem",
    "FABulkRefreshResponse",
    "FARefreshResult",
    "SyncStatus",
    "FXSyncStatus",
    "FXSyncPairRequest",
    "FXSyncPairResult",
    "FXSyncBulkResponse",
    # FX
    "FXProviderInfo",
    "FXConversionRequest",
    "FXConversionResult",
    "FXConvertResponse",
    "FXUpsertItem",
    "FXBulkUpsertResponse",
    "FXDeleteItem",
    "FXDeleteResult",
    "FXBulkDeleteResponse",
    "FXRouteStep",
    "FXConversionRouteItem",
    "FXConversionRoutesResponse",
    "FXConversionRouteResult",
    "FXCreateRoutesResponse",
    "FXDeleteRouteItem",
    "FXDeleteRouteResult",
    "FXDeleteRoutesResponse",
    "validate_chain_steps",
    # BRIM (Broker Report Import Manager)
    "FAKE_ASSET_ID_BASE",
    "is_fake_asset_id",
    "BRIMFileStatus",
    "BRIMMatchConfidence",
    "BRIMDuplicateLevel",
    "BRIMFileInfo",
    "BRIMPluginInfo",
    "BRIMAssetCandidate",
    "BRIMAssetMapping",
    "BRIMDuplicateMatch",
    "BRIMTXDuplicateCandidate",
    "BRIMDuplicateReport",
    "BRIMParseRequest",
    "BRIMParseResponse",
]
