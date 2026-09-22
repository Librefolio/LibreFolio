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

## 🎉 3. Welcome Setup & Quick Tour {: #welcome-setup }

When the Welcome flow is due, LibreFolio takes you to a dedicated **Welcome** page before the
dashboard.

On this page you can:

- 🌍 **Confirm your language and base currency** — pre-filled from your administrator's
  instance-wide defaults.
- 🖼️ **Add a profile picture if you want** — your initials remain in place when you do not
  choose one.
- ✅ Select **Continue** to save the visible choices, or **Skip setup permanently** to keep the
  existing settings and move on.
- 🚪 Use the dedicated **Log out** action in the page header whenever you need to leave safely.

An onboarding refresh or bootstrap failure can fall back to the Dashboard with an inline
**Retry** banner only when LibreFolio already has a cached terminal Welcome state
(**Completed** or **Skipped**) for your signed-in account. Without that cache — including on the
first load or while Welcome is **Pending** — startup stays blocked and offers **Retry** and
**Log out** rather than showing the Dashboard. A user-settings failure also blocks startup.

Right after Welcome, the intro cycles through three short phrases over **8 seconds**. Three
progress marks show which phrase is active; there is no visible countdown. Select **Start tour**
to begin immediately, or let the intro start it automatically.

The core tour is deliberately short and stays focused on navigation:

**Sidebar or mobile navigation control** → **Dashboard** → **Transactions** → **Brokers** →
**FX** → **Assets** → **Tools** → **Settings**.

It points out the main destinations without opening forms or creating data.

### 🧭 Contextual guides

Short guides then appear where their controls are real and useful:

| Area | Contextual guides |
|---|---|
| **Transactions** | Page overview, Add Transaction form, bulk workspace, and Import Wizard |
| **Brokers** | Brokers page, Add Broker form, and broker details |
| **FX** | FX page, Add Pair form, and pair details |
| **Assets** | Assets page, Add Asset form, and asset details |

These guides observe the interface; they never synthesize a click, upload, edit, or save. An
informational area pulses, while a real action is marked with a translucent cursor. Clicking
that real action performs the normal app action and advances the guide.

The message panel becomes translucent after **3 seconds** so the underlying interface is easier
to see, then returns to full strength when you hover it or move focus inside it. When LibreFolio
scrolls to a target, the panel follows the moving target without flashing back to a waiting
message.

You can manually replay any flow from
**[Settings → Preferences → Onboarding and guides](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Import Your First Statement (Create Broker & Assets On-the-Fly)

When you first log in, you will be greeted by an empty dashboard with no data — whether you land there directly or after the welcome screens above.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Empty Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

In LibreFolio, the fastest way to get started is by importing your transaction history directly. You don't need to configure brokers or assets beforehand: the system will automatically create them for you during the import process!

### 📋 Steps

1. **Open the Import Wizard**: Navigate to the **[Transactions](transactions/index.md)** page from the sidebar menu and click the **"Import"** button (:material-file-upload:). You can also start from a broker's detail page — in that case the broker comes pre-selected.

2. **Upload Your Statement**: Drop your broker's report file (`.csv`, `.xlsx` or `.xls`) into the wizard's first step — drag & drop works here — and assign it to a broker, creating the broker **on-the-fly** if it's new. This step is optional: reports uploaded in earlier sessions are already stored, and the next step lists them.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Upload Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Select Files & Parse**: Pick exactly which stored reports to import. Each file gets its parser pre-selected from the broker's default import plugin (overridable per file — use **Generic CSV** for an unknown layout), then LibreFolio reads and validates every row. A consolidated summary shows what will actually be imported: transactions, distinct securities, validation issues, TODOs, warnings and likely duplicates.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Parse Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Extra Steps, Only When Needed**: Depending on what your files contain, up to three more steps appear — **Unify assets** (the same security found under different names or codes), **Corrections** (rows the parser could not fully read), and **Duplicates** (the same movement present in two files imported together). A clean single-file report skips them all.

5. **Review & Import**: Match each instrument to your asset library — or create it **on-the-fly** with details pre-filled from the statement — and check the per-row flags: duplicates (against your existing ledger, or exact copies pending in this import) arrive deselected, and rows dated before the broker's opening date are excluded automatically. For more information, see the **[Import from Broker - Asset Mapping](transactions/import/index.md#asset-mapping)** guide.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Review Step: Asset Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

6. **Save from the Bulk Editor**: Clicking **Import N transactions** hands the selected rows to the bulk editor as new rows — nothing is written yet. Give them one last look, then **Save All** to commit them to your portfolio.

!!! tip "No Need to Re-Upload"

    Reports you uploaded in earlier sessions are already listed in the wizard's **Select Files** step — just tick them again. You can also preview or delete stored reports from the **[Files & Uploads](files/index.md#broker-reports)** page.

!!! info "Guided first import"

    The first time you open the Import Wizard, a contextual guide follows the **N/M** steps your
    files actually trigger. It never uploads, clicks, edits, or saves on your behalf. Its last
    stop highlights the real **Save All** action; the guide advances when you click it, while the
    write still comes from your explicit click. **X** skips only the current Import guide step.
    See
    **[How to Import Transactions](transactions/import/how-to.md#guided-first-import)** for details.

For the full walkthrough see **[How to Import Transactions](transactions/import/how-to.md)**; for the supported brokers and file formats see **[Import from Broker](transactions/import/index.md)**.

---

## 📈 5. Back to the Dashboard

After successfully importing your statement, return to the **Dashboard**. 

LibreFolio calculates your portfolio metrics, asset allocation (by type, sector, geography), and performance history in real-time. You can now see your entire financial situation beautifully plotted!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. What's Next?

Now that your portfolio is populated, you can:

- 🤝 **[Share your broker](brokers/sharing.md)** — Give access to family members or advisors.
- 💱 **[Set up FX rates](fx/index.md)** — Configure currency conversion for multi-currency portfolios.
- ⚙️ **[Customize settings](../admin/settings.md)** — Adjust language, theme, and system preferences.
- 🧭 **[Replay the welcome setup or guided tours](settings/preferences.md#onboarding-and-guides)** — Revisit the welcome screen, quick tour, or import guide any time from Settings → Preferences.
