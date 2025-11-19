"""
Pydantic schemas for LibreFolio.

Used across multiple subsystems (DB, API, Services) to validate data structures
and standardize data exchange between components.

**Organization by Domain**:
- common.py: Shared schemas (BackwardFillInfo, DateRangeModel)
- assets.py: Asset-related schemas (PricePointModel, ScheduledInvestment*, etc.)
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
    CurrentValueModel,
    PricePointModel,
    HistoricalDataModel,
    AssetProviderAssignmentModel,
    # Metadata & classification (NEW)
    ClassificationParamsModel,
    PatchAssetMetadataRequest,
    AssetMetadataResponse,
    MetadataChangeDetail,
    MetadataRefreshResult,
    BulkAssetReadRequest,
    BulkMetadataRefreshRequest,
    BulkMetadataRefreshResponse,
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
    )
from backend.app.schemas.prices import (
    FAUpsertItem,
    FABulkUpsertRequest,
    FABulkUpsertResponse,
    FABulkDeleteRequest,
    FABulkDeleteResponse,
    )
from backend.app.schemas.provider import (
    FAProviderInfo,
    FABulkAssignRequest,
    FABulkAssignResponse,
    FABulkRemoveRequest,
    FABulkRemoveResponse,
    )
from backend.app.schemas.refresh import (
    FABulkRefreshRequest,
    FABulkRefreshResponse,
    FXSyncResponse,
    )

__all__ = [
    # Common
    "BackwardFillInfo",
    "DateRangeModel",
    # Assets
    "CurrentValueModel",
    "PricePointModel",
    "HistoricalDataModel",
    "AssetProviderAssignmentModel",
    # Assets: Metadata & classification
    "ClassificationParamsModel",
    "PatchAssetMetadataRequest",
    "AssetMetadataResponse",
    "MetadataChangeDetail",
    "MetadataRefreshResult",
    "BulkAssetReadRequest",
    "BulkMetadataRefreshRequest",
    "BulkMetadataRefreshResponse",
    # Provider
    "FAProviderInfo",
    "FABulkAssignRequest",
    "FABulkAssignResponse",
    "FABulkRemoveRequest",
    "FABulkRemoveResponse",
    # Prices
    "FAUpsertItem",
    "FABulkUpsertRequest",
    "FABulkUpsertResponse",
    "FABulkDeleteRequest",
    "FABulkDeleteResponse",
    # Refresh
    "FABulkRefreshRequest",
    "FABulkRefreshResponse",
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
]
