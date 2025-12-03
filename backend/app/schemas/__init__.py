"""
Pydantic schemas for LibreFolio.

Used across multiple subsystems (DB, API, Services) to validate data structures
and standardize data exchange between components.

**Organization by Domain**:
- common.py: Shared schemas (BackwardFillInfo, DateRangeModel)
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
"""
from backend.app.schemas.assets import (
    FACurrentValue,
    FAPricePoint,
    FAHistoricalData,
    FAAssetProviderAssignment,
    # Metadata & classification
    FAGeographicArea,
    FAClassificationParams,
    FAClassificationParams,
    FAAssetMetadataResponse,
    FAMetadataChangeDetail,
    FAMetadataRefreshResult,
    FABulkMetadataRefreshResponse,
    FAPatchMetadataItem,
    FABulkPatchMetadataRequest,
    # Asset CRUD (NEW)
    FAAssetCreateItem,
    FABulkAssetCreateRequest,
    FAAssetCreateResult,
    FABulkAssetCreateResponse,
    FAAinfoFiltersRequest,
    FAinfoResponse,
    FABulkAssetDeleteRequest,
    FAAssetDeleteResult,
    FABulkAssetDeleteResponse,
    )
from backend.app.schemas.common import (
    BackwardFillInfo,
    DateRangeModel,
    )
from backend.app.schemas.fx import (
    FXProviderInfo,
    FXConvertRequest,
    FXConvertResponse,
    FXBulkUpsertRequest,
    FXBulkUpsertResponse,
    FXBulkDeleteRequest,
    FXBulkDeleteResponse,
    FXPairSourcesResponse,
    FXCreatePairSourcesRequest,
    FXDeletePairSourceItem,
    FXDeletePairSourcesRequest,
    FXDeletePairSourcesResponse,
    )
from backend.app.schemas.prices import (
    FAUpsert,
    FAUpsertItem,
    FAAssetDelete,
    FABulkUpsertRequest,
    FABulkUpsertResponse,
    FAPriceBulkDeleteRequest,
    FABulkDeleteResponse,
    FAPriceDeleteResult,
    )
from backend.app.schemas.provider import (
    FAProviderInfo,
    FABulkAssignRequest,
    FABulkAssignResponse,
    FABulkRemoveRequest,
    FABulkRemoveResponse,
    FAProviderAssignmentItem,
    FAProviderAssignmentResult,
    FAProviderRemovalResult,
    )
from backend.app.schemas.refresh import (
    FARefreshItem,
    FABulkRefreshRequest,
    FABulkRefreshResponse,
    FARefreshResult,
    FXSyncResponse,
    )

__all__ = [
    # Common
    "BackwardFillInfo",
    "DateRangeModel",
    # Assets
    "FACurrentValue",
    "FAPricePoint",
    "FAHistoricalData",
    "FAAssetProviderAssignment",
    # Assets: Metadata & classification
    "FAGeographicArea",
    "FAClassificationParams",
    "FAClassificationParams",
    "FAAssetMetadataResponse",
    "FAMetadataChangeDetail",
    "FAMetadataRefreshResult",
    "FABulkMetadataRefreshResponse",
    "FAPatchMetadataItem",
    "FABulkPatchMetadataRequest",
    # Assets: CRUD
    "FAAssetCreateItem",
    "FABulkAssetCreateRequest",
    "FAAssetCreateResult",
    "FABulkAssetCreateResponse",
    "FAAinfoFiltersRequest",
    "FAinfoResponse",
    "FABulkAssetDeleteRequest",
    "FAAssetDelete",
    "FAAssetDeleteResult",
    "FABulkAssetDeleteResponse",
    # Provider
    "FAProviderInfo",
    "FABulkAssignRequest",
    "FABulkAssignResponse",
    "FABulkRemoveRequest",
    "FABulkRemoveResponse",
    "FAProviderAssignmentItem",
    "FAProviderAssignmentResult",
    "FAProviderRemovalResult",
    # Prices
    "FAUpsert",
    "FAUpsertItem",
    "FABulkUpsertRequest",
    "FABulkUpsertResponse",
    "FAPriceBulkDeleteRequest",
    "FABulkDeleteResponse",
    "FAPriceDeleteResult",
    # Refresh
    "FARefreshItem",
    "FABulkRefreshRequest",
    "FABulkRefreshResponse",
    "FARefreshResult",
    "FXSyncResponse",
    # FX
    "FXProviderInfo",
    "FXConvertRequest",
    "FXConvertResponse",
    "FXBulkUpsertRequest",
    "FXBulkUpsertResponse",
    "FXBulkDeleteRequest",
    "FXBulkDeleteResponse",
    "FXPairSourcesResponse",
    "FXCreatePairSourcesRequest",
    "FXDeletePairSourceItem",
    "FXDeletePairSourcesRequest",
    "FXDeletePairSourcesResponse",
    ]
