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

The stepper is a **conditional state machine**, not an index. `StepId` is a union of seven ids
and `STEP_DEFS` holds their canonical order; three of them are skipped when they have nothing to
do, so `currentStepId` is never a number and there is nothing to renumber when a step is added.

| # | `StepId` | Always shown | Purpose |
|---|---|---|---|
| 1 | `upload` | ✅ | Pick the broker, drop one or more files. |
| 2 | `select` | ✅ | Pick which of the broker's stored files to parse and, per file, which BRIM plugin reads it. |
| 3 | `analyze` | ✅ | Parse each file (backend), show per-file stats via `ParseDetailModal`. |
| — | `assets` | ⚪ conditional | **Unify assets** — decide how many distinct instruments the files actually describe (`AssetGroupStep`). |
| — | `fix` | ⚪ conditional | **Corrections** — retype rows the plugin flagged as incomplete (`FixFlaggedStep`). |
| — | `duplicates` | ⚪ conditional | **Batch Duplicate Resolver** — arbitrate cross-file twins. |
| 4 | `review` | ✅ | Final grid, asset resolution against the DB, then hand off to `TransactionBulkModal`. |

### 🎚️ What makes a step appear

`stepIsActive(id)` is the single source of truth. `enterNextActiveStep()` walks forward and lands
on the first step that returns `true`, so auto-skip is a property of the predicate, not a special
case in the navigation:

```ts
if (id === 'assets')     return assetGroups.some((g) => g.members.length > 1 || g.state === 'proposed');
if (id === 'fix')        return fixStepRows.length > 0;
if (id === 'duplicates') return duplicateGroups.length > 0;
return true;
```

!!! warning "Database collisions do **not** open the `duplicates` step"

    That step exists for the one decision only the user can make: which copy to keep when the
    same movement appears in two of the files being imported *together*. A row that collides
    with something already stored needs no arbitration here — it simply reaches `review`
    deselected.

`visibleSteps` keeps the **current** step in the progress bar even when its reason to exist
disappears mid-interaction: a user who resolves the last flagged row should not watch the step
they are standing on vanish from under them.

### ⚠️ Why `assets` precedes `fix`

This ordering is load-bearing, and the code says so in `STEP_DEFS`. `fixAnalysisAssets` — the
list behind the asset picker of the correction step — is **derived from `assetResolutions`**.
Because `fakeRemap` is per-file, the same bond read from two files used to produce two
resolutions, so that picker showed **two indistinguishable entries for one security**: half the
corrected rows would attach to half the instrument, invisibly.

Unifying first makes that choice unambiguous and asks it once. Inverting the order would not
just be less tidy — it would force every choice made in `fix` to be migrated or asked again after
the merge.

!!! note "The grouping is folded into the merge, not bolted next to it"

    `applyAssetGrouping()` runs inside `mergeAllTransactions()`, after the per-file loop and
    **before** `rebuildDuplicateGroups()`. It rewrites `tx.asset_id` onto the group
    representative and drops the absorbed entries from `assetMap`. Three consequences come for
    free: the correction picker shows one entry per security, cross-file duplicates finally
    match (the dedup signature includes asset identity), and the final import needs no
    translation table because the links are already rewritten.

---

---

## 🧩 Step components

The three conditional steps each have their own component, all under
`lib/components/transactions/import/`.

### 🧬 `AssetGroupStep.svelte` — unify assets

Answers one question: *how many distinct instruments do these files actually describe?* The
engine (`lib/utils/assetGrouping.ts` + `assetSimilarity.ts`) proposes a partition, the user
adjusts it. See **[Asset Identity](asset-identity.md)** for the matching rules.

The visual grammar is three states, and it is the whole interface:

| State | Border | Meaning |
|---|---|---|
| `confirmed` | solid green | Strong evidence (same ISIN, ticker or normalized name), **or** the user decided |
| `proposed` | dashed amber | Weak evidence — the engine will not act on it alone |
| `single` | plain grey | Nothing to decide |

- **Interaction is always available twice.** Drag-and-drop is an accelerator; the `⋮` menu
  (*Merge with…* / *Extract from group*) is the primary path, because it is the one that works
  from the keyboard and the one E2E tests can drive.
- **Any user gesture promotes a group to `confirmed`** (`userTouched`), after which no
  recalculation may overwrite it.
- **Primary election happens here**, by clicking an identifier badge: the elected value is
  ordered first, and every downstream consumer already reads `groupIsins[0]` as "the code to
  use", so the choice reaches asset creation, candidate search and the identifier prompt without
  any of them learning a new concept.
- **Overrides are stored as a whole partition, not a delta**, keyed by member *content*
  (`fileId|isin|symbol|name`) rather than by `fakeAssetId` — which the wizard reallocates on
  every re-merge. That is what lets an override survive a re-parse of the same files, and what
  makes a **Restore automatic grouping** button meaningful.

### 🔧 `FixFlaggedStep.svelte` — corrections

Renders the rows a plugin booked but could not fully understand: `blocker` (red, blocks Save) and
`warning` (amber, advisory), grouped by the nature of the question so similar cases are settled
together. Fee/tax rows have no quantity field and may legitimately carry **no asset at all**.

Two invariants are worth knowing before touching it:

- **Settled rows stay visible and revisable.** A decision the user cannot see is a decision they
  cannot revise.
- **Accepting resets first.** *Keep as read* calls `resetFixRow` before declaring the row kept —
  otherwise the row would carry an already-applied correction under a label that denies having
  one. Symmetrically, editing a settled row makes its decision lapse (`onreopen`), because a
  badge that contradicts the form underneath it is a badge that lies.

### 🔎 `ImportAssetPicker.svelte` — one field to name the instrument

A single `SearchSelect` with **sections instead of modes**: *In this import* (already unified)
then *In archive*, with a sticky **Create «…»** footer carrying the typed query.

- An instrument already bound to an archived asset appears **once**, in the import section, with
  an *in archive* badge. Listing it in both would be a trap: same security, two rows, no way to
  tell which one behaves.
- Selecting an archive id that is hidden by that dedup resolves **up to the group**, not to
  itself — otherwise the field would look empty immediately after being answered.
- The value is a **discriminated union** (`{kind:'asset',id}` | `{kind:'none'}` | `null`), not
  `number | null`: *"belongs to no instrument"* and *"not answered yet"* are different answers,
  and conflating them is what previously forced the caller to keep two parallel `Set`s in sync.
- There is no `allowNone` flag — passing `noneLabel` is what enables the row. Offering an answer
  you cannot label is a state that should not be expressible.

Section headers are a `SearchSelect` primitive (`SelectOption.header`), filtered by the pure
module `ui/select/optionFilter.ts`: headers never match a query, are skipped by keyboard
navigation, and are dropped in a second pass when the filter emptied their section — a title
claiming a category the list no longer has is invisible in the common case, which is exactly why
it ships.

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
(`beforeOpeningIndices`) and is shown here only because it shares the review-step status filter.
`duplicateStatusAllowsAutoSelect` implements the default-selection column above.

---

## 🧹 Batch Duplicate Resolver

When several files overlap in time, deselecting twins one by one is tedious. The **Batch
Duplicate Resolver** (the `duplicates` step) automates it.

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

!!! tip "Why a row can still reach the review step as a duplicate"

    Only the **cross-file, auto-resolved** twins are removed up front. A row whose duplicate
    lives in the *unsaved editor* (not in another imported file) is still shown on the review step as
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

`ParseDetailModal.svelte` (the `analyze` step) shows each file's parse outcome: total rows, plugin
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
- **[Asset Identity](asset-identity.md)** — the similarity engine, identifier election and merge.
- **[DataTable](../core-ui/data-table.md)** — the grid reused by the resolver.
