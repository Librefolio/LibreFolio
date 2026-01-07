"""
Database models for LibreFolio.

All models use SQLModel (SQLAlchemy 2.x) with the following conventions:
- Decimal columns use Numeric(18, 6) for precision
- Timestamps in UTC (created_at, updated_at, fetched_at)
- Daily-point policy: one record per day for prices and FX rates
- Foreign keys enforced with PRAGMA foreign_keys=ON
- Currency fields validated against ISO 4217 + crypto via Currency.validate_code()
"""
from datetime import date as date_type, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from pydantic import field_validator
from sqlalchemy import (
    Column,
    UniqueConstraint,
    Index,
    Numeric,
    Text,
    event,
    CheckConstraint,
    Integer,
    ForeignKey,
    )
from sqlmodel import Field, SQLModel, Relationship

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
    from backend.app.schemas.common import Currency
    return Currency.validate_code(v)


# ============================================================================
# ENUMS
# ============================================================================

class IdentifierType(str, Enum):
    """
    Asset identifier type.

    Usage: Specify which type of identifier is stored in the `identifier` field.

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


class AssetType(str, Enum):
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
    - OTHER: Any other asset type not listed above

    Impact:
    - Affects default valuation_model:
      - CROWDFUND_LOAN -> SCHEDULED_YIELD
      - HOLD -> MANUAL
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
    OTHER = "OTHER"


class TransactionType(str, Enum):
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

    Impact:
    - TRANSFER and FX_CONVERSION require related_transaction_id
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
    TRANSFER = "TRANSFER"
    FX_CONVERSION = "FX_CONVERSION"
    ADJUSTMENT = "ADJUSTMENT"


class UserRole(str, Enum):
    """
    User role for broker access control.

    - OWNER: Full access (create, read, update, delete)
    - VIEWER: Read-only access
    """
    OWNER = "OWNER"
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

    created_at: datetime = Field(default_factory=utcnow)


class UserSettings(SQLModel, table=True):
    """
    User preferences and settings.

    One-to-one relationship with User.
    """
    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_settings_user_id"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, unique=True)

    base_currency: str = Field(default="EUR", max_length=3)  # ISO 4217
    language: str = Field(default="en", max_length=5)  # e.g., "en", "it", "fr", "es"
    theme: str = Field(default="light", max_length=20)  # e.g., "light", "dark"

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator('base_currency', mode='before')
    @classmethod
    def validate_base_currency(cls, v: Any) -> str:
        """Validate base_currency against ISO 4217 + crypto."""
        return _validate_currency_field(v)


# ============================================================================
# BROKER MODELS
# ============================================================================


class Broker(SQLModel, table=True):
    """
    Broker/platform where assets are held.

    Examples: Interactive Brokers, Degiro, Recrowd, etc.

    Flags:
    - allow_cash_overdraft: If True, cash balance can go negative (margin trading)
    - allow_asset_shorting: If True, asset quantity can go negative (short selling)
    """
    __tablename__ = "brokers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    portal_url: Optional[str] = Field(default=None)

    # New flags for advanced trading scenarios
    allow_cash_overdraft: bool = Field(default=False, description="Allow negative cash balance")
    allow_asset_shorting: bool = Field(default=False, description="Allow negative asset quantities")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BrokerUserAccess(SQLModel, table=True):
    """
    Many-to-many relationship between Users and Brokers with role-based access.

    Defines which users can access which brokers and with what permissions.
    """
    __tablename__ = "broker_user_access"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_id", name="uq_broker_user_access"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    role: UserRole = Field(default=UserRole.VIEWER)

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

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        """Validate currency against ISO 4217 + crypto."""
        return _validate_currency_field(v)

    @field_validator('identifier_isin', mode='before')
    @classmethod
    def validate_identifier_isin(cls, v: Any) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == '':
            return None
        v = str(v).strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator('identifier_ticker', mode='before')
    @classmethod
    def validate_identifier_ticker(cls, v: Any) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == '':
            return None
        return str(v).strip().upper()

    @field_validator('classification_params')
    def validate_classification_params(cls, v):
        # Lazy import to avoid circular dependency
        from backend.app.schemas.assets import FAClassificationParams
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
        )

    id: Optional[int] = Field(default=None, primary_key=True)

    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    asset_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("assets.id"), nullable=True, index=True),
        description="Asset ID, NULL for pure cash transactions"
        )

    type: TransactionType = Field(nullable=False)
    date: date_type = Field(nullable=False, index=True, description="Settlement date")

    # Signed values: + in, - out. Default 0, NOT NULL for SUM calculations
    quantity: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 6), nullable=False, default=0),
        description="Asset quantity delta (+ in, - out)"
        )
    amount: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 6), nullable=False, default=0),
        description="Cash amount delta (+ in, - out)"
        )
    currency: Optional[str] = Field(
        default=None,
        max_length=3,
        description="ISO 4217 currency code, required if amount != 0"
        )

    # Link for paired transactions (TRANSFER, FX_CONVERSION)
    # BIDIRECTIONAL: Both transactions point to each other (A->B and B->A)
    # Uses DEFERRABLE INITIALLY DEFERRED FK - constraint checked only at COMMIT
    # This allows creating both records in the same transaction without FK violations
    related_transaction_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("transactions.id", deferrable=True, initially="DEFERRED"),
            nullable=True
            ),
        description="Links to paired transaction (for TRANSFER, FX_CONVERSION). Bidirectional."
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
        description="Comma-separated tags (e.g., 'tag1,tag2,tag3')"
        )

    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator('currency', mode='before')
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

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        """Validate currency against ISO 4217 + crypto."""
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

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def validate_currencies(cls, v: Any) -> str:
        """Validate base/quote against ISO 4217 + crypto."""
        return _validate_currency_field(v)


class FxCurrencyPairSource(SQLModel, table=True):
    """
    Configuration table: which FX provider to use for each currency pair.

    This table maps currency pairs to their authoritative data source.
    When syncing rates, the system queries this table to determine
    which provider (ECB, FED, BOE, etc.) should be used for each pair.

    Important: Pair direction is semantically significant!
    - EUR/USD (ECB base) ≠ USD/EUR (FED base)
    - Both directions can coexist with DIFFERENT priorities

    Examples:
    - EUR/USD priority=1 → ECB (European Central Bank, EUR base)
    - USD/EUR priority=2 → FED (Federal Reserve, USD base, fallback)
    - GBP/USD priority=1 → BOE (Bank of England, GBP base)
    - USD/GBP priority=2 → FED (Federal Reserve, USD base, fallback)

    Priority field allows fallback providers:
    - priority=1: Primary source (used by default)
    - priority=2: Fallback source (if primary fails)
    - priority=3+: Additional fallbacks

    Note: Unlike fx_rates table, this table does NOT enforce alphabetical ordering.
    The pair direction matters for selecting the correct provider's base currency.
    """
    __tablename__ = "fx_currency_pair_sources"
    __table_args__ = (
        UniqueConstraint("base", "quote", "priority", name="uq_pair_source_base_quote_priority"),
        Index("idx_pair_source_base_quote", "base", "quote"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)

    base: str = Field(nullable=False, min_length=3, max_length=3, index=True)
    quote: str = Field(nullable=False, min_length=3, max_length=3, index=True)

    provider_code: str = Field(nullable=False, description="Provider code (ECB, FED, BOE, etc.)")

    priority: int = Field(default=1, ge=1, description="Priority level (1=primary, 2=fallback, etc.)")

    fetch_interval: Optional[int] = Field(
        default=None,
        ge=1,
        description="Fetch frequency in minutes (NULL = default 1440 = 24h)"
        )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def validate_currencies(cls, v: Any) -> str:
        """Validate base/quote against ISO 4217 + crypto."""
        return _validate_currency_field(v)


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
       - identifier_type: OTHER
       - provider_params: {"selector": ".price", "currency": "EUR"}

    3. scheduled_investment (Synthetic yield calculator):
       - identifier: Asset ID as string or UUID
       - identifier_type: UUID
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
        description="Asset ID (1-to-1 relationship)"
        )

    provider_code: str = Field(
        max_length=50,
        nullable=False,
        description="Provider code (yfinance, cssscraper, scheduled_investment, etc.)"
        )

    identifier: str = Field(
        nullable=False,
        description="Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.)"
        )

    identifier_type: IdentifierType = Field(
        nullable=False,
        description="Type of identifier (TICKER, ISIN, UUID, OTHER, etc.)"
        )

    provider_params: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON configuration for provider (validated by plugin)"
        )

    last_fetch_at: Optional[datetime] = Field(
        default=None,
        description="Last fetch attempt timestamp (NULL = never fetched)"
        )

    fetch_interval: Optional[int] = Field(
        default=None,
        description="Refresh frequency in minutes (NULL = default 1440 = 24h)"
        )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# ============================================================================
# EVENT LISTENERS
# ============================================================================


@event.listens_for(Broker, "before_update")
@event.listens_for(Asset, "before_update")
@event.listens_for(Transaction, "before_update")
@event.listens_for(AssetProviderAssignment, "before_update")
@event.listens_for(FxCurrencyPairSource, "before_update")
@event.listens_for(UserSettings, "before_update")
@event.listens_for(BrokerUserAccess, "before_update")
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp on update."""
    target.updated_at = utcnow()
