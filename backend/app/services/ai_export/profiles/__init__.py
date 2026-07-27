"""Frozen AI Export task specs, detail overlays, and technical bundles."""

from backend.app.services.ai_export.profiles.asset import (
    ASSET_BUNDLES,
    ASSET_COMPACT_BUNDLE,
    ASSET_FULL_BUNDLE,
    ASSET_STANDARD_BUNDLE,
    ASSET_TASK_SPECS,
)
from backend.app.services.ai_export.profiles.base import (
    COMPACT_OVERLAY,
    DETAIL_OVERLAYS,
    FULL_OVERLAY,
    STANDARD_OVERLAY,
)
from backend.app.services.ai_export.profiles.broker import BROKER_TASK_SPECS
from backend.app.services.ai_export.profiles.fx import FX_BUNDLES, FX_COMPACT_BUNDLE, FX_FULL_BUNDLE, FX_STANDARD_BUNDLE, FX_TASK_SPECS
from backend.app.services.ai_export.profiles.portfolio import PORTFOLIO_TASK_SPECS

TASK_SPECS = (
    *PORTFOLIO_TASK_SPECS,
    *ASSET_TASK_SPECS,
    *FX_TASK_SPECS,
    *BROKER_TASK_SPECS,
)

__all__ = [
    "ASSET_BUNDLES",
    "ASSET_COMPACT_BUNDLE",
    "ASSET_FULL_BUNDLE",
    "ASSET_STANDARD_BUNDLE",
    "ASSET_TASK_SPECS",
    "BROKER_TASK_SPECS",
    "COMPACT_OVERLAY",
    "DETAIL_OVERLAYS",
    "FULL_OVERLAY",
    "FX_BUNDLES",
    "FX_COMPACT_BUNDLE",
    "FX_FULL_BUNDLE",
    "FX_STANDARD_BUNDLE",
    "FX_TASK_SPECS",
    "PORTFOLIO_TASK_SPECS",
    "STANDARD_OVERLAY",
    "TASK_SPECS",
]
