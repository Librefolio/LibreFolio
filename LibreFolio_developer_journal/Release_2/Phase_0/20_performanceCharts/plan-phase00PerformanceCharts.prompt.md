# Performance charts - SP06 G3/G1c and SP07 G1a/G1b

**Status:** I10 calendar-return backend COMPLETE / integration pending.
**Implementation:** I10 was explicitly authorized and completed on 2026-09-10.
All portfolio and frontend phases remain FROZEN.
**Revision:** 4 - I10 signal-only implementation and evidence, 2026-09-10.
**Analysis baseline:** `f90d9801bd7a2d74aac6a27efe305314c6c004cc`
(`refs/heads/dev_release2`).
**Gate-0 execution baseline:** `0af66da5f366a9559549154631a4ee15ca620915`,
containing `dev_release2@973968ed2` and workstream F commit `e50d66408`.
**I10 implementation baseline:** `0af66da5f366a9559549154631a4ee15ca620915`;
developer authorization is limited to the signal-only I10 slice.
**Portfolio implementation baseline:** not yet authorized. It will be the later
post-H target SHA supplied after the H-before-I integration gate.
**Coordinator:** Release 2 coordinator, session
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Future runtime lane:** port `6157`, absolute data directory
`/tmp/librefolio-r2-i-charts`.

Previous/master:

- [Advanced charts backlog](../09_feedbackJobs/02_grafici_avanzati.md)
- [Sprint analysis and dependency map](../09_feedbackJobs/06_piano_sprint.md)
- [Feedback-jobs index](../09_feedbackJobs/README.md)
- [Workstream F plan](../17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md)

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
- Existing price/FX lookup, fallback, provenance and faded-line semantics in
  the now-integrated post-F source.
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
- New short-accounting support. The verified post-F engine does not value
  negative positions canonically, so candle output fails closed for that state.
- Feeding synthetic candles into risk, statistical-volatility or factual AI
  Export inputs.
- Database schema changes unless Gate 0 proves one is unavoidable; none is
  expected from the current analysis.

## 2. Hard Gate 0 - post-F code refresh and implementation authorization

**Gate 0 blocks every production/test implementation step in this plan.**

The F checkpoint is now present in the technical-refresh HEAD. The source
refresh items below are complete, but Gate 0 remains **BLOCKED** because the
developer has not authorized implementation.

The assigned owners must:

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
5. Record the post-F technical-refresh HEAD and changed symbols/paths.
6. Preserve the confirmed short-position result: no canonical short valuation
   exists, so retain the fail-closed candle contract; do not create one here.
7. Obtain a new **explicit developer implementation authorization**. The
   current authorization permits this Markdown plan only.

Gate 0 is released only for a phase whose dated note contains the exact
execution SHA, final resolver contract, file reservations and verbatim
developer authorization. I10 now satisfies that condition. Portfolio phases
remain blocked by H0, F engine release, a new post-H baseline and their own
explicit authorization.

### 2.1 Gate 0 technical refresh - 2026-09-10

> **Note implementazione (G0 technical refresh, 2026-09-10):** verified clean
> HEAD `0af66da5f366a9559549154631a4ee15ca620915` on
> `e-alfy-performance-charts-plan`. It merges current
> `dev_release2@973968ed2`, including F commit `e50d66408`. Read F's durable
> plan and exact committed diffs, then re-read the final engine, portfolio
> service/schema, resolver, Asset detail/query/cache path, GrowthChart,
> PriceChartFull, temporal reducers, stores and relevant tests. No production
> or test implementation and no runtime command was executed.

F's relevant delivered delta is narrower than the original conflict forecast:

- `portfolio_engine.py` now exports
  `compute_portfolio_fx_cache_identity(...)` and includes its result in the L1
  blob key.
- F did not change `price_resolver.py`, `portfolio_service.py`,
  `schemas/portfolio.py`, `GrowthChart.svelte`, `PriceChartFull.svelte`,
  `timeSeriesAggregation.ts`, portfolio store or Asset price-cache adapter.
- F's Asset-detail edit adds the transactions link in the header, outside the
  chart state/render block. G3 must preserve it.
- F's `asset_source.py` edits are in Asset deletion, not
  `get_prices_bulk()`/backward-fill/signal execution.
- F added FX-identity/invalidation tests to
  `test_financial/test_portfolio_service.py` and `test_fx_core.py`, plus an
  Asset-detail link test. Future tests extend these files without replacing
  F's coverage.

Final source reality:

- `AssetPriceSeries` remains the single close resolver:
  `MARKET -> TRADE_AVG -> CARRIED (LOCF) -> MISSING`. It carries native
  currency, actual observation date, estimated origin and price
  `BackwardFillInfo`; FX is still applied by the engine adoption layer.
- Asset `get_prices_bulk()` already emits a dense daily backward-filled OHLC
  series, applies target-currency FX to all OHLC fields, and retains price +
  FX provenance on a fresh API response.
- The frontend Asset cache adapter still stores only `originalClose` and price
  `daysBack`. A cache-hit reconstruction drops original O/H/L and FX
  provenance. G3 cannot claim full fade/tooltip parity until that existing
  cache representation is widened or the signal response carries the needed
  provenance independently.
- Existing `RISK_ROLLING_RETURN` remains prepared-observation based. Its
  `window` counts prepared returns, not calendar dates.
- `DailyStateBuilder` still keeps aggregate cash/capital state, per-broker
  quantities, no daily broker P&L DTO, and filters `qty <= 0`. True shorts
  remain unsupported.
- `InTransitInterval.share` is still hardcoded to `1` in the classifier helper.
  The additive broker/candle implementation must correct this before claiming
  ownership-scaled in-transit values.
- Portfolio engine price preload and `AssetPriceSeries` remain close-only even
  though `PriceHistory` stores OHLC. Candles must extend the existing resolver
  data shape, not create a parallel resolver.
- `PortfolioReportQuery/Response` contains none of the proposed broker-history,
  candle or income fields/flags.
- L2 report cache still keys access + transaction + price state only. It does
  not yet consume F's shared FX identity and still lacks split-event identity.
- Frontend `fetchReport(...)` still uses nine positional parameters and manually
  concatenated feature-key suffixes. Adding three more positional booleans
  would be unsafe; use one typed feature-options object/canonical feature key
  while preserving compatibility wrappers for existing callers.
- `PortfolioSummary.period_income`, engine income pools and contribution
  service still use `abs()`; signed legacy corrections are not canonical yet.
- GrowthChart remains `eur|pct`, with total P&L mapped only for the ABS tooltip;
  unused `periodBasePnl` must not be adopted because the approved P&L line is
  never rebased.
- `aggregateOHLCV()` is ready and tested; no flow-sum reducer exists.
- PriceChartFull already owns line/candle, absolute/percentage, semantic zoom
  and `disableCandlestick`, but lacks percentage-unit primary-series and
  hide-view-control props needed by G3.

### 2.2 H-before-I shared-surface gate

Coordinator decision: H/YOC integrates before I on shared portfolio surfaces.
Until H is merged and I re-reads the new target:

- H exclusively owns `portfolio_service.py`, `schemas/portfolio.py`, relevant
  portfolio service/API tests, any approved minimal FIFO eligibility seam, and
  `ExposureTable.svelte` plus its test.
- F retains `portfolio_engine.py` until the coordinator declares its integration
  stable.
- I20 and every dependent portfolio/candle/report/GrowthChart phase remain
  blocked.
- Only the isolated G3 **backend signal** slice may be considered for execution
  after explicit developer authorization, and only if its final file set avoids
  all H/F-owned surfaces.

After H integration, I must merge/rebase only through the developer/coordinator
workflow, verify the new exact SHA, re-read H/F changes and update reservations
before portfolio implementation. H is a sequence dependency, not a reason to
duplicate its YOC calculations or cache changes.

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
- The verified post-F engine still cannot value a true negative position.
  Therefore the candle series is unavailable for that unsupported state. Do
  not omit the short or fabricate a liability; broader short accounting needs
  separate authorization.
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

Frontend feature selection must move behind a typed options object and one
canonical cache-key serialization. Keep existing positional exports as
compatibility wrappers if current callers cannot migrate atomically; do not
append more order-sensitive boolean arguments.

Post-F, L1 already includes F's bounded
`compute_portfolio_fx_cache_identity(...)`; preserve and reuse it. L2 still
lacks both this FX identity and split-event identity. H owns L2's current file
until integration, so I must first consume H's result, then add only whatever
FX/split/feature-key coverage remains. Do not duplicate F's helper.

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

Post-F confirms that `AssetPriceSeries` is the single resolver but currently
carries close only, while `PriceHistory` and Asset query responses carry OHLC.
The candle phase must widen the existing `PriceObservation`/`ResolvedMark`
family (or an equivalent same-resolver envelope) with optional OHLC. It must
not add a second lookup/fallback class.

The final implementation should expose one resolved per-asset/day valuation
record from that same path, carrying:

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

This formula is retained as the future orientation rule, but the verified
engine does not support negative-position valuation. This plan therefore fails
closed before composing a short candle; it does not execute this branch.

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

The technical refresh favors a dedicated calendar-return plugin because the
existing `RISK_ROLLING_RETURN` is statically coupled to prepared observation
returns. The isolated plugin can consume the already-resolved dense daily
`SignalPricePoint` input without changing `asset_source.py`, the price resolver,
portfolio engine/service/schema or H-owned tests.

If implementation evidence proves a smaller backward-compatible extension is
safer, it must still leave the existing signal's default and saved instances
unchanged.

Whichever is chosen:

- consume F's resolved daily series;
- request enough pre-visible history through the existing loader;
- produce one output state per visible chart date;
- include N=30 in normalized/default params;
- carry reference target date and actual observation provenance through an
  additive `SignalValuePoint` metadata contract (currently absent), or an
  equally typed signal-owned companion that does not depend on the lossy Asset
  price cache;
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

| Phase | Size | Owner | Dependency | Deliverable | Status |
|---|---:|---|---|---|---|
| I00 | XS | Workstream I planner | Plan-only developer authorization | Durable product contract, split, storyboards and backlog links | COMPLETE 2026-09-10 |
| G0 | M analysis | Coordinator + assigned integrators | F integrated on `dev_release2` | Post-F technical refresh + phase-specific implementation authorization | I10 RELEASED ONLY 2026-09-10; PORTFOLIO BLOCKED |
| H0 | external | H + coordinator | H/YOC accepted and integrated | Release portfolio service/schema/tests, provide exact target SHA, I re-read | BLOCKED |
| I10 | M | G3 backend owner | G0 developer authorization; no H/F files | Calendar-return backend series + provenance, no resolver duplication | COMPLETE 2026-09-10 / INTEGRATION PENDING |
| I20 | L | Portfolio backend integrator | G0 + H0 + F engine released | Additive daily broker P&L + signed canonical income | BLOCKED |
| I30 | L | Portfolio backend integrator | I20 + same-resolver OHLC envelope | Daily total candles + flat fallback + strict close identity | BLOCKED |
| I40 | M | Portfolio backend integrator + coordinator | I20 + I30 + post-H report contract | DTO/report/cache wiring, then coordinator API sync | BLOCKED |
| I50 | L | GrowthChart owner | I40 | Value/Return/P&L core modes; Line/Candles/Income P&L submodes; broker lines and sum aggregation | BLOCKED |
| I60 | M | G3 Asset UI owner | I10 + coordinator release after shared integration | Historical N-day primary mode in final Asset detail | BLOCKED |
| I70 | L | Test author + owners | Relevant implementation phases; H test ownership released | Targeted backend/frontend regressions and integration gates | BLOCKED |
| I80 | S | Docs writer + coordinator | Stable integrated UI | English docs, coordinator i18n/runner/changelog records | BLOCKED |
| I90 | M | Developer + coordinator | I50 + I60 + I70 + I80 | Desktop/mobile operational review, corrections, integration handoff | BLOCKED |

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

> **Note implementazione (G0 technical refresh, 2026-09-10):** F's merged
> source was re-read at `0af66da5...`; final findings and the H-before-I gate
> are recorded in section 2. Gate 0 is not complete because implementation
> authorization is absent. No implementation/test/runtime action was taken.

> **Note implementazione (G0 I10 release, 2026-09-10):** developer explicitly
> authorized only the signal-owned calendar rolling-return slice on
> `0af66da5f366a9559549154631a4ee15ca620915`. Authorized production boundary:
> dedicated plugin/helper plus minimal signal schema/catalog/service seam.
> Excluded: Asset/portfolio/UI/F/H/shared generated surfaces. Portfolio Gate 0
> remains blocked.

### 6.1 Parallel work after Gate 0

Before H integration, only I10 may be considered independently, after explicit
developer authorization. Its implementation file set must remain within the
signal layer and avoid `asset_source.py`, `price_resolver.py`,
`portfolio_engine.py`, `portfolio_service.py`, `schemas/portfolio.py` and
H-owned portfolio tests.

After H0, the portfolio backend integrator re-reads/re-reserves shared files,
then I20 starts. I30 waits for I20 and extends the same resolver path. I50 waits
for the integrated report contract. I60 waits for I10 plus an explicit
coordinator release so Asset UI work cannot outrun shared integration.

### 6.2 File reservations

| Owner | Reserved surfaces |
|---|---|
| H until integration | `portfolio_service.py`, `schemas/portfolio.py`, relevant portfolio service/API tests, approved FIFO eligibility seam, `ExposureTable.svelte` and test |
| F until coordinator release | `portfolio_engine.py`; preserve its shared FX cache-identity helper and current tests |
| G3 backend | New calendar signal plugin/helper plus signal-owned schema/service tests only; no H/F surface |
| Future portfolio backend integrator | After H/F release: `portfolio_engine.py`, `price_resolver.py`, `portfolio_service.py`, `schemas/portfolio.py`, portfolio cache behavior |
| GrowthChart owner | `GrowthChart.svelte`, `timeSeriesAggregation.ts`, portfolio store, Dashboard/Broker mounts |
| G3 Asset UI | Asset detail page and additive PriceChartFull props/helpers |
| Coordinator | API client generation, i18n catalogues, test runner, nav, changelog, master records |
| Test author | Distinct new/repaired tests only after authorization; portfolio service/API files wait for H release |
| Docs writer | English MkDocs pages after UI/contract stability |

The post-F overlap is now known: preserve the F transactions link in Asset
detail, F's L1 FX identity in the engine and F's tests. H remains the active
shared-file blocker. No I owner edits a reserved file before the coordinator
records its release.

### 6.3 Remaining developer/coordinator gates

No product decision remains open. Readiness still requires:

1. Explicit developer authorization to implement I10 or any later phase.
2. Coordinator confirmation that I10's final file set is signal-only.
3. H accepted/integrated SHA and release of service/schema/portfolio tests.
4. F release of `portfolio_engine.py` as integration-stable.
5. A new post-H exact baseline and conflict refresh before I20.

### 6.4 I10 execution progress

| Step | Scope | Status |
|---|---|---|
| I10.0 | Baseline, post-F resolver verification, authorization and exact file ownership | COMPLETE 2026-09-10 |
| I10.1 | Test-author characterization/regressions in assigned signal test files | COMPLETE 2026-09-10 |
| I10.2 | Sparse typed provenance + internal-catalog execution seam | COMPLETE 2026-09-10 |
| I10.3 | Dedicated calendar-day rolling-return plugin/helper | COMPLETE 2026-09-10 |
| I10.4 | Targeted schema/registry/plugin/asset-signal gates and lint/format | COMPLETE 2026-09-10 |
| I10.5 | Plan evidence, exact manifest and frozen integration handoff | COMPLETE 2026-09-10 |

> **Note implementazione (I10.0, 2026-09-10):** clean exact baseline
> `0af66da5...` verified. `AssetPriceSeries` and Asset query provide the
> approved existing resolution semantics; no new resolver is required.
> Signal-only implementation can avoid every H/F-reserved production file.
> Tests are delegated only in
> `test_signal_registry.py`, `test_risk_signal_plugins.py`,
> `test_asset_signals.py` and `test_signal_schemas.py`; no runner edit is
> required because all four files are already registered.

> **Note implementazione (I10.1, 2026-09-10):** `test-author` added
> contract-first coverage only to the four assigned, already-registered files:
> `test_signal_registry.py`, `test_risk_signal_plugins.py`,
> `test_asset_signals.py` and `test_signal_schemas.py`. Cases cover hidden but
> executable registration, sparse typed provenance, calendar-vs-observation
> windows, all four N values/default 30, target-currency integration,
> backward-resolved references, missing/invalid states and unchanged legacy
> rolling return. It ran no command and requested no runner edit.

> **Note implementazione (I10.2, 2026-09-10):** added strict
> `SignalCalendarReturnPointStatus`, typed provenance and a calendar-specific
> value-point subtype. Existing `SignalValuePoint` remains exactly
> `date + value`; provenance appears only on the new subtype. Added
> `SignalPlugin.catalog_visible=True` and filtered only
> `SignalPluginRegistry.list_definitions()`: hidden plugins remain
> auto-discovered/executable through `get_plugin()`, while public Asset/FX
> overlay catalogs and their existing 22/9 cardinalities stay unchanged.

> **Note implementazione (I10.3, 2026-09-10):** added hidden
> `ASSET_CALENDAR_ROLLING_RETURN`. Params are exactly
> `window_days=7|30|90|365`, default 30. The plugin consumes the existing
> target-currency dense daily `SignalPricePoint` series, performs exact
> `t-N` calendar lookup, emits one typed value/null point per input date and
> reports current/reference price plus available FX observation provenance.
> No resolver, staleness threshold, Asset/portfolio/UI or legacy
> `RISK_ROLLING_RETURN` behavior changed.

> **Fuori pista (I10.4 lint, 2026-09-10):** the first exact-file Ruff check
> stopped before test collection on one `I001` import-order finding in the new
> plugin. No DB, file generation or server was touched. Reordered the one
> import manually; no broad autofix was used.

> **Fuori pista (I10.4 risk selector, 2026-09-10):** command
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services risk-all
> calendar` recreated only the assigned TEST DB, started no server, selected
> 16 tests and returned 15 pass / 1 fail. The sole mismatch was
> `RiskResultMetadata.computed_at`, correctly different between two sequential
> service calls; every reported stable field matched. A required test-author
> follow-up produced no patch, so the integrator normalized only `computed_at`
> in that one equality assertion without weakening any stable payload check.

> **Fuori pista (I10.4 exact-N warm-up, 2026-09-10):** tightening warm-up from
> N+1 to the exact required N calendar days correctly avoided false partial
> status at a boundary, but the targeted risk selector then returned
> 22 pass / 2 fail: with no resolvable visible reference, the plugin attempted
> to construct an all-null series and central schema validation classified it
> as FAILED before SignalService could produce UNAVAILABLE. The command touched
> only the assigned TEST DB and started no server. Added signal-owned
> `validate_input()` that raises typed `INSUFFICIENT_HISTORY` only when no
> visible date has its exact `t-N` point; exact-N warm-up remains unchanged.

> **Fuori pista (I10.4 code review, 2026-09-10):** final read-only code review
> found that unavoidable pre-visible warm-up nulls were counted in
> `UNDEFINED_METRIC_WINDOW` even though SignalService slices those points before
> returning the visible series. This could produce an OK visible result with a
> false warning. Restricted warning counts to `context.requested_range`;
> `test-author` added the focused no-warning assertion to the existing Asset
> warm-up integration case.

> **Note implementazione (I10.4, 2026-09-10):** all commands used
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` and the assigned lane
> `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`. Final evidence:
> Black exact-file pass; Ruff exact-file pass; `schemas signals` 477/477;
> `services signal-registry` 68/68; `services signal-service` 45/45;
> `services asset-signals` 18/18; `services signal-plugin-matrix` 65/65;
> final `services risk-all` 134/134. Earlier targeted selectors also proved
> six provenance schemas, all calendar windows/statuses, target-currency
> integration and the unchanged legacy sibling. Services commands recreated
> only the isolated TEST DB; no backend server was started.

> **Note implementazione (I10.5, 2026-09-10):** production delta is confined
> to `schemas/signals.py`, `provider_registry.py`, `signal_plugins/base.py`
> and new `signal_plugins/calendar_rolling_return.py`; test delta is confined
> to the four assigned registered files. Final read-only code review found one
> false warm-up-warning leak; its fix and focused regression are green. No
> runner, Asset/portfolio/UI, i18n, generated client, docs, nav or changelog
> file changed. Port 6157 is free. The hidden plugin is ready for integration;
> UI consumption and coordinator-owned API client generation remain deferred
> to authorized I60/shared integration.

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
F has already added FX-identity cases to
`test_financial/test_portfolio_service.py` and cache-clear cases to
`test_fx_core.py`; H now owns relevant portfolio service/API tests until
integration. I test work must append to the integrated tests, never replace
those contracts.

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
- Unsupported short fails closed; broader short accounting is separately
  authorized work.

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
