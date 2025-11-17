"""
Database models for LibreFolio.

All models use SQLModel (SQLAlchemy 2.x) with the following conventions:
- Decimal columns use Numeric(18, 6) for precision
- Timestamps in UTC (created_at, updated_at, fetched_at)
- Daily-point policy: one record per day for prices and FX rates
- Foreign keys enforced with PRAGMA foreign_keys=ON
"""
from datetime import date as date_type, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

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
from sqlmodel import Field, SQLModel

from backend.app.utils.datetime_utils import utcnow


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
    - HOLD: Assets without automatic market pricing (real estate, art, collectibles, unlisted companies)
    - OTHER: Any other asset type not listed above
    - Affects default valuation_model:
      - CROWDFUND_LOAN -> SCHEDULED_YIELD
      - HOLD -> MANUAL
      - Others -> MARKET_PRICE
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


class ValuationModel(str, Enum):
    """
    Valuation model for assets.

    Usage: Determines how the asset's current value is calculated.

    - MARKET_PRICE: Uses market prices from price_history table
      When to use: Stocks, ETFs, crypto, traded bonds - any asset with a market price
      Requires: price_history records with daily prices
      Example: Apple stock valued at current market price
    - SCHEDULED_YIELD: Computes NPV from interest_schedule for loans/bonds
      When to use: Crowdfunding loans, bonds with fixed schedules
      Requires: interest_schedule JSON with payment terms
      Example: Recrowd loan valued by remaining principal + accrued interest
    - MANUAL: User-provided valuations only
      When to use: Assets without market prices (real estate, art, unlisted companies, collectibles)
      Requires: User manually enters prices in price_history (source_plugin_key="manual")
      Default value: Purchase price from first BUY transaction
      Example: Private company shares, real estate property, art collection
      Note: User can update valuation anytime by adding new price_history record

    Impact:
    - MARKET_PRICE -> runtime service fetches latest price from price_history (automated)
    - SCHEDULED_YIELD -> runtime service computes NPV from interest_schedule (calculated)
    - MANUAL -> runtime service uses latest price_history with source="manual", if not set by user, use last Buy transaction (user-provided)
    - Affects which data plugins are used (market data vs synthetic vs manual)
    - Changes how portfolio value is computed in aggregation services
    """
    MARKET_PRICE = "MARKET_PRICE"
    SCHEDULED_YIELD = "SCHEDULED_YIELD"
    MANUAL = "MANUAL"


class TransactionType(str, Enum):
    """
    Asset transaction types.

    Usage: Record all asset-related events that affect holdings or generate cash.

    == Quantity-affecting transactions (quantity > 0, require oversell guard) ==

    - BUY: Purchase asset with cash
      When: Buy stocks, ETF, crypto, etc.
      Effect: ↑ quantity, ↓ cash (auto-generates BUY_SPEND movement)
      Example: Buy 10 shares of AAPL at €150 each

    - SELL: Sell asset for cash
      When: Sell holdings to realize gains/losses
      Effect: ↓ quantity, ↑ cash (auto-generates SALE_PROCEEDS movement)
      Example: Sell 5 shares of MSFT at €300 each

    - TRANSFER_IN: Receive asset from another broker
      When: Transfer stocks from Broker A to Broker B (receiving side)
      Effect: ↑ quantity, no cash impact
      Example: Transfer 100 shares of VWCE from Degiro to Interactive Brokers

    - TRANSFER_OUT: Send asset to another broker
      When: Transfer stocks from Broker A to Broker B (sending side)
      Effect: ↓ quantity, no cash impact
      Example: Transfer 50 shares of BTC from Coinbase to hardware wallet

    - ADD_HOLDING: Add asset without purchase
      When: Gifts, airdrops, stock splits, inheritance
      Effect: ↑ quantity, no cash impact
      Example: Receive 10 shares as a gift

    - REMOVE_HOLDING: Remove asset without sale
      When: Lost access, delisting, worthless assets, donations
      Effect: ↓ quantity, no cash impact
      Example: Crypto lost due to exchange bankruptcy

    == Cash-only transactions (quantity = 0, no oversell check) ==

    - DIVIDEND: Receive dividend payment
      When: Company pays dividend on held shares
      Effect: No quantity change, ↑ cash (auto-generates DIVIDEND_INCOME movement)
      Example: Receive €50 dividend from AAPL holdings

    - INTEREST: Receive interest payment
      When: Loan repayment, bond coupon, savings interest
      Effect: No quantity change, ↑ cash (auto-generates INTEREST_INCOME movement)
      Example: Monthly interest payment from Recrowd loan

    - FEE: Standalone fee/commission
      When: Management fee, transaction fee not part of buy/sell
      Effect: No quantity change, ↓ cash (auto-generates FEE movement)
      Example: €5 monthly custody fee

    - TAX: Standalone tax payment
      When: Capital gains tax, dividend tax, stamp duty
      Effect: No quantity change, ↓ cash (auto-generates TAX movement)
      Example: €100 capital gains tax payment

    Impact:
    - All transactions that change quantity are subject to oversell validation
    - BUY, SELL, DIVIDEND, INTEREST, FEE, TAX auto-generate cash_movements
    - FIFO gain/loss calculation uses BUY, SELL, ADD_HOLDING, REMOVE_HOLDING
    - Portfolio value calculation uses all quantity-affecting transactions
    """
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADD_HOLDING = "ADD_HOLDING"
    REMOVE_HOLDING = "REMOVE_HOLDING"
    FEE = "FEE"
    TAX = "TAX"


class CashMovementType(str, Enum):
    """
    Cash movement types.

    Usage: Track all cash inflows and outflows in broker accounts.

    == Manual movements (created by user) ==

    - DEPOSIT: Add funds to broker account
      When: Bank transfer to broker, initial funding
      Effect: ↑ cash balance
      Example: Transfer €1000 from bank to Interactive Brokers

    - WITHDRAWAL: Remove funds from broker account
      When: Transfer money back to bank, cash out
      Effect: ↓ cash balance
      Example: Withdraw €500 from Degiro to personal bank account

    == Auto-generated movements (linked to asset transactions) ==

    Note: The relationship with Transaction is unidirectional (Transaction -> CashMovement).
    To find the Transaction that created a CashMovement, query:
        SELECT * FROM transactions WHERE cash_movement_id = <cash_movement.id>

    - BUY_SPEND: Cash spent on asset purchase
      When: Auto-created from BUY transaction
      Effect: ↓ cash balance
      Example: Spend €1500 to buy 10 shares (price €150 each)

    - SALE_PROCEEDS: Cash received from asset sale
      When: Auto-created from SELL transaction
      Effect: ↑ cash balance
      Example: Receive €3000 from selling 10 shares (price €300 each)

    - DIVIDEND_INCOME: Dividend payment received
      When: Auto-created from DIVIDEND transaction
      Effect: ↑ cash balance
      Example: Receive €50 dividend from stock holdings

    - INTEREST_INCOME: Interest payment received
      When: Auto-created from INTEREST transaction
      Effect: ↑ cash balance
      Example: Receive €20 monthly interest from loan

    - FEE: Fee/commission payment
      When: Auto-created from FEE transaction, or manual broker fees
      Effect: ↓ cash balance
      Example: Pay €5 monthly account maintenance fee

    - TAX: Tax payment
      When: Auto-created from TAX transaction, or manual tax payments
      Effect: ↓ cash balance
      Example: Pay €100 capital gains tax

    == Transfer movements (between brokers) ==

    - TRANSFER_IN: Receive cash from another broker
      When: Transfer money between broker accounts
      Effect: ↑ cash balance
      Example: Transfer €1000 from Degiro to Interactive Brokers

    - TRANSFER_OUT: Send cash to another broker
      When: Transfer money between broker accounts
      Effect: ↓ cash balance
      Example: Transfer €1000 from Interactive Brokers to Degiro

    Impact:
    - All amounts are positive (direction implied by type)
    - Cash balance = sum(DEPOSIT, SALE_PROCEEDS, DIVIDEND_INCOME, INTEREST_INCOME, TRANSFER_IN)
                    - sum(WITHDRAWAL, BUY_SPEND, FEE, TAX, TRANSFER_OUT)
    """
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY_SPEND = "BUY_SPEND"
    SALE_PROCEEDS = "SALE_PROCEEDS"
    DIVIDEND_INCOME = "DIVIDEND_INCOME"
    INTEREST_INCOME = "INTEREST_INCOME"
    FEE = "FEE"
    TAX = "TAX"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT = {
    TransactionType.BUY: CashMovementType.BUY_SPEND,
    TransactionType.SELL: CashMovementType.SALE_PROCEEDS,
    TransactionType.DIVIDEND: CashMovementType.DIVIDEND_INCOME,
    TransactionType.INTEREST: CashMovementType.INTEREST_INCOME,
    TransactionType.FEE: CashMovementType.FEE,
    TransactionType.TAX: CashMovementType.TAX,
}

# Helper to generate SQL IN clause for CHECK constraint
CASH_REQUIRED_TYPES_SQL = ", ".join(f"'{t.value}'" for t in TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT.keys())


# ============================================================================
# MODELS
# ============================================================================


class Broker(SQLModel, table=True):
    """
    Broker/platform where assets are held.

    Examples: Interactive Brokers, Degiro, Recrowd, etc.
    """
    __tablename__ = "brokers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    portal_url: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Asset(SQLModel, table=True):
    """
    Asset definition with interest schedule support for scheduled-yield assets.

    Provider assignments:
    - Use asset_provider_assignments table (1-to-1 relationship)
    - Each asset can have at most one provider for pricing data
    - Provider handles both current and historical data fetching

    Scheduled-yield fields (for CROWDFUND_LOAN, BOND, etc.):
    - interest_schedule: JSON containing complete ScheduledInvestmentSchedule

    The interest_schedule JSON should conform to ScheduledInvestmentSchedule schema:
    {
      "schedule": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "annual_rate": 0.085,
          "compounding": "SIMPLE" | "COMPOUND",
          "compound_frequency": "DAILY" | "MONTHLY" | "QUARTERLY" | "SEMIANNUAL" | "ANNUAL" | "CONTINUOUS",
          "day_count": "ACT/365" | "ACT/360" | "ACT/ACT" | "30/360"
        },
        ...
      ],
      "late_interest": {
        "annual_rate": 0.12,
        "grace_period_days": 30,
        "compounding": "SIMPLE",
        "day_count": "ACT/365"
      }
    }

    Notes:
    - face_value (principal) is calculated from transactions (BUY - SELL)
    - maturity_date is the last period's end_date in the schedule
    - Validation is done via ScheduledInvestmentSchedule Pydantic model
    """
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)

    display_name: str = Field(nullable=False)
    identifier: str = Field(nullable=False, index=True)
    identifier_type: IdentifierType = Field(default=IdentifierType.OTHER)
    currency: str = Field(nullable=False, description="Asset original currency")  # ISO 4217
    asset_type: AssetType = Field(default=AssetType.OTHER)

    # Valuation model
    valuation_model: ValuationModel = Field(default=ValuationModel.MARKET_PRICE)

    # Scheduled-yield configuration (JSON)
    # Should contain ScheduledInvestmentSchedule structure
    # Validated when loaded using ScheduledInvestmentSchedule(**json.loads(interest_schedule))
    interest_schedule: Optional[str] = Field(default=None, sa_column=Column(Text))

    active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Transaction(SQLModel, table=True):
    """
    Unified asset transaction record.

    Dates:
    - trade_date: When the order was executed (optional, informational)
    - settlement_date: When the transaction was settled (REQUIRED for calculations)

    ⚠️ IMPORTANT: All portfolio calculations MUST use settlement_date, not trade_date.

    In financial transactions:
    - trade_date: The date when the order is executed (e.g., buy/sell order placed)
    - settlement_date: The date when the transaction is actually settled (money/securities transfer)

    Example (Directa CSV import):
    - "Data operazione" (Operation date) → trade_date
    - "Data valuta" (Value date) → settlement_date

    For manual entries without trade_date, set trade_date = settlement_date.

    Quantity rules:
    - BUY, SELL, ADD_HOLDING, REMOVE_HOLDING, TRANSFER_IN, TRANSFER_OUT: quantity > 0
    - DIVIDEND, INTEREST, FEE, TAX: quantity = 0

    Price rules:
    - BUY, SELL: price = unit price
    - DIVIDEND, INTEREST: price = total amount
    - ADD_HOLDING, REMOVE_HOLDING: price optional
    - FEE, TAX: price = amount

    Cash impact (auto-generates cash_movements):
    - BUY -> BUY_SPEND
    - SELL -> SALE_PROCEEDS
    - DIVIDEND -> DIVIDEND_INCOME
    - INTEREST -> INTEREST_INCOME
    - FEE -> FEE
    - TAX -> TAX
    """
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_asset_broker_date", "asset_id", "broker_id", "trade_date", "id"),
        CheckConstraint(
            f"""
            (type IN ({CASH_REQUIRED_TYPES_SQL}) AND cash_movement_id IS NOT NULL)
            OR
            (type NOT IN ({CASH_REQUIRED_TYPES_SQL}) AND cash_movement_id IS NULL)
            """,
            name="ck_transaction_cash_movement_required"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    asset_id: int = Field(foreign_key="assets.id", nullable=False, index=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    type: TransactionType = Field(nullable=False)

    quantity: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))
    price: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    currency: str = Field(nullable=False)  # ISO 4217

    # Unidirectional relationship: Transaction -> CashMovement
    # ON DELETE CASCADE ensures that deleting the CashMovement also delete the Transaction that references it
    cash_movement_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("cash_movements.id", ondelete="CASCADE"),
            index=True,
            nullable=True
        ),
        description="ID del movimento di cassa associato (unidirectional: Transaction -> CashMovement)"
    )

    trade_date: date_type = Field(nullable=False, index=True)
    settlement_date: Optional[date_type] = Field(default=None)
    note: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


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
    adjusted_close: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))

    currency: str = Field(nullable=False)  # ISO 4217
    source_plugin_key: str = Field(nullable=False)
    fetched_at: datetime = Field(default_factory=utcnow)


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
    rate: Decimal = Field(sa_column=Column(Numeric(24, 10), nullable=False))  # 14 integer digits, 10 decimal places

    source: str = Field(default="ECB")
    fetched_at: datetime = Field(default_factory=utcnow)


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

    Validation Constraint (enforced in API, not DB):
    Inverse pairs (e.g., EUR/USD and USD/EUR) MUST have different priorities.
    - ✅ OK: EUR/USD priority=1 + USD/EUR priority=2
    - ❌ CONFLICT: EUR/USD priority=1 + USD/EUR priority=1

    This constraint is validated in POST /fx/pair-sources/bulk endpoint
    to provide better error messages than a DB constraint would.

    Note: Unlike fx_rates table, this table does NOT enforce alphabetical ordering.
    The pair direction matters for selecting the correct provider's base currency.
    """
    __tablename__ = "fx_currency_pair_sources"
    __table_args__ = (
        UniqueConstraint("base", "quote", "priority", name="uq_pair_source_base_quote_priority"),
        # Note: NO CHECK constraint for "base < quote" - direction is semantically significant
        Index("idx_pair_source_base_quote", "base", "quote"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)

    # Currency pair (alphabetically ordered)
    base: str = Field(nullable=False, min_length=3, max_length=3, index=True)
    quote: str = Field(nullable=False, min_length=3, max_length=3, index=True)

    # Provider configuration
    provider_code: str = Field(
        nullable=False,
        description="Provider code (ECB, FED, BOE, etc.)"
        )

    priority: int = Field(
        default=1,
        ge=1,
        description="Priority level (1=primary, 2=fallback, etc.)"
        )

    fetch_interval: Optional[int] = Field(
        default=None,
        ge=1,
        description="Fetch frequency in minutes (NULL = default 1440 = 24h)"
        )

    # Metadata
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CashAccount(SQLModel, table=True):
    """
    Cash account per broker and currency.

    Each broker can have multiple cash accounts (one per currency).
    Balance computed at runtime from cash_movements.
    """
    __tablename__ = "cash_accounts"
    __table_args__ = (
        UniqueConstraint("broker_id", "currency", name="uq_cash_accounts_broker_currency"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)

    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    currency: str = Field(nullable=False)  # ISO 4217
    display_name: str = Field(nullable=False)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CashMovement(SQLModel, table=True):
    """
    Cash movement record.

    Dates:
    - trade_date: When the cash movement was initiated (REQUIRED)
    - settlement_date: When the cash movement was settled (optional, defaults to trade_date)

    For consistency with Transaction model, calculations should use settlement_date when available.

    Types:
    - Manual: DEPOSIT, WITHDRAWAL
    - Auto-generated: BUY_SPEND, SALE_PROCEEDS, DIVIDEND_INCOME, INTEREST_INCOME, FEE, TAX
    - Transfer: TRANSFER_IN, TRANSFER_OUT

    Amount is always positive (direction implied by type).

    Note: The relationship with Transaction is unidirectional.
    Use Transaction.cash_movement_id to link a Transaction to its CashMovement.
    To find the Transaction that created a CashMovement, query:
        SELECT * FROM transactions WHERE cash_movement_id = <cash_movement.id>
    """
    __tablename__ = "cash_movements"
    __table_args__ = (
        Index("idx_cash_movements_account_date", "cash_account_id", "trade_date", "id"),
        )

    id: Optional[int] = Field(default=None, primary_key=True)

    cash_account_id: int = Field(foreign_key="cash_accounts.id", nullable=False, index=True)
    type: CashMovementType = Field(nullable=False)
    amount: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))

    trade_date: date_type = Field(nullable=False, index=True)
    settlement_date: Optional[date_type] = Field(
        default=None,
        description="Settlement date (defaults to trade_date if not provided)"
    )
    note: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AssetProviderAssignment(SQLModel, table=True):
    """
    Asset provider assignment (1-to-1 relationship).

    This table assigns pricing providers to assets. Each asset can have
    at most one provider assigned for fetching current and historical prices.

    Provider types:
    - yfinance: Yahoo Finance for stocks/ETFs/funds
    - cssscraper: Custom CSS-based web scraper
    - (future): Alpha Vantage, Polygon.io, custom providers

    Special cases:
    - Assets with valuation_model=MANUAL: No provider assignment needed
    - Assets with valuation_model=SCHEDULED_YIELD: No provider assignment needed
      (values calculated runtime from interest_schedule)
    - Assets with valuation_model=MARKET_PRICE: Provider assignment recommended

    provider_params: JSON configuration for the provider
    Example (yfinance): {"identifier": "AAPL", "type": "Stock"}
    Example (cssscraper): {"url": "https://...", "selector": ".price", "currency": "EUR"}
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
        description="Provider code (yfinance, cssscraper, etc.)"
        )

    provider_params: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON configuration for provider"
        )

    last_fetch_at: Optional[datetime] = Field(
        default=None,
        description="Last fetch attempt timestamp (NULL = never fetched, updated on every fetch)"
        )

    fetch_interval: Optional[int] = Field(
        default=None,
        description="Refresh frequency in minutes (NULL = default 1440 = 24h). Used by scheduled refresh system."
        )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# ============================================================================
# EVENT LISTENERS
# ============================================================================


@event.listens_for(Broker, "before_update")
@event.listens_for(Asset, "before_update")
@event.listens_for(Transaction, "before_update")
@event.listens_for(CashAccount, "before_update")
@event.listens_for(CashMovement, "before_update")
@event.listens_for(AssetProviderAssignment, "before_update")
@event.listens_for(FxCurrencyPairSource, "before_update")
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp on update."""
    target.updated_at = utcnow()
