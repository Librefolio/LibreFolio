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

**Naming Conventions**:
- FA prefix: Financial Assets (stocks, ETFs, bonds, loans)
- FX prefix: Foreign Exchange (currency rates)

**Design Notes**:
- No backward compatibility maintained during v2.1 refactoring
- All models use Pydantic v2 with strict validation
- Schemas separated from API layer (no inline definitions)
- Plan 05b: Removed 16 wrapper classes (now use List[ItemType] directly)
"""
from backend.app.schemas.assets import (
    FACurrentValue,
    FAPricePoint,
    FAHistoricalData,
    FAAssetProviderAssignment,
    FAAssetPatchItem,
    # Distribution models
    BaseDistribution,
    # Metadata & classification
    FAGeographicArea,
    FASectorArea,
    FAClassificationParams,
    FAAssetMetadataResponse,
    FAMetadataChangeDetail,
    FAMetadataRefreshResult,
    FABulkMetadataRefreshResponse,
    FABulkAssetPatchResponse,
    FAAssetPatchResult,
    # Asset CRUD
    FAAssetCreateItem,
    FAAssetCreateResult,
    FABulkAssetCreateResponse,
    FAAinfoFiltersRequest,
    FAinfoResponse,
    FAAssetDeleteResult,
    FABulkAssetDeleteResponse,
    )
from backend.app.schemas.common import (
    BackwardFillInfo,
    DateRangeModel,
    OldNew,
    BaseBulkResponse,
    BaseDeleteResult,
    BaseBulkDeleteResponse,
    )
from backend.app.schemas.fx import (
    FXProviderInfo,
    FXConversionRequest,
    FXConversionResult,
    FXConvertResponse,
    FXUpsertItem,
    FXBulkUpsertResponse,
    FXDeleteItem,
    FXDeleteResult,
    FXBulkDeleteResponse,
    FXPairSourceItem,
    FXPairSourcesResponse,
    FXPairSourceResult,
    FXCreatePairSourcesResponse,
    FXDeletePairSourceItem,
    FXDeletePairSourceResult,
    FXDeletePairSourcesResponse,
    FXCurrenciesResponse,
    )
from backend.app.schemas.prices import (
    FAUpsert,
    FAPricePoint,
    FAAssetDelete,
    FABulkUpsertResponse,
    FABulkDeleteResponse,
    FAPriceDeleteResult,
    FAUpsertResult,
    )
from backend.app.schemas.provider import (
    FAProviderInfo,
    FABulkAssignResponse,
    FABulkRemoveResponse,
    FAProviderAssignmentItem,
    FAProviderAssignmentReadItem,
    FAProviderAssignmentResult,
    FAProviderRemovalResult,
    FAProviderRefreshFieldsDetail,
    )
from backend.app.schemas.refresh import (
    FARefreshItem,
    FABulkRefreshResponse,
    FARefreshResult,
    FXSyncResponse,
    )

__all__ = [
    # Common (base classes)
    "BackwardFillInfo",
    "DateRangeModel",
    "OldNew",
    "BaseBulkResponse",
    "BaseDeleteResult",
    "BaseBulkDeleteResponse",
    # Assets
    "FACurrentValue",
    "FAPricePoint",
    "FAHistoricalData",
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
    "FARefreshItem",
    "FABulkRefreshResponse",
    "FARefreshResult",
    "FXSyncResponse",
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
    "FXPairSourceItem",
    "FXPairSourcesResponse",
    "FXPairSourceResult",
    "FXCreatePairSourcesResponse",
    "FXDeletePairSourceItem",
    "FXDeletePairSourceResult",
    "FXDeletePairSourcesResponse",
    "FXCurrenciesResponse",
    ]
