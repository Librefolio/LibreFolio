# LibreFolio Database Schema Documentation

**Version**: 1.0  
**Last Updated**: October 29, 2025

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

**What it does NOT abstract:**
- Physical commodities (gold bars, oil barrels)
- Real estate properties
- Collectibles (art, wine)
- Business ownership (unless represented as shares)

**Schema:**
```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,          -- "Apple Inc."
    identifier TEXT NOT NULL,            -- "AAPL"
    identifier_type TEXT,                -- TICKER, ISIN, UUID, etc.
    currency TEXT NOT NULL,              -- "USD", "EUR"
    asset_type TEXT,                     -- STOCK, ETF, BOND, CRYPTO, CROWDFUND_LOAN
    
    -- Valuation method
    valuation_model TEXT,                -- MARKET_PRICE or SCHEDULED_YIELD
    
    -- Plugin configuration for market data
    current_data_plugin_key TEXT,        -- "yfinance", NULL for manual
    current_data_plugin_params TEXT,     -- JSON params
    history_data_plugin_key TEXT,
    history_data_plugin_params TEXT,
    
    -- For loans/bonds with scheduled payments
    face_value DECIMAL(18,6),            -- Principal amount
    maturity_date DATE,                  -- When it matures
    interest_schedule TEXT,              -- JSON: [{rate, period, ...}]
    late_interest TEXT,                  -- JSON: {rate, grace_days}
    
    active BOOLEAN,
    created_at DATETIME,
    updated_at DATETIME
);
```

**Key points:**
- One record per unique asset
- `valuation_model`:
  - `MARKET_PRICE`: Value based on market prices (stocks, ETFs, crypto)
  - `SCHEDULED_YIELD`: Value based on payment schedule (loans, some bonds)
- Plugin keys: `NULL` = manual entry allowed, value = automatic fetching

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
- **Broker-specific**: Each broker has its own isolated cash accounts
- **One per currency**: A broker can have multiple cash accounts (EUR, USD, etc.)
- **Balance computed at runtime**: Sum of cash_movements, never stored directly

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
    
    fees DECIMAL(18,6),                  -- Transaction fees
    taxes DECIMAL(18,6),                 -- Taxes paid
    
    trade_date DATE NOT NULL,
    settlement_date DATE,
    note TEXT,
    
    created_at DATETIME,
    updated_at DATETIME
);
```

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
- **Auto-generates cash movements**: BUY, SELL, DIVIDEND, INTEREST, FEE, TAX automatically create corresponding cash_movements
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
    trade_date DATE NOT NULL,
    note TEXT,
    linked_transaction_id INTEGER,       -- FK to transactions (if auto-generated)
    created_at DATETIME,
    updated_at DATETIME
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
- Intraday prices (we only store one price per day)
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

**Important: This is NOT for:**
- Your purchase prices (those are in `transactions.price`)
- Scheduled-yield assets like loans (those have no market price)

---

### 7. `fx_rates` - Currency Exchange Rates

**What it abstracts:**
Exchange rates between currencies for multi-currency portfolios.

**Examples:**
- EUR/USD rate: 1 EUR = 1.0850 USD
- GBP/EUR rate: 1 GBP = 1.1650 EUR

**What it does NOT abstract:**
- Broker-specific exchange rates
- Your actual currency conversions (those are transactions)
- Crypto exchange rates (those are asset prices)

**Schema:**
```sql
CREATE TABLE fx_rates (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    base TEXT NOT NULL,                  -- "EUR"
    quote TEXT NOT NULL,                 -- "USD"
    rate DECIMAL(18,6) NOT NULL,         -- 1 EUR = 1.0850 USD
    source TEXT,                         -- "ECB", "manual"
    fetched_at DATETIME,
    
    UNIQUE(date, base, quote)            -- One rate per day per pair
);
```

**Key points:**
- **Interpretation**: `1 base = rate × quote`
- **Daily-point policy**: One rate per day per currency pair
- **Reverse rate**: Calculated as `1/rate` in code (not stored twice)
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

### 8. `price_raw_payloads` - Plugin Response Cache

**What it abstracts:**
Raw JSON responses from data plugins for debugging and audit.

**Examples:**
- Full Yahoo Finance API response for AAPL
- CoinGecko API response for Bitcoin

**Schema:**
```sql
CREATE TABLE price_raw_payloads (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,           -- FK to assets
    payload_type TEXT NOT NULL,          -- "current" or "history"
    raw_json TEXT NOT NULL,              -- Full JSON response
    source_plugin_key TEXT NOT NULL,     -- "yfinance"
    fetched_at DATETIME
);
```

**Key points:**
- Optional table for debugging
- Allows replaying/reprocessing data
- Helps diagnose API changes

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
                          │ 1:N
                          │
                          ▼
                   ┌──────────────┐
                   │price_history │
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

6. **transaction → cash_movement**: 1:1 optional (some transactions auto-generate movements)
   - BUY → BUY_SPEND
   - SELL → SALE_PROCEEDS
   - DIVIDEND → DIVIDEND_INCOME

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

---

For more technical details, see:
- [Database Models Source Code](../backend/app/db/models.py)
- [STEP 2 Completion Report](../STEP_2_COMPLETION_REPORT.md)
- [Alembic Migration Guide](alembic-guide.md)

