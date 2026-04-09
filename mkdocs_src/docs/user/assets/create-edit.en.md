# ➕ Create & Edit Assets

## Creating a New Asset

1. Click **+ New Asset** on the assets page
2. Fill in the basic information:
    - **Name** (required)
    - **Category** (required): Stock, ETF, Bond, Crypto, Commodity, P2P, Index, etc.
    - **Currency** (required): the currency the asset is denominated in
    - **Identifiers**: ISIN, ticker, CUSIP, SEDOL, etc.
3. Optionally configure a **[Provider](providers/index.en.md)** for automatic price fetching
4. Optionally add **Sector** and **Geographic** distributions
5. Click **Save**

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-modal" alt="Create Asset Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

## 🧪 Testing Provider Configuration

After configuring a provider, click **Test Configuration** to verify that pricing data can be fetched. The test checks:

- **Current Price**: fetches the latest price
- **History**: fetches historical price data (if supported)

Results are displayed inline with execution times. A ⚠️ warning means the operation is not supported by this provider (e.g., CSS Scraper doesn't support history).

## 🔌 Provider Assignment

Each asset can have one pricing provider assigned. See [Providers](providers/index.en.md) for details on available providers and their configuration.

## ⏱️ Fetch Interval

The fetch interval controls how often LibreFolio automatically refreshes the asset's price data. Default is 24 hours (`24:00`). Format: `HH:MM`.

## 🛠️ Editing an Asset

Click the **Edit** (✏️) button on the [detail page](detail/index.en.md) to open the asset modal with all fields pre-populated. All fields are editable, including provider configuration and distributions.

## 🔗 Related

- 📊 **[Asset Detail Page](detail/index.en.md)** — View and analyze asset data
- 🔌 **[Providers](providers/index.en.md)** — Available pricing providers

