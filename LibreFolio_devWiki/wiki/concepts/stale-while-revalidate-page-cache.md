---
title: "Stale-while-revalidate page cache: a write marks answers stale, it never deletes them"
category: concept
tags: [frontend, stores, cache, portfolio, risk, ux, svelte5, stale-while-revalidate]
related: [concepts/portfolio-report-unified, concepts/entity-store-pattern, concepts/timeseries-store-pattern, concepts/discard-the-answer-not-the-question, concepts/prices-current-side-effect, sources/phase00-fx-dashboard-sync-2026-10]
---

# Concept: stale-while-revalidate page cache

## Definition

Since 2026-10-07 (plan *FxDashboardSync Step 2 — PageCache*, decision **E1**) every portfolio view keeps its answers
for the session and follows one rule: **invalidation marks data stale, it does not delete it**. A page shows what it
already has at once, asks again in background, and moves to the fresh figures when they land — the KPIs animate the
correction instead of counting up from zero. There is no time-based TTL: only a write, or the user's «Refresh»,
makes an answer stale.

The developer's words of 2026-10-06 set the scope wider than what shipped: *"also for assets and FX, files,
everything"*. Phase 1 covers the portfolio views; phase 2 (assets, FX, files, transactions, which still clear their
data and show a spinner) is backlog item **N-1**.

## How it is built

| Piece | Rule |
|---|---|
| `portfolioStore` | `invalidate()` bumps a mark and keeps the cache; `peekReport()` hands the old report with `stale: true` while `fetchReport` asks again |
| `riskStore` | `markRiskStale()` marks query and eligibility answers stale and keeps them; the risk catalogs are not marked |
| `lotsAnalysisStore` | new: the lots analysis is cached per key like the report |
| `dashboardViewStore` | the Dashboard's currency and broker filter are kept per session |
| `portfolioMutation` | the signal bus: a successful response is a *write* only when it changed something — a sync counts only if `points_changed`/`events_changed` > 0, so an empty sync and the live-price poll no longer refresh every view (an empty delta is the expected answer after `/prices/current`, [[problems/prices-current-sync-chain-empty-delta]]); `/prices/current` stays a write ([[concepts/prices-current-side-effect]]) but its effect is now "mark stale", not "throw away" |
| «Refresh» (`requestPortfolioRefresh`) | forces report, risk and lots |
| Session change | `resetPortfolioCache()` forgets everything, in-flight requests included — another account's data is never shown |

## Why

A page that wipes its data on every write blinks, loses the user's place, and makes every background sync look like
a reload. Keeping the old answer is safe because the stale flag is explicit, and the newer answer always replaces it
— the counterpart of [[concepts/discard-the-answer-not-the-question]]: a stale answer may be *shown*, a superseded
request's answer is never *applied*.

A defect fixed on the way (F2): the Dashboard asked Performance before it knew which brokers the user owns, so it
briefly showed brokers the user does not own. The view now waits for its scope.

## Where it does not apply yet

The rule is written for the portfolio stores (`mkdocs_src/docs/developer/frontend/state/domain-state.md`, "Portfolio
Page Cache") but not in the frontend instructions, and the broker contribution in Broker detail does not follow it.
`TimeSeriesStore.invalidateAll()` and `entityStore` still clear (N-1).

## Source files

| Role | Path |
|------|------|
| Report cache, `invalidate`, `peekReport`, `resetPortfolioCache` | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` |
| Mutation bus, "a write only when it wrote" | `frontend/src/lib/stores/portfolio/portfolioMutation.ts` |
| Lots analysis cache | `frontend/src/lib/stores/portfolio/lotsAnalysisStore.svelte.ts` |
| Dashboard currency/broker per session | `frontend/src/lib/stores/portfolio/dashboardViewStore.ts` |
| Risk answers, `markRiskStale` | `frontend/src/lib/stores/risk/riskStore.svelte.ts` |
| Still clearing (phase 2, N-1) | `frontend/src/lib/stores/core/TimeSeriesStore.ts` |
| Developer doc (the rule) | `mkdocs_src/docs/developer/frontend/state/domain-state.md` |
| Plan (E1, §3.1-ter/quater) | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSyncStep2PageCache.prompt.md` |
