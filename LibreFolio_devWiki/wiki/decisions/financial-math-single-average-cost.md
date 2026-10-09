---
title: "One average-cost function in a financial_math layer: historical cost in the report currency, never a silent zero"
category: decision
status: resolved
date: 2026-10-07
tags: [backend, architecture, financial-math, wac, average-cost, cost-basis, fx, data-quality, portfolio-engine, issue-32]
related:
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - concepts/inline-wac-computation
  - entities/portfolio-engine
  - entities/portfolio-service
  - entities/lots-analysis-service
  - features/F-097
  - decisions/wac-target-currency-last-acquisition
  - decisions/cost-basis-currency-object
  - concepts/absence-sentinel-vs-nullable-type
  - concepts/3-pool-cash-model
  - concepts/holdings-performance-panel
  - problems/test-transaction-implied-constructor-mismatch
---

# Decision: one average-cost function, in a new `financial_math` layer

> Release 2, workstream **P** — issue [#32](https://github.com/Librefolio/LibreFolio/issues/32). Decided by the
> developer on 2026-10-07, after the read-only analysis relayed by the coordinator; implemented the same day on
> branch `e-alfy-p-costo-medio-unico-32`. The bug itself is filed as
> [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]].

## Context

Issue #32: an asset quoted in USD, bought three times paying EUR (400 € in total), showed a purchase cost of **0** on a
Dashboard in EUR and the correct cost on a Dashboard in USD. The analysis found that #32 was one symptom of a larger
shape: **four** average-cost implementations, each with its own currency model and its own way of hiding a gap.

| # | Implementation | Currency model | When a rate or a cost was missing |
|---|---|---|---|
| 1 | Portfolio engine pools (`_buy_unit_cost`, `_compute_open_cost_basis_inline`, `_capital_flow_for_adjustment_in`, `_apply_split_rescale` in `portfolio_engine.py`) | Pool in the asset currency A. The paid amount (currency P) was converted into A with rates read from the preloaded `fx_rate_map` — r(P→T) when A = T, otherwise the cross rate r(P→T)/r(A→T); the open cost was re-converted into T every day at that day's rate | Quantity added at the current average cost (0 for an empty pool), no trace in `missing_fx`; reductions and position state used the A amount **as if it were in T** |
| 2 | `compute_wac_iterative()` + `compute_wac_from_txlist()` (`backend/app/utils/financial/wac_utils.py`) | Currency of the last acquisition (or an override); each acquisition converted at its own date | Fail-safe: `wac=None` with the missing pairs and dates. An unknown cost counted as zero; the `add_at_wac` / `is_pending` branches were unreachable in production |
| 3 | Lots analysis WAC rows (`_build_wac_row` in `lots_analysis_service.py`) | Report currency, at each acquisition's date | The unconverted cost |
| 4 | Broker summary (`TransactionService.get_cost_basis()` behind `GET /brokers/{id}/summary`) | None: the BUY amounts summed as they were, in mixed currencies, ignoring sales and transfers | Nothing to miss — no conversion was attempted |

The service layer added silent paths of its own: realized P&L skipped a sale, or used its unconverted proceeds, when a
rate was missing, and discarded the missing pairs. The implementations also disagreed on an acquisition with no known
cost (a TRANSFER/ADJUSTMENT-in without `cost_basis_override`): the engine entered it at the current average cost,
`wac_utils` at zero.

## Options Considered

1. **Patch `_buy_unit_cost` with an identity rate** (P = T ⇒ rate 1, or preload the `(T, T, d)` key) — closes the
   exact #32 symptom. Rejected: the same-root twins (a cost basis in T, or in a third currency), the other silent
   fallbacks and the four diverging implementations would all remain. The developer's direction was "no patches".
2. **Keep the pool in A and revalue it every day** (the engine's model) — rejected: the purchase cost of a foreign
   position floats with today's rate, the exchange-rate effect falls into the period's reconciliation residual
   ("Other", see [[concepts/holdings-performance-panel]]), and the engine contradicts the figures that were already
   historical in T: FIFO lots (`original_cost` at the lot's opening date), the PAC planner, the lots WAC line.
3. **Cross rates r(P→T)/r(A→T) read from a preloaded map**, or a direct P→A rate — rejected: the cost depends on keys
   that another method happens to load, which is the #32 mechanism itself; dividing by a rounded rate, or taking P/A
   from a different source, leaves a spurious exchange effect on the purchase day; a direct P→A rate needs a P/A pair
   that may not be configured.
4. **One generic function in a new service layer** — chosen: historical cost in T at each acquisition's own date,
   cost in A kept alongside, every gap reported.

**Placement.** The analysis proposed a single module, `backend/app/services/average_cost.py`. The developer asked for a
service layer for financial calculations instead, starting with this function, with the others to be factored in
later or created there directly; the coordinator named it `financial_math`. It is not in `backend/app/utils/financial/`
because those helpers are pure, while this function calls the FX service itself.

## Decision

### The layer — `backend/app/services/financial_math/`

The package docstring (`__init__.py`) states the rule:

- **A calculation owns its whole problem.** It takes the plain data of the problem — movements, currencies, dates —
  and calls the services it needs (the FX service for conversions, for example) instead of receiving values prepared
  by its caller.
- **Callers depend on the layer, not the reverse.** Engines, services and API handlers call it; it does not depend on
  them.
- **New financial calculations are born here.** The existing pure helpers in `backend/app/utils/financial/`
  (`roi_utils.py`, `valuation_utils.py`) move into the layer later, in a separate refactor — not as part of the work
  that created it.

The first rule is the structural answer to #32: the engine's cost depended on `fx_rate_map` keys loaded by
`_preload_fx_rates`, a different method written for a different purpose, so the missing identity key was invisible
from the place that needed it.

### The function — `compute_average_costs()`

`compute_average_costs(session, positions, *, report_currency, asset_leg=True) -> dict[key, AverageCost]`, in
`financial_math/average_cost.py`, is the only public function that converts. T is the report currency, A a position's
asset currency, P the currency actually paid, d the acquisition's date.

- **Input:** `CostPosition(key, asset_currency, movements)` of `CostMovement(movement_id, transaction_type, date, kind,
  quantity, cost_amount=None, cost_currency=None)`, with `kind` = `ACQUISITION | REDUCTION | SPLIT`.
  `cost_amount=None` means an **unknown** cost, `0` a **zero** cost — two different states, never folded into one.
- **Adapter:** `cost_movement_from_transaction()` is the single transaction→movement rule — a BUY costs the cash paid;
  another acquisition costs `cost_basis_override × quantity` in `cost_basis_currency`, or nothing known; a negative
  quantity is a reduction; a split-linked ADJUSTMENT is a split. `determine_target_currency()` moved here; only the
  facade uses it.
- **Historical cost in T:** `c_T = paid × r(P→T, d)`. An amount already in T is taken as it is — **P = T never needs a
  rate** — so the #32 case gives exactly 400 €.
- **Double sum C_T / C_A:** `c_A` is the amount paid when P = A, `c_T` when A = T, otherwise `c_T × r(T→A, d)` with the
  same day's rate, so a position's exchange-rate effect is exactly 0 on its purchase day.
- **One batched `convert_bulk(..., raise_on_error=False)` per call**, for every position; none at all when nothing
  needs converting.
- **Pool rules:** same-day additions before reductions; a reduction removes `C × q / Q` on both legs and the **whole**
  C when it empties the pool (exact conservation of cost); oversold quantity is clamped and listed in
  `oversold_movement_ids`; a split keeps the cost; an emptied pool restarts at zero and complete.
- **Output** `AverageCost`: `quantity`, `cost_report` (C_T), `cost_asset` (C_A), `steps` — one `CostStep` per movement
  with its effect (`add | add_zero_cost | add_unknown_cost | add_missing_fx | reduce | split_rescale`), quantity and
  costs after it, the changes, completeness on each leg and the conversion's provenance — plus `missing`,
  `unknown_cost_movement_ids`, `oversold_movement_ids` and `state_at(day)` (a bisect over the steps).
- **Arithmetic (D5):** exact sums of converted amounts, WAC = C/Q, instead of the old iterative formula. Measured on
  2 × 2 000 random sequences against the exact rational result: the two arithmetics differ only beyond the ~21st
  significant digit (realistic data: largest relative difference 1.3e-22 on the final WAC), the new one closer to the
  exact value in 569 cases against 163 (1 228 ties); the PAC suite passed with its expected values unchanged.

### Never a silent zero

- **Missing rate:** the quantity is added, the cost is not, the pool is marked incomplete and the pair is reported as
  `MissingConversion(pair "FROM/TO", dates, leg report|asset)`. It always surfaces: engine `missing_fx` →
  `summary.missing_fx_pairs` → the yellow Dashboard banner; `data_quality.missing_fx_pairs` in the lots analysis;
  `BRSummary.missing_fx_pairs` in the broker summary; `wac=None` + `wac_missing_pairs` from the facade.
- **Unknown cost:** counted at zero cost and flagged with the new `IssueCode.MISSING_COST_BASIS` (warning), on the
  Dashboard and in the lots analysis. The engine used to enter such units silently at the current average cost. The
  batch validation (`COST_BASIS_REQUIRED`) already rejects a TRANSFER/ADJUSTMENT-in without a cost basis, so the
  warning catches rows that did not go through it; the developer wanted it on the banner anyway — if the function
  cannot return a cost, that information must reach the banner.
- **Per-position figures** (a WAC, an unrealized P&L, a point of a lots WAC line, a broker holding's `total_cost`) are
  withheld (`None`) while the pool is incomplete; aggregates such as the open cost basis keep the known part.
- **Not covered by this rule (decided 2026-10-09):** an incoming row saved in **Auto** on an *empty* pool gets a cost
  of 0 computed by the facade and written as such — a known value, not an unknown one, so no `MISSING_COST_BASIS`.
  The developer kept it as the correct fallback; the user corrects that transaction if needed —
  [[decisions/auto-cost-basis-zero-without-position]].

### Who calls it

| Caller | Report currency T | `asset_leg` |
|---|---|---|
| `PortfolioCalculationEngine.calculate()` — once per run, all positions (`build_cost_positions()`), after the FX preload; the result goes into `DailyStateBuilder(average_costs=...)`, a required parameter | The report's target currency | `True` |
| `compute_wac_iterative()` — a facade with the same signature, queries, cache and `WACPreviewResultItem` — behind the transaction preview / automatic cost basis, `POST /portfolio/wac` and the PAC planner | The override (the PAC passes T), or the last acquisition's currency ([[decisions/wac-target-currency-last-acquisition]]) | `False` |
| `LotsAnalysisService` WAC lines — one position per broker plus `"__all__"` | The analysis target currency | `False` |
| `BrokerService._holding_average_costs()` — `GET /brokers/{id}/summary` | The asset currency, one call per currency group | `False` |

FIFO stays only where lots are the subject: the lots analysis still creates its lots with the FIFO engine. Every
average cost comes from this one function.

## Consequences

### Behaviour changes worth remembering

- **#32 fixed:** the issue's asset costs exactly 400 € on an EUR Dashboard; the USD Dashboard is unchanged. Opening
  positions and transfers whose cost basis is in T now cost what that cost basis says, and a priced opening
  ADJUSTMENT's in-kind capital now enters deposited capital, so total P&L is no longer inflated by its value.
- **Historical cost:** the purchase cost of a foreign position no longer floats with today's rate. Realized P&L
  compares proceeds converted at the sale date with the historical cost in T; the Yield on Cost denominator is the
  historical WAC in T.
- **Unrealized change includes the exchange-rate effect** — before, it fell into the reconciliation residual. The
  Dashboard explains it (D11): asset effect = MV_T − C_A·r(t), fx effect = C_A·r(t) − C_T, exact sum = MV_T − C_T; for
  A = T everything is asset effect and there is no T→T row. `PortfolioSummary.period_unrealized_breakdown` holds
  `UnrealizedBreakdownRow(kind asset|fx|unsplit, asset_currency, period_delta)`, deltas between the same boundary
  states as `period_unrealized_gain_loss_delta`, shown in the tooltip of the first bar ("Unrealized change") of the
  first Dashboard KPI card.
- **An oversell realizes the whole pool cost**, no longer WAC × the quantity sold. Observed in an engine test that
  sells 15 units out of 10 (the test does not assert it): realized moved from 0 to 500 and the K/R split from 1500/0
  to 1000/500 (see [[concepts/3-pool-cash-model]]).
- **Unknown-cost transfers and adjustments are flagged** (`MISSING_COST_BASIS`) and count at zero cost.
- **In-transit assets with a frozen cost** are converted once, at the arrival date, as the destination pool books
  them — not every day of the transit.
- **Broker summary:** `total_cost` / `average_cost_per_unit` are the historical cost in the asset currency from
  purchases, sales and transfers, `Optional` (`None` when incomplete), with `BRSummary.missing_fx_pairs`.
- **AI Export:** `portfolio.provenance` and `broker.provenance` moved to component version 2 (schema 1 unchanged) with
  a new `valuation_semantics` text — historical WAC in T; FIFO lot `original_cost` converted at the lot's opening
  date; market value at the valuation date's rate, so unrealized P&L includes the exchange-rate effect. The frontend
  renderer (`snapshotDataRenderer.ts`, `COMPACT_COMPONENT_VERSIONS`) renders both compactly at v1 and v2.
- **A fixture the old code had been hiding:** an AI Export integration fixture inserted a SELL with a positive
  quantity, bypassing the API sign rule. It passed only because the old WAC silently added those units at zero cost;
  it now sells `-4`.

### Performance

- Engine: two batched `convert_bulk` calls (FX preload + costs); no cost is converted in the daily loop.
- `get_summary()` / `get_positions_contribution()`: no WAC query per sale or per position — realized P&L comes from
  the engine's `realized_sales`, period-boundary costs from `state_at`.
- Lots WAC lines: one timeline sampled by bisect, O(D log N) instead of O(D×N).

### Removed

`backend/app/utils/financial/wac_utils.py` (`WACInputTX`, `WACCalcResult`, `compute_wac_from_txlist`, the dead
`add_at_wac` / `is_pending` branches) with its test file `test_financial_utils.py` (runner selector
`services financial-utils` → `services financial-math`); the four engine helpers listed above; the lots
`_build_wac_context` / `_build_wac_row` / `_compute_wac_series`; `TransactionService.get_cost_basis()`.

### Known limits (outside P's scope)

- The **FIFO lot** conversions in `lots_analysis_service.py` still fall back to the unconverted amount when a rate is
  missing — e.g. `fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date) or lot.original_cost` in
  `_build_value_history` and `_build_return_history`.
- `oversold_movement_ids` is computed, but no caller surfaces it yet.
- `roi_utils.py` and `valuation_utils.py` still live in `backend/app/utils/financial/` until the separate migration
  into the layer.

## Links

- [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]] — the bug, its twins and the regression tests
- [[concepts/inline-wac-computation]] — the engine's previous single-pass pools, now replaced by a precomputed timeline
- [[entities/portfolio-engine]], [[entities/portfolio-service]], [[entities/lots-analysis-service]] — the migrated consumers
- [[features/F-097]] — the WAC feature
- [[decisions/wac-target-currency-last-acquisition]] — still the target-currency rule of the facade's callers
- [[concepts/absence-sentinel-vs-nullable-type]] — "unknown", "zero" and "rate missing" are three states, not one `None`
- [[problems/test-transaction-implied-constructor-mismatch]] — the required `average_costs` parameter met the same
  per-file test constructions again

## Source files

| Role | Path |
|------|------|
| Layer rule (package docstring) | `backend/app/services/financial_math/__init__.py` |
| The function, adapter and target-currency helper | `backend/app/services/financial_math/average_cost.py` |
| Engine consumer (`build_cost_positions`, `DailyStateBuilder`, `RealizedSale`, `UnrealizedSplit`) | `backend/app/services/portfolio_engine.py` |
| WAC facade, realized P&L, boundary costs, breakdown rows | `backend/app/services/portfolio_service.py` |
| Lots WAC lines and gaps | `backend/app/services/lots_analysis_service.py` |
| Broker summary holdings cost | `backend/app/services/broker_service.py` |
| FX service (`convert_bulk`) | `backend/app/services/fx.py` |
| `MISSING_COST_BASIS`, `UnrealizedBreakdownRow` | `backend/app/schemas/portfolio.py` |
| `BRAssetHolding.total_cost`, `BRSummary.missing_fx_pairs` | `backend/app/schemas/brokers.py` |
| Facade output (`WACPreviewResultItem`, `WACQualifyingTX`) | `backend/app/schemas/wac.py` |
| PAC planner (passes T as override) | `backend/app/services/portfolio_allocation_source.py` |
| `POST /portfolio/wac` | `backend/app/api/v1/portfolio_api.py` |
| Batch auto cost basis | `backend/app/services/transaction_service.py` |
| Dashboard tooltip | `frontend/src/lib/components/dashboard/KpiSection.svelte` |
| AI Export provenance v2 | `backend/app/services/ai_export/components/portfolio_financial.py` |
| AI Export provenance v2 (broker) | `backend/app/services/ai_export/components/broker_financial.py` |
| AI Export component catalogue (both provenances declared `version=2`) | `backend/app/services/ai_export/components/catalog.py` |
| AI Export renderer | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Unit tests of the function | `backend/test_scripts/test_services/test_financial_math/test_average_cost.py` |
| Engine / service / lots tests (#32, breakdown) | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Shared test helper for `average_costs` | `backend/test_scripts/test_services/_engine_average_costs.py` |
| API regression (`TestIssue32PurchaseCostInReportCurrency`) | `backend/test_scripts/test_api/test_portfolio_api.py` |
| Developer docs (layer rule, function, callers) | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Theory | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/weighted-average-cost.en.md` |
| Theory — unrealized split by currency | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.en.md` |
| Plan (decisions D1–D12, measurements) | `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00WacUnification.prompt.md` |
