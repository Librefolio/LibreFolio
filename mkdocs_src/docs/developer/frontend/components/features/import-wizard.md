# 🧭 Import Wizard & Duplicate Detection

The **Import Wizard** (`ImportWizardModal.svelte`) drives the broker-import flow: the user
uploads one or more broker files, the backend BRIM plugin parses each into draft
transactions, and the wizard lets the user review, deduplicate and stage them before they
land in the `TransactionBulkModal` editor.

This page documents the two things that are easy to get wrong when working on it: **how we
decide that two transactions are the same** and **the review UIs built on top of that
decision**.

---

## 🪜 Wizard flow

| Step | Purpose |
|------|---------|
| **1 — Upload** | Select the broker and drop one or more files. Each file is parsed by its BRIM plugin (backend). |
| **2 — Per-file review** | Inspect each file's parse result via `ParseDetailModal` (row counts, warnings, per-file duplicate stats). |
| **3 — Batch resolve** | Rows from all files are merged. The **Batch Duplicate Resolver** groups cross-file duplicates and lets the user pick which copy to keep. |
| **4 — Confirm** | Final table with a status filter. Selected rows are handed to the editor; deselected duplicates and before-opening rows are dropped. |

---

## 🧬 Duplicate detection

Detection runs in **two independent layers**, each producing its own status. A row can only
carry one status; the layers are evaluated so that the stronger signal wins.

### 🗄️ Layer 1 — against the database (backend)

When a plugin parses a file, the backend compares each draft against transactions **already
stored** in LibreFolio and returns two index lists per file: `tx_possible_duplicates` and
`tx_likely_duplicates`. The wizard maps them to:

- **`likely`** — a full match against a stored transaction. **Deselected by default.**
- **`possible`** — the numbers match but something soft (typically the description) differs.
  **Kept selected** for the user to verify.

### 🧺 Layer 2 — in-batch and against the editor (frontend)

The wizard also compares each merged row against **the other rows in this same import** and
against **unsaved rows already staged in the editor** (`TransactionBulkModal`). This catches
the case where the same movement appears in two overlapping exports, or where the user
re-imports a file they already staged but did not save yet. It produces:

- **`pending_duplicate`** — an exact in-batch/editor twin. **Deselected by default.**
- **`pending_possible_duplicate`** — same numbers, different description. **Kept selected**
  for review.

### 🔑 The dedup signature

Both frontend tiers are decided by `buildDedupKey` + `dedupKeysMatch`. The signature is built
**only from fixed and numeric fields** — never from the free-text description:

| Field | Notes |
|-------|-------|
| Broker id | Same broker only |
| Transaction type | `BUY` / `SELL` / `INTEREST` / … |
| Date | Day granularity (first 10 chars) |
| Quantity | Compared within `QUANTITY_TOLERANCE` (`0.0001`) |
| Cash code + amount | Amount compared within `AMOUNT_TOLERANCE` (`0.01`) |
| Per-unit cost override | Distinguishes cashless `ADJUSTMENT` legs booked at different prices (e.g. succession transfers) |
| Asset identity | ISIN / symbol / name / fake-id |

!!! note "Description decides the tier, not the match"

    Two rows are *candidates* when their signatures match within tolerance. The **normalized
    description** (`normalizeDedupDescription`: lower-cased, all whitespace stripped, so
    `DT EMISS.` == `DTEMISS.`) then decides the tier:

    - description **equal** → **sure** duplicate (`pending_duplicate`)
    - description **differs** → **possible** duplicate (`pending_possible_duplicate`)

    This mirrors the product rule: a duplicate is judged on all fixed/numeric data; an equal
    description makes it certain, a differing description only probable.

### 🚦 Status reference

| Status | Layer | Meaning | Default selection |
|--------|-------|---------|-------------------|
| `unique` | — | No match anywhere | ✅ selected |
| `possible` | vs DB | Numbers match a stored tx, description differs | ✅ selected (review) |
| `likely` | vs DB | Full match against a stored tx | ⬜ deselected |
| `pending_possible_duplicate` | in-batch / editor | Signature match, description differs | ✅ selected (review) |
| `pending_duplicate` | in-batch / editor | Signature **and** description match | ⬜ deselected |
| `before_opening` | opening-date gate | `date < broker opening date` | ⛔ blocked (not selectable) |

`before_opening` is **not** a duplicate status — it comes from the broker's opening-date gate
(`beforeOpeningIndices`) and is shown here only because it shares the step-4 status filter.
`duplicateStatusAllowsAutoSelect` implements the default-selection column above.

---

## 🧹 Batch Duplicate Resolver

When several files overlap in time, deselecting twins one by one is tedious. The **Batch
Duplicate Resolver** (foldable panel on step 3) automates it.

- **Grouping** — `buildDuplicateGroups` clusters merged rows by matching signature and keeps
  only clusters that span **≥ 2 source files** (a real cross-file overlap). Each cluster is
  then partitioned by normalized description.
- **Tier** — `DuplicateTier` is `'sure'` when every partition is cross-file (a *total*
  overlap) or `'probable'` when at least one partition is single-file (a *partial* overlap).
  Surfaced to the user as the similarity label (`duplicateSimilarityLabel` →
  *Total* / *Partial*).
- **File priority** — the user orders the source files with an **`OrderableList`** (our custom
  component). `defaultKeeperIndices` keeps exactly one primary row per description-partition,
  taken from the **highest-priority file**; the rest are marked non-keepers and deselected.
- **Recalculate** — after re-ordering priority, the user can recompute the keepers, discarding
  any manual per-row choices and re-deriving them from the new priority order.
- **Member table** — each group renders its members in a **`DataTable`** (`resolverMemberColumns`)
  with a keep checkbox, keeper/duplicate badges, and the file/description columns, so the same
  formatting and icons as the main transactions page are reused.

!!! tip "Why a row can still reach step 4 as a duplicate"

    Only the **cross-file, auto-resolved** twins are removed up front. A row whose duplicate
    lives in the *unsaved editor* (not in another imported file) is still shown on step 4 as
    `pending_duplicate` so the user stays aware of it — it is simply deselected by default.

---

## 🔍 N-way Compare Modal

`TransactionCompareModal.svelte` lets the user compare duplicate candidates **side by side**
before deciding which to keep. It is deliberately presentational (an *N*-column
field-by-field grid) and takes:

- `fields` — the rows to show (date, type, amount, description, …).
- `columns` — one per candidate; each column's header carries the **provenance** (source file
  name, or `#id` when the counterpart is already in the database) plus the broker subtitle.
- `cells` — the parent supplies both a human `display` value and a normalized `cmp` token, so
  purely cosmetic markup differences do **not** count as a real difference; differing cells are
  highlighted.
- `defaultKeep` / `onKeep` — when ≥ 2 columns are `selectable`, a keep-selector is shown.

Because it is *N*-way (not limited to two transactions), it can compare a whole duplicate
group at once, or a candidate against several stored transactions.

---

## 🧾 Per-file parse stats

`ParseDetailModal.svelte` (step 2) shows each file's parse outcome: total rows, plugin
warnings, and the per-file duplicate counts (`unique` / `possible` / `likely`) computed from
Layer 1. It is the fastest way to spot that a re-exported file overlaps an already-imported
one before merging.

---

## 🔗 Related

- **[Transaction Form](transaction-form.md)** — the single-item editor the wizard feeds.
- **[Transaction Staging State](../../state/transaction-draft.md)** — how staged rows become
  `PendingOp`s in the editor.
- **[BRIM Plugin Guide](../../../architecture/patterns/brim_plugin_guide.md)** — the backend
  side that parses each file and reports DB duplicates.
- **[DataTable](../core-ui/data-table.md)** — the grid reused by the resolver.
