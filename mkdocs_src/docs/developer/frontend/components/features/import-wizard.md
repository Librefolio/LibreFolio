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

The stepper is a **conditional state machine**, not an index. `StepId` is a union of eight ids
and `STEP_DEFS` holds their canonical order; four of them are skipped when they have nothing to
do, so `currentStepId` is never a number and there is nothing to renumber when a step is added.

| # | `StepId` | Always shown | Purpose |
|---|---|---|---|
| 1 | `upload` | ✅ | Pick the broker, drop one or more files. |
| 2 | `select` | ✅ | Pick which of the broker's stored files to parse and, per file, which BRIM plugin reads it. A [report set](#report-sets) is one row, with its card. |
| 3 | `analyze` | ✅ | Parse each file (backend), show per-file stats via `ParseDetailModal`. A report set is combined first, then its combined file is parsed. |
| — | `assets` | ⚪ conditional | **Unify assets** — decide how many distinct instruments the files actually describe (`AssetGroupStep`). |
| — | `fix` | ⚪ conditional | **Corrections** — retype rows the plugin flagged as incomplete (`FixFlaggedStep`). |
| — | `duplicates` | ⚪ conditional | **Batch Duplicate Resolver** — arbitrate cross-file twins. |
| 4 | `review` | ✅ | Final grid, asset resolution against the DB, then hand off to `TransactionBulkModal`. |
| — | `gapFix` | ⚪ conditional | **Align with the bank** — report sets only: the bank's truth points against what LibreFolio will hold, and the `gap_fix` corrections that close the difference (`GapFixStep`). |

### 🎚️ What makes a step appear

`stepIsActive(id)` is the single source of truth. `enterNextActiveStep()` walks forward and lands
on the first step that returns `true`, so auto-skip is a property of the predicate, not a special
case in the navigation:

```ts
if (id === 'assets')     return assetGroups.some((g) => g.members.length > 1 || g.state === 'proposed');
if (id === 'fix')        return fixStepRows.length > 0;
if (id === 'duplicates') return duplicateGroups.length > 0;
if (id === 'gapFix')     return gapFixView !== null;
return true;
```

`gapFix` is the exception to the walk: `enterNextActiveStep()` never reaches it, because `review`
is always active and comes first. Only `handleImport()` — the review's **Import N transactions** —
enters it, and only when the gap-fix has something to show
([Step `gapFix`](#gapfix-step)).

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

The conditional steps each have their own component, all under
`lib/components/transactions/import/`. The two components that report sets add there —
`ReportSetCard` (in `select`) and `GapFixStep` — are described in [Report sets](#report-sets).

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

## 🧺 Report sets {: #report-sets }

A **report-set plugin** (non-empty `report_roles`; Danske Bank today) imports several exports of
one bank as one: the files uploaded together for a broker and recognised by the plugin form a
**set**, the backend combines them into one **combined file**, and the wizard parses that file.
The backend half — roles, `/sets/preview`, `/sets/combine`, truth points, the history start (H0)
and `/gap-fix` — is in
[BRIM Plugin Guide → Multi-report plugins](../../../architecture/patterns/brim_plugin_guide.md#report-sets).

The decisions live in two pure modules, tested without the component
(`./dev.py test front-transaction tx-unit`); the wizard keeps the reactive state and the server
calls:

- `lib/utils/transactions/importReportSets.ts` — grouping, selection, analysis units, the card's
  timeline and the FilesTable badges;
- `lib/utils/transactions/gapFixModel.ts` — the gap-fix requests and the view of the `gapFix` step.

| Function (`importReportSets.ts`) | Contract |
|---|---|
| `setPluginFor(file, plugins, override?)` | The report-set plugin a file joins: the first plugin of its `compatible_plugins` (already in priority order) that declares roles, even when a generic plugin could read the file too; a manual override wins. `null` for a combined file and for a file without `batch_id` |
| `groupBrokerFiles(brokerId, files, plugins, overrides?)` | `{sets, singles}` of one broker: one `ReportSetGroup` per plugin and `batch_id` (key `set:<broker>:<plugin>:<batch>`), newest first; combined files are in neither list |
| `setSelectionState(set, selectedIds)` | `all`, `some` or `none` |
| `buildParseUnits(selected, sets)` | The analysis units: the selected files of a set, read with the set's plugin, become **one** `set` unit; every other file is a `file` unit |
| `setBlocksAnalysis(set, selectedIds, state?)` | `true` when a selected set's preview is still loading, failed, or says `complete: false` |
| `combinedFileForSet(set, files)` | The newest combined file of the same broker, batch and plugin, or `null` |
| `buildSetTimeline(preview, roleOrder)` | The card's timeline: one row per role with a bar per file, plus the bar of LibreFolio's history from H0 |
| `setsOfFiles(files, plugins)`, `fileSetBadges(file, ctx)` | The FilesTable badges ([below](#report-set-badges)) |

### ⬆️ Step `upload`: the missing export

The wizard uploads its files only on **Next** (`goNext` → `uploadAllPendingFiles`), so a file's
role is unknown before that. One `batch_id` per wizard session (`uploadBatchId`, regenerated in
`resetState`) lets a file dropped later in the session join the same set. It comes from
`generateUUID()` rather than `crypto.randomUUID()`, which only exists in a secure context — and a
self-hosted LibreFolio may be served over plain HTTP.

After the upload, `collectStep1SetWarnings()` groups the session's uploaded files with
`groupBrokerFiles`, runs `POST /sets/preview` for each set and, when a set is incomplete, the
wizard **stays on `upload`** with one `import-wizard-step1-set-warning` per missing role
(`data-plugin-code`, `data-role`): plugin, role, extensions, the period from `missing`, and the
plugin's `docs_url`. A file dropped now joins the same set; a second **Next** without new files
goes on to `select`, where the set shows as incomplete.

### 🗂️ Step `select`: `ReportSetCard.svelte`

Each broker panel shows one `ReportSetCard` per set above its table, which keeps only the single
files. The sets uploaded in this session are selected and open; older sets stay listed,
unselected. Every set's preview runs in the background.

- A set is selected or deselected **as a whole** (`toggleSetSelection`), and its members take the
  set's plugin (`pickBestPlugin` asks `setPluginFor` first). The card offers no per-member plugin
  choice: the backend's preview and combine collect every file of the batch that the plugin can
  read anyway.
- The card (`report-set-card`, with `data-set-key`, `data-batch-id`, `data-plugin-code`,
  `data-set-status` — `loading`, `complete`, `incomplete` or `error` — `data-selected` and
  `data-analysed`) shows, per role, its localised name (`importWizard.reportSet.roleName.<code>`,
  else the plugin's `description`), its extensions and `max_history`; per file, the coverage, the
  rows, a preview and a delete button; per missing role, the period and **Upload the missing
  file** (`report-set-upload-missing`), which uploads with the same broker and `batch_id`, re-reads
  the broker's files and the set's preview, and selects the new file when the set was selected;
  the preview's warnings (`report-set-warning`, `data-code`); the history note
  (`report-set-history`, `data-kind` `first` or `later`); and the timeline. Everything is plain
  Svelte text: file names and plugin notices are data.
- While a selected set blocks (`setBlocksAnalysis`), **Parse** is disabled with the
  `import-wizard-set-blocks` hint, and the card offers **Exclude from the import**
  (`report-set-exclude`), which deselects the set so that the other files can go on.
- **Parse (n)** counts analysis units: a set counts once.

### 🧠 Step `analyze`: combine, then parse {: #set-analysis }

`initParseResults()` turns each unit into one row. A set's row (`ParsedFileResult.set`) is
labelled *Set of ‹date› · combined (N files)*, with the member names below it (`parse-row-set`).
`parseResultInPlace()` first calls `POST /sets/combine` — the backend reuses an identical combined
file — then parses the combined file with the set's plugin: the row's `fileId` starts as the set
key and becomes the combined file's id. A combine or parse error lands on that row only; the other
rows go on.

`ParseDetailModal` adds, for a set, the **Matching securities ↔ cash** section
(`parse-detail-pairing`): the counters of `summary.outcomes` (`pair`, `standalone`, `summarized`,
`deferred`, `excluded`) and `summary.reasons`, the member names, and a link that downloads the
combined file.

### 👀 Step `review`: rows before H0 {: #rows-before-history }

The parse of a combined file returns `history_start` (H0). `isBeforeHistory()`
(`importRowState.ts`) is true for a row dated **strictly** before it: a row dated H0 is inside the
history, and the duplicate check judges it. Earlier rows are already represented in LibreFolio:

- `buildMergedTransactions` creates them deselected, an `$effect` keeps them so, and
  `shouldAutoSelectOnRecheck` never selects them again;
- they stay out of the Corrections step and of the cross-file duplicate groups — with two sets of
  one broker imported together, the hidden rows of one set repeat rows of the other;
- the review hides them behind `import-wizard-before-history-count` (`data-count`) and its toggle
  `import-wizard-before-history-toggle`. Shown, they are dimmed, with the *Already in LibreFolio*
  badge and a disabled checkbox; they never count in the totals nor reach `buildFinalTxList()`.

### 🏦 Step `gapFix`: align with the bank {: #gapfix-step }

**When.** `handleImport()` runs its usual checks first (asset candidates, the final duplicate
recheck, the selection guard). Then `truthSourcesOf(parseResults)` collects the parse results that
carry checkpoints or verifications. With none, the rows go to the editor as before, and
`POST /gap-fix` is **never** called. Otherwise `computeGapFixView()` sends one request per broker
and plugin, one after the other, and stops if meanwhile the wizard closed or its data or session
changed. When `gapFixHasSomethingToShow(view)` — a proposal, a verification with `ok: false`, or a
failed request; notes alone, such as `unresolved_asset`, do not count — the wizard opens `gapFix`
with every proposal selected (`defaultGapFixSelection`). Otherwise it hands off directly.

**The requests** (`buildGapFixRequests`): one per broker and plugin, in the order of their first
source. Two sources of one broker and plugin — two sets imported together — make one request with
the union of their truth points. `selection` is `buildFinalTxList()` and `pending_creates` the
editor's unsaved rows, both filtered on the request's broker; `pending_delete_tx_ids` goes whole to
every request.

**The assets of the truth positions** (`resolveTruthAssetId`): a real id stays as it is. A plugin
fake id goes to the global fake id of its file (`MergeResult.fakeRemapByFile`, which the wizard
keeps after every merge), then to the survivor of the asset unification
(`representativeMap(assetGroups)`), then to the `resolvedAssetId` of the user's resolution when
there is one; otherwise the survivor stays, still fake. A plugin fake id that **none of its file's
rows used** is missing from the remap and comes back unchanged: plugin and global fake ids share
one range, so looking it up among the globals could bind the position to another instrument. It
stays fake, and the backend leaves it out with an `unresolved_asset` note.

**The view** (`buildGapFixView`): one group per request (key `<broker>:<plugin>`), with its
checkpoints (`<group>:cp:<i>`) and their proposals (`<checkpoint>:p:<j>`), then its verifications
(`<group>:v:<i>`). Each todo of the answer becomes an `ImportTodo` of its proposal (`tx_index`
counts within the checkpoint), its message localised through
`importWizard.reportSet.gapFix.todo.<reason_code>` because the backend writes it in English;
`needsCost` marks a proposal with a blocker on `cost_basis_override`. A failed request is a group
with its `error` and no rows.

**`GapFixStep.svelte`** is controlled: the wizard owns `gapFixSelected` and flips keys in
`onToggle`. Per group (`gapfix-group`) and per checkpoint (`gapfix-checkpoint`, *Starting point*
for `opening`, *After the gap* for `gap`) it shows the LibreFolio / Bank / Difference table (cash
through `CurrencyAmount`, position quantities through `maskableQuantity`, *at least* for
`at_least`), the explanation (`gapfix-explanation`, notes localised by code) and the proposals
(`gapfix-proposal`, toggled by `gapfix-proposal-toggle`) with type, date, asset, quantity, cash,
*cost to enter* and the `gap_fix` tag. The verifications (`gapfix-verification`, `data-ok`) read
*Matches* or *Does not match*; a failed group shows `gapfix-error`. Plain Svelte text, no
`{@html}`.

**The footer**: **Back** (`import-wizard-back`), the count `import-wizard-gapfix-count`
(`data-count`) and **Continue** (`import-wizard-gapfix-continue`, guide anchor
`import.action.gapFix`). **Continue** (`handleGapFixContinue()`) hands the editor the review's
rows plus the selected corrections with their todos,
`[...buildFinalTxList(), ...selectedGapFixCreates(view, selected)]`. A failed group does not block
it: the user goes on without that group's corrections, and the other groups' corrections still go.

**Recomputing**: the view and its selection are dropped on **Back**, on `goToStep()` to an earlier
step, in `resetDownstreamState()` and `resetState()`, and on every `mergeAllTransactions()`. The
next **Import N transactions** computes them again on the current selection.

### 🏷️ Badges in `FilesTable` {: #report-set-badges }

`FilesTable.svelte` serves both the Files page and a broker's **Uploaded Reports** modal
(`BrokerImportFilesModal.svelte`). For `type === 'brim'` it adds the **Report set** column
(`reportSet`), rendered by `FileSetBadges.svelte` (`file-set-badge`, `data-kind`). The logic is
pure:

- `setsOfFiles(files, plugins)` maps each member to its set, running `groupBrokerFiles` broker by
  broker (a file without a broker belongs to none);
- `fileSetBadges(file, {sets, files, previews})` returns, in a fixed order, `combined` (with the
  names in `derived_from` and the deleted ones), `stale` (`combine_is_stale`), `usedInCombined`
  (a non-empty `combined_into`), `set` (with the set's date) and `incomplete` (with the missing
  roles). `incomplete` needs the set's preview ready and saying `complete: false`: it never shows
  while the preview loads, after it failed, or when the set has an up-to-date combined file.

The plugin catalogue is read once (the cache shared with `ImportPluginSelect`), and each set's
preview is requested once per list of members; a failed request only leaves the `incomplete` badge
out.

---

## 🧬 Duplicate detection

Detection runs in **two independent layers**. Each merged row keeps the verdicts that come from
outside the batch in fields of their own — the database verdict in `dbDuplicateStatus`
(`likely` / `possible`), the bulk-editor verdict in `pendingMatchStatus` (`pending_duplicate` /
`pending_possible_duplicate`) — and still **displays one status**, `duplicateStatus`: the
database verdict (or `unique`) unless the in-batch pass or an editor match rewrote it.

`duplicateStatus` alone cannot tell whether a row collides with something *outside* the batch:
the in-batch pass rewrites it to `pending_duplicate` on the secondaries of a cross-file group.
That pass never touches the two kept fields, so the resolver reads those
(`hasFirmOutsideCollision`, below). Every recheck starts them afresh (`rowAfterRecheck`): the
database verdict is replaced, never carried over, because a correction can clear a false
duplicate and a stale `likely` would keep the row out of the keepers.

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
| `before_history` | report-set history start | `date < history_start` (H0) | ⛔ blocked and hidden behind a counter |

`before_opening` is **not** a duplicate status — it comes from the broker's opening-date gate
(`beforeOpeningIndices`) and is shown here only because it shares the review-step status filter.
Neither is `before_history`: it marks the rows of a report set that are already in LibreFolio
(`beforeHistoryIndices`, see [Step `review`: rows before H0](#rows-before-history)).
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
  component). In each description-partition the primary (`groupPartitions`) is the
  **highest-priority copy without a firm outside collision** — `hasFirmOutsideCollision`: a DB
  `likely` or an editor `pending_duplicate`; `possible` and `pending_possible_duplicate` do not
  count. `defaultKeeperIndices` keeps that primary; the rest are marked non-keepers and
  deselected. When every copy collides, the primary is the highest-priority copy **for display
  only** and the partition keeps none: a copy already in the database or in the unsaved editor
  is never the default keeper. An explicit manual choice is still respected.
- **Recalculate** — after re-ordering priority, the user can recompute the keepers, discarding
  any manual per-row choices and re-deriving them from the new priority order.
- **Member table** — each group renders its members in a **`DataTable`** (`resolverMemberColumns`)
  with a keep checkbox, keeper/duplicate badges, and the file/description columns, so the same
  formatting and icons as the main transactions page are reused.
- **Recheck carry-over** — a duplicate recheck (`refreshDuplicateReport`) does not reset the
  resolver. A group counts as *changed* when it has no same-member predecessor (new or
  reshaped), or when the user had arbitrated it and one of its copies started or stopped
  colliding firmly (`hasFirmOutsideCollision`). `carryResolverChoices` carries the choices of
  every arbitrated group that is not changed; every other group starts from its defaults — an
  untouched one even when a copy's status changed. Groups are matched by **member set, not by
  `key`**, because the key embeds the asset identity, which changes when an unresolved asset
  gets bound. The status clause exists because the backend narrows its database match to the
  bound asset only once the asset is resolved: re-binding a group on the review step can turn a
  unique copy into a database duplicate, which a choice carried from before would import.
- **Final recheck** — the recheck run by **Import N transactions** (`handleImport`) sends the
  user back to `duplicates` only when it finds changed groups, with a warning toast ("The final
  duplicate check found new or changed duplicates between your files. Review them before
  importing.") and the app event `tx.import.duplicates.changed` (detail: each changed group's
  key and member indices). Otherwise the import goes on: if the selection changed — e.g. a new
  DB verdict moved a default keeper — the existing `tx.import.selection.changed` guard keeps the
  user on `review` with a warning; if not, the rows go to the bulk editor — through
  [`gapFix`](#gapfix-step) first when a report set brought truth points and the gap-fix has
  something to show.

!!! tip "Why a row can still reach the review step as a duplicate"

    Only the **cross-file, auto-resolved** twins are removed up front: a group's secondaries,
    unless the user kept them (`isResolvedAwayDuplicate`). Two kinds of row still reach the
    review step flagged, so the user stays aware of them — both simply deselected by default:

    - the display primary of a partition whose every copy already exists, listed with its own
      database or editor badge, like any database twin;
    - a row whose duplicate lives in the *unsaved editor* (not in another imported file), shown
      as `pending_duplicate`.

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

On the review step, a row's status badge opens **the comparison it claims** (`compareTargetFor`,
dispatched by `openBadgeCompare`):

- a database badge (`likely` / `possible`) → the row against the stored transaction
  (`openDbCompare`), even when the row also belongs to a cross-file group;
- an editor match → the row against the unsaved editor row (`openPendingCompare`);
- an in-batch secondary → the whole group, *N*-way (`openLotCompare`);
- `unique` → none.

---

## 🧾 Per-file parse stats

`ParseDetailModal.svelte` (the `analyze` step) shows each file's parse outcome: total rows, plugin
warnings, and the per-file duplicate counts (`unique` / `possible` / `likely`) computed from
Layer 1. It is the fastest way to spot that a re-exported file overlaps an already-imported
one before merging. For a report set it also shows how the exports were matched
([Step `analyze`](#set-analysis)).

---

## 🧑‍🏫 Onboarding: the contextual import guide {: #import-guide-wiring }

The wizard is also one of the two places (with the intro tour) that drives
`onboardingGuide.svelte.ts` — the `import_guide` flow, one of the fifteen versioned flows in
`ONBOARDING_FLOW_VERSIONS` (`backend/app/services/onboarding_service.py`). Its nine step ids
(`IMPORT_GUIDE_STEP_IDS`, defined in `lib/features/onboarding/onboardingGuideCatalog.ts` and
re-exported by `onboardingGuide.svelte.ts`) are `import.upload` / `select` / `analyze` / `assets` /
`fix` / `duplicates` / `review` / `gapFix` / `bulk` — the first eight mirror `StepId` above 1:1,
plus a synthetic `bulk` step that has no counterpart in the wizard's own stepper.

**`import.gapFix`** sits between `import.review` and `import.bulk` in the backend
(`ONBOARDING_FLOW_STEPS`), in `IMPORT_GUIDE_STEP_IDS`, in the `OnboardingOverlayHost` table and in
the Settings replay section. Being `import.${StepId}` like the others, it follows the step by
itself: clicking **Import N transactions** (anchor `import.action.review`) finishes
`import.review`, and when the wizard opens `gapFix` its step-sync `$effect` starts
`import.gapFix`, anchored on the step's **Continue** (`import-wizard-gapfix-continue`, anchor
`import.action.gapFix`). The anchor is the only guide code the step added to the wizard. Like the
other conditional steps, it stays pending until an import shows the step. The flow stays at
**version 1**: the guides have never been released, and `test_settings_service.py` requires every
unreleased flow to stay there. Existing users get the step anyway, because
`ensure_onboarding_progress` creates every missing step row as `pending`.

**Wiring, not scripting.** The wizard never imports guide *content* — it only reports its own
state to the guide and renders anchors for it to point at:

- An `$effect` keyed on `open` and `currentStepId` calls `onboardingGuide.startImportAt(...)` the
  first time the modal opens, then `onboardingGuide.setStep(...)` on every subsequent step change
  — but only while `onboardingGuide.active?.flow === 'import_guide'` and a local `guideHandedOff`
  flag is `false`. Closing the modal while the guide is still attached calls
  `onboardingGuide.dismissHost({restartAtFirst: true})`, but `import_guide` is step-managed and
  `dismissHost` ignores `restartAtFirst` for such flows, so nothing is rewound: the next open's
  `startImportAt(...)` shows the guide at the wizard's current step only if that step is still
  due (automatic) or still among the replay's remaining steps (replay).
- Anchors are registered with the `guideAnchor` action against `createGuideAnchorRegistry()`
  (`lib/features/onboarding/guideAnchors.svelte.ts`), a plain `Map<string, HTMLElement>` keyed by
  string id and read back by `OnboardingOverlayHost.svelte`, which owns the single
  `OnboardingCoachmark` instance and the per-step copy/anchor table (`steps: Record<GuideStepId,
  StepPresentation>`). The wizard has no coachmark-specific markup of its own: each step's forward
  button, rendered only in that step's footer branch, carries a fixed id
  (`use:guideAnchor={'import.action.upload'}`, `'import.action.select'`, …), which the table maps
  to the matching `import.*` step. When a registered anchor counts as present is covered in
  [Anchor presence and stalls](#guide-anchor-stall).
- **Nested-modal suspension** is generic, not wizard-specific: `OnboardingOverlayHost` tracks
  `document.body.dataset.modalScrollLockCount` (bumped by every open modal, including
  `ParseDetailModal`, the N-way compare modal, and the asset editor) and derives `suspended =
  modalDepth > step.allowedModalDepth`. Every `import.*` step declares `allowedModalDepth: 2`
  except `import.bulk`, which declares `1`. The Import Wizard itself is depth 1, so the coachmark
  remains visible with one child dialog at depth 2 and hides if that child opens another dialog
  at depth 3. `TransactionBulkModal` is depth 1; any child dialog at depth 2 hides its coachmark.
- **The duplicate-recheck bounce** is the wizard driving its own `currentStepId` back to
  `'duplicates'` inside `handleImport()` when the final `refreshDuplicateReport(true)` returns
  changed groups (see `if (changedGroups.length > 0) { … currentStepId = 'duplicates'; return; }`,
  after the `tx.import.duplicates.changed` notification; *Batch Duplicate Resolver → Final
  recheck* above). The guide does not special-case this: it just observes the same
  `currentStepId` effect firing again with `'duplicates'` and follows.
- **The `bulk` handoff is one-way and explicit.** `handOffToEditor()` is the only way out to the
  editor: `handleImport()` calls it when there is nothing to align, `handleGapFixContinue()` from
  the `gapFix` step. It passes the rows to `onImportBatch(...)` and, while the import guide is
  attached, sets `guideHandedOff = true` — from that point the wizard's own step-sync effect is
  inert (`!guideHandedOff` guards it). `TransactionBulkModal`'s `onImportBatch` arms `import.bulk`,
  and the editor starts it (`onboardingGuide.startImportAt('import.bulk', …)`) once no nested modal
  is open and no guide step is active; only its **Save All** button
  (`use:guideAnchor={'import.bulk.save-all'}`) is highlighted. `OnboardingOverlayHost` swaps the
  coachmark's **Next** button for **Finish guide** only on this step (and on the tour's last
  step); pressing it calls `onboardingGuide.finish()`. In automatic pending mode, that is the
  *only* guide path that POSTs `/api/v1/settings/onboarding/import_guide/complete`. In replay
  mode, the same button only removes `import.bulk` from the stored replay (deleting the key once
  no step remains) and never calls the endpoint. The guide never calls `Save All` itself —
  finishing the guide and saving the batch are two independent user actions.

**The coachmark remains observational.** For `import.upload` through `import.gapFix`,
`OnboardingOverlayHost` does not render its own **Back** or **Next** controls (the one exception
is **Continue anyway** on a [stalled step](#guide-anchor-stall)); the user's actions in the real
wizard drive `currentStepId`, and the guide follows. It never clicks a wizard
control, uploads a file, or reconstructs an earlier wizard draft. Only after the user invokes
**Import N transactions** — or **Continue** on `gapFix` — does the explicit `import.bulk` handoff
highlight **Save All**.

The coachmark's top row holds only **X** (`showSkip={false}`), whose accessible label is *Skip
this tour* in automatic pending mode and *Exit tour* in replay mode. **X** calls
`onboardingGuide.exit()`, which is `skip()`: in automatic pending mode it skips the current step
on the server (`skipStep`); in replay mode, **X** and **Finish guide** only remove the current
step from the stored replay (deleting the key once no step remains), so neither calls a
complete/skip endpoint nor changes the backend onboarding status. Closing the wizard before
handoff is not an exit: `dismissHost({restartAtFirst: true})` rewinds nothing for this
step-managed flow, the active in-memory guide is cleared, and the stored position (an armed
replay included) is kept. No complete/skip endpoint is called, and there is no automatic
wizard-draft restoration.

!!! note "Browser-stored replay vs. server-terminal status"

    `onboarding.startReplay`/`updateReplayStep` (`lib/stores/app/onboarding.svelte.ts`) persist
    the in-progress step under a `localStorage` key scoped to the flow, its content version,
    and the current user id (`lf_{userId}_onboarding_replay_{flow}_v{version}`), so it survives a
    closed tab or a browser restart; a newer content version drops the older key on the next read
    or write. None of this touches the server's `pending` / `completed` / `skipped` status. Only an
    **automatic pending** guide calls the server, completing or skipping the current step
    (`completeStep`/`skipStep`); terminal replays are strictly non-destructive. Logging out or
    switching account keeps every stored key and resets only the in-memory state
    (`createOnboardingSessionResetter` for the controller,
    `registerClientSessionReset('onboardingGuide', ...)` for the guide), so the same account
    resumes from its own key after logging back in on this browser; a page
    refresh loses only the in-memory guide, and the next trigger resumes from the stored key. All
    tabs of the browser share the key: when another tab removes it (for example because the guide
    ended or was cancelled there), the `storage` listener registered at the bottom of
    `lib/features/onboarding/onboardingGuide.svelte.ts`
    (`createReplayStorageListener(onboarding, undefined, () => onboardingGuide.dismissHost())`)
    drops this tab's in-memory replay and closes its step, so the stale step cannot write the key
    back.

### ⏳ Anchor presence and stalls {: #guide-anchor-stall }

These rules apply to every coachmark step of every guide, not only to the import steps.
`OnboardingCoachmark.svelte` measures the anchor in `refreshPosition()` and, through
`isRendered()`, treats it as **absent** — exactly like an anchor that was never registered — when
it is not mounted, when its box is 0×0 (`display:none`, a box-less wrapper), or when
`checkVisibility({visibilityProperty: true})` is available and returns `false`
(`visibility:hidden`, which keeps its box). Opacity is deliberately not a criterion:
hover-revealed controls start transparent and are real targets.

An absent anchor keeps the step `waiting`: the panel is centred, without highlight or pointer, and
reads *Waiting for this area to become available…*. After `GUIDE_STALL_MS` (3,000 ms) the step
turns `stalled`: the panel reads *This part of the page didn't load in time. You can continue with
the guide.*, and `OnboardingOverlayHost` shows **Continue anyway** as the primary button — for
`import.upload` through `import.gapFix`, the only forward control their coachmark ever shows. In
a step-managed flow (`import_guide`, `transaction_bulk_guide`) it calls `onboardingGuide.skip()`:
an automatic guide persists the step as `skipped` (`skipStep`), never `completed`, because the
step was never actually shown (the Round 7 stall rule), and a replay only drops the step from the
stored replay. Every other flow keeps its usual **Next**/**Finish** behaviour under the new label.
The countdown does not run while the panel shows a controller error or a nested modal suspends
the step. Once the anchor is rendered, the step anchors normally, the stall clears (`onstallend`)
and **Continue anyway** is withdrawn; an anchored target that later collapses to 0×0 (its
`ResizeObserver` fires) sends the step back to `waiting`, from where it can stall again.

**Page-author rule.** Bind `use:guideAnchor` only to the element that is actually visible for that
step. When a view hides a region — a tab, a collapsed panel — unmount it or leave the anchor off;
never hide a registered anchor. The registry keeps a single element per id, the last one
registered, so a hidden duplicate can shadow the visible one and stall the step. The broker-detail
guide shows the pattern: its tab steps anchor the `TabBar` buttons (the `guideAnchor` of each
`TabItem`), never the panels, which are `{#if activeTab === …}` branches. The guide observes the
page: it may scroll a target into view, and the intro tour requests its own route and sidebar, but
it never switches a tab or clicks a control for the user.

---

## 🔗 Related

- **[Transaction Form](transaction-form.md)** — the single-item editor the wizard feeds.
- **[Transaction Staging State](../../state/transaction-draft.md)** — how staged rows become
  `PendingOp`s in the editor.
- **[BRIM Plugin Guide](../../../architecture/patterns/brim_plugin_guide.md)** — the backend
  side that parses each file and reports DB duplicates.
- **[Asset Identity](asset-identity.md)** — the similarity engine, identifier election and merge.
- **[DataTable](../core-ui/data-table.md)** — the grid reused by the resolver.
