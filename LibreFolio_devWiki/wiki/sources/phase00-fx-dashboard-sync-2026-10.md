---
title: "Phase 0 / 28 — FX in the Dashboard, page cache, data-quality banners, display currency, `db <path>`"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/
tags: [phase0, release2, fx, dashboard, cache, data-quality, cli, coverage, workstream-n]
related:
  - problems/fx-backward-fill-unbounded-stale-rates
  - concepts/stale-while-revalidate-page-cache
  - problems/db-path-argument-ignored-by-alembic
  - problems/coverage-combine-race-renamed-part
  - features/F-016
  - features/F-054
  - decisions/fx-sync-pair-based
---

# Source: Phase 0 / 28 — the N batches (2026-10-06 … 10-09)

## Summary

Seven plans of workstream N, archived on 2026-10-09 from `Phase_0/` to `phases/28_fxDashboardSync/`. They fix how
the Dashboard repairs missing FX rates, give every portfolio view a session cache that shows stale data while it
refreshes, make five pages open in the user's own currency, make `dev.py db <path>` really act on `<path>`, and fix
the coverage combine that lost whole parallel passes. Two plans are test-only. The open residuals went to backlog 38
as **N-1 … N-9**; N-9 (the backward-fill page) is [[problems/fx-backward-fill-unbounded-stale-rates]].

## Key takeaways

- **FX in the Dashboard** (`plan-phase00FxDashboardSync`, 2026-10-06, `5c1b52612` and follow-ups):
  - **D1** — an FX pair created with a real provider syncs its **whole history** (`start = 'min'` → today), so
    new pairs are born without holes (`frontend/src/lib/services/fxCreationSync.ts`).
  - **D2** — the rule belongs to the creation service; the add-pair modal lost `dateStart/dateEnd` and its five
    callers (the PAC planner among them) were aligned.
  - **D3** — the `MISSING_FX_RATES` banner syncs one range, first missing date − 7 to last + 7, capped at today
    (`frontend/src/lib/utils/sync/syncRange.ts`, the same helper as assets); weekends and holidays resolve from
    the week before.
  - **D4** — if the issue survives the sync, a warning toast says so; **D5** — an issue without dates syncs the
    whole history.
  - **D6** — the margin sync can create an island of rates whose following days are then filled silently from
    it; accepted, see [[problems/fx-backward-fill-unbounded-stale-rates]].
  - **D7** — the day change is shown as a percentage of **|base|** (card 1: yesterday's total P&L; card 2:
    yesterday's NAV), so its sign always follows the change, even on a negative base — "a loss that shrinks is a
    rise"; it is hidden only on a zero or unreadable base (`dayChangePct` in
    `frontend/src/lib/components/dashboard/KpiSection.svelte`, `f7134bb7f`).
- **Page cache** (`…Step2PageCache`, 2026-10-07, `cd1d42fb6`): stale-while-revalidate for the portfolio views —
  [[concepts/stale-while-revalidate-page-cache]]. Syncs count as writes only when they wrote; the live-price poll
  no longer refreshes every view. Fixed on the way: the Dashboard asked Performance before knowing the user's
  brokers.
- **Default display currency** (2026-10-08, `51d1a64db`): five pages (Dashboard, broker list and detail, the
  assets risk panel, the FX-detail AI Export) started from the **instance** default (`global_settings`, the currency
  given to new users). They now start from `defaultDisplayCurrency` — the user's `base_currency`, else the instance
  default, else EUR (`frontend/src/lib/stores/app/settings.ts`); a remembered or manual Dashboard choice still wins.
- **Data-quality banners, nav count** (2026-10-08, test-only): after #32 the seeded data carries a real
  `MISSING_COST_BASIS` issue with its own `navigate_asset` link, and an E2E that counted links page-wide found 3
  instead of 2. Gotcha kept: banner rows are keyed by `code + group_key` in `{#each}`; production Svelte does not
  check duplicate keys, so two issues with the same pair would silently collapse into one row.
- **`dev.py db <path>`** (2026-10-09, `964f3427d`): [[problems/db-path-argument-ignored-by-alembic]].
- **FX add-pair navigation wait** (2026-10-08, test-only): a full `page.goto` followed by a 3 s default `expect` was
  too short under load — a wrong test assumption, not a product bug; `goToFxPage` now takes query params
  (`frontend/e2e/fx/fx-helpers.ts`).
- **Coverage combine race** (2026-10-08): already filed as [[problems/coverage-combine-race-renamed-part]].

## Residuals (backlog 38)

N-1 stale-while-revalidate outside the portfolio (phase 2) · N-2 generic summary when only the coverage combine
fails · N-3 an unreadable coverage part turns later passes red · N-4 SIGTERM during coverage's own save (upstream
non-reentrant handler) · N-5 stale comments about discarding in-flight answers · N-6 false claims in the frontend
state docs · N-7 `cli_tools` wording (closed 2026-10-09) · N-8 `PORT` from `.env` inside the container · N-9 this
wiki's backward-fill page (written 2026-10-09).

## Wiki pages updated

- [[problems/fx-backward-fill-unbounded-stale-rates]] — new (N-9, D6's promised page).
- [[concepts/stale-while-revalidate-page-cache]] — new.
- [[problems/db-path-argument-ignored-by-alembic]] — new.
- [[features/F-016]] — creation syncs the full history (D1, D2).
- [[problems/coverage-combine-race-renamed-part]] — already filed 2026-10-08; unchanged.

## Source files

| Role | Path |
|------|------|
| Folder README (plan table, commits) | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/README.md` |
| FX in the Dashboard (D1-D7, §11) | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSync.prompt.md` |
| Page cache | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSyncStep2PageCache.prompt.md` |
| Default display currency | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DefaultDisplayCurrency.prompt.md` |
| Banners nav count | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DataQualityBannersNavCount.prompt.md` |
| `db <path>` | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00DbPathArgument.prompt.md` |
| Add-pair navigation wait | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxAddPairNavigationWait.prompt.md` |
| Coverage combine race | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00CoverageCombineRace.prompt.md` |
| Pair creation (full history) | `frontend/src/lib/services/fxCreationSync.ts` |
| Banner sync range | `frontend/src/lib/utils/sync/syncRange.ts` |
| `defaultDisplayCurrency` | `frontend/src/lib/stores/app/settings.ts` |
| Data-quality banner | `frontend/src/lib/components/ui/feedback/DataQualityBanner.svelte` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| E2E: data-quality banners | `frontend/e2e/portfolio/data-quality-banners.spec.ts` |
| E2E: default currency | `frontend/e2e/portfolio/default-currency.spec.ts` |
