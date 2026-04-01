# 💼 Assets

Assets are the core of LibreFolio. They represent any financial instrument you own or track: stocks, ETFs, bonds, cryptocurrencies, or custom instruments like savings accounts with scheduled interest.

## 📌 What is an Asset?

An asset in LibreFolio is a financial instrument with:

- **Identity**: name, ISIN, ticker, or other identifiers
- **Category**: stock, ETF, bond, crypto, commodity, etc.
- **Provider**: an optional pricing provider that automatically fetches current prices and history
- **Transactions**: buy, sell, dividend, interest operations linked to a portfolio

## ➕ Creating an Asset

1. Navigate to **Assets** in the sidebar
2. Click **+ New Asset**
3. Fill in the basic information:
    - **Name** (required)
    - **Category** (required)
    - **Currency** (required)
    - **Identifiers**: ISIN, ticker, CUSIP, SEDOL, etc.
4. Optionally configure a **Provider** for automatic price fetching
5. Click **Save**

## 🛠️ Managing Assets

### ✏️ Editing

Click on any asset row to open the detail modal. All fields are editable.

### 🗑️ Deleting

Use the delete button (🗑️) on the row, or select multiple assets and use bulk delete.

### 🧪 Testing Provider Configuration

After configuring a provider, click **Test Configuration** to verify that pricing data can be fetched. The test checks:

- **Current Price**: fetches the latest price
- **History**: fetches historical price data (if supported)

Results are displayed inline with execution times. A ⚠️ warning means the operation is not supported by this provider (e.g., CSS Scraper doesn't support history).

## 🔌 Provider Assignment

Each asset can have one pricing provider assigned. See [Providers](providers/index.en.md) for details on available providers and their configuration.

## ⏱️ Fetch Interval

The fetch interval controls how often LibreFolio automatically refreshes the asset's price data. Default is 24 hours (24:00). Format: `HH:MM`.
