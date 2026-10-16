---
title: "One native-cash ledger: foreign cash revalued every day, its exchange result a return and never capital"
category: decision
status: resolved
date: 2026-10-12
tags: [backend, frontend, portfolio-engine, financial-math, native-cash, fx, cash, k-r-w-pools, broker-pnl, dashboard, ai-export, lot-41]
related:
  - entities/native-cash
  - problems/foreign-cash-never-revalued
  - problems/dirty-days-ignore-fx-only-moves
  - concepts/3-pool-cash-model
  - entities/portfolio-engine
  - entities/portfolio-service
  - decisions/portfolio-pnl-series-contracts
  - decisions/broker-card-aggregation-no-n-plus-one
  - decisions/financial-math-one-home
  - decisions/financial-math-single-average-cost
  - decisions/ai-export-version-bump-once-per-release
  - problems/ai-export-reconciled-false-on-rounding-dust
  - features/F-054
  - features/F-055
  - sources/phase00-broker-pnl-flows-2026-10
---

# Decision: one native-cash ledger, foreign cash revalued every day

## Context

Lot 41 of Release 2 (workstream I) first made the per-broker P&L lines stop jumping at internal transfers (see
[[decisions/portfolio-pnl-series-contracts]], G1a). Its inventory then found two deeper problems in how cash was
counted:

- **B4 — foreign cash was never revalued.** The engine's cash ledger added each movement at the rate of its own date,
  so the exchange result on cash never entered NAV or P&L: not while the currency sat in the account, and not when it
  was spent on a BUY or converted back with an FX_CONVERSION. Cash *in transit*, instead, was valued at the day's
  rate. See [[problems/foreign-cash-never-revalued]].
- **Four loops recomputed the same cash with their own rules** (plan 41 §17.2): the engine's step 1 (G1), the cards
  of `get_summary` (G2), the income / cost / deposit histories of `_signed_transaction_sums_by_date` (G3) and the
  flows of `get_positions_contribution` (G4). The ownership-share rule was written four times (O2), every row was
  converted with its own `convert_bulk` call (X5), and a missing pair was lost in silence in the contributions (B14)
  while the summary reported it.

The developer asked for one function in the financial math layer: «Riguardo la funzione unica ne sono lieto, se serve
un posto dove metterla mettiamola nello stesso modulo dei calcoli matematici, vicino al wac centralizzato» (2026-10-11:
"I am glad about the single function; if it needs a home, put it in the same module as the math, next to the
centralized WAC").

## Options Considered

1. **Where an exchange result on cash goes in the K/R pools.**
   - *k1* — only rescale the pools to the revalued cash: part of an exchange gain would land in K, as if it were
     capital the user brought. Rejected.
   - *k2* — the result goes to the broker's returns pool R_b; a loss larger than R_b comes out of K_b through the
     existing clamp, as a FEE does. Chosen.
2. **A movement dated before the first available rate.**
   - *(a)* it stays out of the value and of the external cash flows, and is reported — what the engine already did.
     Chosen.
   - *(b)* count it from the first available rate, with its external flow at that rate. Rejected: it changes what an
     external cash flow means.
3. **How the Performance view shows the result (F-W).** The developer asked: «stiamo parlando di una riga nella
   tabella della pagina delle performance o di alterare le kpi in dashboard?» ("are we talking about a row in the
   Performance page's table, or about changing the Dashboard KPIs?").
   - *(i)* its own item, in the minimal form: one row of `other_effects`, no new schema and no KPI change. Chosen.
     The fuller version — a waterfall item with a new schema, `api sync` and a KpiSection change — was not pursued.
   - *(ii)* leave it inside «Other» with a note in the docs. Rejected.
4. **The row's name in AI Export (F-AI).**
   - *(a)* nothing new: the broker export already lists the row by name, the portfolio export keeps it inside
     `period_other_result`.
   - *(b)* a field in `portfolio.flows_income` listing the rows per broker, with a version bump.
   - **The developer's decision (2026-10-12, via the coordinator): (a) now, (b) after release 1.2 with a typed code.**
     Today an `OtherPeriodEffect` has no code, so the frontend and any filter can only match the English description.
     At `5d0585595` this is a decision, not yet a row of the post-1.2 backlog: section I still lists F-AI (b) as open,
     and the row enters with I's next checkpoint. *It entered with `8339b0a06` (plan 44, train 48): «F-AI (b) · «FX on
     cash» per nome nell'export del portafoglio», a typed code on `OtherPeriodEffect`, about ¾ day plus the probe.*

## Decision

### One ledger — `financial_math/native_cash.py`

One reconstruction of every broker's cash in the currencies it was recorded in ([[entities/native-cash]]).
`compute_native_cash()` converts everything in **one** `convert_bulk` call: each foreign movement at its own date (the
flows) and one unit of each foreign currency on every day from its first movement to `rates_until` (the valuation).
The value of a broker's cash on a day is its report-currency balance plus each foreign balance at that day's rate.
`effective_share()` is the only copy of the share rule: an owner counts its own share, any other role the whole
broker.

### The engine

- `PortfolioCalculationEngine.calculate()` builds the ledger in step 10c, from the classified movements up to
  `actual_to`, at the classifier's share, with `rates_until = actual_to`.
- `DailyStateBuilder(native_cash=...)` is a **required** argument (decision D-β), like `average_costs`.
- On every rate-change day of a held foreign currency (`NativeCash.rate_change_days()`), in the pre-frame and in the
  frame — where those days become dirty days — `_revalue_foreign_cash()` books, for each broker with foreign cash,
  `value_at(day)[b] − cash[b]` to the broker's cash **and to R_b**; if R_b turns negative, `K_b += R_b` and `R_b = 0`
  (k2). **The capital baseline never moves**: an exchange result is a result, not a contribution.
- The engine's five accumulators that no production code read (`per_realized`, `per_income`, `per_fees_taxes`,
  `unalloc_income`, `unalloc_fees`, backlog B13) were removed; their tests moved to the flows view with the same
  numbers.

### The service

- `get_summary()`: a card's cash is `value_at(valuation_date)[b]`, its `cash_balances` come from `balances()`, and the
  headline cash is the sum of the cards. Period totals come from `flows()`, missing pairs from
  `missing_conversions()`.
- The three histories keep their signature: `get_report()` passes them the run's ledger; called alone they build one
  with `rates_until = date_to or today` — which also stops them reading rows dated after today (B12, histories).
- `get_positions_contribution()` reads its income and cost flows from the same ledger (G4 and B14 closed).

### F-W — the «FX on cash» row

`NativeCash.exchange_results(date_from, date_to)` gives, for each broker with foreign cash, the change in value of its
foreign balances over the window, each at its day's rate, less the window's foreign movements converted at their own
dates. `get_positions_contribution()` adds one `OtherPeriodEffect("FX on cash", "Other", result, broker)` per broker,
in access order, and lowers the residual by the same figure. Below `CONVERSION_DUST` (1e-9) the row is skipped, and
with foreign cash in scope the residual is shown only at or above that size. The schema, the API and KpiSection did
not change; the frontend maps the description to `dashboard.fxOnCash` in `OtherPeriodEffectsTable.svelte` and
`PerformanceChart.svelte`.

### AI Export, F-AI (a)

No bump of `broker.flows_income_costs`: the builder and the payload shape did not change, only the values coming from
the engine (coordinator, 2026-10-12; [[decisions/ai-export-version-bump-once-per-release]]).

## Consequences

- **The guard.** For a portfolio whose cash is all in the report currency, every output stays byte-identical: a
  golden JSON (`eur_only_golden.json`, 14 397 lines) generated **before** the code (step F-0) and never regenerated
  covers the report, the summary with its cards, the eight series getters and `calculate()`.
- **On the mock database** (F-4, 76 reports, before = the target without F): 18 identical — every scope with no
  foreign cash — and 58 changed, all on brokers that hold foreign cash. The gap between the headline cash and the sum
  of the cards fell from up to **866.5** to at most 2.9e-22. For the admin user, all brokers, one year, the period P&L
  fell by 472.16, exactly the sum of the five «FX on cash» rows.
- **Timings**: the 76 cold reports took 9.55 s instead of 10.30 s (0.927×). The native-cash reconstruction costs a
  median 4.4 ms, 2.7 % of a report, and nothing on scopes with cash in the report currency only.
- **AI Export**: 31 of 33 snapshots changed in value, and the row appears by name in the effects of 21 broker
  snapshots. The same comparison found `reconciled` flipping on a 1e-24 residual, which became C-53
  ([[problems/ai-export-reconciled-false-on-rounding-dust]]).
- **Left in the residual, by design** (backlog section I): the exchange result on cash *in transit* (B17), the spread
  of an FX_CONVERSION on the same broker (B18), and the order of the unallocated rows (B19, order only). The
  securities half of B11 stayed open here; J closed it in CP-6 (2026-10-16), with one `change_days` shared by the
  native cash and the engine: [[problems/dirty-days-ignore-fx-only-moves]].
- **Confirmed on real data** (developer, 2026-10-12, via the coordinator): after importing his Scalable Capital
  reports on his own server, the per-broker P&L chart looked «come me lo aspettavo» ("as I expected").

## Links

- [[entities/native-cash]] — the module, its contract and its callers
- [[problems/foreign-cash-never-revalued]] — B4, the defect this closes
- [[problems/dirty-days-ignore-fx-only-moves]] — B11, half closed here
- [[concepts/3-pool-cash-model]] — the K/R rule for an exchange result
- [[decisions/portfolio-pnl-series-contracts]] — the broker lines whose drift this closes
- [[decisions/financial-math-one-home]] — the layer the module lives in
- Source: [[sources/phase00-broker-pnl-flows-2026-10]]

## Source files

| Role | Path |
|------|------|
| The ledger, `exchange_results`, `CONVERSION_DUST`, `effective_share` | `backend/app/services/financial_math/native_cash.py` |
| Step 10c: the ledger built for the run | `backend/app/services/financial_math/portfolio/engine.py` |
| `_revalue_foreign_cash`, rate-change days in pre-frame and frame | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Cards, histories, contributions, the «FX on cash» row | `backend/app/services/portfolio_service.py` |
| Row mapping (table, waterfall) | `frontend/src/lib/features/dashboard/OtherPeriodEffectsTable.svelte`, `frontend/src/lib/features/dashboard/PerformanceChart.svelte` |
| Module tests | `backend/test_scripts/test_services/test_financial_math/test_native_cash.py` |
| Engine scenarios (B1–B12, B3w, B4v) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Report-currency guard and its golden | `backend/test_scripts/test_services/test_financial/test_native_cash_guard.py`, `backend/test_scripts/fixtures/native_cash_guard/eur_only_golden.json` |
| Service tests (policy (a), B12, B14, «FX on cash») | `backend/test_scripts/test_services/test_financial/test_portfolio_service_native_cash.py` |
| Theory — exchange result on foreign cash (§6) | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/index.en.md` |
| Theory — «FX on cash» in the period P&L | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.en.md` |
| Theory — example D, dollars held while the rate moves | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md` |
| Developer docs — the native-cash function | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Plan (§0, §15 F-0…F-C3, §17) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |
