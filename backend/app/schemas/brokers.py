"""
Broker schemas for LibreFolio.

DTOs for Broker CRUD operations.
These schemas provide strict validation for API input/output.

**Naming Convention**:
- BR prefix: Broker-related schemas
- Item suffix: Single item in a list (e.g., BRCreateItem)

**Design Notes**:
- Broker no longer has explicit currency list - currencies are derived from transactions
- initial_balances in BRCreateItem auto-creates DEPOSIT transactions
- Uses Currency from common.py for cash validation
- Uses BaseBulkResponse/BaseDeleteResult from common.py for consistency
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.db.models import UserRole
from backend.app.schemas.common import (
    Currency,
    BaseBulkResponse,
    BaseBulkDeleteResponse,
    BaseDeleteResult,
    )


# =============================================================================
# BROKER CREATE
# =============================================================================

class BRCreateItem(BaseModel):
    """
    DTO for creating a new broker.

    Used by POST /api/v1/brokers endpoint.

    initial_balances: Optional list of Currency objects.
    Creates automatic DEPOSIT transactions for each.
    Example: [Currency(code="EUR", amount=10000), Currency(code="USD", amount=5000)]
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100, description="Broker name (must be unique)")
    description: Optional[str] = Field(default=None, max_length=500, description="Broker description")
    portal_url: Optional[str] = Field(default=None, max_length=255, description="URL to broker's web portal")

    allow_cash_overdraft: bool = Field(default=False, description="Allow negative cash balance (margin trading)")
    allow_asset_shorting: bool = Field(default=False, description="Allow negative asset quantities (short selling)")

    # Auto-creates DEPOSIT transactions - using Currency objects
    initial_balances: Optional[List[Currency]] = Field(default=None, description="Initial cash balances. Creates DEPOSIT transactions.")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not just whitespace."""
        v = v.strip()
        if not v:
            raise ValueError("Broker name cannot be empty or whitespace")
        return v

    @field_validator('initial_balances')
    @classmethod
    def validate_initial_balances(cls, v):
        """Validate initial_balances - only keep positive amounts."""
        if v is None:
            return v

        # Filter out zero/negative amounts
        valid = [c for c in v if c.is_positive()]
        return valid if valid else None


# =============================================================================
# BROKER READ
# =============================================================================

class BRReadItem(BaseModel):
    """
    DTO for reading broker basic data.

    Response format for GET operations.
    Maps directly from Broker SQLModel.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    portal_url: Optional[str] = None

    allow_cash_overdraft: bool
    allow_asset_shorting: bool

    created_at: datetime
    updated_at: datetime


# =============================================================================
# BROKER WITH BALANCES AND HOLDINGS
# =============================================================================

class BRAssetHolding(BaseModel):
    """
    Single asset holding within a broker.

    Represents current position in an asset with cost basis and market value.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    asset_name: str = Field(..., description="Asset display name")

    quantity: Decimal = Field(..., description="Current quantity held")

    # Cost basis (total spent to acquire)
    total_cost: Currency = Field(..., description="Total amount spent to acquire (FIFO)")
    average_cost_per_unit: Decimal = Field(..., description="Average cost per unit")

    # Current valuation (if price available)
    current_price: Optional[Decimal] = Field(default=None, description="Latest price per unit")
    current_value: Optional[Currency] = Field(default=None, description="Current market value")

    # Unrealized P&L
    unrealized_pnl: Optional[Currency] = Field(default=None, description="Unrealized profit/loss")
    unrealized_pnl_percent: Optional[Decimal] = Field(default=None, description="Unrealized P&L %")


class BRSummary(BRReadItem):
    """
    Broker with computed cash balances and asset holdings.

    Includes:
    - Current cash balance per currency (computed from transactions)
    - Asset holdings with cost basis and market value
    - Total portfolio value in base currency (if FX rates available)
    """

    # Cash balances as list of Currency objects
    cash_balances: List[Currency] = Field(default_factory=list, description="Current cash balance per currency")

    # Asset holdings with full details
    holdings: List[BRAssetHolding] = Field(default_factory=list, description="Current asset holdings with cost basis and market value")

    # Optional: Total portfolio value in user's base currency
    total_value_base_currency: Optional[Currency] = Field(default=None, description="Total portfolio value in base currency (cash + holdings)")

    @property
    def currencies(self) -> List[str]:
        """List of currencies used in this broker's cash balances."""
        return [c.code for c in self.cash_balances]

    @property
    def total_cash_positions(self) -> int:
        """Number of different currencies with cash balance."""
        return len(self.cash_balances)

    @property
    def total_asset_positions(self) -> int:
        """Number of different assets held."""
        return len(self.holdings)


# =============================================================================
# BROKER UPDATE
# =============================================================================

class BRUpdateItem(BaseModel):
    """
    DTO for updating a broker.

    All fields are optional.
    Only provided fields will be updated.

    Note: Changing flags from True to False triggers balance validation.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="New broker name")
    description: Optional[str] = Field(default=None, max_length=500, description="New description")
    portal_url: Optional[str] = Field(default=None, max_length=255, description="New portal URL")

    allow_cash_overdraft: Optional[bool] = Field(default=None, description="Update overdraft permission")
    allow_asset_shorting: Optional[bool] = Field(default=None, description="Update shorting permission")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name is not just whitespace."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Broker name cannot be empty or whitespace")
        return v


# =============================================================================
# BROKER DELETE
# =============================================================================

class BRDeleteItem(BaseModel):
    """
    Single broker deletion request.

    Behavior:
    - force=False (default): Delete fails if broker has any transactions.
      Returns error "Broker has N transactions. Use force=True to delete all."
    - force=True: Deletes broker AND all associated transactions.
      transactions_deleted in BRDeleteResult shows how many were removed.
    """
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0, description="Broker ID to delete")
    force: bool = Field(default=False, description="If True, cascade delete all transactions. If False, fail if transactions exist.")


class BRDeleteResult(BaseDeleteResult):
    """
    Result for a single broker deletion attempt.

    Extends BaseDeleteResult with broker-specific fields.
    - transactions_deleted: Count of transactions removed (only >0 when force=True was used)
    """
    id: int = Field(..., description="Broker ID")
    transactions_deleted: int = Field(default=0, ge=0, description="Number of transactions cascade-deleted (only when force=True)")


class BRBulkDeleteResponse(BaseBulkDeleteResponse[BRDeleteResult]):
    """Response for bulk broker deletion."""
    pass


# =============================================================================
# BULK CREATE RESPONSE
# =============================================================================

class BRCreateResult(BaseModel):
    """Result for a single broker creation attempt."""
    model_config = ConfigDict(extra="forbid")

    success: bool
    broker_id: Optional[int] = None
    name: str  # Echo back for client correlation
    deposits_created: int = Field(default=0, ge=0, description="Number of DEPOSIT transactions created")
    error: Optional[str] = None


class BRBulkCreateResponse(BaseBulkResponse[BRCreateResult]):
    """Response for bulk broker creation."""
    pass


# =============================================================================
# BULK UPDATE RESPONSE
# =============================================================================

class BRUpdateResult(BaseModel):
    """Result for a single broker update attempt."""
    model_config = ConfigDict(extra="forbid")

    id: int
    success: bool
    validation_triggered: bool = Field(default=False, description="Whether balance validation was triggered due to flag change")
    error: Optional[str] = None


class BRBulkUpdateResponse(BaseBulkResponse[BRUpdateResult]):
    """Response for bulk broker update."""
    pass


# =============================================================================
# BROKER USER ACCESS
# =============================================================================

class BRUserAccessCreateItem(BaseModel):
    """
    DTO for granting user access to a broker.
    """
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., gt=0, description="User ID")
    broker_id: int = Field(..., gt=0, description="Broker ID")
    role: UserRole = Field(default=UserRole.VIEWER, description="Access role")


class BRUserAccessReadItem(BaseModel):
    """
    DTO for reading broker user access.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    user_id: int
    broker_id: int
    role: UserRole

    created_at: datetime
    updated_at: datetime


class BRUserAccessUpdateItem(BaseModel):
    """
    DTO for updating broker user access.
    """
    model_config = ConfigDict(extra="forbid")

    role: UserRole = Field(..., description="New access role")
