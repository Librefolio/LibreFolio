---
title: "Data-quality warnings proved end to end on real data: a missing cost three ways, and «Sync rates» offline with MOCKFX"
category: decision
status: resolved
date: 2026-10-12
tags: [testing, e2e, playwright, data-quality, dashboard, fx, mockfx, cost-basis, lots, test-isolation, workstream-v]
related:
  - problems/open-panels-stale-after-fx-sync
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - decisions/financial-math-single-average-cost
  - decisions/auto-cost-basis-zero-without-position
  - features/F-054
  - sources/phase00-data-quality-e2e-2026-10
---

# Decision: data-quality warnings proved on real data

## Context

Items 21–23 of the developer's server checklist ask that three data-quality situations be visible in the app:

- **21** — a configured pair with a real provider and no rates: `MISSING_FX_RATES` in the Dashboard banner, a
  «Sincronizza tassi» (Sync rates) button that fixes it, and figures instead of «—» afterwards;
- **22** — an acquisition with no known cost: `MISSING_COST_BASIS`, «—» in the positions and a warning in the lots
  panel;
- **23** — the unrealized breakdown tooltip that splits an asset's move from the exchange-rate move.

Workstream V (plan 46) found every one of them covered only by fakes — reports served by the test
(`serveMissingFxRates`, `injectDashboardIssues`), a held sync, Vitest fixtures — and some not at all: «—» was never
tested, `MISSING_COST_BASIS` never reached a page, an incoming TRANSFER without cost was never tested, and no test
had run a real sync up to the banner. The seed cannot produce `MISSING_COST_BASIS` either: the populate fails when a
TRANSFER or ADJUSTMENT has no cost.

Item 22 had a further obstacle: **the app refuses an incoming TRANSFER or ADJUSTMENT without a cost everywhere**,
promotes included. The only path through the app is backlog P-10 — an Auto ADJUSTMENT linked to a SPLIT is saved
without a cost, and becomes an acquisition of unknown cost when the event is reclassified as a PRICE_ADJUSTMENT.
Everything else is legacy data.

## Options Considered (D1, item 22)

1. **(a)** through P-10 only, with real APIs — depends on a path that a decision on P-10 may close;
2. **(b)** legacy rows only, written into the test database;
3. **(c) both** — chosen by the developer: «(c) Entrambe» ("both"). E2 goes through P-10 with real APIs, a separate
   spec writes «legacy» rows into the lane's database through a Python helper, and the backend test B1 stays.

## Decision

### The four tests, real data only

Each test registers its own disposable account, which owns the whole Dashboard, creates its data through the API and
cleans up in `finally`; it waits on `data-busy`, events or a witness from the same response, never on the clock; it
asserts on test ids, codes, ISO dates, names it created and «—», never on translated text; it runs in parallel.

| Test | Item | What it proves |
|---|---|---|
| B1 (`test_portfolio_cost_currency.py`, S7 and L4) | 22 | a TRANSFER in without cost gives `MISSING_COST_BASIS`; the receiving holding has no WAC and no P&L; the lots analysis is `DEGRADED` |
| E1 (`data-quality-real.spec.ts`) | 21 | the real banner, the real sync, the stored rate (1 234.5 MKD on d1 = 1 000 EUR), the healed report and cells — and the open lots panel refreshing by itself |
| E2 (same spec) | 22 | `MISSING_COST_BASIS` through P-10, with the asset link, «—» on the Dashboard and the broker page, the lots warning; an explicit cost 0 clears it |
| E3 (same spec) | 23 | the breakdown rows (asset EUR, asset KZT, FX KZT) in the tooltip, in order, with no `unsplit` row |
| E4 (`data-quality-legacy.spec.ts`) | 22 | legacy rows — a TRANSFER pair and an ADJUSTMENT without cost — give one `MISSING_COST_BASIS` for both assets, «—» where the cost is unknown and figures where it is known |

### «Sync rates» without a network: MOCKFX

The sync must be real, yet run offline. **MOCKFX** is the provider: registered but hidden from the public list,
accepted by `POST /fx/providers/routes`, and the real `sync_pairs_bulk` writes 1.2345 for every day and currency. It
counts as a real provider, so the banner offers `sync_fx_pair`; the scheduler is off in tests, so nothing syncs by
itself. Rejected: MANUAL (it gives `navigate_fx`, and the sync answers `skipped`) and writing the rate directly (it
skips the button). Each project gets its own reserved currencies — E1 MKD (desktop) and RSD (mobile), E3 KZT and UAH
— never used elsewhere, sorted after EUR so the stored rate is exactly 1.2345, cleaned before and after.

### The legacy rows: `legacy_cost_rows.py`, for the test database only

`backend/test_scripts/test_db/legacy_cost_rows.py` writes rows as an older version would have left them, without
`cost_basis_override`. It is guarded against touching anything else: `setup_test_database()` runs before any other
import and `verify_test_database()` must confirm the lane's test database; a database that does not exist is refused
(exit 2) rather than created empty; the brokers must be distinct and owned by the given user, and the assets must
exist (exit 3). It writes in one transaction, marks its rows in the description, and prints their ids as JSON. The
spec launches it with `execSync`, inheriting the runner's lane variables; it has no `test_` prefix, so pytest does
not collect it.

### D2 and the other decisions

- **D2** (developer): «Sì, procedi; e il pannello lotti si aggiorna da solo dopo il sync: V scrive il test rosso e la
  cura nello stesso lotto» ("yes; and the lots panel refreshes by itself after the sync: V writes the red test and
  the fix in the same lot") — [[problems/open-panels-stale-after-fx-sync]].
- **D3** (coordinator): `data-column-id` on DataTable's data cells, so a test finds a column without CSS classes.
- **D4** (coordinator): E2 also checks the broker page, and that an explicit cost clears the warning; no MOCKFX_FAIL
  case.

## Consequences

- **Results**: B1 11/11; E1–E3 and E4 green with 1 and with 4 workers, E1's D2 step red before the fix and green
  after; `front-portfolio all` with 4 workers 155/156, the one red pre-existing and outside the lot (V-7, a shared
  `TEST_USER` broker deleted by a neighbour spec), green alone 6/6.
- **Two observations, recorded, not changed**: a TRANSFER pair without cost moves the sender's FIFO lot with its cost
  and reports nothing, while the average cost treats the arrival as unknown — which is what feeds the banner and «—»,
  consistent with "a transfer carries its cost in `cost_basis_override`"; an orphan TRANSFER makes the lots analysis
  `FAILED` (`TRANSFER_PAIR_MISSING`), while the Dashboard counts it as in-kind capital (V-3). *Decided on 13/10*: an orphan TRANSFER
  becomes a plain ADJUSTMENT — [[decisions/orphan-transfer-becomes-an-adjustment]] (after 1.2).
- **Left after 1.2** (backlog section V): V-1 the same refresh gap after «Sync prices»; V-2 the lots panel publishes no
  `data-busy`; V-3 the orphan TRANSFER; V-4 E2 must be rebuilt if P-10 is closed; V-5 an outdated comment about the
  seed; V-6 the developer doc lists only part of the banner tests; V-7 the neighbour-spec red above.
  *Update (trains 58 and 64 in the wiki, 2026-10-12)*: V-1, V-5, V-6 and V-7 were closed by V's batch 2 (train 58: `a0722f755`, `4e710a1f9`,
  `6f5a3bcff` — V-7's spec now runs on a disposable account that owns two brokers), V-9 and V-10 by work 3 (`973ca3961`,
  `8994100b4`); the isolation audit that followed is [[problems/e2e-writes-leaked-into-shared-state]].

## Links

- [[problems/open-panels-stale-after-fx-sync]] — D2, the fix found by E1
- [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]] and [[decisions/financial-math-single-average-cost]]
  — where `MISSING_COST_BASIS` comes from
- [[decisions/auto-cost-basis-zero-without-position]] — the Auto rule P-10 runs into
- [[features/F-054]] — the Dashboard and its banner
- Source: [[sources/phase00-data-quality-e2e-2026-10]]

## Source files

| Role | Path |
|------|------|
| E1–E3, real data | `frontend/e2e/portfolio/data-quality-real.spec.ts` |
| E4, legacy rows | `frontend/e2e/portfolio/data-quality-legacy.spec.ts` |
| Legacy-row helper (test database only) | `backend/test_scripts/test_db/legacy_cost_rows.py` |
| B1 (S7) and L4 | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| MOCKFX provider | `backend/app/services/fx_providers/mockfx/plugin.py` |
| Runner actions `data-quality-real`, `data-quality-legacy` | `scripts/test_runner/_frontend_portfolio.py` |
| `data-column-id` (D3) | `frontend/src/lib/components/table/DataTable.svelte` |
| `kpi-unrealized-delta` test id | `frontend/src/lib/features/dashboard/KpiSection.svelte` |
| Developer doc (how to trigger each warning, the tests) | `mkdocs_src/docs/developer/frontend/data-quality-banner.md` |
| Plan 46 | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
