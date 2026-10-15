---
title: "Two measurements of the Spanish toolbar differed by 15 px: the denseRow thresholds compare the bar's width, not the viewport's, and the scrollbar gutter changes it (V-19)"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, layout, responsive, toolbar, i18n, spanish, scrollbar, measurement, workstream-i, workstream-v, release-1.2]
related:
  - concepts/responsive-4mode-layout
  - sources/phase00-ui-polish-2026-10
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: the same bar, measured twice, 15 px apart

## Symptom

V's toolbar sweep went red in Spanish (V-19): the «Exportación IA …» group left the Dashboard's bar by up to 11.0 px
at a 1310 px viewport, and the asset detail's by up to 11.8 px at 1210 px
([[concepts/responsive-4mode-layout]], «A translation can expire the calibration»). When workstream I reproduced it
(plan 48), its numbers did not match V's: the same red appeared at viewports 15 px apart.

## Root Cause

- **The thresholds compare the bar's width.** A page's `denseRow` threshold is tested against the toolbar's own width,
  not against the viewport: «il bisogno non dipende dalla vw, perché le soglie confrontano la larghezza della barra»
  ("the need does not depend on the viewport width, because the thresholds compare the bar's width").
- **The bar is narrower by the scrollbar gutter.** The gutter is measured when the page loads: 15 px in one run, 0 in
  the next. At the same viewport the bar changed by 15 px, so V's viewports (1320/1310, 1220/1210) and I's
  reproduction described the same bar.
- **The sweep's numbers were grid points.** +11.0 and +11.8 px were only where the sweep's 10 px grid fell. The
  actions group in `denseRow` always needs 968 px on the Dashboard and 868.8 px on the asset detail; at the old
  thresholds (950 and 850) the worst case, a bar exactly as wide as the threshold, overflows by 18.0 and 18.8 px.

## Solution

`7f8febd9d` («fix(layout): Spanish toolbar no longer overflows», train 72): `denseRow` from 950 to 990 on the
Dashboard (below its `oneRow`, 1000) and from 850 to 890 on the asset detail — margins of 22 and 21.2 px over the
measured need. `front-utility toolbar-width-sweep` for Spanish was red before (2 failed) and green after; the full
sweep passed 15 of 15, and the served bundle was checked for the new values.

## Prevention

- Reason about the quantity the threshold compares — here the bar's width — and derive the margin from the worst
  case, not from where a sweep's grid happens to fall.
- When two measurements of the same element disagree by a constant, look for a layout input measured at load, such
  as the scrollbar gutter, before suspecting the code.
- 48-1, the AI Export button padded wider than its neighbours in the same bar, was closed in 1.3 by workstream Y,
  lot Y8 (2026-10-15): its trigger and the Dashboard's `sync-button` beside it now use `gap-1.5 px-2.5`, like the
  toolbars of the asset, broker and FX pages. V-19 itself is closed in the backlog (`2166eeb90`).

## Source files

| Role | Path |
|------|------|
| Dashboard thresholds | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Asset detail thresholds | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Plan 48 (step 5, the correction) | `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` |
| Backlog (V-19, 48-1) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| AI Export trigger (48-1) | `frontend/src/lib/features/ai-export/AiExportMenu.svelte` |
