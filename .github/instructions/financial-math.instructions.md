---
applyTo: "backend/app/services/financial_math/**"
---

# Financial Math Layer (backend)

`backend/app/services/financial_math/` is the one home of LibreFolio's financial calculations (developer decision,
2026-10-11; `.github/copilot-instructions.md`, decision 10). This file holds the rules of the layer. The map of what
lives where, inside and outside the layer, is in `backend.instructions.md`, section «Financial Math — One Home».

## Modules

| Module | Calculation |
|---|---|
| `average_cost.py` | average purchase cost (WAC): pools, cost-basis steps, conversions, the conversions that could not be made, the unit cost of each movement (`movement_unit_costs`) |
| `native_cash.py` | cash per broker and currency: balances, value in the report currency on any day, period flows, FX results |
| `ledger_totals.py` | control totals of the transaction ledger, with no price, rate or cost: cash per broker and currency, quantity per broker and asset (`compute_control_totals`, what a backup writes and a restore checks) |
| `returns.py` | simple ROI, TWRR and MWRR, as point values and daily series; the Dashboard's MWRR rule, one for the card and every point of the line (`period_mwrr`, `period_mwrr_series`); cumulative and annualized returns; a period's start (`rebase_to_period`); net holding return; gain or loss as a fraction of its base (`gain_loss_ratio`), of a group of holdings (`group_gain_loss`); a change as a fraction of the size of its base (`change_ratio`); the timing effect, MWRR − TWRR (`timing_effect`); the gain or loss a disposal realizes (`realized_gain`); the return between two prices (`price_return`), as a float for the return series of risk and signals (`float_price_return`); the observed annualization factor of a return series, observations × 365 / days (`observed_annualization`); the change of a price or rate over the fixed periods of the Assets and FX tables, 1D … 5Y, in both orientations (`FIXED_PERIODS`, `fixed_period_dates`, `fixed_period_changes`); the gain that takes a value back to its peak after a drawdown (`required_recovery_return`) |
| `valuation.py` | value of a holding from quantity, price and `quote_base_quantity` |
| `interest.py` | day count conventions — ACT/365, ACT/360, ACT/ACT, 30/360 (`calculate_day_count_fraction`) — simple interest (`calculate_simple_interest`), and daily compounding over a span in closed form (`compound_growth`): the primitives of the Scheduled Investment provider's accrual |
| `price_marks.py` | daily mark of an asset: market quote, same-day trade average, last observation carried forward |
| `yield_on_cost.py` | Yield on Cost of holdings, replayed from the transaction ledger |
| `weights.py` | a part's share of a total, None on a total ≤ 0 (`share_of`, `percent_of`); the signed slices of an allocation (`slice_percents`); gross weights (`gross_weights`); concentration — largest weight and Herfindahl index (`concentration`) |
| `splits.py` | the ADJUSTMENT rows linked to a SPLIT asset event (`load_split_links`, one query for every reader; `split_linked_ids`, the ids an average-cost replay rescales — WAC preview, broker summary, auto cost), the rule for a usable ratio (`is_valid_split_ratio`), and the incoming adjustments without a cost linked to a SPLIT (`costless_incoming_split_adjustments`, what the event store asks before a SPLIT changes type — P-10) |
| `holding_window.py` | how long a position has been held at its broker, from its quantity stream: the oldest lot still open (`oldest_open_lot_date`), a closed position's flight time (`closed_position_window`), how many times units left it in a period (`exits_in`); a split rescales the open lots, never opens or consumes one |
| `fifo/` | FIFO lots: `models`, `eligibility`, `engine` (`run_fifo_lot_engine`) |
| `portfolio/` | daily portfolio state: `models`, `classifier`, `daily_state`, `derived_views`, `data_quality`, `period` (a period's boundary states, P&L and identity; the day's change of the total P&L, `day_change`), `contributions` (a position's figures in the Performance table: P22 transfer split, return on the start value, annualized window, closed positions), `engine` |
| `lots/` | lots analysis math: `prices`, `conversions` (`convert_closure`: a closure's legs, each in its currency at its date), `economic_events`, `histories`, `summary` (a lot's figures: `residual_cost`, `lot_value`, `lot_summary_figures`), `average_cost_lines`, `scope_boundary` (a transfer leg whose partner sits outside the scope, read at its edge: `read_transfers_at_scope_boundary`), `change_days` (the days a daily series can change on and their expansion to every day of the window, L1a: `lot_change_days`, `analysis_event_dates`, `expand_to_days`) |

## Rules

1. **A calculation owns its whole problem.** It takes the plain data of the problem (movements, currencies, dates) and
   calls the infrastructure it needs: `fx.convert_bulk`, the base currency from `settings_service`, the thresholds of
   `data_quality_thresholds`, the cache. It reads its own data from the database only at named points: the portfolio
   engine (`portfolio/engine.py`, and the configured FX pairs of `portfolio/data_quality.py`), the Yield on Cost
   loaders, the ledger totals (`ledger_totals.compute_control_totals`, on the session it is given) and the split links
   (`splits.load_split_links` and `splits.split_linked_ids`, the rows of the transactions it is given).
2. **Callers call the layer, never the other way round.** The layer never imports orchestration services
   (`portfolio_service`, `broker_service`, `transaction_service`, `lots_analysis_service`), the API, AI Export, risk,
   PAC or signals.
3. **No silent fallback.** A missing rate, price or cost is reported — `MissingConversion`, `missing_fx`, a data-quality
   issue — and the value is unavailable: never a number, never the unconverted amount.
4. **No re-exports.** Every `__init__.py` of the layer holds only its docstring. Import a name from the module that
   defines it: tests patch module globals (`convert_bulk`, caches) on the module that reads them, and a re-export would
   make the patch mute.
5. **One implementation.** Before writing a calculation, search the layer; if it exists, call it, with parameters when
   your case differs. Never keep a local or partial copy elsewhere, and report any copy you find.
6. **The frontend computes none of these quantities.** Interactive measures (the measuring tool, what-if, and the
   aggregates of the lots the user chooses, D-MF6(b)) are the only exceptions, and each must be declared where it lives.
7. **Change Decimal precision or rounding only inside `decimal.localcontext()`**, never by mutating `getcontext()`.
   The portfolio replay runs in a worker thread under a copy of the request's context (J-45, `portfolio/engine.py`),
   and that copy shares the same `decimal.Context` object: a `getcontext().prec = …` in the replay would change the
   request's precision too, and the other way round.
8. **A schema may import a pure function of the layer**, never a service or anything that does I/O. A contract
   invariant reads the one formula instead of rewriting it: `schemas/risk.py` checks a result's annualization factor
   with `returns.observations_per_year` (MF-D3). Pure means no session, no network, no file, no cache: a function of
   its arguments only.

## Adding a calculation

- Put it next to the calculations it relates to. A new problem gets a new module; a large engine becomes a
  sub-package with one module per step.
- Write its unit tests. Keep them pure where possible: replace `convert_bulk` on the module that reads it.
- Update the module map in `financial_math/__init__.py`, the table above, and the map in `backend.instructions.md`.

## Guards and tests

- `backend/test_scripts/test_services/test_financial_math/test_layer_boundaries.py` (`services financial-math`)
  parses every module of the layer: forbidden imports, docstring-only `__init__.py`, and the absence of the old homes
  (`services/portfolio_engine.py`, `services/fifo_lot_engine.py`, `services/price_resolver.py`,
  `services/yield_on_cost.py`, `utils/financial/`).
- Targeted selectors: `services financial-math`, `services roi-fifo-utils`, `services portfolio-engine`,
  `services lots-analysis-pure`, `utils roi-utils`. The test files keep their historical paths and names.
- Developer guide: `mkdocs_src/docs/developer/backend/financial_math.md`.
