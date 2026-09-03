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

The **Import** (`Upload` icon) button launches the **BRIM** wizard, which imports your broker's exported statements in bulk: it parses the files, validates every row, unifies the securities found, checks for duplicates, and lets you review everything before anything is written.

The wizard has **four steps you always see** and **three that appear only when your files actually need them** — the progress bar shows just the steps that apply to your import, so a clean single-file report stays a short flow.

### 🖼️ The Import Flow

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-import" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="🗂️ Uploaded Reports Modal" alt="Uploaded Reports Modal">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Wizard — Upload" alt="Import Wizard Upload">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="🧙 Wizard — Select Files" alt="Import Wizard Select Files">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧙 Wizard — Parse" alt="Import Wizard Parse">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🧙 Wizard — Review: Resolve Assets" alt="Import Wizard Asset Resolution">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="🧙 Wizard — Review: Duplicate Badges" alt="Import Wizard Duplicate Badges">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Bulk Editor after Import" alt="Bulk Editor after Import">
</div>

### ✅ Always Shown

1. **Upload** — Drop one or more statement files (`.csv`, `.xlsx`, `.xls`) and assign a broker to each, either file by file or with the global selector. You can also create the broker on the fly from here. This step is **optional**: reports uploaded in earlier sessions are already stored, and you can pick them in the next step without re-uploading.
2. **Select Files** — Every report stored for your brokers, grouped in collapsible per-broker panels; the files you just uploaded are pre-selected. Each selected file gets its own parser: the broker's default import plugin is pre-selected when compatible, and you can override it per file (use **Generic CSV** to manually map an unknown layout). Reports can be previewed or deleted from this step.
3. **Parse** — The files are parsed one after another, with a progress bar and a per-file results table (transactions read, assets found, validation issues, field TODOs, warnings, likely duplicates). The summary tiles are **consolidated**: once parsing completes they describe what will actually be imported — the selected transactions and the distinct securities after unification — not the raw per-file rows; **View All** opens the aggregate detail. Parser notices and warnings are acknowledged before continuing, and you can **Re-parse all** after going back and changing a parser choice.
4. **Review** — The final grid lists every transaction with translated type labels and a per-row status: `✓ Unique`, `ℹ Possible dup` (matches your ledger, but the description differs), `⚠ Likely dup` (matches your ledger — deselected by default), `⧉ Duplicate in batch` (exact copy of a row still pending in this import or in the editor — deselected by default), `≈ Possible batch dup` (same, but the description differs — stays selected), `✗ Unresolved` (the instrument still needs a match) or `⛔ Before opening`. A banner above the grid summarizes why rows are deselected. This is also where each extracted instrument is matched to your asset library — see below.

### 🧩 Only When Needed

- 🧬 **Unify assets** — appears when the same security was read from two files under different names or codes. Each file is parsed independently, so the same bond can arrive twice; here you confirm, adjust or reject the proposed grouping, and elect the leading identifier (⭐) the asset will be quoted under. A single-file import with all-distinct securities never shows this step.
- 🔧 **Corrections** — appears when the parser booked rows it could not fully understand: cash movements that may really be trades (blocking, red), amounts that bundle a trade with its fees or taxes (splittable into separate legs), and charges with no instrument attached. For each row you correct it, split it, or deliberately **keep it as read** — settled rows stay visible with their badge, so every decision remains revisable. A banner at the top links to **open an issue on GitHub** in case a row keeps looking wrong: it may be an importer bug rather than your data. The wizard will not continue until every row is settled.
- 🧹 **Duplicates** — appears when the same movement shows up in two of the files you are importing **together** (overlapping exports are normal: a full-year statement, then a quarterly one repeating part of it). Every row in a group carries a **Keep** checkbox — untouched groups follow the **file-priority list** (drag the files into the order you trust, then **Recalculate by priority** to recompute the defaults), and any group can be overridden by hand, restored with **Reset defaults**, or inspected in an **N-way compare modal** that highlights the differing fields. Groups are labelled *Total overlap* (every row has an exact twin across the files — keeping one copy is the safe call) or *Partial* (at least one row has no exact twin — worth a look). Duplicates against transactions **already in your database** do not open this step: they simply arrive at the Review already deselected.

!!! info "Why this order"

    Each optional step is built on the answers of the one before it. Securities are unified **first**, so the Corrections step offers one clean instrument list instead of three copies of the same bond. Corrections come **before** the duplicate check, because a purchase the parser could only read as a cash withdrawal would otherwise be compared against cash withdrawals — missing a real duplicate, or inventing one. The database comparison runs on the corrected rows, just before the Duplicates step.

### 🗂️ Resolving Assets in the Review Step

A collapsible panel above the final grid lists every instrument found in your files. For each one you can:

- **Pick an existing asset** — auto-matched candidates are pinned at the top of the search field with a confidence badge (Exact / High / Medium / Low).
- **Create a new asset** directly from the wizard, pre-filled with the details extracted from the statement.
- **Edit the matched asset** with the pencil, without leaving the wizard.
- **Merge** when the instrument matches two assets already in your library — the wizard detects the ambiguity and offers the merge action.

Rows whose instrument is still unresolved are marked `✗ Unresolved` and cannot be imported until resolved.

### ⛔ Before the Broker Opening Date

If the target broker has an opening date, rows dated **strictly before** it are flagged `⛔ Before opening`, automatically deselected, and kept out of the import; a row on the opening day stays valid. A per-broker banner in the Review step lets you **edit the broker date** or **auto-fix** it to the earliest transaction date found, then **recheck** the rows against the updated date.

### 📦 Importing into the Bulk Editor

Clicking **Import N transactions** does not write to the ledger directly: the selected rows are handed to the **bulk editor** as new rows, where you can give them one last look — or keep editing — and then **Save All** to commit them to your portfolio.

For the complete walkthrough see **[How to Import Transactions](../transactions/import/how-to.md)**; for the supported brokers, formats and plugin-specific notes see **[Import from Broker (BRIM)](../transactions/import/index.md)**.

---

## ⚠️ Asset Notices

Some broker plugins attach advisory notices to extracted assets. For example, Intesa Sanpaolo and Crédit Agricole can warn that a security may be matured/redeemed and hard to find online. The create-asset modal groups these notices into amber banners; they are informational and do not change the transaction import.

---

## 🗂️ Uploaded Reports

Click the **Uploaded Reports** (`FileText` icon) button to manage the BRIM report files stored for this broker. The modal lets you:

- Review the uploaded reports (name, upload date, size, status), with a quick **preview** of each file's content.
- **Upload** new reports directly — they are auto-assigned to this broker and become available in the wizard's Select Files step.
- **Delete** reports you no longer need.
- Jump to the full **[Files & Uploads](../files/index.md#broker-reports)** page, pre-filtered on this broker.
