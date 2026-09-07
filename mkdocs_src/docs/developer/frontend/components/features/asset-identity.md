# 🧬 Asset Identity — unification, identifiers, merge

One security can reach LibreFolio under several names and several codes: two layouts of the same
broker report, a bond subscribed under one ISIN and traded under another, an import that ran
before the asset existed. This page documents the machinery that decides **how many distinct
instruments there really are**, **which code leads**, and **how to repair the duplicates that got
in anyway**.

!!! abstract "The invariant everything else serves"

    `identifier_isin` holds **only the quoted code** — the one a price provider can index.
    Everything else lives in `identifier_other`, where it does not quote but does **recognise**.
    A price is the value of the last trade, so a code that cannot be traded cannot have a price;
    putting it in the main field silently makes the asset unpriceable.

---

## 🧮 The similarity engine

`lib/utils/assetSimilarity.ts` — pure, no Svelte, unit-tested.

**Normalize** (upper-case, strip accents and punctuation, collapse spaces) → **tokenize**,
splitting tokens into **numeric** (`25-2-33`, `1,65%`, `3,35`) and **alphabetic**. The split is
the whole idea: *dates and coupons identify a bond, trailing alphabetic markers describe its
phase or class.* Treating both the same way is the mistake to avoid.

`compareAssets(a, b)` returns a `SimilarityLink` or `null`:

| Evidence | `strength` | `reason` | Effect |
|---|---|---|---|
| Same ISIN | `strong` | `isin` | Merged automatically |
| Same ticker | `strong` | `ticker` | Merged automatically |
| Identical normalized name, no contradicting ISIN | `strong` | `name` | Merged automatically |
| Names disagree on a **numeric** token | — | — | **`null`, always.** `BTP 1/3/32` ≠ `BTP 1/3/35` |
| Different ISINs, names differ only by a couple of short alphabetic tokens | `weak` | `nameSuffix` | **Proposed** — the CUM ↔ market pair |
| One side has no ISIN, names very close | `weak` | `nameNoIsin` | **Proposed** — the two-layout case |

Only `strong` links merge on their own. `weak` links merge *and mark the group `proposed`*, so
the UI asks instead of assuming.

!!! warning "There is no dictionary of neutral suffixes"

    An earlier version carried a hard-coded list (`CUM`, `EX`, `ACC`, …). It recognised only the
    markers someone had thought of: a `PTF` or an `SR` from another broker was rejected in
    silence, and the "general rule" was in fact a private glossary to maintain.

    The judgement is now **structural**: `onlyMinorTokenDiff` asks *are the differing tokens few
    and short?* — at most **2 tokens**, at most **4 characters**, all alphabetic, on an otherwise
    identical name. It holds because by the time it is consulted the numeric guard has already
    passed: what remains cannot be a different maturity, so it is a marker.

    The price, stated plainly: a structural rule cannot tell `CUM` from `ESG`, so
    `Amundi S&P 500` and `Amundi S&P 500 ESG` will be **proposed**. That costs one click on
    *Separate*. It never causes an automatic merge — weak signals only ever propose.

---

## 🧩 Grouping and overrides

`lib/utils/assetGrouping.ts` turns pairwise links into a partition via union-find, and holds the
user's edits.

```ts
groupExtractedAssets(assets, override, confirmedSignatures) → AssetGroup[]
```

| Concept | Why it is shaped this way |
|---|---|
| `memberKey` = `fileId\|isin\|symbol\|name` | Members are keyed by **content**, not by `fakeAssetId` — the wizard reallocates those on every re-merge. This is what lets an override survive a re-parse of the same files |
| `GroupOverride` = `string[][]` (a whole partition) | Not a delta. The automatic partition is recomputed from scratch each time, so a delta would not be reproducible. A member the override does not name — a file added afterwards — falls back to being single instead of disappearing |
| `clusterSignature` / `confirmedSignatures` | Confirmation is keyed by cluster signature, so it survives recalculation |
| `GroupPrimary` reorders instead of marking | `orderedIdentifiers` puts the elected value first. Every consumer already reads `groupIsins[0]` as "the code to use", so the election reaches asset creation, candidate search and the identifier prompt without any of them learning a new concept |
| A stale election is **inert** | `leadWith()` drops an elected value the group no longer carries, so an election left over from a removed member simply does nothing |

!!! note "Names accept a value the group does not have; codes do not"

    Renaming a group is exactly the case of a value no file carries — and it is not a leftover,
    it is what the user just typed. So the `names` channel takes `allowNew`, the code channels do
    not: inventing an ISIN is an error, inventing a name is the feature.

`summariseLinks()` produces **one line per reason**, not per pair. When a reason covers every
member the text drops the names entirely (*"same ISIN · all 4 extractions"*) — when everything
matches, saying *who* adds nothing. The score is shown only below 100 %.

`representativeMap()` is the function the wizard actually uses to rewrite `tx.asset_id`; the
invariant *"every member of a group lands on exactly one survivor"* is a property of that map,
and is pinned by tests rather than by inspecting the UI.

---

## ⭐ Electing the primary identifier

`components/assets/IdentifierPrimaryChooser.svelte` — one component, four triggers.

The rule never changes: **one value leads, the others move to `identifier_other`, nothing is
discarded.** What changes is who is arguing.

| Trigger | Where |
|---|---|
| The report's code meets an existing asset's code | `checkAndPromptIdentifier()` in the wizard |
| A group carrying several ISINs creates a new asset | `startCreateAsset()` — asked **before** the form opens, so the form arrives correct |
| A provider search returns a different code | `AssetModal.applySearchResult()` |
| Provider enrichment disagrees on several fields | `ProviderComparisonModal` mounts **one chooser per conflicting identifier type** |
| Two archived assets are merged | `AssetMergeModal` |

**Provenance is recorded, never guessed.** `prefilledIdentifiers` registers at the source which
values arrived from a report. A badge that gets the origin wrong is worse than no badge, because
origin is precisely what the user decides on:

| Origin | Badge | Rationale |
|---|---|---|
| provider | blue | The only source with a price feed behind it — if a code must quote, it is this one |
| already saved | LibreFolio green | Yours, already in the library |
| report | grey | A document: informative, but mute |

Design points worth preserving:

- **A provider search is a source of information, not an authority.** It may not overwrite a code
  the user took from their own document. The `applySearchResult` path used to `map` over the rows
  and replace the value outright — the previous code simply ceased to exist.
- **The provider link is established immediately anyway.** Only the *identity* question is
  deferred; blocking the provider assignment too would punish the user for having searched.
- **Cancelling destroys nothing**, and says so. Dismissing the modal keeps the report's code as
  primary while the provider's value still lives in the provider assignment, which carries its
  own `identifier`. A confirmation states this *before* it happens — the only moment it is cheap
  to change your mind.
- **The issuance note describes a mechanism, not a country.** It used to say "BTP" and "loyalty
  premium"; the same structure exists wherever a security is placed under a dedicated code that
  rewards holding to maturity and, precisely because it is not meant to be traded, has no market
  price. The key is `issuanceNote`, not `btpNote` — a key name is documentation too.

---

## 🧲 Merging assets already in the database

`POST /api/v1/assets/merge` — `{source_asset_id, target_asset_id, dry_run}`. The target is always
the survivor; the endpoint never picks. With `dry_run` it returns the counts without writing,
which is what `AssetMergeModal` shows before asking for confirmation. The whole thing runs in a
**single transaction**.

There are exactly four foreign keys to `assets.id`, all handled:

| Table | Constraint | Policy |
|---|---|---|
| `Transaction.asset_id` | nullable, no unique | Reassigned to the target |
| `PriceHistory.asset_id` | `uq_price_history_asset_date` | Reassigned; on a same-day collision the **target's** row wins |
| `AssetEvent.asset_id` | no unique (deliberately) | Reassigned, deduplicated by `(date, type, amount)`, and `Transaction.asset_event_id` is remapped onto the survivors |
| `AssetProviderAssignment.asset_id` | `uq_asset_provider_asset_id` | Moved only if the target has none; otherwise the source's is deleted |

`identifier_other` on the target becomes the **union** of both `other` lists plus every
structured identifier of the source the target does not already hold as a primary. Then the
source asset is deleted.

!!! danger "Two ordering traps, both found by tests"

    - `AssetEvent.provider_assignment_id` is `ondelete=CASCADE`: deleting the source's provider
      assignment **silently destroyed the events just migrated**. Events must be repointed
      *before* the delete.
    - `Transaction.asset_event_id` is `ondelete=RESTRICT`: duplicate events cannot be dropped
      until the transactions pointing at them have been remapped.

---

## 🔎 Recognising the asset on the next import

The election is only worth making if the stored value is actually used next time.
`search_asset_candidates` in `backend/app/services/brim_provider.py` ranks candidates:

| Priority | Criterion | Confidence |
|---|---|---|
| 1 | `identifier_isin` exact | `EXACT` |
| 2 | ISIN found in `identifier_other` | `HIGH` |
| 3 | `identifier_ticker` exact | `MEDIUM` |
| 4 | Name (partial, then `display_name`) | `LOW` |
| 5 | Name found in `identifier_other` | `LOW` |

Priorities 1 and 2 run **together** and merge (deduplicated by `asset_id`). That is deliberate:
an ISIN that is primary on a duplicate asset and alternative on the good one produces **both**
candidates, side by side — which is exactly the moment offering a merge costs the user least.

!!! note "Why 2 is not last"

    It used to run only `if not candidates`, so any vaguely plausible **name** match excluded it.
    But an ISIN the user deliberately saved under `identifier_other` is an assertion; a name
    resemblance is a guess. The assertion has to win.

The frontend side is symmetrical: `AssetSelect` and `ImportAssetPicker` search `identifier_other`
too — otherwise a code the user saved on purpose would be invisible in the very field where they
would look for it.

!!! tip "What is searchable is what is *named*, not what is *described*"

    Currency and asset type were once in the search text. In an all-EUR library, `eur` matched
    every row, so typing "Eurizon" narrowed nothing until the fourth letter. Same class of bug:
    `SearchSelect` matched against `option.icon`, which for assets is a path
    (`/icons/asset-types/bond.png`), so any one- or two-letter query matched everything. Icons
    are searchable **only when the icon is the symbol itself** (a flag pasted in the box).

---

## 🔗 Related

- **[Import Wizard](import-wizard.md)** — the flow these components live in.
- **[BRIM Architecture](../../../backend/brim/architecture.md)** — parsing and candidate search.
- **[Assets Architecture](../../../backend/assets/architecture.md)** — the backend model behind identifiers and providers.
