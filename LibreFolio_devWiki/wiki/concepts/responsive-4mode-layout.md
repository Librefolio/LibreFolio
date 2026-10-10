---
title: "Responsive page toolbars: four tiers per page, thresholds measured, not guessed"
category: concept
tags: [frontend, responsive, layout, breakpoints, toolbar, ux, i18n, e2e, calibration]
related_features: [F-021, F-032, F-033, F-054]
related: [concepts/dual-view-pattern, sources/phase00-taxonomy-select-2026-10, sources/phase06-bugfix-migration]
---

# Concept: responsive page toolbars

> **Rewritten 2026-10-09 (checked at `083ed26dc`).** Until then this page described the April 2026 pattern — four
> modes `wide`/`tablet`/`tablet-s`/`mobile` at fixed breakpoints 1100/770/500 px, each page with its own
> `ResizeObserver`, and it recommended "extracting `responsiveLayout.svelte.ts`". That extraction happened long ago;
> the model below replaced the fixed breakpoints, and its thresholds were **calibrated by measurement** on
> 2026-10-01 (workstream K, step 13 — backlog K-25 asked for this page). The old model is summarised under *History*.

## Definition

Five page toolbars — Assets list, Asset detail, Dashboard, Broker detail, FX list — are built on one component,
`PageToolbar.svelte`, driven by `createResponsiveLayout()` (`responsiveLayout.svelte.ts`). The bar has three blocks
(the DateRangePicker, a centre of filters, a 2×2 grid of actions) and **four tiers**, chosen from the bar's own width
(`ResizeObserver`) against **per-page thresholds**:

| Tier (`LayoutMode`) | Below threshold… | Layout |
|---|---|---|
| `oneRow` | — (widest) | picker on one row, centre and actions beside it |
| `denseRow` | `oneRow` | same structure, denser: the picker goes to two internal rows; a page may reflow its own centre |
| `stackFilters` | `denseRow` | the centre moves **below** the picker; the actions stay beside that column |
| `oneColumn` | `stackFilters` | picker, centre and actions stack in one column (actions keep their labels) |

Labels are an independent axis: `labelHideActions` and `labelHideTabs` hide the text of action buttons and tabs
below their own widths (labels first shrink via `labelShrink.ts`); `noExtraLabel` lets a page shed a decorative label
(the Dashboard's "Currency:" prefix). The `oneColumn` number is deliberately inert — nothing narrower exists yet.

## Calibration — measure the content, in every language (2026-10-01)

**Symptom.** At intermediate widths buttons spilled out of the bars: the thresholds, set by eye in English, were
10–30 px too low.

**Method.**
- For each bar, tier and language, a probe on a copy of real data measured the minimum width the content needs (bar
  width + overflow) while the viewport narrowed from 1920 to 320 px.
- The profile language had to be changed **in the database copy**: the saved user language overrides
  `localStorage` at login.
- Each threshold = **max over the four languages + 16 px, rounded to the nearest ten**. Spanish was usually the
  longest — not French, as first assumed.
- Values were tried live through `window.__lfLayouts.<name>.thresholds` (`registerLayoutDebug`), which recompute the
  tier without a resize.

**Result** (before → after, verified in the pages at `083ed26dc`):

| Bar (`layoutDebugName`) | `denseRow` | `stackFilters` | `labelHideTabs` |
|---|---|---|---|
| assetsList | 850 → **1020** | 440 → **520** | — |
| assetDetail | 780 → **850** | 400 → **510** | — |
| dashboard | 810 → **950** | 430 → **510** | 370 → **460** |
| brokerDetail | 800 → **840** | 470 → **530** | 370 → **660** |
| fxList | 930 → **1030** | 440 → **560** | — |

Also: the asset-list filters became `flex-1 min-w-0` in `oneColumn`, and the asset-detail header containers got
`min-w-0` after red bands at 330→320 and 1060→1030 px.

## The gate and its measuring rule

`frontend/e2e/layout/toolbar-width-sweep.spec.ts` sweeps every bar in FR/IT/ES from 1700 px down to 320 + g px in
10 px steps and fails on any overflow of the bar or of the page, named by testid.

- **The gutter.** `app.css` sets `html { scrollbar-gutter: stable }`; on a host with classic scrollbars the gutter
  takes ~15 px even headless. Measure it as `innerWidth − document.documentElement.getBoundingClientRect().width` —
  **not** `innerWidth − clientWidth`, which reads 0 headless — sweep down to `320 + g`, and check page overflow
  against the layout box, with a positive control (step 15, 2026-10-02/05). Injecting CSS to hide the scrollbar was
  rejected: it changes the layout under test.
- **Long names truncate.** A 31-character broker name overflowed the Dashboard's broker filter on a phone: the
  button now truncates with an ellipsis (`min-w-0` on the wrapper, `max-w-full`, `truncate`), pinned by
  `dashboard-broker-filter-label.spec.ts`. Wrapping was rejected.

**Rule for a new toolbar or a new label:** give it `PageToolbar` thresholds measured the same way (four languages,
+16 px, rounded) and add it to the sweep; a threshold guessed in one language will be wrong in another.

## History — the April 2026 model

The first version (Phase 6, `responsiveLayout` born in Step 2c) used four global modes at fixed widths: `wide`
≥ 1100 px, `tablet` 770–1100, `tablet-s` 500–770 (icon-only actions in a right column — the addition that gave the
pattern its name), `mobile` < 500, on the Assets and FX lists only. Rounds 11–14 renamed the tiers, removed the
icon-only tier, split the label axes and moved the thresholds into each page; K's calibration replaced the guessed
values.

## Source files

| Role | Path |
|------|------|
| Tier logic, thresholds, `__lfLayouts` live tuning | `frontend/src/lib/utils/layout/responsiveLayout.svelte.ts` |
| Toolbar component | `frontend/src/lib/components/ui/toolbar/PageToolbar.svelte` |
| Assets list thresholds | `frontend/src/routes/(app)/assets/+page.svelte` |
| Asset detail thresholds | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Dashboard thresholds | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker detail thresholds | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
| FX list thresholds | `frontend/src/routes/(app)/fx/+page.svelte` |
| Scrollbar gutter | `frontend/src/app.css` |
| Width sweep gate | `frontend/e2e/layout/toolbar-width-sweep.spec.ts` |
| Long broker label | `frontend/e2e/portfolio/dashboard-broker-filter-label.spec.ts` |
| Calibration (step 13 §5) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md` |
| Gutter (step 15) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep15ToolbarSweepGutter.prompt.md` |
