"""The filtered allocation (``POST /portfolio/allocation``, lane 80, issue #89): the query and the view of the «Allocazione» tab.

The view is ``financial_math.portfolio.allocation_view``'s: the NAV of the last day of the period, split in one
dimension after the user's filters, with base + outside + excluded = NAV. Amounts in the report currency, at the
owner's share unless ``apply_ownership_share`` is False; shares are percentages rounded to 0.01, None when their total
is at or below zero. The frontend computes none of them.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Annotated, List, Literal, Optional

from pydantic import Field, StringConstraints

from backend.app.schemas.common import OpenDateRangeModel, SafeDecimal, StrictModel
from backend.app.schemas.portfolio.summary import AllocationHistoryPoint

AllocationDimensionName = Literal["sector", "geography", "type", "asset"]
#: The buckets a user may exclude. Liquidity is only a class: it is filtered by ``classes``, never excluded
ExcludableBucket = Literal["Unknown", "Other"]
AllocationClassName = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class PortfolioAllocationQuery(StrictModel):
    """Request body for POST /portfolio/allocation: the scope and period as the report's, the dimension and the filters."""

    broker_ids: Optional[List[int]] = Field(None, description="Broker filter, as the report's. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="The period, as the report's: the view is its last day («Ora»), the classes, assets and history cover it. None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217).")
    apply_ownership_share: bool = Field(True, description="As the report's: False counts every broker whole (the broker page, D4).")
    dimension: AllocationDimensionName = Field("sector", description="What the slices split by: sector, geography (ISO3 countries), type (the asset type as stored), asset.")
    classes: Optional[List[AllocationClassName]] = Field(
        None,
        max_length=64,
        description="The classes in the selection: an asset's class is the type of what it holds (ETF_STOCK → STOCK; ETF_MONETARY and ETF stay themselves), the cash is «Liquidity». None = every class; [] = none.",
    )
    exclude_buckets: List[ExcludableBucket] = Field(default_factory=list, description="Buckets taken out of the base where they exist: sector Unknown and Other, geography and type Unknown. Elsewhere no effect.")
    exclude_asset_ids: List[int] = Field(default_factory=list, max_length=1000, description="Assets taken out of the base whole.")
    include_history: bool = Field(False, description="Include the selection's slices in steps over the period.")


class AllocationSliceAsset(StrictModel):
    asset_id: int
    amount: SafeDecimal
    share_of_slice: Optional[SafeDecimal] = Field(None, description="Percent of the slice; None when the slice is at or below zero")


class AllocationViewSlice(StrictModel):
    """A slice of the base."""

    key: str = Field(..., description="The bucket: a sector, an ISO3 country, an asset type, «Liquidity»; in the asset dimension the asset id as text (or «Liquidity»)")
    asset_id: Optional[int] = Field(None, description="The asset of a slice of the asset dimension; None otherwise and for its Liquidity slice")
    amount: SafeDecimal
    share_of_selection: Optional[SafeDecimal] = Field(None, description="Percent of the base; None for every slice when the base is at or below zero")
    share_of_portfolio: Optional[SafeDecimal] = Field(None, description="Percent of the NAV; None when the NAV is at or below zero")
    assets: List[AllocationSliceAsset] = Field(default_factory=list, description="The assets that make the slice up, largest first; empty for Liquidity and in the asset dimension")


class AllocationClassAmount(StrictModel):
    asset_class: str
    amount: SafeDecimal


class AllocationBucketAmount(StrictModel):
    key: str
    amount: SafeDecimal


class AllocationAssetAmount(StrictModel):
    asset_id: int
    amount: SafeDecimal


class AllocationUnattributableAmount(StrictModel):
    reason: Literal["in_transit", "no_country"] = Field(..., description="in_transit: securities between brokers (no asset in the day's state); no_country: the cash in the geography")
    amount: SafeDecimal


class AllocationOutside(StrictModel):
    """What the class filter leaves out."""

    amount: SafeDecimal
    by_class: List[AllocationClassAmount] = Field(default_factory=list)


class AllocationExcluded(StrictModel):
    """The user's exclusions, and the amounts with no bucket in the dimension (fixed rows, with their reason)."""

    amount: SafeDecimal
    by_bucket: List[AllocationBucketAmount] = Field(default_factory=list)
    by_asset: List[AllocationAssetAmount] = Field(default_factory=list)
    unattributable: List[AllocationUnattributableAmount] = Field(default_factory=list)


class AllocationScopeAsset(StrictModel):
    """An asset held on some day of the period: what the filter panel lists."""

    asset_id: int
    asset_class: str
    amount: SafeDecimal = Field(..., description="Its value on the view's day; 0 when it was held only earlier in the period")
    name: str
    ticker: Optional[str] = None
    asset_type: Optional[str] = Field(None, description="The asset type as stored (its icon when it has none of its own)")
    icon_url: Optional[str] = None


class AllocationMatrixCell(StrictModel):
    asset_class: str
    key: str
    amount: SafeDecimal
    share_of_portfolio: Optional[SafeDecimal] = None


class AllocationMatrix(StrictModel):
    """Class × dimension of the whole portfolio, whatever the filters: cells + unattributed = NAV."""

    rows: List[str] = Field(default_factory=list, description="Classes, largest first")
    columns: List[str] = Field(default_factory=list, description="Buckets, largest first")
    cells: List[AllocationMatrixCell] = Field(default_factory=list)
    unattributed: List[AllocationUnattributableAmount] = Field(default_factory=list, description="What has no column: the cash in the geography, the securities in transit")


class AllocationViewHistoryStep(AllocationHistoryPoint):
    """A step of the selection's history: the slices hold from ``date`` to ``through``; ``base`` is their sum."""

    base: SafeDecimal


class PortfolioAllocationResponse(StrictModel):
    """Response for POST /portfolio/allocation."""

    currency: str
    date_from: Optional[date_type] = Field(None, description="The period's start, as resolved; None = from the first day")
    as_of: Optional[date_type] = Field(None, description="The view's day: the period's last day; None when the scope holds nothing")
    dimension: AllocationDimensionName
    applicable_buckets: List[ExcludableBucket] = Field(default_factory=list, description="The excludable buckets that exist in this dimension: the panel shows only these")
    portfolio_total: SafeDecimal = Field(..., description="The NAV of the view's day, the KPI «Patrimonio netto»")
    base: SafeDecimal = Field(..., description="The sum of the slices, the 100 % of the chart")
    base_share_of_portfolio: Optional[SafeDecimal] = None
    slices: List[AllocationViewSlice] = Field(default_factory=list, description="Largest first")
    outside: AllocationOutside
    excluded: AllocationExcluded
    classes: List[AllocationClassAmount] = Field(default_factory=list, description="Classes held on some day of the period, with the view's day's amount, largest first")
    assets: List[AllocationScopeAsset] = Field(default_factory=list, description="Assets held on some day of the period, largest first")
    matrix: Optional[AllocationMatrix] = Field(None, description="None in the asset dimension")
    history: Optional[List[AllocationViewHistoryStep]] = Field(None, description="None unless include_history")
