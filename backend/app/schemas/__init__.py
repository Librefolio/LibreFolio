"""
Pydantic schemas for LibreFolio.
Used across multiple subsystems, DB, API, ...
Their scope is validate data structures exchanged between components and standardize data sharing.

Organized by domain:
- common.py: Shared schemas (BackwardFillInfo, etc.)
- fx.py: FX-related schemas
- assets.py: Asset-related schemas
"""
from backend.app.schemas.assets import (
    CurrentValueModel,
    PricePointModel,
    HistoricalDataModel,
    AssetProviderAssignmentModel,
    )
from backend.app.schemas.common import BackwardFillInfo

__all__ = [
    "BackwardFillInfo",
    "CurrentValueModel",
    "PricePointModel",
    "HistoricalDataModel",
    "AssetProviderAssignmentModel",
    ]
