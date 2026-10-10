---
title: "Phase 0 / 25 — Workstream K: asset taxonomy and selects, then 15 follow-up lots (steps 1–23)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/
tags: [phase0, release2, workstream-k, asset-types, select, import-wizard, bulk-editor, xss, auth, modals, escape, pwa, layout, i18n, svelte5]
related:
  - decisions/asset-type-two-level-taxonomy
  - decisions/html-escape-at-the-source
  - problems/stale-price-banner-never-emitted
  - problems/svelte5-teardown-reads-stale-state-timers
  - problems/broker-icon-fields-request-loop
  - problems/modal-layers-escape-and-backdrop
  - problems/fixture-skip-hid-api-test
  - concepts/responsive-4mode-layout
  - entities/import-wizard-modal
  - features/F-001
  - features/F-048
---

# Source: Phase 0 / 25 — workstream K (2026-09-24 → 10-09)

## Summary

One analysis and 18 plans of workstream K (Italian), archived on 2026-10-09 (train 26) after a read-only check that
every delivery is in the code and every commit is an ancestor of `dev_release2`. The folder is named after the first
lot — the asset-type taxonomy and the selects — and then collected K's later lots, one plan each: import duplicates,
a request loop, bulk-editor order and guards, review follow-ups, the developer's notes (a stored XSS among them),
timers at teardown, toolbar sweeps, asset-detail UX, device notes, coverage triage, app start, Escape layering, pure
defects, the register link. Until step 16 the lots reached `dev_release2` by fast-forward; from step 17 by named
trains (4 → 25).

## Lots and what the wiki keeps

| Step | Date | Lot | Wiki |
|---|---|---|---|
| analysis + plan | 09-24 | Two-level type select (`TreeSelect`, `AssetTypeSelect`), composite icons, `CROWDFUND_REAL_ESTATE`, tiered ranking (R13), provider comparison queue (R18); D-K1 … D-K5 | [[decisions/asset-type-two-level-taxonomy]] |
| 9 | 09-24/28 | Import: a row the DB already holds is never the default keeper (C1); resolver choices survive rechecks (C2); write-only fields removed (C6) | [[entities/import-wizard-modal]] |
| 10 | 09-25/28 | Broker icon fields asked once per broker (C3) | [[problems/broker-icon-fields-request-loop]], [[concepts/entity-store-pattern]] |
| 11 | 09-25/28 | Bulk: new rows keep their creation order (C4) | [[features/F-048]] |
| 12 | 09-29 | App title on every page (guard `documentTitle.guard.test.ts`), selection cleared after a save, flags with one font (`'LF Flags'`) | [[problems/flag-emoji-windows]] |
| 13 | 09-30/10-01 | Developer's notes: stored XSS in HTML sinks, Borsa Italiana currency (library 0.3.2), stale prices with a sync CTA, login and password managers, PWA icons, phone layouts, toolbars | [[decisions/html-escape-at-the-source]], [[problems/stale-price-banner-never-emitted]], [[concepts/responsive-4mode-layout]], [[features/F-099]], [[features/F-098]], [[features/F-032]] |
| 14 | 10-01 | Tooltip teardown (timers cancelled); linked-pair test fixture | [[problems/svelte5-teardown-reads-stale-state-timers]], [[problems/fixture-skip-hid-api-test]] |
| 15 | 10-02/05 | Toolbar sweep: gutter measurement; long broker filter label | [[concepts/responsive-4mode-layout]] |
| 16 + R1 | 10-06 | Asset detail: price tooltip on phones, share hashtags, ‹ n/N › navigation; `TreeSelect` timers | [[features/F-033]], [[concepts/echarts-chart-gotchas]], [[problems/svelte5-teardown-reads-stale-state-timers]] |
| 17 | 10-06 | Device notes: AssetModal footer on phones, a family-only type proposal counts as a match | [[decisions/asset-type-two-level-taxonomy]] |
| 18 | 10-07/08 | Coverage triage: one Escape closes the top layer only; a refused broker edit stays in the form; three E2E reds | [[problems/modal-layers-escape-and-backdrop]] |
| 19 | 10-08 | App start: a slow server is not a sign-out, `?redirect=`, modal backdrop margin, Escape on the `SearchSelect` trigger | [[features/F-001]], [[problems/modal-layers-escape-and-backdrop]] |
| 20 | 10-08 | Escape of `SimpleSelect` (the wizard's «Read as» list) | [[problems/modal-layers-escape-and-backdrop]] |
| 21 | 10-08 | Pure defects: avatar lost after saving a preference; `{n}` in 8 messages; ICU-argument guard | [[features/F-008]] |
| 22 | 10-09 | «Register here» hidden when registration is closed; profile date and grid sizes in the app language | [[features/F-001]] |
| 23 | 10-09 | Bulk: cloning pairs; false «Discard changes?» after a Reset or before the type cache; row Reset on pairs | [[features/F-048]] |

## Key takeaways

- **A plan's consequence can be overtaken by another workstream**: D-K3 expected real-estate crowdfunding inside the
  Real-estate slice of the allocation pie; the charts later grouped by family (workstream I, D15), so at HEAD it sits
  under Crowdfund. Checked against `allocationHierarchy.ts`, not the plan.
- **Svelte 5 reactivity traps recur**: props are getters, so an effect re-runs on every version bump of a store it
  reads ([[problems/broker-icon-fields-request-loop]]); teardown reads state that is already gone
  ([[problems/svelte5-teardown-reads-stale-state-timers]]).
- **Guards over promises**: two XSS gates keyed by content, an Escape-layer harness that proves the inner layer
  handled the key before asserting the modal, an ICU-argument guard that parses calls with `svelte/compiler`, the
  enum/scenario coverage gates, a PWA asset test — each one written red first by the test-author.
- **Defects that shipped in v1.1.0** and were fixed here: the stored XSS, the broker request loop, the false discard
  prompt on pairs, a 5 s timeout read as a sign-out, the stale-price banner never emitted.
- **Smaller fixes kept only here**: the avatar vanished from the sidebar after saving a preference, because
  `userSettings.setDirect` replaces the whole value (fixed in the caller, `PreferencesTab`, by merging the current
  settings); `formatBytes` and the profile date now take the app language (residuals C-10, C-11 for other sites);
  the browser tab always shows the `<title>` of `app.html` (developer's rule of 2026-09-29) — Svelte applies a
  `<svelte:head><title>` by assigning `document.title` after mount and never restores it on unmount, which is how
  "Files - LibreFolio" outlived the Files page; `documentTitle.guard.test.ts` fails on either form of a title write.

## Residuals (backlog `Phase_0/38_postReleaseBacklog`, K-1 … K-26)

K-1 … K-4 bulk pairs and slow path; K-5 first-user registration when closed; K-6/K-7 PWA on iPhone/Android; K-8/K-9
E2E hygiene; K-10 a test that runs the real JS-cache update with the network; K-11 `entityStore.merge` bumps on
identical data; K-12 timer handles kept in `$state`; K-13/K-14 flags in ECharts and hand-written stacks; K-15
ECharts formatters outside the XSS gates; K-16 ETC/ETN as `ETF`; K-17 `PasswordInput` eye button; K-18 … K-20
dashboard/asset-list/asset-detail UX; K-21/K-22 AssetModal; K-23 `TreeSelect` focus after Escape; K-24 data-quality
doc; **K-25 the four devWiki pages — written on 2026-10-09** ([[problems/svelte5-teardown-reads-stale-state-timers]],
[[decisions/html-escape-at-the-source]], [[problems/stale-price-banner-never-emitted]],
[[concepts/responsive-4mode-layout]]); K-26 an outdated test header.

**Translation debt**: K rewrote eight English mkdocs pages without touching IT/FR/ES, none stamped
(`financial-theory/instruments/asset-types/` index, etfs, real-estate; `user/assets/` create-edit, index, detail;
`user/dashboard/index`; `user/transactions/import/how-to`).

## Source files

| Role | Path |
|------|------|
| Folder index | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/README.md` |
| Entry analysis | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/analysis-phase00TaxonomySelect.md` |
| First lot | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelect.prompt.md` |
| Step 13 (XSS, stale prices, PWA, layouts) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md` |
| Step 19 (app start) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md` |
| Step 23 (bulk guard) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md` |
| Backlog (K-1 … K-26) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
| Title guard (step 12) | `frontend/src/routes/documentTitle.guard.test.ts` |
| Preferences merge (step 21) | `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte` |
