# 🧙 How to Import Transactions

<style>
/* Corrections plugin table: plugin column keeps icon+name on one line */
.md-typeset details.warning table th:first-child,
.md-typeset details.warning table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details.warning .md-typeset__table table td { vertical-align: middle; }
</style>


Learn how to use the Broker Report Import Module (BRIM) to import your transactions step-by-step.

---

## 🚀 Step-by-Step Guide

1. Export a transaction report from your broker (usually a CSV file — check your broker's help center).
2. In LibreFolio, navigate to the **[Transactions](../index.md)** page.
3. Click the **Import** button (:material-file-upload:) in the page header.
4. The **Import Wizard** opens — you can drag-and-drop your statement file into its upload step.
5. Review the preview — check that dates, amounts, and asset names look correct.
6. Click **Import N transactions** — the selected rows land in the **bulk editor** as new rows, where you can give them one last look (or keep editing) before **Save All** commits them to your portfolio.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Select Files &amp; Parser" alt="Wizard Step 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analysis &amp; Parsing" alt="Wizard Step 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Asset Resolution" alt="Asset Resolution">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Duplicate Detection">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 4: Review &amp; Import" alt="Review and Import">
</div>

!!! tip "On-the-fly Broker & Asset Creation"

    If the imported report contains a broker account or assets that are not yet created in LibreFolio, you don't need to exit the import flow! The wizard will guide you to create the missing **[Brokers](../../brokers/index.md)** and **[Assets](../../assets/index.md)** on-the-fly, pre-filling details from the statement.

!!! tip "You can also use the Files section"

    The **[Files](../../files/index.md)** section (BRIM tab) lets you manage uploaded broker reports centrally, re-import them, or delete them.

---

## 🧙 The Import Wizard Steps

The wizard has **four steps you always see** and **three that appear only when your files
actually need them**. The progress bar shows only the steps that apply to your import, so a
clean single-file report stays a short flow, while a messy multi-file one gets exactly the extra
questions it deserves — and no others.

| Step | Always shown? | Appears when |
| :--- | :--- | :--- |
| 1 · Upload Report File | ✅ Always | — |
| 2 · Select Files & Parser | ✅ Always | — |
| 3 · Analysis & Parsing | ✅ Always | — |
| 🧬 Unify Assets | ⚪ Optional | The same security was found under more than one name or code |
| 🔧 Corrections | ⚪ Optional | The parser booked rows it could not fully understand |
| 🧹 Duplicates | ⚪ Optional | The same movement appears in two of the files you are importing together |
| 4 · Review & Import | ✅ Always | — |

!!! info "The optional steps run in this order for a reason"

    Each one is built on the answers of the one before it. Securities are unified **first**, so
    that when you later attach an instrument to a corrected row you pick from a clean list
    instead of from three copies of the same bond. Corrections come **before** the duplicate
    check, because a purchase the parser could only read as a cash withdrawal would otherwise be
    compared against cash withdrawals — missing a real duplicate, or inventing one that does not
    exist.

### 🧙 Step 1: Upload Report File

This step accepts CSV or XLSX reports exported from your broker. You can select files manually or drag-and-drop them directly into the wizard. Assign a broker to each file, either file by file or with the global selector — and if the broker does not exist yet, you can create it on the fly from here.

The step is **optional**: reports uploaded in earlier sessions are already stored, and you can pick them in the next step without re-uploading.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Step 2: Select Files & Parser

This step lists the reports stored for each broker, grouped in collapsible per-broker panels, so you can pick exactly which ones to parse — including files uploaded in an earlier session (the files you just uploaded are pre-selected). Reports can be previewed or deleted from this step. Each file gets its own parser: the system detects the broker format automatically (e.g. Degiro, Directa, Interactive Brokers, Intesa Sanpaolo, Crédit Agricole), and you can override the choice per file. If you upload a generic spreadsheet, use the **Generic CSV** parser to manually map your columns (date, type, quantity, asset, net cash) to LibreFolio fields.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Step 3: Analysis & Parsing

The system parses the files, validating dates, numbers and currencies. You will see a progress bar indicating the parsing speed and status. Once analysis completes, any warning or error in parsing will be summarized before continuing.

The summary tiles at the top are **consolidated**: once parsing completes they describe what will actually be imported — the selected transactions and the distinct securities after unification — not the raw per-file rows; **View All** opens the aggregate detail. If you go back and change a parser choice, use **Re-parse all** to recompute the results.

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

??? abstract "🧬 Unify Assets — appears when the same security was found under more than one name or code"

    **When you will see it.** Whenever two or more of the instruments read from your files look
    like the same security — because they share an ISIN, a ticker or a name — or when your files
    describe one bond under two different codes. A single-file import in which every security is
    distinct never shows this step.

    **Why it exists.** Each file is read independently, so the same BTP appearing in a holdings
    report *and* in a movements report arrives as two unrelated instruments. Left alone, that
    becomes two duplicate assets in your library — and two identical-looking entries in every
    list that follows, where half your rows would silently attach to half the instrument.

    **What you do here.** The wizard proposes a grouping and you confirm, adjust or reject it.
    Each card is one security, and its border tells you who decided:

    | Border | Meaning |
    | :--- | :--- |
    | 🟩 solid green | **Unified** — the engine is certain (same ISIN, ticker or name), or you said so |
    | 🟨 dashed amber | **To confirm** — a resemblance the engine will not act on by itself |
    | ⬜ plain grey | **On its own** — nothing to decide |

    - **Merge or separate** with the `⋮` menu on each card, or by dragging one card onto another.
    - **Elect the leading code** by clicking one of the coloured badges: it takes a ⭐ and becomes
      the identifier the asset will be known by. The codes that lose are kept as alternative
      identifiers, so nothing your files knew is thrown away.
    - **Rename** a group with the pencil. A group already matching something in your library
      carries an **in archive** badge, and your library's own name wins.
    - **Restore automatic grouping**, at the top, undoes every merge, split and code election in
      one click if you want to start over.

    !!! tip "This is where dual-code bonds get settled"

        Italian retail bonds (BTP Valore, BTP Più, BTP Italia) are subscribed under one ISIN and
        traded under another. Elect the **tradeable** code as the leading one — it is the only
        one a price provider can quote — and leave the subscription ("CUM") code as an
        alternative. See [Create & Edit Assets](../../assets/create-edit.md) for the full story.

??? warning "🔧 Corrections — appears when the parser booked rows it could not fully understand"

    **When you will see it.** When your report contains lines the plugin recorded but could not
    read completely: a trade whose instrument or quantity the file simply does not carry, or a
    fee or tax it could not attach to any security. Reports that parse cleanly skip this step.

    This step exists only if the broker's plugin **flags rows for review** — a plugin that
    never emits these flags will never open it. The plugins that currently do:

    | Plugin | Flags it can raise |
    |--------|--------------------|
    | <img src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> [Crédit Agricole](credit_agricole.md) | Bundled trade+fees lines (offered for **splitting**), cash rows that could not be linked to an instrument, duplicate-relevant blockers |


    As more plugins learn to flag rows, they will be listed here.

    **Why it exists.** A purchase the plugin could only record as a cash withdrawal — because the
    file gave it neither a quantity nor an instrument — would be compared against cash
    withdrawals in the duplicate check. A genuine duplicate would be missed, or an imaginary one
    invented. Fixing these rows *before* the comparison is the only moment it works.

    **What you do here.** Rows are grouped by the nature of the question, so you settle similar
    cases together. For each one you can:

    - **Correct it** — choose the right transaction type and, where it applies, the instrument
      and quantity. Only the types that make sense for that row are offered; a fee or tax has no
      quantity field and may legitimately have **no instrument at all** ("broker charge").
    - **Split it** — when one line bundles a trade together with its fees or taxes.
    - **Keep it as read** — you agree with what the plugin did. The row greys out and stays in
      the list, so you can always see, and revise, what you decided.
    - **Reset** a single row, or every row in a group, and start again.

    A **show-me-the-source** button highlights every original line behind a warning in the file
    preview, so you can check the statement itself before deciding.

    !!! danger "Blocking rows"

        Rows marked in **red** are blocking: the import cannot be saved until you settle them.
        Amber rows are advisory — you may leave them exactly as they are.

??? note "🧹 Duplicates — appears when the same movement is in two of the files you are importing together"

    **When you will see it.** Only when two or more files in this import overlap in time and
    contain the same movement. Duplicates against transactions **already in your database** do
    *not* open this step — they simply arrive at the final review already unchecked.

    **Why it exists.** Overlapping exports are normal: you download a full-year statement, then a
    quarterly one repeating part of it. Unchecking twins one at a time is tedious and easy to get
    wrong, so the wizard groups them and lets you decide once.

    **What you do here.**

    - **Order your files by priority.** Drag them into the order you trust: the copy kept for each
      group is taken from the highest-priority file.
    - **Recalculate** after re-ordering, to re-derive every choice from the new priority.
    - **Override individually** in the group table: every row carries a **Keep** checkbox and shows
      which file it came from and whether it is the copy being kept. **Reset defaults** restores the
      automatic choices.
    - **Compare side by side** when two copies differ and you want to see exactly how before
      choosing — the compare modal highlights the fields that differ.

    Each group is labelled **Total** (the files agree on every detail — a pure overlap) or
    **Partial** (something differs, so it deserves a look).

### 📦 Step 4: Review & Import

The final review shows every transaction to be imported in a spreadsheet-like grid, and is where
each instrument is finally matched to your library.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Review and Import grid" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The table displays:

- **Date**: The execution date.
- **Type**: BUY, SELL, DIVIDEND, DEPOSIT, etc.
- **Asset**: The matched asset from your library.
- **Quantity**: The number of units/shares.
- **Price**: The unit price.
- **Net Amount**: The total cash impact.
- **Fees/Taxes**: Commissions and taxes included.

#### 🗂️ Asset Resolution

A collapsible panel above the grid lists every instrument found in your files and lets you say
what it is in your library. One search field covers everything, in two sections:

- **In this import** — the instruments read from your files, already unified by the step above.
  One that is already linked to your library shows an **in archive** badge and appears here only,
  never twice.
- **In archive** — everything else in your asset library.

Auto-matched candidates are pinned at the top of the search field with a confidence badge
(**Exact** / **High** / **Medium** / **Low**), so the most likely match is usually one click away.

If neither section has what you need, the **Create «…»** button at the bottom of the list is
always visible and already carries whatever you typed — you never have to go looking for it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asset resolution panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The ✏️ pencil next to a matched instrument opens the full asset editor without leaving the
wizard, so you can fix an identifier or a name and come straight back. When an instrument matches
**two** assets already in your library, the wizard detects the ambiguity and offers a **merge**
action to fold one into the other.

!!! question "«Which code is the main one?»"

    When your report carries an identifier and the asset — or the price provider — carries a
    different one of the same kind, LibreFolio does not overwrite anything. It asks which one
    should lead, showing where each value came from: **from the provider**, **already saved** or
    **from the report**. The one you elect becomes the asset's identifier; the others are kept as
    alternative identifiers, so the next import recognises the security either way.

    The provider's value is preselected, because it is the only one with a price feed behind it.

#### ⛔ Broker Opening Date

If the target broker has an opening date, the wizard flags rows whose date is **strictly before**
it with the status `Before opening`. Those rows are deselected and cannot be imported; a row on
the opening day remains valid. If the date is wrong, a per-broker banner lets you **Edit broker
date** by hand or **auto-fix** it to the earliest transaction date found, then re-check/refresh so
the wizard re-evaluates every row against the updated date.

#### ⚠️ Asset Notices

Some plugins attach advisory notices to extracted assets. For example, Intesa Sanpaolo and
Crédit Agricole can warn that a security may be matured or redeemed. These notices appear as
amber banners when you create or map the asset; they do not block the import.

#### ⚠️ Duplicates Against Your Database

Independently of the optional **Duplicates** step — which compares the imported files *with each
other* — every row is also compared with the transactions already in your database, on type,
date, amount, quantity and description. These do not open a step of their own: they are flagged
right here with a status badge.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Duplicate detection badges" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| UI Badge | Confidence Level | Criteria / Matching Rules |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Basic fields and description match, and asset auto-resolved (highly confident duplicate). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Basic fields and description match, but asset is not resolved. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Basic fields match, and asset is auto-resolved (but description differs or is empty). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Basic fields (type, date, quantity, amount) match, but asset is not resolved. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | The transaction has no matching records in the database and is classified as new (no duplicate detected). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ UNRESOLVED</span> | — | The broker or financial instrument was not matched to an existing entity in the database (requires resolution in Step 4 before importing). |

By default, the wizard automatically unchecks "Likely" duplicates to prevent double-entry, but
you can override this choice. A banner above the grid summarizes why rows are deselected.

Two more badges come from comparisons *inside this import* rather than against the database:

| UI Badge | Meaning |
| :--- | :--- |
| ⧉ **Duplicate in batch** | Exact copy of a row still pending in this import (or already staged in the bulk editor) — deselected by default. |
| ≈ **Possible batch dup** | Same, but the description differs — stays selected so you can decide. |

Click **Import N transactions** to hand the selected rows to the **bulk editor** as new rows:
nothing is written to the ledger yet. Give them one last look — or keep editing — and then
**Save All** to commit them to your portfolio.
