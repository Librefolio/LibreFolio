# 🧙 How to Import Transactions

Learn how to use the Broker Report Import Module (BRIM) to import your transactions step-by-step.

---

## 🚀 Step-by-Step Guide

1. Export a transaction report from your broker (usually a CSV file — check your broker's help center).
2. In LibreFolio, navigate to the **[Transactions](../index.md)** page.
3. Click the **Import** button (:material-file-upload:) in the page header, or drag-and-drop your statement file directly into the transaction list.
4. The **Import Wizard** opens.
5. Review the preview — check that dates, amounts, and asset names look correct.
6. Click **Import** to commit all transactions.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Parser Configuration" alt="Wizard Step 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analysis" alt="Wizard Step 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Step 4: Asset Resolution" alt="Wizard Step 4">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Step 4: Duplicate Detection" alt="Duplicate Detection">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 5: Bulk Staging Review" alt="Bulk Staging">
</div>

!!! tip "On-the-fly Broker & Asset Creation"

    If the imported report contains a broker account or assets that are not yet created in LibreFolio, you don't need to exit the import flow! The wizard will guide you to create the missing **[Brokers](../../brokers/index.md)** and **[Assets](../../assets/index.md)** on-the-fly, pre-filling details from the statement.

!!! tip "You can also use the Files section"

    The **[Files](../../files/index.md)** section (BRIM tab) lets you manage uploaded broker reports centrally, re-import them, or delete them.

---

## 🧙 The Import Wizard Steps

The guided wizard contains 5 operational steps designed to parse, validate, resolve and import your transaction history safely.

### 🧙 Step 1: Upload Report File

This step accepts CSV, XLSX or PDF reports exported from your broker. You can select files manually or drag-and-drop them directly into the wizard.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Step 2: Parser Configuration

The system automatically detects the broker format (e.g. Degiro, Directa, Interactive Brokers). If you upload a generic spreadsheet, you can use the **Generic CSV** parser to manually map your columns (date, type, quantity, asset, net cash) to LibreFolio fields.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Step 3: Analysis & Parsing

The system parses the files, validating dates, numbers and currencies. You will see a progress bar indicating the parsing speed and status. Once analysis completes, any warning or error in parsing will be summarized before continuing.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analysis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

At the end of parsing, the table displays a summary of the processing for each file with the following statistical columns marked by emojis:

| Emoji / Column | Metric Name | Meaning and Population Rules |
| :--- | :--- | :--- |
| `📊` | **Transactions** | The total number of financial transactions read and identified within the file. |
| `🏦` | **Identified Assets** | The number of financial instruments (stocks, ETFs, etc.) found within the parsed transactions. |
| `✗` | **Unresolved Assets** | The number of instruments in the file that were not found in LibreFolio's database (marked in red if > 0, requiring mapping in Step 4). |
| `🔴` | **Validation Issues** | Formal errors detected in the data (e.g., invalid formats, incorrect dates, missing required data). |
| `🔧` | **Action Required (TODOs)** | Fields or attributes requiring attention (red if blocking, orange for warning/info level actions). These are not necessarily errors: they simply indicate missing data that cannot be extracted automatically from the statement alone, which you can easily fill in manually in the bulk transaction form at the end of the wizard. |
| `⚠️` | **Warnings** | General notifications or warning messages generated by the parser during processing. |

### 🔍 Step 4: Asset Mapping & Duplicate Detection

This is the reconciliation phase. The wizard performs two core checks:

#### 🗂️ Asset Resolution

If the statement contains ticker symbols or ISINs that are not in your library, the wizard flags them. You can:

- Map them to an existing asset in your database.
- Create them **on-the-fly** directly inside the wizard.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Step 4: Asset Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Duplicate Detection

The system compares parsed entries with your database to find potential duplicates based on type, date, amount, quantity, and description.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Wizard Step 4: Duplicate Detection" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Duplicates are flagged in the UI using two status badges based on 4 confidence levels:

| UI Badge | Confidence Level | Criteria / Matching Rules |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Basic fields and description match, and asset auto-resolved (highly confident duplicate). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Basic fields and description match, but asset is not resolved. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Basic fields match, and asset is auto-resolved (but description differs or is empty). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Basic fields (type, date, quantity, amount) match, but asset is not resolved. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | The transaction has no matching records in the database and is classified as new (no duplicate detected). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ UNRESOLVED</span> | — | The broker or financial instrument was not matched to an existing entity in the database (requires resolution in Step 4 before importing). |

By default, the wizard automatically unchecks "Likely" duplicates to prevent double-entry, but you can override this choice.

### 📦 Step 5: Bulk Staging Review

The final review shows the parsed list in a spreadsheet-like grid.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Wizard Step 5: Bulk Review" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The table displays:

- **Date**: The execution date.
- **Type**: BUY, SELL, DIVIDEND, DEPOSIT, etc.
- **Asset**: The matched asset from your library.
- **Quantity**: The number of units/shares.
- **Price**: The unit price.
- **Net Amount**: The total cash impact.
- **Fees/Taxes**: Commissions and taxes included.

Click **Import** to finalize the import and write the transactions to your ledger.
