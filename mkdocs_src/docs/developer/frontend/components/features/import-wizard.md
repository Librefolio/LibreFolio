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
| 2 | `select` | ✅ | Pick which of the broker's stored files to parse and, per file, which BRIM plugin reads it. A [report set](#report-sets) is one card, above the table of the broker's other files. |
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
The user can read a set another way — with another report-set plugin, or some or all of its files
alone — and the wizard remembers how each file was read at the last analysis
([How a set is read](#set-read-as)). The backend half — roles, `/sets/preview`, `/sets/combine`
and the originals they leave out (`exclude_file_ids`), truth points, the history start (H0) and
`/gap-fix` — is in
[BRIM Plugin Guide → Multi-report plugins](../../../architecture/patterns/brim_plugin_guide.md#report-sets).

The decisions live in two pure modules, tested without the component
(`./dev.py test front-transaction tx-unit`); the wizard keeps the reactive state and the server
calls:

- `lib/utils/transactions/importReportSets.ts` — grouping, how a set is read (the choices the card
  offers, the memory of the last analysis, the set request), selection, analysis units, the card's
  timeline and the FilesTable badges;
- `lib/utils/transactions/gapFixModel.ts` — the gap-fix requests and the view of the `gapFix` step.

| Function (`importReportSets.ts`) | Contract |
|---|---|
| `setPluginFor(file, plugins, override?)` | The report-set plugin a file joins: the first plugin of its `compatible_plugins` (already in priority order) that declares roles, even when a generic plugin could read the file too. An override wins: a report-set plugin puts the file in that set, any other plugin makes it a single file, and `''` a single file with no plugin (removed from its set); `null` and `undefined` mean no choice. `null` for a combined file, for a file without `batch_id` and for a failed original (`status === 'failed'`), whatever the override: a failed original is never a member, as in `collect_members` on the server (rule A2) |
| `groupBrokerFiles(brokerId, files, plugins, overrides?)` | `{sets, singles}` of one broker: one `ReportSetGroup` per plugin and `batch_id` (key `set:<broker>:<plugin>:<batch>`), newest first; combined files are in neither list. `overrides` maps a file id to its choice, read by `setPluginFor` (the wizard passes `choicesFor(brokerId)`) |
| `setSelectionState(set, selectedIds)` | `all`, `some` or `none` |
| `buildParseUnits(selected, sets)` | The analysis units: the selected files of a set, read with the set's plugin, become **one** `set` unit; every other file is a `file` unit |
| `setBlocksAnalysis(set, selectedIds, state?)` | Whether a set holds the analysis back: `false` when none of its files is selected; `true` when only some are, whatever the preview says (rule R6, under Step `select` below); when all are, `true` until the preview is ready and says `complete: true` — while it is still loading, failed, or says `complete: false` |
| `combinedFileForSet(set, files)` | The newest combined file of the same broker, batch and plugin whose live originals — its `derived_from` refs not marked `deleted` — are exactly the set's members, or `null`. A combined file built before a member was left out, or before one was added, belongs to another membership; an original deleted after the combine keeps the set analysed (v5.3) |
| `buildSetTimeline(preview, roleOrder)` | The card's timeline, `null` when no member has a coverage. `rows`: one per role that has bars, in `roleOrder`, with a bar per coverage entry, ordered by start then end and carrying the file's `rows` (`null` when unknown), and the role's `gaps`: walking the bars by start and keeping the furthest end reached `e`, a bar starting after `e + 1` opens a gap from `e + 1` to the eve of its start — never before the first bar or after the last. `history`: from H0 to the later of H0 and `history_end` (an opening correction, dated the eve of H0, may be the history's last transaction), with `count` (`history_count`, else 0); `null` without H0. The span (`start`, `end`) includes the history's end; every bar, gap and history is placed in percentages of it |
| `rememberedChoices(files, plugins)` | The memory of the last analysis: file id → choice, for the originals an analysis spoke about ([below](#set-memory)) |
| `setPluginChoices(set, plugins)` | **Read as**: the report-set plugins that read every member (in each member's `compatible_plugins`), the set's own first |
| `readAlonePlugins(file, plugins, brokerDefault?)` | **Read alone with**: the file's single-file plugins — its `compatible_plugins` that declare no roles — in that order, the broker's default first when it is one of them; `[]` for a file only report-set plugins read |
| `otherSetPlugins(file, setPluginCode, plugins)` | The other report-set plugins that read the file (note C2) |
| `defaultPluginNote(set, brokerDefault, plugins)` | The broker's default plugin when it is not the set's plugin and reads at least one member (note C1), else `null` |
| `setRequest(set, files)` | The body of `/sets/preview` and `/sets/combine`: `{broker_id, plugin_code, batch_id, exclude_file_ids}`. `exclude_file_ids` are the originals of the same broker and batch that the set's plugin reads, that are not failed and not members — read alone, or removed from the set. The wizard sends it for the preview and the combine, `FilesTable` for the preview |
| `setsOfFiles(files, plugins)`, `fileSetBadges(file, ctx)` | The FilesTable badges ([below](#report-set-badges)); `setsOfFiles` groups with the memory, `rememberedChoices` |

The choices are `PluginChoice` objects, `{code, name}`: the name comes from the catalogue, else the
code.

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
files; when the broker has at least one set, that table is headed **Other files of this broker**
(`import-wizard-other-files-<brokerId>`, absent for a broker without sets). The sets uploaded in
this session are selected and open; older sets stay listed, unselected. Every set's preview runs in
the background.

**Which panels open, and the paging of the file tables.** `loadBrokerFiles()`, run when the wizard
enters `select`, decides which broker panels start expanded (`expandedBrokers`): after an upload in
this session, only the brokers that received one of the uploaded files; when the user went on
without uploading anything, every broker that has stored files. The other panels stay collapsed
behind their header (`import-wizard-broker-toggle-<brokerId>`, `toggleBrokerExpand`), which still
shows how many sets and files they hold. Each broker's table of single files pages at five rows
(`defaultPageSize={5}`, page sizes 5 / 10 / 25 / 50 / 100 / All); its pager appears only when the
broker has more than five single files (`enablePagination` and `alwaysShowPagination` are both
`singles.length > 5`), and the page size the user picks is remembered per broker through the
table's `storageKey` (`import-wizard-files-<brokerId>`).

- A set is selected or deselected **as a whole** (`toggleSetSelection`, which, when it selects a set
  whose preview was asked for other members, previews it again), and its members take the set's
  plugin (`pickBestPlugin` returns the choice in force first, then asks `setPluginFor`). Which
  plugin reads the set, and which files it holds, is the user's choice: see
  [How a set is read](#set-read-as).
- **The single files** are ticked one by one in the broker's `DataTable`: `handleSelectionChange`
  drops from `selectedFiles` the single files the table no longer ticks — a set's members are not
  in the table, and keep their selection — and adds a newly ticked file with `pickBestPlugin`. The
  **Plugin** column shows `—` for a file that is not selected. A selected file gets an
  `ImportPluginSelect` that holds its `pluginCode` (*Select plugin…*, `importWizard.selectPlugin`,
  while it is `''`) and offers its `compatible_plugins`, report-set plugins included (the whole
  catalogue when the list is empty); a choice goes through `updateFilePlugin`. **Parse** needs a
  plugin on every selected file (`step2CanParse`): until then it is disabled, with the
  `importWizard.pluginRequired` hint — or the `import-wizard-set-blocks` one, which comes first
  while a selected set blocks. The table reads the selection only when it mounts
  (`initialSelectedIds`, read in `untrack`), so it sits in a `{#key}` on its files' ids and
  remounts whenever a file joins or leaves it: a file arriving from a set keeps its tick, and a
  click on another row cannot drop it. Without the remount, such a file would be selected with its
  box clear, and the next click on another box would emit a selection without it. `DataTable`
  emits `onSelectionChange` only on user actions, never when it mounts, so the remount leaves the
  wizard's selection as it is.
- The card (`report-set-card`, with `data-set-key`, `data-batch-id`, `data-plugin-code`,
  `data-set-status` — `loading`, `complete`, `incomplete` or `error` — `data-selected` and
  `data-analysed`, true when `combinedFileForSet` finds a parsed combined file of exactly its
  members) has the **Read as** select in its header and, in its body, the reading notes (both in
  [How a set is read](#set-read-as)); then it shows, per role, its localised name
  (`importWizard.reportSet.roleName.<code>`, else the plugin's `description`), its extensions and
  `max_history`, then the role's files in a table (below); per missing role, the period and
  **Upload the missing file** (`report-set-upload-missing`), which uploads with the same broker and
  `batch_id`, re-reads the broker's files and the preview of the set as it now stands — the set
  before the upload would name the new file as left out — and selects the new file when the set
  was selected; the files no role recognises, apart (`report-set-unrecognised`, `data-file-id`);
  the timeline (below); the preview's warnings (`report-set-warning`, `data-code`); and the history
  note (`report-set-history`, `data-kind` `first` or `later`). Everything is plain Svelte text: file
  names and plugin notices are data.
- **The role tables**: each role with files gets a shared `DataTable` inside
  `report-set-role-table` (`data-role`), with body rows `tr[data-row-id=<file_id>]` and the columns
  **File**, **Period** (the earliest start → the latest end of the file's coverage entries) and
  **Rows**. The rows are ordered by that start, then by filename in natural order; files without
  coverage come last. The row menu (⋮ `row-actions-<file_id>`) holds `context-menu-action-preview`,
  the reading actions `context-menu-action-read-alone-<code>` and
  `context-menu-action-remove-from-set` ([How a set is read](#set-read-as)), and
  `context-menu-action-delete`; a double click previews the file. Sorting, filters,
  pagination and row selection are off: the set is chosen whole with `report-set-select`, and its
  files keep their period order.
- **The timeline** (`report-set-timeline`, built by `buildSetTimeline`): one row per role, where
  each coverage entry is a bar `report-set-timeline-bar` (`data-role`, `data-file-id`,
  `data-start`, `data-end`, `data-rows` — empty when unknown) and the days no file of the role
  covers between two of its files are a dashed gap `report-set-timeline-gap` (`data-role`,
  `data-start`, `data-end`); the last row, labelled *LibreFolio* and present only with an H0, is
  the history LibreFolio already holds, `report-set-timeline-history` (`data-start` = H0,
  `data-end` = the history's last day, `data-count`). Each bar, gap and history sits in a
  `Tooltip` — after 200 ms of hover, or at once on a click — with its period and, for a file, its
  role, name and rows (when known); for a gap, that no export of the role covers those days; for
  the history, how many transactions LibreFolio holds. The legend `report-set-timeline-legend` has
  a `report-set-timeline-legend-item` per kind: `data-kind="file"` always, `history` and `gap`
  only when the timeline has some.
- **The timeline's grid**: three columns — role label | bars | period — shared by every row, so
  the bars of all rows start and end at the same point. The label column is `fit-content(40%)`:
  as wide as the longest role name, it wraps only past 40% of the timeline's width, so a long name
  such as *Securities transactions* is shown whole on desktop. Each label is a
  `report-set-timeline-label` with `data-role`: the role code, `history` for the LibreFolio row.
  The bars take `minmax(0,1fr)`, and the period column (`max-content`) holds each row's overall
  span — first start → furthest end — or the history's. The date header (the span's first and
  last day) sits in the bar column, and the legend starts there too, spanning the period column.
- While a selected set blocks (`blockingSets`: the sets for which `setBlocksAnalysis` is true),
  **Parse** (`import-wizard-parse`) is disabled (`step2CanParse`) and the
  `import-wizard-set-blocks` hint gives the reason in `data-reason`: `partly-selected`
  (`importWizard.reportSet.partlySelectedBlocks`) while at least one set is selected only in part
  (`partlySelectedSets`) — that reason comes first — else `incomplete`
  (`importWizard.reportSet.incompleteBlocks`): a wholly selected set whose preview is not ready
  and complete (still loading, failed, or `complete: false`). The card has no command of its own
  to leave a set out: the user deselects it with its checkbox, `report-set-select` — what the
  `incomplete` hint asks for, beside uploading the missing file — and the other files go on.
- **A set selected only in part blocks** (rule R6): `setBlocksAnalysis` is true for `some`,
  whatever the preview says. `buildParseUnits` would put only the selected members in the set's
  unit, but `setRequest` leaves out only the files that are not members, so the preview and the
  combine would read the whole set, its deselected members included. The set's checkbox resolves
  it: `toggleSetSelection` deselects every member from `all` or `some` and selects them all from
  `none`, so from `some`, where the box shows a dash, one click deselects the set and a second
  one selects it whole. The card's `selectionState` action writes both `checked` and
  `indeterminate` on every change of `selection`. A plain `checked={selection === 'all'}` would
  not do: from `some` to `none` its value stays `false`, Svelte does not write it again, and the
  tick the browser draws on the click would outlive the wizard's answer. Nothing selects the set
  for the user: no command ticks or unticks a file ([How a set is read](#set-read-as)). In the
  wizard a set ends up selected in part when a selected file goes back into a deselected set —
  for example `removeFileFromSet` on a member (the file keeps its tick), the set deselected with
  `report-set-select`, then the set's plugin chosen again in that file's `ImportPluginSelect`:
  the card then reads `data-selected="some"`.
- **Parse (n)** counts analysis units: a set counts once.

### 🔀 How a set is read {: #set-read-as }

Detection decides first: a file joins the set of the first report-set plugin that recognises it
(`setPluginFor` without override). The user can change that from the card. The card only asks: the
wizard owns the choices.

**The card.** `ReportSetCard` takes five more props: `plugins` (the catalogue),
`brokerDefaultPlugin` (the broker's `default_import_plugin`, or `null`), `onReadAs(code | null)`,
`onReadAlone(fileId, code)` and `onRemoveFromSet(fileId)`.

- **Read as** is LibreFolio's own select — a `compact` `SimpleSelect`, not the browser's native
  `<select>` — in the header, so a folded card shows it too: `report-set-read-as` wraps it, its
  trigger is `report-set-read-as-button` and its list `report-set-read-as-dropdown`. Its value is
  the set's plugin; its options are `setPluginChoices(set, plugins)`, each
  `report-set-read-as-option-<plugin_code>` — the one detection picks for the set's first member
  labelled *(detected)* — then *Read the files one by one*,
  `report-set-read-as-option-one-by-one`, whose value is the sentinel `__one_by_one__`
  (`ONE_BY_ONE`), a value no plugin code can take: to the select, `''` — its default value — means
  «nothing chosen». A choice calls `onReadAs(code)`, or `onReadAs(null)` for the sentinel.
- **The row menu** of the role tables adds, after Preview, one action `read-alone-<code>` per
  plugin that `readAlonePlugins` gives for at least one member (testid
  `context-menu-action-read-alone-<code>`, label *Read alone with ‹plugin›*), visible only on the
  rows of the files that plugin reads, which calls `onReadAlone(fileId, code)`; then
  `remove-from-set` (`context-menu-action-remove-from-set`, *Remove from the set*), which calls
  `onRemoveFromSet(fileId)`; then Delete.
- **The notes**, in the body of an open card, as plain text: `report-set-default-note`
  (`data-default-plugin`) when `defaultPluginNote()` is not `null` — the set is read as the set,
  not with the broker's default plugin, and *Read as* or a file's ⋮ menu changes that (C1); one
  `report-set-also-recognised` per member for which `otherSetPlugins` finds plugins
  (`data-file-id`, `data-plugins`: their codes, comma-separated), naming them (C2).

The labels are
`importWizard.reportSet.{readAs, readAsOneByOne, detected, readAloneWith, removeFromSet, defaultPluginNote, alsoRecognisedBy}`.

**The wizard.** This session's choices live in `filePluginOverrides` (file id → choice), which
`resetState()` clears when the wizard closes:

- `readSetAs(set, code)` changes how the members are read, never whether they are selected: it
  records a choice for every member, and `selectedFiles` keeps the same files, each selected member
  with its new plugin. With a report-set plugin, every member's choice is that plugin, so the set
  moves to that plugin's key. With `null`, each member's choice is its first `readAlonePlugins`
  entry — the broker's default when it reads the file — or `''` when it has none: the members
  leave the set as single files, ticked or not as they were. A selected member with `''` has no
  plugin — its `ImportPluginSelect` shows *Select plugin…* and still offers its
  `compatible_plugins`, the set's plugin included — and **Parse** waits until it has one
  (`step2CanParse`).
- `readFileAlone(fileId, code)`: the file gets `code`, and only its plugin changes — selected, it
  stays selected with `code`; unselected, it stays unselected, and `pickBestPlugin` gives it `code`
  when it is ticked.
- `removeFileFromSet(fileId)`: the file gets `''` — out of its set, with no plugin, waiting for a
  new choice — and again only its plugin changes: selected, it stays selected with
  `pluginCode: ''`, like a member that `readSetAs(set, null)` leaves with no plugin
  (*Select plugin…*, its `compatible_plugins` offered, the set's plugin included; **Parse** waits);
  unselected, it stays unselected, and `pickBestPlugin` gives it `''` when it is ticked. No
  single-file plugin is picked for it, even one that reads the file: taking a file out of a set
  says «not with this plugin», not «not at all», and the next plugin is the user's choice.
- None of these commands changes the selection: `readSetAs`, `readFileAlone` and
  `removeFileFromSet`, like a plugin choice (`updateFilePlugin`), map `selectedFiles`, changing the
  `pluginCode` of the files they target, and never add or drop a file. The same rule holds for
  every report-set plugin
  ([BRIM Plugin Guide → The set and its API](../../../architecture/patterns/brim_plugin_guide.md#the-set-and-its-api)).
- **Back into the set**: a file out of its set is a single file, in the broker's table (headed
  **Other files of this broker** while the broker has a set), selected or not as it was. Selected,
  it has its `ImportPluginSelect`; unselected — a file of a set that was not selected, say — its
  plugin column shows `—` until the user ticks it. Choosing the set's plugin in the select goes
  through `updateFilePlugin`, and the file is a member again. After `readSetAs(set, null)` the set
  is re-formed this way, file by file: the first member given the set's plugin brings back the set
  — same broker, plugin and batch, so the same key — and its card, holding that file only and
  incomplete while a role it needs is out; each next member joins it.

`choicesFor(brokerId)` lays this session's choices over the memory of the last analysis
(`rememberedByBroker`: `rememberedChoices` per broker, [below](#set-memory)). The grouping
(`brokerSetGroups`, through `groupBrokerFiles`) and `pickBestPlugin` read it: before any detection,
`pickBestPlugin` gives a chosen set's plugin, a chosen single-file plugin, or `''`.

**The previews follow the members.** A preview entry (`SetPreviewEntry`) keeps, beside the set's
key, the members it was asked for (`memberSignature`: the sorted file ids), and `previewSet` sends
`setRequest(set, brokerFiles)`, so the server reads the same membership. After each choice, and
after a member is deleted, `refreshChangedSetPreviews()` re-reads the previews whose members no
longer match; selecting a set with `toggleSetSelection` does the same for that set. A file the set
needs, once taken out, makes the set incomplete, and it blocks **Parse** like any incomplete set.
`initParseResults()` keeps each set unit's `excludeFileIds` (`ParsedSetInfo`), which the combine
sends ([Step `analyze`](#set-analysis)).

### 💾 The memory of the last analysis {: #set-memory }

No field records how a file was read: `rememberedChoices(files, plugins)` reads it back from what
the server already saves at analysis, and nothing is remembered while files are only uploaded. For
each original with a `batch_id`, three kinds of events count. The combined files that count are
those of the same broker and batch with `status === 'parsed'`, a report-set `parsed_plugin_code`
and a readable `processed_at`.

| Event | When | Choice | At |
|---|---|---|---|
| E1, member | a counted combined file lists the file among its live `derived_from` refs (not `deleted`) | its `parsed_plugin_code` | the combined file's `processed_at` |
| E2, alone | the file itself has `status === 'parsed'` and a single-file `parsed_plugin_code` | that plugin | the file's `processed_at` |
| E3, left out | a counted combined file does not list it, although its plugin is in the file's `compatible_plugins` and the file's `uploaded_at` is not later than the combined file's: the file was there when the combined file was built | `''` | the combined file's `processed_at` |

The newest E1 wins when it is newer than every E2 and E3. Otherwise an E2 at least as new as the
newest E1 gives its plugin: a lone parse and a set analysis that left the file out agree, both put
it out of the set. Otherwise an E3 gives `''`. With no event the file has no entry, and detection
decides.

A reopened wizard therefore shows a set with the files it was analysed with and its plugin, a file
analysed alone with its plugin, and a file left out of an analysed set as a single file with no
plugin. The user changes that with the same commands, and the next analysis becomes the new memory.
`setsOfFiles` applies the memory too, so the FilesTable badges follow it
([below](#report-set-badges)).

### 🧠 Step `analyze`: combine, then parse {: #set-analysis }

`initParseResults()` turns each unit into one row. A set's row (`ParsedFileResult.set`) is
labelled *Set of ‹date› · combined (N files)*, with the member names below it (`parse-row-set`).
`parseResultInPlace()` first calls `POST /sets/combine` with the unit's `excludeFileIds` — the
backend reuses a combined file of exactly these members — then parses the combined file with the
set's plugin: the row's `fileId` starts as the set key and becomes the combined file's id. A
combine or parse error lands on that row only; the other rows go on.

`ParseDetailModal` adds, for a set, the **Matching securities ↔ cash** section
(`parse-detail-pairing`, whose `data-pair` … `data-excluded` attributes keep the counts of
`summary.outcomes`): the member names; the five outcomes as chips `parse-detail-pairing-outcome`
(`data-outcome`, `data-count`), always in the order `pair`, `standalone`, `summarized`, `deferred`,
`excluded`, those at zero dimmed; when `summary.reasons` has entries, the table
`parse-detail-pairing-reasons` (Reason, Rows), one row `parse-detail-pairing-reason` (`data-reason`,
`data-count`) per reason, labelled through `importWizard.reportSet.reason.<code>`; and two commands.
**Preview the combined file** (`parse-detail-preview-combined`) is a button, present only when the
modal gets `onPreview`: the wizard passes one that opens the file preview on the row's `fileId`,
which for a set is the combined file. **Download the combined file**
(`parse-detail-download-combined`) is a link to `/api/v1/brokers/import/files/{file_id}/download`.

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

**`GapFixStep.svelte`** is controlled: the wizard owns `gapFixSelected`, and the step only asks.
Its props are `view`, `selected`, `onToggle(key)` (flip one correction),
`onSetSelected(keys, selected)` (keep or drop several in one update: the wizard passes
`setGapFixProposals`, which assigns `gapFixSelected` once), `assetName` and `brokerName`. The root
`import-wizard-gapfix` carries `data-proposal-count` and `data-selected-count`, and ends with
`gapfix-info-hidden-titles` (a security that never moved cannot be seen). Each group
(`gapfix-group`, `data-broker-id`, `data-plugin-code`) is headed by its broker's name; a failed
request shows `gapfix-error` and nothing else, otherwise the group shows, top to bottom:

- **The summary cards**: one button `gapfix-summary` per truth point (`data-key`, `data-kind`
  `opening` | `gap` | `verification`, `data-as-of`, `aria-pressed`), in date order — on a shared
  date the checkpoint first — under a hint on what a click does. A checkpoint card (also
  `data-proposals`, `data-positions` — the positions with a non-zero difference — and `data-notes`)
  shows its title (*Starting point · date* or *After the gap · date*), its non-zero cash
  differences through `CurrencyAmount` (masked by the privacy mode), and how many positions (when
  any), corrections and notes (when any). A verification card (also `data-ok`) shows its title
  (*End-of-period check · date*) and reads *Matches*, or *Does not match* with its non-zero
  differences.
- **The active point**: a click makes a card the group's active point (one per group, none when
  the step opens), and a second click clears it. The active point opens `gapfix-point-details`
  (`data-key`) with its full comparison, in the C3 markup. A checkpoint renders `gapfix-checkpoint`
  (`data-as-of`, `data-kind`): the LibreFolio / Bank / Difference table — `gapfix-cash-row`
  (`data-currency`, `data-difference`) through `CurrencyAmount`, `gapfix-position-row`
  (`data-asset-id`, `data-exactness`) with quantities through `maskableQuantity`, *at least* for
  `at_least` — then the explanation (`gapfix-explanation`) and its notes (`gapfix-note`,
  `data-code`, localised by code). A verification renders `gapfix-verification` (`data-as-of`,
  `data-ok`) and, when it does not hold, its `gapfix-verification-cash-row`s. An active checkpoint
  narrows the table to its own corrections (none: *This point needs no correction*). An active
  verification opens its comparison and leaves the table whole: a verification corrects nothing,
  and an empty table would look like lost corrections.
- **The table**: `gapfix-table`, one per group and only when the group proposes corrections — a
  shared `DataTable`, sortable by point, date, type and asset, 10 rows a page by default — with
  rows `tr[data-row-id=<proposal key>]`, the unselected ones dimmed. Columns: the selection;
  **Point** (*Starting point* or *After the gap*); **Date**; **Type**, with its icon through the
  DataTable's `image` cell (no new HTML); **Asset**; **Quantity**, visible because a correction is
  a transaction (the holdings in the comparison stay masked); **Cash** through `CurrencyAmount`;
  **Tags**, `gap_fix`, or *cost to enter* when the correction needs a cost. The selection switch is
  `GapFixToggle.svelte`, a `custom` cell: the button `gapfix-proposal-toggle` (`aria-pressed`,
  `data-key`, `data-type`, `data-date`, `data-point` — its checkpoint's key) calls `onToggle`. The
  shared `editable-checkbox` cell draws the same switch, but without a testid or the row's facts,
  and the shared DataTable stays untouched.
- **The commands**, the review's, above the table next to the group's selected count:
  `gapfix-select-all` and `gapfix-deselect-all` act on every correction of the group, whatever the
  active point; `gapfix-select-visible` selects the rows on the table's current page
  (`getPageRowIds()`) — with a checkpoint active, only that point's — and leaves the others as they
  are. The C3 list `gapfix-proposal` no longer exists.

Everything is plain Svelte text, no `{@html}`: asset names, notes and errors are data.

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
  broker with that broker's `rememberedChoices` as overrides (a file without a broker belongs to
  none): a file left out of an analysed set, or analysed alone, gets no `set` badge;
- `fileSetBadges(file, {sets, files, previews})` returns, in a fixed order, `combined` (with the
  names in `derived_from` and the deleted ones), `stale` (`combine_is_stale`), `usedInCombined`
  (a non-empty `combined_into`), `set` (with the set's date) and `incomplete` (with the missing
  roles). `incomplete` needs the set's preview ready and saying `complete: false`: it never shows
  while the preview loads, after it failed, or when the set has an up-to-date combined file
  (`combinedFileForSet`: of exactly its members).

The plugin catalogue is read once (the cache shared with `ImportPluginSelect`), and each set's
preview is requested once per list of members, with `setRequest`, so the server leaves out the same
originals as the memory; a failed request only leaves the `incomplete` badge out.

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
  step); pressing it calls `onboardingGuide.finish()`. In automatic pending mode, `finish()`
  completes that step on the server: `import_guide` is step-managed, so every `import.*` step is
  recorded on its own through `completeStep` — here
  `POST /api/v1/settings/onboarding/import_guide/steps/import.bulk/complete`; the earlier steps are
  completed the same way when the user activates the control their coachmark points at
  (`handleTargetActivate` in `OnboardingOverlayHost.svelte`). In replay
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
