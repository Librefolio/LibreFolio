"""
Analytics schemas for LibreFolio.

Schemas for the /api/v1/analytics/ endpoints:
- WAC time series (point-per-transaction where WAC changes)
"""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import OpenDateRangeModel, SafeDecimal
from backend.app.schemas.wac import WACMissingPairInfo


# =============================================================================
# WAC ANALYTICS — Time series request/response
# =============================================================================


class WACAnalyticsQuery(BaseModel):
    """Single query for WAC time series."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int = Field(..., description="Broker to compute WAC for")
    asset_id: int = Field(..., description="Asset to compute WAC for")
    date_range: Optional[OpenDateRangeModel] = Field(
        None, description="Date range filter. None = entire history."
    )


class WACAnalyticsRequest(BaseModel):
    """Request body for POST /analytics/wac."""

    model_config = ConfigDict(extra="forbid")

    queries: List[WACAnalyticsQuery] = Field(..., min_length=1, max_length=20, description="WAC queries (max 20)")


class WACSeriesPoint(BaseModel):
    """Single point in WAC time series (where WAC changes)."""

    model_config = ConfigDict(extra="forbid")

    date: date_type
    wac: SafeDecimal = Field(..., description="WAC per unit after this transaction")
    pool_qty: SafeDecimal = Field(..., description="Pool quantity after this transaction")
    effect: str = Field(..., description="Effect on pool: add, reduce, add_zero_cost, add_at_wac")


class WACAnalyticsResultItem(BaseModel):
    """WAC series result for a single (broker, asset) query."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    asset_id: int
    currency: str = Field(..., description="Target currency of WAC values")
    series: List[WACSeriesPoint] = Field(default_factory=list)
    missing_pairs: List["WACMissingPairInfo"] = Field(default_factory=list, description="FX pairs that could not be resolved, with dates")


class WACAnalyticsResponse(BaseModel):
    """Response for POST /analytics/wac."""

    model_config = ConfigDict(extra="forbid")

    results: List[WACAnalyticsResultItem]

