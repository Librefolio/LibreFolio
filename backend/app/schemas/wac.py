"""
WAC (Weighted Average Cost) schemas for LibreFolio.

Contains all schema classes related to WAC calculation:
- WACConversionInfo: FX conversion details applied during WAC
- WACQualifyingTX: A transaction that participated in iterative WAC
- WACPreviewResultItem: Full result for preview/inline WAC (used in batch response)
"""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import BackwardFillInfo, Currency, FxBackwardFillInfo, SafeDecimal

# =============================================================================
# WAC (WEIGHTED AVERAGE COST) — FX-aware calculation results
# =============================================================================


class WACConversionInfo(BaseModel):
    """Single FX conversion applied during WAC calculation."""

    model_config = ConfigDict(extra="forbid")

    tx_id: int = Field(..., description="Transaction ID that needed conversion")
    from_currency: str = Field(..., description="Original currency of the transaction")
    to_currency: str = Field(..., description="Target currency for WAC")
    rate: SafeDecimal = Field(..., description="FX rate applied")
    rate_date: date_type = Field(..., description="Actual date of the FX rate used")
    stale_days: int = Field(0, ge=0, description="Days between TX date and rate date (0 = fresh)")



class WACQualifyingTX(BaseModel):
    """A TX that participated in WAC calculation."""

    model_config = ConfigDict(extra="forbid")

    tx_id: Optional[int] = Field(None, description="DB id, or None if pending without id")
    type: str
    date: date_type
    quantity: SafeDecimal
    unit_cost: Optional[SafeDecimal] = None
    currency: Optional[str] = None
    effect: str = Field(..., description="add | reduce | add_zero_cost")
    fx_info: Optional[FxBackwardFillInfo] = None
    running_wac: Optional[SafeDecimal] = Field(None, description="Running WAC per unit after this TX")
    original_unit_cost: Optional[SafeDecimal] = Field(None, description="Unit cost in original currency (before FX)")
    original_currency: Optional[str] = Field(None, description="Original currency before FX conversion")
    fx_rate_used: Optional[SafeDecimal] = Field(None, description="FX rate applied (derived: converted/original)")


class WACMissingPairInfo(BaseModel):
    """A missing FX pair with all dates that needed conversion."""

    model_config = ConfigDict(extra="forbid")

    pair: str = Field(..., description="FX pair code (e.g. 'USD/EUR')")
    dates: List[date_type] = Field(default_factory=list, description="Dates for which FX rate was needed but unavailable")


class WACPreviewResultItem(BaseModel):
    """Result for a single WAC preview item.

    Also used inline in TXBatchResponse.wac_results[] for items with
    cost_basis_mode in ('auto', 'auto-detail'). In that context the
    optional batch-context fields (operation, index, source_broker_id)
    are populated.
    """

    model_config = ConfigDict(extra="forbid")

    # WAC inventory-aware
    wac: Optional[Currency] = Field(None, description="Calculated WAC per unit. None if FX conversion failed.")
    wac_qualifying_txs: List[WACQualifyingTX] = Field(default_factory=list)
    wac_missing_pairs: List[WACMissingPairInfo] = Field(default_factory=list, description="Missing FX pairs with dates that needed conversion")
    # Asset price at date (useful for ADJUSTMENT scenario)
    asset_price: Optional[Currency] = Field(None, description="Asset close price at as_of_date (backward-filled)")
    asset_price_stale: Optional[BackwardFillInfo] = Field(None, description="Staleness of asset price")
    asset_price_missing: bool = Field(False, description="True if no price data available at all")

    # --- Batch-context fields (only set when used inside TXBatchResponse.wac_results) ---
    operation: Optional[Literal["create", "update"]] = Field(None, description="Batch operation type (set only in inline WAC)")
    index: Optional[int] = Field(None, description="Position in creates[] or updates[] (set only in inline WAC)")
    source_broker_id: Optional[int] = Field(None, description="Broker used for WAC calculation (set only in inline WAC)")
