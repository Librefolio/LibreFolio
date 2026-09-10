# Performance charts - SP06 G3/G1c and SP07 G1a/G1b

**Status:** PLANNED - plan-only authorization recorded on 2026-09-10.
**Implementation:** FROZEN. No production/test code is authorized by this plan.
**Revision:** 2 - developer control-hierarchy correction, 2026-09-10.
**Analysis baseline:** `f90d9801bd7a2d74aac6a27efe305314c6c004cc`
(`refs/heads/dev_release2`).
**Execution baseline:** to be written only after hard Gate 0, when workstream F is
integrated and the code is re-read.
**Coordinator:** Release 2 coordinator, session
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Future runtime lane:** port `6157`, absolute data directory
`/tmp/librefolio-r2-i-charts`.

Previous/master:

- [Advanced charts backlog](../09_feedbackJobs/02_grafici_avanzati.md)
- [Sprint analysis and dependency map](../09_feedbackJobs/06_piano_sprint.md)
- [Feedback-jobs index](../09_feedbackJobs/README.md)

This plan is the durable record of the final product decisions and the
dependency-safe split for an XL integration. It does not claim that any chart,
DTO, calculation, test, generated client, translation or documentation change
has been implemented.

## 1. Goal and scope

Deliver four related but differently owned chart slices:

| Slice | Product result | Revised size |
|---|---|---:|
| G3 | Historical rolling return for N calendar days in Asset detail | L end-to-end |
| G1a / F8a | Third GrowthChart mode for cumulative P&L, including selected-broker contribution lines | L |
| G1b / F8b | Synthetic total P&L candles plus selected-broker close lines | L |
| G1c / F8c | Signed personal DIVIDEND/INTEREST history as stacked bars | L |

Together they are an **XL integration**, not one implementation branch. The
shared theme is temporal performance; the real code ownership splits into:

1. Asset calendar-return backend.
2. Portfolio engine/service/schema integration.
3. GrowthChart frontend integration.
4. Asset-detail frontend integration.
5. Coordinator-owned generated/shared surfaces.

### 1.1 In scope

- Backend-owned financial transformations.
- Existing target-currency and broker-scope controls.
- Existing daily/weekly/monthly semantic zoom.
- Existing price/FX lookup, fallback, provenance and faded-line semantics after
  workstream F is integrated.
- Explicit data-quality states without silent zero-shaped fallbacks.
- Dashboard and Broker-detail GrowthChart behavior.
- Asset-detail primary chart mode.
- Future specialist tests, English documentation, generated API client and
  four-language UI strings, only in their authorized phases.

### 1.2 Out of scope

- A new price, FX or staleness resolver.
- Intraday portfolio truth or simultaneous cross-asset extrema.
- Volume for portfolio candles.
- Asset lines in portfolio P&L modes.
- A second broker, currency or resolution selector inside a chart.
- Standalone transfer-adjusted broker performance.
- New transaction-create semantics for negative DIVIDEND/INTEREST.
- New short-accounting support. If the final post-F engine still does not value
  negative positions canonically, candle output fails closed for that state.
- Feeding synthetic candles into risk, statistical-volatility or factual AI
  Export inputs.
- Database schema changes unless Gate 0 proves one is unavoidable; none is
  expected from the current analysis.

## 2. Hard Gate 0 - workstream F integration and code refresh

**Gate 0 blocks every production/test implementation step in this plan.**

The coordinator must provide the integrated F checkpoint on `dev_release2`.
Then the assigned owners must:

1. Verify exact target HEAD and clean worktree.
2. Read F's execution plan/checkpoint manifest and its final intended paths.
3. Re-read, rather than mechanically preserving current line claims:
   - `backend/app/services/portfolio_engine.py`;
   - the final shared price-resolution/retrieval modules;
   - `backend/app/services/asset_source.py`;
   - `backend/app/services/portfolio_service.py`;
   - `backend/app/schemas/portfolio.py`;
   - `frontend/src/routes/(app)/assets/[id]/+page.svelte`;
   - `frontend/src/lib/components/charts/PriceChartFull.svelte`;
   - `frontend/src/lib/components/dashboard/GrowthChart.svelte`;
   - `frontend/src/lib/components/charts/timeSeriesAggregation.ts`;
   - portfolio/asset stores and current tests.
4. Confirm how F preserves observation date, price/FX backward-fill metadata,
   split handling, quote base, ownership and current fallback provenance.
5. Replace this plan's analysis baseline with the real post-F execution
   baseline and record any changed symbols/paths.
6. Reconfirm the short-position behavior. If no canonical short valuation
   exists, retain the fail-closed candle contract; do not create one here.
7. Obtain a new **explicit developer implementation authorization**. The
   current authorization permits this Markdown plan only.

Gate 0 is complete only when the plan contains a dated implementation note with
the post-F SHA, final resolver contract, file reservations and developer
authorization. A coordinator-only approval is insufficient.

## 3. Final product contract

### 3.1 G3 - rolling return by calendar days

- Asset detail gains a primary mode `Price | N-day return`.
- Output is a historical rolling series, with one result state for every chart
  date in the selected range.
- Windows are `7`, `30`, `90`, `365` calendar days; default is `30`.
- Formula remains backend-owned:

  ```text
  return(t, N) = price(t) / price(t - N calendar days) - 1
  ```

- Prices at `t` and `t-N` come from the **existing final post-F Asset price
  retrieval/resolution path**, including its current backward lookup and
  staleness policy. No return-specific threshold, resolver or service is added.
- Currency is the target currency already selected in the top Asset toolbar.
  The return therefore includes FX movement when target differs from the
  asset's native currency.
- Backfilled/carried result portions reuse the existing faded-line visual
  semantics from Asset/FX price charts.
- Tooltip/point metadata preserves the requested reference date and actual
  observation-date provenance wherever the final resolver contract exposes it.
- The existing observation-count `RISK_ROLLING_RETURN` behavior remains
  backward compatible for saved signal configurations. The calendar view must
  not silently reinterpret those saved instances.
- No TypeScript price lookup or return formula.
- In N-day mode, price-only controls that would misrepresent the series are not
  active: no candlestick, Abs/% rebase or price editing. Saved price/signal
  settings remain untouched and return when the user switches back to Price.

### 3.2 G1a - cumulative P&L with additive broker contributions

- GrowthChart modes are mutually exclusive:

  ```text
  Value | Return % | P&L
  ```

- P&L contains three mutually exclusive submodes:

  ```text
  Line | Synthetic candles | Income
  ```

- Total uses existing canonical `PortfolioHistory.total_pnl`, calculated from
  inception and never rebased at selected-range or zoom start.
- Dashboard behavior uses the effective broker scope already produced by the
  existing top filter:
  - one selected broker: total line only;
  - two or more selected brokers: total line plus one line for every selected
    broker;
  - "All" means the existing explicit owned-broker set, not a new selector.
- Broker detail always renders total only.
- All required lines are initially visible. There are no asset lines.
- Broker lines are additive contributions inside the **one selected combined
  scope**, not independent one-broker engine calculations.
- For an internal transfer, in-transit value stays with the departure broker
  until arrival, then moves to the destination broker. Individual lines may
  jump; this is accepted.
- Mandatory daily Decimal identity:

  ```text
  sum(selected broker P&L contributions) == canonical scoped total_pnl
  ```

- UI wording/tooltips must not describe these lines as standalone
  transfer-adjusted broker performance.

### 3.3 G1b - synthetic P&L candles

- Synthetic candles are the second P&L submode. They do not become a fourth
  top-level GrowthChart mode.

- First release hybrid rendering:
  - total scoped portfolio as candlesticks;
  - when effective scope has at least two brokers, overlay one selected-broker
    **close-P&L line** per broker;
  - one broker or Broker detail: total candle only.
- For each calendar day, apply all transactions first and use historical
  end-of-day quantities, role-aware ownership, quote-base quantity and target
  currency.
- Compose asset contributions into one **daily portfolio candle first**.
  Weekly/monthly rendering then applies:

  ```text
  open  = first daily open
  high  = max daily high
  low   = min daily low
  close = last daily close
  ```

- Never sum daily candles. Never aggregate each asset to week/month before
  cross-asset daily composition.
- Cross-asset high/low are explicitly synthetic and potentially
  non-simultaneous. The label is always visible; tooltip/help repeats the
  limitation.
- No volume field in the backend contract. A frontend chart adapter may use
  `null` only because the shared chart point type allows it.
- Missing OHLC reuses the final existing valuation fallback chain. If no
  intraday variance is known for one asset/day, that resolved contribution is
  flat:

  ```text
  open = high = low = close = resolved valuation contribution
  ```

  The asset/day is not dropped and no new resolver is invented.
- Reuse existing data-quality and faded semantics for carried/fallback values.
- Daily total candle close must equal canonical total P&L exactly.
- If final F still cannot value a true negative position, the candle series is
  unavailable for that unsupported state. Do not omit the short or fabricate a
  liability. Revisit only if F supplies canonical short valuation.
- Synthetic candles are presentation-only. They are not an intraday series,
  statistical-volatility input or factual AI Export dataset.

### 3.4 G1c - signed personal income history

- Income is the third P&L submode. It does not become a fourth top-level
  GrowthChart mode.
- Source is every personal, scoped, committed `Transaction` of type DIVIDEND or
  INTEREST.
- Include asset-linked and broker-level `asset_id=None` rows. Do not derive
  personal cash from global `AssetEvent` declarations.
- Reuse target currency, current broker scope and existing temporal resolution.
- Preserve the transaction amount sign for legacy corrections. The create API
  may continue requiring positive new income rows; this plan does not relax
  that rule.
- DIVIDEND and INTEREST render as distinct-color **stacked** bars. Tooltip shows
  both signed values and their total.
- Daily values are sparse economic flows. Weekly/monthly buckets sum them;
  they never use end-of-period/last-value semantics.
- Period boundary remains the canonical portfolio boundary
  `(date_from, date_to]`.
- Mandatory Decimal identity:

  ```text
  sum(dividend flow) + sum(interest flow)
      == canonical signed PortfolioSummary.period_income
  ```

- Signed corrections must be updated consistently in summary, contribution,
  engine return-pool accounting and history. They must not be pushed into the
  reconciliation residual by an `abs()` mismatch.
- Missing FX uses the existing portfolio data-quality/remediation contract.
  It must not become a known zero.

## 4. Backend architecture

### 4.1 Proposed report DTOs

Keep `PortfolioHistoryPoint.total_pnl` as the single total line source. Add
optional report outputs rather than duplicating total history:

```text
broker_pnl_history:
  - broker_id
  - broker_name
  - points:
      - date
      - total_pnl
      - quality/provenance when required

pnl_candles:
  - date
  - open
  - high
  - low
  - close
  - quality/provenance
  - hypothetical = true at series metadata level
  # no volume

income_history:
  - date
  - dividend
  - interest
  - quality/provenance
```

Names may be adjusted at Gate 0 to match final schema conventions, but the
separation and semantics above are fixed.

Proposed query flags:

| Flag | Caller policy |
|---|---|
| `include_broker_pnl_history` | Dashboard true only when effective scope has at least two brokers |
| `include_income_history` | Dashboard/Broker overview true; sparse payload keeps mode immediately available |
| `include_pnl_candles` | Lazy true on first candle activation; expensive OHLC work stays off ordinary reports |

All optional flags must enter:

- backend L2 report cache key;
- frontend cache/inflight key;
- report metadata `included_features`;
- L1 result key if the engine result shape or preload differs.

The current L2 key lacks split-event fingerprinting while the L1 key includes
it. Gate 0 must verify F's state; if still true, add split fingerprint or
central backend invalidation before shipping split-sensitive candles.

### 4.2 Additive broker contribution state

Do not run one engine calculation per broker. Sub-scope calculations change
linked internal transfers into external boundaries and are not guaranteed to
sum to the combined scope.

Inside one combined-scope daily replay, maintain additive values by broker:

- owned cash;
- held-position market value;
- external capital contribution;
- in-transit cash/asset value attributed to departure until arrival;
- final per-broker P&L contribution.

Internal transfers do not create external capital for the selected combined
scope. At arrival, custody/value attribution moves to the destination. The
implementation must build the total and broker values from the same Decimal
components, not calculate a residual line after the fact.

Every emitted day asserts, through a typed invariant/test:

```text
sum(broker_nav_contribution) == scoped nav
sum(broker_capital_contribution) == scoped capital_baseline
sum(broker_pnl_contribution) == scoped total_pnl
```

If rounding is needed only at serialization, keep internal Decimal values
unrounded and serialize all lines with the same policy.

### 4.3 Daily synthetic candle composition

The final implementation should expose one resolved per-asset/day valuation
record from F's existing path, carrying:

- resolved O/H/L/C or resolved close-only fallback;
- native/target currency provenance;
- price and FX observation dates/backward-fill metadata;
- quote-base quantity;
- data-quality state.

For an EOD owned quantity `q`, quote base `b` and daily FX factor `f`:

```text
factor = q / b * f
asset_open  = factor * open
asset_close = factor * close
```

For a canonically supported negative factor, high/low orientation reverses:

```text
asset_high = factor * low
asset_low  = factor * high
```

This formula is used only if Gate 0 proves the final engine supports negative
positions. Otherwise the series fails closed for that state.

Compose all resolved asset contributions for the day. Then add one common
non-price offset:

```text
offset = canonical total_pnl - sum(asset_close)

portfolio_open  = offset + sum(asset_open)
portfolio_high  = offset + sum(asset_high)
portfolio_low   = offset + sum(asset_low)
portfolio_close = canonical total_pnl
```

The offset carries cash, capital baseline, realized/income effects, in-transit
and flat fallback contributions. Use the same daily FX observation for all four
fields; there are no intraday FX extrema.

### 4.4 Signed income foundation

Extract one signed-income accumulator used by summary, contribution and report
history:

1. Keep `tx.amount` sign through target conversion.
2. Apply role-aware ownership exactly once.
3. Group by `(date, transaction type, broker)` and preserve `asset_id=None`.
4. Update return-pool accounting with the signed value.
5. Replace positive-only inclusion checks with nonzero checks where legacy
   corrections must remain visible.
6. Keep the create/update validation rule unchanged unless separately
   authorized.
7. Update `period_income` schema prose so it no longer falsely promises a
   positive-only value.

For ordinary valid positive income, behavior is unchanged. For a legacy
negative correction, NAV already reflects signed cash; this change moves the
same value from "Other / reconciliation residual" into canonical Income.

### 4.5 Calendar-return signal

After Gate 0, choose the smallest compatible signal integration based on F's
final code:

- either a dedicated calendar-return signal;
- or a backward-compatible explicit calendar mode whose default leaves the
  existing observation-based signal unchanged.

Whichever is chosen:

- consume F's resolved daily series;
- request enough pre-visible history through the existing loader;
- produce one output state per visible chart date;
- include N=30 in normalized/default params;
- carry reference target date and actual observation provenance through an
  additive signal-point metadata contract if the final contract lacks it;
- use the existing signal status/warmup/availability structure;
- never duplicate price lookup, FX conversion, backward fill or finance math
  in TypeScript.

## 5. Frontend architecture

### 5.1 GrowthChart ownership

One owner implements G1a, G1b and G1c in
`frontend/src/lib/components/dashboard/GrowthChart.svelte`.

The component keeps two explicit state axes:

```text
coreMode   = value | return | pnl
pnlSubmode = line | candles | income
```

`pnlSubmode` is active only while `coreMode == pnl`; switching Value/Return does
not promote Income into the core-mode selector.

The same owner also coordinates:

- `timeSeriesAggregation.ts`;
- portfolio store request/cache options;
- Dashboard mount;
- Broker-detail mount;
- pure chart adapters/helpers.

No parallel writer may independently add one of the three modes.

Mode changes must:

1. Snapshot the current logical zoom range.
2. Hide the active ECharts tooltip before changing series structure.
3. Rebuild the selected series.
4. Restore the logical date window at the current semantic resolution.
5. Keep all required total/broker series visible.

Advanced-data fetches must not replace an unchanged `history` reference merely
to obtain optional candle data, because the current chart resets
resolution/zoom on a new history reference.

### 5.2 Temporal reducers

- Keep `aggregateLineSeries()` end-of-period behavior for cumulative P&L and
  broker close lines.
- Keep `aggregateOHLCV()` for already-composed daily total candles.
- Add a separate flow reducer, provisionally `aggregateSumSeries()`, for signed
  DIVIDEND/INTEREST buckets.
- Do not change generic bar-signal downsampling, which intentionally uses a
  last-value snapshot.
- Preserve UTC dates, ISO weeks, UTC months, bucket boundaries,
  representative dates, density thresholds, hysteresis and 200 ms settled
  zoom recomputation.

### 5.3 Asset-detail ownership

A separate owner integrates G3 after F and the backend calendar signal:

- primary selector `Price | N-day return`;
- window controls `7/30/90/365`, default `30`;
- existing target-currency/date/resolution controls only;
- PriceChartFull receives additive props for percentage-unit rendering and
  hiding incompatible controls if required;
- no return editing, price candlestick or extra percentage rebase;
- existing faded gradient and tooltip provenance;
- switching back restores existing Price state/settings.

## 6. Dependency-safe phases and owners

| Phase | Owner | Dependency | Deliverable | Status |
|---|---|---|---|---|
| I00 | Workstream I planner | Plan-only developer authorization | Durable product contract, split, storyboards and backlog links | COMPLETE 2026-09-10 |
| G0 | Coordinator + assigned integrators | F integrated on `dev_release2` | Post-F source refresh, SHA/path reservations, implementation authorization | BLOCKED |
| I10 | G3 backend owner | G0 | Calendar-return backend series + provenance, no resolver duplication | PENDING |
| I20 | Portfolio backend integrator | G0 | Additive daily broker P&L + signed canonical income | PENDING |
| I30 | Portfolio backend integrator | I20 + final F resolver | Daily total candles + flat fallback + strict close identity | PENDING |
| I40 | Portfolio backend integrator + coordinator | I20 + I30 | DTO/report/cache wiring, then coordinator API sync | PENDING |
| I50 | GrowthChart owner | I40 | Value/Return/P&L core modes; Line/Candles/Income P&L submodes; broker lines and sum aggregation | PENDING |
| I60 | G3 Asset UI owner | I10 + G0 | Historical N-day primary mode in final Asset detail | PENDING |
| I70 | Test author + owners | Relevant implementation phases | Targeted backend/frontend regressions and integration gates | PENDING |
| I80 | Docs writer + coordinator | Stable integrated UI | English docs, coordinator i18n/runner/changelog records | PENDING |
| I90 | Developer + coordinator | I50 + I60 + I70 + I80 | Desktop/mobile operational review, corrections, integration handoff | PENDING |

> **Note implementazione (I00, 2026-09-10):** only the durable plan, final
> product decisions, updated ASCII v2 storyboards and minimal feedback-job
> links were written. No production/test implementation, specialist, server,
> suite, API sync, i18n, generated output, staging or commit was started.

> **Note implementazione (I00 revision 2, 2026-09-10):** developer correction
> retained exactly three top-level modes (`Value | Return % | P&L`) and moved
> Income under P&L as the third mutually exclusive submode beside Line and
> Synthetic candles. Architecture, desktop/mobile storyboards, selectors,
> frontend test plan, phase I50 and DoD were realigned; implementation stayed
> frozen.

### 6.1 Parallel work after Gate 0

I10 and I20 may proceed in parallel because their owned backend files are
separate after reservations are confirmed. I30 waits for I20 and F's final
resolver. I50 waits for the integrated report contract. I60 waits for I10 and
F's Asset-detail result.

### 6.2 File reservations

| Owner | Reserved surfaces |
|---|---|
| G3 backend | Calendar signal plugin/helper; signal schema/service/asset-query integration only as required |
| Portfolio backend integrator | `portfolio_engine.py`, `portfolio_service.py`, `schemas/portfolio.py`, portfolio cache behavior |
| GrowthChart owner | `GrowthChart.svelte`, `timeSeriesAggregation.ts`, portfolio store, Dashboard/Broker mounts |
| G3 Asset UI | Asset detail page and additive PriceChartFull props/helpers |
| Coordinator | API client generation, i18n catalogues, test runner, nav, changelog, master records |
| Test author | Distinct new/repaired tests assigned after implementation authorization |
| Docs writer | English MkDocs pages after UI/contract stability |

Any final F overlap overrides this provisional table and must be recorded at
Gate 0 before editing.

## 7. ASCII storyboards v2

These storyboards record the closed product contract. They are implementation
inputs, not proof of a rendered UI.

### 7.1 G3 desktop - historical calendar return

```text
TOP TOOLBAR (unchanged)
[Date range........................] [Target currency] [Sync]

+ Asset chart ------------------------------------------------------+
| [Price] [N-day return]        Window: [7] [30*] [90] [365]       |
|                              [Daily/Weekly/Monthly badge]         |
| Return %                                                        0%|
|      observed line -------- faded carried line ........          |
|                                                                  |
| Tooltip                                                          |
|  Chart date: 2026-09-10                                          |
|  N target: 2026-08-11                                            |
|  Actual reference observation: 2026-08-10                        |
|  Return (30d): +4.21% | existing carry/provenance status         |
+------------------------------------------------------------------+
```

Price mode remains unchanged. N-day mode does not show candlestick, Abs/% or
price-edit controls. No second date/currency/resolution selector appears.

Proposed stable selectors/state:

```text
asset-chart-primary-price
asset-chart-primary-calendar-return
asset-calendar-window-7
asset-calendar-window-30
asset-calendar-window-90
asset-calendar-window-365
data-primary-mode="price|calendar-return"
data-window-days="7|30|90|365"
data-series-state="loading|ready|partial|unavailable|error"
```

### 7.2 G3 mobile

```text
[Date range]
[Target currency] [Sync]

+ Asset chart -------------------------------+
| [Price] [N-day return]                     |
| [7] [30*] [90] [365]        [resolution]  |
| provenance/data-quality state              |
|                                            |
|             rolling return line            |
|       observed ------ carried ......       |
|                                            |
| tap tooltip: chart date / target date /    |
| actual observation / return / carry state  |
+--------------------------------------------+
```

Window chips wrap or scroll without reducing the plot to an unusable width.
Tooltip remains confined to the chart viewport.

### 7.3 P&L desktop - Dashboard with two or more brokers

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution badge]     |
| [Line*] [Synthetic candles] [Income]                              |
|                                                                  |
|  TOTAL (prominent) ==========================================     |
|  Broker A ----------------  Broker B ----------------             |
|  0 -----------------------------------------------------------    |
| Legend: Total | Broker A | Broker B  (all initially visible)     |
| Tooltip: Total; each broker; Sum brokers = Total                 |
+------------------------------------------------------------------+
```

Exactly one selected broker, or Broker detail:

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line*] [Synthetic candles] [Income]      |
| TOTAL only ============================== |
+-------------------------------------------+
```

No broker selector exists inside the chart. Colors are stable by broker ID.

Proposed stable selectors/state:

```text
growth-toggle-value
growth-toggle-return
growth-toggle-pnl
growth-chart-canvas
data-mode="value|return|pnl"
data-pnl-submode="line|candles|income"
data-resolution="daily|weekly|monthly"
data-series-state="loading|ready|partial|unavailable|error"
```

Compatibility note: current selectors may retain aliases during the local
refactor if tests or released integrations require them; Gate 0 decides from
the final code, not from this label proposal.

### 7.4 P&L mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line*] [Candles] [Income]                |
| scroll legend: Total | A | B | ...       |
| total + every selected broker line       |
| tap tooltip lists all required lines     |
+-------------------------------------------+
```

Legend may scroll, but no selected broker starts hidden.

### 7.5 Synthetic candles desktop

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution]          |
| [Line] [Synthetic candles*] [Income]                              |
| Synthetic/hypothetical extremes - not simultaneous - no volume   |
|                                                                  |
|       TOTAL candlesticks                                         |
|       |#|  flat/faded fallback |-|  |#|                         |
|  Broker A close -----------  Broker B close -----------          |
| Legend: Total OHLC | Broker A close | Broker B close             |
| Tooltip: total O/H/L/C; each broker close; fallback provenance   |
+------------------------------------------------------------------+
```

One broker/Broker detail shows total candles only. Flat fallback contributions
remain in the total rather than disappearing.

Proposed stable selectors/state:

```text
growth-pnl-submode-line
growth-pnl-submode-candles
growth-pnl-submode-income
growth-synthetic-badge
data-pnl-submode="line|candles|income"
data-series-state="loading|ready|partial|unavailable|error"
```

### 7.6 Synthetic candles mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]                |
| [Line] [Candles*] [Income] [resolution]  |
| Synthetic (tap for explanation)          |
| total candles + broker close lines       |
| tap: O/H/L/C + broker closes + fallback  |
+-------------------------------------------+
```

The synthetic warning stays visible in compact form. No volume row exists.

### 7.7 Income desktop

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution badge]    |
| [Line] [Synthetic candles] [Income*]                              |
|                                                                  |
|       + DIVIDEND                                                  |
|       + INTEREST     stacked signed bucket SUM                   |
|  ------------------------------------------------------------- 0 |
|       legacy negative corrections stack below zero               |
| Legend: Dividend | Interest                                      |
| Tooltip: bucket range; Dividend; Interest; signed Total          |
+------------------------------------------------------------------+
```

Both types are always present in the stacked view; there is no income-type
selector. Known zero income and unavailable/missing-FX data are distinct states.

Proposed stable selectors/state:

```text
growth-pnl-submode-line
growth-pnl-submode-candles
growth-pnl-submode-income
growth-income-zero
data-mode="value|return|pnl"
data-pnl-submode="line|candles|income"
data-income-state="loading|ready|zero|partial|unavailable|error"
```

### 7.8 Income mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line] [Candles] [Income*]                |
| legend: Dividend | Interest              |
| stacked signed bars                      |
| tap: bucket / both values / total        |
+-------------------------------------------+
```

The chart reuses top-level broker and currency controls. No duplicate selector
is added.

## 8. Data states

| State | Calendar return | P&L lines | Candles | Income |
|---|---|---|---|---|
| Loading | Existing chart skeleton/state | Preserve old data while refreshing | Explicit lazy-load state | Existing report load state |
| Ready | Full historical series | Total and required broker lines | Total candle + required broker closes | Stacked signed flows |
| Zero | Valid zero return | Valid line at zero | Valid flat zero candle | Explicit known-zero income |
| Partial/carried | Existing faded line + provenance | Existing portfolio DQ | Flat fallback/faded candle metadata | Available signed flows + missing-FX DQ |
| Unavailable | Existing resolver/signal reason | No canonical history | Unsupported canonical short or missing resolved valuation | No convertible canonical flow data |
| Error | Signal error, retry through existing flow | Report error | Candle payload error, line mode remains available | Report error |

No missing/partial state is represented by invented zero.

## 9. Future test plan

Tests are not authorized in the current plan-only checkpoint. When
implementation is authorized, invoke `test-author` and give it distinct files.

### 9.1 Backend cases

- Calendar N is measured by date, not observation count, over weekends and
  irregular source observations.
- Default 30 and options 7/30/90/365.
- Existing observation-based rolling signal remains unchanged.
- Selected target currency and final resolver provenance are preserved.
- One combined-scope replay emits additive broker lines; internal transfer
  stays at departure while in transit, moves at arrival, and daily sum remains
  exact.
- Owner share, 0% owner behavior, editor/viewer visibility and selected scope.
- Daily candle close equals canonical total P&L.
- Daily-first vs wrong asset-first weekly aggregation uses a discriminating
  fixture with extrema on different asset/days.
- Quote-base, split, FX, flat fallback, carried values, missing values and
  unsupported short.
- Assetless DIVIDEND/INTEREST and legacy signed correction.
- Signed income changes decomposition, not NAV/total P&L.
- Income bucket total equals `period_income`.
- Cache keys distinguish optional features and split-event changes.

### 9.2 Frontend cases

- Three mutually exclusive core Growth modes and three mutually exclusive P&L
  submodes (`Line | Synthetic candles | Income`).
- Dashboard effective scope of one vs at least two brokers.
- Broker detail total-only behavior.
- Total/broker lines all initially visible; stable broker colors.
- Hybrid total candle + broker close lines.
- Synthetic warning and no volume.
- Stacked signed income bars.
- Mode/resolution/zoom switch preserves logical window and clears stale tooltip.
- G3 historical series, default window, all window controls, no double rebase
  or editing.
- Faded return/candle portions reuse existing chart semantics.
- Desktop/mobile/dark mode; selectors never depend on translated text.

### 9.3 Proposed future selectors

All future commands use the assigned lane and never run concurrently inside it:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts schemas signals <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services signal-service <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services asset-signals <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services portfolio-engine <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services roi-fifo-utils <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset asset-unit
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset asset-detail <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-portfolio store-unit
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-portfolio dashboard <filter>
```

Runner registration remains coordinator-owned.

## 10. Documentation and generated/shared work

Only after stable implementation:

- coordinator runs API sync from the integrated schema;
- coordinator adds UI keys through the i18n CLI for EN/IT/FR/ES;
- docs-writer updates English pages:
  - `mkdocs_src/docs/user/dashboard/charts.en.md`;
  - `mkdocs_src/docs/user/assets/detail/chart.en.md`;
  - `mkdocs_src/docs/user/assets/detail/signals.en.md` if the final signal is
    user-configurable;
  - the directly related portfolio P&L theory page if semantics need
    clarification;
- coordinator updates changelog/master records only for delivered behavior;
- no translation pipeline runs without explicit developer request.

## 11. Definition of done

### 11.1 G3

- Historical backend series covers each chart date with value or explicit
  unavailable state.
- Calendar windows and default are exact.
- Final existing lookup/fallback/staleness is reused, with no parallel resolver.
- Selected target currency is honored.
- Carried sections use existing fade/provenance.
- Observation-based saved signals remain unchanged.
- No frontend finance math, rebase or editing.

### 11.2 G1a

- Top-level GrowthChart controls are exactly `Value | Return % | P&L`.
- Total is canonical cumulative P&L.
- Effective broker count drives total-only vs total-plus-broker lines.
- Dashboard and Broker detail follow the closed surface rules.
- Daily broker Decimal sum equals total, including internal-transfer windows.
- Lines are initially visible and no extra selector exists.

### 11.3 G1b

- Synthetic candles are the second P&L submode, not a top-level mode.
- Total close equals canonical total P&L every day.
- Broker close overlays reuse the exact G1a series.
- EOD quantity, ownership, quote-base, split and target FX are correct.
- Missing OHLC uses flat final-resolver fallback.
- Synthetic label is persistent; no volume or factual-risk reuse.
- Daily composition precedes temporal aggregation.
- Unsupported short fails closed unless F establishes canonical support.

### 11.4 G1c

- Income is the third P&L submode, not a top-level mode.
- Every scoped DIVIDEND/INTEREST, including assetless rows, enters exactly once.
- Signed legacy corrections remain signed throughout all canonical
  decompositions.
- Stacked buckets sum flows, with exact KPI reconciliation.
- Zero, partial FX and unavailable are distinct.

### 11.5 Cross-cutting

- Optional report payloads and both cache layers are coherent.
- API/client types, i18n, docs and tests describe the same contract.
- Zoom, viewport, theme, account/session and broker/currency changes preserve
  correct state.
- No CSS/text selectors; stable `data-testid`/state attributes.
- Developer completes pre-code storyboard/plan review and post-code operational
  walkthrough on desktop/mobile.
- Final workstream handoff contains actual SHA, manifest, evidence, conflicts,
  generated exclusions, stopped runtime proof and proposed commit message.

## 12. Progress protocol

After every authorized implementation phase:

1. Update the phase row immediately with date/status.
2. Add `Note implementazione` describing real code and evidence.
3. Add `Fuori pista` for every meaningful detour/failure.
4. Record exact commands and results.
5. Cross-link any corrective round in both directions.

No pending row may be marked complete from a plan, fixture or test name alone.
The current durable state remains:

```text
PLANNED / IMPLEMENTATION FROZEN / HARD GATE 0 WAITING FOR F
```
