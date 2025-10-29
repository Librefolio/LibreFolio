"""
Database models for LibreFolio.

All models use SQLModel (SQLAlchemy 2.x) with the following conventions:
- Decimal columns use Numeric(18, 6) for precision
- Timestamps in UTC (created_at, updated_at, fetched_at)
- Daily-point policy: one record per day for prices and FX rates
- Foreign keys enforced with PRAGMA foreign_keys=ON
"""
from datetime import date as date_type, datetime, timezone
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
    Date,
)
from sqlmodel import Field, SQLModel


# ============================================================================
# HELPERS
# ============================================================================


def utcnow() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


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
    - CROWDFUND_LOAN: Peer-to-peer lending or crowdfunding loans (e.g., Recrowd, Mintos)
    - OTHER: Any other asset type not listed above

    Impact:
    - Affects default valuation_model (CROWDFUND_LOAN typically uses SCHEDULED_YIELD)
    - Used for portfolio breakdown and allocation analysis
    - May influence available data plugins (e.g., crypto uses different sources)
    """
    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    CRYPTO = "CRYPTO"
    FUND = "FUND"
    CROWDFUND_LOAN = "CROWDFUND_LOAN"
    OTHER = "OTHER"


class ValuationModel(str, Enum):
    """
    Valuation model for assets.

    Usage: Determines how the asset's current value is calculated.

    - MARKET_PRICE: Uses market prices from price_history table
      When to use: Stocks, ETFs, crypto, traded bonds - any asset with a market price
      Requires: price_history records with daily prices
      Example: Apple stock valued at current market price

    - SCHEDULED_YIELD: Calculates value from interest_schedule
      When to use: Loans, P2P lending, non-traded bonds - assets with defined payment schedule
      Requires: face_value, maturity_date, interest_schedule fields populated
      Example: Recrowd loan valued by remaining principal + accrued interest

    Impact:
    - MARKET_PRICE → runtime service fetches latest price from price_history
    - SCHEDULED_YIELD → runtime service computes NPV from interest_schedule
    - Affects which data plugins are used (market data vs synthetic calculation)
    - Changes how portfolio value is computed in aggregation services
    """
    MARKET_PRICE = "MARKET_PRICE"
    SCHEDULED_YIELD = "SCHEDULED_YIELD"


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

    - BUY_SPEND: Cash spent on asset purchase
      When: Auto-created from BUY transaction
      Effect: ↓ cash balance
      Link: linked_transaction_id → BUY transaction
      Example: Spend €1500 to buy 10 shares (price €150 each)

    - SALE_PROCEEDS: Cash received from asset sale
      When: Auto-created from SELL transaction
      Effect: ↑ cash balance
      Link: linked_transaction_id → SELL transaction
      Example: Receive €3000 from selling 10 shares (price €300 each)

    - DIVIDEND_INCOME: Dividend payment received
      When: Auto-created from DIVIDEND transaction
      Effect: ↑ cash balance
      Link: linked_transaction_id → DIVIDEND transaction
      Example: Receive €50 dividend from stock holdings

    - INTEREST_INCOME: Interest payment received
      When: Auto-created from INTEREST transaction
      Effect: ↑ cash balance
      Link: linked_transaction_id → INTEREST transaction
      Example: Receive €20 monthly interest from loan

    - FEE: Fee/commission payment
      When: Auto-created from FEE transaction, or manual broker fees
      Effect: ↓ cash balance
      Link: linked_transaction_id → FEE transaction (if applicable)
      Example: Pay €5 monthly account maintenance fee

    - TAX: Tax payment
      When: Auto-created from TAX transaction, or manual tax payments
      Effect: ↓ cash balance
      Link: linked_transaction_id → TAX transaction (if applicable)
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
    - Auto-generated movements have linked_transaction_id set
    - Cash balance = sum(DEPOSIT, SALE_PROCEEDS, DIVIDEND_INCOME, INTEREST_INCOME, TRANSFER_IN)
                   - sum(WITHDRAWAL, BUY_SPEND, FEE, TAX, TRANSFER_OUT)
    - Used for cash reconciliation and liquidity analysis
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


class PayloadType(str, Enum):
    """
    Raw payload type for price data.

    Usage: Categorize raw JSON responses from data plugins for audit/debugging.

    - CURRENT: Response from fetching current/latest price
      When: Plugin fetches single current price point
      Example: Latest Bitcoin price from CoinGecko API
      Stored in: price_raw_payloads table

    - HISTORY: Response from fetching historical price data
      When: Plugin fetches price history (multiple dates)
      Example: Last 30 days of AAPL prices from Yahoo Finance
      Stored in: price_raw_payloads table

    Impact:
    - Used for debugging data plugin issues
    - Allows replay/reprocessing of raw data
    - Helps diagnose API changes or parsing errors
    """
    CURRENT = "current"
    HISTORY = "history"


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
    Asset definition with plugin bindings and loan schedule support.

    Per-function data source bindings:
    - current_data_plugin_key: Plugin for fetching current price
    - current_data_plugin_params: JSON params for current price plugin
    - history_data_plugin_key: Plugin for fetching price history
    - history_data_plugin_params: JSON params for history plugin

    Derived flags (computed in code):
    - allow_manual_current := (current_data_plugin_key is NULL)
    - allow_manual_history := (history_data_plugin_key is NULL)

    Loan/scheduled-yield fields (for CROWDFUND_LOAN, BOND, etc.):
    - face_value: Principal amount
    - maturity_date: When the loan matures
    - interest_schedule: JSON array of interest rate segments
    - late_interest: JSON object with late payment terms

    Interest schedule segment schema:
    {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD" or null,
      "annual_rate": 0.085,
      "compounding": "SIMPLE" or "COMPOUND",
      "compound_frequency": "DAILY" | "MONTHLY" | "ANNUAL",
      "day_count": "ACT/365" | "ACT/360" | "30/360"
    }

    Late interest schema:
    {
      "annual_rate": 0.12,
      "grace_days": 0
    }
    """
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)

    display_name: str = Field(nullable=False)
    identifier: str = Field(nullable=False, index=True)
    identifier_type: IdentifierType = Field(default=IdentifierType.OTHER)
    currency: str = Field(nullable=False)  # ISO 4217
    asset_type: AssetType = Field(default=AssetType.OTHER)

    # Valuation model
    valuation_model: ValuationModel = Field(default=ValuationModel.MARKET_PRICE)

    # Per-function plugin bindings
    current_data_plugin_key: Optional[str] = Field(default=None)
    current_data_plugin_params: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    history_data_plugin_key: Optional[str] = Field(default=None)
    history_data_plugin_params: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON

    # Loan / scheduled-yield fields
    face_value: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    maturity_date: Optional[date_type] = Field(default=None)
    interest_schedule: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON array
    late_interest: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON object

    active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Transaction(SQLModel, table=True):
    """
    Unified asset transaction record.

    Quantity rules:
    - BUY, SELL, ADD_HOLDING, REMOVE_HOLDING, TRANSFER_IN, TRANSFER_OUT: quantity > 0
    - DIVIDEND, INTEREST, FEE, TAX: quantity = 0

    Price rules:
    - BUY, SELL: price = unit price
    - DIVIDEND, INTEREST: price = total amount
    - ADD_HOLDING, REMOVE_HOLDING: price optional
    - FEE, TAX: price = amount

    Cash impact (auto-generates cash_movements):
    - BUY → BUY_SPEND
    - SELL → SALE_PROCEEDS
    - DIVIDEND → DIVIDEND_INCOME
    - INTEREST → INTEREST_INCOME
    - FEE → FEE
    - TAX → TAX
    """
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_asset_broker_date", "asset_id", "broker_id", "trade_date", "id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    asset_id: int = Field(foreign_key="assets.id", nullable=False, index=True)
    broker_id: int = Field(foreign_key="brokers.id", nullable=False, index=True)
    type: TransactionType = Field(nullable=False)

    quantity: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))
    price: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    currency: str = Field(nullable=False)  # ISO 4217

    fees: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))
    taxes: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(18, 6)))

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


class PriceRawPayload(SQLModel, table=True):
    """
    Raw JSON payloads from price data plugins.

    Used for debugging and audit trail.
    """
    __tablename__ = "price_raw_payloads"

    id: Optional[int] = Field(default=None, primary_key=True)

    asset_id: int = Field(foreign_key="assets.id", nullable=False, index=True)
    payload_type: PayloadType = Field(nullable=False)
    raw_json: str = Field(sa_column=Column(Text, nullable=False))
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

    Example: date=2025-01-15, base=EUR, quote=USD, rate=1.09
    Means: 1 EUR = 1.09 USD
    """
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("date", "base", "quote", name="uq_fx_rates_date_base_quote"),
        Index("idx_fx_rates_base_quote_date", "base", "quote", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    date: date_type = Field(nullable=False)
    base: str = Field(nullable=False)  # ISO 4217
    quote: str = Field(nullable=False)  # ISO 4217
    rate: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))

    source: str = Field(default="ECB")
    fetched_at: datetime = Field(default_factory=utcnow)


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

    Types:
    - Manual: DEPOSIT, WITHDRAWAL
    - Auto-generated: BUY_SPEND, SALE_PROCEEDS, DIVIDEND_INCOME, INTEREST_INCOME, FEE, TAX
    - Transfer: TRANSFER_IN, TRANSFER_OUT

    Amount is always positive (direction implied by type).
    linked_transaction_id set when auto-generated from asset transaction.
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
    note: Optional[str] = Field(default=None, sa_column=Column(Text))
    linked_transaction_id: Optional[int] = Field(
        default=None,
        foreign_key="transactions.id",
        index=True
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
def receive_before_update(mapper, connection, target):
    """Update updated_at timestamp on update."""
    target.updated_at = utcnow()

