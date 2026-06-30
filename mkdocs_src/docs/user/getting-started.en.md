# 🚀 Getting Started

Welcome to LibreFolio! This guide walks you through registering an account, logging in, and importing your first broker statement to instantly populate your dashboard.

---

## 📝 1. Register Your Account

Navigate to the LibreFolio URL (e.g., `http://localhost:6040`) and you'll see the login page. Click **Register** to create a new account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Fill in your details:

- 👤 **Username**: Your display name (unique across the system)
- 📧 **Email**: A valid email address
- 🔑 **Password**: A strong password (the strength indicator helps you)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "First User = Admin"

    The very first user to register automatically becomes the **system administrator** (superuser). This user can manage global settings, promote other users, and access all admin features.

---

## 🔐 2. Log In

After registering, you'll be redirected to the login page. Enter your credentials to access your dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Import Your First Statement (Create Broker & Assets On-the-Fly)

When you first log in, you will be greeted by an empty dashboard with no data.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Empty Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

In LibreFolio, the fastest way to get started is by importing your transaction history directly. You don't need to configure brokers or assets beforehand: the system will automatically create them for you during the import process!

### 📋 Steps

1. **Upload Your Statement**: Navigate to the **[Transactions](transactions/index.md)** page from the sidebar menu. Click the **"Import"** button (:material-file-upload:) or drag & drop your broker statement file (CSV or PDF) directly onto the page.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

2. **Parser Configuration**: The wizard will automatically detect the broker format. You can verify the settings (such as dates and delimiters) and configure fallback options if using a generic CSV report.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    !!! tip "Reprocessing Existing Statements"
    
        You can also re-process any previously uploaded statement directly from the **[Files & Uploads](files/index.md#broker-reports)** page. This is particularly useful after an import plugin update or if you accidentally deleted some transactions and want to restore them.

3. **Analysis & Parsing**: The system reads, validates, and parses the statement rows. You will see a progress bar indicating the parsing speed and status.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analysis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Broker & Asset Resolution**: If the report contains a broker account or assets (such as ETFs or stocks) that do not yet exist in your LibreFolio instance, the system flags them. You can search for existing ones or create them **on-the-fly** directly inside the wizard with pre-filled details. For more information, see the **[Import from Broker - Asset Mapping](transactions/import/index.md#asset-mapping)** guide.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Step 4: Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Duplicate Detection**: The wizard compares statement transactions against your existing ledger. It groups potential matches into two UI status badges based on 4 confidence levels:
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Wizard Step 5: Duplicate Detection" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    | UI Badge | Confidence Level | Criteria / Matching Rules |
    | :--- | :--- | :--- |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Basic fields and description match, and asset auto-resolved (highly confident duplicate). |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Basic fields and description match, but asset is not resolved. |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Basic fields match, and asset is auto-resolved (but description differs or is empty). |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Basic fields (type, date, quantity, amount) match, but asset is not resolved. |
    | <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | The transaction has no matching records in the database and is classified as new (no duplicate detected). |
    | <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ UNRESOLVED</span> | — | The broker or financial instrument was not matched to an existing entity in the database (requires resolution in Step 4 before importing). |

    For duplicate rules and configuration options, see the **[Import from Broker - Duplicate Detection](transactions/import/index.md#duplicate-detection)** section.

6. **Staging & Final Review**: Review the parsed transaction list. Once you verify everything is correct, click **Import** to save all transactions to your portfolio.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Wizard Step 6: Bulk Review" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

    The staging review table displays the following columns:

    - **Date**: The execution date of the transaction.
    - **Type**: The financial operation type (BUY, SELL, DIVIDEND, DEPOSIT, etc.).
    - **Asset**: The matched asset from your library.
    - **Quantity**: The number of units or shares traded.
    - **Price**: The unit price of the asset.
    - **Net Amount**: The total cash impact (positive or negative) on the account.
    - **Fees/Taxes**: Broker commissions or transaction taxes included.

    For advanced settings or validation errors in staging, refer to the **[Import from Broker](transactions/import/index.md)** page.

---

## 📈 4. Back to the Dashboard

After successfully importing your statement, return to the **Dashboard**. 

LibreFolio calculates your portfolio metrics, asset allocation (by type, sector, geography), and performance history in real-time. You can now see your entire financial situation beautifully plotted!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. What's Next?

Now that your portfolio is populated, you can:

- 🤝 **[Share your broker](brokers/sharing.md)** — Give access to family members or advisors.
- 💱 **[Set up FX rates](fx/index.md)** — Configure currency conversion for multi-currency portfolios.
- ⚙️ **[Customize settings](../admin/settings.md)** — Adjust language, theme, and system preferences.
