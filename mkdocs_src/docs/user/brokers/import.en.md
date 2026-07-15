# 📥 Broker Transactions

The **Transactions** tab is the control center for modifying the broker's ledger. It lists all recorded financial operations (buys, sells, dividends, deposits, withdrawals, transfers, and FX conversions) scoped to this broker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

From this tab, you can perform manual transactions or launch bulk statement imports.

---

## ➕ Manual Transactions

Click the **Add Transaction** (`Plus` icon) button to open the single transaction modal wizard. This lets you manually record:

- **Buy / Sell**: Trade assets, specifying date, price, quantity, and currency.
- **Dividend / Income**: Income received from asset holdings.
- **Deposit / Withdrawal**: External cash inflows or outflows to/from the broker cash balance.
- **Transfer**: Transfer of cash or assets between brokers (e.g., funding the account from a bank broker).
- **FX Conversion**: Currency exchanges inside the broker account.

For a detailed explanation of transaction fields and validation rules, see the **[Transaction Form](../transactions/form.md)** guide.

---

## 🧙 BRIM: Broker Report Import Module

The **Import** (`Upload` icon) button launches the **BRIM** wizard. This module allows you to import your broker's exported statements (CSV or Excel formats) in bulk, run automatic sanity validations, and map tickers to local assets before final commit.

### The Import Flow

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-import" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Import Modal">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Wizard — Step 1: Upload" alt="Import Wizard Step 1">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Wizard — Step 2: Parser Config" alt="Import Wizard Step 2">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Wizard — Step 3: Analysis" alt="Import Wizard Step 3">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Wizard — Step 4: Asset Resolution" alt="Import Wizard Asset Resolution">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Import Wizard Duplicate Detection">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Bulk Staging" alt="Import Bulk Staging">
</div>

The wizard progresses through the following steps:

1.  **Select File & Parser**: Choose the statement file and select the appropriate parser configuration (e.g., Interactive Brokers, Degiro, Directa, Charles Schwab, generic CSV, etc.).
2.  **Verify Headers & Mapping**: Renders the CSV headers to confirm the parser aligns correctly with the columns.
3.  **Operation Analysis**: Processes the file and displays a preview grid of parsed actions (Buys, Sells, Dividends, etc.).
    *   **Badges**: Operations are labeled as `UNIQUE` (new trade), `DUPLICATE` (already exists in database), or `UNRESOLVED` (requires mapping ticker/ISIN).
    *   **TODO Notes**: Highlight fields requiring attention or items that could not be parsed automatically.
4.  **Asset Resolution**: If the statement contains tickers or ISINs that do not exist in your local assets registry, BRIM displays a mapping step. You can:
    *   Map the ticker to an existing asset.
    *   Create a new asset directly from this screen, pre-filled with details extracted from the statement.
5.  **Bulk Staging & Commit**: Review the staged checklist of clean, unique transactions. Uncheck any operations you wish to exclude, then click **Commit** to write the records to your portfolio ledger.

---

## 📑 Import History

Click the **Show Import History** (`FileText` icon) button to view a complete ledger of previous import tasks. It displays:

- Uploaded filename and size.
- Processed rows and total committed transactions.
- Upload timestamp.
- User who performed the import.
