"""
Database models for LibreFolio.

All models use SQLModel (SQLAlchemy 2.x) with the following conventions:
- Decimal columns use Numeric(18, 6) for precision
- Timestamps in UTC (created_at, updated_at, fetched_at)
- Daily-point policy: one record per day for prices and FX rates
- Foreign keys enforced with PRAGMA foreign_keys=ON
- Currency fields validated against ISO 4217 + crypto via Currency.validate_code()
"""

import json
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional

from pydantic import field_validator
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    event,
)
from sqlmodel import Field, Relationship, SQLModel

from backend.app.utils.datetime_utils import utcnow

# =============================================================================
# CURRENCY VALIDATION HELPER
# =============================================================================


def _validate_currency_field(v: Any) -> Optional[str]:
    """
    Validate currency field using cached Currency.validate_code().

    This helper is used by @field_validator in SQLModel classes.
    It allows None values for Optional[str] fields.
    """
    if v is None:
        return v
    # Import here to avoid circular imports
    from backend.app.schemas.common import Currency  # noqa: PLC0415 — avoid circular import

    return Currency.validate_code(v)


# ============================================================================
# ENUMS
# ============================================================================


class ProviderInputType(StrEnum):
    """
    Describes the kind of identifier input a provider expects.

    This is NOT the same as IdentifierType (which describes asset record columns).
    ProviderInputType tells the frontend what the provider needs as input:

    - TICKER: A stock ticker symbol (e.g., AAPL)
    - ISIN: An ISIN code (e.g., IE00B4L5Y983)
    - URL: A full URL to scrape (e.g., https://example.com/price)
    - AUTO_GENERATED: No user input needed — identifier is auto-generated (e.g., UUID)

    Mapping to stored IdentifierType:
    - TICKER → IdentifierType.TICKER
    - ISIN → IdentifierType.ISIN
    - URL → IdentifierType.OTHER
    - AUTO_GENERATED → IdentifierType.UUID
    """

    TICKER = "TICKER"
    ISIN = "ISIN"
    URL = "URL"
    AUTO_GENERATED = "AUTO_GENERATED"


class IdentifierType(StrEnum):
    """
    Asset identifier type.

    Usage: Specify which type of identifier is stored in the 'identifier' field.

    - ISIN: International Securities Identification Number (e.g., US0378331005 for Apple)
    - TICKER: Stock ticker symbol (e.g., AAPL, MSFT)
    - CUSIP: Committee on Uniform Securities Identification Procedures (US/Canada)
    - SEDOL: Stock Exchange Daily Official List (UK)
    - FIGI: Financial Instrument Global Identifier (Bloomberg standard)
    - UUID: Universal Unique Identifier (for custom/synthetic assets)
    - OTHER: Any other identifier type not listed above

    Impact: Used for data validation and plugin selection. Some plugins may only
    work with specific identifier types (e.g., Yahoo Finance prefers TICKER).

    ⚠️  DEPENDENT SCHEMAS - If you add/remove values, update these files:

    1. DATABASE SCHEMA:
       - backend/alembic/versions/001_initial.py
         → Add column: identifier_{value.lower()} in assets table
         → Add index if frequently searched (ISIN, TICKER have indexes)

    2. SQLMODEL (this file):
       - Asset class below
         → Add field: identifier_{value.lower()}: Optional[str]
         → Add validator if needed (e.g., ISIN requires 12 chars)

    3. PYDANTIC SCHEMAS (backend/app/schemas/assets.py):
       - FAAssetCreateItem: Add identifier_{value.lower()} field
       - FAAssetPatchItem: Add identifier_{value.lower()} field
       - FAinfoResponse: Add identifier_{value.lower()} field
       - FAAinfoFiltersRequest: Add filter field (exact or partial match)

    4. SERVICE LAYER (backend/app/services/asset_source.py):
       - list_assets(): Add condition for new filter
       - create_assets_bulk(): Pass new field to Asset()

    5. BRIM PROVIDER (backend/app/services/brim_provider.py):
       - search_asset_candidates(): Add search priority if relevant

    6. TESTS:
       - test_identifier_columns_match_enum() will FAIL automatically
         if Asset.identifier_{value.lower()} is missing

    Run: pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v
    """

    ISIN = "ISIN"
    TICKER = "TICKER"
    CUSIP = "CUSIP"
    SEDOL = "SEDOL"
    FIGI = "FIGI"
    UUID = "UUID"
    OTHER = "OTHER"


class AssetType(StrEnum):
    """
    Asset type classification.

    Usage: Categorize assets by their nature for reporting and analysis.

    - STOCK: Individual company shares (e.g., Apple, Microsoft)
    - ETF: Exchange Traded Fund (e.g., VWCE, SPY)
    - BOND: Fixed income securities (government or corporate bonds)
    - CRYPTO: Cryptocurrencies (e.g., Bitcoin, Ethereum)
    - FUND: Mutual funds or investment funds
    - HOLD: Assets without automatic market pricing (real estate, art, collectibles, unlisted companies)
    - CROWDFUND_LOAN: Peer-to-peer lending or crowdfunding loans (e.g., Recrowd, Mintos)
    - INDEX: Market indices and benchmarks (e.g., S&P 500, MSCI World) — no transactions allowed
    - OTHER: Any other asset type not listed above

    Impact:
    - Affects default valuation_model:
      - CROWDFUND_LOAN -> SCHEDULED_YIELD
      - HOLD -> MANUAL
      - INDEX -> MARKET_PRICE (read-only benchmark, no transactions)
      - Others -> MARKET_PRICE
    - Used for portfolio breakdown and allocation analysis
    - May influence available data plugins (e.g., crypto uses different sources)
    """

    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    CRYPTO = "CRYPTO"
    FUND = "FUND"
    CROWDFUND_LOAN = "CROWDFUND_LOAN"
    HOLD = "HOLD"
    INDEX = "INDEX"
    OTHER = "OTHER"


class AssetEventType(StrEnum):
    """
    Types of asset-level events that affect price or generate distributions.

    These events live in the asset domain (not portfolio/transaction domain):
    - DIVIDEND: Cash distribution from equity/ETF (ex-date price drop)
    - INTEREST: Interest payment from debt/loan (ex-date price drop)
    - PRICE_ADJUSTMENT: Non-cash value change (write-down, haircut, re-rating)
    - SPLIT: Stock/unit split (changes quantity, not total value)
    - MATURITY_SETTLEMENT: Asset reaches maturity — final capital return, no further calculations
    """

    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT"
    SPLIT = "SPLIT"
    MATURITY_SETTLEMENT = "MATURITY_SETTLEMENT"


class TransactionType(StrEnum):
    """
    Unified transaction types for all asset and cash operations.

    This enum represents all possible transaction types in the unified
    transaction table. Each type has specific rules for quantity and amount signs.

    == Asset transactions (quantity != 0) ==

    - BUY: Purchase asset with cash
      Signs: quantity > 0, amount < 0
      Example: Buy 10 shares of AAPL for €1500

    - SELL: Sell asset for cash
      Signs: quantity < 0, amount > 0
      Example: Sell 5 shares of MSFT for €1500

    - TRANSFER: Asset transfer between brokers
      Signs: quantity +/-, amount = 0
      Requires: related_transaction_id (links to paired transfer)
      Example: Transfer 100 shares from Broker A to Broker B

    - ADJUSTMENT: Manual asset quantity correction (splits, gifts, etc.)
      Signs: quantity +/-, amount = 0
      Optional: related_transaction_id
      Example: Stock split 2:1 adds 100 shares

    == Cash-only transactions (quantity = 0) ==

    - DIVIDEND: Dividend payment received
      Signs: quantity = 0, amount > 0
      Example: Receive €50 dividend from AAPL

    - INTEREST: Interest payment received
      Signs: quantity = 0, amount > 0
      Example: Monthly interest from crowdfunding loan

    - DEPOSIT: Add cash to broker account
      Signs: quantity = 0, amount > 0
      Example: Transfer €1000 to broker

    - WITHDRAWAL: Remove cash from broker account
      Signs: quantity = 0, amount < 0
      Example: Withdraw €500 from broker

    - FEE: Fee or commission payment
      Signs: quantity = 0, amount < 0
      Example: €5 custody fee

    - TAX: Tax payment
      Signs: quantity = 0, amount < 0
      Example: €100 capital gains tax

    - FX_CONVERSION: Currency exchange
      Signs: quantity = 0, amount +/-
      Requires: related_transaction_id (links to paired conversion)
      Example: Convert €1000 to $1090

    - CASH_TRANSFER: Wire transfer / bonifico between brokers
      Signs: quantity = 0, amount +/- (nonzero)
      Requires: related_transaction_id (links to paired cash transfer)
      Example: Transfer €5000 from IBKR to Fineco

    Impact:
    - TRANSFER, FX_CONVERSION and CASH_TRANSFER require related_transaction_id
    - Validation ensures sign rules are followed
    - All calculations based on settlement date
    """

    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"
    TAX = "TAX"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
    FX_CONVERSION = "FX_CONVERSION"
    CASH_TRANSFER = "CASH_TRANSFER"


class UserRole(StrEnum):
    """
    User role for broker access control.

    - OWNER: Full access (CRUD broker, manage access, delete broker)
    - EDITOR: Modify broker and transactions, can only remove self
    - VIEWER: Read-only access
    """

    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


# ============================================================================
# USER MODELS
# ============================================================================


class User(SQLModel, table=True):
    """
    User account for multi-tenancy support.

    Each user can have multiple brokers with different access levels.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class UserSettings(SQLModel, table=True):
    """
    User preferences and settings.

    One-to-one relationship with User.
    """

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, unique=True)

    base_currency: str = Field(default="EUR", max_length=3)  # ISO 4217
    language: str = Field(default="en", max_length=5)  # e.g., "en", "it", "fr", "es"
    theme: str = Field(default="light", max_length=20)  # e.g., "light", "dark"
    avatar_url: Optional[str] = Field(default=None, max_length=500)  # URL to user avatar image

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("base_currency", mode="before")
    @classmethod
    def validate_base_currency(cls, v: Any) -> str:
        """Validate base_currency against ISO 4217 + crypto."""
        return _validate_currency_field(v)


class GlobalSetting(SQLModel, table=True):
    """
    System-wide settings.

    Key-value store for global configuration.
    Only administrators can modify these settings.

    Predefined keys:
    - session_ttl_hours: Session cookie TTL in hours (int, default: 24)
    - max_file_upload_mb: Max file upload size in MB (int, default: 10)
    - enable_registration: Allow new user registration (bool, default: true)
    """

    __tablename__ = "global_settings"

    key: str = Field(primary_key=True, max_length=100)
    value: str = Field(...)  # Stored as string, converted based on value_type
    value_type: str = Field(max_length=20)  # "string", "int", "bool", "json"
    description: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id", nullable=True)


# ============================================================================
# BROKER MODELS
# ============================================================================


class Broker(SQLModel, table=True):
    """
    Broker/platform where assets are held.

    Examples: Interactive Brokers, Degiro, Recrowd, etc.

    Flags:
    - allow_cash_overdraft: If True, cash balance can go negative (margin/leveraged trading)
    - allow_asset_shorting: If True, asset quantity can go negative (short selling)
    - is_active: If False, the account is closed in reality (but we keep historical data)
    """

    __tablename__ = "brokers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    portal_url: Optional[str] = Field(default=None)
    icon_url: Optional[str] = Field(default=None, description="Custom icon URL for the broker")
    default_import_plugin: Optional[str] = Field(default=None, description="Default BRIM plugin for importing transactions")

    # New flags for advanced trading scenarios
    allow_cash_overdraft: bool = Field(default=False, description="Allow leveraged buying (negative cash balance)")
    allow_asset_shorting: bool = Field(default=False, description="Allow short selling (negative asset quantities)")

    # Account status
    is_active: bool = Field(default=True, description="Whether the broker account is currently active")
    opened_at: Optional[date_type] = Field(default=None, description="Date when the account was opened in reality")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BrokerUserAccess(SQLModel, table=True):
    """
    Many-to-many relationship between Users and Brokers with role-based access.

    Defines which users can access which brokers and with what permissions.

    share_percentage: Ownership fraction (0.00 to 1.00) used for portfolio aggregation.
    - OWNER: defaults to 1.00 (can be reduced for co-ownership, e.g., joint accounts)
    - EDITOR: defaults to 0.00 (delegated operator, e.g., spouse or financial advisor)
    - VIEWER: defaults to 0.00 (e.g., accountant, read-only)
    - Sum of share_percentage across users for a broker MUST NOT exceed 1.00.
      The backend validates this constraint on add/update operations.
    - Sum CAN be less than 1.00 (e.g., co-owned account where co-owner is not in the system).
    - The API sends and receives this value as-is (0-1 fraction).
      The frontend converts to/from percentage for display purposes.
    """

    __tablename__ = "broker_user_access"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_id", name="uq_broker_user_access"),
        CheckConstraint(
            "share_percentage >= 0 AND share_percentage <= 1",
            name="ck_broker_user_access_share_percentage",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    role: UserRole = Field(default=UserRole.VIEWER)
    share_percentage: Decimal = Field(
        default=Decimal("1"),
        sa_column=Column(Numeric(7, 6), nullable=False, default=1),
        description="Ownership fraction (0.000000 to 1.000000) for portfolio aggregation",
    )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# ============================================================================
# ASSET MODELS
# ============================================================================


class Asset(SQLModel, table=True):
    """
    Asset definition - core metadata container.

    This model stores fundamental asset information independent of pricing logic.
    Provider-specific identification and valuation is handled via asset_provider_assignments table.

    Identifier columns:
    - One column per IdentifierType enum value (identifier_isin, identifier_ticker, etc.)
    - Allows direct search without JOIN to asset_provider_assignments
    - An asset can have multiple identifiers (e.g., both ISIN and TICKER)

    Provider assignments:
    - Use asset_provider_assignments table (1-to-1 relationship)
    - Each asset can have at most one provider for pricing data
    - Provider handles both current and historical data fetching
    - Provider assignment includes identifier, identifier_type, and provider_params

    Classification and metadata fields:
    - classification_params: JSON containing ClassificationParamsModel structure

    Notes:
    - display_name must be unique to avoid user confusion
    - Validation is done via ClassificationParamsModel Pydantic model when loaded
    """

    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("display_name", name="uq_assets_display_name"),
        Index("ix_assets_identifier_isin", "identifier_isin"),
        Index("ix_assets_identifier_ticker", "identifier_ticker"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str = Field(nullable=False)

    currency: str = Field(nullable=False, description="Asset original currency")  # ISO 4217
    icon_url: Optional[str] = Field(default=None, description="URL to asset icon (local or remote)")

    # Classification and metadata (JSON TEXT)
    classification_params: Optional[str] = Field(default=None, sa_column=Column(Text))
    asset_type: AssetType = Field(default=AssetType.OTHER)

    active: bool = Field(default=True)
    user_url: Optional[str] = Field(default=None, description="User-defined URL (notes, external dashboard, etc.)")

    # Identifier columns - one per IdentifierType enum value
    # Allows direct search without JOIN to asset_provider_assignments
    identifier_isin: Optional[str] = Field(default=None, max_length=12, description="ISIN code (12 chars)")
    identifier_ticker: Optional[str] = Field(default=None, max_length=20, description="Ticker symbol")
    identifier_cusip: Optional[str] = Field(default=None, max_length=9, description="CUSIP code (9 chars)")
    identifier_sedol: Optional[str] = Field(default=None, max_length=7, description="SEDOL code (7 chars)")
    identifier_figi: Optional[str] = Field(default=None, max_length=12, description="FIGI code (12 chars)")
    identifier_uuid: Optional[str] = Field(default=None, max_length=36, description="UUID for custom assets")
    identifier_other: Optional[str] = Field(default=None, max_length=100, description="Other identifier")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        """Validate currency against ISO 4217 + crypto."""
        return _validate_currency_field(v)

    @field_validator("identifier_isin", mode="before")
    @classmethod
    def validate_identifier_isin(cls, v: Any) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == "":
            return None
        v = str(v).strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator("identifier_ticker", mode="before")
    @classmethod
    def validate_identifier_ticker(cls, v: Any) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == "":
            return None
        return str(v).strip().upper()

    @field_validator("classification_params")
    def validate_classification_params(cls, v):
        # Lazy import to avoid circular dependency
        from backend.app.schemas.assets import FAClassificationParams  # noqa: PLC0415 — avoid circular import

        if v is None:
            return v
        if isinstance(v, FAClassificationParams):
            return v.model_dump_json(exclude_none=True)
        return FAClassificationParams(**v).model_dump_json(exclude_none=True)


# ============================================================================
# TRANSACTION MODEL (UNIFIED)
# ============================================================================


class Transaction(SQLModel, table=True):
    """
    Unified transaction record for all asset and cash movements.

    This is the single source of truth for all financial operations.
    Replaces the old Transaction + CashMovement dual-table model.

    Key design decisions:
    - quantity and amount use signed values (+ in, - out)
    - Both default to 0 and are NOT NULL for easier SUM calculations
    - currency is required only when amount != 0
    - related_transaction_id links paired transactions (transfers, FX)
    - tags stored as comma-separated string for simple queries

    Field semantics:
    - quantity: Asset delta (positive = buy/in, negative = sell/out)
    - amount: Cash delta (positive = receive, negative = spend)
    - date: Settlement date (when transaction is finalized)

    Relationship rules:
    - TRANSFER: quantity != 0, amount = 0, related_transaction_id REQUIRED
    - FX_CONVERSION: quantity = 0, amount != 0, related_transaction_id REQUIRED
    - ADJUSTMENT: quantity != 0, amount = 0, related_transaction_id OPTIONAL
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_broker_date", "broker_id", "date", "id"),
        Index("idx_transactions_asset_date", "asset_id", "date"),
        Index("idx_transactions_related", "related_transaction_id"),
        Index("idx_transactions_asset_event", "asset_event_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    asset_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("assets.id"), nullable=True, index=True),
        description="Asset ID, NULL for pure cash transactions",
    )

    type: TransactionType = Field(nullable=False)
    date: date_type = Field(nullable=False, index=True, description="Settlement date")

    # Signed values: + in, - out. Default 0, NOT NULL for SUM calculations
    quantity: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 6), nullable=False, default=0),
        description="Asset quantity delta (+ in, - out)",
    )
    amount: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 6), nullable=False, default=0),
        description="Cash amount delta (+ in, - out)",
    )
    currency: Optional[str] = Field(default=None, max_length=3, description="ISO 4217 currency code, required if amount != 0")

    # Link for paired transactions (TRANSFER, FX_CONVERSION)
    # BIDIRECTIONAL: Both transactions point to each other (A->B and B->A)
    # Uses DEFERRABLE INITIALLY DEFERRED FK - constraint checked only at COMMIT
    # This allows creating both records in the same transaction without FK violations
    related_transaction_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("transactions.id", deferrable=True, initially="DEFERRED"),
            nullable=True,
        ),
        description="Links to paired transaction (for TRANSFER, FX_CONVERSION). Bidirectional.",
    )

    # Relationship for ORM access (post_update=True for bidirectional self-reference)
    # This tells SQLAlchemy to INSERT first with NULL, then UPDATE to set the link
    related_transaction: Optional["Transaction"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Transaction.related_transaction_id]",
            "remote_side": "[Transaction.id]",
            "post_update": True,
        }
    )

    # User-defined tags for filtering and grouping
    tags: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Comma-separated tags (e.g., 'tag1,tag2,tag3')",
    )

    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Frozen cost basis for TRANSFER_IN transactions
    # When set, this value is used as acquisition price instead of calculating
    # from source broker history. Enables "snapshot" architecture for transfers:
    # - Backend calculates PMC on source broker at transfer time
    # - Saves it here so destination broker never needs to query source history
    # - Can be manually overridden (e.g., Exit Tax, inheritances use market value)
    cost_basis_override: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(18, 6), nullable=True),
        description="Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis.",
    )

    # Currency code for cost_basis_override (ISO 4217 / crypto).
    # Always set together with cost_basis_override (both null or both non-null).
    cost_basis_currency: Optional[str] = Field(default=None, max_length=3, description="Currency code for cost_basis_override.")

    # Link to AssetEvent (global asset-level event realized in this portfolio).
    # NULL = stand-alone transaction. When set, validates that
    # asset_id == asset_event.asset_id (via service layer DB lookup) and
    # that transaction type is "event_compatible" (DIVIDEND, INTEREST, ADJUSTMENT).
    # ondelete=RESTRICT: event cannot be deleted while referenced by transactions.
    # This is consistent with Asset↔Transaction integrity policy (preserves user data).
    asset_event_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("asset_events.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        description="FK to AssetEvent this transaction realizes. RESTRICT on delete.",
    )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("currency", "cost_basis_currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> Optional[str]:
        """Validate currency against ISO 4217 + crypto. Allows None."""
        return _validate_currency_field(v)


# ============================================================================
# PRICE AND FX MODELS
# ============================================================================


class PriceHistory(SQLModel, table=True):
    """
    Daily price points for assets.

    Daily-point policy:
    - Exactly one record per (asset_id, date)
    - No intraday data
    - Upsert behavior: updates replace existing record for that day
    - For today: multiple updates allowed
    - For past dates: insert if missing, avoid overwrites
    """

    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_price_history_asset_date"),
        Index("idx_price_history_asset_date", "asset_id", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    asset_id: int = Field(foreign_key="assets.id", nullable=False)
    date: date_type = Field(nullable=False)

    open: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    high: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    low: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    close: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    volume: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(24, 0)))
    adjusted_close: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))

    currency: str = Field(nullable=False)  # ISO 4217
    source_plugin_key: str = Field(nullable=False)
    fetched_at: datetime = Field(default_factory=utcnow)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        """Validate currency against ISO 4217 + crypto."""
        return _validate_currency_field(v)


class AssetEvent(SQLModel, table=True):
    """
    Asset-level events that affect pricing or generate distributions.

    Source of truth: provider configuration (provider_params) or external API.
    Persisted in DB by sync layer for efficient querying.

    Events are NOT transactions — they describe what happens to the asset globally,
    not what happens in a user's portfolio. The portfolio reads these events
    for display, smart assistant suggestions, and ex-date price adjustments.

    No UniqueConstraint: auto-generated and manual events can coexist on the
    same (asset_id, date, type). Dedup is managed by provider_assignment_id
    (NULL = manual, non-NULL = auto-generated).
    """

    __tablename__ = "asset_events"
    __table_args__ = (
        Index("idx_asset_event_asset_date", "asset_id", "date"),
        Index("idx_asset_event_asset_type_date", "asset_id", "type", "date"),
        Index("idx_asset_event_provider_assignment", "provider_assignment_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", nullable=False)
    date: date_type = Field(nullable=False)
    type: AssetEventType = Field(nullable=False)
    value: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))
    currency: str = Field(nullable=False)
    provider_assignment_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("asset_provider_assignments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        description="FK to provider config that generated this event. NULL = user-created manual event.",
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        return _validate_currency_field(v)


class FxRate(SQLModel, table=True):
    """
    Daily foreign exchange rates.

    Daily-point policy:
    - Exactly one record per (date, base, quote)
    - No intraday data
    - Interpretation: 1 base = rate * quote
    - Reverse rate computed as 1/rate in services
    - Upsert behavior: same as PriceHistory

    Example: date='2025-01-15', base='EUR', quote='USD', rate=1.09
    Means: 1 EUR = 1.09 USD

    Important: To prevent duplicates (EUR/USD and USD/EUR both existing),
    we enforce base < quote alphabetically via CHECK constraint.
    Always store the pair in alphabetical order.
    """

    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("date", "base", "quote", name="uq_fx_rates_date_base_quote"),
        CheckConstraint("base < quote", name="ck_fx_rates_base_less_than_quote"),
        Index("idx_fx_rates_base_quote_date", "base", "quote", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    date: date_type = Field(nullable=False)
    base: str = Field(nullable=False)  # ISO 4217
    quote: str = Field(nullable=False)  # ISO 4217
    rate: Decimal = Field(sa_column=Column(Numeric(24, 10), nullable=False))

    source: str = Field(default="ECB")
    fetched_at: datetime = Field(default_factory=utcnow)

    @field_validator("base", "quote", mode="before")
    @classmethod
    def validate_currencies(cls, v: Any) -> str:
        """Validate base/quote against ISO 4217 + crypto."""
        return _validate_currency_field(v)


class FxConversionRoute(SQLModel, table=True):
    """
    Configuration table: conversion routes for FX currency pairs.

    Each route describes HOW to obtain the rate for a currency pair.
    Routes are stored as a chain of steps (chain_steps JSON):
    - 1-step chain = direct conversion (e.g., EUR→USD via ECB)
    - Multi-step chain = indirect conversion (e.g., RON→EUR→USD via ECB+ECB)

    The pair (base, quote) is always in alphabetical order (base < quote),
    consistent with fx_rates table.

    Priority field allows fallback routes:
    - priority=1: Primary route (used by default)
    - priority=2: Fallback route (if primary fails)
    - priority=3+: Additional fallbacks

    chain_steps JSON format:
    - 1-step: [{"from": "EUR", "to": "USD", "provider": "ECB"}]
    - Multi-step: [{"from": "RON", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "USD", "provider": "ECB"}]
    - MANUAL: [{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]
    """

    __tablename__ = "fx_conversion_routes"
    __table_args__ = (
        UniqueConstraint("base", "quote", "priority", name="uq_route_base_quote_priority"),
        CheckConstraint("base < quote", name="ck_route_base_less_than_quote"),
        Index("idx_route_base_quote", "base", "quote"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    base: str = Field(nullable=False, min_length=3, max_length=3, index=True)
    quote: str = Field(nullable=False, min_length=3, max_length=3, index=True)

    priority: int = Field(default=1, ge=1, description="Priority level (1=primary, 2=fallback, etc.)")

    chain_steps: str = Field(
        sa_column=Column(Text, nullable=False),
        description="JSON array of conversion steps [{from, to, provider}, ...]",
    )

    fetch_interval: Optional[int] = Field(default=None, ge=1, description="Fetch frequency in minutes (NULL = default 1440 = 24h)")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("base", "quote", mode="before")
    @classmethod
    def validate_currencies(cls, v: Any) -> str:
        """Validate base/quote against ISO 4217 + crypto."""
        return _validate_currency_field(v)

    @property
    def parsed_steps(self) -> list[dict]:
        """Parse chain_steps JSON string into a list of dicts."""
        return json.loads(self.chain_steps)

    @property
    def is_chain(self) -> bool:
        """True if this route has more than 1 step (multi-step chain)."""
        return len(self.parsed_steps) > 1

    @property
    def providers_used(self) -> set[str]:
        """Set of provider codes used in this route's chain."""
        return {step["provider"] for step in self.parsed_steps}


# ============================================================================
# ASSET PROVIDER ASSIGNMENT
# ============================================================================


class AssetProviderAssignment(SQLModel, table=True):
    """
    Asset provider assignment (1-to-1 relationship).

    This table assigns pricing providers to assets. Each asset can have
    at most one provider assigned for fetching current and historical prices.

    Fields:
    - identifier: How the provider identifies this asset (ticker, ISIN, UUID, URL, etc.)
    - identifier_type: Type of identifier (TICKER, ISIN, UUID, OTHER, etc.)
    - provider_params: JSON configuration specific to the provider

    Provider types and their configurations:

    1. yfinance (Yahoo Finance):
       - identifier: Stock ticker (e.g., "AAPL", "MSFT")
       - identifier_type: TICKER or ISIN
       - provider_params: {} or {"some_config": "value"}

    2. cssscraper (Custom CSS-based web scraper):
       - identifier: Full URL to scrape
       - identifier_type: URL
       - provider_params: {"selector": ".price", "currency": "EUR"}

    3. scheduled_investment (Synthetic yield calculator):
       - identifier: Auto-generated UUID
       - identifier_type: AUTO_GENERATED
       - provider_params: FAScheduledInvestmentSchedule JSON

    Notes:
    - provider_params validation is done by plugin's validate_params method
    - Each provider may support different identifier types
    - Relationship is 1-to-1 (one asset = one provider)
    """

    __tablename__ = "asset_provider_assignments"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_asset_provider_asset_id"),
        Index("idx_asset_provider_asset_id", "asset_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    asset_id: int = Field(
        foreign_key="assets.id",
        nullable=False,
        unique=True,
        description="Asset ID (1-to-1 relationship)",
    )
    provider_code: str = Field(
        max_length=50,
        nullable=False,
        description="Provider code (yfinance, cssscraper, scheduled_investment, etc.)",
    )
    identifier: Optional[str] = Field(
        default=None,
        nullable=True,
        description="Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.). NULL for AUTO_GENERATED providers.",
    )
    identifier_type: ProviderInputType = Field(nullable=False, description="Provider input type (TICKER, ISIN, URL, AUTO_GENERATED)")
    provider_params: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON configuration for provider (validated by plugin)",
    )
    last_fetch_at: Optional[datetime] = Field(default=None, description="Last fetch attempt timestamp (NULL = never fetched)")
    fetch_interval: Optional[int] = Field(default=None, description="Refresh frequency in minutes (NULL = default 1440 = 24h)")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# ============================================================================
# EVENT LISTENERS
# ============================================================================


@event.listens_for(Broker, "before_update")
@event.listens_for(Asset, "before_update")
@event.listens_for(Transaction, "before_update")
@event.listens_for(AssetProviderAssignment, "before_update")
@event.listens_for(FxConversionRoute, "before_update")
@event.listens_for(UserSettings, "before_update")
@event.listens_for(BrokerUserAccess, "before_update")
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp on update."""
    target.updated_at = utcnow()
