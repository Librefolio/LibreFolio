# 📥 Import from Broker (BRIM)

**BRIM** (Broker Report Import Module) lets you import transactions directly from your broker's export files — no manual entry needed. Upload a CSV report and LibreFolio parses, maps, and imports all transactions in one flow.

---

## 🚀 How to Import

1. Export a transaction report from your broker (usually a CSV file — check your broker's help center).
2. In LibreFolio, navigate to your **Broker** page.
3. Click the **Import** button (:material-file-upload:) in the broker header.
4. The **Import Modal** opens.
5. **Drag & drop** or click to select your file.
6. LibreFolio **auto-detects** the broker format and shows a **preview** of parsed transactions.
7. Review the preview — check that dates, amounts, and asset names look correct.
8. Click **Import** to commit all transactions.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Parser Configuration" alt="Wizard Step 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Step 3: Asset Resolution" alt="Wizard Step 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Duplicate Detection">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Bulk Staging Review" alt="Bulk Staging">
</div>

!!! tip "You can also use the Files section"

    The **[Files](../../files/index.md)** section (BRIM tab) lets you manage uploaded broker reports centrally, re-import them, or delete them.

---

## 🏦 Supported Brokers

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">Import transaction reports using Flex Queries.</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">Import transaction history CSV exports from Degiro.</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">Import account statement XLSX/CSV files from eToro.</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Import transaction history CSV files from Directa SIM.</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">Import CSV transaction history from Charles Schwab.</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">Import account statement PDF/CSV reports from Revolut.</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">Import transaction history CSV files from Coinbase.</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">Import CSV transaction statements from Freetrade.</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">Import transaction history CSV reports from Finpension.</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">Import CSV transaction history from Trading212.</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">Generic CSV</span>
        </div>
        <span class="card-desc">Our fallback parser with manual column mapping.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Request New Plugin</span>
     </div>
     <span class="card-desc">Your broker is missing? Request a new plugin or contribute code!</span>
    </a>
    </div>

### 📊 Importer Capabilities

| Broker | Format | Buy/Sell | Dividends | Deposits/Cash | Fees/Taxes | Notes |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Interactive Brokers** | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Best for multi-currency accounts |
| **Degiro** | CSV | ✅ | ✅ | ✅ | ✅ | Support for standard account statement |
| **eToro** | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Realized gains and dividends support |
| **Directa SIM** | CSV | ✅ | ✅ | ✅ | ✅ | Italian broker tax statement support |
| **Charles Schwab** | CSV | ✅ | ✅ | ✅ | ✅ | Standard US broker activity statement |
| **Revolut** | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Stock and crypto transaction support |
| **Coinbase** | CSV | ✅ | ❌ | ✅ | ✅ | Crypto-only transaction reports |
| **Freetrade** | CSV | ✅ | ✅ | ✅ | ✅ | Simple UK brokerage statements |
| **Finpension** | CSV | ✅ | ✅ | ✅ | ✅ | Swiss pension 3a statements |
| **Trading212** | CSV | ✅ | ✅ | ✅ | ✅ | European trading activity CSV |
| **Generic CSV** | CSV | ✅ | ✅ | ✅ | ✅ | Manual column mapper fallback |

!!! note "All providers are in Beta"

    Import plugins are community-maintained and improve over time. If a specific report format has quirks, the **[Generic CSV](generic-csv/)** provider allows manual column mapping as a fallback.

---

## 🗂️ Asset Mapping

During the preview step, LibreFolio attempts to **auto-match** each asset name from your report to an asset already in your library.

- ✅ **Matched** — will be imported against the existing asset.
- ⚠️ **Unmatched** — select or create the target asset before importing.
- ❌ **Error** — the row could not be parsed.

---

## ♻️ Duplicate Detection

BRIM checks for **duplicate transactions** based on date, type, asset, quantity, and amount. Duplicate rows are flagged in the preview — you can choose to skip or force-import them.

---

## 🔗 Related

- 📋 **[Transaction Table](../index.md)** — View and manage imported transactions
- 🗂️ **[Files](../../files/index.md)** — Manage uploaded broker report files
- 🏦 **[Brokers](../../brokers/index.md)** — Set up your broker accounts first
