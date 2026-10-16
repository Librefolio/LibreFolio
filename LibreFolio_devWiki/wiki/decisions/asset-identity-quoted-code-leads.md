---
title: "One asset per security: the quoted code leads, every other code lives in `identifier_other`; unify before repairing, merge what got in anyway (P3, D1–D11)"
category: decision
status: accepted
date: 2026-08-08
tags: [backend, frontend, assets, identifiers, import, brim, merge, bonds, beta-testing, release-1.1]
related:
  - features/F-024
  - features/F-049
  - workflows/brim-import-flow
  - entities/import-wizard-modal
  - problems/asset-merge-cascade-deleted-the-migrated-events
  - problems/import-wizard-fake-id-collision
  - sources/beta-testing-2026-08-05
---

# Decision: the quoted code leads

## Context

The beta test of 05/08/2026 hit one security four times in a row. Italian retail government bonds (BTP Valore, BTP
Più, BTP Italia) live under **two ISINs**: a placement code ("CUM") that earns the loyalty premium but cannot be traded,
so no provider prices it, and a market code that is quoted. The tester's report carried the CUM code, the provider the
market one, and:

1. candidate search looked in `identifier_other` only as a last resort, after a name match that could return spurious
   candidates;
2. the identifier dialog offered only «replace» or «assign only», so keeping both codes meant losing one;
3. the asset picker did not search `identifier_other`;
4. once matured and deactivated, the asset could not be picked at all.

Each is a nuisance; in a row they force a duplicate asset. A fifth obstacle came out of the analysis: one broker's two
report layouts (Crédit Agricole *Deposito Titoli* without the ISIN, *Movimenti Conto* with it) delivered one security
as two assets to resolve twice.

## Decision

The plan `plan-phase00AssetIdentityAndIdentifiers` (P3, which replaced `plan-phase00AssetLifecycleAndIdentifiers`)
recorded eleven decisions. **One asset per security**: `identifier_isin` holds the market code, the one a provider can
index; the CUM code goes into `identifier_other`, so every re-import that cites it finds the asset again.

| # | Decision | Why |
|---|---|---|
| D1 | `identifier_other` stays the **generic container**; no new typed field | «Oggi è ISIN, domani ticker e poi chissà»: the list is additive, normalised and searchable |
| D2 | When two codes of the same type conflict, the **user elects the primary**; the others move to `other`, never a silent destructive replace | One gesture solves the CUM/market case and any future type |
| D3 | The **origin** of every value is always shown (provider, already saved, report) | Origin is exactly what the user decides on |
| D4 | **Inactive assets are selectable everywhere**, with a badge, sorted last; picking one does **not** reactivate it | Final coupons, redemptions and loyalty premiums land on matured, deactivated securities |
| D5 | A dedicated **«Unify assets»** step, skipped when there is nothing to decide | Identity is a different job from resolution, and its result must drive the candidate search |
| D6–D7 | Groups are drawn as **DOM chips** (solid border = confirmed, dashed = proposed, bare = single), **not** an ECharts canvas | A canvas has no DOM nodes and no `data-testid`, and its drag moves a layout position, not group membership |
| D8 | **Token-aware similarity**: a difference in a numeric token is a strong negative; a short trailing alphabetic marker is neutral | Tells `BTP 1/3/32` from `BTP 1/3/35` (never propose) without losing `… CUM` ↔ `…` (propose) |
| D9 | Merging the duplicates **already in the database** is in scope | The import fix stops new duplicates; without a merge the old ones are permanent debt |
| D10 | Two ordered stages: first among the **import's** assets, then the resulting group against the **database**; the primary is elected **only in the second** | Developer, 07/08: in the first stage there is nothing to elect, only «these rows are the same security» |
| D11 | «Unify assets» comes **before** the repair step | Developer, 08/08: «quando bisogna scegliere l'asset si sceglie già tra quelli agglomerati» |

D11 had a concrete proof behind it. The repair step's asset dropdown is derived from the asset resolutions, and the
placeholder remap is per file, so one bond present in two files showed up as **two identical entries**: a fee typed
against one of them landed on half the instrument, invisibly.

## What the code does today

- **Order of the steps**: `upload → select → analyze → assets → fix → duplicates → review` (`STEP_DEFS` in
  `ImportWizardModal.svelte`), plus the report-set gap step. `v1.1.0` already had `assets` before `fix`.
  The [1.1.0] CHANGELOG line «Wizard rework» lists *corrections* before *unify assets*, which does not match the code.
- **Similarity** (`assetSimilarity.ts`): the first version (`0e07359b4`, 08/08) kept a list of neutral suffixes
  (`NEUTRAL_SUFFIX_TOKENS`: `CUM`, `EX`, `ACC`, `DIST`, …). `d1e04b2b8` (12/08) replaced it with a structural rule,
  `onlyMinorTokenDiff`: at most two differing tokens, short and non-numeric, on an otherwise identical name. A list
  knew only the markers someone had thought of; the price of the rule is that `… ESG` against the plain fund name is
  *proposed*, one click on «Separate». A weak signal only ever proposes; it never merges on its own.
- **Grouping** (`assetGrouping.ts`): the pairwise links become groups whose members are keyed by content
  (`memberKey`) rather than by placeholder id, so a user's regrouping survives a re-parse.
- **Electing the primary** (`IdentifierPrimaryChooser.svelte`): one component, five triggers — the report's code meets
  a saved code, a group with several ISINs creates an asset, a provider search returns another code, provider
  enrichment disagrees, two assets are merged. Nothing is discarded: the losing values move to `identifier_other`.
- **Recognition next time** (`search_asset_candidates` in `brim_provider.py`): an exact `identifier_isin` match and an
  ISIN found in `identifier_other` run **together**, so a code that is primary on a duplicate and alternative on the
  good asset yields both candidates side by side; the wizard offers **Merge** only when at least two candidates are
  `EXACT` or `HIGH` (`duplicateCandidates()`). The pickers (`AssetSelect`, `ImportAssetPicker`) search
  `identifier_other` too.
- **Merge** (`POST /assets/merge`, `AssetMergeModal`, `0e07359b4`): the target always survives and the endpoint never
  picks it; `dry_run` returns the counts the dialog shows before anything is destroyed; the whole merge is one
  transaction. Two ordering traps were found by its tests: [[problems/asset-merge-cascade-deleted-the-migrated-events]].

Everything above shipped in **1.1.0** (`0e07359b4` and `d1e04b2b8` are ancestors of `v1.1.0`), under the CHANGELOG
section «🔁 Import flow & asset identity (post-beta)», line «Instrument unification inside the wizard».

## Consequences

- A price provider can always index the asset: a code that cannot trade has no price, so it never sits in the main
  field.
- The duplicates a beta tester created before the fix can be folded away, from the asset list («Merge with…») or from
  the wizard's resolution card.
- Any new identifier type joins `identifier_other` without a schema change (D1).

## Source files

| Role | Path |
|------|------|
| Similarity engine | `frontend/src/lib/utils/assetSimilarity.ts` |
| Grouping and overrides | `frontend/src/lib/utils/assetGrouping.ts` |
| Identifier ordering | `frontend/src/lib/utils/assetIdentifiers.ts` |
| Unify step | `frontend/src/lib/features/transactions/import/AssetGroupStep.svelte` |
| Primary chooser | `frontend/src/lib/components/assets/IdentifierPrimaryChooser.svelte` |
| Merge dialog | `frontend/src/lib/components/assets/AssetMergeModal.svelte` |
| Picker (D4) | `frontend/src/lib/components/ui/select/AssetSelect.svelte` |
| Duplicate notice in the wizard | `frontend/src/lib/features/transactions/import/importResolutionHelpers.ts` |
| Candidate search | `backend/app/services/brim/brim_provider.py` |
| Merge endpoint | `backend/app/api/v1/assets/crud.py` |
| Merge service | `backend/app/services/assets/crud.py` |
| Merge tests | `backend/test_scripts/test_db/test_asset_merge.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md` |
| Developer docs | `mkdocs_src/docs/developer/frontend/components/features/asset-identity.md` |
| User docs | `mkdocs_src/docs/user/assets/create-edit.en.md` |
