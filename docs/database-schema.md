# LibreFolio Database Schema Documentation

**Version**: 2.0  
**Last Updated**: November 6, 2025  
**Schema Migration**: 001_initial (squashed from 9 migrations)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Tables Reference](#tables-reference)
4. [Relationships](#relationships)
5. [Common Scenarios](#common-scenarios)
6. [Example Data](#example-data)

---

## Overview

LibreFolio uses a relational database schema to track investments across multiple brokers. The schema is designed around these key principles:

- **Multi-broker support**: Track assets across different platforms
- **Multi-currency**: Handle FX rates and currency conversions
- **Transaction integrity**: Every asset transaction has corresponding cash movements
- **Daily-point policy**: One price/FX rate per day (no intraday data)
- **Flexible valuation**: Support both market-priced and scheduled-yield assets

---

## Core Concepts

### What the Database Abstracts

**✅ The database represents:**
- Financial **brokers/platforms** where you hold assets (e.g., Interactive Brokers, Degiro, Directa, Fineco)
- **Assets** you own (stocks, ETFs, bonds, loans)
- **Transactions** on those assets (buy, sell, dividends, etc.)
- **Cash accounts** within each broker (isolated per broker and currency)
- **Market prices** for assets over time
- **FX rates** for currency conversion

**❌ The database does NOT represent:**
- Your **personal bank account** (external to the system)
- **Physical cash** in your wallet
- **Credit cards** or loans from banks
- **Real estate** or other non-financial assets
- **Tax calculations** (only records tax payments)

### Key Design Decisions

1. **Broker isolation**: Each broker is completely isolated from others; you cannot move assets or cash between brokers without explicit transfer transaction
2. **Cash accounts per currency**: A broker can have multiple cash accounts (EUR, USD, GBP, etc.)
3. **Transaction-driven**: All changes tracked through transactions, never direct balance updates
4. **Daily granularity**: Prices and FX rates stored once per day, not intraday

---

## Tables Reference

### 1. `brokers` - Trading Platforms

**What it abstracts:**
The financial platforms or brokers where you hold your investments.

**Examples:**
- Interactive Brokers (multi-asset broker)
- Degiro (European stock broker)
- Recrowd (P2P lending platform)
- Coinbase (crypto exchange)

**What it does NOT abstract:**
- Your personal bank (e.g., Chase, Barclays) - banks are external
- Payment processors (PayPal, Stripe)
- Employers (for stock compensation)

**Schema:**
```sql
CREATE TABLE brokers (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- "Interactive Brokers", "Degiro"
    description TEXT,                    -- Optional details
    portal_url TEXT,                     -- Link to broker's website
    created_at DATETIME,
    updated_at DATETIME
);
```

**Key points:**
- One record per broker/platform you use
- Name must be unique
- Used to organize your portfolio by platform

---

### 2. `assets` - Financial Instruments

**What it abstracts:**
Financial instruments you can own and trade.

**Examples:**
- Stocks: Apple (AAPL), Microsoft (MSFT)
- ETFs: Vanguard All-World (VWCE)
- Crypto: Bitcoin, Ethereum
- Bonds: Government or corporate bonds
- P2P Loans: Crowdfunding loans with scheduled repayments
- HOLD assets: Real estate properties, art collections, unlisted company shares, physical gold

**What it does NOT abstract:**
- Nothing - any asset can be tracked! Use asset_type=HOLD for assets without automatic market pricing

**Schema:**
```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    display_name VARCHAR NOT NULL,       -- "Apple Inc."
    identifier VARCHAR NOT NULL,         -- "AAPL"
    identifier_type VARCHAR(6),          -- TICKER, ISIN, UUID, etc.
    currency VARCHAR NOT NULL,           -- "USD", "EUR"
    asset_type VARCHAR(14),              -- STOCK, ETF, BOND, CRYPTO, CROWDFUND_LOAN, HOLD
    
    -- Valuation method
    valuation_model VARCHAR(15),         -- MARKET_PRICE, SCHEDULED_YIELD, or MANUAL
    
    -- For loans/bonds with scheduled payments
    face_value NUMERIC(18,6),            -- Principal amount
    maturity_date DATE,                  -- When it matures
    interest_schedule TEXT,              -- JSON: [{rate, period, ...}]
    late_interest TEXT,                  -- JSON: {rate, grace_days}
    
    active BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Provider configuration moved to separate table (see asset_provider_assignments)
CREATE INDEX ix_assets_identifier ON assets (identifier);
```

**⚠️ Important Change**: Provider configuration (formerly `*_plugin_*` fields) is now in the `asset_provider_assignments` table (1-to-1 relationship).

**Key points:**
- One record per unique asset
- `valuation_model`:
  - `MARKET_PRICE`: Value based on market prices (stocks, ETFs, crypto)
  - `SCHEDULED_YIELD`: Value based on payment schedule (loans, some bonds)
  - `MANUAL`: User-provided valuations (real estate, art, unlisted companies)
- **Provider configuration**: Moved to `asset_provider_assignments` table (see below)
  - 1-to-1 optional relationship
  - Stores provider code and parameters for automatic pricing

**Valuation model details:**
- **MARKET_PRICE**: Asset price fetched automatically from data sources (yfinance, APIs, plugins developed later by the community)
- **SCHEDULED_YIELD**: Asset value calculated from `interest_schedule` (see below)
- **MANUAL**: No automatic pricing. Value defaults to purchase price from first BUY transaction. User can manually update by adding price_history records with `source_plugin_key="manual"`

**Interest schedule JSON (for SCHEDULED_YIELD assets):**
```json
[
  {
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "annual_rate": 0.085,
    "compounding": "SIMPLE",
    "compound_frequency": "MONTHLY",
    "day_count": "ACT/365"
  },
  {
    "start_date": "2026-01-01", // Note the start date is the day after previous end_date
    "end_date": "2026-12-31",
    "annual_rate": 0.095,
    "compounding": "SIMPLE",
    "compound_frequency": "MONTHLY",
    "day_count": "ACT/365"
  }
]
```
**Why is it a list?** Interest rates can change over the loan lifetime. For example, a loan might have 8.5% APR for the first year, then 9.5% APR for the second year. Each period is a separate element in the array.

[//]: # (TODO: creare la Interest Calculation Guide)
The fields of each object is documented in detail in the [Interest Calculation Guide](docs/interest-calculation.md).

**Late interest JSON (for SCHEDULED_YIELD assets):**
```json
{
  "annual_rate": 0.12,
  "grace_days": 0
}
```
**Why is it NOT a list?** Late interest policy is typically uniform across the entire loan lifetime. If a payment is late, this single policy applies regardless of which payment period is late.

[//]: # (TODO: creare la Interest Calculation Guide)
The fields are documented in detail in the [Interest Calculation Guide](docs/interest-calculation.md).

**Important distinction:**
- An asset definition (AAPL) is **global** - defined once
- Holdings of that asset are tracked via **transactions** per broker

---

### 3. `cash_accounts` - Cash Within Brokers

**What it abstracts:**
Cash balances held **inside** each broker, per currency.

**Examples:**
- EUR cash in your Degiro account
- USD cash in your Interactive Brokers account
- USD cash in your Degiro account (separate from IB!)

**What it does NOT abstract:**
- Your personal bank account (e.g., Chase checking account)
- Cash in your physical wallet
- Money in transit between bank and broker

**Schema:**
```sql
CREATE TABLE cash_accounts (
    id INTEGER PRIMARY KEY,
    broker_id INTEGER NOT NULL,          -- FK to brokers
    currency TEXT NOT NULL,              -- "EUR", "USD", "GBP"
    display_name TEXT NOT NULL,          -- "Degiro EUR Account"
    created_at DATETIME,
    updated_at DATETIME,
    UNIQUE(broker_id, currency)          -- One account per broker per currency
);
```

**Key points:**
- **Broker-specific**: Each cash account is conected with only one broker, to transfert money from one broker to another, need to create a cash_transaction
- **One per currency**: A broker can have multiple cash accounts (EUR, USD, etc.)
- **Balance computed at runtime**: Sum of cash_movements, never stored directly (to allow out-of-order entries)

**Example scenario:**
```
You have:
- 1,000 EUR in Degiro
- 5,000 EUR in Interactive Brokers
- 2,000 USD in Interactive Brokers

This creates 3 cash_accounts:
1. broker_id=Degiro, currency=EUR   → balance: 1,000 EUR
2. broker_id=IB, currency=EUR       → balance: 5,000 EUR
3. broker_id=IB, currency=USD       → balance: 2,000 USD
```

**Important: Why isolated per broker?**
- Each broker is a separate institution
- You can't spend Degiro EUR to buy stocks on Interactive Brokers
- Transfers between brokers require explicit TRANSFER_OUT/IN transactions

---

### 4. `transactions` - Asset Movements

**What it abstracts:**
Any event that changes your asset holdings or generates cash flow.

**Examples:**
- Buying 10 shares of AAPL
- Selling 5 shares of MSFT
- Receiving a dividend payment
- Getting interest from a loan
- Transferring assets between brokers
- Recording a gift of shares

**What it does NOT abstract:**
- Pure cash movements without assets (use cash_movements directly)
- Broker fees unrelated to specific transactions
- Currency exchange (handled via FX rates)

**Schema:**
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,           -- FK to assets
    broker_id INTEGER NOT NULL,          -- FK to brokers
    type TEXT NOT NULL,                  -- BUY, SELL, DIVIDEND, INTEREST, etc.
    
    quantity DECIMAL(18,6) NOT NULL,     -- Amount of asset (>0 for most, =0 for cash-only)
    price DECIMAL(18,6),                 -- Price per unit (BUY/SELL) or total amount (DIVIDEND)
    currency TEXT NOT NULL,              -- Transaction currency
    
    cash_movement_id INTEGER,            -- FK to cash_movements (ON DELETE CASCADE)
    
    trade_date DATE NOT NULL,            -- When order was executed (informational)
    settlement_date DATE,                -- When settled (REQUIRED for calculations)
    note TEXT,
    
    created_at DATETIME,
    updated_at DATETIME,
    
    -- CHECK constraint ensures types that require cash have it
    CHECK (
        (type IN ('BUY', 'SELL', 'DIVIDEND', 'INTEREST', 'FEE', 'TAX') AND cash_movement_id IS NOT NULL)
        OR
        (type NOT IN ('BUY', 'SELL', 'DIVIDEND', 'INTEREST', 'FEE', 'TAX') AND cash_movement_id IS NULL)
    )
);
```

**Important notes on dates:**
- **trade_date**: When the order was executed (optional, informational) - e.g., "Data operazione" in Directa CSV
- **settlement_date**: When the transaction was actually settled - e.g., "Data valuta" in Directa CSV
- ⚠️ **All portfolio calculations MUST use settlement_date**, not trade_date
- For manual entries without trade_date, set trade_date = settlement_date

**Transaction types and their effects:**

| Type | Quantity | Cash Effect | Use Case |
|------|----------|-------------|----------|
| **BUY** | Asset increase | Cash decrease (BUY_SPEND) | Buy stocks |
| **SELL** | Asset decrease | Cash increase (SALE_PROCEEDS) | Sell stocks |
| **DIVIDEND** | No change (qty=0) | Cash increase (DIVIDEND_INCOME) | Receive dividend |
| **INTEREST** | No change (qty=0) | Cash increase (INTEREST_INCOME) | Loan interest |
| **TRANSFER_IN** | Asset increase | No cash change | Receive from another broker |
| **TRANSFER_OUT** | Asset decrease | No cash change | Send to another broker |
| **ADD_HOLDING** | Asset increase | No cash change | Gift, airdrop |
| **REMOVE_HOLDING** | Asset decrease | No cash change | Lost, stolen, delisted |
| **FEE** | No change (qty=0) | Cash decrease (FEE) | Standalone fee |
| **TAX** | No change (qty=0) | Cash decrease (TAX) | Standalone tax |

**Key points:**
- **Unidirectional relationship**: Transaction → CashMovement (via `cash_movement_id`)
  - Types BUY, SELL, DIVIDEND, INTEREST, FEE, TAX **MUST** have `cash_movement_id` set (enforced by CHECK constraint)
  - Types ADD_HOLDING, REMOVE_HOLDING, TRANSFER_IN, TRANSFER_OUT **MUST NOT** have `cash_movement_id` (no cash impact)
  - To find Transaction from CashMovement: `SELECT * FROM transactions WHERE cash_movement_id = <id>`
- **ON DELETE CASCADE**: Deleting a Transaction automatically deletes its linked CashMovement, ensuring no orphan cash movements. Deleting a CashMovement is not allowed if linked to a Transaction thanks the `PRAGMA foreign_keys = ON` .
- **Fees and taxes**: Handled as separate FEE/TAX transactions (not columns), each with its own CashMovement
- **Quantity rules**: 
  - `> 0` for BUY, SELL, TRANSFER, ADD/REMOVE_HOLDING
  - `= 0` for DIVIDEND, INTEREST, FEE, TAX (cash-only)
- **Oversell protection**: You can't sell more than you own (enforced by services, not DB)

---

### 5. `cash_movements` - Cash Flow Tracking

**What it abstracts:**
Individual cash inflows and outflows in broker accounts.

**Examples:**
- Depositing 1,000 EUR from your bank to Degiro
- Withdrawing 500 USD from Interactive Brokers to your bank
- Cash spent when buying stocks (auto-generated)
- Cash received from selling stocks (auto-generated)

**What it does NOT abstract:**
- Movements in your bank account
- Credit card transactions
- Loans or mortgages

**Schema:**
```sql
CREATE TABLE cash_movements (
    id INTEGER PRIMARY KEY,
    cash_account_id INTEGER NOT NULL,   -- FK to cash_accounts
    type TEXT NOT NULL,                  -- DEPOSIT, WITHDRAWAL, BUY_SPEND, etc.
    amount DECIMAL(18,6) NOT NULL,       -- Always positive (direction in type)
    trade_date DATE NOT NULL,            -- When movement was initiated
    settlement_date DATE,                -- When movement was settled (NULL = defaults to trade_date)
    note TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
```

**Cash movement types:**

| Type | Direction | Auto-Generated? | Description |
|------|-----------|-----------------|-------------|
| **DEPOSIT** | Inflow | No | Add funds to broker |
| **WITHDRAWAL** | Outflow | No | Remove funds from broker |
| **BUY_SPEND** | Outflow | Yes (from BUY) | Cash spent buying assets |
| **SALE_PROCEEDS** | Inflow | Yes (from SELL) | Cash received selling assets |
| **DIVIDEND_INCOME** | Inflow | Yes (from DIVIDEND) | Dividend payment |
| **INTEREST_INCOME** | Inflow | Yes (from INTEREST) | Interest payment |
| **FEE** | Outflow | Yes (from FEE) | Fee/commission |
| **TAX** | Outflow | Yes (from TAX) | Tax payment |
| **TRANSFER_IN** | Inflow | No | Cash from another broker |
| **TRANSFER_OUT** | Outflow | No | Cash to another broker |

**Key points:**
- **Unidirectional relationship**: Transaction → CashMovement (via Transaction.cash_movement_id)
  - To find the Transaction that created a CashMovement: `SELECT * FROM transactions WHERE cash_movement_id = <cash_movement.id>`
  - No `linked_transaction_id` field in CashMovement (avoids redundancy and maintains single source of truth)
- **Amount always positive**: Direction is implied by type (inflow vs outflow)
- **Balance calculation**: `SUM(inflows) - SUM(outflows)` for account balance
- **Manual vs auto-generated**: 
  - Manual: DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT (created by user)
  - Auto-generated: BUY_SPEND, SALE_PROCEEDS, DIVIDEND_INCOME, INTEREST_INCOME, FEE, TAX (created by backend when Transaction is created)
);
```

**Movement types:**

**Manual (created by user):**
- `DEPOSIT`: Add cash to broker (from your bank)
- `WITHDRAWAL`: Remove cash from broker (to your bank)
- `TRANSFER_IN`: Receive cash from another broker
- `TRANSFER_OUT`: Send cash to another broker

**Auto-generated (from asset transactions):**
- `BUY_SPEND`: Cash spent on purchase
- `SALE_PROCEEDS`: Cash from sale
- `DIVIDEND_INCOME`: Dividend received
- `INTEREST_INCOME`: Interest received
- `FEE`: Fee payment
- `TAX`: Tax payment

**Key points:**
- Amount is always **positive** (direction implied by type)
- `linked_transaction_id` links to the transaction that generated this movement
- Balance = SUM(incoming types) - SUM(outgoing types)

**Example flow:**
```
1. You deposit 10,000 EUR from your bank to Degiro
   → DEPOSIT: +10,000 EUR (manual, no linked_transaction_id)

2. You buy 10 shares of AAPL at 150 USD each
   → Transaction: BUY (quantity=10, price=150)
   → Cash movement: BUY_SPEND: -1,500 USD (auto, linked_transaction_id=123)

3. You receive dividend of 50 USD
   → Transaction: DIVIDEND (quantity=0, price=50)
   → Cash movement: DIVIDEND_INCOME: +50 USD (auto, linked_transaction_id=124)
```

---

### 6. `price_history` - Market Prices Over Time

**What it abstracts:**
Historical market prices for assets with `valuation_model = MARKET_PRICE`.

**Examples:**
- Daily closing prices for AAPL stock
- Daily prices for VWCE ETF
- Daily Bitcoin prices

**What it does NOT abstract:**
- Intraday prices (we only store one price per day), in the today record any time you have a new input it replaces the existing one
- Prices for scheduled-yield assets (those use interest_schedule)
- Your purchase prices (those are in transactions)

**Schema:**
```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,           -- FK to assets
    date DATE NOT NULL,
    
    open DECIMAL(18,6),                  -- Opening price
    high DECIMAL(18,6),                  -- High price
    low DECIMAL(18,6),                   -- Low price
    close DECIMAL(18,6),                 -- Closing price (most important)
    volume DECIMAL(24,0),                -- Trading volume (optional)
    adjusted_close DECIMAL(18,6),        -- Split/dividend adjusted
    
    currency TEXT NOT NULL,              -- Price currency
    source_plugin_key TEXT NOT NULL,     -- "yfinance", "manual"
    fetched_at DATETIME,
    
    UNIQUE(asset_id, date)               -- One price per day
);
```

**Key points:**
- **Daily-point policy**: Exactly one record per (asset, date)
- **Upsert behavior**: Updating today's price replaces the existing record
- **Close price**: Usually used for calculations
- **Adjusted close**: Accounts for stock splits and dividends
- **Volume field**: Trading volume for liquidity analysis (see details below)

**Volume Field Details:**

**Type**: `DECIMAL(24,0)` - integer-like decimal supporting large volumes

**Domain**: 
- **Positive integers**: Represents number of shares/units traded
- **NULL**: Acceptable when volume data is unavailable or not applicable
- **Zero**: Rare but valid (no trading activity on that day)

**Motivations**:
1. **Liquidity analysis**: Assess how easily an asset can be bought/sold
2. **Future VWAP calculations**: Volume-Weighted Average Price for better entry/exit decisions
3. **Market activity indicator**: High volume may indicate significant news or events
4. **Provider compatibility**: Most price providers (yfinance, etc.) already include volume in their responses

**Backward-fill behavior**:
- When prices are backward-filled (gaps in data), the `volume` field is also propagated from the last known value
- This ensures consistency in the price series structure
- `PricePointModel.backward_fill_info` indicates when data is backfilled vs actual

**Retrocompatibility Note**:
- **Before schema v2.1**: Volume field did not exist
- **After schema v2.1**: Volume field present but optional (NULL if unknown)
- **No breaking changes**: Existing queries continue to work; volume is simply available as additional data when present
- **Manual entries**: Users can leave volume NULL when manually adding prices

**Important: This is NOT for:**
- Your purchase prices (those are in `transactions.price`)
- Scheduled-yield assets like loans (those have no market price)

---

### 7. `asset_provider_assignments` - Asset Pricing Provider Configuration

**What it abstracts:**
Configuration for automatic price fetching per asset (moved from `assets` table in v2.0).

**Examples:**
- AAPL → yfinance provider (fetches from Yahoo Finance)
- BTC → coinbase provider
- Custom asset → manual (no automatic pricing)

**What it does NOT abstract:**
- The actual prices (those are in `price_history`)
- Provider implementations (those are Python plugins)

**Schema:**
```sql
CREATE TABLE asset_provider_assignments (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,               -- FK to assets (1-to-1)
    provider_code VARCHAR(50) NOT NULL,      -- "yfinance", "coinbase", "manual"
    provider_params TEXT,                    -- JSON params for provider
    last_fetch_at DATETIME,                  -- Last fetch attempt timestamp (NULL = never fetched)
    fetch_interval INTEGER,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    CONSTRAINT uq_asset_provider_asset_id UNIQUE (asset_id)
);

CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments (asset_id);
```

**Key points:**
- **1-to-1 relationship**: One asset can have at most one provider assignment
- **Optional**: Assets without assignment use manual pricing or scheduled yield
- **CASCADE DELETE**: Deleting asset removes its provider assignment
- **Single provider**: One provider handles both current and historical data
  - No separate current/history configuration (simplified from old design)
- **fetch_interval**: How often to refresh prices (in minutes)
  - `NULL` = default to 1440 minutes (24 hours)
- **Provider params**: JSON configuration specific to provider (e.g., ticker symbol mapping)
- **last_fetch_at**: Tracks last fetch attempt (for scheduling, monitoring, and debugging)
  - `NULL` = never attempted
  - Updated on every fetch attempt (success or failure)
  - Used by schedulers to determine when to retry
  - Useful for health monitoring and alerting

**Why separate table?**
- Cleaner separation of concerns (asset definition vs pricing source)
- Easier to add/remove providers without touching asset records
- Better for future plugin system expansion

**Example provider_params:**
```json
{
  "ticker": "AAPL",              // For yfinance
  "exchange": "NASDAQ"
}
```

**Migration note:**
In database v1.0, this data was stored as `current_data_plugin_key`, `current_data_plugin_params`, etc. in the `assets` table. These fields were removed in v2.0 (migration 001_initial).

---

### 8. `fx_currency_pair_sources` - FX Rate Provider Configuration

**What it abstracts:**
Which provider to use for fetching FX rates for specific currency pairs, with priority fallback.

**Examples:**
- EUR/USD → ECB (European Central Bank) priority=1
- EUR/USD → FED (Federal Reserve) priority=2 (fallback)
- GBP/USD → BOE (Bank of England) priority=1

**What it does NOT abstract:**
- The actual FX rates (those are in `fx_rates`)
- Provider implementations (those are Python plugins)

**Schema:**
```sql
CREATE TABLE fx_currency_pair_sources (
    id INTEGER PRIMARY KEY,
    base VARCHAR NOT NULL,                   -- "EUR"
    quote VARCHAR NOT NULL,                  -- "USD"
    provider_code VARCHAR NOT NULL,          -- "ECB", "FED", "BOE", "SNB"
    priority INTEGER NOT NULL,               -- Lower = higher priority (1 is highest)
    fetch_interval INTEGER,                  -- Fetch frequency in minutes (NULL = default 1440)
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_pair_source_base_quote_priority UNIQUE (base, quote, priority)
);

CREATE INDEX idx_pair_source_base_quote ON fx_currency_pair_sources (base, quote);
CREATE INDEX ix_fx_currency_pair_sources_base ON fx_currency_pair_sources (base);
CREATE INDEX ix_fx_currency_pair_sources_quote ON fx_currency_pair_sources (quote);
```

**Key points:**
- **Per currency pair**: Different providers for different pairs (EUR/USD vs GBP/USD)
- **Priority fallback**: If priority=1 fails, try priority=2, then 3, etc.
- **Multiple providers**: Same pair can have multiple providers with different priorities
- **No params**: Provider configuration is global (not per-pair), unlike asset providers
- **Alphabetical ordering**: base/quote follow same rule as fx_rates (base < quote)
- **fetch_interval**: How often to refresh rates (in minutes)
  - `NULL` = default to 1440 minutes (24 hours)
  - Example: 60 = hourly, 240 = every 4 hours, 1440 = daily
  - Used by automatic sync schedulers to optimize API calls
  - Different pairs can have different intervals (volatile pairs more frequent)

**Why separate from fx_rates?**
- Configuration (which provider to use) separate from data (actual rates)
- Allows dynamic provider switching without touching rate data
- Supports multi-source strategy (primary + fallback providers)

**Example configuration:**
```
EUR/USD → ECB (priority=1), FED (priority=2)
GBP/USD → BOE (priority=1), ECB (priority=2)
CHF/USD → SNB (priority=1), ECB (priority=2)
```

If ECB fails for EUR/USD, system automatically tries FED.

**Auto-configuration vs manual:**
- API endpoints can specify provider explicitly OR
- Use auto-configuration to lookup provider from this table
- Fallback logic: Try each provider in priority order until success

---

### 9. `fx_rates` - Currency Exchange Rates

**What it abstracts:**
Exchange rates between currencies for multi-currency portfolios.

**Examples:**
- EUR/USD rate: 1 EUR = 1.0850 USD
- GBP/EUR rate: 1 GBP = 1.1650 EUR

**What it does NOT abstract:**
- Broker-specific exchange rates
- Your actual currency conversions (those are transactions)
- Crypto exchange rates (those are referred to the `price_history` and then converted to the desired currency)

**Schema:**
```sql
CREATE TABLE fx_rates (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    base VARCHAR NOT NULL,                   -- "EUR"
    quote VARCHAR NOT NULL,                  -- "USD"
    rate NUMERIC(24, 10) NOT NULL,           -- 1 EUR = 1.0850 USD (high precision)
    source VARCHAR NOT NULL,                 -- "ECB", "FED", "BOE", "SNB", "manual"
    fetched_at DATETIME NOT NULL,
    CONSTRAINT ck_fx_rates_base_less_than_quote CHECK (base < quote),
    CONSTRAINT uq_fx_rates_date_base_quote UNIQUE (date, base, quote)
);

CREATE INDEX idx_fx_rates_base_quote_date ON fx_rates (base, quote, date);
```

**Key points:**
- **base**: Currency you start with (valuta di partenza)
- **quote**: Currency you want to get (valuta di arrivo)
- **Interpretation**: `1 base = rate × quote`
- **Daily-point policy**: One rate per day per currency pair
- **Unique constraint**: `(date, base, quote)` - we store only one direction!
- **CHECK constraint**: `base < quote` (alphabetically) - prevents storing both EUR/USD and USD/EUR
  - We **always** store currency pairs in alphabetical order
  - Example: Store EUR/USD (not USD/EUR), GBP/USD (not USD/GBP), EUR/GBP (not GBP/EUR)
  - The backend must normalize pairs before inserting: if you want USD/EUR, store as EUR/USD with rate = 1/original_rate
- **Reverse rate**: Calculated as `1/rate` in code (not stored twice)
  - Example: If we have EUR/USD = 1.0850, we calculate USD/EUR = 1/1.0850 = 0.9217
  - This saves space and avoids inconsistency
- **Used for**: Portfolio valuation in a single currency

**Example:**
```sql
-- EUR/USD on 2025-10-29
date='2025-10-29', base='EUR', quote='USD', rate=1.0850
-- Means: 1 EUR = 1.0850 USD

-- To get USD/EUR, we calculate: 1/1.0850 = 0.9217
-- Means: 1 USD = 0.9217 EUR
```

---

## Relationships

### Entity Relationship Diagram

```
┌─────────────┐
│   brokers   │
└──────┬──────┘
       │
       │ 1:N
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌─────────────┐    ┌──────────────┐
│cash_accounts│    │transactions  │
└──────┬──────┘    └──────┬───────┘
       │                  │
       │ 1:N              │ N:1
       │                  │
       ▼                  ▼
┌──────────────┐   ┌─────────────┐
│cash_movements│   │   assets    │
└──────────────┘   └──────┬──────┘
                          │
                          ├────────────────────┐
                          │ 1:N                │ 1:1 (optional)
                          │                    │
                          ▼                    ▼
                   ┌──────────────┐   ┌───────────────────────────┐
                   │price_history │   │asset_provider_assignments │
                   └──────────────┘   └───────────────────────────┘

┌──────────────────────────┐
│fx_currency_pair_sources  │  (Configuration for FX providers)
└──────────────────────────┘

┌──────────────┐
│   fx_rates   │  (FX exchange rates)
└──────────────┘
```

### Relationship Rules

1. **broker → cash_accounts**: 1:N (one broker, many cash accounts)
   - One per currency: EUR, USD, GBP, etc.

2. **broker → transactions**: 1:N (one broker, many transactions)
   - All transactions on a broker

3. **cash_account → cash_movements**: 1:N (one account, many movements)
   - All inflows/outflows for that account

4. **asset → transactions**: 1:N (one asset, many transactions)
   - All trades of that asset across all brokers

5. **asset → price_history**: 1:N (one asset, many prices)
   - Daily prices over time

6. **asset → asset_provider_assignments**: 1:1 optional (one asset, at most one provider)
   - Configures automatic price fetching
   - CASCADE DELETE when asset is deleted

7. **transaction → cash_movement**: 1:1 optional (some transactions auto-generate movements)
   - BUY → BUY_SPEND
   - SELL → SALE_PROCEEDS
   - DIVIDEND → DIVIDEND_INCOME

8. **fx_currency_pair_sources**: Standalone configuration table
   - No foreign keys (references currency codes as strings)
   - Configures which provider to use per currency pair

9. **fx_rates**: Standalone data table
   - No foreign keys (stores rates by date and currency pair)

---

## Common Scenarios

### Scenario 1: Buying a Stock

**Action**: Buy 10 shares of AAPL at $150 on Degiro

**Database changes:**

1. **Transaction record:**
```sql
INSERT INTO transactions (
    asset_id = (SELECT id FROM assets WHERE identifier='AAPL'),
    broker_id = (SELECT id FROM brokers WHERE name='Degiro'),
    type = 'BUY',
    quantity = 10,
    price = 150.00,
    currency = 'USD',
    fees = 1.50,
    trade_date = '2025-10-29'
);
```

2. **Auto-generated cash movement:**
```sql
INSERT INTO cash_movements (
    cash_account_id = (SELECT id FROM cash_accounts 
                       WHERE broker_id=Degiro AND currency='USD'),
    type = 'BUY_SPEND',
    amount = 1501.50,  -- 10 × 150 + 1.50 fees
    trade_date = '2025-10-29',
    linked_transaction_id = (last inserted transaction)
);
```

**Result:**
- You now own 10 AAPL shares on Degiro
- Your USD cash in Degiro decreased by $1,501.50

---

### Scenario 2: Receiving a Dividend

**Action**: Receive $25 dividend from AAPL holdings

**Database changes:**

1. **Transaction record:**
```sql
INSERT INTO transactions (
    asset_id = (SELECT id FROM assets WHERE identifier='AAPL'),
    broker_id = (SELECT id FROM brokers WHERE name='Degiro'),
    type = 'DIVIDEND',
    quantity = 0,  -- No change in holdings
    price = 25.00,  -- Total dividend amount
    currency = 'USD',
    trade_date = '2025-10-29'
);
```

2. **Auto-generated cash movement:**
```sql
INSERT INTO cash_movements (
    cash_account_id = (SELECT id FROM cash_accounts 
                       WHERE broker_id=Degiro AND currency='USD'),
    type = 'DIVIDEND_INCOME',
    amount = 25.00,
    trade_date = '2025-10-29',
    linked_transaction_id = (last inserted transaction)
);
```

**Result:**
- Your AAPL holdings unchanged
- Your USD cash in Degiro increased by $25

**Important note on dividends:**
When a dividend is paid, the stock price typically drops by approximately the dividend amount (ex-dividend effect). This is NOT handled internally by LibreFolio - the system simply fetches the new market price from external sources (yfinance, etc.) which will already reflect the post-dividend price. The database doesn't need to do anything special; the price_history table will naturally show the lower price on the ex-dividend date when the next price fetch occurs.

---

### Scenario 3: Transferring Assets Between Brokers

**Action**: Transfer 5 AAPL shares from Degiro to Interactive Brokers

**Database changes:**

1. **Transfer out from Degiro:**
```sql
INSERT INTO transactions (
    asset_id = (SELECT id FROM assets WHERE identifier='AAPL'),
    broker_id = (SELECT id FROM brokers WHERE name='Degiro'),
    type = 'TRANSFER_OUT',
    quantity = 5,
    currency = 'USD',
    trade_date = '2025-10-29',
    note = 'Transfer to Interactive Brokers'
);
```

2. **Transfer in to Interactive Brokers:**
```sql
INSERT INTO transactions (
    asset_id = (SELECT id FROM assets WHERE identifier='AAPL'),
    broker_id = (SELECT id FROM brokers WHERE name='Interactive Brokers'),
    type = 'TRANSFER_IN',
    quantity = 5,
    currency = 'USD',
    trade_date = '2025-10-29',
    note = 'Transfer from Degiro'
);
```

**Result:**
- Degiro: 5 fewer AAPL shares
- Interactive Brokers: 5 more AAPL shares
- No cash movements (just asset movement)

---

### Scenario 4: Depositing Cash

**Action**: Deposit €1,000 from your bank to Degiro

**Database changes:**

```sql
INSERT INTO cash_movements (
    cash_account_id = (SELECT id FROM cash_accounts 
                       WHERE broker_id=Degiro AND currency='EUR'),
    type = 'DEPOSIT',
    amount = 1000.00,
    trade_date = '2025-10-29',
    note = 'Transfer from Chase bank',
    linked_transaction_id = NULL  -- Manual, not linked to transaction
);
```

**Result:**
- Your EUR cash in Degiro increased by €1,000
- No transaction record (pure cash movement)

**Important:** Your bank account is **outside** this system!

---

## Example Data

### See It In Action

To explore a fully populated database with realistic data:

```bash
# Run database tests
./dev.sh test db all
```

This will:
1. Create a fresh database
2. Validate the schema
3. **Populate with example data** including:
   - Multiple brokers (Degiro, Interactive Brokers)
   - Various assets (stocks, ETFs, loans)
   - Multiple transactions (buy, sell, dividends)
   - Cash accounts and movements
   - Price history
   - FX rates

### Inspect the Data

After running tests, inspect with:

```bash
sqlite3 backend/data/sqlite/app.db

-- See all brokers
SELECT * FROM brokers;

-- See assets
SELECT display_name, identifier, asset_type FROM assets;

-- See transactions
SELECT t.type, a.identifier, t.quantity, t.price, t.trade_date
FROM transactions t
JOIN assets a ON t.asset_id = a.id;

-- See cash accounts
SELECT b.name, c.currency, c.display_name
FROM cash_accounts c
JOIN brokers b ON c.broker_id = b.id;

-- Calculate cash balance
SELECT ca.display_name, 
       SUM(CASE 
           WHEN cm.type IN ('DEPOSIT', 'SALE_PROCEEDS', 'DIVIDEND_INCOME', 'INTEREST_INCOME', 'TRANSFER_IN')
           THEN cm.amount
           ELSE -cm.amount
       END) as balance
FROM cash_accounts ca
JOIN cash_movements cm ON ca.id = cm.cash_account_id
GROUP BY ca.id;
```

---

## Summary

**Key Takeaways:**

1. **Brokers** = platforms where you trade (Degiro, IB, etc.)
2. **Assets** = financial instruments (stocks, ETFs, loans)
3. **Cash accounts** = cash **inside** brokers, isolated per broker
4. **Transactions** = events that change holdings or generate cash
5. **Cash movements** = individual cash flows (in/out)
6. **Price history** = daily market prices
7. **FX rates** = currency conversions

**Remember:**
- Cash accounts are **broker-specific** (Degiro EUR ≠ IB EUR)
- Your **bank account is external** (not tracked)
- Balances are **computed**, never stored directly
- One price per day (daily-point policy)
- Transactions auto-generate cash movements

**Smart scheduling features:**
- `asset_provider_assignments.last_fetch_at`: Tracks when each asset was last fetched (for scheduling and monitoring)
- `fx_currency_pair_sources.fetch_interval`: Defines refresh frequency per currency pair (optimizes API usage)

---

For more technical details, see:
- [Database Models Source Code](../backend/app/db/models.py)
- [Alembic Migration Guide](alembic-guide.md)

