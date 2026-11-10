---
title: "Page busy: one Refresh per page, and what it waits for"
category: concept
date: 2026-10-17
tags: [frontend, svelte, pagebusy, refresh, ux, p3, e2e]
related: [problems/direct-playwright-run-in-a-test-lane, problems/e2e-chained-waits-outlast-the-test-budget, sources/phase00-fx-dashboard-sync-2026-10]
---

# Concept: Page busy — one Refresh per page, and what it waits for

## Definition

Every page has **one Refresh button** in its toolbar. It spins, greys out and cannot be pressed again while the page's
«big» requests are in flight: the ones the page decided to make, upstream, because the user asked for something. It
never moves for a reload the user did not ask for. This is developer decision 48 / P3 (16/10/2026), delivered as Y11 of
release 1.3.

The mechanism is `pageBusy` (`frontend/src/lib/stores/app/pageBusy.svelte.ts`), a store of **tokens**:
- `track(label, work)` holds a token while `work()` runs, and ends it in `finally`;
- `begin`/`end` do the same by hand;
- `join(label, work)` takes a token only if the page is already busy (N55): a lazy load that completes what the page is
  doing makes the button wait for it, but the same load on a quiet page does not;
- every token has a timeout (`PAGE_BUSY_TIMEOUT_MS`, 120 s): the request is not cancelled, the button just stops
  waiting for it;
- `reset()` runs on a change of route (`onNavigate` in `routes/(app)/+layout.svelte`) and on a client-session reset.

The writers read the pending list with `untrack`, because `track`/`join` are called from `$effect`s: an effect that
started depending on the list would rerun at every token, or loop.

## The rules

1. **Tokens sit on the trigger, never inside a load function.**
   - The same `loadAll()`/`loadOverview()`/`handleRefresh()` also runs in the background: after a price catch-up
     (Z-13), after a sync, or for a cache a portfolio mutation marked stale.
   - The token therefore wraps the call where the user's request arrives:
     - `onMount`;
     - the button's handler;
     - the period, currency or scope change;
     - the panel that opens;
     - the view toggle and the calendar window on an asset's page (N64);
     - the reload after a save in a window (`assets-reload`, `asset-reload`).
   - On an asset's page the token sits on the button's `onrefresh`, because `handleRefresh()` also runs after a sync.
2. **Never for**:
   - the live-price poller;
   - per-card and per-row refreshes;
   - actions with their own indicator (price and FX sync, the import wizard, a save in a modal, the PAC's «Calcola»);
   - background reloads: after a price catch-up, and after a sync (P3), e.g. `handlePageSyncComplete()` on an asset's
     page.
3. **Panels keep their own tokens.** A sync can still make the button wait for an open panel.
   - The Dashboard's data-quality banner syncs bump `refreshVersion`, and the asset page's `handleRefresh()` bumps
     `riskRefreshVersion`.
   - So an open lots panel or Risk tab reloads under its own `risk-refresh`/`lots-*-refresh` token.
   - Accepted as behaviour; under review with N55/N64.
4. **The button contract**: `disabled={pageBusy.busy}`, `data-busy`, and `animate-spin` on the icon. The colour comes
   from the button's text: no palette class.
   - A presentational toolbar component takes a `busy` prop rather than reading the store (`AssetDetailToolbarActions`).
5. **The page root keeps its own `data-busy`**, from the page's loading flags, and `waitForSettled()` waits on it.
   - After a price catch-up both stay `false`: the button because no token is taken, the Dashboard root because the
     reload runs with `{background: true}` (Z-18).
6. **A double Refresh is no longer reachable.** While its first request runs, the button is disabled.
   - An E2E that pressed Refresh twice mid-load to prove «the newest request wins» now starts the first request
     through a path with no token (the page's own Sync, stubbed in the browser), then presses Refresh.
   - See `refreshThroughPageSync()` in `frontend/e2e/assets/asset-detail.spec.ts`.

## Testing it

- **Vitest**: `frontend/src/lib/stores/app/pageBusy.test.ts` pins the tokens, the timeout and the warning, `track`
  on a rejection or a throw, `join` on an idle and on a busy page, and that no writer makes an `$effect` depend on the
  store.
  - Its `// @vitest-environment jsdom` docblock is load-bearing: under `node`, `$effect` never runs.
- **E2E**: `frontend/e2e/portfolio/page-busy.spec.ts`. A localhost answer lands before an assertion can look, so each
  case *owns* the busy state:
  - `hold()` parks the request the trigger sends (by method, path and body) through `page.route`;
  - `expectBusy()`/`expectIdle()` read only `data-busy` and `disabled`;
  - `recordBusy()` keeps every value through a `MutationObserver`, so «it never waited» means never.
  - A **control** follows in the same page under the same recording: a user action that must make the button wait.
    Without it, the silence proves nothing.
  - The asset pages' block also refuses the live poll at the network and answers the page's Sync in the browser, so
    nothing is written.
- Running a single case or a trace needs a direct Playwright run: see [[problems/direct-playwright-run-in-a-test-lane]].

## Where it applies

The eleven page buttons (Dashboard, broker page and list, Transactions, Files, FX list and detail, Assets list and
detail, Tools hub and tool page) and the Assets list's Correlation tab «Reload All». They are listed with their lines
in the developer page `mkdocs_src/docs/developer/frontend/state/app-state.md`, section «Page busy».

## Source files

| Role | Path |
|------|------|
| The store and its contract | `frontend/src/lib/stores/app/pageBusy.svelte.ts` |
| Store tests | `frontend/src/lib/stores/app/pageBusy.test.ts` |
| Reset on route change | `frontend/src/routes/(app)/+layout.svelte` |
| Dashboard triggers | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker page triggers | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
| Asset page triggers (N64, post-sync) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Asset toolbar button (`busy` prop) | `frontend/src/lib/components/assets/detail/AssetDetailToolbarActions.svelte` |
| Assets list, Correlation «Reload All» | `frontend/src/routes/(app)/assets/+page.svelte` |
| Risk panels' own tokens | `frontend/src/lib/features/risk/riskPanelController.svelte.ts` |
| Lots panel's own tokens | `frontend/src/lib/features/brokers/lots/LotsAnalysisPanel.svelte` |
| E2E | `frontend/e2e/portfolio/page-busy.spec.ts` |
| Developer docs | `mkdocs_src/docs/developer/frontend/state/app-state.md` |
| History (plan, steps 1–4b, the assets lot) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |
