---
title: "Open panels stayed stale after «Sync rates»: the banner reloaded the report but sent no refresh signal"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, dashboard, svelte5, data-quality, fx, lots, risk, refresh, cache, workstream-v]
related:
  - decisions/data-quality-proved-on-real-data
  - features/F-054
  - sources/phase00-data-quality-e2e-2026-10
---

# Problem: open panels stayed stale after «Sync rates»

## Symptom

On the Dashboard, the data-quality banner's «Sincronizza tassi» (Sync rates) fetched the missing FX rates and the
report reloaded: the KPI cards and the positions healed (P&L +60,00 €, +10,00 % in the test). A lots panel already
open kept its old `MISSING_FX_RATES` warning, and no new `POST /portfolio/lots/analysis` left the page in the 45 seconds
after the click. The risk panel, when mounted, was in the same position: risk depends on exchange rates too. Found by
test E1 of workstream V's real-data E2E (plan 46), red for exactly this reason before the fix.

## Root Cause

`syncMissingFxRates()` (`dashboard/+page.svelte`) called `invalidate()` and reloaded the report, but did not increment
`refreshVersion`, the signal that the «Aggiorna» (Refresh) button sends and that the open panels listen to —
`LotsAnalysisPanel.svelte` reloads its analysis and the selection's histories when the value changes, and
`RiskLevelsPanel` receives it too. A panel that holds its own data does not see a report reload.

## Solution

Commit `15bfcf1e8` ("fix(dashboard): refresh open panels after FX sync", train 56): in `syncMissingFxRates()`, after
`invalidate()` and only without a transport error, `refreshVersion += 1`. With the fix the lots request leaves about
1 ms after the sync's response, together with the report reload, and E1 is green with 1 and with 4 workers. The
decision to write the red test and the fix in the same lot was the developer's (D2,
[[decisions/data-quality-proved-on-real-data]]).

## Prevention

Any action that changes the data under the Dashboard must send the same refresh signal as «Aggiorna», not only reload
the report. **The same gap after «Sync prices» (V-1)** — the stale-price button (`sync_asset_prices` in
`handleBannerAction`) reloaded the report without incrementing `refreshVersion`, so open panels stayed old until a
reload — was closed the same way in V's batch 2 (`a0722f755`, train 58): red first in `stale-price-banner.spec.ts`
(the lots panel already open must ask `POST /portfolio/lots/analysis` again, in the same page load), then
`refreshVersion += 1` after `invalidate()`.

## Source files

| Role | Path |
|------|------|
| `syncMissingFxRates`, `refreshVersion`, `handleBannerAction` | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| The listener in the lots panel | `frontend/src/lib/features/brokers/lots/LotsAnalysisPanel.svelte` |
| E1, the red then the green | `frontend/e2e/portfolio/data-quality-real.spec.ts` |
| Developer doc (the `sync_fx_pair` CTA) | `mkdocs_src/docs/developer/frontend/data-quality-banner.md` |
| Backlog V-1 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
