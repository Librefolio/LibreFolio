# 🧙 How to Import Transactions

The **Import Wizard** turns the reports you download from your broker into transactions. You check
what it read and settle its doubts; nothing is saved until you press **Save All**.

---

## 🚀 Step-by-Step Guide

1. Export a transaction report from your broker: its page in **[Supported Brokers](index.md)** says
   which file.
2. On the **[Transactions](../index.md)** page, click **Import** (:material-file-upload:).
3. Drop the report into the wizard, assign it to its broker and follow the steps below.
4. Click **Import N transactions**: the rows open in the bulk workspace, not saved yet.
5. Give them a last look and click **Save All**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Select Files &amp; Parser" alt="Wizard Step 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analysis &amp; Parsing" alt="Wizard Step 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Asset Resolution" alt="Asset Resolution">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Duplicate Detection">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 4: Review &amp; Import" alt="Review and Import">
</div>

---

## 🧙 The Import Wizard Steps

Four steps are always there; the others appear only when your files need them, and the progress
bar shows only the steps of the current import.

| Step | When you see it |
| :--- | :--- |
| 1 · **Upload** | Always |
| 2 · **Select Files** | Always |
| 3 · **Parse** | Always |
| 🧬 **Unify assets** | The same security appears under more than one name or code |
| 🔧 **Corrections** | The importer recorded rows it could not fully understand |
| 🧹 **Duplicates** | The same movement is in two of the files you import together |
| 4 · **Review** | Always |
| ⚖️ **Align with the bank** | Report sets only, when the bank's figures differ from LibreFolio's |

### 📤 Step 1: Upload

Drag your reports into the wizard, or click to choose them (CSV or XLSX), and assign each one to
its broker — or all at once with **Assign broker for uploads**. A missing broker can be created
from the same list (**Create new**).

- Every report you upload is kept: to reuse one, skip this step with **Next: Select Files**.
- When one account comes in several exports (e.g. [Danske Bank](danske-bank.md)), upload them
  together: if one is missing, the wizard stays here and names it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 A file in the wrong broker {: #wrong-broker }

When you click **Next: Select Files**, the wizard checks each file you have just uploaded against
its broker's **Default Import Plugin**. If that plugin cannot read a file, the file probably
belongs to another broker, and the wizard asks you about it before going on (*This file may belong
to another broker*). From top to bottom, it shows:

- **Assigned to** — the broker the file is in, with its icon, and its default plugin, marked
  *cannot read it*;
- **Notes from the plugin** — why that plugin cannot read the file, when it says why: in your
  language when a translation exists;
- **Move it to** — the broker whose default plugin *can read it*. When the default plugins of
  several brokers read it, the prompt lists those brokers instead: choose one, the first is already
  selected.

Then choose:

- **Move to ‹broker›**, with that broker's icon — the file is uploaded to that broker, in the same
  session, and removed from the wrong one. If the move fails, an error says so and the file stays
  where it was;
- **Keep it here** — the file stays, and the wizard reads it with another plugin that can, as
  before: you see it in the **Plugin** column of **Select Files**;
- **Remove the file** — the file is deleted.

One prompt per file, in turn (*File 1 of 3*); closing it keeps the file. If you remove every file
you have just uploaded, the wizard stays on **Upload**, ready for others. When none of your brokers
has a default plugin that reads the file, the prompt names the plugins that read it — or says that
none can — and offers only to keep or remove it.

Brokers without a default import plugin are never questioned, and neither are the reports you
reuse without uploading them again.

### 🗂️ Step 2: Select Files

Each broker's panel lists its stored reports, with the files you have just uploaded already ticked.
Tick the files to read and click **Parse (N)**.

The importer of each file is detected for you: change it in the **Plugin** column if it is wrong,
and for a CSV you built yourself choose **[Generic CSV](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Report sets** are one card, ticked as a whole. **Read as**, in its header, changes how the set is
read, and each file's **⋮** menu can take it out of the set (**Read alone with ‹plugin›**,
**Remove from the set**) — [details](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Report set card in Select Files with the Read as list open: Danske Bank (detected) and Read the files one by one" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="A cash file's ⋮ menu in a report set: Preview, Remove from the set and Delete" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Parse is disabled?** A ticked file has no plugin, or a ticked set is incomplete or only partly
ticked (a dash in its checkbox): choose the plugin, use **Upload the missing file**, or tick or
untick the whole set.

### 🧠 Step 3: Parse

LibreFolio reads each file, checks it and sums it up in a table:

| Column | What it counts |
| :--- | :--- |
| 📊 | Transactions read |
| 🏦 | Securities found |
| ✗ | Securities not matched to your assets yet — you match them in **Review** |
| 🔴 | Validation issues: rows that could not become transactions |
| 🔧 | Fields to fill in before saving (red when one blocks the save) |
| ⚠️ | Importer warnings, such as skipped rows |

The tiles above the table count what will really be imported; **View All** opens the details.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analysis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Warnings**: **Continue** lists them first; read them, then click **Continue anyway**.
- **A file failed**: a banner says why. Fix its plugin in **Select Files**, then click
  **Re-parse all**.

### 🧩 Steps that appear only when needed {: #only-when-needed }

Depending on what **Parse** finds, up to three steps can come before **Review**, in this order.
Open the one the wizard shows you:

??? abstract "🧬 Unify assets — when the same security appears under more than one name or code"

    Your files describe the same security more than once — under two names or codes, or in two files.
    Unify it here, or it becomes two assets with its transactions split between them.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Import wizard — Unify Assets step with a proposed group">
    </div>

    Each card is one security: a **solid green** border means unified, **dashed amber** means to
    confirm, **grey** means nothing to decide.

    - **Confirm** or **Split** a proposal; merge or separate cards with **⋮** (**Merge with…**,
      **Remove from group**) or by drag and drop.
    - **Click a code badge** to make it the leading code (⭐) — pick the one prices are quoted on; the
      others stay as alternatives.
    - **Rename** with the pencil; a security already in your library (**in archive**) keeps its name.
    - **Continue** waits until no proposal is open: **Confirm all (N)** settles them at once, and
      **Restore automatic grouping** starts over.

??? warning "🔧 Corrections — when the importer recorded rows it could not fully understand"

    The importer recorded rows it could not fully understand — today, rows from
    [Crédit Agricole](credit_agricole.md) and [Danske Bank](danske-bank.md) reports.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Import wizard — Corrections step with flagged rows">
    </div>

    Rows are grouped by question. Give each one an answer:

    - **Correct it**: pick the type and, where it applies, the security and the quantity, then
      **Apply correction**. A fee or tax may belong to **No instrument (broker charge)**.
    - **Split it**: separate the price from the commissions, taxes or accrued interest shown on your
      contract note.
    - **Keep as recorded**: accept what the importer read.

    **Row N in the file** shows the original line, and **Restore** undoes an answer. **Continue** waits
    for every answer; **Keep the remaining N rows as read** answers all the open ones.

??? note "🧹 Duplicates — when the same movement is in two of the files you import together"

    The same movement is in two of the files you import together, such as a yearly and a quarterly
    statement. Matches with transactions already saved do not open this step: **Review** flags them.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Import wizard — Duplicates step with a cross-file pair">
    </div>

    - **File priority**: drag the files into the order you trust and click **Recalculate by priority**.
      Each group keeps the copy from the highest file — never one already saved or waiting in the bulk
      workspace.
    - **Keep**: tick the copies to import, row by row; **Reset defaults** restores the automatic choice.
    - **Compare** shows the copies side by side, differences highlighted.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="N-way compare modal with per-field differences highlighted">
    </div>

    Groups are listed under **Total overlap** (identical copies) and **Partial overlap** (something
    differs).

### 📦 Step 4: Review {: #review }

Every row to import in one grid — status, date, type, security, broker, quantity, cash and tags,
plus the file when you import several.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Review and Import grid" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Match each security

The **Resolve Assets** panel above the grid lists the securities of your files. Match each one:

- Search **In this import** and **In the archive** (your library) from one field. Likely matches
  come first, with a confidence badge (**Exact** to **Low**); a single match is already selected.
- **Create “…”** opens the new-asset form, filled in with the name and codes from the report.
- ✏️ **Inspect / edit** opens the chosen asset; **Merge** appears when two of your assets match.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asset resolution panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

If the report's code differs from the asset's or the price provider's, LibreFolio asks which one is
the main one. The provider's code, the one with prices, is preselected; the others stay as
alternatives. An amber note on a new asset, such as a possible maturity, is only advice.

#### 🚦 Read the status badges

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Duplicate detection badges" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge | Meaning | Ticked at first? |
| :--- | :--- | :--- |
| **✓ Unique** | Nothing similar is saved | ✅ |
| **ℹ Possible dup** | A saved transaction has the same type, date, quantity and amount, but another description | ✅ — check it |
| **⚠ Likely dup** | A saved transaction matches, description included | ⬜ |
| **⧉ Duplicate in batch** | Exact copy of another row of this import, or of the bulk workspace | ⬜ |
| **≈ Possible batch dup** | The same, with another description | ✅ — check it |
| **✗ Unresolved** | Its security is not matched yet | ✅ — match it or untick it |
| **⛔ Before opening** | Dated before the broker's opening date | Cannot be imported |
| **⏮ Already in LibreFolio** | Report sets: older than the history LibreFolio holds; hidden behind a counter | Cannot be imported |

Click a duplicate badge to compare the row with its twin; a banner says why rows are unticked. A
currency conversion is one row, imported whole.

#### ⛔ Rows before the broker's opening date {: #opening-date }

Rows dated before the broker's opening date cannot be imported (the opening day itself is fine). If
the date is wrong, the banner offers **Set opening to ‹date›** — the earliest row date — and
**Edit broker date**; the rows are then checked again.

#### 📥 Import the rows

**Import N transactions** is enabled once at least one row is ticked and every ticked row has its
security. A last duplicate check runs first: changed duplicates between files send you back to
**Duplicates**, and a changed selection keeps you here with a message — check the ticks and click
again.

??? info "⚖️ Align with the bank — after Review, only for a report set such as Danske Bank"

    For a report set such as [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio
    compares what it will hold with the bank's balances and positions. Cards show each point —
    **Starting point**, **After the gap**, **End-of-period check** — above the proposed corrections,
    all ticked. Untick those you do not want and click **Continue**; if the comparison failed, continue
    without them.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Align with the bank: the Starting point, After the gap and End-of-period check cards above the proposed corrections tagged gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Save in the bulk workspace

The rows arrive in the bulk workspace unsaved. Check or edit them, then click **Save All**: it waits
for the rows listed in red, and asks before saving the values listed in amber that you have not
verified (**Save anyway**).

---

## 🧭 Guided First Import {: #guided-first-import }

The first time you open the wizard, a guide bubble walks you through it:

- its **Step N of M** counts only the steps you see; the tips for optional steps wait for an import
  that needs them;
- it only points: it never clicks, uploads or edits for you;
- it ends by highlighting **Save All**, without pressing it;
- **X** skips only the current tip.

To see it again, choose **Replay at next trigger** for the **Import guide** in
**[Settings → Preferences → Onboarding and guides](../../settings/preferences.md#onboarding-and-guides)**:
it starts with your next import.

---

## 🔗 Related

- 🏦 **[Supported Brokers](index.md)** — which file to export
- 🛠️ **[Import Wizard internals](../../../developer/frontend/components/features/import-wizard.md)** — for developers
